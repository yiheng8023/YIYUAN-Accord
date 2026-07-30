from __future__ import annotations

import copy
import unittest

from scripts.probe_source_pinned_skill_projection_preflight import (
    compare_inventory,
    validate_preflight_report,
)


class SourcePinnedSkillProjectionPreflightTests(unittest.TestCase):
    def test_inventory_comparison_selects_only_project_candidate(self) -> None:
        control = [
            {
                "name": "candidate",
                "path": "C:/tmp/run/.agents/skills/candidate/SKILL.md",
                "scope": "repo",
                "enabled": True,
            },
            {
                "name": "other",
                "path": "C:/Users/test/.agents/skills/other/SKILL.md",
                "scope": "user",
                "enabled": True,
            },
            {
                "name": "system",
                "path": "C:/runtime/system/SKILL.md",
                "scope": "system",
                "enabled": True,
            },
        ]
        effective = copy.deepcopy(control)
        effective[1]["enabled"] = False
        result = compare_inventory(
            control,
            effective,
            selected_path=control[0]["path"],
            selected=True,
        )
        self.assertTrue(result["onlyExpectedConfigurableSkillEnabled"])
        self.assertTrue(result["allNonConfigurableStatesPreserved"])

    def test_inventory_comparison_rejects_second_enabled_skill(self) -> None:
        rows = [
            {
                "name": "candidate",
                "path": "C:/tmp/candidate/SKILL.md",
                "scope": "repo",
                "enabled": True,
            },
            {
                "name": "other",
                "path": "C:/tmp/other/SKILL.md",
                "scope": "user",
                "enabled": True,
            },
        ]
        result = compare_inventory(
            rows,
            rows,
            selected_path=rows[0]["path"],
            selected=True,
        )
        self.assertFalse(result["onlyExpectedConfigurableSkillEnabled"])

    def test_report_rejects_claim_promotion(self) -> None:
        report = {
            "schema": 1,
            "probeId": "source-pinned-skill-projection-preflight-v1",
            "status": "preflight-pass-no-turn",
            "threadStarted": False,
            "turnStarted": False,
            "arms": [
                {
                    "arm": "candidate-selected",
                    "inventory": {
                        "sameIdentitySet": True,
                        "selectedIdentityPresent": True,
                        "onlyExpectedConfigurableSkillEnabled": True,
                        "allNonConfigurableStatesPreserved": True,
                    },
                }
            ],
            "stability": {
                "projectionTreeStable": True,
                "globalConfigStable": True,
                "repositoryStatusStable": True,
            },
            "claimBoundary": {
                "bodyDeliveryProved": True,
            },
        }
        self.assertIn(
            "hard-fail-claim-promotion",
            validate_preflight_report(report),
        )


if __name__ == "__main__":
    unittest.main()
