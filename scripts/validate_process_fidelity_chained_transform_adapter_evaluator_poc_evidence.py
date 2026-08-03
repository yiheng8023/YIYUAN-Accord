#!/usr/bin/env python3
"""Validate zero-dispatch chained-transform adapter/evaluator evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

try:
    from .build_process_fidelity_chained_transform_adapter_evaluator_poc import (
        build_poc,
    )
    from .run_process_fidelity_chained_transform_trial import (
        canonical_sha256,
    )
    from .repository_text_identity import (
        repository_text_sha256,
        windows_crlf_projection_sha256,
    )
except ImportError:  # pragma: no cover - direct script execution
    from build_process_fidelity_chained_transform_adapter_evaluator_poc import (
        build_poc,
    )
    from run_process_fidelity_chained_transform_trial import (
        canonical_sha256,
    )
    from repository_text_identity import (
        repository_text_sha256,
        windows_crlf_projection_sha256,
    )


ROOT = Path(__file__).resolve().parent.parent
EVIDENCE_PATH = (
    "registry/human-ai-collaboration-process-fidelity-chained-transform-"
    "adapter-evaluator-poc-evidence-2026-07-27.json"
)
DOC_PATH = (
    "docs/strategy/HUMAN-AI-COLLABORATION-PROCESS-FIDELITY-CHAINED-"
    "TRANSFORM-ADAPTER-EVALUATOR-POC-EVIDENCE-2026-07-27.md"
)


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def _file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _validate_manifest(root: Path, manifest_path: Path) -> dict[str, Any]:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    body = dict(manifest)
    digest = body.pop("manifestSha256", None)
    _require(
        digest == canonical_sha256(body),
        "Adapter/evaluator audit manifest digest drifted",
    )
    audit_root = manifest_path.parent
    indexed = {
        item["path"]: item for item in manifest.get("files", [])
    }
    actual = {
        path.relative_to(audit_root).as_posix()
        for path in audit_root.rglob("*")
        if path.is_file() and path.name != "MANIFEST.json"
    }
    _require(
        set(indexed) == actual,
        "Adapter/evaluator audit file inventory drifted",
    )
    for relative, item in indexed.items():
        path = audit_root / relative
        data = path.read_bytes() if path.is_file() else b""
        exact_capture_match = (
            len(data) == item.get("bytes")
            and hashlib.sha256(data).hexdigest().lower()
            == str(item.get("sha256", "")).lower()
        )
        crlf_projection = data.replace(b"\n", b"\r\n")
        normalized_repository_match = (
            path.suffix.lower() in {".json", ".md"}
            and b"\r\n" not in data
            and len(crlf_projection) == item.get("bytes")
            and hashlib.sha256(crlf_projection).hexdigest().lower()
            == str(item.get("sha256", "")).lower()
        )
        _require(
            path.is_file() and (exact_capture_match or normalized_repository_match),
            f"Adapter/evaluator audit file hash drifted: {relative}",
        )
    _require(
        manifest.get("agentDispatchCount") == 0
        and manifest.get("modelCallCount") == 0
        and manifest.get("actualRouteObserved") is False
        and manifest.get("formalProcessCohortCount") == 0
        and manifest.get("cleanupDisposition")
        == "retain-authoritative-mechanism-evidence",
        "Adapter/evaluator audit manifest boundary drifted",
    )
    return manifest


def validate_evidence(
    document: dict[str, Any],
    *,
    root: Path = ROOT,
) -> None:
    _require(
        document.get("schema") == 1
        and document.get("id")
        == (
            "human-ai-collaboration-process-fidelity-chained-transform-"
            "adapter-evaluator-poc-evidence-2026-07-27"
        )
        and document.get("date") == "2026-07-27"
        and document.get("status")
        == (
            "zero-agent-zero-dispatch-sequential-artifact-adapter-and-"
            "trace-evaluator-poc-passed-live-not-tested"
        ),
        "Adapter/evaluator PoC evidence identity drifted",
    )
    bindings = document.get("bindings")
    _require(
        isinstance(bindings, dict) and len(bindings) == 7,
        "Adapter/evaluator PoC binding set drifted",
    )
    for key, binding in bindings.items():
        path = root / binding["path"]
        _require(
            path.is_file()
            and binding.get("fileSha256", "").lower()
            == _file_sha256(path).lower(),
            f"Adapter/evaluator PoC binding drifted: {key}",
        )
    audit = document.get("auditEvidence")
    _require(
        isinstance(audit, dict)
        and audit.get("repositoryFileIdentity")
        == {
            "algorithm": "sha256",
            "gitAttributes": "*.json and *.md text eol=lf",
            "captureTransform": "repository-lf-to-observed-windows-crlf",
        }
        and not str(audit.get("root", "")).startswith(".tmp")
        and (root / audit["root"]).is_dir()
        and audit.get("repositoryLocalNonTemporaryDestinationBound") is True
        and audit.get("gitOrRemoteDurabilityProved") is False
        and audit.get("cleanupDisposition")
        == "retain-authoritative-mechanism-evidence",
        "Adapter/evaluator audit evidence boundary drifted",
    )
    manifest_path = root / audit["manifestPath"]
    report_path = root / audit["reportPath"]
    _require(
        manifest_path.is_file()
        and report_path.is_file()
        and audit.get("manifestRepositoryFileSha256", "").lower()
        == repository_text_sha256(manifest_path).lower()
        and audit.get("reportRepositoryFileSha256", "").lower()
        == repository_text_sha256(report_path).lower(),
        "Adapter/evaluator audit evidence hash drifted",
    )
    _require(
        audit.get("manifestFileSha256", "").lower()
        == windows_crlf_projection_sha256(manifest_path).lower()
        and audit.get("reportFileSha256", "").lower()
        == windows_crlf_projection_sha256(report_path).lower(),
        "Adapter/evaluator audit evidence capture hash drifted",
    )
    _validate_manifest(root, manifest_path)
    report = json.loads(report_path.read_text(encoding="utf-8"))
    body = dict(report)
    report_digest = body.pop("reportSha256", None)
    _require(
        report_digest == canonical_sha256(body),
        "Adapter/evaluator PoC report digest drifted",
    )
    results = document.get("results")
    _require(
        isinstance(results, dict)
        and results.get("validCaseCount")
        == results.get("validCaseOutcomeMatchCount")
        == len(report.get("validCaseResults", []))
        == 2
        and results.get("registeredFaultCaseCount")
        == results.get("registeredFaultClassificationMatchCount")
        == len(report.get("faultCaseResults", []))
        == 6
        and all(item.get("matched") is True for item in report["validCaseResults"])
        and all(
            item.get("matched") is True
            and item.get("candidateTraceProduced") is False
            for item in report["faultCaseResults"]
        )
        and results.get("conditionalRecoverySourceExposureProved") is True
        and results.get("controlSourcePayloadStayedSealed") is True
        and results.get("invalidDetectionStoppedBeforeHop3") is True
        and results.get("callerSuppliedMetricsIgnored") is True
        and results.get("absoluteAndProcessLedgersSeparated") is True,
        "Adapter/evaluator PoC result drifted",
    )
    execution = document.get("execution")
    _require(
        isinstance(execution, dict)
        and execution.get("agentDispatchCount") == 0
        and execution.get("modelCallCount") == 0
        and execution.get("actualRouteObserved") is False
        and execution.get("liveDispatchAuthorized") is False
        and execution.get("externalAccessUsed") is False
        and execution.get("hostConfigurationChanged") is False
        and execution.get("globalSkillStateChanged") is False,
        "Adapter/evaluator PoC execution boundary drifted",
    )
    decision = document.get("decision")
    _require(
        isinstance(decision, dict)
        and decision.get("sequentialArtifactAdapterMechanismPassed") is True
        and decision.get(
            "parentRecomputedTraceEvaluatorMechanismPassed"
        )
        is True
        and decision.get("faultClassifierPassed") is True
        and decision.get("nonTemporaryRawEvidenceDestinationBound") is True
        and decision.get("liveDispatchReady") is False
        and decision.get("formalProcessCohortCount") == 0
        and decision.get("endToEndProcessFidelityAssessment") == "partial",
        "Adapter/evaluator PoC decision boundary drifted",
    )
    _require(
        isinstance(document.get("claimBoundary"), dict)
        and document["claimBoundary"]
        and all(value is False for value in document["claimBoundary"].values()),
        "Adapter/evaluator PoC claim boundary was promoted",
    )
    with TemporaryDirectory() as temporary:
        replay = build_poc(
            root=root,
            output_root=Path(temporary) / "replay",
        )
    replay_report = replay["report"]
    _require(
        all(item["matched"] for item in replay_report["validCaseResults"])
        and all(item["matched"] for item in replay_report["faultCaseResults"])
        and replay_report["execution"]["agentDispatchCount"] == 0
        and replay_report["execution"]["modelCallCount"] == 0
        and replay_report["decision"]["liveDispatchReady"] is False,
        "Adapter/evaluator PoC replay drifted",
    )
    _require(
        document.get("documentation") == DOC_PATH
        and (root / DOC_PATH).is_file()
        and isinstance(document.get("claimLimit"), str),
        "Adapter/evaluator PoC documentation binding drifted",
    )
    normalized = " ".join(
        (root / DOC_PATH).read_text(encoding="utf-8").split()
    )
    for phrase in (
        "zero Agent, zero dispatch",
        "Invalid detection stops before hop 3",
        "formal process cohort count remains zero",
        "does not prove that a live weak Agent",
        "rather than treated as `.tmp` cleanup debt",
    ):
        _require(
            phrase in normalized,
            f"Adapter/evaluator PoC documentation missing: {phrase}",
        )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args()
    root = args.root.resolve()
    document = json.loads(
        (root / EVIDENCE_PATH).read_text(encoding="utf-8")
    )
    validate_evidence(document, root=root)
    print("Process-fidelity adapter/evaluator PoC evidence passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
