# Codex app-server 0.145.0 direct MCP tool-call evidence

Date: 2026-07-23
Status: `observed-single-host-direct-local-tool-call-multi-instance-release-gap`

## Outcome

Codex CLI `0.145.0` exposes the stable `mcpServer/tool/call` method, and an
isolated Windows app-server completed a direct local MCP tool call without a
model turn, account login, copied user configuration, or copied Plugin state.
This is a bounded positive result for the direct-call surface only.

The same probe also produced a material negative lifecycle result. One
configured Sentinel was represented by two Sentinel instances: a
thread-bound tool-call instance and a status/resource-discovery instance, with
both roles classified from their observed MCP methods. After
`thread/unsubscribe`, closing the launcher wrapper timed out; the wrapper
received a kill signal, but the actual app-server PID and termination were not
independently observed. The status/resource-discovery PID was still present at
the immediate wrapper-shutdown observation. The runner sent a PID-only cleanup
signal and the process was absent at a later read-only check, but its process
identity was not revalidated before the signal and its exact exit latency is
unknown. This is not exact-instance cleanup evidence.

Therefore the result does not prove a single runtime instance, immediate
task-end release, deterministic shutdown release, or task-scoped lifecycle
control.

## Official and schema evidence

The reviewed official tag is `rust-v0.145.0` at commit
`25af12f7e61572b0bc18ddb1008be543b91519b0`.

- Official app-server documentation:
  <https://github.com/openai/codex/blob/rust-v0.145.0/codex-rs/app-server/README.md>
- Official release:
  <https://github.com/openai/codex/releases/tag/rust-v0.145.0>

The stable schema was generated without the experimental flag under
`C:\tmp\codex-app-server-schema-0.145.0-20260723`. It requires
`threadId`, `server`, and `tool` for `mcpServer/tool/call`; `arguments` and
`_meta` are optional. The pinned hashes are in
`registry/mcp-app-server-0.145.0-direct-tool-call-evidence-2026-07-23.json`.

Official source review adds the following semantic boundaries:

- `mcpServer/tool/call` loads the named thread and directly calls the MCP tool;
  it need not start a model turn, but it still requires a thread;
- `config/mcpServer/reload` queues a refresh for loaded threads, so an empty
  response proves acceptance rather than completed actuation or process
  release;
- the last `thread/unsubscribe` does not immediately unload the thread;
- unload requires both no subscribers and no activity for 30 minutes;
- `thread/closed` follows successful thread shutdown and manager removal, but
  does not by itself prove that every MCP child process exited.

The 30-minute idle unload was not executed in this PoC.

## Primary isolated run

The primary retained normalized result is:

`C:\tmp\agent-autonomy-mcp-tool-call-0.145.0-20260723-run05\probe-result.json`

Its SHA-256 is
`36710711b35aec0d92fe7b7326a6f3e5274ac785f586233d1201b12c5a592d2a`.

Observed facts:

- ephemeral read-only thread:
  `019f8e2e-19cc-71e3-962e-0dd740446b83`;
- no `turn/start`;
- status listed one configured Sentinel with two tools and no resources;
- direct `identity` call succeeded on PID `43368`, instance
  `4eafdc24-723a-4400-9637-5bc6736d5f74`;
- two Sentinel instances existed, with auxiliary PID `40724`;
- `thread/unsubscribe` returned `unsubscribed`;
- launcher-wrapper graceful shutdown timed out and the wrapper received a kill
  signal; actual app-server termination was not independently established;
- auxiliary PID `40724` remained at the immediate shutdown observation;
- a PID-only cleanup signal was used without revalidating process identity, and
  a later read-only PID check reported it absent;
- the isolated config hash was identical before and after;
- no auth state was produced;
- Plugins, remote plugin discovery, Apps, and plugin sharing were disabled.

No external URL attempt appeared in application stderr during the primary run.
This does not prove network traffic was absent because no packet-level monitor
was used.

Five local attempts completed the direct MCP tool call, and each event log
showed two Sentinel instances. All five event logs are pinned by SHA-256 and
record their two method-classified instance roles in the registry. This
repetition justifies a warning for this specific app-server path; it is not a
universal topology claim for Codex, Desktop, Plugins, other MCP transports, or
other hosts.

## Claim boundary

Supported on this host and version:

- the stable schema contains `mcpServer/tool/call`;
- a direct local MCP tool call works through an ephemeral app-server thread;
- this call path can run without a model turn or account login;
- status discovery and direct invocation may create different Sentinel
  instances for one configured server.

Not proved:

- same-thread hot enable/disable; same-thread hot enable/disable remains
  unproven;
- reload completion, tool-surface transition, or old-process release;
- a public task-level lease or reference-count API;
- task-end immediate release or the documented 30-minute idle unload;
- crash recovery or prior-state restoration;
- stable resource savings;
- Desktop, Plugin MCP, Claude, or other-host equivalence;
- absence of network traffic.

## Next falsifiable gate

Use a new isolated home and the same local Sentinel to test this sequence:

1. establish a direct-call and multi-instance baseline;
2. change only the isolated config to disable the Sentinel;
3. call reload and verify status/tool/PID deltas rather than trusting `{}`;
4. compare the existing thread with a newly created thread;
5. re-enable and verify a third thread;
6. restore the isolated config and account for every owned process identity.

This next gate may establish version-specific enable/disable behavior. It must
not be described as task-level leases, idle release, crash recovery, or
resource benefit unless those separate observations are performed.

The temporary schema and five probe roots are retained as bounded process
evidence. They are cleanup debt, not product payloads, and this record does not
authorize deletion.
