"""Thin, stateless Codex reference-host projection.

The adapter translates Codex's native ``SessionStart`` event into a fresh,
bounded projection of the current repository authority.  It does not read the
user prompt or transcript, persist session state, activate a Hook, or promote
product evidence.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .control import verify_product


ADAPTER_ID = "harness-codex-session-start-v0.2-candidate.1"
SUPPORTED_SESSION_SOURCES = frozenset({"startup", "resume", "clear", "compact"})
CODEX_ENTRY_SUBSTRATE = {
    "source": "https://github.com/openai/codex/tree/be6e8eac029b183056b7e4402879f15d2c85f61b",
    "package": "@openai/codex",
    "version": "0.147.0",
    "license": "Apache-2.0",
    "maturity": "non-prerelease reference-host package with native SessionStart hooks",
    "reuseBoundary": (
        "SessionStart input and additionalContext output only; no prompt or transcript "
        "content access, session store, lifecycle receipt, result validation, or Hook activation"
    ),
}


def _inside_root(root: Path, cwd: Path) -> bool:
    try:
        cwd.resolve(strict=False).relative_to(root.resolve(strict=True))
    except (OSError, RuntimeError, ValueError):
        return False
    return True


def _read_authority(root: Path, relative: str) -> dict[str, Any]:
    value = json.loads((root / relative).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{relative} must contain an object")
    return value


def _active_increment_projection(program: dict[str, Any]) -> dict[str, Any] | None:
    active_id = program.get("activeIncrementId")
    if not isinstance(active_id, str) or not active_id:
        return None
    increments = program.get("increments")
    if not isinstance(increments, list):
        return None
    for increment in increments:
        if not isinstance(increment, dict) or increment.get("id") != active_id:
            continue
        return {
            "id": active_id,
            "correctionClass": increment.get("correctionClass"),
            "observedProblem": increment.get("observedProblem"),
            "hypothesis": increment.get("hypothesis"),
            "falsifier": increment.get("falsifier"),
            "stopCondition": increment.get("stopCondition"),
            "acceptanceIds": increment.get("acceptanceIds"),
        }
    return None


def render_session_start_context(root: Path, payload: Any) -> str | None:
    """Return model context for a supported Codex SessionStart event.

    ``None`` is an explicit unsupported/no-op state.  The function deliberately
    ignores ``transcript_path`` and never opens it.
    """

    if not isinstance(payload, dict):
        return None
    if payload.get("hook_event_name") != "SessionStart":
        return None
    source = payload.get("source")
    if source not in SUPPORTED_SESSION_SOURCES:
        return None
    cwd = payload.get("cwd")
    if not isinstance(cwd, str) or not cwd.strip():
        return None

    try:
        resolved_root = root.resolve(strict=True)
    except (OSError, RuntimeError):
        return None
    if not _inside_root(resolved_root, Path(cwd)):
        return None

    report = verify_product(resolved_root)
    projection: dict[str, Any] = {
        "schema": 1,
        "adapter": ADAPTER_ID,
        "role": "derived-read-only-continuation-context-not-product-authority-or-evidence",
        "event": {"name": "SessionStart", "source": source},
        "referenceHostSubstrate": CODEX_ENTRY_SUBSTRATE,
        "authorityOrder": [
            "product/constitution.json",
            "product/program.json",
            "product/acceptance.json",
            "current repository verifier",
        ],
        "verification": {
            "valid": report.get("valid"),
            "programStatus": report.get("programStatus"),
            "completionState": report.get("completionState"),
            "activeIncrement": report.get("activeIncrement"),
            "criterionStates": report.get("criterionStates"),
            "errors": report.get("errors"),
        },
        "claimBoundary": (
            "This projection restores current authority and route state only; it does not "
            "prove behavior, value, acceptance, portability, release, or production use."
        ),
    }

    if report.get("valid") is not True:
        projection["nextRoute"] = "repair-current-authority-before-product-mutation"
        return json.dumps(projection, ensure_ascii=False, sort_keys=True)

    try:
        constitution = _read_authority(resolved_root, "product/constitution.json")
        program = _read_authority(resolved_root, "product/program.json")
        acceptance = _read_authority(resolved_root, "product/acceptance.json")
    except (OSError, UnicodeError, ValueError, json.JSONDecodeError):
        projection["nextRoute"] = "repair-current-authority-before-product-mutation"
        return json.dumps(projection, ensure_ascii=False, sort_keys=True)

    projection["product"] = {
        "id": constitution.get("productId"),
        "purpose": constitution.get("purpose"),
        "durableOutputs": (
            constitution.get("productForm", {}).get("durableOutputs")
            if isinstance(constitution.get("productForm"), dict)
            else None
        ),
    }
    projection["program"] = {
        "release": program.get("release"),
        "purpose": program.get("purpose"),
        "status": program.get("status"),
        "activeIncrementId": program.get("activeIncrementId"),
        "completionExpression": program.get("completionExpression"),
        "progressionPolicy": program.get("progressionPolicy"),
    }
    projection["acceptance"] = {
        "completionExpression": acceptance.get("completionExpression"),
        "progressRule": acceptance.get("progressRule"),
    }
    active = _active_increment_projection(program)
    if active is not None:
        projection["currentWork"] = active
        projection["nextRoute"] = "continue-current-active-increment"
    elif program.get("status") == "ready":
        projection["nextRoute"] = (
            "select-smallest-causally-justified-product-delivery-increment-from-current-authority"
        )
    elif report.get("completionState") == "accepted":
        projection["nextRoute"] = "stop-product-is-accepted"
    else:
        projection["nextRoute"] = "reconcile-program-state-before-continuing"
    return json.dumps(projection, ensure_ascii=False, sort_keys=True)


def session_start_hook_output(root: Path, payload: Any) -> dict[str, Any]:
    """Return a schema-compatible, non-blocking Codex Hook output."""

    context = render_session_start_context(root, payload)
    output: dict[str, Any] = {"continue": True, "suppressOutput": True}
    if context is not None:
        output["hookSpecificOutput"] = {
            "hookEventName": "SessionStart",
            "additionalContext": context,
        }
    return output
