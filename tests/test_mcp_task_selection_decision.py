import copy
import json
import unittest
from pathlib import Path

from scripts.evaluate_mcp_task_selection_decision import (
    canonical_sha256,
    evaluate_fixture_document,
    evaluate_selection,
)


ROOT = Path(__file__).resolve().parents[1]
FIXTURE_PATH = (
    ROOT / "tests/fixtures/mcp-task-selection-decision-2026-07-23.json"
)


class McpTaskSelectionDecisionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.document = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))

    def test_all_fixtures_match_expected_outcomes(self) -> None:
        results = evaluate_fixture_document(self.document)
        self.assertEqual(27, len(results))
        for result in results:
            with self.subTest(result["id"]):
                self.assertEqual(
                    result["expectedStatus"],
                    result["actualStatus"],
                )
                self.assertEqual(
                    set(result["expectedFailureCodes"]),
                    set(result["actualFailureCodes"]),
                )
                self.assertFalse(result["countsAsLiveHostProof"])
                self.assertFalse(result["countsAsWeakAgentAcceptance"])
                self.assertFalse(result["countsAsActivationOrReleaseProof"])

    def _packet_with_digest(self) -> dict:
        packet = copy.deepcopy(self.document["basePacket"])
        digest_payload = copy.deepcopy(packet)
        digest_payload.pop("packetSha256", None)
        packet["packetSha256"] = canonical_sha256(digest_payload)
        return packet

    def test_valid_selection_is_still_selection_only(self) -> None:
        result = evaluate_selection(self._packet_with_digest())
        self.assertEqual(
            "offline-selection-contract-valid-no-host-actuation-proof",
            result["status"],
        )
        self.assertEqual(
            ["example:local-schema-mcp"],
            result["selectedIdentities"],
        )
        self.assertFalse(result["countsAsActivationOrReleaseProof"])

    def test_digest_covers_release_and_claim_boundaries(self) -> None:
        packet = self._packet_with_digest()
        packet["releasePlan"]["releaseObserved"] = True
        result = evaluate_selection(packet)
        self.assertEqual("fail", result["status"])
        self.assertIn("fail-release-plan", result["failureCodes"])
        self.assertIn("fail-packet-digest", result["failureCodes"])

    def test_candidate_universe_is_bounded(self) -> None:
        packet = self._packet_with_digest()
        packet["candidates"] = [
            copy.deepcopy(packet["candidates"][0]) for _ in range(33)
        ]
        digest_payload = copy.deepcopy(packet)
        digest_payload.pop("packetSha256", None)
        packet["packetSha256"] = canonical_sha256(digest_payload)
        result = evaluate_selection(packet)
        self.assertIn("fail-candidate-set-limit", result["failureCodes"])


if __name__ == "__main__":
    unittest.main()
