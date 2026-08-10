# Program Acceptance Authority v2 Zero-Model Rehearsal Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build and verify an isolated zero-model rehearsal that migrates the frozen program acceptance map into immutable v2 snapshots, registers the thirteen-scenario manifest evidence in a separate generation, atomically selects and rolls back candidate state, and leaves all live v1 authority and fixture bytes unchanged.

**Architecture:** A pure authority module creates complete immutable snapshots, typed transition receipts, and selectors. A separate inventory module discovers and classifies every tracked reference to the legacy authority. A rehearsal orchestrator writes only to a new disposable root, validates historical and candidate-current modes, rolls the selector back without deleting history, removes the root, and emits an independently governed result record; the repository's live acceptance authority remains v1.

**Tech Stack:** Python 3 standard library (`argparse`, `copy`, `hashlib`, `json`, `os`, `pathlib`, `shutil`, `subprocess`, `tempfile`, `typing`, `unittest`, `unittest.mock`), JSON Schema Draft 2020-12 documents, repository JSON registries, Markdown, Git, and local `scripts/verify.py` integration.

**Authoritative Design:** `docs/superpowers/specs/2026-08-10-program-acceptance-authority-v2-design.md`.

## Global Constraints

- Work directly in `C:\Projects\agent-autonomy-harness` on `main`; do not create a branch or worktree for this sequential mainline slice.
- Preserve `registry/program-acceptance-map.json` byte for byte with SHA-256 `c9d0fb437fb3eae93ffd144a2e3ee418dca90d96e5a266b61d7c7ec3efa6079f`.
- Preserve `registry/curation-program-plan.json` byte for byte with SHA-256 `38bba19b4f4f8471ea7ebaa80765e4110fa169ff892eec3784e3316783a88bd3`.
- Preserve `tests/fixtures/harness-decision-packet-gen-research-01.json` byte for byte with SHA-256 `58410f9576fbbc2f006135d97184d29a9996b1eb11abeaf07988a3a5acf4fc22`.
- Preserve `tests/fixtures/harness-decision-packet-thirteen-scenario-manifest.json` byte for byte with SHA-256 `ef29ec4de82091dfba3b2e0cfd49c5570cc40410b2beadfd3b5be5bc003176c3`.
- Do not create `registry/program-acceptance-authority/current.json` or any other live selector, snapshot, receipt, or program-plan v2 authority.
- Rehearsal generation g000001 is a structural migration with no business-state delta. Generation g000002 adds exactly one manifest evidence row and one reciprocal criterion link.
- Keep all 61 criteria and 46 verified / 15 partial / 0 planned in g000001 and g000002. Keep `acceptance.decision-ready-consumer-projection` at `partial`.
- Keep structural migration, evidence registration, assessment transition, and rollback as mutually exclusive transaction classes.
- Derive the migration-inventory baseline from the live tracked reference set. Do not preserve an obsolete reference count merely to make a test pass.
- A historical consumer remains bound to v1. A simulated current consumer resolves the rehearsal selector. A version-neutral validator receives documents and bindings explicitly and owns no current registry path.
- Use canonical JSON with `ensure_ascii=False`, `sort_keys=True`, and `separators=(",", ":")`; append exactly one trailing newline for persisted JSON fixtures and records.
- Compute a file digest over exact bytes. Compute a body digest only where an existing canonical-object helper explicitly requires it. Do not put a file's own digest inside that file.
- File-output mode accepts only a new empty disposable root outside the repository. It exposes no production activation option.
- Snapshot and receipt files are immutable. Rollback creates a receipt and changes only the selector; it does not delete or rewrite history.
- Any failed file-output operation writes no stdout, returns exit code 2, emits stable JSON on stderr, and preserves a pre-existing selector sentinel byte for byte.
- Use `strict_json_equal` from `scripts/harness_decision_packet.py` for exact JSON comparisons so `true`, `1`, and `1.0` cannot alias.
- Use `apply_patch` for tracked repository writes. Test and CLI temporary outputs may use operating-system temporary directories.
- Do not install, enable, invoke, connect an account, dispatch a model, mutate CC Switch or a consumer, publish, release, delete user data, promote acceptance, or mark the Harness complete.
- Run focused tests first, then the direct validator, the complete unittest suite serially, and `python -B scripts/verify.py`. GitHub Actions is optional corroboration, never the primary or sole acceptance surface.
- Each implementation task commits but does not push. Push requires a later controller decision after specification and quality review.
- A missing module or symbol is interface preflight, not sufficient TDD RED. Each task's first behavioral run must reach a callable interface and fail by assertion or the task's declared typed `acceptance-authority-not-implemented` error.

---

## File Structure

**Create:**

- `schemas/program-acceptance-authority-v2.schema.json` — complete immutable snapshot shape.
- `schemas/program-acceptance-current-selector-v1.schema.json` — candidate-current selector shape.
- `schemas/program-acceptance-transition-receipt-v1.schema.json` — structural, evidence, assessment, and rollback receipt shape.
- `schemas/program-acceptance-migration-inventory-v1.schema.json` — exact tracked-reference occurrence inventory shape.
- `scripts/program_acceptance_authority_v2.py` — legacy locks, bindings, snapshot/plan construction, transition validation, historical/current resolution, and rollback semantics.
- `scripts/program_acceptance_migration_inventory.py` — tracked-file discovery, per-occurrence identity, classification validation, and exact-set reconciliation.
- `scripts/program_acceptance_authority_v2_rehearsal.py` — pure rehearsal bundle, staged writes, selector replacement, rollback, cleanup, and result projection.
- `scripts/build_program_acceptance_authority_v2_rehearsal.py` — stdout or disposable-root rehearsal CLI with structured errors.
- `scripts/validate_program_acceptance_authority_v2_rehearsal.py` — repository record validation and real-path failure-matrix replay.
- `tests/test_program_acceptance_authority_v2.py` — legacy, schema, snapshot, transition, selector, historical/current, and rollback unit tests.
- `tests/test_program_acceptance_migration_inventory.py` — live occurrence discovery and classification tests.
- `tests/test_program_acceptance_authority_v2_rehearsal.py` — fixture, CLI, atomicity, cleanup, record, and mutation-matrix tests.
- `tests/fixtures/program-acceptance-authority-v2-rehearsal/curation-program-plan-v2.json` — candidate companion plan.
- `tests/fixtures/program-acceptance-authority-v2-rehearsal/snapshots/v2/g000001.json` — semantics-equivalent structural snapshot.
- `tests/fixtures/program-acceptance-authority-v2-rehearsal/snapshots/v2/g000002.json` — evidence-registration snapshot.
- `tests/fixtures/program-acceptance-authority-v2-rehearsal/transitions/g000000-to-g000001.json` — structural-migration receipt.
- `tests/fixtures/program-acceptance-authority-v2-rehearsal/transitions/g000001-to-g000002.json` — evidence-registration receipt.
- `tests/fixtures/program-acceptance-authority-v2-rehearsal/transitions/g000002-to-g000001-rollback.json` — rollback receipt.
- `tests/fixtures/program-acceptance-authority-v2-rehearsal/selectors/current-g000002.json` — pre-rollback candidate selector.
- `tests/fixtures/program-acceptance-authority-v2-rehearsal/selectors/current-g000001-rollback.json` — post-rollback candidate selector.
- `registry/program-acceptance-authority-v2-migration-inventory-2026-08-10.json` — reviewed occurrence-by-occurrence migration classification.
- `registry/program-acceptance-authority-v2-zero-model-rehearsal-2026-08-10.json` — independent rehearsal evidence, not registered in v1.
- `docs/strategy/PROGRAM-ACCEPTANCE-AUTHORITY-V2-ZERO-MODEL-REHEARSAL-2026-08-10.md` — human-readable result and claim ceiling.

**Modify:**

- `scripts/verify.py` — require the new governed artifacts and call the focused repository validator once.
- `tests/test_verify_integration.py` — prove normal verifier integration and isolate the expensive matrix from unrelated mutation helpers.
- `docs/strategy/RESEARCH-AND-POC-PLAN.md` — record the bounded rehearsal result and separate live-migration gate.
- `docs/operations/CURRENT-GOAL-MODE-PROMPT.md` — replace the “future versioned migration” wording with the proved rehearsal and still-unapproved live transition.
- `docs/operations/CONTINUATION.md` — append the exact commit, tests, evidence boundary, and next authorization gate.

**Must remain unmodified:**

- `registry/program-acceptance-map.json`;
- `registry/curation-program-plan.json`;
- `tests/fixtures/harness-decision-packet-gen-research-01.json`;
- `tests/fixtures/harness-decision-packet-thirteen-scenario-manifest.json`;
- existing packet-v1 and packet-v2 schemas and builders; and
- historical registry records, plans, specifications, and evidence documents.

README and README.zh-CN remain unchanged because the rehearsal adds no active public product capability or current authority. Recheck their wording before the final documentation commit; if no current-state sentence becomes false, retain exact bytes.

---

### Task 1: Lock legacy identities and define strict contract shapes

**Files:**
- Create: `schemas/program-acceptance-authority-v2.schema.json`
- Create: `schemas/program-acceptance-current-selector-v1.schema.json`
- Create: `schemas/program-acceptance-transition-receipt-v1.schema.json`
- Create: `schemas/program-acceptance-migration-inventory-v1.schema.json`
- Create: `scripts/program_acceptance_authority_v2.py`
- Create: `tests/test_program_acceptance_authority_v2.py`

**Interfaces:**
- Consumes: repository root `Path` and exact legacy files.
- Produces: `AcceptanceAuthorityError`, `file_sha256(root, relative) -> str`, `canonical_file_bytes(value) -> bytes`, `binding_for_bytes(*, authority_schema, authority_id, generation, path, data) -> dict[str, object]`, and `validate_legacy_locks(root, *, expected=None) -> dict[str, dict[str, object]]`.

- [ ] **Step 1: Add a callable skeleton and failing behavioral tests**

Create `scripts/program_acceptance_authority_v2.py` with the public interface present but deliberately not implemented:

```python
from __future__ import annotations

from pathlib import Path
from collections.abc import Mapping
from typing import Any


class AcceptanceAuthorityError(ValueError):
    def __init__(self, code: str, message: str, *, path: str | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.path = path


def validate_legacy_locks(
    root: Path,
    *,
    expected: Mapping[str, str] | None = None,
) -> dict[str, dict[str, Any]]:
    raise AcceptanceAuthorityError(
        "acceptance-authority-not-implemented",
        "Legacy lock validation has not been implemented.",
    )
```

Create `tests/test_program_acceptance_authority_v2.py` with:

```python
import json
from pathlib import Path
import unittest

from scripts.program_acceptance_authority_v2 import (
    AcceptanceAuthorityError,
    validate_legacy_locks,
)

ROOT = Path(__file__).resolve().parent.parent


class ProgramAcceptanceAuthorityLegacyTests(unittest.TestCase):
    def test_exact_legacy_locks_are_current(self) -> None:
        locks = validate_legacy_locks(ROOT)
        self.assertEqual(
            "c9d0fb437fb3eae93ffd144a2e3ee418dca90d96e5a266b61d7c7ec3efa6079f",
            locks["acceptance"]["sha256"],
        )
        self.assertEqual(
            "38bba19b4f4f8471ea7ebaa80765e4110fa169ff892eec3784e3316783a88bd3",
            locks["programPlan"]["sha256"],
        )
        self.assertEqual(
            "58410f9576fbbc2f006135d97184d29a9996b1eb11abeaf07988a3a5acf4fc22",
            locks["packetFixture"]["sha256"],
        )
        self.assertEqual(
            "ef29ec4de82091dfba3b2e0cfd49c5570cc40410b2beadfd3b5be5bc003176c3",
            locks["manifestFixture"]["sha256"],
        )

    def test_legacy_lock_drift_has_a_typed_code(self) -> None:
        with self.assertRaises(AcceptanceAuthorityError) as raised:
            validate_legacy_locks(ROOT, expected={"acceptance": "0" * 64})
        self.assertEqual("legacy-authority-drift", raised.exception.code)
```

Both calls must raise `acceptance-authority-not-implemented`, proving the callable path was reached.

- [ ] **Step 2: Run the focused RED**

```powershell
python -B -m unittest tests.test_program_acceptance_authority_v2.ProgramAcceptanceAuthorityLegacyTests -v
```

Expected: both tests ERROR with typed code `acceptance-authority-not-implemented`; no import or loader error.

- [ ] **Step 3: Implement byte locks, canonical bytes, and strict bindings**

Use these exact constants and algorithms:

```python
LEGACY_LOCKS = {
    "acceptance": (
        Path("registry/program-acceptance-map.json"),
        "curation-program-acceptance-map-v1",
        "c9d0fb437fb3eae93ffd144a2e3ee418dca90d96e5a266b61d7c7ec3efa6079f",
        "legacy-authority-drift",
    ),
    "programPlan": (
        Path("registry/curation-program-plan.json"),
        "curation-program-plan-v1",
        "38bba19b4f4f8471ea7ebaa80765e4110fa169ff892eec3784e3316783a88bd3",
        "legacy-program-plan-drift",
    ),
    "packetFixture": (
        Path("tests/fixtures/harness-decision-packet-gen-research-01.json"),
        "harness-decision-packet-v1:harness.core.poc.gen-research-01",
        "58410f9576fbbc2f006135d97184d29a9996b1eb11abeaf07988a3a5acf4fc22",
        "legacy-packet-fixture-drift",
    ),
    "manifestFixture": (
        Path("tests/fixtures/harness-decision-packet-thirteen-scenario-manifest.json"),
        "harness-decision-packet-thirteen-scenario-manifest-v1",
        "ef29ec4de82091dfba3b2e0cfd49c5570cc40410b2beadfd3b5be5bc003176c3",
        "legacy-manifest-fixture-drift",
    ),
}


def canonical_file_bytes(value: object) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        .encode("utf-8")
        + b"\n"
    )


def file_sha256(root: Path, relative: Path) -> str:
    return hashlib.sha256((root / relative).read_bytes()).hexdigest()
```

`validate_legacy_locks` loads JSON objects only after byte identity passes, validates exact IDs, and returns public bindings containing `id`, `path`, and `sha256`. `binding_for_bytes` additionally carries `authoritySchema` and `generation`; generation is `None` only for legacy v1.

- [ ] **Step 4: Add strict JSON schemas**

All four schemas use Draft 2020-12, `type: object`, `additionalProperties: false`, and exact `required` arrays.

Authority v2 required fields:

```json
[
  "schema", "id", "authoritySeriesId", "generation",
  "predecessorBinding", "programPlanBinding", "assessmentVocabulary",
  "objectives", "acceptanceCriteria", "verifications", "evidence"
]
```

Selector v1 required fields:

```json
[
  "schema", "id", "authoritySeriesId", "selectionMode",
  "activeSnapshotBinding", "activeTransitionBinding", "programPlanBinding",
  "activationAuthorized", "executionCounters"
]
```

Receipt v1 required fields:

```json
[
  "schema", "id", "authoritySeriesId", "transactionType",
  "fromSnapshotBinding", "toSnapshotBinding", "fromProgramPlanBinding",
  "toProgramPlanBinding", "delta", "invariants", "authorizationBoundary",
  "executionCounters", "claimBoundary"
]
```

Inventory v1 required fields:

```json
[
  "schema", "id", "date", "status", "sourcePatterns",
  "baselineObservation", "occurrences", "claimBoundary"
]
```

Use integer `const`, boolean `const`, strict 64-lowercase-hex patterns, non-empty strings, and `enum` values from the approved design. Do not use broad `number` types for integer generations or counters.

- [ ] **Step 5: Add schema-shape and bool/int alias tests, then run GREEN**

Add tests that load each schema, assert the exact required field set, and mutate `schema`, `generation`, `activationAuthorized`, and every counter with `True`, `1`, and `1.0`. Runtime validation added in later tasks must use `type(value) is int` and `type(value) is bool`; schema documents alone are not acceptance.

```powershell
python -B -m unittest tests.test_program_acceptance_authority_v2.ProgramAcceptanceAuthorityLegacyTests -v
```

Expected: PASS.

- [ ] **Step 6: Commit Task 1**

```powershell
git add schemas/program-acceptance-*.schema.json scripts/program_acceptance_authority_v2.py tests/test_program_acceptance_authority_v2.py
git commit -m "feat: lock versioned acceptance authority contracts"
```

---

### Task 2: Build semantics-equivalent g000001 and evidence-only g000002 snapshots

**Files:**
- Modify: `scripts/program_acceptance_authority_v2.py`
- Modify: `tests/test_program_acceptance_authority_v2.py`
- Create: `tests/fixtures/program-acceptance-authority-v2-rehearsal/curation-program-plan-v2.json`
- Create: `tests/fixtures/program-acceptance-authority-v2-rehearsal/snapshots/v2/g000001.json`
- Create: `tests/fixtures/program-acceptance-authority-v2-rehearsal/snapshots/v2/g000002.json`

**Interfaces:**
- Consumes: validated v1 acceptance and program-plan objects plus exact source bindings from Task 1.
- Produces: `build_candidate_program_plan_v2(legacy_plan) -> dict[str, object]`, `build_structural_snapshot_v2(legacy_acceptance, *, predecessor_binding, program_plan_binding) -> dict[str, object]`, `build_evidence_snapshot_v2(g000001) -> dict[str, object]`, `validate_authority_snapshot(snapshot, *, predecessor=None, program_plan_binding=None) -> None`, `authority_business_projection(document) -> dict[str, object]`, and `assessment_inventory(document) -> dict[str, int]`.

- [ ] **Step 1: Write failing g000001/g000002 behavior tests**

Add:

```python
class ProgramAcceptanceAuthoritySnapshotTests(unittest.TestCase):
    def setUp(self) -> None:
        self.legacy = json.loads((ROOT / "registry/program-acceptance-map.json").read_text(encoding="utf-8"))
        self.plan = json.loads((ROOT / "registry/curation-program-plan.json").read_text(encoding="utf-8"))
        self.locks = validate_legacy_locks(ROOT)

    def build_g1(self) -> dict[str, object]:
        candidate_plan = build_candidate_program_plan_v2(self.plan)
        plan_binding = binding_for_bytes(
            authority_schema=2,
            authority_id="curation-program-plan-v2",
            generation=1,
            path="curation-program-plan-v2.json",
            data=canonical_file_bytes(candidate_plan),
        )
        return build_structural_snapshot_v2(
            self.legacy,
            predecessor_binding={
                **self.locks["acceptance"],
                "authoritySchema": 1,
                "generation": None,
            },
            program_plan_binding=plan_binding,
        )

    def test_g000001_is_business_semantics_equivalent_to_v1(self) -> None:
        g1 = self.build_g1()
        self.assertEqual(authority_business_projection(self.legacy), authority_business_projection(g1))
        self.assertEqual(1, g1["generation"])

    def test_g000002_adds_only_manifest_evidence_and_reciprocal_link(self) -> None:
        g1 = self.build_g1()
        g2 = build_evidence_snapshot_v2(g1)
        self.assertEqual(2, g2["generation"])
        self.assertEqual(len(g1["evidence"]) + 1, len(g2["evidence"]))
        criterion = next(row for row in g2["acceptanceCriteria"] if row["id"] == TARGET_CRITERION_ID)
        self.assertEqual("partial", criterion["assessment"])
        self.assertEqual({"verified": 46, "partial": 15, "planned": 0}, assessment_inventory(g2))
```

Public builders initially raise `acceptance-authority-not-implemented` so the tests reach the declared interface.

- [ ] **Step 2: Run the snapshot RED**

```powershell
python -B -m unittest tests.test_program_acceptance_authority_v2.ProgramAcceptanceAuthoritySnapshotTests -v
```

Expected: ERROR with typed code `acceptance-authority-not-implemented`.

- [ ] **Step 3: Implement the candidate plan and snapshot builders**

Candidate plan v2 is a deep copy of v1 with these exact changes:

```python
candidate["schema"] = 2
candidate["id"] = "curation-program-plan-v2"
candidate["acceptanceAuthoritySelector"] = "program-acceptance-authority/current.json"
del candidate["acceptanceMap"]
```

Preserve the order and exact values of every other program-plan field. Reject any additional difference with `acceptance-structural-migration-overreach`.

Use:

```python
AUTHORITY_SERIES_ID = "curation-program-acceptance-authority-v2"
TARGET_CRITERION_ID = "acceptance.decision-ready-consumer-projection"
MANIFEST_EVIDENCE_ID = "evidence.harness-decision-packet-thirteen-scenario-manifest-poc-2026-08-09"
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
```

`authority_business_projection` returns exactly `assessmentVocabulary`, `objectives`, `acceptanceCriteria`, `verifications`, and `evidence`. g000001 copies those five values without normalization. g000002 deep-copies g000001, changes its ID, generation, and predecessor binding, appends the exact evidence row, and appends its ID to the target criterion. It rejects a pre-existing evidence ID.

- [ ] **Step 4: Implement strict snapshot validation and delta checks**

Validation requires exact top-level fields, actual Python JSON types, exact series ID, a positive integer generation, a predecessor generation of `None` only for v1, and strict program-plan/source bindings. Reuse the v1 map relationship checks through a focused pure helper copied out of the existing path-owning assumptions; do not call `scripts.verify.validate_program_acceptance_map` from the new core.

Add adversarial tests for:

```text
acceptance-authority-schema-invalid
acceptance-authority-series-invalid
acceptance-authority-generation-invalid
acceptance-authority-predecessor-mismatch
acceptance-program-plan-binding-drift
acceptance-structural-migration-overreach
acceptance-evidence-registration-overreach
acceptance-assessment-promotion-forbidden
acceptance-inventory-count-drift
acceptance-evidence-link-asymmetric
acceptance-evidence-id-duplicate
acceptance-evidence-source-missing
acceptance-evidence-source-drift
```

Each test asserts `raised.exception.code`, including bool/int/float aliases for schema, generation, counts, and assessment-related exact comparisons.

- [ ] **Step 5: Generate checked candidate fixtures and prove exact replay**

Use a one-off invocation of the module's canonical serializers only after all unit tests are GREEN. The checked fixture test rebuilds the candidate plan, g000001, and g000002 from live locked v1 inputs and compares exact bytes with the three fixture files.

```powershell
python -B -m unittest tests.test_program_acceptance_authority_v2.ProgramAcceptanceAuthoritySnapshotTests -v
```

Expected: PASS, with 61 criteria and 46/15/0 in both snapshots.

- [ ] **Step 6: Commit Task 2**

```powershell
git add scripts/program_acceptance_authority_v2.py tests/test_program_acceptance_authority_v2.py tests/fixtures/program-acceptance-authority-v2-rehearsal/curation-program-plan-v2.json tests/fixtures/program-acceptance-authority-v2-rehearsal/snapshots
git commit -m "feat: build immutable acceptance authority snapshots"
```

---

### Task 3: Add typed receipts, current/historical resolution, and rollback

**Files:**
- Modify: `scripts/program_acceptance_authority_v2.py`
- Modify: `tests/test_program_acceptance_authority_v2.py`
- Create: `tests/fixtures/program-acceptance-authority-v2-rehearsal/transitions/g000000-to-g000001.json`
- Create: `tests/fixtures/program-acceptance-authority-v2-rehearsal/transitions/g000001-to-g000002.json`
- Create: `tests/fixtures/program-acceptance-authority-v2-rehearsal/transitions/g000002-to-g000001-rollback.json`
- Create: `tests/fixtures/program-acceptance-authority-v2-rehearsal/selectors/current-g000002.json`
- Create: `tests/fixtures/program-acceptance-authority-v2-rehearsal/selectors/current-g000001-rollback.json`

**Interfaces:**
- Consumes: canonical snapshot and plan bytes from Task 2.
- Produces: `build_transition_receipt(transaction_type, *, from_snapshot_binding, to_snapshot_binding, from_program_plan_binding, to_program_plan_binding, from_document, to_document) -> dict[str, object]`, `validate_transition_receipt(receipt, *, from_document, to_document) -> None`, `build_selector(*, snapshot_binding, transition_binding, program_plan_binding) -> dict[str, object]`, `resolve_historical_authority(root, binding, *, frozen_program_plan_binding=None) -> dict[str, object]`, `resolve_current_authority(root, selector_path) -> dict[str, object]`, and `build_rollback_receipt(*, from_snapshot_binding, to_snapshot_binding, active_program_plan_binding, ancestor_bindings) -> dict[str, object]`.

- [ ] **Step 1: Write failing receipt and resolver tests**

Add this concrete setup and the two transaction assertions:

```python
FIXTURE_ROOT = ROOT / "tests/fixtures/program-acceptance-authority-v2-rehearsal"


class ProgramAcceptanceAuthorityTransitionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.legacy = json.loads((ROOT / "registry/program-acceptance-map.json").read_text(encoding="utf-8"))
        self.g1_path = FIXTURE_ROOT / "snapshots/v2/g000001.json"
        self.g2_path = FIXTURE_ROOT / "snapshots/v2/g000002.json"
        self.plan_path = FIXTURE_ROOT / "curation-program-plan-v2.json"
        self.g1 = json.loads(self.g1_path.read_text(encoding="utf-8"))
        self.g2 = json.loads(self.g2_path.read_text(encoding="utf-8"))
        self.plan = json.loads(self.plan_path.read_text(encoding="utf-8"))
        locks = validate_legacy_locks(ROOT)
        self.legacy_binding = {
            **locks["acceptance"],
            "authoritySchema": 1,
            "generation": None,
        }
        self.legacy_plan_binding = {
            **locks["programPlan"],
            "authoritySchema": 1,
            "generation": None,
        }
        self.candidate_plan_binding = binding_for_bytes(
            authority_schema=2,
            authority_id=self.plan["id"],
            generation=1,
            path="curation-program-plan-v2.json",
            data=self.plan_path.read_bytes(),
        )
        self.g1_binding = binding_for_bytes(
            authority_schema=2,
            authority_id=self.g1["id"],
            generation=1,
            path="snapshots/v2/g000001.json",
            data=self.g1_path.read_bytes(),
        )
        self.g2_binding = binding_for_bytes(
            authority_schema=2,
            authority_id=self.g2["id"],
            generation=2,
            path="snapshots/v2/g000002.json",
            data=self.g2_path.read_bytes(),
        )

    def test_structural_and_evidence_receipts_have_disjoint_deltas(self) -> None:
        structural = build_transition_receipt(
            "structural-migration",
            from_snapshot_binding=self.legacy_binding,
            to_snapshot_binding=self.g1_binding,
            from_program_plan_binding=self.legacy_plan_binding,
            to_program_plan_binding=self.candidate_plan_binding,
            from_document=self.legacy,
            to_document=self.g1,
        )
        self.assertEqual([], structural["delta"]["evidenceAdded"])
        self.assertEqual([], structural["delta"]["assessmentsChanged"])

        evidence = build_transition_receipt(
            "evidence-registration",
            from_snapshot_binding=self.g1_binding,
            to_snapshot_binding=self.g2_binding,
            from_program_plan_binding=self.candidate_plan_binding,
            to_program_plan_binding=self.candidate_plan_binding,
            from_document=self.g1,
            to_document=self.g2,
        )
        self.assertEqual([MANIFEST_EVIDENCE_ID], evidence["delta"]["evidenceAdded"])
        self.assertEqual([], evidence["delta"]["assessmentsChanged"])
```

Also create a temporary candidate tree, resolve v1 explicitly in historical mode, resolve g000002 through a rehearsal selector in current mode, and assert both return their own bindings.

- [ ] **Step 2: Run the receipt/resolver RED**

```powershell
python -B -m unittest tests.test_program_acceptance_authority_v2.ProgramAcceptanceAuthorityTransitionTests -v
```

Expected: ERROR with `acceptance-authority-not-implemented` from a reached public builder.

- [ ] **Step 3: Implement exact receipt deltas and invariant projections**

Every receipt has:

```python
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
```

`authorizationBoundary` contains `rehearsalAuthorized: true`, `liveMigrationAuthorized: false`, `assessmentTransitionAuthorized: false`, and `productionActivationAuthorized: false`. `claimBoundary` keeps behavior, value, portability, production, release, and overall-closeout claims false.

The structural receipt requires an empty business delta. The evidence receipt permits exactly one evidence row and one reciprocal criterion link. The rollback receipt permits only selector movement to a verified ancestor and carries no snapshot business delta.

- [ ] **Step 4: Implement selectors and both resolution modes**

The rehearsal selector uses:

```python
{
    "schema": 1,
    "id": "curation-program-acceptance-current-selector-v1",
    "authoritySeriesId": AUTHORITY_SERIES_ID,
    "selectionMode": "rehearsal-candidate",
    "activeSnapshotBinding": snapshot_binding,
    "activeTransitionBinding": transition_binding,
    "programPlanBinding": program_plan_binding,
    "activationAuthorized": False,
    "executionCounters": copy.deepcopy(ZERO_EXECUTION_COUNTERS),
}
```

Historical resolution reopens the explicit artifact binding and never reads a selector. Current resolution rejects absolute paths, `..`, paths outside the supplied root, wrong snapshot/receipt/plan digests, a selector outside `rehearsal-candidate`, `activationAuthorized=True`, or non-zero counters.

- [ ] **Step 5: Add mutation tests and checked receipt/selector fixtures**

Cover exact codes:

```text
acceptance-selector-target-invalid
acceptance-transition-receipt-invalid
acceptance-transition-chain-broken
acceptance-transition-type-mismatch
acceptance-assessment-promotion-forbidden
acceptance-rollback-receipt-invalid
acceptance-rollback-target-not-ancestor
acceptance-activation-not-authorized
acceptance-side-effect-counter-nonzero
```

Generate the five checked receipt/selector fixtures only after the positive and mutation tests pass. Rebuild them from the locked sources and compare exact bytes in the test.

```powershell
python -B -m unittest tests.test_program_acceptance_authority_v2 -v
```

Expected: PASS.

- [ ] **Step 6: Commit Task 3**

```powershell
git add scripts/program_acceptance_authority_v2.py tests/test_program_acceptance_authority_v2.py tests/fixtures/program-acceptance-authority-v2-rehearsal/transitions tests/fixtures/program-acceptance-authority-v2-rehearsal/selectors
git commit -m "feat: validate acceptance transitions and rollback"
```

---

### Task 4: Govern every live legacy-reference occurrence

**Files:**
- Create: `scripts/program_acceptance_migration_inventory.py`
- Create: `tests/test_program_acceptance_migration_inventory.py`
- Create: `registry/program-acceptance-authority-v2-migration-inventory-2026-08-10.json`

**Interfaces:**
- Consumes: Git tracked-file list and the two exact literals `registry/program-acceptance-map.json` and `curation-program-acceptance-map-v1`.
- Produces: `discover_acceptance_reference_occurrences(root) -> list[dict[str, object]]`, `load_migration_inventory(root, path=MIGRATION_INVENTORY_PATH) -> dict[str, object]`, and `validate_migration_inventory(root, inventory) -> None`.

- [ ] **Step 1: Add a callable skeleton and failing exact-set tests**

The discovery function uses `git -C <root> ls-files -z`, reads UTF-8 text files, and emits one row per literal occurrence:

```python
{
    "path": relative.as_posix(),
    "line": line_number,
    "literal": matched_literal,
    "lineSha256": hashlib.sha256(line.encode("utf-8")).hexdigest(),
}
```

Create tests:

```python
class ProgramAcceptanceMigrationInventoryTests(unittest.TestCase):
    def test_inventory_covers_the_fresh_live_occurrence_set_exactly_once(self) -> None:
        inventory = load_migration_inventory(ROOT)
        validate_migration_inventory(ROOT, inventory)
        discovered = discover_acceptance_reference_occurrences(ROOT)
        projected = [
            {key: row[key] for key in ("path", "line", "literal", "lineSha256")}
            for row in inventory["occurrences"]
        ]
        self.assertEqual(discovered, projected)

    def test_missing_occurrence_fails_closed(self) -> None:
        inventory = load_migration_inventory(ROOT)
        inventory["occurrences"].pop()
        with self.assertRaises(AcceptanceAuthorityError) as raised:
            validate_migration_inventory(ROOT, inventory)
        self.assertEqual("migration-inventory-incomplete", raised.exception.code)
```

The initial skeleton raises `acceptance-authority-not-implemented` from `validate_migration_inventory`.

- [ ] **Step 2: Run the inventory RED**

```powershell
python -B -m unittest tests.test_program_acceptance_migration_inventory -v
```

Expected: ERROR with typed `acceptance-authority-not-implemented` after discovery succeeds.

- [ ] **Step 3: Implement exact occurrence discovery and strict inventory validation**

Each governed occurrence adds these fields to the discovery identity:

```json
[
  "purpose", "classification", "currentBinding", "candidateBinding",
  "rehearsalAction", "liveMigrationAction", "rollbackAction",
  "verificationSurface", "separateAuthorizationRequired"
]
```

Classification is one of:

```text
A-immutable-historical
B-current-authority-consumer
C-version-neutral-component
D-migration-governance-and-regression
```

The file is occurrence-based, so different lines in `scripts/verify.py` may have different classifications. Preserve dated registry records, packet builders, fixed fixtures, and historical plans/specifications as class A. Mark current plan/load/navigation references as class B. Mark a reusable validation occurrence as class C only when its function receives documents and bindings explicitly. Mark the new inventory, tests, schemas, rehearsal code, and current design/plan references as class D where they govern the migration rather than consume authority.

Reject missing, duplicate, extra, reordered, stale-line-digest, invalid-class, empty-action, or boolean-alias rows. Reject class A with a candidate repoint action, class B with a simulated activated legacy bypass, class C that owns a registry path, and class D that claims live activation.

- [ ] **Step 4: Materialize and review the complete inventory**

Add a temporary `--emit-candidate` mode to print canonical JSON with every discovered occurrence and empty governance fields. Capture it outside the repository, then populate every governance field and add the reviewed JSON through `apply_patch`. Remove `--emit-candidate` before committing so the production module has no incomplete-inventory output path.

Run:

```powershell
python -B -m unittest tests.test_program_acceptance_migration_inventory -v
python -B -c "from pathlib import Path; from scripts.program_acceptance_migration_inventory import load_migration_inventory, validate_migration_inventory; p=load_migration_inventory(Path('.')); validate_migration_inventory(Path('.'), p); print(len(p['occurrences']))"
```

Expected: PASS and a current occurrence count derived from the final tracked tree. Do not hard-code the earlier 103-, 104-, or 105-file observations as the acceptance count.

- [ ] **Step 5: Add adversarial classification tests**

Mutate one row for each of:

```text
migration-inventory-incomplete
migration-consumer-class-invalid
acceptance-historical-consumer-repointed
acceptance-current-consumer-legacy-bypass
acceptance-neutral-consumer-path-owned
```

Also create a tracked-reference fixture in a temporary Git repository and prove that an unclassified new reference fails closed instead of being ignored.

- [ ] **Step 6: Commit Task 4**

```powershell
git add scripts/program_acceptance_migration_inventory.py tests/test_program_acceptance_migration_inventory.py registry/program-acceptance-authority-v2-migration-inventory-2026-08-10.json schemas/program-acceptance-migration-inventory-v1.schema.json
git commit -m "feat: govern acceptance authority migration references"
```

---

### Task 5: Execute the disposable rehearsal, atomic selector swap, and real failure matrix

**Files:**
- Create: `scripts/program_acceptance_authority_v2_rehearsal.py`
- Create: `scripts/build_program_acceptance_authority_v2_rehearsal.py`
- Create: `scripts/validate_program_acceptance_authority_v2_rehearsal.py`
- Create: `tests/test_program_acceptance_authority_v2_rehearsal.py`
- Create: `registry/program-acceptance-authority-v2-zero-model-rehearsal-2026-08-10.json`
- Create: `docs/strategy/PROGRAM-ACCEPTANCE-AUTHORITY-V2-ZERO-MODEL-REHEARSAL-2026-08-10.md`

**Interfaces:**
- Consumes: Tasks 1-4 builders, validators, fixtures, and migration inventory.
- Produces: `build_rehearsal_bundle(repo_root) -> dict[str, bytes]`, `write_rehearsal_bundle(output_root, bundle) -> None`, `replace_selector_atomically(path, data) -> None`, `run_rehearsal(repo_root, output_root) -> dict[str, object]`, `run_failure_matrix(repo_root) -> list[dict[str, str]]`, and `validate_repository_record(root) -> dict[str, object]`.

- [ ] **Step 1: Add callable skeletons and failing end-to-end tests**

Create tests:

```python
class ProgramAcceptanceAuthorityRehearsalTests(unittest.TestCase):
    def test_rehearsal_builds_selects_rolls_back_and_cleans_disposable_root(self) -> None:
        with tempfile.TemporaryDirectory() as parent:
            output = Path(parent) / "rehearsal"
            result = run_rehearsal(ROOT, output)
            self.assertFalse(output.exists())
        self.assertEqual("verified-zero-model-versioning-and-migration-rehearsal-only", result["status"])
        self.assertEqual(2, result["highestGeneration"])
        self.assertEqual(1, result["rollbackGeneration"])
        self.assertEqual({"verified": 46, "partial": 15, "planned": 0}, result["acceptanceInventory"])

    def test_file_output_rejects_repository_authority_root(self) -> None:
        with self.assertRaises(AcceptanceAuthorityError) as raised:
            run_rehearsal(ROOT, ROOT / "registry/program-acceptance-authority")
        self.assertEqual("acceptance-activation-not-authorized", raised.exception.code)
```

The skeleton reaches `run_rehearsal` and raises `acceptance-authority-not-implemented`.

- [ ] **Step 2: Run the rehearsal RED**

```powershell
python -B -m unittest tests.test_program_acceptance_authority_v2_rehearsal.ProgramAcceptanceAuthorityRehearsalTests -v
```

Expected: ERROR with typed `acceptance-authority-not-implemented`.

- [ ] **Step 3: Implement pure bundle construction and checked-fixture replay**

The bundle contains these relative paths:

```text
curation-program-plan-v2.json
snapshots/v2/g000001.json
snapshots/v2/g000002.json
transitions/g000000-to-g000001.json
transitions/g000001-to-g000002.json
transitions/g000002-to-g000001-rollback.json
selectors/current-g000002.json
selectors/current-g000001-rollback.json
```

Build every byte sequence from live locked sources and compare it to the checked fixture before writing. The in-workspace live selector path is `program-acceptance-authority/current.json`; the two named selector fixtures are expected before/after bytes, not production selector paths.

- [ ] **Step 4: Implement staged writes and atomic selector replacement**

`write_rehearsal_bundle` requires `output_root` not to exist, resolves its parent, rejects the repository and all ancestors/descendants of the production authority path, creates one staging sibling, writes and fsyncs every immutable file, validates the full candidate tree, renames the staging directory to the requested disposable root, and writes the selector last.

Use:

```python
def replace_selector_atomically(path: Path, data: bytes) -> None:
    temporary_name: str | None = None
    try:
        with tempfile.NamedTemporaryFile(
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            temporary_name = handle.name
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_name, path)
        temporary_name = None
    finally:
        if temporary_name is not None:
            Path(temporary_name).unlink(missing_ok=True)
```

Patch `os.replace` to raise `OSError` in a unit test and assert an existing selector sentinel remains exact. Map the failure to `acceptance-atomic-output-preserved` without swallowing the original cause.

- [ ] **Step 5: Implement run, rollback, cleanup, and CLI behavior**

`run_rehearsal`:

1. records the four legacy byte hashes and initial Git tracked status;
2. builds and writes the candidate tree;
3. resolves g000002 through current mode;
4. atomically replaces the live rehearsal selector with the rollback selector;
5. resolves g000001, g000002, and all receipts;
6. removes only the exact disposable root with `shutil.rmtree` after resolved-path checks;
7. confirms the root is absent and the four legacy hashes are unchanged; and
8. returns a canonical result with all zero counters and narrow claims.

The CLI supports:

```text
--root <repository-root>
--output-root <new-disposable-root>
```

When `--output-root` is omitted, create a temporary parent, run and clean the rehearsal, and print the canonical result to stdout. On `AcceptanceAuthorityError` or `OSError`, print an exact envelope such as `{"status":"error","code":"acceptance-activation-not-authorized","message":"Production authority output is not authorized.","path":"registry/program-acceptance-authority"}` to stderr and exit 2. No flag enables activation or preserves a rehearsal root.

- [ ] **Step 6: Implement the real builder/validator/CLI mutation matrix**

`run_failure_matrix` creates isolated copies or in-memory mutations but invokes the actual public builder, validator, selector resolver, atomic writer, or CLI for every case. It covers every typed code in the design, including the five inventory codes from Task 4. Each result is:

```python
{"caseId": case_id, "expectedCode": expected, "observedCode": observed, "status": "rejected"}
```

Add an explicit direct subprocess test:

```powershell
python -B scripts/build_program_acceptance_authority_v2_rehearsal.py --root .
```

Expected: exit 0, one canonical JSON result on stdout, empty stderr, no surviving output root, and all counters zero.

- [ ] **Step 7: Create and validate the independent evidence record**

The record binds:

- all new schemas, modules, tests, fixtures, migration inventory, design, and this plan by SHA-256;
- the four immutable legacy locks;
- g000001/g000002 and transition/selector fixture digests;
- exact mutation results;
- 61 criteria and 46/15/0 in both generations;
- `acceptance.decision-ready-consumer-projection: partial`;
- `acceptanceRegistration.registered: false` with reason `frozen-v1-authority-live-v2-migration-not-authorized`;
- `liveMigrationAuthorized: false`;
- all execution and side-effect counters at zero; and
- explicit false behavior, value, portability, production, release, residual-gap, and overall-closeout claims.

`validate_repository_record` independently rebuilds and validates the candidate bundle and matrix. It must not trust summary counts stored in the record.

- [ ] **Step 8: Write the human-readable result and run Task 5 GREEN**

The Markdown states the exact mechanism proved, immutable v1 boundaries, g0/g1/g2 sequence, rollback behavior, local verification, non-registration, and every unproved claim. It does not call the candidate selector current or the migration complete.

```powershell
python -B -m unittest tests.test_program_acceptance_authority_v2 tests.test_program_acceptance_migration_inventory tests.test_program_acceptance_authority_v2_rehearsal -v
python -B scripts/validate_program_acceptance_authority_v2_rehearsal.py
```

Expected: all focused tests PASS; the direct validator reports every matrix case rejected with its exact expected code.

- [ ] **Step 9: Commit Task 5**

```powershell
git add scripts/program_acceptance_authority_v2_rehearsal.py scripts/build_program_acceptance_authority_v2_rehearsal.py scripts/validate_program_acceptance_authority_v2_rehearsal.py tests/test_program_acceptance_authority_v2_rehearsal.py registry/program-acceptance-authority-v2-zero-model-rehearsal-2026-08-10.json docs/strategy/PROGRAM-ACCEPTANCE-AUTHORITY-V2-ZERO-MODEL-REHEARSAL-2026-08-10.md
git commit -m "feat: rehearse versioned acceptance authority migration"
```

---

### Task 6: Integrate repository verification and current documentation without activating v2

**Files:**
- Modify: `scripts/verify.py`
- Modify: `tests/test_verify_integration.py`
- Modify: `docs/strategy/RESEARCH-AND-POC-PLAN.md`
- Modify: `docs/operations/CURRENT-GOAL-MODE-PROMPT.md`
- Modify: `docs/operations/CONTINUATION.md`

**Interfaces:**
- Consumes: `validate_repository_record(root) -> dict[str, object]` from Task 5.
- Produces: one top-level verifier invocation, required-file coverage, current documentation projection, and final local evidence.

- [ ] **Step 1: Write failing verifier integration tests**

Add the new validator and artifacts to the existing import/required-file assertions. Add:

```python
def test_verify_calls_acceptance_authority_v2_rehearsal_once(self) -> None:
    with mock.patch.object(
        verify_script,
        "validate_program_acceptance_authority_v2_rehearsal",
        return_value={},
    ) as validator:
        verify_script.verify()
    validator.assert_called_once_with(verify_script.ROOT)
```

Extend both `assert_verify_contract_error` and `assert_verify_runtime_error` helper patch stacks so unrelated repository mutation tests replace the expensive rehearsal validator with a side-effect-free return. Do not patch it in the positive integration test above.

- [ ] **Step 2: Run the verifier RED**

```powershell
python -B -m unittest tests.test_verify_integration.StructuralValidationIntegrationTests.test_verify_calls_acceptance_authority_v2_rehearsal_once -v
```

Expected: FAIL because `scripts/verify.py` does not yet expose or call the validator.

- [ ] **Step 3: Add focused verifier integration**

At the import surface, add:

```python
from validate_program_acceptance_authority_v2_rehearsal import (
    validate_repository_record as validate_program_acceptance_authority_v2_rehearsal,
)
```

Add every new schema, script, test, fixture, registry record, and human result to `REQUIRED_FILES`. At the top of `verify()`, beside the existing manifest PoC validator, call:

```python
validate_program_acceptance_authority_v2_rehearsal(ROOT)
```

Do not change the existing load of `registry/program-acceptance-map.json` or `registry/curation-program-plan.json`; the repository remains on v1.

- [ ] **Step 4: Update current planning and continuation projections**

Append a 2026-08-10 subsection to `docs/strategy/RESEARCH-AND-POC-PLAN.md` stating:

- immutable v1 bytes remained exact;
- g000001 structural migration and g000002 evidence registration replayed offline;
- selector selection and ancestor rollback were atomic in a disposable root;
- evidence remains unregistered in live v1;
- assessment remains partial and 46/15/0; and
- live plan/selector migration requires separate user authority.

Update `CURRENT-GOAL-MODE-PROMPT.md` only in the current decision-packet/acceptance boundary. Append the corresponding latest checkpoint to `CONTINUATION.md`. Do not rewrite older checkpoint text.

- [ ] **Step 5: Refresh evidence digests after documentation is final**

Recompute every file binding in `registry/program-acceptance-authority-v2-zero-model-rehearsal-2026-08-10.json` after the documentation and verifier changes settle. The record may not bind itself. Run its focused validator again and confirm no digest mismatch.

- [ ] **Step 6: Run focused integration and direct validator**

```powershell
python -B -m unittest tests.test_program_acceptance_authority_v2 tests.test_program_acceptance_migration_inventory tests.test_program_acceptance_authority_v2_rehearsal tests.test_verify_integration.StructuralValidationIntegrationTests.test_verify_calls_acceptance_authority_v2_rehearsal_once -v
python -B scripts/validate_program_acceptance_authority_v2_rehearsal.py
```

Expected: PASS with exact failure-matrix rejection and no live authority change.

- [ ] **Step 7: Run the complete serial repository acceptance**

```powershell
python -B -m unittest discover -s tests -q
python -B scripts/verify.py
```

Expected: the complete unittest suite reports `OK`; verifier prints `Agent Autonomy Harness validation passed.`. Allow a timeout long enough for the existing full suite; do not interpret a command timeout as PASS.

- [ ] **Step 8: Recheck immutable bytes, Git state, and forbidden effects**

```powershell
git diff --exit-code 39f0b308edbcf9af5c70549a255f7629384cf395 -- registry/program-acceptance-map.json registry/curation-program-plan.json tests/fixtures/harness-decision-packet-gen-research-01.json tests/fixtures/harness-decision-packet-thirteen-scenario-manifest.json
git status --short --branch
git rev-list --left-right --count HEAD...origin/main
```

Also rerun `validate_legacy_locks(ROOT)` and assert no `registry/program-acceptance-authority/current.json` exists. Confirm no model, account, Plugin, CC Switch, consumer, publication, release, or production selector action was executed.

- [ ] **Step 9: Commit Task 6**

```powershell
git add scripts/verify.py tests/test_verify_integration.py docs/strategy/RESEARCH-AND-POC-PLAN.md docs/operations/CURRENT-GOAL-MODE-PROMPT.md docs/operations/CONTINUATION.md registry/program-acceptance-authority-v2-zero-model-rehearsal-2026-08-10.json
git commit -m "docs: govern acceptance authority rehearsal evidence"
```

- [ ] **Step 10: Run post-commit verification and stop before push or live migration**

```powershell
python -B scripts/validate_program_acceptance_authority_v2_rehearsal.py
python -B scripts/verify.py
git status --short --branch
git log -8 --oneline --decorate
```

Expected: validators PASS, worktree clean, local `main` ahead only by the reviewed task commits. Do not push, create a live selector, register evidence into v1, or promote any assessment without a new controller/user decision.

---

## Final Acceptance Checklist

- [ ] All four legacy files match their exact approved SHA-256 values.
- [ ] The live tracked reference occurrence set is represented exactly once in the migration inventory.
- [ ] g000001 is business-semantics-equivalent to v1.
- [ ] g000002 adds only the manifest evidence and reciprocal criterion link.
- [ ] Both v2 generations contain 61 criteria and 46/15/0.
- [ ] The target criterion remains `partial`.
- [ ] Historical v1 and candidate-current v2 resolution both pass.
- [ ] Rollback targets verified ancestor g000001 and preserves immutable g000002.
- [ ] Selector replacement failure preserves an existing sentinel exactly.
- [ ] The disposable rehearsal root is absent after success and failure.
- [ ] Every mutation reaches the real public path and rejects with its expected typed code.
- [ ] Direct CLI and validator output are deterministic and machine-readable.
- [ ] Full serial unittest and local repository verifier pass.
- [ ] No live selector, v2 plan, snapshot, receipt, or evidence registration is created under the production authority path.
- [ ] No model, install, enablement, account, Plugin, manager, consumer, publication, release, production, assessment-promotion, or closeout action occurs.
- [ ] Final wording remains zero-model mechanism evidence only.
