import copy
import json
from pathlib import Path
import unittest

from scripts.validate_portfolio_tasktime_projection_contract import (
    MUTATION_CASE_IDS,
    validate_contract,
)


ROOT = Path(__file__).resolve().parent.parent
AUTHORITY_ID = "skill-portfolio-current-authority-v1"
PROJECTION_ID = "portfolio-tasktime-projection-v1"


def load_json(path: str) -> dict:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


class PortfolioTasktimeProjectionContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.authority = load_json("registry/skill-portfolio-current-authority.json")
        self.projection = load_json(
            "registry/portfolio-tasktime-projection-contract-2026-08-06.json"
        )
        self.plugin_decision = load_json(
            "registry/plugin-distribution-and-manager-boundary-decision-2026-08-08.json"
        )
        self.acceptance = load_json("registry/program-acceptance-map.json")
        self.texts = {
            "plan_text": read("docs/strategy/RESEARCH-AND-POC-PLAN.md"),
            "goal_prompt_text": read("docs/operations/CURRENT-GOAL-MODE-PROMPT.md"),
            "readme_text": read("README.md"),
            "readme_zh_text": read("README.zh-CN.md"),
        }

    def validate(
        self,
        *,
        authority: dict | None = None,
        projection: dict | None = None,
        plugin_decision: dict | None = None,
        acceptance: dict | None = None,
        texts: dict[str, str] | None = None,
    ) -> None:
        validate_contract(
            self.authority if authority is None else authority,
            self.projection if projection is None else projection,
            self.plugin_decision if plugin_decision is None else plugin_decision,
            self.acceptance if acceptance is None else acceptance,
            **(self.texts if texts is None else texts),
        )

    def test_focused_validator_accepts_current_projection(self) -> None:
        self.validate()

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

    def test_cc_switch_release_binding_is_projected_consistently(self) -> None:
        release = self.projection["sourceBindings"]["ccSwitch"]["release"]
        self.assertEqual("v3.19.2", release)
        for path in (
            "docs/strategy/RESEARCH-AND-POC-PLAN.md",
            "docs/operations/CURRENT-GOAL-MODE-PROMPT.md",
            "README.md",
            "README.zh-CN.md",
        ):
            self.assertIn(release, read(path))

        texts = copy.deepcopy(self.texts)
        texts["plan_text"] = texts["plan_text"].replace(release, "v0.0.0", 1)
        with self.assertRaisesRegex(RuntimeError, "plan CC Switch release projection"):
            self.validate(texts=texts)

    def test_plugin_is_a_manager_agnostic_non_release_consumer_projection(self) -> None:
        boundary = self.projection["pluginDistributionBoundary"]
        decision = self.plugin_decision["decision"]

        self.assertFalse(boundary["wholeRepositoryBecomesPlugin"])
        self.assertTrue(boundary["pluginCompatibilityRequired"])
        self.assertTrue(boundary["pluginIsConsumerProjection"])
        self.assertFalse(boundary["portableCoreDependsOnCcSwitch"])
        self.assertTrue(boundary["oneLifecycleAuthorityPerComponent"])
        self.assertFalse(boundary["ccManagedThirdPartyPayloadMayBeBundled"])
        self.assertFalse(boundary["releaseEligibleNow"])
        self.assertEqual(
            "registry/offline-plugin-projection-poc-2026-08-08.json",
            boundary["offlineProjectionPoc"],
        )
        self.assertEqual(
            "offline-preview-verified-release-not-eligible",
            boundary["offlineProjectionPocStatus"],
        )
        self.assertEqual(
            "admitted-repository-owned-component-plus-natural-real-task-before-live-plugin-validation",
            boundary["nextGate"],
        )
        self.assertEqual(
            decision["currentPosture"],
            "plugin-compatible-manager-agnostic-release-not-eligible",
        )

    def test_failure_injection_matrix_fails_closed(self) -> None:
        mutations = []

        authority = copy.deepcopy(self.authority)
        authority["id"] = "wrong-authority"
        mutations.append(
            ("authority-id-drift", authority, None, None, None, None)
        )

        projection_mutations = {
            "curation-real-task-global-stop": (
                ("schedulerLanes", "portfolioCuration", "requiresRealTask"),
                True,
            ),
            "curation-installation-authority-promotion": (
                (
                    "schedulerLanes",
                    "portfolioCuration",
                    "installationOrActivationAuthorized",
                ),
                True,
            ),
            "curation-stop-rule-removal": (
                ("schedulerLanes", "portfolioCuration", "stopRuleRequired"),
                False,
            ),
            "mechanism-real-task-global-stop": (
                ("schedulerLanes", "mechanismValidation", "requiresRealTask"),
                True,
            ),
            "mechanism-claim-promotion": (
                ("schedulerLanes", "mechanismValidation", "claimBoundary"),
                "behavior-value-production",
            ),
            "task-time-real-task-removal": (
                ("schedulerLanes", "taskTimeBehaviorAndValue", "requiresRealTask"),
                False,
            ),
            "task-time-current-gap-removal": (
                (
                    "schedulerLanes",
                    "taskTimeBehaviorAndValue",
                    "requiresCurrentCapabilityGap",
                ),
                False,
            ),
            "task-time-activation-authority-removal": (
                (
                    "schedulerLanes",
                    "taskTimeBehaviorAndValue",
                    "requiresSeparateActivationAuthority",
                ),
                False,
            ),
            "user-invented-task-burden-promotion": (
                ("burdenBoundary", "doNotRequireUserToInventTasks"),
                False,
            ),
            "direct-installer-manager-authority-promotion": (
                (
                    "ccSwitchFreshnessBoundary",
                    "directUpstreamInstallerPreservesManagerAuthority",
                ),
                True,
            ),
            "plugin-whole-product-promotion": (
                ("pluginDistributionBoundary", "wholeRepositoryBecomesPlugin"),
                True,
            ),
            "plugin-cc-switch-dependency-promotion": (
                ("pluginDistributionBoundary", "portableCoreDependsOnCcSwitch"),
                True,
            ),
            "plugin-third-party-bundling-promotion": (
                (
                    "pluginDistributionBoundary",
                    "ccManagedThirdPartyPayloadMayBeBundled",
                ),
                True,
            ),
            "plugin-release-eligibility-promotion": (
                ("pluginDistributionBoundary", "releaseEligibleNow"),
                True,
            ),
            "residual-gap-authoring-gate-removal": (
                (
                    "schedulerLanes",
                    "repositoryAuthoredGapFill",
                    "requiresResidualGapEvidence",
                ),
                False,
            ),
            "broad-claim-promotion": (
                ("claimBoundary", "projectionConsistencyProvesBehavior"),
                True,
            ),
        }
        for case_id, (path, value) in projection_mutations.items():
            projection = copy.deepcopy(self.projection)
            target = projection
            for key in path[:-1]:
                target = target[key]
            target[path[-1]] = value
            mutations.append((case_id, None, projection, None, None, None))

        projection = copy.deepcopy(self.projection)
        del projection["sourceBindings"]["decisionPacketCore"]
        mutations.append(
            (
                "decision-packet-core-boundary-removal",
                None,
                projection,
                None,
                None,
                None,
            )
        )

        acceptance = copy.deepcopy(self.acceptance)
        criterion = next(
            item
            for item in acceptance["acceptanceCriteria"]
            if item["id"] == "acceptance.sequence-integrity"
        )
        criterion["assessment"] = "partial"
        mutations.append(
            (
                "acceptance-verification-downgrade",
                None,
                None,
                None,
                acceptance,
                None,
            )
        )

        self.assertEqual([item[0] for item in mutations], MUTATION_CASE_IDS)
        for (
            case_id,
            authority,
            projection,
            plugin_decision,
            acceptance,
            texts,
        ) in mutations:
            with self.subTest(case_id=case_id):
                with self.assertRaises(RuntimeError):
                    self.validate(
                        authority=authority,
                        projection=projection,
                        plugin_decision=plugin_decision,
                        acceptance=acceptance,
                        texts=texts,
                    )


if __name__ == "__main__":
    unittest.main()
