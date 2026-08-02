# Superpowers plugin and spec-governance research — 2026-08-02

## Decision card

- **Codex:** Superpowers is authored by Jesse Vincent / `obra` and distributed
  through OpenAI's curated plugin marketplace. It is not OpenAI-authored.
- **Kimi Code:** Kimi's own marketplace registry lists Superpowers as
  `tier: curated`, sourced from `obra/superpowers`. It is not `kimi-official`.
- **Operational consequence:** where the host plugin is installed, enabled,
  healthy, and exposes the required Skills, CC Switch should not install a
  second standalone copy for that same host. Inventory ownership and live
  exposure still require separate verification.
- **Spec policy:** Matt-like and Superpowers workflows are not a binary choice
  between specs and no specs. They assign different authority, granularity,
  lifetime, and change cost to specs and plans.
- **Governance:** multiple high-quality Skill sets may coexist in inventory;
  only one workflow orchestrator should own a phase. Other Skills should be
  invoked as bounded primitives.

## Scope and claim boundary

This is a dated primary-source review plus one zero-side-effect synthetic dry
simulation. It does not prove live Skill loading, instruction delivery,
behavior causation, cross-host portability, real-task value, or the superiority
of Matt, Superpowers, or the Harness.

No Skill, Plugin, Hook, MCP server, or CC Switch state was installed, removed,
enabled, disabled, or changed. No external model was dispatched.

## Frozen sources

Retrieved on 2026-08-02:

- OpenAI plugin catalog at commit
  [`11c74d6`](https://github.com/openai/plugins/tree/11c74d6ba24d3a6d48f54a194cd00ef3beea18f9/plugins/superpowers).
- Kimi Code marketplace at commit
  [`e22479a`](https://github.com/MoonshotAI/kimi-code/blob/e22479a62eed9c3b78a67b313f4332c2c0ba9670/plugins/marketplace.json).
- Superpowers release `v6.2.0`, commit
  [`3dcbd5c`](https://github.com/obra/superpowers/tree/3dcbd5c4b48e02263fbf4a3c01e3fe4f81d584d9),
  matching the locally exposed plugin version reviewed for workflow semantics.
- Current Matt Skills main at commit
  [`2ab9580`](https://github.com/mattpocock/skills/tree/2ab958093e83e0ec752e6c1c5932da465bf23e0c).
- Matt's user-supplied X post locator:
  [`2083563195671667176`](https://x.com/i/status/2083563195671667176).
  The locator is now bound, but the current text retrieval surface returned no
  post body, so exact wording and surrounding thread context remain unverified.
- Harness simulation fixture
  `audits/software-lifecycle-thin-slice-zero-model-domain-fixture-calibration-v3-2026-07-27/RAW-ARTIFACTS/SOURCE-BUNDLE.json`.

## Plugin provenance and deduplication

### Codex

OpenAI's own plugin repository contains a Superpowers plugin projection. The
upstream Superpowers manifest identifies Jesse Vincent / `obra` as author and
`obra/superpowers` as the source repository. The maintainer also records that
Superpowers shipped through the Codex plugin repository.

The public `openai/plugins` copy inspected at the frozen commit reports
Superpowers `5.1.3`, while the local OpenAI-curated cache contains `6.2.0` and
its reviewed README and four workflow Skills match the author's `v6.2.0` Git
blobs. This is evidence that the public catalog snapshot and effective remote
distribution can drift; catalog presence or version alone is not a live
enablement or exposure proof.

This supports the classification:

```text
content authority: obra/superpowers
distribution and review surface: OpenAI curated plugin marketplace
host projection: Codex plugin
```

Primary sources:

- [OpenAI plugin repository](https://github.com/openai/plugins)
- [Superpowers upstream](https://github.com/obra/superpowers)
- [Maintainer's Codex marketplace notice](https://github.com/obra/superpowers/issues/984)

### Kimi Code

Kimi's official repository distinguishes `official`, `curated`, and
third-party/custom sources. Its current marketplace file lists Superpowers as
`curated` and points directly to `https://github.com/obra/superpowers`.
Kimi's documentation defines trust badges and lifecycle operations for those
tiers. The Superpowers author documentation describes the Kimi-specific plugin
manifest and session-start Skill loading.

This supports the classification:

```text
content authority: obra/superpowers
distribution and review surface: Kimi-maintained marketplace, curated tier
host projection: Kimi plugin
```

Primary sources:

- [Kimi marketplace registry](https://github.com/MoonshotAI/kimi-code/blob/e22479a62eed9c3b78a67b313f4332c2c0ba9670/plugins/marketplace.json)
- [Kimi plugin documentation](https://www.kimi.com/code/docs/en/kimi-code-cli/customization/plugins.html)
- [Superpowers Kimi integration](https://github.com/obra/superpowers/blob/3dcbd5c4b48e02263fbf4a3c01e3fe4f81d584d9/docs/README.kimi.md)

### CC Switch consequence

The deduplication rule must be per host and per effective capability, not a
global deletion rule:

1. Prefer the host-owned plugin projection when it is installed, enabled,
   healthy, current enough, and exposes the required Skills.
2. Do not separately install the same Superpowers Skills through CC Switch for
   that host.
3. Retain provenance, version, enablement, exposure, and fallback as separate
   lifecycle facts.
4. A different Agent without a working plugin projection may still require a
   separately governed projection; one host's plugin does not prove another
   host's coverage.

Current local inspection found no standalone `superpowers*` directory under
the checked CC Switch, shared Agent, or Codex user Skill roots. The current
Codex runtime exposed the namespaced plugin Skills. This is a dated inventory
snapshot, not a permanent health guarantee.

## Matt and Superpowers on specs

### What current primary sources establish

Matt's current README criticizes process frameworks that take control away
from the user and make workflow bugs hard to repair. It describes his Skills
as small, adaptable, and composable. However, the same repository contains a
`to-spec -> to-tickets -> implement` flow. `to-spec` produces an extensive
specification while deliberately excluding file paths and code snippets that
may become stale quickly. `grilling` keeps factual lookup with the Agent and
decisions with the user.

Primary sources:

- [Matt Skills README](https://github.com/mattpocock/skills/blob/2ab958093e83e0ec752e6c1c5932da465bf23e0c/README.md)
- [`to-spec`](https://github.com/mattpocock/skills/blob/2ab958093e83e0ec752e6c1c5932da465bf23e0c/skills/engineering/to-spec/SKILL.md)
- [`grilling`](https://github.com/mattpocock/skills/blob/2ab958093e83e0ec752e6c1c5932da465bf23e0c/skills/productivity/grilling/SKILL.md)

Superpowers `v6.2.0` makes workflow selection mandatory. Its default path
requires brainstorming, a reviewed design specification, a detailed
implementation plan, TDD, review, and branch completion. The plan carries
requirements into explicit constraints, tasks, files, commands, and expected
test outcomes. Yet `executing-plans` explicitly returns to review when the
partner changes the plan or the fundamental approach changes.

Primary sources:

- [`using-superpowers`](https://github.com/obra/superpowers/blob/3dcbd5c4b48e02263fbf4a3c01e3fe4f81d584d9/skills/using-superpowers/SKILL.md)
- [`brainstorming`](https://github.com/obra/superpowers/blob/3dcbd5c4b48e02263fbf4a3c01e3fe4f81d584d9/skills/brainstorming/SKILL.md)
- [`writing-plans`](https://github.com/obra/superpowers/blob/3dcbd5c4b48e02263fbf4a3c01e3fe4f81d584d9/skills/writing-plans/SKILL.md)
- [`executing-plans`](https://github.com/obra/superpowers/blob/3dcbd5c4b48e02263fbf4a3c01e3fe4f81d584d9/skills/executing-plans/SKILL.md)

### Bound X locator; text pending independent capture

The user supplied the exact X status locator for the statement that Matt
regards a spec as a cache or temporary worker rather than a hard, end-to-end
constraint. That resolves source identity, but the current text retrieval
surface exposed no post body. Until the post text and surrounding context are
captured, the interpretation remains user-reported rather than independently
verified. Current repository material is directionally compatible with lower
spec rigidity, but it does not support the stronger claim that Matt rejects
specs.

Matt's separately published AI Coding Dictionary is more explicit: it defines
a spec as a handoff artifact for multi-session work, says it changes as work
progresses, and treats it as the durable intent carrier because sessions are
disposable. That source supports **mutable but persistent** task authority, not
a merely disposable cache. It also reinforces the separation between what is
being built and how each session performs its portion.

- [Matt's Spec definition](https://github.com/mattpocock/dictionary-of-ai-coding/blob/251fec7ec3b08059e4203863024e6123090a54e3/dictionary/Spec.md)

### Comparative judgment

Neither approach is universally better:

| Dimension | Matt-like workflow | Superpowers workflow |
|---|---|---|
| Primary optimization | Adaptability and user control | Repeatability and execution discipline |
| Spec/plan granularity | Lighter and less implementation-specific | Detailed and execution-oriented |
| Change cost | Lower | Higher because review and replanning repeat |
| Drift control | More dependent on current human/Agent judgment | Stronger explicit constraints and checks |
| Handoff and auditability | Lower by default | Higher by default |
| Main failure mode | Under-specification or implicit drift | Ceremony, stale detailed plans, or excess governance |

Superpowers is strict but not immovable. Matt uses specs but resists process
ownership and rapidly stale implementation detail. The substantive difference
is the authority and lifecycle of the artifact, not the existence of the
artifact.

## Synthetic phase-change simulation

The frozen capped-backoff fixture was extended only in the simulation with this
event: after initial approval, the cap changes and jitter is added. The cap
value, jitter semantics, random source, and test tolerance were deliberately
left undecided.

| Path | Estimated coordination steps | Human decisions | Logical artifact updates | Main trade-off |
|---|---:|---:|---:|---|
| Matt-like | about 7 | at least 4 | 1 spec revision | Fastest adaptation; more reliance on current judgment |
| Superpowers | about 11 | at least 5 | design spec plus implementation plan | Lowest modeled drift; highest replanning cost |
| Harness layered composition | about 8-10 | at least 4 | 1 atomic projection set | Balanced only if invalidation and projection are automated |

The simulation supports mechanism comparison only. It does not measure elapsed
time, implementation quality, user satisfaction, or net value. The Harness
path is especially conditional: if `current`/`superseded` projection and
validation remain manual, its overhead may equal or exceed Superpowers.

## Recommended governance model

Use layered authority rather than one universal spec rule:

1. **Persistent hard floors:** safety, permission, provenance, data boundary,
   irreversible side effects, rollback, and truthful evidence claims.
2. **Durable decisions:** ADRs and domain language, versioned and explicitly
   superseded when changed.
3. **Stage-scoped specs and acceptance:** authoritative for the active stage,
   mutable through an explicit re-intake and approval transition.
4. **Short-lived execution plans:** replaceable and allowed to expire; never
   silently treated as current after a material phase change.
5. **Scratch and prototypes:** disposable evidence-generation aids, not product
   authority.
6. **Code, tests, and runtime evidence:** verification surfaces, not automatic
   substitutes for intent or authorization.

Multiple Skill families can coexist in inventory under these controls:

- task-bound routing instead of simultaneous activation;
- one active workflow orchestrator per phase;
- bounded primitive use from other Skill sets;
- explicit overlap and conflict rules;
- source, version, host projection, and permission tracking;
- phase-change rerouting and old-plan invalidation;
- observable verification, safe fallback, and retirement criteria;
- net-benefit comparison against a lighter path before promotion to default.

This aligns with the Harness north star: portable decision contracts,
host-specific adapters, governed capability sources, native/official/current
reuse first, and self-authored machinery only for an evidenced residual gap.
It also creates a falsifier: if the layered governance path cannot beat a
lighter path on real tasks after its coordination cost is counted, it should
be simplified rather than promoted.
