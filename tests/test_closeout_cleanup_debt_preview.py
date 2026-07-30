from __future__ import annotations

import copy
import json
import tempfile
from pathlib import Path
import unittest

from scripts.inventory_closeout_cleanup_debt import (
    ROOT,
    build_cleanup_debt_preview,
    canonical_sha256,
    validate_cleanup_debt_preview,
)


class CloseoutCleanupDebtPreviewTests(unittest.TestCase):
    def fixture(self, root: Path) -> tuple[dict, ...]:
        (root / ".tmp" / "trial-root" / "nested").mkdir(parents=True)
        (root / ".tmp" / "trial-root" / "state.sqlite").write_bytes(b"x" * 7)
        (root / ".tmp" / "trial-root" / "nested" / "events.jsonl").write_text(
            "{}\n",
            encoding="utf-8",
        )
        (root / "docs").mkdir()
        (root / "docs" / "evidence.md").write_text(
            "Raw root: trial-root\n",
            encoding="utf-8",
        )
        return (
            {
                "id": "trial",
                "relativePath": ".tmp/trial-root",
                "evidenceRole": "fixture",
                "evidenceRefs": ["docs/evidence.md"],
            },
        )

    def test_exact_root_inventory_is_non_authorizing(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            report = build_cleanup_debt_preview(
                root,
                root_specs=self.fixture(root),
            )
            self.assertEqual(
                "inventory-current-retain-no-delete-authority",
                report["status"],
            )
            self.assertEqual(2, report["aggregate"]["fileCount"])
            self.assertEqual(1, report["aggregate"]["directoryCount"])
            self.assertEqual(11, report["aggregate"]["totalBytes"])
            self.assertEqual(1, report["aggregate"]["potentialRuntimeStateRootCount"])
            self.assertEqual("direct-path", report["entries"][0]["evidenceBinding"])
            self.assertEqual(
                "retain-process-artifact-authority-unresolved",
                report["entries"][0]["retentionClass"],
            )
            self.assertFalse(report["entries"][0]["contentInspected"])
            self.assertFalse(report["entries"][0]["deletionAuthorized"])
            self.assertFalse(
                report["protectedExternalBoundary"]["deletionAuthorized"]
            )
            self.assertEqual([], validate_cleanup_debt_preview(report))

    def test_unexpected_root_requires_review(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            specs = self.fixture(root)
            (root / ".tmp" / "foreign-root").mkdir()
            report = build_cleanup_debt_preview(root, root_specs=specs)
            self.assertEqual("inventory-needs-review", report["status"])
            self.assertEqual(
                ["foreign-root"],
                report["unexpectedTopLevelEntries"],
            )

    def test_digest_and_deletion_promotion_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            report = build_cleanup_debt_preview(
                root,
                root_specs=self.fixture(root),
            )
            promoted = copy.deepcopy(report)
            promoted["entries"][0]["deletionAuthorized"] = True
            promoted["reportSha256"] = canonical_sha256(
                {
                    key: value
                    for key, value in promoted.items()
                    if key != "reportSha256"
                }
            )
            self.assertIn(
                "hard-fail-entry-promotion",
                validate_cleanup_debt_preview(promoted),
            )
            drifted = copy.deepcopy(report)
            drifted["status"] = "cleanup-complete"
            self.assertIn(
                "fail-report-digest",
                validate_cleanup_debt_preview(drifted),
            )

    def test_repository_record_remains_a_frozen_pre_cleanup_snapshot(self) -> None:
        actual = json.loads(
            (
                ROOT
                / "registry"
                / "closeout-cleanup-debt-preview-2026-07-24.json"
            ).read_text(encoding="utf-8")
        )
        self.assertEqual([], validate_cleanup_debt_preview(actual))
        self.assertEqual(
            "inventory-current-retain-no-delete-authority",
            actual["status"],
        )
        self.assertEqual("2026-07-27", actual["lastObservedDate"])
        self.assertEqual(
            {
                "retain-authoritative-evidence": {
                    "rootCount": 16,
                    "fileCount": 1235,
                    "directoryCount": 566,
                    "totalBytes": 36352497,
                },
                "retain-invalid-or-excluded-attempt-evidence": {
                    "rootCount": 11,
                    "fileCount": 516,
                    "directoryCount": 237,
                    "totalBytes": 16758179,
                },
                "retain-process-artifact-authority-unresolved": {
                    "rootCount": 7,
                    "fileCount": 707,
                    "directoryCount": 8,
                    "totalBytes": 6686417,
                },
                "retain-user-source-preservation": {
                    "rootCount": 1,
                    "fileCount": 1,
                    "directoryCount": 0,
                    "totalBytes": 549186,
                },
            },
            actual["aggregate"]["retentionClassSummary"],
        )
        self.assertTrue(actual["protectedExternalBoundary"]["exists"])
        self.assertFalse(
            actual["protectedExternalBoundary"]["aggregateIncluded"]
        )

    def test_external_retention_and_classification_promotions_fail_closed(
        self,
    ) -> None:
        report = build_cleanup_debt_preview(ROOT)
        promoted = copy.deepcopy(report)
        promoted["protectedExternalBoundary"]["deletionAuthorized"] = True
        promoted["reportSha256"] = canonical_sha256(
            {
                key: value
                for key, value in promoted.items()
                if key != "reportSha256"
            }
        )
        self.assertIn(
            "hard-fail-external-retention-boundary",
            validate_cleanup_debt_preview(promoted),
        )
        drifted = copy.deepcopy(report)
        drifted["entries"][0]["retentionClass"] = "safe-to-delete"
        drifted["reportSha256"] = canonical_sha256(
            {
                key: value
                for key, value in drifted.items()
                if key != "reportSha256"
            }
        )
        self.assertIn(
            "hard-fail-entry-promotion",
            validate_cleanup_debt_preview(drifted),
        )
        summary_drift = copy.deepcopy(report)
        summary_drift["aggregate"]["retentionClassSummary"][
            "retain-authoritative-evidence"
        ]["totalBytes"] += 1
        summary_drift["reportSha256"] = canonical_sha256(
            {
                key: value
                for key, value in summary_drift.items()
                if key != "reportSha256"
            }
        )
        self.assertIn(
            "fail-retention-class-summary",
            validate_cleanup_debt_preview(summary_drift),
        )


if __name__ == "__main__":
    unittest.main()
