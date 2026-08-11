# Evidence Binding Precision Reconciliation v1 Design

Date: 2026-08-11

## Decision

Refine the existing evaluation and software-engineering coverage reconciliation
so that every criterion row distinguishes the evidence used for coordinate
selection, claim boundaries, and the next admissible evidence class. Preserve
the current flat `evidenceIds` field as an exact compatibility projection of
those role bindings.

The change corrects evidence precision only. It does not change any criterion,
cluster, evaluation dimension, lifecycle slice, scenario, disposition, route
state, claim ceiling, next-evidence wording, acceptance assessment, or
authority flag.

## Current problem

The existing validator proves that every `evidenceIds` entry is known and is
registered to the same acceptance criterion. It does not prove that the row is
anchored by the most specific current evidence already available.

Nine rows expose that gap:

- eight rows use only `evidence.program-plan`;
- one row uses only `evidence.readme`;
- each of those nine criteria already registers more specific evidence in the
  frozen v1 acceptance authority.

The current bindings are legal but under-specified. They make it difficult to
tell which evidence supports the mapped coordinates, which evidence constrains
the claim ceiling, and which evidence demonstrates why the next gate remains
open.

## Approaches considered

### 1. Role-aware bindings with a flat compatibility projection — selected

Add `evidenceRoleBindings` to every criterion row with three ordered unique ID
lists:

- `coordinateBasisIds`;
- `boundaryBasisIds`;
- `nextEvidenceBasisIds`.

Keep `evidenceIds` as the stable first-seen union of those three lists. This
provides semantic precision without breaking existing readers that consume the
flat list.

Trade-off: the record becomes slightly larger, but the role distinction is
explicit, locally verifiable, and reversible.

### 2. Flat-list strengthening only

Replace generic-only lists with more specific evidence IDs and add a validator
rule that rejects generic-only rows.

Trade-off: smaller change, but the flat list still cannot distinguish support
for a coordinate from evidence that only establishes a boundary or open gate.
It would address the symptom while retaining the ambiguity.

### 3. Separate evidence-role crosswalk record

Leave the current record unchanged and create a second crosswalk keyed by
criterion ID.

Trade-off: avoids changing the current record shape, but creates a second
authority that must remain synchronized with the criterion rows. This conflicts
with the existing subtraction decision against duplicate authorities.

## Data model

Every `criterionReconciliations` row gains:

```json
"evidenceRoleBindings": {
  "coordinateBasisIds": ["evidence.specific-coordinate-source"],
  "boundaryBasisIds": ["evidence.specific-boundary-source"],
  "nextEvidenceBasisIds": ["evidence.specific-open-gate-source"]
}
```

Rules:

1. All three keys are required and no additional role key is allowed.
2. Every role value is an ordered, unique, non-empty list.
3. Every referenced ID exists in the frozen acceptance authority and belongs
   to the same criterion.
4. IDs within each role preserve their relative order from the criterion's
   frozen authority `evidenceIds` list.
5. `evidenceIds` equals the stable first-seen union of coordinate, boundary,
   and next-evidence IDs in that order.
6. `evidence.program-plan` and `evidence.readme` are generic evidence. They may
   remain supplemental boundary or next-gate evidence, but a row's
   `coordinateBasisIds` may not be generic-only.
7. One specific item may support multiple roles when the governed evidence
   genuinely contains both mechanism and boundary semantics. Repetition across
   roles is allowed; duplication within one role is not.
8. Evidence precision does not promote the evidence's claim. Each referenced
   evidence kind and the row's existing `claimCeiling` remain authoritative.

## Nine-row replacement set

The following table names the minimum specific evidence set. Generic evidence
is removed unless it carries a role not already supported by a specific item.

| Criterion | Coordinate basis | Boundary basis | Next-evidence basis |
| --- | --- | --- | --- |
| `acceptance.decision-ready-consumer-projection` | `evidence.harness-decision-packet-core-poc-2026-08-08` | `evidence.decision-ready-consumer-projection-evaluation` | `evidence.decision-ready-consumer-projection-evaluation`, `evidence.harness-decision-packet-core-poc-2026-08-08` |
| `acceptance.consumer-mapping-evidence` | `evidence.codex-consumer-skill-mapping-snapshot-2026-08-07`, `evidence.claude-consumer-skill-projection-snapshot-2026-08-07`, `evidence.offline-plugin-projection-poc-2026-08-08` | `evidence.consumer-mapping-evidence-gap-reconciliation-2026-07-18` | `evidence.cc-switch-disabled-consumer-root-readonly-inventory-2026-08-08` |
| `acceptance.standard-revalidation-cascade` | `evidence.standard-revalidation-cascade-poc-2026-08-07` | `evidence.standard-revalidation-cascade-poc-2026-08-07` | `evidence.standard-revalidation-cascade-poc-2026-08-07` |
| `acceptance.final-program-cleanup-gate` | `evidence.closeout-cleanup-debt-preview-2026-07-24`, `evidence.closeout-cleanup-execution-2026-07-30` | `evidence.closeout-cleanup-debt-preview-2026-07-24` | `evidence.closeout-cleanup-debt-preview-2026-07-24` |
| `acceptance.dynamic-runtime-control-gap-research` | `evidence.dynamic-runtime-control-gap-review-2026-07-18`, `evidence.mcp-app-server-0.146.0-reload-release-version-change-2026-08-02`, `evidence.codex-desktop-resource-observability-preflight-2026-07-31`, `evidence.codex-desktop-official-control-surface-access-preflight-2026-07-31` | `evidence.dynamic-runtime-control-gap-review-2026-07-18` | `evidence.mcp-app-server-multi-connection-subscription-preflight-2026-07-27` |
| `acceptance.cc-switch-source-preserving-skill-pool` | `evidence.cc-switch-source-preserving-skill-pool-strategy`, `evidence.codex-consumer-skill-mapping-snapshot-2026-08-07`, `evidence.claude-consumer-skill-projection-snapshot-2026-08-07`, `evidence.mattpocock-skills-v1.2.3-exact-pin-reconciliation-event-2026-08-08` | `evidence.portfolio-tasktime-projection-contract-2026-08-06` | `evidence.cc-switch-disabled-consumer-root-readonly-inventory-2026-08-08` |
| `acceptance.foreign-managed-capability-coexistence` | `evidence.user-sovereignty-and-foreign-coexistence-reconciliation-2026-07-18`, `evidence.codex-consumer-skill-mapping-snapshot-2026-08-07`, `evidence.claude-consumer-skill-projection-snapshot-2026-08-07` | `evidence.cc-switch-live-source-ownership-reconciliation-2026-07-18` | `evidence.cc-switch-disabled-consumer-root-readonly-inventory-2026-08-08` |
| `acceptance.optional-hook-mode-chain` | `evidence.round03-native-runtime-baseline`, `evidence.dynamic-runtime-control-gap-review-2026-07-18` | `evidence.custom-manager-retirement-reconciliation` | `evidence.dynamic-runtime-control-gap-review-2026-07-18` |
| `acceptance.native-task-orchestration-boundary` | `evidence.harness-three-lane-program-acceptance-reconciliation-2026-07-27` | `evidence.harness-three-lane-program-acceptance-reconciliation-2026-07-27` | `evidence.harness-three-lane-program-acceptance-reconciliation-2026-07-27` |

## The other six rows

The six rows that already use specific evidence gain these exact role sets:

| Criterion | Coordinate basis | Boundary basis | Next-evidence basis |
| --- | --- | --- | --- |
| `acceptance.solution-neutral-collaboration-rebaseline` | `evidence.human-ai-collaboration-coverage-rebaseline`, `evidence.human-ai-collaboration-scenario-evidence-matrix-batch-01` | `evidence.human-ai-collaboration-coverage-rebaseline` | `evidence.human-ai-collaboration-scenario-evidence-matrix-batch-01`, `evidence.human-ai-collaboration-current-candidate-capability-coverage-reconciliation-2026-08-01` |
| `acceptance.software-engineering-lifecycle-specialization` | `evidence.human-ai-collaboration-coverage-rebaseline`, `evidence.human-ai-collaboration-scenario-evidence-matrix-batch-01`, `evidence.multidimensional-software-engineering-evaluation-contract-2026-07-31`, `evidence.multidimensional-software-engineering-source-snapshot-2026-07-31` | `evidence.multidimensional-software-engineering-evaluation-contract-2026-07-31`, `evidence.multidimensional-software-engineering-source-snapshot-2026-07-31` | `evidence.human-ai-collaboration-tdd-noncomparative-dispatch-successor-contract-v2-2026-07-27` |
| `acceptance.end-to-end-process-fidelity` | `evidence.human-ai-collaboration-coverage-rebaseline`, `evidence.human-ai-collaboration-scenario-evidence-matrix-batch-01`, `evidence.human-ai-collaboration-process-fidelity-cumulative-loss-accounting-poc-2026-07-27`, `evidence.human-ai-collaboration-software-lifecycle-thin-slice-zero-model-calibration-2026-07-27` | `evidence.human-ai-collaboration-process-fidelity-v2-protocol-2026-07-27`, `evidence.human-ai-collaboration-process-fidelity-raw-event-trace-eligibility-2026-07-27`, `evidence.process-loss-longhorizon-harness-static-reuse-assessment-2026-08-07` | `evidence.human-ai-collaboration-process-fidelity-chained-transform-dispatch-gate-contract-2026-07-27`, `evidence.human-ai-collaboration-process-fidelity-chained-transform-dispatch-ledger-contract-2026-07-27`, `evidence.human-ai-collaboration-process-fidelity-raw-event-trace-eligibility-2026-07-27`, `evidence.process-loss-longhorizon-harness-exact-source-static-review-2026-08-07` |
| `acceptance.native-runtime-baseline` | `evidence.round03-native-runtime-baseline` | `evidence.native-runtime-baseline-evidence-gap-reconciliation-2026-07-18` | `evidence.native-runtime-baseline-evidence-gap-reconciliation-2026-07-18` |
| `acceptance.residual-gap-proof` | `evidence.round03-alternative-comparison-batch-01`, `evidence.round03-evidence-protocol-batch-01` | `evidence.residual-gap-proof-evidence-gap-reconciliation-2026-07-18`, `evidence.skill-ecosystem-current-evidence-reconciliation-2026-07-27` | `evidence.round03-evidence-protocol-batch-01`, `evidence.human-ai-collaboration-current-candidate-capability-coverage-reconciliation-2026-08-01` |
| `acceptance.standard-candidate-contract` | `evidence.ai-era-classical-software-engineering-principles-revalidation-2026-07-31`, `evidence.multidimensional-software-engineering-evaluation-contract-2026-07-31`, `evidence.multidimensional-software-engineering-source-snapshot-2026-07-31` | `evidence.multidimensional-software-engineering-independent-review-readiness-2026-07-31` | `evidence.multidimensional-software-engineering-independent-review-readiness-2026-07-31` |

This slice does not attempt an exhaustive mapping of every evidence item
registered to a criterion. The role lists remain bounded to evidence necessary
to explain the current sparse row.

## Validator behavior

The existing validator is extended to fail closed when:

- a row omits `evidenceRoleBindings` or adds an unknown role;
- a role list is empty, duplicated, violates frozen criterion evidence order,
  or contains an unknown or cross-criterion evidence ID;
- `coordinateBasisIds` contains only generic evidence;
- the flat `evidenceIds` value is not the stable first-seen role union;
- a row loses its existing criterion, cluster, coordinate, disposition, route,
  claim, next-evidence, counter, or authority boundary; or
- a generic evidence ID is treated as proof of behavior, value, portability,
  production, release, closeout, or a residual gap.

The validator does not attempt to infer semantic relevance from evidence ID
keywords. The canonical role assignments are reviewed repository data; the
validator enforces their structure, ownership, and generic-only prohibition.

## TDD and repository integration

The focused test suite first adds failing mutations for:

- missing role bindings;
- an unknown role key;
- an empty role;
- duplicate role evidence;
- role evidence reordered against the frozen criterion evidence list;
- cross-criterion evidence;
- generic-only coordinate evidence;
- a flat-list/role-union mismatch; and
- coordinate, assessment, claim, authority, or counter drift during the
  precision update.

After the RED failures are observed, update the canonical record and validator
minimally, then integrate the new design, plan, record, validator, and tests
into the repository verifier. Append bounded checkpoints to the current
strategy, goal-mode, and continuation projections.

## Acceptance

The slice is accepted only when:

1. all fifteen rows have exact three-role evidence bindings;
2. zero row is generic-only for coordinate support;
3. the nine weak rows use the reviewed specific evidence set above;
4. `evidenceIds` is the exact stable role union for every row;
5. all evidence remains criterion-owned under the frozen v1 authority;
6. the 15 criterion rows and every existing coordinate, route, disposition,
   claim ceiling, and next-evidence statement remain unchanged;
7. the acceptance inventory remains 46 verified / 15 partial / 0 planned;
8. the four frozen v1 authority/fixture inputs remain byte-identical;
9. no live selector, v2 migration, assessment transition, external execution,
   consumer mutation, cleanup, publication, or release occurs; and
10. focused tests, the standalone validator, repository verifier, and full
    local serial test suite pass.

## Non-goals

- no coordinate redesign or Cartesian coverage model;
- no new evidence generation, model dispatch, candidate execution, or real
  task simulation;
- no external discovery, installation, enablement, account connection, CC
  Switch mutation, or consumer change;
- no acceptance promotion, hard-standard admission, residual-gap admission,
  live v2 plan/selector migration, cleanup, publication, or release; and
- no commit or push without a later explicit authorization.
