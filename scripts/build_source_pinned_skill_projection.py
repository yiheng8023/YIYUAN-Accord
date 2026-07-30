#!/usr/bin/env python3
"""Build one byte-exact project Skill projection in a disposable root."""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
from pathlib import Path
import subprocess
from typing import Any, Callable


ROOT = Path(__file__).resolve().parent.parent
PROTOCOL_PATH = (
    ROOT
    / "registry"
    / "source-pinned-debugging-skill-projection-protocol-2026-07-24.json"
)


def sha256_bytes(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def git_blob_sha1(content: bytes) -> str:
    header = f"blob {len(content)}\0".encode("ascii")
    return hashlib.sha1(header + content).hexdigest()


def canonical_sha256(value: Any) -> str:
    return sha256_bytes(
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    )


def load_protocol(path: Path = PROTOCOL_PATH) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def candidate_by_id(
    protocol: dict[str, Any],
    candidate_id: str,
) -> dict[str, Any]:
    candidates = [
        *protocol.get("candidates", []),
        *protocol.get("projectionCandidates", []),
    ]
    matches = [
        candidate
        for candidate in candidates
        if candidate.get("candidateId") == candidate_id
    ]
    if len(matches) != 1:
        raise RuntimeError(f"candidate is not uniquely bound: {candidate_id}")
    return matches[0]


def _git_show(repo: Path, revision: str, relative_path: str) -> bytes:
    if not (repo / ".git").exists():
        raise RuntimeError("Matt source checkout is not a Git object store")
    result = subprocess.run(
        ["git", "-C", str(repo), "show", f"{revision}:{relative_path}"],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"unable to read pinned Git object: {relative_path}"
        )
    return result.stdout


def _safe_local_read(root: Path, relative_path: str) -> bytes:
    root = root.resolve()
    path = (root / relative_path).resolve()
    if not path.is_relative_to(root) or not path.is_file() or path.is_symlink():
        raise RuntimeError(f"unsafe or missing package source: {relative_path}")
    return path.read_bytes()


def _github_api_read(
    repository: str,
    revision: str,
    relative_path: str,
) -> bytes:
    endpoint = (
        f"repos/{repository}/contents/{relative_path}?ref={revision}"
    )
    result = subprocess.run(
        ["gh", "api", endpoint],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"unable to read pinned GitHub object: {relative_path}"
        )
    try:
        response = json.loads(result.stdout)
        encoded = response["content"]
        if response.get("encoding") != "base64" or not isinstance(encoded, str):
            raise ValueError("unexpected GitHub content encoding")
        return base64.b64decode(encoded, validate=False)
    except (json.JSONDecodeError, KeyError, TypeError, ValueError) as error:
        raise RuntimeError(
            f"invalid pinned GitHub content response: {relative_path}"
        ) from error


def _verify_content(
    content: bytes,
    record: dict[str, Any],
    *,
    label: str,
) -> None:
    if len(content) != record.get("bytes"):
        raise RuntimeError(f"{label} byte count drifted")
    if sha256_bytes(content) != str(record.get("sha256", "")).lower():
        raise RuntimeError(f"{label} SHA-256 drifted")
    if git_blob_sha1(content) != str(record.get("gitBlobSha1", "")).lower():
        raise RuntimeError(f"{label} Git blob drifted")


def materialize_candidate(
    candidate: dict[str, Any],
    output_root: Path,
    *,
    matt_checkout: Path | None = None,
    superpowers_package_root: Path | None = None,
    allow_existing: bool = False,
    github_reader: Callable[[str, str, str], bytes] | None = None,
) -> dict[str, Any]:
    output_root = output_root.resolve()
    if output_root.exists():
        if not output_root.is_dir():
            raise RuntimeError("projection output is not a directory")
        if any(output_root.iterdir()) and not allow_existing:
            raise RuntimeError("projection output must not already contain files")
    else:
        output_root.mkdir(parents=True)
    for protected in (
        output_root / ".agents",
        output_root / ".aah-provenance",
        output_root / "SOURCE-PINNED-SKILL-PROJECTION.json",
    ):
        if protected.exists():
            raise RuntimeError("projection namespace already exists")

    source = candidate["source"]
    source_class = candidate["sourceClass"]
    if source_class == "reviewed-maintained-external-public-git":
        if matt_checkout is None:
            raise RuntimeError("Matt source checkout is required")
        revision = source["revision"]

        def read(relative_path: str) -> bytes:
            return _git_show(matt_checkout.resolve(), revision, relative_path)

        source_locator = {
            "mode": source["readMode"],
            "revision": revision,
            "checkout": matt_checkout.resolve().as_posix(),
        }
    elif source_class == "reviewed-maintained-external-public-github-api":
        repository = source["githubRepository"]
        revision = source["revision"]
        reader = github_reader or _github_api_read

        def read(relative_path: str) -> bytes:
            return reader(repository, revision, relative_path)

        source_locator = {
            "mode": source["readMode"],
            "repository": repository,
            "revision": revision,
            "externalReadOnly": True,
        }
    elif source_class == "openai-curated-runtime-distributed-third-party":
        package_root = (
            superpowers_package_root
            if superpowers_package_root is not None
            else Path(source["packageRoot"])
        ).resolve()
        manifest_content = _safe_local_read(
            package_root,
            source["pluginManifestRelativePath"],
        )
        if (
            len(manifest_content) != source["pluginManifestBytes"]
            or sha256_bytes(manifest_content)
            != source["pluginManifestSha256"].lower()
        ):
            raise RuntimeError("Superpowers plugin manifest drifted")

        def read(relative_path: str) -> bytes:
            return _safe_local_read(package_root, relative_path)

        source_locator = {
            "mode": source["readMode"],
            "packageVersion": source["packageVersion"],
            "packageRoot": package_root.as_posix(),
            "pluginManifestSha256": sha256_bytes(manifest_content),
        }
    else:
        raise RuntimeError(f"unsupported source class: {source_class}")

    skill_root = (
        output_root
        / ".agents"
        / "skills"
        / candidate["skillName"]
    )
    projected_files: list[dict[str, Any]] = []
    for record in candidate["files"]:
        content = read(record["sourceRelativePath"])
        _verify_content(
            content,
            record,
            label=record["sourceRelativePath"],
        )
        destination = (skill_root / record["projectionRelativePath"]).resolve()
        if not destination.is_relative_to(skill_root.resolve()):
            raise RuntimeError("projection path escaped the selected Skill root")
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(content)
        projected_files.append(
            {
                "path": destination.relative_to(output_root).as_posix(),
                "bytes": len(content),
                "sha256": sha256_bytes(content),
                "gitBlobSha1": git_blob_sha1(content),
            }
        )

    license_record = candidate["license"]
    license_content = read(license_record["sourceRelativePath"])
    _verify_content(
        license_content,
        license_record,
        label=license_record["sourceRelativePath"],
    )
    license_path = (
        output_root
        / ".aah-provenance"
        / candidate["candidateId"]
        / "LICENSE"
    )
    license_path.parent.mkdir(parents=True, exist_ok=True)
    license_path.write_bytes(license_content)

    manifest = {
        "schema": 1,
        "id": f"source-pinned-skill-projection:{candidate['candidateId']}",
        "status": "materialized-no-host-turn",
        "candidateId": candidate["candidateId"],
        "skillName": candidate["skillName"],
        "sourceClass": source_class,
        "sourceLocator": source_locator,
        "projectionRoot": output_root.as_posix(),
        "skillPath": (skill_root / "SKILL.md").as_posix(),
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
        "hostTurnStarted": False,
    }
    manifest["manifestSha256"] = canonical_sha256(manifest)
    manifest_path = output_root / "SOURCE-PINNED-SKILL-PROJECTION.json"
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--protocol", type=Path, default=PROTOCOL_PATH)
    parser.add_argument(
        "--matt-checkout",
        type=Path,
        default=Path("C:/tmp/mattpocock-skills-current-9603c1c"),
    )
    parser.add_argument(
        "--superpowers-package-root",
        type=Path,
        default=Path(
            "C:/Users/15521/.codex/plugins/cache/"
            "openai-curated-remote/superpowers/6.1.1"
        ),
    )
    arguments = parser.parse_args()
    protocol = load_protocol(arguments.protocol)
    candidate = candidate_by_id(protocol, arguments.candidate)
    manifest = materialize_candidate(
        candidate,
        arguments.output,
        matt_checkout=arguments.matt_checkout,
        superpowers_package_root=arguments.superpowers_package_root,
    )
    print(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
