"""Prepare, run and inspect one bounded no-model Codex package lifecycle episode.

The runner uses only task-owned CODEX_HOME, marketplace, workspace, state and
temporary roots.  ``prepare`` freezes every executable source before ``run``;
``run`` is exclusive and retains raw native traffic; ``inspect`` never repairs
or fills missing observations.  This is a mechanism observation, not Agent
behaviour, Desktop/IDE equivalence, product value or release acceptance.
Windows uses pre-execution Job containment. POSIX uses a new session/process
group and observes direct-child exit and group disappearance only; descendants
can escape that group. Controller identity and this evidence limit are frozen
at preparation and retained in execution/inspection. Unknown or live process
post-state retains owned roots rather than claiming cleanup.
"""

from __future__ import annotations

import argparse
import hashlib
import http.server
import json
import os
from pathlib import Path
import queue
import re
import shutil
import stat
import subprocess
import sys
import threading
import time

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.codex_rpc import BoundedRpc
from scripts.inspect_native_resources import native_processes_released, read_native_resource_records
from scripts.observe_codex_entry import PosixProcessGroup, WindowsJob, digest, read_regular, save


SCHEMA = "accord-codex-lifecycle/v1"
PLUGIN_ID = "yiyuan-accord-codex@yiyuan-accord"
RESOURCE_LABELS = (
    "discovery", "end-enabled", "end-disabled", "interrupted", "resumed",
    "restored-exposure", "after-remove",
)
COMMAND_LABELS = ("marketplace-add", "package-add", "invalid-candidate", "healthy-retry",
                  "package-remove", "package-list-after-remove")
HOT_CASE = "loaded-accord-paused-thread-upgrade-rollback/v1"
HOT_BUILD = "codex.hot-reload-observation"
HOT_COMMAND_LABELS = (*COMMAND_LABELS, "hot-reload-upgrade", "hot-reload-rollback")
HOT_PROMPTS = ("保持已绑定任务暂停；观察插件新构建生效。", "保持已绑定任务暂停；观察插件原构建恢复。")
OWNED_ROOTS = ("home", "marketplace", "workspace", "state", "temp")
PROMPT = "本地材料已提供。保持暂停，不生成 pending.json，也不修改原始材料。"


def _controller_kind():
    if os.name == "nt":
        return "windows-job-object"
    if os.name == "posix":
        return "posix-session-process-group"
    raise ValueError("lifecycle process control requires Windows or POSIX")


def _new_controller():
    return WindowsJob() if _controller_kind() == "windows-job-object" else PosixProcessGroup()


def _spawn_options():
    if _controller_kind() == "windows-job-object":
        return {"creationflags": subprocess.CREATE_NO_WINDOW | 4}  # CREATE_SUSPENDED
    return {"start_new_session": True}


def _resource_scope(controller):
    if controller == "windows-job-object":
        return "Windows Job assigned before execution; Job process counts and working sets"
    return "POSIX direct child exit and same process group only; escaped descendants, process counts, CPU and memory unobserved; no kill-on-close guarantee"


def _released(sample):
    return native_processes_released(sample, sample.get("controller", "windows-job-object"))


def _resource_record(manifest, process, forced, after, failure=None):
    controller = manifest.get("resourceController", "windows-job-object")
    state = ("released-within-controller-scope" if _released(after) else
             "not-started" if process is None else
             "unobservable" if after.get("processGroupState") in {"unobservable", "not-started"} else "still-alive")
    return {"exitCode": process.returncode if process else None, "forced": forced,
            "failure": failure, "after": after, "controller": controller,
            "evidenceScope": _resource_scope(controller), "cleanupState": state}


def _record_released(record, manifest):
    if not isinstance(record, dict) or not isinstance(record.get("after"), dict):
        return False
    controller = manifest.get("resourceController", "windows-job-object")
    return (record.get("controller", "windows-job-object") == controller
            and type(record.get("exitCode")) is int
            and type(record.get("forced")) is bool
            and record.get("readerStopped", True) is True
            and (controller != "posix-session-process-group"
                 or record["exitCode"] == record["after"].get("rootExitCode"))
            and native_processes_released(record.get("after"), controller))


def _invoked_processes_released(evidence, manifest):
    # Never remove the owned workspace/home beneath a still alive or unknown
    # invocation. Missing receipts do not establish release.
    for area, filename in (("native", "resources.json"), ("commands", "record.json")):
        for directory in (Path(evidence) / area).iterdir():
            if directory.is_dir():
                try:
                    record = json.loads(read_regular(directory / filename))
                    if not _record_released(record, manifest):
                        return False
                except (OSError, ValueError, TypeError):
                    return False
    return True


def _regular_file(path):
    path = Path(path).resolve(strict=True)
    info = path.lstat()
    if (not stat.S_ISREG(info.st_mode) or path.is_symlink()
            or getattr(info, "st_file_attributes", 0) & 0x400):
        raise ValueError("ordinary file required: " + str(path))
    return path


def _ordinary_dir(path):
    path = Path(path).absolute()
    if path.resolve(strict=True) != path or path.is_symlink():
        raise ValueError("ordinary directory required: " + str(path))
    return path


def _validate_tree(root):
    root = _ordinary_dir(root)
    for path in root.rglob("*"):
        info = path.lstat()
        if (path.is_symlink() or getattr(info, "st_file_attributes", 0) & 0x400
                or root not in path.resolve(strict=True).parents):
            raise ValueError("package tree contains redirected content")
        if path.is_file() and (not stat.S_ISREG(info.st_mode) or info.st_nlink != 1):
            raise ValueError("package tree contains non-ordinary file")
    return root


def _tree_hashes(root):
    root = _validate_tree(root)
    result = {}
    for path in sorted(root.rglob("*"), key=lambda value: value.relative_to(root).as_posix()):
        if path.is_file():
            result[path.relative_to(root).as_posix()] = digest(path)
    if not result:
        raise ValueError("package cannot be empty")
    return result


def _version_bytes(data, field, old, new):
    document = json.loads(data)
    if document.get(field) != old:
        raise ValueError("hot-reload version field differs")
    pattern = rb'("' + field.encode("ascii") + rb'"\s*:\s*)' + re.escape(json.dumps(old).encode())
    changed, count = re.subn(pattern, lambda match: match[1] + json.dumps(new).encode(), data)
    if count != 1 or json.loads(changed) != {**document, field: new}:
        raise ValueError("hot-reload requires exactly one version field")
    return changed


def _hot_variant(snapshot):
    """Change version tokens only; do not add product fields or runtime hooks."""
    path = Path(snapshot) / ".codex-plugin/plugin.json"
    old = json.loads(read_regular(path)).get("version")
    if not isinstance(old, str) or not old:
        raise ValueError("hot-reload requires an original package version")
    new = old.split("+", 1)[0] + "+" + HOT_BUILD
    if old == new:
        raise ValueError("hot-reload requires a distinct original package version")
    changes = {".codex-plugin/plugin.json": _version_bytes(read_regular(path), "version", old, new)}
    adapter = Path(snapshot) / "adapter.json"
    if adapter.exists() and "packageVersion" in json.loads(read_regular(adapter)):
        changes["adapter.json"] = _version_bytes(read_regular(adapter), "packageVersion", old, new)
    return old, new, changes


def _hot_binding(manifest):
    root = Path(manifest["evidence"])
    hot = manifest.get("hotReload")
    if manifest.get("case") != HOT_CASE:
        if "case" in manifest or hot is not None:
            raise ValueError("unknown lifecycle case")
        return None
    old, new, changes = _hot_variant(root / "source-package")
    if (not isinstance(hot, dict) or set(hot) != {"originalVersion", "upgradeVersion", "snapshot", "hashes", "changedFiles", "prompts"}
            or hot["originalVersion"] != old or hot["upgradeVersion"] != new
            or hot["snapshot"] != str(root / "hot-reload-package")
            or hot["changedFiles"] != sorted(changes) or hot["prompts"] != list(HOT_PROMPTS)):
        raise ValueError("hot-reload case binding mismatch")
    original = _tree_hashes(root / "source-package")
    upgraded = _tree_hashes(hot["snapshot"])
    expected = {**original, **{name: hashlib.sha256(data).hexdigest() for name, data in changes.items()}}
    if original != manifest["snapshotHashes"] or upgraded != expected or hot["hashes"] != expected:
        raise ValueError("hot-reload frozen bytes differ")
    for name in original:
        expected_bytes = changes.get(name, read_regular(root / "source-package" / name))
        if read_regular(Path(hot["snapshot"]) / name) != expected_bytes:
            raise ValueError("hot-reload changed non-version bytes")
    return hot


def _latest_input_context(request):
    contexts = []
    for item in request.get("input", []):
        if isinstance(item, dict) and item.get("role") == "developer":
            for content in item.get("content", []):
                if isinstance(content, dict) and isinstance(content.get("text"), str):
                    if "Accord task entry:" in content["text"] and "Native input receipt: session=" in content["text"]:
                        contexts.append(content["text"])
    return contexts[-1] if contexts else ""


def _declared_hook_count(package):
    document = json.loads(read_regular(Path(package) / "hooks/hooks.json"))
    try:
        return sum(len(item["hooks"]) for items in document["hooks"].values() for item in items)
    except (KeyError, TypeError):
        raise ValueError("invalid package Hook declaration") from None


def _validate_marketplace_manifest(path):
    document = json.loads(read_regular(path))
    try:
        plugins = document["plugins"]
        source = plugins[0]["source"]
        if (document["name"] != "yiyuan-accord" or len(plugins) != 1
                or plugins[0]["name"] != "yiyuan-accord-codex"
                or source != {"source": "local", "path": "./plugins/yiyuan-accord-codex"}):
            raise ValueError
    except (KeyError, TypeError, IndexError, ValueError):
        raise ValueError("marketplace manifest must select only the task-owned Accord package") from None
    return document


def _toml(value):
    if isinstance(value, dict):
        return "{" + ",".join(json.dumps(str(k)) + "=" + _toml(v) for k, v in value.items()) + "}"
    if isinstance(value, list):
        return "[" + ",".join(_toml(v) for v in value) + "]"
    if isinstance(value, bool):
        return "true" if value else "false"
    return json.dumps(value)


def _hook_rows(result):
    try:
        return [hook for group in result["data"] for hook in group["hooks"]]
    except (KeyError, TypeError):
        raise ValueError("invalid native hook listing") from None


def _skill_rows(result):
    try:
        return [skill for group in result["data"] for skill in group["skills"]]
    except (KeyError, TypeError):
        raise ValueError("invalid native skill listing") from None


def _strings(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for item in value.values():
            yield from _strings(item)
    elif isinstance(value, list):
        for item in value:
            yield from _strings(item)


def _contains_path(value, path):
    target = str(path).replace("\\", "/").casefold()
    return any(target in text.replace("\\", "/").casefold() for text in _strings(value))


def _checkpoint_matches(state, source_hash, recovery_count=None):
    try:
        checkpoint = state["checkpoint"]
        inputs, outputs = checkpoint["inputs"], checkpoint["outputs"]
        inspected_inputs, inspected_outputs = state["inspection"]["inputs"], state["inspection"]["outputs"]
        return (state["mode"] == "paused" and state["revision"] == 2
            and (recovery_count is None or state["recoveryInputs"] == {"available": True, "count": recovery_count})
            and checkpoint["result"] == "Deliver pending.json only after an explicit later decision"
            and checkpoint["nextAction"] == "retain pause and wait for decision"
            and checkpoint["canContinue"] is False and checkpoint["reason"] == "user explicitly paused pending decision"
            and len(inputs) == len(outputs) == len(inspected_inputs) == len(inspected_outputs) == 1
            and inputs[0]["path"] == inspected_inputs[0]["path"] == "source.json"
            and inputs[0]["observed"] == {"present": True, "sha256": source_hash}
            and inspected_inputs[0]["current"] == {"present": True, "sha256": source_hash}
            and inspected_inputs[0]["unchanged"] is True and inspected_inputs[0]["stable"] is True
            and outputs[0] == {"path": "pending.json", "json": {"/total": 140}}
            and inspected_outputs[0]["path"] == "pending.json"
            and inspected_outputs[0]["current"] == {"present": False}
            and inspected_outputs[0]["matched"] is False and inspected_outputs[0]["stable"] is True)
    except (KeyError, TypeError, IndexError):
        return False


def _source_paths():
    return {
        "runner": Path(__file__).resolve(),
        "entry": ROOT / "scripts/observe_codex_entry.py",
        "rpc": ROOT / "scripts/codex_rpc.py",
        "resources": ROOT / "scripts/inspect_native_resources.py",
    }


def _remaining(deadline):
    remaining = deadline - time.monotonic()
    if remaining <= 0:
        raise TimeoutError("whole lifecycle deadline exceeded")
    return remaining


def _root_hashes(path):
    path = _ordinary_dir(path)
    return _tree_hashes(path) if any(path.iterdir()) else {}


def _remove_owned_tree(path):
    root = _validate_tree(path)

    def readonly_retry(function, failed, error):
        target = Path(failed).absolute()
        if not target.is_relative_to(root):
            raise error
        target = _regular_file(target)
        info = target.stat()
        if os.name != "nt" or not getattr(info, "st_file_attributes", 0) & 1:
            raise error
        os.chmod(target, info.st_mode | stat.S_IWRITE)
        function(target)

    # https://docs.python.org/3/library/shutil.html#rmtree-example
    if sys.version_info >= (3, 12):
        shutil.rmtree(root, onexc=readonly_retry)
    else:
        shutil.rmtree(root, onerror=lambda function, failed, info: readonly_retry(function, failed, info[1]))


def _provider_response_matches(receipt, ordinal):
    response = receipt.get("response", {})
    transport = receipt.get("transportStatus")
    if receipt.get("ordinal") != ordinal or response.get("id") != f"resp_fixture_{ordinal}":
        return False
    if ordinal == 3 and transport == "peer-closed":
        return True  # Native interruption is checked separately.
    output = response.get("output")
    return (transport == "completed" and response.get("status") == "completed"
            and isinstance(output, list) and len(output) == 1
            and output[0].get("id") == f"msg_fixture_{ordinal}")


def _owned_environment(manifest):
    # Pass only host process essentials. Provider endpoints, proxies, tokens and
    # unrelated credentials from the launching shell cannot reach the fixture.
    allowed = {
        "SYSTEMROOT", "WINDIR", "COMSPEC", "PATH", "PATHEXT", "USERPROFILE",
        "HOMEDRIVE", "HOMEPATH", "APPDATA", "LOCALAPPDATA", "PROGRAMDATA",
        "PROGRAMFILES", "PROGRAMFILES(X86)", "PROGRAMW6432", "COMMONPROGRAMFILES",
        "COMMONPROGRAMFILES(X86)", "COMMONPROGRAMW6432", "PROCESSOR_ARCHITECTURE",
        "NUMBER_OF_PROCESSORS", "OS",
    }
    env = {key: value for key, value in os.environ.items() if key.upper() in allowed}
    bound_node = str(Path(manifest["node"]).parent)
    env["PATH"] = bound_node + os.pathsep + env.get("PATH", "")
    env.update(CODEX_HOME=manifest["ownedRoots"]["home"], CODEX_SQLITE_HOME=manifest["ownedRoots"]["home"],
        YIYUAN_ACCORD_TASK_STATE_DIR=manifest["ownedRoots"]["state"], TEMP=manifest["ownedRoots"]["temp"],
        TMP=manifest["ownedRoots"]["temp"], NO_PROXY="127.0.0.1,localhost", no_proxy="127.0.0.1,localhost",
        GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL=os.devnull, GIT_TERMINAL_PROMPT="0")
    if os.name == "posix":
        # No inherited HOME/XDG roots, proxy, provider or credential variables.
        home = manifest["ownedRoots"]["home"]
        env.update(HOME=home, XDG_CONFIG_HOME=str(Path(home) / "config"),
            XDG_CACHE_HOME=str(Path(home) / "cache"), XDG_DATA_HOME=str(Path(home) / "data"),
            TMPDIR=manifest["ownedRoots"]["temp"], LANG="C", LC_ALL="C", PYTHONUTF8="1")
    return env


def prepare(args):
    controller = _controller_kind()
    evidence = Path(args.evidence).absolute()
    package = _ordinary_dir(args.package)
    marketplace_manifest = _regular_file(args.marketplace_manifest)
    _validate_marketplace_manifest(marketplace_manifest)
    codex, node = _regular_file(args.codex), _regular_file(args.node)
    python = _regular_file(sys.executable)
    protected = [_regular_file(path) for path in args.protected_file]
    if not protected or len({str(path) for path in protected}) != len(protected):
        raise ValueError("at least one distinct protected file must be bound")
    if evidence.exists() or not evidence.parent.is_dir() or evidence.parent.resolve() != evidence.parent:
        raise ValueError("evidence must be a fresh root with an ordinary parent")
    if evidence == package or package in evidence.parents or evidence in package.parents:
        raise ValueError("evidence and package must be separate non-nested roots")
    _validate_tree(package)
    if node.name.lower() not in {"node", "node.exe"}:
        raise ValueError("bind the Node executable used by package Hooks")
    if not 1 <= args.timeout <= 1800 or not 1 <= args.request_timeout <= 120 or not 1 <= args.recovery_timeout <= 120:
        raise ValueError("invalid lifecycle deadlines")
    variant = _hot_variant(package) if getattr(args, "hot_reload", False) else None
    evidence.mkdir()
    for name in (*OWNED_ROOTS, "native", "commands", "retained"):
        (evidence / name).mkdir()
    snapshot = evidence / "source-package"
    shutil.copytree(package, snapshot)
    hot = None
    if variant is not None:
        old, new, changes = variant
        upgrade = evidence / "hot-reload-package"
        shutil.copytree(snapshot, upgrade)
        for name, data in changes.items():
            (upgrade / name).write_bytes(data)
        hot = {"originalVersion": old, "upgradeVersion": new, "snapshot": str(upgrade),
               "hashes": _tree_hashes(upgrade), "changedFiles": sorted(changes), "prompts": list(HOT_PROMPTS)}
    market = evidence / "marketplace"
    (market / ".agents/plugins").mkdir(parents=True)
    (market / "plugins").mkdir()
    shutil.copy2(marketplace_manifest, market / ".agents/plugins/marketplace.json")
    shutil.copytree(snapshot, market / "plugins/yiyuan-accord-codex")
    workspace = evidence / "workspace"
    (workspace / "source.json").write_text('{"total":140}\n', encoding="utf-8")
    standalone_root = evidence / "standalone-skills"
    standalone = standalone_root / "exposure-control"
    standalone.mkdir(parents=True)
    (standalone / "SKILL.md").write_text(
        "---\nname: exposure-control\ndescription: Task-owned lifecycle exposure control; never user configuration.\n---\n"
        "# Exposure control\n\nThis fixed sample exists only for a no-model process-scoped exposure contrast.\n",
        encoding="utf-8")
    sources = _source_paths()
    manifest = {
        "schema": SCHEMA,
        "evidence": str(evidence),
        "package": str(package),
        "packageHashes": _tree_hashes(package),
        "declaredHookRegistrations": _declared_hook_count(package),
        "snapshotHashes": _tree_hashes(snapshot),
        "marketplaceManifest": str(marketplace_manifest),
        "marketplaceManifestSha256": digest(marketplace_manifest),
        "codex": str(codex), "node": str(node), "python": str(python),
        "binaryHashes": {"codex": digest(codex), "node": digest(node), "python": digest(python)},
        "preparedMarketplaceHashes": _tree_hashes(market),
        "sourceHashes": {name: digest(path) for name, path in sources.items()},
        "sourcePaths": {name: str(path) for name, path in sources.items()},
        "protectedFiles": {str(path): digest(path) for path in protected},
        "nativeResourceLabels": list(RESOURCE_LABELS),
        "nativeCommandLabels": list(COMMAND_LABELS),
        "ownedRoots": {name: str(evidence / name) for name in OWNED_ROOTS},
        "initialRootHashes": {name: _root_hashes(evidence / name) for name in OWNED_ROOTS},
        "standaloneSkill": {"root": str(standalone_root), "path": str(standalone / "SKILL.md"),
                            "hashes": _tree_hashes(standalone_root), "role": "task-owned-fixed-control"},
        "pluginId": PLUGIN_ID,
        "promptSha256": hashlib.sha256(PROMPT.encode("utf-8")).hexdigest(),
        "limits": {"workSeconds": args.timeout, "requestSeconds": args.request_timeout,
                   "recoverySeconds": args.recovery_timeout, "providerRequests": 4,
                   "providerRequestBytes": 2 * 1024 * 1024},
        "claimLimit": "no-model native mechanism only; no Agent, Desktop, IDE, value or release claim",
        "resourceController": controller,
        "resourceEvidenceScope": _resource_scope(controller),
    }
    if hot is not None:
        manifest.update(case=HOT_CASE, hotReload=hot, nativeCommandLabels=list(HOT_COMMAND_LABELS))
        manifest["limits"]["providerRequests"] = 6
        manifest["claimLimit"] += "; hot-reload applies only to this case's already Accord-bound paused task; unchanged Hook declarations and trust; no prior-user-history takeover, same-version replacement, host upgrade or autonomous Agent update claim"
    save(evidence / "manifest.json", manifest)
    return {"prepared": True, "modelCalls": 0, "evidence": str(evidence)}


def _load(evidence):
    evidence = _ordinary_dir(evidence)
    manifest = json.loads(read_regular(evidence / "manifest.json"))
    if not isinstance(manifest, dict) or manifest.get("evidence") != str(evidence):
        raise ValueError("lifecycle manifest evidence root mismatch")
    hot = _hot_binding(manifest)
    if (manifest.get("schema") != SCHEMA or manifest.get("evidence") != str(evidence)
            or manifest.get("pluginId") != PLUGIN_ID
            or manifest.get("promptSha256") != hashlib.sha256(PROMPT.encode("utf-8")).hexdigest()
            or tuple(manifest.get("nativeResourceLabels", ())) != RESOURCE_LABELS
            or tuple(manifest.get("nativeCommandLabels", ())) != (HOT_COMMAND_LABELS if hot else COMMAND_LABELS)
            or set(manifest.get("ownedRoots", {})) != set(OWNED_ROOTS)
            or set(manifest.get("initialRootHashes", {})) != set(OWNED_ROOTS)
            or set(manifest.get("binaryHashes", {})) != {"codex", "node", "python"}
            or not isinstance(manifest.get("protectedFiles"), dict) or not manifest["protectedFiles"]
            or set(manifest.get("limits", {})) != {"workSeconds", "requestSeconds", "recoverySeconds",
                                                    "providerRequests", "providerRequestBytes"}
            or any(type(manifest["limits"][name]) is not int or manifest["limits"][name] <= 0
                   for name in ("workSeconds", "requestSeconds", "recoverySeconds"))
            or manifest["limits"].get("providerRequests") != (6 if hot else 4)
            or manifest["limits"].get("providerRequestBytes") != 2 * 1024 * 1024
            or any(manifest["ownedRoots"][name] != str(evidence / name) for name in OWNED_ROOTS)):
        raise ValueError("lifecycle manifest binding mismatch")
    controller = manifest.get("resourceController", "windows-job-object")
    if (controller not in {"windows-job-object", "posix-session-process-group"}
            or "resourceController" in manifest
            and manifest.get("resourceEvidenceScope") != _resource_scope(controller)):
        raise ValueError("lifecycle resource controller binding mismatch")
    return manifest


def _validate_prebound(manifest):
    _hot_binding(manifest)
    if manifest.get("resourceController", "windows-job-object") != _controller_kind():
        raise ValueError("prepared resource controller differs from this host")
    evidence = Path(manifest["evidence"])
    sources = _source_paths()
    if (set(manifest.get("sourceHashes", {})) != set(sources)
            or manifest.get("sourcePaths") != {name: str(path) for name, path in sources.items()}):
        raise ValueError("prepared source set changed")
    if manifest.get("python") != str(_regular_file(sys.executable)):
        raise ValueError("running Python differs from the prepared interpreter")
    for name in ("codex", "node", "python"):
        if digest(_regular_file(manifest[name])) != manifest["binaryHashes"][name]:
            raise ValueError("prepared native binary changed: " + name)
    for path, expected in manifest["protectedFiles"].items():
        if digest(_regular_file(path)) != expected:
            raise ValueError("prepared protected file changed")
    for name, expected in manifest["sourceHashes"].items():
        if digest(manifest["sourcePaths"][name]) != expected:
            raise ValueError("prepared source changed: " + name)
    if digest(manifest["marketplaceManifest"]) != manifest["marketplaceManifestSha256"]:
        raise ValueError("prepared marketplace source changed")
    if (manifest.get("packageHashes") != manifest.get("snapshotHashes")
            or _tree_hashes(manifest["package"]) != manifest["packageHashes"]):
        raise ValueError("prepared package changed")
    if _tree_hashes(evidence / "source-package") != manifest["snapshotHashes"]:
        raise ValueError("package snapshot changed")
    if _tree_hashes(evidence / "marketplace") != manifest["preparedMarketplaceHashes"]:
        raise ValueError("prepared marketplace changed")
    if _tree_hashes(evidence / "marketplace/plugins/yiyuan-accord-codex") != manifest["snapshotHashes"]:
        raise ValueError("prepared marketplace package differs")
    for name in OWNED_ROOTS:
        _ordinary_dir(manifest["ownedRoots"][name])
        if _root_hashes(manifest["ownedRoots"][name]) != manifest["initialRootHashes"][name]:
            raise ValueError("prepared owned root changed: " + name)
    standalone = manifest.get("standaloneSkill", {})
    if (standalone.get("root") != str(evidence / "standalone-skills")
            or standalone.get("path") != str(evidence / "standalone-skills/exposure-control/SKILL.md")
            or standalone.get("role") != "task-owned-fixed-control"
            or _tree_hashes(standalone["root"]) != standalone.get("hashes")):
        raise ValueError("prepared standalone Skill changed")


def _wait_job(job, deadline):
    sample = job.sample()
    while not _released(sample) and time.monotonic() < deadline:
        time.sleep(0.05)
        sample = job.sample()
    return sample


def _run_cli(manifest, label, arguments, env, work_deadline):
    evidence = Path(manifest["evidence"])
    root = evidence / "commands" / label
    root.mkdir()
    job, process, forced, failure, recovery_deadline = _new_controller(), None, False, None, None
    stdout_path, stderr_path = root / "stdout.json", root / "stderr.txt"
    arguments = ["-c", 'cli_auth_credentials_store="file"', *arguments]
    try:
        with stdout_path.open("xb") as stdout, stderr_path.open("xb") as stderr:
            process = subprocess.Popen([manifest["codex"], *arguments], cwd=manifest["ownedRoots"]["workspace"],
                env=env, stdin=subprocess.DEVNULL, stdout=stdout, stderr=stderr,
                **_spawn_options())
            try:
                job.attach_and_resume(process)
            except BaseException:
                forced = True
                failure = "job-attach"
                try:
                    job.terminate()
                finally:
                    if process.poll() is None:
                        process.kill()
                raise
            try:
                process.wait(timeout=min(manifest["limits"]["requestSeconds"], _remaining(work_deadline)))
            except (subprocess.TimeoutExpired, TimeoutError):
                forced, failure = True, "work-deadline"
                job.terminate()
        recovery_deadline = time.monotonic() + manifest["limits"]["recoverySeconds"]
        if process is not None and process.poll() is None:
            process.wait(timeout=max(0.001, recovery_deadline - time.monotonic()))
        after = _wait_job(job, recovery_deadline)
        if not _released(after):
            forced = True
            job.terminate()
            after = _wait_job(job, recovery_deadline)
        record = {"arguments": arguments, **_resource_record(manifest, process, forced, after, failure)}
        save(root / "record.json", record)
        if not _record_released(record, manifest):
            raise RuntimeError("native command process release unobserved within recovery deadline")
        raw = read_regular(stdout_path, 4 * 1024 * 1024)
        parsed = json.loads(raw) if raw.strip() else None
        return record, parsed
    except BaseException:
        recovery_deadline = recovery_deadline or time.monotonic() + manifest["limits"]["recoverySeconds"]
        if process is not None and process.poll() is None:
            forced = True
            try:
                job.terminate()
            finally:
                if process.poll() is None:
                    process.kill()
            try:
                process.wait(timeout=max(0.001, recovery_deadline - time.monotonic()))
            except subprocess.TimeoutExpired:
                pass
        after = _wait_job(job, recovery_deadline)
        save(root / "record.json", {"arguments": arguments,
            **_resource_record(manifest, process, forced, after, failure or "native-command")})
        raise
    finally:
        job.close()


class _Fixture:
    def __init__(self, manifest):
        self.requests, self.auth_seen = [], False
        self.release, self.received, self.hold_next = threading.Event(), threading.Event(), False
        owner, limit = self, manifest["limits"]["providerRequestBytes"]
        self.receipt = Path(manifest["evidence"]) / "retained/provider-requests.jsonl"

        class Handler(http.server.BaseHTTPRequestHandler):
            def setup(self):
                super().setup()
                self.connection.settimeout(manifest["limits"]["recoverySeconds"])

            def log_message(self, *_args):
                pass

            def do_POST(self):
                if self.headers.get("Authorization"):
                    owner.auth_seen = True
                    self.send_error(400, "fixture refuses credentials")
                    return
                length = int(self.headers.get("Content-Length", "0"))
                if length <= 0 or length > limit or len(owner.requests) >= manifest["limits"]["providerRequests"]:
                    self.send_error(429, "fixture bound exceeded")
                    return
                body = json.loads(self.rfile.read(length))
                owner.requests.append(body)
                ordinal = len(owner.requests)
                with owner.receipt.open("a", encoding="utf-8") as stream:
                    stream.write(json.dumps({"ordinal": ordinal, "request": body}, ensure_ascii=False) + "\n")
                owner.received.set()
                response = {"id": f"resp_fixture_{ordinal}", "object": "response", "created_at": int(time.time()),
                            "status": "in_progress", "output": []}
                transport = "started"

                def emit(kind, **data):
                    self.wfile.write(("data: " + json.dumps({"type": kind, **data}) + "\n\n").encode())
                    self.wfile.flush()
                try:
                    self.send_response(200)
                    self.send_header("Content-Type", "text/event-stream")
                    self.end_headers()
                    emit("response.created", response=response)
                    if owner.hold_next:
                        owner.hold_next = False
                        if not owner.release.wait(25):
                            transport = "hold-timeout"
                            return
                    text = "受控固定响应；不代表模型判断或任务交付。"
                    item = {"id": f"msg_fixture_{ordinal}", "type": "message", "role": "assistant", "status": "completed",
                            "content": [{"type": "output_text", "text": text, "annotations": []}]}
                    emit("response.output_item.added", output_index=0, item={**item, "status": "in_progress", "content": []})
                    emit("response.output_text.delta", item_id=item["id"], output_index=0, content_index=0, delta=text)
                    emit("response.output_item.done", output_index=0, item=item)
                    response.update(status="completed", output=[item], usage={"input_tokens": 1, "output_tokens": 1, "total_tokens": 2})
                    emit("response.completed", response=response)
                    transport = "completed"
                except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
                    transport = "peer-closed"
                except TimeoutError:
                    transport = "socket-timeout"
                finally:
                    save(Path(owner.receipt).parent / f"provider-response-{ordinal}.json",
                         {"ordinal": ordinal, "response": response, "transportStatus": transport,
                          "claimLimit": "server transport attempt; native receipts determine consumer outcome"})

        self.server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.server.daemon_threads = False  # server_close joins workers after release.
        self.thread = threading.Thread(target=self.server.serve_forever, kwargs={"poll_interval": 0.05}, daemon=True)
        self.thread.start()

    @property
    def port(self):
        return self.server.server_port

    def close(self):
        self.release.set()
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(5)


class _App:
    def __init__(self, manifest, label, argv, env, work_deadline):
        evidence = Path(manifest["evidence"])
        self.root = evidence / "native" / label
        self.workspace = manifest["ownedRoots"]["workspace"]
        self.request_timeout = manifest["limits"]["requestSeconds"]
        self.root.mkdir()
        self.job, self.events, self.queue = _new_controller(), [], queue.Queue()
        self.manifest, self.work_deadline = manifest, work_deadline
        self.hot_arguments = list(argv) if label == "resumed" and manifest.get("case") == HOT_CASE else None
        self._closed, self._close_record = False, None
        self.stderr = (self.root / "stderr.txt").open("xb")
        self.stdout = (self.root / "stdout.jsonl").open("xb")
        self.process = None
        try:
            self.process = subprocess.Popen(argv, cwd=manifest["ownedRoots"]["workspace"], env=env,
                stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=self.stderr,
                **_spawn_options())
            self.job.attach_and_resume(self.process)
        except BaseException:
            if self.process is not None and self.process.poll() is None:
                try:
                    self.job.terminate()
                finally:
                    if self.process.poll() is None:
                        self.process.kill()
                try:
                    self.process.wait(timeout=manifest["limits"]["recoverySeconds"])
                except subprocess.TimeoutExpired:
                    pass
            after = self.job.sample()
            save(self.root / "resources.json", _resource_record(manifest, self.process, True, after, "job-attach"))
            for name in ("stdin", "stdout"):
                pipe = getattr(self.process, name, None)
                if pipe is not None:
                    pipe.close()
            self.job.close(); self.stderr.close(); self.stdout.close()
            raise

        def reader():
            try:
                for raw in self.process.stdout:
                    if len(raw) > 1024 * 1024:
                        raise ValueError("oversized native event")
                    self.stdout.write(raw)
                    self.stdout.flush()
                    self.queue.put(json.loads(raw))
            except BaseException as error:
                self.queue.put(error)
            finally:
                self.queue.put(None)

        self.reader = threading.Thread(target=reader, daemon=True)
        self.reader.start()
        self.rpc_client = BoundedRpc(self._send, self._receive, work_deadline=work_deadline,
            request_timeout=manifest["limits"]["requestSeconds"],
            recovery_timeout=manifest["limits"]["recoverySeconds"], on_event=self.events.append)

    def _send(self, request):
        with (self.root / "requests.jsonl").open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(request, ensure_ascii=False) + "\n")
        self.process.stdin.write((json.dumps(request) + "\n").encode())
        self.process.stdin.flush()

    def _receive(self, deadline):
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise TimeoutError("native receive deadline")
        try:
            value = self.queue.get(timeout=remaining)
        except queue.Empty as error:
            raise TimeoutError("native receive deadline") from error
        if value is None:
            raise RuntimeError("native stdout closed")
        if isinstance(value, BaseException):
            raise value
        return value

    def rpc(self, method, params):
        return self.rpc_client.request(method, params)

    def initialize(self):
        self.rpc("initialize", {"clientInfo": {"name": "accord_lifecycle_observer", "version": "1"},
                                "capabilities": {"experimentalApi": True}})
        self._send({"method": "initialized", "params": {}})

    def wait_turn(self, thread_id, turn_id):
        for event in self.events:
            if (event.get("method") == "turn/completed" and event.get("params", {}).get("threadId") == thread_id
                    and event["params"].get("turn", {}).get("id") == turn_id):
                return event["params"]["turn"].get("status")
        deadline = min(self.work_deadline, time.monotonic() + self.request_timeout)
        while True:
            event = self._receive(deadline)
            self.events.append(event)
            if (event.get("method") == "turn/completed" and event.get("params", {}).get("threadId") == thread_id
                    and event["params"].get("turn", {}).get("id") == turn_id):
                return event["params"]["turn"].get("status")

    def close(self, manifest=None):
        if self._closed:
            return self._close_record
        manifest = self.manifest if manifest is None else manifest
        forced = False
        try:
            self.process.stdin.close()
            recovery_deadline = time.monotonic() + manifest["limits"]["recoverySeconds"]
            try:
                self.process.wait(timeout=max(0.001, recovery_deadline - time.monotonic()))
            except subprocess.TimeoutExpired:
                forced = True
                self.job.terminate()
                try:
                    self.process.wait(timeout=max(0.001, recovery_deadline - time.monotonic()))
                except subprocess.TimeoutExpired:
                    pass
            after = _wait_job(self.job, recovery_deadline)
            if not _released(after):
                forced = True
                self.job.terminate()
                after = _wait_job(self.job, recovery_deadline)
            self.reader.join(timeout=max(0, recovery_deadline - time.monotonic()))
            record = _resource_record(manifest, self.process, forced, after)
            record["readerStopped"] = not self.reader.is_alive()
            if self.hot_arguments is not None:
                record["arguments"] = self.hot_arguments
            save(self.root / "resources.json", record)
            self._close_record = record
            if not _record_released(record, manifest):
                raise RuntimeError("native app process release unobserved within recovery deadline")
            return record
        finally:
            self._closed = True
            self.job.close()
            if not self.reader.is_alive():
                self.process.stdout.close()
            self.stderr.close()
            self.stdout.close()


def _provider(manifest, fixture):
    return {"name": "Accord no-model lifecycle fixture", "base_url": f"http://127.0.0.1:{fixture.port}/v1",
            "wire_api": "responses", "requires_openai_auth": False, "supports_websockets": False,
            "request_max_retries": 0, "stream_max_retries": 0, "stream_idle_timeout_ms": 25000}


def _argv(manifest, fixture, extra=()):
    return [manifest["codex"], "app-server", "-c", "features.plugins=true", "-c", "features.hooks=true",
            "-c", "features.apps=false", "-c", 'web_search="disabled"', "-c", 'cli_auth_credentials_store="file"',
            "-c", 'model_provider="accord_fixture"', "-c", 'model="fixture-no-model"', "-c",
            "model_providers.accord_fixture=" + _toml(_provider(manifest, fixture)), *extra]


def _helper(manifest, installed, env, work_deadline, thread, op, **fields):
    request = {"op": op, "session_id": thread, "cwd": manifest["ownedRoots"]["workspace"], **fields}
    receipt = Path(manifest["evidence"]) / "retained/helper.jsonl"
    with receipt.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps({"phase": "request", "request": request}, ensure_ascii=False) + "\n")
    try:
        process = subprocess.run([manifest["node"], str(installed / "runtime/task-checkpoint.cjs")],
            input=json.dumps(request).encode(), capture_output=True,
            timeout=min(manifest["limits"]["requestSeconds"], _remaining(work_deadline)),
            env=env, cwd=manifest["ownedRoots"]["workspace"])
    except subprocess.TimeoutExpired as error:
        with receipt.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps({"phase": "response", "op": op, "timeout": True,
                "stdout": (error.stdout or b"").decode("utf-8", "replace"),
                "stderr": (error.stderr or b"").decode("utf-8", "replace")}, ensure_ascii=False) + "\n")
        raise
    terminal = {"phase": "response", "op": op, "exitCode": process.returncode,
                "stdout": process.stdout.decode("utf-8", "replace"),
                "stderr": process.stderr.decode("utf-8", "replace")}
    try:
        terminal["result"] = json.loads(process.stdout)
    except (ValueError, UnicodeError):
        terminal["parseError"] = True
    with receipt.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(terminal, ensure_ascii=False) + "\n")
    if process.returncode or terminal.get("parseError"):
        raise RuntimeError("checkpoint helper failed; inspect retained/helper.jsonl")
    return terminal["result"]


def _start_turn(app, ephemeral, prompt):
    thread = app.rpc("thread/start", {"ephemeral": ephemeral, "model": "fixture-no-model",
        "modelProvider": "accord_fixture", "cwd": app.workspace,
        "sandbox": "read-only", "approvalPolicy": "never"})["thread"]["id"]
    turn = app.rpc("turn/start", {"threadId": thread, "input": [{"type": "text", "text": prompt}]})["turn"]["id"]
    return thread, turn


def _hot_hooks_match(hooks, trust, installed):
    rows = [row for row in _hook_rows(hooks) if row.get("key", "").startswith(PLUGIN_ID + ":")]
    return (len(rows) == len(trust) and {row.get("key") for row in rows} == set(trust)
            and all(row.get("currentHash") == trust[row["key"]]["trusted_hash"]
                    and row.get("enabled") is True and row.get("trustStatus") == "trusted"
                    and isinstance(row.get("sourcePath"), str)
                    and Path(row["sourcePath"]).is_relative_to(installed) for row in rows))


def _run_hot_reload(manifest, app, fixture, installed, env, work_deadline, thread, prior, trust):
    hot, evidence = manifest["hotReload"], Path(manifest["evidence"])
    source = Path(manifest["ownedRoots"]["marketplace"]) / "plugins/yiyuan-accord-codex"
    current = installed
    source_hash = manifest["initialRootHashes"]["workspace"]["source.json"]
    for index, (label, snapshot, hashes) in enumerate((
            ("hot-reload-upgrade", Path(hot["snapshot"]), hot["hashes"]),
            ("hot-reload-rollback", evidence / "source-package", manifest["packageHashes"]))):
        retained = evidence / "retained" / label
        retained.mkdir()
        shutil.copytree(manifest["ownedRoots"]["state"], retained / "before-install-state")
        for name in hot["changedFiles"]:
            (source / name).write_bytes(read_regular(snapshot / name))
        if _tree_hashes(source) != hashes:
            raise RuntimeError("selected hot-reload marketplace bytes differ")
        record, payload = _run_cli(manifest, label, ["plugin", "add", manifest["pluginId"], "--json"], env, work_deadline)
        if record["exitCode"] or not isinstance(payload, dict) or not payload.get("installedPath"):
            raise RuntimeError("hot-reload package install failed")
        selected = _ordinary_dir(payload["installedPath"])
        if (Path(manifest["ownedRoots"]["home"]) not in selected.parents
                or index == 0 and selected == installed or index == 1 and selected != installed
                or _tree_hashes(selected) != hashes):
            raise RuntimeError("hot-reload installed identity or bytes differ")
        shutil.copytree(selected, retained / "installed-package")
        shutil.copytree(manifest["ownedRoots"]["state"], retained / "after-install-state")
        before = _helper(manifest, selected, env, work_deadline, thread, "status")
        if (before != prior or _tree_hashes(retained / "before-install-state")
                != _tree_hashes(retained / "after-install-state")):
            raise RuntimeError("package install changed the bound paused task")
        turn = app.rpc("turn/start", {"threadId": thread,
            "input": [{"type": "text", "text": HOT_PROMPTS[index]}]})["turn"]["id"]
        if app.wait_turn(thread, turn) != "completed" or len(fixture.requests) != index + 5:
            raise RuntimeError("hot-reload bounded turn did not complete")
        after = _helper(manifest, selected, env, work_deadline, thread, "status")
        context = _latest_input_context(fixture.requests[-1])
        if (not _checkpoint_matches(after, source_hash, index + 3)
                or after.get("checkpoint") != prior.get("checkpoint")
                or after.get("epoch") == prior.get("epoch")
                or after.get("currentInputReconciled") is not False
                or after.get("hostObservationCurrent") is not True
                or after.get("hostObservation", {}).get("turnId") != turn
                or not _contains_path(context, selected / "runtime/task-checkpoint.cjs")
                or f"Native input receipt: session={thread}; epoch={after['epoch']}." not in context
                or digest(Path(app.workspace) / "source.json") != source_hash
                or (Path(app.workspace) / "pending.json").exists()):
            raise RuntimeError("hot-reload native input or paused checkpoint differs")
        # Observe trust only AFTER the turn; this list cannot refresh the tested turn.
        hooks = app.rpc("hooks/list", {"cwds": [app.workspace]})
        if not _hot_hooks_match(hooks, trust, selected):
            raise RuntimeError("hot-reload changed Hook declaration identity or trust")
        shutil.copytree(manifest["ownedRoots"]["state"], retained / "after-turn-state")
        save(retained / "observation.json", {"installedPath": str(selected), "threadId": thread,
            "turnId": turn, "providerOrdinal": index + 5, "beforeTurn": before, "afterTurn": after, "hooks": hooks})
        prior, current = after, selected
    return current


def run(args):
    manifest = _load(args.evidence)
    _validate_prebound(manifest)
    evidence = Path(manifest["evidence"])
    with (evidence / "run-started.json").open("x", encoding="utf-8") as stream:
        json.dump({"time": time.time(), "manifestSha256": digest(evidence / "manifest.json"),
                   "nativeResourceLabels": list(RESOURCE_LABELS), "nativeCommandLabels": manifest["nativeCommandLabels"],
                   "resourceController": manifest.get("resourceController", "windows-job-object")}, stream)
    env = _owned_environment(manifest)
    work_deadline = time.monotonic() + manifest["limits"]["workSeconds"]
    result = {"failure": None, "failureStage": None, "modelCalls": 0, "claimLimit": manifest["claimLimit"],
              "resourceController": manifest.get("resourceController", "windows-job-object"),
              "resourceEvidenceScope": _resource_scope(manifest.get("resourceController", "windows-job-object"))}
    fixture, apps = None, []
    installed = None
    try:
        market = manifest["ownedRoots"]["marketplace"]
        result["failureStage"] = "marketplace-add"
        record, _ = _run_cli(manifest, "marketplace-add", ["plugin", "marketplace", "add", market, "--json"], env, work_deadline)
        if record["exitCode"]:
            raise RuntimeError("marketplace add failed")
        result["failureStage"] = "package-add"
        record, payload = _run_cli(manifest, "package-add", ["plugin", "add", manifest["pluginId"], "--json"], env, work_deadline)
        if record["exitCode"] or not isinstance(payload, dict) or not payload.get("installedPath"):
            raise RuntimeError("package add failed")
        installed = _ordinary_dir(payload["installedPath"])
        owned_home = _ordinary_dir(manifest["ownedRoots"]["home"])
        if owned_home not in installed.parents:
            raise RuntimeError("native installed path escaped owned CODEX_HOME")
        if _tree_hashes(installed) != manifest["packageHashes"]:
            raise RuntimeError("installed package differs")
        result["installedPathReturned"] = str(installed)
        result["installedPackageHashes"] = _tree_hashes(installed)
        fixture = _Fixture(manifest)
        base = _argv(manifest, fixture)

        result["failureStage"] = "discovery"
        app = _App(manifest, "discovery", base, env, work_deadline); apps.append(app); app.initialize()
        app.rpc("skills/extraRoots/set", {"extraRoots": [manifest["standaloneSkill"]["root"]]})
        hooks = app.rpc("hooks/list", {"cwds": [manifest["ownedRoots"]["workspace"]]})
        skills = app.rpc("skills/list", {"cwds": [manifest["ownedRoots"]["workspace"]], "forceReload": True})
        save(evidence / "retained/hooks-before.json", hooks)
        save(evidence / "retained/skills-before.json", skills)
        result["discoveryResources"] = app.close(manifest); apps.remove(app)
        owned = [hook for hook in _hook_rows(hooks) if hook.get("key", "").startswith(manifest["pluginId"] + ":")]
        package_skills = [skill for skill in _skill_rows(skills) if Path(skill["path"]).is_relative_to(installed)]
        hook_sources = [hook.get("sourcePath") for hook in owned if isinstance(hook.get("sourcePath"), str)]
        if (len(owned) != manifest["declaredHookRegistrations"] or not package_skills or not hook_sources
                or any(not Path(path).is_relative_to(installed) for path in hook_sources)):
            raise RuntimeError("installed hooks absent")
        result["loadedObject"] = {"installedPath": str(installed), "hookSourcePaths": hook_sources,
                                  "skillPaths": [skill["path"] for skill in package_skills]}
        result["exactPackageLoadedAndTrusted"] = True
        trust = {hook["key"]: {"enabled": True, "trusted_hash": hook["currentHash"]} for hook in owned}
        standalone_path = manifest["standaloneSkill"]["path"]
        controls = [skill for skill in _skill_rows(skills) if Path(skill["path"]).resolve() == Path(standalone_path)]
        if len(controls) != 1 or controls[0].get("pluginId") is not None or not controls[0].get("enabled"):
            raise RuntimeError("task-owned standalone Skill exposure unavailable")
        standalone_before = manifest["standaloneSkill"]["hashes"]
        skill_config = [{"path": standalone_path, "enabled": False}]
        common = ("-c", "skills.config=" + _toml(skill_config))

        def launch(label, states=trust):
            result["failureStage"] = label
            app = _App(manifest, label, _argv(manifest, fixture, (*common, "-c", "hooks.state=" + _toml(states))), env, work_deadline)
            if label == "resumed" and manifest.get("case") == HOT_CASE:
                save(evidence / "retained/hot-reload-launch.json", {"arguments": _argv(manifest, fixture,
                    (*common, "-c", "hooks.state=" + _toml(states))), "trust": states})
            apps.append(app); app.initialize()
            app.rpc("skills/extraRoots/set", {"extraRoots": [manifest["standaloneSkill"]["root"]]})
            checked = _hook_rows(app.rpc("hooks/list", {"cwds": [manifest["ownedRoots"]["workspace"]]}))
            if {h["key"] for h in checked if h.get("enabled")} != {k for k, v in states.items() if v["enabled"]}:
                raise RuntimeError("hook state mismatch")
            if any(h.get("trustStatus") != "trusted" for h in checked if h.get("enabled")):
                raise RuntimeError("hook trust mismatch")
            visible = _skill_rows(app.rpc("skills/list", {"cwds": [manifest["ownedRoots"]["workspace"]], "forceReload": True}))
            selected = [s for s in visible if Path(s["path"]).resolve() == Path(standalone_path)]
            if len(selected) != 1 or selected[0].get("enabled"):
                raise RuntimeError("standalone Skill exposure mismatch")
            return app

        for label, enabled in (("end-enabled", True), ("end-disabled", False)):
            states = json.loads(json.dumps(trust))
            if not enabled:
                matches = [hook["key"] for hook in owned if str(hook.get("eventName", "")).lower() == "sessionend"
                           or ":session_end:" in hook["key"]]
                if len(matches) != 1:
                    raise RuntimeError("SessionEnd hook identity ambiguous")
                states[matches[0]]["enabled"] = False
            app = launch(label, states)
            thread, turn = _start_turn(app, True, "只确认收到，不操作任何文件。")
            if app.wait_turn(thread, turn) != "completed":
                raise RuntimeError("fixed turn did not complete")
            before = _helper(manifest, installed, env, work_deadline, thread, "status")
            if before.get("mode") != "unbound":
                raise RuntimeError("unexpected checkpoint state")
            state_before = _tree_hashes(manifest["ownedRoots"]["state"])
            app.rpc("thread/unsubscribe", {"threadId": thread})
            app.close(manifest); apps.remove(app)
            state_after = _tree_hashes(manifest["ownedRoots"]["state"]) if any(Path(manifest["ownedRoots"]["state"]).iterdir()) else {}
            if bool(set(state_before) - set(state_after)) != enabled:
                raise RuntimeError("SessionEnd contrast failed")
            if not enabled:
                status = _helper(manifest, installed, env, work_deadline, thread, "status")
                _helper(manifest, installed, env, work_deadline, thread, "retire", epoch=status["epoch"], expectedRevision=0,
                        reason="controlled no-model episode complete")
        result["sessionEndEnabledDisabledContrast"] = True

        app = launch("interrupted")
        fixture.received.clear(); fixture.release.clear(); fixture.hold_next = True
        thread, turn = _start_turn(app, False, PROMPT)
        if not fixture.received.wait(min(manifest["limits"]["requestSeconds"], _remaining(work_deadline))):
            raise RuntimeError("fixture request absent")
        status = _helper(manifest, installed, env, work_deadline, thread, "status")
        bound = _helper(manifest, installed, env, work_deadline, thread, "bind", epoch=status["epoch"], expectedRevision=0,
            result="Deliver pending.json only after an explicit later decision", inputs=["source.json"],
            outputs=[{"path": "pending.json", "json": {"/total": 140}}],
            nextAction="retain pause and wait for decision", canContinue=False)
        _helper(manifest, installed, env, work_deadline, thread, "pause", epoch=status["epoch"],
                expectedRevision=bound["revision"], reason="user explicitly paused pending decision")
        before_pause = _helper(manifest, installed, env, work_deadline, thread, "status")
        source_hash = digest(Path(manifest["ownedRoots"]["workspace"]) / "source.json")
        if not _checkpoint_matches(before_pause, source_hash, 1) or before_pause.get("currentInputReconciled") is not True:
            raise RuntimeError("paused checkpoint contract differs")
        save(evidence / "retained/before-pause.json", before_pause)
        app.rpc("turn/interrupt", {"threadId": thread, "turnId": turn})
        if app.wait_turn(thread, turn) != "interrupted":
            raise RuntimeError("native interrupt absent")
        fixture.release.set()
        after_interrupt = _helper(manifest, installed, env, work_deadline, thread, "status")
        if (not _checkpoint_matches(after_interrupt, source_hash, 1)
                or after_interrupt.get("epoch") == before_pause.get("epoch")
                or after_interrupt.get("currentInputReconciled") is not False
                or after_interrupt.get("hostObservationCurrent") is not False):
            raise RuntimeError("interrupt did not invalidate observation")
        save(evidence / "retained/after-interrupt.json", after_interrupt)
        result["nativeInterruptInvalidatesReadiness"] = True
        app.rpc("thread/unsubscribe", {"threadId": thread}); app.close(manifest); apps.remove(app)
        after_exit = _helper(manifest, installed, env, work_deadline, thread, "status")
        if (not _checkpoint_matches(after_exit, source_hash, 1)
                or after_exit.get("checkpoint") != after_interrupt.get("checkpoint")
                or after_exit.get("epoch") != after_interrupt.get("epoch")):
            raise RuntimeError("unfinished paused state did not survive exit")
        save(evidence / "retained/after-exit.json", after_exit)

        app = launch("resumed")
        resumed = app.rpc("thread/resume", {"threadId": thread, "cwd": manifest["ownedRoots"]["workspace"],
            "model": "fixture-no-model", "modelProvider": "accord_fixture", "sandbox": "read-only",
            "approvalPolicy": "never"})
        resumed_before = _helper(manifest, installed, env, work_deadline, thread, "status")
        if (resumed["thread"]["id"] != thread or not _checkpoint_matches(resumed_before, source_hash, 1)
                or resumed_before.get("checkpoint") != after_exit.get("checkpoint")):
            raise RuntimeError("paused state did not resume")
        save(evidence / "retained/resumed-before-continue.json", resumed_before)
        result["nativeResumePreservesPausedBinding"] = True
        turn = app.rpc("turn/start", {"threadId": thread, "input": [{"type": "text", "text": "继续。"}]})["turn"]["id"]
        if app.wait_turn(thread, turn) != "completed":
            raise RuntimeError("resume turn did not complete")
        after_resume = _helper(manifest, installed, env, work_deadline, thread, "status")
        if (not _checkpoint_matches(after_resume, source_hash, 2)
                or after_resume.get("checkpoint") != after_exit.get("checkpoint")
                or after_resume.get("currentInputReconciled") is not False
                or after_resume.get("hostObservationCurrent") is not True
                or after_resume.get("epoch") == after_exit.get("epoch")
                or (Path(manifest["ownedRoots"]["workspace"]) / "pending.json").exists()):
            raise RuntimeError("continue silently resumed paused work")
        save(evidence / "retained/after-resume.json", after_resume)
        save(evidence / "retained/paused-thread.json", {"threadId": thread})
        result["continueReceiptDoesNotResumeBinding"] = True
        if manifest.get("case") == HOT_CASE:
            result["failureStage"] = "hot-reload-upgrade-rollback"
            installed = _run_hot_reload(manifest, app, fixture, installed, env, work_deadline, thread, after_resume, trust)
            result["hotReloadObserved"] = True
        app.rpc("thread/unsubscribe", {"threadId": thread}); app.close(manifest); apps.remove(app)

        result["providerRequests"] = len(fixture.requests)
        result["standaloneSkillPathAbsentFromProviderInput"] = not _contains_path(fixture.requests, standalone_path)
        result["standaloneCatalogEntryAbsent"] = (
            result["standaloneSkillPathAbsentFromProviderInput"]
            and not any(controls[0]["name"].casefold() in text.casefold() for text in _strings(fixture.requests)))
        result["accordCatalogPresent"] = all("deliver-demand-driven-outcome" in json.dumps(body) for body in fixture.requests)
        result["selectedPathsDisabledInOwnedProcess"] = result["standaloneSkillPathAbsentFromProviderInput"]

        result["failureStage"] = "restored-exposure"
        app = _App(manifest, "restored-exposure", base, env, work_deadline); apps.append(app); app.initialize()
        app.rpc("skills/extraRoots/set", {"extraRoots": [manifest["standaloneSkill"]["root"]]})
        restored = [s for s in _skill_rows(app.rpc("skills/list", {
            "cwds": [manifest["ownedRoots"]["workspace"]], "forceReload": True}))
            if Path(s["path"]).resolve() == Path(standalone_path)]
        result["originalExposureRestored"] = len(restored) == 1 and restored[0].get("enabled") is True
        app.rpc("skills/extraRoots/set", {"extraRoots": []})
        cleared = _skill_rows(app.rpc("skills/list", {"cwds": [manifest["ownedRoots"]["workspace"]], "forceReload": True}))
        result["standaloneExposureCleared"] = not any(Path(s["path"]).resolve() == Path(standalone_path) for s in cleared)
        result["standaloneSkillBytesUnchanged"] = _tree_hashes(manifest["standaloneSkill"]["root"]) == standalone_before
        app.close(manifest); apps.remove(app)

        source = Path(manifest["ownedRoots"]["marketplace"]) / "plugins/yiyuan-accord-codex/.codex-plugin/plugin.json"
        original = source.read_bytes(); installed_before = _tree_hashes(installed); state_before = _tree_hashes(manifest["ownedRoots"]["state"])
        try:
            source.write_bytes(b"{invalid candidate")
            result["failureStage"] = "invalid-candidate"
            bad, _ = _run_cli(manifest, "invalid-candidate", ["plugin", "add", manifest["pluginId"], "--json"], env, work_deadline)
            if bad["exitCode"] == 0 or _tree_hashes(installed) != installed_before or _tree_hashes(manifest["ownedRoots"]["state"]) != state_before:
                raise RuntimeError("malformed candidate changed healthy state")
            save(evidence / "retained/invalid-candidate-preserved.json",
                 {"package": _tree_hashes(installed), "state": _tree_hashes(manifest["ownedRoots"]["state"])})
            result["malformedCandidateRejectedWithoutReplacement"] = True
        finally:
            source.write_bytes(original)
        result["failureStage"] = "healthy-retry"
        healthy, _ = _run_cli(manifest, "healthy-retry", ["plugin", "add", manifest["pluginId"], "--json"], env, work_deadline)
        result["healthyRetryExact"] = healthy["exitCode"] == 0 and _tree_hashes(installed) == installed_before
        result["failureStage"] = "package-remove"
        removed, _ = _run_cli(manifest, "package-remove", ["plugin", "remove", manifest["pluginId"], "--json"], env, work_deadline)
        if removed["exitCode"] or installed.exists():
            raise RuntimeError("native uninstall failed")
        result["failureStage"] = "package-list-after-remove"
        listed, inventory = _run_cli(manifest, "package-list-after-remove", ["plugin", "list", "--json"], env, work_deadline)
        if (listed["exitCode"] or not isinstance(inventory, dict) or not isinstance(inventory.get("installed"), list)
                or any(row.get("pluginId") == manifest["pluginId"] for row in inventory["installed"]
                       if isinstance(row, dict))):
            raise RuntimeError("removed plugin remains in native inventory")
        result["failureStage"] = "after-remove"
        app = _App(manifest, "after-remove", base, env, work_deadline); apps.append(app); app.initialize()
        hooks_after = _hook_rows(app.rpc("hooks/list", {"cwds": [manifest["ownedRoots"]["workspace"]]}))
        skills_after = _skill_rows(app.rpc("skills/list", {"cwds": [manifest["ownedRoots"]["workspace"]], "forceReload": True}))
        result["nativeUninstallRemovesCacheAndDiscovery"] = (not any(h.get("key", "").startswith(manifest["pluginId"] + ":") for h in hooks_after)
            and not any(Path(s["path"]).is_relative_to(installed) for s in skills_after))
        app.close(manifest); apps.remove(app)
        result["unfinishedStatePreservedAcrossExitAndUninstall"] = _tree_hashes(manifest["ownedRoots"]["state"]) == state_before
        save(evidence / "retained/state-after-uninstall.json", _tree_hashes(manifest["ownedRoots"]["state"]))
        result["sourceHashAfter"] = digest(Path(manifest["ownedRoots"]["workspace"]) / "source.json")
        result["sourceUnchanged"] = result["sourceHashAfter"] == manifest["initialRootHashes"]["workspace"]["source.json"]
        result["providerBound"] = len(fixture.requests) == manifest["limits"]["providerRequests"] and not fixture.auth_seen
        result["mechanismComplete"] = all((result.get("standaloneCatalogEntryAbsent"), result.get("accordCatalogPresent"),
            result.get("originalExposureRestored"), result.get("standaloneExposureCleared"),
            result.get("standaloneSkillBytesUnchanged"),
            result.get("malformedCandidateRejectedWithoutReplacement"), result.get("healthyRetryExact"),
            result.get("nativeUninstallRemovesCacheAndDiscovery"), result.get("unfinishedStatePreservedAcrossExitAndUninstall"),
            result.get("sourceUnchanged"), result.get("providerBound")))
        if not result["mechanismComplete"]:
            raise RuntimeError("one or more observed lifecycle predicates failed")
        result["failureStage"] = "retain-state"
        shutil.copytree(manifest["ownedRoots"]["state"], evidence / "retained/unfinished-state")
        result["failureStage"] = None
    except BaseException as error:
        result["failure"] = type(error).__name__
        result["failureReason"] = str(error)[:300]
    finally:
        for app in apps:
            try:
                app.close(manifest)
            except BaseException:
                result.setdefault("cleanupErrors", []).append("native-app-close")
        if fixture is not None:
            try:
                fixture.close()
                result["loopbackListenerClosed"] = not fixture.thread.is_alive()
            except BaseException:
                result["loopbackListenerClosed"] = False
                result.setdefault("cleanupErrors", []).append("loopback-listener")
            result["credentialHeaderSeen"] = fixture.auth_seen
        state = Path(manifest["ownedRoots"]["state"])
        retained_state = evidence / "retained/unfinished-state"
        if state.exists() and not retained_state.exists():
            try:
                shutil.copytree(state, retained_state)
            except OSError:
                result.setdefault("cleanupErrors", []).append("retain-state")
        processes_released = _invoked_processes_released(evidence, manifest)
        result["invokedProcessesReleasedWithinControllerScope"] = processes_released
        if not processes_released:
            result.setdefault("cleanupErrors", []).append("process-release-unobserved; owned roots retained")
        for name in OWNED_ROOTS if processes_released else ():
            path = Path(manifest["ownedRoots"][name])
            if path.exists():
                try:
                    _remove_owned_tree(path)
                except (OSError, ValueError) as error:
                    result.setdefault("cleanupErrors", []).append({"root": name, "reason": str(error)[:1024]})
        result["ownedRootsAbsent"] = {name: not Path(manifest["ownedRoots"][name]).exists() for name in OWNED_ROOTS}
        protected_after = {}
        for path, expected in manifest["protectedFiles"].items():
            try:
                observed = digest(_regular_file(path))
            except (OSError, ValueError):
                observed = None
            protected_after[path] = observed
        result["protectedFileHashesAfter"] = protected_after
        result["protectedSharedFilesUnchanged"] = protected_after == manifest["protectedFiles"]
        result["sharedSettingsAndSelectionsPreserved"] = result["protectedSharedFilesUnchanged"]
        if (result.get("failure") is None
                and (not all(result["ownedRootsAbsent"].values()) or result.get("cleanupErrors")
                     or not result["protectedSharedFilesUnchanged"])):
            result["failure"] = "CleanupError"
            result["failureReason"] = "owned cleanup or protected-file poststate differs"
            result["failureStage"] = "cleanup"
        save(evidence / "result.json", result)
    return result


def _inspect_hot_reload(manifest, installed, thread, prior, provider_rows, requests, commands, resources):
    """Recompute optional-case predicates from CLI, native, package and receipt bytes."""
    root, hot = Path(manifest["evidence"]), _hot_binding(manifest)
    original_hooks = [row for row in _hook_rows(json.loads(read_regular(root / "retained/hooks-before.json")))
                      if row.get("key", "").startswith(PLUGIN_ID + ":")]
    trust = {row["key"]: {"enabled": True, "trusted_hash": row["currentHash"]} for row in original_hooks}
    launch = json.loads(read_regular(root / "retained/hot-reload-launch.json"))
    argv = resources["resumed"].get("arguments", [])
    if (not trust or len(trust) != manifest["declaredHookRegistrations"] or launch.get("trust") != trust
            or launch.get("arguments") != argv or argv[:2] != [manifest["codex"], "app-server"]
            or argv.count("hooks.state=" + _toml(trust)) != 1):
        raise ValueError("hot-reload original invocation or trust differs")
    starts = [index for index, row in enumerate(requests) if row.get("method") == "turn/start"]
    if (len(starts) != 3 or [row.get("method") for row in requests[starts[0]:]]
            != ["turn/start", "turn/start", "hooks/list", "turn/start", "hooks/list", "thread/unsubscribe"]
            or any(row.get("method") in {"config/write", "config/batchWrite", "plugin/install"} for row in requests)):
        raise ValueError("hot-reload adds native reload, trust mutation or another turn")
    native = [json.loads(line) for line in read_regular(root / "native/resumed/stdout.jsonl").decode().splitlines() if line]
    source_hash = manifest["initialRootHashes"]["workspace"]["source.json"]
    previous_tree = None
    for index, (label, hashes) in enumerate((("hot-reload-upgrade", hot["hashes"]),
                                            ("hot-reload-rollback", manifest["packageHashes"]))):
        retained = root / "retained" / label
        observed = json.loads(read_regular(retained / "observation.json"))
        payload = json.loads(read_regular(root / "commands" / label / "stdout.json"))
        selected, turn = payload.get("installedPath"), observed.get("turnId")
        if (not isinstance(selected, str) or not isinstance(turn, str) or not turn
                or not Path(selected).is_relative_to(manifest["ownedRoots"]["home"])
                or index == 0 and selected == installed or index == 1 and selected != installed
                or _tree_hashes(retained / "installed-package") != hashes
                or observed.get("installedPath") != selected or observed.get("threadId") != thread
                or observed.get("providerOrdinal") != index + 5
                or commands[label].get("arguments") != ["-c", 'cli_auth_credentials_store="file"',
                    "plugin", "add", PLUGIN_ID, "--json"]):
            raise ValueError("hot-reload installed identity, CLI or bytes differ")
        request = requests[starts[index + 1]]
        if (request.get("params") != {"threadId": thread, "input": [{"type": "text", "text": HOT_PROMPTS[index]}]}
                or not any(row.get("id") == request.get("id") and row.get("result", {}).get("turn", {}).get("id") == turn for row in native)
                or not any(row.get("method") == "turn/completed" and row.get("params", {}).get("threadId") == thread
                    and row["params"].get("turn", {}).get("id") == turn
                    and row["params"]["turn"].get("status") == "completed" for row in native)):
            raise ValueError("hot-reload native turn identity or terminal differs")
        before, after = observed["beforeTurn"], observed["afterTurn"]
        context = _latest_input_context(provider_rows[index + 4]["request"])
        if (before != prior or not _checkpoint_matches(after, source_hash, index + 3)
                or after.get("checkpoint") != prior.get("checkpoint") or after.get("epoch") == prior.get("epoch")
                or after.get("currentInputReconciled") is not False or after.get("hostObservationCurrent") is not True
                or after.get("hostObservation", {}).get("turnId") != turn
                or not _contains_path(context, Path(selected) / "runtime/task-checkpoint.cjs")
                or f"Native input receipt: session={thread}; epoch={after['epoch']}." not in context
                or not _hot_hooks_match(observed["hooks"], trust, Path(selected))):
            raise ValueError("hot-reload current input, checkpoint or unchanged trust differs")
        hook_request = requests[starts[index + 1] + 1]
        if not any(row.get("id") == hook_request.get("id") and row.get("result") == observed["hooks"] for row in native):
            raise ValueError("hot-reload Hook list has no native response")
        before_hashes = _tree_hashes(retained / "before-install-state")
        if (before_hashes != _tree_hashes(retained / "after-install-state")
                or previous_tree is not None and before_hashes != previous_tree):
            raise ValueError("hot-reload installation changed owned task state")
        after_hashes = _tree_hashes(retained / "after-turn-state")
        state_files = {name: value for name, value in before_hashes.items() if name.endswith(".state.json")}
        if not state_files or state_files != {name: value for name, value in after_hashes.items() if name.endswith(".state.json")}:
            raise ValueError("hot-reload changed saved paused responsibility bytes")
        receipts = [json.loads(read_regular(retained / "after-turn-state" / name))
                    for name in after_hashes if name.endswith(".input.json")]
        current = [row for row in receipts if row.get("epoch") == after["epoch"] and row.get("turnId") == turn]
        if len(current) != 1:
            raise ValueError("hot-reload native input receipt missing")
        receipt = current[0]
        inputs = receipt.get("nativeInputs", [])
        previous_receipts = [json.loads(read_regular(retained / "before-install-state" / name))
                             for name in before_hashes if name.endswith(".input.json")]
        previous = [row for row in previous_receipts if row.get("epoch") == prior["epoch"]]
        if (receipt.get("inputSource") != "native-input-event" or len(inputs) != index + 3
                or len(previous) != 1 or previous[0].get("nativeInputs") != inputs[:-1]
                or inputs[-1] != {"epoch": after["epoch"], "turnId": turn, "source": "native-input-event",
                    "promptSha256": hashlib.sha256(HOT_PROMPTS[index].encode()).hexdigest(), "prompt": HOT_PROMPTS[index]}):
            raise ValueError("hot-reload native receipt content differs")
        prior, previous_tree = after, after_hashes


def inspect(evidence):
    manifest = _load(evidence)
    root = Path(manifest["evidence"])
    result = json.loads(read_regular(root / "result.json", 4 * 1024 * 1024))
    started = json.loads(read_regular(root / "run-started.json"))
    if (started.get("manifestSha256") != digest(root / "manifest.json")
            or tuple(started.get("nativeResourceLabels", ())) != RESOURCE_LABELS
            or tuple(started.get("nativeCommandLabels", ())) != tuple(manifest["nativeCommandLabels"])):
        raise ValueError("execution does not match prepared manifest")
    controller = manifest.get("resourceController", "windows-job-object")
    if ("resourceController" in manifest
            and (started.get("resourceController") != controller
                 or result.get("resourceController") != controller
                 or result.get("resourceEvidenceScope") != _resource_scope(controller))):
        raise ValueError("execution resource controller differs from prepared scope")
    resource_error = None
    try:
        records = read_native_resource_records(root / "native", manifest["nativeResourceLabels"])
        resources_ok = all(record["exitCode"] == 0 and _record_released(record, manifest)
                           for record in records.values())
    except (OSError, ValueError, json.JSONDecodeError):
        records, resources_ok = {}, False
        resource_error = "native resource record set incomplete or invalid"
    raw_error = None
    try:
        observed_commands = {path.name for path in (root / "commands").iterdir() if path.is_dir()}
        if observed_commands != set(manifest["nativeCommandLabels"]):
            raise ValueError("command record set differs")
        command_records = {label: json.loads(read_regular(root / "commands" / label / "record.json"))
                           for label in manifest["nativeCommandLabels"]}
        for label in manifest["nativeCommandLabels"]:
            _regular_file(root / "commands" / label / "stdout.json")
            _regular_file(root / "commands" / label / "stderr.txt")
        if (any(command_records[label].get("exitCode") != 0 for label in manifest["nativeCommandLabels"] if label != "invalid-candidate")
                or command_records["invalid-candidate"].get("exitCode") in (None, 0)):
            raise ValueError("command terminal differs")
        if any(not _record_released(record, manifest) for record in command_records.values()):
            raise ValueError("command process release unobserved or controller differs")
        if any(record.get("arguments", [])[:2] != ["-c", 'cli_auth_credentials_store="file"']
               for record in command_records.values()):
            raise ValueError("command credential-store boundary differs")
        installed_payload = json.loads(read_regular(root / "commands/package-add/stdout.json"))
        loaded = result.get("loadedObject", {})
        installed_path = installed_payload.get("installedPath")
        if (not isinstance(installed_path, str)
                or not Path(installed_path).is_relative_to(Path(manifest["ownedRoots"]["home"]))
                or installed_path != result.get("installedPathReturned")
                or loaded.get("installedPath") != installed_path
                or not loaded.get("hookSourcePaths") or not loaded.get("skillPaths")
                or any(not Path(path).is_relative_to(Path(installed_path))
                       for path in (*loaded["hookSourcePaths"], *loaded["skillPaths"]))):
            raise ValueError("installed and loaded package identities differ")
        for label in RESOURCE_LABELS:
            for name in ("stdout.jsonl", "stderr.txt", "requests.jsonl", "resources.json"):
                _regular_file(root / "native" / label / name)
        provider_rows = [json.loads(line) for line in read_regular(root / "retained/provider-requests.jsonl").decode("utf-8").splitlines() if line]
        if ([row.get("ordinal") for row in provider_rows] != list(range(1, manifest["limits"]["providerRequests"] + 1))
                or any(not isinstance(row.get("request"), dict) for row in provider_rows)):
            raise ValueError("provider receipts differ")
        controls = [skill for skill in _skill_rows(json.loads(read_regular(root / "retained/skills-before.json")))
                    if skill.get("path") == manifest["standaloneSkill"]["path"]]
        if (len(controls) != 1 or not controls[0].get("name")
                or _contains_path(provider_rows, manifest["standaloneSkill"]["path"])
                or any(controls[0]["name"].casefold() in text.casefold() for text in _strings(provider_rows))):
            raise ValueError("standalone control remains in provider input")
        provider_responses = [json.loads(read_regular(root / "retained" / f"provider-response-{ordinal}.json"))
                              for ordinal in range(1, manifest["limits"]["providerRequests"] + 1)]
        if any(not _provider_response_matches(row, ordinal)
               for ordinal, row in enumerate(provider_responses, 1)):
            raise ValueError("provider response receipts differ")
        helper_rows = [json.loads(line) for line in read_regular(root / "retained/helper.jsonl").decode("utf-8").splitlines() if line]
        if (not helper_rows or not any(row.get("phase") == "request" for row in helper_rows)
                or not any(row.get("phase") == "response" for row in helper_rows)):
            raise ValueError("helper receipts absent")
        paused_thread = json.loads(read_regular(root / "retained/paused-thread.json"))["threadId"]
        critical_requests = [row["request"] for row in helper_rows if row.get("phase") == "request"
                             and row.get("request", {}).get("op") in {"bind", "pause"}]
        if (not isinstance(paused_thread, str) or not paused_thread
                or {request.get("session_id") for request in critical_requests} != {paused_thread}):
            raise ValueError("helper thread identity differs")
        resumed_requests = [json.loads(line) for line in read_regular(root / "native/resumed/requests.jsonl").decode("utf-8").splitlines() if line]
        if (not any(row.get("method") == "thread/resume" and row.get("params", {}).get("threadId") == paused_thread
                    for row in resumed_requests)
                or not any(row.get("method") == "turn/start" and row.get("params", {}).get("threadId") == paused_thread
                           for row in resumed_requests)):
            raise ValueError("native resume identity differs")
        source_hash = manifest["initialRootHashes"]["workspace"]["source.json"]
        if result.get("sourceHashAfter") != source_hash:
            raise ValueError("protected source poststate differs")
        snapshots = {name: json.loads(read_regular(root / "retained" / (name + ".json"))) for name in
            ("before-pause", "after-interrupt", "after-exit", "resumed-before-continue", "after-resume")}
        expected_counts = {"before-pause": 1, "after-interrupt": 1, "after-exit": 1,
                           "resumed-before-continue": 1, "after-resume": 2}
        if (any(not _checkpoint_matches(value, source_hash, expected_counts[name]) for name, value in snapshots.items())
                or snapshots["after-interrupt"]["epoch"] != snapshots["after-exit"]["epoch"]
                or snapshots["after-interrupt"]["checkpoint"] != snapshots["after-resume"]["checkpoint"]
                or snapshots["after-resume"]["epoch"] == snapshots["after-exit"]["epoch"]):
            raise ValueError("checkpoint receipts differ")
        preserved = json.loads(read_regular(root / "retained/invalid-candidate-preserved.json"))
        after_uninstall = json.loads(read_regular(root / "retained/state-after-uninstall.json"))
        if preserved.get("package") != manifest["packageHashes"] or preserved.get("state") != after_uninstall:
            raise ValueError("package or unfinished state evidence differs")
        if manifest.get("case") == HOT_CASE:
            _inspect_hot_reload(manifest, installed_path, paused_thread, snapshots["after-resume"],
                                provider_rows, resumed_requests, command_records, records)
        command_raw_complete = True
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError, UnicodeError):
        command_records, command_raw_complete = {}, False
        raw_error = "native command or semantic receipt set incomplete or invalid"
    required_true = ("mechanismComplete", "loopbackListenerClosed", "providerBound",
        "malformedCandidateRejectedWithoutReplacement", "healthyRetryExact",
        "nativeUninstallRemovesCacheAndDiscovery", "unfinishedStatePreservedAcrossExitAndUninstall",
        "exactPackageLoadedAndTrusted", "sessionEndEnabledDisabledContrast",
        "nativeInterruptInvalidatesReadiness", "nativeResumePreservesPausedBinding",
        "continueReceiptDoesNotResumeBinding", "selectedPathsDisabledInOwnedProcess",
        "protectedSharedFilesUnchanged", "sharedSettingsAndSelectionsPreserved", "standaloneCatalogEntryAbsent")
    decision = (result.get("failure") is None and result.get("modelCalls") == 0
        and result.get("credentialHeaderSeen") is False and resources_ok and command_raw_complete
        and all(result.get(key) is True for key in required_true)
        and result.get("protectedFileHashesAfter") == manifest["protectedFiles"]
        and result.get("ownedRootsAbsent") == {name: True for name in OWNED_ROOTS})
    return {"decision": "pass" if decision else "fail", "nativeResources": records,
        "resourceError": resource_error, "nativeCommands": command_records, "rawEvidenceError": raw_error,
        "recorded": result, "claimLimit": manifest["claimLimit"],
        "resourceController": controller, "resourceEvidenceScope": _resource_scope(controller)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="action", required=True)
    prep = sub.add_parser("prepare")
    for name in ("package", "evidence", "marketplace-manifest", "codex", "node"):
        prep.add_argument("--" + name, required=True)
    prep.add_argument("--protected-file", action="append", required=True,
                      help="repeat for each necessary shared file; hashes only, contents are not copied")
    prep.add_argument("--hot-reload", action="store_true",
                      help="bind a version-only isolated build and rollback in one already Accord-bound paused thread; six fixed responses and two extra CLI commands")
    prep.add_argument("--timeout", type=int, required=True,
                      help="prospectively justified whole-episode limit; no product default")
    prep.add_argument("--request-timeout", type=int, required=True,
                      help="per native request/turn ceiling within the whole deadline")
    prep.add_argument("--recovery-timeout", type=int, required=True,
                      help="single non-renewing cleanup reserve per owned process")
    for action in ("run", "inspect"):
        item = sub.add_parser(action)
        item.add_argument("--evidence", required=True)
    args = parser.parse_args()
    if args.action == "prepare":
        result = prepare(args)
    elif args.action == "run":
        result = run(args)
    else:
        result = inspect(args.evidence)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if ((args.action == "run" and (result.get("failure") is not None or result.get("mechanismComplete") is not True))
            or (args.action == "inspect" and result.get("decision") != "pass")):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
