#!/usr/bin/env python3
"""Validate the dated read-only Codex consumer Skill mapping snapshot."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
RECORD_PATH = Path("registry/codex-consumer-skill-mapping-snapshot-2026-08-07.json")
ACCEPTANCE_PATH = Path("registry/program-acceptance-map.json")
AUTHORITY_PATH = Path("registry/skill-portfolio-current-authority.json")
PREDECESSOR_PATH = Path(
    "registry/consumer-mapping-evidence-gap-reconciliation-2026-07-18.json"
)
EVIDENCE_ID = "evidence.codex-consumer-skill-mapping-snapshot-2026-08-07"
SUPPORTED_ACCEPTANCE_IDS = (
    "acceptance.consumer-mapping-evidence",
    "acceptance.cc-switch-source-preserving-skill-pool",
    "acceptance.foreign-managed-capability-coexistence",
)
SOURCE_BACKED_SYMLINKS = (
    "ask-matt",
    "code-review",
    "codebase-design",
    "diagnosing-bugs",
    "domain-modeling",
    "grill-me",
    "grill-with-docs",
    "grilling",
    "handoff",
    "implement",
    "improve-codebase-architecture",
    "prototype",
    "research",
    "resolving-merge-conflicts",
    "setup-matt-pocock-skills",
    "tdd",
    "teach",
    "to-questionnaire",
    "to-spec",
    "to-tickets",
    "triage",
    "wait-what",
    "wayfinder",
    "writing-for-agents",
)
LOCAL_SYMLINKS = (
    "caveman",
    "design-an-interface",
    "disciplined-coding",
    "doc",
    "edit-article",
    "obsidian-vault",
    "pdf",
    "playwright",
    "qa",
    "request-refactor-plan",
    "security-ownership-map",
    "setup-pre-commit",
    "writing-beats",
    "writing-fragments",
    "writing-shape",
    "zoom-out",
)
LOCAL_MATERIALIZED = (
    "capability-router",
    "closure-contract",
    "intent-contract",
    "kimi-webbridge",
)
EXPECTED_MATERIALIZED_OWNERSHIP = {
    "consumerRepositoryExactTreeNames": [
        "capability-router",
        "closure-contract",
        "intent-contract",
    ],
    "consumerRepositoryHead": "fff0041bf074996b63a4f178741ccbc1bf0d6657",
    "consumerRepositoryDirtyPathsExcluded": [".tmp/"],
    "consumerRepositoryTreesDifferFromCcSwitchStoredCopies": True,
    "ccSwitchExactTreeNames": ["kimi-webbridge"],
    "commonAndCodexTreeDigestsMatch": True,
    "treeDigests": {
        "capability-router": {
            "sha256": "0b8353d560cc9db5d4e6597c7cf9bb1167068081aa612e078848dd90b5a138be",
            "fileCount": 2,
        },
        "closure-contract": {
            "sha256": "e8f49bc07384c8cadaba5514311ee10ab5f08a16a9ab48ee95058d8ed885e0f6",
            "fileCount": 1,
        },
        "intent-contract": {
            "sha256": "51a50d52c2dd8daf8e7636e977de96ba04876792a2a1e0bef047f4fc12b6cb34",
            "fileCount": 2,
        },
        "kimi-webbridge": {
            "sha256": "7b6432f344d01dafc1f0fa717fff87efdf95d19092d468e7bc7415cfb08ea23e",
            "fileCount": 2,
        },
    },
}


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def validate_snapshot_record(
    record: dict[str, Any],
    *,
    acceptance: dict[str, Any] | None = None,
    root: Path = ROOT,
) -> None:
    """Validate one in-memory dated mapping record without reading live homes."""
    _require(
        record.get("schema") == 1
        and record.get("id") == "codex-consumer-skill-mapping-snapshot-v1"
        and record.get("status") == "verified-read-only-physical-mapping-partial"
        and record.get("asOf") == "2026-08-07",
        "Codex consumer mapping snapshot identity drifted",
    )
    _require(
        record.get("documentation")
        == "docs/strategy/CODEX-CONSUMER-SKILL-MAPPING-SNAPSHOT-2026-08-07.md"
        and (root / record["documentation"]).is_file(),
        "Codex consumer mapping documentation binding drifted",
    )
    source_bindings = record.get("sourceBindings", {})
    _require(
        source_bindings
        == {
            "currentPortfolioAuthority": str(AUTHORITY_PATH).replace("\\", "/"),
            "predecessorMapping": str(PREDECESSOR_PATH).replace("\\", "/"),
            "programAcceptanceMap": str(ACCEPTANCE_PATH).replace("\\", "/"),
        }
        and all((root / path).is_file() for path in source_bindings.values()),
        "Codex consumer mapping source binding drifted",
    )

    common = record.get("commonRoot", {})
    _require(
        common
        == {
            "path": "C:/Users/15521/.agents/skills",
            "entryCount": 44,
            "symbolicLinkCount": 40,
            "materializedDirectoryCount": 4,
            "readOnlyObservation": True,
        },
        "Codex consumer mapping common-root snapshot drifted",
    )
    codex = record.get("codexSpecificRoot", {})
    _require(
        codex
        == {
            "path": "C:/Users/15521/.codex/skills",
            "allEntryCount": 45,
            "userProjectionEntryCount": 43,
            "intersectionWithCommonRootCount": 43,
            "commonRootOnlyNames": ["doc"],
            "codexUserOnlyNames": [],
            "runtimeOwnedNames": [".system", "codex-primary-runtime"],
            "readOnlyObservation": True,
        },
        "Codex consumer mapping Codex-root snapshot drifted",
    )

    buckets = record.get("projectionBuckets", {})
    _require(
        buckets.get("sourceBackedSymlinks") == list(SOURCE_BACKED_SYMLINKS)
        and buckets.get("localSymlinks") == list(LOCAL_SYMLINKS)
        and buckets.get("sourceBackedMaterialized") == []
        and buckets.get("localMaterialized") == list(LOCAL_MATERIALIZED),
        "Codex consumer mapping projection buckets drifted",
    )
    names = [name for values in buckets.values() for name in values]
    _require(
        len(names) == 44 and len(set(names)) == 44,
        "Codex consumer mapping projection buckets are not unique and complete",
    )

    database = record.get("databaseReconciliation", {})
    _require(
        database.get("path") == "C:/Users/15521/.cc-switch/cc-switch.db"
        and database.get("openMode") == "sqlite-uri-mode-ro"
        and database.get("queriedTable") == "skills"
        and database.get("queriedColumns")
        == [
            "id",
            "name",
            "directory",
            "repo_owner",
            "repo_name",
            "repo_branch",
            "enabled_codex",
            "content_hash",
            "updated_at",
        ]
        and database.get("skillRowCount") == 61
        and database.get("enabledCodexFlagCount") == 44
        and database.get("matchedCommonRootEntryCount") == 44
        and database.get("missingCommonRootRowCount") == 0
        and database.get("sourceBackedCommonRootCount") == 24
        and database.get("localCommonRootCount") == 20
        and database.get("sourceOwner") == "mattpocock"
        and database.get("sourceRepository") == "skills"
        and database.get("sourceRevision") == "v1.2.2"
        and database.get("enabledFlagProvesLoaderOrBehavior") is False,
        "Codex consumer mapping source-backed database reconciliation drifted",
    )
    _require(
        record.get("materializedOwnership") == EXPECTED_MATERIALIZED_OWNERSHIP,
        "Codex consumer mapping materialized ownership drifted",
    )

    claims = record.get("claimBoundary", {})
    _require(
        claims.get("provesDatedPhysicalRootSnapshot") is True
        and claims.get("provesDatabaseRowReconciliation") is True
        and claims.get("provesSourceRevisionForTwentyFourRows") is True
        and claims.get("provesMaterializedTreeIdentity") is True
        and all(
            claims.get(key) is False
            for key in (
                "provesInstructionDiscovery",
                "provesLoaderPrecedence",
                "provesEnablement",
                "provesInvocation",
                "provesInstructionDelivery",
                "provesBehavior",
                "provesBackupRestore",
                "provesCrossDeviceOrCrossHostParity",
                "provesProductionReadiness",
            )
        ),
        "Codex consumer mapping claim boundary drifted",
    )
    _require(
        record.get("authorityBoundary")
        and all(value is False for value in record["authorityBoundary"].values()),
        "Codex consumer mapping authority boundary expanded",
    )

    if acceptance is None:
        acceptance = json.loads((root / ACCEPTANCE_PATH).read_text(encoding="utf-8"))
    criteria = {row.get("id"): row for row in acceptance.get("acceptanceCriteria", [])}
    evidence = {row.get("id"): row for row in acceptance.get("evidence", [])}
    for acceptance_id in SUPPORTED_ACCEPTANCE_IDS:
        criterion = criteria.get(acceptance_id, {})
        _require(
            criterion.get("assessment") == "partial"
            and EVIDENCE_ID in criterion.get("evidenceIds", []),
            "Codex consumer mapping acceptance boundary drifted",
        )
    _require(
        evidence.get(EVIDENCE_ID, {}).get("path")
        == str(RECORD_PATH).replace("\\", "/")
        and evidence.get(EVIDENCE_ID, {}).get("supports")
        == list(SUPPORTED_ACCEPTANCE_IDS),
        "Codex consumer mapping evidence binding drifted",
    )


def validate_repository_snapshot(root: Path = ROOT) -> dict[str, Any]:
    """Validate the checked-in snapshot; do not inspect mutable live state."""
    record = json.loads((root / RECORD_PATH).read_text(encoding="utf-8"))
    validate_snapshot_record(record, root=root)
    return record


def main() -> int:
    validate_repository_snapshot()
    print("Codex consumer Skill mapping snapshot validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
