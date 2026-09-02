from datetime import datetime
from hashlib import sha256
import json
import re
import subprocess
from urllib.parse import unquote, urlsplit

from .closure import (
    RESPONSIBILITY_MODES,
    SCHEMA as CLOSURE_SCHEMA,
    reconcile_closure,
)
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
PROVISIONAL_GT20_21_SOURCE = (
    "evals/evidence/2026-08-30-v310-gt20-21-source.json"
)
_PROVISIONAL_GT20_21_EVALUATION_SHA256 = (
    "312693dc71c52c44fe6a11b564671c95818466f1d8ddfd263763dab2af055ab5"
)
_PROVISIONAL_GT20_21_CONTRACT_SHA256 = {
    "GT-20": "ad7c1438037bd4253d68c3ebad07499ed2abeba29ad67c1fd49e68a8cdd6db9d",
    "GT-21": "0cb08c560e250ddc6b06827704ac4d7dc90815f6be37e6487e13cb8b223824d3",
}
_PROVISIONAL_GT20_21_RETAINED_RECORDS = (
    ("GT-21-live-carrier-preflight-working-tree",
     "19bfd829179fc57f3e45afc8fd17d9360c786006053f50ea9d772a783d16d597"),
    ("GT-21-isolated-live-carrier-2f6e3de",
     "e49eb8442e45f4b2fc520e617a787e6254cc3def87bdeb591ac2279d2c28bd7f"),
    ("GT-21-simple-native-route-f5f281c",
     "2d92c0dbee3d5816679b4cc479c382d3b199570ce1f468163911c4acb8f3cd37"),
    ("GT-21-simple-native-route-model-variable-6d91360",
     "a27837ca5d08b9d88e11ccf3bc023cb86380a236f0318714104662b906ca0e83"),
    ("GT-21-claude-simple-auth-boundary-7a4c932",
     "0e61fe32697c383a301e6701560b2cb8a47f4d5317d48e12de51e14a83168e13"),
    ("GT-21-claude-current-account-pre-model-boundary-5473c43",
     "7799873a3516ca386feaf6f9380f6deca2b875557e40f4e28a272ba41ba26fd2"),
    ("GT-21-codex-current-account-simple-consequence-fded9a6",
     "0ddb105e819e3c4d1dcb4d6ae91766d783196d3e210e6585e41ca68408e8707e"),
    ("GT-21-fresh-zero-history-handoff-3878968",
     "cb14e25128123afcfb6354fefcb480d18b171d7539af0a78dc905f61df33b5cc"),
    ("GT-20-transactional-lifecycle-4c8bcc3",
     "a66b9aa05610baf362c38213d266d31a005c737ab1699173a590a25542cd32ec"),
)
_PROVISIONAL_GT20_21_LIFECYCLE_SCHEMA = (
    "yiyuan-accord-provisional-evidence-lifecycle/v2"
)
_FROZEN_GT20_21_PROMOTION_SCHEMA = "frozen-r3-promotion/v1"
_FROZEN_GT20_21_SOURCE_BOUND_REVISION = (
    "ef10100649c95ee0bb359a45ab3097a14884cf97"
)
_FROZEN_GT20_21_CURRENT_CONTRACT_REVISION = (
    "cf1d8c9e57741ed5c353bb630ca8dded7bd225b9"
)
_GT16_RETAINED_FAILURE_REVISION = (
    "cf1d8c9e57741ed5c353bb630ca8dded7bd225b9"
)
_FROZEN_GT20_21_BASE_SOURCE_SHA256 = (
    "044cf9ba000da7819c7a64c15d8c08da2f3e973596e761a7ae0182f58af45256"
)
_FROZEN_GT20_21_PROMOTION_SHA256 = (
    "7da9ddc93d4a8df0e66c85e2d427193f8acd9ae058bdcc4d6f5cfee1f84d0163"
)
FROZEN_GT20_21_OBSERVATIONS = {
    "GT-20": (
        "evals/observations/cf1d8c9-gt20-frozen-r3-promotion.json",
        "fca5f8a311dd3aa90596094722fd712de9fc8dee427684151b928518ffcb9ee6",
        ("GT-20-transactional-lifecycle-4c8bcc3",),
    ),
    "GT-21": (
        "evals/observations/cf1d8c9-gt21-frozen-r3-promotion.json",
        "f4d23755b359f65fc20f5b7bb03eea37fa0c5279637ce0b066eddd60951e0ba6",
        (
            "GT-21-isolated-live-carrier-2f6e3de",
            "GT-21-codex-current-account-simple-consequence-fded9a6",
            "GT-21-fresh-zero-history-handoff-3878968",
        ),
    ),
}
FROZEN_GT20_21_REPRESENTATIVE_LANES = {
    locator: {
        "taskId": task_id,
        "sourceClass": "frozen-source-metadata-promotion",
        "targetClass": "representative-behavior",
    }
    for task_id, (locator, _, _) in FROZEN_GT20_21_OBSERVATIONS.items()
}


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


def _continuity_handoff_bundle(payload, task, narrative_hashes=None):
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
            and set(facts) == set(expected) | {
                "kind", "sourceNarrativeRevision", "sourceNarrativeSha256",
            }
            and facts.get("kind") == kind
            and isinstance(narrative_hashes, dict)
            and facts["sourceNarrativeRevision"] == narrative_hashes.get("revision")
            and facts["sourceNarrativeSha256"] == narrative_hashes.get(
                result["taskLocator"].rsplit("/", 1)[-1]
            )
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


def _continuity_narrative_hashes(root, locator, record_id, payload, task):
    if task.get("kind") != "continuity":
        return {}
    results = payload.get("independentCommandResults") \
        if isinstance(payload, dict) else None
    phases = ("destination-poststate", "source-reconciliation")
    current = {
        item["taskLocator"].rsplit("/", 1)[-1]: item
        for item in results or []
        if isinstance(item, dict) and _text(item.get("taskLocator"))
    }
    typed = [current.get(phase) for phase in phases]
    if any(not isinstance(item, dict) or not isinstance(item.get("facts"), dict)
           for item in typed):
        return None
    revisions = {item["facts"].get("sourceNarrativeRevision") for item in typed}
    if (len(revisions) != 1
            or re.fullmatch(r"[0-9a-f]{40}", next(iter(revisions), "")) is None):
        return None
    revision = next(iter(revisions))
    try:
        _bounded_git_bytes(
            root, ["merge-base", "--is-ancestor", revision, "HEAD"], 1,
        )
        historical = _strict_json_object(_bounded_git_bytes(
            root, ["show", "--end-of-options", f"{revision}:{locator}"],
            1_048_576,
        ))
    except (OSError, subprocess.SubprocessError, UnicodeError, ValueError):
        return None
    records = historical.get("records") if isinstance(historical, dict) else None
    record = records.get(record_id) if isinstance(records, dict) else None
    old_results = record.get("payload", {}).get("independentCommandResults") \
        if isinstance(record, dict) else None
    old = {
        item["taskLocator"].rsplit("/", 1)[-1]: item
        for item in old_results or []
        if isinstance(item, dict) and _text(item.get("taskLocator"))
    }
    identity = ("kind", "carrierSessionId", "taskLocator", "phase", "nonce")
    if any(
        not isinstance(old.get(phase), dict)
        or "facts" in old[phase] or not _text(old[phase].get("report"))
        or any(old[phase].get(field) != current[phase].get(field)
               for field in identity)
        for phase in phases
    ):
        return None
    return {"revision": revision, **{
        phase: sha256(old[phase]["report"].encode("utf-8")).hexdigest()
        for phase in phases
    }}


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


def _hold_unknown_episode_decision(episode):
    decision = episode.get("coreDecision") if isinstance(episode, dict) else None
    lifecycle = decision.get("lifecycle") if isinstance(decision, dict) else None
    observation = decision.get("environmentObservation") \
        if isinstance(decision, dict) else None
    return (
        isinstance(decision, dict)
        and decision.get("valid") is True
        and decision.get("errors") == []
        and decision.get("selectedRouteId") is None
        and decision.get("frontierRouteIds") == []
        and decision.get("disposition") == "hold-unknown"
        and isinstance(observation, dict)
        and observation.get("current") is False
        and isinstance(lifecycle, dict)
        and lifecycle.get("completionAllowed") is False
        and isinstance(lifecycle.get("completionFailures"), list)
        and lifecycle["completionFailures"]
        and lifecycle.get("residualTaskResources") is None
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
    regression_terms = set(regression_rule.partition("-weakens-")[2].split("-"))
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
        request.get("schema") != CLOSURE_SCHEMA
        or not isinstance(routes, list) or not routes
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
    expected_selected = baseline_route if order in {0, 3} else replacement_route
    successful_events = [
        event for event in events if isinstance(event, dict)
        and event.get("routeId") == expected_selected
    ]
    observed_facts = {
        event.get("factId") for event in successful_events
        if event.get("kind") == "fact-observed"
        and event.get("state") == "observed"
        and event.get("independent") == "observed"
    }
    clean_poststates = [
        event for event in successful_events
        if event.get("kind") == "resource-poststate"
        and event.get("residualTaskResources") == []
        and event.get("independent") == "observed"
    ]
    event_only = [
        event for event in events if isinstance(event, dict)
        and event.get("kind") == "fact-observed"
        and event.get("factId") in {"hook-fired", "context-injection"}
        and event.get("state") == "observed"
    ]
    forbidden_event_only_consequences = [
        event for event in events if isinstance(event, dict)
        and (
            event.get("kind") == "resource-poststate"
            or event.get("kind") == "responsibility-allocation-retired"
            or event.get("kind") == "fact-observed"
            and event.get("factId") in {"execution", "consequence"}
        )
    ]
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
        and (
            bool(event_only) and not forbidden_event_only_consequences
            if order == 1 else
            {"execution", "consequence"} <= observed_facts
            and len(clean_poststates) == 1
        )
    )


def _gt19_route_modes(routes):
    if not isinstance(routes, list):
        return None
    observed_modes = set()
    mixed = False
    for route in routes:
        supplies = _string_set(route.get("supplies")) \
            if isinstance(route, dict) else None
        modes = route.get("responsibilityModes") \
            if isinstance(route, dict) else None
        if (
            supplies is None or not isinstance(modes, dict)
            or set(modes) != supplies
            or any(mode not in RESPONSIBILITY_MODES for mode in modes.values())
        ):
            return None
        values = set(modes.values())
        observed_modes.update(values)
        mixed = mixed or len(values) > 1
    return observed_modes, mixed


def _gt19_observation_semantics(episodes, decisions):
    receipts = [
        episode.get("closureRequest", {}).get("environment", {}).get("observation")
        for episode in episodes
    ]
    environments = [
        episode.get("closureRequest", {}).get("environment")
        for episode in episodes
    ]
    if any(not isinstance(item, dict) for item in receipts + environments):
        return False
    ids = [item.get("id") for item in receipts]
    compositions = [item.get("compositionKey") for item in receipts]
    generations = [item.get("generation") for item in receipts]
    decision_observations = [
        decision.get("environmentObservation")
        if isinstance(decision, dict) else None
        for decision in decisions
    ]
    freshness = (
        "current", "invalidated-event-only",
        "current-resensed", "current-recomputed",
    )
    expected_state_views = []
    for receipt, current_freshness in zip(receipts, freshness):
        bindings = receipt.get("stateBindings") if isinstance(receipt, dict) else None
        expected_state_views.append({
            binding["field"]: {
                key: binding[key] for key in (
                    "targetKind", "subjectRef", "factId", "value", "writer",
                    "readers", "sourceKind", "sourceRef",
                    "unavailableSources", "generation",
                )
            } | {"freshness": current_freshness}
            for binding in bindings or [] if isinstance(binding, dict)
        })
    return (
        all(isinstance(item.get("stateBindings"), list)
            and item["stateBindings"] for item in receipts)
        and receipts[1].get("stateBindings") == receipts[0].get("stateBindings")
        and ids[0] == ids[1] and ids[2] not in ids[:2]
        and ids[3] not in ids[:3]
        and compositions[0] == compositions[1]
        and compositions[2] not in compositions[:2]
        and compositions[3] not in compositions[:3]
        and all(
            environment.get("compositionKey") == receipt.get("compositionKey")
            for environment, receipt in zip(environments, receipts)
        )
        and isinstance(generations[0], int)
        and not isinstance(generations[0], bool)
        and generations == [generations[0], generations[0],
                            generations[0] + 1, generations[0] + 2]
        and receipts[0].get("invalidatedBy") == []
        and "user-intervention" in receipts[1].get("invalidatedBy", [])
        and receipts[2].get("invalidatedBy") == []
        and receipts[3].get("invalidatedBy") == []
        and all(
            isinstance(observation, dict)
            and observation.get("id") == receipt.get("id")
            and observation.get("generation") == receipt.get("generation")
            and observation.get("current") is current
            for observation, receipt, current in zip(
                decision_observations, receipts, (True, False, True, True)
            )
        )
        and all(
            episode.get("sparseViews", {}).get("S") == expected
            for episode, expected in zip(episodes, expected_state_views)
        )
    )


def _gt19_stage_semantics(episodes):
    decisions = [episode.get("coreDecision") for episode in episodes]
    invalidated = decisions[1]
    invalidated_lifecycle = invalidated.get("lifecycle") \
        if isinstance(invalidated, dict) else None
    invalidated_results = invalidated_lifecycle.get("eventResults") \
        if isinstance(invalidated_lifecycle, dict) else None
    invalidated_environment = invalidated.get("environmentObservation") \
        if isinstance(invalidated, dict) else None
    preserved = invalidated.get("preservedAllocation") \
        if isinstance(invalidated, dict) else None
    baseline = decisions[0].get("selectedRouteId") \
        if isinstance(decisions[0], dict) else None
    successful = []
    for order in (0, 2, 3):
        decision = decisions[order]
        lifecycle = decision.get("lifecycle") if isinstance(decision, dict) else None
        facts = lifecycle.get("facts") if isinstance(lifecycle, dict) else None
        event_results = lifecycle.get("eventResults") \
            if isinstance(lifecycle, dict) else None
        successful.append(
            _valid_episode_decision(episodes[order])
            and isinstance(facts, dict)
            and all(
                isinstance(facts.get(fact), dict)
                and facts[fact].get("state") == "observed"
                and facts[fact].get("independent") == "observed"
                for fact in ("execution", "consequence", "cleanup-poststate")
            )
            and isinstance(event_results, list)
            and all(result.get("accepted") is True for result in event_results)
        )
    return (
        all(successful)
        and _hold_unknown_episode_decision(episodes[1])
        and isinstance(invalidated_environment, dict)
        and invalidated_environment.get("preservedLastSafe") is True
        and isinstance(preserved, dict)
        and preserved.get("routeId") == baseline
        and isinstance(preserved.get("responsibilityModes"), dict)
        and isinstance(invalidated_results, list) and invalidated_results
        and all(result.get("accepted") is False for result in invalidated_results)
        and all(
            isinstance(result.get("reason"), str)
            and "selected route" in result["reason"]
            for result in invalidated_results
        )
    )


def _gt19_carrier_semantics(
    event, episodes, baseline_route, replacement_route,
    responsibilities, outside_scope,
):
    edges = event.get("carrierEdges")
    carrier = event.get("stateCarrier")
    if not isinstance(edges, list) or len(edges) != 3 or not isinstance(carrier, dict):
        return False
    states = [edges[0].get("sourceState")] + [edge.get("targetState") for edge in edges]
    receipts = [
        episode["closureRequest"]["environment"]["observation"]
        for episode in episodes
    ]
    expected_allocations = []
    for order in range(4):
        allocation = {item: baseline_route for item in outside_scope}
        allocation.update({
            item: replacement_route if order == 2 else baseline_route
            for item in responsibilities
        })
        expected_allocations.append(allocation)
    expected_retired = [
        [], [], [f"{baseline_route}/{item}" for item in responsibilities], [],
    ]
    expected_freshness = [
        "current", "invalidated-event-only", "current-resensed",
        "current-recomputed",
    ]
    return (
        all(isinstance(state, dict) for state in states)
        and all(
            state.get("episodeOrder") == order
            and state.get("effectiveAllocations") == expected_allocations[order]
            and state.get("retiredAllocations") == expected_retired[order]
            and state.get("observationId") == receipts[order].get("id")
            and state.get("observationGeneration") == receipts[order].get("generation")
            and state.get("evidenceFreshness") == expected_freshness[order]
            for order, state in enumerate(states)
        )
        and carrier.get("finalEffectiveAllocations") == expected_allocations[3]
        and carrier.get("lastObservationId") == receipts[3].get("id")
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
        or _string_set(responsibilities) is None or not responsibilities
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
    route_sets = [
        {route.get("id") for route in episode.get("closureRequest", {}).get("routes", [])
         if isinstance(route, dict) and _text(route.get("id"))}
        for episode in episodes
    ]
    mode_summaries = [
        _gt19_route_modes(episode.get("closureRequest", {}).get("routes"))
        for episode in episodes
    ]
    baseline_modes = [
        next((route.get("responsibilityModes") for route in episode.get(
            "closureRequest", {}).get("routes", [])
              if isinstance(route, dict) and route.get("id") == baseline_route), None)
        for episode in episodes
    ]
    replacement_modes = [
        next((route.get("responsibilityModes") for route in episode.get(
            "closureRequest", {}).get("routes", [])
              if isinstance(route, dict) and route.get("id") == replacement_route), None)
        for episode in episodes
    ]
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
            and _passing_episode(episode, dimension_ids)
            for order, episode in enumerate(episodes)
        )
        and _gt19_observation_semantics(episodes, decisions)
        and _gt19_stage_semantics(episodes)
        and selected == [baseline_route, None,
                         replacement_route, baseline_route]
        and outside_scope
        and all(route_set == route_sets[0] for route_set in route_sets)
        and all(summary is not None for summary in mode_summaries)
        and set().union(*(summary[0] for summary in mode_summaries))
        == set(RESPONSIBILITY_MODES)
        and any(summary[1] for summary in mode_summaries)
        and all(isinstance(modes, dict) for modes in baseline_modes + replacement_modes)
        and all(
            baseline_modes[order].get(responsibility)
            in {"accord-contained", "accord-agent-composed"}
            and replacement_modes[order].get(responsibility) == "agent-native"
            for order in (1, 2, 3) for responsibility in responsibilities
        )
        and all(
            len(set(baseline_modes[order].values())) > 1
            for order in range(4)
        )
        and all(
            isinstance(episode.get("sparseViews"), dict)
            and isinstance(episode["sparseViews"].get("H"), dict)
            and isinstance(episode["sparseViews"].get("A"), dict)
            and _text(episode["sparseViews"]["H"].get(
                f"{replacement_route}/{responsibilities[0]}"
            ))
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
        and episodes[0]["sparseViews"]["A"].get(
            f"{baseline_route}/{responsibilities[0]}"
        ) == "allocated"
        and episodes[1]["sparseViews"]["A"].get(
            f"{baseline_route}/{responsibilities[0]}"
        ) == "preserved-last-valid"
        and episodes[2]["sparseViews"]["A"].get(
            f"{baseline_route}/{responsibilities[0]}"
        ) == "retired-with-recheck"
        and episodes[2]["sparseViews"]["A"].get(
            f"{replacement_route}/{responsibilities[0]}"
        ) == "allocated"
        and episodes[3]["sparseViews"]["A"].get(
            f"{baseline_route}/{responsibilities[0]}"
        ) == "restored"
        and episodes[3]["sparseViews"]["A"].get(
            f"{replacement_route}/{responsibilities[0]}"
        ) == "unavailable"
        and _gt19_carrier_semantics(
            event, episodes, baseline_route, replacement_route,
            responsibilities, outside_scope,
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


def _embedded_research_source_packet(payload, task, captured_at):
    if not isinstance(payload, dict):
        return False
    events = payload.get("materialEvents")
    bindings = [
        item for item in events or []
        if isinstance(item, dict)
        and item.get("kind") == "current-source-packet-binding"
    ]
    if "sourcePacket" not in payload and not bindings:
        return True
    packet = payload.get("sourcePacket")
    sources = packet.get("sources") if isinstance(packet, dict) else None
    authority = packet.get("authority") if isinstance(packet, dict) else None
    retrieved_at = _time(packet.get("retrievedAt")) \
        if isinstance(packet, dict) else None
    if (
        not _exact(packet, (
            "schema", "taskId", "retrievedAt", "runtimeModelSelection",
            "sources", "authority",
        ), ("schema", "taskId", "retrievedAt", "runtimeModelSelection"))
        or packet.get("schema") != "yiyuan-accord-current-source-packet/v1"
        or packet.get("taskId") != task.get("id")
        or packet.get("runtimeModelSelection") != "host-default-variable"
        or retrieved_at is None or captured_at is None
        or retrieved_at > captured_at
        or not isinstance(sources, dict) or not sources
        or not _exact(authority, (
            "networkReadUsedByEvaluator", "agentUnderEvaluationMayBrowse",
            "installConnectSpendImplementPublish", "credentialOrSessionAccess",
        ))
        or authority != {
            "networkReadUsedByEvaluator": True,
            "agentUnderEvaluationMayBrowse": False,
            "installConnectSpendImplementPublish": False,
            "credentialOrSessionAccess": False,
        }
        or len(bindings) != 1
    ):
        return False
    allowed_roles = {
        "primary-product-source", "maintained-existing-route",
        "official-native-capability-example", "official-primary-source-interface",
        "official-primary-source-interface-with-current-authority-gap",
        "official-maintained-wheel-candidate",
        "maintained-third-party-wheel-candidate", "public-lead-only",
    }
    source_urls = []
    roles = []
    evaluated_revision = payload.get("evaluatedRevision")
    for source in sources.values():
        if not _exact(source, (
            "role", "url", "revision", "license", "maintenance", "facts",
            "counterevidence",
        ), ("role", "url", "revision", "license", "maintenance")):
            return False
        role, url = source["role"], source["url"]
        facts, counterevidence = source["facts"], source["counterevidence"]
        repository_match = re.fullmatch(
            r"repo:(product/reshaping-guidance\.json|yiyuan_accord/closure\.py)@"
            r"([0-9a-f]{40})",
            url,
        )
        if (
            role not in allowed_roles
            or not isinstance(facts, list) or not facts
            or not isinstance(counterevidence, list) or not counterevidence
            or any(not _text(value) for value in (*facts, *counterevidence))
            or len(facts) != len(set(facts))
            or len(counterevidence) != len(set(counterevidence))
            or not (
                _safe_https_locator(url)
                or repository_match is not None
                and repository_match.group(2) == source["revision"]
                == evaluated_revision
            )
            or role == "public-lead-only"
            and (source["license"] != "unknown" or source["maintenance"] != "unknown")
        ):
            return False
        roles.append(role)
        source_urls.append(url)
    if (
        set(roles) != allowed_roles
        or len(source_urls) != len(set(source_urls))
        or sum(role == "public-lead-only" for role in roles) != 1
    ):
        return False
    official_urls = {
        item.get("url") for item in payload.get("officialSources", [])
        if isinstance(item, dict)
    }
    binding = bindings[0]
    return bool(
        official_urls <= set(source_urls)
        and _exact(binding, (
            "kind", "artifact", "artifactSha256", "retrievedAt",
        ), ("artifact", "artifactSha256", "retrievedAt"))
        and binding["artifact"] == "embedded:payload.sourcePacket"
        and binding["artifactSha256"] == _digest(packet)
        and binding["retrievedAt"] == packet["retrievedAt"]
    )


def _embedded_utf8_json(record):
    if not _exact(
        record, ("encoding", "byteLength", "sha256", "text"),
        ("encoding", "sha256", "text"),
    ) or record.get("encoding") != "utf-8":
        return None
    try:
        raw = record["text"].encode("utf-8")
    except UnicodeEncodeError:
        return None
    if (
        not isinstance(record.get("byteLength"), int)
        or isinstance(record.get("byteLength"), bool)
        or record["byteLength"] != len(raw)
        or record["sha256"] != sha256(raw).hexdigest()
    ):
        return None
    try:
        return _strict_json_object(record["text"])
    except (TypeError, ValueError):
        return None


def _gt16_retained_failure_bundle(payload, task, cleanup):
    if (
        task.get("id") != "GT-16"
        or payload.get("evaluatedRevision") != _GT16_RETAINED_FAILURE_REVISION
    ):
        return {}
    events = payload.get("materialEvents")
    by_kind = {
        kind: [event for event in events or []
               if isinstance(event, dict) and event.get("kind") == kind]
        for kind in (
            "model-result-binding", "bounded-bootstrap-result",
            "retained-prior-failed-counterevidence", "independent-poststate",
        )
    }
    if any(len(items) != 1 for items in by_kind.values()):
        return None
    retained = by_kind["retained-prior-failed-counterevidence"][0]
    result_binding = by_kind["model-result-binding"][0]
    bootstrap = by_kind["bounded-bootstrap-result"][0]
    original_record = retained.get("originalResult")
    adjudication_record = retained.get("oracleAdjudication")
    original = _embedded_utf8_json(original_record)
    adjudication = _embedded_utf8_json(adjudication_record)
    if original is None or adjudication is None:
        return None

    expected_failure = {
        "field": "correctedState.effectObserved",
        "observedValue": False,
        "classification": "behavior-failure",
        "correction": (
            "desired-materialized-poststate-must-set-effectObserved-true-"
            "while-receipt-observations-remain-pending"
        ),
    }
    decision = (
        "retain-as-failed-counterevidence-and-run-one-corrected-replay-"
        "in-a-shared-call"
    )
    original_state = original.get("correctedState")
    mismatches = adjudication.get("mismatches")
    behavior_failures = [
        mismatch for mismatch in mismatches or []
        if isinstance(mismatch, dict)
        and mismatch.get("classification") == "behavior-failure"
    ]
    corrected = retained.get("correctedAttempt")
    model_result = payload.get("modelResult")
    model_value = model_result.get("value") \
        if isinstance(model_result, dict) else None
    prior = model_value.get("priorFailureBinding") \
        if isinstance(model_value, dict) else None
    corrected_state = model_value.get("correctedState") \
        if isinstance(model_value, dict) else None
    corrected_sha = model_result.get("sha256") \
        if isinstance(model_result, dict) else None
    value_sha = model_result.get("valueSha256") \
        if isinstance(model_result, dict) else None
    assistant_messages = [
        message for message in payload.get("messages", [])
        if isinstance(message, dict) and message.get("role") == "assistant"
    ]
    try:
        assistant_text = assistant_messages[0]["text"] \
            if len(assistant_messages) == 1 else None
        assistant_value = _strict_json_object(assistant_text)
        assistant_raw = assistant_text.encode("utf-8")
    except (KeyError, TypeError, UnicodeEncodeError, ValueError):
        assistant_value, assistant_raw = None, None

    results = payload.get("independentCommandResults")
    result_by_locator = {
        result.get("taskLocator"): result
        for result in results or [] if isinstance(result, dict)
    }
    expected_locators = {
        "GT-16/effect-poststate", "GT-16/rollback-release-poststate",
        "GT-16/cleanup-poststate",
    }
    if (
        not isinstance(results, list) or len(results) != 3
        or set(result_by_locator) != expected_locators
    ):
        return None
    effect = result_by_locator["GT-16/effect-poststate"].get("facts")
    rollback = result_by_locator[
        "GT-16/rollback-release-poststate"
    ].get("facts")
    cleanup_result = result_by_locator["GT-16/cleanup-poststate"].get("facts")
    effect_observation = effect.get("observation") \
        if isinstance(effect, dict) else None
    rollback_observation = rollback.get("observation") \
        if isinstance(rollback, dict) else None
    cleanup_observation = cleanup_result.get("observation") \
        if isinstance(cleanup_result, dict) else None
    effect_facts = effect_observation.get("facts") \
        if isinstance(effect_observation, dict) else None
    rollback_facts = rollback_observation.get("facts") \
        if isinstance(rollback_observation, dict) else None
    cleanup_facts = cleanup_observation.get("facts") \
        if isinstance(cleanup_observation, dict) else None

    valid = (
        _exact(retained, (
            "kind", "priorBehaviorFailureRetained", "originalResult",
            "oracleAdjudication", "failure", "decision", "correctedAttempt",
        ))
        and retained["priorBehaviorFailureRetained"] is True
        and retained.get("failure") == expected_failure
        and retained.get("decision") == decision
        and isinstance(original_state, dict)
        and original.get("taskId") == "GT-16"
        and original_state.get("effectObserved") is False
        and _exact(adjudication, (
            "schema", "taskId", "resultSha256", "mismatches", "decision",
            "oracleMutationPermitted", "preCallOracleRetained",
        ), ("schema", "taskId", "resultSha256", "decision"))
        and adjudication["schema"]
        == "yiyuan-accord-independent-oracle-adjudication/v1"
        and adjudication["taskId"] == "GT-16"
        and adjudication["resultSha256"] == original_record["sha256"]
        and adjudication["decision"] == decision
        and adjudication["oracleMutationPermitted"] is False
        and adjudication["preCallOracleRetained"] is True
        and isinstance(mismatches, list) and mismatches
        and len(behavior_failures) == 1
        and _exact(behavior_failures[0], (
            "field", "observed", "classification", "reason",
        ), ("field", "classification", "reason"))
        and behavior_failures[0]["field"] == expected_failure["field"]
        and behavior_failures[0]["observed"] is False
        and _exact(corrected, (
            "state", "resultSha256", "effectObserved",
            "independentPoststateObserved", "cleanupObserved",
        ), ("state", "resultSha256"))
        and corrected == {
            "state": "passed", "resultSha256": corrected_sha,
            "effectObserved": True, "independentPoststateObserved": True,
            "cleanupObserved": True,
        }
        and corrected_sha != original_record["sha256"]
        and _exact(model_result, (
            "kind", "taskId", "sha256", "valueSha256", "value",
        ), ("kind", "taskId", "sha256", "valueSha256"))
        and model_result["kind"] == "model-result-slice"
        and model_result["taskId"] == "GT-16"
        and re.fullmatch(r"[0-9a-f]{64}", corrected_sha or "") is not None
        and isinstance(model_value, dict)
        and re.fullmatch(r"[0-9a-f]{64}", value_sha or "") is not None
        and value_sha == _digest(model_value)
        and assistant_value == model_value
        and assistant_raw is not None
        and sha256(assistant_raw).hexdigest() == value_sha
        and model_value.get("taskId") == "GT-16"
        and model_value.get("replayKind")
        == "corrected-replay-after-retained-behavior-failure"
        and _exact(prior, (
            "originalResultPath", "originalResultSha256",
            "oracleAdjudicationPath", "oracleAdjudicationSha256", "failure",
        ), (
            "originalResultPath", "originalResultSha256",
            "oracleAdjudicationPath", "oracleAdjudicationSha256",
        ))
        and prior["originalResultSha256"] == original_record["sha256"]
        and prior["oracleAdjudicationSha256"] == adjudication_record["sha256"]
        and prior["failure"] == expected_failure
        and isinstance(corrected_state, dict)
        and corrected_state.get("effectObserved") is True
        and _exact(result_binding, (
            "kind", "taskId", "resultSha256", "runtimeModelSelection",
            "qualificationBranchesOnModelIdentityOrVersion",
        ), ("kind", "taskId", "resultSha256", "runtimeModelSelection"))
        and result_binding["taskId"] == "GT-16"
        and result_binding["resultSha256"] == corrected_sha
        and result_binding["runtimeModelSelection"] == "host-default-variable"
        and result_binding["qualificationBranchesOnModelIdentityOrVersion"] is False
        and _exact(bootstrap, (
            "kind", "selectedRoute", "correctedState",
            "poststateArtifactSha256",
        ), ("kind", "selectedRoute", "poststateArtifactSha256"))
        and bootstrap["selectedRoute"] == model_value.get("selectedRouteId")
        and bootstrap["correctedState"] == corrected_state
        and isinstance(effect, dict) and effect.get("resultSha256") == corrected_sha
        and effect.get("artifactSha256") == bootstrap["poststateArtifactSha256"]
        and isinstance(effect_facts, dict)
        and effect_facts.get("valid") is True
        and effect_facts.get("correctedState") == corrected_state
        and effect_facts.get("effectObserved") is True
        and effect_facts.get("correctionPreserved") is True
        and effect_facts.get("unrelatedStatePreserved") is True
        and isinstance(rollback, dict)
        and rollback.get("resultSha256") == corrected_sha
        and isinstance(rollback_facts, dict)
        and rollback_facts.get("valid") is True
        and rollback_facts.get("rollbackDisposition") == "discard-and-rollback"
        and rollback_facts.get("releasedResources") == ["task-scoped-handoff"]
        and rollback_facts.get("residualTaskResources") == []
        and rollback_facts.get("persistentControllerMaterialized") is False
        and rollback_facts.get("fixtureRestoredToBaseline") is True
        and isinstance(cleanup_result, dict)
        and isinstance(cleanup_observation, dict)
        and cleanup_observation.get("resultSha256") == corrected_sha
        and cleanup_observation.get("taskId") == "GT-16"
        and cleanup_observation.get("phase") == "cleanup-poststate"
        and cleanup_facts == {
            "exactRunRootAbsent": True, "taskOwnedResidueCount": 0,
            "fixtureRemoved": True, "unrelatedStatePreserved": True,
        }
        and payload.get("cleanupEvidence", {}).get("state") == "verified-clean"
        and cleanup == {
            "state": "verified-clean", "taskOwnedResidueCount": 0,
            "verified": True,
        }
    )
    return retained if valid else None


def _publishable_payload(
    payload, task, cleanup, captured_at, projection, continuity_narratives=None,
):
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
        and _embedded_research_source_packet(payload, task, captured_at)
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
        and _gt16_retained_failure_bundle(payload, task, cleanup) is not None
        and _continuity_handoff_bundle(
            payload, task, continuity_narratives
        ) is not None
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
_EXPECTED_EVALUATION_CONTRACT_HISTORY_SHA256 = (
    "7cdc8cfc0d90703ccf3f41692464b9823e3e9aac4b66c1348b2b8517392d9be9"
)
_EXPECTED_EVALUATION_CONTRACT_SUCCESSOR_SHA256 = (
    "6282c8dfb92f9d4f84bd516f2fb675e3816c5dd27e503d60e0432439bc2a0f6b"
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
        source_revision = item.get("sourceRevision") if isinstance(item, dict) else None
        fields = ("kind", "sha256", "preservedTaskIds", "reason") + (
            ("sourceRevision",) if source_revision is not None else ()
        )
        if (
            not _exact(item, fields, ("sha256", "reason") + (
                ("sourceRevision",) if source_revision is not None else ()
            ))
            or item["kind"] != "scoped-evaluation-contract-supersession"
            or re.fullmatch(r"[0-9a-f]{64}", item["sha256"]) is None
            or _string_set(preserved) is None or not preserved
            or source_revision is not None
            and re.fullmatch(r"[0-9a-f]{40}", source_revision) is None
        ):
            return None
        if (
            current == _EXPECTED_EVALUATION_CONTRACT_SUCCESSOR_SHA256
            and task_id in preserved
        ):
            contracts.add(item["sha256"])
    if _digest(history) != _EXPECTED_EVALUATION_CONTRACT_HISTORY_SHA256:
        return None
    return contracts


def evaluation_contract_history_valid(policy, current=None):
    return _evaluation_contracts(
        policy, "", current or _EXPECTED_EVALUATION_CONTRACT_SUCCESSOR_SHA256,
    ) is not None


def _historical_evaluation_contract(root, policy, task_id, current, target):
    admitted = _evaluation_contracts(policy, task_id, current)
    history = policy.get("evaluationContractHistory") if isinstance(policy, dict) else []
    matches = [
        item for item in history if isinstance(item, dict)
        and item.get("sha256") == target and task_id in item.get("preservedTaskIds", [])
        and isinstance(item.get("sourceRevision"), str)
    ]
    if admitted is None or target not in admitted or len(matches) != 1:
        return None
    revision = matches[0]["sourceRevision"]
    try:
        _bounded_git_bytes(root, ["merge-base", "--is-ancestor", revision, "HEAD"], 1)
        acceptance = _strict_json_object(_bounded_git_bytes(
            root, ["show", "--end-of-options", f"{revision}:product/acceptance.json"]
        ))
        golden = _strict_json_object(_bounded_git_bytes(
            root, ["show", "--end-of-options", f"{revision}:evals/golden-tasks.json"]
        ))
    except (OSError, subprocess.SubprocessError, UnicodeError, ValueError):
        return None
    return (acceptance, golden) \
        if representative_contract_sha256(acceptance, golden) == target else None


def _source_amendments(
    root, record, task, task_digest, captured_at, current_contract=None,
):
    amendments = record.get("amendments") if isinstance(record, dict) else None
    if amendments is None:
        if current_contract is None:
            return True
        if not isinstance(record, dict) or not isinstance(current_contract, tuple) \
                or len(current_contract) != 3:
            return False
        acceptance, _, current = current_contract
        admitted = _evaluation_contracts(
            acceptance.get("representativeBehaviorPolicy", {}), task.get("id"), current,
        ) if isinstance(acceptance, dict) else None
        return admitted is not None and record.get("evaluationContractSha256") in admitted
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
        corrected_evaluation = amendment.get("correctedEvaluationContractSha256")
        delta_contract = (current_acceptance, current_golden)
        if corrected_evaluation != current_evaluation:
            delta_contract = _historical_evaluation_contract(
                root, current_acceptance.get("representativeBehaviorPolicy"),
                task.get("id"), current_evaluation, corrected_evaluation,
            )
            if delta_contract is None:
                return False
        if not _candidate_evaluation_delta(
            prior_acceptance, prior_golden,
            amendment.get("priorEvaluationContractSha256"),
            *delta_contract, corrected_evaluation,
        ):
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
    if observation.get("evidenceClass") == "frozen-source-metadata-promotion":
        return _frozen_gt20_21_observation_errors(
            root, label, observation, task, projection_id, read_json,
            require_current_subject,
        )
    errors, retained_prior_failure = [], False
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
        continuity_narratives = _continuity_narrative_hashes(
            root, locator, record_id, record.get("payload", {}), task,
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
                observation.get("projectionIdentity"), continuity_narratives,
            )
            and (
                record_id != "GT-15-current-artifacts-cf1d8c9e"
                or isinstance(record.get("payload"), dict)
                and "sourcePacket" in record["payload"]
                and _embedded_research_source_packet(
                    record["payload"], task, captured,
                )
            )
            and source.get("sha256") == _digest(record)
            and (not binding_contract or postcapture is not None and source.get(
                "postSessionBindingsSha256") == _digest(postcapture))
        )
        if not valid:
            errors.append(f"{label} sourceEvidence[{index}] is invalid")
        elif _gt16_retained_failure_bundle(
            record.get("payload"), task, observation.get("cleanup")
        ):
            retained_prior_failure = True

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
    elif behavior_valid:
        expected_exclusions = set(failures)
        if retained_prior_failure:
            expected_exclusions.add("the retained prior behavior failure passed")
        if (
            claim["retainedFailure"] is not bool(expected_exclusions)
            or set(claim["excludedClaims"]) != expected_exclusions
            or len(claim["excludedClaims"]) != len(expected_exclusions)
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
    current_subject_replays=(),
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
        and item.get("assessment") in ("verified", "continuing")
        and "representative-behavior" in item.get("requiredEvidenceClasses", [])
    ]
    if not users:
        return []
    if representative.get("assessment") not in ("verified", "continuing"):
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
    require_current_subject = representative.get("assessment") in (
        "verified", "continuing"
    )
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
            require_current_subject and task_id not in current_subject_replays,
            (acceptance, golden, evaluation),
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


def _provisional_projection_files(root, program, read_json, errors):
    subjects, packages = set(), {}
    projections = program.get("hostProjections") if isinstance(program, dict) else None
    for projection in projections if isinstance(projections, list) else []:
        if not isinstance(projection, dict) or not _text(projection.get("id")):
            continue
        locators = [projection.get(field) for field in ("manifest", "contract", "skill")]
        for field in ("metadataFiles", "mechanismFiles"):
            value = projection.get(field)
            locators.extend(value if isinstance(value, list) else [])
        manifest_locator = projection.get("manifest")
        manifest = read_json(root, manifest_locator, errors) \
            if _text(manifest_locator) else {}
        interface = manifest.get("interface") if isinstance(manifest, dict) else None
        plugin_root = manifest_locator.rsplit("/", 2)[0] \
            if _text(manifest_locator) and manifest_locator.count("/") >= 2 else None
        for field in ("composerIcon", "logo", "logoDark"):
            value = interface.get(field) if isinstance(interface, dict) else None
            parts = value[2:].split("/") \
                if isinstance(value, str) and value.startswith("./") else []
            if plugin_root and parts and all(part not in {"", ".", ".."} for part in parts):
                locators.append("/".join((plugin_root, *parts)))
        package = {locator for locator in locators if _text(locator)}
        packages[projection["id"]] = package
        subjects.update(package)
        marketplace = projection.get("marketplace")
        if _text(marketplace):
            subjects.add(marketplace)
    return subjects, packages


def _provisional_revision_digest(root, revision, locator):
    content = _bounded_git_bytes(
        root, ["show", "--end-of-options", f"{revision}:{locator}"]
    )
    return sha256(content).hexdigest()


def _provisional_package_digest(root, revision, locators):
    digest = sha256()
    for locator in sorted(locators):
        digest.update(locator.encode("utf-8"))
        digest.update(b"\0")
        digest.update(bytes.fromhex(
            _provisional_revision_digest(root, revision, locator)
        ))
    return digest.hexdigest()


def _frozen_path(value, dotted_path):
    current = value
    for part in dotted_path.split("."):
        if not isinstance(current, dict) or part not in current:
            return None
        current = current[part]
    return current


def _frozen_projection_identity(root, program, projection_id):
    items = program.get("hostProjections") if isinstance(program, dict) else None
    matches = [
        item for item in items or []
        if isinstance(item, dict) and item.get("id") == projection_id
    ]
    if len(matches) != 1:
        return None
    item = matches[0]
    contract, skill, mechanisms = (
        item.get("contract"), item.get("skill"), item.get("mechanismFiles")
    )
    if (
        not _text(contract) or not _text(skill)
        or not isinstance(mechanisms, list) or not mechanisms
        or any(not _text(locator) for locator in mechanisms)
    ):
        return None
    try:
        mechanism_files = [
            {
                "locator": locator,
                "sha256": _provisional_revision_digest(root, "HEAD", locator),
            }
            for locator in mechanisms
        ]
        mechanism_sha256 = _provisional_package_digest(
            root, "HEAD", mechanisms
        )
        contract_sha256 = _provisional_revision_digest(root, "HEAD", contract)
        skill_sha256 = _provisional_revision_digest(root, "HEAD", skill)
    except (OSError, subprocess.SubprocessError, UnicodeError, ValueError):
        return None
    return {
        "adapterId": projection_id,
        "packageId": item.get("packageId"),
        "packageVersion": item.get("packageVersion"),
        "packageSha256": item.get("packageSha256"),
        "contract": contract,
        "contractSha256": contract_sha256,
        "skill": skill,
        "skillSha256": skill_sha256,
        "mechanismFiles": mechanism_files,
        "mechanismSha256": mechanism_sha256,
    }


def gt20_exact_lifecycle_invalidated(value):
    return (
        isinstance(value, dict)
        and (value.get("schema"), value.get("earliestAffectedBoundary")) in {
            ("yiyuan-accord-exact-package-evidence-lifecycle/v1",
             "complete-host-projection-package-identity"),
            ("yiyuan-accord-exact-package-evidence-lifecycle/v2",
             "exact-package-evaluator-failure-closure"),
            ("yiyuan-accord-exact-package-evidence-lifecycle/v3",
             "exact-package-evaluator-privacy-termination-cleanup-closure"),
            ("yiyuan-accord-exact-package-evidence-lifecycle/v4",
             "exact-package-command-contract-host-neighbor-and-brand-surface-closure"),
            ("yiyuan-accord-exact-package-evidence-lifecycle/v5",
             "exact-package-evaluator-privacy-ownership-and-native-host-adaptation-closure"),
            ("yiyuan-accord-exact-package-evidence-lifecycle/v6",
             "exact-package-host-activation-and-mutation-phase-failed-update-"
             "recovery-closure"),
            ("yiyuan-accord-exact-package-evidence-lifecycle/v7",
             "single-intent-agent-decision-and-bounded-failed-update-recovery-"
             "closure"),
        }
        and value.get("taskId") == "GT-20"
        and value.get("state") in {"pending", "verified"}
    )


def provisional_gt20_21_source_errors(
    root, program, acceptance, golden, read_json,
):
    errors = []
    program = program if isinstance(program, dict) else {}
    acceptance = acceptance if isinstance(acceptance, dict) else {}
    golden = golden if isinstance(golden, dict) else {}
    task_items = golden.get("tasks")
    task_items = task_items if isinstance(task_items, list) else []
    tasks = {
        item.get("id"): item for item in task_items
        if isinstance(item, dict) and _text(item.get("id"))
    }

    expected_inputs = {
        "gt20-transactional-lifecycle-2026-08-30",
        "gt21-live-carrier-preflight-2026-08-29",
    }
    input_items = program.get("inputEvidence")
    input_items = input_items if isinstance(input_items, list) else []
    inputs = {
        item.get("id"): item for item in input_items
        if isinstance(item, dict) and _text(item.get("id"))
        and item.get("id") in expected_inputs
    }
    if (
        set(inputs) != expected_inputs
        or any(item.get("repositoryLocator") != PROVISIONAL_GT20_21_SOURCE
               for item in inputs.values())
    ):
        errors.append("provisional GT-20/21 source input binding is invalid")

    criteria = acceptance.get("criteria")
    criteria = criteria if isinstance(criteria, list) else []
    r3 = next((
        item for item in criteria
        if isinstance(item, dict) and item.get("id") == "R3"
    ), {})
    increment = program.get("increment")
    lifecycle = increment.get("provisionalEvidenceLifecycle") \
        if isinstance(increment, dict) else None
    exact_lifecycle = increment.get("exactPackageEvidenceLifecycle") \
        if isinstance(increment, dict) else None
    invalidated_gt20 = gt20_exact_lifecycle_invalidated(exact_lifecycle)
    lifecycle_fields = (
        "schema", "state", "criterionId", "taskIds", "sourceLocator",
        "sourceSha256", "inputEvidenceIds", "targetReleaseTag",
        "promotionGate", "retirementGate", "retiredByPublicRelease",
    )
    lifecycle_base_valid = (
        _exact(lifecycle, lifecycle_fields,
               ("schema", "state", "criterionId", "sourceLocator",
                "sourceSha256", "targetReleaseTag", "promotionGate",
                "retirementGate"))
        and lifecycle.get("schema") == _PROVISIONAL_GT20_21_LIFECYCLE_SCHEMA
        and lifecycle.get("criterionId") == "R3"
        and lifecycle.get("taskIds") == ["GT-20", "GT-21"]
        and lifecycle.get("sourceLocator") == PROVISIONAL_GT20_21_SOURCE
        and lifecycle.get("inputEvidenceIds") == sorted(expected_inputs)
        and isinstance(lifecycle.get("sourceSha256"), str)
        and re.fullmatch(r"[0-9a-f]{64}", lifecycle["sourceSha256"])
        and all(item.get("repositorySha256") == lifecycle.get("sourceSha256")
                for item in inputs.values())
        and lifecycle.get("promotionGate")
        == "program-ready-with-complete-current-r3"
        and lifecycle.get("retirementGate")
        == "recorded-post-release-reconciliation"
    )
    state = lifecycle.get("state") if lifecycle_base_valid else None
    target_release = lifecycle.get("targetReleaseTag") \
        if lifecycle_base_valid else None
    active_current_gate = True
    if not lifecycle_base_valid:
        errors.append("provisional GT-20/21 lifecycle contract is invalid")
    elif state == "active-current-byte-gate":
        if (
            lifecycle.get("retiredByPublicRelease") is not None
            or target_release != program.get("distributionVersion")
        ):
            errors.append("provisional GT-20/21 lifecycle transition is invalid")
    elif state == "promoted-by-complete-current-r3":
        if invalidated_gt20 and (
            lifecycle.get("retiredByPublicRelease") is None
            and target_release == program.get("distributionVersion")
            and program.get("status") in {"active", "ready"}
            and r3.get("assessment") in ("continuing", "verified")
        ):
            active_current_gate = False
        elif (
            lifecycle.get("retiredByPublicRelease") is not None
            or target_release != program.get("distributionVersion")
            or program.get("status") != "ready"
            or r3.get("assessment") != "verified"
        ):
            errors.append("provisional GT-20/21 lifecycle transition is invalid")
        else:
            active_current_gate = False
    elif state == "retired-after-recorded-public-release":
        program_history = program.get("historicalRelease", {})
        acceptance_history = acceptance.get("historicalRelease", {})
        public_releases = program_history.get("publicReleases", []) \
            if isinstance(program_history, dict) else []
        matching_release = [
            item for item in public_releases if isinstance(item, dict)
            and item.get("tag") == target_release
            and item.get("releaseKind") == "full-release"
            and item.get("prerelease") is False
        ] if isinstance(public_releases, list) else []
        retirement = lifecycle.get("retiredByPublicRelease")
        retirement_fields = {
            "tag", "revision", "observedAt", "source", "releaseApi", "tagApi",
        }
        public_policy = acceptance.get("publicRelease", {})
        observed_at = _time(retirement.get("observedAt")) \
            if isinstance(retirement, dict) else None
        published_at = _time(matching_release[0].get("publishedAt")) \
            if len(matching_release) == 1 else None
        if (
            target_release != program.get("distributionVersion")
            or target_release != acceptance.get("distributionVersion")
            or program.get("status") != "ready"
            or r3.get("assessment") != "verified"
            or not isinstance(retirement, dict)
            or set(retirement) != retirement_fields
            or retirement.get("tag") != target_release
            or not isinstance(retirement.get("revision"), str)
            or re.fullmatch(r"[0-9a-f]{40}", retirement["revision"]) is None
            or retirement.get("source") != "task-time-live-github-observation"
            or not isinstance(public_policy, dict)
            or public_policy.get("tag") != target_release
            or retirement.get("releaseApi") != public_policy.get("releaseApi")
            or retirement.get("tagApi") != public_policy.get("tagApi")
            or not isinstance(program_history, dict)
            or not isinstance(acceptance_history, dict)
            or program_history != acceptance_history
            or program_history.get("recommendedPublicRelease") != target_release
            or len(matching_release) != 1
            or retirement.get("revision") != matching_release[0].get("revision")
            or observed_at is None
            or published_at is None
            or observed_at < published_at
        ):
            errors.append("provisional GT-20/21 lifecycle transition is invalid")
        else:
            active_current_gate = False
    else:
        errors.append("provisional GT-20/21 lifecycle state is invalid")

    package_files = {}
    if active_current_gate:
        declared, package_files = _provisional_projection_files(
            root, program, read_json, errors,
        )
        gt20_files = tasks.get("GT-20", {}).get("behaviorSubjectFiles")
        if _string_set(gt20_files) != declared:
            errors.append(
                "provisional GT-20 behavior subject does not match declared projection files"
            )

    bundle = read_json(root, PROVISIONAL_GT20_21_SOURCE, errors)
    contract = bundle.get("provisionalContract") if isinstance(bundle, dict) else None
    if (
        not _exact(bundle, (
            "schema", "provisionalContract", "frozenPromotion", "records",
        ))
        or bundle.get("schema") != 1
        or not _exact(contract, (
            "schema", "sourceLocator", "retainedRecords", "records",
        ),
                      ("schema", "sourceLocator"))
        or contract.get("schema") != "yiyuan-accord-provisional-gt20-21-source/v2"
        or contract.get("sourceLocator") != PROVISIONAL_GT20_21_SOURCE
        or not isinstance(contract.get("retainedRecords"), list)
        or not isinstance(contract.get("records"), list)
    ):
        errors.append("provisional GT-20/21 source contract is invalid")
        contract = {}
    records = bundle.get("records") if isinstance(bundle, dict) else None
    records = records if isinstance(records, dict) else {}
    retained_records = contract.get("retainedRecords") \
        if isinstance(contract, dict) else None
    expected_retained_records = [
        {"recordId": record_id, "sha256": digest}
        for record_id, digest in _PROVISIONAL_GT20_21_RETAINED_RECORDS
    ]
    if (
        retained_records != expected_retained_records
        or tuple(records) != tuple(
            record_id for record_id, _ in _PROVISIONAL_GT20_21_RETAINED_RECORDS
        )
        or any(
            _digest(records.get(record_id)) != digest
            for record_id, digest in _PROVISIONAL_GT20_21_RETAINED_RECORDS
        )
    ):
        errors.append("provisional GT-20/21 retained attempt ledger is invalid")
    entries = contract.get("records") if isinstance(contract, dict) else None
    entries = entries if isinstance(entries, list) else []
    by_task = {
        item.get("taskId"): item for item in entries
        if isinstance(item, dict) and _text(item.get("taskId"))
    }
    if len(entries) != 2 or len(by_task) != 2 or set(by_task) != {"GT-20", "GT-21"}:
        errors.append("provisional GT-20/21 source record set is invalid")

    definitions = {
        "GT-20": {
            "recordId": "GT-20-transactional-lifecycle-4c8bcc3",
            "goldenTaskSha256": "22368fc53a4154aacf7ae91ebf5a535e3953f65353b86e16f0fc296cdedd1fd4",
            "postPath": "cleanupEvidence",
            "claimPath": "claimLimit",
            "cleanupState": "verified-foreign-state-preserved",
            "observer": "no-evaluated-agent-or-model-participated",
            "allowedScope": (
                "exact tracked v3.0.1 to 4c8bcc3 package bytes in two disposable "
                "non-empty windows host scopes"
            ),
            "excludedClaims": [
                "unmanaged", "production", "actual claude host hook triggering",
                "product value", "cross-host equivalence", "whole-system balance",
                "independent review", "candidate readiness", "release readiness",
            ],
            "recordSha256": "a66b9aa05610baf362c38213d266d31a005c737ab1699173a590a25542cd32ec",
            "claimSha256": "b00d2ff5650ae82efce5da9aa9096767dfd44107e6cb3e92688e75933d97b5fb",
        },
        "GT-21": {
            "recordId": "GT-21-fresh-zero-history-handoff-3878968",
            "goldenTaskSha256": "a7634cccb150a0cde1c8d35899fab0da621b40b6ae42ec3729c62b5b7382b0ea",
            "postPath": "payload.liveObservation.independentPoststate",
            "claimPath": "payload.decision.claimLimit",
            "cleanupState": "verified-clean",
            "observer": "parent-evaluator-not-evaluated-agent",
            "allowedScope": (
                "one exact bounded current-host fresh zero-history handoff on revision 3878968"
            ),
            "excludedClaims": [
                "cross-host", "production", "value", "independent review",
                "candidate", "release",
            ],
            "recordSha256": "cb14e25128123afcfb6354fefcb480d18b171d7539af0a78dc905f61df33b5cc",
            "claimSha256": "0a57fd9adfa7c52be3d81dd6e11c6b15f2e826602a4316a233deeef2798da954",
        },
    }
    evaluation = representative_contract_sha256(acceptance, golden) \
        if active_current_gate else None
    evaluation_policy = acceptance.get("representativeBehaviorPolicy")
    projection_items = program.get("hostProjections")
    projection_items = projection_items if isinstance(projection_items, list) else []
    current_packages = {
        item.get("id"): item.get("packageSha256")
        for item in projection_items if isinstance(item, dict)
    }
    fields = (
        "taskId", "recordId", "goldenTaskSha256", "evaluationContractSha256",
        "evaluatedRevision", "behaviorSubject", "projectionPackageSha256",
        "sourceBindings", "independentPoststate", "cleanup", "claimCeiling",
    )
    for task_id, definition in definitions.items():
        label, task = f"provisional {task_id}", tasks.get(task_id)
        record = records.get(definition["recordId"])
        record = record if isinstance(record, dict) else {}
        payload = record.get("payload") if isinstance(record.get("payload"), dict) else {}
        live_observation = payload.get("liveObservation")
        live_observation = live_observation \
            if isinstance(live_observation, dict) else {}
        decision_record = payload.get("decision")
        decision_record = decision_record if isinstance(decision_record, dict) else {}
        authority_record = record.get("authorityAndPrivacy")
        authority_record = authority_record \
            if isinstance(authority_record, dict) else {}
        revision = record.get("evaluatedRevision") if task_id == "GT-20" \
            else payload.get("evaluatedRevision")
        if not isinstance(revision, str) or re.fullmatch(
            r"[0-9a-f]{40}", revision
        ) is None:
            errors.append(f"{label} evaluatedRevision is invalid")
            revision = None
        else:
            try:
                relation = subprocess.run(
                    ["git", "-C", str(root), "merge-base", "--is-ancestor",
                     revision, "HEAD"],
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                ).returncode
            except (OSError, subprocess.SubprocessError, UnicodeError, ValueError):
                errors.append(f"{label} evaluatedRevision is unavailable")
                revision = None
            else:
                if relation != 0:
                    errors.append(f"{label} evaluatedRevision is not an ancestor")

        entry = by_task.get(task_id)
        if not _exact(entry, fields):
            errors.append(f"{label} contract is invalid")
            entry = {}
        if entry.get("taskId") != task_id or entry.get("recordId") != definition["recordId"]:
            errors.append(f"{label} source record identity mismatch")
        if _digest(entry) != _PROVISIONAL_GT20_21_CONTRACT_SHA256[task_id]:
            errors.append(f"{label} source contract record is not admitted")
        if entry.get("goldenTaskSha256") != definition["goldenTaskSha256"]:
            errors.append(f"{label} source Golden Task digest is not admitted")
        if (
            active_current_gate
            and (not isinstance(task, dict)
                 or entry.get("goldenTaskSha256") != _digest(task))
        ):
            errors.append(f"{label} Golden Task digest mismatch")
        if (
            entry.get("evaluationContractSha256")
            != _PROVISIONAL_GT20_21_EVALUATION_SHA256
        ):
            errors.append(f"{label} source evaluation contract digest is not admitted")
        admitted_evaluations = _evaluation_contracts(
            evaluation_policy, task_id, evaluation,
        ) if active_current_gate else None
        if (
            active_current_gate
            and (admitted_evaluations is None
                 or entry.get("evaluationContractSha256") not in admitted_evaluations)
        ):
            errors.append(f"{label} evaluation contract digest mismatch")
        if entry.get("evaluatedRevision") != revision:
            errors.append(f"{label} evaluatedRevision binding mismatch")
        if active_current_gate and isinstance(task, dict) and revision is not None:
            errors.extend(_behavior_subject_revision_errors(
                root, label, {"evaluatedRevision": revision}, task,
            ))
        subject = entry.get("behaviorSubject")
        subject_valid = (
            isinstance(subject, dict) and bool(subject)
            and all(
                _text(locator) and isinstance(value, str)
                and re.fullmatch(r"[0-9a-f]{64}", value)
                for locator, value in subject.items()
            )
        )
        if active_current_gate:
            subject_files = task.get("behaviorSubjectFiles") \
                if isinstance(task, dict) else None
            subject_valid = (
                subject_valid
                and _string_set(subject_files) == set(subject)
            )
        if task_id == "GT-21" and subject != payload.get("behaviorSubject"):
            subject_valid = False
        if subject_valid and revision is not None:
            try:
                subject_valid = all(
                    digest == _provisional_revision_digest(root, revision, locator)
                    for locator, digest in subject.items()
                )
            except (OSError, subprocess.SubprocessError, UnicodeError, ValueError):
                subject_valid = False
        if not subject_valid:
            errors.append(f"{label} behavior subject binding is invalid")

        package_binding = entry.get("projectionPackageSha256")
        if task_id == "GT-20" and active_current_gate and revision is not None:
            try:
                revision_packages = {
                    adapter: _provisional_package_digest(root, revision, locators)
                    for adapter, locators in package_files.items()
                }
            except (OSError, subprocess.SubprocessError, UnicodeError, ValueError):
                revision_packages = None
            if package_binding != revision_packages or package_binding != current_packages:
                errors.append(f"{label} projection package digest mismatch")
        elif task_id == "GT-21" and package_binding != {}:
            errors.append(f"{label} projection package digest is out of scope")

        bindings = entry.get("sourceBindings")
        record_digest = _digest(record)
        expected_binding = [{
            "kind": "bundle-record-sha256",
            "locator": PROVISIONAL_GT20_21_SOURCE,
            "recordId": definition["recordId"],
            "sha256": definition["recordSha256"],
        }]
        if record_digest != definition["recordSha256"]:
            errors.append(f"{label} source record digest is not admitted")
        if bindings != expected_binding:
            errors.append(f"{label} source binding is invalid")

        poststate = record.get("cleanupEvidence") if task_id == "GT-20" \
            else live_observation.get("independentPoststate")
        post_contract = entry.get("independentPoststate")
        post_valid = (
            _exact(post_contract, ("sourcePath", "sha256", "observerSeparation"),
                   ("sourcePath", "sha256", "observerSeparation"))
            and post_contract.get("sourcePath") == definition["postPath"]
            and post_contract.get("sha256") == _digest(poststate)
            and post_contract.get("observerSeparation") == definition["observer"]
        )
        if task_id == "GT-20":
            phases = record.get("orderedObservations")
            release = next((item for item in phases if isinstance(item, dict)
                            and item.get("phase") == "task-resource-release"), {}) \
                if isinstance(phases, list) else {}
            cache = record.get("hostCacheDisposition")
            claude_cache = cache.get("claude") if isinstance(cache, dict) else None
            post_valid = post_valid and (
                isinstance(poststate, dict)
                and all(poststate.get(field) == 0 for field in (
                    "activeAccordRegistrations", "activeAccordMarketplaces",
                    "activeAccordDataRoots", "matchingTaskProcesses",
                ))
                and poststate.get("formalFixtureRootExists") is False
                and poststate.get("learningFixtureRootExists") is False
                and poststate.get("repositoryTmpInspectedOrModified") is False
                and authority_record.get("modelCallCount") == 0
                and _text(release.get("observed"))
                and "independently" in release["observed"]
                and isinstance(claude_cache, dict)
                and claude_cache.get("listedOrEnabled") is False
                and claude_cache.get("callable") is False
                and claude_cache.get("dataStatePresent") is False
                and _text(claude_cache.get("cleanupContract"))
            )
        else:
            post_valid = post_valid and (
                isinstance(poststate, dict)
                and _text(poststate.get("observer"))
                and "not the evaluated Agent" in poststate["observer"]
                and all(poststate.get(field) is True for field in (
                    "sourceDeleted", "destinationDeleted",
                    "disposableCredentialStateRemoved", "disposablePluginStateRemoved",
                    "taskRootRemoved", "taskRootAbsentAfterRemoval",
                ))
                and all(poststate.get(field) == 0 for field in (
                    "remainingTaskThreads", "matchingTaskProcesses",
                    "taskOwnedResidueRetained",
                ))
            )
        if not post_valid:
            errors.append(f"{label} independent post-state is invalid")

        cleanup = entry.get("cleanup")
        if (
            not _exact(cleanup, ("state", "taskOwnedResidueCount", "verified"),
                       ("state",))
            or cleanup.get("state") != definition["cleanupState"]
            or type(cleanup.get("taskOwnedResidueCount")) is not int
            or cleanup.get("taskOwnedResidueCount") != 0
            or cleanup.get("verified") is not True
            or not post_valid
        ):
            errors.append(f"{label} cleanup contract is invalid")

        claim = record.get("claimLimit") if task_id == "GT-20" \
            else decision_record.get("claimLimit")
        ceiling = entry.get("claimCeiling")
        claim_text = claim.lower() if isinstance(claim, str) else ""
        marker = "does not prove" if "does not prove" in claim_text else "; no "
        prefix, separator, exclusions = claim_text.partition(marker)
        if (
            not _exact(ceiling, (
                "sourcePath", "sha256", "scope", "allowedScope", "excludedClaims",
                "independentReviewClaimed", "candidateClaimed", "releaseClaimed",
            ), ("sourcePath", "sha256", "scope", "allowedScope"))
            or ceiling.get("sourcePath") != definition["claimPath"]
            or ceiling.get("sha256") != definition["claimSha256"]
            or _digest(claim) != definition["claimSha256"]
            or ceiling.get("scope") != "bounded-provisional-source-only"
            or ceiling.get("allowedScope") != definition["allowedScope"]
            or ceiling.get("excludedClaims") != definition["excludedClaims"]
            or any(ceiling.get(field) is not False for field in (
                "independentReviewClaimed", "candidateClaimed", "releaseClaimed",
            ))
            or not separator or definition["allowedScope"] not in prefix
            or any(value in prefix for value in (
                "independent review", "candidate", "release",
            ))
            or any(value not in exclusions for value in definition["excludedClaims"])
        ):
            errors.append(f"{label} claim ceiling is invalid")
    return errors


def _frozen_gt20_21_observation_errors(
    root, label, observation, task, projection_id, read_json,
    require_current_subject,
):
    admitted = FROZEN_GT20_21_OBSERVATIONS.get(task.get("id"))
    errors = []
    if (
        projection_id not in {"", "codex"}
        or admitted is None
        or _digest(observation) != admitted[1]
    ):
        errors.append(f"{label} frozen promotion observation is invalid")
    if require_current_subject:
        errors.extend(_behavior_subject_revision_errors(
            root, label, observation, task,
        ))
    return errors, "passed" if not errors else None


def frozen_gt20_21_promotion_errors(
    root, program, acceptance, golden, read_json,
):
    errors = []

    def git_source(revision):
        try:
            data = _bounded_git_bytes(root, [
                "show", "--end-of-options", f"{revision}:{PROVISIONAL_GT20_21_SOURCE}",
            ], 1_048_576)
            return data, _strict_json_object(data)
        except (OSError, subprocess.SubprocessError, UnicodeError, ValueError):
            return b"", None

    base_bytes, base = git_source(_FROZEN_GT20_21_CURRENT_CONTRACT_REVISION)
    if (
        not isinstance(base, dict)
        or sha256(base_bytes).hexdigest() != _FROZEN_GT20_21_BASE_SOURCE_SHA256
    ):
        return ["frozen GT-20/21 base source binding is invalid"]
    bundle = read_json(root, PROVISIONAL_GT20_21_SOURCE, errors)
    if (
        not isinstance(bundle, dict)
        or set(bundle) != {"schema", "provisionalContract", "frozenPromotion", "records"}
        or any(bundle.get(field) != base.get(field)
               for field in ("schema", "provisionalContract", "records"))
    ):
        return errors + ["frozen GT-20/21 source preimage or retained attempts drifted"]
    promotion = bundle.get("frozenPromotion")
    if (
        not isinstance(promotion, dict)
        or promotion.get("schema") != _FROZEN_GT20_21_PROMOTION_SCHEMA
        or _digest(promotion) != _FROZEN_GT20_21_PROMOTION_SHA256
    ):
        return errors + ["frozen GT-20/21 promotion contract is invalid"]
    serialized = _canonical_json(promotion)
    if (
        "direct-host-material-events-v1" in serialized
        or any(f'\"{field}\"' in serialized for field in (
            "messages", "materialEvents", "observedAt", "capturedAt",
        ))
        or re.search(
            r"\b(?:gpt|claude|gemini|deepseek|llama|qwen)[\s_-]*"
            r"(?:\d|opus|sonnet|haiku|pro|flash|max|turbo)",
            serialized, re.IGNORECASE,
        )
    ):
        errors.append("frozen GT-20/21 promotion claims live, timed or model-bound behavior")
    for revision in (
        _FROZEN_GT20_21_SOURCE_BOUND_REVISION,
        _FROZEN_GT20_21_CURRENT_CONTRACT_REVISION,
    ):
        try:
            code = subprocess.run(
                ["git", "-C", str(root), "merge-base", "--is-ancestor", revision, "HEAD"],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            ).returncode
        except (OSError, subprocess.SubprocessError, UnicodeError, ValueError):
            code = 1
        if code:
            errors.append("frozen GT-20/21 source-bound revision is not an ancestor")

    program = program if isinstance(program, dict) else {}
    acceptance = acceptance if isinstance(acceptance, dict) else {}
    golden = golden if isinstance(golden, dict) else {}
    increment = program.get("increment")
    exact_lifecycle = increment.get("exactPackageEvidenceLifecycle") \
        if isinstance(increment, dict) else None
    invalidated_gt20 = gt20_exact_lifecycle_invalidated(exact_lifecycle)
    tasks = {item.get("id"): item for item in golden.get("tasks", [])
             if isinstance(item, dict) and _text(item.get("id"))}
    entries = {item.get("taskId"): item
               for item in base["provisionalContract"].get("records", [])
               if isinstance(item, dict)}
    promoted = {item.get("taskId"): item
                for item in promotion.get("promotedRecords", [])
                if isinstance(item, dict)}
    current_evaluation = representative_contract_sha256(acceptance, golden)
    policy = acceptance.get("representativeBehaviorPolicy", {})
    promotion_evaluation = promotion.get("currentEvaluationContractSha256") \
        if isinstance(promotion, dict) else None
    successors = [
        item for item in acceptance.get("representativeBehaviorPolicy", {}).get(
            "evaluationContractHistory", []
        ) if isinstance(item, dict)
        and item.get("sha256") == _PROVISIONAL_GT20_21_EVALUATION_SHA256
        and item.get("preservedTaskIds") == ["GT-20", "GT-21"]
    ]
    projections = {
        key: _frozen_projection_identity(root, program, key)
        for key in ("codex", "claude-code")
    }
    if (
        set(promoted) != set(FROZEN_GT20_21_OBSERVATIONS)
        or not set(promoted) <= set(tasks) or set(entries) != set(promoted)
        or len(successors) != 1
        or any(promotion_evaluation not in (
            _evaluation_contracts(policy, task_id, current_evaluation) or set()
        ) for task_id in promoted if task_id != "GT-20" or not invalidated_gt20)
        or promotion.get("contractSupersessionSha256") != _digest(successors[0])
        or None in projections.values()
        or not invalidated_gt20
        and promotion.get("projectionIdentities") != projections
    ):
        errors.append("frozen GT-20/21 current contract binding is invalid")

    _, ancestor = git_source(_FROZEN_GT20_21_SOURCE_BOUND_REVISION)
    ancestor_records = ancestor.get("records") if isinstance(ancestor, dict) else {}
    records = base["records"]
    selected_ids = set()
    gt21_roles = (
        "event-to-core-to-agent-consequence",
        "sufficient-simple-silent-route",
        "fresh-zero-history-handoff",
    )
    for task_id, (locator, _, record_ids) in FROZEN_GT20_21_OBSERVATIONS.items():
        task, entry, item = tasks.get(task_id), entries.get(task_id), promoted.get(task_id)
        selected_ids.update(record_ids)
        if not all(isinstance(value, dict) for value in (task, entry, item)):
            errors.append(f"frozen {task_id} source binding is invalid")
            continue
        if task_id == "GT-20" and invalidated_gt20:
            continue
        try:
            current_subject = {
                path: _provisional_revision_digest(root, "HEAD", path)
                for path in task.get("behaviorSubjectFiles", [])
            }
        except (OSError, subprocess.SubprocessError, UnicodeError, ValueError):
            current_subject = None
        shared_valid = (
            item.get("sourceDigests") == {
                "goldenTaskSha256": entry.get("goldenTaskSha256"),
                "evaluationContractSha256": entry.get("evaluationContractSha256"),
            }
            and item.get("currentDigests") == {
                "goldenTaskSha256": _digest(task),
                "evaluationContractSha256": promotion_evaluation,
            }
            and item.get("observationLocator") == locator
        )
        if task_id == "GT-20":
            record_id = record_ids[0]
            record = records.get(record_id)
            if (
                not isinstance(record, dict) or not shared_valid
                or ancestor_records.get(record_id) != record
                or item.get("selectedRecordId") != record_id
                or item.get("selectedRecordSha256") != _digest(record)
                or item.get("sourceContractEntrySha256") != _digest(entry)
                or item.get("evaluatedRevision") != entry.get("evaluatedRevision")
                or item.get("behaviorSubject") != entry.get("behaviorSubject")
                or item.get("behaviorSubject") != current_subject
            ):
                errors.append(f"frozen {task_id} source or digest binding is invalid")
                continue
            components = [(
                item, record, item["poststateBinding"], item["cleanupBinding"],
                item["claimCeilingBinding"],
            )]
        else:
            selection = item.get("selectedRecordSet")
            components = selection.get("components") \
                if isinstance(selection, dict) else None
            if (
                not shared_valid
                or item.get("sourceTaskContractEntrySha256") != _digest(entry)
                or item.get("evaluatedRevision")
                != _FROZEN_GT20_21_CURRENT_CONTRACT_REVISION
                or item.get("candidateBehaviorSubject") != current_subject
                or not isinstance(selection, dict)
                or selection.get("schema") != "ordered-frozen-source-composite/v1"
                or selection.get("orderRequired") is not True
                or selection.get("allComponentsRequired") is not True
                or not isinstance(components, list)
                or len(components) != len(record_ids)
                or [component.get("recordId") for component in components
                    if isinstance(component, dict)] != list(record_ids)
                or [component.get("role") for component in components
                    if isinstance(component, dict)] != list(gt21_roles)
                or [component.get("order") for component in components
                    if isinstance(component, dict)] != [1, 2, 3]
            ):
                errors.append("frozen GT-21 ordered composite selection is invalid")
                continue
            bound_components = []
            for component, record_id in zip(components, record_ids):
                record = records.get(record_id)
                payload = record.get("payload") if isinstance(record, dict) else None
                if (
                    not isinstance(record, dict) or not isinstance(payload, dict)
                    or ancestor_records.get(record_id) != record
                    or component.get("sourceRecordSha256") != _digest(record)
                    or component.get("evaluatedRevision") != payload.get("evaluatedRevision")
                    or component.get("behaviorSubject") != payload.get("behaviorSubject")
                    or component.get("behaviorSubject") != current_subject
                ):
                    errors.append(f"frozen GT-21 composite component {record_id} is invalid")
                    continue
                bound_components.append((
                    component, record, component.get("poststateBinding", {}),
                    component.get("cleanupBinding", {}),
                    component.get("claimCeilingBinding", {}),
                ))
                errors.extend(_behavior_subject_revision_errors(
                    root, f"frozen GT-21 {record_id}",
                    {"evaluatedRevision": component.get("evaluatedRevision")}, task,
                ))
            components = bound_components
            aggregate = item.get("compositeClaimCeilingBinding", {})
            aggregate_record = records.get(record_ids[0], {})
            if (
                aggregate.get("sourceRecordId") != record_ids[0]
                or aggregate.get("scope")
                != "three-selected-finite-source-claims-no-expansion"
                or aggregate.get("sourceClaimSha256") != _digest(_frozen_path(
                    aggregate_record, aggregate.get("sourcePath", "")
                ))
            ):
                errors.append("frozen GT-21 composite claim ceiling is invalid")
            errors.extend(_behavior_subject_revision_errors(
                root, "frozen GT-21 promoted candidate",
                {"evaluatedRevision": item.get("evaluatedRevision")}, task,
            ))

        for component, record, post, cleanup, claim in components:
            markers = cleanup.get("requiredMarkers")
            if (
                not isinstance(markers, dict)
                or post.get("sha256") != _digest(_frozen_path(
                    record, post.get("sourcePath", "")
                ))
                or cleanup.get("requiredMarkersSha256") != _digest(markers)
                or any(_frozen_path(record, path) != value
                       for path, value in markers.items())
                or claim.get("sourceClaimSha256") != _digest(_frozen_path(
                    record, claim.get("sourcePath", "")
                ))
                or task_id == "GT-20"
                and (
                    cleanup.get("contractSha256") != _digest(entry.get("cleanup"))
                    or claim.get("contractSha256") != _digest(
                        entry.get("claimCeiling")
                    )
                )
            ):
                errors.append(
                    f"frozen {task_id} poststate, cleanup or claim binding is invalid"
                )
        if task_id == "GT-20":
            errors.extend(_behavior_subject_revision_errors(
                root, f"frozen {task_id}",
                {"evaluatedRevision": item.get("evaluatedRevision")}, task,
            ))

    retained = [
        {"recordId": record_id,
         "disposition": "retained-in-raw-source-not-promoted"}
        for record_id in records if record_id not in selected_ids
    ]
    if promotion.get("nonPromotedAttempts") != retained:
        errors.append("frozen GT-20/21 failed or nonselected attempt ledger is invalid")

    for task_id, (locator, digest, _) in FROZEN_GT20_21_OBSERVATIONS.items():
        if task_id == "GT-20" and invalidated_gt20:
            continue
        observation, task = read_json(root, locator, errors), tasks.get(task_id)
        if (
            not isinstance(observation, dict) or _digest(observation) != digest
            or not isinstance(task, dict)
            or observation.get("evaluatedRevision")
            != promoted.get(task_id, {}).get("evaluatedRevision")
        ):
            errors.append(f"frozen {task_id} current observation is invalid")
        else:
            local, _ = _frozen_gt20_21_observation_errors(
                root, f"frozen {task_id}", observation, task, "codex",
                read_json, True,
            )
            errors.extend(local)
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
