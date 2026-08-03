import hashlib
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parent.parent
MAPPING = ROOT / "registry/skill-portfolio-candidate-demand-mapping-2026-08-03.json"
COHORT = ROOT / "registry/skill-portfolio-bound-cohort-reconciliation-2026-08-03.json"


class SkillPortfolioCandidateDemandMappingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.mapping = json.loads(MAPPING.read_text(encoding="utf-8"))
        self.cohort = json.loads(COHORT.read_text(encoding="utf-8"))

    def test_source_bindings_are_byte_frozen(self) -> None:
        for binding in self.mapping["sourceBindings"]:
            path = ROOT / binding["path"]
            payload = path.read_bytes()
            self.assertEqual(len(payload), binding["bytes"])
            self.assertEqual(hashlib.sha256(payload).hexdigest(), binding["sha256"])

    def test_all_seventeen_candidates_are_mapped_exactly_once(self) -> None:
        expected = {
            name
            for names in self.cohort["staticDefaultDisabledCandidates"]["bySource"].values()
            for name in names
        }
        rows = self.mapping["candidateMappings"]
        names = [row["name"] for row in rows]
        self.assertEqual(len(rows), 17)
        self.assertEqual(set(names), expected)
        self.assertEqual(len(names), len(set(names)))
        self.assertTrue(all(row["mappingState"] == "static-hypothesis-only" for row in rows))

    def test_each_candidate_has_a_domain_effect_boundary_and_current_comparator(self) -> None:
        for row in self.mapping["candidateMappings"]:
            self.assertTrue(row["domainIds"])
            self.assertTrue(row["effectGroupId"])
            self.assertTrue(row["currentAlternativeIds"])
            self.assertTrue(row["incrementalHypothesis"])
            self.assertTrue(row["boundaryIds"])
            self.assertEqual(row["claimCeiling"], "mapping-and-protocol-design-only")

    def test_scenario_mapping_reuses_only_the_thirteen_governed_scenarios(self) -> None:
        allowed = set(self.mapping["scenarioAuthority"]["scenarioIds"])
        self.assertEqual(len(allowed), 13)
        for row in self.mapping["candidateMappings"]:
            self.assertTrue(set(row["scenarioIds"]).issubset(allowed))
        domain_only = [row["name"] for row in self.mapping["candidateMappings"] if not row["scenarioIds"]]
        self.assertEqual(domain_only, ["json-canvas", "obsidian-bases", "obsidian-markdown"])

    def test_eight_effect_groups_cover_all_candidates_without_composition_attribution(self) -> None:
        groups = self.mapping["effectGroups"]
        self.assertEqual(len(groups), 8)
        group_ids = {group["id"] for group in groups}
        self.assertEqual(len(group_ids), 8)
        mapped_group_ids = {row["effectGroupId"] for row in self.mapping["candidateMappings"]}
        self.assertEqual(mapped_group_ids, group_ids)
        for group in groups:
            self.assertTrue(group["oracleDimensions"])
            self.assertEqual(group["comparisonOrder"], "native-or-current-first-then-one-candidate-arm")
            self.assertFalse(group["compositionArmEligible"])

    def test_domain_and_scenario_absence_are_not_promoted_to_residual_gaps(self) -> None:
        coverage = self.mapping["coverageInterpretation"]
        self.assertFalse(coverage["candidateSetCoversEveryPortfolioDomain"])
        self.assertFalse(coverage["candidateSetCoversEveryGovernedScenario"])
        self.assertFalse(coverage["unmappedDomainOrScenarioIsResidualGap"])
        self.assertFalse(coverage["newScenarioAuthorizedByMapping"])

    def test_next_gate_stays_zero_execution_and_inactive(self) -> None:
        gate = self.mapping["nextGate"]
        self.assertTrue(gate["mappingCompleteWithinSeventeenCandidateSet"])
        self.assertTrue(gate["effectGroupFixtureDesignEligible"])
        self.assertFalse(gate["candidateInstallationEligible"])
        self.assertFalse(gate["candidateExecutionEligible"])
        self.assertFalse(gate["modelDispatchEligible"])
        self.assertFalse(gate["userManualTestRequiredNow"])
        self.assertFalse(gate["selfAuthoredResidualGapEligible"])
        for value in self.mapping["claimBoundary"].values():
            self.assertFalse(value)


if __name__ == "__main__":
    unittest.main()
