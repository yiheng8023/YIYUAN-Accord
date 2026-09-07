"""Independent file oracle regressions; synthetic captures are not host evidence."""

import json
import os
from contextlib import contextmanager
from pathlib import Path
import tempfile
import subprocess
import time
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


def offline_communicate(controller, root, input_text=None, timeout=20):
    """Preserve safe timeout diagnostics after containing the owned controller."""
    try:
        return controller.communicate(input_text, timeout=timeout)
    except subprocess.TimeoutExpired:
        controller.kill()  # Closing its Job handle also contains native descendants.
        closed = False
        try:
            stdout, stderr = controller.communicate(timeout=5)
            closed = True
        except subprocess.TimeoutExpired as failure:
            stdout, stderr = failure.stdout or b"", failure.stderr or b""
        output = stdout.decode("utf-8", errors="replace") if isinstance(stdout, bytes) else stdout
        ready = False
        for line in output.splitlines():
            try:
                reply = json.loads(line)
                ready |= isinstance(reply, dict) and reply.get("ready") is True
            except (ValueError, TypeError):
                pass
        journal = root / "native/native-stdout.jsonl"
        size = journal.stat().st_size if journal.exists() else None
        diagnostic = {"readyReceived": ready, "nativeJournalBytes": size,
            "controllerExited": controller.poll() is not None, "controllerPipesClosed": closed,
            "controllerStdoutBytes": len(output.encode("utf-8")),
            "controllerStderrBytes": len(stderr if isinstance(stderr, bytes) else stderr.encode("utf-8"))}
        # No raw stdout/stderr, exception message, prompt or inherited route data.
        raise AssertionError("offline observer timeout: " + json.dumps(diagnostic)) from None


class ClaudeEntryOracleTests(unittest.TestCase):
    def test_repeated_turn_init_must_preserve_the_observed_session_and_composition(self):
        init = {"type": "system", "subtype": "init", "session_id": "s", "model": "bound"}
        final = {"type": "result", "subtype": "success", "is_error": False, "session_id": "s"}
        for delta in ({}, {"session_id": "other"}, {"model": "changed"}):
            capture = {"stdout": "\n".join(json.dumps(v) for v in [init, final, {**init, **delta}, final]),
                       "exitCode": 0, "forced": False, "childrenBeforeCleanup": 0}
            self.assertEqual(inspect_capture(capture, Path.cwd(), turns=2)["normalExit"], not delta)

    def test_normal_exit_does_not_hide_an_observed_tool_boundary_violation(self):
        for tool, path, count in (("Bash", "", 1), ("Read", "../private-canary.txt", 1),
                                  ("Write", "orders.csv", 1), ("Read", "keep.txt", 0),
                                  ("Read", ".", 0), ("Read", "missing/file.txt", 0)):
            events = [{"type": "system", "subtype": "init", "session_id": "s"},
                {"type": "assistant", "session_id": "s", "message": {"content": [
                    {"type": "tool_use", "id": "t", "name": tool, "input": {"file_path": path}}]}},
                {"type": "user", "session_id": "s", "message": {"content": [
                    {"type": "tool_result", "tool_use_id": "t"}]}},
                {"type": "result", "subtype": "success", "is_error": False, "session_id": "s"}]
            capture = {"stdout": "\n".join(json.dumps(v) for v in events), "exitCode": 0,
                       "forced": False, "childrenBeforeCleanup": 0}
            with self.subTest(tool=tool, path=path):
                host = inspect_capture(capture, Path.cwd())
                self.assertTrue(host["normalExit"])
                self.assertEqual(host["unexpectedToolCalls"], count)
                self.assertNotIn("private-canary", json.dumps(host))

    @windows_process_case
    def test_correction_follows_verified_first_delivery_in_one_live_session(self):
        program = r'''using System; using System.IO;
class Probe {
  static string Q(string s) { return "\"" + s.Replace("\\", "\\\\").Replace("\"", "\\\"") + "\""; }
  static void Turn(int n) {
    File.WriteAllText("details.csv", "id,units\nA,60\n" + (n == 140 ? "B,80\n" : ""));
    File.WriteAllText("summary.json", "{\"ready_ids\":" + (n == 140 ? "[\"A\",\"B\"]" : "[\"A\"]") + ",\"total_units\":" + n + "}");
    foreach (string file in new[]{"details.csv", "summary.json"})
      foreach (string tool in new[]{"Write", "Read"}) {
        string id = Q(n + file + tool);
        Console.WriteLine("{\"type\":\"assistant\",\"session_id\":\"bound\",\"message\":{\"content\":[{\"type\":\"tool_use\",\"id\":" + id + ",\"name\":" + Q(tool) + ",\"input\":{\"file_path\":" + Q(file) + "}}]}}");
        Console.WriteLine("{\"type\":\"user\",\"session_id\":\"bound\",\"message\":{\"content\":[{\"type\":\"tool_result\",\"tool_use_id\":" + id + "}]}}");
      }
    Console.WriteLine("{\"type\":\"result\",\"subtype\":\"success\",\"is_error\":false,\"session_id\":\"bound\"}");
  }
  static int Main(string[] args) {
    if (args.Length == 1) { Console.WriteLine("fixture"); return 0; }
    string first = Console.ReadLine();
    if (first == null || !first.Contains("\"type\":\"user\"")) return 8;
    int p = Array.IndexOf(args, "--plugin-dir");
    Console.WriteLine("{\"type\":\"system\",\"subtype\":\"init\",\"session_id\":\"bound\",\"cwd\":" + Q(Directory.GetCurrentDirectory()) + ",\"plugins\":" + (p < 0 ? "[]" : "[{\"name\":\"yiyuan-accord-claude\",\"path\":" + Q(args[p+1]) + "}]") + ",\"skills\":" + (p < 0 ? "[]" : "[\"yiyuan-accord-claude:deliver-demand-driven-outcome\"]") + "}");
    Turn(140);
    string correction = Console.ReadLine();
    if (correction != null) {
      if (!correction.Contains("\"type\":\"user\"") || !correction.Contains("B")) return 9;
      Turn(60);
    }
    return 0;
  }
}'''
        with offline_probe(program, 10) as (repository, root, binary, request):
            report = observe_ready_orders(repository, binary, timeout=10, correction=True)
        self.assertTrue(report["taskRootRemoved"])
        for arm in report["arms"].values():
            self.assertTrue(arm["matchesFixture"], arm)
            self.assertEqual(arm["firstDelivery"]["actual"]["effect"]["summary"]["total_units"], 140)
            self.assertEqual(arm["actual"]["effect"]["summary"], {"ready_ids": ["A"], "total_units": 60})
            self.assertTrue(arm["correctionSent"])
            self.assertTrue(arm["host"]["normalExit"])
        directory_read = r'''
      Console.WriteLine("{\"type\":\"assistant\",\"session_id\":\"bound\",\"message\":{\"content\":[{\"type\":\"tool_use\",\"id\":\"dir\",\"name\":\"Read\",\"input\":{\"file_path\":\".\"}}]}}");
      try { File.ReadAllText("."); return 10; }
      catch (UnauthorizedAccessException) {
        Console.WriteLine("{\"type\":\"user\",\"session_id\":\"bound\",\"message\":{\"content\":[{\"type\":\"tool_result\",\"tool_use_id\":\"dir\",\"is_error\":true}]}}");
      }
      Turn(60);'''
        with offline_probe(program.replace("Turn(60);", directory_read), 10) as (repository, root, binary, request):
            recovered = observe_ready_orders(repository, binary, timeout=10, correction=True)
        self.assertTrue(recovered["taskRootRemoved"])
        for arm in recovered["arms"].values():
            self.assertTrue(arm["firstDelivery"]["matchesFixture"])
            self.assertEqual(arm["actual"]["effect"]["summary"]["total_units"], 60)
            self.assertTrue(arm["host"]["normalExit"])
            self.assertEqual(arm["host"]["unexpectedToolCalls"], 0)
            self.assertTrue(arm["matchesFixture"])
        for condition in ("n == 140", 'n == 140 || tool == "Read"'):
            # Actual second delivery changes, but first-turn events cannot
            # attest its writes or readback, even if the second turn reads.
            missing = program.replace('string id = Q(n + file + tool);',
                                      'if (!(' + condition + ')) continue; string id = Q(n + file + tool);')
            with self.subTest(second_turn_events=condition), offline_probe(missing, 10) as (repository, root, binary, request):
                failed = observe_ready_orders(repository, binary, timeout=10, correction=True)
                self.assertTrue(failed["taskRootRemoved"])
                for arm in failed["arms"].values():
                    self.assertTrue(arm["firstDelivery"]["matchesFixture"])
                    self.assertEqual(arm["actual"]["effect"]["summary"]["total_units"], 60)
                    self.assertTrue(arm["correctionSent"])
                    self.assertTrue(arm["host"]["normalExit"])
                    self.assertEqual(arm["host"]["toolCalls"]["Write"], 2)
                    self.assertFalse(arm["matchesFixture"])
                    self.assertEqual(arm["host"]["agentReadback"], {"details.csv": False, "summary.json": False})
        with offline_probe(program.replace("Turn(140);", "Turn(190);"), 10) as (repository, root, binary, request):
            failed = observe_ready_orders(repository, binary, timeout=10, correction=True)
        self.assertTrue(failed["taskRootRemoved"])
        for arm in failed["arms"].values():
            self.assertFalse(arm["matchesFixture"])
            self.assertFalse(arm["correctionSent"])

    @windows_process_case
    def test_capture_failure_preserves_native_prefix_and_contains_the_child(self):
        for line, stage, overflow in (("not-json", "event-decode", False),
                                     ('{"type":"result"}', "checkpoint", False),
                                     ("{}", "capture-read", True)):
            prefix = '{"type":"system","subtype":"init","session_id":"fixture"}\n' + line + '\n'
            literal = json.dumps(prefix)
            program = ('class Probe { static void Main(string[] args) { '
                'if (args.Length == 1) { System.Console.WriteLine("fixture"); return; } '
                'System.Console.Write(' + literal + '); '
                'System.Console.Error.Write("private-stderr-canary"); ' +
                ('System.Console.Write(new string(\'x\', 3000000)); ' if overflow else '') +
                'System.Threading.Thread.Sleep(6000); } }')
            with self.subTest(stage=stage), offline_probe(program, 3) as (repository, root, binary, request):
                request.update(correction="bound correction", python=str(root / "missing.exe"))
                environment = {**os.environ, "ANTHROPIC_BASE_URL": "http://127.0.0.1:9",
                               "ANTHROPIC_AUTH_TOKEN": "fixture-not-a-real-token"}
                with subprocess.Popen(["pwsh", "-NoProfile", "-NonInteractive", "-File",
                    str(repository / "scripts/observe-claude-entry.ps1")], stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=environment) as controller:
                    stdout, stderr = offline_communicate(controller, root,
                        json.dumps(request) + '\n{"op":"run","arm":"native"}\n{"op":"close"}\n')
                self.assertEqual(controller.returncode, 0, {"stdoutBytes": len(stdout), "stderrBytes": len(stderr)})
                capture = json.loads(stdout.splitlines()[1])
                self.assertTrue(capture["stdout"].startswith(prefix))
                self.assertLessEqual(len(capture["stdout"].encode()), 2097152)
                self.assertEqual(capture["failure"]["stage"], stage)
                if overflow:
                    self.assertIn("stdout-final", [v["stage"] for v in capture["secondaryFailures"]])
                self.assertTrue(capture["forced"])
                self.assertEqual(capture["evaluatorChildrenAfterCleanup"], 0)
                self.assertFalse("private-stderr-canary" in stdout + stderr)
                self.assertFalse("fixture-not-a-real-token" in stdout + stderr)
                self.assertEqual((root / 'native/native-stdout.jsonl').read_text(), capture["stdout"])

    @windows_process_case
    def test_controller_timeout_reports_safe_stage_and_kills_the_owned_process_tree(self):
        import ctypes
        program = ('class Probe { static void Main(string[] args) { '
            'if (args.Length == 2) { '
            'System.IO.File.WriteAllText("descendant-pid", System.Diagnostics.Process.GetCurrentProcess().Id.ToString()); '
            'System.Threading.Thread.Sleep(30000); return; } '
            'if (args.Length == 1) { System.Console.WriteLine("fixture"); return; } '
            'System.IO.File.WriteAllText("pid", System.Diagnostics.Process.GetCurrentProcess().Id.ToString()); '
            'System.Diagnostics.Process.Start(new System.Diagnostics.ProcessStartInfo('
            'System.Diagnostics.Process.GetCurrentProcess().MainModule.FileName, "descendant fixture") '
            '{ UseShellExecute = false, CreateNoWindow = true }); '
            'while (!System.IO.File.Exists("descendant-pid")) System.Threading.Thread.Sleep(10); '
            'System.Console.Error.Write("private-stderr-canary"); '
            'System.Console.WriteLine("recorded-prefix"); System.Threading.Thread.Sleep(30000); } }')
        with offline_probe(program, 30) as (repository, root, binary, request):
            request["routeMode"] = "host-user-settings"
            marker = root / "controller-started"
            delayed = ("[Console]::Error.Write('private-stderr-canary'); "
                "[Console]::WriteLine('fixture-not-a-real-token'); "
                "[IO.File]::WriteAllText('" + str(marker).replace("'", "''") + "', 'started'); "
                "Start-Sleep -Seconds 30")
            with subprocess.Popen(["pwsh", "-NoProfile", "-NonInteractive", "-Command",
                delayed], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                stderr=subprocess.PIPE, text=True) as controller:
                deadline = time.monotonic() + 10
                while not marker.exists():
                    if time.monotonic() >= deadline:
                        controller.kill()
                        controller.communicate(timeout=5)
                        self.fail("controlled startup did not reach its delay")
                    time.sleep(.05)
                with self.assertRaises(AssertionError) as timeout:
                    offline_communicate(controller, root, timeout=.1)
                diagnostic = str(timeout.exception)
                self.assertNotIn("private-stderr-canary", diagnostic)
                self.assertNotIn("fixture-not-a-real-token", diagnostic)
                before = json.loads(diagnostic.split(": ", 1)[1])
                self.assertFalse(before["readyReceived"])
                self.assertIsNone(before["nativeJournalBytes"])
                self.assertTrue(before["controllerExited"])
                self.assertTrue(before["controllerPipesClosed"])
                self.assertGreater(before["controllerStdoutBytes"], 0)
                self.assertGreater(before["controllerStderrBytes"], 0)
            with subprocess.Popen(["pwsh", "-NoProfile", "-NonInteractive", "-File",
                str(repository / "scripts/observe-claude-entry.ps1")], stdin=subprocess.PIPE,
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True) as controller:
                try:
                    controller.stdin.write(json.dumps(request) + '\n{"op":"run","arm":"native"}\n')
                    controller.stdin.flush()
                    journal = root / 'native/native-stdout.jsonl'
                    deadline = time.monotonic() + 10
                    while not journal.exists() or 'recorded-prefix' not in journal.read_text():
                        self.assertLess(time.monotonic(), deadline, "no incremental native capture")
                        time.sleep(.05)
                    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
                    kernel.OpenProcess.restype = ctypes.c_void_p
                    handles = []
                    try:
                        for name in ("pid", "descendant-pid"):
                            handle = kernel.OpenProcess(0x100000, False, int((root / 'native/work' / name).read_text()))
                            self.assertTrue(handle)
                            handles.append(handle)
                        with self.assertRaises(AssertionError) as timeout:
                            offline_communicate(controller, root, timeout=.1)
                        diagnostic = str(timeout.exception)
                        self.assertNotIn("private-stderr-canary", diagnostic)
                        self.assertNotIn("recorded-prefix", diagnostic)
                        after = json.loads(diagnostic.split(": ", 1)[1])
                        self.assertTrue(after["readyReceived"])
                        self.assertGreater(after["nativeJournalBytes"], 0)
                        self.assertTrue(after["controllerExited"])
                        self.assertTrue(after["controllerPipesClosed"])
                        for handle in handles:
                            self.assertEqual(kernel.WaitForSingleObject(ctypes.c_void_p(handle), 5000), 0)
                    finally:
                        for handle in handles:
                            kernel.CloseHandle(ctypes.c_void_p(handle))
                    self.assertEqual(journal.read_text().strip(), 'recorded-prefix')
                finally:
                    if controller.poll() is None:
                        controller.kill()
                    controller.communicate(timeout=10)

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
