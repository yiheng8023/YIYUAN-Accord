import copy
import json
from pathlib import Path
import unittest

from scripts.validate_human_ai_collaboration_process_fidelity_information_equivalent_trial_protocol import (
    PROTOCOL_PATH,
    validate_protocol,
)


ROOT = Path(__file__).resolve().parent.parent
PROTOCOL = ROOT / PROTOCOL_PATH
MATRIX = (
    ROOT
    / "registry"
    / "human-ai-collaboration-scenario-evidence-matrix-batch-01-"
    "2026-07-24.json"
)


class InformationEquivalentProcessFidelityProtocolTests(unittest.TestCase):
    def setUp(self) -> None:
        self.protocol = json.loads(PROTOCOL.read_text(encoding="utf-8"))
        self.matrix = json.loads(MATRIX.read_text(encoding="utf-8"))

    def test_current_protocol_is_valid(self) -> None:
        validate_protocol(self.protocol, root=ROOT, matrix=self.matrix)

    def test_arm_information_set_drift_fails_before_dispatch(self) -> None:
        mutated = copy.deepcopy(self.protocol)
        mutated["trialArms"][1]["sourceIdsExact"].remove("SRC-D")
        with self.assertRaisesRegex(RuntimeError, "manifest drifted"):
            validate_protocol(mutated, root=ROOT, matrix=self.matrix)
        self.assertTrue(
            mutated["executionBoundary"]["zeroDispatchOnPreflightFailure"]
        )

    def test_one_arm_cannot_receive_a_different_oracle(self) -> None:
        mutated = copy.deepcopy(self.protocol)
        mutated["trialArms"][2]["privateOracleCanonicalSha256"] = "0" * 64
        with self.assertRaisesRegex(RuntimeError, "manifest drifted"):
            validate_protocol(mutated, root=ROOT, matrix=self.matrix)

    def test_model_or_effort_difference_is_an_arm_confound(self) -> None:
        mutated = copy.deepcopy(self.protocol)
        mutated["trialArms"][1]["modelId"] = "gpt-5.6-terra"
        with self.assertRaisesRegex(RuntimeError, "confound"):
            validate_protocol(mutated, root=ROOT, matrix=self.matrix)

    def test_private_oracle_cannot_enter_any_public_carrier(self) -> None:
        mutated = copy.deepcopy(self.protocol)
        mutated["sourceAndOracleBinding"]["privateOracle"][
            "contentWrittenIntoSourceBackedArtifact"
        ] = True
        with self.assertRaisesRegex(RuntimeError, "exposed"):
            validate_protocol(mutated, root=ROOT, matrix=self.matrix)

    def test_manual_path_cannot_promote_automatic_host_capability(self) -> None:
        mutated = copy.deepcopy(self.protocol)
        mutated["authorityBoundary"]["automaticThreadCreationClaimed"] = True
        with self.assertRaisesRegex(RuntimeError, "authority overclaimed"):
            validate_protocol(mutated, root=ROOT, matrix=self.matrix)

    def test_incomplete_repetitions_cannot_form_a_comparison(self) -> None:
        mutated = copy.deepcopy(self.protocol)
        mutated["repetitionAndOrderingContract"][
            "minimumValidRepetitionsPerArm"
        ] = 2
        mutated["claimBoundary"]["armComparisonComplete"] = True
        with self.assertRaisesRegex(
            RuntimeError,
            "repetition or ordering contract|claim boundary",
        ):
            validate_protocol(mutated, root=ROOT, matrix=self.matrix)

    def test_offline_protocol_cannot_promote_matrix_evidence(self) -> None:
        mutated_matrix = copy.deepcopy(self.matrix)
        mutated_matrix["crossCuttingRisks"][0]["evidenceState"] = (
            "verified-end-to-end-process-fidelity"
        )
        with self.assertRaisesRegex(RuntimeError, "promoted matrix"):
            validate_protocol(
                self.protocol,
                root=ROOT,
                matrix=mutated_matrix,
            )

    def test_terminal_match_cannot_erase_intermediate_loss_rule(self) -> None:
        mutated = copy.deepcopy(self.protocol)
        mutated["measurementContract"]["intermediateLossRule"] = (
            "A terminal oracle match passes."
        )
        with self.assertRaisesRegex(RuntimeError, "process-loss boundary"):
            validate_protocol(mutated, root=ROOT, matrix=self.matrix)


if __name__ == "__main__":
    unittest.main()
