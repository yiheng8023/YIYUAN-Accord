# Starred Capability Source Discovery

Inspection date: 2026-06-24  
Discovery surface: <https://github.com/yiheng8023?tab=stars>

Current authority note: this dated discovery record does not authorize
neutralization or adaptation. Third-party Skill bodies remain exact upstream;
the inherited adapted 19-Skill release is deprecated transition evidence under
`registry/skill-portfolio-current-authority.json`.

This document records a user-curated discovery surface for future Skill and
capability-source intake. It is not approval, not installation, not managed
inventory, and not an execution path.

Machine-readable candidate-source snapshots live in
`registry/starred-skill-sources.json`. That registry is a candidate-discovery input and
non-approval surface only; it does not promote sources into `skills/`, release
manifests, or runtime installation.

A newer scoped public list was explicitly supplied on 2026-07-18:
<https://github.com/stars/yiheng8023/lists/skills>. Its 13 visible repositories,
eight-source overlap with the broad public discovery, and five newly observed
sources are recorded separately in
`registry/user-starred-skill-source-list-intake-2026-07-18.json`. This scoped
list raises review priority but is not a whitelist and does not limit discovery.
The older table below remains dated historical triage and must not be read as
current list membership.

The pinned `helloianneo/awesome-claude-code-skills` index was then parsed as a
source artifact rather than trusted as an executable catalog. It contains 20
direct `npx skills add` source coordinates; four overlap the broad public
capture and 16 are new. Read-only tree preflight currently resolves 14 of those
16. Two coordinates return 404 and are preserved as stale evidence. A possible
successor is never substituted automatically: it must re-enter with its own
pin, license, provenance, demand, and review. See
`registry/user-starred-index-child-source-extraction-2026-07-18.json`,
`registry/user-starred-index-child-source-preflight-2026-07-18.json`, and
`registry/user-starred-index-stale-source-resolution-2026-07-18.json`.

GitHub-wide candidate discovery is governed by
`registry/github-skill-discovery-profile.json` and the scheduled
`discover-candidate-sources` workflow. That workflow performs read-only search
and writes a run summary only; it does not star repositories, modify this
repository, approve candidates, or install runtime Skills.

Broad coverage planning is governed by
`registry/collaboration-domain-coverage.json` and
`registry/curation-expansion-rounds.json`. Local runtime alignment is deferred
until enough curated coverage has been admitted and release validation is stable.

This is not managed inventory.

The goal is cross-agent capability sharing:

- discover high-quality third-party Skills or adjacent capability packages;
- classify official/runtime baselines separately from third-party candidates;
- avoid collecting for size alone;
- preserve source and restore traceability;
- let routing choose the best available capability even when overlap exists.

## Discovery Classes

| Class | Meaning | Default disposition |
| --- | --- | --- |
| official external baseline | Official Skills or capability packages owned by an Agent, runtime, platform, or tool ecosystem | baseline matrix / reference; no vendoring |
| third-party skill source | Repository appears to contain reusable Skills, agents, commands, prompts, or workflows | candidate; must pass intake |
| index / awesome list | Curated list of other projects | discovery index only |
| agent runtime / harness | Tooling that may expose capabilities but is not directly a Skill source | capability baseline or adapter research |
| methodology / standards | Behavioral or workflow guidance | reference or exact-source review candidate |
| risk / exclusion | Source may raise license, ToS, leaked-prompt, proxy, credential, or maintenance concerns | reject or reference-only until reviewed |

## Initial Starred Source Triage

The following rows are initial triage only. They are intentionally conservative.

| Source | Class | Initial disposition | Reason |
| --- | --- | --- | --- |
| `openai/skills` | official external baseline | baseline / reference | Official source for Codex capability comparison; do not vendor by default. |
| `anthropics/skills` | official external baseline | baseline / reference | Already recorded as first official baseline instance. |
| `addyosmani/agent-skills` | third-party skill source | historical adapted subset deprecated / fresh candidate review | The old adapted subset is transition evidence only; any current candidate starts from an exact upstream revision. |
| `mattpocock/skills` | third-party skill source | historical adapted subset deprecated / fresh candidate review | The old adapted subset is transition evidence only; any current candidate starts from an exact upstream revision. |
| `kepano/obsidian-skills` | third-party skill source | candidate | Potential Obsidian workflow coverage; requires license, tool dependency, and portability review. |
| `obra/superpowers` | methodology / skill framework | reference / candidate | Installed ecosystem already exposes Superpowers; future curated use must avoid duplicating runtime-owned capability. |
| `alchaincyf/huashu-design` | third-party skill source | candidate | Design workflow candidate; requires license, asset, export, and agent-neutrality review. |
| `multica-ai/andrej-karpathy-skills` | methodology / guidance | reference / candidate | Potential behavioral guidance; likely better as reference unless a concrete portable Skill gap is proven. |
| `github/awesome-copilot` | index / awesome list | discovery index | Useful for finding Copilot-style agents/instructions, not direct import. |
| `LangGPT/awesome-claude-code` | index / awesome list | discovery index | Useful Claude ecosystem map; not direct import. |
| `helloianneo/awesome-claude-code-skills` | index / awesome list | discovery index | Useful skill list; every child source requires independent review. |
| `hesreallyhim/awesome-claude-code` | index / awesome list | discovery index | Useful ecosystem map; not direct import. |
| `ComposioHQ/awesome-claude-skills` | index / awesome list | discovery index | Useful ecosystem map; not direct import. |
| `sickn33/antigravity-awesome-skills` | index / large skill library | discovery index / high-risk candidate | Large library needs sampling, license normalization, duplicate control, and quality gates before any intake. |
| `VoltAgent/awesome-claude-code-subagents` | index / subagent collection | discovery index | May inform cross-agent role topology; not direct Skill import. |
| `colbymchenry/codegraph` | agent tooling | external capability baseline | Runtime/tool capability; restore through tool installation, not Skill vendoring. |
| `anthropics/claude-code` | agent runtime / harness | official external baseline | Runtime capability source; not a curated Skill source. |
| `openai/codex` | agent runtime / harness | official external baseline | Runtime capability source; not a curated Skill source. |
| `anomalyco/opencode` | agent runtime / harness | external baseline | May inform cross-agent capability mapping; not direct Skill import. |
| `NousResearch/hermes-agent` | agent runtime / harness | external baseline | May inform cross-agent capability mapping; not direct Skill import. |
| `farion1231/cc-switch` | agent runtime / local skill manager | external baseline / restore source | Explains local external Skill roots; not automatically curated content. |
| `code-yeongyu/oh-my-openagent` | agent harness / workflow tooling | external baseline / candidate research | Review as ecosystem tooling, not direct Skill intake. |
| `Yeachan-Heo/oh-my-codex` | Codex ecosystem tooling | external baseline / candidate research | Potential hooks/agent-team tooling; requires strict side-effect review. |
| `github/spec-kit` | methodology / tooling | reference / candidate | Spec-driven workflow may map to lifecycle Recipes; not direct Skill import without review. |
| `itcoffee66/githubweekly` | discovery feed | skip / reference | General project discovery, not a Skill source. |
| `router-for-me/CLIProxyAPI` | proxy / external service bridge | risk / exclusion | Possible account, ToS, credential, and routing-risk surface; do not ingest without explicit review. |
| `asgeirtj/system_prompts_leaks` | leaked prompt archive | risk / exclusion | Do not ingest as Skill source; may carry provenance, safety, and policy risk. |

## Intake Rule

Stars are only discovery hints. A starred repository may become:

- an official external baseline;
- a third-party candidate;
- an index for discovering child sources;
- external capability metadata;
- reference-only evidence;
- rejected.

No starred third-party body enters `skills/` or `release-manifest.json` under
the current policy. Exact-upstream candidates may enter governed metadata and,
only after review plus separate authority, a manager transaction. Discovery or
review alone never enters a live execution path.

## Discovery Disposition Feedback

When a discovered source is explicitly rejected, marked reference-only, or
otherwise already handled by this curated repository, record the machine-readable
feedback in `registry/radar-feedback.json`.

This file is a read-only suppression surface for discovery processes. It lets a
consumer avoid re-recommending already-decided or unsuitable Skill candidates
without writing back to this repository and without parsing prose. It is not an
approval surface, not a release manifest, and not runtime inventory.

## Next Review Slices

1. Separate direct Skill sources from indexes and agent runtimes.
2. For each direct Skill source, pin a revision and record license posture.
3. Sample representative Skills for overlap, quality, security, portability,
   source fidelity, and host compatibility without rewriting the payload.
4. Prefer `covered` or `reference` when Codex native/runtime/plugin capability
   is already materially sufficient.
5. Admit only reviewed exact-upstream candidates; prove a residual gap before
   authoring any repository-owned replacement or wrapper.
