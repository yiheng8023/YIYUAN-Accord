"""Validate governed scenario-to-source evidence bindings."""

from __future__ import annotations

from datetime import date
from pathlib import Path
import re
from typing import Any

from scripts.harness_decision_packet import DecisionPacketError, load_source_evidence_record


BINDING_REGISTRY_PATH = Path("registry/harness-scenario-evidence-bindings-v1.json")
BINDING_MODES = {"scenario-record", "document-level-support"}
BINDING_FIELDS = {
    "scenarioId", "sourcePath", "bindingMode", "identityPointers",
    "aggregateScenarioPointer", "expectedAggregateScenarioId",
    "scenarioIdentityPresentInSource", "bindingEvidenceCeiling", "explanation",
}
REGISTRY_FIELDS = {"schema", "id", "date", "status", "coverageAuthority", "bindings"}
COVERAGE_AUTHORITY_FIELDS = {"path", "id", "sha256"}


def load_binding_registry(
    root: Path, relative: Path = BINDING_REGISTRY_PATH
) -> dict[str, Any]:
    """Load the governed binding registry as a repository-relative JSON object."""

    return load_source_evidence_record(root, relative)["document"]


def validate_binding_registry(root: Path, registry: object, coverage: object) -> None:
    """Fail closed unless bindings exactly match the current coverage authority."""

    normalized_registry = _require_registry(registry)
    coverage_record = _require_dict(
        coverage, "binding-coverage-authority-drift", "Coverage authority record is invalid."
    )
    coverage_document = _require_dict(
        coverage_record.get("document"),
        "binding-coverage-authority-drift",
        "Coverage authority document is invalid.",
    )
    authority = _require_dict(
        normalized_registry["coverageAuthority"],
        "binding-coverage-authority-drift",
        "Registry coverage authority is invalid.",
    )
    if set(authority) != COVERAGE_AUTHORITY_FIELDS or any(
        authority[key] != coverage_record.get(key) for key in COVERAGE_AUTHORITY_FIELDS
    ):
        raise DecisionPacketError(
            "binding-coverage-authority-drift",
            "Registry coverage authority does not match the current coverage source.",
        )

    scenarios = coverage_document.get("scenarioCoverage")
    if not isinstance(scenarios, list) or not all(isinstance(item, dict) for item in scenarios):
        raise DecisionPacketError(
            "binding-scenario-set-drift", "Coverage scenarios are invalid."
        )
    expected_ids = [item.get("scenarioId") for item in scenarios]
    bindings = normalized_registry["bindings"]
    actual_ids = [item.get("scenarioId") for item in bindings]
    if (
        not all(isinstance(item, str) for item in expected_ids)
        or actual_ids != expected_ids
        or len(actual_ids) != len(set(actual_ids))
    ):
        raise DecisionPacketError(
            "binding-scenario-set-drift",
            "Registry bindings must exactly match the current coverage scenario order.",
        )

    for scenario, binding in zip(scenarios, bindings, strict=True):
        _validate_binding_against_scenario(root, binding, scenario)


def resolve_scenario_evidence_binding(
    root: Path, registry: object, scenario: object
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Resolve one coverage scenario through its exact governed source binding."""

    normalized_registry = _require_registry(registry)
    normalized_scenario = _require_dict(
        scenario, "binding-scenario-set-drift", "Coverage scenario is invalid."
    )
    scenario_id = normalized_scenario.get("scenarioId")
    if not isinstance(scenario_id, str):
        raise DecisionPacketError("binding-scenario-set-drift", "Coverage scenario ID is invalid.")
    matching = [item for item in normalized_registry["bindings"] if item["scenarioId"] == scenario_id]
    if len(matching) != 1:
        raise DecisionPacketError(
            "binding-scenario-set-drift", "Scenario must have exactly one registry binding."
        )
    return _validate_binding_against_scenario(root, matching[0], normalized_scenario)


def resolve_json_pointer(document: object, pointer: str) -> object:
    """Resolve one non-root JSON Pointer with stable fail-closed errors."""

    if not isinstance(pointer, str) or not pointer.startswith("/"):
        raise DecisionPacketError("binding-pointer-invalid", "Binding pointer must be a non-root JSON Pointer.")
    current = document
    for raw in pointer[1:].split("/"):
        token = _decode_json_pointer_token(raw)
        if isinstance(current, list):
            if not token.isdigit() or (len(token) > 1 and token.startswith("0")):
                raise DecisionPacketError(
                    "binding-pointer-invalid", "Binding pointer has an invalid array index."
                )
            if int(token) >= len(current):
                raise DecisionPacketError(
                    "binding-pointer-unresolved", "Binding pointer does not resolve."
                )
            current = current[int(token)]
        elif isinstance(current, dict) and token in current:
            current = current[token]
        else:
            raise DecisionPacketError(
                "binding-pointer-unresolved", "Binding pointer does not resolve."
            )
    return current


def _decode_json_pointer_token(raw: str) -> str:
    decoded: list[str] = []
    index = 0
    while index < len(raw):
        character = raw[index]
        if character != "~":
            decoded.append(character)
            index += 1
            continue
        if index + 1 >= len(raw) or raw[index + 1] not in {"0", "1"}:
            raise DecisionPacketError(
                "binding-pointer-invalid", "Binding pointer contains an invalid escape."
            )
        decoded.append("~" if raw[index + 1] == "0" else "/")
        index += 2
    return "".join(decoded)


def _require_dict(value: object, code: str, message: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise DecisionPacketError(code, message)
    return value


def _require_registry(registry: object) -> dict[str, Any]:
    normalized = _require_dict(registry, "binding-registry-invalid", "Binding registry is invalid.")
    if set(normalized) != REGISTRY_FIELDS:
        raise DecisionPacketError(
            "binding-registry-invalid", "Binding registry must contain exactly its v1 fields."
        )
    if (
        not _is_exact_integer(normalized["schema"], 1)
        or not isinstance(normalized["id"], str)
        or normalized["id"] != "harness-scenario-evidence-bindings-v1"
        or not _is_registry_date(normalized["date"])
        or not isinstance(normalized["status"], str)
        or not normalized["status"]
        or not isinstance(normalized["bindings"], list)
    ):
        raise DecisionPacketError("binding-registry-invalid", "Binding registry has invalid v1 fields.")
    for binding in normalized["bindings"]:
        _validate_binding_shape(binding)
    return normalized


def _is_exact_integer(value: object, expected: int) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value == expected


def _is_registry_date(value: object) -> bool:
    if not isinstance(value, str) or re.fullmatch(r"\d{4}-\d{2}-\d{2}", value) is None:
        return False
    try:
        date.fromisoformat(value)
    except ValueError:
        return False
    return True


def _validate_binding_shape(binding: object) -> dict[str, Any]:
    normalized = _require_dict(binding, "binding-mode-invalid", "Binding record is invalid.")
    if set(normalized) != BINDING_FIELDS:
        raise DecisionPacketError(
            "binding-mode-invalid", "Binding record must contain exactly its v1 fields."
        )
    mode = normalized["bindingMode"]
    identity_present = normalized["scenarioIdentityPresentInSource"]
    if identity_present is False and mode != "document-level-support":
        raise DecisionPacketError(
            "document-level-identity-promotion",
            "Only document-level support may omit an independent scenario identity.",
        )
    if (
        not isinstance(normalized["scenarioId"], str)
        or not normalized["scenarioId"]
        or not isinstance(normalized["sourcePath"], str)
        or not normalized["sourcePath"]
        or mode not in BINDING_MODES
        or not isinstance(normalized["identityPointers"], list)
        or not all(isinstance(pointer, str) for pointer in normalized["identityPointers"])
        or len(normalized["identityPointers"]) != len(set(normalized["identityPointers"]))
        or not isinstance(identity_present, bool)
        or not isinstance(normalized["bindingEvidenceCeiling"], str)
        or not normalized["bindingEvidenceCeiling"]
        or not isinstance(normalized["explanation"], str)
        or not normalized["explanation"]
    ):
        raise DecisionPacketError("binding-mode-invalid", "Binding record has invalid field values.")
    if mode == "scenario-record":
        if (
            not normalized["identityPointers"]
            or normalized["aggregateScenarioPointer"] is not None
            or normalized["expectedAggregateScenarioId"] is not None
            or identity_present is not True
        ):
            raise DecisionPacketError(
                "binding-mode-invalid", "Scenario-record binding has an invalid shape."
            )
    else:
        if (
            normalized["identityPointers"]
            or not isinstance(normalized["aggregateScenarioPointer"], str)
            or not normalized["aggregateScenarioPointer"]
            or not isinstance(normalized["expectedAggregateScenarioId"], str)
            or not normalized["expectedAggregateScenarioId"]
            or identity_present is not False
        ):
            raise DecisionPacketError(
                "binding-mode-invalid", "Document-level support binding has an invalid shape."
            )
    return normalized


def _validate_binding_against_scenario(
    root: Path, binding: object, scenario: dict[str, Any]
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    normalized_binding = _validate_binding_shape(binding)
    scenario_id = scenario.get("scenarioId")
    expected_paths = scenario.get("evidenceSourcePaths")
    if not isinstance(scenario_id, str) or not isinstance(expected_paths, list):
        raise DecisionPacketError("binding-scenario-set-drift", "Coverage scenario is invalid.")
    if normalized_binding["scenarioId"] != scenario_id:
        raise DecisionPacketError("binding-scenario-set-drift", "Binding scenario does not match coverage.")
    if expected_paths != [normalized_binding["sourcePath"]]:
        raise DecisionPacketError(
            "binding-source-path-drift", "Binding source path does not match coverage."
        )

    source = load_source_evidence_record(root, normalized_binding["sourcePath"])
    document = source["document"]
    mode = normalized_binding["bindingMode"]
    resolved_identity_values: list[dict[str, object]] = []
    resolved_aggregate_scenario_id: object = None

    if mode == "document-level-support":
        if _matching_identity_pointers(document, scenario_id):
            raise DecisionPacketError(
                "document-level-identity-promotion",
                "Document-level support may not promote a target scenario identity.",
            )
        aggregate_pointer = normalized_binding["aggregateScenarioPointer"]
        expected_aggregate_id = normalized_binding["expectedAggregateScenarioId"]
        assert isinstance(aggregate_pointer, str)
        resolved_aggregate_scenario_id = resolve_json_pointer(document, aggregate_pointer)
        if resolved_aggregate_scenario_id != expected_aggregate_id:
            raise DecisionPacketError(
                "binding-aggregate-identity-drift",
                "Aggregate source scenario identity does not match the registry.",
            )
        source_scenario_id = resolved_aggregate_scenario_id
    else:
        for pointer in normalized_binding["identityPointers"]:
            resolved = resolve_json_pointer(document, pointer)
            if resolved != scenario_id:
                raise DecisionPacketError(
                    "binding-scenario-identity-mismatch",
                    "Binding identity pointer does not resolve to the requested scenario.",
                )
            resolved_identity_values.append({"pointer": pointer, "value": resolved})
        matching_identity_pointers = _declared_surface_identity_pointers(
            document, normalized_binding["identityPointers"], scenario_id
        )
        if set(normalized_binding["identityPointers"]) != set(matching_identity_pointers):
            raise DecisionPacketError(
                "binding-scenario-identity-mismatch",
                "Binding identity pointers do not exactly cover source scenario identities.",
            )
        source_scenario_id = scenario_id

    normalized = {
        **normalized_binding,
        "sourceId": source["id"],
        "sourceScenarioId": source_scenario_id,
        "resolvedIdentityValues": resolved_identity_values,
        "resolvedAggregateScenarioId": resolved_aggregate_scenario_id,
    }
    return normalized, [source]


def _declared_surface_identity_pointers(
    document: object, declared_pointers: list[str], scenario_id: str
) -> list[str]:
    """Enumerate identities only inside the collection surfaces a binding declares."""

    matches: list[str] = []
    for pointer in declared_pointers:
        raw_tokens = pointer[1:].split("/")
        index_position = next(
            (index for index, token in enumerate(raw_tokens) if token.isdigit()), None
        )
        if index_position is None:
            if resolve_json_pointer(document, pointer) == scenario_id:
                matches.append(pointer)
            continue
        collection_pointer = "/" + "/".join(raw_tokens[:index_position])
        collection = resolve_json_pointer(document, collection_pointer)
        if not isinstance(collection, list):
            raise DecisionPacketError(
                "binding-pointer-unresolved", "Binding pointer collection does not resolve to a list."
            )
        suffix = raw_tokens[index_position + 1 :]
        for index, item in enumerate(collection):
            current = item
            resolved = True
            for raw in suffix:
                token = _decode_json_pointer_token(raw)
                if isinstance(current, list):
                    if (
                        not token.isdigit()
                        or (len(token) > 1 and token.startswith("0"))
                        or int(token) >= len(current)
                    ):
                        resolved = False
                        break
                    current = current[int(token)]
                elif isinstance(current, dict) and token in current:
                    current = current[token]
                else:
                    resolved = False
                    break
            if resolved and current == scenario_id:
                candidate = "/" + "/".join(
                    [*raw_tokens[:index_position], str(index), *suffix]
                )
                matches.append(candidate)
    return matches


def _matching_identity_pointers(document: object, scenario_id: str) -> list[str]:
    matches: list[str] = []

    def escaped(token: str) -> str:
        return token.replace("~", "~0").replace("/", "~1")

    def visit(value: object, pointer: str) -> None:
        if isinstance(value, dict):
            scenario_value = value.get("scenarioId")
            if scenario_value == scenario_id:
                matches.append(f"{pointer}/scenarioId")
            scenarios = value.get("scenarios")
            if isinstance(scenarios, list):
                for index, item in enumerate(scenarios):
                    if isinstance(item, dict) and item.get("id") == scenario_id:
                        matches.append(f"{pointer}/scenarios/{index}/id")
            for key, child in value.items():
                visit(child, f"{pointer}/{escaped(key)}")
        elif isinstance(value, list):
            for index, child in enumerate(value):
                visit(child, f"{pointer}/{index}")

    visit(document, "")
    return matches
