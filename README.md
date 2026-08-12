# Agent Autonomy Harness

English | [简体中文](README.zh-CN.md)

Shortest path: [verify the checkout](#start-here) · [understand the loop](#what-the-harness-does) · [choose a deeper path](#progressive-paths)

Agent Autonomy Harness is an open, Agent-neutral, demand-driven human-Agent
capability control plane. It is being built to keep a real task's goal,
capability route, authority boundary, lifecycle, continuity, evidence, and
cleanup coherent without making the user orchestrate every Agent, Skill, MCP
server, Plugin, Hook, thread, worktree, catalog, or manager.

It is not a large Skills list, fixed capability catalog, or universal runtime.
External capabilities and discovery channels are replaceable inputs; the
product contract requires the Harness to observe what is available, detect a
real gap, discover only when needed, select and dispatch the smallest
sufficient route, and release it when the need ends.

The durable target is a collaboration methodology, an open standard, and an
executable reference implementation. Codex is the first reference slice, not
a dependency of the portable core.

The current implementation verifies that contract and its causal program.
Task execution, behavior evaluation, and cross-host adapters remain planned
v0.2 outcomes rather than current runtime claims.

Delivery is sequenced Codex-first: Codex is the reference host for the first
vertical slice, while the product semantics remain Agent-neutral. Stabilizing
that reference path does not satisfy cross-host O5; a distinct second Agent
host or runtime remains separate proof.

## Start here

Prerequisites: Git and Python 3.10 or newer. The current checkout is
standard-library-only; no package installation, account, or external service is
needed for local verification.

```powershell
git clone https://github.com/yiheng8023/agent-autonomy-harness.git
cd agent-autonomy-harness
python -B -m harness verify --root . --json
```

Current `main` is the paused v0.2 program. It reports `0/5` outcomes, `4/4`
guardrails, no active causal increment, and completion `in-progress`. The
current increment graph is empty; closed outcome-neutral repairs remain in Git
history instead of accumulating as a current work queue. The
guardrail-only authority reset was pushed at `a5a0834`; it counts as zero
product progress. A later six-thread capability-chain and current-asset audit
established the route-delta evaluation and clean-tree baseline without
verifying O4 or any other outcome. The accepted v0.1 repository-control milestone remains
pinned at `be498f9`; it is history, not proof that the terminal product
proposition is complete. The pause applies to an outcome-bearing increment,
not to retrospective counterexample analysis, bounded portfolio curation,
mechanism-only validation, or authority-defect repair. Historical failures may
trigger replanning without becoming acceptance authority. The next outcome
increment opens only around a bound natural task; the user is not asked to
invent one to keep the repository busy.

For the full deterministic product suite:

```powershell
python -B -m unittest discover -s tests/product -v
```

## What the Harness does

For one goal-level bound task, the Harness keeps this loop explicit:

1. bind the real goal, inputs, authority, and verification surface without
   requiring a user-specified capability route;
2. observe available healthy and authorized capability, then assess the gap;
3. discover through a source-bound adaptive channel only when the gap requires it;
4. select and preview the smallest sufficient route before meaningful side effects;
5. dispatch only inside the granted task boundary;
6. observe, recover, and verify the result, user intervention, and claim ceiling;
7. release task-scoped exposure, clean up, and leave a continuation record.

The historical v0.1 O3 evidence exercised this loop once on a source-bound
current-host task. v0.2 now tests whether the loop actually reduces user
tool-learning and orchestration burden across repeated natural tasks.

## Completion standard

The machine-readable [acceptance](product/acceptance.json) is the current
release target. Product acceptance requires all five outcomes, all four
guardrails, a completed program, no active increment, and a terminal work
graph. Tests, inventories, fixtures, memberships, and research volume may
support an outcome; they never substitute for one.

Current v0.2 outcomes are:

- O1 — one goal-level natural real task completes the demand-to-capability
  closed loop with zero user capability-orchestration intervention under a
  pre-registered protocol;
- O2 — lower user capability-orchestration burden across repeated goal-level
  real tasks;
- O3 — adaptive discovery and evidence-backed lifecycle decisions keep a broad
  and changing ecosystem outside the user's cognitive path;
- O4 — an accepted Agent-neutral human-Agent collaboration methodology and
  core minimum standard, with software engineering as the first reference
  profile;
- O5 — portable closed-loop delivery through Codex and a distinct second Agent
  host or runtime through its own thin adapter. A same-host second adapter is
  conformance evidence only and cannot pass O5.

## Progressive paths

| If you want to… | Continue with… |
| --- | --- |
| check whether the checkout is coherent | the one-command [verification](#start-here) |
| understand product boundaries and extension seams | [Architecture](docs/architecture.md) |
| inspect purpose, work, and acceptance authority | [Constitution](product/constitution.json), [program](product/program.json), and [acceptance](product/acceptance.json) |
| resume active repository work | [Continuation](docs/operations/CONTINUATION.md) after checking live Git truth |
| propose a focused change | [Contributing](CONTRIBUTING.md) |
| ask a question or report a non-sensitive problem | [Support](SUPPORT.md) |
| report a vulnerability or sensitive finding | [Security](SECURITY.md) |
| inspect provenance and rights | [NOTICE](NOTICE), [third-party notices](THIRD_PARTY_NOTICES.md), and [license policy](docs/license-policy.md) |

## Capability order and authority

For a bound need, first observe healthy and already-authorized capability. If
it is insufficient, prefer a suitable native/runtime or official route, then a
reviewed maintained external implementation, then composition. Author new
capability only for a reproducible residual gap.

Capability scope follows demand rather than catalog size. End task-scoped
exposure when the need ends; retaining a candidate inactive is distinct from
persistent activation, which requires separate evidence and authority.
The user does not need to name a capability, product, discovery channel, or
invocation syntax. Catalogs, providers, and discovery channels remain adaptive
sources rather than product authority.

Installation, enablement, account connection, meaningful cost, live dispatch,
consumer mutation, acceptance, publication, and release are separate state
transitions. Native host authorization remains authoritative.

`AGENTS.md` is execution guidance, Skills and Hooks are advisory execution
inputs, self-authored Skills are replaceable host projections, and the
peripheral ecosystem is a replaceable capability input. None can set product
direction, create causal work without an observed problem, expand authority,
or promote evidence and acceptance. Bound user intent and the current product
authority win; a conflicting or process-heavy route is rejected or downgraded.

## Product contract

The current machine authority is deliberately small:

- `product/constitution.json` — purpose, invariants, adaptive surfaces, and
  planning method;
- `product/program.json` — the finite causal program and current active or paused state;
- `product/acceptance.json` — five outcomes and four mandatory guardrails;
- `harness/` — the public product-control kernel;
- `tests/product/` — mutation tests through the public CLI seam.

Historical v0.1 evidence, research, and predecessor payloads remain retrievable
from Git history, but do not become current authority by remaining
recoverable. See the [history boundary](docs/operations/HISTORY.md).

## Community and rights

Community support is best effort. Read [Support](SUPPORT.md),
[Contributing](CONTRIBUTING.md), the [Code of Conduct](CODE_OF_CONDUCT.md), and
[Security](SECURITY.md) before sharing evidence. Remove credentials, private
memory, account state, restricted material, and sensitive logs.

Repository-owned code and documentation are licensed under Apache-2.0 unless a
file says otherwise. Third-party material retains its original rights. See
[LICENSE](LICENSE), [NOTICE](NOTICE), and [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).

Voluntary sponsorship is described in [SPONSORING.md](SPONSORING.md); it does
not purchase support priority, features, release authority, or technical
influence.
