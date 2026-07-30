#!/usr/bin/env python3
"""Evaluate an offline task-to-MCP selection and release decision packet.

The evaluator refines an already-bound upstream routing decision inside the MCP
candidate class. It performs no discovery, installation, enablement, call,
release, process inspection, or configuration mutation. Synthetic fixtures can
validate packet semantics but never prove evidence references are true.
"""

from __future__ import annotations

import copy
import hashlib
import itertools
import json
from typing import Any


TRUSTED_SELECTED_STATES = {
    "runtime-owned",
    "official",
    "approved-reviewed",
    "synthetic-reviewed-fixture",
}
ALL_REVIEW_STATES = TRUSTED_SELECTED_STATES | {
    "candidate-unreviewed",
    "blocked",
}
EVIDENCE_CLASSES = {
    "synthetic-fixture",
    "recorded-static",
    "parent-observed",
    "observed-single-host",
}
HOST_LIFECYCLE_STATES = {
    "unknown",
    "startup-or-new-thread-profile-only",
    "documented-native-idle-timeout",
    "same-session-actuation-observed-for-exact-host",
}
FALLBACKS = {
    "startup-or-new-thread-profile",
    "documented-native-idle-timeout",
    "none-selected",
}
FORBIDDEN_PLACEHOLDERS = {
    "unknown",
    "unbound",
    "tbd",
    "todo",
    "n/a",
    "later",
}


def canonical_sha256(value: Any) -> str:
    encoded = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _non_empty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _bound_string(value: Any) -> bool:
    return _non_empty_string(value) and value.strip().lower() not in FORBIDDEN_PLACEHOLDERS


def _sha256(value: Any) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(character in "0123456789abcdef" for character in value)
    )


def _string_set(value: Any) -> set[str] | None:
    if (
        not isinstance(value, list)
        or not value
        or len(value) != len(set(value))
        or any(not _bound_string(item) for item in value)
    ):
        return None
    return set(value)


def _evidence_pointer_errors(
    evidence_class: Any,
    evidence_ref: Any,
    evidence_sha256: Any,
    code: str,
) -> list[str]:
    if (
        evidence_class not in EVIDENCE_CLASSES
        or not _bound_string(evidence_ref)
        or not _sha256(evidence_sha256)
    ):
        return [code]
    return []


def _candidate_errors(candidate: Any) -> list[str]:
    if not isinstance(candidate, dict):
        return ["fail-candidate-shape"]
    required_keys = {
        "identity",
        "source",
        "revision",
        "sourceSha256",
        "reviewState",
        "reviewEvidenceRef",
        "reviewEvidenceSha256",
        "capabilityIds",
        "surfaceAreaScore",
        "dataBoundary",
        "accountBoundary",
        "authorityBoundary",
        "costBoundary",
        "maintenanceState",
        "eligibleForSelection",
        "selected",
        "decisionReason",
    }
    if set(candidate) != required_keys:
        return ["fail-candidate-shape"]
    if any(
        not _bound_string(candidate.get(key))
        for key in (
            "identity",
            "source",
            "revision",
            "dataBoundary",
            "accountBoundary",
            "authorityBoundary",
            "costBoundary",
            "maintenanceState",
            "decisionReason",
        )
    ):
        return ["fail-candidate-boundary-unbound"]
    if (
        not _sha256(candidate.get("sourceSha256"))
        or not _bound_string(candidate.get("reviewEvidenceRef"))
        or not _sha256(candidate.get("reviewEvidenceSha256"))
        or candidate.get("reviewState") not in ALL_REVIEW_STATES
        or _string_set(candidate.get("capabilityIds")) is None
        or not isinstance(candidate.get("surfaceAreaScore"), int)
        or candidate["surfaceAreaScore"] <= 0
        or not isinstance(candidate.get("eligibleForSelection"), bool)
        or not isinstance(candidate.get("selected"), bool)
    ):
        return ["fail-candidate-shape"]
    if candidate["selected"] and (
        not candidate["eligibleForSelection"]
        or candidate["reviewState"] not in TRUSTED_SELECTED_STATES
    ):
        return ["fail-selected-candidate-not-admitted"]
    return []


def _minimal_selection_errors(
    candidates: list[dict[str, Any]],
    required_gap_ids: set[str],
    declared_selected: Any,
) -> tuple[list[str], list[str]]:
    failures: list[str] = []
    selected = [
        candidate
        for candidate in candidates
        if isinstance(candidate, dict) and candidate.get("selected") is True
    ]
    selected_ids = [
        candidate.get("identity")
        for candidate in selected
        if _bound_string(candidate.get("identity"))
    ]
    if (
        not isinstance(declared_selected, list)
        or len(declared_selected) != len(set(declared_selected))
        or any(not _bound_string(item) for item in declared_selected)
        or declared_selected != selected_ids
    ):
        failures.append("fail-selected-set-mismatch")

    eligible = [
        candidate
        for candidate in candidates
        if isinstance(candidate, dict)
        and candidate.get("eligibleForSelection") is True
        and candidate.get("reviewState") in TRUSTED_SELECTED_STATES
        and _string_set(candidate.get("capabilityIds")) is not None
        and isinstance(candidate.get("surfaceAreaScore"), int)
        and candidate["surfaceAreaScore"] > 0
    ]
    admitted_selected = [
        candidate
        for candidate in selected
        if candidate.get("eligibleForSelection") is True
        and candidate.get("reviewState") in TRUSTED_SELECTED_STATES
    ]
    selected_coverage = set().union(
        *(
            _string_set(candidate["capabilityIds"]) or set()
            for candidate in admitted_selected
        )
    ) if admitted_selected else set()
    if not required_gap_ids.issubset(selected_coverage):
        failures.append("fail-required-gap-coverage")

    eligible_sets: list[tuple[tuple[int, int], frozenset[str]]] = []
    for size in range(len(eligible) + 1):
        for combination in itertools.combinations(eligible, size):
            coverage = set().union(
                *(
                    _string_set(candidate["capabilityIds"]) or set()
                    for candidate in combination
                )
            ) if combination else set()
            if required_gap_ids.issubset(coverage):
                metric = (
                    len(combination),
                    sum(candidate["surfaceAreaScore"] for candidate in combination),
                )
                eligible_sets.append(
                    (
                        metric,
                        frozenset(candidate["identity"] for candidate in combination),
                    )
                )
    if not eligible_sets:
        failures.append("fail-no-admitted-candidate-cover")
    else:
        best_metric = min(metric for metric, _ in eligible_sets)
        selected_metric = (
            len(selected),
            sum(
                candidate.get("surfaceAreaScore", 0)
                for candidate in selected
                if isinstance(candidate.get("surfaceAreaScore"), int)
            ),
        )
        if selected_metric != best_metric:
            failures.append("fail-selected-set-not-minimal")
    return failures, selected_ids


def evaluate_selection(packet: dict[str, Any]) -> dict[str, Any]:
    """Return a deterministic selection-only decision verdict."""

    if not isinstance(packet, dict):
        raise ValueError("packet must be an object")
    expected_top_keys = {
        "schema",
        "synthetic",
        "liveExecutionObserved",
        "targetHost",
        "task",
        "upstreamRoutingDecision",
        "nativeCurrentAssessment",
        "candidates",
        "selectedMinimalSet",
        "decisionBoundary",
        "releasePlan",
        "hostApprovalCreditedToContract",
        "claimBoundary",
        "packetSha256",
    }
    failures: list[str] = []
    if set(packet) != expected_top_keys or packet.get("schema") != 1:
        failures.append("fail-packet-shape")
    if packet.get("synthetic") is not True:
        failures.append("fail-offline-contract-requires-synthetic-packet")
    if packet.get("liveExecutionObserved") is not False:
        failures.append("hard-fail-live-execution-claim")

    target = packet.get("targetHost", {})
    if (
        not isinstance(target, dict)
        or set(target) != {"identity", "version", "adapterVersion"}
        or any(not _bound_string(target.get(key)) for key in target)
    ):
        failures.append("fail-target-host-binding")

    task = packet.get("task", {})
    if (
        not isinstance(task, dict)
        or set(task)
        != {
            "bound",
            "taskId",
            "phaseId",
            "concreteUseCase",
            "acceptanceSurface",
            "requiredCapabilityIds",
        }
        or task.get("bound") is not True
        or any(
            not _bound_string(task.get(key))
            for key in ("taskId", "phaseId", "concreteUseCase")
        )
    ):
        failures.append("fail-task-unbound")
    acceptance = task.get("acceptanceSurface", []) if isinstance(task, dict) else []
    if (
        not isinstance(acceptance, list)
        or not acceptance
        or any(not _bound_string(item) for item in acceptance)
    ):
        failures.append("fail-acceptance-surface-unbound")
    required_gap_ids = (
        _string_set(task.get("requiredCapabilityIds")) if isinstance(task, dict) else None
    )
    if required_gap_ids is None:
        failures.append("fail-required-capability-binding")
        required_gap_ids = set()

    routing = packet.get("upstreamRoutingDecision", {})
    if (
        not isinstance(routing, dict)
        or set(routing)
        != {
            "scope",
            "decisionRef",
            "decisionSha256",
            "evidenceClass",
            "candidateClassDecision",
        }
        or routing.get("scope") != "mcp-subset-refinement-only"
        or routing.get("candidateClassDecision") != "mcp-evaluation-authorized"
    ):
        failures.append("fail-upstream-routing-decision")
    else:
        failures.extend(
            _evidence_pointer_errors(
                routing.get("evidenceClass"),
                routing.get("decisionRef"),
                routing.get("decisionSha256"),
                "fail-upstream-routing-decision",
            )
        )

    native = packet.get("nativeCurrentAssessment", {})
    if (
        not isinstance(native, dict)
        or set(native)
        != {
            "assessed",
            "sufficient",
            "residualGapIds",
            "evidenceClass",
            "evidenceRef",
            "evidenceSha256",
        }
        or native.get("assessed") is not True
        or not isinstance(native.get("sufficient"), bool)
    ):
        failures.append("fail-native-current-assessment")
        native_sufficient = False
        native_gap_ids: set[str] = set()
    else:
        native_sufficient = native["sufficient"]
        native_gap_list = native.get("residualGapIds")
        if not isinstance(native_gap_list, list) or len(native_gap_list) != len(
            set(native_gap_list)
        ) or any(not _bound_string(item) for item in native_gap_list):
            failures.append("fail-native-gap-binding")
            native_gap_ids = set()
        else:
            native_gap_ids = set(native_gap_list)
        failures.extend(
            _evidence_pointer_errors(
                native.get("evidenceClass"),
                native.get("evidenceRef"),
                native.get("evidenceSha256"),
                "fail-native-current-assessment",
            )
        )
        if native_sufficient and native_gap_ids:
            failures.append("fail-native-gap-contradiction")
        if not native_sufficient and native_gap_ids != required_gap_ids:
            failures.append("fail-native-gap-contradiction")

    raw_candidates = packet.get("candidates")
    candidates: list[dict[str, Any]] = []
    candidate_ids: list[str] = []
    if not isinstance(raw_candidates, list):
        failures.append("fail-candidate-set-shape")
    elif len(raw_candidates) > 32:
        failures.append("fail-candidate-set-limit")
    else:
        for candidate in raw_candidates:
            failures.extend(_candidate_errors(candidate))
            if isinstance(candidate, dict):
                candidates.append(candidate)
                identity = candidate.get("identity")
                if _bound_string(identity):
                    if identity in candidate_ids:
                        failures.append("fail-duplicate-candidate-identity")
                    candidate_ids.append(identity)

    if native_sufficient:
        selected_ids = [
            candidate.get("identity")
            for candidate in candidates
            if candidate.get("selected") is True
        ]
        if selected_ids:
            failures.append("fail-mcp-selected-despite-native-sufficiency")
        if packet.get("selectedMinimalSet") != []:
            failures.append("fail-selected-set-mismatch")
    else:
        minimal_failures, selected_ids = _minimal_selection_errors(
            candidates,
            required_gap_ids,
            packet.get("selectedMinimalSet"),
        )
        failures.extend(minimal_failures)

    decision = packet.get("decisionBoundary", {})
    if (
        not isinstance(decision, dict)
        or set(decision)
        != {
            "selectionOnly",
            "selectionDoesNotAuthorizeActivation",
            "activationState",
            "activationAuthorityGranted",
            "activationScope",
            "persistentActivationRequested",
            "unselectedCandidatesRemainInactive",
        }
        or decision.get("selectionOnly") is not True
        or decision.get("selectionDoesNotAuthorizeActivation") is not True
        or decision.get("activationState")
        not in {"not-requested", "request-prepared"}
        or decision.get("activationAuthorityGranted") is not False
    ):
        failures.append("hard-fail-selection-actuation-conflation")
    if (
        decision.get("activationScope") != "task-or-phase-only"
        or decision.get("persistentActivationRequested") is not False
    ):
        failures.append("hard-fail-persistent-activation-default")
    if decision.get("unselectedCandidatesRemainInactive") is not True:
        failures.append(
            "hard-fail-unselected-candidates-must-remain-inactive"
        )

    release = packet.get("releasePlan", {})
    release_keys = {
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
        "releaseRequestDoesNotProveActuation",
        "releaseObserved",
    }
    if (
        not isinstance(release, dict)
        or set(release) != release_keys
        or release.get("hostLifecycleCapability") not in HOST_LIFECYCLE_STATES
        or release.get("fallback") not in FALLBACKS
        or release.get("fallbackEvidenceState")
        not in {"planned-unproved", "recorded-static", "observed-single-host"}
        or release.get("releaseRequestDoesNotProveActuation") is not True
        or release.get("releaseObserved") is not False
    ):
        failures.append("fail-release-plan")
    else:
        failures.extend(
            _evidence_pointer_errors(
                release.get("lifecycleEvidenceClass"),
                release.get("lifecycleEvidenceRef"),
                release.get("lifecycleEvidenceSha256"),
                "fail-release-lifecycle-evidence",
            )
        )
        failures.extend(
            _evidence_pointer_errors(
                release.get("fallbackEvidenceClass"),
                release.get("fallbackEvidenceRef"),
                release.get("fallbackEvidenceSha256"),
                "fail-release-fallback-evidence",
            )
        )
        if (
            release.get("observedHostIdentity") != target.get("identity")
            or release.get("observedHostVersion") != target.get("version")
            or release.get("observedHostAdapterVersion")
            != target.get("adapterVersion")
        ):
            failures.append("fail-release-host-binding")
        state = release["hostLifecycleCapability"]
        fallback = release["fallback"]
        fallback_state = release["fallbackEvidenceState"]
        lifecycle_class = release["lifecycleEvidenceClass"]
        fallback_class = release["fallbackEvidenceClass"]
        lifecycle_class_valid = (
            state == "unknown"
            and lifecycle_class in {"synthetic-fixture", "recorded-static"}
        ) or (
            state
            in {
                "startup-or-new-thread-profile-only",
                "documented-native-idle-timeout",
            }
            and lifecycle_class in {"recorded-static", "observed-single-host"}
        ) or (
            state == "same-session-actuation-observed-for-exact-host"
            and lifecycle_class == "observed-single-host"
        )
        if not lifecycle_class_valid:
            failures.append("fail-release-lifecycle-evidence-class")
        fallback_class_valid = (
            fallback_state == "planned-unproved"
            and fallback_class in {"synthetic-fixture", "recorded-static"}
        ) or (
            fallback_state == "recorded-static"
            and fallback_class == "recorded-static"
        ) or (
            fallback_state == "observed-single-host"
            and fallback_class == "observed-single-host"
        )
        if not fallback_class_valid:
            failures.append("fail-release-fallback-evidence-class")
        allowed = (
            state == "unknown"
            and fallback == "startup-or-new-thread-profile"
            and fallback_state == "planned-unproved"
        ) or (
            state == "startup-or-new-thread-profile-only"
            and fallback == "startup-or-new-thread-profile"
            and fallback_state in {"recorded-static", "observed-single-host"}
        ) or (
            state == "documented-native-idle-timeout"
            and fallback == "documented-native-idle-timeout"
            and fallback_state in {"recorded-static", "observed-single-host"}
        ) or (
            state == "same-session-actuation-observed-for-exact-host"
            and fallback == "startup-or-new-thread-profile"
            and fallback_state in {"recorded-static", "observed-single-host"}
        )
        if selected_ids and not allowed:
            failures.append("fail-release-state-fallback-mismatch")
        if selected_ids and release.get("requestAtTaskOrPhaseEnd") is not True:
            failures.append("fail-release-request-missing")
        if not selected_ids and (
            release.get("requestAtTaskOrPhaseEnd") is not False
            or fallback != "none-selected"
            or state != "unknown"
            or fallback_state != "planned-unproved"
        ):
            failures.append("fail-no-selection-release-contradiction")

    if packet.get("hostApprovalCreditedToContract") is not False:
        failures.append("hard-fail-host-approval-credit")
    claim = packet.get("claimBoundary", {})
    expected_false_claims = {
        "activationProved",
        "sameSessionSwitchingProved",
        "taskEndReleaseProved",
        "leaseOrReferenceCountProved",
        "resourceBenefitProved",
        "weakAgentAcceptanceProved",
        "crossHostSupportProved",
        "candidateUniverseCompleteProved",
        "candidateReviewTruthProved",
        "minimalityBeyondDeclaredCandidatesProved",
        "persistentActivationSafeOrBeneficialProved",
    }
    if (
        not isinstance(claim, dict)
        or set(claim) != expected_false_claims
        or any(value is not False for value in claim.values())
    ):
        failures.append("hard-fail-selection-claim-overreach")

    reported_digest = packet.get("packetSha256")
    digest_payload = copy.deepcopy(packet)
    digest_payload.pop("packetSha256", None)
    if reported_digest != canonical_sha256(digest_payload):
        failures.append("fail-packet-digest")

    failures = list(dict.fromkeys(failures))
    if failures:
        status = "fail"
    elif selected_ids:
        status = "offline-selection-contract-valid-no-host-actuation-proof"
    else:
        status = "offline-no-mcp-needed-contract-valid"
    return {
        "status": status,
        "failureCodes": failures,
        "selectedIdentities": selected_ids,
        "countsAsLiveHostProof": False,
        "countsAsWeakAgentAcceptance": False,
        "countsAsActivationOrReleaseProof": False,
    }


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


def evaluate_fixture_document(document: dict[str, Any]) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for fixture in document["fixtures"]:
        packet = merge_patch(document["basePacket"], fixture.get("patch", {}))
        if fixture.get("recomputePacketSha256"):
            digest_payload = copy.deepcopy(packet)
            digest_payload.pop("packetSha256", None)
            packet["packetSha256"] = canonical_sha256(digest_payload)
        actual = evaluate_selection(packet)
        results.append(
            {
                "id": fixture["id"],
                "expectedStatus": fixture["expectedStatus"],
                "actualStatus": actual["status"],
                "expectedFailureCodes": fixture.get("expectedFailureCodes", []),
                "actualFailureCodes": actual["failureCodes"],
                "countsAsLiveHostProof": actual["countsAsLiveHostProof"],
                "countsAsWeakAgentAcceptance": actual[
                    "countsAsWeakAgentAcceptance"
                ],
                "countsAsActivationOrReleaseProof": actual[
                    "countsAsActivationOrReleaseProof"
                ],
            }
        )
    return results
