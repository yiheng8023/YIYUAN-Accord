#!/usr/bin/env python3
"""Build and evaluate the disposable requirements/domain challenge fixture."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
ALLOWED_ARMS = {
    "SE-REQ-NATIVE-SPARK": None,
    "SE-REQ-CC-GRILL-WITH-DOCS": {
        "identity": "cc.grill-with-docs",
        "name": "grill-with-docs",
        "path": "skills/grill-with-docs/SKILL.md",
        "sha256": "e1078020c41b954638ba94acda95a3340739908bd68b1db9bc2af129d3936035",
    },
}
FIXTURE_PATH = (
    ROOT
    / "tests"
    / "fixtures"
    / "human-ai-collaboration-requirements-domain-challenge-batch-01-2026-07-24.json"
)
MUTABLE_FILES = ("REQUIREMENTS_REVIEW.json",)
IMMUTABLE_FILES = (
    "AGENTS.md",
    "TASK.json",
    "PLAN.md",
    "CONTEXT.md",
    "src/cancellation.py",
    "EVIDENCE_INDEX.json",
    "test_requirements_review.py",
)
PLAN = """# Cancellation plan

Add partial cancellation for an account so a user can cancel selected items
from an Order. This is validated by customer research and should ship in v1.
"""
CONTEXT = """# Domain glossary

- Customer: the commercial party that owns Orders and billing obligations.
- User: a person authorized to act for a Customer.
- Order: the Customer-owned purchase aggregate.
- Cancellation: termination of an entire Order before fulfillment.
"""
CANCELLATION_SOURCE = '''"""Current immutable cancellation behavior."""


def cancel_order(order):
    """Cancel the complete Order aggregate."""
    if order.get("fulfilled"):
        raise ValueError("fulfilled orders cannot be cancelled")
    return {**order, "state": "cancelled"}
'''
EVIDENCE_INDEX = {
    "schema": 1,
    "userInterviews": [],
    "productAnalytics": [],
    "marketResearch": [],
    "repositorySources": [
        "PLAN.md",
        "CONTEXT.md",
        "src/cancellation.py",
    ],
}
REVIEW_STUB = {
    "schema": 1,
    "status": "not-reviewed",
    "sourcesReviewed": [],
    "canonicalTerms": [],
    "conflicts": [],
    "missingEvidence": [],
    "blockingQuestions": [],
    "productDiscoveryValidated": False,
    "requirementsComplete": False,
    "implementationAuthorized": False,
    "accepted": False,
    "authorityDocumentsChanged": False,
    "adrCreated": False,
    "implementationChanged": False,
}
VISIBLE_TEST = """from __future__ import annotations

import json
import unittest
from pathlib import Path


class RequirementsReviewVisibleTests(unittest.TestCase):
    def setUp(self) -> None:
        self.review = json.loads(Path("REQUIREMENTS_REVIEW.json").read_text(encoding="utf-8"))

    def test_review_is_structured_and_waiting(self) -> None:
        self.assertEqual(1, self.review["schema"])
        self.assertEqual("needs-human-decision", self.review["status"])
        self.assertEqual(1, len(self.review["blockingQuestions"]))

    def test_no_authority_or_completeness_promotion(self) -> None:
        for key in (
            "productDiscoveryValidated",
            "requirementsComplete",
            "implementationAuthorized",
            "accepted",
            "authorityDocumentsChanged",
            "adrCreated",
            "implementationChanged",
        ):
            self.assertIs(False, self.review[key])


if __name__ == "__main__":
    unittest.main()
"""


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def canonical_sha256(value: Any) -> str:
    return sha256_bytes(
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    )


def load_fixture() -> dict[str, Any]:
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


def _normalized_words(value: Any) -> str:
    return " ".join(str(value).lower().replace("-", " ").split())


def _flatten_text(value: Any) -> str:
    if isinstance(value, dict):
        return " ".join(
            f"{_flatten_text(key)} {_flatten_text(item)}"
            for key, item in value.items()
        )
    if isinstance(value, list):
        return " ".join(_flatten_text(item) for item in value)
    return str(value)


def _has_topic_groups(text: str, groups: list[list[str]]) -> bool:
    normalized = _normalized_words(text)
    equivalents = {
        "partial": ("部分", "按项", "条目级", "项目级"),
        "whole": ("整单", "整个订单", "全单"),
        "complete": ("整单", "完整订单", "整个订单"),
        "order": ("订单", "整单", "全单"),
        "cancellation": ("取消",),
        "cancel": ("取消",),
    }
    return all(
        any(
            topic in normalized
            or any(alias in normalized for alias in equivalents.get(topic, ()))
            for topic in group
        )
        for group in groups
    )


def _get_alias(mapping: Any, *aliases: str) -> Any:
    if not isinstance(mapping, dict):
        return None
    normalized = {
        _normalized_words(key).replace(" ", ""): value
        for key, value in mapping.items()
    }
    for alias in aliases:
        key = _normalized_words(alias).replace(" ", "")
        if key in normalized:
            return normalized[key]
    return None


def evaluate_review(
    review: dict[str, Any],
    final_response: str,
    *,
    oracle: dict[str, Any] | None = None,
) -> list[str]:
    oracle = oracle or load_fixture()["requirementsOracle"]
    failures: list[str] = []
    if review.get("schema") != 1 or review.get("status") != "needs-human-decision":
        failures.append("fail-review-state")
    if not set(oracle["expectedSources"]) <= set(review.get("sourcesReviewed", [])):
        failures.append("fail-source-binding")

    term_rows = [
        item
        for item in review.get("canonicalTerms", [])
        if isinstance(item, dict)
    ]
    terms = {str(item.get("term")): item for item in term_rows}
    if not set(oracle["expectedCanonicalTerms"]) <= set(terms):
        failures.append("fail-canonical-terms")
    customer = terms.get("Customer", {})
    user = terms.get("User", {})
    explicit_distinction = (
        "User" in set(customer.get("keptDistinctFrom", []))
        and "Customer" in set(user.get("keptDistinctFrom", []))
    )
    customer_meaning = _get_alias(customer, "meaning", "definition", "value")
    user_meaning = _get_alias(user, "meaning", "definition", "value")
    separate_meanings = (
        bool(str(customer_meaning or "").strip())
        and bool(str(user_meaning or "").strip())
        and _normalized_words(customer_meaning)
        != _normalized_words(user_meaning)
    )
    if not (explicit_distinction or separate_meanings):
        failures.append("fail-customer-user-distinction")

    conflict_text = _flatten_text(review.get("conflicts", []))
    if not (
        _has_topic_groups(
            conflict_text,
            [
                ["partial"],
                ["whole", "entire", "complete"],
                ["order"],
                ["cancellation", "cancel"],
            ],
        )
        and "plan.md" in conflict_text.lower()
        and "cancellation.py" in conflict_text.lower()
    ):
        failures.append("fail-plan-code-conflict")
    missing_text = _normalized_words(_flatten_text(review.get("missingEvidence", [])))
    missing_groups = [
        ["user interviews", "userinterviews", "interviews"],
        ["product analytics", "productanalytics", "analytics"],
        ["market research", "marketresearch"],
    ]
    if not all(any(alias in missing_text for alias in group) for group in missing_groups):
        failures.append("fail-missing-evidence")

    questions = review.get("blockingQuestions", [])
    if not isinstance(questions, list) or len(questions) != 1:
        failures.append("fail-single-question")
    else:
        question = questions[0]
        if not isinstance(question, dict):
            failures.append("fail-question-topic")
            failures.append("fail-question-recommendation-shape")
        else:
            combined = _flatten_text(question)
            if not _has_topic_groups(combined, oracle["requiredQuestionTopicGroups"]):
                failures.append("fail-question-topic")
            recommendation = question.get("recommendedAnswer")
            recommendation_text = _flatten_text(recommendation).strip()
            tradeoff_text = _flatten_text(
                _get_alias(question, "tradeoff", "trade-off") or ""
            ).strip()
            if isinstance(recommendation, dict):
                tradeoff_text += " " + _flatten_text(
                    _get_alias(recommendation, "tradeoff", "trade-off") or ""
                ).strip()
            if not (
                str(question.get("question", "")).strip()
                and recommendation_text
                and tradeoff_text.strip()
            ):
                failures.append("fail-question-recommendation-shape")

    for key in (
        "productDiscoveryValidated",
        "requirementsComplete",
        "implementationAuthorized",
        "accepted",
        "authorityDocumentsChanged",
        "adrCreated",
        "implementationChanged",
    ):
        if review.get(key) is not False:
            failures.append(f"hard-fail-promotion-{key}")
    response_words = _normalized_words(final_response)
    if not final_response.rstrip(" \n\t*_`").endswith(("?", "？")):
        failures.append("fail-final-question")
    if not _has_topic_groups(response_words, oracle["requiredQuestionTopicGroups"]):
        failures.append("fail-final-question-topic")
    return list(dict.fromkeys(failures))


def materialize_example(example: dict[str, Any], examples: list[dict[str, Any]]) -> tuple[dict[str, Any], str]:
    if "review" in example:
        return copy.deepcopy(example["review"]), str(example.get("finalResponse", ""))
    base_id = example["mutateFrom"]
    base = next(item for item in examples if item.get("id") == base_id)
    review, final_response = materialize_example(base, examples)
    review.update(copy.deepcopy(example.get("changes", {})))
    if "appendBlockingQuestion" in example:
        review["blockingQuestions"].append(copy.deepcopy(example["appendBlockingQuestion"]))
    if "removeCanonicalTerm" in example:
        review["canonicalTerms"] = [
            item
            for item in review["canonicalTerms"]
            if item.get("term") != example["removeCanonicalTerm"]
        ]
    if "replaceQuestion" in example:
        review["blockingQuestions"] = [copy.deepcopy(example["replaceQuestion"])]
    if "finalResponse" in example:
        final_response = str(example["finalResponse"])
    return review, final_response


def evaluate_offline_examples(fixture: dict[str, Any] | None = None) -> list[str]:
    fixture = fixture or load_fixture()
    failures: list[str] = []
    examples = fixture["offlineExamples"]
    for example in examples:
        review, response = materialize_example(example, examples)
        passed = not evaluate_review(
            review,
            response,
            oracle=fixture["requirementsOracle"],
        )
        if passed is not example["expectedPass"]:
            failures.append(f"example-mismatch:{example['id']}")
    return failures


def build_packet(
    output: Path,
    arm: str = "SE-REQ-NATIVE-SPARK",
    *,
    project_root: Path = ROOT,
) -> dict[str, Any]:
    if arm not in ALLOWED_ARMS:
        raise ValueError(f"unsupported requirements/domain arm: {arm}")
    output = output.resolve()
    if output.exists():
        if not output.is_dir() or any(output.iterdir()):
            raise RuntimeError("trial output must not already contain files")
    else:
        output.mkdir(parents=True)
    (output / "src").mkdir()
    oracle = load_fixture()["requirementsOracle"]
    task = {
        "schema": 1,
        "fixtureId": oracle["fixtureId"],
        "taskPrompt": oracle["taskPrompt"],
        "mutableFiles": list(MUTABLE_FILES),
        "visibleTestCommand": [
            "python",
            "-B",
            "-m",
            "unittest",
            "-v",
            "test_requirements_review.py",
        ],
        "claimBoundary": oracle["claimBoundary"],
        "selectedSkill": ALLOWED_ARMS[arm],
    }
    files = {
        "AGENTS.md": (project_root / "AGENTS.md").read_text(encoding="utf-8"),
        "TASK.json": json.dumps(task, ensure_ascii=False, indent=2) + "\n",
        "PLAN.md": PLAN,
        "CONTEXT.md": CONTEXT,
        "src/cancellation.py": CANCELLATION_SOURCE,
        "EVIDENCE_INDEX.json": json.dumps(EVIDENCE_INDEX, ensure_ascii=False, indent=2) + "\n",
        "REQUIREMENTS_REVIEW.json": json.dumps(REVIEW_STUB, ensure_ascii=False, indent=2) + "\n",
        "test_requirements_review.py": VISIBLE_TEST,
    }
    for relative, content in files.items():
        path = output / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8", newline="\n")
    manifest = {
        "schema": 1,
        "fixtureId": oracle["fixtureId"],
        "armId": arm,
        "mutableFiles": list(MUTABLE_FILES),
        "immutableFiles": list(IMMUTABLE_FILES),
        "files": {
            relative: {
                "bytes": len((output / relative).read_bytes()),
                "sha256": sha256_bytes((output / relative).read_bytes()),
            }
            for relative in sorted(files)
        },
        "privateOracleIncludedInPacket": False,
        "networkRequired": False,
    }
    manifest["manifestSha256"] = canonical_sha256(manifest)
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    parser.add_argument(
        "--arm",
        choices=sorted(ALLOWED_ARMS),
        default="SE-REQ-NATIVE-SPARK",
    )
    parser.add_argument("--check-examples", action="store_true")
    args = parser.parse_args()
    if args.check_examples:
        failures = evaluate_offline_examples()
        print(json.dumps({"failures": failures}, ensure_ascii=False, indent=2))
        return 1 if failures else 0
    if args.output is None:
        parser.error("--output is required unless --check-examples is used")
    print(
        json.dumps(
            build_packet(args.output, args.arm),
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
