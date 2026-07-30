import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
from unittest import mock

from scripts.probe_codex_app_server_mcp_tool_call import (
    PROBE_ID,
    SERVER_NAME,
    build_initial_requests,
    build_isolated_config,
    build_thread_requests,
    extract_tool_payload,
    process_exists,
    resolve_native_codex_executable,
    run_probe,
)


ROOT = Path(__file__).resolve().parent.parent
SENTINEL = ROOT / "scripts/mcp_lifecycle_sentinel.py"


class CodexAppServerMcpToolCallProbeTests(unittest.TestCase):
    def test_isolated_config_binds_only_local_sentinel(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            text = build_isolated_config(
                Path(sys.executable),
                SENTINEL,
                root / "events.jsonl",
            )
        self.assertIn(f"[mcp_servers.{SERVER_NAME}]", text)
        self.assertIn(str(SENTINEL.resolve()).replace("\\", "\\\\"), text)
        self.assertIn("enabled = true", text)
        self.assertNotIn(str((Path.home() / ".codex").resolve()), text)

    def test_isolated_config_can_disable_only_the_local_sentinel(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            text = build_isolated_config(
                Path(sys.executable),
                SENTINEL,
                root / "events.jsonl",
                enabled=False,
            )
        self.assertIn(f"[mcp_servers.{SERVER_NAME}]", text)
        self.assertIn("enabled = false", text)
        self.assertNotIn("enabled = true", text)

    def test_isolated_config_can_bind_test_only_cleanup_marker(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            marker = root / "cleanup.marker"
            text = build_isolated_config(
                Path(sys.executable),
                SENTINEL,
                root / "events.jsonl",
                cleanup_marker=marker,
            )
        self.assertIn("--cleanup-marker", text)
        self.assertIn(str(marker.resolve()).replace("\\", "\\\\"), text)

    def test_requests_use_ephemeral_thread_and_direct_tool_call(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            initial = build_initial_requests(Path(temp))
        self.assertEqual(
            ["initialize", "initialized", "thread/start"],
            [item["method"] for item in initial],
        )
        self.assertTrue(initial[2]["params"]["ephemeral"])
        self.assertEqual("read-only", initial[2]["params"]["sandbox"])
        self.assertNotIn("turn/start", [item["method"] for item in initial])

        requests = build_thread_requests("thread-fixture")
        self.assertEqual(
            [
                "mcpServerStatus/list",
                "mcpServer/tool/call",
                "thread/unsubscribe",
            ],
            [item["method"] for item in requests],
        )
        self.assertEqual("thread-fixture", requests[1]["params"]["threadId"])
        self.assertEqual(SERVER_NAME, requests[1]["params"]["server"])
        self.assertEqual("identity", requests[1]["params"]["tool"])

    def test_sentinel_serves_identity_without_network_or_dependency(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            event_log = root / "events.jsonl"
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
                {
                    "jsonrpc": "2.0",
                    "id": 0,
                    "method": "initialize",
                    "params": {"protocolVersion": "2024-11-05"},
                },
                {
                    "jsonrpc": "2.0",
                    "method": "notifications/initialized",
                    "params": {},
                },
                {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "tools/list",
                    "params": {},
                },
                {
                    "jsonrpc": "2.0",
                    "id": 2,
                    "method": "resources/list",
                    "params": {},
                },
                {
                    "jsonrpc": "2.0",
                    "id": 3,
                    "method": "resources/templates/list",
                    "params": {},
                },
                {
                    "jsonrpc": "2.0",
                    "id": 4,
                    "method": "tools/call",
                    "params": {
                        "name": "identity",
                        "arguments": {"probe": PROBE_ID},
                    },
                },
            ]
            stdout, stderr = process.communicate(
                "".join(json.dumps(item) + "\n" for item in requests),
                timeout=10,
            )
            self.assertEqual("", stderr)
            self.assertEqual(0, process.returncode)
            responses = [json.loads(line) for line in stdout.splitlines()]
            by_id = {item["id"]: item for item in responses}
            self.assertEqual([], by_id[2]["result"]["resources"])
            self.assertEqual([], by_id[3]["result"]["resourceTemplates"])
            payload = by_id[4]["result"]["structuredContent"]
            self.assertEqual(process.pid, payload["pid"])
            self.assertEqual("identity", payload["tool"])
            self.assertEqual({"probe": PROBE_ID}, payload["arguments"])
            events = [
                json.loads(line)
                for line in event_log.read_text(encoding="utf-8").splitlines()
            ]
            self.assertEqual("instance-start", events[0]["event"])
            self.assertEqual("instance-stop", events[-1]["event"])
            self.assertEqual(
                1, sum(item["event"] == "tool-call" for item in events)
            )

    def test_sentinel_cleanup_marker_is_labeled_as_harness_cleanup(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            event_log = root / "events.jsonl"
            cleanup_marker = root / "cleanup.marker"
            process = subprocess.Popen(
                [
                    sys.executable,
                    "-B",
                    str(SENTINEL),
                    "--event-log",
                    str(event_log),
                    "--cleanup-marker",
                    str(cleanup_marker),
                ],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
            )
            deadline = time.monotonic() + 5
            while time.monotonic() < deadline:
                if event_log.is_file() and "instance-start" in event_log.read_text(
                    encoding="utf-8"
                ):
                    break
                time.sleep(0.05)
            else:
                process.kill()
                self.fail("Sentinel did not record instance-start")
            cleanup_marker.write_text("test\n", encoding="utf-8")
            process.wait(timeout=5)
            assert process.stdin is not None
            assert process.stdout is not None
            assert process.stderr is not None
            process.stdin.close()
            process.stdout.close()
            process.stderr.close()
            events = [
                json.loads(line)
                for line in event_log.read_text(encoding="utf-8").splitlines()
            ]
            self.assertEqual(0, process.returncode)
            self.assertIn(
                "harness-cleanup-marker-observed",
                [event["event"] for event in events],
            )
            self.assertNotIn("instance-stop", [event["event"] for event in events])

    @unittest.skipUnless(os.name == "nt", "Windows wrapper layout test")
    def test_native_codex_resolution_bypasses_command_wrapper(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            wrapper = root / "codex.cmd"
            wrapper.write_text("@echo off\n", encoding="utf-8")
            native = (
                root
                / "node_modules"
                / "@openai"
                / "codex"
                / "node_modules"
                / "@openai"
                / "codex-win32-x64"
                / "vendor"
                / "x86_64-pc-windows-msvc"
                / "bin"
                / "codex.exe"
            )
            native.parent.mkdir(parents=True)
            native.write_bytes(b"fixture")
            with mock.patch(
                "scripts.probe_codex_app_server_mcp_tool_call.resolve_codex_executable",
                return_value=str(wrapper),
            ):
                self.assertEqual(
                    str(native.resolve()),
                    resolve_native_codex_executable(None),
                )

    def test_extract_tool_payload_requires_real_payload(self) -> None:
        payload = {"pid": 123, "instanceId": "instance"}
        self.assertEqual(
            payload,
            extract_tool_payload({"result": {"structuredContent": payload}}),
        )
        with self.assertRaisesRegex(RuntimeError, "omitted Sentinel"):
            extract_tool_payload({"result": {"content": []}})

    def test_process_exists_observes_current_process(self) -> None:
        self.assertTrue(process_exists(os.getpid()))

    def test_probe_rejects_default_or_nonempty_home_before_launch(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "default Codex home"):
            run_probe(
                Path.home() / ".codex",
                Path(tempfile.gettempdir()) / "unused-mcp-workspace",
                SENTINEL,
                None,
                1,
            )
        with tempfile.TemporaryDirectory() as temp:
            home = Path(temp)
            (home / "sentinel.txt").write_text("preserve", encoding="utf-8")
            with self.assertRaisesRegex(RuntimeError, "absent or empty"):
                run_probe(
                    home,
                    home / "workspace",
                    SENTINEL,
                    None,
                    1,
                )


if __name__ == "__main__":
    unittest.main()
