import hashlib
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parent.parent
EVENT = ROOT / "registry/mattpocock-skills-v1.2.2-manifest-update-preview-2026-08-06.json"


def canonical_digest(value: object) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


class MattPocockSkillsV122ManifestUpdatePreviewEventTests(unittest.TestCase):
    def setUp(self) -> None:
        self.event = json.loads(EVENT.read_text(encoding="utf-8"))
        self.report_path = ROOT / self.event["report"]
        self.report = json.loads(self.report_path.read_text(encoding="utf-8"))

    def test_event_binds_exact_report_and_release_authority(self) -> None:
        self.assertEqual(self.event["source"]["releaseTag"], "v1.2.2")
        self.assertEqual(
            self.event["source"]["releaseCommit"],
            "8b36d4fb2635b3c21998dcd8144439c9e5ba7302",
        )
        self.assertTrue(self.event["source"]["tagObjectPeelsToReleaseCommit"])
        self.assertEqual(
            hashlib.sha256(self.report_path.read_bytes()).hexdigest(),
            self.event["reportFileSha256"],
        )
        embedded = dict(self.report)
        embedded_digest = embedded.pop("reportSha256")
        self.assertEqual(canonical_digest(embedded), embedded_digest)
        self.assertEqual(embedded_digest, self.event["reportSha256"])
        self.assertEqual(
            self.report["sourceProjectionSha256"],
            self.event["sourceProjectionSha256"],
        )

    def test_manifest_manager_and_consumer_counts_remain_distinct(self) -> None:
        self.assertEqual(self.report["discovery"]["promotedCount"], 25)
        self.assertEqual(self.report["discovery"]["recursiveSkillCount"], 35)
        self.assertEqual(self.report["liveManager"]["sourceRowCount"], 22)
        self.assertEqual(self.event["transition"]["retainOrReplaceCount"], 21)
        self.assertEqual(len(self.event["transition"]["add"]), 4)
        self.assertEqual(self.event["transition"]["remove"], ["writing-great-skills"])
        self.assertEqual(
            self.event["consumerTopology"]["commonAgentsRoot"]["directDirectoryCount"],
            13,
        )
        self.assertFalse(
            self.event["consumerTopology"]["singleManagerRevisionClosureProved"]
        )

    def test_preview_does_not_upgrade_lifecycle_claims(self) -> None:
        self.assertFalse(self.report["transaction"]["executionEligible"])
        self.assertEqual(self.report["executionCounters"]["managerMutations"], 0)
        self.assertEqual(self.report["executionCounters"]["consumerWrites"], 0)
        self.assertFalse(self.event["decision"]["executionAuthorized"])
        self.assertFalse(self.event["decision"]["ccSwitchUpdateAuthorized"])
        self.assertFalse(self.event["decision"]["consumerReconciliationAuthorized"])
        for field in (
            "loaderExposureProved",
            "instructionDeliveryProved",
            "invocationProved",
            "behaviorProved",
            "valueProved",
            "crossHostPortabilityProved",
            "updateSuitabilityProved",
        ):
            self.assertFalse(self.event["claimBoundary"][field])


if __name__ == "__main__":
    unittest.main()
