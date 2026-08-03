#!/usr/bin/env python3
"""Validate the offline observer acquisition-path admission gate."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

try:
    from .repository_text_identity import (
        windows_crlf_projection_sha256 as _shared_windows_crlf_projection_sha256,
    )
except ImportError:  # pragma: no cover - direct script execution
    from repository_text_identity import (
        windows_crlf_projection_sha256 as _shared_windows_crlf_projection_sha256,
    )


ROOT = Path(__file__).resolve().parent.parent
RECORD_PATH = (
    "registry/"
    "mcp-thread-creator-close-observer-acquisition-path-admission-"
    "2026-07-27.json"
)
DOCUMENTATION_PATH = (
    "docs/"
    "mcp-thread-creator-close-observer-acquisition-path-admission-"
    "2026-07-27.md"
)
PROTOCOL_PATH = (
    "registry/"
    "mcp-thread-creator-connection-close-attribution-protocol-2026-07-27.json"
)
PROTOCOL_SHA256 = (
    "8A110058AAC75DDC54E2B3795F6F6BE12004E4CDE0262045BEA79D112D157326"
)
PROBE_PATH = (
    "scripts/probe_codex_app_server_mcp_thread_creator_connection_close.py"
)
PROBE_SHA256 = (
    "66CF7066B68D92139653C5E41AD74CAA64D00273C662A2899E396501974C2CF6"
)
CALIBRATION_PATH = (
    "registry/"
    "mcp-thread-creator-connection-close-calibration-attempt-2026-07-27.json"
)
CALIBRATION_SHA256 = (
    "D0872E69083A79A87CDF9D3A269E6AC53E676AE7D2EAA4AFF97110618BE3A0FA"
)
MULTI_EVIDENCE_PATH = (
    "registry/"
    "mcp-app-server-0.145.0-multi-connection-subscription-preflight-"
    "evidence-2026-07-27.json"
)
MULTI_EVIDENCE_SHA256 = (
    "ED3047D4EDC8B1FC437A1EF90E5DDB9C660078CE6D66B98112CEEF83E76F3E22"
)
REPORT_BINDINGS = (
    {
        "path": (
            "audits/mcp-multi-connection-subscription-preflight-0.145.0-"
            "2026-07-27/run-01/report.json"
        ),
        "sha256": (
            "F4C0230E4C87C8499365F892671FA41BD5B4A615EB7539A73557D65C278CCB5D"
        ),
        "reportSha256": (
            "F8036D42AD148A0C4B11F61EB2D25E2C4F4B4CC13F9BEED67E60CAA3E6004D04"
        ),
    },
    {
        "path": (
            "audits/mcp-multi-connection-subscription-preflight-0.145.0-"
            "2026-07-27/run-02/report.json"
        ),
        "sha256": (
            "769BA186566817C5120BEDA3769D4C4B870C303A1A4540EA36FC47B2F077DC2D"
        ),
        "reportSha256": (
            "A37A5308B878210870A341F928D7B580D8E4710C5CD369FDDE55C9A8B1BA8F2C"
        ),
    },
    {
        "path": (
            "audits/mcp-multi-connection-subscription-preflight-0.145.0-"
            "2026-07-27/run-03/report.json"
        ),
        "sha256": (
            "C9D569B30F80DA680A46C79A8650F7ECB9B61E6298D4748326447F0F883E8E36"
        ),
        "reportSha256": (
            "6B28F7D0AA804608D1C2A721D4BA9E364EAF3C59F8A945F3382A704CEBD71359"
        ),
    },
)
CONCLUSION = "offline-amendment-required-before-live"
EXPECTED_TOP_LEVEL_KEYS = {
    "schema",
    "id",
    "date",
    "status",
    "purpose",
    "sourceBindings",
    "machineVerifiedObservation",
    "currentConflict",
    "requiredOfflineAmendment",
    "admissionDecision",
    "executionBoundary",
    "claimBoundary",
    "documentation",
}
EXPECTED_CLAIM_KEYS = {
    "autoAttachIsSecondSubscriptionProved",
    "autoAttachCreatesIndependentOwnerProved",
    "leaseOrReferenceCountProved",
    "taskEndSemanticsProved",
    "finalReleaseSemanticsProved",
    "resourceBenefitProved",
    "crossHostParityProved",
    "crossVersionParityProved",
    "selfAuthoredControllerNeedProved",
    "liveReadinessProved",
}


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def windows_crlf_projection_sha256(path: Path) -> str:
    return _shared_windows_crlf_projection_sha256(path, uppercase=True)


def canonical_json_sha256(value: Any) -> str:
    encoded = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest().upper()


def load_json_object(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    _require(isinstance(value, dict), f"JSON object required: {path}")
    return value


def validate_protocol_probe_conflict(
    protocol: dict[str, Any],
    probe_source: str,
) -> None:
    sequence = protocol.get("design", {}).get("setupSequence")
    _require(
        isinstance(sequence, list)
        and any("resumes the same thread" in str(item) for item in sequence),
        "Current protocol no longer requires thread/resume in setup",
    )
    _require(
        "thread/resume"
        in protocol.get("design", {})
        .get("window", {})
        .get("forbiddenActions", []),
        "Current protocol window thread/resume boundary drifted",
    )
    _require(
        '"thread/resume"' in probe_source
        and 'phase="observer-thread-resume"' in probe_source,
        "Current probe no longer contains its thread/resume acquisition path",
    )


def validate_formal_report(report: dict[str, Any]) -> None:
    stored_report_hash = report.get("reportSha256")
    without_hash = dict(report)
    without_hash.pop("reportSha256", None)
    _require(
        isinstance(stored_report_hash, str)
        and canonical_json_sha256(without_hash) == stored_report_hash,
        "Formal report canonical hash drifted",
    )

    host = report.get("host", {})
    thread = report.get("thread", {})
    connections = report.get("connections", {})
    owner_a = connections.get("owner-a", {})
    owner_b = connections.get("owner-b", {})
    bridge_a = owner_a.get("bridgeProcess", {})
    bridge_b = owner_b.get("bridgeProcess", {})
    thread_id = thread.get("id")
    _require(
        host.get("singleAppServerProcess") is True
        and host.get("appServerProcess", {}).get("exists") is True,
        "Formal report does not bind one live app-server",
    )
    _require(
        bridge_a.get("exists") is True
        and bridge_b.get("exists") is True
        and isinstance(bridge_a.get("pid"), int)
        and isinstance(bridge_b.get("pid"), int)
        and bridge_a["pid"] != bridge_b["pid"],
        "Formal report does not bind two distinct bridge processes",
    )
    _require(
        isinstance(thread_id, str)
        and thread_id
        and thread.get("subscriptionAcquisitionPath")
        == "thread-created-auto-attach",
        "Formal report acquisition path or thread binding drifted",
    )

    a_ledger = owner_a.get("requestLedger")
    b_ledger = owner_b.get("requestLedger")
    _require(
        isinstance(a_ledger, list) and isinstance(b_ledger, list),
        "Formal report request ledger is missing",
    )
    a_thread_entries = [entry for entry in a_ledger if entry.get("threadId")]
    b_thread_entries = [entry for entry in b_ledger if entry.get("threadId")]
    _require(
        a_thread_entries
        and b_thread_entries
        and all(entry.get("threadId") == thread_id for entry in a_thread_entries)
        and all(entry.get("threadId") == thread_id for entry in b_thread_entries),
        "Formal report does not bind both connections to one thread",
    )
    _require(
        not any(entry.get("method") == "thread/resume" for entry in b_ledger)
        and any(
            entry.get("method") == "mcpServer/tool/call"
            and entry.get("phase") == "owner-b-joined-call"
            and entry.get("threadId") == thread_id
            and entry.get("succeeded") is True
            for entry in b_ledger
        ),
        "Formal report does not contain connection-B direct call evidence",
    )

    sentinel = report.get("sentinel", {})
    calls = [
        sentinel.get("baselineCall", {}),
        sentinel.get("ownerBJoinedCall", {}),
        sentinel.get("ownerBAfterOwnerAReleaseCall", {}),
    ]
    pids = {call.get("pid") for call in calls}
    instances = {call.get("instanceId") for call in calls}
    _require(
        all(
            call.get("succeeded") is True
            and call.get("server")
            == "agent-autonomy-harness-mcp-lifecycle-sentinel"
            and call.get("tool") == "identity"
            for call in calls
        )
        and len(pids) == 1
        and None not in pids
        and len(instances) == 1
        and None not in instances
        and sentinel.get("process", {}).get("pid") in pids,
        "Formal report does not bind the same exact Sentinel across connections",
    )
    _require(
        thread.get("modelTurnRequests") == 0
        and thread.get("turnStartedNotifications") == 0,
        "Formal report contains a model turn",
    )

    classification = report.get("classification", {})
    _require(
        classification.get("valid") is True
        and classification.get("classification")
        == "second-connection-subscription-not-observed-bounded"
        and classification.get("distinctClientConnectionsObserved") is True
        and classification.get("sameLoadedThreadObserved") is True
        and classification.get("sameExactSentinelObservedAcrossConnections")
        is True
        and classification.get("modelTurnRequested") is False
        and classification.get("secondConnectionSubscriptionObserved")
        is False,
        "Formal report classification or non-subscription boundary drifted",
    )


def _validate_sources(record: dict[str, Any], *, root: Path) -> None:
    bindings = record.get("sourceBindings")
    _require(isinstance(bindings, dict), "Source bindings are missing")
    expected = {
        "protocol": {"path": PROTOCOL_PATH, "sha256": PROTOCOL_SHA256},
        "currentProbe": {"path": PROBE_PATH, "sha256": PROBE_SHA256},
        "invalidCalibration": {
            "path": CALIBRATION_PATH,
            "sha256": CALIBRATION_SHA256,
        },
        "multiConnectionEvidence": {
            "path": MULTI_EVIDENCE_PATH,
            "sha256": MULTI_EVIDENCE_SHA256,
        },
        "formalReports": list(REPORT_BINDINGS),
    }
    _require(bindings == expected, "Exact source bindings drifted")
    for binding in (
        expected["protocol"],
        expected["currentProbe"],
        expected["invalidCalibration"],
        expected["multiConnectionEvidence"],
        *expected["formalReports"],
    ):
        path = root / str(binding["path"])
        observed_hash = (
            windows_crlf_projection_sha256(path)
            if binding in expected["formalReports"] and path.is_file()
            else file_sha256(path) if path.is_file() else None
        )
        _require(
            path.is_file() and observed_hash == binding["sha256"],
            f"Bound source SHA256 drifted: {binding['path']}",
        )

    protocol = load_json_object(root / PROTOCOL_PATH)
    probe_source = (root / PROBE_PATH).read_text(encoding="utf-8")
    validate_protocol_probe_conflict(protocol, probe_source)

    calibration = load_json_object(root / CALIBRATION_PATH)
    _require(
        calibration.get("attempt", {}).get("pairedWindowEntered") is False
        and calibration.get("attempt", {}).get("formalLivePairedRunCount") == 0
        and calibration.get("remediation", {}).get("liveRerunPerformed")
        is False
        and calibration.get("authorityIncident", {}).get(
            "incidentDoesNotAuthorizeContinuation"
        )
        is True,
        "Invalid calibration boundary drifted",
    )
    _require(
        calibration.get("probe", {}).get("currentSha256") == PROBE_SHA256,
        "Invalid calibration current-probe binding drifted",
    )

    evidence = load_json_object(root / MULTI_EVIDENCE_PATH)
    _require(
        evidence.get("preflightDesign", {}).get("formalAcquisitionPath")
        == "thread-created-auto-attach"
        and evidence.get("aggregateObservation", {}).get(
            "protocolValidRunCount"
        )
        == 3
        and evidence.get("aggregateObservation", {}).get(
            "sameThreadSameExactSentinelCallPairCount"
        )
        == 3
        and evidence.get("decision", {}).get(
            "secondIndependentlyReleasableSubscriptionObserved"
        )
        is False,
        "Multi-connection evidence boundary drifted",
    )
    formal_evidence = evidence.get("formalEvidence")
    _require(
        isinstance(formal_evidence, list)
        and len(formal_evidence) == len(REPORT_BINDINGS),
        "Multi-connection formal report bindings drifted",
    )
    for binding, summary in zip(REPORT_BINDINGS, formal_evidence, strict=True):
        _require(
            all(summary.get(key) == value for key, value in binding.items()),
            "Multi-connection formal report bindings drifted",
        )
        report = load_json_object(root / binding["path"])
        _require(
            report.get("reportSha256") == binding["reportSha256"],
            f"Formal report embedded SHA256 drifted: {binding['path']}",
        )
        validate_formal_report(report)
        _require(
            summary.get("classification")
            == report.get("classification", {}).get("classification")
            and summary.get("threadId") == report.get("thread", {}).get("id")
            and summary.get("sentinelPid")
            == report.get("sentinel", {}).get("process", {}).get("pid")
            and summary.get("sentinelInstanceId")
            == report.get("sentinel", {})
            .get("baselineCall", {})
            .get("instanceId"),
            "Multi-connection formal report summary drifted",
        )


def _validate_documentation(record: dict[str, Any], *, root: Path) -> None:
    _require(
        record.get("documentation") == DOCUMENTATION_PATH
        and (root / DOCUMENTATION_PATH).is_file(),
        "Admission documentation binding drifted",
    )
    text = (root / DOCUMENTATION_PATH).read_text(encoding="utf-8")
    for phrase in (
        CONCLUSION,
        PROTOCOL_SHA256,
        PROBE_SHA256,
        CALIBRATION_SHA256,
        MULTI_EVIDENCE_SHA256,
        "`thread-created-auto-attach`",
        "direct connection-B tool call",
        "not admitted for",
        "second independently releasable subscription was **not** observed",
        "That candidate sequence is not live authorization.",
        "remain unchanged",
    ):
        _require(
            phrase in text,
            f"Admission documentation boundary missing: {phrase}",
        )


def validate_admission(
    record: dict[str, Any],
    *,
    root: Path = ROOT,
) -> None:
    _require(
        set(record) == EXPECTED_TOP_LEVEL_KEYS,
        "Admission record top-level surface drifted",
    )
    _require(
        record.get("schema") == 1
        and record.get("id")
        == (
            "mcp-thread-creator-close-observer-acquisition-path-admission-"
            "2026-07-27"
        )
        and record.get("date") == "2026-07-27"
        and record.get("status") == CONCLUSION,
        "Admission identity or status drifted",
    )
    _validate_sources(record, root=root)

    observation = record.get("machineVerifiedObservation")
    _require(
        observation
        == {
            "formalRunCount": 3,
            "acquisitionPath": "thread-created-auto-attach",
            "singleAppServerPerRun": True,
            "twoDistinctBridgeProcessesPerRun": True,
            "sameThreadPerRun": True,
            "sameExactSentinelPerRun": True,
            "connectionBDirectToolCallPerRun": True,
            "modelTurnRequestCount": 0,
            "turnStartedNotificationCount": 0,
            "secondIndependentlyReleasableSubscriptionObserved": False,
        },
        "Machine-verified observation was promoted or drifted",
    )
    conflict = record.get("currentConflict")
    _require(
        isinstance(conflict, dict)
        and conflict.get("protocolSetupRequiresThreadResume") is True
        and conflict.get("currentProbeCallsThreadResume") is True
        and conflict.get("zeroTurnResumePathValidatedByFormalReports")
        is False
        and conflict.get("invalidCalibrationPairedWindowEntered") is False
        and conflict.get("invalidCalibrationFormalLivePairedRunCount") == 0,
        "Current resume-path conflict was erased or promoted",
    )
    amendment = record.get("requiredOfflineAmendment")
    _require(
        isinstance(amendment, dict)
        and amendment.get("disposition")
        == "amend-new-revision-do-not-rewrite-bound-history"
        and amendment.get("protocolRevisionRequired") is True
        and amendment.get("probeRevisionRequired") is True
        and amendment.get("oldProtocolMutationAuthorized") is False
        and amendment.get("oldProbeMutationAuthorized") is False
        and amendment.get("candidateSequenceIsLiveAuthorization") is False
        and any(
            "without thread/resume" in str(item)
            for item in amendment.get("candidateSequence", [])
        ),
        "Offline amendment or history-preservation boundary drifted",
    )
    decision = record.get("admissionDecision")
    _require(
        isinstance(decision, dict)
        and decision.get("conclusion") == CONCLUSION
        and decision.get("currentProtocolProbePairAdmittedForLiveExecution")
        is False
        and decision.get("autoAttachAcquisitionPathAdmittedAsSecondSubscription")
        is False
        and decision.get("liveRerunAuthorized") is False,
        "Admission decision was promoted beyond evidence",
    )
    execution = record.get("executionBoundary")
    _require(
        isinstance(execution, dict)
        and execution.get("readOnlySourceAndReportValidationAuthorized")
        is True
        and execution.get("offlineArtifactCreationAuthorized") is True
        and all(
            execution.get(key) is False
            for key in (
                "appServerStartAuthorized",
                "loopbackTransportExecutionAuthorized",
                "modelTurnAuthorized",
                "externalNetworkUseAuthorized",
                "configurationMutationAuthorized",
                "installationAuthorized",
                "liveProtocolExecutionAuthorized",
            )
        ),
        "Admission execution boundary was expanded",
    )
    claims = record.get("claimBoundary")
    _require(
        isinstance(claims, dict)
        and set(claims) == EXPECTED_CLAIM_KEYS
        and all(value is False for value in claims.values()),
        "Admission subscription/owner/lease/release/resource claim promoted",
    )
    _validate_documentation(record, root=root)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--record", type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = args.root.resolve()
    record_path = (
        args.record.resolve()
        if args.record is not None
        else (root / RECORD_PATH).resolve()
    )
    validate_admission(load_json_object(record_path), root=root)
    print("MCP observer acquisition-path admission validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
