#!/usr/bin/env python3
"""Apply one recoverable, exact-release Matt Skill manager transaction."""

from __future__ import annotations

from datetime import UTC, datetime
import csv
import hashlib
import json
import os
from pathlib import Path
import shutil
import sqlite3
import subprocess
import time
from typing import Any, Iterable

try:
    from .build_mattpocock_skills_manifest_update_preview import (
        git,
        manifest_inventory,
    )
except ImportError:
    from build_mattpocock_skills_manifest_update_preview import git, manifest_inventory


OWNER = "mattpocock"
REPOSITORY = "skills"
APPS = ("claude", "codex", "gemini", "opencode", "hermes", "grokbuild")
SKILL_COLUMNS = (
    "id",
    "name",
    "description",
    "directory",
    "repo_owner",
    "repo_name",
    "repo_branch",
    "readme_url",
    "enabled_claude",
    "enabled_codex",
    "enabled_gemini",
    "enabled_opencode",
    "enabled_hermes",
    "installed_at",
    "content_hash",
    "updated_at",
    "enabled_grokbuild",
)


def compute_cc_directory_hash(root: Path) -> str:
    """Match CC Switch's non-hidden relative-path/content SHA-256 contract."""

    files = sorted(
        path
        for path in root.rglob("*")
        if path.is_file()
        and not any(part.startswith(".") for part in path.relative_to(root).parts)
    )
    digest = hashlib.sha256()
    for path in files:
        relative = path.relative_to(root).as_posix().encode("utf-8")
        digest.update(relative)
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def _canonical(value: Any) -> str:
    encoded = json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _running_manager_process_ids() -> list[int]:
    if os.name == "nt":
        result = subprocess.run(
            [
                "tasklist",
                "/FI",
                "IMAGENAME eq cc-switch.exe",
                "/FO",
                "CSV",
                "/NH",
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        process_ids: list[int] = []
        for row in csv.reader(result.stdout.splitlines()):
            if len(row) >= 2 and row[0].lower() == "cc-switch.exe":
                process_ids.append(int(row[1]))
        return process_ids
    result = subprocess.run(
        ["pgrep", "-x", "cc-switch"], capture_output=True, text=True
    )
    if result.returncode not in {0, 1}:
        raise RuntimeError("unable to determine whether CC Switch is running")
    return [int(line) for line in result.stdout.splitlines() if line.strip()]


def ensure_manager_quiesced(process_ids: Iterable[int] | None = None) -> None:
    observed = list(_running_manager_process_ids() if process_ids is None else process_ids)
    if observed:
        raise RuntimeError(f"CC Switch is still running: {observed}")


def _write_journal(path: Path, value: dict[str, Any]) -> None:
    temporary = path.with_suffix(".json.partial")
    with temporary.open("w", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2, sort_keys=True)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)


def _parse_frontmatter(path: Path, fallback: str) -> tuple[str, str | None]:
    text = path.read_text(encoding="utf-8-sig")
    parts = text.split("---", 2)
    if len(parts) < 3:
        return fallback, None
    values: dict[str, str] = {}
    for line in parts[1].splitlines():
        if line[:1].isspace() or ":" not in line:
            continue
        key, raw = line.split(":", 1)
        if key.strip() not in {"name", "description"}:
            continue
        value = raw.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
            value = value[1:-1]
        values[key.strip()] = value
    return values.get("name") or fallback, values.get("description") or None


def _materialize_release(
    source_git: Path,
    release_commit: str,
    target_root: Path,
    expected_target_names: tuple[str, ...],
) -> tuple[list[dict[str, Any]], dict[str, str]]:
    _, promoted = manifest_inventory(source_git, release_commit)
    by_name = {str(item["name"]): item for item in promoted}
    if set(by_name) != set(expected_target_names):
        raise ValueError("release manifest target cohort mismatch")
    hashes: dict[str, str] = {}
    for name in sorted(by_name):
        record = by_name[name]
        destination = target_root / name
        destination.mkdir(parents=True)
        for item in record["files"]:
            if item["mode"] not in {"100644", "100755"}:
                raise ValueError(f"unsupported Git mode for {name}: {item['mode']}")
            relative = Path(*str(item["path"]).split("/"))
            output = destination / relative
            if output.resolve(strict=False).parent != destination.resolve() and not str(
                output.resolve(strict=False)
            ).startswith(str(destination.resolve()) + os.sep):
                raise ValueError(f"release path escaped target: {item['path']}")
            output.parent.mkdir(parents=True, exist_ok=True)
            content = git(source_git, "cat-file", "blob", item["gitBlob"], text=False)
            assert isinstance(content, bytes)
            if hashlib.sha256(content).hexdigest() != item["sha256"]:
                raise RuntimeError(f"Git blob digest mismatch: {name}/{item['path']}")
            output.write_bytes(content)
        hashes[name] = compute_cc_directory_hash(destination)
    return promoted, hashes


def _verify_release_binding(
    source_git: Path, release_tag: str, release_commit: str
) -> None:
    try:
        peeled = git(source_git, "rev-parse", f"{release_tag}^{{commit}}")
    except subprocess.CalledProcessError as error:
        raise ValueError("release tag is missing or cannot be peeled") from error
    if peeled != release_commit:
        raise ValueError("release tag does not peel to the requested commit")


def _read_rows(database: Path, *, all_rows: bool = False) -> list[dict[str, Any]]:
    connection = sqlite3.connect(database)
    connection.row_factory = sqlite3.Row
    try:
        query = f"SELECT {', '.join(SKILL_COLUMNS)} FROM skills"
        parameters: tuple[str, ...] = ()
        if not all_rows:
            query += " WHERE repo_owner = ? AND repo_name = ?"
            parameters = (OWNER, REPOSITORY)
        query += " ORDER BY directory"
        return [dict(row) for row in connection.execute(query, parameters)]
    finally:
        connection.close()


def _replace_rows(database: Path, rows: list[dict[str, Any]]) -> None:
    connection = sqlite3.connect(database)
    try:
        connection.execute("BEGIN IMMEDIATE")
        connection.execute(
            "DELETE FROM skills WHERE repo_owner = ? AND repo_name = ?",
            (OWNER, REPOSITORY),
        )
        placeholders = ", ".join("?" for _ in SKILL_COLUMNS)
        columns = ", ".join(SKILL_COLUMNS)
        connection.executemany(
            f"INSERT INTO skills ({columns}) VALUES ({placeholders})",
            [[row[column] for column in SKILL_COLUMNS] for row in rows],
        )
        connection.commit()
    except BaseException:
        connection.rollback()
        raise
    finally:
        connection.close()


def _target_rows(
    promoted: list[dict[str, Any]],
    prepared_root: Path,
    hashes: dict[str, str],
    current_rows: list[dict[str, Any]],
    release_tag: str,
) -> list[dict[str, Any]]:
    current = {str(row["directory"]): row for row in current_rows}
    now = int(time.time())
    rows: list[dict[str, Any]] = []
    for item in sorted(promoted, key=lambda value: str(value["name"])):
        name = str(item["name"])
        existing = current.get(name)
        title, description = _parse_frontmatter(prepared_root / name / "SKILL.md", name)
        enabled = {
            app: int(bool(existing and existing[f"enabled_{app}"]))
            for app in APPS
        }
        if existing is None and name != "wizard":
            enabled["claude"] = 1
            enabled["codex"] = 1
        if name == "wizard":
            enabled = {app: 0 for app in APPS}
        source_path = str(item["sourcePath"])
        rows.append(
            {
                "id": f"{OWNER}/{REPOSITORY}:{source_path}",
                "name": title,
                "description": description,
                "directory": name,
                "repo_owner": OWNER,
                "repo_name": REPOSITORY,
                "repo_branch": release_tag,
                "readme_url": (
                    f"https://github.com/{OWNER}/{REPOSITORY}/blob/"
                    f"{release_tag}/{source_path}/SKILL.md"
                ),
                "enabled_claude": enabled["claude"],
                "enabled_codex": enabled["codex"],
                "enabled_gemini": enabled["gemini"],
                "enabled_opencode": enabled["opencode"],
                "enabled_hermes": enabled["hermes"],
                "installed_at": existing["installed_at"] if existing else now,
                "content_hash": hashes[name],
                "updated_at": now,
                "enabled_grokbuild": enabled["grokbuild"],
            }
        )
    return rows


def _projection_roots(home: Path) -> dict[str, Path]:
    return {
        "claude": home / ".claude" / "skills",
        "codex": home / ".codex" / "skills",
        "agents": home / ".agents" / "skills",
    }


def _snapshot_projections(home: Path, names: Iterable[str]) -> dict[str, Any]:
    snapshot: dict[str, Any] = {}
    for label, root in _projection_roots(home).items():
        rows: dict[str, Any] = {}
        for name in names:
            path = root / name
            if path.is_symlink():
                rows[name] = {"kind": "symlink", "target": os.readlink(path)}
            elif path.exists():
                rows[name] = {"kind": "unsupported-live-path"}
            else:
                rows[name] = {"kind": "absent"}
        snapshot[label] = rows
    return snapshot


def _sync_projections(home: Path, rows: list[dict[str, Any]], names: Iterable[str]) -> None:
    ssot = home / ".cc-switch" / "skills"
    by_name = {str(row["directory"]): row for row in rows}
    for label, root in _projection_roots(home).items():
        root.mkdir(parents=True, exist_ok=True)
        if label == "agents":
            desired = {
                name
                for name, row in by_name.items()
                if row["enabled_claude"] or row["enabled_codex"]
            }
        else:
            desired = {
                name for name, row in by_name.items() if row[f"enabled_{label}"]
            }
        for name in sorted(set(names)):
            path = root / name
            if path.is_symlink():
                if name in desired and path.resolve(strict=True) == (ssot / name).resolve(
                    strict=True
                ):
                    continue
                path.unlink()
            elif path.exists():
                raise RuntimeError(f"refusing to replace non-link projection: {path}")
            if name in desired:
                os.symlink(ssot / name, path, target_is_directory=True)


def _restore_projections(home: Path, snapshot: dict[str, Any]) -> None:
    for label, rows in snapshot.items():
        root = _projection_roots(home)[label]
        root.mkdir(parents=True, exist_ok=True)
        for name, prior in rows.items():
            path = root / name
            if path.is_symlink():
                path.unlink()
            elif path.exists():
                raise RuntimeError(f"cannot restore over non-link projection: {path}")
            if prior["kind"] == "symlink":
                os.symlink(prior["target"], path, target_is_directory=True)


def _restore_ssot(ssot: Path, transaction_root: Path) -> None:
    original = transaction_root / "original-skills"
    if not original.is_dir():
        return
    failed_new = transaction_root / "failed-new-skills"
    if failed_new.exists() or failed_new.is_symlink():
        raise RuntimeError("failed-new-skills already exists")
    if ssot.exists() or ssot.is_symlink():
        os.replace(ssot, failed_new)
    os.replace(original, ssot)


def execute_transaction(
    *,
    home: Path,
    source_git: Path,
    release_commit: str,
    release_tag: str,
    transaction_root: Path,
    expected_live_names: tuple[str, ...],
    expected_target_names: tuple[str, ...],
    require_manager_quiesced: bool = True,
    failure_point: str | None = None,
) -> dict[str, Any]:
    if require_manager_quiesced:
        ensure_manager_quiesced()
    home = home.resolve(strict=True)
    cc_home = home / ".cc-switch"
    backups = (cc_home / "skill-backups").resolve(strict=True)
    transaction_root = transaction_root.resolve(strict=False)
    if transaction_root.parent != backups:
        raise ValueError("transaction root must be a direct child of skill-backups")
    if transaction_root.exists() or transaction_root.is_symlink():
        raise FileExistsError(f"transaction root already exists: {transaction_root}")
    database = cc_home / "cc-switch.db"
    ssot = cc_home / "skills"
    source_git = source_git.resolve(strict=True)
    _verify_release_binding(source_git, release_tag, release_commit)
    current_rows = _read_rows(database)
    if {str(row["directory"]) for row in current_rows} != set(expected_live_names):
        raise RuntimeError("live Matt manager cohort drifted")
    all_rows = _read_rows(database, all_rows=True)
    conflicts = {
        str(row["directory"])
        for row in all_rows
        if row["repo_owner"] != OWNER or row["repo_name"] != REPOSITORY
    } & set(expected_target_names)
    if conflicts:
        raise RuntimeError(f"target directories conflict with other manager rows: {conflicts}")

    transaction_root.mkdir()
    prepared = transaction_root / "prepared-release"
    prepared.mkdir()
    promoted, hashes = _materialize_release(
        source_git,
        release_commit,
        prepared,
        expected_target_names,
    )
    target_rows = _target_rows(promoted, prepared, hashes, current_rows, release_tag)
    names = tuple(sorted(set(expected_live_names) | set(expected_target_names)))
    projection_before = _snapshot_projections(home, names)
    if any(
        row["kind"] == "unsupported-live-path"
        for root in projection_before.values()
        for row in root.values()
    ):
        raise RuntimeError("one managed projection is not a symlink")

    staged_ssot = transaction_root / "staged-skills"
    shutil.copytree(ssot, staged_ssot, symlinks=True)
    for name in expected_live_names:
        target = staged_ssot / name
        if target.is_symlink():
            target.unlink()
        elif target.exists():
            shutil.rmtree(target)
    for name in expected_target_names:
        shutil.copytree(prepared / name, staged_ssot / name)

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
            "projections": projection_before,
        },
        "target": {
            "rows": target_rows,
            "rowsSha256": _canonical(target_rows),
            "names": list(expected_target_names),
            "wizardEnabled": False,
        },
        "rawDatabaseCopied": False,
        "thirdPartyScriptExecutions": 0,
    }
    _write_journal(transaction_root / "journal.json", journal)

    original_ssot = transaction_root / "original-skills"
    try:
        os.replace(ssot, original_ssot)
        os.replace(staged_ssot, ssot)
        journal["status"] = "ssot-swapped"
        _write_journal(transaction_root / "journal.json", journal)
        if failure_point == "after-ssot-swap":
            raise RuntimeError("injected-after-ssot-swap")
        _replace_rows(database, target_rows)
        journal["status"] = "database-committed"
        _write_journal(transaction_root / "journal.json", journal)
        if failure_point == "after-database-commit":
            raise RuntimeError("injected-after-database-commit")
        _sync_projections(home, target_rows, names)
        if failure_point == "after-projection-update":
            raise RuntimeError("injected-after-projection-update")
    except BaseException as failure:
        rollback_errors: list[str] = []
        for action in (
            lambda: _restore_projections(home, projection_before),
            lambda: _replace_rows(database, current_rows),
            lambda: _restore_ssot(ssot, transaction_root),
        ):
            try:
                action()
            except BaseException as rollback_error:
                rollback_errors.append(str(rollback_error))
        journal["status"] = (
            "rollback-failed" if rollback_errors else "rolled-back-after-error"
        )
        journal["failure"] = f"{type(failure).__name__}: {failure}"
        journal["rollbackErrors"] = rollback_errors
        journal["rolledBackAt"] = datetime.now(UTC).isoformat()
        _write_journal(transaction_root / "journal.json", journal)
        if rollback_errors:
            raise RuntimeError(
                f"transaction failed and rollback was incomplete: {rollback_errors}"
            ) from failure
        raise
    journal["status"] = "committed"
    journal["committedAt"] = datetime.now(UTC).isoformat()
    _write_journal(transaction_root / "journal.json", journal)
    return {
        "status": "committed",
        "transactionRoot": transaction_root.as_posix(),
        "targetCount": len(target_rows),
        "wizardEnabled": False,
    }


def rollback_transaction(
    *,
    home: Path,
    transaction_root: Path,
    require_manager_quiesced: bool = True,
) -> dict[str, Any]:
    if require_manager_quiesced:
        ensure_manager_quiesced()
    home = home.resolve(strict=True)
    backups = (home / ".cc-switch" / "skill-backups").resolve(strict=True)
    transaction_root = transaction_root.resolve(strict=True)
    if transaction_root.parent != backups:
        raise ValueError("transaction root must be a direct child of skill-backups")
    journal_path = transaction_root / "journal.json"
    journal = json.loads(journal_path.read_text(encoding="utf-8"))
    if journal.get("status") != "committed":
        raise ValueError("only a committed transaction can be explicitly rolled back")
    database = home / ".cc-switch" / "cc-switch.db"
    ssot = home / ".cc-switch" / "skills"
    _restore_ssot(ssot, transaction_root)
    _replace_rows(database, journal["before"]["rows"])
    _restore_projections(home, journal["before"]["projections"])
    journal["status"] = "rolled-back"
    journal["rolledBackAt"] = datetime.now(UTC).isoformat()
    _write_journal(journal_path, journal)
    return {
        "status": "rolled-back",
        "transactionRoot": transaction_root.as_posix(),
    }
