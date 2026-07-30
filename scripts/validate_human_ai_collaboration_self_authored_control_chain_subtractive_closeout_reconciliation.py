#!/usr/bin/env python3
"""Validate subtractive closeout reconciliation for the control chain."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
RECORD_PATH = Path(
    "registry/human-ai-collaboration-self-authored-control-chain-subtractive-"
    "closeout-reconciliation-2026-07-28.json"
)


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def validate_reconciliation(document: dict, *, root: Path = ROOT) -> None:
    _require(
        document.get("schema") == 1
        and document.get("status")
        == (
            "static-subtractive-reconciliation-complete-live-value-and-"
            "program-closeout-open"
        ),
        "Subtractive reconciliation identity drifted",
    )
    sources = document.get("sourceBindings", {})
    expected_local_sources = {
        "carrierAudit",
        "factorialProtocol",
        "loaderHookObservabilityAdmission",
        "currentEcosystemEvidence",
        "overlapMatrix",
        "sourceAuthorityReconciliation",
        "runtimeAndCcDrift",
        "externalScenarioCoverage",
        "programAcceptanceReconciliation",
    }
    _require(
        expected_local_sources.issubset(sources)
        and all((root / sources[key]).is_file() for key in expected_local_sources)
        and sources.get("officialAppServerReadme")
        == "https://github.com/openai/codex/blob/main/codex-rs/app-server/README.md",
        "Subtractive reconciliation source binding drifted",
    )
    _require(
        document.get("comparisonOrderApplied")
        == [
            "native-or-runtime",
            "official",
            "reviewed-maintained-external",
            "composition",
            "self-authored-only-for-evidenced-residual-gap",
        ],
        "Subtractive comparison order drifted",
    )
    recalibration = document.get("rootAndCausalityRecalibration20260729", {})
    _require(
        recalibration.get("commonAgentsSkillsRootMustBeRetained") is True
        and recalibration.get("rootRetentionImpliesPayloadRetention") is False
        and recalibration.get("hostSpecificSkillPackagesMayDiffer") is True
        and recalibration.get("claudeCodexByteParityRequired") is False
        and recalibration.get(
            "currentCodexTurnImplicitSelectionLikeBehaviorObserved"
        )
        is True
        and recalibration.get("nativeRuntimeCauseProved") is False
        and recalibration.get("selfAuthoredSkillCauseProved") is False
        and recalibration.get("hookCauseProved") is False
        and recalibration.get("composedCauseProved") is False
        and recalibration.get("nativeFirstCausalAblationRequired") is False
        and recalibration.get(
            "nativeImplicitInvocationCapabilityProvedCurrentHost"
        )
        is True
        and recalibration.get("selfAuthoredIncrementalValueAblationRequired")
        is True
        and recalibration.get("liveMutationAuthorized") is False,
        "Subtractive root and causality recalibration drifted",
    )
    layers = {
        row["layer"]: row for row in document.get("layerReconciliation", [])
    }
    _require(
        set(layers)
        == {
            "negative-boundary-intake",
            "cross-ecosystem-capability-routing",
            "claim-sufficient-closeout",
            "hook-recall",
            "host-loading-and-continuity",
        }
        and all(row.get("residualAssessment") for row in layers.values()),
        "Subtractive layer coverage drifted",
    )
    lifecycle = document.get("lifecycleCoverage", {})
    _require(
        lifecycle.get("notACompleteSoftwareLifecycle") is True
        and len(lifecycle.get("coveredControlCheckpoints", [])) == 3
        and len(lifecycle.get("notCoveredAsDomainExecutionByThisChain", []))
        == 7
        and lifecycle.get("domainCoverageMetadataProvesValue") is False,
        "Subtractive lifecycle boundary drifted",
    )
    findings = document.get("overlapAndConflictFindings", [])
    _require(
        {row.get("id") for row in findings}
        == {f"SUB-{index:02d}" for index in range(1, 8)}
        and all(row.get("severity") in {"medium", "high"} for row in findings),
        "Subtractive finding coverage drifted",
    )
    decisions = document.get("subtractiveDecisions", {})
    expected_true = {
        "retainThreeSkillsProvisionallyForFrozenAblation",
        "reuseMattHandoffBeforeAuthoringAnotherGenericHandoff",
        "reuseReviewedDomainWorkflowsBeforeAuthoringDomainSkills",
        "allowFinalAdmittedSelfAuthoredPayloadCountToBeZero",
    }
    _require(
        all(decisions.get(key) is True for key in expected_true)
        and all(
            value is False
            for key, value in decisions.items()
            if key not in expected_true
        ),
        "Subtractive disposition overclaimed",
    )
    closeout = {
        row["requirement"]: row["status"]
        for row in document.get("closeoutCoverage", [])
    }
    _require(
        closeout
        == {
            "exact current Matt dependency-complete no-model exposure": "covered",
            "three-Skill chain and Hook static overlap, authority, lifecycle, and fallback audit": "covered-with-limits",
            "weak-model factorial value attribution": "blocked",
            "portfolio retirement, replacement, installation, or deduplication decision": "needs-verification",
            "three-lane program acceptance and final cleanup": "cannot-close",
        },
        "Subtractive closeout status drifted",
    )
    authority = document.get("authorityBoundary", {})
    _require(
        authority and all(value is False for value in authority.values()),
        "Subtractive authority expanded",
    )
    next_gate = document.get("nextGate", {})
    _require(
        next_gate.get("programCloseoutSupportedNow") is False
        and "exact-loader" in next_gate.get("recommended", "")
        and "owner decision"
        in next_gate.get("alternativeRequiresOwnerDecision", "").lower(),
        "Subtractive next gate drifted",
    )
    documentation = document.get("documentation")
    _require(
        isinstance(documentation, str) and (root / documentation).is_file(),
        "Subtractive documentation binding drifted",
    )


def main() -> int:
    document = json.loads((ROOT / RECORD_PATH).read_text(encoding="utf-8"))
    validate_reconciliation(document, root=ROOT)
    print("Self-authored control-chain subtractive closeout verified.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
