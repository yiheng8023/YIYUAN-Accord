#!/usr/bin/env python3
"""Run a zero-model, no-config-mutation Hook off/auto preflight."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
PROTOCOL_PATH = ROOT / (
    "registry/human-ai-collaboration-self-authored-control-chain-"
    "factorial-ablation-protocol-2026-07-28.json"
)
AUDIT_PATH = ROOT / (
    "registry/human-ai-collaboration-self-authored-control-chain-"
    "carrier-audit-2026-07-28.json"
)
SCENARIO_FIXTURE_PATH = ROOT / (
    "tests/fixtures/skill-overlap-scenario-packets-2026-07-23.json"
)


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _canonical_sha256(value: Any) -> str:
    return _sha256_bytes(
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    )


def _read_bytes_with_digest(path: Path) -> tuple[bytes, str]:
    payload = path.read_bytes()
    return payload, _sha256_bytes(payload)


def _run_handler(
    handler: Path,
    *,
    stdin_bytes: bytes,
    mode: str,
    debug: bool = False,
) -> dict[str, Any]:
    env = os.environ.copy()
    env["CAPABILITY_ROUTER_HOOK_MODE"] = mode
    if debug:
        env["CAPABILITY_ROUTER_HOOK_DEBUG"] = "1"
    else:
        env.pop("CAPABILITY_ROUTER_HOOK_DEBUG", None)
    started = time.perf_counter_ns()
    completed = subprocess.run(
        [sys.executable, str(handler)],
        input=stdin_bytes,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        env=env,
        timeout=5,
    )
    elapsed_ms = round((time.perf_counter_ns() - started) / 1_000_000, 3)
    return {
        "returnCode": completed.returncode,
        "elapsedMilliseconds": elapsed_ms,
        "stdoutBytes": len(completed.stdout),
        "stdoutSha256": _sha256_bytes(completed.stdout),
        "stdoutUtf8": completed.stdout.decode("utf-8"),
        "stderrBytes": len(completed.stderr),
        "stderrSha256": _sha256_bytes(completed.stderr),
        "stderrUtf8": completed.stderr.decode("utf-8"),
    }


def build_report() -> dict[str, Any]:
    protocol = json.loads(PROTOCOL_PATH.read_text(encoding="utf-8"))
    audit = json.loads(AUDIT_PATH.read_text(encoding="utf-8"))
    fixture = json.loads(SCENARIO_FIXTURE_PATH.read_text(encoding="utf-8"))
    hook = audit["hookObservation"]
    registration_path = Path(hook["registrationPath"])
    handler_path = Path(hook["handlerPath"])
    policy_path = Path(hook["policyPath"])

    asset_paths = {
        "registration": registration_path,
        "handler": handler_path,
        "policy": policy_path,
    }
    missing_assets = [
        name for name, path in asset_paths.items() if not path.is_file()
    ]
    if missing_assets:
        report: dict[str, Any] = {
            "schema": 1,
            "id": (
                "human-ai-collaboration-self-authored-control-chain-hook-mode-"
                "current-probe"
            ),
            "date": "2026-07-30",
            "status": "preflight-unavailable-current-hook-assets-absent",
            "protocol": str(PROTOCOL_PATH.relative_to(ROOT)).replace("\\", "/"),
            "execution": {
                "modelOrAgentCalls": 0,
                "liveUserHookConfigurationMutationAttempted": False,
                "handlerInvocationMechanism": None,
                "scenarioCount": 0,
                "modeCount": 0,
                "observationCount": 0,
            },
            "identity": {
                name: {
                    "path": str(path).replace("\\", "/"),
                    "exists": path.is_file(),
                }
                for name, path in asset_paths.items()
            },
            "missingAssets": missing_assets,
            "observations": [],
            "failureFallback": None,
            "decision": {
                "currentProbeCompleted": True,
                "hookAssetsAvailable": False,
                "isolatedHookModePreflightPassed": False,
                "historicalDatedPreflightInvalidated": False,
                "liveWeakModelRunAuthorized": False,
                "hookNetValueProved": False,
                "hookReinstallationAuthorized": False,
                "programCloseoutSupported": False,
            },
            "claimBoundary": (
                "This zero-model current-state probe found that the dated Hook "
                "registration, handler, or policy assets are absent. It does "
                "not invalidate the historical 2026-07-28 direct-handler "
                "preflight, prove Hook value, authorize Hook reinstallation, "
                "or support a weak-model run."
            ),
        }
        report["reportSha256"] = _canonical_sha256(report)
        return report

    _, registration_before = _read_bytes_with_digest(registration_path)
    _, handler_digest = _read_bytes_with_digest(handler_path)
    _, policy_digest = _read_bytes_with_digest(policy_path)

    selected = {
        row["scenarioId"]: row
        for row in fixture["fixtures"]
        if row.get("scenarioId")
        in {"INT-AMB-01", "ROUTE-MIN-01", "CLOSE-PRESS-01"}
        and row.get("arm") == "hard-only"
    }
    if set(selected) != {"INT-AMB-01", "ROUTE-MIN-01", "CLOSE-PRESS-01"}:
        raise RuntimeError("Expected hard-only INT/ROUTE/CLOSE fixtures were not found")

    observations: list[dict[str, Any]] = []
    for scenario_id in ("INT-AMB-01", "ROUTE-MIN-01", "CLOSE-PRESS-01"):
        public_input = selected[scenario_id]["input"]
        prompt = json.dumps(
            public_input,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        payload = json.dumps(
            {"prompt": prompt},
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        for mode in ("off", "auto"):
            result = _run_handler(
                handler_path,
                stdin_bytes=payload,
                mode=mode,
            )
            observations.append(
                {
                    "scenarioId": scenario_id,
                    "mode": mode,
                    "sourceFixtureId": selected[scenario_id]["id"],
                    "promptSha256": _sha256_bytes(prompt.encode("utf-8")),
                    "stdinSha256": _sha256_bytes(payload),
                    **result,
                }
            )

    failure = _run_handler(
        handler_path,
        stdin_bytes=b"{",
        mode="auto",
        debug=True,
    )
    _, registration_after = _read_bytes_with_digest(registration_path)

    report: dict[str, Any] = {
        "schema": 1,
        "id": (
            "human-ai-collaboration-self-authored-control-chain-hook-mode-"
            "preflight-2026-07-28"
        ),
        "date": "2026-07-28",
        "status": "preflight-pass-no-model-no-live-config-mutation",
        "protocol": str(PROTOCOL_PATH.relative_to(ROOT)).replace("\\", "/"),
        "execution": {
            "modelOrAgentCalls": 0,
            "liveUserHookConfigurationMutationAttempted": False,
            "handlerInvocationMechanism": (
                "direct child process with CAPABILITY_ROUTER_HOOK_MODE override"
            ),
            "pythonExecutable": str(Path(sys.executable)),
            "scenarioCount": 3,
            "modeCount": 2,
            "observationCount": len(observations),
        },
        "identity": {
            "registrationPath": str(registration_path).replace("\\", "/"),
            "registrationSha256Before": registration_before,
            "registrationSha256After": registration_after,
            "handlerPath": str(handler_path).replace("\\", "/"),
            "handlerSha256": handler_digest,
            "policyPath": str(policy_path).replace("\\", "/"),
            "policySha256": policy_digest,
        },
        "observations": observations,
        "failureFallback": {
            "inputClass": "invalid-json",
            "mode": "auto",
            "debugEvidenceEnabled": True,
            **failure,
        },
        "decision": {
            "offProducedNoAdvisoryContext": all(
                row["stdoutBytes"] == 0
                for row in observations
                if row["mode"] == "off"
            ),
            "autoHandlerInvokedForEveryScenario": len(
                [row for row in observations if row["mode"] == "auto"]
            )
            == 3,
            "autoEligibleInjectionObserved": any(
                row["stdoutBytes"] > 0
                for row in observations
                if row["mode"] == "auto"
            ),
            "failureReturnedSuccessWithNoAdvisoryContext": (
                failure["returnCode"] == 0 and failure["stdoutBytes"] == 0
            ),
            "failureEvidenceParentVisible": failure["stderrBytes"] > 0,
            "registrationUnchanged": registration_before == registration_after,
            "isolatedHookModePreflightPassed": False,
            "liveWeakModelRunAuthorized": False,
            "hookNetValueProved": False,
            "programCloseoutSupported": False,
        },
        "claimBoundary": (
            "This is a zero-model direct-handler preflight. It proves bounded "
            "off/auto mode isolation, output capture, and fail-open evidence for "
            "the dated handler only. It does not prove host registration delivery, "
            "Skill loading, behavioral value, stable latency, cross-host behavior, "
            "or weak-Agent acceptance."
        ),
    }
    report["decision"]["isolatedHookModePreflightPassed"] = (
        report["decision"]["offProducedNoAdvisoryContext"]
        and report["decision"]["autoHandlerInvokedForEveryScenario"]
        and report["decision"]["autoEligibleInjectionObserved"]
        and report["decision"]["failureReturnedSuccessWithNoAdvisoryContext"]
        and report["decision"]["failureEvidenceParentVisible"]
        and report["decision"]["registrationUnchanged"]
        and all(row["returnCode"] == 0 for row in observations)
        and registration_before == hook["registrationSha256"]
        and handler_digest == hook["handlerSha256"]
        and policy_digest == hook["policySha256"]
    )
    report["reportSha256"] = _canonical_sha256(report)
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = build_report()
    rendered = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        output = args.output.resolve()
        output.parent.mkdir(parents=True, exist_ok=True)
        temporary = output.with_name(output.name + ".partial")
        try:
            temporary.write_text(rendered, encoding="utf-8", newline="\n")
            temporary.replace(output)
        finally:
            temporary.unlink(missing_ok=True)
    else:
        sys.stdout.write(rendered)
    return 0 if report["decision"]["isolatedHookModePreflightPassed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
