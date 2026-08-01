#!/usr/bin/env python3
"""Materialize the exact current Matt semantic-authority composition."""

from __future__ import annotations

import argparse
import base64
from contextlib import contextmanager, nullcontext
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import time
from typing import Any, Callable, Iterator
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


@contextmanager
def _pinned_git_object_reader(
    repository: str,
    revision: str,
    temporary_parent: Path,
    *,
    command_runner: Callable[..., Any] = subprocess.run,
) -> Iterator[Callable[[str, str, str], bytes]]:
    """Fetch one exact commit, then expose verified Git object reads."""
    temporary_parent = temporary_parent.resolve()
    if not temporary_parent.is_dir():
        raise RuntimeError("Git object temporary parent does not exist")
    environment = os.environ.copy()
    environment["GIT_TERMINAL_PROMPT"] = "0"

    def run(command: list[str], label: str) -> bytes:
        completed = command_runner(
            command,
            capture_output=True,
            check=False,
            env=environment,
            timeout=60,
        )
        if completed.returncode != 0:
            stderr = bytes(completed.stderr or b"")[:400].decode(
                "utf-8", errors="replace"
            )
            raise RuntimeError(f"{label} failed: {stderr}")
        return bytes(completed.stdout)

    with tempfile.TemporaryDirectory(
        prefix="aah-sem03-git-objects-",
        dir=temporary_parent,
    ) as temporary:
        object_root = Path(temporary).resolve() / "objects.git"
        run(
            ["git", "init", "--bare", "--quiet", str(object_root)],
            "temporary Git object database initialization",
        )
        remote = f"https://github.com/{repository}.git"
        run(
            [
                "git",
                "-C",
                str(object_root),
                "fetch",
                "--quiet",
                "--depth=1",
                remote,
                revision,
            ],
            "exact Git revision fetch",
        )
        observed_revision = run(
            [
                "git",
                "-C",
                str(object_root),
                "rev-parse",
                "FETCH_HEAD^{commit}",
            ],
            "fetched Git revision verification",
        ).decode("ascii", errors="strict").strip()
        if observed_revision != revision:
            raise RuntimeError("fetched Git revision identity drifted")

        def reader(
            requested_repository: str,
            requested_revision: str,
            relative_path: str,
        ) -> bytes:
            relative = Path(relative_path)
            if (
                requested_repository != repository
                or requested_revision != revision
                or relative.is_absolute()
                or ".." in relative.parts
            ):
                raise RuntimeError("Git object read escaped the pinned source")
            return run(
                [
                    "git",
                    "-C",
                    str(object_root),
                    "show",
                    f"FETCH_HEAD:{relative.as_posix()}",
                ],
                f"Git object read for {relative_path}",
            )

        yield reader


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
    source_transport: str = "github-rest-api-exact-revision",
    git_command_runner: Callable[..., Any] = subprocess.run,
) -> dict[str, Any]:
    admission = admission or load_admission()
    output_root = output_root.resolve()
    output_root.parent.mkdir(parents=True, exist_ok=True)
    output_existed = output_root.exists()
    if output_root.exists():
        if not output_root.is_dir():
            raise RuntimeError("composition output is not a directory")
        if any(output_root.iterdir()) and not allow_existing:
            raise RuntimeError("composition output must not already contain files")
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
    if github_reader is not None:
        reader_context = nullcontext(github_reader)
        effective_transport = "injected-reader-exact-revision"
    elif source_transport == "github-rest-api-exact-revision":
        reader_context = nullcontext(_github_rest_read)
        effective_transport = source_transport
    elif source_transport == "git-object-exact-revision":
        reader_context = _pinned_git_object_reader(
            repository,
            revision,
            output_root.parent,
            command_runner=git_command_runner,
        )
        effective_transport = source_transport
    else:
        raise RuntimeError(f"unsupported composition source transport: {source_transport}")
    verified_package: list[tuple[dict[str, Any], bytes]] = []
    with reader_context as reader:
        for record in admission["exactPackageFiles"]:
            source_path = record["path"]
            content = reader(repository, revision, source_path)
            _verify_content(content, record, label=source_path)
            _projection_parts(source_path)
            verified_package.append((record, content))
        license_record = admission["license"]
        license_content = reader(repository, revision, license_record["path"])
        _verify_content(
            license_content,
            license_record,
            label=license_record["path"],
        )

    staging_root = Path(
        tempfile.mkdtemp(
            prefix=f".{output_root.name}-sem03-staging-",
            dir=output_root.parent,
        )
    ).resolve()
    committed = False
    try:
        if output_existed:
            shutil.copytree(output_root, staging_root, dirs_exist_ok=True)
        projected_files: list[dict[str, Any]] = []
        skill_paths: dict[str, str] = {}
        for record, content in verified_package:
            source_path = record["path"]
            skill_name, relative = _projection_parts(source_path)
            staged_destination = (
                staging_root / ".agents" / "skills" / skill_name / relative
            ).resolve()
            staged_skill_root = (
                staging_root / ".agents" / "skills" / skill_name
            ).resolve()
            if not staged_destination.is_relative_to(staged_skill_root):
                raise RuntimeError("composition projection path escaped Skill root")
            staged_destination.parent.mkdir(parents=True, exist_ok=True)
            staged_destination.write_bytes(content)
            relative_destination = staged_destination.relative_to(staging_root)
            projected_files.append(
                {
                    "path": relative_destination.as_posix(),
                    "sourcePath": source_path,
                    "skillName": skill_name,
                    "bytes": len(content),
                    "sha256": sha256_bytes(content),
                    "gitBlobSha1": git_blob_sha1(content),
                }
            )
            if relative == "SKILL.md":
                skill_paths[skill_name] = (
                    output_root / relative_destination
                ).as_posix()

        if set(skill_paths) != EXPECTED_SKILL_NAMES:
            raise RuntimeError("composition projection is missing a Skill entry")
        staged_license_path = (
            staging_root / ".aah-provenance" / CANDIDATE_ID / "LICENSE"
        )
        staged_license_path.parent.mkdir(parents=True, exist_ok=True)
        staged_license_path.write_bytes(license_content)

        manifest = {
            "schema": 1,
            "id": f"semantic-authority-composition-projection:{CANDIDATE_ID}",
            "status": "materialized-no-host-turn",
            "candidateId": CANDIDATE_ID,
            "entrySkillName": "grill-with-docs",
            "requiredSkillNames": sorted(EXPECTED_SKILL_NAMES),
            "sourceLocator": {
                "mode": effective_transport,
                "repository": repository,
                "revision": revision,
                "externalReadOnly": True,
            },
            "projectionRoot": output_root.as_posix(),
            "skillPaths": dict(sorted(skill_paths.items())),
            "projectedFiles": projected_files,
            "projectedTreeSha256": canonical_sha256(projected_files),
            "license": {
                "path": staged_license_path.relative_to(staging_root).as_posix(),
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
        staged_manifest_path = (
            staging_root / "SEMANTIC-AUTHORITY-COMPOSITION-PROJECTION.json"
        )
        staged_manifest_path.write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
            newline="\n",
        )

        if output_existed:
            backup_root = Path(
                tempfile.mkdtemp(
                    prefix=f".{output_root.name}-sem03-backup-",
                    dir=output_root.parent,
                )
            ).resolve()
            backup_root.rmdir()
            os.replace(output_root, backup_root)
            try:
                os.replace(staging_root, output_root)
                committed = True
            except BaseException:
                os.replace(backup_root, output_root)
                raise
            shutil.rmtree(backup_root)
        else:
            os.replace(staging_root, output_root)
            committed = True
        return manifest
    finally:
        if not committed and staging_root.exists():
            shutil.rmtree(staging_root)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--allow-existing", action="store_true")
    parser.add_argument(
        "--source-transport",
        choices=(
            "github-rest-api-exact-revision",
            "git-object-exact-revision",
        ),
        default="github-rest-api-exact-revision",
    )
    args = parser.parse_args()
    manifest = materialize_composition(
        args.output,
        allow_existing=args.allow_existing,
        source_transport=args.source_transport,
    )
    print(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
