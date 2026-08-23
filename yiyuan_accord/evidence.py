from datetime import datetime
from hashlib import sha256
import json
import re

from .identity import _exact, _nonempty_string as _text


STATES = {
    "passed", "failed", "failed-repeated-same-purpose",
}


def _records(value):
    return isinstance(value, list) and all(
        isinstance(item, dict) and _text(item.get("kind")) for item in value
    )


def _time(value):
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (AttributeError, ValueError):
        return None
    return parsed if parsed.tzinfo is not None else None


def _digest(value):
    return sha256(json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode()).hexdigest()
def representative_contract_sha256(acceptance, golden):
    semantic_fields = (
        "id", "class", "name", "mapsTo", "statement", "passRule",
        "requiredEvidenceClasses",
    )
    criteria = acceptance.get("criteria")
    return _digest({
        "productId": acceptance.get("productId"),
        "release": acceptance.get("release"),
        "evidenceLanes": acceptance.get("evidenceLanes"),
        "representativeBehaviorPolicy": acceptance.get("representativeBehaviorPolicy"),
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
    })


def _observation_errors(
    root, label, observation, task, burden_metrics, observation_locator,
    projection_id, evaluation_digest, read_json,
):
    errors = []
    observed_at = _time(observation.get("observedAt"))
    observer, host = observation.get("observer"), observation.get("hostIdentity")
    if observed_at is None or observed_at > datetime.now().astimezone():
        errors.append(f"{label} observedAt is invalid")
    if not _exact(observer, ("kind", "identity"), ("identity",)) or observer.get(
        "kind"
    ) not in {"human-observer", "host-event-recorder"}:
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
    if observation.get("evaluationContractSha256") != evaluation_digest:
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
        valid = (
            _exact(source, ("kind", "locator", "recordId", "sha256", "claim"),
                   ("locator", "recordId", "claim"))
            and source.get("kind") in {"host-transcript", "host-event-log"}
            and _exact(bundle, ("schema", "records")) and bundle.get("schema") == 1
            and _exact(record, (
                "kind", "taskId", "goldenTaskSha256", "evaluationContractSha256",
                "hostIdentity", "capturedAt", "payload",
            ), ("payload",))
            and record.get("kind") == source.get("kind")
            and record.get("taskId") == task.get("id")
            and record.get("goldenTaskSha256") == task_digest
            and record.get("evaluationContractSha256") == evaluation_digest
            and record.get("hostIdentity") == host
            and captured is not None and observed_at is not None and captured <= observed_at
            and source.get("sha256") == _digest(record)
        )
        if not valid:
            errors.append(f"{label} sourceEvidence[{index}] is invalid")

    behaviors = observation.get("behaviorDecisions")
    required = behaviors.get("required") if isinstance(behaviors, dict) else None
    prohibited = behaviors.get("prohibited") if isinstance(behaviors, dict) else None
    behavior_valid = (
        isinstance(behaviors, dict) and set(behaviors) == {"required", "prohibited"}
        and isinstance(required, dict) and set(required) == set(task.get("required", []))
        and set(required.values()) <= {"observed", "not-observed"}
        and isinstance(prohibited, dict) and set(prohibited) == set(task.get("prohibited", []))
        and set(prohibited.values()) <= {"absent", "observed"}
    )
    if not behavior_valid:
        errors.append(f"{label} behaviorDecisions are incomplete")
    failures = [] if not behavior_valid else [
        *(f"required:{key}" for key, value in required.items() if value == "not-observed"),
        *(f"prohibited:{key}" for key, value in prohibited.items() if value == "observed"),
    ]
    burden = observation.get("humanBurden")
    if (
        not isinstance(burden, dict) or set(burden) != set(burden_metrics)
        or any(not isinstance(value, int) or isinstance(value, bool) or value < 0 for value in burden.values())
    ):
        errors.append(f"{label} humanBurden is invalid")
    cleanup = observation.get("cleanup")
    cleanup_valid = (
        _exact(cleanup, ("state", "taskOwnedResidueCount", "verified"))
        and cleanup.get("state") in {"verified-clean", "verified-foreign-state-preserved", "failed-residue"}
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
    if (
        not isinstance(decisions, dict) or set(decisions) != mapped
        or set(decisions.values()) != {expected_decision}
    ):
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
    state = decision.get("state") if isinstance(decision, dict) else None
    if state not in STATES:
        errors.append(f"{label} has invalid decision")
    elif state == "passed" and (failures or not clean):
        errors.append(f"{label} passed decision contradicts records")
    elif state in {"failed", "failed-repeated-same-purpose"} and not failures:
        errors.append(f"{label} failure lacks counterevidence")
    return errors, state


def representative_sample_errors(
    root, acceptance, required_task_ids, golden, read_json,
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
        and item.get("assessment") == "verified"
        and "representative-behavior" in item.get("requiredEvidenceClasses", [])
    ]
    if not users:
        return []
    if representative.get("assessment") != "verified":
        return ["verified representative evidence requires a verified R3 sample"]
    protocol = golden.get("evaluationProtocol")
    fields = protocol.get("requiredObservationFields", []) if isinstance(protocol, dict) else []
    tasks = {
        item.get("id"): item for item in golden.get("tasks", [])
        if isinstance(item, dict) and _text(item.get("id"))
    }
    burden = golden.get("metrics", {}).get("humanBurden", [])
    evaluation = representative_contract_sha256(acceptance, golden)
    errors, observed, states, r3_locators, exclusions = [], {}, {}, {}, []
    exact_fields = set(fields) | {"evidenceClass"}
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
        local, state = _observation_errors(
            root, label, observation, task, burden, item["locator"],
            projection if _text(projection) else "", evaluation, read_json,
        )
        errors.extend(local)
        states[task_id] = state
        claim = observation.get("claimLimit")
        if state in {"failed", "failed-repeated-same-purpose"} and isinstance(claim, dict):
            exclusions.extend(
                f"{task_id}:{value}" for value in claim.get("excludedClaims", [])
                if _text(value)
            )
    required = set(required_task_ids)
    missing = sorted(required - set(observed))
    duplicates = sorted(task for task in required if observed.get(task, 0) > 1)
    if missing:
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
    if failed_must_pass:
        errors.append(f"must-pass tasks failed: {failed_must_pass}")
    declared = acceptance.get("claimCeiling", {}).get("retainedBehaviorExclusions")
    if declared != sorted(exclusions):
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
        if len(actual) != len(set(actual)) or set(actual) != expected:
            errors.append(
                f"{criterion_id} representative coverage mismatch"
            )
    return errors
