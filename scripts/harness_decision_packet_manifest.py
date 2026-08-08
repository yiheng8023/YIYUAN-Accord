"""Build and validate atomic Harness decision packet manifests."""

from __future__ import annotations

from collections import Counter
import copy
import os
from pathlib import Path
import tempfile
from typing import Any

from scripts.harness_decision_packet import (
    ACCEPTANCE_PATH,
    AUTHORIZATION_GATES,
    COVERAGE_PATH,
    DecisionPacketError,
    PROJECTION_BOUNDARY,
    SCHEDULER_PATH,
    SEMANTIC_AUTHORITY_PATH,
    canonical_json_bytes,
    canonical_sha256,
    load_current_authority_bundle,
    load_source_evidence_record,
)
from scripts.harness_decision_packet_v2 import (
    build_decision_packet_v2,
    validate_decision_packet_v2,
)
from scripts.harness_scenario_evidence_binding import (
    BINDING_REGISTRY_PATH,
    load_binding_registry,
    resolve_scenario_evidence_binding,
    validate_binding_registry,
)


MANIFEST_ID = "harness-decision-packet-thirteen-scenario-manifest-v1"
MANIFEST_FIELDS = {
    "schema",
    "id",
    "packetSchema",
    "authorityBinding",
    "atomic",
    "scenarioCount",
    "entries",
    "executionCounters",
    "authorizationGates",
    "claimBoundary",
    "projectionBoundary",
    "manifestSha256",
}
MANIFEST_ENTRY_FIELDS = {
    "scenarioId",
    "bindingMode",
    "sourcePath",
    "sourceSha256",
    "packetSha256",
    "decisionState",
    "selectedRoute",
    "bindingEvidenceCeiling",
}
AUTHORITY_BINDING_FIELDS = {
    "semanticAuthority",
    "coverage",
    "scheduler",
    "acceptance",
    "bindingRegistry",
}
EXECUTION_COUNTERS = {
    "modelRequestCount": 0,
    "candidateExecutionCount": 0,
    "pluginExecutionCount": 0,
    "managerMutationCount": 0,
    "accountConnectionCount": 0,
    "consumerMutationCount": 0,
    "installationCount": 0,
    "enablementCount": 0,
    "publicationCount": 0,
}
HEX_DIGITS = frozenset("0123456789abcdef")


class BatchBindingError(DecisionPacketError):
    """Aggregate deterministic scenario-binding failures."""

    def __init__(self, issues: list[dict[str, object]]) -> None:
        super().__init__(
            "batch-binding-failed",
            "One or more scenario bindings failed; no manifest was produced.",
        )
        self.issues = copy.deepcopy(issues)

    def as_dict(self) -> dict[str, object]:
        return {**super().as_dict(), "issues": copy.deepcopy(self.issues)}


def build_canonical_probe_request(scenario_id: str) -> dict[str, object]:
    """Return the deterministic zero-model mechanism request for one scenario."""

    return {
        "schema": 1,
        "requestId": f"harness.manifest.v1:{scenario_id}",
        "scenarioId": scenario_id,
        "evidenceLane": "mechanism-validation",
        "expectedSemanticAuthorityId": "skill-portfolio-current-authority-v1",
        "observedAvailability": None,
        "taskBinding": None,
        "currentCapabilityGap": None,
        "activationAuthority": None,
    }


def _public_binding(record: dict[str, Any]) -> dict[str, Any]:
    return {key: record[key] for key in ("path", "id", "sha256")}


def _strict_json_equal(actual: object, expected: object) -> bool:
    """Compare JSON values without Python's bool/int or int/float aliases."""

    if type(actual) is not type(expected):
        return False
    if isinstance(expected, dict):
        return set(actual) == set(expected) and all(
            _strict_json_equal(actual[key], value)
            for key, value in expected.items()
        )
    if isinstance(expected, list):
        return len(actual) == len(expected) and all(
            _strict_json_equal(actual_item, expected_item)
            for actual_item, expected_item in zip(actual, expected, strict=True)
        )
    return actual == expected


def _is_nonempty_string(value: object) -> bool:
    return type(value) is str and bool(value)


def _is_sha256(value: object) -> bool:
    return (
        type(value) is str
        and len(value) == 64
        and set(value).issubset(HEX_DIGITS)
    )


def _is_source_binding(value: object) -> bool:
    return (
        type(value) is dict
        and set(value) == {"path", "id", "sha256"}
        and _is_nonempty_string(value["path"])
        and _is_nonempty_string(value["id"])
        and _is_sha256(value["sha256"])
    )


def _is_manifest_entry(value: object) -> bool:
    return (
        type(value) is dict
        and set(value) == MANIFEST_ENTRY_FIELDS
        and _is_nonempty_string(value["scenarioId"])
        and type(value["bindingMode"]) is str
        and value["bindingMode"] in {"scenario-record", "document-level-support"}
        and _is_nonempty_string(value["sourcePath"])
        and _is_sha256(value["sourceSha256"])
        and _is_sha256(value["packetSha256"])
        and _is_nonempty_string(value["decisionState"])
        and value["selectedRoute"] is None
        and _is_nonempty_string(value["bindingEvidenceCeiling"])
    )


def _issue(
    scenario_id: str | None,
    code: str,
    message: str,
    path: str | None = None,
) -> dict[str, object]:
    return {
        "scenarioId": scenario_id,
        "code": code,
        "message": message,
        "path": path,
    }


def _exception_issue(
    scenario_id: str | None, error: DecisionPacketError
) -> dict[str, object]:
    return _issue(scenario_id, error.code, str(error), error.path)


def _load_manifest_inputs(
    root: Path,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    request = build_canonical_probe_request("GEN-CREATIVE-01")
    authorities: dict[str, Any] | None = None
    registry: dict[str, Any] | None = None
    try:
        authorities = load_current_authority_bundle(root, request)
        registry = load_binding_registry(root)
        registry_record = load_source_evidence_record(root, BINDING_REGISTRY_PATH)
        validate_binding_registry(root, registry, authorities["coverage"])
    except DecisionPacketError as error:
        code = error.code
        if (
            code == "evidence-source-missing"
            and error.path == BINDING_REGISTRY_PATH.as_posix()
        ):
            code = "binding-registry-missing"
        scenario_id: str | None = None
        issue_path = error.path
        binding_specific_codes = {
            "binding-mode-invalid",
            "binding-pointer-invalid",
            "binding-pointer-unresolved",
            "binding-scenario-identity-mismatch",
            "binding-aggregate-identity-drift",
            "document-level-identity-promotion",
        }
        if (
            code in binding_specific_codes
            and authorities is not None
            and registry is not None
        ):
            for scenario in authorities["coverage"]["document"]["scenarioCoverage"]:
                try:
                    resolve_scenario_evidence_binding(root, registry, scenario)
                except DecisionPacketError as candidate:
                    if candidate.code == code:
                        scenario_id = scenario["scenarioId"]
                        source_paths = scenario.get("evidenceSourcePaths")
                        if (
                            issue_path is None
                            and isinstance(source_paths, list)
                            and source_paths
                            and isinstance(source_paths[0], str)
                        ):
                            issue_path = source_paths[0]
                        break
        raise BatchBindingError(
            [_issue(scenario_id, code, str(error), issue_path)]
        ) from error
    return authorities, registry, registry_record


def _build_manifest_projection(root: Path) -> dict[str, Any]:
    authorities, _, registry_record = _load_manifest_inputs(root)
    coverage_scenarios = authorities["coverage"]["document"]["scenarioCoverage"]
    packets: list[dict[str, Any]] = []
    issues: list[dict[str, object]] = []
    for scenario in coverage_scenarios:
        scenario_id = scenario["scenarioId"]
        try:
            packet = build_decision_packet_v2(
                root, build_canonical_probe_request(scenario_id)
            )
            validate_decision_packet_v2(root, packet)
        except DecisionPacketError as error:
            issues.append(_exception_issue(scenario_id, error))
        else:
            packets.append(packet)
    if issues:
        raise BatchBindingError(issues)

    entries: list[dict[str, Any]] = []
    for packet in packets:
        binding = packet["scenarioEvidenceBinding"]
        source = packet["sourceEvidence"][0]
        entries.append(
            {
                "scenarioId": binding["scenarioId"],
                "bindingMode": binding["bindingMode"],
                "sourcePath": binding["sourcePath"],
                "sourceSha256": source["sha256"],
                "packetSha256": packet["packetSha256"],
                "decisionState": packet["decisionState"],
                "selectedRoute": packet["selectedRoute"],
                "bindingEvidenceCeiling": binding["bindingEvidenceCeiling"],
            }
        )

    first_packet = packets[0]
    authority_binding = copy.deepcopy(first_packet["authorityBinding"])
    authority_binding["bindingRegistry"] = _public_binding(registry_record)
    manifest: dict[str, Any] = {
        "schema": 1,
        "id": MANIFEST_ID,
        "packetSchema": 2,
        "authorityBinding": authority_binding,
        "atomic": True,
        "scenarioCount": len(entries),
        "entries": entries,
        "executionCounters": copy.deepcopy(EXECUTION_COUNTERS),
        "authorizationGates": copy.deepcopy(AUTHORIZATION_GATES),
        "claimBoundary": copy.deepcopy(first_packet["claimBoundary"]),
        "projectionBoundary": copy.deepcopy(PROJECTION_BOUNDARY),
    }
    manifest["manifestSha256"] = canonical_sha256(manifest)
    return manifest


def build_decision_packet_manifest(root: Path) -> dict[str, Any]:
    """Build all thirteen packets in memory and return one validated manifest."""

    manifest = _build_manifest_projection(root)
    validate_decision_packet_manifest(root, manifest)
    return manifest


def _raise_manifest_issue(
    code: str,
    message: str,
    *,
    scenario_id: str | None = None,
    path: str | None = None,
) -> None:
    raise BatchBindingError([_issue(scenario_id, code, message, path)])


def validate_decision_packet_manifest(root: Path, manifest: object) -> None:
    """Independently rebuild and compare the complete manifest projection."""

    if type(manifest) is not dict or set(manifest) != MANIFEST_FIELDS:
        _raise_manifest_issue(
            "invalid-manifest-shape",
            "Manifest must contain exactly its v1 fields.",
        )
    assert isinstance(manifest, dict)
    if not (
        type(manifest["schema"]) is int
        and _is_nonempty_string(manifest["id"])
        and type(manifest["packetSchema"]) is int
        and type(manifest["atomic"]) is bool
        and type(manifest["scenarioCount"]) is int
        and type(manifest["entries"]) is list
        and type(manifest["executionCounters"]) is dict
        and type(manifest["authorizationGates"]) is dict
        and type(manifest["claimBoundary"]) is dict
        and type(manifest["projectionBoundary"]) is dict
        and _is_sha256(manifest["manifestSha256"])
    ):
        _raise_manifest_issue(
            "invalid-manifest-shape",
            "Manifest fields must use their exact JSON schema types.",
        )
    entries = manifest.get("entries")
    if not isinstance(entries, list) or not all(
        _is_manifest_entry(entry) for entry in entries
    ):
        _raise_manifest_issue(
            "invalid-manifest-shape",
            "Manifest entries must contain exactly their typed v1 fields.",
        )
    bindings = manifest.get("authorityBinding")
    if (
        type(bindings) is not dict
        or set(bindings) != AUTHORITY_BINDING_FIELDS
        or not all(_is_source_binding(value) for value in bindings.values())
    ):
        _raise_manifest_issue(
            "invalid-manifest-shape",
            "Manifest authority bindings must contain exactly the typed current sources.",
        )

    assert isinstance(bindings, dict)
    current_authority_paths = {
        "semanticAuthority": SEMANTIC_AUTHORITY_PATH,
        "coverage": COVERAGE_PATH,
        "scheduler": SCHEDULER_PATH,
        "acceptance": ACCEPTANCE_PATH,
        "bindingRegistry": BINDING_REGISTRY_PATH,
    }
    for name, relative in current_authority_paths.items():
        try:
            current_record = load_source_evidence_record(root, relative)
        except DecisionPacketError as error:
            raise BatchBindingError([_exception_issue(None, error)]) from error
        current_binding = _public_binding(current_record)
        if bindings.get(name) != current_binding:
            code = (
                "binding-registry-digest-drift"
                if name == "bindingRegistry"
                else "authority-source-digest-drift"
            )
            _raise_manifest_issue(
                code,
                f"Manifest {name} binding differs from current repository bytes.",
                path=relative.as_posix(),
            )

    expected = _build_manifest_projection(root)
    for field in ("schema", "id", "packetSchema", "atomic", "scenarioCount"):
        if not _strict_json_equal(manifest.get(field), expected[field]):
            _raise_manifest_issue(
                "invalid-manifest-shape",
                f"Manifest {field} differs from the v1 contract.",
            )

    expected_bindings = expected["authorityBinding"]
    for name in (
        "semanticAuthority",
        "coverage",
        "scheduler",
        "acceptance",
        "bindingRegistry",
    ):
        if not _strict_json_equal(bindings.get(name), expected_bindings[name]):
            code = (
                "binding-registry-digest-drift"
                if name == "bindingRegistry"
                else "authority-source-digest-drift"
            )
            _raise_manifest_issue(
                code,
                f"Manifest {name} binding differs from current repository bytes.",
                path=expected_bindings[name]["path"],
            )

    assert isinstance(entries, list)
    expected_entries = expected["entries"]
    actual_ids = [entry["scenarioId"] for entry in entries]
    expected_ids = [entry["scenarioId"] for entry in expected_entries]
    if Counter(actual_ids) != Counter(expected_ids):
        _raise_manifest_issue(
            "manifest-entry-set-drift",
            "Manifest entries do not contain the exact current scenario set.",
        )
    if actual_ids != expected_ids:
        _raise_manifest_issue(
            "manifest-entry-order-drift",
            "Manifest entries do not preserve current coverage order.",
        )
    for actual, expected_entry in zip(entries, expected_entries, strict=True):
        if _strict_json_equal(actual, expected_entry):
            continue
        scenario_id = expected_entry["scenarioId"]
        if actual.get("sourceSha256") != expected_entry["sourceSha256"]:
            _raise_manifest_issue(
                "evidence-source-digest-drift",
                "Manifest source digest differs from current repository bytes.",
                scenario_id=scenario_id,
                path=expected_entry["sourcePath"],
            )
        if actual.get("packetSha256") != expected_entry["packetSha256"]:
            _raise_manifest_issue(
                "packet-digest-mismatch",
                "Manifest packet digest is not reproducible from current sources.",
                scenario_id=scenario_id,
            )
        if actual.get("selectedRoute") is not None:
            _raise_manifest_issue(
                "manifest-route-selection",
                "Manifest entries may not select a route.",
                scenario_id=scenario_id,
            )
        _raise_manifest_issue(
            "manifest-entry-drift",
            "Manifest entry differs from its independently rebuilt packet.",
            scenario_id=scenario_id,
            path=expected_entry["sourcePath"],
        )

    if not _strict_json_equal(
        manifest.get("executionCounters"), EXECUTION_COUNTERS
    ):
        _raise_manifest_issue(
            "execution-counter-promotion",
            "Manifest execution counters must remain exactly zero.",
        )
    if not _strict_json_equal(
        manifest.get("authorizationGates"), AUTHORIZATION_GATES
    ):
        _raise_manifest_issue(
            "authorization-gate-promotion",
            "Manifest authorization gates must remain exactly false.",
        )
    if not _strict_json_equal(
        manifest.get("claimBoundary"), expected["claimBoundary"]
    ):
        _raise_manifest_issue(
            "claim-boundary-promotion",
            "Manifest claim boundary differs from current coverage authority.",
        )
    if not _strict_json_equal(manifest.get("projectionBoundary"), PROJECTION_BOUNDARY):
        _raise_manifest_issue(
            "projection-boundary-drift",
            "Manifest projection boundary differs from the packet contract.",
        )
    body = {
        key: value for key, value in manifest.items() if key != "manifestSha256"
    }
    if manifest.get("manifestSha256") != canonical_sha256(body):
        _raise_manifest_issue(
            "manifest-digest-mismatch",
            "Manifest digest is invalid.",
        )


def serialize_decision_packet_manifest(manifest: object) -> bytes:
    """Return canonical manifest JSON bytes plus one newline."""

    return canonical_json_bytes(manifest) + b"\n"


def write_manifest_atomically(path: Path, data: bytes) -> None:
    """Replace one explicit output only after a complete sibling-temp write."""

    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_name: str | None = None
    try:
        with tempfile.NamedTemporaryFile(
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            temporary_name = handle.name
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_name, path)
        temporary_name = None
    finally:
        if temporary_name is not None:
            Path(temporary_name).unlink(missing_ok=True)
