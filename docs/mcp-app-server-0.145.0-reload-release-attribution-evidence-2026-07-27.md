# Codex app-server 0.145.0 MCP reload-release attribution

The machine evidence is
[`registry/mcp-app-server-0.145.0-reload-release-attribution-evidence-2026-07-27.json`](../registry/mcp-app-server-0.145.0-reload-release-attribution-evidence-2026-07-27.json).

## Question

When one already-loaded local stdio MCP is disabled in an isolated config and
`config/mcpServer/reload` returns, does reload itself release that exact runtime
while app-server and the original thread remain alive?

This is narrower than same-thread hot switching, task-end release, leases,
resource savings, crash recovery, or general MCP lifecycle control.

## Attribution design

The runner started no model turn. Each of three formal repetitions used a new
empty `CODEX_HOME`, a new app-server, an ephemeral read-only thread, and a new
Sentinel PID and instance. It copied no current authentication, user config, or
Plugin state.

After one baseline direct tool call, the runner:

1. atomically wrote the isolated config with the Sentinel disabled;
2. sent `config/mcpServer/reload`;
3. read the thread-scoped status projection;
4. spent five seconds only sampling the exact PID identity and Sentinel event
   log.

No new thread, unsubscribe, teardown, cleanup marker, or PID signal occurred in
the attribution window. The runner called the original thread only after the
window, then restored the exact config bytes and verified a new-thread control.

The first calibration inherited the previous probe identifier. Three later
runs predated raw-report self-binding. All four remain preserved and excluded;
only `evidence-01.json` through `evidence-03.json` count.

## Observation

All three formal repetitions produced the same bounded result:

- all 33 process samples matched the baseline PID, creation time, image, and
  parent PID;
- the attribution window contained zero stop events for the exact instance;
- the post-window same-thread call returned the same PID and instance;
- status listed the server but exposed an empty tool projection;
- the exact config was restored, the restored-new-thread control succeeded,
  app-server exited gracefully, and cleanup was verified.

Therefore Codex app-server `0.145.0` retained the already-loaded Sentinel across
the tested five-second reload window, while its status projection and loaded
runtime diverged. The empty reload response proves request acceptance, not
completed actuation or release.

Every repetition also logged an unauthenticated Responses websocket attempt
that returned HTTP 401. The harness sent no `turn/start` and records no model
request, but this evidence does not claim zero network traffic.

## Boundary

This falsifies use of reload as an observed immediate release mechanism for the
already-loaded Sentinel on this host/version/window. It does not prove that
reload can never release a runtime, that arbitrary MCPs behave identically, or
that task-end release, same-thread enable/disable, leases, reference counts,
stable resource savings, crash recovery, cross-host parity, or a residual need
for a self-authored controller exists.

The next named gap is task-end or thread-unsubscribe release attribution while
app-server remains alive; overlapping task leases remain a separate experiment.
