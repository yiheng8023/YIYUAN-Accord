#!/usr/bin/env python3
"""Evaluate parent-observed same-thread MCP refresh evidence.

This module parses already-captured evidence only. It never starts a host,
changes configuration, invokes an MCP, opens a thread, or stops a process.
"""

from __future__ import annotations

import base64
import copy
import hashlib
import json
from typing import Any

try:
    from scripts.build_mcp_lifecycle_trial_skeleton import validate_trial_skeleton
    from scripts.evaluate_mcp_task_selection_decision import canonical_sha256
except ModuleNotFoundError:
    from build_mcp_lifecycle_trial_skeleton import validate_trial_skeleton
    from evaluate_mcp_task_selection_decision import canonical_sha256


EVENT_ROLES = (
    "pre-status",
    "baseline-direct-call",
    "config-delta",
    "reload-request",
    "reload-response",
    "active-turn",
    "post-direct-call",
    "post-status",
    "config-restore",
)
CLAIM_KEYS = {
    "oldRuntimeReleaseProved",
    "taskEndReleaseProved",
    "leaseProved",
    "referenceCountProved",
    "resourceBenefitProved",
    "desktopParityProved",
    "globalConfigMutationAuthorized",
    "reloadAloneProvesCausality",
}
LIVE_EVENT_SOURCE = "parent-captured-raw-bytes"
SYNTHETIC_EVENT_SOURCE = "synthetic-fixture"


def _sha256(value: Any) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(
        character in "0123456789abcdef" for character in value
    )


def _bound(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _result(classification: str, *, live_transition: bool = False) -> dict[str, Any]:
    return {
        "classification": classification,
        "countsAsLiveHostProof": live_transition,
        "countsAsSameThreadTransitionProof": live_transition,
        "countsAsTaskEndReleaseProof": False,
        "countsAsResourceBenefitProof": False,
        "countsAsCrossHostProof": False,
    }


def _decode_artifact(artifacts: dict[str, Any], event: dict[str, Any]) -> Any:
    encoded = artifacts.get(event.get("artifactRef"))
    if not isinstance(encoded, str):
        raise ValueError("missing event artifact")
    raw = base64.b64decode(encoded, validate=True)
    if hashlib.sha256(raw).hexdigest() != event.get("artifactSha256"):
        raise ValueError("event artifact digest mismatch")
    return json.loads(raw.decode("utf-8"))


def _event_envelope_failure(
    evidence: dict[str, Any],
) -> tuple[str | None, dict[str, dict[str, Any]]]:
    events = evidence.get("events")
    artifacts = evidence.get("artifactsBase64")
    if not isinstance(events, list) or not isinstance(artifacts, dict):
        return "fail-parent-event-envelope", {}

    observed: dict[str, dict[str, Any]] = {}
    previous_time = -1
    expected_keys = {
        "seq",
        "role",
        "threadId",
        "monotonicNs",
        "artifactRef",
        "artifactSha256",
        "evidenceSource",
        "details",
    }
    for index, event in enumerate(events, start=1):
        if (
            not isinstance(event, dict)
            or set(event) != expected_keys
            or event.get("seq") != index
            or event.get("role") not in EVENT_ROLES
            or event["role"] in observed
            or not isinstance(event.get("monotonicNs"), int)
            or event["monotonicNs"] <= previous_time
            or not _bound(event.get("artifactRef"))
            or not _sha256(event.get("artifactSha256"))
            or not isinstance(event.get("details"), dict)
        ):
            return "fail-parent-event-envelope", {}
        previous_time = event["monotonicNs"]
        try:
            decoded = _decode_artifact(artifacts, event)
        except (ValueError, TypeError, json.JSONDecodeError):
            return "fail-parent-event-envelope", {}
        if decoded != event["details"]:
            return "fail-parent-event-envelope", {}
        observed[event["role"]] = event

    if "active-turn" not in observed and "reload-response" in observed:
        if observed["reload-response"]["details"].get("accepted") is True:
            return "reload-accepted-active-turn-unobserved", observed
    if tuple(event["role"] for event in events) != EVENT_ROLES:
        return "fail-parent-event-envelope", observed
    return None, observed


def evaluate_same_thread_refresh(
    evidence: dict[str, Any],
    lifecycle_skeleton: dict[str, Any],
    selection_packet: dict[str, Any],
) -> dict[str, Any]:
    """Classify one captured same-thread refresh evidence envelope."""

    if validate_trial_skeleton(lifecycle_skeleton, selection_packet):
        return _result("blocked-source-skeleton-binding")
    if lifecycle_skeleton.get("plannedLifecycleDimensions") != [
        "sameSessionSwitching"
    ]:
        return _result("blocked-source-skeleton-binding")
    if evidence.get("sourceSkeletonSha256") != lifecycle_skeleton.get(
        "skeletonSha256"
    ):
        return _result("blocked-source-skeleton-binding")

    synthetic = evidence.get("synthetic") is True
    if not synthetic and evidence.get("liveExecutionObserved") is not True:
        return _result("blocked-authority-or-host-binding")

    host = evidence.get("hostBinding")
    target_host = lifecycle_skeleton.get("targetHost", {})
    expected_host_keys = {
        "identity",
        "version",
        "platform",
        "protocolSchemaSha256",
        "adapterId",
        "adapterVersion",
        "appServerInstanceId",
        "appServerPid",
        "appServerCreateTime",
        "evidenceSource",
    }
    expected_source = SYNTHETIC_EVENT_SOURCE if synthetic else LIVE_EVENT_SOURCE
    if (
        not isinstance(host, dict)
        or set(host) != expected_host_keys
        or host.get("identity") != target_host.get("identity")
        or host.get("version") != target_host.get("version")
        or host.get("adapterVersion") != target_host.get("adapterVersion")
        or not all(
            _bound(host.get(key))
            for key in (
                "platform",
                "adapterId",
                "appServerInstanceId",
                "appServerCreateTime",
            )
        )
        or not isinstance(host.get("appServerPid"), int)
        or host["appServerPid"] <= 0
        or not _sha256(host.get("protocolSchemaSha256"))
        or host.get("evidenceSource") != expected_source
    ):
        return _result("blocked-authority-or-host-binding")

    authority = evidence.get("authority")
    if (
        not isinstance(authority, dict)
        or set(authority)
        != {
            "disposableHomeAuthorized",
            "configDeltaAuthorized",
            "reloadAuthorized",
            "activeTurnAuthorized",
            "restoreAuthorized",
            "userConfigRead",
            "authOrSecretRead",
        }
        or any(
            authority.get(key) is not True
            for key in (
                "disposableHomeAuthorized",
                "configDeltaAuthorized",
                "reloadAuthorized",
                "activeTurnAuthorized",
                "restoreAuthorized",
            )
        )
        or authority.get("userConfigRead") is not False
        or authority.get("authOrSecretRead") is not False
    ):
        return _result("blocked-authority-or-host-binding")

    selected = lifecycle_skeleton.get("selectedMcpPayloads")
    target = evidence.get("target")
    if (
        not isinstance(selected, list)
        or len(selected) != 1
        or not isinstance(target, dict)
        or set(target) != {
            "identity",
            "source",
            "revision",
            "sourceSha256",
            "semanticKey",
            "expectedTransition",
        }
        or {key: target.get(key) for key in selected[0]} != selected[0]
        or not _bound(target.get("semanticKey"))
        or target.get("expectedTransition")
        not in {"available-to-unavailable", "unavailable-to-available"}
    ):
        return _result("blocked-authority-or-host-binding")

    claim = evidence.get("claimBoundary")
    if (
        not isinstance(claim, dict)
        or set(claim) != CLAIM_KEYS
        or any(value is not False for value in claim.values())
    ):
        return _result("hard-fail-lifecycle-claim-promotion")

    event_failure, events = _event_envelope_failure(evidence)
    if event_failure:
        return _result(event_failure)
    if any(event.get("threadId") != evidence.get("threadId") for event in events.values()):
        return _result("fail-same-thread-identity")
    if any(event.get("evidenceSource") != expected_source for event in events.values()):
        return _result("fail-parent-event-envelope")

    configuration = evidence.get("configuration")
    if (
        not isinstance(configuration, dict)
        or set(configuration)
        != {"initialSha256", "changedSha256", "restoredSha256", "changedKeys"}
        or not all(
            _sha256(configuration.get(key))
            for key in ("initialSha256", "changedSha256", "restoredSha256")
        )
        or configuration["initialSha256"] == configuration["changedSha256"]
        or configuration.get("changedKeys") != [target["semanticKey"]]
        or events["config-delta"]["details"]
        != {
            "configSha256": configuration["changedSha256"],
            "changedKeys": [target["semanticKey"]],
        }
    ):
        return _result("fail-config-delta-scope")
    if (
        configuration["restoredSha256"] != configuration["initialSha256"]
        or events["config-restore"]["details"]
        != {"configSha256": configuration["restoredSha256"]}
    ):
        return _result("fail-config-restore")
    if events["reload-response"]["details"].get("accepted") is not True:
        return _result("same-thread-actuation-unproved-or-falsified")
    if (
        events["pre-status"]["details"].get("diagnosticOnly") is not True
        or events["post-status"]["details"].get("diagnosticOnly") is not True
        or events["active-turn"]["details"].get("completed") is not True
        or not _bound(events["active-turn"]["details"].get("turnId"))
    ):
        return _result("fail-parent-event-envelope")

    baseline = events["baseline-direct-call"]["details"]
    post = events["post-direct-call"]["details"]
    if (
        set(baseline) != {"outcome", "runtimeInstanceId"}
        or set(post) != {"outcome", "runtimeInstanceId"}
        or baseline.get("outcome") not in {"available", "unavailable"}
        or post.get("outcome") not in {"available", "unavailable"}
        or not _bound(baseline.get("runtimeInstanceId"))
        or not _bound(post.get("runtimeInstanceId"))
    ):
        return _result("fail-parent-event-envelope")

    expected_outcomes = (
        ("available", "unavailable")
        if target["expectedTransition"] == "available-to-unavailable"
        else ("unavailable", "available")
    )
    direct_transition = (baseline["outcome"], post["outcome"]) == expected_outcomes
    status_transition = (
        events["pre-status"]["details"].get("reportedToolState")
        != events["post-status"]["details"].get("reportedToolState")
    )
    if status_transition and not direct_transition:
        return _result("same-thread-status-runtime-divergence")
    if not direct_transition:
        return _result("same-thread-actuation-unproved-or-falsified")

    release = evidence.get("releaseObservation")
    if release != {
        "state": "not-observed",
        "cause": "not-claimed",
        "evidenceSource": expected_source,
    }:
        return _result("release-unknown-exact-ownership-or-causation-missing")
    if synthetic:
        return _result("evidence-contract-ready-not-live-host-proved")
    return _result(
        "observed-same-thread-active-turn-tool-transition-"
        "release-unknown-single-host",
        live_transition=True,
    )


def merge_patch(base: Any, patch: Any) -> Any:
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


def materialize_synthetic_event_artifacts(evidence: dict[str, Any]) -> None:
    artifacts: dict[str, str] = {}
    for event in evidence.get("events", []):
        raw = json.dumps(
            event["details"],
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        ref = f"artifact-{event['seq']:02d}-{event['role']}"
        event["artifactRef"] = ref
        event["artifactSha256"] = hashlib.sha256(raw).hexdigest()
        artifacts[ref] = base64.b64encode(raw).decode("ascii")
    evidence["artifactsBase64"] = artifacts


def evaluate_fixture_document(
    document: dict[str, Any],
    lifecycle_skeleton: dict[str, Any],
    selection_packet: dict[str, Any],
) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    base_evidence = copy.deepcopy(document["baseEvidence"])
    base_evidence["sourceSkeletonSha256"] = lifecycle_skeleton["skeletonSha256"]
    for fixture in document["fixtures"]:
        evidence = merge_patch(base_evidence, fixture.get("patch", {}))
        if fixture.get("dropEventRoles"):
            dropped = set(fixture["dropEventRoles"])
            evidence["events"] = [
                event for event in evidence["events"] if event["role"] not in dropped
            ]
            for index, event in enumerate(evidence["events"], start=1):
                event["seq"] = index
        for role, patch in fixture.get("eventPatches", {}).items():
            event = next(item for item in evidence["events"] if item["role"] == role)
            updated = merge_patch(event, patch)
            event.clear()
            event.update(updated)
        materialize_synthetic_event_artifacts(evidence)
        actual = evaluate_same_thread_refresh(
            evidence,
            lifecycle_skeleton,
            selection_packet,
        )
        results.append(
            {
                "id": fixture["id"],
                "expected": fixture["expected"],
                "actual": actual["classification"],
                "countsAsLiveHostProof": actual["countsAsLiveHostProof"],
                "countsAsTaskEndReleaseProof": actual[
                    "countsAsTaskEndReleaseProof"
                ],
            }
        )
    return results
