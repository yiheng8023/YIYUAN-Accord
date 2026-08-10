from __future__ import annotations

import copy
import hashlib
import json
import re
from pathlib import Path
from typing import Any

from scripts.harness_decision_packet import strict_json_equal


LEGACY_LOCKS = {
    "acceptance": (
        Path("registry/program-acceptance-map.json"),
        "id",
        "curation-program-acceptance-map-v1",
        "c9d0fb437fb3eae93ffd144a2e3ee418dca90d96e5a266b61d7c7ec3efa6079f",
        "legacy-authority-drift",
    ),
    "programPlan": (
        Path("registry/curation-program-plan.json"),
        "id",
        "curation-program-plan-v1",
        "38bba19b4f4f8471ea7ebaa80765e4110fa169ff892eec3784e3316783a88bd3",
        "legacy-program-plan-drift",
    ),
    "packetFixture": (
        Path("tests/fixtures/harness-decision-packet-gen-research-01.json"),
        "packetId",
        "harness-decision-packet-v1:fixture.gen-research-01",
        "58410f9576fbbc2f006135d97184d29a9996b1eb11abeaf07988a3a5acf4fc22",
        "legacy-packet-fixture-drift",
    ),
    "manifestFixture": (
        Path("tests/fixtures/harness-decision-packet-thirteen-scenario-manifest.json"),
        "id",
        "harness-decision-packet-thirteen-scenario-manifest-v1",
        "ef29ec4de82091dfba3b2e0cfd49c5570cc40410b2beadfd3b5be5bc003176c3",
        "legacy-manifest-fixture-drift",
    ),
}


AUTHORITY_SERIES_ID = "curation-program-acceptance-authority-v2"
TARGET_CRITERION_ID = "acceptance.decision-ready-consumer-projection"
MANIFEST_EVIDENCE_ID = (
    "evidence.harness-decision-packet-thirteen-scenario-manifest-poc-2026-08-09"
)
MANIFEST_EVIDENCE_ROW = {
    "id": MANIFEST_EVIDENCE_ID,
    "path": "registry/harness-decision-packet-thirteen-scenario-manifest-poc-2026-08-09.json",
    "kind": (
        "pure-zero-model-thirteen-scenario-decision-packet-binding-and-atomic-"
        "manifest-mechanism-no-behavior-value-portability-production-release-"
        "or-residual-gap-proof"
    ),
    "asOf": "2026-08-09",
    "supports": [TARGET_CRITERION_ID],
}
_SNAPSHOT_FIELDS = {
    "schema",
    "id",
    "authoritySeriesId",
    "generation",
    "predecessorBinding",
    "programPlanBinding",
    "assessmentVocabulary",
    "objectives",
    "acceptanceCriteria",
    "verifications",
    "evidence",
}
_BUSINESS_FIELDS = (
    "assessmentVocabulary",
    "objectives",
    "acceptanceCriteria",
    "verifications",
    "evidence",
)
_ASSESSMENTS = {"planned", "partial", "verified", "stale", "blocked", "not-applicable"}
_SHA256 = re.compile(r"[0-9a-f]{64}")
ZERO_EXECUTION_COUNTERS = {
    "modelRequestCount": 0,
    "candidateExecutionCount": 0,
    "pluginExecutionCount": 0,
    "installCount": 0,
    "enableCount": 0,
    "accountConnectionCount": 0,
    "managerMutationCount": 0,
    "consumerMutationCount": 0,
    "publicationCount": 0,
    "releaseCount": 0,
    "productionActivationCount": 0,
}
_REHEARSAL_AUTHORIZATION = {
    "rehearsalAuthorized": True,
    "liveMigrationAuthorized": False,
    "assessmentTransitionAuthorized": False,
    "productionActivationAuthorized": False,
}
_ZERO_CLAIM_BOUNDARY = {
    "provesBehavior": False,
    "provesValue": False,
    "provesCrossHostPortability": False,
    "provesProductionReadiness": False,
    "provesReleaseEligibility": False,
    "provesOverallHarnessCompletion": False,
}


def authority_business_projection(document: dict[str, object]) -> dict[str, object]:
    """Return the immutable business surface used for generation deltas."""

    return {field: copy.deepcopy(document.get(field)) for field in _BUSINESS_FIELDS}


def assessment_inventory(document: dict[str, object]) -> dict[str, int]:
    criteria = document.get("acceptanceCriteria")
    if not isinstance(criteria, list):
        raise AcceptanceAuthorityError(
            "acceptance-inventory-count-drift",
            "Acceptance criteria must be an array before inventory can be counted.",
        )
    inventory = {"verified": 0, "partial": 0, "planned": 0}
    for criterion in criteria:
        if not isinstance(criterion, dict) or type(criterion.get("assessment")) is not str:
            raise AcceptanceAuthorityError(
                "acceptance-inventory-count-drift",
                "Acceptance assessments must be JSON strings.",
            )
        assessment = criterion["assessment"]
        if assessment not in _ASSESSMENTS:
            raise AcceptanceAuthorityError(
                "acceptance-inventory-count-drift",
                "Acceptance assessment is outside the frozen vocabulary.",
            )
        if assessment in inventory:
            inventory[assessment] += 1
    return inventory


def _require_binding(binding: object, *, code: str) -> dict[str, object]:
    if not isinstance(binding, dict) or set(binding) != {
        "authoritySchema", "id", "generation", "path", "sha256"
    }:
        raise AcceptanceAuthorityError(code, "Authority binding has an invalid shape.")
    schema = binding["authoritySchema"]
    generation = binding["generation"]
    if type(schema) is not int or schema not in (1, 2):
        raise AcceptanceAuthorityError(code, "Authority binding schema is invalid.")
    if (schema == 1 and generation is not None) or (
        schema == 2 and (type(generation) is not int or generation < 1)
    ):
        raise AcceptanceAuthorityError(code, "Authority binding generation is invalid.")
    if (
        type(binding["id"]) is not str
        or not binding["id"]
        or type(binding["path"]) is not str
        or not binding["path"]
        or type(binding["sha256"]) is not str
        or _SHA256.fullmatch(binding["sha256"]) is None
    ):
        raise AcceptanceAuthorityError(code, "Authority binding fields are invalid.")
    return binding


def _records_by_id(
    document: dict[str, object], key: str, *, code: str
) -> dict[str, dict[str, object]]:
    value = document.get(key)
    if not isinstance(value, list) or not value:
        raise AcceptanceAuthorityError(code, f"{key} must be a non-empty array.")
    records: dict[str, dict[str, object]] = {}
    for row in value:
        if not isinstance(row, dict) or type(row.get("id")) is not str or not row["id"]:
            raise AcceptanceAuthorityError(code, f"{key} records require string ids.")
        if row["id"] in records:
            duplicate_code = "acceptance-evidence-id-duplicate" if key == "evidence" else code
            raise AcceptanceAuthorityError(duplicate_code, f"{key} contains a duplicate id.")
        records[row["id"]] = row
    return records


def _is_nonempty_string(value: object) -> bool:
    return type(value) is str and bool(value)


def _is_string_list(value: object) -> bool:
    return isinstance(value, list) and all(_is_nonempty_string(item) for item in value)


def _validate_snapshot_nested_schema(document: dict[str, object]) -> None:
    """Mirror the declared closed nested v2 schema before relationship checks."""

    vocabulary = document.get("assessmentVocabulary")
    if not isinstance(vocabulary, list) or not vocabulary or not all(
        _is_nonempty_string(value) and value in _ASSESSMENTS for value in vocabulary
    ):
        raise AcceptanceAuthorityError("acceptance-authority-schema-invalid", "Assessment vocabulary is invalid.")
    objectives = document.get("objectives")
    if not isinstance(objectives, list) or not all(
        isinstance(row, dict)
        and set(row) == {"id", "acceptanceIds"}
        and _is_nonempty_string(row["id"])
        and _is_string_list(row["acceptanceIds"])
        for row in objectives
    ):
        raise AcceptanceAuthorityError("acceptance-authority-schema-invalid", "Objective shape is invalid.")
    criteria = document.get("acceptanceCriteria")
    basic = {"id", "statement", "assessment", "verificationIds", "evidenceIds"}
    optional = {
        "currentApplicability": {"currentApplicability"},
        "semanticProjectionId": {"semanticProjectionId"},
        "graduationSubgates": {"graduationSubgates"},
    }
    if not isinstance(criteria, list):
        raise AcceptanceAuthorityError("acceptance-authority-schema-invalid", "Acceptance criteria must be an array.")
    for row in criteria:
        if not isinstance(row, dict) or not (set(row) == basic or any(set(row) == basic | fields for fields in optional.values())):
            raise AcceptanceAuthorityError("acceptance-authority-schema-invalid", "Acceptance criterion shape is invalid.")
        if not all(_is_nonempty_string(row[field]) for field in ("id", "statement")) or type(row["assessment"]) is not str or row["assessment"] not in _ASSESSMENTS or not _is_string_list(row["verificationIds"]) or not _is_string_list(row["evidenceIds"]):
            raise AcceptanceAuthorityError("acceptance-authority-schema-invalid", "Acceptance criterion fields are invalid.")
        if "currentApplicability" in row and not _is_nonempty_string(row["currentApplicability"]):
            raise AcceptanceAuthorityError("acceptance-authority-schema-invalid", "Current applicability is invalid.")
        if "semanticProjectionId" in row and not _is_nonempty_string(row["semanticProjectionId"]):
            raise AcceptanceAuthorityError("acceptance-authority-schema-invalid", "Semantic projection id is invalid.")
        if "graduationSubgates" in row:
            gates = row["graduationSubgates"]
            if not isinstance(gates, list) or not all(
                isinstance(gate, dict)
                and set(gate) == {"id", "requiredEvidence", "promotionBoundary", "status"}
                and all(_is_nonempty_string(gate[field]) for field in gate)
                for gate in gates
            ):
                raise AcceptanceAuthorityError("acceptance-authority-schema-invalid", "Graduation subgate shape is invalid.")
    verifications = document.get("verifications")
    if not isinstance(verifications, list) or not all(
        isinstance(row, dict)
        and set(row) in ({"id", "method", "evidenceRequirement", "expectedResult"}, {"id", "method", "command", "evidenceRequirement", "expectedResult"})
        and all(_is_nonempty_string(value) for value in row.values())
        for row in verifications
    ):
        raise AcceptanceAuthorityError("acceptance-authority-schema-invalid", "Verification shape is invalid.")
    evidence = document.get("evidence")
    if not isinstance(evidence, list) or not all(
        isinstance(row, dict)
        and set(row) == {"id", "path", "kind", "asOf", "supports"}
        and all(_is_nonempty_string(row[field]) for field in ("id", "path", "kind"))
        and type(row["asOf"]) is str and re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", row["asOf"]) is not None
        and _is_string_list(row["supports"])
        for row in evidence
    ):
        raise AcceptanceAuthorityError("acceptance-authority-schema-invalid", "Evidence shape is invalid.")


def _validate_snapshot_relationships(document: dict[str, object]) -> None:
    objectives = _records_by_id(document, "objectives", code="acceptance-structural-migration-overreach")
    criteria = _records_by_id(document, "acceptanceCriteria", code="acceptance-structural-migration-overreach")
    verifications = _records_by_id(document, "verifications", code="acceptance-structural-migration-overreach")
    evidence = _records_by_id(document, "evidence", code="acceptance-evidence-link-asymmetric")

    referenced_criteria: set[str] = set()
    for objective in objectives.values():
        acceptance_ids = objective.get("acceptanceIds")
        if not isinstance(acceptance_ids, list) or not acceptance_ids:
            raise AcceptanceAuthorityError(
                "acceptance-structural-migration-overreach",
                "Each objective requires acceptance ids.",
            )
        for criterion_id in acceptance_ids:
            if type(criterion_id) is not str or criterion_id not in criteria:
                raise AcceptanceAuthorityError(
                    "acceptance-structural-migration-overreach",
                    "An objective references an unknown acceptance criterion.",
                )
            referenced_criteria.add(criterion_id)
    if referenced_criteria != set(criteria):
        raise AcceptanceAuthorityError(
            "acceptance-structural-migration-overreach",
            "Every acceptance criterion must be owned by an objective.",
        )

    referenced_verifications: set[str] = set()
    referenced_evidence: set[str] = set()
    for criterion_id, criterion in criteria.items():
        if type(criterion.get("statement")) is not str or not criterion["statement"]:
            raise AcceptanceAuthorityError(
                "acceptance-structural-migration-overreach",
                "Acceptance criteria require statements.",
            )
        assessment = criterion.get("assessment")
        if type(assessment) is not str or assessment not in _ASSESSMENTS:
            raise AcceptanceAuthorityError(
                "acceptance-inventory-count-drift",
                "Acceptance criterion assessment is invalid.",
            )
        verification_ids = criterion.get("verificationIds")
        evidence_ids = criterion.get("evidenceIds")
        if not isinstance(verification_ids, list) or not verification_ids or not isinstance(evidence_ids, list):
            raise AcceptanceAuthorityError(
                "acceptance-structural-migration-overreach",
                "Acceptance criterion references are invalid.",
            )
        if assessment == "verified" and not evidence_ids:
            raise AcceptanceAuthorityError(
                "acceptance-evidence-link-asymmetric",
                "Verified acceptance criteria require evidence.",
            )
        for verification_id in verification_ids:
            if type(verification_id) is not str or verification_id not in verifications:
                raise AcceptanceAuthorityError(
                    "acceptance-structural-migration-overreach",
                    "Acceptance criterion references unknown verification.",
                )
            referenced_verifications.add(verification_id)
        for evidence_id in evidence_ids:
            if type(evidence_id) is not str or evidence_id not in evidence:
                raise AcceptanceAuthorityError(
                    "acceptance-evidence-link-asymmetric",
                    "Acceptance criterion references unknown evidence.",
                )
            if criterion_id not in evidence[evidence_id].get("supports", []):
                raise AcceptanceAuthorityError(
                    "acceptance-evidence-link-asymmetric",
                    "Evidence does not reciprocally support the criterion.",
                )
            referenced_evidence.add(evidence_id)
    if referenced_verifications != set(verifications):
        raise AcceptanceAuthorityError(
            "acceptance-structural-migration-overreach",
            "Every verification must be referenced by an acceptance criterion.",
        )
    if referenced_evidence != set(evidence):
        raise AcceptanceAuthorityError(
            "acceptance-evidence-link-asymmetric",
            "Every evidence row must be referenced by an acceptance criterion.",
        )
    for evidence_id, evidence_row in evidence.items():
        supports = evidence_row.get("supports")
        if not isinstance(supports, list) or not supports:
            raise AcceptanceAuthorityError(
                "acceptance-evidence-link-asymmetric",
                "Evidence rows require supported criteria.",
            )
        for criterion_id in supports:
            if type(criterion_id) is not str or criterion_id not in criteria or evidence_id not in criteria[criterion_id].get("evidenceIds", []):
                raise AcceptanceAuthorityError(
                    "acceptance-evidence-link-asymmetric",
                    "Evidence support is not reciprocal.",
                )


def _expected_snapshot_id(generation: int) -> str:
    return f"{AUTHORITY_SERIES_ID}-g{generation:06d}"


def _validate_evidence_registration_delta(
    predecessor: dict[str, object], snapshot: dict[str, object]
) -> None:
    before = authority_business_projection(predecessor)
    after = authority_business_projection(snapshot)
    before_evidence = before.pop("evidence")
    after_evidence = after.pop("evidence")
    before_criteria = before.pop("acceptanceCriteria")
    after_criteria = after.pop("acceptanceCriteria")
    if not strict_json_equal(before, after):
        raise AcceptanceAuthorityError(
            "acceptance-evidence-registration-overreach",
            "Evidence registration changed non-evidence business state.",
        )
    if not isinstance(before_evidence, list) or not isinstance(after_evidence, list):
        raise AcceptanceAuthorityError(
            "acceptance-evidence-registration-overreach",
            "Evidence registration requires evidence arrays.",
        )
    if not strict_json_equal(
        after_evidence, [*before_evidence, MANIFEST_EVIDENCE_ROW]
    ):
        manifest_row = next(
            (
                row
                for row in after_evidence
                if isinstance(row, dict) and row.get("id") == MANIFEST_EVIDENCE_ID
            ),
            None,
        )
        if manifest_row is None:
            raise AcceptanceAuthorityError(
                "acceptance-evidence-source-missing",
                "Evidence registration is missing the manifest evidence row.",
            )
        if not strict_json_equal(manifest_row, MANIFEST_EVIDENCE_ROW):
            raise AcceptanceAuthorityError(
                "acceptance-evidence-source-drift",
                "The manifest evidence row is not exact.",
            )
        raise AcceptanceAuthorityError(
            "acceptance-evidence-registration-overreach",
            "Evidence registration changed unrelated evidence state.",
        )
    if not isinstance(before_criteria, list) or not isinstance(after_criteria, list):
        raise AcceptanceAuthorityError(
            "acceptance-evidence-registration-overreach",
            "Evidence registration requires criterion arrays.",
        )
    expected_criteria = copy.deepcopy(before_criteria)
    target = next(
        (row for row in expected_criteria if row.get("id") == TARGET_CRITERION_ID), None
    )
    if target is None:
        raise AcceptanceAuthorityError(
            "acceptance-evidence-registration-overreach",
            "The manifest target criterion is absent.",
        )
    if target.get("assessment") != "partial":
        raise AcceptanceAuthorityError(
            "acceptance-assessment-promotion-forbidden",
            "Evidence registration may not promote its target criterion.",
        )
    target["evidenceIds"] = [*target["evidenceIds"], MANIFEST_EVIDENCE_ID]
    if not strict_json_equal(after_criteria, expected_criteria):
        changed_target = next(
            (row for row in after_criteria if isinstance(row, dict) and row.get("id") == TARGET_CRITERION_ID),
            None,
        )
        if changed_target is not None and changed_target.get("assessment") != "partial":
            raise AcceptanceAuthorityError(
                "acceptance-assessment-promotion-forbidden",
                "Evidence registration may not change assessments.",
            )
        raise AcceptanceAuthorityError(
            "acceptance-evidence-registration-overreach",
            "Evidence registration changed more than its reciprocal link.",
        )


def build_candidate_program_plan_v2(legacy_plan: dict[str, object]) -> dict[str, object]:
    if (
        not isinstance(legacy_plan, dict)
        or not strict_json_equal(legacy_plan.get("schema"), 1)
        or legacy_plan.get("id") != "curation-program-plan-v1"
    ):
        raise AcceptanceAuthorityError(
            "acceptance-structural-migration-overreach",
            "Candidate program plan must start from the frozen v1 plan shape.",
        )
    candidate = copy.deepcopy(legacy_plan)
    candidate["schema"] = 2
    candidate["id"] = "curation-program-plan-v2"
    candidate["acceptanceAuthoritySelector"] = "program-acceptance-authority/current.json"
    candidate.pop("acceptanceMap", None)
    expected = copy.deepcopy(legacy_plan)
    expected["schema"] = 2
    expected["id"] = "curation-program-plan-v2"
    expected["acceptanceAuthoritySelector"] = "program-acceptance-authority/current.json"
    del expected["acceptanceMap"]
    if not strict_json_equal(candidate, expected):
        raise AcceptanceAuthorityError(
            "acceptance-structural-migration-overreach",
            "Candidate program plan changed outside the versioned relationship.",
        )
    return candidate


def build_structural_snapshot_v2(
    legacy_acceptance: dict[str, object],
    *,
    predecessor_binding: dict[str, object],
    program_plan_binding: dict[str, object],
) -> dict[str, object]:
    _require_binding(predecessor_binding, code="acceptance-authority-predecessor-mismatch")
    _require_binding(program_plan_binding, code="acceptance-program-plan-binding-drift")
    if predecessor_binding["authoritySchema"] != 1 or predecessor_binding["generation"] is not None:
        raise AcceptanceAuthorityError(
            "acceptance-authority-predecessor-mismatch",
            "Generation one must bind the v1 predecessor.",
        )
    snapshot = {
        "schema": 2,
        "id": _expected_snapshot_id(1),
        "authoritySeriesId": AUTHORITY_SERIES_ID,
        "generation": 1,
        "predecessorBinding": copy.deepcopy(predecessor_binding),
        "programPlanBinding": copy.deepcopy(program_plan_binding),
        **authority_business_projection(legacy_acceptance),
    }
    validate_authority_snapshot(
        snapshot, predecessor=legacy_acceptance, program_plan_binding=program_plan_binding
    )
    return snapshot


def build_evidence_snapshot_v2(g000001: dict[str, object]) -> dict[str, object]:
    validate_authority_snapshot(g000001)
    existing_evidence = _records_by_id(
        g000001, "evidence", code="acceptance-evidence-registration-overreach"
    )
    if MANIFEST_EVIDENCE_ID in existing_evidence:
        raise AcceptanceAuthorityError(
            "acceptance-evidence-id-duplicate",
            "The manifest evidence already exists in g000001.",
        )
    snapshot = copy.deepcopy(g000001)
    snapshot["id"] = _expected_snapshot_id(2)
    snapshot["generation"] = 2
    snapshot["predecessorBinding"] = binding_for_bytes(
        authority_schema=2,
        authority_id=g000001["id"],
        generation=1,
        path="snapshots/v2/g000001.json",
        data=canonical_file_bytes(g000001),
    )
    snapshot["evidence"].append(copy.deepcopy(MANIFEST_EVIDENCE_ROW))
    target = next(
        row for row in snapshot["acceptanceCriteria"] if row["id"] == TARGET_CRITERION_ID
    )
    target["evidenceIds"].append(MANIFEST_EVIDENCE_ID)
    validate_authority_snapshot(
        snapshot, predecessor=g000001, program_plan_binding=g000001["programPlanBinding"]
    )
    return snapshot


def validate_authority_snapshot(
    snapshot: dict[str, object],
    *,
    predecessor: dict[str, object] | None = None,
    program_plan_binding: dict[str, object] | None = None,
) -> None:
    if not isinstance(snapshot, dict) or set(snapshot) != _SNAPSHOT_FIELDS or type(snapshot.get("schema")) is not int or snapshot["schema"] != 2:
        raise AcceptanceAuthorityError(
            "acceptance-authority-schema-invalid", "Authority snapshot schema is invalid."
        )
    if snapshot.get("authoritySeriesId") != AUTHORITY_SERIES_ID or type(snapshot.get("id")) is not str:
        raise AcceptanceAuthorityError(
            "acceptance-authority-series-invalid", "Authority snapshot series is invalid."
        )
    generation = snapshot.get("generation")
    if type(generation) is not int or generation < 1 or snapshot["id"] != _expected_snapshot_id(generation):
        raise AcceptanceAuthorityError(
            "acceptance-authority-generation-invalid", "Authority snapshot generation is invalid."
        )
    predecessor_binding = _require_binding(
        snapshot.get("predecessorBinding"), code="acceptance-authority-predecessor-mismatch"
    )
    if generation == 1:
        valid_predecessor = (
            predecessor_binding["authoritySchema"] == 1
            and predecessor_binding["generation"] is None
            and predecessor_binding["id"] == LEGACY_LOCKS["acceptance"][2]
            and predecessor_binding["path"]
            == LEGACY_LOCKS["acceptance"][0].as_posix()
            and predecessor_binding["sha256"] == LEGACY_LOCKS["acceptance"][3]
        )
    else:
        valid_predecessor = (
            predecessor_binding["authoritySchema"] == 2
            and predecessor_binding["generation"] == generation - 1
            and predecessor_binding["id"] == _expected_snapshot_id(generation - 1)
        )
    if not valid_predecessor:
        raise AcceptanceAuthorityError(
            "acceptance-authority-predecessor-mismatch", "Authority predecessor does not match generation."
        )
    if generation > 1 and predecessor is not None:
        expected_predecessor = binding_for_bytes(
            authority_schema=2,
            authority_id=predecessor["id"],
            generation=generation - 1,
            path=f"snapshots/v2/g{generation - 1:06d}.json",
            data=canonical_file_bytes(predecessor),
        )
        if not strict_json_equal(predecessor_binding, expected_predecessor):
            raise AcceptanceAuthorityError(
                "acceptance-authority-predecessor-mismatch",
                "Authority predecessor source binding drifted.",
            )
    actual_plan_binding = _require_binding(
        snapshot.get("programPlanBinding"), code="acceptance-program-plan-binding-drift"
    )
    if (
        actual_plan_binding["authoritySchema"] != 2
        or actual_plan_binding["generation"] != 1
        or actual_plan_binding["id"] != "curation-program-plan-v2"
        or actual_plan_binding["path"] != "curation-program-plan-v2.json"
        or (program_plan_binding is not None and not strict_json_equal(actual_plan_binding, program_plan_binding))
    ):
        raise AcceptanceAuthorityError(
            "acceptance-program-plan-binding-drift", "Authority program-plan binding drifted."
        )
    _validate_snapshot_nested_schema(snapshot)
    _validate_snapshot_relationships(snapshot)
    if len(snapshot["acceptanceCriteria"]) != 61 or assessment_inventory(snapshot) != {
        "verified": 46,
        "partial": 15,
        "planned": 0,
    }:
        raise AcceptanceAuthorityError(
            "acceptance-inventory-count-drift", "Authority assessment inventory drifted."
        )
    evidence = _records_by_id(
        snapshot, "evidence", code="acceptance-evidence-registration-overreach"
    )
    if generation == 1:
        if len(evidence) != 152 or MANIFEST_EVIDENCE_ID in evidence:
            raise AcceptanceAuthorityError(
                "acceptance-structural-migration-overreach",
                "Structural migration must retain the frozen evidence inventory.",
            )
    elif generation == 2:
        manifest = evidence.get(MANIFEST_EVIDENCE_ID)
        if manifest is None:
            raise AcceptanceAuthorityError(
                "acceptance-evidence-source-missing",
                "Evidence registration requires the manifest evidence row.",
            )
        if not strict_json_equal(manifest, MANIFEST_EVIDENCE_ROW):
            raise AcceptanceAuthorityError(
                "acceptance-evidence-source-drift",
                "Manifest evidence row drifted from its exact source binding.",
            )
        target = _records_by_id(
            snapshot, "acceptanceCriteria", code="acceptance-evidence-registration-overreach"
        ).get(TARGET_CRITERION_ID)
        if target is None or target.get("assessment") != "partial":
            raise AcceptanceAuthorityError(
                "acceptance-assessment-promotion-forbidden",
                "Evidence registration may not promote the target criterion.",
            )
        if target.get("evidenceIds", []).count(MANIFEST_EVIDENCE_ID) != 1:
            raise AcceptanceAuthorityError(
                "acceptance-evidence-link-asymmetric",
                "Manifest evidence must have one reciprocal target link.",
            )
        if len(evidence) != 153:
            raise AcceptanceAuthorityError(
                "acceptance-evidence-registration-overreach",
                "Evidence registration may add exactly one evidence row.",
            )
    if predecessor is not None:
        if generation == 1:
            if not strict_json_equal(
                authority_business_projection(snapshot), authority_business_projection(predecessor)
            ):
                raise AcceptanceAuthorityError(
                    "acceptance-structural-migration-overreach",
                    "Structural migration changed business semantics.",
                )
        elif generation == 2:
            _validate_evidence_registration_delta(predecessor, snapshot)


class AcceptanceAuthorityError(ValueError):
    def __init__(self, code: str, message: str, *, path: str | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.path = path


def canonical_file_bytes(value: object) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        .encode("utf-8")
        + b"\n"
    )


def file_sha256(root: Path, relative: Path) -> str:
    return hashlib.sha256((root / relative).read_bytes()).hexdigest()


def binding_for_bytes(
    *,
    authority_schema: int,
    authority_id: str,
    generation: int | None,
    path: str,
    data: bytes,
) -> dict[str, object]:
    if type(authority_schema) is not int:
        raise AcceptanceAuthorityError(
            "acceptance-authority-schema-invalid",
            "Authority schema must be an integer.",
            path=path,
        )
    if authority_schema not in (1, 2):
        raise AcceptanceAuthorityError(
            "acceptance-authority-schema-invalid",
            "Authority schema must be version 1 or 2.",
            path=path,
        )
    if (authority_schema == 1 and generation is not None) or (
        authority_schema != 1 and (type(generation) is not int or generation < 1)
    ):
        raise AcceptanceAuthorityError(
            "acceptance-authority-generation-invalid",
            "Only legacy v1 bindings may have a null generation.",
            path=path,
        )
    return {
        "authoritySchema": authority_schema,
        "id": authority_id,
        "generation": generation,
        "path": path,
        "sha256": hashlib.sha256(data).hexdigest(),
    }


def validate_legacy_locks(
    root: Path,
) -> dict[str, dict[str, Any]]:
    locks: dict[str, dict[str, Any]] = {}
    for name, (
        relative,
        identity_field,
        expected_identity,
        locked_sha256,
        error_code,
    ) in LEGACY_LOCKS.items():
        actual_sha256 = file_sha256(root, relative)
        path = relative.as_posix()
        if not strict_json_equal(actual_sha256, locked_sha256):
            raise AcceptanceAuthorityError(
                error_code,
                "Legacy authority bytes do not match the locked SHA-256.",
                path=path,
            )
        document = json.loads((root / relative).read_bytes())
        if not isinstance(document, dict) or not strict_json_equal(
            document.get(identity_field), expected_identity
        ):
            raise AcceptanceAuthorityError(
                error_code,
                "Legacy authority identity does not match the lock.",
                path=path,
            )
        locks[name] = {
            "id": expected_identity,
            "path": path,
            "sha256": actual_sha256,
        }
    return locks


def build_transition_receipt(
    transaction_type: str,
    *,
    from_snapshot_binding: dict[str, object],
    to_snapshot_binding: dict[str, object],
    from_program_plan_binding: dict[str, object],
    to_program_plan_binding: dict[str, object],
    from_document: dict[str, object],
    to_document: dict[str, object],
) -> dict[str, object]:
    """Build one immutable, rehearsal-only receipt for an allowed transition."""

    if type(transaction_type) is not str or transaction_type not in {"structural-migration", "evidence-registration"}:
        raise AcceptanceAuthorityError(
            "acceptance-transition-type-mismatch",
            "This builder accepts only forward rehearsal transaction types.",
        )
    from_snapshot = _require_binding(
        from_snapshot_binding, code="acceptance-transition-receipt-invalid"
    )
    to_snapshot = _require_binding(
        to_snapshot_binding, code="acceptance-transition-receipt-invalid"
    )
    from_plan = _require_binding(
        from_program_plan_binding, code="acceptance-transition-receipt-invalid"
    )
    to_plan = _require_binding(
        to_program_plan_binding, code="acceptance-transition-receipt-invalid"
    )
    delta = _receipt_delta(transaction_type, from_document, to_document)
    receipt = {
        "schema": 1,
        "id": _receipt_id(transaction_type, from_snapshot, to_snapshot),
        "authoritySeriesId": AUTHORITY_SERIES_ID,
        "transactionType": transaction_type,
        "fromSnapshotBinding": copy.deepcopy(from_snapshot),
        "toSnapshotBinding": copy.deepcopy(to_snapshot),
        "fromProgramPlanBinding": copy.deepcopy(from_plan),
        "toProgramPlanBinding": copy.deepcopy(to_plan),
        "delta": delta,
        "invariants": _receipt_invariants(to_document),
        "authorizationBoundary": copy.deepcopy(_REHEARSAL_AUTHORIZATION),
        "executionCounters": copy.deepcopy(ZERO_EXECUTION_COUNTERS),
        "claimBoundary": copy.deepcopy(_ZERO_CLAIM_BOUNDARY),
    }
    validate_transition_receipt(receipt, from_document=from_document, to_document=to_document)
    return receipt


def _receipt_id(
    transaction_type: str,
    from_snapshot_binding: dict[str, object],
    to_snapshot_binding: dict[str, object],
) -> str:
    from_generation = from_snapshot_binding.get("generation")
    from_label = "g000000" if from_generation is None else f"g{from_generation:06d}"
    to_generation = to_snapshot_binding.get("generation")
    if type(to_generation) is not int:
        raise AcceptanceAuthorityError(
            "acceptance-transition-receipt-invalid",
            "Transition receipt target requires a numeric generation.",
        )
    return f"{AUTHORITY_SERIES_ID}-{from_label}-to-g{to_generation:06d}-{transaction_type}"


def _receipt_invariants(document: dict[str, object]) -> dict[str, object]:
    return {
        "authoritySeriesPreserved": True,
        "generationStepValid": True,
        "immutableHistoryPreserved": True,
        "programPlanBindingsValid": True,
        "acceptanceInventory": assessment_inventory(document),
    }


def _empty_receipt_delta(*, selector_target_generation: int | None = None) -> dict[str, object]:
    return {
        "evidenceAdded": [],
        "evidenceRemoved": [],
        "criterionEvidenceLinksAdded": [],
        "criterionEvidenceLinksRemoved": [],
        "assessmentsChanged": [],
        "selectorTargetGeneration": selector_target_generation,
    }


def _receipt_delta(
    transaction_type: str, from_document: dict[str, object], to_document: dict[str, object]
) -> dict[str, object]:
    if transaction_type == "structural-migration":
        if not strict_json_equal(
            authority_business_projection(from_document), authority_business_projection(to_document)
        ):
            raise AcceptanceAuthorityError(
                "acceptance-structural-migration-overreach",
                "Structural migration must have an empty business delta.",
            )
        return _empty_receipt_delta()

    _validate_evidence_registration_delta(from_document, to_document)
    return {
        "evidenceAdded": [MANIFEST_EVIDENCE_ID],
        "evidenceRemoved": [],
        "criterionEvidenceLinksAdded": [
            {"criterionId": TARGET_CRITERION_ID, "evidenceId": MANIFEST_EVIDENCE_ID}
        ],
        "criterionEvidenceLinksRemoved": [],
        "assessmentsChanged": [],
        "selectorTargetGeneration": None,
    }


def _require_exact_zero_counters(counters: object) -> None:
    if not strict_json_equal(counters, ZERO_EXECUTION_COUNTERS):
        raise AcceptanceAuthorityError(
            "acceptance-side-effect-counter-nonzero",
            "Rehearsal execution counters must be exact JSON zeroes.",
        )


def _require_rehearsal_boundaries(receipt: dict[str, object]) -> None:
    if not strict_json_equal(receipt.get("authorizationBoundary"), _REHEARSAL_AUTHORIZATION):
        raise AcceptanceAuthorityError(
            "acceptance-activation-not-authorized",
            "Transition receipt exceeds the rehearsal authorization boundary.",
        )
    if not strict_json_equal(receipt.get("claimBoundary"), _ZERO_CLAIM_BOUNDARY):
        raise AcceptanceAuthorityError(
            "acceptance-transition-receipt-invalid",
            "Transition receipt claim boundary is invalid.",
        )
    _require_exact_zero_counters(receipt.get("executionCounters"))


def validate_transition_receipt(
    receipt: dict[str, object],
    *,
    from_document: dict[str, object],
    to_document: dict[str, object],
) -> None:
    """Validate a receipt against the two real authority documents it binds."""

    required_fields = {
        "schema", "id", "authoritySeriesId", "transactionType", "fromSnapshotBinding",
        "toSnapshotBinding", "fromProgramPlanBinding", "toProgramPlanBinding", "delta",
        "invariants", "authorizationBoundary", "executionCounters", "claimBoundary",
    }
    if (
        not isinstance(receipt, dict)
        or set(receipt) != required_fields
        or type(receipt.get("schema")) is not int
        or receipt["schema"] != 1
        or type(receipt.get("id")) is not str
        or not receipt["id"]
        or receipt.get("authoritySeriesId") != AUTHORITY_SERIES_ID
    ):
        raise AcceptanceAuthorityError(
            "acceptance-transition-receipt-invalid", "Transition receipt shape is invalid."
        )
    transaction_type = receipt.get("transactionType")
    if type(transaction_type) is not str or transaction_type not in {"structural-migration", "evidence-registration", "rollback"}:
        raise AcceptanceAuthorityError(
            "acceptance-transition-type-mismatch", "Transition type is not recognized."
        )
    from_binding = _require_binding(
        receipt.get("fromSnapshotBinding"), code="acceptance-transition-receipt-invalid"
    )
    to_binding = _require_binding(
        receipt.get("toSnapshotBinding"), code="acceptance-transition-receipt-invalid"
    )
    _require_binding(receipt.get("fromProgramPlanBinding"), code="acceptance-transition-receipt-invalid")
    _require_binding(receipt.get("toProgramPlanBinding"), code="acceptance-transition-receipt-invalid")
    if (
        from_binding.get("id") != from_document.get("id")
        or to_binding.get("id") != to_document.get("id")
        or from_binding.get("authoritySchema") != from_document.get("schema")
        or to_binding.get("authoritySchema") != to_document.get("schema")
    ):
        raise AcceptanceAuthorityError(
            "acceptance-transition-receipt-invalid", "Receipt bindings do not name their documents."
        )
    _require_rehearsal_boundaries(receipt)
    expected_invariants = _receipt_invariants(to_document)
    if not strict_json_equal(receipt.get("invariants"), expected_invariants):
        raise AcceptanceAuthorityError(
            "acceptance-transition-receipt-invalid", "Receipt invariants are invalid."
        )
    if transaction_type == "rollback":
        _validate_rollback_receipt(receipt, from_document, to_document)
        return
    if not strict_json_equal(to_document.get("predecessorBinding"), from_binding):
        raise AcceptanceAuthorityError(
            "acceptance-transition-chain-broken",
            "Receipt source is not the exact successor snapshot predecessor binding.",
        )
    from_generation = from_binding.get("generation")
    to_generation = to_binding.get("generation")
    expected_from = None if transaction_type == "structural-migration" else 1
    if (
        type(to_generation) is not int
        or to_generation < 1
        or from_generation != expected_from
        or to_generation != (1 if transaction_type == "structural-migration" else 2)
    ):
        raise AcceptanceAuthorityError(
            "acceptance-transition-chain-broken", "Receipt generation step is invalid."
        )
    expected_delta = _receipt_delta(transaction_type, from_document, to_document)
    if not strict_json_equal(receipt.get("delta"), expected_delta):
        if transaction_type == "evidence-registration" and isinstance(receipt.get("delta"), dict):
            changes = receipt["delta"].get("assessmentsChanged")
            if changes not in ([], None):
                raise AcceptanceAuthorityError(
                    "acceptance-assessment-promotion-forbidden",
                    "Evidence registration may not claim assessment transition.",
                )
        raise AcceptanceAuthorityError(
            "acceptance-transition-receipt-invalid", "Receipt delta is not exact."
        )


def _validate_rollback_receipt(
    receipt: dict[str, object], from_document: dict[str, object], to_document: dict[str, object]
) -> None:
    from_generation = receipt["fromSnapshotBinding"]["generation"]
    to_generation = receipt["toSnapshotBinding"]["generation"]
    if (
        type(from_generation) is not int
        or type(to_generation) is not int
        or to_generation >= from_generation
        or from_document.get("authoritySeriesId") != AUTHORITY_SERIES_ID
        or to_document.get("authoritySeriesId") != AUTHORITY_SERIES_ID
    ):
        raise AcceptanceAuthorityError(
            "acceptance-rollback-target-not-ancestor", "Rollback target is not an earlier authority state."
        )
    if not strict_json_equal(
        receipt.get("delta"), _empty_receipt_delta(selector_target_generation=to_generation)
    ):
        raise AcceptanceAuthorityError(
            "acceptance-rollback-receipt-invalid", "Rollback may only move the selector."
        )


def build_rollback_receipt(
    *,
    from_snapshot_binding: dict[str, object],
    to_snapshot_binding: dict[str, object],
    active_program_plan_binding: dict[str, object],
    ancestor_bindings: list[dict[str, object]],
) -> dict[str, object]:
    """Build a selector-only rollback receipt to one explicit immutable ancestor."""

    from_binding = _require_binding(
        from_snapshot_binding, code="acceptance-rollback-receipt-invalid"
    )
    to_binding = _require_binding(to_snapshot_binding, code="acceptance-rollback-receipt-invalid")
    plan_binding = _require_binding(
        active_program_plan_binding, code="acceptance-rollback-receipt-invalid"
    )
    if (
        from_binding["authoritySchema"] != 2
        or to_binding["authoritySchema"] != 2
        or plan_binding["authoritySchema"] != 2
        or not isinstance(ancestor_bindings, list)
        or not any(strict_json_equal(to_binding, candidate) for candidate in ancestor_bindings)
        or type(from_binding["generation"]) is not int
        or type(to_binding["generation"]) is not int
        or to_binding["generation"] >= from_binding["generation"]
    ):
        raise AcceptanceAuthorityError(
            "acceptance-rollback-target-not-ancestor", "Rollback target is not a declared ancestor."
        )
    return {
        "schema": 1,
        "id": _receipt_id("rollback", from_binding, to_binding),
        "authoritySeriesId": AUTHORITY_SERIES_ID,
        "transactionType": "rollback",
        "fromSnapshotBinding": copy.deepcopy(from_binding),
        "toSnapshotBinding": copy.deepcopy(to_binding),
        "fromProgramPlanBinding": copy.deepcopy(plan_binding),
        "toProgramPlanBinding": copy.deepcopy(plan_binding),
        "delta": _empty_receipt_delta(selector_target_generation=to_binding["generation"]),
        "invariants": {
            "authoritySeriesPreserved": True,
            "generationStepValid": True,
            "immutableHistoryPreserved": True,
            "programPlanBindingsValid": True,
            "acceptanceInventory": {"verified": 46, "partial": 15, "planned": 0},
        },
        "authorizationBoundary": copy.deepcopy(_REHEARSAL_AUTHORIZATION),
        "executionCounters": copy.deepcopy(ZERO_EXECUTION_COUNTERS),
        "claimBoundary": copy.deepcopy(_ZERO_CLAIM_BOUNDARY),
    }


def build_selector(
    *,
    snapshot_binding: dict[str, object],
    transition_binding: dict[str, object],
    program_plan_binding: dict[str, object],
) -> dict[str, object]:
    """Build a non-activating selector for an already validated candidate tree."""

    snapshot = _require_binding(snapshot_binding, code="acceptance-selector-target-invalid")
    transition = _require_binding(transition_binding, code="acceptance-selector-target-invalid")
    plan = _require_binding(program_plan_binding, code="acceptance-selector-target-invalid")
    if (
        snapshot["authoritySchema"] != 2
        or transition["authoritySchema"] != 1
        or transition["generation"] is not None
        or plan["authoritySchema"] != 2
        or plan["generation"] != 1
    ):
        raise AcceptanceAuthorityError(
            "acceptance-selector-target-invalid", "Selector bindings have invalid authority roles."
        )
    return {
        "schema": 1,
        "id": "curation-program-acceptance-current-selector-v1",
        "authoritySeriesId": AUTHORITY_SERIES_ID,
        "selectionMode": "rehearsal-candidate",
        "activeSnapshotBinding": copy.deepcopy(snapshot),
        "activeTransitionBinding": copy.deepcopy(transition),
        "programPlanBinding": copy.deepcopy(plan),
        "activationAuthorized": False,
        "executionCounters": copy.deepcopy(ZERO_EXECUTION_COUNTERS),
    }


def _safe_relative_path(root: Path, value: object, *, code: str) -> Path:
    if type(value) is not str or not value:
        raise AcceptanceAuthorityError(code, "Authority path must be a non-empty relative string.")
    candidate = Path(value)
    if candidate.is_absolute() or any(part == ".." for part in candidate.parts):
        raise AcceptanceAuthorityError(code, "Authority path escapes the supplied root.", path=value)
    resolved_root = root.resolve()
    resolved = (resolved_root / candidate).resolve()
    try:
        resolved.relative_to(resolved_root)
    except ValueError as error:
        raise AcceptanceAuthorityError(code, "Authority path escapes the supplied root.", path=value) from error
    return resolved


def _load_bound_document(root: Path, binding: object, *, code: str) -> dict[str, object]:
    normalized = _require_binding(binding, code=code)
    path = _safe_relative_path(root, normalized["path"], code=code)
    try:
        data = path.read_bytes()
    except OSError as error:
        raise AcceptanceAuthorityError(code, "Bound authority document cannot be read.") from error
    try:
        document = json.loads(data)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise AcceptanceAuthorityError(code, "Bound authority document cannot be read.") from error
    if (
        not isinstance(document, dict)
        or not strict_json_equal(hashlib.sha256(data).hexdigest(), normalized["sha256"])
        or document.get("id") != normalized["id"]
        or type(document.get("schema")) is not int
        or document["schema"] != normalized["authoritySchema"]
    ):
        raise AcceptanceAuthorityError(code, "Bound authority document drifted.", path=normalized["path"])
    if normalized["authoritySchema"] == 2 and "generation" in document:
        if not strict_json_equal(document["generation"], normalized["generation"]):
            raise AcceptanceAuthorityError(code, "Bound authority generation drifted.", path=normalized["path"])
    return document


def _validate_selector(selector: object) -> dict[str, object]:
    required = {
        "schema", "id", "authoritySeriesId", "selectionMode", "activeSnapshotBinding",
        "activeTransitionBinding", "programPlanBinding", "activationAuthorized", "executionCounters",
    }
    if (
        not isinstance(selector, dict)
        or set(selector) != required
        or type(selector.get("schema")) is not int
        or selector["schema"] != 1
        or selector.get("id") != "curation-program-acceptance-current-selector-v1"
        or selector.get("authoritySeriesId") != AUTHORITY_SERIES_ID
        or selector.get("selectionMode") != "rehearsal-candidate"
    ):
        raise AcceptanceAuthorityError("acceptance-selector-target-invalid", "Selector shape is invalid.")
    if type(selector.get("activationAuthorized")) is not bool or selector["activationAuthorized"]:
        raise AcceptanceAuthorityError(
            "acceptance-activation-not-authorized", "Selector activation is not authorized."
        )
    _require_exact_zero_counters(selector.get("executionCounters"))
    snapshot = _require_binding(
        selector.get("activeSnapshotBinding"), code="acceptance-selector-target-invalid"
    )
    transition = _require_binding(
        selector.get("activeTransitionBinding"), code="acceptance-selector-target-invalid"
    )
    plan = _require_binding(selector.get("programPlanBinding"), code="acceptance-selector-target-invalid")
    if (
        snapshot["authoritySchema"] != 2
        or transition["authoritySchema"] != 1
        or transition["generation"] is not None
        or plan["authoritySchema"] != 2
        or plan["generation"] != 1
    ):
        raise AcceptanceAuthorityError(
            "acceptance-selector-target-invalid", "Selector target binding roles are invalid."
        )
    return selector


def _validate_program_plan_document(
    root: Path,
    document: dict[str, object],
    binding: dict[str, object],
    authority_binding: dict[str, object],
) -> None:
    if binding["authoritySchema"] == 1:
        locks = validate_legacy_locks(root)
        expected_binding = {
            **locks["programPlan"],
            "authoritySchema": 1,
            "generation": None,
        }
        if (
            not strict_json_equal(binding, expected_binding)
            or document.get("id") != "curation-program-plan-v1"
            or document.get("acceptanceMap") != authority_binding["path"]
        ):
            raise AcceptanceAuthorityError(
                "acceptance-program-plan-binding-drift",
                "Historical program plan does not bind the supplied authority path.",
            )
        return
    locks = validate_legacy_locks(root)
    legacy_binding = {
        **locks["programPlan"],
        "authoritySchema": 1,
        "generation": None,
    }
    legacy_plan = _load_bound_document(
        root, legacy_binding, code="acceptance-program-plan-binding-drift"
    )
    expected_candidate = build_candidate_program_plan_v2(legacy_plan)
    if (
        binding["authoritySchema"] != 2
        or binding["generation"] != 1
        or not strict_json_equal(document, expected_candidate)
    ):
        raise AcceptanceAuthorityError(
            "acceptance-program-plan-binding-drift",
            "Candidate program plan relationship is invalid.",
        )


def _receipt_relative_path(
    from_binding: dict[str, object], to_binding: dict[str, object]
) -> str:
    from_generation = from_binding["generation"]
    to_generation = to_binding["generation"]
    if type(to_generation) is not int or (
        from_generation is not None and type(from_generation) is not int
    ):
        raise AcceptanceAuthorityError(
            "acceptance-transition-chain-broken", "Receipt generation is not a strict JSON integer."
        )
    from_label = "g000000" if from_generation is None else f"g{from_generation:06d}"
    return f"transitions/{from_label}-to-g{to_generation:06d}.json"


def _load_introducing_receipt(
    root: Path, from_binding: dict[str, object], to_binding: dict[str, object]
) -> dict[str, object]:
    transaction_type = (
        "structural-migration" if from_binding["authoritySchema"] == 1 else "evidence-registration"
    )
    relative = _receipt_relative_path(from_binding, to_binding)
    path = _safe_relative_path(root, relative, code="acceptance-transition-chain-broken")
    try:
        data = path.read_bytes()
    except OSError as error:
        raise AcceptanceAuthorityError(
            "acceptance-transition-chain-broken", "Expected introducing receipt is absent."
        ) from error
    binding = binding_for_bytes(
        authority_schema=1,
        authority_id=_receipt_id(transaction_type, from_binding, to_binding),
        generation=None,
        path=relative,
        data=data,
    )
    receipt = _load_bound_document(root, binding, code="acceptance-transition-chain-broken")
    _reject_duplicate_introducing_receipts(root, relative, to_binding)
    return receipt


def _reject_duplicate_introducing_receipts(
    root: Path, canonical_relative: str, to_binding: dict[str, object]
) -> None:
    transitions = _safe_relative_path(root, "transitions", code="acceptance-transition-chain-broken")
    lexical_root = root.resolve()
    canonical_path = lexical_root / Path(canonical_relative)
    for candidate in transitions.glob("*.json"):
        if candidate.absolute() == canonical_path.absolute():
            continue
        try:
            resolved_candidate = candidate.resolve(strict=True)
            resolved_candidate.relative_to(lexical_root)
        except (OSError, RuntimeError, ValueError) as error:
            raise AcceptanceAuthorityError(
                "acceptance-transition-chain-broken",
                "Candidate receipt child escapes or cannot resolve inside the candidate root.",
                path=str(candidate),
            ) from error
        try:
            alternate = json.loads(candidate.read_bytes())
        except (OSError, json.JSONDecodeError):
            continue
        if (
            isinstance(alternate, dict)
            and alternate.get("transactionType") != "rollback"
            and strict_json_equal(alternate.get("toSnapshotBinding"), to_binding)
        ):
            raise AcceptanceAuthorityError(
                "acceptance-transition-chain-broken",
                "Authority target has more than one introducing receipt.",
            )


def _require_exact_rollback_ancestor(
    root: Path, from_binding: dict[str, object], to_binding: dict[str, object]
) -> None:
    current = from_binding
    seen: set[str] = set()
    while True:
        token = current["sha256"]
        if token in seen:
            raise AcceptanceAuthorityError(
                "acceptance-rollback-target-not-ancestor", "Rollback ancestry contains a cycle."
            )
        seen.add(token)
        if strict_json_equal(current, to_binding):
            return
        if current["authoritySchema"] != 2:
            break
        document = _load_bound_document(
            root, current, code="acceptance-rollback-target-not-ancestor"
        )
        current = _require_binding(
            document.get("predecessorBinding"), code="acceptance-rollback-target-not-ancestor"
        )
    raise AcceptanceAuthorityError(
        "acceptance-rollback-target-not-ancestor", "Rollback target is not an exact source ancestor."
    )


def _validate_snapshot_chain(
    root: Path,
    binding: dict[str, object],
    program_plan_binding: dict[str, object],
    seen: set[str] | None = None,
) -> dict[str, object]:
    seen = set() if seen is None else seen
    token = binding["sha256"]
    if token in seen:
        raise AcceptanceAuthorityError(
            "acceptance-transition-chain-broken", "Authority predecessor chain contains a cycle."
        )
    seen.add(token)
    document = _load_bound_document(root, binding, code="acceptance-transition-chain-broken")
    if binding["authoritySchema"] == 1:
        locks = validate_legacy_locks(root)
        expected = {**locks["acceptance"], "authoritySchema": 1, "generation": None}
        if not strict_json_equal(binding, expected):
            raise AcceptanceAuthorityError(
                "acceptance-transition-chain-broken", "Historical authority binding drifted."
            )
        return document
    predecessor_binding = _require_binding(
        document.get("predecessorBinding"), code="acceptance-transition-chain-broken"
    )
    predecessor = _validate_snapshot_chain(root, predecessor_binding, program_plan_binding, seen)
    validate_authority_snapshot(
        document, predecessor=predecessor, program_plan_binding=program_plan_binding
    )
    return document


def _validate_receipt_ancestry(
    root: Path, receipt: dict[str, object], seen: set[str] | None = None
) -> None:
    seen = set() if seen is None else seen
    token = receipt.get("id")
    if type(token) is not str or token in seen:
        raise AcceptanceAuthorityError(
            "acceptance-transition-chain-broken", "Receipt chain contains a cycle."
        )
    seen.add(token)
    from_binding = _require_binding(
        receipt.get("fromSnapshotBinding"), code="acceptance-transition-chain-broken"
    )
    to_binding = _require_binding(
        receipt.get("toSnapshotBinding"), code="acceptance-transition-chain-broken"
    )
    from_document = _load_bound_document(root, from_binding, code="acceptance-transition-chain-broken")
    to_document = _load_bound_document(root, to_binding, code="acceptance-transition-chain-broken")
    from_plan_binding = _require_binding(
        receipt.get("fromProgramPlanBinding"), code="acceptance-program-plan-binding-drift"
    )
    to_plan_binding = _require_binding(
        receipt.get("toProgramPlanBinding"), code="acceptance-program-plan-binding-drift"
    )
    from_plan = _load_bound_document(
        root, from_plan_binding, code="acceptance-program-plan-binding-drift"
    )
    to_plan = _load_bound_document(root, to_plan_binding, code="acceptance-program-plan-binding-drift")
    _validate_program_plan_document(root, from_plan, from_plan_binding, from_binding)
    _validate_program_plan_document(root, to_plan, to_plan_binding, to_binding)
    if from_binding["authoritySchema"] == 2 and not strict_json_equal(
        from_document.get("programPlanBinding"), from_plan_binding
    ):
        raise AcceptanceAuthorityError(
            "acceptance-program-plan-binding-drift", "Receipt plan does not match source snapshot."
        )
    if to_binding["authoritySchema"] == 2 and not strict_json_equal(
        to_document.get("programPlanBinding"), to_plan_binding
    ):
        raise AcceptanceAuthorityError(
            "acceptance-program-plan-binding-drift", "Receipt plan does not match successor snapshot."
        )
    validate_transition_receipt(receipt, from_document=from_document, to_document=to_document)
    if receipt["transactionType"] == "rollback":
        _require_exact_rollback_ancestor(root, from_binding, to_binding)
    if from_binding["authoritySchema"] == 2:
        predecessor_binding = _require_binding(
            from_document.get("predecessorBinding"), code="acceptance-transition-chain-broken"
        )
        prior = _load_introducing_receipt(root, predecessor_binding, from_binding)
        _validate_receipt_ancestry(root, prior, seen)


def resolve_historical_authority(
    root: Path,
    binding: dict[str, object],
    *,
    frozen_program_plan_binding: dict[str, object] | None = None,
) -> dict[str, object]:
    """Resolve exactly one explicitly bound authority without consulting a selector."""

    normalized = _require_binding(binding, code="acceptance-selector-target-invalid")
    if normalized["authoritySchema"] == 1:
        document = _validate_snapshot_chain(root, normalized, normalized)
        if frozen_program_plan_binding is not None:
            plan_binding = _require_binding(
                frozen_program_plan_binding, code="acceptance-program-plan-binding-drift"
            )
            plan = _load_bound_document(
                root, plan_binding, code="acceptance-program-plan-binding-drift"
            )
            _validate_program_plan_document(root, plan, plan_binding, normalized)
    else:
        if frozen_program_plan_binding is None:
            raise AcceptanceAuthorityError(
                "acceptance-program-plan-binding-drift",
                "Versioned historical authority requires its frozen program-plan binding.",
            )
        plan_binding = _require_binding(
            frozen_program_plan_binding, code="acceptance-program-plan-binding-drift"
        )
        plan = _load_bound_document(root, plan_binding, code="acceptance-program-plan-binding-drift")
        _validate_program_plan_document(root, plan, plan_binding, normalized)
        document = _validate_snapshot_chain(root, normalized, plan_binding)
    return {"authority": document, "binding": copy.deepcopy(normalized)}


def resolve_current_authority(root: Path, selector_path: str) -> dict[str, object]:
    """Resolve a candidate current authority only through its selector and receipt chain."""

    path = _safe_relative_path(root, selector_path, code="acceptance-selector-target-invalid")
    try:
        selector_bytes = path.read_bytes()
    except OSError as error:
        raise AcceptanceAuthorityError(
            "acceptance-selector-target-invalid", "Selector cannot be read."
        ) from error
    try:
        selector = json.loads(selector_bytes)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise AcceptanceAuthorityError(
            "acceptance-selector-target-invalid", "Selector cannot be read."
        ) from error
    selector = _validate_selector(selector)
    snapshot_binding = selector["activeSnapshotBinding"]
    transition_binding = selector["activeTransitionBinding"]
    plan_binding = selector["programPlanBinding"]
    plan = _load_bound_document(root, plan_binding, code="acceptance-selector-target-invalid")
    _validate_program_plan_document(root, plan, plan_binding, snapshot_binding)
    snapshot = _load_bound_document(root, snapshot_binding, code="acceptance-selector-target-invalid")
    receipt = _load_bound_document(root, transition_binding, code="acceptance-transition-receipt-invalid")
    if not strict_json_equal(receipt.get("toSnapshotBinding"), snapshot_binding):
        raise AcceptanceAuthorityError(
            "acceptance-transition-chain-broken", "Selector receipt does not introduce its snapshot."
        )
    if not strict_json_equal(receipt.get("toProgramPlanBinding"), plan_binding):
        raise AcceptanceAuthorityError(
            "acceptance-selector-target-invalid", "Selector receipt plan binding drifted."
        )
    if receipt.get("transactionType") != "rollback":
        _reject_duplicate_introducing_receipts(
            root, transition_binding["path"], snapshot_binding
        )
    _validate_receipt_ancestry(root, receipt)
    _validate_snapshot_chain(root, snapshot_binding, plan_binding)
    return {
        "authority": snapshot,
        "binding": copy.deepcopy(snapshot_binding),
        "selector": copy.deepcopy(selector),
        "receipt": receipt,
        "programPlan": plan,
    }
