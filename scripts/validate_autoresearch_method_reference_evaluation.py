#!/usr/bin/env python3
"""Validate the source-bound autoresearch method-reference evaluation."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

try:
    from .validate_multidimensional_software_engineering_evaluation_report import (
        validate_report,
    )
except ImportError:  # pragma: no cover - direct script execution
    from validate_multidimensional_software_engineering_evaluation_report import (
        validate_report,
    )


ROOT = Path(__file__).resolve().parent.parent
SNAPSHOT_PATH = ROOT / "registry/autoresearch-exact-source-snapshot-2026-08-05.json"
EVALUATION_PATH = (
    ROOT
    / "registry/autoresearch-multidimensional-software-engineering-evaluation-2026-08-05.json"
)
DOCUMENT_PATH = (
    ROOT / "docs/strategy/AUTORESEARCH-METHOD-REFERENCE-EVALUATION-2026-08-05.md"
)
EXPECTED_REVISION = "228791fb499afffb54b46200aca536f79142f117"
EXPECTED_OBJECTS = {
    "README.md": ("blob", "953ea55d5599c45c1be7dad93ec03e47dfa7df9d", 8039),
    "prepare.py": ("blob", "06bea9165abd3ae94ea82dd733997aec7928f40c", 15043),
    "program.md": ("blob", "dea9bcc0174f1502d0ba64000b94b81ba605855b", 7039),
    "pyproject.toml": ("blob", "94ae3298925ddae47821f703faf44d4e3b8381bb", 543),
    "train.py": ("blob", "2e743974c7f06b54311643b314712303fbb26e65", 26230),
    "uv.lock": ("blob", "c840d62f5285b5ce4b5fe62f135cfe8a47bc9915", 443159),
}
EXPECTED_MANIFEST_SHA256 = (
    "5a16f3c29ebe513afa5be3bbf3dec1a2c323c1428d64da9ad9d961bddc3afa93"
)


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def _load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    _require(isinstance(value, dict), f"{path.name} must contain one object")
    return value


def _manifest_sha256(objects: list[dict[str, Any]]) -> str:
    rows = [
        f"{item['path']}\t{item['type']}\t{item['oid']}\t{item['size']}"
        for item in objects
    ]
    return hashlib.sha256("\n".join(sorted(rows)).encode("utf-8")).hexdigest()


def validate_autoresearch_evaluation(
    *,
    snapshot: dict[str, Any] | None = None,
    evaluation: dict[str, Any] | None = None,
    root: Path = ROOT,
) -> None:
    snapshot = snapshot or _load(root / SNAPSHOT_PATH.relative_to(ROOT))
    evaluation = evaluation or _load(root / EVALUATION_PATH.relative_to(ROOT))

    _require(snapshot.get("schemaVersion") == 1, "Source snapshot version drifted")
    _require(snapshot.get("revision") == EXPECTED_REVISION, "Source revision drifted")
    _require(
        snapshot.get("revisionObservation", {}).get("observedRevision")
        == EXPECTED_REVISION,
        "Observed source revision drifted",
    )
    objects = snapshot.get("gitObjects", [])
    _require(len(objects) == len(EXPECTED_OBJECTS), "Git object inventory is incomplete")
    observed_objects = {
        item.get("path"): (item.get("type"), item.get("oid"), item.get("size"))
        for item in objects
    }
    _require(observed_objects == EXPECTED_OBJECTS, "Git object identity drifted")
    observed_manifest = _manifest_sha256(objects)
    _require(
        observed_manifest == EXPECTED_MANIFEST_SHA256
        and snapshot.get("gitObjectManifestSha256") == observed_manifest,
        "Git object manifest digest drifted",
    )

    observations = snapshot.get("mutableObservations", [])
    _require(len(observations) == 1, "Mutable counterevidence inventory drifted")
    issue = observations[0]
    _require(
        issue.get("locator") == "https://github.com/karpathy/autoresearch/issues/599"
        and issue.get("observedState") == "open"
        and issue.get("claimUse")
        == "external-observational-counterevidence-only",
        "Mutable counterevidence boundary drifted",
    )
    _require(
        snapshot.get("licenseArtifactStatus") == "not-observed-at-revision"
        and snapshot.get("securityPolicyArtifactStatus")
        == "not-observed-at-revision",
        "Unobserved rights or security artifacts were promoted",
    )
    _require(
        snapshot.get("authorityBoundary")
        == {
            "upstreamDownloadAuthorized": False,
            "upstreamExecutionAuthorized": False,
            "dependencyInstallationAuthorized": False,
            "skillOrRuntimeActivationAuthorized": False,
            "directAdoptionAuthorized": False,
        },
        "Source snapshot authority boundary drifted",
    )

    validate_report(evaluation)
    _require(
        evaluation["targetIdentity"]["revision"] == EXPECTED_REVISION,
        "Evaluation target revision drifted",
    )
    _require(
        set(evaluation["applicableDimensions"])
        == {
            item["dimensionId"] for item in evaluation["dimensionResults"]
        }
        and len(evaluation["applicableDimensions"]) == 12,
        "Evaluation does not cover all twelve declared dimensions",
    )
    floors = {item["floorId"]: item["result"] for item in evaluation["floorResults"]}
    _require(
        floors.get("evidence-truth-and-provenance") == "blocked"
        and floors.get("authority-and-data-boundary") == "blocked",
        "Direct-adoption floors are no longer blocked",
    )
    _require(
        evaluation.get("statusClaim") == "research-only"
        and evaluation["independentReview"]["status"] == "not-performed"
        and evaluation["acceptanceAuthority"]["status"] == "not-sought",
        "Research-only review or acceptance boundary drifted",
    )
    claim_boundary = evaluation.get("claimBoundary", "")
    for phrase in ("not installed", "not executed", "not admitted"):
        _require(phrase in claim_boundary, f"Evaluation claim boundary missing: {phrase}")

    document = (root / DOCUMENT_PATH.relative_to(ROOT)).read_text(encoding="utf-8")
    normalized = " ".join(document.split())
    for phrase in (
        "high-value external method reference",
        "direct Harness adoption is blocked",
        "What is reusable",
        "What must not be transplanted",
        "trusted evaluator must sit outside the mutable agent surface",
    ):
        _require(phrase in normalized, f"Decision document missing: {phrase}")


def main() -> int:
    validate_autoresearch_evaluation()
    print("Autoresearch method-reference evaluation validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
