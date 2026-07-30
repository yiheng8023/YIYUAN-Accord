from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from scripts.build_mcp_lifecycle_trial_skeleton import build_trial_skeleton
from scripts.evaluate_mcp_same_thread_refresh_evidence import (
    evaluate_fixture_document,
)
from scripts.evaluate_mcp_task_selection_decision import canonical_sha256


ROOT = Path(__file__).resolve().parents[1]
SELECTION_PATH = (
    ROOT / "tests/fixtures/mcp-task-selection-decision-2026-07-23.json"
)
FIXTURE_PATH = (
    ROOT / "tests/fixtures/mcp-same-thread-refresh-evidence-2026-07-24.json"
)


class McpSameThreadRefreshEvidenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.selection_document = json.loads(
            SELECTION_PATH.read_text(encoding="utf-8")
        )
        cls.fixture_document = json.loads(
            FIXTURE_PATH.read_text(encoding="utf-8")
        )

    def _selection_packet(self) -> dict:
        packet = copy.deepcopy(self.selection_document["basePacket"])
        body = copy.deepcopy(packet)
        body.pop("packetSha256", None)
        packet["packetSha256"] = canonical_sha256(body)
        return packet

    def test_all_fixtures_match_and_never_prove_live_behavior(self) -> None:
        selection = self._selection_packet()
        skeleton = build_trial_skeleton(
            selection,
            lifecycle_dimensions=["sameSessionSwitching"],
        )
        results = evaluate_fixture_document(
            self.fixture_document,
            skeleton,
            selection,
        )
        self.assertEqual(12, len(results))
        self.assertEqual(
            [],
            [item for item in results if item["expected"] != item["actual"]],
        )
        self.assertTrue(
            all(item["countsAsLiveHostProof"] is False for item in results)
        )
        self.assertTrue(
            all(item["countsAsTaskEndReleaseProof"] is False for item in results)
        )

    def test_wrong_lifecycle_dimension_cannot_seed_refresh_evidence(self) -> None:
        selection = self._selection_packet()
        skeleton = build_trial_skeleton(selection, lifecycle_dimensions=["lease"])
        results = evaluate_fixture_document(
            self.fixture_document,
            skeleton,
            selection,
        )
        self.assertTrue(
            all(
                item["actual"] == "blocked-source-skeleton-binding"
                for item in results
            )
        )


if __name__ == "__main__":
    unittest.main()
