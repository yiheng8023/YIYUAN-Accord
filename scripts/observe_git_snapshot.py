#!/usr/bin/env python3
"""Observe a local Git repository without mutating it.

The probe intentionally performs no fetch and labels upstream comparisons as
local-ref-only. Test setup may create disposable repositories, but this module
only issues read-only Git commands against the bound repository.
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

try:
    from scripts.evaluate_git_topology_trial import evaluate_snapshot
except ModuleNotFoundError:  # Direct execution from the scripts directory.
    from evaluate_git_topology_trial import evaluate_snapshot


class GitObservationError(RuntimeError):
    """Raised when a required read-only Git observation cannot be completed."""


def _git(repository: Path, *arguments: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        ["git", "-C", str(repository), *arguments],
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="surrogateescape",
    )
    if check and result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip() or "unknown Git error"
        raise GitObservationError(f"git {' '.join(arguments)} failed: {detail}")
    return result


def _parse_status(repository: Path) -> tuple[list[str], list[str]]:
    raw = _git(
        repository,
        "status",
        "--porcelain=v1",
        "-z",
        "--untracked-files=all",
    ).stdout
    tokens = [token for token in raw.split("\0") if token]
    entries: list[str] = []
    paths: list[str] = []
    index = 0
    while index < len(tokens):
        token = tokens[index]
        if len(token) < 4:
            raise GitObservationError(f"unexpected porcelain entry: {token!r}")
        entries.append(token)
        paths.append(token[3:])
        status = token[:2]
        if "R" in status or "C" in status:
            index += 1
            if index >= len(tokens):
                raise GitObservationError("rename/copy porcelain entry omitted its second path")
            entries.append(tokens[index])
            paths.append(tokens[index])
        index += 1
    return entries, sorted(set(paths))


def _parse_worktrees(repository: Path) -> list[str]:
    output = _git(repository, "worktree", "list", "--porcelain").stdout
    return [line.removeprefix("worktree ") for line in output.splitlines() if line.startswith("worktree ")]


def observe_repository(repository: str | Path) -> dict[str, Any]:
    requested = Path(repository).resolve()
    root = Path(_git(requested, "rev-parse", "--show-toplevel").stdout.strip()).resolve()
    head = _git(root, "rev-parse", "HEAD").stdout.strip()

    branch_result = _git(root, "symbolic-ref", "--quiet", "--short", "HEAD", check=False)
    if branch_result.returncode not in (0, 1):
        raise GitObservationError(branch_result.stderr.strip() or "unable to determine branch state")
    branch = branch_result.stdout.strip() if branch_result.returncode == 0 else None

    recent_raw = _git(root, "log", "-1", "--format=%H%x00%s").stdout.rstrip("\n")
    recent_parts = recent_raw.split("\0", 1)
    if len(recent_parts) != 2:
        raise GitObservationError("recent commit output did not contain hash and subject")

    status_entries, dirty_paths = _parse_status(root)
    worktrees = _parse_worktrees(root)
    remotes = [line for line in _git(root, "remote", "-v").stdout.splitlines() if line]

    upstream_result = _git(
        root,
        "rev-parse",
        "--abbrev-ref",
        "--symbolic-full-name",
        "@{upstream}",
        check=False,
    )
    if upstream_result.returncode == 0:
        upstream = upstream_result.stdout.strip()
        counts = _git(root, "rev-list", "--left-right", "--count", f"HEAD...{upstream}").stdout.split()
        if len(counts) != 2:
            raise GitObservationError("ahead/behind output did not contain two counts")
        ahead_behind: dict[str, Any] = {
            "state": "known",
            "ahead": int(counts[0]),
            "behind": int(counts[1]),
        }
        upstream_state = "present"
        remote_claim = "local-ref-only"
    else:
        upstream = None
        ahead_behind = {"state": "not-applicable", "ahead": None, "behind": None}
        upstream_state = "absent"
        remote_claim = "none"

    facts = {
        "repositoryBound": True,
        "branchKnown": True,
        "headKnown": True,
        "statusKnown": True,
        "recentCommitKnown": True,
        "worktreesKnown": True,
        "remoteIdentityKnown": True,
        "upstreamState": upstream_state,
        "aheadBehindState": ahead_behind["state"],
        "dirtyPathComparison": "exact",
        "remoteClaim": remote_claim,
        "networkRefreshObserved": False,
    }
    return {
        "repository": root.as_posix(),
        "branch": branch,
        "detachedHead": branch is None,
        "head": head,
        "recentCommit": {"hash": recent_parts[0], "subject": recent_parts[1]},
        "statusEntries": status_entries,
        "dirtyPaths": dirty_paths,
        "worktrees": worktrees,
        "remotes": remotes,
        "upstream": upstream,
        "aheadBehind": ahead_behind,
        "freshness": remote_claim,
        "facts": facts,
        "outcome": evaluate_snapshot(facts),
    }
