import argparse
from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import sys

from scripts import observe_codex_lifecycle as lifecycle


class CodexLifecycleTests(unittest.TestCase):
    def fixture(self, root):
        package = root / "package"
        (package / ".codex-plugin").mkdir(parents=True)
        (package / "hooks").mkdir()
        (package / "runtime").mkdir()
        (package / "skills/demo").mkdir(parents=True)
        (package / ".codex-plugin/plugin.json").write_text('{"name":"yiyuan-accord-codex","version":"3.3.0-dev.1"}', encoding="utf-8")
        (package / "hooks/hooks.json").write_text('{"hooks":{}}', encoding="utf-8")
        (package / "runtime/task-checkpoint.cjs").write_text("// fixture", encoding="utf-8")
        (package / "skills/demo/SKILL.md").write_text("---\nname: demo\n---\n", encoding="utf-8")
        marketplace = root / "marketplace.json"
        marketplace.write_text(json.dumps({"name": "yiyuan-accord", "plugins": [{"name": "yiyuan-accord-codex",
            "source": {"source": "local", "path": "./plugins/yiyuan-accord-codex"}}]}), encoding="utf-8")
        codex, node = root / "codex.exe", root / "node.exe"
        codex.write_bytes(b"codex fixture")
        node.write_bytes(b"node fixture")
        protected = root / "protected-config.toml"
        protected.write_text("[projects]\n", encoding="utf-8")
        args = argparse.Namespace(package=str(package.resolve()), evidence=str((root / "evidence").resolve()),
            marketplace_manifest=str(marketplace.resolve()), codex=str(codex.resolve()), node=str(node.resolve()),
            protected_file=[str(protected.resolve())],
            timeout=180, request_timeout=30, recovery_timeout=10)
        lifecycle.prepare(args)
        return args, lifecycle._load(args.evidence)

    def test_prepare_binds_package_binaries_dependencies_and_seven_resources(self):
        with tempfile.TemporaryDirectory() as tmp:
            args, manifest = self.fixture(Path(tmp).resolve())
            self.assertEqual(tuple(manifest["nativeResourceLabels"]), lifecycle.RESOURCE_LABELS)
            self.assertEqual(manifest["packageHashes"], manifest["snapshotHashes"])
            self.assertEqual(manifest["declaredHookRegistrations"], 0)
            self.assertEqual(set(manifest["sourceHashes"]), {"runner", "entry", "rpc", "resources"})
            self.assertEqual(set(manifest["binaryHashes"]), {"codex", "node", "python"})
            self.assertEqual(tuple(manifest["nativeCommandLabels"]), lifecycle.COMMAND_LABELS)
            self.assertEqual(manifest["standaloneSkill"]["role"], "task-owned-fixed-control")
            self.assertEqual(len(manifest["protectedFiles"]), 1)
            self.assertFalse((Path(args.evidence) / "run-started.json").exists())
            self.assertEqual(json.loads((Path(args.evidence) / "workspace/source.json").read_text()), {"total": 140})

    def test_changed_direct_dependency_is_rejected_before_execution(self):
        with tempfile.TemporaryDirectory() as tmp:
            _, manifest = self.fixture(Path(tmp).resolve())
            original = manifest["sourcePaths"]["rpc"]
            manifest["sourcePaths"]["rpc"] = manifest["sourcePaths"]["runner"]
            with self.assertRaisesRegex(ValueError, "prepared source set changed"):
                lifecycle._validate_prebound(manifest)
            manifest["sourcePaths"]["rpc"] = original
            manifest["python"] = manifest["codex"]
            manifest["binaryHashes"]["python"] = manifest["binaryHashes"]["codex"]
            with self.assertRaisesRegex(ValueError, "running Python differs"):
                lifecycle._validate_prebound(manifest)

    def test_owned_environment_does_not_forward_credentials_endpoints_or_proxies(self):
        with tempfile.TemporaryDirectory() as tmp:
            _, manifest = self.fixture(Path(tmp).resolve())
            env = lifecycle._owned_environment(manifest)
            self.assertEqual(env["CODEX_HOME"], manifest["ownedRoots"]["home"])
            self.assertEqual(env["NO_PROXY"], "127.0.0.1,localhost")
            self.assertTrue(env["PATH"].startswith(str(Path(manifest["node"]).parent)))
            for key in ("OPENAI_API_KEY", "OPENAI_BASE_URL", "CODEX_API_KEY", "HTTP_PROXY", "HTTPS_PROXY"):
                self.assertNotIn(key, env)

    def test_provider_path_search_uses_parsed_strings_and_windows_separators(self):
        path = r"C:\owned\standalone-skills\exposure-control\SKILL.md"
        self.assertTrue(lifecycle._contains_path({"tools": [{"path": path}]}, path))
        self.assertTrue(lifecycle._contains_path({"context": "source C:/owned/standalone-skills/exposure-control/SKILL.md"}, path))
        self.assertFalse(lifecycle._contains_path({"context": r"C:\other\SKILL.md"}, path))

    def test_prepare_rejects_nested_evidence_and_run_rejects_changed_owned_home(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            args, manifest = self.fixture(root)
            (Path(manifest["ownedRoots"]["home"]) / "auth.json").write_text("{}", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "prepared owned root changed"):
                lifecycle._validate_prebound(manifest)
            (Path(manifest["ownedRoots"]["home"]) / "auth.json").unlink()
            protected = Path(next(iter(manifest["protectedFiles"])))
            original = protected.read_text(encoding="utf-8")
            protected.write_text(original + "# changed\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "prepared protected file changed"):
                lifecycle._validate_prebound(manifest)
            protected.write_text(original, encoding="utf-8")
            nested = argparse.Namespace(**vars(args))
            nested.evidence = str((Path(args.package) / "evidence").resolve())
            with self.assertRaisesRegex(ValueError, "separate non-nested"):
                lifecycle.prepare(nested)

    def test_attach_failure_kills_suspended_root_and_records_failure(self):
        with tempfile.TemporaryDirectory() as tmp:
            _, manifest = self.fixture(Path(tmp).resolve())
            class Process:
                returncode = None
                def poll(self): return self.returncode
                def kill(self): self.returncode = 1
                def wait(self, timeout=None): return self.returncode
            class Job:
                def attach_and_resume(self, _process): raise RuntimeError("attach failed")
                def terminate(self): pass
                def sample(self): return {"activeProcesses": 0}
                def close(self): pass
            process = Process()
            with patch.object(lifecycle.subprocess, "Popen", return_value=process), \
                    patch.object(lifecycle.subprocess, "CREATE_NO_WINDOW", 0, create=True), \
                    patch.object(lifecycle, "WindowsJob", return_value=Job()), \
                    self.assertRaisesRegex(RuntimeError, "attach failed"):
                lifecycle._run_cli(manifest, "attach-control", ["plugin", "list", "--json"], {},
                                   lifecycle.time.monotonic() + 10)
            self.assertEqual(process.returncode, 1)
            recorded = json.loads((Path(manifest["evidence"]) / "commands/attach-control/record.json").read_text())
            self.assertTrue(recorded["forced"])
            self.assertEqual(recorded["failure"], "job-attach")

    def test_app_attach_failure_kills_suspended_root_and_writes_resource_receipt(self):
        with tempfile.TemporaryDirectory() as tmp:
            _, manifest = self.fixture(Path(tmp).resolve())
            class Process:
                returncode = None
                def poll(self): return self.returncode
                def kill(self): self.returncode = 1
                def wait(self, timeout=None): return self.returncode
            class Job:
                def attach_and_resume(self, _process): raise RuntimeError("attach failed")
                def terminate(self): pass
                def sample(self): return {"activeProcesses": 0}
                def close(self): pass
            process = Process()
            with patch.object(lifecycle.subprocess, "Popen", return_value=process), \
                    patch.object(lifecycle.subprocess, "CREATE_NO_WINDOW", 0, create=True), \
                    patch.object(lifecycle, "WindowsJob", return_value=Job()), \
                    self.assertRaisesRegex(RuntimeError, "attach failed"):
                lifecycle._App(manifest, "discovery", [manifest["codex"], "app-server"], {},
                               lifecycle.time.monotonic() + 10)
            recorded = json.loads((Path(manifest["evidence"]) / "native/discovery/resources.json").read_text())
            self.assertTrue(recorded["forced"])
            self.assertEqual(recorded["failure"], "job-attach")

    def test_inspect_requires_exact_complete_resource_set_and_explicit_facts(self):
        with tempfile.TemporaryDirectory() as tmp:
            args, manifest = self.fixture(Path(tmp).resolve())
            evidence = Path(args.evidence)
            for name in lifecycle.OWNED_ROOTS:
                path = Path(manifest["ownedRoots"][name])
                if path.exists():
                    import shutil
                    shutil.rmtree(path)
            for label in lifecycle.RESOURCE_LABELS:
                root = evidence / "native" / label
                root.mkdir()
                lifecycle.save(root / "resources.json", {"exitCode": 0, "forced": False,
                    "after": {"activeProcesses": 0}})
                (root / "stdout.jsonl").write_text("", encoding="utf-8")
                (root / "stderr.txt").write_text("", encoding="utf-8")
                (root / "requests.jsonl").write_text("", encoding="utf-8")
            paused_thread = "native-paused-thread"
            (evidence / "native/resumed/requests.jsonl").write_text(
                json.dumps({"id": 1, "method": "thread/resume", "params": {"threadId": paused_thread}}) + "\n"
                + json.dumps({"id": 2, "method": "turn/start", "params": {"threadId": paused_thread}}) + "\n",
                encoding="utf-8")
            for label in lifecycle.COMMAND_LABELS:
                root = evidence / "commands" / label
                root.mkdir()
                lifecycle.save(root / "record.json", {"exitCode": 1 if label == "invalid-candidate" else 0,
                    "forced": False, "arguments": ["-c", 'cli_auth_credentials_store="file"'],
                    "after": {"activeProcesses": 0}})
                (root / "stdout.json").write_text("", encoding="utf-8")
                (root / "stderr.txt").write_text("", encoding="utf-8")
            installed = str(Path(manifest["ownedRoots"]["home"]) / "plugins/cache/yiyuan-accord/yiyuan-accord-codex/3.3.0-dev.1")
            (evidence / "commands/package-add/stdout.json").write_text(json.dumps({"installedPath": installed}), encoding="utf-8")
            with (evidence / "retained/provider-requests.jsonl").open("w", encoding="utf-8") as stream:
                for ordinal in range(1, 5):
                    stream.write(json.dumps({"ordinal": ordinal, "request": {"id": ordinal}}) + "\n")
                    lifecycle.save(evidence / "retained" / f"provider-response-{ordinal}.json", {
                        "ordinal": ordinal, "response": {"id": f"resp_fixture_{ordinal}",
                        "output": [{"id": f"msg_fixture_{ordinal}"}]}})
            (evidence / "retained/helper.jsonl").write_text(
                json.dumps({"phase": "request", "request": {"op": "bind", "session_id": paused_thread}}) + "\n"
                + json.dumps({"phase": "request", "request": {"op": "pause", "session_id": paused_thread}}) + "\n"
                + json.dumps({"phase": "response", "op": "status", "result": {}}) + "\n", encoding="utf-8")
            lifecycle.save(evidence / "retained/paused-thread.json", {"threadId": paused_thread})
            source_hash = manifest["initialRootHashes"]["workspace"]["source.json"]
            checkpoint = {"epoch": "bound", "result": "Deliver pending.json only after an explicit later decision",
                "inputs": [{"path": "source.json", "observed": {"present": True, "sha256": source_hash}}],
                "outputs": [{"path": "pending.json", "json": {"/total": 140}}],
                "nextAction": "retain pause and wait for decision", "canContinue": False,
                "reason": "user explicitly paused pending decision"}
            def state(epoch, count):
                return {"mode": "paused", "revision": 2, "epoch": epoch, "checkpoint": checkpoint,
                    "recoveryInputs": {"available": True, "count": count},
                    "inspection": {"inputs": [{"path": "source.json", "current": {"present": True, "sha256": source_hash},
                        "unchanged": True, "stable": True}], "outputs": [{"path": "pending.json",
                        "current": {"present": False}, "matched": False, "stable": True}]}}
            lifecycle.save(evidence / "retained/before-pause.json", state("before", 1))
            for name in ("after-interrupt", "after-exit", "resumed-before-continue"):
                lifecycle.save(evidence / "retained" / (name + ".json"), state("after", 1))
            lifecycle.save(evidence / "retained/after-resume.json", state("after-continue", 2))
            retained_state = {"unfinished.state.json": "hash"}
            lifecycle.save(evidence / "retained/invalid-candidate-preserved.json",
                {"package": manifest["packageHashes"], "state": retained_state})
            lifecycle.save(evidence / "retained/state-after-uninstall.json", retained_state)
            facts = {"failure": None, "modelCalls": 0, "credentialHeaderSeen": False,
                "ownedRootsAbsent": {name: True for name in lifecycle.OWNED_ROOTS},
                "protectedSharedFilesUnchanged": True,
                "sharedSettingsAndSelectionsPreserved": True,
                "protectedFileHashesAfter": manifest["protectedFiles"],
                "installedPathReturned": installed, "loadedObject": {"installedPath": installed,
                    "hookSourcePaths": [str(Path(installed) / "hooks/hooks.json")],
                    "skillPaths": [str(Path(installed) / "skills/demo/SKILL.md")]}}
            for key in ("mechanismComplete", "loopbackListenerClosed", "providerBound",
                    "malformedCandidateRejectedWithoutReplacement", "healthyRetryExact",
                    "nativeUninstallRemovesCacheAndDiscovery", "unfinishedStatePreservedAcrossExitAndUninstall",
                    "exactPackageLoadedAndTrusted", "sessionEndEnabledDisabledContrast",
                    "nativeInterruptInvalidatesReadiness", "nativeResumePreservesPausedBinding",
                    "continueReceiptDoesNotResumeBinding", "selectedPathsDisabledInOwnedProcess"):
                facts[key] = True
            lifecycle.save(evidence / "result.json", facts)
            lifecycle.save(evidence / "run-started.json", {"manifestSha256": lifecycle.digest(evidence / "manifest.json"),
                "nativeResourceLabels": list(lifecycle.RESOURCE_LABELS),
                "nativeCommandLabels": list(lifecycle.COMMAND_LABELS)})
            self.assertEqual(lifecycle.inspect(evidence)["decision"], "pass")
            facts.pop("healthyRetryExact")
            lifecycle.save(evidence / "result.json", facts)
            self.assertEqual(lifecycle.inspect(evidence)["decision"], "fail")

    def test_inspect_rejects_missing_or_extra_native_resource_receipt(self):
        with tempfile.TemporaryDirectory() as tmp:
            args, _ = self.fixture(Path(tmp).resolve())
            evidence = Path(args.evidence)
            for label in lifecycle.RESOURCE_LABELS[:-1]:
                root = evidence / "native" / label
                root.mkdir()
                lifecycle.save(root / "resources.json", {"exitCode": 0, "forced": False,
                    "after": {"activeProcesses": 0}})
            lifecycle.save(evidence / "result.json", {})
            lifecycle.save(evidence / "run-started.json", {"manifestSha256": lifecycle.digest(evidence / "manifest.json"),
                "nativeResourceLabels": list(lifecycle.RESOURCE_LABELS),
                "nativeCommandLabels": list(lifecycle.COMMAND_LABELS)})
            checked = lifecycle.inspect(evidence)
            self.assertEqual(checked["decision"], "fail")
            self.assertEqual(checked["resourceError"], "native resource record set incomplete or invalid")

    def test_cli_returns_nonzero_for_failed_run_or_inspection(self):
        cases = ((["observe_codex_lifecycle.py", "run", "--evidence", "x"], "run", {"failure": "BoundedFailure"}),
                 (["observe_codex_lifecycle.py", "inspect", "--evidence", "x"], "inspect", {"decision": "fail"}))
        for argv, action, result in cases:
            with self.subTest(action=action), patch.object(sys, "argv", argv), \
                    patch.object(lifecycle, action, return_value=result), self.assertRaises(SystemExit) as stopped, \
                    redirect_stdout(io.StringIO()):
                lifecycle.main()
            self.assertEqual(stopped.exception.code, 1)


if __name__ == "__main__":
    unittest.main()
