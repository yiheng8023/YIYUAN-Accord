#!/usr/bin/env python3
"""Validate the authorized exact-source LongHorizon static-review receipt."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
RECORD_PATH = Path(
    "registry/process-loss-longhorizon-harness-exact-source-static-review-2026-08-07.json"
)
DOCUMENTATION_PATH = Path(
    "docs/strategy/PROCESS-LOSS-EXTERNAL-REUSE-RESEARCH-2026-08-07.md"
)
ACCEPTANCE_PATH = Path("registry/program-acceptance-map.json")
EVIDENCE_ID = "evidence.process-loss-longhorizon-harness-exact-source-static-review-2026-08-07"
SUPPORTS = {
    "acceptance.end-to-end-process-fidelity",
    "acceptance.residual-gap-proof",
    "acceptance.discovery-reuse-before-authoring",
}
REVISION = "b49ebf9654c1ee75eaf56dfe9eec1745fddcfa58"
TREE_OID = "cf5470d1242e6a092c91a709efeff68c61d36681"
PATH_HASH = "090e746768a20f4273ed6925e5a0b0740246cc7b7b6bb8a33ac400758d3e3aa8"
EXPECTED_OBJECTS = {
    ".github/workflows/release.yml": ("45f0d4d1797fc39a56a1a1a1778c1a95479af5c2", 2449),
    "LICENSE": ("5cdcf793dd964337f2bab257e74dac461c469018", 1089),
    "pyproject.toml": ("7c4871a927df5a59a4648839120b6576a3d9ae65", 838),
    "src/lh_harness/adapters/claude_code.py": ("6184bdbec492875f6e6d2ff332dd4f34caa86942", 5693),
    "src/lh_harness/adapters/claude_permissions.py": ("a30c124cf10a0ed7780cc98bf3a73938fa3b196b", 5748),
    "src/lh_harness/adapters/codex.py": ("b9928c8df556f978f3476b7d0543ab7257958b36", 5570),
    "src/lh_harness/auditor_agent.py": ("736ac8d14b7982a2e5315baeab82f9b2a2760f8a", 34397),
    "src/lh_harness/cli.py": ("7d553c228ab99c736b328e1f6c22a2b58a597f5a", 37599),
    "src/lh_harness/environment/local.py": ("3752a5d0f9fa1a4b1e7fbadb172b0113bb4c1a5c", 7650),
    "src/lh_harness/manager.py": ("9892d459d517a2de2980244b19ed4c6a46b5018d", 45368),
    "src/lh_harness/plugins/npm.py": ("e3a15ea9eb5d6196df9702b4a7563e81624c2d3a", 4043),
    "src/lh_harness/utils/process_group.py": ("598552cd9a34183e2f96f85fd1021939658e23ec", 3608),
    "src/lh_harness/plugins/community_computer_use.py": ("f5e729286040d36fe62f520732423b065bdcb80b", 13811),
    "src/lh_harness/plugins/codex_computer_use.py": ("4b8fed7abc9add95eb5f8bf1d2c1a6641fd67c63", 13198),
}
EXPECTED_FINDING_IDS = {
    "default-host-permission-bypass",
    "auditor-post-hoc-detection-without-restore",
    "large-file-snapshot-content-gap",
    "no-cross-process-resume-command",
    "windows-portability-gap",
    "arbitrary-workspace-without-transaction-rollback",
    "plugin-lifecycle-authority-conflict",
    "no-independent-core-test-suite",
    "repository-scope-rights-and-weight",
}


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def validate_record(
    record: dict[str, Any],
    *,
    acceptance: dict[str, Any] | None = None,
    root: Path = ROOT,
) -> None:
    _require(
        record.get("schema") == 1
        and record.get("id")
        == "process-loss-longhorizon-harness-exact-source-static-review-v1"
        and record.get("asOf") == "2026-08-07"
        and record.get("status")
        == "exact-source-acquired-static-review-complete-temp-recycled-no-execution",
        "LongHorizon exact-source review identity drifted",
    )
    _require(
        record.get("documentation") == DOCUMENTATION_PATH.as_posix()
        and (root / DOCUMENTATION_PATH).is_file()
        and len(record.get("predecessorEvidence", [])) == 3
        and all((root / path).is_file() for path in record["predecessorEvidence"]),
        "LongHorizon exact-source predecessor or documentation binding drifted",
    )
    contract = record.get("transactionContract", {})
    _require(
        isinstance(contract.get("forbiddenActions"), list)
        and len(contract["forbiddenActions"]) == 10
        and "candidate-code-execution" in contract["forbiddenActions"]
        and "model-dispatch" in contract["forbiddenActions"],
        "LongHorizon exact-source transaction contract drifted",
    )

    acquisition = record.get("sourceAcquisition", {})
    fetch = acquisition.get("fetch", {})
    checkout = acquisition.get("checkout", {})
    cleanup = acquisition.get("cleanup", {})
    _require(
        acquisition.get("transactionId")
        == "longhorizon-exact-source-2f46ee51636042b0843133510a7d629d"
        and acquisition.get("normalizedPathSha256") == PATH_HASH
        and acquisition.get("revision") == REVISION
        and acquisition.get("treeOid") == TREE_OID
        and acquisition.get("remoteMainMatchedRevisionAtReview") is True,
        "LongHorizon exact-source acquisition identity drifted",
    )
    _require(
        re.fullmatch(r"[0-9a-f]{64}", PATH_HASH) is not None
        and re.fullmatch(r"[0-9a-f]{40}", REVISION) is not None
        and re.fullmatch(r"[0-9a-f]{40}", TREE_OID) is not None,
        "LongHorizon exact-source identities are not immutable digests",
    )
    _require(
        fetch.get("initialCommandTimedOutAfterPackDownload") is True
        and fetch.get("refsCreatedByTimedOutFetch") is False
        and fetch.get("targetCommitObjectPresentAfterTimeout") is True
        and fetch.get("fullFsckPassedBeforeCheckout") is True
        and fetch.get("detachedCheckoutRecoveredFromVerifiedObject") is True
        and fetch.get("candidateCrashRecoveryEvidence") is False,
        "LongHorizon fetch-recovery claim boundary drifted",
    )
    _require(
        checkout
        == {
            "clean": True,
            "trackedPaths": 1367,
            "gitlinks": 0,
            "symlinks": 0,
            "totalBytesIncludingGitObjects": 211769067,
            "coreSourcePaths": 39,
            "evalPaths": 1317,
        },
        "LongHorizon checkout inventory drifted",
    )
    _require(
        cleanup.get("method") == "Windows Recycle Bin"
        and cleanup.get("originalPathExistsAfterCleanup") is False
        and cleanup.get("recycleBinEntryMatchedNameAndDeletedFromOsTemp") is True
        and cleanup.get("recoverableByUserFromRecycleBin") is True
        and cleanup.get("otherPathsRemoved") is False,
        "LongHorizon exact-temp cleanup receipt drifted",
    )

    snapshot = record.get("sourceSnapshot", {})
    _require(
        snapshot.get("repository") == "github:AMAP-ML/LongHorizon-Harness"
        and snapshot.get("revision") == REVISION
        and snapshot.get("treeOid") == TREE_OID
        and snapshot.get("package", {}).get("name") == "lh-harness"
        and snapshot.get("package", {}).get("version") == "0.1.2"
        and snapshot.get("package", {}).get("sdistIncludesCoreOnly") is True,
        "LongHorizon exact-source package identity drifted",
    )
    actual_objects = {
        item["path"]: (item.get("oid"), item.get("size"))
        for item in snapshot.get("selectedGitObjects", [])
        if isinstance(item, dict) and isinstance(item.get("path"), str)
    }
    _require(actual_objects == EXPECTED_OBJECTS, "LongHorizon selected objects drifted")
    _require(
        len(snapshot.get("licenseScopes", [])) == 4
        and len(snapshot.get("largeTrackedObjects", [])) == 3,
        "LongHorizon source-scope or rights boundary drifted",
    )

    findings = record.get("staticFindings", [])
    _require(
        {item.get("id") for item in findings if isinstance(item, dict)}
        == EXPECTED_FINDING_IDS
        and all(
            item.get("severity")
            and item.get("evidencePaths")
            and item.get("finding")
            for item in findings
        ),
        "LongHorizon exact-source static findings drifted",
    )
    _require(
        set(path for item in findings for path in item["evidencePaths"])
        .issubset(EXPECTED_OBJECTS),
        "LongHorizon finding evidence is not bound to selected objects",
    )
    decision = record.get("decision", {})
    _require(
        decision.get("stopEquivalentCoordinatorAuthoring") is True
        and decision.get("directAdoption") == "blocked"
        and len(decision.get("safeReusableReferences", [])) == 6
        and len(decision.get("retainedHarnessAuthority", [])) == 7
        and "separate owner decision" in decision.get("nextGate", ""),
        "LongHorizon exact-source reuse decision drifted",
    )
    authority = record.get("authorityBoundary", {})
    _require(
        authority.get("exactSourceAcquisitionAuthorized") is True
        and authority.get("staticReviewAuthorized") is True
        and authority.get("exactTempCleanupToRecycleBinAuthorized") is True
        and all(
            authority.get(key) is False
            for key in (
                "installAuthorized", "executeAuthorized", "modelDispatchAuthorized",
                "adapterImplementationAuthorized", "accountConnectionAuthorized",
                "configurationMutationAuthorized", "ccSwitchMutationAuthorized",
                "consumerMutationAuthorized", "publicationAuthorized", "releaseAuthorized",
            )
        ),
        "LongHorizon exact-source authority boundary drifted",
    )
    claims = record.get("claimBoundary", {})
    _require(
        claims.get("provesExactSourceAcquisitionAndIntegrity") is True
        and claims.get("provesStaticSourceFindings") is True
        and claims.get("provesAuthorizedTempCleanupReceipt") is True
        and all(
            claims.get(key) is False
            for key in (
                "provesCandidateCrashRecovery", "provesInstallation",
                "provesRuntimeBehavior", "provesPermissionSafety", "provesRollback",
                "provesCrossProcessResume", "provesWindowsPortability",
                "provesCoreQuality", "provesCrossHostValue", "provesResidualGap",
                "provesProductionReadiness",
            )
        ),
        "LongHorizon exact-source claim boundary drifted",
    )

    if acceptance is not None:
        counts: dict[str, int] = {}
        for criterion in acceptance.get("acceptanceCriteria", []):
            status = criterion.get("assessment")
            counts[status] = counts.get(status, 0) + 1
        boundary = record.get("acceptanceBoundary", {})
        _require(
            counts == {
                "verified": boundary.get("verifiedCriteria"),
                "partial": boundary.get("partialCriteria"),
            }
            and boundary.get("plannedCriteria") == 0
            and boundary.get("criteriaAdvancedByThisReview") == [],
            "LongHorizon exact-source acceptance non-promotion drifted",
        )
        evidence = [
            item
            for item in acceptance.get("evidence", [])
            if isinstance(item, dict) and item.get("id") == EVIDENCE_ID
        ]
        _require(
            len(evidence) == 1
            and evidence[0].get("path") == RECORD_PATH.as_posix()
            and set(evidence[0].get("supports", [])) == SUPPORTS
            and "no-execution" in evidence[0].get("kind", "")
            and "no-behavior-value-or-residual-gap-proof" in evidence[0].get("kind", ""),
            "LongHorizon exact-source acceptance evidence registration drifted",
        )

    document = (root / DOCUMENTATION_PATH).read_text(encoding="utf-8")
    normalized_document = " ".join(document.split())
    for phrase in (
        "Authorized exact-source acquisition and deeper static review",
        REVISION,
        PATH_HASH,
        "Windows Recycle Bin",
        "no restoration implementation was found",
        "Direct adoption stays blocked",
    ):
        _require(
            phrase in normalized_document,
            "LongHorizon exact-source documentation drifted",
        )


def validate_repository_review(root: Path = ROOT) -> dict[str, Any]:
    record = json.loads((root / RECORD_PATH).read_text(encoding="utf-8"))
    acceptance = json.loads((root / ACCEPTANCE_PATH).read_text(encoding="utf-8"))
    validate_record(record, acceptance=acceptance, root=root)
    return record


def main() -> int:
    validate_repository_review(ROOT)
    print("LongHorizon exact-source static-review validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
