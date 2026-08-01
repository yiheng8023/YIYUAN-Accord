#!/usr/bin/env python3
"""Validate independent-review readiness and any later review receipt."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable

try:
    from .build_multidimensional_software_engineering_independent_review_packet import (
        CONTRACT_PATH,
        PACKET_PATH,
        ROOT,
        IndependentReviewPacketError,
        build_packet,
        canonical_sha256,
        file_sha256,
        validate_contract,
        _parse_timestamp,
    )
except ImportError:  # pragma: no cover - direct script execution
    from build_multidimensional_software_engineering_independent_review_packet import (
        CONTRACT_PATH,
        PACKET_PATH,
        ROOT,
        IndependentReviewPacketError,
        build_packet,
        canonical_sha256,
        file_sha256,
        validate_contract,
        _parse_timestamp,
    )


DOCUMENT_PATH = (
    ROOT
    / "docs/strategy/"
    "MULTIDIMENSIONAL-SOFTWARE-ENGINEERING-INDEPENDENT-REVIEW-READINESS-"
    "2026-07-31.md"
)
PROGRAM_PLAN_PATH = ROOT / "registry/curation-program-plan.json"
PROGRAM_MAP_PATH = ROOT / "registry/program-acceptance-map.json"
EVIDENCE_ID = (
    "evidence.multidimensional-software-engineering-independent-review-"
    "readiness-2026-07-31"
)
EXPECTED_ACCEPTANCE_ID = "acceptance.standard-candidate-contract"


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise IndependentReviewPacketError(message)


def _load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    _require(isinstance(value, dict), f"{path.name} must contain one object")
    return value


def validate_packet_integrity(
    packet: dict[str, Any] | None = None,
    *,
    root: Path = ROOT,
    check_projections: bool = True,
) -> None:
    """Validate the retained packet without requiring historical Git objects."""

    root = root.resolve()
    contract = _load(root / CONTRACT_PATH)
    validate_contract(contract)
    packet = packet or _load(root / PACKET_PATH)
    _require(
        set(packet)
        == {
            "schema",
            "id",
            "asOf",
            "status",
            "contractBinding",
            "targetBinding",
            "subjectPackages",
            "producerBoundary",
            "reviewAxes",
            "receiptContract",
            "packetState",
            "reproduction",
            "claimBoundary",
            "authorityBoundary",
            "packetSha256",
        },
        "Independent-review packet top-level field set drifted",
    )
    _require(
        packet.get("schema") == 1
        and packet.get("id")
        == (
            "multidimensional-software-engineering-independent-review-packet-"
            "2026-07-31"
        )
        and packet.get("asOf") == contract["asOf"]
        and packet.get("status") == "prepared-not-reviewed-deferred",
        "Independent-review packet identity drifted",
    )
    _require(
        packet.get("contractBinding")
        == {
            "path": CONTRACT_PATH.as_posix(),
            "sha256": file_sha256(root / CONTRACT_PATH),
        },
        "Independent-review contract binding drifted",
    )
    for field in (
        "subjectPackages",
        "producerBoundary",
        "reviewAxes",
        "receiptContract",
        "packetState",
        "claimBoundary",
        "authorityBoundary",
    ):
        _require(
            packet.get(field) == contract[field],
            f"Independent-review packet contract projection drifted: {field}",
        )
    digest = packet.get("packetSha256")
    _require(
        isinstance(digest, str)
        and digest
        == canonical_sha256(
            {
                key: value
                for key, value in packet.items()
                if key != "packetSha256"
            }
        ),
        "Independent-review packet digest drifted",
    )
    target = packet.get("targetBinding", {})
    files = target.get("files", [])
    _require(
        target.get("revision") == contract["targetRevision"]
        and target.get("pathCount") == len(contract["targetPaths"])
        and isinstance(files, list)
        and len(files) == len(contract["targetPaths"])
        and [item.get("path") for item in files] == contract["targetPaths"],
        "Independent-review target binding drifted",
    )
    for item in files:
        _require(
            set(item)
            == {
                "path",
                "mode",
                "objectType",
                "gitObjectId",
                "contentSha256",
            }
            and item.get("mode") == "100644"
            and item.get("objectType") == "blob"
            and isinstance(item.get("gitObjectId"), str)
            and len(item["gitObjectId"]) == 40
            and all(
                character in "0123456789abcdef"
                for character in item["gitObjectId"]
            )
            and isinstance(item.get("contentSha256"), str)
            and len(item["contentSha256"]) == 64
            and all(
                character in "0123456789abcdef"
                for character in item["contentSha256"]
            ),
            f"Independent-review target file binding drifted: {item.get('path')}",
        )
    _require(
        target.get("manifestSha256")
        == canonical_sha256(files),
        "Independent-review target manifest digest drifted",
    )
    _require(
        packet.get("reproduction")
        == {
            "requiresRepositoryWithTargetGitObjects": True,
            "networkRequired": False,
            "modelRequired": False,
            "commands": [
                "python -B scripts/build_multidimensional_software_engineering_independent_review_packet.py --check",
                "python -B scripts/validate_multidimensional_software_engineering_independent_review_packet.py",
                "python -B -m unittest tests.test_multidimensional_software_engineering_independent_review_packet",
            ],
        },
        "Independent-review reproduction contract drifted",
    )
    _require(
        packet.get("packetState", {}).get("reviewPerformed") is False
        and packet["packetState"].get("reviewReceiptPath") is None
        and packet["packetState"].get("reviewDeferredUntilCandidateCoverage")
        is True
        and packet["packetState"].get("acceptanceDecisionRequested") is False
        and packet["packetState"].get("modelDispatchPerformed") is False
        and packet["packetState"].get("externalWritePerformed") is False,
        "Independent-review packet falsely claims review or side effects",
    )
    claims = packet.get("claimBoundary", {})
    _require(
        claims.get("provesIndependentReviewPerformed") is False
        and claims.get("provesReviewerIdentityBeyondFutureReceiptEvidence")
        is False
        and claims.get("provesSourceInterpretationCorrect") is False
        and claims.get("provesAssessmentJudgmentsCorrect") is False
        and claims.get("provesBroadPopulationValidity") is False
        and claims.get("provesHardStandardEligibility") is False
        and claims.get("provesEvaluationSkillNecessary") is False
        and claims.get("authorizesAcceptanceOrRelease") is False,
        "Independent-review packet claim boundary drifted",
    )
    if not check_projections:
        return

    program_plan = _load(root / PROGRAM_PLAN_PATH.relative_to(ROOT))
    initiative = next(
        (
            item
            for item in program_plan.get("currentInitiatives", [])
            if item.get("id")
            == "initiative.human-ai-collaboration-coverage-rebaseline"
        ),
        None,
    )
    _require(initiative is not None, "Coverage-rebaseline initiative is missing")
    _require(
        initiative.get(
            "currentMultidimensionalSoftwareEngineeringIndependentReviewContract"
        )
        == CONTRACT_PATH.as_posix()
        and initiative.get(
            "currentMultidimensionalSoftwareEngineeringIndependentReviewPacket"
        )
        == PACKET_PATH.as_posix()
        and initiative.get(
            "currentMultidimensionalSoftwareEngineeringIndependentReviewState"
        )
        == "prepared-not-reviewed-deferred-candidate-coverage-first",
        "Program-plan independent-review projection drifted",
    )

    program_map = _load(root / PROGRAM_MAP_PATH.relative_to(ROOT))
    _require(
        len(program_map.get("acceptanceCriteria", [])) == 61,
        "Independent-review readiness changed the acceptance inventory",
    )
    acceptances = {
        item.get("id"): item for item in program_map.get("acceptanceCriteria", [])
    }
    _require(
        EXPECTED_ACCEPTANCE_ID in acceptances
        and EVIDENCE_ID
        in acceptances[EXPECTED_ACCEPTANCE_ID].get("evidenceIds", []),
        "Independent-review readiness is not linked to the standard candidate",
    )
    _require(
        acceptances[EXPECTED_ACCEPTANCE_ID].get("assessment") == "partial",
        "Review readiness falsely promoted the standard candidate",
    )
    evidence = {
        item.get("id"): item for item in program_map.get("evidence", [])
    }
    _require(EVIDENCE_ID in evidence, "Review-readiness evidence is missing")
    _require(
        evidence[EVIDENCE_ID].get("path") == PACKET_PATH.as_posix()
        and evidence[EVIDENCE_ID].get("supports") == [EXPECTED_ACCEPTANCE_ID],
        "Review-readiness evidence projection drifted",
    )

    document = (
        root
        / DOCUMENT_PATH.relative_to(ROOT)
    ).read_text(encoding="utf-8")
    normalized = " ".join(document.split())
    for phrase in (
        "Preparation is not review",
        "Different execution identity",
        "Rights, evidence, conflict, and affected-party review",
        "No review receipt is generated",
        "does not authorize acceptance",
        "No new evaluation Skill is justified",
    ):
        _require(
            phrase in normalized,
            f"Independent-review readiness document missing: {phrase}",
        )


def validate_packet(
    packet: dict[str, Any] | None = None,
    *,
    root: Path = ROOT,
    check_projections: bool = True,
) -> None:
    """Validate retained integrity and rederive the manifest from Git objects."""

    root = root.resolve()
    packet = packet or _load(root / PACKET_PATH)
    validate_packet_integrity(
        packet,
        root=root,
        check_projections=check_projections,
    )
    contract = _load(root / CONTRACT_PATH)
    expected = build_packet(contract, root=root)
    _require(packet == expected, "Independent-review packet differs from rebuild")


def validate_review_receipt(
    receipt: dict[str, Any],
    *,
    packet: dict[str, Any] | None = None,
    contract: dict[str, Any] | None = None,
    root: Path = ROOT,
    packet_builder: Callable[..., dict[str, Any]] = build_packet,
    contract_validator: Callable[[dict[str, Any]], None] = validate_contract,
) -> None:
    """Validate a later receipt without treating it as acceptance.

    Identity evidence remains declarative unless a future host or accountable
    authority supplies stronger receipts.  This validator proves contract
    shape and explicit separation, not the truth of a reviewer's declaration.
    """

    root = root.resolve()
    contract = contract or _load(root / CONTRACT_PATH)
    packet = packet or _load(root / PACKET_PATH)
    contract_validator(contract)
    _require(
        packet == packet_builder(contract, root=root),
        "Review receipt references a stale packet",
    )
    receipt_contract = contract["receiptContract"]
    _require(
        set(receipt) == set(receipt_contract["requiredTopLevelFields"]),
        "Review receipt top-level field set drifted",
    )
    _require(receipt.get("schema") == 1, "Review receipt schema drifted")
    _require(
        isinstance(receipt.get("id"), str) and bool(receipt["id"]),
        "Review receipt identity is missing",
    )
    packet_binding_matches = (
        receipt.get("packetId") == packet["id"]
        and receipt.get("packetManifestSha256")
        == packet["targetBinding"]["manifestSha256"]
    )
    if "packetSha256" in receipt_contract["requiredTopLevelFields"]:
        packet_binding_matches = (
            packet_binding_matches
            and receipt.get("packetSha256") == packet.get("packetSha256")
        )
    _require(packet_binding_matches, "Review receipt packet binding drifted")
    _require(
        receipt.get("reviewStatus") in receipt_contract["allowedReviewStatus"],
        "Review receipt status drifted",
    )
    _parse_timestamp(receipt.get("reviewedAt"), label="reviewedAt")

    reviewer = receipt.get("reviewer", {})
    _require(
        set(reviewer) == {"identity", "kind", "accountableForReview"}
        and isinstance(reviewer.get("identity"), str)
        and bool(reviewer["identity"])
        and isinstance(reviewer.get("kind"), str)
        and bool(reviewer["kind"])
        and reviewer.get("accountableForReview") is True,
        "Review receipt reviewer identity is incomplete",
    )
    producer = contract["producerBoundary"]
    blocked_identities = {
        producer["packetProducerIdentity"],
        *producer["reportEvaluatorIdentities"],
    }
    _require(
        reviewer["identity"] not in blocked_identities,
        "Review receipt reuses a producer or evaluator identity",
    )

    independence = receipt.get("independence", {})
    _require(
        set(independence)
        == {
            "processId",
            "distinctExecutionIdentity",
            "sameTaskOrThread",
            "priorInvolvementDisclosure",
            "identityEvidence",
            "privateReasoningTransferReceived",
            "artifactMutationPerformed",
        },
        "Review receipt independence field set drifted",
    )
    _require(
        isinstance(independence.get("processId"), str)
        and bool(independence["processId"])
        and independence["processId"] != producer["packetProducerProcessId"],
        "Review receipt process identity is missing or not distinct",
    )
    _require(
        independence.get("distinctExecutionIdentity") is True
        and independence.get("sameTaskOrThread") is False
        and independence.get("privateReasoningTransferReceived") is False
        and independence.get("artifactMutationPerformed") is False,
        "Review receipt independence declaration failed",
    )
    _require(
        isinstance(independence.get("priorInvolvementDisclosure"), str)
        and bool(independence["priorInvolvementDisclosure"]),
        "Review receipt prior-involvement disclosure is missing",
    )
    _require(
        isinstance(independence.get("identityEvidence"), list)
        and bool(independence["identityEvidence"])
        and all(
            isinstance(item, str) and bool(item)
            for item in independence["identityEvidence"]
        ),
        "Review receipt identity evidence is missing",
    )

    axis_ids = {item["id"] for item in contract["reviewAxes"]}
    manifest_paths = {
        item["path"] for item in packet["targetBinding"]["files"]
    }
    axis_results = receipt.get("axisResults")
    _require(
        isinstance(axis_results, list)
        and len(axis_results) == len(axis_ids)
        and {item.get("axisId") for item in axis_results} == axis_ids,
        "Review receipt does not cover every axis exactly once",
    )
    for result in axis_results:
        _require(
            set(result)
            == {"axisId", "outcome", "summary", "evidenceRefs", "limitations"},
            f"Review axis result fields drifted: {result.get('axisId')}",
        )
        _require(
            result["outcome"] in receipt_contract["allowedAxisOutcomes"]
            and isinstance(result["summary"], str)
            and bool(result["summary"])
            and isinstance(result["evidenceRefs"], list)
            and bool(result["evidenceRefs"])
            and all(
                isinstance(item, str)
                and bool(item)
                and item in manifest_paths
                for item in result["evidenceRefs"]
            )
            and isinstance(result["limitations"], list),
            (
                "Review axis result is incomplete or references evidence "
                f"outside the packet manifest: {result['axisId']}"
            ),
        )

    findings = receipt.get("findings")
    _require(isinstance(findings, list), "Review findings are missing")
    finding_ids: set[str] = set()
    for finding in findings:
        _require(
            set(finding)
            == {
                "id",
                "axisId",
                "severity",
                "statement",
                "evidenceRefs",
                "disposition",
            },
            "Review finding fields drifted",
        )
        _require(
            isinstance(finding["id"], str)
            and bool(finding["id"])
            and finding["id"] not in finding_ids,
            "Review finding ids are missing or duplicated",
        )
        finding_ids.add(finding["id"])
        _require(
            finding["axisId"] in axis_ids
            and finding["severity"]
            in receipt_contract["allowedFindingSeverities"]
            and isinstance(finding["statement"], str)
            and bool(finding["statement"])
            and isinstance(finding["evidenceRefs"], list)
            and bool(finding["evidenceRefs"])
            and all(
                isinstance(item, str)
                and bool(item)
                and item in manifest_paths
                for item in finding["evidenceRefs"]
            )
            and isinstance(finding["disposition"], str),
            f"Review finding is incomplete: {finding['id']}",
        )
        if finding["severity"] in {"high", "critical"}:
            _require(
                bool(finding["disposition"]),
                f"High-severity review finding lacks disposition: {finding['id']}",
            )

    disagreements = receipt.get("disagreements")
    _require(isinstance(disagreements, list), "Review disagreements are hidden")
    for disagreement in disagreements:
        _require(
            set(disagreement)
            == {"id", "statement", "evidenceRefs", "disposition"}
            and isinstance(disagreement["id"], str)
            and bool(disagreement["id"])
            and isinstance(disagreement["statement"], str)
            and bool(disagreement["statement"])
            and isinstance(disagreement["evidenceRefs"], list)
            and bool(disagreement["evidenceRefs"])
            and all(
                isinstance(item, str)
                and bool(item)
                and item in manifest_paths
                for item in disagreement["evidenceRefs"]
            )
            and isinstance(disagreement["disposition"], str),
            "Review disagreement record is incomplete",
        )

    corrections = receipt.get("correctionsRequired")
    _require(isinstance(corrections, list), "Review corrections are missing")
    correction_fields = set(
        receipt_contract.get(
            "correctionRecordFields",
            ["id", "axisId", "statement", "evidenceRefs"],
        )
    )
    correction_ids: set[str] = set()
    for correction in corrections:
        _require(
            set(correction) == correction_fields
            and isinstance(correction["id"], str)
            and bool(correction["id"])
            and correction["id"] not in correction_ids
            and correction["axisId"] in axis_ids
            and isinstance(correction["statement"], str)
            and bool(correction["statement"])
            and isinstance(correction["evidenceRefs"], list)
            and bool(correction["evidenceRefs"])
            and all(
                isinstance(item, str)
                and bool(item)
                and item in manifest_paths
                for item in correction["evidenceRefs"]
            ),
            "Review correction record is incomplete or outside the packet manifest",
        )
        correction_ids.add(correction["id"])
    correction_axis_ids = {correction["axisId"] for correction in corrections}
    required_correction_axis_ids = {
        result["axisId"]
        for result in axis_results
        if result["outcome"] == "accept-with-corrections"
    }
    _require(
        required_correction_axis_ids <= correction_axis_ids,
        "Review correction record does not cover each axis requiring correction",
    )
    _require(
        receipt.get("overallOutcome")
        in receipt_contract["allowedOverallOutcomes"],
        "Review overall outcome drifted",
    )
    corrections_required = (
        receipt["overallOutcome"] == "accept-with-corrections"
        or any(
            result["outcome"] == "accept-with-corrections"
            for result in axis_results
        )
    )
    _require(
        not corrections_required or bool(corrections),
        "Review accept-with-corrections requires a correction record",
    )
    _require(
        not corrections or receipt["overallOutcome"] != "accept-bounded",
        "Review correction records cannot be hidden by accept-bounded",
    )
    outcome_strength = {
        "accept-bounded": 0,
        "accept-with-corrections": 1,
        "insufficient-evidence": 2,
        "reject": 3,
    }
    weakest_axis = max(
        outcome_strength[result["outcome"]] for result in axis_results
    )
    _require(
        outcome_strength[receipt["overallOutcome"]] >= weakest_axis,
        "Review overall outcome cancels a weaker axis",
    )
    _require(
        receipt["overallOutcome"] != "accept-bounded"
        or not any(
            finding["severity"] in {"high", "critical"}
            for finding in findings
        ),
        "Review cannot accept-bounded with a high or critical finding",
    )
    _require(
        isinstance(receipt.get("limitations"), list)
        and bool(receipt["limitations"])
        and all(
            isinstance(item, str) and bool(item)
            for item in receipt["limitations"]
        ),
        "Review receipt limitations are missing",
    )
    claims = receipt.get("claimBoundary", {})
    expected_claims = receipt_contract.get(
        "requiredClaimBoundary",
        {
            "acceptanceAuthorityExercised": False,
            "hardStandardPromoted": False,
            "skillNecessityProved": False,
            "broadPopulationValidityProved": False,
            "independentReviewProvedBeyondDeclaredIdentityEvidence": False,
        },
    )
    _require(
        claims == expected_claims,
        "Review receipt exceeded review authority",
    )


def main() -> int:
    validate_packet()
    print("Independent-review readiness validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
