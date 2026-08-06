import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parent.parent
AUTHORITY_ID = "skill-portfolio-current-authority-v1"
PROJECTION_ID = "portfolio-tasktime-projection-v1"


def load_json(path: str) -> dict:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


class PortfolioTasktimeProjectionContractTests(unittest.TestCase):
    def test_projection_binds_one_authority_to_three_distinct_surfaces(self) -> None:
        authority = load_json("registry/skill-portfolio-current-authority.json")
        projection = load_json(
            "registry/portfolio-tasktime-projection-contract-2026-08-06.json"
        )

        self.assertEqual(authority["id"], AUTHORITY_ID)
        self.assertEqual(projection["semanticAuthorityId"], AUTHORITY_ID)
        self.assertEqual(projection["id"], PROJECTION_ID)
        self.assertEqual(
            projection["projections"],
            {
                "plan": "docs/strategy/RESEARCH-AND-POC-PLAN.md",
                "acceptance": "registry/program-acceptance-map.json",
                "goalModePrompt": "docs/operations/CURRENT-GOAL-MODE-PROMPT.md",
            },
        )
        self.assertEqual(
            projection["projectionMarker"],
            f"semantic-projection: {PROJECTION_ID}",
        )

    def test_scheduler_keeps_curation_moving_without_inventing_real_tasks(self) -> None:
        projection = load_json(
            "registry/portfolio-tasktime-projection-contract-2026-08-06.json"
        )
        lanes = projection["schedulerLanes"]

        self.assertFalse(lanes["portfolioCuration"]["requiresRealTask"])
        self.assertIn(
            "exact-revision-inactive-acquisition",
            lanes["portfolioCuration"]["allowedActions"],
        )
        self.assertFalse(lanes["mechanismValidation"]["requiresRealTask"])
        self.assertTrue(lanes["taskTimeBehaviorAndValue"]["requiresRealTask"])
        self.assertEqual(
            lanes["taskTimeBehaviorAndValue"]["claimBoundary"],
            "behavior-value-production",
        )
        self.assertTrue(projection["burdenBoundary"]["doNotRequireUserToInventTasks"])
        self.assertTrue(
            projection["burdenBoundary"]["harnessOwnsBoundedPortfolioProgression"]
        )

    def test_plan_acceptance_and_goal_prompt_carry_the_same_projection_marker(self) -> None:
        marker = f"semantic-projection: {PROJECTION_ID}"
        plan = read("docs/strategy/RESEARCH-AND-POC-PLAN.md")
        goal_prompt = read("docs/operations/CURRENT-GOAL-MODE-PROMPT.md")
        acceptance = load_json("registry/program-acceptance-map.json")
        criteria = {item["id"]: item for item in acceptance["acceptanceCriteria"]}

        self.assertIn(marker, plan)
        self.assertIn(marker, goal_prompt)
        criterion = criteria["acceptance.sequence-integrity"]
        self.assertEqual(criterion["semanticProjectionId"], PROJECTION_ID)
        self.assertEqual(criterion["assessment"], "verified")

    def test_current_execution_surfaces_do_not_turn_real_task_into_global_stop(self) -> None:
        plan = " ".join(read("docs/strategy/RESEARCH-AND-POC-PLAN.md").split()).lower()
        goal_prompt = " ".join(
            read("docs/operations/CURRENT-GOAL-MODE-PROMPT.md").split()
        ).lower()
        english = " ".join(read("README.md").split()).lower()
        chinese = "".join(read("README.zh-CN.md").split())

        for surface in (plan, goal_prompt, english):
            self.assertIn("portfolio curation", surface)
            self.assertIn("does not require", surface)
            self.assertIn("real task", surface)
        self.assertIn("组合策展不要求", chinese)
        self.assertIn("真实任务", chinese)

        self.assertNotIn("current unique action: wait for", goal_prompt)
        self.assertNotIn("the whole program must wait", goal_prompt)

    def test_skills_sh_discovery_preserves_manager_only_when_cc_owns_lifecycle(self) -> None:
        projection = load_json(
            "registry/portfolio-tasktime-projection-contract-2026-08-06.json"
        )
        boundary = projection["ccSwitchFreshnessBoundary"]

        self.assertTrue(boundary["skillsShMayAddUpstreamRepositoryToCc"])
        self.assertTrue(boundary["ccRefreshAndUpdatePreserveManagerAuthority"])
        self.assertFalse(boundary["directUpstreamInstallerPreservesManagerAuthority"])
        self.assertEqual(
            boundary["directInstallerSafeUse"],
            "isolated-inactive-acquisition-only-unless-separately-admitted",
        )


if __name__ == "__main__":
    unittest.main()
