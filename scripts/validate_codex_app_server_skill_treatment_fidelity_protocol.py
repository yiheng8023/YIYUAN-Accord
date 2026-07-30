#!/usr/bin/env python3
"""Validate the Codex Skill treatment-fidelity assay contract."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
PROTOCOL_PATH = (
    "registry/"
    "codex-app-server-skill-treatment-fidelity-protocol-2026-07-24.json"
)


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def validate_treatment_fidelity_protocol(
    document: dict[str, Any],
    *,
    root: Path = ROOT,
) -> None:
    _require(document.get("schema") == 1, "Treatment-fidelity schema must be 1")
    _require(
        document.get("status")
        == "live-assay-passed-synthetic-body-only-delivery-proved",
        "Treatment-fidelity status overclaimed or drifted",
    )
    host = document.get("hostBinding", {})
    _require(
        host.get("runtimeVersion") == "0.145.0"
        and host.get("model") == "gpt-5.3-codex-spark"
        and host.get("reasoningEffort") == "low"
        and host.get("providerFallbackAllowed") is False
        and host.get("approvalPolicy") == "never"
        and host.get("sandbox") == "read-only"
        and host.get("networkAllowed") is False,
        "Treatment-fidelity host binding drifted",
    )
    authority = document.get("authorityBoundary", {})
    _require(
        authority.get("disposableRootWritesAuthorized") is True
        and authority.get("repositoryProtocolWritesAuthorized") is True,
        "Treatment-fidelity local authority is missing",
    )
    for key in (
        "installedSkillMutationAuthorized",
        "globalConfigMutationAuthorized",
        "dependencyInstallAuthorized",
        "mcpOrAppUseAuthorized",
        "externalWriteAuthorized",
        "gitMutationAuthorized",
        "calibrationWriteAuthorized",
    ):
        _require(
            authority.get(key) is False,
            f"Treatment-fidelity authority promoted: {key}",
        )

    assay = document.get("assay", {})
    _require(
        assay.get("skillName") == "treatment-fidelity-canary"
        and assay.get("tokenLocationBeforeTurn") == "Skill body only"
        and assay.get("repetitions") == 3
        and assay.get("armOrder")
        == [
            ["control-unselected", "selected-structured-skill"],
            ["selected-structured-skill", "control-unselected"],
            ["control-unselected", "selected-structured-skill"],
        ],
        "Treatment-fidelity paired assay drifted",
    )
    forbidden_locations = set(assay.get("tokenForbiddenLocations", []))
    _require(
        {
            "Skill name",
            "frontmatter description",
            "Skill path",
            "public prompt",
            "structured Skill input",
            "process-scoped config override",
        }
        <= forbidden_locations,
        "Treatment-fidelity token isolation is incomplete",
    )
    _require(
        assay.get("controlArm", {}).get("expectedExactResponse")
        == "NO_TREATMENT"
        and assay.get("selectedArm", {}).get("structuredSkillInputSent")
        is True,
        "Treatment-fidelity arm contract drifted",
    )

    acceptance = document.get("acceptance", {})
    _require(
        acceptance
        and all(value is True for value in acceptance.values()),
        "Treatment-fidelity acceptance weakened",
    )
    _require(
        len(document.get("falsifiers", [])) >= 8,
        "Treatment-fidelity falsifiers are incomplete",
    )

    ladder = document.get("evidenceLadder", [])
    _require(
        [item.get("level") for item in ladder]
        == [
            "L0-source-identity",
            "L1-selected-metadata-exposure",
            "L2-structured-input-accepted",
            "L3-body-only-content-response",
            "L4-independent-loader-or-model-input-event",
            "L5-candidate-specific-causal-task-value",
        ],
        "Treatment-fidelity evidence ladder drifted",
    )
    _require(
        [item.get("currentInstalledCandidateEvidence") for item in ladder]
        == [True, True, True, False, False, False],
        "Treatment-fidelity installed-candidate evidence overclaimed",
    )

    claims = document.get("claimBoundary", {})
    _require(
        claims.get(
            "assayPassMayProveBodyOnlyContentReachedModelForSyntheticCanaryOnBoundHost"
        )
        is True,
        "Treatment-fidelity assay lost its bounded positive claim",
    )
    for key, value in claims.items():
        if key.startswith("assayPassMayProve") and key != (
            "assayPassMayProveBodyOnlyContentReachedModelForSyntheticCanaryOnBoundHost"
        ):
            _require(
                value is False,
                f"Treatment-fidelity claim promoted: {key}",
            )

    reuse = document.get("reuse", {})
    _require(
        reuse.get("inventoryAndOverride")
        == "scripts/probe_codex_app_server_skill_exposure.py"
        and reuse.get("structuredInputShape")
        == "scripts/run_human_ai_collaboration_weak_agent_trial.py"
        and reuse.get("doesNotCreateParallelSkillManager") is True,
        "Treatment-fidelity reuse boundary drifted",
    )
    for key in ("implementation", "documentation", "liveEvidence"):
        path = root / str(document.get(key))
        _require(path.is_file(), f"Treatment-fidelity {key} is missing")
    documentation = " ".join(
        (root / str(document["documentation"]))
        .read_text(encoding="utf-8")
        .split()
    )
    for phrase in (
        "body-only canary content reached the",
        "not be an independent loader notification",
        "would not prove that the installed historical `diagnose` body",
    ):
        _require(
            phrase in documentation,
            f"Treatment-fidelity documentation boundary missing: {phrase}",
        )
    decision = document.get("decision", {})
    _require(
        decision.get("liveAssayAuthorizedByCurrentGoal") is True
        and decision.get("liveAssayRunStarted") is True
        and decision.get("liveAssayPassed") is True
        and decision.get("syntheticCanaryBodyOnlyDeliveryProved") is True
        and decision.get("independentLoaderEventProved") is False
        and decision.get("installedCandidateAttributionAllowed") is False,
        "Treatment-fidelity decision overclaimed or drifted",
    )


def main() -> int:
    document = json.loads((ROOT / PROTOCOL_PATH).read_text(encoding="utf-8"))
    validate_treatment_fidelity_protocol(document)
    print("Codex Skill treatment-fidelity protocol validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
