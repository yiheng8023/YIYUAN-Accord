from __future__ import annotations

import hashlib
import json
import re
import subprocess
from pathlib import Path

from scripts.harness_decision_packet import strict_json_equal
from scripts.program_acceptance_authority_v2 import (
    AcceptanceAuthorityError,
    canonical_file_bytes,
)


MIGRATION_INVENTORY_PATH = Path(
    "registry/program-acceptance-authority-v2-migration-inventory-2026-08-10.json"
)
LEGACY_ACCEPTANCE_SEARCH_PATTERNS = {
    "legacy-acceptance-path": "registry/program-acceptance-map.json",
    "legacy-acceptance-id": "curation-program-acceptance-map-v1",
}
SOURCE_PATTERN_IDS = ["legacy-acceptance-path", "legacy-acceptance-id"]
CLASSIFICATIONS = {
    "A-immutable-historical",
    "B-current-authority-consumer",
    "C-version-neutral-component",
    "D-migration-governance-and-regression",
}
CURRENT_BINDINGS = {
    "legacy-v1",
    "candidate-selector",
    "explicit-input",
    "migration-metadata",
    "not-applicable",
}
CANDIDATE_BINDINGS = {
    "preserve-legacy-v1",
    "rehearsal-selector",
    "explicit-input",
    "migration-metadata",
    "not-applicable",
}
OCCURRENCE_FIELDS = (
    "path",
    "line",
    "patternId",
    "lineSha256",
    "purpose",
    "classification",
    "currentBinding",
    "candidateBinding",
    "rehearsalAction",
    "liveMigrationAction",
    "rollbackAction",
    "verificationSurface",
    "separateAuthorizationRequired",
)
IDENTITY_FIELDS = ("path", "line", "patternId", "lineSha256")
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


def discover_acceptance_reference_occurrences(root: Path) -> list[dict[str, object]]:
    """Discover every tracked UTF-8 legacy-literal occurrence by symbolic identity."""

    completed = subprocess.run(
        ["git", "-C", str(root), "ls-files", "-z"],
        check=True,
        capture_output=True,
    )
    occurrences: list[dict[str, object]] = []
    for raw_relative in completed.stdout.split(b"\0"):
        if not raw_relative:
            continue
        relative = Path(raw_relative.decode("utf-8"))
        try:
            text = (root / relative).read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for line_number, line in enumerate(text.splitlines(), start=1):
            for pattern_id, literal in LEGACY_ACCEPTANCE_SEARCH_PATTERNS.items():
                start = 0
                while True:
                    index = line.find(literal, start)
                    if index < 0:
                        break
                    occurrences.append(
                        {
                            "path": relative.as_posix(),
                            "line": line_number,
                            "patternId": pattern_id,
                            "lineSha256": hashlib.sha256(line.encode("utf-8")).hexdigest(),
                        }
                    )
                    start = index + len(literal)
    return occurrences


def _inventory_path(root: Path, path: Path) -> Path:
    if path.is_absolute():
        raise AcceptanceAuthorityError(
            "migration-inventory-incomplete", "Migration inventory path must be relative."
        )
    candidate = (root / path).resolve()
    try:
        candidate.relative_to(root.resolve())
    except ValueError as error:
        raise AcceptanceAuthorityError(
            "migration-inventory-incomplete", "Migration inventory path escapes root."
        ) from error
    return candidate


def load_migration_inventory(
    root: Path, path: Path = MIGRATION_INVENTORY_PATH
) -> dict[str, object]:
    """Load the reviewed record without making it a source of truth by itself."""

    try:
        document = json.loads(_inventory_path(root, path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise AcceptanceAuthorityError(
            "migration-inventory-incomplete", "Migration inventory cannot be loaded."
        ) from error
    if not isinstance(document, dict):
        raise AcceptanceAuthorityError(
            "migration-inventory-incomplete", "Migration inventory must be an object."
        )
    return document


def _require_nonempty_string(value: object) -> bool:
    return type(value) is str and bool(value.strip())


def _identity_projection(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    return [{key: row[key] for key in IDENTITY_FIELDS} for row in rows]


def _reference_set_sha256(discovered: list[dict[str, object]]) -> str:
    return hashlib.sha256(canonical_file_bytes(discovered)).hexdigest()


def migration_inventory_wire_bytes(inventory: dict[str, object]) -> bytes:
    """Serialize the record deterministically, escaping only the permitted host path."""

    canonical = canonical_file_bytes(inventory)
    legacy_path = LEGACY_ACCEPTANCE_SEARCH_PATTERNS["legacy-acceptance-path"]
    escaped_path = legacy_path.replace("/", "\\/")
    unescaped_host = f'"path":"{legacy_path}"'.encode("utf-8")
    escaped_host = f'"path":"{escaped_path}"'.encode("utf-8")
    return canonical.replace(unescaped_host, escaped_host)


def _reject_raw_search_literals(inventory: dict[str, object]) -> None:
    sanitized = json.loads(json.dumps(inventory))
    occurrences = sanitized.get("occurrences")
    if isinstance(occurrences, list):
        legacy_path = LEGACY_ACCEPTANCE_SEARCH_PATTERNS["legacy-acceptance-path"]
        for row in occurrences:
            if isinstance(row, dict) and row.get("path") == legacy_path:
                row["path"] = "allowed-legacy-host-locator"
    payload = canonical_file_bytes(sanitized)
    if any(
        literal.encode("utf-8") in payload
        for literal in LEGACY_ACCEPTANCE_SEARCH_PATTERNS.values()
    ):
        raise AcceptanceAuthorityError(
            "migration-consumer-class-invalid",
            "Migration inventory may retain a raw literal only as its exact host locator.",
        )


def _validate_row_governance(row: dict[str, object]) -> None:
    if set(row) != set(OCCURRENCE_FIELDS):
        raise AcceptanceAuthorityError(
            "migration-consumer-class-invalid", "Migration occurrence fields are invalid."
        )
    if (
        not _require_nonempty_string(row["path"])
        or type(row["line"]) is not int
        or row["line"] < 1
        or row["patternId"] not in SOURCE_PATTERN_IDS
        or type(row["lineSha256"]) is not str
        or not _SHA256_RE.fullmatch(row["lineSha256"])
        or any(
            not _require_nonempty_string(row[field])
            for field in (
                "purpose",
                "rehearsalAction",
                "liveMigrationAction",
                "rollbackAction",
                "verificationSurface",
            )
        )
        or type(row["separateAuthorizationRequired"]) is not bool
        or row["classification"] not in CLASSIFICATIONS
        or row["currentBinding"] not in CURRENT_BINDINGS
        or row["candidateBinding"] not in CANDIDATE_BINDINGS
    ):
        raise AcceptanceAuthorityError(
            "migration-consumer-class-invalid", "Migration occurrence governance is invalid."
        )

    classification = row["classification"]
    if classification == "A-immutable-historical":
        if row["candidateBinding"] != "preserve-legacy-v1":
            raise AcceptanceAuthorityError(
                "acceptance-historical-consumer-repointed",
                "Historical consumers must preserve their legacy-v1 binding.",
            )
    elif classification == "B-current-authority-consumer":
        actions = " ".join(
            row[field]
            for field in ("rehearsalAction", "liveMigrationAction", "rollbackAction")
        ).lower()
        if row["candidateBinding"] != "rehearsal-selector" or (
            "activate" in actions and "legacy-v1" in actions
        ):
            raise AcceptanceAuthorityError(
                "acceptance-current-consumer-legacy-bypass",
                "Current consumers cannot bypass the candidate selector with legacy-v1.",
            )
    elif classification == "C-version-neutral-component":
        if (
            row["currentBinding"] != "explicit-input"
            or row["candidateBinding"] != "explicit-input"
        ):
            raise AcceptanceAuthorityError(
                "acceptance-neutral-consumer-path-owned",
                "Version-neutral consumers must receive bindings explicitly.",
            )
    else:
        actions = " ".join(
            row[field]
            for field in ("purpose", "rehearsalAction", "liveMigrationAction", "rollbackAction")
        ).lower()
        if "live activation" in actions:
            raise AcceptanceAuthorityError(
                "migration-consumer-class-invalid",
                "Migration governance cannot claim live activation.",
            )


def validate_migration_inventory(root: Path, inventory: dict[str, object]) -> None:
    """Reject an inventory that is not an exact, symbolic, fail-closed projection."""

    required_fields = {
        "schema",
        "id",
        "date",
        "status",
        "sourcePatternIds",
        "baselineObservation",
        "occurrences",
        "claimBoundary",
    }
    if set(inventory) != required_fields:
        raise AcceptanceAuthorityError(
            "migration-inventory-incomplete", "Migration inventory root fields are invalid."
        )
    if (
        type(inventory["schema"]) is not int
        or inventory["schema"] != 1
        or not _require_nonempty_string(inventory["id"])
        or not _require_nonempty_string(inventory["date"])
        or not _require_nonempty_string(inventory["status"])
        or not strict_json_equal(inventory["sourcePatternIds"], SOURCE_PATTERN_IDS)
        or not isinstance(inventory["occurrences"], list)
        or not isinstance(inventory["baselineObservation"], dict)
        or not isinstance(inventory["claimBoundary"], dict)
    ):
        raise AcceptanceAuthorityError(
            "migration-consumer-class-invalid", "Migration inventory root values are invalid."
        )

    _reject_raw_search_literals(inventory)
    baseline = inventory["baselineObservation"]
    if set(baseline) != {"trackedReferenceCount", "occurrenceCount", "referenceSetSha256"} or (
        type(baseline["trackedReferenceCount"]) is not int
        or baseline["trackedReferenceCount"] < 0
        or type(baseline["occurrenceCount"]) is not int
        or baseline["occurrenceCount"] < 0
        or type(baseline["referenceSetSha256"]) is not str
        or not _SHA256_RE.fullmatch(baseline["referenceSetSha256"])
    ):
        raise AcceptanceAuthorityError(
            "migration-consumer-class-invalid", "Migration baseline is invalid."
        )
    expected_claim_boundary = {
        "provesLiveMigration": False,
        "provesCurrentSelectorActivation": False,
        "provesBehavior": False,
        "provesValue": False,
        "provesCrossHostPortability": False,
        "provesProductionReadiness": False,
        "provesReleaseEligibility": False,
        "provesOverallHarnessCompletion": False,
    }
    if not strict_json_equal(inventory["claimBoundary"], expected_claim_boundary):
        raise AcceptanceAuthorityError(
            "migration-consumer-class-invalid", "Migration claim boundary is invalid."
        )

    rows = inventory["occurrences"]
    if not all(isinstance(row, dict) for row in rows):
        raise AcceptanceAuthorityError(
            "migration-consumer-class-invalid", "Migration occurrences must be objects."
        )
    typed_rows = [row for row in rows if isinstance(row, dict)]
    for row in typed_rows:
        _validate_row_governance(row)

    discovered = discover_acceptance_reference_occurrences(root)
    if not strict_json_equal(_identity_projection(typed_rows), discovered):
        raise AcceptanceAuthorityError(
            "migration-inventory-incomplete", "Migration inventory does not exactly cover discovery."
        )
    if not strict_json_equal(baseline["trackedReferenceCount"], len({row["path"] for row in discovered})) or (
        not strict_json_equal(baseline["occurrenceCount"], len(discovered))
        or not strict_json_equal(baseline["referenceSetSha256"], _reference_set_sha256(discovered))
    ):
        raise AcceptanceAuthorityError(
            "migration-inventory-incomplete", "Migration inventory baseline drifted."
        )
