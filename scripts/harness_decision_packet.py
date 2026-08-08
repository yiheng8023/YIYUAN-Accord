#!/usr/bin/env python3
"""Build and validate source-bound Harness decision packets."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
ROUTE_CLASSES = ("N", "O", "E", "C", "H", "R")
EVIDENCE_LANES = {"portfolio-curation", "mechanism-validation", "task-time"}
SEMANTIC_AUTHORITY_PATH = Path("registry/skill-portfolio-current-authority.json")
COVERAGE_PATH = Path(
    "registry/human-ai-collaboration-current-candidate-capability-coverage-"
    "reconciliation-2026-08-01.json"
)
SCHEDULER_PATH = Path("registry/portfolio-tasktime-projection-contract-2026-08-06.json")
ACCEPTANCE_PATH = Path("registry/program-acceptance-map.json")
REQUEST_FIELDS = {
    "schema",
    "requestId",
    "scenarioId",
    "evidenceLane",
    "expectedSemanticAuthorityId",
    "observedAvailability",
    "taskBinding",
    "currentCapabilityGap",
    "activationAuthority",
}
SCENARIO_ID_PATTERN = re.compile(r"^[A-Z][A-Z0-9-]*$")


class DecisionPacketError(ValueError):
    """A stable machine-readable decision-packet failure."""

    def __init__(self, code: str, message: str, *, path: str | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.path = path

    def as_dict(self) -> dict[str, object]:
        result: dict[str, object] = {
            "status": "error",
            "code": self.code,
            "message": str(self),
        }
        if self.path is not None:
            result["path"] = self.path
        return result


def canonical_json_bytes(value: object) -> bytes:
    """Return the UTF-8 canonical JSON representation used for packet hashes."""

    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def canonical_sha256(value: object) -> str:
    """Return a SHA-256 digest of canonical JSON bytes."""

    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def _is_nonempty_string(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _has_exact_fields(value: object, fields: set[str]) -> bool:
    return isinstance(value, dict) and set(value) == fields


def _is_string_list(
    value: object,
    *,
    allowed: set[str] | None = None,
    require_nonempty: bool = False,
) -> bool:
    if not isinstance(value, list) or (require_nonempty and not value):
        return False
    if not all(_is_nonempty_string(item) for item in value):
        return False
    if len(value) != len(set(value)):
        return False
    return allowed is None or set(value).issubset(allowed)


def _validate_nullable_object(
    value: object,
    *,
    fields: set[str],
    code: str,
    validators: dict[str, Any],
) -> None:
    if value is None:
        return
    if not _has_exact_fields(value, fields):
        raise DecisionPacketError(code, f"{code} must contain exactly its v1 fields.")
    assert isinstance(value, dict)
    for field, validator in validators.items():
        if not validator(value[field]):
            raise DecisionPacketError(code, f"{code} has an invalid {field} field.")


def validate_decision_request(request: object) -> None:
    """Validate the exact v1 request shape and its evidence-bearing fields."""

    if not isinstance(request, dict) or set(request) != REQUEST_FIELDS:
        raise DecisionPacketError(
            "invalid-request-shape",
            "Decision request must contain exactly the v1 request fields.",
        )
    if isinstance(request["activationAuthority"], bool):
        raise DecisionPacketError(
            "invalid-activation-authority",
            "Activation authority must be null or an evidence-backed object.",
        )
    if request["schema"] != 1:
        raise DecisionPacketError("invalid-request-schema", "Request schema must be 1.")
    if not _is_nonempty_string(request["requestId"]):
        raise DecisionPacketError("invalid-request-id", "Request ID must be non-empty.")
    if not isinstance(request["scenarioId"], str) or not SCENARIO_ID_PATTERN.fullmatch(
        request["scenarioId"]
    ):
        raise DecisionPacketError(
            "invalid-scenario-id",
            "Scenario ID must use upper-case letters, digits, and hyphens.",
        )
    if request["evidenceLane"] not in EVIDENCE_LANES:
        raise DecisionPacketError(
            "invalid-evidence-lane",
            "Evidence lane is not recognized by the v1 contract.",
        )
    if not _is_nonempty_string(request["expectedSemanticAuthorityId"]):
        raise DecisionPacketError(
            "invalid-authority-id",
            "Expected semantic authority ID must be non-empty.",
        )

    _validate_nullable_object(
        request["observedAvailability"],
        fields={"asOf", "host", "availableRouteClasses", "evidencePaths"},
        code="invalid-observed-availability",
        validators={
            "asOf": _is_nonempty_string,
            "host": _is_nonempty_string,
            "availableRouteClasses": lambda value: _is_string_list(
                value, allowed=set(ROUTE_CLASSES)
            ),
            "evidencePaths": lambda value: _is_string_list(
                value, require_nonempty=True
            ),
        },
    )
    _validate_nullable_object(
        request["taskBinding"],
        fields={"taskId", "goal", "target", "verificationSurface"},
        code="invalid-task-binding",
        validators={
            "taskId": _is_nonempty_string,
            "goal": _is_nonempty_string,
            "target": _is_nonempty_string,
            "verificationSurface": _is_nonempty_string,
        },
    )
    _validate_nullable_object(
        request["currentCapabilityGap"],
        fields={"requiredCapability", "observedLimitation", "evidencePaths"},
        code="invalid-capability-gap",
        validators={
            "requiredCapability": _is_nonempty_string,
            "observedLimitation": _is_nonempty_string,
            "evidencePaths": lambda value: _is_string_list(
                value, require_nonempty=True
            ),
        },
    )
    _validate_nullable_object(
        request["activationAuthority"],
        fields={"evidencePath", "scope"},
        code="invalid-activation-authority",
        validators={
            "evidencePath": _is_nonempty_string,
            "scope": _is_nonempty_string,
        },
    )


def _resolve_repository_path(root: Path, value: str | Path) -> Path:
    """Resolve a repository-relative path without allowing root escape."""

    relative = Path(value)
    if relative.is_absolute() or ".." in relative.parts:
        raise DecisionPacketError(
            "unsafe-source-path",
            "Source path must be repository-relative and may not traverse parents.",
            path=str(value),
        )
    resolved_root = root.resolve()
    resolved = (resolved_root / relative).resolve()
    if not resolved.is_relative_to(resolved_root):
        raise DecisionPacketError(
            "unsafe-source-path",
            "Resolved source path is outside the repository root.",
            path=str(value),
        )
    return resolved


def _load_json(root: Path, relative: str | Path, missing_code: str) -> dict[str, Any]:
    """Read one repository JSON document with stable typed failures."""

    path = _resolve_repository_path(root, relative)
    if not path.is_file():
        raise DecisionPacketError(missing_code, "Required JSON source is missing.", path=str(relative))
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        raise DecisionPacketError(
            "source-encoding-invalid",
            "Required JSON source is not valid UTF-8.",
            path=str(relative),
        ) from exc
    try:
        document = json.loads(text)
    except json.JSONDecodeError as exc:
        raise DecisionPacketError(
            "source-json-invalid",
            "Required JSON source is not valid JSON.",
            path=str(relative),
        ) from exc
    if not isinstance(document, dict):
        raise DecisionPacketError(
            "source-document-invalid",
            "Required JSON source must contain a top-level object.",
            path=str(relative),
        )
    return document


def _source_sha256(root: Path, relative: str | Path, missing_code: str) -> str:
    path = _resolve_repository_path(root, relative)
    if not path.is_file():
        raise DecisionPacketError(missing_code, "Required source is missing.", path=str(relative))
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _authority_record(
    root: Path,
    relative: Path,
    *,
    missing_code: str,
) -> dict[str, Any]:
    document = _load_json(root, relative, missing_code)
    return {
        "path": relative.as_posix(),
        "id": document.get("id"),
        "sha256": _source_sha256(root, relative, missing_code),
        "document": document,
    }


def _require_dict(value: object, code: str, message: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise DecisionPacketError(code, message)
    return value


def _find_scenario(items: object, key: str, scenario_id: str) -> dict[str, Any] | None:
    if not isinstance(items, list):
        return None
    for item in items:
        if isinstance(item, dict) and item.get(key) == scenario_id:
            return item
    return None


def load_authority_bundle(root: Path, request: object) -> dict[str, Any]:
    """Load the current semantic, coverage, projection, and source authority."""

    validate_decision_request(request)
    assert isinstance(request, dict)
    semantic = _authority_record(root, SEMANTIC_AUTHORITY_PATH, missing_code="semantic-authority-missing")
    if semantic["id"] != request["expectedSemanticAuthorityId"]:
        raise DecisionPacketError(
            "semantic-authority-id-mismatch",
            "Expected semantic authority does not match the current authority.",
        )
    coverage = _authority_record(root, COVERAGE_PATH, missing_code="coverage-authority-missing")
    scheduler = _authority_record(root, SCHEDULER_PATH, missing_code="scheduler-authority-missing")
    acceptance = _authority_record(root, ACCEPTANCE_PATH, missing_code="acceptance-authority-missing")

    scenario = _find_scenario(
        coverage["document"].get("scenarioCoverage"),
        "scenarioId",
        request["scenarioId"],
    )
    if scenario is None:
        raise DecisionPacketError(
            "unknown-scenario",
            "Scenario is not present in the current coverage authority.",
        )

    source_evidence: list[dict[str, Any]] = []
    source_paths = scenario.get("evidenceSourcePaths")
    if not isinstance(source_paths, list) or not source_paths:
        raise DecisionPacketError(
            "evidence-source-missing",
            "Current scenario has no bound original evidence source.",
        )
    for value in source_paths:
        if not _is_nonempty_string(value):
            raise DecisionPacketError("unsafe-source-path", "Evidence source path is invalid.")
        relative = Path(value)
        document = _load_json(root, relative, "evidence-source-missing")
        original_scenario = _find_scenario(document.get("scenarios"), "id", request["scenarioId"])
        if original_scenario is None:
            raise DecisionPacketError(
                "unknown-scenario",
                "Scenario is absent from its bound original evidence source.",
                path=str(value),
            )
        source_evidence.append(
            {
                "path": relative.as_posix(),
                "id": document.get("id"),
                "sha256": _source_sha256(root, relative, "evidence-source-missing"),
                "status": document.get("status"),
                "document": document,
            }
        )

    bundle = {
        "semanticAuthority": semantic,
        "coverage": coverage,
        "scheduler": scheduler,
        "acceptance": acceptance,
        "scenario": scenario,
        "sourceEvidence": source_evidence,
    }
    validate_authority_bundle(bundle, request)
    return bundle


def validate_authority_bundle(bundle: object, request: object) -> None:
    """Fail closed unless a bundle represents the repository's current posture."""

    validate_decision_request(request)
    if not isinstance(bundle, dict):
        raise DecisionPacketError("authority-bundle-invalid", "Authority bundle must be an object.")
    assert isinstance(request, dict)
    semantic = _require_dict(
        bundle.get("semanticAuthority"),
        "authority-bundle-invalid",
        "Semantic authority record is missing.",
    )
    coverage = _require_dict(
        bundle.get("coverage"), "authority-bundle-invalid", "Coverage authority record is missing."
    )
    scheduler = _require_dict(
        bundle.get("scheduler"), "authority-bundle-invalid", "Scheduler authority record is missing."
    )
    acceptance = _require_dict(
        bundle.get("acceptance"), "authority-bundle-invalid", "Acceptance authority record is missing."
    )
    semantic_document = _require_dict(
        semantic.get("document"), "authority-bundle-invalid", "Semantic authority document is invalid."
    )
    scheduler_document = _require_dict(
        scheduler.get("document"), "authority-bundle-invalid", "Scheduler document is invalid."
    )

    expected_ids = {
        "semantic": "skill-portfolio-current-authority-v1",
        "coverage": "human-ai-collaboration-current-candidate-capability-coverage-reconciliation-2026-08-01",
        "scheduler": "portfolio-tasktime-projection-v1",
        "acceptance": "curation-program-acceptance-map-v1",
    }
    if semantic.get("id") != expected_ids["semantic"] or semantic.get("id") != request[
        "expectedSemanticAuthorityId"
    ]:
        raise DecisionPacketError(
            "semantic-authority-id-mismatch", "Semantic authority ID is not current."
        )
    for record, key in ((coverage, "coverage"), (scheduler, "scheduler"), (acceptance, "acceptance")):
        if record.get("id") != expected_ids[key]:
            raise DecisionPacketError("authority-bundle-invalid", f"{key} authority ID is not current.")
    if semantic_document.get("status") != "current-policy-authority":
        raise DecisionPacketError("historical-authority-promotion", "Semantic authority is not current.")
    coverage_document = _require_dict(
        coverage.get("document"), "authority-bundle-invalid", "Coverage document is invalid."
    )
    if coverage_document.get("status") != (
        "zero-model-current-coverage-mapped-overlap-conflict-fallback-and-"
        "unassessed-cells-no-evidence-promotion"
    ):
        raise DecisionPacketError("historical-authority-promotion", "Coverage authority is not current.")

    legacy = _require_dict(
        semantic_document.get("legacyAdaptedRelease"),
        "authority-bundle-invalid",
        "Legacy release boundary is missing.",
    )
    if legacy.get("routingProjectionCurrentAuthority") is not False:
        raise DecisionPacketError(
            "deprecated-routing-authority-promotion",
            "Deprecated routing projection cannot regain current authority.",
        )
    manager = _require_dict(
        semantic_document.get("managerBoundary"),
        "authority-bundle-invalid",
        "Manager boundary is missing.",
    )
    plugin = _require_dict(
        semantic_document.get("pluginDistributionBoundary"),
        "authority-bundle-invalid",
        "Plugin distribution boundary is missing.",
    )
    scheduler_plugin = _require_dict(
        scheduler_document.get("pluginDistributionBoundary"),
        "authority-bundle-invalid",
        "Scheduler plugin boundary is missing.",
    )
    if (
        manager.get("portableProductDependency") is not False
        or plugin.get("portableCoreDependsOnCcSwitch") is not False
        or scheduler_plugin.get("portableCoreDependsOnCcSwitch") is not False
    ):
        raise DecisionPacketError(
            "portable-core-dependency-promotion",
            "Portable core may not depend on CC Switch.",
        )
    if plugin.get("currentPosture") != "plugin-compatible-manager-agnostic-release-not-eligible":
        raise DecisionPacketError("authority-bundle-invalid", "Plugin posture is not current.")
    if plugin.get("releaseEligibleNow") is not False or scheduler_plugin.get(
        "releaseEligibleNow"
    ) is not False:
        raise DecisionPacketError("authority-bundle-invalid", "Plugin release eligibility was promoted.")

    scenario = _require_dict(
        bundle.get("scenario"), "authority-bundle-invalid", "Scenario binding is missing."
    )
    if scenario.get("scenarioId") != request["scenarioId"]:
        raise DecisionPacketError("unknown-scenario", "Scenario binding does not match the request.")
    route_coverage = scenario.get("routeCoverage")
    if not isinstance(route_coverage, dict) or set(route_coverage) != set(ROUTE_CLASSES):
        raise DecisionPacketError(
            "route-class-coverage-incomplete",
            "Scenario coverage must contain exactly the six route classes.",
        )
    source_evidence = bundle.get("sourceEvidence")
    if not isinstance(source_evidence, list) or not source_evidence:
        raise DecisionPacketError("evidence-source-missing", "Original evidence binding is missing.")
    expected_paths = scenario.get("evidenceSourcePaths")
    actual_paths = [item.get("path") for item in source_evidence if isinstance(item, dict)]
    if actual_paths != expected_paths:
        raise DecisionPacketError("evidence-source-missing", "Original evidence paths do not match.")
    for item in source_evidence:
        record = _require_dict(
            item, "authority-bundle-invalid", "Original evidence record is invalid."
        )
        if not _is_nonempty_string(record.get("id")) or not _is_nonempty_string(
            record.get("status")
        ):
            raise DecisionPacketError("authority-bundle-invalid", "Original evidence identity is invalid.")


def validate_bound_source_digests(root: Path, bundle: object) -> None:
    """Reopen every bound authority and original source and reject byte drift."""

    if not isinstance(bundle, dict):
        raise DecisionPacketError("authority-bundle-invalid", "Authority bundle must be an object.")
    records: list[tuple[dict[str, Any], str, str]] = []
    for key in ("semanticAuthority", "coverage", "scheduler", "acceptance"):
        record = _require_dict(
            bundle.get(key), "authority-bundle-invalid", f"{key} record is missing."
        )
        records.append((record, "authority-source-missing", "authority-source-digest-drift"))
    source_evidence = bundle.get("sourceEvidence")
    if not isinstance(source_evidence, list):
        raise DecisionPacketError("evidence-source-missing", "Original evidence binding is missing.")
    for item in source_evidence:
        record = _require_dict(item, "authority-bundle-invalid", "Evidence record is invalid.")
        records.append((record, "evidence-source-missing", "evidence-source-digest-drift"))
    for record, missing_code, drift_code in records:
        path = record.get("path")
        if not _is_nonempty_string(path):
            raise DecisionPacketError("unsafe-source-path", "Bound source path is invalid.")
        current = _source_sha256(root, path, missing_code)
        if current != record.get("sha256"):
            raise DecisionPacketError(
                drift_code,
                "Bound source digest no longer matches current repository bytes.",
                path=path,
            )
