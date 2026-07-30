#!/usr/bin/env python3
"""Validate the additive receiver delta-ledger evidence record."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import sys
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
EVIDENCE_PATH = (
    ROOT
    / "registry/context-handoff-receiver-delta-ledger-evidence-2026-07-27.json"
)
FIXTURE_PATH = (
    ROOT
    / "tests/fixtures/context-handoff-receiver-delta-ledger-2026-07-27.json"
)
EXPECTED_EXECUTION_BOUNDARY = {
    "agentDispatchCount": 0,
    "modelCallCount": 0,
    "threadCreated": False,
    "remoteGitUsed": False,
    "hostConfigurationChanged": False,
}
EXPECTED_CLAIM_BOUNDARY = {
    "receiverRecoveryProved": False,
    "skillInvocationProved": False,
    "freshSessionProved": False,
    "losslessProved": False,
    "atomicityProved": False,
    "dirtyOwnershipProved": False,
    "agentsAdherenceProved": False,
    "weakAgentBehaviorProved": False,
    "crossHostBehaviorProved": False,
}
REQUIRED_CASE_IDS = {
    "exact-control",
    "single-critical-fact-omission",
    "single-critical-fact-value-change",
    "single-provenance-break",
    "accepted-stale-assertion",
    "unknown-stale-assertion",
    "unsupported-automatic-creation-claim",
    "repository-truth-field-drift",
    "packet-digest-drift",
    "artifact-digest-drift",
    "raw-response-digest-drift",
    "oracle-digest-drift",
    "source-manifest-digest-drift",
    "shared-git-before-digest-drift",
    "shared-git-after-digest-drift",
    "private-oracle-leak",
}


def _load_json(path: Path) -> dict[str, Any]:
    document = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(document, dict):
        raise RuntimeError(f"JSON document must be an object: {path}")
    return document


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate_registry_bindings(evidence: dict[str, Any]) -> None:
    if evidence.get("schema") != 1:
        raise RuntimeError("evidence schema drifted")
    if evidence.get("id") != "CTX-HANDOFF-RECEIVER-DELTA-LEDGER-01":
        raise RuntimeError("evidence identity drifted")
    if evidence.get("scenario") != "ABL-CTX-HANDOFF-01":
        raise RuntimeError("canonical scenario binding drifted")
    if evidence.get("mode") != "additive-parent-recomputed":
        raise RuntimeError("ledger mode drifted")
    if evidence.get("canonicalVerdictChanged") is not False:
        raise RuntimeError("ledger may not change the canonical verdict")
    if (
        evidence.get("canonicalScorer")
        != "scripts.evaluate_skill_ablation_batch_01_protocol.evaluate_context_raw_run"
    ):
        raise RuntimeError("canonical scorer identity drifted")

    bindings = evidence.get("sourceBindings")
    if not isinstance(bindings, list) or not bindings:
        raise RuntimeError("source bindings are missing")
    seen: set[str] = set()
    for binding in bindings:
        if not isinstance(binding, dict) or set(binding) != {
            "path",
            "bytes",
            "sha256",
            "role",
        }:
            raise RuntimeError("source binding shape drifted")
        relative = binding["path"]
        if not isinstance(relative, str) or relative in seen:
            raise RuntimeError("source binding identity drifted")
        seen.add(relative)
        path = ROOT / relative
        if not path.is_file():
            raise RuntimeError(f"bound source is missing: {relative}")
        if binding["bytes"] != path.stat().st_size:
            raise RuntimeError(f"bound source byte count drifted: {relative}")
        if binding["sha256"] != _sha256(path):
            raise RuntimeError(f"bound source digest drifted: {relative}")

    required_paths = {
        "scripts/evaluate_context_handoff_receiver_delta_ledger.py",
        "scripts/evaluate_skill_ablation_batch_01_protocol.py",
        "scripts/observe_git_snapshot.py",
        "tests/fixtures/context-handoff-receiver-delta-ledger-2026-07-27.json",
        "tests/test_context_handoff_receiver_delta_ledger.py",
        "docs/context-handoff-receiver-delta-ledger-evidence-2026-07-27.md",
        "scripts/validate_context_handoff_receiver_delta_ledger_evidence.py",
    }
    if seen != required_paths:
        raise RuntimeError("source binding coverage drifted")


def validate_fixture_and_boundaries(evidence: dict[str, Any]) -> None:
    fixture = _load_json(FIXTURE_PATH)
    cases = fixture.get("cases")
    if not isinstance(cases, list):
        raise RuntimeError("fixture cases are missing")
    case_ids = {
        item.get("id")
        for item in cases
        if isinstance(item, dict)
    }
    if case_ids != REQUIRED_CASE_IDS or len(cases) != len(REQUIRED_CASE_IDS):
        raise RuntimeError("fixture case coverage drifted")
    if fixture.get("executionBoundary") != EXPECTED_EXECUTION_BOUNDARY:
        raise RuntimeError("fixture execution boundary drifted")
    if evidence.get("executionBoundary") != EXPECTED_EXECUTION_BOUNDARY:
        raise RuntimeError("evidence execution boundary drifted")
    if evidence.get("claimBoundary") != EXPECTED_CLAIM_BOUNDARY:
        raise RuntimeError("evidence claim boundary drifted")

    coverage = evidence.get("deterministicCoverage")
    if not isinstance(coverage, dict):
        raise RuntimeError("deterministic coverage is missing")
    if coverage.get("fixtureCaseCount") != len(REQUIRED_CASE_IDS):
        raise RuntimeError("fixture case count drifted")
    if set(coverage.get("caseIds", [])) != REQUIRED_CASE_IDS:
        raise RuntimeError("recorded fixture identities drifted")
    if coverage.get("exactSetsCountsAndFailureCodesAsserted") is not True:
        raise RuntimeError("exact ledger assertion is not recorded")
    if coverage.get("canonicalRegressionKeptSeparate") is not True:
        raise RuntimeError("canonical regression separation is not recorded")


def run_focused_tests() -> dict[str, Any]:
    command = [
        sys.executable,
        "-B",
        "-m",
        "unittest",
        "tests.test_context_handoff_receiver_delta_ledger",
    ]
    completed = subprocess.run(
        command,
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    if completed.returncode != 0:
        detail = (completed.stdout + completed.stderr).strip()
        raise RuntimeError(f"focused ledger tests failed: {detail}")
    return {
        "command": "python -B -m unittest tests.test_context_handoff_receiver_delta_ledger",
        "status": "passed",
        "testMethods": 3,
        "fixtureCases": len(REQUIRED_CASE_IDS),
    }


def main() -> int:
    evidence = _load_json(EVIDENCE_PATH)
    validate_registry_bindings(evidence)
    validate_fixture_and_boundaries(evidence)
    focused = run_focused_tests()
    recorded = evidence.get("focusedVerification")
    if recorded != focused:
        raise RuntimeError("focused verification record drifted")
    print(
        json.dumps(
            {
                "status": "validated",
                "id": evidence["id"],
                "scenario": evidence["scenario"],
                "fixtureCases": len(REQUIRED_CASE_IDS),
                "focusedVerification": focused,
                "executionBoundary": EXPECTED_EXECUTION_BOUNDARY,
                "claimBoundary": EXPECTED_CLAIM_BOUNDARY,
            },
            indent=2,
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
