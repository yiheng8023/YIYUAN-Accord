"""Build and validate Harness decision packet v2 projections."""

from __future__ import annotations

import copy
from pathlib import Path
from typing import Any

from scripts.harness_decision_packet import (
    DecisionPacketError,
    PACKET_FIELDS,
    build_decision_packet_from_bundle,
    canonical_json_bytes,
    canonical_sha256,
    load_current_authority_bundle,
    load_source_evidence_record,
    validate_authority_bundle,
    validate_decision_packet_projection,
    validate_decision_request,
)
from scripts.harness_scenario_evidence_binding import (
    BINDING_REGISTRY_PATH,
    load_binding_registry,
    resolve_scenario_evidence_binding,
    validate_binding_registry,
)


PACKET_V2_FIELDS = PACKET_FIELDS | {"scenarioEvidenceBinding"}
SCENARIO_EVIDENCE_BINDING_FIELDS = {
    "registry",
    "scenarioId",
    "sourcePath",
    "bindingMode",
    "identityPointers",
    "resolvedIdentityValues",
    "aggregateScenarioPointer",
    "sourceScenarioId",
    "scenarioIdentityPresentInSource",
    "bindingEvidenceCeiling",
}


def _public_scenario_evidence_binding(
    normalized: dict[str, Any], registry_record: dict[str, Any]
) -> dict[str, Any]:
    """Project the richer internal binding into the exact public v2 contract."""

    projection = {
        "registry": {key: registry_record[key] for key in ("path", "id", "sha256")},
        "scenarioId": normalized["scenarioId"],
        "sourcePath": normalized["sourcePath"],
        "bindingMode": normalized["bindingMode"],
        "identityPointers": copy.deepcopy(normalized["identityPointers"]),
        "resolvedIdentityValues": copy.deepcopy(normalized["resolvedIdentityValues"]),
        "aggregateScenarioPointer": normalized["aggregateScenarioPointer"],
        "sourceScenarioId": normalized["sourceScenarioId"],
        "scenarioIdentityPresentInSource": normalized["scenarioIdentityPresentInSource"],
        "bindingEvidenceCeiling": normalized["bindingEvidenceCeiling"],
    }
    assert set(projection) == SCENARIO_EVIDENCE_BINDING_FIELDS
    return projection


def load_v2_bundle(root: Path, request: object) -> tuple[dict[str, Any], dict[str, Any]]:
    """Load the v2 authority bundle and its public scenario binding projection."""

    core = load_current_authority_bundle(root, request)
    registry = load_binding_registry(root)
    registry_record = load_source_evidence_record(root, BINDING_REGISTRY_PATH)
    validate_binding_registry(root, registry, core["coverage"])
    normalized, sources = resolve_scenario_evidence_binding(
        root, registry, core["scenario"]
    )
    bundle = {**core, "sourceEvidence": sources}
    validate_authority_bundle(bundle, request)
    return bundle, _public_scenario_evidence_binding(normalized, registry_record)


def build_decision_packet_v2(root: Path, request: object) -> dict[str, Any]:
    """Build a deterministic v2 packet with one governed scenario binding."""

    validate_decision_request(request)
    assert isinstance(request, dict)
    bundle, normalized = load_v2_bundle(root, request)
    packet = build_decision_packet_from_bundle(
        root,
        request,
        bundle,
        schema=2,
        packet_id_prefix="harness-decision-packet-v2",
        extra_fields={"scenarioEvidenceBinding": normalized},
    )
    validate_decision_packet_v2(root, packet)
    return packet


def validate_decision_packet_v2(root: Path, packet: object) -> None:
    """Independently reload and compare every v2 authority and binding field."""

    if not isinstance(packet, dict) or set(packet) != PACKET_V2_FIELDS:
        raise DecisionPacketError(
            "invalid-packet-shape", "Decision packet must contain exactly the v2 fields."
        )
    request = packet.get("request")
    validate_decision_request(request)
    bundle, expected_binding = load_v2_bundle(root, request)
    validate_decision_packet_projection(
        root,
        bundle,
        packet,
        packet_fields=PACKET_V2_FIELDS,
        schema=2,
        packet_id_prefix="harness-decision-packet-v2",
    )

    actual_binding = packet.get("scenarioEvidenceBinding")
    if isinstance(actual_binding, dict):
        document_level_promoted = (
            expected_binding["bindingMode"] == "document-level-support"
            and (
                actual_binding.get("bindingMode") != "document-level-support"
                or actual_binding.get("scenarioIdentityPresentInSource") is not False
            )
        )
        invalid_absent_identity_mode = (
            actual_binding.get("scenarioIdentityPresentInSource") is False
            and actual_binding.get("bindingMode") != "document-level-support"
        )
        if document_level_promoted or invalid_absent_identity_mode:
            raise DecisionPacketError(
                "document-level-identity-promotion",
                "Document-level support cannot be promoted to an independent scenario identity.",
            )
    if actual_binding != expected_binding:
        raise DecisionPacketError(
            "historical-authority-promotion",
            "Packet scenario evidence binding differs from the governed source projection.",
        )

    body = {key: value for key, value in packet.items() if key != "packetSha256"}
    if packet.get("packetSha256") != canonical_sha256(body):
        raise DecisionPacketError("packet-digest-mismatch", "Packet digest is invalid.")


def serialize_decision_packet_v2(packet: object) -> bytes:
    """Return canonical v2 JSON bytes plus one newline."""

    return canonical_json_bytes(packet) + b"\n"
