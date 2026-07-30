#!/usr/bin/env python3
"""Validate the chained-transform one-shot dispatch-ledger contract."""

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
    "dispatch-ledger-contract-2026-07-27.json"
)
DOC_PATH = (
    "docs/strategy/HUMAN-AI-COLLABORATION-PROCESS-FIDELITY-CHAINED-"
    "TRANSFORM-DISPATCH-LEDGER-CONTRACT-2026-07-27.md"
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
        "Dispatch ledger gained a live runtime dependency.",
    )
    for forbidden in (
        "AppServerSession(",
        "codex.exe",
        "codex app-server",
        "turn/start",
        "thread/start",
    ):
        _require(
            forbidden not in source,
            f"Dispatch ledger gained a live path: {forbidden}",
        )


def _run_contract_tests(root: Path) -> unittest.TestResult:
    suite = unittest.defaultTestLoader.discover(
        str(root / "tests"),
        pattern=(
            "test_process_fidelity_chained_transform_dispatch_ledger.py"
        ),
        top_level_dir=str(root),
    )
    stream = io.StringIO()
    result = unittest.TextTestRunner(
        stream=stream,
        verbosity=0,
    ).run(suite)
    if not result.wasSuccessful():
        raise RuntimeError(
            "Dispatch-ledger deterministic tests failed: "
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
            "dispatch-ledger-contract-2026-07-27"
        )
        and document.get("date") == "2026-07-27"
        and document.get("status")
        == (
            "same-host-cross-process-one-shot-ledger-validated-live-"
            "stopped"
        ),
        "Dispatch-ledger contract identity drifted.",
    )
    bindings = document.get("bindings")
    _require(
        isinstance(bindings, dict) and len(bindings) == 4,
        "Dispatch-ledger binding set drifted.",
    )
    for key, binding in bindings.items():
        path = root / binding["path"]
        _require(
            path.is_file()
            and _file_sha256(path).lower()
            == binding.get("fileSha256", "").lower(),
            f"Dispatch-ledger binding drifted: {key}",
        )
    _validate_no_live_runtime_path(root / bindings["dispatchLedger"]["path"])

    reuse = document.get("reuseDecision")
    _require(
        isinstance(reuse, dict)
        and reuse.get("generalCapabilityManagerCreated") is False
        and reuse.get("existingExclusiveFileLockReused") is True
        and reuse.get("existingCanonicalHashPrimitiveReused") is True
        and reuse.get("existingEventHashChainPrimitiveReused") is True
        and reuse.get("processSpecificStateMachineOnly") is True,
        "Dispatch-ledger reuse decision drifted.",
    )
    contract = document.get("ledgerContract")
    _require(
        isinstance(contract, dict)
        and contract.get("appendOnlyJsonLines") is True
        and contract.get("exclusiveSameHostFileLock") is True
        and contract.get("flushAndFsyncPerEvent") is True
        and contract.get("nonTerminatedTailFailsClosed") is True
        and contract.get("oneReservationPerAuthorization") is True
        and contract.get("oneReservationPerRunCell") is True
        and contract.get("oneReservationPerAuthorityNonce") is True
        and contract.get("oneReservationPerRawEvidenceRoot") is True
        and contract.get("oneDispatchPerHopNonce") is True
        and contract.get("automaticRetryAllowed") is False
        and contract.get("replacementDispatchAllowed") is False
        and contract.get("automaticReservationReleaseAllowed") is False
        and contract.get("formalCohortPromotionByLedgerAllowed") is False,
        "Dispatch-ledger state contract drifted.",
    )
    preflight = document.get("zeroDispatchPreflight")
    _require(
        isinstance(preflight, dict)
        and preflight.get("modelCalled") is False
        and preflight.get("modelDispatchCount") == 0
        and preflight.get("ledgerMutationPerformed") is False
        and preflight.get("advisoryOnly") is True
        and preflight.get("liveDispatchReady") is False
        and preflight.get("atomicReservationStillRequiredAfterPreflight")
        is True,
        "Zero-dispatch preflight boundary drifted.",
    )
    deterministic = document.get("deterministicValidation")
    result = _run_contract_tests(root)
    _require(
        isinstance(deterministic, dict)
        and deterministic.get("testCommand")
        == (
            "python -B -m unittest "
            "tests.test_process_fidelity_chained_transform_dispatch_ledger"
        )
        and deterministic.get("testCount") == result.testsRun == 10
        and deterministic.get("sameHostProcessContenderCount") == 2
        and deterministic.get("sameHostProcessSuccessCount") == 1
        and deterministic.get("sameHostProcessRejectedCount") == 1
        and len(deterministic.get("failureClassesCovered", [])) == 12
        and deterministic.get("allTestsPassed") is True,
        "Dispatch-ledger deterministic validation drifted.",
    )
    decision = document.get("decision")
    _require(
        isinstance(decision, dict)
        and decision.get(
            "processSpecificAtomicOneShotLedgerImplemented"
        )
        is True
        and decision.get(
            "sameHostCrossProcessOneShotReservationProved"
        )
        is True
        and decision.get("zeroDispatchPreflightContractPassed") is True
        and decision.get("corruptOrPartialLedgerFailsClosed") is True
        and decision.get(
            "failedOrAmbiguousAttemptCannotRetryOrReplace"
        )
        is True
        and decision.get("atomicReservationBoundToCurrentLiveAuthority")
        is False
        and decision.get("exactCurrentTaskLiveAuthorityBound") is False
        and decision.get("freshLiveRoutePreflightBound") is False
        and decision.get("liveDispatchReady") is False
        and decision.get("modelDispatchCount") == 0
        and decision.get("formalProcessCohortCount") == 0
        and decision.get("endToEndProcessFidelityAssessment") == "partial",
        "Dispatch-ledger decision boundary drifted.",
    )
    claims = document.get("claimBoundary")
    _require(
        isinstance(claims, dict)
        and claims
        and all(value is False for value in claims.values()),
        "Dispatch-ledger claim boundary was promoted.",
    )
    _require(
        document.get("documentation") == DOC_PATH
        and (root / DOC_PATH).is_file()
        and isinstance(document.get("claimLimit"), str),
        "Dispatch-ledger documentation binding drifted.",
    )
    normalized = " ".join(
        (root / DOC_PATH).read_text(encoding="utf-8").split()
    )
    for phrase in (
        "same-host one-shot ledger validated; live dispatch stopped",
        "exactly one accepted reservation and one rejection",
        "No automatic retry, replacement, or release is allowed",
        "`liveDispatchReady=false`",
        "Provider execution model and effort remain `unknown`",
    ):
        _require(
            phrase in normalized,
            f"Dispatch-ledger documentation missing: {phrase}",
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
    print("Process-fidelity chained-transform dispatch-ledger contract passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
