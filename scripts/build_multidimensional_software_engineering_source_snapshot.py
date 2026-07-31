#!/usr/bin/env python3
"""Build one deterministic offline software-engineering source snapshot.

Network observation is a separate, non-deterministic input.  This builder
never opens a network connection.  It validates the already-captured
observation against the exact parent source set, merges bounded source use and
limitations from the parent contract, binds all three input files by SHA-256,
sorts records, and adds a canonical manifest digest.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
EVALUATION_CONTRACT_PATH = Path(
    "registry/"
    "multidimensional-software-engineering-evaluation-contract-2026-07-31.json"
)
SNAPSHOT_CONTRACT_PATH = Path(
    "registry/"
    "multidimensional-software-engineering-source-snapshot-contract-2026-07-31.json"
)
OBSERVATION_PATH = Path(
    "registry/"
    "multidimensional-software-engineering-source-observation-2026-07-31.json"
)
SNAPSHOT_PATH = Path(
    "registry/"
    "multidimensional-software-engineering-source-snapshot-2026-07-31.json"
)


class SourceSnapshotError(RuntimeError):
    """Raised when an observation or snapshot contract fails closed."""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise SourceSnapshotError(message)


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def canonical_sha256(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _is_sha256(value: Any) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(character in "0123456789abcdef" for character in value)
    )


def _load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    _require(isinstance(value, dict), f"{path.name} must contain one object")
    return value


def _parse_timestamp(value: Any, *, label: str) -> None:
    _require(isinstance(value, str) and bool(value), f"{label} is missing")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise SourceSnapshotError(f"{label} is invalid") from error
    _require(parsed.tzinfo is not None, f"{label} must include a timezone")


def validate_snapshot_contract(contract: dict[str, Any]) -> None:
    _require(contract.get("schema") == 1, "Snapshot contract schema drifted")
    _require(
        contract.get("status")
        == "calibration-contract-no-automatic-refresh-no-normative-authority",
        "Snapshot contract status drifted",
    )
    _require(
        contract.get("parentEvaluationContract")
        == EVALUATION_CONTRACT_PATH.as_posix(),
        "Snapshot parent contract drifted",
    )
    stages = contract.get("pipeline", [])
    _require(
        [stage.get("stage") for stage in stages]
        == ["observe", "freeze", "verify"],
        "Snapshot pipeline drifted",
    )
    _require(
        stages[0].get("networkAllowed") is True
        and stages[0].get("deterministic") is False
        and all(
            stage.get("networkAllowed") is False
            and stage.get("deterministic") is True
            for stage in stages[1:]
        ),
        "Snapshot observation and offline stages were conflated",
    )
    observation = contract.get("observationContract", {})
    _require(
        observation.get("sourceSetMustExactlyMatchParent") is True
        and observation.get("ownerAndLocatorMustMatchParent") is True
        and observation.get("rightsBoundaryRequired") is True
        and observation.get("mutableUnpinnedMaySupportNormativeClaim") is False
        and observation.get("restrictedIsoUse")
        == "bibliographic-metadata-only",
        "Observation boundary drifted",
    )
    snapshot = contract.get("snapshotContract", {})
    _require(
        snapshot.get("offlineRebuildRequired") is True
        and snapshot.get("rawSourceBodiesRequired") is False
        and snapshot.get("missingRawBodyMustNarrowClaim") is True
        and snapshot.get("independentReviewRequiredForAcceptance") is True,
        "Snapshot rebuild or acceptance boundary drifted",
    )
    claim_boundary = contract.get("claimBoundary", {})
    _require(
        claim_boundary.get("locatorReachabilityIsSourceTruth") is False
        and claim_boundary.get("modelMediatedObservationIsIndependentReceipt")
        is False
        and claim_boundary.get("publicationIdentityIsFullContentIdentity")
        is False
        and claim_boundary.get("snapshotManifestProvesExternalClaimCorrectness")
        is False
        and claim_boundary.get("snapshotMayPreserveWeakOrDisputedBindings")
        is True
        and claim_boundary.get("snapshotMayPromoteHardStandard") is False
        and claim_boundary.get("snapshotMayProveSkillNecessity") is False,
        "Snapshot claim boundary drifted",
    )
    authority = contract.get("authorityBoundary", {})
    _require(
        isinstance(authority, dict)
        and authority
        and all(value is False for value in authority.values()),
        "Snapshot contract expanded authority",
    )


def _validated_parent_sources(
    evaluation_contract: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    rows = evaluation_contract.get("primarySources", [])
    _require(isinstance(rows, list) and rows, "Parent primary sources are missing")
    sources: dict[str, dict[str, Any]] = {}
    for row in rows:
        _require(isinstance(row, dict), "Parent source must be an object")
        source_id = row.get("id")
        _require(
            isinstance(source_id, str)
            and source_id
            and source_id not in sources,
            "Parent source ids must be unique",
        )
        _require(
            isinstance(row.get("owner"), str)
            and bool(row["owner"])
            and str(row.get("locator", "")).startswith("https://")
            and bool(row.get("boundedUse"))
            and bool(row.get("limitation")),
            f"Parent source is incomplete: {source_id}",
        )
        sources[source_id] = row
    return sources


def _validated_observations(
    observation: dict[str, Any],
    *,
    snapshot_contract: dict[str, Any],
    evaluation_contract: dict[str, Any],
) -> list[dict[str, Any]]:
    observation_rules = snapshot_contract["observationContract"]
    _require(
        set(observation) == set(observation_rules["requiredTopLevelFields"]),
        "Observation top-level field set drifted",
    )
    _require(observation.get("schema") == 1, "Observation schema drifted")
    _require(
        observation.get("id")
        == "multidimensional-software-engineering-source-observation-2026-07-31",
        "Observation identity drifted",
    )
    _parse_timestamp(observation.get("observedAt"), label="observedAt")
    _require(
        observation.get("networkAccessUsed") is True
        and observation.get("networkReceiptRetained") is False
        and observation.get("rawBodiesRetained") is False
        and observation.get("modelOrAgentMediated") is True,
        "Observation capture boundary drifted",
    )
    _require(
        observation.get("refreshTrigger")
        in evaluation_contract.get("sourceRefreshAndSnapshotPolicy", {}).get(
            "networkRefreshTriggers",
            [],
        ),
        "Observation refresh trigger is not admitted by the parent contract",
    )
    parent_sources = _validated_parent_sources(evaluation_contract)
    rows = observation.get("sourceObservations")
    _require(isinstance(rows, list) and rows, "Source observations are missing")
    observed: dict[str, dict[str, Any]] = {}
    required_fields = set(observation_rules["requiredSourceFields"])
    allowed_outcomes = set(observation_rules["allowedRetrievalOutcomes"])
    allowed_usability = set(observation_rules["allowedEvidenceUsability"])
    allowed_claims = set(observation_rules["allowedClaimSupportStatuses"])
    allowed_freshness = set(observation_rules["allowedFreshnessClasses"])
    for row in rows:
        _require(
            isinstance(row, dict) and set(row) == required_fields,
            "Source observation field set drifted",
        )
        source_id = row.get("id")
        _require(
            isinstance(source_id, str)
            and source_id in parent_sources
            and source_id not in observed,
            "Source observation id is missing, duplicated, or unknown",
        )
        parent = parent_sources[source_id]
        _require(
            row.get("owner") == parent["owner"]
            and row.get("locator") == parent["locator"],
            f"Source owner or locator drifted: {source_id}",
        )
        _require(
            row.get("retrievalOutcome") in allowed_outcomes,
            f"Source retrieval outcome drifted: {source_id}",
        )
        _require(
            all(
                isinstance(row.get(field), str) and bool(row[field])
                for field in (
                    "identityKind",
                    "identityValue",
                    "publicationState",
                    "contentDigestBasis",
                    "rightsBoundary",
                    "contractStatusCheck",
                    "applicability",
                )
            ),
            f"Source identity or boundary is incomplete: {source_id}",
        )
        _require(
            row.get("evidenceUsability") in allowed_usability
            and row.get("claimSupportStatus") in allowed_claims
            and row.get("freshnessClass") in allowed_freshness,
            f"Source evidence or freshness classification drifted: {source_id}",
        )
        _require(
            isinstance(row.get("contentArchiveAvailable"), bool),
            f"Source archive state is invalid: {source_id}",
        )
        digest = row.get("contentDigest")
        _require(
            digest is None or _is_sha256(digest),
            f"Source content digest is invalid: {source_id}",
        )
        _require(
            not row["contentArchiveAvailable"] or digest is not None,
            f"Archived source lacks a digest: {source_id}",
        )
        _require(
            isinstance(row.get("revalidationTriggers"), list)
            and len(row["revalidationTriggers"]) >= 2
            and all(
                isinstance(trigger, str) and bool(trigger)
                for trigger in row["revalidationTriggers"]
            )
            and isinstance(row.get("conflicts"), list)
            and all(
                isinstance(conflict, str) and bool(conflict)
                for conflict in row["conflicts"]
            ),
            f"Source revalidation or conflict record is incomplete: {source_id}",
        )
        if row["freshnessClass"] == "mutable-unpinned-guidance":
            _require(
                row["claimSupportStatus"] == "bounded-summary-only",
                f"Mutable unpinned source gained normative force: {source_id}",
            )
        if source_id.startswith("iso-"):
            _require(
                row["evidenceUsability"] == "bibliographic-metadata-only"
                and row["claimSupportStatus"] == "bibliographic-only"
                and row["contentArchiveAvailable"] is False
                and row["contentDigest"] is None
                and "AI-use restrictions" in row["rightsBoundary"],
                f"Restricted ISO source exceeded metadata-only use: {source_id}",
            )
        observed[source_id] = row
    _require(
        set(observed) == set(parent_sources),
        "Observation source set does not exactly match the parent contract",
    )
    return [observed[source_id] for source_id in sorted(observed)]


def build_snapshot(
    evaluation_contract: dict[str, Any] | None = None,
    snapshot_contract: dict[str, Any] | None = None,
    observation: dict[str, Any] | None = None,
    *,
    root: Path = ROOT,
) -> dict[str, Any]:
    root = root.resolve()
    evaluation_contract = evaluation_contract or _load(
        root / EVALUATION_CONTRACT_PATH
    )
    snapshot_contract = snapshot_contract or _load(root / SNAPSHOT_CONTRACT_PATH)
    observation = observation or _load(root / OBSERVATION_PATH)
    validate_snapshot_contract(snapshot_contract)
    parent_sources = _validated_parent_sources(evaluation_contract)
    observed_rows = _validated_observations(
        observation,
        snapshot_contract=snapshot_contract,
        evaluation_contract=evaluation_contract,
    )

    sources: list[dict[str, Any]] = []
    for row in observed_rows:
        parent = parent_sources[row["id"]]
        sources.append(
            {
                **row,
                "parentBoundedUseClaim": parent["boundedUse"],
                "parentLimitation": parent["limitation"],
                "snapshotBoundedUse": row["applicability"],
            }
        )

    summary = {
        "sourceCount": len(sources),
        "observedCount": sum(
            row["retrievalOutcome"] == "observed" for row in sources
        ),
        "metadataOnlyCount": sum(
            row["evidenceUsability"] == "bibliographic-metadata-only"
            for row in sources
        ),
        "boundedPublicSummaryCount": sum(
            row["evidenceUsability"] == "bounded-public-summary"
            for row in sources
        ),
        "versionedPublicSpecificationCount": sum(
            row["evidenceUsability"]
            == "versioned-public-specification-summary"
            for row in sources
        ),
        "mutableUnpinnedCount": sum(
            row["freshnessClass"] == "mutable-unpinned-guidance"
            for row in sources
        ),
        "contentArchiveCount": sum(
            row["contentArchiveAvailable"] for row in sources
        ),
        "contentDigestCount": sum(
            row["contentDigest"] is not None for row in sources
        ),
        "conflictSourceCount": sum(bool(row["conflicts"]) for row in sources),
        "partiallyObservedContractStatusCount": sum(
            row["contractStatusCheck"] == "partially-observed"
            for row in sources
        ),
    }
    result = {
        "schema": 1,
        "id": "multidimensional-software-engineering-source-snapshot-2026-07-31",
        "asOf": observation["observedAt"],
        "status": "calibration-snapshot-source-identity-and-usability-only",
        "bindings": {
            "evaluationContractPath": EVALUATION_CONTRACT_PATH.as_posix(),
            "evaluationContractSha256": file_sha256(
                root / EVALUATION_CONTRACT_PATH
            ),
            "snapshotContractPath": SNAPSHOT_CONTRACT_PATH.as_posix(),
            "snapshotContractSha256": file_sha256(root / SNAPSHOT_CONTRACT_PATH),
            "observationPath": OBSERVATION_PATH.as_posix(),
            "observationSha256": file_sha256(root / OBSERVATION_PATH),
        },
        "refreshDecision": {
            "trigger": observation["refreshTrigger"],
            "acquisitionMode": observation["acquisitionMode"],
            "networkAccessUsed": observation["networkAccessUsed"],
            "networkReceiptRetained": observation["networkReceiptRetained"],
            "rawBodiesRetained": observation["rawBodiesRetained"],
            "modelOrAgentMediated": observation["modelOrAgentMediated"],
            "scope": observation["scope"],
        },
        "summary": summary,
        "sources": sources,
        "claimBoundary": {
            "recordsModelMediatedLocatorObservationAtObservedTime": True,
            "provesCurrentLocatorReachabilityAtObservedTime": False,
            "provesNetworkReceipt": False,
            "provesExactExternalContentBytes": False,
            "provesFullNormativeText": False,
            "provesExternalInterpretationCorrect": False,
            "provesParentSourceSetFrozenOffline": True,
            "provesOfflineSnapshotRebuild": True,
            "provesIndependentReview": False,
            "provesEvaluationSkillNecessary": False,
            "authorizesHardStandardOrAcceptance": False,
        },
    }
    result["manifestSha256"] = canonical_sha256(result)
    return result


def _serialized(value: dict[str, Any]) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument(
        "--write",
        action="store_true",
        help="Write the deterministic snapshot to its repository path.",
    )
    mode.add_argument(
        "--check",
        action="store_true",
        help="Fail when the checked-in snapshot differs from a rebuild.",
    )
    arguments = parser.parse_args()
    expected = build_snapshot()
    output_path = ROOT / SNAPSHOT_PATH
    if arguments.write:
        output_path.write_text(_serialized(expected), encoding="utf-8")
        print(f"Wrote {SNAPSHOT_PATH.as_posix()}")
        return 0
    actual = _load(output_path)
    _require(actual == expected, "Checked-in source snapshot is stale")
    print("Software-engineering source snapshot is current.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
