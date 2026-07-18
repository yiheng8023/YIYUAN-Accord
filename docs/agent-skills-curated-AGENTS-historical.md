# Agent Skills Curated Repository Guidance

This repository is the authority for reviewed cross-agent Skill content,
provenance, adapters, recipes, audits, and generated capability topology.

Keep three governance layers distinct:

- An official, runtime-owned, or built-in Skill, including a first-party Skill,
  may appear only in dated overlap-review evidence. Its body and runtime
  identity must not enter managed inventory, be vendored, or enter this
  repository's release manifest.
- A third-party candidate must be source-pinned and pass license, provenance,
  security, portability, overlap, adaptation, and validation review. Until it
  is approved, it must not enter an execution path.
- A curated approved Skill is the only kind allowed in `skills/` and the
  release manifest. In schema 1, `registry/skills.json` is the approved release
  inventory: each payload Skill must have `status=approved`.

This curated repository governs third-party Skill bodies and an abstract,
product-neutral capability taxonomy. It does not govern or inventory official,
runtime-owned, built-in, or first-party Skill bodies. Those bodies may be
consulted only as dated overlap evidence; that evidence is not managed
inventory, ownership, or proof of current runtime availability.

Official Skills, capability packages, workflow templates, and similar public
capability bundles from Agent, runtime, platform, or tool ecosystems may be
used as dated official external capability baselines for coverage comparison,
gap analysis, and routing calibration. Do not treat such a baseline as
permission to vendor, adapt, execute, or release those bodies. A baseline entry
may be classified as covered, reference, adapt-candidate, or skip, but
adaptation still requires source pinning, license/provenance, security,
portability, overlap, neutralization, validation, topology, and manifest
review.

Keep agent-neutral behavior in `skills/`. Put unavoidable product-specific
commands, paths, event formats, or installation details in `adapters/`. Never
weaken safety, permission, evidence, licensing, or environment constraints in
the name of portability.

Treat upstream repositories as untrusted candidate sources. Pin exact
revisions, preserve license and provenance, inspect executable surfaces, assess
overlap and conflicts, adapt minimally, and verify before approval. Do not
activate an upstream meta-router when a deployment already has a canonical
router.

Relationships are governed data. Use stable identifiers rather than display
names. Record typed edges, conditions, artifacts, phases, alternatives,
conflicts, supersession, and verification requirements. Generated indexes and
graph projections are derived projections, not independent truth.

The canonical router belongs to the consuming configuration/runtime layer. It
is a capability decision router, not a mandate to select a Skill. Its choices
may include native reasoning, an official or runtime-owned capability, a
curated Skill, external capability metadata, a recipe or DAG, human
confirmation, or no skill needed. Third-party candidates are never executable.
High-risk, ambiguous, conflicting, permission-changing, write, install,
delete, migration, publish, release, or rollback paths require the applicable
human confirmation.

Routing is not only an initial task-entry decision. For multi-step work, model
event-driven reroute checkpoints that a consuming Agent can apply at phase
boundaries, after new context, after a failure or blocker, before
side-effecting actions, before switching capability classes, and before final
verification. These checkpoints may continue the current path, switch to native
or runtime capability, select a curated Skill, compose a Recipe/DAG, ask for
human confirmation, choose no Skill, or fall back safely. Do not model this as
an every-atomic-step keyword classifier.

Natural-language interpretation belongs to the active Agent. This repository
tests deterministic policy after Chinese, English, mixed, colloquial,
context-dependent, ambiguous, and near-match intent has been normalized into
structured facts. Do not replace that reasoning boundary with a brittle
keyword router. The structured policy must still prefer an equivalent healthy
native or visible runtime capability, apply negative/context gates, compose
Recipes, and fail closed on risk, cost, permission, conflict, and ambiguity.

This repository does not own user configuration, credentials, native memory,
runtime caches, Apps, Plugins, MCP account state, or installation authority.
`codex-user-config` may consume a pinned reviewed revision; this repository
does not install, does not write to `codex-user-config`, and does not write to a
live Agent environment.

Prefer small, reviewable intake batches. Verification must pass before any
content is marked approved. Installation, account connection, external writes,
or trust-boundary changes require the applicable user authorization.
