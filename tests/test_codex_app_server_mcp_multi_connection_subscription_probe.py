from __future__ import annotations

import os
from pathlib import Path
import sys
import unittest
from unittest import mock

from scripts.probe_codex_app_server_mcp_multi_connection_subscription import (
    EXPECTED_SEQUENCES,
    classify_preflight,
)

THREAD_ID = "019f-test-thread"


def complete_identity(pid: int, image: str) -> dict[str, object]:
    return {
        "exists": True,
        "pid": pid,
        "creationTime100ns": pid * 10,
        "imagePath": image,
        "parentPid": max(1, pid - 1),
    }


def ledger(
    owner_id: str,
    acquisition_path: str = "thread-resume",
) -> list[dict[str, object]]:
    return [
        {
            "ownerId": owner_id,
            "method": method,
            "requestSha256": f"request-{index}",
            "responseExpected": method != "initialized",
            **(
                {"threadId": THREAD_ID}
                if method not in {"initialize", "initialized", "config/read"}
                else {}
            ),
            **(
                {"responseSha256": f"response-{index}"}
                if method != "initialized"
                else {}
            ),
        }
        for index, method in enumerate(
            EXPECTED_SEQUENCES[acquisition_path][owner_id]
        )
    ]


class MultiConnectionSubscriptionProbeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.sentinel = complete_identity(os.getpid(), sys.executable)
        self.thread_id = THREAD_ID
        self.instance_id = "instance-1"
        self.call = {
            "pid": os.getpid(),
            "instanceId": self.instance_id,
        }
        self.kwargs = {
            "acquisition_path": "thread-resume",
            "app_server_process": self.sentinel,
            "executable": sys.executable,
            "owner_a_bridge": complete_identity(
                os.getpid() + 10000, sys.executable
            ),
            "owner_b_bridge": complete_identity(
                os.getpid() + 10001, sys.executable
            ),
            "owner_a_ledger": ledger("owner-a"),
            "owner_b_ledger": ledger("owner-b"),
            "thread_id_a": self.thread_id,
            "thread_id_b": self.thread_id,
            "owner_a_baseline": dict(self.call),
            "owner_b_join_call": dict(self.call),
            "owner_b_after_a_release": dict(self.call),
            "sentinel_process": self.sentinel,
            "owner_a_statuses": ["unsubscribed", "notSubscribed"],
            "owner_b_statuses": ["unsubscribed", "notSubscribed"],
            "events_before_harness_shutdown": [
                {
                    "event": "instance-start",
                    "pid": os.getpid(),
                    "instanceId": self.instance_id,
                }
            ],
            "app_server_alive_before_harness_shutdown": True,
            "messages": [],
        }

    def classify(self, **updates: object) -> dict[str, object]:
        values = dict(self.kwargs)
        values.update(updates)
        with mock.patch(
            "scripts.probe_codex_app_server_mcp_multi_connection_subscription.snapshot_process",
            return_value=self.sentinel,
        ):
            return classify_preflight(**values)

    def test_valid_distinct_connections_are_classified_bounded(self) -> None:
        result = self.classify()
        self.assertTrue(result["valid"])
        self.assertEqual(
            result["classification"],
            "multi-connection-overlapping-subscription-observed-bounded",
        )
        self.assertTrue(result["firstConnectionReleasePreservedSecondConnectionCall"])
        self.assertFalse(result["publicSubscriberCountObserved"])
        self.assertFalse(result["publicLeaseOrReferenceCountApiObserved"])
        self.assertFalse(result["finalReleaseObserved"])
        self.assertFalse(result["taskEndSemanticsObserved"])

    def test_same_bridge_process_cannot_impersonate_two_connections(self) -> None:
        same = self.kwargs["owner_a_bridge"]
        result = self.classify(owner_b_bridge=same)
        self.assertFalse(result["valid"])
        self.assertIn("connections-not-distinct", result["invalidReasons"])

    def test_different_thread_is_rejected(self) -> None:
        result = self.classify(thread_id_b="different-thread")
        self.assertFalse(result["valid"])
        self.assertIn("thread-id-mismatch", result["invalidReasons"])

    def test_sentinel_reinstantiation_is_rejected(self) -> None:
        changed = dict(self.call)
        changed["instanceId"] = "instance-2"
        result = self.classify(owner_b_after_a_release=changed)
        self.assertFalse(result["valid"])
        self.assertIn(
            "sentinel-call-identity-mismatch", result["invalidReasons"]
        )

    def test_unsubscribe_statuses_must_be_connection_scoped(self) -> None:
        result = self.classify(
            owner_a_statuses=["unsubscribed", "unsubscribed"]
        )
        self.assertFalse(result["valid"])
        self.assertIn(
            "owner-a-unsubscribe-sequence-mismatch",
            result["invalidReasons"],
        )

    def test_absent_second_subscription_is_a_valid_negative_result(self) -> None:
        result = self.classify(
            owner_b_statuses=["notSubscribed", "notSubscribed"]
        )
        self.assertTrue(result["valid"])
        self.assertEqual(
            result["classification"],
            "second-connection-subscription-not-observed-bounded",
        )
        self.assertFalse(result["secondConnectionSubscriptionObserved"])
        self.assertFalse(result["overlappingSubscriptionObserved"])

    def test_auto_attach_path_can_record_the_same_negative_result(self) -> None:
        result = self.classify(
            acquisition_path="thread-created-auto-attach",
            owner_b_ledger=ledger(
                "owner-b", "thread-created-auto-attach"
            ),
            owner_b_statuses=["notSubscribed", "notSubscribed"],
        )
        self.assertTrue(result["valid"])
        self.assertEqual(
            result["classification"],
            "second-connection-subscription-not-observed-bounded",
        )

    def test_method_sequence_rejects_forbidden_turn(self) -> None:
        owner_b = ledger("owner-b")
        owner_b.append(
            {
                "ownerId": "owner-b",
                "method": "turn/start",
                "requestSha256": "request-turn",
                "responseExpected": True,
                "responseSha256": "response-turn",
            }
        )
        result = self.classify(owner_b_ledger=owner_b)
        self.assertFalse(result["valid"])
        self.assertIn("owner-b-method-sequence-mismatch", result["invalidReasons"])
        self.assertIn("model-turn-requested", result["invalidReasons"])

    def test_missing_response_hash_is_rejected(self) -> None:
        owner_a = ledger("owner-a")
        owner_a[0].pop("responseSha256")
        result = self.classify(owner_a_ledger=owner_a)
        self.assertFalse(result["valid"])
        self.assertIn("owner-a-ledger-hash-missing", result["invalidReasons"])

    def test_turn_started_notification_is_rejected(self) -> None:
        result = self.classify(
            messages=[{"method": "turn/started", "params": {}}]
        )
        self.assertFalse(result["valid"])
        self.assertIn(
            "model-turn-notification-observed", result["invalidReasons"]
        )

    def test_bridge_uses_node_builtin_websocket_without_packages(self) -> None:
        source = (
            Path(__file__).resolve().parents[1]
            / "scripts"
            / "codex_app_server_websocket_bridge.mjs"
        ).read_text(encoding="utf-8")
        self.assertIn("new WebSocket(", source)
        self.assertNotIn("from \"ws\"", source)
        self.assertNotIn("require(\"ws\")", source)


if __name__ == "__main__":
    unittest.main()
