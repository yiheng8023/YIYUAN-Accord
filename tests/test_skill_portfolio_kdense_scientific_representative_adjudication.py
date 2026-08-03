import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parent.parent
DECISION = (
    ROOT
    / "registry/skill-portfolio-kdense-scientific-representative-adjudication-2026-08-03.json"
)


class SkillPortfolioKDenseScientificRepresentativeAdjudicationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.decision = json.loads(DECISION.read_text(encoding="utf-8"))

    def test_exact_preflight_source_and_stable_release_are_bound(self) -> None:
        source = self.decision["source"]
        self.assertEqual(source["repository"], "K-Dense-AI/scientific-agent-skills")
        self.assertEqual(source["commit"], "ad21a3868923628330734375dddbf7b86ea84222")
        self.assertEqual(source["tree"], "30fbe6249859378466dde41fe13200ad3766c142")
        self.assertEqual(source["stableTag"], "v2.62.0")
        self.assertTrue(source["stableTagMatchesPin"])
        self.assertFalse(source["remoteMainCurrentReverified"])

    def test_large_catalog_remains_a_representative_review_only_surface(self) -> None:
        inventory = self.decision["catalogSurface"]
        self.assertEqual(inventory["skillMdPathCount"], 158)
        self.assertEqual(inventory["uniqueDeclaredNames"], 158)
        self.assertEqual(inventory["fileCount"], 2383)
        self.assertEqual(inventory["bytes"], 271853718)
        self.assertEqual(inventory["scriptLikeFileCount"], 668)
        self.assertEqual(inventory["scriptBearingSkillPaths"], 101)
        self.assertFalse(inventory["wholeCatalogReviewComplete"])

    def test_representative_cohort_does_not_masquerade_as_itemized_review(self) -> None:
        cohort = self.decision["representativeCohort"]
        self.assertEqual(cohort["declaredSampleCount"], 16)
        self.assertEqual(cohort["exactSkillBodyReviewed"], ["literature-review"])
        self.assertEqual(len(cohort["catalogLevelOnly"]), 15)
        self.assertFalse(cohort["allSampleBodiesExactBound"])
        self.assertFalse(cohort["representativeBehaviorGeneralizableToCatalog"])

    def test_exact_literature_review_is_dependency_heavy_composition(self) -> None:
        sample = self.decision["exactSkillBodyEvidence"]["literature-review"]
        self.assertEqual(sample["commit"], self.decision["source"]["commit"])
        self.assertEqual(sample["license"], "MIT")
        self.assertIn("parallel-cli", sample["requiredExternalTools"])
        self.assertIn("scientific-schematics", sample["skillDependencies"])
        self.assertTrue(sample["mandatoryGeneratedFigures"])
        self.assertEqual(sample["disposition"], "dependency-heavy-composition-only")
        self.assertFalse(sample["byteIdentityProved"])

    def test_security_scanner_findings_are_not_promoted_to_verdicts(self) -> None:
        security = self.decision["upstreamSecurityGovernance"]
        self.assertEqual(security["scannerEvidenceAuthority"], "review-signal-only")
        self.assertEqual(security["triagedScan"]["criticalFindings"], 33)
        self.assertEqual(security["triagedScan"]["highFindings"], 8)
        self.assertEqual(security["triagedScan"]["reportedCriticalPlusHighArithmetic"], 41)
        self.assertEqual(security["triagedScan"]["triageNarrativeCriticalAndHighCount"], 40)
        self.assertFalse(security["triagedScan"]["severityCountReconciliationComplete"])
        self.assertEqual(
            security["triagedScan"]["criticalAndHighSurvivingVerificationClaimedByUpstream"],
            0,
        )
        self.assertFalse(security["triagedScan"]["harnessIndependentFindingVerificationRun"])
        self.assertTrue(security["realIssuesAndFixesDocumented"])
        self.assertFalse(security["securityCertificationProved"])

    def test_no_default_disabled_candidate_is_promoted_without_item_closure(self) -> None:
        decision = self.decision["decision"]
        self.assertEqual(decision["managerInstallCandidatesDefaultDisabled"], [])
        self.assertFalse(decision["wholeCatalogInstallEligible"])
        self.assertTrue(decision["itemLevelLicenseDependencyAndSecurityClosureRequired"])
        self.assertEqual(
            decision["officialRuntimeCollisionComparison"],
            ["docx", "pdf", "pptx", "xlsx"],
        )
        self.assertEqual(
            decision["taskTimeHighBoundaryOnly"],
            ["clinical-decision-support", "opentrons-integration"],
        )

    def test_transport_block_is_not_candidate_failure_and_cleanup_is_exact(self) -> None:
        acquisition = self.decision["acquisitionAttempt"]
        self.assertEqual(acquisition["result"], "blocked-external")
        self.assertFalse(acquisition["candidateFailure"])
        self.assertFalse(acquisition["targetCommitFetchedThisTurn"])
        cleanup = self.decision["cleanup"]
        self.assertTrue(cleanup["reviewRootRemoved"])
        self.assertTrue(cleanup["repositoryTmpRemovedAfter"])

    def test_no_install_execution_or_runtime_claim_is_made(self) -> None:
        for value in self.decision["claimBoundary"].values():
            self.assertFalse(value)


if __name__ == "__main__":
    unittest.main()
