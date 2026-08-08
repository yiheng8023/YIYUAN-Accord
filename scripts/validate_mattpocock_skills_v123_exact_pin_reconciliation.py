#!/usr/bin/env python3
"""Validate the Matt Skills v1.2.3 exact-pin reconciliation event."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
RECORD_PATH = Path(
    "registry/mattpocock-skills-v1.2.3-exact-pin-reconciliation-event-2026-08-08.json"
)
REPORT_PATH = Path(
    "audits/mattpocock-skills/6acc160e4e0cd062dbbbd7a1b26ae92855edf07e/"
    "exact-pin-reconciliation-2026-08-08/POST-RESTART-REPORT.json"
)
DOCUMENTATION_PATH = Path(
    "docs/strategy/MATTPOCOCK-SKILLS-V1.2.3-EXACT-PIN-RECONCILIATION-2026-08-08.md"
)
ACCEPTANCE_PATH = Path("registry/program-acceptance-map.json")
AUTHORITY_PATH = Path("registry/skill-portfolio-current-authority.json")
PLAN_PATH = Path("docs/strategy/RESEARCH-AND-POC-PLAN.md")
GOAL_PROMPT_PATH = Path("docs/operations/CURRENT-GOAL-MODE-PROMPT.md")
CONTINUATION_PATH = Path("docs/operations/CONTINUATION.md")
README_PATHS = (Path("README.md"), Path("README.zh-CN.md"))
TRANSACTION_SCRIPT_PATH = Path("scripts/reconcile_matt_cc_manager_exact_pin.py")
TRANSACTION_TEST_PATH = Path("tests/test_reconcile_matt_cc_manager_exact_pin.py")
EVIDENCE_ID = (
    "evidence.mattpocock-skills-v1.2.3-exact-pin-reconciliation-event-2026-08-08"
)
RELEASE_COMMIT = "6acc160e4e0cd062dbbbd7a1b26ae92855edf07e"
SUPPORTS = {
    "acceptance.cc-switch-source-preserving-skill-pool",
    "acceptance.consumer-mapping-evidence",
}


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def _canonical_digest(value: Any) -> str:
    encoded = json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def validate_record(
    record: dict[str, Any],
    *,
    acceptance: dict[str, Any] | None = None,
    authority: dict[str, Any] | None = None,
    root: Path = ROOT,
) -> None:
    _require(
        record.get("schema") == 1
        and record.get("id")
        == "mattpocock-skills-v1.2.3-exact-pin-reconciliation-event-v1"
        and record.get("asOf") == "2026-08-08"
        and record.get("status")
        == "exact-v1.2.3-source-metadata-pin-reconciled-payloads-and-projections-unchanged-restart-persistent",
        "Matt v1.2.3 exact-pin event identity drifted",
    )

    source = record.get("source", {})
    _require(
        source.get("releaseTag") == "v1.2.3"
        and source.get("annotatedTagObject")
        == "835450ef244ab7335f75d95b83e7d979eae22a6d"
        and source.get("releaseCommit") == RELEASE_COMMIT
        and source.get("observedMainRevision")
        == "84fdeffd12f2ee307994d1eb6feb48173b6e0502"
        and source.get("tagObjectPeelsToReleaseCommit") is True
        and source.get("observedMainEqualsReleaseCommit") is False
        and source.get("freshRemoteRefCheckPerformed") is True
        and source.get("thirdPartyCodeExecuted") is False,
        "Matt v1.2.3 exact source binding drifted",
    )

    authorization = record.get("authorization", {})
    _require(
        authorization.get("ownerAuthorizedExactPinAlignment") is True
        and authorization.get("ccSwitchSourceMetadataMutationAuthorized") is True
        and authorization.get("managerQuiesceAndRestartAuthorizedAsTransactionMechanics")
        is True
        and all(
            authorization.get(key) is False
            for key in (
                "payloadRewriteAuthorized",
                "consumerMutationAuthorized",
                "enablementMutationAuthorized",
                "installationAuthorized",
                "thirdPartyExecutionAuthorized",
                "modelDispatchAuthorized",
                "accountConnectionAuthorized",
                "broaderConfigurationMutationAuthorized",
            )
        ),
        "Matt v1.2.3 exact-pin authority boundary drifted",
    )

    transaction = record.get("transaction", {})
    _require(
        transaction.get("journalStatus") == "committed"
        and transaction.get("sourceRowCount") == 25
        and transaction.get("targetRowsSha256")
        == transaction.get("afterRowsSha256")
        and transaction.get("beforeRowsSha256")
        != transaction.get("afterRowsSha256")
        and transaction.get("changedColumns")
        == ["repo_branch", "readme_url", "updated_at"]
        and transaction.get("beforeRepoBranch") == "main"
        and transaction.get("afterRepoBranch") == "v1.2.3"
        and transaction.get("afterExactTagReadmeUrlCount") == 25
        and transaction.get("managerContentHashTreatment")
        == "opaque-manager-owned-preserved-unchanged"
        and transaction.get("payloadsWritten") is False
        and transaction.get("projectionsWritten") is False
        and transaction.get("enabledFlagsWritten") is False
        and transaction.get("rawDatabaseCopied") is False
        and transaction.get("thirdPartyScriptExecutions") == 0
        and transaction.get("modelCalls") == 0,
        "Matt v1.2.3 metadata-only transaction boundary drifted",
    )

    recovery = record.get("recovery", {})
    _require(
        recovery.get("journalContainsExactBeforeAndTargetRows") is True
        and recovery.get("failureAfterDatabaseCommitRollbackTested") is True
        and recovery.get("explicitSyntheticRollbackTested") is True
        and recovery.get("liveRollbackExecuted") is False
        and recovery.get("rollbackRemainsSeparatelyControlled") is True,
        "Matt v1.2.3 recovery boundary drifted",
    )

    verification = record.get("postRestartVerification", {})
    _require(
        verification.get("managerRestarted") is True
        and verification.get("managerVersion") == "3.19.2"
        and verification.get("sourceRowCount") == 25
        and verification.get("databaseRepoBranches") == ["v1.2.3"]
        and verification.get("exactTagReadmeUrlCount") == 25
        and verification.get("enabledCountByHost")
        == {
            "claude": 24,
            "codex": 24,
            "gemini": 0,
            "opencode": 0,
            "hermes": 0,
            "grokbuild": 0,
        }
        and verification.get("wizardEnabled") is False
        and verification.get("allTwentyFivePayloadsMatchV123") is True
        and verification.get("bothV122AndV123PayloadCount") == 20
        and verification.get("v123OnlyPayloadCount") == 5
        and verification.get("consumerRootCount") == 3
        and verification.get("consumerSymlinkCount") == 72
        and verification.get("consumerDirectDirectoryCount") == 0
        and verification.get("singleManagerPayloadRevisionClosureProved") is True
        and verification.get("ssotSnapshotBefore")
        == verification.get("ssotSnapshotAfter"),
        "Matt v1.2.3 post-restart verification drifted",
    )

    report_binding = record.get("report", {})
    report_path = root / REPORT_PATH
    _require(
        record.get("documentation") == DOCUMENTATION_PATH.as_posix()
        and (root / DOCUMENTATION_PATH).is_file()
        and report_binding.get("path") == REPORT_PATH.as_posix()
        and report_path.is_file()
        and hashlib.sha256(report_path.read_bytes()).hexdigest()
        == report_binding.get("fileSha256")
        and report_binding.get("status") == "preview-only-zero-live-mutation",
        "Matt v1.2.3 exact-pin report binding drifted",
    )
    report = json.loads(report_path.read_text(encoding="utf-8"))
    report_body = {key: value for key, value in report.items() if key != "reportSha256"}
    _require(
        _canonical_digest(report_body) == report.get("reportSha256")
        and report.get("reportSha256") == report_binding.get("reportSha256")
        and report.get("sourceProjectionSha256")
        == report_binding.get("sourceProjectionSha256")
        and report.get("liveManager", {}).get("payloadClassificationCounts")
        == {
            "both-prior-and-release": 20,
            "prior-only": 0,
            "release-only": 5,
            "neither": 0,
            "missing": 0,
        }
        and report.get("consumerTopology", {}).get("symlinkCountTotal") == 72
        and report.get("consumerTopology", {}).get("directDirectoryCountTotal") == 0
        and all(value == 0 for value in report.get("executionCounters", {}).values()),
        "Matt v1.2.3 post-restart report content drifted",
    )

    temporary = record.get("temporaryAcquisition", {})
    _require(
        temporary.get("newOperatingSystemTemporaryRoot") is True
        and temporary.get("containedOnlyGitObjectDatabaseAndGeneratedReadOnlyReports")
        is True
        and temporary.get("dependencyOrThirdPartyCodeExecuted") is False
        and temporary.get("cleanup") == "sent-to-windows-recycle-bin"
        and temporary.get("originalPathExistsAfterCleanup") is False
        and temporary.get("recycleBinMatchingNameCount", 0) >= 1
        and temporary.get("cleanupRecoverable") is True,
        "Matt v1.2.3 temporary acquisition cleanup drifted",
    )

    decision = record.get("decision", {})
    _require(
        decision.get("currentExactReleaseAuthority") == f"v1.2.3@{RELEASE_COMMIT}"
        and decision.get("mutableMainNoLongerLiveSourceMetadata") is True
        and decision.get("payloadRewriteRequired") is False
        and decision.get("wizardMustRemainDisabled") is True
        and decision.get("currentPortfolioAuthorityMustReferenceThisEvent") is True
        and decision.get("behaviorOrValueTrialRequiredForThisProvenanceRepair")
        is False,
        "Matt v1.2.3 exact-pin decision boundary drifted",
    )

    claims = record.get("claimBoundary", {})
    true_claims = {
        "exactReleaseIdentityProved",
        "metadataOnlyPinCommitted",
        "metadataPinPersistenceAfterOrdinaryRestartProved",
        "payloadBytesUnchangedByTransactionProved",
        "consumerProjectionsUnchangedByTransactionProved",
        "enabledStateUnchangedByTransactionProved",
        "recoveryJournalAvailable",
        "failureInjectionRollbackProved",
    }
    _require(
        all(claims.get(key) is True for key in true_claims)
        and all(value is False for key, value in claims.items() if key not in true_claims),
        "Matt v1.2.3 exact-pin claim boundary drifted",
    )

    acceptance_boundary = record.get("acceptanceBoundary", {})
    _require(
        acceptance_boundary.get("verifiedCriteria") == 46
        and acceptance_boundary.get("partialCriteria") == 15
        and acceptance_boundary.get("plannedCriteria") == 0
        and acceptance_boundary.get("criteriaAdvanced") == []
        and set(acceptance_boundary.get("supportsWithoutAssessmentUpgrade", []))
        == SUPPORTS,
        "Matt v1.2.3 acceptance boundary drifted",
    )

    if acceptance is not None:
        evidence = [
            item
            for item in acceptance.get("evidence", [])
            if item.get("id") == EVIDENCE_ID
        ]
        _require(len(evidence) == 1, "Matt v1.2.3 exact-pin evidence registration drifted")
        _require(
            evidence[0].get("path") == RECORD_PATH.as_posix()
            and set(evidence[0].get("supports", [])) == SUPPORTS
            and "no-loader-behavior-value-portability-or-production-proof"
            in evidence[0].get("kind", ""),
            "Matt v1.2.3 exact-pin evidence boundary drifted",
        )
        for criterion in acceptance.get("acceptanceCriteria", []):
            if criterion.get("id") in SUPPORTS:
                _require(
                    criterion.get("assessment") == "partial"
                    and EVIDENCE_ID in criterion.get("evidenceIds", []),
                    "Matt v1.2.3 exact-pin acceptance reverse reference drifted",
                )

    if authority is not None:
        state = authority.get("currentObservedMattSuiteState", {})
        _require(
            authority.get("asOf") == "2026-08-08"
            and state.get("event") == RECORD_PATH.as_posix()
            and state.get("upstreamReleaseTag") == "v1.2.3"
            and state.get("upstreamReleaseCommit") == RELEASE_COMMIT
            and state.get("databaseSourceMetadataPinnedToExactRelease") is True
            and state.get("metadataOnlyExactPinReconciliationExecuted") is True
            and state.get("metadataOnlyExactPinReconciliationRecoverable") is True
            and state.get("payloadBytesWrittenByExactPin") is False
            and state.get("consumerProjectionsWrittenByExactPin") is False
            and state.get("enabledFlagsWrittenByExactPin") is False
            and state.get("failureInjectionRollbackProved") is True
            and state.get("explicitSyntheticRollbackProved") is True
            and state.get("liveRollbackExecuted") is False
            and state.get("exactPinPersistenceAfterOrdinaryRestartProved") is True,
            "current Matt portfolio authority drifted",
        )

    for path in (PLAN_PATH, GOAL_PROMPT_PATH, CONTINUATION_PATH, *README_PATHS):
        text = (root / path).read_text(encoding="utf-8")
        _require(
            RECORD_PATH.as_posix() in text
            or (
                path in README_PATHS
                and "v1.2.3@6acc160e" in text
                and ("metadata-only" in text or "仅元数据" in text)
            ),
            f"Matt v1.2.3 exact-pin projection missing from {path}",
        )
    _require(
        (root / TRANSACTION_SCRIPT_PATH).is_file()
        and (root / TRANSACTION_TEST_PATH).is_file(),
        "Matt v1.2.3 exact-pin transaction implementation is missing",
    )


def validate_repository_reconciliation(root: Path = ROOT) -> dict[str, Any]:
    record = json.loads((root / RECORD_PATH).read_text(encoding="utf-8"))
    acceptance = json.loads((root / ACCEPTANCE_PATH).read_text(encoding="utf-8"))
    authority = json.loads((root / AUTHORITY_PATH).read_text(encoding="utf-8"))
    validate_record(record, acceptance=acceptance, authority=authority, root=root)
    return record


def main() -> int:
    validate_repository_reconciliation(ROOT)
    print("Matt Pocock Skills v1.2.3 exact-pin reconciliation validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
