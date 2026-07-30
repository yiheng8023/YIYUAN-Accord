#!/usr/bin/env python3
"""Validate the bounded current TDD execution-readiness reconciliation."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
RECONCILIATION_PATH = Path(
    "registry/"
    "human-ai-collaboration-tdd-current-execution-readiness-"
    "reconciliation-2026-07-27.json"
)
DOCUMENTATION_PATH = Path(
    "docs/strategy/"
    "HUMAN-AI-COLLABORATION-TDD-CURRENT-EXECUTION-READINESS-"
    "RECONCILIATION-2026-07-27.md"
)
PROTOCOL_PATH = Path(
    "registry/"
    "human-ai-collaboration-tdd-noncomparative-treatment-diagnostic-"
    "protocol-2026-07-26.json"
)
PREFLIGHT_PATH = Path(
    "registry/"
    "human-ai-collaboration-tdd-noncomparative-treatment-diagnostic-"
    "source-governance-preflight-2026-07-26.json"
)
MATT_PATH = Path(
    "registry/"
    "human-ai-collaboration-tdd-matt-current-diagnostic-only-"
    "admission-decision-2026-07-27.json"
)
SUPERPOWERS_PATH = Path(
    "registry/"
    "human-ai-collaboration-tdd-superpowers-620-diagnostic-only-"
    "admission-decision-2026-07-27.json"
)
LEDGER_EVIDENCE_PATH = Path(
    "registry/"
    "human-ai-collaboration-tdd-noncomparative-dispatch-identity-"
    "ledger-poc-evidence-2026-07-26.json"
)
ADAPTER_EVIDENCE_PATH = Path(
    "registry/"
    "human-ai-collaboration-tdd-noncomparative-dispatch-authorization-"
    "adapter-poc-evidence-2026-07-26.json"
)
RUNNER_PREFLIGHT_EVIDENCE_PATH = Path(
    "registry/"
    "human-ai-collaboration-tdd-noncomparative-runner-preflight-"
    "poc-evidence-2026-07-26.json"
)
FORMAL_EVIDENCE_PATH = Path(
    "registry/"
    "human-ai-collaboration-tdd-formal-runner-first-attempt-"
    "evidence-2026-07-26.json"
)
ADAPTER_SOURCE_PATH = Path(
    "scripts/"
    "human_ai_collaboration_tdd_noncomparative_dispatch_"
    "authorization_adapter.py"
)
FORMAL_RUNNER_PATH = Path(
    "scripts/run_human_ai_collaboration_tdd_formal_trial.py"
)

EXPECTED_SOURCE_BINDINGS = {
    "registry/human-ai-collaboration-tdd-noncomparative-treatment-diagnostic-protocol-2026-07-26.json":
        "80086509febcf37665b301ed43d856ce087a30349ca85f7be81a1dfb47bf12f1",
    "registry/human-ai-collaboration-tdd-noncomparative-treatment-diagnostic-source-governance-preflight-2026-07-26.json":
        "cc6f265eeca164b3f26cfa020976776242a4f95a06deff9a9e88b4167f4866cd",
    "registry/human-ai-collaboration-tdd-exact-candidate-admission-gap-audit-2026-07-26.json":
        "7b9371ef23de7dce3e3c96ffc4595796e519c30736705012b05b467b3d7efef1",
    "registry/human-ai-collaboration-tdd-matt-current-diagnostic-only-admission-decision-2026-07-27.json":
        "8b12683f86dcecffac5cfd398061f194ccc08578b04247e7631c03a922b131e4",
    "registry/human-ai-collaboration-tdd-superpowers-620-diagnostic-only-admission-decision-2026-07-27.json":
        "aa763b96a461b1f6a85d4d8329612eee536923c04bf7ba48ac057b75e83c2376",
    "registry/human-ai-collaboration-tdd-noncomparative-dispatch-identity-ledger-poc-evidence-2026-07-26.json":
        "e3bed94b75d790b7a18f965b7c8c8e5216205e80544af87df332a4bfd13a0429",
    "registry/human-ai-collaboration-tdd-noncomparative-dispatch-authorization-adapter-poc-evidence-2026-07-26.json":
        "ef0c43e50ac7be308ff4cdf5d3ad6f190f81b2459b920f185c02131d21372fcd",
    "registry/human-ai-collaboration-tdd-noncomparative-runner-preflight-poc-evidence-2026-07-26.json":
        "3565b6bc8b9c9ffa17fff53fc6f12eecb08e725fa4c3fed78ff95c9ee6654e5d",
    "registry/human-ai-collaboration-tdd-formal-runner-first-attempt-evidence-2026-07-26.json":
        "6f69df5d3b8d5acb757b2b6cd9aa0a3f1748ccd6335d38deecc95bd041460521",
}

EXPECTED_ARTIFACTS = {
    "scripts/human_ai_collaboration_tdd_noncomparative_dispatch_identity_ledger.py":
        (49057, "c8625d78bd3ae93aea6c7a41eed5981670797f9d49be9a3e1d5124be7103e1e6"),
    "scripts/human_ai_collaboration_tdd_noncomparative_dispatch_authorization_adapter.py":
        (14624, "a146a95c3e37827e9969cc0bcde2652c01547e19ad44ae2deadad398d5cc454c"),
    "scripts/human_ai_collaboration_tdd_noncomparative_runner_preflight.py":
        (8640, "d3aeb2508b7214ce1786f88f79987b0d677e9d8f4c47166cfef453f5f90e6f15"),
    "tests/test_human_ai_collaboration_tdd_noncomparative_resource_contract.py":
        (18829, "1837a335898646c0835273b121e7e658fe3d5481f849e97eae9352f894a27e12"),
    "tests/test_human_ai_collaboration_tdd_noncomparative_preconstruction_transaction.py":
        (7954, "2604a430ea0a2aa73d5a1bb77ba54a4a45c70dbc2886d8330a0901950e745e33"),
    "scripts/run_human_ai_collaboration_tdd_formal_trial.py":
        (24396, "e3550b937cfd301a0bd2468c21fe67582a0b3ebceef0f61fbbeccfa0de4e4f80"),
}

EXPECTED_GATE_STATUSES = {
    "gate.exact-candidate-static-admission":
        "satisfied-for-both-candidates",
    "gate.protocol-execution-eligibility": "blocked",
    "gate.dispatch-source-and-toolchain-freshness": "blocked",
    "gate.dispatch-authorization-envelope": "blocked",
    "gate.dispatch-identity-ledger":
        "offline-poc-satisfied-live-blocked",
    "gate.preconstruction-atomicity":
        "offline-poc-partial-live-blocked",
    "gate.resource-ownership-and-cleanup":
        "offline-poc-partial-live-blocked",
    "gate.diagnostic-runner-successor": "blocked",
    "gate.current-human-and-runtime-authority": "blocked",
}


def _load(path: Path) -> dict[str, Any]:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def _sha256(path: Path) -> str:
    return hashlib.sha256((ROOT / path).read_bytes()).hexdigest()


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def _unique_rows(
    rows: object,
    key: str,
    label: str,
) -> dict[str, dict[str, Any]]:
    _require(isinstance(rows, list), f"{label} must be a list")
    result: dict[str, dict[str, Any]] = {}
    for row in rows:
        _require(isinstance(row, dict), f"{label} row must be an object")
        value = row.get(key)
        _require(
            isinstance(value, str) and value,
            f"{label} {key} is invalid",
        )
        _require(value not in result, f"{label} duplicates {value}")
        result[value] = row
    return result


def _validate_bindings(document: dict[str, Any]) -> None:
    bindings = _unique_rows(
        document.get("sourceBindings"),
        "path",
        "source binding",
    )
    _require(
        set(bindings) == set(EXPECTED_SOURCE_BINDINGS),
        "source binding set drifted",
    )
    for path_text, expected in EXPECTED_SOURCE_BINDINGS.items():
        path = Path(path_text)
        _require(
            bindings[path_text].get("sha256") == expected,
            f"bound SHA-256 drifted for {path_text}",
        )
        _require(
            _sha256(path) == expected,
            f"source bytes drifted for {path_text}",
        )


def _validate_artifacts(document: dict[str, Any]) -> None:
    rows = _unique_rows(
        document.get("currentArtifactIdentities"),
        "path",
        "artifact identity",
    )
    _require(
        set(rows) == set(EXPECTED_ARTIFACTS),
        "artifact identity set drifted",
    )
    for path_text, (size, digest) in EXPECTED_ARTIFACTS.items():
        path = ROOT / path_text
        row = rows[path_text]
        _require(path.is_file(), f"artifact is missing: {path_text}")
        _require(path.stat().st_size == size, f"artifact size drifted: {path_text}")
        _require(row.get("bytes") == size, f"recorded size drifted: {path_text}")
        _require(_sha256(Path(path_text)) == digest, f"artifact bytes drifted: {path_text}")
        _require(row.get("sha256") == digest, f"recorded digest drifted: {path_text}")


def _validate_admissions(
    document: dict[str, Any],
    matt: dict[str, Any],
    superpowers: dict[str, Any],
) -> None:
    rows = _unique_rows(
        document.get("candidateReconciliation"),
        "candidateId",
        "candidate reconciliation",
    )
    expected = {
        "tdd.matt.current": (
            "SE-TDD-MATT-CURRENT",
            MATT_PATH.as_posix(),
            matt,
        ),
        "tdd.superpowers.6.2.0": (
            "SE-TDD-SUPERPOWERS-6.2.0",
            SUPERPOWERS_PATH.as_posix(),
            superpowers,
        ),
    }
    _require(set(rows) == set(expected), "candidate reconciliation set drifted")
    for candidate_id, (arm_id, path_text, admission) in expected.items():
        row = rows[candidate_id]
        decision = admission.get("decision", {})
        _require(
            admission.get("status")
            == "admit-diagnostic-only-current-dispatch-still-blocked",
            f"{candidate_id} admission status drifted",
        )
        _require(
            decision.get("disposition") == "admit-diagnostic-only"
            and decision.get("identityBoundExecutionAdmissionSatisfied")
            is True,
            f"{candidate_id} static admission is not satisfied",
        )
        for key in (
            "approvedReleaseAdmission",
            "candidateMaterializationAuthorizedNow",
            "candidateExecutionAuthorizedNow",
            "modelDispatchAuthorizedNow",
            "currentDispatchEligible",
        ):
            _require(
                decision.get(key) is False,
                f"{candidate_id} unexpectedly promotes {key}",
            )
        _require(row.get("armId") == arm_id, f"{candidate_id} arm drifted")
        _require(
            row.get("admissionDecision") == path_text,
            f"{candidate_id} decision path drifted",
        )
        _require(
            row.get("identityBoundRepositoryGovernanceAdmission")
            == "satisfied",
            f"{candidate_id} reconciliation admission drifted",
        )
        for key in (
            "approvedReleaseAdmission",
            "currentMaterializationAuthorized",
            "currentExecutionAuthorized",
            "currentModelDispatchAuthorized",
            "currentDispatchEligible",
        ):
            _require(
                row.get(key) is False,
                f"{candidate_id} reconciliation promotes {key}",
            )


def _validate_current_blockers(
    protocol: dict[str, Any],
    preflight: dict[str, Any],
    ledger: dict[str, Any],
    adapter: dict[str, Any],
    runner_preflight: dict[str, Any],
    formal: dict[str, Any],
) -> None:
    protocol_decision = protocol.get("decision", {})
    _require(
        protocol_decision.get("anyExactCandidateExecutionEligibleNow")
        is False
        and protocol_decision.get("governanceAdmissionStillRequired")
        is True
        and protocol_decision.get("candidateAdmissionDecisionMade") is False,
        "current protocol no longer has the reconciled blockers",
    )
    _require(
        "dispatchLedgerAuthority" not in protocol,
        "current protocol unexpectedly contains live ledger authority",
    )

    raw_boundary = preflight.get("rawEvidenceBoundary", {})
    preflight_decision = preflight.get("decision", {})
    _require(
        raw_boundary.get("freshForDispatch") is False
        and raw_boundary.get("freshRevalidationStillRequiredAtDispatch")
        is True
        and preflight_decision.get("freshForDispatch") is False,
        "dated preflight freshness boundary drifted",
    )

    ledger_decision = ledger.get("decision", {})
    _require(
        ledger_decision.get("modulePocValidated") is True
        and ledger_decision.get("dispatchCapScope")
        == "protocol-selected-ledger-local"
        and ledger_decision.get("systemGlobalDispatchCapProved") is False
        and ledger_decision.get("formalRunnerIntegrationImplemented")
        is False
        and ledger_decision.get("runtimeDispatchCapEnforcedForLiveRunner")
        is False,
        "identity-ledger evidence boundary drifted",
    )

    adapter_decision = adapter.get("decision", {})
    _require(
        adapter_decision.get("adapterPocValidated") is True
        and adapter_decision.get("currentRepositoryDocumentsRejected")
        is True
        and adapter_decision.get("sourceSnapshotToFactoryMaterializationFreshnessProved")
        is False
        and adapter_decision.get("formalRunnerIntegrationImplemented")
        is False,
        "authorization-adapter evidence boundary drifted",
    )

    runner_decision = runner_preflight.get("decision", {})
    for key in (
        "realAppServerHandleCompatibilityProved",
        "realChildProcessOrSocketCleanupProved",
        "cleanupAfterProcessCrashProved",
        "crossProcessExactlyOnceCleanupProved",
        "liveLedgerAuthorityConfigured",
        "currentCandidateDispatchAuthorized",
        "formalRunnerIntegrationImplemented",
    ):
        _require(
            runner_decision.get(key) is False,
            f"runner-preflight evidence unexpectedly promotes {key}",
        )
    _require(
        runner_decision.get("runnerPreflightPocValidated") is True
        and runner_decision.get("injectedFactoryOnly") is True,
        "runner-preflight offline PoC boundary drifted",
    )

    formal_claims = formal.get("claimBoundary", {})
    _require(
        formal.get("decision", {}).get("formalRunnerIntegratedPathObserved")
        is True
        and formal_claims.get("provesTreatmentDelivery") is False
        and formal_claims.get("provesSkillCausation") is False,
        "formal-runner first-attempt boundary drifted",
    )


def _validate_source_shape() -> None:
    adapter_source = (ROOT / ADAPTER_SOURCE_PATH).read_text(encoding="utf-8")
    for marker in (
        "diagnostic-only-exact-candidate-execution-admission",
        "sourceRevalidatedAt",
        "validFrom",
        "validUntil",
        "dispatchLedgerAuthority",
    ):
        _require(marker in adapter_source, f"adapter marker is missing: {marker}")

    formal_source = (ROOT / FORMAL_RUNNER_PATH).read_text(encoding="utf-8")
    for forbidden in (
        "human_ai_collaboration_tdd_noncomparative_dispatch_authorization_adapter",
        "human_ai_collaboration_tdd_noncomparative_dispatch_identity_ledger",
        "human_ai_collaboration_tdd_noncomparative_runner_preflight",
    ):
        _require(
            forbidden not in formal_source,
            f"formal runner integration changed without reconciliation: {forbidden}",
        )
    materialize_index = formal_source.find("package = build_trial_package(")
    app_server_index = formal_source.find("control = AppServerSession(")
    _require(
        0 <= materialize_index < app_server_index,
        "formal runner materialization/construction ordering drifted",
    )


def _validate_gates_and_decision(document: dict[str, Any]) -> None:
    gates = _unique_rows(
        document.get("gateReconciliation"),
        "gateId",
        "gate reconciliation",
    )
    _require(set(gates) == set(EXPECTED_GATE_STATUSES), "gate set drifted")
    for gate_id, status in EXPECTED_GATE_STATUSES.items():
        _require(
            gates[gate_id].get("status") == status,
            f"gate status drifted: {gate_id}",
        )
    _require(
        "short-lived diagnostic-only-exact-candidate-execution-admission documents"
        in " ".join(gates["gate.dispatch-authorization-envelope"].get("blockers", [])),
        "adapter-envelope distinction is missing",
    )
    _require(
        "replacementDispatchesAllowed"
        in " ".join(
            gates["gate.dispatch-authorization-envelope"].get("blockers", [])
        )
        and "replacementDispatchAllowed"
        in " ".join(
            gates["gate.dispatch-authorization-envelope"].get("blockers", [])
        ),
        "protocol/adapter replacement-dispatch field mismatch is missing",
    )
    _require(
        "historical static gap audit permanently binds the dated preflight"
        in " ".join(
            gates["gate.dispatch-authorization-envelope"].get(
                "blockers",
                [],
            )
        ),
        "static-audit/fresh-preflight incompatibility is missing",
    )
    _require(
        "thread-start-intent"
        in " ".join(
            gates["gate.dispatch-identity-ledger"].get("blockers", [])
        )
        and "turn-start-intent"
        in " ".join(
            gates["gate.dispatch-identity-ledger"].get("blockers", [])
        ),
        "pre-send thread/turn intent gap is missing",
    )
    _require(
        "cleanup callbacks and owner are no longer reachable"
        in " ".join(
            gates["gate.resource-ownership-and-cleanup"].get(
                "blockers",
                [],
            )
        ),
        "successful-path resource-owner gap is missing",
    )
    successor_blockers = " ".join(
        gates["gate.diagnostic-runner-successor"].get("blockers", [])
    )
    _require(
        "formalAcceptanceContribution false" in successor_blockers
        and "countsTowardWeakAcceptance true" in successor_blockers
        and "formal weak-acceptance policy shell" in document.get(
            "decision",
            {},
        ).get("nextBoundedAction", ""),
        "diagnostic/formal runner policy boundary is missing",
    )

    decision = document.get("decision", {})
    for key in (
        "mattIdentityBoundDiagnosticAdmissionSatisfied",
        "superpowersIdentityBoundDiagnosticAdmissionSatisfied",
        "bothStaticRepositoryGovernanceAdmissionsSatisfied",
        "offlineIdentityLedgerPocValidated",
        "offlineAuthorizationAdapterPocValidated",
        "offlineRunnerPreflightPocValidated",
        "offlinePreconstructionAtomicityPartiallyValidated",
    ):
        _require(decision.get(key) is True, f"decision lost {key}")
    for key in (
        "currentProtocolExecutionEligibilitySatisfied",
        "currentDispatchFreshnessSatisfied",
        "currentDispatchAuthorizationEnvelopeSatisfied",
        "protocolAdapterFieldContractAligned",
        "liveLedgerAuthorityConfigured",
        "realAppServerResourceContractSatisfied",
        "sourceSnapshotToMaterializationFreshnessSatisfied",
        "crossProcessAtomicitySatisfied",
        "crashRecoverySatisfied",
        "formalRunnerIntegratedWithDispatchGate",
        "diagnosticRunnerOrSharedTransportIntegrated",
        "currentCandidateMaterializationAuthorized",
        "currentCandidateExecutionAuthorized",
        "currentModelDispatchAuthorized",
        "currentCandidateExecutionReady",
        "liveDiagnosticStarted",
        "candidateInstructionExecuted",
        "modelRequestSent",
    ):
        _require(decision.get(key) is False, f"decision unexpectedly promotes {key}")

    claims = document.get("claimBoundary", {})
    _require(claims, "claim boundary is missing")
    for key, value in claims.items():
        _require(value is False, f"claim boundary unexpectedly promotes {key}")


def _validate_documentation() -> None:
    text = (ROOT / DOCUMENTATION_PATH).read_text(encoding="utf-8")
    for marker in (
        "Current materialization, candidate execution, app-server construction, and",
        "The static decisions are not short-lived adapter dispatch envelopes",
        "does not import or call the non-comparative authorization adapter",
        "No candidate or model was run",
        "Until those gates pass, both candidates remain metadata-only.",
    ):
        _require(marker in text, f"documentation marker is missing: {marker}")


def validate_reconciliation(document: dict[str, Any]) -> None:
    _require(document.get("schema") == 1, "schema drifted")
    _require(
        document.get("id")
        == "human-ai-collaboration-tdd-current-execution-readiness-reconciliation-2026-07-27",
        "id drifted",
    )
    _require(
        document.get("status")
        == "current-execution-readiness-blocked-static-admissions-satisfied-offline-control-plane-only",
        "status drifted",
    )
    _require(
        document.get("documentation") == DOCUMENTATION_PATH.as_posix(),
        "documentation path drifted",
    )

    _validate_bindings(document)
    _validate_artifacts(document)
    matt = _load(MATT_PATH)
    superpowers = _load(SUPERPOWERS_PATH)
    _validate_admissions(document, matt, superpowers)
    _validate_current_blockers(
        _load(PROTOCOL_PATH),
        _load(PREFLIGHT_PATH),
        _load(LEDGER_EVIDENCE_PATH),
        _load(ADAPTER_EVIDENCE_PATH),
        _load(RUNNER_PREFLIGHT_EVIDENCE_PATH),
        _load(FORMAL_EVIDENCE_PATH),
    )
    _validate_source_shape()
    _validate_gates_and_decision(document)

    authority = document.get("authorityBoundary", {})
    _require(
        authority.get("repositoryReconciliationRecordAuthorized") is True,
        "repository reconciliation authority is missing",
    )
    for key, value in authority.items():
        if key in (
            "repositoryReconciliationRecordAuthorized",
            "readExistingRepositoryAndInstalledPackageEvidence",
        ):
            _require(value is True, f"authorized read boundary drifted: {key}")
        else:
            _require(value is False, f"side effect unexpectedly recorded: {key}")
    _validate_documentation()


def main() -> int:
    validate_reconciliation(_load(RECONCILIATION_PATH))
    print("TDD current execution-readiness reconciliation: valid")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
