#!/usr/bin/env python3
"""Validate the bounded, solution-neutral collaboration coverage rebaseline."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent

EXPECTED_SOURCE_HEAD = "e060a08f05361cb4cc9a67be050236cdbbde1de5"
EXPECTED_SOURCE_ARTIFACTS = {
    "common/human-ai-collaboration-shortfalls/sources/2026-07-11-human-ai-shortfall-research-refresh.md": (
        62925,
        "FDC5E4EB1AB7CF01752885BC2C9C335F1C301BE407DDBAD697DFCC21E85C6727",
    ),
    "common/human-ai-collaboration-shortfalls/evidence/corrected-evidence-ledger-20260712.md": (
        51097,
        "7CD7FDDA5B386753B9B53807BAD1EDB974E60A94D35FDB2538A4BBD141AA223A",
    ),
    "common/human-ai-collaboration-shortfalls/taxonomy/two-layer-taxonomy-20260712.md": (
        21707,
        "1BAA51C89A4B51D49DF65948166A708312C343EF9950D896884C31E2C059EC90",
    ),
    "common/human-ai-collaboration-shortfalls/mapping/problem-owner-standard-gap-matrix-20260712.md": (
        39489,
        "AA61EB0C022AE47F6091C9FA8D1CC8FDC8141638B9064F5850A225055248F93A",
    ),
    "common/human-ai-collaboration-shortfalls/decisions/codex-m1-intake-audit-20260712.md": (
        22819,
        "89C9A53F71BD49BB532E6F50D6AC08A08372D357787DC478787642F4795D802A",
    ),
    "assets/engineering-research/intake/ai-assisted-engineering-2026-06-18/chatgpt-ai-programming-risk-report.md": (
        50879,
        "BD096EC08655A07148042BF522FD05F0288A7FDBC57740F91801146E4FFEB210",
    ),
    "assets/engineering-research/intake/ai-assisted-engineering-2026-06-18/claude-ai-programming-risk-report.md": (
        7363,
        "D102782BC47418768FAFA8CB4DB076790CF9B91D68FB7F5D530B033C760BE398",
    ),
    "assets/engineering-research/intake/ai-assisted-engineering-2026-06-18/gemini-ai-programming-risk-report.txt": (
        23408,
        "772F1DA7EAC1282F6EEB30C0802268846D4B889EDA8E0A0E32C163A448A98295",
    ),
}
EXPECTED_FINDINGS = {
    "finding.solution-framing-bias",
    "finding.closed-coordinate-coverage",
    "finding.software-risk-not-lifecycle",
}
SUPPLEMENTAL_INTAKE_PATH = (
    "registry/user-supplied-human-ai-sdlc-research-intake-2026-07-24.json"
)
EXPECTED_AXES = {
    "axis.subjects-and-affected-parties",
    "axis.goals-values-and-intent",
    "axis.work-and-collaboration-modes",
    "axis.cognition-competence-and-agency",
    "axis.context-knowledge-state-and-provenance",
    "axis.capability-data-authority-and-action",
    "axis.evidence-assurance-and-accountability",
    "axis.organization-incentives-and-impacts",
    "axis.lifecycle-operations-and-evolution",
}
EXPECTED_LIFECYCLE_SLICES = {
    "strategy-product-discovery-acquisition-and-supply",
    "stakeholder-needs-and-requirements",
    "system-and-software-architecture",
    "detailed-design-and-modeling",
    "implementation-build-and-dependency-management",
    "review-static-quality-and-configuration-control",
    "verification-validation-testing-and-acceptance",
    "security-privacy-safety-and-software-supply-chain",
    "release-delivery-deployment-and-change-management",
    "operations-observability-reliability-and-support",
    "incident-response-recovery-and-learning",
    "maintenance-evolution-refactoring-and-technical-debt",
    "migration-deprecation-retirement-and-disposal",
    "engineering-management-economics-teamwork-and-professional-practice",
}
EXPECTED_CROSS_CUTS = {
    "human-AI division of labor",
    "requirements and acceptance independence",
    "repository and environment truth",
    "tool and dependency authority",
    "weak-Agent and host variation",
    "reviewer competence and accountability",
    "production evidence and rollback",
    "longitudinal maintainability and human learning",
    "end-to-end process fidelity and cumulative transformation loss",
}
EXPECTED_COORDINATE_SETS = {"STM-01..26", "P1..24", "SG-01..12"}
EXPECTED_REVALIDATION_IDS = {
    "acceptance.multi-domain-coverage",
    "acceptance.full-chain-coverage-matrix",
    "acceptance.alternative-comparison",
    "acceptance.residual-gap-proof",
}
EXPECTED_GATES = {
    "gate.solution-neutrality",
    "gate.open-world-coverage",
    "gate.software-lifecycle-specialization",
    "gate.end-to-end-process-fidelity",
    "gate.ai-independent-hard-standard",
    "gate.narrow-evidence-retention",
}
EXPECTED_ACCEPTANCE = {
    "acceptance.solution-neutral-collaboration-rebaseline": "partial",
    "acceptance.software-engineering-lifecycle-specialization": "partial",
    "acceptance.end-to-end-process-fidelity": "partial",
    "acceptance.ai-independent-hard-standard-boundary": "partial",
}
EVIDENCE_ID = "evidence.human-ai-collaboration-coverage-rebaseline"
EVIDENCE_PATH = "registry/human-ai-collaboration-coverage-rebaseline-2026-07-24.json"
MATRIX_EVIDENCE_ID = (
    "evidence.human-ai-collaboration-scenario-evidence-matrix-batch-01"
)
RELEASE_CHANGE_PROTOCOL_EVIDENCE_ID = (
    "evidence.human-ai-collaboration-release-change-zero-model-"
    "protocol-2026-07-27"
)
RELEASE_CHANGE_CURRENT_CC_CODEX_PREFLIGHT_EVIDENCE_ID = (
    "evidence.human-ai-collaboration-release-change-current-cc-codex-"
    "no-model-preflight-2026-07-30"
)
TDD_READINESS_EVIDENCE_ID = (
    "evidence.human-ai-collaboration-tdd-current-execution-readiness-"
    "reconciliation-2026-07-27"
)
TDD_SUCCESSOR_CONTRACT_EVIDENCE_ID = (
    "evidence.human-ai-collaboration-tdd-noncomparative-dispatch-"
    "successor-contract-v2-2026-07-27"
)
ACCESS_COMMS_CALIBRATION_EVIDENCE_ID = (
    "evidence.human-ai-collaboration-access-comms-zero-model-calibration-"
    "2026-07-27"
)
ORG_DECISION_CALIBRATION_EVIDENCE_ID = (
    "evidence.human-ai-collaboration-org-decision-zero-model-calibration-"
    "2026-07-31"
)
ENGINEERING_MANAGEMENT_CALIBRATION_EVIDENCE_ID = (
    "evidence.human-ai-collaboration-engineering-management-zero-model-"
    "calibration-2026-07-31"
)
AI_ERA_ENGINEERING_REVALIDATION_EVIDENCE_ID = (
    "evidence.ai-era-classical-software-engineering-principles-"
    "revalidation-2026-07-31"
)
MULTIDIMENSIONAL_ENGINEERING_EVALUATION_EVIDENCE_ID = (
    "evidence.multidimensional-software-engineering-evaluation-contract-"
    "2026-07-31"
)
MULTIDIMENSIONAL_ENGINEERING_SOURCE_SNAPSHOT_EVIDENCE_ID = (
    "evidence.multidimensional-software-engineering-source-snapshot-"
    "2026-07-31"
)
LEARNING_CAPABILITY_BASELINE_EVIDENCE_ID = (
    "evidence.human-ai-collaboration-learning-capability-baseline-2026-07-31"
)
CREATIVE_CAPABILITY_BASELINE_EVIDENCE_ID = (
    "evidence.human-ai-collaboration-creative-capability-baseline-2026-07-31"
)
ACCESS_COMMS_CAPABILITY_BASELINE_EVIDENCE_ID = (
    "evidence.human-ai-collaboration-access-comms-capability-baseline-2026-07-31"
)
SEMANTIC_AUTHORITY_CONTINUITY_EVIDENCE_ID = (
    "evidence.human-ai-collaboration-semantic-authority-"
    "continuity-protocol-2026-07-28"
)
CURRENT_MATT_EXPOSURE_REFRESH_EVIDENCE_ID = (
    "evidence.human-ai-collaboration-semantic-authority-"
    "current-matt-no-model-exposure-refresh-2026-07-31"
)
NATIVE_LOCAL_EXPOSURE_ORACLE_EVIDENCE_ID = (
    "evidence.human-ai-collaboration-semantic-authority-native-local-"
    "no-model-exposure-and-oracle-2026-08-01"
)
SEMANTIC_EXECUTION_PLAN_PREFLIGHT_EVIDENCE_ID = (
    "evidence.human-ai-collaboration-semantic-authority-execution-plan-"
    "preflight-2026-08-01"
)
DOCUMENTATION_PATH = (
    "docs/strategy/HUMAN-AI-COLLABORATION-COVERAGE-REBASELINE-2026-07-24.md"
)


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def _index(items: Any, field: str, label: str) -> dict[str, dict[str, Any]]:
    _require(isinstance(items, list), f"{label} must be a list")
    result: dict[str, dict[str, Any]] = {}
    for item in items:
        _require(isinstance(item, dict), f"{label} entries must be objects")
        value = item.get(field)
        _require(isinstance(value, str) and value, f"{label} entries need {field}")
        _require(value not in result, f"{label} contains duplicate {field}: {value}")
        result[value] = item
    return result


def _nonempty_text(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def validate_rebaseline(
    document: dict[str, Any],
    program_document: dict[str, Any],
    acceptance_document: dict[str, Any],
    *,
    root: Path = ROOT,
) -> None:
    """Fail closed on authority promotion, closed-world claims, or map drift."""
    _require(document.get("schema") == 1, "Rebaseline schema must be 1")
    _require(
        document.get("id") == "human-ai-collaboration-coverage-rebaseline-2026-07-24",
        "Rebaseline identity drifted",
    )
    _require(
        document.get("status") == "active-rebaseline-candidate-no-standard-promotion",
        "Rebaseline status promoted or drifted",
    )

    authority = document.get("authorityBoundary")
    _require(isinstance(authority, dict), "Rebaseline authority boundary is missing")
    _require(
        authority.get("owningRepository") == "agent-autonomy-harness",
        "Rebaseline owning repository drifted",
    )
    _require(
        authority.get("calibrationState") == "paused-read-only-source",
        "Paused CALIBRATION boundary drifted",
    )
    for key in (
        "calibrationWriteAuthorized",
        "assetsAdmissionAuthorized",
        "hardStandardPromotionAuthorized",
        "skillOrHookMutationAuthorizedByThisRecord",
        "runtimeMutationAuthorizedByThisRecord",
        "gitCommitOrPushAuthorizedByThisRecord",
    ):
        _require(authority.get(key) is False, f"Rebaseline authority promoted: {key}")

    snapshot = document.get("calibrationSourceSnapshot")
    _require(isinstance(snapshot, dict), "CALIBRATION source snapshot is missing")
    _require(snapshot.get("repository") == "C:/Projects/YIYUAN-CALIBRATION", "CALIBRATION source path drifted")
    _require(snapshot.get("head") == EXPECTED_SOURCE_HEAD, "CALIBRATION source HEAD drifted")
    _require(snapshot.get("observedDirtyFiles") == ["GOVERNANCE.md"], "CALIBRATION dirty-file observation drifted")
    artifacts = _index(snapshot.get("artifacts"), "path", "CALIBRATION source artifacts")
    _require(set(artifacts) == set(EXPECTED_SOURCE_ARTIFACTS), "CALIBRATION source artifact set drifted")
    for path, (size, digest) in EXPECTED_SOURCE_ARTIFACTS.items():
        _require(artifacts[path].get("bytes") == size, f"CALIBRATION source byte count drifted: {path}")
        _require(artifacts[path].get("sha256") == digest, f"CALIBRATION source hash drifted: {path}")
        _require(_nonempty_text(artifacts[path].get("role")), f"CALIBRATION source role missing: {path}")

    references = _index(document.get("externalReferenceBaseline"), "id", "External references")
    _require(len(references) == 6, "External reference baseline must retain six bounded references")
    for item in references.values():
        _require(_nonempty_text(item.get("url")), "External reference URL is missing")
        _require(_nonempty_text(item.get("scope")), "External reference scope is missing")
        _require(_nonempty_text(item.get("boundary")), "External reference boundary is missing")

    supplemental = _index(
        document.get("supplementalResearchInputs"),
        "path",
        "Supplemental research inputs",
    )
    _require(
        set(supplemental) == {SUPPLEMENTAL_INTAKE_PATH},
        "Supplemental research input set drifted",
    )
    _require(
        supplemental[SUPPLEMENTAL_INTAKE_PATH].get("status")
        == "retained-research-input-not-accepted-evidence",
        "Supplemental research input was promoted",
    )
    for field in ("role", "boundary"):
        _require(
            _nonempty_text(supplemental[SUPPLEMENTAL_INTAKE_PATH].get(field)),
            f"Supplemental research input {field} is missing",
        )

    findings = _index(document.get("structuralFindings"), "id", "Structural findings")
    _require(set(findings) == EXPECTED_FINDINGS, "Structural finding set drifted")
    for item in findings.values():
        _require(item.get("state") == "confirmed-bounded", "Structural finding lost its bounded state")
        _require(_nonempty_text(item.get("finding")), "Structural finding text is missing")
        _require(_nonempty_text(item.get("nonClaim")), "Structural finding non-claim is missing")

    coverage = document.get("coverageModel")
    _require(isinstance(coverage, dict), "Coverage model is missing")
    _require(
        coverage.get("completenessModel") == "open-world-versioned-no-absolute-completeness",
        "Coverage model became closed-world or absolute",
    )
    _require(
        coverage.get("motherFrameworkRole")
        == "Human-AI collaboration is the total domain. Software engineering is one priority specialization, not the total domain.",
        "Mother-framework and software-specialization roles drifted",
    )
    axes = _index(coverage.get("motherFrameworkAxes"), "id", "Mother-framework axes")
    _require(set(axes) == EXPECTED_AXES, "Mother-framework axis set drifted")
    for item in axes.values():
        _require(_nonempty_text(item.get("question")), "Mother-framework axis question is missing")
        _require(
            isinstance(item.get("examples"), list) and bool(item["examples"]),
            "Mother-framework axis examples are missing",
        )

    cross_risks = _index(
        coverage.get("crossCuttingRisks"), "id", "Coverage cross-cutting risks"
    )
    _require(
        set(cross_risks) == {"risk.end-to-end-process-fidelity-loss"},
        "Process-fidelity cross-cutting risk drifted",
    )
    process_risk = cross_risks["risk.end-to-end-process-fidelity-loss"]
    _require(
        "transformation-edge risk" in str(process_risk.get("role")),
        "Process-fidelity risk role drifted",
    )
    _require(
        isinstance(process_risk.get("requiredModel"), list)
        and len(process_risk["requiredModel"]) >= 7,
        "Process-fidelity required model is incomplete",
    )
    _require(
        "do not prove lossless" in str(process_risk.get("claimLimit")),
        "Process-fidelity claim limit is missing",
    )

    specialization = coverage.get("softwareEngineeringSpecialization")
    _require(isinstance(specialization, dict), "Software-engineering specialization is missing")
    _require(
        specialization.get("status") == "priority-specialization-baseline-not-complete",
        "Software-engineering specialization was promoted to completeness",
    )
    _require(
        set(specialization.get("lifecycleSlices", [])) == EXPECTED_LIFECYCLE_SLICES
        and len(specialization["lifecycleSlices"]) == len(EXPECTED_LIFECYCLE_SLICES),
        "Software-engineering lifecycle slices drifted",
    )
    _require(
        set(specialization.get("requiredCrossCuts", [])) == EXPECTED_CROSS_CUTS
        and len(specialization["requiredCrossCuts"]) == len(EXPECTED_CROSS_CUTS),
        "Software-engineering cross-cuts drifted",
    )

    historical = document.get("historicalCoordinateBoundary")
    _require(isinstance(historical, dict), "Historical coordinate boundary is missing")
    _require(set(historical.get("sets", [])) == EXPECTED_COORDINATE_SETS, "Historical coordinate sets drifted")
    _require(
        set(historical.get("notAcceptedAs", []))
        == {
            "exhaustive-human-ai-collaboration-ontology",
            "software-engineering-lifecycle-completeness-proof",
            "hard-standard",
            "Skill-or-Hook-architecture-proof",
        },
        "Historical coordinate non-claim boundary drifted",
    )

    revalidations = _index(document.get("acceptanceRevalidation"), "acceptanceId", "Acceptance revalidation")
    _require(set(revalidations) == EXPECTED_REVALIDATION_IDS, "Acceptance revalidation set drifted")
    for item in revalidations.values():
        _require(_nonempty_text(item.get("preservedClaim")), "Preserved narrow claim is missing")
        _require(_nonempty_text(item.get("revalidationRequiredFor")), "Revalidation boundary is missing")

    gates = _index(document.get("gates"), "id", "Rebaseline gates")
    _require(set(gates) == EXPECTED_GATES, "Rebaseline gate set drifted")
    for item in gates.values():
        _require(_nonempty_text(item.get("passCondition")), "Rebaseline pass condition is missing")
        _require(_nonempty_text(item.get("falsifier")), "Rebaseline falsifier is missing")

    decision = document.get("decision")
    _require(isinstance(decision, dict), "Rebaseline decision is missing")
    for key in ("existingNarrowEvidenceRetained", "historicalCoordinateLineageRetained"):
        _require(decision.get(key) is True, f"Valid narrow evidence was discarded: {key}")
    for key in (
        "selfAuthoredSkillsDefineProblemSpace",
        "softwareEngineeringDefinesWholeDomain",
        "wholeHumanAiCoverageClaimed",
        "softwareLifecycleCoverageClaimed",
        "endToEndProcessFidelityCoverageClaimed",
        "hardStandardPromotionAuthorized",
        "calibrationMutationAuthorized",
        "skillsOrHooksMutationAuthorized",
    ):
        _require(decision.get(key) is False, f"Rebaseline claim or authority promoted: {key}")
    _require(_nonempty_text(decision.get("nextBoundedResult")), "Next bounded result is missing")

    _require(document.get("documentation") == DOCUMENTATION_PATH, "Rebaseline documentation path drifted")
    documentation = root / DOCUMENTATION_PATH
    _require(documentation.is_file(), "Rebaseline documentation is missing")
    documentation_text = documentation.read_text(encoding="utf-8")
    documentation_normalized = " ".join(documentation_text.split())
    for phrase in (
        "open-world",
        "Software engineering is a priority specialization",
        "does not modify that repository",
        "scenario-to-evidence matrix",
        "Cross-cutting process fidelity and loss",
    ):
        _require(
            phrase in documentation_normalized,
            f"Rebaseline documentation boundary missing: {phrase}",
        )

    objectives = _index(program_document.get("strategicObjectives"), "id", "Program objectives")
    objective = objectives.get("objective.solution-neutral-collaboration-coverage")
    _require(objective is not None, "Solution-neutral program objective is missing")
    _require(set(objective.get("acceptanceIds", [])) == set(EXPECTED_ACCEPTANCE), "Program objective acceptance mapping drifted")
    sequence_gates = _index(program_document.get("sequenceGates"), "id", "Program sequence gates")
    _require(
        "gate.solution-neutral-coverage-before-generalization" in sequence_gates,
        "Solution-neutral generalization gate is missing",
    )
    initiatives = _index(program_document.get("currentInitiatives"), "id", "Program initiatives")
    initiative = initiatives.get("initiative.human-ai-collaboration-coverage-rebaseline")
    _require(initiative is not None and initiative.get("status") == "active", "Rebaseline initiative is not active")
    _require(initiative.get("currentEvidence") == EVIDENCE_PATH, "Rebaseline initiative evidence path drifted")
    blocked = set(initiative.get("blockedActions", []))
    _require(
        {
            "YIYUAN-CALIBRATION mutation",
            "YIYUAN-ASSETS admission",
            "hard-standard promotion",
            "Skill or Hook mutation from coverage metadata",
            "runtime mutation",
            "whole-domain closure claim",
            "remote push",
        }
        <= blocked,
        "Rebaseline initiative lost a blocked action",
    )

    mapped_objectives = _index(acceptance_document.get("objectives"), "id", "Acceptance objectives")
    mapped = mapped_objectives.get("objective.solution-neutral-collaboration-coverage")
    _require(mapped is not None and set(mapped.get("acceptanceIds", [])) == set(EXPECTED_ACCEPTANCE), "Acceptance objective mapping drifted")
    criteria = _index(acceptance_document.get("acceptanceCriteria"), "id", "Acceptance criteria")
    verifications = _index(acceptance_document.get("verifications"), "id", "Acceptance verifications")
    evidence = _index(acceptance_document.get("evidence"), "id", "Acceptance evidence")
    for acceptance_id, assessment in EXPECTED_ACCEPTANCE.items():
        item = criteria.get(acceptance_id)
        _require(item is not None, f"Acceptance criterion missing: {acceptance_id}")
        _require(item.get("assessment") == assessment, f"Acceptance assessment overclaimed or drifted: {acceptance_id}")
        verification_ids = item.get("verificationIds", [])
        _require(len(verification_ids) == 1 and verification_ids[0] in verifications, f"Acceptance verification missing: {acceptance_id}")
        expected_evidence_ids = [EVIDENCE_ID, MATRIX_EVIDENCE_ID]
        if acceptance_id == "acceptance.solution-neutral-collaboration-rebaseline":
            expected_evidence_ids += [
                LEARNING_CAPABILITY_BASELINE_EVIDENCE_ID,
                CREATIVE_CAPABILITY_BASELINE_EVIDENCE_ID,
                ACCESS_COMMS_CAPABILITY_BASELINE_EVIDENCE_ID,
            ]
        if (
            acceptance_id
            == "acceptance.software-engineering-lifecycle-specialization"
        ):
            expected_evidence_ids += [
                RELEASE_CHANGE_PROTOCOL_EVIDENCE_ID,
                RELEASE_CHANGE_CURRENT_CC_CODEX_PREFLIGHT_EVIDENCE_ID,
                TDD_READINESS_EVIDENCE_ID,
                TDD_SUCCESSOR_CONTRACT_EVIDENCE_ID,
                AI_ERA_ENGINEERING_REVALIDATION_EVIDENCE_ID,
                MULTIDIMENSIONAL_ENGINEERING_EVALUATION_EVIDENCE_ID,
                MULTIDIMENSIONAL_ENGINEERING_SOURCE_SNAPSHOT_EVIDENCE_ID,
                ENGINEERING_MANAGEMENT_CALIBRATION_EVIDENCE_ID,
            ]
        if acceptance_id == "acceptance.ai-independent-hard-standard-boundary":
            expected_evidence_ids += [
                AI_ERA_ENGINEERING_REVALIDATION_EVIDENCE_ID,
                MULTIDIMENSIONAL_ENGINEERING_EVALUATION_EVIDENCE_ID,
                MULTIDIMENSIONAL_ENGINEERING_SOURCE_SNAPSHOT_EVIDENCE_ID,
            ]
        if acceptance_id == "acceptance.end-to-end-process-fidelity":
            expected_evidence_ids += [
                "evidence.process-fidelity-multihop-injection-poc-2026-07-26",
                (
                    "evidence.human-ai-collaboration-process-fidelity-v1-"
                    "calibration-abort-2026-07-27"
                ),
                (
                    "evidence.human-ai-collaboration-process-fidelity-v2-"
                    "protocol-2026-07-27"
                ),
                (
                    "evidence.human-ai-collaboration-process-fidelity-v2-"
                    "source-backed-smoke-2026-07-27"
                ),
                (
                    "evidence.human-ai-collaboration-process-fidelity-"
                    "chained-trace-calibration-2026-07-27"
                ),
                (
                    "evidence.human-ai-collaboration-process-fidelity-"
                    "chained-transform-protocol-2026-07-27"
                ),
                (
                    "evidence.human-ai-collaboration-process-fidelity-"
                    "chained-transform-packet-preflight-2026-07-27"
                ),
                (
                    "evidence.human-ai-collaboration-process-fidelity-"
                    "chained-transform-adapter-evaluator-poc-2026-07-27"
                ),
                (
                    "evidence.human-ai-collaboration-process-fidelity-"
                    "cumulative-loss-accounting-poc-2026-07-27"
                ),
                (
                    "evidence.human-ai-collaboration-software-lifecycle-"
                    "thin-slice-zero-model-calibration-2026-07-27"
                ),
                (
                    "evidence.human-ai-collaboration-process-fidelity-"
                    "chained-transform-dispatch-gate-contract-2026-07-27"
                ),
                (
                    "evidence.human-ai-collaboration-process-fidelity-"
                    "chained-transform-dispatch-ledger-contract-2026-07-27"
                ),
                (
                    "evidence.human-ai-collaboration-process-fidelity-"
                    "chained-transform-v2-amendment-2026-07-27"
                ),
                (
                    "evidence.human-ai-collaboration-process-fidelity-"
                    "raw-event-trace-eligibility-2026-07-27"
                ),
                (
                    "evidence.context-handoff-receiver-delta-ledger-"
                    "2026-07-27"
                ),
                ACCESS_COMMS_CALIBRATION_EVIDENCE_ID,
                ORG_DECISION_CALIBRATION_EVIDENCE_ID,
                ENGINEERING_MANAGEMENT_CALIBRATION_EVIDENCE_ID,
                (
                    "evidence.human-ai-collaboration-semantic-authority-"
                    "layer-reconciliation-2026-07-28"
                ),
                SEMANTIC_AUTHORITY_CONTINUITY_EVIDENCE_ID,
                CURRENT_MATT_EXPOSURE_REFRESH_EVIDENCE_ID,
                NATIVE_LOCAL_EXPOSURE_ORACLE_EVIDENCE_ID,
                SEMANTIC_EXECUTION_PLAN_PREFLIGHT_EVIDENCE_ID,
                MULTIDIMENSIONAL_ENGINEERING_EVALUATION_EVIDENCE_ID,
                MULTIDIMENSIONAL_ENGINEERING_SOURCE_SNAPSHOT_EVIDENCE_ID,
            ]
        _require(
            item.get("evidenceIds") == expected_evidence_ids,
            f"Acceptance evidence mapping drifted: {acceptance_id}",
        )
    evidence_item = evidence.get(EVIDENCE_ID)
    _require(evidence_item is not None, "Rebaseline acceptance evidence is missing")
    _require(evidence_item.get("path") == EVIDENCE_PATH, "Rebaseline acceptance evidence path drifted")
    _require(set(evidence_item.get("supports", [])) == set(EXPECTED_ACCEPTANCE), "Rebaseline evidence support set drifted")


def _load(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        value = json.load(handle)
    _require(isinstance(value, dict), f"Expected JSON object: {path}")
    return value


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args()
    root = args.root.resolve()
    validate_rebaseline(
        _load(root / EVIDENCE_PATH),
        _load(root / "registry/curation-program-plan.json"),
        _load(root / "registry/program-acceptance-map.json"),
        root=root,
    )
    print("human-AI collaboration coverage rebaseline: valid")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
