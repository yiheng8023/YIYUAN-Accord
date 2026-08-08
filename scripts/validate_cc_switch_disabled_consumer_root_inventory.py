#!/usr/bin/env python3
"""Validate the disabled CC Switch consumer-root read-only inventory."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
RECORD_PATH = Path(
    "registry/cc-switch-disabled-consumer-root-readonly-inventory-2026-08-08.json"
)
REPORT_PATH = Path("audits/cc-switch-disabled-consumer-roots-2026-08-08/REPORT.json")
DOCUMENTATION_PATH = Path(
    "docs/strategy/CC-SWITCH-DISABLED-CONSUMER-ROOT-READONLY-INVENTORY-2026-08-08.md"
)
ACCEPTANCE_PATH = Path("registry/program-acceptance-map.json")
AUTHORITY_PATH = Path("registry/skill-portfolio-current-authority.json")
CLOSEOUT_PATH = Path(
    "registry/program-final-closeout-readiness-reconciliation-2026-07-28.json"
)
EVIDENCE_ID = "evidence.cc-switch-disabled-consumer-root-readonly-inventory-2026-08-08"
SUPPORTS = {
    "acceptance.consumer-mapping-evidence",
    "acceptance.cc-switch-source-preserving-skill-pool",
    "acceptance.foreign-managed-capability-coexistence",
}
HOST_PATHS = {
    "gemini": "~/.gemini/skills",
    "grokbuild": "~/.grok/skills",
    "opencode": "~/.config/opencode/skills",
    "hermes": "~/.hermes/skills",
}


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def validate_record(
    record: dict[str, Any],
    *,
    acceptance: dict[str, Any] | None = None,
    authority: dict[str, Any] | None = None,
    closeout: dict[str, Any] | None = None,
    root: Path = ROOT,
) -> None:
    _require(
        record.get("schema") == 1
        and record.get("id")
        == "cc-switch-disabled-consumer-root-readonly-inventory-2026-08-08"
        and record.get("asOf") == "2026-08-08"
        and record.get("status")
        == "four-disabled-consumer-roots-readonly-observed-absent-zero-matt-projections",
        "Disabled-consumer inventory identity drifted",
    )
    observation = record.get("observation", {})
    roots = {item.get("host"): item for item in observation.get("roots", [])}
    _require(
        observation.get("manager") == "CC Switch 3.19.2"
        and observation.get("managerProcessRunning") is True
        and observation.get("databaseReadOnly") is True
        and observation.get("databaseMattRowCount") == 25
        and observation.get("databaseSha256UnchangedDuringObservation") is True
        and observation.get("observationStable") is True
        and observation.get("enabledMattByHost") == {host: 0 for host in HOST_PATHS}
        and set(roots) == set(HOST_PATHS)
        and all(
            roots[host].get("path") == path
            and roots[host].get("exists") is False
            and roots[host].get("topLevelEntryCount") == 0
            and roots[host].get("mattEntryCount") == 0
            for host, path in HOST_PATHS.items()
        )
        and observation.get("allDisabledRootsFreeOfMattProjections") is True,
        "Disabled-consumer live observation drifted",
    )

    privacy = record.get("privacyBoundary", {})
    _require(
        privacy
        and all(value is False for value in privacy.values()),
        "Disabled-consumer privacy boundary drifted",
    )
    authority_boundary = record.get("authorityBoundary", {})
    _require(
        authority_boundary.get("readOnlyLocalRootAndDatabaseObservationAuthorized")
        is True
        and authority_boundary.get("repositoryEvidenceWriteAuthorized") is True
        and all(
            value is False
            for key, value in authority_boundary.items()
            if key
            not in {
                "readOnlyLocalRootAndDatabaseObservationAuthorized",
                "repositoryEvidenceWriteAuthorized",
            }
        ),
        "Disabled-consumer authority boundary drifted",
    )
    _require(
        record.get("executionCounters")
        and all(value == 0 for value in record.get("executionCounters", {}).values()),
        "Disabled-consumer execution counters drifted",
    )
    claims = record.get("claimBoundary", {})
    true_claims = {
        "disabledFlagsAtObservationProved",
        "rootPresenceAtObservationProved",
        "mattProjectionAbsenceAtObservationProved",
    }
    _require(
        all(claims.get(key) is True for key in true_claims)
        and all(value is False for key, value in claims.items() if key not in true_claims),
        "Disabled-consumer claim boundary drifted",
    )

    report_binding = record.get("report", {})
    report_path = root / REPORT_PATH
    _require(
        record.get("documentation") == DOCUMENTATION_PATH.as_posix()
        and (root / DOCUMENTATION_PATH).is_file()
        and report_binding.get("path") == REPORT_PATH.as_posix()
        and report_binding.get("status") == "read-only-disabled-consumer-roots-clear"
        and report_path.is_file()
        and hashlib.sha256(report_path.read_bytes()).hexdigest()
        == report_binding.get("fileSha256"),
        "Disabled-consumer report binding drifted",
    )
    report = json.loads(report_path.read_text(encoding="utf-8"))
    _require(
        report.get("status") == "read-only-disabled-consumer-roots-clear"
        and report.get("database", {}).get("mattRowCount") == 25
        and report.get("database", {}).get("enabledMattByHost")
        == {host: 0 for host in HOST_PATHS}
        and report.get("database", {}).get("sha256Before")
        == report.get("database", {}).get("sha256After")
        and report.get("observationStable") is True
        and report.get("allDisabledRootsFreeOfMattProjections") is True
        and all(value == 0 for value in report.get("executionCounters", {}).values())
        and all(value is False for value in report.get("privacyBoundary", {}).values()),
        "Disabled-consumer report content drifted",
    )

    acceptance_boundary = record.get("acceptanceBoundary", {})
    _require(
        acceptance_boundary.get("verifiedCriteria") == 46
        and acceptance_boundary.get("partialCriteria") == 15
        and acceptance_boundary.get("plannedCriteria") == 0
        and acceptance_boundary.get("criteriaAdvanced") == []
        and set(acceptance_boundary.get("supportsWithoutAssessmentUpgrade", []))
        == SUPPORTS,
        "Disabled-consumer acceptance boundary drifted",
    )
    if acceptance is not None:
        matches = [
            item
            for item in acceptance.get("evidence", [])
            if item.get("id") == EVIDENCE_ID
        ]
        _require(len(matches) == 1, "Disabled-consumer evidence registration drifted")
        _require(
            matches[0].get("path") == RECORD_PATH.as_posix()
            and set(matches[0].get("supports", [])) == SUPPORTS,
            "Disabled-consumer evidence boundary drifted",
        )
        for criterion in acceptance.get("acceptanceCriteria", []):
            if criterion.get("id") in SUPPORTS:
                _require(
                    criterion.get("assessment") == "partial"
                    and EVIDENCE_ID in criterion.get("evidenceIds", []),
                    "Disabled-consumer acceptance reverse reference drifted",
                )
    if authority is not None:
        current = authority.get("currentDisabledConsumerProjectionObservation", {})
        _require(
            current.get("event") == RECORD_PATH.as_posix()
            and current.get("hosts") == list(HOST_PATHS)
            and current.get("allRootsAbsent") is True
            and current.get("allMattFlagsDisabled") is True
            and current.get("mattProjectionCount") == 0
            and current.get("hostInstallationProved") is False
            and current.get("loaderInvocationProved") is False,
            "Current disabled-consumer authority drifted",
        )
    if closeout is not None:
        _require(
            closeout.get("sourceBindings", {}).get("disabledConsumerRootInventory")
            == RECORD_PATH.as_posix(),
            "Closeout disabled-consumer source binding drifted",
        )


def validate_repository_inventory(root: Path = ROOT) -> dict[str, Any]:
    record = json.loads((root / RECORD_PATH).read_text(encoding="utf-8"))
    acceptance = json.loads((root / ACCEPTANCE_PATH).read_text(encoding="utf-8"))
    authority = json.loads((root / AUTHORITY_PATH).read_text(encoding="utf-8"))
    closeout = json.loads((root / CLOSEOUT_PATH).read_text(encoding="utf-8"))
    validate_record(
        record,
        acceptance=acceptance,
        authority=authority,
        closeout=closeout,
        root=root,
    )
    return record


def main() -> int:
    validate_repository_inventory(ROOT)
    print("CC Switch disabled-consumer root inventory validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
