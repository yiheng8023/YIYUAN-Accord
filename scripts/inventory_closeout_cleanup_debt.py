#!/usr/bin/env python3
"""Inventory exact retained cleanup-debt roots without deleting or reading content."""

from __future__ import annotations

import hashlib
import json
import os
import re
import stat
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parent.parent
SENSITIVE_NAME = re.compile(
    r"(auth|token|credential|secret|session)",
    re.IGNORECASE,
)
ROOT_SPECS = (
    {
        "id": "mcp-child-exit-run01",
        "relativePath": ".tmp/mcp-child-exit-recovery-20260723-run01",
        "evidenceRole": "child-exit-recovery-raw-evidence",
        "evidenceRefs": [
            "docs/mcp-app-server-0.145.0-child-exit-recovery-evidence-2026-07-23.md",
            "registry/mcp-app-server-0.145.0-child-exit-recovery-evidence-2026-07-23.json",
        ],
    },
    {
        "id": "mcp-child-exit-run02",
        "relativePath": ".tmp/mcp-child-exit-recovery-20260723-run02",
        "evidenceRole": "child-exit-recovery-raw-evidence",
        "evidenceRefs": [
            "docs/mcp-app-server-0.145.0-child-exit-recovery-evidence-2026-07-23.md",
            "registry/mcp-app-server-0.145.0-child-exit-recovery-evidence-2026-07-23.json",
        ],
    },
    {
        "id": "mcp-idle-observation",
        "relativePath": ".tmp/mcp-idle-observation-20260723",
        "evidenceRole": "thirty-minute-idle-observation-raw-evidence",
        "evidenceRefs": [
            "docs/mcp-app-server-0.145.0-idle-unload-evidence-2026-07-23.md",
            "registry/mcp-app-server-0.145.0-idle-unload-evidence-2026-07-23.json",
        ],
    },
    {
        "id": "mcp-idle-short-preflight-a",
        "relativePath": ".tmp/mcp-idle-preflight-20260723",
        "evidenceRole": "negative-short-idle-preflight-raw-evidence",
        "evidenceRefs": [
            "docs/mcp-app-server-0.145.0-idle-unload-evidence-2026-07-23.md",
            "registry/mcp-app-server-0.145.0-idle-unload-evidence-2026-07-23.json",
        ],
    },
    {
        "id": "mcp-idle-short-preflight-b",
        "relativePath": ".tmp/mcp-idle-preflight-20260723-b",
        "evidenceRole": "negative-short-idle-preflight-raw-evidence",
        "evidenceRefs": [
            "docs/mcp-app-server-0.145.0-idle-unload-evidence-2026-07-23.md",
            "registry/mcp-app-server-0.145.0-idle-unload-evidence-2026-07-23.json",
        ],
    },
    {
        "id": "mcp-startup-profiles-run01",
        "relativePath": ".tmp/mcp-startup-profiles-20260723-run01",
        "evidenceRole": "startup-profile-comparison-raw-evidence",
        "evidenceRefs": [
            "docs/mcp-app-server-0.145.0-startup-profile-evidence-2026-07-23.md",
            "registry/mcp-app-server-0.145.0-startup-profile-evidence-2026-07-23.json",
        ],
    },
    {
        "id": "user-supplied-hmc-source-archive",
        "relativePath": ".tmp/source-archives",
        "evidenceRole": "user-supplied-research-source-local-preservation-copy",
        "evidenceRefs": [
            "docs/strategy/USER-SUPPLIED-HUMAN-AI-SDLC-RESEARCH-INTAKE-2026-07-24.md",
            "registry/user-supplied-human-ai-sdlc-research-intake-2026-07-24.json",
        ],
    },
    {
        "id": "tdd-app-server-schema",
        "relativePath": ".tmp/codex-app-server-schema-0145-tdd-20260726",
        "evidenceRole": "tdd-app-server-schema-and-runner-preflight-evidence",
        "evidenceRefs": [
            "docs/strategy/HUMAN-AI-COLLABORATION-NEW-FEATURE-TDD-PROTOCOL-2026-07-26.md",
            "registry/human-ai-collaboration-new-feature-tdd-protocol-2026-07-26.json",
        ],
    },
    {
        "id": "tdd-raw-item-pilot-r1",
        "relativePath": ".tmp/tdd-raw-item-pilot-20260726-r1",
        "evidenceRole": "tdd-raw-item-pilot-evidence",
        "evidenceRefs": [
            "docs/strategy/HUMAN-AI-COLLABORATION-TDD-RAW-ITEM-PILOT-EVIDENCE-2026-07-26.md",
            "registry/human-ai-collaboration-tdd-raw-item-pilot-evidence-2026-07-26.json",
        ],
    },
    {
        "id": "tdd-raw-item-pilot-r2",
        "relativePath": ".tmp/tdd-raw-item-pilot-20260726-r2",
        "evidenceRole": "tdd-raw-item-pilot-evidence",
        "evidenceRefs": [
            "docs/strategy/HUMAN-AI-COLLABORATION-TDD-RAW-ITEM-PILOT-EVIDENCE-2026-07-26.md",
            "registry/human-ai-collaboration-tdd-raw-item-pilot-evidence-2026-07-26.json",
        ],
    },
    {
        "id": "tdd-formal-native-r1",
        "relativePath": ".tmp/tdd-formal-native-20260726-r1",
        "evidenceRole": "tdd-native-formal-attempt-evidence",
        "evidenceRefs": [
            "docs/strategy/HUMAN-AI-COLLABORATION-TDD-FORMAL-RUNNER-FIRST-ATTEMPT-EVIDENCE-2026-07-26.md",
            "registry/human-ai-collaboration-tdd-formal-runner-first-attempt-evidence-2026-07-26.json",
            "docs/strategy/HUMAN-AI-COLLABORATION-TDD-NATIVE-FORMAL-ATTEMPT-BATCH-2026-07-26.md",
            "registry/human-ai-collaboration-tdd-native-formal-attempt-batch-2026-07-26.json",
        ],
    },
    {
        "id": "tdd-formal-native-r2",
        "relativePath": ".tmp/tdd-formal-native-20260726-r2",
        "evidenceRole": "tdd-native-formal-attempt-evidence",
        "evidenceRefs": [
            "docs/strategy/HUMAN-AI-COLLABORATION-TDD-NATIVE-FORMAL-ATTEMPT-BATCH-2026-07-26.md",
            "registry/human-ai-collaboration-tdd-native-formal-attempt-batch-2026-07-26.json",
        ],
    },
    {
        "id": "tdd-formal-native-r3",
        "relativePath": ".tmp/tdd-formal-native-20260726-r3",
        "evidenceRole": "tdd-native-formal-attempt-evidence",
        "evidenceRefs": [
            "docs/strategy/HUMAN-AI-COLLABORATION-TDD-NATIVE-FORMAL-ATTEMPT-BATCH-2026-07-26.md",
            "registry/human-ai-collaboration-tdd-native-formal-attempt-batch-2026-07-26.json",
        ],
    },
    {
        "id": "process-fidelity-app-server-schema",
        "relativePath": ".tmp/app-server-schema-0.145.0",
        "evidenceRole": "dynamic-tool-schema-supporting-evidence",
        "evidenceRefs": [
            "docs/strategy/HUMAN-AI-COLLABORATION-PROCESS-FIDELITY-INFORMATION-EQUIVALENT-TRIAL-PROTOCOL-V2-2026-07-27.md",
            "registry/human-ai-collaboration-process-fidelity-information-equivalent-trial-protocol-v2-2026-07-27.json",
        ],
    },
    {
        "id": "process-fidelity-v1-calibration",
        "relativePath": ".tmp/process-fidelity-live-20260727",
        "evidenceRole": "measurement-ambiguous-v1-calibration-raw-evidence",
        "evidenceRefs": [
            "docs/strategy/HUMAN-AI-COLLABORATION-PROCESS-FIDELITY-V1-CALIBRATION-ABORT-2026-07-27.md",
            "registry/human-ai-collaboration-process-fidelity-v1-calibration-abort-2026-07-27.json",
        ],
    },
    {
        "id": "process-fidelity-v2-zero-dispatch",
        "relativePath": ".tmp/process-fidelity-v2-zero-dispatch-20260727",
        "evidenceRole": "v2-source-backed-zero-dispatch-preflight-evidence",
        "evidenceRefs": [
            "docs/strategy/HUMAN-AI-COLLABORATION-PROCESS-FIDELITY-INFORMATION-EQUIVALENT-TRIAL-PROTOCOL-V2-2026-07-27.md",
            "registry/human-ai-collaboration-process-fidelity-information-equivalent-trial-protocol-v2-2026-07-27.json",
        ],
    },
    {
        "id": "process-fidelity-v2-zero-dispatch-report",
        "relativePath": ".tmp/process-fidelity-v2-zero-dispatch-20260727-report.json",
        "evidenceRole": "v2-source-backed-zero-dispatch-preflight-summary",
        "evidenceRefs": [
            "docs/strategy/HUMAN-AI-COLLABORATION-PROCESS-FIDELITY-INFORMATION-EQUIVALENT-TRIAL-PROTOCOL-V2-2026-07-27.md",
            "registry/human-ai-collaboration-process-fidelity-information-equivalent-trial-protocol-v2-2026-07-27.json",
        ],
    },
    {
        "id": "process-fidelity-v2-live-smoke-01",
        "relativePath": ".tmp/process-fidelity-v2-live-20260727-r1-source-backed",
        "evidenceRole": "measurement-invalid-v2-source-backed-smoke-raw-evidence",
        "evidenceRefs": [
            "docs/strategy/HUMAN-AI-COLLABORATION-PROCESS-FIDELITY-INFORMATION-EQUIVALENT-TRIAL-PROTOCOL-V2-2026-07-27.md",
            "registry/human-ai-collaboration-process-fidelity-information-equivalent-trial-protocol-v2-2026-07-27.json",
        ],
    },
    {
        "id": "process-fidelity-v2-live-smoke-01-report",
        "relativePath": ".tmp/process-fidelity-v2-live-20260727-r1-source-backed-report.json",
        "evidenceRole": "measurement-invalid-v2-source-backed-smoke-summary",
        "evidenceRefs": [
            "docs/strategy/HUMAN-AI-COLLABORATION-PROCESS-FIDELITY-INFORMATION-EQUIVALENT-TRIAL-PROTOCOL-V2-2026-07-27.md",
            "registry/human-ai-collaboration-process-fidelity-information-equivalent-trial-protocol-v2-2026-07-27.json",
        ],
    },
    {
        "id": "process-fidelity-v2-zero-dispatch-corrected",
        "relativePath": ".tmp/process-fidelity-v2-zero-dispatch-corrected-20260727",
        "evidenceRole": "corrected-v2-source-backed-zero-dispatch-preflight-evidence",
        "evidenceRefs": [
            "docs/strategy/HUMAN-AI-COLLABORATION-PROCESS-FIDELITY-INFORMATION-EQUIVALENT-TRIAL-PROTOCOL-V2-2026-07-27.md",
            "registry/human-ai-collaboration-process-fidelity-information-equivalent-trial-protocol-v2-2026-07-27.json",
        ],
    },
    {
        "id": "process-fidelity-v2-zero-dispatch-corrected-report",
        "relativePath": ".tmp/process-fidelity-v2-zero-dispatch-corrected-20260727-report.json",
        "evidenceRole": "corrected-v2-source-backed-zero-dispatch-preflight-summary",
        "evidenceRefs": [
            "docs/strategy/HUMAN-AI-COLLABORATION-PROCESS-FIDELITY-INFORMATION-EQUIVALENT-TRIAL-PROTOCOL-V2-2026-07-27.md",
            "registry/human-ai-collaboration-process-fidelity-information-equivalent-trial-protocol-v2-2026-07-27.json",
        ],
    },
    {
        "id": "process-fidelity-v2-live-smoke-02",
        "relativePath": ".tmp/process-fidelity-v2-live-20260727-r2-source-backed",
        "evidenceRole": "valid-v2-source-backed-smoke-raw-evidence",
        "evidenceRefs": [
            "docs/strategy/HUMAN-AI-COLLABORATION-PROCESS-FIDELITY-V2-SOURCE-BACKED-SMOKE-EVIDENCE-2026-07-27.md",
            "registry/human-ai-collaboration-process-fidelity-v2-source-backed-smoke-evidence-2026-07-27.json",
        ],
    },
    {
        "id": "process-fidelity-v2-live-smoke-02-report",
        "relativePath": ".tmp/process-fidelity-v2-live-20260727-r2-source-backed-report.json",
        "evidenceRole": "valid-v2-source-backed-smoke-summary",
        "evidenceRefs": [
            "docs/strategy/HUMAN-AI-COLLABORATION-PROCESS-FIDELITY-V2-SOURCE-BACKED-SMOKE-EVIDENCE-2026-07-27.md",
            "registry/human-ai-collaboration-process-fidelity-v2-source-backed-smoke-evidence-2026-07-27.json",
        ],
    },
    {
        "id": "mcp-thread-unsubscribe-calibration-01",
        "relativePath": (
            ".tmp/mcp-unsubscribe-attribution-calibration-20260727-01"
        ),
        "evidenceRole": (
            "excluded-thread-unsubscribe-paired-calibration-host-state"
        ),
        "evidenceRefs": [
            "docs/mcp-app-server-0.145.0-thread-unsubscribe-release-attribution-evidence-2026-07-27.md",
            "registry/mcp-app-server-0.145.0-thread-unsubscribe-release-attribution-evidence-2026-07-27.json",
        ],
    },
    {
        "id": "mcp-thread-unsubscribe-formal-01",
        "relativePath": ".tmp/mcp-unsubscribe-attribution-formal-20260727-01",
        "evidenceRole": "thread-unsubscribe-paired-formal-host-state",
        "evidenceRefs": [
            "docs/mcp-app-server-0.145.0-thread-unsubscribe-release-attribution-evidence-2026-07-27.md",
            "registry/mcp-app-server-0.145.0-thread-unsubscribe-release-attribution-evidence-2026-07-27.json",
        ],
    },
    {
        "id": "mcp-thread-unsubscribe-formal-02",
        "relativePath": ".tmp/mcp-unsubscribe-attribution-formal-20260727-02",
        "evidenceRole": "thread-unsubscribe-paired-formal-host-state",
        "evidenceRefs": [
            "docs/mcp-app-server-0.145.0-thread-unsubscribe-release-attribution-evidence-2026-07-27.md",
            "registry/mcp-app-server-0.145.0-thread-unsubscribe-release-attribution-evidence-2026-07-27.json",
        ],
    },
    {
        "id": "mcp-thread-unsubscribe-formal-03",
        "relativePath": ".tmp/mcp-unsubscribe-attribution-formal-20260727-03",
        "evidenceRole": "thread-unsubscribe-paired-formal-host-state",
        "evidenceRefs": [
            "docs/mcp-app-server-0.145.0-thread-unsubscribe-release-attribution-evidence-2026-07-27.md",
            "registry/mcp-app-server-0.145.0-thread-unsubscribe-release-attribution-evidence-2026-07-27.json",
        ],
    },
    {
        "id": "mcp-multi-connection-preflight-attempt-01",
        "relativePath": (
            ".tmp/mcp-multi-connection-subscription-preflight-"
            "2026-07-27-attempt-01"
        ),
        "evidenceRole": (
            "excluded-multi-connection-preflight-calibration-host-state"
        ),
        "evidenceRefs": [
            "docs/mcp-app-server-0.145.0-multi-connection-subscription-preflight-evidence-2026-07-27.md",
            "registry/mcp-app-server-0.145.0-multi-connection-subscription-preflight-evidence-2026-07-27.json",
        ],
    },
    {
        "id": "mcp-multi-connection-preflight-attempt-02",
        "relativePath": (
            ".tmp/mcp-multi-connection-subscription-preflight-"
            "2026-07-27-attempt-02"
        ),
        "evidenceRole": (
            "excluded-multi-connection-preflight-calibration-host-state"
        ),
        "evidenceRefs": [
            "docs/mcp-app-server-0.145.0-multi-connection-subscription-preflight-evidence-2026-07-27.md",
            "registry/mcp-app-server-0.145.0-multi-connection-subscription-preflight-evidence-2026-07-27.json",
        ],
    },
    {
        "id": "mcp-multi-connection-preflight-attempt-03",
        "relativePath": (
            ".tmp/mcp-multi-connection-subscription-preflight-"
            "2026-07-27-attempt-03"
        ),
        "evidenceRole": (
            "excluded-multi-connection-preflight-calibration-host-state"
        ),
        "evidenceRefs": [
            "docs/mcp-app-server-0.145.0-multi-connection-subscription-preflight-evidence-2026-07-27.md",
            "registry/mcp-app-server-0.145.0-multi-connection-subscription-preflight-evidence-2026-07-27.json",
        ],
    },
    {
        "id": "mcp-multi-connection-preflight-attempt-04",
        "relativePath": (
            ".tmp/mcp-multi-connection-subscription-preflight-"
            "2026-07-27-attempt-04"
        ),
        "evidenceRole": (
            "excluded-multi-connection-preflight-calibration-host-state"
        ),
        "evidenceRefs": [
            "docs/mcp-app-server-0.145.0-multi-connection-subscription-preflight-evidence-2026-07-27.md",
            "registry/mcp-app-server-0.145.0-multi-connection-subscription-preflight-evidence-2026-07-27.json",
        ],
    },
    {
        "id": "mcp-multi-connection-preflight-attempt-05",
        "relativePath": (
            ".tmp/mcp-multi-connection-subscription-preflight-"
            "2026-07-27-attempt-05"
        ),
        "evidenceRole": (
            "excluded-multi-connection-preflight-calibration-host-state"
        ),
        "evidenceRefs": [
            "docs/mcp-app-server-0.145.0-multi-connection-subscription-preflight-evidence-2026-07-27.md",
            "registry/mcp-app-server-0.145.0-multi-connection-subscription-preflight-evidence-2026-07-27.json",
        ],
    },
    {
        "id": "mcp-creator-close-calibration-01",
        "relativePath": ".tmp/mcp-creator-close-calibration-20260727-01",
        "evidenceRole": (
            "invalid-pre-window-creator-connection-close-calibration-host-state"
        ),
        "evidenceRefs": [
            "docs/mcp-thread-creator-connection-close-calibration-attempt-2026-07-27.md",
            "registry/mcp-thread-creator-connection-close-calibration-attempt-2026-07-27.json",
        ],
    },
    {
        "id": "mcp-creator-close-calibration-workspace-01",
        "relativePath": (
            ".tmp/mcp-creator-close-calibration-workspace-20260727-01"
        ),
        "evidenceRole": (
            "invalid-pre-window-creator-connection-close-calibration-empty-workspace"
        ),
        "evidenceRefs": [
            "docs/mcp-thread-creator-connection-close-calibration-attempt-2026-07-27.md",
            "registry/mcp-thread-creator-connection-close-calibration-attempt-2026-07-27.json",
        ],
    },
    {
        "id": "full-suite-failed-verification-log-20260727",
        "relativePath": ".tmp/inflight-full-suite-20260727",
        "evidenceRole": (
            "failed-full-suite-verification-process-log-after-inventory-drift"
        ),
        "evidenceRefs": [
            "docs/closeout-cleanup-debt-preview-2026-07-24.md",
            "registry/closeout-cleanup-debt-preview-2026-07-24.json",
        ],
    },
)

RETENTION_CLASS_BY_ID = {
    **{
        item_id: "retain-authoritative-evidence"
        for item_id in (
            "mcp-child-exit-run01",
            "mcp-child-exit-run02",
            "mcp-idle-observation",
            "mcp-idle-short-preflight-a",
            "mcp-idle-short-preflight-b",
            "mcp-startup-profiles-run01",
            "tdd-raw-item-pilot-r1",
            "tdd-raw-item-pilot-r2",
            "tdd-formal-native-r1",
            "tdd-formal-native-r2",
            "tdd-formal-native-r3",
            "process-fidelity-v2-live-smoke-02",
            "process-fidelity-v2-live-smoke-02-report",
            "mcp-thread-unsubscribe-formal-01",
            "mcp-thread-unsubscribe-formal-02",
            "mcp-thread-unsubscribe-formal-03",
        )
    },
    **{
        item_id: "retain-invalid-or-excluded-attempt-evidence"
        for item_id in (
            "process-fidelity-v1-calibration",
            "process-fidelity-v2-live-smoke-01",
            "process-fidelity-v2-live-smoke-01-report",
            "mcp-thread-unsubscribe-calibration-01",
            "mcp-multi-connection-preflight-attempt-01",
            "mcp-multi-connection-preflight-attempt-02",
            "mcp-multi-connection-preflight-attempt-03",
            "mcp-multi-connection-preflight-attempt-04",
            "mcp-multi-connection-preflight-attempt-05",
            "mcp-creator-close-calibration-01",
            "mcp-creator-close-calibration-workspace-01",
        )
    },
    **{
        item_id: "retain-process-artifact-authority-unresolved"
        for item_id in (
            "tdd-app-server-schema",
            "process-fidelity-app-server-schema",
            "process-fidelity-v2-zero-dispatch",
            "process-fidelity-v2-zero-dispatch-report",
            "process-fidelity-v2-zero-dispatch-corrected",
            "process-fidelity-v2-zero-dispatch-corrected-report",
            "full-suite-failed-verification-log-20260727",
        )
    },
    "user-supplied-hmc-source-archive": "retain-user-source-preservation",
}

PROTECTED_EXTERNAL_BOUNDARY = {
    "id": "legacy-agent-skills-curated-workspace",
    "path": "C:/Projects/agent-skills-curated",
    "scope": "external-workspace-outside-repository-local-tmp-inventory",
    "contentScanned": False,
    "aggregateIncluded": False,
    "archiveAuthorized": False,
    "moveAuthorized": False,
    "deletionAuthorized": False,
    "recommendedDisposition": (
        "retain-through-stability-observation-until-separately-authorized"
    ),
}


def canonical_sha256(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()


def _is_reparse(path: Path) -> bool:
    metadata = path.lstat()
    return path.is_symlink() or bool(
        getattr(metadata, "st_file_attributes", 0)
        & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)
    )


def _tree_stats(path: Path) -> dict[str, int | bool]:
    file_count = 0
    directory_count = 0
    total_bytes = 0
    sqlite_count = 0
    jsonl_count = 0
    potential_sensitive_name_count = 0
    reparse_point_count = 0

    if _is_reparse(path):
        return {
            "fileCount": 0,
            "directoryCount": 0,
            "totalBytes": 0,
            "sqliteFileCount": 0,
            "jsonlFileCount": 0,
            "potentialSensitiveFilenameCount": 0,
            "reparsePointCount": 1,
            "containsPotentialRuntimeState": False,
        }

    if path.is_file():
        metadata = path.stat()
        suffix = path.suffix.lower()
        sqlite_count = int(
            suffix in {".sqlite", ".db"}
            or ".sqlite-" in path.name.lower()
        )
        return {
            "fileCount": 1,
            "directoryCount": 0,
            "totalBytes": metadata.st_size,
            "sqliteFileCount": sqlite_count,
            "jsonlFileCount": int(suffix == ".jsonl"),
            "potentialSensitiveFilenameCount": int(
                bool(SENSITIVE_NAME.search(path.name))
            ),
            "reparsePointCount": 0,
            "containsPotentialRuntimeState": sqlite_count > 0,
        }

    for current, directories, files in os.walk(path, followlinks=False):
        current_path = Path(current)
        retained_directories: list[str] = []
        for name in directories:
            candidate = current_path / name
            if _is_reparse(candidate):
                reparse_point_count += 1
            else:
                directory_count += 1
                retained_directories.append(name)
        directories[:] = retained_directories
        for name in files:
            candidate = current_path / name
            if _is_reparse(candidate):
                reparse_point_count += 1
                continue
            metadata = candidate.stat()
            file_count += 1
            total_bytes += metadata.st_size
            suffix = candidate.suffix.lower()
            if suffix in {".sqlite", ".db"} or ".sqlite-" in candidate.name.lower():
                sqlite_count += 1
            if suffix == ".jsonl":
                jsonl_count += 1
            if SENSITIVE_NAME.search(candidate.name):
                potential_sensitive_name_count += 1
    return {
        "fileCount": file_count,
        "directoryCount": directory_count,
        "totalBytes": total_bytes,
        "sqliteFileCount": sqlite_count,
        "jsonlFileCount": jsonl_count,
        "potentialSensitiveFilenameCount": potential_sensitive_name_count,
        "reparsePointCount": reparse_point_count,
        "containsPotentialRuntimeState": sqlite_count > 0,
    }


def build_cleanup_debt_preview(
    workspace: Path = ROOT,
    *,
    root_specs: Iterable[dict[str, Any]] = ROOT_SPECS,
) -> dict[str, Any]:
    specs = tuple(root_specs)
    spec_ids = {str(spec["id"]) for spec in specs}
    if specs == ROOT_SPECS and spec_ids != set(RETENTION_CLASS_BY_ID):
        raise RuntimeError("cleanup retention-class partition drifted")
    expected_names = {
        Path(spec["relativePath"]).name
        for spec in specs
    }
    temporary_root = workspace / ".tmp"
    actual_names = (
        {path.name for path in temporary_root.iterdir()}
        if temporary_root.is_dir()
        else set()
    )
    entries: list[dict[str, Any]] = []
    for spec in specs:
        relative_path = spec["relativePath"]
        path = workspace / relative_path
        evidence_refs = list(spec["evidenceRefs"])
        evidence_exists = [
            (workspace / reference).is_file()
            for reference in evidence_refs
        ]
        basename = Path(relative_path).name
        direct_refs = [
            reference
            for reference, exists in zip(evidence_refs, evidence_exists)
            if exists
            and basename in (workspace / reference).read_text(
                encoding="utf-8",
                errors="replace",
            )
        ]
        exists = path.exists()
        stats = _tree_stats(path) if exists else {
            "fileCount": 0,
            "directoryCount": 0,
            "totalBytes": 0,
            "sqliteFileCount": 0,
            "jsonlFileCount": 0,
            "potentialSensitiveFilenameCount": 0,
            "reparsePointCount": 0,
            "containsPotentialRuntimeState": False,
        }
        entries.append(
            {
                "id": spec["id"],
                "relativePath": relative_path,
                "exists": exists,
                "evidenceRole": spec["evidenceRole"],
                "retentionClass": RETENTION_CLASS_BY_ID.get(
                    str(spec["id"]),
                    "retain-process-artifact-authority-unresolved",
                ),
                "evidenceRefs": evidence_refs,
                "allEvidenceRefsExist": all(evidence_exists),
                "evidenceBinding": (
                    "direct-path"
                    if direct_refs
                    else "evidence-class-only"
                ),
                "directReferenceRefs": direct_refs,
                **stats,
                "contentInspected": False,
                "contentInspectionAuthorized": False,
                "productPayload": False,
                "deletionAuthorized": False,
                "safeToDeleteProved": False,
                "recoverabilityProved": False,
                "recommendedDisposition": (
                    "retain-as-cleanup-debt-pending-explicit-"
                    "exact-target-deletion-authority"
                ),
            }
        )

    unexpected = sorted(actual_names - expected_names)
    missing = sorted(
        entry["relativePath"]
        for entry in entries
        if entry["exists"] is not True
    )
    aggregate = {
        "rootCount": len(entries),
        "fileCount": sum(entry["fileCount"] for entry in entries),
        "directoryCount": sum(
            entry["directoryCount"] for entry in entries
        ),
        "totalBytes": sum(entry["totalBytes"] for entry in entries),
        "directPathBindingCount": sum(
            entry["evidenceBinding"] == "direct-path"
            for entry in entries
        ),
        "evidenceClassOnlyBindingCount": sum(
            entry["evidenceBinding"] == "evidence-class-only"
            for entry in entries
        ),
        "potentialRuntimeStateRootCount": sum(
            entry["containsPotentialRuntimeState"] is True
            for entry in entries
        ),
        "reparsePointCount": sum(
            entry["reparsePointCount"] for entry in entries
        ),
        "retentionClassSummary": {
            retention_class: {
                "rootCount": sum(
                    entry["retentionClass"] == retention_class
                    for entry in entries
                ),
                "fileCount": sum(
                    entry["fileCount"]
                    for entry in entries
                    if entry["retentionClass"] == retention_class
                ),
                "directoryCount": sum(
                    entry["directoryCount"]
                    for entry in entries
                    if entry["retentionClass"] == retention_class
                ),
                "totalBytes": sum(
                    entry["totalBytes"]
                    for entry in entries
                    if entry["retentionClass"] == retention_class
                ),
            }
            for retention_class in sorted(
                set(RETENTION_CLASS_BY_ID.values())
                if specs == ROOT_SPECS
                else {
                    entry["retentionClass"] for entry in entries
                }
            )
        },
    }
    review_required = bool(
        unexpected
        or missing
        or aggregate["reparsePointCount"]
        or any(
            entry["allEvidenceRefsExist"] is not True
            for entry in entries
        )
    )
    report = {
        "schema": 1,
        "id": "closeout-cleanup-debt-preview-2026-07-24",
        "date": "2026-07-24",
        "lastObservedDate": "2026-07-27",
        "status": (
            "inventory-needs-review"
            if review_required
            else "inventory-current-retain-no-delete-authority"
        ),
        "workspace": workspace.resolve().as_posix(),
        "scope": "repository-local-.tmp-top-level-roots-only",
        "entries": entries,
        "aggregate": aggregate,
        "unexpectedTopLevelEntries": unexpected,
        "missingExpectedRoots": missing,
        "protectedExternalBoundary": {
            **PROTECTED_EXTERNAL_BOUNDARY,
            "exists": Path(
                str(PROTECTED_EXTERNAL_BOUNDARY["path"])
            ).is_dir(),
        },
        "authorityBoundary": {
            "contentInspectionAuthorized": False,
            "deletionAuthorized": False,
            "migrationAuthorized": False,
            "archiveAuthorized": False,
            "commitOrPushAuthorized": False,
        },
        "claimBoundary": {
            "allTemporaryArtifactsInventoried": False,
            "safeDeletionProved": False,
            "normalizedEvidenceSufficientForDeletionProved": False,
            "sensitiveDataAbsentProved": False,
            "cleanupExecuted": False,
            "programCloseoutProved": False,
        },
        "nextGate": (
            "At final closeout, re-run the inventory, review every exact root "
            "and its normalized evidence, bind recoverability and sensitive-"
            "data handling, obtain explicit exact-target deletion authority, "
            "then verify post-delete absence without broad recursive cleanup."
        ),
    }
    report["reportSha256"] = canonical_sha256(report)
    return report


def validate_cleanup_debt_preview(report: dict[str, Any]) -> list[str]:
    failures: list[str] = []
    if not isinstance(report, dict):
        return ["fail-report-shape"]
    body = dict(report)
    digest = body.pop("reportSha256", None)
    if digest != canonical_sha256(body):
        failures.append("fail-report-digest")
    if report.get("scope") != "repository-local-.tmp-top-level-roots-only":
        failures.append("fail-scope-boundary")
    if (
        report.get("schema") != 1
        or report.get("id") != "closeout-cleanup-debt-preview-2026-07-24"
        or report.get("date") != "2026-07-24"
        or report.get("status")
        not in {
            "inventory-current-retain-no-delete-authority",
            "inventory-needs-review",
        }
    ):
        failures.append("fail-report-identity")
    if report.get("lastObservedDate") != "2026-07-27":
        failures.append("fail-observation-date")
    external = report.get("protectedExternalBoundary")
    if (
        not isinstance(external, dict)
        or external.get("id") != "legacy-agent-skills-curated-workspace"
        or external.get("path") != "C:/Projects/agent-skills-curated"
        or external.get("contentScanned") is not False
        or external.get("aggregateIncluded") is not False
        or external.get("archiveAuthorized") is not False
        or external.get("moveAuthorized") is not False
        or external.get("deletionAuthorized") is not False
    ):
        failures.append("hard-fail-external-retention-boundary")
    authority = report.get("authorityBoundary")
    claim = report.get("claimBoundary")
    if (
        not isinstance(authority, dict)
        or not authority
        or any(value is not False for value in authority.values())
    ):
        failures.append("hard-fail-authority-promotion")
    if (
        not isinstance(claim, dict)
        or not claim
        or any(value is not False for value in claim.values())
    ):
        failures.append("hard-fail-claim-promotion")
    entries = report.get("entries")
    if not isinstance(entries, list) or not entries:
        failures.append("fail-entry-shape")
    else:
        for entry in entries:
            if (
                not isinstance(entry, dict)
                or entry.get("contentInspected") is not False
                or entry.get("contentInspectionAuthorized") is not False
                or entry.get("deletionAuthorized") is not False
                or entry.get("safeToDeleteProved") is not False
                or entry.get("recoverabilityProved") is not False
                or entry.get("productPayload") is not False
                or entry.get("retentionClass")
                not in set(RETENTION_CLASS_BY_ID.values())
            ):
                failures.append("hard-fail-entry-promotion")
                break
        aggregate = report.get("aggregate")
        if not isinstance(aggregate, dict):
            failures.append("fail-aggregate-shape")
        else:
            expected_summary = {
                retention_class: {
                    "rootCount": sum(
                        entry.get("retentionClass") == retention_class
                        for entry in entries
                    ),
                    "fileCount": sum(
                        entry.get("fileCount", 0)
                        for entry in entries
                        if entry.get("retentionClass") == retention_class
                    ),
                    "directoryCount": sum(
                        entry.get("directoryCount", 0)
                        for entry in entries
                        if entry.get("retentionClass") == retention_class
                    ),
                    "totalBytes": sum(
                        entry.get("totalBytes", 0)
                        for entry in entries
                        if entry.get("retentionClass") == retention_class
                    ),
                }
                for retention_class in sorted(
                    {
                        entry.get("retentionClass")
                        for entry in entries
                        if isinstance(entry, dict)
                        and isinstance(entry.get("retentionClass"), str)
                    }
                )
            }
            if aggregate.get("retentionClassSummary") != expected_summary:
                failures.append("fail-retention-class-summary")
            expected_aggregate = {
                "rootCount": len(entries),
                "fileCount": sum(
                    entry.get("fileCount", 0) for entry in entries
                ),
                "directoryCount": sum(
                    entry.get("directoryCount", 0) for entry in entries
                ),
                "totalBytes": sum(
                    entry.get("totalBytes", 0) for entry in entries
                ),
            }
            if any(
                aggregate.get(key) != value
                for key, value in expected_aggregate.items()
            ):
                failures.append("fail-aggregate-reconciliation")
    return list(dict.fromkeys(failures))


def main() -> int:
    report = build_cleanup_debt_preview()
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if not validate_cleanup_debt_preview(report) else 1


if __name__ == "__main__":
    raise SystemExit(main())
