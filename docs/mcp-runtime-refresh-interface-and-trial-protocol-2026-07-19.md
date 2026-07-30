# MCP Runtime Refresh Interface And Trial Protocol — 2026-07-19

Status: static interface evidence and one isolated Codex status call observed;
deterministic claim fixtures prepared; no reload, configuration mutation, MCP
actuation, current-account read, or process stop authorized
Scenarios: `MCP-01`, `MCP-02`, `MCP-03`, `MCP-05`, `MCP-07`, `MCP-08`
Machine fixture:
[`../tests/fixtures/mcp-runtime-refresh-trial-2026-07-19.json`](../tests/fixtures/mcp-runtime-refresh-trial-2026-07-19.json)

## Why the route changed

The previous dated review correctly found only startup-oriented controls at
OpenAI Codex revision `2895d82b...`. A targeted recheck on 2026-07-19 found a
newer official `openai/codex` `main` revision,
`0fb559f0f6e231a88ac02ea002d3ecd248e2b515`, with an app-server refresh path.
The current local `codex-cli 0.144.6` stable, non-experimental generated schema
also exposes `config/mcpServer/reload` and `mcpServerStatus/list`.

This narrows the claim “mid-session control is unproven.” A refresh interface
exists statically in the tested binary protocol and the pinned official source,
and the read-only status method is callable in one isolated live app-server.
Live refresh, enable/disable, old-process release, task-end release, leases,
crash recovery, and resource savings remain unobserved.

## Pinned official evidence

At the pinned revision:

- [`mcp_types.rs`](https://github.com/openai/codex/blob/0fb559f0f6e231a88ac02ea002d3ecd248e2b515/codex-rs/config/src/mcp_types.rs)
  says `enabled=false` skips server initialization; `enabled_tools` is an
  allow-list and `disabled_tools` is applied afterward as a deny-list.
- [`mcp_refresh.rs`](https://github.com/openai/codex/blob/0fb559f0f6e231a88ac02ea002d3ecd248e2b515/codex-rs/app-server/src/mcp_refresh.rs)
  reloads the latest configuration, builds a refresh config for each loaded
  thread, and queues `Op::RefreshMcpServers`.
- [`session/mcp.rs`](https://github.com/openai/codex/blob/0fb559f0f6e231a88ac02ea002d3ecd248e2b515/codex-rs/core/src/session/mcp.rs)
  constructs a new `McpConnectionManager` and publishes a new runtime snapshot.
  Its comment states that an old runtime may remain while an in-flight step
  still holds it.
- [`state/service.rs`](https://github.com/openai/codex/blob/0fb559f0f6e231a88ac02ea002d3ecd248e2b515/codex-rs/core/src/state/service.rs)
  replaces the current manager and publishes the new snapshot.
- [`connection_manager.rs`](https://github.com/openai/codex/blob/0fb559f0f6e231a88ac02ea002d3ecd248e2b515/codex-rs/codex-mcp/src/connection_manager.rs)
  cancels its startup token and clears clients when the old manager is dropped.

Those are source semantics, not current Desktop UI behavior or process-release
observations. Reference-counted object lifetime is also not a task-level MCP
lease or per-server reference-count feature.

## Current official product-documentation corroboration

A 2026-07-27 refresh of the
[official Codex MCP documentation](https://developers.openai.com/codex/mcp/)
documents global or project-scoped `config.toml`, `enabled=false`, startup and
tool timeouts, allow/deny lists, and plugin-provided MCP on/off policy. Its
desktop and IDE setup flows still instruct the user to save and restart, while
`/mcp` exposes connected or active servers.

That public page does not document a task-bound acquire/release API,
lease/reference-count ownership, task-end release, idle resource accounting,
or crash-state restoration. Documentation absence is not proof that such a
capability cannot exist. It means those claims remain unproven and cannot be
substituted for the separately observed app-server source and runtime evidence
below.

## Current local stable schema evidence

Commands used:

```powershell
codex --version
codex app-server generate-json-schema --out <temporary-stable-directory>
```

Observed version: `codex-cli 0.144.6`. The generator is labelled experimental,
but `--experimental` was not supplied; the following methods appear in the
stable output:

| Method | Parameters | Static claim boundary |
| --- | --- | --- |
| `config/mcpServer/reload` | `null` | A protocol request exists. The schema does not prove the Desktop UI calls it or that a specific process exits. |
| `mcpServerStatus/list` | optional `threadId`, `detail`, `cursor`, `limit` | A thread-aware status request exists. It was later invoked without `threadId` in the isolated Stage 1 observation below. |

`McpServerRefreshResponse` is an empty object, so a successful response alone
cannot prove which server changed, whether tools changed, whether the prior
runtime was released, or whether resources improved.

Stable generated-file SHA-256 values:

| Generated file | SHA-256 |
| --- | --- |
| `ClientRequest.json` | `AC75A7DD43BF3EBA3681507370C0A218496A79A59FD470A189F4FDA104B1BDAD` |
| `v2/McpServerRefreshResponse.json` | `54A77812DB02175DC69053870E582D3B314AF6F161F0C76846F3563B0F9487C4` |
| `v2/ListMcpServerStatusParams.json` | `701916A7D444AFBBC68AEF9E72AB4E5C3111A8FD97560072E9B84713ADF9DDC0` |

The temporary schema directory is process evidence, not a repository product
artifact. Its later removal remains part of the exact-target cleanup ledger.

## Stage 1 isolated status observation

Machine evidence:
[`../registry/codex-app-server-isolated-mcp-status-probe-2026-07-19.json`](../registry/codex-app-server-isolated-mcp-status-probe-2026-07-19.json)

After explicit user authorization, the repository runner started Codex
app-server 0.144.6 with a new CODEX_HOME, analytics disabled, and account-token
environment variables removed when present. It sent exactly
`initialize -> initialized -> mcpServerStatus/list`; it did not send
`config/mcpServer/reload`, create a thread, mutate MCP configuration, or call an
MCP tool.

The successful run reported the requested isolated home in the initialize
response, returned `data=[]` from `mcpServerStatus/list`, and exited with code
0 after stdin was closed. The isolated home produced runtime databases and
runtime-owned system Skills, but no `auth.json` or `config.toml`. The response
therefore proves only that the status interface was callable without a thread
and that this empty isolated configuration reported no MCP servers.

The host also warned that it discovered a parent project `.codex` directory.
Because the project was not trusted in the isolated home, its config, Hooks,
and exec policies were disabled, while Skills may still remain discoverable
under host rules. This prevents an overclaim that a new CODEX_HOME physically
isolates every project-discovery surface. It did not alter the returned empty
MCP status.

Two failed runner attempts are retained as negative engineering evidence: the
first selected a non-launchable WindowsApps alias; the second closed stdin too
early and received initialization but no status response. The corrected runner
holds stdin open until each requested response arrives. Both the failed home
and successful home remain exact-target closeout debt; no deletion is
authorized in the current research phase.

## Staged falsifiable trial

### Stage 0 — static interface firewall

The pinned source, local version, stable schema method names, and hashes above
must be recorded. Static presence may support only
`recorded-static-refresh-interface-only`.

### Stage 1 — read-only status observation (observed once)

Start a separately authorized isolated app-server process and call only
`mcpServerStatus/list` for a bound thread or disposable environment. Record the
actual process, protocol handshake, thread ID, returned server/tool/auth fields,
approval prompts, data boundary, and process cleanup.

The 2026-07-19 execution used a new isolated home and observed an empty status
list. This does not test current configured or Plugin-provided MCPs, account
authentication, a bound thread, or repeatability.

### Stage 2 — same-config runtime refresh

With separate reload authority, capture status and tool surface before and
after `config/mcpServer/reload` without changing configuration. A response plus
a before/after status observation may prove one live refresh path. It cannot by
itself prove per-server release or resource savings.

### Stage 3 — controlled startup-field delta

In an exact disposable configuration, change one named server's `enabled`,
`enabled_tools`, or `disabled_tools` field, then reload. Record exact pre-state,
post-state, tool delta, process ownership, task result, and verified restoration.
No current Agent Home or production account configuration is the first target.

### Stage 4 — release and resource attribution

Claim per-server release only with exact process or host-owned lifecycle
identity plus observation that the old runtime/client is released. Claim a
resource benefit only after at least two comparable runs show a stable delta
without unacceptable task or restart cost.

Task-end release is a separate hypothesis. Configuration reload does not prove
that the host automatically releases an MCP when a task finishes, becomes
idle, crashes, or loses its final logical consumer.

## Hard failure and claim rules

- No static schema or source path may be promoted to live behavior.
- No status response may be promoted to refresh or release evidence.
- No reload may occur without separate runtime-mutation authority.
- No configuration delta counts without exact pre-state and verified restore.
- No generic `node.exe` or shared process may be assigned to one MCP by guess.
- No successful refresh response proves per-server release.
- No one-run RSS delta proves a stable resource benefit.
- No refresh result proves task-end release, lease/reference counting, crash
  recovery, cross-host parity, or safe automatic actuation.

The deterministic evaluator
[`evaluate_mcp_runtime_refresh_trial.py`](../scripts/evaluate_mcp_runtime_refresh_trial.py)
enforces these boundaries for the prepared fixtures only. It does not exercise
the app-server or prove host behavior.

## Next authority gate

Stage 1 is now observed once on Codex 0.144.6. The smallest next live step is a
disposable same-config Stage 2 observation: capture status before and after
`config/mcpServer/reload` without configuration changes. It requires separate
reload authority and a newly bound disposable home/process/cleanup boundary.
Stage 3 and later remain separate authorization gates.
