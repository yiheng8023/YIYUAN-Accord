# Architecture

## Active post-v3.1 development successor

[The v3.3 consensus and plan](operations/PLAN-v3.3.md) owns current decisions,
source assumptions, duties, quality floors and non-linear procedures; its linked
acceptance view defines the criteria. [product/development.json](../product/development.json)
is the machine validation projection. Version 3.3 distributes only the applicable
OpenAI adaptation. Earlier releases and host observations keep their historical
identities; current implementation or documentation does not grant publication.

Begin design review with necessary user results and actual conditions, not
confidence in inherited assets. Goals and human decision authority constrain
effects; implementations and representations remain revisable. Machine-suited
queries, parallelism, state and automation need not imitate human workflows.
Judge them by effect, decision quality, total lifecycle burden and necessary
human intervention. Neither architectural elegance nor a passing lower-level
test proves that the premise or composition is sufficient.

### Responsibility before packaging

The inherited duties are coverage indexes, not thirteen modules or a fixed
sequence that every task must traverse. Allocate responsibility by its actual
execution and failure window:

| Work | Responsible means and activation | Required evidence |
|---|---|---|
| Task delivery, immediate correction and result verification | Accord owns faithful goal/authority propagation, applicability and result criteria; the active host Agent and supported tools supply reasoning and operations | Authorized actions, correct result and relevant post-state; a current correction must not wait for a cross-task learning pipeline |
| Continuity, recovery and resource exit | Available host controls or a declared composition with necessary state and an applicable surviving failure owner | Check relevant duties against the same execution/state change; in-place continuation need not hand off. An actual carrier/source transfer requires destination reconciliation before safe source release |
| User-authorized package lifecycle | Host lifecycle controls available before installation and after removal, plus any necessary independent compensation | Exact selected components, active state and residue; an absent Skill cannot execute its own unavailable recovery |
| Maintainer assurance and optional reusable learning | Product qualification or an authorized, useful persistence task, separate from ordinary use | Evidence appropriate to the claimed product effect, comparison or reusable correction; these activities are not required ceremony for every user task |

A necessary outcome survives retirement of a redundant implementation. An
unnecessary outcome needs an explicit revised commitment and dependent acceptance.
Unknown irrelevant state need not block safe work; unknown necessary state
cannot be silently promoted. Safety, functional and other applicable quality
floors cannot compensate for each other through an average score.

This allocation applies to every duty, not only adaptation. User decisions and
authorization remain user-owned. Accord must retain the policy, necessary state,
dependency checks and verification needed for its declared result. It may reuse
host reasoning, events, storage and execution, but must verify those dependencies
and respond when they cease to suffice. Machine-checkable consequential controls
need an actual delivered caller; prose or unused reference code is insufficient.
Customized settings and extensions are normal operating conditions. Reuse
compatible help and contain conflicts within their affected scope. Unknown or
broken host facilities require a specific unmet condition and feasible recovery
route, not blanket environmental blame or unconditional compatibility claims.
Open-source, noncommercial delivery retains the same agreed functional, quality,
recovery and maintenance standards; production readiness must be demonstrated.

Accord is open to surrounding ecosystems. Its middle or mixed-layer role is a
logical allocation, not a universal proxy. Resolve collisions by verified source,
applicable scope, current user authorization and actual host limits. Installed
extensions and their output cannot promote themselves to user authority. A Hook
can guard supported execution points; do not extend that claim to other paths or
confuse a model interpreting conflict advice with deterministic enforcement.

Context exposure is part of that responsibility. Keep controllable standing
guidance small and load applicable detail on demand. Distinguish a capability
catalogue from full instructions, tool output and retained history. Resolve
instruction conflicts through the actual instruction hierarchy and applicable
authority; reconcile factual disagreements with evidence. Disabling a capability
does not retract earlier text or repair decisions already influenced by it.
Measure reduced exposure alongside discovery, task results and necessary state
integrity. The recorded native CLI budget probe demonstrates a smaller rendered
catalogue, not a universal budget or improved Agent behavior.

The Agent owns the choice, activation, operation and release of applicable
capabilities within bound authority. Users can state outcomes without knowing
buttons, worktrees or conversation topology. Prefer supported background APIs,
CLI and bounded configuration interfaces; verify actual availability and all
effects before acting. A visible control alone does not prove a callable route.
Temporary worktree use includes result integration and release of unneeded owned
allocations, even when host automatic cleanup is off. Preserve active dependents
and explicit retention decisions. Native operations can combine effects: the
observed Desktop settings deletion handler archives supplied tasks before
deleting a worktree. Those effects need their respective authority. The source
records this code observation and its limits; no deletion experiment was run.

### Current candidate and scoped connections

The current Codex package targets `3.3.0-dev.1`; versioning is not publication
evidence. It exposes one host Skill, the existing resume/compact hint, and a Node task checkpoint
connected to supported UserPromptSubmit, Stop and SessionEnd events. Codex also
connects Interrupt. The Agent binds necessary file inputs, output predicates and
the next authorized action against the current native input receipt. The helper
checks actual file hashes and specified JSON facts, detects stale inputs, and
can request native continuation when results remain unmet. An unchanged failure
does not request endless retries. Fresh user input invalidates an unreconciled
old continuation; receipt publication and retirement protect concurrent input.
All predicates on a file use the same observed bytes, followed by output and
input stability checks. External writers remain independent; these observations
are not an atomic workspace transaction. Pause retains the old contract epoch
until an explicit rebind reconciles new requirements.

This adds scoped task state, no daemon, command executor or extra model call.
The helper never decides user authority or whether the selected predicates fully
express the goal. It leaves semantic judgment, execution and unsupported paths
with the host Agent. Unfinished checkpoints survive session end; verified or
explicitly cancelled tasks can retire only their checkpoint files. Proven dead
locks have an explicit recovery operation. Input failure is latched outside the
input lock with session/workspace generation watermarks, including malformed or
oversized transport whose session cannot be bound. The epoch combines the receipt
and current failures. The surviving caller must reconcile and replay the actual
current native input using that recovery epoch; an old replay cannot acknowledge
a newer loss. Stop rechecks freshness after state publication. Retirement checks
failure generations after deletion and restores its missing checkpoint/receipt
before rejecting a concurrent input failure; partial deletion is also compensated.
These operations preserve failure watermarks and are not an external-writer
transaction. If failure storage or compensation itself cannot work, the native
caller must hold and recover through sufficient means; cross-process protection
is unknown. Transport and bound checkpoint JSON remain bounded to 128 KiB.
The root-task input receipt retains successfully captured native input text and its hash
in event order, bounded to 8 MiB without silent truncation. Recognized own Stop
callbacks are not appended as user input; explicit recovery replays remain labeled.
`read-native-input` returns bounded Unicode-safe pages only when requested, with
original hashes and a continuation cursor. It creates no files or locks: observed
publication locks or changed input/failure evidence reject the read. A stable
snapshot establishes neither later freshness nor transactional isolation from
external writers. It does not replay an event, clear
quarantine or a pause, or authorize effects. Legacy receipts report unavailable
text; the captured range is not complete prior history, attachments, progress
or proof that embedded text represents a new human decision. Corrupt text is
rejected. Full storage fails capture using the existing failure/replay protection.
This local copy can contain sensitive user text and must not be included in routine
public evidence. It follows the same receipt retirement rules below, without a
new service, transcript scan or model request. An older executor may omit this
field or reader; retain a compatible executor for unfinished recovery needs.
Failure watermarks remain until their owning
state directory can safely be retired, without clearing another task's uncertainty.
SessionEnd removes only unbound receipts with no pending input recovery or
interruption. An interrupted receipt remains available even if no checkpoint was
created; ending the native session is not evidence that its unfinished goal was
cancelled. Later native input can be reconciled normally, and explicit current-epoch
retirement remains available to a caller with verified cleanup authority.
A native input blocked by another
Hook can exit without either callback; a surviving caller that verifies this
exit can retire only the matching unbound receipt using its current epoch,
revision zero and a reason. This operation cannot retire a bound checkpoint or
establish task completion. Without a callback or surviving caller, automatic
retirement is not established; the helper does not supply its own scheduler.
The default durable directory is `~/.yiyuan-accord/task-state`; an explicit scoped
directory can override it. Exact-session legacy temporary data stays in place;
conflicting locations are not merged. An empty state directory is not an installed
package cache or an archive executor. CLI checks establish local behavior; exact
native loading and ordinary task use remain separate observations. Current
evidence and unresolved conditions are linked from
[continuation](operations/CONTINUATION.md). Earlier host-specific mechanisms and
observations remain recoverable at their
[exact historical revision](https://github.com/yiheng8023/YIYUAN-Accord/blob/22f99b0e02e3ed8d0061262654953c6e2dcbfd46/docs/architecture.md#current-candidate-and-scoped-connections);
they do not describe the current distribution. Final package changes need
explicit affected-dependency review, not a new date on a historical run.

Continuous correction applies throughout development, including after
a function works; it is not a once-completed planning phase. User-owned
AGENTS.md files are external conditions, not a delivered dependency or a
substitute for Accord's responsibility.

The current package supplies its entry and recovery duties through supported
native events, without requiring user or project instruction files. An isolated
no-model native probe with no `AGENTS.md` confirmed those connections, including
retained input and renewed recovery hints after native context renewal. This
does not prove autonomous restoration or a complete user outcome. The earlier
Windows probe lacked an enabled sandbox backend, so managed read-only permissions
with approval disabled could not admit the command. With a real restricted-token
backend and the same read-only/never policy, the old reader then failed because
it created lock files. The corrected reader retrieved the captured original text
after native context renewal without those writes. This controlled transport
does not demonstrate autonomous choice, semantic restoration or subsequent task
delivery. Source, original failures and limits are recorded in the
[read-only recovery observation](operations/PROCEDURE-v3.3.md#只读恢复的沙箱前提与读锁修正2026-09-11).

Context signals also depend on the actual entry. The helper's `--context-signals`
interface consumes caller-supplied native events; it does not subscribe to a
Desktop event stream. Native context tools may offer a direct alternative when
actually exposed and authorized. In the inspected host version, their remaining
budget uses the tighter applicable auto-compaction or full-window bound; it is
not an efficiency measurement. An experimental setting is not a package
prerequisite. Tool absence, unknown data or a policy denial must remain distinct
from a successful query, renewal or recovery. Source and probe limits are in the
[bounded observation](operations/PROCEDURE-v3.3.md#无agents入口与原生上下文工具边界2026-09-11).

This is a candidate shape, not architecture law. Skill/Hook count, dependencies,
layout and admission may change together when evidence supports the change.
Whole-entry autonomy and incremental value remain unverified. Accepted cases and
impact assessments support only their declared conditions, subject to current
dependencies and independent qualification; use the bound evidence in continuation
instead of treating a historical count as the current state.
Native success can satisfy a duty but does not prove Accord benefit;
forcing a Skill invocation or evaluator rescue cannot establish ordinary-entry
autonomy.

The repository has separate roles:

- The current host package supplies guidance, native entry and recovery hints,
  and the scoped task-state helper described above.
- The no-I/O reference core evaluates supplied facts and policy; it does not
  discover capabilities, authenticate facts or actuate the host.
- Maintainer validation checks source, package identity, evidence and historical
  integrity within its declared scope.

These roles need not all run inside a user's task. Not connecting the reference
core to the Skill is not itself a defect. Add a connection only for a necessary
effect and a real caller, and validate that composition through the actual entry.
The current core's existing callers are historical evidence recalculation and
tests. Source labels and tri-state facts are supplied by callers; the core does
not authenticate or collect them. Its whole-observation invalidation is not yet
an implementation of dependency-scoped adaptation in an ordinary host session.

### Optional representations and host cooperation

The current capability map, duty references, work sequence and scenarios serve
development review and plan generation from one source. Their callers earn
their present place. The duty `dependsOn` view checks implementation order;
it is neither a live execution graph nor a ban on runtime feedback loops.

An index or graph may improve repeated lookup and affected-change analysis.
Compare that benefit with construction, refresh, staleness, coverage, memory
and maintenance cost. Direct queries, host facilities and other representations
are equally eligible. A visible map does not establish actual discovery,
selection or execution. Do not build a universal host/model/tool catalogue.

The uncalled self-contained graph demonstration was removed from the current
tree. Its
[exact historical version](https://github.com/yiheng8023/YIYUAN-Accord/blob/1e5ef9635b41c576edd622001fd477f391944b59/research/PROTOTYPE-dynamic-relation-graph.html)
remains recoverable; frozen source references resolve at their original revision.
This removes an inactive asset, not a functioning host capability, and proves
no runtime speedup. Historical Git indexes and frozen graph assertions still
serve provenance and replay checks; they are not ordinary-entry graph features.

Native means are a low-burden start or equal-fit preference, not an exclusive
route. A material gap or plausible net benefit can justify bounded comparison
beyond installed inventory even when native can finish. Reuse callable host
discovery, selection and lifecycle; use reliable external research as needed.
Compare required effects, evidence, fit, maintenance, license, permissions and
full adoption/use/recovery/exit cost. Stop when further search is unlikely to
change the safe choice. Discovery grants no installation, account, data or cost
authority; a specialist label does not establish domain quality.

### Environment, topology and failure

Bind observations to actual entry, model/provider, effective configuration,
tools, permissions, active package and time. Dated official/interface inventories
identify candidates and limitations, not verified coverage across every desktop,
CLI, IDE, cloud, mobile or SDK surface. Account-unavailable entries remain
untested. Both default supported hosts and customized environments matter;
development-only extensions or evaluator help cannot be counted as product value.
Isolation is an experimental control, not a product prerequisite. Inspect the
shared development environment and exact installed candidate when they affect
a decision; do not infer an empty or default profile. Pre-release tests use
bounded task-local exposure. Loading, hot update and recovery
need separate evidence in the supported host; replacing files cannot undo earlier
decisions or erase instructions already present in a conversation.

Re-sense only decision-relevant changes, including model-native gains, invalidate
dependent assumptions and preserve independently safe work. Retire redundant
intervention after confirming still-needed effects. Model selection may use
supported host controls; requested parameters, inheritance and provider aliases
do not prove actual execution or optimal fit.

For reliability-sensitive work, bind trigger, executor, necessary state and the
actor that survives the relevant failure. A runtime is eligible, neither
mandatory nor forbidden. Native controls, Hooks, scripts or another composition
may suffice. Conversation, execution, code and deployment topology are separate
choices and do not authorize changes to one another.

Continuity is one cross-function example: the destination must reconcile the
latest goal, authority, corrections and upstream/downstream work. Fact checks
alone do not establish takeover: deliver the handoff and confirm its acceptance
with one writer before source release. Archiving user tasks requires explicit
user authorization; neither handoff nor completion nor cleanup grants it.
Preserve the last safe state on failure; user restoration is recovery help,
not successful autonomous handoff.
Observe actual release semantics and protect dependent tasks; acknowledgement
alone does not prove unload or resource savings. If no extra resource was
allocated, do not manufacture a cleanup operation.

The current Desktop scope separates an actual user-requested takeover from
useful continuation after healthy automatic compaction. The latter exercises the
permitted same-carrier branch; no newly necessary forced migration was observed.
The former verifies receipt, transfer of writing responsibility and actual work,
not autonomous detection. Prior user rescue remains a failed autonomous result.
Unknown capacity/efficiency signals require short work spans and early checkpoints;
that fallback rule is not proof of historical prediction or an optimal margin.
Large source reads consume the same capacity as other work. Preserve reusable
verified intermediate results with source and verification references, observed
effects, uncertainties and remaining work in a task-suitable representation.
Recovery should reuse still-valid results and recheck affected or missing facts.
Repeated reading or renewal without result progress is a reason to reconsider
work-unit size, evidence organization and permitted topology, not evidence that
another context change is required. These are conditional guidance duties;
their presence does not prove autonomous timing or successful convergence.
If a task needs migration before compaction or integrity loss becomes unsafe,
unknown timing or takeover capacity becomes a necessary gap again. Source writer
quiescence is the observed release boundary, not runtime unloading.

The user's favorable pre-Accord experience is a useful result target, not proof
of runtime causality. Historical observations, failed probes, observer defects
and their exact attribution remain in `developmentObservations`. They are not
current acceptance receipts.

### Static checks and caller-observed qualification

Run `verify-development` for source conformance. CLI `verify` and
`host-check` retain development static checks: source integrity,
unchanged predecessor, declared package identity, namespace/legal carriage,
hint transport, complexity and bounded changed paths. Their PASS does not
establish functionality, value or candidate eligibility.

The development source's `acceptance.admission` binds required coverage, defined
scopes and cases with a risk-bound independent review policy. Each claimed host
requires function, package lifecycle and impact assessment. Incremental benefit is a
separate claim requiring positive comparison evidence; none is supported for
this candidate. The former positive hypothesis and neutral result keep their
original identities. Negative results, input/authority harm and unknowns necessary
to the declared use cannot be hidden by a neutral label. Stored assessments and
diagnostics grant no acceptance. A `candidate-frozen` source pairs only the exact
authorized target with `final-candidate-not-publication-proof`; dev packages retain
their development state. Neither representation can promote the static source
booleans or replace external qualification and publication checks.

The Python entry `verify_product(root, evidence=observer)` reuses bounded Git
reads, exact package identity and independent-review validation. The caller must
select a trusted, authenticated, independent, bounded read-only observer; a
callable or a JSON record does not establish those properties. The CLI neither
loads observer code from data nor accepts a receipt file as authentication.
No new executor, service, database or host dependency is installed.

Commit the implementation, case definition and oracle files as A before observing
E. At candidate B, the verifier binds HEAD/tree before static reads, verifies A
is an ancestor, and checks the full affected package and oracle files. Case
digests bind shared goal/authority/acceptance semantics and selected dependencies;
progress-only or unrelated case changes do not invalidate unaffected observations.
Changed shared rules, packages or relevant oracles do. Reviews bind exact B/tree,
must postdate B and remain current. No observer result can switch the subject.

The observer receives `phase: observe`, the verifier's subject and computed case,
definition and package identities. It returns independently checked records and
the external review bundle. Each record binds provenance, capture time, conditions
and same-episode effect, authority, post-state, cleanup and applicable comparison
facts to its oracle. During `phase: recheck`, the observer rechecks those sources
and reviews, acknowledges their `observationSha256`, and returns current subject
and per-case conditions. The caller owns source authentication, observation
deadlines, independent attribution and revocation checks; echoing a digest proves
none of them. The verifier rechecks Git, cleanliness and time before qualification.

`requiredCoverage` comes from authorized needs, not successful samples. Missing
IDs stay unbound; deleting scopes or cases cannot erase their obligations. Each
delivered host needs required function and lifecycle scopes. Whole-product duty,
quality and scenario accounting runs once per host over its required scopes,
not once per claim. Impact requires a sufficient assessment for each host, while
any active incremental claim must bind its own required comparison. A local benefit
cannot be attributed to unobserved hosts. Optional scopes cannot fill this ledger.

Scopes bind entry, decisive conditions and applicable requirements. Cases may
vary other conditions for legitimate transitions but cannot borrow another
scope's effects. Complementary hosts cannot fill each other's inventory gaps.
`functionalCompletion` closes only required function scopes, not the product's
lifecycle, value or total-coverage gates. The entry inventory is not a promise to
test every entry. Requirement/definition changes invalidate dependent evidence;
independent review must still judge coverage, oracle adequacy and the legitimacy
of any reduction. A valid hash does not make a convenient sample representative.

Reports distinguish accepted cases, scoped open/unbound and product coverage, functionality,
impact assessment, incremental value and conditional candidate eligibility. Missing, conflicting or
stale facts do not qualify; unaffected accepted cases remain visible. Structured
fixtures validate this admission logic only. Real case adequacy, actual entry and
host effects and independent provenance must be checked against the actual
records; final reviews bind the exact candidate rather than a development draft.
Authority, hosted checks, ordered publication and public post-state are separate
gates, never outputs promoted by this evaluator. The consensus plan owns the
remaining implementation and evidence procedure; generated views support it.

Current development budgets are explicit, including five-percent code/test
headroom; they are revisable cost controls, not product functionality. Measure
necessary implementation and regression cost before revising a budget. Do not
remove required historical isolation or weaken evidence checks to fit a number.

## Frozen predecessor architecture and evidence

The predecessor architecture is preserved
[at exact revision 4f9a21d](https://github.com/yiheng8023/YIYUAN-Accord/blob/4f9a21d79729867bed3bc89917b64c8386ce9ac6/docs/architecture.md#frozen-predecessor-architecture-and-evidence).
Its design and procedures are historical, not an implicit successor constraint.
Detailed earlier development explanations and observation summaries are
[available at exact revision 1e5ef96](https://github.com/yiheng8023/YIYUAN-Accord/blob/1e5ef9635b41c576edd622001fd477f391944b59/docs/architecture.md).
The retained verifier continues to read immutable predecessor objects.

## Maintenance baseline

This anchor remains for published release-document references. The v3.1
maintenance baseline is
[historical, at exact revision 4f9a21d](https://github.com/yiheng8023/YIYUAN-Accord/blob/4f9a21d79729867bed3bc89917b64c8386ce9ac6/docs/architecture.md#maintenance-baseline).
Use the active development source above for current work.


### Native root and subagent identity

Codex 0.154.0 uses one `session_id` for a root task and its descendants. Native
subagent `UserInput` events additionally carry `agent_id` and `agent_type`.
The checkpoint's unchanged `session_id`/cwd key represents root-task state;
subagent events leave it untouched and use native subagent state. Partial or
invalid actor metadata is unknown and follows the existing failure-watermark
path, preserving old text and checkpoints while invalidating stale freshness.
No root-state migration or independent subagent checkpoint store is introduced.

The current V2 spawn path sends inter-agent communication, which skips
UserPromptSubmit. Legacy spawn and directly submitted child UserInput can take
the other path. Subagent start/stop and root start/stop/interrupt are distinct
native routes; do not infer root-event coverage from subagent availability.
This actor separation is not caller authentication or a complete permission
barrier. Actual delegation, receiver reconciliation and safe source release
still require their own execution evidence.
