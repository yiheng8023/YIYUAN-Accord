import copy
import json
import unittest
from pathlib import Path

from scripts.validate_ai_era_classical_software_engineering_principles_revalidation import (
    CONTRACT_PATH,
    PROGRAM_MAP_PATH,
    validate_contract,
)


class AiEraClassicalSoftwareEngineeringPrinciplesRevalidationTests(
    unittest.TestCase
):
    @classmethod
    def setUpClass(cls) -> None:
        cls.contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
        cls.program_map = json.loads(PROGRAM_MAP_PATH.read_text(encoding="utf-8"))

    def test_repository_contract_is_consistent(self) -> None:
        validate_contract()

    def test_missing_classification_fails_closed(self) -> None:
        mutated = copy.deepcopy(self.contract)
        mutated["classifications"].pop()
        with self.assertRaisesRegex(RuntimeError, "Classification vocabulary drifted"):
            validate_contract(mutated)

    def test_hard_standard_promotion_fails_closed(self) -> None:
        mutated = copy.deepcopy(self.contract)
        mutated["authorityBoundary"]["hardStandardPromotionAuthorized"] = True
        with self.assertRaisesRegex(RuntimeError, "expanded authority"):
            validate_contract(mutated)

    def test_acceptance_count_drift_fails_closed(self) -> None:
        mutated_map = copy.deepcopy(self.program_map)
        mutated_map["acceptanceCriteria"].pop()
        with self.assertRaisesRegex(RuntimeError, "acceptance count changed"):
            validate_contract(self.contract, program_map=mutated_map)


if __name__ == "__main__":
    unittest.main()
