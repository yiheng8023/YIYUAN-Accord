from __future__ import annotations

import copy
import hashlib
import json
import os
import shutil
import subprocess
import tempfile
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
_ZERO_CLAIMS = {
    "provesBehavior": False,
    "provesValue": False,
    "provesCrossHostPortability": False,
    "provesProductionReadiness": False,
    "provesReleaseEligibility": False,
    "provesResidualGap": False,
    "provesOverallCloseout": False,
}
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


def write_rehearsal_bundle(output_root: Path, bundle: dict[str, bytes]) -> None:
    """Stage/fsync immutable candidate bytes and publish the disposable directory once."""

    repo_root = Path.cwd().resolve()
    _, resolved_output = _assert_disposable_output(repo_root, output_root)
    if set(bundle) != {path.as_posix() for path in _BUNDLE_PATHS}:
        raise AcceptanceAuthorityError("acceptance-rehearsal-bundle-invalid", "Rehearsal bundle shape is invalid.")
    stage = Path(tempfile.mkdtemp(prefix=f".{resolved_output.name}.stage-", dir=resolved_output.parent))
    try:
        for relative in _BUNDLE_PATHS:
            target = stage / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            _write_fsynced(target, bundle[relative.as_posix()])
        _validate_bundle_bytes(repo_root, stage, bundle)
        os.replace(stage, resolved_output)
    except AcceptanceAuthorityError:
        shutil.rmtree(stage, ignore_errors=True)
        raise
    except OSError as error:
        shutil.rmtree(stage, ignore_errors=True)
        raise AcceptanceAuthorityError("acceptance-rehearsal-output-write-failed", "Rehearsal output could not be written.") from error


def _overlay_with_legacy(repo_root: Path, output_root: Path, selector_bytes: bytes) -> tuple[tempfile.TemporaryDirectory[str], Path]:
    holder = tempfile.TemporaryDirectory(prefix="acceptance-authority-v2-overlay-")
    overlay = Path(holder.name)
    for relative in _BUNDLE_PATHS:
        source = output_root / relative
        target = overlay / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
    for relative in (entry[0] for entry in __import__("scripts.program_acceptance_authority_v2", fromlist=["LEGACY_LOCKS"]).LEGACY_LOCKS.values()):
        target = overlay / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(repo_root / relative, target)
    selector = overlay / REHEARSAL_SELECTOR_PATH
    selector.parent.mkdir(parents=True, exist_ok=True)
    selector.write_bytes(selector_bytes)
    return holder, overlay


def _cleanup_disposable(repo_root: Path, output_root: Path) -> None:
    _, resolved = _assert_cleanup_target(repo_root, output_root)
    try:
        shutil.rmtree(resolved)
    except OSError as error:
        raise AcceptanceAuthorityError("acceptance-rehearsal-cleanup-incomplete", "Disposable rehearsal root could not be removed.") from error
    if resolved.exists():
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
    legacy_before = {name: file_sha256(repo_root, value[0]) for name, value in __import__("scripts.program_acceptance_authority_v2", fromlist=["LEGACY_LOCKS"]).LEGACY_LOCKS.items()}
    tracked_before = subprocess.run(["git", "-C", str(repo_root), "status", "--porcelain=v1"], check=True, capture_output=True).stdout
    bundle = build_rehearsal_bundle(repo_root)
    write_rehearsal_bundle(output_root, bundle)
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
            historical = resolve_historical_authority(overlay, current_g1["binding"], frozen_program_plan_binding=current_g1["selector"]["programPlanBinding"])
        finally:
            holder.cleanup()
        if current_g2["binding"]["generation"] != 2 or current_g1["binding"]["generation"] != 1 or historical["binding"]["generation"] != 1:
            raise AcceptanceAuthorityError("acceptance-rehearsal-bundle-invalid", "Rehearsal resolution generations drifted.")
    finally:
        if output_root.exists():
            _cleanup_disposable(repo_root, output_root)
    legacy_after = {name: file_sha256(repo_root, value[0]) for name, value in __import__("scripts.program_acceptance_authority_v2", fromlist=["LEGACY_LOCKS"]).LEGACY_LOCKS.items()}
    tracked_after = subprocess.run(["git", "-C", str(repo_root), "status", "--porcelain=v1"], check=True, capture_output=True).stdout
    if not strict_json_equal(legacy_before, legacy_after) or not strict_json_equal(tracked_before, tracked_after):
        raise AcceptanceAuthorityError("acceptance-rehearsal-cleanup-incomplete", "Rehearsal changed protected repository state.")
    return {
        "status": _STATUS,
        "highestGeneration": 2,
        "rollbackGeneration": 1,
        "acceptanceInventory": {"verified": 46, "partial": 15, "planned": 0},
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
            validate_migration_inventory(repo_root, inventory)
        return invoke

    def nonzero_receipt() -> None:
        receipt = _read_json(repo_root / FIXTURE_ROOT / "transitions/g000001-to-g000002.json")
        g1 = _read_json(repo_root / FIXTURE_ROOT / "snapshots/v2/g000001.json")
        g2 = _read_json(repo_root / FIXTURE_ROOT / "snapshots/v2/g000002.json")
        receipt["executionCounters"]["modelRequestCount"] = 1
        validate_transition_receipt(receipt, from_document=g1, to_document=g2)

    def snapshots() -> tuple[dict[str, object], dict[str, object], dict[str, object]]:
        return (
            _read_json(repo_root / "registry/program-acceptance-map.json"),
            _read_json(repo_root / FIXTURE_ROOT / "snapshots/v2/g000001.json"),
            _read_json(repo_root / FIXTURE_ROOT / "snapshots/v2/g000002.json"),
        )

    def snapshot_mutation(case: str) -> object:
        def invoke() -> None:
            legacy, g1, g2 = snapshots()
            plan = copy.deepcopy(g1["programPlanBinding"])
            if case == "series":
                g1["authoritySeriesId"] = "wrong"
                validate_authority_snapshot(g1, predecessor=legacy, program_plan_binding=plan)
            elif case == "predecessor":
                g1["predecessorBinding"]["id"] = "wrong"
                validate_authority_snapshot(g1, predecessor=legacy, program_plan_binding=plan)
            elif case == "plan":
                g1["programPlanBinding"]["sha256"] = "0" * 64
                validate_authority_snapshot(g1, predecessor=legacy, program_plan_binding=plan)
            elif case == "structural":
                g1["acceptanceCriteria"][0]["statement"] = "rewritten"
                validate_authority_snapshot(g1, predecessor=legacy, program_plan_binding=plan)
            elif case == "inventory":
                g1["acceptanceCriteria"][0]["assessment"] = "planned"
                validate_authority_snapshot(g1, predecessor=legacy, program_plan_binding=plan)
            elif case == "missing":
                g2["evidence"] = [row for row in g2["evidence"] if row["id"] != "evidence.harness-decision-packet-thirteen-scenario-manifest-poc-2026-08-09"]
                next(row for row in g2["acceptanceCriteria"] if row["id"] == "acceptance.decision-ready-consumer-projection")["evidenceIds"].remove("evidence.harness-decision-packet-thirteen-scenario-manifest-poc-2026-08-09")
                validate_authority_snapshot(g2, predecessor=g1, program_plan_binding=plan)
            elif case == "source-drift":
                next(row for row in g2["evidence"] if row["id"] == "evidence.harness-decision-packet-thirteen-scenario-manifest-poc-2026-08-09")["kind"] = "drift"
                validate_authority_snapshot(g2, predecessor=g1, program_plan_binding=plan)
            elif case == "link":
                next(row for row in g2["acceptanceCriteria"] if row["id"] == "acceptance.decision-ready-consumer-projection")["evidenceIds"].remove("evidence.harness-decision-packet-thirteen-scenario-manifest-poc-2026-08-09")
                validate_authority_snapshot(g2, predecessor=g1, program_plan_binding=plan)
            elif case == "assessment":
                next(row for row in g2["acceptanceCriteria"] if row["id"] == "acceptance.decision-ready-consumer-projection")["assessment"] = "verified"
                next(row for row in g2["acceptanceCriteria"] if row["assessment"] == "verified")["assessment"] = "partial"
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

    def cleanup_fault() -> None:
        with tempfile.TemporaryDirectory(prefix="acceptance-cleanup-matrix-") as directory:
            output = Path(directory) / "rehearsal"
            with mock.patch(
                "scripts.program_acceptance_authority_v2_rehearsal.shutil.rmtree",
                side_effect=OSError("cleanup denied"),
            ):
                run_rehearsal(repo_root, output)
            if output.exists():
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
        ("authority-generation-bool", "acceptance-authority-generation-invalid", lambda: binding_for_bytes(authority_schema=2, authority_id="x", generation=True, path="x", data=b"x")),
        ("authority-series", "acceptance-authority-series-invalid", snapshot_mutation("series")),
        ("authority-predecessor", "acceptance-authority-predecessor-mismatch", snapshot_mutation("predecessor")),
        ("program-plan-binding", "acceptance-program-plan-binding-drift", snapshot_mutation("plan")),
        ("structural-overreach", "acceptance-structural-migration-overreach", snapshot_mutation("structural")),
        ("inventory-count", "acceptance-inventory-count-drift", snapshot_mutation("inventory")),
        ("evidence-source-missing", "acceptance-evidence-source-missing", snapshot_mutation("missing")),
        ("evidence-source-drift", "acceptance-evidence-source-drift", snapshot_mutation("source-drift")),
        ("evidence-link-asymmetric", "acceptance-evidence-link-asymmetric", snapshot_mutation("link")),
        ("assessment-promotion", "acceptance-assessment-promotion-forbidden", snapshot_mutation("assessment")),
        ("evidence-id-duplicate", "acceptance-evidence-id-duplicate", snapshot_mutation("duplicate")),
        ("evidence-registration-overreach", "acceptance-evidence-registration-overreach", snapshot_mutation("overreach")),
        ("selector-escape", "acceptance-selector-target-invalid", lambda: resolve_current_authority(repo_root, "../current.json")),
        ("receipt-invalid", "acceptance-transition-receipt-invalid", receipt_mutation("invalid")),
        ("receipt-chain", "acceptance-transition-chain-broken", receipt_mutation("chain")),
        ("receipt-type", "acceptance-transition-type-mismatch", receipt_mutation("type")),
        ("receipt-side-effect-counter", "acceptance-side-effect-counter-nonzero", nonzero_receipt),
        ("rollback-invalid", "acceptance-rollback-receipt-invalid", rollback_mutation("invalid")),
        ("rollback-target", "acceptance-rollback-target-not-ancestor", rollback_mutation("target")),
        ("atomic-directory-target", "acceptance-atomic-output-preserved", atomic_directory_target),
        ("cleanup-fault", "acceptance-rehearsal-cleanup-incomplete", cleanup_fault),
        ("protected-output-root", "acceptance-activation-not-authorized", lambda: run_rehearsal(repo_root, repo_root / PRODUCTION_AUTHORITY_ROOT)),
    )
    for case_id, expected, invoke in cases:
        try:
            invoke()
        except AcceptanceAuthorityError as error:
            observed = error.code
        else:
            observed = "accepted"
        results.append({"caseId": case_id, "expectedCode": expected, "observedCode": observed, "status": "rejected" if observed == expected else "failed"})
    return results


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
        "claimBoundary", "failureMatrix",
    }:
        raise AcceptanceAuthorityError("acceptance-rehearsal-record-invalid", "Rehearsal record shape is invalid.")
    if record.get("schema") != 1 or record.get("id") != "program-acceptance-authority-v2-zero-model-rehearsal-2026-08-10" or record.get("date") != "2026-08-10" or record.get("status") != _STATUS:
        raise AcceptanceAuthorityError("acceptance-rehearsal-record-invalid", "Rehearsal record identity is invalid.")
    payload = canonical_file_bytes(record)
    if any(literal.encode("utf-8") in payload for literal in LEGACY_ACCEPTANCE_SEARCH_PATTERNS.values()):
        raise AcceptanceAuthorityError("acceptance-rehearsal-record-invalid", "Rehearsal record retains a raw inventory literal.")
    expected_file_digests = {path.as_posix(): file_sha256(root, path) for path in _RECORD_DIGEST_PATHS}
    if not strict_json_equal(record.get("fileDigests"), expected_file_digests):
        raise AcceptanceAuthorityError("acceptance-rehearsal-record-invalid", "Rehearsal record file digests drifted.")
    locks = validate_legacy_locks(root)
    if not strict_json_equal(record.get("legacyLockDigests"), {name: value["sha256"] for name, value in locks.items()}):
        raise AcceptanceAuthorityError("acceptance-rehearsal-record-invalid", "Rehearsal record legacy locks drifted.")
    bundle = build_rehearsal_bundle(root)
    fixture_digests = {path: hashlib.sha256(data).hexdigest() for path, data in bundle.items()}
    if not strict_json_equal(record.get("fixtureDigests"), fixture_digests):
        raise AcceptanceAuthorityError("acceptance-rehearsal-record-invalid", "Rehearsal record fixture digests drifted.")
    inventory = load_migration_inventory(root)
    validate_migration_inventory(root, inventory)
    expected_inventory = copy.deepcopy(inventory["baselineObservation"])
    if not strict_json_equal(record.get("migrationInventory"), expected_inventory):
        raise AcceptanceAuthorityError("acceptance-rehearsal-record-invalid", "Rehearsal record inventory binding drifted.")
    if not strict_json_equal(record.get("acceptanceInventory"), {"verified": 46, "partial": 15, "planned": 0}) or record.get("targetCriterion") != "partial" or not strict_json_equal(record.get("acceptanceRegistration"), {"registered": False, "reason": "frozen-v1-authority-live-v2-migration-not-authorized"}) or record.get("liveMigrationAuthorized") is not False or not strict_json_equal(record.get("executionCounters"), ZERO_EXECUTION_COUNTERS) or not strict_json_equal(record.get("claimBoundary"), _ZERO_CLAIMS):
        raise AcceptanceAuthorityError("acceptance-rehearsal-record-invalid", "Rehearsal record boundaries drifted.")
    matrix = run_failure_matrix(root)
    if not strict_json_equal(record.get("failureMatrix"), matrix) or not all(row["status"] == "rejected" and row["expectedCode"] == row["observedCode"] for row in matrix):
        raise AcceptanceAuthorityError("acceptance-rehearsal-record-invalid", "Rehearsal record failure matrix drifted.")
    return copy.deepcopy(record)
