# Context–Git Snapshot Projection Contract

Date: 2026-07-27
Status: verified local mechanism; no live thread or model run

## Decision

Repository-anchored Context continuation now consumes the existing
`observe_git_snapshot.observe_repository` result. It no longer maintains a
second Git subprocess parser inside the Context packet builder.

This is a subtractive reliability change. One parent observation now supplies
branch or detached state, HEAD, upstream state, local-ref ahead/behind,
NUL-safe status tokens, both rename or copy paths, worktree paths, remotes, and
freshness. The Context layer only projects that result into its established
packet representation.

## Falsifiable behavior

The projection preserves:

- both NUL-delimited paths for rename and copy entries;
- detached HEAD without inventing a branch;
- multiple worktree paths, including paths with spaces;
- known local-ref ahead/behind counts;
- no-upstream as `aheadBehind=null`, never invented `origin/main` or `0/0`;
- `local-ref-only` as local refs without a network-refresh claim; and
- dirty ownership as unproved.

Live-remote freshness and unknown ahead/behind states are rejected rather than
flattened into a Context packet. A freshness check still compares the complete
packet repository-truth object with a newly observed object before dispatch.

Five projection controls and the existing Git, Context packet, handoff
freshness, read-only preflight, ablation, and pressure regressions pass. The
tests create only disposable Git repositories where topology setup is needed.
They do not create a Codex thread or call a model.

## Boundary

Logical Git observations before and after a test may match, but
`filesystemZeroWriteProved=false`: read-only Git commands can still refresh
internal metadata. Local tracking refs are not live remote truth.

This mechanism does not prove automatic thread creation, fresh-session
`handoff` invocation, receiver recovery, lossless handoff, atomic build/create
semantics, cross-host parity, dirty-path ownership, or weak-Agent adherence.
It does not justify a self-authored runtime controller.

Any later authorized creation must rebuild or revalidate the exact packet
inside its creation critical section. The shared observer reduces duplicate
interpretation edges; it does not remove the need for source, authority, host,
and receiver evidence.
