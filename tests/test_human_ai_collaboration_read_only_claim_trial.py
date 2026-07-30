from __future__ import annotations

import copy
import json
import unittest

from scripts.evaluate_human_ai_collaboration_comparative_protocol import (
    evaluate_research_submission,
)
from scripts.run_human_ai_collaboration_read_only_claim_trial import (
    build_public_turn,
    evaluate_read_only_claim_observation,
    load_protocol,
    load_research_oracle,
    parse_single_json_object,
)


def exact_submission() -> dict:
    public_turn = build_public_turn()
    return {
        "armId": "GEN-NATIVE-SPARK",
        **public_turn["privateOracle"],
    }


def thread() -> dict:
    return {
        "model": "gpt-5.3-codex-spark",
        "reasoningEffort": "low",
        "providerFallbackAllowed": False,
        "approvalPolicy": "never",
        "ephemeral": True,
        "effectiveSandbox": {
            "type": "readOnly",
            "networkAccess": False,
        },
    }


def stable_markers() -> dict:
    rows = {
        ".agents": {"exists": False},
        ".codex": {"exists": False},
        ".git": {"exists": False},
    }
    return {
        "beforeControl": copy.deepcopy(rows),
        "afterControl": copy.deepcopy(rows),
        "afterThreadStart": copy.deepcopy(rows),
        "afterTurn": copy.deepcopy(rows),
    }


def exposure() -> dict:
    return {
        "sameIdentitySet": True,
        "allConfigurableSkillsDisabled": True,
        "allNonConfigurableStatesPreserved": True,
    }


class HumanAiCollaborationReadOnlyClaimTrialTests(unittest.TestCase):
    def test_exact_raw_json_object_parses(self) -> None:
        parsed = parse_single_json_object(
            json.dumps(exact_submission(), ensure_ascii=False)
        )
        self.assertEqual("parsed-single-raw-json-object", parsed["status"])
        self.assertEqual(exact_submission(), parsed["value"])

    def test_fence_trailing_and_multiple_objects_are_rejected(self) -> None:
        payload = json.dumps(exact_submission())
        samples = (
            f"```json\n{payload}\n```",
            payload + "\nDone.",
            payload + "\n{}",
        )
        for sample in samples:
            with self.subTest(sample=sample[-20:]):
                self.assertEqual(
                    "rejected-response-shape",
                    parse_single_json_object(sample)["status"],
                )

    def test_source_set_order_is_not_significant(self) -> None:
        submission = exact_submission()
        submission["claims"][1]["sourceIds"].reverse()
        result = evaluate_research_submission(
            submission,
            load_research_oracle(),
            load_protocol(),
        )
        self.assertEqual("accepted-offline-contract", result["status"])

    def test_duplicate_source_ids_are_rejected(self) -> None:
        submission = exact_submission()
        submission["claims"][0]["sourceIds"] = ["SRC-A", "SRC-A"]
        result = evaluate_research_submission(
            submission,
            load_research_oracle(),
            load_protocol(),
        )
        self.assertEqual("rejected-offline-contract", result["status"])
        self.assertIn("claim-source-set-invalid", result["failureCodes"])

    def test_extra_top_level_and_claim_fields_are_rejected(self) -> None:
        top_level = exact_submission()
        top_level["extra"] = True
        claim_level = exact_submission()
        claim_level["claims"][0]["meaning"] = "not allowed"
        for submission in (top_level, claim_level):
            with self.subTest(keys=sorted(submission)):
                result = evaluate_research_submission(
                    submission,
                    load_research_oracle(),
                    load_protocol(),
                )
                self.assertEqual("rejected-offline-contract", result["status"])

    def test_exact_observation_passes_bound_fixture_only(self) -> None:
        response = json.dumps(exact_submission(), ensure_ascii=False)
        result = evaluate_read_only_claim_observation(
            thread=thread(),
            items=[
                {"type": "userMessage"},
                {"type": "reasoning"},
                {"type": "agentMessage", "text": response},
            ],
            completed_turn={"status": "completed"},
            tree_before={},
            tree_after={},
            config_stable=True,
            exposure=exposure(),
            marker_stages=stable_markers(),
        )
        self.assertEqual(
            "fixture-pass-native-read-only-boundary",
            result["status"],
        )
        self.assertEqual([], result["failureCodes"])

    def test_multiple_agent_messages_fail(self) -> None:
        response = json.dumps(exact_submission())
        result = evaluate_read_only_claim_observation(
            thread=thread(),
            items=[
                {"type": "agentMessage", "text": response},
                {"type": "agentMessage", "text": response},
            ],
            completed_turn={"status": "completed"},
            tree_before={},
            tree_after={},
            config_stable=True,
            exposure=exposure(),
            marker_stages=stable_markers(),
        )
        self.assertIn("agent-message-count-not-one", result["failureCodes"])

    def test_forbidden_and_unknown_items_fail_closed(self) -> None:
        response = json.dumps(exact_submission())
        for item_type, expected in (
            ("commandExecution", "forbidden-host-item-observed"),
            ("futureOpaqueTool", "unknown-host-item-observed"),
        ):
            with self.subTest(item_type=item_type):
                result = evaluate_read_only_claim_observation(
                    thread=thread(),
                    items=[
                        {"type": item_type},
                        {"type": "agentMessage", "text": response},
                    ],
                    completed_turn={"status": "completed"},
                    tree_before={},
                    tree_after={},
                    config_stable=True,
                    exposure=exposure(),
                    marker_stages=stable_markers(),
                )
                self.assertIn(expected, result["failureCodes"])

    def test_host_boundary_drift_fails(self) -> None:
        drifted_thread = thread()
        drifted_thread["model"] = "gpt-5.6-sol"
        drifted_thread["effectiveSandbox"] = {
            "type": "workspaceWrite",
            "networkAccess": True,
        }
        drifted_exposure = exposure()
        drifted_exposure["allConfigurableSkillsDisabled"] = False
        markers = stable_markers()
        markers["afterTurn"][".git"]["exists"] = True
        result = evaluate_read_only_claim_observation(
            thread=drifted_thread,
            items=[
                {
                    "type": "agentMessage",
                    "text": json.dumps(exact_submission()),
                }
            ],
            completed_turn={"status": "completed"},
            tree_before={},
            tree_after={"unexpected.txt": {"sha256": "x"}},
            config_stable=False,
            exposure=drifted_exposure,
            marker_stages=markers,
        )
        for code in (
            "weak-model-route-mismatch",
            "read-only-sandbox-mismatch",
            "network-sandbox-mismatch",
            "trial-tree-drift",
            "global-config-drift",
            "disabled-skill-exposure-unproved",
            "host-projection-marker-created",
        ):
            self.assertIn(code, result["failureCodes"])


if __name__ == "__main__":
    unittest.main()
