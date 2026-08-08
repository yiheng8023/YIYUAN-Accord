#!/usr/bin/env python3
"""Replay fail-closed mutations for the Harness decision-packet core PoC."""

from __future__ import annotations

import copy
import json
from pathlib import Path
import shutil
import tempfile
from typing import Callable

try:
    from .harness_decision_packet import (
        DecisionPacketError,
        build_decision_packet,
        canonical_sha256,
        load_authority_bundle,
        serialize_decision_packet,
        validate_decision_packet,
    )
except ImportError:  # Direct script execution.
    from harness_decision_packet import (
        DecisionPacketError,
        build_decision_packet,
        canonical_sha256,
        load_authority_bundle,
        serialize_decision_packet,
        validate_decision_packet,
    )


ROOT = Path(__file__).resolve().parent.parent
EVIDENCE_PATH = Path("registry/harness-decision-packet-core-poc-2026-08-08.json")
EXPECTED_PACKET_PATH = Path("tests/fixtures/harness-decision-packet-gen-research-01.json")
DOCUMENTATION_PATH = Path(
    "docs/strategy/HARNESS-DECISION-PACKET-CORE-POC-2026-08-08.md"
)
REQUEST_PATH = Path("tests/fixtures/harness-decision-request-gen-research-01.json")


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


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def _load_object(root: Path, relative: Path) -> dict[str, object]:
    value = json.loads((root / relative).read_text(encoding="utf-8"))
    _require(isinstance(value, dict), f"Expected JSON object at {relative.as_posix()}")
    return value


def validate_repository_record(root: Path = ROOT) -> dict[str, object]:
    """Replay the checked packet, failures, projections, and narrow evidence limits."""

    record = _load_object(root, EVIDENCE_PATH)
    _require(
        record.get("schema") == 1
        and record.get("id") == "harness-decision-packet-core-poc-2026-08-08"
        and record.get("date") == "2026-08-08"
        and record.get("status")
        == "verified-zero-model-source-bound-decision-packet-mechanism-only"
        and record.get("design")
        == "docs/superpowers/specs/2026-08-08-harness-decision-packet-core-design.md"
        and record.get("documentation") == DOCUMENTATION_PATH.as_posix()
        and record.get("requestFixture") == REQUEST_PATH.as_posix()
        and record.get("expectedPacketFixture") == EXPECTED_PACKET_PATH.as_posix(),
        "Decision-packet evidence identity or path binding drifted",
    )
    for relative in (
        Path(record["design"]),
        DOCUMENTATION_PATH,
        REQUEST_PATH,
        EXPECTED_PACKET_PATH,
    ):
        _require((root / relative).is_file(), f"Decision-packet bound file missing: {relative}")

    request = _load_object(root, REQUEST_PATH)
    expected_packet = _load_object(root, EXPECTED_PACKET_PATH)
    rebuilt = build_decision_packet(root, request)
    validate_decision_packet(root, expected_packet)
    _require(
        serialize_decision_packet(rebuilt)
        == (root / EXPECTED_PACKET_PATH).read_bytes(),
        "Decision-packet fixture is not a byte-stable rebuild",
    )
    _require(
        expected_packet.get("packetSha256") == record.get("packetSha256"),
        "Decision-packet evidence digest drifted",
    )

    authority_bindings = record.get("authorityBindings", {})
    expected_bindings = expected_packet.get("authorityBinding", {})
    _require(
        all(
            authority_bindings.get(key) == expected_bindings.get(key)
            for key in ("semanticAuthority", "coverage", "scheduler", "acceptance")
        ),
        "Decision-packet current authority bindings drifted",
    )
    source_evidence = expected_packet.get("sourceEvidence", [])
    _require(
        len(source_evidence) == 1
        and authority_bindings.get("originalEvidence")
        == {
            key: source_evidence[0][key]
            for key in ("path", "id", "sha256")
        },
        "Decision-packet original evidence binding drifted",
    )
    scenario = record.get("scenario", {})
    packet_routes = expected_packet.get("routeCoverage", {})
    _require(
        scenario.get("id") == "GEN-RESEARCH-01"
        and scenario.get("fallbackOrder") == ["N", "C", "H"]
        and scenario.get("selectedRoute") is None
        and scenario.get("routeStates")
        == {route: packet_routes[route]["state"] for route in ("N", "O", "E", "C", "H", "R")},
        "Decision-packet route-state evidence drifted",
    )

    failure_results = run_failure_matrix(root)
    _require(
        [item["caseId"] for item in failure_results] == MUTATION_CASE_IDS
        and all(item["status"] == "rejected" for item in failure_results),
        "Decision-packet failure matrix did not fail closed",
    )
    _require(
        record.get("mutationResults")
        == [
            {"caseId": case_id, "expectedErrorCode": EXPECTED_ERROR_CODES[case_id]}
            for case_id in MUTATION_CASE_IDS
        ],
        "Decision-packet recorded failure inventory drifted",
    )
    counters = record.get("executionCounters", {})
    _require(
        set(counters)
        == {
            "models",
            "candidates",
            "plugins",
            "managers",
            "accounts",
            "consumers",
            "installs",
            "enablements",
            "publications",
        }
        and all(value == 0 for value in counters.values()),
        "Decision-packet execution counters were promoted",
    )
    claims = record.get("claimBoundary", {})
    _require(
        set(claims)
        == {
            "naturalLanguageInterpretationProved",
            "invocationProved",
            "instructionDeliveryProved",
            "behaviorProved",
            "valueProved",
            "portabilityProved",
            "productionProved",
            "releaseEligibilityProved",
            "residualGapProved",
        }
        and all(value is False for value in claims.values()),
        "Decision-packet claim boundary was promoted",
    )
    authority_boundary = record.get("authorityBoundary", {})
    _require(
        authority_boundary and all(value is False for value in authority_boundary.values()),
        "Decision-packet side-effect authority was promoted",
    )

    acceptance = _load_object(root, Path("registry/program-acceptance-map.json"))
    criteria = acceptance.get("acceptanceCriteria", [])
    criterion = next(
        item
        for item in criteria
        if item.get("id") == "acceptance.decision-ready-consumer-projection"
    )
    assessments = [item.get("assessment") for item in criteria]
    _require(
        criterion.get("assessment") == "partial"
        and "evidence.harness-decision-packet-core-poc-2026-08-08"
        in criterion.get("evidenceIds", [])
        and record.get("acceptance")
        == {
            "id": "acceptance.decision-ready-consumer-projection",
            "assessment": "partial",
            "inventory": {
                "verified": assessments.count("verified"),
                "partial": assessments.count("partial"),
                "planned": assessments.count("planned"),
            },
        }
        and assessments.count("verified") == 46
        and assessments.count("partial") == 15
        and assessments.count("planned") == 0,
        "Decision-packet acceptance boundary or 46/15/0 inventory drifted",
    )

    authority = _load_object(root, Path("registry/skill-portfolio-current-authority.json"))
    projection = _load_object(
        root, Path("registry/portfolio-tasktime-projection-contract-2026-08-06.json")
    )
    expected_core_binding = {
        "design": "docs/superpowers/specs/2026-08-08-harness-decision-packet-core-design.md",
        "evidence": EVIDENCE_PATH.as_posix(),
        "status": "verified-zero-model-source-bound-decision-packet-mechanism-only",
        "primaryConsumer": "agent-or-harness",
        "naturalLanguageInterpretationProved": False,
        "liveRouteSelectionProved": False,
        "behaviorOrValueProved": False,
        "portableCoreDependsOnPluginOrManager": False,
    }
    _require(
        authority.get("decisionPacketCore") == expected_core_binding
        and projection.get("sourceBindings", {}).get("decisionPacketCore")
        == expected_core_binding,
        "Decision-packet current semantic projection binding drifted",
    )
    closeout = _load_object(
        root,
        Path("registry/program-final-closeout-readiness-reconciliation-2026-07-28.json"),
    )
    closeout_core = closeout.get("decisionPacketCore", {})
    _require(
        closeout.get("sourceBindings", {}).get("harnessDecisionPacketCorePoc")
        == EVIDENCE_PATH.as_posix()
        and closeout.get("acceptanceSnapshot")
        == {
            "totalCriteria": 61,
            "verified": 46,
            "partial": 15,
            "planned": 0,
            "other": 0,
            "allCriteriaVerified": False,
        }
        and closeout.get("closeoutDecision", {}).get("goalComplete") is False
        and closeout_core.get("selectedRoute") is None
        and closeout_core.get("mutationCasesRejected") == 14
        and all(value == 0 for value in closeout_core.get("executionCounters", {}).values())
        and all(value is False for value in closeout_core.get("claimBoundary", {}).values()),
        "Decision-packet closeout projection drifted or overclaimed",
    )

    human_markers = {
        "README.md": [
            "GEN-RESEARCH-01",
            "14 injected promotions fail closed",
            "selectedRoute` stays",
            "not execution or value proof",
        ],
        "README.zh-CN.md": [
            "GEN-RESEARCH-01",
            "14 项注入式越权全部 fail closed",
            "selectedRoute` 保持",
            "不是执行或价值证明",
        ],
        "docs/strategy/RESEARCH-AND-POC-PLAN.md": [
            "Harness decision-packet core PoC",
            "Fourteen mutations",
            "selected route remains null",
            "46 verified / 15 partial / 0 planned",
        ],
        "docs/operations/CURRENT-GOAL-MODE-PROMPT.md": [
            "Current decision-packet mechanism boundary",
            "all fourteen bounded mutations",
            "selectedRoute` null",
            "46 verified / 15 partial / 0",
        ],
        "docs/operations/CONTINUATION.md": [
            "Harness decision-packet core PoC checkpoint",
            "Fourteen independent mutations fail closed",
            "selectedRoute: null",
            "46 verified / 15 partial / 0 planned",
        ],
        DOCUMENTATION_PATH.as_posix(): [
            "Fourteen independent mutations fail closed",
            "selectedRoute` remains `null",
            "pure, zero-model mechanism evidence",
            "46 verified / 15 partial / 0",
        ],
    }
    for relative, markers in human_markers.items():
        normalized = " ".join((root / relative).read_text(encoding="utf-8").split())
        _require(
            all(marker in normalized for marker in markers),
            f"Decision-packet human projection drifted: {relative}",
        )
    return record


def main() -> int:
    record = validate_repository_record(ROOT)
    print(
        "Harness decision-packet core PoC verified: "
        f"{len(record['mutationResults'])} fail-closed mutations."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
