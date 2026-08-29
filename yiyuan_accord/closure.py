"""Pure, no-I/O closure decision core with one plain-data interface.

Human authority, provenance, availability, cross-form coherence and independent
consequence/cleanup evidence are stable invariants. Task policy supplies
additional conditions, dimensions, preferences and open-ended route forms.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import datetime, timezone
from math import isfinite
from numbers import Real
from typing import Any


SCHEMA = "yiyuan-accord-closure/v2"
DECISION_SCHEMA = "yiyuan-accord-closure-decision/v2"
FACT_VALUES = frozenset({"observed", "not-observed", "unknown"})
RESPONSIBILITY_MODES = frozenset({
    "accord-contained", "agent-native", "accord-agent-composed",
})
STATE_SOURCE_KINDS = frozenset({
    "official-host-state", "accord-state", "bounded-direct-observation",
})
STATE_SOURCE_ORDER = (
    "official-host-state", "accord-state", "bounded-direct-observation",
)
STATE_TARGET_KINDS = frozenset({
    "environment-fact", "route-fact", "coherence-fact",
})
COMPARISON_VALUES = frozenset({"better", "equal", "worse", "unknown"})
EXPERIMENT_POSTSTATE_VALUES = frozenset({
    "keep-complete", "rollback-complete",
})
EVIDENCE_BINDING_FIELDS = frozenset({
    "sourceRef", "observerRef", "subjectRef", "boundaryRef",
})
OBSERVATION_FIELDS = frozenset({
    "id", "compositionKey", "generation", "capturedAt", "decisionAt",
    "validUntil", "stateBindings", "invalidatedBy",
})
STATE_BINDING_FIELDS = frozenset({
    "field", "targetKind", "subjectRef", "factId", "value", "writer",
    "readers", "sourceKind", "sourceRef", "unavailableSources", "generation",
})
LAST_SAFE_ALLOCATION_FIELDS = frozenset({
    "routeId", "responsibilityModes", "observationId",
    "observationGeneration", "evidence",
})

# These are compliance/evidence invariants, not a product-form or workflow list.
COMPLIANCE_ENVIRONMENT_FACTS = ("provenance-bound",)
COMPLIANCE_ROUTE_FACTS = (
    "within-human-authority",
    "compliant",
    "independent-consequence-verifier",
    "available",
)
COMPLIANCE_COHERENCE_FACTS = (
    "responsibility-boundaries",
    "interfaces-and-version",
    "authority-and-side-effects",
    "state-owner-and-freshness",
    "evidence-and-independent-poststate",
    "failure-degradation-and-recovery",
    "update-replacement-and-rollback",
    "cleanup-retirement-and-residue",
)
COMPLIANCE_COMPLETION_FACTS = ("consequence", "cleanup-poststate")
COMPLIANCE_EXPERIMENT_FACTS = (
    "immutable-evaluator",
    "available-rollback",
    "independent-effect-and-cleanup-poststate",
)
COMPLIANCE_EXPERIMENT_DIMENSIONS = ("authority", "evidence")
COMPLIANCE_RETIREMENT_FACTS = (
    "within-human-authority",
    "current-successor-capability-observed",
    "same-responsibility-overlap-derived",
    "retired-route-prestate",
    "task-defined-observation-window-complete",
    "available-rollback",
)


def _identifier(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip()) and len(value) <= 256


def _string_list(value: Any, *, allow_empty: bool = True) -> bool:
    return (
        isinstance(value, list)
        and (allow_empty or bool(value))
        and all(_identifier(item) for item in value)
        and len(value) == len(set(value))
    )


def _fact_map(value: Any) -> bool:
    return (
        isinstance(value, Mapping)
        and all(_identifier(key) and fact in FACT_VALUES
                for key, fact in value.items())
    )


def _responsibility_modes(value: Any, supplies: Any) -> bool:
    return (
        isinstance(value, Mapping)
        and _string_list(supplies)
        and set(value) == set(supplies)
        and all(mode in RESPONSIBILITY_MODES for mode in value.values())
    )


def _utc(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value.endswith("Z"):
        return None
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError:
        return None
    return parsed if parsed.tzinfo == timezone.utc else None


def _observation(value: Any) -> bool:
    bindings = value.get("stateBindings") if isinstance(value, Mapping) else None
    return (
        isinstance(value, Mapping)
        and set(value) == OBSERVATION_FIELDS
        and _identifier(value.get("id"))
        and _identifier(value.get("compositionKey"))
        and isinstance(value.get("generation"), int)
        and not isinstance(value.get("generation"), bool)
        and value["generation"] > 0
        and all(_utc(value.get(field)) is not None for field in (
            "capturedAt", "decisionAt", "validUntil",
        ))
        and isinstance(bindings, list)
        and all(
            isinstance(item, Mapping)
            and set(item) == STATE_BINDING_FIELDS
            and _identifier(item.get("field"))
            and not item["field"].casefold().startswith((
                "conversation.raw", "credential.", "secret.",
            ))
            and item["field"].casefold() not in {"credential", "secret"}
            and item.get("targetKind") in STATE_TARGET_KINDS
            and _identifier(item.get("subjectRef"))
            and _identifier(item.get("factId"))
            and item.get("value") in FACT_VALUES
            and _identifier(item.get("writer"))
            and _string_list(item.get("readers"), allow_empty=False)
            and item.get("sourceKind") in STATE_SOURCE_KINDS
            and _identifier(item.get("sourceRef"))
            and item.get("unavailableSources") == list(
                STATE_SOURCE_ORDER[:STATE_SOURCE_ORDER.index(
                    item.get("sourceKind")
                )]
            )
            and isinstance(item.get("generation"), int)
            and not isinstance(item.get("generation"), bool)
            and item["generation"] == value["generation"]
            for item in bindings
        )
        and _string_list(value.get("invalidatedBy"))
    )


def _observation_failures(
    observation: Mapping[str, Any], composition_key: str,
) -> list[dict[str, str]]:
    captured = _utc(observation["capturedAt"])
    decision = _utc(observation["decisionAt"])
    valid_until = _utc(observation["validUntil"])
    checks = (
        (not observation["stateBindings"], "state-source", "unknown",
         "environment observation has no current state source"),
        (observation["compositionKey"] != composition_key, "composition",
         "not-observed", "environment observation composition is mismatched"),
        (captured > decision, "future", "not-observed",
         "environment observation was captured after the decision"),
        (decision > valid_until, "expired", "not-observed",
         "environment observation expired before the decision"),
        (bool(observation["invalidatedBy"]), "invalidated", "not-observed",
         "environment observation has pending invalidation signals"),
    )
    return [{"code": f"environment:observation-{code}", "state": state,
             "detail": detail} for failed, code, state, detail in checks if failed]


def _state_binding_failures(
    observation: Mapping[str, Any], environment: Mapping[str, Any],
    routes: Sequence[Mapping[str, Any]], policy: Mapping[str, Any],
) -> list[dict[str, str]]:
    bindings = observation["stateBindings"]
    failures: list[dict[str, str]] = []
    by_field: dict[str, list[Mapping[str, Any]]] = {}
    by_target: dict[tuple[str, str, str], list[Mapping[str, Any]]] = {}
    for binding in bindings:
        by_field.setdefault(binding["field"], []).append(binding)
        target = (
            binding["targetKind"], binding["subjectRef"], binding["factId"],
        )
        by_target.setdefault(target, []).append(binding)
    for field, items in by_field.items():
        if len(items) > 1:
            failures.append({
                "code": f"environment:state-binding-conflict:{field}",
                "state": "unknown",
                "detail": f"state field {field} has multiple bindings",
            })
    for target, items in by_target.items():
        if len(items) > 1:
            failures.append({
                "code": "environment:state-target-conflict:" + ":".join(target),
                "state": "unknown",
                "detail": "decision target has multiple state bindings",
            })

    route_by_id = {route["id"]: route for route in routes}
    for binding in bindings:
        kind, subject, fact_id = (
            binding["targetKind"], binding["subjectRef"], binding["factId"],
        )
        if kind == "environment-fact":
            expected_subject = environment["compositionKey"]
            facts = environment["facts"]
        else:
            route = route_by_id.get(subject)
            expected_subject = subject if route is not None else None
            facts = route.get(
                "facts" if kind == "route-fact" else "coherence", {}
            ) if route is not None else {}
        if expected_subject is None or subject != expected_subject \
                or facts.get(fact_id) != binding["value"]:
            failures.append({
                "code": (
                    f"environment:state-binding-mismatch:{kind}:"
                    f"{subject}:{fact_id}"
                ),
                "state": "not-observed",
                "detail": "state binding does not equal its decision target",
            })

    required_targets = {
        ("environment-fact", environment["compositionKey"], fact_id)
        for fact_id in _ordered_union(
            COMPLIANCE_ENVIRONMENT_FACTS, policy["requiredEnvironmentFacts"]
        )
    }
    required_route_facts = _ordered_union(
        COMPLIANCE_ROUTE_FACTS, policy["requiredRouteFacts"]
    )
    required_coherence = _ordered_union(
        COMPLIANCE_COHERENCE_FACTS, policy["requiredCoherenceFacts"]
    )
    for route in routes:
        required_targets.update(
            ("route-fact", route["id"], fact_id)
            for fact_id in required_route_facts
        )
        if len(route["forms"]) > 1:
            required_targets.update(
                ("coherence-fact", route["id"], fact_id)
                for fact_id in required_coherence
            )
    for target in sorted(required_targets - set(by_target)):
        failures.append({
            "code": "environment:state-binding-missing:" + ":".join(target),
            "state": "unknown",
            "detail": "decision target has no typed state binding",
        })
    return failures


def _retirement_specs(value: Any) -> bool:
    return (
        isinstance(value, list)
        and all(
            isinstance(item, Mapping)
            and set(item) == {"routeId", "responsibilities"}
            and _identifier(item.get("routeId"))
            and _string_list(
                item.get("responsibilities"), allow_empty=False
            )
            for item in value
        )
        and len({
            (item["routeId"], tuple(sorted(item["responsibilities"])))
            for item in value
        }) == len(value)
    )


def _number_map(value: Any, dimensions: Sequence[str]) -> bool:
    return (
        isinstance(value, Mapping)
        and all(
            dimension in value
            and isinstance(value[dimension], Real)
            and not isinstance(value[dimension], bool)
            and isfinite(float(value[dimension]))
            and value[dimension] >= 0
            for dimension in dimensions
        )
    )


def _evidence_binding(value: Any) -> bool:
    return (
        isinstance(value, Mapping)
        and set(value) == EVIDENCE_BINDING_FIELDS
        and all(_identifier(value[field]) for field in EVIDENCE_BINDING_FIELDS)
        and value["observerRef"] != value["subjectRef"]
        and value["sourceRef"] != value["subjectRef"]
        and value["boundaryRef"] != value["subjectRef"]
    )


def _evidence_binding_for(value: Any, subject: Any) -> bool:
    return _evidence_binding(value) and value["subjectRef"] == subject


def _last_safe_allocation(
    value: Any, observation: Any, outcome: Any,
    route_by_id: Mapping[str, Mapping[str, Any]],
) -> bool:
    if value is None:
        return True
    if (
        not isinstance(value, Mapping)
        or set(value) != LAST_SAFE_ALLOCATION_FIELDS
        or not isinstance(observation, Mapping)
        or not isinstance(outcome, Mapping)
        or not _identifier(value.get("routeId"))
        or value["routeId"] not in route_by_id
        or value.get("observationId") != observation.get("id")
        or value.get("observationGeneration") != observation.get("generation")
        or not _evidence_binding_for(value.get("evidence"), value["routeId"])
    ):
        return False
    responsibilities = outcome.get("responsibilities")
    modes = value.get("responsibilityModes")
    route = route_by_id[value["routeId"]]
    return (
        _string_list(responsibilities, allow_empty=False)
        and isinstance(modes, Mapping)
        and set(modes) == set(responsibilities)
        and all(mode in RESPONSIBILITY_MODES for mode in modes.values())
        and all(
            isinstance(route.get("supplies"), list)
            and responsibility in route["supplies"]
            and isinstance(route.get("responsibilityModes"), Mapping)
            and route["responsibilityModes"].get(responsibility)
            == modes[responsibility]
            for responsibility in responsibilities
        )
    )


def _ordered_union(*groups: Sequence[str]) -> list[str]:
    result: list[str] = []
    for group in groups:
        for item in group:
            if item not in result:
                result.append(item)
    return result


def _validate_request(request: Any) -> list[str]:
    errors: list[str] = []
    if not isinstance(request, Mapping):
        return ["request must be an object"]
    if request.get("schema") != SCHEMA:
        errors.append(f"schema must be {SCHEMA}")

    outcome = request.get("outcome")
    if not isinstance(outcome, Mapping):
        errors.append("outcome must be an object")
    else:
        if not _identifier(outcome.get("id")):
            errors.append("outcome.id must be a bounded non-empty string")
        if not _string_list(outcome.get("responsibilities"), allow_empty=False):
            errors.append("outcome.responsibilities must be a unique non-empty string list")

    environment = request.get("environment")
    if not isinstance(environment, Mapping):
        errors.append("environment must be an object")
    else:
        if not _identifier(environment.get("compositionKey")):
            errors.append("environment.compositionKey must be a bounded non-empty string")
        if not _fact_map(environment.get("facts")):
            errors.append("environment.facts must map identifiers to tri-state facts")
        if not _string_list(environment.get("unknowns")):
            errors.append("environment.unknowns must be a unique string list")
        if not _observation(environment.get("observation")):
            errors.append("environment.observation must be a bounded live receipt")
        if "lastSafeAllocation" not in environment:
            errors.append("environment.lastSafeAllocation must be explicit")

    policy = request.get("policy")
    policy_lists = (
        "requiredEnvironmentFacts", "requiredRouteFacts",
        "requiredCoherenceFacts", "comparisonDimensions",
        "sourcePreference", "contextPreference", "requiredCompletionFacts",
        "requiredExperimentFacts", "experimentDimensions",
    )
    if not isinstance(policy, Mapping):
        errors.append("policy must be an object")
    else:
        if not _identifier(policy.get("id")):
            errors.append("policy.id must be a bounded non-empty string")
        for field in policy_lists:
            allow_empty = field != "comparisonDimensions"
            if not _string_list(policy.get(field), allow_empty=allow_empty):
                errors.append(f"policy.{field} must be a unique string list")
        if not _string_list(policy.get("requiredRetirementFacts", [])):
            errors.append(
                "policy.requiredRetirementFacts must be a unique string list"
            )
        if not _retirement_specs(
            policy.get("requiredRetirementAllocations", [])
        ):
            errors.append(
                "policy.requiredRetirementAllocations must be a unique "
                "allocation list"
            )
        if "requiredRetirementRouteIds" in policy:
            errors.append(
                "policy.requiredRetirementRouteIds is unsupported; bind exact "
                "responsibility allocations"
            )

    routes = request.get("routes")
    if not isinstance(routes, list) or not routes:
        errors.append("routes must be a non-empty object list")
        routes = []
    route_ids: list[str] = []
    dimensions = policy.get("comparisonDimensions", []) \
        if isinstance(policy, Mapping) else []
    dimensions = dimensions if _string_list(dimensions, allow_empty=False) else []
    coherence_required = policy.get("requiredCoherenceFacts", []) \
        if isinstance(policy, Mapping) else []
    coherence_required = _ordered_union(
        COMPLIANCE_COHERENCE_FACTS,
        coherence_required if _string_list(coherence_required) else [],
    )
    for index, route in enumerate(routes):
        label = f"routes[{index}]"
        if not isinstance(route, Mapping):
            errors.append(f"{label} must be an object")
            continue
        route_id = route.get("id")
        if not _identifier(route_id):
            errors.append(f"{label}.id must be a bounded non-empty string")
        else:
            route_ids.append(route_id)
        if not _identifier(route.get("sourceKind")):
            errors.append(f"{label}.sourceKind must be a bounded non-empty string")
        route_forms = route.get("forms")
        for field in ("forms", "supplies"):
            if not _string_list(route.get(field)):
                errors.append(f"{label}.{field} must be a unique string list")
        if not _responsibility_modes(
            route.get("responsibilityModes"), route.get("supplies")
        ):
            errors.append(
                f"{label}.responsibilityModes must allocate every supplied "
                "responsibility to one supported implementation mode"
            )
        if not _fact_map(route.get("facts")):
            errors.append(f"{label}.facts must map identifiers to tri-state facts")
        coherence = route.get("coherence")
        if not isinstance(coherence, Mapping) or not _fact_map(coherence):
            errors.append(f"{label}.coherence must map identifiers to tri-state facts")
        elif isinstance(route_forms, list) and len(route_forms) > 1 and any(
            fact not in coherence for fact in coherence_required
        ):
            errors.append(f"{label}.coherence lacks a required policy fact")
        if not _number_map(route.get("lifecycle"), dimensions):
            errors.append(f"{label}.lifecycle lacks a non-negative comparison dimension")
    if len(route_ids) != len(set(route_ids)):
        errors.append("route ids must be unique")
    required_retirements = policy.get("requiredRetirementAllocations", []) \
        if isinstance(policy, Mapping) else []
    route_by_id = {
        route.get("id"): route for route in routes
        if isinstance(route, Mapping)
    }
    outcome_responsibilities = outcome.get("responsibilities", []) \
        if isinstance(outcome, Mapping) else []
    if _retirement_specs(required_retirements):
        for allocation in required_retirements:
            route = route_by_id.get(allocation["routeId"])
            supplies = route.get("supplies", []) \
                if isinstance(route, Mapping) else []
            if route is None:
                errors.append(
                    "policy.requiredRetirementAllocations contains an "
                    "unknown route"
                )
            if any(
                responsibility not in outcome_responsibilities
                or not isinstance(supplies, list)
                or responsibility not in supplies
                for responsibility in allocation["responsibilities"]
            ):
                errors.append(
                    "policy.requiredRetirementAllocations exceeds the "
                    "current route responsibility scope"
                )
    if isinstance(environment, Mapping) and not _last_safe_allocation(
        environment.get("lastSafeAllocation"), environment.get("observation"),
        outcome, route_by_id,
    ):
        errors.append("environment.lastSafeAllocation is invalid")

    events = request.get("events")
    if not isinstance(events, list) or any(
        not isinstance(event, Mapping) for event in events
    ):
        errors.append("events must be an object list")
        events = []
    valid_route_ids = set(route_ids)
    experiment_dimensions = policy.get("experimentDimensions", []) \
        if isinstance(policy, Mapping) else []
    experiment_dimensions = experiment_dimensions \
        if _string_list(experiment_dimensions) else []
    required_experiment_dimensions = _ordered_union(
        COMPLIANCE_EXPERIMENT_DIMENSIONS, experiment_dimensions
    )
    for index, event in enumerate(events):
        label = f"events[{index}]"
        kind = event.get("kind")
        if kind == "fact-observed":
            if not _identifier(event.get("routeId")) \
                    or event.get("routeId") not in valid_route_ids:
                errors.append(f"{label}.routeId is unknown")
            if not _identifier(event.get("factId")):
                errors.append(f"{label}.factId is invalid")
            elif event.get("factId") == "cleanup-poststate":
                errors.append(
                    f"{label}.cleanup-poststate requires resource-poststate"
                )
            if event.get("state") not in FACT_VALUES:
                errors.append(f"{label}.state is invalid")
            if event.get("independent") not in FACT_VALUES:
                errors.append(f"{label}.independent is invalid")
            elif event.get("independent") == "observed" \
                    and not _evidence_binding_for(
                        event.get("evidence"), event.get("routeId")
                    ):
                errors.append(
                    f"{label}.independent evidence binding is invalid"
                )
        elif kind == "resource-poststate":
            if not _identifier(event.get("routeId")) \
                    or event.get("routeId") not in valid_route_ids:
                errors.append(f"{label}.routeId is unknown")
            if not _string_list(event.get("releasedResources")):
                errors.append(f"{label}.releasedResources is invalid")
            if not _string_list(event.get("residualTaskResources")):
                errors.append(f"{label}.residualTaskResources is invalid")
            elif isinstance(event.get("releasedResources"), list) and set(
                event["releasedResources"]
            ).intersection(event["residualTaskResources"]):
                errors.append(f"{label}.resource poststate is contradictory")
            if event.get("independent") not in FACT_VALUES:
                errors.append(f"{label}.independent is invalid")
            elif event.get("independent") == "observed" \
                    and not _evidence_binding_for(
                        event.get("evidence"), event.get("routeId")
                    ):
                errors.append(
                    f"{label}.independent evidence binding is invalid"
                )
        elif kind == "experiment-evaluated":
            if not _identifier(event.get("baselineRouteId")) \
                    or event.get("baselineRouteId") not in valid_route_ids:
                errors.append(f"{label}.baselineRouteId is unknown")
            if not _identifier(event.get("candidateRouteId")) \
                    or event.get("candidateRouteId") not in valid_route_ids:
                errors.append(f"{label}.candidateRouteId is unknown")
            elif event.get("candidateRouteId") == event.get("baselineRouteId"):
                errors.append(f"{label}.candidateRouteId must differ from baseline")
            if not _fact_map(event.get("preconditions")):
                errors.append(f"{label}.preconditions is invalid")
            if not _evidence_binding_for(
                event.get("evidence"), event.get("candidateRouteId")
            ):
                errors.append(f"{label}.evidence binding is invalid")
            comparison = event.get("comparison")
            if not isinstance(comparison, Mapping) or any(
                dimension not in comparison
                or comparison[dimension] not in COMPARISON_VALUES
                for dimension in required_experiment_dimensions
            ):
                errors.append(f"{label}.comparison is invalid")
        elif kind == "experiment-poststate":
            for field in ("baselineRouteId", "candidateRouteId"):
                if not _identifier(event.get(field)) \
                        or event.get(field) not in valid_route_ids:
                    errors.append(f"{label}.{field} is unknown")
            if event.get("disposition") not in EXPERIMENT_POSTSTATE_VALUES:
                errors.append(f"{label}.disposition is invalid")
            if event.get("state") not in FACT_VALUES:
                errors.append(f"{label}.state is invalid")
            if event.get("independent") not in FACT_VALUES:
                errors.append(f"{label}.independent is invalid")
            elif event.get("independent") == "observed" \
                    and not _evidence_binding_for(
                        event.get("evidence"), event.get("candidateRouteId")
                    ):
                errors.append(
                    f"{label}.independent evidence binding is invalid"
                )
        elif kind == "responsibility-allocation-retired":
            if not _identifier(event.get("routeId")) \
                    or event.get("routeId") not in valid_route_ids:
                errors.append(f"{label}.routeId is unknown")
            if not _identifier(event.get("replacementRouteId")) \
                    or event.get("replacementRouteId") not in valid_route_ids:
                errors.append(f"{label}.replacementRouteId is unknown")
            elif event.get("replacementRouteId") == event.get("routeId"):
                errors.append(
                    f"{label}.replacementRouteId must differ from routeId"
                )
            if not _evidence_binding_for(
                event.get("replacementEvidence"),
                event.get("replacementRouteId"),
            ):
                errors.append(
                    f"{label}.replacementEvidence binding is invalid"
                )
            responsibilities = event.get("responsibilities")
            if not _string_list(responsibilities, allow_empty=False):
                errors.append(f"{label}.responsibilities is invalid")
            else:
                outcome_responsibilities = outcome.get("responsibilities", []) \
                    if isinstance(outcome, Mapping) else []
                retired_route = route_by_id.get(event.get("routeId"), {})
                replacement_route = route_by_id.get(
                    event.get("replacementRouteId"), {}
                )
                retired_supplies = retired_route.get("supplies", []) \
                    if isinstance(retired_route, Mapping) else []
                replacement_supplies = replacement_route.get("supplies", []) \
                    if isinstance(replacement_route, Mapping) else []
                if any(item not in outcome_responsibilities
                       for item in responsibilities):
                    errors.append(
                        f"{label}.responsibilities exceed the current outcome"
                    )
                if any(item not in retired_supplies
                       for item in responsibilities):
                    errors.append(
                        f"{label}.responsibilities are not supplied by routeId"
                    )
                if any(item not in replacement_supplies
                       for item in responsibilities):
                    errors.append(
                        f"{label}.responsibilities are not supplied by replacementRouteId"
                    )
            if not _fact_map(event.get("preconditions")):
                errors.append(f"{label}.preconditions is invalid")
            if not _string_list(event.get("recheckTriggers"), allow_empty=False):
                errors.append(f"{label}.recheckTriggers is invalid")
            if event.get("state") not in FACT_VALUES:
                errors.append(f"{label}.state is invalid")
            if event.get("independent") not in FACT_VALUES:
                errors.append(f"{label}.independent is invalid")
            elif event.get("independent") == "observed" \
                    and not _evidence_binding_for(
                        event.get("evidence"), event.get("routeId")
                    ):
                errors.append(
                    f"{label}.independent evidence binding is invalid"
                )
        else:
            errors.append(f"{label}.kind is unsupported")
    return errors


def _fact_failures(
    facts: Mapping[str, str], required: Sequence[str], scope: str,
) -> list[dict[str, str]]:
    failures: list[dict[str, str]] = []
    for fact_id in required:
        state = facts.get(fact_id, "unknown")
        if state != "observed":
            failures.append({
                "code": f"{scope}:{fact_id}",
                "state": state,
                "detail": f"required {scope} fact {fact_id} is {state}",
            })
    return failures


def _dominates(
    left: Mapping[str, Any], right: Mapping[str, Any], dimensions: Sequence[str],
) -> bool:
    return (
        all(left[dimension] <= right[dimension] for dimension in dimensions)
        and any(left[dimension] < right[dimension] for dimension in dimensions)
    )


def _select(
    assessments: list[dict[str, Any]], policy: Mapping[str, Any],
) -> tuple[str | None, list[str], str]:
    admitted = [item for item in assessments if item["admitted"]]
    dimensions = policy["comparisonDimensions"]
    frontier = [
        item for item in admitted
        if not any(
            other["routeId"] != item["routeId"]
            and _dominates(other["lifecycle"], item["lifecycle"], dimensions)
            for other in admitted
        )
    ]
    frontier_ids = [item["routeId"] for item in frontier]
    if not frontier:
        unknown = any(
            failure["state"] == "unknown"
            for item in assessments for failure in item["failures"]
        )
        return None, [], "hold-unknown" if unknown else "honest-stop"
    if len(frontier) == 1:
        selected = frontier[0]
    else:
        preferred = next(
            (route_id for route_id in policy["contextPreference"]
             if route_id in frontier_ids),
            None,
        )
        vectors = {
            tuple(item["lifecycle"][dimension] for dimension in dimensions)
            for item in frontier
        }
        if preferred is not None:
            selected = next(item for item in frontier
                            if item["routeId"] == preferred)
        elif len(vectors) == 1:
            source_rank = {
                source: index
                for index, source in enumerate(policy["sourcePreference"])
            }
            selected = min(
                frontier,
                key=lambda item: (
                    source_rank.get(item["sourceKind"], len(source_rank)),
                    item["routeId"],
                ),
            )
        else:
            return None, sorted(frontier_ids), "hold-unknown"
    disposition = "no-op" if not selected["forms"] else "admit"
    return selected["routeId"], sorted(frontier_ids), disposition


def _experiment_decision(
    event: Mapping[str, Any], policy: Mapping[str, Any],
    admitted_ids: set[str], selected_id: str | None,
) -> tuple[str, list[str]]:
    reasons: list[str] = []
    if event["baselineRouteId"] != selected_id:
        reasons.append("baseline is not the selected route")
    if event["candidateRouteId"] not in admitted_ids:
        reasons.append("candidate route is not admitted")
    missing = _fact_failures(
        event["preconditions"], _ordered_union(
            COMPLIANCE_EXPERIMENT_FACTS,
            policy["requiredExperimentFacts"],
        ),
        "experiment",
    )
    reasons.extend(item["detail"] for item in missing)
    if reasons:
        return "hold-unknown", reasons
    values = [
        event["comparison"][dimension]
        for dimension in _ordered_union(
            COMPLIANCE_EXPERIMENT_DIMENSIONS,
            policy["experimentDimensions"],
        )
    ]
    if "worse" in values:
        return "discard-and-rollback", ["full acceptance vector regressed"]
    if "unknown" in values:
        return "hold-unknown", ["full acceptance vector contains unknown"]
    if "better" in values:
        return "keep-after-independent-poststate", [
            "at least one dimension improved and none regressed"
        ]
    return "hold-unknown", ["no independently observed net improvement"]


def reconcile_closure(request: Mapping[str, Any]) -> dict[str, Any]:
    """Return one deterministic closure decision without performing effects.

    Structural errors return ``valid=False``.  A valid request may still return
    ``hold-unknown`` or ``honest-stop``; those are successful fail-closed
    decisions, not exceptions.  The returned claim is limited to this exact
    request, composition key, policy and ordered observation list.
    """

    errors = _validate_request(request)
    if errors:
        return {
            "schema": DECISION_SCHEMA,
            "valid": False,
            "disposition": "reject",
            "selectedRouteId": None,
            "preservedAllocation": None,
            "frontierRouteIds": [],
            "assessments": [],
            "lifecycle": None,
            "errors": errors,
            "claimLimit": "invalid-request-no-closure-claim",
        }

    outcome = request["outcome"]
    environment = request["environment"]
    policy = request["policy"]
    required_route_facts = _ordered_union(
        COMPLIANCE_ROUTE_FACTS, policy["requiredRouteFacts"]
    )
    required_environment_facts = _ordered_union(
        COMPLIANCE_ENVIRONMENT_FACTS, policy["requiredEnvironmentFacts"]
    )
    required_coherence_facts = _ordered_union(
        COMPLIANCE_COHERENCE_FACTS, policy["requiredCoherenceFacts"]
    )
    environment_failures = _fact_failures(
        environment["facts"], required_environment_facts,
        "environment",
    )
    environment_failures.extend(_observation_failures(
        environment["observation"], environment["compositionKey"]
    ))
    environment_failures.extend(_state_binding_failures(
        environment["observation"], environment, request["routes"], policy
    ))
    assessments: list[dict[str, Any]] = []
    route_by_id = {route["id"]: route for route in request["routes"]}
    for route in request["routes"]:
        failures = [dict(item) for item in environment_failures]
        missing = [
            responsibility for responsibility in outcome["responsibilities"]
            if responsibility not in route["supplies"]
        ]
        failures.extend({
            "code": f"responsibility:{responsibility}",
            "state": "not-observed",
            "detail": f"responsibility {responsibility} is not supplied",
        } for responsibility in missing)
        failures.extend(_fact_failures(
            route["facts"], required_route_facts, "route"
        ))
        if len(route["forms"]) > 1:
            failures.extend(_fact_failures(
                route["coherence"], required_coherence_facts,
                "coherence",
            ))
        assessments.append({
            "routeId": route["id"],
            "sourceKind": route["sourceKind"],
            "forms": list(route["forms"]),
            "responsibilityModes": dict(route["responsibilityModes"]),
            "admitted": not failures,
            "failures": failures,
            "lifecycle": {
                dimension: route["lifecycle"][dimension]
                for dimension in policy["comparisonDimensions"]
            },
        })

    selected_id, frontier_ids, disposition = _select(assessments, policy)
    selected = route_by_id.get(selected_id)
    last_safe = environment["lastSafeAllocation"]
    invalidated = any(
        item["code"] == "environment:observation-invalidated"
        for item in environment_failures
    )
    unsafe_failures = [
        item for item in environment_failures
        if item["code"] != "environment:observation-invalidated"
        and not item["code"].startswith("environment:state-binding-")
    ]
    preserved_allocation = (
        {
            "routeId": last_safe["routeId"],
            "responsibilityModes": dict(last_safe["responsibilityModes"]),
            "observationId": last_safe["observationId"],
            "observationGeneration": last_safe["observationGeneration"],
            "evidenceBinding": dict(last_safe["evidence"]),
        }
        if selected_id is None and invalidated and not unsafe_failures
        and last_safe is not None else None
    )
    effective_route_facts = dict(selected["facts"]) if selected else {}
    admitted_ids = {
        item["routeId"] for item in assessments if item["admitted"]
    }
    facts: dict[str, dict[str, Any]] = {}
    event_results: list[dict[str, Any]] = []
    experiment_results: list[dict[str, Any]] = []
    retirement_results: list[dict[str, Any]] = []
    residual_resources: list[str] | None = None
    retired_allocations: list[dict[str, Any]] = []
    selected_allocation_retired = False

    for index, event in enumerate(request["events"]):
        kind = event["kind"]
        result: dict[str, Any] = {"index": index, "kind": kind}
        if kind == "experiment-evaluated":
            decision, reasons = _experiment_decision(
                event, policy, admitted_ids, selected_id
            )
            experiment = {
                "baselineRouteId": event["baselineRouteId"],
                "candidateRouteId": event["candidateRouteId"],
                "decision": decision,
                "reasons": reasons,
                "evidenceBinding": dict(event["evidence"]),
                "poststate": None,
            }
            experiment_results.append(experiment)
            result.update({"accepted": True, "decision": decision})
        elif kind == "experiment-poststate":
            experiment = next((
                item for item in reversed(experiment_results)
                if item["baselineRouteId"] == event["baselineRouteId"]
                and item["candidateRouteId"] == event["candidateRouteId"]
            ), None)
            expected = {
                "discard-and-rollback": "rollback-complete",
                "keep-after-independent-poststate": "keep-complete",
            }.get(experiment["decision"] if experiment else None)
            accepted = (
                expected is not None
                and event["disposition"] == expected
                and event["state"] == "observed"
                and event["independent"] == "observed"
                and event["evidence"]["observerRef"]
                == experiment["evidenceBinding"]["observerRef"]
                and event["evidence"]["boundaryRef"]
                == experiment["evidenceBinding"]["boundaryRef"]
            )
            poststate = {
                "disposition": event["disposition"],
                "state": event["state"],
                "independent": event["independent"],
                "eventIndex": index,
                "accepted": accepted,
            }
            if experiment is not None:
                experiment["poststate"] = poststate
            result.update({
                "accepted": accepted,
                "reason": None if accepted else (
                    "poststate does not close a preceding experiment decision"
                ),
            })
        elif kind == "responsibility-allocation-retired":
            route_id = event["routeId"]
            replacement_id = event["replacementRouteId"]
            reasons: list[str] = []
            if route_id == selected_id:
                reasons.append("the selected route cannot retire itself")
            if replacement_id != selected_id:
                reasons.append("replacement is not the selected route")
            if replacement_id not in admitted_ids:
                reasons.append("replacement route is not admitted")
            for fact_id in ("consequence", "cleanup-poststate"):
                observation = facts.get(fact_id, {
                    "state": "unknown", "independent": "unknown"
                })
                if observation["state"] != "observed" \
                        or observation["independent"] != "observed":
                    reasons.append(
                        f"replacement {fact_id} is not independently observed"
                    )
            retirement_facts = _ordered_union(
                COMPLIANCE_RETIREMENT_FACTS,
                policy.get("requiredRetirementFacts", []),
            )
            reasons.extend(item["detail"] for item in _fact_failures(
                event["preconditions"], retirement_facts, "retirement"
            ))
            if event["state"] != "observed":
                reasons.append("retirement state is not observed")
            if event["independent"] != "observed":
                reasons.append("retirement post-state is not independent")
            accepted = not reasons
            if accepted:
                retired_allocations.append({
                    "routeId": route_id,
                    "replacementRouteId": replacement_id,
                    "responsibilities": list(event["responsibilities"]),
                    "recheckTriggers": list(event["recheckTriggers"]),
                })
            if route_id == selected_id and event["state"] == "observed":
                selected_allocation_retired = True
            retirement = {
                "routeId": route_id,
                "replacementRouteId": replacement_id,
                "responsibilities": list(event["responsibilities"]),
                "accepted": accepted,
                "disposition": (
                    "retired-with-recheck" if accepted else "hold-unknown"
                ),
                "reasons": reasons,
                "recheckTriggers": list(event["recheckTriggers"]),
                "evidenceBinding": dict(event["evidence"]),
                "replacementEvidenceBinding": dict(
                    event["replacementEvidence"]
                ),
                "eventIndex": index,
            }
            retirement_results.append(retirement)
            result.update({
                "accepted": accepted,
                "disposition": retirement["disposition"],
                "reason": None if accepted else "; ".join(reasons),
            })
        elif event.get("routeId") != selected_id or selected is None:
            result.update({
                "accepted": False,
                "reason": "event is not bound to the selected route",
            })
        elif kind == "fact-observed":
            facts[event["factId"]] = {
                "state": event["state"],
                "independent": event["independent"],
                "eventIndex": index,
            }
            if event["factId"] in required_route_facts:
                effective_route_facts[event["factId"]] = event["state"]
            result.update({"accepted": True, "factId": event["factId"]})
        elif kind == "resource-poststate":
            residual_resources = list(event["residualTaskResources"])
            clean = not residual_resources and event["independent"] == "observed"
            facts["cleanup-poststate"] = {
                "state": "observed" if clean else "not-observed",
                "independent": event["independent"],
                "eventIndex": index,
            }
            result.update({
                "accepted": True,
                "releasedResources": list(event["releasedResources"]),
                "residualTaskResources": residual_resources,
            })
        event_results.append(result)

    required_completion = _ordered_union(
        COMPLIANCE_COMPLETION_FACTS, policy["requiredCompletionFacts"]
    )
    completion_failures: list[dict[str, str]] = []
    if selected is not None:
        completion_failures.extend(_fact_failures(
            effective_route_facts, required_route_facts, "route-poststate"
        ))
    for experiment in experiment_results:
        expected = {
            "discard-and-rollback": "rollback-complete",
            "keep-after-independent-poststate": "keep-complete",
        }.get(experiment["decision"])
        poststate = experiment["poststate"]
        if expected is None or poststate is None or not poststate["accepted"]:
            completion_failures.append({
                "code": (
                    "completion:experiment-poststate:"
                    f"{experiment['candidateRouteId']}"
                ),
                "state": "unknown" if poststate is None else poststate["state"],
                "detail": (
                    "experiment decision lacks its independently observed "
                    "matching lifecycle post-state"
                ),
            })
    for fact_id in required_completion:
        observation = facts.get(fact_id, {
            "state": "unknown", "independent": "unknown"
        })
        if observation["state"] != "observed":
            completion_failures.append({
                "code": f"completion:{fact_id}",
                "state": observation["state"],
                "detail": f"completion fact {fact_id} is not observed",
            })
        elif fact_id in COMPLIANCE_COMPLETION_FACTS and (
            observation["independent"] != "observed"
        ):
            completion_failures.append({
                "code": f"completion:{fact_id}:independence",
                "state": observation["independent"],
                "detail": f"completion fact {fact_id} is not independently observed",
            })
    if residual_resources:
        completion_failures.append({
            "code": "completion:task-residue",
            "state": "not-observed",
            "detail": "task-owned residual resources remain",
        })
    accepted_retirements = [
        item for item in retirement_results if item["accepted"]
    ]
    for allocation in policy.get("requiredRetirementAllocations", []):
        route_id = allocation["routeId"]
        responsibilities = allocation["responsibilities"]
        if not any(
            item["routeId"] == route_id
            and set(item["responsibilities"]) == set(responsibilities)
            for item in accepted_retirements
        ):
            scope = "+".join(responsibilities)
            completion_failures.append({
                "code": f"completion:retirement:{route_id}:{scope}",
                "state": "unknown",
                "detail": (
                    f"required allocation {route_id}:{scope} lacks an "
                    "independently observed reversible retirement bound to "
                    "the selected replacement"
                ),
            })
    if selected_allocation_retired:
        completion_failures.append({
            "code": "completion:selected-allocation-retired",
            "state": "not-observed",
            "detail": "a selected-route allocation was retired before closure",
        })
    completion_allowed = selected_id is not None and not completion_failures

    return {
        "schema": DECISION_SCHEMA,
        "valid": True,
        "outcomeId": outcome["id"],
        "compositionKey": environment["compositionKey"],
        "environmentObservation": {
            "id": environment["observation"]["id"],
            "generation": environment["observation"]["generation"],
            "decisionAt": environment["observation"]["decisionAt"],
            "validUntil": environment["observation"]["validUntil"],
            "sourceKinds": sorted({
                item["sourceKind"]
                for item in environment["observation"]["stateBindings"]
            }),
            "stateFieldCount": len(
                environment["observation"]["stateBindings"]
            ),
            "current": not environment_failures,
            "preservedLastSafe": preserved_allocation is not None,
        },
        "policyId": policy["id"],
        "disposition": disposition,
        "selectedRouteId": selected_id,
        "preservedAllocation": preserved_allocation,
        "frontierRouteIds": frontier_ids,
        "assessments": assessments,
        "lifecycle": {
            "facts": facts,
            "effectiveRouteFacts": effective_route_facts,
            "eventResults": event_results,
            "experimentResults": experiment_results,
            "retirementResults": retirement_results,
            "retiredAllocations": retired_allocations,
            "residualTaskResources": residual_resources,
            "selectedAllocationRetired": selected_allocation_retired,
            "completionFailures": completion_failures,
            "completionAllowed": completion_allowed,
        },
        "unknowns": list(environment["unknowns"]),
        "errors": [],
        "claimLimit": (
            "this-exact-outcome-composition-policy-route-set-and-ordered-"
            "observation-sequence-only"
        ),
    }


__all__ = [
    "DECISION_SCHEMA", "FACT_VALUES", "RESPONSIBILITY_MODES", "SCHEMA",
    "STATE_SOURCE_KINDS", "reconcile_closure",
]
