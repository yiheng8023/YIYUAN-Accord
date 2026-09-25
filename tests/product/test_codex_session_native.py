"""Bounded fixed-response Codex App Server integration for codex-session.cjs."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath, PureWindowsPath
import shutil
import sqlite3
import stat
import sys
import tempfile
import time
import unittest


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.inspect_native_resources import read_native_resource_records
from scripts.observe_codex_entry import digest, read_regular, save
from scripts.observe_codex_lifecycle import (
    _App, _Fixture, _argv, _codex_version, _ordinary_dir, _owned_environment,
    _record_released, _regular_file, _tree_hashes,
)
from tests.product.test_carrier_handoff import proposal_fixture_item


SCHEMA = "accord-codex-session-native-evidence/v1"
PROVIDER_REQUESTS = 10
COLD_PROVIDER_REQUESTS = 2
SOURCE_PROVIDER_REQUESTS = 2
SOURCE_FILES = (
    "tests/product/test_codex_session_native.py",
    "tests/product/codex_session_native.cjs",
    "tests/product/test_carrier_handoff.py",
    "scripts/observe_codex_lifecycle.py",
    "scripts/observe_codex_entry.py",
    "scripts/codex_rpc.py",
    "scripts/inspect_native_resources.py",
    "runtime/codex-session.cjs",
    "runtime/carrier-handoff.cjs",
    "runtime/codex-connection.cjs",
    "runtime/carrier-recorder.cjs",
    "runtime/task-checkpoint.cjs",
    "runtime/codex-context.cjs",
)
TOOL_SEQUENCE = {
    1: "accord_request_handoff",
    3: "accord_inspect_context",
    4: "accord_request_handoff",
    7: "accord_request_handoff",
}
TURN_COUNTS = (1, 3, 2)


def _sha(path: Path) -> str:
    return hashlib.sha256(read_regular(path, 1024 * 1024 * 1024)).hexdigest()


def _fresh_root(value) -> Path:
    root = Path(value).absolute()
    parent = root.parent
    if root.exists() or not parent.is_dir() or parent.resolve(strict=True) != parent or parent.is_symlink():
        raise ValueError("evidence must be a fresh root with an ordinary parent")
    return root


def _restore_roots(evidence_value, prior_value=None):
    root = _fresh_root(evidence_value)
    if prior_value is None:
        return root, None
    prior = _ordinary_dir(Path(prior_value).absolute())
    candidate = root.resolve(strict=False)
    prior_resolved = prior.resolve(strict=True)
    if (candidate == prior_resolved or prior_resolved in candidate.parents
            or candidate in prior_resolved.parents):
        raise ValueError("restore evidence root and prior root must not be nested")
    return root, prior


def _file_observation(path: Path) -> dict:
    if not path.exists():
        return {"path": str(path), "present": False}
    path = _regular_file(path)
    info = path.stat()
    return {"path": str(path), "present": True, "sha256": digest(path),
            "size": info.st_size, "mode": stat.S_IMODE(info.st_mode)}


def _recorded_relative(value, manifest: dict):
    pure = (PureWindowsPath if manifest.get("resourceController") == "windows-job-object"
            else PurePosixPath)
    recorded_root = pure(manifest.get("evidence", ""))
    candidate = pure(value)
    if not recorded_root.is_absolute() or not candidate.is_absolute():
        raise ValueError("recorded native path is not absolute")
    try:
        relative = candidate.relative_to(recorded_root)
    except ValueError:
        raise ValueError("recorded native path is outside its evidence root") from None
    if not relative.parts:
        raise ValueError("recorded native path must name an evidence child")
    return relative.parts


def _portable_path(root: Path, recorded, manifest: dict) -> Path:
    return root.joinpath(*_recorded_relative(recorded, manifest))


def _retained_session_path(root: Path, recorded, manifest: dict) -> Path:
    relative = _recorded_relative(recorded, manifest)
    if relative[:2] != ("home", "sessions") or len(relative) < 3:
        raise ValueError("recorded native session path is outside home/sessions")
    return root.joinpath("retained", "native-sessions", *relative[2:])


def _shared_config_observation() -> dict:
    configured = os.environ.get("CODEX_HOME")
    root = Path(configured) if configured else Path.home() / ".codex"
    return _file_observation(root / "config.toml")


def _source_hashes(root=ROOT) -> dict:
    return {name: _sha(Path(root) / name) for name in SOURCE_FILES}


def _input_inventory(root: Path) -> dict:
    root = _ordinary_dir(root)
    inventory = {}
    def visit(directory: Path):
        with os.scandir(directory) as entries:
            for entry in entries:
                path_value = Path(entry.path)
                info = path_value.lstat()
                relative = path_value.relative_to(root).as_posix()
                reparse = bool(getattr(info, "st_file_attributes", 0) & 0x400)
                if entry.is_symlink():
                    inventory[relative] = {"type": "symlink", "target": os.readlink(entry.path)}
                elif reparse:
                    try:
                        target = os.readlink(entry.path)
                    except OSError:
                        target = None
                    inventory[relative] = {"type": "reparse", "target": target,
                                           "attributes": getattr(info, "st_file_attributes", 0)}
                elif stat.S_ISDIR(info.st_mode):
                    inventory[relative] = {"type": "directory", "mode": stat.S_IMODE(info.st_mode)}
                    visit(path_value)
                elif stat.S_ISREG(info.st_mode) and info.st_nlink == 1:
                    inventory[relative] = {"type": "file", "sha256": digest(path_value),
                                           "size": info.st_size, "mode": stat.S_IMODE(info.st_mode)}
                else:
                    inventory[relative] = {"type": "other", "mode": info.st_mode,
                                           "links": info.st_nlink}
    visit(root)
    return inventory


def _snapshot_sources(evidence: Path, hashes: dict) -> Path:
    snapshot = evidence / "retained" / "executed-sources"
    snapshot.mkdir()
    for name, expected in hashes.items():
        source, destination = ROOT / name, snapshot / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, destination)
        if _sha(source) != expected or _sha(destination) != expected:
            raise ValueError("execution source changed during freeze: " + name)
    return snapshot


def _preserve_native_sessions(root: Path, resource: dict | None, manifest: dict) -> dict:
    if not isinstance(resource, dict) or not _record_released(resource, manifest):
        return {"preserved": False, "reason": "writer-release-unconfirmed"}
    source = root / "home/sessions"
    if not source.exists():
        return {"preserved": False, "reason": "native-sessions-absent"}
    before = _tree_hashes(source)
    destination = root / "retained/native-sessions"
    shutil.copytree(source, destination)
    source_after, retained = _tree_hashes(source), _tree_hashes(destination)
    if source_after != before or retained != before:
        raise RuntimeError("native session history changed during retention")
    save(root / "retained/native-sessions-sha256.json", retained)
    return {"preserved": True, "files": len(retained), "hashes": retained}


def fixed_provider_item(body, ordinal):
    if not 1 <= ordinal <= PROVIDER_REQUESTS:
        raise ValueError("provider request ordinal exceeds fixed sequence")
    tool = TOOL_SEQUENCE.get(ordinal)
    if tool is None:
        return None
    state = {"next": True, "contextRemaining": 1 if tool == "accord_inspect_context" else 0}
    item = proposal_fixture_item(body, ordinal, state)
    if item is None:
        raise ValueError("fixed dynamic tool is unavailable in provider request")
    return item


def cold_provider_item(body, ordinal):
    if not 1 <= ordinal <= COLD_PROVIDER_REQUESTS:
        raise ValueError("cold provider request ordinal exceeds fixed sequence")
    if ordinal == 2:
        return None
    item = proposal_fixture_item(body, ordinal, {"next": True, "contextRemaining": 1})
    if item is None or _provider_tool(item) != "accord_inspect_context":
        raise ValueError("restored context tool is unavailable in provider request")
    return item


def source_provider_item(body, ordinal):
    return cold_provider_item(body, ordinal)


def _read_json(path: Path, limit=8 * 1024 * 1024):
    return json.loads(read_regular(path, limit))


def _json_lines(path: Path, limit=32 * 1024 * 1024):
    data = read_regular(path, limit).decode("utf-8")
    return [json.loads(line) for line in data.splitlines() if line]


def _provider_tool(item: dict):
    if item.get("type") == "function_call":
        return item.get("name")
    if item.get("type") == "custom_tool_call" and item.get("namespace") == "functions":
        source = item.get("input", "")
        for name in ("accord_request_handoff", "accord_inspect_context"):
            if name in source:
                return name
    return None


def _rpc_id(value):
    if type(value) not in (str, int):
        raise ValueError("native RPC id is not a string or integer")
    return (type(value).__name__, value)


def _open_retained_ledger(path):
    database_path = _regular_file(path)
    # mode=ro can create WAL/SHM files. Only inspect a checkpointed ledger after
    # recorded writer release; immutable avoids locks and sidecar creation.
    for suffix in ("-wal", "-journal"):
        sidecar = database_path.with_name(database_path.name + suffix)
        if sidecar.is_symlink() or sidecar.exists() and _regular_file(sidecar).stat().st_size:
            raise ValueError("native ledger has uncheckpointed or unsafe sidecar data")
    return sqlite3.connect(database_path.as_uri() + "?mode=ro&immutable=1", uri=True)


def _validate_restore_ledger_sidecars(path: Path):
    ledger = _regular_file(path)
    for suffix in ("-wal", "-journal"):
        sidecar = ledger.with_name(ledger.name + suffix)
        if sidecar.is_symlink() or sidecar.exists() and _regular_file(sidecar).stat().st_size:
            raise ValueError("native ledger has uncheckpointed or unsafe sidecar data")
    shared_memory = ledger.with_name(ledger.name + "-shm")
    if shared_memory.is_symlink():
        raise ValueError("native ledger SHM is redirected")
    if shared_memory.exists():
        _regular_file(shared_memory)
    return ledger


def _copy_file(source: Path, destination: Path) -> str:
    source = _regular_file(source)
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, destination)
    if _sha(source) != _sha(destination):
        raise ValueError("copied restore input differs: " + str(source))
    return _sha(destination)


def _prepare_restore_inputs(prior_value, root: Path, source_mode=False) -> dict:
    prior = _ordinary_dir(Path(prior_value).absolute())
    root_resolved, prior_resolved = root.resolve(strict=True), prior.resolve(strict=True)
    if (root_resolved == prior_resolved or prior_resolved in root_resolved.parents
            or root_resolved in prior_resolved.parents):
        raise ValueError("restore evidence root and prior root must not be nested")
    prior_inventory = _input_inventory(prior)
    inspection = inspect_evidence(prior)
    prior_manifest = _read_json(prior / "manifest.json")
    prior_post = _read_json(prior / "poststate.json")
    envelope = _read_json(prior / "retained/node-result.json", 16 * 1024 * 1024)
    result = envelope.get("result", {})
    expected_scope = (result.get("scope") if source_mode else
                      result.get("adoptedSecond", {}).get("scope"))
    transfer_id = None if source_mode else result.get("adoptedSecond", {}).get("transferId")
    source = result.get("source") if source_mode else None
    if source_mode:
        if (inspection.get("valid") is not True or inspection.get("mode") != "source-start"
                or prior_manifest.get("mode") != "source-start"
                or not isinstance(source, dict)
                or not isinstance(expected_scope, dict)
                or expected_scope.get("scopeRef") != "native-source-scope"
                or expected_scope.get("activeTransferId") is not None
                or expected_scope.get("writerThreadId") != source.get("threadId")):
            raise ValueError("prior original source is not a restore basis")
    elif (inspection.get("valid") is not True or transfer_id != "native-transfer-2"
            or not isinstance(expected_scope, dict)
            or expected_scope.get("scopeRef") != "native-session-scope"
            or expected_scope.get("activeTransferId") is not None
            or expected_scope.get("writerThreadId") != result.get("threadIds", {}).get("target2")):
        raise ValueError("prior successful adoption scope is not a cold restore basis")
    resources = read_native_resource_records(prior / "native", ("codex-session-controller",))
    resource = resources["codex-session-controller"]
    if not _record_released(resource, prior_manifest):
        raise ValueError("prior controller release is not quiescent evidence")
    ledger = _validate_restore_ledger_sidecars(prior / "retained/carrier.sqlite")
    sessions = _ordinary_dir(prior / "retained/native-sessions")
    session_hashes = _tree_hashes(sessions)
    if session_hashes != prior_post.get("nativeSessions", {}).get("hashes"):
        raise ValueError("prior retained native sessions differ")

    portable = root / "retained/prior-evidence"
    portable.mkdir()
    files = {
        "manifest.json": prior / "manifest.json",
        "poststate.json": prior / "poststate.json",
        "node-result.json": prior / "retained/node-result.json",
        "controller-config.json": prior / "retained/controller-config.json",
        "controller-done.json": prior / "retained/controller-done.json",
        "native-sessions-sha256.json": prior / "retained/native-sessions-sha256.json",
        "controller-resource.json": prior / "native/codex-session-controller/resources.json",
        "workspace/keep.txt": prior / "workspace/keep.txt",
    }
    if source_mode:
        files["native-requests.jsonl"] = prior / "native/app-server/requests.jsonl"
        files["native-stdout.jsonl"] = prior / "native/app-server/stdout.jsonl"
    for name, source_path in files.items():
        _copy_file(source_path, portable / name)
    save(portable / "inspection.json", inspection)
    _copy_file(ledger, portable / "carrier.sqlite")
    _copy_file(ledger, root / "retained/carrier.sqlite")
    shutil.copytree(sessions, portable / "native-sessions")
    shutil.copytree(sessions, root / "home/sessions")
    if (_tree_hashes(portable / "native-sessions") != session_hashes
            or _tree_hashes(root / "home/sessions") != session_hashes):
        raise ValueError("cold native session copies differ")
    _copy_file(prior / "workspace/keep.txt", root / "workspace/keep.txt")
    portable_hashes = _tree_hashes(portable)
    return {"priorPath": str(prior), "priorInventoryBefore": prior_inventory,
            "portableRoot": str(portable), "portableHashes": portable_hashes,
            **({"source": {key: source[key] for key in ("threadId", "connectionId",
                                                       "authorityRef", "stateRef")}}
               if source_mode else {"transferId": transfer_id}),
            "scopeRef": expected_scope["scopeRef"],
            "expectedScope": json.loads(json.dumps(expected_scope)),
            "writerThreadId": expected_scope["writerThreadId"],
            **({"threadIds": result["threadIds"]} if not source_mode else {}),
            "sessionHashes": session_hashes,
            "keepSha256": digest(root / "workspace/keep.txt")}


def _version_record_ok(root: Path, manifest: dict, role: str, identity_name: str) -> bool:
    record = _read_json(root / f"retained/version-probes/{role}/record.json")
    stdout = read_regular(root / f"retained/version-probes/{role}/stdout.txt", 64 * 1024).decode().strip()
    identity = manifest["identities"][identity_name]
    return (record.get("arguments") == [identity["path"], "--version"]
            and record.get("executable") == identity["path"]
            and record.get("sha256") == identity["sha256"]
            and record.get("version") == identity["version"] == stdout
            and record.get("exitCode") == 0 and record.get("forced") is False
            and _record_released(record, manifest))


def _raw_source_origin(requests, received, source, session_path: Path):
    starts = [row for row in requests if row.get("method") == "thread/start"]
    if len(starts) != 1:
        raise ValueError("original source requires exactly one raw thread/start")
    start = starts[0]
    responses = [row for row in received if row.get("id") == start.get("id")
                 and "method" not in row]
    receipt = responses[0].get("result", {}) if len(responses) == 1 else {}
    thread_id = source.get("threadId")
    if (len(responses) != 1 or "error" in responses[0]
            or receipt.get("thread", {}).get("id") != thread_id
            or receipt.get("thread", {}).get("ephemeral") is not False
            or start.get("params", {}).get("model") != "fixture-no-model"
            or start.get("params", {}).get("modelProvider") != "accord_fixture"
            or start.get("params", {}).get("cwd") != source.get("cwd")):
        raise ValueError("raw original source creation acknowledgement differs")
    rows = _json_lines(session_path)
    metas = [row for row in rows if row.get("type") == "session_meta"
             and row.get("payload", {}).get("id") == thread_id]
    tools = metas[0].get("payload", {}).get("dynamic_tools") if len(metas) == 1 else None
    names = [item.get("name") for item in tools] if isinstance(tools, list) else None
    if (tools != start.get("params", {}).get("dynamicTools")
            or names != ["accord_request_handoff", "accord_inspect_context"]):
        raise ValueError("original source persistent dynamic tools differ")
    return {"requestId": start["id"], "threadId": thread_id,
            "tools": names, "sessionRows": len(rows)}


def _inspect_source_start(root: Path, manifest: dict, post: dict,
                          envelope: dict, config: dict):
    result = envelope.get("result", {})
    source = result.get("source", {})
    thread_id = source.get("threadId")
    scope = result.get("scope", {})
    if (manifest.get("mode") != "source-start" or
            manifest.get("providerRequests") != SOURCE_PROVIDER_REQUESTS or
            config.get("mode") != "source-start" or
            config.get("schema") != "accord-codex-session-native-config/v1" or
            envelope.get("success") is not True or envelope.get("failure") is not None or
            result.get("schema") != "accord-codex-session-native-source-start-result/v1" or
            result.get("success") is not True or
            source.get("connectionId") != config.get("binding", {}).get("connectionId") or
            source.get("authorityRef") != "native-source-authority" or
            source.get("stateRef") != "native-source-state" or
            scope.get("scopeRef") != "native-source-scope" or
            scope.get("writerThreadId") != thread_id or
            scope.get("activeTransferId") is not None or
            result.get("sessionState", {}).get("transfers") != [] or
            result.get("sessionState", {}).get("turnCount") != 1 or
            result.get("run", {}).get("status") != "completed" or
            result.get("run", {}).get("sourceThreadId") != thread_id or
            len(result.get("history", {}).get("thread", {}).get("turns", [])) != 1 or
            result["history"]["thread"]["turns"][0].get("status") != "completed"):
        raise ValueError("original source identity, scope or completed turn differs")
    if (not isinstance(manifest.get("sourceHashes"), dict) or
            set(manifest["sourceHashes"]) != set(SOURCE_FILES) or
            any(_sha(root / "retained/executed-sources" / name) != expected
                for name, expected in manifest["sourceHashes"].items()) or
            post.get("sourceHashesAfter") != manifest["sourceHashes"] or
            post.get("keepSha256After") != manifest.get("keepSha256Before") or
            post.get("sharedConfigAfter") != manifest.get("sharedConfigBefore") or
            post.get("codexSha256After") != manifest.get("identities", {}).get("codex", {}).get("sha256") or
            post.get("nodeSha256After") != manifest.get("identities", {}).get("node", {}).get("sha256") or
            post.get("executionFailure") is not None or post.get("cleanupFailure") is not None or
            post.get("fixtureThreadStopped") is not True or
            post.get("nativeSessions", {}).get("preserved") is not True):
        raise ValueError("original source protected evidence differs")
    if (not _version_record_ok(root, manifest, "source", "codex") or
            not _version_record_ok(root, manifest, "node", "node")):
        raise ValueError("original source executable identity differs")
    resource = read_native_resource_records(root / "native", ("codex-session-controller",))["codex-session-controller"]
    close = envelope.get("close", {})
    done = _read_json(root / "retained/controller-done.json")
    if (not _record_released(resource, manifest) or resource.get("exitCode") != 0 or
            done.get("kind") != "done" or done.get("success") is not True or
            close.get("nativeExit") != {"code": 0, "signal": None} or
            close.get("connectionClosed") is not True or close.get("stdoutEnded") is not True or
            close.get("closeFailure") is not None):
        raise ValueError("original source controller release differs")
    sessions = _ordinary_dir(root / "retained/native-sessions")
    session_hashes = _tree_hashes(sessions)
    relative = result.get("nativeSession", {}).get("relativePath")
    session_path = _retained_session_path(root, source.get("sessionPath", ""), manifest)
    if (len(session_hashes) != 1 or session_hashes != post["nativeSessions"].get("hashes") or
            session_hashes != _read_json(root / "retained/native-sessions-sha256.json") or
            session_path.relative_to(sessions).as_posix() != relative or
            result.get("history", {}).get("thread", {}).get("path") != source.get("sessionPath") or
            result.get("nativeSession", {}).get("tools") !=
                ["accord_request_handoff", "accord_inspect_context"]):
        raise ValueError("original source retained session differs")
    requests = _json_lines(root / "native/app-server/requests.jsonl")
    received = _json_lines(root / "native/app-server/stdout.jsonl")
    proof = _raw_source_origin(requests, received, source, session_path)
    starts = [row for row in requests if row.get("method") == "thread/start"]
    turns = [row for row in requests if row.get("method") == "turn/start"]
    if (len(turns) != 1 or turns[0].get("params", {}).get("threadId") != thread_id or
            any(row.get("method") in {"thread/resume", "thread/fork", "thread/archive",
                                      "thread/delete", "thread/unsubscribe"} for row in requests)):
        raise ValueError("original source raw native method sequence differs")
    responses = [row for row in received if row.get("id") == turns[0].get("id") and
                 "method" not in row]
    turn_id = responses[0].get("result", {}).get("turn", {}).get("id") if len(responses) == 1 else None
    terminals = [row for row in received if row.get("method") == "turn/completed" and
                 row.get("params", {}).get("threadId") == thread_id and
                 row.get("params", {}).get("turn", {}).get("id") == turn_id and
                 row.get("params", {}).get("turn", {}).get("status") == "completed"]
    if len(terminals) != 1:
        raise ValueError("original source terminal differs")
    _inspect_source_context_exchange(root, thread_id, turn_id, SOURCE_PROVIDER_REQUESTS)
    database = _open_retained_ledger(root / "retained/carrier.sqlite")
    try:
        scopes = database.execute("SELECT scope_ref,writer_thread_id,active_transfer_id,fence_token FROM scopes").fetchall()
        transfers = database.execute("SELECT transfer_id FROM transfers").fetchall()
    finally:
        database.close()
    if scopes != [("native-source-scope", thread_id, None, scope.get("token"))] or transfers:
        raise ValueError("original source durable scope differs")
    return {"valid": True, "mode": "source-start", "threadId": thread_id,
            "sourceOrigin": proof, "providerRequests": SOURCE_PROVIDER_REQUESTS,
            "claimLimit": "Read-only original source protocol inspection; no model judgment or product acceptance."}


def _inspect_source_context_exchange(root, thread_id, turn_id, count):
    requests = _json_lines(root / "native/app-server/requests.jsonl")
    received = _json_lines(root / "native/app-server/stdout.jsonl")
    tools = [row for row in received if row.get("method") == "item/tool/call"]
    replies = [row for row in requests if "method" not in row and "id" in row]
    if (len(tools) != 1 or tools[0].get("params", {}).get("tool") != "accord_inspect_context" or
            tools[0].get("params", {}).get("threadId") != thread_id or
            tools[0].get("params", {}).get("turnId") != turn_id or
            len([row for row in replies if row.get("id") == tools[0].get("id") and
                 row.get("result", {}).get("success") is True]) != 1):
        raise ValueError("source context tool native request/reply differs")
    provider_rows = _json_lines(root / "retained/provider-requests.jsonl")
    responses = [_read_json(root / f"retained/provider-response-{n}.json")
                 for n in range(1, count + 1)]
    if (len(provider_rows) != count or len(responses) != count or
            _provider_tool(responses[0]["response"]["output"][0]) != "accord_inspect_context" or
            _provider_tool(responses[1]["response"]["output"][0]) is not None or
            any(row.get("transportStatus") != "completed" for row in responses)):
        raise ValueError("source fixed provider receipts differ")
    items = provider_rows[1].get("request", {}).get("input", [])
    prior_items = provider_rows[0].get("request", {}).get("input", [])
    if items[:len(prior_items)] != prior_items:
        raise ValueError("source provider input history changed")
    # Resume includes earlier tool calls. Correlate only the newly appended pair.
    current_items = items[len(prior_items):]
    calls = [item for item in current_items if _provider_tool(item) == "accord_inspect_context"]
    outputs = [item for item in current_items if item.get("type") in
               {"function_call_output", "custom_tool_call_output"}]
    if (len(calls) != 1 or len(outputs) != 1 or
            calls[0].get("call_id") != tools[0].get("params", {}).get("callId") or
            calls[0].get("call_id") != outputs[0].get("call_id")):
        raise ValueError("source provider tool result differs")
    try:
        context = json.loads(outputs[0].get("output", ""))
    except (TypeError, json.JSONDecodeError):
        raise ValueError("source provider context output is not structured") from None
    conditions = context.get("observation", {}).get("conditions", {})
    if (context.get("schema") != "yiyuan-accord-native-context-reply/v1" or
            conditions.get("threadId") != thread_id or conditions.get("turnId") != turn_id):
        raise ValueError("source provider context identity differs")


def _inspect_source_restore(root: Path, manifest: dict, post: dict,
                            envelope: dict, config: dict):
    restore = manifest.get("restore", {})
    portable = _ordinary_dir(root / "retained/prior-evidence")
    previous_manifest = _read_json(portable / "manifest.json")
    previous = _read_json(portable / "node-result.json").get("result", {})
    source = restore.get("source", {})
    thread_id = source.get("threadId")
    result = envelope.get("result", {})
    expected = restore.get("expectedScope", {})
    claimed = result.get("scopeAfter", {})
    if (manifest.get("mode") != "source-restore" or
            config.get("mode") != "source-restore" or
            config.get("schema") != "accord-codex-session-native-config/v2" or
            manifest.get("providerRequests") != SOURCE_PROVIDER_REQUESTS or
            _tree_hashes(portable) != restore.get("portableHashes") or
            _recorded_relative(config.get("restore", {}).get("priorRoot", ""), manifest) !=
                ("retained", "prior-evidence") or
            _recorded_relative(config.get("restore", {}).get("sessionsRoot", ""), manifest) !=
                ("home", "sessions") or
            config.get("restore", {}).get("source") != source or
            config.get("restore", {}).get("expectedScope") != expected or
            config.get("restore", {}).get("portableHashes") != restore.get("portableHashes") or
            previous_manifest.get("mode") != "source-start" or
            previous.get("scope") != expected or
            {key: previous.get("source", {}).get(key) for key in source} != source or
            source.get("connectionId") == config.get("binding", {}).get("connectionId") or
            not _record_released(_read_json(portable / "controller-resource.json"), previous_manifest) or
            envelope.get("success") is not True or envelope.get("failure") is not None or
            result.get("schema") != "accord-codex-session-native-source-restore-result/v1" or
            result.get("success") is not True):
        raise ValueError("restored source portable identity or origin differs")
    for identity in ("codex", "node"):
        if any(previous_manifest.get("identities", {}).get(identity, {}).get(field) !=
               manifest.get("identities", {}).get(identity, {}).get(field)
               for field in ("sha256", "version")):
            raise ValueError("restored source executable identity differs")
    prior_sessions = _ordinary_dir(portable / "native-sessions")
    relative = previous.get("nativeSession", {}).get("relativePath")
    if (not isinstance(relative, str) or
            list(restore.get("sessionHashes", {})) != [relative] or
            not relative.endswith(f"{thread_id}.jsonl") or
            _tree_hashes(prior_sessions) != restore.get("sessionHashes") or
            _tree_hashes(prior_sessions) != _read_json(portable / "native-sessions-sha256.json") or
            len(restore.get("sessionHashes", {})) != 1):
        raise ValueError("restored source prior native session differs")
    proof = _raw_source_origin(_json_lines(portable / "native-requests.jsonl"),
                               _json_lines(portable / "native-stdout.jsonl"),
                               previous.get("source", {}), prior_sessions / relative)
    if (result.get("origin", {}).get("requestId") != proof["requestId"] or
            result.get("origin", {}).get("threadId") != thread_id or
            result.get("origin", {}).get("tools") != proof["tools"] or
            result.get("origin", {}).get("sessionRelativePath") != relative or
            result.get("verifyEvidence", {}).get("prepare", {}).get("origin") != result.get("origin") or
            result.get("restoredState", {}).get("restoration", {}).get("sourceOriginEvidenceRef") !=
                f"raw-thread-start:{proof['requestId']}"):
        raise ValueError("restored source origin verifier is not raw-derived")
    if (result.get("scopeBefore") != expected or
            result.get("priorScope") != expected or
            claimed.get("writerThreadId") != thread_id or
            claimed.get("activeTransferId") is not None or
            claimed.get("token") == expected.get("token") or
            result.get("claimRequests") != [{"scopeRef": expected.get("scopeRef"),
                                             "expectedScope": expected}] or
            result.get("claimReceipts") != [{"scope": claimed}] or
            result.get("staleBasisError") != "RESTORE_PRECONDITION_FAILED" or
            result.get("verifyStages") != ["restore-prepare", "restore-resumed"] or
            result.get("restoredState", {}).get("turnCount") != 0 or
            result.get("restoredState", {}).get("transfers") != [] or
            result.get("sessionState", {}).get("turnCount") != 1 or
            result.get("sessionState", {}).get("transfers") != [] or
            result.get("run", {}).get("status") != "completed" or
            result.get("run", {}).get("sourceThreadId") != thread_id):
        raise ValueError("restored source scope, no-transfer state or continuation differs")
    old_turns = previous.get("history", {}).get("thread", {}).get("turns", [])
    before_turns = result.get("historyBefore", {}).get("thread", {}).get("turns", [])
    after_turns = result.get("historyAfter", {}).get("thread", {}).get("turns", [])
    if (len(old_turns) != 1 or before_turns != old_turns or
            len(after_turns) != 2 or after_turns[:1] != old_turns or
            after_turns[1].get("status") != "completed" or
            result.get("historyAfter", {}).get("thread", {}).get("id") != thread_id or
            result.get("nativeSession", {}).get("relativePath") != relative or
            result.get("nativeSession", {}).get("tools") != proof["tools"]):
        raise ValueError("restored source two-turn native history differs")
    prior_bytes = read_regular(prior_sessions / relative, 32 * 1024 * 1024)
    retained = _ordinary_dir(root / "retained/native-sessions")
    after_bytes = read_regular(retained / relative, 32 * 1024 * 1024)
    if (not after_bytes.startswith(prior_bytes) or len(after_bytes) <= len(prior_bytes) or
            _tree_hashes(retained) != post.get("nativeSessions", {}).get("hashes") or
            _tree_hashes(retained) != _read_json(root / "retained/native-sessions-sha256.json")):
        raise ValueError("restored source original native rows were not retained")
    requests = _json_lines(root / "native/app-server/requests.jsonl")
    received = _json_lines(root / "native/app-server/stdout.jsonl")
    resumes = [row for row in requests if row.get("method") == "thread/resume"]
    turns = [row for row in requests if row.get("method") == "turn/start"]
    if (len(resumes) != 1 or len(turns) != 1 or
            resumes[0].get("params", {}).get("threadId") != thread_id or
            resumes[0].get("params", {}).get("excludeTurns") is not True or
            turns[0].get("params", {}).get("threadId") != thread_id or
            any(row.get("method") in {"thread/start", "thread/fork", "thread/archive",
                                      "thread/delete", "thread/unsubscribe"} for row in requests)):
        raise ValueError("restored source raw native resume sequence differs")
    turn_responses = [row for row in received if row.get("id") == turns[0].get("id")
                      and "method" not in row]
    turn_id = turn_responses[0].get("result", {}).get("turn", {}).get("id") if len(turn_responses) == 1 else None
    terminal = [row for row in received if row.get("method") == "turn/completed" and
                row.get("params", {}).get("threadId") == thread_id and
                row.get("params", {}).get("turn", {}).get("id") == turn_id and
                row.get("params", {}).get("turn", {}).get("status") == "completed"]
    if len(terminal) != 1:
        raise ValueError("restored source terminal differs")
    _inspect_source_context_exchange(root, thread_id, turn_id, SOURCE_PROVIDER_REQUESTS)
    database = _open_retained_ledger(root / "retained/carrier.sqlite")
    try:
        scopes = database.execute("SELECT scope_ref,writer_thread_id,active_transfer_id,fence_token FROM scopes").fetchall()
        transfers = database.execute("SELECT transfer_id FROM transfers").fetchall()
    finally:
        database.close()
    if scopes != [(expected.get("scopeRef"), thread_id, None, claimed.get("token"))] or transfers:
        raise ValueError("restored source durable scope or no-transfer ledger differs")
    resource = read_native_resource_records(root / "native", ("codex-session-restore-controller",))["codex-session-restore-controller"]
    close = envelope.get("close", {})
    if (not _record_released(resource, manifest) or
            close.get("nativeExit") != {"code": 0, "signal": None} or
            close.get("connectionClosed") is not True or close.get("stdoutEnded") is not True or
            close.get("closeFailure") is not None or
            post.get("executionFailure") is not None or post.get("cleanupFailure") is not None or
            post.get("priorInputUnchanged") is not True or
            post.get("priorInputInventoryAfter") != restore.get("priorInventoryBefore") or
            post.get("keepSha256After") != manifest.get("keepSha256Before") or
            post.get("sourceHashesAfter") != manifest.get("sourceHashes") or
            post.get("sharedConfigAfter") != manifest.get("sharedConfigBefore") or
            post.get("fixtureThreadStopped") is not True or
            post.get("providerRequests") != SOURCE_PROVIDER_REQUESTS or
            post.get("credentialsObserved") is not False):
        raise ValueError("restored source protected or released poststate differs")
    return {"valid": True, "mode": "source-restore", "threadId": thread_id,
            "turns": 2, "providerRequests": SOURCE_PROVIDER_REQUESTS,
            "claimLimit": "Read-only original source restore inspection; no transfer, model judgment or product acceptance."}


def _inspect_restore_evidence(root: Path, manifest: dict, post: dict,
                              envelope: dict, controller_config: dict):
    controller_done = _read_json(root / "retained/controller-done.json")
    if (manifest.get("schema") != SCHEMA or manifest.get("mode") != "restore"
            or manifest.get("providerRequests") != COLD_PROVIDER_REQUESTS
            or envelope.get("schema") != "accord-codex-session-native-envelope/v1"
            or envelope.get("success") is not True or envelope.get("failure") is not None
            or controller_config.get("schema") != "accord-codex-session-native-config/v2"
            or controller_config.get("mode") != "restore"):
        raise ValueError("cold restore evidence identity or result differs")
    restore = manifest.get("restore", {})
    portable = _ordinary_dir(root / "retained/prior-evidence")
    if (_tree_hashes(portable) != restore.get("portableHashes")
            or _recorded_relative(restore.get("portableRoot", ""), manifest) != ("retained", "prior-evidence")
            or _recorded_relative(controller_config.get("restore", {}).get("priorRoot", ""), manifest)
                != ("retained", "prior-evidence")
            or _recorded_relative(controller_config.get("restore", {}).get("sessionsRoot", ""), manifest)
                != ("home", "sessions")
            or _recorded_relative(controller_config.get("workspace", ""), manifest) != ("workspace",)
            or _recorded_relative(controller_config.get("recorderPath", ""), manifest)
                != ("retained", "carrier.sqlite")):
        raise ValueError("portable prior evidence hashes or controller binding differ")
    prior_manifest = _read_json(portable / "manifest.json")
    prior_post = _read_json(portable / "poststate.json")
    prior_envelope = _read_json(portable / "node-result.json", 16 * 1024 * 1024)
    prior_resource = _read_json(portable / "controller-resource.json")
    prior_result = prior_envelope.get("result", {})
    expected_scope = prior_result.get("adoptedSecond", {}).get("scope")
    transfer_id = prior_result.get("adoptedSecond", {}).get("transferId")
    if (prior_envelope.get("success") is not True or prior_envelope.get("failure") is not None
            or prior_post.get("executionFailure") is not None or prior_post.get("cleanupFailure") is not None
            or not _record_released(prior_resource, prior_manifest)
            or expected_scope != restore.get("expectedScope")
            or transfer_id != restore.get("transferId")
            or expected_scope != controller_config.get("restore", {}).get("expectedScope")):
        raise ValueError("portable prior release or exact adopted scope differs")
    for identity in ("codex", "node"):
        if any(prior_manifest.get("identities", {}).get(identity, {}).get(field)
               != manifest.get("identities", {}).get(identity, {}).get(field)
               for field in ("sha256", "version")):
            raise ValueError("cold executable identity differs from the prior carrier")
    if (controller_done.get("kind") != "done" or controller_done.get("success") is not True
            or controller_done.get("threadIds") != prior_result.get("threadIds")):
        raise ValueError("cold controller completion receipt differs")
    prior_sessions = _ordinary_dir(portable / "native-sessions")
    prior_session_hashes = _tree_hashes(prior_sessions)
    target_session_names = [name for name in prior_session_hashes if name.endswith(
        expected_scope["writerThreadId"] + ".jsonl")]
    if (prior_session_hashes != restore.get("sessionHashes")
            or prior_session_hashes != _read_json(portable / "native-sessions-sha256.json")
            or len(prior_session_hashes) != 3 or len(target_session_names) != 1):
        raise ValueError("portable prior native sessions differ")
    _validate_restore_ledger_sidecars(root / "retained/carrier.sqlite")

    if (not isinstance(manifest.get("sourceHashes"), dict)
            or set(manifest["sourceHashes"]) != set(SOURCE_FILES)):
        raise ValueError("cold frozen execution source set differs")
    snapshot = _ordinary_dir(root / "retained/executed-sources")
    for name, expected in manifest["sourceHashes"].items():
        if _sha(snapshot / name) != expected:
            raise ValueError("cold frozen execution source differs: " + name)
    if (post.get("sourceHashesAfter") != manifest["sourceHashes"]
            or post.get("keepSha256After") != manifest["keepSha256Before"]
            or post.get("sharedConfigAfter") != manifest["sharedConfigBefore"]
            or post.get("codexSha256After") != manifest["identities"]["codex"]["sha256"]
            or post.get("nodeSha256After") != manifest["identities"]["node"]["sha256"]
            or post.get("fixtureThreadStopped") is not True or post.get("cleanupFailure") is not None
            or post.get("executionFailure") is not None or post.get("resourceRecorded") is not True
            or post.get("priorInputUnchanged") is not True
            or post.get("priorInputInventoryAfter") != restore.get("priorInventoryBefore")
            or post.get("nativeSessions", {}).get("preserved") is not True):
        raise ValueError("cold execution source, prior input or protected poststate differs")
    if (not _version_record_ok(root, manifest, "source", "codex")
            or not _version_record_ok(root, manifest, "node", "node")):
        raise ValueError("cold executable version identity differs")
    resources = read_native_resource_records(root / "native", ("codex-session-restore-controller",))
    resource = resources["codex-session-restore-controller"]
    if (resource.get("exitCode") != 0 or resource.get("forced") is not False
            or resource.get("readerStopped") is not True or not _record_released(resource, manifest)):
        raise ValueError("cold Node controller did not exit naturally")
    close = envelope.get("close", {})
    if (close.get("connectionClosed") is not True or close.get("stdoutEnded") is not True
            or close.get("closeFailure") is not None
            or close.get("nativeExit") != {"code": 0, "signal": None}):
        raise ValueError("cold borrowed connection or native stdio close differs")

    result = envelope.get("result", {})
    if (result.get("schema") != "accord-codex-session-native-restore-result/v1"
            or result.get("success") is not True
            or result.get("providerRequestsExpected") != COLD_PROVIDER_REQUESTS
            or result.get("keepSha256") != manifest["keepSha256Before"]
            or result.get("ownerRequests") != [] or result.get("contextRefs") != []
            or result.get("claimLimit") != "Controlled quiescent-controller restore using copied native history and durable ledger; no crash simulation, new thread, handoff, Goal or other host-state migration, model judgment or product acceptance."):
        raise ValueError("cold result or claim boundary differs")
    identities = result.get("identities", {})
    if (identities.get("codex") != manifest["identities"]["codex"]
            or identities.get("node") != manifest["identities"]["node"]):
        raise ValueError("cold executing identities differ")
    writer = expected_scope["writerThreadId"]
    claimed = result.get("scopeAfter", {})
    restored = result.get("restoredState", {})
    final_state = result.get("sessionState", {})
    if (result.get("prior", {}).get("expectedScope") != expected_scope
            or result.get("prior", {}).get("transferId") != transfer_id
            or result.get("scopeBefore") != expected_scope
            or claimed.get("writerThreadId") != writer or claimed.get("activeTransferId") is not None
            or claimed.get("token") == expected_scope["token"]
            or result.get("verifyStages") != ["restore-prepare", "restore-resumed"]
            or restored.get("status") != "ready" or restored.get("sourceThreadId") != writer
            or restored.get("turnCount") != 0 or len(restored.get("transfers", [])) != 1
            or restored["transfers"][0].get("restored") is not True
            or final_state.get("status") != "ready" or final_state.get("sourceThreadId") != writer
            or final_state.get("turnCount") != 1 or len(final_state.get("transfers", [])) != 1):
        raise ValueError("cold scope claim or restored source state differs")
    claims, receipts = result.get("claimRequests"), result.get("claimReceipts")
    if (claims != [{"scopeRef": expected_scope["scopeRef"], "expectedScope": expected_scope}]
            or not isinstance(receipts, list) or len(receipts) != 1
            or receipts[0].get("scope") != claimed):
        raise ValueError("cold claim request or receipt differs")
    for transfer in ("native-transfer-1", "native-transfer-2"):
        before = result.get("recordsBefore", {}).get(transfer, {})
        after = result.get("recordsAfter", {}).get(transfer, {})
        prior_record = prior_result.get("records", {}).get(transfer, {})
        if (before != prior_record or before.get("revision") != after.get("revision")
                or before.get("state") != after.get("state")
                or after.get("lease", {}).get("writerThreadId") != writer
                or after.get("lease", {}).get("token") != claimed.get("token")):
            raise ValueError("cold restore changed settled transfer history")
    database = _open_retained_ledger(root / "retained/carrier.sqlite")
    try:
        scopes = database.execute(
            "SELECT scope_ref,writer_thread_id,active_transfer_id,fence_token FROM scopes").fetchall()
        transfers = database.execute(
            "SELECT transfer_id,scope_ref,revision,state_json,settled FROM transfers ORDER BY transfer_id").fetchall()
    finally:
        database.close()
    if (scopes != [(expected_scope["scopeRef"], writer, None, claimed.get("token"))]
            or len(transfers) != 2):
        raise ValueError("cold durable scope differs from the claimed receipt")
    for transfer_id, scope_ref, revision, state_json, settled in transfers:
        recorded = result["recordsAfter"].get(transfer_id, {})
        if (scope_ref != expected_scope["scopeRef"] or settled != 1
                or revision != recorded.get("revision")
                or json.loads(state_json) != recorded.get("state")):
            raise ValueError("cold durable transfer row differs")
    prior_turns = prior_result.get("histories", {}).get(writer, {}).get("thread", {}).get("turns")
    before_turns = result.get("historyBefore", {}).get("thread", {}).get("turns")
    after_thread = result.get("historyAfter", {}).get("thread", {})
    if (not isinstance(prior_turns, list) or before_turns != prior_turns
            or after_thread.get("id") != writer
            or after_thread.get("path") != result.get("nativeSession", {}).get("path")
            or after_thread.get("turns", [])[:len(prior_turns)] != prior_turns
            or len(after_thread.get("turns", [])) != len(prior_turns) + 1
            or after_thread["turns"][-1].get("status") != "completed"):
        raise ValueError("cold native history preservation or appended turn differs")
    prepare_evidence = result.get("verifyEvidence", {}).get("prepare", {})
    prepare_path = _retained_session_path(root, prepare_evidence.get("threadPath", ""), manifest)
    evidence = result.get("verifyEvidence", {}).get("resumed", {})
    recorded_native_path = result.get("nativeSession", {}).get("path", "")
    native_path = _retained_session_path(root, recorded_native_path, manifest)
    sessions_root = _ordinary_dir(root / "retained/native-sessions")
    actual = evidence.get("actual", {})
    thread_read = evidence.get("threadRead", {})
    if (sessions_root not in prepare_path.parents or prepare_path.resolve(strict=True) != prepare_path
            or prepare_evidence.get("sessionRelativePath") != target_session_names[0]
            or prepare_evidence.get("tools") != ["accord_request_handoff", "accord_inspect_context"]
            or sessions_root not in native_path.parents or native_path.resolve(strict=True) != native_path
            or evidence.get("threadPath") != recorded_native_path
            or evidence.get("sessionRelativePath") != target_session_names[0]
            or evidence.get("tools") != ["accord_request_handoff", "accord_inspect_context"]
            or _recorded_relative(actual.get("cwd", ""), manifest) != ("workspace",)
            or {key: actual.get(key) for key in ("model", "modelProvider", "sandbox", "approvalPolicy")} != {
                "model": "fixture-no-model", "modelProvider": "accord_fixture",
                "sandbox": "readOnly", "approvalPolicy": "never"}
            or _recorded_relative(thread_read.get("cwd", ""), manifest) != ("workspace",)
            or {key: thread_read.get(key) for key in ("model", "modelProvider")} != {
                "model": "fixture-no-model", "modelProvider": "accord_fixture"}):
        raise ValueError("cold restored native path, tools or settings differ")
    session_rows = _json_lines(native_path)
    metas = [row for row in session_rows if row.get("type") == "session_meta"
             and row.get("payload", {}).get("id") == writer]
    contexts = [row.get("payload", {}) for row in session_rows if row.get("type") == "turn_context"]
    expected_tools = prior_result.get("records", {}).get(transfer_id, {}).get(
        "state", {}).get("plan", {}).get("target", {}).get("dynamicTools")
    if (len(metas) != 1 or metas[0].get("payload", {}).get("dynamic_tools") != expected_tools
            or not contexts or _recorded_relative(contexts[-1].get("cwd", ""), manifest) != ("workspace",)
            or contexts[-1].get("model") != "fixture-no-model"
            or contexts[-1].get("approval_policy") != "never"
            or contexts[-1].get("sandbox_policy", {}).get("type") != "read-only"):
        raise ValueError("cold final persistent session metadata differs")
    retained_sessions = _tree_hashes(sessions_root)
    if (retained_sessions != post.get("nativeSessions", {}).get("hashes")
            or len(retained_sessions) != 3):
        raise ValueError("cold final native session retention differs")

    requests = _json_lines(root / "native/app-server/requests.jsonl")
    received = _json_lines(root / "native/app-server/stdout.jsonl")
    methods = [row.get("method") for row in requests if isinstance(row.get("method"), str)]
    resumes = [row for row in requests if row.get("method") == "thread/resume"]
    starts = [row for row in requests if row.get("method") == "thread/start"]
    turns = [row for row in requests if row.get("method") == "turn/start"]
    resume_params = resumes[0].get("params", {}) if len(resumes) == 1 else {}
    if (len(resumes) != 1 or starts or len(turns) != 1 or methods.count("initialize") != 1
            or _recorded_relative(resume_params.get("cwd", ""), manifest) != ("workspace",)
            or {key: resume_params.get(key) for key in ("threadId", "excludeTurns", "sandbox",
                "approvalPolicy", "model", "modelProvider")} != {"threadId": writer,
                "excludeTurns": True, "sandbox": "read-only", "approvalPolicy": "never",
                "model": "fixture-no-model", "modelProvider": "accord_fixture"}
            or turns[0].get("params", {}).get("threadId") != writer
            or any(method in {"thread/start", "thread/unsubscribe", "thread/archive",
                              "thread/delete", "thread/fork"} for method in methods)):
        raise ValueError("cold native resume/start sequence differs")
    client_requests = [row for row in requests if isinstance(row.get("method"), str) and "id" in row]
    raw_responses = [row for row in received if "id" in row and "method" not in row]
    response_by_id = {}
    for row in raw_responses:
        response_by_id.setdefault(_rpc_id(row["id"]), []).append(row)
    for request in client_requests:
        matched = response_by_id.get(_rpc_id(request["id"]), [])
        if len(matched) != 1 or "result" not in matched[0] or "error" in matched[0]:
            raise ValueError("cold native RPC response is missing, duplicated or failed")
    resume_receipt = response_by_id[_rpc_id(resumes[0]["id"])][0]["result"]
    if (_recorded_relative(resume_receipt.get("cwd", ""), manifest) != ("workspace",)
            or {key: resume_receipt.get(key) for key in ("model", "modelProvider", "approvalPolicy")} != {
                "model": "fixture-no-model", "modelProvider": "accord_fixture",
                "approvalPolicy": "never"}
            or resume_receipt.get("sandbox", {}).get("type") != "readOnly"
            or actual != {"cwd": resume_receipt.get("cwd"), "model": resume_receipt.get("model"),
                "modelProvider": resume_receipt.get("modelProvider"), "sandbox": "readOnly",
                "approvalPolicy": resume_receipt.get("approvalPolicy")}):
        raise ValueError("cold native resume receipt settings differ")
    turn_id = response_by_id[_rpc_id(turns[0]["id"])][0]["result"].get("turn", {}).get("id")
    terminals = [row for row in received if row.get("method") == "turn/completed"
                 and row.get("params", {}).get("threadId") == writer
                 and row.get("params", {}).get("turn", {}).get("id") == turn_id]
    if len(terminals) != 1 or terminals[0]["params"]["turn"].get("status") != "completed":
        raise ValueError("cold turn terminal differs")
    tool_requests = [row for row in received if row.get("method") == "item/tool/call"]
    replies = {_rpc_id(row["id"]): row for row in requests if "method" not in row and "id" in row}
    if (len(tool_requests) != 1 or tool_requests[0].get("params", {}).get("tool") != "accord_inspect_context"
            or tool_requests[0].get("params", {}).get("threadId") != writer
            or tool_requests[0].get("params", {}).get("turnId") != turn_id
            or replies.get(_rpc_id(tool_requests[0]["id"]), {}).get("result", {}).get("success") is not True):
        raise ValueError("cold context tool request/reply identity differs")
    provider_rows = _json_lines(root / "retained/provider-requests.jsonl")
    provider_responses = [_read_json(root / f"retained/provider-response-{ordinal}.json")
                          for ordinal in range(1, COLD_PROVIDER_REQUESTS + 1)]
    if (len(provider_rows) != COLD_PROVIDER_REQUESTS
            or post.get("providerRequests") != COLD_PROVIDER_REQUESTS
            or post.get("credentialsObserved") is not False
            or _provider_tool(provider_responses[0]["response"]["output"][0]) != "accord_inspect_context"
            or _provider_tool(provider_responses[1]["response"]["output"][0]) is not None
            or any(row.get("transportStatus") != "completed" for row in provider_responses)):
        raise ValueError("cold fixed provider receipts differ")
    second_input = provider_rows[1].get("request", {}).get("input", [])
    provider_calls = [row for row in second_input if _provider_tool(row) == "accord_inspect_context"]
    provider_outputs = [row for row in second_input
                        if row.get("type") in {"function_call_output", "custom_tool_call_output"}]
    if (len(provider_calls) != 1 or len(provider_outputs) != 1
            or provider_calls[0].get("call_id") != provider_outputs[0].get("call_id")):
        raise ValueError("cold provider tool call/output identity differs")
    try:
        provider_context = json.loads(provider_outputs[0].get("output", ""))
    except (TypeError, json.JSONDecodeError):
        raise ValueError("cold provider context output is not structured") from None
    conditions = provider_context.get("observation", {}).get("conditions", {})
    if (provider_context.get("schema") != "yiyuan-accord-native-context-reply/v1"
            or conditions.get("threadId") != writer or conditions.get("turnId") != turn_id):
        raise ValueError("cold provider context source identity differs")
    if [p.name for p in (root / "workspace").iterdir()] != ["keep.txt"]:
        raise ValueError("cold workspace contains an unexpected output")
    return {"valid": True, "mode": "restore", "providerRequests": COLD_PROVIDER_REQUESTS,
            "threadId": writer, "transfers": 2,
            "claimLimit": "Read-only cold artifact inspection; no crash, Goal or other host-state migration, model or product acceptance claim."}


def inspect_evidence(value):
    """Read-only independent inspection; never repairs or creates evidence."""
    root = _ordinary_dir(Path(value).absolute())
    manifest = _read_json(root / "manifest.json")
    post = _read_json(root / "poststate.json")
    envelope = _read_json(root / "retained/node-result.json", 16 * 1024 * 1024)
    controller_config = _read_json(root / "retained/controller-config.json")
    mode = manifest.get("mode", "hot")
    if mode == "source-start":
        return _inspect_source_start(root, manifest, post, envelope, controller_config)
    if mode == "source-restore":
        return _inspect_source_restore(root, manifest, post, envelope, controller_config)
    if mode == "restore":
        return _inspect_restore_evidence(root, manifest, post, envelope, controller_config)
    if mode != "hot":
        raise ValueError("unknown native session evidence mode")
    if (manifest.get("schema") != SCHEMA or not isinstance(manifest.get("evidence"), str)
            or manifest.get("providerRequests") != PROVIDER_REQUESTS
            or envelope.get("schema") != "accord-codex-session-native-envelope/v1"
            or envelope.get("success") is not True or envelope.get("failure") is not None):
        raise ValueError("native session evidence identity or result differs")
    argv = controller_config.get("argv")
    if (controller_config.get("schema") != "accord-codex-session-native-config/v1"
            or not isinstance(argv, list)):
        raise ValueError("frozen native controller config differs")
    overrides = [argv[index + 1] for index, value in enumerate(argv[:-1]) if value == "-c"]
    final_overrides = {}
    for value in overrides:
        key = value.split("=", 1)[0]
        final_overrides[key] = value
    if (final_overrides.get("features.plugins") != "features.plugins=false"
            or final_overrides.get("features.hooks") != "features.hooks=false"
            or final_overrides.get("features.apps") != "features.apps=false"
            or final_overrides.get("web_search") != 'web_search="disabled"'
            or final_overrides.get("model_provider") != 'model_provider="accord_fixture"'):
        raise ValueError("native plugins, hooks, apps, web or provider isolation differs")
    if (not isinstance(manifest.get("sourceHashes"), dict)
            or set(manifest["sourceHashes"]) != set(SOURCE_FILES)):
        raise ValueError("frozen execution source set differs")
    snapshot = _ordinary_dir(root / "retained/executed-sources")
    for name, expected in manifest["sourceHashes"].items():
        if _sha(snapshot / name) != expected:
            raise ValueError("frozen execution source differs: " + name)
    if (post.get("sourceHashesAfter") != manifest["sourceHashes"]
            or post.get("keepSha256After") != manifest["keepSha256Before"]
            or post.get("sharedConfigAfter") != manifest["sharedConfigBefore"]
            or post.get("codexSha256After") != manifest["identities"]["codex"]["sha256"]
            or post.get("nodeSha256After") != manifest["identities"]["node"]["sha256"]
            or post.get("fixtureThreadStopped") is not True or post.get("cleanupFailure") is not None
            or post.get("executionFailure") is not None or post.get("resourceRecorded") is not True
            or post.get("nativeSessions", {}).get("preserved") is not True):
        raise ValueError("execution-time source, protected input or shared config receipt differs")
    if (not _version_record_ok(root, manifest, "source", "codex")
            or not _version_record_ok(root, manifest, "node", "node")):
        raise ValueError("bounded executable version identity differs")

    resources = read_native_resource_records(root / "native", ("codex-session-controller",))
    resource = resources["codex-session-controller"]
    if (resource.get("exitCode") != 0 or resource.get("forced") is not False
            or resource.get("readerStopped") is not True or not _record_released(resource, manifest)):
        raise ValueError("outer Node or owned process group did not exit naturally")
    close = envelope.get("close", {})
    if (close.get("connectionClosed") is not True or close.get("stdoutEnded") is not True
            or close.get("closeFailure") is not None or close.get("nativeExit") != {"code": 0, "signal": None}):
        raise ValueError("borrowed connection or native stdio close evidence differs")

    result = envelope["result"]
    identities = result.get("identities", {})
    if (identities.get("codex") != manifest["identities"]["codex"]
            or identities.get("node", {}).get("path") != manifest["identities"]["node"]["path"]
            or identities.get("node", {}).get("sha256") != manifest["identities"]["node"]["sha256"]
            or identities.get("node", {}).get("version") != manifest["identities"]["node"]["version"]):
        raise ValueError("executing Node or Codex identity differs")
    thread_ids = result.get("threadIds", {})
    ordered_ids = [thread_ids.get(name) for name in ("source", "target1", "target2")]
    if any(not isinstance(value, str) or not value for value in ordered_ids) or len(set(ordered_ids)) != 3:
        raise ValueError("actual native thread identities are incomplete")
    if (result.get("first", {}).get("target", {}).get("threadId") != ordered_ids[1]
            or result.get("second", {}).get("target", {}).get("threadId") != ordered_ids[2]
            or result.get("adoptedFirst", {}).get("sourceThreadId") != ordered_ids[1]
            or result.get("adoptedSecond", {}).get("sourceThreadId") != ordered_ids[2]
            or result.get("sessionState", {}).get("status") != "ready"
            or result["sessionState"].get("sourceThreadId") != ordered_ids[2]
            or [row.get("settled") for row in result["sessionState"].get("transfers", [])] != [True, True]):
        raise ValueError("two-transfer hot adoption result differs")
    expected_stages = [stage for _ in range(2) for stage in
        ("prepare", "quiesced", "target-created", "accepted", "continue", "continued", "release", "adopt-target")]
    plans = result.get("plans")
    if (result.get("verifyStages") != expected_stages or result.get("ownerRequests") != []
            or result.get("providerRequestsExpected") != PROVIDER_REQUESTS
            or result.get("keepSha256") != manifest["keepSha256Before"]
            or result.get("claimLimit") != "Fixed localhost provider and evidence-based test verifier only; no model judgment, shared Desktop control, cold recovery or product acceptance."
            or not isinstance(plans, list) or len(plans) != 2):
        raise ValueError("verifier, owner-request or bounded result claims differ")
    for ordinal, plan in enumerate(plans, 1):
        if (plan.get("transferId") != f"native-transfer-{ordinal}"
                or plan.get("authorityRef") != f"native-authority-{ordinal}"
                or plan.get("stateRef") != f"native-state-{ordinal}"
                or plan.get("source", {}).get("threadId") != ordered_ids[ordinal - 1]):
            raise ValueError("handoff plan references or source chain differ")
    if result.get("contextRefs") != [
            {"transferId": "native-transfer-1", "writerThreadId": ordered_ids[0]},
            {"transferId": "native-transfer-2", "writerThreadId": ordered_ids[1]}]:
        raise ValueError("current writer reference chain differs")
    histories = result.get("histories", {})
    for thread_id, count in zip(ordered_ids, TURN_COUNTS):
        thread = histories.get(thread_id, {}).get("thread", {})
        turns = thread.get("turns")
        if (thread.get("id") != thread_id or not isinstance(turns, list) or len(turns) != count
                or any(turn.get("status") != "completed" for turn in turns)):
            raise ValueError("native thread history differs")
    sessions_root = _ordinary_dir(root / "retained/native-sessions")
    retained_session_hashes = _tree_hashes(sessions_root)
    if (retained_session_hashes != _read_json(root / "retained/native-sessions-sha256.json")
            or post["nativeSessions"].get("hashes") != retained_session_hashes):
        raise ValueError("retained native session hash inventory differs")
    session_meta_ids = set()
    for name in retained_session_hashes:
        if not name.endswith(".jsonl"):
            continue
        for line in read_regular(sessions_root / name, 32 * 1024 * 1024).decode("utf-8").splitlines():
            row = json.loads(line)
            if row.get("type") == "session_meta" and isinstance(row.get("payload", {}).get("id"), str):
                session_meta_ids.add(row["payload"]["id"])
    if session_meta_ids != set(ordered_ids):
        raise ValueError("retained raw native session identities differ")

    requests = _json_lines(root / "native/app-server/requests.jsonl")
    received = _json_lines(root / "native/app-server/stdout.jsonl")
    client_requests = [row for row in requests if isinstance(row.get("method"), str) and "id" in row]
    raw_responses = [row for row in received if "id" in row and "method" not in row]
    response_by_id = {}
    for row in raw_responses:
        response_by_id.setdefault(_rpc_id(row["id"]), []).append(row)
    request_ids = [_rpc_id(row["id"]) for row in client_requests]
    if (len(request_ids) != len(set(request_ids)) or len(raw_responses) != len(client_requests)
            or set(response_by_id) != set(request_ids)):
        raise ValueError("native RPC response identity set differs")
    for request in client_requests:
        matched = response_by_id.get(_rpc_id(request["id"]), [])
        if len(matched) != 1 or "result" not in matched[0] or "error" in matched[0]:
            raise ValueError("native client RPC response is missing, duplicated or failed")
    methods = [row.get("method") for row in requests if isinstance(row.get("method"), str)]
    starts = [row for row in requests if row.get("method") == "thread/start"]
    turns = [row for row in requests if row.get("method") == "turn/start"]
    unsubscribes = [row.get("params", {}).get("threadId") for row in requests
                    if row.get("method") == "thread/unsubscribe"]
    initializes = [row for row in requests if row.get("method") == "initialize"]
    if (len(starts) != 3 or len(turns) != 6 or unsubscribes != ordered_ids[:2]
            or len(initializes) != 1
            or initializes[0].get("params", {}).get("capabilities", {}).get("experimentalApi") is not True
            or any(method in {"thread/archive", "thread/delete", "thread/resume", "thread/fork"} for method in methods)):
        raise ValueError("native RPC sequence differs")
    start_ids = [response_by_id[_rpc_id(row["id"])][0]["result"].get("thread", {}).get("id")
                 for row in starts]
    if start_ids != ordered_ids:
        raise ValueError("thread/start raw receipts differ from the actual carrier identities")
    turn_receipts = []
    if sum(event.get("method") == "turn/completed" for event in received) != len(turns):
        raise ValueError("native terminal count differs")
    for row in turns:
        turn_id = response_by_id[_rpc_id(row["id"])][0]["result"].get("turn", {}).get("id")
        thread_id = row.get("params", {}).get("threadId")
        terminals = [event for event in received if event.get("method") == "turn/completed"
                     and event.get("params", {}).get("threadId") == thread_id
                     and event.get("params", {}).get("turn", {}).get("id") == turn_id]
        if not isinstance(turn_id, str) or len(terminals) != 1 or terminals[0]["params"]["turn"].get("status") != "completed":
            raise ValueError("turn/start raw receipt or exact terminal differs")
        turn_receipts.append((thread_id, turn_id))
    history_reads = [row for row in requests if row.get("method") == "thread/read"
                     and row.get("params", {}).get("includeTurns") is True]
    if len(history_reads) != 3:
        raise ValueError("final native history read set differs")
    for row in history_reads:
        thread_id = row["params"].get("threadId")
        raw_history = response_by_id[_rpc_id(row["id"])][0]["result"]
        if thread_id not in histories or raw_history != histories[thread_id]:
            raise ValueError("retained native history is not the exact raw RPC result")
    tool_requests = [row for row in received if row.get("method") == "item/tool/call"]
    if len(tool_requests) != 4:
        raise ValueError("native dynamic tool request count differs")
    tool_by_id = {_rpc_id(row["id"]): row for row in tool_requests}
    reply_rows = [row for row in requests if "method" not in row and "id" in row]
    replies = {_rpc_id(row["id"]): row for row in reply_rows}
    if (len(tool_by_id) != len(tool_requests) or len(replies) != len(reply_rows)
            or set(replies) != set(tool_by_id)):
        raise ValueError("native dynamic tool response set differs")
    context_rows = [row for row in tool_requests if row.get("params", {}).get("tool") == "accord_inspect_context"]
    proposal_rows = [row for row in tool_requests if row.get("params", {}).get("tool") == "accord_request_handoff"]
    if len(context_rows) != 1 or len(proposal_rows) != 3:
        raise ValueError("native context/proposal request sequence differs")
    context_request = context_rows[0]
    nested = [row for row in proposal_rows if row.get("params", {}).get("threadId") == ordered_ids[1]
              and row.get("params", {}).get("turnId") != result["second"].get("turnId")]
    if (context_request.get("params", {}).get("threadId") != ordered_ids[1]
            or replies[_rpc_id(context_request["id"])].get("result", {}).get("success") is not True
            or len(nested) != 1 or replies[_rpc_id(nested[0]["id"])].get("result", {}).get("success") is not False):
        raise ValueError("target intake context or nested refusal differs")
    nested_text = replies[_rpc_id(nested[0]["id"])]["result"]["contentItems"][0]["text"]
    if json.loads(nested_text).get("code") != "TRANSFER_IN_PROGRESS":
        raise ValueError("nested handoff failure code differs")

    provider_rows = _json_lines(root / "retained/provider-requests.jsonl")
    responses = [_read_json(root / f"retained/provider-response-{ordinal}.json")
                 for ordinal in range(1, PROVIDER_REQUESTS + 1)]
    if (len(provider_rows) != PROVIDER_REQUESTS
            or any(row.get("ordinal") != ordinal for ordinal, row in enumerate(provider_rows, 1))
            or post.get("providerRequests") != PROVIDER_REQUESTS
            or post.get("credentialsObserved") is not False
            or any(row.get("ordinal") != ordinal or row.get("transportStatus") != "completed"
                   for ordinal, row in enumerate(responses, 1))):
        raise ValueError("fixed localhost provider receipts differ")
    observed_tools = {ordinal: _provider_tool(row["response"]["output"][0])
                      for ordinal, row in enumerate(responses, 1) if _provider_tool(row["response"]["output"][0])}
    if observed_tools != TOOL_SEQUENCE:
        raise ValueError("fixed provider tool sequence differs")

    database = _open_retained_ledger(root / "retained/carrier.sqlite")
    try:
        scopes = database.execute("SELECT scope_ref,writer_thread_id,active_transfer_id FROM scopes").fetchall()
        transfers = database.execute("SELECT transfer_id,scope_ref,revision,state_json,settled FROM transfers ORDER BY transfer_id").fetchall()
    finally:
        database.close()
    if scopes != [("native-session-scope", ordered_ids[2], None)] or len(transfers) != 2:
        raise ValueError("durable final scope differs")
    for ordinal, row in enumerate(transfers, 1):
        transfer_id, scope_ref, revision, state_json, settled = row
        state = json.loads(state_json)
        node_record = result.get("records", {}).get(transfer_id, {})
        if (transfer_id != f"native-transfer-{ordinal}" or scope_ref != "native-session-scope"
                or not isinstance(revision, int) or revision <= 0 or settled != 1
                or node_record.get("revision") != revision or node_record.get("state") != state
                or state.get("phase") != "source-subscription-released"
                or state.get("pendingEffect") is not None
                or state.get("source", {}).get("threadId") != ordered_ids[ordinal - 1]
                or state.get("target", {}).get("threadId") != ordered_ids[ordinal]):
            raise ValueError("durable transfer ledger differs")
    return {"valid": True, "providerRequests": PROVIDER_REQUESTS,
            "threadIds": thread_ids, "transfers": 2,
            "claimLimit": "Read-only artifact inspection; execution-time external identities rely on retained before/after receipts."}


def native_integration(codex_value, evidence_value, restore_from=None,
                       source_start=False, restore_source_from=None):
    if source_start and (restore_from is not None or restore_source_from is not None):
        raise ValueError("source start cannot restore prior evidence")
    if restore_from is not None and restore_source_from is not None:
        raise ValueError("select one restore evidence mode")
    source_restore = restore_source_from is not None
    root, prior = _restore_roots(evidence_value, restore_source_from or restore_from)
    restore_mode = prior is not None
    codex = _regular_file(Path(codex_value).resolve(strict=True))
    if os.name == "nt" and codex.suffix.lower() != ".exe":
        raise ValueError("existing native Codex executable required")
    node_name = shutil.which("node")
    if not node_name:
        raise ValueError("existing Node executable required")
    node = _regular_file(Path(node_name).resolve(strict=True))
    root.mkdir()
    for name in ("home", "workspace", "state", "temp", "native", "retained"):
        (root / name).mkdir()
    keep = root / "workspace/keep.txt"
    restore_inputs = _prepare_restore_inputs(prior, root, source_restore) if restore_mode else None
    if not restore_mode:
        keep.write_bytes(b"Preserve this fixed native session original.\n")
    keep_hash = digest(keep)
    source_hashes = _source_hashes()
    snapshot = _snapshot_sources(root, source_hashes)
    codex_hash, node_hash = digest(codex), digest(node)
    shared_before = _shared_config_observation()
    provider_requests = (COLD_PROVIDER_REQUESTS if restore_mode else
                         SOURCE_PROVIDER_REQUESTS if source_start else PROVIDER_REQUESTS)
    manifest = {"schema": SCHEMA, "evidence": str(root), "codex": str(codex), "node": str(node),
        "ownedRoots": {name: str(root / name) for name in ("home", "workspace", "state", "temp")},
        "limits": {"requestSeconds": 30, "recoverySeconds": 15,
                   "providerRequestBytes": 2 * 1024 * 1024, "providerRequests": provider_requests},
        "resourceController": "windows-job-object" if os.name == "nt" else "posix-session-process-group",
        "providerRequests": provider_requests, "sourceHashes": source_hashes,
        "sourceSnapshot": str(snapshot), "keepSha256Before": keep_hash,
        "sharedConfigBefore": shared_before,
        "environmentBoundary": ("Isolated CODEX_HOME/SQLITE/state/temp; Windows process essentials may retain USERPROFILE/APPDATA."
                                if os.name == "nt" else "Isolated CODEX_HOME/HOME/XDG/SQLITE/state/temp."),
        "claimLimit": ("Controlled restore from copied quiescent native evidence; no crash simulation, real model, new thread, handoff, Goal or other host-state migration, or product acceptance."
                       if restore_mode else
                       "Fixed localhost responses and test verifier; no real model, shared Desktop control, cold recovery or product acceptance.")}
    if restore_mode or source_start:
        manifest["mode"] = ("source-restore" if source_restore else
                            "restore" if restore_mode else "source-start")
    if restore_mode:
        manifest["restore"] = restore_inputs
    env = _owned_environment(manifest)
    version = _codex_version(codex, manifest, "source", env)
    node_version = _codex_version(node, manifest, "node", env)
    if digest(codex) != codex_hash or digest(node) != node_hash:
        raise ValueError("bound executable changed during version freeze")
    manifest["identities"] = {"codex": {"path": str(codex), "sha256": codex_hash, "version": version},
                              "node": {"path": str(node), "sha256": node_hash, "version": node_version}}
    save(root / "manifest.json", manifest)
    fixture = _Fixture(manifest, (source_provider_item if source_restore or source_start else
                                  cold_provider_item if restore_mode else fixed_provider_item))
    app = None
    resource = None
    fixture_stopped = False
    execution_error = None
    deadline = time.monotonic() + 180
    try:
        native_argv = _argv(manifest, fixture, ("-c", "features.plugins=false", "-c", "features.hooks=false"))
        config = {"schema": ("accord-codex-session-native-config/v2" if restore_mode else
                             "accord-codex-session-native-config/v1"), "evidence": str(root),
            "argv": native_argv, "workspace": str(root / "workspace"),
            "nativeLogRoot": str(root / "native/app-server"),
            "recorderPath": str(root / "retained/carrier.sqlite"),
            "resultPath": str(root / "retained/node-result.json"),
            "binding": {"connectionId": ("accord-native-source-restore-controller" if source_restore else
                                           "accord-native-session-restore-controller" if restore_mode else
                                           "accord-native-source-start-controller" if source_start else
                                           "accord-native-session-controller"), "hostVersion": version},
            "keepPath": str(keep), "keepSha256": keep_hash,
            "overallDeadlineMs": int(time.time() * 1000) + 165000,
            "identities": manifest["identities"]}
        if restore_mode:
            config.update(mode="source-restore" if source_restore else "restore", restore={
                "priorRoot": restore_inputs["portableRoot"],
                "sessionsRoot": str(root / "home/sessions"),
                "scopeRef": restore_inputs["scopeRef"],
                **({"source": restore_inputs["source"],
                    "portableHashes": restore_inputs["portableHashes"]} if source_restore else
                   {"transferId": restore_inputs["transferId"]}),
                "expectedScope": restore_inputs["expectedScope"]})
        elif source_start:
            config["mode"] = "source-start"
        save(root / "retained/controller-config.json", config)
        caller = snapshot / "tests/product/codex_session_native.cjs"
        resource_name = "codex-session-restore-controller" if restore_mode else "codex-session-controller"
        app = _App(manifest, resource_name, [str(node), str(caller)], env, deadline)
        app._send(config)
        done = app._receive(deadline)
        save(root / "retained/controller-done.json", done)
        resource = app.close()
        app = None
        if (done.get("kind") != "done" or done.get("success") is not True
                or resource.get("exitCode") != 0 or resource.get("forced") is not False
                or resource.get("readerStopped") is not True or not _record_released(resource, manifest)):
            raise RuntimeError("native Node controller did not complete and release naturally")
    except BaseException as error:
        execution_error = error
    finally:
        cleanup_error = None
        native_sessions = {"preserved": False, "reason": "writer-release-unconfirmed"}
        if app is not None:
            try:
                resource = app.close()
            except BaseException as error:
                cleanup_error = error
        try:
            native_sessions = _preserve_native_sessions(root, resource, manifest)
        except BaseException as error:
            cleanup_error = cleanup_error or error
        try:
            fixture.close()
        except BaseException as error:
            cleanup_error = cleanup_error or error
        fixture_stopped = not fixture.thread.is_alive()
        post = None
        try:
            prior_after = (_input_inventory(Path(restore_inputs["priorPath"])) if restore_mode else None)
            post = {"providerRequests": len(fixture.requests), "credentialsObserved": fixture.auth_seen,
                "fixtureThreadStopped": fixture_stopped, "keepSha256After": digest(keep),
                "sourceHashesAfter": _source_hashes(), "sharedConfigAfter": _shared_config_observation(),
                "codexSha256After": digest(codex), "nodeSha256After": digest(node),
                "resourceRecorded": resource is not None, "cleanupFailure": (
                    {"type": type(cleanup_error).__name__, "message": str(cleanup_error)} if cleanup_error else None),
                "executionFailure": ({"type": type(execution_error).__name__,
                    "message": str(execution_error)} if execution_error else None),
                "nativeSessions": native_sessions,
                **({"priorInputInventoryAfter": prior_after,
                    "priorInputUnchanged": prior_after == restore_inputs["priorInventoryBefore"]}
                   if restore_mode else {})}
            save(root / "poststate.json", post)
        except BaseException as error:
            cleanup_error = cleanup_error or error
    if execution_error is not None:
        raise execution_error
    if cleanup_error is not None:
        raise RuntimeError("native integration cleanup failed; evidence retained") from cleanup_error
    result = inspect_evidence(root)
    print(json.dumps({"executed": True, "modelCalls": 0, "providerRequests": provider_requests,
                      "evidence": str(root), "inspection": result}, ensure_ascii=False))
    return result


class CodexSessionNativeOfflineTests(unittest.TestCase):
    def test_resumed_context_check_distinguishes_prior_and_current_tool_pairs(self):
        call = {"type": "function_call", "name": "accord_inspect_context", "call_id": "same-id"}
        def output(turn):
            return {"type": "function_call_output", "call_id": "same-id", "output": json.dumps({
                "schema": "yiyuan-accord-native-context-reply/v1", "observation": {
                    "conditions": {"threadId": "source", "turnId": turn}}})}
        prior = [call, output("old-turn")]
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "native/app-server").mkdir(parents=True)
            (root / "retained").mkdir()
            (root / "native/app-server/stdout.jsonl").write_text(json.dumps({"id": 1, "method": "item/tool/call",
                 "params": {"tool": "accord_inspect_context", "threadId": "source",
                            "turnId": "current-turn", "callId": "same-id"}}), encoding="utf-8")
            (root / "native/app-server/requests.jsonl").write_text(
                json.dumps({"id": 1, "result": {"success": True}}), encoding="utf-8")
            for n, item in enumerate((call, {"type": "message"}), 1):
                save(root / f"retained/provider-response-{n}.json", {
                    "transportStatus": "completed", "response": {"output": [item]}})
            path = root / "retained/provider-requests.jsonl"
            for current_turn in ("current-turn", "old-turn"):
                rows = [{"request": {"input": prior}},
                        {"request": {"input": prior + [call, output(current_turn)]}}]
                path.write_text("\n".join(json.dumps(row) for row in rows), encoding="utf-8")
                if current_turn == "current-turn":
                    _inspect_source_context_exchange(root, "source", current_turn, 2)
                else:
                    with self.assertRaisesRegex(ValueError, "context identity"):
                        _inspect_source_context_exchange(root, "source", "current-turn", 2)

    def test_raw_source_origin_requires_ack_and_persisted_tools(self):
        source = {"threadId": "known-source", "cwd": "C:/known"}
        tools = [{"name": "accord_request_handoff"}, {"name": "accord_inspect_context"}]
        start = {"id": 7, "method": "thread/start", "params": {"cwd": source["cwd"],
            "model": "fixture-no-model", "modelProvider": "accord_fixture",
            "dynamicTools": tools}}
        reply = {"id": 7, "result": {"thread": {"id": source["threadId"],
                                              "ephemeral": False}}}
        with tempfile.TemporaryDirectory() as directory:
            session = Path(directory) / "known-source.jsonl"
            session.write_text(json.dumps({"type": "session_meta", "payload": {
                "id": source["threadId"], "dynamic_tools": tools}}) + "\n")
            proof = _raw_source_origin([start], [reply], source, session)
            self.assertEqual(proof["requestId"], 7)
            with self.assertRaisesRegex(ValueError, "acknowledgement"):
                _raw_source_origin([start], [], source, session)
            with self.assertRaisesRegex(ValueError, "acknowledgement"):
                _raw_source_origin([start], [{"id": 7, "result": {"thread": {
                    "id": "other", "ephemeral": False}}}], source, session)
            session.write_text(json.dumps({"type": "session_meta", "payload": {
                "id": source["threadId"], "dynamic_tools": tools[:1]}}) + "\n")
            with self.assertRaisesRegex(ValueError, "dynamic tools"):
                _raw_source_origin([start], [reply], source, session)

    def test_source_restore_cli_modes_cannot_be_combined(self):
        with self.assertRaisesRegex(ValueError, "select one restore"):
            native_integration("unused", "unused", restore_from="old",
                               restore_source_from="source")
        with self.assertRaisesRegex(ValueError, "source start cannot restore"):
            native_integration("unused", "unused", source_start=True,
                               restore_source_from="source")

    def test_retained_ledger_read_creates_no_sidecars_and_rejects_uncheckpointed_data(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / 'retained.sqlite'
            database = sqlite3.connect(path)
            database.execute('PRAGMA journal_mode=WAL')
            database.execute('CREATE TABLE original(value TEXT)')
            database.execute("INSERT INTO original VALUES ('preserve')")
            database.commit()
            database.close()
            before = {p.name: p.read_bytes() for p in root.iterdir()}
            readonly = _open_retained_ledger(path)
            try:
                self.assertEqual(readonly.execute('SELECT value FROM original').fetchone(), ('preserve',))
            finally:
                readonly.close()
            self.assertEqual({p.name: p.read_bytes() for p in root.iterdir()}, before)
            sidecar = path.with_name(path.name + '-wal')
            sidecar.write_bytes(b'unresolved journal evidence')
            with self.assertRaisesRegex(ValueError, 'uncheckpointed'):
                _open_retained_ledger(path)
            self.assertEqual(sidecar.read_bytes(), b'unresolved journal evidence')

    def test_restore_ledger_ignores_ordinary_shm_but_rejects_pending_wal(self):
        with tempfile.TemporaryDirectory() as directory:
            # Runner temp roots can use Windows short names or macOS /var aliases.
            path = Path(directory).resolve(strict=True) / "carrier.sqlite"
            database = sqlite3.connect(path)
            database.execute("CREATE TABLE original(value TEXT)")
            database.commit()
            database.close()
            path.with_name(path.name + "-shm").write_bytes(b"transient shared memory metadata")
            self.assertEqual(_validate_restore_ledger_sidecars(path), path)
            path.with_name(path.name + "-wal").write_bytes(b"pending transaction")
            with self.assertRaisesRegex(ValueError, "uncheckpointed"):
                _validate_restore_ledger_sidecars(path)

    def test_fixed_provider_items_support_direct_and_code_mode_shapes(self):
        direct = {"tools": [{"type": "function", "name": "accord_request_handoff"}]}
        self.assertEqual(fixed_provider_item(direct, 1)["type"], "function_call")
        context = {"tools": [{"type": "function", "name": "accord_inspect_context"}]}
        self.assertEqual(fixed_provider_item(context, 3)["name"], "accord_inspect_context")
        wrapper = {"input": [{"type": "additional_tools", "tools": [{"type": "namespace",
            "name": "functions", "tools": [{"name": "exec",
                "description": "accord_request_handoff accord_inspect_context"}]}]}]}
        self.assertEqual(fixed_provider_item(wrapper, 4)["type"], "custom_tool_call")
        self.assertIsNone(fixed_provider_item({}, 2))

    def test_cold_provider_uses_one_context_call_then_final(self):
        direct = {"tools": [{"type": "function", "name": "accord_inspect_context"}]}
        item = cold_provider_item(direct, 1)
        self.assertEqual((_provider_tool(item), item["type"]),
                         ("accord_inspect_context", "function_call"))
        self.assertIsNone(cold_provider_item({}, 2))
        with self.assertRaisesRegex(ValueError, "ordinal"):
            cold_provider_item({}, 3)

    def test_fresh_evidence_root_rejects_reuse_before_execution(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(ValueError, "fresh root"):
                _fresh_root(directory)

    def test_restore_root_nesting_is_rejected_before_creation(self):
        with tempfile.TemporaryDirectory() as directory:
            prior = Path(directory).resolve(strict=True) / "prior"
            prior.mkdir()
            (prior / "keep.txt").write_bytes(b"preserve")
            evidence = prior / "new-evidence"
            before = _input_inventory(prior)
            with self.assertRaisesRegex(ValueError, "must not be nested"):
                _restore_roots(evidence, prior)
            self.assertFalse(evidence.exists())
            self.assertEqual(_input_inventory(prior), before)

    def test_recorded_native_paths_are_portable_locators(self):
        windows = {"resourceController": "windows-job-object", "evidence": r"C:\old\evidence"}
        self.assertEqual(_recorded_relative(r"C:\old\evidence\home\sessions\one.jsonl", windows),
                         ("home", "sessions", "one.jsonl"))
        posix = {"resourceController": "posix-session-process-group", "evidence": "/old/evidence"}
        self.assertEqual(_recorded_relative("/old/evidence/retained/carrier.sqlite", posix),
                         ("retained", "carrier.sqlite"))
        with self.assertRaisesRegex(ValueError, "outside"):
            _recorded_relative(r"D:\foreign\one.jsonl", windows)


if __name__ == "__main__":
    if "--native-codex" in sys.argv:
        parser = argparse.ArgumentParser()
        parser.add_argument("--native-codex", required=True)
        parser.add_argument("--evidence", required=True)
        parser.add_argument("--restore-from")
        parser.add_argument("--source-start", action="store_true")
        parser.add_argument("--restore-source-from")
        args = parser.parse_args()
        native_integration(args.native_codex, args.evidence, args.restore_from,
                           args.source_start, args.restore_source_from)
    elif "--inspect-evidence" in sys.argv:
        parser = argparse.ArgumentParser()
        parser.add_argument("--inspect-evidence", required=True)
        args = parser.parse_args()
        print(json.dumps(inspect_evidence(args.inspect_evidence), ensure_ascii=False))
    else:
        unittest.main()
