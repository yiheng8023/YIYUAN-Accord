from __future__ import annotations

import copy
import json
from pathlib import Path
import unittest

from scripts.validate_mattpocock_skills_v123_exact_pin_reconciliation import (
    ACCEPTANCE_PATH,
    AUTHORITY_PATH,
    EVIDENCE_ID,
    RECORD_PATH,
    validate_record,
    validate_repository_reconciliation,
)


ROOT = Path(__file__).resolve().parent.parent


def load(path: Path) -> dict:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


class MattPocockSkillsV123ExactPinReconciliationTests(unittest.TestCase):
    def test_repository_reconciliation_is_valid(self) -> None:
        record = validate_repository_reconciliation(ROOT)
        self.assertEqual(
            "exact-v1.2.3-source-metadata-pin-reconciled-payloads-and-projections-unchanged-restart-persistent",
            record["status"],
        )

    def test_metadata_only_and_restart_persistence_are_explicit(self) -> None:
        record = load(RECORD_PATH)
        self.assertEqual(
            ["repo_branch", "readme_url", "updated_at"],
            record["transaction"]["changedColumns"],
        )
        self.assertFalse(record["transaction"]["payloadsWritten"])
        self.assertFalse(record["transaction"]["projectionsWritten"])
        self.assertFalse(record["transaction"]["enabledFlagsWritten"])
        self.assertEqual(
            ["v1.2.3"], record["postRestartVerification"]["databaseRepoBranches"]
        )

    def test_payload_write_or_behavior_promotion_fails_closed(self) -> None:
        record = load(RECORD_PATH)
        record["transaction"]["payloadsWritten"] = True
        with self.assertRaisesRegex(RuntimeError, "metadata-only transaction"):
            validate_record(record, root=ROOT)

        record = load(RECORD_PATH)
        record["claimBoundary"]["behaviorProved"] = True
        with self.assertRaisesRegex(RuntimeError, "claim boundary"):
            validate_record(record, root=ROOT)

    def test_acceptance_and_current_authority_registration_are_required(self) -> None:
        acceptance = copy.deepcopy(load(ACCEPTANCE_PATH))
        acceptance["evidence"] = [
            item for item in acceptance["evidence"] if item.get("id") != EVIDENCE_ID
        ]
        with self.assertRaisesRegex(RuntimeError, "evidence registration"):
            validate_record(
                load(RECORD_PATH),
                acceptance=acceptance,
                authority=load(AUTHORITY_PATH),
                root=ROOT,
            )

        authority = copy.deepcopy(load(AUTHORITY_PATH))
        authority["currentObservedMattSuiteState"]["upstreamReleaseTag"] = "main"
        with self.assertRaisesRegex(RuntimeError, "portfolio authority"):
            validate_record(
                load(RECORD_PATH),
                acceptance=load(ACCEPTANCE_PATH),
                authority=authority,
                root=ROOT,
            )


if __name__ == "__main__":
    unittest.main()
