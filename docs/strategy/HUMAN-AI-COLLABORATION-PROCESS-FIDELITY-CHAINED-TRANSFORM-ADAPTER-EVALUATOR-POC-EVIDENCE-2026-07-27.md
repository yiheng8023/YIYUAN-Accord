# Chained-Transform Sequential Artifact Adapter And Trace Evaluator PoC

Date: 2026-07-27

Status: zero Agent, zero dispatch, synthetic mechanism evidence

## Result

The repository now has a sequential artifact adapter that materializes the
three Agent-stage packets only after the preceding artifact is persisted. A
separate evaluator reopens the raw files and recomputes hashes, loss metrics,
detection validity, recovery validity, and the absolute/process ledgers from
the frozen source and parent-only oracle.

The PoC ran two scripted valid cases:

- clean control, with the source payload remaining sealed;
- one parent-injected authority omission, exact hop-2 detection, conditional
  source unsealing, and terminal restoration that retains the intermediate
  loss ledger.

It also classified six registered failures: predecessor-linkage mismatch,
duplicate edge order, opaque edge, raw-artifact hash mismatch, caller metric
supplementation, and invalid detection. Invalid detection stops before hop 3.

## Evidence boundary

The retained raw captures are under
`audits/process-fidelity-chained-transform-zero-dispatch-sequential-poc-2026-07-27/`.
This is a non-temporary repository-local evidence destination and must be
retained rather than treated as `.tmp` cleanup debt. The current files are
still uncommitted, so repository-local custody does not prove Git or remote
durability.

No Agent or model was called. `actualRouteObserved=false`,
`liveDispatchReady=false`, and the formal process cohort count remains zero.
The requested Spark route is not treated as an observed route.

## What this does not prove

This does not prove that a live weak Agent will produce a valid artifact,
detect the injected loss, recover from the source, or preserve process
fidelity. It does not compare Matt, Superpowers, CC Skills, or the self-authored
chain; it does not establish cross-host portability, automatic thread
behavior, or a residual gap requiring self-authored runtime control.

The next live step still needs a separate authority envelope, fresh per-hop
native route receipts, and an independently authorized dispatch. Any formal
cohort starts from zero; these calibration cases do not count as repetitions.
