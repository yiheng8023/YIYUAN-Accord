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

Version 3.3 internalizes applicable question decomposition, typed results,
uncertainty handling and feedback designs through host models, supported tools
and necessary Accord components. Dedicated third-party decision-model provider
integrations are deferred for evaluation in later versions; no additional user model deployment,
training program or hosted model service is introduced. This boundary preserves
ordinary ecosystem reuse and does not prescribe a fixed model sequence or claim
superiority over specialized models.

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
evidence. It exposes one brief coordinator and four independently discoverable specialist
Skills for capabilities, continuity, verification and plugin lifecycle. Native
SessionStart and UserPromptSubmit read the same brief Skill body and resolve its
package-local pointers; selection of a Skill is not the delivery mechanism.
SessionStart supplies the coordination body separately from the companion
checkpoint Hook's recovery evidence, preserving its bounded snapshot budget.
Startup guidance reads the packaged brief, with no task-state access. A missing
brief is an entry failure; unavailable optional details hold only dependent work.
The package also registers one host-managed stdio MCP process with
`inspect_task_state(cwd, includeContext?, contextMaxAgeMs?, contextAssessment?)`. It reuses checkpoint `status` and returns a selected
subset of the caller's native MCP metadata separately from that snapshot. The
caller selects an absolute workspace; the tool does not attest it as the host's
current cwd. It neither changes saved task state nor opens a control connection or dispatches
a task. Missing input/state remains unavailable. In the inspected host, Hook
session identity is shared by descendants: when native session and thread IDs
differ, the reader holds checkpoint lookup instead of adopting ancestor state.
This adds a host-owned process lifetime, not a separate storage engine or remote
service. Installation, actual tool use and resource release remain separate checks.
The separate `manage_task_state` tool reuses `bind`, `pause` and `retire` in that
same runtime and storage. It accepts only their declared fields, caller-observed
epoch/revision and workspace; native root identity and `nativeTurnId` come from
MCP metadata. The helper checks the turn initially and again under the input lock
before publication/deletion, including host continuation that retains the human
input epoch. Legacy helper callers without this optional turn guard retain their
own identity responsibility. No business output, host mode, replay or lock recovery
is changed through the tool. Pauses and unresolved conditions retain their existing
rules; reasons are caller claims, not proof of authorization. Mutating/destructive
annotations are accurate hints, not a guarantee of approval or server authorization.
The host may require approval for this tool; a `never` policy can reject it before
the adapter runs. Inspect the actual disposition and retain unfinished work;
do not change policy or switch routes merely to bypass a denial. In the inspected
App Server, a tool error is a failed item with a result, whereas a host denial has
an error and no result. Raw MCP `isError` is not repeated in that normalized result.
An execution error requires post-state inspection; a successful operation with
oversized inspection details returns a compact success receipt rather than hiding
the applied mutation. Transport failure does not establish absence of prior effects.
The same process exposes `read_task_input(cwd, index?, offset?, maxChars?,
expectedReceiptEpoch?)` for recovery text. It reuses `read-native-input` without
another store or control connection, selects only the root session from native
call metadata and returns captured-input pages with their original hashes and
input-loss/resume/interruption flags. The returned next cursor pins the observed
receipt epoch; a changed epoch rejects that page instead of joining different
bases. Captured input is not complete history, attachments, work progress or new
authority. Reading does not replay input, clear quarantine, resume pauses or
establish restoration. The command helper remains available where this tool is not.
Context reads are opt-in. They reuse the Hook-bound transcript reader and match
its thread, turn and model to this call's native metadata; the recorded session
version remains separate from the current host version. Different input epochs
are not combined. The caller may select an appropriate age limit; original sample
time, expired-state diagnostics and unobserved-tail uncertainty remain. Without
current host evidence, raw transcript counters do not establish assessment identity.
The optional `contextAssessment` closes the same tool's forecast path by calling
the existing `assess-context` helper. It binds a prior receipt epoch, checkpoint
revision and context generation to the caller's original times, integrity evidence
and sourced tail/work/transfer/recovery/safety estimates. Current native identity
cannot be supplied in arguments. Fresh counters in the same generation may grow;
changed input, revision or generation instead requires reassessment. Assessment
uses existing transient locks, preserves saved state and pauses, and grants no
dispatch or source release. The default status-only call does not read context.
The MCP implementation version is captured from package metadata at startup;
development source execution uses the development projection as its version source.
The ordinary CLI development observer separately reports Hook guidance delivery
and native turn configuration. The latter requires one matching `turn_context`
between the bound turn start and the next turn, before model work or other
non-user native items; missing,
duplicate, conflicting or late records remain unknown. Model, effort, workspace
and collaboration mode are reported configuration, not proof of provider execution.
The session header version remains recorded history. Goal state stays unknown
without its own evidence. Byte length, hash, line and source path retain the
observed snapshot boundary; this projection does not grant case admission or
change an execution receipt's validity.
The continuity Skill obtains decision-relevant Goal state separately through an
available native current-task query or an already-owned App Server connection.
The latter's `thread/goal/get` reads persisted Goal state without resuming a task
in the inspected Codex 0.155.1 source; its Goals-feature gate can reject the read.
A null response establishes absence at the observation time only. Unsupported or
failed reads remain unknown, and this guidance creates neither a control service
nor permission to enable a mode. Existing CLI condition projection stays unchanged.
Standalone startup resolves configured state/session/home/temp paths against its
original cwd, then leaves the plugin cache directory before serving. This avoids
pinning a Windows cache directory during native replacement without rebinding
relative state paths. It does not itself reload code already held by an old process.
The checkpoint connects UserPromptSubmit, Stop, SessionEnd and Interrupt. These
connections establish available mechanisms, not demonstrated ordinary-task adoption
or end-to-end completion. The Agent binds necessary file inputs, output predicates and
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
locks have an explicit recovery operation.
Recovery callers serialize owner inspection through deletion using a shared
`.lock.recovery` gate; ordinary operations keep their existing state/input locks.
State-lock recovery does not acquire the input lock, so two locks left by dead
owners can be recovered in order without a new lock-order cycle. A leftover
recovery gate is not automatically reclaimed: the caller must establish
quiescence and bounded maintenance authority. All copies recovering the same
session must honor the gate, or maintenance needs external exclusivity; an older
recovery helper can bypass this protocol. A gate-only legacy location remains
visible rather than silently selecting a different state directory.
Input failure is latched outside the
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
On `SessionStart` with `source=compact`, a read-only recovery snapshot replaces
repeated generic entry discovery. It compares complete captured bytes of the
input, checkpoint and both failure watermarks, rejects overlapping publication
or recovery locks, and changes no epoch or state. Within 6000 serialized UTF-8
bytes it supplies complete captured input when it fits and checkpoint core fields
when they fit; later corrections are never hidden behind an inline input prefix.
Source paths, hashes and a prepared input-page request support further inspection.
Checkpoint inputs and output predicates remain in the full source file. Oversized
metadata falls back to unknown with retrieval locators; when exact paths alone
exceed the snapshot budget, those locators are emitted separately and intact.
This is optimistic evidence delivery, not completed restoration, current authority
or a transaction with external writers. Pauses, interruption, replay requirements
and epoch differences remain explicit. `status` reuses the same optimistic
read boundary, including outcome inspection before the second source read. It
needs no write access and rejects observed publication/recovery locks, changed
bytes and incompatible checkpoint identity. Invalid JSON or unavailable files
identify their source role without echoing stored content; failure has a nonzero
exit and never becomes an unbound success or automatic repair. This is not a
transaction over external files and grants no authority for later actions.
Resume reconciliation and input publication retain their existing write locks
and lifecycle semantics.
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
Event availability is not a universal Hook-count requirement. The source at
Codex `rust-v0.144.0-alpha.4` lacks Interrupt and SessionEnd Hook events, but its
[native cancellation path](https://github.com/openai/codex/blob/049586f41571e74b44c841868bca3a2233214a71/codex-rs/core/src/tasks/mod.rs#L829)
cancels and aborts the running task and emits TurnAborted; its
[turn loop](https://github.com/openai/codex/blob/049586f41571e74b44c841868bca3a2233214a71/codex-rs/core/src/session/turn.rs#L372)
does not route cancellation errors through normal Stop continuation. A retained
checkpoint cannot start execution. Without Interrupt, that receipt remains
historical until the next native input or resume invalidates its old binding;
inspect prior effects and writers before dependent work. Native cancellation
does not undo external effects, and session-shutdown resource cleanup must not be
assumed for every mid-turn cancellation. Without SessionEnd, use the existing
authorized surviving-caller retirement route; absence of that caller leaves
cleanup unverified. These source-level alternatives do not identify a running
cloud controller or prove its plugin adoption, cancellation behavior or admission.
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
native events, without requiring user or project instruction files. The historical
2026-09-11 isolated no-model probe with no `AGENTS.md` confirmed the source-Hook
entry/recovery variant it bound, including retained input and renewed recovery
hints after native context renewal; it does not validate every later entry variant. This
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
Desktop event stream. Collect connection-level `thread/settings/updated` together
with the turn events in transport receive order; a turn-only subscription is
not a complete input stream. Settings snapshots describe the next turn, while
`model/rerouted` changes only the active turn's observed model. The next
`turn/started` adopts the latest configured model and requires fresh usage.
Record receive times at the transport reader, not when a delayed queue consumer
handles events. In the tested 0.154.0 dynamic-tool flow, the first tool call
preceded its usage notification; that notification followed the tool response.
Return unknown promptly when it is missing rather than waiting for data whose
delivery depends on completing that same call. A later query can use fresh
events, but this does not prescribe repeated polling or measure occupancy.
The current-model and queued-settings tool roundtrips are recorded in the
[controlled connection observation](operations/PROCEDURE-v3.3.md#有序信号工具往返与历史交接复用2026-09-13).
Native context tools may offer a direct alternative when
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

### Host-owned native handoff

Long-lived state readers retain their optional context-reader code when the
runtime loads. Native updates may retire the original package directory before
the first context query; that query must not resolve code from the retired path.
Transcript data is still read only on demand. A missing optional module leaves
ordinary status usable and is reported when context is requested; code loading
does not establish permissions or adopt a newer on-disk runtime generation.

The optional `runtime/carrier-handoff.cjs` is a callable integration seam supplied
in the Codex package. The continuity Skill routes applicable callers to its
[packaged interface](../plugins/yiyuan-accord-codex/skills/deliver-demand-driven-outcome/references/native-handoff.md),
which owns the plan, callback, verification and recovery contract. Consumers need
no development checkout to read it. The adapter composes a surviving authorized
controller's native transport, durable scope ownership and independent verification;
it supplies no default Desktop/IDE control connection or automatic timing.
`prepareHandoff` connects an actual source dynamic-tool request to that same
record and execution core. Preparation only records a queued proposal; an outer,
single-use dispatcher requires the exact tool result, completed source turn and
current bindings before native takeover. Interrupted sources and controller loss
remain reconciliation cases, not automatic replay.
`reconcileContinuation` closes only a bound first-continuation acknowledgement loss:
it correlates original RPC evidence and current native state, obtains independent
authority/effect verification, and uses the existing recorder CAS with readback.
The original failure is retained, the target writer is unchanged, and a matching
repeat returns a stored snapshot. Neither path authorizes new work or source release.
The host read may refresh its own history projection; this is not a new native turn.
`runHandoffProposal` provides the corresponding event coordination for an owned
ordered receiver: subscribe from the exact request, send once, correlate native
receipts, re-read current bindings and invoke the same dispatcher. Source activity
is monitored through dispatch; only this listener is released. The caller retains
its journal and connection, including request-to-subscription replay. This removes
manual receipt assembly without adding storage, a service or automatic timing.
The optional `runtime/codex-connection.cjs` implements that connection for injected
caller-owned Node stdio streams or an already-open standard WebSocket. The latter
reuses the supplied implementation for handshake/framing and adapts complete JSON
messages to the same reader; it adds no network library or connection setup. One
bounded reader correlates RPC, retains an
ordered journal, provides exact-anchor replay/live delivery and derives context
observations from the same native stream. It leaves process startup, initialization,
durable ownership and semantic judgment with the authorized caller. Closing this
module detaches its listeners and rejects waits without destroying injected streams
or closing the caller's socket. Failed WebSocket sends invalidate pending work;
local buffer-limit rejection does not retry. Its message limit applies after the
supplied socket has assembled a message, not to that implementation's whole memory.
Controllers may expose its optional `accord_inspect_context` dynamic tool to the
source. The connection replies from the actual request identity and native journal;
model arguments cannot select another task or operation. Unknown first-use signals
remain unknown. Source access to observations enables judgment but does not supply
the judgment, permission, forecast or semantic verification itself.

The packaged reference also distinguishes official daemon/proxy attachment from
embedded clients and from starting an unrelated server. In the source-bound 0.155.1
path, loaded-thread resume subscribes and replays pending requests but cannot add
a new dynamic tool. Other clients can answer a shared dynamic request; protocol
routing therefore does not replace scope ownership or authorize handling unrelated
requests. The reference carries the upstream experimental-support limit. These
conditions guide integration; no ordinary Desktop/IDE connection is installed by
this documentation or inferred from a successful inventory.

The optional `runtime/codex-session.cjs` supplies the SDK source caller: it borrows
an initialized, authorized connection, creates a source with context/proposal
tools alongside the owner's tools, binds the source writer and pumps its turns.
Source creation explicitly requests `ephemeral: false` and requires the returned
thread to confirm that mode before binding a writer or dispatching work. Missing
or contrary persistence metadata retains the created ID/receipt for owner
reconciliation without retry; this does not establish crash durability.
The owner supplies current authority, the handoff plan, independent effect
verification and decisions for other server requests. A single activity wait
handles either a request or the matching terminal event; it leaves no losing
waiter that could consume a later request. Unscoped requests require explicit
ownership. Failure retains the source/turn and RPC references for reconciliation
and cannot be retried through the failed session. A successful transfer stops
writes to that source. The controller can explicitly adopt its own verified target
after checking the final ledger, native idle/persistent state, current authority
and effects; settlement preserves history and fences the old lease. The target
then serves as the next source in the same scope. Target context/proposal tools
are bound before native creation, and requests during intake are pumped as well;
a nested proposal while a transfer is in progress is refused without queuing.
This is a same-controller path, not automatic cold recovery or arbitrary thread
adoption. Project/sidebar association alone establishes none of these bindings.

For a new controller, `restoreCodexSourceSession` handles only a completed,
settled target with reconciled prior effects. The caller supplies an acknowledged
inactive scope receipt and current authority; the verifier establishes prior
controller quiescence and safe initialization. The existing recorder rotates the
scope token before native resume, so an uncertain resume cannot be replayed with
the old basis. Native settings, necessary history and actual tool-restoration
evidence are checked before readiness, followed by a final token readback.
Ordinary turns check that same held token. This reuses the current schema and
host persistence; it adds no service or timeout-based takeover. Failed restore
executors cannot create a replacement task, and active/uncertain transfers remain
unreconciled rather than being forced into this settled-target path.

Recovered continuation receipts and completed handoffs are separate states.
`finalizeReconciledHandoff` connects a verified `continuation-reconciled` record
to the existing release, settlement and restoration path without executing that
continuation again. It consumes an acknowledged revision, lease and receipt
digest, then rechecks native state, authority, pauses, effects and writer ownership.
On the original connection, release uses a native unsubscribe receipt. A new
controller instead requires independent evidence that the old connection is
closed and cannot dispatch, with source recovery retained; its own lack of a
subscription does not establish those facts. Preserve the actual release basis
in the record. An uncertain effect or state commit requires reconciliation, not
another dispatch or an invented successful release.

`runtime/carrier-recorder.cjs` provides the previously test-only scope ledger
using Node's built-in SQLite, opened explicitly at a caller-owned file. It checks
database identity/schema and reads related rows in one snapshot; transactions
compare scope, writer, revision and fencing token together. Settlement is explicit
and preserves the target writer and history. This storage coordinates cooperating
writers; it is neither an OS writer lock nor permission to replay native effects.
SQLite is loaded only when the optional recorder is opened, so existing Hooks
and MCP do not acquire this dependency. Node must provide `node:sqlite`
`DatabaseSync`; the owner retains connection, database and process shutdown.

These shipped components close source registration, event pumping and storage
assembly gaps for an authorized SDK controller. They do not give an ordinary GUI
plugin a control connection, provide universal semantic verification or qualify
automatic handoff as complete. The native test caller below remains test evidence.

The native test caller in `tests/product/test_carrier_handoff.py` reuses existing
App Server/process controls, local fixed responses and SQLite transactions. It
checks protocol effects, refusal, extra intake and source-tool dispatch; it does not prove model judgment,
autonomous timing, a production verifier or ordinary GUI adoption.

`tests/product/test_codex_session_native.py` reuses that fixture and OS controller
to exercise the shipped source session, connection and recorder against the real
App Server. Its bounded sequence covers two handoffs, intake context and nested
proposal handling, two target adoptions, retained native histories and natural
process exit. The independent artifact reader correlates raw requests/receipts
with the SQLite ledger and preserves the exact execution sources. It reads a
closed, checkpointed ledger with SQLite's immutable option: read-only mode alone
can create WAL/SHM sidecars. The Windows 0.155.1 observation is protocol evidence
with fixed responses, not model judgment or performance evidence; context remained
unknown, and full-history hydration carried a paginated-thread deprecation notice.

### Context timing

Unknown capacity/efficiency signals require short work spans and early checkpoints;
that fallback rule is not proof of historical prediction or an optimal margin.
The helper's `assess-context` keeps `capacityFit` separate from its combined
`decision`. A fresh first-party remaining-budget receipt is compared directly
with the next span and transfer/recovery/safety reserves. Later context changes
invalidate it. Without that receipt, the sourced context and next-work upper
bounds plus reserves are compared against the hard native window. A strict fit
permits `continue-bounded` after critical state is preserved, even when efficiency
is unknown. This forecasts capacity only: an unknown native compaction threshold
may cause earlier compaction, requiring restoration and reassessment. It neither
proves an efficient range nor guarantees an uninterrupted span. A stricter evidenced
efficiency ceiling can still call for handoff or recovery.
Invalid assessment evidence, pauses and stale bindings leave it unknown.
`remainingAfterReserves` continues to use the tighter applicable ceiling.
A capacity fit neither measures live occupancy nor overrides the combined
recommendation, task authority, integrity checks or source-release protection.
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

Development controllers can use `scripts/codex_events.py` for passive, per-request
`NativeTurnWatch` instances. A normal turn needs its own successful terminal and
an observed nonempty final answer, including one carried by the terminal itself.
A compaction watch binds the next new compaction item and requires its matching
completion and turn terminal. Its immutable view records protocol facts only;
raw messages, semantic acceptance, ownership and source release remain separate.
Create the watch before dispatch when possible and retain any notifications that
arrive before the RPC reply. Feed only the bound connection's new ordered window;
quiesce unrelated same-thread work before requesting manual compaction. An early
failure without a compaction item remains unbound and needs the caller's RPC
error/deadline and scoped recovery, never an invented interrupt target.
The observer contains no paths, budgets, model settings, file operations or
callbacks. Controllers must bind those separately to their own run instances;
copying a helper's code identity does not validate its captured configuration.

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

`evidenceAdmission.caseRejections` explains completed case checks with controlled
reason codes: definition/package or dependency changes, invalid or expired
observation time, condition drift and unmet consequences. It exposes no observed
private values, file names or external exception text. This diagnostic is not an
exhaustive blocker list: missing records, observer/review failures and unbound
coverage retain their existing outputs. An absent reason is not admission; use
`acceptedCases` and the complete report. Diagnostics do not refresh timestamps,
change predicates or convert historical observations into current acceptance.

Commit the implementation, case definition and oracle files as A before observing
E. At candidate B, the verifier binds HEAD/tree before static reads, verifies A
is an ancestor, and checks the full affected package and oracle files. Case
digests bind shared goal/authority/acceptance semantics and selected dependencies;
progress-only or unrelated case changes do not invalidate unaffected observations.
Changed shared rules, packages or relevant oracles do. Current v5 single-entry
pure-function cases may prospectively bind `packageFiles`, including the manifest,
adapter contract and primary Skill. Their original full package hash is verified
at A; declared dependencies are then compared with B, normalizing only the default
Codex cache timestamp within an unchanged manifest base version. Other manifest
fields stay significant. The dependency set is part of the definition and cannot
be narrowed retrospectively; independent review must establish its completeness.
Unselected Skill discovery metadata can still affect routing. Reuse reports keep
original and current package identities separate. Cases without this opt-in,
lifecycle, multi-entry, impact and A08 integration cases retain full-package checks.
Current whole-package integration and release review remain mandatory; valid older
function evidence is not relabeled as a new execution. Reviews bind exact B/tree,
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
