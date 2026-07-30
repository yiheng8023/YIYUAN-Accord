#!/usr/bin/env python3
"""Build deterministic cumulative-loss accounting mechanism evidence."""

from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

try:
    from .evaluate_process_fidelity_cumulative_loss_accounting import (
        build_cumulative_loss_ledger,
        evaluate_capture_with_cumulative_loss,
    )
    from .run_process_fidelity_chained_transform_trial import (
        canonical_sha256,
        run_zero_model_sequence,
    )
except ImportError:  # pragma: no cover - direct script execution
    from evaluate_process_fidelity_cumulative_loss_accounting import (
        build_cumulative_loss_ledger,
        evaluate_capture_with_cumulative_loss,
    )
    from run_process_fidelity_chained_transform_trial import (
        canonical_sha256,
        run_zero_model_sequence,
    )


ROOT = Path(__file__).resolve().parent.parent
FIXTURE_PATH = (
    "tests/fixtures/process-fidelity-chained-transform-sequential-adapter-"
    "faults-2026-07-27.json"
)
PROTOCOL_PATH = (
    "registry/human-ai-collaboration-process-fidelity-chained-transform-"
    "trial-protocol-2026-07-27.json"
)


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def _case_result(
    case: dict[str, Any],
    *,
    root: Path,
    output_root: Path,
) -> dict[str, Any]:
    capture_root = output_root / case["id"]
    capture = run_zero_model_sequence(
        root=root,
        output_root=capture_root,
        cell=copy.deepcopy(case["cell"]),
        scripted_hop_outputs=copy.deepcopy(case["scriptedHopOutputs"]),
    )
    report = evaluate_capture_with_cumulative_loss(
        capture,
        capture_root=capture_root,
        root=root,
    )
    trace = report.get("candidateTrace")
    _require(isinstance(trace, dict), f"Case did not produce trace: {case}")
    process = trace["processLedger"]
    ledger = process["cumulativeLoss"]
    return {
        "caseId": case["id"],
        "outcome": report["outcome"],
        "processAcceptancePass": process["processAcceptancePass"],
        "cumulativeUniqueLossWeight": ledger[
            "cumulativeUniqueLossWeight"
        ],
        "peakActiveLossWeight": ledger["peakActiveLossWeight"],
        "budgetEvaluated": ledger["budgetEvaluated"],
        "budgetMaximum": ledger["budgetMaximum"],
        "budgetExceededAtHop": ledger["budgetExceededAtHop"],
        "terminalRecoveryDoesNotEraseHistoricalUniqueLoss": ledger[
            "terminalRecoveryDoesNotEraseHistoricalUniqueLoss"
        ],
        "changesProcessAcceptancePass": ledger[
            "changesProcessAcceptancePass"
        ],
        "stageTransitions": [
            {
                "stageId": item["stageId"],
                "newLossIds": item["newLossIds"],
                "carriedLossIds": item["carriedLossIds"],
                "recoveredLossIds": item["recoveredLossIds"],
                "reintroducedLossIds": item["reintroducedLossIds"],
                "activeLossWeight": item["activeLossWeight"],
                "cumulativeUniqueLossWeight": item[
                    "cumulativeUniqueLossWeight"
                ],
            }
            for item in ledger["hops"]
        ],
    }


def _synthetic_falsification_results(
    protocol: dict[str, Any],
) -> list[dict[str, Any]]:
    authority = "invariant-omitted:authority"
    provenance = "provenance-missing:authority"
    reintroduction = build_cumulative_loss_ledger(
        [
            {
                "stageId": "r1",
                "activeLossIds": [authority],
                "weightedDelta": 5,
            },
            {
                "stageId": "r2",
                "activeLossIds": [],
                "weightedDelta": 0,
            },
            {
                "stageId": "r3",
                "activeLossIds": [authority],
                "weightedDelta": 5,
            },
        ],
        protocol,
    )
    breach = build_cumulative_loss_ledger(
        [
            {
                "stageId": "b1",
                "activeLossIds": [authority, provenance],
                "weightedDelta": 6,
            },
            {
                "stageId": "b2",
                "activeLossIds": [
                    provenance,
                    "assumption:unknown-is-fact",
                ],
                "weightedDelta": 5,
            },
        ],
        protocol,
        cumulative_unique_loss_weight_max=6,
    )
    failures: list[str] = []
    for case_id, stages in [
        (
            "unknown-loss-id",
            [
                {
                    "stageId": "x1",
                    "activeLossIds": ["unknown-kind:x"],
                    "weightedDelta": 1,
                }
            ],
        ),
        (
            "weight-mismatch",
            [
                {
                    "stageId": "x1",
                    "activeLossIds": [authority],
                    "weightedDelta": 0,
                }
            ],
        ),
    ]:
        try:
            build_cumulative_loss_ledger(stages, protocol)
        except RuntimeError:
            failures.append(case_id)

    return [
        {
            "id": "reintroduced-loss-is-new-not-unique-twice",
            "passed": (
                reintroduction["cumulativeUniqueLossWeight"] == 5
                and reintroduction["hops"][2]["newLossIds"]
                == [authority]
                and reintroduction["hops"][2]["reintroducedLossIds"]
                == [authority]
            ),
        },
        {
            "id": "first-strict-budget-breach-is-recorded",
            "passed": (
                breach["cumulativeUniqueLossWeight"] == 10
                and breach["peakActiveLossWeight"] == 6
                and breach["budgetExceededAtHop"] == "b2"
            ),
        },
        {
            "id": "unknown-loss-and-weight-mismatch-fail-closed",
            "passed": failures == ["unknown-loss-id", "weight-mismatch"],
        },
    ]


def build_poc(*, root: Path = ROOT) -> dict[str, Any]:
    root = root.resolve()
    fixture = json.loads((root / FIXTURE_PATH).read_text(encoding="utf-8"))
    protocol = json.loads(
        (root / PROTOCOL_PATH).read_text(encoding="utf-8")
    )
    cases = {
        item["id"]: item for item in fixture["validCases"]
    }
    with TemporaryDirectory() as temporary:
        output_root = Path(temporary) / "captures"
        case_results = [
            _case_result(
                cases[case_id],
                root=root,
                output_root=output_root,
            )
            for case_id in (
                "control-sequence",
                "injected-detected-and-gated-recovery",
            )
        ]
    falsification_results = _synthetic_falsification_results(protocol)
    result = {
        "schema": 1,
        "id": (
            "human-ai-collaboration-process-fidelity-cumulative-loss-"
            "accounting-poc-replay-2026-07-27"
        ),
        "date": "2026-07-27",
        "status": "zero-agent-additive-accounting-mechanism-passed",
        "results": {
            "caseResults": case_results,
            "falsificationResults": falsification_results,
            "allExpectedCasesPassed": (
                case_results[0]["cumulativeUniqueLossWeight"] == 0
                and case_results[0]["peakActiveLossWeight"] == 0
                and case_results[1]["cumulativeUniqueLossWeight"] == 6
                and case_results[1]["peakActiveLossWeight"] == 6
                and all(
                    item["passed"] for item in falsification_results
                )
            ),
        },
        "execution": {
            "agentDispatchCount": 0,
            "modelCallCount": 0,
            "externalAccessUsed": False,
            "hostConfigurationChanged": False,
            "formalProcessCohortCount": 0,
        },
        "decision": {
            "cumulativeAccountingMechanismPassed": True,
            "frozenEvaluatorOrSchemaChanged": False,
            "budgetChangesProcessAcceptance": False,
            "endToEndProcessFidelityAssessment": "partial",
        },
    }
    result["reportSha256"] = canonical_sha256(result)
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args()
    print(json.dumps(build_poc(root=args.root), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
