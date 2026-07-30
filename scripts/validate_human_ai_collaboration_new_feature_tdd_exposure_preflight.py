#!/usr/bin/env python3
"""Validate the bounded new-feature TDD candidate exposure preflight."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
EVIDENCE_PATH = (
    "registry/"
    "human-ai-collaboration-new-feature-tdd-exposure-preflight-2026-07-26.json"
)
DOCUMENTATION_PATH = (
    "docs/strategy/"
    "HUMAN-AI-COLLABORATION-NEW-FEATURE-TDD-EXPOSURE-PREFLIGHT-2026-07-26.md"
)
EXPECTED_CANDIDATES = {
    "tdd.matt.current": {
        "armId": "SE-TDD-MATT-CURRENT",
        "skillName": "tdd",
        "sourceRevisionOrVersion": (
            "ed37663cc5fbef691ddfecd080dff42f7e7e350d"
        ),
        "projectedFileCount": 3,
        "sourceClass": "reviewed-maintained-external-public-github-api",
        "manifestInternalSha256": (
            "1108dce7a8ee6a166208eabcce792168016c2cb9ab78225a2db17581f28aff54"
        ),
        "manifestFileSha256": (
            "c45524e7b717e3d9986f062fea7ff2c9bd5a95b8670c9ed919e8d80025bac465"
        ),
        "projectedTreeSha256": (
            "4004b864c2c2e472edaf4024aca1e9fb5a2861694b5480775d69c7e0001866c3"
        ),
        "reportInternalSha256": (
            "a1e7291d27c413d1e9d2596d57c12d0c65b1a6eaf789f15290a13d0098dc91a4"
        ),
        "reportFileSha256": (
            "a68150ccf17457662552ed9f33a166d89e1ee6c11e40a14f9a577fc6a5032aed"
        ),
    },
    "tdd.superpowers.6.2.0": {
        "armId": "SE-TDD-SUPERPOWERS-6.2.0",
        "skillName": "test-driven-development",
        "sourceRevisionOrVersion": "6.2.0",
        "projectedFileCount": 2,
        "sourceClass": "openai-curated-runtime-distributed-third-party",
        "manifestInternalSha256": (
            "6e5a5380dd502539876213e02660a3eba7b4f31d9e5bb01d85a53125733563ea"
        ),
        "manifestFileSha256": (
            "a81c7071ebd33ca0d6735b9eb37b8e23d14d629d6c0e43d41abe487d1b6434bd"
        ),
        "projectedTreeSha256": (
            "a95561fa9bf2ffbd75242e70a1d28d929c67b4d1df2997fa3061dc20c6b29501"
        ),
        "reportInternalSha256": (
            "525cb5bffd30af650f500a1b3a7660e51615aa92234c7ca7d7575057e579de7e"
        ),
        "reportFileSha256": (
            "968283bd72be8194875939dafb977c57d3d8eaa9222bd723b6880a3bf9ba656e"
        ),
    },
}


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def validate_evidence(
    document: dict[str, Any],
    *,
    root: Path = ROOT,
) -> None:
    _require(document.get("schema") == 1, "TDD exposure schema must be 1")
    _require(
        document.get("status")
        == "pass-current-host-configurable-metadata-selection-only",
        "TDD exposure status drifted or was promoted",
    )
    authority = document.get("authorityBoundary", {})
    _require(
        authority.get("threadOrTurnAuthorizedByThisRecord") is False
        and authority.get("modelRequestAuthorizedByThisRecord") is False
        and authority.get("globalSkillOrPluginConfigurationMutationAuthorized")
        is False
        and authority.get("installedCandidateMutationAuthorized") is False
        and authority.get("ccSwitchMutationAuthorized") is False
        and authority.get("commitOrPushAuthorized") is False,
        "TDD exposure authority boundary drifted",
    )

    host = document.get("host", {})
    _require(
        host.get("version") == "0.145.0"
        and host.get("threadStarted") is False
        and host.get("turnStarted") is False
        and host.get("modelRequestSent") is False,
        "TDD exposure host boundary drifted",
    )

    mechanism = document.get("projectionMechanism", {})
    for path_key, digest_key in (
        ("builder", "observedBuilderSha256"),
        ("preflightProbe", "observedPreflightProbeSha256"),
    ):
        path = mechanism.get(path_key)
        digest = mechanism.get(digest_key)
        _require(
            isinstance(path, str)
            and (root / path).is_file()
            and isinstance(digest, str)
            and len(digest) == 64,
            f"TDD exposure mechanism binding drifted: {path_key}",
        )
    _require(
        mechanism.get("historicalToolBytesVendored") is False
        and mechanism.get("currentToolContentRequiredToMatchObservation")
        is False
        and mechanism.get("sourceMutationAllowed") is False
        and mechanism.get("globalConfigurationMutationAllowed") is False
        and mechanism.get("installedSkillMutationAllowed") is False
        and mechanism.get("fullPluginInstallationOrActivationPerformed")
        is False,
        "TDD exposure projection mutation boundary drifted",
    )

    parent_path = document.get("parentProtocol")
    _require(
        parent_path
        == "registry/human-ai-collaboration-new-feature-tdd-protocol-2026-07-26.json"
        and (root / parent_path).is_file(),
        "TDD exposure parent protocol binding drifted",
    )
    parent = json.loads((root / parent_path).read_text(encoding="utf-8"))
    parent_candidates = {
        item.get("candidateId"): item
        for item in parent.get("projectionCandidates", [])
        if isinstance(item, dict)
    }
    candidates = {
        item.get("candidateId"): item
        for item in document.get("candidateEvidence", [])
        if isinstance(item, dict)
    }
    _require(
        set(candidates) == set(EXPECTED_CANDIDATES),
        "TDD exposure candidate set drifted",
    )
    for candidate_id, expected in EXPECTED_CANDIDATES.items():
        candidate = candidates[candidate_id]
        for key in (
            "armId",
            "skillName",
            "sourceRevisionOrVersion",
            "projectedFileCount",
            "sourceClass",
        ):
            _require(
                candidate.get(key) == expected[key],
                f"TDD exposure candidate binding drifted: {candidate_id}/{key}",
            )
        parent_candidate = parent_candidates.get(candidate_id)
        _require(
            isinstance(parent_candidate, dict)
            and parent_candidate.get("sourceClass")
            == candidate.get("sourceClass"),
            f"TDD exposure parent candidate mapping drifted: {candidate_id}",
        )
        expected_projected_files = [
            {
                "path": (
                    f".agents/skills/{candidate['skillName']}/"
                    f"{record['projectionRelativePath']}"
                ),
                "bytes": record["bytes"],
                "sha256": record["sha256"],
                "gitBlobSha1": record["gitBlobSha1"],
            }
            for record in parent_candidate.get("files", [])
        ]
        _require(
            candidate.get("projectedFiles") == expected_projected_files,
            f"TDD exposure projected file evidence drifted: {candidate_id}",
        )
        parent_license = parent_candidate.get("license", {})
        _require(
            candidate.get("license")
            == {
                "spdx": parent_license.get("spdx"),
                "bytes": parent_license.get("bytes"),
                "sha256": parent_license.get("sha256"),
                "gitBlobSha1": parent_license.get("gitBlobSha1"),
            },
            f"TDD exposure license evidence drifted: {candidate_id}",
        )
        projection = candidate.get("projection", {})
        preflight = candidate.get("preflight", {})
        for key in (
            "manifestInternalSha256",
            "manifestFileSha256",
            "projectedTreeSha256",
        ):
            _require(
                projection.get(key) == expected[key],
                f"TDD exposure projection digest drifted: {candidate_id}/{key}",
            )
        _require(
            projection.get("status") == "materialized-no-host-turn"
            and projection.get("sourceMutated") is False
            and projection.get("globalConfigMutated") is False
            and projection.get("installedSkillMutated") is False
            and projection.get("hostTurnStarted") is False,
            f"TDD exposure projection boundary drifted: {candidate_id}",
        )
        for key in ("reportInternalSha256", "reportFileSha256"):
            _require(
                preflight.get(key) == expected[key],
                f"TDD exposure preflight digest drifted: {candidate_id}/{key}",
            )
        _require(
            preflight.get("status") == "preflight-pass-no-turn"
            and preflight.get("skillCount") == 112
            and preflight.get("countsByScope")
            == {"repo": 1, "system": 6, "user": 105}
            and preflight.get("controlEnabledConfigurableSkillCount") == 0
            and preflight.get("selectedEnabledConfigurableSkillCount") == 1
            and preflight.get("sameIdentitySetInBothArms") is True
            and preflight.get("selectedIdentityPresentInBothArms") is True
            and preflight.get("onlyExpectedConfigurableSkillEnabledInBothArms")
            is True
            and preflight.get("allNonConfigurableStatesPreservedInBothArms")
            is True
            and preflight.get("projectionTreeStable") is True
            and preflight.get("globalConfigStable") is True
            and preflight.get("repositoryStatusStable") is True
            and preflight.get("threadStarted") is False
            and preflight.get("turnStarted") is False,
            f"TDD exposure inventory or stability drifted: {candidate_id}",
        )

    raw = document.get("rawEvidenceBoundary", {})
    _require(
        raw.get("rawReportsVendored") is False
        and raw.get("rawProjectionManifestsVendored") is False
        and raw.get("rawArtifactsRemainTemporary") is True
        and raw.get("rawArtifactsRequiredForRepositoryValidation") is False,
        "TDD exposure raw evidence boundary drifted",
    )
    _require(
        raw.get("validatorReplaysOriginalAppServerSession") is False
        and raw.get("projectionStabilityObservationScope")
        == "projected files listed in each projection manifest only",
        "TDD exposure observation-scope boundary drifted",
    )

    decision = document.get("decision", {})
    for key in (
        "mattCurrentExactProjectionProved",
        "superpowers620ExactProjectionProved",
        "currentHostCandidateSpecificSelectedMetadataExposureProved",
        "technicalReadyForNonScoredRawEventNormalizationPilot",
    ):
        _require(
            decision.get(key) is True,
            f"TDD exposure positive decision drifted: {key}",
        )
    for key in (
        "candidateSpecificTreatmentDeliveryProved",
        "independentLoaderEventProved",
        "liveTaskTurnStarted",
        "formalWeakAgentRunStarted",
        "candidatePreferenceAllowed",
        "selfAuthoredGapProved",
        "portfolioMutationAuthorized",
    ):
        _require(
            decision.get(key) is False,
            f"TDD exposure decision was promoted: {key}",
        )
    _require(
        "non-scored Spark/low TDD task-turn pilot"
        in str(decision.get("nextBoundedAction")),
        "TDD exposure next action drifted",
    )

    claims = document.get("claimBoundary", {})
    _require(
        claims and all(value is False for value in claims.values()),
        "TDD exposure claim boundary was promoted",
    )
    _require(
        document.get("documentation") == DOCUMENTATION_PATH
        and (root / DOCUMENTATION_PATH).is_file(),
        "TDD exposure documentation binding drifted",
    )
    documentation = " ".join(
        (root / DOCUMENTATION_PATH).read_text(encoding="utf-8").split()
    )
    for phrase in (
        "No thread or turn was started",
        "does not prove task-scoped body delivery",
        "Inventory metadata is not an independent loader event",
        "does not replay or independently prove the original app-server session",
        "one non-scored Spark/low task-turn pilot",
        "Formal three-arm repetitions must not start",
    ):
        _require(
            phrase in documentation,
            f"TDD exposure documentation boundary missing: {phrase}",
        )


def main() -> int:
    document = json.loads((ROOT / EVIDENCE_PATH).read_text(encoding="utf-8"))
    validate_evidence(document)
    print("human-AI collaboration new-feature TDD exposure preflight: valid")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
