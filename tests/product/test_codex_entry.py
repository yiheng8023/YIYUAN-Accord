"""Offline oracle and Windows ownership tests; never call a model."""

import argparse
import importlib.util
import json
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
spec = importlib.util.spec_from_file_location("observe_codex_entry", SCRIPT)
entry = importlib.util.module_from_spec(spec)
spec.loader.exec_module(entry)


class EntryTests(unittest.TestCase):
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

    def prepared(self, root, case=None):
        package = root / "package"
        (package / "runtime").mkdir(parents=True)
        (package / "runtime/task-checkpoint.cjs").write_text("// fixture", encoding="utf-8")
        args = argparse.Namespace(package=str(package), evidence=str(root / "evidence"), workspace=str(root / "work"),
                                  codex=PYTHON, node=PYTHON, model="explicit-offline-model",
                                  reasoning="high", timeout=10, windows_sandbox="elevated")
        fake = subprocess.CompletedProcess([], 0, b"app-server --ephemeral --ignore-user-config --dangerously-bypass-hook-trust --sandbox --output-last-message", b"")
        with patch.object(entry.subprocess, "run", return_value=fake) as calls:
            entry.prepare(args, app_server_case=case)
        self.assertEqual(calls.call_count, 2)
        self.assertEqual(calls.call_args_list[0].args[0][-2:], ["app-server" if case is not None else "exec", "--help"])
        self.assertEqual(calls.call_args_list[1].args[0][-1], "--version")
        return entry.load_manifest(args.evidence)

    def installed_listing(self, **changes):
        row = {"pluginId": "yiyuan-accord-codex@yiyuan-accord", "name": "yiyuan-accord-codex",
               "marketplaceName": "yiyuan-accord", "version": "3.3.0-dev.1", "installed": True,
               "enabled": True, "source": {"source": "local", "path": "fixture-marketplace"}}
        row.update(changes)
        return subprocess.CompletedProcess([], 0, json.dumps({"installed": [row]}).encode(), b"")

    def prepared_persistent(self, root, case_path=None, *, native_hooks=False, installed=False):
        package = (root / "home/plugins/cache/yiyuan-accord/yiyuan-accord-codex/3.3.0-dev.1"
                   if installed else root / "package")
        if native_hooks or installed:
            shutil.copytree(SCRIPT.parents[1] / "plugins/yiyuan-accord-codex", package)
        else:
            (package / "runtime").mkdir(parents=True)
            (package / "runtime/task-checkpoint.cjs").write_text("// fixture", encoding="utf-8")
        args = argparse.Namespace(
            package=str(package), evidence=str(root / "evidence"), workspace=str(root / "work"),
            codex=PYTHON, node=shutil.which("node") if native_hooks or installed else PYTHON, model="explicit-offline-model", reasoning="high",
            timeout=600, turn_timeout=180, recovery_timeout=20, windows_sandbox="elevated",
            native_package_hooks=native_hooks, installed_plugin="yiyuan-accord-codex@yiyuan-accord" if installed else None)
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
            entry.prepare(args, persistent_case=entry.load_persistent_case(case_path))
        return entry.load_manifest(args.evidence)

    def test_installed_entry_preserves_native_discovery_trust_and_configuration(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            with patch.dict(os.environ, {"CODEX_HOME": str(root / "home")}):
                manifest = self.prepared_persistent(root, installed=True)
                self.assertEqual(manifest["hookMode"], "installed-plugin")
                self.assertNotIn("nativeHookProjection", manifest)
                self.assertEqual(len(manifest["installedPlugin"]["packageFiles"]), 19)
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
            self.assertEqual(len(expected["SessionStart"]), 2)
            self.assertEqual(sum(len(r["hooks"]) for rows in expected.values() for r in rows), 6)
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
            for change in ("manifest-override", "mcp", "prompt-handler", "shell-command", "null-field", "unknown-event"):
                metadata_path = package / ".codex-plugin/plugin.json"
                original_metadata = metadata_path.read_bytes()
                altered = json.loads(json.dumps(definition))
                if change == "manifest-override":
                    metadata = json.loads(original_metadata)
                    metadata["hooks"] = "./other-hooks.json"
                    entry.save(metadata_path, metadata)
                elif change == "mcp":
                    (package / ".mcp.json").write_text("{}", encoding="utf-8")
                elif change == "prompt-handler":
                    altered["hooks"]["Stop"][0]["hooks"][0]["type"] = "prompt"
                elif change == "shell-command":
                    altered["hooks"]["Stop"][0]["hooks"][0]["command"] += "; echo forged"
                elif change == "null-field":
                    altered["hooks"]["Stop"][0]["hooks"][0]["extra"] = None
                elif change == "unknown-event":
                    altered["hooks"]["Unknown"] = altered["hooks"]["Stop"]
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
            observer.snapshot.return_value = {}
            observer.inspect_stage.return_value = {"files": {}, "decision": "pass"}
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

    def test_native_stage_checks_the_opened_prompt_before_starting_a_process(self):
        with tempfile.TemporaryDirectory() as tmp:
            manifest = self.prepared_persistent(Path(tmp).resolve(), native_hooks=True)
            original = entry._verify_native_stage
            def changed_after_verification(*args):
                bound = original(*args)
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
                actual = subprocess.run('"' + str(shell) + '" /C "' + command + '"', executable=str(shell),
                    cwd=root, capture_output=True, timeout=10)
            else:
                args = ['-NoLogo', '-NoProfile', '-Command'] if kind == 'powershell' else ['-c']
                actual = subprocess.run([str(shell), *args, command], cwd=root, capture_output=True, timeout=10)
            self.assertEqual(actual.returncode, 0, actual.stderr)
            observed = json.loads(actual.stdout)
            self.assertEqual(Path(observed['execPath']).resolve(), renamed)
            self.assertEqual(observed['args'], ['--hook', 'Stop'])

    def test_native_entry_gate_rejects_absent_stale_echoed_truncated_and_late_guidance(self):
        guide = 'Accord task entry: complete current source duties. '
        thread, turn, workspace = 'thread', 'turn', str(Path.cwd())
        core = {'type': 'response_item', 'payload': {'type': 'message', 'role': 'developer',
            'internal_chat_message_metadata_passthrough': {'turn_id': turn, 'content_item_kinds': ['hooks.additional_context']},
            'content': [{'type': 'input_text', 'text': guide + 'Native input receipt: session=thread; epoch=one.'}]}}
        start = [{'type': 'session_meta', 'payload': {'id': thread, 'cwd': workspace}},
                 {'type': 'event_msg', 'payload': {'type': 'task_started', 'turn_id': turn}}]
        action = {'type': 'response_item', 'payload': {'type': 'custom_tool_call'}}
        def check(rows, selected_turn=turn):
            return entry.native_entry_observation('\n'.join(json.dumps(x) for x in rows),
                thread_id=thread, turn_id=selected_turn, workspace=workspace, guide=guide)
        self.assertTrue(check([*start, core, action])['valid'])
        self.assertFalse(check([*start, action])['valid'])
        self.assertFalse(check([*start, action, core])['valid'])
        self.assertFalse(check([*start, core, action], 'another-turn')['valid'])
        for mutation in ('assistant', 'stale', 'truncated'):
            altered = json.loads(json.dumps(core))
            if mutation == 'assistant':
                altered['payload']['role'] = 'assistant'
            elif mutation == 'stale':
                altered['payload']['internal_chat_message_metadata_passthrough']['turn_id'] = 'earlier-turn'
            else:
                altered['payload']['content'][0]['text'] = 'Accord task entry: Native input receipt: session=thread; epoch=one.'
            self.assertFalse(check([*start, altered, action])['valid'], mutation)

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
                actual = subprocess.run('"' + str(shell) + '" /C "' + command + '"', executable=str(shell),
                    cwd=workspace, capture_output=True, timeout=10)
                self.assertEqual(actual.returncode, 0, actual.stderr)
                observed = json.loads(actual.stdout)
                self.assertEqual(Path(observed["execPath"]).resolve(), renamed)
                self.assertEqual(observed["args"], ["--hook", "Stop"])

    def test_native_prepare_rejects_missing_exec_configuration_isolation_before_creating_roots(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            package = root / "package"
            shutil.copytree(SCRIPT.parents[1] / "plugins/yiyuan-accord-codex", package)
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
            with patch.object(entry, "WindowsJob", return_value=job), \
                    patch.object(entry.subprocess, "CREATE_NO_WINDOW", 0, create=True), \
                    patch.object(entry.subprocess, "Popen", return_value=process), \
                    patch.object(entry.time, "sleep"):
                receipt = entry._run_persistent_stage(manifest, 0, None, {}, time.monotonic() - 1)
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


# Register actual POSIX syscall cases only where they apply. Shared record and
# failure tests remain discovered everywhere; Windows keeps its native Job case.
if os.name == "posix":
    for case in ("posix_controller_observes_direct_root_and_never_claims_process_counts",
                 "posix_controller_rejects_unisolated_process_without_signalling_caller_group",
                 "posix_descendant_can_leave_group_and_is_not_counted_as_contained"):
        setattr(EntryTests, "test_" + case, getattr(EntryTests, case))


if __name__ == "__main__":
    unittest.main()
