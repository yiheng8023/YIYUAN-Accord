from __future__ import annotations

import copy
import hashlib
import json
import os
import shutil
import subprocess
import tempfile
import uuid
from unittest import mock
from pathlib import Path

from scripts.harness_decision_packet import strict_json_equal
from scripts.program_acceptance_authority_v2 import (
    AcceptanceAuthorityError,
    ZERO_EXECUTION_COUNTERS,
    assessment_inventory,
    binding_for_bytes,
    build_candidate_program_plan_v2,
    build_evidence_snapshot_v2,
    build_rollback_receipt,
    build_selector,
    build_structural_snapshot_v2,
    build_transition_receipt,
    canonical_file_bytes,
    file_sha256,
    resolve_current_authority,
    resolve_historical_authority,
    validate_transition_receipt,
    validate_authority_snapshot,
    validate_legacy_locks,
    LEGACY_LOCKS,
)
from scripts.program_acceptance_migration_inventory import (
    LEGACY_ACCEPTANCE_SEARCH_PATTERNS,
    MIGRATION_INVENTORY_PATH,
    load_migration_inventory,
    validate_migration_inventory,
)


FIXTURE_ROOT = Path("tests/fixtures/program-acceptance-authority-v2-rehearsal")
PRODUCTION_AUTHORITY_ROOT = Path("registry/program-acceptance-authority")
REHEARSAL_SELECTOR_PATH = Path("program-acceptance-authority/current.json")
RECORD_PATH = Path("registry/program-acceptance-authority-v2-zero-model-rehearsal-2026-08-10.json")
_BUNDLE_PATHS = (
    Path("curation-program-plan-v2.json"),
    Path("snapshots/v2/g000001.json"),
    Path("snapshots/v2/g000002.json"),
    Path("transitions/g000000-to-g000001.json"),
    Path("transitions/g000001-to-g000002.json"),
    Path("transitions/g000002-to-g000001-rollback.json"),
    Path("selectors/current-g000002.json"),
    Path("selectors/current-g000001-rollback.json"),
)
_STATUS = "verified-zero-model-versioning-and-migration-rehearsal-only"
MANIFEST_EVIDENCE_SOURCE_PATH = Path("registry/harness-decision-packet-thirteen-scenario-manifest-poc-2026-08-09.json")
MANIFEST_EVIDENCE_SOURCE_SHA256 = "b7a00f43b37d47d1d620292e7f5e28ee438821c145079507ec12b011ed638be1"
_ZERO_CLAIMS = {
    "provesBehavior": False,
    "provesValue": False,
    "provesCrossHostPortability": False,
    "provesProductionReadiness": False,
    "provesReleaseEligibility": False,
    "provesResidualGap": False,
    "provesOverallCloseout": False,
}
# This is deliberately separate from the executable matrix below: the record
# validates this ordered authority rather than accepting a self-reported list.
REQUIRED_FAILURE_CASES: tuple[tuple[str, str], ...] = (
    ("legacy-authority-drift", "legacy-authority-drift"),
    ("legacy-program-plan-drift", "legacy-program-plan-drift"),
    ("legacy-packet-fixture-drift", "legacy-packet-fixture-drift"),
    ("legacy-manifest-fixture-drift", "legacy-manifest-fixture-drift"),
    ("inventory-missing", "migration-inventory-incomplete"),
    ("inventory-invalid-class", "migration-consumer-class-invalid"),
    ("inventory-historical-repoint", "acceptance-historical-consumer-repointed"),
    ("inventory-current-bypass", "acceptance-current-consumer-legacy-bypass"),
    ("inventory-neutral-path", "acceptance-neutral-consumer-path-owned"),
    ("authority-schema-bool", "acceptance-authority-schema-invalid"),
    ("authority-generation-bool", "acceptance-authority-generation-invalid"),
    ("authority-series", "acceptance-authority-series-invalid"),
    ("authority-predecessor", "acceptance-authority-predecessor-mismatch"),
    ("program-plan-binding", "acceptance-program-plan-binding-drift"),
    ("structural-overreach", "acceptance-structural-migration-overreach"),
    ("inventory-count", "acceptance-inventory-count-drift"),
    ("evidence-source-missing", "acceptance-evidence-source-missing"),
    ("evidence-source-drift", "acceptance-evidence-source-drift"),
    ("evidence-link-asymmetric", "acceptance-evidence-link-asymmetric"),
    ("assessment-promotion", "acceptance-assessment-promotion-forbidden"),
    ("evidence-id-duplicate", "acceptance-evidence-id-duplicate"),
    ("evidence-registration-overreach", "acceptance-evidence-registration-overreach"),
    ("selector-escape", "acceptance-selector-target-invalid"),
    ("receipt-invalid", "acceptance-transition-receipt-invalid"),
    ("receipt-chain", "acceptance-transition-chain-broken"),
    ("receipt-type", "acceptance-transition-type-mismatch"),
    ("receipt-side-effect-counter", "acceptance-side-effect-counter-nonzero"),
    ("rollback-invalid", "acceptance-rollback-receipt-invalid"),
    ("rollback-target", "acceptance-rollback-target-not-ancestor"),
    ("atomic-directory-target", "acceptance-atomic-output-preserved"),
    ("cleanup-fault", "acceptance-rehearsal-cleanup-incomplete"),
    ("protected-output-root", "acceptance-activation-not-authorized"),
    ("inventory-duplicate-row", "migration-inventory-incomplete"),
    ("inventory-extra-row", "migration-inventory-incomplete"),
    ("inventory-reordered-rows", "migration-inventory-incomplete"),
    ("inventory-bool-line", "migration-consumer-class-invalid"),
    ("inventory-float-line", "migration-consumer-class-invalid"),
    ("selector-absolute", "acceptance-selector-target-invalid"),
    ("cli-protected-output", "acceptance-activation-not-authorized"),
    ("authority-schema-alias", "acceptance-authority-schema-invalid"),
    ("authority-generation-alias", "acceptance-authority-generation-invalid"),
    ("authority-predecessor-path", "acceptance-authority-predecessor-mismatch"),
    ("authority-predecessor-digest", "acceptance-authority-predecessor-mismatch"),
    ("program-plan-id", "acceptance-program-plan-binding-drift"),
    ("program-plan-path", "acceptance-program-plan-binding-drift"),
    ("structural-objective", "acceptance-structural-migration-overreach"),
    ("structural-criterion", "acceptance-structural-migration-overreach"),
    ("structural-verification", "acceptance-structural-migration-overreach"),
    ("receipt-from-binding", "acceptance-transition-receipt-invalid"),
    ("receipt-to-binding", "acceptance-transition-receipt-invalid"),
    ("receipt-generation-step", "acceptance-transition-chain-broken"),
    ("inventory-stale-line", "migration-inventory-incomplete"),
    ("inventory-raw-id", "migration-consumer-class-invalid"),
    ("inventory-raw-path-outside-host", "migration-consumer-class-invalid"),
    ("atomic-sentinel-preserved", "acceptance-atomic-output-preserved"),
    ("selector-snapshot-digest", "acceptance-selector-target-invalid"),
    ("selector-receipt-digest", "acceptance-transition-receipt-invalid"),
    ("selector-plan-digest", "acceptance-selector-target-invalid"),
    ("selector-mode", "acceptance-selector-target-invalid"),
    ("selector-activation-bool", "acceptance-activation-not-authorized"),
    ("selector-counter-float", "acceptance-side-effect-counter-nonzero"),
    ("selector-parent-escape", "acceptance-selector-target-invalid"),
    ("selector-symlink-escape", "acceptance-selector-target-invalid"),
    ("selector-plan-path-rewrite", "acceptance-selector-target-invalid"),
    ("snapshot-byte-fork", "acceptance-transition-chain-broken"),
    ("receipt-byte-fork", "acceptance-transition-receipt-invalid"),
    ("rollback-other-series", "acceptance-rollback-target-not-ancestor"),
    ("rollback-rewritten-same-generation", "acceptance-rollback-target-not-ancestor"),
    ("duplicate-introducing-receipt", "acceptance-transition-chain-broken"),
    ("structural-preexisting-evidence", "acceptance-evidence-link-asymmetric"),
    ("receipt-delta", "acceptance-transition-receipt-invalid"),
    ("evidence-manifest-row-missing", "acceptance-evidence-source-missing"),
    ("evidence-manifest-row-wrong", "acceptance-evidence-source-drift"),
    ("evidence-manifest-row-extra", "acceptance-evidence-link-asymmetric"),
    ("evidence-link-wrong", "acceptance-evidence-link-asymmetric"),
    ("assessment-bool-alias", "acceptance-inventory-count-drift"),
    ("assessment-float-alias", "acceptance-inventory-count-drift"),
    ("evidence-criterion-count", "acceptance-structural-migration-overreach"),
    ("assessment-int-alias", "acceptance-inventory-count-drift"),
    ("evidence-unrelated-objective", "acceptance-evidence-registration-overreach"),
    ("evidence-unrelated-verification", "acceptance-structural-migration-overreach"),
    ("evidence-unrelated-criterion", "acceptance-evidence-registration-overreach"),
    ("evidence-unrelated-evidence", "acceptance-evidence-link-asymmetric"),
    ("reciprocal-link-missing", "acceptance-evidence-link-asymmetric"),
    ("reciprocal-link-extra", "acceptance-evidence-link-asymmetric"),
)
REQUIRED_TYPED_CODES: tuple[str, ...] = (
    "legacy-authority-drift", "legacy-program-plan-drift", "legacy-packet-fixture-drift", "legacy-manifest-fixture-drift",
    "migration-inventory-incomplete", "migration-consumer-class-invalid", "acceptance-authority-schema-invalid",
    "acceptance-authority-series-invalid", "acceptance-authority-generation-invalid", "acceptance-authority-predecessor-mismatch",
    "acceptance-program-plan-binding-drift", "acceptance-selector-target-invalid", "acceptance-transition-receipt-invalid",
    "acceptance-transition-chain-broken", "acceptance-transition-type-mismatch", "acceptance-structural-migration-overreach",
    "acceptance-evidence-registration-overreach", "acceptance-assessment-promotion-forbidden", "acceptance-inventory-count-drift",
    "acceptance-evidence-link-asymmetric", "acceptance-evidence-id-duplicate", "acceptance-evidence-source-missing",
    "acceptance-evidence-source-drift", "acceptance-historical-consumer-repointed", "acceptance-current-consumer-legacy-bypass",
    "acceptance-neutral-consumer-path-owned", "acceptance-rollback-receipt-invalid", "acceptance-rollback-target-not-ancestor",
    "acceptance-atomic-output-preserved", "acceptance-rehearsal-cleanup-incomplete", "acceptance-activation-not-authorized",
    "acceptance-side-effect-counter-nonzero",
)
_CODE_ORDER = {code: index for index, code in enumerate(REQUIRED_TYPED_CODES)}
REQUIRED_FAILURE_CASES = tuple(sorted(REQUIRED_FAILURE_CASES, key=lambda item: (_CODE_ORDER[item[1]], item[0])))
_RECORD_DIGEST_PATHS = (
    Path("schemas/program-acceptance-authority-v2.schema.json"),
    Path("schemas/program-acceptance-current-selector-v1.schema.json"),
    Path("schemas/program-acceptance-transition-receipt-v1.schema.json"),
    Path("schemas/program-acceptance-migration-inventory-v1.schema.json"),
    Path("scripts/program_acceptance_authority_v2.py"),
    Path("scripts/program_acceptance_migration_inventory.py"),
    Path("scripts/program_acceptance_authority_v2_rehearsal.py"),
    Path("scripts/build_program_acceptance_authority_v2_rehearsal.py"),
    Path("scripts/validate_program_acceptance_authority_v2_rehearsal.py"),
    Path("tests/test_program_acceptance_authority_v2.py"),
    Path("tests/test_program_acceptance_migration_inventory.py"),
    Path("tests/test_program_acceptance_authority_v2_rehearsal.py"),
    Path("docs/superpowers/specs/2026-08-10-program-acceptance-authority-v2-design.md"),
    Path("docs/superpowers/plans/2026-08-10-program-acceptance-authority-v2-rehearsal.md"),
    Path("docs/strategy/PROGRAM-ACCEPTANCE-AUTHORITY-V2-ZERO-MODEL-REHEARSAL-2026-08-10.md"),
    MIGRATION_INVENTORY_PATH,
    MANIFEST_EVIDENCE_SOURCE_PATH,
    *tuple(FIXTURE_ROOT / relative for relative in _BUNDLE_PATHS),
)


def _read_json(path: Path) -> dict[str, object]:
    try:
        value = json.loads(path.read_bytes())
    except (OSError, json.JSONDecodeError) as error:
        raise AcceptanceAuthorityError(
            "acceptance-rehearsal-bundle-invalid", "Rehearsal source cannot be read."
        ) from error
    if not isinstance(value, dict):
        raise AcceptanceAuthorityError(
            "acceptance-rehearsal-bundle-invalid", "Rehearsal source must be an object."
        )
    return value


def _validate_manifest_evidence_source(repo_root: Path, g2: dict[str, object]) -> None:
    try:
        data = (repo_root / MANIFEST_EVIDENCE_SOURCE_PATH).read_bytes()
        source = json.loads(data)
    except (OSError, json.JSONDecodeError) as error:
        raise AcceptanceAuthorityError("acceptance-evidence-source-missing", "Registered manifest evidence source cannot be reopened.") from error
    if not isinstance(source, dict) or hashlib.sha256(data).hexdigest() != MANIFEST_EVIDENCE_SOURCE_SHA256:
        raise AcceptanceAuthorityError("acceptance-evidence-source-drift", "Registered manifest evidence source digest drifted.")
    row = next((item for item in g2.get("evidence", []) if isinstance(item, dict) and item.get("id") == "evidence.harness-decision-packet-thirteen-scenario-manifest-poc-2026-08-09"), None)
    if row is None:
        raise AcceptanceAuthorityError("acceptance-evidence-source-missing", "Candidate g000002 omits manifest evidence.")
    if row.get("path") != MANIFEST_EVIDENCE_SOURCE_PATH.as_posix() or source.get("id") != "harness-decision-packet-thirteen-scenario-manifest-poc-2026-08-09":
        raise AcceptanceAuthorityError("acceptance-evidence-source-drift", "Candidate evidence row does not bind the reopened source.")


def _binding(schema: int, document: dict[str, object], path: Path, data: bytes) -> dict[str, object]:
    generation = document.get("generation") if schema == 2 else None
    return binding_for_bytes(
        authority_schema=schema,
        authority_id=str(document.get("id")),
        generation=generation if isinstance(generation, int) else (1 if schema == 2 else None),
        path=path.as_posix(),
        data=data,
    )


def _fixture_bytes(repo_root: Path, relative: Path, data: bytes) -> None:
    expected = (repo_root / FIXTURE_ROOT / relative).read_bytes()
    if not strict_json_equal(data, expected):
        raise AcceptanceAuthorityError(
            "acceptance-rehearsal-bundle-invalid", "Rehearsal builder drifted from its checked fixture.", path=relative.as_posix()
        )


def build_rehearsal_bundle(repo_root: Path) -> dict[str, bytes]:
    """Rebuild all eight candidate bytes from locked v1 inputs and checked builders."""

    repo_root = repo_root.resolve()
    locks = validate_legacy_locks(repo_root)
    legacy = _read_json(repo_root / locks["acceptance"]["path"])
    legacy_plan = _read_json(repo_root / locks["programPlan"]["path"])
    legacy_binding = {**locks["acceptance"], "authoritySchema": 1, "generation": None}
    legacy_plan_binding = {**locks["programPlan"], "authoritySchema": 1, "generation": None}

    plan = build_candidate_program_plan_v2(legacy_plan)
    plan_path = Path("curation-program-plan-v2.json")
    plan_bytes = canonical_file_bytes(plan)
    plan_binding = _binding(2, plan, plan_path, plan_bytes)
    g1 = build_structural_snapshot_v2(
        legacy, predecessor_binding=legacy_binding, program_plan_binding=plan_binding
    )
    g1_path = Path("snapshots/v2/g000001.json")
    g1_bytes = canonical_file_bytes(g1)
    g1_binding = _binding(2, g1, g1_path, g1_bytes)
    g2 = build_evidence_snapshot_v2(g1)
    g2_path = Path("snapshots/v2/g000002.json")
    g2_bytes = canonical_file_bytes(g2)
    g2_binding = _binding(2, g2, g2_path, g2_bytes)
    structural = build_transition_receipt(
        "structural-migration", from_snapshot_binding=legacy_binding,
        to_snapshot_binding=g1_binding, from_program_plan_binding=legacy_plan_binding,
        to_program_plan_binding=plan_binding, from_document=legacy, to_document=g1,
    )
    evidence = build_transition_receipt(
        "evidence-registration", from_snapshot_binding=g1_binding,
        to_snapshot_binding=g2_binding, from_program_plan_binding=plan_binding,
        to_program_plan_binding=plan_binding, from_document=g1, to_document=g2,
    )
    rollback = build_rollback_receipt(
        from_snapshot_binding=g2_binding, to_snapshot_binding=g1_binding,
        active_program_plan_binding=plan_binding, ancestor_bindings=[g1_binding],
    )
    structural_path = Path("transitions/g000000-to-g000001.json")
    evidence_path = Path("transitions/g000001-to-g000002.json")
    rollback_path = Path("transitions/g000002-to-g000001-rollback.json")
    structural_bytes = canonical_file_bytes(structural)
    evidence_bytes = canonical_file_bytes(evidence)
    rollback_bytes = canonical_file_bytes(rollback)
    evidence_binding = _binding(1, evidence, evidence_path, evidence_bytes)
    rollback_binding = _binding(1, rollback, rollback_path, rollback_bytes)
    g2_selector_path = Path("selectors/current-g000002.json")
    rollback_selector_path = Path("selectors/current-g000001-rollback.json")
    bundle = {
        plan_path.as_posix(): plan_bytes,
        g1_path.as_posix(): g1_bytes,
        g2_path.as_posix(): g2_bytes,
        structural_path.as_posix(): structural_bytes,
        evidence_path.as_posix(): evidence_bytes,
        rollback_path.as_posix(): rollback_bytes,
        g2_selector_path.as_posix(): canonical_file_bytes(build_selector(
            snapshot_binding=g2_binding, transition_binding=evidence_binding,
            program_plan_binding=plan_binding,
        )),
        rollback_selector_path.as_posix(): canonical_file_bytes(build_selector(
            snapshot_binding=g1_binding, transition_binding=rollback_binding,
            program_plan_binding=plan_binding,
        )),
    }
    if tuple(Path(path) for path in bundle) != _BUNDLE_PATHS:
        raise AcceptanceAuthorityError("acceptance-rehearsal-bundle-invalid", "Rehearsal bundle paths are invalid.")
    for relative in _BUNDLE_PATHS:
        _fixture_bytes(repo_root, relative, bundle[relative.as_posix()])
    return bundle


def _is_within(candidate: Path, container: Path) -> bool:
    try:
        candidate.relative_to(container)
        return True
    except ValueError:
        return False


def _assert_disposable_output(repo_root: Path, output_root: Path) -> tuple[Path, Path]:
    if not isinstance(repo_root, Path) or not isinstance(output_root, Path):
        raise AcceptanceAuthorityError("acceptance-activation-not-authorized", "Rehearsal roots must be paths.")
    try:
        resolved_repo = repo_root.resolve(strict=True)
        parent = output_root.parent.resolve(strict=True)
        resolved_output = parent / output_root.name
        production = (resolved_repo / PRODUCTION_AUTHORITY_ROOT).resolve()
    except (OSError, RuntimeError, ValueError) as error:
        raise AcceptanceAuthorityError("acceptance-activation-not-authorized", "Rehearsal output path is unsafe.") from error
    if output_root.exists() or output_root.is_symlink() or _is_within(resolved_output, resolved_repo) or _is_within(resolved_repo, resolved_output) or _is_within(resolved_output, production) or _is_within(production, resolved_output):
        raise AcceptanceAuthorityError(
            "acceptance-activation-not-authorized", "Production authority output is not authorized.",
            path=PRODUCTION_AUTHORITY_ROOT.as_posix(),
        )
    return resolved_repo, resolved_output


def _write_fsynced(path: Path, data: bytes) -> None:
    with path.open("xb") as handle:
        handle.write(data)
        handle.flush()
        os.fsync(handle.fileno())


def replace_selector_atomically(path: Path, data: bytes) -> None:
    """Replace only a rehearsal selector, preserving an existing target on failure."""

    temporary_name: str | None = None
    try:
        with tempfile.NamedTemporaryFile(
            dir=path.parent, prefix=f".{path.name}.", suffix=".tmp", delete=False
        ) as handle:
            temporary_name = handle.name
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        try:
            os.replace(temporary_name, path)
        except OSError as error:
            raise AcceptanceAuthorityError(
                "acceptance-atomic-output-preserved", "Atomic selector replacement failed; prior output was preserved.",
                path=path.as_posix(),
            ) from error
        temporary_name = None
    finally:
        if temporary_name is not None:
            Path(temporary_name).unlink(missing_ok=True)


def _validate_bundle_bytes(repo_root: Path, root: Path, bundle: dict[str, bytes]) -> None:
    for relative in _BUNDLE_PATHS:
        path = root / relative
        if not path.is_file() or not strict_json_equal(path.read_bytes(), bundle[relative.as_posix()]):
            raise AcceptanceAuthorityError("acceptance-rehearsal-bundle-invalid", "Staged bundle bytes drifted.", path=relative.as_posix())
        _fixture_bytes(repo_root, relative, path.read_bytes())


def _overlay_with_legacy(repo_root: Path, candidate_root: Path, selector_bytes: bytes) -> tuple[tempfile.TemporaryDirectory[str], Path]:
    """Build an isolated resolver root from one candidate directory and frozen v1 files."""

    holder = tempfile.TemporaryDirectory(prefix="acceptance-authority-v2-overlay-")
    overlay = Path(holder.name)
    for relative in _BUNDLE_PATHS:
        source = candidate_root / relative
        target = overlay / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
    for relative, *_ in LEGACY_LOCKS.values():
        target = overlay / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(repo_root / relative, target)
    selector = overlay / REHEARSAL_SELECTOR_PATH
    selector.parent.mkdir(parents=True, exist_ok=True)
    _write_fsynced(selector, selector_bytes)
    return holder, overlay


def _validate_staged_authority(repo_root: Path, stage: Path, bundle: dict[str, bytes]) -> None:
    """Resolve both selectors before publication; bytes alone are not acceptance evidence."""

    _validate_bundle_bytes(repo_root, stage, bundle)
    for selector_name, expected_generation in (
        ("selectors/current-g000002.json", 2),
        ("selectors/current-g000001-rollback.json", 1),
    ):
        holder, overlay = _overlay_with_legacy(repo_root, stage, bundle[selector_name])
        try:
            resolved = resolve_current_authority(overlay, REHEARSAL_SELECTOR_PATH.as_posix())
            if resolved["binding"].get("generation") != expected_generation:
                raise AcceptanceAuthorityError("acceptance-rehearsal-bundle-invalid", "Staged selector resolved an unexpected generation.")
        finally:
            holder.cleanup()


def _cleanup_stage(stage: Path) -> None:
    """Retry only the exact lexical stage directory and fail closed on any residue."""

    if not os.path.lexists(stage):
        return
    _directory_identity(stage)
    first_error: OSError | None = None
    try:
        shutil.rmtree(stage)
    except OSError as error:
        first_error = error
        if not os.path.lexists(stage):
            return
        _directory_identity(stage)
        try:
            shutil.rmtree(stage)
        except OSError as error:
            raise AcceptanceAuthorityError("acceptance-rehearsal-cleanup-incomplete", "Staged rehearsal root could not be removed.") from error
    if os.path.lexists(stage):
        raise AcceptanceAuthorityError("acceptance-rehearsal-cleanup-incomplete", "Staged rehearsal root still exists.")
    if first_error is not None:
        raise AcceptanceAuthorityError("acceptance-rehearsal-cleanup-incomplete", "Staged rehearsal cleanup required a retry.") from first_error


def _write_rehearsal_bundle(repo_root: Path, output_root: Path, bundle: dict[str, bytes]) -> None:
    """Stage/fsync immutable candidate bytes and publish the disposable directory once."""

    repo_root, resolved_output = _assert_disposable_output(repo_root, output_root)
    if set(bundle) != {path.as_posix() for path in _BUNDLE_PATHS}:
        raise AcceptanceAuthorityError("acceptance-rehearsal-bundle-invalid", "Rehearsal bundle shape is invalid.")
    stage = Path(tempfile.mkdtemp(prefix=f".{resolved_output.name}.stage-", dir=resolved_output.parent))
    try:
        for relative in _BUNDLE_PATHS:
            target = stage / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            _write_fsynced(target, bundle[relative.as_posix()])
        _validate_staged_authority(repo_root, stage, bundle)
        os.replace(stage, resolved_output)
    except AcceptanceAuthorityError:
        _cleanup_stage(stage)
        raise
    except OSError as error:
        _cleanup_stage(stage)
        raise AcceptanceAuthorityError("acceptance-rehearsal-output-write-failed", "Rehearsal output could not be written.") from error


def write_rehearsal_bundle(output_root: Path, bundle: dict[str, bytes]) -> None:
    """Public convenience entrypoint bound to this module's repository root."""

    _write_rehearsal_bundle(Path(__file__).resolve().parent.parent, output_root, bundle)


def _directory_identity(path: Path) -> tuple[int, int, int]:
    try:
        status = path.lstat()
    except OSError as error:
        raise AcceptanceAuthorityError("acceptance-rehearsal-cleanup-incomplete", "Disposable output identity cannot be read.") from error
    if not path.is_dir() or path.is_symlink():
        raise AcceptanceAuthorityError("acceptance-rehearsal-cleanup-incomplete", "Disposable output is not a real directory.")
    return (status.st_dev, status.st_ino, status.st_mode)


def _cleanup_disposable(repo_root: Path, output_root: Path, identity: tuple[int, int, int]) -> None:
    _, resolved = _assert_cleanup_target(repo_root, output_root)
    if not os.path.lexists(output_root):
        raise AcceptanceAuthorityError("acceptance-rehearsal-cleanup-incomplete", "Disposable lexical output disappeared before cleanup.")
    quarantine = output_root.parent / f".{output_root.name}.cleanup-{uuid.uuid4().hex}"
    try:
        os.replace(output_root, quarantine)
    except OSError as error:
        raise AcceptanceAuthorityError("acceptance-rehearsal-cleanup-incomplete", "Disposable output cannot be quarantined for cleanup.") from error
    try:
        if _directory_identity(quarantine) != identity:
            raise AcceptanceAuthorityError("acceptance-rehearsal-cleanup-incomplete", "Disposable output identity changed before cleanup.")
        shutil.rmtree(quarantine)
    except OSError as error:
        raise AcceptanceAuthorityError("acceptance-rehearsal-cleanup-incomplete", "Disposable rehearsal root could not be removed.") from error
    if os.path.lexists(quarantine) or os.path.lexists(output_root):
        raise AcceptanceAuthorityError("acceptance-rehearsal-cleanup-incomplete", "Disposable rehearsal root still exists.")


def _assert_cleanup_target(repo_root: Path, output_root: Path) -> tuple[Path, Path]:
    resolved_repo = repo_root.resolve(strict=True)
    try:
        resolved = output_root.resolve(strict=True)
    except (OSError, RuntimeError, ValueError) as error:
        raise AcceptanceAuthorityError("acceptance-rehearsal-cleanup-incomplete", "Disposable output cannot be resolved.") from error
    production = (resolved_repo / PRODUCTION_AUTHORITY_ROOT).resolve()
    if not _is_within(resolved, resolved.parent) or _is_within(resolved, resolved_repo) or _is_within(resolved, production) or _is_within(production, resolved):
        raise AcceptanceAuthorityError("acceptance-rehearsal-cleanup-incomplete", "Cleanup target is not an exact disposable root.")
    return resolved_repo, resolved


def run_rehearsal(repo_root: Path, output_root: Path) -> dict[str, object]:
    """Perform a zero-model candidate build, g2 selection, g1 rollback, and exact cleanup."""

    repo_root, output_root = _assert_disposable_output(repo_root, output_root)
    expected_g2 = _read_json(repo_root / FIXTURE_ROOT / "snapshots/v2/g000002.json")
    _validate_manifest_evidence_source(repo_root, expected_g2)
    inventory = load_migration_inventory(repo_root)
    validate_migration_inventory(repo_root, inventory)
    locks = validate_legacy_locks(repo_root)
    legacy_binding = {**locks["acceptance"], "authoritySchema": 1, "generation": None}
    legacy_plan_binding = {**locks["programPlan"], "authoritySchema": 1, "generation": None}
    resolve_historical_authority(
        repo_root, legacy_binding, frozen_program_plan_binding=legacy_plan_binding
    )
    legacy_before = {name: file_sha256(repo_root, value[0]) for name, value in LEGACY_LOCKS.items()}
    tracked_before = subprocess.run(["git", "-C", str(repo_root), "status", "--porcelain=v1"], check=True, capture_output=True).stdout
    bundle = build_rehearsal_bundle(repo_root)
    expected_acceptance = assessment_inventory(expected_g2)
    expected_target = next((row for row in expected_g2["acceptanceCriteria"] if row.get("id") == "acceptance.decision-ready-consumer-projection"), None)
    if not isinstance(expected_target, dict) or type(expected_target.get("assessment")) is not str:
        raise AcceptanceAuthorityError("acceptance-rehearsal-bundle-invalid", "Candidate target criterion cannot be recomputed.")
    _write_rehearsal_bundle(repo_root, output_root, bundle)
    output_identity = _directory_identity(output_root)
    try:
        g2_selector = bundle["selectors/current-g000002.json"]
        holder, overlay = _overlay_with_legacy(repo_root, output_root, g2_selector)
        try:
            current_g2 = resolve_current_authority(overlay, REHEARSAL_SELECTOR_PATH.as_posix())
        finally:
            holder.cleanup()
        selector_path = output_root / REHEARSAL_SELECTOR_PATH
        selector_path.parent.mkdir(parents=True, exist_ok=True)
        replace_selector_atomically(selector_path, bundle["selectors/current-g000001-rollback.json"])
        holder, overlay = _overlay_with_legacy(repo_root, output_root, selector_path.read_bytes())
        try:
            current_g1 = resolve_current_authority(overlay, REHEARSAL_SELECTOR_PATH.as_posix())
            resolved_g2 = current_g2["authority"]
        finally:
            holder.cleanup()
        acceptance = assessment_inventory(resolved_g2)
        target = next((row for row in resolved_g2["acceptanceCriteria"] if row.get("id") == "acceptance.decision-ready-consumer-projection"), None)
        if current_g2["binding"]["generation"] != 2 or current_g1["binding"]["generation"] != 1 or not strict_json_equal(acceptance, expected_acceptance) or not isinstance(target, dict) or target.get("assessment") != expected_target["assessment"]:
            raise AcceptanceAuthorityError("acceptance-rehearsal-bundle-invalid", "Rehearsal resolution generations drifted.")
    finally:
        if os.path.lexists(output_root):
            _cleanup_disposable(repo_root, output_root, output_identity)
    legacy_after = {name: file_sha256(repo_root, value[0]) for name, value in LEGACY_LOCKS.items()}
    tracked_after = subprocess.run(["git", "-C", str(repo_root), "status", "--porcelain=v1"], check=True, capture_output=True).stdout
    if not strict_json_equal(legacy_before, legacy_after) or not strict_json_equal(tracked_before, tracked_after):
        raise AcceptanceAuthorityError("acceptance-rehearsal-cleanup-incomplete", "Rehearsal changed protected repository state.")
    return {
        "status": _STATUS,
        "highestGeneration": 2,
        "rollbackGeneration": 1,
        "acceptanceInventory": acceptance,
        "executionCounters": copy.deepcopy(ZERO_EXECUTION_COUNTERS),
        "claimBoundary": copy.deepcopy(_ZERO_CLAIMS),
    }


def run_failure_matrix(repo_root: Path) -> list[dict[str, str]]:
    """Run the public failure surfaces used by this disposable proof.

    Task 5's record validator reruns this matrix; each case uses a real public call.
    """

    repo_root = repo_root.resolve()
    results: list[dict[str, str]] = []

    def legacy_mutation(lock_name: str) -> object:
        def invoke() -> None:
            from scripts.program_acceptance_authority_v2 import LEGACY_LOCKS

            with tempfile.TemporaryDirectory(prefix="acceptance-lock-matrix-") as directory:
                copied = Path(directory)
                for relative, *_ in LEGACY_LOCKS.values():
                    target = copied / relative
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(repo_root / relative, target)
                relative = LEGACY_LOCKS[lock_name][0]
                (copied / relative).write_bytes((copied / relative).read_bytes() + b"\n")
                validate_legacy_locks(copied)
        return invoke

    def inventory_mutation(case: str) -> object:
        def invoke() -> None:
            inventory = load_migration_inventory(repo_root)
            rows = inventory["occurrences"]
            assert isinstance(rows, list)
            if case == "missing":
                rows.pop()
            elif case == "invalid-class":
                rows[0]["classification"] = "invalid"
            elif case == "historical-repoint":
                next(row for row in rows if row["classification"] == "A-immutable-historical")["candidateBinding"] = "rehearsal-selector"
            elif case == "current-bypass":
                next(row for row in rows if row["classification"] == "B-current-authority-consumer")["rehearsalAction"] = "legacy-bypass"
            elif case == "neutral-path":
                row = rows[0]
                row["classification"] = "C-version-neutral-component"
            elif case == "duplicate-row":
                rows.append(copy.deepcopy(rows[0]))
            elif case == "extra-row":
                extra = copy.deepcopy(rows[0])
                extra["line"] = 999999
                rows.append(extra)
            elif case == "reordered-rows":
                rows.reverse()
            elif case == "bool-line":
                rows[0]["line"] = True
            elif case == "float-line":
                rows[0]["line"] = 1.0
            elif case == "stale-line":
                rows[0]["lineSha256"] = "0" * 64
            elif case == "raw-id":
                rows[0]["purpose"] = LEGACY_ACCEPTANCE_SEARCH_PATTERNS["legacy-acceptance-id"]
            elif case == "raw-path-outside-host":
                rows[0]["purpose"] = LEGACY_ACCEPTANCE_SEARCH_PATTERNS["legacy-acceptance-path"]
            validate_migration_inventory(repo_root, inventory)
        return invoke

    def manifest_source_mutation(case: str) -> object:
        """Mutate the real evidence source in an isolated Git overlay, then call run_rehearsal."""

        def invoke() -> None:
            with tempfile.TemporaryDirectory(prefix="acceptance-evidence-source-matrix-") as directory:
                clone = Path(directory) / "repository"
                subprocess.run(["git", "clone", "--quiet", "--no-hardlinks", str(repo_root), str(clone)], check=True, capture_output=True)
                source = clone / MANIFEST_EVIDENCE_SOURCE_PATH
                if case == "missing":
                    source.unlink()
                    # The inventory deliberately enumerates Git-tracked files.
                    # Remove only this overlay entry from its temporary index so
                    # that the public run can reach its bound source gate.
                    subprocess.run(["git", "-C", str(clone), "update-index", "--force-remove", MANIFEST_EVIDENCE_SOURCE_PATH.as_posix()], check=True, capture_output=True)
                else:
                    source.write_bytes(source.read_bytes() + b"\n")
                with tempfile.TemporaryDirectory(prefix="acceptance-evidence-output-") as output_parent:
                    run_rehearsal(clone, Path(output_parent) / "rehearsal")
        return invoke

    def nonzero_receipt() -> None:
        receipt = _read_json(repo_root / FIXTURE_ROOT / "transitions/g000001-to-g000002.json")
        g1 = _read_json(repo_root / FIXTURE_ROOT / "snapshots/v2/g000001.json")
        g2 = _read_json(repo_root / FIXTURE_ROOT / "snapshots/v2/g000002.json")
        receipt["executionCounters"]["modelRequestCount"] = 1
        validate_transition_receipt(receipt, from_document=g1, to_document=g2)

    def snapshots() -> tuple[dict[str, object], dict[str, object], dict[str, object]]:
        return (
            _read_json(repo_root / LEGACY_LOCKS["acceptance"][0]),
            _read_json(repo_root / FIXTURE_ROOT / "snapshots/v2/g000001.json"),
            _read_json(repo_root / FIXTURE_ROOT / "snapshots/v2/g000002.json"),
        )

    def snapshot_mutation(case: str) -> object:
        def invoke() -> None:
            legacy, g1, g2 = snapshots()
            plan = copy.deepcopy(g1["programPlanBinding"])
            if case == "schema":
                g1["authoritySchema"] = True
                validate_authority_snapshot(g1, predecessor=legacy, program_plan_binding=plan)
            elif case == "generation":
                g1["generation"] = True
                validate_authority_snapshot(g1, predecessor=legacy, program_plan_binding=plan)
            elif case == "series":
                g1["authoritySeriesId"] = "wrong"
                validate_authority_snapshot(g1, predecessor=legacy, program_plan_binding=plan)
            elif case == "predecessor":
                g1["predecessorBinding"]["id"] = "wrong"
                validate_authority_snapshot(g1, predecessor=legacy, program_plan_binding=plan)
            elif case == "predecessor-path":
                g1["predecessorBinding"]["path"] = "wrong.json"
                validate_authority_snapshot(g1, predecessor=legacy, program_plan_binding=plan)
            elif case == "predecessor-digest":
                g1["predecessorBinding"]["sha256"] = "0" * 64
                validate_authority_snapshot(g1, predecessor=legacy, program_plan_binding=plan)
            elif case == "plan":
                g1["programPlanBinding"]["sha256"] = "0" * 64
                validate_authority_snapshot(g1, predecessor=legacy, program_plan_binding=plan)
            elif case == "plan-id":
                g1["programPlanBinding"]["id"] = "wrong"
                validate_authority_snapshot(g1, predecessor=legacy, program_plan_binding=plan)
            elif case == "plan-path":
                g1["programPlanBinding"]["path"] = "wrong.json"
                validate_authority_snapshot(g1, predecessor=legacy, program_plan_binding=plan)
            elif case == "structural":
                g1["acceptanceCriteria"][0]["statement"] = "rewritten"
                validate_authority_snapshot(g1, predecessor=legacy, program_plan_binding=plan)
            elif case == "structural-objective":
                g1["objectives"][0]["id"] = "objective.rewritten"
                validate_authority_snapshot(g1, predecessor=legacy, program_plan_binding=plan)
            elif case == "structural-criterion":
                g1["acceptanceCriteria"][0]["id"] = "acceptance.rewritten"
                validate_authority_snapshot(g1, predecessor=legacy, program_plan_binding=plan)
            elif case == "structural-verification":
                g1["verifications"][0]["id"] = "verification.rewritten"
                validate_authority_snapshot(g1, predecessor=legacy, program_plan_binding=plan)
            elif case == "structural-evidence":
                g1["evidence"][0]["id"] = "evidence.rewritten"
                validate_authority_snapshot(g1, predecessor=legacy, program_plan_binding=plan)
            elif case == "inventory":
                g1["acceptanceCriteria"][0]["assessment"] = "planned"
                validate_authority_snapshot(g1, predecessor=legacy, program_plan_binding=plan)
            elif case == "missing":
                g2["evidence"] = [row for row in g2["evidence"] if row["id"] != "evidence.harness-decision-packet-thirteen-scenario-manifest-poc-2026-08-09"]
                next(row for row in g2["acceptanceCriteria"] if row["id"] == "acceptance.decision-ready-consumer-projection")["evidenceIds"].remove("evidence.harness-decision-packet-thirteen-scenario-manifest-poc-2026-08-09")
                validate_authority_snapshot(g2, predecessor=g1, program_plan_binding=plan)
            elif case == "manifest-wrong":
                next(row for row in g2["evidence"] if row["id"] == "evidence.harness-decision-packet-thirteen-scenario-manifest-poc-2026-08-09")["path"] = "wrong.json"
                validate_authority_snapshot(g2, predecessor=g1, program_plan_binding=plan)
            elif case == "manifest-extra":
                g2["evidence"].append(copy.deepcopy(g2["evidence"][-1]))
                g2["evidence"][-1]["id"] = "evidence.extra-record"
                validate_authority_snapshot(g2, predecessor=g1, program_plan_binding=plan)
            elif case == "source-drift":
                next(row for row in g2["evidence"] if row["id"] == "evidence.harness-decision-packet-thirteen-scenario-manifest-poc-2026-08-09")["kind"] = "drift"
                validate_authority_snapshot(g2, predecessor=g1, program_plan_binding=plan)
            elif case == "link":
                next(row for row in g2["acceptanceCriteria"] if row["id"] == "acceptance.decision-ready-consumer-projection")["evidenceIds"].remove("evidence.harness-decision-packet-thirteen-scenario-manifest-poc-2026-08-09")
                validate_authority_snapshot(g2, predecessor=g1, program_plan_binding=plan)
            elif case == "link-wrong":
                next(row for row in g2["acceptanceCriteria"] if row["id"] == "acceptance.decision-ready-consumer-projection")["evidenceIds"].append("evidence.wrong")
                validate_authority_snapshot(g2, predecessor=g1, program_plan_binding=plan)
            elif case == "assessment":
                next(row for row in g2["acceptanceCriteria"] if row["id"] == "acceptance.decision-ready-consumer-projection")["assessment"] = "verified"
                next(row for row in g2["acceptanceCriteria"] if row["assessment"] == "verified")["assessment"] = "partial"
                validate_authority_snapshot(g2, predecessor=g1, program_plan_binding=plan)
            elif case == "assessment-bool":
                next(row for row in g2["acceptanceCriteria"] if row["id"] == "acceptance.decision-ready-consumer-projection")["assessment"] = True
                validate_authority_snapshot(g2, predecessor=g1, program_plan_binding=plan)
            elif case == "assessment-float":
                next(row for row in g2["acceptanceCriteria"] if row["id"] == "acceptance.decision-ready-consumer-projection")["assessment"] = 1.0
                validate_authority_snapshot(g2, predecessor=g1, program_plan_binding=plan)
            elif case == "assessment-int":
                next(row for row in g2["acceptanceCriteria"] if row["id"] == "acceptance.decision-ready-consumer-projection")["assessment"] = 1
                validate_authority_snapshot(g2, predecessor=g1, program_plan_binding=plan)
            elif case == "criterion-count":
                g2["acceptanceCriteria"].pop()
                validate_authority_snapshot(g2, predecessor=g1, program_plan_binding=plan)
            elif case == "unrelated-objective":
                g2["objectives"][0]["id"] = "objective.unrelated"
                validate_authority_snapshot(g2, predecessor=g1, program_plan_binding=plan)
            elif case == "unrelated-verification":
                g2["verifications"][0]["id"] = "verification.unrelated"
                validate_authority_snapshot(g2, predecessor=g1, program_plan_binding=plan)
            elif case == "unrelated-criterion":
                g2["acceptanceCriteria"][0]["statement"] = "unrelated"
                validate_authority_snapshot(g2, predecessor=g1, program_plan_binding=plan)
            elif case == "unrelated-evidence":
                g2["evidence"][0]["id"] = "evidence.unrelated"
                validate_authority_snapshot(g2, predecessor=g1, program_plan_binding=plan)
            elif case == "duplicate":
                g2["evidence"].append(copy.deepcopy(g2["evidence"][-1]))
                validate_authority_snapshot(g2, predecessor=g1, program_plan_binding=plan)
            elif case == "overreach":
                extra = copy.deepcopy(g2["evidence"][-1])
                extra["id"] = "evidence.extra"
                g2["evidence"].append(extra)
                target = next(row for row in g2["acceptanceCriteria"] if row["id"] == "acceptance.decision-ready-consumer-projection")
                target["evidenceIds"].append("evidence.extra")
                validate_authority_snapshot(g2, predecessor=g1, program_plan_binding=plan)
        return invoke

    def receipt_mutation(case: str) -> object:
        def invoke() -> None:
            _, g1, g2 = snapshots()
            receipt = _read_json(repo_root / FIXTURE_ROOT / "transitions/g000001-to-g000002.json")
            if case == "invalid":
                receipt.pop("claimBoundary")
            elif case == "chain":
                receipt["fromSnapshotBinding"]["sha256"] = "0" * 64
            elif case == "type":
                receipt["transactionType"] = "unknown"
            elif case == "from":
                receipt["fromSnapshotBinding"]["id"] = "wrong"
            elif case == "to":
                receipt["toSnapshotBinding"]["id"] = "wrong"
            elif case == "generation-step":
                receipt["toSnapshotBinding"]["generation"] = 9
            elif case == "delta":
                receipt["delta"]["evidenceAdded"] = ["rewritten"]
            validate_transition_receipt(receipt, from_document=g1, to_document=g2)
        return invoke

    def rollback_mutation(case: str) -> object:
        def invoke() -> None:
            _, g1, g2 = snapshots()
            plan = g1["programPlanBinding"]
            g1_binding = _binding(2, g1, Path("snapshots/v2/g000001.json"), canonical_file_bytes(g1))
            g2_binding = _binding(2, g2, Path("snapshots/v2/g000002.json"), canonical_file_bytes(g2))
            if case == "target":
                build_rollback_receipt(from_snapshot_binding=g2_binding, to_snapshot_binding=g2_binding, active_program_plan_binding=plan, ancestor_bindings=[g1_binding])
            elif case == "other-series":
                other = copy.deepcopy(g1_binding)
                other["id"] = "other-series:g000001"
                build_rollback_receipt(from_snapshot_binding=g2_binding, to_snapshot_binding=other, active_program_plan_binding=plan, ancestor_bindings=[g1_binding])
            elif case == "rewritten":
                rewritten = copy.deepcopy(g1)
                rewritten["acceptanceCriteria"][0]["statement"] = "rewritten"
                rewritten_binding = _binding(2, rewritten, Path("snapshots/v2/g000001.json"), canonical_file_bytes(rewritten))
                build_rollback_receipt(from_snapshot_binding=g2_binding, to_snapshot_binding=rewritten_binding, active_program_plan_binding=plan, ancestor_bindings=[g1_binding])
            else:
                receipt = _read_json(repo_root / FIXTURE_ROOT / "transitions/g000002-to-g000001-rollback.json")
                receipt["delta"]["evidenceAdded"] = ["bad"]
                validate_transition_receipt(receipt, from_document=g2, to_document=g1)
        return invoke

    def atomic_directory_target() -> None:
        with tempfile.TemporaryDirectory(prefix="acceptance-atomic-matrix-") as directory:
            target = Path(directory) / "current.json"
            target.mkdir()
            replace_selector_atomically(target, b"candidate\n")

    def selector_mutation(field: str) -> None:
        with tempfile.TemporaryDirectory(prefix="acceptance-selector-matrix-") as directory:
            output = Path(directory) / "rehearsal"
            _write_rehearsal_bundle(repo_root, output, build_rehearsal_bundle(repo_root))
            selector = _read_json(output / "selectors/current-g000002.json")
            if field == "snapshot": selector["activeSnapshotBinding"]["sha256"] = "0" * 64
            elif field == "receipt": selector["activeTransitionBinding"]["sha256"] = "0" * 64
            elif field == "plan": selector["programPlanBinding"]["sha256"] = "0" * 64
            elif field == "plan-path": selector["programPlanBinding"]["path"] = "rewritten-plan.json"
            elif field == "mode": selector["selectionMode"] = "live"
            elif field == "activation": selector["activationAuthorized"] = True
            else: selector["executionCounters"]["modelRequestCount"] = 1.0
            holder, overlay = _overlay_with_legacy(repo_root, output, canonical_file_bytes(selector))
            try: resolve_current_authority(overlay, REHEARSAL_SELECTOR_PATH.as_posix())
            finally: holder.cleanup()

    def selector_parent_escape() -> None:
        resolve_current_authority(repo_root, "../current.json")

    def selector_symlink_escape() -> None:
        with tempfile.TemporaryDirectory(prefix="acceptance-selector-link-") as directory:
            root = Path(directory) / "root"
            root.mkdir()
            external = Path(directory) / "external.json"
            external.write_bytes(b"{}")
            os.symlink(external, root / "current.json")
            resolve_current_authority(root, "current.json")

    def candidate_byte_fork(relative: Path) -> None:
        with tempfile.TemporaryDirectory(prefix="acceptance-fork-matrix-") as directory:
            output = Path(directory) / "rehearsal"
            bundle = build_rehearsal_bundle(repo_root)
            _write_rehearsal_bundle(repo_root, output, bundle)
            target = output / relative
            target.write_bytes(target.read_bytes() + b"\n")
            holder, overlay = _overlay_with_legacy(repo_root, output, bundle["selectors/current-g000002.json"])
            try: resolve_current_authority(overlay, REHEARSAL_SELECTOR_PATH.as_posix())
            finally: holder.cleanup()

    def duplicate_introducing_receipt() -> None:
        with tempfile.TemporaryDirectory(prefix="acceptance-duplicate-receipt-") as directory:
            output = Path(directory) / "rehearsal"; bundle = build_rehearsal_bundle(repo_root)
            _write_rehearsal_bundle(repo_root, output, bundle)
            duplicate = output / "transitions/alternate-introducer.json"
            shutil.copyfile(output / "transitions/g000001-to-g000002.json", duplicate)
            holder, overlay = _overlay_with_legacy(repo_root, output, bundle["selectors/current-g000002.json"])
            shutil.copyfile(duplicate, overlay / "transitions/alternate-introducer.json")
            try: resolve_current_authority(overlay, REHEARSAL_SELECTOR_PATH.as_posix())
            finally: holder.cleanup()

    def atomic_sentinel_preserved() -> None:
        with tempfile.TemporaryDirectory(prefix="acceptance-atomic-sentinel-") as directory:
            target = Path(directory) / "current.json"
            sentinel = b"sentinel-selector-bytes\n"
            target.write_bytes(sentinel)
            with mock.patch("os.replace", side_effect=OSError("replace denied")):
                try:
                    replace_selector_atomically(target, b"candidate-selector-bytes\n")
                finally:
                    if target.read_bytes() != sentinel or list(Path(directory).glob(".current.json.*.tmp")):
                        raise RuntimeError("atomic sentinel preservation failed")

    def cli_protected_output() -> str:
        completed = subprocess.run(
            ["python", "-B", "scripts/build_program_acceptance_authority_v2_rehearsal.py", "--root", str(repo_root), "--output-root", str(repo_root / PRODUCTION_AUTHORITY_ROOT)],
            cwd=repo_root,
            check=False,
            capture_output=True,
            text=True,
        )
        if completed.returncode != 2 or completed.stdout:
            return "accepted"
        try:
            envelope = json.loads(completed.stderr)
        except json.JSONDecodeError:
            return "accepted"
        return envelope.get("code") if isinstance(envelope, dict) and type(envelope.get("code")) is str else "accepted"

    def cleanup_fault() -> None:
        with tempfile.TemporaryDirectory(prefix="acceptance-cleanup-matrix-") as directory:
            output = Path(directory) / "rehearsal"
            original_rmtree = shutil.rmtree

            def fail_only_rehearsal_target(path: object, *args: object, **kwargs: object) -> None:
                candidate = Path(path)
                if candidate.parent == output.parent and candidate.name.startswith(f".{output.name}.cleanup-"):
                    raise OSError("cleanup denied")
                original_rmtree(path, *args, **kwargs)

            with mock.patch(
                "scripts.program_acceptance_authority_v2_rehearsal.shutil.rmtree",
                side_effect=fail_only_rehearsal_target,
            ):
                run_rehearsal(repo_root, output)
            if os.path.lexists(output):
                shutil.rmtree(output)

    cases: tuple[tuple[str, str, object], ...] = (
        ("legacy-authority-drift", "legacy-authority-drift", legacy_mutation("acceptance")),
        ("legacy-program-plan-drift", "legacy-program-plan-drift", legacy_mutation("programPlan")),
        ("legacy-packet-fixture-drift", "legacy-packet-fixture-drift", legacy_mutation("packetFixture")),
        ("legacy-manifest-fixture-drift", "legacy-manifest-fixture-drift", legacy_mutation("manifestFixture")),
        ("inventory-missing", "migration-inventory-incomplete", inventory_mutation("missing")),
        ("inventory-invalid-class", "migration-consumer-class-invalid", inventory_mutation("invalid-class")),
        ("inventory-historical-repoint", "acceptance-historical-consumer-repointed", inventory_mutation("historical-repoint")),
        ("inventory-current-bypass", "acceptance-current-consumer-legacy-bypass", inventory_mutation("current-bypass")),
        ("inventory-neutral-path", "acceptance-neutral-consumer-path-owned", inventory_mutation("neutral-path")),
        ("authority-schema-bool", "acceptance-authority-schema-invalid", lambda: binding_for_bytes(authority_schema=True, authority_id="x", generation=None, path="x", data=b"x")),
        ("authority-schema-alias", "acceptance-authority-schema-invalid", snapshot_mutation("schema")),
        ("authority-generation-bool", "acceptance-authority-generation-invalid", lambda: binding_for_bytes(authority_schema=2, authority_id="x", generation=True, path="x", data=b"x")),
        ("authority-generation-alias", "acceptance-authority-generation-invalid", snapshot_mutation("generation")),
        ("authority-series", "acceptance-authority-series-invalid", snapshot_mutation("series")),
        ("authority-predecessor", "acceptance-authority-predecessor-mismatch", snapshot_mutation("predecessor")),
        ("authority-predecessor-path", "acceptance-authority-predecessor-mismatch", snapshot_mutation("predecessor-path")),
        ("authority-predecessor-digest", "acceptance-authority-predecessor-mismatch", snapshot_mutation("predecessor-digest")),
        ("program-plan-binding", "acceptance-program-plan-binding-drift", snapshot_mutation("plan")),
        ("program-plan-id", "acceptance-program-plan-binding-drift", snapshot_mutation("plan-id")),
        ("program-plan-path", "acceptance-program-plan-binding-drift", snapshot_mutation("plan-path")),
        ("structural-overreach", "acceptance-structural-migration-overreach", snapshot_mutation("structural")),
        ("structural-objective", "acceptance-structural-migration-overreach", snapshot_mutation("structural-objective")),
        ("structural-criterion", "acceptance-structural-migration-overreach", snapshot_mutation("structural-criterion")),
        ("structural-verification", "acceptance-structural-migration-overreach", snapshot_mutation("structural-verification")),
        ("structural-preexisting-evidence", "acceptance-evidence-link-asymmetric", snapshot_mutation("structural-evidence")),
        ("inventory-count", "acceptance-inventory-count-drift", snapshot_mutation("inventory")),
        ("evidence-source-missing", "acceptance-evidence-source-missing", manifest_source_mutation("missing")),
        ("evidence-source-drift", "acceptance-evidence-source-drift", manifest_source_mutation("drift")),
        ("evidence-manifest-row-missing", "acceptance-evidence-source-missing", snapshot_mutation("missing")),
        ("evidence-manifest-row-wrong", "acceptance-evidence-source-drift", snapshot_mutation("manifest-wrong")),
        ("evidence-manifest-row-extra", "acceptance-evidence-link-asymmetric", snapshot_mutation("manifest-extra")),
        ("evidence-link-asymmetric", "acceptance-evidence-link-asymmetric", snapshot_mutation("link")),
        ("reciprocal-link-missing", "acceptance-evidence-link-asymmetric", snapshot_mutation("link")),
        ("evidence-link-wrong", "acceptance-evidence-link-asymmetric", snapshot_mutation("link-wrong")),
        ("reciprocal-link-extra", "acceptance-evidence-link-asymmetric", snapshot_mutation("link-wrong")),
        ("assessment-promotion", "acceptance-assessment-promotion-forbidden", snapshot_mutation("assessment")),
        ("assessment-bool-alias", "acceptance-inventory-count-drift", snapshot_mutation("assessment-bool")),
        ("assessment-float-alias", "acceptance-inventory-count-drift", snapshot_mutation("assessment-float")),
        ("assessment-int-alias", "acceptance-inventory-count-drift", snapshot_mutation("assessment-int")),
        ("evidence-criterion-count", "acceptance-structural-migration-overreach", snapshot_mutation("criterion-count")),
        ("evidence-unrelated-objective", "acceptance-evidence-registration-overreach", snapshot_mutation("unrelated-objective")),
        ("evidence-unrelated-verification", "acceptance-structural-migration-overreach", snapshot_mutation("unrelated-verification")),
        ("evidence-unrelated-criterion", "acceptance-evidence-registration-overreach", snapshot_mutation("unrelated-criterion")),
        ("evidence-unrelated-evidence", "acceptance-evidence-link-asymmetric", snapshot_mutation("unrelated-evidence")),
        ("evidence-id-duplicate", "acceptance-evidence-id-duplicate", snapshot_mutation("duplicate")),
        ("evidence-registration-overreach", "acceptance-evidence-registration-overreach", snapshot_mutation("overreach")),
        ("selector-escape", "acceptance-selector-target-invalid", lambda: resolve_current_authority(repo_root, "../current.json")),
        ("receipt-invalid", "acceptance-transition-receipt-invalid", receipt_mutation("invalid")),
        ("receipt-chain", "acceptance-transition-chain-broken", receipt_mutation("chain")),
        ("receipt-from-binding", "acceptance-transition-receipt-invalid", receipt_mutation("from")),
        ("receipt-to-binding", "acceptance-transition-receipt-invalid", receipt_mutation("to")),
        ("receipt-generation-step", "acceptance-transition-chain-broken", receipt_mutation("generation-step")),
        ("receipt-delta", "acceptance-transition-receipt-invalid", receipt_mutation("delta")),
        ("receipt-type", "acceptance-transition-type-mismatch", receipt_mutation("type")),
        ("receipt-side-effect-counter", "acceptance-side-effect-counter-nonzero", nonzero_receipt),
        ("rollback-invalid", "acceptance-rollback-receipt-invalid", rollback_mutation("invalid")),
        ("rollback-target", "acceptance-rollback-target-not-ancestor", rollback_mutation("target")),
        ("rollback-other-series", "acceptance-rollback-target-not-ancestor", rollback_mutation("other-series")),
        ("rollback-rewritten-same-generation", "acceptance-rollback-target-not-ancestor", rollback_mutation("rewritten")),
        ("atomic-directory-target", "acceptance-atomic-output-preserved", atomic_directory_target),
        ("atomic-sentinel-preserved", "acceptance-atomic-output-preserved", atomic_sentinel_preserved),
        ("selector-snapshot-digest", "acceptance-selector-target-invalid", lambda: selector_mutation("snapshot")),
        ("selector-receipt-digest", "acceptance-transition-receipt-invalid", lambda: selector_mutation("receipt")),
        ("selector-plan-digest", "acceptance-selector-target-invalid", lambda: selector_mutation("plan")),
        ("selector-plan-path-rewrite", "acceptance-selector-target-invalid", lambda: selector_mutation("plan-path")),
        ("snapshot-byte-fork", "acceptance-transition-chain-broken", lambda: candidate_byte_fork(Path("snapshots/v2/g000001.json"))),
        ("receipt-byte-fork", "acceptance-transition-receipt-invalid", lambda: candidate_byte_fork(Path("transitions/g000001-to-g000002.json"))),
        ("duplicate-introducing-receipt", "acceptance-transition-chain-broken", duplicate_introducing_receipt),
        ("selector-mode", "acceptance-selector-target-invalid", lambda: selector_mutation("mode")),
        ("selector-activation-bool", "acceptance-activation-not-authorized", lambda: selector_mutation("activation")),
        ("selector-counter-float", "acceptance-side-effect-counter-nonzero", lambda: selector_mutation("counter")),
        ("selector-parent-escape", "acceptance-selector-target-invalid", selector_parent_escape),
        ("selector-symlink-escape", "acceptance-selector-target-invalid", selector_symlink_escape),
        ("cleanup-fault", "acceptance-rehearsal-cleanup-incomplete", cleanup_fault),
        ("protected-output-root", "acceptance-activation-not-authorized", lambda: run_rehearsal(repo_root, repo_root / PRODUCTION_AUTHORITY_ROOT)),
        ("inventory-duplicate-row", "migration-inventory-incomplete", inventory_mutation("duplicate-row")),
        ("inventory-extra-row", "migration-inventory-incomplete", inventory_mutation("extra-row")),
        ("inventory-reordered-rows", "migration-inventory-incomplete", inventory_mutation("reordered-rows")),
        ("inventory-bool-line", "migration-consumer-class-invalid", inventory_mutation("bool-line")),
        ("inventory-float-line", "migration-consumer-class-invalid", inventory_mutation("float-line")),
        ("inventory-stale-line", "migration-inventory-incomplete", inventory_mutation("stale-line")),
        ("inventory-raw-id", "migration-consumer-class-invalid", inventory_mutation("raw-id")),
        ("inventory-raw-path-outside-host", "migration-consumer-class-invalid", inventory_mutation("raw-path-outside-host")),
        ("selector-absolute", "acceptance-selector-target-invalid", lambda: resolve_current_authority(repo_root, str((repo_root / "current.json").resolve()))),
        ("cli-protected-output", "acceptance-activation-not-authorized", cli_protected_output),
    )
    cases = tuple(sorted(cases, key=lambda item: (_CODE_ORDER[item[1]], item[0])))
    if tuple((case_id, expected) for case_id, expected, _ in cases) != REQUIRED_FAILURE_CASES:
        raise AcceptanceAuthorityError("acceptance-rehearsal-record-invalid", "Failure matrix implementation drifted from its required authority.")
    for case_id, expected, invoke in cases:
        try:
            returned = invoke()
        except AcceptanceAuthorityError as error:
            observed = error.code
        else:
            observed = returned if type(returned) is str else "accepted"
        results.append({"caseId": case_id, "expectedCode": expected, "observedCode": observed, "status": "rejected" if observed == expected else "failed"})
    return results


def _is_exact_digest_map(value: object, expected: dict[str, str]) -> bool:
    return (
        isinstance(value, dict)
        and set(value) == set(expected)
        and all(type(key) is str and type(item) is str and len(item) == 64 and item == expected[key] for key, item in value.items())
    )


def _is_manifest_evidence_binding(value: object, expected: dict[str, str]) -> bool:
    return (
        isinstance(value, dict)
        and set(value) == {"path", "sha256"}
        and type(value["path"]) is str
        and type(value["sha256"]) is str
        and value == expected
    )


def _is_exact_int_map(value: object, expected: dict[str, int]) -> bool:
    return (
        isinstance(value, dict)
        and set(value) == set(expected)
        and all(type(key) is str and type(item) is int and item == expected[key] for key, item in value.items())
    )


def _is_exact_bool_map(value: object, expected: dict[str, bool]) -> bool:
    return (
        isinstance(value, dict)
        and set(value) == set(expected)
        and all(type(key) is str and type(item) is bool and item is expected[key] for key, item in value.items())
    )


def _is_exact_bool_string_map(value: object, expected: dict[str, object]) -> bool:
    return (
        isinstance(value, dict)
        and set(value) == set(expected)
        and type(value.get("registered")) is bool
        and value == expected
    )


def _is_exact_observation(value: object, expected: dict[str, object]) -> bool:
    if not isinstance(value, dict) or set(value) != {"occurrenceCount", "trackedReferenceCount", "referenceSetSha256"}:
        return False
    return (
        type(value["occurrenceCount"]) is int
        and type(value["trackedReferenceCount"]) is int
        and type(value["referenceSetSha256"]) is str
        and strict_json_equal(value, expected)
    )


def _is_matrix_row(row: object) -> bool:
    return (
        isinstance(row, dict)
        and set(row) == {"caseId", "expectedCode", "observedCode", "status"}
        and all(type(row[name]) is str for name in row)
        and row["status"] == "rejected"
        and row["expectedCode"] == row["observedCode"]
    )


def validate_repository_record(root: Path) -> dict[str, object]:
    """Recompute the independent local evidence rather than trusting its summaries."""

    root = root.resolve()
    try:
        raw = (root / RECORD_PATH).read_bytes()
        record = json.loads(raw)
    except (OSError, json.JSONDecodeError) as error:
        raise AcceptanceAuthorityError("acceptance-rehearsal-record-invalid", "Rehearsal record cannot be read.") from error
    if not isinstance(record, dict) or set(record) != {
        "schema", "id", "date", "status", "fileDigests", "legacyLockDigests",
        "fixtureDigests", "migrationInventory", "acceptanceInventory", "targetCriterion",
        "acceptanceRegistration", "liveMigrationAuthorized", "executionCounters",
        "claimBoundary", "failureMatrix", "manifestEvidenceSource", "generationProjections",
    }:
        raise AcceptanceAuthorityError("acceptance-rehearsal-record-invalid", "Rehearsal record shape is invalid.")
    if raw != canonical_file_bytes(record):
        raise AcceptanceAuthorityError("acceptance-rehearsal-record-invalid", "Rehearsal record must use canonical compact JSON wire bytes.")
    if type(record.get("schema")) is not int or record.get("schema") != 1 or type(record.get("id")) is not str or record.get("id") != "program-acceptance-authority-v2-zero-model-rehearsal-2026-08-10" or type(record.get("date")) is not str or record.get("date") != "2026-08-10" or type(record.get("status")) is not str or record.get("status") != _STATUS:
        raise AcceptanceAuthorityError("acceptance-rehearsal-record-invalid", "Rehearsal record identity is invalid.")
    payload = canonical_file_bytes(record)
    if any(literal.encode("utf-8") in payload for literal in LEGACY_ACCEPTANCE_SEARCH_PATTERNS.values()):
        raise AcceptanceAuthorityError("acceptance-rehearsal-record-invalid", "Rehearsal record retains a raw inventory literal.")
    expected_file_digests = {path.as_posix(): file_sha256(root, path) for path in _RECORD_DIGEST_PATHS}
    if not _is_exact_digest_map(record.get("fileDigests"), expected_file_digests):
        raise AcceptanceAuthorityError("acceptance-rehearsal-record-invalid", "Rehearsal record file digests drifted.")
    locks = validate_legacy_locks(root)
    if not _is_exact_digest_map(record.get("legacyLockDigests"), {name: value["sha256"] for name, value in locks.items()}):
        raise AcceptanceAuthorityError("acceptance-rehearsal-record-invalid", "Rehearsal record legacy locks drifted.")
    bundle = build_rehearsal_bundle(root)
    fixture_g2 = _read_json(root / FIXTURE_ROOT / "snapshots/v2/g000002.json")
    _validate_manifest_evidence_source(root, fixture_g2)
    expected_evidence_source = {
        "path": MANIFEST_EVIDENCE_SOURCE_PATH.as_posix(),
        "sha256": MANIFEST_EVIDENCE_SOURCE_SHA256,
    }
    if not _is_manifest_evidence_binding(record.get("manifestEvidenceSource"), expected_evidence_source):
        raise AcceptanceAuthorityError("acceptance-rehearsal-record-invalid", "Rehearsal record manifest evidence source binding drifted.")
    fixture_digests = {path: hashlib.sha256(data).hexdigest() for path, data in bundle.items()}
    if not _is_exact_digest_map(record.get("fixtureDigests"), fixture_digests):
        raise AcceptanceAuthorityError("acceptance-rehearsal-record-invalid", "Rehearsal record fixture digests drifted.")
    inventory = load_migration_inventory(root)
    validate_migration_inventory(root, inventory)
    expected_inventory = copy.deepcopy(inventory["baselineObservation"])
    if not _is_exact_observation(record.get("migrationInventory"), expected_inventory):
        raise AcceptanceAuthorityError("acceptance-rehearsal-record-invalid", "Rehearsal record inventory binding drifted.")
    fixture_g1 = _read_json(root / FIXTURE_ROOT / "snapshots/v2/g000001.json")
    expected_projections = {
        "g000001": {"criteriaCount": len(fixture_g1["acceptanceCriteria"]), "assessmentInventory": assessment_inventory(fixture_g1)},
        "g000002": {"criteriaCount": len(fixture_g2["acceptanceCriteria"]), "assessmentInventory": assessment_inventory(fixture_g2)},
    }
    projections = record.get("generationProjections")
    if not isinstance(projections, dict) or set(projections) != set(expected_projections) or any(
        not isinstance(projections[key], dict)
        or set(projections[key]) != {"criteriaCount", "assessmentInventory"}
        or type(projections[key]["criteriaCount"]) is not int
        or not _is_exact_int_map(projections[key]["assessmentInventory"], expected_projections[key]["assessmentInventory"])
        or not strict_json_equal(projections[key], expected_projections[key])
        for key in expected_projections
    ):
        raise AcceptanceAuthorityError("acceptance-rehearsal-record-invalid", "Rehearsal record generation projections drifted.")
    actual_acceptance = expected_projections["g000002"]["assessmentInventory"]
    actual_target = next((row for row in fixture_g2["acceptanceCriteria"] if row.get("id") == "acceptance.decision-ready-consumer-projection"), None)
    if not isinstance(actual_target, dict) or actual_target.get("assessment") != "partial":
        raise AcceptanceAuthorityError("acceptance-rehearsal-record-invalid", "Fixture target criterion cannot be independently recomputed.")
    if not _is_exact_int_map(record.get("acceptanceInventory"), actual_acceptance) or record.get("targetCriterion") != actual_target["assessment"] or not _is_exact_bool_string_map(record.get("acceptanceRegistration"), {"registered": False, "reason": "frozen-v1-authority-live-v2-migration-not-authorized"}) or type(record.get("liveMigrationAuthorized")) is not bool or record.get("liveMigrationAuthorized") is not False or not _is_exact_int_map(record.get("executionCounters"), ZERO_EXECUTION_COUNTERS) or not _is_exact_bool_map(record.get("claimBoundary"), _ZERO_CLAIMS):
        raise AcceptanceAuthorityError("acceptance-rehearsal-record-invalid", "Rehearsal record boundaries drifted.")
    matrix = run_failure_matrix(root)
    expected_matrix_authority = tuple({"caseId": case_id, "expectedCode": code} for case_id, code in REQUIRED_FAILURE_CASES)
    seen_codes: list[str] = []
    for row in matrix:
        code = row.get("expectedCode")
        if type(code) is str and code not in seen_codes:
            seen_codes.append(code)
    if tuple({"caseId": row.get("caseId"), "expectedCode": row.get("expectedCode")} for row in matrix) != expected_matrix_authority or tuple(seen_codes) != REQUIRED_TYPED_CODES or not strict_json_equal(record.get("failureMatrix"), matrix) or not all(_is_matrix_row(row) for row in matrix):
        raise AcceptanceAuthorityError("acceptance-rehearsal-record-invalid", "Rehearsal record failure matrix drifted.")
    return copy.deepcopy(record)
