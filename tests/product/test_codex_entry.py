"""Offline oracle and Windows ownership tests; never call a model."""

import argparse
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

# The preparer binds resolved executable bytes; synthetic traces must use
# that same identity even when the interpreter was launched through a symlink.
PYTHON = str(Path(sys.executable).resolve())

SCRIPT = Path(__file__).resolve().parents[2] / "scripts/observe_codex_entry.py"
spec = importlib.util.spec_from_file_location("observe_codex_entry", SCRIPT)
entry = importlib.util.module_from_spec(spec)
spec.loader.exec_module(entry)


class EntryTests(unittest.TestCase):
    def test_config_observation_survives_a_failed_business_inspection(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            manifest = self.prepared(root)
            shared = root / "shared"
            shared.mkdir()
            (shared / "config.toml").write_text("model = 'offline'\n", encoding="utf-8")
            with patch.dict(os.environ, {"CODEX_HOME": str(shared)}), \
                    patch.object(entry, "WindowsJob") as job, \
                    patch.object(entry.subprocess, "Popen", side_effect=OSError("offline fixture")), \
                    patch.object(entry, "inspect", side_effect=ValueError("business evidence unreadable")):
                job.return_value.sample.return_value = {"activeProcesses": 0}
                with self.assertRaisesRegex(ValueError, "business evidence unreadable"):
                    entry.run(argparse.Namespace(evidence=manifest["evidence"]))
            saved = json.loads((Path(manifest["evidence"]) / "shared-config.json").read_text(encoding="utf-8"))
            self.assertEqual(saved["before"]["state"], "observed")
            self.assertEqual(saved["after"]["state"], "observed")
            self.assertTrue(saved["unchanged"])

    def test_host_registration_change_is_observed_without_disclosing_foreign_values(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            config, workspace = root / "config.toml", root / "work"
            config.write_text('private_value = "do-not-emit"\n', encoding="utf-8")
            before = entry.shared_config_snapshot(config, workspace)
            self.assertEqual(before["workspaceRegistrations"], {} if entry.tomllib else None)
            config.write_text(config.read_text(encoding="utf-8") +
                              '[projects.' + json.dumps(str(workspace)) + ']\ntrust_level = "trusted"\n',
                              encoding="utf-8")
            after = entry.shared_config_snapshot(config, workspace)
            self.assertNotEqual(before["sha256"], after["sha256"])
            self.assertEqual(after["workspaceRegistrations"],
                             {str(workspace): {"trustLevel": "trusted"}} if entry.tomllib else None)
            self.assertNotIn("do-not-emit", json.dumps(after))
            config.write_text("invalid = [", encoding="utf-8")
            invalid = entry.shared_config_snapshot(config, workspace)
            if entry.tomllib:
                self.assertEqual(invalid["state"], "unavailable")
            else:
                self.assertEqual(invalid["registrationState"], "unavailable")

    def test_missing_toml_parser_preserves_hash_without_inventing_registration(self):
        import builtins
        original_import = builtins.__import__

        def without_tomllib(name, *args, **kwargs):
            if name == "tomllib":
                raise ModuleNotFoundError("tomllib unavailable")
            return original_import(name, *args, **kwargs)

        isolated = importlib.util.module_from_spec(spec)
        with patch("builtins.__import__", side_effect=without_tomllib):
            spec.loader.exec_module(isolated)
        with tempfile.TemporaryDirectory() as tmp:
            config = Path(tmp) / "config.toml"
            config.write_text('private_value = "do-not-emit"\n', encoding="utf-8")
            before = isolated.shared_config_snapshot(config, tmp)
            self.assertEqual(before["sha256"], entry.digest(config))
            self.assertIsNone(before["workspaceRegistrations"])
            self.assertEqual(before["registrationState"], "unavailable")
            config.write_text("invalid = [", encoding="utf-8")
            after = isolated.shared_config_snapshot(config, tmp)
            self.assertNotEqual(before["sha256"], after["sha256"])
            self.assertIsNone(after["workspaceRegistrations"])
            self.assertNotIn("do-not-emit", json.dumps(before))

    def prepared(self, root, case=None):
        package = root / "package"
        (package / "runtime").mkdir(parents=True)
        (package / "runtime/task-checkpoint.cjs").write_text("// fixture", encoding="utf-8")
        args = argparse.Namespace(package=str(package), evidence=str(root / "evidence"), workspace=str(root / "work"),
                                  codex=PYTHON, node=PYTHON, model="explicit-offline-model",
                                  reasoning="high", timeout=10, windows_sandbox="elevated")
        fake = subprocess.CompletedProcess([], 0, b"app-server --ephemeral --ignore-user-config --dangerously-bypass-hook-trust --sandbox", b"")
        with patch.object(entry.subprocess, "run", return_value=fake) as calls:
            entry.prepare(args, app_server_case=case)
        self.assertEqual(calls.call_count, 2)
        self.assertEqual(calls.call_args_list[0].args[0][-2:], ["app-server" if case is not None else "exec", "--help"])
        self.assertEqual(calls.call_args_list[1].args[0][-1], "--version")
        return entry.load_manifest(args.evidence)

    def app_case(self):
        return {"prompts": ["Pause delivery; explain only.", "Resume: deliver id,status,units CSV and summary."],
                "expected": {"details": [["id", "status", "units"], ["A", "ready", "60"], ["B", "ready", "80"]],
                             "summary": {"ready_ids": ["A", "B"], "total_units": 140}},
                "limits": {"entry": "two-turn caller-owned native App Server fixture"}}

    def app_trace(self, workspace=None):
        original = [json.loads(line) for line in self.trace().splitlines()]
        result = [{"method": "thread/started", "params": {"thread": {"id": "native-task"}}}]
        for event in original[1:]:
            old = event["item"]
            body = "& '" + PYTHON + "' -B order_source.py; $exitCode = $LASTEXITCODE; \"SOURCE_EXIT=$exitCode\"; exit 0"
            completed = event["type"] == "item.completed"
            code = 75 if old["id"] == "failed" else 0
            result.append({"method": event["type"].replace(".", "/"), "params": {
                "threadId": "native-task", "turnId": "turn-two", "item": {
                    "id": old["id"], "type": "commandExecution", "command": old["command"], "cwd": workspace,
                    "commandActions": [{"type": "unknown", "command": body}],
                    "status": "completed" if completed else "inProgress", "exitCode": 0 if completed else None,
                    "aggregatedOutput": old["aggregated_output"] + f"SOURCE_EXIT={code}\n" if completed else None}}})
        return result

    def test_app_server_preparation_does_not_inherit_cli_input_or_execution(self):
        with tempfile.TemporaryDirectory() as tmp:
            manifest = self.prepared(Path(tmp).resolve(), self.app_case())
            self.assertEqual(manifest["prompts"], self.app_case()["prompts"])
            self.assertEqual(manifest["expected"], self.app_case()["expected"])
            self.assertNotIn("command", manifest)
            self.assertNotIn("promptSha256", manifest)
            self.assertFalse((Path(manifest["evidence"]) / "prompt.txt").exists())
            with self.assertRaisesRegex(ValueError, "CLI command"):
                entry.build_command(manifest)
            with patch.object(entry.subprocess, "Popen") as spawn:
                with self.assertRaisesRegex(ValueError, "caller-owned dispatcher"):
                    entry.run(argparse.Namespace(evidence=manifest["evidence"]))
                spawn.assert_not_called()
            entry.save(Path(manifest["evidence"]) / "manifest.json", dict(manifest, command=["codex", "exec"]))
            with self.assertRaisesRegex(ValueError, "incompatible CLI"):
                entry.inspect(manifest["evidence"])

    def resumed_trace(self, workspace=None):
        events = self.app_trace(workspace)[1:]
        request = {"id": 42, "method": "thread/resume", "params": {"threadId": "native-task"}}
        response = {"id": 42, "result": {"thread": {"id": "native-task"}}}
        start = {"method": "turn/started", "params": {"threadId": "native-task", "turn": {"id": "turn-two"}}}
        end = {"method": "turn/completed", "params": {"threadId": "native-task", "turn": {"id": "turn-two", "status": "completed"}}}
        for event in events:
            item = event["params"]["item"]
            if item.get("aggregatedOutput"):
                item["aggregatedOutput"] = item["aggregatedOutput"].replace(
                    "Local order source temporarily unavailable. Retry this same command.", "Different failure wording.")
        return [response, start, *events, end], [request]

    def test_resume_requires_native_request_response_and_live_turn_window(self):
        events, requests = self.resumed_trace()
        encode = lambda rows: "\n".join(map(json.dumps, rows))
        observed = entry.source_recovery_from_events(encode(events), PYTHON, protocol="app-server",
                                                     request_stream=encode(requests))
        self.assertTrue(observed["recovered"])
        self.assertEqual(observed["entryEvidence"], "matched-resume-request-response")
        self.assertFalse(entry.source_recovery_from_events(encode(events), PYTHON, protocol="app-server")["recovered"])
        for mutation in ("wrong-request-id", "wrong-request-method", "wrong-response-thread", "duplicate-response",
                         "duplicate-request", "history-override", "response-error", "missing-turn-end",
                         "wrong-turn", "failed-turn", "command-before-turn", "conflicting-start", "changed-cwd"):
            log, outgoing = json.loads(json.dumps(events)), json.loads(json.dumps(requests))
            if mutation == "wrong-request-id": outgoing[0]["id"] = 43
            elif mutation == "wrong-request-method": outgoing[0]["method"] = "thread/read"
            elif mutation == "wrong-response-thread": log[0]["result"]["thread"]["id"] = "foreign"
            elif mutation == "duplicate-response": log.append(log[0])
            elif mutation == "duplicate-request": outgoing.append(outgoing[0])
            elif mutation == "history-override": outgoing[0]["params"]["history"] = []
            elif mutation == "response-error": log[0]["error"] = {"code": -1}
            elif mutation == "missing-turn-end": log.pop()
            elif mutation == "wrong-turn": log[2]["params"]["turnId"] = "foreign"
            elif mutation == "failed-turn": log[-1]["params"]["turn"]["status"] = "failed"
            elif mutation == "command-before-turn": log[1], log[2] = log[2], log[1]
            elif mutation == "conflicting-start": log.insert(0, self.app_trace()[0])
            elif mutation == "changed-cwd": log[3]["params"]["item"]["cwd"] = "foreign"
            with self.subTest(mutation=mutation):
                self.assertFalse(entry.source_recovery_from_events(encode(log), PYTHON, protocol="app-server",
                                                                   request_stream=encode(outgoing))["recovered"])

    def test_resume_inspection_reads_request_log_without_rewriting_old_result(self):
        with tempfile.TemporaryDirectory() as tmp:
            manifest = self.prepared(Path(tmp).resolve(), self.app_case())
            evidence = Path(manifest["evidence"])
            (evidence / "native").mkdir()
            events, requests = self.resumed_trace(manifest["workspace"])
            (evidence / "native/stdout.jsonl").write_text("\n".join(map(json.dumps, events)), encoding="utf-8")
            (evidence / "result.json").write_text('{"old":true}', encoding="utf-8")
            for i, prompt in enumerate(manifest["prompts"]):
                entry.save(evidence / f"hooks/{i}-UserPromptSubmit.input.json", {
                    "prompt": prompt, "session_id": "native-task", "cwd": manifest["workspace"],
                    "hook_event_name": "UserPromptSubmit"})
            self.assertFalse(entry.inspect(evidence)["sourceRecovered"])
            (evidence / "native/requests.jsonl").write_text("\n".join(map(json.dumps, requests)), encoding="utf-8")
            result = entry.inspect(evidence)
            self.assertTrue(result["sourceRecovered"])
            self.assertEqual(result["sourceRecoveryEvidence"]["requestTraceSha256"], entry.digest(evidence / "native/requests.jsonl"))
            self.assertEqual((evidence / "result.json").read_text(), '{"old":true}')
            # Matching commands in another directory cannot borrow this case's
            # unchanged source hashes or input receipts.
            for event in events:
                item = event.get("params", {}).get("item")
                if item:
                    item["cwd"] = str(Path(tmp) / "other-work")
            (evidence / "native/stdout.jsonl").write_text("\n".join(map(json.dumps, events)), encoding="utf-8")
            self.assertFalse(entry.inspect(evidence)["sourceRecovered"])

    def test_app_server_case_requires_its_actual_inputs_before_result_claims(self):
        with tempfile.TemporaryDirectory() as tmp:
            manifest = self.prepared(Path(tmp).resolve(), self.app_case())
            evidence, work = Path(manifest["evidence"]), Path(manifest["workspace"])
            (work / "details.csv").write_text("id,status,units\nA,ready,60\nB,ready,80\n", encoding="utf-8")
            (work / "summary.json").write_text(json.dumps(manifest["expected"]["summary"]), encoding="utf-8")
            (work / "report.md").write_text("A60 and B80 total 140", encoding="utf-8")
            (evidence / "native").mkdir()
            (evidence / "native/stdout.jsonl").write_text("\n".join(map(json.dumps, self.app_trace(manifest["workspace"]))), encoding="utf-8")
            self.assertFalse(entry.inspect(evidence)["outputsMatch"])
            for i, prompt in enumerate(manifest["prompts"]):
                entry.save(evidence / f"hooks/{i}-UserPromptSubmit.input.json", {
                    "prompt": prompt, "session_id": "native-task", "cwd": str(work), "hook_event_name": "UserPromptSubmit"})
            checked = entry.inspect(evidence)
            self.assertTrue(checked["outputsMatch"])
            self.assertTrue(checked["sourceRecovered"])
            self.assertEqual(checked["limits"], self.app_case()["limits"])
            entry.save(evidence / "hooks/1-UserPromptSubmit.input.json", {
                "prompt": manifest["prompts"][1], "session_id": "foreign-task", "cwd": str(work), "hook_event_name": "UserPromptSubmit"})
            self.assertFalse(entry.inspect(evidence)["caseInputsMatch"])
            entry.save(evidence / "hooks/1-UserPromptSubmit.input.json", {
                "prompt": "a different goal", "session_id": "native-task", "cwd": str(work), "hook_event_name": "UserPromptSubmit"})
            self.assertFalse(entry.inspect(evidence)["outputsMatch"])
            self.assertFalse(entry.inspect(evidence)["sourceRecovered"])

    def test_app_server_recovery_rejects_cross_task_turn_action_and_child_status_splicing(self):
        original = self.app_trace()
        encode = lambda events: "\n".join(map(json.dumps, events))
        self.assertTrue(entry.source_recovery_from_events(encode(original), PYTHON, protocol="app-server")["recovered"])
        self.assertFalse(entry.source_recovery_from_events(encode(original), PYTHON)["recovered"])
        malformed = original + [{"method": "item/completed", "params": {"threadId": "native-task", "item": None}}]
        self.assertFalse(entry.source_recovery_from_events(encode(malformed), PYTHON, protocol="app-server")["recovered"])
        for field, value in (("threadId", "foreign"), ("turnId", "different")):
            events = json.loads(json.dumps(original))
            events[-1]["params"][field] = value
            self.assertFalse(entry.source_recovery_from_events(encode(events), PYTHON, protocol="app-server")["recovered"])
        for mutate in (lambda x: x.update(aggregatedOutput="SOURCE_EXIT=0\n"),
                       lambda x: x.update(exitCode=2),
                       lambda x: x["commandActions"][0].update(command="Write-Output 'SOURCE_EXIT=0'")):
            events = json.loads(json.dumps(original))
            mutate(events[-1]["params"]["item"])
            self.assertFalse(entry.source_recovery_from_events(encode(events), PYTHON, protocol="app-server")["recovered"])

    def propagated_exit_trace(self):
        events = self.app_trace()
        for event in events[1:]:
            item = event["params"]["item"]
            failed = item["id"] == "failed"
            tail = 'if ($code -ne 0) { exit $code }' if failed else 'exit $code'
            item["commandActions"][0]["command"] = (
                "& '" + PYTHON + "' -B order_source.py; "
                '$code = $LASTEXITCODE; Write-Output "EXIT=$code"; ' + tail)
            if event["method"] == "item/completed":
                item["exitCode"] = 75 if failed else 0
                item["status"] = "failed" if failed else "completed"
                item["aggregatedOutput"] = item["aggregatedOutput"].replace("SOURCE_EXIT=", "EXIT=")
        return events

    def test_app_server_recognizes_propagated_native_exit_status(self):
        events = self.propagated_exit_trace()
        observed = entry.source_recovery_from_events("\n".join(map(json.dumps, events)), PYTHON, protocol="app-server")
        self.assertTrue(observed["recovered"])
        self.assertEqual((observed["failedItemId"], observed["successfulItemId"]), ("failed", "success"))

    def test_app_server_accepts_bare_native_executable_but_not_literal_or_similar_commands(self):
        executable = r"C:\Python\python.exe"
        for body, expected in (
            (executable + " -B order_source.py", True),
            ("'" + executable + "' -B order_source.py", False),
            ('"' + executable + '" -B order_source.py', False),
            ("Write-Output '" + executable + " -B order_source.py'", False),
            (executable + ".other -B order_source.py", False),
            (executable + " -B order_source.py; Write-Output 'ok'", False),
        ):
            events = self.app_trace()
            for event in events[1:]:
                item = event["params"]["item"]
                item["command"] = '"C:\\PowerShell\\pwsh.exe" -Command "' + body + '"'
                item["commandActions"] = [{"type": "unknown", "command": body}]
                if event["method"] == "item/completed":
                    failed = item["id"] == "failed"
                    item.update(status="failed" if failed else "completed", exitCode=1 if failed else 0,
                                aggregatedOutput="Local order source temporarily unavailable. Retry this same command.\n"
                                if failed else entry.ORDERS.decode())
            with self.subTest(body=body):
                observed = entry.source_recovery_from_events("\n".join(map(json.dumps, events)), executable, protocol="app-server")
                self.assertEqual(observed["recovered"], expected)

    def test_app_server_recovery_allows_exact_counter_inspection_before_retry(self):
        prefixes = [
            ("Get-ChildItem -Force .source-attempts.json | Select-Object Name,Length; Get-Content -Raw .source-attempts.json; ", True),
            ("Get-Content -Raw .source-attempts.json; ", True),
            ("Get-Content -Raw .source-attempts.json.other; ", False),
            ("Get-Content -Raw .source-attempts.json | Invoke-Expression; ", False),
            ("Get-ChildItem -Force .source-attempts.json | Select-Object Name,Length; Write-Output 'forged'; ", False),
            ("Set-Content .source-attempts.json '[]'; ", False),
        ]
        for prefix, expected in prefixes:
            events = self.app_trace()
            for event in events[1:]:
                item = event["params"]["item"]
                if item["id"] == "success":
                    body = prefix + item["commandActions"][0]["command"]
                    item["commandActions"][0]["command"] = body
                    item["command"] = '"C:\\PowerShell\\pwsh.exe" -Command "' + body + '"'
            with self.subTest(prefix=prefix):
                result = entry.source_recovery_from_events("\n".join(map(json.dumps, events)), PYTHON, protocol="app-server")
                self.assertEqual(result["recovered"], expected)

    def test_propagated_status_rejects_mismatch_and_forged_shell_suffix(self):
        for mutation in ("wrong-native-code", "wrong-printed-code", "extra-command", "wrong-variable", "fixed-exit"):
            events = self.propagated_exit_trace()
            for event in events[1:]:
                item = event["params"]["item"]
                if item["id"] != "failed":
                    continue
                if mutation == "wrong-native-code" and event["method"] == "item/completed":
                    item["exitCode"] = 0
                elif mutation == "wrong-printed-code" and event["method"] == "item/completed":
                    item["aggregatedOutput"] = item["aggregatedOutput"].replace("EXIT=75", "EXIT=0")
                elif mutation == "extra-command":
                    item["commandActions"][0]["command"] += "; Write-Output 'EXIT=75'"
                elif mutation == "wrong-variable":
                    item["commandActions"][0]["command"] = item["commandActions"][0]["command"].replace("exit $code", "exit $other")
                elif mutation == "fixed-exit":
                    item["commandActions"][0]["command"] = item["commandActions"][0]["command"].replace("exit $code", "exit 75")
            with self.subTest(mutation=mutation):
                self.assertFalse(entry.source_recovery_from_events("\n".join(map(json.dumps, events)), PYTHON, protocol="app-server")["recovered"])

    def test_prepare_is_model_free_and_command_preserves_boundaries(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            manifest = self.prepared(root)
            command = manifest["command"]
            self.assertIn("--ephemeral", command)
            self.assertIn("--ignore-user-config", command)
            self.assertNotIn("--dangerously-bypass-approvals-and-sandbox", command)
            self.assertEqual(command[command.index("--sandbox") + 1], "workspace-write")
            self.assertEqual(command[command.index("-m") + 1], "explicit-offline-model")
            self.assertIn('model_reasoning_effort="high"', command)
            self.assertEqual(manifest["windowsSandbox"], "elevated")
            self.assertIn('windows.sandbox="elevated"', command)
            alternative = dict(manifest, windowsSandbox="unelevated")
            self.assertIn('windows.sandbox="unelevated"', entry.build_command(alternative))
            self.assertNotIn('windows.sandbox="elevated"', entry.build_command(alternative))
            configuration = next(value for value in command if value.startswith("hooks={"))
            if entry.tomllib is not None:
                hooks = entry.tomllib.loads(configuration)["hooks"]
                self.assertEqual(set(hooks), set(entry.EVENTS))
                self.assertEqual(hooks["SessionEnd"][0]["hooks"][0]["timeout"], 3)
                self.assertEqual(hooks["Interrupt"][0]["hooks"][0]["timeout"], 3)
            self.assertNotIn("Accord", entry.PROMPT)
            self.assertNotIn("Skill", entry.PROMPT)
            self.assertFalse((root / "evidence/run-started.json").exists())

    def test_real_source_fails_once_then_recovers_without_changing_input(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            manifest = self.prepared(root)
            work = Path(manifest["workspace"])
            original = (work / "orders.csv").read_bytes()
            first = subprocess.run([PYTHON, "-B", str(work / "order_source.py")], capture_output=True)
            second = subprocess.run([PYTHON, "-B", str(work / "order_source.py")], capture_output=True)
            self.assertEqual(first.returncode, 75)
            self.assertIn(b"temporarily unavailable", first.stderr)
            self.assertEqual(second.returncode, 0)
            self.assertEqual(second.stdout, original)
            self.assertEqual((work / "orders.csv").read_bytes(), original)
            result = entry.inspect(manifest["evidence"])
            self.assertEqual(result["sourceAttempts"], [{"attempt": 1, "exit": 75}, {"attempt": 2, "exit": 0}])
            self.assertFalse(result["sourceRecovered"])  # Mutable counter alone is not native execution evidence.
            self.assertFalse(result["outputsMatch"])

    def trace(self, *, first_code=1, second_code=0, first_command=None, reverse=False):
        command = '"C:\\Program Files\\PowerShell\\7\\pwsh.exe" -Command "& \'' + PYTHON + "' -B order_source.py\""
        failure = "Local order source temporarily unavailable. Retry this same command.\r\n"
        def pair(identity, code, text, native_command):
            item = {"id": identity, "type": "command_execution", "command": native_command}
            return [{"type": "item.started", "item": dict(item, status="in_progress", exit_code=None, aggregated_output="")},
                    {"type": "item.completed", "item": dict(item, status="completed" if code == 0 else "failed", exit_code=code, aggregated_output=text)}]
        pairs = [pair("failed", first_code, failure, first_command or command),
                 pair("success", second_code, entry.ORDERS.decode(), command)]
        if reverse:
            pairs.reverse()
        return "\n".join(json.dumps(event) for event in [{"type": "thread.started", "thread_id": "offline-fixture"}] + sum(pairs, []))

    def test_native_recovery_survives_counter_cleanup_and_preserves_old_result(self):
        with tempfile.TemporaryDirectory() as tmp:
            manifest = self.prepared(Path(tmp).resolve())
            evidence, work = Path(manifest["evidence"]), Path(manifest["workspace"])
            (evidence / "stdout.jsonl").write_text(self.trace(), encoding="utf-8")
            (evidence / "result.json").write_text('{"old":true}', encoding="utf-8")
            result = entry.inspect(evidence)
            self.assertIsNone(result["sourceAttempts"])
            self.assertTrue(result["sourceRecovered"])
            self.assertEqual(result["sourceRecoveryEvidence"]["failedItemId"], "failed")
            self.assertEqual(result["sourceRecoveryEvidence"]["successfulItemId"], "success")
            self.assertEqual((evidence / "result.json").read_text(), '{"old":true}')
            (work / "order_source.py").write_text("print('forged')", encoding="utf-8")
            self.assertFalse(entry.inspect(evidence)["sourceRecovered"])

    def test_recovery_rejects_successes_reversed_order_and_printed_error_templates(self):
        commands = [
            '"C:\\Program Files\\PowerShell\\7\\pwsh.exe" -Command "Get-Content order_source.py"',
            '"C:\\Program Files\\PowerShell\\7\\pwsh.exe" -Command "Write-Output \'Local order source temporarily unavailable. Retry this same command.\'; & \'' + PYTHON + "' -B order_source.py\"",
            '"C:\\Program Files\\PowerShell\\7\\pwsh.exe" -Command "Write-Output \'& ' + PYTHON + " -B order_source.py'\"",
        ]
        counterexamples = [self.trace(first_code=0), self.trace(second_code=1), self.trace(reverse=True)]
        counterexamples += [self.trace(first_command=command) for command in commands]
        for stream in counterexamples:
            with self.subTest(stream=stream):
                self.assertFalse(entry.source_recovery_from_events(stream, PYTHON)["recovered"])

    def test_recovery_requires_matching_unique_native_start_completion_pairs(self):
        events = [json.loads(line) for line in self.trace().splitlines()]
        mutations = [events[:1] + events[2:], events + [events[-1]]]
        changed = json.loads(json.dumps(events))
        changed[2]["item"]["command"] = "changed-command"
        mutations.append(changed)
        wrong_csv = json.loads(json.dumps(events))
        wrong_csv[-1]["item"]["aggregated_output"] = "id,status,units\nB,ready,80\nA,ready,60\nC,pending,50\n"
        mutations.append(wrong_csv)
        for mutation in mutations:
            stream = "\n".join(json.dumps(event) for event in mutation)
            self.assertFalse(entry.source_recovery_from_events(stream, PYTHON)["recovered"])

    def test_file_oracle_rejects_wrong_total_and_reports_input_damage(self):
        with tempfile.TemporaryDirectory() as tmp:
            manifest = self.prepared(Path(tmp).resolve())
            work = Path(manifest["workspace"])
            (work / "details.csv").write_text("id,units\nA,60\nB,80\n", encoding="utf-8")
            (work / "summary.json").write_text('{"ready_ids":["A","B"],"total_units":190}', encoding="utf-8")
            (work / "report.md").write_text("Everything passed.", encoding="utf-8")
            self.assertFalse(entry.inspect(manifest["evidence"])["outputsMatch"])
            (work / "summary.json").write_text('{"ready_ids":["A","B"],"total_units":140}', encoding="utf-8")
            self.assertTrue(entry.inspect(manifest["evidence"])["outputsMatch"])
            (work / "keep.txt").write_text("damaged", encoding="utf-8")
            result = entry.inspect(manifest["evidence"])
            self.assertFalse(result["inputsUnchanged"]["keep.txt"])
            self.assertFalse(result["sourceRecovered"])

    def test_run_rejects_source_drift_before_creating_model_receipt(self):
        with tempfile.TemporaryDirectory() as tmp:
            manifest = self.prepared(Path(tmp).resolve())
            Path(manifest["runtime"]).write_text("// changed", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "prepared source changed"):
                entry.run(argparse.Namespace(evidence=manifest["evidence"]))
            self.assertFalse((Path(manifest["evidence"]) / "run-started.json").exists())

    def test_refuses_existing_workspace_without_changing_it(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            self.prepared(root)
            before = (root / "work/keep.txt").read_bytes()
            args = argparse.Namespace(package=str(root / "package"), evidence=str(root / "other-evidence"),
                                      workspace=str(root / "work"), model="m", reasoning="high", windows_sandbox="elevated")
            with self.assertRaisesRegex(ValueError, "fresh root"):
                entry.prepare(args)
            self.assertEqual((root / "work/keep.txt").read_bytes(), before)
            self.assertFalse((root / "other-evidence").exists())

    def test_job_contains_child_and_reclaims_after_parent_exit(self):
        if os.name != "nt":
            # This is the unsupported-platform contract, not Windows execution
            # evidence and not a skipped CI test.
            with self.assertRaisesRegex(ValueError, "requires Windows"):
                entry.WindowsJob()
            return
        job = entry.WindowsJob()
        process = None
        try:
            code = "import subprocess,sys,time; subprocess.Popen([sys.executable,'-c','import time; time.sleep(30)']); time.sleep(2)"
            process = subprocess.Popen([PYTHON, "-c", code], creationflags=subprocess.CREATE_NO_WINDOW | 4)
            job.attach_and_resume(process)
            deadline = time.monotonic() + 5
            observed = job.sample()
            while observed["activeProcesses"] < 2 and time.monotonic() < deadline:
                time.sleep(0.05)
                observed = job.sample()
            self.assertGreaterEqual(observed["activeProcesses"], 2)
            self.assertIn(process.pid, [p["pid"] for p in observed["processes"]])
            self.assertTrue(any(p["workingSetBytes"] for p in observed["processes"]))
            process.wait(timeout=5)
            self.assertGreaterEqual(job.sample()["activeProcesses"], 1)
            job.terminate()
            deadline = time.monotonic() + 5
            while job.sample()["activeProcesses"] and time.monotonic() < deadline:
                time.sleep(0.05)
            self.assertEqual(job.sample()["activeProcesses"], 0)
        finally:
            job.close()
            if process and process.poll() is None:
                process.kill()
                process.wait(timeout=5)


if __name__ == "__main__":
    unittest.main()
