#!/usr/bin/env python3
"""Validate the source-bound GEN-ACCESS-COMMS-01 capability baseline."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

try:
    from evaluate_human_ai_collaboration_access_comms_zero_model_calibration import (
        evaluate_calibration,
    )
except ModuleNotFoundError:  # Imported as scripts.* from repository-root tests.
    from scripts.evaluate_human_ai_collaboration_access_comms_zero_model_calibration import (
        evaluate_calibration,
    )


ROOT = Path(__file__).resolve().parent.parent
BASELINE_PATH = ROOT / (
    "registry/human-ai-collaboration-access-comms-capability-baseline-2026-07-31.json"
)
DOCUMENT_PATH = ROOT / (
    "docs/strategy/HUMAN-AI-COLLABORATION-ACCESS-COMMS-CAPABILITY-BASELINE-2026-07-31.md"
)
SCENARIO_MATRIX_PATH = ROOT / (
    "registry/human-ai-collaboration-scenario-evidence-matrix-batch-01-2026-07-24.json"
)
PROTOCOL_PATH = ROOT / (
    "registry/human-ai-collaboration-access-comms-zero-model-protocol-2026-07-27.json"
)
FIXTURE_PATH = ROOT / (
    "tests/fixtures/human-ai-collaboration-access-comms-zero-model-calibration-2026-07-27.json"
)
PROGRAM_MAP_PATH = ROOT / "registry/program-acceptance-map.json"
PROGRAM_PLAN_PATH = ROOT / "registry/curation-program-plan.json"
EVIDENCE_ID = (
    "evidence.human-ai-collaboration-access-comms-capability-baseline-2026-07-31"
)
EXPECTED_ACCEPTANCE_IDS = {
    "acceptance.solution-neutral-collaboration-rebaseline",
    "acceptance.capability-survey-result-package",
    "acceptance.cross-agent-claim-limits",
    "acceptance.residual-gap-proof",
}
EXPECTED_FAULT_CLASSES = {
    "accessibility-structure-break",
    "actor-swap",
    "deadline-unit-drift",
    "invented-commitment",
    "negation-flip",
    "obligation-weakening",
    "terminology-drift",
    "uncertainty-deletion",
}
EXPECTED_ROUTE_IDS = {
    "route.source-and-terminology-lock",
    "route.native-semantic-adaptation",
    "route.existing-zero-model-semantic-gate",
    "route.conditional-official-documents-carrier",
    "route.human-review-and-release-control",
}
EXPECTED_DOCUMENT_FILES = {
    ".codex-plugin/plugin.json": (
        1570,
        "1f12c88438dd7ce1ded2d8b063929002f8009c87496a644ec69d71a5bd5dc6d2",
    ),
    "skills/documents/SKILL.md": (
        39780,
        "84dd796a7834889191515ea6508abc9d6559314dd554e0345eeaa07c5e780bd5",
    ),
    "skills/documents/tasks/accessibility_a11y.md": (
        2019,
        "951dca7ba7e520792776a636c22e512a9a3c53699c6da80c5c3e47b0690c1374",
    ),
    "skills/documents/scripts/a11y_audit.py": (
        13207,
        "a832e288503704a24ae4e7d9bde4444dee01c835c651f746f19167c4ef4632bf",
    ),
}
EXPECTED_EXTERNAL_IDS = {
    "external.microsoft-azure-ai-translation-text-py",
    "reference.weblate-glossary",
    "reference.translate-toolkit-pofilter",
    "reference.w3c-wai-readable-and-accessibility-principles",
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
    protocol: dict[str, Any] | None = None,
    fixture: dict[str, Any] | None = None,
    program_map: dict[str, Any] | None = None,
    program_plan: dict[str, Any] | None = None,
) -> None:
    baseline = baseline or _load(
        root
        / "registry/human-ai-collaboration-access-comms-capability-baseline-2026-07-31.json"
    )
    scenario_matrix = scenario_matrix or _load(
        root
        / "registry/human-ai-collaboration-scenario-evidence-matrix-batch-01-2026-07-24.json"
    )
    protocol = protocol or _load(
        root
        / "registry/human-ai-collaboration-access-comms-zero-model-protocol-2026-07-27.json"
    )
    fixture = fixture or _load(
        root
        / "tests/fixtures/human-ai-collaboration-access-comms-zero-model-calibration-2026-07-27.json"
    )
    program_map = program_map or _load(root / "registry/program-acceptance-map.json")
    program_plan = program_plan or _load(root / "registry/curation-program-plan.json")

    _require(baseline.get("schema") == 1, "Access/comms baseline schema drifted")
    _require(
        baseline.get("status")
        == "source-bound-static-capability-baseline-no-live-translation-accessibility-recipient-admission-or-standard-evidence",
        "Access/comms baseline status drifted",
    )

    binding = baseline.get("scenarioBinding", {})
    _require(
        binding.get("scenarioId") == "GEN-ACCESS-COMMS-01",
        "Access/comms scenario binding drifted",
    )
    _require(
        binding.get("evidenceStateMustRemain") == "planned-no-live-domain-evidence",
        "Access/comms evidence boundary drifted",
    )
    scenarios = {item.get("id"): item for item in scenario_matrix.get("scenarios", [])}
    scenario = scenarios.get("GEN-ACCESS-COMMS-01")
    _require(scenario is not None, "GEN-ACCESS-COMMS-01 is missing")
    _require(
        scenario.get("evidenceState") == "planned-no-live-domain-evidence",
        "Static access/comms baseline promoted scenario evidence",
    )
    _require(
        scenario.get("task") == binding.get("task")
        and scenario.get("authorityBoundary") == binding.get("authorityBoundary")
        and scenario.get("dataBoundary") == binding.get("dataBoundary"),
        "Access/comms task or authority boundary drifted",
    )
    _require(
        set(scenario.get("acceptanceSignals", []))
        == set(binding.get("acceptanceSignals", []))
        and set(scenario.get("evidenceNeeded", []))
        == set(binding.get("requiredEvidence", [])),
        "Access/comms evidence surface drifted",
    )

    for source in baseline.get("repositorySourceBindings", []):
        path = root / str(source.get("path", ""))
        _require(path.is_file(), f"Bound access/comms source is missing: {source.get('path')}")
        _require(
            path.stat().st_size == source.get("bytes"),
            f"Bound access/comms source size drifted: {source.get('path')}",
        )
        _require(
            _sha256(path) == source.get("sha256"),
            f"Bound access/comms source hash drifted: {source.get('path')}",
        )

    gate = baseline.get("existingZeroModelGate", {})
    _require(
        gate.get("caseCount") == 9
        and gate.get("faultCaseCount") == 8
        and set(gate.get("coveredFaultClasses", [])) == EXPECTED_FAULT_CLASSES,
        "Access/comms zero-model gate coverage drifted",
    )
    _require(
        gate.get("reuseDecision")
        == "reuse-as-deterministic-structured-semantic-gate-do-not-duplicate",
        "Access/comms zero-model gate reuse decision drifted",
    )
    for field in (
        "freeFormLanguageCorrectnessProved",
        "accessibilityConformanceProved",
        "recipientComprehensionProved",
        "candidateBehaviorOrValueProved",
    ):
        _require(gate.get(field) is False, f"Access/comms gate promoted {field}")
    report = evaluate_calibration(protocol, fixture, root=root)
    _require(
        report.get("outcome") == "valid-zero-model-calibration"
        and report.get("caseCount") == 9
        and report.get("faultCaseCount") == 8
        and report.get("allCasesPassed") is True,
        "Existing access/comms zero-model gate no longer passes",
    )

    documents = baseline.get("officialDocumentsObservation", {})
    _require(
        documents.get("id")
        == "official.openai-primary-runtime-documents-26.730.11710"
        and documents.get("owner") == "OpenAI"
        and documents.get("version") == "26.730.11710",
        "Official Documents candidate identity drifted",
    )
    _require(
        _records(documents.get("fileRecords", [])) == EXPECTED_DOCUMENT_FILES,
        "Official Documents source record drifted",
    )
    _require(
        documents.get("fullWcagEngineClaimedBySource") is False
        and documents.get("semanticTranslationOrTerminologyLockSupplied") is False
        and documents.get("recipientComprehensionSupplied") is False
        and documents.get("currentTaskGoogleDriveBoundaryAuthorized") is False
        and documents.get("instructionDeliveryOrBehaviorProved") is False,
        "Official Documents boundary was promoted",
    )

    near_match = baseline.get("excludedInstalledNearMatch", {})
    _require(
        near_match.get("id") == "external.edit-article-current-cc-switch-projection"
        and _records(near_match.get("fileRecords", []))
        == {
            "SKILL.md": (
                735,
                "3d6f8a603aeef1c6527e203e1a092725605ffe58d9084af8f3043b31ee4144d3",
            )
        }
        and near_match.get("removalAuthorizedByThisBaseline") is False,
        "Installed edit-article exclusion drifted",
    )

    discoveries = baseline.get("targetedExternalDiscovery", [])
    _require(
        {item.get("id") for item in discoveries} == EXPECTED_EXTERNAL_IDS,
        "Access/comms targeted discovery set drifted",
    )
    azure = next(
        item
        for item in discoveries
        if item.get("id") == "external.microsoft-azure-ai-translation-text-py"
    )
    _require(
        azure.get("observedHead") == "4a2873faffc1b101a33a0b59c24713d4ed78142f"
        and azure.get("sourceBlobSha") == "e8ed670c9d5e23a5a08bee0684c7ea18f64fa809"
        and azure.get("sourceBytes") == 10880
        and azure.get("installedOrExecuted") is False
        and azure.get("semanticFidelityAccessibilityOrRecipientValueProved") is False,
        "Azure translation discovery boundary drifted",
    )

    routes = baseline.get("orderedRepresentativeRoute", [])
    _require(
        [item.get("id") for item in routes]
        == [
            "route.source-and-terminology-lock",
            "route.native-semantic-adaptation",
            "route.existing-zero-model-semantic-gate",
            "route.conditional-official-documents-carrier",
            "route.human-review-and-release-control",
        ]
        and {item.get("id") for item in routes} == EXPECTED_ROUTE_IDS,
        "Access/comms ordered representative route drifted",
    )
    decision = baseline.get("comparisonDecision", {})
    _require(
        decision.get("representativeRouteSufficientForNextEvidenceGate") is True,
        "Access/comms representative-route decision drifted",
    )
    for field in (
        "widerCandidateNameDiscoveryNeededNow",
        "externalCapabilityInstallationNeededNow",
        "candidateOrServiceExecutionNeededNow",
        "newZeroModelFixtureNeededNow",
        "selfAuthoredSkillNeededNow",
        "skillOrHardStandardExtractionNeededNow",
    ):
        _require(decision.get(field) is False, f"Access/comms baseline expanded scope: {field}")
    _require(
        decision.get("residualGapState")
        == "behavior-accessibility-and-recipient-evidence-gap-not-capability-name-gap",
        "Access/comms residual-gap classification drifted",
    )

    neutrality = baseline.get("neutralityAndHumanAuthority", {})
    _require(
        neutrality.get("projectNeutralityChanged") is False,
        "Stable project neutrality was misrepresented as a change",
    )
    _require(
        neutrality.get("sourceIntentOwner") == "message-owner"
        and neutrality.get("legallyConsequentialReleaseOwner")
        == "authorized-human-or-accountable-organization",
        "Access/comms human authority drifted",
    )
    authority = baseline.get("authorityBoundary", {})
    _require(
        isinstance(authority, dict)
        and authority
        and all(value is False for value in authority.values()),
        "Access/comms baseline expanded authority",
    )
    claims = baseline.get("claimLimits", {})
    _require(
        isinstance(claims, dict)
        and claims
        and all(value is False for value in claims.values()),
        "Access/comms baseline promoted a prohibited claim",
    )

    acceptances = {
        item.get("id"): item for item in program_map.get("acceptanceCriteria", [])
    }
    _require(len(acceptances) == 61, "Program acceptance count changed")
    for acceptance_id in EXPECTED_ACCEPTANCE_IDS:
        _require(acceptance_id in acceptances, f"Acceptance is missing: {acceptance_id}")
        _require(
            EVIDENCE_ID in acceptances[acceptance_id].get("evidenceIds", []),
            f"Access/comms evidence is not linked to {acceptance_id}",
        )
    evidence = {item.get("id"): item for item in program_map.get("evidence", [])}
    _require(EVIDENCE_ID in evidence, "Access/comms program evidence record is missing")
    _require(
        set(evidence[EVIDENCE_ID].get("supports", [])) == EXPECTED_ACCEPTANCE_IDS,
        "Access/comms program-evidence support set drifted",
    )

    initiatives = {item.get("id"): item for item in program_plan.get("currentInitiatives", [])}
    survey = initiatives.get("initiative.capability-survey-gap-proof")
    coverage = initiatives.get("initiative.human-ai-collaboration-coverage-rebaseline")
    _require(survey is not None and coverage is not None, "Access/comms parent initiative is missing")
    expected_path = (
        "registry/human-ai-collaboration-access-comms-capability-baseline-2026-07-31.json"
    )
    _require(
        survey.get("currentAccessCommsCapabilityBaseline") == expected_path,
        "Capability-survey access/comms baseline pointer is missing",
    )
    _require(
        coverage.get("currentAccessCommsCapabilityBaseline") == expected_path,
        "Coverage-rebaseline access/comms baseline pointer is missing",
    )

    document = (
        root
        / "docs/strategy/HUMAN-AI-COLLABORATION-ACCESS-COMMS-CAPABILITY-BASELINE-2026-07-31.md"
    ).read_text(encoding="utf-8")
    normalized = " ".join(document.split())
    for phrase in (
        "Project neutrality has not changed",
        "ordered composition rather than one universal Skill",
        "reused, not duplicated",
        "not a full WCAG engine",
        "Improved fluency is not semantic fidelity",
        "Explicit non-authorizations",
    ):
        _require(phrase in normalized, f"Access/comms strategy document missing: {phrase}")


def main() -> int:
    validate_baseline()
    print("Human-AI access/comms capability baseline validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
