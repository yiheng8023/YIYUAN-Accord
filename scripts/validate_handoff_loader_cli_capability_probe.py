#!/usr/bin/env python3
"""Validate the bounded Codex CLI handoff capability probe."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
EVIDENCE_PATH = (
    "registry/handoff-loader-cli-0.145.0-capability-probe-2026-07-28.json"
)
DOCUMENTATION_PATH = (
    "docs/handoff-loader-cli-0.145.0-capability-probe-2026-07-28.md"
)


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def _artifact_bytes(arm: dict[str, Any]) -> bytes:
    lines = arm.get("contentLines")
    _require(
        isinstance(lines, list)
        and lines
        and all(isinstance(line, str) for line in lines),
        "Handoff probe artifact content drifted",
    )
    return ("\n".join(lines) + "\n").encode("utf-8")


def validate_probe(document: dict[str, Any], *, root: Path = ROOT) -> None:
    _require(
        document.get("schema") == 1
        and document.get("id")
        == "handoff-loader-cli-0.145.0-capability-probe-2026-07-28"
        and document.get("date") == "2026-07-28"
        and document.get("status")
        == (
            "observed-current-host-explicit-cue-associated-output-"
            "no-exact-loader-event"
        )
        and document.get("scenarioId") == "HND-FRESH-01",
        "Handoff CLI probe identity drifted",
    )
    authority = document.get("authorityBoundary")
    _require(
        isinstance(authority, dict)
        and authority.get("oneTemporaryMarkdownPerSuccessfulProbe") is True
        and all(
            authority.get(key) is False
            for key in (
                "repositoryMutationAuthorized",
                "gitMutationAuthorized",
                "configurationMutationAuthorized",
                "skillMutationAuthorized",
                "accountMutationAuthorized",
                "networkMutationAuthorized",
            )
        ),
        "Handoff CLI probe authority boundary drifted",
    )
    runtime = document.get("runtime")
    _require(
        isinstance(runtime, dict)
        and runtime.get("host") == "codex-cli"
        and runtime.get("hostVersion") == "0.145.0"
        and runtime.get("repositoryHead")
        == "55659f30091990f7c589932e0379880de30dc403"
        and runtime.get("repositoryOriginMain")
        == "55659f30091990f7c589932e0379880de30dc403"
        and runtime.get("repositoryAhead") == 0
        and runtime.get("repositoryBehind") == 0
        and runtime.get("successfulProbeRequestedModel") == "gpt-5.4-mini"
        and runtime.get("successfulProbeRequestedReasoning") == "low"
        and runtime.get("actualModelIndependentlyVerified") is False
        and runtime.get("actualReasoningIndependentlyVerified") is False,
        "Handoff CLI probe runtime boundary drifted",
    )
    source = document.get("sourceBackedSkill")
    _require(
        isinstance(source, dict)
        and source.get("identity") == "handoff"
        and source.get("storageAuthority") == "cc-switch-ssot"
        and source.get("skillMdSha256")
        == "57c9f1f392d7352cdc85b1e39ca49eddc70ce1dc278bd9653fb4f23dfc2560fc"
        and source.get("openaiYamlSha256")
        == "5c479fd562c691851690e8b18c8501045bef0943c10743d636b2fae26add1d28"
        and source.get("skillBodyRequiresSuggestedSkillsSection") is True
        and source.get("implicitInvocationAllowedByOpenaiYaml") is False,
        "Handoff CLI probe source identity drifted",
    )
    sequence = document.get("probeSequence")
    _require(
        isinstance(sequence, list)
        and len(sequence) == 2
        and sequence[0].get("requestedModel") == "gpt-5.3-codex-spark"
        and sequence[0].get("result") == "model-capacity-failure"
        and sequence[0].get("artifactCreated") is False
        and sequence[1].get("result")
        == "completed-generic-skills-budget-message-only"
        and sequence[1].get("exactHandoffLoaderEventObserved") is False,
        "Handoff CLI probe sequence drifted",
    )
    pair = document.get("pairedBehaviorProbe")
    _require(isinstance(pair, dict), "Handoff CLI paired probe missing")
    positive = pair.get("explicitCueArm")
    control = pair.get("nativeControlArm")
    _require(
        isinstance(positive, dict)
        and isinstance(control, dict)
        and positive.get("cue") == "$handoff"
        and control.get("cue") is None
        and positive.get("exactHandoffLoaderEventObserved") is False
        and control.get("exactHandoffLoaderEventObserved") is False,
        "Handoff CLI paired-arm boundary drifted",
    )
    for label, arm in (("positive", positive), ("control", control)):
        digest = hashlib.sha256(_artifact_bytes(arm)).hexdigest()
        _require(
            digest == arm.get("sha256"),
            f"Handoff CLI {label} artifact digest drifted",
        )
    positive_text = _artifact_bytes(positive).decode("utf-8")
    control_text = _artifact_bytes(control).decode("utf-8")
    _require(
        "## Suggested Skills" in positive_text
        and "## Suggested Skills" not in control_text,
        "Handoff CLI discriminating behavior drifted",
    )
    comparison = document.get("comparison")
    _require(
        isinstance(comparison, dict)
        and comparison.get("sameHostVersion") is True
        and comparison.get("sameRequestedModelAndReasoning") is True
        and comparison.get("sameBoundedTaskClass") is True
        and comparison.get("sameNoMutationBoundary") is True
        and comparison.get("distinctFreshCliThreadIds") is True
        and comparison.get("explicitArmHasSuggestedSkillsSection") is True
        and comparison.get("nativeControlHasSuggestedSkillsSection") is False
        and comparison.get("behaviorAssociationObserved") is True
        and comparison.get(
            "exactLoaderIdentityOrDigestBoundToTaskEventObserved"
        )
        is False
        and comparison.get("skillWasKnownToBeModelVisible") is False
        and comparison.get("causalInstructionDeliveryProved") is False,
        "Handoff CLI comparison boundary drifted",
    )
    cleanup = document.get("cleanup")
    _require(
        isinstance(cleanup, dict)
        and cleanup.get("temporaryPositiveDirectoryRemoved") is True
        and cleanup.get("temporaryControlDirectoryRemoved") is True
        and cleanup.get("repositoryProbeArtifactCreated") is False,
        "Handoff CLI cleanup evidence drifted",
    )
    decision = document.get("decision")
    _require(
        isinstance(decision, dict)
        and decision.get("formalPreflightStatusRemains")
        == "blocked-missing-handoff-loader-observability"
        and decision.get("formalArmCAdmitted") is False
        and decision.get("freshSessionSkillInvocationProved") is False,
        "Handoff CLI decision boundary drifted",
    )
    claims = document.get("claimBoundary")
    _require(
        isinstance(claims, dict)
        and claims
        and all(value is False for value in claims.values()),
        "Handoff CLI claim boundary drifted",
    )
    _require(
        document.get("documentation") == DOCUMENTATION_PATH,
        "Handoff CLI documentation binding drifted",
    )
    text = " ".join(
        (root / DOCUMENTATION_PATH).read_text(encoding="utf-8").split()
    )
    for phrase in (
        "bounded behavior association",
        "not exact invocation evidence",
        "blocked-missing-handoff-loader-observability",
        "does not admit canonical Arm C",
        "Both temporary output directories",
    ):
        _require(
            phrase in text,
            f"Handoff CLI documentation missing: {phrase}",
        )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args()
    root = args.root.resolve()
    document = json.loads((root / EVIDENCE_PATH).read_text(encoding="utf-8"))
    validate_probe(document, root=root)
    print("Handoff CLI capability probe verified")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
