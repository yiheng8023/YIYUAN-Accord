#!/usr/bin/env python3
"""Evaluate deterministic Git truth-snapshot and topology fixtures.

The evaluator recommends or rejects decisions only. It never mutates Git.
"""

from __future__ import annotations

from typing import Any


SNAPSHOT_REQUIRED_FLAGS = (
    "branchKnown",
    "headKnown",
    "statusKnown",
    "recentCommitKnown",
    "worktreesKnown",
    "remoteIdentityKnown",
)
VALID_UPSTREAM_STATES = {"present", "absent", "unknown"}
VALID_AHEAD_BEHIND_STATES = {"known", "not-applicable", "unknown"}
VALID_DIRTY_COMPARISONS = {"exact", "mismatch", "unknown"}
VALID_REMOTE_CLAIMS = {"none", "local-ref-only", "live-remote"}
VALID_TASK_KINDS = {
    "read-only",
    "small-write",
    "risky-write",
    "heavy-test",
    "parallel-work",
}
VALID_DIRTY_OVERLAPS = {"none", "related", "unrelated", "unknown"}
VALID_CREATION_TARGETS = {"branch", "worktree"}


def evaluate_snapshot(facts: dict[str, Any]) -> str:
    if not facts.get("repositoryBound"):
        return "ask-for-repository-locator"
    if any(facts.get(flag) is not True for flag in SNAPSHOT_REQUIRED_FLAGS):
        return "fail-incomplete-repository-snapshot"

    upstream = facts.get("upstreamState")
    if upstream not in VALID_UPSTREAM_STATES:
        raise ValueError(f"unsupported upstream state: {upstream}")
    if upstream == "unknown":
        return "fail-upstream-state-unknown"

    ahead_behind = facts.get("aheadBehindState")
    if ahead_behind not in VALID_AHEAD_BEHIND_STATES:
        raise ValueError(f"unsupported ahead/behind state: {ahead_behind}")
    if upstream == "absent" and ahead_behind != "not-applicable":
        return "fail-invented-upstream-comparison"
    if upstream == "present" and ahead_behind != "known":
        return "fail-incomplete-upstream-comparison"

    dirty = facts.get("dirtyPathComparison")
    if dirty not in VALID_DIRTY_COMPARISONS:
        raise ValueError(f"unsupported dirty-path comparison: {dirty}")
    if dirty != "exact":
        return "fail-dirty-path-omission-or-invention"

    remote_claim = facts.get("remoteClaim")
    if remote_claim not in VALID_REMOTE_CLAIMS:
        raise ValueError(f"unsupported remote claim: {remote_claim}")
    if remote_claim == "live-remote" and facts.get("networkRefreshObserved") is not True:
        return "fail-live-remote-freshness-overclaim"

    if upstream == "absent":
        return "snapshot-complete-no-upstream"
    if remote_claim == "live-remote":
        return "snapshot-complete-live-remote-refreshed"
    return "snapshot-complete-local-refs-only"


def evaluate_topology(facts: dict[str, Any]) -> str:
    if not facts.get("repositoryBound"):
        return "ask-for-repository-locator"
    if not facts.get("taskBound"):
        return "ask-for-task-contract"
    if not facts.get("snapshotComplete"):
        return "require-read-only-repository-snapshot"
    if facts.get("mutationAttempted") and not facts.get("mutationAuthorized"):
        return "hard-fail-unauthorized-topology-mutation"

    task_kind = facts.get("taskKind")
    if task_kind not in VALID_TASK_KINDS:
        raise ValueError(f"unsupported task kind: {task_kind}")
    dirty_overlap = facts.get("dirtyOverlap")
    if dirty_overlap not in VALID_DIRTY_OVERLAPS:
        raise ValueError(f"unsupported dirty overlap: {dirty_overlap}")
    if dirty_overlap == "unknown":
        return "resolve-dirty-ownership-before-topology"

    if task_kind == "read-only":
        return "continue-current-workspace-read-only"
    if facts.get("requiresCurrentDirtyState"):
        if dirty_overlap != "related":
            return "fail-current-dirty-state-dependency-mismatch"
        return "continue-current-workspace-related-dirty-state"
    if dirty_overlap == "unrelated":
        return "recommend-isolated-worktree"
    if facts.get("runtimeIsolationNeeded") or task_kind in {
        "risky-write",
        "heavy-test",
        "parallel-work",
    }:
        return "recommend-isolated-worktree"
    if task_kind == "small-write" and not facts.get("currentBranchPurposeAligned"):
        return "recommend-new-branch-current-workspace"
    return "continue-current-workspace-current-branch"


def evaluate_creation(facts: dict[str, Any]) -> str:
    if not facts.get("repositoryBound") or not facts.get("taskBound"):
        return "ask-for-bound-repository-and-task"
    if not facts.get("snapshotComplete"):
        return "require-read-only-repository-snapshot"
    if facts.get("mutationAuthorized") is not True:
        return "stop-no-creation-authority"
    target = facts.get("targetType")
    if target not in VALID_CREATION_TARGETS:
        raise ValueError(f"unsupported creation target: {target}")
    if facts.get("exactStartPointBound") is not True:
        return "stop-bind-exact-start-point"
    if facts.get("targetCollisionState") != "clear":
        return "stop-resolve-target-collision"
    return f"eligible-create-{target}"


def evaluate_merge(facts: dict[str, Any]) -> str:
    if facts.get("mergeAuthorized") is not True:
        return "stop-no-merge-authority"
    if (
        facts.get("sourceShaBound") is not True
        or facts.get("targetShaBound") is not True
    ):
        return "stop-bind-source-and-target-shas"
    if facts.get("targetDirty") is True:
        return "stop-protect-target-dirty-work"
    if facts.get("conflictState") != "none":
        return "stop-for-human-conflict-decision"
    if facts.get("checksPassed") is not True:
        return "stop-require-verification"
    if facts.get("fastForwardPossible") is not True:
        return "stop-no-fast-forward-proof"
    return "eligible-fast-forward-merge"


def evaluate_cleanup(facts: dict[str, Any]) -> str:
    if facts.get("cleanupAuthorized") is not True:
        return "retain-no-cleanup-authority"
    if facts.get("exactTargetsBound") is not True:
        return "stop-bind-exact-cleanup-targets"
    if facts.get("deliveredOrExplicitlyDisposable") is not True:
        return "retain-undelivered-evidence"
    if facts.get("worktreeClean") is not True:
        return "retain-dirty-worktree"
    if facts.get("branchMergedOrExplicitlyDisposable") is not True:
        return "retain-unmerged-branch"
    return "eligible-exact-cleanup"


EVALUATORS = {
    "GIT-01": evaluate_snapshot,
    "GIT-02": evaluate_topology,
    "GIT-03": evaluate_creation,
    "GIT-04": evaluate_merge,
    "GIT-05": evaluate_cleanup,
}


def evaluate_fixture_document(document: dict[str, Any]) -> list[dict[str, str]]:
    results: list[dict[str, str]] = []
    for fixture in document["fixtures"]:
        actual = EVALUATORS[fixture["lane"]](fixture["facts"])
        results.append(
            {"id": fixture["id"], "expected": fixture["expected"], "actual": actual}
        )
    return results
