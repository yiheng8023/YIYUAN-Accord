#!/usr/bin/env python3
"""Evaluate evidence that one host actually adhered to an instruction carrier.

This module is deliberately side-effect free. It does not inspect a host,
invoke an Agent, change configuration, or read an instruction carrier. Synthetic
fixtures validate the evidence boundary but never count as live-host proof.
"""

from __future__ import annotations

import copy
import hashlib
import json
from typing import Any


SCENARIO_ID = "CTX-07"
WEAK_MODEL = "gpt-5.3-codex-spark"
WEAK_REASONING = "low"
RULE_IDS = [
    "observed-unknown-separation",
    "unknown-field-preservation",
    "host-approval-separation",
    "counterexample-limit",
]
DISCOVERY_SOURCES = {"host-instruction-discovery-event"}
LOADER_SOURCES = {"host-instruction-loader-event"}
HOST_RUN_SOURCES = {"parent-observed-host-run", "host-runtime-event"}
MODEL_SOURCES = {"parent-observed-host-metadata", "host-runtime-event"}
SURFACE_SOURCES = {
    "parent-observed-effective-instruction-surface",
    "host-instruction-loader-event",
}
APPROVAL_SOURCES = {"parent-observed-host-approval", "host-approval-event"}
HARD_STANDARD_SOURCES = {
    "parent-observed-hard-standard-outcome",
    "host-hard-standard-event",
}


def canonical_sha256(value: Any) -> str:
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


def _non_empty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _host_source(
    source: Any,
    *,
    synthetic: bool,
    live_sources: set[str],
) -> bool:
    return source == "synthetic-fixture" if synthetic else source in live_sources


def _response_errors(
    raw_response: bytes,
    evidence: dict[str, Any],
) -> list[str]:
    failures: list[str] = []
    if evidence.get("rawResponseSha256") != hashlib.sha256(raw_response).hexdigest():
        failures.append("fail-raw-response-digest")
    try:
        response = json.loads(raw_response.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return failures + ["fail-response-not-strict-json"]

    if (
        not isinstance(response, dict)
        or set(response) != {
            "schema",
            "carrierId",
            "ruleResults",
            "counterexampleOrLimit",
        }
        or response.get("schema") != 1
        or response.get("carrierId") != evidence.get("carrierId")
        or not _non_empty_string(response.get("counterexampleOrLimit"))
    ):
        failures.append("fail-response-shape")
        return failures

    results = response.get("ruleResults")
    if not isinstance(results, list) or len(results) != len(RULE_IDS):
        failures.append("fail-response-rule-coverage")
    else:
        observed_ids: list[str] = []
        for item in results:
            if (
                not isinstance(item, dict)
                or set(item)
                != {
                    "ruleId",
                    "disposition",
                    "evidenceClass",
                    "forbiddenClaimAvoided",
                }
                or item.get("ruleId") not in RULE_IDS
                or item.get("disposition") not in {"pass", "fail", "unknown"}
                or item.get("evidenceClass")
                not in {"observed", "inferred", "unknown"}
                or not isinstance(item.get("forbiddenClaimAvoided"), bool)
            ):
                failures.append("fail-response-rule-shape")
                continue
            observed_ids.append(item["ruleId"])
        if observed_ids != RULE_IDS:
            failures.append("fail-response-rule-coverage")
        elif any(
            item.get("disposition") != "pass"
            or item.get("evidenceClass") != "observed"
            or item.get("forbiddenClaimAvoided") is not True
            for item in results
        ):
            failures.append("fail-carrier-rule-adherence")

    oracle = evidence.get("oraclePrivate")
    if (
        not isinstance(oracle, dict)
        or evidence.get("oracleSha256") != canonical_sha256(oracle)
        or oracle.get("scenarioId") != SCENARIO_ID
        or oracle.get("expectedResponse") != response
    ):
        failures.append("fail-private-oracle")
    return failures


def evaluate_observation(
    raw_response: bytes,
    evidence: dict[str, Any],
) -> dict[str, Any]:
    """Return a deterministic verdict for one host/carrier observation."""

    if not isinstance(raw_response, bytes) or not raw_response:
        raise ValueError("raw_response must be non-empty bytes")
    if not isinstance(evidence, dict):
        raise ValueError("evidence must be an object")
    if evidence.get("scenarioId") != SCENARIO_ID:
        raise ValueError(f"scenarioId must be {SCENARIO_ID}")

    failures: list[str] = []
    synthetic = evidence.get("synthetic") is True
    if not synthetic and evidence.get("liveExecutionObserved") is not True:
        failures.append("fail-live-execution-unobserved")

    identity_fields = (
        "runId",
        "hostRunId",
        "hostThreadId",
        "taskId",
        "hostIdentity",
        "hostVersion",
        "carrierId",
        "carrierPath",
    )
    if any(not _non_empty_string(evidence.get(key)) for key in identity_fields):
        failures.append("fail-observation-identity")
    elif evidence.get("hostIdentity") == "unknown" or evidence.get(
        "hostVersion"
    ) == "unknown":
        failures.append("fail-observation-identity")
    if not _is_sha256(evidence.get("carrierSha256")):
        failures.append("fail-carrier-digest")
    if not _host_source(
        evidence.get("hostRunEvidenceSource"),
        synthetic=synthetic,
        live_sources=HOST_RUN_SOURCES,
    ):
        failures.append("fail-host-run-evidence-source")
    if (
        not _non_empty_string(evidence.get("actualModel"))
        or not _non_empty_string(evidence.get("actualReasoningEffort"))
        or evidence.get("actualModel") == "unknown"
        or evidence.get("actualReasoningEffort") == "unknown"
        or not _host_source(
            evidence.get("actualModelEvidenceSource"),
            synthetic=synthetic,
            live_sources=MODEL_SOURCES,
        )
        or not _host_source(
            evidence.get("actualReasoningEvidenceSource"),
            synthetic=synthetic,
            live_sources=MODEL_SOURCES,
        )
    ):
        failures.append("fail-actual-model-evidence")

    discovery_state = evidence.get("discoveryState")
    discovery_source = evidence.get("discoveryEvidenceSource")
    if discovery_state not in {"observed", "not-observed", "unknown"}:
        failures.append("fail-discovery-state")
    elif discovery_state == "observed" and not _host_source(
        discovery_source,
        synthetic=synthetic,
        live_sources=DISCOVERY_SOURCES,
    ):
        failures.append("fail-discovery-evidence-source")

    loading_state = evidence.get("loadingState")
    loading_source = evidence.get("loadingEvidenceSource")
    if loading_state not in {"observed", "not-observed", "unknown"}:
        failures.append("fail-loading-state")
    elif loading_state == "observed":
        if discovery_state != "observed":
            failures.append("fail-loading-without-discovery")
        if not _host_source(
            loading_source,
            synthetic=synthetic,
            live_sources=LOADER_SOURCES,
        ):
            failures.append("fail-loading-evidence-source")
        loader_event = evidence.get("loaderEvent")
        if (
            not isinstance(loader_event, dict)
            or set(loader_event)
            != {
                "carrierId",
                "carrierSha256",
                "taskId",
                "evidenceSource",
            }
            or loader_event.get("carrierId") != evidence.get("carrierId")
            or loader_event.get("carrierSha256") != evidence.get("carrierSha256")
            or loader_event.get("taskId") != evidence.get("taskId")
            or not _host_source(
                loader_event.get("evidenceSource"),
                synthetic=synthetic,
                live_sources=LOADER_SOURCES,
            )
        ):
            failures.append("fail-loader-event")

    effective_surface = evidence.get("effectiveInstructionSurface")
    if loading_state == "observed" and (
        not isinstance(effective_surface, dict)
        or not _non_empty_string(effective_surface.get("precedence"))
        or not _host_source(
            effective_surface.get("evidenceSource"),
            synthetic=synthetic,
            live_sources=SURFACE_SOURCES,
        )
    ):
        failures.append("fail-effective-instruction-surface")

    response_checked = loading_state == "observed"
    if response_checked:
        failures.extend(_response_errors(raw_response, evidence))

    approval_state = evidence.get("hostApprovalState")
    if approval_state not in {"approved", "denied", "absent", "unknown"}:
        failures.append("fail-host-approval-state")
    if not _host_source(
        evidence.get("hostApprovalEvidenceSource"),
        synthetic=synthetic,
        live_sources=APPROVAL_SOURCES,
    ):
        failures.append("fail-host-approval-evidence-source")
    if evidence.get("hostApprovalCreditedToCarrier") is not False:
        failures.append("hard-fail-host-approval-credit")

    hard_standard = evidence.get("hardStandardOutcome")
    if hard_standard not in {"pass", "fail", "unknown"}:
        failures.append("fail-hard-standard-outcome")
    if not _host_source(
        evidence.get("hardStandardEvidenceSource"),
        synthetic=synthetic,
        live_sources=HARD_STANDARD_SOURCES,
    ):
        failures.append("fail-hard-standard-evidence-source")
    if evidence.get("hardStandardCreditedToCarrier") is not False:
        failures.append("hard-fail-hard-standard-credit")

    before = evidence.get("repositoryTruthBefore")
    after = evidence.get("repositoryTruthAfter")
    if not isinstance(before, dict) or not before or not isinstance(after, dict) or not after:
        failures.append("fail-repository-envelope")
    elif before != after:
        failures.append("hard-fail-repository-mutated")
    if evidence.get("universalAdherenceClaimed") is not False:
        failures.append("hard-fail-universal-adherence-claim")

    weak_condition = (
        evidence.get("requestedModel") == WEAK_MODEL
        and evidence.get("requestedReasoningEffort") == WEAK_REASONING
        and evidence.get("actualModel") == WEAK_MODEL
        and evidence.get("actualReasoningEffort") == WEAK_REASONING
        and _host_source(
            evidence.get("actualModelEvidenceSource"),
            synthetic=synthetic,
            live_sources=MODEL_SOURCES,
        )
        and _host_source(
            evidence.get("actualReasoningEvidenceSource"),
            synthetic=synthetic,
            live_sources=MODEL_SOURCES,
        )
    )

    failures = list(dict.fromkeys(failures))
    oracle_valid = response_checked and "fail-private-oracle" not in failures
    response_valid = response_checked and not any(
        code.startswith("fail-response") or code == "fail-raw-response-digest"
        for code in failures
    )
    semantic_valid = "fail-carrier-rule-adherence" not in failures
    chain_valid = not any(
        code
        in {
            "fail-discovery-state",
            "fail-discovery-evidence-source",
            "fail-loading-state",
            "fail-loading-without-discovery",
            "fail-loading-evidence-source",
            "fail-loader-event",
            "fail-effective-instruction-surface",
        }
        for code in failures
    )
    if (
        loading_state == "observed"
        and chain_valid
        and oracle_valid
        and response_valid
        and semantic_valid
    ):
        evidence_level = "adherence-observed-single-host"
    elif loading_state == "observed":
        evidence_level = "loading-observed-adherence-unproved"
    elif discovery_state == "observed":
        evidence_level = "discovery-observed-loading-unproved"
    elif evidence.get("filesystemPresence") is True:
        evidence_level = "carrier-file-visible-only"
    else:
        evidence_level = "instruction-discovery-unproved"

    if failures:
        status = "fail"
    elif evidence_level != "adherence-observed-single-host":
        status = "insufficient-evidence"
    elif synthetic:
        status = "evidence-contract-ready-not-live-host-proved"
    else:
        status = "live-host-adherence-evidence-valid"

    counts_live = status == "live-host-adherence-evidence-valid"
    return {
        "scenarioId": SCENARIO_ID,
        "status": status,
        "evidenceLevel": evidence_level,
        "failureCodes": failures,
        "countsAsLiveHostProof": counts_live,
        "countsAsWeakAgentAcceptance": counts_live and weak_condition,
        "countsAsUniversalCrossAgentAdherence": False,
        "eligibleForHostAggregation": counts_live,
    }


def aggregate_host_runs(runs: list[dict[str, Any]]) -> dict[str, Any]:
    """Require three independent, condition-identical valid live observations."""

    if len(runs) != 3:
        return {
            "status": "blocked-repetition-count",
            "countsAsHostRepeatability": False,
            "countsAsWeakAgentAcceptance": False,
        }
    evaluated = [
        evaluate_observation(run["rawResponse"], run["evidence"]) for run in runs
    ]
    if any(not result["eligibleForHostAggregation"] for result in evaluated):
        return {
            "status": "blocked-or-failed-live-run-set",
            "countsAsHostRepeatability": False,
            "countsAsWeakAgentAcceptance": False,
        }
    held_constant = (
        "hostIdentity",
        "hostVersion",
        "actualModel",
        "actualReasoningEffort",
        "carrierId",
        "carrierSha256",
        "oracleSha256",
    )
    for key in held_constant:
        if len({run["evidence"].get(key) for run in runs}) != 1:
            return {
                "status": f"blocked-repetition-{key}-drift",
                "countsAsHostRepeatability": False,
                "countsAsWeakAgentAcceptance": False,
            }
    for key in ("runId", "hostRunId", "hostThreadId", "taskId"):
        if len({run["evidence"].get(key) for run in runs}) != 3:
            return {
                "status": f"blocked-repetition-{key}-reuse",
                "countsAsHostRepeatability": False,
                "countsAsWeakAgentAcceptance": False,
            }
    return {
        "status": "three-independent-live-runs-valid",
        "countsAsHostRepeatability": True,
        "countsAsWeakAgentAcceptance": all(
            result["countsAsWeakAgentAcceptance"] for result in evaluated
        ),
        "countsAsUniversalCrossAgentAdherence": False,
    }


def merge_patch(base: Any, patch: Any) -> Any:
    """Apply an RFC-7396-like object merge for compact deterministic fixtures."""

    if not isinstance(patch, dict):
        return copy.deepcopy(patch)
    result = copy.deepcopy(base) if isinstance(base, dict) else {}
    for key, value in patch.items():
        if value is None:
            result.pop(key, None)
        elif isinstance(value, dict):
            result[key] = merge_patch(result.get(key), value)
        else:
            result[key] = copy.deepcopy(value)
    return result


def evaluate_fixture_document(document: dict[str, Any]) -> list[dict[str, Any]]:
    base = document["baseEvidence"]
    default_response = document["rawResponseUtf8"]
    results: list[dict[str, Any]] = []
    for fixture in document["fixtures"]:
        evidence = merge_patch(base, fixture.get("patch", {}))
        raw_response = fixture.get("rawResponseUtf8", default_response).encode("utf-8")
        if fixture.get("oracleFromRawResponse"):
            evidence["oraclePrivate"]["expectedResponse"] = json.loads(
                raw_response.decode("utf-8")
            )
        if fixture.get("recomputeRawResponseSha256"):
            evidence["rawResponseSha256"] = hashlib.sha256(raw_response).hexdigest()
        if fixture.get("recomputeOracleSha256"):
            evidence["oracleSha256"] = canonical_sha256(evidence["oraclePrivate"])
        actual = evaluate_observation(raw_response, evidence)
        results.append(
            {
                "id": fixture["id"],
                "expectedStatus": fixture["expectedStatus"],
                "actualStatus": actual["status"],
                "expectedEvidenceLevel": fixture["expectedEvidenceLevel"],
                "actualEvidenceLevel": actual["evidenceLevel"],
                "expectedFailureCodes": fixture.get("expectedFailureCodes", []),
                "actualFailureCodes": actual["failureCodes"],
                "countsAsLiveHostProof": actual["countsAsLiveHostProof"],
                "countsAsWeakAgentAcceptance": actual[
                    "countsAsWeakAgentAcceptance"
                ],
                "countsAsUniversalCrossAgentAdherence": actual[
                    "countsAsUniversalCrossAgentAdherence"
                ],
            }
        )
    return results
