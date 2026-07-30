#!/usr/bin/env python3
"""Fail closed on drift in the current self-authored TDD treatment gap audit."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
AUDIT_PATH = (
    "registry/human-ai-collaboration-tdd-current-self-authored-treatment-"
    "gap-audit-2026-07-27.json"
)
DOCUMENTATION_PATH = (
    "docs/strategy/HUMAN-AI-COLLABORATION-TDD-CURRENT-SELF-AUTHORED-"
    "TREATMENT-GAP-AUDIT-2026-07-27.md"
)
COMPARATIVE_PROTOCOL_PATH = (
    "registry/human-ai-collaboration-comparative-protocol-batch-01-"
    "2026-07-24.json"
)
TDD_PROTOCOL_PATH = (
    "registry/human-ai-collaboration-new-feature-tdd-protocol-2026-07-26.json"
)
DIAGNOSTIC_PROTOCOL_PATH = (
    "registry/human-ai-collaboration-tdd-noncomparative-treatment-"
    "diagnostic-protocol-2026-07-26.json"
)
SOURCE_PREFLIGHT_PATH = (
    "registry/human-ai-collaboration-tdd-noncomparative-treatment-"
    "diagnostic-source-governance-preflight-2026-07-26.json"
)
MATT_ADMISSION_PATH = (
    "registry/human-ai-collaboration-tdd-matt-current-diagnostic-only-"
    "admission-decision-2026-07-27.json"
)
SUPERPOWERS_ADMISSION_PATH = (
    "registry/human-ai-collaboration-tdd-superpowers-620-diagnostic-only-"
    "admission-decision-2026-07-27.json"
)
LEDGER_EVIDENCE_PATH = (
    "registry/human-ai-collaboration-tdd-noncomparative-dispatch-"
    "identity-ledger-poc-evidence-2026-07-26.json"
)
RUNNER_EVIDENCE_PATH = (
    "registry/human-ai-collaboration-tdd-noncomparative-runner-"
    "preflight-poc-evidence-2026-07-26.json"
)
SKILLS_PATH = "registry/skills.json"
ADMISSIONS_PATH = "registry/admissions.json"
RELEASE_MANIFEST_PATH = "release-manifest.json"
ADAPTED_TDD_PRIMARY_PATH = "skills/tdd/SKILL.md"

SELF_CHAIN_IDS = {
    "self.intent-contract",
    "self.capability-router",
    "self.closure-contract",
}
CURRENT_TREATMENT_IDS = {
    "matt.current-tdd",
    "superpowers.6.2.0-test-driven-development",
}
DIAGNOSTIC_CANDIDATE_IDS = {
    "tdd.matt.current",
    "tdd.superpowers.6.2.0",
}
EXPECTED_RELEASE_FILES = {
    "skills/tdd/SKILL.md",
    "skills/tdd/deep-modules.md",
    "skills/tdd/interface-design.md",
    "skills/tdd/mocking.md",
    "skills/tdd/refactoring.md",
    "skills/tdd/tests.md",
}
EXPECTED_HARD_GATES = {
    "functional visible and hidden oracle pass",
    "ordered valid RED before first production mutation",
    "Agent-authored tests kill every predeclared realistic mutant",
    "public seam and independent literal expectations",
    "exact allowed-file scope",
    "no dependency, network, Git, config, Plugin, MCP, or external write",
    "final output and evidence make no production, causation, or superiority claim",
}


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def _load(root: Path, path: str) -> dict[str, Any]:
    return json.loads((root / path).read_text(encoding="utf-8"))


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _items_by(
    items: list[dict[str, Any]], key: str
) -> dict[str, dict[str, Any]]:
    return {str(item[key]): item for item in items}


def _find_protocol(
    protocols: list[dict[str, Any]], scenario_id: str
) -> dict[str, Any]:
    for protocol in protocols:
        if protocol.get("scenarioId") == scenario_id:
            return protocol
    raise RuntimeError(f"missing comparative protocol: {scenario_id}")


def validate_audit(
    document: dict[str, Any],
    *,
    root: Path = ROOT,
) -> None:
    _require(document.get("schema") == 1, "audit schema must be 1")
    _require(
        document.get("id")
        == "human-ai-collaboration-tdd-current-self-authored-treatment-"
        "gap-audit-2026-07-27",
        "audit identity drifted",
    )
    _require(
        document.get("status")
        == "verified-no-current-symmetric-self-authored-tdd-treatment-"
        "self-build-need-not-proved",
        "audit status drifted",
    )

    expected_binding_paths = {
        COMPARATIVE_PROTOCOL_PATH,
        TDD_PROTOCOL_PATH,
        DIAGNOSTIC_PROTOCOL_PATH,
        SOURCE_PREFLIGHT_PATH,
        MATT_ADMISSION_PATH,
        SUPERPOWERS_ADMISSION_PATH,
        LEDGER_EVIDENCE_PATH,
        RUNNER_EVIDENCE_PATH,
        SKILLS_PATH,
        ADMISSIONS_PATH,
        RELEASE_MANIFEST_PATH,
        ADAPTED_TDD_PRIMARY_PATH,
    }
    bindings = _items_by(document.get("sourceBindings", []), "path")
    _require(
        set(bindings) == expected_binding_paths,
        "source binding set drifted",
    )
    for path, binding in bindings.items():
        source = root / path
        _require(source.is_file(), f"source binding missing: {path}")
        _require(
            binding.get("bytes") == len(source.read_bytes()),
            f"source binding byte count drifted: {path}",
        )
        _require(
            binding.get("sha256") == _sha256(source),
            f"source binding digest drifted: {path}",
        )

    comparative = _load(root, COMPARATIVE_PROTOCOL_PATH)
    tdd_protocol = _load(root, TDD_PROTOCOL_PATH)
    diagnostic_protocol = _load(root, DIAGNOSTIC_PROTOCOL_PATH)
    source_preflight = _load(root, SOURCE_PREFLIGHT_PATH)
    matt_admission = _load(root, MATT_ADMISSION_PATH)
    superpowers_admission = _load(root, SUPERPOWERS_ADMISSION_PATH)
    ledger = _load(root, LEDGER_EVIDENCE_PATH)
    runner = _load(root, RUNNER_EVIDENCE_PATH)
    skills = _load(root, SKILLS_PATH)
    admissions = _load(root, ADMISSIONS_PATH)
    release_manifest = _load(root, RELEASE_MANIFEST_PATH)

    # Self-authored evidence is a three-part phase-control chain, not one TDD
    # method. This rejects silently promoting process controls into a treatment.
    pins = _items_by(comparative.get("candidatePins", []), "id")
    _require(
        SELF_CHAIN_IDS <= set(pins),
        "self-authored control-chain candidate set drifted",
    )
    _require(
        all(
            pins[candidate_id].get("family")
            == "self-authored-control-chain"
            for candidate_id in SELF_CHAIN_IDS
        ),
        "self-authored control-chain family drifted",
    )
    suitability = {
        item["candidateId"]: item
        for item in comparative.get("suitabilityDecisions", [])
        if item.get("candidateId") in SELF_CHAIN_IDS
        and item.get("scenarioId") == "SE-IMPLEMENT-REVIEW-01"
    }
    _require(
        set(suitability) == SELF_CHAIN_IDS
        and all(
            item.get("decision") == "eligible-only-as-phase-control"
            for item in suitability.values()
        ),
        "self-authored chain phase-control decision drifted",
    )
    implementation_protocol = _find_protocol(
        comparative.get("protocols", []), "SE-IMPLEMENT-REVIEW-01"
    )
    self_arm = _items_by(
        implementation_protocol.get("arms", []), "id"
    ).get("SE-SELF-CHAIN-PHASED")
    _require(
        self_arm is not None
        and self_arm.get("class") == "self-authored-control-chain"
        and set(self_arm.get("candidateIds", [])) == SELF_CHAIN_IDS
        and self_arm.get("primaryAcceptanceArm") is False
        and self_arm.get("requiresRedGreen") is False,
        "self-authored chain implementation-arm boundary drifted",
    )

    # The current TDD protocol has only Matt and Superpowers treatment arms.
    protocol_bindings = {
        item["id"] for item in tdd_protocol.get("sourceBindings", [])
    }
    _require(
        protocol_bindings == CURRENT_TREATMENT_IDS,
        "current TDD candidate source set drifted",
    )
    arms = _items_by(tdd_protocol.get("arms", []), "id")
    selected = {
        item["selectedTreatment"]
        for item in arms.values()
        if item.get("selectedTreatment") is not None
    }
    _require(
        selected == CURRENT_TREATMENT_IDS,
        "current TDD selected-treatment set drifted",
    )
    _require(
        arms.get("SE-TDD-NATIVE-SPARK", {}).get("selectedTreatment")
        is None,
        "native TDD arm was promoted to a treatment",
    )
    _require(
        not any(
            str(item.get("selectedTreatment", "")).startswith("self.")
            for item in arms.values()
        ),
        "self-authored chain was promoted to a current TDD treatment",
    )
    control_plane = tdd_protocol.get("commonControlPlane", {})
    _require(
        control_plane.get(
            "samePromptFixtureOracleAndHardAcceptanceAcrossPrimaryArms"
        )
        is True,
        "common hard-standard control across TDD arms drifted",
    )
    _require(
        set(tdd_protocol.get("acceptance", {}).get("hardGates", []))
        == EXPECTED_HARD_GATES,
        "current TDD hard-gate set drifted",
    )
    tdd_decision = tdd_protocol.get("decisionBoundary", {})
    _require(
        tdd_decision.get("formalTreatmentComparisonBlocked") is True
        and tdd_decision.get("nativeValidComparisonBaselineAvailable")
        is False
        and tdd_decision.get("candidateSpecificTreatmentDeliveryProved")
        is False
        and tdd_decision.get("selfAuthoredGapProved") is False,
        "current TDD decision boundary drifted",
    )

    diagnostic_candidates = {
        item["candidateId"]
        for item in diagnostic_protocol.get("candidates", [])
    }
    _require(
        diagnostic_candidates == DIAGNOSTIC_CANDIDATE_IDS,
        "noncomparative diagnostic candidate set drifted",
    )
    _require(
        not any(candidate.startswith("self.") for candidate in diagnostic_candidates),
        "self-authored candidate entered the diagnostic protocol",
    )

    # The approved local TDD payload is adapted Matt-lineage third-party
    # capability evidence. It is not evidence of a self-authored chain member.
    governance = source_preflight.get("governanceObservation", {})
    _require(
        governance.get("mattRelatedRegistrySkillId") == "skill.curated.tdd"
        and governance.get("mattRelatedRegistryStatus") == "approved"
        and governance.get("mattRelatedAdmissionDisposition") == "approve"
        and governance.get("mattRelatedAdmissionValidated") is True
        and governance.get("mattCurrentProjectionEqualsApprovedReleasePayload")
        is False
        and governance.get("mattSharedLogicalFilesAllDiffer") is True
        and set(
            governance.get("mattApprovedReleaseAdditionalLogicalFiles", [])
        )
        == {"deep-modules.md", "interface-design.md", "refactoring.md"}
        and governance.get("anyExactCandidateExecutionAdmissionSatisfied")
        is False,
        "approved-adapted versus current-Matt identity boundary drifted",
    )
    _require(
        len(governance.get("mattApprovedReleaseFiles", [])) == 6
        and len(governance.get("mattCurrentProjectionLogicalFiles", [])) == 3,
        "approved-adapted versus current-Matt file-shape boundary drifted",
    )

    skill = _items_by(skills.get("skills", []), "id").get(
        "skill.curated.tdd"
    )
    admission = _items_by(admissions.get("admissions", []), "skill").get(
        "skill.curated.tdd"
    )
    _require(
        skill is not None
        and skill.get("status") == "approved"
        and skill.get("source") == "github:mattpocock/skills",
        "approved adapted TDD registry identity drifted",
    )
    _require(
        admission is not None
        and admission.get("source") == "github:mattpocock/skills"
        and admission.get("thirdParty") is True
        and admission.get("disposition") == "approve"
        and admission.get("validated") is True,
        "approved adapted TDD admission boundary drifted",
    )
    release_files = {
        item["path"]: item
        for item in release_manifest.get("files", [])
        if item.get("path", "").startswith("skills/tdd/")
    }
    _require(
        set(release_files) == EXPECTED_RELEASE_FILES,
        "approved adapted TDD release file set drifted",
    )
    for item in governance.get("mattApprovedReleaseFiles", []):
        release = release_files.get(item["path"])
        _require(
            release is not None
            and release.get("size") == item["bytes"]
            and release.get("sha256") == item["sha256"],
            f"approved adapted TDD release identity drifted: {item['path']}",
        )
    _require(
        _sha256(root / ADAPTED_TDD_PRIMARY_PATH)
        == governance.get("mattApprovedReleaseSkillSha256"),
        "approved adapted TDD primary payload drifted",
    )

    # A diagnostic admission and offline runner/ledger PoCs remain
    # infrastructure/admission evidence, never method-treatment evidence.
    _require(
        matt_admission.get("status")
        == "admit-diagnostic-only-current-dispatch-still-blocked"
        and matt_admission.get("candidateIdentity", {}).get("candidateId")
        == "tdd.matt.current"
        and matt_admission.get("candidateIdentity", {}).get("sourceClass")
        == "reviewed-maintained-external-public-github-api"
        and matt_admission.get("decision", {}).get(
            "identityBoundExecutionAdmissionSatisfied"
        )
        is True
        and matt_admission.get("decision", {}).get("currentDispatchEligible")
        is False
        and matt_admission.get("claimBoundary", {}).get(
            "diagnosticAdmissionProvesSelfAuthoredResidualGap"
        )
        is False,
        "Matt diagnostic-only admission boundary drifted",
    )
    _require(
        ledger.get("status")
        == "offline-ledger-construction-state-poc-validated-no-live-transition"
        and ledger.get("decision", {}).get("modulePocValidated") is True
        and ledger.get("decision", {}).get(
            "formalRunnerIntegrationImplemented"
        )
        is False
        and ledger.get("decision", {}).get(
            "currentExactCandidateAdmissionSatisfied"
        )
        is False
        and ledger.get("claimBoundary", {}).get("candidateSkillInvoked")
        is False
        and ledger.get("claimBoundary", {}).get(
            "candidateBodyDeliveryProved"
        )
        is False
        and ledger.get("claimBoundary", {}).get(
            "candidateCausationOrValueProved"
        )
        is False,
        "identity-ledger PoC boundary drifted",
    )
    _require(
        runner.get("status")
        == "offline-immutable-authorization-and-construction-state-poc-"
        "validated-current-documents-rejected-no-live-app-server"
        and runner.get("decision", {}).get("runnerPreflightPocValidated")
        is True
        and runner.get("decision", {}).get("injectedFactoryOnly") is True
        and runner.get("decision", {}).get(
            "formalRunnerIntegrationImplemented"
        )
        is False
        and runner.get("decision", {}).get("liveLedgerAuthorityConfigured")
        is False
        and runner.get("decision", {}).get(
            "currentCandidateDispatchAuthorized"
        )
        is False
        and runner.get("claimBoundary", {}).get("candidateSkillInvoked")
        is False
        and runner.get("claimBoundary", {}).get(
            "candidateBodyDeliveryProved"
        )
        is False,
        "runner-preflight PoC boundary drifted",
    )

    classification = document.get("classification", {})
    hard = classification.get("hardStandards", {})
    _require(
        hard.get("role") == "mandatory-common-control"
        and hard.get("sameAcrossTreatmentArms") is True
        and hard.get("candidateCreditAllowed") is False,
        "audit hard-standard classification drifted",
    )
    upstream = classification.get("upstreamSelfAuthoredOrchestration", {})
    _require(
        upstream.get("role") == "phase-controls-not-tdd-treatment"
        and set(upstream.get("candidateIds", [])) == SELF_CHAIN_IDS
        and upstream.get("singleTddMethod") is False
        and upstream.get("currentTddSelectedTreatment") is False
        and upstream.get("primaryAcceptanceArm") is False,
        "audit upstream-orchestration classification drifted",
    )
    treatments = classification.get("currentTddTreatments", {})
    _require(
        set(treatments.get("selectedTreatmentIds", []))
        == CURRENT_TREATMENT_IDS
        and treatments.get("selfAuthoredSelectedTreatmentIds") == []
        and treatments.get("nativeArmHasNoTreatment") is True
        and treatments.get("formalComparisonBlocked") is True
        and treatments.get("validNativeBaselineAvailable") is False
        and treatments.get("candidateSpecificTreatmentDeliveryProved")
        is False,
        "audit current-treatment classification drifted",
    )
    adapted = classification.get("approvedAdaptedTddPayload", {})
    _require(
        adapted.get("registrySkillId") == "skill.curated.tdd"
        and adapted.get("thirdParty") is True
        and adapted.get("sameAsCurrentMattProjection") is False
        and adapted.get("memberOfSelfAuthoredControlChain") is False
        and adapted.get("currentTddProtocolArmPresent") is False
        and adapted.get("currentTddSelectedTreatment") is False
        and adapted.get("symmetricSelfAuthoredTreatmentCandidate") is False,
        "approved adapted payload was reclassified as self-authored treatment",
    )
    infrastructure = classification.get("runnerAndLedger", {})
    _require(
        infrastructure.get("role")
        == "transport-admission-identity-and-lifecycle-infrastructure-"
        "not-method-treatment"
        and infrastructure.get("formalRunnerIntegrationImplemented") is False
        and infrastructure.get("liveLedgerAuthorityConfigured") is False
        and infrastructure.get("currentCandidateDispatchAuthorized") is False
        and infrastructure.get("candidateSkillInvocationProved") is False
        and infrastructure.get("candidateBodyDeliveryProved") is False
        and infrastructure.get("candidateCausationOrValueProved") is False,
        "runner or ledger was promoted to treatment evidence",
    )

    assessment = document.get("currentCandidateAssessment", {})
    _require(
        matt_admission.get("decision", {}).get(
            "identityBoundExecutionAdmissionSatisfied"
        )
        is True
        and matt_admission.get("decision", {}).get("currentDispatchEligible")
        is False
        and superpowers_admission.get("decision", {}).get(
            "identityBoundExecutionAdmissionSatisfied"
        )
        is True
        and superpowers_admission.get("decision", {}).get(
            "currentDispatchEligible"
        )
        is False,
        "current external candidate admission boundary drifted",
    )
    _require(
        assessment.get("mattCurrent", {}).get(
            "diagnosticOnlyAdmissionPresent"
        )
        is True
        and assessment.get("mattCurrent", {}).get("currentDispatchEligible")
        is False
        and assessment.get("superpowers620", {}).get(
            "diagnosticOnlyAdmissionPresent"
        )
        is True
        and assessment.get("superpowers620", {}).get(
            "currentDispatchEligible"
        )
        is False
        and assessment.get("selfAuthoredChain", {}).get(
            "identityBoundPhaseControlsPresent"
        )
        is True
        and assessment.get("selfAuthoredChain", {}).get(
            "singleTddTreatmentIdentityPresent"
        )
        is False
        and assessment.get("selfAuthoredChain", {}).get(
            "currentProtocolArmPresent"
        )
        is False,
        "self-authored current-candidate assessment drifted",
    )
    decision = document.get("decision", {})
    _require(
        decision.get("currentSymmetricSelfAuthoredTddTreatmentCandidateExists")
        is False
        and decision.get("onlySelfAuthoredUpstreamOrchestrationChainExists")
        is True
        and decision.get("approvedAdaptedThirdPartyTddPayloadExists") is True
        and decision.get(
            "approvedAdaptedPayloadCanBeCountedAsSelfAuthoredChainCandidate"
        )
        is False
        and decision.get("runnerOrLedgerCanBeCountedAsTreatment") is False
        and decision.get("gapClass")
        == "current-experiment-treatment-identity-and-attribution-gap"
        and decision.get("selfAuthoredTddImplementationNecessary") is False
        and decision.get("absenceConstitutesResidualGapProof") is False
        and decision.get("absenceAuthorizesSelfAuthoring") is False,
        "audit decision promoted an unproved self-authored treatment need",
    )

    execution = document.get("executionBoundary", {})
    _require(
        execution.get("repositoryReadOnlyAudit") is True
        and execution.get("modelRequestCount") == 0
        and execution.get("candidateDispatchCount") == 0
        and execution.get("candidateSkillInvocationCount") == 0
        and all(
            execution.get(key) is False
            for key in (
                "installationPerformed",
                "globalConfigurationChanged",
                "ccSwitchChanged",
                "externalAccessUsed",
                "programMapChanged",
                "globalVerifierChanged",
            )
        ),
        "audit execution boundary drifted",
    )
    _require(
        document.get("claimBoundary")
        and all(value is False for value in document["claimBoundary"].values()),
        "audit claim boundary was promoted",
    )
    _require(
        document.get("documentation") == DOCUMENTATION_PATH,
        "audit documentation pointer drifted",
    )
    documentation = (root / DOCUMENTATION_PATH).read_text(encoding="utf-8")
    for phrase in (
        "not a Skill treatment",
        "Hard standards",
        "Upstream orchestration",
        "Runner and ledger",
        "Why the gap does not justify self-authoring",
        "does not add such an arm",
        "experiment-treatment identity and attribution gap",
    ):
        _require(
            phrase in documentation,
            f"audit documentation boundary missing: {phrase}",
        )


def main() -> int:
    validate_audit(_load(ROOT, AUDIT_PATH))
    print(
        "human-ai collaboration current self-authored TDD treatment gap "
        "audit validation passed"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
