import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parent.parent
DECISION = ROOT / "registry/skill-portfolio-kepano-obsidian-adjudication-2026-08-02.json"


class SkillPortfolioKepanoObsidianAdjudicationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.decision = json.loads(DECISION.read_text(encoding="utf-8"))

    def test_exact_source_and_license_are_bound(self) -> None:
        source = self.decision["source"]
        self.assertEqual(source["repository"], "kepano/obsidian-skills")
        self.assertEqual(source["commit"], "a1dc48e68138490d522c04cbf5822214c6eb1202")
        self.assertEqual(source["tree"], "49d7c3b7f6aa4d266631c886284415d111070941")
        self.assertEqual(source["license"], "MIT")
        self.assertTrue(source["worktreeClean"])
        self.assertFalse(source["payloadModified"])

    def test_three_format_skills_advance_and_two_dependency_skills_hold(self) -> None:
        items = {item["name"]: item for item in self.decision["skills"]}
        self.assertEqual(set(items), {
            "defuddle", "json-canvas", "obsidian-bases", "obsidian-cli", "obsidian-markdown"
        })
        for name in ("json-canvas", "obsidian-bases", "obsidian-markdown"):
            self.assertEqual(items[name]["disposition"], "manager-install-candidate-default-disabled")
            self.assertEqual(items[name]["executableFileCount"], 0)
        for name in ("defuddle", "obsidian-cli"):
            self.assertEqual(items[name]["disposition"], "hold-missing-runtime-dependency")
            self.assertFalse(items[name]["runtimeDependencyPresent"])

    def test_existing_local_vault_skill_is_not_removed_by_overlap(self) -> None:
        overlap = self.decision["currentPortfolioOverlap"]
        self.assertEqual(overlap["currentSkill"], "local:obsidian-vault")
        self.assertEqual(overlap["disposition"], "retain-pending-behavioral-comparison")
        self.assertFalse(overlap["removalAuthorized"])

    def test_manager_limitation_blocks_install_without_transient_activation_authority(self) -> None:
        manager = self.decision["managerBoundary"]
        self.assertTrue(manager["repositoryRegistrationEligible"])
        self.assertTrue(manager["installRequiresCurrentApp"])
        self.assertFalse(manager["atomicDefaultDisabledInstallProved"])
        self.assertFalse(manager["candidateInstallationExecuted"])
        self.assertFalse(manager["transientHostActivationAuthorized"])

    def test_claims_stop_before_behavior_and_value(self) -> None:
        claims = self.decision["claimBoundary"]
        self.assertFalse(claims["managerRepositoryRegistered"])
        self.assertFalse(claims["candidateInstalled"])
        self.assertFalse(claims["hostExposed"])
        self.assertFalse(claims["behaviorProved"])
        self.assertFalse(claims["valueProved"])


if __name__ == "__main__":
    unittest.main()
