import copy
import json
from pathlib import Path
import unittest

from scripts.validate_process_fidelity_chained_transform_trial_protocol import (
    MATRIX_PATH,
    PROTOCOL_PATH,
    validate_protocol,
)


ROOT = Path(__file__).resolve().parent.parent


class ProcessFidelityChainedTransformTrialProtocolTests(
    unittest.TestCase
):
    def setUp(self) -> None:
        self.protocol = json.loads(
            (ROOT / PROTOCOL_PATH).read_text(encoding="utf-8")
        )
        self.matrix = json.loads(
            (ROOT / MATRIX_PATH).read_text(encoding="utf-8")
        )

    def test_current_protocol_is_valid(self) -> None:
        validate_protocol(self.protocol, root=ROOT, matrix=self.matrix)

    def test_live_dispatch_cannot_be_enabled_by_design(self) -> None:
        mutated = copy.deepcopy(self.protocol)
        mutated["designBoundary"]["liveExecutionAuthorized"] = True
        with self.assertRaisesRegex(RuntimeError, "zero-dispatch"):
            validate_protocol(mutated, root=ROOT, matrix=self.matrix)

    def test_noncanonical_hard_requirement_fails(self) -> None:
        mutated = copy.deepcopy(self.protocol)
        mutated["scenarioBinding"]["hardRequirementIds"][0] = "HR-UNKNOWN"
        with self.assertRaisesRegex(RuntimeError, "scenario binding"):
            validate_protocol(mutated, root=ROOT, matrix=self.matrix)

    def test_mutation_may_not_expand_beyond_authority_omission(self) -> None:
        mutated = copy.deepcopy(self.protocol)
        mutated["armDefinitions"][1]["allowedDelta"][
            "addedAssumptionIds"
        ] = ["commit-authorized"]
        with self.assertRaisesRegex(RuntimeError, "injected mutation"):
            validate_protocol(mutated, root=ROOT, matrix=self.matrix)

    def test_weak_route_cannot_silently_fallback(self) -> None:
        mutated = copy.deepcopy(self.protocol)
        mutated["cohortDesign"]["primaryAgentRoute"][
            "automaticFallbackAllowed"
        ] = True
        with self.assertRaisesRegex(RuntimeError, "cohort design"):
            validate_protocol(mutated, root=ROOT, matrix=self.matrix)

    def test_run_order_must_remain_position_balanced(self) -> None:
        mutated = copy.deepcopy(self.protocol)
        mutated["cohortDesign"]["pairedRunBlocks"][1].reverse()
        with self.assertRaisesRegex(RuntimeError, "cohort design"):
            validate_protocol(mutated, root=ROOT, matrix=self.matrix)

    def test_strong_diagnostic_cannot_rescue_weak_failure(self) -> None:
        mutated = copy.deepcopy(self.protocol)
        mutated["strongAgentDiagnostic"]["mayRescueWeakAgentFailure"] = True
        with self.assertRaisesRegex(RuntimeError, "strong diagnostic"):
            validate_protocol(mutated, root=ROOT, matrix=self.matrix)

    def test_terminal_pass_cannot_cancel_process_failure(self) -> None:
        mutated = copy.deepcopy(self.protocol)
        mutated["acceptanceDecision"][
            "terminalAbsolutePassMayOverrideProcessFailure"
        ] = True
        with self.assertRaisesRegex(RuntimeError, "acceptance boundary"):
            validate_protocol(mutated, root=ROOT, matrix=self.matrix)

    def test_opaque_material_edge_cannot_be_scored_as_zero(self) -> None:
        mutated = copy.deepcopy(self.protocol)
        mutated["estimandBoundary"][
            "opaqueMaterialEdgeMayBeScoredAsZero"
        ] = True
        with self.assertRaisesRegex(RuntimeError, "estimand"):
            validate_protocol(mutated, root=ROOT, matrix=self.matrix)


if __name__ == "__main__":
    unittest.main()
