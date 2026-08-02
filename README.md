# Agent Autonomy Harness

English | [简体中文](README.zh-CN.md)

An agent-neutral autonomy, collaboration, and capability-orchestration harness.
Its north star is to move Agent learning, capability selection, resource
scheduling, context continuity, and engineering coordination out of the user's
head so the user can focus on creation, decisions, and bounded authorization.

## Decision card

- **Current state:** research and falsifiable proof; no host-neutral runtime,
  broad candidate value, or residual self-authored gap is proved.
- **Current Skill authority:** active adapted third-party payload release: `0`.
  The inherited 19-Skill/40-file manifest is deprecated transition evidence;
  it remains hash-bound history, not a current install or update source.
- **Current operating boundary:** the portable decision contract, host-neutral
  adapter contract, and host-specific implementation are separate layers.
  CC Switch is one current operational adapter where supported, not the
  portable product contract. Native host authorization, lifecycle, and
  permission enforcement surfaces retain authority.
- **Current action:** build a bounded, source-preserving, inactive candidate
  pool from named CC Switch, official, and reviewed external sources; review
  exact revisions before a separately authorized manager transaction. Keep
  task-time activation minimal and task-scoped. Real-task Harness-versus-
  lightweight comparisons continue in parallel; self-author only after reuse
  and composition leave a reproducible residual gap.
- **Evidence archive:** [current plan](docs/strategy/RESEARCH-AND-POC-PLAN.md),
  [inactive Skill source pool](docs/strategy/SKILL-PORTFOLIO-INACTIVE-SOURCE-CANDIDATE-POOL-2026-08-02.md),
  [scenario matrix](docs/strategy/POC-SCENARIO-EVIDENCE-MATRIX.md), and
  [continuation](docs/operations/CONTINUATION.md).

## Current phase

This private repository was bootstrapped on 2026-07-18 from the complete Git
history of `agent-skills-curated`. The inherited capability-curation system is
preserved below as the first governed component and evidence base; it is not the
whole product identity.

Current work is research and proof, not a claim that every host already exposes
the required control surfaces. The first three proof lanes are:

1. context lifecycle -> timely repository-anchored handoff -> same-workspace continuation;
2. task topology -> branch/worktree judgment -> bounded execution and cleanup;
3. task-scoped MCP activation -> lease/idle release -> failure recovery.

Native and official capabilities are evaluated first, then maintained external
implementations, and only then residual-gap authoring. Host approval dialogs
are one form of the native host authorization and permission enforcement
surfaces; permission rules or equivalent host-owned mechanisms may serve that
role on other hosts. This project should minimize and respect those surfaces,
not replace them.

## Start here

- [Product north star](docs/strategy/PRODUCT-NORTH-STAR.md)
- [Research and PoC plan](docs/strategy/RESEARCH-AND-POC-PLAN.md)
- [Continuation handoff](docs/operations/CONTINUATION.md)
- [Bootstrap authority record](registry/agent-autonomy-harness-bootstrap-2026-07-18.json)

Run `python -B scripts/verify_bootstrap.py` to verify the new repository identity
and migration anchors.

---

## Inherited capability-curation component

A public-safe, cross-agent authority for reviewed Skill content, provenance,
governance evidence, capability topology, and deterministic release manifests.

## Repository Role

This repository governs reusable Skill assets from intake through an approved,
auditable release. It is an agent-neutral producer for downstream consumer
configuration lanes. Codex and Claude are the currently characterized consumer
examples, but their evidence states differ: Codex has current pinned static
consumer-repository evidence with live-state gaps, while Claude remains a
conceptual chain example here.
Neither is a current supported mapping yet, and neither defines the boundary of
the model. Public readers should start from the public-safe
templates `codex-user-config-template` and `claude-user-config-template`,
which demonstrate a broader pattern for agent-environment migration, cloud
sync/backup, verification, and restore without proving current consumer state.

## What This Repository Provides

- Source pins, licenses, provenance, review decisions, and exact upstream
  identity for current third-party candidates.
- Legacy adapted Skill bodies under `skills/` as deprecated transition evidence.
- Security, portability, overlap, lifecycle, and conflict evidence.
- Authoritative registries for Skills, capabilities, relations, conflicts, and
  recipes.
- Deterministic generated projections and a schema-1 release manifest.

The inherited release contains 19 Skills and 40 files: 5 adapted from
`addyosmani/agent-skills`, 13 from `mattpocock/skills`, and 1 from
`kepano/obsidian-skills`. It is deprecated transition evidence because those
payloads were neutralized or generalized. The current policy does not rewrite
third-party Skill bodies. The exact legacy manifest remains retained only for
history, provenance, migration, and rollback analysis.

## Strategic Positioning

Reviewed Skills are the first terminal MVP in an independent, bounded
resource-governance flow. They are a low-burden, cross-Agent entry point that
can carry guidance, resources, scripts, and deterministic checks for internal
and external consumers. They are not the only possible terminal and do not
constrain upstream discovery to Skills.

The repository is multi-domain. Human-AI collaboration shortfalls are one
evidence-backed demand lane, not the repository's whole mission. Its stable
operating rule is reuse before build: establish the demand, compare native,
official, runtime, single-Skill, composed-Skill, and other Harness alternatives,
then prove a residual gap before authoring any repository-owned capability.
Third-party bodies remain upstream-owned and unchanged. Discovery
volume, popularity, or an old draft is not gap evidence.

The intended external-brain outcome is decision-ready rather than inventory
heavy. Consumers should receive a small, governed set of routes, alternatives,
conflicts, evidence limits, and recheck signals instead of repeatedly
enumerating unknown Skills. This reduces selection, routing, context, and
maintenance burden so the human can concentrate on creation and decisions; it
does not claim to raise a model ceiling or prove identical behavior across
Agents.

The stable process is a dependency graph, not a mandatory linear conveyor:
consumer projection is an optional branch, lifecycle metabolism is
cross-cutting, and standards extraction is conditional on repeated evidence.
Public discovery, community submissions, dated research corpora, and other
read-only source signals may be broad. This repository requires bounded demand,
a baseline, an exact source pin, review, and acceptance before any signal can
affect a curated decision. Program control and Round 02 closeout both have
explicit owner acceptance events. Round 02 is closed; the Round 03
capability-survey rebaseline is accepted and the bounded read-only survey is
active behind its demand-and-baseline sequence gate. The current initiative is
the capability survey and residual-gap proof phase.

Reliability is layered rather than text-only: instructions and rules may route
to Skills and Recipes; deterministic scripts, schemas, and validators cover
machine-checkable behavior; consumer-owned controls and project-owned hard
standards remain higher-authority integration surfaces. Current modes, fields,
and review checks are working hypotheses and observation protocols, not hard
standards. Standard-candidate work is deferred until value repeats across
independent sources, Agents or hosts, task classes, and real feedback cycles,
with net benefit and separate authority. This repository does not admit,
publish, or install project hard standards. Consumer
configuration repositories are temporary consumption, validation, and feedback
surfaces for this purpose, not the long-term carrier for research or standards.
The pinned human-AI collaboration-shortfalls corpus in
`YIYUAN-CALIBRATION` is read-only candidate, evidence, and research input.
CALIBRATION is not Skill or Manager product authority. Standard admission and
final carriage remain with the applicable project authority.

The inherited adapted release is deprecated and is not current coverage of
human-AI collaboration shortfalls. The current characterized consumer path uses CC
Switch where supported for operational source, install, update, distribution,
backup, and restore management. It is a replaceable consumer adapter, not a
portable Harness dependency or universal target operating model. This is not a
claim that the existing pool has already been migrated: a 2026-07-18 read-only
audit found 43 active CC Switch targets,
42 local database rows, zero source-backed rows, and one missing row. The 19
legacy curated targets still exactly match this repository's adapted release.
The source-preserving pool acceptance is therefore partial pending per-Skill
migration review and separately authorized migration evidence. This repository
keeps external payloads unchanged by default and owns safety,
quality, superiority, overlap, redundancy, provenance, and shortfall-coverage
decisions. Repository authoring begins only after a reproducible residual gap.
The first read-only migration review now gives 16 provisional upstream-exact
replacement candidates and three provisional retirement or supersession
candidates; it authorizes no live change.
A disposable CC Switch 3.17.0 source-management preview has now verified source
registration, source enablement, cross-source directory collision, selective
projection, backup, restore, and migration-snapshot contracts without changing
the real Skill trees. The stock Windows test boundary nevertheless bypasses
`CC_SWITCH_TEST_HOME` in five Skill-service paths; the full 7/7 result required
a diagnostic-only correction in `C:/tmp`. Acceptance therefore remains partial,
and no real source-backed migration or network update is claimed.
A later loopback update fixture verified v1 installation, v2 detection,
pre-update backup, replacement, and manual v1 recovery, while proving that
CC Switch's updater is not atomic. Its first run also exposed a second Windows
test-home precedence defect and briefly created exact test-only records and a
fixture payload in the live CC Switch store. Two identity-checked cleanup
transactions, each preceded by a consistent database copy, removed two test
Skill rows, one test source row, the payload, and its backups. Final checks
returned the live database to 248 Skill rows and five repository rows; the
corrected second run created no new live fixture residue. The first real canary is therefore gated on a
one-Skill preview, external before-state snapshots, readable backup, and an
explicit recovery rehearsal rather than automatic update.
The read-only canary decision package now selects `handoff`: it has the smallest
reviewed semantic delta, no executable surface, exact local/target hashes, and a
previewed uninstall-install rollback path. Execution was unauthorized at that
preview stage.
CC Switch persists only the moving `main` branch rather than the reviewed commit,
so the external revision pin must be rechecked immediately before any mutation.
The authorized local canary subsequently succeeded through CC Switch's own
source, backup, install, projection, and update-check paths. A first hash attempt
failed closed on Windows-checkout versus GitHub-archive line endings and restored
the local state; the accepted archive-byte result is source-backed and reports
no `handoff` update. Twenty unrelated `larksuite/cli` update signals were
observed and deliberately left untouched for gated review. The owner later
authorized normal WebDAV synchronization; CC Switch is running, reports a
successful local sync, and the source-backed `handoff` state remains intact.
Cross-device content equality and fresh-session invocation remain open.
The release has no growth quota: retention, composition, replacement,
supersession, deprecation, or retirement are as valid as addition when the
evidence supports them.
The earlier custom Manager work is preserved as historical experiment evidence
and is no longer an active product roadmap. The current machine objective is
source-preserving cross-Agent capability governance, with a separate retirement
record preventing historical work from becoming silent reactivation authority.

The dated 2026-07-18 public discovery projection records 188 unique public
source IDs and 20 balanced, source-pinned structure preflights. A separate
user-provided public star list adds five sources not present in that projection
without limiting discovery to the list. The five-source non-executing static
review is now complete. Its Loopy follow-up has also closed: all 18
deterministic contract fixtures passed, then an explicitly authorized,
exact-pinned disposable Agent trial completed 12/12 correct runs across native,
current-chain, and Loopy arms. Loopy added no false-positive loop selection, but
showed no material benefit over both baselines at proportionate context cost.
Its full body is therefore retained as reference-only and is not admitted; no
source or component is approved by this evidence.

The five sources newly contributed by the user list were also preflighted: one
stays a discovery index, two reuse older component-level reviews, one stays a
license-incomplete overlapping reference, and one is external Skill tooling
rather than an admission candidate. Exact extraction from the pinned index
found 20 direct-install coordinates, 16 new relative to the broad capture. Of
those 16, 14 currently resolve and two are stale; no possible successor is
substituted automatically. The PM Skills current-revision delta changes only
five lines across two Skill bodies, so the prior suite decomposition remains
usable while host-command changes stay separately held.

The ten-part Round 03 result package is now assembled for the selected demand
batch. Its 62-row STM/P/SG envelope now maps all 62 coordinates through eight
source-supported demand lanes; none remain unassessed, while whole demand-model
and longitudinal-evidence closure are still not claimed.
The added `STM-11`/`P1`/`P2`/`SG-01` intent-binding lane is currently covered
by proportional native, current-chain, curated, recipe, runtime, fallback, and
human-authority paths, so it triggers neither external discovery nor authoring.
The added `STM-20`/`P9`/`SG-05` authority lane separates advisory guidance,
host runtime enforcement, and accountable authority; its current paths likewise
support no residual Skill or Hook gap.
The added `STM-07`/`P4`/`SG-03` premise lane keeps challenge proportional,
document grilling opt-in, and open or divergent work on a native fast path.
The final `STM-09`/`P17`/`P20`/`SG-10` lane separates immediate assistance,
longitudinal cognition, live monitoring, maintainer learning, and anti-accretion.
The package is
therefore partial, not survey closure: it supports no residual gap, candidate
admission, repository-authored Skill or Hook, or hard-standard extraction. The
Loopy behavior gate has now been executed and resolved reference-only. The next
gate is to reconcile the complete selected coordinate envelope while keeping
demand-model, longitudinal, production, and cross-host evidence limits open;
closed lanes are rechecked only after their recorded triggers.

This repository applies **strict admission and free consumption**. Unchanged
upstream content does not imply whole-suite admission: multi-Skill sources are
reviewed at source, suite, component, and capability levels, and Hooks require
separate approval. Users remain free to add, remove, combine, fork, or modify
Skills; changed derivatives simply do not inherit the original curated digest
or verification automatically. The Harness stays proportional through open,
assist, and guarded postures, with native reasoning, no Skill, no Hook, and no
additional structure all remaining valid outcomes.
Any future residual-gap repository-authored Skill or Hook must adapt
transparently to task, risk, permission, host capability, user posture, and
feedback without hidden self-modification, permission expansion, or automatic
publication.

Dynamic MCP and collaboration-topology control is now a dated research gap,
not an implementation commitment. Codex already exposes startup-time standalone
and plugin MCP enablement plus tool allow/deny filters, so those native controls
must be evaluated before authoring. Mid-session hot switching, unloading an
already-running MCP server, and exact context/compaction telemetry remain
unproven. The portable instruction and checkpoint contract stays here; the
owner-specific Codex realization belongs in the private consumer configuration.
A public consumer configuration should not maintain a third handwritten copy;
any later public form should be a sanitized generated non-authoritative
projection.

The strategic objective-to-acceptance-to-verification-to-evidence mapping is
`registry/program-acceptance-map.json`. Partial or dated evidence remains
partial or stale; a green repository verifier does not prove current live Agent
state.

## What This Repository Does Not Own

This repository does not own user configuration, authentication, runtime
memory, Plugins, Apps, MCP account state, installation permissions, or live
environment state. It does not install, does not write to
private consumer configuration repositories such as `codex-user-config` or
`claude-user-config`, and does not write to a live Agent environment.
Any cross-repository write, including a possible CALIBRATION handoff, is a
separate explicitly authorized transaction rather than an implicit side effect
of this repository's verification or release workflow.

Official, runtime-owned, or built-in Skill bodies remain environment-owned.
This curated repository governs third-party Skill bodies and an abstract,
product-neutral capability taxonomy. It does not govern or inventory official,
runtime-owned, built-in, or first-party Skill bodies. They may appear only in
dated overlap evidence; that evidence is not managed inventory, repository
ownership, or proof of current runtime availability.

Official Skills, capability packages, workflow templates, and similar public
capability bundles from Agent, runtime, platform, or tool ecosystems may be
recorded as dated official external capability baselines. Baselines are used
for coverage comparison, gap analysis, and routing calibration; they are not
managed inventory. This repository uses baseline matrices to decide
`covered`, `reference`, `adapt-candidate`, or `skip`; it does not blindly
import official repositories and does not claim full coverage until workflow,
resources, scripts, trigger description, and output standard have been checked.
The current first baseline instance is
`docs/anthropic-official-skills-coverage.md`.

## Relationship To The Paired Repository

The dependency and authority direction is one-way:

```text
Current public reader entry points
  codex-user-config-template
  claude-user-config-template
    -> show public-safe structure, placeholders, and user-owned setup guidance

Current private consumer repositories
  codex-user-config
  claude-user-config
    -> may consume a pinned reviewed revision and release manifest
    -> plan, back up, install, verify, and roll back managed Skill paths

agent-skills-curated
  -> owns reviewed Skill content, provenance, topology, conflicts, policies,
     audits, and deterministic release manifests
  -> does not write back to private consumer configuration repositories or
     live Agent environments
```

The public templates do not contain the maintainer's private configuration,
memory, account assumptions, preferences, or local machine state. They are the
public way to understand the consumer-side pattern. A private configuration
repository is not assumed to be a current downstream or supported consumer
without a dated consumer-owned mapping and verification record.

The consumer-side pattern is generic even when a concrete implementation is
agent-specific. Future agents or toolchains can add their own public template
and private overlay once their runtime files, settings, memory, hooks, tools,
permissions, and restore behavior have been mapped.

Consumer repositories do not take ownership of third-party Skill-body
governance. This repository does not take ownership of consumer-side
installation or runtime integration. Each consumer owns its own integration;
this repository stays agent-neutral and binds to none.

A real user configuration repository may contain personal information,
preferences, memory snapshots, account assumptions, local restore policy, or
private operational choices. It should remain private unless deliberately
sanitized. If a public configuration example is useful, create a separate
public template such as `codex-user-config-template` or
`claude-user-config-template`, with placeholders and user-owned setup guidance,
not a copy of the private repository.

Discovery sources, configuration repositories, public templates, this
governance repository, and CC Switch each retain a bounded role. This
repository owns candidate review, routing, composition, admission metadata,
and self-authored residual-gap releases; upstreams own third-party bodies. CC
Switch provides operational Skill management for supported Agents; consumer environments own their
instruction, Skill, Hook, and live-loader behavior.

Shared Skills and their portable instruction/Skill/Hook/verification chain are
Agent-neutral authority here. They must not be consolidated wholesale into a
single-Agent consumer such as `codex-user-config`; that repository owns only
the Codex-specific installation, runtime, Hook deployment, and rollback adapter.

## Capability Layers And Routing

Three layers are deliberately noninterchangeable:

1. An official, runtime-owned, built-in, or first-party Skill may appear only
   in dated overlap evidence; neither its body nor runtime identity is managed
   inventory, vendored, or released here.
2. A third-party candidate remains exact upstream. Its source pin, license,
   provenance, security, dependencies, portability, overlap, maintenance, and
   validation are governed before a separately authorized manager transaction;
   its body does not enter this repository's current product release.
3. A repository-authored residual-gap Skill may enter a future active release
   only after necessity and admission close. The current active adapted third-
   party payload count is zero. `registry/skills.json`, `registry/routing.json`,
   and `release-manifest.json` retain the deprecated schema-1 transition release
   for historical verification only.

A repository-authored gap-fill is a candidate origin, not a fourth release
layer and not a platform/runtime/vendor first-party baseline. It remains
non-executable until a material residual gap, alternative comparison, design
provenance and licensing, security, portability, overlap, validation, and owner
approval have all passed the same curated-admission boundary.

The configuration-owned `capability-router` is a capability decision router,
not a skill-router. Its options include native reasoning, an official or
runtime-owned capability, a curated Skill, external capability metadata, a
recipe or DAG, human confirmation, or no skill needed. Third-party candidates
are not executable routing targets. High-risk, ambiguous, conflicting,
permission-changing, write, install, delete, migration, publish, release, or
rollback choices require human confirmation.

Routing is not only a task-entry decision. For multi-step work, consumers
should re-evaluate at event-driven reroute checkpoints: phase boundaries, new
context, failures or blockers, before side-effecting actions, before switching
capability classes, and before final verification. The routing projection
supplies deterministic policy input for those checkpoints; it does not require
per-step routing and does not prove live capability availability.

The `capability-router` is a characterized Codex consumer mechanism, not a
universal prerequisite or proof of current live loading. Consumer invocation
chains are Agent-specific. Claude Code is retained here only as a conceptual
direct-surfacing example until a dated official-source review, consumer-owned
inventory, precedence map, behavior probes, and backup/restore evidence exist.
Codex has historical partial evidence, not a complete current mapping. Other
agents' chains must likewise be mapped before this repository describes their
install, routing, or restore behavior.
This repository names mechanisms structurally and stays agent-neutral, open,
and compatible — it must not hard-code any single agent's chain.

Schema-2 runtime coverage is structurally product-neutral. A
`runtime-resolved` capability carries
`runtimeResolution: visible-capability-inventory`; it names the resolution
mechanism, not a product, vendor, owner, or assumed live capability. The
consumer must probe its currently visible, authorized capability inventory.

## Layout

- `skills/`: curated approved portable Skill content.
- `sources/`: immutable source locks, licenses, selection, and hashes.
- `registry/`: hand-maintained authority for topology and release inventory.
- `policies/`: intake, portability, security, overlap, and lifecycle rules.
- `audits/`: source-specific provenance and review evidence.
- `docs/decisions/`: accepted governance decisions that constrain future
  contract changes.
- `docs/official-external-capability-baselines.md`: general policy for official
  external capability baseline handling.
- `docs/anthropic-official-skills-coverage.md`: dated external baseline
  coverage matrix for the first official baseline instance.
- `docs/mvp02-preflight-readiness.md`: historical MVP-02 preflight record now
  consumed by bounded owner approval.
- `docs/mvp02-post-approval-execution-plan.md`: executed plan for the narrow
  post-approval adapted-draft step; stopped before release or runtime gates.
- `docs/mvp02-adapted-draft-review.md`: non-runtime adapted draft review
  evidence; not approved payload, not routing, and not live install.
- `docs/mvp03-release-or-routing-preflight.md`: next-gate preflight and
  approval request; not release, routing, manifest, or runtime approval.
- `docs/mvp03-release-or-routing-review-template.md`: template-only candidate
  review contract to use after owner approval; not a candidate decision.
- `docs/mvp03-release-or-routing-approval-request.md`: formal owner approval
  request for MVP-03 candidate review; now consumed by a bounded approval
  event.
- `docs/mvp03-release-or-routing-candidate-review.md`: candidate-specific
  MVP-03 disposition evidence; not approved payload, not manifest, not routing,
  and not live install.
- `docs/mvp03-release-routing-execution.md`: owner-approved follow-up gate that
  merges two candidates into existing approved Skill payloads, models
  `spec-driven-development` as a recipe/routing projection, and hands runtime
  install proof to the consumer repository.
- `docs/mvp06-lifecycle-feedback.md`: lifecycle feedback from the verified
  consumer install, including radar dedupe metadata and the pause/observe
  decision before the next batch.
- `registry/program-acceptance-map.json`: stable strategic objective,
  acceptance, verification, and evidence relationships with honest current
  assessments.
- `docs/curation-program-plan.md`: machine-plan projection, strategic baseline,
  delivery lifecycle, and current stage-closeout reconciliation state.
- `docs/curation-harness-model.md`: continuous curation loop, first-terminal MVP,
  layered reliability, multi-Agent consumer, and standard-candidate boundaries.
- `docs/superpowers/specs/2026-07-15-production-capability-manager-design.md`:
  superseded historical custom-Manager design and bounded experiment lineage.
- `docs/cc-switch-source-preserving-skill-pool-strategy-2026-07-17.md`:
  current owner-accepted strategy that reuses CC Switch, preserves upstream
  Skill bodies, and reserves repository authoring for proven residual gaps.
- `docs/cc-switch-live-source-ownership-reconciliation-2026-07-18.md`:
  read-only live projection evidence showing operational CC Switch reuse but
  zero source-backed rows across 43 active targets, with migration still open.
- `docs/cc-switch-disposable-source-management-preview-2026-07-18.md`:
  disposable source, collision, backup, and restore contract evidence plus the
  stock Windows test-isolation limitation.
- `docs/cc-switch-disposable-source-update-and-recovery-review-2026-07-18.md`:
  loopback source update, non-atomic failure, manual recovery, isolation
  incident, exact cleanup, and revised real-canary gate.
- `docs/cc-switch-handoff-real-canary-readonly-preview-2026-07-18.md`:
  the selected one-Skill canary, exact before/target hashes, moving-branch pin
  limit, bounded ownership transition, acceptance checks, and rollback preview.
- `docs/cc-switch-handoff-real-canary-execution-2026-07-18.md`:
  the authorized local source-backed migration, fail-closed archive-byte hash
  correction, whole-database post-state audit, no-delta update check, and
  external-sync boundary.
- `docs/dynamic-runtime-control-gap-review-2026-07-18.md`:
  native MCP startup controls, unproven hot-switch/context telemetry, and the
  portable/private/public instruction-carrier boundary.
- `docs/legacy-curated-skill-source-migration-review-2026-07-18.md`:
  per-Skill read-only review of the 19 legacy derivatives, with 16 provisional
  upstream-exact replacement candidates and three retirement candidates.
- `docs/custom-manager-retirement-reconciliation-2026-07-18.md`: current
  product-neutral governance identity, historical Manager evidence retention,
  and the explicit reactivation gate.
- `docs/evidence-backed-release-evolution-reconciliation-2026-07-18.md`: no
  Skill-count KPI, valid retain/add/replace/compose/retire outcomes, and the
  current retain-and-monitor decision.
- `docs/layered-reliability-projection-reconciliation-2026-07-18.md`: verified
  smallest-sufficient layer roles and project-standard precedence at
  governance-projection scope, with runtime and standardization limits open.
- `docs/decision-ready-consumer-projection-evaluation-2026-07-18.md`:
  repository-fixture routing and structural-burden evidence, while dated
  consumer-owned verification remains explicitly open.
- `docs/github-repository-configuration-evidence-2026-07-18.md`: dated GitHub
  metadata, community-file publication boundary, sponsorship surface, enabled
  security settings, and zero-result CodeQL analyses for the recorded remote
  `main` revision without extending that claim to local unpublished work.
- `docs/adaptive-harness-source-suite-and-user-sovereignty-2026-07-18.md`:
  current strict-admission/free-consumption, selective source-suite review, and
  proportional open/assist/guarded Harness contract.
- `docs/round-lifecycle-contract.md`: reusable plan, execution, acceptance,
  and stage-closeout contract for iterative curation rounds.
- `docs/round02-candidate-review-2026-07-02.md`: round-02 candidate-specific
  source disposition evidence; not approved payload, not manifest, not
  routing, and not local runtime sync.
- `docs/round02-obsidian-adaptation-gate.md`: Obsidian sub-batch adapted draft
  gate; records open-format, CLI, and Defuddle dispositions without approving
  payload, routing, manifest, or local sync.
- `docs/round02-pm-execution-adaptation-gate.md`: PM AI-shipping and
  execution-document adapted draft gate; excludes analytics, market/GTM,
  discovery, legal/privacy, and script/tooling groups for separate review.
- `docs/round02-pm-analytics-adaptation-gate.md`: PM analytics and data-safety
  adapted draft gate; records analytics runtime-equivalence and synthetic
  data/SQL tooling dispositions without approving payload, routing, manifest,
  execution, or local sync.
- `docs/round02-pm-market-discovery-adaptation-gate.md`: PM market and
  product-discovery adapted draft gate; records strategy evidence and discovery
  research dispositions without approving payload, routing, manifest, external
  research, participant-data handling, or local sync.
- `docs/round02-pm-toolkit-boundary-adaptation-gate.md`: PM toolkit
  high-boundary adapted draft gate; records legal/privacy reference and
  personal-document/copyediting dispositions without approving payload,
  routing, manifest, legal/compliance claims, resume data handling, or local
  sync.
- `docs/round02-huashu-design-guidance-adaptation-gate.md`: Huashu design
  guidance adapted draft gate; records design-direction and brand-asset
  provenance dispositions without approving payload, routing, manifest,
  toolchains, bundled assets, external media generation, or local sync.
- `docs/round02-huashu-toolchain-media-adaptation-gate.md`: Huashu toolchain
  and media adapted draft gate; records HTML deck/export, voiceover/TTS, and
  bundled asset redistribution boundaries without approving payload, routing,
  manifest, dependency install, generated media, asset reuse, or local sync.
- `docs/round02-release-readiness-review.md`: Round-02 GitHub-stage readiness
  review; summarizes all 3 reviewed sources and 7 sub-gates without approving
  release payload, routing, manifest changes, publication, or local sync.
- `docs/round02-release-admission-review-template.md`: template-only contract
  for a future Round-02 release/admission review after owner approval; not a
  candidate decision and not approval for payload, routing, manifest, install,
  publication, or local sync.
- `docs/round02-release-admission-approval-request.md`: formal request for the
  smallest approval needed to enter Round-02 release/admission review; now
  consumed by a bounded approval event and still blocks payload, manifest,
  routing, live install, publication, and local sync.
- `docs/round02-release-admission-candidate-review.md`: candidate-specific
  Round-02 release/admission disposition evidence; not approved payload, not
  manifest, not routing, not publication, and not local sync.
- `docs/round02-release-execution-approval-request.md`: formal request for the
  next GitHub-only approved-payload and routing proposal gate; excludes
  adapter runtime work, reference-only promotion, rejected assets, publication,
  live install, and local sync.
- `docs/round02-approved-payload-routing-proposal-template.md`: template-only
  execution contract for the future Round-02 approved-payload/routing proposal
  after owner approval; not release execution and not local sync.
- `docs/round02-approved-payload-routing-proposal.md`: owner-approved
  GitHub-only execution record that admits open-format Obsidian payload, merges
  bounded Round-02 improvements, updates routing/manifest/generated
  projections, and still blocks local sync.
- `docs/round02-local-runtime-sync-approval-request.md`: formal request for
  the smallest bounded approval needed to sync the validated Round-02 release
  payload into local cc-switch, agents, and Codex Skill directories; not sync
  approval and not a local write.
- `docs/round02-local-runtime-sync-execution.md`: recorded local runtime sync
  execution; aligns cc-switch hashes to the Round-02 manifest and records
  Junction fallback links for agents and Codex.
- `docs/round02-stage-closeout-review.md`: requirement-by-requirement Round-02
  closeout decision package; recommends bounded round closure plus a pause for
  Round-03 rebaselining, but does not close the round or authorize a push.
- `docs/round02-stage-closeout-acceptance.md`: owner acceptance of the bounded
  Round-02 `complete` outcome, with residual risks and non-authorizations kept
  explicit.
- `docs/round03-capability-survey-rebaseline.md`: proposed evidence-first
  capability-survey replacement for the overlapping old Round-03 plan; now
  accepted for bounded read-only execution.
- `docs/round03-capability-survey-rebaseline-acceptance.md`: owner activation
  event projection and its explicit research/non-authorization boundary.
- `docs/round03-demand-coordinate-source-contract.md`: source-pinned STM/P/SG
  input, evidence-state, and promotion-firewall contract; it copies no external
  research body and does not itself authorize discovery.
- `docs/demand-coordinate-contract-reconciliation-2026-07-18.md`: reconciles
  eight source-supported demand records and all 62 bounded coordinate rows,
  verifies the bounded contract, and keeps demand-model exhaustiveness open.
- `docs/native-runtime-baseline-evidence-gap-reconciliation-2026-07-18.md`:
  keeps the baseline acceptance partial by separating the four-record dated
  single-host metadata baseline from four later review-only demand lanes.
- `docs/residual-gap-proof-evidence-gap-reconciliation-2026-07-18.md`: verifies
  the rejection firewall while keeping the positive residual-gap proof path
  partial and non-vacuous because no supported residual gap currently exists.
- `docs/starred-capability-source-discovery.md`: user-starred discovery surface
  triage for future candidate sources, baselines, indexes, and exclusions.
- `docs/public-skill-source-static-review-batch-2026-07-18.md`: first
  source-pinned, non-executing five-source static review and component
  dispositions.
- `docs/loopy-demand-level-alternative-comparison-2026-07-18.md`: native,
  current-chain, and exact Loopy-body comparison with a fixture-only next gate.
- `docs/user-starred-new-source-preflight-2026-07-18.md`: current metadata,
  historical-evidence reuse, drift, license, and next-gate triage for the five
  sources newly contributed by the user's public list.
- `docs/user-starred-index-stale-source-resolution-2026-07-18.md`: read-only
  resolution of two stale direct-install coordinates without silent successor
  substitution.
- `docs/user-starred-index-child-source-classification-2026-07-18.md`: clusters
  all 14 available pinned child sources, records zero demand-linked selections,
  and verifies the bounded-round marginal-yield stop rule without claiming
  ecosystem completeness.
- `docs/lifecycle-metabolism-reconciliation-2026-07-18.md`: verifies the
  repository-governed feedback return path from observed consumer evidence,
  plus a deterministic approved-Skill deprecation, migration, rollback, and
  retirement contract; observed live-consumer maturity remains open.
- `docs/cross-agent-claim-limit-reconciliation-2026-07-18.md`: records nine
  evidence classes with host, model, reasoning, loader, activation, permission,
  workspace, date, counterexample, and recheck limits; it verifies the claim
  firewall without claiming cross-Agent behavior or parity.
- `docs/consumer-mapping-evidence-gap-reconciliation-2026-07-18.md`: separates
  current-static-partial Codex evidence and conceptual-only Claude evidence
  from a current supported live mapping; its read-only shared-root snapshot
  records 73 Skills, 19 drifted old transaction claims, 27 lock-declared Lark
  Skills, and 27 foreign or unknown directories without claiming ownership or
  mutation authority.
- `docs/user-sovereignty-and-foreign-coexistence-reconciliation-2026-07-18.md`:
  verifies foreign-by-default ownership, explicit previewable reversible
  transitions, and no account or telemetry assumption while leaving
  multi-Agent operational coexistence evidence partial.
- `docs/pm-skills-current-revision-delta-review-2026-07-18.md`: exact one-commit
  PM Skills delta review separating five Skill-body changed lines from larger
  host-command changes.
- `docs/loopy-contract-fixture-protocol-2026-07-18.md`: 18 deterministic paired
  contract fixtures and the historical pre-authorization trial boundary.
- `docs/loopy-disposable-agent-trial-result-2026-07-18.md`: authorized 12-run
  native/current-chain/Loopy behavior comparison and reference-only decision.
- `docs/round03-intent-binding-demand-review-2026-07-18.md`: source-bound
  `STM-11`/`P1`/`P2`/`SG-01` comparison and current-path-sufficient decision.
- `docs/round03-authority-boundary-demand-review-2026-07-18.md`: source-bound
  `STM-20`/`P9`/`SG-05` layered authority comparison and no-residual-gap decision.
- `docs/round03-premise-challenge-demand-review-2026-07-18.md`: source-bound
  `STM-07`/`P4`/`SG-03` balanced challenge and open-divergence decision.
- `docs/round03-cognitive-offload-monitoring-demand-review-2026-07-18.md`:
  source-bound final coordinate lane with longitudinal and production limits.
- `docs/round03-capability-survey-result-package-2026-07-18.md`: the ten-part
  result package, decision-ready 62-row bounded coordinate envelope, open
  demand-model evidence, and explicit non-authorization.
- `docs/round03-complete-coordinate-envelope-reconciliation-2026-07-18.md`:
  deterministic 62/62 state reconciliation, four open-gap classes, and the
  evidence-triggered monitoring and recheck decision.
- `LICENSE`, `NOTICE`, and `THIRD_PARTY_NOTICES.md`: repository license,
  attribution, and third-party Skill notices.
- `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`, and `SECURITY.md`: public
  contribution, community, and vulnerability-reporting boundaries.
- `docs/license-policy.md`: layered licensing for repo-owned code, docs,
  generated projections, third-party Skill bodies, and official baselines.
- `docs/public-private-boundary.md`: public/private release boundary and user-config template guidance.
- `docs/sustainability.md`: cost posture, funding boundaries, and free-first discipline.
- `generated/`: deterministic derived projections, never a second truth source.
- `registry/routing.json` and `registry/scenarios.json`: legacy adapted-routing
  metadata and the 105-case structured policy corpus.
- `registry/skill-portfolio-current-authority.json`: current Skill
  payload and portfolio/activation authority.
- `registry/skill-portfolio-inactive-source-candidate-pool-2026-08-02.json`:
  bounded current source screening and the nine-source exact-acquisition cohort.
- `registry/skill-portfolio-exact-acquisition-static-preflight-2026-08-02.json`:
  exact clean acquisition, static dependency signals, and collision evidence.
- `registry/legacy-adapted-live-lineage-reconciliation-2026-08-02.json`:
  the 13 byte-exact deprecated live derivatives separated from six same-name
  Matt upstream Skills.
- `registry/cc-switch-legacy-adapted-thirteen-removal-event-2026-08-02.json`:
  the manager-backed subtraction event, retained backups, post-state, and
  cleanup boundary for those 13 derivatives.
- `registry/skill-portfolio-kepano-obsidian-adjudication-2026-08-02.json` and
  its manager-registration event: exact five-Skill review, three held-back
  install candidates, and repository discovery without installation.
- `release-manifest.json`: exact deprecated transition payload paths, sizes,
  and hashes.
- `scripts/`: validation and deterministic projection generation only.

## Verification

```bash
python -B -m unittest discover -s tests -v
python -B scripts/build_release_manifest.py --check
python -B scripts/build_topology.py --check
python -B scripts/simulate_routing.py --all
python -B scripts/verify.py
```

Verification covers registry contracts, references, generated parity, source
evidence, the exact manifest payload, input-bound routing projection, all 27
lifecycle nodes, and 105 deterministic adversarial scenarios. Natural-language
interpretation remains an Agent responsibility; the simulator verifies the
normalized policy decision and does not pretend to be a keyword classifier.
It does not install a Skill.

## Update Rules

Treat each upstream revision as a new immutable intake: pin it, preserve its
license and provenance, review executable surfaces, assess security,
portability, dependencies, maintenance, and overlap, then record the review and
manager-transaction decision without rewriting the payload. Candidate
dispositions are not runtime approval.

Official external capability baselines may be used for comparison, but license,
provenance, security, portability, dependency, overlap, and maintenance gates
still apply before use. Source-available or all-rights-reserved official content
remains reference-only unless a separate permission path is approved.

User-starred repositories may seed discovery, but stars are not approval. A
starred source may become an official baseline, third-party candidate, discovery
index, external capability metadata, reference-only evidence, or rejection.
It must not enter `skills/`, the manifest, generated routing projections, or a
live execution path until the normal intake process closes.

Historical discovery records may remain source evidence, but no discovery
source has a privileged admission path. Every candidate remains advisory until
intake, exact-source review, validation, topology/metadata update, and the
applicable manager/consumer authority close.

## Safety Boundaries

- Generated files are derived projections of registry truth.
- Candidate content or dated overlap evidence is never treated as installed or
  executable content.
- Cross-agent portability never weakens permission, safety, evidence, license,
  or real environment constraints.
- Installation, account connection, external writes, and trust-boundary
  changes remain consumer-side actions requiring applicable authorization.

## Public release posture

This repository is designed to be public-safe, but public visibility does not
weaken the release gates. Third-party redistribution boundaries, provenance,
private-overlay exclusion, and funding links remain owner-controlled release
decisions. Repository-owned code and governance machinery are Apache-2.0;
repository-owned documentation and public governance text follow the layered
policy in [`docs/license-policy.md`](docs/license-policy.md). GitHub Free is
sufficient for the current path; GitHub Team or Pro is only a future option if
private Actions minutes, organization governance, or team review needs require
it.

## Sponsor

If this project is useful to you and you would like to support continued
maintenance, source review, documentation, testing, and community work,
voluntary sponsorships are appreciated. Sponsorship is optional and does not
purchase support priority, admission, release decisions, governance exceptions,
feature commitments, or technical influence.

| WeChat Pay (CNY) | Alipay (CNY) |
| --- | --- |
| ![WeChat Pay QR code](https://raw.githubusercontent.com/yiheng8023/home-edge-bootstrap-public/main/docs/assets/sponsoring/wechat-pay.png) | ![Alipay QR code](https://raw.githubusercontent.com/yiheng8023/home-edge-bootstrap-public/main/docs/assets/sponsoring/alipay.png) |

For cross-border or other supported currencies, use the
[PayPal payment link](https://www.paypal.com/ncp/payment/LNTF8KXGJXMZY). Verify
the displayed recipient before confirming a payment. See
[Sponsoring](SPONSORING.md) for the complete boundary.
