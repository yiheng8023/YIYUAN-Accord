import copy
import json
import unittest
from pathlib import Path

from scripts.build_mcp_lifecycle_trial_skeleton import (
    build_trial_skeleton,
    evaluate_fixture_document,
    validate_trial_skeleton,
)
from scripts.evaluate_mcp_task_selection_decision import canonical_sha256


ROOT = Path(__file__).resolve().parents[1]
SELECTION = ROOT / "tests/fixtures/mcp-task-selection-decision-2026-07-23.json"
FIXTURES = ROOT / "tests/fixtures/mcp-lifecycle-trial-skeleton-2026-07-24.json"


class McpLifecycleTrialSkeletonTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.selection_document = json.loads(SELECTION.read_text(encoding="utf-8"))
        cls.fixture_document = json.loads(FIXTURES.read_text(encoding="utf-8"))

    def _selection_packet(self) -> dict:
        packet = copy.deepcopy(self.selection_document["basePacket"])
        body = copy.deepcopy(packet)
        body.pop("packetSha256", None)
        packet["packetSha256"] = canonical_sha256(body)
        return packet

    def test_fixture_matrix(self) -> None:
        source = self._selection_packet()
        results = evaluate_fixture_document(self.fixture_document, source)
        self.assertGreaterEqual(len(results), 10)
        for result in results:
            with self.subTest(result["id"]):
                self.assertEqual(
                    set(result["expectedFailures"]),
                    set(result["actualFailures"]),
                )
                self.assertFalse(result["countsAsLiveHostProof"])
                self.assertFalse(result["countsAsWeakAgentAcceptance"])
                self.assertFalse(result["countsAsActivationOrReleaseProof"])

    def test_invalid_or_empty_selection_cannot_seed_trial(self) -> None:
        packet = self._selection_packet()
        packet["nativeCurrentAssessment"]["sufficient"] = True
        packet["nativeCurrentAssessment"]["residualGapIds"] = []
        packet["candidates"] = []
        packet["selectedMinimalSet"] = []
        packet["releasePlan"]["requestAtTaskOrPhaseEnd"] = False
        packet["releasePlan"]["fallback"] = "none-selected"
        body = copy.deepcopy(packet)
        body.pop("packetSha256", None)
        packet["packetSha256"] = canonical_sha256(body)
        with self.assertRaisesRegex(ValueError, "contains no MCP selected"):
            build_trial_skeleton(packet)

    def test_source_selection_failure_is_rejected_during_validation(self) -> None:
        source = self._selection_packet()
        skeleton = build_trial_skeleton(source)
        source["decisionBoundary"]["activationAuthorityGranted"] = True
        body = copy.deepcopy(source)
        body.pop("packetSha256", None)
        source["packetSha256"] = canonical_sha256(body)
        self.assertIn("fail-source-selection-not-valid", validate_trial_skeleton(skeleton, source))

    def test_task_contract_binds_use_case_acceptance_and_digest(self) -> None:
        source = self._selection_packet()
        skeleton = build_trial_skeleton(source, lifecycle_dimensions=["lease"])
        self.assertEqual(source["task"]["concreteUseCase"], skeleton["task"]["concreteUseCase"])
        self.assertEqual(source["task"]["acceptanceSurface"], skeleton["task"]["acceptanceSurface"])
        self.assertIn("fullLifecycleCoverageProved", skeleton["claimBoundary"])
        self.assertFalse(skeleton["claimBoundary"]["fullLifecycleCoverageProved"])
        self.assertIn("sameSessionSwitchingProved", skeleton["claimBoundary"])
        self.assertFalse(skeleton["claimBoundary"]["sameSessionSwitchingProved"])


if __name__ == "__main__":
    unittest.main()
