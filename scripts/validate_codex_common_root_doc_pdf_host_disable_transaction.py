#!/usr/bin/env python3
"""Validate the live Codex common-root doc/pdf host-disable transaction."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
EVIDENCE_PATH = (
    "registry/"
    "codex-common-root-doc-pdf-host-disable-transaction-2026-07-30.json"
)
DOCUMENTATION_PATH = (
    "docs/strategy/"
    "CODEX-COMMON-ROOT-DOC-PDF-HOST-DISABLE-TRANSACTION-2026-07-30.md"
)
TARGETS = [
    "C:/Users/15521/.agents/skills/doc/SKILL.md",
    "C:/Users/15521/.agents/skills/pdf/SKILL.md",
]


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def validate_transaction(
    document: dict[str, Any],
    *,
    root: Path = ROOT,
) -> None:
    _require(
        document.get("schema") == 1
        and document.get("id")
        == "codex-common-root-doc-pdf-host-disable-transaction-2026-07-30"
        and document.get("date") == "2026-07-30"
        and document.get("status")
        == "applied-live-no-model-verified-clean",
        "Codex doc/pdf host-disable transaction identity drifted",
    )
    _require(
        document.get("predecessor")
        == (
            "registry/"
            "codex-common-root-doc-pdf-shadow-disable-exposure-"
            "reconciliation-2026-07-30.json"
        ),
        "Codex doc/pdf host-disable predecessor drifted",
    )
    authority = document.get("authorityBoundary", {})
    _require(
        authority.get("explicitUserAuthorizationObserved") is True
        and authority.get("globalCodexConfigMutation") is True
        and authority.get("codexDesktopRestart") is True
        and authority.get("exactRollbackBackupCleanup") is True
        and authority.get("ccSwitchMutation") is False
        and authority.get("commonRootMutation") is False
        and authority.get("claudeMutation") is False
        and authority.get("traeMutation") is False
        and authority.get("threadOrTurnStartedByProbe") is False
        and authority.get("modelDispatch") is False
        and authority.get("gitCommitOrPush") is False,
        "Codex doc/pdf host-disable authority drifted",
    )
    preflight = document.get("preflight", {})
    _require(
        preflight.get("configSha256")
        == "5ef4129a7ae5c4018f5884879ab22abdd72e833f6d486e52bee2a061ba6e630d"
        and preflight.get("tomlParsePassed") is True
        and preflight.get("existingSkillsConfigEntryCount") == 0,
        "Codex doc/pdf host-disable preflight drifted",
    )
    transaction = document.get("transaction", {})
    _require(
        transaction.get("oldHashPreconditionEnforced") is True
        and transaction.get("rollbackBackupMatchesPreflight") is True
        and transaction.get("postWriteTomlParsePassed") is True
        and transaction.get("targetRowCount") == 2
        and transaction.get("targetRows")
        == [{"path": path, "enabled": False} for path in TARGETS]
        and transaction.get("concurrentConfigDriftDetected") is False,
        "Codex doc/pdf host-disable atomic transaction drifted",
    )
    restart = document.get("restart", {})
    _require(
        restart.get("desktopProcessesStoppedAndRelaunched") is True
        and restart.get("postRestartHostUserAgent")
        == "Codex Desktop/0.146.0 (Windows 10.0.26200; x86_64)"
        and restart.get("intendedRowsRetainedAfterRestart") is True
        and set(restart.get("hostOwnedVolatileConfigDrift", []))
        == {
            "SKY_CUA_NATIVE_PIPE_DIRECTORY",
            "marketplaces.openai-bundled.last_updated",
        },
        "Codex doc/pdf host-disable restart evidence drifted",
    )
    probe = document.get("liveNoModelExposureProbe", {})
    disabled = probe.get("pluginFeaturesDisabledArm", {})
    enabled = probe.get("pluginFeaturesEnabledArm", {})
    _require(
        probe.get("protocol")
        == "Codex app-server skills/list with forceReload=true"
        and probe.get("freshProcess") is True
        and probe.get("threadStarted") is False
        and probe.get("turnStarted") is False
        and probe.get("modelRequestSent") is False
        and probe.get("configPrePostStable") is True
        and disabled.get("skillCount") == 64
        and disabled.get("stderrLineCount") == 0
        and disabled.get("doc", {}).get("enabled") is False
        and disabled.get("pdf", {}).get("enabled") is False
        and enabled.get("skillCount") == 76
        and enabled.get("doc", {}).get("enabled") is False
        and enabled.get("pdf", {}).get("enabled") is False
        and enabled.get("runtimeDocuments", {}).get("enabled") is True
        and enabled.get("runtimePdf", {}).get("enabled") is True,
        "Codex doc/pdf live no-model exposure evidence drifted",
    )
    _require(
        disabled.get("doc", {}).get("resolvedPath")
        == "C:/Users/15521/.cc-switch/skills/doc/SKILL.md"
        and disabled.get("pdf", {}).get("resolvedPath")
        == "C:/Users/15521/.cc-switch/skills/pdf/SKILL.md"
        and enabled.get("runtimeDocuments", {}).get("name")
        == "documents:documents"
        and enabled.get("runtimePdf", {}).get("name") == "pdf:pdf",
        "Codex doc/pdf live carrier identity drifted",
    )
    stderr = enabled.get("stderrClassification", {})
    _require(
        stderr.get("lineCount") == 6
        and stderr.get("errorKeywordLineCount") == 0
        and stderr.get("mcpStartupFailureCount") == 0
        and stderr.get("skillBudgetWarningCount") == 0
        and stderr.get("rawStderrRecorded") is False,
        "Codex doc/pdf live stderr classification drifted",
    )
    carriers = document.get("carrierPreservation", {})
    _require(
        all(
            carriers.get(key) is True
            for key in (
                "ccSwitchDocAndPdfBodiesPresent",
                "agentsDocAndPdfLinksPresent",
                "claudeDocAndPdfLinksPresent",
                "codexPrivateDocAndPdfLinksAbsent",
                "commonRootRetained",
            )
        )
        and carriers.get("sharedEntityDeleted") is False,
        "Codex doc/pdf carrier preservation drifted",
    )
    _require(
        document.get("rollbackDecision", {}).get("triggered") is False,
        "Codex doc/pdf rollback decision drifted",
    )
    cleanup = document.get("cleanup", {})
    _require(
        cleanup
        == {
            "sameDirectoryWriteTempAbsent": True,
            "restartHelperRetained": False,
            "rollbackBackupState": (
                "removed-after-repository-evidence-verification"
            ),
            "exactRollbackBackupAbsent": True,
            "repositoryCleanupInventoryStable": True,
        },
        "Codex doc/pdf cleanup state drifted",
    )
    verification = document.get("verification", {})
    _require(
        verification
        == {
            "eventValidatorTestsPassed": True,
            "topLevelVerifierPassed": True,
        },
        "Codex doc/pdf verification state drifted",
    )
    claims = document.get("claimBoundary", {})
    _require(
        claims.get("liveGlobalDisableApplied") is True
        and claims.get("postRestartTargetExposureStateProved") is True
        and claims.get("runtimeOwnedAlternativesRemainEnabled") is True
        and claims.get("sharedCarrierPreservationProved") is True
        and claims.get("loaderInvocationProved") is False
        and claims.get("behavioralValueProved") is False
        and claims.get("crossHostBehavioralEquivalenceProved") is False
        and claims.get("remainingPortfolioQualityProved") is False
        and claims.get("programCloseoutProved") is False,
        "Codex doc/pdf claim boundary drifted",
    )
    _require(
        document.get("documentation") == DOCUMENTATION_PATH,
        "Codex doc/pdf documentation binding drifted",
    )
    text = (root / DOCUMENTATION_PATH).read_text(encoding="utf-8")
    for phrase in (
        "applied; live no-model exposure verified",
        "shared `doc=false` and `pdf=false`",
        "runtime `documents:documents=true` and `pdf:pdf=true`",
        "No thread, turn, model request",
        "removed by exact path",
        "does not prove Skill invocation",
    ):
        _require(
            phrase in text,
            f"Codex doc/pdf transaction documentation missing: {phrase}",
        )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args()
    root = args.root.resolve()
    document = json.loads((root / EVIDENCE_PATH).read_text(encoding="utf-8"))
    validate_transaction(document, root=root)
    print("Codex common-root doc/pdf host-disable transaction passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
