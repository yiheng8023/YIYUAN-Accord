#!/usr/bin/env python3
"""Build a dated lineage/collision index from existing repository evidence only."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
SOURCE_PATHS = (
    "registry/legacy-curated-skill-source-migration-review-2026-07-18.json",
    "registry/cc-switch-handoff-real-canary-execution-2026-07-18.json",
    "registry/skill-portfolio-and-closeout-inventory-2026-07-19.json",
    "registry/skill-source-authority-and-runtime-reconciliation-2026-07-19.json",
    "registry/skill-ablation-batch-01-selection-2026-07-19.json",
    "registry/cc-switch-3.18-live-drift-and-transaction-gate-2026-07-23.json",
    "registry/skill-ecosystem-overlap-and-ablation-matrix-2026-07-23.json",
)
GROUP_IDS = (
    "handoff-source-backed-versus-historical",
    "repository-contract-chain-root-collision",
    "lark-attributed-cross-root-collision-cohort",
    "legacy-matt-mapped-mixed-snapshot",
    "selected-cc-three-source-reconciliation",
    "matt-current-content-sample",
    "superpowers-local-plugin-sample",
    "runtime-plugin-alias-reconciliation-gap",
)
ALLOWED_DISPOSITIONS = {
    "compare-baseline",
    "freeze-pending-host-isolated-ablation",
    "freeze-as-atomic-cohort",
    "freeze-unresolved-or-runtime-owned-do-not-copy",
    "candidate-source-review",
    "runtime-owned-do-not-copy",
}


def canonical_sha256(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _record(path: str, document: dict[str, Any], root: Path) -> dict[str, Any]:
    return {
        "path": path,
        "id": document["id"],
        "date": document["date"],
        "status": document["status"],
        "sha256": file_sha256(root / path),
    }


def build_index(root: Path = ROOT) -> dict[str, Any]:
    documents = {
        path: _load(root / path)
        for path in SOURCE_PATHS
    }
    legacy_path, canary_path, inventory_path, authority_path, selection_path, live_path, overlap_path = SOURCE_PATHS
    legacy = documents[legacy_path]
    canary = documents[canary_path]
    inventory = documents[inventory_path]
    authority = documents[authority_path]
    selection = documents[selection_path]
    live = documents[live_path]
    overlap = documents[overlap_path]

    matt_snapshot = next(
        item
        for item in legacy["sourceSnapshots"]
        if item["sourceId"] == "github:mattpocock/skills"
    )
    legacy_handoff = next(
        item
        for item in legacy["skills"]
        if item["skill"] == "handoff"
    )
    legacy_matt = [
        {
            "logicalSkillId": item["skill"],
            "currentUpstreamPath": item["currentPath"],
            "currentUpstreamName": Path(item["currentPath"]).name,
            "lifecycle": item["lifecycle"],
            "priorToCurrent": item["priorToCurrent"],
            "provisionalDisposition": item["provisionalDisposition"],
            "artifactDigest": "unknown",
        }
        for item in legacy["skills"]
        if (
            item["sourceId"] == "github:mattpocock/skills"
            and item["skill"] != "handoff"
        )
    ]
    contract_relations = [
        {
            "logicalSkillId": name,
            "canonicalRepository": authority["contractCanonicalComparison"][
                "canonicalRepository"
            ],
            "canonicalRepositoryObservedHead": authority[
                "contractCanonicalComparison"
            ]["canonicalRepositoryObservedHead"],
            "equalRoots": relation["equalRoots"],
            "differentRoots": relation["differentRoots"],
            "artifactDigests": "unknown",
        }
        for name, relation in sorted(
            authority["contractCanonicalComparison"]["skills"].items()
        )
    ]
    contract_names = {
        item["logicalSkillId"]
        for item in contract_relations
    }
    lark_names = sorted(
        name
        for name in inventory["findings"]["sameNameDifferentSkillMdHashNames"]
        if name not in contract_names
    )
    handoff_binding = selection["payloadDigestPolicy"]["handoffSelectedBinding"]
    source_backed = canary["acceptedAttempt"]
    repository_legacy = selection["payloadDigestPolicy"][
        "repositoryLegacyHandoffNotSelected"
    ]
    matt_current = overlap["baselines"]["mattPocock"]
    superpowers = overlap["baselines"]["superpowers"]
    selected_cc = overlap["ccInstalledStaticComparisonCohort"]
    runtime_gap = authority["missingCcPhysicalRuntimeReconciliation"]

    groups = [
        {
            "id": "handoff-source-backed-versus-historical",
            "logicalSkillIds": ["handoff"],
            "observations": [
                {
                    "surface": "cc-switch-ssot",
                    "observedAt": canary["date"],
                    "sourceEvidenceRef": canary_path,
                    "relativePathOrOpaqueId": source_backed["newIdentity"],
                    "sourceRepo": handoff_binding["identity"].split(":")[0],
                    "immutableRevisionOrUnknown": handoff_binding[
                        "reviewedRevision"
                    ],
                    "artifactDigest": {
                        "treeSha256": source_backed["ssotTreeSha256"].lower(),
                        "files": {
                            path: digest.lower()
                            for path, digest in source_backed["files"].items()
                        },
                    },
                    "representationClass": "source-backed-upstream-archive-exact",
                    "projectionState": "enabled-for-claude-and-codex-as-of-source-record",
                    "activeState": "observed-dated-not-currently-revalidated",
                },
                {
                    "surface": "repository-historical-payload",
                    "observedAt": selection["date"],
                    "sourceEvidenceRef": selection_path,
                    "relativePathOrOpaqueId": "repository:legacy-handoff",
                    "sourceRepo": "historical-repository-payload",
                    "immutableRevisionOrUnknown": "unknown",
                    "artifactDigest": {
                        "harnessTreeHashV1": repository_legacy[
                            "harnessTreeHashV1"
                        ]
                    },
                    "representationClass": "historical-one-file-body",
                    "projectionState": "not-selected-for-arm-c",
                    "activeState": "comparison-only",
                },
                {
                    "surface": "legacy-cc-local-row",
                    "observedAt": legacy["date"],
                    "sourceEvidenceRef": legacy_path,
                    "relativePathOrOpaqueId": "local:handoff",
                    "sourceRepo": "unknown-local-lineage",
                    "immutableRevisionOrUnknown": "unknown",
                    "reviewedUpstreamSource": matt_snapshot["sourceId"],
                    "reviewedUpstreamRevision": matt_snapshot[
                        "currentRevision"
                    ],
                    "artifactDigest": "unknown",
                    "representationClass": "legacy-rewritten-uncompared-occurrence",
                    "projectionState": "historically-projected-before-source-backed-canary",
                    "activeState": "superseded-by-dated-canary",
                    "currentUpstreamPath": legacy_handoff["currentPath"],
                },
            ],
            "collisionRelation": "known-different-plus-one-uncompared-occurrence",
            "disposition": "compare-baseline",
            "recheckTrigger": "fresh-session-loader-trial-or-source-update",
        },
        {
            "id": "repository-contract-chain-root-collision",
            "logicalSkillIds": sorted(contract_names),
            "observedAt": authority["date"],
            "sourceEvidenceRef": authority_path,
            "memberRelations": contract_relations,
            "collisionRelation": "agents-and-codex-equal-cc-and-claude-different",
            "representationClass": "repository-authored-versus-older-cc-tree",
            "activeState": "dated-root-comparison-not-current-loader-proof",
            "disposition": "freeze-pending-host-isolated-ablation",
            "recheckTrigger": "verified-spark-low-task-scoped-exposure",
        },
        {
            "id": "lark-attributed-cross-root-collision-cohort",
            "logicalSkillIds": lark_names,
            "observedAt": authority["date"],
            "sourceEvidenceRefs": [authority_path, inventory_path, live_path],
            "sourceRepo": "larksuite/cli",
            "immutableRevisionOrUnknown": "unknown",
            "artifactDigests": "unknown-per-occurrence",
            "collisionRelation": "same-name-different-skill-md-hash-in-dated-roots",
            "representationClass": "source-attributed-cc-body-versus-different-agent-root-occurrence",
            "projectionState": "dated-root-evidence-not-current-loader-proof",
            "activeState": "unknown-current",
            "atomicCohort": live["criticalCohorts"]["lark"][
                "treatAsAtomicCohort"
            ],
            "substantiveDriftAfterEolNormalization": live[
                "criticalCohorts"
            ]["lark"]["substantiveDriftAfterEolNormalization"],
            "disposition": "freeze-as-atomic-cohort",
            "recheckTrigger": "secret-free-backup-plus-cohort-version-and-portability-review",
        },
        {
            "id": "legacy-matt-mapped-mixed-snapshot",
            "logicalSkillIds": [
                item["logicalSkillId"]
                for item in legacy_matt
            ],
            "observedAt": legacy["date"],
            "sourceEvidenceRef": legacy_path,
            "sourceRepo": "unknown-per-local-occurrence",
            "immutableRevisionOrUnknown": "unknown",
            "reviewedUpstreamSource": matt_snapshot["sourceId"],
            "reviewedUpstreamRevision": matt_snapshot["currentRevision"],
            "wholeTreeExactMatchesToCurrentUpstream": legacy[
                "observations"
            ]["wholeTreeExactMatchesToCurrentUpstream"],
            "mappings": legacy_matt,
            "collisionRelation": "legacy-local-names-map-to-current-renamed-deprecated-or-changed-upstream",
            "representationClass": "mixed-historical-adapted-snapshot",
            "projectionState": "historically-projected-through-cc-local-rows",
            "activeState": "unknown-current-except-handoff-separately-observed",
            "disposition": "candidate-source-review",
            "recheckTrigger": "per-skill-current-revision-delta-and-source-backed-preview",
        },
        {
            "id": "selected-cc-three-source-reconciliation",
            "logicalSkillIds": [
                item["name"]
                for item in selected_cc["skills"]
            ],
            "observedAt": selected_cc["observedAt"],
            "sourceEvidenceRef": overlap_path,
            "observations": [
                {
                    "logicalSkillId": item["name"],
                    "ccPayloadPath": item["path"],
                    "artifactDigest": {
                        "bytes": item["bytes"],
                        "sha256": item["sha256"],
                    },
                    "triggerMode": item["triggerMode"],
                    "triggerBoundary": item["triggerBoundary"],
                    "representationClass": item["lineageState"],
                    "sourceReconciliation": item["sourceReconciliation"],
                    "activeState": (
                        "current-file-bytes-observed-no-enable-or-invocation-proof"
                    ),
                }
                for item in selected_cc["skills"]
            ],
            "collisionRelation": (
                "one-normalized-exact-historical-upstream-plus-two-exact-"
                "repository-adaptations-based-on-historical-upstream"
            ),
            "representationClass": (
                "selected-cc-static-content-lineage-reconciled"
            ),
            "projectionState": (
                "content-bytes-only-no-loader-or-cc-source-row-proof"
            ),
            "activeState": (
                "current-file-bytes-observed-no-enable-or-invocation-proof"
            ),
            "disposition": "compare-baseline",
            "recheckTrigger": (
                "cc-source-row-update-or-task-scoped-host-ablation"
            ),
        },
        {
            "id": "matt-current-content-sample",
            "logicalSkillIds": ["ask-matt", "implement", "code-review"],
            "observedAt": overlap["date"],
            "sourceEvidenceRef": overlap_path,
            "sourceRepo": matt_current["repository"],
            "immutableRevisionOrUnknown": matt_current[
                "currentContentReviewCommit"
            ],
            "artifactDigests": matt_current[
                "currentContentReviewGitBlobShas"
            ],
            "collisionRelation": "official-sample-only-not-cc-occurrence-equality",
            "representationClass": "official-current-content-sample",
            "projectionState": "not-proved-installed-or-exposed",
            "activeState": "comparison-metadata-only",
            "disposition": "compare-baseline",
            "recheckTrigger": "source-delta-or-task-scoped-host-ablation",
        },
        {
            "id": "superpowers-local-plugin-sample",
            "logicalSkillIds": sorted(
                superpowers["localPayloadSha256"]
            ),
            "observedAt": overlap["date"],
            "sourceEvidenceRef": overlap_path,
            "sourceRepo": "unknown-for-local-payload-bytes",
            "immutableRevisionOrUnknown": "unknown",
            "candidateUpstreamRepo": superpowers["repository"],
            "upstreamReleaseReference": superpowers["releaseCommit"],
            "artifactDigests": superpowers["localPayloadSha256"],
            "collisionRelation": "local-digests-pinned-upstream-byte-equality-unproved",
            "representationClass": "runtime-owned-local-plugin-sample",
            "projectionState": "startup-visibility-and-invocation-unproved",
            "activeState": "unknown-current",
            "comparisonBaseline": True,
            "disposition": "runtime-owned-do-not-copy",
            "recheckTrigger": "plugin-update-or-task-scoped-host-ablation",
        },
        {
            "id": "runtime-plugin-alias-reconciliation-gap",
            "logicalSkillIds": [
                item["name"]
                for item in runtime_gap["unresolved"]
            ],
            "observedAt": authority["date"],
            "sourceEvidenceRef": authority_path,
            "databaseDirectoriesMissingPhysical": runtime_gap[
                "databaseDirectoriesMissingPhysical"
            ],
            "runtimeOrPluginMatchesTotal": runtime_gap[
                "runtimeOrPluginMatchesTotal"
            ],
            "unresolved": runtime_gap["unresolved"],
            "collisionRelation": "runtime-or-plugin-alias-match-is-not-cc-source-lineage",
            "representationClass": "runtime-owned-or-unresolved-missing-cc-body",
            "projectionState": "dated-reconciliation-only",
            "activeState": "unknown-current",
            "disposition": "freeze-unresolved-or-runtime-owned-do-not-copy",
            "recheckTrigger": "runtime-or-plugin-version-change-or-cc-reinventory",
        },
    ]

    unique_logical_ids = sorted(
        {
            logical_id
            for group in groups
            for logical_id in group["logicalSkillIds"]
        }
    )
    report = {
        "schema": 1,
        "id": "skill-source-lineage-collision-index-2026-07-24",
        "date": "2026-07-24",
        "status": "derived-dated-evidence-index-no-current-runtime-or-behavior-claim",
        "scope": "repository-evidence-only-no-live-cc-or-agent-home-scan",
        "sourceRecords": [
            _record(path, documents[path], root)
            for path in SOURCE_PATHS
        ],
        "groups": groups,
        "summary": {
            "groupCount": len(groups),
            "uniqueLogicalSkillIdCount": len(unique_logical_ids),
            "sourceRecordCount": len(SOURCE_PATHS),
            "datedSourceRecordDates": sorted(
                {documents[path]["date"] for path in SOURCE_PATHS}
            ),
            "currentRuntimeSnapshot": False,
            "allOccurrencesExhaustivelyIndexed": False,
        },
        "authorityBoundary": {
            "liveCcSwitchReadAuthorized": False,
            "agentHomeReadAuthorized": False,
            "installOrEnableAuthorized": False,
            "relinkOrProjectionRepairAuthorized": False,
            "migrationAuthorized": False,
            "deletionOrCleanupAuthorized": False,
            "commitOrPushAuthorized": False,
        },
        "claimBoundary": {
            "currentCcDatabaseTruthProved": False,
            "currentProjectionOrLoaderStateProved": False,
            "sourceAttributionProvesInvocation": False,
            "contentDigestProvesBehavioralEquivalence": False,
            "localSuperpowersBytesEqualReleaseProved": False,
            "legacyMattLikePoolIsCurrentMattSuiteProved": False,
            "selectedCcInstallOrSourceRowProvenanceProved": False,
            "crossDeviceEqualityProved": False,
            "residualSelfAuthoredGapProved": False,
            "safeMigrationOrDeletionProved": False,
        },
        "nonActions": [
            "no live CC Switch database or settings read",
            "no Agent Home or CC Skill body scan",
            "no network fetch or candidate download",
            "no Skill install enable disable relink migration or deletion",
            "no commit push release or publication",
        ],
        "nextGate": (
            "Use this dated index to select exact per-Skill source and collision "
            "questions; re-observe only the bound occurrence needed for that "
            "decision, then require host invocation evidence before any "
            "behavior or replacement claim."
        ),
    }
    report["reportSha256"] = canonical_sha256(report)
    return report


def validate_index(
    document: dict[str, Any],
    root: Path = ROOT,
) -> list[str]:
    failures: list[str] = []
    if not isinstance(document, dict):
        return ["fail-document-shape"]
    body = dict(document)
    digest = body.pop("reportSha256", None)
    if digest != canonical_sha256(body):
        failures.append("fail-report-digest")
    if (
        document.get("schema") != 1
        or document.get("id")
        != "skill-source-lineage-collision-index-2026-07-24"
        or document.get("status")
        != "derived-dated-evidence-index-no-current-runtime-or-behavior-claim"
        or document.get("scope")
        != "repository-evidence-only-no-live-cc-or-agent-home-scan"
    ):
        failures.append("fail-index-identity")
    source_records = document.get("sourceRecords")
    if (
        not isinstance(source_records, list)
        or [item.get("path") for item in source_records] != list(SOURCE_PATHS)
    ):
        failures.append("fail-source-record-coverage")
    else:
        for item in source_records:
            path = item.get("path")
            if (
                not isinstance(path, str)
                or not (root / path).is_file()
                or item.get("sha256") != file_sha256(root / path)
            ):
                failures.append("fail-source-record-digest")
                break
    groups = document.get("groups")
    if (
        not isinstance(groups, list)
        or [group.get("id") for group in groups] != list(GROUP_IDS)
    ):
        failures.append("fail-group-coverage")
    else:
        for group in groups:
            if (
                not isinstance(group.get("logicalSkillIds"), list)
                or not group["logicalSkillIds"]
                or group.get("disposition") not in ALLOWED_DISPOSITIONS
                or not group.get("collisionRelation")
                or not group.get("recheckTrigger")
            ):
                failures.append("fail-group-boundary")
                break
    summary = document.get("summary")
    if (
        not isinstance(summary, dict)
        or summary.get("groupCount") != len(GROUP_IDS)
        or summary.get("sourceRecordCount") != len(SOURCE_PATHS)
        or summary.get("datedSourceRecordDates")
        != ["2026-07-18", "2026-07-19", "2026-07-23"]
        or summary.get("currentRuntimeSnapshot") is not False
        or summary.get("allOccurrencesExhaustivelyIndexed") is not False
    ):
        failures.append("fail-summary-boundary")
    for key in ("authorityBoundary", "claimBoundary"):
        boundary = document.get(key)
        if (
            not isinstance(boundary, dict)
            or not boundary
            or any(value is not False for value in boundary.values())
        ):
            failures.append(f"hard-fail-{key}-promotion")
    non_actions = " ".join(document.get("nonActions", []))
    for phrase in (
        "no live CC Switch database",
        "no Agent Home",
        "no network fetch",
        "no Skill install",
        "no commit",
    ):
        if phrase not in non_actions:
            failures.append("fail-non-action-boundary")
            break
    return list(dict.fromkeys(failures))


def main() -> int:
    document = build_index()
    print(json.dumps(document, ensure_ascii=False, indent=2))
    return 0 if not validate_index(document) else 1


if __name__ == "__main__":
    raise SystemExit(main())
