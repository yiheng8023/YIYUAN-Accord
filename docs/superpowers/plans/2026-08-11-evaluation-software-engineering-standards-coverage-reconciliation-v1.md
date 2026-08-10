# Evaluation & Software-Engineering Standards Coverage Reconciliation v1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build one deterministic sparse reconciliation of the current fifteen partial acceptance criteria across six evidence clusters, fourteen software lifecycle slices, twelve evaluation dimensions, thirteen Harness scenarios, and six route classes without changing acceptance or runtime authority.

**Architecture:** A canonical registry record carries reviewed sparse mappings. One deep Python validation module exposes `validate_reconciliation(document, root=ROOT)` and a standalone CLI; it derives every authoritative identity set from frozen repository inputs and fails closed on drift, omission, promotion, or authority expansion. The top-level verifier calls that same interface, while strategy and continuation documents project only the bounded result.

**Tech Stack:** Python 3 standard library, JSON registry records, `unittest`, repository `scripts/verify.py`, Markdown strategy and continuation documents.

## Global Constraints

- Work directly on the existing `main` checkout; do not create a branch or worktree.
- Do not commit or push.
- Preserve `registry/program-acceptance-map.json`, `registry/curation-program-plan.json`, `tests/fixtures/harness-decision-packet-gen-research-01.json`, and `tests/fixtures/harness-decision-packet-thirteen-scenario-manifest.json` byte for byte.
- Do not create a live v2 selector, migrate the program plan, or change an acceptance assessment.
- Do not install, enable, connect, dispatch, execute, mutate CC Switch or consumers, clean external state, publish, or release.
- Keep all execution counters zero and all prohibited authority and claim flags false.
- Use sparse mappings; do not materialize a Cartesian coverage cube.
- Keep accountable human control as a distinct sixth route class.

---

### Task 1: Canonical reconciliation record and deep validator

**Files:**
- Create: `tests/test_evaluation_software_engineering_standards_coverage_reconciliation_v1.py`
- Create: `scripts/validate_evaluation_software_engineering_standards_coverage_reconciliation_v1.py`
- Create: `registry/evaluation-software-engineering-standards-coverage-reconciliation-v1-2026-08-11.json`

**Interfaces:**
- Consumes: exact JSON inputs named in the design specification.
- Produces: `validate_reconciliation(document: dict[str, object], *, root: Path = ROOT) -> None` and a CLI that prints `Evaluation and software-engineering standards coverage reconciliation v1 verified.` on success.

- [ ] **Step 1: Write the failing positive test**

```python
class EvaluationSoftwareEngineeringStandardsCoverageReconciliationV1Tests(unittest.TestCase):
    def test_repository_record_reconciles_exact_current_coordinate_sets(self) -> None:
        document = load(RECORD_PATH)
        validate_reconciliation(document, root=ROOT)
        self.assertEqual(15, document["inputInventory"]["partialCriterionCount"])
        self.assertEqual(6, document["inputInventory"]["clusterCount"])
        self.assertEqual(14, document["inputInventory"]["lifecycleSliceCount"])
        self.assertEqual(12, document["inputInventory"]["evaluationDimensionCount"])
        self.assertEqual(13, document["inputInventory"]["scenarioCount"])
        self.assertEqual(15, len(document["criterionReconciliations"]))
```

- [ ] **Step 2: Run RED and confirm the missing module is the failure**

Run:

```powershell
python -B -m unittest tests.test_evaluation_software_engineering_standards_coverage_reconciliation_v1 -q
```

Expected: import failure for the not-yet-created validator module.

- [ ] **Step 3: Add mutation tests before implementation**

Use literal mutations against the loaded real record. Each test must name the production break it catches and call the real validator:

```python
def test_missing_partial_criterion_fails_closed(self) -> None:
    document = load(RECORD_PATH)
    document["criterionReconciliations"].pop()
    with self.assertRaisesRegex(RuntimeError, "partial criterion coverage drifted"):
        validate_reconciliation(document, root=ROOT)

def test_unassessed_route_cannot_become_residual_gap(self) -> None:
    document = load(RECORD_PATH)
    row = document["criterionReconciliations"][0]
    row["routeComparison"]["R"] = "eligible-residual-gap"
    with self.assertRaisesRegex(RuntimeError, "residual route overclaimed"):
        validate_reconciliation(document, root=ROOT)

def test_live_migration_authority_fails_closed(self) -> None:
    document = load(RECORD_PATH)
    document["authorityBoundary"]["liveV2MigrationAuthorized"] = True
    with self.assertRaisesRegex(RuntimeError, "authority expanded"):
        validate_reconciliation(document, root=ROOT)
```

Add separate tests for duplicate criteria, wrong cluster, missing dimension,
missing lifecycle slice, missing scenario, missing route class, unknown
coordinate, unknown evidence ID, unexplained empty coordinate set, unknown
disposition, behavior/value/production claim promotion, non-zero execution
counter, and source digest drift.

- [ ] **Step 4: Run RED and confirm failures arise from the missing interface**

Run the same focused test command. Expected: module import failure; the tests
must not pass through fixtures or source-text checks.

- [ ] **Step 5: Implement the validator interface**

Implement these exact functions in the validation module: `_load(path: Path)
-> dict[str, object]`, `_sha256(path: Path) -> str`,
`_records_by_id(value: object, *, field: str) -> dict[str, dict[str,
object]]`, `_require_exact_string_list(value: object, *, field: str) ->
list[str]`, `validate_reconciliation(document: dict[str, object], *, root:
Path = ROOT) -> None`, and `main() -> int`. `_load` must read UTF-8 JSON and
require an object root; `_sha256` must hash raw file bytes; the two collection
helpers must reject JSON type aliases, duplicates, empty strings, and malformed
records; `main` must load the canonical record, call the public validator, print
the exact success line, and return zero.

`validate_reconciliation` must derive:

- partial criteria and their assessments from the v1 acceptance map;
- cluster membership from the closeout record;
- dimensions from the evaluation contract;
- lifecycle slice IDs from the coverage rebaseline;
- scenario IDs and evidence IDs from the scenario matrix and acceptance map;
- route-cell, overlap, conflict, and unassessed facts from the current candidate coverage reconciliation; and
- the six route IDs from the canonical record, checked against exact literals `N/O/E/C/H/R`.

Validate exact source digests before trusting source contents. Reject boolean or
float aliases where integer counts are required. Require every criterion row to
have all six route entries and a non-empty claim ceiling. Permit empty coordinate
lists only when `coordinatePosture` is `not-applicable` or `cross-cut` and the
row includes the `not-applicable` disposition.

- [ ] **Step 6: Create the canonical sparse record**

Create one row for each of the fifteen exact partial criterion IDs. Preserve
the closeout cluster assignment. Bind only known dimension, slice, scenario,
and evidence IDs. Use these route-state literals:

```text
represented-bounded-evidence
unassessed
needs-real-task
needs-human-judgment
needs-separate-authorization
not-applicable
not-eligible-no-residual-gap
```

Every row's `R` route must be `not-eligible-no-residual-gap`. Include aggregate
coordinate coverage that proves all 12/14/13 identities are represented by at
least one row or explicitly retained as a governed coordinate. Keep route
comparison and evidence status independent.

- [ ] **Step 7: Run GREEN**

Run the focused test module and standalone validator. Expected: all focused
tests pass and the CLI prints its exact success line.

- [ ] **Step 8: Review the Task 1 diff without committing**

Run:

```powershell
git diff --check
git status --short
```

Confirm only the three Task 1 files plus the already-approved spec and plan are
present. Do not stage or commit.

### Task 2: Top-level verifier integration

**Files:**
- Modify: `scripts/verify.py`
- Modify: `tests/test_verify_integration.py`

**Interfaces:**
- Consumes: `validate_reconciliation` from Task 1.
- Produces: one mandatory top-level verifier call and governed-file inventory entries.

- [ ] **Step 1: Write the failing verifier-integration test**

Add a test that patches the imported validator, calls `verify_script.verify()`,
and asserts exactly one call with `verify_script.ROOT`. Extend the required-file
test with the record, validator, focused test, design spec, implementation plan,
and strategy documentation paths.

- [ ] **Step 2: Run RED**

Run only the new integration test. Expected: failure because `scripts/verify.py`
does not import or call the validator and does not list the governed files.

- [ ] **Step 3: Add the minimal verifier integration**

Import the Task 1 interface under the explicit alias
`validate_evaluation_software_engineering_standards_coverage_reconciliation_v1`,
add one call in the verifier's deterministic validation phase, and add all new
governed paths to the existing required-path collection. Do not duplicate the
validator's internal assertions in `verify.py`.

- [ ] **Step 4: Run GREEN and adjacent integration tests**

Run the new integration test, the complete `tests.test_verify_integration`
module, the Task 1 focused tests, and the standalone validator.

- [ ] **Step 5: Review the Task 2 diff without committing**

Run `git diff --check` and inspect the exact `scripts/verify.py` and
`tests/test_verify_integration.py` hunks. Do not stage or commit.

### Task 3: Strategy, execution projection, and continuation documentation

**Files:**
- Create: `docs/strategy/EVALUATION-SOFTWARE-ENGINEERING-STANDARDS-COVERAGE-RECONCILIATION-V1-2026-08-11.md`
- Modify: `docs/strategy/RESEARCH-AND-POC-PLAN.md`
- Modify: `docs/operations/CURRENT-GOAL-MODE-PROMPT.md`
- Modify: `docs/operations/CONTINUATION.md`

**Interfaces:**
- Consumes: the validated Task 1 record.
- Produces: human-readable claim limits and current-phase navigation; no new authority.

- [ ] **Step 1: Write the strategy record**

Document the exact 15/6/14/12/13 inventories, the sparse non-Cartesian method,
all eight disposition types, all six route classes, the subtraction decisions,
the ordered evidence queue, and the claim/authority limits. Link the canonical
registry record and validator.

- [ ] **Step 2: Update current projections**

Append one dated checkpoint to the research plan and continuation. Add a
compact current reconciliation boundary to the goal-mode prompt. State that
this is deterministic planning/evidence reconciliation only and that no
assessment changed.

- [ ] **Step 3: Run documentation and record validation**

Run the standalone validator, focused tests, and `scripts/verify.py`. The
record must bind any governed document digests only if the architecture avoids
a circular documentation dependency; otherwise the verifier's required-file
inventory owns document existence.

- [ ] **Step 4: Verify frozen v1 bytes**

Run:

```powershell
git diff --exit-code 7e6f613d996a871578e245998ad008729171f4d4 -- registry/program-acceptance-map.json registry/curation-program-plan.json tests/fixtures/harness-decision-packet-gen-research-01.json tests/fixtures/harness-decision-packet-thirteen-scenario-manifest.json
```

Expected: exit 0 and no output.

- [ ] **Step 5: Run final deterministic verification**

Run in order:

```powershell
python -B -m unittest tests.test_evaluation_software_engineering_standards_coverage_reconciliation_v1 -q
python -B scripts/validate_evaluation_software_engineering_standards_coverage_reconciliation_v1.py
python -B scripts/verify.py
python -B -m unittest discover -s tests -p 'test_*.py' -q
git diff --check
git status --short --branch
```

Classify local test and verifier success as local deterministic evidence only.

- [ ] **Step 6: Run closure review without committing**

Check every design acceptance criterion, report changed files, verification,
dirty state, skipped external checks, and residual authority gates. Do not
stage, commit, push, migrate, promote acceptance, or clean the six historical
overlay roots.
