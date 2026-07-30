#!/usr/bin/env python3
"""Validate the bounded comparative candidate-exposure preflight."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
EVIDENCE_PATH = (
    "registry/"
    "codex-app-server-comparative-candidate-exposure-preflight-2026-07-24.json"
)
PROTOCOL_PATH = (
    "registry/"
    "human-ai-collaboration-comparative-protocol-batch-01-2026-07-24.json"
)


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def validate_preflight(
    document: dict[str, Any],
    *,
    root: Path = ROOT,
    protocol: dict[str, Any] | None = None,
    program: dict[str, Any] | None = None,
) -> None:
    _require(document.get("schema") == 1, "Candidate preflight schema must be 1")
    _require(
        document.get("status")
        == "partial-current-host-disciplined-and-diagnose-pass-superpowers-selection-blocked",
        "Candidate preflight status overclaimed or drifted",
    )
    _require(
        document.get("parentProtocol") == PROTOCOL_PATH,
        "Candidate preflight parent protocol drifted",
    )

    host = document.get("host", {})
    _require(host.get("version") == "0.145.0", "Candidate preflight host drifted")
    _require(
        host.get("modelRequested") == "gpt-5.3-codex-spark"
        and host.get("reasoningEffortRequested") == "low"
        and host.get("providerFallbackAllowed") is False,
        "Candidate preflight weak-model binding drifted",
    )

    authority = document.get("authorityBoundary", {})
    _require(authority.get("metadataOnly") is True, "Candidate preflight left metadata-only mode")
    for key in (
        "taskTurnSent",
        "modelRequestSent",
        "candidateSkillContentMutated",
        "globalConfigWritten",
        "capabilityInstalledUpdatedOrRemoved",
        "mcpToolInvoked",
        "accountOrPrivateDataAccessed",
        "externalWritePerformed",
        "gitMutationPerformed",
    ):
        _require(authority.get(key) is False, f"Candidate preflight crossed authority: {key}")

    results = {
        item.get("candidateId"): item
        for item in document.get("candidateResults", [])
        if isinstance(item, dict)
    }
    _require(
        set(results)
        == {
            "cc.disciplined-coding",
            "cc.diagnose",
            "superpowers.test-driven-development",
            "superpowers.systematic-debugging",
        },
        "Candidate preflight result set drifted",
    )

    matt = results["cc.disciplined-coding"]
    _require(
        matt.get("outcome") == "pass-current-host-selected-skill-exposure-only",
        "Disciplined-coding exposure result drifted",
    )
    _require(
        matt.get("sha256")
        == "d36f49ed0d252b9c9c656bc9c0f72d43710c68591ce234e8dc2886dc4785fc7b",
        "Disciplined-coding digest drifted",
    )
    control = matt.get("controlInventory", {})
    selected = matt.get("selectedInventory", {})
    _require(
        control.get("userSkillCount") == 105
        and control.get("systemSkillCount") == 6,
        "Disciplined-coding control inventory drifted",
    )
    for key in (
        "onlySelectedUserSkillEnabled",
        "allOtherUserSkillsDisabled",
        "allNonUserStatesPreserved",
        "sameIdentitySet",
    ):
        _require(selected.get(key) is True, f"Disciplined-coding exposure invariant failed: {key}")
    _require(
        selected.get("enabledUserSkillCount") == 1,
        "Disciplined-coding enabled user Skill count drifted",
    )
    thread = matt.get("threadConfiguration", {})
    _require(
        thread.get("model") == "gpt-5.3-codex-spark"
        and thread.get("reasoningEffort") == "low"
        and thread.get("turnStarted") is False,
        "Disciplined-coding thread boundary drifted",
    )
    for key in (
        "selectedSkillStable",
        "globalConfigStable",
        "repositoryStatusDigestStable",
    ):
        _require(
            matt.get("prePostChecks", {}).get(key) is True,
            f"Disciplined-coding stability check failed: {key}",
        )

    diagnose = results["cc.diagnose"]
    _require(
        diagnose.get("outcome") == "pass-current-host-selected-skill-exposure-only",
        "Diagnose exposure result drifted",
    )
    _require(
        diagnose.get("sha256")
        == "28886402bbfa0470248086eab9106a103b964b76ae9496e63ff0c8a6761b6d13",
        "Diagnose digest drifted",
    )
    _require(
        diagnose.get("controlInventory") == matt.get("controlInventory"),
        "Diagnose control inventory drifted",
    )
    diagnose_selected = diagnose.get("selectedInventory", {})
    for key in (
        "onlySelectedUserSkillEnabled",
        "allOtherUserSkillsDisabled",
        "allNonUserStatesPreserved",
        "sameIdentitySet",
    ):
        _require(
            diagnose_selected.get(key) is True,
            f"Diagnose exposure invariant failed: {key}",
        )
    _require(
        diagnose_selected.get("enabledUserSkillCount") == 1,
        "Diagnose enabled user Skill count drifted",
    )
    diagnose_thread = diagnose.get("threadConfiguration", {})
    _require(
        diagnose_thread.get("model") == "gpt-5.3-codex-spark"
        and diagnose_thread.get("reasoningEffort") == "low"
        and diagnose_thread.get("turnStarted") is False,
        "Diagnose thread boundary drifted",
    )
    for key in (
        "selectedSkillStable",
        "globalConfigStable",
        "repositoryStatusDigestStable",
    ):
        _require(
            diagnose.get("prePostChecks", {}).get(key) is True,
            f"Diagnose stability check failed: {key}",
        )
    lineage = diagnose.get("sourceLineage", {})
    _require(
        lineage.get("exactHistoricalMattCommit")
        == "7afa86d3a5dd96edde06ffa014e16c64e733681e"
        and lineage.get("equalsCurrentMattMain") is False,
        "Diagnose source-lineage boundary drifted",
    )

    superpowers = results["superpowers.test-driven-development"]
    _require(
        superpowers.get("outcome")
        == "blocked-not-present-in-skills-list-selection-surface",
        "Superpowers selection result drifted",
    )
    _require(
        superpowers.get("sha256")
        == "b5b4717b8b761cce15a6cfe9022e33fd959e0894c0c39d72c9cb49c23486c10e",
        "Superpowers digest drifted",
    )
    attempts = superpowers.get("attempts", [])
    _require(
        [attempt.get("profile") for attempt in attempts]
        == [
            "all-plugin-features-disabled",
            "local-plugin-discovery-only",
            "installed-remote-plugin-discovery",
        ],
        "Superpowers feature-profile sequence drifted",
    )
    for attempt in attempts:
        _require(
            attempt.get("sameNameOrPathHints") == []
            and attempt.get("selectedThreadStarted") is False,
            "Superpowers absence boundary drifted",
        )
    _require(
        "does not prove" in superpowers.get("claimLimit", ""),
        "Superpowers claim limit is missing",
    )
    systematic = results["superpowers.systematic-debugging"]
    _require(
        systematic.get("outcome")
        == "blocked-not-present-in-skills-list-selection-surface",
        "Superpowers systematic-debugging selection result drifted",
    )
    _require(
        systematic.get("sha256")
        == "3b20719eca4f0461cb51a195221320d775dcf03b6859271066a03a5132a6ce7a",
        "Superpowers systematic-debugging digest drifted",
    )
    systematic_attempts = systematic.get("attempts", [])
    _require(
        [attempt.get("profile") for attempt in systematic_attempts]
        == [
            "all-plugin-features-disabled",
            "local-plugin-discovery-only",
            "installed-remote-plugin-discovery",
        ],
        "Superpowers systematic-debugging feature-profile sequence drifted",
    )
    for attempt in systematic_attempts:
        _require(
            attempt.get("sameNameOrPathHints") == []
            and attempt.get("selectedThreadStarted") is False,
            "Superpowers systematic-debugging absence boundary drifted",
        )

    postflight = document.get("postflightSnapshot", {})
    _require(
        postflight.get("failedSuperpowersAttemptsHavePerAttemptPrePostProof")
        is False
        and postflight.get("failedSuperpowersAttemptsHavePostflightOnly")
        is True,
        "Failed-attempt evidence limit was promoted",
    )
    sandbox_observation = postflight.get("managedCommandSandboxObservation", {})
    _require(
        sandbox_observation.get("defaultManagedCommandSandboxUserSkillCount")
        == 0
        and sandbox_observation.get(
            "outsideManagedCommandSandboxUserSkillCount"
        )
        == 105
        and sandbox_observation.get(
            "provesCcOrCodexSkillDiscoveryFailure"
        )
        is False,
        "Managed-command-sandbox visibility boundary drifted",
    )

    decision = document.get("decision", {})
    _require(
        decision.get("disciplinedCodingCandidateSpecificExposureProved") is True,
        "Disciplined-coding exposure decision drifted",
    )
    _require(
        decision.get("diagnoseCandidateSpecificExposureProved") is True,
        "Diagnose exposure decision drifted",
    )
    for key in (
        "superpowersTddCandidateSpecificExposureProved",
        "superpowersSystematicDebuggingCandidateSpecificExposureProved",
        "superpowersTddContentRejected",
        "superpowersSystematicDebuggingContentRejected",
        "superpowersTddLiveArmDispatched",
        "superpowersSystematicDebuggingLiveArmDispatched",
        "allPrimarySkillArmsReady",
        "liveComparativeExecutionStarted",
    ):
        _require(decision.get(key) is False, f"Candidate preflight decision overclaimed: {key}")

    claims = document.get("claimBoundary", {})
    _require(
        all(value is False for value in claims.values()),
        "Candidate preflight claim boundary was promoted",
    )

    doc_path = root / str(document.get("documentation"))
    _require(doc_path.is_file(), "Candidate preflight documentation is missing")
    text = " ".join(doc_path.read_text(encoding="utf-8").split())
    for phrase in (
        "selected exposure only",
        "host-interface selection result, not a content rejection",
        "task-scoped plugin Skill selection surface",
        "managed command sandbox",
    ):
        _require(phrase in text, f"Candidate preflight documentation boundary missing: {phrase}")

    if protocol is not None:
        exposure = protocol.get("exposureBinding", {})
        _require(
            exposure.get("candidateExposureEvidence") == EVIDENCE_PATH,
            "Candidate preflight protocol binding drifted",
        )
        _require(
            exposure.get("disciplinedCodingSelectedExposureProved") is True
            and exposure.get("diagnoseSelectedExposureProved") is True
            and exposure.get("superpowersTddSelectedExposureProved") is False,
            "Candidate preflight protocol projection drifted",
        )

    if program is not None:
        initiative = next(
            (
                item
                for item in program.get("currentInitiatives", [])
                if item.get("id")
                == "initiative.human-ai-collaboration-coverage-rebaseline"
            ),
            None,
        )
        _require(initiative is not None, "Candidate preflight initiative is missing")
        _require(
            initiative.get("currentCandidateExposureEvidence") == EVIDENCE_PATH,
            "Candidate preflight program binding drifted",
        )


def main() -> int:
    document = json.loads((ROOT / EVIDENCE_PATH).read_text(encoding="utf-8"))
    validate_preflight(document)
    print("Codex comparative candidate exposure preflight validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
