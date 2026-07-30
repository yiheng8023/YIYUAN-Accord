#!/usr/bin/env python3
"""Evaluate parent-captured chained-transform artifacts.

All metrics are recomputed from persisted bytes and the parent-only oracle.
Zero-model captures remain calibration-only even when every mechanism passes.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

try:
    from .evaluate_process_fidelity_multihop_injection_poc import (
        _evaluate_hop,
    )
    from .run_process_fidelity_chained_transform_trial import (
        AGENT_STAGE_IDS,
        AMENDMENT_PATH,
        BASE_PROTOCOL_PATH,
        EDGE_IDS,
        RAW_SCHEMA_PATH,
        TRACE_SCHEMA_PATH,
        canonical_sha256,
        file_sha256,
    )
except ImportError:  # pragma: no cover - direct script execution
    from evaluate_process_fidelity_multihop_injection_poc import (
        _evaluate_hop,
    )
    from run_process_fidelity_chained_transform_trial import (
        AGENT_STAGE_IDS,
        AMENDMENT_PATH,
        BASE_PROTOCOL_PATH,
        EDGE_IDS,
        RAW_SCHEMA_PATH,
        TRACE_SCHEMA_PATH,
        canonical_sha256,
        file_sha256,
    )


ROOT = Path(__file__).resolve().parent.parent
MATERIAL_STAGE_IDS = [
    "hop-1-decomposition",
    "edge-controlled-mutation",
    "hop-2-routing",
    "edge-recovery-envelope",
    "hop-3-acceptance-and-recovery",
]


def _core(artifact: dict[str, Any]) -> dict[str, Any]:
    return {
        "values": artifact.get("values", {}),
        "provenanceIds": sorted(artifact.get("provenanceIds", [])),
        "assumptionIds": sorted(artifact.get("assumptionIds", [])),
    }


def _metric(
    artifact: dict[str, Any],
    protocol: dict[str, Any],
    *,
    stage_id: str,
) -> dict[str, Any]:
    oracle = protocol["oracle"]
    source_values = protocol["frozenSource"]["values"]
    invariant_values = {
        item["id"]: source_values[item["id"]]
        for item in oracle["invariants"]
    }
    invariant_weights = {
        item["id"]: item["weight"]
        for item in oracle["invariants"]
    }
    assumption_weights = {
        item["id"]: item["weight"]
        for item in oracle["unauthorizedAssumptions"]
    }
    result = _evaluate_hop(
        {
            "id": stage_id,
            "values": artifact.get("values", {}),
            "provenanceIds": artifact.get("provenanceIds", []),
            "assumptionIds": artifact.get("assumptionIds", []),
            "detectedLossIds": artifact.get("detectedLossIds", []),
        },
        invariant_values,
        invariant_weights,
        assumption_weights,
    )
    expected_provenance = {
        item["id"] for item in protocol["oracle"]["invariants"]
    }
    observed_provenance = set(artifact.get("provenanceIds", []))
    missing_provenance = sorted(
        expected_provenance - observed_provenance
    )
    legacy_missing = set(result.get("missingProvenanceIds", []))
    new_missing = [
        item for item in missing_provenance if item not in legacy_missing
    ]
    active_loss_ids = sorted(
        set(result.get("activeLossIds", []))
        | {f"provenance-missing:{item}" for item in missing_provenance}
    )
    detected = sorted(artifact.get("detectedLossIds", []))
    detection_valid = (
        detected == active_loss_ids if detected else None
    )
    return {
        "stageId": stage_id,
        "invariantSurvivalRate": result["invariantSurvivalRate"],
        "weightedOmissionScore": result["weightedOmissionScore"],
        "addedAssumptionCount": result["addedAssumptionCount"],
        "provenanceBreakCount": (
            result["provenanceBreakCount"] + len(new_missing)
        ),
        "authorityDriftCount": result["authorityDriftCount"],
        "weightedDelta": result["weightedDelta"] + len(new_missing),
        "omittedInvariantIds": result["omittedInvariantIds"],
        "changedInvariantIds": result["changedInvariantIds"],
        "activeLossIds": active_loss_ids,
        "detectedLossIds": detected,
        "detectionEvidenceValid": detection_valid,
    }


def _safe_artifact_path(capture_root: Path, value: Any) -> Path | None:
    if not isinstance(value, str) or not value:
        return None
    relative = Path(value)
    if relative.is_absolute() or ".." in relative.parts:
        return None
    path = (capture_root / relative).resolve()
    if not path.is_relative_to(capture_root.resolve()):
        return None
    return path


def _load_documents(
    root: Path,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, str]]:
    paths = {
        "baseProtocol": root / BASE_PROTOCOL_PATH,
        "protocolAmendment": root / AMENDMENT_PATH,
        "rawCaptureSchema": root / RAW_SCHEMA_PATH,
        "formalTraceSchema": root / TRACE_SCHEMA_PATH,
    }
    protocol = json.loads(paths["baseProtocol"].read_text(encoding="utf-8"))
    amendment = json.loads(
        paths["protocolAmendment"].read_text(encoding="utf-8")
    )
    hashes = {key: file_sha256(path) for key, path in paths.items()}
    return protocol, amendment, hashes


def _derive_arm(
    protocol: dict[str, Any],
    cell: dict[str, Any],
) -> str | None:
    try:
        return protocol["cohortDesign"]["pairedRunBlocks"][
            cell["blockIndex"] - 1
        ][cell["positionInBlock"] - 1]
    except (KeyError, IndexError, TypeError):
        return None


def _read_indexed_artifacts(
    capture: dict[str, Any],
    *,
    capture_root: Path,
) -> tuple[dict[str, dict[str, Any]], list[str]]:
    artifacts: dict[str, dict[str, Any]] = {}
    failures: list[str] = []
    index = capture.get("rawArtifactIndex")
    if not isinstance(index, list) or not index:
        return {}, ["raw-artifact-index-missing"]
    for item in index:
        if not isinstance(item, dict):
            failures.append("raw-artifact-index-invalid")
            continue
        artifact_id = item.get("artifactId")
        path = _safe_artifact_path(capture_root, item.get("path"))
        if not isinstance(artifact_id, str) or artifact_id in artifacts:
            failures.append("raw-artifact-index-invalid")
            continue
        if path is None or not path.is_file():
            failures.append("raw-artifact-durability-failure")
            continue
        raw = path.read_bytes()
        if (
            item.get("bytes") != len(raw)
            or item.get("rawSha256") != file_sha256(path)
        ):
            failures.append("raw-artifact-hash-mismatch")
            continue
        try:
            artifact = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            failures.append("raw-artifact-parse-failure")
            continue
        if (
            not isinstance(artifact, dict)
            or artifact.get("artifactId") != artifact_id
            or item.get("canonicalSha256") != canonical_sha256(artifact)
        ):
            failures.append("raw-artifact-hash-mismatch")
            continue
        artifacts[artifact_id] = artifact
    return artifacts, failures


def _validate_bindings(
    capture: dict[str, Any],
    hashes: dict[str, str],
) -> list[str]:
    bindings = capture.get("bindings")
    if not isinstance(bindings, dict):
        return ["contract-binding-missing"]
    failures: list[str] = []
    expected = {
        "baseProtocol": (BASE_PROTOCOL_PATH, hashes["baseProtocol"]),
        "protocolAmendment": (
            AMENDMENT_PATH,
            hashes["protocolAmendment"],
        ),
        "rawCaptureSchema": (
            RAW_SCHEMA_PATH,
            hashes["rawCaptureSchema"],
        ),
        "formalTraceSchema": (
            TRACE_SCHEMA_PATH,
            hashes["formalTraceSchema"],
        ),
    }
    for key, (path, digest) in expected.items():
        value = bindings.get(key)
        if (
            not isinstance(value, dict)
            or value.get("path") != path
            or value.get("fileSha256", "").lower() != digest.lower()
        ):
            failures.append("contract-binding-drift")
    return failures


def _validate_sequence(
    capture: dict[str, Any],
    protocol: dict[str, Any],
    amendment: dict[str, Any],
    artifacts: dict[str, dict[str, Any]],
    *,
    capture_root: Path,
) -> list[str]:
    failures: list[str] = []
    cell = capture.get("cell")
    if (
        not isinstance(cell, dict)
        or cell.get("armId") != _derive_arm(protocol, cell)
    ):
        failures.append("cohort-cell-or-arm-drift")
        return failures
    run_id = cell.get("runId")
    completion = capture.get("completion", {})
    complete = completion.get("status") == "zero-model-sequence-complete"
    expected_artifacts = [
        "S0",
        f"{run_id}-O1",
        f"{run_id}-M1",
        f"{run_id}-O2",
    ]
    if complete:
        expected_artifacts += [f"{run_id}-R2", f"{run_id}-O3"]
    if set(artifacts) != set(expected_artifacts):
        failures.append("raw-artifact-set-drift")

    stage_receipts = capture.get("stageReceipts")
    expected_stages = AGENT_STAGE_IDS if complete else AGENT_STAGE_IDS[:2]
    if (
        not isinstance(stage_receipts, list)
        or [item.get("stageId") for item in stage_receipts]
        != expected_stages
    ):
        failures.append("stage-order-drift")
    else:
        for receipt in stage_receipts:
            runtime = (
                capture_root
                / "AGENT-RUNTIME"
                / receipt["stageId"]
            )
            visible = sorted(
                item.name for item in runtime.iterdir()
            ) if runtime.is_dir() else []
            if (
                visible
                != ["INPUT-ENVELOPE.json", "STAGE-CONTRACT.json"]
                or receipt.get("dynamicInputCount") != 1
                or receipt.get("privateOracleCanonicalRowLeakCount") != 0
                or receipt.get("parseStatus") != "parsed-structured-json"
            ):
                failures.append("stage-isolation-or-exposure-drift")
                break

    edges = capture.get("materialEdges")
    expected_edges = EDGE_IDS if complete else EDGE_IDS[:3]
    if (
        not isinstance(edges, list)
        or [item.get("edgeId") for item in edges] != expected_edges
        or [item.get("stageId") for item in edges]
        != MATERIAL_STAGE_IDS[: len(expected_edges)]
    ):
        failures.append("material-edge-order-drift")
        return failures
    for edge in edges:
        predecessor = artifacts.get(
            edge.get("predecessorOutputArtifactId")
        )
        current_input = artifacts.get(edge.get("currentInputArtifactId"))
        output = artifacts.get(edge.get("outputArtifactId"))
        if not all(
            isinstance(item, dict)
            for item in (predecessor, current_input, output)
        ):
            failures.append("material-edge-artifact-missing")
            continue
        predecessor_hash = canonical_sha256(predecessor)
        input_hash = canonical_sha256(current_input)
        if (
            edge.get("predecessorOutputArtifactSha256")
            != predecessor_hash
            or edge.get("currentInputArtifactSha256") != input_hash
            or edge.get("outputArtifactSha256")
            != canonical_sha256(output)
            or edge.get("inputEqualsDeclaredPredecessor")
            is not (predecessor_hash == input_hash)
            or predecessor_hash != input_hash
        ):
            failures.append("predecessor-input-linkage-mismatch")
        if edge.get("opaque") is True:
            failures.append("opaque-material-edge")

    receipts = capture.get("parentTransformReceipts")
    expected_parent_stages = [
        "edge-controlled-mutation",
        "edge-recovery-envelope",
    ]
    if (
        not isinstance(receipts, list)
        or [item.get("stageId") for item in receipts]
        != expected_parent_stages
    ):
        failures.append("parent-transform-receipt-drift")
        return failures
    mutation = receipts[0]
    arm = next(
        item
        for item in protocol["armDefinitions"]
        if item["armId"] == cell["armId"]
    )
    if (
        mutation.get("contractMatch") is not True
        or mutation.get("expectedDelta") != arm["allowedDelta"]
        or mutation.get("observedDelta") != arm["allowedDelta"]
    ):
        failures.append("mutation-contract-mismatch")

    recovery = receipts[1]
    o2 = artifacts.get(f"{run_id}-O2")
    if isinstance(o2, dict):
        o2_metric = _metric(o2, protocol, stage_id="hop-2-routing")
        detected = sorted(o2.get("detectedLossIds", []))
        active = o2_metric["activeLossIds"]
        detection_valid = bool(active) and detected == active
        if recovery.get("detectionEvidenceValid") is not detection_valid:
            failures.append("invalid-detection-marker")
        if complete:
            envelope = artifacts.get(f"{run_id}-R2")
            if not isinstance(envelope, dict):
                failures.append("recovery-envelope-missing")
            else:
                exposed = envelope.get("sourceAnchorPayloadExposed")
                if (
                    exposed is not detection_valid
                    or ("sourceAnchorArtifact" in envelope) is not exposed
                    or amendment["recoveryGateAmendment"][
                        "sourceAnchorPayloadExposurePolicy"
                    ]
                    != "valid-exact-hop-2-detection-only"
                ):
                    failures.append("source-anchor-exposure-gate-drift")
        elif completion.get("failureCodes") != ["invalid-detection-marker"]:
            failures.append("incomplete-capture-disposition-drift")
    return failures


def _dedupe(values: list[str]) -> list[str]:
    return list(dict.fromkeys(values))


def evaluate_capture(
    capture: dict[str, Any],
    *,
    capture_root: Path,
    root: Path = ROOT,
) -> dict[str, Any]:
    root = root.resolve()
    capture_root = capture_root.resolve()
    protocol, amendment, hashes = _load_documents(root)
    failures: list[str] = []
    if (
        capture.get("schema") != 1
        or capture.get("kind")
        != "chained-transform-raw-sequence-capture"
        or capture.get("mode")
        != "zero-model-scripted-order-calibration"
        or capture.get("eligibleForFormalLiveEvidence") is not False
    ):
        failures.append("raw-capture-identity-drift")
    execution = capture.get("execution")
    if (
        not isinstance(execution, dict)
        or execution.get("agentDispatchCount") != 0
        or execution.get("modelCallCount") != 0
        or execution.get("actualRouteObserved") is not False
        or execution.get("dispatchAuthorized") is not False
    ):
        failures.append("zero-dispatch-boundary-drift")
    if any(
        key in capture
        for key in ("hopMetrics", "absoluteLedger", "processLedger")
    ):
        failures.append("manual-metric-supplementation")
    failures.extend(_validate_bindings(capture, hashes))
    artifacts, artifact_failures = _read_indexed_artifacts(
        capture,
        capture_root=capture_root,
    )
    failures.extend(artifact_failures)
    if not artifact_failures:
        failures.extend(
            _validate_sequence(
                capture,
                protocol,
                amendment,
                artifacts,
                capture_root=capture_root,
            )
        )
    failures = _dedupe(failures)
    cell = capture.get("cell", {})
    run_id = cell.get("runId")
    complete = (
        capture.get("completion", {}).get("status")
        == "zero-model-sequence-complete"
    )
    completion_failures = capture.get("completion", {}).get(
        "failureCodes", []
    )
    if isinstance(completion_failures, list):
        failures.extend(
            item
            for item in completion_failures
            if isinstance(item, str) and item
        )
    if not complete and "invalid-detection-marker" not in failures:
        failures.append("incomplete-sequence")

    candidate_trace: dict[str, Any] | None = None
    outcome = "invalid-capture"
    if complete and not failures:
        artifact_ids = [
            f"{run_id}-O1",
            f"{run_id}-O2",
            f"{run_id}-O3",
        ]
        metrics = [
            _metric(
                artifacts[artifact_id],
                protocol,
                stage_id=stage_id,
            )
            for artifact_id, stage_id in zip(
                artifact_ids,
                AGENT_STAGE_IDS,
            )
        ]
        source = artifacts["S0"]
        m1_metric = _metric(
            artifacts[f"{run_id}-M1"],
            protocol,
            stage_id="edge-controlled-mutation",
        )
        first_delta_stage: str | None = None
        first_delta_index: int | None = None
        stage_metrics = [
            (1, "hop-1-decomposition", metrics[0]),
            (2, "edge-controlled-mutation", m1_metric),
            (3, "hop-2-routing", metrics[1]),
            (5, "hop-3-acceptance-and-recovery", metrics[2]),
        ]
        for index, stage_id, metric in stage_metrics:
            if metric["weightedDelta"] > 0:
                first_delta_stage = stage_id
                first_delta_index = index
                break
        detection_items = [
            (1, "hop-1-decomposition", metrics[0]),
            (3, "hop-2-routing", metrics[1]),
            (5, "hop-3-acceptance-and-recovery", metrics[2]),
        ]
        first_detection = next(
            (
                (index, stage_id)
                for index, stage_id, metric in detection_items
                if metric["detectionEvidenceValid"] is True
            ),
            None,
        )
        detection_latency = (
            first_detection[0] - first_delta_index
            if first_detection is not None
            and first_delta_index is not None
            else None
        )
        injected_delta = m1_metric["weightedDelta"]
        expected_injected_authority_drift = (
            1 if cell["armId"] == "injected-authority-omission" else 0
        )
        unexpected_authority_drift = max(
            0,
            metrics[1]["authorityDriftCount"]
            - expected_injected_authority_drift,
        )
        downstream_metrics = [m1_metric, metrics[1], metrics[2]]
        amplification = (
            max(item["weightedDelta"] for item in downstream_metrics)
            / injected_delta
            if injected_delta > 0
            else 0.0
        )
        downstream_affected = (
            sum(
                1
                for index, _, metric in stage_metrics
                if first_delta_index is not None
                and index > first_delta_index
                and metric["weightedDelta"] > 0
            )
            if first_delta_index is not None
            else 0
        )
        terminal_matches = _core(artifacts[f"{run_id}-O3"]) == _core(source)
        recovery_receipt = capture["parentTransformReceipts"][1]
        arm_id = cell["armId"]
        recovery_valid = (
            terminal_matches
            and (
                (
                    arm_id == "injected-authority-omission"
                    and recovery_receipt["detectionEvidenceValid"] is True
                    and recovery_receipt["sourceAnchorPayloadExposed"] is True
                )
                or (
                    arm_id == "control-identity"
                    and recovery_receipt["detectionEvidenceValid"] is False
                    and recovery_receipt["sourceAnchorPayloadExposed"] is False
                )
            )
        )
        thresholds = protocol["thresholds"]
        if arm_id == "control-identity":
            process_pass = (
                all(item["weightedDelta"] == 0 for item in metrics)
                and all(
                    not item["detectedLossIds"] for item in metrics
                )
                and recovery_valid
            )
            outcome = (
                "zero-model-control-mechanism-pass"
                if process_pass
                else "zero-model-control-mechanism-fail"
            )
        else:
            process_pass = (
                metrics[0]["weightedDelta"] == 0
                and m1_metric["weightedDelta"]
                == next(
                    item["expectedInjectedWeightedDelta"]
                    for item in protocol["armDefinitions"]
                    if item["armId"] == arm_id
                )
                and metrics[1]["detectionEvidenceValid"] is True
                and detection_latency
                <= thresholds["injectedDetectionLatencyMaterialHopsMax"]
                and amplification
                <= thresholds["injectedAmplificationFactorMax"]
                and metrics[1]["addedAssumptionCount"]
                <= thresholds["injectedAddedAssumptionCountMax"]
                and unexpected_authority_drift
                <= thresholds["injectedAuthorityDriftCountMax"]
                and recovery_valid
            )
            outcome = (
                "zero-model-injected-mechanism-pass"
                if process_pass
                else "zero-model-injected-mechanism-fail"
            )
        candidate_trace = {
            "schema": 2,
            "kind": "process-fidelity-chained-transform-evaluated-trace",
            "eligibility": {
                "status": "calibration-only",
                "failureCodes": [],
                "formalLiveEvidenceEligible": False,
            },
            "execution": {
                "agentDispatchCount": 0,
                "modelCallCount": 0,
                "actualRouteObserved": False,
                "requestedRouteCountsAsObservedRoute": False,
            },
            "runIdentity": dict(cell),
            "materialEdges": capture["materialEdges"],
            "hopMetrics": metrics,
            "injectionLedger": {
                **capture["parentTransformReceipts"][0],
                "observedWeightedDelta": m1_metric["weightedDelta"],
                "expectedInjectedAuthorityDriftCount": (
                    expected_injected_authority_drift
                ),
                "unexpectedAuthorityDriftCount": (
                    unexpected_authority_drift
                ),
            },
            "recoveryLedger": {
                **recovery_receipt,
                "restored": recovery_valid,
            },
            "absoluteLedger": {
                "terminalMatchesSourceAnchor": terminal_matches,
                "terminalAcceptancePass": terminal_matches,
            },
            "processLedger": {
                "firstDeltaStageId": first_delta_stage,
                "firstDetectionStageId": (
                    first_detection[1] if first_detection else None
                ),
                "detectionLatencyMaterialHops": detection_latency,
                "downstreamAffectedHopCount": downstream_affected,
                "amplificationFactor": amplification,
                "sourceBackedRecoveryValid": recovery_valid,
                "recoveryDistanceMaterialHops": (
                    3 if arm_id == "injected-authority-omission" else 0
                ),
                "intermediateLossPresent": any(
                    item["weightedDelta"] > 0
                    for item in (m1_metric, metrics[1])
                ),
                "processAcceptancePass": process_pass,
            },
            "rawArtifactIndex": capture["rawArtifactIndex"],
            "manualMetricSupplementationUsed": False,
            "claimBoundary": {
                "liveAgentBehaviorProved": False,
                "actualWeakModelRouteObserved": False,
                "formalCohortStarted": False,
                "endToEndProcessFidelityAccepted": False,
                "candidateSkillEffectMeasured": False,
                "deliveryTopologyCompared": False,
                "selfAuthoredResidualGapProved": False,
            },
        }

    eligibility = (
        "calibration-only"
        if candidate_trace is not None
        else (
            "opaque"
            if "opaque-material-edge" in failures
            else "invalid"
        )
    )
    report = {
        "schema": 1,
        "id": f"process-fidelity-chained-transform-evaluation-{run_id}",
        "status": eligibility,
        "failureCodes": failures,
        "outcome": outcome,
        "agentDispatchCount": 0,
        "modelCallCount": 0,
        "actualRouteObserved": False,
        "formalProcessCohortCount": 0,
        "formalLiveEvidenceEligible": False,
        "candidateTrace": candidate_trace,
        "claimLimit": (
            "This report can prove only zero-model sequencing, persisted "
            "artifact linkage, conditional source exposure, parent metric "
            "recomputation, and fault detection. It does not prove live Agent "
            "behavior, an observed Spark route, a formal cohort result, "
            "cross-host portability, or end-to-end acceptance."
        ),
    }
    report["reportSha256"] = canonical_sha256(report)
    return report
