#!/usr/bin/env python3
"""Validate the first bounded weak-Agent live comparison evidence."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
EVIDENCE_PATH = (
    "registry/"
    "human-ai-collaboration-weak-agent-live-comparison-batch-01-2026-07-24.json"
)
PROTOCOL_PATH = (
    "registry/"
    "human-ai-collaboration-comparative-protocol-batch-01-2026-07-24.json"
)
DOCUMENTATION_PATH = (
    "docs/"
    "human-ai-collaboration-weak-agent-live-comparison-batch-01-2026-07-24.md"
)


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def validate_live_comparison(
    document: dict[str, Any],
    *,
    root: Path = ROOT,
) -> None:
    _require(document.get("schema") == 1, "Live comparison schema must be 1")
    _require(
        document.get("status")
        == "three-paired-observations-complete-mixed-process-outcome",
        "Live comparison status was promoted or drifted",
    )
    _require(
        document.get("protocol") == PROTOCOL_PATH,
        "Live comparison protocol binding drifted",
    )
    _require(
        document.get("scenarioId") == "SE-IMPLEMENT-REVIEW-01"
        and document.get("fixtureId") == "fixture.python-retry-policy-v1",
        "Live comparison scenario or fixture drifted",
    )

    host = document.get("host", {})
    _require(
        host.get("runtimeVersion") == "0.145.0"
        and host.get("model") == "gpt-5.3-codex-spark"
        and host.get("reasoningEffort") == "low"
        and host.get("providerFallbackAllowed") is False
        and host.get("approvalPolicy") == "never"
        and host.get("sandboxType") == "workspaceWrite"
        and host.get("networkAccess") is False,
        "Live comparison control plane drifted",
    )

    harness = document.get("harness", {})
    _require(
        harness.get("runner")
        == "scripts/run_human_ai_collaboration_weak_agent_trial.py"
        and harness.get("builder")
        == "scripts/build_human_ai_collaboration_weak_agent_trial.py",
        "Live comparison harness binding drifted",
    )
    _require(
        harness.get("allowedMutableFiles")
        == ["retry_policy.py", "test_retry_policy.py"],
        "Live comparison mutable-file allowlist drifted",
    )
    _require(
        harness.get("rawReportsRepositoryOwned") is False
        and harness.get("rawReportRetention")
        == "local-temporary-cleanup-debt",
        "Live comparison raw-report boundary drifted",
    )
    for key in (
        "runnerSha256AtFirstTwoPairs",
        "runnerSha256AtThirdPair",
        "builderSha256",
        "protocolSha256AtRun",
        "hiddenOracleSha256",
    ):
        value = harness.get(key)
        _require(
            isinstance(value, str) and len(value) == 64,
            f"Live comparison digest is missing: {key}",
        )

    runs = {
        item.get("id"): item
        for item in document.get("runs", [])
        if isinstance(item, dict)
    }
    _require(
        set(runs)
        == {
            "SE-NATIVE-SPARK-R1-FORMAL",
            "SE-MATT-DISCIPLINED-CODING-R1-FORMAL",
            "SE-NATIVE-SPARK-R2-FORMAL",
            "SE-MATT-DISCIPLINED-CODING-R2-FORMAL",
            "SE-NATIVE-SPARK-R3-FORMAL",
            "SE-MATT-DISCIPLINED-CODING-R3-FORMAL",
        },
        "Live comparison formal run set drifted",
    )
    for run_id, run in runs.items():
        expected_status = (
            "fixture-fail-or-host-evidence-incomplete"
            if run_id == "SE-MATT-DISCIPLINED-CODING-R3-FORMAL"
            else "fixture-pass-loader-causation-unproved"
        )
        _require(
            run.get("status") == expected_status,
            f"Live comparison run status drifted: {run_id}",
        )
        outcome = run.get("outcome")
        if outcome is None:
            outcome = {
                "visibleTestsPassed": run.get("visibleTestsPassed"),
                "hiddenTestsPassed": run.get("hiddenTestsPassed"),
                "globalConfigStable": run.get("globalConfigStable"),
            }
        _require(
            outcome.get("visibleTestsPassed") is True
            and outcome.get("hiddenTestsPassed") is True
            and outcome.get("globalConfigStable") is True,
            f"Live comparison run boundary failed: {run_id}",
        )
        if "exposure" in run:
            _require(
                run["exposure"].get("controlUserSkillCount") == 105
                and run["exposure"].get("sameIdentitySet") is True
                and run["exposure"].get("loaderInvocationProved") is False,
                f"Live comparison exposure boundary drifted: {run_id}",
            )
        else:
            _require(
                run.get("taskScopedExposureProved") is True
                and run.get("loaderInvocationProved") is False
                and run.get("changedFilesExact") is True,
                f"Live comparison compact run boundary drifted: {run_id}",
            )
        for key in (
            "rawReportFileSha256",
            "internalReportSha256",
            "responseSha256",
        ):
            value = run.get(key)
            _require(
                isinstance(value, str) and len(value) == 64,
                f"Live comparison run digest is missing: {run_id}/{key}",
            )

    native = runs["SE-NATIVE-SPARK-R1-FORMAL"]
    native_exposure = native["exposure"]
    _require(
        native_exposure.get("effectiveEnabledUserSkillCount") == 0
        and native_exposure.get("allUserSkillsDisabled") is True
        and native_exposure.get("selectedSkill") is None
        and native_exposure.get("promptExplicitlyNamedSelectedSkill") is False,
        "Native formal exposure drifted",
    )
    _require(
        native.get("process", {}).get("commandCount") == 1
        and native["process"].get("failedCommandCount") == 0
        and native["process"].get("testCommandObserved") is False,
        "Native formal process evidence drifted",
    )

    matt = runs["SE-MATT-DISCIPLINED-CODING-R1-FORMAL"]
    matt_exposure = matt["exposure"]
    selected = matt_exposure.get("selectedSkill", {})
    _require(
        matt_exposure.get("effectiveEnabledUserSkillCount") == 1
        and matt_exposure.get("onlySelectedUserSkillEnabled") is True
        and matt_exposure.get("allOtherUserSkillsDisabled") is True
        and matt_exposure.get("promptExplicitlyNamedSelectedSkill") is True
        and selected.get("name") == "disciplined-coding"
        and selected.get("contentSha256")
        == "d36f49ed0d252b9c9c656bc9c0f72d43710c68591ce234e8dc2886dc4785fc7b",
        "Matt formal exposure drifted",
    )
    _require(
        matt.get("process", {}).get("commandCount") == 4
        and matt["process"].get("failedCommandCount") == 0
        and matt["process"].get("testCommandObserved") is True,
        "Matt formal process evidence drifted",
    )
    native_r3 = runs["SE-NATIVE-SPARK-R3-FORMAL"]
    matt_r3 = runs["SE-MATT-DISCIPLINED-CODING-R3-FORMAL"]
    _require(
        native_r3.get("testCommandObserved") is True
        and native_r3.get("failedCommandCount") == 0
        and native_r3.get("transientOutOfScopeWritePaths") == [],
        "Native third-run process evidence drifted",
    )
    _require(
        matt_r3.get("testCommandObserved") is True
        and matt_r3.get("failedCommandCount") == 5
        and matt_r3.get("transientOutOfScopeWritePaths") == [".tmp.patch"],
        "Matt third-run process evidence drifted",
    )

    observation = document.get("pairedObservation", {})
    _require(
        observation.get("completedPairCount") == 3
        and observation.get("bothFixtureOutcomesPassed") is True
        and observation.get("decision")
        == "no-superiority-or-retention-decision-expand-attribution-before-architecture-change",
        "Live comparison paired decision was promoted or drifted",
    )
    _require(
        observation.get("strictProcessPassCounts")
        == {"native": 3, "matt": 2},
        "Live comparison strict process aggregate drifted",
    )
    _require(
        len(document.get("excludedPilots", [])) == 6,
        "Live comparison excluded-pilot ledger drifted",
    )

    claims = document.get("claimBoundary", {})
    _require(
        claims.get("provesBoundFixtureOutcomeForRecordedRuns") is True
        and claims.get("provesRequestedWeakModelRoute") is True
        and claims.get("provesTaskScopedSkillMetadataExposure") is True,
        "Live comparison supported claim boundary drifted",
    )
    for key in (
        "provesSkillLoaderInvocation",
        "provesSkillInstructionsReachedModel",
        "provesSkillCausation",
        "provesMattSuperiority",
        "provesNativeSuperiority",
        "provesGeneralCodingQuality",
        "provesProductionReadiness",
        "provesCrossHostValue",
    ):
        _require(claims.get(key) is False, f"Live comparison overclaimed: {key}")

    next_gate = document.get("nextGate", {})
    _require(
        next_gate.get("strongModelEscalationAllowed") is False
        and next_gate.get("superpowersArmBlocked") is True,
        "Live comparison next gate drifted",
    )

    documentation = root / DOCUMENTATION_PATH
    _require(documentation.is_file(), "Live comparison documentation is missing")
    text = " ".join(documentation.read_text(encoding="utf-8").split())
    for phrase in (
        "three paired observations complete; mixed process outcome",
        "does not prove that the Skill loader invoked the Skill",
        "three-run-per-arm threshold is met",
        "clean final directory is not proof",
    ):
        _require(
            phrase in text,
            f"Live comparison documentation boundary is missing: {phrase}",
        )


def main() -> int:
    document = json.loads((ROOT / EVIDENCE_PATH).read_text(encoding="utf-8"))
    validate_live_comparison(document)
    print("Weak-Agent live comparison validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
