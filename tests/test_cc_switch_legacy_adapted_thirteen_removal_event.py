import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parent.parent
EVENT = ROOT / "registry/cc-switch-legacy-adapted-thirteen-removal-event-2026-08-02.json"


class CcSwitchLegacyAdaptedThirteenRemovalEventTests(unittest.TestCase):
    def setUp(self) -> None:
        self.event = json.loads(EVENT.read_text(encoding="utf-8"))

    def test_live_manager_transaction_is_distinct_from_preview(self) -> None:
        self.assertEqual(self.event["status"], "verified-live-manager-transaction")
        self.assertEqual(self.event["execution"]["managerCommand"], "uninstall_skill_unified")
        self.assertFalse(self.event["execution"]["directDatabaseWrite"])
        self.assertEqual(self.event["execution"]["canary"], "local:review")
        self.assertTrue(self.event["execution"]["stopOnFirstFailure"])

    def test_exact_thirteen_have_manager_backups_and_are_absent(self) -> None:
        outcomes = self.event["outcomes"]
        self.assertEqual(len(outcomes), 13)
        self.assertTrue(all(item["managerSuccess"] for item in outcomes))
        self.assertTrue(all(item["backupVerified"] for item in outcomes))
        self.assertEqual(self.event["postState"]["databaseSkillRows"], 42)
        self.assertEqual(self.event["postState"]["cohortRowsPresent"], 0)
        self.assertEqual(self.event["postState"]["cohortPathsPresentAcrossFourRoots"], 0)
        self.assertEqual(self.event["postState"]["brokenConsumerLinks"], 0)

    def test_excluded_upstream_and_first_party_sentinels_survived(self) -> None:
        post = self.event["postState"]
        self.assertEqual(post["sourceAttributedMattRows"], 22)
        self.assertEqual(post["sameNameMattUpstreamsPresent"], 6)
        self.assertEqual(post["firstPartyPhysicalConsumerSkillsPresent"], 3)
        self.assertTrue(post["agentsCompatibilityRootPresent"])
        self.assertTrue(post["traeOwnedRootsPresent"])

    def test_temporary_transaction_surfaces_were_removed(self) -> None:
        cleanup = self.event["cleanup"]
        self.assertTrue(cleanup["debugPortClosed"])
        self.assertTrue(cleanup["standardCcSwitchRestarted"])
        self.assertTrue(cleanup["temporaryBridgeRemoved"])
        self.assertTrue(cleanup["officialSourceReviewRootRemoved"])
        self.assertTrue(cleanup["externalRecoverySnapshotRemoved"])

    def test_claims_remain_narrow(self) -> None:
        claims = self.event["claimBoundary"]
        self.assertTrue(claims["uninstallExecuted"])
        self.assertTrue(claims["postStateProved"])
        self.assertFalse(claims["hostReloadProved"])
        self.assertFalse(claims["remainingPortfolioValueProved"])
        self.assertFalse(claims["replacementAdmissionProved"])


if __name__ == "__main__":
    unittest.main()
