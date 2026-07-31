#!/usr/bin/env python3
"""Validate the source-bound GEN-LEARNING-01 capability baseline."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
BASELINE_PATH = (
    ROOT / "registry/human-ai-collaboration-learning-capability-baseline-2026-07-31.json"
)
DOCUMENT_PATH = (
    ROOT / "docs/strategy/HUMAN-AI-COLLABORATION-LEARNING-CAPABILITY-BASELINE-2026-07-31.md"
)
SCENARIO_MATRIX_PATH = (
    ROOT / "registry/human-ai-collaboration-scenario-evidence-matrix-batch-01-2026-07-24.json"
)
CLAIM_LEDGER_PATH = (
    ROOT / "registry/human-ai-collaboration-high-impact-primary-source-claim-ledger-2026-07-27.json"
)
PROGRAM_MAP_PATH = ROOT / "registry/program-acceptance-map.json"
PROGRAM_PLAN_PATH = ROOT / "registry/curation-program-plan.json"
EVIDENCE_ID = "evidence.human-ai-collaboration-learning-capability-baseline-2026-07-31"
EXPECTED_OFFICIAL_IDS = {
    "official.openai-chatgpt-study-mode",
    "official.anthropic-claude-learning-mode",
    "official.google-gemini-guided-learning",
}
EXPECTED_ALTERNATIVES = {
    "alternative.native-no-dedicated-learning-capability",
    "alternative.official-host-learning-mode",
    "alternative.matt-teach-explicit",
    "alternative.human-instructor-control",
}
EXPECTED_ACCEPTANCE_IDS = {
    "acceptance.solution-neutral-collaboration-rebaseline",
    "acceptance.capability-survey-result-package",
    "acceptance.cross-agent-claim-limits",
    "acceptance.residual-gap-proof",
}


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _canonical_manifest_sha(records: list[dict[str, Any]]) -> str:
    payload = json.dumps(
        records,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def validate_baseline(
    baseline: dict[str, Any] | None = None,
    *,
    root: Path = ROOT,
    scenario_matrix: dict[str, Any] | None = None,
    claim_ledger: dict[str, Any] | None = None,
    program_map: dict[str, Any] | None = None,
    program_plan: dict[str, Any] | None = None,
) -> None:
    baseline = baseline or _load(
        root
        / "registry/human-ai-collaboration-learning-capability-baseline-2026-07-31.json"
    )
    scenario_matrix = scenario_matrix or _load(
        root
        / "registry/human-ai-collaboration-scenario-evidence-matrix-batch-01-2026-07-24.json"
    )
    claim_ledger = claim_ledger or _load(
        root
        / "registry/human-ai-collaboration-high-impact-primary-source-claim-ledger-2026-07-27.json"
    )
    program_map = program_map or _load(root / "registry/program-acceptance-map.json")
    program_plan = program_plan or _load(root / "registry/curation-program-plan.json")

    _require(baseline.get("schema") == 1, "Learning baseline schema drifted")
    _require(
        baseline.get("status")
        == "source-bound-static-capability-baseline-no-live-learning-or-admission-evidence",
        "Learning baseline status drifted",
    )

    binding = baseline.get("scenarioBinding", {})
    _require(binding.get("scenarioId") == "GEN-LEARNING-01", "Scenario binding drifted")
    _require(
        binding.get("evidenceStateMustRemain") == "planned-no-live-domain-evidence",
        "Scenario evidence boundary drifted",
    )
    scenarios = {item.get("id"): item for item in scenario_matrix.get("scenarios", [])}
    scenario = scenarios.get("GEN-LEARNING-01")
    _require(scenario is not None, "GEN-LEARNING-01 is missing")
    _require(
        scenario.get("evidenceState") == "planned-no-live-domain-evidence",
        "Static baseline promoted scenario evidence",
    )
    _require(
        scenario.get("task") == binding.get("task")
        and scenario.get("authorityBoundary") == binding.get("authorityBoundary")
        and scenario.get("dataBoundary") == binding.get("dataBoundary"),
        "Scenario task or authority boundary drifted",
    )
    _require(
        set(scenario.get("evidenceNeeded", [])) == set(binding.get("requiredEvidence", [])),
        "Scenario evidence requirements drifted",
    )

    claims = {item.get("id"): item for item in claim_ledger.get("claims", [])}
    claim_id = binding.get("primarySourceDesignInputId")
    _require(claim_id in claims, "Learning design-input claim is missing")
    _require(
        "GEN-LEARNING-01" in claims[claim_id].get("allowedScenarioIds", []),
        "Learning claim is not bound to the scenario",
    )

    for source in baseline.get("repositorySourceBindings", []):
        path = root / str(source.get("path", ""))
        _require(path.is_file(), f"Bound repository source is missing: {source.get('path')}")
        _require(path.stat().st_size == source.get("bytes"), f"Bound source size drifted: {source.get('path')}")
        _require(_sha256(path) == source.get("sha256"), f"Bound source hash drifted: {source.get('path')}")

    official = baseline.get("officialCapabilityObservations", [])
    _require(
        {item.get("id") for item in official} == EXPECTED_OFFICIAL_IDS,
        "Official learning-capability set drifted",
    )
    for item in official:
        _require(str(item.get("locator", "")).startswith("https://"), "Official source locator is invalid")
        for field in (
            "currentUserAccountAvailabilityProved",
            "delayedRetentionOrTransferOutcomeProved",
            "crossHostBehaviorProved",
        ):
            _require(item.get(field) is False, f"Official metadata promoted {field}: {item.get('id')}")

    teach = baseline.get("mattTeachObservation", {})
    _require(
        teach.get("observedHead") == "2ab958093e83e0ec752e6c1c5932da465bf23e0c",
        "Matt teach source pin drifted",
    )
    records = teach.get("fileRecords", [])
    _require(len(records) == 6, "Matt teach file set drifted")
    _require(
        _canonical_manifest_sha(records) == teach.get("fileRecordManifestSha256"),
        "Matt teach file manifest drifted",
    )
    _require(
        {item.get("path") for item in records}
        == {
            "GLOSSARY-FORMAT.md",
            "LEARNING-RECORD-FORMAT.md",
            "MISSION-FORMAT.md",
            "RESOURCES-FORMAT.md",
            "SKILL.md",
            "agents/openai.yaml",
        },
        "Matt teach exact file inventory drifted",
    )
    _require(
        teach.get("implicitInvocationAllowedByOpenAiMetadata") is False,
        "Matt teach explicit-invocation boundary drifted",
    )
    for field in (
        "installedOrProjectedStateProvesInstructionDelivery",
        "behaviorOrLearningValueProved",
        "delayedRetentionOrNovelTransferProved",
    ):
        _require(teach.get(field) is False, f"Matt teach static evidence promoted {field}")

    alternatives = baseline.get("representativeAlternatives", [])
    _require(
        {item.get("id") for item in alternatives} == EXPECTED_ALTERNATIVES,
        "Representative learning alternatives drifted",
    )
    decision = baseline.get("comparisonDecision", {})
    _require(
        decision.get("representativeSetSufficientForProtocolDesign") is True,
        "Representative-set decision drifted",
    )
    for field in (
        "widerThirdPartyDiscoveryNeededNow",
        "externalCapabilityInstallationNeededNow",
        "candidateExecutionNeededNow",
        "selfAuthoredSkillNeededNow",
        "skillOrHardStandardExtractionNeededNow",
    ):
        _require(decision.get(field) is False, f"Learning baseline expanded scope: {field}")
    _require(
        decision.get("residualGapState")
        == "behavioral-evidence-gap-not-capability-name-gap",
        "Residual-gap classification drifted",
    )

    authority = baseline.get("authorityBoundary", {})
    _require(
        isinstance(authority, dict)
        and authority
        and all(value is False for value in authority.values()),
        "Learning baseline expanded authority",
    )
    claims_boundary = baseline.get("claimLimits", {})
    _require(
        isinstance(claims_boundary, dict)
        and claims_boundary
        and all(value is False for value in claims_boundary.values()),
        "Learning baseline promoted a prohibited claim",
    )

    acceptances = {
        item.get("id"): item for item in program_map.get("acceptanceCriteria", [])
    }
    _require(len(acceptances) == 61, "Program acceptance count changed")
    for acceptance_id in EXPECTED_ACCEPTANCE_IDS:
        _require(acceptance_id in acceptances, f"Acceptance is missing: {acceptance_id}")
        _require(
            EVIDENCE_ID in acceptances[acceptance_id].get("evidenceIds", []),
            f"Learning evidence is not linked to {acceptance_id}",
        )
    evidence = {item.get("id"): item for item in program_map.get("evidence", [])}
    _require(EVIDENCE_ID in evidence, "Learning program evidence record is missing")
    _require(
        set(evidence[EVIDENCE_ID].get("supports", [])) == EXPECTED_ACCEPTANCE_IDS,
        "Learning program-evidence support set drifted",
    )

    initiatives = {item.get("id"): item for item in program_plan.get("currentInitiatives", [])}
    survey = initiatives.get("initiative.capability-survey-gap-proof")
    coverage = initiatives.get("initiative.human-ai-collaboration-coverage-rebaseline")
    _require(survey is not None and coverage is not None, "Learning parent initiative is missing")
    expected_path = "registry/human-ai-collaboration-learning-capability-baseline-2026-07-31.json"
    _require(
        survey.get("currentLearningCapabilityBaseline") == expected_path,
        "Capability-survey learning baseline pointer is missing",
    )
    _require(
        coverage.get("currentLearningCapabilityBaseline") == expected_path,
        "Coverage-rebaseline learning baseline pointer is missing",
    )

    document = (
        root
        / "docs/strategy/HUMAN-AI-COLLABORATION-LEARNING-CAPABILITY-BASELINE-2026-07-31.md"
    ).read_text(encoding="utf-8")
    normalized = " ".join(document.split())
    for phrase in (
        "behavioral-evidence gap, not a capability-name gap",
        "planned-no-live-domain-evidence",
        "must not be merged into a fictional cross-host treatment",
        "stays installed but task-bound and explicit",
        "Simulation comes first",
        "Explicit non-authorizations",
    ):
        _require(phrase in normalized, f"Learning strategy document missing: {phrase}")


def main() -> int:
    validate_baseline()
    print("Human-AI learning capability baseline validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
