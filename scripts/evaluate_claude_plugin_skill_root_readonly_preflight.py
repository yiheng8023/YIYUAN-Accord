#!/usr/bin/env python3
"""Evaluate the Claude Plugin Skill-root read-only inventory preflight."""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
RECORD_PATH = Path(
    "registry/claude-plugin-skill-root-readonly-inventory-preflight-2026-08-07.json"
)
ACCEPTANCE_PATH = Path("registry/program-acceptance-map.json")
CLAUDE_SNAPSHOT_PATH = Path(
    "registry/claude-consumer-skill-projection-snapshot-2026-08-07.json"
)
EVIDENCE_ID = (
    "evidence.claude-plugin-skill-root-readonly-inventory-preflight-2026-08-07"
)
ALLOWED_PATH_CLASSES = (
    "plugin-marketplace-manifests",
    "plugin-version-metadata",
    "plugin-skill-root-locators",
    "filesystem-link-metadata",
)
ALLOWED_FIELDS = (
    "plugin-id",
    "plugin-name",
    "plugin-version",
    "marketplace-id",
    "source-locator",
    "revision-or-digest",
    "skill-root-relative-path",
    "link-target",
    "cache-or-install-state",
)
FORBIDDEN_CONTENT_CLASSES = (
    "credentials",
    "account-data",
    "session-data",
    "prompt-content",
    "settings-content",
    "plugin-payload-body",
    "skill-body",
    "runtime-logs",
)
STOP_RULES = (
    "stop-on-path-escape-outside-claude-plugin-root",
    "stop-if-identity-requires-plugin-execution",
    "stop-if-identity-requires-network-refresh",
    "stop-before-credential-account-session-prompt-settings-or-log-content",
    "record-unknown-without-substitution-when-source-or-revision-is-absent",
)
MUTATION_CASE_IDS = (
    "synthetic-boundary",
    "use-case",
    "target-host",
    "target-root",
    "allowed-path-classes",
    "allowed-fields",
    "forbidden-content",
    "network",
    "plugin-execution",
    "external-write",
    "configuration-mutation",
    "verification-surface",
    "stop-rules",
)


def _blocked(blockers: list[str]) -> dict[str, Any]:
    return {
        "decision": "blocked",
        "blockers": list(dict.fromkeys(blockers)),
        "inventoryExecutionAuthorized": False,
        "claimBoundary": "preflight-mechanism-only",
    }


def evaluate_preflight(request: dict[str, Any]) -> dict[str, Any]:
    """Return a synthetic mechanism decision; never authorize an inventory."""
    blockers: list[str] = []
    task = request.get("task", {})
    data = request.get("dataBoundary", {})
    authority = request.get("authority", {})
    verification = request.get("verification", {})
    stop_rules = request.get("stopRules", [])
    if not isinstance(task, dict):
        task = {}
    if not isinstance(data, dict):
        data = {}
    if not isinstance(authority, dict):
        authority = {}
    if not isinstance(verification, dict):
        verification = {}

    if not (
        request.get("declaredSynthetic") is True
        and request.get("realAuthorizationRepresented") is False
    ):
        blockers.append("synthetic-boundary-missing")
    if task.get("useCase") != "consumer-mapping-evidence-gap":
        blockers.append("use-case-invalid")
    if task.get("targetHost") != "claude-code-local":
        blockers.append("target-host-invalid")
    if task.get("targetRoot") != "C:/Users/15521/.claude/plugins":
        blockers.append("target-root-invalid")
    if data.get("allowedPathClasses") != list(ALLOWED_PATH_CLASSES):
        blockers.append("allowed-path-boundary-invalid")
    if data.get("allowedFields") != list(ALLOWED_FIELDS):
        blockers.append("allowed-field-boundary-invalid")
    if data.get("forbiddenContentClasses") != list(FORBIDDEN_CONTENT_CLASSES):
        blockers.append("forbidden-content-boundary-incomplete")
    if data.get("networkAccessAllowed") is not False:
        blockers.append("network-access-forbidden")
    if authority.get("syntheticReadOnlyBoundaryAcknowledged") is not True:
        blockers.append("synthetic-readonly-boundary-missing")
    for field, blocker in (
        ("pluginExecutionAuthorized", "plugin-execution-forbidden"),
        ("externalWriteAuthorized", "external-write-forbidden"),
        ("configurationMutationAuthorized", "configuration-mutation-forbidden"),
        ("accountOrSessionAccessAuthorized", "account-session-access-forbidden"),
        ("contentBodyReadAuthorized", "content-body-read-forbidden"),
    ):
        if authority.get(field) is not False:
            blockers.append(blocker)
    if verification != {
        "outputPath": "registry/claude-plugin-skill-root-readonly-inventory-YYYY-MM-DD.json",
        "validatorPath": "scripts/validate_claude_plugin_skill_root_readonly_inventory.py",
        "acceptanceAssessmentMustRemain": "partial",
        "evidenceTruthMustBeFieldBound": True,
    }:
        blockers.append("verification-surface-invalid")
    if stop_rules != list(STOP_RULES):
        blockers.append("stop-rules-incomplete")
    if blockers:
        return _blocked(blockers)
    return {
        "decision": "eligible-synthetic-mechanism-only",
        "blockers": [],
        "inventoryExecutionAuthorized": False,
        "claimBoundary": "preflight-mechanism-only",
    }


def _mutation_cases(request: dict[str, Any]) -> list[tuple[str, dict[str, Any]]]:
    specifications = (
        ("synthetic-boundary", ("declaredSynthetic",), False),
        ("use-case", ("task", "useCase"), "portfolio-growth"),
        ("target-host", ("task", "targetHost"), "all-hosts"),
        ("target-root", ("task", "targetRoot"), "C:/Users/15521/.claude"),
        ("allowed-path-classes", ("dataBoundary", "allowedPathClasses"), []),
        ("allowed-fields", ("dataBoundary", "allowedFields"), []),
        ("forbidden-content", ("dataBoundary", "forbiddenContentClasses"), []),
        ("network", ("dataBoundary", "networkAccessAllowed"), True),
        ("plugin-execution", ("authority", "pluginExecutionAuthorized"), True),
        ("external-write", ("authority", "externalWriteAuthorized"), True),
        ("configuration-mutation", ("authority", "configurationMutationAuthorized"), True),
        ("verification-surface", ("verification", "outputPath"), "C:/temp/result.json"),
        ("stop-rules", ("stopRules",), []),
    )
    cases: list[tuple[str, dict[str, Any]]] = []
    for case_id, path, replacement in specifications:
        mutated = copy.deepcopy(request)
        target: Any = mutated
        for key in path[:-1]:
            target = target[key]
        target[path[-1]] = replacement
        cases.append((case_id, mutated))
    return cases


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def validate_preflight_record(
    record: dict[str, Any],
    *,
    acceptance: dict[str, Any] | None = None,
    root: Path = ROOT,
) -> None:
    _require(
        record.get("schema") == 1
        and record.get("id")
        == "claude-plugin-skill-root-readonly-inventory-preflight-v1"
        and record.get("asOf") == "2026-08-07"
        and record.get("status")
        == "blocked-awaiting-explicit-readonly-authorization",
        "Claude Plugin inventory preflight identity drifted",
    )
    _require(
        record.get("documentation")
        == "docs/strategy/CLAUDE-PLUGIN-SKILL-ROOT-READONLY-INVENTORY-PREFLIGHT-2026-08-07.md"
        and (root / record["documentation"]).is_file(),
        "Claude Plugin inventory preflight documentation binding drifted",
    )
    _require(
        record.get("sourceBindings")
        == {
            "claudeConsumerProjectionSnapshot": str(CLAUDE_SNAPSHOT_PATH).replace(
                "\\", "/"
            ),
            "programAcceptanceMap": str(ACCEPTANCE_PATH).replace("\\", "/"),
        },
        "Claude Plugin inventory preflight source binding drifted",
    )
    request = record.get("syntheticFixture", {}).get("request", {})
    _require(
        evaluate_preflight(request)
        == {
            "decision": "eligible-synthetic-mechanism-only",
            "blockers": [],
            "inventoryExecutionAuthorized": False,
            "claimBoundary": "preflight-mechanism-only",
        },
        "Claude Plugin inventory preflight positive fixture drifted",
    )
    mutations = _mutation_cases(request)
    _require(
        record.get("failureInjectionCaseIds") == list(MUTATION_CASE_IDS)
        and [case_id for case_id, _ in mutations] == list(MUTATION_CASE_IDS),
        "Claude Plugin inventory preflight mutation ledger drifted",
    )
    for case_id, mutated in mutations:
        result = evaluate_preflight(mutated)
        _require(
            result.get("decision") == "blocked"
            and result.get("inventoryExecutionAuthorized") is False,
            f"Claude Plugin inventory preflight mutation did not fail closed: {case_id}",
        )
    _require(
        record.get("currentDecision")
        == {
            "readOnlyInventoryAuthorized": False,
            "decision": "await-explicit-user-authorization",
            "eligibleSyntheticFixtureIsNotAuthorization": True,
        },
        "Claude Plugin inventory preflight current decision drifted",
    )
    _require(
        record.get("claimBoundary")
        == {
            "provesPreflightMechanism": True,
            "provesLiveInventory": False,
            "provesPluginOrSkillIdentity": False,
            "provesEnablement": False,
            "provesLoaderPrecedence": False,
            "provesInvocation": False,
            "provesBehavior": False,
            "provesValue": False,
            "provesProductionReadiness": False,
        },
        "Claude Plugin inventory preflight claim boundary drifted",
    )
    _require(
        record.get("authorityBoundary")
        and all(value is False for value in record["authorityBoundary"].values()),
        "Claude Plugin inventory preflight authority boundary expanded",
    )
    if acceptance is None:
        acceptance = json.loads((root / ACCEPTANCE_PATH).read_text(encoding="utf-8"))
    criteria = {row.get("id"): row for row in acceptance.get("acceptanceCriteria", [])}
    evidence = {row.get("id"): row for row in acceptance.get("evidence", [])}
    criterion = criteria.get("acceptance.consumer-mapping-evidence", {})
    _require(
        criterion.get("assessment") == "partial"
        and EVIDENCE_ID in criterion.get("evidenceIds", []),
        "Claude Plugin inventory preflight acceptance boundary drifted",
    )
    _require(
        evidence.get(EVIDENCE_ID, {}).get("path")
        == str(RECORD_PATH).replace("\\", "/")
        and evidence.get(EVIDENCE_ID, {}).get("supports")
        == ["acceptance.consumer-mapping-evidence"],
        "Claude Plugin inventory preflight evidence binding drifted",
    )


def validate_repository_preflight(root: Path = ROOT) -> dict[str, Any]:
    record = json.loads((root / RECORD_PATH).read_text(encoding="utf-8"))
    validate_preflight_record(record, root=root)
    return record


def main() -> int:
    validate_repository_preflight()
    print("Claude Plugin Skill-root read-only inventory preflight passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
