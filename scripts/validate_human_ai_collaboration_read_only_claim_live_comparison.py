#!/usr/bin/env python3
"""Validate the bounded native read-only claim live evidence."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

try:
    from .evaluate_human_ai_collaboration_comparative_protocol import (
        evaluate_research_submission,
    )
except ImportError:
    from evaluate_human_ai_collaboration_comparative_protocol import (
        evaluate_research_submission,
    )


ROOT = Path(__file__).resolve().parent.parent
EVIDENCE_PATH = (
    "registry/"
    "human-ai-collaboration-read-only-claim-live-comparison-2026-07-26.json"
)
PROTOCOL_PATH = (
    "registry/"
    "human-ai-collaboration-comparative-protocol-batch-01-2026-07-24.json"
)
FIXTURE_PATH = (
    "tests/fixtures/"
    "human-ai-collaboration-comparative-protocol-batch-01-2026-07-24.json"
)
DOCUMENTATION_PATH = (
    "docs/"
    "human-ai-collaboration-read-only-claim-live-comparison-2026-07-26.md"
)


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def _digest(value: Any) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(character in "0123456789abcdef" for character in value)
    )


def validate_live_comparison(
    document: dict[str, Any],
    *,
    root: Path = ROOT,
    protocol: dict[str, Any] | None = None,
    fixture: dict[str, Any] | None = None,
) -> None:
    _require(document.get("schema") == 1, "Read-only evidence schema must be 1")
    _require(
        document.get("status")
        == "three-native-weak-agent-runs-complete-hard-oracle-failed",
        "Read-only evidence status was promoted or drifted",
    )
    _require(
        document.get("protocol") == PROTOCOL_PATH
        and document.get("scenarioId") == "GEN-RESEARCH-01"
        and document.get("fixtureId")
        == "fixture.synthetic-conflicting-claims-v1",
        "Read-only evidence binding drifted",
    )

    host = document.get("host", {})
    _require(
        host.get("runtimeVersion") == "0.145.0"
        and host.get("model") == "gpt-5.3-codex-spark"
        and host.get("reasoningEffort") == "low"
        and host.get("providerFallbackAllowed") is False
        and host.get("approvalPolicy") == "never"
        and host.get("sandboxType") == "readOnly"
        and host.get("networkAccess") is False
        and host.get("ephemeral") is True,
        "Read-only evidence host boundary drifted",
    )

    harness = document.get("harness", {})
    _require(
        harness.get("runner")
        == "scripts/run_human_ai_collaboration_read_only_claim_trial.py",
        "Read-only evidence runner binding drifted",
    )
    for key in (
        "runnerSha256AtRun",
        "protocolSha256AtRun",
        "fixtureSha256AtRun",
        "publicPacketSha256",
        "privateOracleSha256",
    ):
        _require(
            _digest(harness.get(key)),
            f"Read-only evidence digest is invalid: {key}",
        )
    _require(
        harness.get("privateOracleVersion")
        == "synthetic-conflicting-claims-hidden-oracle-v1"
        and harness.get("publicPacketContentWrittenIntoTrial") is False
        and harness.get("privateOracleContentWrittenIntoTrial") is False
        and harness.get("privateOracleSerializationFoundInPrompt") is False
        and harness.get("privateOracleLeakageScanComplete") is False
        and harness.get("rawReportsRepositoryOwned") is False
        and harness.get("rawReportRetention")
        == "local-temporary-cleanup-debt",
        "Read-only evidence oracle or retention boundary drifted",
    )

    isolation = document.get("capabilityIsolation", {})
    _require(
        isolation.get("configurableSkillCount") == 105
        and isolation.get("enabledConfigurableSkillCount") == 0
        and isolation.get("sameIdentitySet") is True
        and isolation.get("allConfigurableUserAndRepoSkillsDisabled") is True
        and isolation.get("allNonConfigurableStatesPreserved") is True
        and isolation.get("mcpInventoryCompletenessProved") is False,
        "Read-only evidence capability isolation drifted",
    )
    _require(
        isolation.get("pluginFeaturesDisabled")
        == ["plugins", "remote_plugin", "apps", "plugin_sharing"]
        and isolation.get("staticMcpServersDisabled")
        == [
            "codegraph",
            "context7",
            "neo4j-graph",
            "node_repl",
            "playwright",
            "github",
        ],
        "Read-only evidence disabled capability list drifted",
    )

    if protocol is None:
        protocol = json.loads((root / PROTOCOL_PATH).read_text(encoding="utf-8"))
    if fixture is None:
        fixture = json.loads((root / FIXTURE_PATH).read_text(encoding="utf-8"))
    oracle = fixture["researchOracle"]
    runs = {
        run.get("id"): run
        for run in document.get("runs", [])
        if isinstance(run, dict)
    }
    _require(
        set(runs)
        == {
            "GEN-NATIVE-SPARK-R1-FORMAL",
            "GEN-NATIVE-SPARK-R2-FORMAL",
            "GEN-NATIVE-SPARK-R3-FORMAL",
        },
        "Read-only evidence formal run set drifted",
    )
    expected_unsupported = {
        "GEN-NATIVE-SPARK-R1-FORMAL": 1,
        "GEN-NATIVE-SPARK-R2-FORMAL": 3,
        "GEN-NATIVE-SPARK-R3-FORMAL": 3,
    }
    for run_id, run in runs.items():
        _require(
            run.get("status")
            == "fixture-fail-or-host-evidence-incomplete",
            f"Read-only evidence run status drifted: {run_id}",
        )
        for key in (
            "rawReportFileSha256",
            "internalReportSha256",
            "responseSha256",
        ):
            _require(
                _digest(run.get(key)),
                f"Read-only evidence run digest is invalid: {run_id}/{key}",
            )
        submission = run.get("submission")
        _require(
            isinstance(submission, dict),
            f"Read-only evidence submission missing: {run_id}",
        )
        actual = evaluate_research_submission(submission, oracle, protocol)
        _require(
            actual
            == {
                "status": "rejected-offline-contract",
                "failureCodes": [
                    "claim-oracle-mismatch",
                    "unsupported-conclusion",
                ],
            }
            and run.get("oracleEvaluation") == actual,
            f"Read-only evidence oracle result drifted: {run_id}",
        )
        claims = {
            claim["id"]: claim
            for claim in submission.get("claims", [])
            if isinstance(claim, dict) and isinstance(claim.get("id"), str)
        }
        _require(
            claims.get("C3", {}).get("state") == "contradicted"
            and submission.get("unsupportedConclusionCount")
            == expected_unsupported[run_id],
            f"Read-only evidence observed failure changed: {run_id}",
        )
        boundary = run.get("hostBoundary", {})
        _require(
            boundary.get("agentMessageCount") == 1
            and boundary.get("forbiddenItemTypesObserved") == []
            and boundary.get("unknownItemTypesObserved") == []
            and boundary.get("treeChangedPaths") == []
            and boundary.get("globalConfigStable") is True
            and boundary.get("newHostProjectionMarkerObserved") is False
            and boundary.get("commandExecutionObserved") is False
            and boundary.get("fileChangeObserved") is False
            and boundary.get("webSearchObserved") is False
            and boundary.get("mcpToolCallObserved") is False
            and boundary.get("dynamicToolCallObserved") is False,
            f"Read-only evidence host observation drifted: {run_id}",
        )
        stderr = run.get("stderrClassification", {})
        _require(
            stderr.get("mcpStartupFailureCount") == 0
            and stderr.get("skillBudgetWarningCount") == 0
            and stderr.get("rawStderrRecorded") is False
            and stderr.get("lineCount") == stderr.get("errorKeywordLineCount"),
            f"Read-only evidence stderr boundary drifted: {run_id}",
        )

    aggregate = document.get("aggregateObservation", {})
    _require(
        aggregate.get("completedRunCount") == 3
        and aggregate.get("hardOraclePassCount") == 0
        and aggregate.get("c3ContradictedInsteadOfUnknownCount") == 3
        and aggregate.get("unsupportedConclusionCounts") == [1, 3, 3]
        and aggregate.get("hostBoundaryPassCount") == 3
        and aggregate.get("decision")
        == "native-spark-low-fails-bound-oracle-hold-preference-and-self-build",
        "Read-only evidence aggregate decision drifted",
    )

    claims = document.get("claimBoundary", {})
    _require(
        claims.get("provesThreeBoundSyntheticNativeRunsFailedOracle") is True,
        "Read-only evidence bounded result was removed",
    )
    for key, value in claims.items():
        if key == "provesThreeBoundSyntheticNativeRunsFailedOracle":
            continue
        _require(
            value is False,
            f"Read-only evidence claim was overpromoted: {key}",
        )

    _require(
        document.get("documentation") == DOCUMENTATION_PATH
        and (root / DOCUMENTATION_PATH).is_file(),
        "Read-only evidence documentation binding drifted",
    )
    documentation = " ".join(
        (root / DOCUMENTATION_PATH).read_text(encoding="utf-8").split()
    )
    for phrase in (
        "hard oracle failed",
        "did not meet this synthetic source-conflict oracle",
        "does not establish weak-model failure in general",
        "does not yet establish a residual self-authored gap",
        "not proof of complete MCP inventory",
    ):
        _require(
            phrase in documentation,
            f"Read-only evidence documentation boundary missing: {phrase}",
        )


def main() -> int:
    document = json.loads((ROOT / EVIDENCE_PATH).read_text(encoding="utf-8"))
    validate_live_comparison(document)
    print("human-ai collaboration read-only claim live comparison: valid")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
