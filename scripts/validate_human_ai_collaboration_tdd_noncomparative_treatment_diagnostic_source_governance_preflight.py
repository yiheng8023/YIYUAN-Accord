#!/usr/bin/env python3
"""Validate the dated TDD candidate source/governance preflight evidence."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
EVIDENCE_PATH = (
    "registry/"
    "human-ai-collaboration-tdd-noncomparative-treatment-diagnostic-"
    "source-governance-preflight-2026-07-26.json"
)
PROTOCOL_PATH = (
    "registry/"
    "human-ai-collaboration-tdd-noncomparative-treatment-diagnostic-"
    "protocol-2026-07-26.json"
)
DOCUMENTATION_PATH = (
    "docs/strategy/"
    "HUMAN-AI-COLLABORATION-TDD-NONCOMPARATIVE-TREATMENT-DIAGNOSTIC-"
    "SOURCE-GOVERNANCE-PREFLIGHT-2026-07-26.md"
)


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def _digest(value: Any, size: int = 64) -> bool:
    return (
        isinstance(value, str)
        and len(value) == size
        and all(character in "0123456789abcdef" for character in value)
    )


def _load(root: Path, path: str) -> dict[str, Any]:
    return json.loads((root / path).read_text(encoding="utf-8"))


def validate_evidence(
    document: dict[str, Any],
    *,
    root: Path = ROOT,
) -> None:
    _require(document.get("schema") == 1, "preflight schema must be 1")
    _require(
        document.get("status")
        == "dated-observation-source-identities-matched-governance-blocked-no-live-diagnostic",
        "preflight status drifted or was promoted",
    )
    _require(
        document.get("parentProtocol") == PROTOCOL_PATH
        and document.get("observedAt") == "2026-07-26T18:26:18+08:00",
        "preflight parent or time binding drifted",
    )
    protocol = _load(root, PROTOCOL_PATH)
    protocol_candidates = {
        candidate.get("candidateId"): candidate
        for candidate in protocol.get("candidates", [])
        if isinstance(candidate, dict)
    }

    authority = document.get("authorityBoundary", {})
    _require(
        authority.get("authenticatedReadOnlyGithubApiUsed") is True
        and authority.get("safeLocalOpenaiCuratedPluginCacheReadUsed") is True
        and authority.get("repositoryRegistryAndReleaseReadUsed") is True
        and authority.get("networkWriteAuthorized") is False
        and authority.get("candidateProjectionMaterializationPerformed")
        is False
        and authority.get("appServerInitializationPerformed") is False
        and authority.get("threadOrTurnStarted") is False
        and authority.get("modelRequestSent") is False
        and authority.get("candidateInstructionExecutionPerformed") is False
        and authority.get("installedCandidateMutationPerformed") is False
        and authority.get("globalConfigurationMutationPerformed") is False
        and authority.get("ccSwitchMutationPerformed") is False
        and authority.get("gitMutationPerformed") is False,
        "preflight authority boundary drifted",
    )

    observations = {
        item.get("candidateId"): item
        for item in document.get("candidateObservations", [])
        if isinstance(item, dict)
    }
    _require(
        set(observations) == set(protocol_candidates),
        "preflight candidate set drifted",
    )
    for candidate_id, observation in observations.items():
        protocol_candidate = protocol_candidates[candidate_id]
        expected_files = {
            item["path"]: item for item in protocol_candidate.get("files", [])
        }
        actual_files = {
            item.get("projectedPath"): item
            for item in observation.get("files", [])
            if isinstance(item, dict)
        }
        _require(
            set(actual_files) == set(expected_files)
            and observation.get("liveBytesMatchProtocol") is True,
            f"preflight candidate source binding drifted: {candidate_id}",
        )
        for path, actual in actual_files.items():
            expected = expected_files[path]
            _require(
                actual.get("bytes") == expected.get("bytes")
                and actual.get("sha256") == expected.get("sha256")
                and _digest(actual.get("sha256")),
                f"preflight candidate source binding drifted: {candidate_id}/{path}",
            )
            if candidate_id == "tdd.matt.current":
                _require(
                    actual.get("gitBlobSha1")
                    == expected.get("gitBlobSha1")
                    and _digest(actual.get("gitBlobSha1"), 40),
                    f"preflight Matt blob binding drifted: {path}",
                )

    matt = observations["tdd.matt.current"]
    _require(
        matt.get("observationSurface")
        == "authenticated-read-only-github-contents-api-exact-revision"
        and matt.get("repository") == "mattpocock/skills"
        and matt.get("pinnedRevision")
        == "ed37663cc5fbef691ddfecd080dff42f7e7e350d"
        and matt.get("currentMainRevision") == matt.get("pinnedRevision")
        and matt.get("currentMainMatchesPinned") is True
        and matt.get("license", {}).get("sha256")
        == protocol_candidates["tdd.matt.current"]["license"]["sha256"]
        and matt.get("license", {}).get("bytes")
        == protocol_candidates["tdd.matt.current"]["license"]["bytes"],
        "preflight Matt observation drifted",
    )
    superpowers = observations["tdd.superpowers.6.2.0"]
    parent = _load(root, protocol["parentProtocol"])
    parent_superpowers = next(
        item
        for item in parent["projectionCandidates"]
        if item["candidateId"] == "tdd.superpowers.6.2.0"
    )
    _require(
        superpowers.get("observationSurface")
        == "safe-local-openai-curated-plugin-cache-read"
        and superpowers.get("packageVersion") == "6.2.0"
        and superpowers.get("pluginManifest", {}).get("sha256")
        == parent_superpowers["source"]["pluginManifestSha256"]
        and superpowers.get("pluginManifest", {}).get("bytes")
        == parent_superpowers["source"]["pluginManifestBytes"]
        and superpowers.get("license", {}).get("sha256")
        == protocol_candidates["tdd.superpowers.6.2.0"]["license"]["sha256"]
        and superpowers.get("license", {}).get("bytes")
        == protocol_candidates["tdd.superpowers.6.2.0"]["license"]["bytes"],
        "preflight Superpowers observation drifted",
    )

    toolchain = document.get("toolchainObservation", {})
    expected_tools = {
        "rawItemNormalizer": (
            "scripts/normalize_human_ai_collaboration_tdd_app_server_items.py",
            "589498499b85a898a71070c04b23a34f744407b2d05aa96b304e78cb4931daaa",
        ),
        "projectionBuilder": (
            "scripts/build_source_pinned_skill_projection.py",
            "d1e43ee71a462f97bf0f4eee4387ceb86e70a4619b86774d608d7d9d498ac23f",
        ),
        "selectionPreflightProbe": (
            "scripts/probe_source_pinned_skill_projection_preflight.py",
            "2c6d22b19f301a6ef27bc575c4177704cb462c05c98863603f8a60de5268516b",
        ),
    }
    _require(
        toolchain.get("codexCliVersion") == "0.145.0",
        "preflight Codex version drifted",
    )
    for key, (path, digest) in expected_tools.items():
        record = toolchain.get(key, {})
        _require(
            record.get("path") == path
            and record.get("sha256") == digest
            and _digest(record.get("sha256"))
            and isinstance(record.get("bytes"), int)
            and record["bytes"] > 0,
            f"preflight toolchain binding drifted: {key}",
        )
        actual = (root / path).read_bytes()
        _require(
            len(actual) == record["bytes"]
            and hashlib.sha256(actual).hexdigest() == record["sha256"],
            f"preflight toolchain actual bytes drifted: {key}",
        )

    governance = document.get("governanceObservation", {})
    skills = _load(root, "registry/skills.json").get("skills", [])
    admissions = _load(root, "registry/admissions.json").get("admissions", [])
    release_files = _load(root, "release-manifest.json").get("files", [])
    skill = next(item for item in skills if item.get("id") == "skill.curated.tdd")
    admission = next(
        item
        for item in admissions
        if item.get("skill") == "skill.curated.tdd"
    )
    release = next(
        item
        for item in release_files
        if item.get("path") == "skills/tdd/SKILL.md"
    )
    release_tdd_files = sorted(
        (
            {
                "path": item["path"],
                "bytes": item["size"],
                "sha256": item["sha256"],
            }
            for item in release_files
            if str(item.get("path", "")).startswith("skills/tdd/")
        ),
        key=lambda item: item["path"],
    )
    current_matt_logical_files = sorted(
        (
            {
                "name": Path(item["path"]).name,
                "bytes": item["bytes"],
                "sha256": item["sha256"],
            }
            for item in protocol_candidates["tdd.matt.current"]["files"]
        ),
        key=lambda item: item["name"],
    )
    release_by_name = {
        Path(item["path"]).name: item for item in release_tdd_files
    }
    current_by_name = {
        item["name"]: item for item in current_matt_logical_files
    }
    shared_names = set(release_by_name) & set(current_by_name)
    _require(
        governance.get("mattRelatedRegistrySkillId") == skill.get("id")
        and governance.get("mattRelatedRegistryStatus") == skill.get("status")
        == "approved"
        and governance.get("mattRelatedAdmissionDisposition")
        == admission.get("disposition")
        == "approve"
        and governance.get("mattRelatedAdmissionValidated")
        == admission.get("validated")
        is True
        and governance.get("mattApprovedReleaseSkillSha256")
        == release.get("sha256")
        and governance.get("mattCurrentProjectionSkillSha256")
        == protocol_candidates["tdd.matt.current"]["files"][0]["sha256"]
        and governance.get("mattCurrentProjectionEqualsApprovedReleasePayload")
        is False
        and governance["mattApprovedReleaseSkillSha256"]
        != governance["mattCurrentProjectionSkillSha256"]
        and governance.get("mattApprovedReleaseFiles") == release_tdd_files
        and governance.get("mattCurrentProjectionLogicalFiles")
        == current_matt_logical_files
        and governance.get("mattSharedLogicalFilesAllDiffer") is True
        and shared_names == {"SKILL.md", "mocking.md", "tests.md"}
        and all(
            release_by_name[name]["sha256"]
            != current_by_name[name]["sha256"]
            for name in shared_names
        )
        and governance.get("mattApprovedReleaseAdditionalLogicalFiles")
        == ["deep-modules.md", "interface-design.md", "refactoring.md"]
        and governance.get("superpowers620RepositorySkillEntryPresent")
        is False
        and governance.get("superpowers620RepositoryAdmissionPresent") is False
        and governance.get("superpowers620RepositoryReleaseEntryPresent")
        is False
        and governance.get("anyExactCandidateExecutionAdmissionSatisfied")
        is False,
        "preflight governance observation drifted",
    )
    _require(
        not any(
            skill_item.get("name") == "test-driven-development"
            or "superpowers"
            in str(skill_item.get("source", "")).lower()
            for skill_item in skills
        )
        and not any(
            "superpowers" in str(admission_item.get("source", "")).lower()
            or "test-driven-development"
            in str(admission_item.get("skill", "")).lower()
            for admission_item in admissions
        )
        and not any(
            str(release_item.get("path", "")).startswith(
                "skills/test-driven-development/"
            )
            for release_item in release_files
        ),
        "preflight Superpowers absence observation drifted",
    )

    raw = document.get("rawEvidenceBoundary", {})
    _require(
        raw.get("githubApiResponsesVendored") is False
        and raw.get("localPluginFilesVendored") is False
        and raw.get("validatorReplaysGithubApi") is False
        and raw.get("validatorRereadsExternalPluginCache") is False
        and raw.get("datedObservationMayDrift") is True
        and raw.get("historicalObservationValidated") is True
        and raw.get("freshForDispatch") is False
        and raw.get("freshRevalidationStillRequiredAtDispatch") is True,
        "preflight raw evidence boundary drifted",
    )

    decision = document.get("decision", {})
    _require(
        decision.get("mattPinnedSourceIdentityRevalidated") is True
        and decision.get("superpowers620LocalSourceIdentityRevalidated")
        is True
        and decision.get("currentToolchainIdentityRevalidated") is True
        and decision.get("historicalObservationValidated") is True
        and decision.get("freshForDispatch") is False
        and decision.get("liveDiagnosticStarted") is False
        and decision.get("modelRequestSent") is False
        and decision.get("candidateInstructionExecutionPerformed") is False
        and decision.get("candidateSpecificBodyDeliveryProved") is False
        and decision.get("candidateExecutionAdmissionSatisfied") is False
        and decision.get("formalComparisonRemainsBlocked") is True
        and "Do not dispatch either candidate"
        in str(decision.get("nextBoundedAction")),
        "preflight decision boundary drifted",
    )
    claims = document.get("claimBoundary", {})
    _require(
        len(claims) >= 12 and all(value is False for value in claims.values()),
        "preflight claim boundary was promoted",
    )
    _require(
        document.get("documentation") == DOCUMENTATION_PATH
        and (root / DOCUMENTATION_PATH).is_file(),
        "preflight documentation binding drifted",
    )
    documentation = " ".join(
        (root / DOCUMENTATION_PATH).read_text(encoding="utf-8").split()
    )
    for phrase in (
        "No projection, app-server session, thread, turn, or model request was started",
        "Matt current main still matched",
        "Superpowers 6.2.0 local package bytes still matched",
        "not the approved release payload",
        "no repository Skill, admission, or release entry",
        "does not replay the GitHub API observation",
        "must be repeated immediately before any later admitted dispatch",
    ):
        _require(
            phrase in documentation,
            f"preflight documentation boundary missing: {phrase}",
        )


def main() -> int:
    validate_evidence(_load(ROOT, EVIDENCE_PATH))
    print("human-AI TDD noncomparative source/governance preflight: valid")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
