#!/usr/bin/env python3
"""Validate the pre-registered requirements/domain challenge protocol."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
PROTOCOL_PATH = Path(
    "registry/human-ai-collaboration-requirements-domain-challenge-protocol-batch-01-2026-07-24.json"
)


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def validate_protocol(document: dict, *, root: Path = ROOT) -> None:
    _require(
        document.get("schema") == 1
        and document.get("status")
        == "technical-preflight-ready-no-live-run"
        and document.get("scenarioId") == "SE-DISCOVERY-REQ-01",
        "Requirements/domain protocol identity drifted",
    )
    selection = document.get("selectionDecision", {})
    _require(
        selection.get("selectedCapabilityId") == "cc.grill-with-docs"
        and selection.get("nativeArmRequired") is True
        and selection.get("selfAuthoredArmEligibleNow") is False,
        "Requirements/domain selection boundary drifted",
    )
    candidate = document.get("candidatePin", {})
    candidate_path = root / Path(str(candidate.get("path")))
    _require(
        candidate.get("managementOwner") == "CC Switch"
        and candidate.get("path") == "skills/grill-with-docs/SKILL.md"
        and candidate.get("bytes") == 5340
        and candidate.get("sha256")
        == "e1078020c41b954638ba94acda95a3340739908bd68b1db9bc2af129d3936035"
        and candidate_path.is_file(),
        "Requirements/domain candidate pin drifted",
    )
    candidate_bytes = candidate_path.read_bytes()
    _require(
        len(candidate_bytes) == candidate["bytes"]
        and hashlib.sha256(candidate_bytes).hexdigest() == candidate["sha256"],
        "Requirements/domain frozen candidate bytes drifted",
    )
    for key in ("sourceEvidence", "lineageEvidence"):
        _require((root / candidate[key]).is_file(), f"Candidate {key} is missing")

    fixture = document.get("fixtureDesign", {})
    _require(
        fixture.get("fixtureId") == "fixture.source-bound-domain-plan-challenge-v1"
        and fixture.get("allowedMutableFiles") == ["REQUIREMENTS_REVIEW.json"]
        and len(fixture.get("immutableInputs", [])) == 6
        and len(fixture.get("sharedAcceptance", [])) == 10
        and len(fixture.get("falsifiers", [])) == 6
        and "must not require an undisclosed preferred wording"
        in fixture.get("hiddenOracleBoundary", ""),
        "Requirements/domain fixture contract drifted",
    )

    arms = {item.get("id"): item for item in document.get("arms", [])}
    _require(
        set(arms)
        == {
            "SE-REQ-NATIVE-SPARK",
            "SE-REQ-CC-GRILL-WITH-DOCS",
            "SE-REQ-HUMAN-CONTROL",
        }
        and arms["SE-REQ-NATIVE-SPARK"].get("allConfigurableUserSkillsDisabled")
        is True
        and arms["SE-REQ-CC-GRILL-WITH-DOCS"].get("selectedUserSkills")
        == ["cc.grill-with-docs"],
        "Requirements/domain arm set drifted",
    )

    authority = document.get("authorityBoundary", {})
    _require(
        authority.get("repositoryProtocolWritesAuthorized") is True
        and authority.get("disposableFixtureWritesAuthorized") is True,
        "Requirements/domain local authority drifted",
    )
    for key, value in authority.items():
        if key not in {
            "repositoryProtocolWritesAuthorized",
            "disposableFixtureWritesAuthorized",
        }:
            _require(value is False, f"Requirements/domain authority expanded: {key}")

    gate = document.get("executionGate", {})
    for key in (
        "fixtureBuilderImplemented",
        "privateOracleImplemented",
        "offlineClassifierFixturesPass",
    ):
        _require(gate.get(key) is True, f"Requirements/domain implementation gate rolled back: {key}")
    _require(
        gate.get("fixtureDefinition")
        == "tests/fixtures/human-ai-collaboration-requirements-domain-challenge-batch-01-2026-07-24.json"
        and gate.get("fixtureDefinitionSha256")
        == "3b06392a4ac47a76d0a1eea5e777533c67577a13abca890204f4a8aba61dbb81"
        and gate.get("fixtureBuilder")
        == "scripts/build_human_ai_collaboration_requirements_domain_trial.py"
        and gate.get("fixtureBuilderSha256")
        == "ee71f0f393744ad3852af1fd3c7e5d32aef084a515f1d70e0a2b12e25ec74822"
        and (root / gate["fixtureDefinition"]).is_file()
        and (root / gate["fixtureBuilder"]).is_file(),
        "Requirements/domain fixture implementation pin drifted",
    )
    _require(
        gate.get("minimumValidPairsPerPrimaryArm") == 3
        and gate.get("invalidEnvironmentOrMeasurementRunsCount") == 9,
        "Requirements/domain repetition boundary drifted",
    )
    _require(
        gate.get("freshCandidateHashVerified") is True
        and gate.get("nativeDisabledExposureProved") is True
        and gate.get("candidateSpecificSelectedExposureProved") is True
        and gate.get("publicPromptPrivateOracleBoundaryPassed") is True
        and gate.get("preflightEvidence")
        == "registry/requirements-domain-exposure-preflight-evidence-2026-07-24.json"
        and (root / gate["preflightEvidence"]).is_file(),
        "Requirements/domain exposure preflight drifted",
    )
    invalid = document.get("invalidMeasurementRuns", [])
    _require(
        len(invalid) == 9
        and invalid[0].get("id") == "oracle-v1-flat-shape-native"
        and invalid[0].get("reportFileSha256")
        == "a3e80c479cb15ba1b20e3245b6d7bd844c3f1fdc7f057f8cad900a88f8c0f44c"
        and invalid[0].get("internalReportSha256")
        == "c17f6611ea2e6bfa383012cf77968fe4b54b720a35f87c600f5c456f2b10a797"
        and invalid[0].get("countsInAggregate") is False,
        "Requirements/domain invalid measurement accounting drifted",
    )
    _require(
        invalid[1].get("id") == "oracle-v2-value-only-flattening-native"
        and invalid[1].get("threadId")
        == "019f97b9-cc1a-7ff3-b63b-74c6f5510627"
        and invalid[1].get("turnId")
        == "019f97b9-cda2-71d0-9e3e-44afaacbe5c7"
        and invalid[1].get("reportFileSha256")
        == "fe5929e21c37d0dfa2478401ddbf81a531be3049c6bd66719eea532f169dbe4d"
        and invalid[1].get("internalReportSha256")
        == "5e8cc3b2c3121fcd3c26068b99487b438c1271e43b5054419e10f1eb912d0ece"
        and invalid[1].get("postCorrectionFailureCodes")
        == ["fail-review-state"]
        and invalid[1].get("countsInAggregate") is False,
        "Requirements/domain second invalid measurement accounting drifted",
    )
    _require(
        invalid[2].get("id") == "oracle-v3-undisclosed-order-term-native"
        and invalid[2].get("reportFileSha256")
        == "b73a51ee03cf0fa1fe9977ac7f3b36f4b788baa230616bb35b5428227d1277c0"
        and invalid[2].get("postCorrectionFailureCodes")
        == [
            "fail-review-state",
            "fail-question-topic",
            "fail-final-question",
            "fail-final-question-topic",
        ]
        and invalid[2].get("countsInAggregate") is False,
        "Requirements/domain third invalid measurement accounting drifted",
    )
    _require(
        invalid[3].get("id") == "oracle-v3-undisclosed-order-term-candidate"
        and invalid[3].get("reportFileSha256")
        == "9bf80c3d6471b05a0960528fecdc94862b25d8e0d240a460b7867fe9c7c5db23"
        and invalid[3].get("postCorrectionFailureCodes")
        == ["fail-review-state"]
        and invalid[3].get("countsInAggregate") is False,
        "Requirements/domain fourth invalid measurement accounting drifted",
    )
    _require(
        invalid[4].get("id")
        == "runner-v1-json-content-write-target-false-positive-native"
        and invalid[4].get("reportFileSha256")
        == "0244845c360389ed8769d2081d59a4cdcb59dc69159499b1e2f15d6b37d2f3d7"
        and invalid[4].get("internalReportSha256")
        == "7b813973c4235468a03d899c4d760fd28417df3c91056c95afe4bf451421eed2"
        and invalid[4].get("correctedRunnerSha256")
        == "2ee64fdc5ccc2164e978e6fa77a51d5cfd46f8b05b29ac03871d5dfae36bd567"
        and invalid[4].get("countsInAggregate") is False,
        "Requirements/domain fifth invalid measurement accounting drifted",
    )
    _require(
        invalid[5].get("id")
        == "oracle-v4-english-only-question-normalization-native"
        and invalid[5].get("reportFileSha256")
        == "5a52c77e3b263f765731bbdd4996dc01b550ff95c4d7f7854479273a62d7fc51"
        and invalid[5].get("internalReportSha256")
        == "50e0919c7b80faa7d25b5c36d2281f8dda7861ee478aeabc910c9c9cdf5b322d"
        and invalid[5].get("postCorrectionFailureCodes")
        == ["fail-review-state"]
        and invalid[5].get("countsInAggregate") is False,
        "Requirements/domain sixth invalid measurement accounting drifted",
    )
    _require(
        invalid[6].get("id")
        == "runner-v2-app-server-escaped-target-candidate"
        and invalid[6].get("reportFileSha256")
        == "0d9978fd5607012e4f98f059673ea050e169dd224c4a470540da276a47cb4969"
        and invalid[6].get("correctedRunnerSha256")
        == "c2641bc868e74847720ca51a2f632804b62e39c7ef00694ecee71d90aea3c94d"
        and invalid[6].get("countsInAggregate") is False,
        "Requirements/domain seventh invalid measurement accounting drifted",
    )
    _require(
        invalid[7].get("id")
        == "host-turn-timeout-stable-pair-01-candidate"
        and invalid[7].get("timeoutSeconds") == 300
        and invalid[7].get("reportProduced") is False
        and invalid[7].get("stderrSha256")
        == "85dc576e9ed59e63d79c805671abdb07baf6b43a180fd4fd50a4e3dcd363e6ce"
        and invalid[7].get("countsInAggregate") is False,
        "Requirements/domain eighth invalid environment run drifted",
    )
    _require(
        invalid[8].get("id")
        == "oracle-v5-non-object-question-crash-stable-pair-02-candidate"
        and invalid[8].get("reportProduced") is False
        and invalid[8].get("stderrSha256")
        == "29d214604714d225347e8df90f6568fdc587a640c4c7d395d0f85093c937d64b"
        and invalid[8].get("correctedBuilderSha256")
        == "ee71f0f393744ad3852af1fd3c7e5d32aef084a515f1d70e0a2b12e25ec74822"
        and invalid[8].get("countsInAggregate") is False,
        "Requirements/domain ninth invalid measurement run drifted",
    )

    decision = document.get("decision", {})
    _require(
        decision.get("scenarioSelected") is True
        and decision.get("candidateSuitabilityReviewed") is True
        and decision.get("liveExecutionStarted") is False
        and decision.get("preferenceDecisionAllowed") is False
        and decision.get("selfAuthoredChangeJustified") is False
        and decision.get("candidateInstallUpdateOrRemovalJustified") is False,
        "Requirements/domain decision overclaimed",
    )
    _require(
        all(value is False for value in document.get("claimBoundary", {}).values()),
        "Requirements/domain claim boundary was promoted",
    )

    doc_path = root / str(document.get("documentation"))
    _require(doc_path.is_file(), "Requirements/domain protocol documentation is missing")
    text = " ".join(doc_path.read_text(encoding="utf-8").split())
    for phrase in (
        "materially different upstream collaboration test",
        "exactly one highest-priority blocking question",
        "wording-neutral",
        "five offline",
        "no private oracle sentinel",
        "proves no candidate value",
    ):
        _require(phrase in text, f"Requirements/domain documentation missing boundary: {phrase}")


def main() -> int:
    document = json.loads((ROOT / PROTOCOL_PATH).read_text(encoding="utf-8"))
    validate_protocol(document, root=ROOT)
    print("Requirements/domain challenge protocol validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
