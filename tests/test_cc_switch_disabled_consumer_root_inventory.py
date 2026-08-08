from __future__ import annotations

import copy
import json
from pathlib import Path
import unittest

from scripts.validate_cc_switch_disabled_consumer_root_inventory import (
    ACCEPTANCE_PATH,
    AUTHORITY_PATH,
    CLOSEOUT_PATH,
    EVIDENCE_ID,
    RECORD_PATH,
    validate_record,
    validate_repository_inventory,
)


ROOT = Path(__file__).resolve().parent.parent


def load(path: Path) -> dict:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


class CcSwitchDisabledConsumerRootInventoryTests(unittest.TestCase):
    def test_repository_inventory_is_valid(self) -> None:
        record = validate_repository_inventory(ROOT)
        self.assertEqual(
            "four-disabled-consumer-roots-readonly-observed-absent-zero-matt-projections",
            record["status"],
        )

    def test_four_roots_are_absent_and_all_flags_are_zero(self) -> None:
        record = load(RECORD_PATH)
        self.assertEqual(
            {"gemini", "grokbuild", "opencode", "hermes"},
            {root["host"] for root in record["observation"]["roots"]},
        )
        self.assertTrue(all(not root["exists"] for root in record["observation"]["roots"]))
        self.assertEqual(
            {0}, set(record["observation"]["enabledMattByHost"].values())
        )

    def test_host_or_behavior_promotion_fails_closed(self) -> None:
        record = load(RECORD_PATH)
        record["claimBoundary"]["hostInstalledProved"] = True
        with self.assertRaisesRegex(RuntimeError, "claim boundary"):
            validate_record(record, root=ROOT)

        record = load(RECORD_PATH)
        record["authorityBoundary"]["enablementAuthorized"] = True
        with self.assertRaisesRegex(RuntimeError, "authority boundary"):
            validate_record(record, root=ROOT)

    def test_acceptance_authority_and_closeout_links_are_required(self) -> None:
        acceptance = copy.deepcopy(load(ACCEPTANCE_PATH))
        acceptance["evidence"] = [
            item for item in acceptance["evidence"] if item.get("id") != EVIDENCE_ID
        ]
        with self.assertRaisesRegex(RuntimeError, "evidence registration"):
            validate_record(
                load(RECORD_PATH),
                acceptance=acceptance,
                authority=load(AUTHORITY_PATH),
                closeout=load(CLOSEOUT_PATH),
                root=ROOT,
            )


if __name__ == "__main__":
    unittest.main()
