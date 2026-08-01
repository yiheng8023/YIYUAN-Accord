#!/usr/bin/env python3
"""Validate the Codex 0.146.0 MCP reload-release version-change evidence."""

from __future__ import annotations

from datetime import datetime
import hashlib
import json
from pathlib import Path
from typing import Any

try:
    from .probe_codex_app_server_mcp_reload_release_attribution import (
        PROBE_ID,
        same_process_identity,
        status_reports_callable_sentinel_tools,
    )
    from .validate_mcp_reload_release_attribution_evidence import _recompute_raw
except ImportError:  # pragma: no cover - direct script execution
    from probe_codex_app_server_mcp_reload_release_attribution import (
        PROBE_ID,
        same_process_identity,
        status_reports_callable_sentinel_tools,
    )
    from validate_mcp_reload_release_attribution_evidence import _recompute_raw


ROOT = Path(__file__).resolve().parent.parent
EVIDENCE_PATH = (
    "registry/mcp-app-server-0.146.0-reload-release-version-change-"
    "evidence-2026-08-02.json"
)
DOC_PATH = (
    "docs/mcp-app-server-0.146.0-reload-release-version-change-"
    "evidence-2026-08-02.md"
)
AUDIT_ROOT = "audits/mcp-reload-release-attribution-0.146.0-2026-08-02"
README_PATH = f"{AUDIT_ROOT}/README.md"
PROGRAM_ACCEPTANCE_PATH = "registry/program-acceptance-map.json"
PROGRAM_ACCEPTANCE_ID = "acceptance.dynamic-runtime-control-gap-research"
PROGRAM_EVIDENCE_ID = (
    "evidence.mcp-app-server-0.146.0-reload-release-version-change-2026-08-02"
)
EXPECTED_RAW_PATHS = [f"{AUDIT_ROOT}/evidence-{index:02d}.json" for index in range(1, 4)]
REQUIRED_FILES = (
    EVIDENCE_PATH,
    DOC_PATH,
    README_PATH,
    *EXPECTED_RAW_PATHS,
    "scripts/validate_mcp_reload_release_version_change_evidence.py",
    "tests/test_mcp_reload_release_version_change_evidence.py",
)

EXPECTED_PULL_REQUESTS = [
    (34550, "27a9c4d6bd1f6875127a2f0f6c2c10d95b5e5b09", "thread-scoped-refresh-regression-coverage"),
    (34930, "e497325a6a1743cfadeee41a6b5f05ebf7fd0221", "thread-mcp-runtime-ownership-and-atomic-publication"),
    (34952, "e19e65317a333ce725b18ac6f1e3bc904b74d2a1", "connection-reconciliation-and-reuse"),
    (35151, "f201c30c52a35f819262865a53df94b6f4ea7a50", "explicit-refresh-reconnect"),
    (35204, "3645a4397c4889ea483a3b9a61ad7cf5921aa384", "thread-startup-runtime-invalidation"),
    (35216, "58b427722857117ac3e702b9eb406d47616022e2", "best-effort-config-refresh-across-threads"),
]
EXPECTED_SOURCE_FILES = [
    (
        "codex-rs/codex-mcp/src/runtime.rs",
        "9cad1c0251a5a61f2da6f8efc9aff8518bc44cc2",
        23972,
        "38ea69ec3fab3e40e4c67ea216e76a41ab5ad1e17d2b025247f2b86ddae2bd3a",
    ),
    (
        "codex-rs/codex-mcp/src/connection_manager.rs",
        "2e6be9864f842d56d93535e34597875fc185ce14",
        26654,
        "5749cd2486041e1a53b63f9d6cec81d1a5413d5211cba8fed427f83687d770cf",
    ),
    (
        "codex-rs/codex-mcp/src/rmcp_client.rs",
        "8901c3672314e9010af8e4c5a370ae1b095e5b45",
        42837,
        "7e73d5feadc299906753f2aafcc6601cd58fb36784fc46bd220a5ebf54b48474",
    ),
]


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load_json(path: Path) -> dict[str, Any]:
    document = json.loads(path.read_text(encoding="utf-8"))
    _require(isinstance(document, dict), f"JSON document is not an object: {path}")
    return document


def _exact_identity(sample: dict[str, Any], baseline: dict[str, Any]) -> bool:
    return same_process_identity(baseline, sample)


def load_bound_raw_reports(
    document: dict[str, Any], *, root: Path = ROOT
) -> list[dict[str, Any]]:
    bindings = document.get("formalEvidence")
    _require(
        isinstance(bindings, list)
        and [item.get("path") for item in bindings if isinstance(item, dict)]
        == EXPECTED_RAW_PATHS,
        "0.146.0 formal evidence paths drifted",
    )
    reports: list[dict[str, Any]] = []
    for repetition, binding in enumerate(bindings, start=1):
        _require(isinstance(binding, dict), "0.146.0 raw binding is invalid")
        path = root / str(binding.get("path"))
        _require(path.is_file(), f"0.146.0 raw report is missing: {path}")
        _require(path.stat().st_size == binding.get("bytes"), f"0.146.0 raw bytes drifted: {path}")
        _require(_sha256(path) == binding.get("sha256"), f"0.146.0 raw hash drifted: {path}")
        raw = _load_json(path)
        baseline = raw.get("toolCalls", {}).get("baseline", {})
        threads = raw.get("threads", {})
        _require(
            baseline.get("pid") == binding.get("baselinePid")
            and baseline.get("instanceId") == binding.get("baselineInstanceId")
            and threads.get("a", {}).get("id") == binding.get("threadA")
            and threads.get("b", {}).get("id") == binding.get("threadB"),
            f"0.146.0 raw binding drifted in repetition {repetition}",
        )
        reports.append(raw)
    return reports


def validate_raw_report(raw: dict[str, Any], *, repetition: int) -> dict[str, Any]:
    _require(
        raw.get("schema") == 1
        and raw.get("id") == PROBE_ID
        and raw.get("hostBinding", {}).get("codexVersion") == "codex-cli 0.146.0",
        f"0.146.0 raw identity drifted in repetition {repetition}",
    )
    _require(
        raw.get("hostBinding", {}).get("probeScriptSha256")
        == "c418737169a3133bc0bfb2df18e7b26600158c2bcd98b28a004f4dec79d83e4b"
        and raw.get("hostBinding", {}).get("sentinelScriptSha256")
        == "48656683eaff80d0162fc230b111880ee59cc619475187531b09c341136ee590",
        f"0.146.0 raw producer binding drifted in repetition {repetition}",
    )
    recomputed = _recompute_raw(raw)
    recorded = raw.get("classification")
    compared_keys = (
        "classification",
        "valid",
        "invalidReasons",
        "reloadReleaseObserved",
        "loadedRuntimeRetained",
        "sameIdentityBySample",
        "finalSameProcessIdentity",
        "postWindowCallSameInstance",
    )
    _require(
        isinstance(recorded, dict)
        and all(recorded.get(key) == recomputed.get(key) for key in compared_keys)
        and recomputed.get("classification") == "reload-release-observed-bounded"
        and recomputed.get("reloadReleaseObserved") is True,
        f"0.146.0 raw classification drifted in repetition {repetition}",
    )

    calls = raw.get("toolCalls", {})
    baseline_call = calls.get("baseline", {})
    post_call = calls.get("postWindowSameThread", {})
    recovery_call = calls.get("restoredNewThreadControl", {})
    _require(
        baseline_call.get("succeeded") is True
        and post_call.get("succeeded") is False
        and post_call.get("error", {}).get("message")
        == "unknown MCP server 'lifecycle_sentinel'"
        and recovery_call.get("succeeded") is True,
        f"0.146.0 raw call boundary drifted in repetition {repetition}",
    )
    status = raw.get("statusAfterDisableReload", {})
    _require(
        status.get("succeeded") is True
        and status.get("sentinelPresent") is True
        and not status_reports_callable_sentinel_tools(status),
        f"0.146.0 raw status boundary drifted in repetition {repetition}",
    )

    process = raw.get("processObservation", {})
    baseline = process.get("baseline", {})
    samples = process.get("samples", [])
    stop_events = process.get("stopEventsInAttributionWindow", [])
    cleanup = process.get("cleanup", {})
    _require(
        len(samples) == 21
        and len(stop_events) == 1
        and stop_events[0].get("pid") == baseline_call.get("pid")
        and stop_events[0].get("instanceId") == baseline_call.get("instanceId")
        and process.get("appServerAliveThroughWindow") is True
        and process.get("appServerReturnCode") == 0
        and process.get("appServerKillSent") is False
        and cleanup.get("cleanupVerified") is True
        and cleanup.get("pidSignalCleanupUsed") is False,
        f"0.146.0 raw process or cleanup boundary drifted in repetition {repetition}",
    )
    same_identity_count = sum(_exact_identity(sample, baseline) for sample in samples)
    pid_reuse_count = sum(
        sample.get("exists") is True
        and sample.get("pid") == baseline.get("pid")
        and not _exact_identity(sample, baseline)
        for sample in samples
    )
    _require(
        same_identity_count == 2
        and not _exact_identity(samples[-1], baseline),
        f"0.146.0 exact process identity drifted in repetition {repetition}",
    )

    isolation = raw.get("isolation", {})
    claims = raw.get("claimBoundary", {})
    configuration = raw.get("configuration", {})
    reload_observation = raw.get("reloadObservation", {})
    _require(
        isolation.get("defaultCodexHomeRejected") is True
        and isolation.get("currentAuthCopied") is False
        and isolation.get("currentPluginsCopied") is False
        and isolation.get("authStateProduced") is False
        and isolation.get("applicationLogExternalNetworkAttemptObserved") is True
        and claims.get("modelTurnStarted") is False
        and claims.get("modelRequestSent") is False
        and claims.get("provesReloadCausedOldRuntimeRelease") is True
        and claims.get("provesNoNetworkTraffic") is False
        and configuration.get("restoredBytesEqualBefore") is True
        and reload_observation.get("newThreadDuringAttributionWindow") is False
        and reload_observation.get("unsubscribeDuringAttributionWindow") is False
        and reload_observation.get("teardownDuringAttributionWindow") is False
        and reload_observation.get("harnessCleanupDuringAttributionWindow") is False
        and reload_observation.get("pidSignalDuringAttributionWindow") is False,
        f"0.146.0 isolation or authority boundary drifted in repetition {repetition}",
    )

    all_events = process.get("eventsBeforeHarnessCleanup", [])
    post_restore_starts = {
        event.get("instanceId")
        for event in all_events
        if event.get("event") == "instance-start"
        and event.get("instanceId") != baseline_call.get("instanceId")
    }
    _require(
        len(post_restore_starts) == 2,
        f"0.146.0 post-restore instance observation drifted in repetition {repetition}",
    )
    response_at = datetime.fromisoformat(reload_observation["reloadResponseAt"])
    stop_at = datetime.fromisoformat(stop_events[0]["timestamp"])
    release_latency_ms = (stop_at - response_at).total_seconds() * 1000
    return {
        "reloadReleaseObserved": True,
        "loadedRuntimeRetained": False,
        "sampleCount": len(samples),
        "sameExactIdentityCount": same_identity_count,
        "stopEventCount": len(stop_events),
        "postWindowUnknownServer": True,
        "configRestored": True,
        "recoverySucceeded": True,
        "postRestoreDistinctSentinelStartCount": len(post_restore_starts),
        "cleanupVerified": True,
        "gracefulAppServerShutdown": True,
        "externalAttemptObserved": True,
        "pidReuseDifferentIdentityCount": pid_reuse_count,
        "releaseLatencyMilliseconds": round(release_latency_ms, 3),
        "exactBaselineIdentityAbsentByWindowEnd": True,
    }


def _validate_official_snapshot(snapshot: Any) -> None:
    _require(isinstance(snapshot, dict), "0.146.0 official source snapshot is invalid")
    prs = snapshot.get("relevantPullRequests")
    sources = snapshot.get("sourceFiles")
    _require(
        snapshot.get("repository") == "openai/codex"
        and snapshot.get("releaseTag") == "rust-v0.146.0"
        and snapshot.get("annotatedTagObject") == "be449751a978f02e5bbba886999662956c7f38f5"
        and snapshot.get("releaseCommit") == "e363b08c9175ac1cbe5893615dd2cb9ddf95043b"
        and snapshot.get("publishedAt") == "2026-07-29T01:42:51Z"
        and snapshot.get("releaseUrl")
        == "https://github.com/openai/codex/releases/tag/rust-v0.146.0"
        and isinstance(prs, list)
        and [
            (item.get("number"), item.get("mergeCommit"), item.get("role"))
            for item in prs
        ]
        == EXPECTED_PULL_REQUESTS
        and isinstance(sources, list)
        and [
            (item.get("path"), item.get("gitBlob"), item.get("bytes"), item.get("sha256"))
            for item in sources
        ]
        == EXPECTED_SOURCE_FILES
        and snapshot.get("boundedInterpretation")
        == {
            "threadScopedRuntimeAndAtomicPublicationPresent": True,
            "unchangedConnectionsMayBeReused": True,
            "explicitRefreshRequestsFreshConnections": True,
            "connectionAndClientShutdownPathsPresent": True,
            "sourceAloneProvesObservedProcessRelease": False,
            "sourceAloneProvesTaskEndRelease": False,
            "sourceAloneProvesResourceBenefit": False,
        },
        "0.146.0 official source snapshot drifted",
    )


def validate_evidence(
    document: dict[str, Any],
    *,
    root: Path = ROOT,
    program_map: dict[str, Any] | None = None,
) -> None:
    _require(
        document.get("schema") == 1
        and document.get("id")
        == "mcp-app-server-0.146.0-reload-release-version-change-evidence-2026-08-02"
        and document.get("date") == "2026-08-02"
        and document.get("status")
        == (
            "observed-three-repetition-single-host-version-bounded-config-"
            "disable-plus-reload-release"
        ),
        "0.146.0 reload-release evidence identity drifted",
    )
    _validate_official_snapshot(document.get("officialSourceSnapshot"))
    host = document.get("hostBinding", {})
    _require(
        host.get("codexVersion") == "codex-cli 0.146.0"
        and host.get("probeId") == PROBE_ID
        and host.get("observationSecondsPerRepetition") == 10.0
        and host.get("sampleIntervalSeconds") == 0.5
        and host.get("formalRepetitionCount") == 3
        and host.get("postRunBinaryObservation", {}).get("rawReportSelfBindsBinaryDigest")
        is False,
        "0.146.0 host binding drifted",
    )
    for key in ("probeScript", "sentinel"):
        binding = host.get(key, {})
        path = root / str(binding.get("path"))
        _require(
            path.is_file() and _sha256(path) == binding.get("sha256"),
            f"0.146.0 {key} binding drifted",
        )

    raw_reports = load_bound_raw_reports(document, root=root)
    summaries = [
        validate_raw_report(raw, repetition=index)
        for index, raw in enumerate(raw_reports, start=1)
    ]
    aggregate = {
        "validRepetitionCount": len(summaries),
        "reloadReleaseObservedCount": sum(item["reloadReleaseObserved"] for item in summaries),
        "loadedRuntimeRetainedCount": sum(item["loadedRuntimeRetained"] for item in summaries),
        "exactProcessIdentitySampleCount": sum(item["sampleCount"] for item in summaries),
        "sameExactIdentitySampleCount": sum(item["sameExactIdentityCount"] for item in summaries),
        "attributionWindowStopEventCount": sum(item["stopEventCount"] for item in summaries),
        "postWindowSameThreadUnknownServerCount": sum(item["postWindowUnknownServer"] for item in summaries),
        "exactConfigRestoreCount": sum(item["configRestored"] for item in summaries),
        "restoredNewThreadControlSuccessCount": sum(item["recoverySucceeded"] for item in summaries),
        "postRestoreDistinctSentinelStartCount": sum(item["postRestoreDistinctSentinelStartCount"] for item in summaries),
        "verifiedCleanupCount": sum(item["cleanupVerified"] for item in summaries),
        "gracefulAppServerShutdownCount": sum(item["gracefulAppServerShutdown"] for item in summaries),
        "applicationLogExternalNetworkAttemptCount": sum(item["externalAttemptObserved"] for item in summaries),
        "pidReuseDifferentIdentityCount": sum(item["pidReuseDifferentIdentityCount"] for item in summaries),
        "releaseLatencyMilliseconds": [item["releaseLatencyMilliseconds"] for item in summaries],
    }
    _require(
        aggregate == document.get("aggregateObservation"),
        "0.146.0 aggregate observation drifted",
    )
    _require(
        document.get("rawProducerClaimCorrection")
        == {
            "field": "claimBoundary.provesReloadCausedOldRuntimeRelease",
            "recordedValue": True,
            "canonicalDisposition": (
                "rejected-confounded-by-prior-config-disable-no-ablation"
            ),
            "rawFilesPreservedUnmodified": True,
            "canonicalAllowedClaim": (
                "release-observed-after-config-disable-plus-reload"
            ),
        },
        "0.146.0 raw producer claim correction drifted",
    )
    _require(
        document.get("versionComparison")
        == {
            "priorEvidence": "registry/mcp-app-server-0.145.0-reload-release-attribution-evidence-2026-07-27.json",
            "priorResult": "three-of-three-loaded-runtime-retained-for-five-seconds",
            "currentResult": (
                "three-of-three-exact-baseline-runtimes-released-after-config-"
                "disable-plus-reload-inside-ten-second-window"
            ),
            "behaviorChangedAcrossBoundVersions": True,
            "crossVersionParityProved": False,
            "priorEvidenceInvalidatedForItsBoundVersion": False,
        },
        "0.146.0 version comparison drifted",
    )
    decision = document.get("decision", {})
    _require(
        decision.get(
            "boundedNativeSameThreadConfigDisablePlusReloadAndReleaseObserved"
        )
        is True
        and decision.get("nativeCurrentVersionMustPrecedeCustomController") is True
        and decision.get("selfAuthoredControllerEligible") is False
        and decision.get("dynamicRuntimeControlAssessment")
        == "partial-native-current-version-win"
        and decision.get("remainingDecisionGaps")
        == [
            "task-end-versus-config-disable-semantics",
            "concurrent-or-overlapping-owner-safety",
            "per-thread-runtime-multiplication-cost",
            "arbitrary-local-stdio-and-remote-http-behavior",
            "stable-total-host-resource-benefit",
            "failure-recovery-and-rollback",
        ],
        "0.146.0 decision drifted",
    )
    expected_claims = {
        "reloadAloneCausedReleaseProved": False,
        "taskEndImmediateReleaseProved": False,
        "sameThreadHotEnableDisableForArbitraryMcpProved": False,
        "leaseOrReferenceCountProved": False,
        "perThreadOneProcessRuleProved": False,
        "stableResourceSavingsProved": False,
        "genericCrashRecoveryProved": False,
        "remoteHttpLifecycleProved": False,
        "crossHostParityProved": False,
        "crossVersionParityProved": False,
        "noNetworkTrafficProved": False,
        "residualNeedForSelfAuthoredControllerProved": False,
        "productionReadinessProved": False,
    }
    _require(document.get("claimBoundary") == expected_claims, "0.146.0 claim boundary drifted")

    cleanup = document.get("cleanupDisposition", {})
    _require(
        cleanup
        == {
            "repositoryAudit": "retain-three-raw-reports-and-derived-evidence",
            "isolatedProbeRootsRemoved": True,
            "repositoryTmpRootEmptyAfterRemoval": True,
            "deletionAuthorizedForRetainedAudit": False,
        }
        and all(
            not (root / f".tmp/mcp-reload-0.146.0-20260802-run{index:02d}").exists()
            for index in range(1, 4)
        ),
        "0.146.0 cleanup disposition drifted",
    )
    _require((root / DOC_PATH).is_file() and (root / README_PATH).is_file(), "0.146.0 documentation is missing")

    if program_map is None:
        program_map = _load_json(root / PROGRAM_ACCEPTANCE_PATH)
    acceptances = program_map.get("acceptanceCriteria", [])
    evidence_items = program_map.get("evidence", [])
    acceptance = [item for item in acceptances if item.get("id") == PROGRAM_ACCEPTANCE_ID]
    evidence = [item for item in evidence_items if item.get("id") == PROGRAM_EVIDENCE_ID]
    _require(
        len(acceptance) == 1
        and acceptance[0].get("assessment") == "partial"
        and PROGRAM_EVIDENCE_ID in acceptance[0].get("evidenceIds", []),
        "0.146.0 acceptance mapping drifted",
    )
    _require(
        evidence
        == [
            {
                "id": PROGRAM_EVIDENCE_ID,
                "path": EVIDENCE_PATH,
                "kind": "official-source-bound-three-repetition-current-version-native-reload-release-no-model-no-residual-gap-promotion",
                "asOf": "2026-08-02",
                "supports": [PROGRAM_ACCEPTANCE_ID],
            }
        ],
        "0.146.0 program evidence mapping drifted",
    )


def main() -> int:
    document = _load_json(ROOT / EVIDENCE_PATH)
    validate_evidence(document, root=ROOT)
    print("Codex 0.146.0 MCP reload-release version-change evidence passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
