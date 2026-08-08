#!/usr/bin/env python3
"""Reconcile Matt CC Switch source metadata to one exact, verified release.

This transaction intentionally does not write Skill payloads, enabled flags, or
consumer projections. It verifies those surfaces, updates only source-pin
metadata, and keeps an exact row journal for recovery.
"""

from __future__ import annotations

import argparse
from datetime import UTC, datetime
import json
import os
from pathlib import Path
import sqlite3
import time
from typing import Any, Iterable

try:
    from .build_mattpocock_skills_manifest_update_preview import (
        inventory_local_directory,
        manifest_inventory,
        snapshot_path,
    )
    from .update_matt_cc_manager_cohort import (
        OWNER,
        REPOSITORY,
        SKILL_COLUMNS,
        _canonical,
        _read_rows,
        _verify_release_binding,
        _write_journal,
        compute_cc_directory_hash,
        ensure_manager_quiesced,
    )
except ImportError:
    from build_mattpocock_skills_manifest_update_preview import (
        inventory_local_directory,
        manifest_inventory,
        snapshot_path,
    )
    from update_matt_cc_manager_cohort import (
        OWNER,
        REPOSITORY,
        SKILL_COLUMNS,
        _canonical,
        _read_rows,
        _verify_release_binding,
        _write_journal,
        compute_cc_directory_hash,
        ensure_manager_quiesced,
    )


PIN_COLUMNS = ("repo_branch", "readme_url", "updated_at")
CONSUMER_ROOTS = {
    "claude": Path(".claude") / "skills",
    "codex": Path(".codex") / "skills",
    "agents": Path(".agents") / "skills",
}


def _projection_snapshot(home: Path, names: Iterable[str]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for host, relative_root in CONSUMER_ROOTS.items():
        root = home / relative_root
        entries: dict[str, Any] = {}
        for name in sorted(names):
            path = root / name
            if path.is_symlink():
                entries[name] = {
                    "kind": "symlink",
                    "target": os.readlink(path),
                    "resolvedTarget": path.resolve(strict=True).as_posix(),
                }
            elif path.exists():
                entries[name] = {"kind": "unsupported-live-path"}
            else:
                entries[name] = {"kind": "absent"}
        result[host] = entries
    return result


def _verify_projection_topology(
    home: Path,
    rows: list[dict[str, Any]],
    snapshot: dict[str, Any],
) -> None:
    ssot = home / ".cc-switch" / "skills"
    for row in rows:
        name = str(row["directory"])
        desired = {
            "claude": bool(row["enabled_claude"]),
            "codex": bool(row["enabled_codex"]),
            "agents": bool(row["enabled_claude"] or row["enabled_codex"]),
        }
        for host, should_exist in desired.items():
            entry = snapshot[host][name]
            if should_exist:
                expected = (ssot / name).resolve(strict=True).as_posix()
                if entry.get("kind") != "symlink" or entry.get("resolvedTarget") != expected:
                    raise RuntimeError(f"{host} projection is not the CC Switch SSOT link: {name}")
            elif entry.get("kind") != "absent":
                raise RuntimeError(f"disabled {host} projection is unexpectedly present: {name}")


def _verify_payloads(
    home: Path,
    rows: list[dict[str, Any]],
    promoted_by_name: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    result: dict[str, Any] = {}
    ssot = home / ".cc-switch" / "skills"
    for row in rows:
        name = str(row["directory"])
        local = inventory_local_directory(ssot / name)
        if local is None or local.get("unsupported"):
            raise RuntimeError(f"live payload is missing or unsupported: {name}")
        if (
            local["newlineNormalizedTreeSha256"]
            != promoted_by_name[name]["newlineNormalizedTreeSha256"]
        ):
            raise RuntimeError(f"payload does not match exact release: {name}")
        computed_directory_hash = compute_cc_directory_hash(ssot / name)
        result[name] = {
            "treeSha256": local["treeSha256"],
            "newlineNormalizedTreeSha256": local["newlineNormalizedTreeSha256"],
            # Preserve CC Switch's opaque manager-owned field. Exact payload
            # identity is established independently by the Git-tree digest.
            "managerContentHash": row["content_hash"],
            "computedDirectoryHash": computed_directory_hash,
            "fileCount": local["fileCount"],
        }
    return result


def _update_pin_metadata(database: Path, rows: list[dict[str, Any]]) -> None:
    connection = sqlite3.connect(database)
    try:
        connection.execute("BEGIN IMMEDIATE")
        for row in rows:
            cursor = connection.execute(
                """
                UPDATE skills
                SET repo_branch = ?, readme_url = ?, updated_at = ?
                WHERE id = ? AND repo_owner = ? AND repo_name = ?
                """,
                (
                    row["repo_branch"],
                    row["readme_url"],
                    row["updated_at"],
                    row["id"],
                    OWNER,
                    REPOSITORY,
                ),
            )
            if cursor.rowcount != 1:
                raise RuntimeError(f"pin update did not match exactly one row: {row['id']}")
        connection.commit()
    except BaseException:
        connection.rollback()
        raise
    finally:
        connection.close()


def _target_rows(
    current_rows: list[dict[str, Any]],
    promoted_by_name: dict[str, dict[str, Any]],
    release_tag: str,
    updated_at: int,
) -> list[dict[str, Any]]:
    target: list[dict[str, Any]] = []
    for row in current_rows:
        result = dict(row)
        name = str(row["directory"])
        source_path = str(promoted_by_name[name]["sourcePath"])
        result["repo_branch"] = release_tag
        result["readme_url"] = (
            f"https://github.com/{OWNER}/{REPOSITORY}/blob/"
            f"{release_tag}/{source_path}/SKILL.md"
        )
        result["updated_at"] = updated_at
        target.append(result)
    return target


def _assert_only_pin_columns_changed(
    before: list[dict[str, Any]], target: list[dict[str, Any]]
) -> None:
    if len(before) != len(target):
        raise RuntimeError("target row count changed")
    for prior, after in zip(before, target, strict=True):
        for column in SKILL_COLUMNS:
            if column not in PIN_COLUMNS and prior[column] != after[column]:
                raise RuntimeError(f"non-pin column changed: {column}")


def reconcile_exact_pin(
    *,
    home: Path,
    source_git: Path,
    release_commit: str,
    release_tag: str,
    transaction_root: Path,
    expected_names: tuple[str, ...],
    require_manager_quiesced: bool = True,
    updated_at: int | None = None,
    failure_point: str | None = None,
) -> dict[str, Any]:
    """Verify exact payload identity, then update only exact-source metadata."""

    if require_manager_quiesced:
        ensure_manager_quiesced()
    home = Path(home).resolve(strict=True)
    source_git = Path(source_git).resolve(strict=True)
    cc_home = home / ".cc-switch"
    backups = (cc_home / "skill-backups").resolve(strict=True)
    transaction_root = Path(transaction_root).resolve(strict=False)
    if transaction_root.parent != backups:
        raise ValueError("transaction root must be a direct child of skill-backups")
    if transaction_root.exists() or transaction_root.is_symlink():
        raise FileExistsError(f"transaction root already exists: {transaction_root}")

    _verify_release_binding(source_git, release_tag, release_commit)
    _, promoted = manifest_inventory(source_git, release_commit)
    promoted_by_name = {str(item["name"]): item for item in promoted}
    if set(promoted_by_name) != set(expected_names):
        raise RuntimeError("release manifest cohort does not match the expected names")

    database = cc_home / "cc-switch.db"
    current_rows = _read_rows(database)
    if {str(row["directory"]) for row in current_rows} != set(expected_names):
        raise RuntimeError("live Matt manager cohort drifted")
    if any(row["repo_branch"] not in {"main", release_tag} for row in current_rows):
        raise RuntimeError("live Matt source metadata has an unexpected branch or tag")

    payloads_before = _verify_payloads(home, current_rows, promoted_by_name)
    projections_before = _projection_snapshot(home, expected_names)
    _verify_projection_topology(home, current_rows, projections_before)
    ssot_before = snapshot_path(cc_home / "skills")

    timestamp = int(time.time()) if updated_at is None else updated_at
    target_rows = _target_rows(current_rows, promoted_by_name, release_tag, timestamp)
    _assert_only_pin_columns_changed(current_rows, target_rows)
    if current_rows == target_rows:
        return {
            "status": "already-aligned",
            "targetCount": len(target_rows),
            "releaseTag": release_tag,
            "releaseCommit": release_commit,
        }

    transaction_root.mkdir()
    journal: dict[str, Any] = {
        "schema": 1,
        "status": "prepared",
        "createdAt": datetime.now(UTC).isoformat(),
        "source": {
            "owner": OWNER,
            "repository": REPOSITORY,
            "releaseTag": release_tag,
            "releaseCommit": release_commit,
        },
        "before": {
            "rows": current_rows,
            "rowsSha256": _canonical(current_rows),
            "payloads": payloads_before,
            "ssotSnapshot": ssot_before,
            "projections": projections_before,
        },
        "target": {
            "rows": target_rows,
            "rowsSha256": _canonical(target_rows),
        },
        "changedColumns": list(PIN_COLUMNS),
        "payloadsWritten": False,
        "projectionsWritten": False,
        "rawDatabaseCopied": False,
        "thirdPartyScriptExecutions": 0,
    }
    _write_journal(transaction_root / "journal.json", journal)

    try:
        _update_pin_metadata(database, target_rows)
        journal["status"] = "database-committed"
        _write_journal(transaction_root / "journal.json", journal)
        if failure_point == "after-database-commit":
            raise RuntimeError("injected-after-database-commit")

        observed_rows = _read_rows(database)
        if _canonical(observed_rows) != _canonical(target_rows):
            raise RuntimeError("post-commit Matt rows do not match the exact target")
        if snapshot_path(cc_home / "skills") != ssot_before:
            raise RuntimeError("SSOT changed during metadata-only reconciliation")
        projections_after = _projection_snapshot(home, expected_names)
        if projections_after != projections_before:
            raise RuntimeError("consumer projections changed during metadata-only reconciliation")
        _verify_payloads(home, observed_rows, promoted_by_name)
        _verify_projection_topology(home, observed_rows, projections_after)
    except BaseException as failure:
        rollback_errors: list[str] = []
        try:
            _update_pin_metadata(database, current_rows)
        except BaseException as rollback_error:
            rollback_errors.append(str(rollback_error))
        journal["status"] = "rollback-failed" if rollback_errors else "rolled-back-after-error"
        journal["failure"] = f"{type(failure).__name__}: {failure}"
        journal["rollbackErrors"] = rollback_errors
        journal["rolledBackAt"] = datetime.now(UTC).isoformat()
        _write_journal(transaction_root / "journal.json", journal)
        if rollback_errors:
            raise RuntimeError(
                f"pin reconciliation failed and rollback was incomplete: {rollback_errors}"
            ) from failure
        raise

    journal["status"] = "committed"
    journal["committedAt"] = datetime.now(UTC).isoformat()
    journal["after"] = {
        "rowsSha256": _canonical(_read_rows(database)),
        "ssotSnapshot": snapshot_path(cc_home / "skills"),
        "projections": _projection_snapshot(home, expected_names),
    }
    _write_journal(transaction_root / "journal.json", journal)
    return {
        "status": "committed",
        "transactionRoot": transaction_root.as_posix(),
        "targetCount": len(target_rows),
        "releaseTag": release_tag,
        "releaseCommit": release_commit,
        "changedColumns": list(PIN_COLUMNS),
        "payloadsWritten": False,
        "projectionsWritten": False,
    }


def rollback_exact_pin(
    *, home: Path, transaction_root: Path, require_manager_quiesced: bool = True
) -> dict[str, Any]:
    """Restore the three source-pin columns from one committed journal."""

    if require_manager_quiesced:
        ensure_manager_quiesced()
    home = Path(home).resolve(strict=True)
    backups = (home / ".cc-switch" / "skill-backups").resolve(strict=True)
    transaction_root = Path(transaction_root).resolve(strict=True)
    if transaction_root.parent != backups:
        raise ValueError("transaction root must be a direct child of skill-backups")
    journal_path = transaction_root / "journal.json"
    journal = json.loads(journal_path.read_text(encoding="utf-8"))
    if journal.get("status") != "committed":
        raise ValueError("only a committed pin transaction can be rolled back")
    database = home / ".cc-switch" / "cc-switch.db"
    if _canonical(_read_rows(database)) != journal["target"]["rowsSha256"]:
        raise RuntimeError("current Matt rows no longer match the committed target")
    _update_pin_metadata(database, journal["before"]["rows"])
    if _canonical(_read_rows(database)) != journal["before"]["rowsSha256"]:
        raise RuntimeError("rollback verification failed")
    journal["status"] = "rolled-back"
    journal["rolledBackAt"] = datetime.now(UTC).isoformat()
    _write_journal(journal_path, journal)
    return {"status": "rolled-back", "transactionRoot": transaction_root.as_posix()}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--home", type=Path, required=True)
    parser.add_argument("--source-git", type=Path, required=True)
    parser.add_argument("--release-commit", required=True)
    parser.add_argument("--release-tag", required=True)
    parser.add_argument("--transaction-root", type=Path, required=True)
    parser.add_argument("--expected-name", action="append", required=True)
    args = parser.parse_args()
    result = reconcile_exact_pin(
        home=args.home,
        source_git=args.source_git,
        release_commit=args.release_commit,
        release_tag=args.release_tag,
        transaction_root=args.transaction_root,
        expected_names=tuple(args.expected_name),
    )
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
