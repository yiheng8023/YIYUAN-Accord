#!/usr/bin/env python3
"""Validate the Agent resource-pressure attribution protocol."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

try:
    from .evaluate_agent_resource_pressure_attribution import (
        METRIC_CLASSES,
        RESOURCE_TYPES,
        evaluate_fixture_document,
    )
except ImportError:
    from evaluate_agent_resource_pressure_attribution import (
        METRIC_CLASSES,
        RESOURCE_TYPES,
        evaluate_fixture_document,
    )


ROOT = Path(__file__).resolve().parent.parent
PROTOCOL_PATH = (
    ROOT / "registry/agent-resource-pressure-attribution-protocol-2026-07-31.json"
)
FIXTURE_PATH = (
    ROOT
    / "tests/fixtures/agent-resource-pressure-attribution-fixtures-2026-07-31.json"
)
DOCUMENT_PATH = (
    ROOT
    / "docs/strategy/AGENT-RESOURCE-PRESSURE-ATTRIBUTION-PROTOCOL-2026-07-31.md"
)
PROGRAM_MAP_PATH = ROOT / "registry/program-acceptance-map.json"
EVIDENCE_ID = "evidence.agent-resource-pressure-attribution-protocol-2026-07-31"
ACCEPTANCE_ID = "acceptance.dynamic-runtime-control-gap-research"


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def validate_protocol(
    protocol: dict[str, Any] | None = None,
    *,
    root: Path = ROOT,
    program_map: dict[str, Any] | None = None,
) -> None:
    protocol = protocol or _load(
        root / "registry/agent-resource-pressure-attribution-protocol-2026-07-31.json"
    )
    fixtures = _load(
        root
        / "tests/fixtures/agent-resource-pressure-attribution-fixtures-2026-07-31.json"
    )
    program_map = program_map or _load(root / "registry/program-acceptance-map.json")

    _require(protocol.get("schema") == 1, "Protocol schema drifted")
    _require(
        protocol.get("status")
        == "offline-synthetic-resource-pressure-attribution-and-autonomy-decision-contract-live-not-tested",
        "Protocol status drifted",
    )
    _require(
        set(protocol.get("resourceTypes", [])) == RESOURCE_TYPES,
        "Resource-type inventory drifted",
    )
    _require(
        protocol.get("autonomyDecisionPolicy", {}).get(
            "taskCompletionIsResourceRelease"
        )
        is False,
        "Task completion was promoted to resource release",
    )
    _require(
        protocol.get("autonomyDecisionPolicy", {}).get(
            "persistedThreadCountAloneProvesPressure"
        )
        is False,
        "Persisted-thread count was promoted to pressure evidence",
    )
    _require(
        protocol.get("autonomyDecisionPolicy", {}).get(
            "zombieThreadIsOneRuntimeState"
        )
        is False,
        "Zombie thread was collapsed to one runtime state",
    )
    authority = protocol.get("authorityBoundary", {})
    _require(
        isinstance(authority, dict)
        and authority
        and all(value is False for value in authority.values()),
        "Offline authority boundary drifted",
    )
    claims = protocol.get("claimBoundary", {})
    _require(
        isinstance(claims, dict)
        and claims
        and all(value is False for value in claims.values()),
        "Offline claim boundary drifted",
    )

    _require(fixtures.get("schema") == 1, "Fixture schema drifted")
    _require(len(fixtures.get("fixtures", [])) == 26, "Fixture count drifted")
    defaults = fixtures.get("defaults", {})
    _require(
        set(defaults.get("candidateResourceTypes", [])) <= RESOURCE_TYPES,
        "Fixture resource types drifted",
    )
    _require(
        set(defaults.get("metricClassesRecorded", [])) <= METRIC_CLASSES,
        "Fixture metric classes drifted",
    )
    results = evaluate_fixture_document(fixtures)
    mismatches = [
        item
        for item in results
        if item["expectedClassification"] != item["actual"]["classification"]
    ]
    _require(not mismatches, f"Fixture classifications drifted: {mismatches}")
    _require(
        all(item["actual"]["countsAsLiveHostProof"] is False for item in results),
        "Synthetic fixture became live proof",
    )
    _require(
        all(
            item["actual"]["countsAsSelfAuthoredControllerGapEvidence"] is False
            for item in results
        ),
        "Synthetic fixture became self-authored gap evidence",
    )

    document = (
        root
        / "docs/strategy/AGENT-RESOURCE-PRESSURE-ATTRIBUTION-PROTOCOL-2026-07-31.md"
    ).read_text(encoding="utf-8")
    normalized_document = " ".join(document.split())
    for phrase in (
        '"Zombie thread"',
        "persisted thread count alone",
        "Task completion does not prove resource release",
        "Agent should act and",
        "authorizes no live host read",
        "does not prove",
    ):
        _require(
            phrase in normalized_document,
            f"Protocol documentation missing: {phrase}",
        )

    acceptances = {
        item.get("id"): item for item in program_map.get("acceptanceCriteria", [])
    }
    _require(ACCEPTANCE_ID in acceptances, "Runtime acceptance is missing")
    _require(
        EVIDENCE_ID in acceptances[ACCEPTANCE_ID].get("evidenceIds", []),
        "Runtime acceptance is not linked to the protocol",
    )
    evidence = {
        item.get("id"): item for item in program_map.get("evidence", [])
    }
    _require(EVIDENCE_ID in evidence, "Program evidence record is missing")
    _require(
        evidence[EVIDENCE_ID].get("path")
        == "registry/agent-resource-pressure-attribution-protocol-2026-07-31.json",
        "Program evidence path drifted",
    )


def main() -> int:
    validate_protocol()
    print("Agent resource-pressure attribution protocol validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
