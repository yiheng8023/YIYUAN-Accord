#!/usr/bin/env python3
"""Validate the source-pinned debugging projection protocol."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent


def validate_protocol(
    document: dict[str, Any],
    *,
    root: Path = ROOT,
) -> list[str]:
    failures: list[str] = []
    if (
        document.get("schema") != 1
        or document.get("id")
        != "source-pinned-debugging-skill-projection-protocol-2026-07-24"
        or document.get("date") != "2026-07-24"
        or document.get("status")
        != "two-candidate-materialization-and-no-turn-inventory-preflight-pass"
    ):
        failures.append("fail-identity")

    task = document.get("taskBinding", {})
    for key in (
        "scenarioId",
        "capabilityGap",
        "dataBoundary",
        "authorityBoundary",
        "verificationSurface",
    ):
        if not task.get(key):
            failures.append(f"fail-task-binding-{key}")

    candidates = {
        item.get("candidateId"): item
        for item in document.get("candidates", [])
        if isinstance(item, dict)
    }
    if set(candidates) != {
        "matt.current-diagnosing-bugs",
        "superpowers.runtime-6.1.1-systematic-debugging",
    }:
        failures.append("fail-candidate-coverage")
        return failures

    matt = candidates["matt.current-diagnosing-bugs"]
    matt_source = matt.get("source", {})
    if (
        matt.get("skillName") != "diagnosing-bugs"
        or matt_source.get("revision")
        != "ed37663cc5fbef691ddfecd080dff42f7e7e350d"
        or matt_source.get("sourceCheckoutHeadEqualsSelectedRevision") is not False
        or matt_source.get("readMode")
        != "git-show-immutable-revision-never-working-tree"
        or len(matt.get("files", [])) != 3
    ):
        failures.append("fail-matt-source-pin")

    superpowers = candidates[
        "superpowers.runtime-6.1.1-systematic-debugging"
    ]
    sp_source = superpowers.get("source", {})
    sp_files = superpowers.get("files", [])
    upstream_matches = [
        item.get("publicUpstreamMatch")
        for item in sp_files
        if isinstance(item, dict)
    ]
    if (
        superpowers.get("skillName") != "systematic-debugging"
        or sp_source.get("packageVersion") != "6.1.1"
        or sp_source.get("publicTag") != "v6.1.1"
        or sp_source.get("publicTagRevision")
        != "c984ea2e7aeffdcc865784fd6c5e3ab75da0209a"
        or len(sp_files) != 12
        or upstream_matches.count(False) != 1
        or not any(
            item.get("projectionRelativePath") == "agents/openai.yaml"
            and item.get("publicUpstreamMatch") is False
            for item in sp_files
        )
    ):
        failures.append("fail-superpowers-source-pin")

    for candidate in candidates.values():
        license_record = candidate.get("license", {})
        if (
            license_record.get("spdx") != "MIT"
            or license_record.get("noticeMustAccompanySubstantialCopy") is not True
        ):
            failures.append("fail-license-boundary")
        files = candidate.get("files", [])
        projection_paths = [
            item.get("projectionRelativePath")
            for item in files
            if isinstance(item, dict)
        ]
        if (
            len(projection_paths) != len(set(projection_paths))
            or "SKILL.md" not in projection_paths
        ):
            failures.append("fail-projection-file-set")
        for item in files:
            if (
                not item.get("sourceRelativePath")
                or not item.get("projectionRelativePath")
                or not isinstance(item.get("bytes"), int)
                or item["bytes"] <= 0
                or len(str(item.get("sha256", ""))) != 64
                or len(str(item.get("gitBlobSha1", ""))) != 40
            ):
                failures.append("fail-file-pin")
                break

    dependencies = superpowers.get("dependencyBoundary", {})
    if (
        dependencies.get("crossSkillReferencesNotProjected")
        != [
            "superpowers:test-driven-development",
            "superpowers:verification-before-completion",
        ]
        or dependencies.get("fullSuperpowersOrchestrationEquivalenceProved")
        is not False
    ):
        failures.append("fail-superpowers-dependency-boundary")

    projection = document.get("projectionContract", {})
    for key in (
        "sourceMutationAllowed",
        "existingOutputOverwriteAllowed",
        "globalConfigMutationAllowed",
        "installedSkillMutationAllowed",
        "networkRequiredAtProjectionTime",
        "skillBodyRewriteAllowed",
    ):
        if projection.get(key) is not False:
            failures.append(f"hard-fail-projection-{key}")

    gate = document.get("livePreflightGate", {})
    if not gate or any(value is not True for value in gate.values()):
        failures.append("fail-live-preflight-gate")

    claim_boundary = document.get("claimBoundary", {})
    if (
        not claim_boundary
        or any(value is not False for value in claim_boundary.values())
    ):
        failures.append("hard-fail-claim-promotion")

    for path in (
        document.get("builder"),
        document.get("preflightProbe"),
        document.get("validator"),
        document.get("tests"),
        document.get("preflightTests"),
        document.get("livePreflightEvidence"),
        document.get("documentation"),
    ):
        if not isinstance(path, str) or not (root / path).is_file():
            failures.append("fail-artifact-link")

    doc_path = root / str(document.get("documentation", ""))
    if doc_path.is_file():
        doc = " ".join(doc_path.read_text(encoding="utf-8").split())
        for phrase in (
            "must not reuse the installed historical `diagnose` body as “current Matt,”",
            "git show",
            "OpenAI runtime metadata extension",
            "not projected in the first single-Skill arm",
            "does not prove an independent loader event",
            "Both candidates were materialized into separate disposable roots",
            "No installation, update, cleanup, commit, or push",
        ):
            if phrase not in doc:
                failures.append(f"fail-doc-phrase:{phrase}")

    return list(dict.fromkeys(failures))


def main() -> int:
    path = (
        ROOT
        / "registry"
        / "source-pinned-debugging-skill-projection-protocol-2026-07-24.json"
    )
    document = json.loads(path.read_text(encoding="utf-8"))
    failures = validate_protocol(document)
    print(
        json.dumps(
            {
                "id": document.get("id"),
                "status": "pass" if not failures else "fail",
                "failures": failures,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
