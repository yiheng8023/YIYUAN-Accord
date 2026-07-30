#!/usr/bin/env python3
"""Validate the offline chained-transform dispatch-gate contract."""

from __future__ import annotations

import argparse
import ast
import hashlib
import io
import json
from pathlib import Path
import unittest
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
EVIDENCE_PATH = (
    "registry/human-ai-collaboration-process-fidelity-chained-transform-"
    "dispatch-gate-contract-2026-07-27.json"
)
DOC_PATH = (
    "docs/strategy/HUMAN-AI-COLLABORATION-PROCESS-FIDELITY-CHAINED-"
    "TRANSFORM-DISPATCH-GATE-CONTRACT-2026-07-27.md"
)


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def _file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _validate_no_live_runtime_path(path: Path) -> None:
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source)
    imports = {
        alias.name.split(".", 1)[0]
        for node in ast.walk(tree)
        if isinstance(node, (ast.Import, ast.ImportFrom))
        for alias in node.names
    }
    _require(
        not imports.intersection(
            {"subprocess", "socket", "requests", "urllib", "httpx"}
        ),
        "Dispatch-gate contract gained a live runtime dependency.",
    )
    for forbidden in (
        "AppServerSession(",
        "subprocess.",
        "codex.exe",
        "codex app-server",
    ):
        _require(
            forbidden not in source,
            f"Dispatch-gate contract gained a live path: {forbidden}",
        )


def _run_contract_tests(root: Path) -> unittest.TestResult:
    suite = unittest.defaultTestLoader.discover(
        str(root / "tests"),
        pattern="test_process_fidelity_chained_transform_dispatch_gate.py",
        top_level_dir=str(root),
    )
    stream = io.StringIO()
    result = unittest.TextTestRunner(
        stream=stream,
        verbosity=0,
    ).run(suite)
    if not result.wasSuccessful():
        raise RuntimeError(
            "Dispatch-gate deterministic tests failed: "
            + stream.getvalue().strip()
        )
    return result


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
            "dispatch-gate-contract-2026-07-27"
        )
        and document.get("date") == "2026-07-27"
        and document.get("status")
        == (
            "offline-dispatch-authorization-and-native-receipt-contract-"
            "validated-live-stopped"
        ),
        "Dispatch-gate contract identity drifted.",
    )
    bindings = document.get("bindings")
    _require(
        isinstance(bindings, dict) and len(bindings) == 6,
        "Dispatch-gate binding set drifted.",
    )
    for key, binding in bindings.items():
        path = root / binding["path"]
        _require(
            path.is_file()
            and _file_sha256(path).lower()
            == binding.get("fileSha256", "").lower(),
            f"Dispatch-gate binding drifted: {key}",
        )
    _validate_no_live_runtime_path(root / bindings["dispatchGate"]["path"])

    contract = document.get("contract")
    _require(
        isinstance(contract, dict)
        and contract.get("oneRunCellPerAuthorityEnvelope") is True
        and contract.get("maximumAgentDispatchCount") == 3
        and contract.get("oneDispatchNoncePerHop") is True
        and contract.get("freshInvocationPerHop") is True
        and contract.get("sharedConversationStateAllowed") is False
        and contract.get("automaticRetryAllowed") is False
        and contract.get("replacementDispatchAllowed") is False
        and contract.get("strongDiagnosticAuthorized") is False
        and contract.get("toolsAllowed") == []
        and contract.get("requestedModel") == "gpt-5.3-codex-spark"
        and contract.get("requestedReasoningEffort") == "low"
        and contract.get("providerFallbackAllowed") is False
        and contract.get("privateOracleVisibility") == "commitment-only",
        "Dispatch-gate authority contract drifted.",
    )
    receipt = document.get("nativeReceiptBoundary")
    _require(
        isinstance(receipt, dict)
        and receipt.get("routeEvidenceClass")
        == "host-reported-effective-thread-route"
        and receipt.get("providerExecutionModelTelemetry") == "unknown"
        and receipt.get("providerExecutionEffortTelemetry") == "unknown"
        and receipt.get("rawClientAndServerWireEventsRequired") is True
        and receipt.get("parentTransformReceiptRequiredBetweenAgentHops")
        is True
        and receipt.get("unknownReceiptFieldsFailClosed") is True
        and receipt.get("agentSelfReportedRouteOrReceiptTrusted") is False,
        "Dispatch-gate native receipt boundary drifted.",
    )
    deterministic = document.get("deterministicValidation")
    result = _run_contract_tests(root)
    _require(
        isinstance(deterministic, dict)
        and deterministic.get("testCommand")
        == (
            "python -B -m unittest "
            "tests.test_process_fidelity_chained_transform_dispatch_gate"
        )
        and deterministic.get("testCount") == result.testsRun == 10
        and deterministic.get("allTestsPassed") is True
        and len(deterministic.get("failureClassesCovered", [])) == 11,
        "Dispatch-gate deterministic validation drifted.",
    )
    decision = document.get("decision")
    _require(
        isinstance(decision, dict)
        and decision.get("offlineAuthorityEnvelopeContractPassed") is True
        and decision.get(
            "offlineParentDerivedNativeReceiptContractPassed"
        )
        is True
        and decision.get(
            "hostReportedEffectiveThreadRouteCanBeBound"
        )
        is True
        and decision.get("providerBackendActualRouteCanBeProved") is False
        and decision.get("atomicOneShotReservationLedgerBound") is False
        and decision.get("exactCurrentTaskLiveAuthorityBound") is False
        and decision.get("liveDispatchReady") is False
        and decision.get("formalProcessCohortCount") == 0
        and decision.get("endToEndProcessFidelityAssessment") == "partial",
        "Dispatch-gate decision boundary drifted.",
    )
    claims = document.get("claimBoundary")
    _require(
        isinstance(claims, dict)
        and claims
        and all(value is False for value in claims.values()),
        "Dispatch-gate claim boundary was promoted.",
    )
    _require(
        document.get("documentation") == DOC_PATH
        and (root / DOC_PATH).is_file()
        and isinstance(document.get("claimLimit"), str),
        "Dispatch-gate documentation binding drifted.",
    )
    normalized = " ".join(
        (root / DOC_PATH).read_text(encoding="utf-8").split()
    )
    for phrase in (
        "offline contract validated; live dispatch stopped",
        "host-reported-effective-thread-route",
        "Provider execution model and effort remain `unknown`",
        "`atomicReservationLedgerBound=false`",
        "No automatic retry or replacement is allowed",
    ):
        _require(
            phrase in normalized,
            f"Dispatch-gate documentation missing: {phrase}",
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
    print("Process-fidelity chained-transform dispatch-gate contract passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
