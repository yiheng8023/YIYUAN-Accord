# Codex 0.146.0 MCP reload/release version-change evidence

Canonical record: [`registry/mcp-app-server-0.146.0-reload-release-version-change-evidence-2026-08-02.json`](../registry/mcp-app-server-0.146.0-reload-release-version-change-evidence-2026-08-02.json)

## Decision

The current Windows Codex CLI `0.146.0` released the exact already-loaded
Sentinel runtime after same-thread configuration disable plus
`config/mcpServer/reload` in all three isolated repetitions. Each exact stop
occurred inside the ten-second attribution window; the original thread then
rejected the disabled server, exact configuration restoration succeeded, and a
new-thread recovery control succeeded.

This is a bounded native-current-version win. It reverses the observed
five-second retention result for the separately bound `0.145.0` version, but it
does not invalidate that historical evidence or prove cross-version parity.
Native current behavior must be compared before any self-authored controller;
the current record does not make such a controller eligible.

## Source and execution boundary

- Official source is pinned to OpenAI Codex release `rust-v0.146.0`, release
  commit `e363b08c9175ac1cbe5893615dd2cb9ddf95043b`, the relevant merged pull
  requests, and three exact source-file Blob/SHA-256 bindings recorded in the
  canonical JSON.
- Each repetition used an empty isolated `CODEX_HOME`, one local Sentinel,
  disabled Plugins/Apps/sharing features, and no copied user configuration,
  authentication, or Plugin state.
- No model turn or model request was started. Application logs did show an
  unauthenticated Responses WebSocket attempt that failed before any model
  turn, so this evidence does not prove zero network traffic.
- The raw reports bind the CLI version and producer digests. The separately
  observed installed executable digest is informative only; the raw reports do
  not self-bind it.

## Process attribution

Across three repetitions there were 63 process samples, six exact baseline
identity samples, three matching stop events, and three graceful app-server
exits. Release latencies from reload response to the exact stop event were
`717.753 ms`, `717.591 ms`, and `695.640 ms`.

One run observed reuse of the baseline PID by a different `sleep.exe` process.
The validator therefore uses PID, creation time, and image path as the exact
identity boundary; PID-only disappearance or reuse is not release proof.

Each restored run also observed two distinct post-restore Sentinel starts. This
is evidence of the tested recovery paths, not proof of a universal one-process-
per-thread rule.

The unmodified raw producer reports set
`claimBoundary.provesReloadCausedOldRuntimeRelease=true`. That wording is
rejected by the canonical record: configuration disable occurred before reload
in the same attribution sequence, and no ablation isolated reload alone. The
only allowed claim is release observed after configuration disable plus reload.
The validator binds both the raw defect and its canonical rejection so the
producer sentence cannot be silently promoted.

## Open claims

The evidence does not prove task-end release semantics, concurrent-owner or
lease safety, arbitrary local stdio or remote HTTP behavior, stable total host
resource savings, generic crash recovery, cross-host parity, production
readiness, or a residual need for a self-authored controller.

The next decision gate is one bound workload comparing a static-minimal profile
with the native phase-gated profile. Host-neutral lifecycle semantics and
host-specific mechanisms must remain separate in that comparison.
