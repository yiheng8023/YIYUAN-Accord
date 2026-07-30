#!/usr/bin/env python3
"""Validate the zero-model self-authored control-chain Hook-mode preflight."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
REPORT_PATH = Path(
    "audits/human-ai-collaboration-self-authored-control-chain-"
    "hook-mode-preflight-2026-07-28/REPORT.json"
)
PROTOCOL_PATH = Path(
    "registry/human-ai-collaboration-self-authored-control-chain-"
    "factorial-ablation-protocol-2026-07-28.json"
)
AUDIT_PATH = Path(
    "registry/human-ai-collaboration-self-authored-control-chain-"
    "carrier-audit-2026-07-28.json"
)


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


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


def validate_evidence(document: dict, *, root: Path = ROOT) -> None:
    _require(
        document.get("schema") == 1
        and document.get("id")
        == (
            "human-ai-collaboration-self-authored-control-chain-hook-mode-"
            "preflight-2026-07-28"
        )
        and document.get("status")
        == "preflight-pass-no-model-no-live-config-mutation"
        and document.get("protocol") == str(PROTOCOL_PATH).replace("\\", "/"),
        "Hook-mode preflight identity drifted",
    )
    body = dict(document)
    reported_digest = body.pop("reportSha256", None)
    _require(
        reported_digest == _canonical_sha256(body),
        "Hook-mode preflight report digest drifted",
    )

    protocol = json.loads((root / PROTOCOL_PATH).read_text(encoding="utf-8"))
    audit = json.loads((root / AUDIT_PATH).read_text(encoding="utf-8"))
    _require(
        protocol.get("preflightEvidence") == str(REPORT_PATH).replace("\\", "/"),
        "Hook-mode preflight protocol binding drifted",
    )

    execution = document.get("execution", {})
    _require(
        execution.get("modelOrAgentCalls") == 0
        and execution.get("liveUserHookConfigurationMutationAttempted") is False
        and execution.get("handlerInvocationMechanism")
        == "direct child process with CAPABILITY_ROUTER_HOOK_MODE override"
        and execution.get("scenarioCount") == 3
        and execution.get("modeCount") == 2
        and execution.get("observationCount") == 6,
        "Hook-mode preflight execution boundary drifted",
    )

    hook = audit["hookObservation"]
    identity = document.get("identity", {})
    _require(
        identity.get("registrationPath") == hook["registrationPath"]
        and identity.get("registrationSha256Before")
        == hook["registrationSha256"]
        and identity.get("registrationSha256After")
        == hook["registrationSha256"]
        and identity.get("handlerPath") == hook["handlerPath"]
        and identity.get("handlerSha256") == hook["handlerSha256"]
        and identity.get("policyPath") == hook["policyPath"]
        and identity.get("policySha256") == hook["policySha256"],
        "Hook-mode preflight identity pins drifted",
    )

    expected_pairs = {
        (scenario, mode)
        for scenario in ("INT-AMB-01", "ROUTE-MIN-01", "CLOSE-PRESS-01")
        for mode in ("off", "auto")
    }
    observations = document.get("observations", [])
    indexed = {
        (row.get("scenarioId"), row.get("mode")): row
        for row in observations
        if isinstance(row, dict)
    }
    _require(
        len(indexed) == len(observations) == 6
        and set(indexed) == expected_pairs,
        "Hook-mode preflight observation coverage drifted",
    )
    empty_digest = _sha256_bytes(b"")
    injected_scenarios: set[str] = set()
    for scenario in ("INT-AMB-01", "ROUTE-MIN-01", "CLOSE-PRESS-01"):
        off = indexed[(scenario, "off")]
        auto = indexed[(scenario, "auto")]
        _require(
            off.get("promptSha256") == auto.get("promptSha256")
            and off.get("stdinSha256") == auto.get("stdinSha256"),
            f"Hook-mode paired input drifted: {scenario}",
        )
        for row in (off, auto):
            stdout = str(row.get("stdoutUtf8", "")).encode("utf-8")
            stderr = str(row.get("stderrUtf8", "")).encode("utf-8")
            _require(
                row.get("returnCode") == 0
                and isinstance(row.get("elapsedMilliseconds"), (int, float))
                and row["elapsedMilliseconds"] >= 0
                and row.get("stdoutBytes") == len(stdout)
                and row.get("stdoutSha256") == _sha256_bytes(stdout)
                and row.get("stderrBytes") == len(stderr)
                and row.get("stderrSha256") == _sha256_bytes(stderr),
                f"Hook-mode observation bytes drifted: {scenario}/{row.get('mode')}",
            )
        _require(
            off.get("stdoutBytes") == 0
            and off.get("stdoutSha256") == empty_digest
            and off.get("stderrBytes") == 0,
            f"Hook off isolation drifted: {scenario}",
        )
        if auto.get("stdoutBytes", 0) > 0:
            payload = json.loads(auto["stdoutUtf8"])
            output = payload.get("hookSpecificOutput", {})
            _require(
                output.get("hookEventName") == "UserPromptSubmit"
                and isinstance(output.get("additionalContext"), str)
                and bool(output["additionalContext"]),
                f"Hook auto advisory output drifted: {scenario}",
            )
            injected_scenarios.add(scenario)
        else:
            _require(
                auto.get("stdoutSha256") == empty_digest,
                f"Hook auto empty output digest drifted: {scenario}",
            )
    _require(
        injected_scenarios == {"INT-AMB-01", "ROUTE-MIN-01"},
        "Hook auto eligibility observation drifted",
    )

    fallback = document.get("failureFallback", {})
    fallback_stdout = str(fallback.get("stdoutUtf8", "")).encode("utf-8")
    fallback_stderr = str(fallback.get("stderrUtf8", "")).encode("utf-8")
    _require(
        fallback.get("inputClass") == "invalid-json"
        and fallback.get("mode") == "auto"
        and fallback.get("debugEvidenceEnabled") is True
        and fallback.get("returnCode") == 0
        and fallback.get("stdoutBytes") == len(fallback_stdout) == 0
        and fallback.get("stdoutSha256") == _sha256_bytes(fallback_stdout)
        and fallback.get("stderrBytes") == len(fallback_stderr) > 0
        and fallback.get("stderrSha256") == _sha256_bytes(fallback_stderr)
        and fallback_stderr.startswith(b"capability-router hook:"),
        "Hook failure-fallback evidence drifted",
    )

    decision = document.get("decision", {})
    for key in (
        "offProducedNoAdvisoryContext",
        "autoHandlerInvokedForEveryScenario",
        "autoEligibleInjectionObserved",
        "failureReturnedSuccessWithNoAdvisoryContext",
        "failureEvidenceParentVisible",
        "registrationUnchanged",
        "isolatedHookModePreflightPassed",
    ):
        _require(decision.get(key) is True, f"Hook preflight decision rolled back: {key}")
    for key in (
        "liveWeakModelRunAuthorized",
        "hookNetValueProved",
        "programCloseoutSupported",
    ):
        _require(decision.get(key) is False, f"Hook preflight decision overclaimed: {key}")

    gate = protocol.get("executionAdmission", {})
    _require(
        gate.get("isolatedHookModeHarnessImplemented") is True
        and gate.get("zeroModelFailureFallbackProbePassed") is True
        and gate.get("hookModePreflightEvidenceValidated") is True
        and gate.get("factorialEvidenceAdapterImplemented") is True
        and gate.get("dependencyCompleteProjectionImplemented") is True
        and gate.get("projectionBuilderFaultTestsPass") is True
        and gate.get("taskScopedFourCellExposureProved") is True
        and gate.get("liveWeakModelRunAuthorizedByThisRecord") is False
        and gate.get("admittedForLiveExecution") is False,
        "Hook preflight protocol gate overclaimed",
    )


def main() -> int:
    document = json.loads((ROOT / REPORT_PATH).read_text(encoding="utf-8"))
    validate_evidence(document, root=ROOT)
    print("Self-authored control-chain Hook-mode preflight evidence verified.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
