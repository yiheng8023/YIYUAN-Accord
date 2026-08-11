# Agent Autonomy Harness

English | [简体中文](README.zh-CN.md)

Shortest path: [verify the checkout](#start-here) · [understand the loop](#what-the-harness-does) · [choose a deeper path](#progressive-paths)

Agent Autonomy Harness is an agent-neutral product being built to keep a real task's
goal, capability route, authority boundary, lifecycle, continuity, evidence,
and cleanup coherent without making the user orchestrate every Agent, Skill,
MCP server, Plugin, Hook, thread, worktree, or manager.

It is not a large Skills list. External capabilities are replaceable inputs;
the product contract requires the Harness to decide when one is needed, what authority it receives, how its
effects are observed, and when the route is released.

The current implementation verifies that contract and its causal program.
Task execution, behavior evaluation, and cross-host adapters remain planned
v0.2 outcomes rather than current runtime claims.

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
guardrail-only authority reset was pushed at `a5a0834`; it counts as zero
product progress. The accepted v0.1 repository-control milestone remains
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

For one bound task, the Harness keeps this loop explicit:

1. bind the real goal, inputs, authority, and verification surface;
2. choose native, official, reviewed external, composed, or authored capability;
3. preview the route before meaningful side effects;
4. activate only inside the granted task boundary;
5. observe the result, user intervention, and claim ceiling;
6. project only where a host or consumer actually requires it;
7. roll back, clean up, and leave a continuation record.

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

- O1 — one natural real task completes the autonomous closed loop with zero
  user tool-orchestration intervention under a pre-registered protocol;
- O2 — lower user tool-orchestration burden across repeated real tasks;
- O3 — broad-portfolio coexistence and evidence-backed capability decisions;
- O4 — an accepted Agent-neutral software-engineering evaluation and minimum
  standard;
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

For a bound need, prefer a healthy native/runtime capability, then a suitable
official capability, then a reviewed maintained external implementation, then
composition. Author new capability only for a reproducible residual gap.

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
from Git history or `product/evidence`, but do not become current authority by
remaining available. See the [history boundary](docs/operations/HISTORY.md).

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
