# TDD Current Execution-Readiness Reconciliation

Date: 2026-07-27

Status: current execution readiness blocked; both static diagnostic admissions
satisfied; control-plane evidence remains offline-only

## Decision

The exact Matt and Superpowers candidates now both have identity-bound,
diagnostic-only repository-governance admission. That closes the static
candidate-review gate. It does not make either candidate executable now.

Current materialization, candidate execution, app-server construction, and
model dispatch remain blocked.

## Gate reconciliation

| Gate | Current result | Boundary |
| --- | --- | --- |
| Exact-candidate static admission | Satisfied for both | Repository-governance diagnostic only |
| Protocol execution eligibility | Blocked | Current protocol still says no candidate is eligible and contains no live ledger-authority binding |
| Dispatch source/toolchain freshness | Blocked | The 2026-07-26 preflight is a dated observation and explicitly is not fresh for dispatch |
| Adapter authorization envelope | Blocked | The static decisions are not short-lived adapter dispatch envelopes and contain no current validity window |
| Identity ledger | Offline PoC satisfied; live blocked | Append-only ordering is tested, but authority is not configured and the cap is ledger-local |
| Preconstruction atomicity | Offline partial; live blocked | Reservation-before-fake-factory is tested; source-to-materialization freshness and real app-server construction are not |
| Resource ownership and cleanup | Offline partial; live blocked | Same-process synthetic cleanup is tested; real process/socket, crash, and cross-process cleanup are not |
| Diagnostic-runner successor | Blocked | The formal weak-acceptance policy shell conflicts with the non-comparative protocol; no independent diagnostic runner or shared transport core exists |
| Current human/runtime authority | Blocked | Both decisions and this reconciliation explicitly authorize no materialization, execution, or model request |

## Why the two admissions are still useful

The admissions remove an ambiguity that previously affected both candidates:
the exact bytes, license, bounded fixture compatibility, exclusions, and
non-release scope have now been reviewed. A future dispatch gate may consume
that fact as one input.

They are intentionally not converted into the authorization adapter's
short-lived `diagnostic-only-exact-candidate-execution-admission` document.
That adapter document must bind a dispatch-time fresh source/toolchain
preflight, protocol identity, static audit, candidate identity, validity
window, and live ledger authority. Reusing the static decision as that
ephemeral authority would erase the freshness and current-authorization
boundary.

The historical adapter also reads
`diagnosticDesign.replacementDispatchAllowed`, while the governing protocol
declares `replacementDispatchesAllowed`. Its synthetic unit bundle repeats the
singular field, so those tests do not establish production-protocol
compatibility. Do not rewrite the hash-bound historical PoC in place. A future
successor dispatch contract must make the plural protocol field canonical,
reject the singular alias, and bind its own fresh evidence chain.

There is a second incompatibility that a fresh preflight alone cannot repair.
The historical static gap audit permanently binds the dated preflight, while
the historical adapter requires the audit's preflight digest to equal the
dispatch-time fresh preflight digest. Static governance, dispatch-time
freshness, and independent execution authority must therefore become three
separate successor evidence layers. Do not rewrite the old audit or adapter to
make their hashes appear continuous.

## Current runner and resource mismatches

The formal runner already knows the Matt and Superpowers arm names and can
materialize source-pinned projections. Its native first attempt also proves
that a bounded app-server and normalization path has run before.

That is not candidate execution readiness. The current runner:

- uses a formal policy shell that counts valid output toward weak-Agent
  acceptance, while the non-comparative diagnostic protocol explicitly sets
  `formalAcceptanceContribution=false`;
- does not import or call the non-comparative authorization adapter;
- does not reserve through the append-only identity ledger;
- does not construct through the tested runner preflight;
- materializes the treatment before app-server construction without a current
  dispatch authorization transaction; and
- has no live app-server handle/resource contract tied to reservation,
  construction outcome, crash recovery, or cross-process exclusion.

The historical ledger records host thread and turn identifiers only after the
host responds. It has no durable pre-send `thread-start-intent` or
`turn-start-intent`, leaving an accepted-before-bind crash window ambiguous.
The historical runner preflight also transfers a raw successful handle without
returning an owner that exposes its cleanup callbacks. A successor must return
an explicit closeable owner and persist a terminal `resources-closed` event.

No candidate or model was run while producing this reconciliation.

## Bounded next transition

A zero-side-effect successor slice must first:

1. preregister a successor dispatch contract and pure offline bundle builder;
2. preserve the historical protocol, preflight, audit, adapter, ledger, runner
   preflight, and formal runner as immutable evidence;
3. separate static governance, dispatch-time source freshness, and independent
   authority;
4. normalize the plural replacement field and reject the historical singular
   alias; and
5. exclude the formal weak-acceptance policy shell from the non-comparative
   diagnostic path.

A later separately authorized diagnostic runner or shared transport
integration must then bind one live ledger authority, persist pre-send thread
and turn intents, materialize only from the frozen source snapshot after
reservation, return an explicit closeable app-server owner, and validate real
child-process/socket ownership, cross-process exclusion, crash recovery, and
exactly-once cleanup before any candidate or model request.

Until those gates pass, both candidates remain metadata-only.

## Claim boundary

This reconciliation does not prove invocation, Skill-body delivery,
behavioral causation, value, preference, superiority, general TDD competence,
production readiness, cross-host portability, a residual self-authored gap, or
release admission.
