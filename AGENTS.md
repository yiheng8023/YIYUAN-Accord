# Agent Autonomy Harness Repository Guidance

This repository is the product authority for an open, Agent-neutral,
demand-driven human-Agent collaboration quality harness. Its durable product
target is portable demand-to-outcome collaboration semantics, an open minimum
quality and evidence-conformance contract, and adaptive thin reference
projections that reuse sufficient external protocol, runtime, identity,
evidence, and evaluation layers. Methodology, documentation, CLI, API, Skill,
plugin, MCP, Hook, adapter, package, service, or another carrier is a
non-exhaustive delivery shape, not mandatory product body.

## Current authority

Start from `product/constitution.json`, `product/program.json`, and
`product/acceptance.json`. They are the current purpose, work, and acceptance
authority. `docs/operations/CONTINUATION.md` is only a navigation aid; verify
live Git truth before relying on it.

Historical registries, research records, fixtures, payloads, scripts, and tests
are inactive evidence unless the active causal increment binds them. They do
not become current authority because a file remains on disk or an old verifier
passes. Historical failures remain non-authoritative counterevidence and may
trigger replanning; lack of acceptance authority does not erase observed loss.

## Delivery discipline

- Keep exactly one causal increment and at most one work item active.
- Every work item must map to at least one product outcome or mandatory
  guardrail.
- Product progress counts only O1-O5. Guardrails, artifacts, inventory,
  exposure, fixtures, and test counts do not count as outcomes.
- State the observed problem, hypothesis, falsifier, and finite stop condition
  before adding material product or behavior work. A typo, broken link, wording
  clarification, or narrow test repair may instead bind the exact defect,
  target, and relevant check when it changes no product or behavior semantics.
- Replan when evidence falsifies the hypothesis, changes the critical path, or
  closes the increment. Do not accumulate speculative future work.
- Use `python -B -m harness verify --root . --json` and
  `python -B -m unittest discover -s tests/product -v` as the current product
  verification seam.
- Before outcome-bearing execution, bind the task-specific code validator's
  identity, committed locator, earlier revision, and digest in the immutable
  task registration; require the registration seam to pass its preregistration
  callback, and reuse the same validator identity for later outcome evidence.
  A validator added or changed after measurement cannot validate that task.
- Treat user descriptions as authoritative intent and judgment, not as an
  exhaustive fact inventory. Proactively inspect, detect omissions, disclose
  assumptions, seek counterexamples, reconcile evidence, and supplement
  coverage inside the bound task.
- A `ready` program with no active increment is nonterminal and open to the
  next causally justified increment. Absence of a natural task gates outcome
  verification and behavior or value claims; it does not complete or block the
  program. Bounded retrospective counterexample analysis, portfolio curation,
  mechanism-only validation, and authority-defect repair remain available
  when an observed problem and finite stop exist, count as zero O1-O5
  progress, and must not require the user to invent work.

## Capability and authority boundary

Prefer healthy native/runtime capability, then suitable official capability,
then a reviewed maintained external implementation, then composition. Author
only for an evidenced residual gap.

Treat model, provider, reasoning effort, and delegation as adaptive capability
routes, not a Harness-owned router or a user curriculum. Preserve sufficient
host-native selection when it is healthy. Intervene only when task risk,
quality, latency, cost, or failure evidence makes a mismatch material; then use
a supported task-scoped override, delegation, carrier transition, fallback,
stronger verification, degradation, escalation, or honest stop. Bind the
effective execution identity and lifecycle delta, but never make a current
model label, reasoning level, provider, or benchmark permanent product
authority.

Before a product-layer protocol, human-allocation model, registry, gateway,
search surface, runtime, identity or authorization system, governance kernel,
audit or provenance format, or evaluation mechanism influences a route, bind
its exact source identity, version or commit, license or applicable terms,
maturity, and reuse boundary through a source-bound as-of landscape check.
Resolve the current suitable official or maintained source at each decision;
bind the exact execution identity for that task, but do not turn one historical
version into a permanent global lock. An unresolved mutable label such as
`latest`, or material drift during execution, requires re-registration or an
honest stop.
Reuse or adapt a
sufficient existing layer; compose only when integration is the remaining
need; author only when evidence isolates a repeatable residual semantic gap.
External breadth can change the implementation route but cannot define product
authority or prove acceptance.

Goal-level demand is the normal entry. The Agent owns observation of available
capability, gap detection, source-bounded discovery when needed, route
selection, task-scoped dispatch and release, verification, and cleanup. Do not
require the user to know or name a capability, product, discovery channel, or
invocation syntax unless it is an explicit user preference or task boundary.

Code and conversation topology are Agent-owned orchestration. Preserve the
healthy current task and checkout by default, but do not wait for preventable
context quality or host-capacity failure. At material checkpoints, use
available source-bound host and task signals to decide whether the current
conversation carrier remains safe; if reliable signals are unavailable, keep
that state explicit and apply a conservative task-bound transition rule rather
than asking the user to guess. Create a branch, worktree,
repository fork, conversation fork, or new task only for bounded causal
necessity, then own carrier identity, synchronization, merge or conclusion
reconciliation, archive or release, and cleanup. Ask only when the topology
would represent a real goal divergence or cross a new authority, trust, data,
cost, destructive, or irreversible boundary.

Before archiving or releasing a source conversation carrier, inspect the
current verifier's `sourceCarrierRelease` preflight. This field covers only the
live cohort source-evidence dependency and is necessary, not sufficient, for
release. A verified destination does not make the source releasable when its
carrier still contains source-native
evidence required for a live cohort claim. `allowed=false`, an unknown state, or
an invalid authority graph means retain the source carrier and repair or revoke
the evidence dependency first; never move private source data to bypass the
guard.

Use already-installed, already-authorized, healthy capabilities proactively
when they materially improve a bound task. Within a bound task or complete
portfolio-curation contract, the Agent may perform coverage analysis, targeted
candidate discovery, static review, and exact-revision acquisition into an
isolated inactive `.tmp/` pool; a task-time discovery must also bind the actual
capability gap. Planned gates are preconditions, not grants. Installation,
enablement, accounts/OAuth, meaningful cost, execution, consumer projection,
persistent activation, and new trust or data boundaries require a scoped user
grant for the exact work and operations. After demand reveals a need, the Agent
performs every supported authorized mechanic. If the host or authority boundary
reserves an action to the human, the Agent identifies it, explains and requests
only the smallest exact step, verifies the resulting state, and resumes; it
does not make the user discover the route, variable, syntax, recovery path, or
cleanup.

Do not infer installation, enablement, account connection, model dispatch,
consumer mutation, publication, release, destructive cleanup, or a new trust
boundary. Preserve native host authorization. Keep portable contracts,
host-specific adapters, operational managers, and consumer projections
separate.

This file is execution guidance only. Skills and Hooks are advisory execution
inputs, self-authored Skills are replaceable host projections, and the
peripheral ecosystem is replaceable capability input. None can set product
direction, create causal work without an observed problem, expand authority,
or promote evidence, acceptance, or release state. Bound user intent and
`product/constitution.json`, `product/program.json`, and
`product/acceptance.json` win; reject or downgrade a conflicting or
disproportionately process-heavy route.

Capability catalogs and discovery channels are adaptive sources, not product
authority. Do not turn one catalog, provider, host, manager, or current
installation into the portable core or a standing user-learning requirement.

Treat host/client version, model, provider and reasoning effort, account or managed policy,
instruction chain, consumer configuration, rules, Skills, plugins, Apps, MCP,
Hooks, memory, managers, operating system, runtime, and tool/resource surfaces
as explicit evaluation variables. Never assume another user shares the current
maintainer's presets or that an unobservable surface is absent. For a measured
Harness-effect comparison, follow the acceptance-owned environment contract:
compare only pre-registered matched tasks with the same starting environment
and authority-and-available-source envelope, make exact Harness activation the
only planned initial route/configuration difference, and record later
Agent-selected or human-authorized changes as treatment-mediated lifecycle
deltas. The initial state is a starting condition, not a static capability
ceiling. Keep unavoidable task differences explicit, limit the claim to
matched observational evidence, and keep observed-native-minimum separate from
user-configured evidence. Count all human actions in burden; classify a
source-bound unavoidable human-only step separately from a prohibited transfer
of Agent-owned work, which remains zero.

Treat the operating system, virtualization or compatibility boundary, and
OS-specific authorization, protected storage, execution, rollback, cleanup,
and evidence path as explicit adapter variables. Resolve current supported
routes at task time and bind exact tested identities; do not lock one host
version or claim universal OS support. WSL is a Linux environment hosted by
Windows and must be recorded as such rather than represented as bare-metal
Linux or as macOS evidence.

Before applying a capability route, compare whether it adds a goal, input,
deliverable, human round trip, authority, side effect, or acceptance
requirement. An addition needs source-bound causal necessity for the bound
task; otherwise use the smaller native route or reject the capability route.

Before repository changes, inspect branch, status, HEAD, upstream,
ahead/behind, and dirty files. Preserve unrelated user changes. Use exact,
bounded targets for cleanup. Local deterministic verification is the primary
evidence surface; hosted CI is corroboration only.
