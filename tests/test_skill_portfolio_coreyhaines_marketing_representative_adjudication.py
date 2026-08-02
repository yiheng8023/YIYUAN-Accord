import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parent.parent
DECISION = ROOT / "registry/skill-portfolio-coreyhaines-marketing-representative-adjudication-2026-08-03.json"


class SkillPortfolioCoreyHainesMarketingRepresentativeAdjudicationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.decision = json.loads(DECISION.read_text(encoding="utf-8"))

    def test_exact_source_and_object_only_acquisition_are_bound(self) -> None:
        source = self.decision["source"]
        self.assertEqual(source["repository"], "coreyhaines31/marketingskills")
        self.assertEqual(source["commit"], "7868cb9251fad80a73d26e488a5ad5f6c4a9f335")
        self.assertEqual(source["tree"], "795fbd548840b43ee3e5a69cbfdda280a22c0422")
        self.assertEqual(source["license"], "MIT")
        self.assertEqual(source["licenseSha256"], "b70d71e24e40fce5da8f4b6f9cd862096a048e433db7f3c8cac5e348e6d34591")
        self.assertEqual(source["reviewMode"], "exact-bare-git-object-read-only")
        self.assertFalse(source["thirdPartyCodeExecuted"])
        self.assertFalse(source["payloadModified"])

    def test_repository_script_surface_is_not_misattributed_to_every_skill(self) -> None:
        cohort = self.decision["cohort"]
        self.assertEqual(cohort["sourceSkillCount"], 49)
        self.assertEqual(cohort["reviewedSkillCount"], 9)
        self.assertEqual(cohort["repositoryScriptLikeFileCount"], 67)
        self.assertEqual(cohort["scriptBearingSkillPathCount"], 0)
        self.assertFalse(cohort["wholeCatalogAdmissionUnit"])
        self.assertEqual(len(self.decision["representativeSkills"]), 9)

    def test_three_methods_advance_only_to_default_disabled_comparison(self) -> None:
        items = {item["name"]: item for item in self.decision["representativeSkills"]}
        advanced = {
            name for name, item in items.items()
            if item["disposition"] == "manager-install-candidate-default-disabled-behavior-comparison-required"
        }
        self.assertEqual(advanced, {"copywriting", "copy-editing", "customer-research"})
        for name in advanced:
            self.assertEqual(items[name]["bundledExecutableFileCount"], 0)

    def test_collision_context_scheduler_and_repository_dependencies_hold(self) -> None:
        items = {item["name"]: item for item in self.decision["representativeSkills"]}
        self.assertEqual(items["marketing-ideas"]["disposition"], "hold-cross-source-name-collision")
        self.assertEqual(items["product-marketing"]["disposition"], "hold-persistent-context-authority-and-adapter-review")
        self.assertEqual(items["marketing-loops"]["disposition"], "hold-cross-host-scheduler-and-lifecycle-adapter-review")
        self.assertEqual(items["analytics"]["disposition"], "hold-repository-level-dependency-incomplete")

    def test_outbound_and_persona_routes_do_not_advance(self) -> None:
        items = {item["name"]: item for item in self.decision["representativeSkills"]}
        self.assertEqual(items["cold-email"]["disposition"], "hold-high-impact-outbound-compliance-review")
        self.assertEqual(items["marketing-council"]["disposition"], "reference-only-simulated-persona-and-overlap")

    def test_install_and_runtime_claims_remain_false(self) -> None:
        manager = self.decision["managerBoundary"]
        self.assertFalse(manager["repositoryRegistrationExecuted"])
        self.assertFalse(manager["candidateInstallationExecuted"])
        self.assertFalse(manager["candidateEnablementExecuted"])
        claims = self.decision["claimBoundary"]
        for key in (
            "candidateInstalled",
            "hostExposed",
            "instructionDeliveryProved",
            "behaviorProved",
            "valueProved",
            "wholeCatalogSuitable",
            "crossHostPortabilityProved",
        ):
            self.assertFalse(claims[key])

    def test_isolated_review_root_is_removed(self) -> None:
        cleanup = self.decision["cleanup"]
        self.assertTrue(cleanup["reviewRootRemoved"])
        self.assertTrue(cleanup["repositoryTmpRemovedAfter"])


if __name__ == "__main__":
    unittest.main()
