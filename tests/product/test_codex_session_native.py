"""Bounded fixed-response Codex App Server integration for codex-session.cjs."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
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


def _file_observation(path: Path) -> dict:
    if not path.exists():
        return {"path": str(path), "present": False}
    path = _regular_file(path)
    info = path.stat()
    return {"path": str(path), "present": True, "sha256": digest(path),
            "size": info.st_size, "mode": stat.S_IMODE(info.st_mode)}


def _shared_config_observation() -> dict:
    configured = os.environ.get("CODEX_HOME")
    root = Path(configured) if configured else Path.home() / ".codex"
    return _file_observation(root / "config.toml")


def _source_hashes(root=ROOT) -> dict:
    return {name: _sha(Path(root) / name) for name in SOURCE_FILES}


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


def inspect_evidence(value):
    """Read-only independent inspection; never repairs or creates evidence."""
    root = _ordinary_dir(Path(value).absolute())
    manifest = _read_json(root / "manifest.json")
    post = _read_json(root / "poststate.json")
    envelope = _read_json(root / "retained/node-result.json", 16 * 1024 * 1024)
    controller_config = _read_json(root / "retained/controller-config.json")
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


def native_integration(codex_value, evidence_value):
    root = _fresh_root(evidence_value)
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
    keep.write_bytes(b"Preserve this fixed native session original.\n")
    keep_hash = digest(keep)
    source_hashes = _source_hashes()
    snapshot = _snapshot_sources(root, source_hashes)
    codex_hash, node_hash = digest(codex), digest(node)
    shared_before = _shared_config_observation()
    manifest = {"schema": SCHEMA, "evidence": str(root), "codex": str(codex), "node": str(node),
        "ownedRoots": {name: str(root / name) for name in ("home", "workspace", "state", "temp")},
        "limits": {"requestSeconds": 30, "recoverySeconds": 15,
                   "providerRequestBytes": 2 * 1024 * 1024, "providerRequests": PROVIDER_REQUESTS},
        "resourceController": "windows-job-object" if os.name == "nt" else "posix-session-process-group",
        "providerRequests": PROVIDER_REQUESTS, "sourceHashes": source_hashes,
        "sourceSnapshot": str(snapshot), "keepSha256Before": keep_hash,
        "sharedConfigBefore": shared_before,
        "environmentBoundary": ("Isolated CODEX_HOME/SQLITE/state/temp; Windows process essentials may retain USERPROFILE/APPDATA."
                                if os.name == "nt" else "Isolated CODEX_HOME/HOME/XDG/SQLITE/state/temp."),
        "claimLimit": "Fixed localhost responses and test verifier; no real model, shared Desktop control, cold recovery or product acceptance."}
    env = _owned_environment(manifest)
    version = _codex_version(codex, manifest, "source", env)
    node_version = _codex_version(node, manifest, "node", env)
    if digest(codex) != codex_hash or digest(node) != node_hash:
        raise ValueError("bound executable changed during version freeze")
    manifest["identities"] = {"codex": {"path": str(codex), "sha256": codex_hash, "version": version},
                              "node": {"path": str(node), "sha256": node_hash, "version": node_version}}
    save(root / "manifest.json", manifest)
    fixture = _Fixture(manifest, fixed_provider_item)
    app = None
    resource = None
    fixture_stopped = False
    execution_error = None
    deadline = time.monotonic() + 180
    try:
        native_argv = _argv(manifest, fixture, ("-c", "features.plugins=false", "-c", "features.hooks=false"))
        config = {"schema": "accord-codex-session-native-config/v1", "evidence": str(root),
            "argv": native_argv, "workspace": str(root / "workspace"),
            "nativeLogRoot": str(root / "native/app-server"),
            "recorderPath": str(root / "retained/carrier.sqlite"),
            "resultPath": str(root / "retained/node-result.json"),
            "binding": {"connectionId": "accord-native-session-controller", "hostVersion": version},
            "keepPath": str(keep), "keepSha256": keep_hash,
            "overallDeadlineMs": int(time.time() * 1000) + 165000,
            "identities": manifest["identities"]}
        save(root / "retained/controller-config.json", config)
        caller = snapshot / "tests/product/codex_session_native.cjs"
        app = _App(manifest, "codex-session-controller", [str(node), str(caller)], env, deadline)
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
            post = {"providerRequests": len(fixture.requests), "credentialsObserved": fixture.auth_seen,
                "fixtureThreadStopped": fixture_stopped, "keepSha256After": digest(keep),
                "sourceHashesAfter": _source_hashes(), "sharedConfigAfter": _shared_config_observation(),
                "codexSha256After": digest(codex), "nodeSha256After": digest(node),
                "resourceRecorded": resource is not None, "cleanupFailure": (
                    {"type": type(cleanup_error).__name__, "message": str(cleanup_error)} if cleanup_error else None),
                "executionFailure": ({"type": type(execution_error).__name__,
                    "message": str(execution_error)} if execution_error else None),
                "nativeSessions": native_sessions}
            save(root / "poststate.json", post)
        except BaseException as error:
            cleanup_error = cleanup_error or error
    if execution_error is not None:
        raise execution_error
    if cleanup_error is not None:
        raise RuntimeError("native integration cleanup failed; evidence retained") from cleanup_error
    result = inspect_evidence(root)
    print(json.dumps({"executed": True, "modelCalls": 0, "providerRequests": PROVIDER_REQUESTS,
                      "evidence": str(root), "inspection": result}, ensure_ascii=False))
    return result


class CodexSessionNativeOfflineTests(unittest.TestCase):
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

    def test_fresh_evidence_root_rejects_reuse_before_execution(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(ValueError, "fresh root"):
                _fresh_root(directory)


if __name__ == "__main__":
    if "--native-codex" in sys.argv:
        parser = argparse.ArgumentParser()
        parser.add_argument("--native-codex", required=True)
        parser.add_argument("--evidence", required=True)
        args = parser.parse_args()
        native_integration(args.native_codex, args.evidence)
    elif "--inspect-evidence" in sys.argv:
        parser = argparse.ArgumentParser()
        parser.add_argument("--inspect-evidence", required=True)
        args = parser.parse_args()
        print(json.dumps(inspect_evidence(args.inspect_evidence), ensure_ascii=False))
    else:
        unittest.main()
