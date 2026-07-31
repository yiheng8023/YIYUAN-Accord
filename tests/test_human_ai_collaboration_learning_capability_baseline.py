import copy
import json
import unittest

from scripts.validate_human_ai_collaboration_learning_capability_baseline import (
    BASELINE_PATH,
    SCENARIO_MATRIX_PATH,
    validate_baseline,
)


class HumanAiCollaborationLearningCapabilityBaselineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.baseline = json.loads(BASELINE_PATH.read_text(encoding="utf-8"))
        cls.scenario_matrix = json.loads(
            SCENARIO_MATRIX_PATH.read_text(encoding="utf-8")
        )

    def test_repository_baseline_is_consistent(self) -> None:
        validate_baseline()

    def test_official_metadata_cannot_become_account_availability(self) -> None:
        mutated = copy.deepcopy(self.baseline)
        mutated["officialCapabilityObservations"][0][
            "currentUserAccountAvailabilityProved"
        ] = True
        with self.assertRaisesRegex(RuntimeError, "promoted currentUserAccountAvailabilityProved"):
            validate_baseline(mutated)

    def test_installed_teach_cannot_become_behavior_proof(self) -> None:
        mutated = copy.deepcopy(self.baseline)
        mutated["mattTeachObservation"]["behaviorOrLearningValueProved"] = True
        with self.assertRaisesRegex(RuntimeError, "promoted behaviorOrLearningValueProved"):
            validate_baseline(mutated)

    def test_static_baseline_cannot_promote_scenario_evidence(self) -> None:
        mutated_matrix = copy.deepcopy(self.scenario_matrix)
        scenario = next(
            item
            for item in mutated_matrix["scenarios"]
            if item["id"] == "GEN-LEARNING-01"
        )
        scenario["evidenceState"] = "verified"
        with self.assertRaisesRegex(RuntimeError, "promoted scenario evidence"):
            validate_baseline(self.baseline, scenario_matrix=mutated_matrix)

    def test_self_authored_skill_promotion_fails_closed(self) -> None:
        mutated = copy.deepcopy(self.baseline)
        mutated["comparisonDecision"]["selfAuthoredSkillNeededNow"] = True
        with self.assertRaisesRegex(RuntimeError, "expanded scope"):
            validate_baseline(mutated)

    def test_matt_file_manifest_drift_fails_closed(self) -> None:
        mutated = copy.deepcopy(self.baseline)
        mutated["mattTeachObservation"]["fileRecords"][0]["bytes"] += 1
        with self.assertRaisesRegex(RuntimeError, "file manifest drifted"):
            validate_baseline(mutated)


if __name__ == "__main__":
    unittest.main()
