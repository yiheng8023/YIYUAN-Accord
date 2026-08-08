from __future__ import annotations

import json
from pathlib import Path
import sqlite3
import tempfile
import unittest

from scripts.build_cc_switch_disabled_consumer_inventory import build_report


SCHEMA = """
CREATE TABLE skills (
    directory TEXT NOT NULL,
    repo_owner TEXT,
    repo_name TEXT,
    enabled_gemini INTEGER NOT NULL,
    enabled_grokbuild INTEGER NOT NULL,
    enabled_opencode INTEGER NOT NULL,
    enabled_hermes INTEGER NOT NULL
)
"""


def fixture(raw: str, *, enabled_gemini: int = 0) -> Path:
    home = Path(raw) / "home"
    cc = home / ".cc-switch"
    cc.mkdir(parents=True)
    database = cc / "cc-switch.db"
    connection = sqlite3.connect(database)
    try:
        connection.execute(SCHEMA)
        for name in ("alpha", "wizard"):
            connection.execute(
                "INSERT INTO skills VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    name,
                    "mattpocock",
                    "skills",
                    enabled_gemini if name == "alpha" else 0,
                    0,
                    0,
                    0,
                ),
            )
        connection.commit()
    finally:
        connection.close()
    return home


class BuildCcSwitchDisabledConsumerInventoryTests(unittest.TestCase):
    def test_absent_roots_and_zero_flags_are_clear_without_database_write(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            home = fixture(raw)

            report = build_report(home, "2026-08-08T17:00:00+08:00")

        self.assertEqual("read-only-disabled-consumer-roots-clear", report["status"])
        self.assertEqual(2, report["database"]["mattRowCount"])
        self.assertEqual({0}, set(report["database"]["enabledMattByHost"].values()))
        self.assertTrue(report["database"]["readOnly"])
        self.assertEqual(
            report["database"]["sha256Before"], report["database"]["sha256After"]
        )
        self.assertEqual(0, sum(root["mattEntryCount"] for root in report["roots"]))
        self.assertTrue(all(not root["exists"] for root in report["roots"]))
        self.assertTrue(all(value == 0 for value in report["executionCounters"].values()))

    def test_non_matt_names_are_counted_but_not_disclosed(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            home = fixture(raw)
            root = home / ".gemini" / "skills"
            (root / "private-local-name").mkdir(parents=True)

            report = build_report(home, "2026-08-08T17:00:00+08:00")

        rendered = json.dumps(report)
        gemini = next(root for root in report["roots"] if root["host"] == "gemini")
        self.assertEqual(1, gemini["topLevelEntryCount"])
        self.assertEqual(0, gemini["mattEntryCount"])
        self.assertNotIn("private-local-name", rendered)

    def test_matt_projection_or_enabled_flag_is_reported_as_drift(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            home = fixture(raw, enabled_gemini=1)
            root = home / ".hermes" / "skills" / "alpha"
            root.mkdir(parents=True)

            report = build_report(home, "2026-08-08T17:00:00+08:00")

        self.assertEqual(
            "read-only-disabled-consumer-drift-observed", report["status"]
        )
        self.assertEqual(1, report["database"]["enabledMattByHost"]["gemini"])
        hermes = next(root for root in report["roots"] if root["host"] == "hermes")
        self.assertEqual(["alpha"], [entry["name"] for entry in hermes["mattEntries"]])


if __name__ == "__main__":
    unittest.main()
