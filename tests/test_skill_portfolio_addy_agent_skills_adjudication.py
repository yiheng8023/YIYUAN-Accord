import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parent.parent
DECISION = (
    ROOT
    / "registry/skill-portfolio-addy-agent-skills-adjudication-2026-08-03.json"
)


class SkillPortfolioAddyAgentSkillsAdjudicationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.decision = json.loads(DECISION.read_text(encoding="utf-8"))

    def test_exact_current_source_is_bound(self) -> None:
        source = self.decision["source"]
        self.assertEqual(source["repository"], "addyosmani/agent-skills")
        self.assertEqual(source["commit"], "7829ffd90d973b6325f5f12f1b1226dcace74443")
        self.assertEqual(source["tree"], "d0d903cfb69e783b05b45c0773ad8a2ec3916a3e")
        self.assertTrue(source["remoteMainMatchesPin"])
        self.assertFalse(source["thirdPartyCodeExecuted"])

    def test_repository_and_skill_root_counts_reconcile(self) -> None:
        catalog = self.decision["catalogSurface"]
        self.assertEqual(catalog["skillCount"], 24)
        self.assertEqual(catalog["lifecycleSkillCount"], 23)
        self.assertEqual(catalog["metaSkillCount"], 1)
        self.assertEqual(catalog["skillRootFileCount"], 28)
        self.assertEqual(catalog["repositorySupportFileCount"], 148)
        self.assertEqual(
            catalog["skillRootFileCount"] + catalog["repositorySupportFileCount"],
            self.decision["source"]["fileCount"],
        )
        self.assertEqual(catalog["repositoryExecutableFileCount"], 7)
        self.assertEqual(catalog["skillRootExecutableFileCount"], 1)

    def test_upstream_quality_evidence_is_bounded(self) -> None:
        quality = self.decision["upstreamQualityEvidence"]
        self.assertEqual(quality["license"], "MIT")
        self.assertEqual(quality["evalCaseFileCount"], 24)
        self.assertEqual(quality["exactCommitSuccessfulCheckCount"], 4)
        self.assertTrue(all(check["conclusion"] == "success" for check in quality["checks"]))
        self.assertEqual(quality["declaredTriggerRank1BaselinePercent"], 86)
        self.assertEqual(quality["ciTriggerRank1FloorPercent"], 80)
        self.assertFalse(quality["behavioralResultsCommitted"])
        self.assertFalse(quality["provesCurrentCrossHostBehaviorOrValue"])

    def test_legacy_source_attributed_derivatives_are_history_only(self) -> None:
        comparison = self.decision["legacyDerivativeComparison"]
        self.assertEqual(comparison["sourceAttributedSkillCount"], 5)
        self.assertEqual(
            [item["name"] for item in comparison["items"]],
            [
                "ci-cd-and-automation",
                "deprecation-and-migration",
                "observability-and-instrumentation",
                "performance-optimization",
                "shipping-and-launch",
            ],
        )
        self.assertTrue(all(not item["byteEqual"] for item in comparison["items"]))
        self.assertFalse(comparison["legacyPayloadRestoredAsAuthority"])

    def test_selective_candidates_are_not_a_whole_catalog_admission(self) -> None:
        decision = self.decision["decision"]
        self.assertEqual(
            decision["managerInstallCandidatesDefaultDisabled"],
            [
                "ci-cd-and-automation",
                "deprecation-and-migration",
                "documentation-and-adrs",
                "source-driven-development",
            ],
        )
        self.assertEqual(
            decision["dependencyCompleteCompositionCandidates"],
            ["observability-and-instrumentation", "performance-optimization"],
        )
        self.assertFalse(decision["wholeCatalogInstallEligible"])
        self.assertTrue(decision["blockedByCurrentInactiveInstallGap"])

    def test_out_of_root_dependencies_and_meta_router_conflict_are_visible(self) -> None:
        catalog = self.decision["catalogSurface"]
        self.assertEqual(catalog["outOfRootReferenceSkillCount"], 11)
        items = {item["name"]: item for item in self.decision["items"]}
        self.assertEqual(
            items["using-agent-skills"]["disposition"],
            "routing-reference-only-conflicts-with-minimal-dynamic-router",
        )
        self.assertEqual(
            items["planning-and-task-breakdown"]["disposition"],
            "current-official-overlap-fixed-plan-mode-and-layout",
        )
        self.assertEqual(
            items["doubt-driven-development"]["disposition"],
            "architecture-input-fresh-review-with-resource-and-route-gates",
        )

    def test_existing_official_and_installed_routes_are_not_duplicated(self) -> None:
        items = {item["name"]: item for item in self.decision["items"]}
        expected = {
            "browser-testing-with-devtools": "current-browser-routes-no-duplicate-mcp-requirement",
            "debugging-and-error-recovery": "current-official-and-managed-overlap-no-duplicate",
            "frontend-ui-engineering": "current-official-design-routes-no-duplicate",
            "security-and-hardening": "current-official-security-plugin-no-duplicate",
            "test-driven-development": "current-official-superpowers-and-managed-overlap-no-duplicate",
        }
        for name, disposition in expected.items():
            self.assertEqual(items[name]["disposition"], disposition)

    def test_no_install_hook_activation_or_runtime_claim_is_made(self) -> None:
        self.assertTrue(all(not item["candidateFailure"] for item in self.decision["items"]))
        for value in self.decision["claimBoundary"].values():
            self.assertFalse(value)


if __name__ == "__main__":
    unittest.main()
