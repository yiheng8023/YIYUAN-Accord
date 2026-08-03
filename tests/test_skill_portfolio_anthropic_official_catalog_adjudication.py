import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parent.parent
DECISION = (
    ROOT
    / "registry/skill-portfolio-anthropic-official-catalog-adjudication-2026-08-03.json"
)


class SkillPortfolioAnthropicOfficialCatalogAdjudicationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.decision = json.loads(DECISION.read_text(encoding="utf-8"))

    def test_exact_current_official_source_is_bound(self) -> None:
        source = self.decision["source"]
        self.assertEqual(source["repository"], "anthropics/skills")
        self.assertEqual(source["commit"], "b29e7cf65e5cb78a5ac33d582270551bc74a14eb")
        self.assertEqual(source["tree"], "a87780349fa9dc5c65c9a11dcc7151ec297f21a1")
        self.assertTrue(source["remoteMainMatchesPin"])
        self.assertFalse(source["thirdPartyCodeExecuted"])

    def test_eighteen_skill_files_are_seventeen_plugin_skills_plus_template(self) -> None:
        catalog = self.decision["catalogSurface"]
        self.assertEqual(catalog["skillMdPathCount"], 18)
        self.assertEqual(catalog["pluginSkillCount"], 17)
        self.assertEqual(catalog["templateScaffoldingCount"], 1)
        self.assertFalse(catalog["managerVisibleCountEqualsAdmissibleCapabilityCount"])
        items = {item["name"]: item for item in self.decision["items"]}
        self.assertEqual(items["template-skill"]["disposition"], "scaffolding-not-capability")

    def test_repository_file_total_reconciles_with_itemized_payloads(self) -> None:
        source = self.decision["source"]
        catalog = self.decision["catalogSurface"]
        self.assertEqual(catalog["itemizedPayloadFileCount"], 406)
        self.assertEqual(catalog["repositorySupportFileCount"], 5)
        self.assertEqual(
            catalog["repositorySupportFiles"],
            [
                ".claude-plugin/marketplace.json",
                ".gitignore",
                "README.md",
                "THIRD_PARTY_NOTICES.md",
                "spec/agent-skills-spec.md",
            ],
        )
        self.assertEqual(
            sum(item["fileCount"] for item in self.decision["items"]),
            catalog["itemizedPayloadFileCount"],
        )
        self.assertEqual(
            catalog["itemizedPayloadFileCount"] + catalog["repositorySupportFileCount"],
            source["fileCount"],
        )

    def test_license_classes_block_blanket_catalog_install(self) -> None:
        licenses = self.decision["licenseClasses"]
        self.assertEqual(licenses["apache20SkillCount"], 12)
        self.assertEqual(licenses["sourceAvailableRestrictedSkillCount"], 4)
        self.assertEqual(licenses["missingExplicitSkillLicenseCount"], 1)
        self.assertEqual(licenses["unlicensedTemplateCount"], 1)
        self.assertFalse(licenses["wholeCatalogInstallEligible"])

    def test_restricted_document_skills_use_existing_official_routes(self) -> None:
        items = {item["name"]: item for item in self.decision["items"]}
        for name in ("docx", "pdf", "pptx", "xlsx"):
            self.assertEqual(
                items[name]["disposition"],
                "official-runtime-route-license-restricted-no-cc-install",
            )
            self.assertTrue(items[name]["currentCodexOfficialRouteVisible"])
            self.assertTrue(items[name]["claudeOfficialPluginRouteDeclared"])

    def test_only_one_low_dependency_item_reaches_manager_candidate(self) -> None:
        items = {item["name"]: item for item in self.decision["items"]}
        candidates = [
            item["name"]
            for item in self.decision["items"]
            if item["disposition"] == "manager-install-candidate-default-disabled"
        ]
        self.assertEqual(candidates, ["internal-comms"])
        self.assertEqual(items["internal-comms"]["executableLikeFileCount"], 0)
        self.assertEqual(items["internal-comms"]["licenseClass"], "Apache-2.0")
        self.assertTrue(items["internal-comms"]["taskTimeAccountDataGateRequired"])

    def test_overlap_dependency_and_license_holds_are_not_candidate_failures(self) -> None:
        items = {item["name"]: item for item in self.decision["items"]}
        self.assertEqual(
            items["skill-creator"]["disposition"],
            "current-official-system-route-no-duplicate",
        )
        self.assertEqual(
            items["webapp-testing"]["disposition"],
            "current-native-installed-browser-route-no-duplicate",
        )
        self.assertEqual(
            items["doc-coauthoring"]["disposition"],
            "hold-no-explicit-skill-license",
        )
        self.assertTrue(all(not item["candidateFailure"] for item in self.decision["items"]))

    def test_no_install_or_activation_claim_is_made(self) -> None:
        manager = self.decision["managerBoundary"]
        self.assertFalse(manager["sourceRegistrationExecuted"])
        self.assertFalse(manager["candidateInstallationExecuted"])
        self.assertFalse(manager["hostEnablementChanged"])
        self.assertFalse(manager["wholeCatalogInstallEligible"])
        for value in self.decision["claimBoundary"].values():
            self.assertFalse(value)


if __name__ == "__main__":
    unittest.main()
