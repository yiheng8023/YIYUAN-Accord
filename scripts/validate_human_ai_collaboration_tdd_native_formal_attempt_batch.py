#!/usr/bin/env python3
"""Validate the capped native weak-Agent TDD formal-attempt batch."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
EVIDENCE_PATH = (
    ROOT
    / "registry"
    / "human-ai-collaboration-tdd-native-formal-attempt-batch-2026-07-26.json"
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


def _validate_artifact(
    artifact: dict[str, Any],
    *,
    path_key: str,
    hash_key: str,
    root: Path,
    label: str,
) -> Path:
    path_value = artifact.get(path_key)
    _require(
        isinstance(path_value, str)
        and path_value.startswith(".tmp/")
        and _digest(artifact.get(hash_key)),
        f"TDD native batch artifact metadata drifted: {label}",
    )
    path = root / path_value
    if path.is_file():
        _require(
            hashlib.sha256(path.read_bytes()).hexdigest()
            == artifact[hash_key],
            f"TDD native batch retained artifact hash drifted: {label}",
        )
    return path


def validate_evidence(
    document: dict[str, Any],
    *,
    root: Path = ROOT,
) -> None:
    _require(
        document.get("schema") == 1
        and document.get("status")
        == "native-attempt-cap-reached-zero-valid-comparative-inference-blocked"
        and document.get("arm") == "SE-TDD-NATIVE-SPARK"
        and document.get("selectedTreatment") is None,
        "TDD native batch identity drifted",
    )
    control = document.get("controlPlane", {})
    _require(
        control.get("model") == "gpt-5.3-codex-spark"
        and control.get("reasoningEffort") == "low"
        and control.get("providerFallbackAllowed") is False
        and control.get("approvalPolicy") == "never"
        and control.get("networkAccess") is False
        and control.get("allConfigurableSkillsDisabled") is True
        and control.get("mcpInventoryCompletenessProved") is False,
        "TDD native batch control plane drifted",
    )
    artifacts = document.get("analysisArtifacts", {})
    for key in ("normalizer", "parentOutcomeEvaluator", "formalRunner"):
        artifact = artifacts.get(key, {})
        path = artifact.get("path")
        _require(
            isinstance(path, str)
            and (root / path).is_file()
            and _digest(artifact.get("sha256"))
            and hashlib.sha256((root / path).read_bytes()).hexdigest()
            == artifact["sha256"],
            f"TDD native batch analysis artifact drifted: {key}",
        )
    _require(
        artifacts["normalizer"].get("contractVersion")
        == "codex-app-server-tdd-normalizer-v2",
        "TDD native batch normalizer version drifted",
    )
    policy = document.get("attemptPolicy", {})
    _require(
        policy.get("nativeAttemptCap") == 3
        and policy.get("attempted") == 3
        and policy.get("valid") == 0
        and policy.get("invalid") == 3
        and policy.get("replacementRunsUsedToReachThreePasses") is False
        and policy.get("sameCompleteFailureSignatureObservedThreeTimes")
        is False,
        "TDD native batch attempt policy drifted",
    )
    attempts = document.get("attempts", [])
    _require(
        isinstance(attempts, list)
        and [attempt.get("id") for attempt in attempts]
        == ["native-formal-r1", "native-formal-r2", "native-formal-r3"],
        "TDD native batch attempt set drifted",
    )
    expected_classification_failures = {
        "native-formal-r1": {
            "ordered-tdd-process-rejected",
            "parent-owned-final-outcome-rejected",
        },
        "native-formal-r2": {
            "raw-event-normalization-incomplete",
            "ordered-tdd-process-rejected",
            "parent-owned-final-outcome-rejected",
        },
        "native-formal-r3": {"ordered-tdd-process-rejected"},
    }
    reports: dict[str, dict[str, Any]] = {}
    for attempt in attempts:
        attempt_id = attempt["id"]
        raw_path = _validate_artifact(
            attempt["rawArtifact"],
            path_key="path",
            hash_key="sha256",
            root=root,
            label=f"{attempt_id}:raw",
        )
        report_path = _validate_artifact(
            attempt["analysisReport"],
            path_key="path",
            hash_key="fileSha256",
            root=root,
            label=f"{attempt_id}:report",
        )
        _require(
            attempt["classification"].get("formalRunCounted") is False
            and set(attempt["classification"].get("failureCodes", []))
            == expected_classification_failures[attempt_id],
            f"TDD native batch classification drifted: {attempt_id}",
        )
        _require(
            attempt["parentOutcome"].get("mutantCount") == 7
            and attempt["parentOutcome"].get("hiddenOracleTestCount") == 2,
            f"TDD native batch parent outcome boundary drifted: {attempt_id}",
        )
        if report_path.is_file():
            report = json.loads(report_path.read_text(encoding="utf-8"))
            reports[attempt_id] = report
            _require(
                report.get("reportSha256")
                == attempt["analysisReport"]["canonicalReportSha256"]
                and report_path.stat().st_size
                == attempt["analysisReport"]["bytes"]
                and report.get("rawArtifact", {}).get("sha256")
                == attempt["rawArtifact"]["sha256"]
                and report.get("rawArtifact", {}).get("bytes")
                == attempt["rawArtifact"]["bytes"]
                and report.get("thread", {}).get("threadId")
                == attempt["threadId"]
                and report.get("thread", {}).get("turnId")
                == attempt["turnId"]
                and report.get("classification", {}).get("formalRunCounted")
                is False
                and set(
                    report.get("classification", {}).get(
                        "failureCodes",
                        [],
                    )
                )
                == expected_classification_failures[attempt_id],
                f"TDD native batch report binding drifted: {attempt_id}",
            )
        _require(
            not raw_path.is_file()
            or attempt["rawArtifact"].get("bytes") == raw_path.stat().st_size,
            f"TDD native batch raw size drifted: {attempt_id}",
        )
    if reports:
        _require(
            reports["native-formal-r1"]["parentOutcome"]["killedMutantCount"]
            == 5
            and reports["native-formal-r2"]["parentOutcome"][
                "killedMutantCount"
            ]
            == 5
            and reports["native-formal-r3"]["parentOutcome"][
                "killedMutantCount"
            ]
            == 7
            and all(
                report["offlineTimeline"]["status"]
                == "rejected-offline-tdd-timeline"
                for report in reports.values()
            ),
            "TDD native batch cross-report finding drifted",
        )
    finding = document.get("crossAttemptFinding", {})
    _require(
        finding.get("distinctTrialRoots") is True
        and finding.get("distinctThreadIds") is True
        and finding.get("distinctTurnIds") is True
        and finding.get("sameTaskSha256") is True
        and finding.get("allFinalVisibleSuitesGreen") is True
        and finding.get("allHiddenOraclesGreen") is True
        and finding.get("allOrderedTddProcessesRejected") is True
        and finding.get("measurementObservableAttemptCount") == 2
        and finding.get("parentOutcomeAcceptedAttemptCount") == 1
        and finding.get("validFormalRepetitionCount") == 0
        and finding.get("completeFailureSignaturesHeterogeneous") is True,
        "TDD native batch cross-attempt finding drifted",
    )
    decision = document.get("decision", {})
    _require(
        decision.get("nativeArmPaused") is True
        and decision.get("nativeValidComparisonBaselineAvailable") is False
        and decision.get("formalTreatmentComparisonAuthorizedByThisEvidence")
        is False
        and decision.get("mattOrSuperpowersPreferenceProved") is False
        and decision.get("selfAuthoredResidualGapProved") is False
        and decision.get(
            "nonComparativeTreatmentDiagnosticEligibleAfterPreregistration"
        )
        is True,
        "TDD native batch decision boundary drifted",
    )
    claims = document.get("claimBoundary", {})
    _require(
        claims.get("provesBoundNativeAttemptBatch") is True
        and claims.get("provesNativeWeakAgentTddAcceptance") is False
        and claims.get("provesNativeInability") is False
        and claims.get("provesTreatmentValue") is False
        and claims.get("provesSkillDelivery") is False
        and claims.get("provesSkillCausation") is False
        and claims.get("provesCandidatePreference") is False
        and claims.get("provesProductionReadiness") is False,
        "TDD native batch claim boundary drifted",
    )
    documentation = document.get("documentation")
    _require(
        isinstance(documentation, str) and (root / documentation).is_file(),
        "TDD native batch documentation missing",
    )
    text = " ".join(
        (root / documentation).read_text(encoding="utf-8").split()
    )
    for phrase in (
        "None counts as a valid formal repetition",
        "Final green did not erase process loss",
        "complete failure signatures are heterogeneous",
        "There is no valid native comparison baseline",
        "must not now be run as formal comparative treatment arms",
    ):
        _require(
            phrase in text,
            f"TDD native batch documentation boundary missing: {phrase}",
        )


def main() -> int:
    document = json.loads(EVIDENCE_PATH.read_text(encoding="utf-8"))
    validate_evidence(document)
    print("human-ai collaboration TDD native formal attempt batch: valid")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
