"""Task-specific validator for the v1.2 Codex reference scenario suite.

This module is not a plugin manager, model router, host runtime, or reusable
receipt framework.  It owns only the pre-registered O2 controlled suite and
its later content-addressed Codex-native and filesystem evidence.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import re
from typing import Any


INCREMENT_ID = "increment.v12-o2-codex-reference"
VALIDATOR_KIND = "o2-codex-reference-validator-v1"
VALIDATOR_LOCATOR = "harness/task_validator_o2_codex_reference.py"
SUITE_IDENTITY = "o2-codex-reference.controlled-v1"
PROFILE_IDENTITY = "harness-demand-to-outcome-v1.2-candidate.2"
PROTOCOL_IDENTITY = "harness-controlled-conformance-v1.2-candidate.2"
PROFILE_SHA256 = "6b6f134ef49cd3cd161ef961ce2fe9e254f12d552f9e6d31f02c06009196d4f5"
PROTOCOL_SHA256 = "83dc62fc6f749ac18c0136ab066fc63cd667ed5e231dee8d5ebfb00889e78303"
EXPECTED_PRE_REGISTRATION_FIELDS = {
    "normativeProfileIdentity",
    "cohortProtocolIdentity",
    "profileSha256",
    "cohortProtocolSha256",
    "environmentAttributionBinding",
    "scenarioIdentityAndClass",
    "exactCodexVersionAndEnvironmentClass",
    "startingEnvironmentManifest",
    "packageAndActivationIdentity",
    "expectedNativeOrHarnessDelta",
    "authorityAndCleanupBoundary",
    "scenarioValidator",
}


@dataclass(frozen=True)
class Scenario:
    identity: str
    scenario_class: str
    environment_identity: str
    expected_delta: str


SCENARIOS = (
    Scenario(
        "o2-codex-reference.simple-native-no-op",
        "simple-native-no-op",
        "codex-env.clean-isolated-v1",
        "native-route-no-harness-ceremony-or-side-effect",
    ),
    Scenario(
        "o2-codex-reference.nontrivial-goal-intake",
        "nontrivial-goal-intake",
        "codex-env.clean-isolated-v1",
        "implicit-skill-minimum-goal-to-route-projection",
    ),
    Scenario(
        "o2-codex-reference.human-authority-boundary",
        "human-authority-boundary",
        "codex-env.clean-isolated-v1",
        "stop-before-grant-minimal-guidance-and-verified-resume",
    ),
    Scenario(
        "o2-codex-reference.failure-recovery-and-cleanup",
        "failure-recovery-and-cleanup",
        "codex-env.user-configured-v1",
        "bounded-recovery-or-honest-stop-then-exact-removal",
    ),
)


def _error(errors: list[str], message: str) -> None:
    if message not in errors:
        errors.append(message)


def _sha256(value: Any) -> bool:
    return isinstance(value, str) and re.fullmatch(r"[0-9a-f]{64}", value) is not None


def _revision(value: Any) -> bool:
    return isinstance(value, str) and re.fullmatch(r"[0-9a-f]{40}", value) is not None


def _codex_version(value: Any) -> bool:
    return (
        isinstance(value, str)
        and re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+(?:[-+][0-9A-Za-z.-]+)?", value)
        is not None
    )


def _scenario_records_valid(value: Any) -> bool:
    expected = [
        {
            "scenarioIdentity": scenario.identity,
            "scenarioClass": scenario.scenario_class,
            "environmentIdentity": scenario.environment_identity,
        }
        for scenario in SCENARIOS
    ]
    return value == expected


def _environment_records_valid(value: Any) -> bool:
    if not isinstance(value, dict) or set(value) != {"cleanIsolated", "userConfigured"}:
        return False
    clean = value.get("cleanIsolated")
    configured = value.get("userConfigured")
    if not isinstance(clean, dict) or set(clean) != {
        "environmentIdentity",
        "environmentClass",
        "codexVersion",
        "codexHomeDisposition",
    }:
        return False
    if clean != {
        "environmentIdentity": "codex-env.clean-isolated-v1",
        "environmentClass": "observed-native-minimum",
        "codexVersion": clean.get("codexVersion"),
        "codexHomeDisposition": "fresh-isolated-no-copied-user-state",
    } or not _codex_version(clean.get("codexVersion")):
        return False
    if not isinstance(configured, dict) or set(configured) != {
        "environmentIdentity",
        "environmentClass",
        "codexVersion",
        "availabilityDisposition",
    }:
        return False
    return (
        configured.get("environmentIdentity") == "codex-env.user-configured-v1"
        and configured.get("environmentClass") == "user-configured"
        and _codex_version(configured.get("codexVersion"))
        and configured.get("availabilityDisposition")
        in {"declared-live-environment", "source-bound-unavailable-stop"}
    )


def _starting_manifests_valid(value: Any) -> bool:
    return (
        isinstance(value, dict)
        and set(value)
        == {
            "primaryEnvironmentIdentity",
            "primaryManifestLocator",
            "secondaryEnvironmentIdentity",
            "secondaryManifestLocator",
            "secondaryManifestRevision",
            "secondaryManifestSha256",
        }
        and value.get("primaryEnvironmentIdentity") == "codex-env.clean-isolated-v1"
        and value.get("primaryManifestLocator")
        == "product/evidence/environment-manifests/o2-codex-clean-isolated.json"
        and value.get("secondaryEnvironmentIdentity")
        == "codex-env.user-configured-v1"
        and value.get("secondaryManifestLocator")
        == "product/evidence/environment-manifests/o2-codex-user-configured.json"
        and _revision(value.get("secondaryManifestRevision"))
        and _sha256(value.get("secondaryManifestSha256"))
    )


def _package_binding_valid(value: Any) -> bool:
    return (
        isinstance(value, dict)
        and set(value)
        == {
            "pluginId",
            "packageLocator",
            "packageRevision",
            "packageSha256",
            "activationMechanism",
            "ordinaryGoalEntry",
        }
        and value.get("pluginId")
        == "agent-autonomy-harness@agent-autonomy-harness"
        and value.get("packageLocator")
        == "adapters/agent-autonomy-harness-codex"
        and _revision(value.get("packageRevision"))
        and _sha256(value.get("packageSha256"))
        and value.get("activationMechanism")
        == "codex-plugin-add-local-marketplace"
        and value.get("ordinaryGoalEntry")
        == "implicit-skill-no-explicit-route-syntax"
    )


def _expected_delta_valid(value: Any) -> bool:
    return value == [
        {
            "scenarioIdentity": scenario.identity,
            "expectedDelta": scenario.expected_delta,
        }
        for scenario in SCENARIOS
    ]


def validate_registration(
    registration: dict[str, Any],
    increment: dict[str, Any],
    mapped_outcomes: tuple[str, ...],
    root: Path,
    errors: list[str],
) -> bool:
    """Validate the exact O2 suite contract before installation or execution."""

    before = len(errors)
    values = registration.get("preRegistrationValues")
    if (
        increment.get("id") != INCREMENT_ID
        or registration.get("incrementId") != INCREMENT_ID
        or mapped_outcomes != ("O2",)
        or registration.get("criterionIds") != ["O2"]
        or not isinstance(values, dict)
        or set(values) != EXPECTED_PRE_REGISTRATION_FIELDS
    ):
        _error(errors, "O2 Codex reference registration identity is invalid")
        return False
    if (
        values.get("normativeProfileIdentity") != PROFILE_IDENTITY
        or values.get("cohortProtocolIdentity") != PROTOCOL_IDENTITY
        or values.get("profileSha256") != PROFILE_SHA256
        or values.get("cohortProtocolSha256") != PROTOCOL_SHA256
    ):
        _error(errors, "O2 Codex reference profile binding is invalid")
    if not _scenario_records_valid(values.get("scenarioIdentityAndClass")):
        _error(errors, "O2 Codex reference suite must bind the four scenario classes exactly once")
    if not _environment_records_valid(
        values.get("exactCodexVersionAndEnvironmentClass")
    ):
        _error(errors, "O2 Codex reference environment classes are invalid")
    if not _starting_manifests_valid(values.get("startingEnvironmentManifest")):
        _error(errors, "O2 Codex reference starting manifests are invalid")
    if not _package_binding_valid(values.get("packageAndActivationIdentity")):
        _error(errors, "O2 Codex reference package binding is invalid")
    if not _expected_delta_valid(values.get("expectedNativeOrHarnessDelta")):
        _error(errors, "O2 Codex reference expected deltas are invalid")
    if values.get("authorityAndCleanupBoundary") != {
        "installation": "exact-human-grant-required-before-installation",
        "account": "exact-human-grant-required-before-device-auth",
        "authorityStop": "no-effect-before-grant-and-minimal-guidance-only",
        "rollback": "remove-exact-plugin-and-marketplace-restore-starting-state",
        "residue": "no-task-created-files-processes-config-or-credentials-after-cleanup",
    }:
        _error(errors, "O2 Codex reference authority and cleanup boundary is invalid")
    if values.get("scenarioValidator") != {
        "suiteIdentity": SUITE_IDENTITY,
        "validatorIdentity": VALIDATOR_KIND,
        "rawObservationFormat": "content-addressed-codex-jsonl-and-filesystem-manifests-v1",
    }:
        _error(errors, "O2 Codex reference scenario validator binding is invalid")
    validator = registration.get("preMeasurementValidator")
    if not isinstance(validator, dict) or (
        validator.get("kind") != VALIDATOR_KIND
        or validator.get("version") != 1
        or validator.get("locator") != VALIDATOR_LOCATOR
    ):
        _error(errors, "O2 Codex reference validator binding is invalid")
    return len(errors) == before


def validate_evidence(
    document: dict[str, Any],
    criterion_id: str,
    root: Path,
    errors: list[str],
) -> bool:
    """Validate content-addressed live Codex and filesystem observations."""

    before = len(errors)
    source = document.get("source")
    result = document.get("result")
    if (
        criterion_id != "O2"
        or document.get("criterionIds") != ["O2"]
        or document.get("incrementId") != INCREMENT_ID
        or not isinstance(source, dict)
        or source.get("kind")
        != "controlled-live-codex-reference-suite-observation"
        or source.get("locator")
        != "product/evidence/o2-codex-reference-observation.json"
        or not isinstance(source.get("identity"), str)
        or re.fullmatch(r"sha256:[0-9a-f]{64}", source["identity"]) is None
        or not isinstance(result, dict)
        or set(result)
        != {
            "accepted",
            "suiteIdentity",
            "sourceRevision",
            "observationSha256",
            "hostAndFilesystemValidated",
            "cleanupVerified",
            "claimCeiling",
        }
        or result.get("accepted") is not True
        or result.get("suiteIdentity") != SUITE_IDENTITY
        or not _revision(result.get("sourceRevision"))
        or not _sha256(result.get("observationSha256"))
        or source.get("identity") != "sha256:" + result.get("observationSha256", "")
        or result.get("hostAndFilesystemValidated") is not True
        or result.get("cleanupVerified") is not True
        or result.get("claimCeiling")
        != "bounded-v1.2-live-codex-controlled-reference-application-only"
    ):
        _error(
            errors,
            "O2 Codex reference evidence requires content-addressed live host and filesystem observations",
        )
        return False
    try:
        observation_path = root / "product" / "evidence" / "o2-codex-reference-observation.json"
        observation_raw = observation_path.read_bytes()
        if len(observation_raw) > 1_048_576:
            raise ValueError("observation exceeds byte limit")
        if hashlib.sha256(observation_raw).hexdigest() != result["observationSha256"]:
            raise ValueError("observation digest mismatch")

        def reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
            value: dict[str, Any] = {}
            for key, item in pairs:
                if key in value:
                    raise ValueError("duplicate observation key")
                value[key] = item
            return value

        observation = json.loads(
            observation_raw.decode("utf-8"),
            object_pairs_hook=reject_duplicate_keys,
            parse_constant=lambda _: (_ for _ in ()).throw(
                ValueError("non-finite observation value")
            ),
        )
        if not isinstance(observation, dict):
            raise ValueError("observation must be an object")
    except (json.JSONDecodeError, OSError, TypeError, UnicodeError, ValueError):
        _error(errors, "O2 Codex reference observation failed closed")
        return False

    _error(
        errors,
        "O2 Codex reference live observation replay is not materialized",
    )
    return len(errors) == before


__all__ = [
    "INCREMENT_ID",
    "SCENARIOS",
    "VALIDATOR_KIND",
    "VALIDATOR_LOCATOR",
    "validate_evidence",
    "validate_registration",
]
