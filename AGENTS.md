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
passes.

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

## Capability and authority boundary

Prefer healthy native/runtime capability, then suitable official capability,
then a reviewed maintained external implementation, then composition. Author
only for an evidenced residual gap.

Do not infer installation, enablement, account connection, model dispatch,
consumer mutation, publication, release, destructive cleanup, or a new trust
boundary. Preserve native host authorization. Keep portable contracts,
host-specific adapters, operational managers, and consumer projections
separate.

Before repository changes, inspect branch, status, HEAD, upstream,
ahead/behind, and dirty files. Preserve unrelated user changes. Use exact,
bounded targets for cleanup. Local deterministic verification is the primary
evidence surface; hosted CI is corroboration only.
