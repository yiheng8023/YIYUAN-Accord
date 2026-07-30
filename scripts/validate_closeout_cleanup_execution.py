#!/usr/bin/env python3
"""Validate exact repository-local temporary cleanup execution."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

try:
    from .inventory_closeout_cleanup_debt import ROOT_SPECS, canonical_sha256
except ImportError:
    from inventory_closeout_cleanup_debt import ROOT_SPECS, canonical_sha256


ROOT = Path(__file__).resolve().parent.parent
RECORD_PATH = "registry/closeout-cleanup-execution-2026-07-30.json"
PREVIEW_PATH = "registry/closeout-cleanup-debt-preview-2026-07-24.json"
DOC_PATH = "docs/closeout-cleanup-execution-2026-07-30.md"


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def _file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def validate_execution(document: dict[str, Any], *, root: Path = ROOT) -> None:
    body = dict(document)
    digest = body.pop("reportSha256", None)
    _require(
        digest == canonical_sha256(body),
        "Cleanup execution report digest drifted",
    )
    _require(
        {
            "schema": document.get("schema"),
            "id": document.get("id"),
            "date": document.get("date"),
            "status": document.get("status"),
            "scope": document.get("scope"),
        }
        == {
            "schema": 1,
            "id": "closeout-cleanup-execution-2026-07-30",
            "date": "2026-07-30",
            "status": "repository-local-temporary-debt-cleaned-stage-checkpoint",
            "scope": (
                "exact-repository-local-.tmp-and-audit-runtime-debris-cleanup"
            ),
        },
        "Cleanup execution identity drifted",
    )

    preview = json.loads((root / PREVIEW_PATH).read_text(encoding="utf-8"))
    preview_body = dict(preview)
    preview_digest = preview_body.pop("reportSha256")
    _require(
        preview_digest == canonical_sha256(preview_body),
        "Cleanup source preview digest drifted",
    )
    source = document.get("sourcePreview")
    _require(
        isinstance(source, dict)
        and source
        == {
            "path": PREVIEW_PATH,
            "reportSha256": preview_digest,
            "rootCount": preview["aggregate"]["rootCount"],
            "fileCount": preview["aggregate"]["fileCount"],
            "directoryCount": preview["aggregate"]["directoryCount"],
            "totalBytes": preview["aggregate"]["totalBytes"],
        },
        "Cleanup source preview binding drifted",
    )

    expected_targets = [str(spec["relativePath"]) for spec in ROOT_SPECS]
    execution = document.get("cleanupExecution")
    _require(
        isinstance(execution, dict)
        and execution.get("targetPaths") == expected_targets
        and execution.get("targetCount") == len(expected_targets)
        and execution.get("unexpectedPathsDeleted") == []
        and execution.get("sourceFilesDeleted") == 2459
        and execution.get("sourceDirectoriesDeleted") == 811
        and execution.get("sourceBytesDeleted") == 60346279
        and execution.get("temporaryRootRemoved") is True
        and execution.get("allExactTargetsAbsentAfterCleanup") is True
        and execution.get("cleanupExecuted") is True,
        "Cleanup execution target or aggregate drifted",
    )
    _require(
        not (root / ".tmp").exists()
        and all(not (root / path).exists() for path in expected_targets),
        "Repository-local temporary cleanup postcondition drifted",
    )
    screening = document.get("commitScreeningCleanup")
    expected_screening_targets = [
        (
            "audits/mcp-multi-connection-subscription-preflight-"
            "0.145.0-2026-07-27/resume-calibration-01/codex-home"
        ),
        (
            "audits/mcp-multi-connection-subscription-preflight-"
            "0.145.0-2026-07-27/resume-calibration-01/workspace"
        ),
        (
            "audits/mcp-multi-connection-subscription-preflight-"
            "0.145.0-2026-07-27/run-01/codex-home"
        ),
        (
            "audits/mcp-multi-connection-subscription-preflight-"
            "0.145.0-2026-07-27/run-01/workspace"
        ),
        (
            "audits/mcp-multi-connection-subscription-preflight-"
            "0.145.0-2026-07-27/run-02/codex-home"
        ),
        (
            "audits/mcp-multi-connection-subscription-preflight-"
            "0.145.0-2026-07-27/run-02/workspace"
        ),
        (
            "audits/mcp-multi-connection-subscription-preflight-"
            "0.145.0-2026-07-27/run-03/codex-home"
        ),
        (
            "audits/mcp-multi-connection-subscription-preflight-"
            "0.145.0-2026-07-27/run-03/workspace"
        ),
    ]
    expected_compact_paths = [
        (
            "audits/mcp-multi-connection-subscription-preflight-"
            "0.145.0-2026-07-27/README.md"
        ),
        (
            "audits/mcp-multi-connection-subscription-preflight-"
            "0.145.0-2026-07-27/resume-calibration-01.log"
        ),
        (
            "audits/mcp-multi-connection-subscription-preflight-"
            "0.145.0-2026-07-27/run-01/report.json"
        ),
        (
            "audits/mcp-multi-connection-subscription-preflight-"
            "0.145.0-2026-07-27/run-02/report.json"
        ),
        (
            "audits/mcp-multi-connection-subscription-preflight-"
            "0.145.0-2026-07-27/run-03/report.json"
        ),
    ]
    _require(
        isinstance(screening, dict)
        and screening.get("targetPaths") == expected_screening_targets
        and screening.get("targetCount") == 8
        and screening.get("sourceFilesDeleted") == 292
        and screening.get("sourceDirectoriesDeleted") == 124
        and screening.get("sourceBytesDeleted") == 9058784
        and screening.get("rawRuntimeStateDetected") is True
        and screening.get("unexpectedPathsDeleted") == []
        and screening.get("retainedCompactAuditPaths") == expected_compact_paths
        and screening.get("allExactTargetsAbsentAfterCleanup") is True
        and screening.get("cleanupExecuted") is True
        and all(not (root / path).exists() for path in expected_screening_targets)
        and all((root / path).is_file() for path in expected_compact_paths),
        "Commit-screening runtime debris cleanup drifted",
    )

    authority = document.get("authorityBoundary")
    _require(
        isinstance(authority, dict)
        and authority.get("exactRepositoryTemporaryProcessCleanupAuthorized")
        is True
        and authority.get("commitPushDiscretionAuthorized") is True
        and authority.get("externalWorkspaceMutationAuthorized") is False
        and authority.get("globalConfigurationMutationAuthorized") is False
        and authority.get("ccSwitchMutationAuthorized") is False,
        "Cleanup authority boundary drifted",
    )

    durable = document.get("durableEvidence")
    _require(
        isinstance(durable, dict)
        and durable.get("allPreviewEvidenceReferencesExist") is True
        and durable.get("rawRuntimeStateCommitted") is False,
        "Cleanup durable evidence boundary drifted",
    )
    for key in ("userSourceArchive", "creatorCloseNormalizedEvidence"):
        binding = durable.get(key)
        _require(isinstance(binding, dict), f"Cleanup durable binding missing: {key}")
        path = root / str(binding.get("path"))
        _require(
            path.is_file()
            and path.stat().st_size == binding.get("bytes")
            and _file_sha256(path) == binding.get("sha256"),
            f"Cleanup durable artifact drifted: {key}",
        )

    normalized = json.loads(
        (
            root
            / durable["creatorCloseNormalizedEvidence"]["path"]
        ).read_text(encoding="utf-8")
    )
    _require(
        normalized.get("sourceArtifacts", {}).get("rawArtifactsRetained")
        is False
        and len(normalized.get("sentinelEvents", [])) == 5
        and normalized.get("isolatedConfigSemantics", {}).get(
            "machineAbsolutePathsPreserved"
        )
        is False
        and normalized.get("isolatedConfigSemantics", {}).get(
            "secretMaterialPreserved"
        )
        is False,
        "Cleanup normalized evidence semantics drifted",
    )

    external = document.get("protectedExternalBoundary")
    _require(
        external
        == {
            "path": "C:/Projects/agent-skills-curated",
            "insideCleanupScope": False,
            "inspectedByCleanup": False,
            "modifiedByCleanup": False,
        },
        "Cleanup protected external boundary drifted",
    )
    claims = document.get("claimBoundary")
    _require(
        isinstance(claims, dict)
        and claims
        and all(value is False for value in claims.values()),
        "Cleanup claim boundary was promoted",
    )
    doc = " ".join((root / DOC_PATH).read_text(encoding="utf-8").split())
    for phrase in (
        "stage checkpoint, not program closeout",
        "thirty-five exact `.tmp` targets",
        "2,459 files",
        "60,346,279 bytes",
        "repository-local `.tmp` root is absent",
        "No unexpected path was included",
        "excludes raw runtime state",
        "eight additional process-only directories",
        "9,058,784 bytes",
    ):
        _require(phrase in doc, f"Cleanup execution documentation missing: {phrase}")


def main() -> int:
    document = json.loads((ROOT / RECORD_PATH).read_text(encoding="utf-8"))
    validate_execution(document)
    print("Closeout cleanup execution validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
