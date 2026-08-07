#!/usr/bin/env python3
"""Validate the LongHorizon safe-adapter and upstream-change design."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
RECORD_PATH = Path(
    "registry/process-loss-longhorizon-safe-adapter-upstream-design-2026-08-07.json"
)
DOCUMENTATION_PATH = Path(
    "docs/strategy/PROCESS-LOSS-LONGHORIZON-SAFE-ADAPTER-UPSTREAM-DESIGN-2026-08-07.md"
)
ACCEPTANCE_PATH = Path("registry/program-acceptance-map.json")
PLAN_PATH = Path("docs/strategy/RESEARCH-AND-POC-PLAN.md")
GOAL_PROMPT_PATH = Path("docs/operations/CURRENT-GOAL-MODE-PROMPT.md")
REVISION = "b49ebf9654c1ee75eaf56dfe9eec1745fddcfa58"
TREE_OID = "cf5470d1242e6a092c91a709efeff68c61d36681"
EVIDENCE_ID = "evidence.process-loss-longhorizon-safe-adapter-upstream-design-2026-08-07"
SUPPORTS = {
    "acceptance.end-to-end-process-fidelity",
    "acceptance.residual-gap-proof",
    "acceptance.discovery-reuse-before-authoring",
}
UPSTREAM_IDS = {
    "safe-host-permission-defaults",
    "cross-process-resume-command",
    "portable-process-control",
    "complete-mutation-evidence",
    "independent-core-tests-and-release-gate",
}
ADAPTER_IDS = {
    "host-execution-policy-port",
    "disposable-workspace-transaction-port",
    "parent-derived-route-receipt-port",
    "cumulative-process-loss-port",
    "capability-lifecycle-port",
    "recovery-validation-port",
}
FORBIDDEN = {
    "reimplement-manage-execute-audit-loop",
    "silently-fork-upstream-core",
    "replace-host-permission-system",
    "become-skill-or-plugin-manager",
    "self-authorize-installation-or-model-dispatch",
    "convert-static-evidence-into-behavior-or-value-claims",
}
PHASES = {
    "design": ("complete", False, True),
    "upstream-proposal": ("not-authorized", False, False),
    "pure-adapter-contract-poc-with-fake-candidate": ("not-authorized", False, False),
    "isolated-candidate-execution": ("not-authorized", False, False),
    "behavior-and-value-comparison": (
        "blocked-pending-natural-real-task-and-separate-authority",
        True,
        False,
    ),
}


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def _acceptance_evidence(acceptance: dict[str, Any]) -> dict[str, Any]:
    matches = [
        item
        for item in acceptance.get("evidence", [])
        if isinstance(item, dict) and item.get("id") == EVIDENCE_ID
    ]
    _require(len(matches) == 1, "LongHorizon design acceptance evidence registration drifted")
    return matches[0]


def validate_record(
    record: dict[str, Any],
    *,
    acceptance: dict[str, Any] | None = None,
    root: Path = ROOT,
) -> None:
    _require(
        record.get("schema") == 1
        and record.get("id") == "process-loss-longhorizon-safe-adapter-upstream-design-v1"
        and record.get("asOf") == "2026-08-07"
        and record.get("status")
        == "owner-authorized-design-complete-no-implementation-or-upstream-write",
        "LongHorizon design identity drifted",
    )
    source = record.get("sourceBindings", {})
    _require(
        record.get("documentation") == DOCUMENTATION_PATH.as_posix()
        and (root / DOCUMENTATION_PATH).is_file()
        and source.get("exactSourceReview")
        == "registry/process-loss-longhorizon-harness-exact-source-static-review-2026-08-07.json"
        and (root / source["exactSourceReview"]).is_file()
        and source.get("revision") == REVISION
        and source.get("treeOid") == TREE_OID,
        "LongHorizon design source binding drifted",
    )
    decision = record.get("decision", {})
    _require(
        decision
        == {
            "strategy": "upstream-first-with-thin-harness-adapter-only-for-retained-authority",
            "directAdoption": "blocked",
            "equivalentCoordinatorAuthoring": "stopped",
            "adapterImplementation": "not-authorized",
            "upstreamWrite": "not-authorized",
        },
        "LongHorizon design decision drifted",
    )
    upstream = record.get("upstreamChangeCandidates", [])
    _require(
        {item.get("id") for item in upstream if isinstance(item, dict)} == UPSTREAM_IDS
        and all(item.get("scope") and item.get("reason") for item in upstream),
        "LongHorizon upstream-change classification drifted",
    )
    adapter = record.get("thinAdapterResponsibilities", [])
    _require(
        {item.get("id") for item in adapter if isinstance(item, dict)} == ADAPTER_IDS
        and all(item.get("responsibility") for item in adapter),
        "LongHorizon thin-adapter responsibility drifted",
    )
    _require(
        set(record.get("forbiddenAdapterResponsibilities", [])) == FORBIDDEN,
        "LongHorizon adapter non-goal drifted",
    )
    phases = {
        item.get("id"): (
            item.get("status"), item.get("requiresRealTask"), item.get("allowedNow")
        )
        for item in record.get("phaseGates", [])
        if isinstance(item, dict)
    }
    _require(phases == PHASES, "LongHorizon design phase gate drifted")
    _require(
        len(record.get("adoptionStopConditions", [])) == 6,
        "LongHorizon adoption stop condition drifted",
    )
    authority = record.get("authorityBoundary", {})
    _require(
        authority.get("designAuthorized") is True
        and all(
            authority.get(key) is False
            for key in (
                "adapterImplementationAuthorized",
                "upstreamIssueOrPullRequestAuthorized",
                "candidateAcquisitionAuthorized",
                "installAuthorized",
                "executeAuthorized",
                "modelDispatchAuthorized",
                "accountConnectionAuthorized",
                "configurationMutationAuthorized",
                "ccSwitchMutationAuthorized",
                "consumerMutationAuthorized",
                "publicationAuthorized",
                "releaseAuthorized",
            )
        ),
        "LongHorizon design authority boundary drifted",
    )
    claims = record.get("claimBoundary", {})
    _require(
        claims.get("provesDesignClassification") is True
        and all(value is False for key, value in claims.items() if key != "provesDesignClassification"),
        "LongHorizon design claim boundary drifted",
    )
    _require(
        "separate owner authority" in record.get("nextGate", "")
        and "fake candidate" in record.get("nextGate", "")
        and "neither route authorizes candidate execution or model dispatch"
        in record.get("nextGate", ""),
        "LongHorizon design next gate drifted",
    )

    if acceptance is not None:
        counts: dict[str, int] = {}
        for criterion in acceptance.get("acceptanceCriteria", []):
            status = criterion.get("assessment")
            counts[status] = counts.get(status, 0) + 1
        boundary = record.get("acceptanceBoundary", {})
        _require(
            counts
            == {
                "verified": boundary.get("verifiedCriteria"),
                "partial": boundary.get("partialCriteria"),
            }
            and boundary.get("plannedCriteria") == 0
            and boundary.get("criteriaAdvancedByThisDesign") == [],
            "LongHorizon design acceptance non-promotion drifted",
        )
        evidence = _acceptance_evidence(acceptance)
        _require(
            evidence.get("path") == RECORD_PATH.as_posix()
            and set(evidence.get("supports", [])) == SUPPORTS
            and "no-implementation" in evidence.get("kind", "")
            and "no-behavior-value-or-residual-gap-proof" in evidence.get("kind", ""),
            "LongHorizon design acceptance evidence registration drifted",
        )

    normalized = " ".join((root / DOCUMENTATION_PATH).read_text(encoding="utf-8").split())
    for phrase in (
        "upstream-first, thin-adapter-only",
        REVISION,
        "The adapter is a boundary translator, not a second coordinator",
        "No real Claude task is required for this design gate",
        "Direct adoption is still blocked",
    ):
        _require(phrase in normalized, "LongHorizon design documentation drifted")
    plan = " ".join((root / PLAN_PATH).read_text(encoding="utf-8").split())
    goal_prompt = " ".join((root / GOAL_PROMPT_PATH).read_text(encoding="utf-8").split())
    for label, text in (("plan", plan), ("goal prompt", goal_prompt)):
        lowered = text.lower()
        _require(
            RECORD_PATH.as_posix() in text
            and REVISION in text
            and "no real claude task" in lowered
            and "direct adoption" in lowered,
            f"LongHorizon design {label} projection drifted",
        )


def validate_repository_design(root: Path = ROOT) -> dict[str, Any]:
    record = json.loads((root / RECORD_PATH).read_text(encoding="utf-8"))
    acceptance = json.loads((root / ACCEPTANCE_PATH).read_text(encoding="utf-8"))
    validate_record(record, acceptance=acceptance, root=root)
    return record


def main() -> int:
    validate_repository_design(ROOT)
    print("LongHorizon safe-adapter and upstream-change design validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
