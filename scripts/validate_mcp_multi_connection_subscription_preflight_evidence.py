#!/usr/bin/env python3
"""Validate Codex 0.145.0 multi-connection subscription preflight evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
EVIDENCE_PATH = (
    "registry/mcp-app-server-0.145.0-multi-connection-subscription-"
    "preflight-evidence-2026-07-27.json"
)
EXPECTED_CLASSIFICATION = (
    "second-connection-subscription-not-observed-bounded"
)
EXPECTED_STATUS = (
    "observed-three-valid-no-model-turn-preflights-"
    "second-connection-subscription-not-observed"
)
EXPECTED_SOURCE_HASHES = {
    "codex-rs/app-server/src/thread_state.rs": (
        "81E020028F6A47EB1B5E5F3ACC79D02F726B3FCE18A7D45E8BE05795C0D61862"
    ),
    "codex-rs/app-server/src/request_processors/thread_lifecycle.rs": (
        "D60B9AC54DBEE113A530AE7245C2D827A8D6715C5D88D15585CFB479F4F6580D"
    ),
    "codex-rs/app-server/src/request_processors/thread_processor.rs": (
        "3BAE6A6CB8F983F20538CDCC01C4F0BA6CECDAC73E15F980D4ABAA8284DCC731"
    ),
    "codex-rs/app-server/src/lib.rs": (
        "A1D8569DCC4F0B2C9D6C7F617CE47A0980F4620AD1A24E5DA0377DBE47CA853A"
    ),
}


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def _repository_text_sha256(path: Path) -> str:
    data = path.read_bytes()
    _require(
        b"\r" not in data.replace(b"\r\n", b""),
        f"Invalid text EOL: {path}",
    )
    return hashlib.sha256(data.replace(b"\r\n", b"\n")).hexdigest().upper()


def _windows_crlf_projection_sha256(path: Path) -> str:
    data = path.read_bytes()
    _require(b"\r\n" not in data, f"Repository evidence is not LF: {path}")
    return hashlib.sha256(data.replace(b"\n", b"\r\n")).hexdigest().upper()


def _canonical_report_sha256(report: dict[str, Any]) -> str:
    payload = dict(report)
    payload.pop("reportSha256", None)
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest().upper()


def _load_bound_json(
    root: Path,
    item: dict[str, Any],
    label: str,
) -> dict[str, Any]:
    raw_path = item.get("path")
    _require(isinstance(raw_path, str), f"{label} path is invalid")
    path = Path(raw_path)
    if not path.is_absolute():
        path = root / path
    _require(path.is_file(), f"{label} is missing: {path}")
    observed_hash = (
        _windows_crlf_projection_sha256(path)
        if root.resolve() in path.resolve().parents and path.suffix == ".json"
        else _sha256(path)
    )
    _require(
        observed_hash == str(item.get("sha256", "")).upper(),
        f"{label} hash drifted: {path}",
    )
    value = json.loads(path.read_text(encoding="utf-8"))
    _require(isinstance(value, dict), f"{label} is not an object")
    return value


def validate_document(
    root: Path,
    document: dict[str, Any],
) -> dict[str, Any]:
    _require(document.get("schema") == 1, "Evidence schema drifted")
    _require(document.get("status") == EXPECTED_STATUS, "Evidence status drifted")
    host = document.get("hostBinding")
    _require(isinstance(host, dict), "Host binding is missing")
    _require(
        host.get("codexVersion") == "codex-cli 0.145.0"
        and host.get("officialSourceTag") == "rust-v0.145.0"
        and host.get("officialSourceCommit")
        == "25af12f7e61572b0bc18ddb1008be543b91519b0",
        "Host or official source pin drifted",
    )
    for key in ("probeScript", "bridgeScript", "sentinel"):
        binding = host.get(key)
        _require(isinstance(binding, dict), f"{key} binding is missing")
        raw_path = binding.get("path")
        _require(isinstance(raw_path, str), f"{key} path is invalid")
        path = root / raw_path
        observed_hash = (
            _repository_text_sha256(path)
            if key == "bridgeScript" and path.is_file()
            else _sha256(path) if path.is_file() else None
        )
        _require(
            path.is_file()
            and observed_hash == str(binding.get("sha256", "")).upper(),
            f"{key} binding drifted",
        )

    schema_bindings = host.get("stableSchemaEvidence")
    _require(
        isinstance(schema_bindings, list)
        and len(schema_bindings) == 6
        and all(isinstance(item, dict) for item in schema_bindings),
        "Stable schema bindings drifted",
    )
    for index, binding in enumerate(schema_bindings, start=1):
        _load_bound_json(root, binding, f"schema binding {index}")

    source_bindings = host.get("pinnedOfficialSourceEvidence")
    _require(
        isinstance(source_bindings, list)
        and len(source_bindings) == len(EXPECTED_SOURCE_HASHES)
        and all(isinstance(item, dict) for item in source_bindings),
        "Pinned source bindings drifted",
    )
    observed_source_hashes = {
        str(item.get("path")): str(item.get("sha256", "")).upper()
        for item in source_bindings
    }
    _require(
        observed_source_hashes == EXPECTED_SOURCE_HASHES,
        "Pinned official source hash set drifted",
    )
    _require(
        all(
            str(item.get("url", "")).startswith(
                "https://github.com/openai/codex/blob/rust-v0.145.0/"
            )
            and isinstance(item.get("blobSha"), str)
            and len(str(item["blobSha"])) == 40
            and isinstance(item.get("boundedFinding"), str)
            and bool(item["boundedFinding"])
            for item in source_bindings
        ),
        "Pinned official source metadata is incomplete",
    )

    design = document.get("preflightDesign")
    _require(isinstance(design, dict), "Preflight design is missing")
    for key in (
        "singleAppServerPerRun",
        "freshExplicitCodexHomePerRun",
        "twoIndependentBridgeProcessesPerRun",
        "nodeBuiltinWebSocketOnly",
        "noModelTurnRequested",
        "noModelTurnNotificationAllowed",
        "noGlobalConfigurationMutation",
        "noSecondAppServerAsSecondOwner",
        "noFabricatedRolloutOrSubscriberState",
        "cleanupAfterEvidenceBoundaryOnly",
    ):
        _require(design.get(key) is True, f"Preflight design gate drifted: {key}")
    _require(
        design.get("formalAcquisitionPath")
        == "thread-created-auto-attach",
        "Formal acquisition path drifted",
    )

    calibrations = document.get("excludedCalibration")
    _require(
        isinstance(calibrations, list)
        and len(calibrations) == 1
        and isinstance(calibrations[0], dict),
        "Excluded calibration binding drifted",
    )
    calibration = calibrations[0]
    calibration_path = root / str(calibration.get("path"))
    _require(
        calibration_path.is_file()
        and _sha256(calibration_path)
        == str(calibration.get("sha256", "")).upper()
        and calibration.get("acquisitionPath") == "thread-resume"
        and calibration.get("result")
        == "advertised-rollout-path-did-not-materialize",
        "Excluded resume calibration drifted",
    )

    evidence = document.get("formalEvidence")
    _require(
        isinstance(evidence, list)
        and len(evidence) == 3
        and all(isinstance(item, dict) for item in evidence),
        "Formal evidence set drifted",
    )
    thread_ids: set[str] = set()
    instance_ids: set[str] = set()
    report_hashes: set[str] = set()
    for index, binding in enumerate(evidence, start=1):
        report = _load_bound_json(root, binding, f"formal report {index}")
        claimed_self_hash = str(report.get("reportSha256", "")).upper()
        _require(
            claimed_self_hash
            == str(binding.get("reportSha256", "")).upper()
            == _canonical_report_sha256(report),
            f"Formal report {index} canonical hash drifted",
        )
        report_hashes.add(claimed_self_hash)
        classification = report.get("classification")
        _require(
            isinstance(classification, dict)
            and classification.get("valid") is True
            and classification.get("classification")
            == EXPECTED_CLASSIFICATION
            and classification.get("distinctClientConnectionsObserved") is True
            and classification.get("sameLoadedThreadObserved") is True
            and classification.get("sameExactSentinelObservedAcrossConnections")
            is True
            and classification.get("secondConnectionSubscriptionObserved")
            is False
            and classification.get("overlappingSubscriptionObserved") is False
            and classification.get("publicSubscriberCountObserved") is False
            and classification.get("publicLeaseOrReferenceCountApiObserved")
            is False,
            f"Formal report {index} classification drifted",
        )
        thread = report.get("thread")
        unsubscribe = report.get("unsubscribe")
        sentinel = report.get("sentinel")
        host_report = report.get("host")
        isolation = report.get("isolation")
        _require(
            isinstance(thread, dict)
            and thread.get("modelTurnRequests") == 0
            and thread.get("turnStartedNotifications") == 0
            and thread.get("subscriptionAcquisitionPath")
            == "thread-created-auto-attach",
            f"Formal report {index} thread boundary drifted",
        )
        _require(
            isinstance(unsubscribe, dict)
            and unsubscribe.get("ownerAStatuses")
            == ["unsubscribed", "notSubscribed"]
            and unsubscribe.get("ownerBStatuses")
            == ["notSubscribed", "notSubscribed"],
            f"Formal report {index} unsubscribe sequence drifted",
        )
        _require(
            isinstance(host_report, dict)
            and host_report.get("codexVersion") == "codex-cli 0.145.0"
            and host_report.get("singleAppServerProcess") is True
            and host_report.get("appServerAliveBeforeHarnessShutdown") is True
            and host_report.get("applicationLogExternalNetworkAttemptObserved")
            is True,
            f"Formal report {index} host boundary drifted",
        )
        _require(
            isinstance(isolation, dict)
            and isolation.get("authStateProduced") is False
            and isolation.get("pluginsAndAppsDisabled") is True,
            f"Formal report {index} isolation boundary drifted",
        )
        cleanup = sentinel.get("cleanup") if isinstance(sentinel, dict) else None
        baseline = (
            sentinel.get("baselineCall") if isinstance(sentinel, dict) else None
        )
        _require(
            isinstance(cleanup, dict)
            and cleanup.get("cleanupVerified") is True
            and isinstance(baseline, dict),
            f"Formal report {index} cleanup or baseline drifted",
        )
        _require(
            thread.get("id") == binding.get("threadId")
            and baseline.get("pid") == binding.get("sentinelPid")
            and baseline.get("instanceId") == binding.get("sentinelInstanceId"),
            f"Formal report {index} registry identity binding drifted",
        )
        bindings = report.get("bindings")
        _require(isinstance(bindings, dict), f"Formal report {index} bindings missing")
        for report_key, registry_key in (
            ("probeScript", "probeScript"),
            ("bridgeScript", "bridgeScript"),
            ("sentinelScript", "sentinel"),
        ):
            value = bindings.get(report_key)
            registry_value = host.get(registry_key)
            _require(
                isinstance(value, dict)
                and isinstance(registry_value, dict)
                and str(value.get("sha256", "")).upper()
                == str(registry_value.get("sha256", "")).upper(),
                f"Formal report {index} {report_key} binding drifted",
            )
        thread_ids.add(str(thread.get("id")))
        instance_ids.add(str(baseline.get("instanceId")))

    _require(
        len(thread_ids) == 3
        and len(instance_ids) == 3
        and len(report_hashes) == 3,
        "Formal run identities are not independent",
    )
    aggregate = document.get("aggregateObservation")
    _require(isinstance(aggregate, dict), "Aggregate observation is missing")
    expected_counts = {
        "formalRunCount": 3,
        "protocolValidRunCount": 3,
        "distinctWebSocketConnectionPairCount": 3,
        "sameThreadSameExactSentinelCallPairCount": 3,
        "ownerAUnsubscribedThenNotSubscribedCount": 3,
        "ownerBNotSubscribedThenNotSubscribedCount": 3,
        "overlappingSubscriptionObservedCount": 0,
        "modelTurnRequestCount": 0,
        "turnStartedNotificationCount": 0,
        "verifiedCleanupCount": 3,
        "appServerAliveBeforeHarnessShutdownCount": 3,
        "applicationLogExternalNetworkAttemptCount": 3,
    }
    _require(aggregate == expected_counts, "Aggregate observation drifted")

    decision = document.get("decision")
    claims = document.get("claimBoundary")
    program = document.get("programAcceptance")
    _require(
        isinstance(decision, dict)
        and decision.get("multiConnectionWebSocketTransportObserved") is True
        and decision.get(
            "sameLoadedThreadSameExactSentinelCallsAcrossConnectionsObserved"
        )
        is True
        and decision.get("secondIndependentlyReleasableSubscriptionObserved")
        is False
        and decision.get("overlappingOwnerPreconditionSatisfied") is False
        and decision.get("finalObservedOwnerReleaseTrialShouldProceed") is False
        and decision.get("residualSelfAuthoredControllerGapProved") is False,
        "Decision boundary drifted",
    )
    _require(
        isinstance(claims, dict)
        and all(value is False for value in claims.values()),
        "Claim boundary must remain entirely negative",
    )
    _require(
        isinstance(program, dict)
        and program.get("acceptanceId")
        == "acceptance.dynamic-runtime-control-gap-research"
        and program.get("assessment") == "partial"
        and program.get("supportsResidualGapProof") is False,
        "Program acceptance boundary drifted",
    )
    return {
        "status": "validated",
        "formalRuns": len(evidence),
        "classification": EXPECTED_CLASSIFICATION,
        "overlappingSubscriptionObserved": False,
        "finalReleaseTrialShouldProceed": False,
    }


def validate_evidence(root: Path, evidence_path: Path) -> dict[str, Any]:
    document = json.loads(evidence_path.read_text(encoding="utf-8"))
    _require(isinstance(document, dict), "Evidence registry is not an object")
    return validate_document(root, document)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument(
        "--evidence",
        type=Path,
        default=ROOT / EVIDENCE_PATH,
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    summary = validate_evidence(args.root.resolve(), args.evidence.resolve())
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
