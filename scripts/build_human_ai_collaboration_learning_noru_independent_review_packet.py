#!/usr/bin/env python3
"""Build the frozen surface for a later independent Noru material review."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

try:
    from .build_multidimensional_software_engineering_independent_review_packet import (
        canonical_sha256,
        file_sha256,
        git_blob_manifest,
    )
except ImportError:  # pragma: no cover - direct script execution
    from build_multidimensional_software_engineering_independent_review_packet import (
        canonical_sha256,
        file_sha256,
        git_blob_manifest,
    )


ROOT = Path(__file__).resolve().parent.parent
CONTRACT_PATH = Path(
    "registry/human-ai-collaboration-learning-noru-independent-review-"
    "readiness-contract-2026-08-01.json"
)
PACKET_PATH = Path(
    "registry/human-ai-collaboration-learning-noru-independent-review-"
    "packet-2026-08-01.json"
)
EXPECTED_REVIEW_AXIS_IDS = {
    "content-and-answer-key-correctness",
    "immediate-delayed-form-balance",
    "misconception-coverage-and-falsifiers",
    "readability-and-instruction-clarity",
    "accessibility-and-accommodation-boundary",
    "public-private-oracle-isolation",
    "cleanup-data-and-participant-safety-boundary",
    "claim-authority-and-live-readiness",
    "deterministic-reproduction-and-negative-controls",
    "capability-reuse-and-residual-gap-boundary",
}
EXPECTED_AUTHORITY_BOUNDARY = {
    "independentReviewerDispatchAuthorized": False,
    "newThreadOrSubagentAuthorized": False,
    "modelOrCandidateExecutionAuthorized": False,
    "officialAccountAccessAuthorized": False,
    "participantContactOrTrialAuthorized": False,
    "externalCapabilityMutationAuthorized": False,
    "ccSwitchOrGlobalConfigMutationAuthorized": False,
    "reviewerMutationOfTargetArtifactsAuthorized": False,
    "hardStandardPromotionAuthorized": False,
    "acceptanceReleaseOrLiveTrialAuthorized": False,
}
EXPECTED_PRODUCER_BOUNDARY = {
    "packetProducerIdentity": (
        "codex-goal-turn-learning-review-packet-producer-2026-08-01"
    ),
    "packetProducerProcessId": (
        "codex-thread-019fbc6f-ffcb-76f0-82b2-1f51d60e9028-"
        "learning-review-preparation"
    ),
    "reportEvaluatorIdentities": [
        "current-task Noru material and oracle producer",
        "current-task deterministic calibration evaluator",
    ],
    "identityEvidenceIsCryptographic": False,
    "sameTaskRereadQualifiesAsIndependentReview": False,
    "reviewSkillInvocationAloneQualifiesAsIndependentReview": False,
    "distinctExecutionIdentityRequired": True,
    "distinctProcessIdRequired": True,
    "privateReasoningTransferAllowed": False,
    "reviewerArtifactMutationAllowed": False,
}
EXPECTED_RECEIPT_CONTRACT = {
    "requiredTopLevelFields": [
        "schema",
        "id",
        "packetId",
        "packetManifestSha256",
        "packetSha256",
        "reviewStatus",
        "reviewedAt",
        "reviewer",
        "independence",
        "axisResults",
        "findings",
        "disagreements",
        "correctionsRequired",
        "overallOutcome",
        "limitations",
        "claimBoundary",
    ],
    "allowedReviewStatus": ["performed"],
    "allowedAxisOutcomes": [
        "accept-bounded",
        "accept-with-corrections",
        "reject",
        "insufficient-evidence",
    ],
    "allowedOverallOutcomes": [
        "accept-bounded",
        "accept-with-corrections",
        "reject",
        "insufficient-evidence",
    ],
    "allowedFindingSeverities": [
        "informational",
        "low",
        "medium",
        "high",
        "critical",
    ],
    "correctionRecordFields": ["id", "axisId", "statement", "evidenceRefs"],
    "allReviewAxesRequiredExactlyOnce": True,
    "overallOutcomeMayNotBeStrongerThanAnyAxis": True,
    "acceptWithCorrectionsRequiresCorrectionRecord": True,
    "everyAcceptWithCorrectionsAxisRequiresCorrectionRecord": True,
    "highOrCriticalFindingBlocksAcceptBounded": True,
    "reviewerIdentityMustDifferFromAllProducerIdentities": True,
    "reviewProcessMustDifferFromProducerProcess": True,
    "priorInvolvementDisclosureRequired": True,
    "identityEvidenceRequired": True,
    "findingEvidenceReferencesRequired": True,
    "highAndCriticalFindingDispositionRequired": True,
    "disagreementsMustRemainVisible": True,
    "acceptanceAuthorityMayBeExercisedByReceipt": False,
    "hardStandardMayBePromotedByReceipt": False,
    "skillNecessityMayBeProvedByReceipt": False,
    "liveTrialMayBeAuthorizedByReceipt": False,
    "requiredClaimBoundary": {
        "acceptanceAuthorityExercised": False,
        "hardStandardPromoted": False,
        "skillNecessityProved": False,
        "liveTrialAuthorized": False,
        "broadPopulationValidityProved": False,
        "independentReviewProvedBeyondDeclaredIdentityEvidence": False,
    },
}
EXPECTED_CLAIM_BOUNDARY = {
    "provesTargetArtifactsFrozen": True,
    "provesManifestRebuildableFromGit": True,
    "provesIndependentReviewPerformed": False,
    "provesReviewerIdentityBeyondFutureReceiptEvidence": False,
    "provesContentAndAnswerKeyCorrect": False,
    "provesHumanReadability": False,
    "provesAccessibilityInUse": False,
    "provesParallelFormDifficultyEquivalence": False,
    "provesParticipantSafeguardsComplete": False,
    "provesLearningEffect": False,
    "provesCandidateValue": False,
    "provesLiveTrialReadiness": False,
    "provesSkillOrHardStandardNeed": False,
    "authorizesAcceptanceReleaseOrLiveTrial": False,
}


class LearningNoruIndependentReviewPacketError(RuntimeError):
    """Raised when the review-readiness surface fails closed."""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise LearningNoruIndependentReviewPacketError(message)


def validate_contract(contract: dict[str, Any]) -> None:
    _require(
        contract.get("schema") == 1
        and contract.get("id")
        == (
            "human-ai-collaboration-learning-noru-independent-review-"
            "readiness-contract-2026-08-01"
        )
        and contract.get("date") == "2026-08-01"
        and contract.get("status")
        == "prepared-not-reviewed-live-trial-blocked",
        "Noru review-readiness contract identity drifted",
    )
    target_paths = contract.get("targetPaths", [])
    _require(
        isinstance(target_paths, list)
        and target_paths
        and target_paths == sorted(set(target_paths)),
        "Noru review target paths must be one sorted unique set",
    )
    subject_paths = [
        path
        for subject in contract.get("subjectPackages", [])
        for path in subject.get("paths", [])
    ]
    _require(
        len(subject_paths) == len(set(subject_paths))
        and set(subject_paths) == set(target_paths),
        "Noru review subject packages do not cover the exact targets",
    )
    _require(
        contract.get("producerBoundary") == EXPECTED_PRODUCER_BOUNDARY,
        "Noru review producer boundary drifted",
    )
    review_axes = contract.get("reviewAxes", [])
    _require(
        isinstance(review_axes, list)
        and len(review_axes) == len(EXPECTED_REVIEW_AXIS_IDS)
        and {row.get("id") for row in review_axes} == EXPECTED_REVIEW_AXIS_IDS
        and all(
            set(row) == {"id", "question"}
            and isinstance(row.get("question"), str)
            and bool(row["question"])
            for row in review_axes
        ),
        "Noru review axes must cover the exact vocabulary exactly once",
    )
    _require(
        contract.get("receiptContract") == EXPECTED_RECEIPT_CONTRACT,
        "Noru review receipt contract drifted",
    )
    _require(
        contract.get("packetState")
        == {
            "reviewPerformed": False,
            "reviewReceiptPath": None,
            "candidateCoveragePrerequisiteSatisfied": True,
            "acceptanceDecisionRequested": False,
            "modelDispatchPerformed": False,
            "participantContactPerformed": False,
            "externalWritePerformed": False,
        },
        "Noru review packet state falsely claims execution",
    )
    _require(
        contract.get("claimBoundary") == EXPECTED_CLAIM_BOUNDARY,
        "Noru review claim boundary drifted",
    )
    _require(
        contract.get("authorityBoundary") == EXPECTED_AUTHORITY_BOUNDARY,
        "Noru review authority boundary drifted",
    )


def _load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    _require(isinstance(value, dict), f"Expected one JSON object: {path}")
    return value


def build_packet(
    contract: dict[str, Any] | None = None,
    *,
    root: Path = ROOT,
) -> dict[str, Any]:
    root = root.resolve()
    contract_path = root / CONTRACT_PATH
    contract = contract or _load(contract_path)
    validate_contract(contract)
    manifest = git_blob_manifest(
        contract["targetRevision"], contract["targetPaths"], root=root
    )
    result = {
        "schema": 1,
        "id": (
            "human-ai-collaboration-learning-noru-independent-review-"
            "packet-2026-08-01"
        ),
        "date": contract["date"],
        "status": "prepared-not-reviewed-live-trial-blocked",
        "contractBinding": {
            "path": CONTRACT_PATH.as_posix(),
            "sha256": file_sha256(contract_path),
        },
        "targetBinding": {
            "revision": contract["targetRevision"],
            "pathCount": len(manifest),
            "manifestSha256": canonical_sha256(manifest),
            "files": manifest,
        },
        "subjectPackages": contract["subjectPackages"],
        "producerBoundary": contract["producerBoundary"],
        "reviewAxes": contract["reviewAxes"],
        "receiptContract": contract["receiptContract"],
        "packetState": contract["packetState"],
        "reproduction": {
            "requiresRepositoryWithTargetGitObjects": True,
            "networkRequired": False,
            "modelRequired": False,
            "commands": [
                "python -B scripts/build_human_ai_collaboration_learning_noru_independent_review_packet.py --check",
                "python -B scripts/validate_human_ai_collaboration_learning_noru_independent_review_packet.py",
                "python -B -m unittest tests.test_human_ai_collaboration_learning_noru_independent_review_packet",
            ],
        },
        "claimBoundary": contract["claimBoundary"],
        "authorityBoundary": contract["authorityBoundary"],
    }
    result["packetSha256"] = canonical_sha256(result)
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--print", action="store_true")
    mode.add_argument("--check", action="store_true")
    arguments = parser.parse_args()
    expected = build_packet()
    if arguments.print:
        print(json.dumps(expected, ensure_ascii=False, indent=2))
        return 0
    actual = _load(ROOT / PACKET_PATH)
    _require(actual == expected, "Checked-in Noru independent-review packet is stale")
    print("Noru independent-review packet is current.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
