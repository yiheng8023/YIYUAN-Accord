from datetime import datetime
from hashlib import sha256
import json
import re
import subprocess
from urllib.parse import unquote, urlsplit

from .closure import reconcile_closure
from .identity import (
    _bounded_git_bytes, _exact, _nonempty_string as _text,
    _safe_https_locator, _strict_json_object,
)


STATES = {"passed", "failed", "failed-repeated-same-purpose"}
_OFFICIAL_HOSTS = {
    "openai.com", "help.openai.com", "platform.openai.com",
    "developers.openai.com", "github.com", "code.claude.com",
    "learn.chatgpt.com",
}
_PROJECTION_FIELDS = (
    "adapterId", "contract", "contractSha256", "skill", "skillSha256",
    "mechanismFiles", "mechanismSha256",
)
_UNRESERVED = frozenset("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-._~")


def _records(value):
    return isinstance(value, list) and all(isinstance(x, dict) and
        _text(x.get("kind")) for x in value)


def _string_set(value):
    return set(value) if isinstance(value, list) and all(_text(x) for x in value) else None


def _enum_map(value, expected, choices):
    return (expected is not None and isinstance(value, dict) and set(value) == expected
            and all(_text(item) and item in choices for item in value.values()))


def _time(value):
    normalized = value.replace("Z", "+00:00") if isinstance(value, str) else value
    if isinstance(normalized, str):
        normalized = re.sub(
            r"(\.\d{6})\d+(?=[+-]\d{2}:\d{2}$)", r"\1", normalized
        )
    try:
        parsed = datetime.fromisoformat(normalized)
    except (TypeError, ValueError):
        return None
    return parsed if parsed.tzinfo is not None else None


def _canonical_json(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"))


def _digest(value):
    return sha256(_canonical_json(value).encode()).hexdigest()


def _canonical_official_url(value):
    if (not _safe_https_locator(value) or "\\" in value
            or any(ord(char) < 32 or ord(char) == 127 for char in value)):
        return None
    try:
        parsed = urlsplit(value)
        host, path = parsed.hostname.lower(), parsed.path
        escapes = re.findall(r"%([0-9a-fA-F]{2})", path)
        if (parsed.port is not None or host not in _OFFICIAL_HOSTS
                or not path.startswith("/") or "%" in re.sub(r"%[0-9a-fA-F]{2}", "", path)
                or any(chr(int(code, 16)) not in _UNRESERVED for code in escapes)):
            return None
        path = unquote(path)
    except (AttributeError, TypeError, ValueError):
        return None
    if (any(part in {".", ".."} or any(ord(char) < 32 or ord(char) == 127 for char in part)
            for part in path.split("/")) or host == "github.com" and not path.startswith("/openai/")):
        return None
    return f"https://{host}{path}"


def _official_source(source, captured_at):
    retrieved_at = _time(source.get("retrievedAt")) if isinstance(source, dict) else None
    url = source.get("url") if isinstance(source, dict) else None
    return (
        _exact(source, ("kind", "url", "retrievedAt", "claim"),
               ("url", "retrievedAt", "claim"))
        and source.get("kind") == "official-source"
        and _canonical_official_url(url) is not None
        and retrieved_at is not None and captured_at is not None
        and retrieved_at <= captured_at
    )


def _postcapture_binding(binding, payload, captured_at, task_id=None):
    if not isinstance(binding, dict):
        return False
    if binding.get("kind") == "observer-session-event":
        observed_at = _time(binding.get("observedAt"))
        return (
            _exact(binding, ("kind", "sessionId", "eventLocator", "observedAt", "claim"),
                   ("sessionId", "eventLocator", "observedAt", "claim"))
            and observed_at is not None and captured_at is not None
            and observed_at <= captured_at
            and re.fullmatch(
                r"[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}",
                binding["sessionId"],
            ) is not None
            and re.fullmatch(
                r"response_item/call_[A-Za-z0-9]+", binding["eventLocator"]
            ) is not None
        )
    if binding.get("kind") == "direct-independent-command-result":
        results = (
            payload.get("independentCommandResults")
            if isinstance(payload, dict) else None
        )
        task_locator = binding.get("taskLocator")
        nonces = binding.get("phaseNonces")
        completed_at = _time(binding.get("completedAt"))
        valid_results = (
            _records(results) and results
            and all(
                set(result) in ({
                    "kind", "carrierSessionId", "taskLocator", "phase", "nonce",
                    "report",
                }, {
                    "kind", "carrierSessionId", "taskLocator", "phase", "nonce",
                    "report", "facts",
                })
                and result["kind"] == "independent-command-result"
                and all(_text(result[field]) for field in (
                    "carrierSessionId", "taskLocator", "phase", "nonce", "report"
                ))
                and (
                    "facts" not in result
                    or isinstance(result["facts"], dict) and result["facts"]
                    and result["report"] == _canonical_json(result["facts"])
                )
                for result in results
            )
        )
        bound_results = [
            result for result in results
            if isinstance(result, dict)
            and result.get("carrierSessionId") == binding.get("carrierSessionId")
            and result.get("taskLocator") == task_locator
        ] if isinstance(results, list) else []
        return bool(
            _exact(
                binding,
                ("kind", "carrierSessionId", "taskLocator", "resultLocator",
                 "phaseNonces", "resultSha256", "resultRecordSha256",
                 "completedAt", "claim"),
                ("carrierSessionId", "taskLocator", "resultLocator",
                 "resultSha256", "resultRecordSha256", "completedAt", "claim"),
            )
            and re.fullmatch(
                r"[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}",
                binding["carrierSessionId"],
            ) is not None
            and _text(task_locator)
            and _text(task_id)
            and task_locator.split("/")[0] == task_id
            and len(task_locator.split("/")) > 1
            and all(
                segment not in {"", ".", ".."}
                for segment in task_locator.split("/")
            )
            and re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._/-]{0,127}", task_locator)
            is not None
            and binding["resultLocator"] == (
                f"task-artifact:{task_locator}/agent-final.txt"
            )
            and completed_at is not None and captured_at is not None
            and completed_at <= captured_at
            and isinstance(nonces, list) and nonces
            and all(_text(value) for value in nonces)
            and len(nonces) == len(set(nonces))
            and valid_results and bound_results
            and [result["nonce"] for result in bound_results] == nonces
            and binding.get("resultSha256") == sha256(
                bound_results[0]["report"].encode("utf-8")
            ).hexdigest()
            and binding.get("resultRecordSha256") == _digest(bound_results)
        )
    return False


def _postcapture_binding_key(binding):
    if binding.get("kind") == "observer-session-event":
        return binding["kind"], binding.get("sessionId"), binding.get("eventLocator")
    return (binding.get("kind"), binding.get("carrierSessionId"),
            binding.get("taskLocator"), binding.get("resultLocator"),
            binding.get("resultSha256"), binding.get("resultRecordSha256"))


def _postcapture_bundle(payload, task, captured_at):
    if not isinstance(payload, dict):
        return None
    cleanup = payload.get("cleanupEvidence")
    observations = cleanup.get("observations") if isinstance(cleanup, dict) else None
    material = payload.get("materialEvents")
    pools = {
        "materialEvents": material if isinstance(material, list) else [],
        "cleanupEvidence.observations": observations if isinstance(observations, list) else [],
    }
    kinds = {"independent-poststate", "post-capture-fixture-removal"}
    special = [event for events in pools.values() if isinstance(events, list)
               for event in events if isinstance(event, dict)
               and _text(event.get("kind")) and event["kind"] in kinds]
    contract = task.get("postSessionBindingContract")
    if contract is None:
        return ({"contract": [], "events": []}
                if "postSessionBindingContract" not in payload and not special else None)
    if (payload.get("postSessionBindingContract") != contract
            or not _records(contract) or not contract):
        return None
    selected = []
    for spec in contract:
        location = spec.get("location")
        count = spec.get("bindingCount")
        if (not _exact(spec, ("kind", "location", "bindingCount"), ("kind", "location"))
                or spec["kind"] not in kinds or location not in pools
                or not isinstance(count, int) or isinstance(count, bool) or count < 1):
            return None
        matches = [event for event in pools[location]
                   if isinstance(event, dict) and event.get("kind") == spec["kind"]]
        if len(matches) != 1:
            return None
        event = matches[0]
        bindings = event.get("sourceBindings")
        if (
            not _records(bindings) or len(bindings) != count
            or not all(_postcapture_binding(
                binding, payload, captured_at, task.get("id")
            )
                       for binding in bindings)
            or len({_postcapture_binding_key(binding) for binding in bindings}) != count
        ):
            return None
        selected.append({"location": location, "event": event})
    locators = [_postcapture_binding_key(binding)
                for item in selected for binding in item["event"]["sourceBindings"]]
    command_results = payload.get("independentCommandResults")
    command_bindings = [
        binding for item in selected for binding in item["event"]["sourceBindings"]
        if binding.get("kind") == "direct-independent-command-result"
    ]
    if command_results is not None or command_bindings:
        actual = [
            (result.get("carrierSessionId"), result.get("taskLocator"), result.get("nonce"))
            for result in command_results
        ] if isinstance(command_results, list) else []
        expected = [
            (binding.get("carrierSessionId"), binding.get("taskLocator"), nonce)
            for binding in command_bindings for nonce in binding.get("phaseNonces", [])
        ]
        if not actual or len(actual) != len(set(actual)) or actual != expected:
            return None
    return ({"contract": contract, "events": selected} if len(special) == len(selected)
            and len(locators) == len(set(locators)) else None)


def _passing_episode(episode, dimension_ids):
    vector = episode.get("acceptanceVector") if isinstance(episode, dict) else None
    return (
        isinstance(vector, list)
        and [item.get("id") for item in vector if isinstance(item, dict)]
        == dimension_ids
        and len(vector) == len(dimension_ids)
        and all(item.get("state") == "pass" for item in vector)
    )


def _decision_matches(decision, route_id, disposition):
    lifecycle = decision.get("lifecycle") if isinstance(decision, dict) else None
    return (
        isinstance(decision, dict)
        and decision.get("valid") is True
        and decision.get("errors") == []
        and decision.get("selectedRouteId") == route_id
        and decision.get("frontierRouteIds") == [route_id]
        and decision.get("disposition") == disposition
        and isinstance(lifecycle, dict)
        and lifecycle.get("completionAllowed") is True
        and lifecycle.get("completionFailures") == []
        and lifecycle.get("residualTaskResources") == []
    )


def _continuity_handoff_bundle(payload, task):
    """Validate observable carrier inheritance and release ordering."""
    if task.get("kind") != "continuity":
        return {}
    required_contract = {
        "record-capacity-as-unknown",
        "distinguish-same-carrier-compaction-causal-fork-and-sequential-handoff",
        "use-a-fresh-zero-inherited-history-destination-for-sequential-load-relief",
        "transfer-only-minimum-verified-goal-code-binding-authority-state-and-evidence",
        "prepare-and-verify-destination",
        "reconcile-before-source-release",
    }
    task_required = _string_set(task.get("required"))
    if task_required is None or not required_contract <= task_required:
        return {}
    events = payload.get("materialEvents") if isinstance(payload, dict) else None
    if not _records(events):
        return None
    by_kind = {
        kind: [event for event in events if event.get("kind") == kind]
        for kind in (
            "capacity-observation", "conversation-topology-classification",
            "independent-poststate",
        )
    }
    if any(len(items) != 1 for items in by_kind.values()):
        return None
    capacity = by_kind["capacity-observation"][0]
    topology = by_kind["conversation-topology-classification"][0]
    poststate = by_kind["independent-poststate"][0]
    classifications = topology.get("classifications")
    classified = {
        item.get("id"): item for item in classifications or []
        if isinstance(item, dict) and _text(item.get("id"))
    }
    expected = {
        "compact": ("same-carrier-memory-reduction", "same-carrier", False),
        "causal-fork": ("copied-history-causal-branch", "copied", False),
        "sequential-handoff": (
            "fresh-zero-inherited-history-destination", "none", True,
        ),
    }
    code = topology.get("codeTopology")
    execution = topology.get("executionPlacement")
    bindings = poststate.get("sourceBindings")
    binding_by_phase = {
        binding["taskLocator"].rsplit("/", 1)[-1]: binding
        for binding in bindings or []
        if isinstance(binding, dict) and _text(binding.get("taskLocator"))
    }
    destination = binding_by_phase.get("destination-poststate")
    reconciliation = binding_by_phase.get("source-reconciliation")
    destination_at = _time(destination.get("completedAt")) \
        if isinstance(destination, dict) else None
    reconciliation_at = _time(reconciliation.get("completedAt")) \
        if isinstance(reconciliation, dict) else None
    command_results = payload.get("independentCommandResults")
    result_by_phase = {
        result["taskLocator"].rsplit("/", 1)[-1]: result
        for result in command_results or []
        if isinstance(result, dict) and _text(result.get("taskLocator"))
    }
    destination_result = result_by_phase.get("destination-poststate")
    reconciliation_result = result_by_phase.get("source-reconciliation")
    required_fields = {
        "goal", "authority", "code-binding", "current-state", "evidence",
        "claim-limit",
    }
    destination_expected = {
        "capacity": {
            key: capacity.get(key) for key in (
                "capacity", "reliableSignal", "universalThreshold"
            )
        },
        "receivedFields": topology.get("receivedFields"),
        "classifications": classifications,
        "codeTopology": code,
        "executionPlacement": execution,
        "sourceReleasedObserved": topology.get("sourceReleasedObserved"),
    }
    reconciliation_expected = {
        "destinationResultSha256": topology.get("destinationResultSha256"),
        "destinationVerifiedBeforeSourceRelease": True,
        "codeTopology": code,
        "executionPlacement": execution,
        "sourceReleasedObserved": topology.get("sourceReleasedObserved"),
    }

    def structured(result, kind, expected):
        facts = result.get("facts") if isinstance(result, dict) else None
        return (
            isinstance(facts, dict)
            and set(facts) == set(expected) | {"kind", "sourceNarrativeSha256"}
            and facts.get("kind") == kind
            and re.fullmatch(
                r"[0-9a-f]{64}", facts.get("sourceNarrativeSha256", "")
            ) is not None
            and all(facts.get(key) == value for key, value in expected.items())
            and result.get("report") == _canonical_json(facts)
        )

    return topology if (
        _exact(
            capacity,
            ("kind", "capacity", "reliableSignal", "universalThreshold"),
        )
        and capacity.get("capacity") == "unknown"
        and capacity.get("reliableSignal") is False
        and capacity.get("universalThreshold") is None
        and isinstance(classifications, list)
        and len(classifications) == len(classified)
        and set(expected) <= set(classified)
        and all(
            item.get("semantic") == semantic
            and item.get("historyInheritance") == inheritance
            and item.get("sequentialContextRelief") is sequential
            for key, (semantic, inheritance, sequential) in expected.items()
            for item in (classified[key],)
        )
        and _string_set(topology.get("receivedFields")) == required_fields
        and len(topology["receivedFields"]) == len(required_fields)
        and isinstance(topology.get("reportedTokensUsed"), int)
        and not isinstance(topology.get("reportedTokensUsed"), bool)
        and topology["reportedTokensUsed"] >= 0
        and isinstance(code, dict)
        and all(_text(code.get(field)) for field in ("repository", "branch", "head"))
        and code.get("head") == payload.get("evaluatedRevision")
        and code.get("changed") is False
        and isinstance(execution, dict) and _text(execution.get("kind"))
        and execution.get("changed") is False
        and topology.get("sourceReleasedObserved") is False
        and isinstance(bindings, list) and len(bindings) == 2
        and len(binding_by_phase) == 2
        and destination_at is not None and reconciliation_at is not None
        and destination_at < reconciliation_at
        and len(result_by_phase) == 3
        and structured(
            destination_result, "continuity-destination-poststate/v1",
            destination_expected,
        )
        and structured(
            reconciliation_result, "continuity-source-reconciliation/v1",
            reconciliation_expected,
        )
        and _text(poststate.get("result"))
    ) else None


def _sequence_digest(event):
    if not isinstance(event, dict) or "sequenceSha256" not in event:
        return None
    return _digest({
        key: value for key, value in event.items() if key != "sequenceSha256"
    })


def _valid_episode_decision(episode):
    decision = episode.get("coreDecision") if isinstance(episode, dict) else None
    route_id = decision.get("selectedRouteId") if isinstance(decision, dict) else None
    disposition = decision.get("disposition") if isinstance(decision, dict) else None
    return _text(route_id) and _text(disposition) and _decision_matches(
        decision, route_id, disposition
    )


def _evolution_disposition(disposition, order):
    if not _text(disposition):
        return False
    return (
        disposition.startswith("observe-") if order == 0 else
        "reject" in disposition and "rollback" in disposition if order == 1 else
        disposition.startswith("retain-bounded-") if order == 2 else
        "replace" in disposition and "retire" in disposition
    )


def _lifecycle_disposition(disposition, order):
    if not _text(disposition):
        return False
    return (
        disposition.startswith("retain-") and "retire" not in disposition
        if order in {0, 1} else
        disposition.startswith("retire-exact-") and "whole-product" not in disposition
        if order == 2 else
        "restore" in disposition and (
            "drift" in disposition or "expiry" in disposition
        )
    )


def _gt18_longitudinal_semantics(task, event, episodes, dimension_ids):
    if len(episodes) != 4 or any(not isinstance(episode, dict) for episode in episodes):
        return False
    base_fields = {
        "order", "role", "evaluatorSha256", "coreDecision",
        "coreDecisionSha256", "sourceFacts", "acceptanceVector", "disposition",
    }
    candidate = episodes[1].get("candidateAcceptanceVector")
    failed_candidate_dimensions = {
        item.get("id") for item in candidate or []
        if isinstance(item, dict) and item.get("state") == "fail"
    }
    regression_rule = next((
        marker for marker in task.get("required", [])
        if isinstance(marker, str)
        and marker.startswith("reject-proxy-improvement-that-weakens-")
    ), "")
    regression_terms = set(regression_rule.split("-"))
    declared_regression_dimensions = {
        dimension for dimension in dimension_ids
        if regression_terms & set(dimension.split("-"))
    }
    carrier = event.get("stateCarrier")
    selected = [episode.get("coreDecision", {}).get("selectedRouteId")
                for episode in episodes]
    return (
        _exact(event, (
            "kind", "revision", "fixedBudget", "fullAcceptanceVector",
            "evaluatorCanonicalSha256", "episodes", "carrierEdges",
            "stateCarrier", "stateCarrierSha256", "unknowns", "sequenceSha256",
        ), ("revision", "evaluatorCanonicalSha256", "stateCarrierSha256",
             "sequenceSha256"))
        and re.fullmatch(r"[0-9a-f]{40}", event.get("revision", "")) is not None
        and event.get("sequenceSha256") == _sequence_digest(event)
        and event.get("fixedBudget") == 4
        and all(
            set(episode) == base_fields | (
                {"candidateAcceptanceVector"} if order == 1 else
                {"invalidatedRoute", "selectedRoute"} if order == 3 else set()
            )
            and _evolution_disposition(episode.get("disposition"), order)
            and _valid_episode_decision(episode)
            and _passing_episode(episode, dimension_ids)
            for order, episode in enumerate(episodes)
        )
        and isinstance(candidate, list)
        and [item.get("id") for item in candidate if isinstance(item, dict)]
        == dimension_ids
        and len(candidate) == len(dimension_ids)
        and all(
            _exact(item, ("id", "state"), ("id", "state"))
            and item["state"] in {"pass", "fail"}
            for item in candidate
        )
        and failed_candidate_dimensions & declared_regression_dimensions
        and selected[1] == selected[0]
        and selected[2] != selected[0]
        and episodes[3].get("invalidatedRoute") == selected[2]
        and episodes[3].get("selectedRoute") == selected[3]
        and selected[3] != selected[2]
        and isinstance(carrier, dict)
        and _text(carrier.get("schema"))
        and carrier.get("owner") == task.get("id")
        and _text(carrier.get("authorizedWriter"))
        and _text(carrier.get("authorizedReader"))
        and carrier.get("hiddenMemory") is False
        and _text(carrier.get("freshness")) and _text(carrier.get("ttl"))
        and carrier.get("finalActiveRoute") == selected[3]
        and _string_set(carrier.get("retiredRoutes")) is not None
        and selected[2] in carrier["retiredRoutes"]
        and event.get("stateCarrierSha256") == _digest(carrier)
        and _string_set(event.get("unknowns")) is not None
    )


def _gt19_request_semantics(
    request, order, baseline_route, replacement_route, outcome_id,
    responsibilities,
):
    if not isinstance(request, dict):
        return False
    outcome, policy, routes, events = (
        request.get("outcome"), request.get("policy"),
        request.get("routes"), request.get("events"),
    )
    if (
        not isinstance(routes, list) or not routes
        or any(not isinstance(route, dict) or not _text(route.get("id"))
               for route in routes)
        or len({route["id"] for route in routes}) != len(routes)
        or not isinstance(events, list)
    ):
        return False
    route_by_id = {route["id"]: route for route in routes}
    retirement_events = [
        event for event in events or [] if isinstance(event, dict)
        and event.get("kind") == "responsibility-allocation-retired"
    ]
    expected_retirements = ([{
        "routeId": baseline_route, "responsibilities": responsibilities,
    }] if order == 2 else [])
    exact_retirement_event = (
        len(retirement_events) == 1
        and retirement_events[0].get("routeId") == baseline_route
        and retirement_events[0].get("replacementRouteId") == replacement_route
        and retirement_events[0].get("responsibilities") == responsibilities
        and retirement_events[0].get("state") == "observed"
        and retirement_events[0].get("independent") == "observed"
        and isinstance(retirement_events[0].get("preconditions"), dict)
        and retirement_events[0]["preconditions"]
        and all(value == "observed" for value in retirement_events[0][
            "preconditions"].values())
        and _string_set(retirement_events[0].get("recheckTriggers")) is not None
        and retirement_events[0]["recheckTriggers"]
    ) if order == 2 else not retirement_events
    baseline = route_by_id.get(baseline_route)
    replacement = route_by_id.get(replacement_route)
    baseline_supplies = _string_set(baseline.get("supplies")) \
        if isinstance(baseline, dict) else None
    replacement_supplies = _string_set(replacement.get("supplies")) \
        if isinstance(replacement, dict) else None
    target = set(responsibilities)
    return (
        isinstance(outcome, dict)
        and outcome.get("id") == outcome_id
        and outcome.get("responsibilities") == responsibilities
        and isinstance(policy, dict)
        and policy.get("requiredRetirementAllocations", []) == expected_retirements
        and baseline_supplies is not None and target < baseline_supplies
        and replacement_supplies is not None
        and (target.isdisjoint(replacement_supplies) if order == 0
             else target <= replacement_supplies)
        and exact_retirement_event
    )


def _gt19_longitudinal_semantics(task, event, episodes, dimension_ids):
    if len(episodes) != 4 or any(not isinstance(episode, dict) for episode in episodes):
        return False
    episode_fields = {
        "order", "role", "evaluatorSha256", "coreDecision",
        "coreDecisionSha256", "sourceFacts", "acceptanceVector",
        "closureRequest", "closureRequestSha256", "sparseViews", "masks",
        "disposition",
    }
    carrier = event.get("stateCarrier")
    behavior_arms = event.get("behaviorArms")
    decisions = [episode.get("coreDecision") for episode in episodes]
    selected = [decision.get("selectedRouteId") if isinstance(decision, dict) else None
                for decision in decisions]
    baseline_route, replacement_route = selected[0], selected[2]
    first_request = episodes[0].get("closureRequest")
    first_outcome = first_request.get("outcome") if isinstance(first_request, dict) else None
    outcome_id = first_outcome.get("id") if isinstance(first_outcome, dict) else None
    responsibilities = first_outcome.get("responsibilities") \
        if isinstance(first_outcome, dict) else None
    if (
        not _text(outcome_id)
        or not isinstance(responsibilities, list) or len(responsibilities) != 1
        or not _text(responsibilities[0])
        or not _text(baseline_route) or not _text(replacement_route)
        or baseline_route == replacement_route
    ):
        return False
    first_routes = first_request.get("routes") if isinstance(first_request, dict) else None
    first_route_by_id = {
        route.get("id"): route for route in first_routes or []
        if isinstance(route, dict) and _text(route.get("id"))
    }
    baseline_supplies = _string_set(
        first_route_by_id.get(baseline_route, {}).get("supplies")
    )
    outside_scope = baseline_supplies - set(responsibilities or []) \
        if baseline_supplies is not None else None
    accord_arms = [arm for arm in behavior_arms.values()
                   if isinstance(behavior_arms, dict) and isinstance(arm, dict)
                   and arm.get("skillRead") is True] \
        if isinstance(behavior_arms, dict) else []
    native_arms = [arm for arm in behavior_arms.values()
                   if isinstance(behavior_arms, dict) and isinstance(arm, dict)
                   and arm.get("skillRead") is False] \
        if isinstance(behavior_arms, dict) else []
    transcription_errors = accord_arms[0].get("finalAnswerTranscriptionErrors") \
        if len(accord_arms) == 1 else None
    return (
        _exact(event, (
            "kind", "revision", "fixedBudget", "fullAcceptanceVector",
            "evaluatorCanonicalSha256", "episodes", "carrierEdges",
            "stateCarrier", "stateCarrierSha256", "behaviorArms", "unknowns",
            "sequenceSha256",
        ), ("revision", "evaluatorCanonicalSha256", "stateCarrierSha256",
             "sequenceSha256"))
        and re.fullmatch(r"[0-9a-f]{40}", event.get("revision", "")) is not None
        and event.get("sequenceSha256") == _sequence_digest(event)
        and event.get("fixedBudget") == 4
        and isinstance(behavior_arms, dict)
        and len(accord_arms) == len(native_arms) == 1
        and all(
            isinstance(arm, dict)
            and _text(arm.get("sessionId"))
            and isinstance(arm.get("mutations"), list)
            and isinstance(arm.get("reportedTokens"), int)
            and not isinstance(arm.get("reportedTokens"), bool)
            and arm["reportedTokens"] >= 0
            for arm in behavior_arms.values()
        )
        and isinstance(transcription_errors, list)
        and all(_text(item) for item in transcription_errors)
        and len(transcription_errors) == len(set(transcription_errors))
        and all(
            set(episode) == episode_fields
            and _lifecycle_disposition(episode.get("disposition"), order)
            and episode.get("closureRequestSha256") == _digest(
                episode.get("closureRequest")
            )
            and _gt19_request_semantics(
                episode.get("closureRequest"), order, baseline_route,
                replacement_route, outcome_id, responsibilities,
            )
            and episode.get("coreDecision") == reconcile_closure(
                episode.get("closureRequest")
            )
            and _valid_episode_decision(episode)
            and _passing_episode(episode, dimension_ids)
            for order, episode in enumerate(episodes)
        )
        and selected == [baseline_route, baseline_route,
                         replacement_route, baseline_route]
        and outside_scope
        and all(
            isinstance(episode.get("sparseViews"), dict)
            and isinstance(episode["sparseViews"].get("H"), dict)
            and isinstance(episode["sparseViews"].get("A"), dict)
            and _text(episode["sparseViews"]["H"].get(
                f"{replacement_route}/{responsibilities[0]}"
            ))
            and episode["sparseViews"]["A"].get(
                f"{baseline_route}/{responsibilities[0]}"
            ) == "allocated"
            and all(episode["sparseViews"]["A"].get(
                f"{baseline_route}/{responsibility}"
            ) == "preserved-outside-scope" for responsibility in outside_scope)
            and isinstance(episode.get("masks"), dict)
            and set(episode["masks"]) == {"admission", "closureLifecycle"}
            for episode in episodes
        )
        and episodes[2]["masks"] == {
            "admission": "pass", "closureLifecycle": "pass",
        }
        and all(episode["masks"].get("admission") != "pass"
                and episode["masks"].get("closureLifecycle") != "pass"
                for episode in (episodes[0], episodes[1], episodes[3]))
        and episodes[0]["sparseViews"]["H"].get(
            f"{replacement_route}/{responsibilities[0]}"
        ) != episodes[2]["sparseViews"]["H"].get(
            f"{replacement_route}/{responsibilities[0]}"
        )
        and episodes[1]["sparseViews"]["H"].get(
            f"{replacement_route}/{responsibilities[0]}"
        ) != episodes[2]["sparseViews"]["H"].get(
            f"{replacement_route}/{responsibilities[0]}"
        )
        and episodes[3]["sparseViews"]["H"].get(
            f"{replacement_route}/{responsibilities[0]}"
        ) != episodes[2]["sparseViews"]["H"].get(
            f"{replacement_route}/{responsibilities[0]}"
        )
        and isinstance(carrier, dict)
        and _text(carrier.get("kind"))
        and _text(carrier.get("authorizedWriter"))
        and _text(carrier.get("authorizedReader"))
        and carrier.get("persistent") is False
        and _text(carrier.get("finalDisposition"))
        and event.get("stateCarrierSha256") == _digest(carrier)
        and _string_set(event.get("unknowns")) is not None
    )


def _longitudinal_semantics(task, event, episodes, dimension_ids):
    return {
        "longitudinal-self-evolution": _gt18_longitudinal_semantics,
        "dynamic-lifecycle": _gt19_longitudinal_semantics,
    }.get(task.get("kind"), lambda *_: False)(
        task, event, episodes, dimension_ids
    )


def _longitudinal_bundle(payload, task):
    design = task.get("evaluationDesign")
    if not isinstance(design, dict) or design.get("caseType") != "longitudinal-sequence":
        return {}
    events = payload.get("materialEvents") if isinstance(payload, dict) else None
    matches = [event for event in events or [] if isinstance(event, dict)
               and event.get("kind") == "longitudinal-sequence"]
    if len(matches) != 1:
        return None
    event = matches[0]
    vector, episodes, edges = (event.get("fullAcceptanceVector"),
                               event.get("episodes"), event.get("carrierEdges"))
    states = vector.get("states") if isinstance(vector, dict) else None
    dimensions = vector.get("dimensions") if isinstance(vector, dict) else None
    roles, minimum = design.get("episodeRoles"), design.get("minimumEpisodes")
    dimension_ids = [item.get("id") for item in dimensions or []
                     if isinstance(item, dict)]
    evaluator = event.get("evaluatorCanonicalSha256")
    carrier = event.get("stateCarrier")
    valid_vector = (
        isinstance(vector, dict) and set(vector) == {
            "states", "dimensions", "casePassRule", "candidateKeepRule",
            "aggregationForbidden",
        }
        and all(_text(vector[field]) for field in (
            "casePassRule", "candidateKeepRule", "aggregationForbidden",
        ))
        and _string_set(states) is not None and states and len(states) == len(set(states))
        and isinstance(dimensions, list) and dimensions
        and len(dimension_ids) == len(dimensions) == len(set(dimension_ids))
        and all(
            _exact(item, ("id", "hardGate", "requires"), ("id",))
            and isinstance(item["hardGate"], bool)
            and _string_set(item["requires"]) is not None and item["requires"]
            for item in dimensions
        )
        and _digest(vector) == design.get("fullAcceptanceVectorSha256")
    )
    valid_episodes = valid_vector and (
        isinstance(minimum, int) and not isinstance(minimum, bool) and minimum > 1
        and isinstance(roles, list) and len(roles) == minimum
        and all(_text(role) for role in roles) and len(roles) == len(set(roles))
        and isinstance(episodes, list) and len(episodes) == minimum
        and re.fullmatch(r"[0-9a-f]{64}", evaluator or "") is not None
        and all(
            isinstance(episode, dict)
            and episode.get("order") == order and episode.get("role") == roles[order]
            and episode.get("evaluatorSha256") == evaluator
            and isinstance(episode.get("coreDecision"), dict)
            and episode.get("coreDecisionSha256") == _digest(episode["coreDecision"])
            and _records(episode.get("sourceFacts")) and episode["sourceFacts"]
            and len({item.get("id") for item in episode["sourceFacts"]}) == len(
                episode["sourceFacts"])
            and all(
                _exact(item, ("kind", "id", "valueSha256", "summary"),
                       ("id", "valueSha256", "summary"))
                and item["kind"] == "sequence-source-fact"
                and item["valueSha256"] == episode["coreDecisionSha256"]
                for item in episode["sourceFacts"]
            )
            and isinstance(episode.get("acceptanceVector"), list)
            and [item.get("id") for item in episode["acceptanceVector"]] == dimension_ids
            and all(
                _exact(item, ("id", "state", "rationale", "sourceFacts"),
                       ("id", "state", "rationale"))
                and item["state"] in states
                and isinstance(item["sourceFacts"], list) and item["sourceFacts"]
                and all(_text(fact) for fact in item["sourceFacts"])
                and set(item["sourceFacts"]) <= {
                    fact["id"] for fact in episode["sourceFacts"]
                }
                for item in episode["acceptanceVector"]
            )
            for order, episode in enumerate(episodes)
        )
    )
    valid_edges = valid_episodes and (
        isinstance(carrier, dict)
        and _text(carrier.get("authorizedWriter"))
        and _text(carrier.get("authorizedReader"))
        and isinstance(edges, list) and len(edges) == minimum - 1
        and all(
            _exact(edge, ("kind", "fromOrder", "toOrder", "sourceState",
                          "targetState", "sourceStateSha256", "targetStateSha256",
                          "sourceStateSummary",
                          "targetStateSummary", "transition", "authorizedWriter",
                          "authorizedReader"),
                   ("sourceStateSha256", "targetStateSha256", "sourceStateSummary",
                    "targetStateSummary", "transition", "authorizedWriter",
                    "authorizedReader"))
            and edge["kind"] == "carrier-edge"
            and edge["fromOrder"] == order and edge["toOrder"] == order + 1
            and all(re.fullmatch(r"[0-9a-f]{64}", edge[field]) is not None
                    for field in ("sourceStateSha256", "targetStateSha256"))
            and isinstance(edge["sourceState"], dict)
            and isinstance(edge["targetState"], dict)
            and edge["sourceState"].get("episodeOrder") == order
            and edge["targetState"].get("episodeOrder") == order + 1
            and edge["sourceStateSha256"] == _digest(edge["sourceState"])
            and edge["targetStateSha256"] == _digest(edge["targetState"])
            and edge["authorizedWriter"] == carrier["authorizedWriter"]
            and edge["authorizedReader"] == carrier["authorizedReader"]
            for order, edge in enumerate(edges)
        )
        and all(edges[index]["targetStateSha256"] == edges[index + 1][
            "sourceStateSha256"] for index in range(len(edges) - 1))
    )
    valid_semantics = valid_edges and _longitudinal_semantics(
        task, event, episodes, dimension_ids
    )
    valid_revision = (
        _text(payload.get("evaluatedRevision"))
        and event.get("revision") == payload.get("evaluatedRevision")
    )
    return event if (
        valid_vector and valid_episodes and valid_edges and valid_semantics
        and valid_revision
    ) else None


def _publishable_payload(payload, task, cleanup, captured_at, projection):
    if not isinstance(payload, dict):
        return False
    messages, sources, evidence, exposure = (
        payload.get("messages"), payload.get("officialSources"),
        payload.get("cleanupEvidence"), payload.get("projectionExposure")
    )
    triggers = payload.get("recheckTriggers")
    required = task.get("required", [])
    projection_fields = (
        _PROJECTION_FIELDS
        if isinstance(projection, dict)
        and all(field in projection for field in (
            "mechanismFiles", "mechanismSha256",
        ))
        else ("adapterId", "skill", "skillSha256")
    )
    projection_text_fields = tuple(
        field for field in projection_fields if field != "mechanismFiles"
    )
    return (
        payload.get("captureProtocol") == "direct-host-material-events-v1"
        and _records(messages) and messages
        and all(_text(item.get(field)) for item in messages
                for field in ("role", "phase", "text"))
        and {item.get("role") for item in messages} == {"user", "assistant"}
        and _records(payload.get("materialEvents")) and payload["materialEvents"]
        and (
            "report-scoped-unknowns-recheck-triggers-and-claim-limit" not in required
            or _records(triggers) and triggers and all(
                _exact(item, ("kind", "condition", "scope", "action"),
                       ("kind", "condition", "scope", "action"))
                and item["kind"] == "recheck-trigger"
                and all(_text(item[field]) for field in item)
                for item in triggers
            )
        )
        and _postcapture_bundle(payload, task, captured_at) is not None
        and _continuity_handoff_bundle(payload, task) is not None
        and _longitudinal_bundle(payload, task) is not None
        and all(field in projection_fields for field in (
            "adapterId", "skill", "skillSha256",
        ))
        and _exact(
            exposure, ("kind", *projection_fields), projection_text_fields,
        )
        and (
            "mechanismFiles" not in projection_fields
            or isinstance(exposure.get("mechanismFiles"), list)
            and exposure["mechanismFiles"]
            and len(exposure["mechanismFiles"]) == len(set(exposure["mechanismFiles"]))
            and all(_text(locator) for locator in exposure["mechanismFiles"])
        )
        and _text(exposure.get("kind"))
        and exposure["kind"] in {
            "exact-skill-content-read", "host-runtime-attribution"
        }
        and isinstance(projection, dict)
        and all(exposure[field] == projection[field]
                for field in projection_fields)
        and _records(sources)
        and all(_official_source(item, captured_at) for item in sources)
        and len({_canonical_official_url(item["url"]) for item in sources}) == len(sources)
        and ("resolve-current-official-guidance" not in required or len(sources) >= 2)
        and isinstance(evidence, dict) and set(evidence) == {"state", "observations"}
        and isinstance(cleanup, dict)
        and evidence["state"] == cleanup.get("state")
        and _records(evidence["observations"]) and evidence["observations"]
        and _records(payload.get("redactions")) and _text(payload.get("evidenceBoundary"))
        and ("surface-only-the-exact-human-decision" not in required or any(
            item["phase"] == "human-grant" and item["role"] == "user"
            for item in messages
        ))
    )


_CANDIDATE_RULE_INSERTION = (
    "Each task declares only its relevant behavior-subject files; a promoted "
    "observation and its source record bind one ancestor evaluatedRevision, and "
    "current tracked subject bytes must remain identical while task and evaluation "
    "digests bind current semantics. This sparse invalidation rule neither accepts "
    "stale core behavior nor forces replay for unrelated evidence or presentation "
    "changes."
)


def _representative_contract(acceptance, golden):
    semantic_fields = (
        "id", "class", "name", "mapsTo", "statement", "passRule",
        "requiredEvidenceClasses",
    )
    criteria = acceptance.get("criteria")
    policy = acceptance.get("representativeBehaviorPolicy")
    digest_policy = dict(policy) if isinstance(policy, dict) else policy
    if isinstance(digest_policy, dict):
        digest_policy.pop("evaluationContractHistory", None)
    return {
        "productId": acceptance.get("productId"),
        "release": acceptance.get("release"),
        "evidenceLanes": acceptance.get("evidenceLanes"),
        "representativeBehaviorPolicy": digest_policy,
        "claimCeiling": {
            field: acceptance.get("claimCeiling", {}).get(field)
            for field in ("finiteReleaseClaims", "notImplied")
        },
        "criteria": [
            {field: item.get(field) for field in semantic_fields}
            for item in criteria if isinstance(item, dict)
            and "representative-behavior" in item.get("requiredEvidenceClasses", [])
        ] if isinstance(criteria, list) else [],
        "evaluationProtocol": golden.get("evaluationProtocol"),
        "metrics": golden.get("metrics"),
    }


def representative_contract_sha256(acceptance, golden):
    return _digest(_representative_contract(acceptance, golden))


def _candidate_evaluation_delta(
    prior_acceptance, prior_golden, prior_digest,
    current_acceptance, current_golden, current_digest,
):
    try:
        prior = _representative_contract(prior_acceptance, prior_golden)
        current = _representative_contract(current_acceptance, current_golden)
    except (AttributeError, TypeError, ValueError):
        return False
    if _digest(prior) != prior_digest or _digest(current) != current_digest:
        return False
    prior_policy, current_policy = (
        prior.get("representativeBehaviorPolicy"),
        current.get("representativeBehaviorPolicy"),
    )
    prior_protocol, current_protocol = (
        prior.get("evaluationProtocol"), current.get("evaluationProtocol"),
    )
    if not all(isinstance(item, dict) for item in (
        prior_policy, current_policy, prior_protocol, current_protocol,
    )):
        return False
    prior_rule, current_rule = (
        prior_policy.get("releaseDecisionRule"),
        current_policy.get("releaseDecisionRule"),
    )
    head, separator, tail = prior_rule.partition(". ") \
        if isinstance(prior_rule, str) else ("", "", "")
    expected_rule = f"{head}. {_CANDIDATE_RULE_INSERTION} {tail}"
    if (
        not separator or current_rule != expected_rule
        or "requiredCandidateObservationFields" in prior_protocol
        or current_protocol.get("requiredCandidateObservationFields")
        != ["evaluatedRevision"]
    ):
        return False
    normalized = json.loads(json.dumps(current))
    normalized["representativeBehaviorPolicy"]["releaseDecisionRule"] = prior_rule
    normalized["evaluationProtocol"].pop("requiredCandidateObservationFields")
    return normalized == prior


def _evaluation_contracts(policy, task_id, current):
    contracts = {current}
    history = policy.get("evaluationContractHistory") if isinstance(policy, dict) else None
    if not isinstance(history, list):
        return None
    for item in history:
        preserved = item.get("preservedTaskIds") if isinstance(item, dict) else None
        if (
            not _exact(item, ("kind", "sha256", "preservedTaskIds", "reason"),
                       ("sha256", "reason"))
            or item["kind"] != "scoped-evaluation-contract-supersession"
            or re.fullmatch(r"[0-9a-f]{64}", item["sha256"]) is None
            or _string_set(preserved) is None or not preserved
        ):
            return None
        if task_id in preserved:
            contracts.add(item["sha256"])
    return contracts


def _source_amendments(
    root, record, task, task_digest, captured_at, current_contract=None,
):
    amendments = record.get("amendments") if isinstance(record, dict) else None
    if amendments is None:
        if current_contract is None:
            return True
        return (isinstance(record, dict)
                and isinstance(current_contract, tuple)
                and len(current_contract) == 3
                and record.get("evaluationContractSha256") == current_contract[2])
    if (not isinstance(amendments, list) or not amendments
            or any(not isinstance(a, dict) for a in amendments)):
        return False
    change_class = amendments[0].get("changeClass")
    prior_digest = amendments[0].get("priorGoldenTaskSha256")
    if change_class == "observed-context-correction":
        ws = task.get("workspaceContract")
        if (not isinstance(ws, dict)
                or prior_digest != ws.get("supersedesGoldenTaskSha256")):
            return False
    elif change_class == "candidate-subject-binding":
        payload = record.get("payload")
        revision = payload.get("evaluatedRevision") if isinstance(payload, dict) else None
        if re.fullmatch(r"[0-9a-f]{40}", revision or "") is None:
            return False
        try:
            prior_golden = _strict_json_object(_bounded_git_bytes(
                root, ["show", "--end-of-options", f"{revision}:evals/golden-tasks.json"]
            ))
            prior_acceptance = _strict_json_object(_bounded_git_bytes(
                root, ["show", "--end-of-options", f"{revision}:product/acceptance.json"]
            ))
        except (OSError, subprocess.SubprocessError, UnicodeError, ValueError):
            return False
        tasks = prior_golden.get("tasks")
        if (not isinstance(tasks, list)
                or any(not isinstance(item, dict) for item in tasks)):
            return False
        matches = [item for item in tasks if item.get("id") == task.get("id")]
        if len(matches) != 1:
            return False
        prior_task = matches[0]
        current = dict(task)
        current.pop("behaviorSubjectFiles", None)
        current_tuple = current_contract if isinstance(current_contract, tuple) else ()
        amendment = amendments[0]
        if (len(amendments) != 1 or len(current_tuple) != 3
                or prior_task != current
                or _digest(prior_task) != prior_digest
                or record.get("evaluationContractSha256")
                != amendment.get("priorEvaluationContractSha256")):
            return False
        current_acceptance, current_golden, current_evaluation = current_tuple
        if not _candidate_evaluation_delta(
            prior_acceptance, prior_golden,
            amendment.get("priorEvaluationContractSha256"),
            current_acceptance, current_golden,
            amendment.get("correctedEvaluationContractSha256"),
        ) or amendment.get("correctedEvaluationContractSha256") != current_evaluation:
            return False
    else:
        return False
    previous_time = captured_at
    previous_digest = None
    evaluation_fields = (
        "priorEvaluationContractSha256", "correctedEvaluationContractSha256",
    ) if change_class == "candidate-subject-binding" else ()
    for amendment in amendments:
        amended_at = _time(amendment.get("amendedAt"))
        if (
            not _exact(amendment, (
                "kind", "amendedAt", "changeClass", "priorGoldenTaskSha256",
                "correctedGoldenTaskSha256", "behaviorReplayPerformed",
                "scope", "reason", "claimImpact",
                *evaluation_fields,
            ), (
                "kind", "amendedAt", "changeClass", "priorGoldenTaskSha256",
                "correctedGoldenTaskSha256", "scope", "reason", "claimImpact",
                *evaluation_fields,
            ))
            or amendment.get("kind") != "contract-correction"
            or amendment.get("changeClass") != change_class
            or amendment.get("behaviorReplayPerformed") is not False
            or amendment.get("claimImpact") != "metadata-only-no-new-behavior-claim"
            or re.fullmatch(
                r"[0-9a-f]{64}", amendment.get("priorGoldenTaskSha256", "")
            ) is None
            or re.fullmatch(
                r"[0-9a-f]{64}", amendment.get("correctedGoldenTaskSha256", "")
            ) is None
            or any(re.fullmatch(
                r"[0-9a-f]{64}", amendment.get(field, "")
            ) is None for field in evaluation_fields)
            or evaluation_fields and amendment["priorEvaluationContractSha256"]
            == amendment["correctedEvaluationContractSha256"]
            or amendment.get("priorGoldenTaskSha256")
            == amendment.get("correctedGoldenTaskSha256")
            or previous_digest is not None
            and amendment.get("priorGoldenTaskSha256") != previous_digest
            or amended_at is None or amended_at > datetime.now().astimezone()
            or previous_time is None or amended_at < previous_time
        ):
            return False
        previous_time = amended_at
        previous_digest = amendment["correctedGoldenTaskSha256"]
    return previous_digest == task_digest


def _behavior_subject_revision_errors(root, label, observation, task):
    revision, files = observation.get("evaluatedRevision"), task.get(
        "behaviorSubjectFiles"
    )
    if re.fullmatch(r"[0-9a-f]{40}", revision or "") is None:
        return [f"{label} evaluatedRevision is invalid"]
    if (not isinstance(files, list) or not files
            or any(not _text(locator) for locator in files)):
        return [f"{label} behavior subject is invalid"]
    try:
        tracked = subprocess.check_output(
            ["git", "-C", str(root), "ls-files", "--", *files],
            stderr=subprocess.DEVNULL, text=True,
        ).splitlines()
        ancestor = subprocess.run(
            ["git", "-C", str(root), "merge-base", "--is-ancestor", revision, "HEAD"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        ).returncode
        changed = subprocess.run(
            ["git", "-C", str(root), "diff", "--quiet", revision, "--", *files],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        ).returncode
    except (OSError, subprocess.SubprocessError, UnicodeError, ValueError):
        return [f"{label} behavior subject is unavailable"]
    if set(tracked) != set(files) or len(tracked) != len(files):
        return [f"{label} behavior subject is not the exact tracked set"]
    if ancestor != 0:
        return [f"{label} evaluatedRevision is not an ancestor"]
    if changed != 0:
        return [f"{label} behavior subject differs from evaluatedRevision"]
    return []


def _observation_errors(
    root, label, observation, task, burden_metrics, observation_locator,
    projection_id, evaluation_digest, read_json, require_current_subject=False,
    current_contract=None,
):
    errors = []
    if require_current_subject:
        errors.extend(_behavior_subject_revision_errors(
            root, label, observation, task
        ))
    observed_at = _time(observation.get("observedAt"))
    observer, host = observation.get("observer"), observation.get("hostIdentity")
    if observed_at is None or observed_at > datetime.now().astimezone():
        errors.append(f"{label} observedAt is invalid")
    if (
        not _exact(observer, ("kind", "identity"), ("identity",))
        or not _text(observer.get("kind"))
        or observer["kind"] not in {"human-observer", "host-event-recorder"}
    ):
        errors.append(f"{label} observer is invalid")
    if (
        not _exact(host, ("adapterId", "hostProduct", "hostVersion", "sessionId"),
                   ("hostProduct", "hostVersion", "sessionId"))
        or host.get("adapterId") != projection_id
    ):
        errors.append(f"{label} hostIdentity is invalid")
    if not isinstance(observation.get("projectionIdentity"), dict) or not observation[
        "projectionIdentity"
    ]:
        errors.append(f"{label} projectionIdentity is invalid")
    if observation.get("startingState") != {"declared": task.get("startingState")}:
        errors.append(f"{label} startingState does not match the Golden Task")
    task_digest = _digest(task)
    if observation.get("goldenTaskSha256") != task_digest:
        errors.append(f"{label} Golden Task digest mismatch")
    evaluation_digests = ({evaluation_digest} if isinstance(evaluation_digest, str)
                          else set(evaluation_digest or []))
    if observation.get("evaluationContractSha256") not in evaluation_digests:
        errors.append(f"{label} evaluation contract digest mismatch")
    for field in ("observedAgentActions", "observedHumanActions", "materialEffects", "residue"):
        value = observation.get(field)
        if not _records(value) or field == "observedAgentActions" and not value:
            errors.append(f"{label} {field} has invalid records")

    sources = observation.get("transcriptOrEventEvidence")
    if not isinstance(sources, list) or not sources:
        errors.append(f"{label} lacks source evidence")
        sources = []
    for index, source in enumerate(sources):
        locator = source.get("locator") if isinstance(source, dict) else None
        record_id = source.get("recordId") if isinstance(source, dict) else None
        bundle = read_json(root, locator, errors) if _text(locator) and locator != observation_locator else {}
        records = bundle.get("records") if isinstance(bundle, dict) else None
        record = records.get(record_id) if isinstance(records, dict) else None
        captured = _time(record.get("capturedAt")) if isinstance(record, dict) else None
        binding_contract = task.get("postSessionBindingContract")
        source_fields = ("kind", "locator", "recordId", "sha256", "claim") + (
            ("postSessionBindingsSha256",) if binding_contract else ()
        )
        postcapture = _postcapture_bundle(
            record.get("payload", {}), task, captured
        ) if isinstance(record, dict) else None
        record_fields = (
            "kind", "taskId", "goldenTaskSha256", "evaluationContractSha256",
            "hostIdentity", "capturedAt", "payload",
        ) + (("amendments",) if isinstance(record, dict) and "amendments" in record else ())
        valid = (
            _exact(source, source_fields,
                   ("locator", "recordId", "claim"))
            and _text(source.get("kind"))
            and source["kind"] in {"host-transcript", "host-event-log"}
            and _exact(bundle, ("schema", "records")) and bundle.get("schema") == 1
            and _exact(record, record_fields)
            and _source_amendments(
                root, record, task, task_digest, captured, current_contract,
            )
            and record.get("kind") == source.get("kind")
            and record.get("taskId") == task.get("id")
            and record.get("goldenTaskSha256") == task_digest
            and record.get("evaluationContractSha256") == observation.get(
                "evaluationContractSha256")
            and (not require_current_subject or isinstance(record.get("payload"), dict)
                 and record["payload"].get("evaluatedRevision")
                 == observation.get("evaluatedRevision"))
            and record.get("hostIdentity") == host
            and captured is not None and observed_at is not None and captured <= observed_at
            and _publishable_payload(
                record.get("payload"), task, observation.get("cleanup"), captured,
                observation.get("projectionIdentity"),
            )
            and source.get("sha256") == _digest(record)
            and (not binding_contract or postcapture is not None and source.get(
                "postSessionBindingsSha256") == _digest(postcapture))
        )
        if not valid:
            errors.append(f"{label} sourceEvidence[{index}] is invalid")

    behaviors = observation.get("behaviorDecisions")
    required = behaviors.get("required") if isinstance(behaviors, dict) else None
    prohibited = behaviors.get("prohibited") if isinstance(behaviors, dict) else None
    behavior_valid = (
        isinstance(behaviors, dict) and set(behaviors) == {"required", "prohibited"}
        and _enum_map(required, _string_set(task.get("required")), {"observed", "not-observed"})
        and _enum_map(prohibited, _string_set(task.get("prohibited")), {"absent", "observed"})
    )
    if not behavior_valid:
        errors.append(f"{label} behaviorDecisions are incomplete")
    failures = [] if not behavior_valid else [
        *(f"required:{key}" for key, value in required.items() if value == "not-observed"),
        *(f"prohibited:{key}" for key, value in prohibited.items() if value == "observed"),
    ]
    burden = observation.get("humanBurden")
    expected_burden = _string_set(burden_metrics)
    if (
        expected_burden is None or not isinstance(burden, dict)
        or set(burden) != expected_burden
        or any(not isinstance(value, int) or isinstance(value, bool) or value < 0 for value in burden.values())
    ):
        errors.append(f"{label} humanBurden is invalid")
    cleanup = observation.get("cleanup")
    cleanup_valid = (
        _exact(cleanup, ("state", "taskOwnedResidueCount", "verified"))
        and _text(cleanup.get("state"))
        and cleanup["state"] in {"verified-clean", "verified-foreign-state-preserved", "failed-residue"}
        and isinstance(cleanup.get("taskOwnedResidueCount"), int)
        and not isinstance(cleanup.get("taskOwnedResidueCount"), bool)
        and cleanup["taskOwnedResidueCount"] >= 0 and isinstance(cleanup.get("verified"), bool)
    )
    if not cleanup_valid:
        errors.append(f"{label} cleanup is invalid")
    residue = observation.get("residue")
    cleanup_consistent = cleanup_valid and not (
        cleanup["state"] == "verified-clean" and residue
        or cleanup["state"] == "failed-residue"
        and (not residue or not cleanup["taskOwnedResidueCount"])
        or cleanup["taskOwnedResidueCount"] and not residue
    )
    if cleanup_valid and not cleanup_consistent:
        errors.append(f"{label} cleanup contradicts residue records")
    clean = cleanup_consistent and cleanup["verified"] and not cleanup[
        "taskOwnedResidueCount"
    ] and cleanup["state"] != "failed-residue"
    if cleanup_valid and not clean:
        failures.append("cleanup")

    mapped = {
        value for value in task.get("mapsTo", [])
        if isinstance(value, str) and re.fullmatch(r"[RQ][0-9]+", value)
    }
    decisions = observation.get("criterionDecisions")
    expected_decision = "accepted-with-exclusion" if failures else "accepted"
    if not _enum_map(decisions, mapped, {expected_decision}):
        errors.append(f"{label} criterionDecisions contradict behavior")
    claim = observation.get("claimLimit")
    if (
        not _exact(claim, ("retainedFailure", "excludedClaims", "statement"), ("statement",))
        or not isinstance(claim.get("retainedFailure"), bool)
        or not isinstance(claim.get("excludedClaims"), list)
        or any(not _text(value) for value in claim.get("excludedClaims", []))
    ):
        errors.append(f"{label} claimLimit is invalid")
    elif behavior_valid and (
        claim["retainedFailure"] is not bool(failures)
        or set(claim["excludedClaims"]) != set(failures)
        or len(claim["excludedClaims"]) != len(failures)
    ):
        errors.append(f"{label} claimLimit contradicts behavior")
    decision = observation.get("decision")
    raw_state = decision.get("state") if isinstance(decision, dict) else None
    state = raw_state if _text(raw_state) and raw_state in STATES else None
    if state is None:
        errors.append(f"{label} has invalid decision")
    elif state == "passed" and (failures or not clean):
        errors.append(f"{label} passed decision contradicts records")
    elif state in {"failed", "failed-repeated-same-purpose"} and not failures:
        errors.append(f"{label} failure lacks counterevidence")
    return errors, state


def representative_sample_errors(
    root, acceptance, required_task_ids, golden, read_json, require_complete=False,
):
    criteria = acceptance.get("criteria")
    if not isinstance(criteria, list):
        return []
    representative = next(
        (item for item in criteria if isinstance(item, dict) and item.get("id") == "R3"), None
    )
    if not isinstance(representative, dict):
        return ["acceptance must contain representative criterion R3"]
    users = [
        item for item in criteria if isinstance(item, dict)
        and item.get("assessment") in {"verified", "continuing"}
        and "representative-behavior" in item.get("requiredEvidenceClasses", [])
    ]
    if not users:
        return []
    if representative.get("assessment") not in {"verified", "continuing"}:
        return [
            "verified or continuing representative evidence requires a retained R3 sample"
        ]
    protocol = golden.get("evaluationProtocol")
    fields = protocol.get("requiredObservationFields", []) if isinstance(protocol, dict) else []
    tasks = {
        item.get("id"): item for item in golden.get("tasks", [])
        if isinstance(item, dict) and _text(item.get("id"))
    }
    burden = golden.get("metrics", {}).get("humanBurden", [])
    evaluation = representative_contract_sha256(acceptance, golden)
    policy = acceptance.get("representativeBehaviorPolicy")
    binding_contracts = policy.get("postSessionBindingContracts", {}) \
        if isinstance(policy, dict) else {}
    if not isinstance(binding_contracts, dict):
        binding_contracts = {}
    errors, observed, states, r3_locators, exclusions = [], {}, {}, {}, []
    if _evaluation_contracts(policy, "", evaluation) is None:
        errors.append("representative evaluation contract history is invalid")
    exact_fields = set(fields) | {"evidenceClass"}
    require_current_subject = representative.get("assessment") in {
        "verified", "continuing"
    }
    if require_current_subject:
        exact_fields.update(protocol.get("requiredCandidateObservationFields", []))
    for index, item in enumerate(representative.get("evidence", [])):
        if not isinstance(item, dict) or not _text(item.get("locator")):
            continue
        label = f"R3 evidence[{index}]"
        observation = read_json(root, item["locator"], [])
        if set(observation) != exact_fields:
            errors.append(f"{label} observation shape invalid")
        task_id, task = observation.get("taskId"), tasks.get(observation.get("taskId"))
        if not _text(task_id) or not isinstance(task, dict):
            errors.append(f"{label} has unknown Golden Task")
            continue
        observed[task_id] = observed.get(task_id, 0) + 1
        r3_locators[item["locator"]] = task_id
        projection = item.get("bindsProjection")
        if task_id in required_task_ids and not _text(projection):
            errors.append(f"{label} required observation is not projection-bound")
        if task.get("postSessionBindingContract") != binding_contracts.get(task_id):
            errors.append(
                f"{label} post-session binding contract does not match representative policy"
            )
        local, state = _observation_errors(
            root, label, observation, task, burden, item["locator"],
            projection if _text(projection) else "",
            _evaluation_contracts(policy, task_id, evaluation) or {evaluation}, read_json,
            require_current_subject, (acceptance, golden, evaluation),
        )
        errors.extend(local)
        states[task_id] = state
        claim = observation.get("claimLimit")
        if state in {"failed", "failed-repeated-same-purpose"} and isinstance(claim, dict):
            exclusions.extend(
                f"{task_id}:{projection}:{value}"
                for value in claim.get("excludedClaims", [])
                if _text(value)
            )
    required = set(required_task_ids)
    missing = sorted(required - set(observed))
    duplicates = sorted(task for task in required if observed.get(task, 0) > 1)
    if require_complete and missing:
        errors.append(f"representative tasks missing: {missing}")
    if duplicates:
        errors.append(f"representative tasks duplicated: {duplicates}")
    must_pass = acceptance.get("representativeBehaviorPolicy", {}).get(
        "mustPassTaskIdsForRelease", []
    )
    failed_must_pass = sorted(
        task_id for task_id in must_pass
        if states.get(task_id) != "passed"
    ) if isinstance(must_pass, list) else []
    if require_complete and failed_must_pass:
        errors.append(f"must-pass tasks failed: {failed_must_pass}")
    policy = acceptance.get("representativeBehaviorPolicy", {})
    historical = policy.get("historicalEvidence", []) if isinstance(policy, dict) else []
    for item in historical if isinstance(historical, list) else []:
        locator = item.get("locator") if isinstance(item, dict) else None
        observation = read_json(root, locator, []) if _text(locator) else {}
        task_id = observation.get("taskId") if isinstance(observation, dict) else None
        claim = observation.get("claimLimit") if isinstance(observation, dict) else None
        if _text(task_id) and isinstance(claim, dict) and claim.get("retainedFailure") is True:
            adapter_id = observation.get("hostIdentity", {}).get("adapterId")
            exclusions.extend(
                f"{task_id}:{adapter_id}:{value}"
                for value in claim.get("excludedClaims", [])
                if _text(adapter_id) and _text(value)
            )
    declared = acceptance.get("claimCeiling", {}).get("retainedBehaviorExclusions")
    if declared != sorted(set(exclusions)):
        errors.append("retained behavior exclusions mismatch")
    for criterion in users:
        criterion_id = criterion.get("id")
        expected = {
            task_id for task_id in required
            if criterion_id in set(tasks.get(task_id, {}).get("mapsTo", []))
        }
        actual = [
            r3_locators.get(item.get("locator")) for item in criterion.get("evidence", [])
            if isinstance(item, dict)
        ]
        invalid_coverage = (
            len(actual) != len(set(actual))
            or require_complete and set(actual) != expected
            or not require_complete and not set(actual).issubset(expected)
        )
        if invalid_coverage:
            errors.append(
                f"{criterion_id} representative coverage mismatch"
            )
    return errors


def historical_representative_errors(root, acceptance, golden, read_json):
    policy = acceptance.get("representativeBehaviorPolicy")
    if not isinstance(policy, dict):
        return []
    items = policy.get("historicalEvidence")
    evaluation = policy.get("historicalEvidenceContractSha256")
    protocol = golden.get("evaluationProtocol") if isinstance(golden, dict) else None
    fields = protocol.get("requiredObservationFields", []) \
        if isinstance(protocol, dict) else []
    if not isinstance(items, list) or not _text(evaluation):
        return []
    tasks = {
        item.get("id"): item for item in golden.get("tasks", [])
        if isinstance(item, dict) and _text(item.get("id"))
    }
    historical_tasks = policy.get("historicalTaskContracts")
    if not isinstance(historical_tasks, dict):
        historical_tasks = {}
    for task_id, contract in historical_tasks.items():
        task = contract.get("task") if isinstance(contract, dict) else None
        if (
            not _text(task_id) or not isinstance(task, dict)
            or task.get("id") != task_id
            or contract.get("goldenTaskSha256") != _digest(task)
        ):
            errors = [f"historicalTaskContracts[{task_id!r}] is invalid"]
            return errors
        tasks[task_id] = task
    burden = golden.get("metrics", {}).get("humanBurden", [])
    binding_contracts = policy.get("postSessionBindingContracts", {})
    if not isinstance(binding_contracts, dict):
        binding_contracts = {}
    exact_fields = set(fields) | {"evidenceClass"}
    errors = []
    for index, item in enumerate(items):
        if not isinstance(item, dict) or not _text(item.get("locator")):
            continue
        label = f"historicalEvidence[{index}]"
        observation = read_json(root, item["locator"], [])
        if set(observation) != exact_fields:
            errors.append(f"{label} observation shape invalid")
        task_id = observation.get("taskId")
        task = tasks.get(task_id)
        if not isinstance(task, dict):
            errors.append(f"{label} has unknown Golden Task")
            continue
        if (
            task_id not in historical_tasks
            and task.get("postSessionBindingContract")
            != binding_contracts.get(task_id)
        ):
            errors.append(
                f"{label} post-session binding contract does not match representative policy"
            )
        projection = item.get("bindsProjection")
        local, _ = _observation_errors(
            root, label, observation, task, burden, item["locator"],
            projection if _text(projection) else "", evaluation, read_json,
        )
        errors.extend(local)
        claim = observation.get("claimLimit")
        if (
            item.get("supportsCriterion") != "R3"
            or not isinstance(claim, dict)
            or item.get("claim") != claim.get("statement")
        ):
            errors.append(f"{label} historical claim binding is invalid")
    return errors
