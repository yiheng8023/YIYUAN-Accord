# Agent Autonomy Harness Repository Guidance

This repository is the product authority for an agent-neutral autonomy,
collaboration, and capability-lifecycle harness.

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

Before repository changes, inspect branch, status, HEAD, upstream,
ahead/behind, and dirty files. Preserve unrelated user changes. Use exact,
bounded targets for cleanup. Local deterministic verification is the primary
evidence surface; hosted CI is corroboration only.
