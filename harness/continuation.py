"""Host-neutral, read-only continuation projection.

Host adapters validate their native lifecycle envelope, then delegate here to
derive the same bounded view of current Harness authority.  This module does
not activate a host integration, inspect prompts or transcripts, persist
session state, or promote product evidence.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .control import verify_product


SUPPORTED_SESSION_SOURCES = frozenset({"startup", "resume", "clear", "compact"})


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


def render_continuation_context(
    root: Path,
    payload: Any,
    *,
    adapter_id: str,
    host_substrate: dict[str, str],
) -> str | None:
    """Render the common projection for a supported native SessionStart event."""

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
        "adapter": adapter_id,
        "role": "derived-read-only-continuation-context-not-product-authority-or-evidence",
        "event": {"name": "SessionStart", "source": source},
        "referenceHostSubstrate": host_substrate,
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
