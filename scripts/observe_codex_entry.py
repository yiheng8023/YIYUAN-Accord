"""Prepare/run a bounded Codex CLI observation or prepare an App Server case.

No model is called by prepare or inspect. Run uses existing CODEX_HOME auth,
explicit model/effort, workspace-write and reviewed task-local hooks. The default
case is ephemeral; a persistent coordination case uses native exec/resume and the
existing stage oracle. Neither establishes full plugin or resource acceptance.
Optional --native-package-hooks projects every package Node hook registration
directly into an isolated persistent CLI process. It binds all package bytes,
keeps the existing CODEX_HOME authentication location and quotes the bound Node
absolute path for a frozen supported shell (PATH priority is supplementary).
Stage prompts and resume commands remain bound to the original case and observed
source thread. This is source configuration projection, not marketplace-installed
plugin or implicit Skill registration evidence; no checkpoint wrapper logs exist.
Optional --installed-plugin instead uses the existing native installation and
user configuration without injecting hooks or bypassing trust. Bind the native
inventory and installed bytes, then independently require actual entry delivery.
Optional --admission-case checks a committed case's conditions.execution against
the prepared run and exact package before dispatch. It creates no admission facts.
Windows Job Objects contain descendants before the suspended CLI starts executing.
The caller must select an existing Windows sandbox backend explicitly; this runner
does not initialize/install a sandbox or directly edit shared configuration.
Native thread startup may persist workspace trust. The caller owns authorization
and exact recovery of that registration; before/after observations do not undo it.
Evidence and deliverables are retained for review; owned live processes are released.
The Python prepare API accepts an explicit app_server_case for a caller-owned
dispatcher; inspect then checks that protocol and its actual input receipts.
Optional limits.usageCaps names native cumulative token dimensions explicitly.
The persistent CLI runner enforces observed cumulative caps while retaining its
independent time, output, interruption and cleanup bounds.
"""

import argparse
import csv
import ctypes
import hashlib
import io
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import signal
import stat
import subprocess
import sys
import time
import uuid

try:
    import tomllib
except ModuleNotFoundError:  # Python 3.10 has no standard-library TOML parser.
    tomllib = None

if os.name == "nt":
    from ctypes import wintypes as W

EVENTS = ("UserPromptSubmit", "Stop", "SessionEnd", "Interrupt")
HOOK_MODES = ("checkpoint-wrapper", "native-package-hooks", "installed-plugin")
PROMPT = "请使用这个目录提供的订单数据接口，整理已经备妥的订单，按原顺序生成 details.csv（id,units 两列）、summary.json（ready_ids 和 total_units 两项）以及简短的 report.md。不要把待处理订单算进去。保留原始材料和无关文件，检查实际交付文件后告诉我结果。本次只处理本地材料，不联网、不安装软件、不修改共享设置。"
ORDERS = b"id,status,units\nA,ready,60\nB,ready,80\nC,pending,50\n"
SOURCE = '''import json
from pathlib import Path
import sys
root = Path(__file__).resolve().parent
state = root / ".source-attempts.json"
attempts = json.loads(state.read_text()) if state.exists() else []
attempts.append({"attempt": len(attempts) + 1, "exit": 75 if not attempts else 0})
state.write_text(json.dumps(attempts), encoding="utf-8")
if len(attempts) == 1:
    print("Local order source temporarily unavailable. Retry this same command.", file=sys.stderr)
    raise SystemExit(75)
sys.stdout.buffer.write((root / "orders.csv").read_bytes())
'''
LIMITS = {"nativeCliInvocations": 1, "backendRequests": "not separately capped; tool-loop requests share the explicit wall-clock cap and native usage stream",
          "interaction": "single ephemeral exec; no second-turn correction or restart-resume proof",
          "acceptance": "task-isolated mechanism observation only; no full plugin/custom-environment/system acceptance",
          "resources": "owned job CPU, working-set RAM, PIDs and exit; GPU/VRAM and system-wide I/O/load recovery unmeasured",
          "evidence": "raw files retained; hashes are provenance aids, not adversarial attestation"}


def read_regular(path, limit=8 * 1024 * 1024):
    path = Path(path)
    info = path.lstat()
    if (not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or path.is_symlink()
            or getattr(info, "st_file_attributes", 0) & 0x400 or info.st_size > limit):
        raise ValueError("not a bounded ordinary file: " + str(path))
    return path.read_bytes()


def digest(path, *, os_shell=False):
    path = Path(path)
    before = path.lstat()
    # Windows servicing hard-links its system shells. Accept those
    # OS-owned links only for the explicitly bound default shell, never package,
    # credentials, inputs, executable Node or any prior evidence hash source.
    system = Path(os.environ.get("SystemRoot", "C:/Windows")) / "System32"
    allowed_os_shell = (os_shell and os.name == "nt" and path in {
        (system / "cmd.exe").resolve(), (system / "WindowsPowerShell/v1.0/powershell.exe").resolve()})
    if (not stat.S_ISREG(before.st_mode) or (before.st_nlink != 1 and not allowed_os_shell) or path.is_symlink()
            or getattr(before, "st_file_attributes", 0) & 0x400 or before.st_size > 1024 * 1024 * 1024):
        raise ValueError("unsafe or oversized hash source")
    result = hashlib.sha256()
    with path.open("rb") as stream:
        opened = os.fstat(stream.fileno())
        if (opened.st_ino, opened.st_size) != (before.st_ino, before.st_size):
            raise ValueError("hash source changed")
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            result.update(chunk)
    after = path.lstat()
    if (after.st_ino, after.st_size, after.st_mtime_ns) != (before.st_ino, before.st_size, before.st_mtime_ns):
        raise ValueError("hash source changed")
    return result.hexdigest()


def save(path, value):
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _usage_caps(caps):
    allowed = {"totalTokens", "inputTokens", "uncachedInputTokens", "cachedInputTokens", "outputTokens"}
    if (not isinstance(caps, dict) or set(caps) - allowed
            or any(type(value) is not int or value < 0 for value in caps.values())):
        raise ValueError("usage caps must name supported token dimensions with nonnegative integer limits")
    return dict(caps)


def app_server_usage_budget(stream, *, thread_id, caps=None):
    """Read cumulative native receipts, preserving explicit limits and unknowns.

The caller binds the actual connection/thread and a prospective case. These are
reported thread totals, not a resumed turn's incremental cost. Never sum repeated
cumulative receipts, substitute last/total for occupancy, or assign token prices.
Missing, invalid or decreasing counters leave budget availability unknown; the
caller retains independent deadlines and must not interpret unknown as permission.
This read-only diagnostic neither enforces a spending cap nor authenticates logs.
"""
    caps = _usage_caps({} if caps is None else caps)
    result = {"decision": "unknown", "observed": None, "caps": caps, "exceeded": [],
              "receipts": 0, "firstExceededReceipt": None, "contextOccupancy": None, "monetaryCost": None,
              "scope": "reported cumulative thread usage; not current occupancy, per-turn cost or completion"}
    if not isinstance(thread_id, str) or not thread_id:
        return result
    try:
        if len(stream.encode("utf-8")) > 32 * 1024 * 1024:
            return result
        previous = None
        for line in stream.splitlines():
            if not line.strip():
                continue
            event = json.loads(line)
            if not isinstance(event, dict):
                return result
            if event.get("method") != "thread/tokenUsage/updated" or "id" in event:
                continue
            params = event["params"]
            if params["threadId"] != thread_id:
                continue
            total = params["tokenUsage"]["total"]
            current = {key: total[key] for key in ("totalTokens", "inputTokens", "cachedInputTokens", "outputTokens")}
            if (any(type(value) is not int or value < 0 for value in current.values())
                    or current["cachedInputTokens"] > current["inputTokens"]):
                return result
            current["uncachedInputTokens"] = current["inputTokens"] - current["cachedInputTokens"]
            if previous is not None and any(current[key] < previous[key] for key in current):
                return result
            previous = current
            result["receipts"] += 1
            result["exceeded"] = sorted(set(result["exceeded"]) | {key for key, limit in caps.items() if current[key] > limit})
            if result["exceeded"] and result["firstExceededReceipt"] is None:
                result["firstExceededReceipt"] = result["receipts"]
        if previous is not None:
            result["observed"] = previous
            result["decision"] = ("over-limit" if result["exceeded"] else
                                  "within-observed-limits" if caps else "observe-only")
    except (KeyError, TypeError, AttributeError, ValueError, UnicodeError):
        pass
    return result


def shared_config_snapshot(config, workspace):
    """Observe the exact workspace registration without exposing other config values."""
    try:
        data = read_regular(config)
        if tomllib is None:
            return {"state": "observed", "sha256": hashlib.sha256(data).hexdigest(),
                    "workspaceRegistrations": None, "registrationState": "unavailable",
                    "reason": "toml-parser-unavailable"}
        parsed = tomllib.loads(data.decode("utf-8"))
        target = os.path.normcase(os.path.abspath(workspace))
        projects = parsed.get("projects", {})
        if not isinstance(projects, dict):
            raise ValueError("invalid project registration table")
        owned = {key: {"trustLevel": value.get("trust_level")}
                 for key, value in projects.items() if isinstance(value, dict)
                 and os.path.normcase(os.path.abspath(key)) == target}
        return {"state": "observed", "sha256": hashlib.sha256(data).hexdigest(),
                "workspaceRegistrations": owned}
    except (OSError, ValueError, UnicodeError) as error:
        return {"state": "unavailable", "reason": type(error).__name__}


def ordinary_dir(path):
    path = Path(path).absolute()
    if path.resolve() != path or path.is_symlink():
        raise ValueError("directory alias not allowed")
    info = path.stat()
    if not stat.S_ISDIR(info.st_mode) or getattr(info, "st_file_attributes", 0) & 0x400:
        raise ValueError("ordinary directory required")
    return path


def load_manifest(evidence):
    evidence = ordinary_dir(evidence)
    manifest = json.loads(read_regular(evidence / "manifest.json"))
    if manifest["evidence"] != str(evidence) or manifest["schema"] != "accord-codex-entry/v1":
        raise ValueError("manifest binding mismatch")
    protocol = manifest.get("entryProtocol", "exec")
    _hook_mode(manifest)
    if protocol not in ("exec", "exec-resume", "app-server"):
        raise ValueError("unsupported entry protocol")
    if (protocol == "exec-resume" and manifest.get("caseSchema", "yiyuan-accord-coordination-case/v1")
            not in ("yiyuan-accord-coordination-case/v1", "yiyuan-accord-scoped-task-case/v1")):
        raise ValueError("unsupported persistent case schema")
    if protocol == "app-server" and ("command" in manifest or "promptSha256" in manifest
                                     or manifest.get("tracePath") != "native/stdout.jsonl"):
        raise ValueError("App Server manifest contains incompatible CLI or trace metadata")
    if "usageCaps" in manifest["limits"]:
        _usage_caps(manifest["limits"]["usageCaps"])
    ordinary_dir(manifest["workspace"])
    return manifest


def _hook_mode(manifest):
    mode = manifest.get("hookMode", "checkpoint-wrapper")
    if mode not in HOOK_MODES:
        raise ValueError("unsupported hook mode")
    if mode in ("native-package-hooks", "installed-plugin") and manifest.get("entryProtocol") != "exec-resume":
        raise ValueError("native package hooks require persistent exec-resume")
    return mode


def _direct_package_hooks(manifest):
    return _hook_mode(manifest) in ("native-package-hooks", "installed-plugin")


def _toml_value(value):
    # Inline tables retain registration boundaries and all manifest fields.
    if isinstance(value, dict) and all(isinstance(key, str) for key in value):
        return "{" + ",".join(json.dumps(key) + "=" + _toml_value(item) for key, item in value.items()) + "}"
    if isinstance(value, list):
        return "[" + ",".join(_toml_value(item) for item in value) + "]"
    if isinstance(value, (str, bool)) or type(value) is int:
        return json.dumps(value, ensure_ascii=False)
    raise ValueError("hook field cannot be faithfully projected to TOML")


def _native_hook_shell():
    """Follow the supported native user-shell selection, not the engine fallback.

    rust-v0.154.0 session/mod.rs build_hooks_config supplies TurnEnvironment.shell.
    shell_detect.rs prefers PowerShell on Windows; COMSPEC is only a fallback.
    """
    if os.name == "nt":
        candidates = [shutil.which("pwsh"), r"C:\Program Files\PowerShell\7\pwsh.exe",
                      shutil.which("powershell"), str(Path(os.environ.get("SystemRoot", "C:/Windows")) /
                          "System32/WindowsPowerShell/v1.0/powershell.exe")]
        for value in candidates:
            if value and Path(value).is_file():
                path = Path(value).resolve()
                if any(part.lower() == "windowsapps" for part in path.parts):
                    raise ValueError("native Store shell requires separately verified sandbox-compatible resolution")
                return path, "powershell"
        return (Path(os.environ.get("SystemRoot", "C:/Windows")) / "System32/cmd.exe").resolve(), "cmd"
    import pwd
    selected = Path(pwd.getpwuid(os.getuid()).pw_shell)
    if selected.name in {"bash", "zsh", "sh", "pwsh", "powershell"} and selected.is_file():
        return selected.resolve(), "powershell" if selected.name in {"pwsh", "powershell"} else "posix"
    for name in (("zsh", "bash", "sh") if sys.platform == "darwin" else ("bash", "zsh", "sh")):
        value = shutil.which(name)
        if value:
            return Path(value).resolve(), "posix"
    raise ValueError("native command shell unavailable")


def _entry_guide(node, runtime):
    result = subprocess.run([str(node), "-e",
        "process.stdout.write(require(process.argv[1]).entryGuidance())", str(runtime)],
        capture_output=True, timeout=10)
    guide = result.stdout.decode("utf-8")
    if result.returncode or not guide.startswith("Accord task entry:") or len(result.stdout) > 100000:
        raise ValueError("current package entry guidance unavailable")
    return guide


def _package_hashes(package):
    package = ordinary_dir(package)
    files = {}
    def inaccessible(error):
        raise error
    for directory, children, names in os.walk(package, followlinks=False, onerror=inaccessible):
        ordinary_dir(directory)
        for child in children:
            ordinary_dir(Path(directory) / child)
        for name in names:
            path = Path(directory) / name
            files[path.relative_to(package).as_posix()] = digest(path)
    return dict(sorted(files.items()))


def _native_inventory(codex, market, workspace, evidence, label):
    # Reuse lifecycle command containment and receipts. This lazy import avoids
    # loading its fixture machinery for the established source-projection modes.
    repo = str(Path(__file__).resolve().parents[1])
    if repo not in sys.path:
        sys.path.insert(0, repo)
    from scripts.observe_codex_lifecycle import _run_cli
    root = Path(evidence) / "installed-inventory"
    (root / "commands").mkdir(parents=True, exist_ok=True)
    if (root / "commands" / label).exists():
        raise ValueError("inventory receipt already exists; preserve the original attempt")
    manifest = {"codex": str(codex), "evidence": str(root),
                "ownedRoots": {"workspace": str(workspace)},
                "limits": {"requestSeconds": 20, "recoverySeconds": 15},
                "resourceController": "windows-job-object" if os.name == "nt" else "posix-session-process-group"}
    config = Path(os.environ.get("CODEX_HOME", str(Path.home() / ".codex"))) / "config.toml"
    before = shared_config_snapshot(config, workspace)
    try:
        record, data = _run_cli(manifest, label, ["plugin", "list", "--marketplace", market, "--json"],
                               dict(os.environ), time.monotonic() + 20, auth_store_override=None)
    finally:
        after = shared_config_snapshot(config, workspace)
        unchanged = before["state"] == after["state"] == "observed" and before["sha256"] == after["sha256"]
        save(root / "commands" / label / "shared-config.json", {"before": before, "after": after, "unchanged": unchanged})
    if record["exitCode"] != 0 or record["forced"] or record["failure"]:
        raise ValueError("native installed plugin inventory failed; inspect retained command receipt")
    if not unchanged:
        raise ValueError("native inventory shared configuration changed or is unknown")
    return data


def _installed_package_identity(package, plugin_id):
    """Validate local identity without starting a process or creating fixture roots."""
    if not isinstance(plugin_id, str) or not re.fullmatch(r'[A-Za-z0-9_-]+@[A-Za-z0-9_-]+', plugin_id):
        raise ValueError("explicit installed plugin name@marketplace required")
    name, market = plugin_id.split("@")
    package = ordinary_dir(package)
    codex_home = ordinary_dir(os.environ.get("CODEX_HOME", str(Path.home() / ".codex")))
    metadata = json.loads(read_regular(package / ".codex-plugin/plugin.json"))
    version = metadata.get("version") if isinstance(metadata, dict) else None
    if (not isinstance(version, str) or not re.fullmatch(r'[A-Za-z0-9_.+-]+', version)
            or metadata.get("name") != name
            or package != codex_home / "plugins/cache" / market / name / version):
        raise ValueError("package is not the named native installed cache root")
    return package, codex_home, name, market, version


def _installed_plugin_binding(package, codex, plugin_id, workspace, evidence, label):
    package, codex_home, name, market, version = _installed_package_identity(package, plugin_id)
    data = _native_inventory(codex, market, workspace, evidence, label)
    if not isinstance(data, dict) or not isinstance(data.get("installed"), list):
        raise ValueError("native installed plugin inventory unavailable")
    rows = [row for row in data["installed"] if isinstance(row, dict) and row.get("pluginId") == plugin_id]
    if (len(rows) != 1 or rows[0].get("enabled") is not True or rows[0].get("installed") is not True
            or rows[0].get("version") != version or rows[0].get("name") != name
            or rows[0].get("marketplaceName") != market or not isinstance(rows[0].get("source"), dict)
            or rows[0]["source"].get("source") not in ("local", "git", "npm")):
        raise ValueError("native installed plugin is absent, disabled or differs")
    return {"codexHome": str(codex_home), "pluginId": plugin_id, "inventory": rows[0],
            "packageFiles": _package_hashes(package),
            "claimLimit": "installed catalog and byte binding; actual entry delivery and behavior require separate native receipts; existing user configuration and other components remain active"}


def _native_hook_projection(package, node):
    package = ordinary_dir(package)
    node = Path(node).resolve()
    shell, shell_kind = _native_hook_shell()
    if any(c in str(node) for c in ('"', '\n', '\r', '%', '!', '`', '$', '&', '|', '<', '>', '^')):
        raise ValueError("shell-sensitive Node path cannot be projected")
    files = _package_hashes(package)
    metadata = json.loads(read_regular(package / ".codex-plugin/plugin.json"))
    # These surfaces require plugin loading semantics, not a hooks override.
    if (not isinstance(metadata, dict)
            or set(metadata) - {"name", "version", "description", "author", "homepage", "repository",
                                "license", "keywords", "skills", "interface"}
            or metadata.get("skills", "./skills/") != "./skills/"
            or any(name in files for name in (".mcp.json", ".app.json"))):
        raise ValueError("unsupported plugin manifest override or non-hook component")
    definition = json.loads(read_regular(package / "hooks/hooks.json"))
    if not isinstance(definition, dict) or set(definition) != {"hooks"} or not isinstance(definition["hooks"], dict):
        raise ValueError("unsupported hook definition")
    projected = json.loads(json.dumps(definition["hooks"]))
    sources = set()
    for event, registrations in projected.items():
        if event not in (*EVENTS, "SessionStart") or not isinstance(registrations, list) or not registrations:
            raise ValueError("unsupported hook event or registrations")
        for registration in registrations:
            if not isinstance(registration, dict) or not isinstance(registration.get("hooks"), list) or not registration["hooks"]:
                raise ValueError("unsupported hook registration")
            for handler in registration["hooks"]:
                if not isinstance(handler, dict) or handler.get("type") != "command":
                    raise ValueError("only native Node command hooks can be projected")
                command = handler.get("command", "")
                match = re.fullmatch(r'node "\$\{PLUGIN_ROOT\}/(runtime/[A-Za-z0-9_.-]+\.cjs)"(?: --hook ([A-Za-z]+))?', command)
                if not match or match[2] not in (None, event) or match[1] not in files:
                    raise ValueError("unsupported native Node hook command or source")
                sources.add(match[1])
                # The core supplies its detected user shell. A quoted executable
                # is a string in PowerShell until the call operator invokes it.
                handler["command"] = ("& " if shell_kind == "powershell" else "") + '"' + node.as_posix() + '"' + command[len("node"):].replace("${PLUGIN_ROOT}", package.as_posix())
    configuration = "hooks=" + _toml_value(projected)
    return {"sourceConfigurationOnly": True, "marketplaceInstalled": False,
            "definition": definition, "hooks": projected, "configuration": configuration,
            "sourceFiles": sorted(sources), "packageFiles": dict(sorted(files.items())), "node": str(node),
            "hookShell": str(shell), "shellKind": shell_kind,
            "commandShellContract": "rust-v0.154.0: core TurnEnvironment user shell; PowerShell call operator or POSIX/cmd absolute invocation, not COMSPEC/SHELL fallback inference",
            "claimLimit": "source configuration projection of native hooks only; no marketplace installation, implicit Skill registration or complete plugin acceptance"}


def _verify_prepared_sources(manifest, *, inventory_label="run-preflight"):
    mode = _hook_mode(manifest)
    installed_observation = None
    for key, expected in manifest["sourceHashes"].items():
        if digest(manifest[key], os_shell=key == "hookShell") != expected:
            raise ValueError("prepared source changed; prepare a fresh observation: " + key)
    if mode == "native-package-hooks" and _native_hook_projection(manifest["package"], manifest["node"]) != manifest.get("nativeHookProjection"):
        raise ValueError("prepared package or native hook projection changed; prepare a fresh observation")
    if mode == "installed-plugin":
        binding = manifest["installedPlugin"]
        installed_observation = _installed_plugin_binding(manifest["package"], manifest["codex"], binding["pluginId"], manifest["workspace"], manifest["evidence"], inventory_label)
        if installed_observation != binding:
            raise ValueError("prepared installed plugin changed; prepare a fresh observation")
    if _direct_package_hooks(manifest):
        guide = manifest.get("entryGuide")
        if (not isinstance(guide, str) or not guide.startswith("Accord task entry:")
                or hashlib.sha256(guide.encode("utf-8")).hexdigest() != manifest.get("entryGuideSha256")):
            raise ValueError("prepared entry guide changed")
    if "admissionBinding" in manifest:
        bound = manifest["admissionBinding"]
        if _admission_binding(manifest, bound["case"]) != bound:
            raise ValueError("prepared admission binding changed")
    return installed_observation


def _admission_binding(manifest, case_id):
    project = Path(__file__).resolve().parents[1]
    if str(project) not in sys.path:
        sys.path.insert(0, str(project))
    from yiyuan_accord.admission import bind_evidence_execution
    version = manifest["nativeVersion"]
    match = re.fullmatch(r"codex-cli ([0-9]+\.[0-9]+\.[0-9]+(?:[-+][0-9A-Za-z.-]+)?)", version)
    if not match:
        raise ValueError("admission binding requires an exact native version receipt")
    execution = {key: manifest[key] for key in (
        "entryProtocol", "hookMode", "model", "reasoning", "windowsSandbox",
        "timeoutSeconds", "turnTimeoutSeconds", "recoveryTimeoutSeconds", "caseSha256")}
    execution.update(host="codex", entry="cx-cli", codexVersion=match[1],
                     usageCaps=manifest["limits"]["usageCaps"], usageScope=manifest["limits"]["usageScope"],
                     runner=Path(manifest["runner"]).relative_to(project).as_posix(),
                     caseFile=Path(manifest["case"]).relative_to(project).as_posix())
    return bind_evidence_execution(project, case_id, execution, _package_hashes(manifest["package"]))


def _verify_native_stage(manifest, stage, thread_id):
    installed_observation = _verify_prepared_sources(manifest, inventory_label=f"stage-{stage + 1}-before")
    case = json.loads(read_regular(manifest["case"]))
    if type(stage) is not int or not 0 <= stage < len(case["stages"]):
        raise ValueError("invalid native persistent stage")
    raw = read_regular(Path(manifest["evidence"]) / f"prompt-{stage + 1}.txt")
    prompt = case["stages"][stage]["prompt"]
    if (hashlib.sha256(raw).hexdigest() != manifest["promptSha256s"][stage]
            or raw != prompt.encode("utf-8") or manifest["prompts"][stage] != prompt):
        raise ValueError("prepared stage prompt changed or differs from bound case")
    if stage:
        stream = read_regular(Path(manifest["evidence"]) / "stdout-1.jsonl", 32 * 1024 * 1024)
        starts = [event.get("thread_id") for event in (json.loads(line) for line in stream.splitlines() if line.strip())
                  if isinstance(event, dict) and event.get("type") == "thread.started"]
        if len(starts) != 1 or not isinstance(starts[0], str) or not starts[0] or starts[0] != thread_id:
            raise ValueError("resume thread id is not the uniquely observed initial source")
    command = build_command(manifest, stage=stage, thread_id=thread_id)
    expected = list(manifest["stageCommandTemplates"][stage])
    if stage:
        if expected[-2] != "__OBSERVED_NATIVE_THREAD_ID__":
            raise ValueError("prepared stage command template changed")
        expected[-2] = thread_id
    if command != expected or (stage == 0 and command != manifest["initialCommand"]):
        raise ValueError("prepared stage command changed")
    return raw, command, installed_observation


def _hook_configuration(manifest):
    if _hook_mode(manifest) == "installed-plugin":
        raise ValueError("installed plugin must use native hook discovery")
    if _hook_mode(manifest) == "native-package-hooks":
        return manifest["nativeHookProjection"]["configuration"]
    hooks = []
    for event in EVENTS:
        parts = [manifest["python"], "-B", manifest["runner"], "hook", "--evidence", manifest["evidence"], "--event", event]
        command = subprocess.list2cmdline(parts)
        timeout = 3 if event in ("SessionEnd", "Interrupt") else 10
        hooks.append(event + "=[{hooks=[{type=\"command\",command=" + json.dumps(command)
                     + ",timeout=" + str(timeout) + "}]}]")
    return "hooks={" + ",".join(hooks) + "}"


def build_command(manifest, *, stage=0, thread_id=None):
    protocol = manifest.get("entryProtocol", "exec")
    if protocol not in ("exec", "exec-resume"):
        raise ValueError("CLI command cannot represent an App Server case")
    installed = _hook_mode(manifest) == "installed-plugin"
    hooks = None if installed else _hook_configuration(manifest)
    trust = [] if installed else ["--dangerously-bypass-hook-trust"]
    isolation = (["--ignore-user-config", "--disable", "plugins", "--disable", "apps"]
                 if _hook_mode(manifest) == "native-package-hooks" else [])
    if protocol == "exec-resume":
        if type(stage) is not int or not 0 <= stage < len(manifest["prompts"]):
            raise ValueError("invalid persistent stage")
        output = str(Path(manifest["evidence"]) / f"last-message-{stage + 1}.txt")
        config = ([] if installed else ["--enable", "hooks"]) + ["-m", manifest["model"],
                  "-c", "approval_policy=\"never\"",
                  "-c", "sandbox_mode=\"workspace-write\"",
                  "-c", "model_reasoning_effort=" + json.dumps(manifest["reasoning"]),
                  "-c", "windows.sandbox=" + json.dumps(manifest["windowsSandbox"])]
        if hooks is not None:
            config += ["-c", hooks]
        if stage == 0:
            if thread_id is not None:
                raise ValueError("initial persistent stage cannot resume a thread")
            return [manifest["codex"], "exec", *isolation, "--skip-git-repo-check", "--sandbox", "workspace-write",
                    "--json", "--color", "never", "--output-last-message", output,
                    *trust, "-C", manifest["workspace"],
                    "--add-dir", str(Path(manifest["evidence"]) / "state"), *config, "-"]
        if not isinstance(thread_id, str) or not thread_id:
            raise ValueError("persistent resume requires the observed thread id")
        return [manifest["codex"], "exec", *isolation, "-C", manifest["workspace"],
                "--add-dir", str(Path(manifest["evidence"]) / "state"),
                "resume", "--json", "--output-last-message", output,
                *trust, "--skip-git-repo-check", *config, thread_id, "-"]
    return [manifest["codex"], "exec", "--ignore-user-config", "--disable", "plugins", "--disable", "apps", "--enable", "hooks",
            "--ephemeral", "--skip-git-repo-check", "--sandbox", "workspace-write", "--json", "--color", "never",
            "--output-last-message", str(Path(manifest["evidence"]) / "last-message.txt"),
            "--dangerously-bypass-hook-trust", "-C", manifest["workspace"], "-m", manifest["model"],
            "--add-dir", str(Path(manifest["evidence"]) / "state"),
            "-c", "approval_policy=\"never\"", "-c", "model_reasoning_effort=" + json.dumps(manifest["reasoning"]),
            "-c", "windows.sandbox=" + json.dumps(manifest["windowsSandbox"]),
            "-c", hooks, "-"]


def load_persistent_case(path):
    path = Path(path).resolve()
    raw = read_regular(path)
    observer = coordination_observer()
    case = observer._strict_json(raw.decode("utf-8"))
    observer.validate_case(case)
    return path, raw, case


def prepare(args, *, app_server_case=None, persistent_case=None):
    """Prepare CLI execution, or explicitly bind a caller-owned App Server case.

    App Server lifecycle/dispatch remains caller-owned; preparing its fixtures
    must not fabricate a CLI command or silently supply a different prompt.
    """
    if app_server_case is not None and persistent_case is not None:
        raise ValueError("choose one App Server or persistent CLI case")
    native_hooks = getattr(args, "native_package_hooks", False)
    installed_id = getattr(args, "installed_plugin", None)
    direct_hooks = native_hooks or installed_id is not None
    admission_case = getattr(args, "admission_case", None)
    if admission_case is not None and (persistent_case is None or not direct_hooks):
        raise ValueError("admission binding requires a persistent native Hook or installed-plugin case")
    if native_hooks and installed_id is not None:
        raise ValueError("source projection and installed plugin are mutually exclusive")
    if direct_hooks and persistent_case is None:
        raise ValueError("native package hooks require persistent exec-resume")
    if app_server_case is not None:
        if (not isinstance(app_server_case, dict) or set(app_server_case) != {"prompts", "expected", "limits"}
                or not isinstance(app_server_case["prompts"], list) or not 1 <= len(app_server_case["prompts"]) <= 16
                or any(not isinstance(p, str) or not p.strip() or len(p) > 100000 for p in app_server_case["prompts"])
                or not isinstance(app_server_case["expected"], dict)
                or set(app_server_case["expected"]) != {"details", "summary"}
                or not isinstance(app_server_case["expected"]["details"], list)
                or not isinstance(app_server_case["expected"]["summary"], dict)
                or not isinstance(app_server_case["limits"], dict) or not app_server_case["limits"]):
            raise ValueError("App Server case must prebind prompts, exact expected outputs and limits")
        app_server_case = json.loads(json.dumps(app_server_case, allow_nan=False))
        if "usageCaps" in app_server_case["limits"]:
            _usage_caps(app_server_case["limits"]["usageCaps"])
    if persistent_case is not None:
        case_path, case_bytes, case = persistent_case
        turn_timeout, recovery_timeout = args.turn_timeout, args.recovery_timeout
        if (type(turn_timeout) is not int or type(recovery_timeout) is not int
                or not 1 <= turn_timeout <= args.timeout <= 3600
                or not 1 <= recovery_timeout <= 300):
            raise ValueError("persistent case requires per-instance work, turn and recovery deadlines")
        if (not isinstance(case.get("limits"), dict)
                or set(case["limits"]) != {"usageCaps", "usageScope"}
                or not isinstance(case["limits"]["usageScope"], str)
                or not case["limits"]["usageScope"].strip()):
            raise ValueError("persistent case must prebind native cumulative usage limits")
        usage_caps = _usage_caps(case["limits"]["usageCaps"])
    evidence, workspace = Path(args.evidence).absolute(), Path(args.workspace).absolute()
    package = ordinary_dir(args.package)
    if installed_id is not None:
        _installed_package_identity(package, installed_id)
    projection = _native_hook_projection(package, args.node) if native_hooks else None
    if not args.model.strip() or not args.reasoning.strip():
        raise ValueError("explicit nonempty model and reasoning required")
    if args.windows_sandbox not in ("elevated", "unelevated"):
        raise ValueError("explicit existing Windows sandbox backend required")
    if evidence == workspace or evidence in workspace.parents or workspace in evidence.parents:
        raise ValueError("evidence and workspace must be separate non-nested fresh directories")
    for path in (evidence, workspace):
        if path.exists() or not path.parent.is_dir() or path.parent.resolve() != path.parent:
            raise ValueError("fresh root with ordinary existing parent required: " + str(path))
    paths = {"codex": Path(args.codex).resolve(), "node": Path(args.node).resolve(),
             "python": Path(sys.executable).resolve(), "runner": Path(__file__).resolve(),
             "runtime": package / "runtime/task-checkpoint.cjs"}
    if native_hooks:
        paths["hookShell"] = Path(projection["hookShell"])
    if installed_id is not None:
        paths.update({key: Path(__file__).with_name(name) for key, name in (
            ("inventoryRunner", "observe_codex_lifecycle.py"), ("inventoryResources", "inspect_native_resources.py"),
            ("inventoryRpc", "codex_rpc.py"))})
    if persistent_case is not None:
        paths["case"] = case_path
        observer_key = ("coordinationObserver" if case["schema"] == "yiyuan-accord-coordination-case/v1"
                        else "scopedTaskObserver")
        paths[observer_key] = Path(__file__).with_name("inspect_coordination.py").resolve()
    if any(any(c in str(p) for c in ('"', '\n', '\r', '%', '!', '`', '$', '&', '|', '<', '>', '^')) for p in (*paths.values(), package, evidence, workspace)):
        raise ValueError("shell-sensitive path cannot be used in hook command")
    if os.name == "nt" and paths["codex"].suffix.lower() != ".exe":
        raise ValueError("bind the native codex.exe, not an npm shell wrapper")
    hashes = {k: digest(p, os_shell=k == "hookShell") for k, p in paths.items()}
    protocol = "app-server" if app_server_case is not None else "exec-resume" if persistent_case is not None else "exec"
    help_protocol = "app-server" if protocol == "app-server" else "exec"
    help_run = subprocess.run([str(paths["codex"]), help_protocol, "--help"], capture_output=True, timeout=15)
    help_text = help_run.stdout.decode("utf-8", "replace")
    required = (("--ephemeral", "--ignore-user-config", "--dangerously-bypass-hook-trust", "--sandbox", "--output-last-message")
                if protocol == "exec" else ("--dangerously-bypass-hook-trust", "--sandbox", "--output-last-message")
                if protocol == "exec-resume" else ("app-server",))
    if native_hooks:
        required += ("--ignore-user-config", "--disable")
    if installed_id is not None:
        required = ("--sandbox", "--output-last-message")
    if help_run.returncode or any(flag not in help_text for flag in required):
        raise ValueError("native CLI help does not support required boundary")
    resume_help = None
    if protocol == "exec-resume":
        resume_help = subprocess.run([str(paths["codex"]), "exec", "resume", "--help"], capture_output=True, timeout=15)
        resume_text = resume_help.stdout.decode("utf-8", "replace")
        if resume_help.returncode or any(flag not in resume_text for flag in ("--json", "--output-last-message", "--model")):
            raise ValueError("native CLI resume help does not support required boundary")
    version = subprocess.run([str(paths["codex"]), "--version"], capture_output=True, timeout=15)
    if version.returncode:
        raise ValueError("native version probe failed")
    native_version = version.stdout.decode("utf-8", "strict").strip()
    admission_binding = None
    if admission_case is not None:
        # Reject incompatible candidates before creating fixtures or querying
        # the installed inventory. Help/version probes above call no model.
        admission_binding = _admission_binding({
            "package": str(package), "runner": str(paths["runner"]), "case": str(case_path),
            "nativeVersion": native_version, "entryProtocol": protocol,
            "hookMode": "installed-plugin" if installed_id is not None else "native-package-hooks",
            "model": args.model, "reasoning": args.reasoning, "windowsSandbox": args.windows_sandbox,
            "timeoutSeconds": args.timeout, "turnTimeoutSeconds": turn_timeout,
            "recoveryTimeoutSeconds": recovery_timeout, "caseSha256": hashlib.sha256(case_bytes).hexdigest(),
            "limits": {"usageCaps": usage_caps, "usageScope": case["limits"]["usageScope"]}}, admission_case)
    entry_guide = _entry_guide(paths["node"], paths["runtime"]) if direct_hooks else None
    evidence.mkdir()
    workspace.mkdir()
    ordinary_dir(evidence)
    ordinary_dir(workspace)
    installed = (_installed_plugin_binding(package, paths["codex"], installed_id, workspace, evidence, "prepare")
                 if installed_id is not None else None)
    for name in ("hooks", "state", "temp"):
        if name == "hooks" and direct_hooks:
            continue
        (evidence / name).mkdir()
    if persistent_case is not None:
        inputs = {name: ((json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n").encode("utf-8")
                         if isinstance(value, (dict, list)) else value.encode("utf-8"))
                  for name, value in case["inputs"].items()}
    else:
        inputs = {"orders.csv": ORDERS, "order_source.py": SOURCE.encode(), "keep.txt": b"Unrelated original. Preserve exactly.\n",
                  "README.txt": ("订单数据接口是 order_source.py；从本目录运行以下本地命令获取 CSV：\n"
                                 + subprocess.list2cmdline([str(paths["python"]), "-B", "order_source.py"])
                                 + "\norders.csv 为接口原始存档，请保留。\n").encode()}
    for name, data in inputs.items():
        (workspace / name).write_bytes(data)
    if protocol == "exec":
        (evidence / "prompt.txt").write_text(PROMPT, encoding="utf-8")
    elif protocol == "exec-resume":
        for index, stage in enumerate(case["stages"]):
            (evidence / f"prompt-{index + 1}.txt").write_text(stage["prompt"], encoding="utf-8")
    (evidence / "native-help.txt").write_bytes(help_run.stdout + help_run.stderr)
    if resume_help is not None:
        (evidence / "native-resume-help.txt").write_bytes(resume_help.stdout + resume_help.stderr)
    (evidence / "native-version.txt").write_bytes(version.stdout + version.stderr)
    manifest = {"schema": "accord-codex-entry/v1", "episode": uuid.uuid4().hex,
                "evidence": str(evidence), "workspace": str(workspace), "package": str(package),
                **{k: str(p) for k, p in paths.items()}, "sourceHashes": hashes,
                "model": args.model, "reasoning": args.reasoning, "timeoutSeconds": args.timeout,
                "nativeVersion": native_version,
                "windowsSandbox": args.windows_sandbox,
                "sandboxSetup": "caller-selected existing backend; no setup/install or direct shared config mutation by runner; native workspace trust requires caller-authorized recovery",
                "inputs": {k: hashlib.sha256(v).hexdigest() for k, v in inputs.items()},
                "expected": {"details": [["id", "units"], ["A", "60"], ["B", "80"]],
                             "summary": {"ready_ids": ["A", "B"], "total_units": 140}}, "limits": LIMITS,
                "docs": ["https://learn.chatgpt.com/docs/hooks", "https://learn.chatgpt.com/docs/config-file/config-reference",
                         "https://learn.chatgpt.com/docs/config-file/config-basic#windows-sandbox-mode"]}
    manifest["hookMode"] = "installed-plugin" if installed is not None else "native-package-hooks" if native_hooks else "checkpoint-wrapper"
    if native_hooks:
        manifest["nativeHookProjection"] = projection
    if installed is not None:
        manifest["installedPlugin"] = installed
    if direct_hooks:
        manifest["entryGuide"] = entry_guide
        manifest["entryGuideSha256"] = hashlib.sha256(entry_guide.encode("utf-8")).hexdigest()
    if protocol == "exec":
        manifest["promptSha256"] = digest(evidence / "prompt.txt")
        manifest["command"] = build_command(manifest)
    elif protocol == "exec-resume":
        manifest.pop("expected")
        manifest.update({"entryProtocol": protocol,
                         "caseSchema": case["schema"],
                         "casePurpose": case["purpose"],
                         "prompts": [stage["prompt"] for stage in case["stages"]],
                         "promptSha256s": [digest(evidence / f"prompt-{index + 1}.txt")
                                           for index in range(len(case["stages"]))],
                         "deliverables": case["deliverables"],
                         "caseSha256": hashlib.sha256(case_bytes).hexdigest(),
                         "turnTimeoutSeconds": turn_timeout,
                         "recoveryTimeoutSeconds": recovery_timeout,
                         "limits": {"interaction": "persistent native exec followed by exact-id exec resume",
                                    "workSeconds": args.timeout, "turnSeconds": turn_timeout,
                                    "recoverySeconds": recovery_timeout,
                                    "usageCaps": usage_caps,
                                    "usageScope": case["limits"]["usageScope"],
                                    "acceptance": "native execution receipt; business semantics and admission remain separate"},
                         "initialCommand": build_command({**manifest, "entryProtocol": protocol,
                                                          "prompts": [stage["prompt"] for stage in case["stages"]]})})
        if direct_hooks:
            manifest["stageCommandTemplates"] = [build_command(manifest, stage=index,
                thread_id="__OBSERVED_NATIVE_THREAD_ID__" if index else None)
                for index in range(len(manifest["prompts"]))]
    else:
        manifest.update(app_server_case)
        manifest["entryProtocol"] = "app-server"
        manifest["tracePath"] = "native/stdout.jsonl"
        manifest["executionOwner"] = "caller-owned native App Server; no CLI run command"
    if admission_case is not None:
        manifest["admissionBinding"] = admission_binding
        try:
            if _admission_binding(manifest, admission_case) != admission_binding:
                raise ValueError("admission subject changed while preparing the observation")
        except (OSError, ValueError, subprocess.SubprocessError):
            # Retain any model-free inventory receipts for caller-owned recovery;
            # do not leave an apparently runnable manifest or erase evidence.
            save(evidence / "preparation-failed.json", {
                "state": "failed", "reason": "admission-binding-recheck-failed", "modelCalled": False,
                "retainedRoots": {"evidence": str(evidence), "workspace": str(workspace)},
                "recovery": "Caller must review retained preparation/inventory receipts and release these owned roots; no run manifest was published."})
            raise
    save(evidence / "manifest.json", manifest)
    return {"prepared": True, "evidence": str(evidence), "workspace": str(workspace), "modelCalled": False}


def hook(args):
    manifest = load_manifest(args.evidence)
    if _direct_package_hooks(manifest):
        raise ValueError("native package hooks cannot use the checkpoint wrapper")
    if digest(manifest["runtime"]) != manifest["sourceHashes"]["runtime"]:
        raise ValueError("prepared runtime changed")
    raw = sys.stdin.buffer.read(1024 * 1024 + 1)
    if len(raw) > 1024 * 1024:
        raise ValueError("hook input limit")
    payload = json.loads(raw)
    if payload.get("hook_event_name") != args.event or Path(payload.get("cwd", "")).resolve() != Path(manifest["workspace"]):
        raise ValueError("foreign hook event or workspace")
    prefix = Path(args.evidence) / "hooks" / (str(time.time_ns()) + "-" + args.event + "-" + uuid.uuid4().hex)
    prefix.with_suffix(".input.json").write_bytes(raw)
    env = dict(os.environ, YIYUAN_ACCORD_TASK_STATE_DIR=str(Path(args.evidence) / "state"))
    result = subprocess.run([manifest["node"], manifest["runtime"], "--hook", args.event], input=raw,
                            capture_output=True, timeout=2.5 if args.event in ("SessionEnd", "Interrupt") else 8, env=env)
    prefix.with_suffix(".stdout").write_bytes(result.stdout)
    prefix.with_suffix(".stderr").write_bytes(result.stderr)
    save(prefix.with_suffix(".result.json"), {"event": args.event, "exitCode": result.returncode})
    sys.stdout.buffer.write(result.stdout)
    sys.stderr.buffer.write(result.stderr)
    return result.returncode


class WindowsJob:
    """Only a newly-created owned process and descendants can enter this job."""
    def __init__(self):
        if os.name != "nt":
            raise ValueError("native process containment currently requires Windows")
        self.k = ctypes.WinDLL("kernel32", use_last_error=True)
        self.p = ctypes.WinDLL("psapi", use_last_error=True)
        signatures = {
            "CreateJobObjectW": ([ctypes.c_void_p, W.LPCWSTR], W.HANDLE),
            "SetInformationJobObject": ([W.HANDLE, ctypes.c_int, ctypes.c_void_p, W.DWORD], W.BOOL),
            "QueryInformationJobObject": ([W.HANDLE, ctypes.c_int, ctypes.c_void_p, W.DWORD, ctypes.c_void_p], W.BOOL),
            "AssignProcessToJobObject": ([W.HANDLE, W.HANDLE], W.BOOL),
            "TerminateJobObject": ([W.HANDLE, W.UINT], W.BOOL),
            "OpenProcess": ([W.DWORD, W.BOOL, W.DWORD], W.HANDLE),
            "OpenThread": ([W.DWORD, W.BOOL, W.DWORD], W.HANDLE),
            "ResumeThread": ([W.HANDLE], W.DWORD),
            "CloseHandle": ([W.HANDLE], W.BOOL),
            "CreateToolhelp32Snapshot": ([W.DWORD, W.DWORD], W.HANDLE),
            "Thread32First": ([W.HANDLE, ctypes.c_void_p], W.BOOL),
            "Thread32Next": ([W.HANDLE, ctypes.c_void_p], W.BOOL),
        }
        for name, (args, result) in signatures.items():
            fn = getattr(self.k, name)
            fn.argtypes, fn.restype = args, result
        self.p.GetProcessMemoryInfo.argtypes = [W.HANDLE, ctypes.c_void_p, W.DWORD]
        self.p.GetProcessMemoryInfo.restype = W.BOOL
        class Basic(ctypes.Structure):
            _fields_ = [("PerProcessUserTimeLimit", ctypes.c_longlong), ("PerJobUserTimeLimit", ctypes.c_longlong),
                        ("LimitFlags", W.DWORD), ("MinimumWorkingSetSize", ctypes.c_size_t), ("MaximumWorkingSetSize", ctypes.c_size_t),
                        ("ActiveProcessLimit", W.DWORD), ("Affinity", ctypes.c_size_t), ("PriorityClass", W.DWORD), ("SchedulingClass", W.DWORD)]
        class Extended(ctypes.Structure):
            _fields_ = [("BasicLimitInformation", Basic), ("IoInfo", ctypes.c_ulonglong * 6),
                        ("ProcessMemoryLimit", ctypes.c_size_t), ("JobMemoryLimit", ctypes.c_size_t),
                        ("PeakProcessMemoryUsed", ctypes.c_size_t), ("PeakJobMemoryUsed", ctypes.c_size_t)]
        self.handle = self.k.CreateJobObjectW(None, None)
        if not self.handle:
            raise ctypes.WinError(ctypes.get_last_error())
        limit = Extended()
        limit.BasicLimitInformation.LimitFlags = 0x2000  # JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
        if not self.k.SetInformationJobObject(self.handle, 9, ctypes.byref(limit), ctypes.sizeof(limit)):
            self.close()
            raise ctypes.WinError(ctypes.get_last_error())

    def attach_and_resume(self, process):
        handle = self.k.OpenProcess(0x0100 | 0x0001 | 0x0400, False, process.pid)
        try:
            if not handle or not self.k.AssignProcessToJobObject(self.handle, handle):
                raise ctypes.WinError(ctypes.get_last_error())
        finally:
            if handle:
                self.k.CloseHandle(handle)
        class ThreadEntry(ctypes.Structure):
            _fields_ = [(name, W.DWORD) for name in ("size", "usage", "tid", "pid", "base", "delta", "flags")]
        snapshot = self.k.CreateToolhelp32Snapshot(4, 0)
        if snapshot == ctypes.c_void_p(-1).value:
            raise ctypes.WinError(ctypes.get_last_error())
        resumed = False
        try:
            entry = ThreadEntry()
            entry.size = ctypes.sizeof(entry)
            found = self.k.Thread32First(snapshot, ctypes.byref(entry))
            while found:
                if entry.pid == process.pid:
                    thread = self.k.OpenThread(2, False, entry.tid)
                    if thread:
                        try:
                            resumed = self.k.ResumeThread(thread) != 0xFFFFFFFF
                        finally:
                            self.k.CloseHandle(thread)
                    break
                found = self.k.Thread32Next(snapshot, ctypes.byref(entry))
        finally:
            self.k.CloseHandle(snapshot)
        if not resumed:
            raise ValueError("owned suspended thread could not resume")

    def sample(self):
        class Pids(ctypes.Structure):
            _fields_ = [("assigned", W.DWORD), ("count", W.DWORD), ("pids", ctypes.c_size_t * 1024)]
        class Accounting(ctypes.Structure):
            _fields_ = [("user", ctypes.c_longlong), ("kernel", ctypes.c_longlong), ("periodUser", ctypes.c_longlong),
                        ("periodKernel", ctypes.c_longlong), ("faults", W.DWORD), ("total", W.DWORD), ("active", W.DWORD), ("terminated", W.DWORD)]
        class Memory(ctypes.Structure):
            _fields_ = [("size", W.DWORD), ("faults", W.DWORD)] + [(name, ctypes.c_size_t) for name in
                         ("peakWorking", "working", "peakPaged", "paged", "peakNonpaged", "nonpaged", "pagefile", "peakPagefile")]
        ids, accounting = Pids(), Accounting()
        if not self.k.QueryInformationJobObject(self.handle, 3, ctypes.byref(ids), ctypes.sizeof(ids), None):
            raise ctypes.WinError(ctypes.get_last_error())
        if not self.k.QueryInformationJobObject(self.handle, 1, ctypes.byref(accounting), ctypes.sizeof(accounting), None):
            raise ctypes.WinError(ctypes.get_last_error())
        rows = []
        for pid in list(ids.pids)[:ids.count]:
            handle = self.k.OpenProcess(0x0400 | 0x0010, False, pid)
            ram = None
            if handle:
                try:
                    mem = Memory()
                    mem.size = ctypes.sizeof(mem)
                    if self.p.GetProcessMemoryInfo(handle, ctypes.byref(mem), ctypes.sizeof(mem)):
                        ram = mem.working
                finally:
                    self.k.CloseHandle(handle)
            rows.append({"pid": pid, "workingSetBytes": ram})
        return {"time": time.time(), "cpuSeconds": (accounting.user + accounting.kernel) / 10000000,
                "activeProcesses": accounting.active, "totalProcesses": accounting.total, "processes": rows}

    def terminate(self):
        if not self.k.TerminateJobObject(self.handle, 124):
            raise ctypes.WinError(ctypes.get_last_error())

    def close(self):
        if self.handle:
            self.k.CloseHandle(self.handle)
            self.handle = None


class PosixProcessGroup:
    """A caller-created session/group, not kernel descendant containment.

    Popen must use start_new_session=True: Python calls setsid before exec.
    killpg observes/signals only this group; descendants can leave it. Counts,
    CPU and memory are deliberately unknown, and no close-time kill is implied.
    https://docs.python.org/3/library/subprocess.html#subprocess.Popen
    https://docs.python.org/3/library/os.html#os.killpg
    """
    def __init__(self):
        if os.name != "posix":
            raise ValueError("POSIX process groups require POSIX")
        self.process, self.pgid, self.absent = None, None, False
        self.last_observation_error = None

    def attach_and_resume(self, process):
        if self.process is not None or type(process.pid) is not int or process.pid <= 0:
            raise ValueError("one newly created positive process id required")
        if process.pid == os.getpgrp():
            raise ValueError("refusing the caller process group")
        # start_new_session establishes both identities before Popen returns.
        # A fast exiting leader can already be reaped while its group survives.
        try:
            if os.getpgid(process.pid) != process.pid or os.getsid(process.pid) != process.pid:
                raise ValueError("owned process did not start a new session/group")
        except ProcessLookupError:
            if process.poll() is None:
                raise
        self.process, self.pgid = process, process.pid

    def sample(self):
        exit_code = self.process.poll() if self.process is not None else None
        state = "not-started" if self.pgid is None else "absent" if self.absent else "alive"
        observation_error = None
        if self.pgid is not None and not self.absent:
            try:
                os.killpg(self.pgid, 0)
            except ProcessLookupError:
                self.absent, state = True, "absent"
            except OSError as error:
                state = "unobservable"
                observation_error = {"operation": "killpg", "signal": 0,
                                     "type": type(error).__name__, "errno": error.errno,
                                     "message": str(error)[:1024], "observedAt": time.time()}
                self.last_observation_error = observation_error
        return {"time": time.time(), "controller": "posix-session-process-group",
                "activeProcesses": None, "cpuSeconds": None, "totalProcesses": None,
                "processes": None, "processGroupId": self.pgid,
                "processGroupState": state, "rootPid": self.process.pid if self.process else None,
                "rootExitCode": exit_code,
                "observationError": observation_error,
                "lastObservationError": self.last_observation_error,
                "evidenceScope": "direct child exit and same process group only; escaped descendants, CPU and memory unobserved"}

    def terminate(self):
        if self.pgid is not None and not self.absent:
            try:
                os.killpg(self.pgid, signal.SIGKILL)
            except ProcessLookupError:
                self.absent = True

    def close(self):
        pass  # POSIX has no Job handle or kill-on-close guarantee.


def source_recovery_from_events(stream, python, *, protocol="exec", request_stream=None, workspace=None):
    """Recognize a bounded native PowerShell direct-call trace, not shell prose.

This intentionally does not parse arbitrary shell/Python programs. Unsupported
invocation forms remain unverified. Resumed App Server traces require the original
outgoing request stream and its matching response; a thread-shaped result alone
does not identify a resume. Saved logs are diagnostic, not attestations.
"""
    result = {"oracle": "bounded-native-command-pairs/v3", "traceValid": False,
              "failedItemId": None, "successfulItemId": None, "recovered": False}
    if len(stream.encode("utf-8")) > 32 * 1024 * 1024:
        return result
    try:
        events = [json.loads(line) for line in stream.splitlines() if line.strip()]
        if any(not isinstance(event, dict) for event in events):
            return result
    except (ValueError, UnicodeError):
        return result
    if protocol == "app-server":
        try:
            starts = [e["params"]["thread"]["id"] for e in events if e.get("method") == "thread/started"]
            requests = []
            if request_stream is not None:
                if len(request_stream.encode("utf-8")) > 8 * 1024 * 1024:
                    return result
                requests = [json.loads(line) for line in request_stream.splitlines() if line.strip()]
                if any(not isinstance(r, dict) for r in requests):
                    return result
            resumes = [r for r in requests if r.get("method") == "thread/resume"]
            resume_index, turn_windows = None, {}
            if resumes:
                if starts or len(resumes) != 1:
                    return result
                request = resumes[0]
                identity, params = request["id"], request["params"]
                thread = params["threadId"]
                if (type(identity) not in (str, int) or not isinstance(thread, str) or not thread
                        or any(params.get(k) is not None for k in ("history", "path"))
                        or sum(r.get("id") == identity for r in requests) != 1):
                    return result
                responses = [(i, e) for i, e in enumerate(events) if e.get("id") == identity]
                if len(responses) != 1:
                    return result
                resume_index, response = responses[0]
                if ("method" in response or "error" in response
                        or response["result"]["thread"]["id"] != thread):
                    return result
                starts = [thread]
                # Do not borrow historical turns embedded in the resume response.
                # Only subsequent native start/completion notifications bind work.
                for i, event in enumerate(events):
                    method = event.get("method")
                    if method not in ("turn/started", "turn/completed"):
                        continue
                    params = event["params"]
                    turn = params["turn"]["id"]
                    if (i <= resume_index or params["threadId"] != thread
                            or not isinstance(turn, str) or not turn):
                        return result
                    window = turn_windows.setdefault(turn, {})
                    if method in window:
                        return result
                    window[method] = i
                    if method == "turn/completed" and params["turn"]["status"] != "completed":
                        return result
                if not turn_windows or any(set(w) != {"turn/started", "turn/completed"}
                        or w["turn/started"] >= w["turn/completed"] for w in turn_windows.values()):
                    return result
            if len(starts) != 1 or not isinstance(starts[0], str) or not starts[0]:
                return result
            normalized = [{"type": "thread.started", "thread_id": starts[0]}]
            for index, event in enumerate(events):
                if event.get("method") not in ("item/started", "item/completed"):
                    continue
                params = event["params"]
                if params.get("threadId") != starts[0]:
                    return result
                if resume_index is not None:
                    window = turn_windows.get(params.get("turnId"), {})
                    if not window.get("turn/started", index) < index < window.get("turn/completed", index):
                        return result
                item = params["item"]
                if item.get("type") != "commandExecution":
                    continue
                if workspace is not None and (not isinstance(item.get("cwd"), str)
                                               or Path(item["cwd"]) != Path(workspace)):
                    return result
                normalized.append({"type": event["method"].replace("/", "."), "item": {
                    "id": item["id"], "type": "command_execution", "command": item["command"],
                    "actions": item.get("commandActions"), "turn": params["turnId"],
                    "cwd": item.get("cwd"),
                    "status": item.get("status"), "exit_code": item.get("exitCode"),
                    "aggregated_output": item.get("aggregatedOutput"),
                }})
            events = normalized
            result["entryEvidence"] = "matched-resume-request-response" if resumes else "thread-started-notification"
        except (KeyError, TypeError, AttributeError, ValueError):
            return result
    elif protocol != "exec":
        return result
    threads = [e.get("thread_id") for e in events if e.get("type") == "thread.started"]
    if len(threads) != 1 or not isinstance(threads[0], str) or not threads[0]:
        return result
    result["threadId"] = threads[0]
    # Native command display doubles Windows backslashes. Only admit a direct
    # Python source call, optionally preceded by this fixture's read-only checks.
    executable = str(python).replace("\\\\", "\\")
    invocation = r"&\s+(?:'" + re.escape(executable) + r"'|\"" + re.escape(executable) + r"\"|" + re.escape(executable) + r")"
    # A plain Windows path without whitespace or shell syntax is itself an
    # invocation. Quoted strings still require &: they are not executions.
    # CLI and App Server both emit this legal direct invocation. CLI display
    # quoting is removed once below; an inner quoted string is not execution.
    # Keep the exact prepared executable and the bounded direct-call tail.
    if re.fullmatch(r"[A-Za-z]:[\\/][A-Za-z0-9_./\\-]+", executable):
        invocation = r"(?:" + invocation + "|" + re.escape(executable) + ")"
    call = re.compile(invocation + r"\s+-B\s+(?:order_source\.py|'order_source\.py'|\"order_source\.py\")\s*$", re.I)
    preludes = (
        re.compile(r"Get-FileHash -Algorithm SHA256 -LiteralPath (?:README\.txt|order_source\.py|orders\.csv|keep\.txt)(?:,(?:README\.txt|order_source\.py|orders\.csv|keep\.txt))*", re.I),
        re.compile(r"Get-ChildItem -Force \| Select-Object Name,Length", re.I),
        re.compile(r"Get-ChildItem -Force \.source-attempts\.json \| Select-Object Name,Length", re.I),
        re.compile(r"Get-Content -LiteralPath \.source-attempts\.json(?: -Raw)?", re.I),
        re.compile(r"Get-Content -Raw \.source-attempts\.json", re.I),
    )

    child_status = re.compile(r';\s*\$exitCode = \$LASTEXITCODE;\s*"(?:`n)?SOURCE_EXIT=\$exitCode";\s*exit 0\s*$', re.I)
    propagated_status = re.compile(
        r';\s*\$(?P<code>[a-z_][a-z_0-9]*)\s*=\s*\$LASTEXITCODE;\s*'
        r'Write-Output\s+"(?P<label>[a-z_][a-z_0-9]*)=\$(?P=code)";\s*'
        r'(?:exit\s+\$(?P=code)|if\s*\(\$(?P=code)\s+-ne\s+0\)\s*'
        r'\{\s*exit\s+\$(?P=code)\s*\})\s*$', re.I)

    def direct_source(command, actions):
        if not isinstance(command, str):
            return False, False
        if protocol == "app-server":
            normalized = command.replace("\\\\", "\\")
            if not re.fullmatch(r'"[^"\r\n]+[\\/]pwsh\.exe" -Command ([\s\S]+)', normalized, re.I):
                return False, False
            if (not isinstance(actions, list) or len(actions) != 1 or not isinstance(actions[0], dict)
                    or actions[0].get("type") != "unknown" or not isinstance(actions[0].get("command"), str)):
                return False, False
            # Native parsed action avoids interpreting display-only shell quoting.
            # Both action and displayed command must match their start event.
            body = actions[0]["command"]
        else:
            # Native CommandExecutionPresentation uses shlex_join(argv), even
            # on Windows. Decode that display layer, not PowerShell syntax;
            # stripping outer quotes corrupts adjacent mixed-quote segments.
            try:
                argv = shlex.split(command)
            except ValueError:
                return False, False
            if (len(argv) != 3 or not re.fullmatch(r'[^\r\n]+[\\/]pwsh\.exe', argv[0], re.I)
                    or argv[1].lower() != "-command"):
                return False, False
            body = argv[2]
        status_mode = None
        if protocol == "app-server" and child_status.search(body) is not None:
            status_mode = "wrapped"
            body = child_status.sub("", body)
        elif (status := propagated_status.search(body)) is not None:
            status_mode = ("propagated", status["label"])
            body = propagated_status.sub("", body)
        match = call.search(body)
        if not match:
            return False, False
        prefix = body[:match.start()].strip()
        if not prefix:
            return True, status_mode
        if not prefix.endswith(";"):
            return False, False
        return (all(any(pattern.fullmatch(part.strip()) for pattern in preludes)
                    for part in prefix[:-1].split(";")), status_mode)

    pending, completed, candidates = {}, set(), []
    for index, event in enumerate(events):
        item = event.get("item")
        if not isinstance(item, dict) or item.get("type") != "command_execution":
            continue
        identity = item.get("id")
        if not isinstance(identity, str) or not identity:
            return result
        if event.get("type") == "item.started":
            if identity in pending or identity in completed:
                return result
            pending[identity] = (index, item.get("command"), item.get("actions"), item.get("turn"), item.get("cwd"))
        elif event.get("type") == "item.completed":
            if identity not in pending or identity in completed:
                return result
            start, command, actions, turn, cwd = pending.pop(identity)
            completed.add(identity)
            if (item.get("command") != command or item.get("actions") != actions
                    or item.get("turn") != turn or item.get("cwd") != cwd):
                return result
            output, code = item.get("aggregated_output"), item.get("exit_code")
            direct, status_mode = direct_source(command, actions)
            if not direct or not isinstance(output, str) or type(code) is not int:
                continue
            lines = output.replace("\r\n", "\n").splitlines()
            if status_mode == "wrapped":
                if code != 0 or item.get("status") != "completed" or not lines or not re.fullmatch(r"SOURCE_EXIT=-?\d+", lines[-1]):
                    continue
                code = int(lines.pop().split("=")[1])
            elif isinstance(status_mode, tuple) and status_mode[0] == "propagated":
                if (not lines or not re.fullmatch(re.escape(status_mode[1]) + r"=-?\d+", lines[-1])
                        or int(lines.pop().split("=")[1]) != code):
                    continue
            # Native status proves failure of the bound direct invocation. Error
            # prose is neither required nor evidence of a particular failure cause.
            failed = code != 0 and (status_mode == "wrapped" or item.get("status") == "failed")
            csv_output = ORDERS.decode().strip().splitlines()
            succeeded = code == 0 and item.get("status") == "completed" and any(
                lines[offset:offset + len(csv_output)] == csv_output for offset in range(len(lines)))
            candidates.append((identity, start, index, failed, succeeded, cwd))
    if pending:
        return result
    result["traceValid"] = True
    for failed_id, _, failed_end, failed, _, failed_cwd in candidates:
        if failed:
            for success_id, success_start, _, _, success, success_cwd in candidates:
                if success and success_start > failed_end and success_cwd == failed_cwd:
                    result.update(failedItemId=failed_id, successfulItemId=success_id, recovered=True)
                    return result
    return result


def coordination_observer():
    project = str(Path(__file__).resolve().parents[1])
    if project not in sys.path:
        sys.path.insert(0, project)
    from scripts import inspect_coordination
    return inspect_coordination


def _installed_evidence_valid(manifest, recorded):
    repo = str(Path(__file__).resolve().parents[1])
    if repo not in sys.path:
        sys.path.insert(0, repo)
    from scripts.inspect_native_resources import native_processes_released
    try:
        binding = manifest["installedPlugin"]
        stages = recorded["stages"]
        labels = {"prepare", "run-preflight"} | {f"stage-{i + 1}-{phase}"
            for i in range(len(stages)) for phase in ("before", "after")}
        root = Path(manifest["evidence"]) / "installed-inventory/commands"
        if {path.name for path in root.iterdir()} != labels:
            return False
        for label in labels:
            record = json.loads(read_regular(root / label / "record.json"))
            config = json.loads(read_regular(root / label / "shared-config.json"))
            data = json.loads(read_regular(root / label / "stdout.json", 4 * 1024 * 1024))
            rows = [row for row in data["installed"] if row.get("pluginId") == binding["pluginId"]]
            if (rows != [binding["inventory"]] or config.get("unchanged") is not True
                    or config["before"]["state"] != "observed" or config["after"]["state"] != "observed"
                    or config["before"]["sha256"] != config["after"]["sha256"]
                    or record.get("arguments") != ["plugin", "list", "--marketplace", binding["inventory"]["marketplaceName"], "--json"]
                    or record.get("exitCode") != 0 or record.get("forced") is not False or record.get("failure") is not None
                    or not native_processes_released(record["after"], record["controller"])):
                return False
        return all(stage.get("stage") == i + 1 and stage.get("installedBefore") == binding
            and stage.get("installedAfter") == binding and stage.get("entryObservation", {}).get("valid") is True
            for i, stage in enumerate(stages))
    except (OSError, ValueError, KeyError, TypeError, AttributeError):
        return False


def inspect(evidence):
    manifest = load_manifest(evidence)
    if manifest.get("entryProtocol") == "exec-resume":
        evidence = Path(evidence)
        observer_key = ("coordinationObserver" if manifest.get("caseSchema", "yiyuan-accord-coordination-case/v1")
                        == "yiyuan-accord-coordination-case/v1" else "scopedTaskObserver")
        for key in ("case", observer_key):
            if digest(manifest[key]) != manifest["sourceHashes"][key]:
                raise ValueError("bound persistent inspection source changed: " + key)
        recorded = json.loads(read_regular(evidence / "result.json"))
        if (recorded.get("schema") != "accord-codex-persistent-exec/v1"
                or recorded.get("episode") != manifest["episode"]
                or not isinstance(recorded.get("stages"), list) or not recorded["stages"]):
            raise ValueError("persistent result binding mismatch")
        stage_id = recorded["stages"][-1]["fileObservation"]["stage"]
        current = coordination_observer().inspect_stage(
            manifest["workspace"], stage_id,
            originals=json.loads(read_regular(evidence / "originals.json")),
            history=json.loads(read_regular(evidence / "history.json")), fixture_path=manifest["case"])
        installed_checks = None
        if _hook_mode(manifest) == "installed-plugin":
            # Review retained observations, not a cache that may have legitimately
            # advanced after this run. These remain caller-recorded evidence.
            installed_checks = _installed_evidence_valid(manifest, recorded)
        return {"entryProtocol": "exec-resume", "caseSchema": manifest.get("caseSchema"),
                "recordedExecution": recorded,
                "retainedInstalledChecksValid": installed_checks,
                "currentFileObservation": current,
                "claimLimit": "Fresh file check and retained execution receipts; no automatic admission."}
    root, evidence = Path(manifest["workspace"]), Path(evidence)
    unchanged = {}
    for name, expected in manifest["inputs"].items():
        try:
            unchanged[name] = digest(root / name) == expected
        except (OSError, ValueError):
            unchanged[name] = False
    def read_output(name, convert):
        try:
            return convert(read_regular(root / name).decode("utf-8-sig"))
        except (OSError, ValueError, UnicodeError, csv.Error):
            return None
    details = read_output("details.csv", lambda s: list(csv.reader(io.StringIO(s))))
    summary = read_output("summary.json", json.loads)
    report = read_output("report.md", str)
    attempts = read_output(".source-attempts.json", json.loads)
    usage = None
    if manifest.get("entryProtocol") == "app-server":
        usage = app_server_usage_budget("", thread_id=None, caps=manifest["limits"].get("usageCaps"))
    try:
        protocol = manifest.get("entryProtocol", "exec")
        trace_path = "native/stdout.jsonl" if protocol == "app-server" else "stdout.jsonl"
        trace = read_regular(evidence / trace_path, 32 * 1024 * 1024)
        requests_path = evidence / "native/requests.jsonl"
        requests = read_regular(requests_path) if protocol == "app-server" and requests_path.exists() else None
        recovery = source_recovery_from_events(trace.decode("utf-8"), manifest["python"], protocol=protocol,
                                              request_stream=requests.decode("utf-8") if requests is not None else None,
                                              workspace=root)
        if protocol == "app-server":
            usage = app_server_usage_budget(trace.decode("utf-8"), thread_id=recovery.get("threadId"),
                                            caps=manifest["limits"].get("usageCaps"))
        recovery["traceSha256"] = hashlib.sha256(trace).hexdigest()
        if requests is not None:
            recovery["requestTraceSha256"] = hashlib.sha256(requests).hexdigest()
    except (OSError, ValueError, UnicodeError):
        recovery = {"oracle": "bounded-native-command-pairs/v3", "traceValid": False, "recovered": False}
    recovery["sourceUnchanged"] = unchanged.get("order_source.py") is True and unchanged.get("orders.csv") is True
    events = []
    for path in sorted((evidence / "hooks").glob("*.result.json")):
        events.append(json.loads(read_regular(path)))
    input_binding = None
    if manifest.get("entryProtocol") == "app-server":
        try:
            receipts = [json.loads(read_regular(p)) for p in sorted((evidence / "hooks").glob("*UserPromptSubmit*.input.json"))]
            input_binding = (bool(receipts) and recovery.get("traceValid") is True
                             and [r["prompt"] for r in receipts] == manifest["prompts"]
                             and all(r["session_id"] == recovery.get("threadId")
                                     and r["hook_event_name"] == "UserPromptSubmit"
                                     and Path(r["cwd"]) == root for r in receipts))
        except (OSError, ValueError, KeyError, TypeError):
            input_binding = False
    state = sorted(p.name for p in (evidence / "state").iterdir())
    return {"outputs": {"details": details, "summary": summary, "report": report},
            "outputsMatch": input_binding is not False and details == manifest["expected"]["details"] and summary == manifest["expected"]["summary"] and bool(report and report.strip()),
            "caseInputsMatch": input_binding,
            "reportSemanticReview": "manual; nonempty report is not semantic verification",
            "inputsUnchanged": unchanged, "sourceAttempts": attempts,
            "sourceRecovered": input_binding is not False and recovery["recovered"] and recovery["sourceUnchanged"],
            "sourceRecoveryEvidence": recovery,
            "usageObservation": usage,
            "hookResults": events, "runtimeStateResidue": state,
            "unexpectedWorkspacePaths": sorted(set(p.name for p in root.iterdir()) - set(manifest["inputs"]) - {"details.csv", "summary.json", "report.md", ".source-attempts.json"}),
            "limits": manifest["limits"]}


def persistent_cli_usage_budget(stream, caps):
    """Read one native CLI turn's reported cumulative thread usage.

    Native exec emits the thread total on ``turn.completed``. A resumed turn is
    therefore another observation of the same cumulative value, not an amount
    to add to earlier turns. This protects only the prebound observed limits;
    it does not predict future usage, context occupancy, or monetary cost.
    """
    result = _usage_from_native_counters(None, caps)
    try:
        if len(stream.encode("utf-8")) > 32 * 1024 * 1024:
            return result
        terminals = [json.loads(line) for line in stream.splitlines() if line.strip()]
        terminals = [event for event in terminals if event.get("type") == "turn.completed"]
        if len(terminals) != 1:
            return result
        return _usage_from_native_counters(terminals[0]["usage"], caps)
    except (ValueError, UnicodeError, AttributeError, KeyError, TypeError):
        pass
    return result


def _usage_from_native_counters(usage, caps, *, source=None, observed_at=None):
    """Apply the existing cumulative caps to one native usage counter set."""
    caps = _usage_caps(caps)
    result = {"decision": "unknown", "observed": None, "caps": caps, "exceeded": [],
              "contextOccupancy": None, "monetaryCost": None,
              "scope": "native reported cumulative thread usage; not per-turn cost or future usage"}
    if source is not None:
        result.update(source=source, observedAt=observed_at)
    try:
        names = ("input_tokens", "cached_input_tokens", "output_tokens")
        if not isinstance(usage, dict) or any(type(usage.get(name)) is not int or usage[name] < 0 for name in names):
            return result
        if usage["cached_input_tokens"] > usage["input_tokens"]:
            return result
        observed = {"inputTokens": usage["input_tokens"],
                    "cachedInputTokens": usage["cached_input_tokens"],
                    "outputTokens": usage["output_tokens"]}
        observed["uncachedInputTokens"] = observed["inputTokens"] - observed["cachedInputTokens"]
        observed["totalTokens"] = observed["inputTokens"] + observed["outputTokens"]
        if "total_tokens" in usage and usage["total_tokens"] != observed["totalTokens"]:
            return result
        result["observed"] = observed
        result["exceeded"] = sorted(key for key, limit in caps.items() if observed[key] > limit)
        result["decision"] = "over-limit" if result["exceeded"] else "within-observed-limits"
    except (KeyError, TypeError):
        pass
    return result


class _IncrementalLines:
    """Read appended ordinary-file bytes once, retaining an incomplete final line."""

    def __init__(self, path, *, limit, chunk=256 * 1024):
        self.path, self.limit, self.chunk = Path(path), limit, chunk
        self.offset, self.pending, self.unavailable = 0, b"", None
        self.identity = None

    def read(self):
        if self.unavailable:
            return []
        try:
            before = self.path.lstat()
            identity = (before.st_dev, before.st_ino)
            if (not stat.S_ISREG(before.st_mode) or before.st_nlink != 1 or self.path.is_symlink()
                    or getattr(before, "st_file_attributes", 0) & 0x400
                    or before.st_size < self.offset or before.st_size > self.limit
                    or self.identity is not None and identity != self.identity):
                raise ValueError("not a bounded ordinary incremental source")
            with self.path.open("rb") as stream:
                opened = os.fstat(stream.fileno())
                if opened.st_ino != before.st_ino:
                    raise ValueError("incremental source changed")
                stream.seek(self.offset)
                data = stream.read(min(self.chunk, before.st_size - self.offset))
            self.identity = identity
            self.offset += len(data)
            data = self.pending + data
            lines = data.split(b"\n")
            self.pending = lines.pop()
            if len(self.pending) > self.chunk:
                raise ValueError("oversized incomplete native record")
            return [line.rstrip(b"\r") for line in lines]
        except (OSError, ValueError) as error:
            self.unavailable = type(error).__name__
            return []


def _rust_string(value):
    return json.loads('"' + value + '"')


def _session_configuration(lines):
    for raw in lines:
        try:
            line = raw.decode("utf-8")
        except UnicodeError:
            continue
        if "Codex initialized with event: SessionConfiguredEvent" not in line:
            continue
        identity = re.search(r"thread_id: ThreadId \{ uuid: ([0-9a-f-]+) \}", line)
        cwd = re.search(r'cwd: AbsolutePathBuf\("((?:[^"\\]|\\.)*)"\)', line)
        rollout = re.search(r'rollout_path: Some\("((?:[^"\\]|\\.)*)"\)', line)
        try:
            if identity and cwd and rollout:
                return {"threadId": identity.group(1), "cwd": _rust_string(cwd.group(1)),
                        "rolloutPath": _rust_string(rollout.group(1))}
        except (ValueError, UnicodeError):
            return None
    return None


def _stdout_thread(lines):
    for raw in lines:
        try:
            event = json.loads(raw)
            if event.get("type") == "thread.started" and isinstance(event.get("thread_id"), str):
                return event["thread_id"]
        except (ValueError, UnicodeError, AttributeError):
            continue
    return None


def _ordinary_rollout(path, sessions_root):
    root = ordinary_dir(sessions_root)
    candidate = Path(path).absolute()
    if ".." in candidate.parts:
        raise ValueError("native rollout is outside the sessions root")
    try:
        relative = candidate.relative_to(root)
    except ValueError as error:
        raise ValueError("native rollout is outside the sessions root") from error
    current = root
    for part in relative.parts[:-1]:
        current /= part
        info = current.lstat()
        if (not stat.S_ISDIR(info.st_mode) or current.is_symlink()
                or getattr(info, "st_file_attributes", 0) & 0x400):
            raise ValueError("native rollout parent is not ordinary")
    info = candidate.lstat()
    if (not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or candidate.is_symlink()
            or getattr(info, "st_file_attributes", 0) & 0x400):
        raise ValueError("native rollout is not an ordinary file")
    if not candidate.resolve(strict=True).is_relative_to(root.resolve(strict=True)):
        raise ValueError("native rollout is outside the sessions root")
    return candidate


class NativeRolloutUsage:
    """Task-bound incremental reader for the native persisted usage stream."""

    def __init__(self, path, *, sessions_root, thread_id, cwd, caps):
        self.path = _ordinary_rollout(path, sessions_root)
        self.thread_id, self.cwd, self.caps = thread_id, os.path.normcase(os.path.abspath(cwd)), _usage_caps(caps)
        self.lines = _IncrementalLines(self.path, limit=32 * 1024 * 1024, chunk=1024 * 1024)
        self.meta_bound, self.last_counters, self.last_ordinal = False, None, -1
        self.result = _usage_from_native_counters(None, self.caps,
            source={"kind": "native-rollout-token-count", "path": str(self.path)}, observed_at=None)

    def matches(self, configuration):
        return (configuration["threadId"] == self.thread_id
                and os.path.normcase(os.path.abspath(configuration["cwd"])) == self.cwd
                and Path(configuration["rolloutPath"]).absolute() == self.path)

    def poll(self):
        if self.result["decision"] == "over-limit":
            return dict(self.result)
        for raw in self.lines.read():
            try:
                event = json.loads(raw)
                if not self.meta_bound:
                    payload = event["payload"]
                    if (event.get("type") != "session_meta"
                            or payload.get("id", payload.get("session_id")) != self.thread_id
                            or os.path.normcase(os.path.abspath(payload["cwd"])) != self.cwd):
                        raise ValueError("native rollout task binding mismatch")
                    self.meta_bound = True
                if event.get("type") != "event_msg" or event.get("payload", {}).get("type") != "token_count":
                    continue
                ordinal = event.get("ordinal")
                usage = event["payload"]["info"]["total_token_usage"]
                checked = _usage_from_native_counters(usage, self.caps,
                    source={"kind": "native-rollout-token-count", "path": str(self.path),
                            "ordinal": ordinal}, observed_at=event.get("timestamp"))
                if (type(ordinal) is not int or ordinal <= self.last_ordinal
                        or checked["decision"] == "unknown"
                        or self.last_counters is not None
                        and any(checked["observed"][key] < self.last_counters[key] for key in self.last_counters)):
                    raise ValueError("invalid native cumulative usage record")
                self.last_ordinal, self.last_counters, self.result = ordinal, checked["observed"], checked
            except (KeyError, TypeError, ValueError, UnicodeError, AttributeError) as error:
                if self.result["decision"] != "over-limit":
                    self.result = _usage_from_native_counters(None, self.caps,
                        source={"kind": "native-rollout-token-count", "path": str(self.path)}, observed_at=None)
                    self.result["unavailableReason"] = type(error).__name__
                self.lines.unavailable = type(error).__name__
                break
        if self.lines.unavailable and self.result["decision"] != "over-limit":
            self.result["decision"], self.result["observed"], self.result["observedAt"] = "unknown", None, None
            self.result["unavailableReason"] = self.lines.unavailable
        return dict(self.result)


def persistent_cli_turn_receipt(stream, last_message, *, expected_thread_id=None, usage_caps=None):
    """Read the native exec JSON terminal for one initial or resumed turn."""
    usage = persistent_cli_usage_budget(stream, usage_caps) if usage_caps is not None else None
    result = {"valid": False, "threadId": None, "terminal": None, "finalMessageSha256": None,
              "usageObservation": usage}
    try:
        if len(stream.encode("utf-8")) > 32 * 1024 * 1024:
            return result
        events = [json.loads(line) for line in stream.splitlines() if line.strip()]
        starts = [event.get("thread_id") for event in events if event.get("type") == "thread.started"]
        terminals = [event for event in events if event.get("type") in ("turn.completed", "turn.failed")]
        messages = [event.get("item", {}).get("text") for event in events
                    if event.get("type") == "item.completed"
                    and event.get("item", {}).get("type") == "agent_message"
                    and isinstance(event.get("item", {}).get("text"), str)
                    and event["item"]["text"].strip()]
        if (len(starts) != 1 or not isinstance(starts[0], str) or not starts[0]
                or expected_thread_id is not None and starts[0] != expected_thread_id
                or len(terminals) != 1 or terminals[0].get("type") != "turn.completed"
                or not isinstance(last_message, str) or not last_message.strip()
                or not messages or messages[-1].rstrip("\r\n") != last_message.rstrip("\r\n")):
            return result
        final_message = last_message.rstrip("\r\n")
        result.update(valid=usage is None or usage["decision"] == "within-observed-limits",
                      threadId=starts[0], terminal="completed",
                      finalMessageSha256=hashlib.sha256(final_message.encode("utf-8")).hexdigest())
    except (ValueError, UnicodeError, AttributeError):
        pass
    return result


def _native_activity_barrier(row):
    payload = row.get("payload", {})
    if row.get("type") == "response_item":
        return (payload.get("type") in {"reasoning", "function_call", "custom_tool_call"}
                or payload.get("role") == "assistant")
    if row.get("type") == "event_msg":
        if payload.get("type") in {"item_started", "item_completed"}:
            # Only UserMessage is known input here. Other or malformed items
            # end the known-input prefix; this need not prove model execution.
            item = payload.get("item")
            return not isinstance(item, dict) or item.get("type") != "UserMessage"
        return payload.get("type") in {"agent_message", "agent_reasoning"}
    return False


def native_turn_context_observation(stream, *, thread_id, turn_id, workspace):
    """Project native reported turn conditions, never infer Goal or provider execution."""
    result = {"state": "unknown", "threadId": thread_id, "turnId": turn_id,
              "conditions": None, "recordedHostVersion": None, "line": None,
              "goalModeActive": None, "goalSource": "not-observed-by-this-projection",
              "limit": "native reported turn configuration only; not provider execution, Goal state, authority or case admission"}
    try:
        if not all(isinstance(value, str) and value.strip() for value in (thread_id, turn_id)) or not os.path.isabs(workspace):
            return result
        raw = stream.encode("utf-8") if isinstance(stream, str) else stream
        result["sourceSha256"] = hashlib.sha256(raw).hexdigest()
        result["sourceBytes"] = len(raw)
        rows = [(i, json.loads(line)) for i, line in enumerate(raw.splitlines(), 1) if line.strip()]
        headers = [row["payload"] for _, row in rows if row.get("type") == "session_meta"]
        same_workspace = lambda value: (isinstance(value, str) and os.path.isabs(value)
            and os.path.normcase(os.path.abspath(value)) == os.path.normcase(os.path.abspath(workspace)))
        if len(headers) != 1 or headers[0].get("id") != thread_id or not same_workspace(headers[0].get("cwd")):
            return result
        starts = [i for i, (_, row) in enumerate(rows) if row.get("type") == "event_msg"
                  and row.get("payload", {}).get("type") == "task_started"
                  and row["payload"].get("turn_id") == turn_id]
        if len(starts) != 1:
            return result
        context, activity_barrier = [], False
        for line, row in rows[starts[0] + 1:]:
            payload = row.get("payload", {})
            if row.get("type") == "event_msg" and payload.get("type") == "task_started":
                break
            if _native_activity_barrier(row):
                activity_barrier = True
            if row.get("type") == "turn_context":
                # A changed/duplicate context or a late record cannot stand in for
                # one bound configuration supplied before this turn's model work.
                if activity_barrier or payload.get("turn_id") != turn_id:
                    return result
                context.append((line, payload))
        if len(context) != 1:
            return result
        line, payload = context[0]
        mode = payload.get("collaboration_mode", {}).get("mode")
        if (not same_workspace(payload.get("cwd"))
                or not all(isinstance(v, str) and v.strip() for v in (payload.get("model"), payload.get("effort"), mode))):
            return result
        version = headers[0].get("cli_version")
        result.update(state="observed", line=line,
            recordedHostVersion=version if isinstance(version, str) and version.strip() else None,
            conditions={"model": payload["model"], "effort": payload["effort"],
                        "cwd": payload["cwd"], "collaborationMode": mode})
    except (ValueError, UnicodeError, TypeError, KeyError, AttributeError):
        pass
    return result


def native_entry_observation(stream, *, thread_id, turn_id, workspace, guide):
    """Require the current input Hook's full guide before model activity.

    Native role, hook provenance and turn identity prevent prior context or an
    assistant echo from being mistaken for this turn's upstream participation.
    This observes delivery, not semantic adoption or business completion.
    """
    result = {"valid": False, "decision": "not-observed", "threadId": thread_id,
              "turnId": turn_id, "limit": "full native input guidance before model activity; not adoption or outcome acceptance"}
    try:
        rows = [json.loads(line) for line in stream.splitlines() if line.strip()]
        metadata = [row["payload"] for row in rows if row.get("type") == "session_meta"]
        if (len(metadata) != 1 or metadata[0].get("id") != thread_id
                or os.path.normcase(os.path.abspath(metadata[0].get("cwd", ""))) != os.path.normcase(os.path.abspath(workspace))
                or not isinstance(guide, str) or not guide.startswith("Accord task entry:")):
            raise ValueError("native entry source binding differs")
        starts = [i for i, row in enumerate(rows) if row.get("type") == "event_msg"
                  and row.get("payload", {}).get("type") == "task_started"
                  and row["payload"].get("turn_id") == turn_id]
        if len(starts) != 1:
            raise ValueError("native turn boundary unavailable")
        for i in range(starts[0] + 1, len(rows)):
            row, payload = rows[i], rows[i].get("payload", {})
            if row.get("type") == "event_msg" and payload.get("type") == "task_started":
                break
            if _native_activity_barrier(row):
                break
            if row.get("type") != "response_item":
                continue
            origin = payload.get("internal_chat_message_metadata_passthrough") or {}
            if (payload.get("role") != "developer" or origin.get("turn_id") != turn_id
                    or "hooks.additional_context" not in origin.get("content_item_kinds", [])):
                continue
            text = "".join(item.get("text", "") for item in payload.get("content", []) if isinstance(item, dict))
            if text.startswith(guide) and f"Native input receipt: session={thread_id}; epoch=" in text:
                result.update(valid=True, decision="observed", line=i + 1,
                              guideSha256=hashlib.sha256(guide.encode("utf-8")).hexdigest())
                break
    except (ValueError, UnicodeError, TypeError, KeyError, AttributeError):
        result["decision"] = "unknown"
    return result


def _run_persistent_stage(manifest, stage, thread_id, env, deadline, native_usage=None):
    native_hooks = _direct_package_hooks(manifest)
    bound_prompt, bound_command, installed_before = (_verify_native_stage(manifest, stage, thread_id)
                                                     if native_hooks else (None, None, None))
    evidence = Path(manifest["evidence"])
    command = build_command(manifest, stage=stage, thread_id=thread_id)
    if native_hooks and command != bound_command:
        raise ValueError("prepared stage command changed before dispatch")
    prompt_path = evidence / f"prompt-{stage + 1}.txt"
    stdout_path = evidence / f"stdout-{stage + 1}.jsonl"
    stderr_path = evidence / f"stderr-{stage + 1}.txt"
    process, job, samples = None, WindowsJob(), []
    stdout_lines = _IncrementalLines(stdout_path, limit=32 * 1024 * 1024)
    stderr_lines = _IncrementalLines(stderr_path, limit=32 * 1024 * 1024)
    configured, started_thread = None, None
    live_usage = None
    forced, failure, after = False, None, {"activeProcesses": None}
    started = time.monotonic()
    stage_deadline = min(deadline, started + manifest["turnTimeoutSeconds"])
    try:
        with prompt_path.open("rb") as stdin, stdout_path.open("xb") as stdout, stderr_path.open("xb") as stderr:
            if native_hooks:
                if stdin.read() != bound_prompt:
                    raise ValueError("prepared stage prompt changed before dispatch")
                stdin.seek(0)
            process = subprocess.Popen(command, cwd=manifest["workspace"], env=env, stdin=stdin,
                                       stdout=stdout, stderr=stderr,
                                       creationflags=subprocess.CREATE_NO_WINDOW | 4)
            job.attach_and_resume(process)
            while process.poll() is None:
                samples.append(job.sample())
                configured = configured or _session_configuration(stderr_lines.read())
                started_thread = started_thread or _stdout_thread(stdout_lines.read())
                if configured and started_thread:
                    if (configured["threadId"] != started_thread
                            or thread_id is not None and started_thread != thread_id
                            or os.path.normcase(os.path.abspath(configured["cwd"]))
                               != os.path.normcase(os.path.abspath(manifest["workspace"]))):
                        failure = "native-rollout-binding-mismatch"
                        break
                    if native_usage is not None and "observer" not in native_usage:
                        try:
                            sessions = Path(manifest.get("installedPlugin", {}).get("codexHome",
                                env.get("CODEX_HOME", str(Path.home() / ".codex")))) / "sessions"
                            native_usage["observer"] = NativeRolloutUsage(
                                configured["rolloutPath"], sessions_root=sessions,
                                thread_id=started_thread, cwd=manifest["workspace"],
                                caps=manifest["limits"]["usageCaps"])
                        except (OSError, ValueError):
                            native_usage["unavailable"] = "native-rollout-unavailable"
                    observer = native_usage.get("observer") if native_usage is not None else None
                    if observer is not None:
                        if not observer.matches(configured):
                            failure = "native-rollout-binding-mismatch"
                            break
                        live_usage = observer.poll()
                        if live_usage["decision"] == "over-limit":
                            failure = "usage-limit"
                            break
                if (time.monotonic() >= stage_deadline
                        or stdout_path.stat().st_size + stderr_path.stat().st_size > 32 * 1024 * 1024):
                    forced, failure = True, "turn-time-or-output-limit"
                    break
                time.sleep(0.25)
    except BaseException as error:
        failure = type(error).__name__ + ": " + str(error)
    finally:
        try:
            recovery_deadline = time.monotonic() + manifest["recoveryTimeoutSeconds"]
            before = job.sample()
            naturally_exited = process is not None and process.poll() is not None and failure is None
            after = before
            while naturally_exited and after["activeProcesses"] and time.monotonic() < recovery_deadline:
                time.sleep(0.1)
                after = job.sample()
            if after["activeProcesses"]:
                forced = True
                job.terminate()
            if process is not None:
                if process.poll() is None and not after["activeProcesses"]:
                    forced = True
                    process.kill()
                try:
                    process.wait(timeout=max(0, recovery_deadline - time.monotonic()))
                except subprocess.TimeoutExpired:
                    forced = True
                    if failure is None:
                        failure = "recovery-time-limit"
                    if process.poll() is None:
                        process.kill()
            after = job.sample()
            while after["activeProcesses"] and time.monotonic() < recovery_deadline:
                time.sleep(0.1)
                after = job.sample()
            if after["activeProcesses"] and failure is None:
                failure = "recovery-time-limit"
        finally:
            job.close()
    try:
        stream = read_regular(stdout_path, 32 * 1024 * 1024).decode("utf-8")
        final = read_regular(evidence / f"last-message-{stage + 1}.txt").decode("utf-8")
        receipt = persistent_cli_turn_receipt(stream, final, expected_thread_id=thread_id,
                                              usage_caps=manifest["limits"]["usageCaps"])
    except (OSError, ValueError, UnicodeError):
        receipt = {"valid": False, "threadId": thread_id, "terminal": None,
                   "finalMessageSha256": None, "usageObservation": None}
    if native_usage is not None:
        observer = native_usage.get("observer")
        if observer is not None:
            live_usage = observer.poll()
        elif live_usage is None:
            live_usage = _usage_from_native_counters(None, manifest["limits"]["usageCaps"],
                source={"kind": "native-rollout-token-count", "path": None}, observed_at=None)
            live_usage["unavailableReason"] = native_usage.get("unavailable", "native-rollout-not-bound")
        receipt["runningUsageObservation"] = live_usage
        if (receipt.get("usageObservation") is None
                or receipt["usageObservation"].get("decision") == "unknown"):
            receipt["usageObservation"] = live_usage
    receipt.update({"stage": stage + 1, "command": command, "exitCode": process.returncode if process else None,
                    "forced": forced, "failure": failure, "elapsedSeconds": time.monotonic() - started,
                    "remainingOwnedProcesses": after["activeProcesses"], "samples": samples})
    receipt["valid"] &= (receipt["exitCode"] == 0 and not forced and failure is None
                         and receipt["remainingOwnedProcesses"] == 0)
    if _hook_mode(manifest) == "installed-plugin":
        receipt["installedBefore"] = installed_before
        try:
            receipt["installedAfter"] = _verify_prepared_sources(manifest, inventory_label=f"stage-{stage + 1}-after")
            receipt["installedPackageStable"] = True
        except (OSError, ValueError, RuntimeError, subprocess.TimeoutExpired) as error:
            receipt["installedPackageStable"] = False
            receipt["installedAfter"] = {"error": type(error).__name__}
            receipt["valid"] = False
            receipt["failure"] = receipt["failure"] or "installed-plugin-poststate: " + str(error)
    if native_hooks:
        entry = {"valid": False, "decision": "unknown"}
        conditions = {"state": "unknown", "goalModeActive": None,
                      "goalSource": "not-observed-by-this-projection"}
        try:
            stderr = read_regular(stderr_path, 32 * 1024 * 1024)
            source = _session_configuration(stderr.splitlines())
            turns = re.findall(rb"Sent prompt with event ID: ([0-9a-f-]{36})", stderr)
            if (source is None or source["threadId"] != receipt["threadId"] or len(turns) != 1
                    or os.path.normcase(os.path.abspath(source["cwd"])) != os.path.normcase(os.path.abspath(manifest["workspace"]))):
                raise ValueError("native entry turn source unavailable")
            sessions = Path(manifest.get("installedPlugin", {}).get("codexHome",
                env.get("CODEX_HOME", str(Path.home() / ".codex")))) / "sessions"
            rollout = _ordinary_rollout(source["rolloutPath"], sessions)
            stream = read_regular(rollout, 32 * 1024 * 1024)
            entry = native_entry_observation(stream,
                thread_id=receipt["threadId"], turn_id=turns[0].decode("ascii"),
                workspace=manifest["workspace"], guide=manifest["entryGuide"])
            entry["sourcePath"] = str(rollout)
            conditions = native_turn_context_observation(stream, thread_id=receipt["threadId"],
                turn_id=turns[0].decode("ascii"), workspace=manifest["workspace"])
            conditions["sourcePath"] = str(rollout)
        except (OSError, ValueError, UnicodeError, TypeError, KeyError):
            pass
        receipt["entryObservation"] = entry
        receipt["nativeTurnConditions"] = conditions
        receipt["valid"] &= entry["valid"]
        if not entry["valid"] and receipt["failure"] is None:
            receipt["failure"] = "required-native-entry-not-observed"
    return receipt


def run_persistent(args):
    # Reuse the bound read-only case oracle; it never supplies prompts or repairs files.
    observer = coordination_observer()

    manifest = load_manifest(args.evidence)
    if manifest.get("entryProtocol") != "exec-resume":
        raise ValueError("persistent runner requires an exec-resume case")
    evidence = Path(args.evidence)
    _verify_prepared_sources(manifest)
    for index, expected in enumerate(manifest["promptSha256s"]):
        if digest(evidence / f"prompt-{index + 1}.txt") != expected:
            raise ValueError("prepared prompt changed")
    if build_command(manifest) != manifest["initialCommand"]:
        raise ValueError("prepared initial command changed")
    for name, expected in manifest["inputs"].items():
        if digest(Path(manifest["workspace"]) / name) != expected:
            raise ValueError("prepared input changed")
    started, deadline = time.monotonic(), time.monotonic() + manifest["timeoutSeconds"]
    with (evidence / "run-started.json").open("x", encoding="utf-8") as receipt:
        json.dump({"time": time.time(), "deadlineSeconds": manifest["timeoutSeconds"],
                   "turnTimeoutSeconds": manifest["turnTimeoutSeconds"],
                   "recoveryTimeoutSeconds": manifest["recoveryTimeoutSeconds"],
                   "nativeCliInvocationsAllowed": len(manifest["prompts"]),
                   "additionalModelFreeInventoryCalls": (1 + 2 * len(manifest["prompts"])
                       if _hook_mode(manifest) == "installed-plugin" else 0),
                   "inventoryScope": "each model-free query uses the existing lifecycle controller, 20-second work plus 15-second recovery bounds, and retained command/resource receipts"}, receipt)
    env = dict(os.environ, YIYUAN_ACCORD_TASK_STATE_DIR=str(evidence / "state"),
               TEMP=str(evidence / "temp"), TMP=str(evidence / "temp"), RUST_LOG="error,codex_exec=info")
    if _hook_mode(manifest) == "native-package-hooks":
        env["PATH"] = str(Path(manifest["node"]).parent) + os.pathsep + env.get("PATH", "")
        # Native core selects the user shell itself; COMSPEC/SHELL cannot force
        # it. Keep its bound executable first in discovery without changing the
        # user's persistent shell or environment configuration.
        env["PATH"] = str(Path(manifest["hookShell"]).parent) + os.pathsep + env["PATH"]
    shared_config = Path(os.environ.get("CODEX_HOME", str(Path.home() / ".codex"))) / "config.toml"
    config_before = shared_config_snapshot(shared_config, manifest["workspace"])
    fixture = json.loads(read_regular(manifest["case"]))
    originals = observer.snapshot(manifest["workspace"], fixture["inputs"])
    save(evidence / "originals.json", originals)
    thread_id, stages, history, native_usage = None, [], {}, {}
    try:
        for stage in range(len(manifest["prompts"])):
            if time.monotonic() >= deadline:
                break
            if _hook_mode(manifest) == "native-package-hooks":
                _verify_native_stage(manifest, stage, thread_id)
            observed = _run_persistent_stage(manifest, stage, thread_id, env, deadline, native_usage)
            stage_id = fixture["stages"][stage]["id"]
            files = observer.inspect_stage(manifest["workspace"], stage_id, originals=originals,
                                           history=history, fixture_path=manifest["case"])
            retained = evidence / f"stage-{stage + 1}"
            retained.mkdir()
            try:
                for name in files["files"]:
                    (retained / name).write_bytes(read_regular(Path(manifest["workspace"]) / name))
            except (OSError, ValueError) as error:
                files["decision"] = "unknown"
                files["observationErrors"].append(str(error))
            save(retained / "inspection.json", files)
            history[stage_id] = files["files"]
            save(evidence / "history.json", history)
            observed["fileObservation"] = files
            observed["valid"] &= files["decision"] == "pass"
            stages.append(observed)
            thread_id = observed.get("threadId") or thread_id
            if not observed["valid"]:
                break
    finally:
        config_after = shared_config_snapshot(shared_config, manifest["workspace"])
        if _direct_package_hooks(manifest):
            # Retain poststate even when source drift or business inspection
            # rejects continuation; process cleanup remains stage-owned.
            save(evidence / "shared-config.json", {"before": config_before, "after": config_after,
                "unchanged": (config_before["sha256"] == config_after["sha256"]
                              if config_before["state"] == config_after["state"] == "observed" else None)})
    result = {"schema": "accord-codex-persistent-exec/v1", "episode": manifest["episode"],
              "threadId": thread_id, "stages": stages,
              "completedStages": sum(bool(stage["valid"]) for stage in stages),
              "caseComplete": len(stages) == len(manifest["prompts"]) and all(stage["valid"] for stage in stages),
              "sourceThreadIdKnown": bool(thread_id),
              "nativeResumeSucceeded": any(stage["valid"] for stage in stages[1:]),
              "elapsedSeconds": time.monotonic() - started,
              "sharedConfigObservation": {"before": config_before, "after": config_after,
                  "unchanged": (config_before["sha256"] == config_after["sha256"]
                                if config_before["state"] == config_after["state"] == "observed" else None)},
              "claimLimit": "native persistent execution receipt only; business semantics and formal admission remain independently reviewed"}
    result["hookMode"] = _hook_mode(manifest)
    if result["hookMode"] == "native-package-hooks":
        result["nativeHookProjection"] = {"sourceConfigurationOnly": True, "marketplaceInstalled": False,
                                          "claimLimit": manifest["nativeHookProjection"]["claimLimit"]}
    if result["hookMode"] == "installed-plugin":
        result["installedPlugin"] = manifest["installedPlugin"]
    save(evidence / "result.json", result)
    return result


def run(args):
    manifest = load_manifest(args.evidence)
    if manifest.get("entryProtocol", "exec") != "exec":
        raise ValueError("App Server case requires its caller-owned dispatcher; CLI run cannot execute it")
    evidence = Path(args.evidence)
    for key, expected in manifest["sourceHashes"].items():
        if digest(manifest[key]) != expected:
            raise ValueError("prepared source changed; prepare a fresh observation: " + key)
    if digest(evidence / "prompt.txt") != manifest["promptSha256"] or build_command(manifest) != manifest["command"]:
        raise ValueError("prepared prompt or command changed")
    for name, expected in manifest["inputs"].items():
        if digest(Path(manifest["workspace"]) / name) != expected:
            raise ValueError("prepared input changed")
    # Exclusive receipt forbids retrying the model under the same evidence identity.
    with (evidence / "run-started.json").open("x", encoding="utf-8") as receipt:
        json.dump({"time": time.time(), "command": manifest["command"], "nativeCliInvocationsAllowed": 1}, receipt)
    # The CLI's JSON projection omits bootstrap configuration. Its version-bound
    # codex_exec INFO event records the native start response; no HTTP debug log.
    env = dict(os.environ, YIYUAN_ACCORD_TASK_STATE_DIR=str(evidence / "state"), TEMP=str(evidence / "temp"), TMP=str(evidence / "temp"),
               RUST_LOG="error,codex_exec=info")
    shared_config = Path(os.environ.get("CODEX_HOME", str(Path.home() / ".codex"))) / "config.toml"
    config_before = shared_config_snapshot(shared_config, manifest["workspace"])
    config_observation = {
        "before": config_before, "after": {"state": "not-observed"}, "unchanged": None,
        "limit": "config.toml only; changed content may include concurrent work, so no automatic shared cleanup",
    }
    save(evidence / "shared-config.json", config_observation)
    process, job, samples = None, WindowsJob(), []
    forced, failure, before_cleanup = False, None, None
    started = time.monotonic()
    try:
        with (evidence / "prompt.txt").open("rb") as stdin, (evidence / "stdout.jsonl").open("xb") as stdout, (evidence / "stderr.txt").open("xb") as stderr:
            process = subprocess.Popen(manifest["command"], cwd=manifest["workspace"], env=env,
                                       stdin=stdin, stdout=stdout, stderr=stderr,
                                       creationflags=subprocess.CREATE_NO_WINDOW | 4)  # CREATE_SUSPENDED
            job.attach_and_resume(process)
            save(evidence / "process.json", {"pid": process.pid, "jobAssignedBeforeResume": True})
            while process.poll() is None:
                samples.append(job.sample())
                output_size = (evidence / "stdout.jsonl").stat().st_size + (evidence / "stderr.txt").stat().st_size
                if time.monotonic() - started > manifest["timeoutSeconds"] or output_size > 32 * 1024 * 1024:
                    forced = True
                    failure = "wall-time-or-output-limit"
                    break
                time.sleep(1)
    except BaseException as error:
        failure = type(error).__name__ + ": " + str(error)
    finally:
        try:
            before_cleanup = job.sample()
            if before_cleanup["activeProcesses"]:
                forced = True
                job.terminate()
            if process is not None:
                # Handles assignment failure while the owned root remains suspended.
                if process.poll() is None and not before_cleanup["activeProcesses"]:
                    forced = True
                    process.kill()
                process.wait(timeout=10)
            deadline = time.monotonic() + 10
            after = job.sample()
            while after["activeProcesses"] and time.monotonic() < deadline:
                time.sleep(0.1)
                after = job.sample()
        finally:
            job.close()
            config_after = shared_config_snapshot(shared_config, manifest["workspace"])
            config_observation.update({
                "after": config_after,
                "unchanged": (config_before["sha256"] == config_after["sha256"]
                              if config_before["state"] == config_after["state"] == "observed" else None),
            })
            save(evidence / "shared-config.json", config_observation)
    save(evidence / "resources.json", {"samples": samples, "beforeCleanup": before_cleanup, "afterCleanup": after,
                                       "elapsedSeconds": time.monotonic() - started, "forced": forced, "failure": failure,
                                       "exitCode": process.returncode if process else None})
    result = inspect(evidence)
    result["sharedConfigObservation"] = config_observation
    result["process"] = {"pid": process.pid if process else None, "exitCode": process.returncode if process else None,
                         "forced": forced, "failure": failure, "remainingOwnedProcesses": after["activeProcesses"]}
    result["runtimeStateRetainedForReview"] = bool(result["runtimeStateResidue"])
    save(evidence / "result.json", result)
    return result


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="action", required=True)
    prep = sub.add_parser("prepare", help="prepare reviewable fixture; no model call")
    for name in ("package", "evidence", "workspace", "codex", "node", "model", "reasoning"):
        prep.add_argument("--" + name, required=True)
    prep.add_argument("--timeout", type=int, required=True, help="one invocation wall-clock cap, 1..900 seconds")
    prep.add_argument("--persistent-case", help="existing coordination case to run through native exec/resume")
    prep.add_argument("--admission-case", help="optional committed admission case ID; requires matching conditions.execution, not an admission verdict")
    prep.add_argument("--native-package-hooks", action="store_true",
                      help="persistent CLI only: project all source Node hooks; isolate process config, not a marketplace-installed plugin")
    prep.add_argument("--installed-plugin", help="persistent CLI only: existing enabled name@marketplace; retain native discovery, user configuration and Hook trust")
    prep.add_argument("--turn-timeout", type=int, help="per-turn cap for a persistent case")
    prep.add_argument("--recovery-timeout", type=int, help="owned process recovery cap for a persistent case")
    prep.add_argument("--windows-sandbox", choices=("elevated", "unelevated"), required=True,
                      help="existing native backend, independent of workspace-write policy; no setup is performed")
    for name in ("run", "inspect", "hook"):
        item = sub.add_parser(name)
        item.add_argument("--evidence", required=True)
        if name == "hook":
            item.add_argument("--event", choices=EVENTS, required=True)
    args = parser.parse_args()
    if args.action == "prepare" and not 1 <= args.timeout <= 900:
        parser.error("timeout must be 1..900 seconds")
    if args.action == "hook":
        raise SystemExit(hook(args))
    if args.action == "prepare":
        case = load_persistent_case(args.persistent_case) if args.persistent_case else None
        result = prepare(args, persistent_case=case)
    elif args.action == "run":
        result = run_persistent(args) if load_manifest(args.evidence).get("entryProtocol") == "exec-resume" else run(args)
    else:
        result = inspect(args.evidence)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
