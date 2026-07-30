# Process-Fidelity Chained-Transform Dispatch Ledger Contract

Date: 2026-07-27

Status: **same-host one-shot ledger validated; live dispatch stopped**

## Outcome

The process-fidelity calibration now has a narrow, process-specific
reservation ledger. It does not introduce another general capability manager.
It reuses the repository's existing exclusive file-lock, canonical-hash, and
event-hash-chain primitives.

Two independent Python processes contending for the same authorization
produced exactly one accepted reservation and one rejection. The ledger also
failed closed on duplicate authorization, run cell, authority nonce, dispatch
nonce, evidence root, out-of-order hops, repeated dispatch, invalid terminal
evidence, hash corruption, and a non-terminated JSONL tail.

## One-shot state boundary

Reservation consumes the authorization and all three hop nonces. Each hop may
start once, in protocol order, and only after the preceding hop has a
`completed-valid` terminal receipt. A failed or ambiguous attempt blocks the
remaining run.

No automatic retry, replacement, or release is allowed. An ambiguous terminal
may only be reconciled as `retain-consumed-no-retry`; reconciliation cannot
make the run dispatchable again.

The ledger never promotes a run into the formal cohort. Native receipt
validation, process-fidelity scoring, and acceptance remain separate gates.

## Zero-dispatch preflight

The advisory preflight revalidates the immutable dispatch envelope, authority
window, host-route freshness, and collision classes without writing the
ledger. It reports:

- `modelCalled=false`
- `modelDispatchCount=0`
- `ledgerMutationPerformed=false`
- `advisoryOnly=true`
- `liveDispatchReady=false`

Because an advisory read can race, only the locked append performed by
`reserve` can consume an authorization. The atomic hop-start append is the
one-shot permit for the following model dispatch.

## Evidence boundary

The cross-process result applies to the current same-host filesystem and the
reused lock primitive. Network-filesystem atomicity, cross-host coordination,
and power-loss durability are not proved. Flush and `fsync` are implemented,
and a corrupt or partial tail is rejected rather than truncated, but this is
not a power-loss experiment.

No model was called. No current-task live authority or fresh live route was
bound. Provider execution model and effort remain `unknown`. The formal
process cohort remains at zero, and end-to-end process fidelity remains
`partial`.

The next bounded live step still requires exact user authority for one run
cell, a fresh host-reported Spark/low route observation, atomic reservation,
and at most three no-tool hops with no fallback, retry, replacement, or
automatic cohort acceptance.
