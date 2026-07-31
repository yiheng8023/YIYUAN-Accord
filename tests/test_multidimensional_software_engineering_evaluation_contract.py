import copy
import json
import unittest

from scripts.validate_multidimensional_software_engineering_evaluation_contract import (
    CONTRACT_PATH,
    PROGRAM_MAP_PATH,
    validate_contract,
)


class MultidimensionalSoftwareEngineeringEvaluationContractTests(
    unittest.TestCase
):
    @classmethod
    def setUpClass(cls) -> None:
        cls.contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
        cls.program_map = json.loads(PROGRAM_MAP_PATH.read_text(encoding="utf-8"))

    def test_repository_contract_is_consistent(self) -> None:
        validate_contract()

    def test_scalar_total_score_fails_closed(self) -> None:
        mutated = copy.deepcopy(self.contract)
        mutated["assessmentModel"]["scalarTotalScoreAllowed"] = True
        with self.assertRaisesRegex(RuntimeError, "Anti-gaming boundary drifted"):
            validate_contract(mutated)

    def test_missing_dimension_fails_closed(self) -> None:
        mutated = copy.deepcopy(self.contract)
        mutated["dimensions"].pop()
        with self.assertRaisesRegex(RuntimeError, "Evaluation dimensions drifted"):
            validate_contract(mutated)

    def test_hard_standard_promotion_fails_closed(self) -> None:
        mutated = copy.deepcopy(self.contract)
        mutated["candidateHardFloorBoundary"]["admittedHardStandardsCreated"] = True
        with self.assertRaisesRegex(RuntimeError, "Candidate floors were promoted"):
            validate_contract(mutated)

    def test_new_skill_necessity_claim_fails_closed(self) -> None:
        mutated = copy.deepcopy(self.contract)
        mutated["capabilityBoundary"]["newEvaluationSkillNecessary"] = True
        with self.assertRaisesRegex(RuntimeError, "new Skill was declared necessary"):
            validate_contract(mutated)

    def test_unpinned_latest_source_claim_fails_closed(self) -> None:
        mutated = copy.deepcopy(self.contract)
        mutated["sourceRefreshAndSnapshotPolicy"][
            "latestClaimWithoutPinnedSnapshotAllowed"
        ] = True
        with self.assertRaisesRegex(RuntimeError, "source-refresh"):
            validate_contract(mutated)

    def test_hard_standard_readiness_fails_closed(self) -> None:
        mutated = copy.deepcopy(self.contract)
        mutated["softAndHardStandardBoundary"][
            "currentHardStandardAdmissionReady"
        ] = True
        with self.assertRaisesRegex(RuntimeError, "hard-floor separation"):
            validate_contract(mutated)

    def test_automatic_user_agreement_fails_closed(self) -> None:
        mutated = copy.deepcopy(self.contract)
        mutated["subjectAndBiasBoundary"]["automaticAgreementAllowed"] = True
        with self.assertRaisesRegex(RuntimeError, "anti-deference"):
            validate_contract(mutated)

    def test_mechanical_opposition_is_not_independence(self) -> None:
        mutated = copy.deepcopy(self.contract)
        mutated["subjectAndBiasBoundary"][
            "mechanicalOppositionCountsAsIndependence"
        ] = True
        with self.assertRaisesRegex(RuntimeError, "anti-deference"):
            validate_contract(mutated)

    def test_acceptance_count_drift_fails_closed(self) -> None:
        mutated_map = copy.deepcopy(self.program_map)
        mutated_map["acceptanceCriteria"].pop()
        with self.assertRaisesRegex(RuntimeError, "Acceptance-count boundary drifted"):
            validate_contract(self.contract, program_map=mutated_map)


if __name__ == "__main__":
    unittest.main()
