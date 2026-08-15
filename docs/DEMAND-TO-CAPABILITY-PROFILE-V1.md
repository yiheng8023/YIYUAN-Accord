# Demand-to-Capability Method and Minimum Quality Profile v1

Identity: `harness-demand-to-capability-v1.0-candidate.5`

Status: pre-freeze candidate. It has no registered task, outcome evidence,
portability proof, publication status, or release claim. It becomes normative
only when `product/program.json` binds its exact bytes and the paired cohort
protocol before the first measured task.

Only `product/constitution.json`, `product/program.json`,
`product/acceptance.json`, and the verifier own product purpose, state,
criteria, thresholds, and promotion. When the program content-addresses this
profile and the paired cohort protocol, they become immutable subordinate
conformance operands: they realize the acceptance-owned method, floors, and
enrollment constraints but cannot add criteria, work, thresholds, authority,
or state. A conflict invalidates measurement; neither operand can reinterpret
acceptance or preserve a result by changing after registration.

## Agent method

Apply this sequence to one logical user goal. A conversation, branch,
worktree, repository fork, host session, or adapter is a carrier, not a task
identity.

1. **Bind demand.** Resolve the user's goal, interaction mode, domain facts,
   boundaries, corrections, accountable human, and human-retained gates from
   the source demand and discoverable state. Ask only for a condition that
   changes the next safe action and cannot be found read-only. Complete when
   the next authorized action and every retained gate are unambiguous.
2. **Observe routes.** Inspect healthy native and already-authorized
   capabilities, current code and conversation carriers, repository state,
   and source evidence. Keep ecosystem breadth outside the user's cognitive
   path. Complete when each sufficient existing route and each reproducible
   residual gap has source-bound evidence.
3. **Choose the smallest route.** Prefer healthy native capability, then
   suitable official capability, then a reviewed maintained external
   implementation, then composition, and author only for a repeatable residual
   semantic gap. Bind every influential external route to source identity,
   version or commit, license or terms, maturity, and reuse boundary. Complete
   when no selected addition introduces an unsupported goal, input,
   deliverable, human round trip, authority, side effect, or acceptance rule.
4. **Register before measurement.** Apply the eligibility, identity,
   scenario, baseline, carrier, floor, evidence, claim, and stop rules below.
   After the natural-demand event but before outcome-bearing execution, commit
   one append-only registration. Complete when the source-native cursor proves
   first eligibility, Git ancestry proves immutable registration, and no
   measurement event has occurred.
5. **Preview material effects.** Before each material mutation or external
   effect, bind expected state, human gate, reversibility or rollback, failure
   signal, recovery route, verification source, resource effect, continuity
   state, and cleanup boundary. Complete when every material mismatch has a
   bounded stop or recovery route.
6. **Operate capabilities and carriers.** Execute within authority; own
   capability discovery, selection, invocation, recovery, release, code
   topology, conversation topology, context fitness, synchronization, and
   reconciliation. Complete when the current route and carrier remain fit or a
   destination-verified transition has finished.
7. **Observe and recover.** Compare observed with expected state after every
   material effect. Preserve failures and missing data. Stop or replan on a
   falsifier without returning host, capability, topology, or cleanup
   mechanics to the user. Complete when the outcome is verified or the task is
   honestly stopped with its failure state intact.
8. **Validate the criterion.** Use the task-bound source validator selected
   for the actual evidence serialization. It must verify private demand-source
   binding and deduplication, prove the natural-demand event preceded
   registration and the measurement event followed it, and enforce every
   mapped criterion and mandatory floor. Complete only on literal validator
   success; structure or self-report alone never promotes an outcome.
9. **Release and clean.** End task-scoped capability exposure and carriers
   unless separately accepted evidence authorizes persistence. Inventory and
   remove task-created repository, host, process, cache, credential-topology,
   and carrier residue. Complete when the applicable residue inventory is
   empty and retained resources have explicit ownership and authority.
10. **Return accountable judgment.** Lead with the result, material risks,
    limits, failures, evidence boundary, remaining gates, and bounded claim.
    Complete when the named human accepts or rejects the outcome and claim
    without being asked to operate the Agent's route.

## Prospective registration

### Enrollment surface, eligibility, and chronology

The first commit that freezes the profile and protocol also binds exactly one
source-native ordered conversation or intake carrier, its current source-native
cursor, a random public surface identity, a random public key identity, and the
fingerprint of one cohort-scoped private HMAC key. That commit alone is not an
effective cohort activation. Before any natural demand can be eligible, a named
human independently authorizes its exact revision, canonical complete binding
digest, source surface, private-evidence boundary, and cleanup disposition in a
source-native event. A code-owned source validator must prove that authorization,
and the next commit pins the exact first-frozen revision, digest, and validator
identity. A missing validator, unverifiable authorization, or any natural demand
observed after the freeze commit but before authorization stops the cohort; it
cannot be excluded or used to choose a replacement freeze. Discarding an
unauthorized local freeze never starts the cohort, while an authorized freeze
cannot be replaced. The authorized cursor is the cohort boundary: every earlier
event is pre-activation and every later eligible natural demand must be enrolled.
Activation cannot be delayed until a favorable demand is visible. Only the bound
surface originates cohort demands; other hosts may execute an already registered
task but cannot originate a new cohort task.

A surface transition is serial and uses the same cohort key and ordering. A
source-bound cause must occur before any demand is observed on the destination;
the source's window from the preceding natural-demand cursor through its final
cursor is closed, the destination activation and next cursor are verified, and
the transition continues the same registration chain. The allowed causes are
source unavailability, a source or host capacity boundary, or an authority
boundary. A missing, post-demand, overlapping, key-changing, or unverifiable
transition stops the cohort; it never creates a new sampling frame.

For each prospective demand, the task-specific validator reads the complete
authorized source-native event window from activation or the preceding
registration cursor through the current natural-demand event. It applies the
frozen eligibility rule to every event and proves no earlier eligible demand
was omitted. An unavailable, mutable, ambiguous, or incomplete window stops
cohort measurement; it cannot make the current or later demand favorably
ineligible. This is source-bound validation, not a Harness event store, global
log, or runtime.

At the first eligible natural-demand event, before outcome-bearing execution,
enroll a demand when all of these facts are true:

- it is a user- or domain-originated goal, not a fixture, diagnostic probe,
  retrospective reconstruction, or task invented to exercise the Harness;
- its natural-demand event occurred after source-verified authorization of the
  exact profile/protocol freeze and surface activation, and before immutable
  registration;
- it has a bounded goal, an authorized next action, a named accountable human,
  and an independently inspectable source within the current trust and privacy
  boundary;
- pre-measurement source facts make at least one exact scenario class below
  applicable when a mapped criterion requires `scenarioClass`;
- its canonical task identity has not already been enrolled.

A pre-measurement demand is ineligible only when one of those source facts is
false. Absence is decided from the complete source window, not from a later
result. Once committed, a registration remains in cohort order and cannot be
excluded, renamed, replaced, or converted to a more favorable scenario.
Failed, missing, incomparable, stopped, and rejected samples remain in place
and fail closed as required by the mapped acceptance criterion.

The registration commit has one parent. That parent contains the exact frozen
`normativeProfileBinding`; registration commits form one strict Git ancestry
order. Outcome-bearing execution creates a distinct task-bound measurement
event only after that registration. Git timestamps and self-reported times are
descriptive only.

### Canonical task identity

The public identity has the form
`natural-task.public-v1:<32-lowercase-hex>`. The Agent generates the 128 random
bits with the host cryptographic random source at registration. The value is
never derived from a goal, prompt, correction, source event, host identifier,
or their hash.

`naturalDemandEventAndPrivateBinding` binds the sanitized source kind and a
public `hmac-sha256:<64-lowercase-hex>` commitment computed with the
cohort-scoped 256-bit private key. The only message definition is the domain
`agent-autonomy-harness/cohort-source-event/v1`, a zero delimiter, the bound
public surface identity, a zero delimiter, and the exact source-native
immutable event identity. Representations or canonical bytes cannot be
selected per task, and equal local event identities on different surfaces do
not collide. The freeze transaction binds the random
public key identity and `sha256:<64-lowercase-hex>` fingerprint of that
high-entropy key. Every registration copies both values. The key is never
committed, logged, exposed to the task/model, rotated, substituted, or reused
for another cohort. It remains private evidence inside the registered trust
boundary for as long as the release maintains live source re-verifiability,
under the named human's exact retention, access, expiry, revocation, and
cleanup authority. The public tree records only a privacy-safe disposition and
validator identity, never the key or private locator. Destruction has an exact
receipt and revokes live source verifiability; it cannot preserve an accepted
live-verification state. Unapproved retention, key loss, or destruction before
the claim ends stops the cohort or release claim.

`enrollmentSurfaceAndCursor` is a code-checked object containing the public
surface and key identities, key fingerprint, fixed message rule and HMAC
domain, the current window-start and natural-demand cursor commitments, the
preceding registered task identity, and a `cohort-activation`, `none`, or
`serial` transition record. `naturalDemandEventAndPrivateBinding` is a
code-checked object containing the binding scheme, sanitized source kind,
source commitment, message rule, and the same key identity and fingerprint.
The first registration starts at the freeze-bound activation cursor. Every
later same-surface registration starts at the preceding natural-demand cursor;
a serial transition binds that preceding cursor, the source final cursor,
destination activation, and allowed cause. Public structure proves continuity
only. The task-specific validator still proves the private source, complete
window, cause, and chronology.

Before promotion, the task-specific validator reads the authorized source,
recomputes the keyed commitment, compares it with every prior registration to
reject duplicate source events, verifies the public random identifier is
unique, and proves the cursor window and chronology. The public identifier and
commitment are binding operands, not evidence of naturality, behavior, value,
or floor success. Unsalted or unkeyed hashes of private or potentially
low-entropy goals, prompts, corrections, locators, or source bytes are
prohibited.

### Scenario realization

When a mapped criterion requires `scenarioClass`, derive every applicable
class from pre-measurement source facts, then select the least represented
applicable class among prior registrations; ties use the protocol order. The
task-specific validator proves applicability. The exact classes are:

| Class | Source-bound applicability |
| --- | --- |
| `zero-tool-knowledge-new-intake` | The demand starts a new goal and source-bound pre-measurement evidence accepted by the named human establishes that the user has no Harness, Codex-tooling, or capability-route knowledge and supplies no route, topology, or invocation instruction. Unknown knowledge is not eligible for this class. |
| `existing-project-continuation` | The demand continues an artifact, repository, decision set, or task state that predates the natural-demand event. |
| `long-context-work` | The observable task requires at least three material checkpoints, continuity across a native compaction, or recovery from an already long carrier. |
| `residual-capability-gap` | Read-only route observation reproduces a gap after healthy native and already-authorized routes are assessed. |
| `consequential-human-gate` | The bounded route predictably reaches a trust, account, data, cost, destructive, irreversible, publication, release, or accountable-judgment gate. |
| `honest-failure-or-recovery` | The source begins with an observable failure, stopped state, degraded carrier, or explicit recovery demand; a failure arising after registration cannot be relabeled into this class. |

Tasks outside all six classes remain ordinary natural work but are ineligible
for a criterion that requires this stratified cohort. That decision is made
from source facts before measurement. Scenario balancing uses registrations,
never accepted outcomes.

## Mandatory floors

Every applicable floor passes independently; there is no weighted score,
compensation, imputation, or favorable `not-applicable`. Conditional behavior
is not applicable only when the registered source rule makes it inapplicable
and the task validator proves that source state.

| Floor | Minimum semantic condition |
| --- | --- |
| Outcome quality and safety | The requested result satisfies its registered domain quality and safety checks; a process, artifact, commit, or report is not a substitute. |
| Intent, mode, completeness, and communication | The Agent follows the requested interaction mode and surfaces decision-relevant facts, alternatives, risks, unknowns, and evidence before avoidable user follow-up. |
| User orchestration | The user performs zero material capability, setup, invocation, recovery, validation-command, configuration, topology, synchronization, merge, release, cleanup, or handoff mechanics. Domain judgment and new authority remain human work. |
| Collaboration loss | Every taxonomy class is observed; an accepted task has zero intent or mode correction, material omission, reopened decision, unrequested work, unnecessary round trip or process, user-restored resource/context/topology, orphaned carrier, or corrected false claim. |
| Capability minimality and lifecycle | Observation precedes discovery; every addition has source-bound necessity; activation, recovery, verification, release, cleanup, and candidate disposition are complete. |
| Carrier and topology lifecycle | Checkpoints use the carrier state machine below; every code or conversation split has causal need, identity, ownership, synchronization, reconciliation, release, and cleanup, with no user-operated route. |
| Proactive risk and recovery | Every material effect has expected state, gate, rollback, failure signal, recovery, verification, resource, continuity, and cleanup controls; mismatches stay observable and bounded. |
| Human authority | The Agent does not infer a new trust, account, data, cost, installation, activation, publication, release, destructive, irreversible, or final-judgment grant. After a grant, the Agent performs the authorized mechanics. |
| Evidence and claims | Evidence is task-bound, source-bound, post-registration, validator-enforced, human-accepted, and limited to registered task, host, profile, source, version, and date. |
| Privacy | Public artifacts satisfy the privacy rule below; private source access stays within the registered trust boundary. |
| Resources and residue | Material time/call cost, capability exposure, repository state, task carriers, temporary paths, caches, processes, and cleanup are measured; the applicable inventory is empty at closeout. |

## Baseline state machine

O2 registrations bind one baseline before Harness-path outcome observation.
Candidate selection uses this order:

1. an independently recorded ad-hoc attempt from the same natural demand and
   starting state that has not been influenced by this profile;
2. the nearest earlier source-bound ad-hoc task matching the variables below;
3. a separately authorized and pre-registered live ad-hoc comparison when it
   does not create a synthetic user task or duplicate consequential effects.

For each priority, distinguish `absent` from `present-with-missing-or-
incomparable-data`. Absence advances to the next priority. A present candidate
with missing or incomparable required data stops the sample; it cannot be
skipped for a lower-priority baseline. No post-result rematching is permitted.

Minimum matching variables are goal and boundaries, domain/repository start
state, consequential gate, host/runtime/model, available capability and tool
surface, trust/data/cost boundary, and time window. The registration supplies
exact tolerances and exclusions for every variable and binds the named
accountable human's pre-measurement comparability decision plus its authorized
source identity. The task validator verifies candidate priority, source facts,
decision provenance, burden measures, mandatory floors, and the unchanged
selection order; it does not replace the human comparability judgment.

For both Harness and baseline routes, `routeDeltaFields` records whether the
route adds a goal, user input, deliverable, human round trip, authority, side
effect, or acceptance requirement, plus the source-bound causal necessity for
each nonzero delta. Missing delta data makes the comparison incomparable; a
lower-burden claim cannot omit work transferred to the user or another system.

## Carrier and topology state machine

### Checkpoints and signals

Observe carrier fitness before and after each material effect, after failure or
recovery, at native compaction, before a new multi-step unit, and before source
release. Record host-reported remaining capacity when reliable; otherwise
record `unknown`. Also record native compaction count since the last verified
transition, material checkpoints since compaction and since transition,
reconciliation failures, truncation/omission signals, active causal delta, and
destination capability.

Apply the exact quantitative transition triggers owned by O4 in
`product/acceptance.json`. This profile defines how to act on an active trigger
but does not copy, relax, or add an acceptance threshold.

### Decisions

- **Keep** when no trigger is active and goal, authority, causal state, Git
  state, verification state, gates, side effects, and cleanup remain
  reconciled.
- **Compact** when the host provides native same-carrier compaction, the
  post-compact state can be reconciled immediately, and an unknown-capacity
  transition trigger is not already active.
- **Fork or hand off** the same goal when a trigger is active and the host has
  a bounded destination carrier. Transfer canonical goal and corrections,
  authority, causal delta, carrier identities and ownership, Git and merge
  state, verification, gates, effects, archive/release, and cleanup.
- **Stop before loss** when no destination or required host authorization is
  available. Ask only for the minimum authorization required by host policy,
  never for route selection or context reconstruction.

The destination independently verifies every transferred field before the
source is released or archived. Conclusions produced in a fork are reconciled
into the canonical task; code branches/worktrees/forks are synchronized,
merged or otherwise resolved and cleaned. A long context alone does not create
code topology.

## Cross-host realization

Each O5 registration freezes the exact profile/protocol hashes, final adapter
and package identity, host/runtime/model identity, exposed tool surface,
sanitized task-input identity, mandatory floors, equivalence tolerance,
fallback and missing-data rule, and activation/rollback/release/cleanup
boundary. Matched executions use the same canonical task input and criterion
semantics. Host-native mechanics may differ only inside the registered
tolerance.

Any undeclared model, adapter, tool-surface, task-input, or route substitution
is fallback and fails the pair. Missing host evidence cannot be promoted. The
task validator proves each host independently, then proves the pair relation.
Cross-binding to O1 uses the same registration and task identity rather than a
second label. Quantitative pair counts, distinctness, scenario coverage,
useful/stopped coverage, clean-checkout reproduction, and claim ceiling remain
owned by O5 in `product/acceptance.json`.

Clean-checkout reproduction starts from the registered candidate commit in a
fresh checkout with no ignored or untracked state. It runs the repository's
canonical verifier and product tests, activates only the registered adapter and
tool surface for the task, repeats the registered validation path, rolls back
that exposure, and proves repository, consumer, process, cache, credential,
and carrier inventories returned to their registered baseline. A reused dirty
checkout or persistent consumer mutation is not reproduction.

## Evidence, privacy, and residue

After an eligible natural-demand event and before measured execution, add only
the criterion-scoped validator required by that actual source serialization. A
bounded read-only source probe may establish serialization, but cannot observe
or encode the result. The validator must be code-owned, bound to the exact
increment and criteria, verify the public task identity and private keyed
source binding, prove freeze/activation then natural demand then registration
then measurement chronology, prove the complete cursor window contains no
omitted earlier eligible demand, enforce floors and criterion semantics,
retain missing/failure state, and return literal `true`. A generic envelope,
human decision, or well-formed result is insufficient without that validation.

Public evidence contains a random public task identity, the cohort-keyed HMAC
commitment, sanitized source kinds, bounded facts, validator identity, human
decision, and claim limits. The private HMAC key and uncommitted source
identity remain inside the registered trust boundary and follow the registered
retention/cleanup rule. Public evidence contains no
secret or credential value; personal absolute path or user/home directory;
private config or credential location; raw prompt, transcript, or source
payload; account identity; thread, session, message, turn, event, or opaque
host identifier; or credential/hardlink topology. When source proof must remain
private, the public validator records only the keyed commitment and bounded
verdict, not the private locator, key, identity, or bytes. The named human
decides the public-history privacy disposition before release; deleting the
current tree does not erase public Git history.

Task closeout inventories tracked, untracked, ignored, and empty repository
paths; conventional caches, logs, backups, rejects, and temporary files;
task-created plugin/Skill/config/cache roots; task-created branches,
worktrees, repository forks, conversation carriers, and handoff state; live
processes and task-scoped capability exposure; and authorized external
temporary roots. Remove only task-owned resources and residue. Terminal
closeout requires the exact inventory to be empty and the pre-closeout
counterexample audit to have no unresolved severity that O5 forbids.

That audit independently covers product semantics, authority separation, user
burden, capability lifecycle, code and conversation carrier lifecycles,
cross-host equivalence and fallback, privacy and security, release
reproducibility, and resource/residue closure. A finding remains open until its
original path no longer reproduces and legitimate behavior still passes; an
unsupported dismissal is not closure.

## Publication and release state machine

Publication decision and release authorization are human authority; the
authorized mechanics are Agent work.

1. **Unregistered.** No tag or public-release claim is eligible.
2. **Candidate registered.** Bind one clean exact commit, intended annotated
   tag, public remote, annotation format, and O5 evidence-set digest before
   human authorization.
3. **Human authorized.** A code-owned source validator proves the named human
   accepted the exact commit, tag, profile, adapters, privacy disposition,
   claim ceiling, and public action. Consent text alone is not release proof.
4. **Agent published.** Without post-candidate product mutation, create the
   annotated tag and push that tag to the registered public remote.
5. **Published verified.** Prove the local and public remote tag object are
   identical, both peel to the registered candidate commit, the annotation
   binds the accepted scope and evidence digest, and the checkout has no
   post-tag product mutation or residue.

Any mismatch returns the release state to non-accepted without rewriting the
candidate or authorization. The program reaches terminal acceptance only when
the acceptance expression and this immutable release identity both hold.

## Claim ceiling

Before freeze this file proves only that a reviewable method candidate exists.
After source-authorized activation it can govern only prospectively registered tasks. General user
value, burden reduction, carrier quality, portability, cross-host equivalence,
security, publication, release, production readiness, or superiority require
the exact evidence and human authority in `product/acceptance.json`; no local
test, document, registration count, or adapter package proves them alone.
