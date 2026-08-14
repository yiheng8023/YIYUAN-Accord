"""Host-neutral, read-only continuation projection.

Host adapters validate their native lifecycle envelope, then delegate here to
derive the same bounded view of current Harness authority.  This module does
not activate a host integration, inspect prompts or transcripts, persist
session state, or promote product evidence.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
from typing import Any

from .control import verify_product


SUPPORTED_SESSION_SOURCES = frozenset({"startup", "resume", "clear", "compact"})
MAX_PROJECTION_CHARACTERS = 3072
GIT_OBSERVATION_TIMEOUT_SECONDS = 2


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
        active_work = None
        work_items = increment.get("workItems")
        if isinstance(work_items, list):
            for work in work_items:
                if isinstance(work, dict) and work.get("state") == "active":
                    active_work = {
                        "id": work.get("id"),
                        "state": "active",
                    }
                    break
        return {
            "id": active_id,
            "state": increment.get("state"),
            "workItem": active_work,
            "taskRegistration": increment.get("taskRegistration"),
            "cleanupPaths": (
                increment.get("cleanupBoundary", {}).get("repositoryTemporaryPaths")
                if isinstance(increment.get("cleanupBoundary"), dict)
                else None
            ),
        }
    return None


def _git_output(root: Path, *arguments: str) -> bytes | None:
    try:
        completed = subprocess.run(
            ["git", "--no-optional-locks", "-C", str(root), *arguments],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            check=False,
            timeout=GIT_OBSERVATION_TIMEOUT_SECONDS,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return completed.stdout if completed.returncode == 0 else None


def _unknown_repository_checkpoint(reason: str) -> dict[str, Any]:
    return {
        "state": "unknown",
        "reason": reason,
        "branch": "unknown",
        "head": "unknown",
        "upstream": "unknown",
        "aheadBehind": "unknown",
        "worktreeCount": "unknown",
        "dirtyEntryCount": "unknown",
        "statusSha256": "unknown",
    }


def _repository_checkpoint(root: Path) -> dict[str, Any]:
    raw_status = _git_output(root, "status", "--porcelain=v2", "--branch", "-z")
    if raw_status is None:
        return _unknown_repository_checkpoint("git-status-unavailable")

    branch = "unknown"
    head = "unknown"
    upstream: str | None = None
    ahead_behind: dict[str, int] | str = "unknown-no-upstream"
    dirty_count = 0
    records = raw_status.split(b"\0")
    skip_rename_source = False
    try:
        for raw_record in records:
            if not raw_record:
                continue
            if skip_rename_source:
                skip_rename_source = False
                continue
            if raw_record.startswith(b"# branch.oid "):
                value = raw_record.removeprefix(b"# branch.oid ").decode("ascii")
                head = "unborn" if value == "(initial)" else value
            elif raw_record.startswith(b"# branch.head "):
                value = raw_record.removeprefix(b"# branch.head ").decode("utf-8")
                branch = "detached" if value == "(detached)" else value
            elif raw_record.startswith(b"# branch.upstream "):
                upstream = raw_record.removeprefix(b"# branch.upstream ").decode(
                    "utf-8"
                )
            elif raw_record.startswith(b"# branch.ab "):
                values = raw_record.removeprefix(b"# branch.ab ").split()
                if len(values) == 2:
                    ahead_behind = {
                        "ahead": int(values[0]),
                        "behind": abs(int(values[1])),
                    }
            elif raw_record.startswith((b"1 ", b"u ", b"? ", b"! ")):
                dirty_count += 1
            elif raw_record.startswith(b"2 "):
                dirty_count += 1
                skip_rename_source = True
    except (UnicodeError, ValueError):
        return _unknown_repository_checkpoint("git-status-malformed")

    raw_worktrees = _git_output(root, "worktree", "list", "--porcelain", "-z")
    worktree_count: int | str = "unknown"
    if raw_worktrees is not None:
        worktree_count = sum(
            1
            for record in raw_worktrees.split(b"\0")
            if record.startswith(b"worktree ")
        )

    return {
        "state": "observed",
        "branch": branch,
        "head": head,
        "upstream": upstream if upstream is not None else "absent",
        "aheadBehind": ahead_behind,
        "worktreeCount": worktree_count,
        "dirtyEntryCount": dirty_count,
        "statusSha256": hashlib.sha256(raw_status).hexdigest(),
    }


def _serialize_bounded(projection: dict[str, Any]) -> str:
    budget = {"limit": MAX_PROJECTION_CHARACTERS, "characters": 0}
    projection["projectionBudget"] = budget
    serialized = ""
    for _ in range(3):
        serialized = json.dumps(projection, ensure_ascii=False, sort_keys=True)
        characters = len(serialized)
        if budget["characters"] == characters:
            break
        budget["characters"] = characters
    if len(serialized) <= MAX_PROJECTION_CHARACTERS:
        return serialized

    full_projection_sha256 = hashlib.sha256(serialized.encode("utf-8")).hexdigest()
    fallback = {
        "schema": 1,
        "adapter": projection.get("adapter"),
        "role": projection.get("role"),
        "event": projection.get("event"),
        "authorityPaths": projection.get("authorityPaths"),
        "verification": projection.get("verification"),
        "repositoryCheckpoint": projection.get("repositoryCheckpoint"),
        "program": projection.get("program"),
        "currentWork": projection.get("currentWork"),
        "nextRoute": "re-read-authority-and-reconcile-before-product-mutation",
        "projectionBudget": {
            "limit": MAX_PROJECTION_CHARACTERS,
            "state": "full-projection-overflow",
            "fullProjectionSha256": full_projection_sha256,
        },
        "claimBoundary": projection.get("claimBoundary"),
    }
    fallback_serialized = json.dumps(fallback, ensure_ascii=False, sort_keys=True)
    if len(fallback_serialized) <= MAX_PROJECTION_CHARACTERS:
        return fallback_serialized

    current_work = projection.get("currentWork")
    work_identity = None
    if isinstance(current_work, dict):
        active_work = current_work.get("workItem")
        work_identity = {
            "incrementId": current_work.get("id"),
            "workItemId": (
                active_work.get("id") if isinstance(active_work, dict) else None
            ),
        }
    minimal_fallback = {
        "schema": 1,
        "adapter": projection.get("adapter"),
        "event": projection.get("event"),
        "verification": {
            "valid": projection.get("verification", {}).get("valid")
            if isinstance(projection.get("verification"), dict)
            else None,
            "completionState": projection.get("verification", {}).get(
                "completionState"
            )
            if isinstance(projection.get("verification"), dict)
            else None,
        },
        "repositoryCheckpoint": projection.get("repositoryCheckpoint"),
        "currentWorkIdentity": work_identity,
        "nextRoute": "re-read-authority-and-reconcile-before-product-mutation",
        "projectionBudget": {
            "limit": MAX_PROJECTION_CHARACTERS,
            "state": "fallback-overflow",
            "fullProjectionSha256": full_projection_sha256,
            "fallbackProjectionSha256": hashlib.sha256(
                fallback_serialized.encode("utf-8")
            ).hexdigest(),
        },
        "claimBoundary": projection.get("claimBoundary"),
    }
    return json.dumps(minimal_fallback, ensure_ascii=False, sort_keys=True)


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
        "authorityPaths": [
            "product/constitution.json",
            "product/program.json",
            "product/acceptance.json",
        ],
        "verification": {
            "valid": report.get("valid"),
            "programStatus": report.get("programStatus"),
            "completionState": report.get("completionState"),
            "activeIncrement": report.get("activeIncrement"),
            "criterionStates": report.get("criterionStates"),
            "errors": report.get("errors"),
        },
        "repositoryCheckpoint": _repository_checkpoint(resolved_root),
        "claimBoundary": (
            "Read-only reconciliation context; not authority, evidence, acceptance, "
            "portability, release, or production proof."
        ),
    }

    if report.get("valid") is not True:
        projection["nextRoute"] = "repair-current-authority-before-product-mutation"
        return _serialize_bounded(projection)

    try:
        constitution = _read_authority(resolved_root, "product/constitution.json")
        program = _read_authority(resolved_root, "product/program.json")
        acceptance = _read_authority(resolved_root, "product/acceptance.json")
    except (OSError, UnicodeError, ValueError, json.JSONDecodeError):
        projection["nextRoute"] = "repair-current-authority-before-product-mutation"
        return _serialize_bounded(projection)

    projection["productId"] = constitution.get("productId")
    projection["program"] = {
        "release": program.get("release"),
        "status": program.get("status"),
        "activeIncrementId": program.get("activeIncrementId"),
        "completionExpression": program.get("completionExpression"),
    }
    projection["acceptanceCompletionExpression"] = acceptance.get(
        "completionExpression"
    )
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
    projection["beforeMutation"] = [
        "re-read-authority-paths",
        "compare-repository-checkpoint",
        "reconcile-active-work-registration-and-cleanup",
        "confirm-human-gates-and-required-verification",
    ]
    projection["remainingContextCapacity"] = "unknown"
    return _serialize_bounded(projection)
