"""Bounded Codex carrier-lifecycle Hook.

This package-owned script never imports task-repository code, reads prompts or
transcripts, invokes Git, or creates a conversation.  It records only bounded
native lifecycle counters under Codex's plugin-data directory and gives the
Agent a small decision input.  Thread transition remains a native Agent tool
operation and measured use remains forbidden until the package profile binding
and trusted interpreter are materialized.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import stat
import sys
import time
from typing import Any
import uuid


ADAPTER_ID = "agent-autonomy-harness-codex-carrier-v1-candidate"
MAX_INPUT_BYTES = 65_536
MAX_OUTPUT_CHARACTERS = 3_072
MAX_SESSION_ID_CHARACTERS = 256
MAX_TURN_ID_CHARACTERS = 256
MAX_COUNTER = 99
MAX_SESSION_TEMP_FILES = 64
LOCK_WAIT_SECONDS = 0.5
LOCK_RETRY_SECONDS = 0.01
STALE_LOCK_SECONDS = 10.0
STATE_SCHEMA = 1
PROFILE_BINDING = "unbound-mechanism-only"
SUPPORTED_EVENTS = frozenset(
    {"PreCompact", "PostCompact", "SessionStart", "SessionEnd"}
)
SUPPORTED_START_SOURCES = frozenset({"startup", "resume", "clear", "compact"})
SUPPORTED_COMPACT_TRIGGERS = frozenset({"auto", "manual"})


def _noop(*, warning: str | None = None, stop: bool = False) -> dict[str, Any]:
    output: dict[str, Any] = {
        "continue": not stop,
        "suppressOutput": warning is None,
    }
    if warning is not None:
        output["systemMessage"] = warning
    return output


def _bounded_identifier(value: Any, limit: int) -> str | None:
    if not isinstance(value, str) or not value or len(value) > limit:
        return None
    if any(ord(character) < 32 for character in value):
        return None
    return value


def _is_reparse(info: os.stat_result) -> bool:
    attributes = getattr(info, "st_file_attributes", 0)
    marker = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
    return bool(attributes & marker)


def _plugin_data_root() -> Path | None:
    raw = os.environ.get("PLUGIN_DATA")
    if not isinstance(raw, str) or not raw.strip() or len(raw) > 4096:
        return None
    candidate = Path(raw)
    if not candidate.is_absolute():
        return None
    try:
        info = candidate.lstat()
        if not stat.S_ISDIR(info.st_mode) or stat.S_ISLNK(info.st_mode) or _is_reparse(info):
            return None
        root = candidate.resolve(strict=True)
    except (OSError, RuntimeError):
        return None
    return root


def _state_path(root: Path, session_id: str) -> Path:
    digest = hashlib.sha256(session_id.encode("utf-8")).hexdigest()
    return root / f"carrier-{digest}.json"


def _lock_path(root: Path, session_id: str) -> Path:
    digest = hashlib.sha256(session_id.encode("utf-8")).hexdigest()
    return root / f"carrier-{digest}.lock"


def _empty_state(session_id: str) -> dict[str, Any]:
    return {
        "schema": STATE_SCHEMA,
        "sessionDigest": hashlib.sha256(session_id.encode("utf-8")).hexdigest(),
        "compactionCount": 0,
        "automaticCompactionCount": 0,
        "manualCompactionCount": 0,
        "clearCount": 0,
        "unpairedCompactionCount": 0,
        "lastCompactTurnDigest": None,
        "pendingCompactStart": False,
        "counterOverflow": False,
    }


def _valid_counter(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and 0 <= value <= MAX_COUNTER


def _load_state(path: Path, session_id: str) -> dict[str, Any] | None:
    try:
        initial = path.lstat()
    except FileNotFoundError:
        return _empty_state(session_id)
    except OSError:
        return None
    if (
        not stat.S_ISREG(initial.st_mode)
        or stat.S_ISLNK(initial.st_mode)
        or _is_reparse(initial)
        or initial.st_size > 2048
    ):
        return None
    try:
        flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0)
        descriptor = os.open(path, flags)
        with os.fdopen(descriptor, "rb") as handle:
            opened = os.fstat(handle.fileno())
            if not stat.S_ISREG(opened.st_mode) or opened.st_size > 2048:
                return None
            raw = handle.read(2049)
        if len(raw) > 2048:
            return None
        value = json.loads(raw.decode("utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError, RecursionError):
        return None
    expected = _empty_state(session_id)
    if not isinstance(value, dict) or set(value) != set(expected):
        return None
    if value.get("schema") != STATE_SCHEMA or value.get("sessionDigest") != expected["sessionDigest"]:
        return None
    for field in (
        "compactionCount",
        "automaticCompactionCount",
        "manualCompactionCount",
        "clearCount",
        "unpairedCompactionCount",
    ):
        if not _valid_counter(value.get(field)):
            return None
    if not isinstance(value.get("pendingCompactStart"), bool):
        return None
    if not isinstance(value.get("counterOverflow"), bool):
        return None
    digest = value.get("lastCompactTurnDigest")
    if digest is not None and (not isinstance(digest, str) or len(digest) != 64):
        return None
    return value


def _increment(state: dict[str, Any], field: str) -> None:
    value = state[field]
    if value >= MAX_COUNTER:
        state["counterOverflow"] = True
        return
    state[field] = value + 1


def _write_state(path: Path, state: dict[str, Any]) -> bool:
    encoded = (json.dumps(state, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")
    if len(encoded) > 2048:
        return False
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    try:
        with temporary.open("xb") as handle:
            handle.write(encoded)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    except OSError:
        try:
            temporary.unlink(missing_ok=True)
        except OSError:
            pass
        return False
    return True


def _remove_session_state(path: Path) -> bool:
    candidates = [path]
    try:
        for temporary in path.parent.glob(f".{path.name}.*.tmp"):
            candidates.append(temporary)
            if len(candidates) > MAX_SESSION_TEMP_FILES + 1:
                return False
        for candidate in candidates:
            candidate.unlink(missing_ok=True)
    except OSError:
        return False
    return True


def _acquire_lock(path: Path) -> bool:
    deadline = time.monotonic() + LOCK_WAIT_SECONDS
    contended = False
    while True:
        if contended and time.monotonic() >= deadline:
            return False
        try:
            path.mkdir(mode=0o700)
            if contended and time.monotonic() >= deadline:
                try:
                    path.rmdir()
                except OSError:
                    pass
                return False
            return True
        except FileExistsError:
            contended = True
            try:
                info = path.lstat()
                if not stat.S_ISDIR(info.st_mode) or stat.S_ISLNK(info.st_mode) or _is_reparse(info):
                    return False
                if time.time() - info.st_mtime > STALE_LOCK_SECONDS:
                    path.rmdir()
                    continue
            except FileNotFoundError:
                continue
            except OSError:
                return False
            if time.monotonic() >= deadline:
                return False
            time.sleep(LOCK_RETRY_SECONDS)
        except OSError:
            return False


def _release_lock(path: Path) -> bool:
    try:
        path.rmdir()
    except OSError:
        return False
    return True


def _record_compaction(
    state: dict[str, Any], *, turn_id: str | None, trigger: str | None
) -> None:
    digest = hashlib.sha256(turn_id.encode("utf-8")).hexdigest() if turn_id else None
    if digest is not None and digest == state["lastCompactTurnDigest"]:
        state["pendingCompactStart"] = True
        return
    _increment(state, "compactionCount")
    if trigger == "auto":
        _increment(state, "automaticCompactionCount")
    elif trigger == "manual":
        _increment(state, "manualCompactionCount")
    else:
        _increment(state, "unpairedCompactionCount")
    state["lastCompactTurnDigest"] = digest
    state["pendingCompactStart"] = True


def _risk(state: dict[str, Any]) -> str:
    if state["counterOverflow"] or state["compactionCount"] >= 2:
        return "transition-required-at-next-material-checkpoint"
    if state["compactionCount"] == 1 or state["clearCount"] > 0:
        return "reconcile-durable-state-before-mutation"
    return "observe-and-keep-only-while-task-risk-remains-low"


def _context(event: str, state: dict[str, Any]) -> str:
    projection = {
        "schema": 1,
        "adapter": ADAPTER_ID,
        "profileBinding": PROFILE_BINDING,
        "event": event,
        "remainingContextCapacity": "unknown",
        "carrierRisk": _risk(state),
        "compactionCount": state["compactionCount"],
        "automaticCompactionCount": state["automaticCompactionCount"],
        "manualCompactionCount": state["manualCompactionCount"],
        "clearCount": state["clearCount"],
        "counterOverflow": state["counterOverflow"],
        "agentRoute": (
            "At a material checkpoint, re-observe goal, authority, Git and verification state. "
            "When carrierRisk requires transition and same-goal native fork is available, the Agent "
            "creates and continues the destination, verifies recovery, then archives the source. "
            "Do not ask the user to choose or operate the carrier."
        ),
        "claimBoundary": (
            "Inactive mechanism candidate; profile is not frozen, no measured behavior or outcome claim."
        ),
    }
    output = json.dumps(projection, ensure_ascii=False, sort_keys=True)
    if len(output) > MAX_OUTPUT_CHARACTERS:
        raise ValueError("bounded carrier projection overflow")
    return output


def _handle_locked(
    payload: dict[str, Any], event: str, session_id: str, path: Path
) -> dict[str, Any]:
    if event == "SessionEnd":
        first_cleanup = _remove_session_state(path)
        time.sleep(LOCK_WAIT_SECONDS + LOCK_RETRY_SECONDS)
        second_cleanup = _remove_session_state(path)
        if not first_cleanup or not second_cleanup:
            return _noop(warning="Carrier session residue could not be removed; cleanup remains required.")
        return _noop()

    state = _load_state(path, session_id)
    if state is None:
        return _noop(
            warning="Carrier lifecycle state is malformed or over budget; stop before material mutation.",
            stop=True,
        )

    if event in {"PreCompact", "PostCompact"}:
        trigger = payload.get("trigger")
        if trigger not in SUPPORTED_COMPACT_TRIGGERS:
            return _noop(warning="Unsupported compaction trigger; continuation safety is unknown.", stop=True)
        turn_id = _bounded_identifier(payload.get("turn_id"), MAX_TURN_ID_CHARACTERS)
        if turn_id is None:
            return _noop(warning="Missing bounded compaction turn identity; continuation safety is unknown.", stop=True)
        _record_compaction(state, turn_id=turn_id, trigger=trigger)
    elif event == "SessionStart":
        source = payload.get("source")
        if source not in SUPPORTED_START_SOURCES:
            return _noop(warning="Unsupported SessionStart source; continuation safety is unknown.", stop=True)
        if source == "compact":
            if state["pendingCompactStart"]:
                state["pendingCompactStart"] = False
            else:
                _record_compaction(state, turn_id=None, trigger=None)
                state["pendingCompactStart"] = False
        elif source == "clear":
            _increment(state, "clearCount")

    if not _write_state(path, state):
        return _noop(
            warning="Carrier lifecycle state could not be committed; stop before material mutation.",
            stop=True,
        )
    if event != "SessionStart":
        return _noop()
    try:
        context = _context(event, state)
    except ValueError:
        return _noop(warning="Carrier lifecycle projection exceeded its fixed budget.", stop=True)
    return {
        "continue": True,
        "suppressOutput": False,
        "hookSpecificOutput": {
            "hookEventName": event,
            "additionalContext": context,
        },
    }


def handle(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict):
        return _noop(warning="Carrier Hook input is malformed; continuation safety is unknown.", stop=True)
    event = payload.get("hook_event_name")
    if event not in SUPPORTED_EVENTS:
        return _noop(warning="Unsupported carrier lifecycle event; continuation safety is unknown.", stop=True)
    session_id = _bounded_identifier(payload.get("session_id"), MAX_SESSION_ID_CHARACTERS)
    root = _plugin_data_root()
    if session_id is None or root is None:
        return _noop(
            warning="Carrier lifecycle state is unavailable; stop before material mutation and repair or disable this adapter.",
            stop=True,
        )
    path = _state_path(root, session_id)
    lock = _lock_path(root, session_id)
    if not _acquire_lock(lock):
        return _noop(warning="Carrier lifecycle state lock is unavailable; continuation safety is unknown.", stop=True)
    try:
        output = _handle_locked(payload, event, session_id, path)
    except Exception:
        output = _noop(warning="Carrier lifecycle processing failed closed.", stop=True)
    released = _release_lock(lock)
    if not released:
        return _noop(warning="Carrier lifecycle state lock residue remains; cleanup is required.", stop=True)
    return output


def main() -> int:
    try:
        raw = sys.stdin.buffer.read(MAX_INPUT_BYTES + 1)
    except OSError:
        raw = b""
    if len(raw) > MAX_INPUT_BYTES:
        output = _noop(warning="Carrier Hook input exceeded its fixed byte budget.", stop=True)
    else:
        try:
            payload = json.loads(raw.decode("utf-8"))
        except (UnicodeError, json.JSONDecodeError, RecursionError):
            output = _noop(warning="Carrier Hook input is malformed; continuation safety is unknown.", stop=True)
        else:
            output = handle(payload)
    encoded = json.dumps(output, ensure_ascii=False, sort_keys=True)
    if len(encoded) > MAX_OUTPUT_CHARACTERS:
        encoded = json.dumps(_noop(warning="Carrier Hook output exceeded its fixed budget.", stop=True), sort_keys=True)
    print(encoded)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
