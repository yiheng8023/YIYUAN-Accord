#!/usr/bin/env python3
"""Build a two-sample, non-recovery Git preflight evidence envelope.

The module reuses ``observe_git_snapshot.observe_repository``.  It neither
chooses a topology nor runs a recovery/topology mutation.  Git inspection may
refresh internal metadata, so this module does not claim filesystem zero-write
behavior. Dirty ownership is deliberately unknown by default and therefore
cannot be promoted into mutation authority.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable
from uuid import uuid4

try:
    from scripts.observe_git_snapshot import observe_repository
except ModuleNotFoundError:  # Direct execution from the scripts directory.
    from observe_git_snapshot import observe_repository


SCENARIO_ID = "GIT-READONLY-PREFLIGHT-ENVELOPE-01"
EVIDENCE_SOURCE = "native-git-non-recovery-observer"
RFC3339 = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})$")


def canonical_sha256(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode(
            "utf-8"
        )
    ).hexdigest()


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _path_evidence(snapshot: dict[str, Any]) -> list[dict[str, Any]]:
    """Bind every parsed dirty path to all raw porcelain tokens mentioning it.

    ``observe_repository`` deliberately retains both NUL-separated paths for
    rename/copy entries.  Keeping the raw tokens here avoids flattening those
    paths into an invented one-path status model.
    """

    raw_entries = snapshot.get("statusEntries", [])
    result: list[dict[str, Any]] = []
    for path in snapshot.get("dirtyPaths", []):
        matching = [
            entry
            for entry in raw_entries
            if entry == path or (isinstance(entry, str) and len(entry) >= 4 and entry[3:] == path)
        ]
        result.append(
            {
                "path": path,
                "ownerState": "unknown",
                "rawPorcelainEntries": matching,
            }
        )
    return result


def _event(
    *,
    run_id: str,
    sequence: int,
    snapshot: dict[str, Any],
    started_at: str,
    completed_at: str,
) -> dict[str, Any]:
    return {
        "sequence": sequence,
        "eventId": f"{run_id}:{sequence}",
        "startedAt": started_at,
        "completedAt": completed_at,
        "evidenceSource": EVIDENCE_SOURCE,
        "snapshot": snapshot,
        "snapshotSha256": canonical_sha256(snapshot),
        "rawPorcelainEntries": snapshot.get("statusEntries", []),
    }


def build_readonly_preflight_envelope(
    repository: str | Path,
    *,
    observer: Callable[[str | Path], dict[str, Any]] = observe_repository,
    clock: Callable[[], str] = _utc_now,
    run_id: str | None = None,
) -> dict[str, Any]:
    """Take exactly two observations and return a non-authorizing envelope."""

    run_id = run_id or f"git-readonly-preflight-{uuid4()}"
    before_started = clock()
    before = observer(repository)
    before_completed = clock()
    after_started = clock()
    after = observer(repository)
    after_completed = clock()
    before_event = _event(
        run_id=run_id, sequence=1, snapshot=before,
        started_at=before_started, completed_at=before_completed,
    )
    after_event = _event(
        run_id=run_id, sequence=2, snapshot=after,
        started_at=after_started, completed_at=after_completed,
    )
    locator = before.get("repository") if isinstance(before, dict) else None
    exact_equal = before == after
    dirty_evidence = _path_evidence(before) if isinstance(before, dict) else []
    envelope = {
        "schema": 1,
        "id": "git-readonly-preflight-envelope",
        "scenarioId": SCENARIO_ID,
        "runId": run_id,
        "repositoryWorktreeLocator": locator,
        "events": {"before": before_event, "after": after_event},
        "snapshotExactEquality": exact_equal,
        "dirtyOwnership": dirty_evidence,
        "taskDependsOnCurrentDirtyState": False,
        "approval": {"state": "not-requested", "evidenceSource": "not-observed"},
        "execution": {"attempted": False, "evidenceSource": "not-observed"},
        "retryAttempted": False,
        "writeAttempted": False,
        "countsAsNativeApprovalEvidence": False,
        "countsAsCreationSafetyEvidence": False,
        "countsAsRemoteFreshnessEvidence": False,
    }
    envelope["envelopeSha256"] = canonical_sha256(envelope)
    validation = validate_readonly_preflight_envelope(envelope)
    envelope["status"] = validation["status"]
    envelope["failureCodes"] = validation["failureCodes"]
    return envelope


def validate_readonly_preflight_envelope(envelope: dict[str, Any]) -> dict[str, Any]:
    """Validate evidence shape without reading a repository or calling Git."""

    failures: list[str] = []
    if not isinstance(envelope, dict):
        return {"status": "fail", "failureCodes": ["fail-envelope-shape"]}
    normalized = copy.deepcopy(envelope)
    for derived_key in ("status", "failureCodes"):
        normalized.pop(derived_key, None)
    required = {
        "schema", "id", "scenarioId", "runId", "repositoryWorktreeLocator", "events",
        "snapshotExactEquality", "dirtyOwnership", "taskDependsOnCurrentDirtyState",
        "approval", "execution", "retryAttempted", "writeAttempted",
        "countsAsNativeApprovalEvidence", "countsAsCreationSafetyEvidence",
        "countsAsRemoteFreshnessEvidence", "envelopeSha256",
    }
    if set(normalized) != required:
        return {"status": "fail", "failureCodes": ["fail-envelope-shape"]}
    if normalized.get("schema") != 1 or normalized.get("id") != "git-readonly-preflight-envelope" or normalized.get("scenarioId") != SCENARIO_ID or not isinstance(normalized.get("runId"), str) or not normalized["runId"].strip():
        failures.append("fail-envelope-identity")
    body = copy.deepcopy(normalized)
    digest = body.pop("envelopeSha256")
    if digest != canonical_sha256(body):
        failures.append("fail-envelope-digest")
    events = normalized.get("events")
    if not isinstance(events, dict) or set(events) != {"before", "after"}:
        failures.append("fail-event-shape")
        events = {}
    else:
        before, after = events["before"], events["after"]
        for event in (before, after):
            if not isinstance(event, dict) or set(event) != {"sequence", "eventId", "startedAt", "completedAt", "evidenceSource", "snapshot", "snapshotSha256", "rawPorcelainEntries"}:
                failures.append("fail-event-shape")
                continue
            if event.get("evidenceSource") != EVIDENCE_SOURCE or event.get("snapshotSha256") != canonical_sha256(event.get("snapshot")) or event.get("rawPorcelainEntries") != event.get("snapshot", {}).get("statusEntries"):
                failures.append("fail-event-binding")
        if isinstance(before, dict) and isinstance(after, dict) and (before.get("sequence") != 1 or after.get("sequence") != 2 or before.get("eventId") != f"{normalized.get('runId')}:1" or after.get("eventId") != f"{normalized.get('runId')}:2"):
            failures.append("fail-independent-event-identity")
        if isinstance(before, dict) and isinstance(after, dict):
            try:
                if any(not isinstance(event.get(key), str) or not RFC3339.fullmatch(event[key]) for event in (before, after) for key in ("startedAt", "completedAt")):
                    raise ValueError("non-RFC3339 event time")
                before_started = datetime.fromisoformat(before["startedAt"].replace("Z", "+00:00"))
                before_completed = datetime.fromisoformat(before["completedAt"].replace("Z", "+00:00"))
                after_started = datetime.fromisoformat(after["startedAt"].replace("Z", "+00:00"))
                after_completed = datetime.fromisoformat(after["completedAt"].replace("Z", "+00:00"))
            except (KeyError, TypeError, ValueError):
                failures.append("fail-event-time-rfc3339")
            else:
                if any(value.tzinfo is None for value in (before_started, before_completed, after_started, after_completed)):
                    failures.append("fail-event-time-rfc3339")
                elif before_started > before_completed or after_started > after_completed or before_completed > after_started:
                    failures.append("fail-event-time-order")
        if isinstance(before, dict) and before.get("snapshot", {}).get("repository") != normalized.get("repositoryWorktreeLocator"):
            failures.append("fail-repository-locator-binding")
        if isinstance(after, dict) and after.get("snapshot", {}).get("repository") != normalized.get("repositoryWorktreeLocator"):
            failures.append("fail-repository-locator-binding")
        if isinstance(before, dict) and isinstance(after, dict):
            exact = before.get("snapshot") == after.get("snapshot")
            if normalized.get("snapshotExactEquality") is not exact:
                failures.append("fail-snapshot-equality-claim")
            if not exact:
                failures.append("blocked-concurrent-drift")
            for snapshot in (before.get("snapshot"), after.get("snapshot")):
                facts = snapshot.get("facts", {}) if isinstance(snapshot, dict) else {}
                if (not isinstance(snapshot, dict) or snapshot.get("freshness") not in {"none", "local-ref-only"} or not isinstance(facts, dict) or snapshot.get("freshness") != facts.get("remoteClaim") or facts.get("networkRefreshObserved") is not False):
                    failures.append("fail-readonly-freshness-binding")
    ownership = normalized.get("dirtyOwnership")
    before_snapshot = events.get("before", {}).get("snapshot", {}) if isinstance(events, dict) else {}
    expected_paths = before_snapshot.get("dirtyPaths", []) if isinstance(before_snapshot, dict) else []
    expected_ownership = _path_evidence(before_snapshot) if isinstance(before_snapshot, dict) else []
    if ownership != expected_ownership:
        failures.append("fail-dirty-ownership-coverage")
    if isinstance(ownership, list):
        for row in ownership:
            if not isinstance(row, dict) or set(row) != {"path", "ownerState", "rawPorcelainEntries"} or row.get("ownerState") != "unknown" or not isinstance(row.get("rawPorcelainEntries"), list):
                failures.append("hard-fail-dirty-ownership-promotion")
                break
    if normalized.get("taskDependsOnCurrentDirtyState") is not False:
        failures.append("hard-fail-task-dependency-promotion")
    if normalized.get("approval") != {"state": "not-requested", "evidenceSource": "not-observed"}:
        failures.append("hard-fail-approval-claim")
    if normalized.get("execution") != {"attempted": False, "evidenceSource": "not-observed"} or normalized.get("retryAttempted") is not False or normalized.get("writeAttempted") is not False:
        failures.append("hard-fail-write-or-retry-claim")
    if any(normalized.get(key) is not False for key in ("countsAsNativeApprovalEvidence", "countsAsCreationSafetyEvidence", "countsAsRemoteFreshnessEvidence")):
        failures.append("hard-fail-count-promotion")
    failures = list(dict.fromkeys(failures))
    if failures and failures != ["blocked-concurrent-drift"]:
        status = "fail"
    elif failures:
        status = "blocked-concurrent-drift"
    elif expected_paths:
        status = "preflight-observed-dirty-ownership-unbound"
    else:
        status = "preflight-observed-clean-ownership-not-applicable"
    return {"status": status, "failureCodes": failures}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("repository", type=Path)
    args = parser.parse_args()
    print(json.dumps(build_readonly_preflight_envelope(args.repository), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
