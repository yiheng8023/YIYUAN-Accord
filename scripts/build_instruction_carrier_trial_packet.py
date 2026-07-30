#!/usr/bin/env python3
"""Build a read-only, public/private-separated preflight packet for CTX-07.

This module never starts a host task, loads an instruction carrier, invokes a
model, or changes repository/host state.  It only binds the intended carrier
bytes and records whether the named host can emit the loader evidence required
by the existing CTX-07 scorer.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


SCENARIO_ID = "CTX-07"
VALID_LOADER_CAPTURE = {"available", "unavailable", "unknown"}
RULE_IDS = (
    "observed-unknown-separation",
    "unknown-field-preservation",
    "host-approval-separation",
    "counterexample-limit",
)
TOP_LEVEL_KEYS = {
    "schema",
    "id",
    "status",
    "publicPacket",
    "packetSha256",
    "privateOracle",
    "oracleSha256",
    "countsAsLiveHostProof",
    "countsAsWeakAgentAcceptance",
    "countsAsCrossHostParity",
}


def canonical_sha256(value: Any) -> str:
    """Return a stable digest for JSON evidence objects."""

    encoded = json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _require_non_empty(name: str, value: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty string")
    return value.strip()


def _non_empty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _carrier_digest(carrier_path: Path) -> str:
    if not carrier_path.is_file():
        raise ValueError(f"carrier path is not a readable file: {carrier_path}")
    return hashlib.sha256(carrier_path.read_bytes()).hexdigest()


def _is_sha256(value: Any) -> bool:
    return isinstance(value, str) and bool(__import__("re").fullmatch(r"[0-9a-f]{64}", value))


def _contains_actual_condition_field(value: Any) -> bool:
    forbidden = {"actualModel", "actualReasoning", "actualReasoningEffort"}
    if isinstance(value, dict):
        return any(key in forbidden or _contains_actual_condition_field(item) for key, item in value.items())
    if isinstance(value, list):
        return any(_contains_actual_condition_field(item) for item in value)
    return False


def _valid_expected_response(value: Any) -> bool:
    if not isinstance(value, dict) or set(value) != {
        "schema", "carrierId", "ruleResults", "counterexampleOrLimit"
    } or value.get("schema") != 1 or not _non_empty_string(value.get("carrierId")) or not _non_empty_string(value.get("counterexampleOrLimit")):
        return False
    rules = value.get("ruleResults")
    if not isinstance(rules, list) or len(rules) != len(RULE_IDS):
        return False
    return all(
        isinstance(rule, dict)
        and set(rule) == {"ruleId", "disposition", "evidenceClass", "forbiddenClaimAvoided"}
        and rule.get("ruleId") == rule_id
        and rule.get("disposition") == "pass"
        and rule.get("evidenceClass") == "observed"
        and rule.get("forbiddenClaimAvoided") is True
        for rule, rule_id in zip(rules, RULE_IDS)
    )


def _status(loader_evidence_capture: str) -> str:
    if loader_evidence_capture == "available":
        return "ready-for-separately-authorized-live-attempt"
    return "blocked-missing-host-loader-observability"


def build_trial_packet(
    *,
    carrier_path: Path,
    carrier_identity: str,
    host_identity: str,
    host_version: str,
    requested_model: str,
    requested_reasoning_effort: str,
    loader_evidence_capture: str,
) -> dict[str, Any]:
    """Create a packet that is safe to inspect before a separately authorized run.

    ``available`` means only that a host/parent adapter has a declared way to
    capture an exact task-bound loader event.  It is not an observation that a
    carrier was loaded, and it never counts as live, weak-Agent, or cross-host
    evidence.
    """

    if loader_evidence_capture not in VALID_LOADER_CAPTURE:
        raise ValueError(
            "loader_evidence_capture must be available, unavailable, or unknown"
        )
    carrier_path = carrier_path.resolve()
    carrier_sha256 = _carrier_digest(carrier_path)
    carrier_identity = _require_non_empty("carrier_identity", carrier_identity)
    host_identity = _require_non_empty("host_identity", host_identity)
    host_version = _require_non_empty("host_version", host_version)
    requested_model = _require_non_empty("requested_model", requested_model)
    requested_reasoning_effort = _require_non_empty(
        "requested_reasoning_effort", requested_reasoning_effort
    )

    templates = {
        "runId": "ctx07-run-{ordinal:02d}",
        "hostRunId": "ctx07-host-run-{ordinal:02d}",
        "hostThreadId": "ctx07-host-thread-{ordinal:02d}",
        "taskId": "ctx07-task-{ordinal:02d}",
        "minimumIndependentOrdinals": [1, 2, 3],
    }
    public_packet = {
        "schema": 1,
        "id": "instruction-carrier-ctx07-public-packet",
        "scenarioId": SCENARIO_ID,
        "carrier": {
            "identity": carrier_identity,
            "path": str(carrier_path),
            "sha256": carrier_sha256,
        },
        "targetHost": {
            "identity": host_identity,
            "version": host_version,
            "requestedModel": requested_model,
            "requestedReasoningEffort": requested_reasoning_effort,
        },
        "identityTemplates": templates,
        "loaderEvidenceCapture": loader_evidence_capture,
        "formalLiveAttemptGate": {
            "status": _status(loader_evidence_capture),
            "requiredLoaderEvent": {
                "carrierId": carrier_identity,
                "carrierSha256": carrier_sha256,
                "taskId": "must-equal-instantiated-taskId",
                "evidenceSource": "host-instruction-loader-event",
            },
            "nonEvidence": [
                "filesystem presence",
                "startup-visible list",
                "agent self-report",
            ],
        },
        "responseSchema": {
            "topLevelKeys": [
                "schema",
                "carrierId",
                "ruleResults",
                "counterexampleOrLimit",
            ],
            "ruleIds": list(RULE_IDS),
        },
        "authorityBoundary": {
            "hostTaskCreationAuthorizedByPacket": False,
            "hostConfigurationMutationAuthorizedByPacket": False,
            "repositoryMutationAuthorizedByPacket": False,
            "carrierMutationAuthorizedByPacket": False,
        },
    }
    private_oracle = {
        "scenarioId": SCENARIO_ID,
        "expectedResponse": {
            "schema": 1,
            "carrierId": carrier_identity,
            "ruleResults": [
                {
                    "ruleId": rule_id,
                    "disposition": "pass",
                    "evidenceClass": "observed",
                    "forbiddenClaimAvoided": True,
                }
                for rule_id in RULE_IDS
            ],
            "counterexampleOrLimit": (
                "A result is scoped to the recorded host, version, model, carrier "
                "digest, and scenario."
            ),
        },
    }
    return {
        "schema": 1,
        "id": "instruction-carrier-ctx07-trial-preflight",
        "status": _status(loader_evidence_capture),
        "publicPacket": public_packet,
        "packetSha256": canonical_sha256(public_packet),
        "privateOracle": private_oracle,
        "oracleSha256": canonical_sha256(private_oracle),
        "countsAsLiveHostProof": False,
        "countsAsWeakAgentAcceptance": False,
        "countsAsCrossHostParity": False,
    }


def validate_packet_binding(packet: dict[str, Any]) -> list[str]:
    """Return binding/separation errors without treating a packet as a live run."""

    failures: list[str] = []
    if not isinstance(packet, dict) or set(packet) != TOP_LEVEL_KEYS:
        return ["fail-top-level-packet-shape"]
    if _contains_actual_condition_field(packet):
        return ["hard-fail-unobserved-actual-condition-field"]
    if packet.get("schema") != 1 or packet.get("id") != "instruction-carrier-ctx07-trial-preflight":
        return ["fail-top-level-packet-shape"]
    public_packet = packet.get("publicPacket")
    private_oracle = packet.get("privateOracle")
    if not isinstance(public_packet, dict):
        return ["fail-public-packet-shape"]
    expected_public_keys = {
        "schema", "id", "scenarioId", "carrier", "targetHost", "identityTemplates",
        "loaderEvidenceCapture", "formalLiveAttemptGate", "responseSchema", "authorityBoundary",
    }
    if set(public_packet) != expected_public_keys or public_packet.get("schema") != 1 or public_packet.get("id") != "instruction-carrier-ctx07-public-packet" or public_packet.get("scenarioId") != SCENARIO_ID:
        failures.append("fail-public-packet-shape")
    if packet.get("packetSha256") != canonical_sha256(public_packet):
        failures.append("fail-public-packet-digest")
    if not isinstance(private_oracle, dict) or set(private_oracle) != {"scenarioId", "expectedResponse"} or private_oracle.get("scenarioId") != SCENARIO_ID or not _valid_expected_response(private_oracle.get("expectedResponse")):
        failures.append("fail-private-oracle-shape")
    elif packet.get("oracleSha256") != canonical_sha256(private_oracle):
        failures.append("fail-private-oracle-digest")
    else:
        public_text = json.dumps(public_packet, ensure_ascii=False, sort_keys=True)
        private_text = json.dumps(private_oracle, ensure_ascii=False, sort_keys=True)
        if "privateOracle" in public_packet or private_text in public_text:
            failures.append("fail-private-oracle-exposed")

    target_host = public_packet.get("targetHost")
    if not isinstance(target_host, dict) or set(target_host) != {
        "identity", "version", "requestedModel", "requestedReasoningEffort"
    } or any(not _non_empty_string(target_host.get(key)) for key in target_host):
        failures.append("fail-target-host-shape")

    templates = public_packet.get("identityTemplates")
    expected_templates = {"runId", "hostRunId", "hostThreadId", "taskId", "minimumIndependentOrdinals"}
    if not isinstance(templates, dict) or set(templates) != expected_templates or any(
        not _non_empty_string(templates.get(key)) for key in expected_templates - {"minimumIndependentOrdinals"}
    ) or templates.get("minimumIndependentOrdinals") != [1, 2, 3]:
        failures.append("fail-identity-templates-shape")

    capture = public_packet.get("loaderEvidenceCapture")
    if capture not in VALID_LOADER_CAPTURE:
        failures.append("fail-loader-evidence-capture-state")
    expected_status = _status(capture) if capture in VALID_LOADER_CAPTURE else None
    if packet.get("status") != expected_status:
        failures.append("fail-preflight-status")
    if capture != "available" and packet.get("status") != "blocked-missing-host-loader-observability":
        failures.append("hard-fail-nonavailable-loader-capture-promoted")

    carrier = public_packet.get("carrier")
    if (
        not isinstance(carrier, dict)
        or set(carrier) != {"identity", "path", "sha256"}
        or not _non_empty_string(carrier.get("identity"))
        or not isinstance(carrier.get("path"), str)
        or not Path(carrier["path"]).is_absolute()
        or not _is_sha256(carrier.get("sha256"))
    ):
        failures.append("fail-carrier-binding")
    elif isinstance(private_oracle, dict):
        expected = private_oracle.get("expectedResponse")
        if not isinstance(expected, dict) or expected.get("carrierId") != carrier["identity"]:
            failures.append("fail-carrier-identity-binding")

    formal_gate = public_packet.get("formalLiveAttemptGate")
    if not isinstance(formal_gate, dict) or set(formal_gate) != {"status", "requiredLoaderEvent", "nonEvidence"}:
        failures.append("fail-formal-gate-shape")
    else:
        required_event = formal_gate.get("requiredLoaderEvent")
        if not isinstance(required_event, dict) or set(required_event) != {
            "carrierId", "carrierSha256", "taskId", "evidenceSource"
        } or required_event.get("carrierId") != carrier.get("identity") or required_event.get("carrierSha256") != carrier.get("sha256") or required_event.get("taskId") != "must-equal-instantiated-taskId" or required_event.get("evidenceSource") != "host-instruction-loader-event" or formal_gate.get("status") != expected_status or formal_gate.get("nonEvidence") != ["filesystem presence", "startup-visible list", "agent self-report"]:
            failures.append("fail-formal-gate-shape")

    response_schema = public_packet.get("responseSchema")
    if not isinstance(response_schema, dict) or set(response_schema) != {"topLevelKeys", "ruleIds"} or response_schema.get("topLevelKeys") != ["schema", "carrierId", "ruleResults", "counterexampleOrLimit"] or response_schema.get("ruleIds") != list(RULE_IDS):
        failures.append("fail-response-schema-shape")
    authority = public_packet.get("authorityBoundary")
    if not isinstance(authority, dict) or set(authority) != {"hostTaskCreationAuthorizedByPacket", "hostConfigurationMutationAuthorizedByPacket", "repositoryMutationAuthorizedByPacket", "carrierMutationAuthorizedByPacket"} or any(value is not False for value in authority.values()):
        failures.append("fail-authority-boundary-shape")
    if any(packet.get(key) is not False for key in (
        "countsAsLiveHostProof",
        "countsAsWeakAgentAcceptance",
        "countsAsCrossHostParity",
    )):
        failures.append("hard-fail-preflight-count-promotion")
    return failures


def validate_loader_event_for_packet(
    packet: dict[str, Any],
    *,
    instantiated_task_id: str,
    loader_event: dict[str, Any],
) -> list[str]:
    """Validate the run-time loader event against one prepared public packet.

    This deliberately validates only packet binding.  The canonical CTX-07
    evaluator still decides whether the full host observation is admissible.
    """

    failures = validate_packet_binding(packet)
    public_packet = packet.get("publicPacket")
    if not isinstance(public_packet, dict):
        return failures
    if public_packet.get("loaderEvidenceCapture") != "available":
        return failures + ["blocked-missing-host-loader-observability"]
    if not isinstance(instantiated_task_id, str) or not instantiated_task_id.strip():
        return failures + ["fail-instantiated-task-id"]
    if not isinstance(loader_event, dict) or set(loader_event) != {
        "carrierId",
        "carrierSha256",
        "taskId",
        "evidenceSource",
    }:
        return failures + ["fail-loader-event-shape"]
    carrier = public_packet.get("carrier", {})
    if loader_event.get("carrierId") != carrier.get("identity"):
        failures.append("fail-loader-event-carrier-identity")
    if loader_event.get("taskId") != instantiated_task_id:
        failures.append("fail-loader-event-task-binding")
    if loader_event.get("carrierSha256") != carrier.get("sha256"):
        failures.append("fail-loader-event-carrier-digest")
    if loader_event.get("evidenceSource") != "host-instruction-loader-event":
        failures.append("fail-loader-event-source")
    return failures


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--carrier", required=True, type=Path)
    parser.add_argument("--carrier-id", required=True)
    parser.add_argument("--host", required=True)
    parser.add_argument("--host-version", required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--reasoning", required=True)
    parser.add_argument(
        "--loader-evidence-capture", choices=sorted(VALID_LOADER_CAPTURE), required=True
    )
    args = parser.parse_args()
    packet = build_trial_packet(
        carrier_path=args.carrier,
        carrier_identity=args.carrier_id,
        host_identity=args.host,
        host_version=args.host_version,
        requested_model=args.model,
        requested_reasoning_effort=args.reasoning,
        loader_evidence_capture=args.loader_evidence_capture,
    )
    public_envelope = {key: value for key, value in packet.items() if key != "privateOracle"}
    print(json.dumps(public_envelope, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
