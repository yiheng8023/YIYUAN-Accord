import copy
import json
import unittest

from scripts.evaluate_human_ai_collaboration_learning_protocol import evaluate_record
from scripts.validate_human_ai_collaboration_learning_fixed_fixture_protocol import (
    FIXTURE_PATH,
    PROTOCOL_PATH,
    validate_protocol,
)


class HumanAiCollaborationLearningFixedFixtureProtocolTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.protocol = json.loads(PROTOCOL_PATH.read_text(encoding="utf-8"))
        cls.fixtures = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))

    def test_repository_protocol_is_consistent(self) -> None:
        validate_protocol()

    def test_all_preregistered_mechanism_fixtures_match(self) -> None:
        for fixture in self.fixtures["fixtures"]:
            self.assertEqual(fixture["expected"], evaluate_record(fixture["record"]))

    def test_current_phase_cannot_skip_to_live_trial(self) -> None:
        mutated = copy.deepcopy(self.protocol)
        mutated["phaseOrder"][0]["current"] = False
        mutated["phaseOrder"][3]["current"] = True
        with self.assertRaisesRegex(RuntimeError, "current phase drifted"):
            validate_protocol(mutated)

    def test_silent_model_substitution_fails_closed(self) -> None:
        fixture = next(
            item
            for item in self.fixtures["fixtures"]
            if item["id"] == "sim.formally-shaped-record-only-eligible-for-analysis"
        )
        mutated = copy.deepcopy(fixture["record"])
        mutated["weakAgentRoute"]["actualModel"] = "gpt-5.4"
        self.assertEqual(
            {"decision": "invalid", "failureCodes": ["weak-agent-route-substituted"]},
            evaluate_record(mutated),
        )

    def test_learning_effect_claim_cannot_follow_complete_record(self) -> None:
        fixture = next(
            item
            for item in self.fixtures["fixtures"]
            if item["id"] == "sim.formally-shaped-record-only-eligible-for-analysis"
        )
        mutated = copy.deepcopy(fixture["record"])
        mutated["claim"]["kind"] = "learning-effect"
        self.assertEqual(
            {"decision": "invalid", "failureCodes": ["formal-trial-effect-claim-premature"]},
            evaluate_record(mutated),
        )

    def test_protocol_cannot_authorize_model_dispatch(self) -> None:
        mutated = copy.deepcopy(self.protocol)
        mutated["authorityBoundary"]["modelDispatchAuthorizedByProtocol"] = True
        with self.assertRaisesRegex(RuntimeError, "expanded authority"):
            validate_protocol(mutated)

    def test_cleanup_contract_cannot_be_weakened(self) -> None:
        mutated = copy.deepcopy(self.protocol)
        mutated["cleanupContract"]["exactCleanupVerificationRequired"] = False
        with self.assertRaisesRegex(RuntimeError, "cleanup contract weakened"):
            validate_protocol(mutated)


if __name__ == "__main__":
    unittest.main()
