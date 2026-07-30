#!/usr/bin/env python3
"""Validate the bounded high-impact primary-source claim ledger."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
LEDGER_PATH = (
    "registry/"
    "human-ai-collaboration-high-impact-primary-source-claim-ledger-"
    "2026-07-27.json"
)
MATRIX_PATH = (
    "registry/"
    "human-ai-collaboration-scenario-evidence-matrix-batch-01-"
    "2026-07-24.json"
)
INTAKE_PATH = (
    "registry/user-supplied-human-ai-sdlc-research-intake-2026-07-24.json"
)
DOC_PATH = (
    "docs/strategy/"
    "HUMAN-AI-COLLABORATION-HIGH-IMPACT-PRIMARY-SOURCE-"
    "CLAIM-LEDGER-2026-07-27.md"
)

EXPECTED_URLS = {
    "claim.dora-2025-organizational-amplifier-and-delivery-tension":
        "https://dora.dev/research/2025/dora-report/",
    "claim.stack-overflow-2025-trust-and-rework":
        "https://survey.stackoverflow.co/2025/ai",
    "claim.metr-2025-experienced-oss-productivity-perception-gap":
        (
            "https://metr.org/blog/2025-07-10-early-2025-ai-"
            "experienced-os-dev-study/"
        ),
    "claim.laban-2025-multi-turn-unreliability":
        "https://arxiv.org/abs/2505.06120",
    "claim.shen-tamkin-2026-skill-formation":
        "https://arxiv.org/abs/2601.20245",
}

EXPECTED_BINDINGS = {
    "GEN-RESEARCH-01": [
        "claim.laban-2025-multi-turn-unreliability",
    ],
    "GEN-LEARNING-01": [
        "claim.shen-tamkin-2026-skill-formation",
    ],
    "GEN-ORG-DECISION-01": [
        "claim.dora-2025-organizational-amplifier-and-delivery-tension",
    ],
    "SE-DISCOVERY-REQ-01": [
        "claim.laban-2025-multi-turn-unreliability",
    ],
    "SE-IMPLEMENT-REVIEW-01": [
        "claim.stack-overflow-2025-trust-and-rework",
        "claim.metr-2025-experienced-oss-productivity-perception-gap",
        "claim.laban-2025-multi-turn-unreliability",
        "claim.shen-tamkin-2026-skill-formation",
    ],
    "SE-VERIFY-SECURE-01": [
        "claim.stack-overflow-2025-trust-and-rework",
        "claim.shen-tamkin-2026-skill-formation",
    ],
    "SE-RELEASE-CHANGE-01": [
        "claim.dora-2025-organizational-amplifier-and-delivery-tension",
    ],
    "SE-OPS-INCIDENT-01": [
        "claim.dora-2025-organizational-amplifier-and-delivery-tension",
    ],
    "SE-MGMT-PRACTICE-01": [
        "claim.dora-2025-organizational-amplifier-and-delivery-tension",
        "claim.stack-overflow-2025-trust-and-rework",
        "claim.metr-2025-experienced-oss-productivity-perception-gap",
        "claim.shen-tamkin-2026-skill-formation",
    ],
}

EXPECTED_EVIDENCE_STATES = {
    "GEN-RESEARCH-01": (
        "bounded-synthetic-v2-source-backed-smoke-pass-"
        "no-topology-comparison"
    ),
    "GEN-LEARNING-01": "planned-no-live-domain-evidence",
    "GEN-ORG-DECISION-01": "planned-no-live-domain-evidence",
    "SE-DISCOVERY-REQ-01": (
        "bounded-synthetic-live-agent-evidence-"
        "no-loader-causation-or-live-domain-evidence"
    ),
    "SE-IMPLEMENT-REVIEW-01": (
        "bounded-synthetic-live-agent-evidence-"
        "no-loader-causation-or-live-domain-evidence"
    ),
    "SE-VERIFY-SECURE-01": (
        "zero-model-seeded-fault-calibration-"
        "no-live-agent-or-domain-evidence"
    ),
    "SE-RELEASE-CHANGE-01": "planned-no-live-domain-evidence",
    "SE-OPS-INCIDENT-01": (
        "bounded-synthetic-live-agent-evidence-no-live-domain-evidence"
    ),
    "SE-MGMT-PRACTICE-01": "planned-no-live-domain-evidence",
}


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def _text(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _index(
    items: Any,
    field: str,
    label: str,
) -> dict[str, dict[str, Any]]:
    _require(isinstance(items, list), f"{label} must be a list")
    result: dict[str, dict[str, Any]] = {}
    for item in items:
        _require(isinstance(item, dict), f"{label} entries must be objects")
        key = item.get(field)
        _require(_text(key), f"{label} entry needs {field}")
        _require(key not in result, f"{label} duplicate {field}: {key}")
        result[key] = item
    return result


def _load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    _require(isinstance(value, dict), f"Expected JSON object: {path}")
    return value


def validate_claim_ledger(
    ledger: dict[str, Any],
    *,
    root: Path = ROOT,
    matrix: dict[str, Any] | None = None,
    intake: dict[str, Any] | None = None,
) -> None:
    """Reject source drift, missing qualifiers, or evidence promotion."""
    expected_identity = {
        "schema": 1,
        "id": (
            "human-ai-collaboration-high-impact-primary-source-"
            "claim-ledger-2026-07-27"
        ),
        "date": "2026-07-27",
        "status": (
            "verified-primary-source-reading-bounded-design-input-only"
        ),
    }
    for key, value in expected_identity.items():
        _require(
            ledger.get(key) == value,
            f"Primary-source claim ledger {key} drifted",
        )

    authority = ledger.get("authorityBoundary")
    _require(isinstance(authority, dict), "Authority boundary is missing")
    _require(
        authority.get("owningRepository") == "agent-autonomy-harness"
        and authority.get("publicSourcesOnly") is True
        and authority.get("calibrationState") == "paused-read-only",
        "Primary-source claim ledger authority identity drifted",
    )
    for key in (
        "externalWriteAuthorized",
        "accountConnectionAuthorized",
        "capabilityInstallationAuthorized",
        "runtimeOrGlobalConfigurationMutationAuthorized",
        "calibrationWriteAuthorized",
        "hardStandardPromotionAuthorized",
        "selfAuthoredCapabilityMutationAuthorized",
        "gitCommitOrPushAuthorized",
    ):
        _require(
            authority.get(key) is False,
            f"Primary-source claim ledger authority overclaimed: {key}",
        )

    verification = ledger.get("verificationBoundary")
    _require(
        isinstance(verification, dict)
        and verification.get("sourceIntake") == INTAKE_PATH
        and verification.get("retrievalDate") == "2026-07-27"
        and verification.get("futureSourceDriftRecheckRequired") is True,
        "Primary-source verification boundary drifted",
    )
    for key in (
        "studyResultsIndependentlyReproduced",
        "sourcePageBytesSnapshotted",
        "bodyLinksFromUserReportAcceptedAsEvidence",
        "reportConfidenceLabelsAccepted",
        "wholeReportAccepted",
    ):
        _require(
            verification.get(key) is False,
            f"Primary-source verification was overclaimed: {key}",
        )

    claims = _index(ledger.get("claims"), "id", "Primary-source claims")
    _require(
        set(claims) == set(EXPECTED_URLS),
        "Primary-source claim set drifted",
    )
    for claim_id, claim in claims.items():
        source = claim.get("source")
        _require(
            isinstance(source, dict)
            and source.get("canonicalUrl") == EXPECTED_URLS[claim_id]
            and _text(source.get("title"))
            and _text(source.get("publisherOrAuthors"))
            and _text(source.get("versionOrDate")),
            f"Primary source identity drifted: {claim_id}",
        )
        source_class = source.get("sourceClass")
        _require(
            _text(source_class)
            and "secondary" not in source_class.lower(),
            f"Secondary source entered the repaired ledger: {claim_id}",
        )
        supporting = source.get("supportingPrimaryUrls")
        _require(
            isinstance(supporting, list)
            and supporting
            and all(_text(url) and url.startswith("https://") for url in supporting),
            f"Supporting primary URLs are incomplete: {claim_id}",
        )
        _require(
            claim.get("entailmentStatus")
            == "direct-primary-source-reading-bounded",
            f"Claim entailment boundary drifted: {claim_id}",
        )
        for field in (
            "paraphrasedClaim",
            "quantitativeScope",
            "populationOrSetting",
        ):
            _require(
                _text(claim.get(field)),
                f"Primary-source claim field missing: {claim_id}.{field}",
            )
        limits = claim.get("methodLimits")
        allowed = claim.get("allowedUses")
        forbidden = claim.get("forbiddenInferences")
        _require(
            isinstance(limits, list)
            and len(limits) >= 4
            and all(_text(item) for item in limits),
            f"Method qualifiers are incomplete: {claim_id}",
        )
        _require(
            isinstance(allowed, list)
            and len(allowed) >= 3
            and all(_text(item) for item in allowed),
            f"Allowed uses are incomplete: {claim_id}",
        )
        _require(
            isinstance(forbidden, list)
            and len(forbidden) >= 4
            and all(_text(item) for item in forbidden),
            f"Forbidden inferences are incomplete: {claim_id}",
        )

    backflow = _index(
        ledger.get("matrixBackflow"),
        "scenarioId",
        "Primary-source matrix backflow",
    )
    _require(
        set(backflow) == set(EXPECTED_BINDINGS),
        "Primary-source matrix backflow scenario set drifted",
    )
    for scenario_id, expected_claim_ids in EXPECTED_BINDINGS.items():
        item = backflow[scenario_id]
        _require(
            item.get("claimIds") == expected_claim_ids
            and _text(item.get("designUse")),
            f"Primary-source matrix backflow drifted: {scenario_id}",
        )

    expected_scenarios_by_claim = {
        claim_id: [
            scenario_id
            for scenario_id, claim_ids in EXPECTED_BINDINGS.items()
            if claim_id in claim_ids
        ]
        for claim_id in EXPECTED_URLS
    }
    for claim_id, expected_scenario_ids in expected_scenarios_by_claim.items():
        _require(
            claims[claim_id].get("allowedScenarioIds")
            == expected_scenario_ids,
            f"Claim scenario allowance drifted: {claim_id}",
        )

    claim_boundary = ledger.get("claimBoundary")
    _require(
        isinstance(claim_boundary, dict)
        and len(claim_boundary) >= 9
        and all(value is False for value in claim_boundary.values()),
        "Primary-source claim boundary was promoted",
    )
    decision = ledger.get("decision")
    _require(
        isinstance(decision, dict)
        and decision.get("claimSubsetRepaired") is True
        and decision.get("matrixDesignInputReady") is True
        and decision.get("matrixEvidenceStatePromotionAuthorized") is False
        and decision.get("newUniversalThresholdAuthorized") is False
        and _text(decision.get("nextBoundedResult")),
        "Primary-source claim ledger decision drifted",
    )

    if matrix is None:
        matrix = _load(root / MATRIX_PATH)
    ledger_binding = matrix.get("primarySourceClaimLedger")
    _require(
        isinstance(ledger_binding, dict)
        and ledger_binding.get("path") == LEDGER_PATH
        and ledger_binding.get("claimCount") == len(EXPECTED_URLS)
        and ledger_binding.get("boundScenarioCount")
        == len(EXPECTED_BINDINGS)
        and ledger_binding.get("evidenceStatePromotionAuthorized") is False
        and ledger_binding.get("hardStandardPromotionAuthorized") is False
        and ledger_binding.get("candidatePreferenceOrAdmissionAuthorized")
        is False
        and ledger_binding.get("selfAuthoredCapabilityMutationAuthorized")
        is False,
        "Scenario matrix primary-source ledger binding drifted",
    )
    scenarios = _index(matrix.get("scenarios"), "id", "Scenarios")
    for scenario_id, expected_claim_ids in EXPECTED_BINDINGS.items():
        scenario = scenarios.get(scenario_id)
        _require(
            scenario is not None
            and scenario.get("primarySourceDesignInputIds")
            == expected_claim_ids
            and _text(scenario.get("primarySourceDesignInputBoundary")),
            f"Scenario primary-source design inputs drifted: {scenario_id}",
        )
        _require(
            scenario.get("evidenceState")
            == EXPECTED_EVIDENCE_STATES[scenario_id],
            f"Literature promoted scenario evidence state: {scenario_id}",
        )

    if intake is None:
        intake = _load(root / INTAKE_PATH)
    repair = intake.get("primarySourceRepair")
    _require(
        isinstance(repair, dict)
        and repair.get("ledgerPath") == LEDGER_PATH
        and repair.get("claimCount") == len(EXPECTED_URLS)
        and repair.get("status")
        == "bounded-subset-repaired-design-input-only"
        and repair.get("wholeReportAccepted") is False
        and repair.get("hardStandardPromotionAuthorized") is False
        and repair.get("selfAuthoredCapabilityMutationAuthorized") is False,
        "User-supplied research intake repair binding drifted",
    )

    _require(
        ledger.get("documentation") == DOC_PATH,
        "Primary-source claim ledger documentation path drifted",
    )
    doc_path = root / DOC_PATH
    _require(doc_path.is_file(), "Primary-source claim ledger documentation is missing")
    normalized = " ".join(doc_path.read_text(encoding="utf-8").split())
    for phrase in (
        "bounded design input only",
        "not independent reproduction",
        "not model error rates",
        "cannot be generalized",
        "does not prove host compression behavior",
        "does not prove long-term skill decay",
        "No scenario evidence state is promoted",
    ):
        _require(
            phrase in normalized,
            f"Primary-source claim documentation boundary missing: {phrase}",
        )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args()
    root = args.root.resolve()
    validate_claim_ledger(_load(root / LEDGER_PATH), root=root)
    print("high-impact primary-source claim ledger: valid")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
