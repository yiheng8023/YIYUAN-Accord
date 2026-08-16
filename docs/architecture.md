# Architecture

Agent Autonomy Harness is an open, Agent-neutral, demand-driven human-Agent
collaboration quality harness. Its durable results are portable
demand-to-outcome collaboration semantics, an open minimum quality and
evidence-conformance contract, and adaptive thin reference projections. It has
one testable portable product contract, one common read-only continuation
projection, and replaceable host and operating-system edges. Methodology,
documentation, CLI, API, Skill, plugin, MCP, Hook, adapter, package, service,
or another carrier is a non-exhaustive projection, not the product boundary.

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

The current v1.1 program is `ready`, has no active increment, and has one
source-authorized, code-pinned frozen `normativeProfileBinding`. The
[v1.0 profile candidate](DEMAND-TO-CAPABILITY-PROFILE-V1.md) and paired
[prospective cohort protocol](PROSPECTIVE-COHORT-PROTOCOL-V1.json) remain exact
historical inputs only. v1.0 froze two independently authorized generations,
registered no natural task, produced O1-O5 0/5, and stopped after deterministic
cleanup removed the successor protected resource and exact expiry task. The
verifier pins the exact v1.0 program and acceptance bytes at revision
`910ac01`; no later release may reuse that profile binding, cohort state,
authorization, task identity, ordering state, result or outcome.

v1.1 makes environment attribution part of the acceptance authority rather
than a supporting-document convention. Every future O1-O5 registration binds
one pre-task manifest, one initial authority-and-available-source envelope, one
of two environment classes, one treatment arm, and the exact Harness activation
delta if present:

```text
observed-native-minimum: exclude discoverable user-global influence at start;
                         retain system/built-in/account/managed/unknown state
user-configured:         freeze the actual relevant user starting environment

within-class comparison: matched starting manifest + authority/source envelope;
                         exact Harness activation is the only planned initial
                         route/configuration difference
task-time adaptation:    attribute Agent-selected or human-authorized lifecycle
                         deltas instead of treating start state as a ceiling
claim ceiling:            matched observational, not single-variable causal
cross-class comparison:   descriptive only, never a Harness effect
```

The manifest covers host/client version, model/provider/reasoning, account and
managed requirements, observed-or-unknown system/developer/built-in state,
working directory and instruction chain, configuration layers, rules, Skills,
plugins, Apps, MCP, Hooks, memory, managers, OS/runtime/tool/resource surface,
the initial authority-and-available-source envelope, and exact Harness package/
activation. A without-Harness baseline cannot inherit
Harness repository guidance, so it runs in a neutral workspace or real target
repository with the same task-inherent non-Harness guidance as its comparator.
Each natural task-host unit runs once in one pre-registered arm. O5's same-task
cross-host pair is pre-registered portability replication, not same-host
treatment replay. The O5 pair set must also span at least two operating-system
families, with at least one pair executing its two host units across that
boundary. Each unit binds the exact OS family/version, runtime, host
relationship and virtualization or compatibility boundary. WSL2 is Linux
hosted by Windows, not bare-metal Linux or macOS evidence, and no tested pair
implies universal OS support. The pre-task state is a starting condition, not
a static capability ceiling. After demand reveals need, the Agent may adapt under the
registered authority: it performs every supported authorized mechanic, while
any technically or authoritatively human-only action is reduced to the smallest
exact step, guided, and verified before work resumes. All human actions remain
visible in burden evidence; only transfer of Agent-owned work is prohibited.
Each decision resolves the current suitable official or maintained source from
bounded as-of evidence and binds the exact execution version, commit, or package
identity. A historical version is not a global lock, an unresolved moving target
cannot execute, and material mid-execution drift requires re-registration or an
honest stop. Missing starting identity, unregistered lifecycle drift, or failed
restoration stops the pair; it is never normalized away after a result.
Historical evidence is explicitly environment-independent, environment-bound,
or invalidated before reuse and never inherits outcome credit.

The tree now contains one code-pinned v1.1 profile and paired cohort protocol as
the frozen normative binding under that environment contract. Revision
`5ce2773`, its canonical digest, public activation identities, protected source
window, retention disposition and exact S4U expiry task were independently
authorized and code-validated before any eligible demand. This activation is
not an outcome or terminal acceptance. Their source-native eligibility,
privacy-preserving task
identity, first-eligible ordering, chronology, retention and cleanup controls
must be code-validated before any natural task can enter the cohort. Git dates
and evidence timestamps remain diagnostic consistency fields, not trusted
chronology.

Terminal release is an external-state transition over one immutable candidate,
not a final mutation inside that candidate. The tree predeclares the semantic
tag, fixed public HTTPS remote and O5 evidence-set digest. After the named human
authorizes that exact candidate and publication, the Agent creates an annotated
JSON tag. The code-owned terminal gate then requires clean `HEAD`, zero ignored
or untracked repository residue, an annotated local tag object over `HEAD`, and
the identical public tag object plus peeled commit. This removes the
self-reference loop while keeping release authorization separate from Agent-
owned mechanics.
An annotation's claimed human name and time are not authority proof. Terminal
acceptance additionally dispatches a code-owned validator for the annotation's
bound authorization source; that terminal validator remains absent until the
actual final authorization carrier and trust boundary are known. The only current
human-authorization registry entry is the active v1.1 first-freeze source
validator. Its execution-specific anchors are code-pinned, but it cannot
promote an outcome.

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

Historical v0.2 O1 was verified by three accepted, task-bound results: the public-intake rewrite
and the uninstalled Codex and Claude task-facing Skill source packages. O2 uses
three materially distinct scenarios, O3 binds their route choices, O4 accepts a
bounded Codex reference-host calibration, and O5 binds one accepted matched
Codex plus Claude Code/DeepSeek decision pair. A repository-authored JSON file
alone cannot promote an outcome: every verified outcome requires a code-owned validator
scoped to the criterion and exact causal increment for the bound task
evidence. Before measured execution, the increment freezes an immutable task
registration containing every mapped criterion's required values, the task's
source-capture eligibility and stop rule, floors, and claim limit. The same
registration binds a code-owned task-specific validator identity, committed
locator, earlier revision, and digest. The registration seam executes that
validator's preregistration check fail-closed, and later outcome evidence must
reuse the exact identity. A task-specific validator may implement a newly
observed source serialization only before the measurement event; it cannot be
added or changed after the result. It must bind source-window, environment,
registration identity and chronology, enforce its unchanged rules, and pass the
exact evidence and completed causal binding. This permits later replay of a
prebound check, not post-hoc rule changes. A generic self-report schema could
validate only its own structure, not naturalness, source truth, behavior, or
value.

The historical v0.2 program completed after the public-intake, task-facing Codex and
Claude Skill source deliveries, continuation-reconciliation implementation,
bounded Codex reference-host calibration, and pre-registered O5 matched
source-candidate gate. The first three support O1. A
criterion-scoped aggregate check supports O3 through one native-retain route
and two finite official discovery or adaptation routes. O2 uses a different
three-scenario cohort: public intake, Codex Skill source, and continuation
reconciliation, with exact baselines, two native-compaction recoveries, zero
material user orchestration or topology interventions, zero material
collaboration losses, and named-human acceptance. The similar Claude and Codex
Skill deliveries are deliberately not double-counted. O4 applies the unchanged
candidate.5 profile to those three accepted scenarios and one honestly stopped
plugin-rollover case under fixed comparators, mandatory floors, and a named-
human Codex-only claim. O5 adds one exact Codex CLI and distinct-host Claude
Code/DeepSeek task pair. Both independently returned the same fact-grounded
single-P1 `blocked` decision, and the named human accepted both outcomes, their
normalized equivalence, and only the pre-registered task/target/host/model/
adapter/date claim. Those bindings remain immutable at the v0.2 revision and
are not registered current v1.1 validators. v1.0 is stopped with O1-O5 at 0/5;
live program state comes only from the verifier. v1.1 must
prospectively preserve or strengthen the criteria requiring sustained natural
tasks, same-environment comparative burden
reduction, a real live capability lifecycle, proactive verified carrier
transition, and live reproducible cross-host and cross-operating-system release
evidence.
Authorized product-plan delivery is real demand
when its primary purpose is the required deliverable rather than exercising or
diagnosing the Harness; this does not make the task outcome-eligible without
the unchanged pre-registration, evidence, floors, and human-acceptance burden.
The current verifier and inactive adapters are not a task runtime or an
installed-host behavior result. The cross-host evidence proves bounded decision
portability for the registered O5 pair only; it does not establish adapter
support for the newer carrier, production, publication, or universal
portability.

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

Destination verification and source release are separate checks. A source
conversation may still hold source-native bytes required to re-verify a frozen
cohort authorization. The verifier therefore derives a privacy-safe
`sourceCarrierRelease` preflight without exposing the carrier path or private
event: frozen live verification retains the source, invalid or unknown state
fails closed, and only a valid unbound or revoked binding clears this one
dependency. The result is necessary but not sufficient for release; topology,
authority, reconciliation and cleanup remain separate. This is a lifecycle
guard for Agent-owned archive mechanics, not a transcript
monitor, session store, or conversation runtime.

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
source-bound as-of landscape check resolves the then-current suitable official
or maintained source and records the exact execution version, commit, or package
identity, licence or applicable terms, maturity, and reuse boundary before deciding whether to
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
authority transitions. Once authorized, the Agent owns every supported mechanic;
when host policy reserves an action to the human, the Agent supplies the minimal
exact instruction and verifies the resulting state rather than transferring
discovery, route design, recovery, or cleanup.

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

The repository as a whole is not a plugin. Portable collaboration semantics,
quality and evidence-conformance rules, and acceptance remain delivery-form-,
manager-, host-, and operating-system-neutral. OS-specific authorization,
protected storage, execution, rollback, cleanup, and evidence paths stay in
replaceable projections or evidence mechanisms.
`harness/continuation.py` derives the common bounded reconciliation projection;
host modules validate native event envelopes and supply only adapter identity,
host substrate metadata, and output translation.
`adapters/agent-autonomy-harness-codex` is a replaceable Codex distribution
projection. It contains one concise, implicitly invocable task-facing Skill
still bound only to the historical Codex-reference-calibrated candidate.5
profile, plus the inactive v1 carrier-mechanism Hook. The package-owned Hook
uses Python isolated mode, accepts only bounded native lifecycle input, stores
only bounded session-keyed compaction and clear counters in `PLUGIN_DATA`, and
removes the exact state on `SessionEnd`. It does not load task-repository code,
invoke Git, inspect prompts or transcripts, create threads, or validate
outcomes. Its checked-in commands point to an absolute fail-closed
unmaterialized interpreter sentinel; activation remains impossible until a
separate authorized materialization binds a trusted absolute runtime. Measured
activation additionally requires a new current program-frozen,
environment-attributed profile binding.

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
honest stopped counterexample preserved only in public Git history at the fixed
v0.2 revision.

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
generation. That stopped result is preserved only in public Git history at the
fixed v0.2 revision. Future
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
zero-progress result only in public Git history at the fixed v0.2 revision.
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
package and `harness/claude_reference.py`. The fixed source package's strict
manifest validation and offline semantic-parity checks pass. Historical v0.2
later obtained one matched Codex plus Claude Code/DeepSeek source-gate pair and
a bounded human equivalence judgment; that pair is not live installed-adapter
behavior and did not satisfy the stopped v1.0 O5 contract.

For the Codex reference host, reuse the host's lifecycle event before inventing
a Harness-owned continuation protocol. The fixed v0.147.0 `SessionStart` event
fires for startup, resume, clear, and compact, supplies the working directory
and source, and can return additional model context. The legacy repository-
bound adapter in `harness/codex_reference.py` uses only that seam to project
code-owned live-authority and verifier state. It hashes active increment/work
identity, excludes registration, cleanup paths, and raw verifier diagnostics,
and leaves repository state explicitly unknown for observation through a
trusted Agent execution boundary; it does not execute Git or repository-selected
configuration in model-context construction. The common projection has a 3,072-character budget inside the
Codex Hook's 4,096-character limit; an over-budget full form degrades to an
explicit hashed fallback rather than silent truncation. It ignores the supplied
transcript and session fields, stores no session data, is a no-op outside the
bound repository, and does not validate results or emit receipts. It remains a
historical mechanism seam and is not the outside-Harness v1 plugin Hook.

The public verifier separately caps per-file and cumulative bytes, parsed
structure, evidence-locator references, file count, diagnostic count, authority
enumeration, residue enumeration, and traversal depth; repeated canonical paths
reuse one immutable verification snapshot. Its future content-addressed
registration checks resolve an absolute Git executable from code-owned anchored
system installation roots outside the task repository (and on Windows only the
OS-reported system drive), reject repository-local, lookalike, UNC, non-regular,
link, and reparse candidates, strip ambient Git configuration variables, disable system
and global configuration, fsmonitor, hooks, external diff, replacement objects,
locking, paging, and prompts, and pass only fixed built-in operations. These
operations preflight blob size and stream stdout through the same hard byte
ceiling before caching. These mechanism limits are guardrails, not outcome or
installed-host evidence.

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

### Codex v1 carrier feasibility boundary

The v1 carrier route is feasible as a thin host projection, but it is not the
current candidate. Codex 0.147.0 exposes native `PreCompact`, `PostCompact`,
`SessionStart`, and `SessionEnd` events with a session identity; compact events
identify automatic versus manual compaction, plugin Hooks receive a stable
installed-package root and writable plugin-data root, and the host exposes a
same-directory thread-fork primitive. These are separate seams and must remain
separate in the adapter:

- a trusted Hook may observe lifecycle events, maintain only bounded
  session-keyed carrier-risk state, inject the frozen profile and an explicit
  remaining-capacity `unknown` state, and remove its state at session end;
- the Agent, not the Hook, decides at the predeclared material checkpoint and
  uses the host-native fork surface to create the destination, continue it,
  verify recovered goal, authority, Git and work state, and only then archive
  or release the source;
- the packaged profile and adapter are trusted installed bytes. An arbitrary
  task repository is untrusted task input, not the source of adapter code or
  product authority, and the adapter must work outside a Harness-shaped
  checkout;
- activation must bind an absolute trusted interpreter or equivalent
  app-managed runtime. It must not resolve `python`, `git`, or other executable
  names through an untrusted session working directory, and task-repository
  observation must not execute repository-controlled Git configuration;
- Hook failure, missing native fork exposure, state overflow, malformed input,
  or unavailable verification fails closed to an explicit stopped route. It
  cannot silently treat continuation as safe or transfer topology work to the
  user.

The CLI `codex fork` and App Server `thread/fork` API corroborate the native
host primitive, but Harness does not embed, proxy, or reimplement App Server
and does not make a Hook launch a second Codex client. The current Codex app
tool contract additionally proves that an Agent can fork the calling thread in
the same directory and that only completed history is copied; therefore the
Agent must transmit and independently verify the active handoff delta before
source release. The exact conservative risk threshold belongs in the new
current program-frozen profile before measured work. This feasibility decision is
mechanism-only: no Hook has been installed or enabled and no O1-O5 result is
claimed.

An authorized user-layer Hook edit was later present and trusted on disk but
did not refresh the already-running task's Hook runtime before native
compaction. That stopped result is preserved only in public Git history at the
fixed v0.2 revision and receives zero O1-O5 credit. The plugin projection
corrects the packaging boundary and lets Codex own materialization; exact Hook
trust and an app-owned runtime config reload remain part of the later activation
gate. The inactive candidate and its offline tests do not claim that ingestion
or live refresh has happened.

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
canonical `product/evidence/*-registration.json` by raw-byte SHA-256 and one
task-specific, code-owned validator by identity, committed locator, strictly
earlier revision, and digest. The registration seam executes the validator's
preregistration callback fail-closed, and later evidence must reuse that exact
identity. The
registration must cover the union of the mapped criteria's current
`preRegistrationFields`, the current acceptance-contract identity, source
eligibility, mandatory task floors, loss taxonomies, named human, stop rule,
and claim limits. The content addresses detect registration or validator drift.
The bound validator must prove that the committed binding preceded eligible
execution and bind the observation chronology; the registration is
not product authority, result evidence, or an outcome validator. Outcome-neutral
increments bind `null` rather than manufacture a task.
