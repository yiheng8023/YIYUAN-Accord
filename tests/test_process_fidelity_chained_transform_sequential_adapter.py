from __future__ import annotations

import copy
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from scripts.run_process_fidelity_chained_transform_trial import (
    EDGE_IDS,
    SequenceCaptureError,
    run_zero_model_sequence,
)


ROOT = Path(__file__).resolve().parent.parent
FIXTURE_PATH = ROOT / (
    "tests/fixtures/process-fidelity-chained-transform-sequential-adapter-"
    "faults-2026-07-27.json"
)


class ProcessFidelityChainedTransformSequentialAdapterTests(
    unittest.TestCase
):
    @classmethod
    def setUpClass(cls) -> None:
        cls.fixture = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
        cls.cases = {
            item["id"]: item for item in cls.fixture["validCases"]
        }

    def run_case(
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

    def test_control_sequence_is_strict_and_zero_dispatch(self) -> None:
        capture, output_root = self.run_case("control-sequence")
        self.assertEqual("control-identity", capture["cell"]["armId"])
        self.assertEqual(
            [
                "hop-1-decomposition",
                "hop-2-routing",
                "hop-3-acceptance-and-recovery",
            ],
            [item["stageId"] for item in capture["stageReceipts"]],
        )
        self.assertEqual(
            EDGE_IDS,
            [item["edgeId"] for item in capture["materialEdges"]],
        )
        self.assertEqual(
            [
                "S0",
                "fixture-control-b1-p1-O1",
                "fixture-control-b1-p1-M1",
                "fixture-control-b1-p1-O2",
                "fixture-control-b1-p1-R2",
                "fixture-control-b1-p1-O3",
            ],
            [item["artifactId"] for item in capture["rawArtifactIndex"]],
        )
        self.assertEqual(0, capture["execution"]["agentDispatchCount"])
        self.assertEqual(0, capture["execution"]["modelCallCount"])
        self.assertFalse(capture["execution"]["actualRouteObserved"])
        self.assertFalse(capture["eligibleForFormalLiveEvidence"])
        for stage_id in (
            "hop-1-decomposition",
            "hop-2-routing",
            "hop-3-acceptance-and-recovery",
        ):
            self.assertEqual(
                ["INPUT-ENVELOPE.json", "STAGE-CONTRACT.json"],
                sorted(
                    item.name
                    for item in (
                        output_root / "AGENT-RUNTIME" / stage_id
                    ).iterdir()
                ),
            )

    def test_arm_is_derived_from_frozen_cell(self) -> None:
        capture, _ = self.run_case(
            "injected-detected-and-gated-recovery"
        )
        self.assertEqual(
            "injected-authority-omission",
            capture["cell"]["armId"],
        )
        mutation = capture["parentTransformReceipts"][0]
        self.assertTrue(mutation["contractMatch"])
        self.assertEqual(
            ["authority"],
            mutation["observedDelta"]["removedInvariantIds"],
        )
        self.assertEqual(
            ["authority"],
            mutation["observedDelta"]["removedProvenanceIds"],
        )

    def test_source_payload_is_conditional_on_exact_detection(self) -> None:
        control, control_root = self.run_case("control-sequence")
        injected, injected_root = self.run_case(
            "injected-detected-and-gated-recovery"
        )
        control_envelope = json.loads(
            (
                control_root
                / "RAW-ARTIFACTS"
                / "fixture-control-b1-p1-R2.json"
            ).read_text(encoding="utf-8")
        )
        injected_envelope = json.loads(
            (
                injected_root
                / "RAW-ARTIFACTS"
                / "fixture-injected-b1-p2-R2.json"
            ).read_text(encoding="utf-8")
        )
        self.assertFalse(control_envelope["sourceAnchorPayloadExposed"])
        self.assertNotIn("sourceAnchorArtifact", control_envelope)
        self.assertTrue(injected_envelope["sourceAnchorPayloadExposed"])
        self.assertEqual(
            "S0",
            injected_envelope["sourceAnchorArtifact"]["artifactId"],
        )
        self.assertFalse(
            control["parentTransformReceipts"][1][
                "sourceAnchorPayloadExposed"
            ]
        )
        self.assertTrue(
            injected["parentTransformReceipts"][1][
                "sourceAnchorPayloadExposed"
            ]
        )

    def test_invalid_detection_halts_before_hop_3(self) -> None:
        def mutate(outputs):
            outputs["hop-2-routing"]["detectedLossIds"].pop()

        capture, output_root = self.run_case(
            "injected-detected-and-gated-recovery",
            mutate_outputs=mutate,
        )
        self.assertEqual(
            "invalid-detection-halted-before-hop-3",
            capture["completion"]["status"],
        )
        self.assertFalse(
            (
                output_root
                / "AGENT-RUNTIME"
                / "hop-3-acceptance-and-recovery"
            ).exists()
        )
        self.assertNotIn(
            "fixture-injected-b1-p2-R2",
            [item["artifactId"] for item in capture["rawArtifactIndex"]],
        )

    def test_missing_required_output_section_fails_closed(self) -> None:
        case = copy.deepcopy(self.cases["control-sequence"])
        del case["scriptedHopOutputs"]["hop-1-decomposition"]["sections"][
            "workItems"
        ]
        with TemporaryDirectory() as temporary:
            with self.assertRaisesRegex(
                SequenceCaptureError,
                "Required output section",
            ):
                run_zero_model_sequence(
                    root=ROOT,
                    output_root=Path(temporary) / "capture",
                    cell=case["cell"],
                    scripted_hop_outputs=case["scriptedHopOutputs"],
                )

    def test_injected_target_must_exist_before_parent_mutation(self) -> None:
        case = copy.deepcopy(
            self.cases["injected-detected-and-gated-recovery"]
        )
        o1 = case["scriptedHopOutputs"]["hop-1-decomposition"]
        o1["values"].pop("authority")
        o1["provenanceIds"].remove("authority")
        with TemporaryDirectory() as temporary:
            with self.assertRaisesRegex(
                SequenceCaptureError,
                "Injected target",
            ):
                run_zero_model_sequence(
                    root=ROOT,
                    output_root=Path(temporary) / "capture",
                    cell=case["cell"],
                    scripted_hop_outputs=case["scriptedHopOutputs"],
                )


if __name__ == "__main__":
    unittest.main()
