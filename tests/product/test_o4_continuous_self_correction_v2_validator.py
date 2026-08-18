from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from harness import task_validator_o4_continuous_self_correction as v1
from harness import task_validator_o4_continuous_self_correction_v2 as validator
from tests.product.test_o4_continuous_self_correction_validator import (
    SOURCE_CARRIER_ID,
    SOURCE_REVISION,
    raw_compaction_observations,
)


def registration_values() -> dict[str, object]:
    return {
        "normativeProfileIdentity": "bound-by-core",
        "cohortProtocolIdentity": "bound-by-core",
        "profileSha256": "b" * 64,
        "cohortProtocolSha256": "c" * 64,
        "environmentAttributionBinding": "bound-by-core",
        "counterexampleIdentityAndSource": validator.COUNTEREXAMPLE_SOURCES,
        "startingAuthorityGoalAndCarrierState": {
            "registrationRevisionRule": v1.REGISTRATION_REVISION_RULE,
            "measurementBaselineRevisionRule": v1.MEASUREMENT_BASELINE_REVISION_RULE,
            "authorityPaths": [
                "product/constitution.json",
                "product/program.json",
                "product/acceptance.json",
            ],
            "goalBoundary": (
                "registered-o4-controlled-carrier-goal-under-current-v1.2-acceptance"
            ),
            "controlledGoalArtifact": v1.CARRIER_GOAL_BINDING,
            "carrierState": {
                "repository": "single-main-checkout-clean-at-scenario-start",
                "sourceConversation": "native-active-goal-observed-before-compaction-or-transition-and-cleared-only-after-destination-verification",
                "destinationConversation": "fresh-thread-started-with-zero-inherited-turns-then-exact-active-goal-installed-from-this-registration",
                "capacitySignal": "reliable-risk-or-explicit-unknown-rule-only",
            },
        },
        "injectedOrObservedFailure": validator.FAILURE_BINDINGS,
        "expectedDetectionAndCorrection": validator.CORRECTION_BINDINGS,
        "transitionAndCleanupBoundary": v1.TRANSITION_AND_CLEANUP_BOUNDARY,
        "scenarioValidator": {
            "suiteIdentity": validator.SUITE_IDENTITY,
            "scenarioIdentities": list(validator.SCENARIO_IDENTITIES),
            "validatorIdentity": validator.VALIDATOR_KIND,
            "validatorLocator": validator.VALIDATOR_LOCATOR,
            "hostProjectionBuilder": (
                f"{validator.VALIDATOR_LOCATOR}:project_raw_carrier_observations"
            ),
            "codexSourceBinding": v1.CODEX_SOURCE_BINDING,
            "controlledGoalArtifact": v1.CARRIER_GOAL_BINDING,
            "receiptOnlyAccepted": False,
        },
    }


def run_git(root: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", *args],
        cwd=root,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=30,
        text=True,
    )
    return completed.stdout.strip()


def write_json(path: Path, value: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )


class O4ContinuousSelfCorrectionV2ValidatorTests(unittest.TestCase):
    def test_first_generation_validator_bytes_remain_frozen(self) -> None:
        raw = Path(v1.VALIDATOR_LOCATOR).read_bytes()
        self.assertEqual(
            hashlib.sha256(raw).hexdigest(),
            "4e08aed6dd4070016e910aac31192af2ff2c78cf2b779da2a04acada20fd8aa1",
        )

    def test_registration_is_generation_isolated(self) -> None:
        increment = {
            "id": validator.INCREMENT_ID,
            "taskRegistration": {
                "locator": validator.REGISTRATION_LOCATOR,
                "sourceRevision": SOURCE_REVISION,
            },
        }
        registration = {
            "incrementId": validator.INCREMENT_ID,
            "criterionIds": ["O4"],
            "preRegistrationValues": registration_values(),
            "preMeasurementValidator": {
                "kind": validator.VALIDATOR_KIND,
                "version": 1,
                "locator": validator.VALIDATOR_LOCATOR,
            },
        }
        errors: list[str] = []
        with patch.object(v1, "_goal_artifact_committed", return_value=True):
            self.assertTrue(
                validator.validate_registration(
                    registration, increment, ("O4",), Path("."), errors
                ),
                errors,
            )

        crossed = deepcopy(registration)
        crossed["preMeasurementValidator"]["kind"] = v1.VALIDATOR_KIND
        errors = []
        with patch.object(v1, "_goal_artifact_committed", return_value=True):
            self.assertFalse(
                validator.validate_registration(
                    crossed, increment, ("O4",), Path("."), errors
                )
            )
        self.assertIn(
            "O4 second-generation pre-measurement validator is invalid", errors
        )

        wrong_locator = deepcopy(increment)
        wrong_locator["taskRegistration"]["locator"] = (
            "product/evidence/o4-continuous-self-correction-registration.json"
        )
        errors = []
        with patch.object(v1, "_goal_artifact_committed", return_value=True):
            self.assertFalse(
                validator.validate_registration(
                    registration, wrong_locator, ("O4",), Path("."), errors
                )
            )
        self.assertIn("O4 second-generation registration identity is invalid", errors)

    def test_corrected_diagnostic_matches_the_observable_generic_gate(self) -> None:
        self.assertEqual(
            validator.FAULT_SCENARIOS[2].expected_diagnostic,
            "criterion O1 evidence shape is invalid: "
            "product/evidence/o1-lifecycle-suite-accepted.json",
        )
        self.assertNotEqual(
            validator.FAULT_SCENARIOS[2].expected_diagnostic,
            v1.FAULT_SCENARIOS[2].expected_diagnostic,
        )

    def test_raw_projection_rejects_cross_generation_verifier_state(self) -> None:
        raw = raw_compaction_observations()
        with self.assertRaisesRegex(ValueError, "wrong O4 generation"):
            validator.project_raw_carrier_observations(
                v1.CARRIER_SCENARIO_IDENTITIES[0],
                raw,
                source_carrier_id=SOURCE_CARRIER_ID,
                expected_head=SOURCE_REVISION,
            )
        raw[8]["report"]["activeIncrement"] = validator.INCREMENT_ID
        projection = validator.project_raw_carrier_observations(
            v1.CARRIER_SCENARIO_IDENTITIES[0],
            raw,
            source_carrier_id=SOURCE_CARRIER_ID,
            expected_head=SOURCE_REVISION,
        )
        self.assertEqual(0, projection["retainedPrivateFieldCount"])

    def test_measurement_baseline_requires_v2_program_only_activation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            run_git(root, "init", "--quiet", "--initial-branch=main")
            run_git(root, "config", "user.name", "O4 V2 Fixture")
            run_git(root, "config", "user.email", "o4-v2@example.invalid")
            run_git(root, "config", "commit.gpgsign", "false")
            run_git(root, "config", "core.autocrlf", "false")
            write_json(root / "product/program.json", {"status": "ready"})
            write_json(root / validator.REGISTRATION_LOCATOR, {"schema": 1})
            run_git(
                root,
                "add",
                "product/program.json",
                validator.REGISTRATION_LOCATOR,
            )
            run_git(root, "commit", "--quiet", "--no-gpg-sign", "-m", "Register")
            registration_revision = run_git(root, "rev-parse", "HEAD")
            active = {
                "status": "active",
                "activeIncrementId": validator.INCREMENT_ID,
                "increments": [
                    {
                        "id": validator.INCREMENT_ID,
                        "state": "active",
                        "taskRegistration": {
                            "locator": validator.REGISTRATION_LOCATOR,
                            "sourceRevision": registration_revision,
                        },
                        "workItems": [{"id": "work.o4-v2", "state": "active"}],
                    }
                ],
            }
            write_json(root / "product/program.json", active)
            run_git(root, "add", "product/program.json")
            run_git(root, "commit", "--quiet", "--no-gpg-sign", "-m", "Activate")
            baseline = run_git(root, "rev-parse", "HEAD")
            self.assertTrue(validator._measurement_baseline_valid(root, baseline))

    def test_fault_suite_requires_every_v2_floor(self) -> None:
        def passing(
            root: Path,
            source_revision: str,
            scenario: v1.FaultScenario,
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

        result = validator.run_fault_suite(
            Path("."), SOURCE_REVISION, executor=passing
        )
        self.assertEqual(result["suiteIdentity"], validator.SUITE_IDENTITY)
        self.assertTrue(result["allFaultControlsObserved"])


if __name__ == "__main__":
    unittest.main()
