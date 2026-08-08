from pathlib import Path
import unittest

from scripts.validate_harness_decision_packet_core_poc import (
    MUTATION_CASE_IDS,
    run_failure_matrix,
)

ROOT = Path(__file__).resolve().parent.parent


class HarnessDecisionPacketCorePocTests(unittest.TestCase):
    def test_all_fourteen_mutations_fail_closed(self) -> None:
        results = run_failure_matrix(ROOT)
        self.assertEqual(MUTATION_CASE_IDS, [item["caseId"] for item in results])
        self.assertTrue(all(item["status"] == "rejected" for item in results))
