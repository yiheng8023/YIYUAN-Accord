"""Task-specific validator for the second native-Windows O2 Codex suite.

The first O2 generation remains append-only stopped counterevidence.  This
module admits only the separately captured built-in ``:workspace`` permission
profile generation and reuses the already bounded projection primitives; it is
not a generic receipt framework, sandbox, plugin manager, or Codex runtime.
"""

from __future__ import annotations

from copy import deepcopy
import hashlib
from pathlib import Path
from typing import Any

from . import task_validator_o2_codex_reference as base


INCREMENT_ID = "increment.v12-o2-codex-reference-permission-profile"
VALIDATOR_KIND = "o2-codex-reference-permission-profile-validator-v1"
VALIDATOR_LOCATOR = "harness/task_validator_o2_codex_reference_permission_profile.py"
SUITE_IDENTITY = "o2-codex-reference-permission-profile.controlled-v2"
REGISTRATION_LOCATOR = (
    "product/evidence/o2-codex-reference-permission-profile-registration.json"
)
OBSERVATION_LOCATOR = (
    "product/evidence/o2-codex-reference-permission-profile-observation.json"
)
MANIFEST_LOCATOR = (
    "product/evidence/environment-manifests/"
    "o2-codex-clean-isolated-permission-profile.json"
)
STOP_LOCATOR = (
    "product/evidence/o2-codex-reference-artifacts/"
    "user-configured-unavailable-stop-permission-profile.json"
)
CLEAN_ENVIRONMENT_IDENTITY = "codex-env.clean-isolated-permission-profile-v2"
USER_ENVIRONMENT_IDENTITY = "codex-env.user-configured-permission-profile-v2"
PROFILE_IDENTITY = base.PROFILE_IDENTITY
PROTOCOL_IDENTITY = base.PROTOCOL_IDENTITY
PROFILE_SHA256 = base.PROFILE_SHA256
PROTOCOL_SHA256 = base.PROTOCOL_SHA256
FIELD_CLAIM_EXCLUSIONS = base.FIELD_CLAIM_EXCLUSIONS
EXPECTED_PRE_REGISTRATION_FIELDS = base.EXPECTED_PRE_REGISTRATION_FIELDS
REGISTRATION_BINDING_FIELDS = base.REGISTRATION_BINDING_FIELDS


SCENARIOS = tuple(
    base.Scenario(
        "o2-codex-reference-permission-profile."
        + scenario.identity.removeprefix("o2-codex-reference."),
        scenario.scenario_class,
        CLEAN_ENVIRONMENT_IDENTITY,
        scenario.expected_delta,
    )
    for scenario in base.SCENARIOS
)
_V2_TO_V1_SCENARIO = {
    current.identity: historical.identity
    for current, historical in zip(SCENARIOS, base.SCENARIOS, strict=True)
}


def _error(errors: list[str], message: str) -> None:
    if message not in errors:
        errors.append(message)


def _scenario_records_valid(value: Any) -> bool:
    return value == [
        {
            "scenarioIdentity": scenario.identity,
            "scenarioClass": scenario.scenario_class,
            "environmentIdentity": scenario.environment_identity,
        }
        for scenario in SCENARIOS
    ]


def _environment_records_valid(value: Any) -> bool:
    if not isinstance(value, dict) or set(value) != {
        "cleanIsolated",
        "userConfigured",
    }:
        return False
    clean = value.get("cleanIsolated")
    configured = value.get("userConfigured")
    return (
        isinstance(clean, dict)
        and set(clean)
        == {
            "environmentIdentity",
            "environmentClass",
            "codexVersion",
            "codexHomeDisposition",
            "permissionProfile",
            "legacySandboxComposition",
            "configSha256",
        }
        and clean.get("environmentIdentity") == CLEAN_ENVIRONMENT_IDENTITY
        and clean.get("environmentClass") == "observed-native-minimum"
        and base._codex_version(clean.get("codexVersion"))
        and clean.get("codexHomeDisposition")
        == "fresh-isolated-no-copied-user-state"
        and clean.get("permissionProfile") == ":workspace"
        and clean.get("legacySandboxComposition") == "absent"
        and base._sha256(clean.get("configSha256"))
        and isinstance(configured, dict)
        and set(configured)
        == {
            "environmentIdentity",
            "environmentClass",
            "codexVersion",
            "availabilityDisposition",
            "stopSourceIdentity",
            "stopArtifactSha256",
        }
        and configured.get("environmentIdentity") == USER_ENVIRONMENT_IDENTITY
        and configured.get("environmentClass") == "user-configured"
        and base._codex_version(configured.get("codexVersion"))
        and configured.get("availabilityDisposition")
        == "source-bound-unavailable-stop"
        and isinstance(configured.get("stopSourceIdentity"), str)
        and configured["stopSourceIdentity"].startswith("public-decision:")
        and base._sha256(configured.get("stopArtifactSha256"))
    )


def _starting_manifests_valid(value: Any) -> bool:
    return (
        isinstance(value, dict)
        and set(value)
        == {
            "primaryEnvironmentIdentity",
            "primaryManifestLocator",
            "primaryManifestRevision",
            "primaryManifestSha256",
            "secondaryEnvironmentIdentity",
            "secondaryAvailabilityDisposition",
            "secondaryStopSourceIdentity",
            "secondaryStopArtifactSha256",
        }
        and value.get("primaryEnvironmentIdentity") == CLEAN_ENVIRONMENT_IDENTITY
        and value.get("primaryManifestLocator") == MANIFEST_LOCATOR
        and base._revision(value.get("primaryManifestRevision"))
        and base._sha256(value.get("primaryManifestSha256"))
        and value.get("secondaryEnvironmentIdentity") == USER_ENVIRONMENT_IDENTITY
        and value.get("secondaryAvailabilityDisposition")
        == "source-bound-unavailable-stop"
        and isinstance(value.get("secondaryStopSourceIdentity"), str)
        and value["secondaryStopSourceIdentity"].startswith("public-decision:")
        and base._sha256(value.get("secondaryStopArtifactSha256"))
    )


def _permission_profile_manifest_valid(
    root: Path,
    manifests: Any,
    environment_binding: Any,
    environments: Any,
) -> bool:
    if not (
        _starting_manifests_valid(manifests)
        and isinstance(environment_binding, dict)
        and isinstance(environments, dict)
    ):
        return False
    revision = manifests["primaryManifestRevision"]
    expected_sha256 = manifests["primaryManifestSha256"]
    try:
        from harness.control import _evidence_git

        raw = _evidence_git(root, "show", f"{revision}:{MANIFEST_LOCATOR}")
        if (
            raw is None
            or hashlib.sha256(raw).hexdigest() != expected_sha256
            or any(marker in raw.decode("utf-8").lower() for marker in base.PRIVATE_TEXT_MARKERS)
        ):
            return False
        manifest = base._strict_json_object(raw)
        configuration = manifest["configuration-layers-profiles-and-overrides"]
        surfaces = manifest["rules-skills-plugins-apps-mcp-hooks-memory-and-managers"]
        capture = manifest["capture-time-source-identities-fingerprint-and-drift-check"]
        repository = manifest["cwd-repository-and-project-instruction-chain"]
        delta = manifest["exact-harness-package-activation-and-exposure-delta"]
        account = manifest["account-managed-and-administrator-requirements-presence"]
        clean = environments["cleanIsolated"]
    except (KeyError, OSError, RecursionError, TypeError, UnicodeError, ValueError):
        return False
    return (
        manifest.get("environmentClass") == "observed-native-minimum"
        and manifest.get("treatmentArm") == "with-exact-harness"
        and manifest.get("host-client-and-version", {}).get("codexCli")
        == clean.get("codexVersion")
        and configuration.get("codexHome")
        == "fresh-isolated-no-copied-user-state"
        and configuration.get("configToml")
        == "default_permissions=:workspace;approval_policy=never"
        and configuration.get("configTomlSha256") == clean.get("configSha256")
        and configuration.get("profiles") == "official-built-in-:workspace"
        and configuration.get("legacySandboxSettings")
        == "absent-no-sandbox_mode-no-sandbox_workspace_write-no---sandbox"
        and configuration.get("physicalPackageStateAtCapture") == "not-installed"
        and configuration.get("explicitOverrides") == "none-at-capture"
        and surfaces.get("plugins")
        == "native-plugin-list-reported-installed-empty-and-available-empty-at-pre-activation-capture"
        and surfaces.get("marketplaces")
        == "native-marketplace-list-reported-empty-at-pre-activation-capture"
        and surfaces.get("userGlobalSurfaces") == "not-copied-not-read-not-loaded"
        and capture.get("permissionSource")
        == "https://learn.chatgpt.com/docs/permissions"
        and capture.get("permissionSourceResolvedAt") == "2026-08-18"
        and capture.get("permissionProfile") == ":workspace"
        and capture.get("pressureProbe")
        == "32-cycles-four-workers-32-in-root-allowed-32-out-of-root-denied-zero-residue"
        and repository.get("repositoryWorktreeAtCapture") == "clean"
        and base._revision(repository.get("repositoryRevisionAtCapture"))
        and account.get("account")
        == "official-device-auth-present-in-private-isolated-state-not-publicly-committed"
        and delta == environment_binding.get("harnessActivationDelta")
    )


def _expected_delta_valid(value: Any) -> bool:
    return value == [
        {
            "scenarioIdentity": scenario.identity,
            "expectedDelta": scenario.expected_delta,
        }
        for scenario in SCENARIOS
    ]


def _scenario_validator_binding_valid(value: Any) -> bool:
    if not isinstance(value, dict):
        return False
    if (
        value.get("suiteIdentity") != SUITE_IDENTITY
        or value.get("validatorIdentity") != VALIDATOR_KIND
    ):
        return False
    translated = deepcopy(value)
    translated["suiteIdentity"] = base.SUITE_IDENTITY
    translated["validatorIdentity"] = base.VALIDATOR_KIND
    contracts = translated.get("scenarioContracts")
    if not isinstance(contracts, list) or len(contracts) != len(SCENARIOS):
        return False
    try:
        for contract in contracts:
            identity = contract["scenarioIdentity"]
            contract["scenarioIdentity"] = _V2_TO_V1_SCENARIO[identity]
    except (KeyError, TypeError):
        return False
    return base._scenario_validator_binding_valid(translated)


def _stop_artifact_valid(
    root: Path,
    binding: Any,
    configured_environment: dict[str, Any],
) -> bool:
    if (
        not isinstance(binding, dict)
        or binding.get("locator") != STOP_LOCATOR
        or binding.get("sha256")
        != configured_environment.get("stopArtifactSha256")
    ):
        return False
    try:
        value = base._read_bound_artifact(root, binding, "source-bound-stop-v2")
    except (OSError, RecursionError, TypeError, ValueError):
        return False
    return (
        set(value)
        == {
            "schema",
            "kind",
            "environmentIdentity",
            "sourceKind",
            "sourceIdentity",
            "reason",
        }
        and type(value.get("schema")) is int
        and value.get("schema") == 1
        and value.get("kind") == "source-bound-user-configured-unavailable-stop"
        and value.get("environmentIdentity") == USER_ENVIRONMENT_IDENTITY
        and value.get("sourceKind") == "named-human-configuration-boundary"
        and value.get("sourceIdentity")
        == configured_environment.get("stopSourceIdentity")
        and value.get("reason")
        == "existing-user-configured-environment-excluded-by-exact-second-generation-grant"
    )


def _read_registration_document(
    root: Path,
    binding: Any,
) -> tuple[dict[str, Any], str]:
    if not isinstance(binding, dict) or set(binding) != REGISTRATION_BINDING_FIELDS:
        raise ValueError("registration binding shape")
    source_revision = binding.get("sourceRevision")
    validator = binding.get("preMeasurementValidator")
    if (
        binding.get("locator") != REGISTRATION_LOCATOR
        or not base._sha256(binding.get("sha256"))
        or not base._revision(source_revision)
        or binding.get("profileSha256") != PROFILE_SHA256
        or binding.get("cohortProtocolSha256") != PROTOCOL_SHA256
        or not isinstance(validator, dict)
        or set(validator) != {"kind", "version", "locator", "revision", "sha256"}
        or validator.get("kind") != VALIDATOR_KIND
        or type(validator.get("version")) is not int
        or validator.get("version") != 1
        or validator.get("locator") != VALIDATOR_LOCATOR
        or not base._revision(validator.get("revision"))
        or not base._sha256(validator.get("sha256"))
    ):
        raise ValueError("registration binding identity")
    path = (root / REGISTRATION_LOCATOR).resolve(strict=True)
    resolved_root = root.resolve(strict=True)
    if resolved_root not in path.parents or not path.is_file():
        raise ValueError("registration escapes root")
    raw = path.read_bytes()
    if len(raw) > 262_144:
        raise ValueError("registration byte limit")
    normalized = raw.replace(b"\r\n", b"\n")
    if hashlib.sha256(normalized).hexdigest() != binding["sha256"]:
        raise ValueError("registration digest")
    return base._strict_json_object(normalized), source_revision


def _observation_valid(root: Path, observation: dict[str, Any]) -> bool:
    if set(observation) != {
        "schema",
        "suiteIdentity",
        "sourceRevision",
        "packageIdentity",
        "environmentDisposition",
        "pluginLifecycleArtifacts",
        "scenarioArtifacts",
        "accepted",
        "cleanupVerified",
        "fieldClaimsExcluded",
    } or type(observation.get("schema")) is not int or observation.get("schema") != 1:
        return False
    try:
        program = base._strict_json_object((root / "product/program.json").read_bytes())
        increment = next(
            item
            for item in program.get("increments", [])
            if isinstance(item, dict) and item.get("id") == INCREMENT_ID
        )
        registration, source_revision = _read_registration_document(
            root, increment.get("taskRegistration")
        )
        registration_errors: list[str] = []
        if not validate_registration(
            registration, increment, ("O2",), root, registration_errors
        ):
            return False
        values = registration["preRegistrationValues"]
        environments = values["exactCodexVersionAndEnvironmentClass"]
        package = values["packageAndActivationIdentity"]
        scenario_binding = values["scenarioValidator"]
        projection_builder = scenario_binding["projectionBuilder"]
        if (
            observation.get("suiteIdentity") != SUITE_IDENTITY
            or observation.get("sourceRevision") != source_revision
            or observation.get("packageIdentity") != package
            or observation.get("accepted") is not True
            or observation.get("cleanupVerified") is not True
            or observation.get("fieldClaimsExcluded") != FIELD_CLAIM_EXCLUSIONS
        ):
            return False
        disposition = observation.get("environmentDisposition")
        if (
            not isinstance(disposition, dict)
            or set(disposition) != {"cleanIsolated", "userConfigured"}
            or disposition.get("cleanIsolated") != "available-and-measured"
        ):
            return False
        configured = disposition.get("userConfigured")
        configured_registration = environments["userConfigured"]
        if (
            not isinstance(configured, dict)
            or set(configured) != {"state", "stopArtifact"}
            or configured_registration.get("availabilityDisposition")
            != "source-bound-unavailable-stop"
            or configured.get("state") != "source-bound-unavailable-stop"
            or not _stop_artifact_valid(
                root, configured.get("stopArtifact"), configured_registration
            )
        ):
            return False
        lifecycle = observation.get("pluginLifecycleArtifacts")
        if not isinstance(lifecycle, dict) or set(lifecycle) != {
            "before",
            "active",
            "removed",
        }:
            return False
        clean_version = environments["cleanIsolated"]["codexVersion"]
        before = base._plugin_state(
            root,
            lifecycle["before"],
            CLEAN_ENVIRONMENT_IDENTITY,
            clean_version,
            projection_builder,
        )
        active = base._plugin_state(
            root,
            lifecycle["active"],
            CLEAN_ENVIRONMENT_IDENTITY,
            clean_version,
            projection_builder,
        )
        removed = base._plugin_state(
            root,
            lifecycle["removed"],
            CLEAN_ENVIRONMENT_IDENTITY,
            clean_version,
            projection_builder,
        )
        plugin_id = package["pluginId"]
        expected_plugin = (
            plugin_id,
            package["packageVersion"],
            True,
            True,
            "local-marketplace",
        )
        if before != removed or any(item[0] == plugin_id for item in before):
            return False
        if expected_plugin not in active or tuple(
            item for item in active if item[0] != plugin_id
        ) != before:
            return False
        records = observation.get("scenarioArtifacts")
        contracts = scenario_binding["scenarioContracts"]
        return (
            isinstance(records, list)
            and len(records) == len(SCENARIOS)
            and all(
                base._scenario_artifacts_valid(
                    root,
                    record,
                    scenario,
                    contract,
                    clean_version,
                    projection_builder,
                )
                for record, scenario, contract in zip(
                    records, SCENARIOS, contracts, strict=True
                )
            )
        )
    except (KeyError, OSError, RecursionError, StopIteration, TypeError, ValueError):
        return False


def validate_registration(
    registration: dict[str, Any],
    increment: dict[str, Any],
    mapped_outcomes: tuple[str, ...],
    root: Path,
    errors: list[str],
) -> bool:
    """Validate the exact second-generation O2 suite before installation."""

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
        _error(errors, "O2 permission-profile registration identity is invalid")
        return False
    if (
        values.get("normativeProfileIdentity") != PROFILE_IDENTITY
        or values.get("cohortProtocolIdentity") != PROTOCOL_IDENTITY
        or values.get("profileSha256") != PROFILE_SHA256
        or values.get("cohortProtocolSha256") != PROTOCOL_SHA256
    ):
        _error(errors, "O2 permission-profile binding is invalid")
    if not _scenario_records_valid(values.get("scenarioIdentityAndClass")):
        _error(errors, "O2 permission-profile suite must bind four scenarios exactly once")
    environments = values.get("exactCodexVersionAndEnvironmentClass")
    manifests = values.get("startingEnvironmentManifest")
    environment_binding = values.get("environmentAttributionBinding")
    if not _environment_records_valid(environments):
        _error(errors, "O2 permission-profile environment classes are invalid")
    if not _starting_manifests_valid(manifests):
        _error(errors, "O2 permission-profile starting manifests are invalid")
    if not _permission_profile_manifest_valid(
        root, manifests, environment_binding, environments
    ):
        _error(errors, "O2 permission-profile starting manifest is invalid")
    package = values.get("packageAndActivationIdentity")
    if not base._package_binding_valid(package):
        _error(errors, "O2 permission-profile package binding is invalid")
    if not base._environment_package_cross_binding_valid(
        environment_binding, manifests, package, environments
    ):
        _error(errors, "O2 permission-profile environment and package binding drift")
    registration_binding = increment.get("taskRegistration")
    registration_source_revision = (
        registration_binding.get("sourceRevision")
        if isinstance(registration_binding, dict)
        else None
    )
    if not base._package_source_binding_valid(
        root, package, registration_source_revision
    ):
        _error(errors, "O2 permission-profile package source binding is invalid")
    scenario_validator = values.get("scenarioValidator")
    projection_builder = (
        scenario_validator.get("projectionBuilder")
        if isinstance(scenario_validator, dict)
        else None
    )
    if not base._projection_builder_source_binding_valid(
        root, projection_builder, registration_source_revision
    ):
        _error(errors, "O2 permission-profile projection builder binding is invalid")
    if not _expected_delta_valid(values.get("expectedNativeOrHarnessDelta")):
        _error(errors, "O2 permission-profile expected deltas are invalid")
    if values.get("authorityAndCleanupBoundary") != {
        "installation": "exact-second-generation-grant-complete-install-only-after-registration",
        "account": "exact-isolated-device-auth-complete-before-manifest-capture",
        "authorityStop": "no-effect-before-grant-and-minimal-guidance-only",
        "rollback": "remove-exact-plugin-and-marketplace-restore-starting-state",
        "residue": "no-task-created-files-processes-config-or-credentials-after-cleanup",
    }:
        _error(errors, "O2 permission-profile authority and cleanup boundary is invalid")
    if not _scenario_validator_binding_valid(scenario_validator):
        _error(errors, "O2 permission-profile scenario validator binding is invalid")
    validator = registration.get("preMeasurementValidator")
    if not isinstance(validator, dict) or (
        validator.get("kind") != VALIDATOR_KIND
        or type(validator.get("version")) is not int
        or validator.get("version") != 1
        or validator.get("locator") != VALIDATOR_LOCATOR
    ):
        _error(errors, "O2 permission-profile validator binding is invalid")
    return len(errors) == before


def validate_evidence(
    document: dict[str, Any],
    criterion_id: str,
    root: Path,
    errors: list[str],
) -> bool:
    """Validate content-addressed second-generation Codex observations."""

    before = len(errors)
    source = document.get("source")
    result = document.get("result")
    if (
        criterion_id != "O2"
        or document.get("criterionIds") != ["O2"]
        or document.get("incrementId") != INCREMENT_ID
        or not isinstance(source, dict)
        or source.get("kind")
        != "controlled-live-codex-permission-profile-suite-observation"
        or source.get("locator") != OBSERVATION_LOCATOR
        or not isinstance(source.get("identity"), str)
        or not source["identity"].startswith("sha256:")
        or not base._sha256(source["identity"].removeprefix("sha256:"))
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
        or not base._revision(result.get("sourceRevision"))
        or not base._sha256(result.get("observationSha256"))
        or source.get("identity")
        != "sha256:" + result.get("observationSha256", "")
        or result.get("hostAndFilesystemValidated") is not True
        or result.get("cleanupVerified") is not True
        or result.get("claimCeiling")
        != "bounded-v1.2-live-codex-controlled-reference-application-only"
    ):
        _error(errors, "O2 permission-profile evidence requires replayed host evidence")
        return False
    try:
        observation_path = root / OBSERVATION_LOCATOR
        observation_raw = observation_path.read_bytes()
        if len(observation_raw) > 1_048_576:
            raise ValueError("observation exceeds byte limit")
        if hashlib.sha256(observation_raw).hexdigest() != result["observationSha256"]:
            raise ValueError("observation digest mismatch")
        observation = base._strict_json_object(observation_raw)
        if (
            observation.get("sourceRevision") != result["sourceRevision"]
            or not _observation_valid(root, observation)
        ):
            raise ValueError("observation replay failed")
    except (OSError, RecursionError, TypeError, UnicodeError, ValueError):
        _error(errors, "O2 permission-profile observation is missing or invalid")
    return len(errors) == before


__all__ = [
    "CLEAN_ENVIRONMENT_IDENTITY",
    "INCREMENT_ID",
    "MANIFEST_LOCATOR",
    "OBSERVATION_LOCATOR",
    "REGISTRATION_LOCATOR",
    "SCENARIOS",
    "SUITE_IDENTITY",
    "USER_ENVIRONMENT_IDENTITY",
    "VALIDATOR_KIND",
    "VALIDATOR_LOCATOR",
    "validate_evidence",
    "validate_registration",
]
