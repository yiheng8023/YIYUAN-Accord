#!/usr/bin/env python3
"""Validate the source-pinned weak-Agent debugging comparison."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
EVIDENCE_PATH = (
    "registry/"
    "human-ai-collaboration-weak-agent-live-comparison-batch-03-2026-07-24.json"
)
PROTOCOL_PATH = (
    "registry/"
    "human-ai-collaboration-comparative-protocol-batch-01-2026-07-24.json"
)


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def validate_live_comparison_batch_03(
    document: dict[str, Any],
    *,
    root: Path = ROOT,
    protocol: dict[str, Any] | None = None,
) -> None:
    _require(document.get("schema") == 1, "Batch 03 schema must be 1")
    _require(
        document.get("status")
        == "three-source-pinned-pairs-complete-no-preference-or-causation",
        "Batch 03 status overclaimed or drifted",
    )
    _require(
        document.get("scenarioId") == "SE-OPS-INCIDENT-01"
        and document.get("fixtureId")
        == "fixture.python-tenant-policy-cache-incident-v1",
        "Batch 03 scenario binding drifted",
    )
    _require(
        document.get("parentProtocol") == PROTOCOL_PATH
        and document.get("projectionProtocol")
        == "registry/source-pinned-debugging-skill-projection-protocol-2026-07-24.json",
        "Batch 03 protocol binding drifted",
    )

    authority = document.get("authorityBoundary", {})
    _require(
        authority.get("disposableRootsOnly") is True,
        "Batch 03 disposable-root boundary drifted",
    )
    for key in (
        "networkAllowed",
        "mcpOrAppAllowed",
        "dependencyInstallAllowed",
        "globalConfigMutationAllowed",
        "installedSkillMutationAllowed",
        "sourceMutationAllowed",
        "gitMutationAllowed",
        "externalWriteAllowed",
        "productionRecoveryClaimAllowed",
        "calibrationWriteAllowed",
    ):
        _require(authority.get(key) is False, f"Batch 03 authority promoted: {key}")

    control = document.get("controlPlaneAtRun", {})
    _require(
        control.get("model") == "gpt-5.3-codex-spark"
        and control.get("reasoningEffort") == "low"
        and control.get("providerFallbackAllowed") is False,
        "Batch 03 weak-model control drifted",
    )
    for key in (
        "runnerSha256",
        "builderSha256",
        "protocolSha256BeforeBatch03Projection",
        "projectionProtocolSha256",
        "publicTaskPromptSha256",
        "baselinePolicyCacheSha256",
        "baselineVisibleTestSha256",
        "baselineEvidenceStubSha256",
    ):
        _require(
            isinstance(control.get(key), str) and len(control[key]) == 64,
            f"Batch 03 control digest missing: {key}",
        )

    candidates = {
        item.get("id"): item
        for item in document.get("candidates", [])
        if isinstance(item, dict)
    }
    _require(
        set(candidates)
        == {
            "matt.current-diagnosing-bugs",
            "superpowers.runtime-6.1.1-systematic-debugging",
        },
        "Batch 03 candidate set drifted",
    )
    _require(
        candidates["matt.current-diagnosing-bugs"].get("sourceRevision")
        == "ed37663cc5fbef691ddfecd080dff42f7e7e350d"
        and candidates["matt.current-diagnosing-bugs"].get("skillSha256")
        == "7a0779480f323a66d109404646bcc1a14bf0232b45b3e3ea93b652a035718acb",
        "Batch 03 current Matt pin drifted",
    )
    _require(
        candidates["superpowers.runtime-6.1.1-systematic-debugging"].get(
            "packageVersion"
        )
        == "6.1.1"
        and candidates["superpowers.runtime-6.1.1-systematic-debugging"].get(
            "skillSha256"
        )
        == "3b20719eca4f0461cb51a195221320d775dcf03b6859271066a03a5132a6ce7a",
        "Batch 03 Superpowers pin drifted",
    )
    for candidate in candidates.values():
        _require(
            candidate.get("selectedExposureProved") is True
            and candidate.get("structuredSkillInputSent") is True
            and candidate.get("hostAcceptedStructuredSkillInput") is True
            and candidate.get("loaderInvocationProved") is False
            and candidate.get("instructionsReachedModelProved") is False,
            "Batch 03 candidate treatment boundary drifted",
        )

    invalid = {
        item.get("id"): item
        for item in document.get("invalidatedGuardRuns", [])
        if isinstance(item, dict)
    }
    _require(
        set(invalid) == {"matt:guard-r1", "superpowers:guard-r1"},
        "Batch 03 invalid guard-run set drifted",
    )
    for run in invalid.values():
        _require(
            run.get("rawFailureCodes")
            == ["git-host-or-agent-mutation-observed"]
            and run.get("rawReportMutated") is False
            and run.get("countsInAggregate") is False
            and str(run.get("measurementValidity", "")).startswith(
                "invalid-old-marker-classifier"
            ),
            "Batch 03 invalid guard-run boundary drifted",
        )
        for key in ("reportFileSha256", "internalReportSha256"):
            _require(
                isinstance(run.get(key), str) and len(run[key]) == 64,
                f"Batch 03 invalid run digest missing: {run.get('id')}:{key}",
            )

    runs = {
        item.get("id"): item
        for item in document.get("runs", [])
        if isinstance(item, dict)
    }
    expected = {
        f"{candidate}:r{repetition}"
        for candidate in ("matt", "superpowers")
        for repetition in (1, 2, 3)
    }
    _require(set(runs) == expected, "Batch 03 valid run set drifted")
    for run_id, run in runs.items():
        for key in (
            "reportFileSha256",
            "internalReportSha256",
            "agentResponseSha256",
            "policyCacheSha256",
            "visibleTestSha256",
            "incidentEvidenceSha256",
            "projectionManifestSha256",
        ):
            _require(
                isinstance(run.get(key), str) and len(run[key]) == 64,
                f"Batch 03 run digest missing: {run_id}:{key}",
            )
        _require(
            run.get("visibleTestsPassed") is True
            and run.get("changedFileScopeValid") is True
            and run.get("outOfScopeReadObserved") is False
            and run.get("transientOutOfScopeWritePaths") == []
            and run.get("globalConfigStable") is True
            and run.get("exactHostProjectionPatternObserved") is True
            and run.get("productionRecoveryClaimed") is False,
            f"Batch 03 shared boundary drifted: {run_id}",
        )

    expected_outcomes = {
        "matt:r1": (False, True, 2, True, "fail-candidate-process-hypothesis-count"),
        "superpowers:r1": (False, True, 1, False, "fail-shared-evidence-schema"),
        "matt:r2": (False, True, 1, True, "fail-candidate-process-hypothesis-count"),
        "superpowers:r2": (True, True, 1, True, "pass"),
        "matt:r3": (True, True, 3, True, "pass"),
        "superpowers:r3": (
            True,
            False,
            1,
            True,
            "fail-red-before-green-not-observed",
        ),
    }
    for run_id, expected_values in expected_outcomes.items():
        run = runs[run_id]
        actual = (
            run.get("hiddenTestsPassed"),
            run.get("redBeforeGreenObserved"),
            run.get("hypothesisCountRecorded"),
            run.get("exactSymptomBoolean"),
            run.get("strictOutcome"),
        )
        _require(
            actual == expected_values,
            f"Batch 03 observed outcome drifted: {run_id}",
        )

    pair_results = document.get("pairResults", [])
    _require(
        [pair.get("pairId") for pair in pair_results] == ["r1", "r2", "r3"]
        and all(
            pair.get("visibleOracle")
            == {"matt": "pass", "superpowers": "pass"}
            for pair in pair_results
        ),
        "Batch 03 pair result set drifted",
    )
    aggregate = document.get("aggregateResult", {})
    _require(
        aggregate.get("pairCount") == 3
        and aggregate.get("visiblePassCount")
        == {"matt": 3, "superpowers": 3}
        and aggregate.get("fullHiddenContractPassCount")
        == {"matt": 1, "superpowers": 2}
        and aggregate.get("strictProcessPassCount")
        == {"matt": 1, "superpowers": 1},
        "Batch 03 aggregate counts drifted",
    )
    for key in (
        "observedAssociationFavorsEitherCandidate",
        "associationSupportsPreferenceDecision",
        "associationSupportsSuperiorityClaim",
        "candidateEffectOrCausationProved",
        "productionIncidentCompetenceProved",
        "crossHostValueProved",
        "selfAuthoredResidualGapProved",
    ):
        _require(
            aggregate.get(key) is False,
            f"Batch 03 aggregate overclaimed: {key}",
        )

    treatment = document.get("treatmentFidelityBoundary", {})
    _require(
        treatment.get("sourcePinnedExactBytesProjected") is True
        and treatment.get("projectSkillSelectedExposureProved") is True
        and treatment.get("structuredSkillInputAccepted") is True
        and treatment.get(
            "syntheticBodyOnlyDeliveryMechanismPreviouslyProvedOnBoundHost"
        )
        is True
        and treatment.get("independentLoaderEventProved") is False
        and treatment.get("candidateSpecificInstructionsReachedModelProved")
        is False
        and treatment.get("candidateSpecificCausationProved") is False
        and treatment.get("superpowersCrossSkillReferencesProjected") is False
        and treatment.get("provesFullSuperpowersSuiteBehavior") is False,
        "Batch 03 treatment-fidelity boundary drifted",
    )

    decision = document.get("decision", {})
    _require(
        decision.get("sourcePinnedCurrentMattExecutionStarted") is True
        and decision.get("sourcePinnedSuperpowersExecutionStarted") is True
        and decision.get("minimumThreePairsMet") is True
        and decision.get("threePairsRecorded") is True
        and decision.get("guardInvalidRunsPreserved") is True
        and decision.get("preferenceDecisionAllowed") is False
        and decision.get("selfAuthoredChainChangeJustified") is False
        and decision.get("candidateInstallUpdateOrRemovalJustified") is False
        and decision.get("identicalRepetitionShouldContinue") is False,
        "Batch 03 decision overclaimed or drifted",
    )
    _require(
        all(value is False for value in document.get("claimBoundary", {}).values()),
        "Batch 03 claim boundary was promoted",
    )

    doc_path = root / str(document.get("documentation"))
    _require(doc_path.is_file(), "Batch 03 documentation is missing")
    text = " ".join(doc_path.read_text(encoding="utf-8").split())
    for phrase in (
        "mixed outcomes",
        "raw reports are preserved unchanged",
        "favors neither candidate",
        "no independent loader event",
        "does not represent or evaluate full-Superpowers orchestration",
        "oracle must not be tuned",
    ):
        _require(phrase in text, f"Batch 03 documentation boundary missing: {phrase}")

    if protocol is not None:
        _require(
            EVIDENCE_PATH
            in protocol.get("additionalLiveComparisonEvidence", []),
            "Batch 03 protocol evidence binding drifted",
        )
        decision = protocol.get("decision", {})
        _require(
            decision.get("sourcePinnedDebuggingThreePairThresholdMet") is True
            and decision.get("sourcePinnedDebuggingPreferenceAllowed") is False
            and decision.get("sourcePinnedDebuggingSkillCausationProved")
            is False,
            "Batch 03 protocol decision projection drifted",
        )


def main() -> int:
    document = json.loads((ROOT / EVIDENCE_PATH).read_text(encoding="utf-8"))
    protocol = json.loads((ROOT / PROTOCOL_PATH).read_text(encoding="utf-8"))
    validate_live_comparison_batch_03(document, root=ROOT, protocol=protocol)
    print("Weak-Agent live comparison batch 03 validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
