import copy
import json
from pathlib import Path
import unittest

from scripts.evaluate_process_fidelity_multihop_injection_poc import (
    evaluate_protocol,
    validate_protocol,
)


ROOT = Path(__file__).resolve().parent.parent
FIXTURE = (
    ROOT
    / "tests"
    / "fixtures"
    / "process-fidelity-multihop-injection-poc-2026-07-26.json"
)


class ProcessFidelityMultihopInjectionPocTests(unittest.TestCase):
    def setUp(self) -> None:
        self.protocol = json.loads(FIXTURE.read_text(encoding="utf-8"))

    def test_current_protocol_is_valid_and_falsifiable(self) -> None:
        report = evaluate_protocol(self.protocol)
        self.assertEqual([], validate_protocol(self.protocol, report))
        self.assertEqual(
            {
                "control-preserved": "control-preserved",
                "injected-loss-detected-and-restored": (
                    "loss-detected-source-restored"
                ),
                "injected-loss-undetected-and-amplified": (
                    "hard-fail-undetected-amplification"
                ),
                "opaque-compression-edge": "opaque-stop",
            },
            {
                case["id"]: case["outcome"]
                for case in report["caseResults"]
            },
        )

    def test_detected_case_exposes_loss_latency_and_recovery(self) -> None:
        report = evaluate_protocol(self.protocol)
        result = next(
            item
            for item in report["caseResults"]
            if item["id"] == "injected-loss-detected-and-restored"
        )
        self.assertEqual(1, result["detectionLatencyHops"])
        self.assertEqual(1.0, result["amplificationFactor"])
        self.assertEqual(4, result["recoveryDistanceHops"])
        self.assertEqual(1.0, result["rollbackSuccessRate"])
        self.assertGreater(result["maxWeightedOmissionScore"], 0.0)
        self.assertGreater(result["maxAuthorityDriftCount"], 0)

    def test_undetected_case_records_downstream_amplification(self) -> None:
        report = evaluate_protocol(self.protocol)
        result = next(
            item
            for item in report["caseResults"]
            if item["id"] == "injected-loss-undetected-and-amplified"
        )
        self.assertGreater(result["amplificationFactor"], 1.0)
        self.assertIsNone(result["detectionLatencyHops"])
        self.assertIsNone(result["rollbackSuccessRate"])
        self.assertIn(
            "downstream amplification above the preregistered bound",
            result["stopConditionsTriggered"],
        )

    def test_removing_detection_cannot_preserve_recovered_outcome(self) -> None:
        mutated = copy.deepcopy(self.protocol)
        case = next(
            item
            for item in mutated["cases"]
            if item["id"] == "injected-loss-detected-and-restored"
        )
        for hop in case["hops"]:
            hop["detectedLossIds"] = []
        report = evaluate_protocol(mutated)
        self.assertIn("fail-expected-outcome-mismatch", validate_protocol(mutated, report))

    def test_recovery_from_wrong_anchor_fails_closed(self) -> None:
        mutated = copy.deepcopy(self.protocol)
        case = next(
            item
            for item in mutated["cases"]
            if item["id"] == "injected-loss-detected-and-restored"
        )
        case["hops"][-1]["recoveryFromHopId"] = "compression"
        report = evaluate_protocol(mutated)
        self.assertIn("fail-source-backed-recovery", validate_protocol(mutated, report))

    def test_fabricated_recovery_provenance_fails_closed(self) -> None:
        mutated = copy.deepcopy(self.protocol)
        case = next(
            item
            for item in mutated["cases"]
            if item["id"] == "injected-loss-detected-and-restored"
        )
        case["hops"][-1]["provenanceIds"].append("fabricated-source")
        report = evaluate_protocol(mutated)
        result = next(
            item
            for item in report["caseResults"]
            if item["id"] == case["id"]
        )
        self.assertFalse(result["sourceBackedRecoveryValid"])
        self.assertEqual("hard-fail-process-fidelity", result["outcome"])
        self.assertIn(
            "fail-source-backed-recovery",
            validate_protocol(mutated, report),
        )

    def test_bogus_detection_marker_is_not_accepted(self) -> None:
        mutated = copy.deepcopy(self.protocol)
        case = next(
            item
            for item in mutated["cases"]
            if item["id"] == "injected-loss-detected-and-restored"
        )
        case["hops"][2]["detectedLossIds"] = ["bogus-unrelated-marker"]
        report = evaluate_protocol(mutated)
        result = next(
            item
            for item in report["caseResults"]
            if item["id"] == case["id"]
        )
        self.assertEqual("hard-fail-invalid-detection-marker", result["outcome"])
        self.assertIn(
            "fail-detection-evidence",
            validate_protocol(mutated, report),
        )

    def test_undetected_loss_without_amplification_is_labeled_exactly(self) -> None:
        mutated = copy.deepcopy(self.protocol)
        case = next(
            item
            for item in mutated["cases"]
            if item["id"] == "injected-loss-undetected-and-amplified"
        )
        for hop in case["hops"][2:]:
            hop["assumptionIds"] = ["commit-authorized"]
        report = evaluate_protocol(mutated)
        result = next(
            item
            for item in report["caseResults"]
            if item["id"] == case["id"]
        )
        self.assertEqual("hard-fail-undetected-loss", result["outcome"])
        self.assertEqual(1.0, result["amplificationFactor"])
        self.assertIn(
            "fail-expected-outcome-mismatch",
            validate_protocol(mutated, report),
        )

    def test_late_detection_maps_to_preregistered_stop_condition(self) -> None:
        mutated = copy.deepcopy(self.protocol)
        case = next(
            item
            for item in mutated["cases"]
            if item["id"] == "injected-loss-detected-and-restored"
        )
        case["hops"][2]["detectedLossIds"] = []
        report = evaluate_protocol(mutated)
        result = next(
            item
            for item in report["caseResults"]
            if item["id"] == case["id"]
        )
        self.assertEqual("hard-fail-process-fidelity", result["outcome"])
        self.assertIn(
            "material delta detection latency above the preregistered bound",
            result["stopConditionsTriggered"],
        )

    def test_missing_required_recovery_maps_to_stop_condition(self) -> None:
        mutated = copy.deepcopy(self.protocol)
        case = next(
            item
            for item in mutated["cases"]
            if item["id"] == "injected-loss-detected-and-restored"
        )
        case["hops"].pop()
        report = evaluate_protocol(mutated)
        result = next(
            item
            for item in report["caseResults"]
            if item["id"] == case["id"]
        )
        self.assertEqual("hard-fail-process-fidelity", result["outcome"])
        self.assertIn(
            "required source-backed recovery absent",
            result["stopConditionsTriggered"],
        )

    def test_changed_value_is_not_mislabeled_as_omission(self) -> None:
        mutated = copy.deepcopy(self.protocol)
        case = next(
            item
            for item in mutated["cases"]
            if item["id"] == "control-preserved"
        )
        case["hops"][-1]["values"]["non-goal"] = (
            "large-scale implementation is allowed"
        )
        report = evaluate_protocol(mutated)
        result = next(
            item
            for item in report["caseResults"]
            if item["id"] == case["id"]
        )
        final_hop = result["hopResults"][-1]
        self.assertEqual(0.0, final_hop["weightedOmissionScore"])
        self.assertEqual(["non-goal"], final_hop["changedInvariantIds"])

    def test_opaque_metrics_remain_unknown(self) -> None:
        report = evaluate_protocol(self.protocol)
        result = next(
            item
            for item in report["caseResults"]
            if item["id"] == "opaque-compression-edge"
        )
        self.assertIsNone(result["amplificationFactor"])
        self.assertIsNone(result["rollbackSuccessRate"])

    def test_claim_boundary_cannot_be_promoted(self) -> None:
        mutated = copy.deepcopy(self.protocol)
        mutated["claimBoundary"]["liveAgentBehaviorProved"] = True
        report = evaluate_protocol(mutated)
        self.assertIn("hard-fail-claim-promotion", validate_protocol(mutated, report))

    def test_stop_conditions_are_part_of_the_machine_contract(self) -> None:
        mutated = copy.deepcopy(self.protocol)
        mutated["stopConditions"] = ["opaque material edge"]
        report = evaluate_protocol(mutated)
        self.assertIn(
            "fail-stop-condition-contract",
            validate_protocol(mutated, report),
        )

    def test_transformation_edges_are_part_of_the_machine_contract(self) -> None:
        mutated = copy.deepcopy(self.protocol)
        mutated["scenarioBinding"]["transformationEdges"] = []
        report = evaluate_protocol(mutated)
        self.assertIn(
            "fail-edge-contract",
            validate_protocol(mutated, report),
        )

    def test_unknown_downstream_assumption_fails_closed(self) -> None:
        mutated = copy.deepcopy(self.protocol)
        case = next(
            item
            for item in mutated["cases"]
            if item["id"] == "control-preserved"
        )
        case["hops"][-1]["assumptionIds"] = ["unregistered-assumption"]
        report = evaluate_protocol(mutated)
        result = next(
            item
            for item in report["caseResults"]
            if item["id"] == "control-preserved"
        )
        self.assertEqual("hard-fail-undetected-loss", result["outcome"])
        self.assertIn(
            "fail-expected-outcome-mismatch",
            validate_protocol(mutated, report),
        )


if __name__ == "__main__":
    unittest.main()
