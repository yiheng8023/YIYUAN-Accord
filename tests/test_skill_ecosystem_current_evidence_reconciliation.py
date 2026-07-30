from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import unittest

from scripts.validate_skill_ecosystem_current_evidence_reconciliation import (
    EVIDENCE_PATH,
    PROGRAM_EVIDENCE_ID,
    PROGRAM_PATH,
    ROOT,
    validate_reconciliation,
)


class SkillEcosystemCurrentEvidenceReconciliationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.document = json.loads(
            (ROOT / EVIDENCE_PATH).read_text(encoding="utf-8")
        )
        cls.program = json.loads(
            (ROOT / PROGRAM_PATH).read_text(encoding="utf-8")
        )

    def test_current_reconciliation_passes(self) -> None:
        validate_reconciliation(deepcopy(self.document), root=ROOT)

    def test_rejects_historical_611_behavior_relabeled_as_620(self) -> None:
        document = deepcopy(self.document)
        document["evidenceCells"][4]["candidateVersion"] = "6.2.0"
        document["evidenceCells"][4]["currentBehavioralEvidence"] = True
        with self.assertRaises(RuntimeError):
            validate_reconciliation(document, root=ROOT)

    def test_rejects_selected_exposure_as_loader_invocation(self) -> None:
        document = deepcopy(self.document)
        document["evidenceCells"][0]["treatmentFidelity"][
            "independentLoaderEventProved"
        ] = True
        with self.assertRaises(RuntimeError):
            validate_reconciliation(document, root=ROOT)

    def test_rejects_repeated_hard_oracle_failure_as_value(self) -> None:
        document = deepcopy(self.document)
        document["sharedCellClaimBoundary"]["valueProved"] = True
        with self.assertRaises(RuntimeError):
            validate_reconciliation(document, root=ROOT)

    def test_rejects_static_lineage_as_behavioral_equivalence(self) -> None:
        document = deepcopy(self.document)
        document["baselineReconciliation"]["historicalMatrix"][
            "contentLineageProvesBehavioralEquivalence"
        ] = True
        with self.assertRaises(RuntimeError):
            validate_reconciliation(document, root=ROOT)

    def test_rejects_missing_self_authored_arm_as_residual_gap(self) -> None:
        document = deepcopy(self.document)
        document["missingArmBoundary"]["missingArmProvesResidualGap"] = True
        with self.assertRaises(RuntimeError):
            validate_reconciliation(document, root=ROOT)

    def test_rejects_cc_rows_as_loaded_or_invoked_count(self) -> None:
        document = deepcopy(self.document)
        document["baselineReconciliation"]["currentCcLayeredCounts"][
            "loadedOrInvokedCount"
        ] = 251
        document["baselineReconciliation"]["currentCcLayeredCounts"][
            "databaseRowsProveLoadedOrInvokedCount"
        ] = True
        with self.assertRaises(RuntimeError):
            validate_reconciliation(document, root=ROOT)

    def test_rejects_current_source_pin_as_execution_admission(self) -> None:
        document = deepcopy(self.document)
        document["baselineReconciliation"]["currentSuperpowersSourceBaseline"][
            "executionAdmissionSatisfied"
        ] = True
        with self.assertRaises(RuntimeError):
            validate_reconciliation(document, root=ROOT)

    def test_rejects_stale_historical_next_gate_as_current(self) -> None:
        document = deepcopy(self.document)
        document["currentNextGate"]["requiredBeforeAnotherComparativeRun"] = [
            "obtain-verifiable-spark-low-and-task-scoped-skill-exposure"
        ]
        with self.assertRaises(RuntimeError):
            validate_reconciliation(document, root=ROOT)

    def test_rejects_source_digest_drift_in_record(self) -> None:
        document = deepcopy(self.document)
        document["sourceBindings"][0]["fileSha256"] = "0" * 64
        with self.assertRaises(RuntimeError):
            validate_reconciliation(document, root=ROOT)

    def test_rejects_missing_source_under_alternate_root(self) -> None:
        with self.assertRaises(RuntimeError):
            validate_reconciliation(
                deepcopy(self.document),
                root=Path("C:/definitely-not-this-repository"),
            )

    def test_rejects_program_evidence_kind_drift(self) -> None:
        program = deepcopy(self.program)
        evidence = next(
            item
            for item in program["evidence"]
            if item["id"] == PROGRAM_EVIDENCE_ID
        )
        evidence["kind"] = "value-proved"
        with self.assertRaisesRegex(RuntimeError, "program projection"):
            validate_reconciliation(
                deepcopy(self.document),
                root=ROOT,
                program=program,
            )

    def test_rejects_extra_acceptance_backlink(self) -> None:
        program = deepcopy(self.program)
        criterion = next(
            item
            for item in program["acceptanceCriteria"]
            if item["id"] == "acceptance.alternative-comparison"
        )
        criterion["evidenceIds"].append(PROGRAM_EVIDENCE_ID)
        with self.assertRaisesRegex(RuntimeError, "acceptance backlink"):
            validate_reconciliation(
                deepcopy(self.document),
                root=ROOT,
                program=program,
            )


if __name__ == "__main__":
    unittest.main()
