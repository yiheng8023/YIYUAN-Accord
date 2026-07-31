#!/usr/bin/env python3
"""Validate the source-bound GEN-CREATIVE-01 capability baseline."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

try:
    from evaluate_human_ai_collaboration_unknown_knowns_creative_preference_packet import (
        evaluate_packet_document,
    )
except ModuleNotFoundError:  # Imported as scripts.* from repository-root tests.
    from scripts.evaluate_human_ai_collaboration_unknown_knowns_creative_preference_packet import (
        evaluate_packet_document,
    )


ROOT = Path(__file__).resolve().parent.parent
BASELINE_PATH = ROOT / (
    "registry/human-ai-collaboration-creative-capability-baseline-2026-07-31.json"
)
DOCUMENT_PATH = (
    ROOT / "docs/strategy/HUMAN-AI-COLLABORATION-CREATIVE-CAPABILITY-BASELINE-2026-07-31.md"
)
SCENARIO_MATRIX_PATH = (
    ROOT / "registry/human-ai-collaboration-scenario-evidence-matrix-batch-01-2026-07-24.json"
)
PACKET_PATH = (
    ROOT
    / "tests/fixtures/human-ai-collaboration-unknown-knowns-creative-preference-packet-2026-07-27.json"
)
PROGRAM_MAP_PATH = ROOT / "registry/program-acceptance-map.json"
PROGRAM_PLAN_PATH = ROOT / "registry/curation-program-plan.json"
EVIDENCE_ID = "evidence.human-ai-collaboration-creative-capability-baseline-2026-07-31"
EXPECTED_ACCEPTANCE_IDS = {
    "acceptance.solution-neutral-collaboration-rebaseline",
    "acceptance.capability-survey-result-package",
    "acceptance.cross-agent-claim-limits",
    "acceptance.residual-gap-proof",
}
EXPECTED_ALTERNATIVES = {
    "alternative.native-open-divergence",
    "alternative.official-openai-creative-production",
    "alternative.conditional-grilling-then-official-production",
    "alternative.human-led-ideation-control",
}
EXPECTED_EXCLUSIONS = {
    "external.superpowers-brainstorming-6.2.0",
    "external.huashu-current-root-suite",
}
EXPECTED_OFFICIAL_FILES = {
    ".codex-plugin/plugin.json": (
        2168,
        "3dc7136df983952de274587cb357620aaf566a102dd88bc96e9526542ea61eec",
    ),
    ".app.json": (
        17,
        "1284c18c07b6548843fdcaa9ff0cb0d2dd61d029248cfa3f93a2dddeba55d0fb",
    ),
    ".mcp.json": (
        166,
        "ea6d3c52f5c6782d7e3737f8937ae7df48ecacbdc4d92eba178ea757b1d6eb4b",
    ),
    "skills/intake/SKILL.md": (
        1367,
        "8b5c1b507e48ef90ed1104eee45d4a3f3c780f37683d487ff16dc635e1fe666e",
    ),
    "skills/produce/SKILL.md": (
        5026,
        "056d2f32c7d27639c3cf861981d7331cab8e7723ded1ae1966de6efd8ce01b7c",
    ),
    "skills/produce/references/contracts/source-preservation.md": (
        417,
        "d1084b343e9ba956fd6d6ebee0306074852a378df3dbfadf370dbe32b74160f0",
    ),
    "skills/produce/references/contracts/exact-content.md": (
        458,
        "ebad12eb80f6fc1d0254d59fda901400443320fc691ee6d25afe7f87d03b9b20",
    ),
}
EXPECTED_GRILLING_FILES = {
    "SKILL.md": (
        843,
        "44331dda57f461db4fec3f2efb6ddabe7aaaa0a57ae0f88a883bc61aed8a0587",
    ),
    "agents/openai.yaml": (
        105,
        "cf29b9a8dbf35a58a908a6ca4f64dcd86c2b2130291eee0a78b9f706b138825b",
    ),
}


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _records(records: list[dict[str, Any]]) -> dict[str, tuple[int, str]]:
    return {
        str(item.get("path")): (int(item.get("bytes", -1)), str(item.get("sha256")))
        for item in records
    }


def validate_baseline(
    baseline: dict[str, Any] | None = None,
    *,
    root: Path = ROOT,
    scenario_matrix: dict[str, Any] | None = None,
    packet: dict[str, Any] | None = None,
    program_map: dict[str, Any] | None = None,
    program_plan: dict[str, Any] | None = None,
) -> None:
    baseline = baseline or _load(
        root
        / "registry/human-ai-collaboration-creative-capability-baseline-2026-07-31.json"
    )
    scenario_matrix = scenario_matrix or _load(
        root
        / "registry/human-ai-collaboration-scenario-evidence-matrix-batch-01-2026-07-24.json"
    )
    packet = packet or _load(
        root
        / "tests/fixtures/human-ai-collaboration-unknown-knowns-creative-preference-packet-2026-07-27.json"
    )
    program_map = program_map or _load(root / "registry/program-acceptance-map.json")
    program_plan = program_plan or _load(root / "registry/curation-program-plan.json")

    _require(baseline.get("schema") == 1, "Creative baseline schema drifted")
    _require(
        baseline.get("status")
        == "source-bound-static-capability-baseline-no-live-creative-rights-admission-or-standard-evidence",
        "Creative baseline status drifted",
    )

    binding = baseline.get("scenarioBinding", {})
    _require(
        binding.get("scenarioId") == "GEN-CREATIVE-01",
        "Creative scenario binding drifted",
    )
    _require(
        binding.get("evidenceStateMustRemain") == "planned-no-live-domain-evidence",
        "Creative evidence boundary drifted",
    )
    scenarios = {item.get("id"): item for item in scenario_matrix.get("scenarios", [])}
    scenario = scenarios.get("GEN-CREATIVE-01")
    _require(scenario is not None, "GEN-CREATIVE-01 is missing")
    _require(
        scenario.get("evidenceState") == "planned-no-live-domain-evidence",
        "Static creative baseline promoted scenario evidence",
    )
    _require(
        scenario.get("task") == binding.get("task")
        and scenario.get("authorityBoundary") == binding.get("authorityBoundary")
        and scenario.get("dataBoundary") == binding.get("dataBoundary"),
        "Creative task or authority boundary drifted",
    )
    _require(
        set(scenario.get("acceptanceSignals", []))
        == set(binding.get("acceptanceSignals", []))
        and set(scenario.get("evidenceNeeded", [])) == set(binding.get("requiredEvidence", [])),
        "Creative evidence surface drifted",
    )

    for source in baseline.get("repositorySourceBindings", []):
        path = root / str(source.get("path", ""))
        _require(path.is_file(), f"Bound creative source is missing: {source.get('path')}")
        _require(
            path.stat().st_size == source.get("bytes"),
            f"Bound creative source size drifted: {source.get('path')}",
        )
        _require(
            _sha256(path) == source.get("sha256"),
            f"Bound creative source hash drifted: {source.get('path')}",
        )

    packet_binding = baseline.get("existingZeroModelPacket", {})
    _require(
        packet_binding.get("offlineExampleCount") == 6,
        "Creative packet count drifted",
    )
    _require(
        packet_binding.get("reuseDecision")
        == "reuse-as-deterministic-output-gate-do-not-duplicate",
        "Creative packet reuse decision drifted",
    )
    _require(
        packet_binding.get("candidateBehaviorProved") is False
        and packet_binding.get("liveCreativeValueProved") is False,
        "Creative packet was promoted to behavior or value evidence",
    )
    results = evaluate_packet_document(packet)
    _require(
        len(results) == 6
        and all(item["actual"] == item["expected"] for item in results),
        "Existing creative packet no longer matches its deterministic oracle",
    )

    official = baseline.get("officialCreativeProductionObservation", {})
    _require(
        official.get("id") == "official.openai-creative-production-0.1.25"
        and official.get("owner") == "OpenAI"
        and official.get("version") == "0.1.25",
        "Official creative candidate identity drifted",
    )
    _require(
        _records(official.get("packageFileRecords", [])) == EXPECTED_OFFICIAL_FILES,
        "Official creative source record drifted",
    )
    _require(
        official.get("implicitInvocationAllowedByMetadata") is True
        and official.get("appDeclarationContainsCallableApps") is False
        and official.get("bundledMcpDeclared") is True,
        "Official creative package-shape observation drifted",
    )
    for field in (
        "currentTaskMcpHealthProved",
        "boardOrGenerationExecutionAuthorized",
        "instructionDeliveryOrBehaviorProved",
        "rightsOrCreativeValueProved",
    ):
        _require(
            official.get(field) is False,
            f"Official creative static evidence promoted {field}",
        )

    grilling = baseline.get("conditionalGrillingObservation", {})
    _require(
        grilling.get("observedHead") == "2ab958093e83e0ec752e6c1c5932da465bf23e0c",
        "Grilling source pin drifted",
    )
    _require(
        _records(grilling.get("fileRecords", [])) == EXPECTED_GRILLING_FILES,
        "Grilling source record drifted",
    )
    _require(
        grilling.get("defaultDisposition") == "not-a-default-creative-treatment"
        and grilling.get("metadataExplicitlyAllowsImplicitInvocation") is False
        and grilling.get("instructionDeliveryOrMarginalValueProved") is False,
        "Grilling proportional-use boundary drifted",
    )

    exclusions = baseline.get("excludedNearMatchObservations", [])
    _require(
        {item.get("id") for item in exclusions} == EXPECTED_EXCLUSIONS,
        "Creative near-match exclusions drifted",
    )
    alternatives = baseline.get("representativeAlternatives", [])
    _require(
        {item.get("id") for item in alternatives} == EXPECTED_ALTERNATIVES,
        "Creative representative alternatives drifted",
    )
    decision = baseline.get("comparisonDecision", {})
    _require(
        decision.get("representativeSetSufficientForNextEvidenceGate") is True,
        "Creative representative-set decision drifted",
    )
    for field in (
        "widerThirdPartyDiscoveryNeededNow",
        "externalCapabilityInstallationNeededNow",
        "candidateExecutionNeededNow",
        "newZeroModelPacketNeededNow",
        "selfAuthoredSkillNeededNow",
        "skillOrHardStandardExtractionNeededNow",
    ):
        _require(decision.get(field) is False, f"Creative baseline expanded scope: {field}")
    _require(
        decision.get("residualGapState")
        == "behavior-rights-and-edit-burden-evidence-gap-not-capability-name-gap",
        "Creative residual-gap classification drifted",
    )

    neutrality = baseline.get("neutralityAndJudgmentBoundary", {})
    _require(
        neutrality.get("projectNeutralityChanged") is False,
        "Stable project neutrality was misrepresented as a change",
    )
    _require(
        neutrality.get("finalAestheticDecisionOwner") == "human"
        and neutrality.get("rightsAndPublicationDecisionOwner")
        == "authorized-human-or-accountable-organization",
        "Creative human decision ownership drifted",
    )

    authority = baseline.get("authorityBoundary", {})
    _require(
        isinstance(authority, dict)
        and authority
        and all(value is False for value in authority.values()),
        "Creative baseline expanded authority",
    )
    claims = baseline.get("claimLimits", {})
    _require(
        isinstance(claims, dict)
        and claims
        and all(value is False for value in claims.values()),
        "Creative baseline promoted a prohibited claim",
    )

    acceptances = {
        item.get("id"): item for item in program_map.get("acceptanceCriteria", [])
    }
    _require(len(acceptances) == 61, "Program acceptance count changed")
    for acceptance_id in EXPECTED_ACCEPTANCE_IDS:
        _require(acceptance_id in acceptances, f"Acceptance is missing: {acceptance_id}")
        _require(
            EVIDENCE_ID in acceptances[acceptance_id].get("evidenceIds", []),
            f"Creative evidence is not linked to {acceptance_id}",
        )
    evidence = {item.get("id"): item for item in program_map.get("evidence", [])}
    _require(EVIDENCE_ID in evidence, "Creative program evidence record is missing")
    _require(
        set(evidence[EVIDENCE_ID].get("supports", [])) == EXPECTED_ACCEPTANCE_IDS,
        "Creative program-evidence support set drifted",
    )

    initiatives = {item.get("id"): item for item in program_plan.get("currentInitiatives", [])}
    survey = initiatives.get("initiative.capability-survey-gap-proof")
    coverage = initiatives.get("initiative.human-ai-collaboration-coverage-rebaseline")
    _require(survey is not None and coverage is not None, "Creative parent initiative is missing")
    expected_path = "registry/human-ai-collaboration-creative-capability-baseline-2026-07-31.json"
    _require(
        survey.get("currentCreativeCapabilityBaseline") == expected_path,
        "Capability-survey creative baseline pointer is missing",
    )
    _require(
        coverage.get("currentCreativeCapabilityBaseline") == expected_path,
        "Coverage-rebaseline creative baseline pointer is missing",
    )

    document = (
        root
        / "docs/strategy/HUMAN-AI-COLLABORATION-CREATIVE-CAPABILITY-BASELINE-2026-07-31.md"
    ).read_text(encoding="utf-8")
    normalized = " ".join(document.split())
    for phrase in (
        "Project neutrality has not changed",
        "behavior-, rights-, and edit-burden evidence gap, not a capability-name gap",
        "reused, not duplicated",
        "not the default creative route",
        "Direction count is not creative diversity",
        "Explicit non-authorizations",
    ):
        _require(phrase in normalized, f"Creative strategy document missing: {phrase}")


def main() -> int:
    validate_baseline()
    print("Human-AI creative capability baseline validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
