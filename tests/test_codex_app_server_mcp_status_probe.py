import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts.probe_codex_app_server_mcp_status import (
    build_child_environment,
    build_command,
    build_requests,
    parse_json_lines,
    validate_responses,
)


class CodexAppServerMcpStatusProbeTests(unittest.TestCase):
    def test_request_sequence_is_status_only_after_handshake(self) -> None:
        requests = build_requests()
        self.assertEqual(
            ["initialize", "initialized", "mcpServerStatus/list"],
            [request["method"] for request in requests],
        )
        self.assertNotIn("config/mcpServer/reload", [request["method"] for request in requests])
        self.assertEqual({"detail": "full", "limit": 100}, requests[-1]["params"])

    def test_child_environment_removes_account_variables_and_rebinds_home(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            with patch.dict(
                os.environ,
                {
                    "OPENAI_API_KEY": "secret-not-recorded",
                    "CODEX_API_KEY": "secret-not-recorded",
                    "CHATGPT_AUTH_TOKEN": "secret-not-recorded",
                    "OPENAI_BASE_URL": "https://example.invalid",
                    "CODEX_HOME": "C:/wrong-home",
                },
                clear=False,
            ):
                environment, removed = build_child_environment(Path(temp))
        self.assertEqual(
            {"OPENAI_API_KEY", "CODEX_API_KEY", "CHATGPT_AUTH_TOKEN", "OPENAI_BASE_URL"},
            set(removed),
        )
        for key in removed:
            self.assertNotIn(key, environment)
        self.assertEqual(str(Path(temp)), environment["CODEX_HOME"])

    def test_response_validation_accepts_empty_status_and_exact_home(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            expected_home = Path(temp).resolve()
            messages = [
                {
                    "id": 0,
                    "result": {
                        "codexHome": str(expected_home),
                        "userAgent": "probe",
                        "platformFamily": "windows",
                        "platformOs": "windows",
                    },
                },
                {"method": "mcpServerStatus/updated", "params": {"data": []}},
                {"id": 1, "result": {"data": [], "nextCursor": None}},
            ]
            summary = validate_responses(messages, expected_home)
        self.assertEqual(0, summary["mcpStatus"]["serverCount"])
        self.assertEqual([], summary["mcpStatus"]["serverNames"])
        self.assertEqual(["mcpServerStatus/updated"], summary["notificationMethods"])

    def test_json_lines_reject_non_json_stdout(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "not JSON"):
            parse_json_lines("not-json\n")

    def test_response_validation_rejects_status_error(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            messages = [
                {"id": 0, "result": {"codexHome": temp}},
                {"id": 1, "error": {"code": -32000, "message": "failure"}},
            ]
            with self.assertRaisesRegex(RuntimeError, "returned error"):
                validate_responses(messages, Path(temp))

    @unittest.skipUnless(os.name == "nt", "Windows command-wrapper behavior")
    def test_windows_cmd_wrapper_uses_command_interpreter(self) -> None:
        command = build_command(r"C:\tools\codex.cmd")
        self.assertEqual(["/d", "/s", "/c"], command[1:4])
        self.assertEqual(r"C:\tools\codex.cmd", command[4])
        self.assertIn("mcpServerStatus/list", [request["method"] for request in build_requests()])


if __name__ == "__main__":
    unittest.main()
