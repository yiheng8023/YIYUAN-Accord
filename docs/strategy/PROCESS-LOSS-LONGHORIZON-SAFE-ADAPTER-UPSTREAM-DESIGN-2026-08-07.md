# LongHorizon Safe-Adapter And Upstream-Change Design

## Decision

The authorized design uses an **upstream-first, thin-adapter-only** strategy.
LongHorizon-Harness remains the preferred external reference for the
Manage-Execute-Audit coordinator loop, fresh-context execution, persistent
round evidence, completion gating, and human routes. The Harness must not
reimplement that coordinator while the candidate remains viable.

Direct adoption is still blocked. This design does not acquire or run the
candidate, install dependencies, dispatch a model, write upstream, implement an
adapter, change CC Switch, change consumer configuration, or advance any
acceptance criterion. No real Claude task is required for this design gate.

Governed record:
`registry/process-loss-longhorizon-safe-adapter-upstream-design-2026-08-07.json`.

## Source boundary

The design is bound to exact revision
`b49ebf9654c1ee75eaf56dfe9eec1745fddcfa58` and tree
`cf5470d1242e6a092c91a709efeff68c61d36681`. It consumes the findings in the
authorized exact-source static review. It does not treat mutable upstream
`main`, author benchmarks, or repository visibility as behavior evidence.

## What belongs upstream

Changes that improve the candidate for every responsible consumer should be
proposed upstream before they are wrapped locally:

1. Make Claude and Codex permission-bypass flags explicit opt-ins and preserve
   host-owned approval and sandbox defaults.
2. Add a versioned cross-process resume or replay command that validates saved
   state before continuing.
3. Replace POSIX-only command, process-group, signal, and screenshot assumptions
   with tested platform abstractions.
4. Hash large files or mark them explicitly unverifiable; size and mtime alone
   cannot stand in for content integrity.
5. Add an independent core-package test suite and require it before release.

These are design candidates only. No issue, pull request, fork, or publication
is authorized by this record.

## What the thin Harness adapter may own

The adapter is a boundary translator, not a second coordinator:

| Port | Harness-owned obligation |
| --- | --- |
| Host execution policy | Translate role policy into native host approval and sandbox settings; reject bypass flags. |
| Disposable workspace transaction | Create a protected disposable root, journal mutations, stop on boundary drift, and emit rollback receipts. |
| Parent-derived route receipt | Observe the actual role, model, reasoning, command, artifact, and termination path outside candidate self-report. |
| Cumulative process-loss accounting | Compute per-hop new, carried, recovered, unique, peak, and budget-breach loss separately from final correctness. |
| Capability lifecycle | Keep Plugin, MCP, and Skill acquisition or activation under CC Switch or host authority. |
| Recovery validation | Validate candidate state, workspace identity, transaction journal, and replay safety before any resume. |

The adapter must not reimplement the Manage-Execute-Audit loop, silently fork
the candidate core, replace the host permission system, become a capability
manager, self-authorize execution, or convert static evidence into behavior or
value claims.

## Phase gates

1. **Design — complete.** Static classification only; no real task required.
2. **Upstream proposal package — not authorized.** May later contain focused
   issue/patch proposals, but making an external write requires separate owner
   authority.
3. **Pure adapter-contract PoC with a fake candidate — not authorized.** This
   would test only ports, receipts, rejection, and rollback contracts without
   acquiring or running LongHorizon-Harness and without model dispatch.
4. **Isolated candidate execution — not authorized.** It requires a fresh
   disposable root, exact source, dependency and supply-chain review, preventive
   permission enforcement, transaction recovery, and separate execution
   authority.
5. **Behavior and value comparison — blocked.** It additionally requires a
   naturally occurring real task, fixed comparison artifacts, and separate
   model/data/account authority. The user must not invent a Claude task merely
   to unblock the research program.

## Adoption stop conditions

Stop rather than adapt around the candidate when any of these remain true at a
future execution gate:

- permission bypass cannot be disabled;
- disposable-root or protected-root exclusion cannot be proved;
- the mutation journal or rollback receipt is missing;
- parent-derived route receipts cannot be observed;
- cross-process resume cannot fail closed; or
- candidate core tests do not cover the integrated path.

## Evidence and acceptance boundary

This design proves only a source-bound responsibility classification and phased
decision boundary. It proves no adapter implementation, upstream acceptance,
candidate execution, permission safety, rollback, crash resume, Windows
portability, behavior, value, residual gap, or production readiness. The
program inventory remains 46 verified, 15 partial, and zero planned criteria.

The next gate needs a new owner choice between an upstream proposal package and
a pure zero-model adapter-contract PoC against a fake candidate. Neither choice
would authorize candidate execution or model dispatch.
