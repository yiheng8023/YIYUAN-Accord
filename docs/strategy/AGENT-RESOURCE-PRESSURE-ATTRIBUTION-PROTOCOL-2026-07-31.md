# Agent Resource-Pressure Attribution Protocol

Date: 2026-07-31

Status: offline synthetic contract; live host attribution and actuation not
tested

## Purpose

The desired product behavior is not a dashboard that makes the user operate
threads, workers, MCP sessions, or processes manually. The Agent should judge
the workload, observe host state, choose the smallest safe scheduling or
release action within existing authority, verify the result, and retain
cleanup debt. User input is reserved for a real permission, trust, cost,
shared-ownership, destructive, or host-observability boundary.

This protocol supplies the missing attribution and autonomy-decision layer. It
reuses:

- the existing context-pressure advisory for context and handoff decisions;
- the existing MCP task-lifecycle contract for leases, reference counts,
  task-end exit, duplicate identity, recovery, and resource controls;
- the reviewed host, gateway, scoped-session, worker, lease, stale-resource,
  durable-recovery, and observability landscape.

It does not implement another supervisor, scheduler, Hook, MCP gateway, or
runtime controller.

## Resource objects must remain distinct

"Zombie thread" is useful user language for a symptom, but it is not one
runtime state. A trial must distinguish:

| Resource object | Examples of identity and evidence |
| --- | --- |
| context | thread/turn identity, context or tool-result size, compression event |
| active turn | turn identity, start/end/cancel event |
| loaded thread | host thread identity plus observed loaded/unloaded state |
| persisted thread | durable record identity; persistence alone is not live load |
| subagent or worker | parent task, worker identity, start/end/cancel state |
| MCP connection | client/server/session identity and connection lifecycle |
| MCP subscription | subscriber and connection identity, acquire/release state |
| child process | PID plus executable/start identity and exit observation |
| host cache or renderer | host-owned cache/render identity and bounded metric |

A persisted thread count alone does not prove resource pressure. Task
completion does not prove resource release. An `unsubscribed` response does
not prove process exit. A process disappearance does not prove that context,
connections, workers, or host cache were reclaimed.

## Evidence order

The evaluator enforces this order:

1. Bind the scenario, exact host profile, and same-workload profile.
2. Record exact resource identities, owners or leases, and distinct lifecycle
   states.
3. Declare what the host exposes and what remains opaque.
4. Capture bounded time-series metrics and lifecycle inventory.
5. Repeat at least three times with an idle control, concurrent arm,
   cancellation arm, and release-latency observation.
6. Attribute pressure only when the candidate resource delta repeats and
   material confounders are controlled.
7. Attribute release only to a bound action with pre/post state, an action
   receipt, an observed release, and no shared-owner confounder.
8. Decide whether the Agent may act autonomously under existing authority.
9. Verify the observed outcome and retain cleanup debt.

Metric classes are host-dependent. They can include context size, CPU, memory,
process or handle counts, connection/subscription/worker counts, loaded-thread
count, and host cache size. Missing host metrics must be declared; heuristics
must not masquerade as telemetry.

## Bounded autonomy decision

An Agent action is only eligible for autonomous execution when:

- pressure attribution is eligible for the bound scenario;
- the action is already inside existing authority;
- the host exposes a real actuator;
- the action is reversible and has a bound verification surface;
- it does not need new permission or trust;
- it does not conflict with another owner;
- it is not destructive and does not add meaningful cost.

If those conditions hold, asking the user to operate the mechanism would shift
the learning and orchestration burden back to them. The Agent should act and
verify.

If a new permission, trust boundary, shared-owner conflict, destructive scope,
meaningful cost, or unverifiable action appears, the decision returns to the
user. If the host cannot actuate the state, the outcome is advisory-only, not
fabricated automation.

## Deterministic falsification corpus

The 26 offline fixtures cover:

- complete measurement, pressure attribution, release attribution, and safe
  autonomous-action eligibility;
- non-synthetic, live-proof, runtime-actuation, and self-authored-gap claim
  rejection;
- unbound or unpinned trials;
- merged "zombie thread" state, missing identity/owner/state separation, and
  insufficient observability;
- missing time series, repeats, and idle control;
- persisted-thread count promoted to a pressure cause;
- task completion promoted to release;
- release without an action receipt;
- new permission, shared ownership, unavailable actuation, and missing
  verification boundaries.

These are mechanism tests only. They do not prove that a current Codex,
ChatGPT, Claude, Trae, or other host exposes the required state or actuator.

## Authority and claim boundary

This protocol authorizes no live host read, process inspection, thread or
worker mutation, MCP mutation, Hook or global-configuration change, model
dispatch, installation, third-party execution, or controller implementation.

It does not prove:

- that zombie threads are the main cause of resource pressure;
- live host causation or resource savings;
- actual release or recovery;
- cross-host parity;
- weak-Agent acceptance;
- a residual gap requiring a self-authored controller.

The next gate is a separately authorized read-only same-workload observation
with exact identities, three repeats, idle and concurrent controls,
cancellation, bounded metrics, and release-latency evidence.
