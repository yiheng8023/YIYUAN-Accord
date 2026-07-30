#!/usr/bin/env python3
"""Validate the quarantined v1 process-fidelity calibration evidence."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
EVIDENCE_PATH = (
    "registry/"
    "human-ai-collaboration-process-fidelity-v1-calibration-abort-2026-07-27.json"
)
V1_PROTOCOL_PATH = (
    "registry/"
    "human-ai-collaboration-process-fidelity-information-equivalent-"
    "trial-protocol-2026-07-27.json"
)
V2_FIXTURE_PATH = (
    "tests/fixtures/"
    "human-ai-collaboration-process-fidelity-research-oracle-v2-2026-07-27.json"
)
DOC_PATH = (
    "docs/strategy/"
    "HUMAN-AI-COLLABORATION-PROCESS-FIDELITY-V1-CALIBRATION-ABORT-"
    "2026-07-27.md"
)


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def _load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    _require(isinstance(value, dict), f"Expected JSON object: {path}")
    return value


def _file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate_evidence(
    evidence: dict[str, Any],
    *,
    root: Path = ROOT,
) -> None:
    _require(
        evidence.get("id")
        == "human-ai-collaboration-process-fidelity-v1-calibration-abort-2026-07-27"
        and evidence.get("status")
        == "measurement-ambiguous-v1-cohort-aborted",
        "V1 calibration identity or status drifted",
    )
    authority = evidence.get("authorityBoundary")
    _require(
        isinstance(authority, dict)
        and authority.get("liveDispatchWasSeparatelyAuthorized") is True
        and authority.get("dispatchedTaskCount") == 1
        and authority.get("remainingPlannedTaskCount") == 8
        and authority.get("remainingTasksDispatched") is False
        and authority.get("candidateCapabilityExecuted") is False
        and authority.get("gitCommitOrPushPerformed") is False,
        "V1 calibration authority boundary drifted",
    )

    binding = evidence.get("v1ProtocolBinding")
    _require(
        isinstance(binding, dict)
        and binding.get("path") == V1_PROTOCOL_PATH
        and binding.get("fileSha256AtDispatch")
        == _file_sha256(root / V1_PROTOCOL_PATH)
        and binding.get("fixtureId")
        == "fixture.synthetic-conflicting-claims-v1",
        "V1 calibration protocol binding drifted",
    )
    run = evidence.get("runEvidence")
    _require(
        isinstance(run, dict)
        and run.get("informationArmId") == "complete-single-turn"
        and run.get("repetition") == 1
        and run.get("requestedAndObservedModel") == "gpt-5.3-codex-spark"
        and run.get("requestedAndObservedReasoningEffort") == "low"
        and run.get("providerFallbackAllowed") is False
        and run.get("failureCodes")
        == ["claim-oracle-mismatch", "unsupported-conclusion"],
        "V1 calibration run evidence drifted",
    )
    submission = run.get("submission")
    claims = submission.get("claims") if isinstance(submission, dict) else None
    _require(
        isinstance(claims, list)
        and [item.get("id") for item in claims]
        == ["C1", "C2", "C3", "C4", "C5"]
        and claims[2].get("state") == "contradicted"
        and submission.get("unsupportedConclusionCount") == 3
        and submission.get("externalAccessUsed") is False
        and submission.get("writePerformed") is False,
        "V1 calibration structured submission drifted",
    )

    design = evidence.get("designValidity")
    _require(
        isinstance(design, dict)
        and design.get("status") == "invalid-design-no-semantic-comparison"
        and all(
            design.get(key) is False
            for key in (
                "v1TaskSemanticsUnambiguous",
                "v1PrivateOracleIndependentlyValidated",
                "v1UnsupportedConclusionCountSemanticsDefined",
                "v1SourceIdCompletenessSemanticsDefined",
                "sourceBackedRuntimeOracleIsolationProved",
                "countsAsWeakAgentCapabilityFailure",
                "countsAsValidThreeArmRepetition",
                "countsAsProcessFidelityComparison",
                "countsAsEndToEndProcessFidelityAcceptance",
            )
        ),
        "V1 calibration design invalidity was weakened",
    )
    decision = evidence.get("decision")
    _require(
        isinstance(decision, dict)
        and decision.get("cohortStoppedAtFirstFailure") is True
        and decision.get("remainingV1RunsCancelled") is True
        and decision.get("v1ArtifactsPreservedAsHistoricalDiagnostic") is True
        and decision.get("v1RunMayNotSupportAgentOrArmRanking") is True
        and decision.get("versionedV2FixtureRequired") is True
        and decision.get("versionedV2ProtocolRequiredBeforeDispatch") is True
        and decision.get("sourceBackedScopedReadBoundaryRequiredBeforeDispatch")
        is True
        and decision.get("weakAgentRemainsPrimaryAcceptanceRoute") is True
        and decision.get("strongAgentMayOnlyBeUsedForConditionalDiagnosis")
        is True,
        "V1 calibration decision boundary drifted",
    )

    v2_fixture = _load(root / V2_FIXTURE_PATH).get("researchOracle")
    _require(
        isinstance(v2_fixture, dict)
        and v2_fixture.get("fixtureId")
        == "fixture.synthetic-conflicting-claims-v2"
        and v2_fixture.get("semanticContractVersion")
        == "research-claim-entailment-v2",
        "Required versioned v2 fixture is missing",
    )

    raw_path = run.get("rawTemporaryReportPath")
    _require(isinstance(raw_path, str), "Raw report lifecycle path is missing")
    raw = root / raw_path
    if raw.is_file():
        _require(
            _file_sha256(raw) == run.get("rawTemporaryReportFileSha256"),
            "Temporary raw calibration report drifted",
        )

    _require(
        evidence.get("documentation") == DOC_PATH,
        "V1 calibration documentation path drifted",
    )
    normalized = " ".join((root / DOC_PATH).read_text(encoding="utf-8").split())
    for phrase in (
        "measurement defects",
        "cannot be counted as a valid weak-Agent failure",
        "parent-owned scoped read interface",
        "three arms must restart from zero",
        "temporary cleanup debt",
    ):
        _require(phrase in normalized, f"V1 calibration boundary missing: {phrase}")


def main() -> int:
    validate_evidence(_load(ROOT / EVIDENCE_PATH))
    print("process-fidelity v1 calibration abort evidence: valid")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
