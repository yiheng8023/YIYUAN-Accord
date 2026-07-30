#!/usr/bin/env python3
"""Validate durable no-turn four-cell control-chain exposure evidence."""

from __future__ import annotations

import json
from pathlib import Path

try:
    from scripts.probe_codex_app_server_skill_exposure import canonical_sha256
    from scripts.probe_human_ai_collaboration_self_authored_control_chain_four_cell_exposure import (
        CELL_FACTORS,
        validate_report,
    )
except ModuleNotFoundError:  # pragma: no cover - direct script execution
    from probe_codex_app_server_skill_exposure import canonical_sha256
    from probe_human_ai_collaboration_self_authored_control_chain_four_cell_exposure import (
        CELL_FACTORS,
        validate_report,
    )


ROOT = Path(__file__).resolve().parent.parent
REPORT_PATH = Path(
    "audits/human-ai-collaboration-self-authored-control-chain-four-cell-"
    "exposure-2026-07-28/REPORT.json"
)
PROTOCOL_PATH = Path(
    "registry/human-ai-collaboration-self-authored-control-chain-"
    "factorial-ablation-protocol-2026-07-28.json"
)


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def validate_evidence(document: dict, *, root: Path = ROOT) -> None:
    body = dict(document)
    reported_digest = body.pop("reportSha256", None)
    _require(
        reported_digest == canonical_sha256(body),
        "Four-cell exposure report digest drifted",
    )
    _require(
        validate_report(document) == [],
        "Four-cell exposure report contract failed",
    )
    protocol = json.loads((root / PROTOCOL_PATH).read_text(encoding="utf-8"))
    _require(
        document.get("protocol") == str(PROTOCOL_PATH).replace("\\", "/")
        and protocol.get("fourCellExposureEvidence")
        == str(REPORT_PATH).replace("\\", "/"),
        "Four-cell exposure protocol binding drifted",
    )
    host = document.get("host", {})
    _require(
        str(host.get("userAgent", "")).startswith("Codex Desktop/0.145.0")
        and host.get("platformFamily") == "windows"
        and isinstance(host.get("isolatedCodexHome"), str),
        "Four-cell exposure host identity drifted",
    )

    chain = protocol["factors"]["chain"]
    expected_files = {
        (row["name"], "SKILL.md"): (row["bytes"], row["sha256"])
        for row in chain["exactSkillPins"]
    }
    expected_files.update(
        {
            (row["skillName"], row["relativePath"]): (
                row["bytes"],
                row["sha256"],
            )
            for row in chain["exactDependencyPins"]
        }
    )
    observed_files = {
        (row["skillName"], row["relativePath"]): (
            row["bytes"],
            row["sha256"],
        )
        for row in document["projection"]["projectedFiles"]
    }
    _require(
        observed_files == expected_files and len(observed_files) == 5,
        "Four-cell dependency-complete projection pins drifted",
    )
    _require(
        set(document["projection"]["exactSkillPathSha256"])
        == {"intent-contract", "capability-router", "closure-contract"},
        "Four-cell exact Skill path set drifted",
    )

    cells = {row["cellId"]: row for row in document["cells"]}
    _require(
        set(cells) == set(CELL_FACTORS),
        "Four-cell evidence coverage drifted",
    )
    expected_counts = {
        "CHAIN-HARD-HOOK-OFF": (0, 0),
        "CHAIN-HARD-HOOK-AUTO": (0, 428),
        "CHAIN-EXACT-HOOK-OFF": (3, 0),
        "CHAIN-EXACT-HOOK-AUTO": (3, 428),
    }
    for cell_id, (skill_count, hook_bytes) in expected_counts.items():
        row = cells[cell_id]
        _require(
            row["inventory"]["enabledConfigurableSkillCount"] == skill_count
            and row["hookDirectEvidence"]["stdoutBytes"] == hook_bytes
            and row["hookDirectEvidence"]["returnCode"] == 0
            and row["hookDirectEvidence"]["stderrBytes"] == 0,
            f"Four-cell observation drifted: {cell_id}",
        )

    gate = protocol.get("executionAdmission", {})
    _require(
        gate.get("dependencyCompleteProjectionImplemented") is True
        and gate.get("projectionBuilderFaultTestsPass") is True
        and gate.get("taskScopedFourCellExposureProved") is True
        and gate.get("liveWeakModelRunAuthorizedByThisRecord") is False
        and gate.get("admittedForLiveExecution") is False,
        "Four-cell protocol gate overclaimed",
    )


def main() -> int:
    document = json.loads((ROOT / REPORT_PATH).read_text(encoding="utf-8"))
    validate_evidence(document, root=ROOT)
    print("Self-authored control-chain four-cell exposure evidence verified.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
