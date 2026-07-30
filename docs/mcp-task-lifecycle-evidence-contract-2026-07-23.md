# MCP task lifecycle offline evidence contract

Date: 2026-07-23
Status: synthetic offline decision contract only
Machine record: [`../registry/mcp-task-lifecycle-evidence-contract-2026-07-23.json`](../registry/mcp-task-lifecycle-evidence-contract-2026-07-23.json)

## Purpose and boundary

This is a deterministic classifier for the evidence required before asserting
task-scoped MCP lifecycle behavior. It does not start a host or MCP server,
read host/process state, alter configuration, access accounts, or run a weak
Agent. Every output has `countsAsLiveHostProof=false` and
`countsAsWeakAgentAcceptance=false`.

Synthetic records can reject premature claims and show that a proposed
evidence packet is structurally complete. They cannot prove live lease or
reference-count correctness, task-end exit, duplicate freedom, crash recovery,
or resource benefit.

The accepted operating policy is subtractive: keep MCPs off unless the current
bounded task or phase needs them, activate only the smallest relevant set, and
request release at task or phase end. Re-evaluate at task entry, phase changes,
task end, and failures. This policy does not prove that a host can perform
same-session actuation. Until that is observed, use a startup/new-thread profile
or documented native idle timeout as the visible fallback.

## Required evidence by dimension

| Dimension | Minimum structural evidence | Still not proved offline |
| --- | --- | --- |
| Lease | exact task identity; acquire/release events plus an evaluated multi-task event sequence with validated order | live ownership and release |
| Reference count | exact identity; evaluated overlapping multi-task acquire/release sequence; underflow/double-release cases; terminal zero | concurrent host correctness |
| Task-end exit | task-end, final release, zero reference count, and exact exit in that order | task-end-triggered process release |
| Duplicate identity | exact MCP identity; concurrent instance window; duplicate attempt and collision outcome | duplicate freedom in a host |
| Crash recovery | named fault class; pre/post exact identities; same-thread outcome; bounded fallback | automatic, same-thread, or universal recovery |
| Resource control | at least two trials; baseline/post state; bounded metric and sample window; control workload | stable resource savings or idle release |
| Same-session switching | exact same-thread identity; baseline/post direct-call pair; an active turn between calls; a bound refresh evidence packet | live same-thread actuation or reload causality |

The classifier fails closed when a live/weak-Agent claim, non-synthetic mode,
host/MCP start, or live-state read appears in the packet. Its event-sequence
evaluator rejects duplicate acquisition, unknown/double/cross-task release,
server release while another lease remains, leaked leases, missing final
server release, and traces without overlapping tasks. The valid synthetic sequence
includes a nested task and a cancellation, then releases the server only after
the final lease. A fully populated synthetic fixture remains
`synthetic-lifecycle-contract-complete-live-claims-unproven`.

Twenty-two fixtures now cover the original dimension gates plus concrete
multi-task lease/reference-count failures. They are a model-level falsifier,
not a runtime lease manager, dynamic switch, or process-release proof.

## Falsifiable next gate

Only a separately authorized, concrete workload may move to live-host testing.
That trial must identify exact task and MCP instances, repeat observations,
capture bounded resource measurements, and declare a fallback before any
lifecycle claim. It must not treat this contract or its unit tests as proof of
dynamic enable/disable, task-end release, a lease manager, or a resource gain.
