#!/usr/bin/env python3
"""Validate maintenance/migration exposure preflight evidence."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
EVIDENCE_PATH = (
    "registry/maintenance-migration-exposure-preflight-evidence-2026-07-24.json"
)
PROTOCOL_PATH = (
    "registry/"
    "human-ai-collaboration-maintenance-migration-protocol-batch-01-2026-07-24.json"
)


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def validate_evidence(document: dict[str, Any], *, root: Path = ROOT) -> None:
    _require(document.get("schema") == 1, "Migration preflight schema must be 1")
    _require(
        document.get("status")
        == "pass-current-host-exposure-and-prompt-boundary-only"
        and document.get("parentProtocol") == PROTOCOL_PATH,
        "Migration preflight identity or status drifted",
    )
    host = document.get("host", {})
    _require(
        host.get("version") == "0.145.0"
        and host.get("modelRequested") == "gpt-5.3-codex-spark"
        and host.get("reasoningEffortRequested") == "low"
        and host.get("providerFallbackAllowed") is False,
        "Migration preflight host binding drifted",
    )

    authority = document.get("authorityBoundary", {})
    _require(
        authority.get("metadataAndThreadConfigurationOnly") is True,
        "Migration preflight authority mode drifted",
    )
    for key, value in authority.items():
        if key != "metadataAndThreadConfigurationOnly":
            _require(value is False, f"Migration preflight crossed authority: {key}")

    invalid = document.get("invalidAttempts", [])
    _require(
        len(invalid) == 2
        and invalid[0].get("errorCode") == -32600
        and invalid[0].get("countsAsCandidateResult") is False
        and invalid[1].get("reportSha256")
        == "db77ed185f5d440bef6c4348f02b2ef3e7e1b4f1686f38d40d4c069156698b49"
        and invalid[1].get("countsAsCandidateResult") is False,
        "Migration preflight invalid-attempt accounting drifted",
    )

    fixture = document.get("fixtureBoundary", {})
    _require(
        fixture.get("fixtureId")
        == "fixture.python-versioned-record-migration-v1"
        and fixture.get("privateOracleSha256")
        == "7fc220dafd0bf2eafc1c6de1dca94774580a1e9d14ae5d7a88081674a271aecf"
        and fixture.get("privateOracleContentWrittenIntoTrial") is False
        and fixture.get("instructionCarrierSourceAndCopiesEqual") is True
        and fixture.get("baselineVisibleTestsPass") is True
        and fixture.get("baselinePrivateOraclePasses") is False
        and fixture.get("temporaryPreflightRootRemovedAfterCapture") is True,
        "Migration preflight fixture boundary drifted",
    )

    candidate = document.get("candidate", {})
    _require(
        candidate.get("bytes") == 12510
        and candidate.get("sha256")
        == "52ef07de05726292c0f5e9fe666cc30e6efbe580ed775621e785a49ec80bd4ea"
        and candidate.get("prePostStable") is True,
        "Migration preflight candidate pin drifted",
    )
    inventory = document.get("controlInventory", {})
    _require(
        inventory.get("skillCount") == 111
        and inventory.get("userSkillCount") == 105
        and inventory.get("systemSkillCount") == 6
        and inventory.get("identityManifestSha256")
        == "09bff0fcecfaf92cf962fbf9d4838d1831b83e4632c488500c4acbb4a392158e",
        "Migration preflight inventory drifted",
    )

    native = document.get("nativeDisabledProfile", {})
    _require(
        native.get("sameIdentitySet") is True
        and native.get("enabledConfigurableSkillCount") == 0
        and native.get("allConfigurableSkillsDisabled") is True
        and native.get("allNonConfigurableStatesPreserved") is True,
        "Migration native-disabled exposure drifted",
    )
    selected = document.get("selectedProfile", {})
    _require(
        selected.get("sameIdentitySet") is True
        and selected.get("enabledConfigurableSkillCount") == 1
        and selected.get("onlyExpectedConfigurableSkillEnabled") is True
        and selected.get("allNonConfigurableStatesPreserved") is True,
        "Migration selected exposure drifted",
    )

    for arm in ("native", "selected"):
        thread = document.get("threadProfiles", {}).get(arm, {})
        _require(
            thread.get("model") == "gpt-5.3-codex-spark"
            and thread.get("reasoningEffort") == "low"
            and thread.get("modelProvider") == "openai"
            and thread.get("approvalPolicy") == "never"
            and thread.get("sandbox", {}).get("type") == "readOnly"
            and thread.get("sandbox", {}).get("networkAccess") is False,
            f"Migration {arm} thread binding drifted",
        )

    prompt = document.get("promptBoundary", {})
    _require(
        prompt.get("samePublicTaskPrompt") is True
        and prompt.get("nativeSelectedSkillAbsent") is True
        and prompt.get("candidateSelectedSkillName")
        == "deprecation-and-migration"
        and prompt.get("privateSentinelsPresentInTrialFiles") == []
        and prompt.get("privateOracleFilePresent") is False
        and prompt.get("publicTaskPromptSha256")
        == "70f7a7e7797b0b366b754876c593d9cac83957fe0b612c32509436594873e8e7",
        "Migration prompt/oracle boundary drifted",
    )
    process = document.get("processBoundary", {})
    _require(
        process.get("turnStarted") is False
        and process.get("modelRequestSent") is False
        and process.get("mcpStartupFailureCount") == 0,
        "Migration preflight process boundary drifted",
    )
    _require(
        all(document.get("mutationBoundary", {}).values()),
        "Migration preflight mutation stability drifted",
    )

    decision = document.get("decision", {})
    for key in (
        "freshCandidateHashVerified",
        "nativeDisabledExposureProved",
        "candidateSpecificSelectedExposureProved",
        "publicPromptPrivateOracleBoundaryPassed",
        "technicalPreflightReadyForFirstLivePair",
    ):
        _require(decision.get(key) is True, f"Migration preflight decision drifted: {key}")
    _require(
        decision.get("liveWeakAgentRunStarted") is False
        and decision.get("preferenceDecisionAllowed") is False,
        "Migration preflight decision overclaimed",
    )
    _require(
        all(value is False for value in document.get("claimBoundary", {}).values()),
        "Migration preflight claim boundary was promoted",
    )
    _require(
        document.get("validReportSha256")
        == "58382ffaa0ab7fb7dcef583af2f0f10334648fca59649a6866019f97c576608d",
        "Migration preflight report digest drifted",
    )

    doc_path = root / str(document.get("documentation"))
    _require(doc_path.is_file(), "Migration preflight documentation is missing")
    text = " ".join(doc_path.read_text(encoding="utf-8").split())
    for phrase in (
        "No `turn/start` was sent",
        "private sentinels",
        "excluded",
        "proves no Skill loader invocation",
    ):
        _require(phrase in text, f"Migration preflight doc missing boundary: {phrase}")


def main() -> int:
    document = json.loads((ROOT / EVIDENCE_PATH).read_text(encoding="utf-8"))
    validate_evidence(document, root=ROOT)
    print("Maintenance/migration exposure preflight evidence validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
