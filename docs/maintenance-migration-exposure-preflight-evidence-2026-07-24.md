# Maintenance/Migration Exposure Preflight Evidence

Date: 2026-07-24
Status: pass for current-host exposure and prompt boundary only

## Result

On Codex Desktop app-server 0.145.0, the same 111-Skill identity set was
observed across control, native-disabled, and selected profiles:

- control: 105 user Skills enabled and 6 system Skills enabled;
- native arm: all 105 configurable user Skills disabled;
- candidate arm: only the exact CC Switch-managed
  `deprecation-and-migration` Skill enabled;
- non-configurable states and the identity manifest remained unchanged.

Both effective profiles started ephemeral read-only Spark/low threads. No
`turn/start` was sent, no model request was sent, and no MCP, installation,
global configuration, Git, or external write action occurred.

The candidate remained byte-stable at
`52ef07de05726292c0f5e9fe666cc30e6efbe580ed775621e785a49ec80bd4ea`.
The global configuration and both fixture trees were stable.

## Prompt and oracle boundary

The native and candidate packets used the same public task prompt. The
candidate packet differed only by the selected-Skill metadata required for the
treatment. The private oracle was not written into either trial tree, and the
private sentinels `Mira`, `Qin`, `Archive`, and `"v0"` were absent. The
temporary preflight trees were removed after evidence capture.

## Invalid attempts retained

Two attempts are retained but excluded:

1. an interface-invalid attempt used `runtimeWorkspaceRoots` without enabling
   the experimental API and failed with JSON-RPC `-32600` before any task turn;
2. a measurement-invalid attempt used `v3` as a private sentinel even though
   `v3` already appeared in the public visible unsupported-format test.

Neither attempt counts as a candidate result. The valid report SHA-256 is
`58382ffaa0ab7fb7dcef583af2f0f10334648fca59649a6866019f97c576608d`.

## Claim boundary

This preflight proves current-host task-scoped disabled and selected inventory
states plus the prompt/oracle separation. It proves no Skill loader invocation,
instructions reaching the model, behavioral value, causation, general migration
competence, production or removal readiness, or cross-host portability.
