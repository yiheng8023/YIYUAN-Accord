#!/usr/bin/env python3
"""Validate the zero-model LongHorizon-Harness interface gap mapping."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
RECORD_PATH = Path(
    "registry/process-loss-longhorizon-harness-interface-gap-mapping-2026-08-07.json"
)
DOCUMENTATION_PATH = Path(
    "docs/strategy/PROCESS-LOSS-LONGHORIZON-HARNESS-INTERFACE-GAP-MAPPING-2026-08-07.md"
)
ACCEPTANCE_PATH = Path("registry/program-acceptance-map.json")
EXTERNAL_ASSESSMENT_PATH = Path(
    "registry/process-loss-longhorizon-harness-static-reuse-assessment-2026-08-07.json"
)
EVIDENCE_ID = (
    "evidence.process-loss-longhorizon-harness-interface-gap-mapping-2026-08-07"
)
SUPPORTED_ACCEPTANCE_ASSESSMENTS = {
    "acceptance.end-to-end-process-fidelity": "partial",
    "acceptance.residual-gap-proof": "partial",
    "acceptance.discovery-reuse-before-authoring": "verified",
}
EXPECTED_SOURCE_BINDINGS = {
    "externalAssessment": str(EXTERNAL_ASSESSMENT_PATH).replace("\\", "/"),
    "baseProcessProtocol": "registry/human-ai-collaboration-process-fidelity-chained-transform-trial-protocol-2026-07-27.json",
    "processProtocolV2Amendment": "registry/human-ai-collaboration-process-fidelity-chained-transform-trial-protocol-v2-amendment-2026-07-27.json",
    "cumulativeLossContract": "registry/human-ai-collaboration-process-fidelity-cumulative-loss-accounting-contract-2026-07-27.json",
    "receiverDeltaLedger": "registry/context-handoff-receiver-delta-ledger-evidence-2026-07-27.json",
    "dispatchGateContract": "registry/human-ai-collaboration-process-fidelity-chained-transform-dispatch-gate-contract-2026-07-27.json",
    "programAcceptanceMap": str(ACCEPTANCE_PATH).replace("\\", "/"),
}
EXPECTED_ROWS = {
    "task-state-and-next-contract": ("partial", "thin-adapter-required"),
    "manager-route": ("present", "direct-reference"),
    "fresh-context-executor": ("present", "direct-reference"),
    "independent-audit-report": ("partial", "thin-adapter-required"),
    "persistent-round-evidence": ("present", "direct-reference"),
    "completion-guard": ("present", "direct-reference"),
    "human-ask-and-blocked-gates": ("partial", "thin-adapter-required"),
    "parent-derived-raw-receipts": ("absent", "harness-retained"),
    "cumulative-process-loss-ledger": ("absent", "harness-retained"),
    "failure-repair-and-resume": ("partial", "thin-adapter-required"),
    "host-owned-permission-enforcement": ("absent", "harness-retained"),
    "backend-adapter-seam": ("partial", "thin-adapter-required"),
}
EXPECTED_COVERAGE_COUNTS = {"present": 4, "partial": 5, "absent": 3}
EXPECTED_DISPOSITION_COUNTS = {
    "direct-reference": 4,
    "thin-adapter-required": 5,
    "harness-retained": 3,
}


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def _nonempty(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def validate_mapping_record(
    record: dict[str, Any],
    *,
    external_assessment: dict[str, Any] | None = None,
    acceptance: dict[str, Any] | None = None,
    root: Path = ROOT,
) -> None:
    _require(
        record.get("schema") == 1
        and record.get("id")
        == "process-loss-longhorizon-harness-interface-gap-mapping-v1"
        and record.get("asOf") == "2026-08-07"
        and record.get("status")
        == "verified-zero-model-interface-gap-mapping-no-execution",
        "LongHorizon interface mapping identity drifted",
    )
    _require(
        record.get("documentation") == str(DOCUMENTATION_PATH).replace("\\", "/")
        and (root / DOCUMENTATION_PATH).is_file(),
        "LongHorizon interface mapping documentation binding drifted",
    )
    _require(
        record.get("sourceBindings") == EXPECTED_SOURCE_BINDINGS
        and all((root / path).is_file() for path in EXPECTED_SOURCE_BINDINGS.values()),
        "LongHorizon interface mapping source bindings drifted",
    )

    external_assessment = external_assessment or json.loads(
        (root / EXTERNAL_ASSESSMENT_PATH).read_text(encoding="utf-8")
    )
    repository = external_assessment.get("sourceSnapshot", {}).get("repository", {})
    _require(
        repository.get("revision")
        == "b49ebf9654c1ee75eaf56dfe9eec1745fddcfa58"
        and repository.get("treeOid")
        == "cf5470d1242e6a092c91a709efeff68c61d36681",
        "LongHorizon interface mapping external source identity drifted",
    )
    selected_paths = {
        item.get("path")
        for item in repository.get("selectedGitObjects", [])
        if isinstance(item, dict)
    }

    contract = record.get("mappingContract", {})
    _require(
        contract.get("mode") == "repository-local-zero-model-static-mapping"
        and contract.get("externalAccessUsed") is False
        and contract.get("thirdPartyCodeAcquired") is False
        and contract.get("thirdPartyCodeExecuted") is False
        and contract.get("modelCallCount") == 0
        and contract.get("hostConfigurationChanged") is False
        and contract.get("consumerWorkspaceAccessed") is False
        and set(contract.get("mappingVocabulary", {}))
        == {
            "present",
            "partial",
            "absent",
            "direct-reference",
            "thin-adapter-required",
            "harness-retained",
        },
        "LongHorizon interface mapping zero-model contract drifted",
    )

    rows = record.get("interfaceRows", [])
    _require(
        isinstance(rows, list)
        and len(rows) == len(EXPECTED_ROWS)
        and len({item.get("interfaceId") for item in rows if isinstance(item, dict)})
        == len(EXPECTED_ROWS),
        "LongHorizon interface mapping row identity drifted",
    )
    indexed = {
        item["interfaceId"]: item
        for item in rows
        if isinstance(item, dict) and _nonempty(item.get("interfaceId"))
    }
    _require(set(indexed) == set(EXPECTED_ROWS), "LongHorizon interface set drifted")
    for interface_id, (coverage, disposition) in EXPECTED_ROWS.items():
        item = indexed[interface_id]
        _require(
            item.get("coverage") == coverage
            and item.get("disposition") == disposition
            and item.get("sourcePaths")
            and set(item["sourcePaths"]).issubset(selected_paths)
            and item.get("harnessRequirements")
            and len(set(item["harnessRequirements"]))
            == len(item["harnessRequirements"])
            and _nonempty(item.get("longHorizonSurface"))
            and _nonempty(item.get("gap")),
            f"LongHorizon interface row drifted: {interface_id}",
        )

    actual_coverage = dict(Counter(item["coverage"] for item in rows))
    actual_dispositions = dict(Counter(item["disposition"] for item in rows))
    summary = record.get("mappingSummary", {})
    _require(
        actual_coverage == EXPECTED_COVERAGE_COUNTS
        and actual_dispositions == EXPECTED_DISPOSITION_COUNTS
        and summary.get("interfaceCount") == 12
        and summary.get("coverageCounts") == EXPECTED_COVERAGE_COUNTS
        and summary.get("dispositionCounts") == EXPECTED_DISPOSITION_COUNTS,
        "LongHorizon interface mapping counts drifted",
    )
    _require(
        set(summary.get("directReferenceInterfaceIds", []))
        == {
            interface_id
            for interface_id, (_, disposition) in EXPECTED_ROWS.items()
            if disposition == "direct-reference"
        }
        and set(summary.get("thinAdapterInterfaceIds", []))
        == {
            interface_id
            for interface_id, (_, disposition) in EXPECTED_ROWS.items()
            if disposition == "thin-adapter-required"
        }
        and set(summary.get("harnessRetainedInterfaceIds", []))
        == {
            interface_id
            for interface_id, (_, disposition) in EXPECTED_ROWS.items()
            if disposition == "harness-retained"
        }
        and len(summary.get("additionalHarnessRetainedScope", [])) == 5
        and summary.get("directCodeReuseAuthorized") is False
        and summary.get("interfaceCompatibilityProved") is False
        and summary.get("operationalCoordinatorReplacementProved") is False,
        "LongHorizon interface disposition summary drifted",
    )

    decision = record.get("decision", {})
    _require(
        decision.get("mappingCompleteForFrozenRevision") is True
        and decision.get("stopSelfAuthoringEquivalentCoordinator") is True
        and decision.get("directAdoptionSupported") is False
        and decision.get("thinAdapterImplementationAuthorized") is False
        and decision.get("upstreamContributionAuthorized") is False
        and decision.get("liveComparisonAuthorized") is False
        and decision.get("realClaudeTaskRequiredAtThisGate") is False
        and _nonempty(decision.get("nextGate")),
        "LongHorizon interface mapping decision drifted",
    )
    authority = record.get("authorityBoundary", {})
    _require(
        authority.get("repositoryLocalMappingAuthorized") is True
        and all(
            authority.get(key) is False
            for key in (
                "thirdPartyAcquisitionAuthorized",
                "installAuthorized",
                "enableAuthorized",
                "executeAuthorized",
                "modelDispatchAuthorized",
                "accountConnectionAuthorized",
                "consumerMutationAuthorized",
                "adapterImplementationAuthorized",
                "upstreamWriteAuthorized",
                "publicationAuthorized",
                "releaseAuthorized",
            )
        ),
        "LongHorizon interface mapping authority boundary drifted",
    )
    claims = record.get("claimBoundary", {})
    _require(
        claims.get("provesFrozenSourceToProtocolMapping") is True
        and claims.get("provesStaticReuseAndGapClassification") is True
        and all(
            claims.get(key) is False
            for key in (
                "provesInterfaceCompatibility",
                "provesSafeExecution",
                "provesRuntimeBehavior",
                "provesIndependentValue",
                "provesCrossHostPortability",
                "provesCrashRecovery",
                "provesResidualGap",
                "provesProductionReadiness",
                "advancesProcessFidelityAcceptance",
                "authorizesInstallationExecutionOrAdoption",
            )
        ),
        "LongHorizon interface mapping claim boundary drifted",
    )

    acceptance = acceptance or json.loads(
        (root / ACCEPTANCE_PATH).read_text(encoding="utf-8")
    )
    criteria = {
        item.get("id"): item
        for item in acceptance.get("acceptanceCriteria", [])
        if isinstance(item, dict)
    }
    evidence = {
        item.get("id"): item
        for item in acceptance.get("evidence", [])
        if isinstance(item, dict)
    }
    _require(
        all(
            criteria.get(acceptance_id, {}).get("assessment") == assessment
            and EVIDENCE_ID
            in criteria.get(acceptance_id, {}).get("evidenceIds", [])
            for acceptance_id, assessment in SUPPORTED_ACCEPTANCE_ASSESSMENTS.items()
        ),
        "LongHorizon interface mapping acceptance boundary drifted",
    )
    evidence_record = evidence.get(EVIDENCE_ID, {})
    _require(
        evidence_record.get("path") == str(RECORD_PATH).replace("\\", "/")
        and evidence_record.get("asOf") == "2026-08-07"
        and set(evidence_record.get("supports", []))
        == set(SUPPORTED_ACCEPTANCE_ASSESSMENTS),
        "LongHorizon interface mapping acceptance evidence drifted",
    )

    documentation = " ".join(
        (root / DOCUMENTATION_PATH).read_text(encoding="utf-8").split()
    )
    for phrase in (
        "four directly useful design references",
        "five surfaces that would require a thin Harness-owned adapter",
        "three requirements that must remain entirely Harness-owned",
        "This mapping does not authorize that adapter",
        "A real Claude task is not required for this zero-model gate",
    ):
        _require(
            phrase in documentation,
            f"LongHorizon interface mapping documentation boundary missing: {phrase}",
        )


def validate_repository_mapping(root: Path = ROOT) -> dict[str, Any]:
    record = json.loads((root / RECORD_PATH).read_text(encoding="utf-8"))
    external_assessment = json.loads(
        (root / EXTERNAL_ASSESSMENT_PATH).read_text(encoding="utf-8")
    )
    acceptance = json.loads((root / ACCEPTANCE_PATH).read_text(encoding="utf-8"))
    validate_mapping_record(
        record,
        external_assessment=external_assessment,
        acceptance=acceptance,
        root=root,
    )
    return record


def main() -> int:
    record = validate_repository_mapping()
    print(
        "PASS: LongHorizon-Harness zero-model interface gap mapping "
        f"({record['mappingSummary']['interfaceCount']} interfaces)."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
