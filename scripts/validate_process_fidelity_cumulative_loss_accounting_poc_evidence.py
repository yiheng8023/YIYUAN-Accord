#!/usr/bin/env python3
"""Validate additive cumulative-loss accounting PoC evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

try:
    from .build_process_fidelity_cumulative_loss_accounting_poc import (
        build_poc,
    )
except ImportError:  # pragma: no cover - direct script execution
    from build_process_fidelity_cumulative_loss_accounting_poc import (
        build_poc,
    )


ROOT = Path(__file__).resolve().parent.parent
EVIDENCE_PATH = (
    "registry/human-ai-collaboration-process-fidelity-cumulative-loss-"
    "accounting-poc-evidence-2026-07-27.json"
)
CONTRACT_PATH = (
    "registry/human-ai-collaboration-process-fidelity-cumulative-loss-"
    "accounting-contract-2026-07-27.json"
)
DOC_PATH = (
    "docs/strategy/HUMAN-AI-COLLABORATION-PROCESS-FIDELITY-CUMULATIVE-"
    "LOSS-ACCOUNTING-POC-2026-07-27.md"
)
EXPECTED_CLAIM_KEYS = {
    "liveAgentBehaviorProved",
    "formalCohortStarted",
    "endToEndProcessFidelityAccepted",
    "humanBoundaryCoverageProved",
    "softwareLifecycleCoverageProved",
    "crossHostPortabilityProved",
    "candidateSkillEffectMeasured",
    "selfAuthoredResidualGapProved",
}


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def _file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _validate_contract(document: dict[str, Any], *, root: Path) -> None:
    _require(
        document.get("schema") == 1
        and document.get("id")
        == (
            "human-ai-collaboration-process-fidelity-cumulative-loss-"
            "accounting-contract-2026-07-27"
        )
        and document.get("status")
        == "zero-agent-additive-accounting-contract-live-not-tested",
        "Cumulative accounting contract identity drifted",
    )
    bindings = document.get("frozenInputBindings")
    _require(
        isinstance(bindings, dict)
        and set(bindings)
        == {"baseProtocol", "formalTraceSchema", "frozenTraceEvaluator"},
        "Cumulative accounting frozen binding set drifted",
    )
    for key, binding in bindings.items():
        _require(
            isinstance(binding, dict)
            and isinstance(binding.get("path"), str)
            and isinstance(binding.get("fileSha256"), str),
            f"Cumulative accounting binding shape drifted: {key}",
        )
        path = root / binding["path"]
        _require(
            path.is_file()
            and _file_sha256(path).lower()
            == binding["fileSha256"].lower(),
            f"Cumulative accounting binding hash drifted: {key}",
        )
    stage_policy = document.get("scoredStagePolicy")
    _require(
        isinstance(stage_policy, dict)
        and stage_policy.get("includedStageIdsInOrder")
        == [
            "hop-1-decomposition",
            "edge-controlled-mutation",
            "hop-2-routing",
            "hop-3-acceptance-and-recovery",
        ]
        and stage_policy.get("excludedStageIds")
        == ["edge-recovery-envelope"]
        and stage_policy.get("parentRecomputedMetricsOnly") is True
        and stage_policy.get("agentReportedCumulativeMetricsEligible")
        is False
        and stage_policy.get(
            "opaqueOrInvalidCaptureProducesTrustedLedger"
        )
        is False,
        "Cumulative accounting scored-stage policy drifted",
    )
    definitions = document.get("setAccountingDefinitions")
    _require(
        isinstance(definitions, dict)
        and set(definitions)
        == {
            "new",
            "carried",
            "recovered",
            "firstSeen",
            "reintroduced",
            "unique",
            "peak",
        },
        "Cumulative accounting set definitions drifted",
    )
    weights = document.get("weightPolicy")
    _require(
        isinstance(weights, dict)
        and weights.get("unknownLossIdType") == "fail-closed"
        and weights.get("activeWeightMustEqualParentWeightedDelta") is True,
        "Cumulative accounting weight policy drifted",
    )
    budget = document.get("budgetPolicy")
    _require(
        isinstance(budget, dict)
        and budget.get("cumulativeUniqueLossWeightMaxByArm")
        == {
            "control-identity": 0,
            "injected-authority-omission": 6,
        }
        and budget.get("comparison") == "strictly-greater-than"
        and budget.get("firstBreachStageRecorded") is True
        and budget.get("missingBudgetDisposition")
        == "budgetEvaluated=false-and-budgetExceededAtHop=null"
        and budget.get("enforcement")
        == "advisory-only-does-not-change-process-acceptance",
        "Cumulative accounting budget policy drifted",
    )
    execution = document.get("executionBoundary")
    _require(
        isinstance(execution, dict)
        and execution.get("agentDispatchCount") == 0
        and execution.get("modelCallCount") == 0
        and execution.get("formalProcessCohortCount") == 0
        and execution.get("liveDispatchAuthorized") is False,
        "Cumulative accounting execution boundary drifted",
    )
    claims = document.get("claimBoundary")
    _require(
        isinstance(claims, dict)
        and set(claims) == EXPECTED_CLAIM_KEYS
        and all(value is False for value in claims.values()),
        "Cumulative accounting contract claim boundary drifted",
    )


def validate_evidence(
    document: dict[str, Any],
    *,
    root: Path = ROOT,
) -> None:
    root = root.resolve()
    _require(
        document.get("schema") == 1
        and document.get("id")
        == (
            "human-ai-collaboration-process-fidelity-cumulative-loss-"
            "accounting-poc-evidence-2026-07-27"
        )
        and document.get("date") == "2026-07-27"
        and document.get("status")
        == (
            "zero-agent-zero-dispatch-additive-cumulative-loss-"
            "accounting-poc-passed-live-not-tested"
        ),
        "Cumulative accounting evidence identity drifted",
    )
    bindings = document.get("bindings")
    _require(
        isinstance(bindings, dict)
        and set(bindings)
        == {
            "accountingContract",
            "additiveEvaluator",
            "pocBuilder",
            "frozenTraceEvaluator",
            "fixtureCorpus",
            "documentation",
        },
        "Cumulative accounting evidence binding set drifted",
    )
    for key, binding in bindings.items():
        _require(
            isinstance(binding, dict)
            and isinstance(binding.get("path"), str)
            and isinstance(binding.get("fileSha256"), str),
            f"Cumulative accounting evidence binding shape drifted: {key}",
        )
        path = root / binding["path"]
        _require(
            path.is_file()
            and _file_sha256(path).lower()
            == binding["fileSha256"].lower(),
            f"Cumulative accounting evidence binding drifted: {key}",
        )
    contract = json.loads((root / CONTRACT_PATH).read_text(encoding="utf-8"))
    _validate_contract(contract, root=root)

    replay = build_poc(root=root)
    replay_body = dict(replay)
    replay_digest = replay_body.pop("reportSha256", None)
    try:
        from .run_process_fidelity_chained_transform_trial import (
            canonical_sha256,
        )
    except ImportError:  # pragma: no cover - direct script execution
        from run_process_fidelity_chained_transform_trial import (
            canonical_sha256,
        )
    _require(
        replay_digest == canonical_sha256(replay_body),
        "Cumulative accounting replay digest drifted",
    )
    case_results = replay["results"]["caseResults"]
    cases = {item["caseId"]: item for item in case_results}
    falsifications = {
        item["id"]: item["passed"]
        for item in replay["results"]["falsificationResults"]
    }
    expected_results = {
        "validCaseCount": 2,
        "allExpectedCasesPassed": True,
        "controlCumulativeUniqueLossWeight": 0,
        "controlPeakActiveLossWeight": 0,
        "injectedCumulativeUniqueLossWeight": 6,
        "injectedPeakActiveLossWeight": 6,
        "injectedTerminalRecoveryPreservedHistoricalUniqueLoss": True,
        "injectedRepeatedLossWasNotDoubleCounted": True,
        "reintroductionWasNewButNotUniqueTwice": True,
        "firstStrictBudgetBreachWasRecorded": True,
        "unknownLossAndWeightMismatchFailedClosed": True,
    }
    _require(
        document.get("results") == expected_results
        and replay["results"]["allExpectedCasesPassed"] is True
        and set(cases)
        == {
            "control-sequence",
            "injected-detected-and-gated-recovery",
        }
        and cases["control-sequence"]["cumulativeUniqueLossWeight"] == 0
        and cases["control-sequence"]["peakActiveLossWeight"] == 0
        and cases["injected-detected-and-gated-recovery"][
            "cumulativeUniqueLossWeight"
        ]
        == 6
        and cases["injected-detected-and-gated-recovery"][
            "peakActiveLossWeight"
        ]
        == 6
        and cases["injected-detected-and-gated-recovery"][
            "terminalRecoveryDoesNotEraseHistoricalUniqueLoss"
        ]
        is True
        and cases["injected-detected-and-gated-recovery"][
            "changesProcessAcceptancePass"
        ]
        is False
        and falsifications
        == {
            "reintroduced-loss-is-new-not-unique-twice": True,
            "first-strict-budget-breach-is-recorded": True,
            "unknown-loss-and-weight-mismatch-fail-closed": True,
        },
        "Cumulative accounting evidence result drifted",
    )
    execution = document.get("execution")
    _require(
        isinstance(execution, dict)
        and execution.get("agentDispatchCount") == 0
        and execution.get("modelCallCount") == 0
        and execution.get("actualRouteObserved") is False
        and execution.get("liveDispatchAuthorized") is False
        and execution.get("externalAccessUsed") is False
        and execution.get("hostConfigurationChanged") is False
        and execution.get("formalProcessCohortCount") == 0,
        "Cumulative accounting evidence execution boundary drifted",
    )
    decision = document.get("decision")
    _require(
        isinstance(decision, dict)
        and decision.get("cumulativeAccountingMechanismPassed") is True
        and decision.get("frozenEvaluatorOrSchemaChanged") is False
        and decision.get("budgetChangesProcessAcceptance") is False
        and decision.get("endToEndProcessFidelityAssessment") == "partial"
        and decision.get("advancedSubgate")
        == "subgate.process-fidelity-boundary-and-cumulative-coverage"
        and decision.get("subgateClosed") is False,
        "Cumulative accounting evidence decision drifted",
    )
    claims = document.get("claimBoundary")
    _require(
        isinstance(claims, dict)
        and set(claims) == EXPECTED_CLAIM_KEYS
        and all(value is False for value in claims.values()),
        "Cumulative accounting evidence claim boundary drifted",
    )
    _require(
        document.get("documentation") == DOC_PATH
        and (root / DOC_PATH).is_file()
        and isinstance(document.get("claimLimit"), str),
        "Cumulative accounting documentation binding drifted",
    )
    normalized = " ".join(
        (root / DOC_PATH).read_text(encoding="utf-8").split()
    )
    for phrase in (
        "zero Agent, zero dispatch",
        "rather than being double-counted as 12 or erased back to zero",
        "does not change the existing `processAcceptancePass`",
        "does not prove live process fidelity",
        "program acceptance remains `partial`",
    ):
        _require(
            phrase in normalized,
            f"Cumulative accounting documentation missing: {phrase}",
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
    print("Process-fidelity cumulative-loss accounting evidence passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
