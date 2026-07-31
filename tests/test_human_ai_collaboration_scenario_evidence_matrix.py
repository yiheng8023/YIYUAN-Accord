from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from scripts.validate_human_ai_collaboration_scenario_evidence_matrix import (
    MATRIX_PATH,
    REBASELINE_PATH,
    validate_matrix,
)


ROOT = Path(__file__).resolve().parent.parent


def load(path: str) -> dict:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


class HumanAiCollaborationScenarioEvidenceMatrixTests(unittest.TestCase):
    def setUp(self) -> None:
        self.document = load(MATRIX_PATH)
        self.rebaseline = load(REBASELINE_PATH)
        self.program = load("registry/curation-program-plan.json")
        self.acceptance = load("registry/program-acceptance-map.json")

    def validate(
        self,
        *,
        document: dict | None = None,
        program: dict | None = None,
        acceptance: dict | None = None,
    ) -> None:
        validate_matrix(
            document or self.document,
            self.rebaseline,
            program or self.program,
            acceptance or self.acceptance,
            root=ROOT,
        )

    def test_current_matrix_is_valid(self) -> None:
        self.validate()

    def test_rejects_planned_scenario_as_live_evidence(self) -> None:
        document = copy.deepcopy(self.document)
        document["scenarios"][0]["evidenceState"] = "verified-live"
        with self.assertRaisesRegex(RuntimeError, "evidence was overclaimed"):
            self.validate(document=document)

    def test_rejects_synthetic_incident_as_live_domain_evidence(self) -> None:
        document = copy.deepcopy(self.document)
        scenario = next(
            item
            for item in document["scenarios"]
            if item["id"] == "SE-OPS-INCIDENT-01"
        )
        scenario["evidenceState"] = "verified-live-domain"
        with self.assertRaisesRegex(RuntimeError, "overclaimed or drifted"):
            self.validate(document=document)

    def test_rejects_synthetic_implementation_as_live_domain_evidence(self) -> None:
        document = copy.deepcopy(self.document)
        scenario = next(
            item
            for item in document["scenarios"]
            if item["id"] == "SE-IMPLEMENT-REVIEW-01"
        )
        scenario["evidenceState"] = "verified-live-domain"
        with self.assertRaisesRegex(RuntimeError, "Implementation scenario evidence"):
            self.validate(document=document)

    def test_rejects_missing_tdd_noncomparative_governance_protocol(self) -> None:
        document = copy.deepcopy(self.document)
        scenario = next(
            item
            for item in document["scenarios"]
            if item["id"] == "SE-IMPLEMENT-REVIEW-01"
        )
        scenario.pop("nextProtocolNoncomparativeDiagnostic")
        with self.assertRaisesRegex(RuntimeError, "Implementation scenario evidence"):
            self.validate(document=document)

    def test_rejects_missing_tdd_exact_candidate_admission_gap_audit(self) -> None:
        document = copy.deepcopy(self.document)
        scenario = next(
            item
            for item in document["scenarios"]
            if item["id"] == "SE-IMPLEMENT-REVIEW-01"
        )
        scenario.pop("nextProtocolExactCandidateAdmissionGapAuditEvidence")
        with self.assertRaisesRegex(RuntimeError, "Implementation scenario evidence"):
            self.validate(document=document)

    def test_rejects_missing_tdd_dispatch_identity_ledger_poc(self) -> None:
        document = copy.deepcopy(self.document)
        scenario = next(
            item
            for item in document["scenarios"]
            if item["id"] == "SE-IMPLEMENT-REVIEW-01"
        )
        scenario.pop("nextProtocolDispatchIdentityLedgerPocEvidence")
        with self.assertRaisesRegex(RuntimeError, "Implementation scenario evidence"):
            self.validate(document=document)

    def test_rejects_missing_tdd_dispatch_authorization_adapter_poc(self) -> None:
        document = copy.deepcopy(self.document)
        scenario = next(
            item
            for item in document["scenarios"]
            if item["id"] == "SE-IMPLEMENT-REVIEW-01"
        )
        scenario.pop("nextProtocolDispatchAuthorizationAdapterPocEvidence")
        with self.assertRaisesRegex(RuntimeError, "Implementation scenario evidence"):
            self.validate(document=document)

    def test_rejects_missing_tdd_runner_preflight_poc(self) -> None:
        document = copy.deepcopy(self.document)
        scenario = next(
            item
            for item in document["scenarios"]
            if item["id"] == "SE-IMPLEMENT-REVIEW-01"
        )
        scenario.pop("nextProtocolRunnerPreflightPocEvidence")
        with self.assertRaisesRegex(RuntimeError, "Implementation scenario evidence"):
            self.validate(document=document)

    def test_rejects_live_ledger_authority_promotion(self) -> None:
        document = copy.deepcopy(self.document)
        scenario = next(
            item
            for item in document["scenarios"]
            if item["id"] == "SE-IMPLEMENT-REVIEW-01"
        )
        scenario["remainingEvidenceGap"] = scenario[
            "remainingEvidenceGap"
        ].replace(
            "no live ledger authority is configured",
            "a live ledger authority is configured",
        )
        with self.assertRaisesRegex(RuntimeError, "Implementation scenario evidence"):
            self.validate(document=document)

    def test_rejects_live_materialization_freshness_promotion(self) -> None:
        document = copy.deepcopy(self.document)
        scenario = next(
            item
            for item in document["scenarios"]
            if item["id"] == "SE-IMPLEMENT-REVIEW-01"
        )
        scenario["remainingEvidenceGap"] = scenario[
            "remainingEvidenceGap"
        ].replace(
            "live source-snapshot-to-factory materialization freshness",
            "factory materialization freshness is proved",
        )
        with self.assertRaisesRegex(RuntimeError, "Implementation scenario evidence"):
            self.validate(document=document)

    def test_rejects_missing_process_dispatch_ledger_index(self) -> None:
        document = copy.deepcopy(self.document)
        scenario = next(
            item
            for item in document["scenarios"]
            if item["id"] == "GEN-RESEARCH-01"
        )
        scenario.pop("chainedTransformDispatchLedgerContract")
        with self.assertRaisesRegex(RuntimeError, "Research scenario evidence"):
            self.validate(document=document)

    def test_rejects_missing_cumulative_loss_accounting_index(self) -> None:
        document = copy.deepcopy(self.document)
        document["crossCuttingRisks"][0].pop(
            "cumulativeLossAccountingEvidence"
        )
        with self.assertRaisesRegex(
            RuntimeError,
            "calibration evidence binding",
        ):
            self.validate(document=document)

    def test_rejects_missing_human_boundary_process_gap(self) -> None:
        document = copy.deepcopy(self.document)
        scenario = next(
            item
            for item in document["scenarios"]
            if item["id"] == "GEN-RESEARCH-01"
        )
        scenario["remainingEvidenceGap"] = scenario[
            "remainingEvidenceGap"
        ].replace(
            "human-to-source or terminal-to-human accountable edge",
            "human boundary proved",
        )
        with self.assertRaisesRegex(RuntimeError, "Research scenario evidence"):
            self.validate(document=document)

    def test_rejects_whole_domain_claim(self) -> None:
        document = copy.deepcopy(self.document)
        document["decision"]["wholeHumanAiCoverageClaimed"] = True
        with self.assertRaisesRegex(RuntimeError, "wholeHumanAiCoverageClaimed"):
            self.validate(document=document)

    def test_rejects_lifecycle_completeness_from_sampling(self) -> None:
        document = copy.deepcopy(self.document)
        document["coverageSemantics"][
            "allLifecycleSlicesSampledMeansSoftwareLifecycleCovered"
        ] = True
        with self.assertRaisesRegex(RuntimeError, "allLifecycleSlicesSampled"):
            self.validate(document=document)

    def test_rejects_synthetic_lifecycle_as_live_domain_evidence(self) -> None:
        document = copy.deepcopy(self.document)
        document["coverageProjection"]["softwareLifecycleEvidenceGradeCounts"][
            "liveDomain"
        ] = 8
        with self.assertRaisesRegex(RuntimeError, "evidence-grade counts"):
            self.validate(document=document)

    def test_rejects_duplicate_lifecycle_grade_slice(self) -> None:
        document = copy.deepcopy(self.document)
        grade = next(
            item
            for item in document["coverageProjection"][
                "softwareLifecycleEvidenceGrades"
            ]
            if item["grade"]
            == "bounded-synthetic-agent-no-live-domain"
        )
        grade["sliceIds"].append(grade["sliceIds"][0])
        with self.assertRaisesRegex(
            RuntimeError,
            "evidence-grade partition",
        ):
            self.validate(document=document)

    def test_rejects_missing_lifecycle_slice(self) -> None:
        document = copy.deepcopy(self.document)
        scenario = next(
            item for item in document["scenarios"] if item["id"] == "SE-MGMT-PRACTICE-01"
        )
        scenario["softwareLifecycleSlices"] = []
        with self.assertRaisesRegex(RuntimeError, "general/software lifecycle boundary"):
            self.validate(document=document)

    def test_rejects_ai_dependent_hard_requirement(self) -> None:
        document = copy.deepcopy(self.document)
        document["hardRequirements"][0]["validWithoutAi"] = False
        with self.assertRaisesRegex(RuntimeError, "AI-dependent"):
            self.validate(document=document)

    def test_rejects_missing_human_control(self) -> None:
        document = copy.deepcopy(self.document)
        document["scenarios"][0]["hostClassIds"].remove("host.human-only-control")
        with self.assertRaisesRegex(RuntimeError, "host comparison drifted"):
            self.validate(document=document)

    def test_rejects_repository_authoring_justification(self) -> None:
        document = copy.deepcopy(self.document)
        document["decision"]["repositoryAuthoringJustified"] = True
        with self.assertRaisesRegex(RuntimeError, "repositoryAuthoringJustified"):
            self.validate(document=document)

    def test_rejects_calibration_write_authority(self) -> None:
        document = copy.deepcopy(self.document)
        document["authorityBoundary"]["calibrationWriteAuthorized"] = True
        with self.assertRaisesRegex(RuntimeError, "calibrationWriteAuthorized"):
            self.validate(document=document)

    def test_rejects_process_fidelity_cross_cut_removal(self) -> None:
        document = copy.deepcopy(self.document)
        document["crossCuttingRisks"] = []
        with self.assertRaisesRegex(RuntimeError, "process-fidelity"):
            self.validate(document=document)

    def test_rejects_process_fidelity_evidence_overclaim(self) -> None:
        document = copy.deepcopy(self.document)
        document["crossCuttingRisks"][0]["evidenceState"] = "verified-lossless"
        with self.assertRaisesRegex(RuntimeError, "Process-fidelity evidence"):
            self.validate(document=document)

    def test_rejects_end_to_end_fidelity_decision_overclaim(self) -> None:
        document = copy.deepcopy(self.document)
        document["decision"]["endToEndProcessFidelityClaimed"] = True
        with self.assertRaisesRegex(
            RuntimeError, "endToEndProcessFidelityClaimed"
        ):
            self.validate(document=document)

    def test_rejects_acceptance_promotion(self) -> None:
        acceptance = copy.deepcopy(self.acceptance)
        criterion = next(
            item
            for item in acceptance["acceptanceCriteria"]
            if item["id"] == "acceptance.software-engineering-lifecycle-specialization"
        )
        criterion["assessment"] = "verified"
        with self.assertRaisesRegex(RuntimeError, "acceptance state drifted"):
            self.validate(acceptance=acceptance)

    def test_rejects_ai_era_revalidation_evidence_projection_removal(self) -> None:
        acceptance = copy.deepcopy(self.acceptance)
        criterion = next(
            item
            for item in acceptance["acceptanceCriteria"]
            if item["id"] == "acceptance.software-engineering-lifecycle-specialization"
        )
        criterion["evidenceIds"].remove(
            "evidence.ai-era-classical-software-engineering-principles-"
            "revalidation-2026-07-31"
        )
        with self.assertRaisesRegex(RuntimeError, "evidence mapping drifted"):
            self.validate(acceptance=acceptance)

    def test_rejects_source_snapshot_evidence_projection_removal(self) -> None:
        acceptance = copy.deepcopy(self.acceptance)
        criterion = next(
            item
            for item in acceptance["acceptanceCriteria"]
            if item["id"] == "acceptance.software-engineering-lifecycle-specialization"
        )
        criterion["evidenceIds"].remove(
            "evidence.multidimensional-software-engineering-source-snapshot-"
            "2026-07-31"
        )
        with self.assertRaisesRegex(RuntimeError, "evidence mapping drifted"):
            self.validate(acceptance=acceptance)

    def test_rejects_semantic_authority_continuity_evidence_removal(self) -> None:
        acceptance = copy.deepcopy(self.acceptance)
        criterion = next(
            item
            for item in acceptance["acceptanceCriteria"]
            if item["id"] == "acceptance.end-to-end-process-fidelity"
        )
        criterion["evidenceIds"].remove(
            "evidence.human-ai-collaboration-semantic-authority-"
            "continuity-protocol-2026-07-28"
        )
        with self.assertRaisesRegex(RuntimeError, "evidence mapping drifted"):
            self.validate(acceptance=acceptance)

    def test_rejects_current_matt_exposure_refresh_evidence_removal(self) -> None:
        acceptance = copy.deepcopy(self.acceptance)
        criterion = next(
            item
            for item in acceptance["acceptanceCriteria"]
            if item["id"] == "acceptance.end-to-end-process-fidelity"
        )
        criterion["evidenceIds"].remove(
            "evidence.human-ai-collaboration-semantic-authority-"
            "current-matt-no-model-exposure-refresh-2026-07-31"
        )
        with self.assertRaisesRegex(RuntimeError, "evidence mapping drifted"):
            self.validate(acceptance=acceptance)

    def test_rejects_native_local_exposure_evidence_removal(self) -> None:
        acceptance = copy.deepcopy(self.acceptance)
        criterion = next(
            item
            for item in acceptance["acceptanceCriteria"]
            if item["id"] == "acceptance.end-to-end-process-fidelity"
        )
        criterion["evidenceIds"].remove(
            "evidence.human-ai-collaboration-semantic-authority-native-local-"
            "no-model-exposure-and-oracle-2026-08-01"
        )
        with self.assertRaisesRegex(RuntimeError, "evidence mapping drifted"):
            self.validate(acceptance=acceptance)


if __name__ == "__main__":
    unittest.main()
