#!/usr/bin/env python3
"""Validate the current Skill ecosystem evidence reconciliation ledger."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
EVIDENCE_PATH = (
    "registry/skill-ecosystem-current-evidence-reconciliation-2026-07-27.json"
)
DOC_PATH = (
    "docs/strategy/"
    "SKILL-ECOSYSTEM-CURRENT-EVIDENCE-RECONCILIATION-2026-07-27.md"
)
PROGRAM_PATH = "registry/program-acceptance-map.json"
PROGRAM_EVIDENCE_ID = (
    "evidence.skill-ecosystem-current-evidence-reconciliation-2026-07-27"
)
PROGRAM_EVIDENCE_KIND = (
    "sha-bound-current-skill-evidence-reconciliation-historical-611-current-"
    "620-source-only-missing-self-authored-arm-no-mutation"
)
EXPECTED_BINDINGS = [
    (
        "registry/skill-ecosystem-overlap-and-ablation-matrix-2026-07-23.json",
        "7b6fcfd9dab80d42a4180c49ed3b3a97162d4d8ac47a24890d86da71ea57ba8c",
    ),
    (
        "registry/skill-portfolio-rebaseline-and-closeout-gate-2026-07-19.json",
        "1c1729389461022817562848a0bf14c2f75b2965cb2bd66365f9d1b5b91a4edf",
    ),
    (
        "registry/skill-runtime-and-cc-count-drift-snapshot-2026-07-27.json",
        "07bbcf8ebebf0093ad9b85b2b9acf22c4e17e40e3000a2c836ab6068fd352bf6",
    ),
    (
        "registry/skill-source-lineage-collision-index-2026-07-24.json",
        "986f823948c30ac0a03cbbbc00116fbbd0fdd6575e88357211556bde2cc2aab8",
    ),
    (
        "registry/skill-live-run-evidence-contract-2026-07-23.json",
        "37e05c8c6a52c3f69f455a2b9b577adb0b331393b9224bb0737c980e58522e30",
    ),
    (
        "registry/human-ai-collaboration-requirements-domain-live-comparison-"
        "batch-01-2026-07-24.json",
        "7ac2c67c200c988a16b0e35acf92b9bd330d4be75daa572dbe74b504e555aeec",
    ),
    (
        "registry/human-ai-collaboration-weak-agent-live-comparison-"
        "batch-01-2026-07-24.json",
        "4ce4cc26dc17d32344159b23d0748f1a999b9d045c71ce4ebc22690abdb0eca2",
    ),
    (
        "registry/human-ai-collaboration-weak-agent-live-comparison-"
        "batch-02-2026-07-24.json",
        "6db331c8cf185c0b98e123f51bbd95e7dd5e9753a353f062cb21c4948ab8c40b",
    ),
    (
        "registry/human-ai-collaboration-weak-agent-live-comparison-"
        "batch-03-2026-07-24.json",
        "24a57daf38e6d38ef354fe3b0992062a73df72ab84aa4045af35a2c0adb1521a",
    ),
    (
        "registry/human-ai-collaboration-maintenance-migration-live-"
        "comparison-batch-01-2026-07-24.json",
        "58c17ef6c1510ad5d0c4425079c5d2323973635469e12da7f04b032c7569ca36",
    ),
    (
        "registry/human-ai-collaboration-tdd-native-formal-attempt-"
        "batch-2026-07-26.json",
        "cc2bd67e0350188ace0762ccb8ae05f7f9254ffd95ccce865789c900b4fe578f",
    ),
    (
        "registry/human-ai-collaboration-tdd-exact-candidate-admission-gap-"
        "audit-2026-07-26.json",
        "7b9371ef23de7dce3e3c96ffc4595796e519c30736705012b05b467b3d7efef1",
    ),
]
EXPECTED_FAIL_CLOSED_RULES = [
    "historical-superpowers-611-behavior-must-not-be-relabeled-as-current-620",
    "payload-presence-or-selected-exposure-must-not-be-relabeled-as-loader-invocation",
    "repetition-with-hard-oracle-failure-must-not-be-relabeled-as-value",
    "static-content-lineage-must-not-be-relabeled-as-behavioral-equivalence",
    "missing-self-authored-arm-must-not-be-relabeled-as-zero-performance-or-residual-gap",
    "cc-database-row-count-must-not-be-relabeled-as-loaded-or-invoked-count",
    "current-source-pin-must-not-be-relabeled-as-execution-admission",
]
EXPECTED_CELLS = {
    "requirements-native-vs-cc-grill-with-docs": {
        "candidateId": "cc.grill-with-docs",
        "candidateVersion": (
            "sha256:e1078020c41b954638ba94acda95a3340739908bd68b1db9bc2af129d3936035"
        ),
        "validRepetitions": 3,
        "outcome": (0, 1, 0, 0, None, None),
        "currentBehavioralEvidence": True,
    },
    "implementation-native-vs-cc-disciplined-coding": {
        "candidateId": "cc.disciplined-coding",
        "candidateVersion": (
            "sha256:d36f49ed0d252b9c9c656bc9c0f72d43710c68591ce234e8dc2886dc4785fc7b"
        ),
        "validRepetitions": 3,
        "outcome": (3, 3, 3, 3, 3, 2),
        "currentBehavioralEvidence": True,
    },
    "incident-native-vs-cc-historical-diagnose": {
        "candidateId": "cc.diagnose",
        "candidateVersion": (
            "sha256:28886402bbfa0470248086eab9106a103b964b76ae9496e63ff0c8a6761b6d13"
        ),
        "validRepetitions": 3,
        "outcome": (3, 3, 3, 3, 0, 2),
        "currentBehavioralEvidence": True,
    },
    "incident-current-matt-diagnosing-bugs": {
        "candidateId": "matt.current-diagnosing-bugs",
        "candidateVersion": "ed37663cc5fbef691ddfecd080dff42f7e7e350d",
        "validRepetitions": 3,
        "outcome": (None, 3, None, 1, None, 1),
        "currentBehavioralEvidence": True,
    },
    "incident-historical-superpowers-611-systematic-debugging": {
        "candidateId": "superpowers.runtime-6.1.1-systematic-debugging",
        "candidateVersion": "6.1.1",
        "validRepetitions": 3,
        "outcome": (None, 3, None, 2, None, 1),
        "currentBehavioralEvidence": False,
    },
    "maintenance-native-vs-cc-deprecation-and-migration": {
        "candidateId": "cc.deprecation-and-migration",
        "candidateVersion": (
            "sha256:52ef07de05726292c0f5e9fe666cc30e6efbe580ed775621e785a49ec80bd4ea"
        ),
        "validRepetitions": 3,
        "outcome": (3, 3, 3, 1, 3, 3),
        "currentBehavioralEvidence": True,
    },
    "new-feature-tdd-native-formal-attempts": {
        "candidateId": "native.spark-low-tdd",
        "candidateVersion": "gpt-5.3-codex-spark/low",
        "validRepetitions": 0,
        "outcome": (3, None, 0, None, 0, None),
        "currentBehavioralEvidence": True,
    },
    "new-feature-tdd-current-matt-missing-arm": {
        "candidateId": "tdd.matt.current",
        "candidateVersion": "ed37663cc5fbef691ddfecd080dff42f7e7e350d",
        "validRepetitions": 0,
        "outcome": (None, None, None, None, None, None),
        "currentBehavioralEvidence": False,
    },
    "new-feature-tdd-current-superpowers-620-missing-arm": {
        "candidateId": "tdd.superpowers.6.2.0",
        "candidateVersion": "6.2.0",
        "validRepetitions": 0,
        "outcome": (None, None, None, None, None, None),
        "currentBehavioralEvidence": False,
    },
    "self-authored-contract-chain-live-ablation-missing": {
        "candidateId": "self.intent-router-closure-chain",
        "candidateVersion": "repository-deterministic-packets-only",
        "validRepetitions": 0,
        "outcome": (None, None, None, None, None, None),
        "currentBehavioralEvidence": False,
    },
}
OUTCOME_KEYS = (
    "nativeVisiblePassCount",
    "candidateVisiblePassCount",
    "nativeHardOraclePassCount",
    "candidateHardOraclePassCount",
    "nativeStrictProcessPassCount",
    "candidateStrictProcessPassCount",
)


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load(root: Path, path: str) -> dict[str, Any]:
    return json.loads((root / path).read_text(encoding="utf-8"))


def validate_reconciliation(
    document: dict[str, Any],
    *,
    root: Path = ROOT,
    program: dict[str, Any] | None = None,
) -> None:
    _require(
        document.get("schema") == 1
        and document.get("id")
        == "skill-ecosystem-current-evidence-reconciliation-2026-07-27"
        and document.get("date") == "2026-07-27"
        and document.get("status")
        == "current-evidence-reconciled-no-value-causation-or-portfolio-mutation",
        "Current Skill evidence reconciliation identity changed.",
    )
    authority = document.get("authorityBoundary")
    _require(
        isinstance(authority, dict)
        and authority.get("readExistingRepositoryEvidence") is True
        and all(
            authority.get(key) is False
            for key in (
                "skillBodyExecution",
                "modelRequest",
                "networkAccess",
                "skillInstallEnableDisableOrDelete",
                "ccSwitchOrGlobalConfigurationMutation",
                "agentHomeMutation",
                "portfolioMutation",
                "gitMutation",
            )
        ),
        "Current Skill evidence authority boundary changed.",
    )

    bindings = document.get("sourceBindings")
    _require(
        isinstance(bindings, list)
        and [
            (item.get("path"), item.get("fileSha256"))
            for item in bindings
            if isinstance(item, dict)
        ]
        == EXPECTED_BINDINGS,
        "Current Skill evidence source bindings changed.",
    )
    for path, digest in EXPECTED_BINDINGS:
        source_path = root / path
        _require(
            source_path.is_file() and _sha256(source_path) == digest,
            f"Bound source digest changed: {path}",
        )

    historical = _load(root, EXPECTED_BINDINGS[0][0])
    runtime = _load(root, EXPECTED_BINDINGS[2][0])
    requirements = _load(root, EXPECTED_BINDINGS[5][0])
    implementation = _load(root, EXPECTED_BINDINGS[6][0])
    incident_cc = _load(root, EXPECTED_BINDINGS[7][0])
    incident_current = _load(root, EXPECTED_BINDINGS[8][0])
    maintenance = _load(root, EXPECTED_BINDINGS[9][0])
    tdd_native = _load(root, EXPECTED_BINDINGS[10][0])
    tdd_admission = _load(root, EXPECTED_BINDINGS[11][0])

    baseline = document.get("baselineReconciliation")
    _require(isinstance(baseline, dict), "Baseline reconciliation is missing.")
    historical_baseline = baseline.get("historicalMatrix", {})
    historical_superpowers = historical.get("baselines", {}).get(
        "superpowers", {}
    )
    _require(
        historical_superpowers.get("localCuratedPluginVersion") == "6.1.1"
        and historical.get("nextGate")
        == (
            "obtain-verifiable-spark-low-and-task-scoped-skill-exposure-"
            "then-run-repeated-host-isolated-arms"
        )
        and historical_baseline
        == {
            "recordId": historical["id"],
            "superpowersVersion": "6.1.1",
            "historicalCurrentDecisionAuthority": False,
            "preservedUnmodified": True,
            "contentLineageProvesBehavioralEquivalence": False,
            "selectedExposureProvesInvocation": False,
        },
        "Historical 6.1.1 matrix boundary changed.",
    )
    current_matt = baseline.get("currentMattSourceBaseline")
    current_superpowers = baseline.get("currentSuperpowersSourceBaseline")
    runtime_sources = runtime.get("externalSourceRevalidation", {})
    runtime_matt = runtime_sources.get("mattPocock", {})
    runtime_superpowers = runtime_sources.get("superpowers", {})
    _require(
        current_matt
        == {
            "repository": runtime_matt.get("repository"),
            "revision": runtime_matt.get("mainCommit"),
            "sourceDriftObserved": False,
            "behavioralBaselineProved": False,
            "executionAdmissionSatisfied": False,
        },
        "Current Matt source baseline or admission boundary changed.",
    )
    _require(
        current_superpowers
        == {
            "repository": runtime_superpowers.get("repository"),
            "version": "6.2.0",
            "releaseCommit": runtime_superpowers.get("releaseCommit"),
            "runtimeSkillEntryCount": 14,
            "allSkillEntriesExactReleaseBytes": True,
            "behavioralBaselineProved": False,
            "executionAdmissionSatisfied": False,
        }
        and runtime_superpowers.get("latestRelease") == "v6.2.0"
        and runtime.get("decision", {}).get(
            "superpowers620IsCurrentRuntimeOwnedSourcePackageBaseline"
        )
        is True
        and runtime.get("decision", {}).get(
            "superpowers620IsBehavioralBaseline"
        )
        is False,
        "Current Superpowers 6.2.0 source-only boundary changed.",
    )
    current_candidates = incident_current.get("candidates", [])
    historical_sp = next(
        (
            candidate
            for candidate in current_candidates
            if candidate.get("id")
            == "superpowers.runtime-6.1.1-systematic-debugging"
        ),
        None,
    )
    _require(
        isinstance(historical_sp, dict)
        and historical_sp.get("packageVersion") == "6.1.1"
        and historical_sp.get("loaderInvocationProved") is False
        and baseline.get("historicalSuperpowersBehaviorBoundary")
        == {
            "observedVersion": "6.1.1",
            "observedScenarioId": "SE-OPS-INCIDENT-01",
            "evidencePath": EXPECTED_BINDINGS[8][0],
            "countsAsCurrent620Behavior": False,
        },
        "Historical Superpowers behavior was promoted to current 6.2.0.",
    )
    cc_counts = baseline.get("currentCcLayeredCounts")
    runtime_cc = runtime.get("ccSwitchObservation", {})
    _require(
        cc_counts
        == {
            "databaseRows": runtime_cc.get("database", {}).get("rows"),
            "distinctNames": runtime_cc.get("database", {}).get(
                "distinctNames"
            ),
            "physicalBodies": runtime_cc.get("roots", {})
            .get("ccSwitch", {})
            .get("resolvableSkillMd"),
            "resolvableConsumerBodies": runtime_cc.get("roots", {})
            .get("claude", {})
            .get("resolvableSkillMd"),
            "unresolvedClaudeLinks": runtime_cc.get("roots", {})
            .get("claude", {})
            .get("unresolvedSkillMd"),
            "loadedOrInvokedCount": None,
            "databaseRowsProveLoadedOrInvokedCount": False,
            "backupRestoreVerified": False,
            "crossDeviceEqualityProved": False,
        },
        "CC layered count was promoted to loader or recovery evidence.",
    )

    cells = document.get("evidenceCells")
    _require(
        isinstance(cells, list)
        and len(cells) == len(EXPECTED_CELLS)
        and all(isinstance(cell, dict) for cell in cells),
        "Evidence cell shape changed.",
    )
    cells_by_id = {cell.get("cellId"): cell for cell in cells}
    _require(
        set(cells_by_id) == set(EXPECTED_CELLS),
        "Evidence cell identity changed.",
    )
    for cell_id, expected in EXPECTED_CELLS.items():
        cell = cells_by_id[cell_id]
        outcome = cell.get("outcome")
        fidelity = cell.get("treatmentFidelity")
        _require(
            isinstance(outcome, dict)
            and tuple(outcome.get(key) for key in OUTCOME_KEYS)
            == expected["outcome"]
            and cell.get("candidateId") == expected["candidateId"]
            and cell.get("candidateVersion") == expected["candidateVersion"]
            and cell.get("validRepetitions")
            == expected["validRepetitions"]
            and cell.get("currentBehavioralEvidence")
            is expected["currentBehavioralEvidence"]
            and isinstance(fidelity, dict)
            and fidelity.get("independentLoaderEventProved") in (False, None)
            and fidelity.get("candidateInstructionsReachedModelProved")
            in (False, None),
            f"Evidence cell promoted or drifted: {cell_id}",
        )

    _require(
        requirements.get("aggregateResult", {}).get("visiblePassCount")
        == {"native": 0, "candidate": 1}
        and requirements.get("aggregateResult", {}).get(
            "fullHiddenContractPassCount"
        )
        == {"native": 0, "candidate": 0}
        and implementation.get("pairedObservation", {}).get(
            "strictProcessPassCounts"
        )
        == {"native": 3, "matt": 2}
        and incident_cc.get("aggregateResult", {}).get(
            "strictProcessPassCount"
        )
        == {"native": 0, "diagnose": 2}
        and incident_current.get("aggregateResult", {}).get(
            "fullHiddenContractPassCount"
        )
        == {"matt": 1, "superpowers": 2}
        and maintenance.get("aggregateResult", {}).get(
            "fullHiddenContractPassCount"
        )
        == {"native": 3, "candidate": 1},
        "Bound live comparison aggregates changed.",
    )
    _require(
        tdd_native.get("attemptPolicy", {}).get("attempted") == 3
        and tdd_native.get("attemptPolicy", {}).get("valid") == 0
        and tdd_native.get("decision", {}).get(
            "nativeValidComparisonBaselineAvailable"
        )
        is False
        and {
            candidate.get("candidateId"): candidate.get(
                "exactCandidateAdmissionPresent"
            )
            for candidate in tdd_admission.get("candidates", [])
        }
        == {
            "tdd.matt.current": False,
            "tdd.superpowers.6.2.0": False,
        },
        "TDD missing-arm or exact-admission boundary changed.",
    )
    _require(
        all(
            scenario.get("livePacketReady") is False
            for scenario in historical.get("scenarios", [])
        ),
        "Historical deterministic packets were promoted to live ablation.",
    )

    shared = document.get("sharedCellClaimBoundary")
    missing = document.get("missingArmBoundary")
    claims = document.get("claimBoundary")
    _require(
        isinstance(shared, dict)
        and shared
        and all(value is False for value in shared.values()),
        "A shared evidence-cell claim was promoted.",
    )
    _require(
        missing
        == {
            "selfAuthoredLiveCellCount": 0,
            "missingArmCountsAsZeroPerformance": False,
            "missingArmProvesResidualGap": False,
            "deterministicPacketsCountAsLiveBehavior": False,
            "currentCandidateSourcePinCountsAsExecutionAdmission": False,
        },
        "Missing-arm evidence was promoted.",
    )
    _require(
        document.get("failClosedRules") == EXPECTED_FAIL_CLOSED_RULES,
        "Fail-closed rule set changed.",
    )
    _require(
        isinstance(claims, dict)
        and claims
        and all(value is False for value in claims.values()),
        "Current reconciliation claim boundary was promoted.",
    )
    _require(
        document.get("currentNextGate")
        == {
            "alreadyObservedAndNotRepeated": [
                "verifiable-spark-low-route",
                "task-scoped-selected-skill-exposure",
            ],
            "requiredBeforeAnotherComparativeRun": [
                "exact-current-candidate-execution-admission",
                "candidate-specific-treatment-fidelity-or-explicit-unknown",
                "materially-different-scenario-with-frozen-hard-oracle",
            ],
            "modelDispatchAuthorized": False,
            "skillOrPortfolioMutationAuthorized": False,
        },
        "Current next gate regressed or authorized dispatch/mutation.",
    )

    _require(
        document.get("documentation") == DOC_PATH
        and (root / DOC_PATH).is_file(),
        "Current reconciliation documentation binding changed.",
    )
    normalized_doc = " ".join(
        (root / DOC_PATH).read_text(encoding="utf-8").split()
    )
    for phrase in (
        "does not rewrite the 2026-07-23 overlap matrix",
        "historical evidence",
        "source identity, not behavioral equivalence",
        "must not be relabeled as 6.2.0 behavior",
        "Database rows are not a loaded or invoked Skill count",
        "Missing-arm evidence is absence of evidence",
        "verifiable Spark/low routing plus task-scoped selected Skill exposure",
        "No deduplication, migration, retirement, deletion, installation",
    ):
        _require(
            phrase in normalized_doc,
            f"Current reconciliation documentation missing: {phrase}",
        )

    carrier_requirements = {
        "docs/strategy/RESEARCH-AND-POC-PLAN.md": (
            "SKILL-ECOSYSTEM-CURRENT-EVIDENCE-RECONCILIATION-2026-07-27.md",
            "tested Superpowers `6.1.1` behavior cells historical",
            "`6.2.0` as source/package metadata",
            "self-authored arm as missing rather than zero-performing",
        ),
        "docs/strategy/POC-SCENARIO-EVIDENCE-MATRIX.md": (
            "SKILL-ECOSYSTEM-CURRENT-EVIDENCE-RECONCILIATION-2026-07-27.md",
            "historical Superpowers `6.1.1`",
            "Superpowers `6.2.0` remains a source/package baseline only",
            "missing arm remains `unknown`, not zero performance",
        ),
        "docs/operations/CONTINUATION.md": (
            "SKILL-ECOSYSTEM-CURRENT-EVIDENCE-RECONCILIATION-2026-07-27.md",
            "only bound Superpowers behavioral evidence remains `6.1.1`",
            "`6.2.0` is current source/package identity only",
            "Missing arms are not zero scores",
        ),
    }
    for path, phrases in carrier_requirements.items():
        carrier_path = root / path
        _require(
            carrier_path.is_file(),
            f"Current reconciliation carrier is missing: {path}",
        )
        normalized_carrier = " ".join(
            carrier_path.read_text(encoding="utf-8").split()
        )
        for phrase in phrases:
            _require(
                phrase in normalized_carrier,
                f"Current reconciliation carrier boundary missing: {path}: {phrase}",
            )

    loaded_program = program or _load(root, PROGRAM_PATH)
    evidence_matches = [
        item
        for item in loaded_program.get("evidence", [])
        if isinstance(item, dict)
        and item.get("id") == PROGRAM_EVIDENCE_ID
    ]
    _require(
        evidence_matches
        == [
            {
                "id": PROGRAM_EVIDENCE_ID,
                "path": EVIDENCE_PATH,
                "kind": PROGRAM_EVIDENCE_KIND,
                "asOf": "2026-07-27",
                "supports": ["acceptance.residual-gap-proof"],
            }
        ],
        "Current Skill evidence program projection changed.",
    )
    criteria = [
        item
        for item in loaded_program.get("acceptanceCriteria", [])
        if isinstance(item, dict)
    ]
    backlinks = [
        item.get("id")
        for item in criteria
        if PROGRAM_EVIDENCE_ID in item.get("evidenceIds", [])
    ]
    residual = next(
        (
            item
            for item in criteria
            if item.get("id") == "acceptance.residual-gap-proof"
        ),
        None,
    )
    _require(
        backlinks == ["acceptance.residual-gap-proof"]
        and isinstance(residual, dict)
        and residual.get("assessment") == "partial",
        "Current Skill evidence acceptance backlink changed.",
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args()
    root = args.root.resolve()
    document = _load(root, EVIDENCE_PATH)
    validate_reconciliation(document, root=root)
    print("Skill ecosystem current evidence reconciliation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
