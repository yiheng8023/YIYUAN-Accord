#!/usr/bin/env python3
"""Build one durable, zero-model seven-stage lifecycle calibration capture."""

from __future__ import annotations

import argparse
import hashlib
import json
from copy import deepcopy
from pathlib import Path
from typing import Any

try:
    from .evaluate_software_lifecycle_domain_suboracles import (
        DOMAIN_SUBORACLE_ARTIFACT_ID,
        build_domain_suboracle_pack,
        stage_suboracle_bindings,
    )
except ImportError:  # pragma: no cover - direct script execution
    from evaluate_software_lifecycle_domain_suboracles import (
        DOMAIN_SUBORACLE_ARTIFACT_ID,
        build_domain_suboracle_pack,
        stage_suboracle_bindings,
    )


ROOT = Path(__file__).resolve().parent.parent
PROTOCOL_PATH = (
    "registry/"
    "human-ai-collaboration-software-lifecycle-thin-slice-protocol-"
    "2026-07-27.json"
)
CAPTURE_NAME = "LIFECYCLE-CAPTURE.json"
ZERO = "0" * 64


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


def self_hash(value: dict[str, Any], field: str) -> str:
    candidate = deepcopy(value)
    candidate.pop(field, None)
    return canonical_sha256(candidate)


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def _descriptor(
    *,
    artifact_id: str,
    role: str,
    relative_path: str,
    path: Path,
    value: dict[str, Any],
    producer_class: str,
    authority_class: str,
    ordinal: int,
) -> dict[str, Any]:
    return {
        "ordinal": ordinal,
        "artifactId": artifact_id,
        "role": role,
        "mediaType": "application/json",
        "relativePath": relative_path,
        "byteLength": len(path.read_bytes()),
        "byteSha256": file_sha256(path),
        "canonicalJsonSha256": canonical_sha256(value),
        "producerClass": producer_class,
        "authorityClass": authority_class,
    }


def _stage_assertions(stage_class: str) -> dict[str, Any]:
    assertions: dict[str, dict[str, Any]] = {
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
    return assertions[stage_class]


def _artifact(
    *,
    artifact_id: str,
    stage_id: str,
    required_sections: list[str],
    accepted_invariant_ids: list[str],
    stage_class: str,
    domain_suboracle_bindings: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "schema": 1,
        "kind": "software-lifecycle-stage-output",
        "artifactId": artifact_id,
        "stageId": stage_id,
        "sections": {
            section: {"status": "synthetic-calibration-present"}
            for section in required_sections
        },
        "acceptedInvariantIdsObserved": list(accepted_invariant_ids),
        "semanticAssertions": _stage_assertions(stage_class),
        "domainSuboracleBindings": deepcopy(
            domain_suboracle_bindings
        ),
        "provenanceIds": ["source.lifecycle-fixture"],
        "assumptionIds": [],
        "detectedLossIds": [],
    }


def _receipt(
    *,
    run_id: str,
    gate: dict[str, Any],
    stage_id: str | None,
    proposal_sha256: str | None,
    before_ledger_sha256: str | None,
    allowed_change_ids: list[str],
    artifact_ids: list[str],
) -> dict[str, Any]:
    receipt = {
        "schema": 1,
        "kind": "software-lifecycle-human-authority-receipt",
        "receiptId": f"{run_id}-{gate['gateId']}",
        "runId": run_id,
        "gateId": gate["gateId"],
        "stageId": stage_id,
        "sequence": gate["sequence"],
        "decision": "approve",
        "decisionClass": gate["decisionClass"],
        "proposalArtifactCanonicalSha256": proposal_sha256,
        "beforeAcceptedLedgerSha256": before_ledger_sha256,
        "allowedChangeIds": allowed_change_ids,
        "rejectedChangeIds": [],
        "scope": {
            "stageIds": [] if stage_id is None else [stage_id],
            "artifactIds": artifact_ids,
            "actions": list(gate["mayAuthorize"]),
        },
        "inputArtifactDigests": (
            [] if proposal_sha256 is None else [proposal_sha256]
        ),
        "conditions": ["synthetic-zero-model-calibration-only"],
        "issuer": {
            "subjectId": "synthetic-calibration-authority",
            "accountableRole": gate["authorityRole"],
            "evidenceClass": "synthetic-calibration-authority",
        },
        "issuedAt": f"2026-07-27T00:00:{gate['sequence']:02d}+00:00",
        "expiresAt": None,
        "singleUse": True,
        "simulated": True,
        "receiptSha256": ZERO,
    }
    receipt["receiptSha256"] = self_hash(receipt, "receiptSha256")
    return receipt


def _invariant(
    *,
    invariant_id: str,
    sequence: int,
    claim: dict[str, Any],
    basis_kind: str,
    basis_sha256: str,
    source_pointer: dict[str, Any] | None,
) -> dict[str, Any]:
    return {
        "invariantId": invariant_id,
        "version": 1,
        "status": "active",
        "claim": claim,
        "claimCanonicalSha256": canonical_sha256(claim),
        "weight": 1,
        "sourcePointers": (
            [] if source_pointer is None else [source_pointer]
        ),
        "firstAcceptedSequence": max(sequence, 1),
        "lastChangedSequence": max(sequence, 1),
        "currentAcceptanceBasis": {
            "kind": basis_kind,
            "bindingSha256": basis_sha256,
        },
    }


def _ledger(
    *,
    run_id: str,
    protocol_sha256: str,
    source_registry_sha256: str,
    stage_id: str,
    sequence: int,
    previous_ledger_sha256: str | None,
    active_invariants: list[dict[str, Any]],
    history: list[dict[str, Any]],
    ledger_index: int | None = None,
) -> dict[str, Any]:
    source_count = sum(
        change["basis"]["kind"] == "source"
        for transition in history
        for change in transition["changes"]
    )
    receipt_count = sum(
        change["basis"]["kind"] == "human-authority-receipt"
        for transition in history
        for change in transition["changes"]
    )
    ledger = {
        "schema": 1,
        "kind": "cumulative-accepted-invariant-ledger",
        "ledgerId": (
            f"{run_id}-ledger-"
            f"{(sequence if ledger_index is None else ledger_index):02d}"
        ),
        "runId": run_id,
        "protocolCanonicalSha256": protocol_sha256,
        "sourceRegistryCanonicalSha256": source_registry_sha256,
        "asOfStageId": stage_id,
        "asOfSequence": max(sequence, 1),
        "previousLedgerSha256": previous_ledger_sha256,
        "activeInvariants": deepcopy(active_invariants),
        "retiredInvariantIds": [],
        "transitionHistory": deepcopy(history),
        "summary": {
            "activeInvariantCount": len(active_invariants),
            "retiredInvariantCount": 0,
            "acceptedChangeCount": source_count + receipt_count,
            "sourceBackedChangeCount": source_count,
            "humanReceiptBackedChangeCount": receipt_count,
        },
        "producer": "parent-evaluator",
        "ledgerSha256": ZERO,
    }
    ledger["ledgerSha256"] = self_hash(ledger, "ledgerSha256")
    return ledger


def _transition(
    *,
    transition_id: str,
    stage_id: str,
    sequence: int,
    before_ledger_sha256: str | None,
    proposal_sha256: str,
    invariant: dict[str, Any],
    basis_kind: str,
    basis_sha256: str,
) -> dict[str, Any]:
    change = {
        "changeId": transition_id,
        "operation": "add",
        "invariantId": invariant["invariantId"],
        "beforeVersion": None,
        "afterVersion": 1,
        "beforeClaimCanonicalSha256": None,
        "afterClaimCanonicalSha256": invariant["claimCanonicalSha256"],
        "basis": {
            "kind": basis_kind,
            "bindingSha256": basis_sha256,
        },
    }
    transition = {
        "transitionId": transition_id,
        "stageId": stage_id,
        "sequence": max(sequence, 1),
        "beforeLedgerSha256": before_ledger_sha256,
        "proposalArtifactCanonicalSha256": proposal_sha256,
        "decision": (
            "accepted-source-change"
            if basis_kind == "source"
            else "accepted-human-authority-change"
        ),
        "changes": [change],
        "transitionCanonicalSha256": ZERO,
    }
    transition["transitionCanonicalSha256"] = self_hash(
        transition,
        "transitionCanonicalSha256",
    )
    return transition


def build_calibration_capture(
    output: Path,
    *,
    root: Path = ROOT,
    run_id: str = "SE-E2E-THIN-01-ZERO-001",
) -> dict[str, Any]:
    output = output.resolve()
    if output.exists():
        if not output.is_dir() or any(output.iterdir()):
            raise RuntimeError("calibration output must be an empty directory")
    else:
        output.mkdir(parents=True)
    protocol_path = root / PROTOCOL_PATH
    protocol = json.loads(protocol_path.read_text(encoding="utf-8"))
    protocol_sha256 = canonical_sha256(protocol)

    source = {
        "schema": 1,
        "kind": "software-lifecycle-frozen-source-bundle",
        "artifactId": "SOURCE-BUNDLE",
        "fixtureId": "fixture.capped-backoff-lifecycle-thin-slice-v1",
        "goal": "Implement and evaluate one bounded capped-backoff change.",
        "nonGoals": [
            "real Git mutation",
            "remote CI",
            "deployment",
            "MCP lifecycle proof",
            "candidate Skill comparison",
        ],
        "acceptedInvariants": [
            {
                "invariantId": "inv.source-goal",
                "claim": {"goalRemainsSourceBound": True},
            },
            {
                "invariantId": "inv.no-live-side-effects",
                "claim": {"liveSideEffectsAuthorized": False},
            },
        ],
    }
    source_relative = "RAW-ARTIFACTS/SOURCE-BUNDLE.json"
    source_path = output / source_relative
    _write_json(source_path, source)
    source_descriptor = _descriptor(
        artifact_id="SOURCE-BUNDLE",
        role="frozen-source-bundle",
        relative_path=source_relative,
        path=source_path,
        value=source,
        producer_class="frozen-source",
        authority_class="accepted-truth-source",
        ordinal=1,
    )
    source_sha256 = canonical_sha256(source)
    source_pointer_template = {
        "artifactId": "SOURCE-BUNDLE",
        "artifactCanonicalSha256": source_sha256,
        "jsonPointer": "/acceptedInvariants",
    }

    raw_items: list[tuple[str, str, dict[str, Any]]] = [
        ("SOURCE-BUNDLE", source_relative, source)
    ]
    domain_suboracle_pack = build_domain_suboracle_pack(root=root)
    domain_suboracle_relative = (
        "RAW-ARTIFACTS/DOMAIN-SUBORACLE-PACK.json"
    )
    _write_json(
        output / domain_suboracle_relative,
        domain_suboracle_pack,
    )
    raw_items.append(
        (
            DOMAIN_SUBORACLE_ARTIFACT_ID,
            domain_suboracle_relative,
            domain_suboracle_pack,
        )
    )
    active_invariants: list[dict[str, Any]] = []
    history: list[dict[str, Any]] = []
    for item in source["acceptedInvariants"]:
        invariant = _invariant(
            invariant_id=item["invariantId"],
            sequence=1,
            claim=item["claim"],
            basis_kind="source",
            basis_sha256=source_sha256,
            source_pointer=source_pointer_template,
        )
        active_invariants.append(invariant)
        history.append(
            _transition(
                transition_id=f"source-add-{item['invariantId']}",
                stage_id="SOURCE",
                sequence=1,
                before_ledger_sha256=None,
                proposal_sha256=source_sha256,
                invariant=invariant,
                basis_kind="source",
                basis_sha256=source_sha256,
            )
        )
    initial_ledger = _ledger(
        run_id=run_id,
        protocol_sha256=protocol_sha256,
        source_registry_sha256=source_sha256,
        stage_id="SOURCE",
        sequence=1,
        previous_ledger_sha256=None,
        active_invariants=active_invariants,
        history=history,
        ledger_index=0,
    )
    ledger_relative = "ACCEPTED-INVARIANT-LEDGERS/ledger-00.json"
    _write_json(output / ledger_relative, initial_ledger)
    raw_items.append((initial_ledger["ledgerId"], ledger_relative, initial_ledger))
    ledgers = [initial_ledger]

    stage_outputs: list[tuple[dict[str, Any], dict[str, Any]]] = []
    for stage in protocol["stages"]:
        artifact_id = f"{run_id}-O{stage['sequence']}"
        artifact = _artifact(
            artifact_id=artifact_id,
            stage_id=stage["stageId"],
            required_sections=stage["requiredSections"],
            accepted_invariant_ids=[
                item["invariantId"] for item in active_invariants
            ],
            stage_class=stage["stageClass"],
            domain_suboracle_bindings=stage_suboracle_bindings(
                stage["stageClass"],
                domain_suboracle_pack,
            ),
        )
        relative = f"RAW-ARTIFACTS/{artifact_id}.json"
        path = output / relative
        _write_json(path, artifact)
        descriptor = _descriptor(
            artifact_id=artifact_id,
            role=stage["requiredOutputRoles"][0],
            relative_path=relative,
            path=path,
            value=artifact,
            producer_class="synthetic-calibration",
            authority_class="proposal-only",
            ordinal=1,
        )
        raw_items.append((artifact_id, relative, artifact))
        stage_outputs.append((artifact, descriptor))

    gate_to_stage = {
        0: None,
        1: protocol["stages"][0]["stageId"],
        2: protocol["stages"][1]["stageId"],
        3: protocol["stages"][2]["stageId"],
        4: protocol["stages"][3]["stageId"],
        5: protocol["stages"][4]["stageId"],
        6: protocol["stages"][5]["stageId"],
        7: protocol["stages"][6]["stageId"],
    }
    receipts: dict[str, dict[str, Any]] = {}
    for gate in protocol["gates"]:
        stage_id = gate_to_stage[gate["sequence"]]
        proposal_sha256 = (
            source_sha256
            if gate["sequence"] == 0
            else canonical_sha256(stage_outputs[gate["sequence"] - 1][0])
        )
        before_sha256 = (
            None
            if gate["sequence"] == 0
            else ledgers[-1]["ledgerSha256"]
        )
        change_ids = (
            []
            if gate["sequence"] in {0, 3}
            else [f"accept-stage-{gate['sequence']}"]
        )
        artifact_ids = (
            ["SOURCE-BUNDLE"]
            if gate["sequence"] == 0
            else [stage_outputs[gate["sequence"] - 1][0]["artifactId"]]
        )
        receipt = _receipt(
            run_id=run_id,
            gate=gate,
            stage_id=stage_id,
            proposal_sha256=proposal_sha256,
            before_ledger_sha256=before_sha256,
            allowed_change_ids=change_ids,
            artifact_ids=artifact_ids,
        )
        relative = f"AUTHORITY-RECEIPTS/{gate['gateId']}.json"
        _write_json(output / relative, receipt)
        raw_items.append((receipt["receiptId"], relative, receipt))
        receipts[gate["gateId"]] = receipt

        if gate["sequence"] == 0:
            continue
        stage = protocol["stages"][gate["sequence"] - 1]
        artifact = stage_outputs[gate["sequence"] - 1][0]
        if gate["sequence"] != 3:
            invariant = _invariant(
                invariant_id=f"inv.stage-{gate['sequence']}-accepted",
                sequence=gate["sequence"],
                claim={
                    "stageId": stage["stageId"],
                    "acceptedForSyntheticCalibration": True,
                },
                basis_kind="human-authority-receipt",
                basis_sha256=receipt["receiptSha256"],
                source_pointer=None,
            )
            active_invariants.append(invariant)
            history.append(
                _transition(
                    transition_id=f"accept-stage-{gate['sequence']}",
                    stage_id=stage["stageId"],
                    sequence=gate["sequence"],
                    before_ledger_sha256=ledgers[-1]["ledgerSha256"],
                    proposal_sha256=canonical_sha256(artifact),
                    invariant=invariant,
                    basis_kind="human-authority-receipt",
                    basis_sha256=receipt["receiptSha256"],
                )
            )
        ledger = _ledger(
            run_id=run_id,
            protocol_sha256=protocol_sha256,
            source_registry_sha256=source_sha256,
            stage_id=stage["stageId"],
            sequence=stage["sequence"],
            previous_ledger_sha256=ledgers[-1]["ledgerSha256"],
            active_invariants=active_invariants,
            history=history,
        )
        relative = (
            "ACCEPTED-INVARIANT-LEDGERS/"
            f"ledger-{stage['sequence']:02d}.json"
        )
        _write_json(output / relative, ledger)
        raw_items.append((ledger["ledgerId"], relative, ledger))
        ledgers.append(ledger)

    envelopes: list[dict[str, Any]] = []
    previous_output_descriptor: dict[str, Any] | None = None
    for index, stage in enumerate(protocol["stages"]):
        artifact, output_descriptor = stage_outputs[index]
        input_bindings = [deepcopy(source_descriptor)]
        if previous_output_descriptor is not None:
            predecessor = deepcopy(previous_output_descriptor)
            predecessor["ordinal"] = len(input_bindings) + 1
            input_bindings.append(predecessor)
        required_receipts = [
            receipts[gate_id]
            for gate_id in stage["requiredAuthorityGates"]
        ]
        before_ledger = ledgers[index]
        after_ledger = ledgers[index + 1]
        accepted_change_ids = [
            change["changeId"]
            for transition in after_ledger["transitionHistory"][
                len(before_ledger["transitionHistory"]) :
            ]
            for change in transition["changes"]
        ]
        envelope = {
            "schema": 1,
            "kind": "source-backed-software-lifecycle-stage-envelope",
            "envelopeId": f"{run_id}-E{stage['sequence']}",
            "runId": run_id,
            "protocolBinding": {
                "protocolId": protocol["id"],
                "protocolCanonicalSha256": protocol_sha256,
                "stageDefinitionCanonicalSha256": canonical_sha256(stage),
            },
            "stage": {
                "stageId": stage["stageId"],
                "sequence": stage["sequence"],
                "stageClass": stage["stageClass"],
            },
            "role": stage["role"],
            "independenceClass": stage["independenceClass"],
            "lineage": {
                "primaryPredecessorEnvelopeSha256": (
                    None
                    if not envelopes
                    else envelopes[-1]["envelopeSha256"]
                ),
                "additionalPredecessorEnvelopeSha256s": [],
                "previousAcceptedLedgerSha256": before_ledger[
                    "ledgerSha256"
                ],
            },
            "sourceBindings": [deepcopy(source_descriptor)],
            "inputBindings": input_bindings,
            "inputSetCanonicalSha256": canonical_sha256(input_bindings),
            "outputBindings": [deepcopy(output_descriptor)],
            "outputSetCanonicalSha256": canonical_sha256(
                [output_descriptor]
            ),
            "sections": list(stage["requiredSections"]),
            "provenanceIds": list(artifact["provenanceIds"]),
            "assumptionIds": list(artifact["assumptionIds"]),
            "detectedLossIds": list(artifact["detectedLossIds"]),
            "acceptanceObligationIds": [
                f"acceptance.{stage['stageClass']}"
            ],
            "humanAuthorityReceiptBindings": [
                receipt["receiptSha256"]
                for receipt in required_receipts
            ],
            "repositoryTruthBefore": {
                "required": False,
                "observed": False,
                "snapshotArtifactId": None,
                "snapshotSha256": None,
                "provesFilesystemZeroWrite": False,
            },
            "repositoryTruthAfter": {
                "required": False,
                "observed": False,
                "snapshotArtifactId": None,
                "snapshotSha256": None,
                "provesFilesystemZeroWrite": False,
            },
            "allowedMutableFiles": (
                ["feature.py", "test_feature.py"]
                if stage["stageClass"] == "implementation-tdd"
                else []
            ),
            "changedFiles": [],
            "rawEventArtifactIds": [],
            "absoluteGateResults": [
                {
                    "gateId": f"mechanism.{stage['stageClass']}",
                    "passed": True,
                    "evidenceArtifactIds": [artifact["artifactId"]],
                }
            ],
            "truthTransition": {
                "proposalArtifactCanonicalSha256": canonical_sha256(
                    artifact
                ),
                "proposedChangeIds": (
                    []
                    if stage["sequence"] == 3
                    else [f"accept-stage-{stage['sequence']}"]
                ),
                "acceptedChangeIds": accepted_change_ids,
                "rejectedChangeIds": [],
                "basisKindsUsed": (
                    []
                    if not accepted_change_ids
                    else ["human-authority-receipt"]
                ),
                "beforeAcceptedLedgerSha256": before_ledger[
                    "ledgerSha256"
                ],
                "afterAcceptedLedgerSha256": after_ledger[
                    "ledgerSha256"
                ],
            },
            "parentEvaluation": {
                "evaluatorId": "software-lifecycle-zero-model-calibrator-v1",
                "evaluatorCanonicalSha256": canonical_sha256(
                    {
                        "id": "software-lifecycle-zero-model-calibrator-v1",
                        "mode": "mechanism-only",
                    }
                ),
                "stageValidators": list(stage["stageValidators"]),
                "status": "accepted",
                "failureCodes": [],
            },
            "execution": {
                "mode": "zero-model-scripted-calibration",
                "agentDispatchCount": 0,
                "modelCallCount": 0,
                "actualRouteObserved": False,
                "networkAccessUsed": False,
                "gitMutationUsed": False,
                "externalWriteUsed": False,
            },
            "status": "accepted",
            "stopReason": None,
            "nextGate": stage["exitGate"],
            "claimBoundary": {
                "liveAgentBehaviorProved": False,
                "productionLifecycleProved": False,
                "humanDecisionQualityProved": False,
                "crossHostPortabilityProved": False,
            },
            "envelopeSha256": ZERO,
        }
        envelope["envelopeSha256"] = self_hash(
            envelope,
            "envelopeSha256",
        )
        relative = f"STAGE-ENVELOPES/{stage['stageId']}.json"
        _write_json(output / relative, envelope)
        raw_items.append((envelope["envelopeId"], relative, envelope))
        envelopes.append(envelope)
        previous_output_descriptor = output_descriptor

    raw_index = []
    for artifact_id, relative, value in raw_items:
        path = output / relative
        raw_index.append(
            {
                "artifactId": artifact_id,
                "path": relative,
                "bytes": len(path.read_bytes()),
                "rawSha256": file_sha256(path),
                "canonicalSha256": canonical_sha256(value),
                "repositoryLocalAuditPath": True,
            }
        )
    capture = {
        "schema": 1,
        "kind": "software-lifecycle-thin-slice-zero-model-capture",
        "mode": "zero-model-scripted-calibration",
        "protocolBinding": {
            "path": PROTOCOL_PATH,
            "fileSha256": file_sha256(protocol_path),
            "canonicalSha256": protocol_sha256,
        },
        "execution": {
            "agentDispatchCount": 0,
            "modelCallCount": 0,
            "actualRouteObserved": False,
            "dispatchAuthorized": False,
            "networkAccessUsed": False,
            "gitMutationUsed": False,
            "externalWriteUsed": False,
        },
        "runId": run_id,
        "sourceArtifactId": "SOURCE-BUNDLE",
        "domainSuboraclePackArtifactId": (
            DOMAIN_SUBORACLE_ARTIFACT_ID
        ),
        "stageEnvelopeIds": [
            envelope["envelopeId"] for envelope in envelopes
        ],
        "authorityReceiptIds": [
            receipts[gate_id]["receiptId"]
            for gate_id in [
                gate["gateId"] for gate in protocol["gates"]
            ]
        ],
        "acceptedInvariantLedgerIds": [
            ledger["ledgerId"] for ledger in ledgers
        ],
        "rawArtifactIndex": raw_index,
        "completion": {
            "status": "valid-calibration-only",
            "failureCodes": [],
        },
        "eligibleForFormalLiveEvidence": False,
        "claimBoundary": deepcopy(protocol["claimBoundary"]),
    }
    _write_json(output / CAPTURE_NAME, capture)
    return capture


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--run-id",
        default="SE-E2E-THIN-01-ZERO-001",
    )
    arguments = parser.parse_args()
    capture = build_calibration_capture(
        arguments.output,
        run_id=arguments.run_id,
    )
    print(json.dumps(capture, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
