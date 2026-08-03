#!/usr/bin/env python3
"""Validate the dated zero-model software lifecycle calibration evidence."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
from tempfile import TemporaryDirectory
from typing import Any
from unittest.mock import patch

try:
    from .evaluate_human_ai_collaboration_software_lifecycle_thin_slice_calibration import (
        evaluate_capture,
    )
    from .evaluate_software_lifecycle_domain_suboracles import (
        build_domain_suboracle_pack,
    )
    from .validate_human_ai_collaboration_software_lifecycle_thin_slice_protocol import (
        EXPECTED_CLAIM_KEYS,
    )
except ImportError:  # pragma: no cover - direct script execution
    from evaluate_human_ai_collaboration_software_lifecycle_thin_slice_calibration import (
        evaluate_capture,
    )
    from evaluate_software_lifecycle_domain_suboracles import (
        build_domain_suboracle_pack,
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
REPLAY_INPUT_PATH = (
    "registry/"
    "human-ai-collaboration-software-lifecycle-thin-slice-replay-input-"
    "2026-08-01.json"
)
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
INSTRUCTION_CARRIER_RECEIPT_DRIFT_FAILURES = {
    "domain-suboracle-pack-drift",
    "stage-domain-suboracle-binding-drift:observation-incident-handling",
    "stage-domain-suboracle-binding-drift:maintenance-evolution",
}


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def _file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _build_historical_domain_suboracle_pack(*, root: Path) -> dict[str, Any]:
    """Replay the frozen Windows capture without changing bound source bytes."""

    if os.name == "nt":
        return build_domain_suboracle_pack(root=root)

    original_write_text = Path.write_text
    written_paths: set[str] = set()

    def write_with_capture_newlines(
        path: Path,
        data: str,
        *args: Any,
        **kwargs: Any,
    ) -> int:
        identity = path.resolve(strict=False).as_posix()
        if identity not in written_paths:
            written_paths.add(identity)
            kwargs = dict(kwargs)
            kwargs["newline"] = "\r\n"
        return original_write_text(path, data, *args, **kwargs)

    with patch.object(Path, "write_text", write_with_capture_newlines):
        return build_domain_suboracle_pack(root=root)


def _restore_historical_source_bindings(
    *,
    replay_root: Path,
    repository_root: Path,
    source_bindings: list[dict[str, Any]],
) -> bool:
    """Materialize exact bound source blobs instead of replaying current source."""

    for binding in source_bindings:
        relative = binding.get("path")
        expected = binding.get("fileSha256")
        if not isinstance(relative, str) or not isinstance(expected, str):
            return False
        destination = (replay_root / relative).resolve(strict=False)
        if not destination.is_relative_to(replay_root.resolve()):
            return False
        if destination.is_file() and _file_sha256(destination) == expected:
            continue
        try:
            history = subprocess.run(
                [
                    "git",
                    "-C",
                    str(repository_root),
                    "log",
                    "--all",
                    "--format=%H",
                    "--",
                    relative,
                ],
                check=True,
                capture_output=True,
                text=True,
                timeout=30,
            )
        except (OSError, subprocess.SubprocessError):
            return False
        matched: bytes | None = None
        for commit in history.stdout.splitlines():
            try:
                blob = subprocess.run(
                    [
                        "git",
                        "-C",
                        str(repository_root),
                        "show",
                        f"{commit}:{relative}",
                    ],
                    check=True,
                    capture_output=True,
                    timeout=30,
                ).stdout
            except (OSError, subprocess.SubprocessError):
                continue
            if hashlib.sha256(blob).hexdigest() == expected:
                matched = blob
                break
        if matched is None:
            return False
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(matched)
    return True

def _replays_exactly_with_instruction_carrier(
    historical_pack: dict[str, Any],
    *,
    instruction_carrier_path: Path,
    root: Path,
) -> bool:
    """Rebuild the complete historical pack with its frozen AGENTS input."""

    source_bindings = historical_pack.get("sourceBindings")
    if not isinstance(source_bindings, list):
        return False
    try:
        with TemporaryDirectory(
            prefix="aah-lifecycle-frozen-carrier-replay-"
        ) as temporary:
            replay_root = Path(temporary).resolve()
            for relative in ("scripts", "tests/fixtures", "registry"):
                source = (root / relative).resolve()
                target = (replay_root / relative).resolve()
                if not source.is_dir() or not target.is_relative_to(
                    replay_root
                ):
                    return False
                shutil.copytree(
                    source,
                    target,
                    ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
                )
            if not instruction_carrier_path.is_file():
                return False
            shutil.copy2(instruction_carrier_path, replay_root / "AGENTS.md")
            if not _restore_historical_source_bindings(
                replay_root=replay_root,
                repository_root=root,
                source_bindings=source_bindings,
            ):
                return False
            replayed_pack = _build_historical_domain_suboracle_pack(
                root=replay_root
            )
    except (OSError, RuntimeError, TypeError, ValueError):
        return False
    return replayed_pack == historical_pack


def _is_instruction_carrier_receipt_only_drift(
    *,
    result: dict[str, Any],
    capture: dict[str, Any],
    capture_root: Path,
    root: Path,
    instruction_carrier_path: Path,
) -> bool:
    """Accept no historical drift beyond AGENTS-dependent receipt digests."""

    if set(result.get("failureCodes", [])) != (
        INSTRUCTION_CARRIER_RECEIPT_DRIFT_FAILURES
    ):
        return False
    artifact_id = capture.get("domainSuboraclePackArtifactId")
    rows = capture.get("rawArtifactIndex")
    if not isinstance(artifact_id, str) or not isinstance(rows, list):
        return False
    row = next(
        (
            item
            for item in rows
            if isinstance(item, dict)
            and item.get("artifactId") == artifact_id
            and isinstance(item.get("path"), str)
        ),
        None,
    )
    if row is None:
        return False
    historical_pack = json.loads(
        (capture_root / row["path"]).read_text(encoding="utf-8")
    )
    return _replays_exactly_with_instruction_carrier(
        historical_pack,
        instruction_carrier_path=instruction_carrier_path,
        root=root,
    )


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
    replay_input = json.loads(
        (root / REPLAY_INPUT_PATH).read_text(encoding="utf-8")
    )
    _require(
        replay_input.get("schema") == 1
        and replay_input.get("id")
        == (
            "human-ai-collaboration-software-lifecycle-thin-slice-"
            "replay-input-2026-08-01"
        )
        and replay_input.get("date") == "2026-08-01"
        and replay_input.get("kind")
        == "historical-instruction-carrier-replay-binding",
        "Lifecycle replay input identity drifted",
    )
    replay_evidence_binding = replay_input.get("calibrationEvidence")
    _require(
        replay_evidence_binding
        == {
            "path": EVIDENCE_PATH,
            "fileSha256": _file_sha256(root / EVIDENCE_PATH),
        },
        "Lifecycle replay evidence binding drifted",
    )
    instruction_carrier_binding = replay_input.get("instructionCarrier")
    _require(
        isinstance(instruction_carrier_binding, dict)
        and set(instruction_carrier_binding)
        == {"path", "bytes", "fileSha256"},
        "Lifecycle replay instruction carrier binding invalid",
    )
    instruction_carrier_path = root / instruction_carrier_binding["path"]
    _require(
        instruction_carrier_path.is_file()
        and instruction_carrier_path.stat().st_size
        == instruction_carrier_binding["bytes"]
        and _file_sha256(instruction_carrier_path)
        == instruction_carrier_binding["fileSha256"],
        "Lifecycle replay instruction carrier identity drifted",
    )
    _require(
        replay_input.get("claimBoundary")
        == {
            "historicalEvidenceModified": False,
            "liveAgentExecuted": False,
            "modelCalled": False,
            "currentInstructionSemanticsProved": False,
        },
        "Lifecycle replay input claim boundary drifted",
    )
    capture_binding = bindings["capture"]
    _require(
        set(capture_binding) == {"path", "fileSha256", "captureRoot"},
        "Lifecycle capture binding shape drifted",
    )
    capture = json.loads(
        (root / capture_binding["path"]).read_text(encoding="utf-8")
    )
    capture_root = root / capture_binding["captureRoot"]
    result = evaluate_capture(
        capture,
        capture_root=capture_root,
        root=root,
    )
    instruction_carrier_receipt_only_drift = (
        _is_instruction_carrier_receipt_only_drift(
            result=result,
            capture=capture,
            capture_root=capture_root,
            root=root,
            instruction_carrier_path=instruction_carrier_path,
        )
    )
    _require(
        (
            result.get("status") == "valid-calibration-only"
            and result.get("failureCodes") == []
        )
        or instruction_carrier_receipt_only_drift,
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
