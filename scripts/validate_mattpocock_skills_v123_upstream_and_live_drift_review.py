#!/usr/bin/env python3
"""Validate the Matt Pocock Skills v1.2.3 upstream and live-drift review."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
RECORD_PATH = Path(
    "registry/mattpocock-skills-v1.2.3-upstream-and-live-drift-review-2026-08-07.json"
)
REPORT_PATH = Path(
    "audits/mattpocock-skills/6acc160e4e0cd062dbbbd7a1b26ae92855edf07e/"
    "manifest-update-preview-2026-08-07/REPORT.json"
)
DOCUMENTATION_PATH = Path(
    "docs/strategy/MATTPOCOCK-SKILLS-V1.2.3-UPSTREAM-DELTA-2026-08-07.md"
)
ACCEPTANCE_PATH = Path("registry/program-acceptance-map.json")
PLAN_PATH = Path("docs/strategy/RESEARCH-AND-POC-PLAN.md")
GOAL_PROMPT_PATH = Path("docs/operations/CURRENT-GOAL-MODE-PROMPT.md")
EVIDENCE_ID = "evidence.mattpocock-skills-v1.2.3-upstream-and-live-drift-review-2026-08-07"
RELEASE_COMMIT = "6acc160e4e0cd062dbbbd7a1b26ae92855edf07e"
MAIN_COMMIT = "84fdeffd12f2ee307994d1eb6feb48173b6e0502"
RELEASE_CHANGED_SKILLS = {
    "code-review",
    "codebase-design",
    "diagnosing-bugs",
    "improve-codebase-architecture",
    "wizard",
}
SUPPORTS = {
    "acceptance.cc-switch-source-preserving-skill-pool",
    "acceptance.consumer-mapping-evidence",
}


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def _canonical_digest(value: Any) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def validate_record(
    record: dict[str, Any],
    *,
    acceptance: dict[str, Any] | None = None,
    root: Path = ROOT,
) -> None:
    _require(
        record.get("schema") == 1
        and record.get("id")
        == "mattpocock-skills-v1.2.3-upstream-and-live-drift-review-v1"
        and record.get("asOf") == "2026-08-07"
        and record.get("status")
        == "exact-release-reviewed-live-payloads-match-release-mutable-main-metadata-drift-held",
        "Matt v1.2.3 review identity drifted",
    )

    source = record.get("source", {})
    _require(
        source.get("releaseTag") == "v1.2.3"
        and source.get("releaseCommit") == RELEASE_COMMIT
        and source.get("observedMainRevision") == MAIN_COMMIT
        and source.get("tagObjectPeelsToReleaseCommit") is True
        and source.get("priorIsAncestorOfRelease") is True
        and source.get("observedMainEqualsReleaseCommit") is False,
        "Matt v1.2.3 source binding drifted",
    )

    delta = record.get("releaseDelta", {})
    _require(
        delta.get("commitCount") == 11
        and delta.get("changedFileCount") == 11
        and delta.get("promotedSkillCountBefore") == 25
        and delta.get("promotedSkillCountAfter") == 25
        and delta.get("recursiveSkillCountBefore") == 35
        and delta.get("recursiveSkillCountAfter") == 35
        and set(delta.get("changedPromotedSkills", [])) == RELEASE_CHANGED_SKILLS
        and delta.get("addedPromotedSkills") == []
        and delta.get("removedPromotedSkills") == [],
        "Matt v1.2.3 release delta drifted",
    )

    live = record.get("liveObservation", {})
    _require(
        live.get("databaseReadOnly") is True
        and live.get("databaseRepoBranch") == "main"
        and live.get("databaseSourceRowCount") == 25
        and live.get("bothV122AndV123PayloadCount") == 20
        and live.get("v123OnlyPayloadCount") == 5
        and set(live.get("v123OnlyPayloadNames", [])) == RELEASE_CHANGED_SKILLS
        and live.get("allTwentyFivePayloadsMatchV123") is True
        and live.get("consumerRootCount") == 3
        and live.get("consumerSymlinkCount") == 72
        and live.get("consumerDirectDirectoryCount") == 0
        and live.get("singleManagerPayloadRevisionClosureProved") is True
        and live.get("wizardEnabled") is False
        and live.get("updateTriggerOrActor") == "unattributed"
        and live.get("ccSwitchOrConsumerMutationPerformedByThisReview") is False,
        "Matt v1.2.3 live observation drifted",
    )
    temporary = record.get("temporaryAcquisition", {})
    _require(
        temporary.get("newOperatingSystemTemporaryRoot") is True
        and temporary.get("containedOnlyGitObjectDatabase") is True
        and temporary.get("dependencyOrThirdPartyCodeExecuted") is False
        and temporary.get("originalPathExistsAfterCleanup") is False
        and temporary.get("cleanup") == "sent-to-windows-recycle-bin"
        and temporary.get("cleanupRecoverable") is True,
        "Matt v1.2.3 temporary acquisition boundary drifted",
    )

    report_binding = record.get("report", {})
    report_path = root / REPORT_PATH
    _require(
        record.get("documentation") == DOCUMENTATION_PATH.as_posix()
        and (root / DOCUMENTATION_PATH).is_file()
        and report_binding.get("path") == REPORT_PATH.as_posix()
        and report_path.is_file()
        and hashlib.sha256(report_path.read_bytes()).hexdigest()
        == report_binding.get("fileSha256"),
        "Matt v1.2.3 report or documentation binding drifted",
    )
    report = json.loads(report_path.read_text(encoding="utf-8"))
    report_body = {key: value for key, value in report.items() if key != "reportSha256"}
    _require(
        _canonical_digest(report_body) == report.get("reportSha256")
        and report.get("reportSha256") == report_binding.get("reportSha256")
        and report.get("sourceProjectionSha256")
        == report_binding.get("sourceProjectionSha256"),
        "Matt v1.2.3 report digest drifted",
    )

    decision = record.get("decision", {})
    _require(
        decision.get("exactReleaseSelectedForGovernance") == f"v1.2.3@{RELEASE_COMMIT}"
        and decision.get("securityAndPortabilityDeltaWorthRetaining") is True
        and decision.get("blindRefreshAllowed") is False
        and decision.get("perSkillBestEffortRefreshAllowed") is False
        and decision.get("mutableMainAllowedAsDurablePin") is False
        and decision.get("managerReconciliationAuthorized") is False
        and decision.get("payloadRewriteNeededIfCurrentIdentityHolds") is False
        and decision.get("wizardMustRemainDisabled") is True
        and "separate owner authority" in decision.get("nextGate", ""),
        "Matt v1.2.3 decision boundary drifted",
    )

    authority = record.get("authorityBoundary", {})
    _require(
        authority.get("readOnlyUpstreamReviewAuthorized") is True
        and authority.get("repositoryEvidenceWriteAuthorized") is True
        and authority.get("temporaryExactSourceAcquisitionAndRecoverableCleanupAuthorized")
        is True
        and all(
            authority.get(key) is False
            for key in (
                "ccSwitchMutationAuthorized",
                "consumerMutationAuthorized",
                "installationAuthorized",
                "enablementAuthorized",
                "thirdPartyExecutionAuthorized",
                "modelDispatchAuthorized",
                "accountConnectionAuthorized",
                "configurationMutationAuthorized",
            )
        ),
        "Matt v1.2.3 authority boundary drifted",
    )
    claims = record.get("claimBoundary", {})
    true_claims = {
        "exactReleaseIdentityProved",
        "releaseDeltaStaticallyReviewed",
        "livePayloadIdentityAtObservationProved",
        "mutableMainMetadataDriftObserved",
    }
    _require(
        all(claims.get(key) is True for key in true_claims)
        and all(value is False for key, value in claims.items() if key not in true_claims),
        "Matt v1.2.3 claim boundary drifted",
    )

    if acceptance is not None:
        matches = [
            item
            for item in acceptance.get("evidence", [])
            if item.get("id") == EVIDENCE_ID
        ]
        _require(len(matches) == 1, "Matt v1.2.3 acceptance evidence registration drifted")
        evidence = matches[0]
        _require(
            evidence.get("path") == RECORD_PATH.as_posix()
            and set(evidence.get("supports", [])) == SUPPORTS
            and "no-behavior-value-or-update-trigger-proof" in evidence.get("kind", ""),
            "Matt v1.2.3 acceptance evidence boundary drifted",
        )
        for criterion in acceptance.get("acceptanceCriteria", []):
            if criterion.get("id") in SUPPORTS:
                _require(
                    EVIDENCE_ID in criterion.get("evidenceIds", []),
                    "Matt v1.2.3 acceptance criterion reverse reference drifted",
                )

    for path, label in ((PLAN_PATH, "plan"), (GOAL_PROMPT_PATH, "goal prompt")):
        text = (root / path).read_text(encoding="utf-8")
        lowered = text.lower()
        _require(
            RECORD_PATH.as_posix() in text
            and RELEASE_COMMIT in text
            and "mutable `main`" in lowered
            and "no behavior" in lowered,
            f"Matt v1.2.3 {label} projection drifted",
        )


def validate_repository_review(root: Path = ROOT) -> dict[str, Any]:
    record = json.loads((root / RECORD_PATH).read_text(encoding="utf-8"))
    acceptance = json.loads((root / ACCEPTANCE_PATH).read_text(encoding="utf-8"))
    validate_record(record, acceptance=acceptance, root=root)
    return record


def main() -> int:
    validate_repository_review(ROOT)
    print("Matt Pocock Skills v1.2.3 upstream and live-drift review validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
