# Anthropic Official Skills Coverage

Inspection date: 2026-06-24  
Source: <https://github.com/anthropics/skills>  
Reviewed revision: `57546260929473d4e0d1c1bb75297be2fdfa1949`

Current authority note: this is a dated 2026-06-24 coverage snapshot. Its
legacy `adapt-candidate`, neutralization, adaptation, and approved-release
language is superseded by
`registry/skill-portfolio-current-authority.json`. Current review preserves
external Skill bodies exact upstream and keeps official/runtime bodies outside
this repository's release. The historical matrix remains evidence only.

Anthropic official Skills are the first recorded official external capability
baseline instance in this repository.

This is the first recorded instance of the official external capability
baseline model described in
`docs/official-external-capability-baselines.md`. It treats Anthropic official
Skills as a dated external baseline and dated external capability baseline. It
does not make those Skills part of this repository's managed inventory. In
short: this is not managed inventory, not release manifest content, and not an
execution path.

## Scope And Rules

- Do not blindly import the official repository.
- Do not claim full coverage merely because an Agent can usually complete a
  task with native reasoning.
- Distinguish functional ability from stable coverage of workflow, resources,
  scripts, trigger descriptions, and output standards.
- Use `covered` only when current native, runtime, ecosystem, or curated
  capability is materially sufficient for the relevant workflow.
- Use `reference` when the source is useful as dated baseline evidence but
  should not be copied, adapted, or executed.
- Use `adapt-candidate` when the capability is useful, not fully covered, and
  can only enter this repository after the normal intake path.
- Use `skip` when the Skill is product-specific, not portable, or not aligned
  with this repository's agent-neutral scope.

Anthropic official, runtime-owned, or first-party content remains official
external baseline evidence and dated overlap evidence. It is not vendored here
and does not enter `release-manifest.json`.

## License And Provenance Findings

The inspected repository does not provide a root `LICENSE` file. Licensing is
per Skill or described by repository documentation:

- Many example Skills include per-directory `LICENSE.txt` files using Apache
  License 2.0.
- `docx`, `pdf`, `pptx`, and `xlsx` include Anthropic source-available /
  all-rights-reserved terms. Their bodies, scripts, templates, and resources
  must be treated as reference-only unless separate permission is obtained.
- `doc-coauthoring` did not include a per-skill `LICENSE.txt` in the inspected
  revision. Treat it as reference or candidate-only until license provenance is
  clarified.
- `THIRD_PARTY_NOTICES.md` lists additional dependency notices, including
  media and document-processing dependencies. Any future adaptation must repeat
  dependency and redistribution review.

## Coverage Matrix

| Anthropic official Skill | Category | Purpose | Covered by Codex native? | Covered by Codex ecosystem? | Covered by existing curated Skills? | Gap / risk | Decision | Reason |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `algorithmic-art` | Creative coding | Generate algorithmic art with p5.js, seeded randomness, and parameter exploration. | Partial | Partial | No | p5.js-specific workflow, templates, and deterministic exploration are not governed here. | `adapt-candidate` / `reference` | Useful Apache-2.0 baseline, but should enter only through normal intake and overlap review. |
| `brand-guidelines` | Brand governance | Apply Anthropic brand colors and typography. | No | No | No | Anthropic-specific brand identity is not portable or user-neutral. | `skip` / `reference` | Keep as evidence that brand-specific Skills exist; do not import into an agent-neutral repository. |
| `canvas-design` | Static visual design | Create PNG/PDF visual art using design philosophy, fonts, and assets. | Partial | Partial | No | Asset/font footprint and output workflow need license and portability review. | `adapt-candidate` / `reference` | Creative workflow may be valuable, but resources must be reviewed before any adaptation. |
| `claude-api` | Provider API reference | Reference Anthropic Claude API, SDKs, models, streaming, tools, MCP, pricing, and migrations. | No | Partial | No | Provider-specific, time-sensitive API facts; native Codex/OpenAI docs do not cover Anthropic-specific details. | `reference` | Model-neutral repository may record it as external provider metadata, not import volatile provider docs as curated Skill content. |
| `doc-coauthoring` | Documentation workflow | Guide structured document co-authoring, context transfer, iteration, and reader verification. | Partial | Partial | Partial | License provenance unclear; existing writing/review Skills cover parts but not the full structured workflow. | `adapt-candidate` / `reference` | Candidate only after license clarification and overlap review. |
| `docx` | Document processing | Create, read, edit, comment, redline, and validate Word documents. | No | Yes | No | Unique scripts and XML workflows exist, but licensing is source-available / all-rights-reserved. | `covered` + `reference` | Current document ecosystem covers normal use; official body is reference-only and must not be copied. |
| `frontend-design` | UI design | Produce distinctive, intentional frontend design guidance. | Partial | Yes | Partial | Potential overlap with Product Design, Figma, prototype, and interface-design capabilities. | `reference` / `adapt-candidate` | Avoid duplicate design Skills unless a concrete workflow gap remains after ecosystem comparison. |
| `internal-comms` | Enterprise writing | Draft internal status reports, leadership updates, newsletters, FAQs, and incident communications. | Partial | Partial | No | Native writing can approximate, but reusable templates and examples are not governed here. | `adapt-candidate` | Likely useful Apache-2.0 candidate for business communication workflows. |
| `mcp-builder` | Developer tooling | Build high-quality MCP servers with API integration, SDK patterns, and evaluation. | Partial | Partial | No | Existing plugin/developer tooling does not fully govern MCP-specific build/evaluation workflow. | `adapt-candidate` | High-value Apache-2.0 candidate, but must be neutralized away from Claude-only assumptions. |
| `pdf` | Document processing | Read, extract, create, split, merge, watermark, OCR, and validate PDFs. | No | Yes | No | Unique helper scripts exist, but licensing is source-available / all-rights-reserved. | `covered` + `reference` | Runtime PDF ecosystem covers ordinary tasks; official scripts remain reference-only. |
| `pptx` | Presentation processing | Create, read, edit, combine, split, template, and validate slide decks. | No | Yes | No | Unique Office helper scripts exist, but licensing is source-available / all-rights-reserved. | `covered` + `reference` | Runtime presentation ecosystem covers ordinary tasks; official scripts remain reference-only. |
| `skill-creator` | Skill authoring | Create, improve, evaluate, benchmark, and package Skills. | Partial | Yes | Partial | Creation is covered; benchmarking/eval assets may not be fully covered. | `covered` / `adapt-candidate` | Use existing creator capabilities first; consider adapting evaluation patterns only after overlap review. |
| `slack-gif-creator` | Media workflow | Create Slack-optimized animated GIFs with validation constraints. | Partial | Partial | No | Slack-specific constraints and media dependency notices require review. | `adapt-candidate` / `reference` | Useful niche workflow, but lower priority and dependency-heavy. |
| `theme-factory` | Theme system | Apply reusable visual themes across slides, docs, reports, and HTML artifacts. | Partial | Partial | No | Theme packs and cross-artifact style rules are not governed here. | `adapt-candidate` | Potentially useful if neutralized into portable theme guidance. |
| `web-artifacts-builder` | Web artifacts | Build complex multi-component Claude.ai HTML artifacts with React/Tailwind/shadcn patterns. | Partial | Partial | Partial | Claude.ai artifact assumptions are not portable; web prototype overlap exists. | `reference` / `adapt-candidate` | Do not import directly; possible future generic web-prototype adapter. |
| `webapp-testing` | Frontend testing | Test local web apps with Playwright, screenshots, browser logs, and server helpers. | Partial | Yes | Partial | Existing Playwright/browser ecosystem covers the core; examples may be useful evidence. | `covered` + `reference` | No import needed unless a concrete testing workflow gap is proven. |
| `xlsx` | Spreadsheet processing | Read, edit, repair, convert, format, calculate, and validate spreadsheets. | No | Yes | No | Unique spreadsheet helper scripts exist, but licensing is source-available / all-rights-reserved. | `covered` + `reference` | Runtime spreadsheet ecosystem covers ordinary tasks; official body is reference-only. |

## Incremental Priority

1. Reference-only baselines: `docx`, `pdf`, `pptx`, `xlsx`, `claude-api`.
2. Strong adaptation candidates after normal intake: `mcp-builder`,
   `internal-comms`, `doc-coauthoring`, and `skill-creator` evaluation
   patterns.
3. Creative/design candidates after overlap and resource review:
   `algorithmic-art`, `canvas-design`, `frontend-design`,
   `slack-gif-creator`, `theme-factory`, and `web-artifacts-builder`.
4. Skip except as dated evidence: `brand-guidelines`.

## Required Future Intake Path

Any future work item that evaluates this baseline follows the current
source-preserving gate:

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

Until that path completes, the official Anthropic Skills remain dated external
baseline evidence only.
