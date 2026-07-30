from pathlib import Path
import tempfile
import unittest

from scripts.probe_codex_app_server_mcp_reload_new_threads import (
    atomic_replace_bytes,
    build_status_request,
    build_thread_start_request,
    build_tool_request,
    sha256_bytes,
)


class CodexAppServerMcpReloadNewThreadsProbeTests(unittest.TestCase):
    def test_status_surface_is_minimal_and_thread_scoped(self) -> None:
        request = build_status_request(4, "thread-fixture")
        self.assertEqual("mcpServerStatus/list", request["method"])
        self.assertEqual("thread-fixture", request["params"]["threadId"])
        self.assertEqual("toolsAndAuthOnly", request["params"]["detail"])
        self.assertEqual(10, request["params"]["limit"])

    def test_thread_and_tool_requests_never_start_a_model_turn(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            start = build_thread_start_request(1, Path(temp), "fixture")
        call = build_tool_request(2, "thread-fixture", "phase-fixture")
        self.assertEqual("thread/start", start["method"])
        self.assertTrue(start["params"]["ephemeral"])
        self.assertEqual("never", start["params"]["approvalPolicy"])
        self.assertEqual("read-only", start["params"]["sandbox"])
        self.assertEqual("mcpServer/tool/call", call["method"])
        self.assertNotEqual("turn/start", start["method"])
        self.assertNotEqual("turn/start", call["method"])

    def test_atomic_config_replacement_is_exact_and_leaves_no_temp_file(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "config.toml"
            before = b"enabled = true\n"
            disabled = b"enabled = false\n"
            self.assertEqual(sha256_bytes(before), atomic_replace_bytes(path, before))
            self.assertEqual(
                sha256_bytes(disabled),
                atomic_replace_bytes(path, disabled),
            )
            self.assertEqual(disabled, path.read_bytes())
            self.assertEqual([], list(path.parent.glob(f".{path.name}.*.tmp")))

    def test_runner_uses_no_pid_signal_cleanup(self) -> None:
        source = (
            Path(__file__).resolve().parent.parent
            / "scripts"
            / "probe_codex_app_server_mcp_reload_new_threads.py"
        ).read_text(encoding="utf-8")
        self.assertNotIn("os.kill(", source)
        self.assertNotIn("signal.SIG", source)
        self.assertIn("cleanupMarkerExitIsNaturalReleaseEvidence", source)
        self.assertIn("resolve_native_codex_executable", source)


if __name__ == "__main__":
    unittest.main()
