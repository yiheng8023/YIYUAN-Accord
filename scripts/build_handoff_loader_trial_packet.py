#!/usr/bin/env python3
"""Build a read-only loader-observability preflight for HND-FRESH-01 Arm C.

The packet binds only repository-recorded source-backed handoff metadata.  It
does not read the live CC Switch payload, create a task, write an artifact, or
inspect any host/private account surface.
"""

from __future__ import annotations

import argparse
from copy import deepcopy
import hashlib
import json
import re
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
PROTOCOL_PATH = ROOT / "registry/skill-ablation-batch-01-protocol-2026-07-19.json"
PREFLIGHT_CONTRACT_PATH = (
    ROOT / "registry/handoff-loader-trial-preflight-contract-2026-07-24.json"
)
SCENARIO_ID = "ABL-CTX-HANDOFF-01"
VIEW_ID = "HND-FRESH-01"
CAPTURES = {"available", "unavailable", "unknown"}
CAPTURE_EVIDENCE_CLASSES = {
    "parent-adapter-capability-evidence",
    "host-adapter-capability-evidence",
}
CAPTURE_RECORD_FIELDS = {
    "evidenceId",
    "evidenceClass",
    "adapterIdentity",
    "adapterVersion",
    "hostIdentity",
    "hostVersion",
    "captureSurface",
    "artifactRef",
    "artifactSha256",
    "observedAt",
    "evidenceScope",
    "claimBoundary",
}
CAPTURE_RECORD_CLAIM_BOUNDARY = {
    "provesCaptureCapabilityOnly": True,
    "provesLoaderInvocation": False,
    "provesFreshSession": False,
    "provesReceiverOutcome": False,
    "provesAutomaticThreadCreation": False,
    "provesActualModelOrReasoning": False,
}
TOP_LEVEL = {
    "schema", "id", "status", "publicPacket", "packetSha256", "privateOracle",
    "oracleSha256", "countsAsLoaderInvocationProof", "countsAsFreshSessionProof",
    "countsAsWeakAgentAcceptance", "countsAsCrossHostParity",
}


def canonical_sha256(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


def _non_empty(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _sha256(value: Any) -> bool:
    return isinstance(value, str) and bool(re.fullmatch(r"[0-9a-f]{64}", value))


def _status(capture: str) -> str:
    return "ready-for-separately-authorized-handoff-loader-attempt" if capture == "available" else "blocked-missing-handoff-loader-observability"


def load_protocol_handoff_binding(protocol_path: Path = PROTOCOL_PATH) -> dict[str, Any]:
    """Read only repository protocol metadata; never open the live payload root."""

    if protocol_path.resolve() != PROTOCOL_PATH.resolve():
        raise ValueError("only the canonical repository protocol path is allowed")
    protocol_bytes = protocol_path.read_bytes()
    protocol = json.loads(protocol_bytes.decode("utf-8"))
    handoff = protocol["payloadObservation"]["handoff"]
    files = handoff.get("files")
    if (
        not isinstance(files, dict)
        or not files
        or any(not _non_empty(path) or not _sha256(digest) for path, digest in files.items())
        or not _non_empty(handoff.get("selectedIdentity"))
        or not _sha256(handoff.get("harnessTreeHashV1"))
    ):
        raise ValueError("repository protocol handoff binding is invalid")
    return {
        "identity": handoff["selectedIdentity"],
        "harnessTreeHashV1": handoff["harnessTreeHashV1"],
        "files": dict(files),
        "fileManifestSha256": canonical_sha256(files),
        "protocolPath": str(PROTOCOL_PATH.resolve()),
        "protocolSha256": hashlib.sha256(protocol_bytes).hexdigest(),
    }


def validate_capture_capability_registry(document: dict[str, Any]) -> list[str]:
    """Validate the canonical admission surface without observing a host."""

    registry = document.get("captureCapabilityEvidenceRegistry")
    if (
        not isinstance(registry, dict)
        or set(registry)
        != {
            "schema",
            "status",
            "requiredRecordFields",
            "admittedRecords",
            "emptyResult",
            "claimBoundary",
        }
        or registry.get("schema") != 1
        or registry.get("status")
        not in {
            "no-admitted-capture-capability-evidence",
            "admitted-capture-capability-evidence-present",
        }
        or registry.get("requiredRecordFields") != sorted(CAPTURE_RECORD_FIELDS)
        or registry.get("emptyResult")
        != "blocked-missing-handoff-loader-observability"
        or registry.get("claimBoundary")
        != {
            "callerAssertionIsAdmissionEvidence": False,
            "shapeValidReferenceIsAdmissionEvidence": False,
            "registryPresenceProvesLoaderInvocation": False,
            "registryPresenceProvesFreshSession": False,
        }
    ):
        return ["fail-capture-capability-registry-shape"]
    records = registry.get("admittedRecords")
    if not isinstance(records, list):
        return ["fail-capture-capability-registry-shape"]
    failures: list[str] = []
    evidence_ids: list[str] = []
    for record in records:
        if (
            not isinstance(record, dict)
            or set(record) != CAPTURE_RECORD_FIELDS
            or record.get("evidenceClass") not in CAPTURE_EVIDENCE_CLASSES
            or any(
                not _non_empty(record.get(key))
                for key in CAPTURE_RECORD_FIELDS
                - {"claimBoundary", "artifactSha256"}
            )
            or not _sha256(record.get("artifactSha256"))
        ):
            failures.append("fail-capture-capability-record-shape")
            continue
        if record.get("claimBoundary") != CAPTURE_RECORD_CLAIM_BOUNDARY:
            failures.append("hard-fail-capture-capability-claim-promotion")
        evidence_ids.append(record["evidenceId"])
    if len(evidence_ids) != len(set(evidence_ids)):
        failures.append("fail-duplicate-capture-capability-evidence-id")
    if (
        bool(records)
        != (
            registry.get("status")
            == "admitted-capture-capability-evidence-present"
        )
    ):
        failures.append("fail-capture-capability-registry-status")
    return list(dict.fromkeys(failures))


def load_capture_capability_registry(
    contract_path: Path = PREFLIGHT_CONTRACT_PATH,
) -> dict[str, Any]:
    """Load only the repository-owned capture-capability admission record."""

    if contract_path.resolve() != PREFLIGHT_CONTRACT_PATH.resolve():
        raise ValueError("only the canonical capture capability registry is allowed")
    contract_bytes = contract_path.read_bytes()
    document = json.loads(contract_bytes.decode("utf-8"))
    failures = validate_capture_capability_registry(document)
    if failures:
        raise ValueError(f"canonical capture capability registry invalid: {failures[0]}")
    return {
        "path": str(PREFLIGHT_CONTRACT_PATH.resolve()),
        "sha256": hashlib.sha256(contract_bytes).hexdigest(),
        "records": deepcopy(
            document["captureCapabilityEvidenceRegistry"]["admittedRecords"]
        ),
    }


def _capture_adapter_binding(
    capture: str,
    host_identity: str,
    host_version: str,
    adapter_identity: str | None,
    adapter_version: str | None,
    capability_evidence_id: str | None,
    capability_registry: dict[str, Any],
) -> tuple[dict[str, str] | None, dict[str, Any] | None]:
    """Bind an available capture interface without mistaking it for an event."""

    if capture != "available":
        if any(
            value is not None
            for value in (
                adapter_identity,
                adapter_version,
                capability_evidence_id,
            )
        ):
            raise ValueError("non-available capture must not carry adapter capability evidence")
        return None, None
    if any(
        not _non_empty(value)
        for value in (
            adapter_identity,
            adapter_version,
            capability_evidence_id,
        )
    ):
        raise ValueError(
            "available capture requires adapter identity, version, and canonical "
            "capability evidence id"
        )
    matching = [
        record
        for record in capability_registry["records"]
        if record["evidenceId"] == capability_evidence_id
    ]
    if not matching:
        raise ValueError(
            "available capture requires admitted canonical capability evidence"
        )
    record = matching[0]
    if (
        record["adapterIdentity"] != adapter_identity.strip()
        or record["adapterVersion"] != adapter_version.strip()
        or record["hostIdentity"] != host_identity.strip()
        or record["hostVersion"] != host_version.strip()
    ):
        raise ValueError(
            "canonical capture capability evidence does not match host and adapter"
        )
    public_evidence = deepcopy(record)
    public_evidence["registrySha256"] = capability_registry["sha256"]
    return (
        {"identity": adapter_identity.strip(), "version": adapter_version.strip()},
        public_evidence,
    )


def build_preflight_packet(
    *,
    host_identity: str,
    host_version: str,
    requested_model: str,
    requested_reasoning_effort: str,
    loader_evidence_capture: str,
    loader_capture_adapter_identity: str | None = None,
    loader_capture_adapter_version: str | None = None,
    capture_capability_evidence_id: str | None = None,
    protocol_path: Path = PROTOCOL_PATH,
) -> dict[str, Any]:
    if loader_evidence_capture not in CAPTURES:
        raise ValueError("loader_evidence_capture must be available, unavailable, or unknown")
    if any(not _non_empty(value) for value in (host_identity, host_version, requested_model, requested_reasoning_effort)):
        raise ValueError("host/model/reasoning inputs must be non-empty strings")
    binding = load_protocol_handoff_binding(protocol_path)
    capability_registry = load_capture_capability_registry()
    adapter, capability_evidence = _capture_adapter_binding(
        loader_evidence_capture,
        host_identity,
        host_version,
        loader_capture_adapter_identity,
        loader_capture_adapter_version,
        capture_capability_evidence_id,
        capability_registry,
    )
    identity_templates = {
        "runId": "hnd-fresh-run-{ordinal:02d}",
        "producerHostRunId": "hnd-fresh-producer-host-run-{ordinal:02d}",
        "producerHostThreadId": "hnd-fresh-producer-host-thread-{ordinal:02d}",
        "producerTaskId": "hnd-fresh-producer-task-{ordinal:02d}",
        "receiverHostThreadId": "hnd-fresh-receiver-host-thread-{ordinal:02d}",
        "minimumIndependentOrdinals": [1, 2, 3],
    }
    public_packet = {
        "schema": 1,
        "id": "handoff-loader-fresh-public-packet",
        "viewId": VIEW_ID,
        "scenarioId": SCENARIO_ID,
        "targetHost": {
            "identity": host_identity.strip(), "version": host_version.strip(),
            "requestedModel": requested_model.strip(),
            "requestedReasoningEffort": requested_reasoning_effort.strip(),
        },
        "payloadBinding": {
            "identity": binding["identity"], "harnessTreeHashV1": binding["harnessTreeHashV1"],
            "fileManifestSha256": binding["fileManifestSha256"], "files": binding["files"],
            "protocolSha256": binding["protocolSha256"],
        },
        "identityTemplates": identity_templates,
        "loaderEvidenceCapture": loader_evidence_capture,
        "loaderCaptureAdapter": adapter,
        "captureCapabilityEvidence": capability_evidence,
        "formalAttemptGate": {
            "status": _status(loader_evidence_capture),
            "requiredProducerLoaderEvent": {
                "identity": binding["identity"], "fileManifestSha256": binding["fileManifestSha256"],
                "taskId": "must-equal-instantiated-producerTaskId", "evidenceSource": "host-loader-event",
            },
            "nonEvidence": ["filesystem presence", "startup-visible list", "agent self-report"],
        },
        "authorityBoundary": {
            "taskCreationAuthorizedByPacket": False, "temporaryArtifactWriteAuthorizedByPacket": False,
            "hostConfigurationMutationAuthorizedByPacket": False, "repositoryMutationAuthorizedByPacket": False,
        },
    }
    private_oracle = {
        "scenarioId": SCENARIO_ID,
        "viewId": VIEW_ID,
        "canonicalArmCEvaluator": "scripts/evaluate_skill_ablation_batch_01_protocol.py:_verify_live_context_arm_c",
        "protocolPath": binding["protocolPath"],
        "protocolSha256": binding["protocolSha256"],
        "captureCapabilityRegistryPath": capability_registry["path"],
        "captureCapabilityRegistrySha256": capability_registry["sha256"],
        "selectedPayload": {
            "identity": binding["identity"], "harnessTreeHashV1": binding["harnessTreeHashV1"],
            "files": binding["files"], "fileManifestSha256": binding["fileManifestSha256"],
        },
    }
    return {
        "schema": 1, "id": "handoff-loader-fresh-preflight", "status": _status(loader_evidence_capture),
        "publicPacket": public_packet, "packetSha256": canonical_sha256(public_packet),
        "privateOracle": private_oracle, "oracleSha256": canonical_sha256(private_oracle),
        "countsAsLoaderInvocationProof": False, "countsAsFreshSessionProof": False,
        "countsAsWeakAgentAcceptance": False, "countsAsCrossHostParity": False,
    }


def validate_packet_binding(packet: dict[str, Any]) -> list[str]:
    if not isinstance(packet, dict) or set(packet) != TOP_LEVEL:
        return ["fail-top-level-shape"]
    failures: list[str] = []
    public = packet.get("publicPacket")
    private = packet.get("privateOracle")
    expected_public = {"schema", "id", "viewId", "scenarioId", "targetHost", "payloadBinding", "identityTemplates", "loaderEvidenceCapture", "loaderCaptureAdapter", "captureCapabilityEvidence", "formalAttemptGate", "authorityBoundary"}
    if not isinstance(public, dict) or set(public) != expected_public or public.get("schema") != 1 or public.get("id") != "handoff-loader-fresh-public-packet" or public.get("viewId") != VIEW_ID or public.get("scenarioId") != SCENARIO_ID:
        failures.append("fail-public-packet-shape")
        return failures
    if packet.get("packetSha256") != canonical_sha256(public):
        failures.append("fail-public-packet-digest")
    target = public["targetHost"]
    if not isinstance(target, dict) or set(target) != {"identity", "version", "requestedModel", "requestedReasoningEffort"} or any(not _non_empty(value) for value in target.values()):
        failures.append("fail-target-host-shape")
    binding = public["payloadBinding"]
    expected_binding_keys = {"identity", "harnessTreeHashV1", "fileManifestSha256", "files", "protocolSha256"}
    if not isinstance(binding, dict) or set(binding) != expected_binding_keys or not _non_empty(binding.get("identity")) or not _sha256(binding.get("harnessTreeHashV1")) or not _sha256(binding.get("fileManifestSha256")) or not _sha256(binding.get("protocolSha256")) or not isinstance(binding.get("files"), dict) or not binding["files"] or canonical_sha256(binding["files"]) != binding["fileManifestSha256"]:
        failures.append("fail-payload-binding")
    templates = public["identityTemplates"]
    required_templates = {"runId", "producerHostRunId", "producerHostThreadId", "producerTaskId", "receiverHostThreadId", "minimumIndependentOrdinals"}
    if not isinstance(templates, dict) or set(templates) != required_templates or any(not _non_empty(templates.get(key)) for key in required_templates - {"minimumIndependentOrdinals"}) or templates.get("minimumIndependentOrdinals") != [1, 2, 3]:
        failures.append("fail-identity-templates-shape")
    capture = public["loaderEvidenceCapture"]
    expected_status = _status(capture) if capture in CAPTURES else None
    if capture not in CAPTURES or packet.get("status") != expected_status:
        failures.append("fail-preflight-status")
    adapter = public["loaderCaptureAdapter"]
    capability_evidence = public["captureCapabilityEvidence"]
    try:
        capability_registry = load_capture_capability_registry()
    except (OSError, ValueError, json.JSONDecodeError):
        capability_registry = None
        failures.append("fail-canonical-capture-registry-read")
    if capture == "available":
        expected_evidence_keys = CAPTURE_RECORD_FIELDS | {"registrySha256"}
        if (
            not isinstance(adapter, dict)
            or set(adapter) != {"identity", "version"}
            or any(not _non_empty(value) for value in adapter.values())
            or not isinstance(capability_evidence, dict)
            or set(capability_evidence) != expected_evidence_keys
        ):
            failures.append("fail-capture-adapter-binding")
        elif capability_registry is not None:
            evidence_id = capability_evidence.get("evidenceId")
            matching = [
                record
                for record in capability_registry["records"]
                if record["evidenceId"] == evidence_id
            ]
            canonical_evidence = (
                {
                    **matching[0],
                    "registrySha256": capability_registry["sha256"],
                }
                if len(matching) == 1
                else None
            )
            if (
                capability_evidence != canonical_evidence
                or adapter
                != {
                    "identity": capability_evidence.get("adapterIdentity"),
                    "version": capability_evidence.get("adapterVersion"),
                }
                or not isinstance(target, dict)
                or target.get("identity")
                != capability_evidence.get("hostIdentity")
                or target.get("version")
                != capability_evidence.get("hostVersion")
            ):
                failures.append("fail-canonical-capture-capability-binding")
    elif adapter is not None or capability_evidence is not None:
        failures.append("hard-fail-nonavailable-capture-promoted")
    gate = public["formalAttemptGate"]
    if not isinstance(gate, dict) or set(gate) != {"status", "requiredProducerLoaderEvent", "nonEvidence"}:
        failures.append("fail-formal-gate-shape")
    else:
        event = gate.get("requiredProducerLoaderEvent")
        if not isinstance(event, dict) or set(event) != {"identity", "fileManifestSha256", "taskId", "evidenceSource"} or event.get("identity") != binding.get("identity") or event.get("fileManifestSha256") != binding.get("fileManifestSha256") or event.get("taskId") != "must-equal-instantiated-producerTaskId" or event.get("evidenceSource") != "host-loader-event" or gate.get("status") != expected_status or gate.get("nonEvidence") != ["filesystem presence", "startup-visible list", "agent self-report"]:
            failures.append("fail-formal-gate-shape")
    authority = public["authorityBoundary"]
    if not isinstance(authority, dict) or set(authority) != {"taskCreationAuthorizedByPacket", "temporaryArtifactWriteAuthorizedByPacket", "hostConfigurationMutationAuthorizedByPacket", "repositoryMutationAuthorizedByPacket"} or any(value is not False for value in authority.values()):
        failures.append("fail-authority-boundary-shape")
    try:
        canonical_binding = load_protocol_handoff_binding()
    except (OSError, ValueError, json.JSONDecodeError):
        canonical_binding = None
        failures.append("fail-canonical-protocol-read")
    if canonical_binding is not None and binding != {
        "identity": canonical_binding["identity"],
        "harnessTreeHashV1": canonical_binding["harnessTreeHashV1"],
        "fileManifestSha256": canonical_binding["fileManifestSha256"],
        "files": canonical_binding["files"],
        "protocolSha256": canonical_binding["protocolSha256"],
    }:
        failures.append("fail-canonical-payload-binding")
    expected_private_keys = {"scenarioId", "viewId", "canonicalArmCEvaluator", "protocolPath", "protocolSha256", "captureCapabilityRegistryPath", "captureCapabilityRegistrySha256", "selectedPayload"}
    if not isinstance(private, dict) or set(private) != expected_private_keys or private.get("scenarioId") != SCENARIO_ID or private.get("viewId") != VIEW_ID or private.get("canonicalArmCEvaluator") != "scripts/evaluate_skill_ablation_batch_01_protocol.py:_verify_live_context_arm_c" or canonical_binding is None or capability_registry is None or private.get("protocolPath") != canonical_binding["protocolPath"] or private.get("protocolSha256") != canonical_binding["protocolSha256"] or private.get("captureCapabilityRegistryPath") != capability_registry["path"] or private.get("captureCapabilityRegistrySha256") != capability_registry["sha256"] or private.get("selectedPayload") != {"identity": canonical_binding["identity"], "harnessTreeHashV1": canonical_binding["harnessTreeHashV1"], "files": canonical_binding["files"], "fileManifestSha256": canonical_binding["fileManifestSha256"]} or packet.get("oracleSha256") != canonical_sha256(private):
        failures.append("fail-private-oracle-binding")
    elif "privateOracle" in public or json.dumps(private, sort_keys=True) in json.dumps(public, sort_keys=True):
        failures.append("fail-private-oracle-exposed")
    if capture != "available" and packet.get("status") != "blocked-missing-handoff-loader-observability":
        failures.append("hard-fail-nonavailable-capture-promoted")
    if any(packet.get(key) is not False for key in ("countsAsLoaderInvocationProof", "countsAsFreshSessionProof", "countsAsWeakAgentAcceptance", "countsAsCrossHostParity")):
        failures.append("hard-fail-preflight-count-promotion")
    return list(dict.fromkeys(failures))


def validate_producer_loader_event(packet: dict[str, Any], *, producer_task_id: str, loader_event: dict[str, Any]) -> list[str]:
    failures = validate_packet_binding(packet)
    public = packet.get("publicPacket")
    if not isinstance(public, dict):
        return failures
    if public.get("loaderEvidenceCapture") != "available":
        return failures + ["blocked-missing-handoff-loader-observability"]
    if not _non_empty(producer_task_id):
        return failures + ["fail-producer-task-id"]
    if not isinstance(loader_event, dict) or set(loader_event) != {"identity", "fileManifestSha256", "taskId", "evidenceSource"}:
        return failures + ["fail-loader-event-shape"]
    binding = public["payloadBinding"]
    if loader_event.get("identity") != binding["identity"]:
        failures.append("fail-loader-event-identity")
    if loader_event.get("fileManifestSha256") != binding["fileManifestSha256"]:
        failures.append("fail-loader-event-manifest")
    if loader_event.get("taskId") != producer_task_id:
        failures.append("fail-loader-event-task-binding")
    if loader_event.get("evidenceSource") != "host-loader-event":
        failures.append("fail-loader-event-source")
    return failures


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", required=True)
    parser.add_argument("--host-version", required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--reasoning", required=True)
    parser.add_argument("--loader-evidence-capture", choices=sorted(CAPTURES), required=True)
    parser.add_argument("--loader-capture-adapter-identity")
    parser.add_argument("--loader-capture-adapter-version")
    parser.add_argument("--capture-capability-evidence-id")
    args = parser.parse_args()
    packet = build_preflight_packet(host_identity=args.host, host_version=args.host_version, requested_model=args.model, requested_reasoning_effort=args.reasoning, loader_evidence_capture=args.loader_evidence_capture, loader_capture_adapter_identity=args.loader_capture_adapter_identity, loader_capture_adapter_version=args.loader_capture_adapter_version, capture_capability_evidence_id=args.capture_capability_evidence_id)
    print(json.dumps({key: value for key, value in packet.items() if key != "privateOracle"}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
