import json
from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parent.parent
POOL = ROOT / "registry/skill-portfolio-inactive-source-candidate-pool-2026-08-02.json"


class SkillPortfolioInactiveSourceCandidatePoolTests(unittest.TestCase):
    def setUp(self) -> None:
        self.pool = json.loads(POOL.read_text(encoding="utf-8"))
        self.sources = self.pool["sources"]

    def test_pool_is_bounded_inactive_and_source_preserving(self) -> None:
        self.assertEqual(self.pool["schema"], 1)
        self.assertEqual(len(self.sources), 22)
        self.assertEqual(self.pool["state"], "inactive-source-screening")
        self.assertFalse(self.pool["authorityBoundary"]["installAuthorized"])
        self.assertFalse(self.pool["authorityBoundary"]["enableAuthorized"])
        self.assertFalse(self.pool["authorityBoundary"]["executeAuthorized"])
        self.assertEqual(
            self.pool["payloadPolicy"],
            {
                "ownership": "upstream",
                "bodyTreatment": "exact-upstream-unchanged",
                "modifiedDerivativeRequiresSeparateIdentity": True,
            },
        )

    def test_sources_have_exact_identity_and_explicit_disposition(self) -> None:
        ids = [source["id"] for source in self.sources]
        self.assertEqual(len(ids), len(set(ids)))
        for source in self.sources:
            with self.subTest(source=source["id"]):
                self.assertRegex(source["revision"], re.compile(r"^[0-9a-f]{40}$"))
                self.assertTrue(source["url"].startswith("https://github.com/"))
                self.assertIn(
                    source["disposition"],
                    {
                        "existing-official-or-plugin-route",
                        "installed-upstream-delta-review",
                        "exact-acquisition-review",
                        "discovery-index-only",
                        "system-or-manager-review-only",
                    },
                )

    def test_exact_acquisition_cohort_is_small_and_excludes_aggregates(self) -> None:
        cohort = set(self.pool["nextExactAcquisitionCohort"])
        by_id = {source["id"]: source for source in self.sources}
        self.assertEqual(len(cohort), 9)
        self.assertTrue(cohort <= set(by_id))
        self.assertTrue(
            all(by_id[source_id]["disposition"] == "exact-acquisition-review" for source_id in cohort)
        )
        self.assertTrue(
            all(by_id[source_id]["tree"]["skillMdCount"] <= 158 for source_id in cohort)
        )
        self.assertNotIn("github:ComposioHQ/awesome-claude-skills", cohort)
        self.assertNotIn("github:sickn33/agentic-awesome-skills", cohort)
        self.assertNotIn("github:alirezarezvani/claude-skills", cohort)

    def test_live_inventory_does_not_upgrade_lifecycle_evidence(self) -> None:
        live = self.pool["liveInventory"]
        self.assertEqual(live["ccSwitch"]["version"], "3.19.1")
        self.assertEqual(live["ccSwitch"]["databaseSkillRows"], 55)
        self.assertEqual(live["ccSwitch"]["sourceAttributedMattRows"], 22)
        self.assertEqual(live["ccSwitch"]["localOrUnattributedRows"], 33)
        self.assertEqual(live["codexOfficialPlugins"]["superpowers"], "6.2.0")
        for claim in self.pool["claimBoundary"].values():
            self.assertFalse(claim)

    def test_old_adapted_release_does_not_authorize_name_based_deletion(self) -> None:
        legacy = self.pool["legacyCollisionBoundary"]
        self.assertEqual(legacy["deprecatedAdaptedSkillCount"], 19)
        self.assertFalse(legacy["sameNameLiveSkillAutoRemovalAuthorized"])
        self.assertEqual(
            legacy["requiredDisambiguation"],
            ["source-lineage", "exact-revision", "payload-digest", "manager-row-identity"],
        )


if __name__ == "__main__":
    unittest.main()
