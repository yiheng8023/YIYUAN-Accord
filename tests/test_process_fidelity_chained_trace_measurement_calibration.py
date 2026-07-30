import copy
import json
from pathlib import Path
import unittest

from scripts.calibrate_process_fidelity_chained_trace import (
    FIXTURE_PATH,
    evaluate_contract,
    validate_contract,
)
from scripts.validate_process_fidelity_chained_trace_measurement_calibration import (
    EVIDENCE_PATH,
    validate_evidence,
)


ROOT = Path(__file__).resolve().parent.parent


class ProcessFidelityChainedTraceMeasurementCalibrationTests(
    unittest.TestCase
):
    def setUp(self) -> None:
        self.contract = json.loads(
            (ROOT / FIXTURE_PATH).read_text(encoding="utf-8")
        )
        self.evidence = json.loads(
            (ROOT / EVIDENCE_PATH).read_text(encoding="utf-8")
        )

    def test_current_contract_and_evidence_are_valid(self) -> None:
        report = validate_contract(self.contract)
        self.assertTrue(report["decision"]["measurementCalibrationPassed"])
        validate_evidence(self.evidence, root=ROOT)

    def test_predecessor_output_input_mismatch_fails_closed(self) -> None:
        report = evaluate_contract(self.contract)
        case = next(
            item
            for item in report["caseResults"]
            if item["id"] == "predecessor-input-linkage-mismatch"
        )
        self.assertEqual(
            "hard-fail-predecessor-input-linkage",
            case["outcome"],
        )
        self.assertEqual(
            ["decomposition-to-routing"],
            case["absoluteLedger"]["predecessorLinkageFailureEdgeIds"],
        )

    def test_local_loss_propagation_and_amplification_are_measured(self) -> None:
        report = evaluate_contract(self.contract)
        case = next(
            item
            for item in report["caseResults"]
            if item["id"] == "local-loss-propagated-and-amplified"
        )
        self.assertEqual(2, case["processLedger"]["downstreamAffectedHopCount"])
        self.assertEqual(2.8, case["processLedger"]["amplificationFactor"])

    def test_terminal_restoration_cannot_erase_intermediate_loss(self) -> None:
        report = evaluate_contract(self.contract)
        case = next(
            item
            for item in report["caseResults"]
            if item["id"]
            == "terminal-restoration-does-not-erase-intermediate-loss"
        )
        self.assertTrue(
            case["absoluteLedger"]["terminalMatchesSourceAnchor"]
        )
        self.assertTrue(case["processLedger"]["intermediateLossPresent"])
        self.assertFalse(case["processAcceptancePass"])

    def test_opaque_material_edge_metrics_remain_unknown(self) -> None:
        report = evaluate_contract(self.contract)
        case = next(
            item
            for item in report["caseResults"]
            if item["id"] == "opaque-material-edge"
        )
        self.assertIsNone(case["processLedger"]["amplificationFactor"])
        self.assertIsNone(case["processLedger"]["rollbackSuccessRate"])
        self.assertTrue(case["processLedger"]["opaqueMetricsRemainUnknown"])

    def test_acknowledgement_cannot_be_promoted_to_semantic_snapshot(self) -> None:
        mutated = copy.deepcopy(self.contract)
        mutated["estimandBoundary"][
            "acknowledgementProvesSemanticRetention"
        ] = True
        with self.assertRaisesRegex(RuntimeError, "estimand"):
            validate_contract(mutated)

    def test_live_cohort_cannot_be_authorized_by_calibration(self) -> None:
        mutated = copy.deepcopy(self.evidence)
        mutated["scopeBoundary"]["formalLiveCohortAuthorized"] = True
        with self.assertRaisesRegex(RuntimeError, "scope"):
            validate_evidence(mutated, root=ROOT)

    def test_evaluator_hash_is_enforced(self) -> None:
        mutated = copy.deepcopy(self.evidence)
        mutated["calibrator"]["reusedMetricEvaluatorFileSha256"] = "0" * 64
        with self.assertRaisesRegex(RuntimeError, "file hash"):
            validate_evidence(mutated, root=ROOT)


if __name__ == "__main__":
    unittest.main()
