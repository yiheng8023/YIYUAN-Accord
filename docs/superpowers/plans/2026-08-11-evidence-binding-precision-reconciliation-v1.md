# Evidence Binding Precision Reconciliation v1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace nine generic-only evidence anchors with criterion-owned specific evidence and make coordinate, boundary, and next-evidence roles deterministic for all fifteen reconciliation rows.

**Architecture:** Extend each existing criterion row in the canonical reconciliation record with `evidenceRoleBindings`, while retaining `evidenceIds` as the stable first-seen union compatibility view. Extend the existing standalone validator rather than creating a second authority, then reuse its existing repository-verifier integration.

**Tech Stack:** Python 3 standard library, JSON repository records, `unittest`, PowerShell, Git.

## Global Constraints

- Work directly in `C:\Projects\agent-autonomy-harness` on the existing `main` checkout.
- Do not create a branch or worktree.
- Do not change the fifteen criterion coordinates, clusters, dispositions, route comparisons, claim ceilings, or next-evidence text.
- Keep 46 verified / 15 partial / 0 planned unchanged.
- Keep the four frozen v1 authority and packet-fixture inputs byte-identical.
- Do not create a live v2 selector, migrate live authority, or change an acceptance assessment.
- Do not dispatch a model or candidate; do not mutate CC Switch, a consumer, an account, cleanup state, publication, or release state.
- Do not stage, commit, or push without later explicit user authority.
- Use `apply_patch` for source and document edits.

---

### Task 1: Add the role-aware canonical evidence projection

**Files:**
- Modify: `tests/test_evaluation_software_engineering_standards_coverage_reconciliation_v1.py`
- Modify: `registry/evaluation-software-engineering-standards-coverage-reconciliation-v1-2026-08-11.json`

**Interfaces:**
- Consumes: the exact fifteen role assignments in `docs/superpowers/specs/2026-08-11-evidence-binding-precision-reconciliation-v1-design.md`.
- Produces: each criterion row has `evidenceRoleBindings` with `coordinateBasisIds`, `boundaryBasisIds`, and `nextEvidenceBasisIds`; `evidenceIds` is their stable first-seen union.

- [ ] **Step 1: Add the failing positive record test**

Add imports for `hashlib` and define a test that validates all fifteen rows have the exact three role keys, no coordinate role is generic-only, and the non-evidence projection hash remains frozen:

```python
    def test_repository_record_has_precise_role_bindings_without_coordinate_drift(
        self,
    ) -> None:
        generic_ids = {"evidence.program-plan", "evidence.readme"}
        projection = []
        for row in self.document["criterionReconciliations"]:
            roles = row["evidenceRoleBindings"]
            self.assertEqual(
                {
                    "coordinateBasisIds",
                    "boundaryBasisIds",
                    "nextEvidenceBasisIds",
                },
                set(roles),
            )
            self.assertTrue(set(roles["coordinateBasisIds"]) - generic_ids)
            projection.append(
                {
                    key: value
                    for key, value in row.items()
                    if key not in {"evidenceIds", "evidenceRoleBindings"}
                }
            )

        encoded = json.dumps(
            projection,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        self.assertEqual(
            "5f9ccfaf9572ae99b2f9f63ffb4394be8c9b148309d5b772f40f18eba905f9b6",
            hashlib.sha256(encoded).hexdigest(),
        )
```

- [ ] **Step 2: Run the focused test and observe RED**

Run:

```powershell
python -B -m unittest tests.test_evaluation_software_engineering_standards_coverage_reconciliation_v1.EvaluationSoftwareEngineeringStandardsCoverageReconciliationV1Tests.test_repository_record_has_precise_role_bindings_without_coordinate_drift -q
```

Expected: ERROR or FAIL because `evidenceRoleBindings` is absent from the current record.

- [ ] **Step 3: Apply the fifteen reviewed role assignments**

For every criterion row, add the exact role lists from the design specification. Replace `evidenceIds` with this deterministic projection:

```python
def stable_role_union(roles: dict[str, list[str]]) -> list[str]:
    result: list[str] = []
    for role in (
        "coordinateBasisIds",
        "boundaryBasisIds",
        "nextEvidenceBasisIds",
    ):
        for evidence_id in roles[role]:
            if evidence_id not in result:
                result.append(evidence_id)
    return result
```

Apply the function manually to the JSON values; do not add this helper to production code in this task. Update the record `status` to
`verified-sparse-zero-model-coverage-reconciliation-role-bound-no-acceptance-promotion`
and extend its purpose to mention role-aware evidence precision without changing its claim or authority boundaries.

- [ ] **Step 4: Run the positive test and existing focused suite**

Run:

```powershell
python -B -m unittest tests.test_evaluation_software_engineering_standards_coverage_reconciliation_v1 -q
```

Expected: the new positive test passes; the existing validator may fail only if its exact status check has not yet been updated. If it fails on the old status, proceed directly to Task 2 without weakening the test or reverting the record.

- [ ] **Step 5: Record the checkpoint without committing**

Run `git status --short` and confirm that only the design, plan, focused test, and canonical record are dirty at this checkpoint.

### Task 2: Enforce role ownership, order, generic precision, and flat projection

**Files:**
- Modify: `tests/test_evaluation_software_engineering_standards_coverage_reconciliation_v1.py`
- Modify: `scripts/validate_evaluation_software_engineering_standards_coverage_reconciliation_v1.py`

**Interfaces:**
- Consumes: `validate_reconciliation(document: dict[str, object], *, root: Path = ROOT) -> None`, the acceptance criterion `evidenceIds` order, and the new record fields from Task 1.
- Produces: `_stable_role_union(roles: dict[str, list[str]]) -> list[str]` and fail-closed role validation inside `validate_reconciliation`.

- [ ] **Step 1: Add real mutation tests before validator changes**

Add these independent tests using `copy.deepcopy(self.document)` and the real `validate_reconciliation` function:

```python
    def test_missing_evidence_role_bindings_fails_closed(self) -> None:
        document = copy.deepcopy(self.document)
        document["criterionReconciliations"][0].pop("evidenceRoleBindings")
        self.assert_rejected(document, "evidence role binding drifted")

    def test_unknown_evidence_role_fails_closed(self) -> None:
        document = copy.deepcopy(self.document)
        document["criterionReconciliations"][0]["evidenceRoleBindings"][
            "inventedBasisIds"
        ] = ["evidence.human-ai-collaboration-coverage-rebaseline"]
        self.assert_rejected(document, "evidence role binding drifted")

    def test_empty_evidence_role_fails_closed(self) -> None:
        document = copy.deepcopy(self.document)
        document["criterionReconciliations"][0]["evidenceRoleBindings"][
            "boundaryBasisIds"
        ] = []
        self.assert_rejected(document, "evidence role binding drifted")

    def test_duplicate_role_evidence_fails_closed(self) -> None:
        document = copy.deepcopy(self.document)
        role = document["criterionReconciliations"][0]["evidenceRoleBindings"][
            "coordinateBasisIds"
        ]
        role.append(role[0])
        self.assert_rejected(document, "evidence role binding drifted")

    def test_cross_criterion_role_evidence_fails_closed(self) -> None:
        document = copy.deepcopy(self.document)
        document["criterionReconciliations"][0]["evidenceRoleBindings"][
            "coordinateBasisIds"
        ] = ["evidence.round03-native-runtime-baseline"]
        self.assert_rejected(document, "unknown evidence identity")

    def test_role_evidence_authority_order_fails_closed(self) -> None:
        document = copy.deepcopy(self.document)
        role = document["criterionReconciliations"][0]["evidenceRoleBindings"][
            "coordinateBasisIds"
        ]
        role.reverse()
        self.assert_rejected(document, "evidence role order drifted")

    def test_generic_only_coordinate_basis_fails_closed(self) -> None:
        document = copy.deepcopy(self.document)
        row = next(
            row
            for row in document["criterionReconciliations"]
            if row["criterionId"]
            == "acceptance.decision-ready-consumer-projection"
        )
        row["evidenceRoleBindings"]["coordinateBasisIds"] = [
            "evidence.program-plan"
        ]
        self.assert_rejected(document, "coordinate evidence is generic-only")

    def test_flat_evidence_projection_drift_fails_closed(self) -> None:
        document = copy.deepcopy(self.document)
        document["criterionReconciliations"][0]["evidenceIds"].pop()
        self.assert_rejected(document, "evidence projection drifted")
```

- [ ] **Step 2: Run the eight mutation tests and observe RED**

Run the whole focused module:

```powershell
python -B -m unittest tests.test_evaluation_software_engineering_standards_coverage_reconciliation_v1 -q
```

Expected: the new mutation tests fail because the existing validator does not inspect role bindings.

- [ ] **Step 3: Add minimal validator constants and helper**

Add these constants after the existing source-path declarations so the tracked legacy-reference line remains stable:

```python
EVIDENCE_ROLE_KEYS = (
    "coordinateBasisIds",
    "boundaryBasisIds",
    "nextEvidenceBasisIds",
)
GENERIC_EVIDENCE_IDS = {"evidence.program-plan", "evidence.readme"}


def _stable_role_union(roles: dict[str, list[str]]) -> list[str]:
    result: list[str] = []
    for role in EVIDENCE_ROLE_KEYS:
        for evidence_id in roles[role]:
            if evidence_id not in result:
                result.append(evidence_id)
    return result
```

- [ ] **Step 4: Validate each role against criterion-owned authority evidence**

Inside the criterion-row loop, replace the current flat-evidence-only block with logic equivalent to:

```python
        criterion_evidence = criteria[criterion_id].get("evidenceIds", [])
        roles = row.get("evidenceRoleBindings")
        if not isinstance(roles, dict) or tuple(roles) != EVIDENCE_ROLE_KEYS:
            raise RuntimeError("evidence role binding drifted")
        typed_roles: dict[str, list[str]] = {}
        for role_name in EVIDENCE_ROLE_KEYS:
            role_ids = _require_exact_string_list(
                roles.get(role_name), field=role_name
            )
            if not role_ids:
                raise RuntimeError("evidence role binding drifted")
            if not set(role_ids).issubset(evidence_ids) or not set(
                role_ids
            ).issubset(set(criterion_evidence)):
                raise RuntimeError("unknown evidence identity")
            positions = [criterion_evidence.index(value) for value in role_ids]
            if positions != sorted(positions):
                raise RuntimeError("evidence role order drifted")
            typed_roles[role_name] = role_ids
        if not set(typed_roles["coordinateBasisIds"]) - GENERIC_EVIDENCE_IDS:
            raise RuntimeError("coordinate evidence is generic-only")
        row_evidence = _require_exact_string_list(
            row.get("evidenceIds"), field="evidenceIds"
        )
        if row_evidence != _stable_role_union(typed_roles):
            raise RuntimeError("evidence projection drifted")
```

Also update the exact accepted status string to the Task 1 role-bound status.

- [ ] **Step 5: Run focused tests to GREEN**

Run:

```powershell
python -B -m unittest tests.test_evaluation_software_engineering_standards_coverage_reconciliation_v1 -q
python -B scripts/validate_evaluation_software_engineering_standards_coverage_reconciliation_v1.py
```

Expected: all focused tests pass and the CLI prints its verified message.

- [ ] **Step 6: Refactor only after GREEN**

Remove duplicated evidence-membership logic left by the old flat validation block. Re-run the focused module and standalone validator after the cleanup.

### Task 3: Integrate required artifacts and current projections

**Files:**
- Modify: `tests/test_verify_integration.py`
- Modify: `scripts/verify.py`
- Modify: `docs/strategy/EVALUATION-SOFTWARE-ENGINEERING-STANDARDS-COVERAGE-RECONCILIATION-V1-2026-08-11.md`
- Modify: `docs/strategy/RESEARCH-AND-POC-PLAN.md`
- Modify: `docs/operations/CURRENT-GOAL-MODE-PROMPT.md`
- Modify: `docs/operations/CONTINUATION.md`

**Interfaces:**
- Consumes: the existing repository-verifier alias `validate_evaluation_software_engineering_standards_coverage_reconciliation_v1` and `REQUIRED_FILES` tuple extension at the end of `scripts/verify.py`.
- Produces: required-file protection for the new design and plan plus bounded current-strategy and continuation checkpoints.

- [ ] **Step 1: Add the failing required-file integration assertions**

Extend `test_reconciliation_files_are_required_verifier_inputs` with:

```python
"docs/superpowers/specs/2026-08-11-evidence-binding-precision-reconciliation-v1-design.md",
"docs/superpowers/plans/2026-08-11-evidence-binding-precision-reconciliation-v1.md",
```

Run:

```powershell
python -B -m unittest tests.test_verify_integration.EvaluationStandardsReconciliationIntegrationTests.test_reconciliation_files_are_required_verifier_inputs -q
```

Expected: FAIL because neither path is yet in `verify_script.REQUIRED_FILES`.

- [ ] **Step 2: Add both paths to the existing bottom-of-file required tuple**

Append both exact paths to the existing reconciliation `REQUIRED_FILES += (...)` block at the bottom of `scripts/verify.py`. Keep this registration after legacy-reference discovery lines so the existing migration-inventory occurrence identities do not shift.

- [ ] **Step 3: Run integration tests to GREEN**

Run:

```powershell
python -B -m unittest tests.test_verify_integration.EvaluationStandardsReconciliationIntegrationTests -q
```

Expected: both integration tests pass.

- [ ] **Step 4: Append bounded narrative checkpoints**

Append a dated 2026-08-11 checkpoint to the strategy, research plan,
goal-mode prompt, and continuation files. Each checkpoint must state:

- fifteen exact role-aware rows and zero generic-only coordinate basis;
- the flat list remains a compatibility projection;
- coordinates and 46/15/0 remain unchanged;
- no behavior, value, portability, production, release, closeout, residual gap,
  live migration, assessment transition, model/candidate execution, manager,
  consumer, cleanup, publication, or release claim follows.

Do not insert text before existing tracked legacy-reference occurrences; append
at file ends to preserve the migration inventory.

- [ ] **Step 5: Run the repository verifier**

Run:

```powershell
python -B scripts/verify.py
```

Expected: `Agent Autonomy Harness validation passed.`

### Task 4: Final verification and closure audit

**Files:**
- Verify only; do not edit after the final full-suite run.

**Interfaces:**
- Consumes: all prior tasks.
- Produces: current-state evidence for goal closure without Git publication.

- [ ] **Step 1: Run focused and repository checks**

```powershell
python -B -m unittest tests.test_evaluation_software_engineering_standards_coverage_reconciliation_v1 tests.test_verify_integration.EvaluationStandardsReconciliationIntegrationTests -q
python -B scripts/validate_evaluation_software_engineering_standards_coverage_reconciliation_v1.py
python -B scripts/verify.py
git diff --check
```

Expected: all commands exit zero.

- [ ] **Step 2: Run the full serial unit-test suite**

```powershell
python -B -m unittest discover -s tests -p 'test_*.py' -q
```

Expected: exit zero and `OK`; report the exact observed test count and elapsed time.

- [ ] **Step 3: Verify frozen and authority boundaries**

Use the existing acceptance-authority v2 rehearsal validator plus a Git diff
against `52ebb7cf9955e45170e1418fa927866abf24c473` for the four frozen v1 inputs.
Require no live selector, no assessment change, and no protected-file diff.

- [ ] **Step 4: Inspect final Git posture**

```powershell
git status --short --branch
git diff --stat
git diff --check
```

Expected: only this objective's record, validator, tests, design, plan, and
four narrative projections are dirty; `main` remains at the prior pushed SHA
until separate commit authority is granted.

- [ ] **Step 5: Run closure contract**

Audit every acceptance item from the design against current files and command
outputs. Mark the active goal complete only when every item is proved. Report
the dirty worktree and the still-closed commit/push and external-effect gates.
