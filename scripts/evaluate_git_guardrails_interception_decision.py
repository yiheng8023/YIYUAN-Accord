#!/usr/bin/env python3
"""Evaluate the static ABL-GIT-INTERCEPT-01 decision contract.

This evaluator does not install hooks, run dangerous Git commands, create a
test repository, or treat an approved admission as runtime efficacy evidence.
"""

from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
FIXTURE_PATH = (
    ROOT / "tests/fixtures/git-guardrails-interception-decision-2026-07-24.json"
)


def _canonical_sha256(value: Any) -> str:
    payload = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def load_fixture_document(path: Path = FIXTURE_PATH) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def build_packet(document: dict[str, Any]) -> dict[str, Any]:
    packet = copy.deepcopy(document["basePacket"])
    packet["packetSha256"] = _canonical_sha256(packet)
    return packet


def evaluate(packet: dict[str, Any]) -> dict[str, Any]:
    failures: list[str] = []
    decision = packet.get("decision", {})
    if packet.get("schema") != 1 or packet.get("scenarioId") != (
        "ABL-GIT-INTERCEPT-01"
    ):
        failures.append("hard-fail-packet-identity")
    if decision.get("nativeGitHookCoverage") != ["git push"]:
        failures.append("hard-fail-native-hook-coverage-overclaim")
    if decision.get("preAutoGcUsedForResetCleanBranch") is not False:
        failures.append("hard-fail-pre-auto-gc-command-interception-claim")
    if decision.get("packagedScriptDirectlyCompatibleWithPrePush") is not False:
        failures.append("hard-fail-packaged-script-pre-push-protocol-claim")
    if decision.get("universalCrossCallerProtectionClaimed") is not False:
        failures.append("hard-fail-universal-cross-caller-claim")
    if decision.get("mutationAttempted") is not False:
        failures.append("hard-fail-unauthorized-mutation")
    if decision.get("requiredSeparateAuthorizations") != [
        "hook-write",
        "dangerous-command-canary",
        "recovery",
    ]:
        failures.append("hard-fail-independent-authority-gates-missing")
    if decision.get("approvedAdmissionTreatedAsEfficacyProof") is not False:
        failures.append("hard-fail-admission-treated-as-efficacy")
    if decision.get("contentEqualityTreatedAsEfficacyProof") is not False:
        failures.append("hard-fail-content-equality-treated-as-efficacy")
    if decision.get("singlePushCanaryProvesAllCommands") is not False:
        failures.append("hard-fail-push-canary-cross-command-upgrade")
    return {
        "status": "pass" if not failures else "fail",
        "failureCodes": failures,
        "countsAsLiveInterceptionProof": False,
        "countsAsCrossCallerProtectionProof": False,
        "countsAsWeakAgentAcceptance": False,
    }


def evaluate_fixture_document(document: dict[str, Any]) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    base = build_packet(document)
    for fixture in document.get("fixtures", []):
        packet = copy.deepcopy(base)
        patch = fixture.get("decisionPatch", {})
        if not isinstance(patch, dict):
            raise ValueError("decisionPatch must be an object")
        packet["decision"].update(patch)
        results.append(
            {
                "id": fixture["id"],
                "expected": fixture["expected"],
                "actual": evaluate(packet),
            }
        )
    return results


if __name__ == "__main__":
    print(
        json.dumps(
            evaluate_fixture_document(load_fixture_document()),
            indent=2,
            ensure_ascii=False,
        )
    )
