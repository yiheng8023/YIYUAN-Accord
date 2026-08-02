import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parent.parent
PREVIEW = ROOT / "registry/cc-switch-legacy-adapted-thirteen-removal-preview-2026-08-02.json"


class CcSwitchLegacyAdaptedThirteenRemovalPreviewTests(unittest.TestCase):
    def setUp(self) -> None:
        self.preview = json.loads(PREVIEW.read_text(encoding="utf-8"))

    def test_preview_targets_only_thirteen_exact_derivatives(self) -> None:
        cohort = self.preview["cohort"]
        self.assertEqual(len(cohort), 13)
        self.assertEqual(cohort[0]["name"], "review")
        self.assertTrue(all(item["id"] == f"local:{item['name']}" for item in cohort))
        self.assertTrue(all(item["legacyTreeExact"] for item in cohort))
        self.assertNotIn("grill-with-docs", {item["name"] for item in cohort})
        self.assertNotIn("tdd", {item["name"] for item in cohort})

    def test_recovery_and_manager_semantics_are_bound(self) -> None:
        recovery = self.preview["recoverySnapshot"]
        self.assertEqual(recovery["archiveSha256"], "e162d944bb01bcfc86b82ffe35b4ed024413b924361f865c08626a2fd3131820")
        self.assertTrue(recovery["secretScanPassed"])
        self.assertFalse(recovery["rawDatabaseCopied"])
        manager = self.preview["managerSemantics"]
        self.assertEqual(manager["version"], "3.19.1")
        self.assertEqual(manager["uninstallCommand"], "uninstall_skill_unified")
        self.assertTrue(manager["createsBackupBeforeFilesystemRemoval"])
        self.assertFalse(manager["directDatabaseWriteRequired"])

    def test_transaction_is_sequential_reversible_and_not_yet_executed(self) -> None:
        transaction = self.preview["transaction"]
        self.assertEqual(transaction["canary"], "local:review")
        self.assertTrue(transaction["stopOnFirstFailure"])
        self.assertTrue(transaction["restoreCompletedItemsInReverseOrder"])
        self.assertTrue(transaction["cleanBrokenAgentsLinksOnlyAfterFullManagerSuccess"])
        self.assertFalse(self.preview["claimBoundary"]["uninstallExecuted"])
        self.assertFalse(self.preview["claimBoundary"]["postStateProved"])


if __name__ == "__main__":
    unittest.main()
