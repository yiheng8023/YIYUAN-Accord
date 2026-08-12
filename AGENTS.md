# Agent Autonomy Harness Repository Guidance

This repository is the product authority for an open, Agent-neutral,
demand-driven human-Agent collaboration quality harness. Its durable product
target is a methodology, an open minimum quality-conformance profile, and thin
executable reference adapters that reuse sufficient external protocol, runtime,
identity, evidence, and evaluation layers.

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
  before adding work.
- Replan when evidence falsifies the hypothesis, changes the critical path, or
  closes the increment. Do not accumulate speculative future work.
- Use `python -B -m harness verify --root . --json` and
  `python -B -m unittest discover -s tests/product -v` as the current product
  verification seam.
- Treat user descriptions as authoritative intent and judgment, not as an
  exhaustive fact inventory. Proactively inspect, detect omissions, disclose
  assumptions, seek counterexamples, reconcile evidence, and supplement
  coverage inside the bound task.
- A paused product program blocks outcome-bearing experimentation, not bounded
  retrospective counterexample analysis, portfolio curation, mechanism-only
  validation, or authority-defect repair. These lanes require an observed
  problem and finite stop, count as zero O1-O5 progress, and must not require
  the user to invent work.

## Capability and authority boundary

Prefer healthy native/runtime capability, then suitable official capability,
then a reviewed maintained external implementation, then composition. Author
only for an evidenced residual gap.

Before implementing a product-layer protocol, registry, gateway, search
surface, runtime, governance kernel, or evaluation mechanism, perform a
source-bound as-of landscape check. Reuse or adapt a sufficient existing layer;
compose only when integration is the remaining need; author only when evidence
isolates a repeatable residual semantic gap. External breadth can change the
implementation route but cannot define product authority or prove acceptance.

Goal-level demand is the normal entry. The Agent owns observation of available
capability, gap detection, source-bounded discovery when needed, route
selection, task-scoped dispatch and release, verification, and cleanup. Do not
require the user to know or name a capability, product, discovery channel, or
invocation syntax unless it is an explicit user preference or task boundary.

Use already-installed, already-authorized, healthy capabilities proactively
when they materially improve a bound task. Within a bound task or complete
portfolio-curation contract, the Agent may perform coverage analysis, targeted
candidate discovery, static review, and exact-revision acquisition into an
isolated inactive `.tmp/` pool; a task-time discovery must also bind the actual
capability gap. Planned gates are preconditions, not grants. Installation,
enablement, accounts/OAuth, meaningful cost, execution, consumer projection,
persistent activation, and new trust or data boundaries require a scoped user
grant for the exact work and operations.

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

Before applying a capability route, compare whether it adds a goal, input,
deliverable, human round trip, authority, side effect, or acceptance
requirement. An addition needs source-bound causal necessity for the bound
task; otherwise use the smaller native route or reject the capability route.

Before repository changes, inspect branch, status, HEAD, upstream,
ahead/behind, and dirty files. Preserve unrelated user changes. Use exact,
bounded targets for cleanup. Local deterministic verification is the primary
evidence surface; hosted CI is corroboration only.
