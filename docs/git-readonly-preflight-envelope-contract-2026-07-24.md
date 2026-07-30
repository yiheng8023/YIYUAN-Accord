# Git read-only preflight envelope

Date: 2026-07-24
Status: local read-only envelope builder; no approval or creation trial
Machine record: [`../registry/git-readonly-preflight-envelope-contract-2026-07-24.json`](../registry/git-readonly-preflight-envelope-contract-2026-07-24.json)

`GIT-READONLY-PREFLIGHT-ENVELOPE-01` reuses the existing Git observer and takes
exactly two observations. The Python builder emits its envelope JSON to stdout.
It does not choose a topology, create a branch/worktree, fetch, retry, prompt
for approval, or issue a Git recovery/topology mutation. The underlying Git
inspection may refresh internal metadata such as index stat-cache fields, so
this contract does not prove filesystem zero-write behavior.

The envelope retains raw porcelain entries so rename/copy paths are not
silently flattened. Every parsed dirty path receives `ownerState: unknown`.
This is intentional: the non-recovery observer can establish that a path is
dirty, not who owns it or whether a new task depends on it. A dirty envelope
therefore stops as `preflight-observed-dirty-ownership-unbound`.

Each observation records a run-bound sequence (`1` then `2`), exact event ID,
RFC3339 start and completion time, and canonical digest immediately around the
observer call. The first completion cannot be later than the second start.
Snapshots must be exactly equal. A difference returns `blocked-concurrent-drift`;
it does not trigger retry or recovery.

The validator recomputes every dirty path's raw porcelain evidence, including
rename/copy, whitespace, and Unicode paths. All ownership stays `unknown`.
The three proof counters are digest-bound and strictly false. Freshness is only
`none` or `local-ref-only`, must equal `facts.remoteClaim`, and requires
`networkRefreshObserved: false`; a local tracking ref is not live remote
freshness.

Passing tests establish only the current observer/envelope behavior in
temporary repositories and injected drift examples. They do not prove dirty
ownership, a host approval dialog or denial, creation safety, recovery, remote
freshness, filesystem zero-write behavior, or cross-host parity.
`writeAttempted: false` means that this builder attempted no explicit
recovery/topology write command; it is not a filesystem-write monitor. The
remaining claims stay behind a separately authorized bounded create-or-denial
trial.
