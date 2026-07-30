from __future__ import annotations

from pathlib import Path
import tempfile
import textwrap
import unittest

from scripts.evaluate_human_ai_collaboration_tdd_trial_outcome import (
    EVALUATOR_CONTRACT_VERSION,
    MUTANT_IMPLEMENTATIONS,
    evaluate_trial_outcome,
)


CORRECT_FEATURE = '''"""Correct fixture implementation."""


def capped_backoff_delay(attempt, schedule):
    if isinstance(attempt, bool) or not isinstance(attempt, int) or attempt <= 0:
        raise ValueError("attempt must be a positive integer")
    if not isinstance(schedule, (list, tuple)) or not schedule:
        raise ValueError("schedule must be a non-empty list or tuple")
    if any(
        isinstance(delay, bool) or not isinstance(delay, int) or delay <= 0
        for delay in schedule
    ):
        raise ValueError("schedule entries must be positive integers")
    return schedule[min(attempt - 1, len(schedule) - 1)]
'''

STRONG_TESTS = '''
import unittest

from feature import capped_backoff_delay


class CappedBackoffTests(unittest.TestCase):
    def test_literal_schedule_positions_and_cap(self):
        self.assertEqual(3, capped_backoff_delay(1, [3, 7, 15]))
        self.assertEqual(7, capped_backoff_delay(2, [3, 7, 15]))
        self.assertEqual(15, capped_backoff_delay(3, [3, 7, 15]))
        self.assertEqual(15, capped_backoff_delay(8, [3, 7, 15]))

    def test_invalid_attempts(self):
        for attempt in (0, -1, True, 1.5):
            with self.subTest(attempt=attempt):
                with self.assertRaises(ValueError):
                    capped_backoff_delay(attempt, [3])

    def test_invalid_schedules(self):
        for schedule in ([], "3,7", [0, 3], [True, 3]):
            with self.subTest(schedule=schedule):
                with self.assertRaises(ValueError):
                    capped_backoff_delay(1, schedule)


if __name__ == "__main__":
    unittest.main()
'''

WEAK_TESTS = '''
import unittest

from feature import capped_backoff_delay


class CappedBackoffTests(unittest.TestCase):
    def test_first_attempt(self):
        self.assertEqual(3, capped_backoff_delay(1, [3, 7, 15]))


if __name__ == "__main__":
    unittest.main()
'''


class HumanAiCollaborationTddTrialOutcomeTests(unittest.TestCase):
    def build_trial(self, root: Path, tests: str) -> None:
        (root / "feature.py").write_text(
            CORRECT_FEATURE,
            encoding="utf-8",
        )
        (root / "test_feature.py").write_text(
            textwrap.dedent(tests),
            encoding="utf-8",
        )

    def test_strong_public_tests_kill_all_predeclared_mutants(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.build_trial(root, STRONG_TESTS)
            result = evaluate_trial_outcome(root)
        self.assertEqual(EVALUATOR_CONTRACT_VERSION, result["evaluatorContractVersion"])
        self.assertEqual("parent-outcome-accepted", result["status"])
        self.assertEqual(len(MUTANT_IMPLEMENTATIONS), result["mutantCount"])
        self.assertEqual(result["mutantCount"], result["killedMutantCount"])
        self.assertEqual([], result["survivingMutantIds"])
        self.assertTrue(result["hiddenOracle"]["greenProved"])
        self.assertFalse(result["hiddenOracle"]["contentWrittenIntoTrial"])
        self.assertFalse(result["mutantSourcesWrittenIntoTrial"])

    def test_weak_tests_cannot_pass_mutation_gate(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.build_trial(root, WEAK_TESTS)
            result = evaluate_trial_outcome(root)
        self.assertEqual("parent-outcome-rejected", result["status"])
        self.assertIn(
            "predeclared-mutants-survived",
            result["failureCodes"],
        )
        self.assertGreater(len(result["survivingMutantIds"]), 0)
        self.assertTrue(result["visibleSuite"]["greenProved"])
        self.assertTrue(result["hiddenOracle"]["greenProved"])

    def test_test_source_introspection_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.build_trial(root, STRONG_TESTS + "\nimport inspect\n")
            result = evaluate_trial_outcome(root)
        self.assertEqual("parent-outcome-rejected", result["status"])
        self.assertIn(
            "implementation-source-read",
            result["sourceBoundary"]["failureCodes"],
        )


if __name__ == "__main__":
    unittest.main()
