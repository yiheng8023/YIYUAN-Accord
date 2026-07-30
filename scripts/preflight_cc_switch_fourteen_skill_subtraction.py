#!/usr/bin/env python3
"""Read-only, fail-closed preflight for the fourteen-Skill CC transaction.

The preflight never invokes CC Switch commands and never writes a file.  It
captures only safe Skill metadata and filesystem identity surfaces, compares
the whole live state with a governed fingerprint, and then checks the exact
target and protected-sentinel semantics needed by the subtraction transaction.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sqlite3
import tomllib
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
REFRESH_PATH = (
    ROOT
    / "registry"
    / "cc-switch-fourteen-skill-subtraction-preview-3.19-refresh-2026-07-30.json"
)
CONTRACT_PATH = (
    ROOT
    / "registry"
    / "cc-switch-fourteen-skill-live-preflight-contract-2026-07-30.json"
)
FIRST_PARTY_PATH = (
    ROOT
    / "registry"
    / "self-authored-three-live-authority-and-cc-collision-reconciliation-2026-07-30.json"
)
PORTFOLIO_PATH = (
    ROOT / "registry" / "skill-portfolio-current-55-subtractive-triage-2026-07-30.json"
)
SAFE_SKILL_COLUMNS = (
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
PROJECTION_ROOTS = {
    "ccSwitch": ".cc-switch/skills",
    "agents": ".agents/skills",
    "claude": ".claude/skills",
    "codex": ".codex/skills",
}


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def _json_sha256(value: Any) -> str:
    payload = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _path_kind(path: Path) -> str:
    if path.is_symlink():
        return "symlink"
    if hasattr(os.path, "isjunction") and os.path.isjunction(path):
        return "junction"
    return "physical"


def _normalized_path(path: Path) -> str:
    return str(path).replace("\\", "/")


def _tree_identity(root: Path) -> dict[str, Any]:
    _require(root.is_dir(), f"required Skill tree is missing: {root}")
    resolved = root.resolve(strict=True)
    records: list[dict[str, Any]] = []
    for current, directories, filenames in os.walk(resolved, followlinks=False):
        current_path = Path(current)
        for name in directories:
            child = current_path / name
            _require(
                _path_kind(child) == "physical",
                f"nested link is outside the frozen tree identity: {child}",
            )
        for name in filenames:
            path = current_path / name
            _require(
                _path_kind(path) == "physical",
                f"linked file is outside the frozen tree identity: {path}",
            )
            relative = path.relative_to(resolved).as_posix()
            content = path.read_bytes()
            file_hash = hashlib.sha256(content).hexdigest()
            records.append(
                {
                    "path": relative,
                    "bytes": len(content),
                    "sha256": file_hash,
                }
            )
    records.sort(key=lambda item: (item["path"].casefold(), item["path"]))
    manifest_lines = [
        item["path"].encode("utf-8")
        + b"\0"
        + str(item["bytes"]).encode("ascii")
        + b"\0"
        + item["sha256"].encode("ascii")
        for item in records
    ]
    return {
        "fileCount": len(records),
        "bytes": sum(item["bytes"] for item in records),
        "treeManifestSha256": hashlib.sha256(b"\n".join(manifest_lines)).hexdigest(),
        "files": records,
    }


def _database_projection(database: Path) -> dict[str, Any]:
    _require(database.is_file(), f"CC Switch database is missing: {database}")
    connection = sqlite3.connect(f"file:{database}?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    try:
        available = {
            row[1] for row in connection.execute("pragma table_info(skills)")
        }
        missing = sorted(set(SAFE_SKILL_COLUMNS) - available)
        _require(not missing, f"CC skills table columns drifted: {missing}")
        rows = [
            dict(row)
            for row in connection.execute(
                f"select {','.join(SAFE_SKILL_COLUMNS)} "
                "from skills order by directory,id"
            )
        ]
    finally:
        connection.close()
    return {
        "rowCount": len(rows),
        "distinctNames": len({row["name"] for row in rows}),
        "rows": rows,
    }


def _projection_root(root: Path) -> dict[str, Any]:
    _require(root.is_dir(), f"projection root is missing: {root}")
    entries: dict[str, Any] = {}
    for path in sorted(root.iterdir(), key=lambda item: item.name.casefold()):
        kind = _path_kind(path)
        resolvable = path.is_dir()
        entry: dict[str, Any] = {
            "path": _normalized_path(path),
            "kind": kind,
            "resolvedTarget": (
                _normalized_path(path.resolve(strict=False))
                if kind != "physical"
                else None
            ),
            "resolvableDirectory": resolvable,
            "skillMdResolvable": (path / "SKILL.md").is_file(),
        }
        if resolvable:
            identity = _tree_identity(path)
            entry.update(
                {
                    "fileCount": identity["fileCount"],
                    "bytes": identity["bytes"],
                    "treeManifestSha256": identity["treeManifestSha256"],
                }
            )
        entries[path.name] = entry
    return {
        "entryCount": len(entries),
        "entries": entries,
    }


def _backup_inventory(backups_root: Path) -> dict[str, Any]:
    _require(backups_root.is_dir(), f"CC backup root is missing: {backups_root}")
    items: list[dict[str, Any]] = []
    for path in backups_root.iterdir():
        if _path_kind(path) != "physical" or not path.is_dir():
            continue
        identity = _tree_identity(path)
        items.append(
            {
                "id": path.name,
                "mtimeNs": path.stat().st_mtime_ns,
                "fileCount": identity["fileCount"],
                "bytes": identity["bytes"],
                "treeManifestSha256": identity["treeManifestSha256"],
            }
        )
    items.sort(key=lambda item: (item["mtimeNs"], item["id"]))
    return {
        "count": len(items),
        "orderedIds": [item["id"] for item in items],
        "items": items,
    }


def _settings_projection(settings_path: Path) -> dict[str, Any]:
    _require(settings_path.is_file(), f"CC Switch settings are missing: {settings_path}")
    document = json.loads(settings_path.read_text(encoding="utf-8"))
    override_keys = sorted(
        key
        for key in document
        if "skill" in key.casefold() and "path" in key.casefold()
    )
    return {
        "skillStorageLocation": document.get("skillStorageLocation"),
        "skillSyncMethod": document.get("skillSyncMethod"),
        "skillPathOverrideKeys": override_keys,
    }


def _codex_skill_config(config_path: Path) -> dict[str, Any]:
    _require(config_path.is_file(), f"Codex config is missing: {config_path}")
    with config_path.open("rb") as handle:
        document = tomllib.load(handle)
    rows = document.get("skills", {}).get("config", [])
    selected = sorted(
        (
            {
                "path": str(row.get("path", "")).replace("\\", "/"),
                "enabled": row.get("enabled"),
            }
            for row in rows
            if isinstance(row, dict)
            and str(row.get("path", "")).replace("\\", "/").endswith(
                ("/doc/SKILL.md", "/pdf/SKILL.md")
            )
        ),
        key=lambda item: item["path"],
    )
    return {"docPdfRows": selected}


def capture_live_state(home: Path, manager_binary: Path) -> dict[str, Any]:
    """Capture a safe, read-only identity projection of the live Skill state."""
    home = home.resolve(strict=True)
    manager_binary = manager_binary.resolve(strict=True)
    database = _database_projection(home / ".cc-switch/cc-switch.db")
    cc_root = home / ".cc-switch/skills"
    cc_trees: dict[str, Any] = {}
    for path in sorted(cc_root.iterdir(), key=lambda item: item.name.casefold()):
        if _path_kind(path) == "physical" and path.is_dir() and (path / "SKILL.md").is_file():
            cc_trees[path.name] = _tree_identity(path)
    projections = {
        name: _projection_root(home / relative)
        for name, relative in PROJECTION_ROOTS.items()
    }
    state = {
        "schema": 1,
        "managerBinary": {
            "path": _normalized_path(manager_binary),
            "bytes": manager_binary.stat().st_size,
            "sha256": _sha256_file(manager_binary),
        },
        "settings": _settings_projection(home / ".cc-switch/settings.json"),
        "database": database,
        "ccTrees": cc_trees,
        "projections": projections,
        "backups": _backup_inventory(home / ".cc-switch/skill-backups"),
        "codexSkillConfig": _codex_skill_config(home / ".codex/config.toml"),
    }
    state["fingerprints"] = {
        key: _json_sha256(state[key])
        for key in (
            "managerBinary",
            "settings",
            "database",
            "ccTrees",
            "projections",
            "backups",
            "codexSkillConfig",
        )
    }
    state["fingerprints"]["wholeState"] = _json_sha256(state["fingerprints"])
    return state


def validate_contract_document(
    contract: dict[str, Any],
    *,
    root: Path | None = None,
) -> None:
    _require(
        contract.get("schema") == 1
        and contract.get("id")
        == "cc-switch-fourteen-skill-live-preflight-contract-2026-07-30"
        and contract.get("status") == "read-only-fail-closed-preflight-ready",
        "fourteen-Skill live preflight contract identity drifted",
    )
    _require(
        contract.get("mutationAuthority")
        == {
            "ccSwitchMutation": False,
            "hostProjectionMutation": False,
            "recoveryArchiveCreation": False,
            "remoteSnapshot": False,
            "gitCommitOrPush": False,
        },
        "fourteen-Skill live preflight mutation boundary drifted",
    )
    fingerprints = contract.get("expectedFingerprints", {})
    _require(
        set(fingerprints)
        == {
            "managerBinary",
            "settings",
            "database",
            "ccTrees",
            "projections",
            "backups",
            "codexSkillConfig",
            "wholeState",
        }
        and all(
            isinstance(value, str) and len(value) == 64
            for value in fingerprints.values()
        ),
        "fourteen-Skill live preflight fingerprints drifted",
    )
    _require(
        contract.get("failClosedOnAnyWholeStateDrift") is True
        and contract.get("pointInTimeCheckNotTransactionLock") is True
        and contract.get("mustRerunImmediatelyBeforeCanary") is True
        and contract.get("authorizesUninstall") is False,
        "fourteen-Skill live preflight claim boundary drifted",
    )
    if root is not None:
        _require(
            contract.get("inputs")
            == {
                "managerRefresh": "registry/cc-switch-fourteen-skill-subtraction-preview-3.19-refresh-2026-07-30.json",
                "firstPartyCollisionSentinels": "registry/self-authored-three-live-authority-and-cc-collision-reconciliation-2026-07-30.json",
                "portfolioPartition": "registry/skill-portfolio-current-55-subtractive-triage-2026-07-30.json",
                "runtime": "scripts/preflight_cc_switch_fourteen_skill_subtraction.py",
            }
            and all(contract.get("identitySurfaces", {}).values())
            and all(contract.get("semanticChecks", {}).values())
            and contract.get("mustStopIfAnyFingerprintOrSemanticCheckFails")
            is True
            and all(
                value is False
                for value in contract.get("claimBoundary", {}).values()
            ),
            "fourteen-Skill live preflight governed surfaces drifted",
        )
        summary = contract.get("observedSummary", {})
        _require(
            summary.get("managerBinaryBytes") == 32584192
            and summary.get("databaseRows") == 55
            and summary.get("databaseDistinctNames") == 55
            and summary.get("ccSkillTrees") == 55
            and summary.get("projectionEntryCounts")
            == {"ccSwitch": 55, "agents": 41, "claude": 55, "codex": 55}
            and summary.get("backupCount") == 20
            and summary.get("targetCount") == 14
            and summary.get("firstPartyPhysicalSentinelCount") == 3
            and summary.get("mattPromotedSentinelCount") == 22
            and summary.get("docPdfPolicySentinelCount") == 2,
            "fourteen-Skill live preflight observed summary drifted",
        )
        documentation = contract.get("documentation")
        _require(
            documentation
            == "docs/strategy/CC-SWITCH-FOURTEEN-SKILL-LIVE-PREFLIGHT-CONTRACT-2026-07-30.md",
            "fourteen-Skill live preflight documentation binding drifted",
        )
        text = (root / documentation).read_text(encoding="utf-8")
        for phrase in (
            "repeatable live preflight",
            "whole-state fingerprint is not a transaction lock",
            "case-insensitively",
            "Protected sentinels",
            "does not authorize uninstall",
        ):
            _require(
                phrase in text,
                f"fourteen-Skill live preflight documentation missing: {phrase}",
            )


def validate_live_state(
    state: dict[str, Any],
    *,
    contract: dict[str, Any],
    refresh: dict[str, Any],
    first_party: dict[str, Any],
    portfolio: dict[str, Any],
) -> dict[str, Any]:
    """Validate a captured state against the governed transaction surfaces."""
    validate_contract_document(contract)
    _require(
        state.get("fingerprints") == contract.get("expectedFingerprints"),
        "whole live Skill state drifted from the governed preflight fingerprint",
    )
    manager = refresh["manager"]
    _require(
        state["managerBinary"]["path"].casefold()
        == manager["binaryPath"].casefold()
        and state["managerBinary"]["bytes"] == manager["binaryBytes"]
        and state["managerBinary"]["sha256"] == manager["binarySha256"],
        "CC Switch manager binary drifted",
    )
    _require(
        state["settings"]
        == {
            "skillStorageLocation": "cc_switch",
            "skillSyncMethod": "symlink",
            "skillPathOverrideKeys": [],
        },
        "CC Switch Skill settings drifted",
    )

    rows = state["database"]["rows"]
    by_name = {row["name"]: row for row in rows}
    live = refresh["livePreState"]
    _require(
        state["database"]["rowCount"] == live["databaseRows"]
        and state["database"]["distinctNames"] == live["databaseDistinctNames"]
        and len(by_name) == len(rows),
        "CC Switch database cardinality drifted",
    )
    target_items = refresh["candidateCohort"]["items"]
    target_names = [item["name"] for item in target_items]
    for item in target_items:
        name = item["name"]
        row = by_name.get(name)
        _require(row is not None, f"target database row is missing: {name}")
        _require(
            row["directory"] == name
            and row["content_hash"] == item["dbContentHash"]
            and row["repo_owner"] in (None, "")
            and row["repo_name"] in (None, "")
            and row["enabled_claude"] == 1
            and row["enabled_codex"] == 1
            and row["enabled_gemini"] == 0
            and row["enabled_opencode"] == 0
            and row["enabled_hermes"] == 0
            and row["enabled_grokbuild"] == 0,
            f"target database metadata drifted: {name}",
        )
        tree = state["ccTrees"].get(name)
        _require(
            tree is not None
            and tree["fileCount"] == item["fileCount"]
            and tree["bytes"] == item["bytes"]
            and tree["treeManifestSha256"] == item["currentTreeManifestSha256"],
            f"target CC tree drifted: {name}",
        )
        expected_target = state["projections"]["ccSwitch"]["entries"][name][
            "path"
        ].casefold()
        for root_name in ("agents", "claude", "codex"):
            entry = state["projections"][root_name]["entries"].get(name)
            _require(
                entry is not None
                and entry["kind"] == "symlink"
                and entry["resolvableDirectory"] is True
                and entry["resolvedTarget"].casefold() == expected_target,
                f"target host projection drifted: {root_name}/{name}",
            )

    rotation = refresh["backupRotation"]
    ordered_ids = state["backups"]["orderedIds"]
    expected_order = (
        rotation["expectedEvictedBackupIds"]
        + rotation["expectedRetainedExistingBackupIds"]
    )
    _require(
        state["backups"]["count"] == rotation["currentBackupCount"]
        and ordered_ids == expected_order,
        "CC Switch backup count or modified-time eviction order drifted",
    )

    for package in first_party["packages"]:
        name = package["name"]
        expected_hash = package["currentSourceProjection"]["treeManifestSha256"]
        for root_name in ("agents", "codex"):
            entry = state["projections"][root_name]["entries"].get(name)
            _require(
                entry is not None
                and entry["kind"] == "physical"
                and entry["treeManifestSha256"] == expected_hash,
                f"first-party physical sentinel drifted: {root_name}/{name}",
            )

    cohorts = {
        item["id"]: item for item in portfolio["portfolioPartition"]["cohorts"]
    }
    matt_names = cohorts["current-matt-promoted-exact"]["names"]
    matt_rows = [row for row in rows if row["repo_owner"] == "mattpocock"]
    _require(
        len(matt_rows) == 22
        and {row["name"] for row in matt_rows} == set(matt_names)
        and all(
            row["repo_name"] == "skills"
            and row["repo_branch"] == "main"
            and row["enabled_claude"] == 1
            and row["enabled_codex"] == 1
            and row["name"] in state["ccTrees"]
            for row in matt_rows
        ),
        "Matt promoted 22-row sentinel drifted",
    )

    for name in ("doc", "pdf"):
        cc_entry = state["projections"]["ccSwitch"]["entries"].get(name)
        agents_entry = state["projections"]["agents"]["entries"].get(name)
        claude_entry = state["projections"]["claude"]["entries"].get(name)
        codex_entry = state["projections"]["codex"]["entries"].get(name)
        _require(
            cc_entry is not None
            and cc_entry["kind"] == "physical"
            and agents_entry is not None
            and agents_entry["kind"] == "symlink"
            and claude_entry is not None
            and claude_entry["kind"] == "symlink"
            and codex_entry is None,
            f"doc/pdf carrier sentinel drifted: {name}",
        )
    config_rows = state["codexSkillConfig"]["docPdfRows"]
    _require(
        len(config_rows) == 2
        and all(row["enabled"] is False for row in config_rows)
        and {Path(row["path"]).parent.name for row in config_rows} == {"doc", "pdf"},
        "Codex doc/pdf disable-policy sentinel drifted",
    )
    _require(
        "diagnose" in by_name
        and set(target_names).isdisjoint(
            {"diagnose", "intent-contract", "capability-router", "closure-contract"}
        ),
        "transaction exclusion sentinel drifted",
    )
    return {
        "status": "pass",
        "wholeStateFingerprint": state["fingerprints"]["wholeState"],
        "databaseRows": state["database"]["rowCount"],
        "targetCount": len(target_names),
        "backupCount": state["backups"]["count"],
        "mattPromotedSentinelCount": len(matt_rows),
        "firstPartyPhysicalSentinelCount": len(first_party["packages"]),
        "docPdfPolicySentinelCount": 2,
        "authorizesMutation": False,
        "pointInTimeOnly": True,
    }


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--home", type=Path, default=Path.home())
    parser.add_argument(
        "--manager-binary",
        type=Path,
        default=Path(
            "C:/Users/15521/AppData/Local/Programs/CC Switch/cc-switch.exe"
        ),
    )
    parser.add_argument(
        "--observe",
        action="store_true",
        help="print the safe captured state instead of validating the contract",
    )
    parser.add_argument("--contract", type=Path, default=CONTRACT_PATH)
    parser.add_argument("--refresh", type=Path, default=REFRESH_PATH)
    parser.add_argument("--first-party", type=Path, default=FIRST_PARTY_PATH)
    parser.add_argument("--portfolio", type=Path, default=PORTFOLIO_PATH)
    args = parser.parse_args()

    state = capture_live_state(args.home, args.manager_binary)
    if args.observe:
        print(json.dumps(state, ensure_ascii=False, indent=2, sort_keys=True))
        return 0
    result = validate_live_state(
        state,
        contract=_load(args.contract),
        refresh=_load(args.refresh),
        first_party=_load(args.first_party),
        portfolio=_load(args.portfolio),
    )
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
