import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parent.parent
DECISION = (
    ROOT
    / "registry/skill-portfolio-baoyu-skills-adjudication-2026-08-03.json"
)


class SkillPortfolioBaoyuSkillsAdjudicationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.decision = json.loads(DECISION.read_text(encoding="utf-8"))

    def test_exact_current_source_is_bound(self) -> None:
        source = self.decision["source"]
        self.assertEqual(source["repository"], "JimLiu/baoyu-skills")
        self.assertEqual(source["commit"], "6b7a2e417500561a5ecdd0b168332f4142584617")
        self.assertEqual(source["tree"], "22d34a6f2c157ea249a2e3d0c04b17cd023289b9")
        self.assertTrue(source["remoteMainMatchesPin"])
        self.assertFalse(source["thirdPartyCodeExecuted"])

    def test_plugin_surface_is_separate_from_internal_release_skill(self) -> None:
        catalog = self.decision["catalogSurface"]
        self.assertEqual(catalog["skillMdCount"], 22)
        self.assertEqual(catalog["pluginSkillCount"], 21)
        self.assertEqual(catalog["internalMaintainerSkillCount"], 1)
        self.assertEqual(catalog["repositoryFileCount"], 920)
        self.assertEqual(catalog["scriptBearingSkillCount"], 16)
        self.assertEqual(catalog["testFileCount"], 27)

    def test_selective_candidates_are_native_backend_methods_not_bulk_admission(self) -> None:
        decision = self.decision["decision"]
        self.assertEqual(
            decision["managerInstallCandidatesDefaultDisabled"],
            [
                "baoyu-article-illustrator",
                "baoyu-cover-image",
                "baoyu-infographic",
            ],
        )
        self.assertFalse(decision["wholeCatalogInstallEligible"])
        self.assertTrue(decision["blockedByCurrentInactiveInstallGap"])
        items = {item["name"]: item for item in self.decision["items"]}
        for name in decision["managerInstallCandidatesDefaultDisabled"]:
            self.assertEqual(
                items[name]["disposition"],
                "manager-install-candidate-default-disabled-native-image-backend",
            )
            self.assertEqual(items[name]["scriptLikeFileCount"], 0)

    def test_selective_install_dependency_gaps_are_not_hidden(self) -> None:
        gaps = self.decision["dependencyBoundary"]["selectiveInstallUnboundImports"]
        self.assertEqual(
            gaps,
            {
                "baoyu-comic": ["pdf-lib"],
                "baoyu-compress-image": ["sharp"],
                "baoyu-diagram": ["sharp"],
                "baoyu-slide-deck": ["pdf-lib", "pptxgenjs"],
            },
        )
        items = {item["name"]: item for item in self.decision["items"]}
        self.assertEqual(
            items["baoyu-diagram"]["disposition"],
            "useful-method-selective-install-dependency-gap",
        )
        self.assertEqual(
            items["baoyu-compress-image"]["disposition"],
            "utility-value-dependency-and-replacement-semantics-review",
        )

    def test_high_boundary_capabilities_remain_task_time_only(self) -> None:
        decision = self.decision["decision"]
        self.assertEqual(
            decision["taskTimeHighBoundaryOnly"],
            [
                "baoyu-danger-gemini-web",
                "baoyu-danger-x-to-markdown",
                "baoyu-electron-extract",
                "baoyu-image-gen",
                "baoyu-post-to-wechat",
                "baoyu-post-to-weibo",
                "baoyu-post-to-x",
                "baoyu-url-to-markdown",
                "baoyu-wechat-summary",
                "baoyu-youtube-transcript",
            ],
        )
        items = {item["name"]: item for item in self.decision["items"]}
        self.assertEqual(
            items["baoyu-wechat-summary"]["disposition"],
            "task-time-only-private-data-sandbox-bypass-macos",
        )
        self.assertEqual(
            items["release-skills"]["disposition"],
            "internal-maintainer-skill-not-plugin-candidate",
        )

    def test_remote_ci_observation_failure_is_not_candidate_failure(self) -> None:
        quality = self.decision["upstreamQualityEvidence"]
        self.assertEqual(quality["license"], "MIT")
        self.assertEqual(quality["workflowFileCount"], 2)
        self.assertEqual(quality["testFileCount"], 27)
        self.assertEqual(quality["remoteCheckObservation"], "blocked-external")
        self.assertFalse(quality["candidateFailureFromRemoteCheckObservation"])
        self.assertFalse(quality["behavioralResultsCommitted"])

    def test_no_install_execution_or_runtime_claim_is_made(self) -> None:
        self.assertTrue(all(not item["candidateFailure"] for item in self.decision["items"]))
        for value in self.decision["claimBoundary"].values():
            self.assertFalse(value)


if __name__ == "__main__":
    unittest.main()
