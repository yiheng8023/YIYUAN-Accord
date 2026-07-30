from __future__ import annotations

import ast
import copy
import inspect
import json
from pathlib import Path
import tempfile
import unittest
from typing import Any

import scripts.probe_codex_app_server_mcp_thread_creator_connection_close_auto_attach_v2 as probe
from scripts.validate_mcp_thread_creator_connection_close_auto_attach_v2 import (
    AMENDMENT_PATH,
    load_and_validate,
    validate_amendment,
    validate_protocol,
    validate_probe_source,
)


ROOT = Path(__file__).resolve().parent.parent
PROTOCOL_PATH = (
    ROOT
    / "registry"
    / "mcp-thread-creator-connection-close-auto-attach-protocol-v2-"
    "2026-07-27.json"
)


def sentinel_response(
    *,
    pid: int = 4100,
    instance_id: str = "sentinel-v2",
    call_id: str = "sentinel-v2:1",
) -> dict[str, Any]:
    return {
        "result": {
            "structuredContent": {
                "server": "agent-autonomy-harness-mcp-lifecycle-sentinel",
                "tool": "identity",
                "pid": pid,
                "instanceId": instance_id,
                "callId": call_id,
                "arguments": {},
            },
            "isError": False,
        }
    }


class FakeTransport:
    def __init__(
        self,
        owner: str,
        *,
        rollout_path: Path,
        sentinel_pid: int = 4100,
        sentinel_instance: str = "sentinel-v2",
    ) -> None:
        self.owner = owner
        self.rollout_path = rollout_path
        self.sentinel_pid = sentinel_pid
        self.sentinel_instance = sentinel_instance
        self.ledger: list[dict[str, Any]] = []
        self.closed = False
        self.call_count = 0

    def request(
        self,
        request_id: int,
        method: str,
        params: Any,
        *,
        phase: str,
        thread_id: str | None = None,
    ) -> dict[str, Any]:
        self.ledger.append(
            {
                "kind": "request",
                "id": request_id,
                "method": method,
                "params": copy.deepcopy(params),
                "phase": phase,
                "threadId": thread_id,
            }
        )
        if method == "initialize":
            return {"result": {"codexHome": "C:/offline"}}
        if method == "config/read":
            return {"result": {"config": {}}}
        if method == "thread/start":
            return {
                "result": {
                    "thread": {
                        "id": "thread-v2",
                        "path": self.rollout_path.as_posix(),
                    }
                }
            }
        if method == "mcpServer/tool/call":
            self.call_count += 1
            return sentinel_response(
                pid=self.sentinel_pid,
                instance_id=self.sentinel_instance,
                call_id=f"{self.sentinel_instance}:{self.call_count}",
            )
        raise AssertionError(f"unexpected request: {method}")

    def notify(
        self,
        method: str,
        params: Any,
        *,
        phase: str,
    ) -> None:
        self.ledger.append(
            {
                "kind": "notify",
                "method": method,
                "params": params,
                "phase": phase,
            }
        )

    def close(self) -> None:
        self.closed = True


class AutoAttachV2ProbeTests(unittest.TestCase):
    def run_arm(
        self,
        *,
        observer_instance: str = "sentinel-v2",
        sample_window=None,
    ):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        root = Path(directory.name)
        rollout = root / "rollout.jsonl"
        creator = FakeTransport("creator-a", rollout_path=rollout)
        observer = FakeTransport(
            "observer-b",
            rollout_path=rollout,
            sentinel_instance=observer_instance,
        )
        cleanup_calls: list[str] = []
        trace = probe.execute_offline_injected_arm(
            arm=probe.ARM_CONTROL,
            creator_a=creator,
            observer_b=observer,
            workspace=root,
            sample_window=sample_window
            or (
                lambda arm, thread_id: {
                    "arm": arm,
                    "threadId": thread_id,
                    "samples": 11,
                }
            ),
            bounded_cleanup=lambda: cleanup_calls.append("sentinel"),
        )
        return trace, creator, observer, cleanup_calls

    def test_exact_auto_attach_rpc_order(self) -> None:
        trace, creator, observer, cleanup = self.run_arm()
        combined = trace["events"]
        self.assertLess(
            combined.index("observer-b:config/read"),
            combined.index("creator-a:thread/start"),
        )
        self.assertEqual(
            [entry["method"] for entry in observer.ledger],
            [
                "initialize",
                "initialized",
                "config/read",
                "mcpServer/tool/call",
                "mcpServer/tool/call",
            ],
        )
        self.assertEqual(
            [entry["method"] for entry in creator.ledger],
            [
                "initialize",
                "initialized",
                "thread/start",
                "mcpServer/tool/call",
            ],
        )
        self.assertEqual(cleanup, ["sentinel"])

    def test_connection_b_never_resumes(self) -> None:
        _, _, observer, _ = self.run_arm()
        self.assertNotIn(
            "thread/resume",
            [entry["method"] for entry in observer.ledger],
        )
        direct_calls = [
            entry
            for entry in observer.ledger
            if entry["method"] == "mcpServer/tool/call"
        ]
        self.assertEqual(len(direct_calls), 2)
        self.assertTrue(
            all(entry["threadId"] == "thread-v2" for entry in direct_calls)
        )

    def test_thread_start_is_read_only_and_non_ephemeral(self) -> None:
        _, creator, _, _ = self.run_arm()
        start = next(
            entry
            for entry in creator.ledger
            if entry["method"] == "thread/start"
        )
        self.assertIs(start["params"]["ephemeral"], False)
        self.assertEqual(start["params"]["sandbox"], "read-only")
        self.assertEqual(start["params"]["approvalPolicy"], "never")

    def test_rollout_absence_is_diagnostic_only(self) -> None:
        trace, _, _, _ = self.run_arm()
        self.assertEqual(
            trace["thread"]["rolloutMaterialization"]["role"],
            "diagnostic-only",
        )
        self.assertFalse(
            trace["thread"]["rolloutMaterialization"]["observed"]
        )

    def test_same_thread_and_exact_sentinel_are_bound(self) -> None:
        trace, _, _, _ = self.run_arm()
        self.assertEqual(trace["thread"]["id"], "thread-v2")
        self.assertTrue(trace["baseline"]["sameThread"])
        self.assertTrue(trace["baseline"]["sameExactSentinel"])
        self.assertEqual(
            trace["baseline"]["creatorCall"]["instanceId"],
            trace["baseline"]["observerCall"]["instanceId"],
        )

    def test_sentinel_identity_mismatch_fails_and_cleans_up(self) -> None:
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        root = Path(directory.name)
        rollout = root / "rollout.jsonl"
        creator = FakeTransport("creator-a", rollout_path=rollout)
        observer = FakeTransport(
            "observer-b",
            rollout_path=rollout,
            sentinel_instance="different-sentinel",
        )
        cleanup_calls: list[str] = []
        with self.assertRaisesRegex(
            probe.OfflineProbeFailure, "same exact Sentinel"
        ) as caught:
            probe.execute_offline_injected_arm(
                arm=probe.ARM_CONTROL,
                creator_a=creator,
                observer_b=observer,
                workspace=root,
                sample_window=lambda arm, thread_id: {},
                bounded_cleanup=lambda: cleanup_calls.append("sentinel"),
            )
        self.assertTrue(creator.closed)
        self.assertTrue(observer.closed)
        self.assertEqual(cleanup_calls, ["sentinel"])
        self.assertEqual(
            caught.exception.trace["failure"]["type"], "RuntimeError"
        )
        self.assertTrue(
            caught.exception.trace["cleanup"]["boundedCleanupInvoked"]
        )

    def test_window_failure_closes_both_transports_and_cleans_sentinel(
        self,
    ) -> None:
        def fail_window(arm: str, thread_id: str) -> dict[str, Any]:
            raise RuntimeError("simulated-window-failure")

        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        root = Path(directory.name)
        rollout = root / "rollout.jsonl"
        creator = FakeTransport("creator-a", rollout_path=rollout)
        observer = FakeTransport("observer-b", rollout_path=rollout)
        cleanup_calls: list[str] = []
        with self.assertRaisesRegex(
            RuntimeError, "simulated-window-failure"
        ):
            probe.execute_offline_injected_arm(
                arm=probe.ARM_CREATOR_CLOSE,
                creator_a=creator,
                observer_b=observer,
                workspace=root,
                sample_window=fail_window,
                bounded_cleanup=lambda: cleanup_calls.append("sentinel"),
            )
        self.assertTrue(creator.closed)
        self.assertTrue(observer.closed)
        self.assertEqual(cleanup_calls, ["sentinel"])

    def test_cleanup_failure_does_not_skip_remaining_cleanup(self) -> None:
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        root = Path(directory.name)
        rollout = root / "rollout.jsonl"
        creator = FakeTransport("creator-a", rollout_path=rollout)
        observer = FakeTransport("observer-b", rollout_path=rollout)
        cleanup_calls: list[str] = []

        def fail_creator_close() -> None:
            raise RuntimeError("creator-close-failed")

        creator.close = fail_creator_close  # type: ignore[method-assign]
        with self.assertRaisesRegex(
            probe.OfflineProbeFailure, "offline cleanup failed"
        ) as caught:
            probe.execute_offline_injected_arm(
                arm=probe.ARM_CONTROL,
                creator_a=creator,
                observer_b=observer,
                workspace=root,
                sample_window=lambda arm, thread_id: {},
                bounded_cleanup=lambda: cleanup_calls.append("sentinel"),
            )
        self.assertTrue(observer.closed)
        self.assertEqual(cleanup_calls, ["sentinel"])
        self.assertEqual(
            caught.exception.trace["cleanup"]["errors"][0]["target"],
            "creator-a",
        )

    def test_evidence_is_sealed_before_observer_post_window_call(self) -> None:
        trace, _, _, _ = self.run_arm()
        self.assertTrue(
            trace["evidenceSealedBeforeObserverPostWindowCall"]
        )
        self.assertLess(
            trace["events"].index("evidence:seal"),
            trace["events"].index(
                "observer-b:mcpServer/tool/call:post-window"
            ),
        )
        self.assertTrue(trace["evidenceSeal"]["sealed"])

    def test_probe_ast_has_no_live_or_model_transport(self) -> None:
        tree = ast.parse(inspect.getsource(probe))
        imported_roots: set[str] = set()
        requested_methods: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported_roots.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported_roots.add(node.module.split(".")[0])
            elif isinstance(node, ast.Call):
                if (
                    isinstance(node.func, ast.Attribute)
                    and node.func.attr == "request"
                    and len(node.args) > 1
                    and isinstance(node.args[1], ast.Constant)
                    and isinstance(node.args[1].value, str)
                ):
                    requested_methods.append(node.args[1].value)
        self.assertTrue(
            imported_roots.isdisjoint(
                {
                    "socket",
                    "subprocess",
                    "requests",
                    "urllib",
                    "websocket",
                    "websockets",
                }
            )
        )
        self.assertNotIn("turn/start", requested_methods)
        self.assertNotIn("thread/resume", requested_methods)
        self.assertNotIn("thread/unsubscribe", requested_methods)
        self.assertIn("thread/start", requested_methods)
        self.assertIn("mcpServer/tool/call", requested_methods)

    def test_protocol_has_zero_live_runs_and_no_authority(self) -> None:
        protocol = json.loads(PROTOCOL_PATH.read_text(encoding="utf-8"))
        self.assertEqual(protocol["formalRunCount"], 0)
        boundary = protocol["executionBoundary"]
        self.assertFalse(boundary["formalLivePairedRunsExecuted"])
        for key in (
            "appServerStartAuthorized",
            "loopbackTransportExecutionAuthorized",
            "modelOrAccountUseAuthorized",
            "externalNetworkUseAuthorized",
            "globalConfigurationMutationAuthorized",
            "installationAuthorized",
            "liveProtocolExecutionAuthorized",
        ):
            self.assertFalse(boundary[key], msg=key)
        self.assertTrue(
            all(
                value is False
                for value in protocol["claimBoundary"].values()
            )
        )

    def test_v2_protocol_and_amendment_validator_pass(self) -> None:
        load_and_validate(root=ROOT)

    def test_validator_rejects_formal_run_promotion(self) -> None:
        protocol = json.loads(PROTOCOL_PATH.read_text(encoding="utf-8"))
        protocol["formalRunCount"] = 1
        with self.assertRaisesRegex(RuntimeError, "formal-run boundary"):
            validate_protocol(protocol)

    def test_validator_rejects_setup_order_drift(self) -> None:
        protocol = json.loads(PROTOCOL_PATH.read_text(encoding="utf-8"))
        sequence = protocol["design"]["setupSequence"]
        sequence[1], sequence[3] = sequence[3], sequence[1]
        with self.assertRaisesRegex(RuntimeError, "setup sequence drifted"):
            validate_protocol(protocol)

    def test_validator_rejects_resume_request_in_probe(self) -> None:
        source = inspect.getsource(probe) + (
            "\ndef forbidden(connection):\n"
            '    connection.request(9, "thread/resume", {}, phase="bad")\n'
        )
        with self.assertRaisesRegex(RuntimeError, "forbidden host RPC"):
            validate_probe_source(source)

    def test_validator_rejects_live_authority_or_claim_promotion(self) -> None:
        amendment = json.loads(
            (ROOT / AMENDMENT_PATH).read_text(encoding="utf-8")
        )
        promoted = copy.deepcopy(amendment)
        promoted["executionBoundary"]["appServerStartAuthorized"] = True
        with self.assertRaisesRegex(RuntimeError, "execution boundary"):
            validate_amendment(promoted)
        promoted = copy.deepcopy(amendment)
        promoted["claimBoundary"]["leaseOrReferenceCountProved"] = True
        with self.assertRaisesRegex(RuntimeError, "claim boundary"):
            validate_amendment(promoted)


if __name__ == "__main__":
    unittest.main()
