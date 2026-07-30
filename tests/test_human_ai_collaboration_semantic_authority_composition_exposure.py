from __future__ import annotations

import copy
import unittest

from scripts.probe_human_ai_collaboration_semantic_authority_composition_exposure import (
    compare_inventory,
    validate_report,
)


class SemanticAuthorityCompositionExposureTests(unittest.TestCase):
    def inventory(self, enabled: set[str]) -> list[dict]:
        return [
            {
                "name": name,
                "path": f"C:/tmp/trial/.agents/skills/{name}/SKILL.md",
                "scope": "repo",
                "enabled": name in enabled,
            }
            for name in ("domain-modeling", "grill-with-docs", "grilling")
        ] + [
            {
                "name": "system",
                "path": "C:/runtime/system/SKILL.md",
                "scope": "system",
                "enabled": True,
            }
        ]

    def report(self) -> dict:
        required = ["domain-modeling", "grill-with-docs", "grilling"]
        return {
            "schema": 1,
            "probeId": "semantic-authority-composition-exposure-preflight-v1",
            "status": "preflight-pass-no-turn",
            "threadStarted": False,
            "turnStarted": False,
            "exposure": {
                "requiredSkillCount": 3,
                "requiredSkillNames": required,
                "allRequiredExactPathsPresent": True,
            },
            "arms": [
                {
                    "arm": "control-unselected",
                    "inventory": compare_inventory(
                        self.inventory(set()),
                        self.inventory(set()),
                        expected_enabled_paths=set(),
                    ),
                },
                {
                    "arm": "composition-selected",
                    "inventory": compare_inventory(
                        self.inventory(set()),
                        self.inventory(set(required)),
                        expected_enabled_paths={
                            f"C:/tmp/trial/.agents/skills/{name}/SKILL.md"
                            for name in required
                        },
                    ),
                },
            ],
            "stability": {
                "projectionTreeStable": True,
                "globalConfigStable": True,
                "repositoryStatusStable": True,
            },
            "claimBoundary": {
                "entryLoaderInvocationProved": False,
                "dependencyLoaderInvocationProved": False,
            },
        }

    def test_valid_offline_report_passes(self) -> None:
        self.assertEqual([], validate_report(self.report()))

    def test_rejects_missing_dependency_exposure(self) -> None:
        report = copy.deepcopy(self.report())
        report["exposure"]["requiredSkillCount"] = 2
        self.assertIn("fail-required-skill-count", validate_report(report))

    def test_rejects_extra_enabled_skill(self) -> None:
        report = copy.deepcopy(self.report())
        arm = report["arms"][1]
        arm["inventory"]["enabledConfigurableSkillCount"] = 4
        self.assertIn(
            "fail-enabled-count:composition-selected",
            validate_report(report),
        )

    def test_rejects_loader_claim_promotion(self) -> None:
        report = copy.deepcopy(self.report())
        report["claimBoundary"]["entryLoaderInvocationProved"] = True
        self.assertIn("hard-fail-claim-promotion", validate_report(report))


if __name__ == "__main__":
    unittest.main()
