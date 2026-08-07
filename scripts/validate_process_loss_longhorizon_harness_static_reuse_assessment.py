#!/usr/bin/env python3
"""Validate the exact-revision LongHorizon-Harness static reuse assessment."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
RECORD_PATH = Path(
    "registry/process-loss-longhorizon-harness-static-reuse-assessment-2026-08-07.json"
)
ACCEPTANCE_PATH = Path("registry/program-acceptance-map.json")
DOCUMENTATION_PATH = Path(
    "docs/strategy/PROCESS-LOSS-EXTERNAL-REUSE-RESEARCH-2026-08-07.md"
)
EVIDENCE_ID = (
    "evidence.process-loss-longhorizon-harness-static-reuse-assessment-2026-08-07"
)
SUPPORTED_ACCEPTANCE_IDS = (
    "acceptance.end-to-end-process-fidelity",
    "acceptance.residual-gap-proof",
    "acceptance.discovery-reuse-before-authoring",
)
EXPECTED_ACCEPTANCE_ASSESSMENTS = {
    "acceptance.end-to-end-process-fidelity": "partial",
    "acceptance.residual-gap-proof": "partial",
    "acceptance.discovery-reuse-before-authoring": "verified",
}
REVISION = "b49ebf9654c1ee75eaf56dfe9eec1745fddcfa58"
TREE_OID = "cf5470d1242e6a092c91a709efeff68c61d36681"
EXPECTED_GIT_OBJECTS = {
    ".github/workflows/release.yml": (
        "45f0d4d1797fc39a56a1a1a1778c1a95479af5c2",
        2449,
    ),
    "LICENSE": ("5cdcf793dd964337f2bab257e74dac461c469018", 1089),
    "README.md": ("5f9518f1baf32ddb29eafb72cc6a500c556cc1c9", 23851),
    "pyproject.toml": ("7c4871a927df5a59a4648839120b6576a3d9ae65", 838),
    "src/lh_harness/adapters/claude_code.py": (
        "6184bdbec492875f6e6d2ff332dd4f34caa86942",
        5693,
    ),
    "src/lh_harness/adapters/claude_permissions.py": (
        "a30c124cf10a0ed7780cc98bf3a73938fa3b196b",
        5748,
    ),
    "src/lh_harness/adapters/codex.py": (
        "b9928c8df556f978f3476b7d0543ab7257958b36",
        5570,
    ),
    "src/lh_harness/cli.py": (
        "7d553c228ab99c736b328e1f6c22a2b58a597f5a",
        37599,
    ),
    "src/lh_harness/manager.py": (
        "9892d459d517a2de2980244b19ed4c6a46b5018d",
        45368,
    ),
}
EXPECTED_MECHANISM_IDS = {
    "manage-execute-audit-loop",
    "audited-persistent-task-state",
    "completion-guard-and-human-routes",
    "thin-backend-adapters",
    "natural-language-state-contract",
}
EXPECTED_BLOCKER_IDS = {
    "host-permission-bypass",
    "auditor-readonly-not-enforced",
    "no-verified-cross-process-resume",
    "early-verification-surface",
}


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def _nonempty(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def validate_assessment_record(
    record: dict[str, Any],
    *,
    acceptance: dict[str, Any] | None = None,
    root: Path = ROOT,
) -> None:
    """Validate one in-memory assessment without accessing the external source."""
    _require(
        record.get("schema") == 1
        and record.get("id")
        == "process-loss-longhorizon-harness-static-reuse-assessment-v1"
        and record.get("asOf") == "2026-08-07"
        and record.get("status")
        == "exact-revision-static-reuse-candidate-review-complete-no-adoption",
        "LongHorizon-Harness assessment identity drifted",
    )
    _require(
        record.get("documentation") == str(DOCUMENTATION_PATH).replace("\\", "/")
        and (root / DOCUMENTATION_PATH).is_file(),
        "LongHorizon-Harness documentation binding drifted",
    )

    contract = record.get("taskContract", {})
    _require(
        isinstance(contract, dict)
        and all(
            _nonempty(contract.get(key))
            for key in (
                "useCase",
                "currentGap",
                "sourceBoundary",
                "accountAndDataBoundary",
                "authorityBoundary",
                "verificationSurface",
            )
        ),
        "LongHorizon-Harness task and capability-gap contract drifted",
    )

    snapshot = record.get("sourceSnapshot", {})
    post = snapshot.get("xPost", {})
    paper = snapshot.get("paper", {})
    repository = snapshot.get("repository", {})
    _require(
        post.get("url")
        == "https://x.com/Xudong07452910/status/2085206732096025020"
        and post.get("claimAuthority")
        == "not implementation, license, or benchmark authority",
        "LongHorizon-Harness discovery-source boundary drifted",
    )
    _require(
        paper.get("identifier") == "arXiv:2608.01964v1"
        and paper.get("url") == "https://arxiv.org/abs/2608.01964"
        and paper.get("independentlyReplicatedInThisAssessment") is False,
        "LongHorizon-Harness paper identity or replication boundary drifted",
    )
    _require(
        repository.get("id") == "github:AMAP-ML/LongHorizon-Harness"
        and repository.get("observedRef") == "refs/heads/main"
        and repository.get("revision") == REVISION
        and repository.get("treeOid") == TREE_OID
        and repository.get("mainMatchedRevisionAtReview") is True
        and repository.get("public") is True
        and repository.get("archived") is False
        and repository.get("license") == "MIT",
        "LongHorizon-Harness repository identity or license drifted",
    )
    _require(
        re.fullmatch(r"[0-9a-f]{40}", repository["revision"]) is not None
        and re.fullmatch(r"[0-9a-f]{40}", repository["treeOid"]) is not None,
        "LongHorizon-Harness revision is not an exact Git identity",
    )

    objects = repository.get("selectedGitObjects", [])
    _require(
        isinstance(objects, list)
        and len(objects) == len(EXPECTED_GIT_OBJECTS)
        and len({item.get("path") for item in objects if isinstance(item, dict)})
        == len(EXPECTED_GIT_OBJECTS),
        "LongHorizon-Harness selected Git-object set drifted",
    )
    actual_objects = {
        item["path"]: (item.get("oid"), item.get("size"))
        for item in objects
        if isinstance(item, dict) and _nonempty(item.get("path"))
    }
    _require(
        actual_objects == EXPECTED_GIT_OBJECTS
        and all(
            re.fullmatch(r"[0-9a-f]{40}", oid) is not None and size > 0
            for oid, size in actual_objects.values()
        ),
        "LongHorizon-Harness selected Git-object identity drifted",
    )
    _require(
        snapshot.get("rawThirdPartyBodyRetained") is False
        and snapshot.get("thirdPartyCodeExecuted") is False
        and snapshot.get("dependenciesInstalled") is False
        and snapshot.get("liveStateMutated") is False,
        "LongHorizon-Harness static acquisition boundary drifted",
    )

    mechanisms = record.get("mechanismFindings", [])
    mechanism_ids = {
        item.get("id") for item in mechanisms if isinstance(item, dict)
    }
    object_paths = set(EXPECTED_GIT_OBJECTS)
    _require(
        mechanism_ids == EXPECTED_MECHANISM_IDS
        and all(
            item.get("sourcePaths")
            and set(item["sourcePaths"]).issubset(object_paths)
            and _nonempty(item.get("finding"))
            and _nonempty(item.get("reuseDisposition"))
            for item in mechanisms
            if isinstance(item, dict)
        ),
        "LongHorizon-Harness mechanism evidence mapping drifted",
    )

    benchmarks = record.get("reportedBenchmarkObservations", {})
    _require(
        benchmarks.get("source") == "arXiv:2608.01964v1"
        and benchmarks.get("aggregateOnly") is True
        and benchmarks.get("taskDependentDeclinesPresent") is True
        and benchmarks.get("tokenReductionClaimUniversal") is False
        and benchmarks.get("independentlyReplicatedInThisAssessment") is False
        and len(benchmarks.get("results", [])) == 4
        and _nonempty(benchmarks.get("admissibleConclusion")),
        "LongHorizon-Harness author-reported benchmark boundary drifted",
    )

    fit = record.get("harnessFit", {})
    _require(
        len(fit.get("reuseEligibleSurfaceIds", [])) == 7
        and len(fit.get("retainedHarnessAuthorityIds", [])) == 7
        and fit.get("directReplacementDecision")
        == "not-authorized-and-not-supported"
        and fit.get("candidateDisposition")
        == "exact-revision-external-operational-coordinator-reference-for-no-model-interface-mapping"
        and _nonempty(fit.get("stopAuthoringDecision"))
        and _nonempty(fit.get("nextGate")),
        "LongHorizon-Harness reuse or retained-authority decision drifted",
    )
    blockers = fit.get("adoptionBlockers", [])
    blocker_ids = {item.get("id") for item in blockers if isinstance(item, dict)}
    _require(
        blocker_ids == EXPECTED_BLOCKER_IDS
        and all(
            item.get("evidencePaths")
            and set(item["evidencePaths"]).issubset(object_paths)
            and _nonempty(item.get("finding"))
            for item in blockers
            if isinstance(item, dict)
        ),
        "LongHorizon-Harness adoption-blocker mapping drifted",
    )

    authority = record.get("authorityBoundary", {})
    _require(
        authority.get("staticPublicSourceReviewAuthorized") is True
        and authority.get("repositoryEvidenceWriteAuthorized") is True
        and all(
            authority.get(key) is False
            for key in (
                "thirdPartyAcquisitionAuthorized",
                "installAuthorized",
                "enableAuthorized",
                "executeAuthorized",
                "modelDispatchAuthorized",
                "accountConnectionAuthorized",
                "consumerWorkspaceAccessAuthorized",
                "managerSubstitutionAuthorized",
                "forkOrModificationAuthorized",
                "publicationAuthorized",
                "releaseAuthorized",
            )
        ),
        "LongHorizon-Harness authority boundary drifted",
    )
    claims = record.get("claimBoundary", {})
    _require(
        claims.get("provesExactRepositoryRevisionAndSelectedObjects") is True
        and claims.get("provesCoreRepositoryMitLicense") is True
        and claims.get("provesStaticMechanismPresence") is True
        and all(
            claims.get(key) is False
            for key in (
                "provesHarnessInterfaceFit",
                "provesAuditorReadOnlyEnforcement",
                "provesCrashRecovery",
                "provesRuntimeBehavior",
                "provesIndependentBenchmarkReproduction",
                "provesCrossHostPortability",
                "provesSecurity",
                "provesUserValue",
                "provesResidualGap",
                "provesProductionReadiness",
                "authorizesInstallationActivationExecutionOrAdoption",
            )
        ),
        "LongHorizon-Harness claim boundary drifted",
    )

    acceptance = acceptance or json.loads(
        (root / ACCEPTANCE_PATH).read_text(encoding="utf-8")
    )
    criteria = {
        item.get("id"): item
        for item in acceptance.get("acceptanceCriteria", [])
        if isinstance(item, dict)
    }
    evidence = {
        item.get("id"): item
        for item in acceptance.get("evidence", [])
        if isinstance(item, dict)
    }
    _require(
        set(SUPPORTED_ACCEPTANCE_IDS).issubset(criteria)
        and all(
            criteria[acceptance_id].get("assessment")
            == EXPECTED_ACCEPTANCE_ASSESSMENTS[acceptance_id]
            and EVIDENCE_ID in criteria[acceptance_id].get("evidenceIds", [])
            for acceptance_id in SUPPORTED_ACCEPTANCE_IDS
        ),
        "LongHorizon-Harness acceptance boundary drifted",
    )
    evidence_record = evidence.get(EVIDENCE_ID, {})
    _require(
        evidence_record.get("path") == str(RECORD_PATH).replace("\\", "/")
        and evidence_record.get("asOf") == "2026-08-07"
        and set(evidence_record.get("supports", []))
        == set(SUPPORTED_ACCEPTANCE_IDS),
        "LongHorizon-Harness acceptance evidence binding drifted",
    )

    documentation = (root / DOCUMENTATION_PATH).read_text(encoding="utf-8")
    _require(
        REVISION in documentation
        and "not a replacement for the Harness process-fidelity contract"
        in documentation
        and "Direct adoption is not currently justified" in documentation
        and "No real Claude task is required" in documentation,
        "LongHorizon-Harness documentation lost a material claim boundary",
    )


def validate_repository_assessment(root: Path = ROOT) -> dict[str, Any]:
    record = json.loads((root / RECORD_PATH).read_text(encoding="utf-8"))
    acceptance = json.loads((root / ACCEPTANCE_PATH).read_text(encoding="utf-8"))
    validate_assessment_record(record, acceptance=acceptance, root=root)
    return record


def main() -> int:
    record = validate_repository_assessment()
    print(
        "PASS: LongHorizon-Harness exact-revision static reuse assessment "
        f"({record['sourceSnapshot']['repository']['revision']})."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
