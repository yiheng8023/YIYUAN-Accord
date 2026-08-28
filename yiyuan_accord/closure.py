"""Pure, no-I/O closure decision core with one plain-data interface.

Human authority, compliance and independent consequence/cleanup evidence are
stable invariants. Task policy supplies every other condition, dimension,
preference and open-ended route form.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from math import isfinite
from numbers import Real
from typing import Any


SCHEMA = "yiyuan-accord-closure/v1"
DECISION_SCHEMA = "yiyuan-accord-closure-decision/v1"
FACT_VALUES = frozenset({"observed", "not-observed", "unknown"})
COMPARISON_VALUES = frozenset({"better", "equal", "worse", "unknown"})
EXPERIMENT_POSTSTATE_VALUES = frozenset({
    "keep-complete", "rollback-complete",
})
EVIDENCE_BINDING_FIELDS = frozenset({
    "sourceRef", "observerRef", "subjectRef", "boundaryRef",
})

# These are compliance/evidence invariants, not a product-form or workflow list.
COMPLIANCE_ROUTE_FACTS = (
    "within-human-authority",
    "compliant",
    "independent-consequence-verifier",
)
COMPLIANCE_COMPLETION_FACTS = ("consequence", "cleanup-poststate")
COMPLIANCE_EXPERIMENT_FACTS = (
    "immutable-evaluator",
    "available-rollback",
    "independent-effect-and-cleanup-poststate",
)
COMPLIANCE_EXPERIMENT_DIMENSIONS = ("authority", "evidence")


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
    coherence_required = coherence_required \
        if _string_list(coherence_required) else []
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
        elif kind == "route-retired":
            if not _identifier(event.get("routeId")) \
                    or event.get("routeId") not in valid_route_ids:
                errors.append(f"{label}.routeId is unknown")
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
    environment_failures = _fact_failures(
        environment["facts"], policy["requiredEnvironmentFacts"],
        "environment",
    )
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
                route["coherence"], policy["requiredCoherenceFacts"],
                "coherence",
            ))
        assessments.append({
            "routeId": route["id"],
            "sourceKind": route["sourceKind"],
            "forms": list(route["forms"]),
            "admitted": not failures,
            "failures": failures,
            "lifecycle": {
                dimension: route["lifecycle"][dimension]
                for dimension in policy["comparisonDimensions"]
            },
        })

    selected_id, frontier_ids, disposition = _select(assessments, policy)
    selected = route_by_id.get(selected_id)
    effective_route_facts = dict(selected["facts"]) if selected else {}
    admitted_ids = {
        item["routeId"] for item in assessments if item["admitted"]
    }
    facts: dict[str, dict[str, Any]] = {}
    event_results: list[dict[str, Any]] = []
    experiment_results: list[dict[str, Any]] = []
    residual_resources: list[str] | None = None
    retired = False

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
        elif kind == "route-retired":
            retired = event["state"] == "observed"
            result.update({"accepted": True, "retired": retired})
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
    if retired:
        completion_failures.append({
            "code": "completion:selected-route-retired",
            "state": "not-observed",
            "detail": "the selected route was retired before closure",
        })
    completion_allowed = selected_id is not None and not completion_failures

    return {
        "schema": DECISION_SCHEMA,
        "valid": True,
        "outcomeId": outcome["id"],
        "compositionKey": environment["compositionKey"],
        "policyId": policy["id"],
        "disposition": disposition,
        "selectedRouteId": selected_id,
        "frontierRouteIds": frontier_ids,
        "assessments": assessments,
        "lifecycle": {
            "facts": facts,
            "effectiveRouteFacts": effective_route_facts,
            "eventResults": event_results,
            "experimentResults": experiment_results,
            "residualTaskResources": residual_resources,
            "selectedRouteRetired": retired,
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


__all__ = ["DECISION_SCHEMA", "FACT_VALUES", "SCHEMA", "reconcile_closure"]
