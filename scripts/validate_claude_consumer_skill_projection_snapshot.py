#!/usr/bin/env python3
"""Validate the dated read-only Claude consumer Skill projection snapshot."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

try:
    from scripts.validate_codex_consumer_skill_mapping_snapshot import (
        SOURCE_BACKED_SYMLINKS,
    )
except ModuleNotFoundError:  # Direct script execution places scripts/ on sys.path.
    from validate_codex_consumer_skill_mapping_snapshot import (  # type: ignore[no-redef]
        SOURCE_BACKED_SYMLINKS,
    )


ROOT = Path(__file__).resolve().parent.parent
RECORD_PATH = Path(
    "registry/claude-consumer-skill-projection-snapshot-2026-08-07.json"
)
ACCEPTANCE_PATH = Path("registry/program-acceptance-map.json")
AUTHORITY_PATH = Path("registry/skill-portfolio-current-authority.json")
CODEX_SNAPSHOT_PATH = Path(
    "registry/codex-consumer-skill-mapping-snapshot-2026-08-07.json"
)
EVIDENCE_ID = "evidence.claude-consumer-skill-projection-snapshot-2026-08-07"
SUPPORTED_ACCEPTANCE_IDS = (
    "acceptance.consumer-mapping-evidence",
    "acceptance.cc-switch-source-preserving-skill-pool",
    "acceptance.foreign-managed-capability-coexistence",
)
LOCAL_SYMLINKS = (
    "capability-router",
    "caveman",
    "closure-contract",
    "design-an-interface",
    "disciplined-coding",
    "doc",
    "edit-article",
    "intent-contract",
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


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def validate_snapshot_record(
    record: dict[str, Any],
    *,
    acceptance: dict[str, Any] | None = None,
    root: Path = ROOT,
) -> None:
    """Validate a checked-in snapshot without consulting mutable live state."""
    _require(
        record.get("schema") == 1
        and record.get("id") == "claude-consumer-skill-projection-snapshot-v1"
        and record.get("asOf") == "2026-08-07"
        and record.get("status")
        == "verified-read-only-cc-switch-projection-partial",
        "Claude consumer projection snapshot identity drifted",
    )
    _require(
        record.get("documentation")
        == "docs/strategy/CLAUDE-CONSUMER-SKILL-PROJECTION-SNAPSHOT-2026-08-07.md"
        and (root / record["documentation"]).is_file(),
        "Claude consumer projection documentation binding drifted",
    )
    sources = record.get("sourceBindings", {})
    _require(
        sources
        == {
            "currentPortfolioAuthority": str(AUTHORITY_PATH).replace("\\", "/"),
            "codexConsumerSnapshot": str(CODEX_SNAPSHOT_PATH).replace("\\", "/"),
            "programAcceptanceMap": str(ACCEPTANCE_PATH).replace("\\", "/"),
        }
        and all((root / path).is_file() for path in sources.values()),
        "Claude consumer projection source binding drifted",
    )
    _require(
        record.get("claudeSkillRoot")
        == {
            "path": "C:/Users/15521/.claude/skills",
            "entryCount": 44,
            "symbolicLinkCount": 43,
            "materializedDirectoryCount": 1,
            "nameSetMatchesCommonRoot": True,
            "readOnlyObservation": True,
        },
        "Claude root snapshot drifted",
    )
    buckets = record.get("projectionBuckets", {})
    _require(
        buckets.get("sourceBackedSymlinks") == list(SOURCE_BACKED_SYMLINKS)
        and buckets.get("localSymlinks") == list(LOCAL_SYMLINKS)
        and buckets.get("localMaterialized") == ["kimi-webbridge"],
        "Claude projection buckets drifted",
    )
    names = [name for values in buckets.values() for name in values]
    _require(
        len(names) == 44 and len(set(names)) == 44,
        "Claude projection buckets are not unique and complete",
    )
    _require(
        record.get("databaseReconciliation")
        == {
            "path": "C:/Users/15521/.cc-switch/cc-switch.db",
            "openMode": "sqlite-uri-mode-ro",
            "skillRowCount": 61,
            "enabledClaudeFlagCount": 44,
            "enabledCodexFlagCount": 44,
            "enabledBothFlagCount": 44,
            "matchedClaudeRootEntryCount": 44,
            "sourceBackedCount": 24,
            "localCount": 20,
            "sourceRevision": "mattpocock/skills@v1.2.2",
            "enabledFlagsProveLoaderOrBehavior": False,
        },
        "Claude database reconciliation drifted",
    )
    _require(
        record.get("crossConsumerDifference")
        == {
            "controlContractNames": [
                "capability-router",
                "closure-contract",
                "intent-contract",
            ],
            "controlContractsUseCcSwitchLinksOnClaude": True,
            "controlContractsUseConsumerRepositoryMaterializedTreesOnCommonAndCodexRoots": True,
            "hostProjectionByteParityRequired": False,
            "differenceProvesLoaderOrValue": False,
        },
        "Claude cross-consumer projection boundary drifted",
    )
    _require(
        record.get("pluginBoundary")
        == {
            "path": "C:/Users/15521/.claude/plugins",
            "rootExistenceObserved": True,
            "pluginSkillRootsInventoried": False,
            "pluginPayloadsOrSettingsRead": False,
            "pluginStateProved": False,
        },
        "Claude plugin boundary drifted",
    )
    claims = record.get("claimBoundary", {})
    _require(
        claims.get("provesDatedPhysicalProjectionSnapshot") is True
        and claims.get("provesCrossConsumerProjectionDifference") is True
        and claims.get("provesDatabaseFlagReconciliation") is True
        and all(
            claims.get(key) is False
            for key in (
                "provesInstructionDiscovery",
                "provesLoaderPrecedence",
                "provesEnablement",
                "provesInvocation",
                "provesInstructionDelivery",
                "provesBehavior",
                "provesPluginMapping",
                "provesBackupRestore",
                "provesCrossDeviceParity",
                "provesProductionReadiness",
            )
        ),
        "Claude projection claim boundary drifted",
    )
    _require(
        record.get("authorityBoundary")
        and all(value is False for value in record["authorityBoundary"].values()),
        "Claude projection authority boundary expanded",
    )
    if acceptance is None:
        acceptance = json.loads((root / ACCEPTANCE_PATH).read_text(encoding="utf-8"))
    criteria = {row.get("id"): row for row in acceptance.get("acceptanceCriteria", [])}
    evidence = {row.get("id"): row for row in acceptance.get("evidence", [])}
    for acceptance_id in SUPPORTED_ACCEPTANCE_IDS:
        _require(
            criteria.get(acceptance_id, {}).get("assessment") == "partial"
            and EVIDENCE_ID
            in criteria.get(acceptance_id, {}).get("evidenceIds", []),
            "Claude projection acceptance boundary drifted",
        )
    _require(
        evidence.get(EVIDENCE_ID, {}).get("path")
        == str(RECORD_PATH).replace("\\", "/")
        and evidence.get(EVIDENCE_ID, {}).get("supports")
        == list(SUPPORTED_ACCEPTANCE_IDS),
        "Claude projection evidence binding drifted",
    )


def validate_repository_snapshot(root: Path = ROOT) -> dict[str, Any]:
    record = json.loads((root / RECORD_PATH).read_text(encoding="utf-8"))
    validate_snapshot_record(record, root=root)
    return record


def main() -> int:
    validate_repository_snapshot()
    print("Claude consumer Skill projection snapshot validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
