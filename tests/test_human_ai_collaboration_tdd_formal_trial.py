from __future__ import annotations

import unittest

from scripts.probe_codex_app_server_skill_exposure import EFFORT, MODEL
from scripts.run_human_ai_collaboration_tdd_formal_trial import (
    NATIVE_ARM,
    evaluate_formal_trial,
)


class HumanAiCollaborationTddFormalTrialTests(unittest.TestCase):
    def valid_inputs(self) -> dict:
        return {
            "arm": NATIVE_ARM,
            "thread": {
                "model": MODEL,
                "reasoningEffort": EFFORT,
                "providerFallbackAllowed": False,
                "approvalPolicy": "never",
                "requestedSandbox": {
                    "type": "workspaceWrite",
                    "networkAccess": False,
                },
            },
            "exposure": {
                "sameIdentitySet": True,
                "allConfigurableSkillsDisabled": True,
                "allNonConfigurableStatesPreserved": True,
            },
            "normalization": {
                "status": "normalized-observable",
                "rawEnvelopeCount": 20,
            },
            "offline_timeline": {
                "status": "accepted-offline-tdd-timeline",
            },
            "parent_outcome": {
                "status": "parent-outcome-accepted",
            },
            "changed": ["feature.py", "test_feature.py"],
            "config_stable": True,
            "turn_status": "completed",
            "projection_materialized": False,
        }

    def test_valid_native_repetition_counts(self) -> None:
        result = evaluate_formal_trial(**self.valid_inputs())
        self.assertEqual(
            "valid-formal-weak-agent-tdd-repetition",
            result["status"],
        )
        self.assertTrue(result["formalRunCounted"])
        self.assertTrue(result["countsTowardWeakAcceptance"])

    def test_final_green_cannot_override_rejected_timeline(self) -> None:
        inputs = self.valid_inputs()
        inputs["offline_timeline"] = {
            "status": "rejected-offline-tdd-timeline",
        }
        result = evaluate_formal_trial(**inputs)
        self.assertFalse(result["formalRunCounted"])
        self.assertIn(
            "ordered-tdd-process-rejected",
            result["failureCodes"],
        )

    def test_treatment_requires_exact_selected_exposure(self) -> None:
        inputs = self.valid_inputs()
        inputs["arm"] = "SE-TDD-MATT-CURRENT"
        inputs["projection_materialized"] = True
        inputs["exposure"] = {
            "sameIdentitySet": True,
            "selectedIdentityPresent": True,
            "onlyExpectedConfigurableSkillEnabled": False,
            "allNonConfigurableStatesPreserved": True,
        }
        result = evaluate_formal_trial(**inputs)
        self.assertFalse(result["formalRunCounted"])
        self.assertIn(
            "exact-skill-exposure-not-proved",
            result["failureCodes"],
        )

    def test_parent_oracle_failure_invalidates_repetition(self) -> None:
        inputs = self.valid_inputs()
        inputs["parent_outcome"] = {
            "status": "parent-outcome-rejected",
        }
        result = evaluate_formal_trial(**inputs)
        self.assertFalse(result["formalRunCounted"])
        self.assertIn(
            "parent-owned-final-outcome-rejected",
            result["failureCodes"],
        )


if __name__ == "__main__":
    unittest.main()
