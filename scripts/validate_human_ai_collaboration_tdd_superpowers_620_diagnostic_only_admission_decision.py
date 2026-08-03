#!/usr/bin/env python3
"""Fail closed on drift in the Superpowers 6.2.0 TDD diagnostic admission."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
DECISION_PATH = (
    "registry/human-ai-collaboration-tdd-superpowers-620-diagnostic-only-"
    "admission-decision-2026-07-27.json"
)
DOCUMENTATION_PATH = (
    "docs/strategy/HUMAN-AI-COLLABORATION-TDD-SUPERPOWERS-620-"
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
RUNTIME_SNAPSHOT_PATH = (
    "registry/skill-runtime-and-cc-count-drift-snapshot-2026-07-27.json"
)
NOTICES_PATH = "THIRD_PARTY_NOTICES.md"
PROGRAM_PATH = "registry/program-acceptance-map.json"
ACCEPTANCE_ID = "acceptance.third-party-admission-gates"
PROGRAM_EVIDENCE_ID = (
    "evidence.human-ai-collaboration-tdd-superpowers-620-diagnostic-only-"
    "admission-decision-2026-07-27"
)
PROGRAM_EVIDENCE_KIND = (
    "identity-bound-diagnostic-only-admission-current-dispatch-blocked-"
    "no-release-value-or-residual-gap-promotion"
)

EXPECTED_VERSION = "6.2.0"
EXPECTED_COMMIT = "3dcbd5c4b48e02263fbf4a3c01e3fe4f81d584d9"
EXPECTED_PACKAGE_TREE = (
    "948ff71f332ad9bb3f1031ad468bf0a6f6a55c80d1c106f92a831b63e6ea7874"
)
EXPECTED_PACKAGE_HOME_RELATIVE = (
    ".codex/plugins/cache/openai-curated-remote/superpowers/6.2.0"
)
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
    "superpowers:writing-skills",
    "full Superpowers orchestration",
    "other-test repair",
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


def _package_root() -> Path:
    return Path.home() / Path(EXPECTED_PACKAGE_HOME_RELATIVE)


def validate_decision(
    document: dict[str, Any],
    *,
    root: Path = ROOT,
    installed_package_root: Path | None = None,
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
        RUNTIME_SNAPSHOT_PATH,
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
    runtime_snapshot = _load(root, RUNTIME_SNAPSHOT_PATH)

    authority = document.get("authorityBoundary", {})
    _require(
        authority
        == {
            "repositoryDecisionRecordAuthorized": True,
            "readExistingRepositoryAndInstalledPackageEvidence": True,
            "networkAccess": False,
            "candidateMaterialized": False,
            "candidateSkillInvoked": False,
            "candidateTaskTurnStarted": False,
            "modelRequestSent": False,
            "dependencyInstalled": False,
            "installedPluginOrSkillMutation": False,
            "globalConfigurationOrCcSwitchMutation": False,
            "approvedRegistryOrReleaseManifestMutation": False,
            "portfolioMutation": False,
            "externalWrite": False,
            "gitMutation": False,
        },
        "authority boundary drifted",
    )

    expected_norms = {
        "exact package, release, and selected-file identity",
        "license, notice, and attribution",
        "security and executable or permission surface",
        "portability and host or language assumptions",
        "native, Matt, and project-hard-standard overlap",
        "candidate conflict disposition without byte modification",
        "frozen-fixture compatibility",
        "identity-bound admission distinct from release admission",
    }
    _require(
        set(document.get("reviewNorms", [])) == expected_norms,
        "review norm set drifted",
    )

    protocol_candidates = _items_by(
        diagnostic_protocol["candidates"], "candidateId"
    )
    observed_candidates = _items_by(
        preflight["candidateObservations"], "candidateId"
    )
    audited_candidates = _items_by(gap_audit["candidates"], "candidateId")
    candidate_id = "tdd.superpowers.6.2.0"
    protocol_candidate = protocol_candidates[candidate_id]
    observation = observed_candidates[candidate_id]
    audit_candidate = audited_candidates[candidate_id]
    identity = document.get("candidateIdentity", {})

    source = runtime_snapshot["externalSourceRevalidation"]["superpowers"]
    current = reconciliation["baselineReconciliation"][
        "currentSuperpowersSourceBaseline"
    ]
    _require(
        identity.get("candidateId") == candidate_id
        and identity.get("repository") == "obra/superpowers"
        and identity.get("sourceClass") == protocol_candidate["sourceClass"]
        and identity.get("version") == EXPECTED_VERSION
        and identity.get("releaseTag") == source["latestRelease"] == "v6.2.0"
        and identity.get("releaseCommit")
        == source["releaseCommit"]
        == current["releaseCommit"]
        == EXPECTED_COMMIT
        and source["mainCommitMatchesReleaseCommit"] is True,
        "candidate release identity drifted",
    )
    _require(
        identity.get("packageRootHomeRelative")
        == source["currentRuntimePackageRootHomeRelative"]
        == EXPECTED_PACKAGE_HOME_RELATIVE
        and identity.get("packageTreeSha256")
        == source["currentRuntimePackageTreeSha256"]
        == EXPECTED_PACKAGE_TREE
        and identity.get("runtimeSkillEntryCount")
        == current["runtimeSkillEntryCount"]
        == source["skillEntryCount"]
        == 14
        and identity.get("allSkillEntriesExactReleaseBytes") is True
        and source["allSkillEntriesExactReleaseBytes"] is True
        and current["allSkillEntriesExactReleaseBytes"] is True,
        "candidate package identity drifted",
    )
    _require(
        identity.get("projectionTreeSha256")
        == protocol_candidate["projectionTreeSha256"]
        == "a95561fa9bf2ffbd75242e70a1d28d929c67b4d1df2997fa3061dc20c6b29501",
        "candidate projection identity drifted",
    )

    manifest_identity = identity.get("pluginManifest", {})
    _require(
        manifest_identity.get("sourcePath") == ".codex-plugin/plugin.json"
        and manifest_identity.get("bytes") == 1722
        and manifest_identity.get("sha256")
        == observation["pluginManifest"]["sha256"]
        and observation["pluginManifest"]["bytes"] == 1722,
        "frozen plugin manifest identity drifted",
    )
    license_identity = identity.get("license", {})
    _require(
        license_identity.get("spdx") == "MIT"
        and license_identity.get("sourcePath") == "LICENSE"
        and license_identity.get("bytes") == 1070
        and license_identity.get("sha256")
        == observation["license"]["sha256"]
        and observation["license"]["bytes"] == 1070
        and license_identity.get("copyright")
        == "Copyright (c) 2025 Jesse Vincent",
        "frozen package license or attribution drifted",
    )

    decision_files = _items_by(identity.get("files", []), "projectedPath")
    protocol_files = _items_by(protocol_candidate["files"], "path")
    observed_files = _items_by(observation["files"], "projectedPath")
    _require(
        set(decision_files) == set(protocol_files) == set(observed_files),
        "candidate file set drifted",
    )
    for projected_path, decision_file in decision_files.items():
        _require(
            decision_file
            == {
                "sourcePath": observed_files[projected_path]["sourcePath"],
                "projectedPath": projected_path,
                "bytes": protocol_files[projected_path]["bytes"],
                "sha256": protocol_files[projected_path]["sha256"],
            }
            and observed_files[projected_path]["bytes"]
            == decision_file["bytes"]
            and observed_files[projected_path]["sha256"]
            == decision_file["sha256"],
            f"candidate file identity drifted: {projected_path}",
        )

    if installed_package_root is not None:
        package_root = installed_package_root.resolve(strict=False)
        _require(
            package_root.is_dir(),
            "installed Superpowers package is missing",
        )
        manifest_path = package_root / ".codex-plugin/plugin.json"
        license_path = package_root / "LICENSE"
        _require(
            manifest_path.is_file(),
            "installed plugin manifest is missing",
        )
        _require(
            license_path.is_file(),
            "installed package license is missing",
        )
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        license_text = license_path.read_text(encoding="utf-8")
        _require(
            manifest_path.stat().st_size == manifest_identity["bytes"]
            and _sha256(manifest_path) == manifest_identity["sha256"]
            and manifest.get("version") == EXPECTED_VERSION
            and manifest.get("repository")
            == "https://github.com/obra/superpowers"
            and manifest.get("license") == "MIT"
            and manifest.get("hooks") == {}
            and manifest.get("skills") == "./skills/"
            and manifest.get("interface", {}).get("capabilities")
            == ["Interactive", "Read", "Write"],
            "installed plugin manifest drifted",
        )
        _require(
            license_path.stat().st_size == license_identity["bytes"]
            and _sha256(license_path) == license_identity["sha256"]
            and "Copyright (c) 2025 Jesse Vincent" in license_text,
            "installed package license or attribution drifted",
        )
        for projected_path, decision_file in decision_files.items():
            source_path = package_root / decision_file["sourcePath"]
            _require(
                source_path.is_file()
                and source_path.stat().st_size == decision_file["bytes"]
                and _sha256(source_path) == decision_file["sha256"],
                f"candidate live file identity drifted: {projected_path}",
            )
        skill_text = (
            package_root / "skills/test-driven-development/SKILL.md"
        ).read_text(encoding="utf-8")
        writing_text = (
            package_root
            / "skills/test-driven-development/writing-good-tests.md"
        ).read_text(encoding="utf-8")
        for marker in (
            "npm test path/to/test.test.ts",
            "Delete means delete",
            "**Other tests fail?** Fix now.",
            "[writing-good-tests.md](writing-good-tests.md)",
        ):
            _require(
                marker in skill_text,
                f"candidate conflict marker missing: {marker}",
            )
        _require(
            "superpowers:writing-skills" in writing_text,
            "unprojected writing-skills reference marker missing",
        )

    blocker_ids = {item["id"] for item in audit_candidate["blockers"]}
    _require(
        {
            "superpowers-python-command-conflict",
            "superpowers-delete-existing-code-conflict",
            "superpowers-other-tests-scope-conflict",
            "superpowers-exact-review-missing",
            "superpowers-no-identity-bound-diagnostic-admission",
        }
        <= blocker_ids,
        "gap-audit basis drifted",
    )
    review = document.get("review", {})
    expected_assessments = {
        "provenance": "pass-bounded-current-package-and-release",
        "licenseNoticeAndAttribution": "pass-diagnostic-record-only",
        "security": "pass-selected-two-file-static-review",
        "executableSurface": (
            "pass-no-bundled-executable-in-selected-projection"
        ),
        "portability": "pass-only-for-frozen-python-fixture",
        "overlap": "pass-bounded-controlled-differences",
        "fixtureCompatibility": "pass-only-with-explicit-conflict-controls",
        "validation": "pass-static-decision-contract",
    }
    _require(
        {
            key: value.get("assessment")
            for key, value in review.items()
            if isinstance(value, dict)
        }
        == expected_assessments,
        "review assessment set drifted",
    )
    _require(
        all(
            isinstance(value.get("evidence"), list)
            and bool(value["evidence"])
            and all(isinstance(item, str) and item for item in value["evidence"])
            for value in review.values()
        ),
        "review evidence path set incomplete",
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
        and scope.get("winnerSelectionAllowed") is False
        and scope.get("candidateBytesModified") is False,
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
        scope.get("conflictControls")
        == {
            "frozenPythonCommandOverridesNpmExamples": True,
            "authorizedFixtureScaffoldMustNotBeDeletedOrMutatedBeforeValidRed": True,
            "unrelatedTestFailurePolicy": (
                "abort-diagnostic-no-out-of-scope-repair"
            ),
            "writingSkillsWorkflowExcluded": True,
            "fullSuperpowersOrchestrationExcluded": True,
        },
        "candidate conflict control drifted",
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
        len(decision.get("whyCurrentDispatchRemainsBlocked", [])) == 5,
        "current dispatch blocker set drifted",
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
        criterion.get("evidenceIds", []).count(PROGRAM_EVIDENCE_ID) == 1
        and sum(
            item.get("evidenceIds", []).count(PROGRAM_EVIDENCE_ID)
            for item in program.get("acceptanceCriteria", [])
            if isinstance(item, dict)
        )
        == 1,
        "diagnostic admission criterion backlink must be unique",
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

    admissions = json.dumps(_load(root, "registry/admissions.json"))
    release = json.dumps(_load(root, "release-manifest.json"))
    _require(
        "tdd.superpowers.6.2.0" not in admissions
        and EXPECTED_COMMIT not in admissions,
        "exact candidate leaked into registry/admissions.json",
    )
    _require(
        "tdd.superpowers.6.2.0" not in release
        and EXPECTED_COMMIT not in release,
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
        "No candidate projection was materialized or executed",
        "python -B -m unittest -v test_feature.py",
        "must not be deleted or mutated before a valid RED",
        "If an unrelated test fails, the diagnostic aborts",
        "Source or package identity is not behavior or value",
        "Until every downstream gate passes",
    ):
        _require(
            phrase in documentation,
            f"documentation boundary missing: {phrase}",
        )


def main() -> int:
    validate_decision(_load(ROOT, DECISION_PATH))
    print("Superpowers 6.2.0 TDD diagnostic-only admission decision: valid")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
