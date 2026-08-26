from datetime import datetime
from hashlib import sha256
import json
import re
from urllib.parse import unquote, urlsplit

from .identity import _exact, _nonempty_string as _text, _safe_https_locator


STATES = {"passed", "failed", "failed-repeated-same-purpose"}
_OFFICIAL_HOSTS = {
    "openai.com", "help.openai.com", "platform.openai.com",
    "developers.openai.com", "github.com", "code.claude.com",
    "learn.chatgpt.com",
}
_PROJECTION_FIELDS = ("adapterId", "skill", "skillSha256")
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
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (AttributeError, ValueError):
        return None
    return parsed if parsed.tzinfo is not None else None


def _digest(value):
    return sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
        separators=(",", ":")).encode()).hexdigest()


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


def _postcapture_binding(binding, payload, captured_at):
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
    if binding.get("kind") != "direct-independent-agent-result":
        return False
    nonces = binding.get("phaseNonces")
    results = payload.get("independentAgentResults") if isinstance(payload, dict) else None
    completed_at = _time(binding.get("completedAt"))
    agent_task = binding.get("agentTask")
    return (
        _exact(
            binding,
            ("kind", "carrierSessionId", "agentTask", "resultLocator", "phaseNonces",
             "resultSha256", "completedAt", "claim"),
            ("carrierSessionId", "agentTask", "resultLocator",
             "resultSha256", "completedAt", "claim"),
        )
        and _text(agent_task)
        and re.fullmatch(
            r"[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}",
            binding["carrierSessionId"],
        ) is not None
        and binding["resultLocator"] == f"codex-collaboration-agent:{agent_task}"
        and completed_at is not None and captured_at is not None
        and completed_at <= captured_at
        and isinstance(nonces, list) and nonces
        and all(_text(value) for value in nonces)
        and len(nonces) == len(set(nonces))
        and _records(results) and results
        and all(
            _exact(result, ("kind", "agentTask", "phase", "nonce", "report"),
                   ("agentTask", "phase", "nonce", "report"))
            and result["kind"] == "independent-agent-result"
            and result["agentTask"] == binding["agentTask"]
            and _text(result["phase"]) and _text(result["nonce"])
            and _text(result["report"])
            for result in results
        )
        and [result["nonce"] for result in results] == nonces
        and binding.get("resultSha256") == _digest(results)
    )


def _postcapture_binding_key(binding):
    if binding.get("kind") == "observer-session-event":
        return binding["kind"], binding.get("sessionId"), binding.get("eventLocator")
    return (binding.get("kind"), binding.get("carrierSessionId"),
            binding.get("resultLocator"), binding.get("resultSha256"))


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
            or not all(_postcapture_binding(binding, payload, captured_at)
                       for binding in bindings)
            or len({_postcapture_binding_key(binding) for binding in bindings}) != count
        ):
            return None
        selected.append({"location": location, "event": event})
    locators = [_postcapture_binding_key(binding)
                for item in selected for binding in item["event"]["sourceBindings"]]
    return ({"contract": contract, "events": selected} if len(special) == len(selected)
            and len(locators) == len(set(locators)) else None)


def _publishable_payload(payload, task, cleanup, captured_at, projection):
    if not isinstance(payload, dict):
        return False
    messages, sources, evidence, exposure = (
        payload.get("messages"), payload.get("officialSources"),
        payload.get("cleanupEvidence"), payload.get("projectionExposure")
    )
    triggers = payload.get("recheckTriggers")
    required = task.get("required", [])
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
        and _exact(exposure, ("kind", *_PROJECTION_FIELDS), _PROJECTION_FIELDS)
        and _text(exposure.get("kind"))
        and exposure["kind"] in {
            "exact-skill-content-read", "host-runtime-attribution"
        }
        and isinstance(projection, dict)
        and all(exposure[field] == projection.get(field)
                for field in _PROJECTION_FIELDS)
        and _records(sources)
        and all(_official_source(item, captured_at) for item in sources)
        and len({_canonical_official_url(item["url"]) for item in sources}) == len(sources)
        and ("resolve-current-official-guidance" not in required or len(sources) >= 2)
        and isinstance(evidence, dict) and set(evidence) == {"state", "observations"}
        and evidence["state"] == (cleanup or {}).get("state")
        and _records(evidence["observations"]) and evidence["observations"]
        and _records(payload.get("redactions")) and _text(payload.get("evidenceBoundary"))
        and ("surface-only-the-exact-human-decision" not in required or any(
            item["phase"] == "human-grant" and item["role"] == "user"
            for item in messages
        ))
    )


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
        binding_contract = task.get("postSessionBindingContract")
        source_fields = ("kind", "locator", "recordId", "sha256", "claim") + (
            ("postSessionBindingsSha256",) if binding_contract else ()
        )
        postcapture = _postcapture_bundle(
            record.get("payload", {}), task, captured
        ) if isinstance(record, dict) else None
        valid = (
            _exact(source, source_fields,
                   ("locator", "recordId", "claim"))
            and _text(source.get("kind"))
            and source["kind"] in {"host-transcript", "host-event-log"}
            and _exact(bundle, ("schema", "records")) and bundle.get("schema") == 1
            and _exact(record, (
                "kind", "taskId", "goldenTaskSha256", "evaluationContractSha256",
                "hostIdentity", "capturedAt", "payload",
            ))
            and record.get("kind") == source.get("kind")
            and record.get("taskId") == task.get("id")
            and record.get("goldenTaskSha256") == task_digest
            and record.get("evaluationContractSha256") == evaluation_digest
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
        if task.get("postSessionBindingContract") != binding_contracts.get(task_id):
            errors.append(
                f"{label} post-session binding contract does not match representative policy"
            )
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
            exclusions.extend(
                f"{task_id}:{value}" for value in claim.get("excludedClaims", [])
                if _text(value)
            )
    declared = acceptance.get("claimCeiling", {}).get("retainedBehaviorExclusions")
    if require_complete and declared != sorted(set(exclusions)):
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
        if task.get("postSessionBindingContract") != binding_contracts.get(task_id):
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
