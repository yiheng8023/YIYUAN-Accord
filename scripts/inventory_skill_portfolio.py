#!/usr/bin/env python3
"""Build a read-only local Skill portfolio inventory.

The inventory intentionally reads only Skill names, link targets, top-level
SKILL.md hashes, selected non-secret CC Switch settings, and Skill database
metadata. It never changes CC Switch, Agent homes, links, or the database.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sqlite3
from pathlib import Path
from typing import Any


ROOT_NAMES = {
    "ccSwitch": ".cc-switch/skills",
    "agents": ".agents/skills",
    "claude": ".claude/skills",
    "codex": ".codex/skills",
}
SAFE_SETTINGS = (
    "backupRetainCount",
    "skillStorageLocation",
    "skillSyncMethod",
    "visibleApps",
)


def link_kind(path: Path) -> str:
    if os.path.islink(path):
        return "symlink"
    if hasattr(os.path, "isjunction") and os.path.isjunction(path):
        return "junction"
    return "physical"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    digest.update(path.read_bytes())
    return digest.hexdigest()


def inspect_root(root: Path) -> dict[str, Any]:
    if not root.is_dir():
        return {"path": str(root), "exists": False, "entries": {}}

    entries: dict[str, dict[str, Any]] = {}
    for path in sorted(root.iterdir(), key=lambda item: item.name.casefold()):
        kind = link_kind(path)
        if not path.is_dir() and kind == "physical":
            continue
        skill_file = path / "SKILL.md"
        has_skill = skill_file.is_file()
        entries[path.name] = {
            "kind": kind,
            "target": str(path.resolve(strict=False)) if kind != "physical" else None,
            "skillMd": has_skill,
            "skillMdSha256": sha256(skill_file) if has_skill else None,
        }

    return {
        "path": str(root),
        "exists": True,
        "counts": {
            "topLevelDirectories": len(entries),
            "physical": sum(item["kind"] == "physical" for item in entries.values()),
            "symlink": sum(item["kind"] == "symlink" for item in entries.values()),
            "junction": sum(item["kind"] == "junction" for item in entries.values()),
            "resolvableSkillMd": sum(item["skillMd"] for item in entries.values()),
        },
        "entries": entries,
    }


def inspect_database(database: Path, roots: dict[str, dict[str, Any]]) -> dict[str, Any]:
    if not database.is_file():
        return {"path": str(database), "exists": False}

    connection = sqlite3.connect(f"file:{database}?mode=ro", uri=True)
    try:
        rows = connection.execute(
            "select name,directory,repo_owner,repo_name,enabled_claude,"
            "enabled_codex,enabled_gemini,enabled_opencode,enabled_hermes "
            "from skills"
        ).fetchall()
        repos = connection.execute(
            "select owner,name,branch,enabled from skill_repos order by owner,name"
        ).fetchall()
    finally:
        connection.close()

    enabled_columns = ("claude", "codex", "gemini", "opencode", "hermes")
    enabled = {
        name: sum(bool(row[4 + index]) for row in rows)
        for index, name in enumerate(enabled_columns)
    }
    duplicates: dict[str, int] = {}
    for name, *_ in rows:
        duplicates[name] = duplicates.get(name, 0) + 1

    root_presence: dict[str, dict[str, int]] = {}
    for root_name, root_record in roots.items():
        entries = root_record.get("entries", {})
        directories = [row[1] for row in rows if row[1]]
        root_presence[root_name] = {
            "databaseRowsWithDirectory": sum(directory in entries for directory in directories),
            "databaseRowsWithResolvableSkillMd": sum(
                bool(entries.get(directory, {}).get("skillMd"))
                for directory in directories
            ),
        }

    return {
        "path": str(database),
        "exists": True,
        "rows": len(rows),
        "distinctNames": len({row[0] for row in rows}),
        "enabled": enabled,
        "duplicateNames": {
            name: count for name, count in sorted(duplicates.items()) if count > 1
        },
        "repositories": [
            {"owner": owner, "name": name, "branch": branch, "enabled": bool(enabled_flag)}
            for owner, name, branch, enabled_flag in repos
        ],
        "rootPresence": root_presence,
    }


def inspect_settings(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {"path": str(path), "exists": False, "selected": {}}
    document = json.loads(path.read_text(encoding="utf-8"))
    return {
        "path": str(path),
        "exists": True,
        "selected": {key: document.get(key) for key in SAFE_SETTINGS},
    }


def inspect_backups(root: Path) -> dict[str, Any]:
    if not root.is_dir():
        return {"path": str(root), "exists": False}
    paths = list(root.rglob("*"))
    files = [path for path in paths if path.is_file()]
    return {
        "path": str(root),
        "exists": True,
        "topLevelEntries": len(list(root.iterdir())),
        "directories": sum(path.is_dir() for path in paths),
        "files": len(files),
        "bytes": sum(path.stat().st_size for path in files),
    }


def build_inventory(home: Path, database: Path | None = None) -> dict[str, Any]:
    roots = {
        name: inspect_root(home / relative)
        for name, relative in ROOT_NAMES.items()
    }
    all_names = sorted(
        set().union(*(set(record.get("entries", {})) for record in roots.values()))
    )
    collisions = []
    for name in all_names:
        hashes = {
            root_name: record["entries"][name]["skillMdSha256"]
            for root_name, record in roots.items()
            if name in record.get("entries", {})
            and record["entries"][name]["skillMdSha256"]
        }
        if len(set(hashes.values())) > 1:
            collisions.append({"name": name, "hashes": hashes})

    missing = {
        root_name: sorted(
            name
            for name, item in record.get("entries", {}).items()
            if not item["skillMd"]
        )
        for root_name, record in roots.items()
    }
    db_path = database or home / ".cc-switch/cc-switch.db"
    return {
        "schema": 1,
        "mode": "read-only-local-inventory",
        "roots": roots,
        "missingOrUnresolvedSkillMd": missing,
        "sameNameDifferentSkillMdHash": collisions,
        "database": inspect_database(db_path, roots),
        "settings": inspect_settings(home / ".cc-switch/settings.json"),
        "skillBackups": inspect_backups(home / ".cc-switch/skill-backups"),
        "claimBoundary": {
            "provesLiveInvocation": False,
            "provesCrossDeviceEquality": False,
            "authorizesRepairOrCleanup": False,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--home", type=Path, default=Path.home())
    parser.add_argument("--cc-db", type=Path)
    parser.add_argument("--compact", action="store_true")
    args = parser.parse_args()
    inventory = build_inventory(args.home, args.cc_db)
    print(
        json.dumps(
            inventory,
            ensure_ascii=False,
            indent=None if args.compact else 2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
