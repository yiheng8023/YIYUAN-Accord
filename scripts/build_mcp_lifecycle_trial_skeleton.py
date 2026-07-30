#!/usr/bin/env python3
"""Bind an offline MCP selection decision to a future lifecycle trial skeleton.

This bridge is deliberately narrower than either source contract.  It reuses
the selection evaluator and the lifecycle dimension vocabulary, but never
starts an MCP, observes a host, or evaluates lifecycle events.
"""

from __future__ import annotations

import copy
import hashlib
import json
from typing import Any

try:
    from scripts.evaluate_mcp_task_lifecycle_evidence import REQUIRED_DIMENSIONS
    from scripts.evaluate_mcp_task_selection_decision import (
        canonical_sha256,
        evaluate_selection,
    )
except ModuleNotFoundError:  # Direct execution from the repository's scripts dir.
    from evaluate_mcp_task_lifecycle_evidence import REQUIRED_DIMENSIONS
    from evaluate_mcp_task_selection_decision import (
        canonical_sha256,
        evaluate_selection,
    )


SKELETON_ID = "mcp-lifecycle-trial-skeleton-2026-07-24"
SKELETON_STATUS = "offline-lifecycle-trial-skeleton-ready-no-host-actuation-proof"
OBSERVATION_KEYS = {
    "activationState",
    "acquireEvents",
    "releaseEvents",
    "exitEvents",
    "processObservations",
    "resourceObservations",
    "approvalState",
}
CLAIM_KEYS = {
    "activationProved",
    "releaseProved",
    "leaseProved",
    "referenceCountProved",
    "taskEndExitProved",
    "duplicateFreedomProved",
    "crashRecoveryProved",
    "processOwnershipProved",
    "resourceBenefitProved",
    "sameSessionSwitchingProved",
    "weakAgentAcceptanceProved",
    "crossHostSupportProved",
    "fullLifecycleCoverageProved",
}


def _sha256(value: Any) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(
        character in "0123456789abcdef" for character in value
    )


def _bound(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _skeleton_digest(skeleton: dict[str, Any]) -> str:
    body = copy.deepcopy(skeleton)
    body.pop("skeletonSha256", None)
    return canonical_sha256(body)


def _task_contract(selection_task: dict[str, Any]) -> dict[str, Any]:
    """Keep the complete task semantics that selection used, not only IDs."""

    return {
        "taskId": selection_task["taskId"],
        "phaseId": selection_task["phaseId"],
        "concreteUseCase": selection_task["concreteUseCase"],
        "acceptanceSurface": copy.deepcopy(selection_task["acceptanceSurface"]),
        "requiredCapabilityIds": copy.deepcopy(selection_task["requiredCapabilityIds"]),
    }


def _selected_payloads(selection_packet: dict[str, Any]) -> list[dict[str, str]]:
    selected = selection_packet["selectedMinimalSet"]
    candidates = {
        candidate["identity"]: candidate for candidate in selection_packet["candidates"]
    }
    return [
        {
            "identity": identity,
            "source": candidates[identity]["source"],
            "revision": candidates[identity]["revision"],
            "sourceSha256": candidates[identity]["sourceSha256"],
        }
        for identity in selected
    ]


def build_trial_skeleton(
    selection_packet: dict[str, Any],
    *,
    lifecycle_dimensions: list[str] | None = None,
) -> dict[str, Any]:
    """Create a no-observation lifecycle packet from one valid selection packet."""

    verdict = evaluate_selection(selection_packet)
    if verdict["status"] == "offline-no-mcp-needed-contract-valid":
        raise ValueError("selection packet contains no MCP selected for a lifecycle trial")
    if verdict["status"] != "offline-selection-contract-valid-no-host-actuation-proof":
        raise ValueError("selection packet is not a valid selected offline decision")

    dimensions = list(REQUIRED_DIMENSIONS) if lifecycle_dimensions is None else lifecycle_dimensions
    if (
        not isinstance(dimensions, list)
        or not dimensions
        or len(dimensions) != len(set(dimensions))
        or any(dimension not in REQUIRED_DIMENSIONS for dimension in dimensions)
    ):
        raise ValueError("lifecycle_dimensions must be a non-empty unique lifecycle subset")

    task = selection_packet["task"]
    release = selection_packet["releasePlan"]
    skeleton = {
        "schema": 1,
        "id": SKELETON_ID,
        "status": SKELETON_STATUS,
        "selectionBinding": {
            "selectionPacketSha256": selection_packet["packetSha256"],
            "selectionStatus": verdict["status"],
            "upstreamRoutingDecision": copy.deepcopy(selection_packet["upstreamRoutingDecision"]),
        },
        "targetHost": copy.deepcopy(selection_packet["targetHost"]),
        "task": {
            **_task_contract(task),
            "taskContractSha256": canonical_sha256(_task_contract(task)),
        },
        "selectedMcpPayloads": _selected_payloads(selection_packet),
        "releasePlan": {
            key: copy.deepcopy(release[key])
            for key in (
                "requestAtTaskOrPhaseEnd",
                "hostLifecycleCapability",
                "lifecycleEvidenceClass",
                "lifecycleEvidenceRef",
                "lifecycleEvidenceSha256",
                "observedHostIdentity",
                "observedHostVersion",
                "observedHostAdapterVersion",
                "fallback",
                "fallbackEvidenceState",
                "fallbackEvidenceClass",
                "fallbackEvidenceRef",
                "fallbackEvidenceSha256",
            )
        },
        "plannedLifecycleDimensions": sorted(dimensions),
        "observationEnvelope": {
            "activationState": "unobserved",
            "acquireEvents": [],
            "releaseEvents": [],
            "exitEvents": [],
            "processObservations": [],
            "resourceObservations": [],
            "approvalState": "unobserved",
        },
        "claimBoundary": {key: False for key in sorted(CLAIM_KEYS)},
        "countsAsLiveHostProof": False,
        "countsAsWeakAgentAcceptance": False,
        "countsAsActivationOrReleaseProof": False,
    }
    skeleton["skeletonSha256"] = _skeleton_digest(skeleton)
    return skeleton


def validate_trial_skeleton(
    skeleton: dict[str, Any], selection_packet: dict[str, Any]
) -> list[str]:
    """Validate a skeleton against its source selection packet without live work."""

    failures: list[str] = []
    if not isinstance(skeleton, dict):
        return ["fail-skeleton-shape"]
    expected_keys = {
        "schema", "id", "status", "selectionBinding", "targetHost", "task",
        "selectedMcpPayloads", "releasePlan", "plannedLifecycleDimensions",
        "observationEnvelope", "claimBoundary", "countsAsLiveHostProof",
        "countsAsWeakAgentAcceptance", "countsAsActivationOrReleaseProof",
        "skeletonSha256",
    }
    if set(skeleton) != expected_keys or skeleton.get("schema") != 1 or skeleton.get("id") != SKELETON_ID:
        failures.append("fail-skeleton-shape")
    if skeleton.get("status") != SKELETON_STATUS:
        failures.append("fail-skeleton-status")
    if not _sha256(skeleton.get("skeletonSha256")) or skeleton.get("skeletonSha256") != _skeleton_digest(skeleton):
        failures.append("fail-skeleton-digest")

    selection = evaluate_selection(selection_packet)
    if selection["status"] != "offline-selection-contract-valid-no-host-actuation-proof":
        failures.append("fail-source-selection-not-valid")
        return list(dict.fromkeys(failures))
    binding = skeleton.get("selectionBinding")
    if (
        not isinstance(binding, dict)
        or set(binding) != {"selectionPacketSha256", "selectionStatus", "upstreamRoutingDecision"}
        or binding.get("selectionPacketSha256") != selection_packet.get("packetSha256")
        or binding.get("selectionStatus") != selection["status"]
        or binding.get("upstreamRoutingDecision") != selection_packet.get("upstreamRoutingDecision")
    ):
        failures.append("fail-selection-binding")
    if skeleton.get("targetHost") != selection_packet.get("targetHost"):
        failures.append("fail-target-host-binding")
    task = skeleton.get("task")
    expected_task = selection_packet.get("task", {})
    expected_task_contract = _task_contract(expected_task)
    expected_skeleton_task = {
        **expected_task_contract,
        "taskContractSha256": canonical_sha256(expected_task_contract),
    }
    if task != expected_skeleton_task:
        failures.append("fail-task-phase-binding")
    if skeleton.get("selectedMcpPayloads") != _selected_payloads(selection_packet):
        failures.append("fail-selected-payload-binding")
    release = selection_packet.get("releasePlan", {})
    expected_release = {
        key: release.get(key)
        for key in (
            "requestAtTaskOrPhaseEnd", "hostLifecycleCapability", "lifecycleEvidenceClass",
            "lifecycleEvidenceRef", "lifecycleEvidenceSha256", "observedHostIdentity",
            "observedHostVersion", "observedHostAdapterVersion", "fallback",
            "fallbackEvidenceState", "fallbackEvidenceClass", "fallbackEvidenceRef",
            "fallbackEvidenceSha256",
        )
    }
    if skeleton.get("releasePlan") != expected_release:
        failures.append("fail-release-plan-binding")
    dimensions = skeleton.get("plannedLifecycleDimensions")
    if (
        not isinstance(dimensions, list)
        or dimensions != sorted(dimensions)
        or not dimensions
        or len(dimensions) != len(set(dimensions))
        or any(dimension not in REQUIRED_DIMENSIONS for dimension in dimensions)
    ):
        failures.append("fail-lifecycle-dimension-binding")
    observation = skeleton.get("observationEnvelope")
    if (
        not isinstance(observation, dict)
        or set(observation) != OBSERVATION_KEYS
        or observation.get("activationState") != "unobserved"
        or observation.get("approvalState") != "unobserved"
        or any(observation.get(key) != [] for key in (
            "acquireEvents", "releaseEvents", "exitEvents", "processObservations", "resourceObservations"
        ))
    ):
        failures.append("hard-fail-observation-or-actuation-smuggled")
    claim = skeleton.get("claimBoundary")
    if not isinstance(claim, dict) or set(claim) != CLAIM_KEYS or any(value is not False for value in claim.values()):
        failures.append("hard-fail-claim-promotion")
    if any(skeleton.get(key) is not False for key in (
        "countsAsLiveHostProof", "countsAsWeakAgentAcceptance", "countsAsActivationOrReleaseProof"
    )):
        failures.append("hard-fail-count-promotion")
    return list(dict.fromkeys(failures))


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


def evaluate_fixture_document(
    document: dict[str, Any],
    selection_packet: dict[str, Any],
) -> list[dict[str, Any]]:
    """Evaluate deterministic skeleton fixtures without calling a host."""

    base = build_trial_skeleton(
        selection_packet,
        lifecycle_dimensions=document["dimensions"],
    )
    results: list[dict[str, Any]] = []
    for fixture in document["fixtures"]:
        skeleton = merge_patch(base, fixture.get("patch", {}))
        if fixture.get("recomputeSkeletonSha256"):
            skeleton["skeletonSha256"] = _skeleton_digest(skeleton)
        failures = validate_trial_skeleton(skeleton, selection_packet)
        results.append(
            {
                "id": fixture["id"],
                "expectedFailures": fixture["expectedFailures"],
                "actualFailures": failures,
                "countsAsLiveHostProof": False,
                "countsAsWeakAgentAcceptance": False,
                "countsAsActivationOrReleaseProof": False,
            }
        )
    return results
