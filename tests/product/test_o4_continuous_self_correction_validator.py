from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from pathlib import Path
import tempfile
import unittest

from harness import task_validator_o4_continuous_self_correction as validator


SOURCE_REVISION = "a" * 40


def event(
    ordinal: int,
    source_class: str,
    event_class: str,
    carrier_role: str,
    state: str,
) -> dict[str, object]:
    return {
        "ordinal": ordinal,
        "sourceClass": source_class,
        "eventClass": event_class,
        "carrierRole": carrier_role,
        "state": state,
    }


def compaction_events() -> list[dict[str, object]]:
    return [
        event(0, "codex-app-server-notification", "context-compaction-started", "source", "observed"),
        event(1, "codex-app-server-notification", "context-compaction-completed", "source", "observed"),
        event(2, "canonical-verifier-observation", "post-compaction-authority-verified", "source", "valid"),
        event(3, "git-observation", "post-compaction-head-reconciled", "source", "matching"),
    ]


def transition_events() -> list[dict[str, object]]:
    return [
        event(0, "carrier-fitness-observation", "capacity-risk-or-unknown-rule-triggered", "source", "transition-required"),
        event(1, "codex-app-server-response", "same-goal-fork-request-accepted", "destination", "created"),
        event(2, "codex-app-server-notification", "destination-thread-started", "destination", "observed"),
        event(3, "canonical-verifier-observation", "destination-authority-verified", "destination", "valid"),
        event(4, "git-observation", "destination-head-reconciled", "destination", "matching"),
        event(5, "harness-source-release-preflight", "source-release-allowed", "source", "allowed"),
        event(6, "codex-app-server-response", "source-carrier-released", "source", "released"),
    ]


def valid_registration_values() -> dict[str, object]:
    return {
        "normativeProfileIdentity": "bound-by-core",
        "cohortProtocolIdentity": "bound-by-core",
        "profileSha256": "b" * 64,
        "cohortProtocolSha256": "c" * 64,
        "environmentAttributionBinding": "bound-by-core",
        "counterexampleIdentityAndSource": validator.COUNTEREXAMPLE_SOURCES,
        "startingAuthorityGoalAndCarrierState": {
            "sourceRevision": SOURCE_REVISION,
            "authorityPaths": [
                "product/constitution.json",
                "product/program.json",
                "product/acceptance.json",
            ],
            "goalBoundary": "current-v1.2-completion-expression-under-named-human-authority",
            "carrierState": {
                "repository": "single-main-checkout-clean-at-scenario-start",
                "conversation": "same-goal-current-carrier-before-controlled-event",
                "capacitySignal": "reliable-risk-or-explicit-unknown-rule-only",
            },
        },
        "injectedOrObservedFailure": validator.FAILURE_BINDINGS,
        "expectedDetectionAndCorrection": validator.CORRECTION_BINDINGS,
        "transitionAndCleanupBoundary": validator.TRANSITION_AND_CLEANUP_BOUNDARY,
        "scenarioValidator": {
            "suiteIdentity": validator.SUITE_IDENTITY,
            "scenarioIdentities": list(validator.SCENARIO_IDENTITIES),
            "validatorIdentity": validator.VALIDATOR_KIND,
            "validatorLocator": validator.VALIDATOR_LOCATOR,
            "hostProjectionBuilder": (
                f"{validator.VALIDATOR_LOCATOR}:project_carrier_events"
            ),
            "codexSourceBinding": validator.CODEX_SOURCE_BINDING,
            "receiptOnlyAccepted": False,
        },
    }


class O4ContinuousSelfCorrectionValidatorTests(unittest.TestCase):
    def test_six_acceptance_owned_scenarios_are_exact_and_distinct(self) -> None:
        self.assertEqual(6, len(validator.SCENARIO_IDENTITIES))
        self.assertEqual(6, len(set(validator.SCENARIO_IDENTITIES)))
        self.assertEqual(
            {
                "repeated-user-correction-detection",
                "stale-or-conflicting-instruction-rejection",
                "expected-versus-observed-effect-mismatch",
                "code-topology-or-residue-reconciliation",
            },
            {item.scenario_class for item in validator.FAULT_SCENARIOS},
        )

    def test_compaction_projection_requires_authority_and_head_reverification(self) -> None:
        projection = validator.project_carrier_events(
            validator.CARRIER_SCENARIO_IDENTITIES[0], compaction_events()
        )
        self.assertEqual(0, projection["retainedPrivateFieldCount"])
        self.assertEqual(0, projection["userReconstructionEventCount"])
        self.assertEqual(
            "post-compaction-head-reconciled",
            projection["eventSequence"][-1]["eventClass"],
        )
        incomplete = compaction_events()[:-1]
        with self.assertRaisesRegex(ValueError, "count"):
            validator.project_carrier_events(
                validator.CARRIER_SCENARIO_IDENTITIES[0], incomplete
            )

    def test_transition_rejects_source_release_before_destination_verification(self) -> None:
        projection = validator.project_carrier_events(
            validator.CARRIER_SCENARIO_IDENTITIES[1], transition_events()
        )
        classes = [item["eventClass"] for item in projection["eventSequence"]]
        self.assertLess(
            classes.index("destination-head-reconciled"),
            classes.index("source-carrier-released"),
        )
        reordered = transition_events()
        reordered[3], reordered[6] = reordered[6], reordered[3]
        reordered[3]["ordinal"] = 3
        reordered[6]["ordinal"] = 6
        with self.assertRaisesRegex(ValueError, "chronology"):
            validator.project_carrier_events(
                validator.CARRIER_SCENARIO_IDENTITIES[1], reordered
            )

    def test_projection_rejects_private_path_and_host_identifier(self) -> None:
        private_path = compaction_events()
        private_path[0]["state"] = "C:\\Users\\person\\private-rollout.jsonl"
        with self.assertRaisesRegex(ValueError, "private"):
            validator.project_carrier_events(
                validator.CARRIER_SCENARIO_IDENTITIES[0], private_path
            )
        private_id = compaction_events()
        private_id[0]["state"] = "thread_01abcdef"
        with self.assertRaisesRegex(ValueError, "private"):
            validator.project_carrier_events(
                validator.CARRIER_SCENARIO_IDENTITIES[0], private_id
            )

    def test_projection_pressure_is_deterministic_and_fail_closed(self) -> None:
        expected_compaction = validator.project_carrier_events(
            validator.CARRIER_SCENARIO_IDENTITIES[0], compaction_events()
        )["eventShapeSha256"]
        expected_transition = validator.project_carrier_events(
            validator.CARRIER_SCENARIO_IDENTITIES[1], transition_events()
        )["eventShapeSha256"]

        def one_cycle(index: int) -> tuple[str, str, bool, bool]:
            compaction = validator.project_carrier_events(
                validator.CARRIER_SCENARIO_IDENTITIES[0], compaction_events()
            )["eventShapeSha256"]
            transition = validator.project_carrier_events(
                validator.CARRIER_SCENARIO_IDENTITIES[1], transition_events()
            )["eventShapeSha256"]
            private = compaction_events()
            private[0]["state"] = f"session_{index:08d}"
            private_rejected = False
            chronology_rejected = False
            try:
                validator.project_carrier_events(
                    validator.CARRIER_SCENARIO_IDENTITIES[0], private
                )
            except ValueError:
                private_rejected = True
            out_of_order = transition_events()
            out_of_order[4]["eventClass"] = "source-carrier-released"
            try:
                validator.project_carrier_events(
                    validator.CARRIER_SCENARIO_IDENTITIES[1], out_of_order
                )
            except ValueError:
                chronology_rejected = True
            return compaction, transition, private_rejected, chronology_rejected

        with ThreadPoolExecutor(max_workers=8) as pool:
            results = list(pool.map(one_cycle, range(256)))
        self.assertEqual(
            {(expected_compaction, expected_transition, True, True)},
            set(results),
        )

    def test_fault_suite_requires_detection_recovery_reverification_and_cleanup(self) -> None:
        def passing_executor(
            root: Path,
            source_revision: str,
            scenario: validator.FaultScenario,
        ) -> dict[str, object]:
            del root, source_revision, scenario
            return {
                "baselineValid": True,
                "divergenceDetected": True,
                "expectedDiagnosticObserved": True,
                "recoveredValid": True,
                "recoveredHeadMatches": True,
                "probeCleanupVerified": True,
                "faultReportSha256": "d" * 64,
                "recoveryReportSha256": "e" * 64,
            }

        suite = validator.run_fault_suite(
            Path("."), SOURCE_REVISION, executor=passing_executor
        )
        self.assertTrue(suite["allFaultControlsObserved"])
        self.assertTrue(suite["cleanupVerified"])

        def missing_recovery(
            root: Path,
            source_revision: str,
            scenario: validator.FaultScenario,
        ) -> dict[str, object]:
            result = passing_executor(root, source_revision, scenario)
            if scenario == validator.FAULT_SCENARIOS[2]:
                result["recoveredValid"] = False
            return result

        stopped = validator.run_fault_suite(
            Path("."), SOURCE_REVISION, executor=missing_recovery
        )
        self.assertFalse(stopped["allFaultControlsObserved"])

    def test_registration_binds_exact_six_scenarios_and_rejects_receipt_mode(self) -> None:
        increment = {
            "id": validator.INCREMENT_ID,
            "taskRegistration": {"sourceRevision": SOURCE_REVISION},
        }
        registration = {
            "incrementId": validator.INCREMENT_ID,
            "criterionIds": ["O4"],
            "preRegistrationValues": valid_registration_values(),
            "preMeasurementValidator": {
                "kind": validator.VALIDATOR_KIND,
                "version": 1,
                "locator": validator.VALIDATOR_LOCATOR,
            },
        }
        errors: list[str] = []
        self.assertTrue(
            validator.validate_registration(
                registration, increment, ("O4",), Path("."), errors
            ),
            errors,
        )
        receipt = deepcopy(registration)
        receipt["preRegistrationValues"]["scenarioValidator"][
            "receiptOnlyAccepted"
        ] = True
        errors = []
        self.assertFalse(
            validator.validate_registration(
                receipt, increment, ("O4",), Path("."), errors
            )
        )
        self.assertIn(
            "O4 correction suite validator and projection binding is invalid", errors
        )

    def test_evidence_rejects_bare_success_receipt_before_replay(self) -> None:
        errors: list[str] = []
        self.assertFalse(
            validator.validate_evidence(
                {
                    "incrementId": validator.INCREMENT_ID,
                    "criterionIds": ["O4"],
                    "source": {"kind": "self-report"},
                    "result": {"accepted": True},
                },
                "O4",
                Path("."),
                errors,
            )
        )
        self.assertEqual(
            ["O4 evidence requires replayed fault behavior and ordered host events"],
            errors,
        )

    def test_strict_json_rejects_duplicate_keys_and_nonfinite_values(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            duplicate = root / "duplicate.json"
            duplicate.write_bytes(b'{"schema":1,"schema":1}')
            with self.assertRaisesRegex(ValueError, "duplicate"):
                validator._strict_json_object(duplicate.read_bytes())
            with self.assertRaisesRegex(ValueError, "non-finite"):
                validator._strict_json_object(b'{"schema":NaN}')


if __name__ == "__main__":
    unittest.main()
