# Codex app-server 0.145.0 new-thread MCP reload evidence

Date: 2026-07-23
Host: Codex CLI app-server 0.145.0 on Windows
Status: observed single-host new-thread transition; same-thread actuation and
release remain unproved

## Outcome

One isolated, no-model-turn run observed a bounded disable/re-enable transition
for **new ephemeral threads**:

- thread A was created while the Sentinel was enabled and could call it;
- after an atomic `enabled = false` replacement plus accepted reload, new
  thread B could not call the Sentinel;
- after exact-byte restoration plus another accepted reload, new thread C
  could call a distinct Sentinel instance.

This supports a narrow new-thread configuration transition on this host and
version. It does not isolate whether reload caused that transition or whether
`thread/start` independently reread the current config. It also does not prove
same-thread hot enable/disable, task-scoped MCP lifecycle control, or resource
release.

## The status/runtime split is the important falsifier

`mcpServerStatus/list` did not represent the already-loaded thread runtime:

- after disable, A's status row had no tools, but A still called the same
  Sentinel instance;
- after re-enable, B's status row again exposed tools, but B still returned
  `unknown MCP server 'lifecycle_sentinel'`;
- only new thread C acquired a callable enabled runtime.

Therefore a status tool list cannot be treated as proof that reload has
actuated inside an existing thread. The accepted empty reload response remains
queue/acceptance evidence, not completion evidence. This matches the
[official 0.145.0 app-server documentation](https://github.com/openai/codex/blob/rust-v0.145.0/codex-rs/app-server/README.md),
which says loaded threads apply refresh on their next active turn.

No active model turn was started in this experiment, so the documented
next-active-turn path was deliberately not exercised.

## Configuration transaction

The isolated config used two atomic replacements:

| State | Bytes | SHA-256 |
|---|---:|---|
| enabled before | 537 | `9b5abb4752f4831a3d3e93082ed831b448ef74e1807aa1c1f5e69e2982c536dd` |
| disabled | 538 | `6d493563417ad935ae7c6474c692c568815da4edacd4774f27eada8a030a2cd9` |
| enabled restored | 537 | `9b5abb4752f4831a3d3e93082ed831b448ef74e1807aa1c1f5e69e2982c536dd` |

The only intended semantic difference was
`mcp_servers.lifecycle_sentinel.enabled`. Restoration was attempted in
`finally`, and the final bytes exactly matched the initial bytes. No current
user config, auth state, or Plugin state was copied.

## Process and cleanup boundary

The runner launched the bundled native `codex.exe`, so PID `61320` and the
termination handle belonged to the actual app-server process rather than a
`codex.cmd` launcher wrapper. Closing stdin did not end it within the fixed
15-second teardown window, so the runner terminated that exact native process
handle.

Five Sentinel instances were observed for one configured server across the
three threads and multiple status/call phases. Four wrote `instance-stop`; the
fifth wrote no stop event but its PID was absent after app-server teardown.
No PID signal cleanup was used, and the test-only cleanup marker was not
needed.

Only two instances were call-capable runtimes bound by returned tool payloads:
thread A used PID `38616`, and thread C used PID `43076`. The other three only
received `tools/list` and are conservatively classified as status/discovery
candidates; they are not assigned to a loaded thread runtime. This also shows
that a status query can create an additional Sentinel instance.

These exits occurred during or around reload and app-server teardown and are
not attributed to reload. They do not prove old-runtime release, task-end
release, idle release, lease/reference counting, or resource savings.

## Raw evidence

- root:
  `C:/tmp/agent-autonomy-mcp-reload-new-threads-0.145.0-20260723-run01`
- normalized result: 33,238 bytes,
  SHA-256 `3bc40708e0e8378389dc9b9fcfd5fb694812063105ff0ca15d43c876e0d25451`
- Sentinel event log: 5,457 bytes,
  SHA-256 `20ec4305cbe90aef991c111ec71337054939f08adf3edce003e4d9f36549c3dc`
- machine record:
  `registry/mcp-app-server-0.145.0-new-thread-reload-evidence-2026-07-23.json`

The temporary root is retained as cleanup debt, not product payload.

## Claim boundary

This run does not establish:

- same-thread hot enable/disable or completed loaded-thread refresh;
- that reload, rather than new-thread config loading, caused the new-thread
  state change;
- status/runtime equivalence;
- release caused by reload;
- task-level lease, reference counting, or task-end immediate release;
- the 30-minute idle-unload path;
- crash recovery or stable resource savings;
- absence of network traffic; no packet monitor was used;
- Desktop, Plugin MCP, Claude, or other-host parity.

The next gate is a decision, not an automatic implementation step: determine
whether an active-turn same-thread refresh trial is worth its added model and
host cost. The new-thread fallback is already evidenced for this isolated
Codex path.
