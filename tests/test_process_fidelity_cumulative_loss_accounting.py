from __future__ import annotations

import copy
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from scripts.evaluate_process_fidelity_cumulative_loss_accounting import (
    build_cumulative_loss_ledger,
    evaluate_capture_with_cumulative_loss,
)
from scripts.run_process_fidelity_chained_transform_trial import (
    run_zero_model_sequence,
)


ROOT = Path(__file__).resolve().parent.parent
FIXTURE_PATH = ROOT / (
    "tests/fixtures/process-fidelity-chained-transform-sequential-adapter-"
    "faults-2026-07-27.json"
)
PROTOCOL_PATH = ROOT / (
    "registry/human-ai-collaboration-process-fidelity-chained-transform-"
    "trial-protocol-2026-07-27.json"
)


class ProcessFidelityCumulativeLossAccountingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        fixture = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
        cls.cases = {
            item["id"]: item for item in fixture["validCases"]
        }
        cls.protocol = json.loads(
            PROTOCOL_PATH.read_text(encoding="utf-8")
        )

    def build(self, case_id: str):
        case = copy.deepcopy(self.cases[case_id])
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

    def test_injected_loss_is_not_double_counted_or_erased(self) -> None:
        capture, root = self.build(
            "injected-detected-and-gated-recovery"
        )
        report = evaluate_capture_with_cumulative_loss(
            capture,
            capture_root=root,
            root=ROOT,
        )
        process = report["candidateTrace"]["processLedger"]
        self.assertTrue(process["processAcceptancePass"])
        ledger = process["cumulativeLoss"]
        self.assertEqual(6, ledger["cumulativeUniqueLossWeight"])
        self.assertEqual(6, ledger["peakActiveLossWeight"])
        self.assertIsNone(ledger["budgetExceededAtHop"])
        self.assertTrue(ledger["budgetEvaluated"])
        self.assertTrue(ledger["advisoryOnly"])
        self.assertFalse(ledger["changesProcessAcceptancePass"])
        hops = {item["stageId"]: item for item in ledger["hops"]}
        expected = [
            "invariant-omitted:authority",
            "provenance-missing:authority",
        ]
        self.assertEqual(
            expected,
            hops["edge-controlled-mutation"]["newLossIds"],
        )
        self.assertEqual(
            expected,
            hops["hop-2-routing"]["carriedLossIds"],
        )
        self.assertEqual(
            expected,
            hops["hop-3-acceptance-and-recovery"][
                "recoveredLossIds"
            ],
        )
        self.assertEqual(
            6,
            hops["hop-3-acceptance-and-recovery"][
                "cumulativeUniqueLossWeight"
            ],
        )

    def test_control_accounting_remains_zero(self) -> None:
        capture, root = self.build("control-sequence")
        report = evaluate_capture_with_cumulative_loss(
            capture,
            capture_root=root,
            root=ROOT,
        )
        ledger = report["candidateTrace"]["processLedger"][
            "cumulativeLoss"
        ]
        self.assertEqual(0, ledger["cumulativeUniqueLossWeight"])
        self.assertEqual(0, ledger["peakActiveLossWeight"])
        self.assertIsNone(ledger["budgetExceededAtHop"])
        self.assertTrue(
            all(
                item["activeLossWeight"] == 0
                and not item["activeLossIds"]
                for item in ledger["hops"]
            )
        )

    def test_reintroduced_loss_is_new_but_not_unique_twice(self) -> None:
        stages = [
            {
                "stageId": "s1",
                "activeLossIds": ["invariant-omitted:authority"],
                "weightedDelta": 5,
            },
            {
                "stageId": "s2",
                "activeLossIds": [],
                "weightedDelta": 0,
            },
            {
                "stageId": "s3",
                "activeLossIds": ["invariant-omitted:authority"],
                "weightedDelta": 5,
            },
        ]
        ledger = build_cumulative_loss_ledger(stages, self.protocol)
        self.assertEqual(
            ["invariant-omitted:authority"],
            ledger["hops"][2]["newLossIds"],
        )
        self.assertEqual(
            ["invariant-omitted:authority"],
            ledger["hops"][2]["reintroducedLossIds"],
        )
        self.assertEqual(5, ledger["cumulativeUniqueLossWeight"])
        self.assertFalse(ledger["budgetEvaluated"])
        self.assertIsNone(ledger["budgetMaximum"])
        self.assertIsNone(ledger["budgetExceededAtHop"])

    def test_partition_and_first_budget_breach_are_exact(self) -> None:
        stages = [
            {
                "stageId": "s1",
                "activeLossIds": [
                    "invariant-omitted:authority",
                    "provenance-missing:authority",
                ],
                "weightedDelta": 6,
            },
            {
                "stageId": "s2",
                "activeLossIds": [
                    "provenance-missing:authority",
                    "assumption:unknown-is-fact",
                ],
                "weightedDelta": 5,
            },
        ]
        ledger = build_cumulative_loss_ledger(
            stages,
            self.protocol,
            cumulative_unique_loss_weight_max=6,
        )
        second = ledger["hops"][1]
        self.assertEqual(
            ["assumption:unknown-is-fact"],
            second["newLossIds"],
        )
        self.assertEqual(
            ["provenance-missing:authority"],
            second["carriedLossIds"],
        )
        self.assertEqual(
            ["invariant-omitted:authority"],
            second["recoveredLossIds"],
        )
        self.assertEqual(10, ledger["cumulativeUniqueLossWeight"])
        self.assertEqual(6, ledger["peakActiveLossWeight"])
        self.assertEqual("s2", ledger["budgetExceededAtHop"])

    def test_invalid_loss_shapes_fail_closed(self) -> None:
        cases = [
            [
                {
                    "stageId": "s1",
                    "activeLossIds": ["mystery:authority"],
                    "weightedDelta": 1,
                }
            ],
            [
                {
                    "stageId": "s1",
                    "activeLossIds": [
                        "invariant-omitted:authority",
                        "invariant-omitted:authority",
                    ],
                    "weightedDelta": 10,
                }
            ],
            [
                {
                    "stageId": "s1",
                    "activeLossIds": [
                        "invariant-omitted:authority",
                    ],
                    "weightedDelta": 0,
                }
            ],
        ]
        for stages in cases:
            with self.subTest(stages=stages):
                with self.assertRaises(RuntimeError):
                    build_cumulative_loss_ledger(stages, self.protocol)

    def test_invalid_base_capture_does_not_gain_trusted_ledger(self) -> None:
        capture, root = self.build(
            "injected-detected-and-gated-recovery"
        )
        capture = copy.deepcopy(capture)
        capture["materialEdges"][0]["opaque"] = True
        report = evaluate_capture_with_cumulative_loss(
            capture,
            capture_root=root,
            root=ROOT,
        )
        self.assertIsNone(report["candidateTrace"])
        self.assertIn("opaque-material-edge", report["failureCodes"])


if __name__ == "__main__":
    unittest.main()
