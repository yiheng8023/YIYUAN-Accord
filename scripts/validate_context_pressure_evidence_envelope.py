#!/usr/bin/env python3
"""Fail-closed offline validator for CTX-03 pressure-signal evidence."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import re
from typing import Any

SUPPORTED = {"direct-counter", "host-event", "heuristic", "user-observed"}
SOURCES = {
    "direct-counter": {"host-context-counter"},
    "host-event": {"host-context-event"},
    "heuristic": {"heuristic-analysis"},
    "user-observed": {"user-reported-degradation"},
}
UNITS = {
    "direct-counter": {"tokens", "percent"}, "host-event": {"event-count"},
    "heuristic": {"score"}, "user-observed": {"report-count"},
}
CLAIM_BOUNDARY = {
    "countsAsLiveHostTelemetryProof": False,
    "countsAsBestEfficiencyThresholdProof": False,
    "countsAsAutomaticThreadCreationProof": False,
    "countsAsContextCompactionProof": False,
    "countsAsFreshSessionProof": False,
    "countsAsLoaderInvocationProof": False,
    "countsAsWeakAgentAcceptanceProof": False,
    "changesHost": False, "createsThread": False, "changesMcp": False,
    "changesAccount": False,
}
ACTION_BOUNDARY = {
    "envelopeAuthorizesHostObservation": False,
    "envelopeAuthorizesThreadCreation": False,
    "envelopeAuthorizesHostMutation": False,
    "envelopeAuthorizesMcpMutation": False,
    "envelopeAuthorizesAccountAccess": False,
}
FIELDS = {
    "schema", "id", "signalProvenance", "hostIdentity", "hostVersion",
    "profileId", "signalEvidenceSource", "observedValue", "unit",
    "observedAt", "parentRunId", "signalDeliveryObserved", "actionAuthority",
    "evidenceArtifact", "claimBoundary",
}
ISO_UTC = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
SHA256 = re.compile(r"^[0-9a-f]{64}$")
BINDING_FIELDS = {
    "hostIdentity",
    "hostVersion",
    "profileId",
    "parentRunId",
    "observedAt",
}


def canonical_sha256(value: Any) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _text(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _artifact(value: Any, require_hash: bool) -> bool:
    if not isinstance(value, dict) or set(value) != {"kind", "ref", "sha256"} or not _text(value.get("ref")):
        return False
    if value.get("kind") == "sha256-bound-artifact":
        return isinstance(value.get("sha256"), str) and bool(SHA256.fullmatch(value["sha256"]))
    return value.get("kind") == "opaque-host-reference" and value.get("sha256") is None and not require_hash


def validate_context_pressure_evidence_envelope(
    envelope: Any,
    expected_binding: Any,
) -> dict[str, Any]:
    """Validate record shape only; never observe its named host or artifact."""
    failures: list[str] = []
    if not isinstance(envelope, dict) or set(envelope) != FIELDS:
        failures.append("fail-envelope-shape")
        envelope = envelope if isinstance(envelope, dict) else {}
    if (
        not isinstance(expected_binding, dict)
        or set(expected_binding) != BINDING_FIELDS
        or any(
            envelope.get(key) != expected_binding.get(key)
            for key in BINDING_FIELDS
        )
    ):
        failures.append("blocked-target-run-time-binding-mismatch")
    provenance = envelope.get("signalProvenance")
    if provenance not in SUPPORTED:
        failures.append("blocked-unsupported-or-unknown-provenance")
    if envelope.get("schema") != 1 or not _text(envelope.get("id")):
        failures.append("fail-envelope-identity")
    if provenance in SUPPORTED and (
        not isinstance(envelope.get("observedValue"), (int, float))
        or isinstance(envelope.get("observedValue"), bool)
        or envelope.get("unit") not in UNITS[provenance]
    ):
        failures.append("blocked-invalid-observed-value-or-unit")
    if not _text(envelope.get("parentRunId")) or not isinstance(envelope.get("signalDeliveryObserved"), bool):
        failures.append("blocked-missing-run-or-delivery-evidence")
    if not isinstance(envelope.get("observedAt"), str) or not ISO_UTC.fullmatch(envelope["observedAt"]):
        failures.append("blocked-invalid-observation-time")
    if envelope.get("actionAuthority") != ACTION_BOUNDARY:
        failures.append("hard-fail-envelope-authority-promotion")
    if envelope.get("claimBoundary") != CLAIM_BOUNDARY:
        failures.append("hard-fail-envelope-claim-promotion")
    if provenance in {"direct-counter", "host-event"}:
        if any(not _text(envelope.get(key)) for key in ("hostIdentity", "hostVersion", "profileId")):
            failures.append("blocked-missing-host-identity-binding")
        if envelope.get("signalEvidenceSource") not in SOURCES[provenance]:
            failures.append("blocked-host-source-provenance-mismatch")
        if not _artifact(envelope.get("evidenceArtifact"), True):
            failures.append("blocked-missing-sha256-bound-host-evidence")
    elif provenance in {"heuristic", "user-observed"}:
        if any(envelope.get(key) is not None for key in ("hostIdentity", "hostVersion", "profileId")):
            failures.append("hard-fail-non-host-provenance-masquerades-as-host-telemetry")
        if envelope.get("signalEvidenceSource") not in SOURCES[provenance]:
            failures.append("blocked-non-host-source-provenance-mismatch")
        if not _artifact(envelope.get("evidenceArtifact"), False):
            failures.append("blocked-invalid-non-host-evidence-reference")
    failures = list(dict.fromkeys(failures))
    return {
        "schema": 1, "id": "context-pressure-evidence-envelope-verdict",
        "status": "advisory-evidence-ready-offline-only" if not failures else "blocked-missing-host-pressure-evidence",
        "failureCodes": failures, "envelopeSha256": canonical_sha256(envelope),
        "claimBoundary": dict(CLAIM_BOUNDARY),
        "nextGate": "existing-CTX-03-advisory-and-separately-authorized-host-specific-observation",
    }


def merge_patch(base: Any, patch: Any) -> Any:
    if not isinstance(patch, dict):
        return copy.deepcopy(patch)
    result = copy.deepcopy(base) if isinstance(base, dict) else {}
    for key, value in patch.items():
        if isinstance(value, dict):
            result[key] = merge_patch(result.get(key), value)
        else:
            result[key] = copy.deepcopy(value)
    return result


def expected_binding(envelope: dict[str, Any]) -> dict[str, Any]:
    return {key: envelope.get(key) for key in BINDING_FIELDS}


def evaluate_fixture_document(document: dict[str, Any]) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for case in document["cases"]:
        envelope = merge_patch(document["baseEnvelope"], case.get("patch", {}))
        binding = merge_patch(
            expected_binding(envelope),
            case.get("bindingPatch", {}),
        )
        actual = validate_context_pressure_evidence_envelope(envelope, binding)
        results.append(
            {
                "id": case["id"],
                "expectedStatus": case["expectedStatus"],
                "actualStatus": actual["status"],
                "expectedFailureCodes": case["expectedFailureCodes"],
                "actualFailureCodes": actual["failureCodes"],
                "claimBoundary": actual["claimBoundary"],
            }
        )
    return results


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("envelope")
    parser.add_argument("expected_binding")
    args = parser.parse_args()
    with open(args.envelope, encoding="utf-8") as handle:
        envelope = json.load(handle)
    with open(args.expected_binding, encoding="utf-8") as handle:
        expected_binding = json.load(handle)
    print(
        json.dumps(
            validate_context_pressure_evidence_envelope(
                envelope,
                expected_binding,
            ),
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
