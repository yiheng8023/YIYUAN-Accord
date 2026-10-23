"""Offline oracle and native Windows/POSIX ownership tests; never call a model."""

import argparse
import importlib.util
import json
import hashlib
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import Mock, patch

# The preparer binds resolved executable bytes; synthetic traces must use
# that same identity even when the interpreter was launched through a symlink.
PYTHON = str(Path(sys.executable).resolve())

SCRIPT = Path(__file__).resolve().parents[2] / "scripts/observe_codex_entry.py"
PACKAGE_VERSION = json.loads((SCRIPT.parents[1] / "plugins/yiyuan-accord-codex/.codex-plugin/plugin.json").read_text(encoding="utf-8"))["version"]
spec = importlib.util.spec_from_file_location("observe_codex_entry", SCRIPT)
entry = importlib.util.module_from_spec(spec)
spec.loader.exec_module(entry)


def _unlink_copied_runtime(runtime, owned_root, *, timeout=5):
    runtime, owned_root = Path(runtime), Path(owned_root).resolve()
    if runtime.is_symlink() or not runtime.resolve().is_relative_to(owned_root):
        raise ValueError("runtime cleanup must stay inside the owned fixture")
    deadline = time.monotonic() + timeout
    while True:
        try:
            runtime.unlink(missing_ok=True)
            return
        except PermissionError as error:
            # Job/process exit can precede image deletion readiness (5), as well
            # as external delete-sharing release (32). Persistent errors fail.
            if getattr(error, 'winerror', None) not in (5, 32) or time.monotonic() >= deadline:
                raise
            time.sleep(0.025)


def _wait_fixture_job_empty(job, timeout):
    deadline = time.monotonic() + timeout
    while job.sample()['activeProcesses']:
        if time.monotonic() >= deadline:
            raise AssertionError("copied-runtime fixture left live processes")
        time.sleep(0.025)


def _run_copied_runtime(command, *, runtime, owned_root, cwd, executable=None, exit_timeout=5):
    if os.name != 'nt':
        return subprocess.run(command, executable=executable, cwd=cwd, capture_output=True, timeout=10)
    if Path(runtime).is_symlink() or not Path(runtime).resolve().is_relative_to(Path(owned_root).resolve()):
        raise ValueError("copied runtime must belong to this fixture")
    job, process, natural_exit = entry.WindowsJob(), None, False
    try:
        process = subprocess.Popen(command, executable=executable, cwd=cwd,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            creationflags=subprocess.CREATE_NO_WINDOW | 4)  # CREATE_SUSPENDED
        job.attach_and_resume(process)
        stdout, stderr = process.communicate(timeout=10)
        _wait_fixture_job_empty(job, exit_timeout)
        natural_exit = True
        return subprocess.CompletedProcess(command, process.returncode, stdout, stderr)
    finally:
        try:
            try:
                if not natural_exit:
                    try:
                        job.terminate()
                    finally:
                        # Reap our direct child even if Job assignment/termination
                        # failed before that suspended child could be contained.
                        if process is not None:
                            try:
                                if process.poll() is None:
                                    process.kill()
                            finally:
                                process.communicate(timeout=5)
                    _wait_fixture_job_empty(job, 5)
            finally:
                try:
                    job.close()
                finally:
                    if process is not None and process.returncode is not None:
                        process._handle.Close()
        finally:
            # Attempt exact-file cleanup on failure too. Python's exception
            # chain retains any original execution/recovery error if this fails.
            _unlink_copied_runtime(runtime, owned_root)


class EntryTests(unittest.TestCase):
    def setUp(self):
        # These pre-existing mocked Job tests exercise the Windows branch on all
        # CI hosts. They provide no POSIX execution or containment evidence.
        windows_units = {
            'test_config_observation_survives_a_failed_business_inspection',
            'test_process_controls_reject_invalid_parameters_before_any_probe_or_root',
            'test_process_controls_source_and_parameter_drift_refuse_before_run_receipt',
            'test_process_controls_initial_resume_actual_dispatch_and_receipts_match_manifest',
            'test_process_controls_resume_drift_rejects_before_resources',
            'test_process_controls_ephemeral_dispatch_uses_manifest_argv',
            'test_process_controls_drift_in_final_dispatch_window_releases_job_without_popen',
            'test_sandbox_mode_rejects_invalid_or_inapplicable_controls_before_resources',
            'test_sandbox_mode_drift_is_rejected_by_command_and_binding_before_stage_resources',
            'test_installed_stage_retains_before_and_after_even_for_last_or_failed_turn',
            'test_stage_resource_creation_failure_keeps_native_execution_phase',
            'test_failure_after_agent_popen_keeps_native_execution_phase',
            'test_native_stage_checks_the_opened_prompt_before_starting_a_process',
            'test_persistent_stage_stops_on_running_usage_without_terminal',
            'test_persistent_stage_allows_natural_job_drain_before_termination',
            'test_persistent_stage_forces_timeout_without_a_second_recovery_window',
            'test_windows_copied_runtime_reaps_unassigned_child_if_job_termination_fails',
        }
        if self._testMethodName in windows_units:
            selection = patch.object(entry, '_controller_kind', return_value='windows-job-object')
            selection.start()
            self.addCleanup(selection.stop)

    def usage_event(self, **changes):
        counters = {"totalTokens": 360404, "inputTokens": 355272,
                    "cachedInputTokens": 316800, "outputTokens": 5132}
        counters.update(changes)
        return {"method": "thread/tokenUsage/updated", "params": {
            "threadId": "native-task", "tokenUsage": {"total": counters,
            "last": {"totalTokens": 36705}, "modelContextWindow": 258400}}}

    def test_usage_dimensions_do_not_reinterpret_an_explicit_total_cap(self):
        stream = json.dumps(self.usage_event())
        checked = entry.app_server_usage_budget(stream, thread_id="native-task",
                    caps={"totalTokens": 350000, "outputTokens": 14000})
        self.assertEqual(checked["decision"], "over-limit")
        self.assertEqual(checked["exceeded"], ["totalTokens"])
        self.assertEqual(checked["observed"]["uncachedInputTokens"], 38472)
        self.assertEqual(checked["observed"]["cachedInputTokens"], 316800)
        self.assertIsNone(checked["contextOccupancy"])
        self.assertIsNone(checked["monetaryCost"])
        # Synthetic dimension limits are not permission to revise an old case.
        for key in ("totalTokens", "inputTokens", "uncachedInputTokens", "cachedInputTokens", "outputTokens"):
            value = checked["observed"][key]
            with self.subTest(key=key):
                self.assertEqual(entry.app_server_usage_budget(stream, thread_id="native-task",
                    caps={key: value})["decision"], "within-observed-limits")
                self.assertEqual(entry.app_server_usage_budget(stream, thread_id="native-task",
                    caps={key: value - 1})["exceeded"], [key])
        self.assertEqual(entry.app_server_usage_budget(stream, thread_id="native-task")["decision"], "observe-only")

    def test_usage_unknown_or_regressing_receipts_never_claim_budget_available(self):
        encode = lambda events: "\n".join(map(json.dumps, events))
        valid = self.usage_event()
        malformed = [self.usage_event(cachedInputTokens=None), self.usage_event(outputTokens=True),
                     self.usage_event(cachedInputTokens=400000), self.usage_event(inputTokens=-1)]
        for events in ([], [{"id": 1, "result": valid}], *[[item] for item in malformed],
                       [valid, self.usage_event(totalTokens=10, inputTokens=8, cachedInputTokens=2, outputTokens=2)]):
            with self.subTest(events=events):
                checked = entry.app_server_usage_budget(encode(events), thread_id="native-task", caps={"outputTokens": 14000})
                self.assertEqual(checked["decision"], "unknown")
                self.assertIsNone(checked["observed"])
        self.assertEqual(entry.app_server_usage_budget(encode([valid]), thread_id="foreign-task")["decision"], "unknown")
        after_overrun = entry.app_server_usage_budget(encode([valid, malformed[0]]), thread_id="native-task",
                                                     caps={"totalTokens": 350000})
        self.assertEqual(after_overrun["decision"], "unknown")
        self.assertEqual(after_overrun["exceeded"], ["totalTokens"])
        self.assertEqual(after_overrun["firstExceededReceipt"], 1)
        for caps in ({"contextOccupancy": 1}, {"outputTokens": True}, {"totalTokens": -1}, []):
            with self.subTest(caps=caps), self.assertRaises(ValueError):
                entry.app_server_usage_budget(encode([valid]), thread_id="native-task", caps=caps)

    def test_inspection_reports_usage_without_promoting_outputs_or_changing_limits(self):
        with tempfile.TemporaryDirectory() as tmp:
            case = self.app_case()
            case["limits"]["usageCaps"] = {"totalTokens": 350000, "outputTokens": 14000}
            manifest = self.prepared(Path(tmp).resolve(), case)
            evidence = Path(manifest["evidence"])
            (evidence / "native").mkdir()
            events = self.app_trace(manifest["workspace"]) + [self.usage_event()]
            trace = evidence / "native/stdout.jsonl"
            trace.write_text("\n".join(map(json.dumps, events)), encoding="utf-8")
            original = trace.read_bytes()
            checked = entry.inspect(evidence)
            self.assertEqual(checked["usageObservation"]["decision"], "over-limit")
            self.assertEqual(checked["usageObservation"]["exceeded"], ["totalTokens"])
            self.assertEqual(checked["limits"], case["limits"])
            self.assertFalse(checked["outputsMatch"])
            self.assertFalse(checked["sourceRecovered"])
            self.assertEqual(trace.read_bytes(), original)
            # A malformed declared policy cannot become observation-only on reload.
            manifest["limits"]["usageCaps"] = None
            entry.save(evidence / "manifest.json", manifest)
            with self.assertRaisesRegex(ValueError, "usage caps"):
                entry.inspect(evidence)

    def test_usage_caps_are_checked_before_native_preparation(self):
        case = self.app_case()
        case["limits"]["usageCaps"] = {"contextOccupancy": 350000}
        with tempfile.TemporaryDirectory() as tmp, patch.object(entry.subprocess, "run") as native:
            root = Path(tmp).resolve()
            with self.assertRaisesRegex(ValueError, "usage caps"):
                entry.prepare(argparse.Namespace(evidence=str(root / "evidence"), workspace=str(root / "work")),
                              app_server_case=case)
            native.assert_not_called()
            self.assertFalse((root / "evidence").exists())
            self.assertFalse((root / "work").exists())

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

    def prepared(self, root, case=None, *, controls=None):
        package = root / "package"
        (package / "runtime").mkdir(parents=True)
        (package / "runtime/task-checkpoint.cjs").write_text("// fixture", encoding="utf-8")
        args = argparse.Namespace(package=str(package), evidence=str(root / "evidence"), workspace=str(root / "work"),
                                  codex=PYTHON, node=PYTHON, model="explicit-offline-model",
                                  reasoning="high", timeout=10, windows_sandbox="elevated")
        vars(args).update(controls or {})
        fake = subprocess.CompletedProcess([], 0, b"app-server --ephemeral --ignore-user-config --dangerously-bypass-hook-trust --sandbox --output-last-message", b"")
        with patch.object(entry.subprocess, "run", return_value=fake) as calls:
            entry.prepare(args, app_server_case=case)
        self.assertEqual(calls.call_count, 2)
        self.assertEqual(calls.call_args_list[0].args[0][-2:], ["app-server" if case is not None else "exec", "--help"])
        self.assertEqual(calls.call_args_list[1].args[0][-1], "--version")
        return entry.load_manifest(args.evidence)

    def installed_listing(self, **changes):
        row = {"pluginId": "yiyuan-accord-codex@yiyuan-accord", "name": "yiyuan-accord-codex",
               "marketplaceName": "yiyuan-accord", "version": PACKAGE_VERSION, "installed": True,
               "enabled": True, "source": {"source": "local", "path": "fixture-marketplace"}}
        row.update(changes)
        return subprocess.CompletedProcess([], 0, json.dumps({"installed": [row]}).encode(), b"")

    def copy_hook_only_fixture(self, package):
        # A source-Hook projection fixture is not the complete installed plugin.
        # MCP and onboarding require native plugin loading, not Hook overrides.
        shutil.copytree(SCRIPT.parents[1] / "plugins/yiyuan-accord-codex", package)
        (package / ".mcp.json").unlink()
        metadata_path = package / ".codex-plugin/plugin.json"
        metadata = json.loads(metadata_path.read_bytes())
        extensions = metadata.get("extensions", {})
        openai = extensions.get("com.openai", {})
        openai.pop("onboardingSkill", None)
        if not openai:
            extensions.pop("com.openai", None)
        if not extensions:
            metadata.pop("extensions", None)
        # Keep unknown fields so the strict projection still rejects them.
        entry.save(metadata_path, metadata)

    def prepared_persistent(self, root, case_path=None, *, native_hooks=False, installed=False, admission_case=None,
                            composition=None, controls=None):
        package = (root / "home/plugins/cache/yiyuan-accord/yiyuan-accord-codex" / PACKAGE_VERSION
                   if installed else root / "package")
        if native_hooks:
            self.copy_hook_only_fixture(package)
        elif installed:
            shutil.copytree(SCRIPT.parents[1] / "plugins/yiyuan-accord-codex", package)
        else:
            (package / "runtime").mkdir(parents=True)
            (package / "runtime/task-checkpoint.cjs").write_text("// fixture", encoding="utf-8")
        args = argparse.Namespace(
            package=str(package), evidence=str(root / "evidence"), workspace=str(root / "work"),
            codex=PYTHON, node=shutil.which("node") if native_hooks or installed else PYTHON, model="explicit-offline-model", reasoning="high",
            timeout=600, turn_timeout=180, recovery_timeout=20, windows_sandbox="elevated",
            native_package_hooks=native_hooks, installed_plugin="yiyuan-accord-codex@yiyuan-accord" if installed else None,
            admission_case=admission_case)
        vars(args).update(controls or {})
        case_path = case_path or SCRIPT.parents[1] / "product/cases/coordination-v3.3.json"
        help_exec = subprocess.CompletedProcess([], 0, b"--dangerously-bypass-hook-trust --sandbox --output-last-message --ignore-user-config --disable", b"")
        help_resume = subprocess.CompletedProcess([], 0, b"--json --output-last-message --model", b"")
        version = subprocess.CompletedProcess([], 0, b"codex-cli fixture", b"")
        native_run = entry.subprocess.run
        cli_results = iter([help_exec, help_resume, version])
        def prepared_calls(command, **kwargs):
            if command[1:3] == ["plugin", "list"]:
                return self.installed_listing()
            if (native_hooks or installed) and Path(command[0]) == Path(args.node).resolve() and "-e" in command:
                return native_run(command, **kwargs)
            return next(cli_results)
        with patch.object(entry.subprocess, "run", side_effect=prepared_calls), \
                patch.object(entry, "_native_inventory", return_value=json.loads(self.installed_listing().stdout)):
            entry.prepare(args, persistent_case=entry.load_persistent_case(case_path), composition=composition)
        return entry.load_manifest(args.evidence)

    def composition_request(self):
        return {"case": "composition-case", "execution": {
            "host": "codex", "entry": "cx-desktop",
            "coordinator": {"role": "observer", "sourceRef": "offline-fixture-not-host-evidence"}}}

    def test_composition_preparation_rejects_before_fixture_or_inventory(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            with patch.dict(os.environ, {"CODEX_HOME": str(root / "home")}), \
                    patch.object(entry, "_composition_binding", side_effect=ValueError("composition mismatch")), \
                    patch.object(entry, "_native_inventory") as inventory, \
                    patch.object(entry.subprocess, "Popen") as process:
                with self.assertRaisesRegex(ValueError, "composition mismatch"):
                    self.prepared_persistent(root, installed=True, composition=self.composition_request())
                inventory.assert_not_called()
                process.assert_not_called()
            self.assertFalse((root / "evidence").exists())
            self.assertFalse((root / "work").exists())

    def test_composition_worker_is_derived_without_relabelling_native_entry(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            with patch.dict(os.environ, {"CODEX_HOME": str(root / "home")}):
                manifest = self.prepared_persistent(root, installed=True)
            manifest["nativeVersion"] = "codex-cli 0.158.0"
            request = self.composition_request()
            before = json.dumps(request, sort_keys=True)
            with patch("yiyuan_accord.admission.bind_evidence_execution", return_value={}) as bind:
                entry._composition_binding(manifest, request)
                project, case_id, execution, package_files = bind.call_args.args
                self.assertEqual((project, case_id), (SCRIPT.parents[1], request["case"]))
                self.assertEqual(execution["entry"], "cx-desktop")
                worker = execution["worker"]
                self.assertEqual(worker["entry"], "cx-cli")
                self.assertEqual(worker["codexVersion"], "0.158.0")
                self.assertEqual(execution["caseSha256"], manifest["caseSha256"])
                self.assertEqual(execution["caseFile"], worker["caseFile"])
                self.assertEqual(package_files, manifest["installedPlugin"]["packageFiles"])
                self.assertEqual(json.dumps(request, sort_keys=True), before)
                for key, value in (("model", "different-model"), ("windowsSandbox", "unelevated"),
                                   ("recoveryTimeoutSeconds", 99), ("caseSha256", "f" * 64)):
                    with self.subTest(key=key):
                        entry._composition_binding({**manifest, key: value}, request)
                        self.assertEqual(bind.call_args.args[2]["worker"][key], value)
                for key in ("worker", "runner", "caseFile", "caseSha256"):
                    with self.subTest(reserved=key), self.assertRaises(ValueError):
                        entry._composition_binding(manifest, {**request, "execution": {
                            **request["execution"], key: "caller-cannot-override-worker"}})

    def test_composition_binding_rechecked_before_run_and_each_stage(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            binding = {"case": "composition-case", "subject": {"revision": "frozen"}}
            with patch.dict(os.environ, {"CODEX_HOME": str(root / "home")}), \
                    patch.object(entry, "_composition_binding", return_value=binding) as bind:
                request = self.composition_request()
                manifest = self.prepared_persistent(root, installed=True, composition=request)
                self.assertEqual(bind.call_count, 2)
                self.assertEqual(manifest["compositionBinding"], binding)
                self.assertEqual(manifest["composition"], request)
                bind.return_value = {**binding, "subject": {"revision": "changed"}}
                with patch.object(entry, "_native_inventory", return_value=json.loads(self.installed_listing().stdout)), \
                        patch.object(entry.subprocess, "Popen") as process:
                    for action in (lambda: entry.run_persistent(argparse.Namespace(evidence=manifest["evidence"])),
                                   lambda: entry._verify_native_stage(manifest, 0, None)):
                        with self.assertRaisesRegex(ValueError, "composition binding changed"):
                            action()
                    process.assert_not_called()
                self.assertFalse((root / "evidence/run-started.json").exists())

    def test_composition_prepare_drift_retains_failure_without_run_manifest(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            with patch.dict(os.environ, {"CODEX_HOME": str(root / "home")}), \
                    patch.object(entry, "_composition_binding", side_effect=[
                        {"case": "composition-case"}, ValueError("private-external-detail")]), \
                    patch.object(entry, "_entry_guide", return_value="Accord task entry: fixture"), \
                    patch.object(entry.subprocess, "Popen") as process:
                with self.assertRaises(ValueError):
                    self.prepared_persistent(root, installed=True, composition=self.composition_request())
                process.assert_not_called()
            receipt = json.loads((root / "evidence/preparation-failed.json").read_text())
            self.assertFalse(receipt["modelCalled"])
            self.assertNotIn("private-external-detail", json.dumps(receipt))
            self.assertFalse((root / "evidence/manifest.json").exists())
            self.assertFalse((root / "evidence/run-started.json").exists())
            self.assertTrue((root / "work/keep.txt").is_file())

    def test_admission_preparation_rejects_before_fixture_writes_or_dispatch(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            with patch.dict(os.environ, {"CODEX_HOME": str(root / "home")}), \
                    patch.object(entry, "_admission_binding", side_effect=ValueError("case mismatch")), \
                    patch.object(entry, "_native_inventory") as inventory, \
                    patch.object(entry.subprocess, "Popen") as process:
                with self.assertRaisesRegex(ValueError, "case mismatch"):
                    self.prepared_persistent(root, installed=True, admission_case="formal-case")
                inventory.assert_not_called()
                process.assert_not_called()
            self.assertFalse((root / "evidence").exists())
            self.assertFalse((root / "work").exists())

    def test_admission_binding_rechecked_before_model_and_each_native_stage(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            binding = {"case": "formal-case", "subject": {"revision": "frozen"}}
            with patch.dict(os.environ, {"CODEX_HOME": str(root / "home")}), \
                    patch.object(entry, "_admission_binding", return_value=binding) as bind:
                manifest = self.prepared_persistent(root, installed=True, admission_case="formal-case")
                self.assertEqual(bind.call_count, 2)
                self.assertEqual(manifest["admissionBinding"], binding)
                bind.return_value = {**binding, "subject": {"revision": "changed"}}
                with patch.object(entry, "_native_inventory", return_value=json.loads(self.installed_listing().stdout)), \
                        patch.object(entry.subprocess, "Popen") as process:
                    for action in (lambda: entry.run_persistent(argparse.Namespace(evidence=manifest["evidence"])),
                                   lambda: entry._verify_native_stage(manifest, 0, None)):
                        with self.assertRaisesRegex(ValueError, "admission binding changed"):
                            action()
                    process.assert_not_called()
                self.assertFalse((root / "evidence/run-started.json").exists())

    def test_admission_bridge_derives_execution_settings_without_copying_expected_conditions(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            with patch.dict(os.environ, {"CODEX_HOME": str(root / "home")}):
                manifest = self.prepared_persistent(root, installed=True)
            with patch("yiyuan_accord.admission.bind_evidence_execution", return_value={}) as bind:
                with self.assertRaisesRegex(ValueError, "exact native version"):
                    entry._admission_binding(manifest, "formal-case")
                bind.assert_not_called()
                manifest["nativeVersion"] = "codex-cli 0.156.1"
                entry._admission_binding(manifest, "formal-case")
                project, case_id, execution, package_files = bind.call_args.args
                self.assertEqual(project, SCRIPT.parents[1])
                self.assertEqual(case_id, "formal-case")
                expected = {
                    "host": "codex", "entry": "cx-cli", "codexVersion": "0.156.1",
                    "entryProtocol": "exec-resume", "hookMode": "installed-plugin",
                    "model": "explicit-offline-model", "reasoning": "high", "windowsSandbox": "elevated",
                    "timeoutSeconds": 600, "turnTimeoutSeconds": 180, "recoveryTimeoutSeconds": 20,
                    "caseSha256": manifest["caseSha256"], "usageCaps": manifest["limits"]["usageCaps"],
                    "usageScope": manifest["limits"]["usageScope"],
                    "runner": "scripts/observe_codex_entry.py", "caseFile": "product/cases/coordination-v3.3.json"}
                if manifest.get("resourceController") == "posix-session-process-group":
                    expected.update(resourceController=manifest["resourceController"],
                                    resourceEvidenceScope=manifest["resourceEvidenceScope"])
                self.assertEqual(execution, expected)
                self.assertEqual(package_files, manifest["installedPlugin"]["packageFiles"])

    def test_admission_prepare_drift_retains_failed_receipt_without_runnable_manifest(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            with patch.dict(os.environ, {"CODEX_HOME": str(root / "home")}), \
                    patch.object(entry, "_admission_binding", side_effect=[
                        {"case": "formal-case"}, ValueError("private-external-detail")]), \
                    patch.object(entry, "_entry_guide", return_value="Accord task entry: fixture"), \
                    patch.object(entry.subprocess, "Popen") as process:
                with self.assertRaises(ValueError):
                    self.prepared_persistent(root, installed=True, admission_case="formal-case")
                process.assert_not_called()
            receipt = json.loads((root / "evidence/preparation-failed.json").read_text())
            self.assertEqual(receipt["state"], "failed")
            self.assertFalse(receipt["modelCalled"])
            self.assertEqual(receipt["retainedRoots"], {"evidence": str(root / "evidence"),
                                                       "workspace": str(root / "work")})
            self.assertNotIn("private-external-detail", json.dumps(receipt))
            self.assertFalse((root / "evidence/manifest.json").exists())
            self.assertFalse((root / "evidence/run-started.json").exists())
            self.assertTrue((root / "work/keep.txt").is_file())

    def test_installed_entry_preserves_native_discovery_trust_and_configuration(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            with patch.dict(os.environ, {"CODEX_HOME": str(root / "home")}):
                manifest = self.prepared_persistent(root, installed=True)
                self.assertEqual(manifest["hookMode"], "installed-plugin")
                self.assertNotIn("nativeHookProjection", manifest)
                source = SCRIPT.parents[1] / "plugins/yiyuan-accord-codex"
                self.assertEqual(manifest["installedPlugin"]["packageFiles"], {
                    p.relative_to(source).as_posix(): entry.digest(p)
                    for p in source.rglob("*") if p.is_file()})
                self.assertIn(".mcp.json", manifest["installedPlugin"]["packageFiles"])
                self.assertFalse((root / "evidence/hooks").exists())
                for command in (manifest["initialCommand"], entry.build_command(manifest, stage=1, thread_id="native-thread")):
                    for flag in ("--ignore-user-config", "--disable", "--enable", "--dangerously-bypass-hook-trust", "--ephemeral"):
                        self.assertNotIn(flag, command)
                    self.assertFalse(any(value.startswith("hooks=") for value in command))
                    self.assertIn('sandbox_mode="workspace-write"', command)
                with self.assertRaisesRegex(ValueError, "native hook discovery"):
                    entry._hook_configuration(manifest)
                with self.assertRaisesRegex(ValueError, "cannot use the checkpoint wrapper"):
                    entry.hook(argparse.Namespace(evidence=manifest["evidence"], event="Stop"))

    def control_skills(self, root):
        paths = []
        for name in ('one', 'two', 'unselected'):
            path = root / 'synthetic-skills' / name / 'SKILL.md'
            path.parent.mkdir(parents=True)
            path.write_text('---\nname: ' + name + '\ndescription: offline fixture\n---\nLocal only.\n', encoding='utf-8')
            paths.append(path)
        return paths

    def cli_config_overrides(self, command):
        # Check exact native assignments on every supported Python version.
        # A standard TOML parser adds syntax checking where available (3.11+).
        self.assertEqual(command[1], 'exec')
        self.assertNotIn('-c', command[:2])
        parsed = {}
        roots = set()
        for index, argument in enumerate(command):
            if argument == '-c':
                assignment = command[index + 1]
                key, separator, value = assignment.partition('=')
                self.assertEqual(separator, '=')
                self.assertRegex(key, r'\A[A-Za-z_][A-Za-z_0-9]*(?:\.[A-Za-z_][A-Za-z_0-9]*)*\Z')
                root = key.split('.', 1)[0]
                self.assertNotIn(root, roots)
                roots.add(root)
                if entry.tomllib is not None:
                    entry.tomllib.loads(assignment)
                parsed[key] = value
        return parsed

    def expected_skill_exclusions(self, *paths):
        return '[' + ','.join('{"path"=' + json.dumps(str(p), ensure_ascii=False) + ',"enabled"=false}' for p in paths) + ']'

    def test_process_controls_override_oracle_rejects_aliases_and_preserves_unicode(self):
        for parser in (entry.tomllib, None):
            with patch.object(entry, 'tomllib', parser):
                for alias in ('skills = {config=[]}', '"skills"={config=[]}'):
                    with self.subTest(alias=alias, parser=parser is not None), self.assertRaises(AssertionError):
                        self.cli_config_overrides(['codex', 'exec', '-c', 'skills.config=[]', '-c', alias])
        self.assertEqual(self.expected_skill_exclusions('C:/测试/😀/SKILL.md'),
                         '[{"path"="C:/测试/😀/SKILL.md","enabled"=false}]')

    def test_process_controls_default_argv_and_manifest_remain_legacy(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            manifest = self.prepared(root)
            self.assertNotIn('controls', manifest)
            self.assertNotIn('controlsSha256', manifest)
            self.assertEqual(entry._prepare_controls(argparse.Namespace(), 'exec'), {})
            self.assertEqual(entry._prepare_controls(argparse.Namespace(exclude_skill=[], project_doc_max_bytes=None), 'exec'), {})
            expected = dict(manifest)
            expected.pop('command')
            self.assertEqual(manifest['command'], entry.build_command(expected))
            config = self.cli_config_overrides(manifest['command'])
            self.assertFalse(any(k == 'skills' or k.startswith('skills.') for k in config))
            self.assertNotIn('project_doc_max_bytes', config)
            self.assertEqual(config['approval_policy'], '"never"')
        self.test_sandbox_mode_preserves_legacy_default_and_binds_initial_and_resume()

    def test_process_controls_reject_invalid_parameters_before_any_probe_or_root(self):
        invalid = [dict(project_doc_max_bytes=value) for value in (-1, True, 1.5, '42', 2**63)]
        invalid += [dict(exclude_skill=value) for value in ('SKILL.md', False, [None], [''], ['relative/SKILL.md'])]
        for controls in invalid:
            with self.subTest(controls=controls), patch.object(entry.subprocess, 'run') as probe, \
                    patch.object(entry, 'ordinary_dir') as directory, patch.object(entry, 'WindowsJob') as job:
                with self.assertRaises((ValueError, OSError)):
                    entry.prepare(argparse.Namespace(**controls))
                probe.assert_not_called()
                directory.assert_not_called()
                job.assert_not_called()
        with patch.object(entry.subprocess, 'run') as probe:
            with self.assertRaisesRegex(ValueError, 'require a CLI'):
                entry.prepare(argparse.Namespace(project_doc_max_bytes=0), app_server_case={})
            probe.assert_not_called()

    def test_process_controls_reject_missing_directory_duplicate_and_hardlink_skills(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            one, two, _ = self.control_skills(root)
            wrong = root / 'wrong.md'; wrong.write_text('fixture')
            hard = root / 'hard' / 'SKILL.md'; hard.parent.mkdir()
            os.link(two, hard)
            cases = [[str(root / 'missing/SKILL.md')], [str(one.parent)], [str(wrong)],
                     [str(one), str(one)], [str(hard)]]
            for paths in cases:
                with self.subTest(paths=paths), patch.object(entry.subprocess, 'run') as probe:
                    with self.assertRaises((ValueError, OSError)):
                        entry.prepare(argparse.Namespace(exclude_skill=paths))
                    probe.assert_not_called()
                    self.assertFalse((root / 'evidence').exists())

    def test_process_controls_prepare_binds_exact_identities_and_native_toml(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            one, two, other = self.control_skills(root)
            before = {p: (p.read_bytes(), p.stat().st_mtime_ns) for p in (one, two, other)}
            manifest = self.prepared(root, controls={'exclude_skill': [str(two), str(one)], 'project_doc_max_bytes': 0})
            self.assertEqual([row['path'] for row in manifest['controls']['excludedSkills']], [str(two), str(one)])
            self.assertEqual(manifest['controls']['excludedSkills'], [entry._skill_identity(str(two)), entry._skill_identity(str(one))])
            self.assertEqual(manifest['controlsSha256'], entry._controls_sha256(manifest['controls']))
            config = self.cli_config_overrides(manifest['command'])
            self.assertEqual(config['skills.config'], self.expected_skill_exclusions(two, one))
            self.assertEqual(config['project_doc_max_bytes'], '0')
            self.assertEqual({p: (p.read_bytes(), p.stat().st_mtime_ns) for p in before}, before)

    def test_process_controls_document_only_and_skill_only_have_no_implicit_overrides(self):
        for kind in ('doc', 'skill'):
            with self.subTest(kind=kind), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp).resolve(); one, _, _ = self.control_skills(root)
                controls = {'project_doc_max_bytes': 2**63-1} if kind == 'doc' else {'exclude_skill': [str(one)]}
                manifest = self.prepared(root, controls=controls)
                config = self.cli_config_overrides(manifest['command'])
                if kind == 'doc':
                    self.assertEqual(config['project_doc_max_bytes'], str(2**63-1))
                    self.assertFalse(any(k == 'skills' or k.startswith('skills.') for k in config))
                else:
                    self.assertEqual(config['skills.config'], self.expected_skill_exclusions(one))
                    self.assertNotIn('project_doc_max_bytes', config)

    def test_process_controls_source_and_parameter_drift_refuse_before_run_receipt(self):
        for mutation in ('content', 'mtime', 'replacement', 'missing', 'parameter', 'rehashed-parameter', 'command'):
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp).resolve(); one, _, _ = self.control_skills(root)
                manifest = self.prepared(root, controls={'exclude_skill': [str(one)], 'project_doc_max_bytes': 64})
                if mutation == 'content': one.write_text('changed')
                elif mutation == 'mtime': os.utime(one, ns=(one.stat().st_atime_ns, one.stat().st_mtime_ns+1000000000))
                elif mutation == 'replacement':
                    stat = one.stat(); replacement = one.with_name('new.md'); replacement.write_bytes(one.read_bytes())
                    os.utime(replacement, ns=(stat.st_atime_ns, stat.st_mtime_ns)); os.replace(replacement, one)
                elif mutation == 'missing': one.unlink()
                elif mutation in ('parameter', 'rehashed-parameter'):
                    manifest['controls']['projectDocMaxBytes'] = 65
                    if mutation == 'rehashed-parameter': manifest['controlsSha256'] = entry._controls_sha256(manifest['controls'])
                else: manifest['command'].insert(-1, '-c'); manifest['command'].insert(-1, 'project_doc_max_bytes=9')
                entry.save(root / 'evidence/manifest.json', manifest)
                with patch.object(entry.subprocess, 'Popen') as process, patch.object(entry, 'WindowsJob') as job, \
                        patch.object(entry, 'shared_config_snapshot') as shared:
                    with self.assertRaises((ValueError, OSError)):
                        entry.run(argparse.Namespace(evidence=manifest['evidence']))
                    process.assert_not_called(); job.assert_not_called(); shared.assert_not_called()
                self.assertFalse((root / 'evidence/run-started.json').exists())

    def test_process_controls_preparation_drift_is_not_silently_adopted(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve(); one, _, _ = self.control_skills(root)
            package = root / 'package'; (package / 'runtime').mkdir(parents=True)
            (package / 'runtime/task-checkpoint.cjs').write_text('// fixture')
            args = argparse.Namespace(package=str(package), evidence=str(root/'evidence'), workspace=str(root/'work'),
                codex=PYTHON, node=PYTHON, model='offline', reasoning='high', timeout=10,
                windows_sandbox='elevated', exclude_skill=[str(one)], project_doc_max_bytes=0)
            def mutate(*args, **kwargs):
                one.write_text('changed during help probe')
                return subprocess.CompletedProcess([], 0, b'--ephemeral --ignore-user-config --dangerously-bypass-hook-trust --sandbox --output-last-message', b'')
            with patch.object(entry.subprocess, 'run', side_effect=mutate), patch.object(entry.subprocess, 'Popen') as process:
                with self.assertRaisesRegex(ValueError, 'prepared excluded Skill changed'):
                    entry.prepare(args)
                process.assert_not_called()
            self.assertFalse((root/'evidence').exists())
            self.assertFalse((root/'work').exists())

    def test_process_controls_initial_resume_actual_dispatch_and_receipts_match_manifest(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve(); one, two, other = self.control_skills(root)
            manifest = self.prepared_persistent(root, controls={'exclude_skill': [str(one), str(two)], 'project_doc_max_bytes': 17})
            actual = []
            process = Mock(returncode=0); process.poll.return_value = 0
            job = Mock(); job.sample.return_value = {'activeProcesses': 0}
            def spawn(command, **kwargs):
                actual.append(list(command))
                stage = len(actual)
                events = [{'type':'thread.started','thread_id':'native-thread'}, {'type':'turn.started'},
                          {'type':'item.completed','item':{'type':'agent_message','text':'done'}},
                          {'type':'turn.completed','usage':{'input_tokens':100,'cached_input_tokens':0,'output_tokens':1}}]
                kwargs['stdout'].write(('\n'.join(map(json.dumps, events))+'\n').encode())
                (root / f'evidence/last-message-{stage}.txt').write_text('done')
                return process
            with patch.object(entry.subprocess, 'Popen', side_effect=spawn), \
                    patch.object(entry.subprocess, 'CREATE_NO_WINDOW', 0, create=True), \
                    patch.object(entry, 'WindowsJob', return_value=job):
                receipts = [entry._run_persistent_stage(manifest, i, 'native-thread' if i else None, {}, time.monotonic()+10) for i in (0,1)]
            initial = manifest['initialCommand']
            resumed = list(manifest['stageCommandTemplates'][1]); resumed[-2] = 'native-thread'
            self.assertEqual(actual, [initial, resumed])
            for receipt, command in zip(receipts, actual):
                self.assertTrue(receipt['valid'], receipt)
                self.assertEqual(receipt['command'], command)
                config = self.cli_config_overrides(command)
                self.assertEqual(config['skills.config'], self.expected_skill_exclusions(one, two))
                self.assertEqual(config['project_doc_max_bytes'], '17')
                self.assertEqual(config['approval_policy'], '"never"')
                self.assertEqual(config['sandbox_mode'], '"workspace-write"')
            self.assertEqual(job.close.call_count, 2)
            self.assertEqual(other.read_text().splitlines()[1], 'name: unselected')

    def test_process_controls_resume_drift_rejects_before_resources(self):
        for mutation in ('skill', 'controls', 'template', 'removed'):
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp).resolve(); one, _, _ = self.control_skills(root)
                manifest = self.prepared_persistent(root, controls={'exclude_skill':[str(one)], 'project_doc_max_bytes': 20})
                if mutation == 'skill': one.write_text('changed between turns')
                elif mutation == 'controls': manifest['controls']['projectDocMaxBytes'] = 21
                elif mutation == 'template': manifest['stageCommandTemplates'][1].insert(-1, 'unexpected')
                else: manifest.pop('controls'); manifest.pop('controlsSha256')
                failed = []
                with patch.object(entry.subprocess, 'Popen') as process, patch.object(entry, 'WindowsJob') as job:
                    with self.assertRaises((ValueError, OSError)):
                        entry._run_persistent_stage(manifest, 1, 'native-thread', {}, time.monotonic()+10, preflight_failure=failed)
                    process.assert_not_called(); job.assert_not_called()
                self.assertEqual(failed, [True])

    def test_process_controls_cli_arguments_reach_preparation_without_passthrough(self):
        argv = ['observe_codex_entry.py', 'prepare']
        for key in ('package', 'evidence', 'workspace', 'codex', 'node', 'model', 'reasoning'):
            argv += ['--'+key, 'offline-'+key]
        argv += ['--timeout','10','--windows-sandbox','elevated', '--exclude-skill','first/SKILL.md',
                 '--exclude-skill','second/SKILL.md', '--project-doc-max-bytes','0']
        with patch.object(sys, 'argv', argv), patch.object(entry, 'prepare', return_value={'prepared': True}) as prepare, \
                patch.object(sys, 'stdout'):
            entry.main()
        args = prepare.call_args.args[0]
        self.assertEqual(args.exclude_skill, ['first/SKILL.md', 'second/SKILL.md'])
        self.assertEqual(args.project_doc_max_bytes, 0)
        with patch.object(sys, 'argv', argv + ['--config', 'arbitrary=true']), patch.object(sys, 'stderr'), \
                patch.object(entry, 'prepare') as prepare:
            with self.assertRaises(SystemExit) as rejected:
                entry.main()
            self.assertEqual(rejected.exception.code, 2)
            prepare.assert_not_called()

    def test_process_controls_malformed_manifest_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve(); one, _, _ = self.control_skills(root)
            manifest = self.prepared(root, controls={'exclude_skill':[str(one)]})
            for mutation in ('unknown', 'boolean', 'identity', 'missing-binding', 'wrong-binding'):
                changed = json.loads(json.dumps(manifest))
                if mutation == 'unknown': changed['controls']['toml'] = 'arbitrary=true'
                elif mutation == 'boolean': changed['controls']['projectDocMaxBytes'] = True
                elif mutation == 'identity': changed['controls']['excludedSkills'][0]['sha256'] = 'unknown'
                elif mutation == 'missing-binding': changed.pop('controlsSha256')
                else: changed['controlsSha256'] = '0'*64
                entry.save(root/'evidence/manifest.json', changed)
                with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                    entry.load_manifest(manifest['evidence'])

    def test_process_controls_ephemeral_dispatch_uses_manifest_argv(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve(); one, _, _ = self.control_skills(root)
            manifest = self.prepared(root, controls={'exclude_skill':[str(one)], 'project_doc_max_bytes': 7})
            process = Mock(pid=123, returncode=0); process.poll.return_value = 0
            job = Mock(); job.sample.return_value = {'activeProcesses':0}
            actual = []
            def spawn(command, **kwargs):
                actual.append(list(command))
                self.assertEqual(kwargs['cwd'], manifest['workspace'])
                return process
            observation = {'state':'observed','sha256':'offline'}
            with patch.dict(os.environ, {'CODEX_HOME':str(root/'isolated-home')}), \
                    patch.object(entry, 'shared_config_snapshot', return_value=observation), \
                    patch.object(entry, 'inspect', return_value={'runtimeStateResidue':[]}), \
                    patch.object(entry.subprocess, 'CREATE_NO_WINDOW', 0, create=True), \
                    patch.object(entry, 'WindowsJob', return_value=job), patch.object(entry.subprocess, 'Popen', side_effect=spawn):
                result = entry.run(argparse.Namespace(evidence=manifest['evidence']))
            self.assertEqual(actual, [manifest['command']])
            self.assertEqual(self.cli_config_overrides(actual[0])['skills.config'], self.expected_skill_exclusions(one))
            self.assertEqual(self.cli_config_overrides(actual[0])['project_doc_max_bytes'], '7')
            self.assertEqual(json.loads((root/'evidence/run-started.json').read_bytes())['command'], actual[0])
            self.assertEqual(result['process']['remainingOwnedProcesses'], 0)
            job.close.assert_called_once()

    def test_process_controls_direct_hook_modes_share_the_same_native_overrides(self):
        for mode in ('native', 'installed'):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp).resolve(); one, _, _ = self.control_skills(root)
                with patch.dict(os.environ, {'CODEX_HOME': str(root/'home')}):
                    manifest = self.prepared_persistent(root, native_hooks=mode=='native', installed=mode=='installed',
                        controls={'exclude_skill':[str(one)], 'project_doc_max_bytes':11})
                for stage in (0,1):
                    command = entry.build_command(manifest, stage=stage, thread_id='thread' if stage else None)
                    config = self.cli_config_overrides(command)
                    self.assertEqual(config['skills.config'], self.expected_skill_exclusions(one))
                    self.assertEqual(config['project_doc_max_bytes'], '11')
                    self.assertEqual(config['approval_policy'], '"never"')
                execution = entry._execution_settings({**manifest, 'nativeVersion':'codex-cli 0.156.1'})
                self.assertEqual(execution['controls'], manifest['controls'])
                execution['controls']['projectDocMaxBytes'] = 12
                self.assertEqual(manifest['controls']['projectDocMaxBytes'], 11)

    def test_process_controls_drift_in_final_dispatch_window_releases_job_without_popen(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve(); one, _, _ = self.control_skills(root)
            manifest = self.prepared_persistent(root, controls={'exclude_skill':[str(one)]})
            job = Mock(); job.sample.return_value = {'activeProcesses':0}
            def changed_after_preflight():
                one.write_text('changed before dispatch')
                return job
            with patch.object(entry, 'WindowsJob', side_effect=changed_after_preflight), patch.object(entry.subprocess, 'Popen') as process:
                receipt = entry._run_persistent_stage(manifest, 0, None, {}, time.monotonic()+10)
                process.assert_not_called()
            self.assertFalse(receipt['valid'])
            self.assertIn('prepared excluded Skill changed', receipt['failure'])
            job.close.assert_called_once()

    def sandbox_manifest(self):
        # Pure offline declaration: no native inventory, sandbox or fixture roots.
        return {"entryProtocol": "exec-resume", "hookMode": "installed-plugin",
                "codex": PYTHON, "package": str(SCRIPT.parents[1] / "plugins/yiyuan-accord-codex"),
                "evidence": str(SCRIPT.parent / "offline-evidence"),
                "workspace": str(SCRIPT.parent / "offline-work"), "prompts": ["initial", "resume"],
                "model": "explicit-offline-model", "reasoning": "high", "windowsSandbox": "elevated",
                "nativeVersion": "codex-cli 0.156.1", "runner": str(SCRIPT),
                "case": str(SCRIPT.parents[1] / "product/cases/coordination-v3.3.json"),
                "caseSha256": "fixture", "timeoutSeconds": 600, "turnTimeoutSeconds": 180,
                "recoveryTimeoutSeconds": 20, "limits": {"usageCaps": {"totalTokens": 1000},
                                                        "usageScope": "native cumulative fixture"}}

    def test_sandbox_mode_preserves_legacy_default_and_binds_initial_and_resume(self):
        manifest = self.sandbox_manifest()
        initial = entry.build_command(manifest)
        expected = [PYTHON, "exec", "--skip-git-repo-check", "--sandbox", "workspace-write",
                    "--json", "--color", "never", "--output-last-message",
                    str(Path(manifest["evidence"]) / "last-message-1.txt"), "-C", manifest["workspace"],
                    "--add-dir", str(Path(manifest["evidence"]) / "state"), "-m", manifest["model"],
                    "-c", 'approval_policy="never"', "-c", 'sandbox_mode="workspace-write"',
                    "-c", 'model_reasoning_effort="high"', "-c", 'windows.sandbox="elevated"', "-"]
        self.assertEqual(initial, expected)
        legacy_execution = entry._execution_settings(manifest)
        self.assertEqual(set(legacy_execution), {
            "host", "entry", "codexVersion", "entryProtocol", "hookMode", "model", "reasoning",
            "windowsSandbox", "timeoutSeconds", "turnTimeoutSeconds", "recoveryTimeoutSeconds",
            "caseSha256", "usageCaps", "usageScope", "runner", "caseFile"})
        explicit_default = {**manifest, "sandboxMode": "workspace-write"}
        for stage in (0, 1):
            thread = "observed-thread" if stage else None
            self.assertEqual(entry.build_command(manifest, stage=stage, thread_id=thread),
                             entry.build_command(explicit_default, stage=stage, thread_id=thread))
        self.assertEqual(entry._execution_settings(explicit_default), legacy_execution)
        wider = {**manifest, "sandboxMode": "danger-full-access"}
        for stage in (0, 1):
            command = entry.build_command(wider, stage=stage, thread_id="observed-thread" if stage else None)
            self.assertIn('sandbox_mode="danger-full-access"', command)
            self.assertNotIn('sandbox_mode="workspace-write"', command)
            self.assertIn('approval_policy="never"', command)
            if not stage:
                self.assertEqual(command[command.index("--sandbox") + 1], "danger-full-access")
            else:
                self.assertEqual(command[-2:], ["observed-thread", "-"])
        self.assertEqual(entry._execution_settings(wider), {**legacy_execution, "sandboxMode": "danger-full-access"})

    def test_sandbox_mode_rejects_invalid_or_inapplicable_controls_before_resources(self):
        rejected = [("danger-full-access", "exec", "checkpoint-wrapper"),
                    ("danger-full-access", "app-server", "checkpoint-wrapper"),
                    ("danger-full-access", "exec-resume", "checkpoint-wrapper"),
                    ("danger-full-access", "exec-resume", "native-package-hooks")]
        rejected += [(mode, "exec-resume", "installed-plugin") for mode in ("read-only", "", None, [], True)]
        for mode, protocol, hooks in rejected:
            with self.subTest(mode=mode, protocol=protocol, hooks=hooks), \
                    patch.object(entry, "ordinary_dir") as directory, \
                    patch.object(entry, "WindowsJob") as job, \
                    patch.object(entry.subprocess, "run") as probe, \
                    patch.object(entry.subprocess, "Popen") as process:
                args = argparse.Namespace(sandbox_mode=mode, native_package_hooks=hooks == "native-package-hooks",
                                          installed_plugin="plugin@market" if hooks == "installed-plugin" else None)
                with self.assertRaisesRegex(ValueError, "sandbox mode|requires installed-plugin"):
                    entry.prepare(args, persistent_case=() if protocol == "exec-resume" else None,
                                  app_server_case={} if protocol == "app-server" else None)
                directory.assert_not_called()
                job.assert_not_called()
                probe.assert_not_called()
                process.assert_not_called()
                manifest = {**self.sandbox_manifest(), "sandboxMode": mode,
                            "entryProtocol": protocol, "hookMode": hooks}
                with self.assertRaises(ValueError):
                    entry.build_command(manifest)
                manifest.update(schema="accord-codex-entry/v1")
                evidence = Path(manifest["evidence"])
                with patch.object(entry, "ordinary_dir", return_value=evidence), \
                        patch.object(entry, "read_regular", return_value=json.dumps(manifest).encode()):
                    with self.assertRaises(ValueError):
                        entry.load_manifest(evidence)

    def test_sandbox_mode_drift_is_rejected_by_command_and_binding_before_stage_resources(self):
        for guard in ("command", "binding"):
            with self.subTest(guard=guard):
                manifest = {**self.sandbox_manifest(), "sandboxMode": "danger-full-access",
                            "sourceHashes": {}, "installedPlugin": {"pluginId": "plugin@market"},
                            "entryGuide": "Accord task entry: fixture"}
                manifest["entryGuideSha256"] = hashlib.sha256(manifest["entryGuide"].encode()).hexdigest()
                manifest["initialCommand"] = entry.build_command(manifest)
                manifest["stageCommandTemplates"] = [manifest["initialCommand"]]
                manifest["promptSha256s"] = [hashlib.sha256(b"initial").hexdigest()]
                if guard == "binding":
                    manifest["admissionBinding"] = {"case": "formal-case", "execution": entry._execution_settings(manifest)}
                manifest["sandboxMode"] = "workspace-write"
                failure = []
                with patch.object(entry, "_installed_plugin_binding", return_value=manifest["installedPlugin"]), \
                        patch.object(entry, "_admission_binding", side_effect=lambda m, case: {
                            "case": case, "execution": entry._execution_settings(m)}), \
                        patch.object(entry, "read_regular", side_effect=[
                            json.dumps({"stages": [{"prompt": "initial"}]}).encode(), b"initial"]), \
                        patch.object(entry, "WindowsJob") as job, \
                        patch.object(entry.subprocess, "Popen") as process:
                    with self.assertRaisesRegex(ValueError, "prepared stage command|prepared admission binding"):
                        entry._run_persistent_stage(manifest, 0, None, {}, time.monotonic() + 1,
                                                    preflight_failure=failure)
                    job.assert_not_called()
                    process.assert_not_called()
                self.assertEqual(failure, [True])

    def test_installed_binding_rejects_catalog_or_package_drift_without_model_dispatch(self):
        for mutation in ("disabled", "absent", "version", "source", "skill", "added-file", "home", "copy"):
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp).resolve()
                with patch.dict(os.environ, {"CODEX_HOME": str(root / "home")}):
                    manifest = self.prepared_persistent(root, installed=True)
                    reply = self.installed_listing()
                    if mutation == "disabled": reply = self.installed_listing(enabled=False)
                    elif mutation == "absent": reply = subprocess.CompletedProcess([], 0, b'{"installed":[]}', b'')
                    elif mutation == "version": reply = self.installed_listing(version="other")
                    elif mutation == "source": reply = self.installed_listing(source={"source": "local", "path": "other-market"})
                    elif mutation == "skill": (Path(manifest["package"]) / "skills/coordinate-capabilities/SKILL.md").write_text("changed")
                    elif mutation == "added-file": (Path(manifest["package"]) / "extra.txt").write_text("new")
                    elif mutation == "home":
                        (root / "other-home").mkdir()
                        os.environ["CODEX_HOME"] = str(root / "other-home")
                    elif mutation == "copy":
                        shutil.copytree(manifest["package"], root / "copied-package")
                        manifest["package"] = str(root / "copied-package")
                    entry.save(root / "evidence/manifest.json", manifest)
                    with patch.object(entry, "_native_inventory", return_value=json.loads(reply.stdout)), patch.object(entry.subprocess, "Popen") as process:
                        with self.assertRaises(ValueError):
                            entry.run_persistent(argparse.Namespace(evidence=manifest["evidence"]))
                        self.assertFalse((root / "evidence/run-started.json").exists())
                        process.assert_not_called()

    def test_installed_mode_requires_persistent_case_and_cannot_mix_source_projection(self):
        for args in (argparse.Namespace(installed_plugin="p@m"),
                     argparse.Namespace(installed_plugin="p@m", native_package_hooks=True)):
            with self.assertRaises(ValueError):
                entry.prepare(args)

    def test_invalid_installed_identity_fails_before_native_probes_or_root_creation(self):
        case = entry.load_persistent_case(SCRIPT.parents[1] / "product/cases/coordination-v3.3.json")
        for plugin_id in ("invalid/name@market", "yiyuan-accord-codex@yiyuan-accord"):
            with self.subTest(plugin_id=plugin_id), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp).resolve()
                package = root / "source-package"
                shutil.copytree(SCRIPT.parents[1] / "plugins/yiyuan-accord-codex", package)
                (root / "home").mkdir()
                args = argparse.Namespace(package=str(package), evidence=str(root / "evidence"),
                    workspace=str(root / "work"), codex=PYTHON, node=PYTHON,
                    model="unused", reasoning="medium", timeout=30, turn_timeout=10,
                    recovery_timeout=2, windows_sandbox="elevated", installed_plugin=plugin_id)
                before = entry._package_hashes(package)
                with patch.dict(os.environ, {"CODEX_HOME": str(root / "home")}), \
                        patch.object(entry.subprocess, "run", side_effect=AssertionError("unexpected native probe")) as process:
                    with self.assertRaisesRegex(ValueError, "installed plugin|installed cache root"):
                        entry.prepare(args, persistent_case=case)
                    process.assert_not_called()
                self.assertFalse((root / "evidence").exists())
                self.assertFalse((root / "work").exists())
                self.assertEqual(entry._package_hashes(package), before)
                self.assertEqual(list((root / "home").iterdir()), [])

    def test_installed_stage_retains_before_and_after_even_for_last_or_failed_turn(self):
        for changed, exit_code in ((False, 0), (True, 0), (True, 1)):
            with self.subTest(changed=changed, exit=exit_code), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp).resolve()
                with patch.dict(os.environ, {"CODEX_HOME": str(root / "home")}):
                    manifest = self.prepared_persistent(root, self.scoped_case(root), installed=True)
                    evidence = Path(manifest["evidence"])
                    rollout = evidence / "fake-rollout.jsonl"
                    rollout.write_text('{}\n')
                    process = Mock(returncode=exit_code)
                    process.poll.return_value = exit_code
                    def spawn(_command, **kwargs):
                        kwargs['stdout'].write(b'{}\n')
                        kwargs['stderr'].write(b'Sent prompt with event ID: 11111111-1111-1111-1111-111111111111\n')
                        (evidence / 'last-message-1.txt').write_text('done')
                        if changed:
                            (Path(manifest['package']) / 'NOTICE').write_text('changed during turn')
                        return process
                    receipt = {'valid': True, 'threadId': 'native-thread', 'terminal': 'completed'}
                    with patch.object(entry, '_native_inventory', return_value=json.loads(self.installed_listing().stdout)), \
                            patch.object(entry.subprocess, 'Popen', side_effect=spawn), \
                            patch.object(entry.subprocess, 'CREATE_NO_WINDOW', 0, create=True), \
                            patch.object(entry, 'WindowsJob') as job, \
                            patch.object(entry, 'persistent_cli_turn_receipt', return_value=receipt), \
                            patch.object(entry, '_session_configuration', return_value={'threadId':'native-thread','cwd':manifest['workspace'],'rolloutPath':str(rollout)}), \
                            patch.object(entry, '_ordinary_rollout', return_value=rollout), \
                            patch.object(entry, 'native_entry_observation', return_value={'valid':True}):
                        job.return_value.sample.return_value = {'activeProcesses':0}
                        observed = entry._run_persistent_stage(manifest, 0, None, dict(os.environ), time.monotonic()+30)
                    self.assertEqual(observed['installedBefore'], manifest['installedPlugin'])
                    self.assertEqual(observed['installedPackageStable'], not changed)
                    self.assertEqual(observed['valid'], not changed and exit_code == 0)
                    self.assertIsNone(observed['nativeTurnConditions']['goalModeActive'])
                    if changed:
                        self.assertIn('error', observed['installedAfter'])
                    else:
                        self.assertEqual(observed['installedAfter'], manifest['installedPlugin'])

    def test_installed_retained_inspection_requires_linked_complete_native_receipts(self):
        for mutation in (None, 'missing', 'extra', 'swapped', 'live-process', 'auth-override', 'config-change'):
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp).resolve()
                with patch.dict(os.environ, {'CODEX_HOME':str(root/'home')}):
                    manifest = self.prepared_persistent(root, installed=True)
                binding = manifest['installedPlugin']
                stages = [{'stage':1, 'installedBefore':binding, 'installedAfter':binding, 'entryObservation':{'valid':True}}]
                command_root = root/'evidence/installed-inventory/commands'
                for label in ('prepare','run-preflight','stage-1-before','stage-1-after'):
                    path = command_root/label
                    path.mkdir(parents=True)
                    entry.save(path/'record.json', {'arguments':['plugin','list','--marketplace','yiyuan-accord','--json'],
                        'exitCode':0,'forced':False,'failure':None,'controller':'windows-job-object','after':{'activeProcesses':0}})
                    entry.save(path/'stdout.json', json.loads(self.installed_listing().stdout))
                    entry.save(path/'shared-config.json', {'unchanged':True,'before':{'state':'observed','sha256':'same'},'after':{'state':'observed','sha256':'same'}})
                path = command_root/'stage-1-after'
                if mutation == 'missing': (path/'record.json').unlink()
                elif mutation == 'extra': (command_root/'unbound').mkdir()
                elif mutation == 'swapped': entry.save(path/'stdout.json', json.loads(self.installed_listing(version='other').stdout))
                elif mutation == 'live-process':
                    record = json.loads((path/'record.json').read_text()); record['after']['activeProcesses']=1; entry.save(path/'record.json',record)
                elif mutation == 'auth-override':
                    record = json.loads((path/'record.json').read_text()); record['arguments']=['-c','cli_auth_credentials_store="file"']+record['arguments']; entry.save(path/'record.json',record)
                elif mutation == 'config-change':
                    config = json.loads((path/'shared-config.json').read_text()); config['after']['sha256']='changed'; entry.save(path/'shared-config.json',config)
                self.assertEqual(entry._installed_evidence_valid(manifest, {'stages':stages}), mutation is None)

    def scoped_case(self, root):
        case = {
            "schema": "yiyuan-accord-scoped-task-case/v1",
            "purpose": "Create one structurally checked local report.",
            "inputs": {"source.json": {"candidate": "abc"}},
            "allowedPaths": ["report.json"], "deliverables": ["report.json"],
            "limits": {"usageCaps": {"totalTokens": 10000, "outputTokens": 1000},
                       "usageScope": "native cumulative thread counters"},
            "stages": [{"id": "report", "prompt": "Create report.json from source.json.",
                        "files": {
                            "source.json": {"state": "preserved", "from": "input"},
                            "report.json": {"state": "required", "format": "json",
                                            "jsonType": "object", "requiredKeys": ["candidate"]}},
                        "semanticReview": "Independently verify the report meaning."}],
        }
        path = root / "scoped-case.json"
        path.write_text(json.dumps(case), encoding="utf-8")
        return path

    def test_persistent_retention_keeps_business_inspection_json_separate_from_metadata(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            case_path = self.scoped_case(root)
            case = json.loads(case_path.read_text(encoding="utf-8"))
            case["allowedPaths"].append("inspection.json")
            case["deliverables"].append("inspection.json")
            case["stages"][0]["files"]["inspection.json"] = {
                "state": "required", "format": "json", "jsonType": "object",
                "requiredKeys": ["business"]}
            case_path.write_text(json.dumps(case), encoding="utf-8")
            manifest = self.prepared_persistent(root, case_path)
            business = b'{"business":"original output"}'

            def execute(prepared, *_):
                workspace = Path(prepared["workspace"])
                (workspace / "report.json").write_text('{"candidate":"abc"}', encoding="utf-8")
                (workspace / "inspection.json").write_bytes(business)
                return {"valid": True, "threadId": "native-thread"}

            with patch.object(entry, "_run_persistent_stage", side_effect=execute):
                result = entry.run_persistent(argparse.Namespace(evidence=manifest["evidence"]))
            self.assertTrue(result["caseComplete"])
            retained = Path(manifest["evidence"]) / "stage-1"
            business_copy = (retained / "files/inspection.json" if manifest.get("retainedLayout") == "stage-files-v1"
                             else retained / "inspection.json")
            self.assertEqual(business_copy.read_bytes(), business)
            self.assertEqual(manifest.get("retainedLayout"), "stage-files-v1")
            metadata = json.loads((retained / "inspection.json").read_text(encoding="utf-8"))
            self.assertEqual(metadata["files"]["inspection.json"]["sha256"], hashlib.sha256(business).hexdigest())
            # Simulate the old flat writer overwriting this business copy. It
            # must remain a missing/conflicting original, never be reconstructed.
            for name in metadata["files"]:
                copy = retained / "files" / name
                if name == "inspection.json":
                    copy.unlink()
                else:
                    copy.replace(retained / name)
            (retained / "files").rmdir()
            manifest.pop("retainedLayout")
            manifest.pop("stageIds")
            entry.save(Path(manifest["evidence"]) / "manifest.json", manifest)
            checked = entry.inspect(manifest["evidence"], retained=True)
            self.assertEqual(checked["retainedStages"][0]["state"], "mismatch")
            self.assertIn("legacy-metadata-name-conflict", checked["retainedStages"][0]["errors"])
            self.assertEqual(checked["recordedExecution"], result)

    def test_persistent_retention_marks_changed_source_copy_unknown(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            manifest = self.prepared_persistent(root, self.scoped_case(root))
            observer = entry.coordination_observer()
            original_inspect = observer.inspect_stage

            def execute(prepared, *_):
                (Path(prepared["workspace"]) / "report.json").write_text(
                    '{"candidate":"observed"}', encoding="utf-8")
                return {"valid": True, "threadId": "native-thread"}

            def change_after_inspection(*args, **kwargs):
                result = original_inspect(*args, **kwargs)
                (Path(manifest["workspace"]) / "report.json").write_text(
                    '{"candidate":"changed-after-observation"}', encoding="utf-8")
                return result

            with patch.object(entry, "_run_persistent_stage", side_effect=execute), \
                    patch.object(observer, "inspect_stage", side_effect=change_after_inspection):
                result = entry.run_persistent(argparse.Namespace(evidence=manifest["evidence"]))
            self.assertFalse(result["caseComplete"])
            observed = result["stages"][0]["fileObservation"]
            self.assertEqual(observed["decision"], "unknown")
            self.assertIn("workspace content changed before retention", observed["observationErrors"])
            self.assertFalse((Path(manifest["evidence"]) / "stage-1/files/report.json").exists())

    def test_retained_inspection_after_workspace_cleanup_keeps_failed_execution_and_default_gate(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            manifest = self.prepared_persistent(root)
            evidence = Path(manifest["evidence"])
            native = {"valid": True, "threadId": "native-thread", "remainingOwnedProcesses": 0}
            observer = entry.coordination_observer()
            with patch.object(entry, "_run_persistent_stage", return_value=native), \
                    patch.object(observer, "inspect_stage", side_effect=ValueError("offline business failure")):
                with self.assertRaisesRegex(ValueError, "offline business failure"):
                    entry.run_persistent(argparse.Namespace(evidence=manifest["evidence"]))
            frozen = {path.relative_to(evidence): path.read_bytes()
                      for path in evidence.rglob("*") if path.is_file()}
            shutil.rmtree(manifest["workspace"])
            with self.assertRaises((OSError, ValueError)):
                entry.inspect(evidence)
            with patch.object(entry, "_run_persistent_stage") as native_call:
                with self.assertRaises((OSError, ValueError)):
                    entry.run_persistent(argparse.Namespace(evidence=manifest["evidence"]))
                native_call.assert_not_called()
            checked = entry.inspect(evidence, retained=True)
            self.assertEqual(checked["inspectionMode"], "retained-only")
            self.assertEqual(checked["recordedExecution"], json.loads(frozen[Path("result.json")]))
            self.assertFalse(checked["recordedExecution"]["caseComplete"])
            self.assertEqual(checked["recordedExecution"]["executionFailure"]["phase"], "file-inspection")
            self.assertEqual(checked["currentFileObservation"]["decision"], "unknown")
            self.assertEqual({path.relative_to(evidence): path.read_bytes()
                              for path in evidence.rglob("*") if path.is_file()}, frozen)

    def retained_scoped_fixture(self, root):
        manifest = self.prepared_persistent(root, self.scoped_case(root))

        def execute(prepared, *_):
            (Path(prepared["workspace"]) / "report.json").write_text(
                '{"candidate":"abc"}', encoding="utf-8")
            return {"valid": True, "threadId": "native-thread"}

        with patch.object(entry, "_run_persistent_stage", side_effect=execute):
            result = entry.run_persistent(argparse.Namespace(evidence=manifest["evidence"]))
        self.assertTrue(result["caseComplete"])
        return manifest, result

    def test_retained_inspection_verifies_current_and_legacy_flat_stage_copies(self):
        for legacy in (False, True):
            with self.subTest(legacy=legacy), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp).resolve()
                manifest, result = self.retained_scoped_fixture(root)
                evidence = Path(manifest["evidence"])
                stage = evidence / "stage-1"
                if legacy:
                    for name in ("source.json", "report.json"):
                        shutil.move(str(stage / "files" / name), str(stage / name))
                    (stage / "files").rmdir()
                    manifest.pop("retainedLayout", None)
                    entry.save(evidence / "manifest.json", manifest)
                shutil.rmtree(manifest["workspace"])
                before = {path.relative_to(evidence): path.read_bytes()
                          for path in evidence.rglob("*") if path.is_file()}
                checked = entry.inspect(evidence, retained=True)
                self.assertEqual(checked["recordedExecution"], result)
                self.assertEqual(checked["retainedStages"][0]["state"], "verified")
                self.assertTrue(all(checked["retainedStages"][0]["files"].values()))
                self.assertEqual(checked["currentFileObservation"]["decision"], "unknown")
                self.assertEqual({path.relative_to(evidence): path.read_bytes()
                                  for path in evidence.rglob("*") if path.is_file()}, before)

    def test_retained_inspection_reports_changed_and_missing_business_copies(self):
        for mutation, state in (("changed", "mismatch"), ("missing", "incomplete")):
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp).resolve()
                manifest, result = self.retained_scoped_fixture(root)
                retained = Path(manifest["evidence"]) / "stage-1/files/report.json"
                if mutation == "changed":
                    retained.write_text('{"candidate":"altered"}', encoding="utf-8")
                else:
                    retained.unlink()
                shutil.rmtree(manifest["workspace"])
                checked = entry.inspect(manifest["evidence"], retained=True)
                self.assertEqual(checked["recordedExecution"], result)
                self.assertEqual(checked["retainedStages"][0]["state"], state)
                self.assertFalse(checked["retainedStages"][0]["files"]["report.json"])

    def test_retained_inspection_binds_separate_goal_observation_after_cleanup(self):
        for mutation, expected in ((None, "verified"), ("changed", "mismatch"),
                                   ("missing", "incomplete"), ("foreign-thread", "mismatch"),
                                   ("unlinked", "mismatch")):
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp).resolve()
                manifest = self.prepared_persistent(root, self.scoped_case(root))
                evidence = Path(manifest["evidence"])
                native = {"valid": True, "threadId": "native-thread", "terminal": "completed",
                          "remainingOwnedProcesses": 0}
                goal = {"state": "observed", "threadId": "native-thread", "stage": 1,
                        "goalPresent": False, "goalModeActive": False, "goalStatus": None}

                def execute(prepared, *_):
                    (Path(prepared["workspace"]) / "report.json").write_text(
                        '{"candidate":"abc"}', encoding="utf-8")
                    return native

                with patch.object(entry, "_run_persistent_stage", side_effect=execute), \
                        patch.object(entry, "_native_goal_readback", return_value=goal):
                    result = entry.run_persistent(argparse.Namespace(
                        evidence=manifest["evidence"], observe_native_goal=True))
                self.assertTrue(result["caseComplete"])
                self.assertEqual(json.loads((evidence / "native-receipt-1.json").read_text()), native)
                self.assertEqual(json.loads((evidence / "native-goal-1.json").read_text()), goal)
                goal_path = evidence / "native-goal-1.json"
                if mutation == "changed":
                    changed = {**goal, "goalStatus": "active"}
                    entry.save(goal_path, changed)
                elif mutation == "missing":
                    goal_path.unlink()
                elif mutation == "foreign-thread":
                    changed = {**goal, "threadId": "foreign"}
                    entry.save(goal_path, changed)
                    result["stages"][0]["nativeGoalObservation"] = changed
                    entry.save(evidence / "result.json", result)
                elif mutation == "unlinked":
                    result["stages"][0].pop("nativeGoalObservation")
                    entry.save(evidence / "result.json", result)
                shutil.rmtree(manifest["workspace"])
                checked = entry.inspect(evidence, retained=True)
                self.assertEqual(checked["retainedStages"][0]["state"], expected)
                if mutation is None:
                    self.assertEqual(checked["recordedExecution"], result)
                else:
                    reason = ("unavailable" if mutation == "missing" else
                              "unlinked" if mutation == "unlinked" else "mismatch")
                    self.assertIn("native-goal-" + reason,
                                  checked["retainedStages"][0]["errors"])

    def test_retained_inspection_rejects_contradictory_stage_records(self):
        for mutation in ("metadata", "history", "native-receipt"):
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp).resolve()
                manifest, result = self.retained_scoped_fixture(root)
                evidence = Path(manifest["evidence"])
                if mutation == "metadata":
                    path = evidence / "stage-1/inspection.json"
                    data = json.loads(path.read_text(encoding="utf-8"))
                    data["files"]["report.json"]["sha256"] = "0" * 64
                elif mutation == "history":
                    path = evidence / "history.json"
                    data = json.loads(path.read_text(encoding="utf-8"))
                    data["report"]["report.json"]["sha256"] = "0" * 64
                else:
                    path = evidence / "native-receipt-1.json"
                    data = json.loads(path.read_text(encoding="utf-8"))
                    data["threadId"] = "foreign-thread"
                entry.save(path, data)
                shutil.rmtree(manifest["workspace"])
                checked = entry.inspect(evidence, retained=True)
                self.assertEqual(checked["recordedExecution"], result)
                self.assertEqual(checked["retainedStages"][0]["state"], "mismatch")

    def test_retained_inspection_rejects_self_consistent_stage_rename_against_manifest(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            manifest, _ = self.retained_scoped_fixture(root)
            evidence = Path(manifest["evidence"])
            self.assertEqual(manifest["stageIds"], ["report"])
            result_path = evidence / "result.json"
            result = json.loads(result_path.read_text(encoding="utf-8"))
            result["stages"][0]["fileObservation"]["stage"] = "renamed"
            entry.save(result_path, result)
            inspection_path = evidence / "stage-1/inspection.json"
            inspection = json.loads(inspection_path.read_text(encoding="utf-8"))
            inspection["stage"] = "renamed"
            entry.save(inspection_path, inspection)
            history_path = evidence / "history.json"
            history = json.loads(history_path.read_text(encoding="utf-8"))
            history["renamed"] = history.pop("report")
            entry.save(history_path, history)
            shutil.rmtree(manifest["workspace"])
            checked = entry.inspect(evidence, retained=True)
            self.assertEqual(checked["recordedExecution"], result)
            self.assertEqual(checked["retainedStages"][0]["state"], "mismatch")

    def test_retained_inspection_rejects_evidence_content_or_directory_change_during_read(self):
        for mutation in ("content", "directory"):
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp).resolve()
                manifest, _ = self.retained_scoped_fixture(root)
                evidence = Path(manifest["evidence"])
                shutil.rmtree(manifest["workspace"])
                original_read = entry.read_regular
                changed = False

                def mutate_after_read(path):
                    nonlocal changed
                    raw = original_read(path)
                    if not changed and Path(path) == evidence / "stage-1/files/report.json":
                        changed = True
                        if mutation == "content":
                            (evidence / "stage-1/inspection.json").write_text("{}", encoding="utf-8")
                        else:
                            (evidence / "stage-1/files/late.txt").write_text("late", encoding="utf-8")
                    return raw

                with patch.object(entry, "read_regular", side_effect=mutate_after_read):
                    with self.assertRaises(ValueError):
                        entry.inspect(evidence, retained=True)
                self.assertTrue(changed)

    def test_retained_inspection_rejects_unsafe_business_leaf_names(self):
        for name in ("../outside.txt", str(Path("C:/outside.txt"))):
            with self.subTest(name=name), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp).resolve()
                manifest, result = self.retained_scoped_fixture(root)
                evidence = Path(manifest["evidence"])
                inspection = evidence / "stage-1/inspection.json"
                data = json.loads(inspection.read_text(encoding="utf-8"))
                data["files"][name] = {"sha256": "0" * 64, "mtimeNs": 0}
                entry.save(inspection, data)
                shutil.rmtree(manifest["workspace"])
                checked = entry.inspect(evidence, retained=True)
                self.assertEqual(checked["recordedExecution"], result)
                self.assertNotEqual(checked["retainedStages"][0]["state"], "verified")

    def test_retained_inspection_keeps_partial_file_retention_unknown(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            manifest = self.prepared_persistent(root, self.scoped_case(root))

            def execute(prepared, *_):
                (Path(prepared["workspace"]) / "report.json").write_text(
                    '{"candidate":"abc"}', encoding="utf-8")
                return {"valid": True, "threadId": "native-thread"}

            regular = entry.read_regular
            def fail_retention(path):
                if Path(path) == Path(manifest["workspace"]) / "report.json":
                    raise OSError("fixture copy failure")
                return regular(path)

            with patch.object(entry, "_run_persistent_stage", side_effect=execute), \
                    patch.object(entry, "read_regular", side_effect=fail_retention):
                result = entry.run_persistent(argparse.Namespace(evidence=manifest["evidence"]))
            self.assertFalse(result["caseComplete"])
            self.assertEqual(result["stages"][0]["fileObservation"]["decision"], "unknown")
            shutil.rmtree(manifest["workspace"])
            checked = entry.inspect(manifest["evidence"], retained=True)
            self.assertEqual(checked["recordedExecution"], result)
            self.assertEqual(checked["retainedStages"][0]["state"], "incomplete")

    def test_scoped_case_reuses_persistent_transport_and_inspect_is_read_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            manifest = self.prepared_persistent(root, self.scoped_case(root))
            self.assertEqual(manifest["caseSchema"], "yiyuan-accord-scoped-task-case/v1")
            self.assertEqual(manifest["casePurpose"], "Create one structurally checked local report.")
            self.assertEqual(len(manifest["prompts"]), 1)
            self.assertIn("scopedTaskObserver", manifest["sourceHashes"])
            def execute(manifest, *_):
                (Path(manifest["workspace"]) / "report.json").write_text(
                    json.dumps({"candidate": "abc"}), encoding="utf-8")
                return {"valid": True, "threadId": "native-thread"}
            with patch.object(entry, "_run_persistent_stage", side_effect=execute) as run_stage:
                result = entry.run_persistent(argparse.Namespace(evidence=manifest["evidence"]))
            self.assertTrue(result["caseComplete"])
            before = {path: path.read_bytes() for path in Path(manifest["evidence"]).rglob("*") if path.is_file()}
            with patch.object(entry, "_run_persistent_stage") as forbidden:
                inspected = entry.inspect(manifest["evidence"])
            self.assertEqual(inspected["currentFileObservation"]["decision"], "pass")
            forbidden.assert_not_called()
            self.assertEqual(before, {path: path.read_bytes() for path in Path(manifest["evidence"]).rglob("*") if path.is_file()})
            result_path = Path(manifest["evidence"]) / "result.json"
            substituted = json.loads(result_path.read_text(encoding="utf-8"))
            substituted["episode"] = "foreign-episode"
            result_path.write_text(json.dumps(substituted), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "result binding"):
                entry.inspect(manifest["evidence"])

    def test_persistent_cli_preparation_uses_normal_config_and_exact_native_resume(self):
        with tempfile.TemporaryDirectory() as tmp:
            manifest = self.prepared_persistent(Path(tmp).resolve())
            initial = manifest["initialCommand"]
            resumed = entry.build_command(manifest, stage=1, thread_id="native-thread")
            for command in (initial, resumed):
                self.assertNotIn("--ephemeral", command)
                self.assertNotIn("--ignore-user-config", command)
                self.assertEqual(command[command.index("-m") + 1], "explicit-offline-model")
                self.assertIn('sandbox_mode="workspace-write"', command)
                self.assertIn('model_reasoning_effort="high"', command)
                self.assertEqual(command[command.index("-C") + 1], manifest["workspace"])
                self.assertEqual(command[command.index("--add-dir") + 1], str(Path(manifest["evidence"]) / "state"))
            self.assertLess(resumed.index("-C"), resumed.index("resume"))
            self.assertLess(resumed.index("--add-dir"), resumed.index("resume"))
            self.assertEqual(resumed[-2:], ["native-thread", "-"])
            self.assertEqual(manifest["timeoutSeconds"], 600)
            self.assertEqual(manifest["turnTimeoutSeconds"], 180)
            self.assertEqual(manifest["recoveryTimeoutSeconds"], 20)
            self.assertEqual(manifest["limits"]["usageCaps"], {
                "totalTokens": 2500000, "uncachedInputTokens": 200000, "outputTokens": 14000})
            self.assertEqual(len(manifest["prompts"]), 5)
            self.assertEqual(json.loads((Path(manifest["workspace"]) / "source.json").read_text(encoding="utf-8"))["venue"], "A厅")

    def test_native_package_hooks_preserve_all_registrations_and_isolate_exec_before_resume(self):
        with tempfile.TemporaryDirectory() as tmp:
            manifest = self.prepared_persistent(Path(tmp).resolve(), native_hooks=True)
            projection = manifest["nativeHookProjection"]
            definition = json.loads((Path(manifest["package"]) / "hooks/hooks.json").read_text(encoding="utf-8"))
            expected = json.loads(json.dumps(definition["hooks"]))
            for registrations in expected.values():
                for registration in registrations:
                    for handler in registration["hooks"]:
                        handler["command"] = ("& " if projection["shellKind"] == "powershell" else "") + '"' + Path(manifest["node"]).as_posix() + '"' + handler["command"][len("node"):].replace("${PLUGIN_ROOT}", Path(manifest["package"]).as_posix())
            self.assertEqual(projection["definition"], definition)
            self.assertEqual(projection["hooks"], expected)
            self.assertEqual(set(expected), {
                "SessionStart", "UserPromptSubmit", "SubagentStart", "SessionEnd", "Interrupt"})
            self.assertNotIn("Stop", expected)
            self.assertEqual({event: sum(len(row["hooks"]) for row in rows)
                              for event, rows in expected.items()}, {
                "SessionStart": 2, "UserPromptSubmit": 1, "SubagentStart": 1,
                "SessionEnd": 1, "Interrupt": 1})
            self.assertEqual(len(expected["SessionStart"]), 2)
            self.assertEqual(sum(len(r["hooks"]) for rows in expected.values() for r in rows), 6)
            self.assertEqual(len(expected["SubagentStart"]), 1)
            child = expected["SubagentStart"][0]["hooks"]
            self.assertEqual(len(child), 1)
            self.assertEqual(child[0]["additionalContextLimit"], 4000)
            self.assertIn("runtime/accord-hook.cjs", child[0]["command"])
            self.assertEqual(projection["sourceFiles"], ["runtime/accord-hook.cjs", "runtime/task-checkpoint.cjs"])
            self.assertEqual(projection["packageFiles"], {
                p.relative_to(Path(manifest["package"])).as_posix(): entry.digest(p)
                for p in Path(manifest["package"]).rglob("*") if p.is_file()})
            self.assertTrue(projection["sourceConfigurationOnly"])
            self.assertFalse(projection["marketplaceInstalled"])
            self.assertFalse((Path(manifest["evidence"]) / "hooks").exists())
            for command in (manifest["initialCommand"], entry.build_command(manifest, stage=1, thread_id="native-thread")):
                self.assertNotIn("--ephemeral", command)
                self.assertEqual(command[2:8], ["--ignore-user-config", "--disable", "plugins", "--disable", "apps", "-C"]
                                 if "resume" in command else ["--ignore-user-config", "--disable", "plugins", "--disable", "apps", "--skip-git-repo-check"])
                if "resume" in command:
                    self.assertLess(command.index("--ignore-user-config"), command.index("resume"))
                configuration = next(value for value in command if value.startswith("hooks="))
                self.assertEqual(configuration, projection["configuration"])
                if entry.tomllib is not None:
                    self.assertEqual(entry.tomllib.loads(configuration)["hooks"], expected)
                self.assertNotIn(" hook --evidence", configuration)
                self.assertEqual(command[command.index("-m") + 1], manifest["model"])
                self.assertIn('model_reasoning_effort="high"', command)
            with self.assertRaisesRegex(ValueError, "cannot use the checkpoint wrapper"):
                entry.hook(argparse.Namespace(evidence=manifest["evidence"], event="Stop"))

    def test_complete_plugin_requires_native_loading_not_hook_projection(self):
        source = SCRIPT.parents[1] / "plugins/yiyuan-accord-codex"
        with self.assertRaisesRegex(ValueError, "non-hook component"):
            entry._native_hook_projection(source, shutil.which("node"))

    def test_hook_fixture_keeps_setup_out_of_projection_and_source_intact(self):
        source = SCRIPT.parents[1] / "plugins/yiyuan-accord-codex"
        before = entry._package_hashes(source)
        with tempfile.TemporaryDirectory() as tmp:
            package = Path(tmp).resolve() / "package"
            self.copy_hook_only_fixture(package)
            metadata = json.loads((package / ".codex-plugin/plugin.json").read_bytes())
            self.assertNotIn("extensions", metadata)
            self.assertFalse((package / ".mcp.json").exists())
            projection = entry._native_hook_projection(package, shutil.which("node"))
            self.assertTrue(projection["sourceConfigurationOnly"])
            self.assertFalse(projection["marketplaceInstalled"])
        self.assertEqual(entry._package_hashes(source), before)

    def test_native_projection_preserves_extra_fields_and_rejects_unsupported_surfaces(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            manifest = self.prepared_persistent(root, native_hooks=True)
            package = Path(manifest["package"])
            hooks_path = package / "hooks/hooks.json"
            definition = json.loads(hooks_path.read_text(encoding="utf-8"))
            definition["hooks"]["SessionStart"][0]["customRegistration"] = {"enabled": True, "labels": ["a", "b"]}
            definition["hooks"]["SessionStart"][0]["hooks"][0]["customHandler"] = "retained"
            entry.save(hooks_path, definition)
            projected = entry._native_hook_projection(package, manifest["node"])
            if entry.tomllib:
                self.assertEqual(entry.tomllib.loads(projected["configuration"])["hooks"], projected["hooks"])
            self.assertEqual(projected["hooks"]["SessionStart"][0]["customRegistration"], {"enabled": True, "labels": ["a", "b"]})
            for change in ("manifest-override", "setup-extension", "unknown-extension", "mcp",
                           "prompt-handler", "shell-command", "null-field", "unknown-event"):
                metadata_path = package / ".codex-plugin/plugin.json"
                original_metadata = metadata_path.read_bytes()
                altered = json.loads(json.dumps(definition))
                if change == "manifest-override":
                    metadata = json.loads(original_metadata)
                    metadata["hooks"] = "./other-hooks.json"
                    entry.save(metadata_path, metadata)
                elif change in ("setup-extension", "unknown-extension"):
                    metadata = json.loads(original_metadata)
                    metadata["extensions"] = ({"com.openai": {
                        "onboardingSkill": "./skills/manage-plugin-lifecycle/SKILL.md"}}
                        if change == "setup-extension" else {"unknown.vendor": {"enabled": True}})
                    entry.save(metadata_path, metadata)
                elif change == "mcp":
                    (package / ".mcp.json").write_text("{}", encoding="utf-8")
                elif change == "prompt-handler":
                    altered["hooks"]["Interrupt"][0]["hooks"][0]["type"] = "prompt"
                elif change == "shell-command":
                    altered["hooks"]["Interrupt"][0]["hooks"][0]["command"] += "; echo forged"
                elif change == "null-field":
                    altered["hooks"]["Interrupt"][0]["hooks"][0]["extra"] = None
                elif change == "unknown-event":
                    altered["hooks"]["Unknown"] = altered["hooks"]["Interrupt"]
                entry.save(hooks_path, altered)
                with self.subTest(change=change), self.assertRaises(ValueError):
                    entry._native_hook_projection(package, manifest["node"])
                metadata_path.write_bytes(original_metadata)
                (package / ".mcp.json").unlink(missing_ok=True)

    def test_native_package_drift_is_rejected_before_receipt_and_each_stage(self):
        for mutation in ("runtime", "skill", "add", "delete", "projection"):
            with tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp).resolve()
                manifest = self.prepared_persistent(root, native_hooks=True)
                package = Path(manifest["package"])
                if mutation == "runtime":
                    (package / "runtime/codex-context.cjs").write_text("// changed", encoding="utf-8")
                elif mutation == "skill":
                    (package / "skills/deliver-demand-driven-outcome/SKILL.md").write_text("changed", encoding="utf-8")
                elif mutation == "add":
                    (package / "new.txt").write_text("new", encoding="utf-8")
                elif mutation == "delete":
                    (package / "NOTICE").unlink()
                else:
                    manifest["nativeHookProjection"]["hooks"]["SessionStart"].pop()
                    entry.save(root / "evidence/manifest.json", manifest)
                with self.subTest(mutation=mutation), patch.object(entry.subprocess, "Popen") as process:
                    with self.assertRaisesRegex(ValueError, "prepared package"):
                        entry.run_persistent(argparse.Namespace(evidence=manifest["evidence"]))
                    self.assertFalse((root / "evidence/run-started.json").exists())
                    with self.assertRaisesRegex(ValueError, "prepared package"):
                        entry._run_persistent_stage(manifest, 1, "native-thread", {}, time.monotonic() + 1)
                    process.assert_not_called()

    def test_native_execution_env_keeps_codex_home_and_bound_node_first(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            manifest = self.prepared_persistent(root, self.scoped_case(root), native_hooks=True)
            shared = root / "shared"
            shared.mkdir()
            (shared / "config.toml").write_text("model = 'private-offline'\n", encoding="utf-8")
            (shared / "auth.json").write_text("must not read or copy", encoding="utf-8")
            def execute(manifest, stage, thread, env, *_):
                self.assertEqual(env["CODEX_HOME"], str(shared))
                self.assertEqual(env["PATH"].split(os.pathsep)[:2], [str(Path(manifest["hookShell"]).parent), str(Path(manifest["node"]).parent)])
                (Path(manifest["workspace"]) / "report.json").write_text('{"candidate":"abc"}', encoding="utf-8")
                return {"valid": True, "threadId": "native-thread"}
            ordinary_read = entry.read_regular
            def no_auth_read(path, *args, **kwargs):
                self.assertNotEqual(Path(path).name, "auth.json")
                return ordinary_read(path, *args, **kwargs)
            with patch.dict(os.environ, {"CODEX_HOME": str(shared), "PATH": "original-path"}), \
                    patch.object(entry, "_run_persistent_stage", side_effect=execute), \
                    patch.object(entry, "read_regular", side_effect=no_auth_read):
                result = entry.run_persistent(argparse.Namespace(evidence=manifest["evidence"]))
            self.assertTrue(result["caseComplete"])
            self.assertTrue(result["sharedConfigObservation"]["unchanged"])
            self.assertTrue(result["nativeHookProjection"]["sourceConfigurationOnly"])
            self.assertEqual((shared / "auth.json").read_text(), "must not read or copy")
            self.assertFalse(any(p.name == "auth.json" for p in (root / "evidence").rglob("*")))

    def test_native_runner_rechecks_package_between_completed_stages(self):
        with tempfile.TemporaryDirectory() as tmp:
            manifest = self.prepared_persistent(Path(tmp).resolve(), native_hooks=True)
            observer = Mock()
            observer.snapshot.return_value = {}
            observer.inspect_stage.return_value = {"files": {}, "decision": "pass"}
            def execute(*_):
                (Path(manifest["package"]) / "runtime/codex-context.cjs").write_text("// changed after first turn", encoding="utf-8")
                return {"valid": True, "threadId": "native-thread"}
            with patch.object(entry, "coordination_observer", return_value=observer), \
                    patch.object(entry, "_run_persistent_stage", side_effect=execute) as stage:
                with self.assertRaisesRegex(ValueError, "prepared package"):
                    entry.run_persistent(argparse.Namespace(evidence=manifest["evidence"]))
            self.assertEqual(stage.call_count, 1)
            saved = json.loads((Path(manifest["evidence"]) / "shared-config.json").read_text(encoding="utf-8"))
            self.assertIn("after", saved)
            partial = json.loads((Path(manifest["evidence"]) / "result.json").read_text(encoding="utf-8"))
            self.assertFalse(partial["caseComplete"])
            self.assertEqual(partial["completedStages"], 1)
            self.assertEqual(partial["threadId"], "native-thread")
            self.assertEqual(partial["executionFailure"]["stage"], 2)
            self.assertEqual(partial["executionFailure"]["phase"], "preflight")

    def test_persistent_preparation_preserves_multiline_prompt_bytes(self):
        for prompt in ("$retro\n审查当前工序。\n", "第一行\r\n第二行\r\n", "甲\n乙\r\n丙\n"):
            with self.subTest(prompt=repr(prompt)), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp).resolve()
                case = json.loads((SCRIPT.parents[1] / "product/cases/coordination-v3.3.json").read_text(encoding="utf-8"))
                case["stages"][0]["prompt"] = prompt
                case_path = root / "multiline-case.json"
                case_path.write_bytes(json.dumps(case, ensure_ascii=False).encode("utf-8"))
                manifest = self.prepared_persistent(root, case_path=case_path, native_hooks=True)
                child = manifest['nativeHookProjection']['hooks']['SubagentStart'][0]['hooks'][0]
                self.assertEqual(child['additionalContextLimit'],4000)
                self.assertIn('accord-hook.cjs',child['command'])
                prepared = Path(manifest["evidence"]) / "prompt-1.txt"
                self.assertEqual(prepared.read_bytes(), prompt.encode("utf-8"))
                with patch.object(entry.subprocess, "Popen") as forbidden:
                    raw, _, _ = entry._verify_native_stage(manifest, 0, None)
                    self.assertEqual(raw, prompt.encode("utf-8"))
                    # Updating only the prepared hash cannot legitimize a newline change.
                    prepared.write_bytes(b"\n" + raw)
                    manifest["promptSha256s"][0] = entry.digest(prepared)
                    with self.assertRaisesRegex(ValueError, "stage prompt changed"):
                        entry._verify_native_stage(manifest, 0, None)
                    forbidden.assert_not_called()

    def test_native_stage_rejects_prompt_case_command_and_observed_thread_substitutions(self):
        for mutation in ("prompt-file", "prompt-and-hash", "manifest-prompt", "model", "template", "thread", "duplicate-source"):
            with tempfile.TemporaryDirectory() as tmp:
                manifest = self.prepared_persistent(Path(tmp).resolve(), native_hooks=True)
                evidence = Path(manifest["evidence"])
                source = {"type": "thread.started", "thread_id": "observed-source"}
                (evidence / "stdout-1.jsonl").write_text(json.dumps(source) + "\n", encoding="utf-8")
                raw, command, installed = entry._verify_native_stage(manifest, 1, "observed-source")
                self.assertIsNone(installed)
                self.assertEqual(raw, manifest["prompts"][1].encode("utf-8"))
                self.assertEqual(command[-2:], ["observed-source", "-"])
                thread_id = "observed-source"
                if mutation in ("prompt-file", "prompt-and-hash"):
                    (evidence / "prompt-2.txt").write_text("substituted prompt", encoding="utf-8")
                    if mutation == "prompt-and-hash":
                        manifest["promptSha256s"][1] = entry.digest(evidence / "prompt-2.txt")
                elif mutation == "manifest-prompt":
                    manifest["prompts"][1] = "substituted prompt"
                elif mutation == "model":
                    manifest["model"] = "different-model"
                elif mutation == "template":
                    manifest["stageCommandTemplates"][1][-2] = "hardcoded-other-thread"
                elif mutation == "thread":
                    thread_id = "unobserved-thread"
                else:
                    (evidence / "stdout-1.jsonl").write_text((json.dumps(source) + "\n") * 2, encoding="utf-8")
                with self.subTest(mutation=mutation), patch.object(entry.subprocess, "Popen") as forbidden:
                    with self.assertRaises(ValueError):
                        entry._run_persistent_stage(manifest, 1, thread_id, {}, time.monotonic() + 1)
                    forbidden.assert_not_called()

    def test_native_runner_rechecks_next_prompt_after_first_completed_stage(self):
        with tempfile.TemporaryDirectory() as tmp:
            manifest = self.prepared_persistent(Path(tmp).resolve(), native_hooks=True)
            observer = Mock()
            observer.snapshot.return_value = entry.coordination_observer().snapshot(
                manifest["workspace"], json.loads(Path(manifest["case"]).read_text(encoding="utf-8"))["inputs"])
            observer.inspect_stage.return_value = {"stage": "plan", "files": {}, "decision": "pass"}
            def execute(*_):
                evidence = Path(manifest["evidence"])
                (evidence / "stdout-1.jsonl").write_text('{"type":"thread.started","thread_id":"observed-source"}\n', encoding="utf-8")
                (evidence / "prompt-2.txt").write_text("drift after first turn", encoding="utf-8")
                return {"valid": True, "threadId": "observed-source"}
            with patch.object(entry, "coordination_observer", return_value=observer), \
                    patch.object(entry, "_run_persistent_stage", side_effect=execute) as stage:
                with self.assertRaisesRegex(ValueError, "prepared stage prompt"):
                    entry.run_persistent(argparse.Namespace(evidence=manifest["evidence"]))
            self.assertEqual(stage.call_count, 1)
            partial = entry.inspect(manifest["evidence"])["recordedExecution"]
            self.assertFalse(partial["caseComplete"])
            self.assertEqual(partial["threadId"], "observed-source")
            self.assertEqual(partial["completedStages"], 1)
            self.assertEqual(partial["executionFailure"]["phase"], "preflight")

    def test_installed_first_stage_internal_preflight_failure_keeps_agent_undispatched(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            with patch.dict(os.environ, {"CODEX_HOME": str(root / "home")}):
                manifest = self.prepared_persistent(root, installed=True)
                (root / "home/config.toml").write_text("", encoding="utf-8")
                listing = json.loads(self.installed_listing().stdout)
                changed = json.loads(self.installed_listing(enabled=False).stdout)
                with patch.object(entry, "_native_inventory", side_effect=[listing, changed]) as inventory, \
                        patch.object(entry.subprocess, "Popen") as agent:
                    with self.assertRaisesRegex(ValueError, "native installed plugin"):
                        entry.run_persistent(argparse.Namespace(evidence=manifest["evidence"]))
                self.assertEqual(inventory.call_count, 2)
                agent.assert_not_called()
                evidence = Path(manifest["evidence"])
                partial = json.loads((evidence / "result.json").read_text(encoding="utf-8"))
                self.assertEqual(partial["executionFailure"], {
                    "stage": 1, "phase": "preflight", "reason": "execution-error"})
                self.assertFalse(partial["caseComplete"])
                self.assertEqual(partial["stages"], [])
                self.assertFalse((evidence / "native-receipt-1.json").exists())
                self.assertTrue(partial["sharedConfigObservation"]["unchanged"])
                with patch.object(entry, "_native_inventory", return_value=listing), \
                        patch.object(entry, "_run_persistent_stage") as replay:
                    with self.assertRaises(FileExistsError):
                        entry.run_persistent(argparse.Namespace(evidence=manifest["evidence"]))
                    replay.assert_not_called()

    def test_stage_internal_prompt_and_command_rechecks_remain_preflight(self):
        for mutation in ("prompt", "command"):
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory() as tmp:
                manifest = self.prepared_persistent(Path(tmp).resolve(), native_hooks=True)
                original_verify = entry._verify_native_stage
                original_command = entry.build_command
                command_calls = 0
                verification_calls = 0

                def verify(prepared, stage, thread_id, **deadline):
                    nonlocal verification_calls
                    verification_calls += 1
                    if mutation == "prompt" and verification_calls == 2:
                        prepared["prompts"][stage] = "drift after outer preflight"
                    return original_verify(prepared, stage, thread_id, **deadline)

                def command(*args, **kwargs):
                    nonlocal command_calls
                    command_calls += 1
                    built = original_command(*args, **kwargs)
                    return built + ["drift"] if mutation == "command" and command_calls == 4 else built

                with patch.object(entry, "_verify_native_stage", side_effect=verify if mutation == "prompt" else original_verify), \
                        patch.object(entry, "build_command", side_effect=command), \
                        patch.object(entry.subprocess, "Popen") as agent:
                    with self.assertRaisesRegex(ValueError, "prepared stage (prompt|command)"):
                        entry.run_persistent(argparse.Namespace(evidence=manifest["evidence"]))
                agent.assert_not_called()
                if mutation == "prompt":
                    self.assertEqual(verification_calls, 2)
                partial = json.loads((Path(manifest["evidence"]) / "result.json").read_text(encoding="utf-8"))
                self.assertEqual(partial["executionFailure"]["phase"], "preflight")
                self.assertFalse(partial["caseComplete"])

    def test_second_stage_internal_preflight_keeps_first_stage_history(self):
        with tempfile.TemporaryDirectory() as tmp:
            manifest = self.prepared_persistent(Path(tmp).resolve(), native_hooks=True)
            evidence = Path(manifest["evidence"])
            observer = Mock()
            observer.snapshot.return_value = entry.coordination_observer().snapshot(
                manifest["workspace"], json.loads(Path(manifest["case"]).read_text(encoding="utf-8"))["inputs"])
            observer.inspect_stage.return_value = {"stage": "plan", "files": {}, "decision": "pass"}
            original_stage = entry._run_persistent_stage
            original_verify = entry._verify_native_stage
            second_checks = 0

            def stage(prepared, index, *args):
                if index == 0:
                    (evidence / "stdout-1.jsonl").write_text(
                        '{"type":"thread.started","thread_id":"observed-source"}\n', encoding="utf-8")
                    return {"valid": True, "threadId": "observed-source"}
                return original_stage(prepared, index, *args)

            def verify(prepared, index, thread_id, **deadline):
                nonlocal second_checks
                if index == 1:
                    second_checks += 1
                    if second_checks == 2:
                        prepared["prompts"][1] = "drift inside second stage"
                return original_verify(prepared, index, thread_id, **deadline)

            with patch.object(entry, "coordination_observer", return_value=observer), \
                    patch.object(entry, "_run_persistent_stage", side_effect=stage), \
                    patch.object(entry, "_verify_native_stage", side_effect=verify), \
                    patch.object(entry.subprocess, "Popen") as agent:
                with self.assertRaisesRegex(ValueError, "prepared stage prompt"):
                    entry.run_persistent(argparse.Namespace(evidence=manifest["evidence"]))
            agent.assert_not_called()
            partial = json.loads((evidence / "result.json").read_text(encoding="utf-8"))
            self.assertEqual(partial["executionFailure"], {
                "stage": 2, "phase": "preflight", "reason": "execution-error"})
            self.assertEqual(partial["completedStages"], 1)
            self.assertEqual(partial["threadId"], "observed-source")
            self.assertEqual(partial["stages"][0]["threadId"], "observed-source")
            self.assertEqual(json.loads((evidence / "history.json").read_text(encoding="utf-8")), {"plan": {}})
            self.assertTrue((evidence / "native-receipt-1.json").exists())
            self.assertFalse((evidence / "native-receipt-2.json").exists())
            self.assertFalse(partial["caseComplete"])

    def test_stage_resource_creation_failure_keeps_native_execution_phase(self):
        with tempfile.TemporaryDirectory() as tmp:
            manifest = self.prepared_persistent(Path(tmp).resolve())
            with patch.object(entry, "WindowsJob", side_effect=KeyboardInterrupt()), \
                    patch.object(entry.subprocess, "Popen") as agent:
                with self.assertRaises(KeyboardInterrupt):
                    entry.run_persistent(argparse.Namespace(evidence=manifest["evidence"]))
            agent.assert_not_called()
            partial = json.loads((Path(manifest["evidence"]) / "result.json").read_text(encoding="utf-8"))
            self.assertEqual(partial["executionFailure"], {
                "stage": 1, "phase": "native-execution", "reason": "interrupted"})
            self.assertFalse(partial["caseComplete"])

    def test_internal_preflight_interrupt_keeps_interrupted_reason(self):
        with tempfile.TemporaryDirectory() as tmp:
            manifest = self.prepared_persistent(Path(tmp).resolve(), native_hooks=True)
            original = entry._verify_native_stage
            checks = 0

            def verify(*args, **deadline):
                nonlocal checks
                checks += 1
                if checks == 2:
                    raise KeyboardInterrupt()
                return original(*args, **deadline)

            with patch.object(entry, "_verify_native_stage", side_effect=verify), \
                    patch.object(entry.subprocess, "Popen") as agent:
                with self.assertRaises(KeyboardInterrupt):
                    entry.run_persistent(argparse.Namespace(evidence=manifest["evidence"]))
            agent.assert_not_called()
            partial = json.loads((Path(manifest["evidence"]) / "result.json").read_text(encoding="utf-8"))
            self.assertEqual(partial["executionFailure"], {
                "stage": 1, "phase": "preflight", "reason": "interrupted"})
            self.assertFalse(partial["caseComplete"])

    def test_failure_after_agent_popen_keeps_native_execution_phase(self):
        with tempfile.TemporaryDirectory() as tmp:
            manifest = self.prepared_persistent(Path(tmp).resolve())
            process = Mock(returncode=1)
            process.poll.return_value = 1
            job = Mock()
            job.sample.return_value = {"activeProcesses": 0}
            job.close.side_effect = ValueError("after-dispatch")
            with patch.object(entry, "WindowsJob", return_value=job), \
                    patch.object(entry.subprocess, "CREATE_NO_WINDOW", 0, create=True), \
                    patch.object(entry.subprocess, "Popen", return_value=process) as agent:
                with self.assertRaisesRegex(ValueError, "after-dispatch"):
                    entry.run_persistent(argparse.Namespace(evidence=manifest["evidence"]))
            agent.assert_called_once()
            self.assertEqual(agent.call_args.kwargs["creationflags"], 4)
            job.attach_and_resume.assert_called_once_with(process)
            partial = json.loads((Path(manifest["evidence"]) / "result.json").read_text(encoding="utf-8"))
            self.assertEqual(partial["executionFailure"], {
                "stage": 1, "phase": "native-execution", "reason": "execution-error"})
            self.assertFalse(partial["caseComplete"])

    def test_persistent_business_inspection_failure_keeps_native_receipt_and_unverified_result(self):
        with tempfile.TemporaryDirectory() as tmp:
            manifest = self.prepared_persistent(Path(tmp).resolve())
            observer = entry.coordination_observer()
            native = {"valid": True, "threadId": "native-thread", "remainingOwnedProcesses": 0}
            with patch.object(entry, "_run_persistent_stage", return_value=native) as stage, \
                    patch.object(observer, "inspect_stage", side_effect=ValueError("private-probe-detail")):
                with self.assertRaisesRegex(ValueError, "private-probe-detail"):
                    entry.run_persistent(argparse.Namespace(evidence=manifest["evidence"]))
            stage.assert_called_once()
            evidence = Path(manifest["evidence"])
            self.assertEqual(json.loads((evidence / "native-receipt-1.json").read_text()), native)
            partial = entry.inspect(evidence)["recordedExecution"]
            self.assertFalse(partial["caseComplete"])
            self.assertEqual(partial["completedStages"], 0)
            self.assertEqual(partial["threadId"], "native-thread")
            self.assertEqual(partial["executionFailure"]["phase"], "file-inspection")
            self.assertEqual(partial["stages"][0]["fileObservation"]["decision"], "unknown")
            self.assertNotIn("private-probe-detail", json.dumps(partial))
            frozen_result = (evidence / "result.json").read_bytes()
            (Path(manifest["workspace"]) / "plan.md").write_text("A later file, not the original execution.")
            fresh = entry.inspect(evidence)
            self.assertEqual(fresh["currentFileObservation"]["decision"], "pass")
            self.assertFalse(fresh["recordedExecution"]["caseComplete"])
            self.assertEqual(fresh["recordedExecution"]["completedStages"], 0)
            self.assertEqual((evidence / "result.json").read_bytes(), frozen_result)
            with patch.object(entry, "_run_persistent_stage") as replay:
                with self.assertRaises(FileExistsError):
                    entry.run_persistent(argparse.Namespace(evidence=manifest["evidence"]))
                replay.assert_not_called()

    def test_persistent_goal_read_interrupt_keeps_completed_cli_receipt(self):
        with tempfile.TemporaryDirectory() as tmp:
            manifest = self.prepared_persistent(Path(tmp).resolve())
            native = {"valid": True, "threadId": "native-thread", "remainingOwnedProcesses": 0}
            with patch.object(entry, "_run_persistent_stage", return_value=native) as stage, \
                    patch.object(entry, "_native_goal_readback", side_effect=KeyboardInterrupt()) as readback:
                with self.assertRaises(KeyboardInterrupt):
                    entry.run_persistent(argparse.Namespace(
                        evidence=manifest["evidence"], observe_native_goal=True))
            stage.assert_called_once(); readback.assert_called_once()
            evidence = Path(manifest["evidence"])
            self.assertEqual(json.loads((evidence / "native-receipt-1.json").read_text()), native)
            partial = json.loads((evidence / "result.json").read_text())
            self.assertEqual(partial["threadId"], "native-thread")
            self.assertEqual(partial["stages"][0]["threadId"], "native-thread")
            self.assertEqual(partial["stages"][0]["fileObservation"]["decision"], "unknown")
            self.assertEqual(partial["executionFailure"], {"stage": 1, "phase": "native-goal-readback",
                "reason": "interrupted"})
            self.assertFalse((evidence / "native-goal-1.json").exists())
            with patch.object(entry, "_run_persistent_stage") as replay:
                with self.assertRaises(FileExistsError):
                    entry.run_persistent(argparse.Namespace(
                        evidence=manifest["evidence"], observe_native_goal=True))
                replay.assert_not_called()

    def test_persistent_failure_before_receipt_keeps_effects_unknown_and_does_not_replay(self):
        for error in (ValueError("private-detail"), KeyboardInterrupt()):
            with self.subTest(error=type(error).__name__), tempfile.TemporaryDirectory() as tmp:
                manifest = self.prepared_persistent(Path(tmp).resolve())
                with patch.object(entry, "_run_persistent_stage", side_effect=error) as stage:
                    with self.assertRaises(type(error)):
                        entry.run_persistent(argparse.Namespace(evidence=manifest["evidence"]))
                stage.assert_called_once()
                checked = entry.inspect(manifest["evidence"])
                partial = checked["recordedExecution"]
                self.assertFalse(partial["caseComplete"])
                self.assertIsNone(partial["threadId"])
                self.assertEqual(partial["stages"], [])
                self.assertEqual(partial["executionFailure"]["phase"], "native-execution")
                self.assertEqual(partial["executionFailure"]["reason"],
                    "interrupted" if isinstance(error, KeyboardInterrupt) else "execution-error")
                self.assertEqual(checked["currentFileObservation"]["decision"], "unknown")
                self.assertNotIn("private-detail", json.dumps(checked))
                with patch.object(entry, "_run_persistent_stage") as replay:
                    with self.assertRaises(FileExistsError):
                        entry.run_persistent(argparse.Namespace(evidence=manifest["evidence"]))
                    replay.assert_not_called()

    def test_persistent_result_survives_separate_config_receipt_write_failure(self):
        with tempfile.TemporaryDirectory() as tmp:
            manifest = self.prepared_persistent(Path(tmp).resolve(), native_hooks=True)
            original_save = entry.save
            def fail_config(path, value):
                if Path(path).name == "shared-config.json":
                    raise OSError("private-storage-detail")
                return original_save(path, value)
            with patch.object(entry, "save", side_effect=fail_config), \
                    patch.object(entry, "_run_persistent_stage", side_effect=ValueError("original-failure")):
                with self.assertRaisesRegex(ValueError, "original-failure"):
                    entry.run_persistent(argparse.Namespace(evidence=manifest["evidence"]))
            partial = entry.inspect(manifest["evidence"])["recordedExecution"]
            self.assertFalse(partial["caseComplete"])
            self.assertEqual(partial["executionFailure"]["phase"], "native-execution")
            self.assertEqual(partial["poststateRetentionFailure"], "shared-config-receipt-unwritten")
            self.assertNotIn("private-storage-detail", json.dumps(partial))

    def test_persistent_poststate_observation_failure_preserves_original_error_and_unknown(self):
        with tempfile.TemporaryDirectory() as tmp:
            manifest = self.prepared_persistent(Path(tmp).resolve(), native_hooks=True)
            with patch.object(entry, "shared_config_snapshot", side_effect=[
                    {"state": "observed", "sha256": "original"}, KeyboardInterrupt()]), \
                    patch.object(entry, "_run_persistent_stage", side_effect=ValueError("original-failure")):
                with self.assertRaisesRegex(ValueError, "original-failure"):
                    entry.run_persistent(argparse.Namespace(evidence=manifest["evidence"]))
            partial = entry.inspect(manifest["evidence"])["recordedExecution"]
            self.assertFalse(partial["caseComplete"])
            self.assertEqual(partial["executionFailure"]["phase"], "native-execution")
            self.assertEqual(partial["sharedConfigObservation"]["after"]["state"], "unavailable")
            self.assertIsNone(partial["sharedConfigObservation"]["unchanged"])
            self.assertEqual(partial["poststateObservationFailure"], "shared-config-observation-unavailable")

    def test_native_stage_checks_the_opened_prompt_before_starting_a_process(self):
        with tempfile.TemporaryDirectory() as tmp:
            manifest = self.prepared_persistent(Path(tmp).resolve(), native_hooks=True)
            original = entry._verify_native_stage
            def changed_after_verification(*args, **deadline):
                bound = original(*args, **deadline)
                (Path(manifest["evidence"]) / "prompt-1.txt").write_text("changed before stdin open", encoding="utf-8")
                return bound
            with patch.object(entry, "_verify_native_stage", side_effect=changed_after_verification), \
                    patch.object(entry, "WindowsJob") as job, patch.object(entry.subprocess, "Popen") as forbidden:
                job.return_value.sample.return_value = {"activeProcesses": 0}
                receipt = entry._run_persistent_stage(manifest, 0, None, {}, time.monotonic() + 10)
            self.assertFalse(receipt["valid"])
            self.assertIn("prepared stage prompt changed before dispatch", receipt["failure"])
            forbidden.assert_not_called()

    def test_os_shell_hash_exception_does_not_accept_hardlinked_package_or_node(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            source = root / "node.exe"
            source.write_bytes(b"ordinary test runtime")
            os.link(source, root / "linked.exe")
            for override in (False, True):
                with self.subTest(os_shell=override), self.assertRaisesRegex(ValueError, "unsafe"):
                    entry.digest(source, os_shell=override)

    def test_native_node_projection_binds_an_absolute_renamed_executable(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            manifest = self.prepared_persistent(root, native_hooks=True)
            renamed = root / "runtime with spaces" / ("bound-runtime.exe" if os.name == "nt" else "bound-runtime")
            renamed.parent.mkdir()
            renamed.write_bytes(b"synthetic executable for projection only")
            projected = entry._native_hook_projection(manifest["package"], renamed)
            for registrations in projected["hooks"].values():
                for registration in registrations:
                    for handler in registration["hooks"]:
                        self.assertTrue(handler["command"].startswith(("& " if projected["shellKind"] == "powershell" else "") + '"' + renamed.as_posix() + '" "'))
                        self.assertFalse(handler["command"].startswith("node "))

    def test_native_projection_executes_in_the_detected_user_shell(self):
        node = shutil.which("node")
        self.assertIsNotNone(node)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            runtime = root / 'runtime with spaces'
            runtime.mkdir()
            renamed = runtime / ('bound-runtime.exe' if os.name == 'nt' else 'bound-runtime')
            shutil.copy2(node, renamed)
            package = root / 'package'
            (package / '.codex-plugin').mkdir(parents=True)
            (package / 'hooks').mkdir()
            (package / 'runtime').mkdir()
            (package / '.codex-plugin/plugin.json').write_text('{"name":"test","version":"1"}', encoding='utf-8')
            (package / 'runtime/check-runtime.cjs').write_text(
                'console.log(JSON.stringify({execPath:process.execPath,args:process.argv.slice(2)}));', encoding='utf-8')
            (package / 'hooks/hooks.json').write_text(json.dumps({'hooks': {'Stop': [{'hooks': [{
                'type': 'command', 'command': 'node "${PLUGIN_ROOT}/runtime/check-runtime.cjs" --hook Stop'}]}]}}), encoding='utf-8')
            (root / 'node.cmd').write_text('@echo shadow\r\nexit /B 91\r\n', encoding='utf-8')
            projection = entry._native_hook_projection(package, renamed)
            shell, kind = Path(projection['hookShell']), projection['shellKind']
            command = projection['hooks']['Stop'][0]['hooks'][0]['command']
            if kind == 'cmd':
                actual = _run_copied_runtime('"' + str(shell) + '" /C "' + command + '"', executable=str(shell),
                    cwd=root, runtime=renamed, owned_root=root)
            else:
                args = ['-NoLogo', '-NoProfile', '-Command'] if kind == 'powershell' else ['-c']
                actual = _run_copied_runtime([str(shell), *args, command], cwd=root,
                    runtime=renamed, owned_root=root)
            self.assertEqual(actual.returncode, 0, actual.stderr)
            observed = json.loads(actual.stdout)
            self.assertEqual(Path(observed['execPath']).resolve(), renamed)
            self.assertEqual(observed['args'], ['--hook', 'Stop'])

    def turn_context_rows(self, mode='default'):
        workspace = str(Path.cwd())
        return [
            {'type': 'session_meta', 'payload': {'id': 'thread', 'cwd': workspace, 'cli_version': 'recorded-version'}},
            {'type': 'event_msg', 'payload': {'type': 'task_started', 'turn_id': 'turn'}},
            {'type': 'turn_context', 'payload': {'turn_id': 'turn', 'cwd': workspace,
                'model': 'reported-model', 'effort': 'medium', 'collaboration_mode': {'mode': mode}}},
            {'type': 'response_item', 'payload': {'type': 'reasoning'}},
        ]

    def observe_turn_context(self, rows, **binding):
        # Leading blank line checks that the reported ordinal addresses the original.
        stream = '\n' + '\n'.join(json.dumps(row) for row in rows) + '\n'
        observed = entry.native_turn_context_observation(stream,
            **{'thread_id': 'thread', 'turn_id': 'turn', 'workspace': str(Path.cwd()), **binding})
        self.assertEqual(observed['sourceSha256'], hashlib.sha256(stream.encode()).hexdigest())
        self.assertEqual(observed['sourceBytes'], len(stream.encode()))
        return observed

    def test_native_turn_conditions_preserve_reported_mode_and_leave_goal_unknown(self):
        for mode in ('default', 'plan'):
            rows = self.turn_context_rows(mode)
            rows[2]['payload']['goal_mode_active'] = False  # Not a consumed native Goal receipt.
            result = self.observe_turn_context(rows)
            self.assertEqual(result['state'], 'observed')
            self.assertEqual(result['line'], 4)
            self.assertEqual(result['conditions'], {'model': 'reported-model', 'effort': 'medium',
                'cwd': str(Path.cwd()), 'collaborationMode': mode})
            self.assertEqual(result['recordedHostVersion'], 'recorded-version')
            self.assertIsNone(result['goalModeActive'])

    def test_native_turn_conditions_reject_missing_conflicting_and_late_context(self):
        base = self.turn_context_rows()
        cases = [base[:2] + base[3:], base[:3] + [base[2]] + base[3:],
                 base[:2] + [base[3], base[2]], base + [base[1]]]
        cases += [base[:2] + [{'type': 'event_msg', 'payload': {'type': 'item_completed',
                  'item': {'type': kind}}}] + base[2:] for kind in ('Reasoning', 'AgentMessage', 'CommandExecution', 'FileChange', 'UnknownNativeItem')]
        for field, value in (('turn_id', 'other'), ('cwd', str(Path.cwd().parent)),
                             ('model', ''), ('effort', None), ('collaboration_mode', None)):
            rows = json.loads(json.dumps(base)); rows[2]['payload'][field] = value; cases.append(rows)
        changed = json.loads(json.dumps(base[2])); changed['payload']['model'] = 'changed-model'
        cases.append(base + [changed])
        for rows in cases:
            with self.subTest(rows=rows):
                result = self.observe_turn_context(rows)
                self.assertEqual(result['state'], 'unknown')
                self.assertIsNone(result['conditions'])
                self.assertIsNone(result['goalModeActive'])
        for binding in ({'thread_id': 'foreign'}, {'turn_id': 'foreign'}, {'workspace': str(Path.cwd().parent)}):
            self.assertEqual(self.observe_turn_context(base, **binding)['state'], 'unknown')

    def test_native_turn_conditions_do_not_join_a_later_turn(self):
        base = self.turn_context_rows()
        following = json.loads(json.dumps(base[1:]))
        following[0]['payload']['turn_id'] = 'following'
        following[1]['payload'].update(turn_id='following', model='different-model')
        self.assertEqual(self.observe_turn_context(base + following)['conditions']['model'], 'reported-model')
        user_item = {'type': 'event_msg', 'payload': {'type': 'item_completed', 'item': {'type': 'UserMessage'}}}
        self.assertEqual(self.observe_turn_context(base[:2] + [user_item] + base[2:])['state'], 'observed')

    def test_native_goal_readback_binds_persisted_thread_and_releases_reader(self):
        thread_id = '11111111-1111-4111-8111-111111111111'
        with tempfile.TemporaryDirectory() as temporary:
            # Hosted Windows TEMP may use an 8.3 alias. The observer requires
            # canonical source paths; bind the fixture before recording them.
            root = Path(temporary).resolve()
            evidence, workspace, sessions = root / 'evidence', root / 'workspace', root / 'home' / 'sessions'
            evidence.mkdir(); workspace.mkdir(); sessions.mkdir(parents=True)
            rollout = sessions / 'rollout.jsonl'
            rollout.write_text(json.dumps({'type': 'session_meta', 'payload':
                {'id': thread_id, 'cwd': str(workspace)}}) + '\n', encoding='utf-8')
            rollout_alias = '\\\\?\\' + str(rollout) if os.name == 'nt' else str(rollout)
            codex = root / 'codex.exe'; codex.write_bytes(b'fixed executable')
            (evidence / 'stderr-1.txt').write_text(
                'Codex initialized with event: SessionConfiguredEvent { thread_id: ThreadId { uuid: '
                + thread_id + ' }, cwd: AbsolutePathBuf(' + json.dumps(str(workspace))
                + '), rollout_path: Some(' + json.dumps(rollout_alias) + ') }\n', encoding='utf-8')
            (evidence / 'stdout-1.jsonl').write_text(json.dumps(
                {'type': 'thread.started', 'thread_id': thread_id}) + '\n', encoding='utf-8')
            for stage in range(2, 17):
                (evidence / f'stderr-{stage}.txt').write_bytes((evidence / 'stderr-1.txt').read_bytes())
                (evidence / f'stdout-{stage}.jsonl').write_bytes((evidence / 'stdout-1.jsonl').read_bytes())
            manifest = {'evidence': str(evidence), 'workspace': str(workspace), 'codex': str(codex),
                'sourceHashes': {'codex': entry.digest(codex)}, 'recoveryTimeoutSeconds': 5}
            env = {'CODEX_HOME': str(root / 'home')}
            native = {'threadId': thread_id, 'terminal': 'completed', 'remainingOwnedProcesses': 0}
            calls, closed = [], []
            controller = 'windows-job-object' if os.name == 'nt' else 'posix-session-process-group'
            after = ({'activeProcesses': 0} if os.name == 'nt' else
                {'controller': controller, 'activeProcesses': None, 'processGroupState': 'absent',
                 'processGroupId': 1234, 'rootPid': 1234, 'rootExitCode': 0})
            normal_release = {'controller': controller, 'exitCode': 0, 'forced': False,
                'failure': None, 'readerStopped': True, 'after': after}
            manifest.update(resourceController=controller, resourceEvidenceScope=entry._resource_scope(controller))
            native.update(controller=controller, evidenceScope=entry._resource_scope(controller), after=after,
                          exitCode=0, remainingOwnedProcesses=0 if os.name == 'nt' else None)

            class Reader:
                goal_result = {'goal': None}
                read_path = rollout_alias
                ephemeral = False
                raw_override = {}
                duplicate_response = False
                duplicate_request_id = False
                raw_error = False
                release = normal_release

                def __init__(self, reader_manifest, label, argv, reader_env, deadline):
                    self.root = Path(reader_manifest['evidence']) / 'native' / label
                    self.root.mkdir()
                    (self.root / 'stdout.jsonl').write_text('', encoding='utf-8')
                    calls.append(('launch', argv, reader_env['CODEX_HOME']))

                def initialize(self):
                    calls.append(('initialize',))
                    with (self.root / 'requests.jsonl').open('a', encoding='utf-8') as stream:
                        stream.write(json.dumps({'id': 'init', 'method': 'initialize',
                            'params': {'clientInfo': {'name': 'accord_lifecycle_observer', 'version': '1'},
                                       'capabilities': {'experimentalApi': True}}}) + '\n')
                        stream.write(json.dumps({'method': 'initialized', 'params': {}}) + '\n')
                    with (self.root / 'stdout.jsonl').open('a', encoding='utf-8') as stream:
                        stream.write(json.dumps({'id': 'init', 'result': {}}) + '\n')

                def rpc(self, method, params):
                    calls.append((method, params))
                    request_id = 'same' if self.duplicate_request_id else str(len(calls))
                    with (self.root / 'requests.jsonl').open('a', encoding='utf-8') as stream:
                        stream.write(json.dumps({'id': request_id, 'method': method, 'params': params}) + '\n')
                    if method == 'thread/read':
                        result = {'thread': {'id': thread_id, 'cwd': str(workspace),
                            'ephemeral': self.ephemeral, 'path': self.read_path}}
                    else:
                        result = self.goal_result
                    wire_result = self.raw_override.get(method, result)
                    response = {'id': request_id, 'result': wire_result}
                    if self.raw_error and method == 'thread/goal/get':
                        response['error'] = {'code': -1, 'message': 'ambiguous'}
                    with (self.root / 'stdout.jsonl').open('a', encoding='utf-8') as stream:
                        stream.write(json.dumps(response) + '\n')
                        if self.duplicate_response and method == 'thread/goal/get':
                            stream.write(json.dumps(response) + '\n')
                    return result

                def close(self):
                    closed.append(True)
                    return self.release

            with patch('scripts.observe_codex_lifecycle._App', Reader):
                result = entry._native_goal_readback(manifest, native, stage=1, env=env,
                                                     deadline=time.monotonic() + 30)
                self.assertEqual(result['state'], 'observed', result)
                self.assertIs(result['goalPresent'], False)
                self.assertIs(result['goalModeActive'], False)
                self.assertEqual([call[0] for call in calls],
                                 ['launch', 'initialize', 'thread/read', 'thread/goal/get'])
                self.assertEqual(calls[-1][1], {'threadId': thread_id})
                self.assertEqual(len(closed), 1)
                self.assertEqual(result['cliSource']['rolloutPath'], str(rollout))
                self.assertEqual(result['rpcEvidence']['requestIds'].keys(), {'thread/read', 'thread/goal/get'})

                calls.clear(); Reader.read_path = str(root / 'foreign.jsonl')
                mismatch = entry._native_goal_readback(manifest, native, stage=2, env=env,
                                                       deadline=time.monotonic() + 30)
                self.assertEqual(mismatch['state'], 'unknown')
                self.assertEqual(mismatch['reason'], 'thread-read-persistent-binding-mismatch')
                self.assertNotIn('thread/goal/get', [call[0] for call in calls])
                self.assertEqual(len(closed), 2)

                calls.clear(); Reader.read_path = str(rollout); Reader.ephemeral = True
                ephemeral = entry._native_goal_readback(manifest, native, stage=3, env=env,
                                                       deadline=time.monotonic() + 30)
                self.assertEqual(ephemeral['state'], 'unknown')
                self.assertNotIn('thread/goal/get', [call[0] for call in calls])

                calls.clear(); Reader.read_path = str(rollout)
                Reader.ephemeral = False
                Reader.goal_result = {'goal': {'threadId': 'foreign', 'status': 'active'}}
                foreign = entry._native_goal_readback(manifest, native, stage=4, env=env,
                                                      deadline=time.monotonic() + 30)
                self.assertEqual(foreign['state'], 'unknown')
                self.assertIsNone(foreign['goalPresent'])
                self.assertIsNone(foreign['goalModeActive'])
                Reader.goal_result = {}
                missing = entry._native_goal_readback(manifest, native, stage=5, env=env,
                                                      deadline=time.monotonic() + 30)
                self.assertEqual(missing['state'], 'unknown')
                self.assertEqual(missing['reason'], 'goal-response-missing')
                Reader.goal_result = {'goal': None}
                Reader.release = {**normal_release, 'forced': True}
                unreleased = entry._native_goal_readback(manifest, native, stage=6, env=env,
                                                         deadline=time.monotonic() + 30)
                self.assertEqual(unreleased['state'], 'unknown')
                self.assertEqual(unreleased['reason'], 'reader-release-unobserved')

                Reader.release = normal_release
                Reader.raw_override = {'thread/read': {'thread': {'id': thread_id, 'cwd': str(workspace),
                    'ephemeral': False, 'path': str(root / 'foreign.jsonl')}}}
                tampered_thread = entry._native_goal_readback(manifest, native, stage=8, env=env,
                                                             deadline=time.monotonic() + 30)
                self.assertEqual(tampered_thread['state'], 'unknown')
                self.assertEqual(tampered_thread['reason'], 'raw-reader-receipt-unavailable')
                Reader.raw_override = {'thread/goal/get': {'goal': {'threadId': thread_id, 'status': 'active'}}}
                tampered_goal = entry._native_goal_readback(manifest, native, stage=9, env=env,
                                                           deadline=time.monotonic() + 30)
                self.assertEqual(tampered_goal['state'], 'unknown')
                Reader.raw_override = {}
                Reader.duplicate_response = True
                duplicate = entry._native_goal_readback(manifest, native, stage=10, env=env,
                                                        deadline=time.monotonic() + 30)
                self.assertEqual(duplicate['state'], 'unknown')
                Reader.duplicate_response = False
                Reader.raw_error = True
                error = entry._native_goal_readback(manifest, native, stage=11, env=env,
                                                    deadline=time.monotonic() + 30)
                self.assertEqual(error['state'], 'unknown')
                Reader.raw_error = False
                Reader.release = {**Reader.release, 'exitCode': 1}
                failed_exit = entry._native_goal_readback(manifest, native, stage=12, env=env,
                                                          deadline=time.monotonic() + 30)
                self.assertEqual(failed_exit['state'], 'unknown')
                Reader.release = {**Reader.release, 'exitCode': 0, 'readerStopped': False}
                live_reader = entry._native_goal_readback(manifest, native, stage=13, env=env,
                                                          deadline=time.monotonic() + 30)
                self.assertEqual(live_reader['state'], 'unknown')
                Reader.release = {'controller': 'posix-session-process-group', 'exitCode': 0,
                    'forced': False, 'failure': None, 'readerStopped': True,
                    'after': {'controller': 'posix-session-process-group', 'activeProcesses': None,
                        'processGroupState': 'absent', 'processGroupId': 1234, 'rootPid': 1234, 'rootExitCode': 0}}
                with patch('scripts.observe_codex_lifecycle._controller_kind', return_value='posix-session-process-group'):
                    posix = entry._native_goal_readback(manifest, native, stage=14, env=env,
                                                       deadline=time.monotonic() + 30)
                self.assertEqual(posix['state'], 'observed')
                self.assertIs(posix['goalModeActive'], False)
                Reader.release = normal_release
                Reader.duplicate_request_id = True
                duplicate_request = entry._native_goal_readback(manifest, native, stage=15, env=env,
                                                                deadline=time.monotonic() + 30)
                self.assertEqual(duplicate_request['state'], 'unknown')
                Reader.duplicate_request_id = False

            calls.clear()
            native['threadId'] = 'foreign'
            with patch('scripts.observe_codex_lifecycle._App', Reader):
                unbound = entry._native_goal_readback(manifest, native, stage=7, env=env,
                                                     deadline=time.monotonic() + 30)
            self.assertEqual(unbound['state'], 'unknown')
            self.assertEqual(calls, [])
            native['threadId'] = thread_id
            native.pop('terminal')
            with patch('scripts.observe_codex_lifecycle._App', Reader):
                no_current_turn = entry._native_goal_readback(manifest, native, stage=16, env=env,
                                                              deadline=time.monotonic() + 30)
            self.assertEqual(no_current_turn['state'], 'unknown')
            self.assertEqual(no_current_turn['reason'], 'cli-turn-not-completed')
            self.assertEqual(calls, [])

    def test_native_entry_gate_rejects_absent_stale_echoed_truncated_and_late_guidance(self):
        guide = 'Accord task entry: complete current source duties. '
        thread, turn, workspace = 'thread', 'turn', str(Path.cwd())
        epoch = '11111111-1111-4111-8111-111111111111'
        core = {'type': 'response_item', 'payload': {'type': 'message', 'role': 'developer',
            'internal_chat_message_metadata_passthrough': {'turn_id': turn, 'content_item_kinds': ['hooks.additional_context']},
            'content': [{'type': 'input_text', 'text': guide + f'Native input receipt: session=thread; epoch={epoch}.'}]}}
        start = [{'type': 'session_meta', 'payload': {'id': thread, 'cwd': workspace}},
                 {'type': 'event_msg', 'payload': {'type': 'task_started', 'turn_id': turn}}]
        action = {'type': 'response_item', 'payload': {'type': 'custom_tool_call'}}
        def check(rows, selected_turn=turn):
            return entry.native_entry_observation('\n'.join(json.dumps(x) for x in rows),
                thread_id=thread, turn_id=selected_turn, workspace=workspace, guide=guide)
        self.assertTrue(check([*start, core, action])['valid'])
        full, notice = (json.loads(json.dumps(core)) for _ in range(2))
        full['payload']['content'][0]['text'] = guide
        notice['payload']['content'][0]['text'] = f'Accord input/state notice. Native input receipt: session=thread; epoch={epoch}.'
        for pair in ([full, notice], [notice, full]):
            self.assertTrue(check([*start, *pair, action])['valid'])
        for rows in ([full], [notice], [full, action, notice], [notice, action, full]):
            self.assertFalse(check([*start, *rows, action])['valid'])
        for original, other in ((full, notice), (notice, full)):
            for mutation in ('assistant', 'stale', 'untrusted', 'truncated'):
                altered = json.loads(json.dumps(original))
                payload = altered['payload']
                if mutation == 'assistant':
                    payload['role'] = 'assistant'
                elif mutation == 'stale':
                    payload['internal_chat_message_metadata_passthrough']['turn_id'] = 'earlier-turn'
                elif mutation == 'untrusted':
                    payload.pop('internal_chat_message_metadata_passthrough')
                else:
                    payload['content'][0]['text'] = payload['content'][0]['text'][:25]
                self.assertFalse(check([*start, altered, other, action])['valid'], mutation)
        self.assertFalse(check([*start, action])['valid'])
        self.assertFalse(check([*start, action, core])['valid'])
        self.assertFalse(check([*start, core, action], 'another-turn')['valid'])
        for event in ('agent_reasoning', 'agent_message', 'item_completed'):
            early = {'type': 'event_msg', 'payload': {'type': event, 'item': {'type': 'Reasoning'}}}
            self.assertFalse(check([*start, early, core, action])['valid'])
            self.assertTrue(check([*start, core, early, action])['valid'])
        for kind in ('UserMessage', 'CommandExecution', 'FileChange', 'UnknownNativeItem'):
            native_item = {'type': 'event_msg', 'payload': {'type': 'item_completed', 'item': {'type': kind}}}
            self.assertEqual(check([*start, native_item, core, action])['valid'], kind == 'UserMessage')
        for mutation in ('assistant', 'stale', 'truncated'):
            altered = json.loads(json.dumps(core))
            if mutation == 'assistant':
                altered['payload']['role'] = 'assistant'
            elif mutation == 'stale':
                altered['payload']['internal_chat_message_metadata_passthrough']['turn_id'] = 'earlier-turn'
            else:
                altered['payload']['content'][0]['text'] = f'Accord task entry: Native input receipt: session=thread; epoch={epoch}.'
            self.assertFalse(check([*start, altered, action])['valid'], mutation)

    def test_native_entry_receipt_requires_complete_native_epoch_and_bound_source(self):
        guide, thread, turn = 'Accord task entry: complete source duties. ', 'thread', 'turn'
        workspace = str(Path.cwd())
        uuid_epoch = '11111111-1111-4111-8111-111111111111'
        sha_epoch = 'a' * 64
        def check(epoch, *, session=thread, source_turn=turn, terminator='.', prefix=guide, selected_guide=guide):
            rows = [
                {'type': 'session_meta', 'payload': {'id': thread, 'cwd': workspace}},
                {'type': 'event_msg', 'payload': {'type': 'task_started', 'turn_id': turn}},
                {'type': 'response_item', 'payload': {'type': 'message', 'role': 'developer',
                    'internal_chat_message_metadata_passthrough': {'turn_id': source_turn,
                        'content_item_kinds': ['hooks.additional_context']},
                    'content': [{'type': 'input_text', 'text': prefix
                        + f'Native input receipt: session={session}; epoch={epoch}{terminator}'}]}},
            ]
            return entry.native_entry_observation('\n'.join(map(json.dumps, rows)),
                thread_id=thread, turn_id=turn, workspace=workspace, guide=selected_guide)
        for epoch in (uuid_epoch, sha_epoch):
            with self.subTest(valid_epoch=epoch):
                self.assertTrue(check(epoch)['valid'])
        for epoch in ('', ' ', 'one', uuid_epoch[:-1], uuid_epoch + 'suffix', 'a' * 63,
                      'a' * 65, 'x' * 64, '11111111-1111-4111-z111-111111111111'):
            with self.subTest(invalid_epoch=epoch):
                self.assertFalse(check(epoch)['valid'])
        self.assertFalse(check(uuid_epoch, terminator='')['valid'])
        self.assertFalse(check(uuid_epoch, session='foreign')['valid'])
        self.assertFalse(check(uuid_epoch, source_turn='foreign')['valid'])
        # A complete sample inside the guide is not this turn's actual receipt.
        example = guide + f'Example Native input receipt: session={thread}; epoch={uuid_epoch}. '
        self.assertFalse(check('', prefix=example, selected_guide=example)['valid'])

    if os.name == "nt":
        def test_windows_native_cmd_runs_bound_renamed_node_despite_cwd_shadow(self):
            node = shutil.which("node")
            self.assertIsNotNone(node)
            with tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp).resolve()
                runtime = root / "runtime with spaces"
                runtime.mkdir()
                renamed = runtime / "bound-runtime.exe"
                shutil.copy2(node, renamed)
                workspace = root / "work"
                workspace.mkdir()
                (workspace / "node.cmd").write_text("@echo shadow\r\nexit /B 91\r\n", encoding="utf-8")
                source = workspace / "check-runtime.cjs"
                source.write_text("console.log(JSON.stringify({execPath:process.execPath,args:process.argv.slice(2)}));", encoding="utf-8")
                shell = Path(os.environ.get("SystemRoot", "C:/Windows")) / "System32/cmd.exe"
                # Reproduce command_runner.rs's raw_arg, without list2cmdline/shlex:
                # cmd receives /C followed by an extra outer quote pair around the
                # already quoted absolute executable and its quoted source argument.
                command = '"' + renamed.as_posix() + '" "' + source.as_posix() + '" --hook Stop'
                actual = _run_copied_runtime('"' + str(shell) + '" /C "' + command + '"', executable=str(shell),
                    cwd=workspace, runtime=renamed, owned_root=root)
                self.assertEqual(actual.returncode, 0, actual.stderr)
                observed = json.loads(actual.stdout)
                self.assertEqual(Path(observed["execPath"]).resolve(), renamed)
                self.assertEqual(observed["args"], ["--hook", "Stop"])

        def test_windows_copied_runtime_cleanup_retries_only_the_owned_sharing_lock(self):
            k = entry.ctypes.WinDLL('kernel32', use_last_error=True)
            k.CreateFileW.argtypes = [entry.W.LPCWSTR, entry.W.DWORD, entry.W.DWORD,
                entry.ctypes.c_void_p, entry.W.DWORD, entry.W.DWORD, entry.W.HANDLE]
            k.CreateFileW.restype = entry.W.HANDLE
            k.CloseHandle.argtypes, k.CloseHandle.restype = [entry.W.HANDLE], entry.W.BOOL
            with tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp).resolve()
                runtime, keep = root / 'bound-runtime.exe', root / 'keep.txt'
                runtime.write_bytes(b'owned image fixture')
                keep.write_bytes(b'preserve')
                handle = k.CreateFileW(str(runtime), 0x80000000, 3, None, 3, 0, None)
                self.assertNotEqual(handle, entry.ctypes.c_void_p(-1).value)
                original, attempts = Path.unlink, 0
                def release_on_third_attempt(path, **kwargs):
                    nonlocal handle, attempts
                    self.assertEqual(path, runtime)
                    attempts += 1
                    if attempts == 3:
                        self.assertTrue(k.CloseHandle(handle))
                        handle = None
                    return original(path, **kwargs)
                try:
                    with patch.object(Path, 'unlink', autospec=True, side_effect=release_on_third_attempt):
                        _unlink_copied_runtime(runtime, root)
                finally:
                    if handle is not None:
                        k.CloseHandle(handle)
                self.assertEqual(attempts, 3)
                self.assertFalse(runtime.exists())
                self.assertEqual(keep.read_bytes(), b'preserve')

        def test_windows_copied_runtime_cleanup_preserves_errors_and_scope(self):
            with tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp).resolve()
                runtime = root / 'bound-runtime.exe'
                runtime.write_bytes(b'owned image fixture')
                for code in (32, 5, 19):
                    error = PermissionError('persistent sharing lock or unrelated access denial')
                    error.winerror = code
                    with self.subTest(code=code), patch.object(Path, 'unlink', side_effect=error) as unlink:
                        with self.assertRaises(PermissionError) as caught:
                            _unlink_copied_runtime(runtime, root, timeout=0 if code in (32, 5) else 5)
                        self.assertIs(caught.exception, error)
                        self.assertEqual(unlink.call_count, 1)
                    self.assertTrue(runtime.exists())
                with patch.object(Path, 'unlink') as unlink, self.assertRaises(ValueError):
                    _unlink_copied_runtime(runtime, root / 'different-owned-root')
                unlink.assert_not_called()

        def test_windows_copied_runtime_waits_for_descendants_and_bounds_cleanup(self):
            node = shutil.which('node')
            self.assertIsNotNone(node)
            for delayed_exit in (True, False):
                with self.subTest(delayed_exit=delayed_exit), tempfile.TemporaryDirectory() as tmp:
                    root = Path(tmp).resolve()
                    runtime = root / 'bound-runtime.exe'
                    shutil.copy2(node, runtime)
                    marker = root / 'child-finished.txt'
                    child = ("setTimeout(()=>require('node:fs').writeFileSync(" + json.dumps(str(marker))
                             + ",'finished')," + ('250' if delayed_exit else '30000') + ");")
                    script = root / 'parent.cjs'
                    script.write_text("require('node:child_process').spawn(process.execPath,['-e',"
                        + json.dumps(child) + "],{detached:true,stdio:'ignore'}).unref();console.log('parent-finished');",
                        encoding='utf-8')
                    command = [str(runtime), str(script)]
                    if delayed_exit:
                        result = _run_copied_runtime(command, runtime=runtime, owned_root=root, cwd=root)
                        self.assertEqual(result.returncode, 0, result.stderr)
                        self.assertEqual(marker.read_text(), 'finished')
                    else:
                        with self.assertRaisesRegex(AssertionError, 'left live processes'):
                            _run_copied_runtime(command, runtime=runtime, owned_root=root,
                                cwd=root, exit_timeout=0.05)
                        self.assertFalse(marker.exists())
                    self.assertFalse(runtime.exists())

        def test_windows_copied_runtime_reaps_unassigned_child_if_job_termination_fails(self):
            with tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp).resolve()
                runtime = root / 'bound-runtime.exe'
                shutil.copy2(shutil.which('node'), runtime)
                job, created, native_popen = entry.WindowsJob(), [], subprocess.Popen
                recovery_handles, api = {}, subprocess._winapi
                def spawn(*args, **kwargs):
                    process = native_popen(*args, **kwargs)
                    created.append(process)
                    try:
                        owner = api.GetCurrentProcess()
                        recovery_handles[process.pid] = api.DuplicateHandle(owner, process._handle,
                            owner, 0, False, api.DUPLICATE_SAME_ACCESS)
                    except Exception:
                        process.kill()
                        process.communicate(timeout=5)
                        process._handle.Close()
                        raise
                    return process
                try:
                    with patch.object(entry, 'WindowsJob', return_value=job), \
                            patch.object(job, 'attach_and_resume', side_effect=OSError('assignment failed')), \
                            patch.object(job, 'terminate', side_effect=OSError('Job termination failed')), \
                            patch.object(subprocess, 'Popen', side_effect=spawn):
                        with self.assertRaisesRegex(OSError, 'Job termination failed'):
                            _run_copied_runtime([str(runtime), '-e', 'setTimeout(()=>{},30000)'],
                                runtime=runtime, owned_root=root, cwd=root)
                    self.assertEqual(len(created), 1)
                    self.assertIsNotNone(created[0].returncode, 'unassigned suspended child was not reaped')
                    self.assertTrue(created[0]._handle.closed)
                    self.assertIsNone(job.handle)
                    self.assertFalse(runtime.exists(), 'helper skipped image cleanup after recovery failure')
                finally:
                    for process in created:
                        handle = recovery_handles.get(process.pid)
                        try:
                            if process.returncode is None and handle is not None:
                                # The tested failure may close Popen's handle.
                                # This independent owned handle keeps a red test safe.
                                api.TerminateProcess(handle, 1)
                                self.assertEqual(api.WaitForSingleObject(handle, 5000), 0)
                                process.returncode = api.GetExitCodeProcess(handle)
                                process.communicate(timeout=5)
                        finally:
                            if handle is not None:
                                api.CloseHandle(handle)
                            if process.returncode is not None:
                                process._handle.Close()
                    job.close()
                    _unlink_copied_runtime(runtime, root)

    def test_native_prepare_rejects_missing_exec_configuration_isolation_before_creating_roots(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            package = root / "package"
            self.copy_hook_only_fixture(package)
            args = argparse.Namespace(package=str(package), evidence=str(root / "evidence"), workspace=str(root / "work"),
                codex=PYTHON, node=PYTHON, model="explicit-offline-model", reasoning="high", timeout=600,
                turn_timeout=180, recovery_timeout=20, windows_sandbox="elevated", native_package_hooks=True)
            unsupported = subprocess.CompletedProcess([], 0, b"--dangerously-bypass-hook-trust --sandbox --output-last-message", b"")
            with patch.object(entry.subprocess, "run", return_value=unsupported) as native:
                with self.assertRaisesRegex(ValueError, "required boundary"):
                    entry.prepare(args, persistent_case=entry.load_persistent_case(SCRIPT.parents[1] / "product/cases/coordination-v3.3.json"))
            self.assertEqual(native.call_count, 1)
            self.assertFalse((root / "evidence").exists())
            self.assertFalse((root / "work").exists())

    def test_hook_mode_validation_rejects_unknown_or_nonpersistent_native_projection(self):
        with tempfile.TemporaryDirectory() as tmp:
            manifest = self.prepared(Path(tmp).resolve())
            for mode in ("unknown", "native-package-hooks"):
                manifest["hookMode"] = mode
                entry.save(Path(manifest["evidence"]) / "manifest.json", manifest)
                with self.subTest(mode=mode), self.assertRaises(ValueError):
                    entry.load_manifest(manifest["evidence"])
                with self.assertRaises(ValueError):
                    entry.build_command(manifest)
            with self.assertRaisesRegex(ValueError, "require persistent"):
                entry.prepare(argparse.Namespace(native_package_hooks=True))

    def test_persistent_cli_receipt_requires_same_thread_completed_terminal_and_final(self):
        events = [
            {"type": "thread.started", "thread_id": "native-thread"},
            {"type": "turn.started"},
            {"type": "item.completed", "item": {"type": "agent_message", "text": "done"}},
            {"type": "turn.completed", "usage": {"output_tokens": 4}},
        ]
        encode = lambda rows: "\n".join(map(json.dumps, rows))
        self.assertTrue(entry.persistent_cli_turn_receipt(encode(events), "done", expected_thread_id="native-thread")["valid"])
        for name, changed, final, identity in (
            ("foreign-thread", events, "done", "other"),
            ("failed-terminal", events[:-1] + [{"type": "turn.failed"}], "done", "native-thread"),
            ("missing-final", events, "", "native-thread"),
            ("stale-final", events, "older answer", "native-thread"),
            ("duplicate-terminal", events + [events[-1]], "done", "native-thread"),
        ):
            with self.subTest(name=name):
                self.assertFalse(entry.persistent_cli_turn_receipt(encode(changed), final, expected_thread_id=identity)["valid"])

    def test_persistent_cli_usage_is_cumulative_and_never_summed_across_resume_turns(self):
        caps = {"totalTokens": 900000, "uncachedInputTokens": 200000, "outputTokens": 14000}
        def trace(input_tokens, cached_tokens, output_tokens):
            return json.dumps({"type": "turn.completed", "usage": {
                "input_tokens": input_tokens, "cached_input_tokens": cached_tokens,
                "output_tokens": output_tokens}})
        first = entry.persistent_cli_usage_budget(trace(700000, 550000, 10000), caps)
        resumed = entry.persistent_cli_usage_budget(trace(850000, 660000, 13000), caps)
        self.assertEqual(first["decision"], "within-observed-limits")
        self.assertEqual(resumed["decision"], "within-observed-limits")
        self.assertEqual(resumed["observed"]["totalTokens"], 863000)
        self.assertEqual(resumed["observed"]["uncachedInputTokens"], 190000)
        self.assertIn("cumulative", resumed["scope"])
        self.assertIsNone(resumed["monetaryCost"])

    def test_persistent_cli_usage_missing_malformed_or_over_limit_blocks_receipt(self):
        caps = {"totalTokens": 900000, "uncachedInputTokens": 200000, "outputTokens": 14000}
        base = [{"type": "thread.started", "thread_id": "native-thread"},
                {"type": "turn.started"},
                {"type": "item.completed", "item": {"type": "agent_message", "text": "done"}}]
        for name, usage, decision in (
                ("missing", None, "unknown"),
                ("missing-counter", {"input_tokens": 4, "output_tokens": 1}, "unknown"),
                ("boolean", {"input_tokens": 4, "cached_input_tokens": 2, "output_tokens": True}, "unknown"),
                ("cached-over-input", {"input_tokens": 4, "cached_input_tokens": 5, "output_tokens": 1}, "unknown"),
                ("over-total", {"input_tokens": 899000, "cached_input_tokens": 800000, "output_tokens": 2000}, "over-limit"),
                ("over-uncached", {"input_tokens": 850000, "cached_input_tokens": 649999, "output_tokens": 1000}, "over-limit"),
                ("over-output", {"input_tokens": 100000, "cached_input_tokens": 90000, "output_tokens": 14001}, "over-limit")):
            terminal = {"type": "turn.completed"}
            if usage is not None:
                terminal["usage"] = usage
            stream = "\n".join(map(json.dumps, base + [terminal]))
            with self.subTest(name=name):
                receipt = entry.persistent_cli_turn_receipt(
                    stream, "done", expected_thread_id="native-thread", usage_caps=caps)
                self.assertFalse(receipt["valid"])
                self.assertEqual(receipt["usageObservation"]["decision"], decision)

    def test_native_rollout_usage_binds_task_and_retains_partial_line(self):
        caps = {"totalTokens": 900000, "uncachedInputTokens": 200000, "outputTokens": 14000}
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            sessions, workspace = root / "sessions", root / "work"
            sessions.mkdir()
            workspace.mkdir()
            rollout = sessions / "rollout.jsonl"
            meta = {"type": "session_meta", "payload": {
                "id": "native-thread", "cwd": str(workspace)}}
            first = {"ordinal": 2, "timestamp": "2026-09-14T08:00:00Z", "type": "event_msg",
                     "payload": {"type": "token_count", "info": {"total_token_usage": {
                         "input_tokens": 700000, "cached_input_tokens": 550000,
                         "output_tokens": 10000, "total_tokens": 710000}}}}
            second = {"ordinal": 3, "timestamp": "2026-09-14T08:01:00Z", "type": "event_msg",
                      "payload": {"type": "token_count", "info": {"total_token_usage": {
                          "input_tokens": 850000, "cached_input_tokens": 660000,
                          "output_tokens": 13000, "total_tokens": 863000}}}}
            rollout.write_text(json.dumps(meta) + "\n" + json.dumps(first) + "\n", encoding="utf-8")
            observer = entry.NativeRolloutUsage(rollout, sessions_root=sessions,
                thread_id="native-thread", cwd=workspace, caps=caps)
            observed = observer.poll()
            self.assertEqual(observed["decision"], "within-observed-limits")
            self.assertEqual(observed["observed"]["totalTokens"], 710000)
            encoded = json.dumps(second).encode()
            with rollout.open("ab") as stream:
                stream.write(encoded[:len(encoded) // 2])
            unchanged = observer.poll()
            self.assertEqual(unchanged["observedAt"], "2026-09-14T08:00:00Z")
            with rollout.open("ab") as stream:
                stream.write(encoded[len(encoded) // 2:] + b"\n")
            resumed = observer.poll()
            self.assertEqual(resumed["observed"]["totalTokens"], 863000)
            self.assertEqual(resumed["observed"]["uncachedInputTokens"], 190000)
            self.assertEqual(resumed["source"]["ordinal"], 3)
            replacement = sessions / "replacement.jsonl"
            replacement.write_bytes(rollout.read_bytes() + b"{}\n")
            replacement.replace(rollout)
            self.assertEqual(observer.poll()["decision"], "unknown")

    def test_native_rollout_drive_alias_preserves_file_and_task_guards(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            sessions, workspace = root / 'sessions', root / 'work'
            sessions.mkdir(); workspace.mkdir()
            rollout = sessions / 'rollout.jsonl'
            rollout.write_text(json.dumps({'type': 'session_meta', 'payload': {
                'id': 'native-thread', 'cwd': str(workspace)}}) + '\n', encoding='utf-8')
            alias = '\\\\?\\' + str(rollout) if os.name == 'nt' else str(rollout)
            observer = entry.NativeRolloutUsage(rollout, sessions_root=sessions,
                thread_id='native-thread', cwd=workspace, caps={'totalTokens': 900000})
            config = {'threadId': 'native-thread', 'cwd': str(workspace), 'rolloutPath': alias}
            self.assertTrue(observer.matches(config))
            self.assertEqual(entry._ordinary_rollout(alias, sessions), rollout)
            resumed = entry.NativeRolloutUsage(alias, sessions_root=sessions,
                thread_id='native-thread', cwd=workspace, caps={'totalTokens': 900000})
            self.assertTrue(resumed.matches({**config, 'rolloutPath': str(rollout)}))
            self.assertFalse(observer.matches({**config, 'threadId': 'foreign-thread'}))
            self.assertFalse(observer.matches({**config, 'cwd': str(root)}))
            outside = root / 'outside.jsonl'; outside.write_bytes(rollout.read_bytes())
            self.assertFalse(observer.matches({**config, 'rolloutPath': str(outside)}))
            link = sessions / 'linked.jsonl'
            os.link(rollout, link)
            try:
                self.assertFalse(observer.matches(config))
            finally:
                link.unlink()
            self.assertTrue(observer.matches(config))

    def test_native_rollout_namespace_conversion_rejects_non_equivalent_spellings(self):
        # Replace this module's OS reference, not global os.name/Path behavior.
        with patch.object(entry, 'os', argparse.Namespace(name='nt', fspath=os.fspath)):
            self.assertEqual(entry._native_rollout_path(r'\\?\C:\Users\sample\rollout.jsonl'),
                             Path(r'C:\Users\sample\rollout.jsonl'))
            ordinary_unc = r'\\server\share\sessions\rollout.jsonl'
            self.assertEqual(entry._native_rollout_path(ordinary_unc), Path(ordinary_unc))
            for raw in (r'\\?\UNC\server\share\rollout.jsonl', r'\\?\GLOBALROOT\Device\rollout',
                        r'\\?\Volume{abc}\rollout', r'\\?\C:relative', r'\\?\C:\sessions\..\rollout',
                        r'\\?\C:\sessions\.\rollout', r'\\?\C:\sessions\rollout.',
                        '\\\\?\\C:\\sessions\\rollout ', r'\\?\C:\sessions\rollout:stream',
                        r'\\?\C:\sessions/rollout'):
                with self.subTest(path=raw), self.assertRaises(ValueError):
                    entry._native_rollout_path(raw)

    def test_native_rollout_usage_rejects_foreign_task_and_outside_path(self):
        caps = {"totalTokens": 900000}
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            sessions, workspace = root / "sessions", root / "work"
            sessions.mkdir()
            workspace.mkdir()
            rollout = sessions / "rollout.jsonl"
            rollout.write_text(json.dumps({"type": "session_meta", "payload": {
                "id": "foreign-thread", "cwd": str(workspace)}}) + "\n", encoding="utf-8")
            observer = entry.NativeRolloutUsage(rollout, sessions_root=sessions,
                thread_id="native-thread", cwd=workspace, caps=caps)
            self.assertEqual(observer.poll()["decision"], "unknown")
            outside = root / "outside.jsonl"
            outside.write_text("{}\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "outside the sessions root"):
                entry.NativeRolloutUsage(outside, sessions_root=sessions,
                    thread_id="native-thread", cwd=workspace, caps=caps)
            with self.assertRaisesRegex(ValueError, "outside the sessions root"):
                entry.NativeRolloutUsage(sessions / ".." / "outside.jsonl", sessions_root=sessions,
                    thread_id="native-thread", cwd=workspace, caps=caps)

    def test_persistent_stage_stops_on_running_usage_without_terminal(self):
        with tempfile.TemporaryDirectory() as tmp:
            manifest = self.prepared_persistent(Path(tmp).resolve())
            evidence = Path(manifest["evidence"])
            identity = "01a09f0c-7449-7400-8632-b5e6d27057b5"
            configuration = ('Codex initialized with event: SessionConfiguredEvent { '
                'session_id: SessionId { uuid: ' + identity + ' }, '
                'thread_id: ThreadId { uuid: ' + identity + ' }, '
                'cwd: AbsolutePathBuf("' + manifest["workspace"].replace("\\", "\\\\") + '"), '
                'rollout_path: Some("C:\\\\fake\\\\rollout.jsonl") }\n')
            other = "01a09f0c-7449-7400-8632-b5e6d27057b6"
            changed = configuration.replace('thread_id: ThreadId { uuid: ' + identity,
                                            'thread_id: ThreadId { uuid: ' + other)
            self.assertEqual(entry._session_configuration([changed.encode()])["threadId"], other)
            process = Mock(returncode=124)
            process.poll.return_value = None
            process.wait.return_value = 124
            job = Mock()
            job.sample.side_effect = [
                {"activeProcesses": 1}, {"activeProcesses": 1}, {"activeProcesses": 0}]
            observer = Mock()
            observer.matches.return_value = True
            observer.poll.return_value = {
                "decision": "over-limit", "observed": {"totalTokens": manifest["limits"]["usageCaps"]["totalTokens"] + 1},
                "caps": manifest["limits"]["usageCaps"], "exceeded": ["totalTokens"],
                "source": {"kind": "native-rollout-token-count", "path": "bound-rollout", "ordinal": 182},
                "observedAt": "2026-09-14T08:37:24.439Z"}
            def spawn(*_, **kwargs):
                kwargs["stdout"].write((json.dumps({"type": "thread.started", "thread_id": identity}) + "\n").encode())
                kwargs["stdout"].flush()
                kwargs["stderr"].write(configuration.encode())
                kwargs["stderr"].flush()
                return process
            with patch.object(entry, "WindowsJob", return_value=job), \
                    patch.object(entry.subprocess, "CREATE_NO_WINDOW", 0, create=True), \
                    patch.object(entry.subprocess, "Popen", side_effect=spawn), \
                    patch.object(entry.time, "sleep"):
                receipt = entry._run_persistent_stage(
                    manifest, 0, None, {}, time.monotonic() + 10, {"observer": observer})
            self.assertFalse(receipt["valid"])
            self.assertTrue(receipt["forced"])
            self.assertEqual(receipt["failure"], "usage-limit")
            self.assertIsNone(receipt["terminal"])
            self.assertEqual(receipt["usageObservation"]["observed"]["totalTokens"],
                             manifest["limits"]["usageCaps"]["totalTokens"] + 1)
            self.assertEqual(receipt["usageObservation"]["source"]["ordinal"], 182)
            job.terminate.assert_called_once_with()

    def test_persistent_case_rejects_workspace_escape_names(self):
        source = SCRIPT.parents[1] / "product/cases/coordination-v3.3.json"
        case = json.loads(source.read_text(encoding="utf-8"))
        for name in ("../outside.txt", "sub/file.txt", str(Path(source).resolve())):
            with self.subTest(name=name), tempfile.TemporaryDirectory() as tmp:
                changed = json.loads(json.dumps(case))
                changed["inputs"][name] = "escape"
                path = Path(tmp) / "case.json"
                path.write_text(json.dumps(changed), encoding="utf-8")
                with self.assertRaisesRegex(ValueError, "unsupported persistent case"):
                    entry.load_persistent_case(path)

    def test_persistent_cli_stops_after_first_failed_stage_and_reports_known_source_identity(self):
        with tempfile.TemporaryDirectory() as tmp:
            manifest = self.prepared_persistent(Path(tmp).resolve())
            first = {"valid": True, "threadId": "native-thread"}
            failed = {"valid": False, "threadId": "native-thread"}
            def execute(manifest, stage, *_):
                if stage == 0:
                    (Path(manifest["workspace"]) / "plan.md").write_text("Pending approval.", encoding="utf-8")
                return first if stage == 0 else failed
            with patch.object(entry, "_run_persistent_stage", side_effect=execute) as stages:
                result = entry.run_persistent(argparse.Namespace(evidence=manifest["evidence"]))
            self.assertEqual(stages.call_count, 2)
            self.assertFalse(result["caseComplete"])
            self.assertEqual(result["completedStages"], 1)
            self.assertEqual(result["threadId"], "native-thread")
            self.assertTrue(result["sourceThreadIdKnown"])
            self.assertFalse(result["nativeResumeSucceeded"])
            fresh = entry.inspect(manifest["evidence"])
            self.assertEqual(fresh["entryProtocol"], "exec-resume")
            self.assertEqual(fresh["currentFileObservation"]["decision"], "fail")

    def test_persistent_cli_stops_before_agreement_when_required_plan_is_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            manifest = self.prepared_persistent(Path(tmp).resolve())
            with patch.object(entry, "_run_persistent_stage", return_value={
                    "valid": True, "threadId": "native-thread"}) as stages:
                result = entry.run_persistent(argparse.Namespace(evidence=manifest["evidence"]))
            self.assertEqual(stages.call_count, 1)
            self.assertFalse(result["caseComplete"])
            self.assertIn("required file missing: plan.md", result["stages"][0]["fileObservation"]["violations"])

    def test_persistent_stage_allows_natural_job_drain_before_termination(self):
        with tempfile.TemporaryDirectory() as tmp:
            manifest = self.prepared_persistent(Path(tmp).resolve())
            evidence = Path(manifest["evidence"])
            usage = {"input_tokens": 1000, "cached_input_tokens": 800, "output_tokens": 50}
            events = [{"type": "thread.started", "thread_id": "native-thread"},
                      {"type": "turn.started"},
                      {"type": "item.completed", "item": {"type": "agent_message", "text": "done"}},
                      {"type": "turn.completed", "usage": usage}]
            process = Mock(returncode=0)
            process.poll.return_value = 0
            process.wait.return_value = 0
            job = Mock()
            job.sample.side_effect = [
                {"activeProcesses": 1}, {"activeProcesses": 0}, {"activeProcesses": 0}]
            def spawn(*_, **kwargs):
                kwargs["stdout"].write("\n".join(map(json.dumps, events)).encode())
                kwargs["stdout"].flush()
                (evidence / "last-message-1.txt").write_text("done", encoding="utf-8")
                return process
            with patch.object(entry, "WindowsJob", return_value=job), \
                    patch.object(entry.subprocess, "CREATE_NO_WINDOW", 0, create=True), \
                    patch.object(entry.subprocess, "Popen", side_effect=spawn), \
                    patch.object(entry.time, "sleep"):
                receipt = entry._run_persistent_stage(
                    manifest, 0, None, {}, time.monotonic() + 10)
            self.assertTrue(receipt["valid"])
            self.assertFalse(receipt["forced"])
            self.assertEqual(receipt["remainingOwnedProcesses"], 0)
            self.assertEqual(receipt["usageObservation"]["decision"], "within-observed-limits")
            job.terminate.assert_not_called()

    def test_persistent_stage_forces_timeout_without_a_second_recovery_window(self):
        with tempfile.TemporaryDirectory() as tmp:
            manifest = self.prepared_persistent(Path(tmp).resolve())
            process = Mock(returncode=124)
            process.poll.return_value = None
            process.wait.return_value = 124
            job = Mock()
            job.sample.side_effect = [
                {"activeProcesses": 1}, {"activeProcesses": 1}, {"activeProcesses": 0}]
            clock = [100.0]
            def spawn(*args, **kwargs):
                # Exercise expiry during owned work. An already-expired input
                # is now separately required to remain undispatched.
                clock[0] = 102.0
                return process
            with patch.object(entry, "WindowsJob", return_value=job), \
                    patch.object(entry.subprocess, "CREATE_NO_WINDOW", 0, create=True), \
                    patch.object(entry.subprocess, "Popen", side_effect=spawn), \
                    patch.object(entry.time, "monotonic", side_effect=lambda: clock[0]), \
                    patch.object(entry.time, "sleep"):
                receipt = entry._run_persistent_stage(manifest, 0, None, {}, 101.0)
            self.assertFalse(receipt["valid"])
            self.assertTrue(receipt["forced"])
            self.assertEqual(receipt["failure"], "turn-time-or-output-limit")
            job.terminate.assert_called_once_with()
            wait_timeout = process.wait.call_args.kwargs["timeout"]
            self.assertGreaterEqual(wait_timeout, 0)
            self.assertLessEqual(wait_timeout, manifest["recoveryTimeoutSeconds"])

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

    def test_cli_mixed_display_quotes_preserve_the_executed_script(self):
        # Native 0.154 display shape from a failed observation, with private
        # paths shortened. Adjacent quotes encode one argv element, not a shell.
        command = r'''"C:\\Program Files\\PowerShell\\7\\pwsh.exe" -Command "& 'C:\\Python\\python.exe' -B order_source.py; "'$code=$LASTEXITCODE; Write-Output "EXIT_CODE=$code"; exit $code' '''.strip()
        events = [json.loads(line) for line in self.trace(first_code=75).splitlines()]
        for event in events[1:]:
            item = event["item"]
            item["command"] = command
            if event["type"] == "item.completed":
                item["aggregated_output"] += f'EXIT_CODE={item["exit_code"]}\n'
        observed = entry.source_recovery_from_events("\n".join(map(json.dumps, events)), r"C:\Python\python.exe")
        self.assertTrue(observed["recovered"])
        self.assertEqual((observed["failedItemId"], observed["successfulItemId"]), ("failed", "success"))

    def test_cli_status_propagation_requires_exact_call_tail_and_native_receipt(self):
        for mutation in (None, "wrong-native-code", "wrong-printed-code", "wrong-label", "extra-command",
                         "wrong-variable", "fixed-exit", "printed-call", "foreign-executable",
                         "extra-argv", "broken-display"):
            events = [json.loads(line) for line in self.trace(first_code=75).splitlines()]
            for event in events[1:]:
                item = event["item"]
                body = "& '" + PYTHON + "' -B order_source.py; " + '$code=$LASTEXITCODE; Write-Output "STATUS=$code"; exit $code'
                if item["id"] == "failed":
                    if mutation == "extra-command": body += "; Write-Output 'STATUS=75'"
                    elif mutation == "wrong-variable": body = body.replace("exit $code", "exit $other")
                    elif mutation == "fixed-exit": body = body.replace("exit $code", "exit 75")
                    elif mutation == "printed-call": body = "Write-Output " + body
                    elif mutation == "foreign-executable": body = body.replace(PYTHON, PYTHON + ".other")
                argv = [r"C:\PowerShell\pwsh.exe", "-Command", body]
                if mutation == "extra-argv": argv.append("extra")
                item["command"] = shlex.join(argv) + ("'" if mutation == "broken-display" else "")
                if event["type"] == "item.completed":
                    printed = item["exit_code"]
                    if item["id"] == "failed":
                        if mutation == "wrong-native-code": item["exit_code"] = 0
                        elif mutation == "wrong-printed-code": printed = 0
                    label = "FOREIGN" if mutation == "wrong-label" else "STATUS"
                    item["aggregated_output"] += f'{label}={printed}\n'
            with self.subTest(mutation=mutation):
                observed = entry.source_recovery_from_events("\n".join(map(json.dumps, events)), PYTHON)
                self.assertEqual(observed["recovered"], mutation is None)

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
            self.assertEqual(command[command.index("--output-last-message") + 1], str(root / "evidence/last-message.txt"))
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

    def test_cli_accepts_exact_safe_bare_executable_but_not_quoted_or_printed_commands(self):
        executable = r"C:\Python314\python.exe"
        body = executable + " -B order_source.py"
        def trace(command_body):
            events = [json.loads(line) for line in self.trace().splitlines()]
            command = '"C:\\Program Files\\PowerShell\\7\\pwsh.exe" -Command "' + command_body + '"'
            for event in events:
                if "item" in event:
                    event["item"]["command"] = command
            return "\n".join(map(json.dumps, events))
        self.assertTrue(entry.source_recovery_from_events(trace(body), executable)["recovered"])
        for literal in ("'" + body + "'", '\\"' + body + '\\"',
                        "Write-Output '" + body + "'", body + "; Write-Output 'extra'",
                        body.replace(executable, r"C:\Other\python.exe")):
            with self.subTest(command=literal):
                self.assertFalse(entry.source_recovery_from_events(trace(literal), executable)["recovered"])

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

    def test_posix_observation_error_keeps_os_cause_and_cannot_prove_release(self):
        from scripts.inspect_native_resources import native_processes_released
        group = object.__new__(entry.PosixProcessGroup)
        group.process, group.pgid, group.absent = Mock(pid=43210), 43210, False
        group.last_observation_error = None
        group.process.poll.return_value = 0
        with patch.object(entry.os, "killpg", create=True,
                          side_effect=PermissionError(1, "Operation not permitted")):
            sample = group.sample()
        self.assertEqual(sample["processGroupState"], "unobservable")
        self.assertEqual(sample["observationError"]["errno"], 1)
        self.assertEqual(sample["observationError"]["type"], "PermissionError")
        self.assertIn("Operation not permitted", sample["observationError"]["message"])
        self.assertEqual(sample["lastObservationError"], sample["observationError"])
        self.assertFalse(native_processes_released(sample, "posix-session-process-group"))
        self.assertIsNone(sample["activeProcesses"])

    def test_posix_disappearance_retains_prior_observation_error_without_signalling_again(self):
        group = object.__new__(entry.PosixProcessGroup)
        group.process, group.pgid, group.absent = Mock(pid=43210), 43210, False
        group.last_observation_error = None
        group.process.poll.return_value = 0
        with patch.object(entry.os, "killpg", create=True,
                          side_effect=[OSError(4, "Interrupted system call"),
                                       ProcessLookupError(3, "No such process")]) as killpg:
            failed = group.sample()
            disappeared = group.sample()
            group.sample()
            group.terminate()
        self.assertEqual(killpg.call_count, 2)
        self.assertEqual(disappeared["processGroupState"], "absent")
        self.assertIsNone(disappeared["observationError"])
        self.assertEqual(disappeared["lastObservationError"], failed["observationError"])

    def posix_controller_observes_direct_root_and_never_claims_process_counts(self):
        group = entry.PosixProcessGroup()
        process = subprocess.Popen([PYTHON, "-c", "import time; time.sleep(30)"], start_new_session=True)
        try:
            group.attach_and_resume(process)
            observed = group.sample()
            self.assertEqual(observed["processGroupId"], process.pid)
            self.assertNotEqual(process.pid, os.getpgrp())
            self.assertEqual(observed["processGroupState"], "alive")
            self.assertIsNone(observed["activeProcesses"])
            self.assertIsNone(observed["cpuSeconds"])
            self.assertIn("escaped descendants", observed["evidenceScope"])
            with patch.object(entry.os, "killpg", side_effect=PermissionError):
                self.assertEqual(group.sample()["processGroupState"], "unobservable")
            group.terminate()
            process.wait(timeout=5)
            self.assertEqual(group.sample()["processGroupState"], "absent")
            # Once disappearance is observed, a recycled numerical id is not
            # queried/signalled again by this controller.
            with patch.object(entry.os, "killpg") as signal_group:
                group.sample(); group.terminate(); group.close()
            signal_group.assert_not_called()
        finally:
            if process.poll() is None:
                process.kill(); process.wait(timeout=5)

    def posix_controller_rejects_unisolated_process_without_signalling_caller_group(self):
        group = entry.PosixProcessGroup()
        process = subprocess.Popen([PYTHON, "-c", "import time; time.sleep(30)"])
        try:
            with self.assertRaisesRegex(ValueError, "new session/group"):
                group.attach_and_resume(process)
            with patch.object(entry.os, "killpg") as signal_group:
                group.terminate()
            signal_group.assert_not_called()
        finally:
            process.kill(); process.wait(timeout=5)

    def posix_descendant_can_leave_group_and_is_not_counted_as_contained(self):
        code = ("import subprocess,sys; child=subprocess.Popen([sys.executable,'-c','import time; time.sleep(30)'],"
                "start_new_session=True,stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL);"
                "print(child.pid,flush=True); sys.stdin.readline(); child.terminate(); child.wait()")
        process = subprocess.Popen([PYTHON, "-u", "-c", code], start_new_session=True,
                                   stdin=subprocess.PIPE, stdout=subprocess.PIPE)
        group = entry.PosixProcessGroup()
        try:
            group.attach_and_resume(process)
            child_pid = int(process.stdout.readline())
            self.assertNotEqual(os.getpgid(child_pid), group.pgid)
            self.assertIsNone(group.sample()["activeProcesses"])
        finally:
            # Ask the parent to reap its escaped child; do not orphan test work.
            process.stdin.write(b"\n"); process.stdin.flush(); process.stdin.close()
            process.wait(timeout=5)
            process.stdout.close()
            group.close()
        self.assertEqual(group.sample()["processGroupState"], "absent")



    def sample_release(self, *, pid=1, exit_code=124, controller=None):
        controller = controller or entry._controller_kind()
        after = ({"activeProcesses": 0} if controller == "windows-job-object" else
                 {"controller": controller, "activeProcesses": None,
                  "processGroupState": "absent", "processGroupId": pid,
                  "rootPid": pid, "rootExitCode": exit_code, "observationError": None})
        return {"controller": controller, "evidenceScope": entry._resource_scope(controller),
                "pid": pid, "after": after,
                "remainingOwnedProcesses": 0 if controller == "windows-job-object" else None}

    def sample_fixture(self, root, *, stem="native-receipt-1", controller=None):
        samples = [{"time": i, "processes": [{"pid": i + 1, "name": "x" * 40000}]}
                   for i in range(3)]
        sink = entry.ResourceSamples(root, stem)
        for sample in samples:
            sink.append(sample)
        record = {"stage": 1, "valid": False, "threadId": "native-thread",
                  "exitCode": 124, "forced": True, "failure": "usage-limit",
                  **self.sample_release(controller=controller), **sink.record()}
        path = root / (stem + ".json")
        entry._save_control(path, record)
        return samples, record, path

    def test_samples_preserve_large_and_small(self):
        for controller in ("windows-job-object", "posix-session-process-group"):
            with self.subTest(controller=controller), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp).resolve()
                small = entry.ResourceSamples(root, "resources")
                small.append({"time": 1, "processes": []})
                self.assertEqual(small.record(), {"samples": [{"time": 1, "processes": []}]})
                samples, record, path = self.sample_fixture(root, controller=controller)
                loaded = entry._read_observer_record(path)
                self.assertEqual(loaded, record)
                self.assertTrue(entry._entry_resources_released(loaded, {
                    "resourceController": controller,
                    "resourceEvidenceScope": entry._resource_scope(controller)}))
                ref = loaded["sampleEvidence"]
                rows = [row for chunk in ref["chunks"]
                        for row in json.loads((root / chunk["path"]).read_bytes())]
                self.assertEqual(rows, samples)
                self.assertEqual(ref["count"], len(samples))
                self.assertLess(path.stat().st_size, entry.RESOURCE_INLINE_BYTES)
                self.assertNotIn("samples", loaded)

    def test_samples_reject_bad_refs(self):
        for fault in ("hash", "bytes", "count", "total-count", "total-bytes",
                      "duplicate", "escape", "absolute", "missing", "mixed", "extra"):
            with self.subTest(fault=fault), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp).resolve()
                _, record, path = self.sample_fixture(root)
                ref = record["sampleEvidence"]
                chunk = ref["chunks"][0]
                if fault == "hash": chunk["sha256"] = "0" * 64
                elif fault == "bytes": chunk["bytes"] += 1
                elif fault == "count": chunk["count"] += 1
                elif fault == "total-count": ref["count"] += 1
                elif fault == "total-bytes": ref["bytes"] += 1
                elif fault == "duplicate": ref["chunks"].append(dict(chunk))
                elif fault == "escape": chunk["path"] = "../" + chunk["path"]
                elif fault == "absolute": chunk["path"] = str(root / chunk["path"])
                elif fault == "missing": (root / chunk["path"]).unlink()
                elif fault == "mixed": record["samples"] = []
                elif fault == "extra": (root / "native-receipt-1.samples-9999.json").write_bytes(b"[]")
                entry.save(path, record)
                with self.assertRaises((ValueError, OSError)):
                    entry._read_observer_record(path)

    def test_samples_reject_links_and_drift(self):
        for fault in ("symlink", "hardlink", "drift"):
            with self.subTest(fault=fault), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp).resolve()
                _, record, path = self.sample_fixture(root)
                chunk = root / record["sampleEvidence"]["chunks"][0]["path"]
                if fault != "drift":
                    original = root / "original.json"
                    chunk.rename(original)
                    try:
                        if fault == "symlink": chunk.symlink_to(original)
                        else: os.link(original, chunk)
                    except OSError as error:
                        self.skipTest("Link fixture unavailable: " + str(error))
                    with self.assertRaises(ValueError):
                        entry._read_observer_record(path)
                else:
                    read = entry.read_regular
                    def changed(file, *args, **kwargs):
                        raw = read(file, *args, **kwargs)
                        if Path(file) == chunk:
                            chunk.write_bytes(raw + b" ")
                        return raw
                    with patch.object(entry, "read_regular", side_effect=changed):
                        with self.assertRaisesRegex(ValueError, "changed"):
                            entry._read_observer_record(path)

    def test_samples_persistent_inspection(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            manifest = self.prepared_persistent(root, self.scoped_case(root))
            evidence = Path(manifest["evidence"])
            def execute(prepared, *_):
                (Path(prepared["workspace"]) / "report.json").write_text('{"candidate":"abc"}')
                _, record, _ = self.sample_fixture(evidence)
                # run_persistent is the sole receipt writer.
                (evidence / "native-receipt-1.json").unlink()
                return record
            with patch.object(entry, "_run_persistent_stage", side_effect=execute):
                result = entry.run_persistent(argparse.Namespace(evidence=str(evidence)))
            frozen = {p.relative_to(evidence): p.read_bytes() for p in evidence.rglob("*") if p.is_file()}
            for retained in (False, True):
                with patch.object(entry, "_run_persistent_stage") as forbidden:
                    checked = entry.inspect(evidence, retained=retained)
                forbidden.assert_not_called()
                self.assertFalse(checked["recordedExecution"]["caseComplete"])
                self.assertEqual(checked["recordedExecution"]["stages"][0]["failure"], "usage-limit")
                self.assertTrue(checked["retainedResourceObservations"][0]["releasedWithinScope"])
                self.assertLess(len(json.dumps(checked)), 100000)
            self.assertEqual(frozen, {p.relative_to(evidence): p.read_bytes() for p in evidence.rglob("*") if p.is_file()})

    def test_samples_legacy_readonly_views(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            manifest, result = self.retained_scoped_fixture(root)
            evidence = Path(manifest["evidence"])
            samples = [{"sample": "x" * 900000, "ordinal": i} for i in range(10)]
            stage = result["stages"][0]
            stage.update(samples=samples, failure="usage-limit", exitCode=124, forced=True, valid=False,
                         stage=1, **self.sample_release())
            result.update(caseComplete=False, completedStages=0)
            native = {key: value for key, value in stage.items()
                      if key not in ("fileObservation", "nativeGoalObservation")}
            entry.save(evidence / "native-receipt-1.json", native)
            entry.save(evidence / "result.json", result)
            frozen = {p.name: p.read_bytes() for p in (evidence / "result.json", evidence / "native-receipt-1.json")}
            self.assertGreater(len(frozen["result.json"]), 8 * 1024 * 1024)
            with self.assertRaises(ValueError):
                entry.read_regular(evidence / "result.json")
            for retained in (False, True):
                checked = entry.inspect(evidence, retained=retained)
                viewed = checked["recordedExecution"]["stages"][0]
                self.assertNotIn("samples", viewed)
                self.assertEqual(viewed["legacySamples"]["count"], 10)
                self.assertEqual(viewed["legacySamples"]["pointer"], "/stages/0/samples")
                self.assertEqual(viewed["legacySamples"]["sha256"], hashlib.sha256(frozen["result.json"]).hexdigest())
                self.assertEqual(viewed["failure"], "usage-limit")
                self.assertFalse(checked["recordedExecution"]["caseComplete"])
                self.assertLess(len(json.dumps(checked)), 100000)
            self.assertEqual(frozen, {name: (evidence / name).read_bytes() for name in frozen})

    def test_samples_legacy_bound(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            control = {"label": "\u4e2d", "payload": ""}
            encoded = lambda: (json.dumps(control, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
            control["payload"] = "x" * (8 * 1024 * 1024 - len(encoded()))
            entry._save_control(root / "exact.json", control)
            self.assertEqual((root / "exact.json").read_bytes(), encoded())
            self.assertEqual(len(encoded()), 8 * 1024 * 1024)
            control["payload"] += "x"
            with self.assertRaisesRegex(ValueError, "size-limit"):
                entry._save_control(root / "over.json", control)
            self.assertFalse((root / "over.json").exists())
            oversized = {"schema": "accord-codex-persistent-exec/v1", "stages": [],
                         "unrelated": "x" * (8 * 1024 * 1024)}
            entry.save(root / "result.json", oversized)
            with self.assertRaisesRegex(ValueError, "not legacy"):
                entry._read_observer_record(root / "result.json")
            with self.assertRaisesRegex(ValueError, "size-limit"):
                entry._save_control(root / "new-result.json", oversized)
            self.assertFalse((root / "new-result.json").exists())

    def test_samples_ephemeral_inspection(self):
        for legacy in (False, True):
            with self.subTest(legacy=legacy), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp).resolve()
                manifest = self.prepared(root)
                evidence = Path(manifest["evidence"])
                samples, record, path = self.sample_fixture(evidence, stem="resources")
                if legacy:
                    for chunk in record.pop("sampleEvidence")["chunks"]:
                        (evidence / chunk["path"]).unlink()
                    record["samples"] = [{"payload": "x" * 900000} for _ in range(10)]
                record["afterCleanup"] = record.pop("after")
                entry.save(path, record)
                before = path.read_bytes()
                with patch.object(entry.subprocess, "Popen") as forbidden:
                    checked = entry.inspect(evidence)
                forbidden.assert_not_called()
                self.assertTrue(checked["retainedResourceObservation"]["releasedWithinScope"])
                self.assertLess(len(json.dumps(checked)), 100000)
                self.assertEqual(path.read_bytes(), before)
                if not legacy:
                    chunk = evidence / record["sampleEvidence"]["chunks"][0]["path"]
                    chunk.write_bytes(b"[]")
                    self.assertFalse(entry.inspect(evidence)["retainedResourceObservation"]["releasedWithinScope"])

    def test_samples_budget_cleanup(self):
        for persistent in (False, True):
            with self.subTest(persistent=persistent), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp).resolve()
                manifest = self.prepared_persistent(root) if persistent else self.prepared(root)
                evidence = Path(manifest["evidence"])
                process, job = Mock(returncode=124, pid=1234), Mock()
                process.poll.return_value = None
                after = self.sample_release(pid=1234)["after"]
                sample = {**after, "payload": "x" * 70000}
                if entry._controller_kind() == "windows-job-object":
                    sample["activeProcesses"] = 1
                else:
                    sample.update(processGroupState="alive", rootExitCode=None)
                cleanup = (sample, after, True, None)
                with patch.object(entry, "RESOURCE_SAMPLE_BYTES", 100000), \
                        patch.object(entry, "_new_controller", return_value=job), \
                        patch.object(entry, "_sample_resources", return_value=sample), \
                        patch.object(entry, "_close_processes", return_value=cleanup) as close, \
                        patch.object(entry.subprocess, "Popen", return_value=process), \
                        patch.object(entry.time, "sleep"), \
                        patch.dict(os.environ, {"CODEX_HOME": str(root / "isolated-home")}):
                    if persistent:
                        record = entry._run_persistent_stage(manifest, 0, None, {}, time.monotonic()+10)
                        path = evidence / "native-receipt-1.json"
                        entry._save_control(path, record)
                    else:
                        result = entry.run(argparse.Namespace(evidence=str(evidence)))
                        path = evidence / "resources.json"
                        self.assertIn("resource-sample-budget-exceeded", result["process"]["failure"])
                    record = entry._read_observer_record(path)
                    self.assertEqual(record["exitCode"], 124)
                    self.assertTrue(record["forced"])
                    self.assertIn("resource-sample-budget-exceeded", record["failure"])
                    self.assertEqual(record["sampleEvidence"]["count"], 2)
                    rows = [row for chunk in record["sampleEvidence"]["chunks"]
                            for row in json.loads((evidence / chunk["path"]).read_bytes())]
                    self.assertEqual(rows, [sample, sample])
                    self.assertTrue(record["sampleEvidence"]["limitExceeded"])
                    close.assert_called_once()
                    record["failure"] = None
                    entry.save(path, record)
                    with self.assertRaisesRegex(ValueError, "cannot claim success"):
                        entry._read_observer_record(path)



    def test_group_stat_bounds(self):
        import io
        from types import SimpleNamespace
        from scripts.observe_codex_entry import _linux_group_members
        def stat(pid=77, pgid=77):
            tail = ["S", "1", str(pgid), "77"] + ["0"] * 15 + ["123"]
            return (str(pid) + " (short ) comm) " + " ".join(tail)).encode()
        for fault in ("none", "other", "race", "read", "oversized", "entries", "time", "members"):
            with self.subTest(fault=fault):
                values = iter([77, 78]) if fault == "race" else None
                getpgid = lambda pid: next(values) if values else (1 if fault in ("other","entries") else 77)
                count = 513 if fault == "entries" else 33 if fault == "members" else 1
                directory = Mock()
                directory.__enter__ = Mock(return_value=iter(SimpleNamespace(name=str(77+i)) for i in range(count)))
                directory.__exit__ = Mock(return_value=False)
                def opened(path, mode):
                    if fault == "read": raise PermissionError()
                    return io.BytesIO(b"x"*4097 if fault == "oversized" else stat(int(path.parent.name)))
                clock = iter([0, 1]) if fault == "time" else None
                with patch.object(entry.sys, "platform", "linux"), \
                        patch.object(entry.os, "scandir", return_value=directory), \
                        patch.object(entry.os, "getpgid", side_effect=getpgid, create=True), \
                        patch.object(Path, "open", opened), \
                        patch.object(entry.time, "monotonic", side_effect=lambda: next(clock) if clock else 0):
                    value = _linux_group_members(77)
                self.assertLess(len(json.dumps(value)), 8192)
                self.assertLessEqual(value["scanned"], 512)
                self.assertLessEqual(len(value["members"]), 32)
                self.assertEqual(value["state"], "observed" if fault in ("none", "other") else "unknown")
                if fault == "none": self.assertEqual(value["members"][0]["starttime"], 123)
                if fault == "other": self.assertEqual(value["members"], [])

    def test_group_probe_timeout(self):
        group = entry.PosixProcessGroup.__new__(entry.PosixProcessGroup)
        group.pgid = 77
        for failure in (None, subprocess.TimeoutExpired("reader", .2), OSError()):
            with patch.object(entry.sys, "platform", "linux"), \
                    patch.object(entry.time, "monotonic", return_value=10), \
                    patch.object(entry.subprocess, "run", side_effect=failure,
                        return_value=argparse.Namespace(returncode=0, stdout=b'{"state":"observed","pgid":77,"members":[]}')) as run:
                value = group.diagnose_members(10.2)
                self.assertLessEqual(run.call_args.kwargs["timeout"], .2 + 1e-9)
                self.assertEqual(value["state"], "unknown" if failure else "observed")
        for platform, deadline in (("win32", 11), ("darwin", 11), ("linux", 10)):
            with patch.object(entry.sys, "platform", platform), \
                    patch.object(entry.time, "monotonic", return_value=10), \
                    patch.object(entry.subprocess, "run") as run:
                self.assertEqual(group.diagnose_members(deadline)["state"], "unknown")
                run.assert_not_called()


class ResourceExecutionBindingTests(unittest.TestCase):
    def manifests(self, root):
        manifest = EntryTests().prepared_persistent(root)
        manifest['nativeVersion'] = 'codex-cli 0.158.0'
        variants = {}
        for controller in ('windows-job-object', 'posix-session-process-group'):
            variants[controller] = {**manifest, 'resourceController': controller,
                                    'resourceEvidenceScope': entry._resource_scope(controller)}
        return variants

    def bind_against_fixture(self, manifest, planned, *, composition=None):
        # Exercise the real admission comparison. Only immutable source reads,
        # schema eligibility and package provenance are synthetic here; this is
        # not a committed case, observed condition or product admission claim.
        from yiyuan_accord import admission
        package = {path: entry.read_regular(Path(manifest['package']) / path)
                   for path in entry._package_hashes(manifest['package'])}
        fixture = entry.read_regular(manifest['case'])
        case_id = composition['case'] if composition else 'resource-fixture'
        case = {'id': case_id, 'scope': 'synthetic-resource-comparison',
                'host': planned['host'], 'entry': planned['entry'],
                'conditions': {'execution': planned},
                'oracleFiles': [planned['runner'], planned['caseFile']]}
        contract = {'acceptance': {'admission': {'cases': [case]}}, 'delivery': {'hostProjections': [
            {'id': 'codex', 'manifest': 'plugins/fixture/.codex-plugin/plugin.json', 'packageSha256': 'f' * 64}]}}
        def read_git(_root, _operation, target):
            return json.dumps(contract).encode() if target.endswith(':product/development.json') else fixture
        with patch.object(admission, 'clean_git_checkout', return_value=True), \
                patch.object(admission, 'evidence_subject', return_value={'revision': 'a' * 40}), \
                patch.object(admission, '_git', side_effect=read_git), \
                patch.object(admission, 'admission_contract_errors', return_value=[]), \
                patch.object(admission, '_definition', return_value='synthetic-definition'), \
                patch.object(admission, '_revision_package_snapshot', return_value={
                    'sha256': 'f' * 64, 'files': {'plugins/fixture/' + path: raw for path, raw in package.items()}}):
            return (entry._composition_binding(manifest, composition) if composition else
                    entry._admission_binding(manifest, case_id))

    def test_nondefault_resources_are_execution_identity_and_windows_stays_legacy(self):
        with tempfile.TemporaryDirectory() as temporary:
            variants = self.manifests(Path(temporary).resolve())
            windows = variants['windows-job-object']
            legacy = {key: value for key, value in windows.items()
                      if key not in ('resourceController', 'resourceEvidenceScope')}
            old = entry._execution_settings(legacy)
            self.assertEqual(entry._execution_settings(windows), old)
            self.assertNotIn('resourceController', old)
            self.assertNotIn('resourceEvidenceScope', old)
            posix = entry._execution_settings(variants['posix-session-process-group'])
            self.assertNotEqual(posix, old)
            self.assertEqual(posix['resourceController'], 'posix-session-process-group')
            self.assertEqual(posix['resourceEvidenceScope'], entry._resource_scope('posix-session-process-group'))

    def test_old_windows_prebinding_rejects_posix_and_explicit_posix_is_accepted(self):
        with tempfile.TemporaryDirectory() as temporary:
            variants = self.manifests(Path(temporary).resolve())
            windows, posix = variants['windows-job-object'], variants['posix-session-process-group']
            old, explicit = entry._execution_settings(windows), entry._execution_settings(posix)
            self.assertEqual(self.bind_against_fixture(windows, old)['execution'], old)
            with self.assertRaisesRegex(ValueError, 'prebound case conditions'):
                self.bind_against_fixture(posix, old)
            self.assertEqual(self.bind_against_fixture(posix, explicit)['execution'], explicit)
            with self.assertRaisesRegex(ValueError, 'prebound case conditions'):
                self.bind_against_fixture(windows, explicit)

    def test_composition_worker_carries_scope_and_rejects_prebound_or_current_drift(self):
        with tempfile.TemporaryDirectory() as temporary:
            variants = self.manifests(Path(temporary).resolve())
            request = EntryTests().composition_request()
            plans = {}
            for controller, manifest in variants.items():
                worker = entry._execution_settings(manifest)
                plans[controller] = {**request['execution'], 'worker': worker,
                    **{key: worker[key] for key in ('runner', 'caseFile', 'caseSha256')}}
                self.assertEqual(self.bind_against_fixture(manifest, plans[controller], composition=request)['execution'],
                                 plans[controller])
            old, explicit = plans['windows-job-object'], plans['posix-session-process-group']
            self.assertNotIn('resourceController', old['worker'])
            self.assertEqual(explicit['worker']['resourceController'], 'posix-session-process-group')
            self.assertNotEqual(old, explicit)
            for current, planned in ((variants['posix-session-process-group'], old),
                                     (variants['windows-job-object'], explicit)):
                with self.subTest(current=current['resourceController']), \
                        self.assertRaisesRegex(ValueError, 'prebound case conditions'):
                    self.bind_against_fixture(current, planned, composition=request)
            malformed = {**variants['posix-session-process-group'], 'resourceEvidenceScope': 'all descendants contained'}
            with self.assertRaisesRegex(ValueError, 'controller binding mismatch'):
                self.bind_against_fixture(malformed, explicit, composition=request)

    def test_preparation_binds_same_resources_before_and_after_fixture_creation(self):
        for composition in (False, True):
            with self.subTest(composition=composition), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary).resolve()
                observations = []
                def bind(manifest, _request):
                    observations.append((manifest['resourceController'], manifest['resourceEvidenceScope'],
                                         (root / 'evidence').exists()))
                    return {'case': 'synthetic-resource-binding'}
                with patch.dict(os.environ, {'CODEX_HOME': str(root / 'home')}), \
                        patch.object(entry, '_entry_guide', return_value='Accord task entry: synthetic'), \
                        patch.object(entry, '_composition_binding' if composition else '_admission_binding', side_effect=bind):
                    manifest = EntryTests().prepared_persistent(root, installed=True, controls={'node': PYTHON},
                        composition=EntryTests().composition_request() if composition else None,
                        admission_case=None if composition else 'synthetic-resource-binding')
                expected = (manifest['resourceController'], manifest['resourceEvidenceScope'])
                self.assertEqual(observations, [(*expected, False), (*expected, True)])

    def test_resource_helper_comes_from_sibling_despite_cached_other_checkout(self):
        import types
        cached = types.ModuleType('scripts.inspect_native_resources')
        cached.native_processes_released = Mock(return_value=True)
        sibling_spec = importlib.util.spec_from_file_location('isolated_candidate_entry', SCRIPT)
        sibling = importlib.util.module_from_spec(sibling_spec)
        with patch.dict(sys.modules, {'scripts.inspect_native_resources': cached}):
            sibling_spec.loader.exec_module(sibling)
            self.assertIsNot(sibling.native_processes_released, cached.native_processes_released)
            self.assertEqual(Path(sibling.native_processes_released.__code__.co_filename).resolve(),
                             SCRIPT.with_name('inspect_native_resources.py').resolve())
            self.assertFalse(sibling._released({'activeProcesses': 1}, 'windows-job-object'))
        cached.native_processes_released.assert_not_called()


class PosixEntryRunnerTests(unittest.TestCase):
    def test_resource_release_requires_bound_scope_and_observed_group_absence(self):
        controller = 'posix-session-process-group'
        manifest = {'resourceController': controller, 'resourceEvidenceScope': entry._resource_scope(controller)}
        after = {'controller': controller, 'activeProcesses': None, 'processGroupState': 'absent',
                 'processGroupId': 1234, 'rootPid': 1234, 'rootExitCode': 0}
        record = {'controller': controller, 'evidenceScope': entry._resource_scope(controller),
                  'exitCode': 0, 'remainingOwnedProcesses': None, 'pid': 1234, 'after': after}
        self.assertTrue(entry._entry_resources_released(record, manifest))
        for changes in ({'processGroupState': 'alive'}, {'processGroupState': 'unobservable'},
                        {'activeProcesses': 0}, {'rootExitCode': None}, {'rootPid': 999},
                        {'observationError': {'type': 'PermissionError'}}):
            with self.subTest(changes=changes):
                changed = {**record, 'after': {**after, **changes}}
                self.assertFalse(entry._entry_resources_released(changed, manifest))
                self.assertFalse(entry._resource_observation(changed, manifest)['releasedWithinScope'])
        for changes in ({'controller': 'windows-job-object'}, {'remainingOwnedProcesses': 0},
                        {'exitCode': 1}, {'pid': 999}, {'evidenceScope': 'all descendants contained'},
                        {'after': None}):
            with self.subTest(changes=changes):
                self.assertFalse(entry._entry_resources_released({**record, **changes}, manifest))

    def test_resource_controller_drift_refuses_before_receipt_and_stage_resources(self):
        for persistent in (False, True):
            with self.subTest(persistent=persistent), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp).resolve()
                fixture = EntryTests()
                manifest = fixture.prepared_persistent(root) if persistent else fixture.prepared(root)
                other = 'posix-session-process-group' if os.name == 'nt' else 'windows-job-object'
                manifest.update(resourceController=other, resourceEvidenceScope=entry._resource_scope(other))
                entry.save(root / 'evidence/manifest.json', manifest)
                marker = []
                with patch.object(entry, '_new_controller') as controller, patch.object(entry.subprocess, 'Popen') as child:
                    with self.assertRaisesRegex(ValueError, 'differs from this host'):
                        if persistent:
                            with self.assertRaisesRegex(ValueError, 'differs from this host'):
                                entry.run_persistent(argparse.Namespace(evidence=manifest['evidence']))
                            entry._run_persistent_stage(manifest, 0, None, {}, time.monotonic()+5,
                                                        preflight_failure=marker)
                        else:
                            entry.run(argparse.Namespace(evidence=manifest['evidence']))
                controller.assert_not_called(); child.assert_not_called()
                self.assertEqual(marker, [True] if persistent else [])
                self.assertFalse((root / 'evidence/run-started.json').exists())

    def test_retained_resource_observation_requires_the_original_stage_receipt(self):
        with tempfile.TemporaryDirectory() as tmp:
            evidence = Path(tmp).resolve()
            controller = 'posix-session-process-group'
            manifest = {'resourceController': controller, 'resourceEvidenceScope': entry._resource_scope(controller)}
            record = {'controller': controller, 'evidenceScope': entry._resource_scope(controller),
                      'exitCode': 0, 'pid': 1234, 'remainingOwnedProcesses': None,
                      'after': {'controller': controller, 'activeProcesses': None, 'processGroupState': 'absent',
                                'processGroupId': 1234, 'rootPid': 1234, 'rootExitCode': 0}}
            path = evidence / 'native-receipt-1.json'
            entry.save(path, record)
            observed = entry._retained_resource_observations(evidence, manifest, [record])[0]
            self.assertTrue(observed['releasedWithinScope'])
            entry.save(path, {**record, 'after': {**record['after'], 'processGroupState': 'alive'}})
            observed = entry._retained_resource_observations(evidence, manifest, [record])[0]
            self.assertFalse(observed['matchesRecordedStage'])
            self.assertFalse(observed['releasedWithinScope'])
            path.unlink()
            self.assertFalse(entry._retained_resource_observations(evidence, manifest, [record])[0]['releasedWithinScope'])

    def assert_reaped_group(self, process, receipt):
        self.assertIsNotNone(process.poll())
        self.assertIsNone(receipt['remainingOwnedProcesses'])
        self.assertEqual(receipt['controller'], 'posix-session-process-group')
        self.assertEqual(receipt['after']['processGroupState'], 'absent')
        self.assertEqual(receipt['after']['rootPid'], process.pid)
        self.assertEqual(receipt['after']['rootExitCode'], process.returncode)
        for field in ('activeProcesses', 'totalProcesses', 'cpuSeconds', 'processes'):
            self.assertIsNone(receipt['after'][field])
        with self.assertRaises(ProcessLookupError):
            os.killpg(process.pid, 0)

    def posix_persistent_runner_uses_real_cli_terminal_and_resume(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            fixture = EntryTests()
            one, two, _ = fixture.control_skills(root)
            manifest = fixture.prepared_persistent(root,
                controls={'exclude_skill': [str(one), str(two)], 'project_doc_max_bytes': 17})
            children, commands = [], []
            real_popen = subprocess.Popen
            code = '''import json,sys
from pathlib import Path
args = sys.argv[1:]
Path(args[args.index('--output-last-message')+1]).write_text('done', encoding='utf-8')
events = [{'type':'thread.started','thread_id':'native-thread'}, {'type':'turn.started'},
 {'type':'item.completed','item':{'type':'agent_message','text':'done'}},
 {'type':'turn.completed','usage':{'input_tokens':100,'cached_input_tokens':0,'output_tokens':1}}]
for event in events: print(json.dumps(event), flush=True)
'''
            def spawn(command, **options):
                self.assertEqual(options.get('start_new_session'), True)
                self.assertNotIn('creationflags', options)
                commands.append(list(command))
                child = real_popen([PYTHON, '-B', '-c', code, *command[1:]], **options)
                children.append(child)
                return child
            with patch.object(entry.subprocess, 'Popen', side_effect=spawn):
                receipts = [entry._run_persistent_stage(manifest, stage,
                    'native-thread' if stage else None, {}, time.monotonic()+10)
                    for stage in (0, 1)]
            self.assertEqual(commands[0], manifest['initialCommand'])
            self.assertIn('resume', commands[1])
            self.assertIn('native-thread', commands[1])
            for child, receipt in zip(children, receipts):
                self.assertTrue(receipt['valid'], receipt)
                self.assertEqual(receipt['terminal'], 'completed')
                self.assertFalse(receipt['forced'])
                self.assert_reaped_group(child, receipt)
                settings = fixture.cli_config_overrides(receipt['command'])
                self.assertEqual(settings['skills.config'], fixture.expected_skill_exclusions(one, two))
                self.assertEqual(settings['project_doc_max_bytes'], '17')
            # Both bound controls and resume command drift remain guarded on POSIX.
            for changes in ('controls', 'command'):
                changed = json.loads(json.dumps(manifest))
                thread = 'native-thread'
                if changes == 'controls':
                    changed['controls']['projectDocMaxBytes'] = 18
                else:
                    changed['stageCommandTemplates'][1].append('--unreviewed')
                with self.subTest(changes=changes), patch.object(entry, '_new_controller') as controller, \
                        patch.object(entry.subprocess, 'Popen') as forbidden:
                    with self.assertRaises(ValueError):
                        entry._run_persistent_stage(changed, 1, thread, {}, time.monotonic()+5)
                controller.assert_not_called(); forbidden.assert_not_called()

    def posix_ephemeral_runner_records_actual_scoped_release(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            manifest = EntryTests().prepared(root)
            real_popen, children = subprocess.Popen, []
            def spawn(command, **options):
                self.assertEqual(command, manifest['command'])
                self.assertIs(options.get('start_new_session'), True)
                self.assertNotIn('creationflags', options)
                child = real_popen([PYTHON, '-B', '-c', 'print("{}")'], **options)
                children.append(child)
                return child
            with patch.dict(os.environ, {'CODEX_HOME': str(root / 'isolated-home')}), \
                    patch.object(entry.subprocess, 'Popen', side_effect=spawn):
                result = entry.run(argparse.Namespace(evidence=manifest['evidence']))
            self.assert_reaped_group(children[0], result['process'])
            self.assertFalse(result['process']['forced'])
            self.assertTrue(result['retainedResourceObservation']['releasedWithinScope'])
            self.assertFalse(result['outputsMatch'])  # This process fixture does no business work.
            launch = json.loads((root / 'evidence/process.json').read_bytes())
            self.assertFalse(launch['jobAssignedBeforeResume'])
            self.assertTrue(launch['newSessionProcessGroup'])

    def posix_persistent_deadline_kills_and_reaps_real_child(self):
        with tempfile.TemporaryDirectory() as tmp:
            manifest = EntryTests().prepared_persistent(Path(tmp).resolve())
            manifest.update(turnTimeoutSeconds=0.2, recoveryTimeoutSeconds=2)
            real_popen, children = subprocess.Popen, []
            def spawn(command, **options):
                child = real_popen([PYTHON, '-B', '-c', 'import time; time.sleep(60)'], **options)
                children.append(child)
                return child
            started = time.monotonic()
            with patch.object(entry.subprocess, 'Popen', side_effect=spawn):
                receipt = entry._run_persistent_stage(manifest, 0, None, {}, started+5)
            self.assertLess(time.monotonic()-started, 3)
            self.assertTrue(receipt['forced'])
            self.assertEqual(receipt['failure'], 'turn-time-or-output-limit')
            self.assertFalse(receipt['valid'])
            self.assert_reaped_group(children[0], receipt)

    def posix_observation_failure_cannot_sign_release_even_after_root_exit(self):
        with tempfile.TemporaryDirectory() as tmp:
            manifest = EntryTests().prepared_persistent(Path(tmp).resolve())
            manifest['recoveryTimeoutSeconds'] = 1
            real_popen, children = subprocess.Popen, []
            controller = entry.PosixProcessGroup()
            def spawn(command, **options):
                child = real_popen([PYTHON, '-B', '-c', 'pass'], **options)
                children.append(child)
                return child
            with patch.object(entry, '_new_controller', return_value=controller), \
                    patch.object(controller, 'sample', side_effect=PermissionError('fixture observation unavailable')), \
                    patch.object(entry.subprocess, 'Popen', side_effect=spawn):
                receipt = entry._run_persistent_stage(manifest, 0, None, {}, time.monotonic()+5)
            self.assertIsNotNone(children[0].poll())
            with self.assertRaises(ProcessLookupError):
                os.killpg(children[0].pid, 0)
            self.assertIsNone(receipt['remainingOwnedProcesses'])
            self.assertFalse(receipt['valid'])
            self.assertEqual(receipt['after']['processGroupState'], 'unobservable')
            self.assertEqual(receipt['failure'], 'resource-release-unobserved')
            self.assertFalse(entry._entry_resources_released(receipt, manifest))

    def posix_cleanup_interrupt_reaps_owned_child_without_signing_receipt(self):
        for phase in ('sample', 'drain'):
            with self.subTest(phase=phase):
                child = subprocess.Popen([PYTHON, '-B', '-c', 'import time; time.sleep(60)'], start_new_session=True)
                controller = entry.PosixProcessGroup()
                controller.attach_and_resume(child)
                target, method = (controller, 'sample') if phase == 'sample' else (entry.time, 'sleep')
                original, interrupted = getattr(target, method), []
                def interrupt_once(*args, **kwargs):
                    if not interrupted:
                        interrupted.append(True)
                        raise KeyboardInterrupt('fixture cleanup interruption')
                    return original(*args, **kwargs)
                try:
                    with patch.object(target, method, side_effect=interrupt_once):
                        with self.assertRaises(KeyboardInterrupt):
                            entry._close_processes(controller, child, 'posix-session-process-group', 2, natural=True)
                    self.assertIsNotNone(child.poll())
                    with self.assertRaises(ProcessLookupError):
                        os.killpg(child.pid, 0)
                finally:
                    if child.poll() is None:
                        controller.terminate()
                    child.wait(timeout=2)
                    controller.close()


# Register actual POSIX syscall cases only where they apply. Shared record and
# failure tests remain discovered everywhere; Windows keeps its native Job case.
if os.name == "posix":
    for case in ('posix_persistent_runner_uses_real_cli_terminal_and_resume',
                 'posix_ephemeral_runner_records_actual_scoped_release',
                 'posix_persistent_deadline_kills_and_reaps_real_child',
                 'posix_observation_failure_cannot_sign_release_even_after_root_exit',
                 'posix_cleanup_interrupt_reaps_owned_child_without_signing_receipt'):
        setattr(PosixEntryRunnerTests, 'test_' + case, getattr(PosixEntryRunnerTests, case))
    for case in ("posix_controller_observes_direct_root_and_never_claims_process_counts",
                 "posix_controller_rejects_unisolated_process_without_signalling_caller_group",
                 "posix_descendant_can_leave_group_and_is_not_counted_as_contained"):
        setattr(EntryTests, "test_" + case, getattr(EntryTests, case))


if __name__ == "__main__":
    unittest.main()
