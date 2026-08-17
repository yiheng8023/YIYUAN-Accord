"""Inactive Codex pre-response enrollment-capture mechanism candidate.

The Hook never stores or emits the raw prompt, transcript path, session identity,
or credential locator. It requires a separately authorized 32-byte cohort key in
PLUGIN_DATA, emits only keyed commitments, and deletes its derived session state
at SessionEnd. The protected source and cohort validator remain authoritative;
this projection cannot prove registration or block every host output/tool path.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
from pathlib import Path
import stat
import sys
import time
import uuid
from typing import Any


ADAPTER_ID = "agent-autonomy-harness-codex-enrollment-candidate.1"
PROFILE_BINDING = "v1.2-pre-response-enrollment-mechanism-candidate.1"
SUPPORTED_EVENTS = {"UserPromptSubmit", "SessionEnd"}
STATE_SCHEMA = 1
MAX_INPUT_BYTES = 65_536
MAX_OUTPUT_CHARACTERS = 3_072
MAX_IDENTIFIER_CHARACTERS = 512
MAX_PROMPT_BYTES = 262_144
MAX_EVENTS = 256
MAX_STATE_BYTES = 262_144
LOCK_WAIT_SECONDS = 1.0
LOCK_RETRY_SECONDS = 0.02
STALE_LOCK_SECONDS = 30.0
KEY_FILE_NAME = "enrollment-cohort-key.v1.2.bin"
SESSION_DOMAIN = b"agent-autonomy-harness/enrollment-session/v1.2\0"
TURN_DOMAIN = b"agent-autonomy-harness/enrollment-turn/v1.2\0"
PROMPT_DOMAIN = b"agent-autonomy-harness/enrollment-prompt/v1.2\0"
CHAIN_DOMAIN = b"agent-autonomy-harness/enrollment-chain/v1.2\0"


def _is_reparse(info: os.stat_result) -> bool:
    marker = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
    return bool(getattr(info, "st_file_attributes", 0) & marker)


def _bounded_identifier(value: Any) -> str | None:
    if not isinstance(value, str) or not value or len(value) > MAX_IDENTIFIER_CHARACTERS:
        return None
    return value


def _noop(*, warning: str | None = None, stop: bool = False) -> dict[str, Any]:
    output: dict[str, Any] = {"continue": not stop, "suppressOutput": False}
    if warning:
        output["systemMessage"] = warning
    if stop:
        output["stopReason"] = warning or "Enrollment capture stopped fail closed."
    return output


def _block(reason: str) -> dict[str, Any]:
    return {"decision": "block", "reason": reason}


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
        return candidate.resolve(strict=True)
    except (OSError, RuntimeError):
        return None


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            raise ValueError("duplicate JSON key")
        value[key] = item
    return value


def _reject_constant(value: str) -> None:
    raise ValueError(f"non-finite JSON constant: {value}")


def _parse_json(raw: bytes) -> Any:
    return json.loads(
        raw.decode("utf-8"),
        object_pairs_hook=_unique_object,
        parse_constant=_reject_constant,
    )


def _load_key(root: Path) -> bytes | None:
    path = root / KEY_FILE_NAME
    try:
        info = path.lstat()
        if (
            not stat.S_ISREG(info.st_mode)
            or stat.S_ISLNK(info.st_mode)
            or _is_reparse(info)
            or info.st_size != 32
        ):
            return None
        flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0)
        descriptor = os.open(path, flags)
        with os.fdopen(descriptor, "rb") as handle:
            opened = os.fstat(handle.fileno())
            if not stat.S_ISREG(opened.st_mode) or opened.st_size != 32:
                return None
            key = handle.read(33)
    except OSError:
        return None
    return key if len(key) == 32 else None


def _session_commitment(key: bytes, session_id: str) -> str:
    return _hmac(key, SESSION_DOMAIN, session_id.encode("utf-8"))


def _state_path(root: Path, key: bytes, session_id: str) -> Path:
    return root / f"enrollment-{_session_commitment(key, session_id)[12:]}.json"


def _lock_path(root: Path, key: bytes, session_id: str) -> Path:
    return root / f"enrollment-{_session_commitment(key, session_id)[12:]}.lock"


def _empty_state(key: bytes, session_id: str) -> dict[str, Any]:
    return {
        "schema": STATE_SCHEMA,
        "sessionCommitment": _session_commitment(key, session_id),
        "lastCaptureCommitment": None,
        "events": [],
    }


def _valid_commitment(value: Any) -> bool:
    return isinstance(value, str) and len(value) == 76 and value.startswith("hmac-sha256:") and all(
        character in "0123456789abcdef" for character in value[12:]
    )


def _load_state(path: Path, key: bytes, session_id: str) -> dict[str, Any] | None:
    try:
        initial = path.lstat()
    except FileNotFoundError:
        return _empty_state(key, session_id)
    except OSError:
        return None
    if (
        not stat.S_ISREG(initial.st_mode)
        or stat.S_ISLNK(initial.st_mode)
        or _is_reparse(initial)
        or initial.st_size > MAX_STATE_BYTES
    ):
        return None
    try:
        flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0)
        descriptor = os.open(path, flags)
        with os.fdopen(descriptor, "rb") as handle:
            opened = os.fstat(handle.fileno())
            if not stat.S_ISREG(opened.st_mode) or opened.st_size > MAX_STATE_BYTES:
                return None
            raw = handle.read(MAX_STATE_BYTES + 1)
        value = _parse_json(raw)
    except (OSError, UnicodeError, json.JSONDecodeError, RecursionError, ValueError):
        return None
    if (
        not isinstance(value, dict)
        or set(value) != {"schema", "sessionCommitment", "lastCaptureCommitment", "events"}
        or type(value.get("schema")) is not int
        or value.get("schema") != STATE_SCHEMA
        or value.get("sessionCommitment") != _session_commitment(key, session_id)
        or not isinstance(value.get("events"), list)
        or len(value["events"]) > MAX_EVENTS
    ):
        return None
    expected_previous: str | None = None
    for index, event in enumerate(value["events"], start=1):
        if (
            not isinstance(event, dict)
            or set(event) != {
                "sequence",
                "turnDigest",
                "promptCommitment",
                "captureCommitment",
            }
            or type(event.get("sequence")) is not int
            or event["sequence"] != index
            or not _valid_commitment(event.get("turnDigest"))
            or not _valid_commitment(event.get("promptCommitment"))
            or not _valid_commitment(event.get("captureCommitment"))
        ):
            return None
        expected_previous = event["captureCommitment"]
    if value.get("lastCaptureCommitment") != expected_previous:
        return None
    return value


def _write_state(path: Path, state: dict[str, Any]) -> bool:
    encoded = (json.dumps(state, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")
    if len(encoded) > MAX_STATE_BYTES:
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


def _remove_state(path: Path) -> bool:
    candidates = [path]
    try:
        for temporary in path.parent.glob(f".{path.name}.*.tmp"):
            candidates.append(temporary)
            if len(candidates) > 33:
                return False
        for candidate in candidates:
            candidate.unlink(missing_ok=True)
    except OSError:
        return False
    return True


def _acquire_lock(path: Path) -> bool:
    deadline = time.monotonic() + LOCK_WAIT_SECONDS
    while True:
        try:
            path.mkdir(mode=0o700)
            return True
        except FileExistsError:
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
        return True
    except OSError:
        return False


def _hmac(key: bytes, domain: bytes, *parts: bytes) -> str:
    message = domain + b"\0".join(parts)
    return "hmac-sha256:" + hmac.new(key, message, hashlib.sha256).hexdigest()


def _capture(
    state: dict[str, Any], key: bytes, session_id: str, turn_id: str, prompt: str
) -> dict[str, Any] | None:
    prompt_bytes = prompt.encode("utf-8")
    if not prompt_bytes or len(prompt_bytes) > MAX_PROMPT_BYTES:
        return None
    session_bytes = session_id.encode("utf-8")
    turn_bytes = turn_id.encode("utf-8")
    turn_digest = _hmac(key, TURN_DOMAIN, session_bytes, turn_bytes)
    prompt_commitment = _hmac(key, PROMPT_DOMAIN, session_bytes, turn_bytes, prompt_bytes)
    for event in state["events"]:
        if event["turnDigest"] != turn_digest:
            continue
        return event if event["promptCommitment"] == prompt_commitment else None
    if len(state["events"]) >= MAX_EVENTS:
        return None
    sequence = len(state["events"]) + 1
    previous = state["lastCaptureCommitment"] or "cohort-activation"
    capture_commitment = _hmac(
        key,
        CHAIN_DOMAIN,
        str(sequence).encode("ascii"),
        previous.encode("ascii"),
        turn_digest.encode("ascii"),
        prompt_commitment.encode("ascii"),
    )
    event = {
        "sequence": sequence,
        "turnDigest": turn_digest,
        "promptCommitment": prompt_commitment,
        "captureCommitment": capture_commitment,
    }
    state["events"].append(event)
    state["lastCaptureCommitment"] = capture_commitment
    return event


def _context(event: dict[str, Any]) -> str:
    projection = {
        "schema": 1,
        "adapter": ADAPTER_ID,
        "profileBinding": PROFILE_BINDING,
        "event": "UserPromptSubmit",
        "captureSequence": event["sequence"],
        "turnIdentity": event["turnDigest"],
        "sourceCommitment": event["captureCommitment"],
        "enrollmentState": "pre-response-captured-registration-resolution-required",
        "agentRoute": (
            "Before any outcome-bearing answer or action, reconcile current product authority. "
            "For an eligible natural demand, commit the exact task registration and task-specific "
            "validator binding first. For a source-bound exclusion, preserve its code-owned reason "
            "for complete-window validation. Never ask the user to classify or resubmit the task."
        ),
        "claimBoundary": (
            "Private keyed capture plus bounded developer context only; not proof of eligibility, "
            "registration, result, output withholding, complete tool interception, activation or outcome."
        ),
    }
    output = json.dumps(projection, ensure_ascii=False, sort_keys=True)
    if len(output) > MAX_OUTPUT_CHARACTERS:
        raise ValueError("bounded enrollment projection overflow")
    return output


def _handle_locked(
    payload: dict[str, Any],
    event_name: str,
    session_id: str,
    path: Path,
    key: bytes,
) -> dict[str, Any]:
    if event_name == "SessionEnd":
        if not _remove_state(path):
            return _noop(
                warning="Enrollment session state could not be removed; cleanup remains required.",
                stop=True,
            )
        return _noop()
    turn_id = _bounded_identifier(payload.get("turn_id"))
    prompt = payload.get("prompt")
    if turn_id is None or not isinstance(prompt, str):
        return _block(
            "Enrollment capture is unavailable or malformed; disable the inactive candidate or complete exact authorized activation before retrying."
        )
    state = _load_state(path, key, session_id)
    if state is None:
        return _block("Enrollment capture state is malformed or over budget; stop and clean the exact candidate state.")
    captured = _capture(state, key, session_id, turn_id, prompt)
    if captured is None or not _write_state(path, state):
        return _block("Enrollment capture could not be committed without ambiguity; stop before model processing.")
    try:
        context = _context(captured)
    except ValueError:
        return _block("Enrollment capture projection exceeded its fixed budget; stop before model processing.")
    return {
        "continue": True,
        "suppressOutput": False,
        "hookSpecificOutput": {
            "hookEventName": "UserPromptSubmit",
            "additionalContext": context,
        },
    }


def handle(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict):
        return _block("Enrollment Hook input is malformed; stop before model processing.")
    event_name = payload.get("hook_event_name")
    if event_name not in SUPPORTED_EVENTS:
        return _block("Unsupported enrollment event; stop before model processing.")
    session_id = _bounded_identifier(payload.get("session_id"))
    root = _plugin_data_root()
    if session_id is None or root is None:
        return _block("Enrollment capture root is unavailable; stop before model processing.")
    key = _load_key(root)
    if key is None:
        return _block(
            "Enrollment capture key is unavailable; disable the inactive candidate or complete exact authorized activation before retrying."
        )
    path = _state_path(root, key, session_id)
    lock = _lock_path(root, key, session_id)
    if not _acquire_lock(lock):
        return _block("Enrollment capture lock is unavailable; stop before model processing.")
    try:
        output = _handle_locked(payload, event_name, session_id, path, key)
    except Exception:
        output = _block("Enrollment capture failed closed before model processing.")
    if not _release_lock(lock):
        return _block("Enrollment capture lock residue remains; stop and clean the exact candidate state.")
    return output


def main() -> int:
    try:
        raw = sys.stdin.buffer.read(MAX_INPUT_BYTES + 1)
    except OSError:
        raw = b""
    if len(raw) > MAX_INPUT_BYTES:
        output = _block("Enrollment Hook input exceeded its fixed byte budget.")
    else:
        try:
            payload = _parse_json(raw)
        except (UnicodeError, json.JSONDecodeError, RecursionError, ValueError):
            output = _block("Enrollment Hook input is malformed; stop before model processing.")
        else:
            output = handle(payload)
    encoded = json.dumps(output, ensure_ascii=False, sort_keys=True)
    if len(encoded) > MAX_OUTPUT_CHARACTERS:
        encoded = json.dumps(_block("Enrollment Hook output exceeded its fixed budget."), sort_keys=True)
    print(encoded)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
