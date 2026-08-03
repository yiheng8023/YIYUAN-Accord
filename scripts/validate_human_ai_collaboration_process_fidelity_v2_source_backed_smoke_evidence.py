#!/usr/bin/env python3
"""Validate the bounded v2 source-backed live smoke evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
EVIDENCE_PATH = (
    "registry/human-ai-collaboration-process-fidelity-v2-source-backed-"
    "smoke-evidence-2026-07-27.json"
)
DOC_PATH = (
    "docs/strategy/HUMAN-AI-COLLABORATION-PROCESS-FIDELITY-V2-"
    "SOURCE-BACKED-SMOKE-EVIDENCE-2026-07-27.md"
)


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def _file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _windows_crlf_projection_sha256(path: Path) -> str:
    data = path.read_bytes()
    _require(b"\r\n" not in data, f"Repository evidence is not LF-normalized: {path}")
    return hashlib.sha256(data.replace(b"\n", b"\r\n")).hexdigest()


def _canonical_sha256(value: Any) -> str:
    payload = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def validate_evidence(document: dict[str, Any], *, root: Path = ROOT) -> None:
    expected_identity = {
        "schema": 1,
        "id": (
            "human-ai-collaboration-process-fidelity-v2-source-backed-"
            "smoke-evidence-2026-07-27"
        ),
        "date": "2026-07-27",
        "status": (
            "bounded-source-backed-smoke-pass-one-absolute-task-valid-"
            "transport-repetition"
        ),
        "scenarioId": "GEN-RESEARCH-01",
    }
    for key, value in expected_identity.items():
        _require(document.get(key) == value, f"Smoke evidence {key} drifted")

    identity = document.get("identityLedger")
    _require(
        isinstance(identity, dict)
        and identity.get("fixtureId")
        == "fixture.synthetic-conflicting-claims-v2"
        and identity.get("submissionArmId") == "GEN-NATIVE-SPARK"
        and identity.get("informationArmId")
        == "source-backed-fresh-session-recovery"
        and identity.get("identitiesSubstituted") is False,
        "Smoke evidence identity ledger drifted",
    )

    execution = document.get("execution")
    _require(
        isinstance(execution, dict)
        and execution.get("dispatchCount") == 1
        and execution.get("validRepetitionCount") == 1
        and execution.get("requiredValidRepetitionsForCompletedArm") == 3
        and execution.get("completedArmCount") == 0
        and execution.get("model") == "gpt-5.3-codex-spark"
        and execution.get("reasoningEffort") == "low"
        and execution.get("providerFallbackAllowed") is False
        and execution.get("sandboxType") == "readOnly"
        and execution.get("networkAccess") is False
        and execution.get("approvalPolicy") == "never",
        "Smoke evidence execution boundary drifted",
    )

    durable = document.get("durableRunEvidence")
    _require(
        isinstance(durable, dict)
        and durable.get("temporaryEvidenceRequiredForIndependentReverification")
        is False,
        "Smoke evidence durable run boundary drifted",
    )
    _require(
        durable.get("repositoryFileIdentity")
        == {
            "algorithm": "sha256",
            "gitAttributes": "*.json text eol=lf",
            "captureTransform": "repository-lf-to-observed-windows-crlf",
            "meaning": (
                "Repository hashes bind the governed LF Git representation; "
                "existing FileSha256 fields preserve the original Windows CRLF "
                "capture identity."
            ),
        },
        "Smoke evidence repository file identity boundary drifted",
    )
    durable_paths = {
        "rawReportPath": (
            "rawReportFileSha256",
            "rawReportRepositoryFileSha256",
        ),
        "trialPacketPath": (
            "trialPacketFileSha256",
            "trialPacketRepositoryFileSha256",
        ),
        "buildManifestPath": (
            "buildManifestFileSha256",
            "buildManifestRepositoryFileSha256",
        ),
        "publicSourceBundlePath": (
            "publicSourceBundleFileSha256",
            "publicSourceBundleRepositoryFileSha256",
        ),
    }
    loaded: dict[str, dict[str, Any]] = {}
    for path_key, (capture_hash_key, repository_hash_key) in durable_paths.items():
        relative = durable.get(path_key)
        capture_hash = durable.get(capture_hash_key)
        repository_hash = durable.get(repository_hash_key)
        _require(
            isinstance(relative, str)
            and relative.startswith("audits/")
            and isinstance(capture_hash, str)
            and bool(capture_hash)
            and isinstance(repository_hash, str)
            and bool(repository_hash),
            f"Smoke evidence durable path binding drifted: {path_key}",
        )
        path = root / relative
        _require(path.is_file(), f"Smoke evidence durable file missing: {relative}")
        _require(
            _file_sha256(path).lower() == repository_hash.lower(),
            f"Smoke evidence durable file hash drifted: {relative}",
        )
        _require(
            _windows_crlf_projection_sha256(path).lower() == capture_hash.lower(),
            f"Smoke evidence capture file hash drifted: {relative}",
        )
        loaded[path_key] = json.loads(path.read_text(encoding="utf-8"))

    raw = loaded["rawReportPath"]
    packet = loaded["trialPacketPath"]
    manifest = loaded["buildManifestPath"]
    raw_without_hash = {
        key: value for key, value in raw.items() if key != "reportSha256"
    }
    response_text = raw.get("turnEvidence", {}).get("agentResponseText")
    _require(
        raw.get("reportSha256")
        == durable.get("rawReportCanonicalSha256")
        and _canonical_sha256(raw_without_hash)
        == durable.get("rawReportCanonicalSha256")
        and raw.get("thread", {}).get("threadId") == durable.get("threadId")
        and raw.get("thread", {}).get("turnId") == durable.get("turnId")
        and isinstance(response_text, str)
        and hashlib.sha256(response_text.encode("utf-8")).hexdigest().lower()
        == str(durable.get("agentResponseSha256")).lower()
        and raw.get("submission", {}).get("value") == json.loads(response_text),
        "Smoke evidence durable raw report identity drifted",
    )
    _require(
        packet.get("protocolBinding", {}).get("path")
        == document.get("protocolPath")
        and str(packet.get("protocolBinding", {}).get("sha256")).lower()
        == str(durable.get("atDispatchProtocolFileSha256")).lower()
        and str(packet.get("sourceFixtureBinding", {}).get("sha256")).lower()
        == str(durable.get("sourceFixtureFileSha256")).lower(),
        "Smoke evidence at-dispatch protocol or fixture identity drifted",
    )
    manifest_files = {
        item.get("name"): str(item.get("sha256")).lower()
        for item in manifest.get("files", [])
        if isinstance(item, dict)
    }
    _require(
        manifest.get("dispatchCount") == 0
        and manifest.get("agentRunStartedAtBuildTime") is False
        and manifest_files.get("PUBLIC-SOURCE-BUNDLE.json")
        == str(durable.get("publicSourceBundleFileSha256")).lower()
        and manifest_files.get("TRIAL-PACKET.json")
        == str(durable.get("trialPacketFileSha256")).lower(),
        "Smoke evidence durable build manifest drifted",
    )

    read = document.get("inputAndReadBoundary")
    _require(
        isinstance(read, dict)
        and read.get("agentVisibleFileNames")
        == ["PUBLIC-SOURCE-BUNDLE.json"]
        and read.get("parentEvidenceRootIsRuntimeWorkspaceRoot") is False
        and read.get("preDispatchPublicCarrierOracleIsolationProved") is True
        and read.get("privateOracleExposureObserved") is False
        and read.get("privateOracleLeakageScanComplete") is False
        and read.get("dynamicToolName") == "read_public_information_bundle"
        and read.get("expectedDynamicToolCallCount") == 1
        and read.get("observedDynamicToolCallCount") == 1
        and read.get("locator") == "PUBLIC-SOURCE-BUNDLE.json"
        and read.get("generalFilesystemAuthorityGranted") is False
        and read.get("runtimeReadBoundaryProved") is True
        and read.get("observedCanonicalSha256")
        == read.get("publicInformationBundleCanonicalSha256"),
        "Smoke evidence scoped-read boundary drifted",
    )

    task = document.get("taskAndHostEvidence")
    _require(
        isinstance(task, dict)
        and task.get("absoluteTaskPass") is True
        and task.get("oracleFailureCodes") == []
        and task.get("classificationStatus")
        == "fixture-pass-native-read-only-boundary"
        and task.get("commandExecutionObserved") is False
        and task.get("fileChangeObserved") is False
        and task.get("treeChangedPaths") == []
        and task.get("globalConfigStable") is True
        and task.get("mcpToolCallObserved") is False
        and task.get("webSearchObserved") is False,
        "Smoke evidence task or host boundary drifted",
    )

    claims = document.get("claimBoundary")
    _require(
        isinstance(claims, dict)
        and claims
        and all(value is False for value in claims.values()),
        "Smoke evidence claim boundary was promoted",
    )
    decision = document.get("decision")
    _require(
        isinstance(decision, dict)
        and decision.get("countsAsBoundSyntheticFixtureOutcome") is True
        and decision.get(
            "countsAsOneAbsoluteTaskValidSourceBackedTransportRepetition"
        )
        is True
        and decision.get("countsAsProcessTraceValidRepetition") is False
        and decision.get("processHopLedgerPresent") is False
        and decision.get("cascadeMeasurementPresent") is False
        and decision.get("countsAsCompletedInformationArm") is False
        and decision.get("countsAsProcessFidelityComparison") is False
        and decision.get("widerCohortStarted") is False
        and decision.get("evidenceStopRequired") is True,
        "Smoke evidence decision drifted",
    )
    _require(
        document.get("documentation") == DOC_PATH
        and (root / DOC_PATH).is_file()
        and isinstance(document.get("claimLimit"), str)
        and bool(document["claimLimit"]),
        "Smoke evidence documentation or claim limit drifted",
    )
    normalized = " ".join(
        (root / DOC_PATH).read_text(encoding="utf-8").split()
    )
    for phrase in (
        "one absolute-task-valid transport repetition",
        "Durable run record",
        "not a process-trace-valid repetition",
        "no completed arm or topology comparison",
        "called `read_public_information_bundle` exactly once",
        "no general filesystem authority",
        "full private-oracle leakage absence is still not universally proved",
        "evidence stop",
    ):
        _require(phrase in normalized, f"Smoke evidence doc missing: {phrase}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args()
    root = args.root.resolve()
    document = json.loads((root / EVIDENCE_PATH).read_text(encoding="utf-8"))
    validate_evidence(document, root=root)
    print("Process-fidelity v2 source-backed smoke evidence validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
