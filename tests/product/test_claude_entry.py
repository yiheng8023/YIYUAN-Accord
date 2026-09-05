"""Independent file oracle regressions; synthetic captures are not host evidence."""

import json
import os
from contextlib import contextmanager
from pathlib import Path
import tempfile
import subprocess
import unittest
import uuid
from unittest.mock import patch

from scripts.observe_claude_entry import inspect_capture, inspect_entry, observe_ready_orders


def windows_process_case(test):
    """Discover Windows process cases only where applicable; never skip failures."""
    return test if os.name == "nt" else None


@contextmanager
def offline_probe(program, timeout):
    """Own the repeated fixture setup; each case supplies its executable behavior."""
    repository = Path(__file__).resolve().parents[2]
    with tempfile.TemporaryDirectory(prefix="accord-entry-") as directory:
        root = Path(directory)
        episode = uuid.uuid4().hex
        (root / "owner").write_text(episode, encoding="utf-8")
        for name in ("work", "home", "config", "appdata", "localappdata", "temp"):
            (root / "native" / name).mkdir(parents=True)
        source, binary = root / "probe.cs", root / "probe.exe"
        source.write_text(program, encoding="utf-8")
        subprocess.run(["C:/Windows/Microsoft.NET/Framework64/v4.0.30319/csc.exe", "/nologo",
                        "/out:" + str(binary), str(source)], check=True, capture_output=True, timeout=15)
        yield repository, root, binary, {
            "schema": "accord-live-cli-source/v1", "episode": episode, "timeout": timeout,
            "repository": str(repository), "taskRoot": str(root), "executable": str(binary), "prompt": "fixture"}


class ClaudeEntryOracleTests(unittest.TestCase):
    @windows_process_case
    def test_explicit_user_route_is_loaded_by_host_not_observer(self):
        program = ('class Probe { static int Main(string[] args) { '
                'if (args.Length == 1) { System.Console.WriteLine("fixture"); return 0; } '
                'bool user = System.Array.IndexOf(args,"user") >= 0 && '
                'System.Environment.GetEnvironmentVariable("USERPROFILE").EndsWith("original-profile"); '
                'bool restricted = System.Array.IndexOf(args,"--restricted") >= 0; '
                'System.Console.WriteLine(user && !restricted ? "host-user-route" : "wrong-route"); return 0; } }')
        with offline_probe(program, 3) as (repository, root, binary, request):
            request["routeMode"] = "host-user-settings"
            environment = {k: v for k, v in os.environ.items() if not k.startswith("ANTHROPIC_")}
            environment["USERPROFILE"] = str(root / "original-profile")
            result = subprocess.run(["pwsh", "-NoProfile", "-NonInteractive", "-File",
                                     str(repository / "scripts/observe-claude-entry.ps1")],
                input=json.dumps(request) + '\n{"op":"run","arm":"native"}\n{"op":"close"}\n',
                capture_output=True, text=True, env=environment, timeout=20)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            replies = [json.loads(line) for line in result.stdout.splitlines()]
            self.assertEqual(replies[1]["stdout"].strip(), "host-user-route")
            self.assertEqual(replies[1]["evaluatorChildrenAfterCleanup"], 0)
            self.assertEqual(result.stderr, "")
            observed = observe_ready_orders(repository, binary, timeout=3)
            self.assertTrue(observed["taskRootRemoved"])
            self.assertFalse(any(arm["matchesFixture"] for arm in observed["arms"].values()))

    @windows_process_case
    def test_nonreading_child_cannot_hold_stdin_past_the_run_deadline(self):
        program = ('class Probe { static int Main(string[] args) { '
                               'if (args.Length == 1 && args[0] == "--version") { '
                               'System.Console.WriteLine("offline-fixture"); return 0; } '
                               'System.Console.WriteLine("nonreading-fixture"); '
                               'System.Threading.Thread.Sleep(6000); return 0; } }')
        with offline_probe(program, 1) as (repository, root, binary, request):
            request["prompt"] = "x" * 32768
            environment = {**os.environ, "ANTHROPIC_BASE_URL": "http://127.0.0.1:9",
                           "ANTHROPIC_AUTH_TOKEN": "fixture-not-a-real-token"}
            result = subprocess.run(["pwsh", "-NoProfile", "-NonInteractive", "-File",
                                     str(repository / "scripts/observe-claude-entry.ps1")],
                                    input=json.dumps(request) + '\n{"op":"run","arm":"native"}\n{"op":"close"}\n',
                                    capture_output=True, text=True, env=environment, timeout=20)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            replies = [json.loads(line) for line in result.stdout.splitlines()]
            self.assertEqual(len(replies), 2)
            self.assertEqual(replies[1]["stdout"].strip(), "nonreading-fixture")
            self.assertTrue(replies[1]["forced"])
            self.assertEqual(replies[1]["exitCode"], 124)
            self.assertGreaterEqual(replies[1]["childrenBeforeCleanup"], 1)
            self.assertEqual(replies[1]["evaluatorChildrenAfterCleanup"], 0)
            self.assertLess(replies[1]["elapsedSeconds"], 5)
            self.assertEqual(result.stderr, "")

    @windows_process_case
    def test_inherited_route_does_not_read_private_settings(self):
        program = 'class Probe { static int Main() { System.Console.WriteLine("offline-fixture"); return 0; } }'
        with offline_probe(program, 3) as (repository, root, binary, request):
            # Replace only the external filesystem boundary. A regression is
            # reported without allowing a real private settings read in the test.
            command = """function global:Get-Content {
              param([string]$LiteralPath, [switch]$Raw)
              if ([IO.Path]::GetFileName($LiteralPath) -eq 'owner') {
                return Microsoft.PowerShell.Management\\Get-Content -LiteralPath $LiteralPath -Raw
              }
              [Console]::WriteLine('{"forbiddenReadAttempt":true}')
              throw 'private-read-blocked-by-test'
            }
            & '""" + str(repository / "scripts/observe-claude-entry.ps1").replace("'", "''") + "'"
            environment = {**os.environ, "ANTHROPIC_BASE_URL": "http://127.0.0.1:9",
                           "ANTHROPIC_AUTH_TOKEN": "fixture-not-a-real-token"}
            result = subprocess.run(["pwsh", "-NoProfile", "-NonInteractive", "-Command", command],
                                    input=json.dumps(request) + '\n{"op":"run","arm":"native"}\n{"op":"close"}\n',
                                    capture_output=True, text=True, env=environment, timeout=20)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            replies = [json.loads(line) for line in result.stdout.splitlines()]
            self.assertEqual(len(replies), 2)
            self.assertEqual(replies[1]["stdout"].strip(), "offline-fixture")
            self.assertEqual(replies[1]["evaluatorChildrenAfterCleanup"], 0)
            self.assertEqual(result.stderr, "")

    def test_only_the_bound_accord_skill_is_attributed_to_accord(self):
        for skill, expected in (("unrelated-skill", False),
                                ("yiyuan-accord-claude:deliver-demand-driven-outcome", True)):
            events = [{"type": "assistant", "message": {"content": [
                {"type": "tool_use", "id": "s", "name": "Skill", "input": {"skill": skill}}]}},
                {"type": "user", "message": {"content": [{"type": "tool_result", "tool_use_id": "s"}]}}]
            with self.subTest(skill=skill):
                result = inspect_capture({"stdout": "\n".join(json.dumps(v) for v in events)}, Path.cwd())
                self.assertEqual(result["skillInvoked"], expected)

    def test_completion_cannot_precede_tool_effects_or_leave_a_call_open(self):
        init = {"type": "system", "subtype": "init", "session_id": "bound"}
        final = {"type": "result", "subtype": "success", "is_error": False, "session_id": "bound"}
        call = {"type": "assistant", "session_id": "bound", "message": {"content": [
            {"type": "tool_use", "id": "w1", "name": "Write", "input": {"file_path": "summary.json"}}]}}
        result = {"type": "user", "session_id": "bound", "message": {"content": [
            {"type": "tool_result", "tool_use_id": "w1"}]}}
        for events in ([init, final, call, result], [init, call, final]):
            with self.subTest(events=events):
                capture = {"stdout": "\n".join(json.dumps(v) for v in events), "exitCode": 0,
                           "forced": False, "childrenBeforeCleanup": 0}
                self.assertFalse(inspect_capture(capture, Path.cwd())["normalExit"])

    def test_another_session_success_cannot_close_the_observed_session(self):
        events = [{"type": "system", "subtype": "init", "session_id": "first"},
                  {"type": "result", "subtype": "success", "is_error": False, "session_id": "second"}]
        capture = {"stdout": "\n".join(json.dumps(v) for v in events), "exitCode": 0,
                   "forced": False, "childrenBeforeCleanup": 0}
        self.assertFalse(inspect_capture(capture, Path.cwd())["normalExit"])

    @windows_process_case
    def test_version_query_is_timed_and_contained_before_route_access(self):
        program = 'class Probe { static int Main() { System.Threading.Thread.Sleep(6000); return 7; } }'
        with offline_probe(program, 1) as (repository, root, binary, request):
            result = subprocess.run(["pwsh", "-NoProfile", "-NonInteractive", "-File",
                                     str(repository / "scripts/observe-claude-entry.ps1")],
                                    input=json.dumps(request) + "\n", capture_output=True,
                                    text=True, timeout=15)
            self.assertEqual(result.returncode, 3)
            self.assertEqual(json.loads(result.stdout), {"error": "version-query-not-completed",
                             "forced": True, "evaluatorChildrenAfterCleanup": 0})
            self.assertEqual(result.stderr, "")

    def test_false_is_not_a_zero_exit_code_or_zero_children_receipt(self):
        events = [{"type": "system", "subtype": "init", "session_id": "bound"},
                  {"type": "result", "subtype": "success", "is_error": False, "session_id": "bound"}]
        for field in ("exitCode", "childrenBeforeCleanup"):
            capture = {"stdout": "\n".join(json.dumps(v) for v in events), "exitCode": 0,
                       "forced": False, "childrenBeforeCleanup": 0}
            capture[field] = False
            with self.subTest(field=field):
                self.assertFalse(inspect_capture(capture, Path.cwd())["normalExit"])

    @windows_process_case
    def test_live_source_rejects_an_unbound_request_before_host_launch(self):
        script = Path(__file__).resolve().parents[2] / "scripts/observe-claude-entry.ps1"
        result = subprocess.run(["pwsh", "-NoProfile", "-NonInteractive", "-File", str(script)],
                                input="{}\n", capture_output=True, text=True, timeout=15)
        self.assertEqual(result.returncode, 2)
        self.assertEqual(json.loads(result.stdout), {"error": "unbound-observation-request"})
        self.assertEqual(result.stderr, "")

    @windows_process_case
    def test_each_arm_is_observed_and_released_before_the_next_starts(self):
        roots = []
        drift = {}

        def source(*args, **kwargs):
            commands = [json.loads(line) for line in kwargs["input"].splitlines()]
            bound, run = commands[:2]
            self.assertEqual(sum(v.get("op") == "run" for v in commands), 1)
            self.assertTrue(all(not root.exists() for root in roots))
            root = Path(bound["taskRoot"])
            roots.append(root)
            (root / run["arm"] / "work/summary.json").write_text('{"total_units":190}', encoding="utf-8")
            replies = [{"ready": True, "episode": bound["episode"], "version": "fixture", "binarySha256": "a" * 64},
                       {"arm": run["arm"], "episode": bound["episode"], "stdout": ""},
                       {"episode": bound["episode"], "binaryUnchanged": True,
                        "profileUnchanged": True, "routeUnchanged": None}]
            replies[-1].update(drift)
            return subprocess.CompletedProcess(args, 0, "\n".join(json.dumps(v) for v in replies), "")

        with patch("subprocess.run", side_effect=source):
            report = observe_ready_orders(Path(__file__).resolve().parents[2], "offline-fixture")
        self.assertEqual(len(roots), 2)
        self.assertNotEqual(*roots)
        self.assertTrue(report["taskRootRemoved"])
        self.assertTrue(report["sourceBindingValid"])
        self.assertEqual(report["arms"]["native"]["actual"]["effect"]["summary"], {"total_units": 190})
        for field, value in (("episode", "foreign"), ("binaryUnchanged", False),
                             ("profileUnchanged", 1), ("routeUnchanged", True)):
            drift = {field: value}
            with self.subTest(field=field), patch("subprocess.run", side_effect=source):
                report = observe_ready_orders(Path(__file__).resolve().parents[2], "offline-fixture")
                self.assertFalse(report["sourceBindingValid"])
                self.assertEqual(report["arms"]["native"]["actual"]["effect"]["summary"], {"total_units": 190})

    @windows_process_case
    def test_initialization_failure_releases_the_new_empty_root(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(tempfile, "tempdir", directory):
            with patch.object(Path, "write_text", side_effect=OSError("fixture disk failure")):
                with self.assertRaises(OSError):
                    observe_ready_orders(Path.cwd(), "offline-fixture")
            self.assertEqual(list(Path(directory).iterdir()), [])

    def test_tool_listing_and_success_do_not_prove_skill_use_or_file_verification(self):
        events = [
            {"type": "system", "subtype": "init", "session_id": "bound", "cwd": "C:/case", "model": "reported-only",
             "tools": ["Read", "Write", "Edit", "Skill"], "skills": ["yiyuan-accord-claude:deliver-demand-driven-outcome"],
             "plugins": [{"name": "yiyuan-accord-claude", "path": "not-for-publication"}]},
            {"type": "result", "subtype": "success", "session_id": "bound", "is_error": False, "result": "Everything verified."},
        ]
        capture = {"stdout": "\n".join(json.dumps(v) for v in events), "exitCode": 0,
                   "forced": False, "childrenBeforeCleanup": 0}
        result = inspect_capture(capture, Path("C:/case"))
        self.assertTrue(result["normalExit"])
        self.assertEqual(result["toolCalls"], {})
        self.assertFalse(result["skillInvoked"])
        self.assertEqual(result["agentReadback"], {"details.csv": False, "summary.json": False})
        self.assertNotIn("not-for-publication", json.dumps(result))

    def test_rejected_skill_and_read_before_last_write_are_not_verified_use(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            events = []
            for number, (name, failed) in enumerate([
                    ("Write", False), ("Read", False), ("Write", False), ("Read", True), ("Skill", True)]):
                key = str(number)
                events.extend([
                    {"type": "assistant", "message": {"content": [{"type": "tool_use", "id": key,
                      "name": name, "input": {"file_path": str(root / "details.csv")}}]}},
                    {"type": "user", "message": {"content": [{"type": "tool_result", "tool_use_id": key,
                      "is_error": failed}]}},
                ])
            result = inspect_capture({"stdout": "\n".join(json.dumps(v) for v in events)}, root)
            self.assertFalse(result["agentReadback"]["details.csv"])
            self.assertFalse(result["skillInvoked"])
            self.assertEqual(result["toolCalls"]["Skill"], 1)

    def test_replayed_old_read_result_cannot_verify_a_later_write(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            events = []
            for key, name in (("w1", "Write"), ("r1", "Read"), ("w2", "Write")):
                events.extend([
                    {"type": "assistant", "message": {"content": [{"type": "tool_use", "id": key,
                      "name": name, "input": {"file_path": str(root / "summary.json")}}]}},
                    {"type": "user", "message": {"content": [{"type": "tool_result", "tool_use_id": key}]}},
                ])
            events.append({"type": "user", "message": {"content": [
                {"type": "tool_result", "tool_use_id": "r1"}]}})
            result = inspect_capture({"stdout": "\n".join(json.dumps(v) for v in events)}, root)
            self.assertFalse(result["agentReadback"]["summary.json"])

    def test_success_text_cannot_replace_the_actual_delivery(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "orders.csv").write_text("immutable input\n", encoding="utf-8")
            (root / "keep.txt").write_text("unrelated\n", encoding="utf-8")
            before = {p.name: p.read_bytes() for p in root.iterdir()}
            (root / "details.csv").write_text("id,amount\nA,60\nB,80\n", encoding="utf-8")
            (root / "summary.json").write_text(json.dumps({"total": 190}), encoding="utf-8")
            result = inspect_entry(root, before)
            self.assertEqual(result["effect"], {
                "details": [["id", "amount"], ["A", "60"], ["B", "80"]],
                "summary": {"total": 190},
            })
            self.assertTrue(result["authority"]["inputsUnchanged"])
            self.assertEqual(result["poststate"]["unexpectedPaths"], [])


if __name__ == "__main__":
    unittest.main()
