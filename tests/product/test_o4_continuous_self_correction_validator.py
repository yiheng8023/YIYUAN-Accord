from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from harness import task_validator_o4_continuous_self_correction as validator


SOURCE_REVISION = "a" * 40
SOURCE_CARRIER_ID = "thread_01source123456"
DESTINATION_CARRIER_ID = "thread_01destination789"


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
        event(0, "codex-app-server-response", "registered-source-goal-observed", "source", "active"),
        event(1, "codex-app-server-notification", "context-compaction-started", "source", "observed"),
        event(2, "codex-app-server-notification", "context-compaction-completed", "source", "observed"),
        event(3, "codex-app-server-response", "registered-source-goal-preserved-after-compaction", "source", "active"),
        event(4, "canonical-verifier-observation", "post-compaction-authority-verified", "source", "valid"),
        event(5, "git-observation", "post-compaction-head-reconciled", "source", "matching"),
    ]


def transition_events() -> list[dict[str, object]]:
    return [
        event(0, "carrier-fitness-observation", "capacity-risk-or-unknown-rule-triggered", "source", "transition-required"),
        event(1, "codex-app-server-response", "registered-source-goal-observed", "source", "active"),
        event(2, "codex-app-server-response", "same-goal-fork-request-accepted", "destination", "created"),
        event(3, "codex-app-server-notification", "destination-thread-started", "destination", "observed"),
        event(4, "codex-app-server-response", "registered-goal-preserved-in-destination", "destination", "active"),
        event(5, "canonical-verifier-observation", "destination-authority-verified", "destination", "valid"),
        event(6, "git-observation", "destination-head-reconciled", "destination", "matching"),
        event(7, "harness-source-release-preflight", "source-release-allowed", "source", "allowed"),
        event(8, "codex-app-server-notification", "source-goal-released", "source", "released"),
        event(9, "codex-app-server-response", "source-carrier-released", "source", "released"),
    ]


def canonical_report() -> dict[str, object]:
    return {
        "valid": True,
        "programStatus": "active",
        "completionState": "in-progress",
        "activeIncrement": validator.INCREMENT_ID,
        "criterionStates": {
            "O1": True,
            "O2": False,
            "O3": False,
            "O4": False,
            "O5": False,
            "G1": True,
            "G2": True,
            "G3": True,
            "G4": True,
        },
        "errors": [],
    }


def app_message(message: dict[str, object]) -> dict[str, object]:
    return {
        "source": "codex-app-server-json-rpc-v0.147.0",
        "message": message,
    }


def goal_response(request_id: int, carrier_id: str) -> dict[str, object]:
    return app_message(
        {
            "id": request_id,
            "result": {
                "goal": {
                    "threadId": carrier_id,
                    "objective": validator.CARRIER_GOAL_TEXT,
                    "status": "active",
                    "tokenBudget": None,
                    "tokensUsed": 123,
                    "timeUsedSeconds": 7,
                    "createdAt": 1_777_000_000,
                    "updatedAt": 1_777_000_007,
                }
            },
        }
    )


def raw_compaction_observations() -> list[dict[str, object]]:
    return [
        app_message(
            {
                "method": "thread/goal/get",
                "id": 5,
                "params": {"threadId": SOURCE_CARRIER_ID},
            }
        ),
        goal_response(5, SOURCE_CARRIER_ID),
        app_message(
            {
                "method": "thread/compact/start",
                "id": 7,
                "params": {"threadId": SOURCE_CARRIER_ID},
            }
        ),
        app_message({"id": 7, "result": {}}),
        app_message(
            {
                "method": "item/started",
                "params": {
                    "threadId": SOURCE_CARRIER_ID,
                    "turnId": "turn_01000001",
                    "item": {"type": "contextCompaction", "id": "item_01000001"},
                },
            }
        ),
        app_message(
            {
                "method": "item/completed",
                "params": {
                    "threadId": SOURCE_CARRIER_ID,
                    "turnId": "turn_01000001",
                    "item": {"type": "contextCompaction", "id": "item_01000001"},
                },
            }
        ),
        app_message(
            {
                "method": "thread/goal/get",
                "id": 8,
                "params": {"threadId": SOURCE_CARRIER_ID},
            }
        ),
        goal_response(8, SOURCE_CARRIER_ID),
        {
            "source": "python--B--m-harness-verify-json",
            "carrierId": SOURCE_CARRIER_ID,
            "report": canonical_report(),
        },
        {
            "source": "git-rev-parse-and-status-v1",
            "carrierId": SOURCE_CARRIER_ID,
            "head": SOURCE_REVISION,
            "expectedHead": SOURCE_REVISION,
            "statusPorcelainV1": "",
        },
    ]


def raw_transition_observations() -> list[dict[str, object]]:
    return [
        {
            "source": "task-bound-carrier-fitness-observer-v1",
            "carrierId": SOURCE_CARRIER_ID,
            "remainingCapacityState": "unknown",
            "ruleIdentity": validator.TRANSITION_AND_CLEANUP_BOUNDARY[
                "unknownCapacityRule"
            ],
            "materialCheckpointCount": 7,
            "transitionTriggered": True,
        },
        app_message(
            {
                "method": "thread/goal/get",
                "id": 10,
                "params": {"threadId": SOURCE_CARRIER_ID},
            }
        ),
        goal_response(10, SOURCE_CARRIER_ID),
        app_message(
            {
                "method": "thread/fork",
                "id": 12,
                "params": {
                    "threadId": SOURCE_CARRIER_ID,
                    "deferGoalContinuation": True,
                },
            }
        ),
        app_message(
            {
                "id": 12,
                "result": {
                    "thread": {
                        "id": DESTINATION_CARRIER_ID,
                        "forkedFromId": SOURCE_CARRIER_ID,
                        "cwd": "C:\\private\\discarded",
                    }
                },
            }
        ),
        app_message(
            {
                "method": "thread/started",
                "params": {
                    "thread": {
                        "id": DESTINATION_CARRIER_ID,
                        "forkedFromId": SOURCE_CARRIER_ID,
                    }
                },
            }
        ),
        app_message(
            {
                "method": "thread/goal/get",
                "id": 13,
                "params": {"threadId": DESTINATION_CARRIER_ID},
            }
        ),
        goal_response(13, DESTINATION_CARRIER_ID),
        {
            "source": "python--B--m-harness-verify-json",
            "carrierId": DESTINATION_CARRIER_ID,
            "report": canonical_report(),
        },
        {
            "source": "git-rev-parse-and-status-v1",
            "carrierId": DESTINATION_CARRIER_ID,
            "head": SOURCE_REVISION,
            "expectedHead": SOURCE_REVISION,
            "statusPorcelainV1": "",
        },
        {
            "source": "harness-source-carrier-release-preflight-v1",
            "carrierId": SOURCE_CARRIER_ID,
            "report": {"allowed": True, "state": "release-eligible"},
        },
        app_message(
            {
                "method": "thread/goal/clear",
                "id": 20,
                "params": {"threadId": SOURCE_CARRIER_ID},
            }
        ),
        app_message({"id": 20, "result": {"cleared": True}}),
        app_message(
            {
                "method": "thread/goal/cleared",
                "params": {"threadId": SOURCE_CARRIER_ID},
            }
        ),
        app_message(
            {
                "method": "thread/archive",
                "id": 21,
                "params": {"threadId": SOURCE_CARRIER_ID},
            }
        ),
        app_message({"id": 21, "result": {}}),
        app_message(
            {
                "method": "thread/archived",
                "params": {"threadId": SOURCE_CARRIER_ID},
            }
        ),
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
            "goalBoundary": "registered-o4-controlled-carrier-goal-under-current-v1.2-acceptance",
            "controlledGoalArtifact": validator.CARRIER_GOAL_BINDING,
            "carrierState": {
                "repository": "single-main-checkout-clean-at-scenario-start",
                "conversation": "native-active-goal-observed-before-and-after-each-controlled-carrier-event",
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
                f"{validator.VALIDATOR_LOCATOR}:project_raw_carrier_observations"
            ),
            "codexSourceBinding": validator.CODEX_SOURCE_BINDING,
            "controlledGoalArtifact": validator.CARRIER_GOAL_BINDING,
            "receiptOnlyAccepted": False,
        },
    }


class O4ContinuousSelfCorrectionValidatorTests(unittest.TestCase):
    def test_controlled_goal_artifact_matches_code_owned_binding(self) -> None:
        raw = Path(validator.CARRIER_GOAL_LOCATOR).read_bytes()
        self.assertEqual(validator.CARRIER_GOAL_TEXT.encode("utf-8"), raw)
        self.assertEqual(validator.CARRIER_GOAL_SHA256, hashlib.sha256(raw).hexdigest())

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
        self.assertLess(
            classes.index("source-goal-released"),
            classes.index("source-carrier-released"),
        )
        reordered = transition_events()
        reordered[5], reordered[9] = reordered[9], reordered[5]
        reordered[5]["ordinal"] = 5
        reordered[9]["ordinal"] = 9
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

    def test_privacy_scan_does_not_treat_https_url_as_windows_drive_path(self) -> None:
        self.assertFalse(
            validator._contains_private_value("https://github.com/openai/codex")
        )
        self.assertTrue(validator._contains_private_value("C:/Users/person/source"))

    def test_raw_compaction_projection_derives_events_and_discards_identifiers(self) -> None:
        projection = validator.project_raw_carrier_observations(
            validator.CARRIER_SCENARIO_IDENTITIES[0],
            raw_compaction_observations(),
            source_carrier_id=SOURCE_CARRIER_ID,
            expected_head=SOURCE_REVISION,
        )
        serialized = json.dumps(projection, sort_keys=True)
        self.assertNotIn(SOURCE_CARRIER_ID, serialized)
        self.assertNotIn("turn_01000001", serialized)
        self.assertNotIn("item_01000001", serialized)
        self.assertEqual(
            [item["eventClass"] for item in projection["eventSequence"]],
            [item[1] for item in validator.COMPACTION_EVENT_SEQUENCE],
        )

        mismatched_item = raw_compaction_observations()
        mismatched_item[5]["message"]["params"]["item"]["id"] = "item_01000002"
        with self.assertRaisesRegex(ValueError, "identities"):
            validator.project_raw_carrier_observations(
                validator.CARRIER_SCENARIO_IDENTITIES[0],
                mismatched_item,
                source_carrier_id=SOURCE_CARRIER_ID,
                expected_head=SOURCE_REVISION,
            )

        mismatched_response = raw_compaction_observations()
        mismatched_response[3]["message"]["id"] = 8
        with self.assertRaisesRegex(ValueError, "response"):
            validator.project_raw_carrier_observations(
                validator.CARRIER_SCENARIO_IDENTITIES[0],
                mismatched_response,
                source_carrier_id=SOURCE_CARRIER_ID,
                expected_head=SOURCE_REVISION,
            )

    def test_raw_transition_binds_fork_destination_and_release_order(self) -> None:
        projection = validator.project_raw_carrier_observations(
            validator.CARRIER_SCENARIO_IDENTITIES[1],
            raw_transition_observations(),
            source_carrier_id=SOURCE_CARRIER_ID,
            destination_carrier_id=DESTINATION_CARRIER_ID,
            expected_head=SOURCE_REVISION,
        )
        serialized = json.dumps(projection, sort_keys=True)
        self.assertNotIn(SOURCE_CARRIER_ID, serialized)
        self.assertNotIn(DESTINATION_CARRIER_ID, serialized)
        self.assertNotIn("C:\\\\private", serialized)
        self.assertEqual(
            "source-carrier-released",
            projection["eventSequence"][-1]["eventClass"],
        )

        cross_thread = raw_transition_observations()
        cross_thread[4]["message"]["result"]["thread"][
            "forkedFromId"
        ] = "thread_01different999"
        with self.assertRaisesRegex(ValueError, "source carrier"):
            validator.project_raw_carrier_observations(
                validator.CARRIER_SCENARIO_IDENTITIES[1],
                cross_thread,
                source_carrier_id=SOURCE_CARRIER_ID,
                destination_carrier_id=DESTINATION_CARRIER_ID,
                expected_head=SOURCE_REVISION,
            )

        partial_history = raw_transition_observations()
        partial_history[3]["message"]["params"]["beforeTurnId"] = "turn_01000001"
        with self.assertRaisesRegex(ValueError, "request"):
            validator.project_raw_carrier_observations(
                validator.CARRIER_SCENARIO_IDENTITIES[1],
                partial_history,
                source_carrier_id=SOURCE_CARRIER_ID,
                destination_carrier_id=DESTINATION_CARRIER_ID,
                expected_head=SOURCE_REVISION,
            )

        no_goal = raw_transition_observations()
        no_goal[2]["message"]["result"]["goal"] = None
        with self.assertRaisesRegex(ValueError, "registered active goal"):
            validator.project_raw_carrier_observations(
                validator.CARRIER_SCENARIO_IDENTITIES[1],
                no_goal,
                source_carrier_id=SOURCE_CARRIER_ID,
                destination_carrier_id=DESTINATION_CARRIER_ID,
                expected_head=SOURCE_REVISION,
            )

        changed_goal = raw_transition_observations()
        changed_goal[7]["message"]["result"]["goal"]["objective"] = "different goal"
        with self.assertRaisesRegex(ValueError, "registered active goal"):
            validator.project_raw_carrier_observations(
                validator.CARRIER_SCENARIO_IDENTITIES[1],
                changed_goal,
                source_carrier_id=SOURCE_CARRIER_ID,
                destination_carrier_id=DESTINATION_CARRIER_ID,
                expected_head=SOURCE_REVISION,
            )

        no_deferred_goal = raw_transition_observations()
        del no_deferred_goal[3]["message"]["params"]["deferGoalContinuation"]
        with self.assertRaisesRegex(ValueError, "deferred-goal"):
            validator.project_raw_carrier_observations(
                validator.CARRIER_SCENARIO_IDENTITIES[1],
                no_deferred_goal,
                source_carrier_id=SOURCE_CARRIER_ID,
                destination_carrier_id=DESTINATION_CARRIER_ID,
                expected_head=SOURCE_REVISION,
            )

        source_goal_retained = raw_transition_observations()
        source_goal_retained[12]["message"]["result"]["cleared"] = False
        with self.assertRaisesRegex(ValueError, "goal-clear response"):
            validator.project_raw_carrier_observations(
                validator.CARRIER_SCENARIO_IDENTITIES[1],
                source_goal_retained,
                source_carrier_id=SOURCE_CARRIER_ID,
                destination_carrier_id=DESTINATION_CARRIER_ID,
                expected_head=SOURCE_REVISION,
            )

        wrong_goal_cleared = raw_transition_observations()
        wrong_goal_cleared[13]["message"]["params"]["threadId"] = (
            DESTINATION_CARRIER_ID
        )
        with self.assertRaisesRegex(ValueError, "goal-clear notification"):
            validator.project_raw_carrier_observations(
                validator.CARRIER_SCENARIO_IDENTITIES[1],
                wrong_goal_cleared,
                source_carrier_id=SOURCE_CARRIER_ID,
                destination_carrier_id=DESTINATION_CARRIER_ID,
                expected_head=SOURCE_REVISION,
            )

        archive_before_goal_clear = raw_transition_observations()
        archive_before_goal_clear[11], archive_before_goal_clear[14] = (
            archive_before_goal_clear[14],
            archive_before_goal_clear[11],
        )
        with self.assertRaisesRegex(ValueError, "request"):
            validator.project_raw_carrier_observations(
                validator.CARRIER_SCENARIO_IDENTITIES[1],
                archive_before_goal_clear,
                source_carrier_id=SOURCE_CARRIER_ID,
                destination_carrier_id=DESTINATION_CARRIER_ID,
                expected_head=SOURCE_REVISION,
            )

    def test_raw_projector_rejects_normalized_receipt_and_reordered_release(self) -> None:
        with self.assertRaisesRegex(ValueError, "count|envelope"):
            validator.project_raw_carrier_observations(
                validator.CARRIER_SCENARIO_IDENTITIES[0],
                compaction_events(),
                source_carrier_id=SOURCE_CARRIER_ID,
                expected_head=SOURCE_REVISION,
            )
        reordered = raw_transition_observations()
        reordered[5], reordered[10] = reordered[10], reordered[5]
        with self.assertRaises(ValueError):
            validator.project_raw_carrier_observations(
                validator.CARRIER_SCENARIO_IDENTITIES[1],
                reordered,
                source_carrier_id=SOURCE_CARRIER_ID,
                destination_carrier_id=DESTINATION_CARRIER_ID,
                expected_head=SOURCE_REVISION,
            )

    def test_projection_pressure_is_deterministic_and_fail_closed(self) -> None:
        expected_compaction = validator.project_carrier_events(
            validator.CARRIER_SCENARIO_IDENTITIES[0], compaction_events()
        )["eventShapeSha256"]
        expected_transition = validator.project_carrier_events(
            validator.CARRIER_SCENARIO_IDENTITIES[1], transition_events()
        )["eventShapeSha256"]

        def one_cycle(index: int) -> tuple[str, str, bool, bool]:
            compaction = validator.project_raw_carrier_observations(
                validator.CARRIER_SCENARIO_IDENTITIES[0],
                raw_compaction_observations(),
                source_carrier_id=SOURCE_CARRIER_ID,
                expected_head=SOURCE_REVISION,
            )["eventShapeSha256"]
            transition = validator.project_raw_carrier_observations(
                validator.CARRIER_SCENARIO_IDENTITIES[1],
                raw_transition_observations(),
                source_carrier_id=SOURCE_CARRIER_ID,
                destination_carrier_id=DESTINATION_CARRIER_ID,
                expected_head=SOURCE_REVISION,
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
        with patch.object(validator, "_goal_artifact_committed", return_value=True):
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
        with patch.object(validator, "_goal_artifact_committed", return_value=True):
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

        nested: dict[str, object] = {"leaf": True}
        for _ in range(validator.MAX_JSON_DEPTH + 1):
            nested = {"next": nested}
        with self.assertRaisesRegex(ValueError, "message"):
            validator._app_server_record(app_message(nested))

        cyclic: dict[str, object] = {}
        cyclic["self"] = cyclic
        with self.assertRaisesRegex(ValueError, "message"):
            validator._app_server_record(app_message(cyclic))


if __name__ == "__main__":
    unittest.main()
