#!/usr/bin/env python3
"""Atomically project the exact five-file current self-authored control chain."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import uuid
from typing import Any

try:
    from scripts.probe_codex_app_server_skill_exposure import canonical_sha256
except ModuleNotFoundError:  # pragma: no cover - direct script execution
    from probe_codex_app_server_skill_exposure import canonical_sha256


ROOT = Path(__file__).resolve().parent.parent
PROTOCOL_PATH = ROOT / (
    "registry/human-ai-collaboration-self-authored-control-chain-"
    "factorial-ablation-protocol-2026-07-28.json"
)
DEFAULT_SOURCE_ROOT = Path("C:/Users/15521/.agents/skills")
MANIFEST_NAME = "SELF-AUTHORED-CONTROL-CHAIN-PROJECTION.json"


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _expected_files(protocol: dict[str, Any]) -> list[dict[str, Any]]:
    chain = protocol["factors"]["chain"]
    records = [
        {
            "skillName": row["name"],
            "relativePath": "SKILL.md",
            "bytes": row["bytes"],
            "sha256": row["sha256"],
            "role": "skill-entry",
        }
        for row in chain["exactSkillPins"]
    ]
    records.extend(
        {
            "skillName": row["skillName"],
            "relativePath": row["relativePath"],
            "bytes": row["bytes"],
            "sha256": row["sha256"],
            "role": "referenced-instruction",
        }
        for row in chain["exactDependencyPins"]
    )
    return sorted(
        records,
        key=lambda row: (row["skillName"], row["relativePath"]),
    )


def materialize_current_chain(
    output_root: Path,
    *,
    source_root: Path = DEFAULT_SOURCE_ROOT,
    protocol: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Verify all source bytes first, then atomically publish one projection."""

    protocol = protocol or json.loads(PROTOCOL_PATH.read_text(encoding="utf-8"))
    output_root = output_root.resolve()
    source_root = source_root.resolve()
    if output_root.exists():
        raise RuntimeError("control-chain projection output must not already exist")
    expected = _expected_files(protocol)

    verified: list[tuple[dict[str, Any], bytes, Path]] = []
    for record in expected:
        source = (
            source_root / record["skillName"] / record["relativePath"]
        ).resolve()
        skill_root = (source_root / record["skillName"]).resolve()
        if not source.is_relative_to(skill_root) or not source.is_file():
            raise RuntimeError(
                f"control-chain source missing or escaped: "
                f"{record['skillName']}/{record['relativePath']}"
            )
        payload = source.read_bytes()
        if (
            len(payload) != record["bytes"]
            or _sha256_bytes(payload) != record["sha256"]
        ):
            raise RuntimeError(
                f"control-chain source digest drifted: "
                f"{record['skillName']}/{record['relativePath']}"
            )
        verified.append((record, payload, source))

    staging = output_root.with_name(
        f"{output_root.name}.partial-{uuid.uuid4().hex}"
    )
    if staging.exists():
        raise RuntimeError("control-chain projection staging collision")
    projected_files: list[dict[str, Any]] = []
    skill_paths: dict[str, str] = {}
    try:
        for record, payload, source in verified:
            destination = (
                staging
                / ".agents"
                / "skills"
                / record["skillName"]
                / record["relativePath"]
            ).resolve()
            projected_skill_root = (
                staging / ".agents" / "skills" / record["skillName"]
            ).resolve()
            if not destination.is_relative_to(projected_skill_root):
                raise RuntimeError("control-chain projection path escaped Skill root")
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(payload)
            relative = destination.relative_to(staging).as_posix()
            projected_files.append(
                {
                    "skillName": record["skillName"],
                    "relativePath": record["relativePath"],
                    "role": record["role"],
                    "path": relative,
                    "sourcePath": source.as_posix(),
                    "bytes": len(payload),
                    "sha256": _sha256_bytes(payload),
                }
            )
            if record["relativePath"] == "SKILL.md":
                final_destination = (
                    output_root
                    / ".agents"
                    / "skills"
                    / record["skillName"]
                    / record["relativePath"]
                ).resolve()
                skill_paths[record["skillName"]] = final_destination.as_posix()

        if set(skill_paths) != {
            "intent-contract",
            "capability-router",
            "closure-contract",
        }:
            raise RuntimeError("control-chain projection omitted a Skill entry")
        manifest = {
            "schema": 1,
            "id": "self-authored-control-chain-projection:current-five-file",
            "status": "materialized-no-host-turn",
            "protocol": str(PROTOCOL_PATH.relative_to(ROOT)).replace("\\", "/"),
            "projectionRoot": output_root.as_posix(),
            "sourceRoot": source_root.as_posix(),
            "requiredSkillNames": sorted(skill_paths),
            "requiredFileCount": len(projected_files),
            "skillPaths": dict(sorted(skill_paths.items())),
            "projectedFiles": projected_files,
            "projectedTreeSha256": canonical_sha256(projected_files),
            "sourceMutated": False,
            "globalConfigMutated": False,
            "installedSkillMutated": False,
            "ccSwitchMutated": False,
            "liveHookConfigMutated": False,
            "hostThreadStarted": False,
            "hostTurnStarted": False,
        }
        manifest["manifestSha256"] = canonical_sha256(manifest)
        (staging / MANIFEST_NAME).write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
            newline="\n",
        )
        staging.replace(output_root)
        return manifest
    except BaseException:
        if staging.exists():
            shutil.rmtree(staging)
        raise


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--source-root", type=Path, default=DEFAULT_SOURCE_ROOT)
    args = parser.parse_args()
    manifest = materialize_current_chain(
        args.output,
        source_root=args.source_root,
    )
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
