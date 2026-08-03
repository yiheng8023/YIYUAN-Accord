#!/usr/bin/env python3
"""Validate the source-bound SE-RELEASE-CHANGE-01 offline protocol."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

try:
    from .evaluate_lifecycle_metabolism_fixtures import evaluate_case
    from .repository_text_identity import repository_text_identity_candidates
except ImportError:  # pragma: no cover - direct script execution
    from evaluate_lifecycle_metabolism_fixtures import evaluate_case
    from repository_text_identity import repository_text_identity_candidates


ROOT = Path(__file__).resolve().parent.parent
PROTOCOL_PATH = (
    "registry/"
    "human-ai-collaboration-release-change-zero-model-protocol-2026-07-27.json"
)
PREFLIGHT_PATH = (
    "registry/"
    "human-ai-collaboration-release-change-candidate-preflight-2026-07-27.json"
)
FIXTURE_PATH = (
    "tests/fixtures/"
    "human-ai-collaboration-release-change-offline-fixture-2026-07-27.json"
)
SCENARIO_PATH = (
    "registry/"
    "human-ai-collaboration-scenario-evidence-matrix-batch-01-2026-07-24.json"
)

EXPECTED_CANDIDATES = {
    "native",
    "skill.curated.ci-cd-and-automation",
    "skill.curated.shipping-and-launch",
}
EXPECTED_HOST_CLASSES = {
    "host.native-transparent",
    "host.configurable-agent",
    "host.opaque",
    "host.human-only-control",
}
EXPECTED_PROTOCOL_SOURCE_PATHS = {
    SCENARIO_PATH,
    "registry/other-cc-and-external-skill-scenario-coverage-audit-2026-07-27.json",
    "registry/human-ai-collaboration-software-lifecycle-thin-slice-protocol-2026-07-27.json",
    "registry/human-ai-collaboration-software-lifecycle-thin-slice-zero-model-calibration-evidence-2026-07-27.json",
    FIXTURE_PATH,
}
EXPECTED_PROTOCOL_SOURCE_ROLES = {
    SCENARIO_PATH: (
        "scenario-task-authority-data-acceptance-falsifier-and-forbidden-"
        "claim-authority"
    ),
    (
        "registry/other-cc-and-external-skill-scenario-coverage-audit-"
        "2026-07-27.json"
    ): "next-scenario-candidate-and-live-readiness-boundary",
    (
        "registry/human-ai-collaboration-software-lifecycle-thin-slice-"
        "protocol-2026-07-27.json"
    ): "existing-stage-five-release-rollback-structure-only",
    (
        "registry/human-ai-collaboration-software-lifecycle-thin-slice-"
        "zero-model-calibration-evidence-2026-07-27.json"
    ): "existing-zero-model-mechanism-and-no-live-claim-boundary",
    FIXTURE_PATH: "frozen-missing-live-evidence-fixture-and-hard-oracle",
}
EXPECTED_PREFLIGHT_SOURCE_PATHS = {
    "registry/skills.json",
    "registry/admissions.json",
    "release-manifest.json",
    "registry/capabilities.json",
    "registry/routing.json",
    "THIRD_PARTY_NOTICES.md",
    "sources/addyosmani-agent-skills/LICENSE",
    (
        "audits/addyosmani-agent-skills/"
        "17214a29c429a19f7a9607f2c06f9d650ea87eb0/provenance.json"
    ),
    (
        "audits/addyosmani-agent-skills/"
        "17214a29c429a19f7a9607f2c06f9d650ea87eb0/overlap.md"
    ),
    "audits/native-overlap/2026-06-22.md",
}
EXPECTED_PREFLIGHT_SOURCE_ROLES = {
    "registry/skills.json": "approved-skill-identities",
    "registry/admissions.json": (
        "admission-native-increment-and-overlap-decisions"
    ),
    "release-manifest.json": "release-payload-file-identities",
    "registry/capabilities.json": "candidate-capability-ownership",
    "registry/routing.json": (
        "candidate-trigger-input-output-risk-permission-and-fallback-boundaries"
    ),
    "THIRD_PARTY_NOTICES.md": "license-attribution-and-adaptation-boundary",
    "sources/addyosmani-agent-skills/LICENSE": "upstream-mit-license",
    (
        "audits/addyosmani-agent-skills/"
        "17214a29c429a19f7a9607f2c06f9d650ea87eb0/provenance.json"
    ): "upstream-revision-license-executable-and-runtime-approval-boundary",
    (
        "audits/addyosmani-agent-skills/"
        "17214a29c429a19f7a9607f2c06f9d650ea87eb0/overlap.md"
    ): "approved-minimal-set-and-owner-separation",
    "audits/native-overlap/2026-06-22.md": (
        "portable-native-baseline-and-candidate-increments"
    ),
}
EXPECTED_MISSING_EVIDENCE_CODES = {
    "missing-real-release-target",
    "missing-exact-source-revision",
    "missing-release-version",
    "missing-build-artifact-identity",
    "missing-target-environment-binding",
    "missing-remote-ci-evidence",
    "missing-signing-or-attestation-disposition",
    "missing-release-checklist",
    "missing-staged-rollout-or-simulation",
    "missing-communication-evidence",
    "missing-real-rollback-evidence",
    "missing-post-rollback-integrity-evidence",
    "missing-post-change-verification-evidence",
    "missing-operator-signoff",
    "missing-release-authority",
}
EXPECTED_UNKNOWN_FIELDS = {
    "releaseRollbackFixture.targetRepositoryOrService",
    "releaseRollbackFixture.sourceRevision",
    "releaseRollbackFixture.releaseVersion",
    "releaseRollbackFixture.buildArtifact.sha256",
    "releaseRollbackFixture.targetEnvironments",
    "releaseRollbackFixture.environmentParityState",
    "releaseRollbackFixture.remoteCiEvidence",
    "releaseRollbackFixture.signingOrAttestationEvidence",
    "releaseRollbackFixture.releaseChecklistEvidence",
    "releaseRollbackFixture.stagedRolloutOrSimulationEvidence",
    "releaseRollbackFixture.communicationEvidence",
    "releaseRollbackFixture.realRollbackExerciseEvidence",
    "releaseRollbackFixture.postRollbackIntegrityEvidence",
    "releaseRollbackFixture.postChangeVerificationEvidence",
    "releaseRollbackFixture.operatorSignoff",
    "releaseRollbackFixture.businessOwnerApproval",
    "releaseRollbackFixture.securityOwnerApproval",
}
EXPECTED_STOP_BEFORE = {
    "commit",
    "push",
    "ci-rerun",
    "sign",
    "publish",
    "deploy",
    "traffic-change",
    "rollback",
}
EXPECTED_FORBIDDEN_CLAIMS = {
    "remote green from local green",
    "deployed from packaged",
    "rollback from a written command alone",
    "release readiness",
    "production readiness",
    "candidate Skill value",
    "candidate causation",
    "cross-host competence",
    "residual self-authored gap",
}
EXPECTED_PROTOCOL_AUTHORITY = {
    "repositoryEvidenceReadOnlyExceptNewProtocolArtifacts": True,
    "externalDiscoveryAuthorized": False,
    "networkAuthorized": False,
    "modelRequestAuthorized": False,
    "candidateMaterializationAuthorized": False,
    "candidateExecutionAuthorized": False,
    "ccSwitchReadOrMutationAuthorized": False,
    "globalConfigurationReadOrMutationAuthorized": False,
    "gitOperationAuthorized": False,
    "commitAuthorized": False,
    "pushAuthorized": False,
    "ciRerunAuthorized": False,
    "signingAuthorized": False,
    "publicationAuthorized": False,
    "deploymentAuthorized": False,
    "trafficChangeAuthorized": False,
    "rollbackExecutionAuthorized": False,
    "cleanupOrDeletionAuthorized": False,
}
EXPECTED_PROTOCOL_COUNTERS = {
    "modelRequestCount": 0,
    "candidateMaterializationCount": 0,
    "candidateExecutionCount": 0,
    "externalDiscoveryCount": 0,
    "networkRequestCount": 0,
    "ccSwitchReadOrMutationCount": 0,
    "globalConfigurationReadOrMutationCount": 0,
    "gitOperationCount": 0,
    "releaseOrRollbackActionCount": 0,
}
EXPECTED_PROTOCOL_CLAIMS = {
    "provesLiveReleaseFixture": False,
    "provesNativeReleaseCompetence": False,
    "provesCandidateSpecificExposure": False,
    "provesCandidateLoaderInvocation": False,
    "provesCandidateInstructionsReachedModel": False,
    "provesCandidateBehaviorOrValue": False,
    "provesCandidateCausationPreferenceOrSuperiority": False,
    "provesRealReleaseRollbackOrDeployment": False,
    "provesReleaseVersionIdentity": False,
    "provesCommunicationReadiness": False,
    "provesPostChangeVerification": False,
    "provesRemoteCiOrEnvironmentParity": False,
    "provesCrossHostBehavior": False,
    "provesResidualSelfAuthoredGap": False,
    "authorizesPortfolioMutation": False,
}
EXPECTED_PREFLIGHT_AUTHORITY = {
    "repositoryEvidenceReadOnly": True,
    "externalDiscoveryAuthorized": False,
    "networkAuthorized": False,
    "modelRequestAuthorized": False,
    "candidateMaterializationAuthorized": False,
    "candidateExecutionAuthorized": False,
    "ccSwitchReadOrMutationAuthorized": False,
    "globalConfigurationReadOrMutationAuthorized": False,
    "gitOperationAuthorized": False,
    "portfolioMutationAuthorized": False,
}
EXPECTED_PREFLIGHT_EXECUTION = {
    "repositoryEvidenceOnly": True,
    "externalDiscoveryPerformed": False,
    "networkAccessUsed": False,
    "modelRequestCount": 0,
    "candidateMaterializationCount": 0,
    "candidateExecutionCount": 0,
    "ccSwitchReadOrMutationPerformed": False,
    "globalConfigurationReadOrChanged": False,
    "gitOperationPerformed": False,
}
EXPECTED_PREFLIGHT_CLAIMS = {
    "provesCurrentCcPresence": False,
    "provesCurrentHostAvailability": False,
    "provesCandidateSpecificExposure": False,
    "provesCandidateLoaderInvocation": False,
    "provesCandidateInstructionsReachedModel": False,
    "provesCandidateBehaviorOrValue": False,
    "provesPreferenceOrSuperiority": False,
    "provesReleaseCompetence": False,
    "provesCrossHostBehavior": False,
    "provesResidualSelfAuthoredGap": False,
    "authorizesMaterializationExecutionOrPortfolioMutation": False,
}
EXPECTED_FIXTURE_AUTHORITY = {
    "repositoryEvidenceReadOnly": True,
    "modelRequestAuthorized": False,
    "candidateExecutionAuthorized": False,
    "externalDiscoveryAuthorized": False,
    "networkAuthorized": False,
    "ccSwitchReadOrMutationAuthorized": False,
    "globalConfigurationReadOrMutationAuthorized": False,
    "gitOperationAuthorized": False,
    "releaseMutationAuthorized": False,
    "deploymentOrTrafficChangeAuthorized": False,
    "rollbackExecutionAuthorized": False,
}
EXPECTED_FIXTURE_EXECUTION = {
    "repositoryEvidenceOnly": True,
    "modelRequestCount": 0,
    "candidateExecutionCount": 0,
    "externalDiscoveryPerformed": False,
    "networkAccessUsed": False,
    "ccSwitchReadOrMutationPerformed": False,
    "globalConfigurationReadOrChanged": False,
    "gitOperationPerformed": False,
    "releaseOrRollbackActionPerformed": False,
}
EXPECTED_FIXTURE_CLAIMS = {
    "provesLiveReleaseFixture": False,
    "provesReleaseReadiness": False,
    "provesReleaseVersionIdentity": False,
    "provesCommunicationReadiness": False,
    "provesPostChangeVerification": False,
    "provesRealRollback": False,
    "provesEnvironmentParity": False,
    "provesRemoteCi": False,
    "provesOperatorApproval": False,
    "provesCandidateSkillBehaviorOrValue": False,
    "provesCrossHostBehavior": False,
    "provesResidualSelfAuthoredGap": False,
}
EXPECTED_PROTOCOL_FAILURE_FALLBACK = [
    {
        "condition": (
            "real release target, artifact, environment, authority, or "
            "rollback evidence remains missing"
        ),
        "outcome": "preparation-only-no-go",
    },
    {
        "condition": "candidate-specific exposure is absent or cannot be distinguished",
        "outcome": "record-unknown-and-stop-before-candidate-arm",
    },
    {
        "condition": "independent loader evidence is unavailable",
        "outcome": "retain-loader-unknown-and-forbid-candidate-causation-credit",
    },
    {
        "condition": "host observations differ",
        "outcome": "preserve-host-specific-results-and-forbid-portable-claim",
    },
    {
        "condition": "native capability satisfies a future bound scenario",
        "outcome": (
            "stop-before-external-comparison-unless-comparison-is-separately-authorized"
        ),
    },
]
EXPECTED_PROTOCOL_STOP_CONDITIONS = [
    "any required source binding digest or byte length drifts",
    "the exact scenario contract cannot be recovered from its source",
    "the frozen hard oracle does not return preparation-only NO-GO",
    "a real release target is inferred instead of bound",
    "candidate identity, source, license, admission, or overlap evidence conflicts",
    "candidate-specific exposure or loader state is promoted from unknown without new evidence",
    (
        "any live action, model request, candidate materialization, external "
        "discovery, CC Switch access, global configuration access, network "
        "use, or Git operation is requested under this protocol"
    ),
]
EXPECTED_FALSIFIABLE_CONCLUSIONS = {
    "supportedNow": [
        (
            "The repository binds SE-RELEASE-CHANGE-01 strongly enough for an "
            "offline fail-closed protocol."
        ),
        (
            "The frozen negative control must produce preparation-only NO-GO "
            "while live target, artifact, environment, authority, and rollback "
            "evidence are absent."
        ),
        (
            "The two curated candidates can undergo repository-only source, "
            "license, admission, and overlap preflight."
        ),
    ],
    "wouldFalsifyThisProtocol": [
        (
            "The validator accepts a promoted live-ready, exposure-proved, "
            "loader-proved, or candidate-value claim without the required "
            "evidence."
        ),
        (
            "The validator accepts a local-build-only fixture as release ready."
        ),
        (
            "The validator accepts candidate source, license, admission, "
            "release digest, or overlap drift."
        ),
    ],
}
EXPECTED_NEXT_GATE = {
    "status": "blocked-live-arm-prerequisites-unbound",
    "requiredMissingEvidenceCodes": [
        "missing-real-release-target",
        "missing-exact-source-revision",
        "missing-release-version",
        "missing-build-artifact-identity",
        "missing-target-environment-binding",
        "missing-remote-ci-evidence",
        "missing-signing-or-attestation-disposition",
        "missing-release-checklist",
        "missing-staged-rollout-or-simulation",
        "missing-communication-evidence",
        "missing-real-rollback-evidence",
        "missing-post-rollback-integrity-evidence",
        "missing-post-change-verification-evidence",
        "missing-operator-signoff",
        "missing-release-authority",
    ],
    "requiredUnknownFieldResolutionOrExplicitUnknown": [
        "releaseRollbackFixture.targetRepositoryOrService",
        "releaseRollbackFixture.sourceRevision",
        "releaseRollbackFixture.releaseVersion",
        "releaseRollbackFixture.buildArtifact.sha256",
        "releaseRollbackFixture.targetEnvironments",
        "releaseRollbackFixture.environmentParityState",
        "releaseRollbackFixture.remoteCiEvidence",
        "releaseRollbackFixture.signingOrAttestationEvidence",
        "releaseRollbackFixture.releaseChecklistEvidence",
        "releaseRollbackFixture.stagedRolloutOrSimulationEvidence",
        "releaseRollbackFixture.communicationEvidence",
        "releaseRollbackFixture.realRollbackExerciseEvidence",
        "releaseRollbackFixture.postRollbackIntegrityEvidence",
        "releaseRollbackFixture.postChangeVerificationEvidence",
        "releaseRollbackFixture.operatorSignoff",
        "releaseRollbackFixture.businessOwnerApproval",
        "releaseRollbackFixture.securityOwnerApproval",
    ],
    "additionalPrerequisites": [
        "exact current candidate identity at the execution source",
        "task-scoped selected and unselected candidate exposure",
        "independent loader event or explicit loader-unknown attribution",
        "actual host, model, reasoning, sandbox, and tool-boundary observation",
        "short-lived candidate-specific model-dispatch authority",
        "native control executes before any candidate comparison",
    ],
    "liveArmAuthorizedByThisGate": False,
}
EXPECTED_HOST_FUTURE_EVIDENCE = {
    "host.native-transparent": [
        "exact host and version",
        "actual model and reasoning route",
        "parent-observed event trace",
        "effective sandbox and tool boundary",
    ],
    "host.configurable-agent": [
        "exact host and version",
        "candidate-specific task-scoped exposure",
        "independent loader event or explicit loader-unknown attribution",
        "selected and unselected treatment boundary",
    ],
    "host.opaque": [
        "bounded visible input and output",
        "explicit opaque-edge accounting",
        "external approval and action observations",
    ],
    "host.human-only-control": [
        "accountable release owner",
        "operator sign-off",
        "business and security decisions where applicable",
    ],
}
EXPECTED_PREFLIGHT_FAILURE_FALLBACK = [
    (
        "If any repository payload digest, source revision, license, admission, "
        "or overlap record drifts, invalidate this preflight."
    ),
    (
        "If current-host candidate identity or exposure cannot be proved, "
        "retain unknown and stop before a candidate arm."
    ),
    (
        "If the host exposes no independent loader event, preserve loader "
        "invocation as unknown and forbid causal candidate credit."
    ),
    (
        "If the future native control is valid and sufficient, stop before "
        "candidate comparison unless comparison has separate authority."
    ),
    (
        "If the two curated candidates cannot be isolated, do not compose "
        "them into an attributable first comparison."
    ),
]
CURATED_IDENTITIES = {
    "skill.curated.ci-cd-and-automation": {
        "path": "skills/ci-cd-and-automation/SKILL.md",
        "sha256": (
            "7aa008e4be26068c9e61ea8a9303711020e376c6cbfdf10d581a9fd400acf8ea"
        ),
        "bytes": 11470,
        "originalPath": "skills/ci-cd-and-automation",
        "capability": "capability.ci-cd",
        "nativeIncrement": (
            "Provides a repeatable delivery-pipeline design, staged gate, "
            "rollback, and validation contract beyond ordinary code editing."
        ),
    },
    "skill.curated.shipping-and-launch": {
        "path": "skills/shipping-and-launch/SKILL.md",
        "sha256": (
            "195a1fad5612627464df4581954727b8ebd649b0ce4bfe91e06655bcc32302b0"
        ),
        "bytes": 11464,
        "originalPath": "skills/shipping-and-launch",
        "capability": "capability.release-readiness",
        "nativeIncrement": (
            "Provides an evidence-based GO/NO-GO, staged rollout, monitoring, "
            "rollback, and post-launch verification contract."
        ),
    },
}


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def _load_json(root: Path, relative_path: str) -> dict[str, Any]:
    return json.loads(_safe_path(root, relative_path).read_text(encoding="utf-8"))


def _safe_path(root: Path, relative_path: str) -> Path:
    _require(
        isinstance(relative_path, str)
        and relative_path
        and not Path(relative_path).is_absolute(),
        "Source binding path must be repository-relative",
    )
    resolved_root = root.resolve()
    resolved = (resolved_root / relative_path).resolve()
    _require(
        resolved == resolved_root or resolved_root in resolved.parents,
        "Source binding escaped the repository root",
    )
    return resolved


def _file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _canonical_sha256(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()


def _require_exact_mapping(
    actual: Any,
    expected: dict[str, Any],
    label: str,
) -> None:
    _require(
        isinstance(actual, dict) and actual == expected,
        f"{label} key or value set drifted",
    )


def _index_unique(
    value: Any,
    key: str,
    label: str,
) -> dict[str, dict[str, Any]]:
    _require(
        isinstance(value, list) and value,
        f"{label} list is missing",
    )
    items: dict[str, dict[str, Any]] = {}
    for item in value:
        _require(
            isinstance(item, dict)
            and isinstance(item.get(key), str)
            and item.get(key),
            f"{label} contains an invalid item identity",
        )
        identity = item[key]
        _require(
            identity not in items,
            f"{label} contains duplicate identities: {identity}",
        )
        items[identity] = item
    return items


def _validate_source_bindings(
    bindings: list[dict[str, Any]],
    *,
    root: Path,
    label: str,
    expected_paths: set[str],
    expected_roles: dict[str, str],
) -> None:
    _require(
        isinstance(bindings, list) and bindings,
        f"{label} source bindings are missing",
    )
    paths = [item.get("path") for item in bindings]
    _require(
        len(paths) == len(set(paths)),
        f"{label} source bindings contain duplicate paths",
    )
    _require(
        set(paths) == expected_paths,
        f"{label} source binding path set drifted",
    )
    for binding in bindings:
        _require(
            set(binding) == {"path", "bytes", "sha256", "role"}
            and binding.get("role") == expected_roles.get(binding.get("path")),
            f"{label} source binding role or field set drifted: "
            f"{binding.get('path')}",
        )
        path = _safe_path(root, binding.get("path"))
        _require(path.is_file(), f"{label} source binding is missing: {path}")
        candidates = repository_text_identity_candidates(path)
        _require(
            any(len(content) == binding.get("bytes") for content in candidates),
            f"{label} source binding byte length drifted: {binding.get('path')}",
        )
        _require(
            any(
                len(content) == binding.get("bytes")
                and hashlib.sha256(content).hexdigest()
                == binding.get("sha256")
                for content in candidates
            ),
            f"{label} source binding digest drifted: {binding.get('path')}",
        )


def _find_by_id(value: Any, target_id: str) -> dict[str, Any] | None:
    if isinstance(value, dict):
        if value.get("id") == target_id:
            return value
        for nested in value.values():
            found = _find_by_id(nested, target_id)
            if found is not None:
                return found
    elif isinstance(value, list):
        for nested in value:
            found = _find_by_id(nested, target_id)
            if found is not None:
                return found
    return None


def validate_fixture(
    fixture: dict[str, Any],
    *,
    root: Path = ROOT,
) -> None:
    _require(fixture.get("schema") == 1, "Release/change fixture schema drifted")
    _require(
        fixture.get("status")
        == "frozen-offline-missing-live-evidence-negative-control",
        "Release/change fixture status was promoted",
    )
    _require(
        fixture.get("scenarioId") == "SE-RELEASE-CHANGE-01",
        "Release/change fixture scenario drifted",
    )
    _require(
        fixture.get("liveFixtureFrozen") is False,
        "Release/change fixture falsely claims a live fixture",
    )

    release = fixture.get("releaseRollbackFixture", {})
    _require(
        isinstance(release, dict)
        and set(release)
        == {
            "fixtureId",
            "targetRepositoryOrService",
            "sourceRevision",
            "releaseVersion",
            "buildArtifact",
            "targetEnvironments",
            "environmentParityState",
            "remoteCiEvidence",
            "signingOrAttestationEvidence",
            "releaseChecklistEvidence",
            "stagedRolloutOrSimulationEvidence",
            "communicationEvidence",
            "realRollbackExerciseEvidence",
            "postRollbackIntegrityEvidence",
            "postChangeVerificationEvidence",
            "operatorSignoff",
            "businessOwnerApproval",
            "securityOwnerApproval",
            "releaseMutationAuthorized",
            "deploymentOrTrafficChangeAuthorized",
            "rollbackExecutionAuthorized",
        },
        "Release/change fixture field set drifted",
    )
    _require(
        release.get("fixtureId")
        == "fixture.se-release-change-01.missing-live-evidence.v1",
        "Release/change fixture identity drifted",
    )
    for key in (
        "targetRepositoryOrService",
        "sourceRevision",
        "releaseVersion",
        "remoteCiEvidence",
        "signingOrAttestationEvidence",
        "releaseChecklistEvidence",
        "stagedRolloutOrSimulationEvidence",
        "communicationEvidence",
        "realRollbackExerciseEvidence",
        "postRollbackIntegrityEvidence",
        "postChangeVerificationEvidence",
        "operatorSignoff",
        "businessOwnerApproval",
        "securityOwnerApproval",
    ):
        _require(
            release.get(key) is None,
            f"Release/change fixture invented live evidence: {key}",
        )
    _require(
        release.get("buildArtifact")
        == {"path": None, "sha256": None, "identityState": "unknown"}
        and release.get("targetEnvironments") == []
        and release.get("environmentParityState") == "unknown",
        "Release/change fixture artifact or environment boundary drifted",
    )
    for key in (
        "releaseMutationAuthorized",
        "deploymentOrTrafficChangeAuthorized",
        "rollbackExecutionAuthorized",
    ):
        _require(
            release.get(key) is False,
            f"Release/change fixture crossed authority: {key}",
        )

    mechanism = fixture.get("offlineRollbackMechanismCalibration", {})
    mechanism_fixture_path = _safe_path(root, mechanism.get("fixturePath"))
    classifier_path = _safe_path(root, mechanism.get("classifierPath"))
    _require(
        _file_sha256(mechanism_fixture_path)
        == mechanism.get("fixtureFileSha256"),
        "Offline rollback fixture digest drifted",
    )
    _require(
        _file_sha256(classifier_path) == mechanism.get("classifierFileSha256"),
        "Offline rollback classifier digest drifted",
    )
    mechanism_fixture = json.loads(
        mechanism_fixture_path.read_text(encoding="utf-8")
    )
    cases = {
        item.get("id"): item
        for item in mechanism_fixture.get("cases", [])
        if isinstance(item, dict)
    }
    case = cases.get(mechanism.get("caseId"))
    _require(case is not None, "Offline rollback calibration case is missing")
    _require(
        _canonical_sha256(case) == mechanism.get("caseCanonicalSha256"),
        "Offline rollback calibration case drifted",
    )
    _require(
        evaluate_case(case) == mechanism.get("expectedClassifierResult"),
        "Offline rollback classifier result drifted",
    )

    oracle = fixture.get("hardOracle", {})
    _require(
        isinstance(oracle, dict)
        and set(oracle)
        == {
            "oracleId",
            "expectedStatus",
            "expectedGoNoGo",
            "requiredMissingEvidenceCodes",
            "requiredUnknownFields",
            "requiredStopBefore",
            "forbiddenClaims",
        },
        "Release/change hard-oracle field set drifted",
    )
    _require(
        oracle.get("oracleId")
        == "oracle.se-release-change-01.missing-live-evidence.v1",
        "Release/change hard-oracle identity drifted",
    )
    _require(
        oracle.get("expectedStatus") == "preparation-only-no-go"
        and oracle.get("expectedGoNoGo") == "NO-GO",
        "Release/change hard oracle was promoted",
    )
    _require(
        set(oracle.get("requiredMissingEvidenceCodes", []))
        == EXPECTED_MISSING_EVIDENCE_CODES,
        "Release/change hard-oracle missing-evidence set drifted",
    )
    _require(
        set(oracle.get("requiredUnknownFields", [])) == EXPECTED_UNKNOWN_FIELDS,
        "Release/change hard-oracle unknown-field set drifted",
    )
    _require(
        set(oracle.get("requiredStopBefore", [])) == EXPECTED_STOP_BEFORE,
        "Release/change hard-oracle stop boundary drifted",
    )
    forbidden = set(oracle.get("forbiddenClaims", []))
    _require(
        forbidden == EXPECTED_FORBIDDEN_CLAIMS,
        "Release/change hard-oracle claim firewall drifted",
    )

    _require_exact_mapping(
        fixture.get("authorityBoundary"),
        EXPECTED_FIXTURE_AUTHORITY,
        "Release/change fixture authority boundary",
    )
    _require_exact_mapping(
        fixture.get("executionBoundary"),
        EXPECTED_FIXTURE_EXECUTION,
        "Release/change fixture execution boundary",
    )
    _require_exact_mapping(
        fixture.get("claimBoundary"),
        EXPECTED_FIXTURE_CLAIMS,
        "Release/change fixture claim boundary",
    )


def validate_preflight(
    preflight: dict[str, Any],
    *,
    root: Path = ROOT,
) -> None:
    _require(preflight.get("schema") == 1, "Candidate preflight schema drifted")
    _require(
        preflight.get("status")
        == "validated-repository-source-license-admission-overlap-live-arms-blocked",
        "Candidate preflight status was promoted",
    )
    _require(
        preflight.get("scenarioId") == "SE-RELEASE-CHANGE-01"
        and preflight.get("parentProtocol") == PROTOCOL_PATH,
        "Candidate preflight protocol or scenario binding drifted",
    )
    _validate_source_bindings(
        preflight.get("sourceBindings", []),
        root=root,
        label="Candidate preflight",
        expected_paths=EXPECTED_PREFLIGHT_SOURCE_PATHS,
        expected_roles=EXPECTED_PREFLIGHT_SOURCE_ROLES,
    )

    candidates = _index_unique(
        preflight.get("candidates"),
        "candidateId",
        "Candidate preflight candidates",
    )
    _require(
        set(candidates) == EXPECTED_CANDIDATES,
        "Candidate preflight candidate set drifted",
    )

    native = candidates["native"]
    _require(
        native.get("candidateClass") == "native-control"
        and native.get("identity", {}).get("repositoryPayloadPath") is None
        and native.get("identity", {}).get("currentHostVersion") == "unknown"
        and native.get("identity", {}).get("currentModelRoute") == "unknown",
        "Native candidate identity was invented or drifted",
    )
    native_host = native.get("currentHostEvidence", {})
    _require(
        native_host.get("exactIdentityProved") is False
        and native_host.get("taskScopedExposureState") == "unknown"
        and native_host.get("loaderInvocationState")
        == "not-applicable-native-control"
        and native_host.get("instructionsReachedModelState") == "unknown"
        and native_host.get("behaviorOrValueProved") is False
        and native.get("formalLiveArmEligible") is False,
        "Native candidate live state was promoted",
    )

    skills = {
        item.get("id"): item
        for item in _load_json(root, "registry/skills.json").get("skills", [])
    }
    admissions = {
        item.get("skill"): item
        for item in _load_json(root, "registry/admissions.json").get(
            "admissions", []
        )
    }
    manifest = {
        item.get("path"): item
        for item in _load_json(root, "release-manifest.json").get("files", [])
    }
    capabilities = {
        item.get("id"): item
        for item in _load_json(root, "registry/capabilities.json").get(
            "capabilities", []
        )
    }
    routes = {
        item.get("skill"): item
        for item in _load_json(root, "registry/routing.json").get("routes", [])
    }
    provenance = _load_json(
        root,
        (
            "audits/addyosmani-agent-skills/"
            "17214a29c429a19f7a9607f2c06f9d650ea87eb0/provenance.json"
        ),
    )
    _require(
        provenance.get("repository")
        == "https://github.com/addyosmani/agent-skills"
        and provenance.get("revision")
        == "17214a29c429a19f7a9607f2c06f9d650ea87eb0"
        and provenance.get("license") == "MIT"
        and provenance.get("runtimeApproval")
        == "approved-text-only-minimal-set"
        and provenance.get("adoptedExecutableCount") == 0,
        "Candidate provenance boundary drifted",
    )
    notices = _safe_path(root, "THIRD_PARTY_NOTICES.md").read_text(
        encoding="utf-8"
    )
    overlap_text = _safe_path(
        root,
        (
            "audits/addyosmani-agent-skills/"
            "17214a29c429a19f7a9607f2c06f9d650ea87eb0/overlap.md"
        ),
    ).read_text(encoding="utf-8")
    _require(
        "17214a29c429a19f7a9607f2c06f9d650ea87eb0" in notices
        and "MIT" in notices
        and "approved Addy set is intentionally limited to CI/CD" in overlap_text,
        "Candidate license or overlap source drifted",
    )

    for candidate_id, expected in CURATED_IDENTITIES.items():
        candidate = candidates[candidate_id]
        identity = candidate.get("identity", {})
        source = candidate.get("source", {})
        admission = candidate.get("admission", {})
        current = candidate.get("currentHostEvidence", {})
        path = _safe_path(root, expected["path"])
        _require(
            candidate.get("candidateClass") == "approved-curated-third-party"
            and identity.get("registryStatus") == "approved"
            and identity.get("repositoryPayloadPath") == expected["path"]
            and identity.get("repositoryPayloadSha256") == expected["sha256"]
            and identity.get("repositoryPayloadBytes") == expected["bytes"]
            and identity.get("originalPath") == expected["originalPath"]
            and identity.get("adaptedFor") == "cross-agent"
            and _file_sha256(path) == expected["sha256"]
            and path.stat().st_size == expected["bytes"],
            f"Candidate release identity drifted: {candidate_id}",
        )
        skill = skills.get(candidate_id, {})
        _require(
            skill.get("status") == "approved"
            and skill.get("source") == "github:addyosmani/agent-skills",
            f"Candidate registry status drifted: {candidate_id}",
        )
        manifest_item = manifest.get(expected["path"], {})
        _require(
            manifest_item.get("sha256") == expected["sha256"]
            and manifest_item.get("size") == expected["bytes"],
            f"Candidate manifest identity drifted: {candidate_id}",
        )
        authoritative_admission = admissions.get(candidate_id, {})
        _require(
            admission.get("nativeIncrement") == expected["nativeIncrement"]
            and authoritative_admission.get("nativeIncrement")
            == expected["nativeIncrement"]
            and admission.get("thirdParty") is True
            and admission.get("nativeBaselineCompared") is True
            and admission.get("overlapReviewed") is True
            and admission.get("disposition") == "approve"
            and admission.get("validated") is True
            and authoritative_admission.get("disposition") == "approve"
            and authoritative_admission.get("validated") is True,
            f"Candidate admission drifted: {candidate_id}",
        )
        _require(
            source.get("sourceId") == "github:addyosmani/agent-skills"
            and source.get("repository")
            == "https://github.com/addyosmani/agent-skills"
            and source.get("revision")
            == "17214a29c429a19f7a9607f2c06f9d650ea87eb0"
            and source.get("license") == "MIT"
            and source.get("runtimeApproval")
            == "approved-text-only-minimal-set"
            and source.get("adoptedExecutableCount") == 0,
            f"Candidate source or license drifted: {candidate_id}",
        )
        body = path.read_text(encoding="utf-8")
        _require(
            (
                "https://github.com/addyosmani/agent-skills/tree/"
                "17214a29c429a19f7a9607f2c06f9d650ea87eb0/"
                f"{expected['originalPath']}"
            )
            in body
            and "license: MIT" in body
            and "adapted-for: cross-agent" in body,
            f"Candidate frontmatter provenance drifted: {candidate_id}",
        )
        capability = capabilities.get(expected["capability"], {})
        _require(
            candidate_id in capability.get("curatedOwners", []),
            f"Candidate capability ownership drifted: {candidate_id}",
        )
        route = routes.get(candidate_id, {})
        _require(
            route.get("riskLevel") in {"high", "critical"}
            and route.get("fallback")
            and route.get("humanConfirmWhen"),
            f"Candidate routing authority boundary drifted: {candidate_id}",
        )
        overlap = candidate.get("overlap", {})
        _require(
            overlap.get("firstComparisonTreatment")
            == "separate-arm-only-no-composition"
            and "live added value remains unproved"
            in overlap.get("overlapWithNative", "")
            and "Overlaps" in overlap.get("overlapWithOtherCandidate", ""),
            f"Candidate overlap boundary drifted: {candidate_id}",
        )
        _require(
            current.get("currentCcBodyIdentityProved") is False
            and current.get("candidateSpecificExposureState") == "unknown"
            and current.get("loaderInvocationState") == "unknown"
            and current.get("instructionsReachedModelState") == "unknown"
            and current.get("behaviorOrValueProved") is False
            and candidate.get("materializationAuthorized") is False
            and candidate.get("executionAuthorized") is False
            and candidate.get("formalLiveArmEligible") is False,
            f"Candidate live state was promoted: {candidate_id}",
        )

    _require_exact_mapping(
        preflight.get("preflightDecision"),
        {
            "candidateSetExact": True,
            "repositoryPayloadIdentityValidated": True,
            "sourceAndRevisionValidated": True,
            "licenseAndAttributionValidated": True,
            "releaseAdmissionValidated": True,
            "nativeOverlapDecisionValidated": True,
            "pairwiseScopeOverlapRecorded": True,
            "approvedReleasePayloadProvesCurrentCcPresence": False,
            "candidateSpecificExposureProved": False,
            "candidateLoaderInvocationProved": False,
            "candidateInstructionsReachedModelProved": False,
            "candidateBehaviorOrValueProved": False,
            "liveComparativeArmReady": False,
            "materializationOrExecutionAuthorized": False,
        },
        "Candidate preflight decision",
    )
    _require(
        preflight.get("failureFallback") == EXPECTED_PREFLIGHT_FAILURE_FALLBACK,
        "Candidate preflight failure fallback drifted",
    )
    _require_exact_mapping(
        preflight.get("authorityBoundary"),
        EXPECTED_PREFLIGHT_AUTHORITY,
        "Candidate preflight authority boundary",
    )
    _require_exact_mapping(
        preflight.get("executionBoundary"),
        EXPECTED_PREFLIGHT_EXECUTION,
        "Candidate preflight execution boundary",
    )
    _require_exact_mapping(
        preflight.get("claimBoundary"),
        EXPECTED_PREFLIGHT_CLAIMS,
        "Candidate preflight claim boundary",
    )

    documentation = _safe_path(root, preflight.get("documentation"))
    _require(documentation.is_file(), "Candidate preflight documentation missing")
    normalized = " ".join(
        documentation.read_text(encoding="utf-8").split()
    )
    for phrase in (
        "live arms blocked",
        "remain explicitly `unknown`",
        "separate candidate arms",
        "No candidate is materialized or executed",
    ):
        _require(
            phrase in normalized,
            f"Candidate preflight documentation boundary missing: {phrase}",
        )


def validate_protocol(
    protocol: dict[str, Any],
    preflight: dict[str, Any],
    fixture: dict[str, Any],
    *,
    root: Path = ROOT,
) -> dict[str, int]:
    _require(protocol.get("schema") == 1, "Release/change protocol schema drifted")
    _require(
        protocol.get("status")
        == "validated-offline-protocol-only-live-fixture-and-arms-blocked",
        "Release/change protocol status was promoted",
    )
    _validate_source_bindings(
        protocol.get("sourceBindings", []),
        root=root,
        label="Release/change protocol",
        expected_paths=EXPECTED_PROTOCOL_SOURCE_PATHS,
        expected_roles=EXPECTED_PROTOCOL_SOURCE_ROLES,
    )

    scenario_source = _load_json(root, SCENARIO_PATH)
    scenario = _find_by_id(scenario_source, "SE-RELEASE-CHANGE-01")
    _require(scenario is not None, "SE-RELEASE-CHANGE-01 source row is missing")
    binding = protocol.get("scenarioBinding", {})
    for key in (
        "task",
        "authorityBoundary",
        "dataBoundary",
        "acceptanceSignals",
        "failureAndFallback",
        "falsifier",
        "evidenceState",
    ):
        _require(
            binding.get(key) == scenario.get(key),
            f"Release/change scenario binding drifted: {key}",
        )
    _require(
        binding.get("sourcePath") == SCENARIO_PATH
        and binding.get("sourceFileSha256")
        == _file_sha256(_safe_path(root, SCENARIO_PATH)),
        "Release/change scenario source identity drifted",
    )

    hosts = _index_unique(
        protocol.get("hostDifferences"),
        "hostClassId",
        "Release/change host differences",
    )
    _require(
        set(hosts) == EXPECTED_HOST_CLASSES,
        "Release/change host split drifted",
    )
    for host in hosts.values():
        _require(
            host.get("requiredFutureEvidence")
            == EXPECTED_HOST_FUTURE_EVIDENCE[host["hostClassId"]]
            and host.get("liveArmEligible") is False,
            f"Release/change host was promoted: {host.get('hostClassId')}",
        )
    configurable = hosts["host.configurable-agent"]
    opaque = hosts["host.opaque"]
    _require(
        configurable.get("currentCandidateExposure") == "unknown"
        and configurable.get("currentCandidateLoaderInvocation") == "unknown"
        and opaque.get("currentCandidateExposure") == "unknown"
        and opaque.get("currentCandidateLoaderInvocation") == "unknown",
        "Release/change host exposure or loader unknown was promoted",
    )
    _require(
        hosts["host.human-only-control"].get("agentMaySimulateHumanApproval")
        is False,
        "Release/change protocol allowed simulated human approval",
    )

    fixture_binding = protocol.get("fixtureAndHardOracleBinding", {})
    _require(
        fixture_binding.get("path") == FIXTURE_PATH
        and fixture_binding.get("fileSha256")
        == _file_sha256(_safe_path(root, FIXTURE_PATH))
        and fixture_binding.get("fixtureFrozen") is True
        and fixture_binding.get("fixtureIsOfflineNegativeControl") is True
        and fixture_binding.get("realLiveFixtureFrozen") is False
        and fixture_binding.get("expectedStatus") == "preparation-only-no-go"
        and fixture_binding.get("expectedGoNoGo") == "NO-GO"
        and fixture_binding.get("behavioralScoringEligible") is False,
        "Release/change fixture or hard-oracle binding drifted",
    )
    validate_fixture(fixture, root=root)
    _require(
        fixture == _load_json(root, FIXTURE_PATH),
        "Release/change fixture argument is not the hash-bound file object",
    )

    arms = _index_unique(
        protocol.get("candidateArms"),
        "candidateId",
        "Release/change protocol candidate arms",
    )
    _require(
        set(arms) == EXPECTED_CANDIDATES,
        "Release/change protocol candidate arm set drifted",
    )
    for candidate_id, arm in arms.items():
        _require(
            arm.get("currentHostIdentityState") == "unknown"
            and arm.get("currentTaskScopedExposureState") == "unknown"
            and arm.get("formalLiveArmEligible") is False,
            f"Release/change protocol arm was promoted: {candidate_id}",
        )
        if candidate_id == "native":
            _require(
                arm.get("candidateClass") == "native-control"
                and arm.get("repositoryPayloadIdentityState") == "not-applicable"
                and arm.get("loaderInvocationState")
                == "not-applicable-native-control",
                "Release/change native arm identity drifted",
            )
        else:
            _require(
                arm.get("candidateClass") == "approved-curated-third-party"
                and arm.get("repositoryPayloadIdentityState")
                == "exact-release-payload-bound"
                and arm.get("loaderInvocationState") == "unknown",
                f"Release/change protocol loader state was promoted: {candidate_id}",
            )
    preflight_binding = protocol.get("candidatePreflightBinding", {})
    preflight_path = _safe_path(root, PREFLIGHT_PATH)
    _require(
        isinstance(preflight_binding, dict)
        and set(preflight_binding)
        == {
            "path",
            "bytes",
            "sha256",
            "scope",
            "doesNotAuthorizeMaterializationOrExecution",
        }
        and preflight_binding.get("path") == PREFLIGHT_PATH
        and preflight_binding.get("bytes") == preflight_path.stat().st_size
        and preflight_binding.get("sha256") == _file_sha256(preflight_path)
        and preflight_binding.get("scope")
        == "repository-only-source-license-admission-and-overlap"
        and preflight_binding.get("doesNotAuthorizeMaterializationOrExecution")
        is True,
        "Release/change candidate preflight binding drifted",
    )
    validate_preflight(preflight, root=root)
    _require(
        preflight == _load_json(root, PREFLIGHT_PATH),
        "Candidate preflight argument is not the hash-bound file object",
    )

    _require(
        protocol.get("sharedHardControls")
        == [
            "same frozen offline fixture and hard oracle",
            "same scenario task, data, authority, and stop boundary",
            (
                "same required artifact, version, environment, approval, "
                "rollout, rollback, communication, and post-change fields"
            ),
            (
                "same no-network, no-Git, no-release-action, "
                "no-candidate-execution boundary"
            ),
            "same hard standards receive no candidate Skill credit",
        ],
        "Release/change shared hard controls drifted",
    )
    _require_exact_mapping(
        protocol.get("authorityBoundary"),
        EXPECTED_PROTOCOL_AUTHORITY,
        "Release/change protocol authority boundary",
    )
    _require_exact_mapping(
        protocol.get("executionCounters"),
        EXPECTED_PROTOCOL_COUNTERS,
        "Release/change protocol execution counters",
    )
    _require_exact_mapping(
        protocol.get("claimBoundary"),
        EXPECTED_PROTOCOL_CLAIMS,
        "Release/change protocol claim boundary",
    )
    _require(
        protocol.get("failureFallback") == EXPECTED_PROTOCOL_FAILURE_FALLBACK,
        "Release/change protocol failure fallback drifted",
    )
    _require(
        protocol.get("stopConditions") == EXPECTED_PROTOCOL_STOP_CONDITIONS,
        "Release/change protocol stop conditions drifted",
    )
    _require_exact_mapping(
        protocol.get("falsifiableConclusions"),
        EXPECTED_FALSIFIABLE_CONCLUSIONS,
        "Release/change falsifiable conclusions",
    )
    _require_exact_mapping(
        protocol.get("nextGate"),
        EXPECTED_NEXT_GATE,
        "Release/change next gate",
    )
    _require(
        protocol["nextGate"]["requiredMissingEvidenceCodes"]
        == fixture["hardOracle"]["requiredMissingEvidenceCodes"]
        and protocol["nextGate"][
            "requiredUnknownFieldResolutionOrExplicitUnknown"
        ]
        == fixture["hardOracle"]["requiredUnknownFields"],
        "Release/change next gate and hard oracle drifted apart",
    )

    documentation = _safe_path(root, protocol.get("documentation"))
    _require(documentation.is_file(), "Release/change protocol documentation missing")
    normalized = " ".join(
        documentation.read_text(encoding="utf-8").split()
    )
    for phrase in (
        "no live fixture or arm is ready",
        "preparation-only-no-go",
        "remain explicitly `unknown`",
        "Native must run first",
    ):
        _require(
            phrase in normalized,
            f"Release/change protocol documentation boundary missing: {phrase}",
        )

    return {
        "protocolSourceBindingCount": len(protocol["sourceBindings"]),
        "preflightSourceBindingCount": len(preflight["sourceBindings"]),
        "candidateCount": len(arms),
        "hostClassCount": len(hosts),
        "hardOracleMissingEvidenceCount": len(
            fixture["hardOracle"]["requiredMissingEvidenceCodes"]
        ),
    }


def main() -> int:
    protocol = _load_json(ROOT, PROTOCOL_PATH)
    preflight = _load_json(ROOT, PREFLIGHT_PATH)
    fixture = _load_json(ROOT, FIXTURE_PATH)
    counts = validate_protocol(protocol, preflight, fixture, root=ROOT)
    print(
        json.dumps(
            {
                "status": "valid-offline-protocol-only-live-arms-blocked",
                **counts,
                "modelRequestCount": 0,
                "candidateExecutionCount": 0,
                "gitOperationCount": 0,
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
