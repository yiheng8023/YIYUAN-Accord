# Codex App-Server Task-Scoped Skill Exposure Evidence — 2026-07-24

Machine-readable evidence:
[`../registry/codex-app-server-task-scoped-skill-exposure-evidence-2026-07-24.json`](../registry/codex-app-server-task-scoped-skill-exposure-evidence-2026-07-24.json)

Reproducible probe:
[`../scripts/probe_codex_app_server_skill_exposure.py`](../scripts/probe_codex_app_server_skill_exposure.py)

## Result

Codex app-server `0.145.0` on this Windows host passed a bounded
task-scoped exposure preflight:

- the control process exposed 105 enabled user Skills and 6 enabled system
  Skills;
- a second short-lived process received 105 one-off
  `skills.config=[{path=...,enabled=false}]` entries;
- the same 111 Skill identities remained present, all 105 user Skills became
  effectively disabled, and all 6 system Skills stayed enabled;
- all six duplicate self-authored rows for `intent-contract`,
  `capability-router`, and `closure-contract` changed from enabled to disabled;
- the ephemeral thread reported exact model `gpt-5.3-codex-spark`, reasoning
  effort `low`, provider `openai`, approval policy `never`, and read-only
  sandbox with network disabled;
- the thread reported both global and repository `AGENTS.md` instruction
  sources;
- one completed turn returned exactly
  `AAH_SPARK_LOW_DISABLED_EXPOSURE_OK`;
- completed event items were only `userMessage`, `reasoning`, and
  `agentMessage`; no command, file change, MCP call, dynamic-tool call,
  collaboration-agent call, or web search was observed.

The current global Codex config hash and repository-status digest were identical
before and after the probe. No global config write, application restart,
capability installation, MCP tool invocation, commit, or push occurred.

## Evidence-source correction

`turn/completed` may carry an empty item view. The first marker attempt therefore
did not support a success or failure conclusion. The probe then tested
`thread/read(includeTurns=true)` and observed JSON-RPC `-32600` because
ephemeral threads do not support that request. The accepted run reconstructs
the target turn from matching `item/completed` notifications and uses
`turn/completed` only for the final turn status.

This distinction is enforced by tests so an empty completion payload cannot be
misreported as a missing model response.

## Interpretation

This evidence supersedes the prepared global-config transaction as the
preferred Codex `0.145.0` route for the self-authored-disabled preflight. The
older transaction remains historical evidence and is still blocked by baseline
drift; it was not executed or silently rebaselined.

The result proves only current-host process-scoped exposure control and one
marker-only Spark/low turn. It does not prove:

- a formal five-arm ablation result;
- explicit or implicit invocation of Matt, Superpowers, or repository-authored
  Skills;
- superiority, net value, or behavioral portability;
- cross-host or cross-device equivalence;
- dynamic MCP lifecycle control;
- automatic host thread creation;
- production readiness.

The next bounded gate is one selected-Skill exposure preflight under the same
parent-observed model, effort, instruction-source, repository, and forbidden
action checks. Behavioral comparison still requires the existing repeated
private-oracle live-run envelope.
