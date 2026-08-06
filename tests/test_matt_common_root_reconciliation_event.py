from __future__ import annotations

import hashlib
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parent.parent
EVENT = ROOT / "registry/matt-common-root-reconciliation-event-2026-08-06.json"


class MattCommonRootReconciliationEventTests(unittest.TestCase):
    def setUp(self) -> None:
        self.event = json.loads(EVENT.read_text(encoding="utf-8"))
        self.report_path = ROOT / self.event["verification"]["postProbeReport"]
        self.report = json.loads(self.report_path.read_text(encoding="utf-8"))

    def test_event_binds_post_reconciliation_no_model_report(self) -> None:
        self.assertEqual(
            self.event["verification"]["postProbeReportFileSha256"],
            hashlib.sha256(self.report_path.read_bytes()).hexdigest(),
        )
        self.assertEqual(
            self.event["verification"]["postProbeReportSha256"],
            self.report["reportSha256"],
        )
        self.assertEqual("pass", self.report["status"])
        self.assertEqual(0, self.report["requestBoundary"]["threadStartCount"])
        self.assertEqual(0, self.report["requestBoundary"]["turnStartCount"])
        self.assertEqual(0, self.report["requestBoundary"]["modelRequestCount"])
        self.assertTrue(
            self.report["mutationBoundary"]["allObservedSurfacesStable"]
        )

    def test_all_thirteen_collisions_are_removed_from_listing(self) -> None:
        rows = self.report["collisionRows"]
        self.assertEqual(13, len(rows))
        self.assertEqual(
            13,
            sum(row["listingClassification"] == "codex-only" for row in rows),
        )
        self.assertEqual(
            0,
            sum(row["listingClassification"] == "both-listed" for row in rows),
        )
        self.assertEqual(46, self.report["inventory"]["countsByScope"]["user"])

    def test_transaction_preserves_manager_and_recovery_boundaries(self) -> None:
        tx = self.event["transaction"]
        self.assertEqual(
            set(tx["directNames"]),
            {row["name"] for row in self.report["collisionRows"]},
        )
        self.assertEqual(12, tx["retainedLinksInstalled"])
        self.assertEqual(1, tx["retiredCommonRootCopiesRemoved"])
        self.assertEqual(13, tx["recoverableOriginalDirectories"])
        self.assertTrue(tx["commonDirectoryContainerPreserved"])
        self.assertTrue(tx["ccDatabaseSafeExportUnchanged"])
        self.assertTrue(tx["ccSsotTopologyUnchanged"])
        self.assertFalse(tx["ccManagerUpdateIncluded"])
        self.assertFalse(tx["thirdPartyPayloadBodyRewritten"])
        self.assertFalse(self.event["decision"]["mattV122ManagerUpdateExecuted"])
        self.assertFalse(self.event["decision"]["wizardManagerRowPresent"])

    def test_announcement_does_not_replace_release_authority(self) -> None:
        announcement = self.event["authorAnnouncement"]
        self.assertEqual("Matt Pocock", announcement["author"])
        self.assertEqual("v1.2-series-announcement", announcement["classification"])
        self.assertFalse(announcement["isExactPatchReleaseAuthority"])
        self.assertEqual("v1.2.2", self.event["source"]["releaseTag"])


if __name__ == "__main__":
    unittest.main()
