from __future__ import annotations

import copy
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from scripts.evaluate_process_fidelity_chained_transform_trace import (
    evaluate_capture,
)
from scripts.run_process_fidelity_chained_transform_trial import (
    run_zero_model_sequence,
)


ROOT = Path(__file__).resolve().parent.parent
FIXTURE_PATH = ROOT / (
    "tests/fixtures/process-fidelity-chained-transform-sequential-adapter-"
    "faults-2026-07-27.json"
)


class ProcessFidelityChainedTransformTraceEvaluatorTests(
    unittest.TestCase
):
    @classmethod
    def setUpClass(cls) -> None:
        cls.fixture = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
        cls.cases = {
            item["id"]: item for item in cls.fixture["validCases"]
        }

    def build(
        self,
        case_id: str,
        *,
        mutate_outputs=None,
    ):
        case = copy.deepcopy(self.cases[case_id])
        if mutate_outputs is not None:
            mutate_outputs(case["scriptedHopOutputs"])
        temporary = TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        output_root = Path(temporary.name) / "capture"
        capture = run_zero_model_sequence(
            root=ROOT,
            output_root=output_root,
            cell=case["cell"],
            scripted_hop_outputs=case["scriptedHopOutputs"],
        )
        return capture, output_root

    def test_valid_mechanisms_remain_calibration_only(self) -> None:
        for case_id in (
            "control-sequence",
            "injected-detected-and-gated-recovery",
        ):
            with self.subTest(case_id=case_id):
                capture, root = self.build(case_id)
                report = evaluate_capture(
                    capture,
                    capture_root=root,
                    root=ROOT,
                )
                expected = self.cases[case_id]["expectedOutcome"]
                self.assertEqual(expected, report["outcome"])
                self.assertEqual("calibration-only", report["status"])
                self.assertFalse(report["formalLiveEvidenceEligible"])
                self.assertEqual(0, report["formalProcessCohortCount"])
                trace = report["candidateTrace"]
                self.assertEqual(
                    "calibration-only",
                    trace["eligibility"]["status"],
                )
                self.assertFalse(
                    trace["eligibility"]["formalLiveEvidenceEligible"]
                )

    def test_injected_trace_separates_absolute_and_process_ledgers(self) -> None:
        capture, root = self.build(
            "injected-detected-and-gated-recovery"
        )
        trace = evaluate_capture(
            capture,
            capture_root=root,
            root=ROOT,
        )["candidateTrace"]
        self.assertTrue(
            trace["absoluteLedger"]["terminalMatchesSourceAnchor"]
        )
        self.assertTrue(trace["processLedger"]["intermediateLossPresent"])
        self.assertTrue(trace["processLedger"]["processAcceptancePass"])
        self.assertEqual(
            "edge-controlled-mutation",
            trace["processLedger"]["firstDeltaStageId"],
        )
        self.assertEqual(
            "hop-2-routing",
            trace["processLedger"]["firstDetectionStageId"],
        )
        self.assertEqual(
            1,
            trace["processLedger"]["detectionLatencyMaterialHops"],
        )
        self.assertEqual(
            6,
            trace["injectionLedger"]["observedWeightedDelta"],
        )

    def test_agent_supplied_metrics_are_ignored(self) -> None:
        def mutate(outputs):
            outputs["hop-2-routing"]["hopMetrics"] = {
                "weightedDelta": 0,
                "processAcceptancePass": True,
            }

        capture, root = self.build(
            "injected-detected-and-gated-recovery",
            mutate_outputs=mutate,
        )
        trace = evaluate_capture(
            capture,
            capture_root=root,
            root=ROOT,
        )["candidateTrace"]
        hop_2 = next(
            item
            for item in trace["hopMetrics"]
            if item["stageId"] == "hop-2-routing"
        )
        self.assertEqual(6, hop_2["weightedDelta"])
        self.assertTrue(hop_2["detectionEvidenceValid"])

    def test_registered_fault_corpus_fails_closed(self) -> None:
        for fault in self.fixture["faultCases"]:
            with self.subTest(fault=fault["id"]):
                if (
                    fault["operation"]
                    == "remove-one-hop-2-detected-loss-id-before-run"
                ):
                    def mutate(outputs):
                        outputs["hop-2-routing"]["detectedLossIds"].pop()

                    capture, root = self.build(
                        fault["baseCaseId"],
                        mutate_outputs=mutate,
                    )
                else:
                    capture, root = self.build(fault["baseCaseId"])
                    capture = copy.deepcopy(capture)
                    if (
                        fault["operation"]
                        == "replace-first-edge-predecessor-hash"
                    ):
                        capture["materialEdges"][0][
                            "predecessorOutputArtifactSha256"
                        ] = "0" * 64
                    elif (
                        fault["operation"]
                        == "duplicate-first-edge-id-at-second-position"
                    ):
                        capture["materialEdges"][1]["edgeId"] = (
                            capture["materialEdges"][0]["edgeId"]
                        )
                    elif fault["operation"] == "mark-first-edge-opaque":
                        capture["materialEdges"][0]["opaque"] = True
                    elif (
                        fault["operation"]
                        == "replace-source-index-hash"
                    ):
                        capture["rawArtifactIndex"][0]["rawSha256"] = (
                            "0" * 64
                        )
                    elif (
                        fault["operation"] == "add-caller-hop-metrics"
                    ):
                        capture["hopMetrics"] = [
                            {"processAcceptancePass": True}
                        ]
                    else:  # pragma: no cover - fixture contract
                        self.fail(f"Unknown fault operation: {fault}")
                report = evaluate_capture(
                    capture,
                    capture_root=root,
                    root=ROOT,
                )
                self.assertIn(
                    fault["expectedFailureCode"],
                    report["failureCodes"],
                )
                self.assertIsNone(report["candidateTrace"])
                self.assertFalse(report["formalLiveEvidenceEligible"])


if __name__ == "__main__":
    unittest.main()
