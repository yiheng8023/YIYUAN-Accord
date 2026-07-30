#!/usr/bin/env python3
"""Validate the dated zero-model software lifecycle calibration evidence."""

from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from pathlib import Path
from typing import Any

try:
    from .evaluate_human_ai_collaboration_software_lifecycle_thin_slice_calibration import (
        evaluate_capture,
    )
    from .validate_human_ai_collaboration_software_lifecycle_thin_slice_protocol import (
        EXPECTED_CLAIM_KEYS,
    )
except ImportError:  # pragma: no cover - direct script execution
    from evaluate_human_ai_collaboration_software_lifecycle_thin_slice_calibration import (
        evaluate_capture,
    )
    from validate_human_ai_collaboration_software_lifecycle_thin_slice_protocol import (
        EXPECTED_CLAIM_KEYS,
    )


ROOT = Path(__file__).resolve().parent.parent
EVIDENCE_PATH = (
    "registry/"
    "human-ai-collaboration-software-lifecycle-thin-slice-zero-model-"
    "calibration-evidence-2026-07-27.json"
)
EXPECTED_BINDINGS = {
    "protocol",
    "builder",
    "evaluator",
    "domainSuboracleEvaluator",
    "architectureSecuritySuboracleEvaluator",
    "architectureSecuritySuboracleFixture",
    "protocolValidator",
    "capture",
}
EXPECTED_FALSIFIERS = {
    "raw-artifact-byte-binding-mismatch",
    "missing-G0-through-G7-receipt",
    "same-identity-review-contract-drift",
    "changed-file-outside-allowlist",
    "unknown-telemetry-coerced-to-zero",
    "agent-output-relabelled-as-truth-source",
    "human-authority-receipt-replay",
    "zero-model-capture-claiming-live-route-or-dispatch",
    "schema-hash-or-nested-shape-drift",
    "claim-boundary-key-omission",
    "rehashed-domain-suboracle-pack-drift",
    "syntax-or-wrong-test-identity-masquerading-as-red",
    "implementation-mutated-before-red",
    "architecture-constraint-source-dependency-or-unknown-drift",
    "architecture-hypothetical-seam-or-authority-overclaim",
    "producer-self-review-or-artifact-digest-drift",
    "predeclared-security-fault-missed",
    "benign-security-canary-false-positive",
    "high-security-finding-hidden-by-summary",
    "private-security-oracle-exposed-or-reviewer-mutated-artifact",
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
        == "human-ai-collaboration-software-lifecycle-thin-slice-"
        "zero-model-calibration-evidence-2026-07-27"
        and document.get("status")
        == "mechanism-calibration-passed-no-live-or-end-to-end-claim"
        and document.get("scenarioId") == "SE-E2E-THIN-01",
        "Lifecycle calibration evidence identity drifted",
    )
    bindings = document.get("bindings")
    _require(
        isinstance(bindings, dict)
        and set(bindings) == EXPECTED_BINDINGS,
        "Lifecycle calibration binding set drifted",
    )
    for key, binding in bindings.items():
        _require(
            isinstance(binding, dict)
            and isinstance(binding.get("path"), str)
            and isinstance(binding.get("fileSha256"), str),
            f"Lifecycle calibration binding invalid: {key}",
        )
        path = root / binding["path"]
        _require(
            path.is_file()
            and binding["fileSha256"] == _file_sha256(path),
            f"Lifecycle calibration binding hash drifted: {key}",
        )
    capture_binding = bindings["capture"]
    _require(
        set(capture_binding) == {"path", "fileSha256", "captureRoot"},
        "Lifecycle capture binding shape drifted",
    )
    capture = json.loads(
        (root / capture_binding["path"]).read_text(encoding="utf-8")
    )
    result = evaluate_capture(
        capture,
        capture_root=root / capture_binding["captureRoot"],
        root=root,
    )
    _require(
        result.get("status") == "valid-calibration-only"
        and result.get("failureCodes") == [],
        "Lifecycle calibration capture no longer reevaluates cleanly",
    )
    observations = document.get("observations")
    _require(
        isinstance(observations, dict)
        and observations
        == {
            "status": "valid-calibration-only",
            "stageCount": 7,
            "gateCount": 8,
            "ledgerCount": 8,
            "agentDispatchCount": 0,
            "modelCallCount": 0,
            "actualRouteObserved": False,
            "formalLiveEvidenceEligible": False,
            "networkAccessUsed": False,
            "gitMutationUsed": False,
            "externalWriteUsed": False,
            "networkAbsenceProvedBySystemInstrumentation": False,
            "gitMutationAbsenceProvedBySystemInstrumentation": False,
            "outsideTemporaryRootWriteAbsenceProvedBySystemInstrumentation": (
                False
            ),
        },
        "Lifecycle calibration observations drifted",
    )
    _require(
        set(document.get("falsifiersExercised", []))
        == EXPECTED_FALSIFIERS
        and len(document["falsifiersExercised"]) == len(EXPECTED_FALSIFIERS),
        "Lifecycle calibration falsifier set drifted",
    )
    decision = document.get("decision")
    _require(
        isinstance(decision, dict)
        and decision
        == {
            "protocolAndSchemaMechanismCalibrated": True,
            "durableArtifactReopenAndHashRecomputePassed": True,
            "nonInheritingAuthorityReceiptMechanismCalibrated": True,
            "acceptedInvariantLedgerContinuityMechanismCalibrated": True,
            "existingDomainSuboraclesRecomputed": True,
            "positiveAndNegativeDomainControlsPassed": True,
            "disposableIncidentAndMigrationRedGreenExecuted": True,
            "redFailureClassAndStageReceiptChainCalibrated": True,
            "architectureAndIndependentSecuritySuboraclesCalibrated": True,
            "seededFaultAndBenignCanaryControlsPassed": True,
            "systemLevelSideEffectAbsenceInstrumented": False,
            "weakAgentRunStarted": False,
            "singleWeakAgentAuthorizationRequestJustified": True,
            "candidateSkillComparisonJustified": False,
            "boundedSelfAuthoredCalibrationAdapterJustified": True,
            "selfAuthoredResidualGapProved": False,
        },
        "Lifecycle calibration decision drifted",
    )
    claims = document.get("claimBoundary")
    _require(
        isinstance(claims, dict)
        and set(claims) == EXPECTED_CLAIM_KEYS
        and all(value is False for value in claims.values())
        and claims == result.get("claimBoundary"),
        "Lifecycle calibration claim boundary drifted",
    )
    doc_path = root / str(document.get("documentation"))
    _require(
        doc_path.is_file(),
        "Lifecycle calibration documentation is missing",
    )
    text = " ".join(doc_path.read_text(encoding="utf-8").split())
    for phrase in (
        "valid-calibration-only",
        "G0–G7",
        "0 Agent dispatches",
        "does not prove",
        "gpt-5.3-codex-spark",
        "three predeclared faults",
        "system-level absence proofs",
    ):
        _require(
            phrase in text,
            f"Lifecycle calibration documentation missing boundary: {phrase}",
        )


def main() -> int:
    document = json.loads((ROOT / EVIDENCE_PATH).read_text(encoding="utf-8"))
    validate_evidence(document, root=ROOT)
    print("Software lifecycle thin-slice calibration evidence validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
