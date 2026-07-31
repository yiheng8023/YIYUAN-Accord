from __future__ import annotations

import copy
import json
import unittest

from scripts.validate_human_ai_collaboration_creative_capability_baseline import (
    BASELINE_PATH,
    SCENARIO_MATRIX_PATH,
    validate_baseline,
)


class HumanAiCollaborationCreativeCapabilityBaselineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.baseline = json.loads(BASELINE_PATH.read_text(encoding="utf-8"))
        cls.scenario_matrix = json.loads(
            SCENARIO_MATRIX_PATH.read_text(encoding="utf-8")
        )

    def test_repository_baseline_is_consistent(self) -> None:
        validate_baseline()

    def test_existing_packet_cannot_become_live_value_evidence(self) -> None:
        mutated = copy.deepcopy(self.baseline)
        mutated["existingZeroModelPacket"]["liveCreativeValueProved"] = True
        with self.assertRaisesRegex(RuntimeError, "promoted to behavior or value evidence"):
            validate_baseline(mutated)

    def test_official_metadata_cannot_become_behavior_proof(self) -> None:
        mutated = copy.deepcopy(self.baseline)
        mutated["officialCreativeProductionObservation"][
            "instructionDeliveryOrBehaviorProved"
        ] = True
        with self.assertRaisesRegex(RuntimeError, "promoted instructionDeliveryOrBehaviorProved"):
            validate_baseline(mutated)

    def test_static_baseline_cannot_promote_scenario_evidence(self) -> None:
        mutated_matrix = copy.deepcopy(self.scenario_matrix)
        scenario = next(
            item
            for item in mutated_matrix["scenarios"]
            if item["id"] == "GEN-CREATIVE-01"
        )
        scenario["evidenceState"] = "verified"
        with self.assertRaisesRegex(RuntimeError, "promoted scenario evidence"):
            validate_baseline(self.baseline, scenario_matrix=mutated_matrix)

    def test_candidate_or_self_authored_expansion_fails_closed(self) -> None:
        mutated = copy.deepcopy(self.baseline)
        mutated["comparisonDecision"]["selfAuthoredSkillNeededNow"] = True
        with self.assertRaisesRegex(RuntimeError, "expanded scope"):
            validate_baseline(mutated)

    def test_stable_neutrality_cannot_be_rewritten_as_a_change(self) -> None:
        mutated = copy.deepcopy(self.baseline)
        mutated["neutralityAndJudgmentBoundary"]["projectNeutralityChanged"] = True
        with self.assertRaisesRegex(RuntimeError, "misrepresented as a change"):
            validate_baseline(mutated)

    def test_human_aesthetic_authority_cannot_be_promoted_to_agent(self) -> None:
        mutated = copy.deepcopy(self.baseline)
        mutated["neutralityAndJudgmentBoundary"]["finalAestheticDecisionOwner"] = "agent"
        with self.assertRaisesRegex(RuntimeError, "human decision ownership drifted"):
            validate_baseline(mutated)


if __name__ == "__main__":
    unittest.main()
