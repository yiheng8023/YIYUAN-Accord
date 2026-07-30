# Process-Fidelity Chained-Transform Dispatch Gate Contract

Date: 2026-07-27
Status: offline contract validated; live dispatch stopped

## Result

The repository now has one fail-closed offline contract for a future live
chained-transform run. It binds one exact run cell, one time-bounded authority
document, the frozen protocol and v2 amendment, the exact Spark/low route, an
absent-or-empty repository-local audit destination, and three ordered
single-use hop authorizations.

The same module validates parent-derived native hop receipts against captured
client/server wire events. It recomputes persisted input, stage-contract, turn
input, output, event-log, receipt-lineage, and deterministic parent-transform
bindings. Agent-supplied route, receipt, hash, or metric claims are not trusted.

Ten deterministic tests currently cover requested-versus-observed route,
authority expiry, resealed run-cell drift, live-boundary promotion, per-hop
route drift, cross-thread reuse, parent-transform drift, artifact substitution,
missing terminal evidence, unknown receipt fields, and private-oracle leakage.

## Route truth boundary

Codex app-server 0.145.0 exposes the model, optional reasoning effort, provider,
and thread identity returned by `thread/start`. The contract names this
`host-reported-effective-thread-route`.

It does not relabel that surface as independent provider-backend execution
telemetry. Provider execution model and effort remain `unknown`. A requested
route, an Agent self-report, or a later correct artifact cannot fill that
telemetry gap.

## Why live remains stopped

An envelope with valid bytes is not yet an executable reservation. The current
contract deliberately keeps:

- `atomicReservationLedgerBound=false`;
- `liveDispatchReady=false`;
- formal cohort count at zero; and
- every live or acceptance claim false.

The validator itself starts no Codex process, sends no `thread/start` or
`turn/start`, calls no model, changes no configuration, and writes no evidence.
Even three structurally valid offline receipts remain ineligible for formal
live evidence because no atomic one-shot reservation has consumed the
authorization.

The next bounded result is a process-specific, append-only, atomically locked
reservation ledger with replay, partial-tail, duplicate nonce, conflicting
reservation, crash ambiguity, and manual-reconciliation fault tests. Only
after that ledger, a fresh zero-dispatch route preflight, and one exact
current-task user authority are all bound may a live calibration be considered.
No automatic retry or replacement is allowed.

Machine record:
`registry/human-ai-collaboration-process-fidelity-chained-transform-dispatch-gate-contract-2026-07-27.json`.
