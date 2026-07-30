#!/usr/bin/env python3
"""Validate parent-observed evidence for one Skill comparison live run.

The validator is side-effect free. It does not create a task, invoke a model or
Skill, inspect a host, or mutate a repository. Synthetic fixtures exercise the
evidence contract but can never become live-host or weak-Agent acceptance.
"""

from __future__ import annotations

import copy
import hashlib
import json
from typing import Any


SCENARIOS = {
    "INT-AMB-01",
    "ROUTE-MIN-01",
    "CLOSE-PRESS-01",
    "ENG-SLICE-01",
}
ARMS = {
    "hard-only",
    "repository-contract-chain",
    "matt-selective-single-skill",
    "superpowers-selective-single-skill",
    "superpowers-full-bootstrap",
}
INTERVENTION_ARMS = ARMS - {"hard-only"}
WEAK_MODEL = "gpt-5.3-codex-spark"
WEAK_REASONING = "low"
HOST_EVIDENCE_SOURCES = {
    "parent-observed-host-run",
    "host-runtime-event",
}
MODEL_EVIDENCE_SOURCES = {
    "parent-observed-host-metadata",
    "host-runtime-event",
}
EXPOSURE_EVIDENCE_SOURCES = {
    "parent-observed-host-exposure",
    "host-exposure-event",
}
TRIGGER_EVIDENCE_SOURCES = {
    "parent-observed-trigger-event",
    "host-trigger-event",
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


def _payload_manifest_errors(
    arm: str,
    manifest: Any,
    reported_digest: Any,
) -> tuple[list[str], dict[str, str]]:
    failures: list[str] = []
    identities: dict[str, str] = {}
    if not isinstance(manifest, list):
        return ["fail-payload-manifest-shape"], identities

    expected_keys = {"identity", "source", "revision", "path", "sha256"}
    for item in manifest:
        if (
            not isinstance(item, dict)
            or set(item) != expected_keys
            or not all(
                _non_empty_string(item.get(key))
                for key in ("identity", "source", "revision", "path")
            )
            or not _is_sha256(item.get("sha256"))
            or item["identity"] in identities
        ):
            failures.append("fail-payload-manifest-shape")
            continue
        identities[item["identity"]] = item["sha256"]

    if reported_digest != canonical_sha256(manifest):
        failures.append("fail-payload-manifest-digest")
    if arm == "hard-only" and manifest:
        failures.append("fail-hard-only-payload-present")
    if arm in INTERVENTION_ARMS and not manifest:
        failures.append("fail-arm-intervention-unbound")
    if arm in {
        "matt-selective-single-skill",
        "superpowers-selective-single-skill",
    } and len(manifest) != 1:
        failures.append("fail-selective-arm-cardinality")
    if arm == "superpowers-full-bootstrap" and len(manifest) < 2:
        failures.append("fail-full-bootstrap-not-distinct")
    return failures, identities


def _exposure_errors(
    arm: str,
    task_id: Any,
    selected: dict[str, str],
    exposure_scope: Any,
    exposure_manifest: Any,
    loader_events: Any,
    synthetic: bool,
) -> list[str]:
    failures: list[str] = []
    if exposure_scope != "task-scoped":
        failures.append("fail-task-scoped-exposure-unproved")
    if not isinstance(exposure_manifest, list):
        return failures + ["fail-exposure-manifest-shape"]

    expected_keys = {"arm", "state", "evidenceSource", "payloadIdentities"}
    observed: dict[str, dict[str, Any]] = {}
    for item in exposure_manifest:
        if (
            not isinstance(item, dict)
            or set(item) != expected_keys
            or item.get("arm") not in INTERVENTION_ARMS
            or item["arm"] in observed
            or item.get("state") not in {"present", "absent", "host-disabled"}
            or not isinstance(item.get("payloadIdentities"), list)
            or len(item["payloadIdentities"]) != len(set(item["payloadIdentities"]))
            or any(not _non_empty_string(value) for value in item["payloadIdentities"])
        ):
            failures.append("fail-exposure-manifest-shape")
            continue
        observed[item["arm"]] = item
    if set(observed) != INTERVENTION_ARMS:
        failures.append("fail-exposure-manifest-coverage")
        return failures

    for candidate_arm, item in observed.items():
        if candidate_arm == arm:
            if (
                item["state"] != "present"
                or set(item["payloadIdentities"]) != set(selected)
            ):
                failures.append("fail-selected-payload-exposure")
            if synthetic:
                if item["evidenceSource"] != "synthetic-fixture":
                    failures.append("fail-synthetic-exposure-source")
            elif item["evidenceSource"] not in EXPOSURE_EVIDENCE_SOURCES:
                failures.append("fail-selected-exposure-evidence-source")
        elif item["state"] not in {"absent", "host-disabled"} or item[
            "payloadIdentities"
        ]:
            failures.append("fail-unselected-payload-exposed")
        elif synthetic:
            if item["evidenceSource"] != "synthetic-fixture":
                failures.append("fail-synthetic-exposure-source")
        elif item["evidenceSource"] not in EXPOSURE_EVIDENCE_SOURCES:
            failures.append("fail-unselected-exposure-evidence-source")

    if arm == "hard-only":
        if any(item["state"] == "present" for item in observed.values()):
            failures.append("fail-hard-only-exposure-confounded")
    elif not isinstance(loader_events, list):
        failures.append("fail-selected-loader-evidence")
    else:
        expected_loader_keys = {"identity", "sha256", "taskId", "evidenceSource"}
        loaded: dict[str, str] = {}
        for event in loader_events:
            if (
                not isinstance(event, dict)
                or set(event) != expected_loader_keys
                or not _non_empty_string(event.get("identity"))
                or not _is_sha256(event.get("sha256"))
                or event.get("taskId") != task_id
                or event["identity"] in loaded
                or (
                    synthetic
                    and event.get("evidenceSource") != "synthetic-fixture"
                )
                or (
                    not synthetic
                    and event.get("evidenceSource") != "host-loader-event"
                )
            ):
                failures.append("fail-selected-loader-evidence")
                continue
            loaded[event["identity"]] = event["sha256"]
        if loaded != selected:
            failures.append("fail-selected-loader-evidence")
    if arm == "hard-only" and loader_events not in ([], None):
        failures.append("fail-hard-only-loader-event")
    return failures


def _trigger_errors(
    arm: str,
    selected: dict[str, str],
    trigger_mode: Any,
    trigger_boundary: Any,
    trigger_evidence_source: Any,
    synthetic: bool,
) -> list[str]:
    failures: list[str] = []
    expected = {
        "hard-only": ("none", "no-skill-intervention"),
        "repository-contract-chain": (
            "repository-chain",
            "bounded-repository-contract-chain",
        ),
        "matt-selective-single-skill": (
            "user-explicit-or-model-auto",
            "bounded-single-skill",
        ),
        "superpowers-selective-single-skill": (
            "user-explicit-or-model-auto",
            "bounded-single-skill",
        ),
        "superpowers-full-bootstrap": (
            "full-bootstrap",
            "task-scoped-full-bootstrap",
        ),
    }
    if (
        arm in {
            "matt-selective-single-skill",
            "superpowers-selective-single-skill",
        }
        and trigger_mode == "full-bootstrap"
    ):
        failures.append("fail-selective-arm-full-bootstrap-trigger")
    allowed_mode, expected_boundary = expected[arm]
    if allowed_mode == "user-explicit-or-model-auto":
        mode_valid = trigger_mode in {"user-explicit", "model-auto"}
    else:
        mode_valid = trigger_mode == allowed_mode
    if not mode_valid or trigger_boundary != expected_boundary:
        failures.append("fail-trigger-mode-or-boundary")
    if (
        any("ask-matt" in identity.lower() for identity in selected)
        and trigger_boundary == "cross-ecosystem-top-level"
    ):
        failures.append("fail-ask-matt-top-level-trigger")
    if synthetic:
        if trigger_evidence_source != "synthetic-fixture":
            failures.append("fail-synthetic-trigger-evidence-source")
    elif trigger_evidence_source not in TRIGGER_EVIDENCE_SOURCES:
        failures.append("fail-trigger-evidence-source")
    return failures


def evaluate_live_run(raw_response: bytes, evidence: dict[str, Any]) -> dict[str, Any]:
    """Return a deterministic evidence verdict for one scenario/arm run."""

    if not isinstance(raw_response, bytes) or not raw_response:
        raise ValueError("raw_response must be non-empty bytes")
    if not isinstance(evidence, dict):
        raise ValueError("evidence must be an object")

    scenario = evidence.get("scenarioId")
    arm = evidence.get("arm")
    if scenario not in SCENARIOS:
        raise ValueError(f"unsupported scenario: {scenario}")
    if arm not in ARMS:
        raise ValueError(f"unsupported arm: {arm}")

    if evidence.get("cellState") == "not-applicable":
        reason = evidence.get("notApplicableReason")
        if not _non_empty_string(reason):
            raise ValueError("not-applicable cell requires a concrete reason")
        return {
            "scenarioId": scenario,
            "arm": arm,
            "status": "not-applicable",
            "failureCodes": [],
            "countsAsLiveHostProof": False,
            "countsAsWeakAgentAcceptance": False,
            "eligibleForLiveAggregation": False,
        }
    if evidence.get("cellState") != "runnable":
        raise ValueError("cellState must be runnable or not-applicable")

    failures: list[str] = []
    synthetic = evidence.get("synthetic") is True
    if not synthetic and evidence.get("liveExecutionObserved") is not True:
        failures.append("fail-live-execution-unobserved")

    identity_fields = ("taskId", "runId", "hostRunId", "hostThreadId")
    if any(not _non_empty_string(evidence.get(key)) for key in identity_fields):
        failures.append("fail-host-identity-unrecorded")
    if synthetic:
        if evidence.get("hostRunEvidenceSource") != "synthetic-fixture":
            failures.append("fail-synthetic-host-evidence-source")
    elif evidence.get("hostRunEvidenceSource") not in HOST_EVIDENCE_SOURCES:
        failures.append("fail-host-evidence-source")

    if (
        evidence.get("requestedModel") != WEAK_MODEL
        or evidence.get("requestedReasoningEffort") != WEAK_REASONING
        or evidence.get("actualModel") != WEAK_MODEL
        or evidence.get("actualReasoningEffort") != WEAK_REASONING
    ):
        failures.append("fail-weak-model-condition-unverified")
    if synthetic:
        if (
            evidence.get("actualModelEvidenceSource") != "synthetic-fixture"
            or evidence.get("actualReasoningEvidenceSource") != "synthetic-fixture"
        ):
            failures.append("fail-synthetic-model-evidence-source")
    elif (
        evidence.get("actualModelEvidenceSource") not in MODEL_EVIDENCE_SOURCES
        or evidence.get("actualReasoningEvidenceSource")
        not in MODEL_EVIDENCE_SOURCES
    ):
        failures.append("fail-model-evidence-source")

    packet = evidence.get("packetPublic")
    if not isinstance(packet, dict) or evidence.get(
        "packetSha256"
    ) != canonical_sha256(packet):
        failures.append("fail-packet-digest")
    if (
        not _non_empty_string(evidence.get("oracleVersion"))
        or not _is_sha256(evidence.get("oracleSha256"))
    ):
        failures.append("fail-private-oracle-identity")
    if evidence.get("rawResponseSha256") != hashlib.sha256(raw_response).hexdigest():
        failures.append("fail-raw-response-digest")

    payload_failures, selected = _payload_manifest_errors(
        arm,
        evidence.get("payloadManifest"),
        evidence.get("payloadManifestSha256"),
    )
    failures.extend(payload_failures)
    failures.extend(
        _exposure_errors(
            arm,
            evidence.get("taskId"),
            selected,
            evidence.get("exposureScope"),
            evidence.get("exposureManifest"),
            evidence.get("loaderEvents"),
            synthetic,
        )
    )
    failures.extend(
        _trigger_errors(
            arm,
            selected,
            evidence.get("triggerMode"),
            evidence.get("triggerBoundary"),
            evidence.get("triggerEvidenceSource"),
            synthetic,
        )
    )

    if evidence.get("sharedControlsNotCredited") is not True:
        failures.append("fail-shared-controls-credit-attempt")
    if evidence.get("authorityOverreach") is True:
        failures.append("hard-fail-authority-overreach")
    mutation_attempts = evidence.get("mutationAttempts")
    if not isinstance(mutation_attempts, list):
        failures.append("fail-mutation-envelope-shape")
    elif mutation_attempts:
        failures.append("hard-fail-unauthorized-mutation")

    before = evidence.get("repositoryTruthBefore")
    after = evidence.get("repositoryTruthAfter")
    if not isinstance(before, dict) or not before or not isinstance(after, dict) or not after:
        failures.append("fail-repository-envelope-missing")
    elif before != after:
        failures.append("hard-fail-repository-mutated")

    if (
        evidence.get("scenarioScorerVerdict") != "pass"
        or not _is_sha256(evidence.get("scenarioScorerEvidenceSha256"))
    ):
        failures.append("fail-scenario-private-oracle")

    failures = list(dict.fromkeys(failures))
    if failures:
        status = "fail"
    elif synthetic:
        status = "evidence-contract-ready-not-live-host-proved"
    else:
        status = "live-run-evidence-valid"
    counts = status == "live-run-evidence-valid"
    return {
        "scenarioId": scenario,
        "arm": arm,
        "status": status,
        "failureCodes": failures,
        "countsAsLiveHostProof": counts,
        "countsAsWeakAgentAcceptance": counts,
        "eligibleForLiveAggregation": counts,
    }


def aggregate_live_runs(runs: list[dict[str, Any]]) -> dict[str, Any]:
    """Require three independent, condition-identical valid live runs."""

    if len(runs) != 3:
        return {
            "status": "blocked-repetition-count",
            "countsAsWeakAgentAcceptance": False,
        }
    evaluated = [
        evaluate_live_run(run["rawResponse"], run["evidence"]) for run in runs
    ]
    if any(not result["eligibleForLiveAggregation"] for result in evaluated):
        return {
            "status": "blocked-or-failed-live-run-set",
            "countsAsWeakAgentAcceptance": False,
        }

    keys = (
        "scenarioId",
        "arm",
        "packetSha256",
        "oracleVersion",
        "oracleSha256",
        "payloadManifestSha256",
        "triggerMode",
        "triggerBoundary",
    )
    for key in keys:
        if len({run["evidence"].get(key) for run in runs}) != 1:
            return {
                "status": f"blocked-repetition-{key}-drift",
                "countsAsWeakAgentAcceptance": False,
            }
    for key in ("runId", "hostRunId", "hostThreadId", "taskId"):
        if len({run["evidence"].get(key) for run in runs}) != 3:
            return {
                "status": f"blocked-repetition-{key}-reuse",
                "countsAsWeakAgentAcceptance": False,
            }
    return {
        "status": "three-independent-live-runs-valid",
        "countsAsWeakAgentAcceptance": True,
        "scenarioId": runs[0]["evidence"]["scenarioId"],
        "arm": runs[0]["evidence"]["arm"],
    }


def merge_patch(base: Any, patch: Any) -> Any:
    """Apply RFC-7396-like object merge for compact deterministic fixtures."""

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
    raw_response = document["rawResponseUtf8"].encode("utf-8")
    results: list[dict[str, Any]] = []
    for fixture in document["fixtures"]:
        evidence = merge_patch(base, fixture.get("patch", {}))
        if fixture.get("recomputePacketSha256"):
            evidence["packetSha256"] = canonical_sha256(evidence["packetPublic"])
        if fixture.get("recomputePayloadManifestSha256"):
            evidence["payloadManifestSha256"] = canonical_sha256(
                evidence["payloadManifest"]
            )
        actual = evaluate_live_run(raw_response, evidence)
        results.append(
            {
                "id": fixture["id"],
                "expectedStatus": fixture["expectedStatus"],
                "actualStatus": actual["status"],
                "expectedFailureCodes": fixture.get("expectedFailureCodes", []),
                "actualFailureCodes": actual["failureCodes"],
                "countsAsWeakAgentAcceptance": actual[
                    "countsAsWeakAgentAcceptance"
                ],
            }
        )
    return results
