#!/usr/bin/env python3
"""Validate durable no-turn evidence for source-pinned Skill projections."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent


def validate_evidence(
    document: dict[str, Any],
    *,
    protocol: dict[str, Any],
    root: Path = ROOT,
) -> list[str]:
    failures: list[str] = []
    if (
        document.get("schema") != 1
        or document.get("id")
        != "source-pinned-debugging-skill-projection-preflight-evidence-2026-07-24"
        or document.get("date") != "2026-07-24"
        or document.get("status")
        != "two-candidate-materialization-and-no-turn-inventory-isolation-pass"
    ):
        failures.append("fail-identity")
    if (
        protocol.get("livePreflightEvidence")
        != "registry/source-pinned-debugging-skill-projection-preflight-evidence-2026-07-24.json"
        or protocol.get("status")
        != "two-candidate-materialization-and-no-turn-inventory-preflight-pass"
    ):
        failures.append("fail-protocol-binding")
    expected = {
        "matt.current-diagnosing-bugs": {
            "skillName": "diagnosing-bugs",
            "projectedTreeSha256": "4160945a04d86a2602f59657ae647d6997ee796c53926f9cdbf498548d42edc6",
            "projectionManifestSha256": "723454de86e3a663620f3deaf6c50d6ae65e2631b61d10c11bd4fecf181d9e6b",
        },
        "superpowers.runtime-6.1.1-systematic-debugging": {
            "skillName": "systematic-debugging",
            "projectedTreeSha256": "4a06537def2b81a56b1d63173fd96dd947c2f80f3f4062db7bea77249bad97d8",
            "projectionManifestSha256": "cc3fb8b1362254e5811f8e49c362ed0a9b35ed9068ba7b648ec9fd49b14f819d",
        },
    }
    results = {
        item.get("candidateId"): item
        for item in document.get("results", [])
        if isinstance(item, dict)
    }
    if set(results) != set(expected):
        failures.append("fail-result-coverage")
        return failures
    for candidate_id, pins in expected.items():
        result = results[candidate_id]
        for key, value in pins.items():
            if result.get(key) != value:
                failures.append(f"fail-pin:{candidate_id}:{key}")
        control = result.get("controlInventory", {})
        if (
            control.get("skillCount") != 112
            or control.get("countsByScope")
            != {"repo": 1, "system": 6, "user": 105}
            or result.get("unselectedEnabledCountsByScope")
            != {"repo": 0, "system": 6, "user": 0}
            or result.get("selectedEnabledCountsByScope")
            != {"repo": 1, "system": 6, "user": 0}
        ):
            failures.append(f"fail-inventory:{candidate_id}")
        for key in (
            "projectionTreeStable",
            "globalConfigStable",
            "repositoryStatusStable",
        ):
            if result.get(key) is not True:
                failures.append(f"fail-stability:{candidate_id}:{key}")
        if (
            result.get("threadStarted") is not False
            or result.get("turnStarted") is not False
        ):
            failures.append(f"hard-fail-turn:{candidate_id}")
        for key in (
            "rawReportFileSha256",
            "rawReportInternalSha256",
        ):
            if len(str(result.get(key, ""))) != 64:
                failures.append(f"fail-report-digest:{candidate_id}:{key}")

    claims = document.get("claimBoundary", {})
    if not claims or any(value is not False for value in claims.values()):
        failures.append("hard-fail-claim-promotion")
    for path in (
        document.get("validator"),
        document.get("tests"),
        document.get("documentation"),
    ):
        if not isinstance(path, str) or not (root / path).is_file():
            failures.append("fail-artifact-link")
    doc_path = root / str(document.get("documentation", ""))
    if doc_path.is_file():
        doc = " ".join(doc_path.read_text(encoding="utf-8").split())
        for phrase in (
            "one repository Skill, six system Skills, and 105 user Skills",
            "zero configurable Skills",
            "No thread or model turn started",
            "does not prove candidate body delivery",
            "not eligible for deletion until the total control plan reaches final closeout",
        ):
            if phrase not in doc:
                failures.append(f"fail-doc-phrase:{phrase}")
    return list(dict.fromkeys(failures))


def main() -> int:
    evidence = json.loads(
        (
            ROOT
            / "registry"
            / "source-pinned-debugging-skill-projection-preflight-evidence-2026-07-24.json"
        ).read_text(encoding="utf-8")
    )
    protocol = json.loads(
        (
            ROOT
            / "registry"
            / "source-pinned-debugging-skill-projection-protocol-2026-07-24.json"
        ).read_text(encoding="utf-8")
    )
    failures = validate_evidence(evidence, protocol=protocol)
    print(
        json.dumps(
            {
                "id": evidence.get("id"),
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
