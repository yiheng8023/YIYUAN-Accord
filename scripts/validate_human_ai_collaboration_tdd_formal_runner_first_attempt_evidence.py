#!/usr/bin/env python3
"""Validate the first integrated formal TDD runner attempt."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
EVIDENCE_PATH = (
    ROOT
    / "registry"
    / "human-ai-collaboration-tdd-formal-runner-first-attempt-evidence-2026-07-26.json"
)


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def _digest(value: Any) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(character in "0123456789abcdef" for character in value)
    )


def validate_evidence(
    document: dict[str, Any],
    *,
    root: Path = ROOT,
) -> None:
    _require(document.get("schema") == 1, "TDD formal attempt schema drifted")
    _require(
        document.get("status")
        == "formal-runner-completed-first-native-attempt-invalid-not-counted"
        and document.get("arm") == "SE-TDD-NATIVE-SPARK"
        and document.get("selectedTreatment") is None,
        "TDD formal attempt identity drifted",
    )
    artifacts = document.get("implementationArtifacts", {})
    for key in ("formalRunner", "rawNormalizer", "parentOutcomeEvaluator"):
        artifact = artifacts.get(key, {})
        path = artifact.get("path")
        _require(
            isinstance(path, str)
            and (root / path).is_file()
            and _digest(artifact.get("sha256"))
            and hashlib.sha256((root / path).read_bytes()).hexdigest()
            == artifact["sha256"],
            f"TDD formal attempt implementation drifted: {key}",
        )
    historical_runner = artifacts.get("formalRunnerAtExecution", {})
    _require(
        _digest(historical_runner.get("sha256"))
        and historical_runner.get("currentFileMatches") is False
        and historical_runner.get("retainedHistoricalBytes") is False
        and historical_runner.get("identitySource")
        == "same-turn pre-execution SHA-256 observation",
        "TDD formal attempt historical runner identity drifted",
    )
    retained = document.get("retainedTemporaryEvidence", {})
    _require(
        artifacts["rawNormalizer"].get("contractVersion")
        == "codex-app-server-tdd-normalizer-v2"
        and retained.get("reanalysisReport", {}).get(
            "normalizerContractVersion"
        )
        == "codex-app-server-tdd-normalizer-v2",
        "TDD formal attempt reanalysis contract drifted",
    )
    _require(
        retained.get("vendored") is False
        and retained.get("cleanupAuthorized") is False,
        "TDD formal attempt retention boundary drifted",
    )
    for key, hash_key in (
        ("rawArtifact", "sha256"),
        ("reanalysisReport", "fileSha256"),
    ):
        artifact = retained.get(key, {})
        path = artifact.get("path")
        _require(
            isinstance(path, str)
            and path.startswith(".tmp/")
            and _digest(artifact.get(hash_key)),
            f"TDD formal attempt temporary artifact drifted: {key}",
        )
        candidate = root / path
        if candidate.is_file():
            _require(
                hashlib.sha256(candidate.read_bytes()).hexdigest()
                == artifact[hash_key],
                f"TDD formal attempt retained hash drifted: {key}",
            )
    measurement = document.get("measurement", {})
    _require(
        measurement.get("normalizationStatus") == "normalized-observable"
        and measurement.get("normalizationFailureCodes") == []
        and measurement.get("orderedTimelineStatus")
        == "rejected-offline-tdd-timeline"
        and measurement.get("orderedTimelineFailureCodes")
        == ["green-after-production-not-observed"],
        "TDD formal attempt measurement drifted",
    )
    outcome = document.get("parentOutcome", {})
    _require(
        outcome.get("status") == "parent-outcome-rejected"
        and outcome.get("visibleSuiteGreen") is True
        and outcome.get("hiddenOracleGreen") is True
        and outcome.get("mutantCount") == 7
        and outcome.get("killedMutantCount") == 5
        and set(outcome.get("survivingMutantIds", []))
        == {"nonpositive-delay-accepted", "string-schedule-accepted"}
        and outcome.get("hiddenOracleWrittenIntoTrial") is False
        and outcome.get("mutantSourcesWrittenIntoTrial") is False,
        "TDD formal attempt parent outcome drifted",
    )
    classification = document.get("classification", {})
    _require(
        classification.get("status")
        == "invalid-formal-weak-agent-tdd-repetition"
        and classification.get("formalRunCounted") is False
        and classification.get("countsTowardWeakAcceptance") is False
        and classification.get("validFormalRepetitionCountAfterAttempt") == 0,
        "TDD formal attempt classification drifted",
    )
    decision = document.get("decision", {})
    _require(
        decision.get("formalRunnerIntegratedPathObserved") is True
        and decision.get("parentHiddenOracleExecutable") is True
        and decision.get("predeclaredMutantsExecutable") is True
        and decision.get("formalRunnerReadyForFurtherBoundedAttempts") is True
        and decision.get("nativeValidRepetitionCount") == 0
        and "at most two additional native attempts"
        in str(decision.get("nextBoundedAction")),
        "TDD formal attempt decision boundary drifted",
    )
    claims = document.get("claimBoundary", {})
    _require(
        claims.get("provesBoundFormalRunnerIntegration") is True
        and claims.get("provesNativeWeakAgentTddAcceptance") is False
        and claims.get("provesTreatmentDelivery") is False
        and claims.get("provesSkillCausation") is False
        and claims.get("provesCandidatePreference") is False
        and claims.get("provesProductionReadiness") is False
        and claims.get("provesCrossHostValue") is False,
        "TDD formal attempt claim boundary drifted",
    )
    documentation = document.get("documentation")
    _require(
        isinstance(documentation, str) and (root / documentation).is_file(),
        "TDD formal attempt documentation missing",
    )
    text = " ".join(
        (root / documentation).read_text(encoding="utf-8").split()
    )
    for phrase in (
        "invalid and does not count as a repetition",
        "final green did not satisfy the hard standard",
        "killed only five of seven predeclared mutants",
        "process and independent test quality lose required information",
        "At most two more native attempts",
    ):
        _require(
            phrase in text,
            f"TDD formal attempt documentation boundary missing: {phrase}",
        )


def main() -> int:
    document = json.loads(EVIDENCE_PATH.read_text(encoding="utf-8"))
    validate_evidence(document)
    print("human-ai collaboration TDD formal runner first attempt: valid")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
