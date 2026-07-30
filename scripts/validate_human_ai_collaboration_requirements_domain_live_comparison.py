#!/usr/bin/env python3
"""Validate the bounded requirements/domain weak-Agent comparison."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
EVIDENCE_PATH = Path(
    "registry/human-ai-collaboration-requirements-domain-live-comparison-batch-01-2026-07-24.json"
)
PROTOCOL_PATH = Path(
    "registry/human-ai-collaboration-requirements-domain-challenge-protocol-batch-01-2026-07-24.json"
)


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def validate_live_comparison(
    document: dict,
    *,
    root: Path = ROOT,
    protocol: dict | None = None,
) -> None:
    _require(
        document.get("schema") == 1
        and document.get("id")
        == "human-ai-collaboration-requirements-domain-live-comparison-batch-01-2026-07-24"
        and document.get("status")
        == "three-valid-pairs-both-arms-fail-hidden-contract-no-preference-or-causation"
        and document.get("scenarioId") == "SE-DISCOVERY-REQ-01"
        and document.get("fixtureId")
        == "fixture.source-bound-domain-plan-challenge-v1"
        and document.get("parentProtocol") == PROTOCOL_PATH.as_posix(),
        "Requirements/domain live comparison identity drifted",
    )

    authority = document.get("authorityBoundary", {})
    _require(
        authority.get("disposableRootsOnly") is True,
        "Requirements/domain disposable-root boundary weakened",
    )
    _require(
        all(value is False for key, value in authority.items() if key != "disposableRootsOnly"),
        "Requirements/domain authority boundary was expanded",
    )

    control = document.get("controlPlaneAtRun", {})
    _require(
        control.get("host") == "Codex Desktop app-server 0.145.0"
        and control.get("model") == "gpt-5.3-codex-spark"
        and control.get("reasoningEffort") == "low"
        and control.get("providerFallbackAllowed") is False
        and control.get("approvalPolicy") == "never"
        and control.get("networkAccess") is False
        and control.get("oracleVersion")
        == "requirements-domain-review-hidden-oracle-v1"
        and control.get("oracleSourceSha256")
        == "3b06392a4ac47a76d0a1eea5e777533c67577a13abca890204f4a8aba61dbb81"
        and control.get("runnerSha256")
        == "c2641bc868e74847720ca51a2f632804b62e39c7ef00694ecee71d90aea3c94d"
        and control.get("builderSha256")
        == "ee71f0f393744ad3852af1fd3c7e5d32aef084a515f1d70e0a2b12e25ec74822"
        and control.get("candidateSkillSha256")
        == "e1078020c41b954638ba94acda95a3340739908bd68b1db9bc2af129d3936035",
        "Requirements/domain control plane drifted",
    )
    for key, value in control.items():
        if key.endswith("Sha256"):
            _require(
                isinstance(value, str) and len(value) == 64,
                f"Requirements/domain control digest is invalid: {key}",
            )

    protocol = protocol or json.loads((root / PROTOCOL_PATH).read_text(encoding="utf-8"))
    invalid = document.get("invalidMeasurementRunAccounting", {})
    protocol_invalid = protocol.get("invalidMeasurementRuns", [])
    _require(
        invalid
        == {
            "source": "parentProtocol.invalidMeasurementRuns",
            "count": 9,
            "allExcludedFromAggregate": True,
            "rawEvidenceMutated": False,
        }
        and len(protocol_invalid) == 9
        and all(item.get("countsInAggregate") is False for item in protocol_invalid),
        "Requirements/domain invalid measurement accounting drifted",
    )

    runs = document.get("validRuns", [])
    expected_ids = {
        "native:r1",
        "candidate:r1",
        "native:r2",
        "candidate:r2",
        "native:r3",
        "candidate:r3",
    }
    _require(
        len(runs) == 6 and {item.get("id") for item in runs} == expected_ids,
        "Requirements/domain valid run set drifted",
    )
    for field in (
        "threadId",
        "turnId",
        "reportFileSha256",
        "internalReportSha256",
        "agentResponseSha256",
        "requirementsReviewSha256",
    ):
        values = [item.get(field) for item in runs]
        _require(
            all(isinstance(value, str) and value for value in values)
            and len(values) == len(set(values)),
            f"Requirements/domain run {field} is missing or reused",
        )
    _require(
        all(
            item.get("changedFileScopeValid") is True
            and item.get("immutableInputsStable") is True
            and item.get("outOfScopeReadObserved") is False
            and item.get("transientOutOfScopeWriteObserved") is False
            and item.get("globalConfigStable") is True
            and item.get("rawRunnerStatus")
            == "fixture-fail-or-host-evidence-incomplete"
            for item in runs
        ),
        "Requirements/domain run scope or evidence boundary drifted",
    )
    _require(
        {
            item["id"]: (
                item.get("visibleTestsPassed"),
                item.get("hiddenTestsPassed"),
                len(item.get("hiddenFailureCodes", [])),
            )
            for item in runs
        }
        == {
            "native:r1": (False, False, 15),
            "candidate:r1": (False, False, 4),
            "native:r2": (False, False, 4),
            "candidate:r2": (False, False, 14),
            "native:r3": (False, False, 3),
            "candidate:r3": (True, False, 6),
        },
        "Requirements/domain run outcomes drifted",
    )

    native_runs = [item for item in runs if item["id"].startswith("native:")]
    candidate_runs = [item for item in runs if item["id"].startswith("candidate:")]
    _require(
        all(item.get("allConfigurableUserSkillsDisabled") is True for item in native_runs)
        and all(item.get("onlySelectedUserSkillEnabled") is True for item in candidate_runs)
        and all(item.get("structuredSkillInputAccepted") is True for item in candidate_runs)
        and all(item.get("loaderInvocationProved") is False for item in candidate_runs),
        "Requirements/domain treatment exposure drifted",
    )

    _require(
        [item.get("pairId") for item in document.get("pairResults", [])]
        == ["r1", "r2", "r3"],
        "Requirements/domain pair ordering drifted",
    )
    aggregate = document.get("aggregateResult", {})
    _require(
        aggregate.get("validPairCount") == 3
        and aggregate.get("invalidMeasurementRunCount") == 9
        and aggregate.get("visiblePassCount") == {"native": 0, "candidate": 1}
        and aggregate.get("fullHiddenContractPassCount")
        == {"native": 0, "candidate": 0}
        and aggregate.get("hiddenFailureCodeOccurrenceCount")
        == {"native": 22, "candidate": 24}
        and aggregate.get("hardStatusPromotionRunCount")
        == {"native": 1, "candidate": 1}
        and aggregate.get("canonicalTermFailureRunCount")
        == {"native": 3, "candidate": 3}
        and aggregate.get("customerUserDistinctionFailureRunCount")
        == {"native": 3, "candidate": 3}
        and aggregate.get("sourceBindingFailureRunCount")
        == {"native": 1, "candidate": 2},
        "Requirements/domain aggregate drifted",
    )
    for key in (
        "observedAssociationFavorsEitherArm",
        "candidateDemonstratedBoundedAddedValue",
        "associationSupportsGeneralNativePreference",
        "associationSupportsCandidatePreference",
        "associationSupportsSkillSuperiorityClaim",
        "candidateEffectOrCausationProved",
        "productDiscoveryCompetenceProved",
        "requirementsCompletenessProved",
        "crossHostValueProved",
        "selfAuthoredResidualGapProved",
    ):
        _require(aggregate.get(key) is False, f"Requirements/domain overclaim introduced: {key}")

    treatment = document.get("treatmentFidelityBoundary", {})
    _require(
        treatment.get("nativeAllUserSkillsDisabledExposureProved") is True
        and treatment.get("candidateOnlyExactSelectedSkillExposureProved") is True
        and treatment.get("candidateStructuredSkillInputAccepted") is True
        and treatment.get("independentLoaderEventProved") is False
        and treatment.get("candidateSpecificInstructionsReachedModelProved") is False
        and treatment.get("candidateSpecificCausationProved") is False,
        "Requirements/domain treatment-fidelity boundary drifted",
    )

    decision = document.get("decision", {})
    _require(
        decision.get("minimumThreeValidPairsMet") is True
        and decision.get("nineMeasurementInvalidRunsRetainedByParent") is True
        and decision.get("candidateDemonstratedAddedValue") is False
        and decision.get("eitherArmMetHardAcceptance") is False
        and decision.get("generalPreferenceDecisionAllowed") is False
        and decision.get("selfAuthoredChainChangeJustified") is False
        and decision.get("candidateInstallUpdateOrRemovalJustified") is False
        and decision.get("identicalRepetitionShouldContinue") is False,
        "Requirements/domain decision drifted",
    )
    _require(
        all(value is False for value in document.get("claimBoundary", {}).values()),
        "Requirements/domain claim boundary was promoted",
    )

    doc_path = root / str(document.get("documentation"))
    _require(doc_path.is_file(), "Requirements/domain comparison documentation is missing")
    text = " ".join(doc_path.read_text(encoding="utf-8").split())
    for phrase in (
        "native 0/3 versus candidate 1/3",
        "native 0/3 versus candidate 0/3",
        "does not demonstrate added value",
        "Stop identical requirements/domain repetitions",
        "not evidence that every Skill harms performance",
    ):
        _require(
            phrase in text,
            f"Requirements/domain documentation missing boundary: {phrase}",
        )


def main() -> int:
    document = json.loads((ROOT / EVIDENCE_PATH).read_text(encoding="utf-8"))
    validate_live_comparison(document, root=ROOT)
    print("Requirements/domain live comparison validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
