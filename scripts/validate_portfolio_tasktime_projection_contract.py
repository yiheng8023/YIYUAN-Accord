#!/usr/bin/env python3
"""Validate the portfolio/task-time semantic projection as a pure contract."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
AUTHORITY_PATH = "registry/skill-portfolio-current-authority.json"
PROJECTION_PATH = "registry/portfolio-tasktime-projection-contract-2026-08-06.json"
PLUGIN_DECISION_PATH = (
    "registry/plugin-distribution-and-manager-boundary-decision-2026-08-08.json"
)
PLUGIN_POC_PATH = "registry/offline-plugin-projection-poc-2026-08-08.json"
ACCEPTANCE_PATH = "registry/program-acceptance-map.json"
PLAN_PATH = "docs/strategy/RESEARCH-AND-POC-PLAN.md"
GOAL_PROMPT_PATH = "docs/operations/CURRENT-GOAL-MODE-PROMPT.md"
README_PATH = "README.md"
README_ZH_PATH = "README.zh-CN.md"
AUTHORITY_ID = "skill-portfolio-current-authority-v1"
PROJECTION_ID = "portfolio-tasktime-projection-v1"
MARKER = f"semantic-projection: {PROJECTION_ID}"

MUTATION_CASE_IDS = [
    "authority-id-drift",
    "curation-real-task-global-stop",
    "curation-installation-authority-promotion",
    "curation-stop-rule-removal",
    "mechanism-real-task-global-stop",
    "mechanism-claim-promotion",
    "task-time-real-task-removal",
    "task-time-current-gap-removal",
    "task-time-activation-authority-removal",
    "user-invented-task-burden-promotion",
    "direct-installer-manager-authority-promotion",
    "plugin-whole-product-promotion",
    "plugin-cc-switch-dependency-promotion",
    "plugin-third-party-bundling-promotion",
    "plugin-release-eligibility-promotion",
    "residual-gap-authoring-gate-removal",
    "broad-claim-promotion",
    "decision-packet-core-boundary-removal",
    "acceptance-verification-downgrade",
]


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def _set(value: Any) -> set[Any]:
    return set(value) if isinstance(value, list) else set()


def validate_contract(
    authority: dict[str, Any],
    projection: dict[str, Any],
    plugin_decision: dict[str, Any],
    acceptance: dict[str, Any],
    *,
    plan_text: str,
    goal_prompt_text: str,
    readme_text: str,
    readme_zh_text: str,
) -> None:
    """Fail closed on semantic drift without executing a model or capability."""
    _require(
        authority.get("schema") == 1
        and authority.get("id") == AUTHORITY_ID
        and authority.get("status") == "current-policy-authority"
        and authority.get("activeRelease") is None,
        "portfolio authority identity drifted",
    )
    _require(
        projection.get("schema") == 1
        and projection.get("id") == PROJECTION_ID
        and projection.get("semanticAuthorityId") == AUTHORITY_ID
        and projection.get("semanticAuthorityPath") == AUTHORITY_PATH
        and projection.get("projectionMarker") == MARKER,
        "projection identity drifted",
    )
    _require(
        projection.get("projections")
        == {
            "plan": PLAN_PATH,
            "acceptance": ACCEPTANCE_PATH,
            "goalModePrompt": GOAL_PROMPT_PATH,
        },
        "projection path binding drifted",
    )
    decision_packet_core = {
        "design": "docs/superpowers/specs/2026-08-08-harness-decision-packet-core-design.md",
        "evidence": "registry/harness-decision-packet-core-poc-2026-08-08.json",
        "status": "verified-zero-model-source-bound-decision-packet-mechanism-only",
        "primaryConsumer": "agent-or-harness",
        "naturalLanguageInterpretationProved": False,
        "liveRouteSelectionProved": False,
        "behaviorOrValueProved": False,
        "portableCoreDependsOnPluginOrManager": False,
    }
    _require(
        authority.get("decisionPacketCore") == decision_packet_core
        and projection.get("sourceBindings", {}).get("decisionPacketCore")
        == decision_packet_core,
        "decision-packet core authority/projection binding drifted",
    )

    authority_modes = authority.get("operatingModes", {})
    authority_curation = authority_modes.get("portfolioCuration", {})
    authority_task_time = authority_modes.get("taskTimeActivation", {})
    _require(
        authority_curation.get("requiresOneEndUserTask") is False
        and _set(authority_curation.get("requiredBindings"))
        == {
            "coverage-objective-or-demand-taxonomy",
            "candidate-and-source-boundary",
            "account-and-data-boundary",
            "inactive-acquisition-isolation",
            "review-and-admission-criteria",
            "authority-boundary",
            "verification-surface",
            "cohort-or-stop-rule",
            "cleanup-and-rollback",
        }
        and _set(authority_curation.get("allowedActions"))
        == {
            "discover",
            "acquire-exact-revision-into-inactive-root",
            "review",
            "compare",
            "reject",
            "record-admission-decision",
            "prepare-manager-transaction",
        }
        and _set(authority_curation.get("separatelyAuthorizedActions"))
        == {
            "install",
            "enable",
            "connect-account",
            "execute",
            "promote",
            "persistently-activate",
        },
        "authority portfolio-curation contract drifted",
    )
    _require(
        authority_task_time.get("requiresBoundTaskAndGap") is True
        and authority_task_time.get("defaultState") == "minimal-task-scoped"
        and authority_task_time.get("installationIsNotActivation") is True
        and authority_task_time.get("activationIsNotBehaviorOrValueEvidence") is True,
        "authority task-time contract drifted",
    )

    lanes = projection.get("schedulerLanes", {})
    curation = lanes.get("portfolioCuration", {})
    _require(
        curation.get("requiresRealTask") is False
        and curation.get("stopRuleRequired") is True
        and curation.get("installationOrActivationAuthorized") is False
        and _set(curation.get("allowedActions"))
        == {
            "bounded-discovery",
            "exact-revision-inactive-acquisition",
            "static-and-deterministic-review",
            "overlap-and-dependency-comparison",
            "reject-or-record-admission-decision",
            "prepare-separately-authorized-manager-transaction",
        },
        "portfolio-curation scheduler lane drifted",
    )
    mechanism = lanes.get("mechanismValidation", {})
    _require(
        mechanism.get("requiresRealTask") is False
        and _set(mechanism.get("allowedEvidence"))
        == {
            "synthetic-fixture",
            "zero-model-probe",
            "failure-injection",
            "static-contract-check",
        }
        and mechanism.get("claimBoundary") == "mechanism-only",
        "mechanism-validation scheduler lane drifted",
    )
    task_time = lanes.get("taskTimeBehaviorAndValue", {})
    _require(
        task_time.get("requiresRealTask") is True
        and task_time.get("requiresCurrentCapabilityGap") is True
        and task_time.get("requiresSeparateActivationAuthority") is True
        and task_time.get("claimBoundary") == "behavior-value-production",
        "task-time behavior/value lane drifted",
    )
    authored = lanes.get("repositoryAuthoredGapFill", {})
    authority_authored = authority.get("selfAuthoredBoundary", {})
    _require(
        authored.get("requiresResidualGapEvidence") is True
        and authored.get("currentPriority")
        == "after-native-official-reviewed-external-and-composition"
        and authority_authored.get("residualGapRequired") is True
        and authority_authored.get("currentPriority")
        == "not-before-candidate-and-composition-reuse",
        "residual-gap authoring gate drifted",
    )

    burden = projection.get("burdenBoundary", {})
    _require(
        burden.get("doNotRequireUserToInventTasks") is True
        and burden.get("harnessOwnsBoundedPortfolioProgression") is True
        and _set(burden.get("askUserOnlyFor"))
        == {
            "real-domain-input-when-naturally-available",
            "trust-or-data-boundary-change",
            "meaningful-cost-or-side-effect-authority",
            "consequential-domain-judgment",
        },
        "user-burden boundary drifted",
    )
    freshness = projection.get("ccSwitchFreshnessBoundary", {})
    _require(
        freshness.get("skillsShMayAddUpstreamRepositoryToCc") is True
        and freshness.get("ccRefreshAndUpdatePreserveManagerAuthority") is True
        and freshness.get("upstreamRepositoryRemainsFreshnessAuthority") is True
        and freshness.get("directUpstreamInstallerPreservesManagerAuthority") is False
        and freshness.get("directInstallerSafeUse")
        == "isolated-inactive-acquisition-only-unless-separately-admitted",
        "CC Switch freshness and manager boundary drifted",
    )
    manager = authority.get("managerBoundary", {})
    _require(
        manager.get("currentOperationalAdapter") == "CC Switch where suitable"
        and manager.get("portableProductDependency") is False
        and manager.get("defaultReviewedPoolState")
        == "inactive-until-separately-authorized",
        "replaceable manager boundary drifted",
    )
    authority_plugin = authority.get("pluginDistributionBoundary", {})
    projection_plugin = projection.get("pluginDistributionBoundary", {})
    decision = plugin_decision.get("decision", {})
    release = plugin_decision.get("releaseEligibility", {})
    expected_plugin_boundary = {
        "wholeRepositoryBecomesPlugin": False,
        "pluginCompatibilityRequired": True,
        "pluginIsConsumerProjection": True,
        "managerImplementationRequiredForPackaging": False,
        "portableCoreDependsOnCcSwitch": False,
        "oneLifecycleAuthorityPerComponent": True,
        "ccManagedThirdPartyPayloadMayBeBundled": False,
        "hostNativePluginManagerOwnsHostPluginLifecycle": True,
    }
    _require(
        plugin_decision.get("schema") == 1
        and plugin_decision.get("id")
        == "plugin-distribution-and-manager-boundary-decision-2026-08-08"
        and plugin_decision.get("status")
        == "owner-accepted-plugin-compatible-manager-agnostic-release-not-eligible"
        and release.get("eligibleNow") is False,
        "plugin distribution decision identity or release boundary drifted",
    )
    for key, value in expected_plugin_boundary.items():
        _require(
            authority_plugin.get(key) == value
            and projection_plugin.get(key) == value
            and decision.get(key) == value,
            f"plugin distribution boundary drifted: {key}",
        )
    _require(
        authority_plugin.get("decision") == PLUGIN_DECISION_PATH
        and projection_plugin.get("decisionRecord") == PLUGIN_DECISION_PATH
        and authority_plugin.get("offlineProjectionPoc") == PLUGIN_POC_PATH
        and projection_plugin.get("offlineProjectionPoc") == PLUGIN_POC_PATH
        and authority_plugin.get("offlineProjectionPocStatus")
        == "offline-preview-verified-release-not-eligible"
        and projection_plugin.get("offlineProjectionPocStatus")
        == "offline-preview-verified-release-not-eligible"
        and authority_plugin.get("nextGate")
        == "admitted-repository-owned-component-plus-natural-real-task-before-live-plugin-validation"
        and projection_plugin.get("nextGate")
        == "admitted-repository-owned-component-plus-natural-real-task-before-live-plugin-validation"
        and projection_plugin.get("releaseEligibleNow") is False
        and projection_plugin.get("installationEnablementPublicationAuthorized")
        is False
        and authority_plugin.get("releaseEligibleNow") is False
        and decision.get("currentPosture")
        == "plugin-compatible-manager-agnostic-release-not-eligible",
        "plugin projection authority or current posture drifted",
    )

    claim = projection.get("claimBoundary", {})
    _require(
        claim
        == {
            "projectionConsistencyProvesBehavior": False,
            "portfolioProgressProvesCandidateValue": False,
            "managerInstallationProvesActivation": False,
            "activationProvesInstructionDelivery": False,
            "instructionDeliveryProvesValue": False,
        },
        "projection claim boundary drifted",
    )
    deterministic = projection.get("deterministicValidation", {})
    _require(
        deterministic.get("mode") == "pure-zero-model-failure-injection"
        and deterministic.get("validator")
        == "scripts/validate_portfolio_tasktime_projection_contract.py"
        and deterministic.get("test")
        == "tests/test_portfolio_tasktime_projection_contract.py"
        and deterministic.get("mutationCaseIds") == MUTATION_CASE_IDS
        and deterministic.get("claimBoundary")
        == "projection-consistency-and-fail-closed-mechanism-only",
        "deterministic validation binding drifted",
    )

    criteria = {
        item.get("id"): item
        for item in acceptance.get("acceptanceCriteria", [])
        if isinstance(item, dict)
    }
    sequence = criteria.get("acceptance.sequence-integrity", {})
    _require(
        sequence.get("semanticProjectionId") == PROJECTION_ID
        and sequence.get("assessment") == "verified"
        and "evidence.portfolio-tasktime-projection-contract-2026-08-06"
        in sequence.get("evidenceIds", []),
        "acceptance projection verification drifted",
    )
    _require(
        "evidence.plugin-distribution-and-manager-boundary-decision-2026-08-08"
        in sequence.get("evidenceIds", []),
        "acceptance plugin distribution evidence binding drifted",
    )
    for label, text in (("plan", plan_text), ("goal prompt", goal_prompt_text)):
        _require(MARKER in text, f"{label} projection marker drifted")
    normalized_plan = " ".join(plan_text.split()).lower()
    normalized_goal = " ".join(goal_prompt_text.split()).lower()
    normalized_readme = " ".join(readme_text.split()).lower()
    for label, text in (
        ("plan", normalized_plan),
        ("goal prompt", normalized_goal),
        ("README", normalized_readme),
    ):
        _require(
            "portfolio curation" in text
            and "does not require" in text
            and "real task" in text,
            f"{label} global-stop wording drifted",
        )
        _require(
            "plugin-compatible" in text
            and "manager-agnostic" in text
            and "release-not-eligible" in text,
            f"{label} plugin distribution posture drifted",
        )
    normalized_readme_zh = "".join(readme_zh_text.split())
    _require(
        "组合策展不要求" in normalized_readme_zh
        and "真实任务" in normalized_readme_zh
        and "兼容插件" in normalized_readme_zh
        and "管理器无关" in normalized_readme_zh
        and "不具备发布资格" in normalized_readme_zh,
        "Chinese README global-stop wording drifted",
    )
    cc_release = projection.get("sourceBindings", {}).get("ccSwitch", {}).get("release")
    _require(cc_release == "v3.19.2", "CC Switch release binding drifted")
    for label, text in (
        ("plan", plan_text),
        ("goal prompt", goal_prompt_text),
        ("README", readme_text),
        ("Chinese README", readme_zh_text),
    ):
        _require(cc_release in text, f"{label} CC Switch release projection drifted")


def validate_repository_contract(root: Path = ROOT) -> None:
    validate_contract(
        json.loads((root / AUTHORITY_PATH).read_text(encoding="utf-8")),
        json.loads((root / PROJECTION_PATH).read_text(encoding="utf-8")),
        json.loads((root / PLUGIN_DECISION_PATH).read_text(encoding="utf-8")),
        json.loads((root / ACCEPTANCE_PATH).read_text(encoding="utf-8")),
        plan_text=(root / PLAN_PATH).read_text(encoding="utf-8"),
        goal_prompt_text=(root / GOAL_PROMPT_PATH).read_text(encoding="utf-8"),
        readme_text=(root / README_PATH).read_text(encoding="utf-8"),
        readme_zh_text=(root / README_ZH_PATH).read_text(encoding="utf-8"),
    )


def main() -> int:
    validate_repository_contract()
    print("Portfolio/task-time projection contract validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
