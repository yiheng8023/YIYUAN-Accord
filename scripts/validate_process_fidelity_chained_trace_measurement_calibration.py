#!/usr/bin/env python3
"""Validate the zero-Agent chained-trace measurement calibration evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

try:
    from .calibrate_process_fidelity_chained_trace import validate_contract
except ImportError:  # pragma: no cover - direct script execution
    from calibrate_process_fidelity_chained_trace import validate_contract


ROOT = Path(__file__).resolve().parent.parent
EVIDENCE_PATH = (
    "registry/human-ai-collaboration-process-fidelity-chained-trace-"
    "measurement-calibration-2026-07-27.json"
)
DOC_PATH = (
    "docs/strategy/HUMAN-AI-COLLABORATION-PROCESS-FIDELITY-CHAINED-"
    "TRACE-MEASUREMENT-CALIBRATION-2026-07-27.md"
)


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def _file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate_evidence(document: dict[str, Any], *, root: Path = ROOT) -> None:
    _require(
        document.get("schema") == 1
        and document.get("id")
        == (
            "human-ai-collaboration-process-fidelity-chained-trace-"
            "measurement-calibration-2026-07-27"
        )
        and document.get("date") == "2026-07-27"
        and document.get("status")
        == (
            "zero-agent-chained-trace-measurement-calibration-passed-"
            "live-cohort-not-authorized"
        )
        and document.get("scenarioId") == "GEN-RESEARCH-01"
        and document.get("crossCuttingRiskId")
        == "XCR-01-process-fidelity-and-loss",
        "Chained-trace evidence identity drifted",
    )
    bindings = [
        (document.get("contract"), "path", "fileSha256"),
        (document.get("calibrator"), "path", "fileSha256"),
        (
            document.get("calibrator"),
            "reusedMetricEvaluatorPath",
            "reusedMetricEvaluatorFileSha256",
        ),
    ]
    for binding, path_key, hash_key in bindings:
        _require(
            isinstance(binding, dict)
            and isinstance(binding.get(path_key), str)
            and isinstance(binding.get(hash_key), str),
            f"Chained-trace evidence binding missing: {path_key}",
        )
        path = root / binding[path_key]
        _require(path.is_file(), f"Chained-trace evidence file missing: {path}")
        _require(
            _file_sha256(path).lower() == binding[hash_key].lower(),
            f"Chained-trace evidence file hash drifted: {path}",
        )

    contract_binding = document["contract"]
    contract = json.loads(
        (root / contract_binding["path"]).read_text(encoding="utf-8")
    )
    report = validate_contract(contract)
    observed_outcomes = {
        item["id"]: item["outcome"] for item in report["caseResults"]
    }
    _require(
        observed_outcomes == document.get("caseOutcomes"),
        "Chained-trace calibrated outcomes drifted",
    )
    indexed = {item["id"]: item for item in report["caseResults"]}
    measurement = document.get("measurementEvidence")
    _require(
        isinstance(measurement, dict)
        and measurement.get("linkageFailureEdgeIds")
        == indexed["predecessor-input-linkage-mismatch"]["absoluteLedger"][
            "predecessorLinkageFailureEdgeIds"
        ]
        and measurement.get("amplificationFactor")
        == indexed["local-loss-propagated-and-amplified"][
            "processLedger"
        ]["amplificationFactor"]
        and measurement.get("downstreamAffectedHopCount")
        == indexed["local-loss-propagated-and-amplified"][
            "processLedger"
        ]["downstreamAffectedHopCount"]
        and measurement.get("terminalRestorationMatchedSourceAnchor")
        is True
        and measurement.get(
            "intermediateLossRetainedAfterTerminalRestoration"
        )
        is True
        and measurement.get("opaqueMaterialEdgeMetricsRemainUnknown")
        is True
        and measurement.get("absoluteAndProcessLedgersCanCancelEachOther")
        is False,
        "Chained-trace measurement evidence drifted",
    )
    execution = document.get("execution")
    _require(
        isinstance(execution, dict)
        and execution.get("agentDispatchCount") == 0
        and execution.get("modelCallCount") == 0
        and execution.get("externalAccessUsed") is False
        and execution.get("writeOutsideRepository") is False,
        "Chained-trace execution boundary drifted",
    )
    scope = document.get("scopeBoundary")
    _require(
        isinstance(scope, dict)
        and scope.get(
            "v2DeliveryTopologyProtocolReclassifiedAsTerminalTaskSubprotocol"
        )
        is True
        and scope.get("existingSourceBackedSmokeCountsAsProcessTrace")
        is False
        and scope.get("rawEventTraceAdapterImplementedByCalibration")
        is False
        and scope.get("subsequentTraceEligibilityAssessmentRecorded") is True
        and scope.get("subsequentTraceEligibilityAssessmentPath")
        == (
            "registry/human-ai-collaboration-process-fidelity-raw-event-trace-"
            "eligibility-assessment-2026-07-27.json"
        )
        and (root / scope["subsequentTraceEligibilityAssessmentPath"]).is_file()
        and scope.get(
            "existingSmokeDeterministicallyRescoredWithoutManualSupplementation"
        )
        is False
        and scope.get("formalLiveCohortAuthorized") is False
        and scope.get("endToEndProcessFidelityAcceptanceVerified") is False,
        "Chained-trace scope boundary drifted",
    )
    decision = document.get("decision")
    _require(
        isinstance(decision, dict)
        and decision.get("measurementCalibrationPassed") is True
        and decision.get("evidenceStopRemainsActive") is True
        and isinstance(decision.get("nextBoundedResult"), str)
        and bool(decision["nextBoundedResult"]),
        "Chained-trace decision boundary drifted",
    )
    _require(
        document.get("documentation") == DOC_PATH
        and (root / DOC_PATH).is_file()
        and isinstance(document.get("claimLimit"), str)
        and bool(document["claimLimit"]),
        "Chained-trace documentation binding drifted",
    )
    normalized = " ".join(
        (root / DOC_PATH).read_text(encoding="utf-8").split()
    )
    for phrase in (
        "zero-Agent measurement calibration passed",
        "predecessor-output/current-input mismatch failed closed",
        "amplification factor `2.8`",
        "did not erase the recorded intermediate authority loss",
        "opaque material edge kept amplification and rollback metrics unknown",
        "absolute and process ledgers cannot cancel each other",
        "not a process-trace-valid repetition",
        "evidence stop remains active",
        "starts from zero",
    ):
        _require(
            phrase in normalized,
            f"Chained-trace documentation boundary missing: {phrase}",
        )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args()
    root = args.root.resolve()
    document = json.loads((root / EVIDENCE_PATH).read_text(encoding="utf-8"))
    validate_evidence(document, root=root)
    print("Process-fidelity chained-trace calibration validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
