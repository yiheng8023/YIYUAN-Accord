#!/usr/bin/env python3
"""Validate the Codex common-root doc/pdf exposure reconciliation."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
EVIDENCE_PATH = (
    "registry/"
    "codex-common-root-doc-pdf-shadow-disable-exposure-reconciliation-2026-07-30.json"
)
DOCUMENTATION_PATH = (
    "docs/strategy/"
    "CODEX-COMMON-ROOT-DOC-PDF-SHADOW-DISABLE-EXPOSURE-RECONCILIATION-2026-07-30.md"
)
REMOVED = {
    "-21risk-automation",
    "git-guardrails",
    "git-guardrails-claude-code",
    "scaffold-exercises",
    "sora",
    "write-a-skill",
}


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def validate_reconciliation(
    document: dict[str, Any],
    *,
    root: Path = ROOT,
) -> None:
    _require(
        document.get("schema") == 1
        and document.get("id")
        == "codex-common-root-doc-pdf-shadow-disable-exposure-reconciliation-2026-07-30"
        and document.get("date") == "2026-07-30"
        and document.get("status")
        == "fresh-task-exposure-contradiction-and-isolated-correction-preflight",
        "Codex common-root reconciliation identity drifted",
    )
    authority = document.get("authorityBoundary", {})
    _require(
        authority.get("readOnlyLiveObservationAuthorized") is True
        and authority.get("isolatedTemporaryProjectionAuthorized") is True
        and authority.get("isolatedCodexHomeAuthorized") is True
        and authority.get("globalCodexConfigMutation") is False
        and authority.get("codexDesktopRestart") is False
        and authority.get("commonRootPayloadMutation") is False
        and authority.get("ccSwitchMutation") is False
        and authority.get("modelDispatch") is False
        and authority.get("gitCommitOrPush") is False,
        "Codex common-root reconciliation authority drifted",
    )
    fresh = document.get("freshTaskObservation", {})
    _require(
        set(fresh.get("removedCohortAbsent", [])) == REMOVED
        and fresh.get("docVisible") is True
        and fresh.get("pdfVisible") is True
        and fresh.get("runtimeOwnedDocumentsAlsoVisible") is True
        and fresh.get("runtimeOwnedPdfAlsoVisible") is True
        and fresh.get("independentLoaderEventObserved") is False,
        "Codex fresh-task exposure observation drifted",
    )
    causal = document.get("causalAssessment", {})
    _require(
        causal.get("ccSwitchCodexProjectionDisableSucceeded") is True
        and causal.get("codexHostExposureDisableSucceeded") is False
        and causal.get("alternateCommonRootCarrierStillPresent") is True
        and causal.get("commonRootCarrierIsBestCurrentExplanation") is True
        and causal.get("commonRootCarrierIndependentlyProvedAsCodexDiscoverable")
        is True
        and causal.get("currentTaskExactLoaderCarrierIdentityProved") is False,
        "Codex common-root causal assessment drifted",
    )
    preflight = document.get("isolatedPreflight", {})
    _require(
        preflight.get("temporaryProjectAgentsRoot") is True
        and preflight.get("isolatedCodexHome") is True
        and preflight.get("projectedSkillMdMatchedSource") is True
        and preflight.get("control")
        == {"targetCount": 2, "docEnabled": True, "pdfEnabled": True}
        and preflight.get("treatment")
        == {
            "sameIdentityPaths": True,
            "docEnabled": False,
            "pdfEnabled": False,
        }
        and preflight.get("stderrLineCount") == 0
        and preflight.get("threadStarted") is False
        and preflight.get("turnStarted") is False
        and preflight.get("modelRequestSent") is False
        and preflight.get("globalConfigWritten") is False,
        "Codex common-root isolated preflight drifted",
    )
    options = {
        item.get("option"): item.get("result")
        for item in document.get("optionAssessment", [])
        if isinstance(item, dict)
    }
    _require(
        options
        == {
            "remove doc/pdf links from ~/.agents/skills": "not-preferred",
            "retain current state": "reject",
            "add two exact Codex skills.config disabled entries": (
                "preferred-pending-authorization"
            ),
        },
        "Codex common-root option judgment drifted",
    )
    transaction = document.get("proposedLiveTransaction", {})
    _require(
        transaction.get("targets")
        == [
            "C:/Users/15521/.agents/skills/doc/SKILL.md",
            "C:/Users/15521/.agents/skills/pdf/SKILL.md",
        ]
        and transaction.get("enabled") is False
        and transaction.get("requiresNewAuthorization")
        == [
            "global Codex config mutation",
            "Codex Desktop restart",
            "exact rollback-backup cleanup",
        ]
        and "model dispatch" in transaction.get("doesNotRequire", []),
        "Codex common-root proposed transaction drifted",
    )
    cleanup = document.get("cleanup", {})
    _require(
        cleanup
        == {
            "temporaryProjectionRootAbsent": True,
            "isolatedCodexHomeAbsent": True,
            "repositoryCleanupInventoryStable": True,
        },
        "Codex common-root cleanup evidence drifted",
    )
    claims = document.get("claimBoundary", {})
    _require(
        claims.get("removedCohortFreshTaskAbsenceProved") is True
        and claims.get("docPdfFreshTaskPresenceProved") is True
        and claims.get("isolatedOfficialDisableMechanismProved") is True
        and claims.get("liveGlobalDisableApplied") is False
        and claims.get("livePostRestartExposureVerified") is False
        and claims.get("loaderInvocationProved") is False
        and claims.get("behavioralValueProved") is False
        and claims.get("programCloseoutProved") is False,
        "Codex common-root claim boundary drifted",
    )
    _require(
        document.get("documentation") == DOCUMENTATION_PATH,
        "Codex common-root documentation binding drifted",
    )
    text = (root / DOCUMENTATION_PATH).read_text(encoding="utf-8")
    for phrase in (
        "fresh-task contradiction found",
        "!=\nCodex host exposure disabled",
        "same two identity paths remained listed",
        "Deleting the two common-root links is not the preferred correction.",
        "requires new authorization",
        "still exposed to Codex through the common root",
    ):
        _require(
            phrase in text,
            f"Codex common-root documentation missing: {phrase}",
        )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args()
    root = args.root.resolve()
    document = json.loads((root / EVIDENCE_PATH).read_text(encoding="utf-8"))
    validate_reconciliation(document, root=root)
    print("Codex common-root doc/pdf exposure reconciliation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
