import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parent.parent
RECONCILIATION = (
    ROOT / "registry/skill-portfolio-bound-cohort-reconciliation-2026-08-03.json"
)


class SkillPortfolioBoundCohortReconciliationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.document = json.loads(RECONCILIATION.read_text(encoding="utf-8"))

    def test_all_nine_bound_sources_have_a_gate_without_claiming_itemized_coverage(self) -> None:
        coverage = self.document["sourceGateCoverage"]
        self.assertEqual(coverage["boundSourceCount"], 9)
        self.assertEqual(coverage["sourcesWithCurrentGateRecord"], 9)
        self.assertEqual(coverage["preflightSkillMdPathCount"], 363)
        self.assertEqual(coverage["exactItemizedSourceCount"], 4)
        self.assertEqual(coverage["representativeSourceCount"], 3)
        self.assertEqual(coverage["deepSystemGateSourceCount"], 2)
        self.assertFalse(coverage["allSkillPathsItemized"])
        self.assertFalse(coverage["ecosystemCompletenessProved"])

    def test_static_default_disabled_candidate_set_is_exact_and_unique(self) -> None:
        candidates = self.document["staticDefaultDisabledCandidates"]
        expected_by_source = {
            "kepano/obsidian-skills": [
                "json-canvas",
                "obsidian-bases",
                "obsidian-markdown",
            ],
            "phuryn/pm-skills": [
                "strategy-red-team",
                "interview-script",
                "opportunity-solution-tree",
            ],
            "coreyhaines31/marketingskills": [
                "copywriting",
                "copy-editing",
                "customer-research",
            ],
            "anthropics/skills": ["internal-comms"],
            "addyosmani/agent-skills": [
                "ci-cd-and-automation",
                "deprecation-and-migration",
                "documentation-and-adrs",
                "source-driven-development",
            ],
            "JimLiu/baoyu-skills": [
                "baoyu-article-illustrator",
                "baoyu-cover-image",
                "baoyu-infographic",
            ],
        }
        self.assertEqual(candidates["bySource"], expected_by_source)
        flattened = [
            name
            for source_candidates in candidates["bySource"].values()
            for name in source_candidates
        ]
        self.assertEqual(candidates["count"], 17)
        self.assertEqual(len(flattened), 17)
        self.assertEqual(len(set(flattened)), 17)

    def test_candidate_selection_is_not_installation_or_value_evidence(self) -> None:
        state = self.document["lifecycleState"]
        self.assertEqual(state["managerRepositoryRegistrations"], 1)
        self.assertEqual(state["managerCandidateRows"], 0)
        self.assertEqual(state["candidateInstallations"], 0)
        self.assertEqual(state["candidateEnablements"], 0)
        self.assertEqual(state["candidateExecutions"], 0)
        self.assertEqual(state["behaviorOrValueProofs"], 0)
        self.assertFalse(state["atomicDefaultDisabledManagerInstallProved"])

    def test_no_candidate_is_promoted_from_the_three_held_sources(self) -> None:
        held = self.document["sourcesWithoutStaticManagerCandidates"]
        self.assertEqual(
            held,
            {
                "K-Dense-AI/scientific-agent-skills": "representative-item-closure-incomplete",
                "mvanhorn/last30days-skill": "deep-executable-external-data-and-host-lifecycle-review",
                "OthmanAdi/planning-with-files": "split-mechanism-comparison-full-system-held",
            },
        )

    def test_next_stage_is_zero_execution_mapping_not_more_untargeted_discovery(self) -> None:
        gate = self.document["nextStageGate"]
        self.assertTrue(gate["boundedCohortSourceGateReconciliationComplete"])
        self.assertTrue(gate["zeroExecutionDemandMappingEligible"])
        self.assertTrue(gate["zeroExecutionComparisonProtocolPreparationEligible"])
        self.assertFalse(gate["moreUntargetedCandidateNameDiscoveryAuthorized"])
        self.assertFalse(gate["liveBehaviorExperimentEligible"])
        self.assertFalse(gate["candidateInstallationEligible"])
        self.assertFalse(gate["selfAuthoredResidualGapEligible"])
        self.assertFalse(gate["hardStandardPromotionEligible"])

    def test_main_process_and_claim_boundaries_remain_unchanged(self) -> None:
        self.assertFalse(self.document["decision"]["planChangeRequired"])
        self.assertFalse(self.document["decision"]["processChangeRequired"])
        self.assertFalse(self.document["decision"]["acceptanceChangeRequired"])
        for value in self.document["claimBoundary"].values():
            self.assertFalse(value)


if __name__ == "__main__":
    unittest.main()
