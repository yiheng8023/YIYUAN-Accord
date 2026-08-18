from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from harness import task_validator_o2_codex_reference as base  # noqa: E402
from harness import task_validator_o2_codex_reference_permission_profile as subject  # noqa: E402


def permission_profile_registration_fixture() -> dict:
    registration = json.loads(
        (ROOT / "product/evidence/o2-codex-reference-registration.json").read_text(
            encoding="utf-8"
        )
    )
    values = registration["preRegistrationValues"]
    manifest_raw = (
        ROOT / subject.MANIFEST_LOCATOR
    ).read_bytes().replace(b"\r\n", b"\n")
    manifest_sha256 = hashlib.sha256(manifest_raw).hexdigest()
    stop_raw = (ROOT / subject.STOP_LOCATOR).read_bytes().replace(b"\r\n", b"\n")
    stop = json.loads(stop_raw)
    stop_sha256 = hashlib.sha256(stop_raw).hexdigest()
    manifest_revision = "a" * 40

    registration["id"] = "registration.o2-codex-reference-permission-profile.controlled-v2"
    registration["incrementId"] = subject.INCREMENT_ID
    registration["taskIdentity"] = "conformance-unit.public-v1:" + ("1" * 32)
    values["environmentAttributionBinding"].update(
        {
            "manifestLocator": subject.MANIFEST_LOCATOR,
            "manifestRevision": manifest_revision,
            "manifestSha256": manifest_sha256,
        }
    )
    values["scenarioIdentityAndClass"] = [
        {
            "scenarioIdentity": scenario.identity,
            "scenarioClass": scenario.scenario_class,
            "environmentIdentity": subject.CLEAN_ENVIRONMENT_IDENTITY,
        }
        for scenario in subject.SCENARIOS
    ]
    values["exactCodexVersionAndEnvironmentClass"] = {
        "cleanIsolated": {
            "environmentIdentity": subject.CLEAN_ENVIRONMENT_IDENTITY,
            "environmentClass": "observed-native-minimum",
            "codexVersion": "0.147.0",
            "codexHomeDisposition": "fresh-isolated-no-copied-user-state",
            "permissionProfile": ":workspace",
            "legacySandboxComposition": "absent",
            "configSha256": "ef474e72e420c9b3d49aaea1fc9eea15eac6de310ff3a95d7a931c70e220c9f9",
        },
        "userConfigured": {
            "environmentIdentity": subject.USER_ENVIRONMENT_IDENTITY,
            "environmentClass": "user-configured",
            "codexVersion": "0.147.0",
            "availabilityDisposition": "source-bound-unavailable-stop",
            "stopSourceIdentity": stop["sourceIdentity"],
            "stopArtifactSha256": stop_sha256,
        },
    }
    values["startingEnvironmentManifest"] = {
        "primaryEnvironmentIdentity": subject.CLEAN_ENVIRONMENT_IDENTITY,
        "primaryManifestLocator": subject.MANIFEST_LOCATOR,
        "primaryManifestRevision": manifest_revision,
        "primaryManifestSha256": manifest_sha256,
        "secondaryEnvironmentIdentity": subject.USER_ENVIRONMENT_IDENTITY,
        "secondaryAvailabilityDisposition": "source-bound-unavailable-stop",
        "secondaryStopSourceIdentity": stop["sourceIdentity"],
        "secondaryStopArtifactSha256": stop_sha256,
    }
    values["expectedNativeOrHarnessDelta"] = [
        {
            "scenarioIdentity": scenario.identity,
            "expectedDelta": scenario.expected_delta,
        }
        for scenario in subject.SCENARIOS
    ]
    values["authorityAndCleanupBoundary"] = {
        "installation": "exact-second-generation-grant-complete-install-only-after-registration",
        "account": "exact-isolated-device-auth-complete-before-manifest-capture",
        "authorityStop": "no-effect-before-grant-and-minimal-guidance-only",
        "rollback": "remove-exact-plugin-and-marketplace-restore-starting-state",
        "residue": "no-task-created-files-processes-config-or-credentials-after-cleanup",
    }
    scenario_validator = values["scenarioValidator"]
    scenario_validator["suiteIdentity"] = subject.SUITE_IDENTITY
    scenario_validator["validatorIdentity"] = subject.VALIDATOR_KIND
    for contract, scenario in zip(
        scenario_validator["scenarioContracts"], subject.SCENARIOS, strict=True
    ):
        contract["scenarioIdentity"] = scenario.identity
    registration["preMeasurementValidator"].update(
        {
            "kind": subject.VALIDATOR_KIND,
            "locator": subject.VALIDATOR_LOCATOR,
        }
    )
    return registration


def validate_registration_shape(registration: dict, errors: list[str]) -> bool:
    increment = {
        "id": subject.INCREMENT_ID,
        "taskRegistration": {"sourceRevision": "b" * 40},
    }
    with patch.object(subject, "_permission_profile_manifest_valid", return_value=True), patch.object(
        base, "_package_source_binding_valid", return_value=True
    ), patch.object(base, "_projection_builder_source_binding_valid", return_value=True):
        return subject.validate_registration(
            registration, increment, ("O2",), ROOT, errors
        )


class O2CodexPermissionProfileRegistrationTests(unittest.TestCase):
    def test_accepts_only_exact_second_generation_permission_profile_registration(self) -> None:
        errors: list[str] = []

        self.assertTrue(
            validate_registration_shape(permission_profile_registration_fixture(), errors),
            errors,
        )
        self.assertEqual(errors, [])

    def test_rejects_legacy_sandbox_composition(self) -> None:
        registration = permission_profile_registration_fixture()
        clean = registration["preRegistrationValues"][
            "exactCodexVersionAndEnvironmentClass"
        ]["cleanIsolated"]
        clean["permissionProfile"] = "workspace-write"
        clean["legacySandboxComposition"] = "present"
        errors: list[str] = []

        self.assertFalse(validate_registration_shape(registration, errors))
        self.assertIn(
            "O2 permission-profile environment classes are invalid", errors
        )

    def test_manifest_binds_physical_preinstall_state_and_pressure_probe(self) -> None:
        registration = permission_profile_registration_fixture()
        values = registration["preRegistrationValues"]
        raw = (ROOT / subject.MANIFEST_LOCATOR).read_bytes().replace(
            b"\r\n", b"\n"
        )
        with patch("harness.control._evidence_git", return_value=raw):
            self.assertTrue(
                subject._permission_profile_manifest_valid(
                    ROOT,
                    values["startingEnvironmentManifest"],
                    values["environmentAttributionBinding"],
                    values["exactCodexVersionAndEnvironmentClass"],
                )
            )

        drifted = json.loads(raw)
        drifted["configuration-layers-profiles-and-overrides"][
            "physicalPackageStateAtCapture"
        ] = "installed"
        drifted[
            "capture-time-source-identities-fingerprint-and-drift-check"
        ]["pressureProbe"] = "not-run"
        drifted_raw = (json.dumps(drifted, sort_keys=True) + "\n").encode()
        values["startingEnvironmentManifest"]["primaryManifestSha256"] = (
            hashlib.sha256(drifted_raw).hexdigest()
        )
        with patch("harness.control._evidence_git", return_value=drifted_raw):
            self.assertFalse(
                subject._permission_profile_manifest_valid(
                    ROOT,
                    values["startingEnvironmentManifest"],
                    values["environmentAttributionBinding"],
                    values["exactCodexVersionAndEnvironmentClass"],
                )
            )


class O2CodexPermissionProfileEvidenceTests(unittest.TestCase):
    def test_rejects_structurally_green_receipt_without_replayed_observation(self) -> None:
        observation_sha256 = "5" * 64
        errors: list[str] = []
        accepted = subject.validate_evidence(
            {
                "criterionIds": ["O2"],
                "incrementId": subject.INCREMENT_ID,
                "source": {
                    "kind": "controlled-live-codex-permission-profile-suite-observation",
                    "locator": subject.OBSERVATION_LOCATOR,
                    "identity": "sha256:" + observation_sha256,
                },
                "result": {
                    "accepted": True,
                    "suiteIdentity": subject.SUITE_IDENTITY,
                    "sourceRevision": "6" * 40,
                    "observationSha256": observation_sha256,
                    "hostAndFilesystemValidated": True,
                    "cleanupVerified": True,
                    "claimCeiling": "bounded-v1.2-live-codex-controlled-reference-application-only",
                },
            },
            "O2",
            ROOT,
            errors,
        )

        self.assertFalse(accepted)
        self.assertIn(
            "O2 permission-profile observation is missing or invalid", errors
        )


if __name__ == "__main__":
    unittest.main()
