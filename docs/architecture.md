# Architecture

Agent Autonomy Harness is an open, Agent-neutral, demand-driven human-Agent
collaboration quality harness. Its durable outputs are a demand-to-capability
collaboration methodology, an open minimum quality-conformance profile, and
executable reference adapters. It has one testable portable product contract,
one common read-only continuation projection, and replaceable host edges.

```text
user goal + domain facts + bounded authority
                    |
                    v
        target portable quality profile
 observe capability -> assess gap -> discover if needed -> select route
 -> authorize -> task-scoped dispatch -> execute/observe/recover
 -> verify -> release/clean -> accept or continue
                    |
             desired operations
                    v
       native host / manager adapters
                    |
          source-bound observations
                    v
       evaluation, acceptance, replan
```

## 1. Current product authority

`product/constitution.json`, `product/program.json`, and
`product/acceptance.json` are the machine authority. `harness/control.py`
verifies their identity, mapping, authority, evidence-admission, and
process-loss invariants. The verifier pins the current release in code and
requires the program and acceptance identities to match it.

Historical release evidence remains in Git, but it is not scanned as current
authority. It remains usable as retrospective counterevidence and may trigger
replanning. The accepted v0.1 verifier and event-specific validators remain
reproducible at revision `be498f9`; carrying their one-off logic or raw receipts
in every later current tree would turn evidence history into product debt.

The code-owned supporting-document set explains the current contract,
contribution, support, and security boundaries. The verifier closes this set
and checks that each declared document is a non-empty UTF-8 file; it does not
claim to understand prose or prove semantic parity. Community and rights files
are public review surfaces but do not block G3 merely by existing or changing.
No document can override the three machine-authority files.

## 2. Target portable loop

The product target is one conceptual transaction entered at the goal level:

```text
bind demand and authority -> observe available capability -> assess the gap
-> discover through a source-bound adaptive channel only if needed
-> choose and preview the smallest sufficient route -> task-scoped dispatch
-> observe effects and recover -> verify -> release and clean
-> emit a bounded receipt or continue
```

The natural-task receipt is a logical goal-level demand and accountable outcome
unit, not a host conversation or sidebar-thread unit. Multiple sequential
receipts may remain in one healthy host task. One receipt may be eligible for
multiple criteria only when each criterion's pre-registration, measures,
validator, and human authority independently pass; it remains one sample
within any single criterion.

Portfolio minima are eligibility predicates, not work generators. O3's
reproducible-gap case and O4's rejected or stopped receipt count only when a
bound natural task produces them without induced degradation. The Agent cannot
disable a healthy capability, stage a failure, split or relabel one demand, or
invent a task to fill a cohort; the affected criterion remains false until an
eligible case occurs.

The portable layer owns testable quality semantics, not host commands or wire
primitives. It defines required
authority, unsupported states, lifecycle ownership, evidence shape, outcome
floors, fallback, recovery, cleanup, and process-loss stop rules. It does not
own a fixed catalog, provider list, collaboration protocol, identity system,
audit log, generic human-tool schema, universal runtime, or host projection.
Protocols, runtimes, evidence formats, catalogs, and discovery channels are
replaceable external substrate.

The current implementation is a product-contract verifier. It validates the
authority graph, criterion contracts, admitted evidence, human authority,
process loss, and repository residue. It does not execute tasks, discover or
install capabilities, route work, or operate a host adapter.

O1 is verified by three accepted, task-bound results: the public-intake rewrite
and the uninstalled Codex and Claude task-facing Skill source packages. O2, O4,
and O5 remain false while O3 is true. A repository-authored JSON file alone cannot promote an
outcome: every verified outcome requires a code-owned validator
scoped to the criterion and exact causal increment for the bound task
evidence. Before measured execution, the increment freezes an immutable task
registration containing every mapped criterion's required values, the task's
source-capture eligibility and stop rule, floors, and claim limit. A
task-specific validator may implement previously unknown source serialization
after the event, but no outcome can be promoted unless that validator binds the
registration identity and chronology, enforces its unchanged rules, and passes
the exact evidence and completed causal binding. This permits source-grounded
post-hoc checking, not post-hoc rule changes. A generic self-report schema could
validate only its own structure, not naturalness, source truth, behavior, or
value.

The v0.2 program is ready with no active increment after closing the
public-intake and task-facing Codex and Claude Skill source deliveries and
honestly stopping the later measured Codex attempts. Those three completed
task-bound results support O1. A separate criterion-scoped aggregate
check over their exact validators supports O3 through one no-gap/native-retain
route and two finite source-bound official discovery or adaptation routes,
with every projection inactive and task exposure released. The Codex Skill
task includes one native compaction and an explicit record of duplicate
goal-mode continuation prompts as non-material host process cost rather than
value. The Claude and Codex source deliveries are deliberately not treated as
materially different O2 scenarios. O1 and O3 are true; O2, O4, and O5 remain
false.
Authorized product-plan delivery is real demand
when its primary purpose is the required deliverable rather than exercising or
diagnosing the Harness; this does not make the task outcome-eligible without
the unchanged pre-registration, evidence, floors, and human-acceptance burden.
The current verifier and inactive adapter candidate are not an accepted
methodology, task runtime, behavior result, or cross-host proof.

### Continuity is reconciliation, not unlimited context

A host context window, transcript view, or compaction summary is a lossy
execution cache. It can help the next model step, but it cannot become product,
task, factual, or acceptance authority. The Harness does not reimplement host
compaction or promise that one thread can grow without accuracy loss.

Before any post-compaction mutation, the Agent re-observes the smallest durable
truth set already owned by the task: the bound goal and corrections, current
product authority and active increment, Git branch/HEAD/upstream/status,
completed and pending verification, human-retained gates, known side effects,
and the cleanup boundary. It compares those observations with the last verified
checkpoint. A mismatch blocks further effects while the Agent recovers
read-only from the authoritative sources; it does not ask the user to replay
discoverable context or choose a Codex mechanism.

The measurement contract and its registration identity freeze before the
eligible event; the repository does not freeze while waiting for normal context
growth. Authorized work may advance HEAD. After compaction, evidence binds both
the fixed registration commit and the actual clean reconciliation HEAD while
the validator rechecks the unchanged registration hash. Requiring both commits
to be identical would turn continuity measurement into an artificial delivery
blocker.

Healthy native continuation remains the smallest route. A Hook, external
memory layer, new task, or authored adapter requires a reproducible residual
gap plus its own authority and data boundary. If repeated compaction or a host
limit eventually makes same-task continuation unsafe, the Agent owns a
source-bound, verified handoff when the host and task authority permit it; the
user still supplies judgment, not transcript reconstruction. This decision is
not deferred until failure. At pre-registered material checkpoints, the Agent
uses available source-bound host signals and task signals such as repeated
compression, reconciliation uncertainty, goal or evidence divergence, and the
size and risk of the remaining work to decide whether the current carrier is
still safe. A missing reliable host signal remains `unknown` and activates the
task's conservative pre-declared transition rule; it cannot be treated as
proof that unlimited continuation is safe. No universal token threshold,
transcript monitor, Hook, or new task is mandated. O1 can calibrate only the
exact signals, transition, and task it observes. Repeated reliability and
cross-host portability remain separate O2-O5 burdens.

### Task topology is a lifecycle, not a user prerequisite

Code carriers include the current checkout, a branch, a worktree, and a
repository fork. Conversation carriers include the current task, a conversation
fork, and a new task. The default is the healthy current carrier on both planes.
An isolated carrier is justified only by a source-bound need for parallelism,
isolation, host capacity, or a distinct authority boundary; a routine phase
change or context growth is not enough.

When a split is necessary, the Agent binds the canonical goal and authority,
carrier identity and owner, synchronization point, merge or conclusion-
reconciliation route, archive or release condition, and cleanup boundary. It
then operates those mechanics and verifies the final topology. The user retains
goal divergence and new trust, data, cost, destructive, irreversible, release,
or publication decisions; the user does not decide whether to continue, fork,
open a new task, merge, archive, or clean when that route is safely discoverable
inside existing authority.

This is a quality-contract lifecycle, not a generic Git manager, task manager,
conversation wire protocol, or cross-host synchronization runtime. Each host's
native Git and task primitives remain replaceable substrate behind thin
adapters. Unsupported native behavior is reported and bounded rather than
simulated.

## 3. Capability and lifecycle plane

Capabilities include native functions, official runtime capabilities, reviewed
external Skills and tools, compositions, self-authored components, Apps,
Plugins, MCP servers, and optional Hooks. User-installed breadth is legitimate;
the Harness must keep it outside the user's cognitive path and the portable
core's standing context, then expose only the minimal task-relevant subset.

Each task begins by observing available healthy and authorized routes. Only a
reproducible residual gap justifies finite, source-bound discovery. The query,
channel, and provider may adapt to demand; none becomes product authority.

Implementation follows the same residual-gap rule across layers. Collaboration
protocols, human-allocation patterns, registries, gateways, tool search,
runtimes, identity and authorization, audit and provenance formats, governance
kernels, and evaluation systems are first treated as external substrate. A
source-bound as-of landscape check records exact version or commit, licence or
applicable terms, maturity, and reuse boundary before deciding whether to
reuse, thinly adapt, compose, or author. The reference adapters own only the missing portable quality
semantics and integration needed to preserve the Harness contract; duplicating
a sufficient external layer is a failed route decision, not product
independence.

Acquisition, installation, enablement, exposure, invocation, instruction
delivery, behavior, value, projection, rollback, cleanup, acceptance, release,
and publication are distinct states. One never proves the next. One live
component has one lifecycle owner.

Healthy installed and authorized capabilities may be used proactively for a
bound task. Installation, enablement, account connection, new data or trust,
meaningful cost, consumer mutation, publication, and release remain separate
authority transitions.

`AGENTS.md` remains execution guidance. Skills and Hooks are advisory inputs,
self-authored Skills are replaceable host projections, and the peripheral
ecosystem is a replaceable input. The current machine product authority and
bound user intent outrank them; conflicting or disproportionate routes are
rejected or downgraded.

Route selection is monotonic with respect to the bound task: compare additions
to goal, input, deliverable, human round trip, authority, side effect, and
acceptance. A capability may add one only when source-bound evidence shows it
is causally necessary for the result; completing the capability's preferred
workflow is not an independent outcome.

## 4. Host and manager adapters

Adapters translate only unavoidable host facts:

- available observation and actuation surfaces;
- native authorization and permission mechanisms;
- event, Hook, command, process, and filesystem shapes;
- manager preview, transaction, rollback, and cleanup behavior;
- unsupported-state degradation.

`codex-user-config` is a Codex consumer adapter and projection. CC Switch is a
separately governed capability manager. Neither is Agent-neutral product
authority. A second host must implement the same portable semantics through
its own thin adapter; a Codex projection cannot prove cross-Agent behavior.
Codex-first is the reference-adapter sequence, not a core dependency.

The repository as a whole is not a plugin. The portable methodology, quality
profile, evidence semantics, and acceptance remain manager- and host-neutral.
`harness/continuation.py` derives the common bounded reconciliation projection;
host modules validate native event envelopes and supply only adapter identity,
host substrate metadata, and output translation.
`adapters/agent-autonomy-harness-codex` is a replaceable Codex distribution
projection. It contains one concise, implicitly invocable task-facing Skill
bound to the unaccepted candidate profile, plus a `SessionStart` Hook and
standard-library launcher for the repository-owned continuation adapter. It
adds no MCP server, App, prompt interception, capability router, state store,
or outcome validator. The launcher uses Python isolated mode, reads the adapter
and verifier once, and executes only those same bytes after they match the exact
hashes reviewed for that plugin version. An unknown or changed runtime is a
non-blocking no-op rather than a new repository-code execution grant.

Codex 0.147.0 uses two complementary plugin-loading scopes. The dedicated
`HooksOnly` startup path deliberately omits Skills, MCP servers, and Apps while
preloading Hooks. Normal `AllCapabilities` loading discovers the same legacy
plugin's declared `skills/` path and loads its Skill inventory. A plugin that
contains both the Skill and Hook therefore does not strand the Skill behind the
Hook-only preload path.

`CODEX_HOME` bounds Codex configuration, authentication, plugin cache, and
session state; it is not by itself an authority boundary for every user-global
Skill. One registered source-gate run installed only this plugin in an isolated
home but still exposed a separate user-global code-review Skill. That Skill's
workflow required parallel subagents even though the immutable source-gate task
did not require a diff review or parallel topology. The carrier selected the
larger route and timed out without a final result, so the attempt remains an
honest stopped counterexample at
`product/evidence/cross-host-source-gate-stopped-2026-08-14.json`.

The current native correction stays in the parent dispatch boundary. Codex
0.147.0 can render the model-visible prompt through `codex debug prompt-input`,
disable an exact Skill for one invocation through `skills.config`, and disable
multi-agent tools through `features.multi_agent=false` or `--disable
multi_agent`. The official [Skill documentation](https://learn.chatgpt.com/docs/build-skills),
[configuration reference](https://learn.chatgpt.com/docs/config-file/config-reference),
and [CLI reference](https://learn.chatgpt.com/docs/developer-commands?surface=cli)
describe the implicit Skill selection and per-invocation configuration seams.
Before an outcome-bearing automated Codex dispatch, the parent Agent must inspect
the visible Skill set, bind any causally rejected Skill path and topology state
in the task registration, apply only those task-scoped native overrides, and
verify the resulting prompt and feature state before the model call. It must not
delete or move user Skills, persist a consumer-wide deny list, disable unrelated
healthy capabilities, or ask the user to select the route.

A later registered dispatch demonstrated both the value and the limit of that
preflight. It reduced 25 prompt-visible Skills to the single exact Harness Skill
and verified all multi-agent feature states false, but the immutable
structured-output schema used `const` without an explicit `type` on one
property. The Codex service rejected it as `invalid_json_schema` before model
generation. That stopped result is
`product/evidence/closeout-critical-path-stopped-2026-08-14.json`. Future
one-call registrations must therefore bind a schema known to be accepted by the
exact host, or a deterministic compatibility check when the host exposes one,
before dispatch. General JSON Schema validity, prompt visibility, and feature
state do not prove structured-output compatibility. This remains parent
orchestration evidence, not a reason to add a schema registry or outcome
validator to the product.

The next registered context-carrier dispatch passed the corrected structured
schema and repeated the 25-to-one Skill reduction with multi-agent disabled.
Its single Codex call nevertheless invoked the built-in
`list_mcp_resources` tool, which exposed 46 ambient `codex_apps` plugin and
Skill descriptors from the isolated home. No specific connector or external
data source was called, but the resource enumeration itself crossed the fixed
capability and public-input boundary. The parent terminated the process,
skipped the conditional distinct host, cleaned all task state, and retained the
zero-progress receipt at
`product/evidence/codex-context-carrier-boundary-stopped-2026-08-14.json`.
This proves that `skills.config` and multi-agent controls do not establish the
whole model tool and data surface. A future measured dispatch must first bind
and verify an official stable per-call restriction that removes ambient MCP/App
enumeration while retaining the required read-only repository operations, or
treat this Codex route as ineligible. The correction remains parent
orchestration and does not justify an MCP manager, registry, runtime, or control
plane.

The bounded follow-up mechanism probe used the official app-server configuration
and inspection RPCs against the installed Codex 0.147.0 binary, with no auth,
plugin, thread, turn, or model call. The per-process
`apps._default.enabled=false` override was present in effective configuration;
`app/installed` returned zero installed, enabled, or callable Apps and
`mcpServerStatus/list` returned zero MCP servers. This establishes a usable App
suppression component, not a complete task route. `skills/list` still found 39
enabled Skills: 33 under the shared CC Switch root and six system Skills copied
into the isolated Codex home. The no-thread RPCs cannot prove that
`list_mcp_resources` is absent from a later model-visible tool specification or
that the required model-driven repository operations coexist with the same
boundary. Future dispatch must therefore re-inventory and exclude every
non-task Skill after loading the exact Harness projection, inspect the
thread-specific MCP/App resource surface, and fail before a model call when
that evidence is unavailable. A stable host enumeration primitive is not itself
a product defect when it exposes no unauthorized resource and causes no
unauthorized invocation or effect; registrations must bind the causal boundary,
not an impossible host-implementation shape.

The plugin manifest has no field that can override other installed Skills or
multi-agent policy, and the plugin must not acquire that authority. This keeps
ambient-capability arbitration in Agent-owned task dispatch rather than adding a
capability manager, prompt interceptor, MCP server, runtime, or control plane to
the portable core or thin plugin.

CC Switch has no dependency role in the portable core, verifier, Codex adapter,
or Codex plugin runtime. It may remain useful as one replaceable operational
manager for shared third-party Skills. The exact app-server probe also shows
that those shared Skills remain discoverable from an isolated `CODEX_HOME`, so
CC Switch is an ambient input to task-time arbitration, not an isolation or
security boundary. Stopping or removing it must not change Harness semantics or
disable the Codex continuity projection. Codex's native plugin manager owns
this projection's install, cache, enable, update, disable, and uninstall
lifecycle.

`.agents/plugins/marketplace.json` is only a workspace discovery index. It
marks the existing thin projection `AVAILABLE` and points at that adapter
directory rather than the repository root. Codex 0.147.0 app-server discovery
from this workspace reports the candidate as neither installed nor enabled;
the index does not grant installation, enablement, Hook trust, or runtime
execution.

`adapters/agent-autonomy-harness-claude` is the corresponding inactive
distinct-host projection for Claude Code 2.1.232 at source tag commit
`1f6015b5d578adf79c8527443328a216d6b6a3f1`. It reuses the exact common
task-facing Skill and candidate-profile bytes beside one native `SessionStart`
Hook and an isolated standard-library launcher. Claude Code's session-scoped
`--plugin-dir` exposure avoids persistent installation; Skill discovery plus
native input and plain-stdout context output differences remain behind the thin
package and `harness/claude_reference.py`. The fixed host's strict manifest
validation and offline semantic-parity checks pass, but no Claude model task,
matched Codex pair, human equivalence judgment, or O5 evidence has occurred.

For the Codex reference host, reuse the host's lifecycle event before inventing
a Harness-owned continuation protocol. The fixed v0.147.0 `SessionStart` event
fires for startup, resume, clear, and compact, supplies the working directory
and source, and can return additional model context. The candidate adapter in
`harness/codex_reference.py` uses only that seam to project live authority and
verifier state, exact active increment/work/registration/cleanup identities,
and a shell-free read-only Git checkpoint. The checkpoint exposes branch or
detached state, HEAD, upstream or absence, ahead/behind or unknown, worktree
count or unknown, dirty-entry count, and a status digest, but not dirty paths or
diff content. The common projection has a 3,072-character budget inside the
Codex Hook's 4,096-character limit; an over-budget full form degrades to an
explicit hashed fallback rather than silent truncation. It ignores the supplied
transcript and session fields, stores no session data, is a no-op outside the
bound repository, and does not validate results or emit receipts.

Goal-level demand still enters through Codex's normal native conversation
path. Codex may implicitly select the task-facing Skill from its metadata; the
Hook does not intercept or classify prompts. Using `UserPromptSubmit` would add
raw-prompt access and turn-blocking authority without causal necessity, so it is
not part of the candidate.

The plugin source candidates remain inactive. Installation, enablement, and
exact Hook trust are separate consumer transitions requiring explicit authority
and reversible behavior evidence. The accepted source deliveries establish
only bounded package results plus the exact O3 route lifecycle cohort; they
cannot establish live Skill triggering, Hook behavior, repeated burden
reduction, methodology calibration, or cross-host portability.

An authorized user-layer Hook edit was later present and trusted on disk but
did not refresh the already-running task's Hook runtime before native
compaction. That stopped result is retained at
`product/evidence/o1-codex-session-start-continuity-stopped-2026-08-14.json`
and receives zero O1-O5 credit. The plugin projection corrects the packaging
boundary and lets Codex own materialization; exact Hook trust and an app-owned
runtime config reload remain part of the later activation gate. The inactive
candidate and its offline tests do not claim that ingestion or live refresh
has happened.

## 5. Evidence and acceptance

Evidence binds source, time, authority, operation, result, verification, and
claim limits. Deterministic validation proves structure and invariants. Real
tasks and observations support behavior and value. Accountable human judgment
owns consequential acceptance.

Historical dimensions and scenarios are sampling and risk coordinates.
Membership is not coverage, a fixture is not behavior, and a green test is not
user value. Software engineering is the first calibration profile for the
general human-Agent collaboration method and open minimum quality-conformance
profile, not the product boundary. O4 can establish only a bounded reference-
host calibration; O5 owns the separate cross-host portability claim.

The profile may bind existing protocol or evidence artifacts by fixed identity,
but it does not redefine their wire or record semantics.

## 6. Process-loss control

Every current causal increment declares a correction budget, an outcome-neutral
work budget, a material user capability-orchestration budget, hard authority
stops, and exact repository cleanup paths. Planned increments and work items are not
stored as a future queue: bind the next item only when it becomes current. A
closed outcome-neutral increment leaves the current graph and remains
recoverable from Git; a completed increment stays current only while
validator-accepted outcome evidence needs its exact causal identity. Actual
process loss must be measured by task-bound O1/O2 receipts. Their acceptance
contract separately rejects both capability-orchestration intervention and
material collaboration-loss events such as intent correction, reopened
decisions, unrequested work, unnecessary process, residue or context recovery,
and false completion correction.

Before measured execution, every outcome-bearing increment also binds one
canonical `product/evidence/*-registration.json` by raw-byte SHA-256. The
registration must cover the union of the mapped criteria's current
`preRegistrationFields`, the current acceptance-contract identity, source
eligibility, mandatory task floors, loss taxonomies, named human, stop rule,
and claim limits. The content address detects current registration drift. A
later task-bound validator must still prove that the committed binding preceded
eligible execution and bind the observation chronology; the registration is
not product authority, result evidence, or an outcome validator. Outcome-neutral
increments bind `null` rather than manufacture a task.
