#!/usr/bin/env python3
"""Compile the deny-by-default, zero-transport SEM-03 live dispatch gate."""

from __future__ import annotations

import argparse
import json
import os
import tempfile
from pathlib import Path
from typing import Any

try:
    from .build_human_ai_collaboration_semantic_authority_execution_plan import (
        ALLOWED_TREATMENTS,
        canonical_sha256,
        compile_execution_plan,
        validate_execution_plan,
    )
except ImportError:
    from build_human_ai_collaboration_semantic_authority_execution_plan import (
        ALLOWED_TREATMENTS,
        canonical_sha256,
        compile_execution_plan,
        validate_execution_plan,
    )


GATE_ID = "human-ai-collaboration-semantic-authority-live-dispatch-gate-v1"
DECISION_SHA256 = "aa030f64aef99eb41dc1c749a415a7ed6f3f3470c6d4385e800ab13306d0bfbe"
PHASE_IDS = {
    "SEM-PHASE-1-ELICIT",
    "SEM-PHASE-2-MODEL",
    "SEM-PHASE-3-SPEC",
    "SEM-PHASE-4-REVIEW-HANDOFF",
}
MATRIX_RUN_IDS = {
    "SEM-NATIVE": "SEM03-LIVE-GATE-NATIVE-001",
    "SEM-LOCAL-ADAPTED-MONOLITH": "SEM03-LIVE-GATE-LOCAL-001",
    "SEM-MATT-CURRENT-COMPOSITION": "SEM03-LIVE-GATE-CURRENT-001",
}
EXPECTED_CLAIM_BOUNDARY = {
    "liveAdapterImplemented": False,
    "dispatchReadinessProved": False,
    "loaderInvocationProved": False,
    "behavioralCausationProved": False,
    "treatmentValueProved": False,
}


def compile_zero_authority_matrix() -> dict[str, Any]:
    treatments = []
    for treatment_id in sorted(ALLOWED_TREATMENTS):
        plan = compile_execution_plan(treatment_id, MATRIX_RUN_IDS[treatment_id])
        gate = compile_dispatch_gate(plan, authority_receipt=None)
        treatments.append(
            {
                "treatmentId": treatment_id,
                "planSha256": plan["planSha256"],
                "gate": gate,
            }
        )
    report = {
        "schema": 1,
        "id": "human-ai-collaboration-semantic-authority-live-dispatch-gate-preflight-v1",
        "status": "blocked-no-live-authority",
        "treatments": treatments,
        "authorityReceiptPresent": False,
        "appServerProcessStarted": False,
        "threadStarted": False,
        "turnStarted": False,
        "modelRequestSent": False,
        "claimBoundary": dict(EXPECTED_CLAIM_BOUNDARY),
    }
    report["reportSha256"] = canonical_sha256(report)
    return report


def validate_zero_authority_matrix(report: dict[str, Any]) -> list[str]:
    failures: list[str] = []
    body = dict(report)
    digest = body.pop("reportSha256", None)
    if digest != canonical_sha256(body):
        failures.append("hard-fail-live-gate-report-digest")
    if (
        report.get("schema") != 1
        or report.get("id")
        != "human-ai-collaboration-semantic-authority-live-dispatch-gate-preflight-v1"
        or report.get("status") != "blocked-no-live-authority"
    ):
        failures.append("fail-live-gate-report-identity")
    treatments = report.get("treatments", [])
    if (
        len(treatments) != 3
        or {row.get("treatmentId") for row in treatments}
        != set(ALLOWED_TREATMENTS)
    ):
        failures.append("hard-fail-live-gate-treatment-matrix")
    for row in treatments:
        gate = row.get("gate", {})
        gate_body = dict(gate)
        gate_digest = gate_body.pop("gateSha256", None)
        if (
            gate_digest != canonical_sha256(gate_body)
            or gate.get("status") != "blocked-missing-live-authority-receipt"
            or gate.get("treatmentId") != row.get("treatmentId")
            or gate.get("planSha256") != row.get("planSha256")
            or gate.get("adapterDecisionSha256") != DECISION_SHA256
            or gate.get("mayCreateAppServerProcess") is not False
            or gate.get("modelRequestBudget") != 0
            or gate.get("authorizedPhases") != []
            or gate.get("modelRequestSent") is not False
            or gate.get("threadStarted") is not False
            or gate.get("turnStarted") is not False
        ):
            failures.append("hard-fail-live-gate-treatment-boundary")
    if (
        report.get("authorityReceiptPresent") is not False
        or report.get("appServerProcessStarted") is not False
        or report.get("threadStarted") is not False
        or report.get("turnStarted") is not False
        or report.get("modelRequestSent") is not False
    ):
        failures.append("hard-fail-live-gate-side-effect-promotion")
    claims = report.get("claimBoundary")
    if claims != EXPECTED_CLAIM_BOUNDARY:
        failures.append("hard-fail-live-gate-claim-promotion")
    return list(dict.fromkeys(failures))


def write_report_atomically(output: Path, report: dict[str, Any]) -> None:
    output = output.resolve()
    if output.exists():
        raise RuntimeError("live dispatch gate report already exists")
    output.parent.mkdir(parents=True, exist_ok=True)
    staging: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="\n",
            prefix=f".{output.name}.",
            suffix=".tmp",
            dir=output.parent,
            delete=False,
        ) as handle:
            staging = Path(handle.name)
            json.dump(report, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        if output.exists():
            raise RuntimeError("live dispatch gate report already exists")
        os.replace(staging, output)
        staging = None
    finally:
        if staging is not None and staging.exists():
            staging.unlink()


def evaluate_simulated_phase_observation(
    observation: dict[str, Any],
) -> dict[str, Any]:
    failures: list[str] = []
    if observation.get("phaseId") not in PHASE_IDS:
        failures.append("hard-fail-simulation-phase-identity")
    if observation.get("threadStart") != {
        "model": "gpt-5.3-codex-spark",
        "reasoningEffort": "low",
        "providerFallbackAllowed": False,
    }:
        failures.append("hard-fail-simulation-route")
    notifications = observation.get("notificationMethods", [])
    if "thread/tokenUsage/updated" not in notifications:
        failures.append("hard-fail-simulation-token-observation")
    if observation.get("modelReroutedObserved") is not False:
        failures.append("hard-fail-simulation-model-reroute")
    if observation.get("turnTerminalStatus") != "completed":
        failures.append("hard-fail-simulation-turn-terminal-status")
    if (
        observation.get("writeOutsidePublicRootObserved") is not False
        or observation.get("forbiddenToolObserved") is not False
    ):
        failures.append("hard-fail-simulation-effect-boundary")
    if (
        observation.get("appServerProcessExited") is not True
        or observation.get("temporaryRootRemoved") is not True
    ):
        failures.append("hard-fail-simulation-cleanup-boundary")
    required_stop_actions: list[str] = []
    if failures:
        if observation.get("turnTerminalStatus") not in {
            "completed",
            "interrupted",
            "failed",
        }:
            required_stop_actions.append("turn/interrupt")
        if observation.get("appServerProcessExited") is not True:
            required_stop_actions.append("abort-app-server-process")
        required_stop_actions.extend(
            ["stop-before-next-phase", "do-not-score-run"]
        )
    return {
        "status": (
            "simulation-phase-pass"
            if not failures
            else "simulation-phase-fail-closed"
        ),
        "failureCodes": failures,
        "requiredStopActions": required_stop_actions,
        "countsAsLiveEvidence": False,
    }


def compile_dispatch_gate(
    plan: dict[str, Any],
    *,
    authority_receipt: dict[str, Any] | None,
) -> dict[str, Any]:
    plan_failures = validate_execution_plan(plan)
    if plan_failures:
        raise RuntimeError("invalid SEM-03 execution plan: " + ", ".join(plan_failures))
    if authority_receipt is None:
        gate = {
            "schema": 1,
            "id": GATE_ID,
            "status": "blocked-missing-live-authority-receipt",
            "scenarioId": plan["scenarioId"],
            "runId": plan["runId"],
            "treatmentId": plan["treatmentId"],
            "planSha256": plan["planSha256"],
            "adapterDecisionSha256": DECISION_SHA256,
            "mayCreateAppServerProcess": False,
            "modelRequestBudget": 0,
            "authorizedPhases": [],
            "modelRequestSent": False,
            "threadStarted": False,
            "turnStarted": False,
        }
        gate["gateSha256"] = canonical_sha256(gate)
        return gate
    receipt_body = dict(authority_receipt)
    receipt_digest = receipt_body.pop("receiptSha256", None)
    expected_receipt = {
        "schema": 1,
        "id": (
            "human-ai-collaboration-semantic-authority-live-authority-"
            "receipt-v1"
        ),
        "status": "test-simulation-only",
        "authorityClass": "test-simulation",
        "scenarioId": plan["scenarioId"],
        "runId": plan["runId"],
        "treatmentId": plan["treatmentId"],
        "planSha256": plan["planSha256"],
        "adapterDecisionSha256": DECISION_SHA256,
        "modelDispatchAuthorized": False,
        "appServerProcessCreationAuthorized": False,
    }
    if receipt_digest != canonical_sha256(receipt_body) or receipt_body != expected_receipt:
        raise RuntimeError("invalid SEM-03 simulation authority receipt")
    simulated_phases = [
        {
            "phaseId": phase["id"],
            "sequence": phase["sequence"],
            "newAppServerProcessRequired": True,
            "newEphemeralThreadRequired": True,
            "requestedRoute": dict(plan["requestedRoute"]),
            "requestsTransmitted": False,
        }
        for phase in plan["lifecyclePhases"]
    ]
    gate = {
        "schema": 1,
        "id": GATE_ID,
        "status": "simulation-ready-no-live-authority",
        "scenarioId": plan["scenarioId"],
        "runId": plan["runId"],
        "treatmentId": plan["treatmentId"],
        "planSha256": plan["planSha256"],
        "adapterDecisionSha256": DECISION_SHA256,
        "simulationReceiptSha256": receipt_digest,
        "mayCreateAppServerProcess": False,
        "modelRequestBudget": 0,
        "authorizedPhases": [],
        "simulatedPhases": simulated_phases,
        "modelRequestSent": False,
        "threadStarted": False,
        "turnStarted": False,
    }
    gate["gateSha256"] = canonical_sha256(gate)
    return gate


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-report", type=Path, required=True)
    args = parser.parse_args()
    report = compile_zero_authority_matrix()
    failures = validate_zero_authority_matrix(report)
    if failures:
        for failure in failures:
            print(failure)
        return 1
    write_report_atomically(args.output_report, report)
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
