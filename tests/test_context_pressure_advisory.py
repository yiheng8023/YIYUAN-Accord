import json
from pathlib import Path
import unittest

from scripts.evaluate_context_pressure_advisory import evaluate_advisory, evaluate_fixture_document


ROOT = Path(__file__).resolve().parent.parent
FIXTURE = ROOT / "tests/fixtures/context-pressure-advisory-2026-07-23.json"


class ContextPressureAdvisoryTests(unittest.TestCase):
    def test_all_fixtures_match(self) -> None:
        document = json.loads(FIXTURE.read_text(encoding="utf-8"))
        results = evaluate_fixture_document(document)
        self.assertEqual(12, len(results))
        self.assertEqual(
            [],
            [item for item in results if item["expected"] != {key: item["actual"][key] for key in item["expected"]}],
        )

    def test_unauthorized_pressure_cannot_cross_wait(self) -> None:
        result = evaluate_advisory({
            "signalProvenance": "host-event", "signalObserved": True,
            "pressureIndicated": True, "criticalFactDriftObserved": False,
            "threadCreationAuthorized": False, "ctx0405PacketPrepared": True,
            "automaticCreationClaimed": False, "losslessHandoffClaimed": False,
            "crossHostParityClaimed": False, "fixedPercentageClaimed": False,
            "terraCountsAsWeakAgentAcceptance": False,
        })
        self.assertEqual("WAIT", result["state"])
        self.assertNotIn("HANDOFF_PACKET_READY", result["trace"])

    def test_invalid_provenance_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "signalProvenance"):
            evaluate_advisory({
                "signalProvenance": "telepathy", "signalObserved": False,
                "pressureIndicated": False, "criticalFactDriftObserved": False,
                "threadCreationAuthorized": False, "ctx0405PacketPrepared": False,
                "automaticCreationClaimed": False, "losslessHandoffClaimed": False,
                "crossHostParityClaimed": False, "fixedPercentageClaimed": False,
                "terraCountsAsWeakAgentAcceptance": False,
            })

    def test_every_result_remains_offline_and_not_weak_agent_evidence(self) -> None:
        document = json.loads(FIXTURE.read_text(encoding="utf-8"))
        for result in evaluate_fixture_document(document):
            self.assertFalse(result["actual"]["countsAsLiveHostProof"])
            self.assertFalse(result["actual"]["countsAsWeakAgentAcceptance"])


if __name__ == "__main__":
    unittest.main()
