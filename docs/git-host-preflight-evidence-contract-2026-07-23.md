# Git host preflight, denial, and re-observation evidence contract

Date: 2026-07-23
Status: offline contract only; no bound-repository or host-approval trial
Machine record: [`../registry/git-host-preflight-evidence-contract-2026-07-23.json`](../registry/git-host-preflight-evidence-contract-2026-07-23.json)

## Purpose

This contract fills a narrow evidence gap left intentionally open by the Git
topology PoC: a recommendation is not evidence that a bound repository had a
complete preflight, that a native approval was denied, or that a command
failure was safely re-observed. It is independent from topology choice and
does not call `git`.

Every packet binds an absolute repository/worktree locator, canonical before
and after snapshots, distinct before/after observation IDs and timestamps, and
one ownership row for every dirty path. `statusEntries` and `dirtyPaths` must
be exact path-equivalent; known ahead/behind counts must be non-negative
integers, while unknown/not-applicable counts remain null. An ownership row is
`task-owned`, `other-owned`, or `unknown`, and carries an evidence reference.
Task-owned dirty state must be declared as required by the task. Unknown and
other-owned state both stop before mutation; equivalently, Unknown or
other-owned dirty state stops before mutation. Any attempted command while
either state exists is a hard failure. Neither state silently becomes topology
or mutation authority.

## Approval and failure boundary

Approval evidence is parent-observed. An Agent self-report or a topology
recommendation cannot prove approval. Approval and execution bind the same
action; execution also records its canonical command and matching SHA-256. In
a denial packet the command must be unattempted and the independently observed
post-snapshot must exactly equal the pre-snapshot.

After a nonzero command result, the only automatic action represented here is
re-observation. `reconstructable-state-observed` requires both snapshot drift
and an independent after event; it is not a synonym for a nonzero exit. The
result may be `unchanged`, `reconstructable-state-observed`, or
`recovery-write-needs-authorization`. None means recovery was completed. An
actual recovery write without separate authorization is a hard failure.

The top-level `packetSha256` covers observations, snapshots, ownership,
approval, execution, and recovery as one envelope. It detects internal drift
relative to the supplied synthetic packet; it is not a signature,
source-authentication proof, or live-host evidence.

## Offline fixtures

The 23 synthetic fixtures cover clean/task-owned/other-owned/unknown dirty
preflight, malformed locator or ownership evidence, invalid ahead/behind and
status/path binding, stale post-snapshots, denial with and without accidental
command execution, attempted commands while other-owned or unknown dirty state
exists, command/action/digest mismatch, independent re-observation, envelope
drift, and failure re-observation. They validate the contract shape only. They
do not prove a host dialog, a user-repository safety property, weak-Agent
adherence, or cross-host parity.

## Explicit non-goals

This is not a Git manager, command executor, approval UI emulator, automatic
retry/recovery mechanism, live remote freshness probe, crash/concurrency
test, or cleanup system. It does not create branches or worktrees, mutate a
repository, or reuse `evaluate_git_topology_trial.py` recommendations as
approval evidence.
