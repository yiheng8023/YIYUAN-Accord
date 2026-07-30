# Codex 0.145.0 Multi-Connection Subscription Preflight

This directory contains three formal, sequential, no-model-turn preflight
runs for one Codex app-server process with two independent loopback WebSocket
connections and one local MCP Sentinel.

Each formal run:

- used one fresh explicit `CODEX_HOME`;
- initialized two independent Node built-in WebSocket bridges;
- synchronized the second connection's `initialized` notification with a
  read-only `config/read` response before `thread/start`;
- called the same exact Sentinel instance from both connections;
- observed owner A return `unsubscribed`, then `notSubscribed`;
- observed owner B return `notSubscribed`, then `notSubscribed`;
- started no Codex model turn and received no turn-start notification;
- kept app-server alive until evidence capture; and
- verified Sentinel cleanup only after the evidence boundary.

The three reports are:

- `run-01/report.json`
- `run-02/report.json`
- `run-03/report.json`

`resume-calibration-01.log` is excluded calibration evidence. It records that a
non-ephemeral, zero-turn `thread/start` advertised a rollout path but no file
materialized within the two-second calibration window. Therefore
`thread/resume` could not be used to acquire a second subscription in that
calibration without introducing a model turn or fabricating host state.

The evidence supports only a bounded negative preflight result: the tested
thread-created best-effort auto-attach path did not produce an independently
releasable second subscription. It does not prove that multi-connection
transport is absent, that every resume path is impossible, that internal
reference counting is incorrect, or that a self-authored lifecycle controller
is needed.
