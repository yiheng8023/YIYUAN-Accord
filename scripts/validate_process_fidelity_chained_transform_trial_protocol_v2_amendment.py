#!/usr/bin/env python3
"""Validate the hash-bound chained-transform protocol v2 amendment."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
AMENDMENT_PATH = (
    "registry/human-ai-collaboration-process-fidelity-chained-transform-"
    "trial-protocol-v2-amendment-2026-07-27.json"
)
DOC_PATH = (
    "docs/strategy/HUMAN-AI-COLLABORATION-PROCESS-FIDELITY-CHAINED-"
    "TRANSFORM-TRIAL-PROTOCOL-V2-AMENDMENT-2026-07-27.md"
)


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def _file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate_amendment(
    document: dict[str, Any],
    *,
    root: Path = ROOT,
) -> None:
    _require(
        document.get("schema") == 1
        and document.get("id")
        == (
            "human-ai-collaboration-process-fidelity-chained-transform-"
            "trial-protocol-v2-amendment-2026-07-27"
        )
        and document.get("date") == "2026-07-27"
        and document.get("status")
        == "preregistered-zero-dispatch-protocol-amendment",
        "Chained-transform v2 amendment identity drifted",
    )
    base = document.get("baseProtocol")
    _require(
        isinstance(base, dict)
        and isinstance(base.get("path"), str)
        and (root / base["path"]).is_file()
        and base.get("fileSha256", "").lower()
        == _file_sha256(root / base["path"]).lower(),
        "Chained-transform v2 base binding drifted",
    )
    gate = document.get("recoveryGateAmendment")
    _require(
        isinstance(gate, dict)
        and gate.get("stageId") == "edge-recovery-envelope"
        and gate.get("sourceAnchorPayloadExposurePolicy")
        == "valid-exact-hop-2-detection-only"
        and gate.get("controlDisposition")
        == "forward-predecessor-with-sealed-source-anchor"
        and gate.get("invalidDetectionDisposition")
        == "halt-before-hop-3-and-retain-raw-evidence"
        and gate.get("sourceAnchorReferenceAlwaysAllowed") is True,
        "Chained-transform v2 recovery gate drifted",
    )
    raw = document.get("rawCaptureContract")
    trace = document.get("formalTraceContract")
    _require(
        isinstance(raw, dict)
        and (root / raw["schemaPath"]).is_file()
        and raw.get("parentComputesAllHashes") is True
        and raw.get("agentEchoedHashesAreEvidence") is False
        and raw.get("laterStageMayMaterializeBeforePredecessorPersisted")
        is False
        and raw.get("opaqueOrInvalidStageAllowsDownstreamMaterialization")
        is False
        and raw.get("manualMetricSupplementationAllowed") is False,
        "Chained-transform v2 raw-capture contract drifted",
    )
    _require(
        isinstance(trace, dict)
        and (root / trace["schemaPath"]).is_file()
        and trace.get("rawCaptureRequired") is True
        and trace.get("parentRecomputationRequired") is True
        and trace.get("zeroModelCaptureEligibility") == "calibration-only"
        and trace.get("actualRouteEvidenceRequiredForFormalLiveEligibility")
        is True
        and trace.get("requestedRouteCountsAsObservedRoute") is False,
        "Chained-transform v2 formal-trace contract drifted",
    )
    execution = document.get("executionBoundary")
    _require(
        isinstance(execution, dict)
        and execution.get("agentDispatchCount") == 0
        and execution.get("modelCallCount") == 0
        and execution.get("externalAccessUsed") is False
        and execution.get("hostConfigurationChanged") is False
        and execution.get("formalProcessCohortCount") == 0
        and execution.get("liveDispatchAuthorized") is False,
        "Chained-transform v2 execution boundary drifted",
    )
    _require(
        isinstance(document.get("claimBoundary"), dict)
        and document["claimBoundary"]
        and all(value is False for value in document["claimBoundary"].values()),
        "Chained-transform v2 claim boundary was promoted",
    )
    _require(
        document.get("documentation") == DOC_PATH
        and (root / DOC_PATH).is_file(),
        "Chained-transform v2 documentation binding drifted",
    )
    normalized = " ".join(
        (root / DOC_PATH).read_text(encoding="utf-8").split()
    )
    for phrase in (
        "only when the parent recomputes",
        "stops the sequence before hop 3",
        "Zero-model scripted captures are calibration evidence only",
        "formal cohort count remains zero",
    ):
        _require(
            phrase in normalized,
            f"Chained-transform v2 documentation missing: {phrase}",
        )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args()
    root = args.root.resolve()
    document = json.loads(
        (root / AMENDMENT_PATH).read_text(encoding="utf-8")
    )
    validate_amendment(document, root=root)
    print("Process-fidelity chained-transform v2 amendment passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
