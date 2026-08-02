# Official External Capability Baselines

This repository may evaluate official Skills, capability packages, workflow
templates, and similar public capability bundles from Agent, runtime, platform,
or tool ecosystems as dated external capability baselines.

The purpose is cross-agent coverage calibration, not vendor-specific cloning.
Each record is a dated external baseline for coverage comparison, gap analysis,
and routing calibration.

## Definition

An official external capability baseline is a pinned snapshot of an
environment-owned or ecosystem-owned capability source used to answer:

- what capability boundary the official source claims;
- whether current native, runtime, plugin, MCP, App, Hook, or curated Skill
  surfaces already cover that boundary;
- whether any gap is functional, procedural, resource-based, script-based,
  trigger-based, artifact-standard-based, license-based, or portability-based;
- whether the correct disposition is `covered`, `reference`,
  `review-candidate`, or `skip`.

Baseline status does not create ownership. It is not managed inventory, not an
approved Skill, not release payload, not proof of live availability, and not an
execution route.

## Relationship To Governed Candidates

Official external baselines and reviewed candidates serve different roles:

- An official external baseline is evidence for coverage comparison, gap
  analysis, routing calibration, and future intake decisions.
- A reviewed candidate preserves exact upstream identity and bytes while this
  repository governs provenance, license, security, dependency, maintenance,
  overlap, routing, composition, and admission evidence. Its body does not
  enter `skills/` or `release-manifest.json`.

The transition from baseline evidence to curated content is never automatic.
It requires the normal intake path:

```text
discover
-> candidate
-> source pin
-> license/provenance check
-> security review
-> portability review
-> overlap review
-> validation
-> topology update
-> reviewed candidate decision
-> separately authorized manager or host transaction
```

## Disposition Semantics

- `covered`: current native, runtime, ecosystem, recipe, or curated capability
  is materially sufficient for the relevant workflow. Do not duplicate it.
- `reference`: the source is useful as evidence or design input, but should not
  be copied, adapted, executed, or released.
- `review-candidate`: an exact-upstream candidate may be worth further review,
  but no installation, enablement, execution, or promotion follows without its
  separate authority and verification boundary.
- `skip`: the source is product-specific, not portable, not useful, unsafe,
  license-incompatible, redundant, or outside repository scope.

`review-candidate` is not approval. `reference` is not execution. `covered` is
not installation proof. `skip` does not erase historical evidence.

## Required Matrix Fields

Each baseline coverage matrix should record at least:

- source name and URL;
- inspected revision or release identifier;
- inspection date;
- license posture;
- capability or Skill name;
- category;
- purpose;
- native coverage;
- ecosystem coverage;
- curated Skill coverage;
- gap or risk;
- disposition;
- reason.

## Current Baseline Instances

- `docs/anthropic-official-skills-coverage.md` records the first official
  external capability baseline instance.

Future official baselines should follow this document without naming or
privileging any specific vendor, Agent, runtime, platform, or tool ecosystem.
