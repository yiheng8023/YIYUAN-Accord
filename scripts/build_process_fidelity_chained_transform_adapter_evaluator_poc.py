#!/usr/bin/env python3
"""Build durable zero-dispatch adapter/evaluator PoC artifacts."""

from __future__ import annotations

import argparse
import json
from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

try:
    from .evaluate_process_fidelity_chained_transform_trace import (
        evaluate_capture,
    )
    from .run_process_fidelity_chained_transform_trial import (
        canonical_sha256,
        file_sha256,
        run_zero_model_sequence,
    )
except ImportError:  # pragma: no cover - direct script execution
    from evaluate_process_fidelity_chained_transform_trace import (
        evaluate_capture,
    )
    from run_process_fidelity_chained_transform_trial import (
        canonical_sha256,
        file_sha256,
        run_zero_model_sequence,
    )


ROOT = Path(__file__).resolve().parent.parent
FIXTURE_PATH = (
    "tests/fixtures/process-fidelity-chained-transform-sequential-adapter-"
    "faults-2026-07-27.json"
)


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def _mutate_capture(capture: dict[str, Any], operation: str) -> None:
    if operation == "replace-first-edge-predecessor-hash":
        capture["materialEdges"][0][
            "predecessorOutputArtifactSha256"
        ] = "0" * 64
    elif operation == "duplicate-first-edge-id-at-second-position":
        capture["materialEdges"][1]["edgeId"] = (
            capture["materialEdges"][0]["edgeId"]
        )
    elif operation == "mark-first-edge-opaque":
        capture["materialEdges"][0]["opaque"] = True
    elif operation == "replace-source-index-hash":
        capture["rawArtifactIndex"][0]["rawSha256"] = "0" * 64
    elif operation == "add-caller-hop-metrics":
        capture["hopMetrics"] = [{"processAcceptancePass": True}]
    else:
        raise RuntimeError(f"Unknown post-capture fault operation: {operation}")


def _evaluate_fault(
    fault: dict[str, Any],
    cases: dict[str, dict[str, Any]],
    *,
    root: Path,
) -> dict[str, Any]:
    case = deepcopy(cases[fault["baseCaseId"]])
    operation = fault["operation"]
    if operation == "remove-one-hop-2-detected-loss-id-before-run":
        case["scriptedHopOutputs"]["hop-2-routing"][
            "detectedLossIds"
        ].pop()
    with TemporaryDirectory() as temporary:
        capture_root = Path(temporary) / "capture"
        capture = run_zero_model_sequence(
            root=root,
            output_root=capture_root,
            cell=case["cell"],
            scripted_hop_outputs=case["scriptedHopOutputs"],
        )
        if operation != "remove-one-hop-2-detected-loss-id-before-run":
            capture = deepcopy(capture)
            _mutate_capture(capture, operation)
        report = evaluate_capture(
            capture,
            capture_root=capture_root,
            root=root,
        )
    expected = fault["expectedFailureCode"]
    return {
        "id": fault["id"],
        "operation": operation,
        "expectedFailureCode": expected,
        "observedFailureCodes": report["failureCodes"],
        "matched": expected in report["failureCodes"],
        "candidateTraceProduced": report["candidateTrace"] is not None,
        "formalLiveEvidenceEligible": report["formalLiveEvidenceEligible"],
    }


def build_poc(
    *,
    root: Path,
    output_root: Path,
) -> dict[str, Any]:
    root = root.resolve()
    output_root = output_root.resolve()
    _require(
        not output_root.exists()
        or (output_root.is_dir() and not any(output_root.iterdir())),
        "PoC output root must be absent or empty",
    )
    output_root.mkdir(parents=True, exist_ok=True)
    fixture_path = root / FIXTURE_PATH
    fixture = json.loads(fixture_path.read_text(encoding="utf-8"))
    cases = {item["id"]: item for item in fixture["validCases"]}
    valid_results: list[dict[str, Any]] = []
    for case in fixture["validCases"]:
        case_root = output_root / "CASES" / case["id"]
        capture = run_zero_model_sequence(
            root=root,
            output_root=case_root,
            cell=case["cell"],
            scripted_hop_outputs=case["scriptedHopOutputs"],
        )
        report = evaluate_capture(
            capture,
            capture_root=case_root,
            root=root,
        )
        _write_json(case_root / "EVALUATION.json", report)
        valid_results.append(
            {
                "id": case["id"],
                "expectedOutcome": case["expectedOutcome"],
                "observedOutcome": report["outcome"],
                "matched": report["outcome"] == case["expectedOutcome"],
                "status": report["status"],
                "agentDispatchCount": report["agentDispatchCount"],
                "modelCallCount": report["modelCallCount"],
                "actualRouteObserved": report["actualRouteObserved"],
                "formalLiveEvidenceEligible": (
                    report["formalLiveEvidenceEligible"]
                ),
                "evaluationReportSha256": file_sha256(
                    case_root / "EVALUATION.json"
                ),
            }
        )
    fault_results = [
        _evaluate_fault(fault, cases, root=root)
        for fault in fixture["faultCases"]
    ]
    report = {
        "schema": 1,
        "id": (
            "process-fidelity-chained-transform-zero-dispatch-sequential-"
            "adapter-evaluator-poc-report-2026-07-27"
        ),
        "mode": "zero-agent-zero-dispatch-synthetic-fault-fixture",
        "fixture": {
            "path": FIXTURE_PATH,
            "fileSha256": file_sha256(fixture_path),
        },
        "validCaseResults": valid_results,
        "faultCaseResults": fault_results,
        "decision": {
            "sequentialArtifactAdapterMechanismPassed": all(
                item["matched"] for item in valid_results
            ),
            "parentRecomputedTraceEvaluatorPassed": all(
                item["matched"] for item in valid_results
            ),
            "faultClassifierPassed": all(
                item["matched"]
                and item["candidateTraceProduced"] is False
                and item["formalLiveEvidenceEligible"] is False
                for item in fault_results
            ),
            "nonTemporaryRawEvidenceDestinationBound": (
                output_root.is_relative_to((root / "audits").resolve())
            ),
            "liveDispatchReady": False,
            "formalProcessCohortCount": 0,
        },
        "execution": {
            "agentDispatchCount": 0,
            "modelCallCount": 0,
            "actualRouteObserved": False,
            "liveDispatchAuthorized": False,
            "externalAccessUsed": False,
            "hostConfigurationChanged": False,
        },
        "claimBoundary": dict(fixture["claimBoundary"]),
        "claimLimit": (
            "This PoC proves only zero-model sequential artifact "
            "materialization, persisted hash linkage, conditional source "
            "exposure, parent recomputation, and the registered synthetic "
            "fault classifications. It does not prove live Agent behavior, "
            "route health, a formal cohort outcome, cross-host portability, "
            "Skill treatment value, or end-to-end process fidelity."
        ),
    }
    report["reportSha256"] = canonical_sha256(report)
    _write_json(output_root / "POC-REPORT.json", report)
    (output_root / "README.md").write_text(
        "# Zero-dispatch chained-transform adapter/evaluator PoC\n\n"
        "This directory is repository-local authoritative mechanism evidence. "
        "It contains two scripted valid captures and their parent-recomputed "
        "evaluations. No Agent or model was called. The formal process cohort "
        "remains at zero.\n\n"
        "Retain this directory. It is not `.tmp` cleanup debt. Local custody "
        "does not prove commit or remote durability.\n",
        encoding="utf-8",
    )
    files = [
        path
        for path in output_root.rglob("*")
        if path.is_file() and path.name != "MANIFEST.json"
    ]
    manifest = {
        "schema": 1,
        "id": (
            "process-fidelity-chained-transform-zero-dispatch-sequential-"
            "adapter-evaluator-poc-manifest-2026-07-27"
        ),
        "mode": "zero-agent-zero-dispatch-synthetic-fault-fixture",
        "files": [
            {
                "path": path.relative_to(output_root).as_posix(),
                "bytes": path.stat().st_size,
                "sha256": file_sha256(path),
            }
            for path in sorted(
                files,
                key=lambda item: item.relative_to(output_root).as_posix(),
            )
        ],
        "agentDispatchCount": 0,
        "modelCallCount": 0,
        "actualRouteObserved": False,
        "formalProcessCohortCount": 0,
        "cleanupDisposition": "retain-authoritative-mechanism-evidence",
    }
    manifest["manifestSha256"] = canonical_sha256(manifest)
    _write_json(output_root / "MANIFEST.json", manifest)
    return {
        "report": report,
        "manifest": manifest,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = build_poc(
        root=args.root.resolve(),
        output_root=args.output,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
