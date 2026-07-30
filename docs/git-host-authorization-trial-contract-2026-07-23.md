# Git Host Authorization Trial Contract — 2026-07-23

## Decision

Reuse the existing read-only snapshot, 32 deterministic topology fixtures, and
native disposable Git lifecycle. Do not build a Git manager and do not treat a
Git interception Hook as branch/worktree topology judgment.

The next live step is a bounded host authorization trial against a separately
authorized repository target. It is not authorized by this document.

## Independent authorization phases

### Preflight

Bind the absolute repository/worktree path, complete read-only snapshot, exact
dirty-path ownership, task type, and whether the task depends on current dirty
state. Unknown ownership or incomplete truth stops before mutation. Do not
stash, reset, or restore.

### Create

Creation needs its own authorization and native host approval. Bind the exact
base SHA, topology, branch name, absolute worktree path, and collision check.
After denial or command failure, only reobserve. Do not silently change the
command, retry, or clean up a partial state.

### Merge

Create authorization does not authorize merge. A merge requires a separate
decision, exact source/target SHAs, both sides clean, verification evidence,
fast-forward reachability, and native host approval. Only `--ff-only` is in the
current safe subset. Dirty, non-fast-forward, conflict, or denied states stop
for a human decision; no automatic rebase or conflict resolution follows.

### Cleanup

Create or merge authorization does not authorize cleanup. Bind the exact
objects, delivered/disposable state, clean worktree, merged branch, and
post-cleanup commit reachability. Only non-force worktree removal and safe
merged branch deletion are in scope. Missing evidence retains every target; no
force removal, force deletion, or broad prune follows.

### Recovery

Failure alone grants no recovery-write authority. Record before/after snapshots,
refs, worktree state, dirty bytes, and path/process ownership. A state that can
be reconstructed is not the same as a completed recovery. Any recovery write
needs the original authorization or a new one.

## Evidence boundary

The current disposable lifecycle does not prove safe creation, approval denial,
merge, or cleanup in a bound user repository. It also does not prove crash,
interruption, concurrent-change recovery, remote freshness, CI success,
cross-host parity, or live weak-Agent adherence.
