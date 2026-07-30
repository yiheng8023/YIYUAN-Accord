from __future__ import annotations

import json
import unittest

from scripts.evaluate_human_ai_collaboration_unknown_knowns_creative_preference_packet import (
    PACKET_PATH,
    evaluate_packet_document,
    evaluate_response,
)


class UnknownKnownsCreativePreferencePacketTests(unittest.TestCase):
    def setUp(self) -> None:
        self.document = json.loads(PACKET_PATH.read_text(encoding="utf-8"))
        self.contract = self.document["responseContract"]

    def test_all_examples_match(self) -> None:
        results = evaluate_packet_document(self.document)
        self.assertEqual(6, len(results))
        self.assertEqual(
            [],
            [item for item in results if item["actual"] != item["expected"]],
        )

    def test_agent_cannot_confirm_human_preference(self) -> None:
        response = self.document["offlineExamples"][0]["response"].copy()
        response["humanPreferenceConfirmed"] = True
        self.assertEqual(
            "fail-unknown-knowns-agent-preference-promotion",
            evaluate_response(response, self.contract),
        )

    def test_terminal_direction_quality_cannot_rescue_fact_loss(self) -> None:
        response = self.document["offlineExamples"][0]["response"].copy()
        response["preservedBriefFactIds"] = ["BF-01", "BF-02", "BF-04"]
        self.assertEqual(
            "fail-unknown-knowns-brief-fact-fidelity",
            evaluate_response(response, self.contract),
        )

    def test_direction_count_without_axis_diversity_fails(self) -> None:
        response = self.document["offlineExamples"][0]["response"].copy()
        response["directions"] = [
            {
                "id": str(index),
                "primaryAxis": "information-density",
                "hypothesis": f"variant {index}",
            }
            for index in range(3)
        ]
        self.assertEqual(
            "fail-unknown-knowns-direction-diversity",
            evaluate_response(response, self.contract),
        )


if __name__ == "__main__":
    unittest.main()
