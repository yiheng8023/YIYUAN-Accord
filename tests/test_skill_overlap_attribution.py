from __future__ import annotations

import json
import unittest
from pathlib import Path

from scripts.evaluate_skill_overlap_attribution import (
    FIXTURE_PATH,
    evaluate,
    evaluate_fixture_document,
)


ROOT = Path(__file__).resolve().parent.parent


class SkillOverlapAttributionTests(unittest.TestCase):
    def test_all_fixtures_match(self) -> None:
        document = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
        results = evaluate_fixture_document(document)
        self.assertEqual(19, len(results))
        self.assertEqual(
            [],
            [item for item in results if item["actual"] != item["expected"]],
        )

    def test_hard_standard_cannot_be_credited_to_unobserved_skill(self) -> None:
        self.assertEqual(
            "hard-standard-control-only",
            evaluate(
                {
                    "case": "skill-value-attribution",
                    "hardStandardPreventedFailure": True,
                    "skillInvocationObserved": False,
                }
            ),
        )

    def test_arm_design_requires_loader_evidence(self) -> None:
        self.assertEqual(
            "arm-design-incomplete",
            evaluate(
                {
                    "case": "arm-design",
                    "eligibility": "eligible",
                    "intervention": "selective-single-skill",
                    "payloadIdentity": "source-pinned-example",
                    "payloadSha256": "a" * 64,
                    "hostExposureEvidence": "parent-observed-host-exposure",
                    "primaryMetric": "private-oracle-match",
                    "sharedControlsNotCredited": True,
                }
            ),
        )

    def test_selective_arm_rejects_full_bootstrap_trigger(self) -> None:
        self.assertEqual(
            "arm-design-trigger-boundary-conflict",
            evaluate(
                {
                    "case": "arm-design",
                    "eligibility": "eligible",
                    "intervention": "selective-single-skill",
                    "payloadIdentity": "source-pinned-example",
                    "payloadSha256": "a" * 64,
                    "hostExposureEvidence": "parent-observed-host-exposure",
                    "loaderEvidence": "host-loader-event",
                    "triggerMode": "full-bootstrap",
                    "triggerBoundary": "global-session-bootstrap",
                    "primaryMetric": "private-oracle-match",
                    "sharedControlsNotCredited": True,
                }
            ),
        )

    def test_ask_matt_rejects_cross_ecosystem_top_level_trigger(self) -> None:
        self.assertEqual(
            "arm-design-reject-second-top-level-router-trigger",
            evaluate(
                {
                    "case": "arm-design",
                    "eligibility": "eligible",
                    "intervention": "selective-single-skill",
                    "payloadIdentity": "matt:ask-matt",
                    "payloadSha256": "a" * 64,
                    "hostExposureEvidence": "parent-observed-host-exposure",
                    "loaderEvidence": "host-loader-event",
                    "triggerMode": "user-explicit",
                    "triggerBoundary": "cross-ecosystem-top-level",
                    "primaryMetric": "private-oracle-match",
                    "sharedControlsNotCredited": True,
                }
            ),
        )

    def test_handoff_producer_does_not_prove_receiver_quality(self) -> None:
        self.assertEqual(
            "handoff-producer-evidence-only",
            evaluate(
                {
                    "case": "handoff",
                    "hostLoaderEventObserved": True,
                    "producerEvidenceComplete": True,
                    "receiverExecutionObserved": False,
                }
            ),
        )

    def test_handoff_requires_three_run_and_thread_identities(self) -> None:
        self.assertEqual(
            "handoff-repetition-insufficient",
            evaluate(
                {
                    "case": "handoff",
                    "hostLoaderEventObserved": True,
                    "producerEvidenceComplete": True,
                    "receiverExecutionObserved": True,
                    "receiverPrivateOracleMatched": True,
                    "independentHostRunCount": 3,
                    "independentHostThreadCount": 2,
                }
            ),
        )

    def test_terra_low_cannot_be_relabelled_as_spark_acceptance(self) -> None:
        self.assertEqual(
            "capacity-diagnostic-only-not-weak-acceptance",
            evaluate(
                {
                    "case": "weak-condition",
                    "actualModel": "gpt-5.6-terra",
                    "actualReasoning": "low",
                }
            ),
        )

    def test_unknown_case_fails_closed(self) -> None:
        self.assertEqual(
            "unknown-skill-overlap-attribution-case",
            evaluate({"case": "future-case"}),
        )


if __name__ == "__main__":
    unittest.main()
