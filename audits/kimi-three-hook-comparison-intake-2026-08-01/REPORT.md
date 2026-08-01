# Kimi Three-Hook Comparison Intake

Status: `provisional-intake-evidence`

This record preserves the narrow evidence used to select the first comparison.
It is not a live-host acceptance result, a resource-savings result, or a
standalone replay package.

## Frozen source

- repository: `C:\Projects\kimi-code-user-config`
- branch: `master`
- revision: `3d51621f5f74b5f56cc286e233d2b2396fb62c3f`
- repository posture at inspection: clean, `0/0` against `origin/master`
- candidate identity: leading local candidate for the externally reported
  three prototypes; user confirmation remains open
- reported compatibility PR: not bound

| Artifact | SHA-256 | Git blob |
| --- | --- | --- |
| `hooks/mcp-gate.mjs` | `b1a21741b99c8da39c10c0da4acd9e77052ad7704a7cdc6c5a0519f6c2f16af9` | `3059f6414f6d1c7000e21f1ecb1c642c1d28dd01` |
| `hooks/session-start.mjs` | `7d32d1f2ae9c80eda12af2722cc0dcfb59b6f4af7bbe3574f240dbc7aead122d` | `f758759cc6b010eeff499a42562fb53b5e72078a` |
| `hooks/context-usage.mjs` | `884c40f92e9fdc7e9da8b1a2a03647746a0ca26820f09c7f6709586fde1e35ae` | `44eaccd966399d5a568e534c7cc00fdf972a3dc6` |
| `skills/mcp-gate/SKILL.md` | `c183602591390d19cd028cb11dbbf71512d139be836664808875b812b9a141de` | `912bffd856d91eafa0af69be804fb078d6314b4d` |
| `config.hooks.toml` | `aaff759ee5d57d11165e1025c66158ff2674b677fe8366eabb0139d2cc012bb3` | not recorded |
| `config.permission.toml` | `a876381226447b6cd66de851443b95a9e3b64eded9a10d2bc085643fb808c7b3` | not recorded |
| `mcp-gate.json` | `8e007ccf299637b3d54193cc8686bf9a525fbe4713b4569b56e52c1c469be79e` | not recorded |

The inspected current user projection matched these repository artifacts byte
for byte. No user configuration was changed.

## Isolated mechanism observation

An ephemeral no-model, no-network probe reported 24 passing assertions across:

- JavaScript syntax checks;
- explicit-off and default-off MCP blocking, built-in pass-through, and missing
  gate fail-open behavior;
- fresh memory/gate/handoff injection and stale-handoff exclusion;
- context warning thresholds, hysteresis, critical warning, and compaction
  reset behavior.

The probe used isolated temporary roots and did not write the live Kimi state.
Its temporary script and raw output were removed during cleanup. Therefore this
record preserves the observed result and source identities, but the 24-assertion
run is not independently replayable from this repository alone.

## First same-task observation

A read-only probe inspected only the final `256 KiB` of the then-current Kimi
main wire and retained no conversation content. It observed:

- source wire size at observation: `1056177` bytes;
- usage objects in the inspected tail: `52`;
- last total input: `173234`;
- configured maximum context: `1048576`;
- ratio: `0.165209` (`16.5209%`);
- Kimi `context-usage.mjs` result: no reminder;
- isolated state that would have been written:
  `{ "lastTotal": 173234, "lastWarnLevel": 0 }`;
- live `.context-usage-state.json`: absent before and after the probe;
- Harness `evaluate_context_pressure_advisory` result: `CONTINUE`,
  `supported-signal-no-advisory-trigger`, trace
  `[OBSERVE, EVALUATE, CONTINUE]`, no follow-on action.

The sanitized extraction script and isolated runtime root were removed. This is
a single non-pressure observation, not pressure attribution, a stable benchmark,
resource-savings evidence, cross-host parity, or a live-model result.

## Current decision boundary

The narrow evidence favors composition: the Kimi Hook supplies host-specific
event and telemetry extraction, while the Harness contract supplies portable
decision, authority, and claim semantics. It does not establish a residual
self-authored gap. `mcp-gate` is likewise a Kimi call-control adapter, not a
dynamic resource-lifecycle implementation: it fails open and does not unload
schemas, processes, or connections.

The exact-comparison gate remains open. A decision-relevant replay needs a
retained evaluator and output, the same bound task on both paths, a pressure
state when pressure behavior is claimed, and separately bound comparisons for
`session-start` and `mcp-gate`.
