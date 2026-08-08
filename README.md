# Agent Autonomy Harness

English | [简体中文](README.zh-CN.md)

An agent-neutral research harness for autonomy, human-Agent collaboration,
capability orchestration, lifecycle control, and evidence-bound engineering.

The north star is to move Agent mechanics out of the user's head while
preserving human control over goals, creative judgment, consequential
decisions, and bounded authorization.

## Decision card

- **Repository posture:** public research and falsifiable proof. There is no
  host-neutral production runtime, broad candidate-value result, or proved
  residual self-authored gap.
- **Current Skill authority:** active adapted third-party payload release: `0`.
  The inherited 19-Skill/40-file release is deprecated transition evidence,
  not a current install, update, routing, or product source.
- **Current inactive pool:** 17 reviewed exact-upstream candidates. Sixteen
  dependency-complete candidates are managed by CC Switch v3.19.2 with every
  host flag off and zero consumer projections after an ordinary restart.
  `customer-research` remains review-only and is not installed.
- **Current gate:** portfolio curation does not require a real task and may
  continue in bounded, exact-upstream, inactive cohorts. A naturally occurring
  real task and a demonstrated current-path gap are required only before
  task-time activation or behavior, value, portability, and production claims.
- **Manager boundary:** CC Switch is a replaceable operational adapter where
  suitable, not the portable product contract. PR 6086 and its fork are an
  optional upstream contribution, not a Harness dependency.
- **Current Matt provenance:** the 25 managed payloads match exact release
  `v1.2.3@6acc160e`, and CC Switch source metadata is pinned to that tag after
  a recoverable metadata-only transaction. This does not prove invocation,
  behavior, value, portability, or production readiness.

The detailed current scheduler is the
[goal-mode execution projection](docs/operations/CURRENT-GOAL-MODE-PROMPT.md).

## What problem this project addresses

Agent ecosystems expose native features, Skills, MCP servers, Plugins, Apps,
Hooks, repositories, threads, worktrees, and permission surfaces. Users should
not need to learn and manually orchestrate all of them for ordinary work.

The target experience is a bounded autonomous loop:

1. interpret the real task and authority boundary;
2. observe current host and collaboration state;
3. choose the smallest sufficient capability path;
4. activate only what the task needs;
5. verify effects, release idle resources, and surface cleanup debt;
6. preserve repository-anchored continuity when the collaboration moves.

This is not a promise that every host currently exposes the required control
surfaces. Missing telemetry or actuation remains an explicit research result.

## Product boundaries

The Harness keeps five layers distinct:

1. **Portable decision core** — intent, routing, context lifecycle, task
   topology, verification, handoff, and closure contracts.
2. **Runtime lifecycle plane** — observed state, desired state, ownership,
   leases, release, recovery, and cleanup evidence.
3. **Host adapters** — Codex, Claude Code, Kimi, and future host-specific
   events, Hooks, APIs, commands, and degradation paths.
4. **Capability ecosystem governance** — source discovery, exact revisions,
   licenses, security, dependencies, overlap, maintenance, permissions, and
   admission decisions across capability types.
5. **Consumer projections** — separately governed installation and runtime
   distribution, including CC Switch where appropriate.

Native host authorization and permission enforcement remain authoritative.
The Harness may reduce unnecessary prompts, but it does not bypass or recreate
the host permission system.

## Capability governance

Use this order unless evidence proves a better bounded route:

1. healthy native or runtime-owned capability;
2. suitable official capability;
3. reviewed and maintained external implementation;
4. composition of existing capabilities;
5. self-authored implementation only for a reproducible residual gap.

Three ownership classes remain separate:

- Official, runtime-owned, or built-in capabilities remain environment-owned
  dated baselines and are not vendored here.
- Third-party candidates remain exact upstream. This repository stores review,
  provenance, compatibility, routing, and lifecycle evidence, not a rewritten
  current payload release.
- A repository-authored Skill or other implementation may enter a future
  release only after residual-gap proof and ordinary admission. The valid
  admitted count may remain zero.

Listing, acquisition, installation, enablement, exposure, invocation,
instruction delivery, behavior, value, and portability are separate evidence
states. One does not prove the next.

## Current research lanes

The first three proof lanes are:

1. context lifecycle -> repository-anchored handoff -> continuation;
2. task topology -> branch/worktree judgment -> bounded execution and cleanup;
3. task-scoped MCP lifecycle -> release -> failure recovery.

The project also evaluates cross-Agent semantic continuity, process loss,
resource-pressure attribution, and multidimensional software-engineering
quality. Current synthetic or zero-model results do not prove live-domain,
cross-host, production, or broad-population value.

## Start here

- [Product north star](docs/strategy/PRODUCT-NORTH-STAR.md)
- [Architecture](docs/architecture.md)
- [Research and PoC plan](docs/strategy/RESEARCH-AND-POC-PLAN.md)
- [Scenario and evidence matrix](docs/strategy/POC-SCENARIO-EVIDENCE-MATRIX.md)
- [Latest continuation](docs/operations/CONTINUATION.md)
- [Open-source readiness](docs/operations/OPEN-SOURCE-READINESS.md)
- [Current Skill portfolio authority](registry/skill-portfolio-current-authority.json)
- [Program acceptance map](registry/program-acceptance-map.json)

## Repository map

- `docs/strategy/` — current product, research, evaluation, and proof plans;
- `registry/` — governed policy, evidence, topology, admission, and event data;
- `audits/` — bounded source and runtime evidence;
- `sources/` — source pins, licenses, selections, and provenance;
- `policies/` and `schemas/` — machine-checkable governance contracts;
- `scripts/` and `tests/` — builders, validators, simulations, and tests;
- `generated/` — derived projections, never independent authority;
- `skills/` and `release-manifest.json` — deprecated adapted third-party
  transition evidence, retained for history and deterministic verification.

## Verification

Run the bounded repository checks:

```bash
python -B scripts/verify_bootstrap.py
python -B scripts/verify.py
```

For the complete local test surface:

```bash
python -B -m unittest discover -s tests -v
```

A green verifier proves only the checks it actually covers. It does not prove
current live host state, candidate value, release readiness, or user acceptance.
Hosted CI is optional corroboration, not a paid acceptance dependency.

## Contributing and support

- [Contributing](CONTRIBUTING.md)
- [Security policy](SECURITY.md)
- [Code of conduct](CODE_OF_CONDUCT.md)
- [Support](SUPPORT.md)

Candidate suggestions, source corrections, security findings, host evidence,
counterexamples, and deterministic verification improvements are welcome.
Contribution does not imply admission, installation, activation, release, or
support priority.

## Open-source and safety posture

The repository is public under a layered rights model:

- repository-owned code and governance machinery: Apache-2.0;
- repository-owned documentation and public governance text: see
  [license policy](docs/license-policy.md);
- third-party material: governed by its original license and the boundaries in
  [NOTICE](NOTICE), the [license policy](docs/license-policy.md), and the
  [historical adapted-payload notices](THIRD_PARTY_NOTICES.md).

Do not publish credentials, private memory, account state, proprietary inputs,
restricted source bodies, or unsanitized consumer configuration. Runtime
installation, account connection, external writes, and trust-boundary changes
remain separately authorized operations.

Public visibility is not open-source closure. The current gates and dated
limitations are recorded in
[Open-source readiness](docs/operations/OPEN-SOURCE-READINESS.md).

## Legacy evidence

This repository was bootstrapped on 2026-07-18 from the complete Git history of
`agent-skills-curated`. That literal name, historical `skill.curated.*` IDs,
old approval events, and deprecated manifest identities remain valid historical
evidence. They are not the current product identity or routing authority.

The current boundary is recorded in
[`registry/skill-portfolio-current-authority.json`](registry/skill-portfolio-current-authority.json).
Migration history remains available in
[`docs/legacy-curated-skill-source-migration-review-2026-07-18.md`](docs/legacy-curated-skill-source-migration-review-2026-07-18.md)
and Git history.

## Sponsoring

Sponsorship is optional and does not purchase support priority, admission,
release decisions, governance exceptions, feature commitments, or technical
influence. See [Sponsoring](SPONSORING.md).
