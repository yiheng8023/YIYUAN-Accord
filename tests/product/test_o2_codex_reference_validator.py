from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import unittest


from harness.task_validator_o2_codex_reference import (
    SCENARIOS,
    validate_evidence,
    validate_registration,
)


PROFILE_SHA256 = "6b6f134ef49cd3cd161ef961ce2fe9e254f12d552f9e6d31f02c06009196d4f5"
PROTOCOL_SHA256 = "83dc62fc6f749ac18c0136ab066fc63cd667ed5e231dee8d5ebfb00889e78303"


def registration_fixture() -> dict:
    scenario_records = [
        {
            "scenarioIdentity": scenario.identity,
            "scenarioClass": scenario.scenario_class,
            "environmentIdentity": scenario.environment_identity,
        }
        for scenario in SCENARIOS
    ]
    values = {
        "normativeProfileIdentity": "harness-demand-to-outcome-v1.2-candidate.2",
        "cohortProtocolIdentity": "harness-controlled-conformance-v1.2-candidate.2",
        "profileSha256": PROFILE_SHA256,
        "cohortProtocolSha256": PROTOCOL_SHA256,
        "environmentAttributionBinding": {"fixture": "validated by the core seam"},
        "scenarioIdentityAndClass": scenario_records,
        "exactCodexVersionAndEnvironmentClass": {
            "cleanIsolated": {
                "environmentIdentity": "codex-env.clean-isolated-v1",
                "environmentClass": "observed-native-minimum",
                "codexVersion": "0.147.0",
                "codexHomeDisposition": "fresh-isolated-no-copied-user-state",
            },
            "userConfigured": {
                "environmentIdentity": "codex-env.user-configured-v1",
                "environmentClass": "user-configured",
                "codexVersion": "0.147.0",
                "availabilityDisposition": "declared-live-environment",
            },
        },
        "startingEnvironmentManifest": {
            "primaryEnvironmentIdentity": "codex-env.clean-isolated-v1",
            "primaryManifestLocator": "product/evidence/environment-manifests/o2-codex-clean-isolated.json",
            "secondaryEnvironmentIdentity": "codex-env.user-configured-v1",
            "secondaryManifestLocator": "product/evidence/environment-manifests/o2-codex-user-configured.json",
            "secondaryManifestRevision": "1" * 40,
            "secondaryManifestSha256": "2" * 64,
        },
        "packageAndActivationIdentity": {
            "pluginId": "agent-autonomy-harness@agent-autonomy-harness",
            "packageLocator": "adapters/agent-autonomy-harness-codex",
            "packageRevision": "3" * 40,
            "packageSha256": "4" * 64,
            "activationMechanism": "codex-plugin-add-local-marketplace",
            "ordinaryGoalEntry": "implicit-skill-no-explicit-route-syntax",
        },
        "expectedNativeOrHarnessDelta": [
            {
                "scenarioIdentity": scenario.identity,
                "expectedDelta": scenario.expected_delta,
            }
            for scenario in SCENARIOS
        ],
        "authorityAndCleanupBoundary": {
            "installation": "exact-human-grant-required-before-installation",
            "account": "exact-human-grant-required-before-device-auth",
            "authorityStop": "no-effect-before-grant-and-minimal-guidance-only",
            "rollback": "remove-exact-plugin-and-marketplace-restore-starting-state",
            "residue": "no-task-created-files-processes-config-or-credentials-after-cleanup",
        },
        "scenarioValidator": {
            "suiteIdentity": "o2-codex-reference.controlled-v1",
            "validatorIdentity": "o2-codex-reference-validator-v1",
            "rawObservationFormat": "content-addressed-codex-jsonl-and-filesystem-manifests-v1",
        },
    }
    return {
        "incrementId": "increment.v12-o2-codex-reference",
        "criterionIds": ["O2"],
        "preRegistrationValues": values,
        "preMeasurementValidator": {
            "kind": "o2-codex-reference-validator-v1",
            "version": 1,
            "locator": "harness/task_validator_o2_codex_reference.py",
        },
    }


class O2CodexReferenceRegistrationTests(unittest.TestCase):
    def test_accepts_exact_four_class_live_codex_contract(self) -> None:
        errors: list[str] = []

        accepted = validate_registration(
            registration_fixture(),
            {"id": "increment.v12-o2-codex-reference"},
            ("O2",),
            Path.cwd(),
            errors,
        )

        self.assertTrue(accepted)
        self.assertEqual(errors, [])

    def test_rejects_missing_duplicated_or_reclassified_scenario(self) -> None:
        mutations = {
            "missing": lambda records: records.pop(),
            "duplicated": lambda records: records.__setitem__(3, deepcopy(records[2])),
            "reclassified": lambda records: records[0].update(
                {"scenarioClass": "nontrivial-goal-intake"}
            ),
        }
        for name, mutate in mutations.items():
            with self.subTest(name=name):
                registration = registration_fixture()
                records = registration["preRegistrationValues"][
                    "scenarioIdentityAndClass"
                ]
                mutate(records)
                errors: list[str] = []

                accepted = validate_registration(
                    registration,
                    {"id": "increment.v12-o2-codex-reference"},
                    ("O2",),
                    Path.cwd(),
                    errors,
                )

                self.assertFalse(accepted)
                self.assertIn(
                    "O2 Codex reference suite must bind the four scenario classes exactly once",
                    errors,
                )


class O2CodexReferenceEvidenceTests(unittest.TestCase):
    def test_rejects_bare_accepted_receipt_without_host_and_filesystem_evidence(self) -> None:
        errors: list[str] = []

        accepted = validate_evidence(
            {
                "schema": 1,
                "criterionIds": ["O2"],
                "incrementId": "increment.v12-o2-codex-reference",
                "source": {"kind": "controlled-live-codex-reference-suite"},
                "result": {"accepted": True},
            },
            "O2",
            Path.cwd(),
            errors,
        )

        self.assertFalse(accepted)
        self.assertIn(
            "O2 Codex reference evidence requires content-addressed live host and filesystem observations",
            errors,
        )

    def test_rejects_structurally_green_receipt_when_observation_is_missing(self) -> None:
        observation_sha256 = "5" * 64
        errors: list[str] = []

        accepted = validate_evidence(
            {
                "schema": 1,
                "criterionIds": ["O2"],
                "incrementId": "increment.v12-o2-codex-reference",
                "source": {
                    "kind": "controlled-live-codex-reference-suite-observation",
                    "locator": "product/evidence/o2-codex-reference-observation.json",
                    "identity": "sha256:" + observation_sha256,
                },
                "result": {
                    "accepted": True,
                    "suiteIdentity": "o2-codex-reference.controlled-v1",
                    "sourceRevision": "6" * 40,
                    "observationSha256": observation_sha256,
                    "hostAndFilesystemValidated": True,
                    "cleanupVerified": True,
                    "claimCeiling": "bounded-v1.2-live-codex-controlled-reference-application-only",
                },
            },
            "O2",
            Path.cwd(),
            errors,
        )

        self.assertFalse(accepted)
        self.assertIn("O2 Codex reference observation failed closed", errors)


if __name__ == "__main__":
    unittest.main()
