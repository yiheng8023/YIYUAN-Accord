#!/usr/bin/env python3
"""Reconcile the exact 13 Matt common-root directories to CC Switch links.

The transaction preserves ``~/.agents/skills`` itself. Twelve retained Skill
directories become absolute directory symlinks to the existing CC Switch SSOT;
the retired ``writing-great-skills`` common-root copy is moved into the
transaction recovery root without replacement. The original directories stay
recoverable until a later, separately governed cleanup.

This transaction does not update CC Switch, change its database, enable a
Skill, or touch any third-party payload body.
"""

from __future__ import annotations

import argparse
from datetime import UTC, datetime
import hashlib
import json
import os
from pathlib import Path
from typing import Any

try:
    from .probe_codex_app_server_skill_root_collision import observe_tree
except ImportError:  # Direct script execution.
    from probe_codex_app_server_skill_root_collision import observe_tree


TRANSACTION_ID = "matt-common-root-thirteen-reconciliation-v1"
DIRECT_NAMES = (
    "ask-matt",
    "code-review",
    "codebase-design",
    "diagnosing-bugs",
    "domain-modeling",
    "grilling",
    "implement",
    "research",
    "resolving-merge-conflicts",
    "to-spec",
    "to-tickets",
    "wayfinder",
    "writing-great-skills",
)
RETIRED_NAME = "writing-great-skills"
RETAINED_NAMES = tuple(name for name in DIRECT_NAMES if name != RETIRED_NAME)


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _is_link(path: Path) -> bool:
    return path.is_symlink() or (
        hasattr(os.path, "isjunction") and os.path.isjunction(path)
    )


def _normalized(path: Path) -> str:
    return str(path).replace("\\", "/").rstrip("/").lower()


def _roots(home: Path) -> tuple[Path, Path, Path]:
    home = home.expanduser().resolve(strict=True)
    agents = home / ".agents" / "skills"
    cc = home / ".cc-switch" / "skills"
    backups = home / ".cc-switch" / "skill-backups"
    for path in (agents, cc, backups):
        if not path.is_dir():
            raise ValueError(f"required directory is missing: {path}")
    return agents, cc, backups


def preflight(home: Path) -> dict[str, Any]:
    agents, cc, _ = _roots(home)
    entries: list[dict[str, Any]] = []
    for name in DIRECT_NAMES:
        source = agents / name
        target = cc / name
        source_skill = source / "SKILL.md"
        target_skill = target / "SKILL.md"
        source_physical = source.is_dir() and not _is_link(source)
        target_physical = target.is_dir() and not _is_link(target)
        if not source_physical or not source_skill.is_file():
            raise ValueError(f"common-root source is not one physical Skill: {source}")
        if not target_physical or not target_skill.is_file():
            raise ValueError(f"CC SSOT target is not one physical Skill: {target}")
        entries.append(
            {
                "name": name,
                "source": source.as_posix(),
                "sourceTree": observe_tree(source),
                "sourceSkillMdSha256": _sha256_file(source_skill),
                "ccTarget": target.as_posix(),
                "ccTargetTree": observe_tree(target),
                "ccTargetSkillMdSha256": _sha256_file(target_skill),
                "targetReleaseRetainsName": name != RETIRED_NAME,
            }
        )
    return {
        "directNames": list(DIRECT_NAMES),
        "retainedNames": list(RETAINED_NAMES),
        "retiredName": RETIRED_NAME,
        "allSourcesPhysicalDirectories": True,
        "allCcTargetsPhysicalDirectories": True,
        "entries": entries,
        "agentsRootBefore": observe_tree(agents),
        "ccRootBefore": observe_tree(cc),
    }


def _write_journal(path: Path, journal: dict[str, Any]) -> None:
    content = json.dumps(journal, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    temporary = path.with_suffix(".json.partial")
    with temporary.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(content)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)


def _validate_transaction_root(home: Path, transaction_root: Path) -> Path:
    _, _, backups = _roots(home)
    transaction_root = transaction_root.expanduser().resolve(strict=False)
    if transaction_root.parent != backups.resolve(strict=True):
        raise ValueError("transaction root must be a direct child of CC skill-backups")
    return transaction_root


def _verify_committed(home: Path, transaction_root: Path) -> dict[str, Any]:
    agents, cc, _ = _roots(home)
    originals = transaction_root / "originals"
    entries: list[dict[str, Any]] = []
    for name in RETAINED_NAMES:
        source = agents / name
        target = cc / name
        if not source.is_symlink():
            raise RuntimeError(f"retained common-root path is not a symlink: {source}")
        if source.resolve(strict=True) != target.resolve(strict=True):
            raise RuntimeError(f"retained link target mismatch: {source}")
        if not (originals / name).is_dir() or _is_link(originals / name):
            raise RuntimeError(f"recoverable original is missing: {name}")
        entries.append(
            {
                "name": name,
                "kind": "symlink",
                "target": target.as_posix(),
                "skillMdSha256": _sha256_file(source / "SKILL.md"),
            }
        )
    retired = agents / RETIRED_NAME
    if retired.exists() or retired.is_symlink():
        raise RuntimeError("retired common-root path still exists")
    if not (originals / RETIRED_NAME).is_dir():
        raise RuntimeError("retired recoverable original is missing")
    return {
        "retainedLinkCount": len(entries),
        "retiredCommonRootAbsent": True,
        "recoverableOriginalCount": sum(
            (originals / name).is_dir() and not _is_link(originals / name)
            for name in DIRECT_NAMES
        ),
        "entries": entries,
        "agentsRootAfter": observe_tree(agents),
        "ccRootAfter": observe_tree(cc),
    }


def _restore_originals(home: Path, transaction_root: Path) -> None:
    agents, _, _ = _roots(home)
    originals = transaction_root / "originals"
    staged = transaction_root / "staged-links"
    for name in reversed(DIRECT_NAMES):
        source = agents / name
        original = originals / name
        if source.is_symlink():
            source.unlink()
        elif source.exists() and original.exists():
            raise RuntimeError(f"cannot rollback over unexpected live path: {source}")
        if original.exists():
            os.replace(original, source)
    if staged.is_dir():
        for path in staged.iterdir():
            if path.is_symlink():
                path.unlink()
            else:
                raise RuntimeError(f"unexpected staged transaction entry: {path}")
        staged.rmdir()


def execute_transaction(home: Path, transaction_root: Path) -> dict[str, Any]:
    home = home.expanduser().resolve(strict=True)
    agents, cc, _ = _roots(home)
    transaction_root = _validate_transaction_root(home, transaction_root)
    if transaction_root.exists() or transaction_root.is_symlink():
        raise FileExistsError(f"transaction root already exists: {transaction_root}")
    before = preflight(home)
    transaction_root.mkdir()
    originals = transaction_root / "originals"
    staged = transaction_root / "staged-links"
    originals.mkdir()
    staged.mkdir()
    journal: dict[str, Any] = {
        "schema": 1,
        "id": TRANSACTION_ID,
        "createdAt": datetime.now(UTC).isoformat(),
        "status": "staging",
        "home": home.as_posix(),
        "transactionRoot": transaction_root.as_posix(),
        "before": before,
        "operation": {
            "replaceWithCcSymlink": list(RETAINED_NAMES),
            "removeCommonRootWithoutReplacement": RETIRED_NAME,
            "ccManagerUpdateIncluded": False,
        },
    }
    _write_journal(transaction_root / "journal.json", journal)
    try:
        for name in RETAINED_NAMES:
            target = cc / name
            link = staged / name
            os.symlink(target, link, target_is_directory=True)
            if link.resolve(strict=True) != target.resolve(strict=True):
                raise RuntimeError(f"staged link target mismatch: {name}")
        journal["status"] = "applying"
        _write_journal(transaction_root / "journal.json", journal)
        for name in DIRECT_NAMES:
            source = agents / name
            original = originals / name
            os.replace(source, original)
            if name in RETAINED_NAMES:
                os.replace(staged / name, source)
        verification = _verify_committed(home, transaction_root)
    except BaseException:
        _restore_originals(home, transaction_root)
        journal["status"] = "rolled-back-after-error"
        journal["rolledBackAt"] = datetime.now(UTC).isoformat()
        _write_journal(transaction_root / "journal.json", journal)
        raise
    staged.rmdir()
    journal["status"] = "committed"
    journal["committedAt"] = datetime.now(UTC).isoformat()
    journal["verification"] = verification
    _write_journal(transaction_root / "journal.json", journal)
    return {
        "status": "committed",
        "transactionRoot": transaction_root.as_posix(),
        "journal": (transaction_root / "journal.json").as_posix(),
        "verification": verification,
    }


def rollback_transaction(home: Path, transaction_root: Path) -> dict[str, Any]:
    home = home.expanduser().resolve(strict=True)
    transaction_root = _validate_transaction_root(home, transaction_root)
    journal_path = transaction_root / "journal.json"
    if not journal_path.is_file():
        raise ValueError("transaction journal is missing")
    journal = json.loads(journal_path.read_text(encoding="utf-8"))
    if journal.get("id") != TRANSACTION_ID:
        raise ValueError("transaction journal identity mismatch")
    if journal.get("status") != "committed":
        raise ValueError("only a committed transaction may use explicit rollback")
    _restore_originals(home, transaction_root)
    check = preflight(home)
    journal["status"] = "rolled-back"
    journal["rolledBackAt"] = datetime.now(UTC).isoformat()
    journal["rollbackVerification"] = check
    _write_journal(journal_path, journal)
    return {
        "status": "rolled-back",
        "transactionRoot": transaction_root.as_posix(),
        "verification": check,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--home", type=Path, default=Path.home())
    parser.add_argument("--transaction-root", type=Path, required=True)
    operation = parser.add_mutually_exclusive_group(required=True)
    operation.add_argument("--execute", action="store_true")
    operation.add_argument("--rollback", action="store_true")
    args = parser.parse_args()
    if args.execute:
        result = execute_transaction(args.home, args.transaction_root)
    else:
        result = rollback_transaction(args.home, args.transaction_root)
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
