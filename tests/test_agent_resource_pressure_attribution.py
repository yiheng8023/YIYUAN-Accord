import json
from pathlib import Path
import unittest

from scripts.evaluate_agent_resource_pressure_attribution import (
    evaluate_fixture_document,
    evaluate_resource_pressure_attribution,
)


ROOT = Path(__file__).resolve().parent.parent
FIXTURE_PATH = (
    ROOT
    / "tests/fixtures/agent-resource-pressure-attribution-fixtures-2026-07-31.json"
)


class AgentResourcePressureAttributionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.document = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))

    def test_all_predeclared_fixtures_match(self) -> None:
        results = evaluate_fixture_document(self.document)
        self.assertEqual(26, len(results))
        self.assertEqual(
            [],
            [
                item
                for item in results
                if item["expectedClassification"]
                != item["actual"]["classification"]
            ],
        )

    def test_every_fixture_remains_offline_and_not_gap_evidence(self) -> None:
        for item in evaluate_fixture_document(self.document):
            self.assertFalse(item["actual"]["countsAsLiveHostProof"])
            self.assertFalse(item["actual"]["countsAsWeakAgentAcceptance"])
            self.assertFalse(
                item["actual"]["countsAsSelfAuthoredControllerGapEvidence"]
            )

    def test_safe_existing_authority_route_is_eligible_not_executed(self) -> None:
        facts = dict(self.document["defaults"])
        facts.update(
            {
                "pressureAttributionClaimed": True,
                "pressureObservedAcrossRepeats": True,
                "candidateResourceDeltaCorrelated": True,
                "confoundersControlled": True,
                "autonomousActionRequested": True,
                "existingAuthority": True,
                "hostActuationAvailable": True,
                "verificationSurfaceBound": True,
                "actionReversible": True,
            }
        )
        result = evaluate_resource_pressure_attribution(facts)
        self.assertTrue(result["autonomousActionEligible"])
        self.assertFalse(result["countsAsLiveHostProof"])
        self.assertEqual("autonomous-action-eligible", result["route"])

    def test_unknown_resource_type_is_rejected(self) -> None:
        facts = dict(self.document["defaults"])
        facts["candidateResourceTypes"] = ["telepathic-thread"]
        with self.assertRaisesRegex(ValueError, "unsupported candidateResourceTypes"):
            evaluate_resource_pressure_attribution(facts)

    def test_task_completion_cannot_become_release(self) -> None:
        facts = dict(self.document["defaults"])
        facts.update(
            {
                "pressureAttributionClaimed": True,
                "pressureObservedAcrossRepeats": True,
                "candidateResourceDeltaCorrelated": True,
                "confoundersControlled": True,
                "releaseAttributionClaimed": True,
                "taskCompleteEventRecorded": True,
            }
        )
        result = evaluate_resource_pressure_attribution(facts)
        self.assertEqual(
            "fail-task-completion-promoted-to-resource-release",
            result["classification"],
        )
        self.assertFalse(result["releaseAttributionEligible"])


if __name__ == "__main__":
    unittest.main()
