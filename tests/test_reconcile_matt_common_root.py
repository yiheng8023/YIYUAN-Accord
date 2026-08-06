from __future__ import annotations

import json
import os
from pathlib import Path
import tempfile
import unittest

from scripts.reconcile_matt_common_root import (
    DIRECT_NAMES,
    RETAINED_NAMES,
    RETIRED_NAME,
    execute_transaction,
    preflight,
    rollback_transaction,
)


def write_skill(root: Path, name: str, body: str) -> None:
    target = root / name
    target.mkdir(parents=True)
    (target / "SKILL.md").write_text(body, encoding="utf-8")


class ReconcileMattCommonRootTests(unittest.TestCase):
    def build_fixture(self, temporary: str) -> tuple[Path, Path]:
        home = Path(temporary) / "home"
        agents = home / ".agents" / "skills"
        cc = home / ".cc-switch" / "skills"
        backups = home / ".cc-switch" / "skill-backups"
        backups.mkdir(parents=True)
        for name in DIRECT_NAMES:
            write_skill(agents, name, f"common:{name}\n")
            write_skill(cc, name, f"cc:{name}\n")
        return home, backups / "transaction"

    def test_preflight_requires_exact_direct_cohort_and_cc_targets(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            home, _ = self.build_fixture(temporary)

            result = preflight(home)

        self.assertEqual(list(DIRECT_NAMES), result["directNames"])
        self.assertTrue(result["allSourcesPhysicalDirectories"])
        self.assertTrue(result["allCcTargetsPhysicalDirectories"])

    def test_execute_moves_originals_and_installs_twelve_links(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            home, transaction = self.build_fixture(temporary)

            result = execute_transaction(home, transaction)

            agents = home / ".agents" / "skills"
            cc = home / ".cc-switch" / "skills"
            for name in RETAINED_NAMES:
                self.assertTrue((agents / name).is_symlink())
                self.assertEqual((cc / name).resolve(), (agents / name).resolve())
            self.assertFalse((agents / RETIRED_NAME).exists())
            self.assertTrue((transaction / "originals" / RETIRED_NAME).is_dir())
            self.assertEqual("committed", result["status"])
            journal = json.loads((transaction / "journal.json").read_text("utf-8"))
            self.assertEqual("committed", journal["status"])

    def test_rollback_restores_all_thirteen_directories(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            home, transaction = self.build_fixture(temporary)
            execute_transaction(home, transaction)

            result = rollback_transaction(home, transaction)

            agents = home / ".agents" / "skills"
            for name in DIRECT_NAMES:
                self.assertTrue((agents / name).is_dir())
                self.assertFalse((agents / name).is_symlink())
                self.assertEqual(
                    f"common:{name}\n",
                    (agents / name / "SKILL.md").read_text("utf-8"),
                )
            self.assertEqual("rolled-back", result["status"])

    def test_execute_refuses_existing_transaction_root(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            home, transaction = self.build_fixture(temporary)
            transaction.mkdir()

            with self.assertRaises(FileExistsError):
                execute_transaction(home, transaction)


if __name__ == "__main__":
    unittest.main()
