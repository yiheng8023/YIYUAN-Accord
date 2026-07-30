# Codex app-server 0.145.0 startup-profile evidence

Date: 2026-07-23
Host: Codex CLI app-server 0.145.0 on Windows
Status: observed two-repetition startup-profile direct-call boundary

## Outcome

Six isolated no-model-turn runs compared three configurations, each in a new
native app-server, empty `CODEX_HOME`, and ephemeral thread:

| Profile | Direct `identity` | Direct `hold` | Sentinel instances per run |
|---|---|---|---|
| full: `enabled=true` | success ×2 | success ×2 | 1, 1 |
| filtered: allow `identity,hold`, then deny `hold` | success ×2 | rejected as disabled ×2 | 1, 1 |
| disabled: `enabled=false` | unknown server ×2 | unknown server ×2 | 0, 0 |

This validates the official allow-then-deny filter semantics and complete
server disable for this host/version/Sentinel. Startup or new-thread profiles
are therefore an observed bounded fallback when the active MCP set must be
kept small.

It is not automatic task-scoped on-demand switching, same-thread hot
actuation, or reload completion.

## What this means for a subtractive MCP policy

- Tool filtering reduced the callable surface but still started one Sentinel in
  each filtered run.
- Complete disable prevented Sentinel startup in both disabled runs.
- Therefore filtering and disable solve different costs in this experiment:
  filtering can constrain the tool surface, while disable is the relevant
  startup control when the target cost is the server process itself.

This is not a universal ranking. Other MCP servers may have different process,
startup, connection, authentication, and resource behavior. The current
fallback is to select the smallest startup/new-thread profile for the task and
re-evaluate at phase boundaries.

## Timing and resource samples

| Profile | First direct-call latency | Sentinel working set |
|---|---|---|
| full | 828 ms, 502 ms | 20,287,488; 20,283,392 bytes |
| filtered | 570 ms, 513 ms | 20,135,936; 20,246,528 bytes |
| disabled | 332 ms, 338 ms rejection | no Sentinel |

Two runs are enough to reject a one-off functional accident, not to establish
a stable latency or resource benefit. The profiles were sequential rather
than randomized, and the disabled result does not measure every other
app-server or host cost.

## Isolation and cleanup

The probe copied no current config, auth, account, or Plugin state; called no
status discovery or reload method; and started no model turn. All six temporary
configs remained byte-equal. Each native app-server returned normally, all
bound Sentinel exact identities disappeared, and no owned-handle kill,
PID-only signal, process-name scan, or process-name termination was used.

No application-log external network attempt appeared in these six runs.
Because no packet monitor was used, absence of network traffic and credential
use are not claimed.

## Raw evidence

- root:
  `C:/Projects/agent-autonomy-harness/.tmp/mcp-startup-profiles-20260723-run01`
- normalized result: 109,764 bytes,
  SHA-256 `0c5ca93214fd67d0261081f29d1191adea412cfda62b0daa5bf294c2058136e9`
- machine record:
  `registry/mcp-app-server-0.145.0-startup-profile-evidence-2026-07-23.json`

The temporary root is retained as cleanup debt, not product payload.

## Claim boundary

This comparison does not establish:

- same-thread hot switching, reload completion, or automatic task-scoped
  on-demand switching;
- status/runtime equivalence;
- context/token reduction or stable latency/resource savings;
- that filtering can always replace disable, or disable always outperforms
  filtering;
- release of every server process, lease/refcount behavior, or crash recovery;
- absence of network or credential use;
- Desktop, Plugin MCP, Claude, or cross-host parity.

The next step is not a controller. Use startup/new-thread profiles as the
fallback, and test same-thread actuation only when a concrete workload cannot
tolerate that boundary.
