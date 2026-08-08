#!/usr/bin/env python3
"""Replay fail-closed mutations for the Harness decision-packet core PoC."""

from __future__ import annotations

import copy
import json
from pathlib import Path
import shutil
import tempfile
from typing import Callable

from scripts.harness_decision_packet import (
    DecisionPacketError,
    build_decision_packet,
    canonical_sha256,
    load_authority_bundle,
    validate_decision_packet,
)


MUTATION_CASE_IDS = [
    "unknown-scenario",
    "semantic-authority-id-drift",
    "original-evidence-missing",
    "original-evidence-digest-drift",
    "route-class-removed",
    "unassessed-route-promoted",
    "residual-route-promoted",
    "portfolio-selected-route",
    "claim-boundary-promoted",
    "fallback-order-drift",
    "deprecated-routing-restored",
    "task-time-route-selected",
    "historical-authority-overrides-current",
    "portable-core-dependency-promoted",
]

EXPECTED_ERROR_CODES = {
    "unknown-scenario": "unknown-scenario",
    "semantic-authority-id-drift": "semantic-authority-id-mismatch",
    "original-evidence-missing": "evidence-source-missing",
    "original-evidence-digest-drift": "evidence-source-digest-drift",
    "route-class-removed": "route-class-coverage-incomplete",
    "unassessed-route-promoted": "unassessed-route-promotion",
    "residual-route-promoted": "residual-gap-promotion",
    "portfolio-selected-route": "portfolio-selected-route",
    "claim-boundary-promoted": "claim-boundary-promotion",
    "fallback-order-drift": "fallback-order-drift",
    "deprecated-routing-restored": "deprecated-routing-authority-promotion",
    "task-time-route-selected": "task-time-route-selection",
    "historical-authority-overrides-current": "historical-authority-promotion",
    "portable-core-dependency-promoted": "portable-core-dependency-promotion",
}


def _seal(packet: dict[str, object]) -> None:
    body = {key: value for key, value in packet.items() if key != "packetSha256"}
    packet["packetSha256"] = canonical_sha256(body)


def _mutated_packet(
    packet: dict[str, object],
    mutate: Callable[[dict[str, object]], None],
) -> dict[str, object]:
    result = copy.deepcopy(packet)
    mutate(result)
    _seal(result)
    return result


def _bound_records(bundle: dict[str, object]) -> list[dict[str, object]]:
    return [
        bundle["semanticAuthority"],
        bundle["coverage"],
        bundle["scheduler"],
        bundle["acceptance"],
        *bundle["sourceEvidence"],
    ]


def _copy_records(
    root: Path,
    temporary_root: Path,
    records: list[dict[str, object]],
) -> None:
    for record in records:
        relative = Path(record["path"])
        destination = temporary_root / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(root / relative, destination)


def _complete_task_time_request(request: dict[str, object]) -> None:
    request["evidenceLane"] = "task-time"
    request["taskBinding"] = {
        "taskId": "mutation.task-time-route-selected",
        "goal": "Verify that v1 does not select a live route.",
        "target": "GEN-RESEARCH-01",
        "verificationSurface": "fail-closed mutation matrix",
    }
    request["currentCapabilityGap"] = {
        "requiredCapability": "source-bound route evaluation",
        "observedLimitation": "no validated route decision exists",
        "evidencePaths": ["tests/fixtures/gap-evidence.json"],
    }
    request["observedAvailability"] = {
        "asOf": "2026-08-08T00:00:00Z",
        "host": "codex-desktop",
        "availableRouteClasses": ["N", "C", "H"],
        "evidencePaths": ["tests/fixtures/live-availability.json"],
    }
    request["activationAuthority"] = {
        "evidencePath": "tests/fixtures/authority.json",
        "scope": "evaluate-only",
    }


def run_failure_matrix(root: Path) -> list[dict[str, str]]:
    """Run all fourteen deterministic mutations and return their exact outcomes."""

    request_path = root / "tests/fixtures/harness-decision-request-gen-research-01.json"
    request = json.loads(request_path.read_text(encoding="utf-8"))
    packet = build_decision_packet(root, request)
    bundle = load_authority_bundle(root, request)

    def validate_mutation(mutate: Callable[[dict[str, object]], None]) -> None:
        validate_decision_packet(root, _mutated_packet(packet, mutate))

    def original_evidence_missing() -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            temporary_root = Path(temporary_directory)
            _copy_records(root, temporary_root, _bound_records(bundle)[:4])
            validate_decision_packet(temporary_root, packet)

    def original_evidence_digest_drift() -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            temporary_root = Path(temporary_directory)
            _copy_records(root, temporary_root, _bound_records(bundle))
            evidence_path = temporary_root / bundle["sourceEvidence"][0]["path"]
            evidence_path.write_bytes(evidence_path.read_bytes() + b"\n")
            validate_decision_packet(temporary_root, packet)

    actions: dict[str, Callable[[], None]] = {
        "unknown-scenario": lambda: validate_mutation(
            lambda value: value["request"].__setitem__("scenarioId", "GEN-UNKNOWN-01")
        ),
        "semantic-authority-id-drift": lambda: validate_mutation(
            lambda value: value["request"].__setitem__(
                "expectedSemanticAuthorityId", "stale-authority"
            )
        ),
        "original-evidence-missing": original_evidence_missing,
        "original-evidence-digest-drift": original_evidence_digest_drift,
        "route-class-removed": lambda: validate_mutation(
            lambda value: value["routeCoverage"].pop("O")
        ),
        "unassessed-route-promoted": lambda: validate_mutation(
            lambda value: value["routeCoverage"]["O"].__setitem__(
                "state", "represented-source-static"
            )
        ),
        "residual-route-promoted": lambda: validate_mutation(
            lambda value: value["routeCoverage"]["R"].__setitem__(
                "state", "represented-residual-gap"
            )
        ),
        "portfolio-selected-route": lambda: validate_mutation(
            lambda value: value.__setitem__("selectedRoute", "N")
        ),
        "claim-boundary-promoted": lambda: validate_mutation(
            lambda value: value["claimBoundary"].__setitem__("liveDomainValueProved", True)
        ),
        "fallback-order-drift": lambda: validate_mutation(
            lambda value: value.__setitem__("fallbackOrder", ["C", "N", "H"])
        ),
        "deprecated-routing-restored": lambda: validate_mutation(
            lambda value: value["projectionBoundary"].__setitem__(
                "legacyRoutingIsCurrentAuthority", True
            )
        ),
        "task-time-route-selected": lambda: validate_mutation(
            lambda value: (
                _complete_task_time_request(value["request"]),
                value.__setitem__("selectedRoute", "N"),
            )
        ),
        "historical-authority-overrides-current": lambda: validate_mutation(
            lambda value: value["authorityBinding"]["coverage"].__setitem__(
                "id", "historical-coverage-authority"
            )
        ),
        "portable-core-dependency-promoted": lambda: validate_mutation(
            lambda value: value["projectionBoundary"].__setitem__(
                "portableCoreDependsOnCcSwitch", True
            )
        ),
    }

    results: list[dict[str, str]] = []
    for case_id in MUTATION_CASE_IDS:
        expected_code = EXPECTED_ERROR_CODES[case_id]
        try:
            actions[case_id]()
        except DecisionPacketError as exc:
            results.append(
                {
                    "caseId": case_id,
                    "status": "rejected" if exc.code == expected_code else "wrong-error",
                    "expectedCode": expected_code,
                    "observedCode": exc.code,
                }
            )
        else:
            results.append(
                {
                    "caseId": case_id,
                    "status": "accepted",
                    "expectedCode": expected_code,
                    "observedCode": "none",
                }
            )
    return results
