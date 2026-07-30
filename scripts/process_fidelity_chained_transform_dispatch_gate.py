#!/usr/bin/env python3
"""Validate one-run authority and parent-derived native hop receipts.

This module is deliberately offline.  It does not start Codex, call a model,
reserve a dispatch, or write evidence.  A future live runner may use the
validated structures only after an atomic one-shot reservation has been
implemented and separately authorized.
"""

from __future__ import annotations

from datetime import datetime
import hashlib
import json
from pathlib import Path
import re
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parent.parent
BASE_PROTOCOL_PATH = (
    "registry/human-ai-collaboration-process-fidelity-chained-transform-"
    "trial-protocol-2026-07-27.json"
)
AMENDMENT_PATH = (
    "registry/human-ai-collaboration-process-fidelity-chained-transform-"
    "trial-protocol-v2-amendment-2026-07-27.json"
)
RAW_CAPTURE_SCHEMA_PATH = (
    "schemas/process-fidelity-chained-transform-raw-sequence-capture-v1."
    "schema.json"
)
TRACE_SCHEMA_PATH = (
    "schemas/process-fidelity-chained-transform-trace-v2.schema.json"
)
HOP_IDS = (
    "hop-1-decomposition",
    "hop-2-routing",
    "hop-3-acceptance-and-recovery",
)
OUTPUT_SUFFIXES = ("O1", "O2", "O3")
INPUT_SUFFIXES = ("S0", "M1", "R2")
ALLOWED_ITEM_TYPES = frozenset({"userMessage", "reasoning", "agentMessage"})
PRIVATE_RUNTIME_KEYS = frozenset(
    {
        "invariantWeights",
        "unauthorizedAssumptionWeights",
        "expectedMutationDelta",
        "expectedInjectedWeightedDelta",
        "thresholds",
        "privateScoringFieldsUntilScoring",
    }
)
RUN_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,95}$")


class DispatchGateError(RuntimeError):
    """Raised when an offline dispatch-gate document is invalid."""


def canonical_sha256(value: Any) -> str:
    encoded = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _is_sha256(value: Any) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(character in "0123456789abcdefABCDEF" for character in value)
    )


def _parse_time(value: Any, label: str) -> datetime:
    if not isinstance(value, str):
        raise DispatchGateError(f"{label} is missing")
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as error:
        raise DispatchGateError(f"{label} is invalid") from error
    if parsed.tzinfo is None:
        raise DispatchGateError(f"{label} must include an offset")
    return parsed


def _load_json(path: Path, label: str) -> tuple[dict[str, Any], bytes]:
    try:
        raw = path.read_bytes()
        value = json.loads(raw.decode("utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise DispatchGateError(f"{label} is not readable valid JSON") from error
    if not isinstance(value, dict):
        raise DispatchGateError(f"{label} must be a JSON object")
    return value, raw


def _contained_relative(value: Any, label: str) -> Path:
    if not isinstance(value, str) or not value.strip():
        raise DispatchGateError(f"{label} is missing")
    path = Path(value)
    if path.is_absolute() or ".." in path.parts:
        raise DispatchGateError(f"{label} must be a contained relative path")
    return path


def _find_thread(value: Any) -> dict[str, Any] | None:
    if isinstance(value, dict):
        thread = value.get("thread")
        if (
            isinstance(thread, dict)
            and isinstance(thread.get("id"), str)
            and isinstance(thread.get("model"), str)
        ):
            return thread
        for child in value.values():
            found = _find_thread(child)
            if found is not None:
                return found
    elif isinstance(value, list):
        for child in value:
            found = _find_thread(child)
            if found is not None:
                return found
    return None


def _source_bindings(root: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    paths = {
        "baseProtocol": root / BASE_PROTOCOL_PATH,
        "protocolAmendment": root / AMENDMENT_PATH,
        "rawCaptureSchema": root / RAW_CAPTURE_SCHEMA_PATH,
        "formalTraceSchema": root / TRACE_SCHEMA_PATH,
    }
    if not all(path.is_file() for path in paths.values()):
        raise DispatchGateError("a chained-transform contract file is missing")
    protocol, _ = _load_json(paths["baseProtocol"], "base protocol")
    amendment, _ = _load_json(paths["protocolAmendment"], "protocol amendment")
    if not (
        amendment.get("baseProtocol", {}).get("path") == BASE_PROTOCOL_PATH
        and amendment.get("baseProtocol", {}).get(
            "fileSha256", ""
        ).lower()
        == file_sha256(paths["baseProtocol"]).lower()
        and amendment.get("formalTraceContract", {}).get(
            "actualRouteEvidenceRequiredForFormalLiveEligibility"
        )
        is True
        and amendment.get("executionBoundary", {}).get(
            "liveDispatchAuthorized"
        )
        is False
    ):
        raise DispatchGateError("protocol amendment binding drifted")
    bindings = {
        key: {
            "path": path.relative_to(root).as_posix(),
            "fileSha256": file_sha256(path),
        }
        for key, path in paths.items()
    }
    bindings["frozenSourceCanonicalSha256"] = canonical_sha256(
        protocol["frozenSource"]
    )
    bindings["privateOracleCommitment"] = canonical_sha256(protocol["oracle"])
    return protocol, bindings


def _derive_cell(
    protocol: dict[str, Any],
    *,
    run_id: str,
    block_index: int,
    position_in_block: int,
) -> dict[str, Any]:
    if not isinstance(run_id, str) or not RUN_ID_PATTERN.fullmatch(run_id):
        raise DispatchGateError("runId is invalid")
    blocks = protocol.get("cohortDesign", {}).get("pairedRunBlocks")
    if (
        not isinstance(blocks, list)
        or not isinstance(block_index, int)
        or not 1 <= block_index <= len(blocks)
    ):
        raise DispatchGateError("blockIndex is outside the frozen design")
    block = blocks[block_index - 1]
    if (
        not isinstance(block, list)
        or not isinstance(position_in_block, int)
        or not 1 <= position_in_block <= len(block)
    ):
        raise DispatchGateError(
            "positionInBlock is outside the frozen design"
        )
    return {
        "runId": run_id,
        "blockIndex": block_index,
        "positionInBlock": position_in_block,
        "armId": block[position_in_block - 1],
    }


def _validate_authority(
    authority: dict[str, Any],
    *,
    cell: dict[str, Any],
    route: dict[str, Any],
    observed_at: datetime,
) -> None:
    required = {
        "schema",
        "kind",
        "authorityId",
        "authorityLocator",
        "nonce",
        "runId",
        "blockIndex",
        "positionInBlock",
        "authorizedHopIds",
        "maximumAgentDispatchCount",
        "model",
        "reasoningEffort",
        "providerFallbackAllowed",
        "dispatchAuthorized",
        "automaticRetryAllowed",
        "replacementDispatchAllowed",
        "strongDiagnosticAuthorized",
        "externalAccessAuthorized",
        "hostConfigurationMutationAuthorized",
        "globalSkillMutationAuthorized",
        "cleanupAuthorized",
        "notBefore",
        "expiresAt",
    }
    if set(authority) != required:
        raise DispatchGateError("authority document shape drifted")
    if not (
        authority["schema"] == 1
        and authority["kind"] == "one-chained-transform-run-authority"
        and all(
            isinstance(authority[key], str) and authority[key].strip()
            for key in ("authorityId", "authorityLocator", "nonce")
        )
        and authority["runId"] == cell["runId"]
        and authority["blockIndex"] == cell["blockIndex"]
        and authority["positionInBlock"] == cell["positionInBlock"]
        and authority["authorizedHopIds"] == list(HOP_IDS)
        and authority["maximumAgentDispatchCount"] == len(HOP_IDS)
        and authority["model"] == route["model"]
        and authority["reasoningEffort"] == route["reasoningEffort"]
        and authority["providerFallbackAllowed"] is False
        and authority["dispatchAuthorized"] is True
        and authority["automaticRetryAllowed"] is False
        and authority["replacementDispatchAllowed"] is False
        and authority["strongDiagnosticAuthorized"] is False
        and authority["externalAccessAuthorized"] is False
        and authority["hostConfigurationMutationAuthorized"] is False
        and authority["globalSkillMutationAuthorized"] is False
        and authority["cleanupAuthorized"] is False
    ):
        raise DispatchGateError("authority boundary is not satisfied")
    not_before = _parse_time(authority["notBefore"], "notBefore")
    expires_at = _parse_time(authority["expiresAt"], "expiresAt")
    if not not_before <= observed_at <= expires_at:
        raise DispatchGateError("authority window is invalid")


def _validate_route_observation(
    root: Path,
    observation: dict[str, Any],
    *,
    route: dict[str, Any],
    envelope_observed_at: datetime,
) -> dict[str, Any]:
    required = {
        "schema",
        "kind",
        "hostId",
        "hostVersion",
        "appServerTransport",
        "observedAt",
        "rawThreadStartResponsePath",
        "rawThreadStartResponseSha256",
        "turnStartRequestCount",
        "providerFallbackRequested",
    }
    if set(observation) != required:
        raise DispatchGateError("route observation shape drifted")
    raw_relative = _contained_relative(
        observation["rawThreadStartResponsePath"],
        "rawThreadStartResponsePath",
    )
    raw_path = root / raw_relative
    raw_response, _ = _load_json(raw_path, "thread start response")
    thread = _find_thread(raw_response)
    observed_time = _parse_time(observation["observedAt"], "route observedAt")
    age_seconds = (envelope_observed_at - observed_time).total_seconds()
    if not (
        observation["schema"] == 1
        and observation["kind"]
        == "codex-app-server-thread-route-observation"
        and all(
            isinstance(observation[key], str) and observation[key].strip()
            for key in ("hostId", "hostVersion", "appServerTransport")
        )
        and file_sha256(raw_path).lower()
        == observation["rawThreadStartResponseSha256"].lower()
        and thread is not None
        and thread.get("model") == route["model"]
        and thread.get("reasoningEffort") == route["reasoningEffort"]
        and observation["turnStartRequestCount"] == 0
        and observation["providerFallbackRequested"] is False
        and 0 <= age_seconds <= route["maximumObservationAgeSeconds"]
    ):
        raise DispatchGateError(
            "fresh host-reported effective thread route was not proved"
        )
    return {
        "hostId": observation["hostId"],
        "hostVersion": observation["hostVersion"],
        "appServerTransport": observation["appServerTransport"],
        "observedAt": observation["observedAt"],
        "threadId": thread["id"],
        "hostReportedModel": thread["model"],
        "hostReportedReasoningEffort": thread["reasoningEffort"],
        "hostReportedModelProvider": thread.get("modelProvider"),
        "rawThreadStartResponsePath": raw_relative.as_posix(),
        "rawThreadStartResponseSha256": file_sha256(raw_path),
        "routeClass": "host-reported-effective-thread-route",
        "providerExecutionModelVisible": False,
        "providerExecutionEffortVisible": False,
    }


def build_dispatch_authorization_envelope(
    *,
    root: Path = ROOT,
    authority_document_path: Path,
    route_observation_path: Path,
    run_id: str,
    block_index: int,
    position_in_block: int,
    raw_evidence_relative_path: str,
    observed_at: str,
) -> dict[str, Any]:
    """Build one immutable, offline authorization envelope.

    The result is not dispatch-ready until a future atomic reservation ledger
    consumes it exactly once.
    """

    root = root.resolve()
    protocol, bindings = _source_bindings(root)
    cell = _derive_cell(
        protocol,
        run_id=run_id,
        block_index=block_index,
        position_in_block=position_in_block,
    )
    route = dict(protocol["cohortDesign"]["primaryAgentRoute"])
    route["maximumObservationAgeSeconds"] = 120
    envelope_time = _parse_time(observed_at, "envelope observedAt")
    authority, authority_raw = _load_json(
        authority_document_path.resolve(),
        "authority document",
    )
    _validate_authority(
        authority,
        cell=cell,
        route=route,
        observed_at=envelope_time,
    )
    observation, observation_raw = _load_json(
        route_observation_path.resolve(),
        "route observation",
    )
    observed_route = _validate_route_observation(
        root,
        observation,
        route=route,
        envelope_observed_at=envelope_time,
    )
    raw_relative = _contained_relative(
        raw_evidence_relative_path,
        "rawEvidenceRelativePath",
    )
    if not raw_relative.parts or raw_relative.parts[0] != "audits":
        raise DispatchGateError(
            "raw evidence destination must be repository-local audits"
        )
    raw_root = root / raw_relative
    if raw_root.exists() and (
        not raw_root.is_dir() or any(raw_root.iterdir())
    ):
        raise DispatchGateError(
            "raw evidence destination must be absent or empty"
        )
    stage_authorizations = []
    for sequence, hop_id in enumerate(HOP_IDS, start=1):
        stage_authorizations.append(
            {
                "sequence": sequence,
                "hopId": hop_id,
                "dispatchNonce": canonical_sha256(
                    {
                        "authorityId": authority["authorityId"],
                        "nonce": authority["nonce"],
                        "runId": run_id,
                        "hopId": hop_id,
                    }
                ),
                "maximumDispatchCount": 1,
                "freshInvocationRequired": True,
                "sharedConversationStateAllowed": False,
                "toolsAllowed": [],
            }
        )
    envelope = {
        "schema": 1,
        "kind": "chained-transform-dispatch-authorization-envelope",
        "workspaceRoot": root.as_posix(),
        "observedAt": observed_at,
        "authorizationDocument": {
            "path": authority_document_path.resolve().as_posix(),
            "rawSha256": hashlib.sha256(authority_raw).hexdigest(),
            "authorityId": authority["authorityId"],
            "authorityLocator": authority["authorityLocator"],
            "nonce": authority["nonce"],
        },
        "routeObservationDocument": {
            "path": route_observation_path.resolve().as_posix(),
            "rawSha256": hashlib.sha256(observation_raw).hexdigest(),
        },
        "bindings": bindings,
        "cell": cell,
        "route": {
            "requestedModel": route["model"],
            "requestedReasoningEffort": route["reasoningEffort"],
            "providerFallbackAllowed": False,
            "hostReportedEffectiveRoute": observed_route,
            "providerExecutionRouteTelemetry": "unknown",
        },
        "stageAuthorizations": stage_authorizations,
        "rawEvidenceRoot": raw_relative.as_posix(),
        "boundaries": {
            "maximumAgentDispatchCount": len(HOP_IDS),
            "automaticRetryAllowed": False,
            "replacementDispatchAllowed": False,
            "strongDiagnosticAuthorized": False,
            "externalAccessAuthorizedBeyondModelProvider": False,
            "hostConfigurationMutationAuthorized": False,
            "globalSkillMutationAuthorized": False,
            "cleanupAuthorized": False,
            "atomicReservationLedgerBound": False,
            "liveDispatchReady": False,
        },
    }
    envelope["authorizationSha256"] = canonical_sha256(envelope)
    return envelope


def validate_dispatch_authorization_envelope(
    envelope: dict[str, Any],
) -> list[str]:
    """Validate the immutable envelope shape without promoting live readiness."""

    failures: list[str] = []
    if not isinstance(envelope, dict):
        return ["fail-envelope-shape"]
    body = dict(envelope)
    digest = body.pop("authorizationSha256", None)
    if digest != canonical_sha256(body):
        failures.append("fail-envelope-digest")
    if (
        envelope.get("schema") != 1
        or envelope.get("kind")
        != "chained-transform-dispatch-authorization-envelope"
    ):
        failures.append("fail-envelope-identity")
    try:
        workspace_root = Path(envelope["workspaceRoot"]).resolve()
        protocol, expected_bindings = _source_bindings(workspace_root)
        cell = _derive_cell(
            protocol,
            run_id=envelope.get("cell", {}).get("runId"),
            block_index=envelope.get("cell", {}).get("blockIndex"),
            position_in_block=envelope.get("cell", {}).get(
                "positionInBlock"
            ),
        )
        if cell != envelope.get("cell"):
            failures.append("fail-run-cell-binding")
        if envelope.get("bindings") != expected_bindings:
            failures.append("fail-contract-binding")
        route = dict(protocol["cohortDesign"]["primaryAgentRoute"])
        route["maximumObservationAgeSeconds"] = 120
        envelope_time = _parse_time(
            envelope.get("observedAt"),
            "envelope observedAt",
        )
        authority_path = Path(
            envelope.get("authorizationDocument", {}).get("path", "")
        )
        authority, authority_raw = _load_json(
            authority_path,
            "authority document",
        )
        if not (
            hashlib.sha256(authority_raw).hexdigest()
            == envelope.get("authorizationDocument", {}).get("rawSha256")
            and authority.get("authorityId")
            == envelope.get("authorizationDocument", {}).get("authorityId")
            and authority.get("authorityLocator")
            == envelope.get("authorizationDocument", {}).get(
                "authorityLocator"
            )
            and authority.get("nonce")
            == envelope.get("authorizationDocument", {}).get("nonce")
        ):
            failures.append("fail-authority-document-binding")
        _validate_authority(
            authority,
            cell=cell,
            route=route,
            observed_at=envelope_time,
        )
        observation_path = Path(
            envelope.get("routeObservationDocument", {}).get("path", "")
        )
        observation, observation_raw = _load_json(
            observation_path,
            "route observation",
        )
        if hashlib.sha256(observation_raw).hexdigest() != envelope.get(
            "routeObservationDocument", {}
        ).get("rawSha256"):
            failures.append("fail-route-observation-document-binding")
        rebuilt_observed_route = _validate_route_observation(
            workspace_root,
            observation,
            route=route,
            envelope_observed_at=envelope_time,
        )
        if rebuilt_observed_route != envelope.get("route", {}).get(
            "hostReportedEffectiveRoute"
        ):
            failures.append("fail-route-observation-binding")
        raw_relative = _contained_relative(
            envelope.get("rawEvidenceRoot"),
            "rawEvidenceRoot",
        )
        raw_root = workspace_root / raw_relative
        if (
            not raw_relative.parts
            or raw_relative.parts[0] != "audits"
            or (
                raw_root.exists()
                and (
                    not raw_root.is_dir()
                    or any(raw_root.iterdir())
                )
            )
        ):
            failures.append("fail-raw-evidence-root")
    except (DispatchGateError, KeyError, OSError, TypeError, ValueError):
        failures.append("fail-envelope-source-revalidation")
    stages = envelope.get("stageAuthorizations")
    expected_stage_nonces = [
        canonical_sha256(
            {
                "authorityId": envelope.get(
                    "authorizationDocument",
                    {},
                ).get("authorityId"),
                "nonce": envelope.get(
                    "authorizationDocument",
                    {},
                ).get("nonce"),
                "runId": envelope.get("cell", {}).get("runId"),
                "hopId": hop_id,
            }
        )
        for hop_id in HOP_IDS
    ]
    if (
        not isinstance(stages, list)
        or [item.get("hopId") for item in stages] != list(HOP_IDS)
        or [item.get("sequence") for item in stages] != [1, 2, 3]
        or [item.get("dispatchNonce") for item in stages]
        != expected_stage_nonces
        or any(
            item.get("maximumDispatchCount") != 1
            or item.get("freshInvocationRequired") is not True
            or item.get("sharedConversationStateAllowed") is not False
            or item.get("toolsAllowed") != []
            or not _is_sha256(item.get("dispatchNonce"))
            for item in stages
        )
    ):
        failures.append("fail-stage-authorization")
    route = envelope.get("route", {})
    observed = route.get("hostReportedEffectiveRoute", {})
    if not (
        route.get("requestedModel") == "gpt-5.3-codex-spark"
        and route.get("requestedReasoningEffort") == "low"
        and route.get("providerFallbackAllowed") is False
        and observed.get("hostReportedModel") == route.get("requestedModel")
        and observed.get("hostReportedReasoningEffort")
        == route.get("requestedReasoningEffort")
        and observed.get("routeClass")
        == "host-reported-effective-thread-route"
        and observed.get("providerExecutionModelVisible") is False
        and observed.get("providerExecutionEffortVisible") is False
        and route.get("providerExecutionRouteTelemetry") == "unknown"
    ):
        failures.append("fail-route-binding")
    boundaries = envelope.get("boundaries", {})
    if not (
        boundaries.get("maximumAgentDispatchCount") == 3
        and boundaries.get("automaticRetryAllowed") is False
        and boundaries.get("replacementDispatchAllowed") is False
        and boundaries.get("strongDiagnosticAuthorized") is False
        and boundaries.get("externalAccessAuthorizedBeyondModelProvider")
        is False
        and boundaries.get("hostConfigurationMutationAuthorized") is False
        and boundaries.get("globalSkillMutationAuthorized") is False
        and boundaries.get("cleanupAuthorized") is False
        and boundaries.get("atomicReservationLedgerBound") is False
        and boundaries.get("liveDispatchReady") is False
    ):
        failures.append("hard-fail-boundary-promotion")
    return list(dict.fromkeys(failures))


def _event_messages(path: Path) -> list[dict[str, Any]]:
    messages: list[dict[str, Any]] = []
    try:
        for raw_line in path.read_text(encoding="utf-8").splitlines():
            if not raw_line.strip():
                continue
            record = json.loads(raw_line)
            if not (
                isinstance(record, dict)
                and set(record) == {"captureSequence", "direction", "message"}
                and isinstance(record["captureSequence"], int)
                and record["direction"] in {"client-to-server", "server-to-client"}
                and isinstance(record["message"], dict)
            ):
                raise ValueError
            messages.append(record)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError) as error:
        raise DispatchGateError("native event log is invalid") from error
    if [item["captureSequence"] for item in messages] != list(
        range(1, len(messages) + 1)
    ):
        raise DispatchGateError("native event sequence is not contiguous")
    return messages


def _artifact_binding(
    capture_root: Path,
    binding: dict[str, Any],
    *,
    expected_artifact_id: str,
) -> bool:
    required = {"artifactId", "path", "rawSha256", "canonicalSha256"}
    if not isinstance(binding, dict) or set(binding) != required:
        return False
    try:
        relative = _contained_relative(binding["path"], "artifact path")
        path = capture_root / relative
        value, _ = _load_json(path, "artifact")
    except DispatchGateError:
        return False
    return (
        binding["artifactId"] == expected_artifact_id
        and value.get("artifactId") == expected_artifact_id
        and file_sha256(path).lower() == binding["rawSha256"].lower()
        and canonical_sha256(value).lower()
        == binding["canonicalSha256"].lower()
    )


def _json_binding_value(
    capture_root: Path,
    binding: dict[str, Any],
) -> dict[str, Any] | None:
    required = {"path", "rawSha256", "canonicalSha256"}
    if not isinstance(binding, dict) or set(binding) != required:
        return None
    try:
        relative = _contained_relative(binding["path"], "JSON binding path")
        path = capture_root / relative
        value, _ = _load_json(path, "JSON binding")
    except DispatchGateError:
        return None
    if not (
        file_sha256(path).lower() == binding["rawSha256"].lower()
        and canonical_sha256(value).lower()
        == binding["canonicalSha256"].lower()
    ):
        return None
    return value


def _contains_private_runtime_key(value: Any) -> bool:
    if isinstance(value, dict):
        return bool(set(value) & PRIVATE_RUNTIME_KEYS) or any(
            _contains_private_runtime_key(child)
            for child in value.values()
        )
    if isinstance(value, list):
        return any(_contains_private_runtime_key(child) for child in value)
    return False


def validate_native_hop_receipts(
    *,
    envelope: dict[str, Any],
    receipts: Iterable[dict[str, Any]],
    capture_root: Path,
) -> dict[str, Any]:
    """Validate parent-derived native receipts for one future live run."""

    failures = validate_dispatch_authorization_envelope(envelope)
    receipt_list = list(receipts)
    if len(receipt_list) != len(HOP_IDS):
        failures.append("hop-receipt-count-drift")
    run_id = envelope.get("cell", {}).get("runId")
    authorization_sha = envelope.get("authorizationSha256")
    previous_receipt_sha: str | None = None
    thread_ids: set[str] = set()
    turn_ids: set[str] = set()
    previous_output_canonical_sha: str | None = None

    for index, receipt in enumerate(receipt_list):
        if index >= len(HOP_IDS):
            break
        hop_id = HOP_IDS[index]
        expected_output_id = f"{run_id}-{OUTPUT_SUFFIXES[index]}"
        expected_input_id = (
            INPUT_SUFFIXES[index]
            if index == 0
            else f"{run_id}-{INPUT_SUFFIXES[index]}"
        )
        expected_receipt_keys = {
            "schema",
            "kind",
            "authorizationSha256",
            "runId",
            "hopId",
            "sequence",
            "predecessorReceiptSha256",
            "route",
            "identity",
            "artifacts",
            "parentInputTransform",
            "activity",
            "terminal",
            "nativeEventLog",
            "receiptSha256",
        }
        body = dict(receipt) if isinstance(receipt, dict) else {}
        if set(body) != expected_receipt_keys:
            failures.append(f"unsupported-receipt-schema:{hop_id}")
        receipt_sha = body.pop("receiptSha256", None)
        if receipt_sha != canonical_sha256(body):
            failures.append(f"receipt-digest-drift:{hop_id}")
            continue
        if not (
            receipt.get("schema") == 1
            and receipt.get("kind") == "parent-derived-native-hop-receipt"
            and receipt.get("authorizationSha256") == authorization_sha
            and receipt.get("runId") == run_id
            and receipt.get("hopId") == hop_id
            and receipt.get("sequence") == index + 1
            and receipt.get("predecessorReceiptSha256")
            == previous_receipt_sha
        ):
            failures.append(f"receipt-lineage-drift:{hop_id}")
        route = receipt.get("route", {})
        if not (
            set(route)
            == {
                "requestedModel",
                "requestedReasoningEffort",
                "hostReportedModel",
                "hostReportedReasoningEffort",
                "hostReportedModelProvider",
                "providerFallbackRequested",
                "providerExecutionRouteTelemetry",
            }
            and
            route.get("requestedModel") == "gpt-5.3-codex-spark"
            and route.get("requestedReasoningEffort") == "low"
            and route.get("hostReportedModel") == "gpt-5.3-codex-spark"
            and route.get("hostReportedReasoningEffort") == "low"
            and route.get("providerFallbackRequested") is False
            and route.get("providerExecutionRouteTelemetry") == "unknown"
        ):
            failures.append(f"route-drift:{hop_id}")
        identity = receipt.get("identity", {})
        thread_id = identity.get("threadId")
        turn_id = identity.get("turnId")
        if not (
            isinstance(thread_id, str)
            and thread_id
            and isinstance(turn_id, str)
            and turn_id
            and isinstance(identity.get("threadStartRequestId"), int)
            and isinstance(identity.get("turnStartRequestId"), int)
            and thread_id not in thread_ids
            and turn_id not in turn_ids
            and identity.get("allNativeEventsMatchIdentity") is True
        ):
            failures.append(f"fresh-identity-drift:{hop_id}")
        else:
            thread_ids.add(thread_id)
            turn_ids.add(turn_id)
        artifacts = receipt.get("artifacts", {})
        if not (
            isinstance(artifacts, dict)
            and set(artifacts)
            == {
                "input",
                "stageContract",
                "turnInputCanonicalSha256",
                "output",
            }
        ):
            failures.append(f"artifact-binding-shape-drift:{hop_id}")
        input_ok = _artifact_binding(
            capture_root,
            artifacts.get("input", {}),
            expected_artifact_id=expected_input_id,
        )
        output_ok = _artifact_binding(
            capture_root,
            artifacts.get("output", {}),
            expected_artifact_id=expected_output_id,
        )
        if not input_ok:
            failures.append(f"input-artifact-drift:{hop_id}")
        if not output_ok:
            failures.append(f"output-artifact-drift:{hop_id}")
        stage_contract_value = _json_binding_value(
            capture_root,
            artifacts.get("stageContract", {}),
        )
        if stage_contract_value is None:
            failures.append(f"stage-contract-drift:{hop_id}")
        elif _contains_private_runtime_key(stage_contract_value):
            failures.append(f"private-oracle-leak:{hop_id}")
        input_canonical = artifacts.get("input", {}).get("canonicalSha256")
        parent_transform = receipt.get("parentInputTransform")
        if index == 0:
            if parent_transform is not None:
                failures.append(f"unexpected-parent-transform:{hop_id}")
        elif not (
            isinstance(parent_transform, dict)
            and set(parent_transform)
            == {
                "kind",
                "predecessorOutputCanonicalSha256",
                "currentInputCanonicalSha256",
                "parentReceiptSha256",
                "contractSha256",
                "contractValid",
            }
            and parent_transform.get("kind")
            in {"controlled-mutation", "recovery-envelope"}
            and parent_transform.get("predecessorOutputCanonicalSha256")
            == previous_output_canonical_sha
            and parent_transform.get("currentInputCanonicalSha256")
            == input_canonical
            and _is_sha256(parent_transform.get("parentReceiptSha256"))
            and _is_sha256(parent_transform.get("contractSha256"))
            and parent_transform.get("contractValid") is True
        ):
            failures.append(f"material-edge-input-mismatch:{hop_id}")
        previous_output_canonical_sha = artifacts.get("output", {}).get(
            "canonicalSha256"
        )
        activity = receipt.get("activity", {})
        item_types = activity.get("itemTypes")
        if not (
            isinstance(item_types, list)
            and set(item_types).issubset(ALLOWED_ITEM_TYPES)
            and activity.get("toolCallCount") == 0
            and activity.get("externalAccessUsedBeyondModelProvider") is False
            and activity.get("agentWritePerformed") is False
        ):
            failures.append(f"unauthorized-activity:{hop_id}")
        terminal = receipt.get("terminal", {})
        if not (
            terminal.get("turnStartedObserved") is True
            and terminal.get("turnCompletedObserved") is True
            and terminal.get("status") == "completed"
            and terminal.get("error") is None
            and terminal.get("outputPersisted") is True
            and terminal.get("runnerTimeout") is False
        ):
            failures.append(f"terminal-evidence-missing:{hop_id}")
        native = receipt.get("nativeEventLog", {})
        try:
            native_path = capture_root / _contained_relative(
                native.get("path"), "native event path"
            )
            messages = _event_messages(native_path)
            thread_request_id = identity.get("threadStartRequestId")
            turn_request_id = identity.get("turnStartRequestId")
            thread_requests = [
                item["message"]
                for item in messages
                if item["direction"] == "client-to-server"
                and item["message"].get("id") == thread_request_id
                and item["message"].get("method") == "thread/start"
            ]
            thread_responses = [
                item["message"]
                for item in messages
                if item["direction"] == "server-to-client"
                and item["message"].get("id") == thread_request_id
                and _find_thread(item["message"]) is not None
            ]
            turn_requests = [
                item["message"]
                for item in messages
                if item["direction"] == "client-to-server"
                and item["message"].get("id") == turn_request_id
                and item["message"].get("method") == "turn/start"
            ]
            turn_responses = [
                item["message"]
                for item in messages
                if item["direction"] == "server-to-client"
                and item["message"].get("id") == turn_request_id
                and isinstance(
                    item["message"].get("result", {}).get("turn"),
                    dict,
                )
            ]
            terminal_messages = [
                item["message"]
                for item in messages
                if item["message"].get("method") == "turn/completed"
                and item["message"].get("params", {}).get("threadId")
                == thread_id
                and item["message"].get("params", {}).get(
                    "turn", {}
                ).get("id")
                == turn_id
            ]
            if not (
                len(thread_requests)
                == len(thread_responses)
                == len(turn_requests)
                == len(turn_responses)
                == len(terminal_messages)
                == 1
            ):
                raise DispatchGateError("native event identity is incomplete")
            thread_params = thread_requests[0].get("params", {})
            native_thread = _find_thread(thread_responses[0])
            turn_params = turn_requests[0].get("params", {})
            native_turn = turn_responses[0]["result"]["turn"]
            turn_input = turn_params.get("input")
            if not (
                isinstance(turn_input, list)
                and len(turn_input) == 1
                and isinstance(turn_input[0], dict)
                and turn_input[0].get("type") == "text"
                and isinstance(turn_input[0].get("text"), str)
            ):
                raise DispatchGateError("turn input surface drifted")
            turn_payload = json.loads(turn_input[0]["text"])
            input_path = capture_root / _contained_relative(
                artifacts["input"]["path"],
                "input artifact path",
            )
            input_value, _ = _load_json(input_path, "input artifact")
            native_item_types = [
                item["message"].get("params", {}).get("item", {}).get("type")
                for item in messages
                if item["message"].get("method") == "item/completed"
                and item["message"].get("params", {}).get("threadId")
                == thread_id
                and item["message"].get("params", {}).get("turnId")
                == turn_id
            ]
            all_thread_start_requests = [
                item
                for item in messages
                if item["direction"] == "client-to-server"
                and item["message"].get("method") == "thread/start"
            ]
            all_turn_start_requests = [
                item
                for item in messages
                if item["direction"] == "client-to-server"
                and item["message"].get("method") == "turn/start"
            ]
            tool_requests = [
                item
                for item in messages
                if item["message"].get("method") == "item/tool/call"
            ]
            if (
                len(all_thread_start_requests) != 1
                or len(all_turn_start_requests) != 1
            ):
                failures.append(f"model-call-count-drift:{hop_id}")
            if tool_requests:
                failures.append(f"unauthorized-tool-use:{hop_id}")
            if _contains_private_runtime_key(turn_payload):
                failures.append(f"private-oracle-leak:{hop_id}")
            native_ok = (
                file_sha256(native_path).lower()
                == str(native.get("rawSha256", "")).lower()
                and len(all_thread_start_requests) == 1
                and len(all_turn_start_requests) == 1
                and tool_requests == []
                and thread_params.get("model") == route["requestedModel"]
                and thread_params.get("allowProviderModelFallback") is False
                and native_thread is not None
                and native_thread.get("id") == thread_id
                and native_thread.get("model") == route["hostReportedModel"]
                and native_thread.get("reasoningEffort")
                == route["hostReportedReasoningEffort"]
                and native_thread.get("modelProvider")
                == route["hostReportedModelProvider"]
                and turn_params.get("threadId") == thread_id
                and turn_params.get("model") == route["requestedModel"]
                and turn_params.get("effort")
                == route["requestedReasoningEffort"]
                and native_turn.get("id") == turn_id
                and native_turn.get("status") in {"inProgress", "completed"}
                and terminal_messages[0]["params"]["turn"].get("status")
                == "completed"
                and turn_payload
                == {
                    "artifact": input_value,
                    "stageContract": stage_contract_value,
                }
                and canonical_sha256(turn_input)
                == artifacts.get("turnInputCanonicalSha256")
                and not _contains_private_runtime_key(turn_payload)
                and native_item_types == activity.get("itemTypes")
                and set(native_item_types).issubset(ALLOWED_ITEM_TYPES)
            )
        except DispatchGateError:
            native_ok = False
        except (json.JSONDecodeError, KeyError, TypeError):
            native_ok = False
        if not native_ok:
            failures.append(f"native-event-evidence-missing:{hop_id}")
        previous_receipt_sha = receipt_sha

    failures = list(dict.fromkeys(failures))
    return {
        "status": (
            "native-hop-receipts-valid-offline"
            if not failures
            else "native-hop-receipts-rejected"
        ),
        "failureCodes": failures,
        "formalLiveEvidenceEligible": False,
        "atomicReservationLedgerVerified": False,
        "providerExecutionRouteTelemetry": "unknown",
        "validatedReceiptCount": (
            len(receipt_list) if not failures else 0
        ),
        "claimBoundary": {
            "liveDispatchAuthorizedByThisValidator": False,
            "providerBackendActualRouteProved": False,
            "hiddenTransformObserved": False,
            "formalCohortRepetitionAccepted": False,
            "endToEndProcessFidelityProved": False,
        },
    }
