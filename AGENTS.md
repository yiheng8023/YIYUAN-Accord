# Agent Autonomy Harness Repository Guidance

This repository is the product authority for an agent-neutral autonomy,
collaboration, and capability-orchestration harness.

The north star is to reduce the user's Agent learning and orchestration burden
while preserving human control over goals, creative judgment, consequential
decisions, and bounded authorization.

Current phase: external landscape research, host-capability verification, and
small falsifiable proofs of concept. Do not claim that dynamic MCP lifecycle
control, context telemetry, automatic thread creation, or equivalent behavior
exists on a host until that host has been tested.

Use this priority order:

1. healthy native or runtime-owned capability;
2. suitable official capability;
3. reviewed and maintained external implementation;
4. composition of existing capabilities;
5. self-authored implementation only for an evidenced residual gap.

Keep portable decision contracts, host-specific adapters, capability-source
governance, and consumer projections distinct. Treat AGENTS/rules, Skills,
Hooks, MCPs, Plugins, Apps, and native Agent capabilities as one broad chain
with different authority and lifecycle costs. Do not keep every external
capability permanently active.

Preserve three distinct governance classes. An official, runtime-owned, or
built-in Skill remains dated external capability metadata and must not be
vendored. A third-party candidate remains exact upstream and must not enter an
execution path before license/provenance, security, dependency, maintenance,
portability, overlap, and validation review plus separate manager/consumer
authority; its body does not enter the current repository release. Only an
admitted repository-authored residual-gap Skill may enter a future active
release inventory. Consumer integration remains separately governed and this
repository does not write to `codex-user-config`.

The inherited 19 adapted third-party payloads are deprecated transition
evidence, not current installation or update authority. Preserve third-party
payload identity and bytes exact upstream by default; put portability,
compatibility, routing, composition, and host differences in metadata, Recipes,
adapters, or repository-owned wrappers. Portfolio curation is distinct from
task-time activation: a bounded coverage/source/isolation/review/authority/
verification/stop-rule contract may drive broad inactive-pool discovery and
review without one end-user task, while installation, enablement, execution,
and persistent activation remain separately governed.

Context governance concerns the effective lifetime of a collaboration, not a
single universal token percentage. Support transparent counters, opaque hosts,
automatic compression, heuristic fallback, and repository-anchored handoff.

Use native host authorization and permission enforcement surfaces as the
boundary, including approval dialogs, permission rules, or an equivalent
host-owned mechanism. Plan and batch operations to avoid unnecessary prompts,
but do not bypass or reproduce the host permission system.

Before repository changes, inspect branch, status, HEAD, upstream, and relevant
dirty files. Preserve inherited evidence and user changes. Do not delete the
old repository or other workspaces without separate explicit authorization.

Start continuation work from `docs/operations/CONTINUATION.md`, then verify live
repository truth instead of treating the handoff as current fact.
