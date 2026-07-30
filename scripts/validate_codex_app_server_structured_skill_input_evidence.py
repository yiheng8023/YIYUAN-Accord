#!/usr/bin/env python3
"""Validate bounded Codex structured Skill-input evidence."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
EVIDENCE_PATH = (
    "registry/codex-app-server-structured-skill-input-evidence-2026-07-24.json"
)


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def validate_evidence(document: dict[str, Any], *, root: Path = ROOT) -> None:
    _require(document.get("schema") == 1, "Structured Skill evidence schema drifted")
    _require(
        document.get("status")
        == "host-accepted-structured-skill-input-loader-delivery-unproved",
        "Structured Skill evidence status overclaimed or drifted",
    )
    host = document.get("host", {})
    _require(
        host.get("runtimeVersion") == "0.145.0"
        and host.get("model") == "gpt-5.3-codex-spark"
        and host.get("reasoningEffort") == "low"
        and host.get("networkAccess") is False,
        "Structured Skill host binding drifted",
    )
    schema = document.get("runtimeSchemaEvidence", {})
    _require(
        schema.get("definition") == "SkillUserInput"
        and schema.get("requiredFields") == ["name", "path", "type"]
        and schema.get("typeEnum") == "skill"
        and schema.get("generatedSchemaRepositoryOwned") is False,
        "Structured Skill schema evidence drifted",
    )
    treatment = document.get("treatment", {})
    _require(
        treatment.get("selectedSkillInputMode") == "structured"
        and treatment.get("structuredSkillInputSent") is True
        and treatment.get("textPromptNamedSelectedSkill") is False
        and treatment.get("hostAcceptedStructuredSkillInput") is True
        and treatment.get("onlySelectedUserSkillEnabled") is True
        and treatment.get("allOtherUserSkillsDisabled") is True,
        "Structured Skill treatment fidelity drifted",
    )
    run = document.get("run", {})
    _require(
        run.get("status") == "fixture-pass-loader-causation-unproved"
        and run.get("visibleTestsPassed") is True
        and run.get("hiddenTestsPassed") is True
        and run.get("changedFiles")
        == ["retry_policy.py", "test_retry_policy.py"]
        and run.get("transientOutOfScopeWritePaths") == []
        and run.get("globalConfigStable") is True,
        "Structured Skill run boundary drifted",
    )
    claims = document.get("claimBoundary", {})
    _require(
        claims.get("provesRuntimeSchemaSupportsStructuredSkillInput") is True
        and claims.get("provesHostAcceptedExactStructuredSkillInput") is True
        and claims.get("provesTaskScopedSelectedSkillMetadataExposure") is True,
        "Structured Skill supported claims drifted",
    )
    for key in (
        "provesSkillLoaderInvocation",
        "provesSkillBodyRead",
        "provesSkillInstructionsReachedModel",
        "provesSkillCausation",
        "provesMattSuperiority",
        "provesProductionReadiness",
        "provesCrossHostValue",
    ):
        _require(claims.get(key) is False, f"Structured Skill evidence overclaimed: {key}")
    decision = document.get("decision", {})
    _require(
        decision.get("structuredSkillInputPreferredForFutureCodexTreatmentArms")
        is True
        and decision.get("historicalTextNamedRunsReclassifiedAsInvalid") is False
        and decision.get("architectureOrRetentionDecisionAllowed") is False,
        "Structured Skill decision boundary drifted",
    )
    documentation = root / str(document.get("documentation"))
    _require(documentation.is_file(), "Structured Skill documentation is missing")
    text = " ".join(documentation.read_text(encoding="utf-8").split())
    for phrase in (
        "host accepted structured Skill input; loader delivery unproved",
        "does not prove that the Skill loader invoked the Skill",
        "Future Codex treatment arms should use structured Skill input",
    ):
        _require(phrase in text, f"Structured Skill documentation boundary missing: {phrase}")


def main() -> int:
    document = json.loads((ROOT / EVIDENCE_PATH).read_text(encoding="utf-8"))
    validate_evidence(document)
    print("Codex structured Skill-input evidence validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
