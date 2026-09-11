"""Prepare/run a bounded Codex CLI observation or prepare an App Server case.

No model is called by prepare or inspect. Run uses the existing CODEX_HOME auth,
one ephemeral exec, explicit model/effort, workspace-write, and reviewed task-local
hooks. It does not establish installed-plugin, multi-turn or full resource acceptance.
Windows Job Objects contain descendants before the suspended CLI starts executing.
The caller must select an existing Windows sandbox backend explicitly; this runner
does not initialize/install a sandbox or edit shared configuration.
Evidence and deliverables are retained for review; owned live processes are released.
The Python prepare API accepts an explicit app_server_case for a caller-owned
dispatcher; inspect then checks that protocol and its actual input receipts.
Optional limits.usageCaps names native cumulative token dimensions explicitly.
Inspection reports those limits without changing them or controlling execution;
the dispatcher still owns prospective time, cost, interruption and cleanup bounds.
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


def digest(path):
    path = Path(path)
    before = path.lstat()
    if (not stat.S_ISREG(before.st_mode) or before.st_nlink != 1 or path.is_symlink()
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
    if protocol not in ("exec", "app-server"):
        raise ValueError("unsupported entry protocol")
    if protocol == "app-server" and ("command" in manifest or "promptSha256" in manifest
                                     or manifest.get("tracePath") != "native/stdout.jsonl"):
        raise ValueError("App Server manifest contains incompatible CLI or trace metadata")
    if protocol == "app-server" and "usageCaps" in manifest["limits"]:
        _usage_caps(manifest["limits"]["usageCaps"])
    ordinary_dir(manifest["workspace"])
    return manifest


def build_command(manifest):
    if manifest.get("entryProtocol", "exec") != "exec":
        raise ValueError("CLI command cannot represent an App Server case")
    hooks = []
    for event in EVENTS:
        parts = [manifest["python"], "-B", manifest["runner"], "hook", "--evidence", manifest["evidence"], "--event", event]
        # No shell metacharacters or untrusted prompt text are interpolated here.
        command = subprocess.list2cmdline(parts)
        timeout = 3 if event in ("SessionEnd", "Interrupt") else 10
        hooks.append(event + "=[{hooks=[{type=\"command\",command=" + json.dumps(command)
                     + ",timeout=" + str(timeout) + "}]}]")
    return [manifest["codex"], "exec", "--ignore-user-config", "--disable", "plugins", "--disable", "apps", "--enable", "hooks",
            "--ephemeral", "--skip-git-repo-check", "--sandbox", "workspace-write", "--json", "--color", "never",
            "--output-last-message", str(Path(manifest["evidence"]) / "last-message.txt"),
            "--dangerously-bypass-hook-trust", "-C", manifest["workspace"], "-m", manifest["model"],
            "--add-dir", str(Path(manifest["evidence"]) / "state"),
            "-c", "approval_policy=\"never\"", "-c", "model_reasoning_effort=" + json.dumps(manifest["reasoning"]),
            "-c", "windows.sandbox=" + json.dumps(manifest["windowsSandbox"]),
            "-c", "hooks={" + ",".join(hooks) + "}", "-"]


def prepare(args, *, app_server_case=None):
    """Prepare CLI execution, or explicitly bind a caller-owned App Server case.

    App Server lifecycle/dispatch remains caller-owned; preparing its fixtures
    must not fabricate a CLI command or silently supply a different prompt.
    """
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
    evidence, workspace = Path(args.evidence).absolute(), Path(args.workspace).absolute()
    package = ordinary_dir(args.package)
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
    if any(any(c in str(p) for c in ('"', '\n', '\r', '%', '!', '`', '$', '&', '|', '<', '>', '^')) for p in (*paths.values(), evidence, workspace)):
        raise ValueError("shell-sensitive path cannot be used in hook command")
    if os.name == "nt" and paths["codex"].suffix.lower() != ".exe":
        raise ValueError("bind the native codex.exe, not an npm shell wrapper")
    hashes = {k: digest(p) for k, p in paths.items()}
    protocol = "app-server" if app_server_case is not None else "exec"
    help_run = subprocess.run([str(paths["codex"]), protocol, "--help"], capture_output=True, timeout=15)
    help_text = help_run.stdout.decode("utf-8", "replace")
    required = ("--ephemeral", "--ignore-user-config", "--dangerously-bypass-hook-trust", "--sandbox", "--output-last-message") if protocol == "exec" else ("app-server",)
    if help_run.returncode or any(flag not in help_text for flag in required):
        raise ValueError("native CLI help does not support required boundary")
    version = subprocess.run([str(paths["codex"]), "--version"], capture_output=True, timeout=15)
    if version.returncode:
        raise ValueError("native version probe failed")
    evidence.mkdir()
    workspace.mkdir()
    ordinary_dir(evidence)
    ordinary_dir(workspace)
    for name in ("hooks", "state", "temp"):
        (evidence / name).mkdir()
    inputs = {"orders.csv": ORDERS, "order_source.py": SOURCE.encode(), "keep.txt": b"Unrelated original. Preserve exactly.\n",
              "README.txt": ("订单数据接口是 order_source.py；从本目录运行以下本地命令获取 CSV：\n"
                             + subprocess.list2cmdline([str(paths["python"]), "-B", "order_source.py"])
                             + "\norders.csv 为接口原始存档，请保留。\n").encode()}
    for name, data in inputs.items():
        (workspace / name).write_bytes(data)
    if protocol == "exec":
        (evidence / "prompt.txt").write_text(PROMPT, encoding="utf-8")
    (evidence / "native-help.txt").write_bytes(help_run.stdout + help_run.stderr)
    (evidence / "native-version.txt").write_bytes(version.stdout + version.stderr)
    manifest = {"schema": "accord-codex-entry/v1", "episode": uuid.uuid4().hex,
                "evidence": str(evidence), "workspace": str(workspace), "package": str(package),
                **{k: str(p) for k, p in paths.items()}, "sourceHashes": hashes,
                "model": args.model, "reasoning": args.reasoning, "timeoutSeconds": args.timeout,
                "windowsSandbox": args.windows_sandbox,
                "sandboxSetup": "caller-selected existing backend; no setup/install or shared config mutation by runner",
                "inputs": {k: hashlib.sha256(v).hexdigest() for k, v in inputs.items()},
                "expected": {"details": [["id", "units"], ["A", "60"], ["B", "80"]],
                             "summary": {"ready_ids": ["A", "B"], "total_units": 140}}, "limits": LIMITS,
                "docs": ["https://learn.chatgpt.com/docs/hooks", "https://learn.chatgpt.com/docs/config-file/config-reference",
                         "https://learn.chatgpt.com/docs/config-file/config-basic#windows-sandbox-mode"]}
    if protocol == "exec":
        manifest["promptSha256"] = digest(evidence / "prompt.txt")
        manifest["command"] = build_command(manifest)
    else:
        manifest.update(app_server_case)
        manifest["entryProtocol"] = "app-server"
        manifest["tracePath"] = "native/stdout.jsonl"
        manifest["executionOwner"] = "caller-owned native App Server; no CLI run command"
    save(evidence / "manifest.json", manifest)
    return {"prepared": True, "evidence": str(evidence), "workspace": str(workspace), "modelCalled": False}


def hook(args):
    manifest = load_manifest(args.evidence)
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
        r'Write-Output\s+"EXIT=\$(?P=code)";\s*'
        r'(?:exit\s+\$(?P=code)|if\s*\(\$(?P=code)\s+-ne\s+0\)\s*'
        r'\{\s*exit\s+\$(?P=code)\s*\})\s*$', re.I)

    def direct_source(command, actions):
        if not isinstance(command, str):
            return False, False
        normalized = command.replace("\\\\", "\\")
        wrapper = re.fullmatch(r'"[^"\r\n]+[\\/]pwsh\.exe" -Command ([\s\S]+)', normalized, re.I)
        if not wrapper:
            return False, False
        body = wrapper[1]
        if protocol == "app-server":
            if (not isinstance(actions, list) or len(actions) != 1 or not isinstance(actions[0], dict)
                    or actions[0].get("type") != "unknown" or not isinstance(actions[0].get("command"), str)):
                return False, False
            # Native parsed action avoids interpreting display-only shell quoting.
            # Both action and displayed command must match their start event.
            body = actions[0]["command"]
        elif len(body) >= 2 and body[0] in ("'", '"') and body[-1] == body[0]:
            body = body[1:-1]
        status_mode = None
        if protocol == "app-server" and child_status.search(body) is not None:
            status_mode = "wrapped"
            body = child_status.sub("", body)
        elif protocol == "app-server" and propagated_status.search(body) is not None:
            status_mode = "propagated"
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
            elif status_mode == "propagated":
                if (not lines or not re.fullmatch(r"EXIT=-?\d+", lines[-1])
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


def inspect(evidence):
    manifest = load_manifest(evidence)
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
    result = prepare(args) if args.action == "prepare" else run(args) if args.action == "run" else inspect(args.evidence)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
