#!/usr/bin/env python3
"""Validate bounded current-host raw-item TDD pilot evidence."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
EVIDENCE_PATH = (
    ROOT
    / "registry"
    / "human-ai-collaboration-tdd-raw-item-pilot-evidence-2026-07-26.json"
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
    _require(document.get("schema") == 1, "TDD raw pilot schema drifted")
    _require(
        document.get("status")
        == "current-host-raw-normalization-proved-agent-tdd-outcome-rejected",
        "TDD raw pilot status drifted",
    )
    host = document.get("host", {})
    _require(
        "Codex Desktop/0.145.0" in str(host.get("userAgent"))
        and host.get("platformFamily") == "windows"
        and host.get("model") == "gpt-5.3-codex-spark"
        and host.get("reasoningEffort") == "low"
        and host.get("providerFallbackAllowed") is False,
        "TDD raw pilot host boundary drifted",
    )
    authority = document.get("authority", {})
    _require(
        authority.get("phase")
        == "non-scored-disposable-instrumentation-pilot"
        and authority.get("selectedTreatment") is None
        and authority.get("formalRunCounted") is False
        and authority.get("countsTowardWeakAcceptance") is False
        and authority.get("rawArtifactsVendored") is False,
        "TDD raw pilot authority drifted",
    )
    artifacts = document.get("implementationArtifacts", {})
    for key in ("runner", "normalizer", "offlineRawItemFixtures"):
        artifact = artifacts.get(key, {})
        path = artifact.get("path")
        _require(
            isinstance(path, str)
            and (root / path).is_file()
            and _digest(artifact.get("sha256"))
            and hashlib.sha256((root / path).read_bytes()).hexdigest()
            == artifact["sha256"],
            f"TDD raw pilot implementation artifact drifted: {key}",
        )
    _require(
        artifacts["normalizer"].get("contractVersion")
        == "codex-app-server-tdd-normalizer-v2"
        and artifacts["offlineRawItemFixtures"].get("caseCount") == 15
        and artifacts["offlineRawItemFixtures"].get("matchedCaseCount") == 15,
        "TDD raw pilot normalizer fixture boundary drifted",
    )
    control = document.get("controlPlane", {})
    _require(
        control.get("sameSkillIdentitySet") is True
        and control.get("allConfigurableSkillsDisabled") is True
        and control.get("allNonConfigurableStatesPreserved") is True
        and control.get("effectiveEnabledUserSkillCount") == 0
        and control.get("effectiveEnabledSystemSkillCount") == 6
        and control.get("mcpInventoryCompletenessProved") is False
        and control.get("globalConfigStable") is True,
        "TDD raw pilot control plane drifted",
    )
    runs = {
        run.get("id"): run
        for run in document.get("runs", [])
        if isinstance(run, dict)
    }
    _require(
        set(runs) == {"tdd-raw-item-pilot-r1", "tdd-raw-item-pilot-r2"},
        "TDD raw pilot run set drifted",
    )
    positive = runs["tdd-raw-item-pilot-r1"]
    negative = runs["tdd-raw-item-pilot-r2"]
    _require(
        positive.get("normalizationStatus") == "normalized-observable"
        and positive.get("normalizationFailureCodes") == []
        and positive.get("instrumentationPilotPassed") is True
        and positive.get("agentTddProcessAccepted") is False
        and set(positive.get("agentTddFailureCodes", []))
        == {
            "valid-red-before-production-not-observed",
            "green-after-production-not-observed",
        }
        and positive.get("fullVisibleSuiteGreenObserved") is True
        and positive.get("focusedGreenObserved") is False,
        "TDD raw pilot positive case drifted",
    )
    _require(
        negative.get("normalizationStatus")
        == "normalization-incomplete-or-boundary-failed"
        and set(negative.get("normalizationFailureCodes", []))
        == {"opaque-write-command"}
        and negative.get("instrumentationPilotPassed") is False
        and negative.get("failClosedAsDesigned") is True,
        "TDD raw pilot fail-closed case drifted",
    )
    for run in runs.values():
        for artifact_key in ("rawArtifact", "reanalysisReport"):
            artifact = run.get(artifact_key, {})
            _require(
                str(artifact.get("temporaryPath", "")).startswith(".tmp/")
                and _digest(
                    artifact.get("sha256")
                    if artifact_key == "rawArtifact"
                    else artifact.get("fileSha256")
                ),
                f"TDD raw pilot temporary artifact boundary drifted: {run.get('id')}",
            )
            path = root / artifact["temporaryPath"]
            if path.is_file():
                expected = (
                    artifact["sha256"]
                    if artifact_key == "rawArtifact"
                    else artifact["fileSha256"]
                )
                _require(
                    hashlib.sha256(path.read_bytes()).hexdigest() == expected,
                    f"TDD raw pilot retained artifact hash drifted: {path}",
                )
    decision = document.get("decision", {})
    _require(
        decision.get("currentHostRawEventCaptureReadyForFormalRunner") is True
        and decision.get("currentHostRawEventNormalizationReadyForFormalRunner")
        is True
        and decision.get("agentTddProcessPassed") is False
        and decision.get("formalRunnerReady") is False
        and len(decision.get("remainingFormalRunnerGaps", [])) == 3,
        "TDD raw pilot decision boundary drifted",
    )
    claims = document.get("claimBoundary", {})
    _require(
        claims.get("provesCurrentHost0145RawEventCapture") is True
        and claims.get("provesCurrentHost0145RawEventNormalization") is True
        and claims.get("provesUnknownOrOpaqueEventsFailClosed") is True
        and claims.get("provesAgentTddAbility") is False
        and claims.get("provesWeakAgentAcceptance") is False
        and claims.get("provesNoUnobservedTransientWrite") is False
        and claims.get("provesCrossHostSchemaStability") is False
        and claims.get("provesDynamicMcpLifecycle") is False
        and claims.get("formalLiveRunsStarted") is False,
        "TDD raw pilot claim boundary drifted",
    )
    documentation = document.get("documentation")
    _require(
        isinstance(documentation, str) and (root / documentation).is_file(),
        "TDD raw pilot documentation missing",
    )
    text = " ".join(
        (root / documentation).read_text(encoding="utf-8").split()
    )
    for phrase in (
        "separates measurement validity from Agent performance",
        "did not pass the TDD behavior contract",
        "failed write-capable command could have an unobserved transient effect",
        "does not prove cross-host schema stability",
        "At this pilot checkpoint, formal three-arm repetitions remained blocked",
    ):
        _require(
            phrase in text,
            f"TDD raw pilot documentation boundary missing: {phrase}",
        )


def main() -> int:
    document = json.loads(EVIDENCE_PATH.read_text(encoding="utf-8"))
    validate_evidence(document)
    print("human-ai collaboration TDD raw-item pilot evidence: valid")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
