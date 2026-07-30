#!/usr/bin/env python3
"""Validate requirements/domain exposure preflight evidence."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
EVIDENCE_PATH = Path(
    "registry/requirements-domain-exposure-preflight-evidence-2026-07-24.json"
)


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def validate_evidence(document: dict, *, root: Path = ROOT) -> None:
    _require(
        document.get("schema") == 1
        and document.get("status")
        == "pass-current-host-exposure-and-public-packet-boundary-only"
        and document.get("parentProtocol")
        == "registry/human-ai-collaboration-requirements-domain-challenge-protocol-batch-01-2026-07-24.json",
        "Requirements/domain preflight identity drifted",
    )
    authority = document.get("authorityBoundary", {})
    _require(
        authority.get("metadataAndThreadConfigurationOnly") is True,
        "Requirements/domain preflight authority mode drifted",
    )
    _require(
        all(
            value is False
            for key, value in authority.items()
            if key != "metadataAndThreadConfigurationOnly"
        ),
        "Requirements/domain preflight authority expanded",
    )
    host = document.get("host", {})
    _require(
        host.get("version") == "0.145.0"
        and host.get("modelRequested") == "gpt-5.3-codex-spark"
        and host.get("reasoningEffortRequested") == "low"
        and host.get("providerFallbackAllowed") is False
        and host.get("approvalPolicy") == "never"
        and host.get("sandbox") == "read-only"
        and host.get("networkAccess") is False,
        "Requirements/domain preflight host binding drifted",
    )
    fixture = document.get("fixtureBoundary", {})
    _require(
        fixture.get("fixtureId") == "fixture.source-bound-domain-plan-challenge-v1"
        and fixture.get("fixtureDefinitionSha256")
        == "3b06392a4ac47a76d0a1eea5e777533c67577a13abca890204f4a8aba61dbb81"
        and fixture.get("builderSha256")
        == "ee71f0f393744ad3852af1fd3c7e5d32aef084a515f1d70e0a2b12e25ec74822"
        and fixture.get("samePublicTaskPrompt") is True
        and fixture.get("privateOracleContentWrittenIntoTrial") is False
        and fixture.get("privateSentinelsPresentInTrialFiles") == []
        and fixture.get("nativeSelectedSkillAbsent") is True
        and fixture.get("candidateSelectedSkillName") == "grill-with-docs",
        "Requirements/domain packet or oracle boundary drifted",
    )
    candidate = document.get("candidate", {})
    _require(
        candidate.get("bytes") == 5340
        and candidate.get("sha256")
        == "e1078020c41b954638ba94acda95a3340739908bd68b1db9bc2af129d3936035"
        and candidate.get("prePostStable") is True,
        "Requirements/domain candidate pin drifted",
    )
    inventory = document.get("controlInventory", {})
    _require(
        inventory.get("skillCount") == 111
        and inventory.get("userSkillCount") == 105
        and inventory.get("systemSkillCount") == 6
        and inventory.get("identityManifestSha256")
        == "09bff0fcecfaf92cf962fbf9d4838d1831b83e4632c488500c4acbb4a392158e",
        "Requirements/domain inventory drifted",
    )
    _require(
        document.get("nativeDisabledProfile")
        == {
            "sameIdentitySet": True,
            "enabledConfigurableSkillCount": 0,
            "allConfigurableSkillsDisabled": True,
            "allNonConfigurableStatesPreserved": True,
        },
        "Requirements/domain native profile drifted",
    )
    _require(
        document.get("selectedProfile")
        == {
            "sameIdentitySet": True,
            "enabledConfigurableSkillCount": 1,
            "onlyExpectedConfigurableSkillEnabled": True,
            "allNonConfigurableStatesPreserved": True,
        },
        "Requirements/domain selected profile drifted",
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
            f"Requirements/domain {arm} thread binding drifted",
        )
    process = document.get("processBoundary", {})
    _require(
        process.get("turnStarted") is False
        and process.get("modelRequestSent") is False
        and process.get("mcpStartupFailureCount") == 0
        and process.get("pluginsAndAppsDisabledForProbe") is True
        and process.get("staticMcpServersDisabledForProbe") is True
        and process.get("mcpToolInvoked") is False,
        "Requirements/domain process boundary drifted",
    )
    _require(
        all(document.get("mutationBoundary", {}).values()),
        "Requirements/domain mutation boundary drifted",
    )
    decision = document.get("decision", {})
    for key in (
        "freshCandidateHashVerified",
        "nativeDisabledExposureProved",
        "candidateSpecificSelectedExposureProved",
        "publicPromptPrivateOracleBoundaryPassed",
        "technicalPreflightReadyForFirstLivePair",
    ):
        _require(decision.get(key) is True, f"Requirements/domain decision drifted: {key}")
    _require(
        decision.get("liveWeakAgentRunStarted") is False
        and decision.get("preferenceDecisionAllowed") is False
        and decision.get("selfAuthoredChangeJustified") is False
        and decision.get("candidateInstallUpdateOrRemovalJustified") is False,
        "Requirements/domain decision overclaimed",
    )
    _require(
        all(value is False for value in document.get("claimBoundary", {}).values()),
        "Requirements/domain preflight claim boundary was promoted",
    )
    doc_path = root / str(document.get("documentation"))
    _require(doc_path.is_file(), "Requirements/domain preflight documentation is missing")
    text = " ".join(doc_path.read_text(encoding="utf-8").split())
    for phrase in (
        "No `turn/start` was sent",
        "Three private sentinels",
        "proves no loader invocation",
        "Three valid pairs remain required",
    ):
        _require(phrase in text, f"Requirements/domain preflight doc missing boundary: {phrase}")


def main() -> int:
    document = json.loads((ROOT / EVIDENCE_PATH).read_text(encoding="utf-8"))
    validate_evidence(document, root=ROOT)
    print("Requirements/domain exposure preflight evidence validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
