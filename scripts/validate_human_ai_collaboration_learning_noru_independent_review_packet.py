#!/usr/bin/env python3
"""Validate the frozen Noru independent-review readiness packet."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

try:
    from .build_human_ai_collaboration_learning_noru_independent_review_packet import (
        CONTRACT_PATH,
        PACKET_PATH,
        ROOT,
        LearningNoruIndependentReviewPacketError,
        build_packet,
        validate_contract,
    )
    from .build_multidimensional_software_engineering_independent_review_packet import (
        canonical_sha256,
        file_sha256,
    )
    from .validate_multidimensional_software_engineering_independent_review_packet import (
        validate_review_receipt as validate_generic_review_receipt,
    )
except ImportError:  # pragma: no cover - direct script execution
    from build_human_ai_collaboration_learning_noru_independent_review_packet import (
        CONTRACT_PATH,
        PACKET_PATH,
        ROOT,
        LearningNoruIndependentReviewPacketError,
        build_packet,
        validate_contract,
    )
    from build_multidimensional_software_engineering_independent_review_packet import (
        canonical_sha256,
        file_sha256,
    )
    from validate_multidimensional_software_engineering_independent_review_packet import (
        validate_review_receipt as validate_generic_review_receipt,
    )


DOCUMENT_PATH = Path(
    "docs/strategy/HUMAN-AI-COLLABORATION-LEARNING-NORU-INDEPENDENT-"
    "REVIEW-READINESS-2026-08-01.md"
)
PROGRAM_PLAN_PATH = Path("registry/curation-program-plan.json")
PROGRAM_MAP_PATH = Path("registry/program-acceptance-map.json")
EVIDENCE_ID = (
    "evidence.human-ai-collaboration-learning-noru-independent-review-"
    "readiness-2026-08-01"
)
EXPECTED_ACCEPTANCE_IDS = {
    "acceptance.solution-neutral-collaboration-rebaseline",
    "acceptance.residual-gap-proof",
}
LEARNING_NORU_INDEPENDENT_REVIEW_REQUIRED_FILES = (
    CONTRACT_PATH.as_posix(),
    PACKET_PATH.as_posix(),
    DOCUMENT_PATH.as_posix(),
    "scripts/build_human_ai_collaboration_learning_noru_independent_review_packet.py",
    "scripts/validate_human_ai_collaboration_learning_noru_independent_review_packet.py",
    "tests/test_human_ai_collaboration_learning_noru_independent_review_packet.py",
)


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise LearningNoruIndependentReviewPacketError(message)


def _load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    _require(isinstance(value, dict), f"Expected one JSON object: {path}")
    return value


def validate_packet(
    packet: dict[str, Any] | None = None,
    *,
    root: Path = ROOT,
) -> None:
    root = root.resolve()
    contract = _load(root / CONTRACT_PATH)
    validate_contract(contract)
    packet = packet or _load(root / PACKET_PATH)
    _require(
        set(packet)
        == {
            "schema",
            "id",
            "date",
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
        "Noru independent-review packet top-level field set drifted",
    )
    _require(
        packet.get("schema") == 1
        and packet.get("id")
        == (
            "human-ai-collaboration-learning-noru-independent-review-"
            "packet-2026-08-01"
        )
        and packet.get("date") == "2026-08-01"
        and packet.get("status")
        == "prepared-not-reviewed-live-trial-blocked",
        "Noru independent-review packet identity drifted",
    )
    _require(
        packet.get("contractBinding")
        == {
            "path": CONTRACT_PATH.as_posix(),
            "sha256": file_sha256(root / CONTRACT_PATH),
        },
        "Noru independent-review contract binding drifted",
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
            f"Noru independent-review contract projection drifted: {field}",
        )
    digest = packet.get("packetSha256")
    _require(
        isinstance(digest, str)
        and digest
        == canonical_sha256(
            {key: value for key, value in packet.items() if key != "packetSha256"}
        ),
        "Noru independent-review packet digest drifted",
    )
    target = packet.get("targetBinding", {})
    files = target.get("files", [])
    _require(
        target.get("revision") == contract["targetRevision"]
        and target.get("pathCount") == len(contract["targetPaths"])
        and isinstance(files, list)
        and [row.get("path") for row in files] == contract["targetPaths"]
        and target.get("manifestSha256") == canonical_sha256(files),
        "Noru independent-review target binding drifted",
    )
    for row in files:
        _require(
            set(row)
            == {"path", "mode", "objectType", "gitObjectId", "contentSha256"}
            and row.get("mode") == "100644"
            and row.get("objectType") == "blob"
            and isinstance(row.get("gitObjectId"), str)
            and len(row["gitObjectId"]) == 40
            and isinstance(row.get("contentSha256"), str)
            and len(row["contentSha256"]) == 64,
            f"Noru independent-review target file binding drifted: {row.get('path')}",
        )
    _require(
        packet.get("reproduction")
        == {
            "requiresRepositoryWithTargetGitObjects": True,
            "networkRequired": False,
            "modelRequired": False,
            "commands": [
                "python -B scripts/build_human_ai_collaboration_learning_noru_independent_review_packet.py --check",
                "python -B scripts/validate_human_ai_collaboration_learning_noru_independent_review_packet.py",
                "python -B -m unittest tests.test_human_ai_collaboration_learning_noru_independent_review_packet",
            ],
        },
        "Noru independent-review reproduction contract drifted",
    )
    _require(
        packet == build_packet(contract, root=root),
        "Noru independent-review packet differs from exact Git rebuild",
    )
    plan = _load(root / PROGRAM_PLAN_PATH)
    initiatives = {
        row.get("id"): row for row in plan.get("currentInitiatives", [])
    }
    for initiative_id in {
        "initiative.capability-survey-gap-proof",
        "initiative.human-ai-collaboration-coverage-rebaseline",
    }:
        initiative = initiatives.get(initiative_id, {})
        _require(
            initiative.get("currentLearningIndependentReviewReadinessContract")
            == CONTRACT_PATH.as_posix()
            and initiative.get("currentLearningIndependentReviewPacket")
            == PACKET_PATH.as_posix()
            and initiative.get("currentLearningIndependentReviewState")
            == "prepared-not-reviewed-live-trial-blocked",
            f"Noru independent-review program projection drifted: {initiative_id}",
        )
    program = _load(root / PROGRAM_MAP_PATH)
    criteria = {
        row.get("id"): row for row in program.get("acceptanceCriteria", [])
    }
    for acceptance_id in EXPECTED_ACCEPTANCE_IDS:
        criterion = criteria.get(acceptance_id, {})
        _require(
            criterion.get("assessment") == "partial"
            and EVIDENCE_ID in criterion.get("evidenceIds", []),
            f"Noru independent-review acceptance mapping drifted: {acceptance_id}",
        )
    evidence = {row.get("id"): row for row in program.get("evidence", [])}
    _require(
        evidence.get(EVIDENCE_ID)
        == {
            "id": EVIDENCE_ID,
            "path": PACKET_PATH.as_posix(),
            "kind": (
                "exact-git-object-bound-learning-material-independent-review-"
                "readiness-packet-review-not-performed-live-trial-blocked-no-"
                "value-or-residual-gap-promotion"
            ),
            "asOf": "2026-08-01",
            "supports": [
                "acceptance.solution-neutral-collaboration-rebaseline",
                "acceptance.residual-gap-proof",
            ],
        },
        "Noru independent-review acceptance evidence drifted",
    )
    document = (root / DOCUMENT_PATH).read_text(encoding="utf-8")
    normalized = " ".join(document.split())
    for phrase in (
        "Preparation is not review",
        "all ten axes exactly once",
        "No independent review has been performed",
        "Both linked program acceptances remain `partial`",
        "Even a valid review receipt cannot authorize a pilot",
    ):
        _require(
            phrase in normalized,
            f"Noru independent-review document missing: {phrase}",
        )


def validate_review_receipt(
    receipt: dict[str, Any],
    *,
    packet: dict[str, Any] | None = None,
    contract: dict[str, Any] | None = None,
    root: Path = ROOT,
) -> None:
    """Validate a later distinct review receipt without granting live authority."""

    root = root.resolve()
    contract = contract or _load(root / CONTRACT_PATH)
    packet = packet or _load(root / PACKET_PATH)
    validate_generic_review_receipt(
        receipt,
        packet=packet,
        contract=contract,
        root=root,
        packet_builder=build_packet,
        contract_validator=validate_contract,
    )


def main() -> int:
    validate_packet()
    print("Noru independent-review readiness validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
