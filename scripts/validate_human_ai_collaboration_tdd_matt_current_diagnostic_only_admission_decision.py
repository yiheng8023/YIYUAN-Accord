#!/usr/bin/env python3
"""Fail closed on drift in the exact Matt TDD diagnostic-only admission."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
DECISION_PATH = (
    "registry/human-ai-collaboration-tdd-matt-current-diagnostic-only-"
    "admission-decision-2026-07-27.json"
)
DOCUMENTATION_PATH = (
    "docs/strategy/HUMAN-AI-COLLABORATION-TDD-MATT-CURRENT-"
    "DIAGNOSTIC-ONLY-ADMISSION-DECISION-2026-07-27.md"
)
GAP_AUDIT_PATH = (
    "registry/human-ai-collaboration-tdd-exact-candidate-admission-"
    "gap-audit-2026-07-26.json"
)
SOURCE_PREFLIGHT_PATH = (
    "registry/human-ai-collaboration-tdd-noncomparative-treatment-"
    "diagnostic-source-governance-preflight-2026-07-26.json"
)
DIAGNOSTIC_PROTOCOL_PATH = (
    "registry/human-ai-collaboration-tdd-noncomparative-treatment-"
    "diagnostic-protocol-2026-07-26.json"
)
TDD_PROTOCOL_PATH = (
    "registry/human-ai-collaboration-new-feature-tdd-protocol-2026-07-26.json"
)
RECONCILIATION_PATH = (
    "registry/skill-ecosystem-current-evidence-reconciliation-2026-07-27.json"
)
NOTICES_PATH = "THIRD_PARTY_NOTICES.md"
PROGRAM_PATH = "registry/program-acceptance-map.json"
ACCEPTANCE_ID = "acceptance.third-party-admission-gates"
PROGRAM_EVIDENCE_ID = (
    "evidence.human-ai-collaboration-tdd-matt-current-diagnostic-only-"
    "admission-decision-2026-07-27"
)
PROGRAM_EVIDENCE_KIND = (
    "identity-bound-diagnostic-only-admission-current-dispatch-blocked-"
    "no-release-value-or-residual-gap-promotion"
)

EXPECTED_REVISION = "ed37663cc5fbef691ddfecd080dff42f7e7e350d"
EXPECTED_COMMAND = [
    "python",
    "-B",
    "-m",
    "unittest",
    "-v",
    "test_feature.py",
]
EXPECTED_MUTABLE_FILES = [
    "feature.py",
    "test_feature.py",
    "PROCESS_EVIDENCE.json",
]
EXPECTED_EXCLUSIONS = {
    "code-review",
    "ask-matt",
    "full Matt workflow",
    "network",
    "dependency installation",
    "Git mutation",
    "configuration mutation",
    "MCP",
    "App",
    "Hook",
    "browser",
    "account or credential access",
    "external systems",
    "external writes",
}


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def _load(root: Path, path: str) -> dict[str, Any]:
    return json.loads((root / path).read_text(encoding="utf-8"))


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _items_by(items: list[dict[str, Any]], key: str) -> dict[str, dict[str, Any]]:
    return {str(item[key]): item for item in items}


def validate_decision(
    document: dict[str, Any],
    *,
    root: Path = ROOT,
) -> None:
    _require(document.get("schema") == 1, "decision schema must be 1")
    _require(
        document.get("status")
        == "admit-diagnostic-only-current-dispatch-still-blocked",
        "decision status drifted",
    )

    bindings = _items_by(document.get("sourceBindings", []), "path")
    expected_paths = {
        GAP_AUDIT_PATH,
        SOURCE_PREFLIGHT_PATH,
        DIAGNOSTIC_PROTOCOL_PATH,
        TDD_PROTOCOL_PATH,
        RECONCILIATION_PATH,
        NOTICES_PATH,
    }
    _require(set(bindings) == expected_paths, "source binding set drifted")
    for path, binding in bindings.items():
        _require(
            binding.get("sha256") == _sha256(root / path),
            f"source binding digest drifted: {path}",
        )

    gap_audit = _load(root, GAP_AUDIT_PATH)
    preflight = _load(root, SOURCE_PREFLIGHT_PATH)
    diagnostic_protocol = _load(root, DIAGNOSTIC_PROTOCOL_PATH)
    tdd_protocol = _load(root, TDD_PROTOCOL_PATH)
    reconciliation = _load(root, RECONCILIATION_PATH)
    notices = (root / NOTICES_PATH).read_text(encoding="utf-8")

    authority = document.get("authorityBoundary", {})
    _require(
        authority
        == {
            "repositoryDecisionRecordAuthorized": True,
            "readExistingRepositoryEvidence": True,
            "candidateSourceObservationReused": True,
            "networkAccess": False,
            "candidateMaterialized": False,
            "candidateSkillInvoked": False,
            "candidateTaskTurnStarted": False,
            "modelRequestSent": False,
            "dependencyInstalled": False,
            "globalConfigurationOrCcSwitchMutation": False,
            "approvedRegistryOrReleaseManifestMutation": False,
            "portfolioMutation": False,
            "externalWrite": False,
            "gitMutation": False,
        },
        "authority boundary drifted",
    )
    _require(
        set(document.get("reviewNorms", []))
        == {
            "exact source identity and provenance",
            "license, notice, and attribution",
            "security and executable or permission surface",
            "portability and host or language assumptions",
            "native, approved-adapted, and project-hard-standard overlap",
            "frozen-fixture compatibility",
            "bounded validation and fail-closed execution scope",
            "identity-bound admission distinct from release admission",
        },
        "review norm set drifted",
    )

    protocol_candidates = _items_by(
        diagnostic_protocol["candidates"], "candidateId"
    )
    observed_candidates = _items_by(
        preflight["candidateObservations"], "candidateId"
    )
    audited_candidates = _items_by(gap_audit["candidates"], "candidateId")
    protocol_candidate = protocol_candidates["tdd.matt.current"]
    observation = observed_candidates["tdd.matt.current"]
    audit_candidate = audited_candidates["tdd.matt.current"]
    identity = document.get("candidateIdentity", {})

    _require(
        identity.get("candidateId") == "tdd.matt.current"
        and identity.get("repository") == "mattpocock/skills"
        and identity.get("sourceClass") == protocol_candidate["sourceClass"]
        and identity.get("revision") == EXPECTED_REVISION
        and identity.get("observedCurrentMainRevision") == EXPECTED_REVISION
        and identity.get("currentMainMatchedPinnedAtObservation") is True
        and observation["currentMainMatchesPinned"] is True
        and observation["liveBytesMatchProtocol"] is True,
        "candidate provenance identity drifted",
    )
    _require(
        identity.get("projectionTreeSha256")
        == protocol_candidate["projectionTreeSha256"]
        and identity.get("projectionTreeSha256")
        == "4004b864c2c2e472edaf4024aca1e9fb5a2861694b5480775d69c7e0001866c3",
        "candidate projection identity drifted",
    )
    _require(
        identity.get("license") == {
            **observation["license"],
            "spdx": "MIT",
            "copyright": "Copyright (c) 2026 Matt Pocock",
        },
        "candidate license or attribution drifted",
    )
    decision_files = _items_by(identity.get("files", []), "projectedPath")
    protocol_files = _items_by(protocol_candidate["files"], "path")
    observed_files = _items_by(observation["files"], "projectedPath")
    _require(
        set(decision_files) == set(protocol_files) == set(observed_files),
        "candidate file set drifted",
    )
    for path, decision_file in decision_files.items():
        _require(
            decision_file
            == {
                "sourcePath": observed_files[path]["sourcePath"],
                "projectedPath": path,
                "bytes": protocol_files[path]["bytes"],
                "sha256": protocol_files[path]["sha256"],
                "gitBlobSha1": protocol_files[path]["gitBlobSha1"],
            },
            f"candidate file identity drifted: {path}",
        )

    blocker_ids = {
        item["id"] for item in audit_candidate.get("blockers", [])
    }
    _require(
        {
            "matt-exact-revision-review-missing",
            "matt-notice-attribution-missing",
            "matt-refactor-stage-conflict-unadmitted",
            "matt-no-identity-bound-diagnostic-admission",
        }
        <= blocker_ids,
        "gap-audit basis drifted",
    )
    review = document.get("review", {})
    _require(
        {
            "provenance": "pass-bounded-dated-observation",
            "licenseNoticeAndAttribution": "pass-diagnostic-record-only",
            "security": "pass-bounded-static-text-review",
            "executableSurface": "pass-no-bundled-executable",
            "portability": "pass-only-for-frozen-python-fixture",
            "overlap": "pass-bounded-controlled-difference",
            "fixtureCompatibility": (
                "pass-only-for-preregistered-noncomparative-diagnostic"
            ),
            "validation": "pass-static-decision-contract",
        }
        == {
            key: value.get("assessment")
            for key, value in review.items()
            if isinstance(value, dict)
        },
        "review assessment set drifted",
    )
    review_text = " ".join(
        str(value.get("finding", "")) for value in review.values()
    )
    _require(
        all(
            isinstance(value.get("evidence"), list)
            and bool(value["evidence"])
            and all(
                isinstance(item, str) and bool(item.strip())
                for item in value["evidence"]
            )
            for value in review.values()
        ),
        "review evidence path set incomplete",
    )
    for marker in (
        "No signature or distribution attestation",
        "candidate bytes are not redistributed",
        "no bundled script",
        "All three candidate files are Markdown guidance",
        "CONTEXT.md, ADRs, code-review, ask-matt",
        "byte-distinct",
        "public-seam confirmation is precontrolled",
        "Mutation tests reject boundary promotion",
    ):
        _require(marker in review_text, f"review finding missing: {marker}")
    _require(
        "Copyright (c) 2026 Matt Pocock" in notices
        and EXPECTED_REVISION not in notices
        and "6eeb81b5fcfeeb5bd531dd47ab2f9f2bbea27461" in notices,
        "historical notice versus current diagnostic attribution drifted",
    )

    scope = document.get("diagnosticScope", {})
    _require(
        scope.get("protocolId") == diagnostic_protocol["id"]
        and scope.get("scenarioId") == diagnostic_protocol["scenarioId"]
        and scope.get("armId") == protocol_candidate["armId"]
        and scope.get("maximumDispatchesForThisAdmission") == 1
        and scope.get("comparative") is False
        and scope.get("scored") is False
        and scope.get("rankingAllowed") is False
        and scope.get("winnerSelectionAllowed") is False,
        "diagnostic scope drifted",
    )
    _require(
        scope.get("exactPythonCommandPriority") == EXPECTED_COMMAND,
        "Python command priority drifted",
    )
    _require(
        scope.get("allowedMutableFiles") == EXPECTED_MUTABLE_FILES
        and scope["allowedMutableFiles"]
        == tdd_protocol["fixtureContract"]["allowedMutableFiles"],
        "mutable-file allowlist drifted",
    )
    _require(
        set(scope.get("excludedCapabilitiesAndEffects", []))
        == EXPECTED_EXCLUSIONS,
        "excluded capability or effect set drifted",
    )
    _require(
        scope.get("hardStandardsRemainControls") is True
        and scope.get("hardStandardsCreditedToCandidate") is False,
        "hard-standard control boundary drifted",
    )

    decision = document.get("decision", {})
    _require(
        decision.get("disposition") == "admit-diagnostic-only"
        and decision.get("identityBoundExecutionAdmissionSatisfied") is True,
        "diagnostic-only admission decision drifted",
    )
    for key in (
        "approvedReleaseAdmission",
        "approvedReleaseInventoryEntryCreated",
        "registryAdmissionsEntryCreated",
        "releaseManifestEntryCreated",
        "candidateMaterializationAuthorizedNow",
        "candidateExecutionAuthorizedNow",
        "modelDispatchAuthorizedNow",
        "currentDispatchEligible",
    ):
        _require(decision.get(key) is False, f"decision boundary promoted: {key}")
    _require(
        len(decision.get("whyCurrentDispatchRemainsBlocked", [])) == 5
        and "fresh source and toolchain revalidation at dispatch is still required"
        in decision["whyCurrentDispatchRemainsBlocked"],
        "current dispatch blocker set drifted",
    )
    _require(
        reconciliation["baselineReconciliation"]["currentMattSourceBaseline"][
            "executionAdmissionSatisfied"
        ]
        is False
        and "exact-current-candidate-execution-admission"
        in reconciliation["currentNextGate"]["requiredBeforeAnotherComparativeRun"],
        "pre-decision reconciliation basis drifted",
    )

    claims = document.get("claimBoundary", {})
    _require(
        len(claims) == 13 and all(value is False for value in claims.values()),
        "claim boundary was promoted",
    )
    program = _load(root, PROGRAM_PATH)
    _require(
        sum(
            item.get("id") == ACCEPTANCE_ID
            for item in program.get("acceptanceCriteria", [])
            if isinstance(item, dict)
        )
        == 1,
        "third-party admission criterion id must be unique",
    )
    _require(
        sum(
            item.get("id") == PROGRAM_EVIDENCE_ID
            for item in program.get("evidence", [])
            if isinstance(item, dict)
        )
        == 1,
        "diagnostic admission evidence id must be unique",
    )
    criteria = _items_by(program.get("acceptanceCriteria", []), "id")
    evidence_records = _items_by(program.get("evidence", []), "id")
    criterion = criteria.get(ACCEPTANCE_ID, {})
    evidence_record = evidence_records.get(PROGRAM_EVIDENCE_ID, {})
    _require(
        criterion.get("assessment") == "verified",
        "third-party admission assessment drifted",
    )
    _require(
        criterion.get("evidenceIds", []).count(PROGRAM_EVIDENCE_ID) == 1,
        "diagnostic admission criterion backlink must occur exactly once",
    )
    _require(
        sum(
            item.get("evidenceIds", []).count(PROGRAM_EVIDENCE_ID)
            for item in program.get("acceptanceCriteria", [])
            if isinstance(item, dict)
        )
        == 1,
        "diagnostic admission evidence must map to exactly one criterion",
    )
    _require(
        evidence_record
        == {
            "id": PROGRAM_EVIDENCE_ID,
            "path": DECISION_PATH,
            "kind": PROGRAM_EVIDENCE_KIND,
            "asOf": "2026-07-27",
            "supports": [ACCEPTANCE_ID],
        },
        "diagnostic admission program evidence projection drifted",
    )
    _require(
        evidence_record.get("supports", []).count(ACCEPTANCE_ID) == 1
        and sum(
            item.get("supports", []).count(ACCEPTANCE_ID)
            for item in program.get("evidence", [])
            if isinstance(item, dict) and item.get("id") == PROGRAM_EVIDENCE_ID
        )
        == 1,
        "diagnostic admission evidence backlink must be unique and bidirectional",
    )
    serialized_admissions = json.dumps(_load(root, "registry/admissions.json"))
    serialized_release = json.dumps(_load(root, "release-manifest.json"))
    _require(
        "tdd.matt.current" not in serialized_admissions
        and EXPECTED_REVISION not in serialized_admissions,
        "exact candidate leaked into registry/admissions.json",
    )
    _require(
        "tdd.matt.current" not in serialized_release
        and EXPECTED_REVISION not in serialized_release,
        "exact candidate leaked into release-manifest.json",
    )

    _require(
        document.get("documentation") == DOCUMENTATION_PATH
        and (root / DOCUMENTATION_PATH).is_file(),
        "documentation binding drifted",
    )
    documentation = " ".join(
        (root / DOCUMENTATION_PATH).read_text(encoding="utf-8").split()
    )
    for phrase in (
        "admit-diagnostic-only-current-dispatch-still-blocked",
        "It is not an approved release admission",
        "No candidate bytes were materialized or executed",
        "python -B -m unittest -v test_feature.py",
        "Only these three files may be changed",
        "Source or package identity is not behavior or value",
        "Until every downstream gate passes",
    ):
        _require(
            phrase in documentation,
            f"documentation boundary missing: {phrase}",
        )


def main() -> int:
    validate_decision(_load(ROOT, DECISION_PATH))
    print("Matt current TDD diagnostic-only admission decision: valid")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
