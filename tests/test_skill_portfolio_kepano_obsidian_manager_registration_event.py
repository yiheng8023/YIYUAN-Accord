import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parent.parent
EVENT = ROOT / "registry/skill-portfolio-kepano-obsidian-manager-registration-event-2026-08-02.json"


class SkillPortfolioKepanoObsidianManagerRegistrationEventTests(unittest.TestCase):
    def setUp(self) -> None:
        self.event = json.loads(EVENT.read_text(encoding="utf-8"))

    def test_manager_repository_registration_is_exact_and_non_installing(self) -> None:
        manager = self.event["managerEvent"]
        self.assertEqual(manager["command"], "add_skill_repo")
        self.assertEqual(manager["repositoriesBefore"], 6)
        self.assertEqual(manager["repositoriesAfter"], 7)
        self.assertEqual(manager["repository"], {
            "owner": "kepano", "name": "obsidian-skills", "branch": "main", "enabled": True
        })
        self.assertFalse(manager["candidateInstallationExecuted"])

    def test_discovery_names_match_the_five_reviewed_skills(self) -> None:
        discovery = self.event["discovery"]
        self.assertEqual(discovery["allDiscoverableCount"], 996)
        self.assertEqual(discovery["sourceSkillCount"], 5)
        self.assertEqual(set(discovery["names"]), {
            "defuddle", "json-canvas", "obsidian-bases", "obsidian-cli", "obsidian-markdown"
        })
        self.assertTrue(discovery["reviewedOriginMainMatchedPin"])
        self.assertFalse(discovery["managerExposedCommitOrPayloadDigest"])

    def test_live_installation_and_projection_state_remains_unchanged(self) -> None:
        post = self.event["postState"]
        self.assertEqual(post["databaseSkillRows"], 42)
        self.assertEqual(post["candidateRowsPresent"], 0)
        self.assertEqual(post["candidatePathsAcrossFourRoots"], 0)
        self.assertEqual(post["sourceAttributedMattRows"], 22)

    def test_transaction_surfaces_are_cleaned(self) -> None:
        cleanup = self.event["cleanup"]
        self.assertTrue(cleanup["debugPortClosed"])
        self.assertTrue(cleanup["standardCcSwitchRestarted"])
        self.assertTrue(cleanup["temporaryBridgeRemoved"])
        self.assertTrue(cleanup["temporarySourceReviewRootRemoved"])

    def test_claim_boundary_does_not_promote_discovery_to_bytes_or_value(self) -> None:
        claims = self.event["claimBoundary"]
        self.assertTrue(claims["managerRepositoryRegistered"])
        self.assertTrue(claims["managerDiscoveryNamesProved"])
        self.assertFalse(claims["managerDiscoveryPayloadBytesProved"])
        self.assertFalse(claims["candidateInstalled"])
        self.assertFalse(claims["hostExposed"])
        self.assertFalse(claims["behaviorProved"])
        self.assertFalse(claims["valueProved"])


if __name__ == "__main__":
    unittest.main()
