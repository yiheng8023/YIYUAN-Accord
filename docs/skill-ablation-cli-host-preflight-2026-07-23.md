# Skill Ablation CLI Host Preflight — 2026-07-23

Status: formal weak-Agent arms blocked; CLI login unavailable and requested
model identity unverified
Machine record:
[`../registry/skill-ablation-cli-host-preflight-2026-07-23.json`](../registry/skill-ablation-cli-host-preflight-2026-07-23.json)

## Result first

No `gpt-5.3-codex-spark/low` ablation result exists yet.

The local CLI is `codex-cli 0.145.0`. One ephemeral, read-only, no-tool request
returned a response after requesting `gpt-5.3-codex-spark/low`, but neither the
runtime event stream nor the Agent response exposed an actual model or reasoning
value. This is request-path evidence only, not weak-model identity proof.

Two later ephemeral attempts supplied one-off `skills.config` disable entries
without changing the global config. Both reported that model metadata for
`gpt-5.3-codex-spark` was not found and failed with `401 Unauthorized` before an
Agent result. A direct read-only `codex login status` check then reported
`Not logged in`.

Formal arms remain blocked. No login, OAuth flow, API-key setup, global
configuration write, application restart, Skill install, or repository
mutation was attempted.

The current official
[Codex-Spark announcement](https://openai.com/index/introducing-gpt-5-3-codex-spark/)
describes Spark as a research preview rolling out to ChatGPT Pro users in the
latest Codex app, CLI, and VS Code extension, with access potentially limited
or queued. This establishes a plausible official route, not current account entitlement or live availability. The local CLI is still not logged in, and
this review did not inspect or change the user's subscription, start OAuth, or
create an API key.

Repository-only work continued without crossing that host boundary. The live
evaluator now rejects Agent self-report as proof of actual model, reasoning, or
Skill exposure; requires parent- or host-observed condition evidence; matches
all eight Git Arm A results against the private oracle; and requires three
independent run IDs for a formal pass. This hardens future evidence but does
not execute a live arm or reduce the authentication/model block.

## Current desktop subagent surface

The current official
[Subagents](https://learn.chatgpt.com/docs/agent-configuration/subagents.md)
manual identifies `gpt-5.6-terra` as the faster, lower-cost choice for lighter
subagent work and says explicit spawn model and reasoning values override
defaults. It also describes `low` reasoning for straightforward,
speed-sensitive tasks. The official
[Skills](https://learn.chatgpt.com/docs/build-skills.md) manual documents
`skills.config` disable entries, and the subagent manual says a custom Agent
configuration may contain `skills.config`.

That product capability is not yet reachable through the callable spawn surface
used by this task. The surface accepts model and reasoning overrides, but
exposes neither a custom-Agent selector nor per-run `skills.config`. The current
startup list also exposes `intent-contract`, `capability-router`, and
`closure-contract`. Therefore `gpt-5.6-terra/low` could be a useful lightweight
full-stack diagnostic, but it cannot become the formal self-authored-disabled
arm merely by asking the Agent not to use those Skills.

No subagent was spawned for this review. Running three repetitions under the same visible-Skill condition
would only repeat a confound, so the planned batch was rejected before
execution. No global configuration or custom Agent file was written. A future
callable custom-Agent selector could make project-scoped Skill isolation
testable; documented configuration support alone does not prove that the
current spawn surface can select it.

## Attempts

| Attempt | Isolation | Result | Admissible conclusion |
| --- | --- | --- | --- |
| Baseline control request | ephemeral, ignore user config, read-only, no tools | response completed; actual model/reasoning `unknown` | the request path once returned, but weak condition is unverified |
| Full optional-capability disable | one-off Skill paths plus installed plugin disables | model metadata warning, then 401 and failed turn | no exposure or behavior result |
| Six self-authored projections disabled | one-off six-path `skills.config` override | model metadata warning, then 401 and failed turn | no self-authored-disabled result |

The one-off overrides were process arguments only. The live
`~/.codex/config.toml` was not edited, backed up, replaced, or restarted.

## Why the first response does not rescue the later failures

A successful sampling response does not independently prove which model served
it. The response self-reported `unknown`, and the event stream did not provide
an authoritative model field. The later explicit metadata warning prevents
upgrading the initial request into an exact-model claim.

Likewise, a failed request with `skills.config` arguments does not prove that
the named Skills were disabled in a sampled Agent turn. The control plane must
first authenticate, accept the requested model, sample a turn, expose the
intended Skill state, and return the scenario result.

## Rerun gate

The bounded rerun requires either:

- the user independently confirms an eligible plan and completes CLI
  login/account setup; or
- the host exposes another already-authorized session surface that can verify
  the requested weak model and reasoning level while supporting reversible
  per-run Skill isolation.

After that external state changes, rerun exposure-only preflight before sending
any formal scenario. Do not silently substitute another model, treat
`gpt-5.6-sol` as weak, or infer disablement from a prompt.

This host block does not stop repository-only fixture work, source comparison,
context/Git/MCP PoCs, or strong-model diagnostic design. Those remain separate
from primary weak-Agent acceptance.
