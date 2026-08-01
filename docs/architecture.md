# Architecture

## Producer / Consumer Model

Consumer configuration repositories own portable user configuration,
agent-specific runtime integration, authorization boundaries, and restoration
order. The current characterized private consumers are `codex-user-config` and
`claude-user-config`; public users should learn the pattern through
`codex-user-config-template` and `claude-user-config-template`. This repository
owns the reviewed Skill supply chain and its semantic relationships.

The repositories have a one-way producer-consumer relationship for Skill
release artifacts. This repository produces reviewed content and deterministic
release evidence; it does not install, does not write to private configuration
repositories, and does not write to a live Agent environment. A consumer
configuration repository pins a reviewed revision, then plans, backs up,
installs, verifies, and rolls back managed Skill paths.

The consumer-owned runtime sequence is:

1. restore and verify the user-configuration baseline;
2. resolve the pinned Skills repository revision;
3. verify provenance, policy, hashes, and approval state;
4. materialize agent-neutral Skill cores into the supported Skill directory;
5. apply only the adapter required by the active agent environment;
6. rebuild the capability index and topology from governed registry data;
7. verify discovery, routing, conflicts, and representative workflows.

Steps 1-7 describe consumer behavior, not executable responsibilities of this
repository.

The consumer-side configuration pattern is generic in purpose: environment
migration, cloud sync/backup, restore, verification, rollback, and runtime
integration. Concrete templates may be agent-specific because each agent has
different files, settings, memory surfaces, hooks, plugins, MCPs, tools, and
account state.

## Capability Layers And Decisions

The curated authority governs third-party Skill bodies and an abstract,
product-neutral capability taxonomy. Official, runtime-owned, built-in, and
first-party Skill bodies remain outside its governed and managed inventory.
They may be consulted only as dated overlap evidence; such evidence does not
transfer ownership, assert canonical identity, or prove current runtime
availability. Their bodies must not be vendored or enter the release manifest.

Official Skills, capability packages, workflow templates, and similar public
capability bundles from Agent, runtime, platform, or tool ecosystems may be
recorded as official external capability baselines. A baseline is a pinned
coverage-calibration surface: it may inform gap analysis, overlap review,
routing calibration, and future intake decisions, but it is not managed
inventory, not release payload, and not proof of live availability. Anthropic
official Skills are the first recorded instance, not a special-case vendor
rule.

A third-party candidate remains in source, intake, selection, and audit
surfaces until it has passed source pinning, license, provenance, security,
portability, overlap, adaptation, and validation review. Before approval it
must not enter an execution path. Only a curated approved Skill with
`status=approved` may enter `skills/` and the schema-1 manifest;
`registry/skills.json` is the approved release inventory.

The configuration-owned `capability-router` is a capability decision router.
It may select native reasoning, an official or runtime-owned capability, a
curated Skill, external capability metadata, a recipe or DAG, human
confirmation, or no skill needed. Candidate content is not a routing target.
High-risk, ambiguous, conflicting, permission-changing, write, install,
delete, migration, publish, release, or rollback decisions require human
confirmation.

The routing contract separates semantic normalization from deterministic
policy. The active Agent interprets multilingual and context-dependent intent;
the governed projection then adjudicates availability, native/runtime
equivalence, context and negative gates, Recipe composition, risk, cost,
permission, conflict, ambiguity, validation, and fallback. The checked-in
scenario corpus exercises this policy but is not a replacement language model
or a keyword router.

For multi-step execution, routing is event-driven rather than one-shot or
per-atomic-step. A consumer should re-evaluate at phase boundaries, after new
context, after failures or blockers, before side-effecting actions, before
switching capability classes, and before final verification. The deterministic
projection supports those reroute checkpoints; the consumer still owns live
availability checks and authorization.

## Dynamic Capability Topology

Git-tracked JSON is the initial authority. A graph database or visualization
may consume generated projections later, but must not become a second manual
source of truth.

Accepted contract decisions live under `docs/decisions/`. They constrain
future schema and release-interface changes, but they do not replace the
registries as machine-checked authority.

Nodes may represent Skills, capabilities, artifacts, lifecycle phases,
conditions, tools, adapters, policies, risks, and evidence. Typed edges express
ordering, data flow, collaboration, alternatives, fallbacks, conflicts, and
replacement. Recipes represent multi-node conditional workflows where a simple
pairwise edge is insufficient. A Recipe is not just a list of steps: it must
declare evidence gates, failure policy, and terminal criteria so a consumer can
distinguish a completed composition from an unsafe partial path.
Conflict groups similarly need more than prose: each group must declare its
scope, disposition, tie-breakers, and human-confirmation conditions before a
consumer can safely use the default owner.

Stable IDs survive renames. Every inventory change must regenerate derived
indexes and report impacted routes, unresolved references, cycles where cycles
are forbidden, and newly introduced conflicts.

## Portability Boundary

The portable core describes goals, inputs, outputs, invariants, decisions, and
verification. Adapters translate only unavoidable environment details such as
tool names, hook event shapes, filesystem conventions, and agent-specific
invocation syntax.

Portability does not erase legitimate capability differences. Unsupported
operations must degrade explicitly instead of being simulated or silently
claimed.

Operational managers are replaceable adapters, not the portable contract.
CC Switch may provide source, installation, projection, update, backup, and
restore operations where supported; another consumer may use its own manager
or host-native mechanism. The portable core describes desired state,
invariants, evidence, fallback, and recovery without requiring one manager's
database, release cadence, command surface, or UI.

Authorization is likewise host-owned rather than dialog-shaped. A host adapter
may bind approval dialogs, permission rules, Hooks, policy files, or another
native enforcement mechanism, but it must expose the effective authority and
verification boundary without pretending unsupported controls exist.

A host-local calibration probe is not a product adapter and must not define a
portable lane from one Agent's artifact shape. Portable contracts define the
outcome, authority, observability, lifecycle, fallback, and claim boundary;
thin host adapters translate only the unavoidable execution edge. A targeted
adapter may remain honestly host-specific. A generalized product claim needs
evidence from materially different host mechanisms, while unsupported hosts
must negotiate or degrade explicitly rather than inherit another host's Hook,
rule-file, or control-plane assumptions.
