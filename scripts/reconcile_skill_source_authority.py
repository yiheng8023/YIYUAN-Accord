#!/usr/bin/env python3
"""Reconcile dated Skill source authority without mutating any Skill root."""

from __future__ import annotations

import hashlib
import json
import sqlite3
from pathlib import Path
from typing import Any


def tree_hash(root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(
        (item for item in root.rglob("*") if item.is_file()),
        key=lambda item: item.relative_to(root).as_posix(),
    ):
        relative = path.relative_to(root).as_posix().encode()
        content = path.read_bytes()
        digest.update(len(relative).to_bytes(4, "big"))
        digest.update(relative)
        digest.update(len(content).to_bytes(8, "big"))
        digest.update(content)
    return digest.hexdigest()


def plugin_index(cache: Path) -> tuple[dict[str, list[str]], dict[tuple[str, str], list[str]]]:
    by_directory: dict[str, list[str]] = {}
    by_package_and_name: dict[tuple[str, str], list[str]] = {}
    if not cache.is_dir():
        return by_directory, by_package_and_name
    for skill_file in cache.rglob("SKILL.md"):
        directory = skill_file.parent.name
        by_directory.setdefault(directory, []).append(str(skill_file))
        if len(skill_file.parents) >= 4 and skill_file.parents[1].name == "skills":
            package = skill_file.parents[3].name
            by_package_and_name.setdefault((package, directory), []).append(str(skill_file))
    return by_directory, by_package_and_name


def build_reconciliation(
    repository: Path,
    home: Path,
    codex_user_config: Path | None = None,
) -> dict[str, Any]:
    registry = json.loads((repository / "registry/skills.json").read_text(encoding="utf-8"))
    approved = {
        item["directory"]
        for item in registry["skills"]
        if item.get("status") == "approved"
    }
    repository_skills = repository / "skills"
    cc_root = home / ".cc-switch/skills"
    comparisons = []
    for name in sorted(approved):
        source = repository_skills / name
        target = cc_root / name
        present = (target / "SKILL.md").is_file()
        comparisons.append(
            {
                "name": name,
                "ccPresent": present,
                "treeEqual": present and tree_hash(source) == tree_hash(target),
            }
        )

    database = home / ".cc-switch/cc-switch.db"
    connection = sqlite3.connect(f"file:{database}?mode=ro", uri=True)
    try:
        rows = connection.execute(
            "select name,directory,repo_owner,repo_name from skills"
        ).fetchall()
    finally:
        connection.close()

    plugin_by_directory, plugin_by_package_name = plugin_index(
        home / ".codex/plugins/cache"
    )
    missing_rows = [
        (name, directory)
        for name, directory, *_ in rows
        if directory and not (cc_root / directory / "SKILL.md").is_file()
    ]
    exact: list[str] = []
    qualified: list[dict[str, str]] = []
    unresolved: list[dict[str, str]] = []
    for name, directory in missing_rows:
        if directory in plugin_by_directory:
            exact.append(directory)
            continue
        matched_package = next(
            (
                package
                for package, plugin_name in plugin_by_package_name
                if plugin_name == name
                and directory == f"{package}-{name}"
            ),
            None,
        )
        if matched_package:
            qualified.append(
                {"name": name, "directory": directory, "package": matched_package}
            )
        else:
            unresolved.append({"name": name, "directory": directory})

    physical = {
        path.name for path in cc_root.iterdir() if (path / "SKILL.md").is_file()
    }
    unattributed_outside_approved = sorted(
        directory
        for _, directory, owner, repo_name in rows
        if directory in physical
        and directory not in approved
        and not owner
        and not repo_name
    )

    contracts: dict[str, Any] = {}
    if codex_user_config:
        for name in ("intent-contract", "capability-router", "closure-contract"):
            canonical = codex_user_config / "skills" / name
            if not (canonical / "SKILL.md").is_file():
                continue
            canonical_hash = tree_hash(canonical)
            roots = {
                "ccSwitch": cc_root / name,
                "agents": home / ".agents/skills" / name,
                "claude": home / ".claude/skills" / name,
                "codex": home / ".codex/skills" / name,
            }
            contracts[name] = {
                "canonicalTreeHash": canonical_hash,
                "equalRoots": sorted(
                    root_name
                    for root_name, root in roots.items()
                    if (root / "SKILL.md").is_file() and tree_hash(root) == canonical_hash
                ),
                "differentRoots": sorted(
                    root_name
                    for root_name, root in roots.items()
                    if (root / "SKILL.md").is_file() and tree_hash(root) != canonical_hash
                ),
            }

    return {
        "schema": 1,
        "mode": "read-only-source-authority-reconciliation",
        "approvedRepositoryPayloads": {
            "count": len(comparisons),
            "ccPresent": sum(item["ccPresent"] for item in comparisons),
            "treeEqual": sum(item["treeEqual"] for item in comparisons),
            "drift": sorted(item["name"] for item in comparisons if not item["treeEqual"]),
        },
        "missingCcPhysicalRuntimeReconciliation": {
            "count": len(missing_rows),
            "exactPluginDirectoryMatches": len(exact),
            "qualifiedPluginAliasMatches": len(qualified),
            "unresolved": unresolved,
        },
        "unattributedPhysicalOutsideApprovedInventory": {
            "count": len(unattributed_outside_approved),
            "directories": unattributed_outside_approved,
        },
        "contractCanonicalComparison": contracts,
        "claimBoundary": {
            "runtimeCacheMatchProvesInvocation": False,
            "sourceMatchApprovesInstallation": False,
            "authorizesProjectionRepair": False,
        },
    }

