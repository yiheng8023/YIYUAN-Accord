from __future__ import annotations

import unittest

from scripts.probe_codex_app_server_skill_exposure import EFFORT, MODEL
from scripts.run_human_ai_collaboration_tdd_raw_item_pilot import (
    compare_disabled_inventory,
    evaluate_pilot,
)


class HumanAiCollaborationTddRawItemPilotTests(unittest.TestCase):
    def valid_inputs(self) -> dict:
        return {
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
                "rawEnvelopeCount": 18,
            },
            "offline_timeline": {
                "status": "accepted-offline-tdd-timeline",
            },
            "changed": [
                "PROCESS_EVIDENCE.json",
                "feature.py",
                "test_feature.py",
            ],
            "config_stable": True,
            "turn_status": "completed",
        }

    def test_valid_pilot_is_non_scored(self) -> None:
        result = evaluate_pilot(**self.valid_inputs())
        self.assertEqual(
            "current-host-raw-item-normalization-pilot-pass",
            result["status"],
        )
        self.assertTrue(result["processInstrumentationPilotPassed"])
        self.assertTrue(result["nonScored"])
        self.assertFalse(result["countsTowardWeakAcceptance"])
        self.assertFalse(result["formalRunCounted"])

    def test_unknown_raw_event_fails_closed(self) -> None:
        inputs = self.valid_inputs()
        inputs["normalization"] = {
            "status": "normalization-incomplete-or-boundary-failed",
            "rawEnvelopeCount": 19,
        }
        result = evaluate_pilot(**inputs)
        self.assertEqual(
            "current-host-raw-item-normalization-pilot-incomplete",
            result["status"],
        )
        self.assertIn(
            "raw-event-normalization-incomplete",
            result["failureCodes"],
        )

    def test_inventory_comparison_preserves_system_state(self) -> None:
        before = [
            {
                "name": "candidate",
                "path": "C:/skills/candidate/SKILL.md",
                "scope": "user",
                "enabled": True,
            },
            {
                "name": "system",
                "path": "C:/system/SKILL.md",
                "scope": "system",
                "enabled": True,
            },
        ]
        after = [
            {**before[0], "enabled": False},
            before[1],
        ]
        result = compare_disabled_inventory(before, after)
        self.assertTrue(result["sameIdentitySet"])
        self.assertTrue(result["allConfigurableSkillsDisabled"])
        self.assertTrue(result["allNonConfigurableStatesPreserved"])


if __name__ == "__main__":
    unittest.main()
