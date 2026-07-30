#!/usr/bin/env python3
"""Revalidate a prepared Skill-ablation host transaction without mutating it.

The preflight reads the prepared transaction contract, hashes the bound config
and Skill files, semantically parses the config's ``skills.config`` array, and
checks whether the prepared backup path already exists. It never emits config
or Skill contents and never writes, disables, restarts, invokes, or deletes
anything.
"""

from __future__ import annotations

import copy
from datetime import UTC, datetime
import hashlib
import json
from pathlib import Path
import tomllib
from typing import Any, Callable


REPORT_ID = "skill-ablation-host-transaction-revalidation"
CANONICAL_CONTRACT_PATH = (
    Path(__file__).resolve().parents[1]
    / "registry"
    / "skill-ablation-host-config-transaction-2026-07-19.json"
)
MATCH_STATUS = "preconditions-match-authorization-still-required"
BLOCKED_STATUS = "blocked-baseline-drift-reintake-required"
CLAIM_KEYS = {
    "countsAsAtomicPreconditionSnapshot",
    "countsAsTransactionExecution",
    "countsAsGlobalConfigMutation",
    "countsAsApplicationRestart",
    "countsAsSkillDisablement",
    "countsAsTaskScopedExposureProof",
    "countsAsLoaderInvocationProof",
    "countsAsActualModelOrReasoningProof",
    "countsAsWeakAgentAcceptance",
}


def canonical_sha256(value: Any) -> str:
    encoded = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def sha256_bytes(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _bound(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _sha256(value: Any) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(character in "0123456789abcdef" for character in value)
    )


def _path(value: str) -> Path:
    return Path(value).resolve(strict=False)


def _display_path(path: Path) -> str:
    return path.resolve(strict=False).as_posix()


def _stat_identity(stat_result: Any) -> tuple[int, int]:
    return (stat_result.st_size, stat_result.st_mtime_ns)


def _observe_config(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {
            "path": _display_path(path),
            "exists": False,
            "observationComplete": False,
            "prePostStable": False,
            "readErrorClass": None,
            "tomlParseComplete": False,
            "tomlParseErrorClass": None,
            "lengthBytes": None,
            "lastWriteTimeUtc": None,
            "sha256": None,
            "skillsConfigEntryCount": None,
        }
    try:
        before = path.stat()
        content = path.read_bytes()
        after = path.stat()
    except OSError as error:
        return {
            "path": _display_path(path),
            "exists": path.is_file(),
            "observationComplete": False,
            "prePostStable": False,
            "readErrorClass": type(error).__name__,
            "tomlParseComplete": False,
            "tomlParseErrorClass": None,
            "lengthBytes": None,
            "lastWriteTimeUtc": None,
            "sha256": None,
            "skillsConfigEntryCount": None,
        }
    try:
        parsed = tomllib.loads(content.decode("utf-8"))
        skills = parsed.get("skills", {})
        entries = skills.get("config", []) if isinstance(skills, dict) else []
        if not isinstance(entries, list):
            raise ValueError("skills.config is not an array of tables")
        entry_count: int | None = len(entries)
        parse_complete = True
        parse_error_class: str | None = None
    except (UnicodeDecodeError, tomllib.TOMLDecodeError, ValueError) as error:
        entry_count = None
        parse_complete = False
        parse_error_class = type(error).__name__
    return {
        "path": _display_path(path),
        "exists": True,
        "observationComplete": True,
        "prePostStable": _stat_identity(before) == _stat_identity(after),
        "readErrorClass": None,
        "tomlParseComplete": parse_complete,
        "tomlParseErrorClass": parse_error_class,
        "lengthBytes": len(content),
        "lastWriteTimeUtc": datetime.fromtimestamp(
            after.st_mtime,
            tz=UTC,
        ).isoformat(),
        "sha256": sha256_bytes(content),
        "skillsConfigEntryCount": entry_count,
    }


def _observe_target(target: dict[str, Any]) -> dict[str, Any]:
    path = _path(target["path"])
    if not path.is_file():
        return {
            "name": target["name"],
            "path": _display_path(path),
            "expectedSha256": target["sha256"],
            "exists": False,
            "observationComplete": False,
            "prePostStable": False,
            "readErrorClass": None,
            "lengthBytes": None,
            "observedSha256": None,
            "sha256Matches": False,
        }
    try:
        before = path.stat()
        content = path.read_bytes()
        after = path.stat()
    except OSError as error:
        return {
            "name": target["name"],
            "path": _display_path(path),
            "expectedSha256": target["sha256"],
            "exists": path.is_file(),
            "observationComplete": False,
            "prePostStable": False,
            "readErrorClass": type(error).__name__,
            "lengthBytes": None,
            "observedSha256": None,
            "sha256Matches": False,
        }
    observed_sha256 = sha256_bytes(content)
    return {
        "name": target["name"],
        "path": _display_path(path),
        "expectedSha256": target["sha256"],
        "exists": True,
        "observationComplete": True,
        "prePostStable": _stat_identity(before) == _stat_identity(after),
        "readErrorClass": None,
        "lengthBytes": len(content),
        "observedSha256": observed_sha256,
        "sha256Matches": observed_sha256 == target["sha256"],
    }


def _comparison(
    contract: dict[str, Any],
    config: dict[str, Any],
    targets: list[dict[str, Any]],
    backup_exists_before: bool,
    backup_exists_after: bool,
) -> tuple[dict[str, bool], list[str]]:
    baseline = contract["observedBaseline"]
    comparison = {
        "configExists": config["exists"] is True,
        "configObservationComplete": config["observationComplete"] is True,
        "configPrePostStable": config["prePostStable"] is True,
        "configTomlParseComplete": config["tomlParseComplete"] is True,
        "configSha256Matches": config["sha256"] == baseline["sha256"],
        "configLengthMatches": config["lengthBytes"] == baseline["lengthBytes"],
        "skillsConfigEntryCountMatches": (
            config["skillsConfigEntryCount"]
            == baseline["skillsConfigEntryCount"]
        ),
        "allTargetsExist": all(target["exists"] for target in targets),
        "allTargetObservationsComplete": all(
            target["observationComplete"] for target in targets
        ),
        "allTargetsPrePostStable": all(
            target["prePostStable"] for target in targets
        ),
        "allTargetSha256Match": all(
            target["sha256Matches"] for target in targets
        ),
        "preparedBackupAbsent": (
            backup_exists_before is False and backup_exists_after is False
        ),
        "preparedBackupObservationStable": (
            backup_exists_before == backup_exists_after
        ),
    }
    reason_by_key = {
        "configExists": "config-missing",
        "configObservationComplete": "config-observation-incomplete",
        "configPrePostStable": "config-observation-unstable",
        "configTomlParseComplete": "config-toml-parse-incomplete",
        "configSha256Matches": "config-sha256-drift",
        "configLengthMatches": "config-length-drift",
        "skillsConfigEntryCountMatches": "skills-config-entry-count-drift",
        "allTargetsExist": "target-missing",
        "allTargetObservationsComplete": "target-observation-incomplete",
        "allTargetsPrePostStable": "target-observation-unstable",
        "allTargetSha256Match": "target-sha256-drift",
        "preparedBackupAbsent": "prepared-backup-already-exists",
        "preparedBackupObservationStable": "prepared-backup-observation-unstable",
    }
    reasons = [
        reason_by_key[key]
        for key, matches in comparison.items()
        if not matches
    ]
    return comparison, reasons


def _report_digest(report: dict[str, Any]) -> str:
    body = copy.deepcopy(report)
    body.pop("reportSha256", None)
    return canonical_sha256(body)


def build_revalidation_report(
    contract: dict[str, Any],
    *,
    contract_path: Path,
    contract_sha256: str,
    clock: Callable[[], datetime] | None = None,
) -> dict[str, Any]:
    """Build a secret-safe, read-only precondition comparison."""

    if contract.get("id") != "skill-ablation-host-config-transaction-2026-07-19":
        raise ValueError("unsupported prepared transaction contract")
    if not _sha256(contract_sha256):
        raise ValueError("contract_sha256 must be a lowercase SHA-256")
    active_clock = clock or (lambda: datetime.now(UTC))
    started = active_clock()
    if started.tzinfo is None:
        raise ValueError("clock must return a timezone-aware datetime")

    backup_path = _path(contract["transaction"]["backupPath"])
    backup_exists_before = backup_path.exists()
    config = _observe_config(_path(contract["observedBaseline"]["configPath"]))
    targets = [_observe_target(target) for target in contract["targets"]]
    backup_exists_after = backup_path.exists()
    completed = active_clock()
    if completed.tzinfo is None:
        raise ValueError("clock must return a timezone-aware datetime")
    comparison, reasons = _comparison(
        contract,
        config,
        targets,
        backup_exists_before,
        backup_exists_after,
    )
    report = {
        "schema": 1,
        "id": REPORT_ID,
        "observedAt": started.astimezone(UTC).isoformat(),
        "observationCompletedAt": completed.astimezone(UTC).isoformat(),
        "status": MATCH_STATUS if not reasons else BLOCKED_STATUS,
        "sourceContract": {
            "id": contract["id"],
            "date": contract["date"],
            "path": _display_path(contract_path),
            "sha256": contract_sha256,
        },
        "observer": {
            "identity": "python-read-only-host-transaction-revalidator",
            "version": "1",
        },
        "configObservation": config,
        "targetObservations": targets,
        "targetObservationManifestSha256": canonical_sha256(targets),
        "backupObservation": {
            "path": _display_path(backup_path),
            "existsBefore": backup_exists_before,
            "existsAfter": backup_exists_after,
            "prePostStable": backup_exists_before == backup_exists_after,
        },
        "comparison": comparison,
        "driftReasons": reasons,
        "contentBoundary": {
            "configContentIncluded": False,
            "skillContentIncluded": False,
            "secretValuesRecorded": False,
            "hashesAndMetadataOnly": True,
        },
        "cohortBoundary": {
            "atomicSnapshotProved": False,
            "mustRevalidateInsideAuthorizedMutationCriticalSection": True,
            "reportDigestIsSignatureOrLiveAttestation": False,
        },
        "claimBoundary": {
            key: False for key in sorted(CLAIM_KEYS)
        },
    }
    report["reportSha256"] = _report_digest(report)
    return report


def _validate_revalidation_report_against_digest(
    report: dict[str, Any],
    contract: dict[str, Any],
    *,
    expected_contract_sha256: str,
) -> list[str]:
    """Validate a recorded report without rereading live host state."""

    failures: list[str] = []
    expected_keys = {
        "schema",
        "id",
        "observedAt",
        "observationCompletedAt",
        "status",
        "sourceContract",
        "observer",
        "configObservation",
        "targetObservations",
        "targetObservationManifestSha256",
        "backupObservation",
        "comparison",
        "driftReasons",
        "contentBoundary",
        "cohortBoundary",
        "claimBoundary",
        "reportSha256",
    }
    if (
        not isinstance(report, dict)
        or set(report) != expected_keys
        or report.get("schema") != 1
        or report.get("id") != REPORT_ID
        or not _bound(report.get("observedAt"))
        or not _bound(report.get("observationCompletedAt"))
    ):
        return ["fail-report-shape"]
    if (
        not _sha256(report.get("reportSha256"))
        or report["reportSha256"] != _report_digest(report)
    ):
        failures.append("fail-report-digest")

    source = report.get("sourceContract")
    if (
        not isinstance(source, dict)
        or set(source) != {"id", "date", "path", "sha256"}
        or source.get("id") != contract.get("id")
        or source.get("date") != contract.get("date")
        or not _bound(source.get("path"))
        or not _sha256(source.get("sha256"))
        or not _sha256(expected_contract_sha256)
        or source.get("sha256") != expected_contract_sha256
    ):
        failures.append("fail-source-contract-binding")
    if report.get("observer") != {
        "identity": "python-read-only-host-transaction-revalidator",
        "version": "1",
    }:
        failures.append("fail-observer-binding")

    config = report.get("configObservation")
    expected_config_keys = {
        "path",
        "exists",
        "observationComplete",
        "prePostStable",
        "readErrorClass",
        "tomlParseComplete",
        "tomlParseErrorClass",
        "lengthBytes",
        "lastWriteTimeUtc",
        "sha256",
        "skillsConfigEntryCount",
    }
    config_shape_valid = (
        isinstance(config, dict)
        and set(config) == expected_config_keys
        and config.get("path")
        == _display_path(_path(contract["observedBaseline"]["configPath"]))
    )
    if not config_shape_valid:
        failures.append("fail-config-observation-shape")

    targets = report.get("targetObservations")
    expected_targets = contract.get("targets", [])
    targets_shape_valid = (
        isinstance(targets, list)
        and len(targets) == len(expected_targets)
        and not any(
            not isinstance(observed, dict)
            or set(observed)
            != {
                "name",
                "path",
                "expectedSha256",
                "exists",
                "observationComplete",
                "prePostStable",
                "readErrorClass",
                "lengthBytes",
                "observedSha256",
                "sha256Matches",
            }
            or observed.get("name") != expected.get("name")
            or observed.get("path") != _display_path(_path(expected["path"]))
            or observed.get("expectedSha256") != expected.get("sha256")
            for observed, expected in zip(targets, expected_targets)
        )
    )
    if not targets_shape_valid:
        failures.append("fail-target-observation-binding")
    if (
        not _sha256(report.get("targetObservationManifestSha256"))
        or report.get("targetObservationManifestSha256")
        != canonical_sha256(targets)
    ):
        failures.append("fail-target-observation-manifest")

    backup = report.get("backupObservation")
    expected_backup_path = _display_path(
        _path(contract["transaction"]["backupPath"])
    )
    backup_shape_valid = (
        isinstance(backup, dict)
        and set(backup)
        == {"path", "existsBefore", "existsAfter", "prePostStable"}
        and backup.get("path") == expected_backup_path
        and backup.get("existsBefore") in {True, False}
        and backup.get("existsAfter") in {True, False}
        and backup.get("prePostStable")
        == (backup.get("existsBefore") == backup.get("existsAfter"))
    )
    if not backup_shape_valid:
        failures.append("fail-backup-observation-binding")

    if config_shape_valid and targets_shape_valid and backup_shape_valid:
        expected_comparison, expected_reasons = _comparison(
            contract,
            config,
            targets,
            backup["existsBefore"],
            backup["existsAfter"],
        )
        if report.get("comparison") != expected_comparison:
            failures.append("fail-comparison-binding")
        if report.get("driftReasons") != expected_reasons:
            failures.append("fail-drift-reason-binding")
        expected_status = MATCH_STATUS if not expected_reasons else BLOCKED_STATUS
        if report.get("status") != expected_status:
            failures.append("fail-status-binding")

    if report.get("contentBoundary") != {
        "configContentIncluded": False,
        "skillContentIncluded": False,
        "secretValuesRecorded": False,
        "hashesAndMetadataOnly": True,
    }:
        failures.append("hard-fail-content-boundary")
    if report.get("cohortBoundary") != {
        "atomicSnapshotProved": False,
        "mustRevalidateInsideAuthorizedMutationCriticalSection": True,
        "reportDigestIsSignatureOrLiveAttestation": False,
    }:
        failures.append("hard-fail-cohort-boundary")
    claims = report.get("claimBoundary")
    if (
        not isinstance(claims, dict)
        or set(claims) != CLAIM_KEYS
        or any(value is not False for value in claims.values())
    ):
        failures.append("hard-fail-claim-promotion")
    return list(dict.fromkeys(failures))


def validate_revalidation_report(
    report: dict[str, Any],
    contract: dict[str, Any],
) -> list[str]:
    """Validate against the repository's one canonical prepared contract."""

    contract_bytes = CANONICAL_CONTRACT_PATH.read_bytes()
    canonical_contract = json.loads(contract_bytes.decode("utf-8"))
    source = report.get("sourceContract")
    if (
        contract != canonical_contract
        or not isinstance(source, dict)
        or source.get("path") != _display_path(CANONICAL_CONTRACT_PATH)
    ):
        return ["fail-source-contract-binding"]
    return _validate_revalidation_report_against_digest(
        report,
        contract,
        expected_contract_sha256=sha256_bytes(contract_bytes),
    )


def main() -> int:
    contract_bytes = CANONICAL_CONTRACT_PATH.read_bytes()
    contract = json.loads(contract_bytes.decode("utf-8"))
    report = build_revalidation_report(
        contract,
        contract_path=CANONICAL_CONTRACT_PATH,
        contract_sha256=sha256_bytes(contract_bytes),
    )
    failures = validate_revalidation_report(report, contract)
    if failures:
        raise RuntimeError(f"self-validation failed: {failures}")
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
