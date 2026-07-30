from pathlib import Path
import json
import unittest

from scripts.evaluate_git_topology_trial import (
    evaluate_cleanup,
    evaluate_creation,
    evaluate_fixture_document,
    evaluate_merge,
    evaluate_snapshot,
    evaluate_topology,
)


ROOT = Path(__file__).resolve().parent.parent
FIXTURE_PATH = ROOT / "tests/fixtures/git-topology-decision-fixtures-2026-07-19.json"


class GitTopologyTrialTests(unittest.TestCase):
    def test_all_predeclared_decision_fixtures_pass(self) -> None:
        document = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
        results = evaluate_fixture_document(document)
        self.assertEqual(32, len(results))
        self.assertEqual([], [item for item in results if item["expected"] != item["actual"]])

    def test_snapshot_rejects_unknown_enum(self) -> None:
        facts = {
            "repositoryBound": True,
            "branchKnown": True,
            "headKnown": True,
            "statusKnown": True,
            "recentCommitKnown": True,
            "worktreesKnown": True,
            "remoteIdentityKnown": True,
            "upstreamState": "guessed",
        }
        with self.assertRaisesRegex(ValueError, "unsupported upstream state"):
            evaluate_snapshot(facts)

    def test_topology_never_turns_recommendation_into_authority(self) -> None:
        facts = {
            "repositoryBound": True,
            "taskBound": True,
            "snapshotComplete": True,
            "mutationAttempted": True,
            "mutationAuthorized": False,
        }
        self.assertEqual(
            "hard-fail-unauthorized-topology-mutation",
            evaluate_topology(facts),
        )

    def test_creation_merge_and_cleanup_keep_separate_authority_gates(self) -> None:
        self.assertEqual(
            "stop-no-creation-authority",
            evaluate_creation(
                {
                    "repositoryBound": True,
                    "taskBound": True,
                    "snapshotComplete": True,
                    "mutationAuthorized": False,
                }
            ),
        )
        self.assertEqual(
            "stop-no-merge-authority",
            evaluate_merge({"mergeAuthorized": False}),
        )
        self.assertEqual(
            "retain-no-cleanup-authority",
            evaluate_cleanup({"cleanupAuthorized": False}),
        )


if __name__ == "__main__":
    unittest.main()
