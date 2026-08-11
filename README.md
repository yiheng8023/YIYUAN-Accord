# Agent Autonomy Harness

English | [简体中文](README.zh-CN.md)

Agent Autonomy Harness is an agent-neutral product for keeping a real task's
goal, capability route, authority boundary, lifecycle, continuity, evidence,
and cleanup coherent without making the user orchestrate every Agent, Skill,
MCP server, Plugin, Hook, thread, worktree, or manager.

The product is not a large Skills list. External capabilities are replaceable
inputs and adapters; the Harness is the decision and lifecycle contract that
decides when they are needed, what authority they receive, how their effects
are observed, and when they are released.

## Current product state

- Release target: `v0.1`.
- Product outcomes: `5/5` currently verified.
- Mandatory guardrails: `4/4` currently pass.
- Active causal increment: `increment.current-official-route-evaluation-slice`.
- Completion remains `in-progress` while the program closeout work is active.
  O3 is bound to one source-reconciled scorecard and one current-host lifecycle
  transaction; this is not a general lifecycle or cross-host claim.

The current reset is itself a user-provided real task. It exposed a genuine
Harness failure: a predecessor research and curation program could remain
green while product delivery, user burden, and cleanup were not the controlling
measures. The new product-control seam rejects unmapped work, multiple active
increments, predecessor authority in active surfaces, and guardrails counted
as product progress.

## Product contract

The current machine authority is deliberately small:

- [constitution](product/constitution.json) — purpose, fixed invariants,
  adaptive surfaces, and planning method;
- [program](product/program.json) — one active causal increment and bounded
  future increments;
- [acceptance](product/acceptance.json) — five outcomes plus four mandatory
  guardrails;
- [architecture](docs/architecture.md) — portable core, lifecycle plane, host
  adapters, and consumer projections.

Historical research, fixtures, registries, and regression tools remain
retrievable from Git history, but they have no current product, planning,
acceptance, runtime, or release authority. The former local ignored quarantine
was physically removed; transient ignored bytecode caches are not authority and
remain cleanup items whenever tooling recreates them.

## Verify

Run the current public product seam:

```powershell
python -B -m harness verify --root . --json
python -B scripts/verify.py
python -B -m unittest discover -s tests/product -v
```

A PASS means only that the current product plan, acceptance mapping, evidence
bindings, authority boundary, and identity guard are internally consistent. O3
and O4 each bind one bounded current-host event. They do not prove cross-host
behavior, production readiness, release readiness, or broad user value.

## Delivery method

The project uses a hybrid method:

1. fix the purpose, product boundary, authority floor, and release acceptance;
2. keep exactly one short causal increment active;
3. state the observed problem, hypothesis, falsifier, acceptance mapping, and
   finite stop condition;
4. implement and observe the smallest product slice;
5. replan only when evidence changes the causal model or the increment ends.

Research, ecosystem discovery, inventory growth, static review, zero-model
fixtures, and test counts may support an outcome. They never count as an
outcome themselves.

Minimal sufficiency is measured against demand coverage, not against the
smallest possible capability count. A bounded portfolio-curation increment may
proactively compare and acquire exact candidates into an inactive review pool;
live installation, activation, accounts, and consumer projection remain
separate authority transitions.

## Capability order

For a bound need, prefer:

1. healthy native or runtime-owned capability;
2. suitable official capability;
3. reviewed and maintained external implementation;
4. composition of existing capabilities;
5. repository-authored implementation only for an evidenced residual gap.

Installation, enablement, account connection, live dispatch, consumer
mutation, acceptance, release, and publication remain distinct transitions.

## Repository map

- `product/` — current constitution, program, acceptance, and bounded evidence;
- `harness/` — current product-control kernel;
- `tests/product/` — tests at the public product seam;
- `docs/architecture.md` and `docs/strategy/` — current product design and
  triggered research plan;
- `docs/operations/` — compact continuation and current execution projection;
- Git history — predecessor and later evidence remain retrievable without
  shipping them in every current checkout. See the
  [history boundary](docs/operations/HISTORY.md).

## Safety and rights

Native host authorization remains authoritative. The Harness does not bypass
permission systems or infer new trust, cost, destructive, account, publication,
release, or irreversible authority.

Repository-owned code is Apache-2.0 unless a file states otherwise. Third-party
material retains its original rights; see [NOTICE](NOTICE),
[THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md), and
[license policy](docs/license-policy.md).
