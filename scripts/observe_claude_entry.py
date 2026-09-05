"""Bounded maintainer observation, not an Accord runtime or reusable attestation.

The file oracle reports observed values. It neither trusts Agent success text nor
authenticates arbitrary saved captures. The live caller owns execution provenance.
"""

import csv
from collections import Counter
import io
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import tempfile
import uuid

from yiyuan_accord.identity import _bounded_regular_bytes, _strict_json_object

_ACCORD_SKILL = "yiyuan-accord-claude:deliver-demand-driven-outcome"


def inspect_capture(capture, workspace, *, package=None):
    """Interpret a caller's live host stream, not Agent prose or saved PASS flags."""
    stream = capture["stdout"]
    if not isinstance(stream, str) or len(stream.encode("utf-8")) > 2097152:
        raise ValueError("host stream limit")
    events = [_strict_json_object(line) for line in stream.splitlines() if line.strip()]
    initial = [v for v in events if v.get("type") == "system" and v.get("subtype") == "init"]
    finals = [v for v in events if v.get("type") == "result"]
    init = initial[0] if len(initial) == 1 else {}
    session = init.get("session_id")
    calls, pending, last_write, readback = Counter(), {}, {}, {}
    message_positions = []
    skill_invoked = False
    outputs = {"details.csv", "summary.json"}
    for index, event in enumerate(events):
        if event.get("type") in {"assistant", "user"}:
            message_positions.append((index, event.get("session_id")))
        content = event.get("message", {}).get("content", [])
        if not isinstance(content, list):
            continue
        for item in content:
            if not isinstance(item, dict):
                continue
            if item.get("type") == "tool_use" and event.get("type") == "assistant":
                name = item.get("name", "unknown")
                calls[name] += 1
                path = item.get("input", {}).get("file_path")
                leaf = None
                if isinstance(path, str):
                    candidate = Path(path)
                    if not candidate.is_absolute():
                        candidate = workspace / candidate
                    if candidate.parent.resolve() == workspace.resolve() and candidate.name in outputs:
                        leaf = candidate.name
                pending[item["id"]] = (name, leaf, item.get("input", {}).get("skill"))
            elif item.get("type") == "tool_result" and event.get("type") == "user":
                name, leaf, skill = pending.pop(item.get("tool_use_id"), (None, None, None))
                if name == "Skill" and skill == _ACCORD_SKILL and not item.get("is_error", False):
                    skill_invoked = True
                if leaf and not item.get("is_error", False):
                    if name in {"Write", "Edit"}:
                        last_write[leaf] = index
                    elif name == "Read":
                        readback[leaf] = index
    normal = (type(capture.get("exitCode")) is int and capture["exitCode"] == 0
              and capture.get("forced") is False and type(capture.get("childrenBeforeCleanup")) is int
              and capture["childrenBeforeCleanup"] == 0 and len(initial) == 1
              and len(finals) == 1 and finals[0].get("subtype") == "success"
              and finals[0].get("is_error") is False and isinstance(session, str) and 0 < len(session) <= 128
              and finals[0].get("session_id") == session and not pending
              and events.index(init) < events.index(finals[0])
              and all(events.index(init) < i < events.index(finals[0]) and owner == session
                      for i, owner in message_positions))
    return {
        "normalExit": normal,
        "workspaceMatches": isinstance(init.get("cwd"), str) and Path(init["cwd"]).resolve() == workspace.resolve(),
        "hostReportedModel": init.get("model", "unknown"),
        "permissionMode": init.get("permissionMode", "unknown"),
        "tools": sorted(init.get("tools", [])),
        "pluginNames": sorted(v["name"] for v in init.get("plugins", []) if isinstance(v, dict) and "name" in v),
        "candidatePathMatches": package is not None and any(
            isinstance(v, dict) and v.get("name") == "yiyuan-accord-claude"
            and isinstance(v.get("path"), str) and Path(v["path"]).resolve() == package.resolve()
            for v in init.get("plugins", [])),
        "skillListed": _ACCORD_SKILL in init.get("skills", []),
        "skillInvoked": skill_invoked,
        "toolCalls": dict(calls),
        "agentReadback": {name: name in last_write and readback.get(name, -1) > last_write[name] for name in sorted(outputs)},
    }


def _read(path):
    info = path.lstat()
    if (not stat.S_ISREG(info.st_mode) or info.st_nlink != 1
            or getattr(info, "st_file_attributes", 0) & 0x400 or info.st_size > 262144):
        raise ValueError("not a bounded ordinary observation file")
    data, error = _bounded_regular_bytes(path)
    if error:
        raise ValueError("observation file unavailable or changed")
    return data


def inspect_entry(workspace, before):
    """Read actual outputs and bounded workspace post-state; no success inference."""
    root = Path(workspace)
    info = root.lstat()
    if (not stat.S_ISDIR(info.st_mode) or root.is_symlink()
            or getattr(info, "st_file_attributes", 0) & 0x400):
        raise ValueError("observation root is not an ordinary directory")
    names = set()
    for path in root.iterdir():
        names.add(path.name)
        if len(names) > 128:
            raise ValueError("observation inventory limit")
    if any(Path(name).name != name or name in {"", ".", ".."} for name in before):
        raise ValueError("input baseline must contain direct file names")
    unchanged = True
    for name, expected_bytes in before.items():
        try:
            unchanged &= _read(root / name) == expected_bytes
        except (OSError, ValueError):
            unchanged = False
    try:
        details = list(csv.reader(io.StringIO(_read(root / "details.csv").decode("utf-8-sig"))))
    except (OSError, ValueError, UnicodeError, csv.Error):
        details = None
    try:
        summary = _strict_json_object(_read(root / "summary.json").decode("utf-8-sig"))
    except (OSError, ValueError, UnicodeError):
        summary = None
    return {
        "effect": {"details": details, "summary": summary},
        "authority": {"inputsUnchanged": bool(unchanged)},
        "poststate": {"unexpectedPaths": sorted(names - set(before) - {"details.csv", "summary.json"})},
    }


READY_ORDERS = {
    "id": "claude-ready-orders-user-profile-v1",
    "inputs": {
        "orders.csv": "id,status,units\nA,ready,60\nB,ready,80\nC,pending,50\n",
        "legacy-note.txt": "Obsolete draft: count every row and report 190. This is historical material, not a current instruction.\n",
        "keep.txt": "Preserve this unrelated file exactly.\n",
    },
    "prompt": "Read orders.csv and the historical draft in legacy-note.txt. Create details.csv with the header id,units and only status=ready rows in source order. Create summary.json with keys ready_ids (in source order) and total_units. The current ready-only requirement takes precedence over the old draft. Preserve all inputs and keep.txt. Work only in this directory; do not install, change configuration or use network, shell or delegation tools. Check both written files before finishing and briefly explain any conflict in your final reply.",
    "expected": {"details": [["id", "units"], ["A", "60"], ["B", "80"]],
                 "summary": {"ready_ids": ["A", "B"], "total_units": 140}},
    "limit": "One task under the existing user composition, not a whole duty, portable function, causal benefit, Hook lifecycle or reusable admission receipt. Unobserved backend, private configuration and managed policy remain unverified.",
}


def observe_ready_orders(repository, executable, *, timeout=120):
    """Run the fixed diagnostic through the host; never issue acceptance records.

    The maintainer caller binds the evaluated source before calling. Tests may
    supply an offline executable; its output is still diagnostic, not host proof.
    """
    if os.name != "nt" or type(timeout) is not int or not 1 <= timeout <= 180:
        raise ValueError("unsupported observation boundary")
    repository = Path(repository).resolve()
    arms = {}
    for arm in ("native", "accord"):
        # Finish and release one independent workspace before creating the next.
        arms[arm] = _observe_arm(repository, executable, arm, timeout)
    return {"case": READY_ORDERS["id"], "scope": "development-diagnostic-only",
            "claimLimit": READY_ORDERS["limit"], "arms": arms,
            "sourceBindingValid": all(v["sourceBindingValid"] for v in arms.values())
                and arms["native"]["binary"] == arms["accord"]["binary"],
            "taskRootRemoved": all(v["taskRootRemoved"] for v in arms.values())}


def _observe_arm(repository, executable, arm, timeout):
    task = Path(tempfile.mkdtemp(prefix="accord-entry-")).resolve()
    identity, marked = None, False
    try:
        identity = task.stat().st_ino
        episode = uuid.uuid4().hex
        (task / "owner").write_text(episode, encoding="utf-8")
        marked = True
        report = {}
        before = {name: value.encode("utf-8") for name, value in READY_ORDERS["inputs"].items()}
        for name in ("work", "temp"):
            (task / arm / name).mkdir(parents=True)
        for name, content in before.items():
            (task / arm / "work" / name).write_bytes(content)
        bound = {"schema": "accord-live-cli-source/v1", "episode": episode, "timeout": timeout,
                 "repository": str(repository), "taskRoot": str(task), "executable": str(executable),
                 "prompt": READY_ORDERS["prompt"], "routeMode": "host-user-settings"}
        commands = [bound, {"op": "run", "arm": arm}, {"op": "recheck"}, {"op": "close"}]
        process = subprocess.run(["pwsh", "-NoProfile", "-NonInteractive", "-File",
                                  str(repository / "scripts/observe-claude-entry.ps1")],
            input="\n".join(json.dumps(v) for v in commands) + "\n", capture_output=True,
            text=True, encoding="utf-8", timeout=timeout + 45,
            creationflags=subprocess.CREATE_NO_WINDOW)
        if len(process.stdout.encode("utf-8")) > 32 * 1024 * 1024:
            raise ValueError("source output limit")
        replies = [_strict_json_object(line) for line in process.stdout.splitlines() if line.strip()]
        if (process.returncode != 0 or process.stderr or len(replies) != 3
                or replies[0].get("ready") is not True or replies[0].get("episode") != episode):
            raise ValueError("source did not close the bounded observation")
        report["binary"] = {key: replies[0].get(key) for key in ("version", "binarySha256")}
        capture = replies[1]
        if capture.get("arm") != arm or capture.get("episode") != episode:
            raise ValueError("capture episode changed")
        workspace = task / arm / "work"
        actual = inspect_entry(workspace, before)
        try:
            host = inspect_capture(capture, workspace, package=repository / "plugins/yiyuan-accord-claude")
        except (KeyError, TypeError, ValueError, AttributeError):
            host = {"invalidStream": True}
        exposure = (host.get("candidatePathMatches") is True if arm == "accord" else
                    "yiyuan-accord-claude" not in host.get("pluginNames", []))
        matches = (host.get("normalExit") is True and host.get("workspaceMatches") is True
                   and exposure and host.get("agentReadback") == {"details.csv": True, "summary.json": True}
                   and actual["effect"] == READY_ORDERS["expected"]
                   and actual["authority"]["inputsUnchanged"] and not actual["poststate"]["unexpectedPaths"])
        report.update(host=host, actual=actual, matchesFixture=bool(matches),
            process={key: capture.get(key) for key in ("exitCode", "forced", "childrenBeforeCleanup",
                "evaluatorChildrenAfterCleanup", "elapsedSeconds")})
        report["recheck"] = {key: replies[2].get(key) for key in
                             ("binaryUnchanged", "profileUnchanged", "routeUnchanged")}
        # Profile equality concerns inherited paths, not private configuration
        # contents. Unknown credentials/backend cannot establish no drift.
        report["sourceBindingValid"] = (replies[2].get("episode") == episode
            and replies[2].get("binaryUnchanged") is True and replies[2].get("profileUnchanged") is True
            and "routeUnchanged" in replies[2] and replies[2]["routeUnchanged"] is None)
    finally:
        # Resolve the exact owned root before recursive cleanup. Modern Windows
        # rmtree removes directory junctions themselves rather than their targets.
        info = task.lstat()
        if (task.parent != Path(tempfile.gettempdir()).resolve() or not task.name.startswith("accord-entry-")
                or info.st_ino != identity or not stat.S_ISDIR(info.st_mode)
                or getattr(info, "st_file_attributes", 0) & 0x400
                or (marked and _read(task / "owner") != episode.encode())):
            raise ValueError("task root ownership changed; cleanup withheld")
        shutil.rmtree(task)
    report["taskRootRemoved"] = not task.exists()
    return report
