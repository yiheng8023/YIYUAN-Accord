from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch


from harness.task_validator_o1_lifecycle_suite import (
    SCENARIOS,
    execute_scenario,
    run_suite,
    validate_evidence,
    validate_registration,
)


SOURCE_REVISION = "e060a08f05361cb4cc9a67be050236cdbbde1de5"
SOURCE_PATH = "common/human-ai-collaboration-shortfalls"
SOURCE_MANIFEST_BLOB = "5b2bb49446c43b5d41bdd14fa6a844abefb7c1cc"
SLICES = [f"SG-{index:02d}" for index in range(1, 13)]


def registration_fixture() -> dict:
    phase_by_slice = {
        "SG-01": "intake-and-goal-context-binding",
        "SG-02": "transition-continuity-and-handoff",
        "SG-03": "premise-risk-and-domain-escalation",
        "SG-04": "capability-route-selection-and-retirement",
        "SG-05": "authority-reversibility-and-revocation",
        "SG-06": "evidence-provenance-and-claim-scope",
        "SG-07": "closure-readiness-and-release-transition",
        "SG-08": "human-review-veto-and-accountability",
        "SG-09": "environment-portability-and-evaluation",
        "SG-10": "feedback-correction-and-retirement",
        "SG-11": "governance-privacy-and-projection",
        "SG-12": "proportionality-control-cost-and-subtraction",
    }
    route_by_slice = {
        "SG-01": "native",
        "SG-02": "residual-harness",
        "SG-03": "accountable-domain",
        "SG-04": "native",
        "SG-05": "native",
        "SG-06": "residual-harness",
        "SG-07": "residual-harness",
        "SG-08": "accountable-domain",
        "SG-09": "residual-harness",
        "SG-10": "residual-harness",
        "SG-11": "residual-harness",
        "SG-12": "native",
    }
    values = {
        "normativeProfileIdentity": "harness-demand-to-outcome-v1.2-candidate.2",
        "cohortProtocolIdentity": "harness-controlled-conformance-v1.2-candidate.2",
        "profileSha256": "6b6f134ef49cd3cd161ef961ce2fe9e254f12d552f9e6d31f02c06009196d4f5",
        "cohortProtocolSha256": "83dc62fc6f749ac18c0136ab066fc63cd667ed5e231dee8d5ebfb00889e78303",
        "environmentAttributionBinding": {"fixture": "validated by the core seam"},
        "sourceCustodyRevisionAndPath": {
            "revision": SOURCE_REVISION,
            "path": SOURCE_PATH,
            "manifestBlob": SOURCE_MANIFEST_BLOB,
        },
        "sourceSliceIdentity": SLICES,
        "lifecyclePhaseApplicabilityAndOwner": [
            {
                "sourceSliceIdentity": source_slice,
                "lifecyclePhase": phase_by_slice[source_slice],
                "productOwner": "agent-autonomy-harness-v1.2",
                "applicability": "applicable",
            }
            for source_slice in SLICES
        ],
        "nativeOfficialExternalDomainOrResidualRoute": [
            {
                "sourceSliceIdentity": source_slice,
                "routeClass": route_by_slice[source_slice],
                "routeIdentity": (
                    f"{route_by_slice[source_slice]}:{source_slice.lower()}-with-"
                    f"task-specific-{SCENARIOS[index].mutation_identity}-guard"
                ),
                "sourceBoundJustification": (
                    f"{source_slice} at {SOURCE_REVISION}:{SOURCE_PATH} is exercised by "
                    f"{SCENARIOS[index].scenario_identity}"
                ),
                "residualOrUnsupportedBoundary": (
                    "controlled verifier effect only; no comparative burden, broad "
                    "effectiveness, distinct-Agent or untested-platform claim"
                ),
            }
            for index, source_slice in enumerate(SLICES)
        ],
        "claimedControlEffects": [
            {
                "sourceSliceIdentity": scenario.source_slice_identity,
                "effectClasses": list(scenario.effect_classes),
                "expectedObservableEffect": (
                    f"canonical verifier rejects {scenario.mutation_identity} with "
                    f"{scenario.expected_diagnostic}"
                ),
            }
            for scenario in SCENARIOS
        ],
        "controlledScenarioOrCodeValidator": {
            "suiteIdentity": "o1-lifecycle-coverage.controlled-v1",
            "scenarioIdentities": [
                f"o1-lifecycle-coverage.{source_slice.lower()}" for source_slice in SLICES
            ],
            "validatorIdentity": "o1-lifecycle-suite-validator-v1",
        },
        "claimLimitAndLifecycle": {
            "evidenceClass": "controlled-fault-injection",
            "claimCeiling": "bounded-v1.2-control-detection-stop-recovery-and-claim-limitation-only",
            "fieldClaimsExcluded": [
                "comparative-user-burden",
                "broad-real-world-effectiveness",
                "distinct-agent-equivalence",
            ],
            "retirementRule": "shrink-or-retire-when-sufficient-native-control-is-observed",
        },
    }
    return {
        "schema": 1,
        "id": "registration.o1-lifecycle-coverage.controlled-v1",
        "registeredAt": "2026-08-17T00:00:00+08:00",
        "taskIdentity": "conformance-unit.public-v1:0123456789abcdef0123456789abcdef",
        "incrementId": "increment.v12-o1-lifecycle-suite",
        "criterionIds": ["O1"],
        "preRegistrationValues": values,
        "acceptanceAuthority": {
            "locator": "product/acceptance.json",
            "criteriaContractSha256": "c90197006a028f78c6f7be29a7884ccc447e3c6e606c558b6527df465187095b",
        },
        "namedHumanAcceptor": "project maintainer",
        "qualitySafetyEvidenceAndResidueFloors": {
            "quality": "all twelve slices exactly once",
            "safety": "no unauthorized or irreversible external effect",
            "evidence": "observable replay rather than receipt assertion",
            "residue": "all isolated scenario roots deleted after capture",
        },
        "materialInterventionTaxonomy": ["controlled repository fault injection"],
        "materialCollaborationLossTaxonomy": ["unsupported claim promotion"],
        "scenarioEvidenceAndStopRule": {
            "evidenceClass": "controlled-fault-injection",
            "startingTruthBoundBefore": "immutable-registration",
            "executionStartsAfter": "immutable-registration",
            "expectedInvariantOrCounterexample": "each SG slice rejects its pre-registered counterexample or retains an explicit unsupported disposition",
            "failureDisposition": "retain the failed slice and keep O1 unverified",
            "stopRule": "stop on source drift, validator drift, unexpected side effect, unbounded residue, or any missing slice",
        },
        "claimLimits": ["finite controlled v1.2 delivery claim only"],
        "preMeasurementValidator": {
            "kind": "o1-lifecycle-suite-validator-v1",
            "version": 1,
            "locator": "harness/task_validator_o1_lifecycle_suite.py",
            "revision": "1" * 40,
            "sha256": "2" * 64,
        },
    }


def increment_fixture() -> dict:
    return {
        "id": "increment.v12-o1-lifecycle-suite",
        "acceptanceIds": ["O1", "G2", "G4"],
    }


class O1LifecycleSuiteRegistrationTests(unittest.TestCase):
    def test_accepts_exact_fixed_source_and_twelve_non_reference_dispositions(self) -> None:
        errors: list[str] = []

        accepted = validate_registration(
            registration_fixture(),
            increment_fixture(),
            ("O1",),
            Path.cwd(),
            errors,
        )

        self.assertTrue(accepted)
        self.assertEqual(errors, [])

    def test_rejects_missing_or_duplicated_source_slice(self) -> None:
        registration = registration_fixture()
        values = registration["preRegistrationValues"]
        values["sourceSliceIdentity"] = SLICES[:-1] + ["SG-11"]
        errors: list[str] = []

        accepted = validate_registration(
            registration,
            increment_fixture(),
            ("O1",),
            Path.cwd(),
            errors,
        )

        self.assertFalse(accepted)
        self.assertIn("O1 lifecycle suite must bind SG-01 through SG-12 exactly once", errors)

    def test_rejects_reference_or_implementation_presence_as_control_effect(self) -> None:
        registration = registration_fixture()
        values = registration["preRegistrationValues"]
        claimed = deepcopy(values["claimedControlEffects"])
        claimed[5]["effectClasses"] = ["reference-presence"]
        values["claimedControlEffects"] = claimed
        errors: list[str] = []

        accepted = validate_registration(
            registration,
            increment_fixture(),
            ("O1",),
            Path.cwd(),
            errors,
        )

        self.assertFalse(accepted)
        self.assertIn("O1 lifecycle suite claimed effects must be observable control effects", errors)

    def test_rejects_self_described_disposition_drift_from_the_fixed_suite(self) -> None:
        mutations = {
            "phase": lambda values: values["lifecyclePhaseApplicabilityAndOwner"][0].update(
                {"lifecyclePhase": "unbound-phase"}
            ),
            "route": lambda values: values[
                "nativeOfficialExternalDomainOrResidualRoute"
            ][0].update({"routeClass": "official"}),
            "effect": lambda values: values["claimedControlEffects"][0].update(
                {"effectClasses": ["prevention"]}
            ),
            "claim": lambda values: values["claimLimitAndLifecycle"].update(
                {"claimCeiling": "unbound-claim"}
            ),
        }

        for name, mutate in mutations.items():
            with self.subTest(name=name):
                registration = registration_fixture()
                mutate(registration["preRegistrationValues"])
                errors: list[str] = []

                accepted = validate_registration(
                    registration,
                    increment_fixture(),
                    ("O1",),
                    Path.cwd(),
                    errors,
                )

                self.assertFalse(accepted)


class O1LifecycleSuiteEvidenceTests(unittest.TestCase):
    def test_rejects_bare_accepted_receipt_without_observable_suite_replay(self) -> None:
        evidence = {
            "schema": 1,
            "criterionIds": ["O1"],
            "incrementId": "increment.v12-o1-lifecycle-suite",
            "source": {
                "kind": "controlled-o1-lifecycle-suite",
                "locator": "product/evidence/o1-lifecycle-suite-observation.json",
                "identity": "sha256:" + ("a" * 64),
            },
            "result": {"accepted": True},
            "validator": {
                "kind": "o1-lifecycle-suite-validator-v1",
                "version": 1,
            },
        }
        errors: list[str] = []

        accepted = validate_evidence(evidence, "O1", Path.cwd(), errors)

        self.assertFalse(accepted)
        self.assertIn(
            "O1 lifecycle suite evidence requires an observable twelve-slice replay",
            errors,
        )

    def test_accepts_only_content_addressed_observation_that_replays_exactly(self) -> None:
        source_revision = "4" * 40

        def executor(root: Path, revision: str, scenario: object) -> dict:
            del root
            self.assertEqual(revision, source_revision)
            return {
                "valid": False,
                "completionState": "in-progress",
                "errors": [getattr(scenario, "expected_diagnostic")],
                "probeCleanupVerified": True,
            }

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            observation = run_suite(root, source_revision, executor=executor)
            observation_path = (
                root / "product" / "evidence" / "o1-lifecycle-suite-observation.json"
            )
            observation_path.parent.mkdir(parents=True)
            observation_raw = (
                json.dumps(observation, ensure_ascii=False, indent=2) + "\n"
            ).encode("utf-8")
            observation_path.write_bytes(observation_raw)
            program_path = root / "product" / "program.json"
            program_path.write_text(
                json.dumps(
                    {
                        "increments": [
                            {
                                "id": "increment.v12-o1-lifecycle-suite",
                                "taskRegistration": {
                                    "sourceRevision": source_revision,
                                },
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )
            observation_sha256 = hashlib.sha256(observation_raw).hexdigest()
            evidence = {
                "schema": 1,
                "criterionIds": ["O1"],
                "incrementId": "increment.v12-o1-lifecycle-suite",
                "source": {
                    "kind": "controlled-o1-lifecycle-suite-observation",
                    "locator": "product/evidence/o1-lifecycle-suite-observation.json",
                    "identity": "sha256:" + observation_sha256,
                },
                "result": {
                    "accepted": True,
                    "suiteIdentity": "o1-lifecycle-coverage.controlled-v1",
                    "sourceRevision": source_revision,
                    "observationSha256": observation_sha256,
                    "replayVerified": True,
                },
                "validator": {
                    "kind": "o1-lifecycle-suite-validator-v1",
                    "version": 1,
                },
            }
            errors: list[str] = []

            with patch(
                "harness.task_validator_o1_lifecycle_suite.execute_scenario",
                executor,
            ):
                accepted = validate_evidence(evidence, "O1", root, errors)

        self.assertTrue(accepted)
        self.assertEqual(errors, [])


class O1LifecycleSuiteProbeTests(unittest.TestCase):
    def test_runs_twelve_distinct_registered_faults_through_one_local_seam(self) -> None:
        observed_scenarios: list[str] = []

        def executor(root: Path, source_revision: str, scenario: object) -> dict:
            del root, source_revision
            scenario_identity = getattr(scenario, "scenario_identity")
            expected_diagnostic = getattr(scenario, "expected_diagnostic")
            observed_scenarios.append(scenario_identity)
            return {
                "valid": False,
                "completionState": "in-progress",
                "errors": [expected_diagnostic],
                "probeCleanupVerified": True,
            }

        result = run_suite(Path.cwd(), "3" * 40, executor=executor)

        self.assertTrue(result["accepted"])
        self.assertTrue(result["cleanupVerified"])
        self.assertEqual(
            [item["sourceSliceIdentity"] for item in result["sourceSliceResults"]],
            SLICES,
        )
        self.assertEqual(len(set(observed_scenarios)), 12)
        self.assertEqual(
            result["fieldClaimsExcluded"],
            [
                "comparative-user-burden",
                "broad-real-world-effectiveness",
                "distinct-agent-equivalence",
            ],
        )

    def test_real_adapter_faults_and_cleans_an_isolated_checkout(self) -> None:
        root = Path(__file__).resolve().parents[2]
        program = json.loads(
            (root / "product" / "program.json").read_text(encoding="utf-8")
        )
        o1_increment = next(
            increment
            for increment in program["increments"]
            if increment["id"] == "increment.v12-o1-lifecycle-suite"
        )
        revision = o1_increment["taskRegistration"]["sourceRevision"]

        report = execute_scenario(root, revision, SCENARIOS[0])

        self.assertFalse(report["valid"])
        self.assertIn("program purpose is invalid", report["errors"])
        self.assertTrue(report["probeCleanupVerified"])
        self.assertFalse((root / ".tmp").exists())

    def test_real_adapter_never_removes_a_preexisting_temporary_boundary(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            marker = root / ".tmp" / "foreign.marker"
            marker.parent.mkdir()
            marker.write_text("foreign\n", encoding="utf-8")

            report = execute_scenario(root, "1" * 40, SCENARIOS[0])

            self.assertIsNone(report["valid"])
            self.assertFalse(report["probeCleanupVerified"])
            self.assertTrue(marker.is_file())


if __name__ == "__main__":
    unittest.main()
