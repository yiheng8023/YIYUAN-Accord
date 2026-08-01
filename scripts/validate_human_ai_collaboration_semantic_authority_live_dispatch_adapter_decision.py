#!/usr/bin/env python3
"""Validate the governed SEM-03 live-dispatch adapter decision."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
DECISION_PATH = (
    ROOT
    / "registry"
    / "human-ai-collaboration-semantic-authority-live-dispatch-adapter-decision-2026-08-01.json"
)
EXPECTED_ID = (
    "human-ai-collaboration-semantic-authority-live-dispatch-adapter-decision-"
    "2026-08-01"
)
EXPECTED_CLAIMS = {
    "loaderInvocationProved",
    "skillInstructionsReachedModelProved",
    "behavioralCausationProved",
    "semanticContinuityProved",
    "treatmentValueProved",
    "crossHostValueProved",
    "candidatePreferenceJustified",
    "selfAuthoredCapabilityNeeded",
}


def canonical_sha256(value: Any) -> str:
    encoded = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def validate_decision(document: dict[str, Any]) -> list[str]:
    failures: list[str] = []
    body = dict(document)
    digest = body.pop("decisionSha256", None)
    if digest != canonical_sha256(body):
        failures.append("hard-fail-live-adapter-decision-digest")
    if (
        document.get("schema") != 1
        or document.get("id") != EXPECTED_ID
        or document.get("status") != "reviewed-no-dispatch"
        or document.get("scenarioId") != "HAC-SEMANTIC-AUTHORITY-01"
    ):
        failures.append("fail-live-adapter-decision-identity")

    source = document.get("sourceSnapshot", {})
    runtime_report = source.get("runtimeAdapterReport", {})
    official = source.get("officialCodexManual", {})
    if (
        source.get("repositoryHeadReviewed")
        != "88d23974bf4c652b790f439cd7e2bd396b630a79"
        or source.get("codexCliVersion") != "0.146.0"
        or runtime_report
        != {
            "path": (
                "audits/human-ai-collaboration-semantic-authority-runtime-"
                "adapter-preflight-2026-08-01/REPORT.json"
            ),
            "fileSha256": (
                "849a014057a8d8696da1a9afcfe77c0eea80e1b3541ab8791a82272e58578798"
            ),
            "reportSha256": (
                "284122bab9c24d31308bd75868d7369f7cd47fc4eb49ad17af18f058add3386f"
            ),
        }
        or official.get("sourceLocator")
        != "https://learn.chatgpt.com/docs/app-server.md"
        or official.get("retrievedManualBytes") != 1837849
        or official.get("retrievedManualSha256")
        != "f03e415eedbdfc2682e0e4b9d5e5b0b045d3b3a9568f5c01204f22df619c2cb4"
        or official.get("fullSnapshotVendored") is not False
    ):
        failures.append("hard-fail-live-adapter-source-snapshot")

    decision = document.get("decision", {})
    if (
        decision.get("outcome")
        != "separate-thin-live-adapter-justified-not-implemented"
        or "add-send-flag-to-dry-adapter"
        not in {
            row.get("route")
            for row in decision.get("rejectedAlternatives", [])
            if isinstance(row, dict)
        }
        or "directly-use-shared-weak-agent-runner"
        not in {
            row.get("route")
            for row in decision.get("rejectedAlternatives", [])
            if isinstance(row, dict)
        }
    ):
        failures.append("hard-fail-live-adapter-separation-decision")

    facts = document.get("observedFacts", {})
    if (
        facts.get("dryAdapterPhaseTemplatesTransmitted") is not False
        or facts.get("dryAdapterInventoryRequestsTransmitted") != 12
        or facts.get("sharedWeakAgentRunnerAcceptsSemanticTreatmentIds") is not False
        or facts.get("sharedWeakAgentRunnerProvidesIndependentLoaderEvent") is not False
        or facts.get("officialTurnInterruptAvailable") is not True
        or facts.get("officialModelReroutedNotificationAvailable") is not True
        or facts.get("officialThreadTokenUsageNotificationAvailable") is not True
        or facts.get("officialLastSubscriberUnloadGracePeriodSeconds") != 1800
        or facts.get("officialThreadUnsubscribeGuaranteesImmediateUnload") is not False
    ):
        failures.append("hard-fail-live-adapter-source-facts")

    contract = document.get("requiredLiveAdapterContract", {})
    if (
        contract.get("separateFromDryAdapter") is not True
        or contract.get("denyByDefault") is not True
        or contract.get("authorityReceiptRequiredBeforeSessionStart") is not True
        or contract.get("oneAppServerProcessPerPhase") is not True
        or contract.get("oneEphemeralThreadPerPhase") is not True
        or contract.get("phaseCountPerRun") != 4
        or contract.get("maximumModelRequestsPerRun") != 4
        or contract.get("requestedRoute")
        != {
            "model": "gpt-5.3-codex-spark",
            "reasoningEffort": "low",
            "allowProviderModelFallback": False,
        }
        or contract.get("claimCeilingWithoutIndependentLoaderEvent")
        != "bounded-treatment-association-only"
    ):
        failures.append("hard-fail-live-adapter-contract")
    required_observations = set(contract.get("requiredParentObservations", []))
    if not {
        "thread-start-model-and-reasoning",
        "model-rerouted-events",
        "thread-token-usage-updates",
        "turn-terminal-status",
        "app-server-exact-process-exit",
        "temporary-root-removal",
    }.issubset(required_observations):
        failures.append("hard-fail-live-adapter-observer-boundary")
    hard_stops = set(contract.get("hardStops", []))
    if not {
        "authority-receipt-missing-or-drifted",
        "model-request-budget-exhausted",
        "model-rerouted-or-provider-fallback-observed",
        "write-outside-public-root-observed",
        "process-exit-or-temporary-cleanup-unproved",
    }.issubset(hard_stops):
        failures.append("hard-fail-live-adapter-stop-boundary")
    if contract.get("stopSequence") != [
        "stop-before-next-phase-on-any-hard-fail",
        "turn-interrupt-on-active-turn-timeout-or-route-violation",
        "abort-app-server-if-interrupt-or-completion-does-not-finish-boundedly",
        "do-not-score-the-run",
        "retain-only-governed-redacted-evidence",
    ]:
        failures.append("hard-fail-live-adapter-stop-sequence")
    if contract.get("humanDecisionInjection") != {
        "performedByParent": True,
        "beforePhase": "SEM-PHASE-2-MODEL",
        "absentBeforePhase1Required": True,
    }:
        failures.append("hard-fail-live-adapter-human-authority")

    implementation = document.get("implementationState", {})
    if implementation != {
        "liveAdapterImplemented": False,
        "offlineAuthorityGateImplemented": True,
        "offlineAuthorityGateBuilder": (
            "scripts/build_human_ai_collaboration_semantic_authority_"
            "live_dispatch_gate.py"
        ),
        "offlineAuthorityGateReport": (
            "audits/human-ai-collaboration-semantic-authority-live-dispatch-"
            "gate-preflight-2026-08-01/REPORT.json"
        ),
        "simulatedTransportTestsPass": True,
        "liveHostDispatchTested": False,
        "dispatchReadinessProved": False,
    }:
        failures.append("hard-fail-live-adapter-implementation-promotion")
    authority = document.get("authorityBoundary", {})
    if (
        authority.get("repositoryDecisionRecordWritesAuthorized") is not True
        or authority.get("validatorAndTestWritesAuthorized") is not True
        or any(
            authority.get(key) is not False
            for key in (
                "modelDispatchAuthorized",
                "candidateInstructionExecutionAuthorized",
                "globalConfigMutationAuthorized",
                "ccSwitchMutationAuthorized",
                "selfAuthoredSkillOrHookAuthorized",
                "liveAuthorityReceiptCreationAuthorized",
            )
        )
    ):
        failures.append("hard-fail-live-adapter-authority-boundary")
    claims = document.get("claimBoundary", {})
    if set(claims) != EXPECTED_CLAIMS or any(
        value is not False for value in claims.values()
    ):
        failures.append("hard-fail-live-adapter-claim-promotion")
    return list(dict.fromkeys(failures))


def main() -> int:
    decision = json.loads(DECISION_PATH.read_text(encoding="utf-8"))
    failures = validate_decision(decision)
    if failures:
        for failure in failures:
            print(failure)
        return 1
    print("Semantic-authority live-dispatch adapter decision validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
