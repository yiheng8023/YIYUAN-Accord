#!/usr/bin/env python3
"""Validate the deterministic software-engineering source snapshot."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

try:
    from .build_multidimensional_software_engineering_source_snapshot import (
        ROOT,
        SNAPSHOT_PATH,
        SourceSnapshotError,
        build_snapshot,
        canonical_sha256,
    )
except ImportError:  # pragma: no cover - direct script execution
    from build_multidimensional_software_engineering_source_snapshot import (
        ROOT,
        SNAPSHOT_PATH,
        SourceSnapshotError,
        build_snapshot,
        canonical_sha256,
    )


DOCUMENT_PATH = (
    ROOT
    / "docs/strategy/"
    "MULTIDIMENSIONAL-SOFTWARE-ENGINEERING-SOURCE-SNAPSHOT-2026-07-31.md"
)
PROGRAM_PLAN_PATH = ROOT / "registry/curation-program-plan.json"
PROGRAM_MAP_PATH = ROOT / "registry/program-acceptance-map.json"
EVIDENCE_ID = (
    "evidence.multidimensional-software-engineering-source-snapshot-2026-07-31"
)
EXPECTED_ACCEPTANCE_IDS = {
    "acceptance.software-engineering-lifecycle-specialization",
    "acceptance.end-to-end-process-fidelity",
    "acceptance.ai-independent-hard-standard-boundary",
    "acceptance.standard-candidate-contract",
    "acceptance.adaptive-harness-proportionality",
}


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise SourceSnapshotError(message)


def _load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    _require(isinstance(value, dict), f"{path.name} must contain one object")
    return value


def validate_snapshot(
    snapshot: dict[str, Any] | None = None,
    *,
    root: Path = ROOT,
) -> None:
    root = root.resolve()
    snapshot = snapshot or _load(root / SNAPSHOT_PATH)
    expected = build_snapshot(root=root)
    _require(snapshot == expected, "Source snapshot differs from offline rebuild")
    digest = snapshot.get("manifestSha256")
    _require(
        isinstance(digest, str)
        and digest
        == canonical_sha256(
            {
                key: value
                for key, value in snapshot.items()
                if key != "manifestSha256"
            }
        ),
        "Source snapshot manifest digest drifted",
    )
    _require(
        snapshot.get("summary")
        == {
            "sourceCount": 12,
            "observedCount": 12,
            "metadataOnlyCount": 5,
            "boundedPublicSummaryCount": 6,
            "versionedPublicSpecificationCount": 1,
            "mutableUnpinnedCount": 1,
            "contentArchiveCount": 0,
            "contentDigestCount": 0,
            "conflictSourceCount": 1,
            "partiallyObservedContractStatusCount": 2,
        },
        "Source snapshot summary drifted",
    )
    claims = snapshot.get("claimBoundary", {})
    _require(
        claims.get("recordsModelMediatedLocatorObservationAtObservedTime")
        is True
        and claims.get("provesCurrentLocatorReachabilityAtObservedTime")
        is False
        and claims.get("provesNetworkReceipt") is False
        and claims.get("provesExactExternalContentBytes") is False
        and claims.get("provesFullNormativeText") is False
        and claims.get("provesExternalInterpretationCorrect") is False
        and claims.get("provesParentSourceSetFrozenOffline") is True
        and claims.get("provesOfflineSnapshotRebuild") is True
        and claims.get("provesIndependentReview") is False
        and claims.get("provesEvaluationSkillNecessary") is False
        and claims.get("authorizesHardStandardOrAcceptance") is False,
        "Source snapshot claim boundary drifted",
    )

    program_plan = _load(root / "registry/curation-program-plan.json")
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
        initiative.get("currentMultidimensionalSoftwareEngineeringSourceSnapshot")
        == SNAPSHOT_PATH.as_posix()
        and initiative.get(
            "currentMultidimensionalSoftwareEngineeringSourceRefreshState"
        )
        == "deterministic-offline-snapshot-calibrated-review-deferred-candidate-coverage-first",
        "Program-plan source snapshot projection drifted",
    )

    program_map = _load(root / "registry/program-acceptance-map.json")
    _require(
        len(program_map.get("acceptanceCriteria", [])) == 61,
        "Source snapshot changed the acceptance inventory",
    )
    acceptances = {
        item.get("id"): item
        for item in program_map.get("acceptanceCriteria", [])
    }
    for acceptance_id in EXPECTED_ACCEPTANCE_IDS:
        _require(
            acceptance_id in acceptances
            and EVIDENCE_ID in acceptances[acceptance_id].get("evidenceIds", []),
            f"Source snapshot evidence is not linked to {acceptance_id}",
        )
    evidence = {
        item.get("id"): item for item in program_map.get("evidence", [])
    }
    _require(EVIDENCE_ID in evidence, "Source snapshot evidence record is missing")
    _require(
        evidence[EVIDENCE_ID].get("path") == SNAPSHOT_PATH.as_posix()
        and set(evidence[EVIDENCE_ID].get("supports", []))
        == EXPECTED_ACCEPTANCE_IDS,
        "Source snapshot evidence projection drifted",
    )

    document = DOCUMENT_PATH.read_text(encoding="utf-8")
    normalized = " ".join(document.split())
    for phrase in (
        "Observation is not freezing",
        "No raw external body is retained",
        "ISO metadata-only boundary",
        "Offline reconstruction",
        "does not prove",
        "Independent review remains deferred behind candidate capability coverage",
    ):
        _require(phrase in normalized, f"Source snapshot document missing: {phrase}")


def main() -> int:
    validate_snapshot()
    print("Software-engineering source snapshot validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
