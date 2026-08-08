from __future__ import annotations

import copy
import json
import unittest

from scripts.validate_addy_osmani_ai_assisted_engineering_weak_reference import (
    RECORD_PATH,
    ROOT,
    validate_record,
)


class AddyOsmaniAiAssistedEngineeringWeakReferenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.record = json.loads((ROOT / RECORD_PATH).read_text(encoding="utf-8"))

    def test_repository_record_is_valid(self) -> None:
        validate_record(self.record)

    def test_empirical_strength_promotion_fails_closed(self) -> None:
        mutated = copy.deepcopy(self.record)
        mutated["originalSource"]["empiricalStrength"] = "ES3"
        with self.assertRaisesRegex(RuntimeError, "empiricalStrength"):
            validate_record(mutated)

    def test_acceptance_promotion_fails_closed(self) -> None:
        mutated = copy.deepcopy(self.record)
        mutated["strategyImpact"]["acceptanceChangeRequired"] = True
        with self.assertRaisesRegex(RuntimeError, "acceptanceChangeRequired"):
            validate_record(mutated)

    def test_github_actions_requirement_fails_closed(self) -> None:
        mutated = copy.deepcopy(self.record)
        mutated["strategyImpact"]["githubActionsRequired"] = True
        with self.assertRaisesRegex(RuntimeError, "githubActionsRequired"):
            validate_record(mutated)

    def test_hard_standard_authority_fails_closed(self) -> None:
        mutated = copy.deepcopy(self.record)
        mutated["authorityBoundary"]["hardStandardAdmissionAuthorized"] = True
        with self.assertRaisesRegex(RuntimeError, "expanded authority"):
            validate_record(mutated)


if __name__ == "__main__":
    unittest.main()
