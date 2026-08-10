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
        manifest_rows = [
            row for row in after_evidence if isinstance(row, dict) and row.get("id") == MANIFEST_EVIDENCE_ID
        ]
        code = "acceptance-evidence-source-missing" if not manifest_rows else "acceptance-evidence-source-drift"
        raise AcceptanceAuthorityError(code, "The manifest evidence row is not exact.")
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
