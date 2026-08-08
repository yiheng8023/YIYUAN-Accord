#!/usr/bin/env python3
"""Build a privacy-minimized, read-only inventory of disabled CC consumers."""

from __future__ import annotations

import argparse
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import sqlite3
from typing import Any


OWNER = "mattpocock"
REPOSITORY = "skills"
ROOTS = {
    "gemini": Path(".gemini") / "skills",
    "grokbuild": Path(".grok") / "skills",
    "opencode": Path(".config") / "opencode" / "skills",
    "hermes": Path(".hermes") / "skills",
}
ENABLED_COLUMNS = {host: f"enabled_{host}" for host in ROOTS}


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _canonical_digest(value: Any) -> str:
    encoded = json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _kind(path: Path) -> str:
    if path.is_symlink():
        return "symlink"
    if hasattr(os.path, "isjunction") and os.path.isjunction(path):
        return "junction"
    if path.is_dir():
        return "directory"
    return "other"


def _inspect_root(home: Path, host: str, names: set[str]) -> dict[str, Any]:
    root = home / ROOTS[host]
    entries = list(root.iterdir()) if root.is_dir() else []
    matt_entries: list[dict[str, Any]] = []
    ssot = home / ".cc-switch" / "skills"
    for path in sorted(entries, key=lambda item: item.name.casefold()):
        if path.name not in names:
            continue
        kind = _kind(path)
        matt_entries.append(
            {
                "name": path.name,
                "kind": kind,
                "targetsCcSwitchSsot": (
                    kind in {"symlink", "junction"}
                    and path.resolve(strict=False)
                    == (ssot / path.name).resolve(strict=False)
                ),
            }
        )
    return {
        "host": host,
        "path": f"~/{ROOTS[host].as_posix()}",
        "exists": root.is_dir(),
        "topLevelEntryCount": len(entries),
        "nonMattEntryCount": len(entries) - len(matt_entries),
        "nonMattNamesDisclosed": False,
        "mattEntryCount": len(matt_entries),
        "mattEntries": matt_entries,
    }


def _read_rows(database: Path) -> list[dict[str, Any]]:
    columns = ["directory", *ENABLED_COLUMNS.values()]
    connection = sqlite3.connect(f"{database.resolve().as_uri()}?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    try:
        connection.execute("PRAGMA query_only = ON")
        return [
            dict(row)
            for row in connection.execute(
                f"SELECT {', '.join(columns)} FROM skills "
                "WHERE repo_owner = ? AND repo_name = ? ORDER BY directory",
                (OWNER, REPOSITORY),
            )
        ]
    finally:
        connection.close()


def build_report(home: Path, observed_at: str) -> dict[str, Any]:
    parsed = datetime.fromisoformat(observed_at)
    if parsed.tzinfo is None:
        raise ValueError("observed-at must include an explicit UTC offset")
    home = Path(home).resolve(strict=True)
    database = home / ".cc-switch" / "cc-switch.db"
    if not database.is_file():
        raise FileNotFoundError(database)

    database_before = _sha256_file(database)
    rows = _read_rows(database)
    names = {str(row["directory"]) for row in rows}
    roots_before = [_inspect_root(home, host, names) for host in ROOTS]
    roots_after = [_inspect_root(home, host, names) for host in ROOTS]
    database_after = _sha256_file(database)

    enabled = {
        host: sum(bool(row[column]) for row in rows)
        for host, column in ENABLED_COLUMNS.items()
    }
    stable = (
        database_before == database_after
        and _canonical_digest(roots_before) == _canonical_digest(roots_after)
    )
    clear = (
        stable
        and all(value == 0 for value in enabled.values())
        and all(root["mattEntryCount"] == 0 for root in roots_after)
    )
    return {
        "schema": 1,
        "status": (
            "read-only-disabled-consumer-roots-clear"
            if clear
            else "read-only-disabled-consumer-drift-observed"
        ),
        "observedAt": parsed.isoformat(timespec="seconds"),
        "sourceBinding": {
            "manager": "CC Switch",
            "rootMappingEvidence": (
                "registry/cc-switch-exact-upstream-sixteen-sequential-"
                "inactive-install-event-2026-08-04.json"
            ),
            "owner": OWNER,
            "repository": REPOSITORY,
        },
        "privacyBoundary": {
            "nonMattNamesReadForIdentity": False,
            "nonMattNamesDisclosed": False,
            "skillBodiesRead": False,
            "settingsRead": False,
            "accountDataRead": False,
        },
        "database": {
            "path": "~/.cc-switch/cc-switch.db",
            "readOnly": True,
            "mattRowCount": len(rows),
            "enabledMattByHost": enabled,
            "sha256Before": database_before,
            "sha256After": database_after,
        },
        "roots": roots_after,
        "observationStable": stable,
        "allDisabledRootsFreeOfMattProjections": all(
            root["mattEntryCount"] == 0 for root in roots_after
        ),
        "executionCounters": {
            "databaseWrites": 0,
            "consumerWrites": 0,
            "managerInvocations": 0,
            "thirdPartyScripts": 0,
            "modelCalls": 0,
            "accountReads": 0,
        },
        "claimBoundary": {
            "disabledFlagsAtObservationProved": all(
                value == 0 for value in enabled.values()
            ),
            "rootPresenceAtObservationProved": True,
            "mattProjectionAbsenceAtObservationProved": all(
                root["mattEntryCount"] == 0 for root in roots_after
            ),
            "hostInstalledProved": False,
            "hostLoaderInvocationProved": False,
            "instructionDeliveryProved": False,
            "backupRestoreProved": False,
            "crossDeviceConvergenceProved": False,
            "behaviorProved": False,
            "valueProved": False,
            "productionReadinessProved": False,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--home", type=Path, required=True)
    parser.add_argument("--observed-at", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    home = args.home.resolve(strict=True)
    output = args.output.resolve(strict=False)
    protected = [home / ".cc-switch", *(home / relative for relative in ROOTS.values())]
    for root in protected:
        resolved = root.resolve(strict=False)
        if output == resolved or resolved in output.parents:
            raise ValueError("output must stay outside inspected capability roots")
    report = build_report(home, args.observed_at)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
