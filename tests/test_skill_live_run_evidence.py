from pathlib import Path
import json
import unittest

from scripts.evaluate_skill_live_run_evidence import (
    aggregate_live_runs,
    canonical_sha256,
    evaluate_fixture_document,
    evaluate_live_run,
)


ROOT = Path(__file__).resolve().parent.parent
FIXTURE_PATH = ROOT / "tests/fixtures/skill-live-run-evidence-2026-07-23.json"


class SkillLiveRunEvidenceTests(unittest.TestCase):
    def fixture_document(self) -> dict:
        return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))

    def test_all_deterministic_fixtures_match(self) -> None:
        results = evaluate_fixture_document(self.fixture_document())
        self.assertEqual(15, len(results))
        for result in results:
            self.assertEqual(
                result["expectedStatus"],
                result["actualStatus"],
                result["id"],
            )
            self.assertEqual(
                set(result["expectedFailureCodes"]),
                set(result["actualFailureCodes"]),
                result["id"],
            )
            self.assertFalse(result["countsAsWeakAgentAcceptance"], result["id"])

    def test_synthetic_fixture_cannot_enter_live_aggregate(self) -> None:
        document = self.fixture_document()
        evidence = document["baseEvidence"]
        raw_response = document["rawResponseUtf8"].encode("utf-8")
        runs = [
            {
                "rawResponse": raw_response,
                "evidence": {
                    **evidence,
                    "taskId": f"fixture-task-{index}",
                    "runId": f"fixture-run-{index}",
                    "hostRunId": f"fixture-host-run-{index}",
                    "hostThreadId": f"fixture-thread-{index}",
                },
            }
            for index in range(1, 4)
        ]
        self.assertEqual(
            "blocked-or-failed-live-run-set",
            aggregate_live_runs(runs)["status"],
        )

    def test_packet_and_payload_hashes_are_canonical(self) -> None:
        evidence = self.fixture_document()["baseEvidence"]
        self.assertEqual(
            evidence["packetSha256"],
            canonical_sha256(evidence["packetPublic"]),
        )
        self.assertEqual(
            evidence["payloadManifestSha256"],
            canonical_sha256(evidence["payloadManifest"]),
        )

    def test_not_applicable_cell_requires_concrete_reason(self) -> None:
        document = self.fixture_document()
        evidence = {
            **document["baseEvidence"],
            "cellState": "not-applicable",
            "notApplicableReason": "",
        }
        with self.assertRaisesRegex(ValueError, "concrete reason"):
            evaluate_live_run(document["rawResponseUtf8"].encode("utf-8"), evidence)


if __name__ == "__main__":
    unittest.main()
