import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parent.parent
EVIDENCE = ROOT / "registry/skill-portfolio-exact-acquisition-static-preflight-2026-08-02.json"


class SkillPortfolioExactAcquisitionStaticPreflightTests(unittest.TestCase):
    def setUp(self) -> None:
        self.evidence = json.loads(EVIDENCE.read_text(encoding="utf-8"))
        self.sources = self.evidence["sources"]

    def test_all_nine_sources_are_exact_clean_and_non_active(self) -> None:
        self.assertEqual(len(self.sources), 9)
        self.assertEqual(self.evidence["status"], "exact-acquisition-complete-static-review-open")
        for source in self.sources:
            with self.subTest(source=source["id"]):
                self.assertTrue(source["headMatchesPin"])
                self.assertEqual(source["worktreeStatusRows"], 0)
                self.assertEqual(len(source["commit"]), 40)
                self.assertEqual(len(source["tree"]), 40)
                self.assertGreater(source["inventory"]["skillMdPathCount"], 0)

    def test_batch_timeouts_are_not_candidate_failures(self) -> None:
        batches = self.evidence["transportBatches"]
        self.assertEqual([batch["result"] for batch in batches], ["completed", "observer-timeout", "observer-timeout"])
        self.assertTrue(all(batch["candidateFailureCount"] == 0 for batch in batches))
        self.assertTrue(all(batch["postTimeoutIndividualIntegrityProved"] for batch in batches[1:]))

    def test_static_signals_do_not_become_admission(self) -> None:
        self.assertEqual(self.evidence["executionCounters"]["thirdPartyScriptExecutions"], 0)
        self.assertEqual(self.evidence["executionCounters"]["modelRequests"], 0)
        self.assertEqual(self.evidence["executionCounters"]["ccSwitchMutations"], 0)
        self.assertEqual(self.evidence["executionCounters"]["activeSkillRootWrites"], 0)
        self.assertTrue(all(not value for value in self.evidence["claimBoundary"].values()))

    def test_collisions_are_bound_for_skill_level_review(self) -> None:
        collisions = self.evidence["nameCollisions"]
        self.assertEqual(
            set(collisions["crossSource"]),
            {"docx", "marketing-ideas", "pdf", "pptx", "xlsx"},
        )
        self.assertEqual(
            set(collisions["currentCcSwitch"]),
            {
                "ci-cd-and-automation",
                "deprecation-and-migration",
                "observability-and-instrumentation",
                "pdf",
                "performance-optimization",
                "shipping-and-launch",
            },
        )


if __name__ == "__main__":
    unittest.main()
