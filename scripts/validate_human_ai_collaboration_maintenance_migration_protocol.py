#!/usr/bin/env python3
"""Validate the pre-registered maintenance/migration comparison."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
PROTOCOL_PATH = (
    "registry/"
    "human-ai-collaboration-maintenance-migration-protocol-batch-01-2026-07-24.json"
)


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def validate_protocol(document: dict[str, Any], *, root: Path = ROOT) -> None:
    _require(document.get("schema") == 1, "Migration protocol schema must be 1")
    _require(
        document.get("status")
        == "three-valid-pairs-complete-no-preference-or-causation"
        and document.get("scenarioId") == "SE-MAINT-MIGRATE-01",
        "Migration protocol status or scenario drifted",
    )
    selection = document.get("selectionDecision", {})
    _require(
        selection.get("selectedCapabilityId")
        == "cc.deprecation-and-migration"
        and selection.get("securityScenarioDisposition")
        == "deferred-host-control-and-license-boundary",
        "Migration protocol selection drifted",
    )

    authority = document.get("authorityBoundary", {})
    _require(
        authority.get("repositoryProtocolWritesAuthorized") is True
        and authority.get("disposableFixtureWritesAuthorized") is True,
        "Migration protocol local authority drifted",
    )
    for key, value in authority.items():
        if key not in {
            "repositoryProtocolWritesAuthorized",
            "disposableFixtureWritesAuthorized",
        }:
            _require(value is False, f"Migration protocol authority promoted: {key}")

    host = document.get("hostBinding", {})
    _require(
        host.get("primaryWeakModelRequested") == "gpt-5.3-codex-spark"
        and host.get("primaryReasoningEffortRequested") == "low"
        and host.get("providerFallbackAllowed") is False
        and host.get("strongDiagnosticMayReplaceWeakAcceptance") is False,
        "Migration protocol model boundary drifted",
    )

    pins = {
        item.get("id"): item
        for item in document.get("candidatePins", [])
        if isinstance(item, dict)
    }
    _require(
        set(pins)
        == {
            "cc.deprecation-and-migration",
            "cc.request-refactor-plan",
            "cc.improve-codebase-architecture",
            "superpowers.verification-before-completion",
            "official.codex-security.finding-discovery",
        },
        "Migration protocol candidate set drifted",
    )
    primary = pins["cc.deprecation-and-migration"]
    _require(
        primary.get("bytes") == 12510
        and primary.get("sha256")
        == "52ef07de05726292c0f5e9fe666cc30e6efbe580ed775621e785a49ec80bd4ea"
        and primary.get("declaredLicense") == "MIT"
        and primary.get("declaredAdaptedFor") == "cross-agent",
        "Migration primary candidate pin drifted",
    )
    upstream = primary.get("upstreamCrossCheck", {})
    _require(
        upstream.get("revision")
        == "17214a29c429a19f7a9607f2c06f9d650ea87eb0"
        and upstream.get("bytes") == 9000
        and upstream.get("sha256")
        == "bf2d9b4e3bc635b32e8de70b0ab41e4395d7b585e6474347c53ce89d45fbdb75"
        and upstream.get("gitBlobSha1")
        == "258e2a0396c9c2cb639cff84a9db64753740be96"
        and upstream.get("localGitBlobSha1")
        == "5ee5d33c24abd882e4704bacf5d399ffdb9b784e"
        and upstream.get("localEqualsUpstreamPinnedBlob") is False
        and upstream.get("license") == "MIT"
        and upstream.get("licenseSha256")
        == "6f202f8bd568cd730dbb2b0d1f8e243bc74c2fa1f64dbce9b2c7ea08bd5c9fd7"
        and upstream.get("adaptationDiffFullyReviewed") is True
        and upstream.get("adaptationReviewEvidence")
        == "registry/deprecation-and-migration-local-adaptation-review-2026-07-24.json",
        "Migration candidate upstream/adaptation boundary drifted",
    )
    _require(
        (root / upstream["adaptationReviewEvidence"]).is_file(),
        "Migration candidate adaptation review evidence is missing",
    )
    _require(
        primary.get("candidateSpecificSelectedExposureProved") is False
        and primary.get("loaderInvocationProved") is False
        and primary.get("instructionsReachedModelProved") is False
        and primary.get("behavioralValueProved") is False,
        "Migration candidate evidence was promoted",
    )
    security = pins["official.codex-security.finding-discovery"]
    _require(
        security.get("declaredLicense") == "Proprietary"
        and security.get("pluginVersion") == "0.1.12"
        and security.get("suitability")
        == "defer-security-scenario-no-clean-disabled-control-and-no-vendoring",
        "Codex Security deferral boundary drifted",
    )

    fixture = document.get("fixtureDesign", {})
    _require(
        fixture.get("fixtureId")
        == "fixture.python-versioned-record-migration-v1"
        and fixture.get("baseline", {}).get("visibleTestsPass") is True
        and fixture.get("baseline", {}).get("privateOraclePasses") is False
        and fixture.get("baseline", {}).get("privateOracleWrittenIntoTrial")
        is False,
        "Migration fixture baseline drifted",
    )
    consumers = {
        item.get("id"): item
        for item in fixture.get("affectedConsumerModel", [])
        if isinstance(item, dict)
    }
    _require(
        set(consumers)
        == {
            "consumer.documented-v1",
            "consumer.quirk-v1-none-normalization",
            "consumer.v2-native",
            "consumer.opaque-batch",
        }
        and consumers["consumer.opaque-batch"].get("state")
        == "unknown-incomplete-telemetry",
        "Migration affected-consumer model drifted",
    )
    _require(
        fixture.get("allowedMutableFiles")
        == [
            "record_adapter.py",
            "test_record_adapter.py",
            "MIGRATION_EVIDENCE.json",
        ]
        and len(fixture.get("sharedAcceptance", [])) == 10
        and len(fixture.get("falsifiers", [])) == 5,
        "Migration fixture acceptance surface drifted",
    )
    _require(
        fixture.get("hiddenOracleVersion")
        == "versioned-record-migration-hidden-oracle-v3"
        and fixture.get("hiddenOracleSourceSha256")
        == "2f819444eb3125fe2af10f666f13ab019381a4a37ba6ea36acae08dccb13b7d9"
        and fixture.get("hiddenOracleContractSha256")
        == "1ed7d61f6e2e9ca32b11a8087b0b70276e78756bc2ea0900bd6140e645462b6e"
        and "did not declare an exact migrationStatus enum or preferred vocabulary"
        in fixture.get("oracleMeasurementCorrection", ""),
        "Migration private-oracle correction drifted",
    )

    arms = {
        item.get("id"): item
        for item in document.get("arms", [])
        if isinstance(item, dict)
    }
    _require(
        set(arms)
        == {
            "SE-MAINT-HUMAN-CONTROL",
            "SE-MAINT-NATIVE-SPARK",
            "SE-MAINT-CC-DEPRECATION-MIGRATION",
            "SE-MAINT-SELF-CHAIN-PHASED",
            "SE-MAINT-STRONG-DIAGNOSTIC",
        }
        and arms["SE-MAINT-NATIVE-SPARK"].get("primaryAcceptanceArm") is True
        and arms["SE-MAINT-CC-DEPRECATION-MIGRATION"].get(
            "primaryAcceptanceArm"
        )
        is True,
        "Migration protocol arm set drifted",
    )

    gate = document.get("executionGate", {})
    for key in (
        "fixtureBuilderImplemented",
        "privateOracleImplemented",
        "offlineClassifierFixturesPass",
    ):
        _require(gate.get(key) is True, f"Migration implementation gate drifted: {key}")
    for key in (
        "freshRepositoryTruthRequired",
        "freshCandidateHashRequired",
        "candidateAdaptationDiffReviewRequired",
        "nativeDisabledExposureRequired",
        "candidateSpecificSelectedExposureRequired",
        "promptMustExcludePrivateOracle",
    ):
        _require(gate.get(key) is True, f"Migration execution prerequisite weakened: {key}")
    _require(
        gate.get("candidateAdaptationDiffReviewCompleted") is True,
        "Migration adaptation review completion drifted",
    )
    for key in (
        "freshCandidateHashVerified",
        "nativeDisabledExposureProved",
        "candidateSpecificSelectedExposureProved",
        "publicPromptPrivateOracleBoundaryPassed",
    ):
        _require(gate.get(key) is True, f"Migration preflight gate drifted: {key}")
    _require(
        gate.get("preflightEvidence")
        == "registry/maintenance-migration-exposure-preflight-evidence-2026-07-24.json"
        and (root / gate["preflightEvidence"]).is_file(),
        "Migration preflight evidence binding drifted",
    )
    _require(
        gate.get("minimumValidPairsPerPrimaryArm") == 3
        and gate.get("invalidEnvironmentOrMeasurementRunsCount") == 5
        and gate.get("validPairsRecorded") == 3
        and gate.get("liveComparisonEvidence")
        == "registry/human-ai-collaboration-maintenance-migration-live-comparison-batch-01-2026-07-24.json"
        and (root / gate["liveComparisonEvidence"]).is_file(),
        "Migration repetition boundary drifted",
    )

    decision = document.get("decision", {})
    _require(
        decision.get("scenarioSelected") is True
        and decision.get("candidateSuitabilityReviewed") is True
        and decision.get("liveExecutionStarted") is True
        and decision.get("threeValidPairsComplete") is True
        and decision.get("preferenceDecisionAllowed") is False
        and decision.get("selfAuthoredChangeJustified") is False
        and decision.get("candidateInstallUpdateOrRemovalJustified") is False,
        "Migration decision overclaimed",
    )
    _require(
        all(value is False for value in document.get("claimBoundary", {}).values()),
        "Migration claim boundary was promoted",
    )

    doc_path = root / str(document.get("documentation"))
    _require(doc_path.is_file(), "Migration protocol documentation is missing")
    text = " ".join(doc_path.read_text(encoding="utf-8").split())
    for phrase in (
        "contaminated control",
        "adapted cross-Agent derivative",
        "incomplete telemetry",
        "Three valid pairs are required",
        "proves no Skill value",
        "native 3/3",
        "Identical repetitions stop",
    ):
        _require(phrase in text, f"Migration protocol doc missing boundary: {phrase}")


def main() -> int:
    document = json.loads((ROOT / PROTOCOL_PATH).read_text(encoding="utf-8"))
    validate_protocol(document, root=ROOT)
    print("Maintenance/migration protocol validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
