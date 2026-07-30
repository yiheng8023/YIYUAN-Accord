#!/usr/bin/env python3
"""Validate the Context-to-Git shared-observer projection contract."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.build_context_continuation_trial_packet import (
    collect_git_truth,
    project_git_observation,
)


ROOT = Path(__file__).resolve().parent.parent
REGISTRY_PATH = (
    "registry/context-git-snapshot-projection-contract-2026-07-27.json"
)
DOC_PATH = "docs/context-git-snapshot-projection-contract-2026-07-27.md"


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _fixture(
    *,
    freshness: str = "local-ref-only",
    ahead_state: str = "known",
) -> dict[str, Any]:
    known = ahead_state == "known"
    return {
        "repository": "C:/fixture/repo",
        "branch": "main",
        "detachedHead": False,
        "head": "a" * 40,
        "recentCommit": {
            "hash": "a" * 40,
            "subject": "fixture",
        },
        "statusEntries": ["R  renamed file.txt", "old file.txt"],
        "dirtyPaths": ["old file.txt", "renamed file.txt"],
        "worktrees": [
            "C:/fixture/repo",
            "C:/fixture/secondary worktree",
        ],
        "remotes": [
            "origin\thttps://example.invalid/repo.git (fetch)",
        ],
        "upstream": "origin/main" if known else None,
        "aheadBehind": {
            "state": ahead_state,
            "ahead": 1 if known else None,
            "behind": 1 if known else None,
        },
        "freshness": freshness,
    }


def validate_contract(
    document: dict[str, Any],
    *,
    root: Path = ROOT,
) -> None:
    _require(
        document.get("schema") == 1
        and document.get("id")
        == "context-git-snapshot-projection-contract-2026-07-27"
        and document.get("date") == "2026-07-27"
        and document.get("status")
        == "verified-local-shared-git-observer-projection-no-live-thread",
        "Context-Git projection identity drifted",
    )
    inputs = document.get("inputs")
    _require(
        isinstance(inputs, list)
        and len(inputs) == 6
        and len({item.get("path") for item in inputs}) == 6,
        "Context-Git projection input set drifted",
    )
    for item in inputs:
        path = root / item["path"]
        _require(
            path.is_file()
            and path.stat().st_size == item.get("bytes")
            and _sha256(path).lower()
            == str(item.get("sha256", "")).lower(),
            f"Context-Git projection input drifted: {path}",
        )
    projection = document.get("projectionContract")
    _require(
        isinstance(projection, dict)
        and projection.get("contextGitSubprocessImplementationCount") == 0
        and projection.get("sharedObserverCallCountPerCollection") == 1
        and projection.get("renameAndCopySecondPathPreserved") is True
        and projection.get("noUpstreamProjectedAsAheadBehindNull") is True
        and projection.get("noUpstreamInventsOriginMainOrZeroZero") is False
        and projection.get("liveRemoteOrUnknownAheadBehindRejected") is True
        and projection.get("dirtyOwnershipInferred") is False,
        "Context-Git projection contract drifted",
    )

    fixture = _fixture()
    projected = project_git_observation(fixture)
    _require(
        projected["statusPorcelainV1"] == fixture["statusEntries"]
        and projected["aheadBehind"] == {"ahead": 1, "behind": 1}
        and projected["remoteFreshness"]
        == "local-refs-only-no-network-refresh"
        and projected["worktreesPorcelain"]
        == [
            "worktree C:/fixture/repo",
            "worktree C:/fixture/secondary worktree",
        ],
        "Context-Git known-upstream projection drifted",
    )
    no_upstream = _fixture(
        freshness="none",
        ahead_state="not-applicable",
    )
    no_upstream["branch"] = None
    no_upstream["detachedHead"] = True
    no_upstream["remotes"] = []
    no_upstream_projected = project_git_observation(no_upstream)
    _require(
        no_upstream_projected["upstream"] is None
        and no_upstream_projected["aheadBehind"] is None
        and no_upstream_projected["remoteFreshness"]
        == "no-upstream-no-network-refresh",
        "Context-Git no-upstream projection drifted",
    )
    calls: list[Path] = []

    def observer(path: str | Path) -> dict[str, Any]:
        calls.append(Path(path))
        return fixture

    _require(
        collect_git_truth(Path("C:/fixture/repo"), observer=observer)
        == projected
        and calls == [Path("C:/fixture/repo")],
        "Context-Git observer call count drifted",
    )
    for mutation in (
        _fixture(freshness="live-remote"),
        _fixture(ahead_state="unknown"),
    ):
        try:
            project_git_observation(mutation)
        except RuntimeError:
            pass
        else:
            raise RuntimeError(
                "Context-Git unsupported observation did not fail closed"
            )

    coverage = document.get("deterministicCoverage")
    _require(
        isinstance(coverage, dict)
        and coverage.get("projectionTestCount") == 5
        and coverage.get("focusedRegressionTestCount") == 36
        and coverage.get("additionalContextRegressionTestCount") == 43,
        "Context-Git projection coverage drifted",
    )
    decision = document.get("decision")
    _require(
        isinstance(decision, dict)
        and decision.get("duplicateContextGitCollectorRemoved") is True
        and decision.get("packetShapeCompatibilityRetained") is True
        and decision.get("packetMustStillBeRevalidatedBeforeAuthorizedCreation")
        is True
        and decision.get("newThreadOrModelRunStarted") is False
        and decision.get("selfAuthoredRuntimeControllerJustified") is False,
        "Context-Git projection decision drifted",
    )
    claim = document.get("claimBoundary")
    _require(
        isinstance(claim, dict)
        and len(claim) == 10
        and all(value is False for value in claim.values()),
        "Context-Git projection claim boundary drifted",
    )
    _require(
        document.get("documentation") == DOC_PATH
        and (root / DOC_PATH).is_file(),
        "Context-Git projection documentation binding drifted",
    )
    normalized = " ".join(
        (root / DOC_PATH).read_text(encoding="utf-8").split()
    )
    for phrase in (
        "no longer maintains a second Git subprocess parser",
        "never invented `origin/main` or `0/0`",
        "`filesystemZeroWriteProved=false`",
        "Local tracking refs are not live remote truth",
        "does not prove automatic thread creation",
        "does not justify a self-authored runtime controller",
    ):
        _require(
            phrase in normalized,
            f"Context-Git projection documentation missing: {phrase}",
        )


def main() -> int:
    document = json.loads(
        (ROOT / REGISTRY_PATH).read_text(encoding="utf-8")
    )
    validate_contract(document)
    print("Context-Git snapshot projection contract validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
