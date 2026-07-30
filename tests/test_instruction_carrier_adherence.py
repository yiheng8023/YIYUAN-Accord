import copy
import json
import unittest
from pathlib import Path

from scripts.evaluate_instruction_carrier_adherence import (
    aggregate_host_runs,
    evaluate_fixture_document,
    evaluate_observation,
)


ROOT = Path(__file__).resolve().parents[1]
FIXTURE_PATH = (
    ROOT / "tests/fixtures/instruction-carrier-adherence-2026-07-23.json"
)


class InstructionCarrierAdherenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.document = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))

    def test_all_offline_fixtures_match_expected_outcomes(self) -> None:
        results = evaluate_fixture_document(self.document)
        self.assertEqual(14, len(results))
        for result in results:
            with self.subTest(result["id"]):
                self.assertEqual(
                    result["expectedStatus"],
                    result["actualStatus"],
                )
                self.assertEqual(
                    result["expectedEvidenceLevel"],
                    result["actualEvidenceLevel"],
                )
                self.assertEqual(
                    set(result["expectedFailureCodes"]),
                    set(result["actualFailureCodes"]),
                )
                self.assertFalse(result["countsAsLiveHostProof"])
                self.assertFalse(result["countsAsWeakAgentAcceptance"])
                self.assertFalse(
                    result["countsAsUniversalCrossAgentAdherence"]
                )

    def _live_evidence(self, suffix: str) -> dict:
        evidence = copy.deepcopy(self.document["baseEvidence"])
        evidence.update(
            {
                "synthetic": False,
                "liveExecutionObserved": True,
                "runId": f"run-{suffix}",
                "hostRunId": f"host-run-{suffix}",
                "hostThreadId": f"thread-{suffix}",
                "taskId": f"task-{suffix}",
                "hostRunEvidenceSource": "parent-observed-host-run",
                "discoveryEvidenceSource": (
                    "host-instruction-discovery-event"
                ),
                "loadingEvidenceSource": "host-instruction-loader-event",
                "actualModelEvidenceSource": (
                    "parent-observed-host-metadata"
                ),
                "actualReasoningEvidenceSource": (
                    "parent-observed-host-metadata"
                ),
                "hostApprovalEvidenceSource": (
                    "parent-observed-host-approval"
                ),
                "hardStandardEvidenceSource": (
                    "parent-observed-hard-standard-outcome"
                ),
            }
        )
        evidence["loaderEvent"].update(
            {
                "taskId": f"task-{suffix}",
                "evidenceSource": "host-instruction-loader-event",
            }
        )
        evidence["effectiveInstructionSurface"]["evidenceSource"] = (
            "host-instruction-loader-event"
        )
        return evidence

    def test_three_distinct_live_runs_prove_only_host_scoped_repeatability(
        self,
    ) -> None:
        raw = self.document["rawResponseUtf8"].encode("utf-8")
        runs = [
            {"rawResponse": raw, "evidence": self._live_evidence(str(index))}
            for index in range(1, 4)
        ]
        result = aggregate_host_runs(runs)
        self.assertEqual("three-independent-live-runs-valid", result["status"])
        self.assertTrue(result["countsAsHostRepeatability"])
        self.assertTrue(result["countsAsWeakAgentAcceptance"])
        self.assertFalse(result["countsAsUniversalCrossAgentAdherence"])

    def test_reused_thread_identity_blocks_repetition_claim(self) -> None:
        raw = self.document["rawResponseUtf8"].encode("utf-8")
        runs = [
            {"rawResponse": raw, "evidence": self._live_evidence(str(index))}
            for index in range(1, 4)
        ]
        runs[2]["evidence"]["hostThreadId"] = runs[1]["evidence"][
            "hostThreadId"
        ]
        result = aggregate_host_runs(runs)
        self.assertEqual(
            "blocked-repetition-hostThreadId-reuse",
            result["status"],
        )
        self.assertFalse(result["countsAsHostRepeatability"])

    def test_terra_low_live_run_is_not_weak_agent_acceptance(self) -> None:
        raw = self.document["rawResponseUtf8"].encode("utf-8")
        evidence = self._live_evidence("terra")
        evidence["requestedModel"] = "gpt-5.6-terra"
        evidence["actualModel"] = "gpt-5.6-terra"
        result = evaluate_observation(raw, evidence)
        self.assertEqual("live-host-adherence-evidence-valid", result["status"])
        self.assertTrue(result["countsAsLiveHostProof"])
        self.assertFalse(result["countsAsWeakAgentAcceptance"])

    def test_unobserved_actual_model_blocks_live_host_proof(self) -> None:
        raw = self.document["rawResponseUtf8"].encode("utf-8")
        evidence = self._live_evidence("model-unknown")
        evidence["actualModel"] = "unknown"
        evidence["actualModelEvidenceSource"] = "agent-self-report"
        result = evaluate_observation(raw, evidence)
        self.assertEqual("fail", result["status"])
        self.assertIn("fail-actual-model-evidence", result["failureCodes"])
        self.assertFalse(result["countsAsLiveHostProof"])


if __name__ == "__main__":
    unittest.main()
