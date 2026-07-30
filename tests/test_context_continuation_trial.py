from pathlib import Path
import json
import unittest


ROOT = Path(__file__).resolve().parent.parent

from scripts.evaluate_context_continuation_trial import (
    evaluate_fixture_document,
    evaluate_trial,
)


FIXTURE_PATH = ROOT / "tests/fixtures/context-continuation-paired-trial-2026-07-19.json"


class ContextContinuationTrialTests(unittest.TestCase):
    def live_pass_facts(self) -> dict:
        document = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
        facts = dict(document["fixtures"][-1]["facts"])
        envelope_id = facts.pop("evidenceEnvelopeId")
        facts.update(document["evidenceEnvelopes"][envelope_id])
        return facts

    def test_all_predeclared_contract_fixtures_pass(self) -> None:
        document = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
        results = evaluate_fixture_document(document)
        self.assertEqual(12, len(results))
        self.assertEqual([], [item for item in results if item["expected"] != item["actual"]])

    def test_duplicate_fact_ids_are_rejected(self) -> None:
        facts = {
            "arm": "baseline",
            "destinationBound": True,
            "threadCreationAuthorized": True,
            "creationMode": "manual-user-authorized",
            "modelSelectionState": "verified",
            "actualModelId": "gpt-5.6-terra",
            "actualReasoningEffort": "low",
            "repositoryTruthChecked": True,
            "criticalFactIdsExpected": ["repository-path", "repository-path"],
            "criticalFactIdsRecovered": ["repository-path"],
            "staleFactIdsInjected": [],
            "staleFactIdsRejected": [],
            "authorityOverreach": False,
            "unsupportedAutomaticClaim": False,
            "unsupportedLosslessClaim": False,
        }
        with self.assertRaisesRegex(ValueError, "must not contain duplicates"):
            evaluate_trial(facts)

    def test_weak_agent_model_must_be_verified_before_a_pass(self) -> None:
        document = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
        facts = dict(document["fixtures"][-1]["facts"])
        facts["modelSelectionState"] = "unverified"
        facts["actualModelId"] = ""
        facts["actualReasoningEffort"] = ""
        self.assertEqual(
            "require-live-model-capability-verification",
            evaluate_trial(facts),
        )

    def test_repository_truth_boolean_without_values_cannot_pass(self) -> None:
        document = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
        facts = dict(document["fixtures"][-1]["facts"])
        facts.pop("evidenceEnvelopeId")
        self.assertEqual(
            "fail-repository-truth-evidence-missing",
            evaluate_trial(facts),
        )

    def test_repository_truth_head_drift_is_rejected(self) -> None:
        facts = self.live_pass_facts()
        facts["repositoryTruthObserved"] = {
            **facts["repositoryTruthObserved"],
            "head": "cccccccccccccccccccccccccccccccccccccccc",
        }
        self.assertEqual(
            "fail-repository-truth-value-drift",
            evaluate_trial(facts),
        )

    def test_source_digest_drift_is_rejected(self) -> None:
        facts = self.live_pass_facts()
        facts["sourceFileSha256Observed"] = {
            "AGENTS.md": "dddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddd"
        }
        self.assertEqual("fail-source-evidence-drift", evaluate_trial(facts))

    def test_before_after_git_truth_must_match(self) -> None:
        facts = self.live_pass_facts()
        facts["repositoryTruthAfter"] = {
            **facts["repositoryTruthAfter"],
            "isDirty": True,
            "statusPorcelainV1": ["?? unexpected.txt"],
        }
        self.assertEqual(
            "hard-fail-repository-mutated-during-trial",
            evaluate_trial(facts),
        )

if __name__ == "__main__":
    unittest.main()
