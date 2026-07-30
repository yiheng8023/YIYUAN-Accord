import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from scripts.probe_codex_app_server_mcp_child_exit_recovery import (
    CONTROL_SERVER,
    CRASH_EXIT_CODE,
    PROBE_ID,
    VICTIM_SERVER,
    build_dual_server_config,
    build_initial_requests,
    build_tool_call_request,
    classify_child_exit_result,
    run_probe,
)


ROOT = Path(__file__).resolve().parent.parent
SENTINEL = ROOT / "scripts/mcp_lifecycle_sentinel.py"


def rpc(request_id: int, method: str, params: dict) -> dict:
    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "method": method,
        "params": params,
    }


def full_acceptance_facts() -> dict:
    return {
        "baselineControlSucceeded": True,
        "baselineVictimSucceeded": True,
        "crashAttempted": True,
        "crashCallSucceeded": False,
        "crashRequestEventObserved": True,
        "originalVictimNaturalStopEventObserved": False,
        "originalVictimExactIdentityAbsent": True,
        "appServerExistsAfterCrash": True,
        "appServerSameExactIdentityAfterCrash": True,
        "appServerSameExactIdentityAfterCalls": True,
        "controlPostCrashSucceeded": True,
        "controlSameInstanceId": True,
        "controlSameExactIdentity": True,
        "sameThreadRecoverySucceeded": True,
        "recoveryNewInstanceId": True,
        "recoveryExactIdentityBound": True,
        "fallbackRecoverySucceeded": False,
        "fallbackNewInstanceId": False,
        "fallbackExactIdentityBound": False,
        "simultaneousLiveVictimExactIdentityCount": 1,
        "allLoggedInstancesExactlyBound": True,
        "loggedTopologyMatchesExpected": True,
        "configUnchanged": True,
        "authStateProduced": False,
        "crashTokenLeakedInEventLogs": False,
        "cleanupSafe": True,
    }


class CodexAppServerMcpChildExitRecoveryProbeTests(unittest.TestCase):
    def test_dual_config_gates_crash_to_victim_alias_only(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            token = "fixture-one-process-token"
            text = build_dual_server_config(
                Path(sys.executable),
                SENTINEL,
                root / "control.jsonl",
                root / "victim.jsonl",
                root / "control.marker",
                root / "victim.marker",
                token,
            )
        self.assertIn(f"[mcp_servers.{CONTROL_SERVER}]", text)
        self.assertIn(f"[mcp_servers.{VICTIM_SERVER}]", text)
        control, victim = text.split(f"[mcp_servers.{VICTIM_SERVER}]")
        self.assertNotIn("--allow-crash-token", control)
        self.assertNotIn(token, control)
        self.assertIn("--allow-crash-token", victim)
        self.assertEqual(1, text.count(token))
        self.assertEqual(2, text.count("enabled = true"))
        with self.assertRaisesRegex(ValueError, "non-empty"):
            build_dual_server_config(
                Path(sys.executable),
                SENTINEL,
                Path("control.jsonl"),
                Path("victim.jsonl"),
                Path("control.marker"),
                Path("victim.marker"),
                "",
            )

    def test_request_builders_exclude_turn_status_and_reload(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            requests = build_initial_requests(Path(temp))
        requests.extend(
            [
                build_tool_call_request(
                    2,
                    "thread-fixture",
                    CONTROL_SERVER,
                    "identity",
                    {"probe": PROBE_ID},
                ),
                build_tool_call_request(
                    3,
                    "thread-fixture",
                    VICTIM_SERVER,
                    "crash",
                    {"token": "fixture"},
                ),
            ]
        )
        methods = [request["method"] for request in requests]
        self.assertEqual(
            [
                "initialize",
                "initialized",
                "thread/start",
                "mcpServer/tool/call",
                "mcpServer/tool/call",
            ],
            methods,
        )
        self.assertNotIn("turn/start", methods)
        self.assertNotIn("mcpServerStatus/list", methods)
        self.assertNotIn("config/mcpServer/reload", methods)

    def test_sentinel_does_not_advertise_or_execute_crash_by_default(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            event_log = Path(temp) / "events.jsonl"
            process = subprocess.Popen(
                [
                    sys.executable,
                    "-B",
                    str(SENTINEL),
                    "--event-log",
                    str(event_log),
                ],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
            )
            requests = [
                rpc(
                    0,
                    "initialize",
                    {"protocolVersion": "2024-11-05"},
                ),
                rpc(1, "tools/list", {}),
                rpc(
                    2,
                    "tools/call",
                    {"name": "crash", "arguments": {"token": "unused"}},
                ),
                rpc(3, "tools/call", {"name": "identity", "arguments": {}}),
            ]
            stdout, stderr = process.communicate(
                "".join(json.dumps(request) + "\n" for request in requests),
                timeout=10,
            )
            responses = {
                response["id"]: response
                for response in map(json.loads, stdout.splitlines())
            }
            tools = [tool["name"] for tool in responses[1]["result"]["tools"]]
            self.assertNotIn("crash", tools)
            self.assertTrue(responses[2]["result"]["isError"])
            self.assertFalse(responses[3]["result"]["isError"])
            self.assertEqual("", stderr)
            self.assertEqual(0, process.returncode)
            events = [
                json.loads(line)
                for line in event_log.read_text(encoding="utf-8").splitlines()
            ]
            self.assertNotIn("crash-requested", [event["event"] for event in events])

    def test_sentinel_rejects_wrong_token_without_recording_it(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            event_log = Path(temp) / "events.jsonl"
            allowed = "allowed-fixture-token"
            rejected = "rejected-fixture-token"
            process = subprocess.Popen(
                [
                    sys.executable,
                    "-B",
                    str(SENTINEL),
                    "--event-log",
                    str(event_log),
                    "--allow-crash-token",
                    allowed,
                ],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
            )
            requests = [
                rpc(
                    0,
                    "initialize",
                    {"protocolVersion": "2024-11-05"},
                ),
                rpc(1, "tools/list", {}),
                rpc(
                    2,
                    "tools/call",
                    {"name": "crash", "arguments": {"token": rejected}},
                ),
                rpc(3, "tools/call", {"name": "identity", "arguments": {}}),
            ]
            stdout, stderr = process.communicate(
                "".join(json.dumps(request) + "\n" for request in requests),
                timeout=10,
            )
            responses = {
                response["id"]: response
                for response in map(json.loads, stdout.splitlines())
            }
            tools = [tool["name"] for tool in responses[1]["result"]["tools"]]
            self.assertIn("crash", tools)
            self.assertTrue(responses[2]["result"]["isError"])
            self.assertFalse(responses[3]["result"]["isError"])
            self.assertEqual("", stderr)
            self.assertEqual(0, process.returncode)
            text = event_log.read_text(encoding="utf-8")
            self.assertNotIn(allowed, text)
            self.assertNotIn(rejected, text)
            events = [json.loads(line) for line in text.splitlines()]
            self.assertIn("crash-rejected", [event["event"] for event in events])
            self.assertNotIn("crash-requested", [event["event"] for event in events])

    def test_sentinel_matching_token_exits_before_tool_response(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            event_log = Path(temp) / "events.jsonl"
            token = "one-process-fixture-token"
            process = subprocess.Popen(
                [
                    sys.executable,
                    "-B",
                    str(SENTINEL),
                    "--event-log",
                    str(event_log),
                    "--allow-crash-token",
                    token,
                ],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
            )
            requests = [
                rpc(
                    0,
                    "initialize",
                    {"protocolVersion": "2024-11-05"},
                ),
                rpc(1, "tools/list", {}),
                rpc(
                    2,
                    "tools/call",
                    {"name": "crash", "arguments": {"token": token}},
                ),
            ]
            stdout, stderr = process.communicate(
                "".join(json.dumps(request) + "\n" for request in requests),
                timeout=10,
            )
            responses = {
                response["id"]: response
                for response in map(json.loads, stdout.splitlines())
            }
            self.assertEqual({0, 1}, set(responses))
            self.assertIn(
                "crash",
                [tool["name"] for tool in responses[1]["result"]["tools"]],
            )
            self.assertEqual("", stderr)
            self.assertEqual(CRASH_EXIT_CODE, process.returncode)
            text = event_log.read_text(encoding="utf-8")
            self.assertNotIn(token, text)
            events = [json.loads(line) for line in text.splitlines()]
            crash_events = [
                event for event in events if event["event"] == "crash-requested"
            ]
            self.assertEqual(1, len(crash_events))
            self.assertTrue(crash_events[0]["tokenMatched"])
            self.assertEqual(CRASH_EXIT_CODE, crash_events[0]["exitCode"])
            self.assertNotIn("instance-stop", [event["event"] for event in events])

    def test_classifier_accepts_only_strict_same_thread_isolation(self) -> None:
        result = classify_child_exit_result(full_acceptance_facts())
        self.assertTrue(result["accepted"])
        self.assertEqual(
            "observed-single-host-abrupt-child-exit-isolated-and-"
            "same-thread-next-call-recovery",
            result["resultClass"],
        )
        self.assertEqual("observed", result["dimensions"]["injection"])
        self.assertEqual(
            "same-instance", result["dimensions"]["controlIsolation"]
        )
        self.assertEqual(
            "none-among-logged-and-bound",
            result["dimensions"]["duplicateOrLeak"],
        )

    def test_classifier_separates_fallback_failure_and_cleanup(self) -> None:
        fallback = full_acceptance_facts()
        fallback.update(
            {
                "sameThreadRecoverySucceeded": False,
                "recoveryNewInstanceId": False,
                "recoveryExactIdentityBound": False,
                "fallbackRecoverySucceeded": True,
                "fallbackNewInstanceId": True,
                "fallbackExactIdentityBound": True,
                "loggedTopologyMatchesExpected": False,
            }
        )
        result = classify_child_exit_result(fallback)
        self.assertFalse(result["accepted"])
        self.assertEqual("partial-new-thread-recovery-only", result["resultClass"])

        control_failure = full_acceptance_facts()
        control_failure["controlSameInstanceId"] = False
        result = classify_child_exit_result(control_failure)
        self.assertEqual(
            "falsified-control-mcp-restarted-or-unavailable",
            result["resultClass"],
        )

        duplicate = full_acceptance_facts()
        duplicate["simultaneousLiveVictimExactIdentityCount"] = 2
        result = classify_child_exit_result(duplicate)
        self.assertEqual(
            "falsified-duplicate-victim-or-leak-observed",
            result["resultClass"],
        )

        cleanup = full_acceptance_facts()
        cleanup["cleanupSafe"] = False
        result = classify_child_exit_result(cleanup)
        self.assertEqual(
            "cleanup-incomplete-result-not-admissible",
            result["resultClass"],
        )

    def test_classifier_rejects_graceful_stop_and_token_leak(self) -> None:
        graceful = full_acceptance_facts()
        graceful["originalVictimNaturalStopEventObserved"] = True
        result = classify_child_exit_result(graceful)
        self.assertEqual(
            "falsified-crash-injection-graceful-stop-observed",
            result["resultClass"],
        )

        leaked = full_acceptance_facts()
        leaked["crashTokenLeakedInEventLogs"] = True
        result = classify_child_exit_result(leaked)
        self.assertEqual(
            "invalid-isolation-boundary-crash-token-leaked",
            result["resultClass"],
        )

    @unittest.skipUnless(os.name == "nt", "probe launch guard is Windows-only")
    def test_probe_rejects_nonempty_root_before_launch(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "preserve.txt").write_text("preserve", encoding="utf-8")
            with self.assertRaisesRegex(RuntimeError, "absent or empty"):
                run_probe(root, SENTINEL, None, 1, 1, 1)


if __name__ == "__main__":
    unittest.main()
