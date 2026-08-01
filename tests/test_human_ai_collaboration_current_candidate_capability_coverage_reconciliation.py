from __future__ import annotations

import json
import copy
import unittest

from scripts.validate_human_ai_collaboration_current_candidate_capability_coverage_reconciliation import (
    CURRENT_CANDIDATE_COVERAGE_REQUIRED_FILES,
    MATRIX_PATH,
    RECONCILIATION_PATH,
    ROOT,
    validate_reconciliation,
)


PROGRAM_ACCEPTANCE_PATH = ROOT / "registry/program-acceptance-map.json"
EVIDENCE_ID = (
    "evidence.human-ai-collaboration-current-candidate-capability-coverage-"
    "reconciliation-2026-08-01"
)


class CurrentCandidateCapabilityCoverageReconciliationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.document = json.loads(
            (ROOT / RECONCILIATION_PATH).read_text(encoding="utf-8")
        )
        self.matrix = json.loads((ROOT / MATRIX_PATH).read_text(encoding="utf-8"))

    def test_current_reconciliation_is_valid(self) -> None:
        validate_reconciliation(self.document, root=ROOT)

    def test_all_scenarios_preserve_the_matrix_evidence_state(self) -> None:
        expected = {
            row["id"]: row["evidenceState"] for row in self.matrix["scenarios"]
        }
        actual = {
            row["scenarioId"]: row["inheritedEvidenceState"]
            for row in self.document["scenarioCoverage"]
        }

        self.assertEqual(expected, actual)

    def test_each_scenario_maps_all_route_classes_without_residual_promotion(self) -> None:
        expected_route_classes = {"N", "O", "E", "C", "H", "R"}
        for row in self.document["scenarioCoverage"]:
            with self.subTest(scenario=row["scenarioId"]):
                self.assertEqual(
                    expected_route_classes,
                    set(row["routeCoverage"]),
                )
                self.assertEqual(
                    "not-eligible-no-residual-gap",
                    row["routeCoverage"]["R"]["state"],
                )
                self.assertEqual([], row["routeCoverage"]["R"]["candidateIds"])

    def test_route_evidence_is_bound_and_claim_ceiling_stays_false(self) -> None:
        bound_paths = {row["path"] for row in self.document["sourceBindings"]}
        self.assertEqual(
            {
                "instructionDeliveryProved": False,
                "candidateCausationProved": False,
                "liveDomainValueProved": False,
                "crossHostValueProved": False,
                "humanControlExecuted": False,
                "residualSelfAuthoredGapProved": False,
            },
            self.document["claimBoundary"],
        )
        for row in self.document["scenarioCoverage"]:
            with self.subTest(scenario=row["scenarioId"]):
                self.assertTrue(row["evidenceSourcePaths"])
                self.assertTrue(set(row["evidenceSourcePaths"]).issubset(bound_paths))
                for route in row["routeCoverage"].values():
                    if route["state"] == "unassessed":
                        self.assertEqual([], route["candidateIds"])
                        self.assertEqual("none", route["evidenceCeiling"])

    def test_validator_rejects_claim_promotion(self) -> None:
        mutated = copy.deepcopy(self.document)
        mutated["claimBoundary"]["candidateCausationProved"] = True

        with self.assertRaisesRegex(RuntimeError, "claim boundary promoted"):
            validate_reconciliation(mutated, root=ROOT)

    def test_validator_rejects_unknown_route_state(self) -> None:
        mutated = copy.deepcopy(self.document)
        mutated["scenarioCoverage"][0]["routeCoverage"]["O"] = {
            "state": "live-domain-value-proved",
            "candidateIds": ["official.creative-production"],
            "evidenceCeiling": "live-domain-value",
        }

        with self.assertRaisesRegex(RuntimeError, "route state drifted"):
            validate_reconciliation(mutated, root=ROOT)

    def test_validator_rejects_a_valid_but_unreviewed_route_projection(self) -> None:
        mutated = copy.deepcopy(self.document)
        mutated["scenarioCoverage"][0]["routeCoverage"]["O"][
            "evidenceCeiling"
        ] = "dated-design-input-only"

        with self.assertRaisesRegex(RuntimeError, "route projection drifted"):
            validate_reconciliation(mutated, root=ROOT)

    def test_validator_rejects_incomplete_authority_boundary(self) -> None:
        mutated = copy.deepcopy(self.document)
        del mutated["authorityBoundary"]["modelDispatchAuthorized"]

        with self.assertRaisesRegex(RuntimeError, "authority boundary drifted"):
            validate_reconciliation(mutated, root=ROOT)

    def test_overlap_conflict_fallback_and_unassessed_cells_are_explicit(self) -> None:
        self.assertEqual(
            {
                "scenarioCount": 13,
                "routeCellCount": 78,
                "mappedRouteCellCount": 50,
                "unassessedRouteCellCount": 15,
                "residualIneligibleCellCount": 13,
                "liveDomainValueScenarioCount": 0,
            },
            self.document["coverageSummary"],
        )
        self.assertGreaterEqual(len(self.document["overlapGroups"]), 5)
        self.assertGreaterEqual(len(self.document["conflictGroups"]), 5)
        self.assertGreaterEqual(len(self.document["unassessedCells"]), 6)
        for row in self.document["scenarioCoverage"]:
            with self.subTest(scenario=row["scenarioId"]):
                self.assertEqual("H", row["fallbackOrder"][-1])
                self.assertNotIn("R", row["fallbackOrder"])

    def test_validator_rejects_missing_reviewed_overlap_group(self) -> None:
        mutated = copy.deepcopy(self.document)
        mutated["overlapGroups"] = mutated["overlapGroups"][:-1]

        with self.assertRaisesRegex(RuntimeError, "overlap boundary drifted"):
            validate_reconciliation(mutated, root=ROOT)

    def test_validator_rejects_fallback_that_bypasses_human_control(self) -> None:
        mutated = copy.deepcopy(self.document)
        mutated["scenarioCoverage"][0]["fallbackOrder"] = ["N", "O"]

        with self.assertRaisesRegex(RuntimeError, "fallback boundary drifted"):
            validate_reconciliation(mutated, root=ROOT)

    def test_dimension_and_lifecycle_projections_are_complete_but_not_value_claims(self) -> None:
        self.assertEqual(9, len(self.document["dimensionCoverage"]))
        self.assertEqual(14, len(self.document["softwareLifecycleCoverage"]))
        self.assertTrue(
            all(
                row["liveDomainValueProved"] is False
                for row in self.document["dimensionCoverage"]
                + self.document["softwareLifecycleCoverage"]
            )
        )

    def test_decision_stops_broad_discovery_and_self_authoring(self) -> None:
        self.assertEqual(
            {
                "representativeCoverageMapped": True,
                "widerUntargetedDiscoveryNeededNow": False,
                "unassessedCellIsResidualGap": False,
                "currentEvidenceSupportsPortfolioMutation": False,
                "liveComparisonReady": False,
                "selfAuthoredGapEligible": False,
            },
            self.document["coverageDecision"],
        )
        self.assertEqual(0, self.document["executionCounters"]["modelRequestCount"])
        self.assertEqual(0, self.document["executionCounters"]["installationCount"])
        self.assertEqual(0, self.document["executionCounters"]["candidateExecutionCount"])

    def test_program_map_links_reconciliation_without_promoting_assessment(self) -> None:
        program = json.loads(PROGRAM_ACCEPTANCE_PATH.read_text(encoding="utf-8"))
        criteria = {row["id"]: row for row in program["acceptanceCriteria"]}
        for acceptance_id in {
            "acceptance.solution-neutral-collaboration-rebaseline",
            "acceptance.residual-gap-proof",
        }:
            with self.subTest(acceptance=acceptance_id):
                self.assertEqual("partial", criteria[acceptance_id]["assessment"])
                self.assertIn(EVIDENCE_ID, criteria[acceptance_id]["evidenceIds"])
        evidence = {row["id"]: row for row in program["evidence"]}[EVIDENCE_ID]
        self.assertEqual(str(RECONCILIATION_PATH).replace("\\", "/"), evidence["path"])
        self.assertEqual(
            {
                "acceptance.solution-neutral-collaboration-rebaseline",
                "acceptance.residual-gap-proof",
            },
            set(evidence["supports"]),
        )

    def test_validator_exports_the_stable_verify_integration_surface(self) -> None:
        self.assertEqual(
            (
                str(RECONCILIATION_PATH).replace("\\", "/"),
                "docs/strategy/HUMAN-AI-COLLABORATION-CURRENT-CANDIDATE-"
                "CAPABILITY-COVERAGE-RECONCILIATION-2026-08-01.md",
                "scripts/validate_human_ai_collaboration_current_candidate_"
                "capability_coverage_reconciliation.py",
                "tests/test_human_ai_collaboration_current_candidate_capability_"
                "coverage_reconciliation.py",
            ),
            CURRENT_CANDIDATE_COVERAGE_REQUIRED_FILES,
        )


if __name__ == "__main__":
    unittest.main()
