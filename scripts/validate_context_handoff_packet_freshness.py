#!/usr/bin/env python3
"""Fail-closed, read-only freshness check for one CTX-04/05 handoff packet.

This checks whether a packet is still tied to the repository state from which it
was built.  It does not create a thread, inspect a conversation, invoke a
loader, change configuration, refresh a remote, or establish receiver/model
behaviour.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any, Callable

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.build_context_continuation_trial_packet import (
    CONTRACT_PATH,
    ROOT,
    SOURCE_PATHS,
    build_contract_binding,
    build_critical_fact_oracle,
    build_thread_prompt,
    build_untrusted_assertions,
    collect_git_truth,
    collect_source_hashes,
)


CURRENT_STATUS = "packet-current-read-only-pre-dispatch"
BLOCKED_STATUS = "blocked-stale-packet-regenerate-required"
REMOTE_FRESHNESS_VALUES = {
    "local-refs-only-no-network-refresh",
    "no-upstream-no-network-refresh",
}
CLAIM_BOUNDARY = {
    "countsAsAtomicSnapshotProof": False,
    "countsAsFreshSessionProof": False,
    "countsAsLoaderInvocationProof": False,
    "countsAsActualModelOrReasoningProof": False,
    "countsAsAutomaticThreadCreationProof": False,
    "countsAsRemoteFreshnessProof": False,
    "countsAsReceiverRecoveryProof": False,
    "countsAsSourceSemanticFreshnessProof": False,
}
REPOSITORY_TRUTH_KEYS = {
    "repositoryRoot",
    "branch",
    "detachedHead",
    "head",
    "upstream",
    "aheadBehind",
    "statusPorcelainV1",
    "isDirty",
    "recentCommit",
    "worktreesPorcelain",
    "remotes",
    "remoteFreshness",
}


def _nonempty_text(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _hex_digest(value: Any, length: int) -> bool:
    return (
        isinstance(value, str)
        and len(value) == length
        and all(character in "0123456789abcdef" for character in value)
    )


def _git_oid(value: Any) -> bool:
    return _hex_digest(value, 40) or _hex_digest(value, 64)


def _string_list(value: Any) -> bool:
    return isinstance(value, list) and all(
        isinstance(item, str) for item in value
    )


def _repository_truth_shape_valid(value: Any) -> bool:
    if not isinstance(value, dict) or set(value) != REPOSITORY_TRUTH_KEYS:
        return False
    branch = value.get("branch")
    upstream = value.get("upstream")
    ahead_behind = value.get("aheadBehind")
    status = value.get("statusPorcelainV1")
    if ahead_behind is not None and (
        not isinstance(ahead_behind, dict)
        or set(ahead_behind) != {"ahead", "behind"}
        or any(
            isinstance(ahead_behind.get(key), bool)
            or not isinstance(ahead_behind.get(key), int)
            or ahead_behind.get(key) < 0
            for key in ("ahead", "behind")
        )
    ):
        return False
    return (
        _nonempty_text(value.get("repositoryRoot"))
        and (branch is None or _nonempty_text(branch))
        and isinstance(value.get("detachedHead"), bool)
        and value.get("detachedHead") is (branch is None)
        and _git_oid(value.get("head"))
        and (upstream is None or _nonempty_text(upstream))
        and ((upstream is None) is (ahead_behind is None))
        and _string_list(status)
        and isinstance(value.get("isDirty"), bool)
        and value.get("isDirty") is bool(status)
        and _nonempty_text(value.get("recentCommit"))
        and _string_list(value.get("worktreesPorcelain"))
        and _string_list(value.get("remotes"))
        and _nonempty_text(value.get("remoteFreshness"))
    )


def canonical_sha256(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def _contract() -> dict[str, Any]:
    return json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))


def validate_packet_freshness(
    packet: dict[str, Any],
    *,
    root: Path = ROOT,
    git_observer: Callable[[Path], dict[str, Any]] = collect_git_truth,
    source_observer: Callable[[Path], dict[str, str]] = collect_source_hashes,
) -> dict[str, Any]:
    """Return current only when the entire packet remains exact and local-only."""

    failures: list[str] = []
    if not isinstance(packet, dict):
        failures.append("fail-packet-shape")
        packet = {}
    expected_top = {
        "schema", "id", "generatedFrom", "contractBinding", "arm",
        "sendToThread", "oraclePrivate", "authorityBoundary",
    }
    if set(packet) != expected_top or packet.get("schema") != 1:
        failures.append("fail-packet-shape")

    contract = _contract()
    arms = {item["id"]: item for item in contract["trialArms"]}
    arm = packet.get("arm")
    arm_id = arm.get("id") if isinstance(arm, dict) else None
    if arm_id not in arms or arm != arms.get(arm_id) or packet.get("id") != f"context-continuation-live-packet-{arm_id}":
        failures.append("fail-arm-binding")
    if packet.get("generatedFrom") != "read-only-local-repository-state":
        failures.append("fail-packet-origin")
    if packet.get("contractBinding") != build_contract_binding():
        failures.append("fail-contract-binding")
    if not isinstance(packet.get("sendToThread"), dict) or set(packet["sendToThread"]) != {"prompt"} or not isinstance(packet["sendToThread"].get("prompt"), str) or not packet["sendToThread"]["prompt"].strip():
        failures.append("fail-public-packet-shape")
    if packet.get("authorityBoundary") != {
        "threadCreationAuthorizedByPacket": False,
        "repositoryMutationAuthorized": False,
        "networkRefreshAuthorizedByPacket": False,
        "cleanupAuthorizedByPacket": False,
    }:
        failures.append("hard-fail-authority-promotion")

    oracle = packet.get("oraclePrivate")
    expected_oracle_keys = {
        "repositoryTruth", "sourceFileSha256", "criticalFactIdsExpected", "criticalFactValuesExpected",
        "staleFactIdsInjected", "optionalFactIds", "untrustedAssertions",
    }
    if not isinstance(oracle, dict) or set(oracle) != expected_oracle_keys:
        failures.append("fail-private-oracle-shape")
        oracle = {}
    expected_oracle = contract.get("oracle", {})
    if oracle.get("criticalFactIdsExpected") != expected_oracle.get("criticalFactIds") or oracle.get("staleFactIdsInjected") != expected_oracle.get("staleFactIds") or oracle.get("optionalFactIds") != expected_oracle.get("optionalFactIds"):
        failures.append("fail-oracle-identity-binding")
    packet_truth = oracle.get("repositoryTruth")
    packet_truth_shape_valid = _repository_truth_shape_valid(packet_truth)
    if not packet_truth_shape_valid:
        failures.append("fail-packet-repository-truth-shape")
    elif (
        oracle.get("criticalFactValuesExpected")
        != build_critical_fact_oracle(packet_truth)
    ):
        failures.append("fail-critical-fact-oracle-binding")
    assertions = oracle.get("untrustedAssertions")
    assertions_match = (
        packet_truth_shape_valid
        and assertions == build_untrusted_assertions(packet_truth)
    )
    if not assertions_match:
        failures.append("fail-untrusted-assertion-binding")
    prompt = (
        packet["sendToThread"].get("prompt")
        if isinstance(packet.get("sendToThread"), dict)
        else None
    )
    if (
        arm_id not in arms
        or not assertions_match
        or prompt != build_thread_prompt(arm_id, contract, assertions)
    ):
        failures.append("fail-public-prompt-binding")

    expected_hash_keys = set(SOURCE_PATHS)
    packet_hashes = oracle.get("sourceFileSha256")
    if (
        not isinstance(packet_hashes, dict)
        or set(packet_hashes) != expected_hash_keys
        or any(not _hex_digest(value, 64) for value in packet_hashes.values())
    ):
        failures.append("fail-source-manifest-shape")
        packet_hashes = {}
    try:
        current_hashes = source_observer(root)
    except Exception:
        current_hashes = {}
        failures.append("fail-current-source-observation")
    if not isinstance(current_hashes, dict):
        current_hashes = {}
        failures.append("fail-current-source-observation")
    if (
        set(current_hashes) != expected_hash_keys
        or any(not _hex_digest(value, 64) for value in current_hashes.values())
    ):
        failures.append("fail-current-source-manifest-shape")
    elif packet_hashes != current_hashes:
        failures.append("blocked-source-hash-drift")

    try:
        current_truth = git_observer(root)
    except Exception:
        current_truth = {}
        failures.append("fail-current-git-observation")
    if not isinstance(current_truth, dict):
        current_truth = {}
        failures.append("fail-current-git-observation")
    current_truth_shape_valid = _repository_truth_shape_valid(current_truth)
    if not current_truth_shape_valid:
        failures.append("fail-current-repository-truth-shape")
    if (
        not packet_truth_shape_valid
        or packet_truth.get("remoteFreshness") not in REMOTE_FRESHNESS_VALUES
    ):
        failures.append("fail-packet-remote-freshness-boundary")
    if (
        not current_truth_shape_valid
        or current_truth.get("remoteFreshness") not in REMOTE_FRESHNESS_VALUES
    ):
        failures.append("fail-current-remote-freshness-boundary")
    if packet_truth_shape_valid and current_truth_shape_valid and packet_truth != current_truth:
        failures.append("blocked-repository-truth-drift")

    failures = list(dict.fromkeys(failures))
    return {
        "schema": 1,
        "id": "context-handoff-packet-freshness",
        "status": CURRENT_STATUS if not failures else BLOCKED_STATUS,
        "failureCodes": failures,
        "packetSha256": canonical_sha256(packet),
        "currentRepositoryTruthSha256": canonical_sha256(current_truth),
        "currentSourceManifestSha256": canonical_sha256(current_hashes),
        "claimBoundary": dict(CLAIM_BOUNDARY),
        "cohortBoundary": {
            "atomicSnapshotProved": False,
            "mustRevalidateInsideAuthorizedCreationCriticalSection": True,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("packet", type=Path)
    args = parser.parse_args()
    packet = json.loads(args.packet.read_text(encoding="utf-8"))
    print(json.dumps(validate_packet_freshness(packet), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
