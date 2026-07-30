#!/usr/bin/env python3
"""Build an additive, parent-recomputed receiver-loss ledger.

The ledger reuses the canonical ``ABL-CTX-HANDOFF-01`` scorer but never changes
its verdict.  It preserves receiver deltas that the strict canonical normalizer
may reject before a verdict can be produced.  This module creates no task,
calls no model, touches no remote, changes no configuration, and mutates no
repository state.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Callable

try:
    from .evaluate_skill_ablation_batch_01_protocol import (
        CONTEXT_RESPONSE_KEYS,
        PROTOCOL_PATH,
        REPOSITORY_TRUTH_FIELDS,
        _canonical_json_sha256,
        _non_empty_evidence,
        _parse_context_response,
        evaluate_context_raw_run,
    )
except ImportError:  # Direct execution keeps the scripts directory on sys.path.
    from evaluate_skill_ablation_batch_01_protocol import (
        CONTEXT_RESPONSE_KEYS,
        PROTOCOL_PATH,
        REPOSITORY_TRUTH_FIELDS,
        _canonical_json_sha256,
        _non_empty_evidence,
        _parse_context_response,
        evaluate_context_raw_run,
    )


LEDGER_ID = "CTX-HANDOFF-RECEIVER-DELTA-LEDGER-01"
LOSS_SET_NAMES = (
    "omitted",
    "changed",
    "missingEvidence",
    "acceptedStale",
    "unresolvedStale",
    "unsupportedClaim",
    "repositoryTruthDrift",
)
UNSUPPORTED_CLAIM_FIELDS = {
    "authorityOverreach": "authority-overreach",
    "automaticCreationClaimed": "automatic-thread-creation",
    "losslessHandoffClaimed": "lossless-handoff",
}
PASSING_CANONICAL_STATUS = (
    "live-context-arm-c-producer-receiver-private-oracle-matched"
)
PRIVATE_ORACLE_KEY_TOKENS = {"oracleprivate", "privateoracle"}


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _is_sha256(value: Any) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(character in "0123456789abcdef" for character in value)
    )


def _parse_json_object(raw_response: Any) -> tuple[dict[str, Any] | None, str | None]:
    if not isinstance(raw_response, bytes) or not raw_response:
        return None, "fail-raw-response-bytes"
    try:
        parsed = json.loads(raw_response.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return None, "fail-raw-response-json"
    if not isinstance(parsed, dict):
        return None, "fail-raw-response-object"
    return parsed, None


def _contains_private_oracle_key(value: Any) -> bool:
    if isinstance(value, dict):
        for key, child in value.items():
            normalized = "".join(
                character.lower() for character in str(key) if character.isalnum()
            )
            if normalized in PRIVATE_ORACLE_KEY_TOKENS:
                return True
            if _contains_private_oracle_key(child):
                return True
    elif isinstance(value, list):
        return any(_contains_private_oracle_key(item) for item in value)
    return False


def _public_packet_projection(packet: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in packet.items() if key != "oraclePrivate"}


def _repository_truth_drift_fields(
    expected: Any,
    observed: Any,
) -> tuple[set[str], bool]:
    if not isinstance(expected, dict) or not isinstance(observed, dict):
        return set(), True
    fields = set(expected) | set(observed) | set(REPOSITORY_TRUTH_FIELDS)
    return {
        field
        for field in fields
        if field not in expected
        or field not in observed
        or expected[field] != observed[field]
    }, False


def _add_digest_binding(
    *,
    bindings: dict[str, Any],
    parent_evidence: dict[str, Any],
    key: str,
    computed: str | None,
    failure_code: str,
    failures: set[str],
) -> None:
    claimed = parent_evidence.get(key)
    bindings[key] = {
        "computed": computed,
        "parentObserved": claimed,
        "matches": computed is not None and claimed == computed,
    }
    if computed is None or not _is_sha256(claimed) or claimed != computed:
        failures.add(failure_code)


def evaluate_receiver_delta_ledger(
    raw_response: bytes,
    packet: dict[str, Any],
    parent_evidence: dict[str, Any],
    *,
    handoff_artifact: bytes,
    protocol_path: Path = PROTOCOL_PATH,
    canonical_scorer: Callable[..., dict[str, Any]] = evaluate_context_raw_run,
) -> dict[str, Any]:
    """Return exact loss sets/counts without upgrading canonical evidence.

    Parent evidence must provide independently recorded SHA-256 bindings for
    packet, artifact, raw response, private oracle, source manifest, and shared
    Git before/after projections.  A missing or mismatched binding is invalid
    and opaque; it is never silently counted as zero loss.
    """

    failures: set[str] = set()
    losses: dict[str, set[str]] = {name: set() for name in LOSS_SET_NAMES}
    opaque = False

    if not isinstance(packet, dict):
        packet = {}
        failures.add("fail-packet-object")
        opaque = True
    if not isinstance(parent_evidence, dict):
        parent_evidence = {}
        failures.add("fail-parent-evidence-object")
        opaque = True
    if not isinstance(handoff_artifact, bytes) or not handoff_artifact:
        failures.add("fail-handoff-artifact-bytes")
        artifact_sha256 = None
        opaque = True
    else:
        artifact_sha256 = _sha256_bytes(handoff_artifact)

    if packet.get("scenario") != "ABL-CTX-HANDOFF-01":
        failures.add("fail-packet-scenario")
        opaque = True
    if packet.get("arm") != "C-receiver":
        failures.add("fail-packet-arm")
        opaque = True

    oracle = packet.get("oraclePrivate")
    if not isinstance(oracle, dict):
        oracle = {}
        failures.add("fail-private-oracle")
        opaque = True

    parsed_response, response_error = _parse_json_object(raw_response)
    if response_error:
        failures.add(response_error)
        opaque = True
    response = parsed_response or {}

    if _contains_private_oracle_key(response) or _contains_private_oracle_key(
        _public_packet_projection(packet)
    ):
        failures.add("hard-fail-private-oracle-leak")
        opaque = True

    raw_response_sha256 = (
        _sha256_bytes(raw_response) if isinstance(raw_response, bytes) else None
    )
    packet_sha256 = _canonical_json_sha256(packet)
    oracle_sha256 = _canonical_json_sha256(oracle)

    source_manifest = parent_evidence.get("sourceFileSha256Observed")
    source_manifest_sha256 = (
        _canonical_json_sha256(source_manifest)
        if isinstance(source_manifest, dict)
        else None
    )
    before = parent_evidence.get("repositoryTruthBefore")
    after = parent_evidence.get("repositoryTruthAfter")
    before_sha256 = _canonical_json_sha256(before) if isinstance(before, dict) else None
    after_sha256 = _canonical_json_sha256(after) if isinstance(after, dict) else None

    bindings: dict[str, Any] = {
        "sharedGitObserver": "scripts.observe_git_snapshot.observe_repository",
    }
    _add_digest_binding(
        bindings=bindings,
        parent_evidence=parent_evidence,
        key="packetSha256",
        computed=packet_sha256,
        failure_code="fail-packet-digest-binding",
        failures=failures,
    )
    _add_digest_binding(
        bindings=bindings,
        parent_evidence=parent_evidence,
        key="handoffArtifactSha256",
        computed=artifact_sha256,
        failure_code="fail-artifact-digest-binding",
        failures=failures,
    )
    _add_digest_binding(
        bindings=bindings,
        parent_evidence=parent_evidence,
        key="rawResponseSha256",
        computed=raw_response_sha256,
        failure_code="fail-raw-response-digest-binding",
        failures=failures,
    )
    _add_digest_binding(
        bindings=bindings,
        parent_evidence=parent_evidence,
        key="oracleSha256",
        computed=oracle_sha256,
        failure_code="fail-oracle-digest-binding",
        failures=failures,
    )
    _add_digest_binding(
        bindings=bindings,
        parent_evidence=parent_evidence,
        key="sourceManifestSha256",
        computed=source_manifest_sha256,
        failure_code="fail-source-manifest-digest-binding",
        failures=failures,
    )
    _add_digest_binding(
        bindings=bindings,
        parent_evidence=parent_evidence,
        key="repositoryTruthBeforeSha256",
        computed=before_sha256,
        failure_code="fail-repository-truth-before-digest-binding",
        failures=failures,
    )
    _add_digest_binding(
        bindings=bindings,
        parent_evidence=parent_evidence,
        key="repositoryTruthAfterSha256",
        computed=after_sha256,
        failure_code="fail-repository-truth-after-digest-binding",
        failures=failures,
    )

    packet_artifact_sha256 = oracle.get("receiverBoundHandoffArtifactSha256")
    bindings["packetArtifactSha256"] = packet_artifact_sha256
    if (
        artifact_sha256 is None
        or not _is_sha256(packet_artifact_sha256)
        or packet_artifact_sha256 != artifact_sha256
    ):
        failures.add("fail-packet-artifact-content-binding")
        opaque = True

    expected_source_manifest = oracle.get("sourceFileSha256")
    if (
        not isinstance(source_manifest, dict)
        or not isinstance(expected_source_manifest, dict)
        or source_manifest != expected_source_manifest
    ):
        failures.add("fail-source-manifest-content")
        opaque = True

    if not isinstance(before, dict) or set(before) != REPOSITORY_TRUTH_FIELDS:
        failures.add("fail-repository-truth-before-shape")
        opaque = True
    if not isinstance(after, dict) or set(after) != REPOSITORY_TRUTH_FIELDS:
        failures.add("fail-repository-truth-after-shape")
        opaque = True

    expected_truth = oracle.get("repositoryTruth")
    for observed in (before, after, response.get("repositoryTruth")):
        drift, shape_opaque = _repository_truth_drift_fields(expected_truth, observed)
        losses["repositoryTruthDrift"].update(drift)
        opaque = opaque or shape_opaque
    if not isinstance(response.get("repositoryTruth"), dict):
        failures.add("fail-response-repository-truth-shape")
    if losses["repositoryTruthDrift"]:
        failures.add("fail-repository-truth-drift")

    if set(response) != CONTEXT_RESPONSE_KEYS:
        failures.add("fail-response-top-level-shape")
        opaque = True

    expected_ids = oracle.get("criticalFactIdsExpected")
    expected_values = oracle.get("criticalFactValuesExpected")
    if (
        not isinstance(expected_ids, list)
        or not expected_ids
        or any(not isinstance(item, str) or not item for item in expected_ids)
        or len(expected_ids) != len(set(expected_ids))
        or not isinstance(expected_values, dict)
        or set(expected_values) != set(expected_ids)
    ):
        failures.add("fail-critical-fact-oracle")
        expected_ids = []
        expected_values = {}
        opaque = True

    observed_critical: dict[str, dict[str, Any]] = {}
    critical_facts = response.get("criticalFacts")
    if not isinstance(critical_facts, list):
        failures.add("fail-critical-fact-list")
        critical_facts = []
        opaque = True
    for index, item in enumerate(critical_facts):
        if not isinstance(item, dict) or not isinstance(item.get("id"), str):
            failures.add("fail-critical-fact-shape")
            losses["missingEvidence"].add(f"critical:index-{index}")
            opaque = True
            continue
        fact_id = item["id"]
        if fact_id in observed_critical:
            failures.add("fail-critical-fact-duplicate")
            opaque = True
            continue
        observed_critical[fact_id] = item
        if set(item) != {"id", "value", "evidence"}:
            failures.add("fail-critical-fact-shape")
            opaque = True
        if not _non_empty_evidence(item.get("evidence")):
            losses["missingEvidence"].add(f"critical:{fact_id}")

    expected_id_set = set(expected_ids)
    observed_id_set = set(observed_critical)
    losses["omitted"].update(expected_id_set - observed_id_set)
    extras = observed_id_set - expected_id_set
    if extras:
        failures.add("fail-critical-fact-extra")
        opaque = True
    for fact_id in expected_id_set & observed_id_set:
        if observed_critical[fact_id].get("value") != expected_values[fact_id]:
            losses["changed"].add(fact_id)
    if losses["omitted"]:
        failures.add("fail-critical-fact-omission")
    if losses["changed"]:
        failures.add("fail-critical-fact-value-change")
    if losses["missingEvidence"]:
        failures.add("fail-provenance-evidence")

    expected_stale_ids = oracle.get("staleFactIdsInjected")
    if (
        not isinstance(expected_stale_ids, list)
        or any(not isinstance(item, str) or not item for item in expected_stale_ids)
        or len(expected_stale_ids) != len(set(expected_stale_ids))
    ):
        failures.add("fail-stale-fact-oracle")
        expected_stale_ids = []
        opaque = True

    observed_assessments: dict[str, dict[str, Any]] = {}
    assessments = response.get("assertionAssessments")
    if not isinstance(assessments, list):
        failures.add("fail-stale-assessment-list")
        assessments = []
        opaque = True
    for index, item in enumerate(assessments):
        if not isinstance(item, dict) or not isinstance(item.get("id"), str):
            failures.add("fail-stale-assessment-shape")
            losses["missingEvidence"].add(f"stale:index-{index}")
            opaque = True
            continue
        assertion_id = item["id"]
        if assertion_id in observed_assessments:
            failures.add("fail-stale-assessment-duplicate")
            opaque = True
            continue
        observed_assessments[assertion_id] = item
        if (
            set(item) != {"id", "verdict", "evidence"}
            or item.get("verdict") not in {"accepted", "rejected", "unknown"}
        ):
            failures.add("fail-stale-assessment-shape")
            opaque = True
        if not _non_empty_evidence(item.get("evidence")):
            losses["missingEvidence"].add(f"stale:{assertion_id}")

    expected_stale_set = set(expected_stale_ids)
    observed_stale_set = set(observed_assessments)
    missing_stale = expected_stale_set - observed_stale_set
    losses["unresolvedStale"].update(missing_stale)
    if missing_stale:
        failures.add("fail-stale-assessment-omission")
    if observed_stale_set - expected_stale_set:
        failures.add("fail-stale-assessment-extra")
        opaque = True
    for assertion_id in expected_stale_set & observed_stale_set:
        verdict = observed_assessments[assertion_id].get("verdict")
        if verdict == "accepted":
            losses["acceptedStale"].add(assertion_id)
        elif verdict == "unknown":
            losses["unresolvedStale"].add(assertion_id)
    if losses["acceptedStale"]:
        failures.add("fail-stale-assertion-accepted")
    if losses["unresolvedStale"]:
        failures.add("fail-stale-assertion-unresolved")
    if losses["missingEvidence"]:
        failures.add("fail-provenance-evidence")

    for field, claim_id in UNSUPPORTED_CLAIM_FIELDS.items():
        value = response.get(field)
        if value is True:
            losses["unsupportedClaim"].add(claim_id)
        elif not isinstance(value, bool):
            failures.add("fail-unsupported-claim-field-shape")
            opaque = True
    if losses["unsupportedClaim"]:
        failures.add("fail-unsupported-claim")

    digest_failures = {
        code
        for code in failures
        if code.endswith("-digest-binding")
    }
    if digest_failures:
        opaque = True

    canonical_status: str | None = None
    canonical_error_class: str | None = None
    try:
        _parse_context_response(raw_response)
        canonical_result = canonical_scorer(
            raw_response,
            packet,
            parent_evidence,
            protocol_path,
        )
        canonical_status = canonical_result.get("status")
        if not isinstance(canonical_status, str):
            canonical_status = None
            canonical_error_class = "InvalidCanonicalResult"
    except (TypeError, ValueError, RuntimeError, KeyError) as exc:
        canonical_error_class = type(exc).__name__

    exact_sets = {
        name: sorted(values)
        for name, values in losses.items()
    }
    exact_counts = {
        name: len(values)
        for name, values in exact_sets.items()
    }
    any_loss = any(exact_counts.values())
    if opaque:
        ledger_status = "invalid-opaque"
    elif any_loss or failures:
        ledger_status = "measured-loss"
    else:
        ledger_status = "measured-zero-loss"

    return {
        "schema": 1,
        "id": LEDGER_ID,
        "scenario": "ABL-CTX-HANDOFF-01",
        "arm": "C-receiver",
        "status": ledger_status,
        "sets": exact_sets,
        "counts": exact_counts,
        "opaque": opaque,
        "failureCodes": sorted(failures),
        "failureCodeCount": len(failures),
        "inputBindings": bindings,
        "canonical": {
            "scorer": (
                "scripts.evaluate_skill_ablation_batch_01_protocol."
                "evaluate_context_raw_run"
            ),
            "status": canonical_status,
            "errorClass": canonical_error_class,
            "expectedControlStatus": PASSING_CANONICAL_STATUS,
            "verdictChangedByLedger": False,
            "evidenceClass": "deterministic-replay-not-live-host-proof",
        },
        "executionBoundary": {
            "agentDispatchCount": 0,
            "modelCallCount": 0,
            "threadCreated": False,
            "remoteGitUsed": False,
            "hostConfigurationChanged": False,
        },
        "claimBoundary": {
            "receiverRecoveryProved": False,
            "skillInvocationProved": False,
            "freshSessionProved": False,
            "losslessProved": False,
            "atomicityProved": False,
            "dirtyOwnershipProved": False,
            "agentsAdherenceProved": False,
            "weakAgentBehaviorProved": False,
            "crossHostBehaviorProved": False,
        },
    }


__all__ = [
    "LEDGER_ID",
    "LOSS_SET_NAMES",
    "evaluate_receiver_delta_ledger",
]
