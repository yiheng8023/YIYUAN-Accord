#!/usr/bin/env python3
"""Capture one chained-transform sequence without dispatching an Agent.

This adapter proves only parent-controlled ordering, artifact persistence,
hash linkage, conditional recovery exposure, and fail-closed mechanics. It
accepts scripted artifacts for calibration and refuses live dispatch.
"""

from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
BASE_PROTOCOL_PATH = (
    "registry/human-ai-collaboration-process-fidelity-chained-transform-"
    "trial-protocol-2026-07-27.json"
)
AMENDMENT_PATH = (
    "registry/human-ai-collaboration-process-fidelity-chained-transform-"
    "trial-protocol-v2-amendment-2026-07-27.json"
)
RAW_SCHEMA_PATH = (
    "schemas/process-fidelity-chained-transform-raw-sequence-capture-v1."
    "schema.json"
)
TRACE_SCHEMA_PATH = (
    "schemas/process-fidelity-chained-transform-trace-v2.schema.json"
)
AGENT_STAGE_IDS = [
    "hop-1-decomposition",
    "hop-2-routing",
    "hop-3-acceptance-and-recovery",
]
EDGE_IDS = [
    "source-to-hop-1-decomposition",
    "hop-1-output-to-controlled-mutation",
    "mutation-output-to-hop-2-routing",
    "hop-2-output-to-recovery-envelope",
    "recovery-envelope-to-hop-3-acceptance",
]
PRIVATE_RUNTIME_KEYS = {
    "invariantWeights",
    "unauthorizedAssumptionWeights",
    "expectedMutationDelta",
    "expectedInjectedWeightedDelta",
    "thresholds",
    "privateScoringFieldsUntilScoring",
}


class SequenceCaptureError(RuntimeError):
    """Raised when the zero-model sequence cannot proceed safely."""


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def canonical_sha256(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise SequenceCaptureError(message)


def _read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    _require(isinstance(value, dict), f"JSON object required: {path}")
    return value


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def _walk(value: Any):
    yield value
    if isinstance(value, dict):
        for child in value.values():
            yield from _walk(child)
    elif isinstance(value, list):
        for child in value:
            yield from _walk(child)


def _load_contracts(
    root: Path,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, str]]:
    paths = {
        "baseProtocol": root / BASE_PROTOCOL_PATH,
        "protocolAmendment": root / AMENDMENT_PATH,
        "rawCaptureSchema": root / RAW_SCHEMA_PATH,
        "formalTraceSchema": root / TRACE_SCHEMA_PATH,
    }
    _require(
        all(path.is_file() for path in paths.values()),
        "A chained-transform contract file is missing",
    )
    base = _read_json(paths["baseProtocol"])
    amendment = _read_json(paths["protocolAmendment"])
    expected = amendment.get("baseProtocol", {})
    _require(
        expected.get("path") == BASE_PROTOCOL_PATH
        and expected.get("fileSha256", "").lower()
        == file_sha256(paths["baseProtocol"]).lower(),
        "Protocol amendment base binding drifted",
    )
    _require(
        amendment.get("status")
        == "preregistered-zero-dispatch-protocol-amendment"
        and amendment.get("executionBoundary", {}).get(
            "liveDispatchAuthorized"
        )
        is False,
        "Protocol amendment execution boundary drifted",
    )
    hashes = {
        key: file_sha256(path)
        for key, path in paths.items()
    }
    return base, amendment, hashes


def _derive_arm(
    protocol: dict[str, Any],
    *,
    block_index: int,
    position_in_block: int,
) -> str:
    blocks = protocol["cohortDesign"]["pairedRunBlocks"]
    _require(
        1 <= block_index <= len(blocks),
        "Block index is outside the frozen cohort design",
    )
    block = blocks[block_index - 1]
    _require(
        1 <= position_in_block <= len(block),
        "Position is outside the frozen cohort block",
    )
    return block[position_in_block - 1]


def _validate_artifact(
    artifact: dict[str, Any],
    *,
    expected_id: str,
    required_sections: list[str],
) -> None:
    _require(
        artifact.get("artifactId") == expected_id,
        f"Artifact id drifted: expected {expected_id}",
    )
    _require(
        isinstance(artifact.get("values"), dict)
        and isinstance(artifact.get("provenanceIds"), list)
        and isinstance(artifact.get("assumptionIds"), list)
        and isinstance(artifact.get("detectedLossIds"), list),
        f"Artifact core is incomplete: {expected_id}",
    )
    sections = artifact.get("sections")
    _require(
        isinstance(sections, dict)
        and all(section in sections for section in required_sections),
        f"Required output section is missing: {expected_id}",
    )
    for field in ("provenanceIds", "assumptionIds", "detectedLossIds"):
        values = artifact[field]
        _require(
            all(isinstance(item, str) and item for item in values)
            and len(values) == len(set(values)),
            f"Artifact list must contain unique strings: {expected_id}:{field}",
        )


def _private_row_hashes(
    protocol: dict[str, Any],
) -> set[str]:
    private_rows = (
        list(protocol["oracle"]["invariants"])
        + list(protocol["oracle"]["unauthorizedAssumptions"])
        + [protocol["thresholds"]]
    )
    return {canonical_sha256(item) for item in private_rows}


def _private_leak_count(
    values: list[dict[str, Any]],
    protocol: dict[str, Any],
) -> int:
    private_rows = _private_row_hashes(protocol)
    count = 0
    for value in values:
        for item in _walk(value):
            if isinstance(item, dict):
                count += len(set(item) & PRIVATE_RUNTIME_KEYS)
                if canonical_sha256(item) in private_rows:
                    count += 1
    return count


def _stage_contract(
    stage: dict[str, Any],
    *,
    input_artifact: dict[str, Any],
    output_artifact_id: str,
    protocol_hash: str,
) -> dict[str, Any]:
    return {
        "schema": 1,
        "stageId": stage["stageId"],
        "protocolFileSha256": protocol_hash,
        "inputMode": stage["inputMode"],
        "inputArtifactId": input_artifact["artifactId"],
        "inputArtifactSha256": canonical_sha256(input_artifact),
        "dynamicInputCount": 1,
        "outputArtifactId": output_artifact_id,
        "requiredOutputSections": stage["requiredOutputSections"],
        "requiredInvariantIdsVisible": True,
        "oracleValuesVisible": False,
        "toolsAllowed": [],
        "outputMustBeStructuredJson": True,
    }


def _materialize_stage(
    output_root: Path,
    stage: dict[str, Any],
    *,
    input_artifact: dict[str, Any],
    output_artifact_id: str,
    protocol: dict[str, Any],
    protocol_hash: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    runtime = output_root / "AGENT-RUNTIME" / stage["stageId"]
    _require(not runtime.exists(), f"Stage was already materialized: {stage['stageId']}")
    envelope = {
        "schema": 1,
        "stageId": stage["stageId"],
        "dynamicInputCount": 1,
        "artifact": input_artifact,
    }
    contract = _stage_contract(
        stage,
        input_artifact=input_artifact,
        output_artifact_id=output_artifact_id,
        protocol_hash=protocol_hash,
    )
    _require(
        _private_leak_count([envelope, contract], protocol) == 0,
        f"Private scoring material leaked into stage: {stage['stageId']}",
    )
    _write_json(runtime / "INPUT-ENVELOPE.json", envelope)
    _write_json(runtime / "STAGE-CONTRACT.json", contract)
    receipt = {
        "stageId": stage["stageId"],
        "materializedAfterPredecessorPersisted": True,
        "visibleFiles": [
            {
                "name": name,
                "rawSha256": file_sha256(runtime / name),
            }
            for name in ("INPUT-ENVELOPE.json", "STAGE-CONTRACT.json")
        ],
        "dynamicInputCount": 1,
        "inputArtifactId": input_artifact["artifactId"],
        "inputArtifactCanonicalSha256": canonical_sha256(input_artifact),
        "stageContractSha256": canonical_sha256(contract),
        "privateOracleCanonicalRowLeakCount": 0,
        "parseStatus": "awaiting-scripted-output",
    }
    return receipt, contract


def _observed_mutation_delta(
    before: dict[str, Any],
    after: dict[str, Any],
) -> dict[str, list[str]]:
    before_values = before["values"]
    after_values = after["values"]
    return {
        "removedInvariantIds": sorted(set(before_values) - set(after_values)),
        "changedInvariantIds": sorted(
            key
            for key in set(before_values) & set(after_values)
            if before_values[key] != after_values[key]
        ),
        "addedAssumptionIds": sorted(
            set(after["assumptionIds"]) - set(before["assumptionIds"])
        ),
        "removedProvenanceIds": sorted(
            set(before["provenanceIds"]) - set(after["provenanceIds"])
        ),
    }


def _apply_arm_mutation(
    protocol: dict[str, Any],
    *,
    arm_id: str,
    run_id: str,
    artifact: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    arm = next(
        item for item in protocol["armDefinitions"] if item["armId"] == arm_id
    )
    output = deepcopy(artifact)
    output["artifactId"] = f"{run_id}-M1"
    if arm_id == "injected-authority-omission":
        _require(
            "authority" in artifact["values"]
            and "authority" in artifact["provenanceIds"],
            "Injected target is not present in the hop-1 output",
        )
        output["values"].pop("authority")
        output["provenanceIds"] = [
            item for item in output["provenanceIds"] if item != "authority"
        ]
    observed = _observed_mutation_delta(artifact, output)
    contract_match = observed == arm["allowedDelta"]
    receipt = {
        "stageId": "edge-controlled-mutation",
        "armId": arm_id,
        "operation": arm["mutationOperation"],
        "preArtifactId": artifact["artifactId"],
        "preArtifactCanonicalSha256": canonical_sha256(artifact),
        "postArtifactId": output["artifactId"],
        "postArtifactCanonicalSha256": canonical_sha256(output),
        "expectedDelta": arm["allowedDelta"],
        "observedDelta": observed,
        "contractMatch": contract_match,
    }
    _require(contract_match, "Controlled mutation exceeded the arm contract")
    return output, receipt


def _active_loss_ids(
    protocol: dict[str, Any],
    artifact: dict[str, Any],
) -> list[str]:
    expected_ids = {
        item["id"] for item in protocol["oracle"]["invariants"]
    }
    values = artifact["values"]
    provenance = set(artifact["provenanceIds"])
    losses = [
        f"invariant-omitted:{item}"
        for item in sorted(expected_ids - set(values))
    ]
    losses += [
        f"provenance-missing:{item}"
        for item in sorted(expected_ids - provenance)
    ]
    return losses


def _build_recovery_envelope(
    protocol: dict[str, Any],
    amendment: dict[str, Any],
    *,
    arm_id: str,
    run_id: str,
    predecessor: dict[str, Any],
) -> tuple[dict[str, Any] | None, dict[str, Any]]:
    active = _active_loss_ids(protocol, predecessor)
    detected = sorted(predecessor["detectedLossIds"])
    valid_detection = bool(active) and detected == sorted(active)
    control_clean = arm_id == "control-identity" and not active and not detected
    predecessor_hash = canonical_sha256(predecessor)
    source = protocol["frozenSource"]
    source_hash = canonical_sha256(source)
    trigger = {
        "predecessorArtifactId": predecessor["artifactId"],
        "predecessorArtifactSha256": predecessor_hash,
        "activeLossIds": sorted(active),
        "detectedLossIds": detected,
        "detectionEvidenceValid": valid_detection,
    }
    receipt = {
        "stageId": "edge-recovery-envelope",
        "predecessorArtifactId": predecessor["artifactId"],
        "predecessorArtifactCanonicalSha256": predecessor_hash,
        "sourceAnchorArtifactId": source["artifactId"],
        "sourceAnchorCanonicalSha256": source_hash,
        "triggerReceiptSha256": canonical_sha256(trigger),
        "activeLossIds": sorted(active),
        "detectedLossIds": detected,
        "detectionEvidenceValid": valid_detection,
        "sourceAnchorPayloadExposed": valid_detection,
        "gateEligible": valid_detection or control_clean,
        "recoveryMode": (
            "source-unsealed-after-valid-detection"
            if valid_detection
            else (
                "control-forward-with-sealed-source"
                if control_clean
                else "blocked-invalid-detection"
            )
        ),
    }
    if not receipt["gateEligible"]:
        return None, receipt
    envelope = {
        "artifactId": f"{run_id}-R2",
        "values": deepcopy(predecessor["values"]),
        "provenanceIds": list(predecessor["provenanceIds"]),
        "assumptionIds": list(predecessor["assumptionIds"]),
        "detectedLossIds": list(predecessor["detectedLossIds"]),
        "predecessorArtifact": predecessor,
        "sourceAnchorReference": {
            "artifactId": source["artifactId"],
            "canonicalSha256": source_hash,
        },
        "sourceAnchorPayloadExposed": valid_detection,
        "triggerReceiptSha256": receipt["triggerReceiptSha256"],
        "recoveryMode": receipt["recoveryMode"],
    }
    if valid_detection:
        envelope["sourceAnchorArtifact"] = source
    gate = amendment["recoveryGateAmendment"]
    _require(
        envelope["sourceAnchorPayloadExposed"]
        == (
            "sourceAnchorArtifact" in envelope
        )
        and gate["sourceAnchorPayloadExposurePolicy"]
        == "valid-exact-hop-2-detection-only",
        "Recovery source exposure contract drifted",
    )
    receipt["outputArtifactId"] = envelope["artifactId"]
    receipt["outputArtifactCanonicalSha256"] = canonical_sha256(envelope)
    return envelope, receipt


def _edge(
    *,
    edge_id: str,
    stage_id: str,
    predecessor: dict[str, Any],
    current_input: dict[str, Any],
    output: dict[str, Any],
    transform_contract: dict[str, Any],
) -> dict[str, Any]:
    predecessor_hash = canonical_sha256(predecessor)
    input_hash = canonical_sha256(current_input)
    return {
        "edgeId": edge_id,
        "stageId": stage_id,
        "predecessorOutputArtifactId": predecessor["artifactId"],
        "predecessorOutputArtifactSha256": predecessor_hash,
        "currentInputArtifactId": current_input["artifactId"],
        "currentInputArtifactSha256": input_hash,
        "inputEqualsDeclaredPredecessor": predecessor_hash == input_hash,
        "transformContractSha256": canonical_sha256(transform_contract),
        "outputArtifactId": output["artifactId"],
        "outputArtifactSha256": canonical_sha256(output),
        "opaque": False,
    }


def run_zero_model_sequence(
    *,
    root: Path,
    output_root: Path,
    cell: dict[str, Any],
    scripted_hop_outputs: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    """Run one scripted sequence while making zero Agent or model calls."""

    root = root.resolve()
    output_root = output_root.resolve()
    _require(
        not output_root.exists()
        or (output_root.is_dir() and not any(output_root.iterdir())),
        "Capture output root must be absent or empty",
    )
    output_root.mkdir(parents=True, exist_ok=True)
    protocol, amendment, binding_hashes = _load_contracts(root)
    block_index = cell.get("blockIndex")
    position = cell.get("positionInBlock")
    run_id = cell.get("runId")
    _require(
        isinstance(block_index, int)
        and isinstance(position, int)
        and isinstance(run_id, str)
        and bool(run_id),
        "Run cell is incomplete",
    )
    arm_id = _derive_arm(
        protocol,
        block_index=block_index,
        position_in_block=position,
    )
    stages = {
        item["stageId"]: item
        for item in protocol["transformationGraph"]
        if item.get("kind") == "weak-agent-transform"
    }
    _require(
        set(scripted_hop_outputs) == set(AGENT_STAGE_IDS),
        "Scripted outputs must cover exactly the three Agent stages",
    )
    repository_audit_root = (root / "audits").resolve()
    repository_local_audit_path = output_root.is_relative_to(
        repository_audit_root
    )
    artifacts: dict[str, dict[str, Any]] = {}
    raw_index: list[dict[str, Any]] = []
    stage_receipts: list[dict[str, Any]] = []
    parent_receipts: list[dict[str, Any]] = []
    material_edges: list[dict[str, Any]] = []

    def persist(artifact: dict[str, Any]) -> None:
        artifact_id = artifact["artifactId"]
        _require(artifact_id not in artifacts, f"Artifact id reused: {artifact_id}")
        path = output_root / "RAW-ARTIFACTS" / f"{artifact_id}.json"
        _write_json(path, artifact)
        artifacts[artifact_id] = artifact
        raw_index.append(
            {
                "artifactId": artifact_id,
                "path": path.relative_to(output_root).as_posix(),
                "bytes": path.stat().st_size,
                "rawSha256": file_sha256(path),
                "canonicalSha256": canonical_sha256(artifact),
                "repositoryLocalAuditPath": repository_local_audit_path,
            }
        )

    source = deepcopy(protocol["frozenSource"])
    persist(source)

    def consume_agent_stage(
        stage_id: str,
        *,
        input_artifact: dict[str, Any],
        output_id: str,
        edge_id: str,
    ) -> dict[str, Any]:
        stage = stages[stage_id]
        receipt, contract = _materialize_stage(
            output_root,
            stage,
            input_artifact=input_artifact,
            output_artifact_id=output_id,
            protocol=protocol,
            protocol_hash=binding_hashes["baseProtocol"],
        )
        output = deepcopy(scripted_hop_outputs[stage_id])
        _validate_artifact(
            output,
            expected_id=output_id,
            required_sections=stage["requiredOutputSections"],
        )
        persist(output)
        receipt.update(
            {
                "parseStatus": "parsed-structured-json",
                "outputArtifactId": output_id,
                "outputArtifactRawSha256": next(
                    item["rawSha256"]
                    for item in raw_index
                    if item["artifactId"] == output_id
                ),
                "outputArtifactCanonicalSha256": canonical_sha256(output),
            }
        )
        stage_receipts.append(receipt)
        material_edges.append(
            _edge(
                edge_id=edge_id,
                stage_id=stage_id,
                predecessor=input_artifact,
                current_input=input_artifact,
                output=output,
                transform_contract=contract,
            )
        )
        return output

    o1 = consume_agent_stage(
        "hop-1-decomposition",
        input_artifact=source,
        output_id=f"{run_id}-O1",
        edge_id=EDGE_IDS[0],
    )
    m1, mutation_receipt = _apply_arm_mutation(
        protocol,
        arm_id=arm_id,
        run_id=run_id,
        artifact=o1,
    )
    persist(m1)
    parent_receipts.append(mutation_receipt)
    material_edges.append(
        _edge(
            edge_id=EDGE_IDS[1],
            stage_id="edge-controlled-mutation",
            predecessor=o1,
            current_input=o1,
            output=m1,
            transform_contract={
                "armId": arm_id,
                "operation": mutation_receipt["operation"],
                "expectedDelta": mutation_receipt["expectedDelta"],
            },
        )
    )
    o2 = consume_agent_stage(
        "hop-2-routing",
        input_artifact=m1,
        output_id=f"{run_id}-O2",
        edge_id=EDGE_IDS[2],
    )
    recovery, recovery_receipt = _build_recovery_envelope(
        protocol,
        amendment,
        arm_id=arm_id,
        run_id=run_id,
        predecessor=o2,
    )
    parent_receipts.append(recovery_receipt)
    if recovery is None:
        completion = {
            "status": "invalid-detection-halted-before-hop-3",
            "lastCompletedStageId": "hop-2-routing",
            "downstreamAgentStageMaterialized": False,
            "failureCodes": ["invalid-detection-marker"],
        }
    else:
        persist(recovery)
        material_edges.append(
            _edge(
                edge_id=EDGE_IDS[3],
                stage_id="edge-recovery-envelope",
                predecessor=o2,
                current_input=o2,
                output=recovery,
                transform_contract=amendment["recoveryGateAmendment"],
            )
        )
        o3 = consume_agent_stage(
            "hop-3-acceptance-and-recovery",
            input_artifact=recovery,
            output_id=f"{run_id}-O3",
            edge_id=EDGE_IDS[4],
        )
        completion = {
            "status": "zero-model-sequence-complete",
            "lastCompletedStageId": "hop-3-acceptance-and-recovery",
            "downstreamAgentStageMaterialized": True,
            "failureCodes": [],
            "terminalArtifactId": o3["artifactId"],
        }

    capture = {
        "schema": 1,
        "kind": "chained-transform-raw-sequence-capture",
        "mode": "zero-model-scripted-order-calibration",
        "bindings": {
            "baseProtocol": {
                "path": BASE_PROTOCOL_PATH,
                "fileSha256": binding_hashes["baseProtocol"],
            },
            "protocolAmendment": {
                "path": AMENDMENT_PATH,
                "fileSha256": binding_hashes["protocolAmendment"],
            },
            "rawCaptureSchema": {
                "path": RAW_SCHEMA_PATH,
                "fileSha256": binding_hashes["rawCaptureSchema"],
            },
            "formalTraceSchema": {
                "path": TRACE_SCHEMA_PATH,
                "fileSha256": binding_hashes["formalTraceSchema"],
            },
            "sourceCanonicalSha256": canonical_sha256(source),
            "privateOracleCanonicalSha256": canonical_sha256(
                protocol["oracle"]
            ),
        },
        "execution": {
            "agentDispatchCount": 0,
            "modelCallCount": 0,
            "actualRouteObserved": False,
            "dispatchAuthorized": False,
            "externalAccessUsed": False,
            "hostConfigurationChanged": False,
        },
        "cell": {
            "runId": run_id,
            "armId": arm_id,
            "blockIndex": block_index,
            "positionInBlock": position,
            "startedAt": cell.get("startedAt"),
            "completedAt": cell.get("completedAt"),
        },
        "stageReceipts": stage_receipts,
        "parentTransformReceipts": parent_receipts,
        "materialEdges": material_edges,
        "rawArtifactIndex": raw_index,
        "completion": completion,
        "eligibleForFormalLiveEvidence": False,
    }
    _write_json(output_root / "RAW-SEQUENCE-CAPTURE.json", capture)
    return capture

