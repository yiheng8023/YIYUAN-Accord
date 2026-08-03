from __future__ import annotations

import copy
import unittest
from unittest.mock import patch

import scripts.validate_skill_portfolio_zero_model_effect_oracle_suite as suite
from scripts.validate_skill_portfolio_zero_model_effect_oracle_suite import (
    ROOT,
    validate_suite,
)


class SkillPortfolioZeroModelEffectOracleSuiteTests(unittest.TestCase):
    def test_duplicate_cross_group_candidate_fails_closed(self) -> None:
        groups = copy.deepcopy(suite.EXPECTED_GROUPS)
        groups[-1]["candidateNames"][0] = "strategy-red-team"

        with patch.object(suite, "EXPECTED_GROUPS", groups):
            with self.assertRaisesRegex(
                RuntimeError,
                "Effect-group candidate or comparison mapping drifted",
            ):
                suite.validate_suite(ROOT)

    def test_repository_suite_closes_without_live_or_residual_gap_promotion(self) -> None:
        report = validate_suite(ROOT)

        self.assertEqual("zero-model-effect-oracle-suite-calibrated", report["status"])
        self.assertEqual(8, report["effectGroupCount"])
        self.assertEqual(17, report["candidateCount"])
        self.assertEqual(50, report["caseCount"])
        self.assertEqual(42, report["faultCaseCount"])
        self.assertEqual(0, report["modelCallCount"])
        self.assertEqual(0, report["candidateExecutionCount"])
        self.assertFalse(report["liveBehaviorArmAuthorized"])
        self.assertFalse(report["residualSelfAuthoredGapProved"])
        self.assertTrue(report["nextGateRequiresSeparateAuthorization"])


if __name__ == "__main__":
    unittest.main()
