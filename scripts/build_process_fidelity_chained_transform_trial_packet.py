#!/usr/bin/env python3
"""Build and validate a zero-dispatch first-hop chained-transform packet."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
PROTOCOL_PATH = (
    "registry/human-ai-collaboration-process-fidelity-chained-transform-"
    "trial-protocol-2026-07-27.json"
)
TRACE_SCHEMA_PATH = (
    "schemas/process-fidelity-chained-transform-trace-v1.schema.json"
)
RUN_ID = "preflight-control-b1-p1"
ARM_ID = "control-identity"
EXPECTED_ROOT_ENTRIES = {
    "MANIFEST.json",
    "PARENT-EVIDENCE",
    "AGENT-RUNTIME",
}
EXPECTED_PARENT_FILES = {
    "PROTOCOL.json",
    "PRIVATE-SCORING-ORACLE.json",
    "RUN-PLAN.json",
    "DEFERRED-STAGE-TEMPLATES.json",
}
EXPECTED_RUNTIME_FILES = {
    "INPUT-ENVELOPE.json",
    "STAGE-CONTRACT.json",
}
PRIVATE_RUNTIME_KEYS = {
    "invariantWeights",
    "unauthorizedAssumptionWeights",
    "expectedMutationDelta",
    "thresholds",
    "expectedInjectedWeightedDelta",
}


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


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


def _write_json(path: Path, value: Any) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def _private_oracle(protocol: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema": 1,
        "protocolId": protocol["id"],
        "sourceAnchorId": protocol["oracle"]["lastTrustedRecoveryAnchor"],
        "invariantWeights": {
            item["id"]: item["weight"]
            for item in protocol["oracle"]["invariants"]
        },
        "unauthorizedAssumptionWeights": {
            item["id"]: item["weight"]
            for item in protocol["oracle"]["unauthorizedAssumptions"]
        },
        "expectedMutationDelta": {
            item["armId"]: {
                "allowedDelta": item["allowedDelta"],
                "expectedInjectedWeightedDelta": item[
                    "expectedInjectedWeightedDelta"
                ],
            }
            for item in protocol["armDefinitions"]
        },
        "thresholds": protocol["thresholds"],
    }


def _run_plan(protocol: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema": 1,
        "protocolId": protocol["id"],
        "runId": RUN_ID,
        "armId": ARM_ID,
        "blockIndex": 1,
        "positionInBlock": 1,
        "intendedRoute": protocol["cohortDesign"]["primaryAgentRoute"],
        "actualRouteObserved": False,
        "dispatchAuthorized": False,
        "agentDispatchCount": 0,
        "modelCallCount": 0,
        "materializedAgentStages": ["hop-1-decomposition"],
        "deferredAgentStages": [
            "hop-2-routing",
            "hop-3-acceptance-and-recovery",
        ],
        "rawEvidenceDestinationBound": False,
    }


def _input_envelope(protocol: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema": 1,
        "runId": RUN_ID,
        "armId": ARM_ID,
        "stageId": "hop-1-decomposition",
        "dynamicInputCount": 1,
        "artifact": protocol["frozenSource"],
    }


def _stage_contract(
    protocol: dict[str, Any],
    protocol_file_sha256: str,
) -> dict[str, Any]:
    stage = protocol["transformationGraph"][0]
    return {
        "schema": 1,
        "protocolId": protocol["id"],
        "protocolFileSha256": protocol_file_sha256,
        "runId": RUN_ID,
        "armId": ARM_ID,
        "stageId": stage["stageId"],
        "inputMode": stage["inputMode"],
        "allowedDynamicInputCount": 1,
        "allowedInputArtifactIds": stage["allowedInputArtifactIds"],
        "requiredInvariantIds": [
            item["id"] for item in protocol["oracle"]["invariants"]
        ],
        "requiredOutputSections": stage["requiredOutputSections"],
        "toolsAllowed": [],
        "sharedConversationStateAllowed": False,
        "oracleValuesVisibleOutsideInputArtifact": False,
        "outputMustBeStructuredJson": True,
    }


def build_packet(
    output_root: Path,
    *,
    root: Path = ROOT,
) -> dict[str, Any]:
    output_root = output_root.resolve()
    if output_root.exists():
        _require(
            output_root.is_dir() and not any(output_root.iterdir()),
            "Packet output root must be absent or empty",
        )
    else:
        output_root.mkdir(parents=True)

    protocol_path = root / PROTOCOL_PATH
    schema_path = root / TRACE_SCHEMA_PATH
    protocol = json.loads(protocol_path.read_text(encoding="utf-8"))
    protocol_hash = file_sha256(protocol_path)
    schema_hash = file_sha256(schema_path)

    parent = output_root / "PARENT-EVIDENCE"
    runtime = output_root / "AGENT-RUNTIME" / "hop-1-decomposition"
    parent.mkdir()
    runtime.mkdir(parents=True)

    _write_json(parent / "PROTOCOL.json", protocol)
    _write_json(parent / "PRIVATE-SCORING-ORACLE.json", _private_oracle(protocol))
    _write_json(parent / "RUN-PLAN.json", _run_plan(protocol))
    _write_json(
        parent / "DEFERRED-STAGE-TEMPLATES.json",
        {
            "schema": 1,
            "protocolId": protocol["id"],
            "deferredStages": protocol["transformationGraph"][1:],
            "materializeBeforeDispatchOnly": True,
        },
    )
    _write_json(runtime / "INPUT-ENVELOPE.json", _input_envelope(protocol))
    _write_json(
        runtime / "STAGE-CONTRACT.json",
        _stage_contract(protocol, protocol_hash),
    )

    files = []
    for path in sorted(
        (
            item
            for item in output_root.rglob("*")
            if item.is_file()
        ),
        key=lambda item: item.relative_to(output_root).as_posix(),
    ):
        files.append(
            {
                "path": path.relative_to(output_root).as_posix(),
                "sha256": file_sha256(path),
            }
        )
    manifest = {
        "schema": 1,
        "id": "process-fidelity-chained-transform-zero-dispatch-packet",
        "mode": "zero-dispatch-hop-1-only",
        "protocol": {
            "path": PROTOCOL_PATH,
            "fileSha256": protocol_hash,
        },
        "traceSchema": {
            "path": TRACE_SCHEMA_PATH,
            "fileSha256": schema_hash,
        },
        "runId": RUN_ID,
        "armId": ARM_ID,
        "parentEvidenceRoot": "PARENT-EVIDENCE",
        "agentRuntimeRoot": "AGENT-RUNTIME/hop-1-decomposition",
        "files": files,
        "agentDispatchCount": 0,
        "modelCallCount": 0,
        "actualRouteObserved": False,
        "dispatchAuthorized": False,
        "rawEvidenceDestinationBound": False,
    }
    _write_json(output_root / "MANIFEST.json", manifest)
    return manifest


def _walk_keys(value: Any) -> set[str]:
    keys: set[str] = set()
    if isinstance(value, dict):
        for key, child in value.items():
            keys.add(key)
            keys.update(_walk_keys(child))
    elif isinstance(value, list):
        for child in value:
            keys.update(_walk_keys(child))
    return keys


def validate_packet(
    output_root: Path,
    *,
    root: Path = ROOT,
) -> dict[str, Any]:
    output_root = output_root.resolve()
    _require(output_root.is_dir(), "Packet root is missing")
    _require(
        {item.name for item in output_root.iterdir()}
        == EXPECTED_ROOT_ENTRIES,
        "Packet root exposure drifted",
    )
    manifest = json.loads(
        (output_root / "MANIFEST.json").read_text(encoding="utf-8")
    )
    _require(
        manifest.get("schema") == 1
        and manifest.get("id")
        == "process-fidelity-chained-transform-zero-dispatch-packet"
        and manifest.get("mode") == "zero-dispatch-hop-1-only"
        and manifest.get("runId") == RUN_ID
        and manifest.get("armId") == ARM_ID
        and manifest.get("agentDispatchCount") == 0
        and manifest.get("modelCallCount") == 0
        and manifest.get("actualRouteObserved") is False
        and manifest.get("dispatchAuthorized") is False
        and manifest.get("rawEvidenceDestinationBound") is False,
        "Packet zero-dispatch manifest drifted",
    )
    protocol_path = root / PROTOCOL_PATH
    schema_path = root / TRACE_SCHEMA_PATH
    _require(
        manifest.get("protocol")
        == {
            "path": PROTOCOL_PATH,
            "fileSha256": file_sha256(protocol_path),
        }
        and manifest.get("traceSchema")
        == {
            "path": TRACE_SCHEMA_PATH,
            "fileSha256": file_sha256(schema_path),
        },
        "Packet source binding drifted",
    )

    parent = output_root / manifest["parentEvidenceRoot"]
    runtime = output_root / manifest["agentRuntimeRoot"]
    _require(
        parent.is_dir()
        and {item.name for item in parent.iterdir()}
        == EXPECTED_PARENT_FILES,
        "Packet parent evidence root drifted",
    )
    _require(
        runtime.is_dir()
        and {item.name for item in runtime.iterdir()}
        == EXPECTED_RUNTIME_FILES,
        "Packet Agent runtime root drifted",
    )
    _require(
        not (output_root / "AGENT-RUNTIME" / "hop-2-routing").exists()
        and not (
            output_root
            / "AGENT-RUNTIME"
            / "hop-3-acceptance-and-recovery"
        ).exists(),
        "Packet materialized a deferred Agent stage",
    )

    expected_manifest_paths = {
        item.relative_to(output_root).as_posix()
        for item in output_root.rglob("*")
        if item.is_file() and item.name != "MANIFEST.json"
    }
    indexed_files = {
        item.get("path"): item.get("sha256")
        for item in manifest.get("files", [])
        if isinstance(item, dict)
    }
    _require(
        set(indexed_files) == expected_manifest_paths
        and all(
            file_sha256(output_root / path).lower() == digest.lower()
            for path, digest in indexed_files.items()
        ),
        "Packet manifest file hash drifted",
    )

    protocol = json.loads(protocol_path.read_text(encoding="utf-8"))
    parent_protocol = json.loads(
        (parent / "PROTOCOL.json").read_text(encoding="utf-8")
    )
    private_oracle = json.loads(
        (parent / "PRIVATE-SCORING-ORACLE.json").read_text(encoding="utf-8")
    )
    run_plan = json.loads(
        (parent / "RUN-PLAN.json").read_text(encoding="utf-8")
    )
    input_envelope = json.loads(
        (runtime / "INPUT-ENVELOPE.json").read_text(encoding="utf-8")
    )
    stage_contract = json.loads(
        (runtime / "STAGE-CONTRACT.json").read_text(encoding="utf-8")
    )
    _require(
        canonical_sha256(parent_protocol) == canonical_sha256(protocol),
        "Packet parent protocol is not canonical-equivalent",
    )
    _require(
        set(private_oracle)
        >= {
            "invariantWeights",
            "unauthorizedAssumptionWeights",
            "expectedMutationDelta",
            "thresholds",
        },
        "Packet private scoring oracle is incomplete",
    )
    _require(
        run_plan.get("actualRouteObserved") is False
        and run_plan.get("dispatchAuthorized") is False
        and run_plan.get("agentDispatchCount") == 0
        and run_plan.get("modelCallCount") == 0
        and run_plan.get("materializedAgentStages")
        == ["hop-1-decomposition"]
        and run_plan.get("deferredAgentStages")
        == ["hop-2-routing", "hop-3-acceptance-and-recovery"]
        and run_plan.get("rawEvidenceDestinationBound") is False,
        "Packet run plan overclaimed readiness",
    )
    _require(
        input_envelope.get("dynamicInputCount") == 1
        and input_envelope.get("artifact") == protocol["frozenSource"]
        and stage_contract.get("allowedDynamicInputCount") == 1
        and stage_contract.get("allowedInputArtifactIds") == ["S0"]
        and stage_contract.get("requiredInvariantIds")
        == [item["id"] for item in protocol["oracle"]["invariants"]]
        and stage_contract.get("toolsAllowed") == []
        and stage_contract.get("sharedConversationStateAllowed") is False
        and stage_contract.get("oracleValuesVisibleOutsideInputArtifact")
        is False,
        "Packet first-hop exposure contract drifted",
    )
    runtime_values = [input_envelope, stage_contract]
    runtime_keys = set().union(*(_walk_keys(item) for item in runtime_values))
    _require(
        not (runtime_keys & PRIVATE_RUNTIME_KEYS),
        "Packet leaked private scoring fields into Agent runtime",
    )

    trace_schema = json.loads(schema_path.read_text(encoding="utf-8"))
    required = trace_schema.get("required", [])
    _require(
        trace_schema.get("$schema")
        == "https://json-schema.org/draft/2020-12/schema"
        and trace_schema.get("additionalProperties") is False
        and {
            "runIdentity",
            "materialEdges",
            "hopMetrics",
            "absoluteLedger",
            "processLedger",
            "rawArtifactsDurable",
            "manualMetricSupplementationUsed",
        }
        <= set(required)
        and trace_schema["properties"]["rawArtifactsDurable"].get("const")
        is True
        and trace_schema["properties"][
            "manualMetricSupplementationUsed"
        ].get("const")
        is False,
        "Packet trace schema boundary drifted",
    )
    return {
        "schema": 1,
        "status": "zero-dispatch-packet-preflight-passed",
        "protocolFileSha256": file_sha256(protocol_path),
        "traceSchemaFileSha256": file_sha256(schema_path),
        "agentDispatchCount": 0,
        "modelCallCount": 0,
        "agentVisibleFileCount": len(EXPECTED_RUNTIME_FILES),
        "privateScoringFieldLeakCount": len(
            runtime_keys & PRIVATE_RUNTIME_KEYS
        ),
        "deferredAgentStagesMaterialized": False,
        "actualRouteObserved": False,
        "rawEvidenceDestinationBound": False,
        "liveDispatchReady": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args()
    root = args.root.resolve()
    build_packet(args.output, root=root)
    report = validate_packet(args.output, root=root)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
