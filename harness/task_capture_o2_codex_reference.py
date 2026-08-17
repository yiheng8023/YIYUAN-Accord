"""Pure native-to-public projection builder for the v1.2 O2 Codex suite.

The builder never launches Codex, installs a plugin, or stores native events.
It accepts bounded bytes already emitted by the native host (normally over a
pipe), validates the fixed source contract, and writes only privacy-reduced
data to stdout.  It is task-specific evidence plumbing, not a host runtime.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import sys
from typing import Any


BUILDER_KIND = "o2-codex-public-projection-builder-v1"
BUILDER_LOCATOR = "harness/task_capture_o2_codex_reference.py"
SOURCE_CONTRACT_REVISION = "be6e8eac029b183056b7e4402879f15d2c85f61b"
SOURCE_EVENTS_LOCATOR = "sdk/typescript/src/events.ts"
SOURCE_ITEMS_LOCATOR = "sdk/typescript/src/items.ts"
MAX_NATIVE_JSON_BYTES = 1_048_576
MAX_NATIVE_JSONL_BYTES = 2_097_152
MAX_NATIVE_JSONL_LINES = 128
MAX_JSON_DEPTH = 32
MAX_JSON_NODES = 10_000
MAX_CONTAINER_ITEMS = 256
MAX_STRING_CHARACTERS = 262_144
MAX_FILES = 64
MAX_DIRECTORIES = 64
MAX_FILE_BYTES = 16_777_216
MAX_TOTAL_FILE_BYTES = 16_777_216
MAX_RELATIVE_DEPTH = 8
PLUGIN_ID_PATTERN = re.compile(
    r"[a-z0-9][a-z0-9._-]{0,63}@[a-z0-9][a-z0-9._-]{0,63}"
)
VERSION_PATTERN = re.compile(r"[0-9A-Za-z][0-9A-Za-z.+-]{0,127}")
SHA256_PATTERN = re.compile(r"[0-9a-f]{64}")
IDENTITY_PATTERN = re.compile(r"[a-z0-9][a-z0-9._:-]{0,127}")
KNOWN_ITEM_TYPES = {
    "agent_message",
    "reasoning",
    "command_execution",
    "file_change",
    "todo_list",
}


def _sha256(value: Any) -> bool:
    return isinstance(value, str) and SHA256_PATTERN.fullmatch(value) is not None


def _identity(value: Any) -> bool:
    return isinstance(value, str) and IDENTITY_PATTERN.fullmatch(value) is not None


def _json_within_limits(value: Any) -> bool:
    nodes = 0
    stack: list[tuple[Any, int]] = [(value, 1)]
    while stack:
        current, depth = stack.pop()
        nodes += 1
        if nodes > MAX_JSON_NODES or depth > MAX_JSON_DEPTH:
            return False
        if isinstance(current, str):
            if len(current) > MAX_STRING_CHARACTERS:
                return False
        elif isinstance(current, dict):
            if len(current) > MAX_CONTAINER_ITEMS:
                return False
            for key, item in current.items():
                if not isinstance(key, str) or len(key) > MAX_STRING_CHARACTERS:
                    return False
                stack.append((item, depth + 1))
        elif isinstance(current, list):
            if len(current) > MAX_CONTAINER_ITEMS:
                return False
            stack.extend((item, depth + 1) for item in current)
    return True


def _strict_json_object(raw: bytes, *, max_bytes: int) -> dict[str, Any]:
    if not raw or len(raw) > max_bytes:
        raise ValueError("native JSON byte limit")

    def reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        value: dict[str, Any] = {}
        for key, item in pairs:
            if key in value:
                raise ValueError("duplicate native JSON key")
            value[key] = item
        return value

    try:
        value = json.loads(
            raw.decode("utf-8"),
            object_pairs_hook=reject_duplicate_keys,
            parse_constant=lambda _: (_ for _ in ()).throw(
                ValueError("non-finite native JSON value")
            ),
        )
    except (json.JSONDecodeError, RecursionError, UnicodeError) as exc:
        raise ValueError("invalid native JSON") from exc
    if not isinstance(value, dict) or not _json_within_limits(value):
        raise ValueError("native JSON resource limit")
    return value


def _builder_binding(builder_revision: str, builder_sha256: str) -> dict[str, str]:
    if (
        not isinstance(builder_revision, str)
        or re.fullmatch(r"[0-9a-f]{40}", builder_revision) is None
        or not _sha256(builder_sha256)
    ):
        raise ValueError("projection builder digest")
    return {
        "kind": BUILDER_KIND,
        "locator": BUILDER_LOCATOR,
        "revision": builder_revision,
        "sha256": builder_sha256,
        "sourceContractRevision": SOURCE_CONTRACT_REVISION,
    }


def build_plugin_list_projection(
    raw: bytes,
    *,
    environment_identity: str,
    codex_version: str,
    builder_revision: str,
    builder_sha256: str,
) -> dict[str, Any]:
    """Reduce native ``codex plugin list --json`` output to public state."""

    if not _identity(environment_identity) or re.fullmatch(
        r"[0-9]+\.[0-9]+\.[0-9]+(?:[-+][0-9A-Za-z.-]+)?", codex_version
    ) is None:
        raise ValueError("plugin projection identity")
    value = _strict_json_object(raw, max_bytes=MAX_NATIVE_JSON_BYTES)
    if set(value) != {"installed", "available"}:
        raise ValueError("native plugin list shape")
    installed = value.get("installed")
    available = value.get("available")
    if (
        not isinstance(installed, list)
        or len(installed) > MAX_FILES
        or not isinstance(available, list)
        or len(available) > MAX_FILES
    ):
        raise ValueError("native plugin list bounds")
    records: list[dict[str, Any]] = []
    seen: set[str] = set()
    required = {
        "pluginId",
        "name",
        "marketplaceName",
        "version",
        "installed",
        "enabled",
        "source",
        "installPolicy",
        "authPolicy",
    }
    for item in installed:
        if not isinstance(item, dict) or not required <= set(item):
            raise ValueError("native plugin record shape")
        extras = set(item) - required
        if extras not in (set(), {"marketplaceSource"}):
            raise ValueError("native plugin record shape")
        plugin_id = item.get("pluginId")
        version = item.get("version")
        source = item.get("source")
        marketplace = item.get("marketplaceSource")
        if (
            not isinstance(plugin_id, str)
            or PLUGIN_ID_PATTERN.fullmatch(plugin_id) is None
            or plugin_id in seen
            or not isinstance(version, str)
            or VERSION_PATTERN.fullmatch(version) is None
            or item.get("installed") is not True
            or type(item.get("enabled")) is not bool
            or not isinstance(source, dict)
            or set(source) != {"source", "path"}
            or source.get("source") not in {"local", "git"}
            or not isinstance(source.get("path"), str)
            or not source["path"]
            or not isinstance(item.get("name"), str)
            or not isinstance(item.get("marketplaceName"), str)
            or item.get("installPolicy") not in {"AVAILABLE", "REQUIRED", "BLOCKED"}
            or item.get("authPolicy") not in {"ON_INSTALL", "ON_USE", "NONE"}
        ):
            raise ValueError("native plugin record identity")
        if marketplace is not None:
            if (
                not isinstance(marketplace, dict)
                or set(marketplace) != {"sourceType", "source"}
                or marketplace.get("sourceType") not in {"local", "git"}
                or not isinstance(marketplace.get("source"), str)
                or not marketplace["source"]
            ):
                raise ValueError("native marketplace identity")
            source_type = (
                "local-marketplace"
                if marketplace["sourceType"] == "local"
                else "remote"
            )
        else:
            source_type = "local" if source["source"] == "local" else "remote"
        seen.add(plugin_id)
        records.append(
            {
                "pluginId": plugin_id,
                "version": version,
                "installed": True,
                "enabled": item["enabled"],
                "sourceType": source_type,
            }
        )
    return {
        "schema": 1,
        "captureKind": "codex-plugin-list-public-projection",
        "environmentIdentity": environment_identity,
        "codexVersion": codex_version,
        "projectionBuilder": _builder_binding(builder_revision, builder_sha256),
        "plugins": sorted(records, key=lambda item: item["pluginId"]),
    }


def _usage_valid(value: Any) -> bool:
    return (
        isinstance(value, dict)
        and set(value)
        == {
            "input_tokens",
            "cached_input_tokens",
            "cache_write_input_tokens",
            "output_tokens",
            "reasoning_output_tokens",
        }
        and all(type(item) is int and item >= 0 for item in value.values())
    )


def _item_identity(item: Any) -> tuple[str, str]:
    if not isinstance(item, dict):
        raise ValueError("native item shape")
    identity = item.get("id")
    item_type = item.get("type")
    if (
        not isinstance(identity, str)
        or not identity
        or len(identity) > 128
        or item_type not in KNOWN_ITEM_TYPES
    ):
        raise ValueError("native item identity")
    return identity, item_type


def _completed_item_projection(item: dict[str, Any]) -> dict[str, Any] | None:
    _, item_type = _item_identity(item)
    if item_type == "agent_message":
        if set(item) != {"id", "type", "text"} or not isinstance(
            item.get("text"), str
        ):
            raise ValueError("native agent message")
        return {
            "type": "item.completed",
            "itemType": "agent_message",
            "messageSha256": hashlib.sha256(item["text"].encode("utf-8")).hexdigest(),
        }
    if item_type == "reasoning":
        if set(item) != {"id", "type", "text"} or not isinstance(
            item.get("text"), str
        ):
            raise ValueError("native reasoning item")
        return None
    if item_type == "todo_list":
        if set(item) != {"id", "type", "items"} or not isinstance(
            item.get("items"), list
        ):
            raise ValueError("native todo item")
        return None
    if item_type == "command_execution":
        if set(item) != {
            "id",
            "type",
            "command",
            "aggregated_output",
            "exit_code",
            "status",
        }:
            raise ValueError("native command completion")
        exit_code = item.get("exit_code")
        if (
            not isinstance(item.get("command"), str)
            or not isinstance(item.get("aggregated_output"), str)
            or type(exit_code) is not int
            or not -255 <= exit_code <= 255
            or item.get("status") not in {"completed", "failed"}
        ):
            raise ValueError("native command completion")
        return {
            "type": "item.completed",
            "itemType": "action_completion",
            "exitCode": exit_code,
        }
    if item_type == "file_change":
        if set(item) != {"id", "type", "changes", "status"} or not isinstance(
            item.get("changes"), list
        ) or len(item["changes"]) > MAX_FILES or item.get("status") not in {
            "completed",
            "failed",
        }:
            raise ValueError("native file change completion")
        for change in item["changes"]:
            if (
                not isinstance(change, dict)
                or set(change) != {"path", "kind"}
                or not isinstance(change.get("path"), str)
                or change.get("kind") not in {"add", "delete", "update"}
            ):
                raise ValueError("native file change identity")
        return {
            "type": "item.completed",
            "itemType": "action_completion",
            "exitCode": 0 if item["status"] == "completed" else 1,
        }
    raise ValueError("unsupported native item")


def _in_progress_item_valid(item: dict[str, Any]) -> bool:
    _, item_type = _item_identity(item)
    if item_type == "command_execution":
        return (
            set(item) == {"id", "type", "command", "aggregated_output", "status"}
            and isinstance(item.get("command"), str)
            and isinstance(item.get("aggregated_output"), str)
            and item.get("status") == "in_progress"
        )
    if item_type == "file_change":
        return (
            set(item) == {"id", "type", "changes", "status"}
            and isinstance(item.get("changes"), list)
            and item.get("status") in {"completed", "failed"}
        )
    if item_type in {"reasoning", "agent_message"}:
        return set(item) == {"id", "type", "text"} and isinstance(
            item.get("text"), str
        )
    if item_type == "todo_list":
        return set(item) == {"id", "type", "items"} and isinstance(
            item.get("items"), list
        )
    return False


def build_exec_projection(
    raw: bytes,
    *,
    scenario_identity: str,
    phase: str,
    codex_version: str,
    goal_sha256: str,
    builder_revision: str,
    builder_sha256: str,
) -> dict[str, Any]:
    """Reduce one successful native ``codex exec --json`` stream."""

    if (
        not raw
        or len(raw) > MAX_NATIVE_JSONL_BYTES
        or not _identity(scenario_identity)
        or phase not in {"single", "pre-grant", "post-grant"}
        or re.fullmatch(
            r"[0-9]+\.[0-9]+\.[0-9]+(?:[-+][0-9A-Za-z.-]+)?", codex_version
        )
        is None
        or not _sha256(goal_sha256)
    ):
        raise ValueError("exec projection identity")
    lines = raw.splitlines()
    if not 4 <= len(lines) <= MAX_NATIVE_JSONL_LINES or any(not line for line in lines):
        raise ValueError("native JSONL envelope")
    events = [
        _strict_json_object(line, max_bytes=MAX_NATIVE_JSON_BYTES) for line in lines
    ]
    first = events[0]
    if (
        set(first) != {"type", "thread_id"}
        or first.get("type") != "thread.started"
        or not isinstance(first.get("thread_id"), str)
        or not first["thread_id"]
        or len(first["thread_id"]) > 128
        or events[1] != {"type": "turn.started"}
    ):
        raise ValueError("native JSONL start envelope")
    last = events[-1]
    if (
        set(last) != {"type", "usage"}
        or last.get("type") != "turn.completed"
        or not _usage_valid(last.get("usage"))
    ):
        raise ValueError("native JSONL completion envelope")
    projected: list[dict[str, Any]] = [
        {"type": "thread.started"},
        {"type": "turn.started"},
    ]
    agent_messages = 0
    for event in events[2:-1]:
        event_type = event.get("type")
        if event_type in {"turn.failed", "error"}:
            raise ValueError("native execution failed")
        if event_type not in {"item.started", "item.updated", "item.completed"} or set(
            event
        ) != {"type", "item"}:
            raise ValueError("native event type")
        item = event.get("item")
        if event_type == "item.completed":
            projection = _completed_item_projection(item)
            if projection is not None:
                if projection.get("itemType") == "agent_message":
                    agent_messages += 1
                projected.append(projection)
        elif not isinstance(item, dict) or not _in_progress_item_valid(item):
            raise ValueError("native in-progress item")
    if agent_messages != 1:
        raise ValueError("native agent message count")
    projected.append({"type": "turn.completed"})
    return {
        "schema": 1,
        "captureKind": "codex-jsonl-public-projection",
        "scenarioIdentity": scenario_identity,
        "phase": phase,
        "codexVersion": codex_version,
        "goalSha256": goal_sha256,
        "projectionBuilder": _builder_binding(builder_revision, builder_sha256),
        "events": projected,
    }


def _reparse_or_link(path: Path, metadata: os.stat_result) -> bool:
    attributes = getattr(metadata, "st_file_attributes", 0)
    reparse_flag = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
    return path.is_symlink() or bool(attributes & reparse_flag)


def build_filesystem_projection(
    root: Path,
    *,
    scenario_identity: str,
    phase: str,
    builder_revision: str,
    builder_sha256: str,
) -> dict[str, Any]:
    """Build a bounded manifest of one isolated scenario root."""

    if not _identity(scenario_identity) or phase not in {
        "before",
        "after",
        "pre-grant",
        "post-grant",
    }:
        raise ValueError("filesystem projection identity")
    try:
        canonical_root = root.resolve(strict=True)
        root_metadata = canonical_root.lstat()
    except (OSError, RuntimeError) as exc:
        raise ValueError("filesystem root") from exc
    if not canonical_root.is_dir() or _reparse_or_link(canonical_root, root_metadata):
        raise ValueError("filesystem root identity")
    records: list[dict[str, Any]] = []
    directories = 0
    total_bytes = 0
    for directory, directory_names, file_names in os.walk(
        canonical_root, topdown=True, followlinks=False
    ):
        directories += 1
        if directories > MAX_DIRECTORIES:
            raise ValueError("filesystem directory limit")
        current = Path(directory)
        relative_directory = current.relative_to(canonical_root)
        if len(relative_directory.parts) > MAX_RELATIVE_DEPTH:
            raise ValueError("filesystem depth limit")
        for name in tuple(directory_names):
            candidate = current / name
            metadata = candidate.lstat()
            if _reparse_or_link(candidate, metadata) or not stat.S_ISDIR(metadata.st_mode):
                raise ValueError("filesystem linked directory")
        for name in file_names:
            candidate = current / name
            metadata = candidate.lstat()
            if _reparse_or_link(candidate, metadata) or not stat.S_ISREG(metadata.st_mode):
                raise ValueError("filesystem linked file")
            relative = candidate.relative_to(canonical_root)
            if len(relative.parts) > MAX_RELATIVE_DEPTH:
                raise ValueError("filesystem depth limit")
            relative_text = PurePosixPath(*relative.parts).as_posix()
            if (
                not relative_text
                or any(part in {"", ".", ".."} for part in relative.parts)
                or len(relative_text) > 220
            ):
                raise ValueError("filesystem relative path")
            size = metadata.st_size
            total_bytes += size
            if (
                size < 0
                or size > MAX_FILE_BYTES
                or total_bytes > MAX_TOTAL_FILE_BYTES
                or len(records) >= MAX_FILES
            ):
                raise ValueError("filesystem byte or file limit")
            raw = candidate.read_bytes()
            if len(raw) != size:
                raise ValueError("filesystem file changed during capture")
            records.append(
                {
                    "path": relative_text,
                    "sha256": hashlib.sha256(raw).hexdigest(),
                    "size": size,
                }
            )
    return {
        "schema": 1,
        "captureKind": "task-owned-filesystem-manifest",
        "scenarioIdentity": scenario_identity,
        "phase": phase,
        "projectionBuilder": _builder_binding(builder_revision, builder_sha256),
        "files": sorted(records, key=lambda item: item["path"]),
    }


def _write_projection(value: dict[str, Any]) -> None:
    sys.stdout.buffer.write(
        (json.dumps(value, ensure_ascii=False, sort_keys=True) + "\n").encode("utf-8")
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build public O2 projections from native Codex bytes"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    plugin = subparsers.add_parser("plugin-list")
    plugin.add_argument("--environment-identity", required=True)
    plugin.add_argument("--codex-version", required=True)
    plugin.add_argument("--builder-revision", required=True)
    plugin.add_argument("--builder-sha256", required=True)
    execution = subparsers.add_parser("exec-jsonl")
    execution.add_argument("--scenario-identity", required=True)
    execution.add_argument("--phase", required=True)
    execution.add_argument("--codex-version", required=True)
    execution.add_argument("--goal-sha256", required=True)
    execution.add_argument("--builder-revision", required=True)
    execution.add_argument("--builder-sha256", required=True)
    filesystem = subparsers.add_parser("filesystem")
    filesystem.add_argument("--root", required=True)
    filesystem.add_argument("--scenario-identity", required=True)
    filesystem.add_argument("--phase", required=True)
    filesystem.add_argument("--builder-revision", required=True)
    filesystem.add_argument("--builder-sha256", required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "plugin-list":
            value = build_plugin_list_projection(
                sys.stdin.buffer.read(MAX_NATIVE_JSON_BYTES + 1),
                environment_identity=args.environment_identity,
                codex_version=args.codex_version,
                builder_revision=args.builder_revision,
                builder_sha256=args.builder_sha256,
            )
        elif args.command == "exec-jsonl":
            value = build_exec_projection(
                sys.stdin.buffer.read(MAX_NATIVE_JSONL_BYTES + 1),
                scenario_identity=args.scenario_identity,
                phase=args.phase,
                codex_version=args.codex_version,
                goal_sha256=args.goal_sha256,
                builder_revision=args.builder_revision,
                builder_sha256=args.builder_sha256,
            )
        else:
            value = build_filesystem_projection(
                Path(args.root),
                scenario_identity=args.scenario_identity,
                phase=args.phase,
                builder_revision=args.builder_revision,
                builder_sha256=args.builder_sha256,
            )
    except (OSError, ValueError) as exc:
        print(f"projection failed closed: {exc}", file=sys.stderr)
        return 2
    _write_projection(value)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = [
    "BUILDER_KIND",
    "BUILDER_LOCATOR",
    "SOURCE_CONTRACT_REVISION",
    "SOURCE_EVENTS_LOCATOR",
    "SOURCE_ITEMS_LOCATOR",
    "build_exec_projection",
    "build_filesystem_projection",
    "build_plugin_list_projection",
    "main",
]
