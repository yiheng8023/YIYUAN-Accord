# MCP thread-unsubscribe release attribution audit

This directory preserves raw paired Codex app-server `0.145.0` host evidence.

## Pre-registered formal set

- `calibration-01.json` uses a one-second window and is excluded.
- `evidence-01.json` through `evidence-03.json` are the complete formal set.
- Every formal repetition uses two fresh, independent app-servers, Codex homes,
  ephemeral threads, and exact Sentinel instances.
- A shared monotonic barrier opens concurrent five-second windows. The
  unsubscribe arm sends only `thread/unsubscribe`; the subscribed control arm
  sends no host request. Both arms otherwise perform only read-only exact
  process, app-server liveness, and Sentinel event sampling.
- Reload, config writes, new threads, tool calls, model turns, teardown,
  cleanup, and PID signals are forbidden during the attribution windows.
- Only three valid pairs with the same decisive pair classification support a
  repeated bounded conclusion. Mixed results are non-reproducible rather than a
  majority decision. A failed subscribed control makes its pair inconclusive.

`unsubscribed` proves only that the subscription relationship was removed. It
does not by itself prove thread closure, MCP release, task end, lease or
reference-count behavior, resource benefit, or a need for a self-authored
controller.

Raw reports bind the exact probe, Sentinel, helper dependencies, executable
version, request ledger, process identities, event records, isolation, network
claim boundary, and verified cleanup. The repository audit files remain
authoritative host evidence until a separate cleanup decision.
