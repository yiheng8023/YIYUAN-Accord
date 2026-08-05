#!/usr/bin/env python3
"""Build a read-only, manifest-aware Matt Pocock Skills update preview."""

from __future__ import annotations

import argparse
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import posixpath
import re
import sqlite3
import subprocess
from typing import Any


SUPPORTED_APPS = ("claude", "codex", "gemini", "grokbuild", "opencode", "hermes")
SCRIPT_SUFFIXES = {".bat", ".cmd", ".js", ".mjs", ".ps1", ".py", ".sh", ".ts"}


def canonical_digest(value: Any) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def normalized_bytes(value: bytes) -> bytes:
    return value.replace(b"\r\n", b"\n")


def normalized_observed_at(value: str) -> str:
    compact = re.fullmatch(
        r"(\d{4}-\d{2}-\d{2})_(\d{2})-(\d{2})-(\d{2})([+-]\d{2})-(\d{2})",
        value,
    )
    if compact:
        value = (
            f"{compact.group(1)}T{compact.group(2)}:{compact.group(3)}:"
            f"{compact.group(4)}{compact.group(5)}:{compact.group(6)}"
        )
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        raise ValueError("observed-at must include an explicit UTC offset")
    return parsed.isoformat(timespec="seconds")


def git(repository: Path, *args: str, text: bool = True) -> str | bytes:
    result = subprocess.run(
        ["git", "-C", str(repository), *args],
        check=True,
        capture_output=True,
        text=text,
    )
    return result.stdout.strip() if text else result.stdout


def require_object(repository: Path, object_id: str, expected_type: str, label: str) -> None:
    try:
        actual = git(repository, "cat-file", "-t", object_id)
    except subprocess.CalledProcessError as exc:
        raise ValueError(f"Missing {label}: {object_id}") from exc
    if actual != expected_type:
        raise ValueError(f"Expected {label} to be {expected_type}, found {actual}")


def load_git_json(repository: Path, revision: str, path: str) -> dict[str, Any]:
    raw = git(repository, "show", f"{revision}:{path}", text=False)
    assert isinstance(raw, bytes)
    value = json.loads(raw.decode("utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"Expected JSON object at {revision}:{path}")
    return value


def clean_manifest_path(value: str) -> str:
    path = value[2:] if value.startswith("./") else value
    posix = PurePosixPath(path)
    if posix.is_absolute() or not posix.parts or any(part in {"", ".", ".."} for part in posix.parts):
        raise ValueError(f"Unsafe promoted Skill path: {value}")
    return posix.as_posix().rstrip("/")


def local_markdown_targets(content: bytes) -> list[str]:
    text = content.decode("utf-8", errors="replace")
    targets: list[str] = []
    for match in re.finditer(r"\]\(([^)]+)\)", text):
        target = match.group(1).strip().strip("<>").split(maxsplit=1)[0]
        target = target.split("#", 1)[0].split("?", 1)[0]
        if not target or target.startswith(("#", "/", "\\")):
            continue
        if re.match(r"^[A-Za-z][A-Za-z0-9+.-]*:", target):
            continue
        targets.append(target)
    return targets


def inventory_git_directory(repository: Path, revision: str, root: str) -> dict[str, Any]:
    tree_oid = git(repository, "rev-parse", f"{revision}:{root}")
    listing = git(repository, "ls-tree", "-r", "-z", revision, "--", root, text=False)
    assert isinstance(listing, bytes)
    files: list[dict[str, Any]] = []
    total_bytes = 0
    script_count = 0
    out_of_root_links: list[dict[str, str]] = []
    entrypoint: dict[str, Any] | None = None
    prefix = root.rstrip("/") + "/"
    for record in listing.split(b"\0"):
        if not record:
            continue
        header, encoded_path = record.split(b"\t", 1)
        mode, kind, object_id = header.decode("ascii").split()
        if kind != "blob":
            raise ValueError(f"Unsupported Git tree entry {kind} under {root}")
        path = encoded_path.decode("utf-8")
        if not path.startswith(prefix):
            raise ValueError(f"Git listing escaped promoted root: {path}")
        relative = path[len(prefix):]
        content = git(repository, "cat-file", "blob", object_id, text=False)
        assert isinstance(content, bytes)
        item = {
            "path": relative,
            "mode": mode,
            "gitBlob": object_id,
            "bytes": len(content),
            "sha256": sha256_bytes(content),
            "newlineNormalizedSha256": sha256_bytes(normalized_bytes(content)),
        }
        files.append(item)
        total_bytes += len(content)
        if PurePosixPath(relative).suffix.lower() in SCRIPT_SUFFIXES:
            script_count += 1
        if PurePosixPath(relative).suffix.lower() in {".md", ".txt", ".json", ".yaml", ".yml"}:
            for target in local_markdown_targets(content):
                joined = posixpath.normpath(posixpath.join(posixpath.dirname(relative), target))
                if joined == ".." or joined.startswith("../"):
                    out_of_root_links.append({"source": relative, "target": target})
        if relative == "SKILL.md":
            entrypoint = item
    if entrypoint is None:
        raise ValueError(f"Promoted directory lacks SKILL.md: {root}")
    files.sort(key=lambda item: item["path"].casefold())
    return {
        "sourcePath": root,
        "treeOid": tree_oid,
        "fileCount": len(files),
        "bytes": total_bytes,
        "scriptLikeFileCount": script_count,
        "outOfRootMarkdownLinks": sorted(
            out_of_root_links, key=lambda item: (item["source"], item["target"])
        ),
        "entrypoint": entrypoint,
        "treeSha256": canonical_digest(
            [{"path": item["path"], "sha256": item["sha256"]} for item in files]
        ),
        "newlineNormalizedTreeSha256": canonical_digest(
            [
                {"path": item["path"], "sha256": item["newlineNormalizedSha256"]}
                for item in files
            ]
        ),
        "files": files,
    }


def manifest_inventory(repository: Path, revision: str) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    manifest = load_git_json(repository, revision, ".claude-plugin/plugin.json")
    raw_paths = manifest.get("skills")
    if not isinstance(raw_paths, list) or not all(isinstance(item, str) for item in raw_paths):
        raise ValueError("Plugin manifest skills must be a string list")
    paths = [clean_manifest_path(item) for item in raw_paths]
    if len(paths) != len(set(paths)):
        raise ValueError("Plugin manifest contains duplicate paths")
    records: list[dict[str, Any]] = []
    names: set[str] = set()
    for path in paths:
        name = PurePosixPath(path).name
        if name in names:
            raise ValueError(f"Promoted Skill name is not manager-unique: {name}")
        names.add(name)
        record = inventory_git_directory(repository, revision, path)
        record["name"] = name
        records.append(record)
    return manifest, records


def recursive_skill_paths(repository: Path, revision: str) -> list[str]:
    output = git(repository, "ls-tree", "-r", "--name-only", revision, "--", "skills")
    assert isinstance(output, str)
    return sorted(
        str(PurePosixPath(path).parent)
        for path in output.splitlines()
        if path.endswith("/SKILL.md")
    )


def inventory_local_directory(root: Path) -> dict[str, Any] | None:
    if not root.exists():
        return None
    if root.is_symlink() or not root.is_dir():
        return {"unsupported": True, "path": root.as_posix()}
    files: list[dict[str, str]] = []
    for path in sorted(root.rglob("*"), key=lambda item: item.as_posix().lower()):
        if path.is_symlink():
            files.append(
                {
                    "path": path.relative_to(root).as_posix(),
                    "sha256": canonical_digest({"symlink": os.readlink(path)}),
                    "newlineNormalizedSha256": canonical_digest({"symlink": os.readlink(path)}),
                }
            )
        elif path.is_file():
            content = path.read_bytes()
            files.append(
                {
                    "path": path.relative_to(root).as_posix(),
                    "sha256": sha256_bytes(content),
                    "newlineNormalizedSha256": sha256_bytes(normalized_bytes(content)),
                }
            )
    files.sort(key=lambda item: item["path"].casefold())
    return {
        "path": root.as_posix(),
        "treeSha256": canonical_digest(
            [{"path": item["path"], "sha256": item["sha256"]} for item in files]
        ),
        "newlineNormalizedTreeSha256": canonical_digest(
            [
                {"path": item["path"], "sha256": item["newlineNormalizedSha256"]}
                for item in files
            ]
        ),
        "fileCount": len(files),
    }


def classify_payload(
    name: str,
    local: dict[str, Any] | None,
    promoted_by_name: dict[str, dict[str, Any]],
    prior_by_name: dict[str, dict[str, Any]],
) -> str:
    if local is None:
        return "missing"
    local_digest = local.get("newlineNormalizedTreeSha256")
    matches_release = (
        name in promoted_by_name
        and local_digest == promoted_by_name[name]["newlineNormalizedTreeSha256"]
    )
    matches_prior = (
        name in prior_by_name
        and local_digest == prior_by_name[name]["newlineNormalizedTreeSha256"]
    )
    if matches_release and matches_prior:
        return "both-prior-and-release"
    if matches_release:
        return "release-only"
    if matches_prior:
        return "prior-only"
    return "neither"


def consumer_topology(
    roots: list[Path],
    names: list[str],
    promoted_by_name: dict[str, dict[str, Any]],
    prior_by_name: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for root in roots:
        resolved_root = root.resolve()
        entries: list[dict[str, Any]] = []
        for name in names:
            path = resolved_root / name
            if not path.exists() and not path.is_symlink():
                continue
            if path.is_symlink():
                kind = "symlink"
                target = str(path.resolve())
                payload_root = path.resolve()
            elif path.is_dir():
                kind = "directory"
                target = None
                payload_root = path
            else:
                kind = "other"
                target = None
                payload_root = path
            local = inventory_local_directory(payload_root)
            entries.append(
                {
                    "name": name,
                    "kind": kind,
                    "target": target,
                    "classification": classify_payload(
                        name, local, promoted_by_name, prior_by_name
                    ),
                }
            )
        classifications = {
            classification: sum(
                entry["classification"] == classification for entry in entries
            )
            for classification in (
                "both-prior-and-release",
                "prior-only",
                "release-only",
                "neither",
                "missing",
            )
        }
        result.append(
            {
                "root": resolved_root.as_posix(),
                "presentCount": len(entries),
                "symlinkCount": sum(entry["kind"] == "symlink" for entry in entries),
                "directoryCount": sum(entry["kind"] == "directory" for entry in entries),
                "classificationCounts": classifications,
                "entries": entries,
            }
        )
    return result


def snapshot_path(root: Path) -> str:
    if not root.exists() and not root.is_symlink():
        return canonical_digest({"exists": False, "path": root.as_posix()})
    records: list[dict[str, Any]] = []
    if root.is_file() or root.is_symlink():
        paths = [root]
        base = root.parent
    else:
        paths = []
        base = root
        for current, directories, filenames in os.walk(root, followlinks=False):
            current_path = Path(current)
            for name in sorted(directories + filenames):
                paths.append(current_path / name)
    for path in sorted(paths, key=lambda item: item.as_posix().lower()):
        relative = path.relative_to(base).as_posix()
        if path.is_symlink():
            records.append({"path": relative, "kind": "symlink", "target": os.readlink(path)})
        elif path.is_file():
            records.append({"path": relative, "kind": "file", "sha256": sha256_file(path)})
        elif path.is_dir():
            records.append({"path": relative, "kind": "directory"})
        else:
            records.append({"path": relative, "kind": "other"})
    return canonical_digest(records)


def read_manager_rows(database: Path) -> tuple[list[dict[str, Any]], str, str]:
    before = sha256_file(database)
    connection = sqlite3.connect(f"{database.resolve().as_uri()}?mode=ro", uri=True)
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
        rows = [
            dict(zip(selected, values, strict=True))
            for values in connection.execute(f"SELECT {', '.join(selected)} FROM skills").fetchall()
        ]
    finally:
        connection.close()
    return rows, before, sha256_file(database)


def build_report(args: argparse.Namespace) -> dict[str, Any]:
    source_git = args.source_git.resolve()
    cc_home = args.cc_home.resolve()
    require_object(source_git, args.release_tag_object, "tag", "release tag object")
    require_object(source_git, args.release_commit, "commit", "release commit")
    require_object(source_git, args.observed_main_revision, "commit", "observed main revision")
    require_object(source_git, args.prior_revision, "commit", "prior revision")
    tag_body = git(source_git, "cat-file", "-p", args.release_tag_object)
    assert isinstance(tag_body, str)
    tag_object_line = next(
        (line.split(maxsplit=1)[1] for line in tag_body.splitlines() if line.startswith("object ")),
        None,
    )
    tag_name_line = next(
        (line.split(maxsplit=1)[1] for line in tag_body.splitlines() if line.startswith("tag ")),
        None,
    )
    if tag_object_line != args.release_commit or tag_name_line != args.release_tag:
        raise ValueError("Release tag object does not bind the requested tag and release commit")
    ancestry = subprocess.run(
        ["git", "-C", str(source_git), "merge-base", "--is-ancestor", args.prior_revision, args.release_commit]
    )
    if ancestry.returncode != 0:
        raise ValueError("Prior revision is not an ancestor of the release commit")

    release_manifest, promoted = manifest_inventory(source_git, args.release_commit)
    prior_manifest, prior_promoted = manifest_inventory(source_git, args.prior_revision)
    promoted_by_name = {item["name"]: item for item in promoted}
    prior_by_name = {item["name"]: item for item in prior_promoted}
    recursive_paths = recursive_skill_paths(source_git, args.release_commit)
    recursive_names = [PurePosixPath(path).name for path in recursive_paths]
    non_promoted_paths = sorted(set(recursive_paths) - {item["sourcePath"] for item in promoted})

    database = cc_home / "cc-switch.db"
    all_rows, database_before, database_after = read_manager_rows(database)
    if database_before != database_after:
        raise RuntimeError("Read-only manager query changed database bytes")
    rows = sorted(
        [
            row
            for row in all_rows
            if row.get("repo_owner") == args.repo_owner and row.get("repo_name") == args.repo_name
        ],
        key=lambda row: str(row.get("directory", "")),
    )
    directories = [str(row.get("directory", "")) for row in rows]
    if len(directories) != len(set(directories)):
        raise ValueError("Matt manager rows contain duplicate directories")

    ssot_before = snapshot_path(cc_home / "skills")
    consumer_before = {root.resolve().as_posix(): snapshot_path(root.resolve()) for root in args.consumer_root}
    classifications: list[dict[str, Any]] = []
    counts = {
        "both-prior-and-release": 0,
        "prior-only": 0,
        "release-only": 0,
        "neither": 0,
        "missing": 0,
    }
    for row in rows:
        name = str(row.get("directory", ""))
        local = inventory_local_directory(cc_home / "skills" / name)
        classification = classify_payload(name, local, promoted_by_name, prior_by_name)
        counts[classification] += 1
        classifications.append(
            {
                "name": name,
                "classification": classification,
                "local": local,
                "enabledApps": {
                    app: bool(row.get(f"enabled_{app}", 0)) for app in SUPPORTED_APPS
                },
            }
        )
    ssot_after = snapshot_path(cc_home / "skills")
    consumer_after = {root.resolve().as_posix(): snapshot_path(root.resolve()) for root in args.consumer_root}
    if ssot_before != ssot_after or consumer_before != consumer_after:
        raise RuntimeError("Read-only preview changed manager SSOT or consumer bytes")

    release_names = sorted(promoted_by_name)
    live_names = sorted(directories)
    added = sorted(set(release_names) - set(live_names))
    removed = sorted(set(live_names) - set(release_names))
    retained = sorted(set(release_names) & set(live_names))
    enabled_counts = {
        app: sum(bool(row.get(f"enabled_{app}", 0)) for row in rows) for app in SUPPORTED_APPS
    }
    consumer_names = sorted(set(release_names) | set(live_names))
    consumers = consumer_topology(
        args.consumer_root, consumer_names, promoted_by_name, prior_by_name
    )
    direct_consumer_directories = [
        {"root": consumer["root"], "names": sorted(
            entry["name"] for entry in consumer["entries"] if entry["kind"] == "directory"
        )}
        for consumer in consumers
        if consumer["directoryCount"]
    ]
    script_like_total = sum(item["scriptLikeFileCount"] for item in promoted)
    out_of_root_total = sum(len(item["outOfRootMarkdownLinks"]) for item in promoted)
    license_blob = git(source_git, "rev-parse", f"{args.release_commit}:LICENSE")
    license_content = git(source_git, "cat-file", "blob", str(license_blob), text=False)
    assert isinstance(license_content, bytes)

    report: dict[str, Any] = {
        "schema": 1,
        "status": "preview-only-zero-live-mutation",
        "observation": {
            "observedAt": normalized_observed_at(args.observed_at),
            "reportIncludesMutableLiveSnapshot": True,
            "managerDatabaseByteStableWithinRun": database_before == database_after,
            "crossRunReportByteIdentityRequired": False,
        },
        "source": {
            "repository": "mattpocock/skills",
            "releaseTag": args.release_tag,
            "releaseTagObject": args.release_tag_object,
            "releaseCommit": args.release_commit,
            "releaseVersion": release_manifest.get("version"),
            "observedMainRevision": args.observed_main_revision,
            "priorRevision": args.prior_revision,
            "tagObjectPeelsToReleaseCommit": tag_object_line == args.release_commit,
            "observedMainEqualsReleaseCommit": args.observed_main_revision == args.release_commit,
            "priorIsAncestorOfRelease": True,
            "license": {
                "path": "LICENSE",
                "gitBlob": license_blob,
                "bytes": len(license_content),
                "sha256": sha256_bytes(license_content),
            },
        },
        "discovery": {
            "authority": ".claude-plugin/plugin.json",
            "promotedCount": len(promoted),
            "recursiveSkillCount": len(recursive_paths),
            "promotedNames": release_names,
            "recursiveNames": sorted(recursive_names),
            "nonPromotedNames": sorted(PurePosixPath(path).name for path in non_promoted_paths),
            "nonPromotedPaths": non_promoted_paths,
            "wholeTreeDiscoveryWouldIncludeNonPromotedCount": len(non_promoted_paths),
            "priorPromotedCount": len(prior_promoted),
        },
        "promotedPayloads": promoted,
        "dependencySurface": {
            "scriptLikeFileCount": script_like_total,
            "outOfRootMarkdownLinkCount": out_of_root_total,
            "operationalDependencyClosureProved": script_like_total == 0 and out_of_root_total == 0,
        },
        "liveManager": {
            "databasePath": database.as_posix(),
            "databaseSha256Before": database_before,
            "databaseSha256After": database_after,
            "databaseReadOnly": database_before == database_after,
            "sourceRowCount": len(rows),
            "sourceNames": live_names,
            "enabledCountByHost": enabled_counts,
            "payloadClassifications": classifications,
            "payloadClassificationCounts": counts,
            "ssotSnapshotBefore": ssot_before,
            "ssotSnapshotAfter": ssot_after,
            "consumerSnapshotsBefore": consumer_before,
            "consumerSnapshotsAfter": consumer_after,
        },
        "transition": {
            "add": added,
            "remove": removed,
            "retainOrReplace": retained,
            "addCount": len(added),
            "removeCount": len(removed),
            "retainOrReplaceCount": len(retained),
            "perItemBestEffortRefreshSuitable": False,
        },
        "consumerTopology": {
            "roots": consumers,
            "symlinkCountTotal": sum(item["symlinkCount"] for item in consumers),
            "directDirectoryCountTotal": sum(item["directoryCount"] for item in consumers),
            "directDirectories": direct_consumer_directories,
            "singleManagerRevisionClosureProved": not direct_consumer_directories,
        },
        "transaction": {
            "kind": "preview-only-exact-release-manifest-atomic-cohort",
            "selectionAuthority": ".claude-plugin/plugin.json",
            "targetRevision": args.release_commit,
            "atomicPromotedCohortCount": len(promoted),
            "executionEligible": False,
            "blockers": [
                "preview carries no CC Switch update authority",
                "live rows are enabled and require a separately authorized bounded transition",
                "whole-tree discovery would include non-promoted Skill paths",
                "direct same-name consumer directories prevent single-manager revision closure",
                "manager atomic update and rollback behavior is not exercised by this preview",
            ],
            "requiredRollbackBoundary": {
                "database": database_before,
                "managerSsot": ssot_before,
                "consumers": consumer_before,
            },
        },
        "executionCounters": {
            "networkCallsByBuilder": 0,
            "thirdPartyScriptExecutions": 0,
            "managerInvocations": 0,
            "managerMutations": 0,
            "consumerWrites": 0,
            "modelCalls": 0,
        },
        "claimBoundary": {
            "exactReleaseTagAndCommitVerified": True,
            "promotedManifestInventoried": True,
            "recursiveDiscoveryInventoried": True,
            "liveManagerRowsReadOnlyObserved": True,
            "livePayloadsComparedWithNewlineNormalization": True,
            "consumerProjectionTopologyObserved": True,
            "singleManagerRevisionClosureAcrossConsumersProved": not direct_consumer_directories,
            "managerUpdateImplementedOrExecuted": False,
            "consumerExposureProved": False,
            "instructionDeliveryProved": False,
            "invocationProved": False,
            "behaviorProved": False,
            "valueProved": False,
            "crossHostPortabilityProved": False,
        },
    }
    report["sourceProjectionSha256"] = canonical_digest(
        {
            key: report[key]
            for key in ("source", "discovery", "promotedPayloads", "dependencySurface")
        }
    )
    report["reportSha256"] = canonical_digest(report)
    return report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-git", type=Path, required=True)
    parser.add_argument("--release-tag", required=True)
    parser.add_argument("--release-tag-object", required=True)
    parser.add_argument("--release-commit", required=True)
    parser.add_argument("--observed-main-revision", required=True)
    parser.add_argument("--prior-revision", required=True)
    parser.add_argument("--observed-at", required=True)
    parser.add_argument("--cc-home", type=Path, required=True)
    parser.add_argument("--consumer-root", type=Path, action="append", default=[])
    parser.add_argument("--repo-owner", default="mattpocock")
    parser.add_argument("--repo-name", default="skills")
    parser.add_argument("--output", type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = build_report(args)
    rendered = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.output is None:
        print(rendered, end="")
    else:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8", newline="\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
