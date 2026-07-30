#!/usr/bin/env python3
"""Build a pure offline TDD diagnostic preparation bundle.

This module validates already-provided snapshot, freshness, ledger-authority,
and independent-grant documents.  It never captures source, creates a grant or
ledger, materializes a candidate, starts app-server, or sends a model request.
Even a valid bundle remains ineligible for live dispatch.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from pathlib import Path, PurePosixPath
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
CONTRACT_PATH = Path(
    "registry/"
    "human-ai-collaboration-tdd-noncomparative-dispatch-successor-"
    "contract-v2-2026-07-27.json"
)
PARENT_PROTOCOL_PATH = (
    "registry/"
    "human-ai-collaboration-tdd-noncomparative-treatment-diagnostic-"
    "protocol-2026-07-26.json"
)


class BundleContractError(RuntimeError):
    """Raised when an offline preparation input fails closed."""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise BundleContractError(message)


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


def _parse_time(value: Any, *, label: str) -> datetime:
    _require(isinstance(value, str) and bool(value), f"{label} is missing")
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as error:
        raise BundleContractError(f"{label} is invalid") from error
    _require(parsed.tzinfo is not None, f"{label} must include an offset")
    return parsed


def _safe_repository_file(
    root: Path,
    relative: Any,
    *,
    label: str,
) -> Path:
    _require(
        isinstance(relative, str) and bool(relative),
        f"{label} path is missing",
    )
    relative_path = Path(relative)
    _require(
        not relative_path.is_absolute()
        and ".." not in relative_path.parts,
        f"{label} path escapes the repository root",
    )
    current = root
    for part in relative_path.parts:
        current = current / part
        is_junction = bool(
            getattr(current, "is_junction", lambda: False)()
        )
        _require(
            not current.is_symlink() and not is_junction,
            f"{label} path must not traverse a link",
        )
    try:
        resolved = (root / relative_path).resolve(strict=True)
        resolved.relative_to(root)
    except (OSError, ValueError):
        raise BundleContractError(
            f"{label} path escapes the repository root or is missing"
        ) from None
    _require(resolved.is_file(), f"{label} path is not a file")
    return resolved


def load_contract(root: Path = ROOT) -> dict[str, Any]:
    root = root.resolve()
    path = _safe_repository_file(
        root,
        CONTRACT_PATH.as_posix(),
        label="Successor contract",
    )
    value = json.loads(path.read_text(encoding="utf-8"))
    _require(isinstance(value, dict), "Successor contract must be an object")
    return value


def validate_contract_source_bindings(
    contract: dict[str, Any],
    *,
    root: Path = ROOT,
) -> None:
    root = root.resolve()
    rows = contract.get("sourceBindings")
    _require(isinstance(rows, list) and rows, "Source bindings are missing")
    paths: set[str] = set()
    roles: set[str] = set()
    for row in rows:
        _require(isinstance(row, dict), "Source binding must be an object")
        path_text = row.get("path")
        role = row.get("role")
        _require(
            isinstance(path_text, str)
            and path_text
            and path_text not in paths,
            "Source binding paths must be unique",
        )
        _require(
            isinstance(role, str) and role and role not in roles,
            "Source binding roles must be unique",
        )
        paths.add(path_text)
        roles.add(role)
        path = _safe_repository_file(
            root,
            path_text,
            label=f"Source binding {role}",
        )
        _require(
            row.get("bytes") == path.stat().st_size
            and row.get("sha256") == file_sha256(path),
            f"Source binding bytes drifted: {path_text}",
        )
        _require(
            row.get("dispatchAuthority") is False,
            f"Historical source binding gained authority: {path_text}",
        )
    _require(
        PARENT_PROTOCOL_PATH in paths,
        "Historical parent protocol binding is missing",
    )
    _require(
        "excluded-formal-policy-shell" in roles,
        "Formal policy-shell exclusion is missing",
    )


def _validate_full_contract(
    contract: dict[str, Any],
    *,
    root: Path,
) -> None:
    try:
        from .validate_human_ai_collaboration_tdd_noncomparative_dispatch_successor_contract_v2 import (
            validate_contract,
        )
    except ImportError:  # pragma: no cover - direct script execution
        from validate_human_ai_collaboration_tdd_noncomparative_dispatch_successor_contract_v2 import (
            validate_contract,
        )
    validate_contract(contract, root=root)


def _candidate_binding(
    contract: dict[str, Any],
    candidate_id: str,
) -> dict[str, Any]:
    rows = contract.get("candidateBindings")
    _require(isinstance(rows, list), "Candidate bindings are missing")
    matches = [
        row
        for row in rows
        if isinstance(row, dict) and row.get("candidateId") == candidate_id
    ]
    _require(
        len(matches) == 1,
        "Candidate must have exactly one contract binding",
    )
    row = matches[0]
    _require(
        _is_sha256(row.get("candidateIdentitySha256"))
        and row.get("staticDisposition") == "admit-diagnostic-only"
        and row.get("currentMaterializationAuthorized") is False
        and row.get("currentExecutionAuthorized") is False
        and row.get("currentModelDispatchAuthorized") is False,
        "Candidate static binding drifted",
    )
    return row


def _parent_candidate(
    *,
    root: Path,
    candidate_id: str,
) -> dict[str, Any]:
    parent_path = _safe_repository_file(
        root,
        PARENT_PROTOCOL_PATH,
        label="Historical parent protocol",
    )
    parent = json.loads(parent_path.read_text(encoding="utf-8"))
    matches = [
        item
        for item in parent.get("candidates", [])
        if isinstance(item, dict) and item.get("candidateId") == candidate_id
    ]
    _require(
        len(matches) == 1,
        "Parent protocol candidate binding drifted",
    )
    return matches[0]


def _validate_root_pair(snapshot: dict[str, Any]) -> dict[str, Path]:
    roots: dict[str, Path] = {}
    for field in ("controlRoot", "trialRoot"):
        value = snapshot.get(field)
        _require(
            isinstance(value, str) and Path(value).is_absolute(),
            f"{field} must be an absolute existing directory",
        )
        lexical = Path(value)
        _require(
            ".." not in lexical.parts and "." not in lexical.parts,
            f"{field} must not contain traversal components",
        )
        current = Path(lexical.anchor)
        for part in lexical.parts[1:]:
            current = current / part
            is_junction = bool(
                getattr(current, "is_junction", lambda: False)()
            )
            _require(
                not current.is_symlink() and not is_junction,
                f"{field} and all ancestors must not be links",
            )
        _require(
            not lexical.is_symlink()
            and not bool(getattr(lexical, "is_junction", lambda: False)()),
            f"{field} must not be a link",
        )
        try:
            resolved = lexical.resolve(strict=True)
        except OSError:
            raise BundleContractError(
                f"{field} must be an absolute existing directory"
            ) from None
        _require(
            resolved.is_dir(),
            f"{field} must be an absolute existing directory",
        )
        roots[field] = resolved
    control = roots["controlRoot"]
    trial = roots["trialRoot"]
    overlaps = False
    for parent, child in ((control, trial), (trial, control)):
        try:
            child.relative_to(parent)
        except ValueError:
            continue
        overlaps = True
    _require(
        not overlaps,
        "controlRoot and trialRoot must be disjoint",
    )
    return roots


def _normalized_posix_relative_path(value: Any, *, label: str) -> str:
    _require(
        isinstance(value, str)
        and value
        and "\\" not in value,
        f"{label} must be a normalized POSIX relative path",
    )
    parsed = PurePosixPath(value)
    _require(
        not parsed.is_absolute()
        and ".." not in parsed.parts
        and "." not in parsed.parts
        and parsed.as_posix() == value,
        f"{label} must be a normalized POSIX relative path",
    )
    return value


def _resolve_control_source_file(
    control_root: Path,
    relative: str,
) -> Path:
    current = control_root
    for part in PurePosixPath(relative).parts:
        current = current / part
        is_junction = bool(
            getattr(current, "is_junction", lambda: False)()
        )
        _require(
            not current.is_symlink() and not is_junction,
            "Snapshot source path must not traverse a link",
        )
    try:
        resolved = current.resolve(strict=True)
        resolved.relative_to(control_root)
    except (OSError, ValueError):
        raise BundleContractError(
            "Snapshot source file escapes controlRoot or is missing"
        ) from None
    _require(
        resolved.is_file(),
        "Snapshot source path must resolve to a file",
    )
    return resolved


def _validate_source_files(
    value: Any,
    *,
    label: str,
    control_root: Path,
    expected_candidate_files: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    _require(isinstance(value, list) and value, f"{label} are missing")
    result: list[dict[str, Any]] = []
    normalized_paths: set[str] = set()
    for item in value:
        _require(
            isinstance(item, dict)
            and set(item) == {"path", "bytes", "sha256"},
            f"{label} entry shape drifted",
        )
        path_text = _normalized_posix_relative_path(
            item.get("path"),
            label=f"{label} path",
        )
        collision_key = path_text.casefold()
        _require(
            collision_key not in normalized_paths,
            f"{label} paths must be unique relative paths",
        )
        _require(
            isinstance(item.get("bytes"), int)
            and not isinstance(item.get("bytes"), bool)
            and item["bytes"] >= 0
            and _is_sha256(item.get("sha256")),
            f"{label} digest metadata is invalid",
        )
        path = _resolve_control_source_file(control_root, path_text)
        _require(
            path.stat().st_size == item["bytes"]
            and file_sha256(path) == item["sha256"],
            f"{label} bytes do not match the control-root snapshot",
        )
        normalized_paths.add(collision_key)
        result.append(item)
    expected = [
        {
            "path": item["path"],
            "bytes": item["bytes"],
            "sha256": item["sha256"],
        }
        for item in expected_candidate_files
    ]
    _require(
        result == expected,
        "Snapshot source file set does not equal the parent candidate file set",
    )
    return result


def _validate_snapshot(
    snapshot: dict[str, Any],
    contract: dict[str, Any],
    candidate: dict[str, Any],
    parent_candidate: dict[str, Any],
) -> tuple[datetime, str]:
    snapshot_contract = contract["sourceSnapshotContract"]
    _require(
        set(snapshot) == set(snapshot_contract["requiredFields"]),
        "Source snapshot field set drifted",
    )
    _require(
        snapshot.get("schema") == snapshot_contract["schema"]
        and isinstance(snapshot.get("id"), str)
        and bool(snapshot["id"])
        and snapshot.get("candidateId") == candidate["candidateId"]
        and snapshot.get("candidateIdentitySha256")
        == candidate["candidateIdentitySha256"],
        "Source snapshot identity drifted",
    )
    captured_at = _parse_time(
        snapshot.get("capturedAt"),
        label="snapshot capturedAt",
    )
    roots = _validate_root_pair(snapshot)
    _validate_source_files(
        snapshot.get("sourceFiles"),
        label="Snapshot source files",
        control_root=roots["controlRoot"],
        expected_candidate_files=parent_candidate["files"],
    )
    return captured_at, canonical_sha256(snapshot)


def _validate_preflight(
    preflight: dict[str, Any],
    contract: dict[str, Any],
    candidate: dict[str, Any],
    snapshot: dict[str, Any],
    snapshot_sha256: str,
    captured_at: datetime,
    *,
    now: datetime,
) -> tuple[datetime, str]:
    preflight_contract = contract["freshPreflightContract"]
    _require(
        set(preflight) == set(preflight_contract["requiredFields"]),
        "Fresh preflight field set drifted",
    )
    _require(
        preflight.get("schema") == preflight_contract["schema"]
        and isinstance(preflight.get("id"), str)
        and bool(preflight["id"])
        and preflight.get("candidateId") == candidate["candidateId"]
        and preflight.get("candidateIdentitySha256")
        == candidate["candidateIdentitySha256"]
        and preflight.get("sourceSnapshotManifestSha256")
        == snapshot_sha256,
        "Fresh preflight identity binding drifted",
    )
    _require(
        preflight.get("sourceFiles") == snapshot.get("sourceFiles"),
        "Fresh preflight source-file binding drifted",
    )
    toolchain = preflight.get("toolchain")
    required_toolchain = set(preflight_contract["toolchainFields"])
    _require(
        isinstance(toolchain, dict)
        and set(toolchain) == required_toolchain,
        "Fresh preflight toolchain field set drifted",
    )
    for field in required_toolchain - {
        "codexCliVersion",
        "expectedAppServerInterface",
    }:
        _require(
            _is_sha256(toolchain.get(field)),
            f"Fresh preflight toolchain digest is invalid: {field}",
        )
    _require(
        isinstance(toolchain.get("codexCliVersion"), str)
        and bool(toolchain["codexCliVersion"])
        and toolchain.get("expectedAppServerInterface")
        == "Codex app-server",
        "Fresh preflight toolchain identity drifted",
    )
    _require(
        preflight.get("freshForDispatch") is True
        and preflight.get("freshRevalidationStillRequiredAtDispatch") is False,
        "Fresh preflight declared freshness drifted",
    )
    for field in (
        "candidateMaterialized",
        "candidateInstructionExecuted",
        "appServerStarted",
        "threadStarted",
        "turnStarted",
        "modelRequestSent",
    ):
        _require(
            preflight.get(field) is False,
            f"Fresh preflight unexpectedly records execution: {field}",
        )
    observed_at = _parse_time(
        preflight.get("observedAt"),
        label="preflight observedAt",
    )
    _require(
        captured_at <= observed_at <= now,
        "Fresh preflight time order drifted",
    )
    _require(
        (observed_at - captured_at).total_seconds()
        <= preflight_contract["maximumSnapshotToPreflightSeconds"],
        "Source snapshot exceeds the maximum preflight interval",
    )
    maximum_age = preflight_contract["maximumAgeSeconds"]
    _require(
        (now - observed_at).total_seconds() <= maximum_age,
        "Fresh preflight exceeds the maximum age",
    )
    return observed_at, canonical_sha256(preflight)


def _validate_ledger_authority(
    ledger_authority: dict[str, Any],
    contract: dict[str, Any],
    *,
    now: datetime,
) -> tuple[datetime, str]:
    expected_keys = {
        "schema",
        "id",
        "experimentId",
        "authorityId",
        "candidateIds",
        "authorityScope",
        "issuedAt",
        "liveLedgerCreated",
        "reservationCreated",
    }
    _require(
        set(ledger_authority) == expected_keys,
        "Ledger authority field set drifted",
    )
    authority_contract = contract["ledgerAuthorityContract"]
    _require(
        ledger_authority.get("schema") == authority_contract["schema"]
        and isinstance(ledger_authority.get("id"), str)
        and bool(ledger_authority["id"])
        and isinstance(ledger_authority.get("authorityId"), str)
        and bool(ledger_authority["authorityId"])
        and ledger_authority.get("experimentId")
        == authority_contract["experimentId"]
        and ledger_authority.get("candidateIds")
        == authority_contract["candidateIds"]
        and ledger_authority.get("authorityScope")
        == authority_contract["authorityScope"]
        and ledger_authority.get("liveLedgerCreated") is False
        and ledger_authority.get("reservationCreated") is False,
        "Ledger authority boundary drifted",
    )
    issued_at = _parse_time(
        ledger_authority.get("issuedAt"),
        label="ledger authority issuedAt",
    )
    _require(
        issued_at <= now,
        "Ledger authority cannot be issued in the future",
    )
    _require(
        (now - issued_at).total_seconds()
        <= authority_contract["maximumAuthorityAgeSeconds"],
        "Ledger authority exceeds the maximum age",
    )
    return issued_at, canonical_sha256(ledger_authority)


def _validate_grant(
    grant: dict[str, Any],
    contract: dict[str, Any],
    candidate: dict[str, Any],
    *,
    root: Path,
    snapshot_sha256: str,
    preflight_sha256: str,
    ledger_authority_sha256: str,
    ledger_issued_at: datetime,
    captured_at: datetime,
    observed_at: datetime,
    now: datetime,
) -> tuple[datetime, datetime]:
    grant_contract = contract["separateAuthorityGrantContract"]
    _require(
        set(grant) == set(grant_contract["requiredFields"]),
        "Authority grant field set drifted",
    )
    _require(
        grant.get("schema") == grant_contract["schema"]
        and grant.get("kind") == grant_contract["kind"]
        and isinstance(grant.get("id"), str)
        and bool(grant["id"])
        and isinstance(grant.get("authorityEvidenceLocator"), str)
        and bool(grant["authorityEvidenceLocator"]),
        "Authority grant identity drifted",
    )
    _require(
        any(
            grant["authorityEvidenceLocator"].startswith(prefix)
            for prefix in grant_contract[
                "authorityEvidenceLocatorPrefixes"
            ]
        ),
        "Authority grant locator is not independently bound",
    )
    _require(
        grant.get("candidateId") == candidate["candidateId"]
        and grant.get("candidateIdentitySha256")
        == candidate["candidateIdentitySha256"],
        "Authority grant candidate binding drifted",
    )
    contract_path = _safe_repository_file(
        root,
        CONTRACT_PATH.as_posix(),
        label="Successor contract",
    )
    _require(
        grant.get("successorContractSha256") == file_sha256(contract_path)
        and grant.get("parentProtocolSha256")
        == next(
            row["sha256"]
            for row in contract["sourceBindings"]
            if row["path"] == PARENT_PROTOCOL_PATH
        )
        and grant.get("freshPreflightSha256") == preflight_sha256
        and grant.get("sourceSnapshotManifestSha256") == snapshot_sha256
        and grant.get("staticAdmissionDecisionSha256")
        == candidate["staticAdmissionSha256"]
        and grant.get("ledgerAuthoritySha256")
        == ledger_authority_sha256,
        "Authority grant digest binding drifted",
    )
    _require(
        grant.get("authorizedEffects")
        == grant_contract["authorizedEffects"]
        and grant.get("hostBinding") == grant_contract["hostBinding"]
        and grant.get("maximumDispatches")
        == grant_contract["maximumDispatches"]
        and grant.get("replacementAllowed")
        is grant_contract["replacementAllowed"]
        and grant.get("comparisonAllowed")
        is grant_contract["comparisonAllowed"]
        and grant.get("formalAcceptanceContribution")
        is grant_contract["formalAcceptanceContribution"]
        and grant.get("portfolioMutationAllowed")
        is grant_contract["portfolioMutationAllowed"],
        "Authority grant scope drifted",
    )
    issued_at = _parse_time(grant.get("issuedAt"), label="grant issuedAt")
    valid_from = _parse_time(
        grant.get("validFrom"),
        label="grant validFrom",
    )
    valid_until = _parse_time(
        grant.get("validUntil"),
        label="grant validUntil",
    )
    source_revalidated_at = _parse_time(
        grant.get("sourceRevalidatedAt"),
        label="grant sourceRevalidatedAt",
    )
    _require(
        ledger_issued_at
        <= captured_at
        <= observed_at
        <= issued_at
        <= valid_from
        <= now
        < valid_until
        and source_revalidated_at == observed_at,
        "Authority grant time binding drifted",
    )
    _require(
        (valid_until - valid_from).total_seconds()
        <= grant_contract["maximumTtlSeconds"],
        "Authority grant TTL exceeds the maximum",
    )
    return valid_from, valid_until


def build_offline_dispatch_bundle(
    *,
    candidate_id: str,
    source_snapshot_manifest: dict[str, Any],
    fresh_preflight: dict[str, Any],
    ledger_authority: dict[str, Any],
    separate_authority_grant: dict[str, Any] | None,
    now: datetime,
    root: Path = ROOT,
) -> dict[str, Any]:
    """Validate supplied inputs and return a deterministic offline decision."""

    _require(now.tzinfo is not None, "Injected now must include an offset")
    root = root.resolve()
    contract = load_contract(root)
    _validate_full_contract(contract, root=root)
    candidate = _candidate_binding(contract, candidate_id)
    if separate_authority_grant is None:
        result: dict[str, Any] = {
            "schema": 1,
            "id": "tdd-noncomparative-dispatch-offline-bundle-v2",
            "candidateId": candidate_id,
            "candidateIdentitySha256": candidate[
                "candidateIdentitySha256"
            ],
            "successorContractSha256": file_sha256(root / CONTRACT_PATH),
            "parentProtocolSha256": file_sha256(
                root / PARENT_PROTOCOL_PATH
            ),
            "staticAdmissionDecisionSha256": candidate[
                "staticAdmissionSha256"
            ],
            "decision": contract["controlBundleContract"][
                "missingAuthorityGrantDecision"
            ],
            "reason": "independent-separate-authority-grant-is-missing",
            "candidateMaterialized": False,
            "appServerStarted": False,
            "modelRequestSent": False,
            "liveDispatchEligible": False,
            "authorityAuthenticityVerified": False,
            "clockAuthorityVerified": False,
            "toolchainAuthenticityVerified": False,
        }
        result["bundleSha256"] = canonical_sha256(result)
        return result
    parent_candidate = _parent_candidate(
        root=root,
        candidate_id=candidate_id,
    )
    captured_at, snapshot_sha256 = _validate_snapshot(
        source_snapshot_manifest,
        contract,
        candidate,
        parent_candidate,
    )
    observed_at, preflight_sha256 = _validate_preflight(
        fresh_preflight,
        contract,
        candidate,
        source_snapshot_manifest,
        snapshot_sha256,
        captured_at,
        now=now,
    )
    ledger_issued_at, ledger_sha256 = _validate_ledger_authority(
        ledger_authority,
        contract,
        now=now,
    )
    valid_from, valid_until = _validate_grant(
        separate_authority_grant,
        contract,
        candidate,
        root=root,
        snapshot_sha256=snapshot_sha256,
        preflight_sha256=preflight_sha256,
        ledger_authority_sha256=ledger_sha256,
        ledger_issued_at=ledger_issued_at,
        captured_at=captured_at,
        observed_at=observed_at,
        now=now,
    )
    result = {
        "schema": 1,
        "id": "tdd-noncomparative-dispatch-offline-bundle-v2",
        "candidateId": candidate_id,
        "decision": contract["controlBundleContract"][
            "validOfflineBundleDecision"
        ],
        "successorContractSha256": file_sha256(root / CONTRACT_PATH),
        "parentProtocolSha256": file_sha256(root / PARENT_PROTOCOL_PATH),
        "candidateIdentitySha256": candidate["candidateIdentitySha256"],
        "staticAdmissionDecisionSha256": candidate[
            "staticAdmissionSha256"
        ],
        "sourceSnapshotManifestSha256": snapshot_sha256,
        "freshPreflightSha256": preflight_sha256,
        "ledgerAuthoritySha256": ledger_sha256,
        "authorityGrantSha256": canonical_sha256(
            separate_authority_grant
        ),
        "authorityWindow": {
            "validFrom": valid_from.isoformat(),
            "validUntil": valid_until.isoformat(),
        },
        "evaluatedAt": now.isoformat(),
        "clockClass": "caller-injected-untrusted",
        "candidateMaterialized": False,
        "appServerStarted": False,
        "modelRequestSent": False,
        "liveDispatchEligible": False,
        "formalAcceptanceContribution": False,
        "authorityAuthenticityVerified": False,
        "clockAuthorityVerified": False,
        "toolchainAuthenticityVerified": False,
        "unresolvedLiveGates": [
            "independent-authority-authenticity",
            "trusted-runtime-clock",
            "toolchain-authenticity",
            "live-ledger-authority-and-reservation",
            "diagnostic-runner-or-shared-transport",
            "closeable-app-server-owner",
            "cross-process-exclusion-and-crash-recovery",
        ],
    }
    result["bundleSha256"] = canonical_sha256(result)
    return result


def current_repository_decision(root: Path = ROOT) -> dict[str, Any]:
    """Return the current static decision without constructing live inputs."""

    root = root.resolve()
    contract = load_contract(root)
    _validate_full_contract(contract, root=root)
    return {
        "schema": 1,
        "contractId": contract["id"],
        "status": contract["status"],
        "decision": contract["decision"]["currentOfflineDecision"],
        "currentLiveDispatchEligible": False,
        "candidateMaterialized": False,
        "appServerStarted": False,
        "modelRequestSent": False,
        "nextBoundedAction": contract["decision"]["nextBoundedAction"],
    }


def main() -> int:
    print(
        json.dumps(
            current_repository_decision(ROOT),
            indent=2,
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
