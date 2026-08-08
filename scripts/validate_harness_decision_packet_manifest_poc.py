#!/usr/bin/env python3
"""Replay and validate the dated thirteen-scenario manifest PoC evidence."""

from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from typing import Any, Callable


PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

try:
    from .harness_decision_packet import (
        DecisionPacketError,
        canonical_sha256,
        load_source_evidence_record,
        strict_json_equal,
    )
    from .harness_decision_packet_manifest import (
        BatchBindingError,
        build_canonical_probe_request,
        build_decision_packet_manifest,
        serialize_decision_packet_manifest,
        validate_decision_packet_manifest,
    )
    from .harness_decision_packet_v2 import build_decision_packet_v2
except ImportError:  # Direct script execution.
    from harness_decision_packet import (
        DecisionPacketError,
        canonical_sha256,
        load_source_evidence_record,
        strict_json_equal,
    )
    from harness_decision_packet_manifest import (
        BatchBindingError,
        build_canonical_probe_request,
        build_decision_packet_manifest,
        serialize_decision_packet_manifest,
        validate_decision_packet_manifest,
    )
    from harness_decision_packet_v2 import build_decision_packet_v2


ROOT = PROJECT_ROOT
EVIDENCE_PATH = Path(
    "registry/harness-decision-packet-thirteen-scenario-manifest-poc-2026-08-09.json"
)
EXPECTED_MANIFEST_PATH = Path(
    "tests/fixtures/harness-decision-packet-thirteen-scenario-manifest.json"
)
DOCUMENTATION_PATH = Path(
    "docs/strategy/HARNESS-DECISION-PACKET-THIRTEEN-SCENARIO-MANIFEST-POC-2026-08-09.md"
)
DESIGN_PATH = Path(
    "docs/superpowers/specs/2026-08-08-harness-decision-packet-thirteen-scenario-manifest-design.md"
)
PLAN_PATH = Path(
    "docs/superpowers/plans/2026-08-09-harness-decision-packet-thirteen-scenario-manifest.md"
)
BINDING_REGISTRY_PATH = Path("registry/harness-scenario-evidence-bindings-v1.json")
ACCEPTANCE_PATH = Path("registry/program-acceptance-map.json")
COVERAGE_PATH = Path(
    "registry/human-ai-collaboration-current-candidate-capability-coverage-reconciliation-2026-08-01.json"
)
AUTHORITY_PATHS = (
    Path("registry/skill-portfolio-current-authority.json"),
    COVERAGE_PATH,
    Path("registry/portfolio-tasktime-projection-contract-2026-08-06.json"),
    ACCEPTANCE_PATH,
    BINDING_REGISTRY_PATH,
)
SCHEMA_PATHS = (
    Path("schemas/harness-scenario-evidence-binding-registry-v1.schema.json"),
    Path("schemas/harness-decision-packet-v2.schema.json"),
    Path("schemas/harness-decision-packet-manifest-v1.schema.json"),
)
SCRIPT_PATHS = (
    Path("scripts/harness_scenario_evidence_binding.py"),
    Path("scripts/harness_decision_packet_v2.py"),
    Path("scripts/build_harness_decision_packet_v2.py"),
    Path("scripts/harness_decision_packet_manifest.py"),
    Path("scripts/build_harness_decision_packet_manifest.py"),
    Path("scripts/validate_harness_decision_packet_manifest_poc.py"),
)

MUTATION_CASE_IDS = [
    "binding-scenario-missing",
    "binding-scenario-extra",
    "binding-scenario-reordered",
    "binding-source-redirected",
    "binding-pointer-malformed",
    "binding-pointer-unresolved",
    "binding-identity-mismatch",
    "ops-pointer-removed",
    "document-level-promoted",
    "aggregate-identity-drift",
    "document-level-identity-appears",
    "authority-digest-drift",
    "source-digest-drift",
    "manifest-entry-removed",
    "manifest-entry-reordered",
    "manifest-digest-drift",
    "atomic-output-preserved",
]

EXPECTED_ERROR_CODES = {
    "binding-scenario-missing": "binding-scenario-set-drift",
    "binding-scenario-extra": "binding-scenario-set-drift",
    "binding-scenario-reordered": "binding-scenario-set-drift",
    "binding-source-redirected": "binding-source-path-drift",
    "binding-pointer-malformed": "binding-pointer-invalid",
    "binding-pointer-unresolved": "binding-pointer-unresolved",
    "binding-identity-mismatch": "binding-scenario-identity-mismatch",
    "ops-pointer-removed": "binding-scenario-identity-mismatch",
    "document-level-promoted": "document-level-identity-promotion",
    "aggregate-identity-drift": "binding-aggregate-identity-drift",
    "document-level-identity-appears": "document-level-identity-promotion",
    "authority-digest-drift": "authority-source-digest-drift",
    "source-digest-drift": "evidence-source-digest-drift",
    "manifest-entry-removed": "manifest-entry-set-drift",
    "manifest-entry-reordered": "manifest-entry-order-drift",
    "manifest-digest-drift": "manifest-digest-mismatch",
    "atomic-output-preserved": "batch-binding-failed",
}


def _copy_bound_sources(root: Path, temporary_root: Path) -> None:
    coverage = _load_object(root, COVERAGE_PATH)
    source_paths = {
        Path(path)
        for scenario in coverage["scenarioCoverage"]
        for path in scenario["evidenceSourcePaths"]
    }
    for relative in (*AUTHORITY_PATHS, *sorted(source_paths)):
        destination = temporary_root / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(root / relative, destination)


def _rewrite_json(
    root: Path, relative: Path, mutate: Callable[[dict[str, Any]], None]
) -> None:
    value = _load_object(root, relative)
    mutate(value)
    (root / relative).write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def _with_temporary_build(
    root: Path, mutate: Callable[[Path], None]
) -> None:
    with tempfile.TemporaryDirectory() as temporary_directory:
        temporary_root = Path(temporary_directory)
        _copy_bound_sources(root, temporary_root)
        mutate(temporary_root)
        build_decision_packet_manifest(temporary_root)


def _with_temporary_validation(
    root: Path, mutate: Callable[[Path], None]
) -> None:
    manifest = build_decision_packet_manifest(root)
    with tempfile.TemporaryDirectory() as temporary_directory:
        temporary_root = Path(temporary_directory)
        _copy_bound_sources(root, temporary_root)
        mutate(temporary_root)
        validate_decision_packet_manifest(temporary_root, manifest)


def _reseal_manifest(manifest: dict[str, Any]) -> None:
    manifest["manifestSha256"] = canonical_sha256(
        {key: value for key, value in manifest.items() if key != "manifestSha256"}
    )


def run_failure_matrix(root: Path) -> list[dict[str, str]]:
    """Run the seventeen approved mutations and return exact outcomes."""

    registry_path = BINDING_REGISTRY_PATH
    creative_path = Path(
        "registry/human-ai-collaboration-creative-capability-baseline-2026-07-31.json"
    )
    lifecycle_path = Path(
        "registry/human-ai-collaboration-software-lifecycle-thin-slice-zero-model-calibration-evidence-2026-07-27.json"
    )

    def mutate_binding_scenario_missing() -> None:
        _with_temporary_build(
            root,
            lambda temporary_root: _rewrite_json(
                temporary_root, registry_path, lambda value: value["bindings"].pop()
            ),
        )

    def mutate_binding_scenario_extra() -> None:
        def add_extra(value: dict[str, Any]) -> None:
            extra = copy.deepcopy(value["bindings"][-1])
            extra["scenarioId"] = "SE-EXTRA-01"
            value["bindings"].append(extra)

        _with_temporary_build(
            root,
            lambda temporary_root: _rewrite_json(
                temporary_root, registry_path, add_extra
            ),
        )

    def mutate_binding_scenario_reordered() -> None:
        def reorder(value: dict[str, Any]) -> None:
            value["bindings"][0], value["bindings"][1] = (
                value["bindings"][1],
                value["bindings"][0],
            )

        _with_temporary_build(
            root,
            lambda temporary_root: _rewrite_json(
                temporary_root, registry_path, reorder
            ),
        )

    def mutate_binding_source_redirected() -> None:
        _with_temporary_build(
            root,
            lambda temporary_root: _rewrite_json(
                temporary_root,
                registry_path,
                lambda value: value["bindings"][0].__setitem__(
                    "sourcePath", ACCEPTANCE_PATH.as_posix()
                ),
            ),
        )

    def mutate_binding_pointer_malformed() -> None:
        _with_temporary_build(
            root,
            lambda temporary_root: _rewrite_json(
                temporary_root,
                registry_path,
                lambda value: value["bindings"][0].__setitem__(
                    "identityPointers", ["scenarioBinding/scenarioId"]
                ),
            ),
        )

    def mutate_binding_pointer_unresolved() -> None:
        _with_temporary_build(
            root,
            lambda temporary_root: _rewrite_json(
                temporary_root,
                registry_path,
                lambda value: value["bindings"][0].__setitem__(
                    "identityPointers", ["/missing/scenarioId"]
                ),
            ),
        )

    def mutate_binding_identity_mismatch() -> None:
        _with_temporary_build(
            root,
            lambda temporary_root: _rewrite_json(
                temporary_root,
                creative_path,
                lambda value: value["scenarioBinding"].__setitem__(
                    "scenarioId", "GEN-WRONG-01"
                ),
            ),
        )

    def mutate_ops_pointer_removed() -> None:
        def remove_pointer(value: dict[str, Any]) -> None:
            binding = next(
                item
                for item in value["bindings"]
                if item["scenarioId"] == "SE-OPS-INCIDENT-01"
            )
            binding["identityPointers"].pop()

        _with_temporary_build(
            root,
            lambda temporary_root: _rewrite_json(
                temporary_root, registry_path, remove_pointer
            ),
        )

    def mutate_document_level_promoted() -> None:
        def promote(value: dict[str, Any]) -> None:
            binding = next(
                item
                for item in value["bindings"]
                if item["scenarioId"] == "SE-ARCH-DESIGN-01"
            )
            binding["bindingMode"] = "scenario-record"

        _with_temporary_build(
            root,
            lambda temporary_root: _rewrite_json(
                temporary_root, registry_path, promote
            ),
        )

    def mutate_aggregate_identity_drift() -> None:
        _with_temporary_build(
            root,
            lambda temporary_root: _rewrite_json(
                temporary_root,
                lifecycle_path,
                lambda value: value.__setitem__("scenarioId", "SE-E2E-OTHER-01"),
            ),
        )

    def mutate_document_level_identity_appears() -> None:
        _with_temporary_build(
            root,
            lambda temporary_root: _rewrite_json(
                temporary_root,
                lifecycle_path,
                lambda value: value.__setitem__(
                    "scenarios", [{"id": "SE-ARCH-DESIGN-01"}]
                ),
            ),
        )

    def mutate_authority_digest_drift() -> None:
        _with_temporary_validation(
            root,
            lambda temporary_root: (temporary_root / COVERAGE_PATH).write_bytes(
                (temporary_root / COVERAGE_PATH).read_bytes() + b"\n"
            ),
        )

    def mutate_source_digest_drift() -> None:
        _with_temporary_validation(
            root,
            lambda temporary_root: (temporary_root / creative_path).write_bytes(
                (temporary_root / creative_path).read_bytes() + b"\n"
            ),
        )

    def mutate_manifest_entry_removed() -> None:
        manifest = build_decision_packet_manifest(root)
        manifest["entries"].pop()
        _reseal_manifest(manifest)
        validate_decision_packet_manifest(root, manifest)

    def mutate_manifest_entry_reordered() -> None:
        manifest = build_decision_packet_manifest(root)
        manifest["entries"][0], manifest["entries"][1] = (
            manifest["entries"][1],
            manifest["entries"][0],
        )
        _reseal_manifest(manifest)
        validate_decision_packet_manifest(root, manifest)

    def mutate_manifest_digest_drift() -> None:
        manifest = build_decision_packet_manifest(root)
        manifest["manifestSha256"] = "0" * 64
        validate_decision_packet_manifest(root, manifest)

    def verify_atomic_output_preserved() -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            temporary_root = Path(temporary_directory)
            output = temporary_root / "manifest.json"
            sentinel = b"known-good\n"
            output.write_bytes(sentinel)
            result = subprocess.run(
                [
                    sys.executable,
                    "-B",
                    str(root / "scripts/build_harness_decision_packet_manifest.py"),
                    "--root",
                    str(temporary_root / "missing-root"),
                    "--output",
                    str(output),
                ],
                cwd=root,
                check=False,
                capture_output=True,
            )
            _require(result.returncode == 2, "Failed manifest CLI did not exit 2")
            _require(result.stdout == b"", "Failed manifest CLI wrote to stdout")
            error = json.loads(result.stderr)
            _require(
                type(error) is dict
                and error.get("code") == "batch-binding-failed"
                and type(error.get("issues")) is list,
                "Failed manifest CLI did not return batch-binding-failed",
            )
            _require(
                output.read_bytes() == sentinel,
                "Failed manifest CLI changed the existing output target",
            )
            _require(
                not list(output.parent.glob(f".{output.name}.*.tmp")),
                "Failed manifest CLI left sibling temporary output",
            )
            raise BatchBindingError(error["issues"])

    actions: dict[str, Callable[[], None]] = {
        "binding-scenario-missing": mutate_binding_scenario_missing,
        "binding-scenario-extra": mutate_binding_scenario_extra,
        "binding-scenario-reordered": mutate_binding_scenario_reordered,
        "binding-source-redirected": mutate_binding_source_redirected,
        "binding-pointer-malformed": mutate_binding_pointer_malformed,
        "binding-pointer-unresolved": mutate_binding_pointer_unresolved,
        "binding-identity-mismatch": mutate_binding_identity_mismatch,
        "ops-pointer-removed": mutate_ops_pointer_removed,
        "document-level-promoted": mutate_document_level_promoted,
        "aggregate-identity-drift": mutate_aggregate_identity_drift,
        "document-level-identity-appears": mutate_document_level_identity_appears,
        "authority-digest-drift": mutate_authority_digest_drift,
        "source-digest-drift": mutate_source_digest_drift,
        "manifest-entry-removed": mutate_manifest_entry_removed,
        "manifest-entry-reordered": mutate_manifest_entry_reordered,
        "manifest-digest-drift": mutate_manifest_digest_drift,
        "atomic-output-preserved": verify_atomic_output_preserved,
    }
    results: list[dict[str, str]] = []
    for case_id in MUTATION_CASE_IDS:
        expected = EXPECTED_ERROR_CODES[case_id]
        try:
            actions[case_id]()
        except (DecisionPacketError, BatchBindingError) as exc:
            observed = exc.code
            if (
                case_id != "atomic-output-preserved"
                and isinstance(exc, BatchBindingError)
                and exc.issues
            ):
                observed = str(exc.issues[0]["code"])
            results.append(
                {
                    "caseId": case_id,
                    "status": "rejected" if observed == expected else "wrong-error",
                    "expectedCode": expected,
                    "observedCode": observed,
                }
            )
        else:
            results.append(
                {
                    "caseId": case_id,
                    "status": "accepted",
                    "expectedCode": expected,
                    "observedCode": "none",
                }
            )
    return results


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def _load_object(root: Path, relative: Path) -> dict[str, Any]:
    value = json.loads((root / relative).read_text(encoding="utf-8"))
    _require(type(value) is dict, f"Expected JSON object at {relative.as_posix()}")
    return value


def _file_sha256(root: Path, relative: Path) -> str:
    return hashlib.sha256((root / relative).read_bytes()).hexdigest()


def _file_binding(root: Path, relative: Path) -> dict[str, str]:
    return {"path": relative.as_posix(), "sha256": _file_sha256(root, relative)}


def validate_repository_record(root: Path = ROOT) -> dict[str, object]:
    """Replay the checked manifest, mutations, and narrow claim boundaries."""

    record = _load_object(root, EVIDENCE_PATH)
    expected_fields = {
        "schema", "id", "date", "status", "scenarioCount", "bindingCounts",
        "selectedRoute", "acceptanceAssessment", "acceptanceInventory", "design",
        "plan", "documentation", "manifestFixture", "bindingRegistry", "schemas",
        "scripts", "authorityBindings", "manifestSha256", "mutationResults",
        "executionCounters", "claimBoundary", "authorityBoundary",
        "acceptanceRegistration",
    }
    _require(set(record) == expected_fields, "Manifest PoC evidence fields drifted")
    _require(
        strict_json_equal(record["schema"], 1)
        and strict_json_equal(
            record["id"],
            "harness-decision-packet-thirteen-scenario-manifest-poc-2026-08-09",
        )
        and strict_json_equal(record["date"], "2026-08-09")
        and strict_json_equal(
            record["status"],
            "verified-zero-model-thirteen-scenario-binding-and-atomic-manifest-mechanism-only",
        )
        and strict_json_equal(record["scenarioCount"], 13)
        and strict_json_equal(
            record["bindingCounts"],
            {"scenarioRecord": 11, "documentLevelSupport": 2},
        )
        and strict_json_equal(record["selectedRoute"], None),
        "Manifest PoC evidence identity or scenario boundary drifted",
    )

    expected_file_bindings = {
        "design": _file_binding(root, DESIGN_PATH),
        "plan": _file_binding(root, PLAN_PATH),
        "documentation": _file_binding(root, DOCUMENTATION_PATH),
        "manifestFixture": _file_binding(root, EXPECTED_MANIFEST_PATH),
    }
    _require(
        all(
            strict_json_equal(record[key], value)
            for key, value in expected_file_bindings.items()
        ),
        "Manifest PoC exact file binding drifted",
    )
    _require(
        strict_json_equal(
            record["schemas"],
            [_file_binding(root, path) for path in SCHEMA_PATHS],
        )
        and strict_json_equal(
            record["scripts"],
            [_file_binding(root, path) for path in SCRIPT_PATHS],
        ),
        "Manifest PoC schema or script binding drifted",
    )

    manifest = _load_object(root, EXPECTED_MANIFEST_PATH)
    validate_decision_packet_manifest(root, manifest)
    rebuilt = build_decision_packet_manifest(root)
    _require(
        serialize_decision_packet_manifest(rebuilt)
        == (root / EXPECTED_MANIFEST_PATH).read_bytes(),
        "Checked manifest is not a byte-stable current rebuild",
    )
    _require(
        strict_json_equal(record["manifestSha256"], manifest["manifestSha256"])
        and strict_json_equal(
            record["authorityBindings"], manifest["authorityBinding"]
        )
        and strict_json_equal(
            record["executionCounters"], manifest["executionCounters"]
        ),
        "Manifest PoC manifest or authority projection drifted",
    )
    binding_registry = load_source_evidence_record(root, BINDING_REGISTRY_PATH)
    _require(
        strict_json_equal(
            record["bindingRegistry"],
            {key: binding_registry[key] for key in ("path", "id", "sha256")},
        ),
        "Manifest PoC binding-registry identity drifted",
    )
    for entry in manifest["entries"]:
        packet = build_decision_packet_v2(
            root, build_canonical_probe_request(entry["scenarioId"])
        )
        _require(
            strict_json_equal(packet["packetSha256"], entry["packetSha256"]),
            f"Manifest packet digest is not independently reproducible: {entry['scenarioId']}",
        )
    _require(
        all(
            strict_json_equal(entry["selectedRoute"], None)
            for entry in manifest["entries"]
        )
        and all(
            strict_json_equal(value, 0)
            for value in manifest["executionCounters"].values()
        )
        and all(
            strict_json_equal(value, False)
            for value in manifest["authorizationGates"].values()
        )
        and all(
            strict_json_equal(value, False)
            for value in manifest["claimBoundary"].values()
        ),
        "Manifest execution, route, authorization, or claim boundary was promoted",
    )

    mutation_results = run_failure_matrix(root)
    _require(
        strict_json_equal(record["mutationResults"], mutation_results)
        and strict_json_equal(
            [item["caseId"] for item in mutation_results], MUTATION_CASE_IDS
        )
        and all(
            strict_json_equal(item["status"], "rejected")
            for item in mutation_results
        ),
        "Manifest PoC failure matrix did not fail closed",
    )
    _require(
        strict_json_equal(
            record["claimBoundary"],
            {
                "naturalLanguageInterpretationProved": False,
                "taskTimeSelectionProved": False,
                "behaviorProved": False,
                "valueProved": False,
                "crossHostPortabilityProved": False,
                "productionReadinessProved": False,
                "releaseEligibilityProved": False,
                "residualGapProved": False,
            },
        )
        and strict_json_equal(
            record["authorityBoundary"],
            {
                "installAuthorized": False,
                "enablementAuthorized": False,
                "accountConnectionAuthorized": False,
                "modelDispatchAuthorized": False,
                "candidateExecutionAuthorized": False,
                "pluginExecutionAuthorized": False,
                "managerMutationAuthorized": False,
                "consumerMutationAuthorized": False,
                "publicationAuthorized": False,
                "releaseAuthorized": False,
                "acceptancePromotionAuthorized": False,
                "goalCloseoutAuthorized": False,
            },
        ),
        "Manifest PoC claim or lifecycle authority was promoted",
    )

    acceptance = _load_object(root, ACCEPTANCE_PATH)
    criteria = acceptance["acceptanceCriteria"]
    criterion = next(
        item
        for item in criteria
        if item["id"] == "acceptance.decision-ready-consumer-projection"
    )
    inventory = {
        state: sum(item["assessment"] == state for item in criteria)
        for state in ("verified", "partial", "planned")
    }
    _require(
        strict_json_equal(criterion["assessment"], "partial")
        and "evidence.harness-decision-packet-thirteen-scenario-manifest-poc-2026-08-09"
        not in criterion["evidenceIds"]
        and not any(
            item["id"]
            == "evidence.harness-decision-packet-thirteen-scenario-manifest-poc-2026-08-09"
            for item in acceptance["evidence"]
        )
        and strict_json_equal(record["acceptanceAssessment"], "partial")
        and strict_json_equal(record["acceptanceInventory"], inventory)
        and strict_json_equal(
            inventory, {"verified": 46, "partial": 15, "planned": 0}
        ),
        "Manifest PoC acceptance boundary or 46/15/0 inventory drifted",
    )
    _require(
        strict_json_equal(
            _file_sha256(root, ACCEPTANCE_PATH),
            "c9d0fb437fb3eae93ffd144a2e3ee418dca90d96e5a266b61d7c7ec3efa6079f",
        )
        and strict_json_equal(
            _file_sha256(
                root,
                Path("tests/fixtures/harness-decision-packet-gen-research-01.json"),
            ),
            "58410f9576fbbc2f006135d97184d29a9996b1eb11abeaf07988a3a5acf4fc22",
        )
        and strict_json_equal(
            record["acceptanceRegistration"],
            {
                "registered": False,
                "evidenceId": "evidence.harness-decision-packet-thirteen-scenario-manifest-poc-2026-08-09",
                "reason": "deferred-frozen-v1-acceptance-authority-requires-versioned-migration",
                "futureMigrationAuthorized": False,
            },
        ),
        "Frozen acceptance-map, packet-v1 fixture, or non-registration boundary drifted",
    )
    return record


def main() -> int:
    record = validate_repository_record(ROOT)
    print(
        "Harness thirteen-scenario decision-manifest PoC verified: "
        f"{len(record['mutationResults'])} fail-closed mutations; "
        f"status={record['status']}."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
