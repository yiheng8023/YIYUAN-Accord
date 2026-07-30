#!/usr/bin/env python3
"""Validate the source and adaptation review for the migration candidate."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
REVIEW_PATH = (
    "registry/deprecation-and-migration-local-adaptation-review-2026-07-24.json"
)


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def validate_review(document: dict[str, Any], *, root: Path = ROOT) -> None:
    _require(document.get("schema") == 1, "Adaptation review schema must be 1")
    _require(
        document.get("status") == "review-complete-candidate-not-live-validated"
        and document.get("candidateId") == "cc.deprecation-and-migration",
        "Adaptation review identity or status drifted",
    )

    upstream = document.get("upstreamPin", {})
    _require(
        upstream.get("revision")
        == "17214a29c429a19f7a9607f2c06f9d650ea87eb0"
        and upstream.get("skillBytes") == 9000
        and upstream.get("skillLines") == 206
        and upstream.get("skillSha256")
        == "bf2d9b4e3bc635b32e8de70b0ab41e4395d7b585e6474347c53ce89d45fbdb75"
        and upstream.get("skillGitBlobSha1")
        == "258e2a0396c9c2cb639cff84a9db64753740be96"
        and upstream.get("licenseId") == "MIT"
        and upstream.get("licenseSha256")
        == "6f202f8bd568cd730dbb2b0d1f8e243bc74c2fa1f64dbce9b2c7ea08bd5c9fd7",
        "Adaptation review upstream pin drifted",
    )
    _require(
        upstream.get("commitSignatureVerified") is False
        and upstream.get("commitSignatureReason") == "unsigned",
        "Adaptation review signature boundary drifted",
    )

    local = document.get("localPin", {})
    _require(
        local.get("bytes") == 12510
        and local.get("lines") == 266
        and local.get("sha256")
        == "52ef07de05726292c0f5e9fe666cc30e6efbe580ed775621e785a49ec80bd4ea"
        and local.get("gitBlobSha1")
        == "5ee5d33c24abd882e4704bacf5d399ffdb9b784e"
        and local.get("declaredLicense") == "MIT"
        and local.get("declaredAdaptedFor") == "cross-agent"
        and local.get("equalsPinnedUpstream") is False,
        "Adaptation review local pin drifted",
    )

    metrics = document.get("diffMetrics", {})
    _require(
        metrics.get("equalLines") == 170
        and metrics.get("upstreamLinesInReplacementBlocks") == 36
        and metrics.get("localLinesInReplacementBlocks") == 82
        and metrics.get("deletedUpstreamLinesOutsideReplacementBlocks") == 0
        and metrics.get("insertedLocalLinesOutsideReplacementBlocks") == 14
        and metrics.get("nonEqualBlocks") == 25
        and metrics.get("netLocalLineIncrease") == 60,
        "Adaptation review diff metrics drifted",
    )
    _require(
        abs(float(metrics.get("lineSequenceSimilarityRatio", 0)) - 0.720339)
        < 0.000001,
        "Adaptation review similarity ratio drifted",
    )

    areas = {
        item.get("area"): item
        for item in document.get("semanticReview", [])
        if isinstance(item, dict)
    }
    _require(
        set(areas)
        == {
            "authority-and-coordination",
            "value-and-carrying-cost",
            "replacement-and-controlled-withdrawal",
            "migration-shape",
            "consumer-accountability",
            "removal-readiness",
            "retention-and-history",
            "examples-and-executable-surface",
        },
        "Adaptation review semantic coverage drifted",
    )
    _require(
        areas["removal-readiness"].get("disposition")
        == "retain-critical-safety-adaptation"
        and areas["retention-and-history"].get("disposition")
        == "retain-critical-governance-adaptation",
        "Adaptation review critical disposition drifted",
    )

    provenance = document.get("licenseAndProvenanceReview", {})
    _require(
        provenance.get("upstreamRepositoryLicenseMatchesLocalDeclaration")
        is True
        and provenance.get("localAttributionPinsExactUpstreamRevisionAndPath")
        is True
        and provenance.get("localIsAnAdaptedDerivativeNotAnExactMirror") is True
        and provenance.get(
            "unsignedCommitTreatedAsMissingSignatureEvidenceNotAsACodeFailure"
        )
        is True
        and provenance.get("vendoringIntoThisRepositoryAuthorized") is False
        and provenance.get("copyingCandidateBodyIntoTrialPromptAuthorized")
        is False,
        "Adaptation review provenance or authority drifted",
    )

    disposition = document.get("disposition", {})
    _require(
        disposition.get("sourceAndAdaptationReviewPassed") is True
        and disposition.get("eligibleForDisposableFixturePreflight") is True
        and disposition.get("eligibleForLiveWeakAgentRunNow") is False
        and len(disposition.get("remainingGates", [])) == 6,
        "Adaptation review gate disposition drifted",
    )
    _require(
        all(value is False for value in document.get("claimBoundary", {}).values()),
        "Adaptation review claim boundary was promoted",
    )

    doc_path = root / str(document.get("documentation"))
    _require(doc_path.is_file(), "Adaptation review documentation is missing")
    text = " ".join(doc_path.read_text(encoding="utf-8").split())
    for phrase in (
        "missing signature evidence",
        "25 non-equal blocks",
        "zero observed usage necessary but insufficient",
        "candidate-specific selected exposure",
        "proves no behavioral value",
    ):
        _require(phrase in text, f"Adaptation review doc missing boundary: {phrase}")


def main() -> int:
    document = json.loads((ROOT / REVIEW_PATH).read_text(encoding="utf-8"))
    validate_review(document, root=ROOT)
    print("Deprecation/migration local adaptation review validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
