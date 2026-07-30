#!/usr/bin/env python3
"""Validate the second weak-Agent live comparison evidence."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
EVIDENCE_PATH = (
    "registry/"
    "human-ai-collaboration-weak-agent-live-comparison-batch-02-2026-07-24.json"
)
PROTOCOL_PATH = (
    "registry/"
    "human-ai-collaboration-comparative-protocol-batch-01-2026-07-24.json"
)


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def validate_live_comparison_batch_02(
    document: dict[str, Any],
    *,
    root: Path = ROOT,
    protocol: dict[str, Any] | None = None,
) -> None:
    _require(document.get("schema") == 1, "Batch 02 schema must be 1")
    _require(
        document.get("status")
        == "three-paired-observations-complete-association-not-causation",
        "Batch 02 status overclaimed or drifted",
    )
    _require(
        document.get("scenarioId") == "SE-OPS-INCIDENT-01"
        and document.get("fixtureId")
        == "fixture.python-tenant-policy-cache-incident-v1",
        "Batch 02 scenario binding drifted",
    )
    _require(
        document.get("parentProtocol") == PROTOCOL_PATH,
        "Batch 02 parent protocol drifted",
    )

    authority = document.get("authorityBoundary", {})
    _require(
        authority.get("disposableRootsOnly") is True,
        "Batch 02 disposable-root boundary drifted",
    )
    for key in (
        "networkAllowed",
        "mcpOrAppAllowed",
        "dependencyInstallAllowed",
        "globalConfigMutationAllowed",
        "gitMutationAllowed",
        "externalWriteAllowed",
        "productionRecoveryClaimAllowed",
        "calibrationWriteAllowed",
    ):
        _require(authority.get(key) is False, f"Batch 02 authority promoted: {key}")

    control = document.get("controlPlaneAtRun", {})
    _require(
        control.get("model") == "gpt-5.3-codex-spark"
        and control.get("reasoningEffort") == "low"
        and control.get("providerFallbackAllowed") is False,
        "Batch 02 weak-model control drifted",
    )
    for key in (
        "runnerSha256",
        "builderSha256",
        "protocolSha256",
        "publicTaskPromptSha256",
        "baselinePolicyCacheSha256",
        "baselineVisibleTestSha256",
        "baselineEvidenceStubSha256",
    ):
        _require(
            isinstance(control.get(key), str) and len(control[key]) == 64,
            f"Batch 02 control digest missing: {key}",
        )

    candidate = document.get("candidate", {})
    _require(
        candidate.get("id") == "cc.diagnose"
        and candidate.get("sha256")
        == "28886402bbfa0470248086eab9106a103b964b76ae9496e63ff0c8a6761b6d13"
        and candidate.get("exactHistoricalMattCommit")
        == "7afa86d3a5dd96edde06ffa014e16c64e733681e",
        "Batch 02 candidate pin drifted",
    )
    _require(
        candidate.get("equalsCurrentMattMain") is False
        and candidate.get("selectedExposureProved") is True
        and candidate.get("structuredSkillInputSent") is True
        and candidate.get("hostAcceptedStructuredSkillInput") is True
        and candidate.get("loaderInvocationProved") is False
        and candidate.get("instructionsReachedModelProved") is False,
        "Batch 02 candidate claim boundary drifted",
    )

    runs = {
        item.get("id"): item
        for item in document.get("runs", [])
        if isinstance(item, dict)
    }
    expected_run_ids = {
        f"{arm_id}:r{repetition}"
        for arm_id in ("SE-OPS-NATIVE-SPARK", "SE-OPS-CC-DIAGNOSE")
        for repetition in (1, 2, 3)
    }
    _require(
        set(runs) == expected_run_ids,
        "Batch 02 run set drifted",
    )
    for run_id, run in runs.items():
        for key in (
            "reportFileSha256",
            "internalReportSha256",
            "agentResponseSha256",
            "policyCacheSha256",
            "visibleTestSha256",
            "incidentEvidenceSha256",
        ):
            _require(
                isinstance(run.get(key), str) and len(run[key]) == 64,
                f"Batch 02 run digest missing: {run_id}:{key}",
            )
        _require(
            run.get("visibleTestsPassed") is True
            and run.get("hiddenTestsPassed") is True
            and run.get("changedFileScopeValid") is True
            and run.get("transientOutOfScopeWritePaths") == []
            and run.get("globalConfigStable") is True,
            f"Batch 02 functional or mutation evidence drifted: {run_id}",
        )
        _require(
            run.get("productionRecoveryClaimed") is False
            or run_id == "SE-OPS-NATIVE-SPARK:r1",
            f"Batch 02 production-recovery boundary drifted: {run_id}",
        )

    native_r1 = runs["SE-OPS-NATIVE-SPARK:r1"]
    _require(
        native_r1.get("strictProcessOutcome")
        == "fail-out-of-scope-memory-read"
        and native_r1.get("rawRunnerFailureCodes")
        == ["git-host-or-agent-mutation-observed"]
        and native_r1.get("outOfScopeReadEvidence", {}).get("readObserved")
        is True,
        "Batch 02 native boundary failure drifted",
    )
    post_hoc = native_r1.get("postHocClassifierBoundary", {})
    _require(
        post_hoc.get("rawFailureCodeIsOverbroad") is True
        and post_hoc.get("gitMutationProved") is False
        and post_hoc.get("narrowFailureCode") == "out-of-scope-read-observed"
        and post_hoc.get("rawReportMutated") is False,
        "Batch 02 post-hoc classifier boundary drifted",
    )

    expected_process_outcomes = {
        "SE-OPS-NATIVE-SPARK:r1": (
            "fail-out-of-scope-memory-read",
            True,
        ),
        "SE-OPS-CC-DIAGNOSE:r1": ("pass", True),
        "SE-OPS-NATIVE-SPARK:r2": (
            "fail-red-before-green-not-observed",
            False,
        ),
        "SE-OPS-CC-DIAGNOSE:r2": ("pass", True),
        "SE-OPS-NATIVE-SPARK:r3": (
            "fail-red-before-green-not-observed",
            False,
        ),
        "SE-OPS-CC-DIAGNOSE:r3": (
            "fail-red-before-green-not-observed",
            False,
        ),
    }
    for run_id, (outcome, red_before_green) in expected_process_outcomes.items():
        run = runs[run_id]
        _require(
            run.get("strictProcessOutcome") == outcome
            and run.get("redBeforeGreenObserved") is red_before_green,
            f"Batch 02 strict process outcome drifted: {run_id}",
        )
        if run.get("armId") == "SE-OPS-CC-DIAGNOSE":
            _require(
                run.get("structuredSkillInputMode") == "structured"
                and run.get("hypothesisCountRecorded") == 3,
                f"Batch 02 diagnose treatment evidence drifted: {run_id}",
            )

    pair_results = document.get("pairResults", [])
    _require(
        [pair.get("pairId") for pair in pair_results] == ["r1", "r2", "r3"]
        and all(
            pair.get("functionalOracle")
            == {"native": "pass", "diagnose": "pass"}
            for pair in pair_results
        ),
        "Batch 02 paired result set drifted",
    )
    aggregate = document.get("aggregateResult", {})
    _require(
        aggregate.get("pairCount") == 3
        and aggregate.get("functionalPassCount")
        == {"native": 3, "diagnose": 3}
        and aggregate.get("strictProcessPassCount")
        == {"native": 0, "diagnose": 2}
        and aggregate.get(
            "observedAssociationFavorsDiagnoseOnStrictProcessBoundary"
        )
        is True,
        "Batch 02 aggregate counts drifted",
    )
    for key in (
        "associationSupportsPreferenceDecision",
        "associationSupportsSuperiorityClaim",
        "candidateEffectOrCausationProved",
        "currentMattValueProved",
        "productionIncidentCompetenceProved",
    ):
        _require(
            aggregate.get(key) is False,
            f"Batch 02 result overclaimed: {key}",
        )

    correction = document.get("runnerCorrectionAfterPair", {})
    _require(
        correction.get("newRunnerSha256")
        == "c65de7a607c38fdac18175fdfb1778e2986ac61de7d43b1ce04d6ad5ca5e271d"
        and correction.get("separatesProjectionMutationFromExternalRead") is True
        and correction.get("addsOutOfScopeReadFailureCode") is True
        and correction.get("retroactivelyChangesRawReports") is False,
        "Batch 02 runner correction drifted",
    )
    treatment = document.get("supportingTreatmentFidelityEvidence", {})
    _require(
        treatment.get("path")
        == "registry/codex-app-server-skill-treatment-fidelity-evidence-2026-07-24.json"
        and treatment.get(
            "syntheticProjectCanaryBodyOnlyDeliveryProvedOnBoundHost"
        )
        is True
        and treatment.get("independentLoaderEventProved") is False
        and treatment.get("installedDiagnoseBodyDeliveryProved") is False
        and treatment.get("installedDiagnoseCausationProved") is False,
        "Batch 02 treatment-fidelity support drifted or overclaimed",
    )

    decision = document.get("decision", {})
    _require(
        decision.get("secondScenarioLiveExecutionStarted") is True
        and decision.get("firstPairRecorded") is True
        and decision.get("minimumThreePairsMet") is True
        and decision.get("threePairsRecorded") is True
        and decision.get("preferenceDecisionAllowed") is False
        and decision.get("selfAuthoredChainChangeJustified") is False
        and decision.get("candidateInstallUpdateOrRemovalJustified") is False,
        "Batch 02 decision overclaimed or drifted",
    )
    _require(
        all(value is False for value in document.get("claimBoundary", {}).values()),
        "Batch 02 claim boundary was promoted",
    )

    doc_path = root / str(document.get("documentation"))
    _require(doc_path.is_file(), "Batch 02 documentation is missing")
    text = " ".join(doc_path.read_text(encoding="utf-8").split())
    for phrase in (
        "out-of-scope read",
        "raw report is preserved unchanged",
        "not a preference result",
        "current Matt",
        "zero times",
        "passed twice",
        "synthetic canary assay proves",
        "not an independent loader event",
    ):
        _require(phrase in text, f"Batch 02 documentation boundary missing: {phrase}")

    if protocol is not None:
        _require(
            EVIDENCE_PATH
            in protocol.get("additionalLiveComparisonEvidence", []),
            "Batch 02 protocol evidence binding drifted",
        )
        protocol_decision = protocol.get("decision", {})
        _require(
            protocol_decision.get("secondSoftwareScenarioFirstPairRecorded")
            is True
            and protocol_decision.get(
                "secondSoftwareScenarioThreePairThresholdMet"
            )
            is True
            and protocol_decision.get(
                "secondSoftwareScenarioSkillCausationProved"
            )
            is False,
            "Batch 02 protocol decision projection drifted",
        )


def main() -> int:
    document = json.loads((ROOT / EVIDENCE_PATH).read_text(encoding="utf-8"))
    protocol = json.loads((ROOT / PROTOCOL_PATH).read_text(encoding="utf-8"))
    validate_live_comparison_batch_02(document, root=ROOT, protocol=protocol)
    print("Weak-Agent live comparison batch 02 validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
