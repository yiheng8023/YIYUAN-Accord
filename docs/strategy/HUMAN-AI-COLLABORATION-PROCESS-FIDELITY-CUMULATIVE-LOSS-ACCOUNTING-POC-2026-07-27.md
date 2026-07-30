# Process-Fidelity Cumulative Loss Accounting PoC

Date: 2026-07-27

Status: zero Agent, zero dispatch, additive accounting mechanism

## Result

The Harness now has a parent-recomputed, deduplicated cumulative-loss ledger
for a valid chained-transform capture. It measures, at each scored semantic
state:

- losses that are new relative to the previous state;
- losses carried across consecutive states;
- losses recovered since the previous state;
- first-seen and reintroduced losses;
- the union of unique losses, weighted only once;
- the peak simultaneously active loss weight;
- the first stage where an optional cumulative budget is strictly exceeded.

The frozen chained-transform evaluator, trace schema, protocol, and retained
audit files were not rewritten. The new analysis is added inside the already
open `processLedger` object only after the frozen evaluator accepts the raw
capture. Agent-reported metrics remain ineligible.

The injected calibration has a loss weight of 6 at the parent mutation, carries
the same weight through hop 2, and recovers it at hop 3. Its cumulative unique
weight remains 6 rather than being double-counted as 12 or erased back to zero.
The control remains zero. The budget result is advisory and does not change the
existing `processAcceptancePass`.

## Evidence boundary

The recovery envelope is excluded from semantic-state accounting because it
contains both predecessor and source-anchor material. Counting it as a normal
state would manufacture a misleading loss or recovery transition.

This is zero Agent, zero dispatch synthetic mechanism evidence. It does not
prove live process fidelity, accountable human input or terminal review edges,
software-lifecycle coverage, compression or handoff behavior, cross-host
portability, candidate Skill value, or a residual gap requiring self-authored
runtime control. The program acceptance remains `partial`.

The mechanism advances only the accounting portion of
`subgate.process-fidelity-boundary-and-cumulative-coverage`. The remaining live
cross-boundary, lifecycle, human-burden, and opaque-host requirements stay open.
