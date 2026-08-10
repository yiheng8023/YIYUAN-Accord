# Evaluation & Software-Engineering Standards Coverage Reconciliation v1 Design

## Status and authority

This design is approved for repository-local specification, deterministic
implementation, tests, documentation, and local verification on `main`.
It does not authorize a live Acceptance Authority v2 selector or plan
migration, an acceptance assessment transition, model or candidate execution,
CC Switch or consumer mutation, cleanup, commit, push, publication, or release.

## Problem

The current program has fifteen `partial` acceptance criteria across six
closeout evidence clusters. The current candidate-capability reconciliation
maps thirteen Harness scenarios, fourteen software-engineering lifecycle
slices, nine broad mother-framework axes, six overlap groups, five conflict
groups, and fifteen unassessed route cells. The current engineering evaluation
contract separately defines twelve dimensions.

Those surfaces are individually governed but do not yet provide one sparse,
deterministic answer to these questions:

- which partial criteria are actually covered by existing bounded evidence;
- where evidence or capability paths overlap or conflict;
- which cells remain unassessed;
- which gaps require a naturally occurring real task;
- which judgments remain accountable-human decisions;
- which transitions require separate authority; and
- which provisional coordinates should be retained, revised, or subtracted.

Without that reconciliation, the program risks repeating evidence work,
treating unassessed cells as residual gaps, forcing cross-cutting governance
criteria into inappropriate software-lifecycle coordinates, or letting a
green mechanism check look like acceptance progress.

## Approaches considered

### 1. Sparse criterion-led reconciliation — selected

Create one tracked evidence record with exactly one primary row per current
partial criterion. Each row names its evidence cluster, applicable evaluation
dimensions, lifecycle slices, Harness scenarios, route-class posture, and one
or more explicit disposition states. Empty coordinate sets are permitted only
with a typed `not-applicable` or `cross-cut` reason.

This approach is reviewable, avoids a false Cartesian completeness claim, and
keeps current authorities immutable.

### 2. Full Cartesian coverage cube — rejected

Materializing every criterion × dimension × lifecycle slice × scenario cell
would create 32,760 cells before route classes. Most cells would be meaningless
or inferred. The size would hide judgment rather than improve evidence.

### 3. Narrative-only strategy reconciliation — rejected

A prose report would be easier to write but could not fail closed on missing
criteria, coordinate drift, route omission, evidence promotion, or authority
expansion.

## Architecture

The implementation has one deep validation module and one canonical record.

1. `registry/evaluation-software-engineering-standards-coverage-reconciliation-v1-2026-08-11.json`
   stores the reviewed sparse mapping and its claim and authority ceilings.
2. `scripts/validate_evaluation_software_engineering_standards_coverage_reconciliation_v1.py`
   exposes a small interface: load the canonical record and validate it against
   the frozen source files. The implementation performs all exact-set,
   digest, relationship, state, route, and claim checks.
3. `tests/test_evaluation_software_engineering_standards_coverage_reconciliation_v1.py`
   exercises the real validator with one positive record and focused mutations.
4. `scripts/verify.py` invokes the validator and requires every governed file.
5. Strategy and continuation documents project the bounded result without
   modifying the v1 acceptance authority.

No new schema language, database, runtime adapter, selector, or general-purpose
coverage engine is introduced.

## Frozen inputs

The record binds exact bytes for:

- `registry/program-acceptance-map.json` — 61 criteria, 46 verified, 15 partial;
- `registry/program-final-closeout-readiness-reconciliation-2026-07-28.json`
  — the six current closeout evidence clusters;
- `registry/human-ai-collaboration-current-candidate-capability-coverage-reconciliation-2026-08-01.json`
  — thirteen scenarios, route cells, overlap, conflict, and unassessed evidence;
- `registry/multidimensional-software-engineering-evaluation-contract-2026-07-31.json`
  — twelve evaluation dimensions;
- `registry/human-ai-collaboration-coverage-rebaseline-2026-07-24.json`
  — fourteen software-engineering lifecycle slices; and
- `registry/human-ai-collaboration-scenario-evidence-matrix-batch-01-2026-07-24.json`
  — the thirteen scenario identities and their bounded evidence semantics.

The validator derives the authoritative sets from those inputs. The tracked
record cannot redefine them.

## Record model

The top-level record contains:

- identity, date, status, purpose, and exact source bindings;
- the exact `15 / 6 / 14 / 12 / 13` input inventory;
- six route classes: native/runtime, official, reviewed external, composition,
  accountable human control, and residual/self-authored;
- exactly fifteen criterion rows;
- aggregate coordinate coverage and subtraction decisions;
- execution counters, claim boundary, and authority boundary; and
- the next evidence queue, ordered by expected information gain without
  authorizing execution.

Each criterion row contains:

- `criterionId` and `clusterId`;
- applicable `dimensionIds`, `lifecycleSliceIds`, and `scenarioIds`;
- `coordinatePosture` explaining any empty or cross-cut mapping;
- `dispositions`, selected from:
  `covered`, `overlap`, `conflict`, `unassessed`, `needs-real-task`,
  `needs-human-judgment`, `needs-separate-authorization`, and
  `not-applicable`;
- a six-entry `routeComparison` using the canonical route-class IDs;
- bounded `evidenceIds`; and
- `nextEvidenceClass` and `claimCeiling`.

One row may have multiple dispositions because, for example, mechanism
coverage can coexist with missing real-task value evidence and a separate
authorization gate. `unassessed` is never equivalent to a residual gap.

## Validation and failure behavior

The validator fails closed when:

- a source digest or identity drifts;
- the partial criterion set, cluster membership, dimensions, slices, scenarios,
  or route classes are missing, duplicated, or invented;
- a criterion is absent or assigned to the wrong cluster;
- a referenced coordinate or evidence ID is unknown;
- an empty coordinate set lacks a typed explanation;
- a row omits human control or silently makes residual/self-authored eligible;
- a disposition or route state is outside the declared vocabulary;
- unassessed evidence is promoted to a residual gap;
- a mechanism, inventory, exposure, or zero-model result claims behavior,
  value, portability, production, release, or closeout;
- any execution counter is non-zero; or
- any live migration, assessment transition, model/candidate execution,
  consumer mutation, cleanup, commit, push, or release authority becomes true.

Errors are stable `RuntimeError` messages at the standalone validator seam.
The top-level verifier treats any error as repository validation failure.

## Testing

TDD begins with real-validator tests that fail because the module and record do
not exist. The minimum mutation suite covers:

- missing and duplicate partial criteria;
- cluster-count and cluster-assignment drift;
- dimension, lifecycle, scenario, and route omission;
- unknown coordinate and evidence identities;
- an unexplained empty coordinate set;
- unassessed-to-residual promotion;
- behavior/value/production claim promotion;
- non-zero side-effect counters;
- live v2 or acceptance-transition authorization; and
- source-binding drift.

Focused tests, the standalone validator, `scripts/verify.py`, and the full
serial unit-test suite are the local deterministic acceptance surfaces.

## Acceptance criteria

1. The record maps every current partial criterion exactly once and preserves
   all six closeout clusters.
2. The aggregate coordinate inventories are exactly fourteen lifecycle slices,
   twelve evaluation dimensions, and thirteen Harness scenarios.
3. Sparse mapping and typed non-applicability prevent false Cartesian coverage.
4. All six route classes remain visible; human judgment and residual-gap proof
   are not collapsed into automated capability routes.
5. Coverage, overlap, conflict, unassessed, real-task, human-judgment, and
   separate-authorization states remain distinct.
6. Subtraction decisions remove or defer redundant evidence work without
   retiring a capability or changing an authority.
7. The v1 acceptance map, curation program plan, and two v1-bound packet
   fixtures remain byte-identical.
8. No acceptance assessment changes and no live v2 selector exists.
9. All execution counters and prohibited authority flags remain zero or false.
10. Focused tests, the standalone validator, repository verifier, and full
    serial unit-test suite pass locally.

## Non-goals

- acceptance promotion or program closeout;
- a universal evaluation score;
- a new hard standard or evaluation Skill;
- candidate discovery, installation, enablement, invocation, or value trials;
- real-task invention;
- live authority migration;
- consumer, CC Switch, account, remote, release, or cleanup mutation; and
- proving behavior, value, portability, production, or cross-host validity.
