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
evidence. The active O1 continuity task has one validator bound to its exact
thread, demand turn, increment, work item, immutable registration, and host
event chronology; it cannot validate another task or criterion. Before a task
exists, a generic self-report schema could validate only its own structure,
not naturalness, source truth, behavior, or value; G4 blocks any other
outcome-bearing increment until its smallest required validation path exists.

The v0.2 program has one active Codex same-task continuity increment and one
active work item. O1-O5 remain false. The current verifier is not an accepted
methodology, quality profile, task runtime, reference adapter, or cross-host
proof; this task can establish only one bounded O1 reference-host outcome.

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

For the Codex reference host, reuse the host's pre-execution task-entry event
before considering a Harness-owned entry protocol. The fixed v0.147.0
`UserPromptSubmit` input provides task text, working directory, session and turn
identities, model, permission mode, and transcript location; its output can add
model context or block the turn. That makes it only a possible thin entry seam,
not an evidence store, lifecycle observer, task validator, or accepted adapter.
Because a handler receives the raw prompt and can change turn behavior, any
projection or enablement remains a separate consumer, prompt-data, and trust
decision. It stays off until a bound task exposes a repeatable entry-recall gap
and a reversible test can measure distinct value.

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
