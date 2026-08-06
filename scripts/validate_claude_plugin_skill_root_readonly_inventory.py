#!/usr/bin/env python3
"""Validate the field-bound Claude Plugin Skill-root read-only inventory."""

from __future__ import annotations

import json
from pathlib import Path, PurePosixPath
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
RECORD_PATH = Path(
    "registry/claude-plugin-skill-root-readonly-inventory-2026-08-07.json"
)
ACCEPTANCE_PATH = Path("registry/program-acceptance-map.json")
EVIDENCE_ID = "evidence.claude-plugin-skill-root-readonly-inventory-2026-08-07"
ALLOWED_FIELDS = {
    "plugin-id",
    "plugin-name",
    "plugin-version",
    "marketplace-id",
    "source-locator",
    "revision-or-digest",
    "skill-root-relative-path",
    "link-target",
    "cache-or-install-state",
}
ALLOWED_CACHE_STATES = {
    "marketplace-cache-root-present-install-and-enablement-unknown",
    "catalog-metadata-only-payload-not-read-install-and-enablement-unknown",
}


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def _validate_relative_path(value: str) -> None:
    path = PurePosixPath(value)
    _require(
        value.startswith("./")
        and not path.is_absolute()
        and ".." not in path.parts,
        "Claude Plugin inventory path boundary drifted",
    )


def validate_inventory_record(
    record: dict[str, Any],
    *,
    acceptance: dict[str, Any] | None = None,
    root: Path = ROOT,
) -> None:
    _require(
        record.get("schema") == 1
        and record.get("id")
        == "claude-plugin-skill-root-readonly-inventory-2026-08-07"
        and record.get("asOf") == "2026-08-07"
        and record.get("status")
        == "verified-readonly-field-bound-inventory-partial",
        "Claude Plugin inventory identity drifted",
    )
    for key in ("documentation", "validator", "tests"):
        _require(
            isinstance(record.get(key), str) and (root / record[key]).is_file(),
            f"Claude Plugin inventory {key} binding drifted",
        )
    _require(
        record.get("sourceBindings")
        == {
            "preflight": "registry/claude-plugin-skill-root-readonly-inventory-preflight-2026-08-07.json",
            "claudeConsumerProjectionSnapshot": "registry/claude-consumer-skill-projection-snapshot-2026-08-07.json",
            "programAcceptanceMap": "registry/program-acceptance-map.json",
            "targetRoot": "C:/Users/15521/.claude/plugins",
        },
        "Claude Plugin inventory source binding drifted",
    )
    scope = record.get("inventoryScope", {})
    _require(
        set(scope.get("allowedFields", [])) == ALLOWED_FIELDS
        and scope.get("allowedPathClasses")
        == [
            "plugin-marketplace-manifests",
            "plugin-version-metadata",
            "plugin-skill-root-locators",
            "filesystem-link-metadata",
        ]
        and scope.get("forbiddenContentClasses")
        == [
            "credentials",
            "account-data",
            "session-data",
            "prompt-content",
            "settings-content",
            "plugin-payload-body",
            "skill-body",
            "runtime-logs",
        ],
        "Claude Plugin inventory field or content boundary drifted",
    )
    _require(
        record.get("authorityBoundary")
        == {
            "readOnlyInventoryAuthorized": True,
            "pluginExecutionAuthorized": False,
            "externalWriteAuthorized": False,
            "configurationMutationAuthorized": False,
            "accountOrSessionAccessAuthorized": False,
            "contentBodyReadAuthorized": False,
            "networkAccessAuthorized": False,
            "installationAuthorized": False,
            "enablementAuthorized": False,
            "deletionAuthorized": False,
            "releaseAuthorized": False,
        },
        "Claude Plugin inventory authority boundary drifted",
    )
    _require(
        record.get("executionBoundary")
        == {
            "filesystemMetadataRead": True,
            "allowlistedManifestMetadataRead": True,
            "networkUsed": False,
            "pluginExecuted": False,
            "configurationMutated": False,
            "accountOrSessionAccessed": False,
            "credentialsRead": False,
            "promptOrSettingsRead": False,
            "pluginPayloadBodyRead": False,
            "skillBodyRead": False,
            "runtimeLogsRead": False,
            "externalStateWritten": False,
        },
        "Claude Plugin inventory execution boundary drifted",
    )
    observations = record.get("observations", {})
    _require(
        observations
        == {
            "registeredMarketplaceCount": 1,
            "catalogPluginMetadataCount": 257,
            "localSkillRootCount": 17,
            "manifestDeclaredRemoteSkillEntryCount": 4,
            "manifestDeclaredRemoteSkillLocatorCount": 17,
            "filesystemReparsePointCount": 0,
            "pathEscapeObserved": False,
            "marketplaceRevisionOrDigest": "f9cb226d81172f53a1787cc3ba90dc9ab51aa169",
            "installState": "unknown-not-read-from-settings",
            "enablementState": "unknown-not-read-from-settings",
        },
        "Claude Plugin inventory observation ledger drifted",
    )
    items = record.get("inventoryItems", [])
    _require(isinstance(items, list) and len(items) == 21, "Claude Plugin inventory item count drifted")
    local_count = 0
    remote_count = 0
    remote_locator_count = 0
    ids: set[str] = set()
    for item in items:
        _require(
            isinstance(item, dict) and set(item) == ALLOWED_FIELDS,
            "Claude Plugin inventory item field boundary drifted",
        )
        _require(
            item["plugin-id"]
            == f"claude-plugins-official:{item['plugin-name']}"
            and item["marketplace-id"] == "claude-plugins-official"
            and item["plugin-id"] not in ids,
            "Claude Plugin inventory identity drifted",
        )
        ids.add(item["plugin-id"])
        state = item["cache-or-install-state"]
        _require(
            state in ALLOWED_CACHE_STATES and "unknown" in state,
            "Claude Plugin inventory claimed install or enablement state",
        )
        _require(item["link-target"] is None, "Claude Plugin inventory link ledger drifted")
        paths = item["skill-root-relative-path"]
        if isinstance(paths, str):
            _validate_relative_path(paths)
            local_count += 1
        else:
            _require(isinstance(paths, list) and paths, "Claude Plugin inventory root locator drifted")
            for path in paths:
                _require(isinstance(path, str), "Claude Plugin inventory root locator drifted")
                _validate_relative_path(path)
            remote_count += 1
            remote_locator_count += len(paths)
    _require(
        (local_count, remote_count, remote_locator_count) == (17, 4, 17),
        "Claude Plugin inventory root counts drifted",
    )
    _require(
        record.get("claimBoundary")
        == {
            "provesDatedFilesystemAndManifestMetadataInventory": True,
            "provesMarketplaceCachePresence": True,
            "provesCompleteClaudePluginInventory": False,
            "provesInstallation": False,
            "provesEnablement": False,
            "provesLoaderPrecedence": False,
            "provesInvocation": False,
            "provesInstructionDelivery": False,
            "provesBehavior": False,
            "provesValue": False,
            "provesCrossHostParity": False,
            "provesProductionReadiness": False,
        },
        "Claude Plugin inventory claim boundary drifted",
    )
    _require(
        record.get("acceptanceBoundary")
        == {
            "criterionId": "acceptance.consumer-mapping-evidence",
            "assessment": "partial",
            "programInventory": "46-verified-15-partial-0-planned",
        },
        "Claude Plugin inventory acceptance summary drifted",
    )
    if acceptance is None:
        acceptance = json.loads((root / ACCEPTANCE_PATH).read_text(encoding="utf-8"))
    criteria = {row.get("id"): row for row in acceptance.get("acceptanceCriteria", [])}
    evidence = {row.get("id"): row for row in acceptance.get("evidence", [])}
    criterion = criteria.get("acceptance.consumer-mapping-evidence", {})
    _require(
        criterion.get("assessment") == "partial"
        and EVIDENCE_ID in criterion.get("evidenceIds", []),
        "Claude Plugin inventory acceptance boundary drifted",
    )
    _require(
        evidence.get(EVIDENCE_ID, {}).get("path")
        == str(RECORD_PATH).replace("\\", "/")
        and evidence.get(EVIDENCE_ID, {}).get("supports")
        == ["acceptance.consumer-mapping-evidence"],
        "Claude Plugin inventory evidence binding drifted",
    )


def validate_repository_inventory(root: Path = ROOT) -> dict[str, Any]:
    record = json.loads((root / RECORD_PATH).read_text(encoding="utf-8"))
    validate_inventory_record(record, root=root)
    return record


def main() -> int:
    validate_repository_inventory()
    print("Claude Plugin Skill-root read-only inventory passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
