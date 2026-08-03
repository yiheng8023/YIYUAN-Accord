#!/usr/bin/env python3
"""Validate the complete eight-group zero-model effect-oracle suite."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable

try:
    from .evaluate_skill_portfolio_decision_challenge_zero_model_calibration import (
        evaluate_repository_calibration as evaluate_decision_challenge,
    )
    from .evaluate_skill_portfolio_engineering_lifecycle_zero_model_calibration import (
        evaluate_repository_calibration as evaluate_engineering_lifecycle,
    )
    from .evaluate_skill_portfolio_product_discovery_zero_model_calibration import (
        evaluate_repository_calibration as evaluate_product_discovery,
    )
    from .evaluate_skill_portfolio_marketing_writing_zero_model_calibration import (
        evaluate_repository_calibration as evaluate_marketing_writing,
    )
    from .evaluate_skill_portfolio_customer_research_zero_model_calibration import (
        evaluate_repository_calibration as evaluate_customer_research,
    )
    from .evaluate_skill_portfolio_internal_communications_zero_model_calibration import (
        evaluate_repository_calibration as evaluate_internal_communications,
    )
    from .evaluate_skill_portfolio_visual_method_zero_model_calibration import (
        evaluate_repository_calibration as evaluate_visual_method,
    )
    from .evaluate_skill_portfolio_obsidian_format_semantics_zero_model_calibration import (
        evaluate_repository_calibration as evaluate_obsidian_format_semantics,
    )
except ImportError:  # pragma: no cover - direct script execution
    from evaluate_skill_portfolio_decision_challenge_zero_model_calibration import (
        evaluate_repository_calibration as evaluate_decision_challenge,
    )
    from evaluate_skill_portfolio_engineering_lifecycle_zero_model_calibration import (
        evaluate_repository_calibration as evaluate_engineering_lifecycle,
    )
    from evaluate_skill_portfolio_product_discovery_zero_model_calibration import (
        evaluate_repository_calibration as evaluate_product_discovery,
    )
    from evaluate_skill_portfolio_marketing_writing_zero_model_calibration import (
        evaluate_repository_calibration as evaluate_marketing_writing,
    )
    from evaluate_skill_portfolio_customer_research_zero_model_calibration import (
        evaluate_repository_calibration as evaluate_customer_research,
    )
    from evaluate_skill_portfolio_internal_communications_zero_model_calibration import (
        evaluate_repository_calibration as evaluate_internal_communications,
    )
    from evaluate_skill_portfolio_visual_method_zero_model_calibration import (
        evaluate_repository_calibration as evaluate_visual_method,
    )
    from evaluate_skill_portfolio_obsidian_format_semantics_zero_model_calibration import (
        evaluate_repository_calibration as evaluate_obsidian_format_semantics,
    )


ROOT = Path(__file__).resolve().parent.parent
MAPPING_PATH = "registry/skill-portfolio-candidate-demand-mapping-2026-08-03.json"
Evaluator = Callable[[Path], dict[str, Any]]
EXPECTED_GROUPS: list[dict[str, Any]] = [
    {
        "id": "effect.decision-challenge",
        "candidateNames": ["strategy-red-team"],
        "caseCount": 7,
        "faultCaseCount": 6,
        "evaluator": evaluate_decision_challenge,
    },
    {
        "id": "effect.engineering-lifecycle",
        "candidateNames": [
            "ci-cd-and-automation",
            "deprecation-and-migration",
            "documentation-and-adrs",
            "source-driven-development",
        ],
        "caseCount": 7,
        "faultCaseCount": 6,
        "evaluator": evaluate_engineering_lifecycle,
    },
    {
        "id": "effect.product-discovery",
        "candidateNames": ["interview-script", "opportunity-solution-tree"],
        "caseCount": 6,
        "faultCaseCount": 5,
        "evaluator": evaluate_product_discovery,
    },
    {
        "id": "effect.marketing-writing",
        "candidateNames": ["copywriting", "copy-editing"],
        "caseCount": 6,
        "faultCaseCount": 5,
        "evaluator": evaluate_marketing_writing,
    },
    {
        "id": "effect.customer-research",
        "candidateNames": ["customer-research"],
        "caseCount": 6,
        "faultCaseCount": 5,
        "evaluator": evaluate_customer_research,
    },
    {
        "id": "effect.internal-communications",
        "candidateNames": ["internal-comms"],
        "caseCount": 6,
        "faultCaseCount": 5,
        "evaluator": evaluate_internal_communications,
    },
    {
        "id": "effect.visual-method",
        "candidateNames": [
            "baoyu-article-illustrator",
            "baoyu-cover-image",
            "baoyu-infographic",
        ],
        "caseCount": 6,
        "faultCaseCount": 5,
        "evaluator": evaluate_visual_method,
    },
    {
        "id": "effect.obsidian-format-semantics",
        "candidateNames": ["json-canvas", "obsidian-bases", "obsidian-markdown"],
        "caseCount": 6,
        "faultCaseCount": 5,
        "evaluator": evaluate_obsidian_format_semantics,
    },
]


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def validate_suite(root: Path = ROOT) -> dict[str, Any]:
    root = root.resolve()
    mapping = json.loads((root / MAPPING_PATH).read_text(encoding="utf-8"))
    effect_groups = {item["id"]: item for item in mapping.get("effectGroups", [])}
    _require(
        mapping.get("status")
        == "seventeen-static-candidates-mapped-to-domains-scenarios-effects-and-current-comparators-no-execution"
        and set(effect_groups) == {item["id"] for item in EXPECTED_GROUPS},
        "Effect-group mapping set drifted",
    )

    group_reports: list[dict[str, Any]] = []
    candidate_names: list[str] = []
    total_cases = 0
    total_faults = 0
    for expected in EXPECTED_GROUPS:
        mapped = effect_groups[expected["id"]]
        _require(
            mapped.get("candidateNames") == expected["candidateNames"]
            and mapped.get("comparisonOrder")
            == "native-or-current-first-then-one-candidate-arm"
            and mapped.get("compositionArmEligible") is False,
            "Effect-group candidate or comparison mapping drifted",
        )
        report = expected["evaluator"](root)
        claim = report.get("claimBoundary")
        _require(
            report.get("outcome") == "valid-zero-model-effect-calibration"
            and report.get("effectGroupId") == expected["id"]
            and report.get("caseCount") == expected["caseCount"]
            and report.get("faultCaseCount") == expected["faultCaseCount"]
            and report.get("allCasesPassed") is True
            and report.get("formalLiveEvidenceEligible") is False
            and report.get("agentDispatchCount") == 0
            and report.get("modelCallCount") == 0
            and report.get("candidateExecutionCount") == 0
            and isinstance(claim, dict)
            and claim
            and all(value is False for value in claim.values()),
            "Effect-group report or claim boundary drifted",
        )
        candidate_names.extend(expected["candidateNames"])
        total_cases += expected["caseCount"]
        total_faults += expected["faultCaseCount"]
        group_reports.append(
            {
                "effectGroupId": expected["id"],
                "candidateCount": len(expected["candidateNames"]),
                "caseCount": expected["caseCount"],
                "faultCaseCount": expected["faultCaseCount"],
                "status": report["status"],
                "formalLiveEvidenceEligible": False,
            }
        )

    mapped_candidates = [item.get("name") for item in mapping.get("candidateMappings", [])]
    _require(
        len(candidate_names) == 17
        and len(set(candidate_names)) == 17
        and sorted(candidate_names) == sorted(mapped_candidates)
        and total_cases == 50
        and total_faults == 42,
        "Cross-group candidate or case coverage drifted",
    )
    return {
        "status": "zero-model-effect-oracle-suite-calibrated",
        "effectGroupCount": len(group_reports),
        "candidateCount": len(candidate_names),
        "caseCount": total_cases,
        "faultCaseCount": total_faults,
        "allGroupClaimsRemainFalse": True,
        "agentDispatchCount": 0,
        "modelCallCount": 0,
        "candidateExecutionCount": 0,
        "candidateInstallationAuthorized": False,
        "liveBehaviorArmAuthorized": False,
        "candidateBehaviorOrValueProved": False,
        "residualSelfAuthoredGapProved": False,
        "hardStandardPromotionEligible": False,
        "nextGateRequiresSeparateAuthorization": True,
        "groups": group_reports,
    }


def main() -> int:
    print(json.dumps(validate_suite(ROOT), indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
