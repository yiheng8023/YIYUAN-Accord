#!/usr/bin/env python3
"""Build a digest-bound dispatch reservation input from governed documents."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any


class DispatchAuthorizationError(RuntimeError):
    """Raised when repository evidence cannot authorize one diagnostic."""


@dataclass(frozen=True)
class DispatchAuthorizationEnvelope:
    """Immutable source bytes and derived reservation input for one dispatch."""

    reservation_input_json: bytes
    ledger_path: Path
    source_documents: tuple[tuple[str, bytes], ...]

    def reservation_input(self) -> dict[str, Any]:
        value = json.loads(self.reservation_input_json.decode("utf-8"))
        if not isinstance(value, dict):
            raise DispatchAuthorizationError(
                "authorization envelope payload must be a JSON object"
            )
        return value


def _canonical_sha256(value: Any) -> str:
    encoded = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _is_sha256(value: Any) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(character in "0123456789abcdef" for character in value)
    )


def _safe_relative_path(value: Any, label: str) -> Path:
    if not isinstance(value, str) or not value.strip():
        raise DispatchAuthorizationError(f"{label} is missing")
    path = Path(value)
    if path.is_absolute() or ".." in path.parts:
        raise DispatchAuthorizationError(
            f"{label} must be a contained relative path"
        )
    return path


def _read_document(
    path: Path,
    label: str,
) -> tuple[dict[str, Any], bytes]:
    try:
        raw = path.read_bytes()
        value = json.loads(raw.decode("utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise DispatchAuthorizationError(
            f"{label} is not readable valid JSON"
        ) from error
    if not isinstance(value, dict):
        raise DispatchAuthorizationError(f"{label} must be a JSON object")
    return value, raw


def _parse_time(value: Any, label: str) -> datetime:
    if not isinstance(value, str):
        raise DispatchAuthorizationError(f"{label} is missing")
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as error:
        raise DispatchAuthorizationError(f"{label} is invalid") from error
    if parsed.tzinfo is None:
        raise DispatchAuthorizationError(f"{label} must include an offset")
    return parsed


def _candidate_identity(candidate: dict[str, Any]) -> dict[str, Any]:
    try:
        return {
            "candidateId": candidate["candidateId"],
            "sourceRevisionOrVersion": candidate[
                "sourceRevisionOrVersion"
            ],
            "licenseSha256": candidate["license"]["sha256"],
            "files": [
                {
                    "path": item["path"],
                    "sha256": item["sha256"],
                }
                for item in candidate["files"]
            ],
            "projectionTreeSha256": candidate["projectionTreeSha256"],
        }
    except (KeyError, TypeError) as error:
        raise DispatchAuthorizationError(
            "protocol candidate identity is incomplete"
        ) from error


def build_dispatch_authorization_envelope(
    *,
    protocol_path: Path,
    source_governance_preflight_path: Path,
    static_gap_audit_path: Path,
    diagnostic_admission_path: Path,
    candidate_id: str,
    observed_at: str,
) -> DispatchAuthorizationEnvelope:
    paths = {
        "protocol": protocol_path.resolve(),
        "source governance preflight": (
            source_governance_preflight_path.resolve()
        ),
        "static gap audit": static_gap_audit_path.resolve(),
        "diagnostic admission": diagnostic_admission_path.resolve(),
    }
    loaded_documents = {
        label: _read_document(path, label)
        for label, path in paths.items()
    }
    documents = {
        label: loaded[0]
        for label, loaded in loaded_documents.items()
    }
    source_bytes = {
        label: loaded[1]
        for label, loaded in loaded_documents.items()
    }
    protocol = documents["protocol"]
    preflight = documents["source governance preflight"]
    audit = documents["static gap audit"]
    admission = documents["diagnostic admission"]

    candidates = [
        item
        for item in protocol.get("candidates", [])
        if isinstance(item, dict)
        and item.get("candidateId") == candidate_id
    ]
    if len(candidates) != 1:
        raise DispatchAuthorizationError(
            "candidate is not uniquely bound by the protocol"
        )
    candidate = candidates[0]
    candidate_identity = _candidate_identity(candidate)
    candidate_identity_sha256 = _canonical_sha256(candidate_identity)
    all_candidate_identities_sha256 = _canonical_sha256(
        [
            _candidate_identity(item)
            for item in protocol.get("candidates", [])
            if isinstance(item, dict)
        ]
    )

    design = protocol.get("diagnosticDesign", {})
    decision = protocol.get("decision", {})
    if not (
        design.get("maximumDispatchesPerCandidate") == 1
        and design.get("replacementDispatchAllowed") is False
        and design.get("pairwiseComparisonAllowed") is False
        and decision.get("protocolPreregistered") is True
        and decision.get("liveDiagnosticStarted") is False
        and decision.get("anyExactCandidateExecutionEligibleNow") is True
        and decision.get("governanceAdmissionStillRequired") is False
        and decision.get("candidateAdmissionDecisionMade") is True
    ):
        raise DispatchAuthorizationError(
            "protocol execution eligibility is not satisfied"
        )

    preflight_candidates = [
        item
        for item in preflight.get("candidateObservations", [])
        if isinstance(item, dict)
        and item.get("candidateId") == candidate_id
    ]
    preflight_decision = preflight.get("decision", {})
    raw_boundary = preflight.get("rawEvidenceBoundary", {})
    if not (
        len(preflight_candidates) == 1
        and preflight_candidates[0].get("liveBytesMatchProtocol") is True
        and raw_boundary.get("freshForDispatch") is True
        and raw_boundary.get(
            "freshRevalidationStillRequiredAtDispatch"
        )
        is False
        and preflight_decision.get(
            "currentToolchainIdentityRevalidated"
        )
        is True
        and preflight_decision.get("freshForDispatch") is True
        and preflight_decision.get("liveDiagnosticStarted") is False
        and preflight_decision.get("modelRequestSent") is False
        and preflight_decision.get(
            "candidateInstructionExecutionPerformed"
        )
        is False
    ):
        raise DispatchAuthorizationError(
            "source freshness and toolchain revalidation are not satisfied"
        )

    file_hashes = {
        label: hashlib.sha256(raw).hexdigest()
        for label, raw in source_bytes.items()
    }
    if not (
        audit.get("sourceGovernancePreflightSha256")
        == file_hashes["source governance preflight"]
        and audit.get("candidateIdentityEnvelopeSha256")
        == all_candidate_identities_sha256
        and any(
            isinstance(item, dict)
            and item.get("candidateId") == candidate_id
            and item.get("sourceRevisionOrVersion")
            == candidate.get("sourceRevisionOrVersion")
            and item.get("skillSha256")
            == candidate["files"][0]["sha256"]
            for item in audit.get("candidates", [])
        )
        and audit.get("decision", {}).get("staticGapAuditCompleted") is True
        and audit.get("decision", {}).get(
            "candidateTaskTurnStarted"
        )
        is False
        and audit.get("decision", {}).get("modelRequestSent") is False
        and audit.get("decision", {}).get("candidateSkillInvoked") is False
    ):
        raise DispatchAuthorizationError(
            "static audit input binding is not satisfied"
        )

    if not (
        admission.get("schema") == 1
        and admission.get("kind")
        == "diagnostic-only-exact-candidate-execution-admission"
        and admission.get("candidateId") == candidate_id
        and admission.get("candidateIdentitySha256")
        == candidate_identity_sha256
        and admission.get("protocolFileSha256")
        == file_hashes["protocol"]
        and admission.get("sourceGovernancePreflightFileSha256")
        == file_hashes["source governance preflight"]
        and admission.get("staticGapAuditFileSha256")
        == file_hashes["static gap audit"]
    ):
        raise DispatchAuthorizationError(
            "diagnostic admission digest binding is not satisfied"
        )
    if not (
        admission.get("disposition")
        == "admit-one-noncomparative-diagnostic"
        and admission.get("exactCandidateExecutionAdmitted") is True
        and admission.get("maximumDispatches") == 1
        and admission.get("replacementAllowed") is False
        and admission.get("comparisonAllowed") is False
        and admission.get("portfolioMutationAllowed") is False
        and isinstance(admission.get("admissionId"), str)
        and bool(admission["admissionId"].strip())
    ):
        raise DispatchAuthorizationError(
            "diagnostic admission boundary is not satisfied"
        )

    observed_time = _parse_time(observed_at, "dispatch observation time")
    source_time = _parse_time(
        preflight.get("observedAt"),
        "source revalidation time",
    )
    valid_from = _parse_time(admission.get("validFrom"), "admission validFrom")
    valid_until = _parse_time(
        admission.get("validUntil"),
        "admission validUntil",
    )
    if not (
        admission.get("sourceRevalidatedAt") == preflight.get("observedAt")
        and valid_from <= source_time <= observed_time <= valid_until
    ):
        raise DispatchAuthorizationError(
            "diagnostic admission validity window is not satisfied"
        )

    authority_reference = protocol.get("dispatchLedgerAuthority", {})
    authority_document = _safe_relative_path(
        authority_reference.get("document"),
        "ledger authority document",
    )
    authority_expected_sha256 = authority_reference.get("sha256")
    if not _is_sha256(authority_expected_sha256):
        raise DispatchAuthorizationError(
            "ledger authority digest is invalid"
        )
    protocol_directory = paths["protocol"].parent
    authority_path = (protocol_directory / authority_document).resolve()
    if not authority_path.is_relative_to(protocol_directory):
        raise DispatchAuthorizationError(
            "ledger authority document escapes the protocol directory"
        )
    authority, authority_raw = _read_document(
        authority_path,
        "ledger authority document",
    )
    authority_actual_sha256 = hashlib.sha256(authority_raw).hexdigest()
    if authority_actual_sha256 != authority_expected_sha256:
        raise DispatchAuthorizationError(
            "ledger authority digest binding is not satisfied"
        )
    ledger_relative_path = _safe_relative_path(
        authority.get("ledgerRelativePath"),
        "ledger relative path",
    )
    ledger_path = (authority_path.parent / ledger_relative_path).resolve()
    if (
        not ledger_path.is_relative_to(authority_path.parent)
        or ledger_path == authority_path
        or ledger_path.suffix != ".jsonl"
    ):
        raise DispatchAuthorizationError(
            "ledger relative path is not a contained JSONL target"
        )
    if not (
        authority.get("schema") == 1
        and authority.get("kind") == "single-dispatch-ledger-authority"
        and isinstance(authority.get("authorityId"), str)
        and bool(authority["authorityId"].strip())
        and authority.get("replacementLedgerAllowed") is False
        and authority.get("automaticReleaseAllowed") is False
        and authority.get("automaticRetryAllowed") is False
        and authority.get("manualReconciliationRequired") is True
    ):
        raise DispatchAuthorizationError(
            "ledger authority boundary is not satisfied"
        )

    reservation_input = {
        "schema": 1,
        "candidateId": candidate_id,
        "candidateIdentitySha256": candidate_identity_sha256,
        "protocolFileSha256": file_hashes["protocol"],
        "sourceGovernancePreflightFileSha256": file_hashes[
            "source governance preflight"
        ],
        "staticGapAuditFileSha256": file_hashes["static gap audit"],
        "diagnosticAdmissionFileSha256": file_hashes[
            "diagnostic admission"
        ],
        "diagnosticAdmissionId": admission["admissionId"],
        "ledgerAuthorityDocument": authority_document.as_posix(),
        "ledgerAuthorityDocumentSha256": authority_actual_sha256,
        "ledgerAuthorityId": authority["authorityId"],
        "ledgerRelativePath": ledger_relative_path.as_posix(),
        "observedAt": observed_at,
        "exactCandidateExecutionAdmitted": True,
        "sourceAndToolchainReverifiedAtDispatch": True,
    }
    reservation_input["authorizationSha256"] = _canonical_sha256(
        reservation_input
    )
    return DispatchAuthorizationEnvelope(
        reservation_input_json=json.dumps(
            reservation_input,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8"),
        ledger_path=ledger_path,
        source_documents=tuple(source_bytes.items())
        + (("ledger authority document", authority_raw),),
    )


def build_dispatch_reservation_input(
    *,
    protocol_path: Path,
    source_governance_preflight_path: Path,
    static_gap_audit_path: Path,
    diagnostic_admission_path: Path,
    candidate_id: str,
    observed_at: str,
) -> dict[str, Any]:
    """Compatibility view of the immutable dispatch authorization envelope."""

    return build_dispatch_authorization_envelope(
        protocol_path=protocol_path,
        source_governance_preflight_path=source_governance_preflight_path,
        static_gap_audit_path=static_gap_audit_path,
        diagnostic_admission_path=diagnostic_admission_path,
        candidate_id=candidate_id,
        observed_at=observed_at,
    ).reservation_input()
