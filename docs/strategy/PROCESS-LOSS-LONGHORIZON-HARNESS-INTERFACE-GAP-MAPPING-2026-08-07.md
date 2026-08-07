# LongHorizon-Harness Interface Gap Mapping

Date: 2026-08-07

Status: verified zero-model static mapping; no acquisition or execution

Governed evidence:
[`process-loss-longhorizon-harness-interface-gap-mapping-2026-08-07.json`](../../registry/process-loss-longhorizon-harness-interface-gap-mapping-2026-08-07.json)

## Decision

The frozen LongHorizon-Harness revision provides four directly useful design
references, five surfaces that would require a thin Harness-owned adapter, and
three requirements that must remain entirely Harness-owned. This is sufficient
to stop duplicate authoring of an equivalent operational coordinator while
keeping direct adoption and adapter implementation unauthorized.

The mapping does not install, import, or run LongHorizon-Harness. It calls no
model and does not prove interface compatibility, runtime behavior, benchmark
reproduction, security, portability, user value, residual gap, or production
readiness.

## Bound sources

The external side is fixed by the preceding
[`static reuse assessment`](PROCESS-LOSS-EXTERNAL-REUSE-RESEARCH-2026-08-07.md)
to public repository revision
`b49ebf9654c1ee75eaf56dfe9eec1745fddcfa58`, tree
`cf5470d1242e6a092c91a709efeff68c61d36681`, and nine selected Git objects.

The Harness side is bound to:

- the chained-transform process-fidelity protocol;
- its v2 conditional recovery amendment;
- the additive cumulative-loss accounting contract;
- the handoff receiver delta ledger;
- the parent-derived dispatch and route-receipt contract; and
- the canonical program acceptance map.

No current external branch state, README drift, popularity, benchmark claim,
or later release can silently change this mapping. A future comparison must
freeze a new source snapshot if the candidate revision changes.

## Classification

`present` means the source contains the named operational mechanism. It does
not mean the mechanism has passed Harness acceptance. `partial` means the
surface exists but misses a required evidence, identity, authority, or
lifecycle invariant. `absent` means the frozen source does not expose a
sufficient mechanism for the Harness requirement.

`direct-reference` permits design comparison only, not copying or execution.
`thin-adapter-required` means a future separately authorized adapter would have
to translate or harden the surface without moving governance authority into the
external runtime. `harness-retained` means the obligation cannot be delegated
to LongHorizon-Harness.

## Interface matrix

| Interface | Source coverage | Disposition | Main boundary |
| --- | --- | --- | --- |
| Task state and next contract | Partial | Thin adapter required | Natural-language state lacks typed source, invariant, provenance, authority, uncertainty, and acceptance fields. |
| Manager route | Present | Direct reference | `execute`, `done`, `blocked`, and `ask` are useful, but route quality is unproved. |
| Fresh-context Executor | Present | Direct reference | Fresh context is not a parent-captured host route or raw-artifact receipt. |
| Independent audit report | Partial | Thin adapter required | Hard read-only enforcement, parent recomputation, and equivalent Codex role isolation are missing. |
| Persistent round evidence | Present | Direct reference | Persistence lacks immutable parent-computed identities and crash-consistent replay. |
| Completion guard | Present | Direct reference | It blocks unaudited `done`, but does not prove human acceptance or release readiness. |
| Human ask and blocked gates | Partial | Thin adapter required | Human stopping exists; accountable acceptance, supersession, and decision identity do not. |
| Parent-derived raw receipts | Absent | Harness retained | Trajectories and adapter logs cannot replace effective host route and input/output hash receipts. |
| Cumulative process-loss ledger | Absent | Harness retained | Progress and audit status do not measure new, carried, recovered, unique, peak, or budget-breach loss. |
| Failure repair and resume | Partial | Thin adapter required | Within-run repair exists; conditional recovery receipts and cross-process replay do not. |
| Host-owned permission enforcement | Absent | Harness retained | Default dangerous bypass conflicts with the Harness authority floor. |
| Backend adapter seam | Partial | Thin adapter required | The seam is useful, but safe defaults, exact route receipts, and Codex role authority are not established. |

The resulting counts are exact for this mapping: four `present`, five
`partial`, and three `absent`; equivalently four `direct-reference`, five
`thin-adapter-required`, and three `harness-retained` dispositions.

## Direct references

The Manager route, fresh-context Executor, persisted round artifacts, and
completion guard are strong enough to use as comparison and design references.
They reduce the likelihood that the Harness will duplicate a working loop
shape merely because the current repository has not implemented one.

They remain references rather than adopted code. MIT licensing makes reuse
legally possible under its terms, but license permission does not satisfy
security, dependency, authority, portability, compatibility, maintenance, or
value gates.

## Thin-adapter candidates

A future adapter would have to address all five partial surfaces together:

- translate natural-language task state and contract artifacts into typed,
  source-bound fields without treating the external format as semantic
  authority;
- wrap audit output in parent-recomputed evidence and a preventive read-only
  boundary;
- preserve human decision identity and accountable terminal review around
  `ask` and `blocked`;
- distinguish within-run repair from source-backed recovery, process-crash
  resume, and cross-host replay; and
- replace dangerous backend defaults with exact host route receipts,
  role-specific least privilege, and no silent fallback.

This mapping does not authorize that adapter. An adapter that merely reshapes
JSON or prompts while leaving permission bypass, identity, and recovery gaps
open would not satisfy the gate.

## Harness-retained authority

Three interface obligations are absent from the candidate and remain explicit
Harness responsibilities:

1. Parent-derived raw input/output, stage-contract, thread, turn, and effective
   route receipts with artifact-substitution rejection.
2. Per-hop and cumulative process-loss accounting that keeps terminal
   correctness separate from intermediate loss.
3. Host-owned permission enforcement, least privilege, preventive auditor
   read-only controls, and bounded workspace authority.

The Harness also retains human-to-source binding, semantic and consequential
decision continuity, terminal-to-human acceptance, general and
software-lifecycle coverage, rollback, cleanup, release governance, and
cross-host acceptance. Those are broader than an operational loop interface.

## Next gate

The next bounded result is a pure zero-model, fail-closed execution preflight.
It should specify and failure-test:

- host-owned permission profiles for Manager, Executor, and Auditor;
- an exact disposable workspace and proof that no user workspace is targeted;
- preventive or transactional mutation handling plus a rollback oracle;
- parent-derived thread, turn, effective route, input, output, and contract
  receipts;
- the difference between in-process repair and process-crash resume; and
- stop conditions that reject permission bypass, unknown route identity,
  missing rollback, workspace ambiguity, or recovery overclaim.

That preflight must not acquire or execute LongHorizon-Harness. Installation,
enablement, model dispatch, account connection, consumer mutation, adapter
implementation, upstream contribution, publication, and release remain
separate authorization gates. A real Claude task is not required for this
zero-model gate.
