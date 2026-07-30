# Codex App-Server Selected Skill Exposure Evidence — 2026-07-24

Machine-readable evidence:
[`../registry/codex-app-server-selected-skill-exposure-evidence-2026-07-24.json`](../registry/codex-app-server-selected-skill-exposure-evidence-2026-07-24.json)

Probe:
[`../scripts/probe_codex_app_server_selected_skill_exposure.py`](../scripts/probe_codex_app_server_selected_skill_exposure.py)

## Result

Codex app-server `0.145.0` passed a single-selected-Skill exposure preflight on
this Windows host:

- the control inventory contained 105 enabled user Skills and 6 enabled system
  Skills;
- a one-off `skills.config` array kept only the exact CC Switch-managed
  `grill-me` path enabled;
- the same 111 Skill identities remained visible;
- the selected inventory contained exactly 1 enabled user Skill, all other 104
  user Skills were disabled, and all 6 system Skills retained their state;
- the selected file was 645 bytes and matched the previously reviewed SHA-256
  `c9df326c4ab635765ea884471d21f4e21d5b0ec85aec43a06c238307841eb4bc`
  before and after the probe;
- an ephemeral thread reported exact `gpt-5.3-codex-spark` with `low`
  reasoning, provider `openai`, approval policy `never`, both instruction
  sources, and read-only/no-network sandbox.

No `turn/start` or model request was sent. Global Codex config and repository
status digests were unchanged. The probe performed no installation, restart,
MCP call, file-content capture, commit, or push.

## Selection rationale

`grill-me` is an already-present, CC Switch-managed, user-explicit,
questioning-only Matt-derived capability. The prior static review classifies it
as a post-front-gate deep-questioning complement, not a replacement for the
repository intake contract. That makes it a smaller first selected-exposure
surface than a full engineering workflow or full Superpowers bootstrap.

## Claim boundary

This result proves only that current-host process configuration can expose one
exact external user Skill while disabling all other user Skills. Because no
model turn occurred, it does not prove:

- loader invocation;
- that Skill instructions reached a model;
- explicit or implicit trigger behavior;
- behavioral value, safety, net benefit, or superiority;
- any five-arm ablation result;
- cross-host parity or production readiness.

The next bounded gate is an explicit invocation trial whose input includes the
exact selected Skill name and path, whose parent observes loader/trigger
evidence and response bytes, and whose scenario-specific private oracle remains
separate from the Skill payload.

The generated app-server `0.145.0` v2 protocol exposes `skills/list`,
`skills/changed`, `skills/config/write`, `plugin/skill/read`, and the
`UserInput` variant `{type: "skill", name, path}`. It does not expose a
dedicated Skill-loader-completed notification. A future explicit invocation
may therefore prove that the host accepted and echoed the exact Skill input and
that behavior was consistent with the payload, but those observations must not
be renamed as an independently observed loader event.
