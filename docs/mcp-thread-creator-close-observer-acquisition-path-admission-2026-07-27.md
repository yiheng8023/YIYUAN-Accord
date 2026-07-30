# MCP thread creator-close observer acquisition-path admission

Date: 2026-07-27
Status: `offline-amendment-required-before-live`

## Decision

The current creator-connection-close protocol/probe pair is **not admitted for
live execution**. Its observer setup still requires `thread/resume`, while the
only three protocol-valid, zero-model-turn reports use
`thread-created-auto-attach` followed by a direct connection-B tool call.

This is an offline evidence-admission result. It does not run an app-server,
open loopback transport, request a model turn, use external network access, or
change configuration.

## Exact evidence bindings

- Protocol:
  `8A110058AAC75DDC54E2B3795F6F6BE12004E4CDE0262045BEA79D112D157326`
- Current probe:
  `66CF7066B68D92139653C5E41AD74CAA64D00273C662A2899E396501974C2CF6`
- Invalid calibration record after compact cleanup reconciliation:
  `D0872E69083A79A87CDF9D3A269E6AC53E676AE7D2EAA4AFF97110618BE3A0FA`
- Multi-connection evidence registry:
  `ED3047D4EDC8B1FC437A1EF90E5DDB9C660078CE6D66B98112CEEF83E76F3E22`
- Formal run reports:
  `F4C0230E4C87C8499365F892671FA41BD5B4A615EB7539A73557D65C278CCB5D`,
  `769BA186566817C5120BEDA3769D4C4B870C303A1A4540EA36FC47B2F077DC2D`,
  and
  `C9D569B30F80DA680A46C79A8650F7ECB9B61E6298D4748326447F0F883E8E36`.

The standalone validator checks those bytes and independently checks all three
reports. Each report must show one app-server, two distinct bridge processes,
one shared thread, the same exact Sentinel PID and instance across A and B,
connection B calling `mcpServer/tool/call` directly, and zero requested or
notified model turns.

## Why the current pair is blocked

The current protocol setup says that connection B resumes the thread. The
current probe also sends `thread/resume`. The retained calibration is invalid:
it never entered the paired window, produced zero formal live paired runs, and
does not authorize continuation.

The three formal auto-attach reports establish bounded same-thread,
same-Sentinel callability across two distinct connections. They also explicitly
show that a second independently releasable subscription was **not** observed.
Therefore auto-attach must not be promoted to a second subscription, owner,
lease, reference count, task-end signal, final-release mechanism, or live
readiness result.

## Required offline amendment

A future, separately reviewed revision may:

1. initialize B and finish its `config/read` barrier before A starts the thread;
2. have A start the read-only thread and make the baseline Sentinel call;
3. have B call the same thread and Sentinel directly, without `thread/resume`;
4. retain rollout materialization only as diagnostic evidence.

That candidate sequence is not live authorization. The bound historical
protocol and probe remain unchanged. A new protocol/probe revision plus
deterministic validation is required before a separate decision about live
loopback execution.

## Claim and execution boundary

This artifact authorizes only read-only source/report validation and offline
artifact creation. It does not authorize app-server startup, loopback
transport, model use, external network access, configuration mutation,
installation, or live protocol execution. It proves no second subscription,
independent owner, lease/reference count, task-end semantics, final release,
resource benefit, cross-host parity, cross-version parity, controller need, or
production/live readiness.
