# Codex app-server 0.145.0 MCP thread-unsubscribe release attribution

The machine evidence is
[`registry/mcp-app-server-0.145.0-thread-unsubscribe-release-attribution-evidence-2026-07-27.json`](../registry/mcp-app-server-0.145.0-thread-unsubscribe-release-attribution-evidence-2026-07-27.json).

## Question

After the only client subscription is removed with `thread/unsubscribe`, does
one already-loaded local stdio MCP runtime release within five seconds while
app-server remains alive?

This is not a synonym for task end. The stable `0.145.0` response status
`unsubscribed` describes the subscription relationship, not thread closure or
MCP process release.

## Paired attribution design

Each of three formal repetitions used two fresh, independent app-servers,
Codex homes, ephemeral threads, and exact Sentinel instances:

- the unsubscribe arm sent exactly one `thread/unsubscribe`;
- the subscribed control arm sent no host request.

A shared monotonic barrier opened both five-second windows concurrently.
Every arm sampled the exact Sentinel PID, creation time, image, parent PID,
app-server liveness, and Sentinel event log at 0.5-second intervals. Reload,
config writes, new threads, tool calls, model turns, teardown, cleanup, and PID
signals were forbidden during the windows. The complete method list was
derived from a timestamped request ledger rather than a manually asserted
action list.

The one-second `calibration-01.json` run is excluded. Only
`evidence-01.json` through `evidence-03.json` are formal evidence. The
pre-registered decision rule required all three valid pairs to have the same
decisive result; mixed results would be non-reproducible, not a majority vote.

## Observation

All three formal pairs produced the same bounded result:

- all three unsubscribe requests returned `unsubscribed`;
- all three unsubscribe arms retained the exact loaded runtime;
- all three subscribed controls retained their exact runtime;
- all 66 process samples matched their six independent baseline identities;
- no exact Sentinel stop event occurred in any attribution window;
- all six post-window calls returned the same PID and instance;
- all six app-servers shut down gracefully and all six Sentinel cleanups were
  verified without a PID signal.

Cross-arm action skew was below `0.06 ms` in every formal pair, and the largest
sample skew was below `0.86 ms`.

Every app-server also logged an unauthenticated external network attempt. The
harness sent no `turn/start` and records no model request, but this evidence
does not claim zero network traffic.

## Boundary

For this Windows host, Codex app-server `0.145.0`, local Sentinel, and
five-second window, `thread/unsubscribe` was not an observed immediate-release
mechanism. This reproduces the stable source-level expectation that removing
the last subscription does not immediately unload the thread; the separately
observed approximately 30-minute idle fallback remains a different mechanism.

This does not prove that unsubscribe can never precede release, that
unsubscribe is task end, that arbitrary MCPs behave identically, or that
same-thread hot enable/disable, leases, reference counts, stable resource
savings, crash recovery, cross-host parity, or a residual need for a
self-authored controller exists.

The next bounded gap is overlapping task or subscription ownership and final
release semantics. It remains separate from resource-benefit measurement and
from any implementation decision.
