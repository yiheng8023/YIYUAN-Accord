import hashlib
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

from scripts.observe_git_snapshot import observe_repository


TEMP_ROOT_OVERRIDE = os.environ.get("AGENT_AUTONOMY_GIT_TEST_ROOT")
TEMP_ROOT = Path(TEMP_ROOT_OVERRIDE).resolve() if TEMP_ROOT_OVERRIDE else None


def run_git(repository: Path, *arguments: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(repository), *arguments],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    return result.stdout.strip()


def run_git_failure(repository: Path, *arguments: str) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        ["git", "-C", str(repository), *arguments],
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    if result.returncode == 0:
        raise AssertionError(f"expected Git command to fail: {' '.join(arguments)}")
    return result


def initialize_repository(repository: Path) -> None:
    repository.mkdir(parents=True)
    run_git(repository, "init")
    run_git(repository, "config", "user.name", "Agent Autonomy Harness Test")
    run_git(repository, "config", "user.email", "harness-test@example.invalid")
    run_git(repository, "config", "gc.auto", "0")
    run_git(repository, "config", "maintenance.auto", "false")
    (repository / "tracked.txt").write_text("baseline\n", encoding="utf-8")
    run_git(repository, "add", "tracked.txt")
    run_git(repository, "commit", "-m", "initial fixture")
    run_git(repository, "branch", "-M", "main")


class GitSnapshotIntegrationTests(unittest.TestCase):
    def test_real_repository_without_upstream_is_observed_without_invention(self) -> None:
        with tempfile.TemporaryDirectory(prefix="agent-autonomy-git-no-upstream-", dir=TEMP_ROOT) as temp:
            repository = Path(temp) / "repository"
            initialize_repository(repository)

            observation = observe_repository(repository)

            self.assertEqual("main", observation["branch"])
            self.assertIsNone(observation["upstream"])
            self.assertEqual("none", observation["freshness"])
            self.assertEqual([], observation["dirtyPaths"])
            self.assertEqual("snapshot-complete-no-upstream", observation["outcome"])

    def test_local_upstream_dirty_paths_and_unrelated_bytes_are_preserved(self) -> None:
        with tempfile.TemporaryDirectory(prefix="agent-autonomy-git-local-upstream-", dir=TEMP_ROOT) as temp:
            root = Path(temp)
            repository = root / "repository"
            remote = root / "origin.git"
            initialize_repository(repository)
            remote.mkdir()
            run_git(remote, "init", "--bare")
            run_git(repository, "remote", "add", "origin", str(remote))
            run_git(repository, "push", "--set-upstream", "origin", "main")

            (repository / "tracked.txt").write_text("changed\n", encoding="utf-8")
            (repository / "untracked.txt").write_text("new\n", encoding="utf-8")
            sentinel = repository / "unrelated.bin"
            sentinel.write_bytes(bytes(range(64)))
            before_hash = hashlib.sha256(sentinel.read_bytes()).hexdigest()

            observation = observe_repository(repository)

            after_hash = hashlib.sha256(sentinel.read_bytes()).hexdigest()
            self.assertEqual(before_hash, after_hash)
            self.assertEqual("origin/main", observation["upstream"])
            self.assertEqual("local-ref-only", observation["freshness"])
            self.assertEqual({"tracked.txt", "untracked.txt", "unrelated.bin"}, set(observation["dirtyPaths"]))
            self.assertEqual({"state": "known", "ahead": 0, "behind": 0}, observation["aheadBehind"])
            self.assertEqual("snapshot-complete-local-refs-only", observation["outcome"])

    def test_detached_head_is_explicit_and_not_misreported_as_a_branch(self) -> None:
        with tempfile.TemporaryDirectory(prefix="agent-autonomy-git-detached-", dir=TEMP_ROOT) as temp:
            repository = Path(temp) / "repository"
            initialize_repository(repository)
            run_git(repository, "checkout", "--detach", "HEAD")

            observation = observe_repository(repository)

            self.assertTrue(observation["detachedHead"])
            self.assertIsNone(observation["branch"])
            self.assertEqual("snapshot-complete-no-upstream", observation["outcome"])

    def test_rename_porcelain_preserves_both_paths(self) -> None:
        with tempfile.TemporaryDirectory(prefix="agent-autonomy-git-rename-", dir=TEMP_ROOT) as temp:
            repository = Path(temp) / "repository"
            initialize_repository(repository)
            run_git(repository, "mv", "tracked.txt", "renamed.txt")

            observation = observe_repository(repository)

            self.assertEqual({"tracked.txt", "renamed.txt"}, set(observation["dirtyPaths"]))
            self.assertTrue(any(entry.startswith("R ") for entry in observation["statusEntries"]))

    def test_copy_porcelain_preserves_source_and_target_paths(self) -> None:
        with tempfile.TemporaryDirectory(prefix="agent-autonomy-git-copy-", dir=TEMP_ROOT) as temp:
            repository = Path(temp) / "repository"
            initialize_repository(repository)
            run_git(repository, "config", "status.renames", "copies")
            source = repository / "tracked.txt"
            target = repository / "copied.txt"
            target.write_bytes(source.read_bytes())
            source.write_text("baseline\nsource changed\n", encoding="utf-8")
            run_git(repository, "add", "tracked.txt", "copied.txt")

            observation = observe_repository(repository)

            self.assertIn("tracked.txt", observation["dirtyPaths"])
            self.assertIn("copied.txt", observation["dirtyPaths"])
            copy_index = next(
                index
                for index, entry in enumerate(observation["statusEntries"])
                if entry.startswith("C ")
            )
            self.assertEqual(
                "copied.txt",
                observation["statusEntries"][copy_index][3:],
            )
            self.assertEqual(
                "tracked.txt",
                observation["statusEntries"][copy_index + 1],
            )

    def test_multiple_worktrees_are_enumerated_without_claiming_creation_safety(self) -> None:
        with tempfile.TemporaryDirectory(prefix="agent-autonomy-git-worktrees-", dir=TEMP_ROOT) as temp:
            root = Path(temp)
            repository = root / "repository"
            secondary = root / "secondary"
            initialize_repository(repository)
            run_git(repository, "worktree", "add", "--detach", str(secondary), "HEAD")

            observation = observe_repository(repository)

            observed = {Path(path).resolve() for path in observation["worktrees"]}
            self.assertEqual({repository.resolve(), secondary.resolve()}, observed)
            self.assertEqual("snapshot-complete-no-upstream", observation["outcome"])

    def test_local_tracking_ref_counts_diverged_ahead_and_behind(self) -> None:
        with tempfile.TemporaryDirectory(prefix="agent-autonomy-git-diverged-", dir=TEMP_ROOT) as temp:
            root = Path(temp)
            repository = root / "repository"
            remote = root / "origin.git"
            peer = root / "peer"
            initialize_repository(repository)
            remote.mkdir()
            run_git(remote, "init", "--bare")
            run_git(repository, "remote", "add", "origin", str(remote))
            run_git(repository, "push", "--set-upstream", "origin", "main")

            (repository / "local.txt").write_text("local\n", encoding="utf-8")
            run_git(repository, "add", "local.txt")
            run_git(repository, "commit", "-m", "local divergence")
            ahead = observe_repository(repository)
            self.assertEqual({"state": "known", "ahead": 1, "behind": 0}, ahead["aheadBehind"])

            run_git(root, "clone", "--branch", "main", str(remote), str(peer))
            run_git(peer, "config", "user.name", "Agent Autonomy Harness Peer")
            run_git(peer, "config", "user.email", "harness-peer@example.invalid")
            run_git(peer, "config", "gc.auto", "0")
            run_git(peer, "config", "maintenance.auto", "false")
            (peer / "peer.txt").write_text("peer\n", encoding="utf-8")
            run_git(peer, "add", "peer.txt")
            run_git(peer, "commit", "-m", "peer divergence")
            run_git(peer, "push", "origin", "main")
            run_git(repository, "fetch", "origin")

            diverged = observe_repository(repository)
            self.assertEqual({"state": "known", "ahead": 1, "behind": 1}, diverged["aheadBehind"])
            self.assertEqual("local-ref-only", diverged["freshness"])

    def test_failed_checkout_leaves_reconstructable_head_status_and_bytes(self) -> None:
        with tempfile.TemporaryDirectory(prefix="agent-autonomy-git-checkout-failure-", dir=TEMP_ROOT) as temp:
            repository = Path(temp) / "repository"
            initialize_repository(repository)
            sentinel = repository / "unrelated.bin"
            sentinel.write_bytes(bytes(reversed(range(64))))
            before_hash = hashlib.sha256(sentinel.read_bytes()).hexdigest()
            before = observe_repository(repository)

            failure = run_git_failure(repository, "checkout", "refs/heads/does-not-exist")
            after = observe_repository(repository)

            self.assertIn("did not match", failure.stderr)
            self.assertEqual(before["head"], after["head"])
            self.assertEqual(before["branch"], after["branch"])
            self.assertEqual(before["statusEntries"], after["statusEntries"])
            self.assertEqual(before["worktrees"], after["worktrees"])
            self.assertEqual(before_hash, hashlib.sha256(sentinel.read_bytes()).hexdigest())

    def test_failed_worktree_add_leaves_no_partial_registration(self) -> None:
        with tempfile.TemporaryDirectory(prefix="agent-autonomy-git-worktree-failure-", dir=TEMP_ROOT) as temp:
            root = Path(temp)
            repository = root / "repository"
            blocked_target = root / "blocked-target"
            initialize_repository(repository)
            blocked_target.mkdir()
            sentinel = blocked_target / "sentinel.bin"
            sentinel.write_bytes(bytes(range(32)))
            before_hash = hashlib.sha256(sentinel.read_bytes()).hexdigest()
            before = observe_repository(repository)

            failure = run_git_failure(repository, "worktree", "add", str(blocked_target), "HEAD")
            after = observe_repository(repository)

            self.assertIn("already exists", failure.stderr)
            self.assertEqual(before["head"], after["head"])
            self.assertEqual(before["worktrees"], after["worktrees"])
            self.assertNotIn(blocked_target.resolve(), {Path(path).resolve() for path in after["worktrees"]})
            self.assertEqual(before_hash, hashlib.sha256(sentinel.read_bytes()).hexdigest())

    def test_content_conflict_is_observed_without_recovery_mutation(self) -> None:
        with tempfile.TemporaryDirectory(prefix="agent-autonomy-git-content-conflict-", dir=TEMP_ROOT) as temp:
            repository = Path(temp) / "repository"
            initialize_repository(repository)
            sentinel = repository / "unrelated.bin"
            sentinel.write_bytes(bytes(range(64)))
            run_git(repository, "add", "unrelated.bin")
            run_git(repository, "commit", "-m", "add unrelated sentinel")

            run_git(repository, "checkout", "-b", "topic")
            (repository / "tracked.txt").write_text("topic change\n", encoding="utf-8")
            run_git(repository, "add", "tracked.txt")
            run_git(repository, "commit", "-m", "topic conflict")
            run_git(repository, "checkout", "main")
            (repository / "tracked.txt").write_text("main change\n", encoding="utf-8")
            run_git(repository, "add", "tracked.txt")
            run_git(repository, "commit", "-m", "main conflict")

            failure = run_git_failure(repository, "merge", "topic")
            self.assertIn("CONFLICT", failure.stdout + failure.stderr)
            before_head = run_git(repository, "rev-parse", "HEAD")
            before_merge_head = run_git(repository, "rev-parse", "-q", "--verify", "MERGE_HEAD")
            before_worktrees = run_git(repository, "worktree", "list", "--porcelain")
            before_sentinel_hash = hashlib.sha256(sentinel.read_bytes()).hexdigest()
            before_conflict_hash = hashlib.sha256(
                (repository / "tracked.txt").read_bytes()
            ).hexdigest()
            before_unmerged_index = run_git(repository, "ls-files", "-u")
            self.assertTrue(before_unmerged_index)

            observation = observe_repository(repository)

            self.assertEqual(before_head, run_git(repository, "rev-parse", "HEAD"))
            self.assertEqual(
                before_merge_head,
                run_git(repository, "rev-parse", "-q", "--verify", "MERGE_HEAD"),
            )
            self.assertEqual(
                before_worktrees,
                run_git(repository, "worktree", "list", "--porcelain"),
            )
            self.assertEqual(
                before_sentinel_hash,
                hashlib.sha256(sentinel.read_bytes()).hexdigest(),
            )
            self.assertEqual(
                before_conflict_hash,
                hashlib.sha256(
                    (repository / "tracked.txt").read_bytes()
                ).hexdigest(),
            )
            self.assertEqual(
                before_unmerged_index,
                run_git(repository, "ls-files", "-u"),
            )
            self.assertIn("UU tracked.txt", observation["statusEntries"])
            self.assertEqual({"tracked.txt"}, set(observation["dirtyPaths"]))

    def test_disposable_worktree_fast_forward_and_safe_cleanup_lifecycle(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory(
            prefix="agent-autonomy-git-ff-lifecycle-",
            dir=TEMP_ROOT,
        ) as temp:
            root = Path(temp)
            repository = root / "repository"
            secondary = root / "secondary"
            sentinel = root / "unrelated.bin"
            branch = "codex/fixture-worktree"
            initialize_repository(repository)
            sentinel.write_bytes(bytes(range(128)))
            sentinel_hash = hashlib.sha256(sentinel.read_bytes()).hexdigest()
            base = run_git(repository, "rev-parse", "HEAD")

            run_git(
                repository,
                "worktree",
                "add",
                "-b",
                branch,
                str(secondary),
                base,
            )
            self.assertEqual(base, run_git(secondary, "rev-parse", "HEAD"))
            self.assertEqual(
                base,
                run_git(repository, "rev-parse", f"refs/heads/{branch}"),
            )
            self.assertEqual(base, run_git(repository, "rev-parse", "main"))

            (secondary / "tracked.txt").write_text(
                "feature\n",
                encoding="utf-8",
            )
            run_git(secondary, "add", "tracked.txt")
            run_git(secondary, "commit", "-m", "fixture feature")
            feature = run_git(secondary, "rev-parse", "HEAD")
            self.assertEqual(base, run_git(repository, "rev-parse", "main"))
            self.assertEqual("", run_git(repository, "status", "--porcelain"))
            self.assertEqual("", run_git(secondary, "status", "--porcelain"))

            run_git(repository, "merge", "--ff-only", branch)
            self.assertEqual(feature, run_git(repository, "rev-parse", "main"))
            self.assertEqual(
                [feature, base],
                run_git(repository, "rev-list", "--parents", "-n", "1", feature).split(),
            )
            self.assertFalse((repository / ".git" / "MERGE_HEAD").exists())
            self.assertEqual("", run_git(repository, "status", "--porcelain"))
            self.assertEqual("", run_git(secondary, "status", "--porcelain"))

            run_git(repository, "worktree", "remove", str(secondary))
            run_git(repository, "branch", "-d", branch)

            observation = observe_repository(repository)
            self.assertEqual([repository.resolve()], [
                Path(path).resolve() for path in observation["worktrees"]
            ])
            self.assertFalse(secondary.exists())
            run_git_failure(
                repository,
                "show-ref",
                "--verify",
                f"refs/heads/{branch}",
            )
            run_git(repository, "merge-base", "--is-ancestor", feature, "main")
            self.assertEqual("feature\n", (repository / "tracked.txt").read_text(encoding="utf-8"))
            self.assertEqual(
                sentinel_hash,
                hashlib.sha256(sentinel.read_bytes()).hexdigest(),
            )

    def test_dirty_worktree_refuses_non_force_cleanup_and_preserves_bytes(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory(
            prefix="agent-autonomy-git-dirty-cleanup-",
            dir=TEMP_ROOT,
        ) as temp:
            root = Path(temp)
            repository = root / "repository"
            secondary = root / "secondary"
            branch = "codex/fixture-dirty-worktree"
            initialize_repository(repository)
            base = run_git(repository, "rev-parse", "HEAD")
            run_git(
                repository,
                "worktree",
                "add",
                "-b",
                branch,
                str(secondary),
                base,
            )
            dirty = secondary / "dirty.bin"
            dirty.write_bytes(bytes(reversed(range(64))))
            dirty_hash = hashlib.sha256(dirty.read_bytes()).hexdigest()
            before = observe_repository(repository)

            run_git_failure(
                repository,
                "worktree",
                "remove",
                str(secondary),
            )

            after = observe_repository(repository)
            self.assertEqual(before["head"], after["head"])
            self.assertEqual(before["worktrees"], after["worktrees"])
            self.assertTrue(secondary.exists())
            self.assertEqual(
                dirty_hash,
                hashlib.sha256(dirty.read_bytes()).hexdigest(),
            )
            self.assertEqual(
                base,
                run_git(repository, "rev-parse", f"refs/heads/{branch}"),
            )

    def test_dirty_primary_refuses_fast_forward_and_preserves_state(self) -> None:
        with tempfile.TemporaryDirectory(
            prefix="agent-autonomy-git-dirty-merge-",
            dir=TEMP_ROOT,
        ) as temp:
            root = Path(temp)
            repository = root / "repository"
            secondary = root / "secondary"
            sentinel = root / "unrelated.bin"
            branch = "codex/fixture-dirty-merge"
            initialize_repository(repository)
            base = run_git(repository, "rev-parse", "HEAD")
            sentinel.write_bytes(bytes(range(96)))
            sentinel_hash = hashlib.sha256(sentinel.read_bytes()).hexdigest()
            run_git(
                repository,
                "worktree",
                "add",
                "-b",
                branch,
                str(secondary),
                base,
            )
            (secondary / "tracked.txt").write_text(
                "feature\n",
                encoding="utf-8",
            )
            run_git(secondary, "add", "tracked.txt")
            run_git(secondary, "commit", "-m", "fixture conflicting feature")
            feature = run_git(secondary, "rev-parse", "HEAD")

            dirty = repository / "tracked.txt"
            dirty.write_text("local dirty bytes\n", encoding="utf-8")
            dirty_hash = hashlib.sha256(dirty.read_bytes()).hexdigest()
            before = observe_repository(repository)

            run_git_failure(repository, "merge", "--ff-only", branch)

            after = observe_repository(repository)
            self.assertEqual(base, after["head"])
            self.assertEqual(before["statusEntries"], after["statusEntries"])
            self.assertEqual(before["worktrees"], after["worktrees"])
            self.assertEqual(
                feature,
                run_git(repository, "rev-parse", f"refs/heads/{branch}"),
            )
            self.assertEqual(
                dirty_hash,
                hashlib.sha256(dirty.read_bytes()).hexdigest(),
            )
            self.assertEqual(
                sentinel_hash,
                hashlib.sha256(sentinel.read_bytes()).hexdigest(),
            )
            self.assertFalse((repository / ".git" / "MERGE_HEAD").exists())

    def test_unmerged_branch_refuses_safe_delete_after_clean_worktree_removal(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory(
            prefix="agent-autonomy-git-unmerged-retain-",
            dir=TEMP_ROOT,
        ) as temp:
            root = Path(temp)
            repository = root / "repository"
            secondary = root / "secondary"
            branch = "codex/fixture-unmerged"
            initialize_repository(repository)
            base = run_git(repository, "rev-parse", "HEAD")
            run_git(
                repository,
                "worktree",
                "add",
                "-b",
                branch,
                str(secondary),
                base,
            )
            (secondary / "feature.txt").write_text(
                "undelivered\n",
                encoding="utf-8",
            )
            run_git(secondary, "add", "feature.txt")
            run_git(secondary, "commit", "-m", "undelivered fixture")
            feature = run_git(secondary, "rev-parse", "HEAD")
            run_git(repository, "worktree", "remove", str(secondary))

            run_git_failure(repository, "branch", "-d", branch)

            self.assertEqual(base, run_git(repository, "rev-parse", "main"))
            self.assertEqual(
                feature,
                run_git(repository, "rev-parse", f"refs/heads/{branch}"),
            )
            self.assertFalse(secondary.exists())


if __name__ == "__main__":
    unittest.main()
