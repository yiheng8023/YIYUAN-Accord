#!/usr/bin/env python3
"""Materialize the exact current Matt semantic-authority composition."""

from __future__ import annotations

import argparse
import base64
import json
from pathlib import Path
import time
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

try:
    from .build_source_pinned_skill_projection import (
        _verify_content,
        canonical_sha256,
        git_blob_sha1,
        sha256_bytes,
    )
except ImportError:
    from build_source_pinned_skill_projection import (
        _verify_content,
        canonical_sha256,
        git_blob_sha1,
        sha256_bytes,
    )


ROOT = Path(__file__).resolve().parent.parent
ADMISSION_PATH = (
    ROOT
    / "registry"
    / "human-ai-collaboration-semantic-authority-current-matt-static-admission-2026-07-28.json"
)
CANDIDATE_ID = "matt.current.grill-with-docs-composition"
EXPECTED_SKILL_NAMES = {
    "grill-with-docs",
    "domain-modeling",
    "grilling",
}


def _github_rest_read(
    repository: str,
    revision: str,
    relative_path: str,
) -> bytes:
    """Read one public file at an exact revision through GitHub REST."""
    endpoint = (
        "https://api.github.com/repos/"
        f"{quote(repository, safe='/')}/contents/"
        f"{quote(relative_path, safe='/')}?ref={quote(revision, safe='')}"
    )
    request = Request(
        endpoint,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": "agent-autonomy-harness-sem03-projection",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    payload: bytes | None = None
    last_error: BaseException | None = None
    for attempt in range(4):
        try:
            with urlopen(request, timeout=30) as response:
                payload = response.read()
            break
        except (HTTPError, URLError, TimeoutError, OSError) as error:
            last_error = error
            if attempt < 3:
                time.sleep(2**attempt)
    if payload is None:
        raise RuntimeError(
            f"unable to read pinned GitHub object after bounded retries: {relative_path}"
        ) from last_error
    try:
        decoded = json.loads(payload)
        encoded = decoded["content"]
        if decoded.get("encoding") != "base64" or not isinstance(encoded, str):
            raise ValueError("unexpected GitHub content encoding")
        return base64.b64decode(encoded, validate=False)
    except (json.JSONDecodeError, KeyError, TypeError, ValueError) as error:
        raise RuntimeError(
            f"invalid pinned GitHub content response: {relative_path}"
        ) from error


def load_admission(path: Path = ADMISSION_PATH) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _projection_parts(source_path: str) -> tuple[str, str]:
    parts = Path(source_path).parts
    if len(parts) < 4 or parts[0] != "skills":
        raise RuntimeError(f"unsupported composition source path: {source_path}")
    skill_name = parts[2]
    relative = Path(*parts[3:]).as_posix()
    if skill_name not in EXPECTED_SKILL_NAMES or not relative:
        raise RuntimeError(f"unexpected composition package path: {source_path}")
    return skill_name, relative


def materialize_composition(
    output_root: Path,
    *,
    admission: dict[str, Any] | None = None,
    allow_existing: bool = False,
    github_reader: Callable[[str, str, str], bytes] | None = None,
) -> dict[str, Any]:
    admission = admission or load_admission()
    output_root = output_root.resolve()
    if output_root.exists():
        if not output_root.is_dir():
            raise RuntimeError("composition output is not a directory")
        if any(output_root.iterdir()) and not allow_existing:
            raise RuntimeError("composition output must not already contain files")
    else:
        output_root.mkdir(parents=True)
    for protected in (
        output_root / ".agents",
        output_root / ".aah-provenance",
        output_root / "SEMANTIC-AUTHORITY-COMPOSITION-PROJECTION.json",
    ):
        if protected.exists():
            raise RuntimeError("composition projection namespace already exists")

    source = admission["source"]
    revision = source["revision"]
    repository = source["repository"].removeprefix("https://github.com/").removesuffix(
        ".git"
    )
    reader = github_reader or _github_rest_read
    verified_package: list[tuple[dict[str, Any], bytes]] = []
    for record in admission["exactPackageFiles"]:
        source_path = record["path"]
        content = reader(repository, revision, source_path)
        _verify_content(content, record, label=source_path)
        _projection_parts(source_path)
        verified_package.append((record, content))
    license_record = admission["license"]
    license_content = reader(repository, revision, license_record["path"])
    _verify_content(license_content, license_record, label=license_record["path"])

    projected_files: list[dict[str, Any]] = []
    skill_paths: dict[str, str] = {}
    for record, content in verified_package:
        source_path = record["path"]
        skill_name, relative = _projection_parts(source_path)
        destination = (
            output_root / ".agents" / "skills" / skill_name / relative
        ).resolve()
        skill_root = (
            output_root / ".agents" / "skills" / skill_name
        ).resolve()
        if not destination.is_relative_to(skill_root):
            raise RuntimeError("composition projection path escaped Skill root")
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(content)
        projected_files.append(
            {
                "path": destination.relative_to(output_root).as_posix(),
                "sourcePath": source_path,
                "skillName": skill_name,
                "bytes": len(content),
                "sha256": sha256_bytes(content),
                "gitBlobSha1": git_blob_sha1(content),
            }
        )
        if relative == "SKILL.md":
            skill_paths[skill_name] = destination.as_posix()

    if set(skill_paths) != EXPECTED_SKILL_NAMES:
        raise RuntimeError("composition projection is missing a Skill entry")
    license_path = (
        output_root / ".aah-provenance" / CANDIDATE_ID / "LICENSE"
    )
    license_path.parent.mkdir(parents=True, exist_ok=True)
    license_path.write_bytes(license_content)

    manifest = {
        "schema": 1,
        "id": f"semantic-authority-composition-projection:{CANDIDATE_ID}",
        "status": "materialized-no-host-turn",
        "candidateId": CANDIDATE_ID,
        "entrySkillName": "grill-with-docs",
        "requiredSkillNames": sorted(EXPECTED_SKILL_NAMES),
        "sourceLocator": {
            "mode": "github-rest-api-exact-revision",
            "repository": repository,
            "revision": revision,
            "externalReadOnly": True,
        },
        "projectionRoot": output_root.as_posix(),
        "skillPaths": dict(sorted(skill_paths.items())),
        "projectedFiles": projected_files,
        "projectedTreeSha256": canonical_sha256(projected_files),
        "license": {
            "path": license_path.relative_to(output_root).as_posix(),
            "spdx": license_record["spdx"],
            "bytes": len(license_content),
            "sha256": sha256_bytes(license_content),
        },
        "sourceMutated": False,
        "globalConfigMutated": False,
        "installedSkillMutated": False,
        "ccSwitchMutated": False,
        "hostTurnStarted": False,
    }
    manifest["manifestSha256"] = canonical_sha256(manifest)
    manifest_path = (
        output_root / "SEMANTIC-AUTHORITY-COMPOSITION-PROJECTION.json"
    )
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--allow-existing", action="store_true")
    args = parser.parse_args()
    manifest = materialize_composition(
        args.output,
        allow_existing=args.allow_existing,
    )
    print(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
