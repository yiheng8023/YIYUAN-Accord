# Public Real-Task Sourcing — Fallback Inventory (2026-08-05)

## Decision card

- **Status:** `fallback-sourcing-inventory-only`
- **Primary path:** the user-owned semi-automated production-CAD R&D chain is now the higher-value real task. This public inventory must not displace it or expose private repository identity.
- **Result:** three public issues passed a read-only sourcing screen, all from one small and recently active repository. They are fallback test inputs, not accepted Harness work, candidate-Skill suitability proof, or authorization to contribute upstream.
- **Current action:** no external task should be activated while the user-owned task can supply the native/current baseline. Re-check this inventory only if a fallback is later needed.

## Boundaries and method

Observation date: **2026-08-05 (Asia/Shanghai)**.

This pass used only public, first-party repository surfaces: project issues, repository contribution rules, commit history, and unauthenticated GitHub public metadata. It did not log in, comment, claim an issue, fork, clone, download or execute third-party code, create an issue or pull request, enable a Skill, or modify CC Switch.

The admission screen required all of the following:

1. the issue is currently open, unassigned, and has no visible linked branch or pull request;
2. the repository shows recent maintenance and explicitly accepts external contributions;
3. the issue has a bounded local verification surface and no required personal data, account, paid service, or production system;
4. the likely work is small enough for an isolated native/current baseline;
5. any possible relation to a reviewed Harness effect group is a testable hypothesis, not a name match;
6. setup, execution, issue claiming, and upstream publication remain separate authorization gates.

The relevant current Harness comparison authority is
[`registry/skill-portfolio-candidate-demand-mapping-2026-08-03.json`](../../registry/skill-portfolio-candidate-demand-mapping-2026-08-03.json). The public issues below align most closely with `effect.engineering-lifecycle`; they do not prove that any of its four candidates is needed.

## Ranked fallback candidates

### 1. thingctx/thingctx #77 — `import openapi --out -` writes a file named `-`

Sources: [issue #77](https://github.com/thingctx/thingctx/issues/77) · [contribution rules](https://github.com/thingctx/thingctx/blob/main/CONTRIBUTING.md) · [repository activity](https://github.com/thingctx/thingctx/commits/main/)

**Facts observed**

- The issue was open, unassigned, labelled `good first issue` and `help wanted`, with no visible branch or pull request and no comments.
- The issue supplies one concrete input and an observable mismatch: `thingctx import openapi spec.json --out -` creates a file named `-` instead of writing to standard output, preventing piping.
- The repository contribution rules require small changes, offline tests via `pytest -m "not network"`, issue claiming before a pull request, DCO sign-off by a real accountable human, and human understanding of AI-assisted work.
- The repository was not archived, was pushed on 2026-08-04, and its commit history showed activity on that date.

**Inference and proposed verification surface**

- This is the strongest fallback because the defect and externally visible acceptance oracle are compact: output reaches stdout, piping works, no file named `-` appears, and relevant offline tests pass.
- It can test `effect.engineering-lifecycle` only indirectly. A `source-driven-development` arm might improve repository-source and convention traceability; native/current may already be fully sufficient. If native/current is sufficient, the correct result is **no candidate selected**.

**Unverified**

- No source tree or test suite was acquired, so the exact change size, dependency setup, Windows behavior, and existing test seam remain unknown.
- The issue does not itself prescribe the exact regression-test matrix.

**Expected side effects and stop conditions**

- A later local run would require separate authority to acquire exact upstream code into an isolated worktree or temporary root and execute its offline test commands.
- Commenting to claim the issue, forking, and opening a pull request are independent external-write decisions and are not authorized by this inventory.
- Stop if the issue is closed, assigned, claimed, gains a linked implementation, no longer reproduces at the pinned revision, requires network/account access, or native/current already meets the oracle without a material gap.

### 2. thingctx/thingctx #89 — add tests for two pure-function paths

Sources: [issue #89](https://github.com/thingctx/thingctx/issues/89) · [contribution rules](https://github.com/thingctx/thingctx/blob/main/CONTRIBUTING.md) · [repository activity](https://github.com/thingctx/thingctx/commits/main/)

**Facts observed**

- The issue was open, unassigned, labelled `good first issue` and `help wanted`, with no visible branch or pull request and no comments.
- It names two untested surfaces in `src/thingctx/lint.py`: the rule for a description that repeats an affordance name and `LintFinding.as_dict()`.
- The issue describes both as pure functions over a dictionary; the repository requires offline tests.

**Inference and proposed verification surface**

- This is the cleanest negative-control task: native/current should be able to recover adjacent test conventions, add boundary cases, and prove the public behavior without accounts or external services.
- The only plausible reviewed effect-group comparison is source/convention traceability within `effect.engineering-lifecycle`. There is no admitted TDD candidate in the current sixteen-item cohort. Inventing one or treating an unrelated candidate as TDD would invalidate attribution.
- An acceptable local oracle would cover the equality rule's positive and negative boundaries, stable `as_dict()` output, adjacent suite compatibility, and the repository's offline test command.

**Unverified**

- The exact expected dictionary shape, adjacent fixtures, parameterization style, and coverage gaps have not been inspected.
- The issue does not enumerate all required edge cases, so the oracle must be source-bound before implementation.

**Expected side effects and stop conditions**

- A later run would write only to an isolated checkout and test artifacts after separate acquisition/execution authority.
- Stop if source inspection shows existing equivalent coverage, the issue is no longer unclaimed, dependencies require a wider boundary, or the native/current arm is sufficient and leaves no candidate-specific hypothesis to test.

### 3. thingctx/thingctx #70 — worked `exec://` Git example with destructive action gated

Sources: [issue #70](https://github.com/thingctx/thingctx/issues/70) · [contribution rules](https://github.com/thingctx/thingctx/blob/main/CONTRIBUTING.md) · [repository activity](https://github.com/thingctx/thingctx/commits/main/)

**Facts observed**

- The issue was open and unassigned, labelled `documentation`, `good first issue`, and `help wanted`, with no visible linked implementation.
- Public metadata showed no current assignee and no visible linked branch or pull request on 2026-08-05.
- The requested example must allow only `git`, expose safe `status`/`log`/`diff` actions, mark a destructive action such as `reset --hard` as `tc:Destructive`, preserve each filled placeholder as one argv element, and demonstrate that the approval gate refuses the destructive action.
- The issue names the source docstring and existing example to follow, requests two example artifacts, and gives a reviewer-visible finish line. It says no new library code is needed.

**Inference and proposed verification surface**

- This task is unusually relevant to Harness authority and rollback concerns and could compare native/current source tracing with one `source-driven-development` or `documentation-and-adrs` arm.
- It ranks third because its negative test contains a genuinely destructive command. The command must never target a user repository and the refusal must be proved before any execution path can reach Git.

**Unverified**

- The actual approval-gate enforcement, subprocess isolation, test seam, platform portability, and whether the smoke test can remain fully offline have not been inspected.
- The absence of an assignee is not a maintainer confirmation that a new claimant may start; the contribution rules require a public claim and maintainer confirmation.

**Expected side effects and stop conditions**

- Any later test must use a disposable repository created solely for the experiment, an explicit allowlist, a pre-execution observer, and exact cleanup. It must never reference the Harness worktree or another user repository.
- Stop before acquisition if those controls cannot be established. During a later run, stop on any path that can execute the destructive action, any unexpected executable, network access, or inability to independently attest refusal.

## Source-concentration and maintenance caveat

All three retained issues come from `thingctx/thingctx`. The repository is small and its visible public history is recent, although it showed a push and commits on 2026-08-04 and has explicit contribution and AI-assistance rules. Therefore:

- recent activity is a fact;
- long-term maintenance maturity and review latency are **not** proved;
- three issues from one repository are not representative evidence for cross-project or cross-host value;
- they should never be run as a batch or used to claim portfolio coverage.

## Screened out

- [langfuse/langfuse #15733](https://github.com/langfuse/langfuse/issues/15733) was open and labelled `good first issue`, but it already had an assignee. It was rejected to avoid duplicate work; its full local setup also carries a materially larger service/dependency surface.
- [github/docs #34987](https://github.com/github/docs/issues/34987) was open, unassigned, `help wanted`, and SME-reviewed, but its requested workflow-run state documentation did not identify one exact editable article or deterministic local oracle. GitHub's own [contribution guide](https://docs.github.com/en/contributing/collaborating-on-github-docs/about-contributing-to-github-docs) also says REST API reference pull requests are not accepted, while the issue links the REST reference and asks for inclusion on other pages. The intended contribution surface needs maintainer clarification, so it failed this small, locally reproducible screen.
- Search results that were already assigned, already had an active pull request, required large-model/GPU infrastructure, depended on account data, or lacked a concrete acceptance surface were rejected rather than retained as weak candidates.

## Revalidation gate

This document is a dated discovery inventory, not a live queue. Before selecting any entry later:

1. re-read the issue, comments, assignment, linked development, repository contribution rules, and current default-branch activity;
2. bind an exact upstream revision and a local-only data/authority boundary;
3. decide whether the goal is a private Harness comparison or a possible upstream contribution;
4. establish the native/current baseline first;
5. enable at most one relevant reviewed candidate only after a reproducible gap appears;
6. restore the candidate to inactive state and remove the isolated checkout and process artifacts after the comparison;
7. require separate user authority before claiming, forking, commenting, publishing, or opening a pull request.

Because a user-owned production-CAD R&D need is now available, these fallback tasks should remain inactive unless that path becomes unsuitable for a bounded Harness experiment.
