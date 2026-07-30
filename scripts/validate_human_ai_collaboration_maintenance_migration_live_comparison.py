#!/usr/bin/env python3
"""Validate the bounded maintenance/migration weak-Agent comparison."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
EVIDENCE_PATH = Path(
    "registry/human-ai-collaboration-maintenance-migration-live-comparison-batch-01-2026-07-24.json"
)


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def validate_live_comparison(document: dict, *, root: Path = ROOT) -> None:
    _require(
        document.get("schema") == 1
        and document.get("id")
        == "human-ai-collaboration-maintenance-migration-live-comparison-batch-01-2026-07-24"
        and document.get("status")
        == "three-valid-pairs-native-association-no-causation-or-portfolio-preference"
        and document.get("scenarioId") == "SE-MAINT-MIGRATE-01",
        "Maintenance/migration live comparison identity drifted",
    )

    authority = document.get("authorityBoundary", {})
    _require(authority.get("disposableRootsOnly") is True, "Disposable-root boundary weakened")
    _require(
        all(value is False for key, value in authority.items() if key != "disposableRootsOnly"),
        "Maintenance/migration authority boundary was expanded",
    )

    control = document.get("controlPlaneAtRun", {})
    _require(
        control.get("host") == "Codex Desktop app-server 0.145.0"
        and control.get("model") == "gpt-5.3-codex-spark"
        and control.get("reasoningEffort") == "low"
        and control.get("approvalPolicy") == "never"
        and control.get("networkAccess") is False
        and control.get("oracleVersion")
        == "versioned-record-migration-hidden-oracle-v3"
        and control.get("oracleContractSha256")
        == "1ed7d61f6e2e9ca32b11a8087b0b70276e78756bc2ea0900bd6140e645462b6e"
        and control.get("oracleSourceSha256")
        == "2f819444eb3125fe2af10f666f13ab019381a4a37ba6ea36acae08dccb13b7d9"
        and control.get("candidateSkillSha256")
        == "52ef07de05726292c0f5e9fe666cc30e6efbe580ed775621e785a49ec80bd4ea",
        "Maintenance/migration control plane drifted",
    )

    invalid = document.get("invalidatedMeasurementRuns", [])
    _require(
        len(invalid) == 5
        and {item.get("id") for item in invalid}
        == {
            "oracle-v1-native",
            "oracle-v1-candidate",
            "oracle-v1-candidate-classifier-retry",
            "oracle-v2-native",
            "oracle-v2-candidate",
        }
        and all(item.get("countsInAggregate") is False for item in invalid)
        and all(item.get("reportFileSha256") for item in invalid),
        "Invalid measurement-run retention drifted",
    )

    runs = document.get("validRuns", [])
    _require(
        len(runs) == 6
        and {item.get("id") for item in runs}
        == {
            "native:r1",
            "candidate:r1",
            "native:r2",
            "candidate:r2",
            "native:r3",
            "candidate:r3",
        },
        "Valid run set drifted",
    )
    for field in ("threadId", "turnId", "reportFileSha256", "internalReportSha256"):
        values = [item.get(field) for item in runs]
        _require(all(values) and len(values) == len(set(values)), f"Run {field} is missing or reused")
    _require(
        all(
            item.get("visibleTestsPassed") is True
            and item.get("changedFileScopeValid") is True
            and item.get("immutableInputsStable") is True
            and item.get("outOfScopeReadObserved") is False
            and item.get("transientOutOfScopeWriteObserved") is False
            and item.get("globalConfigStable") is True
            for item in runs
        ),
        "Run scope or process boundary drifted",
    )
    _require(
        {item["id"]: item.get("hiddenTestsPassed") for item in runs}
        == {
            "native:r1": True,
            "candidate:r1": False,
            "native:r2": True,
            "candidate:r2": True,
            "native:r3": True,
            "candidate:r3": False,
        },
        "Hidden-contract outcomes drifted",
    )

    _require(
        [item.get("pairId") for item in document.get("pairResults", [])]
        == ["r1", "r2", "r3"],
        "Pair ordering or repetition count drifted",
    )
    aggregate = document.get("aggregateResult", {})
    _require(
        aggregate.get("validPairCount") == 3
        and aggregate.get("invalidMeasurementRunCount") == 5
        and aggregate.get("visiblePassCount") == {"native": 3, "candidate": 3}
        and aggregate.get("fullHiddenContractPassCount")
        == {"native": 3, "candidate": 1}
        and aggregate.get("candidateFinalResponseContradictedParentObservedArtifactCount")
        == 2
        and aggregate.get("observedAssociationFavorsNativeOnBoundFixture") is True,
        "Maintenance/migration aggregate drifted",
    )
    for key in (
        "associationSupportsGeneralNativePreference",
        "associationSupportsCandidatePreference",
        "associationSupportsSkillSuperiorityClaim",
        "candidateEffectOrCausationProved",
        "productionMigrationCompetenceProved",
        "removalReadinessProved",
        "crossHostValueProved",
        "selfAuthoredResidualGapProved",
    ):
        _require(aggregate.get(key) is False, f"Aggregate overclaim introduced: {key}")

    treatment = document.get("treatmentFidelityBoundary", {})
    _require(
        treatment.get("nativeAllUserSkillsDisabledExposureProved") is True
        and treatment.get("candidateOnlyExactSelectedSkillExposureProved") is True
        and treatment.get("candidateStructuredSkillInputAccepted") is True
        and treatment.get("independentLoaderEventProved") is False
        and treatment.get("candidateSpecificInstructionsReachedModelProved") is False
        and treatment.get("candidateSpecificCausationProved") is False,
        "Treatment-fidelity boundary drifted",
    )

    decision = document.get("decision", {})
    _require(
        decision.get("minimumThreeValidPairsMet") is True
        and decision.get("fiveMeasurementInvalidRunsRetained") is True
        and decision.get("candidateDemonstratedAddedValue") is False
        and decision.get("boundedNativeAssociationObserved") is True
        and decision.get("generalPreferenceDecisionAllowed") is False
        and decision.get("selfAuthoredChainChangeJustified") is False
        and decision.get("candidateInstallUpdateOrRemovalJustified") is False
        and decision.get("identicalRepetitionShouldContinue") is False,
        "Maintenance/migration decision drifted",
    )
    _require(
        all(value is False for value in document.get("claimBoundary", {}).values()),
        "Maintenance/migration claim boundary was promoted",
    )

    doc_path = root / str(document.get("documentation"))
    _require(doc_path.is_file(), "Maintenance/migration live comparison documentation is missing")
    text = " ".join(doc_path.read_text(encoding="utf-8").split())
    for phrase in (
        "native 3/3 versus candidate 1/3",
        "independent hidden oracles",
        "not evidence that every Skill harms performance",
        "Stop identical maintenance repetitions",
    ):
        _require(phrase in text, f"Live comparison documentation missing boundary: {phrase}")


def main() -> int:
    document = json.loads((ROOT / EVIDENCE_PATH).read_text(encoding="utf-8"))
    validate_live_comparison(document, root=ROOT)
    print("Maintenance/migration live comparison validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
