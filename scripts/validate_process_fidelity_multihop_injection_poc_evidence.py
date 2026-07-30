#!/usr/bin/env python3
"""Validate deterministic multi-hop process-fidelity PoC evidence."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

try:
    from scripts.evaluate_process_fidelity_multihop_injection_poc import (
        evaluate_protocol,
        validate_protocol,
    )
except ModuleNotFoundError:
    from evaluate_process_fidelity_multihop_injection_poc import (
        evaluate_protocol,
        validate_protocol,
    )


ROOT = Path(__file__).resolve().parent.parent
FIXTURE_PATH = (
    "tests/fixtures/"
    "process-fidelity-multihop-injection-poc-2026-07-26.json"
)
EVALUATOR_PATH = (
    "scripts/evaluate_process_fidelity_multihop_injection_poc.py"
)
DOC_PATH = (
    "docs/strategy/"
    "PROCESS-FIDELITY-MULTIHOP-INJECTION-POC-EVIDENCE-2026-07-26.md"
)
RESULT_KEYS = (
    "id",
    "outcome",
    "detectionLatencyHops",
    "amplificationFactor",
    "recoveryDistanceHops",
    "rollbackSuccessRate",
    "maxWeightedOmissionScore",
    "maxAuthorityDriftCount",
)
EXPECTED_SUPPORTED_CONCLUSIONS = [
    (
        "The deterministic evaluator preserves an unchanged control "
        "across three transformation edges."
    ),
    (
        "The preregistered injected omission plus unauthorized assumption "
        "is detected after one hop and the final synthetic recovery packet "
        "exact-matches the frozen source anchor."
    ),
    (
        "An undetected added assumption increases weighted downstream delta "
        "from 9 to 13, producing amplification factor 13/9."
    ),
    (
        "An opaque material edge stops the evaluator instead of being "
        "promoted to process-fidelity evidence."
    ),
]
EXPECTED_UNPROVED_CONCLUSIONS = [
    "live Agent process fidelity",
    "automatic host compression behavior",
    "fresh-thread continuation behavior",
    "cross-host portability",
    "lossless end-to-end collaboration",
    "universal process-loss thresholds",
    "Skill or Hook superiority",
    "a residual gap that justifies self-authored runtime capability",
]


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate_evidence(
    evidence: dict[str, Any],
    *,
    root: Path = ROOT,
) -> None:
    expected_identity = {
        "schema": 1,
        "id": (
            "process-fidelity-multihop-injection-poc-"
            "evidence-2026-07-26"
        ),
        "date": "2026-07-26",
        "status": (
            "verified-deterministic-synthetic-poc-"
            "no-live-agent-evidence"
        ),
    }
    for key, value in expected_identity.items():
        if evidence.get(key) != value:
            raise RuntimeError(
                f"Process-fidelity PoC evidence {key} drifted"
            )

    binding = evidence.get("matrixBinding", {})
    if (
        binding.get("riskId")
        != "XCR-01-process-fidelity-and-loss"
        or binding.get("representativeLane")
        != "context-lifecycle-repository-anchored-handoff"
        or binding.get("evidenceState")
        != (
            "deterministic-synthetic-measurement-and-"
            "fail-closed-boundary-only"
        )
    ):
        raise RuntimeError("Process-fidelity PoC matrix binding drifted")

    artifacts = evidence.get("sourceArtifacts")
    expected_paths = [FIXTURE_PATH, EVALUATOR_PATH]
    if (
        not isinstance(artifacts, list)
        or [item.get("path") for item in artifacts] != expected_paths
    ):
        raise RuntimeError("Process-fidelity PoC source binding drifted")
    for item in artifacts:
        path = root / item["path"]
        if not path.is_file() or item.get("sha256") != _sha256(path):
            raise RuntimeError(
                "Process-fidelity PoC source bytes drifted: "
                f"{item['path']}"
            )

    protocol = json.loads((root / FIXTURE_PATH).read_text(encoding="utf-8"))
    report = evaluate_protocol(protocol)
    protocol_failures = validate_protocol(protocol, report)
    if protocol_failures:
        raise RuntimeError(
            "Process-fidelity PoC protocol failed closed: "
            f"{protocol_failures[0]}"
        )

    observed = evidence.get("observed", {})
    if (
        observed.get("oracleFingerprint")
        != report["oracleFingerprint"]
        or observed.get("reportSha256")
        != report["reportSha256"]
    ):
        raise RuntimeError("Process-fidelity PoC report binding drifted")
    compact_results = [
        {key: item[key] for key in RESULT_KEYS}
        for item in report["caseResults"]
    ]
    if observed.get("caseResults") != compact_results:
        raise RuntimeError("Process-fidelity PoC case results drifted")

    claim_boundary = evidence.get("claimBoundary")
    if (
        not isinstance(claim_boundary, dict)
        or claim_boundary != protocol.get("claimBoundary")
        or any(value is not False for value in claim_boundary.values())
    ):
        raise RuntimeError("Process-fidelity PoC claim boundary overclaimed")
    if (
        evidence.get("supportedConclusions")
        != EXPECTED_SUPPORTED_CONCLUSIONS
        or evidence.get("unprovedConclusions")
        != EXPECTED_UNPROVED_CONCLUSIONS
    ):
        raise RuntimeError(
            "Process-fidelity PoC conclusion boundary overclaimed"
        )

    if evidence.get("documentation") != DOC_PATH:
        raise RuntimeError("Process-fidelity PoC documentation drifted")
    doc = " ".join(
        (root / DOC_PATH).read_text(encoding="utf-8").split()
    )
    for phrase in (
        "deterministic synthetic PoC",
        "13/9",
        "opaque edge stops",
        "does not prove live Agent behavior",
        "does not justify a self-authored runtime capability",
    ):
        if phrase not in doc:
            raise RuntimeError(
                "Process-fidelity PoC documentation boundary missing: "
                f"{phrase}"
            )


def main() -> int:
    evidence_path = (
        ROOT
        / "registry"
        / "process-fidelity-multihop-injection-poc-"
        "evidence-2026-07-26.json"
    )
    evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
    validate_evidence(evidence)
    print("Process-fidelity multi-hop injection PoC evidence is valid.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
