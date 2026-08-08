#!/usr/bin/env python3
"""Validate the current program final-closeout readiness reconciliation."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
RECORD_PATH = Path(
    "registry/program-final-closeout-readiness-reconciliation-2026-07-28.json"
)
PROGRAM_MAP_PATH = Path("registry/program-acceptance-map.json")


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def validate_reconciliation(document: dict, *, root: Path = ROOT) -> None:
    _require(
        document.get("schema") == 1
        and document.get("status")
        == "current-program-closeout-audited-cannot-close"
        and document.get("lastReconciledDate") == "2026-08-08",
        "Program closeout reconciliation identity drifted",
    )
    sources = document.get("sourceBindings", {})
    _require(
        sources.get("programAcceptanceMap")
        == str(PROGRAM_MAP_PATH).replace("\\", "/")
        and all((root / path).is_file() for path in sources.values()),
        "Program closeout source binding drifted",
    )
    _require(
        sources.get("mattV123ExactPinReconciliation")
        == "registry/mattpocock-skills-v1.2.3-exact-pin-reconciliation-event-2026-08-08.json"
        and sources.get("mattV123ExactPinPostRestartReport")
        == "audits/mattpocock-skills/6acc160e4e0cd062dbbbd7a1b26ae92855edf07e/exact-pin-reconciliation-2026-08-08/POST-RESTART-REPORT.json",
        "Program closeout Matt v1.2.3 exact-pin binding drifted",
    )
    _require(
        sources.get("disabledConsumerRootInventory")
        == "registry/cc-switch-disabled-consumer-root-readonly-inventory-2026-08-08.json",
        "Program closeout disabled-consumer binding drifted",
    )
    _require(
        sources.get("offlinePluginProjectionPoc")
        == "registry/offline-plugin-projection-poc-2026-08-08.json",
        "Program closeout offline-plugin PoC binding drifted",
    )
    program = json.loads((root / PROGRAM_MAP_PATH).read_text(encoding="utf-8"))
    criteria = program.get("acceptanceCriteria", [])
    counts = Counter(row.get("assessment") for row in criteria)
    expected_snapshot = {
        "totalCriteria": len(criteria),
        "verified": counts["verified"],
        "partial": counts["partial"],
        "planned": counts["planned"],
        "other": len(criteria)
        - counts["verified"]
        - counts["partial"]
        - counts["planned"],
        "allCriteriaVerified": all(
            row.get("assessment") == "verified" for row in criteria
        ),
    }
    _require(
        document.get("acceptanceSnapshot") == expected_snapshot,
        "Program acceptance snapshot drifted",
    )
    expected_open = {
        row["id"]: row["assessment"]
        for row in criteria
        if row.get("assessment") != "verified"
    }
    observed_open = {
        row["id"]: row["assessment"]
        for row in document.get("openCriteria", [])
    }
    _require(
        observed_open == expected_open and len(observed_open) == 15,
        "Program open-criteria reconciliation drifted",
    )
    valid_clusters = {
        "semantic-and-lifecycle-evidence": 3,
        "residual-gap-and-authoring": 2,
        "consumer-and-source-governance": 4,
        "standard-lifecycle": 2,
        "runtime-hook-and-orchestration": 3,
        "final-cleanup": 1,
    }
    observed_cluster_counts = Counter(
        row["cluster"] for row in document.get("openCriteria", [])
    )
    _require(
        dict(observed_cluster_counts) == valid_clusters,
        "Program closeout cluster assignment drifted",
    )
    gate_clusters = {
        row["id"]: row["openCriteriaCount"]
        for row in document.get("gateClusters", [])
    }
    _require(
        gate_clusters == valid_clusters,
        "Program closeout gate-cluster coverage drifted",
    )
    consumer_cluster = next(
        row
        for row in document.get("gateClusters", [])
        if row.get("id") == "consumer-and-source-governance"
    )
    consumer_boundary = consumer_cluster.get("currentBoundary", "")
    _require(
        "25 exact v1.2.3 payloads" in consumer_boundary
        and "72 manager symlinks" in consumer_boundary
        and "Gemini, GrokBuild, OpenCode, and Hermes" in consumer_boundary
        and "all four governed roots were absent" in consumer_boundary
        and "six fail-closed classes" in consumer_boundary
        and "plugin installability or host conformance" in consumer_boundary
        and "behavior, or value" in consumer_boundary,
        "Program closeout consumer/source claim boundary drifted",
    )
    open_ids = set(expected_open)
    expected_open_objectives = {
        row["id"]
        for row in program.get("objectives", [])
        if open_ids.intersection(row.get("acceptanceIds", []))
    }
    _require(
        set(document.get("openObjectiveIds", []))
        == expected_open_objectives
        and len(expected_open_objectives) == 8,
        "Program open-objective reconciliation drifted",
    )
    premise_checks = document.get("butterflyPremiseChecks", [])
    _require(
        len(premise_checks) == 4
        and all(row.get("result") == "falsified" for row in premise_checks),
        "Program premise-check coverage drifted",
    )
    closeout = document.get("closeoutDecision", {})
    _require(
        closeout.get("status") == "cannot-close"
        and closeout.get("goalComplete") is False
        and all(
            closeout.get(key) is False
            for key in (
                "exactLoaderDecisionAloneCanCloseProgram",
                "topLevelVerifierPassCanCloseProgram",
                "cleanupInventoryPassCanCloseProgram",
                "programStatusMutationAuthorized",
            )
        ),
        "Program closeout decision overclaimed",
    )
    authority = document.get("authorityBoundary", {})
    _require(
        authority and all(value is False for value in authority.values()),
        "Program closeout authority expanded",
    )
    progress = document.get("currentEvidenceProgress", {})
    _require(
        progress.get("mattV123ExactSourceMetadataPin")
        == "covered-restart-persistent-metadata-only"
        and progress.get("disabledConsumerRootPresenceAndMattProjectionAbsence")
        == "covered-readonly-single-observation"
        and progress.get("offlinePluginProjectionMapping")
        == "covered-field-failure-and-ownership-mechanism-only",
        "Program closeout current evidence progress drifted",
    )
    documentation = document.get("documentation")
    _require(
        isinstance(documentation, str) and (root / documentation).is_file(),
        "Program closeout documentation binding drifted",
    )


def main() -> int:
    document = json.loads((ROOT / RECORD_PATH).read_text(encoding="utf-8"))
    validate_reconciliation(document, root=ROOT)
    print("Program final-closeout readiness reconciliation verified.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
