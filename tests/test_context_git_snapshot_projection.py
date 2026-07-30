from __future__ import annotations

import os
from pathlib import Path
import tempfile
import unittest

from scripts.build_context_continuation_trial_packet import (
    collect_git_truth,
    project_git_observation,
)
from scripts.observe_git_snapshot import observe_repository
from tests.test_git_snapshot_integration import (
    initialize_repository,
    run_git,
)


TEMP_ROOT_OVERRIDE = os.environ.get("AGENT_AUTONOMY_GIT_TEST_ROOT")
TEMP_ROOT = (
    Path(TEMP_ROOT_OVERRIDE).resolve()
    if TEMP_ROOT_OVERRIDE
    else None
)


class ContextGitSnapshotProjectionTests(unittest.TestCase):
    def test_projection_preserves_shared_observer_semantics(self) -> None:
        observation = {
            "repository": "C:/fixture/repo",
            "branch": "main",
            "detachedHead": False,
            "head": "a" * 40,
            "recentCommit": {
                "hash": "a" * 40,
                "subject": "fixture commit",
            },
            "statusEntries": [
                "R  new name.txt",
                "old name.txt",
            ],
            "dirtyPaths": [
                "new name.txt",
                "old name.txt",
            ],
            "worktrees": [
                "C:/fixture/repo",
                "C:/fixture/secondary",
            ],
            "remotes": [
                "origin\thttps://example.invalid/repo.git (fetch)",
            ],
            "upstream": "origin/main",
            "aheadBehind": {
                "state": "known",
                "ahead": 1,
                "behind": 1,
            },
            "freshness": "local-ref-only",
        }

        projected = project_git_observation(observation)

        self.assertEqual(
            observation["statusEntries"],
            projected["statusPorcelainV1"],
        )
        self.assertEqual(
            {
                "ahead": 1,
                "behind": 1,
            },
            projected["aheadBehind"],
        )
        self.assertEqual(
            [
                "worktree C:/fixture/repo",
                "worktree C:/fixture/secondary",
            ],
            projected["worktreesPorcelain"],
        )
        self.assertEqual(
            "local-refs-only-no-network-refresh",
            projected["remoteFreshness"],
        )

    def test_no_upstream_stays_not_applicable(self) -> None:
        observation = {
            "repository": "C:/fixture/repo",
            "branch": None,
            "detachedHead": True,
            "head": "b" * 40,
            "recentCommit": {
                "hash": "b" * 40,
                "subject": "detached fixture",
            },
            "statusEntries": [],
            "dirtyPaths": [],
            "worktrees": ["C:/fixture/repo"],
            "remotes": [],
            "upstream": None,
            "aheadBehind": {
                "state": "not-applicable",
                "ahead": None,
                "behind": None,
            },
            "freshness": "none",
        }

        projected = project_git_observation(observation)

        self.assertIsNone(projected["branch"])
        self.assertTrue(projected["detachedHead"])
        self.assertIsNone(projected["upstream"])
        self.assertIsNone(projected["aheadBehind"])
        self.assertEqual(
            "no-upstream-no-network-refresh",
            projected["remoteFreshness"],
        )

    def test_collector_uses_one_injected_observer_result(self) -> None:
        calls: list[Path] = []
        observation = {
            "repository": "C:/fixture/repo",
            "branch": "main",
            "detachedHead": False,
            "head": "c" * 40,
            "recentCommit": {
                "hash": "c" * 40,
                "subject": "single observation",
            },
            "statusEntries": [],
            "dirtyPaths": [],
            "worktrees": ["C:/fixture/repo"],
            "remotes": [],
            "upstream": None,
            "aheadBehind": {
                "state": "not-applicable",
                "ahead": None,
                "behind": None,
            },
            "freshness": "none",
        }

        def observer(path: str | Path) -> dict:
            calls.append(Path(path))
            return observation

        truth = collect_git_truth(
            Path("C:/fixture/repo"),
            observer=observer,
        )

        self.assertEqual([Path("C:/fixture/repo")], calls)
        self.assertEqual(
            project_git_observation(observation),
            truth,
        )

    def test_disposable_rename_and_worktrees_match_observer_projection(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory(
            prefix="agent-autonomy-context-git-projection-",
            dir=TEMP_ROOT,
        ) as temporary:
            root = Path(temporary)
            repository = root / "repository with spaces"
            secondary = root / "secondary with spaces"
            initialize_repository(repository)
            run_git(
                repository,
                "worktree",
                "add",
                "--detach",
                str(secondary),
                "HEAD",
            )
            run_git(
                repository,
                "mv",
                "tracked.txt",
                "renamed file.txt",
            )

            observation = observe_repository(repository)
            truth = collect_git_truth(repository)

            self.assertEqual(
                project_git_observation(observation),
                truth,
            )
            self.assertEqual(
                {"tracked.txt", "renamed file.txt"},
                set(observation["dirtyPaths"]),
            )
            self.assertIn(
                "tracked.txt",
                truth["statusPorcelainV1"],
            )
            self.assertEqual(
                {
                    f"worktree {repository.resolve().as_posix()}",
                    f"worktree {secondary.resolve().as_posix()}",
                },
                set(truth["worktreesPorcelain"]),
            )
            self.assertEqual(
                "no-upstream-no-network-refresh",
                truth["remoteFreshness"],
            )

    def test_live_remote_or_unknown_state_fails_closed(self) -> None:
        base = {
            "repository": "C:/fixture/repo",
            "branch": "main",
            "detachedHead": False,
            "head": "d" * 40,
            "recentCommit": {
                "hash": "d" * 40,
                "subject": "fixture",
            },
            "statusEntries": [],
            "dirtyPaths": [],
            "worktrees": ["C:/fixture/repo"],
            "remotes": [],
            "upstream": "origin/main",
            "aheadBehind": {
                "state": "known",
                "ahead": 0,
                "behind": 0,
            },
            "freshness": "live-remote",
        }
        with self.assertRaisesRegex(
            RuntimeError,
            "freshness exceeds local-only scope",
        ):
            project_git_observation(base)

        unknown = dict(base)
        unknown["freshness"] = "local-ref-only"
        unknown["aheadBehind"] = {
            "state": "unknown",
            "ahead": None,
            "behind": None,
        }
        with self.assertRaisesRegex(
            RuntimeError,
            "ahead/behind state is unsupported",
        ):
            project_git_observation(unknown)


if __name__ == "__main__":
    unittest.main()
