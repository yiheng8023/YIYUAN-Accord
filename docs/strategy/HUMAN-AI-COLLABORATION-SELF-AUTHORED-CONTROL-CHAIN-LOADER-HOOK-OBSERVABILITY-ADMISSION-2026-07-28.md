# Self-authored control-chain loader and Hook observability admission

Date: 2026-07-28
Status: current-host observability gap; no live admission

Machine-readable authority:
[`../../registry/human-ai-collaboration-self-authored-control-chain-loader-hook-observability-admission-2026-07-28.json`](../../registry/human-ai-collaboration-self-authored-control-chain-loader-hook-observability-admission-2026-07-28.json)

## Decision

Do not start the 36 preregistered weak-model runs on Codex app-server 0.145.0.
The dependency-complete five-file projection and four no-turn exposure cells
are valid, but the frozen attribution contract additionally requires an
independent task-bound loader event for the scenario-relevant Skill.

The locally generated 0.145.0 schema exposes:

- `skills/list`, which reads Skill metadata;
- `skills/changed`, which only invalidates a watched local Skill inventory;
- `hook/started` and `hook/completed`, whose summaries can carry thread,
  optional turn, event, source path, status, output entries, and timing.

It does not expose a Skill-loader identity or digest notification. The official
app-server README describes the same distinction: callers use `skills/list`
for inventory, `skills/changed` as a file-change invalidation signal, and a
typed `skill` turn input to request backend instruction injection. None of
those surfaces is an independent loader-completed event.

## Attribution consequence

A model turn could produce Hook run notifications, but it would not fill the
separate Skill-loader evidence gap. Dispatching a weak model solely to capture
Hook events would therefore spend a scored resource while leaving the
chain-versus-Hook attribution contract unsatisfied.

This is a host-observability constraint, not a candidate failure or a code
stack failure. The missing event receives no Skill value, harm, or portfolio
credit.

## Next gate

Keep the exact-loader acceptance boundary unless one of two events occurs:

1. a future host exposes a task-bound Skill loader event carrying identity or
   digest; or
2. the owner separately authorizes a protocol amendment that accepts a weaker
   behavior-association surface.

The second option changes the experiment's trust and attribution boundary. It
is not authorized by this evidence record. No model, Skill, Hook
configuration, CC Switch, cleanup, commit, or push action occurred.
