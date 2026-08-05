# Autoresearch method-reference evaluation — 2026-08-05

## Decision card

- **Target:** `karpathy/autoresearch` at exact revision
  `228791fb499afffb54b46200aca536f79142f117`.
- **Current disposition:** high-value external method reference; direct
  Harness adoption is blocked.
- **Current action:** retain the source-bound evaluation and wait for a real,
  bounded research task before simulation. Do not install or run the upstream
  project from this checkpoint.

## What is reusable

Autoresearch and the Harness have different objectives and scopes. This
evaluation therefore asks what the Harness can learn from it, not whether
autoresearch should satisfy the Harness product contract. The upstream design
makes a narrow empirical loop concrete: establish a
baseline, isolate work on a branch, constrain the mutable surface, use
fixed-duration rounds, append a result ledger, and keep or revert each change.
Those mechanisms are relevant to the Harness goal of transferring operational
burden from the user to an Agent without losing traceability.

This is mechanism reuse, not product adoption. A future Harness experiment
would keep its own host authorization, evidence, stop, recovery, resource, and
human-review boundaries.

## What must not be transplanted

- permission bypass or disabling the host permission system;
- an indefinite loop whose only lifecycle boundary is later human interruption;
- evaluation and result reporting that remain inside the agent-editable surface;
- a single metric as sufficient evidence of research value;
- hardware-, dependency-, or domain-specific assumptions as general research
  fitness.

Issue 599 was open when observed and raises a plausible experiment-integrity
concern. It is retained as mutable external counterevidence only, not as a
confirmed defect or maintainer decision.

## Evidence boundary

The exact snapshot binds six Git blobs and a deterministic manifest digest.
No upstream body is vendored. No clone, dependency installation, GPU run,
benchmark replay, security scan, or cross-host test was performed. An exact
license artifact and security policy were not observed at the pinned revision,
so reuse rights and security readiness remain unassessed.

The schema-conformant multidimensional report therefore stays
`research-only`, with direct adoption blocked by the evidence/provenance and
authority/data floors. Independent review and acceptance were not sought.

## Next evidence gate

When a real research task exists, compare two simulations against the same
objective and acceptance surface:

1. the smallest healthy native or ad-hoc loop;
2. a Harness-governed loop using the reusable mechanisms above.

The trusted evaluator must sit outside the mutable agent surface. The trial
must pre-bind maximum rounds and spend, stop conditions, host permissions,
parent observation, recovery, tamper-evident receipts, and human review cadence.
Only a measured net benefit can justify a later implementation or third-party
admission review.
