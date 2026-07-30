#!/usr/bin/env python3
"""Reopen and evaluate a zero-model seven-stage lifecycle capture."""

from __future__ import annotations

import argparse
import json
import re
from copy import deepcopy
from pathlib import Path
from typing import Any

try:
    from .run_human_ai_collaboration_software_lifecycle_thin_slice_calibration import (
        CAPTURE_NAME,
        PROTOCOL_PATH,
        canonical_bytes,
        canonical_sha256,
        file_sha256,
        self_hash,
    )
    from .validate_human_ai_collaboration_software_lifecycle_thin_slice_protocol import (
        validate_protocol,
    )
    from .evaluate_software_lifecycle_domain_suboracles import (
        DOMAIN_SUBORACLE_ARTIFACT_ID,
        build_domain_suboracle_pack,
        stage_suboracle_bindings,
    )
except ImportError:  # pragma: no cover - direct script execution
    from run_human_ai_collaboration_software_lifecycle_thin_slice_calibration import (
        CAPTURE_NAME,
        PROTOCOL_PATH,
        canonical_bytes,
        canonical_sha256,
        file_sha256,
        self_hash,
    )
    from validate_human_ai_collaboration_software_lifecycle_thin_slice_protocol import (
        validate_protocol,
    )
    from evaluate_software_lifecycle_domain_suboracles import (
        DOMAIN_SUBORACLE_ARTIFACT_ID,
        build_domain_suboracle_pack,
        stage_suboracle_bindings,
    )


ROOT = Path(__file__).resolve().parent.parent
SCHEMA_KEYS = {
    "stageEnvelopeSchema": "stage-envelopes",
    "acceptedInvariantLedgerSchema": "accepted-invariant-ledgers",
    "humanAuthorityReceiptSchema": "authority-receipts",
}
STAGE_ASSERTION_RULES = {
    "requirements-domain": {
        "sourceBound": True,
        "authorityPromotedByAgent": False,
        "materialUnknownsResolvedOrBlocked": True,
    },
    "architecture-design": {
        "requirementsDigestMatched": True,
        "securityObservabilityRollbackSurfacesPresent": True,
        "irreversibleCommitmentClaimed": False,
    },
    "implementation-tdd": {
        "validRedObservedBeforeProductionMutation": True,
        "visibleAndHiddenOraclePassed": True,
        "survivingMutantCount": 0,
        "privateOracleExposed": False,
        "effectiveSandboxObserved": True,
    },
    "independent-review-test-security": {
        "reviewerDistinctFromProducer": True,
        "exactArtifactDigestMatched": True,
        "independentReexecutionObserved": True,
        "unresolvedHighFinding": False,
    },
    "release-rollback-gating": {
        "rollbackExercised": True,
        "postRollbackIntegrityPassed": True,
        "realGitCiOrDeploymentAttempted": False,
    },
    "observation-incident-handling": {
        "releaseRuntimeIdentityMatched": True,
        "detectionAndRecoveryEvidencePresent": True,
        "faultEscapedDisposableScope": False,
        "unknownObservationCoercedToZero": False,
    },
    "maintenance-evolution": {
        "distinctConsumerStatesPreserved": True,
        "unknownTelemetryCoercedToZero": False,
        "removalOrProductionMigrationClaimed": False,
        "retentionRollbackOwnerAndRecheckTriggerPresent": True,
    },
}


def _safe_path(capture_root: Path, value: Any) -> Path | None:
    if not isinstance(value, str) or not value:
        return None
    relative = Path(value)
    if relative.is_absolute() or ".." in relative.parts:
        return None
    path = (capture_root / relative).resolve()
    if not path.is_relative_to(capture_root.resolve()):
        return None
    return path


def _resolve_ref(schema_root: dict[str, Any], reference: str) -> Any:
    if not reference.startswith("#/"):
        raise RuntimeError(f"external JSON Schema ref unsupported: {reference}")
    value: Any = schema_root
    for token in reference[2:].split("/"):
        token = token.replace("~1", "/").replace("~0", "~")
        value = value[token]
    return value


def _type_matches(value: Any, expected: str) -> bool:
    if expected == "null":
        return value is None
    if expected == "object":
        return isinstance(value, dict)
    if expected == "array":
        return isinstance(value, list)
    if expected == "string":
        return isinstance(value, str)
    if expected == "boolean":
        return isinstance(value, bool)
    if expected == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if expected == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    return False


def validate_schema_instance(
    value: Any,
    schema: Any,
    *,
    schema_root: dict[str, Any] | None = None,
    location: str = "$",
) -> None:
    if schema is True:
        return
    if schema is False or not isinstance(schema, dict):
        raise RuntimeError(f"schema rejected value at {location}")
    root = schema if schema_root is None else schema_root
    if "$ref" in schema:
        validate_schema_instance(
            value,
            _resolve_ref(root, schema["$ref"]),
            schema_root=root,
            location=location,
        )
        return
    if "anyOf" in schema:
        errors = []
        for candidate in schema["anyOf"]:
            try:
                validate_schema_instance(
                    value,
                    candidate,
                    schema_root=root,
                    location=location,
                )
                return
            except RuntimeError as error:
                errors.append(str(error))
        raise RuntimeError(f"schema anyOf failed at {location}: {errors}")
    if "const" in schema and value != schema["const"]:
        raise RuntimeError(f"schema const failed at {location}")
    if "enum" in schema and value not in schema["enum"]:
        raise RuntimeError(f"schema enum failed at {location}")
    expected_type = schema.get("type")
    if expected_type is not None:
        candidates = (
            expected_type if isinstance(expected_type, list) else [expected_type]
        )
        if not any(_type_matches(value, candidate) for candidate in candidates):
            raise RuntimeError(f"schema type failed at {location}")
    if isinstance(value, dict):
        required = schema.get("required", [])
        if any(key not in value for key in required):
            raise RuntimeError(f"schema required field missing at {location}")
        properties = schema.get("properties", {})
        if schema.get("additionalProperties") is False:
            unknown = set(value) - set(properties)
            if unknown:
                raise RuntimeError(
                    f"schema additional property at {location}: {sorted(unknown)}"
                )
        for key, child in value.items():
            if key in properties:
                validate_schema_instance(
                    child,
                    properties[key],
                    schema_root=root,
                    location=f"{location}/{key}",
                )
    if isinstance(value, list):
        if "minItems" in schema and len(value) < schema["minItems"]:
            raise RuntimeError(f"schema minItems failed at {location}")
        if "maxItems" in schema and len(value) > schema["maxItems"]:
            raise RuntimeError(f"schema maxItems failed at {location}")
        if schema.get("uniqueItems") is True:
            encoded = [canonical_bytes(item) for item in value]
            if len(encoded) != len(set(encoded)):
                raise RuntimeError(f"schema uniqueItems failed at {location}")
        if "items" in schema:
            for index, child in enumerate(value):
                validate_schema_instance(
                    child,
                    schema["items"],
                    schema_root=root,
                    location=f"{location}/{index}",
                )
    if isinstance(value, str):
        if "minLength" in schema and len(value) < schema["minLength"]:
            raise RuntimeError(f"schema minLength failed at {location}")
        if "pattern" in schema and re.fullmatch(schema["pattern"], value) is None:
            raise RuntimeError(f"schema pattern failed at {location}")
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if "minimum" in schema and value < schema["minimum"]:
            raise RuntimeError(f"schema minimum failed at {location}")


def _read_index(
    capture: dict[str, Any],
    *,
    capture_root: Path,
) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]], list[str]]:
    values: dict[str, dict[str, Any]] = {}
    rows: dict[str, dict[str, Any]] = {}
    failures: list[str] = []
    index = capture.get("rawArtifactIndex")
    if not isinstance(index, list) or not index:
        return {}, {}, ["raw-artifact-index-missing"]
    for row in index:
        if not isinstance(row, dict) or set(row) != {
            "artifactId",
            "path",
            "bytes",
            "rawSha256",
            "canonicalSha256",
            "repositoryLocalAuditPath",
        }:
            failures.append("raw-artifact-index-shape")
            continue
        artifact_id = row.get("artifactId")
        if (
            not isinstance(artifact_id, str)
            or not artifact_id
            or artifact_id in values
        ):
            failures.append("raw-artifact-id-duplicate-or-invalid")
            continue
        path = _safe_path(capture_root, row.get("path"))
        if path is None or not path.is_file() or path.is_symlink():
            failures.append("raw-artifact-path-or-durability-failure")
            continue
        raw = path.read_bytes()
        if (
            row.get("bytes") != len(raw)
            or row.get("rawSha256") != file_sha256(path)
            or row.get("repositoryLocalAuditPath") is not True
        ):
            failures.append("raw-artifact-byte-binding-mismatch")
            continue
        try:
            value = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            failures.append("raw-artifact-parse-failure")
            continue
        if (
            not isinstance(value, dict)
            or row.get("canonicalSha256") != canonical_sha256(value)
        ):
            failures.append("raw-artifact-canonical-binding-mismatch")
            continue
        values[artifact_id] = value
        rows[artifact_id] = row
    return values, rows, failures


def _artifact_descriptor_matches(
    descriptor: dict[str, Any],
    *,
    values: dict[str, dict[str, Any]],
    rows: dict[str, dict[str, Any]],
) -> bool:
    artifact_id = descriptor.get("artifactId")
    row = rows.get(artifact_id)
    value = values.get(artifact_id)
    return (
        isinstance(row, dict)
        and isinstance(value, dict)
        and descriptor.get("relativePath") == row.get("path")
        and descriptor.get("byteLength") == row.get("bytes")
        and descriptor.get("byteSha256") == row.get("rawSha256")
        and descriptor.get("canonicalJsonSha256")
        == row.get("canonicalSha256")
    )


def _dedupe(values: list[str]) -> list[str]:
    return list(dict.fromkeys(values))


def evaluate_capture(
    capture: dict[str, Any],
    *,
    capture_root: Path,
    root: Path = ROOT,
) -> dict[str, Any]:
    failures: list[str] = []
    capture_root = capture_root.resolve()
    protocol_path = root / PROTOCOL_PATH
    protocol = json.loads(protocol_path.read_text(encoding="utf-8"))
    try:
        validate_protocol(protocol, root=root)
    except RuntimeError:
        failures.append("protocol-invalid")
    protocol_binding = capture.get("protocolBinding")
    if (
        not isinstance(protocol_binding, dict)
        or protocol_binding.get("path") != PROTOCOL_PATH
        or protocol_binding.get("fileSha256") != file_sha256(protocol_path)
        or protocol_binding.get("canonicalSha256")
        != canonical_sha256(protocol)
    ):
        failures.append("protocol-binding-drift")
    if (
        capture.get("schema") != 1
        or capture.get("kind")
        != "software-lifecycle-thin-slice-zero-model-capture"
        or capture.get("mode") != "zero-model-scripted-calibration"
        or capture.get("eligibleForFormalLiveEvidence") is not False
    ):
        failures.append("capture-identity-drift")
    execution = capture.get("execution")
    if (
        not isinstance(execution, dict)
        or execution
        != {
            "agentDispatchCount": 0,
            "modelCallCount": 0,
            "actualRouteObserved": False,
            "dispatchAuthorized": False,
            "networkAccessUsed": False,
            "gitMutationUsed": False,
            "externalWriteUsed": False,
        }
    ):
        failures.append("zero-model-execution-boundary-drift")
    if capture.get("claimBoundary") != protocol.get("claimBoundary"):
        failures.append("capture-claim-boundary-drift")

    values, rows, index_failures = _read_index(
        capture,
        capture_root=capture_root,
    )
    failures.extend(index_failures)
    if index_failures:
        return {
            "status": "invalid",
            "failureCodes": _dedupe(failures),
            "formalLiveEvidenceEligible": False,
        }

    domain_suboracle_id = capture.get(
        "domainSuboraclePackArtifactId"
    )
    domain_suboracle_pack = values.get(domain_suboracle_id)
    expected_domain_suboracle_pack = build_domain_suboracle_pack(
        root=root
    )
    if (
        domain_suboracle_id != DOMAIN_SUBORACLE_ARTIFACT_ID
        or domain_suboracle_pack != expected_domain_suboracle_pack
        or domain_suboracle_pack.get("allPositiveAccepted") is not True
        or domain_suboracle_pack.get(
            "allNegativeControlsRejected"
        )
        is not True
        or any(
            domain_suboracle_pack.get("claimBoundary", {}).values()
        )
    ):
        failures.append("domain-suboracle-pack-drift")

    schema_documents = {
        key: json.loads(
            (
                root / protocol["contractBindings"][key]["path"]
            ).read_text(encoding="utf-8")
        )
        for key in SCHEMA_KEYS
    }
    receipt_ids = capture.get("authorityReceiptIds")
    envelope_ids = capture.get("stageEnvelopeIds")
    ledger_ids = capture.get("acceptedInvariantLedgerIds")
    if (
        not isinstance(receipt_ids, list)
        or len(receipt_ids) != 8
        or len(receipt_ids) != len(set(receipt_ids))
        or not isinstance(envelope_ids, list)
        or len(envelope_ids) != 7
        or len(envelope_ids) != len(set(envelope_ids))
        or not isinstance(ledger_ids, list)
        or len(ledger_ids) != 8
        or len(ledger_ids) != len(set(ledger_ids))
    ):
        failures.append("capture-lifecycle-set-drift")
        return {
            "status": "invalid",
            "failureCodes": _dedupe(failures),
            "formalLiveEvidenceEligible": False,
        }
    receipts = [values.get(item) for item in receipt_ids]
    envelopes = [values.get(item) for item in envelope_ids]
    ledgers = [values.get(item) for item in ledger_ids]
    if not all(isinstance(item, dict) for item in receipts + envelopes + ledgers):
        failures.append("capture-lifecycle-artifact-missing")
        return {
            "status": "invalid",
            "failureCodes": _dedupe(failures),
            "formalLiveEvidenceEligible": False,
        }

    for label, items, schema_key in (
        ("receipt", receipts, "humanAuthorityReceiptSchema"),
        ("envelope", envelopes, "stageEnvelopeSchema"),
        ("ledger", ledgers, "acceptedInvariantLedgerSchema"),
    ):
        for index, value in enumerate(items):
            try:
                validate_schema_instance(
                    value,
                    schema_documents[schema_key],
                    location=f"{label}[{index}]",
                )
            except RuntimeError:
                failures.append(f"{label}-schema-invalid")

    run_id = capture.get("runId")
    gate_ids = [gate["gateId"] for gate in protocol["gates"]]
    receipt_by_gate = {
        receipt.get("gateId"): receipt for receipt in receipts
    }
    if set(receipt_by_gate) != set(gate_ids):
        failures.append("authority-receipt-gate-set-drift")
    for gate, receipt in zip(protocol["gates"], receipts):
        if (
            receipt.get("runId") != run_id
            or receipt.get("gateId") != gate["gateId"]
            or receipt.get("sequence") != gate["sequence"]
            or receipt.get("decision") != "approve"
            or receipt.get("decisionClass") != gate["decisionClass"]
            or receipt.get("simulated") is not True
            or receipt.get("singleUse") is not True
            or receipt.get("issuer", {}).get("evidenceClass")
            != "synthetic-calibration-authority"
            or receipt.get("receiptSha256")
            != self_hash(receipt, "receiptSha256")
        ):
            failures.append("authority-receipt-invalid")

    source_id = capture.get("sourceArtifactId")
    source = values.get(source_id)
    source_row = rows.get(source_id)
    if (
        not isinstance(source, dict)
        or not isinstance(source_row, dict)
        or source.get("kind")
        != "software-lifecycle-frozen-source-bundle"
    ):
        failures.append("source-bundle-invalid")
        source_sha256 = None
    else:
        source_sha256 = canonical_sha256(source)

    previous_envelope_sha256: str | None = None
    previous_output_descriptor: dict[str, Any] | None = None
    for index, (stage, envelope) in enumerate(
        zip(protocol["stages"], envelopes)
    ):
        output_bindings = envelope.get("outputBindings", [])
        input_bindings = envelope.get("inputBindings", [])
        source_bindings = envelope.get("sourceBindings", [])
        if (
            envelope.get("runId") != run_id
            or envelope.get("stage")
            != {
                "stageId": stage["stageId"],
                "sequence": stage["sequence"],
                "stageClass": stage["stageClass"],
            }
            or envelope.get("role") != stage["role"]
            or envelope.get("independenceClass")
            != stage["independenceClass"]
            or envelope.get("protocolBinding")
            != {
                "protocolId": protocol["id"],
                "protocolCanonicalSha256": canonical_sha256(protocol),
                "stageDefinitionCanonicalSha256": canonical_sha256(stage),
            }
            or envelope.get("sections") != stage["requiredSections"]
            or envelope.get("parentEvaluation", {}).get("stageValidators")
            != stage["stageValidators"]
            or envelope.get("envelopeSha256")
            != self_hash(envelope, "envelopeSha256")
        ):
            failures.append("stage-envelope-contract-drift")
        if envelope.get("lineage", {}).get(
            "primaryPredecessorEnvelopeSha256"
        ) != previous_envelope_sha256:
            failures.append("stage-envelope-predecessor-drift")
        if (
            not isinstance(source_bindings, list)
            or len(source_bindings) != 1
            or source_bindings[0].get("artifactId") != source_id
            or source_bindings[0].get("authorityClass")
            != "accepted-truth-source"
            or not _artifact_descriptor_matches(
                source_bindings[0],
                values=values,
                rows=rows,
            )
        ):
            failures.append("stage-source-rebinding-invalid")
        if (
            not isinstance(input_bindings, list)
            or [item.get("ordinal") for item in input_bindings]
            != list(range(1, len(input_bindings) + 1))
            or envelope.get("inputSetCanonicalSha256")
            != canonical_sha256(input_bindings)
            or not all(
                _artifact_descriptor_matches(
                    item,
                    values=values,
                    rows=rows,
                )
                for item in input_bindings
            )
        ):
            failures.append("stage-input-binding-invalid")
        if previous_output_descriptor is not None and not any(
            item.get("artifactId")
            == previous_output_descriptor.get("artifactId")
            and item.get("canonicalJsonSha256")
            == previous_output_descriptor.get("canonicalJsonSha256")
            for item in input_bindings
        ):
            failures.append("stage-primary-output-input-linkage-missing")
        if (
            not isinstance(output_bindings, list)
            or len(output_bindings) != 1
            or envelope.get("outputSetCanonicalSha256")
            != canonical_sha256(output_bindings)
            or not _artifact_descriptor_matches(
                output_bindings[0],
                values=values,
                rows=rows,
            )
        ):
            failures.append("stage-output-binding-invalid")
            output = None
        else:
            output = values[output_bindings[0]["artifactId"]]
            if output.get("sections") != {
                section: {"status": "synthetic-calibration-present"}
                for section in stage["requiredSections"]
            }:
                failures.append("stage-output-section-drift")
            if output.get("semanticAssertions") != STAGE_ASSERTION_RULES[
                stage["stageClass"]
            ]:
                failures.append(
                    f"stage-semantic-falsifier:{stage['stageClass']}"
                )
            if output.get(
                "domainSuboracleBindings"
            ) != stage_suboracle_bindings(
                stage["stageClass"],
                expected_domain_suboracle_pack,
            ):
                failures.append(
                    f"stage-domain-suboracle-binding-drift:"
                    f"{stage['stageClass']}"
                )
        required_receipt_hashes = {
            receipt_by_gate[gate_id]["receiptSha256"]
            for gate_id in stage["requiredAuthorityGates"]
            if gate_id in receipt_by_gate
        }
        if set(envelope.get("humanAuthorityReceiptBindings", [])) != (
            required_receipt_hashes
        ):
            failures.append("stage-authority-receipt-binding-invalid")
        if not set(envelope.get("changedFiles", [])) <= set(
            envelope.get("allowedMutableFiles", [])
        ):
            failures.append("stage-changed-file-outside-allowlist")
        if envelope.get("execution") != {
            "mode": "zero-model-scripted-calibration",
            "agentDispatchCount": 0,
            "modelCallCount": 0,
            "actualRouteObserved": False,
            "networkAccessUsed": False,
            "gitMutationUsed": False,
            "externalWriteUsed": False,
        }:
            failures.append("stage-zero-model-boundary-drift")
        if any(envelope.get("claimBoundary", {}).values()):
            failures.append("stage-claim-boundary-promoted")
        previous_envelope_sha256 = envelope.get("envelopeSha256")
        previous_output_descriptor = (
            output_bindings[0] if output_bindings else None
        )

    used_receipt_hashes: set[str] = set()
    previous_ledger: dict[str, Any] | None = None
    previous_history: list[dict[str, Any]] = []
    source_digest = source_sha256
    for index, ledger in enumerate(ledgers):
        if (
            ledger.get("runId") != run_id
            or ledger.get("protocolCanonicalSha256")
            != canonical_sha256(protocol)
            or ledger.get("sourceRegistryCanonicalSha256") != source_digest
            or ledger.get("ledgerSha256")
            != self_hash(ledger, "ledgerSha256")
            or ledger.get("previousLedgerSha256")
            != (
                None
                if previous_ledger is None
                else previous_ledger.get("ledgerSha256")
            )
        ):
            failures.append("accepted-ledger-binding-invalid")
        history = ledger.get("transitionHistory", [])
        if history[: len(previous_history)] != previous_history:
            failures.append("accepted-ledger-history-not-append-only")
        active_ids = [
            item.get("invariantId")
            for item in ledger.get("activeInvariants", [])
        ]
        if len(active_ids) != len(set(active_ids)):
            failures.append("accepted-ledger-duplicate-invariant")
        for invariant in ledger.get("activeInvariants", []):
            if invariant.get("claimCanonicalSha256") != canonical_sha256(
                invariant.get("claim")
            ):
                failures.append("accepted-ledger-claim-hash-invalid")
            basis = invariant.get("currentAcceptanceBasis", {})
            if basis.get("kind") == "source":
                if basis.get("bindingSha256") != source_digest:
                    failures.append("unregistered-source-promoted-truth")
            elif basis.get("kind") == "human-authority-receipt":
                if basis.get("bindingSha256") not in {
                    receipt.get("receiptSha256") for receipt in receipts
                }:
                    failures.append("agent-proposal-promoted-without-basis")
        for transition in history[len(previous_history) :]:
            if transition.get("transitionCanonicalSha256") != self_hash(
                transition,
                "transitionCanonicalSha256",
            ):
                failures.append("accepted-ledger-transition-hash-invalid")
            for change in transition.get("changes", []):
                basis = change.get("basis", {})
                if basis.get("kind") == "source":
                    if basis.get("bindingSha256") != source_digest:
                        failures.append("unregistered-source-promoted-truth")
                elif basis.get("kind") == "human-authority-receipt":
                    digest = basis.get("bindingSha256")
                    if digest in used_receipt_hashes:
                        failures.append("human-authority-receipt-replayed")
                    used_receipt_hashes.add(digest)
                    matching = next(
                        (
                            receipt
                            for receipt in receipts
                            if receipt.get("receiptSha256") == digest
                        ),
                        None,
                    )
                    if (
                        matching is None
                        or change.get("changeId")
                        not in matching.get("allowedChangeIds", [])
                        or matching.get("proposalArtifactCanonicalSha256")
                        != transition.get(
                            "proposalArtifactCanonicalSha256"
                        )
                        or matching.get("beforeAcceptedLedgerSha256")
                        != transition.get("beforeLedgerSha256")
                    ):
                        failures.append(
                            "human-authority-receipt-scope-mismatch"
                        )
        summary = ledger.get("summary", {})
        all_changes = [
            change
            for transition in history
            for change in transition.get("changes", [])
        ]
        if summary != {
            "activeInvariantCount": len(ledger.get("activeInvariants", [])),
            "retiredInvariantCount": len(
                ledger.get("retiredInvariantIds", [])
            ),
            "acceptedChangeCount": len(all_changes),
            "sourceBackedChangeCount": sum(
                change.get("basis", {}).get("kind") == "source"
                for change in all_changes
            ),
            "humanReceiptBackedChangeCount": sum(
                change.get("basis", {}).get("kind")
                == "human-authority-receipt"
                for change in all_changes
            ),
        }:
            failures.append("accepted-ledger-summary-mismatch")
        previous_ledger = ledger
        previous_history = history

    for index, envelope in enumerate(envelopes):
        before_ledger = ledgers[index]
        after_ledger = ledgers[index + 1]
        transition = envelope.get("truthTransition", {})
        if (
            envelope.get("lineage", {}).get(
                "previousAcceptedLedgerSha256"
            )
            != before_ledger.get("ledgerSha256")
            or transition.get("beforeAcceptedLedgerSha256")
            != before_ledger.get("ledgerSha256")
            or transition.get("afterAcceptedLedgerSha256")
            != after_ledger.get("ledgerSha256")
        ):
            failures.append("stage-ledger-lineage-drift")

    failures = _dedupe(failures)
    return {
        "status": "valid-calibration-only" if not failures else "invalid",
        "failureCodes": failures,
        "stageCount": len(envelopes),
        "gateCount": len(receipts),
        "ledgerCount": len(ledgers),
        "formalLiveEvidenceEligible": False,
        "agentDispatchCount": execution.get("agentDispatchCount", 0)
        if isinstance(execution, dict)
        else None,
        "modelCallCount": execution.get("modelCallCount", 0)
        if isinstance(execution, dict)
        else None,
        "claimBoundary": deepcopy(protocol["claimBoundary"]),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--capture-root", type=Path, required=True)
    arguments = parser.parse_args()
    capture_path = arguments.capture_root / CAPTURE_NAME
    capture = json.loads(capture_path.read_text(encoding="utf-8"))
    result = evaluate_capture(
        capture,
        capture_root=arguments.capture_root,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"] == "valid-calibration-only" else 1


if __name__ == "__main__":
    raise SystemExit(main())
