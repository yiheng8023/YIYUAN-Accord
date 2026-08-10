# Program Acceptance Authority v2 Versioning And Zero-Model Migration Rehearsal Design

**Status:** User-approved design; implementation planning pending written-spec review

**Date:** 2026-08-10

**Repository:** `C:\Projects\agent-autonomy-harness`

**Execution boundary:** Design and future zero-model rehearsal only

## Purpose

The repository needs an acceptance authority that can evolve without making
previously generated decision packets or evidence manifests unverifiable. The
current `registry/program-acceptance-map.json` is both the live program
acceptance map and the exact acceptance source bound by packet-v1 and the
thirteen-scenario packet-v2 manifest. Its current file SHA-256 is:

```text
c9d0fb437fb3eae93ffd144a2e3ee418dca90d96e5a266b61d7c7ec3efa6079f
```

Changing that file to register the thirteen-scenario manifest evidence would
invalidate the checked packet-v1 and manifest bindings. Freezing the file
forever, however, would prevent the program from registering new evidence or
evolving its acceptance state. This design separates immutable historical
snapshots, current-authority selection, transition evidence, evidence
registration, and assessment promotion.

The immediate implementation target is a pure zero-model migration rehearsal.
It must prove the versioning and migration mechanism in an isolated temporary
root. It must not activate a new repository authority.

## Current Repository Facts

At design time:

- `main`, its upstream, and `origin/main` all resolve to
  `463423cda81f8152427e2010b1fd9b87b639d782`;
- the worktree is clean and ahead/behind is `0/0`;
- the v1 acceptance map contains 61 criteria, 152 evidence rows, and the
  canonical assessment inventory is 46 verified / 15 partial / 0 planned;
- `acceptance.decision-ready-consumer-projection` is `partial`;
- the checked packet-v1 fixture SHA-256 is
  `58410f9576fbbc2f006135d97184d29a9996b1eb11abeaf07988a3a5acf4fc22`;
- the checked thirteen-scenario manifest fixture SHA-256 is
  `ef29ec4de82091dfba3b2e0cfd49c5570cc40410b2beadfd3b5be5bc003176c3`;
- immediately before this specification was added, 103 tracked files directly
  referenced the v1 acceptance path or ID: 21 registry records, 50 scripts, 19
  tests, 11 documents, and two READMEs; this specification is itself one new
  class-A historical reference, so the post-spec live set is expected to be
  104 files; and
- the current program plan and acceptance map enforce a reciprocal path
  relationship, so versioning only the acceptance file would not be sufficient.

These facts are inputs to the rehearsal acceptance boundary, not permanent
product constants except where this design explicitly freezes historical
identity.

## Goals

The design must:

1. preserve the existing v1 acceptance map, packet fixture, and manifest
   fixture byte for byte;
2. distinguish historical validation from current-authority resolution;
3. support independently auditable structural migration, evidence
   registration, assessment transition, and rollback transactions;
4. prevent evidence registration from silently promoting an assessment;
5. classify every current acceptance reference before any current-authority
   switch;
6. validate a candidate v2 authority and selector without activating them;
7. prove atomic selector behavior and reversible migration in a disposable
   zero-model workspace; and
8. preserve the repository's existing evidence and authorization ceilings.

## Non-Goals

This design and its first rehearsal do not:

- modify or replace `registry/program-acceptance-map.json`;
- modify the checked packet-v1 or thirteen-scenario manifest fixtures;
- create or switch a live acceptance-authority selector;
- change any criterion assessment or the 46/15/0 inventory;
- authorize a real program-plan or acceptance-authority migration;
- select or invoke a model, candidate, Skill, Plugin, App, MCP server, Hook, or
  manager;
- install, enable, connect, publish, release, or mutate CC Switch, a consumer,
  an account, or host configuration;
- prove behavior, value, cross-host portability, production readiness,
  release eligibility, or overall Harness completion; or
- make GitHub Actions the primary or sole acceptance surface.

## Approaches Considered

### 1. Immutable snapshots, a current selector, and transition receipts

Every accepted state is a complete immutable snapshot. A small selector names
the current snapshot, and immutable receipts bind each transition. Historical
consumers validate their bound snapshot rather than comparing it with current.

This is the selected approach. It gives simple offline validation, explicit
rollback, and bounded implementation complexity. The current 185-KiB map is
small enough that full snapshots are preferable to a replay-only model.

### 2. Append-only event log with a derived current view

An event stream would record all mutations and replay them into the current
view. This scales well but adds ordering, replay, checkpoint, corruption, and
recovery semantics that are not justified by the current authority size.

### 3. Frozen v1 map plus an evidence sidecar

A sidecar ledger would be easy to add, but it would split acceptance truth
between the map and the ledger. It does not provide a durable carrier for
future criterion, verification, or assessment evolution.

## Architecture

The selected architecture has four roles.

### Legacy v1 snapshot

`registry/program-acceptance-map.json` remains the immutable historical source
bound by existing packet and manifest fixtures. Its path, ID, and SHA-256 must
not change during the rehearsal or an eventual migration.

The current `registry/curation-program-plan.json` also remains available for
the legacy reciprocal relationship. A migration receipt freezes its exact
pre-migration identity so historical validation does not reinterpret the v1
map through a later program plan.

### Immutable v2 snapshots

Each v2 authority state is a complete independently valid document. An
authorized state change creates a new generation; it never edits an earlier
snapshot.

The eventual production layout is:

```text
registry/program-acceptance-authority/
|-- snapshots/
|   `-- v2/
|       |-- g000001.json
|       `-- g000002.json
|-- transitions/
|   |-- g000000-to-g000001.json
|   `-- g000001-to-g000002.json
`-- current.json
```

No file at that production path is created by the rehearsal. The rehearsal
uses an isomorphic tree under a newly created disposable root.

### Transition receipts

A receipt binds the exact predecessor and successor snapshot, program-plan
bindings, transaction class, permitted delta, invariant checks, and
side-effect counters. The first contract recognizes these distinct classes:

- `structural-migration`;
- `evidence-registration`;
- `assessment-transition`; and
- `rollback`.

One receipt has exactly one class. A structural migration cannot register new
evidence. An evidence registration cannot change assessment. An assessment
transition cannot masquerade as evidence discovery. A rollback must target an
ancestor and cannot delete or rewrite immutable history.

### Current selector

The selector resolves the snapshot used to build new artifacts. It binds the
active snapshot, the transition receipt that introduced that state, and the
corresponding program plan.

The selector is not used to invalidate historical artifacts. Packet and
evidence validators follow the exact snapshot originally bound by those
artifacts. Only builders and current-state consumers resolve the selector.

## Contract Files

The rehearsal implementation is expected to introduce these contract types:

- `schemas/program-acceptance-authority-v2.schema.json`;
- `schemas/program-acceptance-current-selector-v1.schema.json`;
- `schemas/program-acceptance-transition-receipt-v1.schema.json`; and
- a machine-readable migration-inventory contract owned by the focused
  implementation module rather than by `scripts/verify.py`.

Schema version numbers are local to their contract. The new selector and
receipt start at schema 1 even though the authority snapshot is schema 2.

### Authority snapshot fields

A v2 snapshot contains exactly:

- `schema` with integer value `2`;
- a unique snapshot `id`;
- stable `authoritySeriesId`;
- positive integer `generation`;
- `predecessorBinding` with explicit schema, ID, generation, path, and SHA-256;
- exact `programPlanBinding`;
- `assessmentVocabulary`;
- `objectives`;
- `acceptanceCriteria`;
- `verifications`; and
- `evidence`.

The snapshot does not contain its own file digest. Its selector and receipt
bind its file SHA-256, avoiding self-reference.

For the v1 predecessor, the binding records authority schema 1 and a null
native generation because the legacy document did not define generations. A
receipt may label it migration generation zero for ordering, but that label
does not modify or claim to be a field in the v1 file.

### Selector fields

The selector contains exactly:

- `schema` with integer value `1`;
- stable selector `id`;
- `authoritySeriesId`;
- `selectionMode`, which is `rehearsal-candidate` in this slice;
- `activeSnapshotBinding`;
- `activeTransitionBinding`;
- `programPlanBinding`;
- `activationAuthorized`, fixed to `false` in the rehearsal; and
- all-zero execution and side-effect counters.

The rehearsal validator rejects a selector that claims current production
activation or any non-zero side-effect counter.

### Transition receipt fields

The receipt contains exactly:

- `schema`, `id`, `authoritySeriesId`, and `transactionType`;
- `fromSnapshotBinding` and `toSnapshotBinding`;
- `fromProgramPlanBinding` and `toProgramPlanBinding`;
- a typed `delta` projection;
- invariant results;
- `authorizationBoundary` distinguishing rehearsal authority from live
  migration authority;
- all-zero model, installation, account, manager, consumer, publication, and
  release counters; and
- an explicit claim boundary.

Receipt files do not contain their own digest. Selectors and later receipts
bind receipt file SHA-256 externally.

## Program-Plan Coupling

The current v1 acceptance validator requires:

```text
program plan -> registry/program-acceptance-map.json
acceptance map -> registry/curation-program-plan.json
```

An eventual migration therefore requires a companion program-plan v2
projection rather than an in-place edit to the historical plan. The candidate
plan preserves all strategic business content and changes only the versioned
acceptance-authority relationship. It points to the stable selector path; the
snapshot binds the exact candidate-plan file digest.

The rehearsal materializes that companion plan only in its fixture and
temporary output root. It does not create a current repository program plan or
change which plan `scripts/verify.py` treats as current.

## Version And Generation Semantics

`schema` and `generation` are separate axes:

- schema changes only when file shape or validation semantics change;
- generation changes for every accepted state transition under the same
  schema;
- immutable files never change generation in place; and
- a current selector change is not sufficient to create or legitimize a
  generation without a valid snapshot and receipt.

The first rehearsal uses three logical states:

```text
legacy v1 / migration generation g000000
  -- structural-migration --> authority v2 / g000001
  -- evidence-registration --> authority v2 / g000002
```

Generation 1 is business-semantics-equivalent to v1. Generation 2 adds only
the thirteen-scenario manifest evidence and its reciprocal criterion link.
This two-transition sequence prevents structural migration and evidence
registration from sharing one receipt.

## Validation Modes

### Historical mode

Historical validation:

1. accepts an explicit authority binding from the artifact under review;
2. reopens that exact path or frozen rehearsal source;
3. verifies ID, schema, and SHA-256;
4. validates the authority under the rules applicable to its schema;
5. validates any frozen companion-plan binding supplied by the transition
   chain; and
6. does not require the snapshot to match the current selector.

### Current mode

Current validation:

1. loads the selector from the configured current-authority surface;
2. validates the selector without following paths outside the allowed root;
3. reopens and validates the active snapshot, introducing receipt, and program
   plan;
4. checks exact reciprocal relationships and SHA-256 bindings;
5. checks transition-chain continuity and generation monotonicity; and
6. returns one resolved authority bundle to the caller.

Builders of new artifacts use current mode only after an independently
authorized real migration. The rehearsal invokes current mode only against
its disposable candidate tree.

### Version-neutral validation components

Pure structure and relationship validators accept an authority document, a
program-plan document, a validation mode, and expected bindings as explicit
arguments. They do not decide which version is current and do not contain an
acceptance registry path.

## Consumer Migration Inventory

Every direct acceptance reference is assigned one semantic class. Directory
or filename alone does not determine the class.

### Class A: immutable historical consumers

This class includes checked packet fixtures, dated evidence records, their
historical validators and tests, and previously committed evidence-specific
plans or specifications. They retain their v1 binding.

### Class B: current-authority consumers

This class includes the current program plan, top-level current acceptance
verification, future packet builders, and current scheduler, closeout, or
goal projections that truly need the latest acceptance state. After a separate
real migration, these consumers resolve the selector.

### Class C: version-neutral components

This class contains pure parsers, relationship validators, and reusable test
helpers. They receive documents and bindings from their caller and own no
current-path policy.

### Class D: migration governance and regression consumers

This class contains the migration inventory, immutable-byte regressions,
candidate rehearsal tests, transition-chain tests, and explicit rollback and
cleanup checks.

Each inventory row records:

- file and reference location;
- consumption purpose;
- class A, B, C, or D;
- current binding;
- candidate binding;
- rehearsal action;
- future live-migration action;
- rollback action;
- verification surface; and
- whether a separate authorization is required.

The inventory is valid only when it covers the exact live reference set with
no missing, duplicate, or extra row. A global string replacement is forbidden.

## Zero-Model Rehearsal Data Flow

The rehearsal performs this sequence:

1. Load and validate the exact v1 acceptance map and current program plan.
2. Verify the v1 map, packet fixture, and manifest fixture byte locks.
3. Discover the live direct-reference set and validate complete inventory
   classification.
4. Create a new empty disposable output root outside the production authority
   path.
5. Build the candidate program-plan v2 projection.
6. Build v2/g000001 as a full semantic projection of v1 with no new evidence.
7. Build and validate the `structural-migration` receipt from v1/g000000 to
   v2/g000001.
8. Build v2/g000002 by adding only
   `evidence.harness-decision-packet-thirteen-scenario-manifest-poc-2026-08-09`
   and the reciprocal link to
   `acceptance.decision-ready-consumer-projection`.
9. Build and validate the `evidence-registration` receipt from g000001 to
   g000002.
10. Stage and atomically write a rehearsal selector pointing to g000002.
11. Validate v1 in historical mode and g000002 in current mode.
12. Build a rollback receipt targeting ancestor g000001 and atomically move the
    rehearsal selector to g000001 without deleting g000002.
13. Revalidate historical v1, current g000001, immutable g000002, and the full
    receipt chain.
14. Remove the entire disposable rehearsal root.
15. Recheck the repository worktree, locked bytes, and zero external-state
    counters.

The reusable builder may emit canonical JSON to stdout. Any file-writing mode
must require an explicit empty disposable output root and must reject the
repository's production authority path. The rehearsal exposes no activation
command.

## Atomicity And Rollback

Snapshot and receipt bytes are serialized canonically, written to a staging
area, flushed, fsynced, and fully validated before the selector can change.
The selector is written to a sibling temporary file and replaced with
`os.replace` only after all dependencies pass.

If snapshot, receipt, or selector validation fails:

- the prior selector bytes remain unchanged;
- stdout remains empty for a file-output CLI;
- a stable machine-readable error is written to stderr;
- the CLI exits 2; and
- staging cleanup is verified.

A rollback creates a new receipt and changes only the selector. It cannot
modify or delete a snapshot or earlier receipt. The target must be a verified
ancestor in the same authority series. Rehearsal cleanup removes only the
newly created disposable root after confirming its resolved path is outside
the repository and other protected roots.

## Typed Failure Boundary

The implementation plan must preserve stable typed errors for at least these
classes:

- `legacy-authority-drift`;
- `legacy-program-plan-drift`;
- `legacy-packet-fixture-drift`;
- `legacy-manifest-fixture-drift`;
- `migration-inventory-incomplete`;
- `migration-consumer-class-invalid`;
- `acceptance-authority-schema-invalid`;
- `acceptance-authority-series-invalid`;
- `acceptance-authority-generation-invalid`;
- `acceptance-authority-predecessor-mismatch`;
- `acceptance-program-plan-binding-drift`;
- `acceptance-selector-target-invalid`;
- `acceptance-transition-receipt-invalid`;
- `acceptance-transition-chain-broken`;
- `acceptance-transition-type-mismatch`;
- `acceptance-structural-migration-overreach`;
- `acceptance-evidence-registration-overreach`;
- `acceptance-assessment-promotion-forbidden`;
- `acceptance-inventory-count-drift`;
- `acceptance-evidence-link-asymmetric`;
- `acceptance-evidence-id-duplicate`;
- `acceptance-evidence-source-missing`;
- `acceptance-evidence-source-drift`;
- `acceptance-historical-consumer-repointed`;
- `acceptance-current-consumer-legacy-bypass`;
- `acceptance-neutral-consumer-path-owned`;
- `acceptance-rollback-receipt-invalid`;
- `acceptance-rollback-target-not-ancestor`;
- `acceptance-atomic-output-preserved`;
- `acceptance-rehearsal-cleanup-incomplete`;
- `acceptance-activation-not-authorized`; and
- `acceptance-side-effect-counter-nonzero`.

Unexpected exceptions are implementation defects and may not be normalized
into a false passing result. CLI input errors must remain deterministic and
must not leak Python tracebacks as the machine contract.

## Fail-Closed Test Matrix

The focused matrix must independently mutate at least:

1. each locked v1 source or fixture;
2. one missing, duplicate, extra, and incorrectly classified inventory row;
3. snapshot schema, series ID, generation, predecessor ID, predecessor path,
   and predecessor digest;
4. program-plan ID, path, digest, and reciprocal selector relationship;
5. selector snapshot, receipt, plan, mode, authorization, and side-effect
   counters;
6. receipt type, predecessor, successor, generation step, and permitted delta;
7. one objective, criterion, verification, and pre-existing evidence row in
   the structural migration;
8. evidence addition, reciprocal criterion link, assessment, criterion count,
   and unrelated records in the evidence-registration transition;
9. registered evidence source existence and digest;
10. a historical consumer redirected to current;
11. a current consumer left on the legacy path in the simulated activated
    state;
12. a version-neutral component that reacquires path ownership;
13. rollback to a non-ancestor, another series, or a rewritten snapshot;
14. selector replacement failure with an existing sentinel file;
15. staging or rehearsal-root cleanup failure; and
16. any non-zero model or external-state counter.

Each mutation must reject with its expected typed code. A matrix runner that
does not execute the real builder and validator path is insufficient.

## Positive Acceptance Standard

The rehearsal is accepted only when all of the following are freshly proved:

- `registry/program-acceptance-map.json` remains byte-identical with SHA-256
  `c9d0fb437fb3eae93ffd144a2e3ee418dca90d96e5a266b61d7c7ec3efa6079f`;
- the packet-v1 fixture remains byte-identical with SHA-256
  `58410f9576fbbc2f006135d97184d29a9996b1eb11abeaf07988a3a5acf4fc22`;
- the thirteen-scenario manifest fixture remains byte-identical with SHA-256
  `ef29ec4de82091dfba3b2e0cfd49c5570cc40410b2beadfd3b5be5bc003176c3`;
- every file in the freshly derived live reference set is represented exactly
  once in the migration inventory, with the pre-spec 103-file observation and
  this specification's additional class-A reference retained as explainable
  baseline history;
- v2/g000001 is business-semantics-equivalent to v1;
- v2/g000002 differs from g000001 only by the one manifest evidence row and
  its reciprocal criterion link;
- g000001 and g000002 both contain 61 criteria and preserve 46 verified / 15
  partial / 0 planned;
- `acceptance.decision-ready-consumer-projection` remains `partial`;
- historical v1 and candidate-current v2 validate independently;
- rollback from g000002 to ancestor g000001 preserves both immutable snapshots
  and all receipts;
- failed selector output preserves a pre-existing sentinel byte for byte;
- the disposable root is removed and the tracked worktree is unchanged by the
  rehearsal itself;
- model, installation, enablement, account, Plugin, manager, consumer,
  publication, release, and production-activation counters remain zero;
- focused tests and the direct rehearsal CLI pass;
- the complete unittest suite runs serially and passes;
- `python -B scripts/verify.py` passes after the focused verifier is integrated;
  and
- GitHub Actions, if available, is treated only as corroboration.

If the live reference count or another input legitimately changes before
implementation, the implementation must stop and rebaseline the design input
through an explicit reviewed inventory change. It may not silently weaken the
exact-coverage check to preserve an earlier count.

## Expected Implementation Boundaries

The future implementation plan should keep responsibilities in small focused
modules:

- schema files define data shape only;
- one pure authority module builds and validates snapshots, selectors,
  receipts, and transition deltas;
- one migration-inventory module owns reference classification and exact set
  reconciliation;
- one thin CLI owns arguments, canonical stdout, atomic disposable-root output,
  structured stderr, and exit codes;
- focused tests own positive and adversarial cases;
- one independent dated evidence record may summarize the successful rehearsal;
  and
- `scripts/verify.py` imports one focused repository validator rather than
  absorbing construction or matrix logic.

The verifier integration must avoid replaying an expensive mutation matrix in
every unrelated `test_verify_integration` mutation. Dedicated tests and the
direct validator still exercise the complete real matrix; top-level verifier
tests may replace the focused runner only inside unrelated failure-isolation
helpers while retaining a positive integration test that proves normal
`verify()` calls it exactly once.

## Documentation And Authority Boundary

After a successful rehearsal implementation, current planning, continuation,
goal-mode, and public navigation documents are updated only where their
current-state wording would otherwise be stale. Historical plans,
specifications, evidence records, packet fixtures, and manifests are not
rewritten.

The rehearsal evidence remains independently governed because the v1
acceptance map is frozen. Registering that rehearsal evidence in a live v2
authority, making the v2 selector current, migrating the program plan, or
changing any assessment requires a later separately reviewed and explicitly
authorized transaction.

## Claim Ceiling

Passing this design's acceptance standard proves only that the repository can
construct, validate, select, roll back, and clean up a versioned acceptance
authority candidate through a deterministic zero-model rehearsal while
preserving historical v1 identity.

It does not prove task-time selection, instruction delivery, candidate or
Plugin behavior, user value, cross-host portability, production readiness,
release eligibility, residual-gap necessity, live authority migration, or
overall Harness completion.
