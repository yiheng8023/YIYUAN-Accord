#!/usr/bin/env python3
"""Validate deterministic chained-transform packet preflight evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

try:
    from .build_process_fidelity_chained_transform_trial_packet import (
        build_packet,
        validate_packet,
    )
except ImportError:  # pragma: no cover - direct script execution
    from build_process_fidelity_chained_transform_trial_packet import (
        build_packet,
        validate_packet,
    )


ROOT = Path(__file__).resolve().parent.parent
EVIDENCE_PATH = (
    "registry/human-ai-collaboration-process-fidelity-chained-transform-"
    "packet-preflight-2026-07-27.json"
)
DOC_PATH = (
    "docs/strategy/HUMAN-AI-COLLABORATION-PROCESS-FIDELITY-CHAINED-"
    "TRANSFORM-PACKET-PREFLIGHT-2026-07-27.md"
)
EXPECTED_BINDINGS = {
    "protocol": (
        "registry/human-ai-collaboration-process-fidelity-chained-transform-"
        "trial-protocol-2026-07-27.json"
    ),
    "traceSchema": (
        "schemas/process-fidelity-chained-transform-trace-v1.schema.json"
    ),
    "packetBuilder": (
        "scripts/build_process_fidelity_chained_transform_trial_packet.py"
    ),
}


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def _file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate_evidence(
    document: dict[str, Any],
    *,
    root: Path = ROOT,
) -> None:
    _require(
        document.get("schema") == 1
        and document.get("id")
        == (
            "human-ai-collaboration-process-fidelity-chained-transform-"
            "packet-preflight-2026-07-27"
        )
        and document.get("date") == "2026-07-27"
        and document.get("status")
        == (
            "zero-dispatch-packet-preflight-passed-live-dispatch-not-ready"
        ),
        "Chained-transform packet preflight identity drifted",
    )
    bindings = document.get("bindings")
    _require(
        isinstance(bindings, dict)
        and set(bindings) == set(EXPECTED_BINDINGS),
        "Chained-transform packet binding set drifted",
    )
    for key, expected_path in EXPECTED_BINDINGS.items():
        binding = bindings[key]
        path = root / expected_path
        _require(
            binding.get("path") == expected_path and path.is_file(),
            f"Chained-transform packet binding missing: {key}",
        )
        _require(
            binding.get("fileSha256", "").lower()
            == _file_sha256(path).lower(),
            f"Chained-transform packet binding hash drifted: {key}",
        )

    execution = document.get("execution")
    _require(
        isinstance(execution, dict)
        and execution.get("agentDispatchCount") == 0
        and execution.get("modelCallCount") == 0
        and execution.get("externalAccessUsed") is False
        and execution.get("hostConfigurationChanged") is False
        and execution.get("globalSkillStateChanged") is False
        and execution.get("temporaryPacketRetained") is False,
        "Chained-transform packet execution boundary drifted",
    )
    with TemporaryDirectory() as temporary:
        packet_root = Path(temporary) / "packet"
        build_packet(packet_root, root=root)
        report = validate_packet(packet_root, root=root)

    result = document.get("preflightResult")
    _require(
        isinstance(result, dict)
        and result.get("status") == report.get("status")
        and result.get("agentVisibleFileCount")
        == report.get("agentVisibleFileCount")
        == 2
        and result.get("privateScoringFieldLeakCount")
        == report.get("privateScoringFieldLeakCount")
        == 0
        and result.get("deferredAgentStagesMaterialized")
        == report.get("deferredAgentStagesMaterialized")
        is False
        and result.get("actualRouteObserved")
        == report.get("actualRouteObserved")
        is False
        and result.get("rawEvidenceDestinationBound")
        == report.get("rawEvidenceDestinationBound")
        is False
        and result.get("liveDispatchReady")
        == report.get("liveDispatchReady")
        is False,
        "Chained-transform packet preflight result drifted",
    )
    exposure = document.get("exposureBoundary")
    _require(
        isinstance(exposure, dict)
        and exposure.get("materializedAgentStageIds")
        == ["hop-1-decomposition"]
        and exposure.get("deferredAgentStageIds")
        == ["hop-2-routing", "hop-3-acceptance-and-recovery"]
        and exposure.get("agentVisibleFiles")
        == ["INPUT-ENVELOPE.json", "STAGE-CONTRACT.json"]
        and exposure.get("parentOnlyFiles")
        == [
            "PROTOCOL.json",
            "PRIVATE-SCORING-ORACLE.json",
            "RUN-PLAN.json",
            "DEFERRED-STAGE-TEMPLATES.json",
        ]
        and exposure.get("singleDynamicInputProvedForMaterializedStage")
        is True
        and exposure.get("privateOracleIsolationProvedForMaterializedStage")
        is True
        and exposure.get("laterStageIsolationProved") is False
        and exposure.get("liveRouteProved") is False,
        "Chained-transform packet exposure boundary drifted",
    )
    decision = document.get("decision")
    _require(
        isinstance(decision, dict)
        and decision.get("protocolAndTraceSchemaBound") is True
        and decision.get("zeroDispatchPacketPreflightPassed") is True
        and decision.get("liveDispatchAuthorized") is False
        and decision.get("liveDispatchReady") is False
        and decision.get("formalProcessCohortCount") == 0
        and isinstance(decision.get("nextBoundedResult"), str)
        and bool(decision["nextBoundedResult"]),
        "Chained-transform packet decision boundary drifted",
    )
    _require(
        isinstance(document.get("claimBoundary"), dict)
        and document["claimBoundary"]
        and all(value is False for value in document["claimBoundary"].values()),
        "Chained-transform packet claim boundary was promoted",
    )
    _require(
        document.get("documentation") == DOC_PATH
        and (root / DOC_PATH).is_file()
        and isinstance(document.get("claimLimit"), str)
        and bool(document["claimLimit"]),
        "Chained-transform packet documentation binding drifted",
    )
    normalized = " ".join(
        (root / DOC_PATH).read_text(encoding="utf-8").split()
    )
    for phrase in (
        "without an Agent or model call",
        "formal process cohort still starts at zero",
        "one dynamic input",
        "zero private scoring-field leaks",
        "`manualMetricSupplementationUsed=false`",
        "`actualRouteObserved=false`",
        "`liveDispatchReady=false`",
        "does not authorize Spark",
    ):
        _require(
            phrase in normalized,
            f"Chained-transform packet documentation missing: {phrase}",
        )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args()
    root = args.root.resolve()
    document = json.loads(
        (root / EVIDENCE_PATH).read_text(encoding="utf-8")
    )
    validate_evidence(document, root=root)
    print("Process-fidelity chained-transform packet preflight passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
