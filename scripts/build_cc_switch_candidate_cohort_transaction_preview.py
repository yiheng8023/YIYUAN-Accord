#!/usr/bin/env python3
"""Build a read-only CC Switch inactive cohort transaction preview."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import sqlite3
import subprocess
from typing import Any, Iterable


SUPPORTED_APPS = ("claude", "codex", "gemini", "grokbuild", "opencode", "hermes")
SCRIPT_SUFFIXES = {".bat", ".cmd", ".js", ".mjs", ".ps1", ".py", ".sh", ".ts"}
CC_SWITCH_UPSTREAM_BASE = "492245dcb9196b0169e227d9eae2ab91466c0058"
CC_SWITCH_FORK_HEAD = "3db0288c2e3d34d26578839c3c14296eed7c6476"
CC_SWITCH_DRAFT_PR = "https://github.com/farion1231/cc-switch/pull/6086"


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"Expected JSON object: {path}")
    return value


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_digest(value: Any) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def safe_relative_path(value: str) -> Path:
    posix = PurePosixPath(value)
    if posix.is_absolute() or not posix.parts or any(part in {"", ".", ".."} for part in posix.parts):
        raise ValueError(f"Unsafe relative path: {value}")
    return Path(*posix.parts)


def git_head(repository: Path) -> str:
    result = subprocess.run(
        ["git", "-C", str(repository), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def walk_candidate_items(value: Any) -> Iterable[dict[str, Any]]:
    if isinstance(value, dict):
        if isinstance(value.get("name"), str) and isinstance(value.get("path"), str):
            yield value
        for child in value.values():
            yield from walk_candidate_items(child)
    elif isinstance(value, list):
        for child in value:
            yield from walk_candidate_items(child)


def find_candidate_item(gate: dict[str, Any], name: str) -> dict[str, Any]:
    matches = [item for item in walk_candidate_items(gate) if item.get("name") == name]
    if len(matches) != 1:
        raise ValueError(f"Expected exactly one gate item for {name}, found {len(matches)}")
    disposition = matches[0].get("disposition")
    if not isinstance(disposition, str) or "manager-install-candidate-default-disabled" not in disposition:
        raise ValueError(f"Candidate {name} lacks a default-disabled manager disposition")
    return matches[0]


def declared_dependency_paths(item: dict[str, Any]) -> list[str]:
    paths: list[str] = []
    dependencies = item.get("dependencyFiles", [])
    if isinstance(dependencies, list):
        for dependency in dependencies:
            if isinstance(dependency, dict) and isinstance(dependency.get("path"), str):
                paths.append(dependency["path"])
    reference = item.get("requiredReference")
    if isinstance(reference, dict) and isinstance(reference.get("path"), str):
        paths.append(reference["path"])
    return sorted(set(paths))


def local_markdown_links(path: Path, text: str) -> Iterable[str]:
    for match in re.finditer(r"\]\(([^)]+)\)", text):
        target = match.group(1).strip().strip("<>").split(maxsplit=1)[0]
        target = target.split("#", 1)[0].split("?", 1)[0]
        if not target or target.startswith(("#", "/", "\\")):
            continue
        if re.match(r"^[A-Za-z][A-Za-z0-9+.-]*:", target):
            continue
        yield target


def inventory_tree(
    root: Path,
) -> tuple[list[dict[str, Any]], int, int, list[dict[str, str]]]:
    files: list[dict[str, Any]] = []
    total_bytes = 0
    script_count = 0
    out_of_root_markdown_links: list[dict[str, str]] = []
    for path in sorted(root.rglob("*"), key=lambda item: item.as_posix().lower()):
        if path.is_symlink():
            raise ValueError(f"Symlink is not eligible in an exact candidate payload: {path}")
        if not path.is_file():
            continue
        relative = path.relative_to(root).as_posix()
        size = path.stat().st_size
        suffix = path.suffix.lower()
        if suffix in SCRIPT_SUFFIXES:
            script_count += 1
        if suffix in {".md", ".txt", ".json", ".yaml", ".yml"}:
            text = path.read_text(encoding="utf-8", errors="replace")
            for target in local_markdown_links(path, text):
                resolved = (path.parent / Path(*PurePosixPath(target).parts)).resolve()
                try:
                    resolved.relative_to(root.resolve())
                except ValueError:
                    out_of_root_markdown_links.append(
                        {"source": relative, "target": target}
                    )
        files.append({"path": relative, "bytes": size, "sha256": sha256_file(path)})
        total_bytes += size
    return files, total_bytes, script_count, out_of_root_markdown_links


def cohort_tree_hash(root: Path) -> str:
    """Match the fork's complete, no-follow cohort ownership hash."""

    digest = hashlib.sha256()

    def visit(directory: Path) -> None:
        for path in sorted(directory.iterdir(), key=lambda item: item.name):
            relative = path.relative_to(root).as_posix()
            if path.is_symlink():
                raise ValueError(
                    f"Symlink cannot enter this exact candidate preview: {path}"
                )
            if path.is_dir():
                digest.update(b"directory\0")
                digest.update(relative.encode("utf-8"))
                digest.update(b"\0")
                visit(path)
            elif path.is_file():
                digest.update(b"file\0")
                digest.update(relative.encode("utf-8"))
                digest.update(b"\0")
                digest.update(path.read_bytes())
                digest.update(b"\0")
            else:
                raise ValueError(f"Unsupported candidate tree entry: {path}")

    visit(root)
    return digest.hexdigest()


def license_files(repository: Path, candidate_root: Path) -> list[dict[str, Any]]:
    candidates = list(repository.glob("LICENSE*")) + list(candidate_root.glob("LICENSE*"))
    unique: dict[str, Path] = {}
    for path in candidates:
        if path.is_file() and not path.is_symlink():
            unique[path.resolve().as_posix()] = path
    return [
        {
            "path": path.relative_to(repository).as_posix(),
            "bytes": path.stat().st_size,
            "sha256": sha256_file(path),
        }
        for path in sorted(unique.values(), key=lambda item: item.as_posix().lower())
    ]


def read_manager_rows(database: Path) -> tuple[list[dict[str, Any]], str, str]:
    before = sha256_file(database)
    uri = f"{database.resolve().as_uri()}?mode=ro"
    connection = sqlite3.connect(uri, uri=True)
    try:
        columns = {
            row[1]
            for row in connection.execute("PRAGMA table_info(skills)").fetchall()
            if isinstance(row[1], str)
        }
        required = {"id", "name", "directory", "repo_owner", "repo_name"}
        if not required.issubset(columns):
            raise ValueError(f"CC Switch skills schema lacks columns: {sorted(required - columns)}")
        app_columns = [f"enabled_{app}" for app in SUPPORTED_APPS if f"enabled_{app}" in columns]
        selected = ["id", "name", "directory", "repo_owner", "repo_name", *app_columns]
        rows = []
        for values in connection.execute(f"SELECT {', '.join(selected)} FROM skills").fetchall():
            rows.append(dict(zip(selected, values, strict=True)))
    finally:
        connection.close()
    after = sha256_file(database)
    return rows, before, after


def build_report(args: argparse.Namespace) -> dict[str, Any]:
    authority_root = args.authority_root.resolve()
    source_root = args.source_root.resolve()
    cc_home = args.cc_home.resolve()
    cohort = load_json(args.cohort.resolve())
    mapping = load_json(args.mapping.resolve())
    mapping_by_name = {
        item["name"]: item
        for item in mapping.get("candidateMappings", [])
        if isinstance(item, dict) and isinstance(item.get("name"), str)
    }

    source_records = {
        item["repository"]: item
        for item in cohort["sourceGateCoverage"]["sources"]
        if isinstance(item, dict) and isinstance(item.get("repository"), str)
    }
    by_source = cohort["staticDefaultDisabledCandidates"]["bySource"]
    expected_count = cohort["staticDefaultDisabledCandidates"]["count"]
    if sum(len(names) for names in by_source.values()) != expected_count:
        raise ValueError("Cohort candidate count does not match by-source entries")

    manager_rows, database_before, database_after = read_manager_rows(cc_home / "cc-switch.db")
    if database_before != database_after:
        raise RuntimeError("Read-only manager snapshot changed the database bytes")
    rows_by_directory = {
        str(row.get("directory", "")).casefold(): row for row in manager_rows
    }

    candidates: list[dict[str, Any]] = []
    collisions: list[dict[str, Any]] = []
    source_summaries: list[dict[str, Any]] = []
    for repository_name, names in by_source.items():
        source_record = source_records.get(repository_name)
        if source_record is None:
            raise ValueError(f"Missing source-gate record for {repository_name}")
        expected_commit = source_record["commit"]
        repository = source_root / repository_name.replace("/", "__")
        actual_commit = git_head(repository)
        if actual_commit != expected_commit:
            raise ValueError(
                f"Source revision mismatch for {repository_name}: {actual_commit} != {expected_commit}"
            )
        gate_path = safe_relative_path(source_record["gateRecord"])
        gate = load_json(authority_root / gate_path)
        source_candidate_names: list[str] = []
        for name in names:
            if name not in mapping_by_name:
                raise ValueError(f"Missing demand mapping for {name}")
            item = find_candidate_item(gate, name)
            item_path = safe_relative_path(item["path"])
            candidate_root_rel = item_path.parent if item_path.name == "SKILL.md" else item_path
            candidate_root = repository / candidate_root_rel
            entrypoint = candidate_root / "SKILL.md"
            if not entrypoint.is_file():
                raise ValueError(f"Missing candidate entrypoint: {entrypoint}")
            declared_dependencies = declared_dependency_paths(item)
            for dependency in declared_dependencies:
                dependency_rel = safe_relative_path(dependency)
                dependency_path = repository / dependency_rel
                if not dependency_path.is_file():
                    raise ValueError(f"Missing declared dependency for {name}: {dependency}")
                try:
                    dependency_path.resolve().relative_to(candidate_root.resolve())
                except ValueError as exc:
                    raise ValueError(
                        f"Declared dependency escapes candidate root for {name}: {dependency}"
                    ) from exc

            files, total_bytes, script_count, out_of_root_links = inventory_tree(candidate_root)
            dependency_evidence = [
                {
                    "path": dependency,
                    "sha256": sha256_file(repository / safe_relative_path(dependency)),
                }
                for dependency in declared_dependencies
            ]
            dependency_complete = not script_count and not out_of_root_links
            dependency_closure_digest = canonical_digest(
                {
                    "candidate": name,
                    "declaredDependencies": dependency_evidence,
                    "outOfRootMarkdownLinks": out_of_root_links,
                    "scriptLikeFileCount": script_count,
                }
            )
            licenses = license_files(repository, candidate_root)
            if not licenses:
                raise ValueError(f"No license artifact found for {name}")
            install_directory = candidate_root.name
            row_collision = rows_by_directory.get(install_directory.casefold())
            path_collisions = []
            for root_kind, root in [
                ("manager-ssot", cc_home / "skills"),
                *[("consumer", consumer.resolve()) for consumer in args.consumer_root],
            ]:
                path = root / install_directory
                if path.exists() or path.is_symlink():
                    path_collisions.append({"kind": root_kind, "path": path.as_posix()})
            if row_collision is not None:
                collisions.append(
                    {"candidate": name, "kind": "manager-row", "row": row_collision}
                )
            collisions.extend(
                {"candidate": name, **collision} for collision in path_collisions
            )
            candidates.append(
                {
                    "name": name,
                    "source": repository_name,
                    "revision": expected_commit,
                    "sourcePath": candidate_root_rel.as_posix(),
                    "installDirectory": install_directory,
                    "effectGroupId": mapping_by_name[name].get("effectGroupId"),
                    "initialApps": {app: False for app in SUPPORTED_APPS},
                    "entrypointSha256": sha256_file(entrypoint),
                    "payloadTreeSha256": canonical_digest(files),
                    "managerAdmission": {
                        "sourceTreeHash": cohort_tree_hash(candidate_root),
                        "dependencyClosureDigest": dependency_closure_digest,
                        "dependencyComplete": dependency_complete,
                    },
                    "fileCount": len(files),
                    "bytes": total_bytes,
                    "scriptLikeFileCount": script_count,
                    "outOfRootMarkdownLinks": out_of_root_links,
                    "declaredDependencies": declared_dependencies,
                    "declaredDependenciesVerified": True,
                    "licenseArtifacts": licenses,
                    "collisionFree": row_collision is None and not path_collisions,
                }
            )
            source_candidate_names.append(name)
        source_summaries.append(
            {
                "repository": repository_name,
                "revision": expected_commit,
                "candidateNames": source_candidate_names,
            }
        )

    if len(candidates) != expected_count:
        raise ValueError("Built candidate count does not match the governed cohort")
    candidate_names = [candidate["name"] for candidate in candidates]
    if len(candidate_names) != len(set(candidate_names)):
        raise ValueError("Candidate names are not unique")

    semantic_dependency_blockers = [
        candidate["name"]
        for candidate in candidates
        if candidate["outOfRootMarkdownLinks"] or candidate["scriptLikeFileCount"]
    ]
    blockers = [
        "CC Switch draft PR 6086 is not merged, released, or available in the live manager runtime",
    ]
    if collisions:
        blockers.append("live manager or consumer collisions require an explicit update/replacement decision")
    if semantic_dependency_blockers:
        blockers.append(
            "script-like files or out-of-root Markdown links require candidate-specific operational dependency adjudication"
        )

    report = {
        "schema": 1,
        "status": (
            "preview-built-zero-live-mutation-manager-fork-unmerged"
            if not collisions
            else "preview-built-zero-live-mutation-collision-and-manager-fork-unmerged"
        ),
        "candidateCount": len(candidates),
        "sourceCount": len(source_summaries),
        "collisionCount": len(collisions),
        "allInitialAppsDisabled": all(
            not any(candidate["initialApps"].values()) for candidate in candidates
        ),
        "sources": source_summaries,
        "candidates": candidates,
        "collisions": collisions,
        "managerSnapshot": {
            "databasePath": (cc_home / "cc-switch.db").as_posix(),
            "databaseSha256Before": database_before,
            "databaseSha256After": database_after,
            "databaseReadOnly": database_before == database_after,
            "managerRowCount": len(manager_rows),
            "ssotRoot": (cc_home / "skills").as_posix(),
            "consumerRoots": [root.resolve().as_posix() for root in args.consumer_root],
        },
        "managerContribution": {
            "upstreamRepository": "farion1231/cc-switch",
            "upstreamBase": CC_SWITCH_UPSTREAM_BASE,
            "forkBranch": "yiheng8023:codex/inactive-skill-cohort-transaction",
            "forkHead": CC_SWITCH_FORK_HEAD,
            "draftPullRequest": CC_SWITCH_DRAFT_PR,
            "state": "open-draft-review-required",
            "merged": False,
            "released": False,
            "liveRuntimeAvailable": False,
            "supportBoundary": "exact-nested-repository-relative-source-path",
            "trustBoundary": {
                "revisionObjectTypeIndependentlyProved": False,
                "dependencyClosureSemanticallyProvedByManager": False,
                "materializedSourceTreeHashVerifiedByManager": True,
                "exactNestedSourcePathRequired": True,
                "repositoryRootSkillSupported": False,
                "recoveryDurability": "interrupted-process-only",
            },
        },
        "transaction": {
            "kind": "preview-only-exact-revision-inactive-cohort",
            "atomicBoundary": f"{len(candidates)}-candidate-cohort",
            "requestedInitialApps": {app: False for app in SUPPORTED_APPS},
            "executionEligible": False,
            "blockers": blockers,
            "backupPlan": [
                "freeze and verify the live database, SSOT, consumer-root, and candidate-source digests",
                "create a manager-owned database and SSOT rollback point before the first mutation",
                "retain a durable transaction journal until post-commit verification succeeds",
            ],
            "rollbackPlan": [
                "restore every pre-existing manager row and SSOT path from the frozen pre-state",
                "remove only transaction-created inactive rows and SSOT paths",
                "verify every consumer root remains byte/path unchanged",
                "retain failed or ambiguous journals for explicit recovery rather than retrying",
            ],
        },
        "executionCounters": {
            "networkCalls": 0,
            "thirdPartyScriptExecutions": 0,
            "managerInvocations": 0,
            "managerMutations": 0,
            "consumerWrites": 0,
            "modelCalls": 0,
        },
        "claimBoundary": {
            "exactSourceRevisionVerified": True,
            "fullCandidateDirectoryInventoried": True,
            "gateDeclaredDependencyFilesVerified": True,
            "operationalDependencyClosureProved": not semantic_dependency_blockers,
            "managerBatchTransactionImplemented": False,
            "managerBatchTransactionImplementedInFork": True,
            "managerBatchTransactionMergedOrReleased": False,
            "candidateInstalled": False,
            "candidateEnabled": False,
            "candidateExposed": False,
            "candidateExecuted": False,
            "candidateBehaviorOrValueProved": False,
        },
    }
    report["reportSha256"] = canonical_digest(report)
    return report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--authority-root", type=Path, required=True)
    parser.add_argument("--cohort", type=Path, required=True)
    parser.add_argument("--mapping", type=Path, required=True)
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--cc-home", type=Path, required=True)
    parser.add_argument("--consumer-root", type=Path, action="append", default=[])
    parser.add_argument("--output", type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = build_report(args)
    rendered = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8", newline="\n")
    else:
        print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
