# Architecture

Agent Autonomy Harness is an open, Agent-neutral, demand-driven human-Agent
collaboration quality harness. Its durable outputs are a demand-to-capability
collaboration methodology, an open minimum quality-conformance profile, and
executable reference adapters. It has one testable portable product contract,
one small reference seam, and replaceable host edges.

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

O1-O5 are deliberately planned and false. A repository-authored JSON file
cannot promote them: every verified outcome requires a code-owned validator
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

The v0.2 program is ready after closing the outcome-neutral Codex continuity
correction. O1-O5 remain false. Authorized product-plan delivery is real demand
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
user still supplies judgment, not transcript reconstruction. O1 can calibrate
only the exact compaction and task it observes. Repeated reliability and
cross-host portability remain separate O2-O5 burdens.

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
`adapters/agent-autonomy-harness-codex` is a replaceable Codex distribution
projection containing only a `SessionStart` Hook and a standard-library
launcher for the repository-owned adapter. It adds no Skill, MCP server, App,
prompt entry, capability router, state store, or outcome validator.
The launcher uses Python isolated mode, reads the adapter and verifier once,
and executes only those same bytes after they match the exact hashes reviewed
for that plugin version. An unknown or changed runtime is a non-blocking no-op
rather than a new repository-code execution grant.

CC Switch has no dependency role in the portable core, verifier, Codex adapter,
or Codex plugin runtime. It may remain useful as one replaceable operational
manager for shared third-party Skills, but stopping or removing it must not
change Harness semantics or disable the Codex continuity projection. Codex's
native plugin manager owns this projection's install, cache, enable, update,
disable, and uninstall lifecycle.

For the Codex reference host, reuse the host's lifecycle event before inventing
a Harness-owned continuation protocol. The fixed v0.147.0 `SessionStart` event
fires for startup, resume, clear, and compact, supplies the working directory
and source, and can return additional model context. The candidate adapter in
`harness/codex_reference.py` uses only that seam to project the live
constitution, program, acceptance, and verifier state. It ignores the supplied
transcript path, stores no session data, is a no-op outside the bound repository,
and does not validate results or emit receipts.

Goal-level demand still enters through Codex's normal native conversation
path. The adapter does not intercept or classify prompts. Using
`UserPromptSubmit` for this continuity gap would add raw-prompt access and
turn-blocking authority without causal necessity, so it is not part of the
candidate.

The adapter remains inactive. Installing or enabling a Hook is a separate
consumer and trust transition requiring explicit authority and reversible
behavior evidence. The candidate therefore establishes only an executable
reference seam and zero O1-O5 progress.

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
