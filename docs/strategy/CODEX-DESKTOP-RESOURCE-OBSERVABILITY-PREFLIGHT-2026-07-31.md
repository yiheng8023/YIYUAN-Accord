# Codex Desktop Resource Observability Preflight

Date: 2026-07-31

Status: live read-only single-host observation; owner attribution and actuation
blocked

## Outcome

The current Codex Desktop runtime exposes enough local process data to show a
material repeated-runtime footprint, but not enough ownership data to attribute
that footprint to a task, thread, lease, or completed lifecycle.

Three observer-excluded samples reported 118 Codex-runtime processes and 34 TCP
connections. Aggregate working set stayed near 6.39 GB and aggregate private
bytes near 4.33 GB. Working-set sums may double-count shared pages, and the
window was neither idle nor a controlled workload; these numbers are a live
inventory, not a resource-pressure causal result.

## Repeated startup cohorts

The process tree contained six near-identical startup cohorts. Each cohort had:

- one `node_repl` root;
- one Neo4j root;
- one Playwright root;
- one Context7 root;
- one CodeGraph root;
- four Node roots that could not be safely named without retaining raw
  machine-local command lines.

Together those repeated cohorts contained 114 processes, about 5.49 GB summed
working set, and about 3.58 GB summed private bytes.

| Runtime label | Root count | Process count | Working set bytes | Private bytes |
| --- | ---: | ---: | ---: | ---: |
| unclassified Node | 24 | 24 | 1,545,682,944 | 962,981,888 |
| Playwright | 6 | 24 | 1,279,348,736 | 1,016,119,296 |
| Context7 | 6 | 24 | 1,168,633,856 | 900,968,448 |
| CodeGraph | 6 | 24 | 982,384,640 | 472,805,376 |
| Neo4j | 6 | 12 | 450,027,520 | 208,887,808 |
| node_repl | 6 | 6 | 64,823,296 | 16,855,040 |

This proves repeated live runtime cohorts on this host at this moment. It does
not prove that six user threads own them, that a `notLoaded` task owns any of
them, or that the processes are leaked.

## Thread and MCP surfaces do not join

The visible task listing returned 20 Codex tasks in its bounded page: two
`active` and eighteen `notLoaded`. The current Harness project had one active
and one not-loaded task. The non-pinned result was truncated at the requested
limit, so it is not the full persisted-task inventory.

`codex mcp list` returned nine enabled configuration entries: seven local and
two remote. That status is configuration inventory, not loaded-runtime state.
The process tree could classify five repeated local runtime labels, while four
Node roots per cohort remained intentionally unclassified.

The available surfaces did not expose:

- a thread-to-process owner or lease;
- an MCP-instance-to-thread owner or lease;
- context size, compression, or compaction telemetry;
- task-completion, cancellation, archive, unsubscribe, or process-release
  receipts;
- a verified task-scoped reversible runtime actuator.

The current task had no attached app-terminal session.

## Official protocol and implementation correlation

The exact `rust-v0.146.0` Codex source tag resolves to commit
`e363b08c9175ac1cbe5893615dd2cb9ddf95043b`. Its app-server protocol already
defines several inputs that a resource governor would need:

- `thread/loaded/list` and `thread/status/changed`;
- `mcpServer/startupStatus/updated`, whose `threadId` identifies a
  thread-scoped MCP startup;
- `thread/tokenUsage/updated`, automatic compaction events, and
  `thread/compact/start`;
- thread-scoped background-terminal list, clean, and terminate methods.

The pinned implementation also contains explicit `McpConnectionManager`
shutdown and stdio child `kill_on_drop` behavior. OpenAI issue `#18881`, which
described a manager-replacement leak, is closed as completed. It is therefore
not eligible as the explanation for the six live cohorts merely because the
shape looks similar.

The broader risk is not imaginary: issues `#11324` and `#17832` remain open for
multi-task MCP memory growth and Playwright child retention. Issue `#35676`
also records that loaded-thread state still does not expose subscriber
presence. These upstream reports corroborate lifecycle risk; they do not prove
the cause of this host's snapshot.

The important residual boundary is therefore narrower than “Codex has no
resource primitives.” The official protocol has useful owner, telemetry, and
bounded-actuator inputs, while the current Desktop task surface did not expose
the loaded-thread list, MCP startup owner receipts, or subscriber presence.
Reusing or exposing those host primitives must precede any self-authored
controller design.

## Decision

The live process and configuration surfaces are useful, but they fail the
ownership and control conditions in the
[resource-pressure attribution protocol](AGENT-RESOURCE-PRESSURE-ATTRIBUTION-PROTOCOL-2026-07-31.md).
Therefore:

- pressure attribution is not eligible;
- release attribution is not eligible;
- autonomous action is not eligible;
- the evidence does not justify a self-authored controller.

No model turn, task creation/archive/deletion, MCP reload or configuration
change, process stop/restart, Hook change, Plugin/App change, or global
configuration mutation occurred. Raw command lines, credential values, task
titles, task bodies, and task summaries were not retained.

## Next gate

First inspect a current official or host-exposed ownership and release surface.
If none exists, the next experiment must be a separately authorized disposable
Desktop lifecycle trial with:

- exact pre/post process identities;
- one bounded task or runtime state transition;
- an explicit owner hypothesis;
- release latency and a receipt oracle;
- rollback and cleanup;
- no weak-model turn.

Until that gate is bound, killing processes, archiving tasks, toggling MCPs, or
adding a controller would be attribution-free intervention.
