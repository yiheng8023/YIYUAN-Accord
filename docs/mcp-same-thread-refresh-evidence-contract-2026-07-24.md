# MCP Same-Thread Refresh Evidence Contract — 2026-07-24

Status: verified offline parent-event adapter; no live actuation
Machine record:
[`../registry/mcp-same-thread-refresh-evidence-contract-2026-07-24.json`](../registry/mcp-same-thread-refresh-evidence-contract-2026-07-24.json)

## Purpose

This contract fills the narrow MCP-03 gap between an offline task/selection
skeleton and a future host trial. It parses already-captured parent events. It
does not start Codex, open a thread, call an MCP, change configuration, stop a
process, or read account data.

The sole runtime oracle is an exact direct-tool-call transition on the same
thread after an active turn. `mcpServerStatus/list` is diagnostic-only. An
empty accepted `config/mcpServer/reload` response proves only that the request
was accepted. Neither one proves runtime actuation.

## Evidence sequence

A record must bind the exact selection packet and lifecycle skeleton whose only
planned dimension is `sameSessionSwitching`. It then preserves this order:

1. diagnostic pre-status;
2. baseline direct tool call with runtime instance identity;
3. a one-key disposable configuration delta;
4. reload request;
5. accepted reload response;
6. a completed active turn on the same thread;
7. post-turn direct call on that same thread;
8. diagnostic post-status;
9. exact-byte configuration restore.

Every event carries a strictly increasing sequence/time, the same thread ID,
an evidence-source class, and a SHA-256 digest recomputed from its captured raw
UTF-8 bytes. The host binding includes exact version, protocol-schema digest,
adapter, app-server instance, PID, and creation time. The target binds one
selected MCP source/revision/digest and one semantic config key.

## Falsifiers

The twelve synthetic fixtures reject:

- a lifecycle skeleton without the `sameSessionSwitching` dimension;
- missing mutation or active-turn authority;
- reload acceptance without an active turn;
- status change while the same-thread direct call remains on the old outcome;
- a post-call made on a new thread;
- config drift beyond the one target key or non-exact restoration;
- no direct-call transition after the active turn;
- PID disappearance without exact ownership and causation;
- Agent self-report substituted for parent event bytes;
- any task-end release or broader lifecycle claim promotion.

A structurally valid synthetic envelope returns
`evidence-contract-ready-not-live-host-proved`. It proves no live switching.
Even a future observed transition remains single-host evidence with release
unknown. Reload is not credited as the sole cause because the active turn is a
recorded common condition.

## Next gate

The next gate requires separate authorization for a disposable host/config
trial, its active turn, and exact-byte restoration. It must not read or copy
the user's live config, authentication, or secrets. Old-runtime release,
task-end release, lease/reference count, resource benefit, and Desktop parity
remain separate experiments.
