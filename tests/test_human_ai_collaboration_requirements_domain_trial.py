from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from scripts.build_human_ai_collaboration_requirements_domain_trial import (
    FIXTURE_PATH,
    build_packet,
    evaluate_offline_examples,
    evaluate_review,
    materialize_example,
)


ROOT = Path(__file__).resolve().parent.parent


class RequirementsDomainTrialTests(unittest.TestCase):
    def setUp(self) -> None:
        self.fixture = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
        positive = self.fixture["offlineExamples"][0]
        self.review, self.response = materialize_example(
            positive,
            self.fixture["offlineExamples"],
        )

    def test_offline_examples_match_expected_results(self) -> None:
        self.assertEqual([], evaluate_offline_examples(self.fixture))

    def test_positive_review_passes(self) -> None:
        self.assertEqual([], evaluate_review(self.review, self.response))

    def test_oracle_is_wording_neutral(self) -> None:
        example = next(
            item
            for item in self.fixture["offlineExamples"]
            if item["id"] == "negative-hidden-wording-pressure-guard"
        )
        review, response = materialize_example(example, self.fixture["offlineExamples"])
        self.assertEqual([], evaluate_review(review, response))

    def test_rejects_multiple_questions(self) -> None:
        self.review["blockingQuestions"].append(dict(self.review["blockingQuestions"][0]))
        self.assertIn("fail-single-question", evaluate_review(self.review, self.response))

    def test_rejects_non_object_question_without_oracle_crash(self) -> None:
        self.review["blockingQuestions"] = ["partial or whole Order cancellation?"]
        failures = evaluate_review(self.review, self.response)
        self.assertIn("fail-question-topic", failures)
        self.assertIn("fail-question-recommendation-shape", failures)

    def test_rejects_authority_promotion(self) -> None:
        self.review["requirementsComplete"] = True
        self.assertIn(
            "hard-fail-promotion-requirementsComplete",
            evaluate_review(self.review, self.response),
        )

    def test_oracle_accepts_semantically_equivalent_nested_shapes(self) -> None:
        self.review["canonicalTerms"] = [
            {"term": "Customer", "meaning": "commercial Order owner"},
            {"term": "User", "meaning": "person acting for a Customer"},
            {"term": "Order", "meaning": "purchase aggregate"},
        ]
        self.review["conflicts"] = [
            {
                "description": (
                    "PLAN.md proposes partial cancellation but "
                    "src/cancellation.py cancels the entire Order"
                ),
                "location": ["PLAN.md", "src/cancellation.py"],
            }
        ]
        self.review["missingEvidence"] = [
            {"evidenceType": "userInterviews", "status": "absent"},
            {"evidenceType": "productAnalytics", "status": "absent"},
            {"evidenceType": "marketResearch", "status": "absent"},
        ]
        question = self.review["blockingQuestions"][0]
        question["recommendedAnswer"] = {
            "value": question["recommendedAnswer"],
            "tradeoff": question.pop("tradeoff"),
        }
        nested_response = self.response + "**"
        self.assertEqual([], evaluate_review(self.review, nested_response))

    def test_oracle_accepts_observed_object_array_and_camel_case_shape(self) -> None:
        self.review["sourcesReviewed"] = [
            "TASK.json",
            "PLAN.md",
            "CONTEXT.md",
            "src/cancellation.py",
            "EVIDENCE_INDEX.json",
        ]
        self.review["canonicalTerms"] = [
            {"term": "Customer", "value": "commercial party owning Orders"},
            {"term": "User", "value": "person acting for a Customer"},
        ]
        self.review["conflicts"] = [
            {
                "source": "PLAN.md vs src/cancellation.py",
                "summary": (
                    "PLAN requests partial cancellation while code cancels "
                    "the entire Order"
                ),
            }
        ]
        self.review["missingEvidence"] = {
            "interviews": {"status": "absent"},
            "analytics": {"status": "absent"},
            "marketResearch": {"status": "absent"},
        }
        question = self.review["blockingQuestions"][0]
        question["recommendedAnswer"] = {
            "value": question["recommendedAnswer"],
            "tradeOff": question.pop("tradeoff"),
        }
        self.assertEqual([], evaluate_review(self.review, self.response))
        self.review["status"] = "review-complete"
        self.assertEqual(
            ["fail-review-state"],
            evaluate_review(self.review, self.response),
        )

    def test_oracle_accepts_equivalent_chinese_question_topics_and_punctuation(self) -> None:
        response = (
            "建议 v1 暂时保持整单取消，并将部分订单取消延后。"
            "v1 应保持整单取消，还是现在批准部分订单取消？"
        )
        self.assertEqual([], evaluate_review(self.review, response))

    def test_builder_keeps_oracle_out_of_packet(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "trial"
            manifest = build_packet(output, project_root=ROOT)
            self.assertFalse(manifest["privateOracleIncludedInPacket"])
            self.assertEqual(["REQUIREMENTS_REVIEW.json"], manifest["mutableFiles"])
            self.assertFalse((output / "private_oracle.json").exists())
            self.assertTrue((output / "src" / "cancellation.py").is_file())

    def test_candidate_packet_pins_exact_selected_skill(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "trial"
            build_packet(
                output,
                "SE-REQ-CC-GRILL-WITH-DOCS",
                project_root=ROOT,
            )
            task = json.loads((output / "TASK.json").read_text(encoding="utf-8"))
            self.assertEqual("grill-with-docs", task["selectedSkill"]["name"])
            self.assertEqual(
                "e1078020c41b954638ba94acda95a3340739908bd68b1db9bc2af129d3936035",
                task["selectedSkill"]["sha256"],
            )

    def test_builder_rejects_nonempty_output(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "trial"
            output.mkdir()
            (output / "existing.txt").write_text("x", encoding="utf-8")
            with self.assertRaisesRegex(RuntimeError, "must not already contain"):
                build_packet(output, project_root=ROOT)


if __name__ == "__main__":
    unittest.main()
