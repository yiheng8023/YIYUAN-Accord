import json
from pathlib import Path
import unittest

from scripts.validate_harness_decision_packet_core_poc import (
    EVIDENCE_PATH,
    EXPECTED_PACKET_PATH,
    MUTATION_CASE_IDS,
    run_failure_matrix,
    validate_repository_record,
)

ROOT = Path(__file__).resolve().parent.parent


class HarnessDecisionPacketCorePocTests(unittest.TestCase):
    def test_all_fourteen_mutations_fail_closed(self) -> None:
        results = run_failure_matrix(ROOT)
        self.assertEqual(MUTATION_CASE_IDS, [item["caseId"] for item in results])
        self.assertTrue(all(item["status"] == "rejected" for item in results))


class HarnessDecisionPacketRepositoryIntegrationTests(unittest.TestCase):
    def test_repository_record_replays_packet_and_failures(self) -> None:
        record = validate_repository_record(ROOT)
        self.assertEqual(
            "verified-zero-model-source-bound-decision-packet-mechanism-only",
            record["status"],
        )
        self.assertTrue((ROOT / EVIDENCE_PATH).is_file())
        self.assertTrue((ROOT / EXPECTED_PACKET_PATH).is_file())

    def test_acceptance_remains_partial(self) -> None:
        acceptance = json.loads(
            (ROOT / "registry/program-acceptance-map.json").read_text(encoding="utf-8")
        )
        criterion = next(
            item
            for item in acceptance["acceptanceCriteria"]
            if item["id"] == "acceptance.decision-ready-consumer-projection"
        )
        self.assertEqual("partial", criterion["assessment"])
        self.assertIn(
            "evidence.harness-decision-packet-core-poc-2026-08-08",
            criterion["evidenceIds"],
        )
