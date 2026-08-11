# Agent Autonomy Harness

English | [简体中文](README.zh-CN.md)

Shortest path: [verify the checkout](#start-here) · [understand the loop](#what-the-harness-does) · [choose a deeper path](#progressive-paths)

Agent Autonomy Harness is an agent-neutral product for keeping a real task's
goal, capability route, authority boundary, lifecycle, continuity, evidence,
and cleanup coherent without making the user orchestrate every Agent, Skill,
MCP server, Plugin, Hook, thread, worktree, or manager.

It is not a large Skills list. External capabilities are replaceable inputs;
the Harness decides when one is needed, what authority it receives, how its
effects are observed, and when the route is released.

## Start here

Prerequisites: Git and Python 3.10 or newer. The current checkout is
standard-library-only; no package installation, account, or external service is
needed for local verification.

```powershell
git clone https://github.com/yiheng8023/agent-autonomy-harness.git
cd agent-autonomy-harness
python -B -m harness verify --root . --json
```

A valid report currently shows `5/5` outcomes and `4/4` guardrails. Completion
remains `in-progress` while the final public-delivery increment is active. A
green report proves repository-bound product consistency only; it is not a
production, release, publication, broad-value, or cross-host claim.

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

The current O3 evidence exercises this loop once on a source-bound current-host
task. It does not establish universal lifecycle support.

## Completion standard

The release acceptance authority is the machine-readable
[acceptance](product/acceptance.json). Product acceptance requires all five
outcomes, all four guardrails, a completed program, no active increment, and a
fully terminal increment/work graph. Tests, inventories, fixtures, and research
volume may support an outcome; they never substitute for one.

Current evidence is intentionally bounded:

- O2 binds one user-provided real task to a non-null capability route.
- O3 binds one 60-entry non-Cartesian evaluation and one six-phase current-host
  lifecycle receipt with explicit attestation limits.
- O4 binds one fresh receiver to one repository state with zero material
  restatement.
- O5 covers named Harness cleanup targets, not unrelated host storage.

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

## Product contract

The active machine authority is deliberately small:

- `product/constitution.json` — purpose, invariants, adaptive surfaces, and
  planning method;
- `product/program.json` — the one active causal increment and its finite stop;
- `product/acceptance.json` — five outcomes and four mandatory guardrails;
- `harness/` — the public product-control kernel;
- `tests/product/` — mutation tests through the public CLI seam.

Historical research and predecessor payloads remain retrievable from Git
history but do not become current authority by remaining available. See the
[history boundary](docs/operations/HISTORY.md).

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
