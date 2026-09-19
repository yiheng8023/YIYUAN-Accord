import argparse
from contextlib import redirect_stdout
import io
import http.client
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import sys
import time

from scripts import observe_codex_lifecycle as lifecycle


class CodexLifecycleTests(unittest.TestCase):
    def resource_record(self, manifest, exit_code=0):
        controller = manifest["resourceController"]
        after = {"activeProcesses": 0}
        if controller == "posix-session-process-group":
            after = {"controller": controller, "activeProcesses": None, "processGroupId": 123,
                     "rootPid": 123, "processGroupState": "absent", "rootExitCode": exit_code}
        return {"controller": controller, "exitCode": exit_code, "forced": False, "after": after}

    def fake_version_probe(self, path, manifest, role, _env, versions):
        version = versions[role]
        root = Path(manifest["evidence"]) / "retained/version-probes" / role
        root.mkdir(parents=True)
        (root / "stdout.txt").write_text(version + "\n", encoding="utf-8")
        (root / "stderr.txt").write_text("", encoding="utf-8")
        lifecycle.save(root / "record.json", {"arguments": [str(path), "--version"],
            "executable": str(path), "sha256": lifecycle.digest(path), "version": version,
            **self.resource_record(manifest)})
        return version

    def fixture(self, root, hot_reload=False, adapter=None, hooks=None, replacement=False,
                prepare=True, versions=("codex-cli 1.0.0", "codex-cli 2.0.0")):
        root.mkdir(parents=True, exist_ok=True)
        package = root / "package"
        (package / ".codex-plugin").mkdir(parents=True)
        (package / "hooks").mkdir()
        (package / "runtime").mkdir()
        (package / "skills/demo").mkdir(parents=True)
        (package / ".codex-plugin/plugin.json").write_text('{"name":"yiyuan-accord-codex","version":"3.3.0-dev.1"}', encoding="utf-8")
        (package / "hooks/hooks.json").write_text(hooks or '{"hooks":{}}', encoding="utf-8")
        (package / "runtime/task-checkpoint.cjs").write_text("// fixture", encoding="utf-8")
        (package / "skills/demo/SKILL.md").write_text("---\nname: demo\n---\n", encoding="utf-8")
        if adapter is not None:
            (package / "adapter.json").write_text(adapter, encoding="utf-8")
        marketplace = root / "marketplace.json"
        marketplace.write_text(json.dumps({"name": "yiyuan-accord", "plugins": [{"name": "yiyuan-accord-codex",
            "source": {"source": "local", "path": "./plugins/yiyuan-accord-codex"}}]}), encoding="utf-8")
        codex, node = root / "codex.exe", root / "node.exe"
        replacement_codex = root / "codex-replacement.exe"
        codex.write_bytes(b"codex fixture")
        if replacement:
            replacement_codex.write_bytes(b"replacement codex fixture")
        node.write_bytes(b"node fixture")
        protected = root / "protected-config.toml"
        protected.write_text("[projects]\n", encoding="utf-8")
        args = argparse.Namespace(package=str(package.resolve()), evidence=str((root / "evidence").resolve()),
            marketplace_manifest=str(marketplace.resolve()), codex=str(codex.resolve()), node=str(node.resolve()),
            replacement_codex=str(replacement_codex.resolve()) if replacement else None,
            protected_file=[str(protected.resolve())],
            timeout=180, request_timeout=30, recovery_timeout=10, hot_reload=hot_reload)
        if prepare:
            if replacement:
                identities = {"source": versions[0], "replacement": versions[1]}
                with patch.object(lifecycle, "_codex_version",
                        side_effect=lambda path, manifest, role, env:
                            self.fake_version_probe(path, manifest, role, env, identities)):
                    lifecycle.prepare(args)
            else:
                lifecycle.prepare(args)
        return args, lifecycle._load(args.evidence) if prepare else None

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
            self.assertEqual(manifest["resourceController"], lifecycle._controller_kind())
            self.assertEqual(len(manifest["protectedFiles"]), 1)
            self.assertFalse((Path(args.evidence) / "run-started.json").exists())
            self.assertEqual(json.loads((Path(args.evidence) / "workspace/source.json").read_text()), {"total": 140})

    def test_manifest_root_is_checked_before_following_variant_paths(self):
        with tempfile.TemporaryDirectory() as tmp:
            args, manifest = self.fixture(Path(tmp).resolve())
            manifest.update(case=lifecycle.HOT_CASE, evidence=str(Path(tmp) / 'unrelated-root'))
            (Path(args.evidence) / 'manifest.json').write_text(json.dumps(manifest), encoding='utf-8')
            with self.assertRaises(ValueError):
                lifecycle._load(args.evidence)
            self.assertFalse((Path(tmp) / 'unrelated-root').exists())

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

    def test_owned_cleanup_removes_readonly_git_objects(self):
        with tempfile.TemporaryDirectory() as tmp:
            owned = Path(tmp).resolve() / "owned"
            pack = owned / ".git/objects/pack/fixture.pack"
            pack.parent.mkdir(parents=True)
            pack.write_bytes(b"task-owned fixture")
            lifecycle.os.chmod(pack, lifecycle.stat.S_IREAD)
            lifecycle._remove_owned_tree(owned)
            self.assertFalse(owned.exists())

    def test_only_the_interrupted_request_may_end_without_a_complete_response(self):
        peer_closed = {"ordinal": 3, "transportStatus": "peer-closed",
                       "response": {"id": "resp_fixture_3", "status": "in_progress", "output": []}}
        self.assertTrue(lifecycle._provider_response_matches(peer_closed, 3))
        for ordinal in (1, 2, 4, 5, 6):
            changed = {**peer_closed, "ordinal": ordinal,
                       "response": {**peer_closed["response"], "id": f"resp_fixture_{ordinal}"}}
            self.assertFalse(lifecycle._provider_response_matches(changed, ordinal))
        self.assertFalse(lifecycle._provider_response_matches({**peer_closed, "transportStatus": "hold-timeout"}, 3))

    def test_hot_reload_freezes_only_existing_version_fields_and_binds_six_responses(self):
        for adapter, changed in ((None, [".codex-plugin/plugin.json"]),
                ('{ "schema": 2, "entry": "unchanged" }\n', [".codex-plugin/plugin.json"]),
                ('{ "packageVersion" : "3.3.0-dev.1", "entry": "unchanged" }\n',
                 [".codex-plugin/plugin.json", "adapter.json"])):
            with self.subTest(adapter=adapter), tempfile.TemporaryDirectory() as tmp:
                args, manifest = self.fixture(Path(tmp).resolve(), hot_reload=True, adapter=adapter)
                hot = manifest["hotReload"]
                self.assertEqual(manifest["case"], lifecycle.HOT_CASE)
                self.assertEqual(hot["changedFiles"], changed)
                self.assertEqual(hot["upgradeVersion"], "3.3.0-dev.1+codex.hot-reload-observation")
                self.assertEqual(tuple(manifest["nativeCommandLabels"]), lifecycle.HOT_COMMAND_LABELS)
                self.assertEqual(tuple(manifest["nativeResourceLabels"]), lifecycle.RESOURCE_LABELS)
                self.assertEqual(manifest["limits"]["providerRequests"], 6)
                lifecycle._validate_prebound(manifest)
                snapshot, upgraded = Path(args.evidence) / "source-package", Path(hot["snapshot"])
                for name in manifest["packageHashes"]:
                    if name not in changed:
                        self.assertEqual((snapshot / name).read_bytes(), (upgraded / name).read_bytes())
                if adapter and "packageVersion" in adapter:
                    self.assertEqual((upgraded / "adapter.json").read_text(),
                        adapter.replace("3.3.0-dev.1", hot["upgradeVersion"]))
                (upgraded / "runtime/task-checkpoint.cjs").write_text("// changed runtime", encoding="utf-8")
                with self.assertRaisesRegex(ValueError, "frozen bytes differ"):
                    lifecycle._load(args.evidence)

    def test_default_episode_cannot_be_relabelled_as_hot_reload_by_result_or_limit(self):
        with tempfile.TemporaryDirectory() as tmp:
            args, manifest = self.fixture(Path(tmp).resolve())
            self.assertNotIn("case", manifest)
            self.assertNotIn("hotReload", manifest)
            manifest["limits"]["providerRequests"] = 6
            lifecycle.save(Path(args.evidence) / "manifest.json", manifest)
            with self.assertRaisesRegex(ValueError, "manifest binding mismatch"):
                lifecycle._load(args.evidence)

    def test_provider_enforces_prepared_four_or_six_response_ceiling(self):
        for hot_reload, ceiling in ((False, 4), (True, 6)):
            with self.subTest(hot_reload=hot_reload), tempfile.TemporaryDirectory() as tmp:
                args, manifest = self.fixture(Path(tmp).resolve(), hot_reload=hot_reload)
                fixture = lifecycle._Fixture(manifest)
                try:
                    for ordinal in range(1, ceiling + 2):
                        connection = http.client.HTTPConnection("127.0.0.1", fixture.port, timeout=5)
                        try:
                            connection.request("POST", "/responses", body=b'{"input":[]}',
                                headers={"Content-Type": "application/json"})
                            response = connection.getresponse()
                            self.assertEqual(response.status, 200 if ordinal <= ceiling else 429)
                            response.read()
                        finally:
                            connection.close()
                finally:
                    fixture.close()
                self.assertEqual(len(fixture.requests), ceiling)
                for ordinal in range(1, ceiling + 1):
                    receipt = json.loads((Path(args.evidence) / "retained" / f"provider-response-{ordinal}.json").read_text(encoding="utf-8"))
                    self.assertTrue(lifecycle._provider_response_matches(receipt, ordinal))

    def test_hot_reload_rejects_same_build_and_duplicate_version_tokens(self):
        with self.assertRaisesRegex(ValueError, "exactly one version field"):
            lifecycle._version_bytes(b'{"version":"old","version":"old"}', "version", "old", "new")
        with tempfile.TemporaryDirectory() as tmp:
            package = Path(tmp).resolve()
            (package / ".codex-plugin").mkdir()
            (package / ".codex-plugin/plugin.json").write_text(
                '{"version":"3.3.0-dev.1+codex.hot-reload-observation"}', encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "distinct original package version"):
                lifecycle._hot_variant(package)

    def test_prepare_binds_distinct_replacement_identity_and_rejects_aliases_or_drift(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            args, manifest = self.fixture(root / "valid", replacement=True)
            binding = manifest["hostReplacement"]
            self.assertEqual(manifest["case"], lifecycle.REPLACEMENT_CASE)
            self.assertEqual(binding["source"]["path"], args.codex)
            self.assertEqual(binding["replacement"]["path"], args.replacement_codex)
            self.assertNotEqual(binding["source"]["sha256"], binding["replacement"]["sha256"])
            self.assertNotEqual(binding["source"]["version"], binding["replacement"]["version"])
            lifecycle._validate_prebound(manifest)
            binding["replacement"]["version"] = "codex-cli forged"
            with self.assertRaisesRegex(ValueError, "version probe receipt differs: replacement"):
                lifecycle._version_probe_records(manifest, binding)
            binding["replacement"]["version"] = "codex-cli 2.0.0"
            Path(args.replacement_codex).write_bytes(b"drifted replacement")
            with self.assertRaisesRegex(ValueError, "prepared Codex executable changed: replacement"):
                lifecycle._validate_prebound(manifest)
            Path(args.replacement_codex).write_bytes(b"replacement codex fixture")
            Path(args.codex).write_bytes(b"drifted source")
            with self.assertRaisesRegex(ValueError, "prepared native binary changed: codex"):
                lifecycle._validate_prebound(manifest)

            args, _ = self.fixture(root / "same-path", replacement=True, prepare=False)
            args.replacement_codex = args.codex
            with self.assertRaisesRegex(ValueError, "different path and bytes"):
                lifecycle.prepare(args)

            args, _ = self.fixture(root / "same-bytes", replacement=True, prepare=False)
            Path(args.replacement_codex).write_bytes(Path(args.codex).read_bytes())
            with self.assertRaisesRegex(ValueError, "different path and bytes"):
                lifecycle.prepare(args)

            args, _ = self.fixture(root / "same-version", replacement=True, prepare=False)
            with patch.object(lifecycle, "_codex_version", side_effect=lambda path, manifest, role, env:
                    self.fake_version_probe(path, manifest, role, env,
                        {"source": "codex-cli 1.0.0", "replacement": "codex-cli 1.0.0"})), \
                    self.assertRaisesRegex(ValueError, "different version"):
                lifecycle.prepare(args)

            args, _ = self.fixture(root / "hot", replacement=True, hot_reload=True, prepare=False)
            with self.assertRaisesRegex(ValueError, "cannot be combined"):
                lifecycle.prepare(args)

    def test_version_probe_uses_owned_controller_minimal_environment_and_separate_receipt(self):
        with tempfile.TemporaryDirectory() as tmp:
            evidence = Path(tmp).resolve()
            for name in (*lifecycle.OWNED_ROOTS, "retained"):
                (evidence / name).mkdir()
            binary = evidence / "fixture-codex.exe"
            binary.write_bytes(b"version probe fixture")
            manifest = {"evidence": str(evidence), "resourceController": lifecycle._controller_kind(),
                "ownedRoots": {name: str(evidence / name) for name in lifecycle.OWNED_ROOTS},
                "limits": {"requestSeconds": 2, "recoverySeconds": 2}}
            after = self.resource_record(manifest)["after"]

            class Process:
                returncode = 0
                def poll(self): return self.returncode
                def wait(self, timeout=None): return self.returncode
                def kill(self): self.returncode = 1

            class Controller:
                def __init__(self): self.attached = False; self.closed = False
                def attach_and_resume(self, _process): self.attached = True
                def terminate(self): pass
                def sample(self): return after
                def close(self): self.closed = True

            process, controller, probe_env = Process(), Controller(), {"PATH": "minimal-probe-path"}
            def popen(arguments, **kwargs):
                self.assertEqual(kwargs["env"], probe_env)
                self.assertEqual(kwargs["cwd"], manifest["ownedRoots"]["workspace"])
                kwargs["stdout"].write(b"codex-cli 1.2.3\n"); kwargs["stdout"].flush()
                return process

            with patch.object(lifecycle, "_new_controller", return_value=controller), \
                    patch.object(lifecycle, "_spawn_options", return_value={}), \
                    patch.object(lifecycle.subprocess, "Popen", side_effect=popen):
                self.assertEqual(lifecycle._codex_version(binary, manifest, "source", probe_env),
                                 "codex-cli 1.2.3")
            self.assertTrue(controller.attached)
            self.assertTrue(controller.closed)
            receipt = json.loads((evidence / "retained/version-probes/source/record.json").read_text())
            self.assertTrue(lifecycle._record_released(receipt, manifest))
            self.assertEqual(receipt["arguments"], [str(binary), "--version"])
            self.assertEqual(receipt["version"], "codex-cli 1.2.3")
            self.assertFalse((evidence / "retained/host-launches.jsonl").exists())

    def test_version_probe_residue_is_retained_then_cleared_without_rebaselining_protected_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            for changes_protected in (False, True):
                with self.subTest(changes_protected=changes_protected):
                    args, _ = self.fixture(Path(tmp).resolve() / str(changes_protected),
                                           replacement=True, prepare=False)
                    def probe(path, manifest, role, env):
                        (Path(manifest['ownedRoots']['home']) / 'native-arg0.txt').write_text('owned residue')
                        if changes_protected:
                            Path(args.protected_file[0]).write_text('changed during version probe')
                        return self.fake_version_probe(path, manifest, role, env,
                            {'source': 'codex-cli 1.0.0', 'replacement': 'codex-cli 2.0.0'})
                    with patch.object(lifecycle, '_codex_version', side_effect=probe):
                        if changes_protected:
                            with self.assertRaisesRegex(ValueError, 'version probe changed a protected file'):
                                lifecycle.prepare(args)
                        else:
                            lifecycle.prepare(args)
                    evidence = Path(args.evidence)
                    residue = json.loads((evidence / 'retained/version-probes/owned-root-residue.json').read_text())
                    self.assertIn('native-arg0.txt', residue['home'])
                    self.assertFalse((evidence / 'home/native-arg0.txt').exists())

    def test_probe_cleanup_records_link_text_without_reading_or_removing_external_targets(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp).resolve()
            owned, external = base / "owned", base / "external"
            owned.mkdir(); external.mkdir()
            outside_file = external / "outside.txt"
            outside_file.write_text("external content", encoding="utf-8")
            outside_dir = external / "directory"
            outside_dir.mkdir(); (outside_dir / "keep.txt").write_text("keep", encoding="utf-8")

            if os.name == "posix":
                ordinary = owned / "ordinary.txt"
                ordinary.write_text("owned", encoding="utf-8")
                os.symlink(outside_file, owned / "file-link")
                os.symlink(outside_dir, owned / "dir-link")
                seen = []
                original_digest = lifecycle.digest
                with patch.object(lifecycle, "digest",
                        side_effect=lambda path: (seen.append(Path(path)), original_digest(path))[1]):
                    inventory = lifecycle._probe_root_inventory(owned)
                self.assertEqual(inventory["file-link"], {"type": "symlink", "target": str(outside_file)})
                self.assertEqual(inventory["dir-link"], {"type": "symlink", "target": str(outside_dir)})
                self.assertIn("ordinary.txt", inventory)
                self.assertNotIn(outside_file, seen)
                self.assertNotIn(outside_dir / "keep.txt", seen)
                lifecycle._clear_probe_root(owned)
                self.assertEqual(list(owned.iterdir()), [])
                self.assertEqual(outside_file.read_text(encoding="utf-8"), "external content")
                self.assertEqual((outside_dir / "keep.txt").read_text(encoding="utf-8"), "keep")
                redirected = base / "redirected-root"
                os.symlink(outside_dir, redirected)
                with self.assertRaisesRegex(ValueError, "ordinary directory required"):
                    lifecycle._probe_root_inventory(redirected)
            else:
                info = type("Info", (), {"st_mode": lifecycle.stat.S_IFLNK, "st_file_attributes": 0})()
                entries = [type("Entry", (), {"name": "file-link", "path": str(owned / "file-link"),
                    "stat": lambda self, follow_symlinks=False: info,
                    "is_symlink": lambda self: True})()]
                class Scan:
                    def __enter__(self): return iter(entries)
                    def __exit__(self, *_args): return False
                with patch.object(lifecycle.os, "scandir", return_value=Scan()), \
                        patch.object(lifecycle, "_probe_lstat", return_value=info), \
                        patch.object(lifecycle, "_probe_symlink_allowed", return_value=True), \
                        patch.object(lifecycle.os, "readlink", return_value=str(outside_file)):
                    inventory = lifecycle._probe_root_inventory(owned)
                self.assertEqual(inventory["file-link"]["target"], str(outside_file))
                with patch.object(lifecycle.os, "scandir", return_value=Scan()), \
                        patch.object(lifecycle, "_probe_lstat", return_value=info), \
                        patch.object(lifecycle, "_probe_symlink_allowed", return_value=True), \
                        patch.object(lifecycle.os, "unlink") as unlink:
                    lifecycle._clear_probe_root(owned)
                unlink.assert_called_once_with(str(owned / "file-link"))
                reparse = type("Info", (), {"st_mode": lifecycle.stat.S_IFDIR,
                    "st_file_attributes": 0x400})()
                entries[0] = type("Entry", (), {"name": "junction", "path": str(owned / "junction"),
                    "stat": lambda self, follow_symlinks=False: reparse,
                    "is_symlink": lambda self: False})()
                with patch.object(lifecycle.os, "scandir", return_value=Scan()), \
                        patch.object(lifecycle, "_probe_lstat", return_value=reparse), \
                        self.assertRaisesRegex(ValueError, "unsupported redirected content"):
                    lifecycle._probe_root_inventory(owned)
                self.assertTrue(outside_file.exists())
                self.assertTrue((outside_dir / "keep.txt").exists())

    def test_shared_callers_keep_their_manifest_contract_and_rejected_launch_owns_no_job(self):
        # Entry inventory and the carrier caller supply their own source bindings.
        self.assertEqual(lifecycle._codex_identity({'codex': 'caller-bound-executable'})['path'],
                         'caller-bound-executable')
        with tempfile.TemporaryDirectory() as tmp:
            args, manifest = self.fixture(Path(tmp).resolve(), replacement=True)
            Path(args.replacement_codex).write_bytes(b'changed before launch')
            with patch.object(lifecycle, '_new_controller') as controller:
                with self.assertRaisesRegex(ValueError, 'prepared Codex executable changed'):
                    lifecycle._run_cli(manifest, 'rejected-before-job', [], {}, 1,
                                       codex_role='replacement')
                controller.assert_not_called()

    def test_replacement_switch_requires_released_source_and_inspects_exact_launch_order(self):
        with tempfile.TemporaryDirectory() as tmp:
            args, manifest = self.fixture(Path(tmp).resolve(), replacement=True)
            evidence = Path(args.evidence)
            resources, commands = {}, {}
            binding = manifest["hostReplacement"]

            def add_launch(area, label, role):
                identity = manifest["hostReplacement"][role]
                arguments = ([identity["path"], "app-server", "-c", "fixture=true"] if area == "native"
                             else [identity["path"], "-c", 'cli_auth_credentials_store="file"', label])
                lifecycle._record_host_launch(manifest, area, label, role, arguments)
                record = {**self.resource_record(manifest), "executable": identity["path"],
                          "hostVersion": identity["version"],
                          "arguments": arguments if area == "native" else arguments[1:]}
                target = evidence / area / label
                target.mkdir()
                lifecycle.save(target / ("resources.json" if area == "native" else "record.json"), record)
                (resources if area == "native" else commands)[label] = record

            for area, label, role in lifecycle.REPLACEMENT_LAUNCH_PLAN[:6]:
                add_launch(area, label, role)
            ledger = evidence / "retained/host-launches.jsonl"
            original_ledger = ledger.read_text(encoding="utf-8")
            damaged = [json.loads(line) for line in original_ledger.splitlines()]
            damaged[0]["area"] = "../outside"
            ledger.write_text("\n".join(json.dumps(row) for row in damaged) + "\n", encoding="utf-8")
            with patch.object(lifecycle, "_launch_record") as read_record, \
                    self.assertRaisesRegex(ValueError, "identity or order differs"):
                lifecycle._activate_host_replacement(manifest, "paused-thread")
            read_record.assert_not_called()
            ledger.write_text(original_ledger, encoding="utf-8")
            interrupted = evidence / "native/interrupted/resources.json"
            original = json.loads(interrupted.read_text(encoding="utf-8"))
            replacement_path = Path(manifest["hostReplacement"]["replacement"]["path"])
            replacement_path.write_bytes(b"replacement changed after prepare")
            with self.assertRaisesRegex(ValueError, "prepared Codex executable changed: replacement"):
                lifecycle._activate_host_replacement(manifest, "paused-thread")
            replacement_path.write_bytes(b"replacement codex fixture")
            changed = json.loads(json.dumps(original))
            if manifest["resourceController"] == "posix-session-process-group":
                changed["after"]["processGroupState"] = "present"
            else:
                changed["after"]["activeProcesses"] = 1
            lifecycle.save(interrupted, changed)
            with self.assertRaisesRegex(RuntimeError, "release unobserved"):
                lifecycle._activate_host_replacement(manifest, "paused-thread")
            lifecycle.save(interrupted, original)
            resources["interrupted"] = original
            lifecycle._activate_host_replacement(manifest, "paused-thread")

            for area, label, role in lifecycle.REPLACEMENT_LAUNCH_PLAN[6:]:
                add_launch(area, label, role)
            Path(args.codex).unlink()
            Path(args.replacement_codex).unlink()
            lifecycle._inspect_host_replacement(manifest, resources, commands, "paused-thread")

            probe = evidence / "retained/version-probes/replacement/record.json"
            probe_record = json.loads(probe.read_text(encoding="utf-8"))
            lifecycle.save(probe, {**probe_record, "version": "codex-cli forged"})
            with self.assertRaisesRegex(ValueError, "version probe receipt differs"):
                lifecycle._inspect_host_replacement(manifest, resources, commands, "paused-thread")
            lifecycle.save(probe, probe_record)

            rows = [json.loads(line) for line in ledger.read_text(encoding="utf-8").splitlines()]
            rows[6]["version"] = manifest["hostReplacement"]["source"]["version"]
            ledger.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "identity or order differs"):
                lifecycle._inspect_host_replacement(manifest, resources, commands, "paused-thread")

    def test_current_input_context_uses_last_developer_receipt_not_historical_path(self):
        first = "Accord task entry: Native input receipt: session=task; epoch=old. use node /old/runtime/task-checkpoint.cjs"
        last = "Accord task entry: Native input receipt: session=task; epoch=new. use node /new/runtime/task-checkpoint.cjs"
        request = {"input": [{"role": "developer", "content": [{"text": first}]},
            {"role": "user", "content": [{"text": first}]},
            {"role": "developer", "content": [{"text": last}]}]}
        self.assertEqual(lifecycle._latest_input_context(request), last)
        self.assertFalse(lifecycle._contains_path(lifecycle._latest_input_context(request), "/old/runtime/task-checkpoint.cjs"))

    def test_hot_reload_inspection_recomputes_packages_turns_trust_and_native_receipts(self):
        import shutil
        with tempfile.TemporaryDirectory() as tmp:
            args, manifest = self.fixture(Path(tmp).resolve(), hot_reload=True,
                hooks='{"hooks":{"UserPromptSubmit":[{"hooks":[{"type":"command","command":"unchanged"}]}]}}')
            evidence, hot = Path(args.evidence), manifest["hotReload"]
            old = str(Path(manifest["ownedRoots"]["home"]) / "plugins/cache/original")
            new = str(Path(manifest["ownedRoots"]["home"]) / "plugins/cache/upgrade")
            thread, source_hash = "paused-thread", manifest["initialRootHashes"]["workspace"]["source.json"]
            key = lifecycle.PLUGIN_ID + ":hooks/hooks.json:user_prompt_submit:0:0"
            trust = {key: {"enabled": True, "trusted_hash": "unchanged-declaration-hash"}}
            def hooks(path):
                return {"data": [{"hooks": [{"key": key, "currentHash": trust[key]["trusted_hash"],
                    "enabled": True, "trustStatus": "trusted", "sourcePath": str(Path(path) / "hooks/hooks.json")}]}]}
            lifecycle.save(evidence / "retained/hooks-before.json", hooks(old))
            argv = [manifest["codex"], "app-server", "-c", "hooks.state=" + lifecycle._toml(trust)]
            lifecycle.save(evidence / "retained/hot-reload-launch.json", {"arguments": argv, "trust": trust})
            resources = {"resumed": {"arguments": argv}}
            checkpoint = {"epoch": "binding-epoch", "result": "Deliver pending.json only after an explicit later decision",
                "nextAction": "retain pause and wait for decision", "canContinue": False,
                "reason": "user explicitly paused pending decision",
                "inputs": [{"path": "source.json", "observed": {"present": True, "sha256": source_hash}}],
                "outputs": [{"path": "pending.json", "json": {"/total": 140}}]}
            def status(epoch, count, turn):
                return {"mode": "paused", "revision": 2, "epoch": epoch, "checkpoint": checkpoint,
                    "recoveryInputs": {"available": True, "count": count}, "currentInputReconciled": False,
                    "hostObservationCurrent": True, "hostObservation": {"turnId": turn},
                    "inspection": {"inputs": [{"path": "source.json", "current": {"present": True, "sha256": source_hash},
                        "unchanged": True, "stable": True}], "outputs": [{"path": "pending.json",
                        "current": {"present": False}, "matched": False, "stable": True}]}}
            prior = status("fourth-input", 2, "fourth-turn")
            current_prior = prior
            inputs = [{"epoch": "original-input", "turnId": "third-turn", "prompt": lifecycle.PROMPT},
                      {"epoch": "fourth-input", "turnId": "fourth-turn", "prompt": "继续。"}]
            request_rows = [{"id": 1, "method": "turn/start", "params": {"threadId": thread}}]
            provider_rows = [{"ordinal": ordinal, "request": {}} for ordinal in range(1, 7)]
            commands, native = {}, []
            previous_after = None
            for index, (label, path, snapshot) in enumerate((
                    ("hot-reload-upgrade", new, Path(hot["snapshot"])),
                    ("hot-reload-rollback", old, evidence / "source-package"))):
                retained = evidence / "retained" / label
                retained.mkdir()
                shutil.copytree(snapshot, retained / "installed-package")
                before_root = retained / "before-install-state"
                if previous_after is None:
                    before_root.mkdir()
                    lifecycle.save(before_root / "task.state.json", {"session": thread, "mode": "paused", "checkpoint": checkpoint})
                    lifecycle.save(before_root / "task.input.json", {"epoch": "fourth-input", "turnId": "fourth-turn",
                        "inputSource": "native-input-event", "nativeInputs": inputs})
                else:
                    shutil.copytree(previous_after, before_root)
                shutil.copytree(before_root, retained / "after-install-state")
                shutil.copytree(before_root, retained / "after-turn-state")
                epoch, turn = f"hot-input-{index}", f"hot-turn-{index}"
                inputs = [*inputs, {"epoch": epoch, "turnId": turn, "source": "native-input-event",
                    "promptSha256": lifecycle.hashlib.sha256(lifecycle.HOT_PROMPTS[index].encode()).hexdigest(),
                    "prompt": lifecycle.HOT_PROMPTS[index]}]
                lifecycle.save(retained / "after-turn-state/task.input.json", {"epoch": epoch, "turnId": turn,
                    "inputSource": "native-input-event", "nativeInputs": inputs})
                after = status(epoch, index + 3, turn)
                lifecycle.save(retained / "observation.json", {"installedPath": path, "threadId": thread,
                    "turnId": turn, "providerOrdinal": index + 5, "beforeTurn": current_prior,
                    "afterTurn": after, "hooks": hooks(path)})
                command_root = evidence / "commands" / label
                command_root.mkdir()
                lifecycle.save(command_root / "stdout.json", {"installedPath": path})
                commands[label] = {"arguments": ["-c", 'cli_auth_credentials_store="file"', "plugin", "add", lifecycle.PLUGIN_ID, "--json"]}
                request_id, hook_id = index * 2 + 2, index * 2 + 3
                request_rows.extend([{"id": request_id, "method": "turn/start", "params": {"threadId": thread,
                    "input": [{"type": "text", "text": lifecycle.HOT_PROMPTS[index]}]}},
                    {"id": hook_id, "method": "hooks/list", "params": {"cwds": [manifest["ownedRoots"]["workspace"]]}}])
                native.extend([{"id": request_id, "result": {"turn": {"id": turn}}},
                    {"method": "turn/completed", "params": {"threadId": thread, "turn": {"id": turn, "status": "completed"}}},
                    {"id": hook_id, "result": hooks(path)}])
                context = f'Accord task entry: Native input receipt: session={thread}; epoch={epoch}. use node "{Path(path) / "runtime/task-checkpoint.cjs"}" --help'
                provider_rows[index + 4]["request"] = {"input": [{"role": "developer", "content": [{"text": context}]}]}
                current_prior, previous_after = after, retained / "after-turn-state"
            request_rows.append({"method": "thread/unsubscribe", "params": {"threadId": thread}})
            native_root = evidence / "native/resumed"
            native_root.mkdir()
            (native_root / "stdout.jsonl").write_text("\n".join(json.dumps(row) for row in native), encoding="utf-8")
            def check():
                lifecycle._inspect_hot_reload(manifest, old, thread, prior, provider_rows, request_rows, commands, resources)
            check()
            # A wrong historical path is rejected even though the new path remains elsewhere in the request.
            original_request = provider_rows[4]["request"]
            provider_rows[4]["request"] = {"input": [*original_request["input"],
                {"role": "developer", "content": [{"text": original_request["input"][0]["content"][0]["text"].replace(new, old)}]}]}
            with self.assertRaisesRegex(ValueError, "current input"):
                check()
            provider_rows[4]["request"] = original_request
            request_rows.insert(1, {"method": "skills/list", "params": {"forceReload": True}})
            with self.assertRaisesRegex(ValueError, "native reload"):
                check()
            request_rows.pop(1)
            upgraded_file = evidence / "retained/hot-reload-upgrade/installed-package/runtime/task-checkpoint.cjs"
            original = upgraded_file.read_bytes()
            upgraded_file.write_bytes(b"wrong installed bytes")
            with self.assertRaisesRegex(ValueError, "identity, CLI or bytes"):
                check()
            upgraded_file.write_bytes(original)
            receipt_file = evidence / "retained/hot-reload-rollback/after-turn-state/task.input.json"
            receipt = json.loads(receipt_file.read_text(encoding="utf-8"))
            receipt["nativeInputs"][0]["prompt"] = "lost original responsibility"
            lifecycle.save(receipt_file, receipt)
            with self.assertRaisesRegex(ValueError, "receipt content"):
                check()

    def test_owned_environment_does_not_forward_credentials_endpoints_or_proxies(self):
        with tempfile.TemporaryDirectory() as tmp:
            _, manifest = self.fixture(Path(tmp).resolve())
            env = lifecycle._owned_environment(manifest)
            self.assertEqual(env["CODEX_HOME"], manifest["ownedRoots"]["home"])
            self.assertEqual(env["NO_PROXY"], "127.0.0.1,localhost")
            if os.name == "posix":
                self.assertEqual(env["HOME"], manifest["ownedRoots"]["home"])
                self.assertEqual(env["TMPDIR"], manifest["ownedRoots"]["temp"])
            self.assertTrue(env["PATH"].startswith(str(Path(manifest["node"]).parent)))
            for key in ("OPENAI_API_KEY", "OPENAI_BASE_URL", "CODEX_API_KEY", "HTTP_PROXY", "HTTPS_PROXY"):
                self.assertNotIn(key, env)

    def test_provider_path_search_uses_parsed_strings_and_windows_separators(self):
        path = r"C:\owned\standalone-skills\exposure-control\SKILL.md"
        self.assertTrue(lifecycle._contains_path({"tools": [{"path": path}]}, path))
        self.assertTrue(lifecycle._contains_path({"context": "source C:/owned/standalone-skills/exposure-control/SKILL.md"}, path))
        self.assertFalse(lifecycle._contains_path({"context": r"C:\other\SKILL.md"}, path))

    def test_platform_spawn_options_preserve_suspended_windows_and_isolated_posix(self):
        with patch.object(lifecycle, "_controller_kind", return_value="windows-job-object"), \
                patch.object(lifecycle.subprocess, "CREATE_NO_WINDOW", 0x08000000, create=True):
            self.assertEqual(lifecycle._spawn_options(), {"creationflags": 0x08000004})
        with patch.object(lifecycle, "_controller_kind", return_value="posix-session-process-group"):
            self.assertEqual(lifecycle._spawn_options(), {"start_new_session": True})

    def test_unknown_or_live_process_receipt_prevents_owned_root_removal(self):
        with tempfile.TemporaryDirectory() as tmp:
            _, manifest = self.fixture(Path(tmp).resolve())
            evidence = Path(manifest["evidence"])
            command = evidence / "commands/marketplace-add"
            command.mkdir()
            self.assertFalse(lifecycle._invoked_processes_released(evidence, manifest))
            record = self.resource_record(manifest)
            lifecycle.save(command / "record.json", record)
            self.assertTrue(lifecycle._invoked_processes_released(evidence, manifest))
            for state in ("alive", "unobservable"):
                if manifest["resourceController"] == "posix-session-process-group":
                    record["after"]["processGroupState"] = state
                else:
                    record["after"]["activeProcesses"] = 1
                lifecycle.save(command / "record.json", record)
                self.assertFalse(lifecycle._invoked_processes_released(evidence, manifest))
            self.assertTrue(Path(manifest["ownedRoots"]["home"]).exists())

    def posix_app_closes_native_stdin_and_observes_limited_release(self):
        with tempfile.TemporaryDirectory() as tmp:
            _, manifest = self.fixture(Path(tmp).resolve())
            app = lifecycle._App(manifest, "discovery", [sys.executable, "-u", "-c",
                "import sys; sys.stdin.buffer.read()"], lifecycle._owned_environment(manifest), time.monotonic() + 10)
            record = app.close()
            self.assertEqual(record["exitCode"], 0)
            self.assertFalse(record["forced"])
            self.assertEqual(record["controller"], "posix-session-process-group")
            self.assertIsNone(record["after"]["activeProcesses"])
            self.assertEqual(record["after"]["processGroupState"], "absent")
            self.assertTrue(record["readerStopped"])
            self.assertEqual(app.close(), record)

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
                    patch.object(lifecycle, "_new_controller", return_value=Job()), \
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
                    patch.object(lifecycle, "_new_controller", return_value=Job()), \
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
                lifecycle.save(root / "resources.json", self.resource_record(manifest))
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
                lifecycle.save(root / "record.json", {**self.resource_record(manifest, 1 if label == "invalid-candidate" else 0),
                    "arguments": ["-c", 'cli_auth_credentials_store="file"']})
                (root / "stdout.json").write_text("", encoding="utf-8")
                (root / "stderr.txt").write_text("", encoding="utf-8")
            installed = str(Path(manifest["ownedRoots"]["home"]) / "plugins/cache/yiyuan-accord/yiyuan-accord-codex/3.3.0-dev.1")
            (evidence / "commands/package-add/stdout.json").write_text(json.dumps({"installedPath": installed}), encoding="utf-8")
            package_skill_paths = sorted(lifecycle._expected_skill_paths(manifest, installed))
            skill_catalog = {"data": [{"skills": [
                {"name": "exposure-control", "path": manifest["standaloneSkill"]["path"], "enabled": True},
                *[{"name": Path(path).parent.name, "path": path, "enabled": True} for path in package_skill_paths]]}]}
            lifecycle.save(evidence / "retained/skills-before.json", skill_catalog)
            with (evidence / "retained/provider-requests.jsonl").open("w", encoding="utf-8") as stream:
                for ordinal in range(1, 5):
                    stream.write(json.dumps({"ordinal": ordinal, "request": {"id": ordinal}}) + "\n")
                    lifecycle.save(evidence / "retained" / f"provider-response-{ordinal}.json", {
                        "ordinal": ordinal, "transportStatus": "completed",
                        "response": {"id": f"resp_fixture_{ordinal}", "status": "completed",
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
                "sourceHashAfter": source_hash,
                "installedPathReturned": installed, "loadedObject": {"installedPath": installed,
                    "hookSourcePaths": [str(Path(installed) / "hooks/hooks.json")],
                    "skillPaths": package_skill_paths}}
            for key in ("mechanismComplete", "loopbackListenerClosed", "providerBound",
                    "malformedCandidateRejectedWithoutReplacement", "healthyRetryExact",
                    "nativeUninstallRemovesCacheAndDiscovery", "unfinishedStatePreservedAcrossExitAndUninstall",
                    "exactPackageLoadedAndTrusted", "sessionEndEnabledDisabledContrast",
                    "nativeInterruptInvalidatesReadiness", "nativeResumePreservesPausedBinding",
                    "continueReceiptDoesNotResumeBinding", "selectedPathsDisabledInOwnedProcess", "standaloneCatalogEntryAbsent"):
                facts[key] = True
            facts.update(resourceController=manifest["resourceController"],
                         resourceEvidenceScope=manifest["resourceEvidenceScope"])
            lifecycle.save(evidence / "result.json", facts)
            lifecycle.save(evidence / "run-started.json", {"manifestSha256": lifecycle.digest(evidence / "manifest.json"),
                "nativeResourceLabels": list(lifecycle.RESOURCE_LABELS),
                "nativeCommandLabels": list(lifecycle.COMMAND_LABELS), "resourceController": manifest["resourceController"]})
            self.assertEqual(lifecycle.inspect(evidence)["decision"], "pass")
            for invalid in ("missing", "disabled"):
                changed_catalog = json.loads(json.dumps(skill_catalog))
                if invalid == "missing": changed_catalog["data"][0]["skills"].pop()
                else: changed_catalog["data"][0]["skills"][-1]["enabled"] = False
                lifecycle.save(evidence / "retained/skills-before.json", changed_catalog)
                self.assertEqual(lifecycle.inspect(evidence)["decision"], "fail")
            lifecycle.save(evidence / "retained/skills-before.json", skill_catalog)
            provider_file = evidence / "retained/provider-requests.jsonl"
            original_provider = provider_file.read_text(encoding="utf-8")
            leaked = [json.loads(line) for line in original_provider.splitlines()]
            leaked[0]["request"]["instructions"] = "Available Skill: exposure-control"
            provider_file.write_text("\n".join(json.dumps(row) for row in leaked), encoding="utf-8")
            self.assertEqual(lifecycle.inspect(evidence)["decision"], "fail")
            provider_file.write_text(original_provider, encoding="utf-8")
            facts["sourceHashAfter"] = "different-source"
            lifecycle.save(evidence / "result.json", facts)
            self.assertEqual(lifecycle.inspect(evidence)["decision"], "fail")
            facts["sourceHashAfter"] = source_hash
            facts.pop("healthyRetryExact")
            lifecycle.save(evidence / "result.json", facts)
            self.assertEqual(lifecycle.inspect(evidence)["decision"], "fail")

    def test_inspect_rejects_missing_or_extra_native_resource_receipt(self):
        with tempfile.TemporaryDirectory() as tmp:
            args, manifest = self.fixture(Path(tmp).resolve())
            evidence = Path(args.evidence)
            for label in lifecycle.RESOURCE_LABELS[:-1]:
                root = evidence / "native" / label
                root.mkdir()
                lifecycle.save(root / "resources.json", self.resource_record(manifest))
            lifecycle.save(evidence / "result.json", {"resourceController": manifest["resourceController"],
                "resourceEvidenceScope": manifest["resourceEvidenceScope"]})
            lifecycle.save(evidence / "run-started.json", {"manifestSha256": lifecycle.digest(evidence / "manifest.json"),
                "nativeResourceLabels": list(lifecycle.RESOURCE_LABELS),
                "nativeCommandLabels": list(lifecycle.COMMAND_LABELS), "resourceController": manifest["resourceController"]})
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


# This real-process case is applicable only to POSIX; no skip or empty Windows
# pass stands in for its syscalls. All shared lifecycle tests remain registered.
if os.name == "posix":
    CodexLifecycleTests.test_posix_app_closes_native_stdin_and_observes_limited_release = (
        CodexLifecycleTests.posix_app_closes_native_stdin_and_observes_limited_release)


if __name__ == "__main__":
    unittest.main()
