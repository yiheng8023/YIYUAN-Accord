import copy
import subprocess
import tempfile
import unittest
from pathlib import Path

from scripts.build_git_readonly_preflight_envelope import (
    build_readonly_preflight_envelope,
    canonical_sha256,
    validate_readonly_preflight_envelope,
)


def git(repository: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(repository), *args], check=True, capture_output=True, text=True)


def repository(path: Path) -> Path:
    path.mkdir()
    git(path, "init")
    git(path, "config", "user.name", "Harness test")
    git(path, "config", "user.email", "harness@example.invalid")
    (path / "tracked.txt").write_text("base\n", encoding="utf-8")
    git(path, "add", "tracked.txt")
    git(path, "commit", "-m", "base")
    git(path, "branch", "-M", "main")
    return path


class GitReadonlyPreflightEnvelopeTests(unittest.TestCase):
    def _clock(self):
        values = iter([
            "2026-07-24T00:00:00Z", "2026-07-24T00:00:01Z",
            "2026-07-24T00:00:02Z", "2026-07-24T00:00:03Z",
        ])
        return lambda: next(values)

    def test_clean_no_upstream_is_readonly_and_not_live_remote(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            envelope = build_readonly_preflight_envelope(repository(Path(temporary) / "repo"), clock=self._clock())
            self.assertEqual("preflight-observed-clean-ownership-not-applicable", envelope["status"])
            self.assertEqual([], envelope["failureCodes"])
            self.assertEqual("none", envelope["events"]["before"]["snapshot"]["freshness"])
            self.assertFalse(envelope["writeAttempted"])

    def test_dirty_paths_default_to_unknown_ownership(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = repository(Path(temporary) / "repo")
            (root / "tracked.txt").write_text("dirty\n", encoding="utf-8")
            (root / "untracked.txt").write_text("new\n", encoding="utf-8")
            envelope = build_readonly_preflight_envelope(root, clock=self._clock())
            self.assertEqual("preflight-observed-dirty-ownership-unbound", envelope["status"])
            self.assertEqual({"tracked.txt", "untracked.txt"}, {item["path"] for item in envelope["dirtyOwnership"]})
            self.assertTrue(all(item["ownerState"] == "unknown" for item in envelope["dirtyOwnership"]))

    def test_rename_preserves_raw_porcelain_evidence_for_both_paths(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = repository(Path(temporary) / "repo")
            git(root, "mv", "tracked.txt", "renamed.txt")
            envelope = build_readonly_preflight_envelope(root, clock=self._clock())
            paths = {item["path"] for item in envelope["dirtyOwnership"]}
            self.assertEqual({"tracked.txt", "renamed.txt"}, paths)
            self.assertTrue(all(item["rawPorcelainEntries"] for item in envelope["dirtyOwnership"]))

    def test_injected_second_snapshot_drift_blocks_without_retry(self) -> None:
        first = {"repository":"C:/repo","statusEntries":[],"dirtyPaths":[],"freshness":"none","facts":{"remoteClaim":"none","networkRefreshObserved":False}}
        second = {"repository":"C:/repo","statusEntries":[],"dirtyPaths":[],"freshness":"none","facts":{"remoteClaim":"none","networkRefreshObserved":False},"changed":True}
        answers = iter([first, second])
        envelope = build_readonly_preflight_envelope("C:/repo", observer=lambda _: next(answers), clock=self._clock())
        self.assertEqual("blocked-concurrent-drift", envelope["status"])
        self.assertIn("blocked-concurrent-drift", envelope["failureCodes"])
        self.assertFalse(envelope["retryAttempted"])

    def test_owner_promotion_and_live_remote_claim_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            envelope = build_readonly_preflight_envelope(repository(Path(temporary) / "repo"), clock=self._clock())
            changed = copy.deepcopy(envelope)
            changed["dirtyOwnership"] = [{"path":"x","ownerState":"task-owned","rawPorcelainEntries":[]}]
            changed["envelopeSha256"] = canonical_sha256({key: value for key, value in changed.items() if key != "envelopeSha256" and key not in {"status", "failureCodes"}})
            self.assertIn("hard-fail-dirty-ownership-promotion", validate_readonly_preflight_envelope(changed)["failureCodes"])
            remote = copy.deepcopy(envelope)
            for event in remote["events"].values():
                event["snapshot"]["freshness"] = "live-remote"
                event["snapshotSha256"] = canonical_sha256(event["snapshot"])
            remote["envelopeSha256"] = canonical_sha256({key: value for key, value in remote.items() if key != "envelopeSha256" and key not in {"status", "failureCodes"}})
            self.assertIn("fail-readonly-freshness-binding", validate_readonly_preflight_envelope(remote)["failureCodes"])

    def test_event_order_path_evidence_and_counts_are_digest_bound(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = repository(Path(temporary) / "repo")
            weird = root / "空 格.md"
            weird.write_text("x\n", encoding="utf-8")
            envelope = build_readonly_preflight_envelope(root, clock=self._clock(), run_id="run-test")
            self.assertEqual("run-test:1", envelope["events"]["before"]["eventId"])
            self.assertEqual("run-test:2", envelope["events"]["after"]["eventId"])
            tampered = copy.deepcopy(envelope)
            tampered["dirtyOwnership"][0]["rawPorcelainEntries"] = []
            tampered["envelopeSha256"] = canonical_sha256({key: value for key, value in tampered.items() if key != "envelopeSha256" and key not in {"status", "failureCodes"}})
            self.assertIn("fail-dirty-ownership-coverage", validate_readonly_preflight_envelope(tampered)["failureCodes"])
            promoted = copy.deepcopy(envelope)
            promoted["countsAsCreationSafetyEvidence"] = True
            promoted["envelopeSha256"] = canonical_sha256({key: value for key, value in promoted.items() if key != "envelopeSha256" and key not in {"status", "failureCodes"}})
            self.assertIn("hard-fail-count-promotion", validate_readonly_preflight_envelope(promoted)["failureCodes"])
            out_of_order = copy.deepcopy(envelope)
            out_of_order["events"]["after"]["startedAt"] = "2026-07-23T23:59:59Z"
            out_of_order["envelopeSha256"] = canonical_sha256({key: value for key, value in out_of_order.items() if key != "envelopeSha256" and key not in {"status", "failureCodes"}})
            self.assertIn("fail-event-time-order", validate_readonly_preflight_envelope(out_of_order)["failureCodes"])


if __name__ == "__main__":
    unittest.main()
