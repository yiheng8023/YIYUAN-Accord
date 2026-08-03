#!/usr/bin/env python3
"""Assess whether a durable smoke can be rescored as a process trace."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
SMOKE_EVIDENCE_PATH = (
    "registry/human-ai-collaboration-process-fidelity-v2-source-backed-"
    "smoke-evidence-2026-07-27.json"
)
ASSESSMENT_EVIDENCE_PATH = (
    "registry/human-ai-collaboration-process-fidelity-raw-event-trace-"
    "eligibility-assessment-2026-07-27.json"
)
DOC_PATH = (
    "docs/strategy/HUMAN-AI-COLLABORATION-PROCESS-FIDELITY-RAW-EVENT-"
    "TRACE-ELIGIBILITY-ASSESSMENT-2026-07-27.md"
)


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def _load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    _require(isinstance(value, dict), f"Expected JSON object: {path}")
    return value


def _file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _windows_crlf_projection_sha256(path: Path) -> str:
    data = path.read_bytes()
    _require(
        b"\r\n" not in data,
        f"Repository evidence is not LF-normalized: {path}",
    )
    return hashlib.sha256(data.replace(b"\n", b"\r\n")).hexdigest()


def assess_smoke(
    smoke: dict[str, Any],
    raw: dict[str, Any],
    packet: dict[str, Any],
) -> dict[str, Any]:
    durable = smoke["durableRunEvidence"]
    source_read = raw.get("sourceBackedReadEvidence", {})
    calls = source_read.get("calls", [])
    source_read_observable = (
        len(calls) == 1
        and calls[0].get("success") is True
        and calls[0].get("observedCanonicalSha256")
        == raw.get("inputBinding", {}).get(
            "publicInformationBundleCanonicalSha256"
        )
    )
    response_observable = (
        isinstance(raw.get("turnEvidence", {}).get("agentResponseSha256"), str)
        and raw.get("submission", {}).get("status")
        == "parsed-single-raw-json-object"
    )
    terminal_oracle_observable = (
        raw.get("oracleEvaluation", {}).get("absoluteTaskPass") is True
        and raw.get("oracleEvaluation", {}).get("failureCodes") == []
    )
    process_trace = raw.get("processTrace")
    process_hop_ledger_present = (
        isinstance(process_trace, dict)
        and isinstance(process_trace.get("edgeLedgers"), list)
        and bool(process_trace["edgeLedgers"])
    )

    edge_observations = [
        {
            "edgeId": "public-bundle-to-scoped-read-result",
            "material": True,
            "status": (
                "observable-linked"
                if source_read_observable
                else "missing-or-drifted"
            ),
            "inputArtifactSha256": durable[
                "publicSourceBundleFileSha256"
            ].lower(),
            "outputArtifactSha256": (
                calls[0].get("observedFileSha256")
                if len(calls) == 1
                else None
            ),
            "semanticDeltaLedgerPresent": False,
        },
        {
            "edgeId": "scoped-read-result-to-agent-structured-response",
            "material": True,
            "status": "opaque-hidden-transform-no-persisted-intermediate-state",
            "inputArtifactSha256": (
                calls[0].get("observedFileSha256")
                if len(calls) == 1
                else None
            ),
            "outputArtifactSha256": raw.get("turnEvidence", {}).get(
                "agentResponseSha256"
            ),
            "inputEqualsPredecessorOutput": None,
            "semanticDeltaLedgerPresent": False,
        },
        {
            "edgeId": "agent-structured-response-to-terminal-oracle",
            "material": True,
            "status": (
                "terminal-observable-no-intermediate-process-ledger"
                if response_observable and terminal_oracle_observable
                else "missing-or-drifted"
            ),
            "inputArtifactSha256": raw.get("turnEvidence", {}).get(
                "agentResponseSha256"
            ),
            "terminalOraclePass": terminal_oracle_observable,
            "semanticDeltaLedgerPresent": False,
        },
    ]
    opaque_edges = [
        item["edgeId"]
        for item in edge_observations
        if str(item["status"]).startswith("opaque-")
    ]
    missing_fields = [
        "processTrace.edgeLedgers",
        "perEdge.invariantStates",
        "perEdge.omittedInvariantIds",
        "perEdge.addedAssumptionIds",
        "perEdge.provenanceBreakIds",
        "perEdge.authorityDeltaIds",
        "perEdge.detectedLossIds",
        "perEdge.recoveryFromAnchorId",
    ]
    eligible = (
        process_hop_ledger_present
        and not opaque_edges
        and all(
            item["semanticDeltaLedgerPresent"]
            for item in edge_observations
        )
    )
    return {
        "sourceSmokeEvidenceId": smoke["id"],
        "atDispatchProtocolFileSha256": durable[
            "atDispatchProtocolFileSha256"
        ],
        "fixtureFileSha256": durable["sourceFixtureFileSha256"],
        "threadId": durable["threadId"],
        "turnId": durable["turnId"],
        "observableTerminalTaskEvidence": {
            "scopedReadObservable": source_read_observable,
            "structuredResponseObservable": response_observable,
            "terminalOracleObservable": terminal_oracle_observable,
        },
        "edgeObservations": edge_observations,
        "opaqueMaterialEdgeIds": opaque_edges,
        "processHopLedgerPresent": process_hop_ledger_present,
        "missingRequiredProcessTraceFields": missing_fields,
        "manualSupplementationUsed": False,
        "eligibleForProcessTraceRepetition": eligible,
        "formalProcessCohortStartingValidRepetitionCount": 0,
        "classification": (
            "transport-pilot-only-process-trace-ineligible"
            if not eligible
            else "process-trace-eligible"
        ),
    }
def validate_evidence(
    document: dict[str, Any],
    *,
    root: Path = ROOT,
) -> None:
    _require(
        document.get("schema") == 1
        and document.get("id")
        == (
            "human-ai-collaboration-process-fidelity-raw-event-trace-"
            "eligibility-assessment-2026-07-27"
        )
        and document.get("date") == "2026-07-27"
        and document.get("status")
        == "existing-smoke-transport-pilot-process-trace-ineligible",
        "Raw-event trace eligibility identity drifted",
    )
    assessor = document.get("assessor")
    _require(
        isinstance(assessor, dict)
        and assessor.get("path")
        == "scripts/assess_process_fidelity_raw_event_trace_eligibility.py"
        and (root / assessor["path"]).is_file()
        and _file_sha256(root / assessor["path"]).lower()
        == str(assessor.get("fileSha256")).lower(),
        "Raw-event trace assessor binding drifted",
    )
    smoke_path = document.get("sourceSmokeEvidencePath")
    _require(
        smoke_path == SMOKE_EVIDENCE_PATH and (root / smoke_path).is_file(),
        "Raw-event trace source smoke binding drifted",
    )
    smoke = _load(root / smoke_path)
    durable = smoke["durableRunEvidence"]
    raw_path = root / durable["rawReportPath"]
    packet_path = root / durable["trialPacketPath"]
    _require(
        _file_sha256(raw_path).lower()
        == durable["rawReportRepositoryFileSha256"].lower()
        and _file_sha256(packet_path).lower()
        == durable["trialPacketRepositoryFileSha256"].lower(),
        "Raw-event trace durable repository input hash drifted",
    )
    _require(
        _windows_crlf_projection_sha256(raw_path).lower()
        == durable["rawReportFileSha256"].lower()
        and _windows_crlf_projection_sha256(packet_path).lower()
        == durable["trialPacketFileSha256"].lower(),
        "Raw-event trace durable capture input hash drifted",
    )
    observed = assess_smoke(
        smoke,
        _load(raw_path),
        _load(packet_path),
    )
    _require(
        observed == document.get("assessment"),
        "Raw-event trace eligibility assessment drifted",
    )
    _require(
        observed["eligibleForProcessTraceRepetition"] is False
        and observed["processHopLedgerPresent"] is False
        and observed["opaqueMaterialEdgeIds"]
        == ["scoped-read-result-to-agent-structured-response"]
        and observed["manualSupplementationUsed"] is False
        and observed["formalProcessCohortStartingValidRepetitionCount"] == 0,
        "Raw-event trace eligibility boundary was promoted",
    )
    decision = document.get("decision")
    _require(
        isinstance(decision, dict)
        and decision.get("existingSmokeDisposition")
        == "retain-as-absolute-task-valid-transport-pilot"
        and decision.get("existingSmokeCountsAsProcessTrace") is False
        and decision.get("formalProcessCohortMustStartFromZero") is True
        and decision.get("additionalLiveDispatchAuthorized") is False
        and decision.get("evidenceStopRemainsActive") is True,
        "Raw-event trace eligibility decision drifted",
    )
    _require(
        document.get("documentation") == DOC_PATH
        and (root / DOC_PATH).is_file()
        and isinstance(document.get("claimLimit"), str)
        and bool(document["claimLimit"]),
        "Raw-event trace documentation binding drifted",
    )
    normalized = " ".join(
        (root / DOC_PATH).read_text(encoding="utf-8").split()
    )
    for phrase in (
        "transport pilot only",
        "process-hop ledger is absent",
        "opaque material edge",
        "No manual supplementation",
        "starts from zero",
        "evidence stop remains active",
    ):
        _require(
            phrase in normalized,
            f"Raw-event trace documentation boundary missing: {phrase}",
        )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--validate-evidence", action="store_true")
    args = parser.parse_args()
    root = args.root.resolve()
    if args.validate_evidence:
        validate_evidence(_load(root / ASSESSMENT_EVIDENCE_PATH), root=root)
        print("Raw-event trace eligibility evidence validation passed.")
        return 0
    smoke = _load(root / SMOKE_EVIDENCE_PATH)
    durable = smoke["durableRunEvidence"]
    assessment = assess_smoke(
        smoke,
        _load(root / durable["rawReportPath"]),
        _load(root / durable["trialPacketPath"]),
    )
    print(json.dumps(assessment, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
