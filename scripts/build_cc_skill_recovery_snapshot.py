#!/usr/bin/env python3
"""Build and verify a secret-screened CC Switch Skill recovery snapshot.

The snapshot intentionally excludes CC Switch settings, provider/account data,
and the raw SQLite database. It contains:

* every physical Skill body in the CC Switch SSOT;
* every unique physical Skill body from ``~/.agents/skills``;
* the canonical portable contracts from ``codex-user-config``;
* every existing CC Skill-level backup, before retention rotation can affect it;
* safe, explicit Skill and Skill-repository database columns; and
* projection topology metadata for recovery diagnosis.

This is a recovery artifact, not an installer or a supported CC Switch restore
operation. It never mutates CC Switch or any Agent Skill root.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sqlite3
import tempfile
import zipfile
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath
from typing import Any


CONTRACTS = ("intent-contract", "capability-router", "closure-contract")
PROJECTION_ROOTS = {
    "ccSwitch": ".cc-switch/skills",
    "agents": ".agents/skills",
    "claude": ".claude/skills",
    "codex": ".codex/skills",
}
SECRET_PATTERNS = {
    "private-key": re.compile(rb"-----BEGIN [A-Z0-9 ]*PRIVATE KEY-----"),
    "openai-key": re.compile(rb"\bsk-(?:proj-|svcacct-)?[A-Za-z0-9_-]{20,}\b"),
    "github-token": re.compile(
        rb"\b(?:gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,})\b"
    ),
    "aws-access-key": re.compile(rb"\bAKIA[A-Z0-9]{16}\b"),
    "slack-token": re.compile(rb"\bxox[baprs]-[A-Za-z0-9-]{20,}\b"),
}
SENSITIVE_FILE_NAMES = {
    ".env",
    ".env.local",
    ".env.production",
    "cookies.json",
    "credentials.json",
    "id_ed25519",
    "id_rsa",
    "private.key",
    "secrets.json",
    "session.json",
    "tokens.json",
}
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


def sha256_bytes(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def link_kind(path: Path) -> str:
    if path.is_symlink():
        return "symlink"
    if hasattr(os.path, "isjunction") and os.path.isjunction(path):
        return "junction"
    return "physical"


def is_within(path: Path, roots: list[Path]) -> bool:
    resolved = path.resolve(strict=True)
    return any(resolved == root or resolved.is_relative_to(root) for root in roots)


def scan_for_secrets(content: bytes, archive_path: str) -> None:
    matches = [
        name for name, pattern in SECRET_PATTERNS.items() if pattern.search(content)
    ]
    if matches:
        labels = ", ".join(sorted(matches))
        raise ValueError(
            f"high-confidence secret pattern detected in {archive_path}: {labels}"
        )


def scan_member_name(archive_path: str) -> None:
    basename = PurePosixPath(archive_path).name.casefold()
    if basename in SENSITIVE_FILE_NAMES:
        raise ValueError(
            f"sensitive filename requires separate review and is not archived: "
            f"{archive_path}"
        )


def safe_database_export(database: Path) -> dict[str, Any]:
    connection = sqlite3.connect(f"file:{database}?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    try:
        available = {
            row[1] for row in connection.execute("pragma table_info(skills)")
        }
        missing = sorted(set(SKILL_COLUMNS) - available)
        if missing:
            raise ValueError(f"skills table is missing expected columns: {missing}")
        skills = [
            dict(row)
            for row in connection.execute(
                f"select {','.join(SKILL_COLUMNS)} from skills order by directory,id"
            )
        ]
        repositories = [
            dict(row)
            for row in connection.execute(
                "select owner,name,branch,enabled "
                "from skill_repos order by owner,name,branch"
            )
        ]
    finally:
        connection.close()
    return {
        "schema": 1,
        "source": "explicit-safe-columns-only",
        "excluded": [
            "settings.json",
            "raw-database",
            "provider-config",
            "account-data",
            "credentials",
        ],
        "skills": skills,
        "skillRepositories": repositories,
    }


def inspect_projection_root(root: Path) -> dict[str, Any]:
    if not root.is_dir():
        return {"exists": False, "entries": {}}
    entries: dict[str, Any] = {}
    for path in sorted(root.iterdir(), key=lambda item: item.name.casefold()):
        kind = link_kind(path)
        if kind == "physical" and not path.is_dir():
            continue
        skill_file = path / "SKILL.md"
        entries[path.name] = {
            "kind": kind,
            "resolvedTarget": str(path.resolve(strict=False))
            if kind != "physical"
            else None,
            "skillMdResolvable": skill_file.is_file(),
            "skillMdSha256": sha256_file(skill_file)
            if skill_file.is_file()
            else None,
        }
    return {
        "exists": True,
        "counts": {
            "topLevelEntries": len(entries),
            "resolvableSkillMd": sum(
                item["skillMdResolvable"] for item in entries.values()
            ),
            "brokenOrMissingSkillMd": sum(
                not item["skillMdResolvable"] for item in entries.values()
            ),
        },
        "entries": entries,
    }


def collect_tree(
    source: Path,
    archive_prefix: str,
    allowed_roots: list[Path],
) -> tuple[list[tuple[Path, str]], list[str], dict[str, Any]]:
    origin_kind = link_kind(source)
    if not source.is_dir():
        raise ValueError(f"required Skill tree is missing: {source}")
    resolved = source.resolve(strict=True)
    if not is_within(resolved, allowed_roots):
        raise ValueError(f"Skill tree resolves outside allowed roots: {source}")

    files: list[tuple[Path, str]] = []
    empty_directories: list[str] = []
    for current, directories, filenames in os.walk(resolved, followlinks=False):
        current_path = Path(current)
        for name in list(directories):
            child = current_path / name
            if link_kind(child) != "physical":
                raise ValueError(f"nested link/reparse point is not archived: {child}")
        relative_directory = current_path.relative_to(resolved)
        if not directories and not filenames:
            empty_directories.append(
                (PurePosixPath(archive_prefix) / relative_directory.as_posix()).as_posix()
                + "/"
            )
        for name in filenames:
            path = current_path / name
            if link_kind(path) != "physical":
                raise ValueError(f"linked file is not archived: {path}")
            relative = path.relative_to(resolved).as_posix()
            archive_path = (PurePosixPath(archive_prefix) / relative).as_posix()
            files.append((path, archive_path))
    return files, empty_directories, {
        "source": str(source),
        "originKind": origin_kind,
        "resolvedSource": str(resolved),
        "archivePrefix": archive_prefix,
        "fileCount": len(files),
        "emptyDirectoryCount": len(empty_directories),
    }


def validate_member_name(name: str) -> None:
    path = PurePosixPath(name)
    if path.is_absolute() or ".." in path.parts or "\\" in name:
        raise ValueError(f"unsafe archive member path: {name}")


def verify_archive(archive: Path, expected_files: dict[str, str]) -> dict[str, Any]:
    with zipfile.ZipFile(archive, "r") as bundle:
        names = bundle.namelist()
        if len(names) != len(set(names)):
            raise ValueError("archive contains duplicate member names")
        if len(names) != len({name.casefold() for name in names}):
            raise ValueError("archive contains case-insensitive member collision")
        for name in names:
            validate_member_name(name)
            if not name.endswith("/"):
                scan_member_name(name)
        payload_names = {
            name for name in names if not name.endswith("/") and name.startswith("payload/")
        }
        if payload_names != set(expected_files):
            raise ValueError("archive payload file set does not match manifest index")
        for name, expected_hash in expected_files.items():
            content = bundle.read(name)
            scan_for_secrets(content, name)
            if sha256_bytes(content) != expected_hash:
                raise ValueError(f"archive hash mismatch: {name}")

        with tempfile.TemporaryDirectory(prefix="cc-skill-recovery-verify-") as temp:
            destination = Path(temp)
            bundle.extractall(destination)
            for name, expected_hash in expected_files.items():
                if sha256_file(destination / Path(*PurePosixPath(name).parts)) != expected_hash:
                    raise ValueError(f"extracted hash mismatch: {name}")
    return {
        "archiveOpened": True,
        "memberPathsValidated": True,
        "payloadFileSetMatched": True,
        "archivePayloadHashesMatched": True,
        "archiveSecretRescanPassed": True,
        "extractedPayloadHashesMatched": True,
    }


def build_snapshot(
    home: Path,
    canonical_config: Path,
    output: Path,
) -> dict[str, Any]:
    output = output.resolve(strict=False)
    sidecar = output.with_suffix(".manifest.json")
    if output.exists() or sidecar.exists():
        raise FileExistsError(f"refusing to overwrite recovery artifact: {output}")
    output.parent.mkdir(parents=True, exist_ok=True)

    cc_root = (home / ".cc-switch/skills").resolve(strict=True)
    backups_root = (home / ".cc-switch/skill-backups").resolve(strict=True)
    agents_root = (home / ".agents/skills").resolve(strict=True)
    canonical_root = (canonical_config / "skills").resolve(strict=True)
    allowed_roots = [cc_root, backups_root, agents_root, canonical_root]
    database = home / ".cc-switch/cc-switch.db"
    if not database.is_file():
        raise ValueError(f"CC Switch database is missing: {database}")

    selections: list[tuple[Path, str]] = []
    cc_names = sorted(
        path.name
        for path in cc_root.iterdir()
        if path.is_dir() and (path / "SKILL.md").is_file()
    )
    for name in cc_names:
        selections.append((cc_root / name, f"payload/cc-switch-skills/{name}"))

    agents_names = sorted(
        path.name
        for path in agents_root.iterdir()
        if link_kind(path) == "physical" and (path / "SKILL.md").is_file()
    )
    required_agents = {
        *CONTRACTS,
        *(
            path.name
            for path in agents_root.iterdir()
            if path.name.startswith("lark-") and (path / "SKILL.md").is_file()
        ),
    }
    missing_required_agents = sorted(required_agents - set(agents_names))
    if missing_required_agents:
        raise ValueError(
            "required Agents unique bodies are not physical snapshot candidates: "
            f"{missing_required_agents}"
        )
    for name in agents_names:
        selections.append((agents_root / name, f"payload/agents-selected/{name}"))
    for name in CONTRACTS:
        selections.append(
            (
                canonical_root / name,
                f"payload/canonical-contracts/{name}",
            )
        )
    backup_ids = sorted(
        path.name
        for path in backups_root.iterdir()
        if link_kind(path) == "physical" and path.is_dir()
    )
    for backup_id in backup_ids:
        selections.append(
            (
                backups_root / backup_id,
                f"payload/cc-existing-backups/{backup_id}",
            )
        )

    collected: list[tuple[Path, str]] = []
    empty_directories: list[str] = []
    trees: list[dict[str, Any]] = []
    for source, prefix in selections:
        files, empties, tree = collect_tree(source, prefix, allowed_roots)
        collected.extend(files)
        empty_directories.extend(empties)
        trees.append(tree)

    database_export = safe_database_export(database)
    topology = {
        name: inspect_projection_root(home / relative)
        for name, relative in PROJECTION_ROOTS.items()
    }
    expected_files: dict[str, str] = {}
    for path, archive_path in collected:
        scan_member_name(archive_path)
        content = path.read_bytes()
        scan_for_secrets(content, archive_path)
        expected_files[archive_path] = sha256_bytes(content)

    metadata = {
        "schema": 1,
        "mode": "secret-screened-read-only-recovery-snapshot",
        "createdAt": datetime.now(UTC).isoformat(),
        "scope": {
            "ccSwitchSkillBodies": cc_names,
            "agentsSelectedBodies": agents_names,
            "canonicalContracts": list(CONTRACTS),
            "ccExistingBackups": backup_ids,
        },
        "trees": trees,
        "payloadIndex": expected_files,
        "emptyDirectories": sorted(empty_directories),
        "projectionTopology": topology,
        "databaseMetadata": database_export,
        "secretScan": {
            "patterns": sorted(SECRET_PATTERNS),
            "sensitiveFileNames": sorted(SENSITIVE_FILE_NAMES),
            "matches": 0,
            "settingsRead": False,
            "rawDatabaseCopied": False,
        },
        "claimBoundary": {
            "isSupportedCcRestoreOperation": False,
            "provesCcUninstallRestoreOnUserState": False,
            "includesSettingsOrCredentials": False,
            "authorizesMutation": False,
        },
    }
    metadata_bytes = json.dumps(
        metadata, ensure_ascii=False, indent=2, sort_keys=True
    ).encode("utf-8")
    scan_for_secrets(metadata_bytes, "metadata/snapshot.json")

    temporary = output.with_suffix(output.suffix + ".partial")
    try:
        with zipfile.ZipFile(
            temporary, "x", compression=zipfile.ZIP_DEFLATED, compresslevel=9
        ) as bundle:
            for path, archive_path in collected:
                info = zipfile.ZipInfo(archive_path, date_time=(1980, 1, 1, 0, 0, 0))
                info.compress_type = zipfile.ZIP_DEFLATED
                info.external_attr = 0o100644 << 16
                bundle.writestr(info, path.read_bytes())
            for directory in sorted(empty_directories):
                info = zipfile.ZipInfo(directory, date_time=(1980, 1, 1, 0, 0, 0))
                info.external_attr = 0o40755 << 16
                bundle.writestr(info, b"")
            info = zipfile.ZipInfo(
                "metadata/snapshot.json", date_time=(1980, 1, 1, 0, 0, 0)
            )
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            bundle.writestr(info, metadata_bytes)
        temporary.replace(output)
    except Exception:
        if temporary.exists():
            temporary.unlink()
        raise

    verification = verify_archive(output, expected_files)
    current_cc_names = sorted(
        path.name
        for path in cc_root.iterdir()
        if path.is_dir() and (path / "SKILL.md").is_file()
    )
    current_agents_names = sorted(
        path.name
        for path in agents_root.iterdir()
        if link_kind(path) == "physical" and (path / "SKILL.md").is_file()
    )
    current_backup_ids = sorted(
        path.name
        for path in backups_root.iterdir()
        if link_kind(path) == "physical" and path.is_dir()
    )
    post_database_export = safe_database_export(database)
    post_topology = {
        name: inspect_projection_root(home / relative)
        for name, relative in PROJECTION_ROOTS.items()
    }
    source_files_unchanged = all(
        path.is_file()
        and link_kind(path) == "physical"
        and sha256_file(path) == expected_files[archive_path]
        for path, archive_path in collected
    )
    source_consistency = {
        "selectedScopeNamesUnchanged": (
            current_cc_names == cc_names
            and current_agents_names == agents_names
            and current_backup_ids == backup_ids
        ),
        "selectedSourceFilesUnchanged": source_files_unchanged,
        "safeDatabaseExportUnchanged": post_database_export == database_export,
        "projectionTopologyUnchanged": post_topology == topology,
    }
    if any(value is not True for value in source_consistency.values()):
        output.unlink(missing_ok=True)
        raise RuntimeError(
            "live Skill source state changed during snapshot; artifact discarded"
        )
    sidecar_document = {
        "schema": 1,
        "archive": str(output),
        "archiveSha256": sha256_file(output),
        "archiveBytes": output.stat().st_size,
        "payloadFiles": len(expected_files),
        "scopeCounts": {
            "ccSwitchSkillBodies": len(cc_names),
            "agentsSelectedBodies": len(agents_names),
            "canonicalContracts": len(CONTRACTS),
            "ccExistingBackups": len(backup_ids),
        },
        "metadataMember": "metadata/snapshot.json",
        "verification": verification,
        "sourceConsistency": source_consistency,
        "secretScan": metadata["secretScan"],
        "claimBoundary": metadata["claimBoundary"],
    }
    sidecar.write_text(
        json.dumps(sidecar_document, ensure_ascii=False, indent=2, sort_keys=True)
        + "\n",
        encoding="utf-8",
    )
    return sidecar_document


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--home", type=Path, default=Path.home())
    parser.add_argument("--canonical-config", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = build_snapshot(args.home, args.canonical_config, args.output)
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
