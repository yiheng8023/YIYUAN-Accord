# Codex App Server 0.145.0 Multi-Connection Subscription Preflight

Date: 2026-07-27
Host: Windows, `codex-cli 0.145.0`
Status: three protocol-valid negative preflight repetitions

## Question

Can one Codex app-server process expose two independently releasable,
connection-scoped subscriptions to one already-loaded local MCP runtime without
a model turn, fabricated host state, a second app-server, or a third-party
WebSocket dependency?

This question is deliberately narrower than task leases, reference counts,
task-end release, or resource savings. Those broader claims require the second
subscription precondition to be observed first.

## Pinned host semantics

The exact `rust-v0.145.0` source is bound at commit
`25af12f7e61572b0bc18ddb1008be543b91519b0`.

- [`thread_state.rs`](https://github.com/openai/codex/blob/rust-v0.145.0/codex-rs/app-server/src/thread_state.rs)
  stores subscribed connections in a `HashSet<ConnectionId>` and removes only
  the requesting connection on unsubscribe.
- [`thread_lifecycle.rs`](https://github.com/openai/codex/blob/rust-v0.145.0/codex-rs/app-server/src/request_processors/thread_lifecycle.rs)
  attempts listener attachment for a concrete connection and separately defines
  the 30-minute thread unloading delay.
- [`thread_processor.rs`](https://github.com/openai/codex/blob/rust-v0.145.0/codex-rs/app-server/src/request_processors/thread_processor.rs)
  reports `unsubscribed` or `notSubscribed` for the requesting connection, and
  running-thread resume still reads stored thread metadata.
- [`lib.rs`](https://github.com/openai/codex/blob/rust-v0.145.0/codex-rs/app-server/src/lib.rs)
  exposes WebSocket as a multi-connection transport and labels thread-created
  listener attachment to initialized connections as best-effort.

Source hashes, blob identities, stable schema hashes, and the exact probe,
bridge, and Sentinel hashes are recorded in the registry evidence.

## Formal design

Each of three sequential runs used:

- one fresh explicit `CODEX_HOME`;
- one native `codex.exe app-server` bound only to loopback WebSocket;
- two separate Node processes, each using Node's built-in `WebSocket`;
- a read-only `config/read` response on B after its `initialized` notification
  and before A's `thread/start`;
- one non-ephemeral thread and one exact local Sentinel child;
- direct identity calls from A and B before A unsubscribed;
- a second B call after A unsubscribed; and
- evidence capture before bridge closure, App Server termination, or Sentinel
  cleanup.

No `turn/start` request was sent and no turn-start notification was observed.
Plugins and Apps were disabled in the isolated host. App Server nevertheless
logged one external unauthenticated attempt in every run, so zero model turns
must not be restated as zero network traffic.

## Observation

All three runs were protocol-valid and had the same bounded result:

| Surface | Run 01 | Run 02 | Run 03 |
| --- | --- | --- | --- |
| Distinct WebSocket bridges | yes | yes | yes |
| Same thread and exact Sentinel for A/B calls | yes | yes | yes |
| A unsubscribe sequence | `unsubscribed`, `notSubscribed` | same | same |
| B unsubscribe sequence | `notSubscribed`, `notSubscribed` | same | same |
| Model-turn requests / notifications | `0 / 0` | `0 / 0` | `0 / 0` |
| App Server alive before harness shutdown | yes | yes | yes |
| Cleanup verified | yes | yes | yes |
| External attempt logged | yes | yes | yes |

Therefore the tested best-effort thread-created path did not expose B as an
independently releasable second subscription, even though B could directly call
the same loaded Sentinel runtime.

One excluded calibration tested `thread/resume`. A zero-turn `thread/start`
advertised a rollout path, but no rollout file materialized within the bounded
two-second calibration window, so resume could not acquire the second
subscription without adding a model turn or fabricating stored state.

## Decision

The overlapping-owner precondition is not satisfied. The final-observed-owner
release pair must not run, because doing so would relabel a callable second
connection as a second subscription owner.

The existing 30-minute no-subscriber idle-unload observation remains separate.
This preflight neither strengthens nor invalidates it.

Re-open the overlap/final-release experiment only when:

1. the tested host/version exposes a reproducible second subscription
   acquisition path without fabricated state; or
2. a separate decision authorizes and justifies a model-turn trial that creates
   a real persisted rollout.

No result here proves a residual need for a self-authored controller.

## Claim boundary

This evidence does not prove:

- thread-created auto-attach can never work;
- resume fails for persisted threads that already have real rollout history;
- a public subscriber-count or lease API exists;
- internal reference counting is correct or incorrect;
- unsubscribe means task end;
- final release, resource savings, arbitrary-MCP behavior, or crash recovery;
- parity across hosts or versions;
- zero network traffic; or
- production readiness or authority to implement a lifecycle controller.
