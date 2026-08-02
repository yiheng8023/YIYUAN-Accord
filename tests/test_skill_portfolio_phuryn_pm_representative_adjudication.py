import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parent.parent
DECISION = ROOT / "registry/skill-portfolio-phuryn-pm-representative-adjudication-2026-08-03.json"


class SkillPortfolioPhurynPmRepresentativeAdjudicationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.decision = json.loads(DECISION.read_text(encoding="utf-8"))

    def test_exact_source_object_and_license_are_bound(self) -> None:
        source = self.decision["source"]
        self.assertEqual(source["repository"], "phuryn/pm-skills")
        self.assertEqual(source["commit"], "18468a95b427e70e258b51389796367c6f684e7d")
        self.assertEqual(source["tree"], "514548cbf646ce42fb9ea9a8cc901f05373ab2ff")
        self.assertEqual(source["license"], "MIT")
        self.assertEqual(source["licenseSha256"], "a2c922f9b81b4f40347ddfa79c38eda0f1278b5a6d108bd4099b4da254c774ee")
        self.assertTrue(source["gitObjectClosureAvailable"])
        self.assertFalse(source["checkoutMaterialized"])
        self.assertFalse(source["payloadModified"])

    def test_review_is_representative_not_whole_catalog_admission(self) -> None:
        cohort = self.decision["cohort"]
        self.assertEqual(cohort["sourceSkillCount"], 68)
        self.assertEqual(cohort["pluginFamilyCount"], 9)
        self.assertEqual(cohort["reviewedSkillCount"], 13)
        self.assertEqual(len(self.decision["representativeSkills"]), 13)
        self.assertEqual(sum(cohort["familyCounts"].values()), 68)
        self.assertFalse(cohort["wholeCatalogAdmissionUnit"])

    def test_only_three_low_dependency_methods_advance_to_comparison(self) -> None:
        items = {item["name"]: item for item in self.decision["representativeSkills"]}
        self.assertEqual(
            {name for name, item in items.items() if item["disposition"] == "manager-install-candidate-default-disabled-behavior-comparison-required"},
            {"strategy-red-team", "interview-script", "opportunity-solution-tree"},
        )
        for name in ("strategy-red-team", "interview-script", "opportunity-solution-tree"):
            self.assertEqual(items[name]["bundledExecutableFileCount"], 0)
            self.assertEqual(items[name]["dependencyFiles"], [])

    def test_dependencies_overlap_and_high_stakes_routes_hold(self) -> None:
        items = {item["name"]: item for item in self.decision["representativeSkills"]}
        self.assertEqual(items["intended-vs-implemented"]["disposition"], "composition-candidate-dependency-review-required")
        self.assertEqual(items["shipping-artifacts"]["disposition"], "hold-plugin-command-dependency-incomplete")
        self.assertEqual(items["prioritize-assumptions"]["disposition"], "hold-missing-skill-dependency")
        self.assertEqual(items["market-sizing"]["disposition"], "hold-existing-official-runtime-overlap")
        for name in ("draft-nda", "privacy-policy"):
            self.assertEqual(items[name]["disposition"], "hold-high-stakes-domain-review")

    def test_templates_and_overlapping_methods_remain_reference_only(self) -> None:
        items = {item["name"]: item for item in self.decision["representativeSkills"]}
        for name in ("pre-mortem", "create-prd", "test-scenarios", "user-stories"):
            self.assertEqual(items[name]["disposition"], "reference-only-overlap-or-opinionated-template")

    def test_no_install_enablement_or_behavior_claim_is_made(self) -> None:
        manager = self.decision["managerBoundary"]
        self.assertFalse(manager["repositoryRegistrationAuthorizedByThisReview"])
        self.assertFalse(manager["candidateInstallationExecuted"])
        self.assertFalse(manager["candidateEnablementExecuted"])
        claims = self.decision["claimBoundary"]
        for key in (
            "managerRepositoryRegistered",
            "candidateInstalled",
            "hostExposed",
            "invocationProved",
            "instructionDeliveryProved",
            "behaviorProved",
            "valueProved",
            "wholeCatalogSuitable",
        ):
            self.assertFalse(claims[key])

    def test_exact_process_root_cleanup_is_recorded(self) -> None:
        cleanup = self.decision["cleanup"]
        self.assertEqual(cleanup["reviewRoot"], "C:\\tmp\\aah-pm-skills-review-20260803")
        self.assertTrue(cleanup["aclRepairRequired"])
        self.assertTrue(cleanup["reviewRootRemoved"])
        self.assertFalse(cleanup["repositoryTmpExistsAfter"])


if __name__ == "__main__":
    unittest.main()
