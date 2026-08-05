# Matt Pocock Skills upstream drift — 2026-08-06

Status: `research-only-source-drift-detected-no-lifecycle-mutation`

This report records a bounded, read-only comparison of the official
`mattpocock/skills` repository. It does not install, enable, project, invoke,
execute, or promote any Skill, and it does not update CC Switch or candidate
state.

## Decision summary

- Official `main` is now
  [`07999e06b58541362f2f3d6de9e2b108ac28dc52`](https://github.com/mattpocock/skills/commit/07999e06b58541362f2f3d6de9e2b108ac28dc52).
- The SEM-03 eight-file package remains an eight-file path closure, but two
  `grilling` files have different bytes. The interaction protocol changed from
  one-question-at-a-time to design-tree frontier rounds and now explicitly
  calls for sub-agent fact finding. The old source-pinned admission remains
  valid historical evidence for `ed37663...`; it is not current-upstream
  admission evidence.
- The author's promoted manifest changed from 22 to 25 Skills. The repository
  contains 35 `skills/**/SKILL.md` files in total, down from 41; total-tree
  count and promoted-manifest count remain different concepts.
- A live read-only CC Switch database check still finds the old 22 source rows
  enabled for both Claude and Codex. The central trees are already a mixed
  revision state: 14 match the old pin, 6 match current `main`, and 2 match
  neither endpoint. Refreshing that source without a preview risks replacing
  this 22-row hybrid with whole-tree discovery of up to 35 current `SKILL.md`
  paths.
- This drift justifies a new static review gate if the current revision is to
  become a candidate. It does not justify an automatic update, activation, or
  replacement.

## Authority reconciliation

The repository currently carries three distinct authorities that must not be
collapsed:

1. `registry/human-ai-collaboration-semantic-authority-current-matt-static-admission-2026-07-28.json`
   locks the SEM-03 package to `ed37663cc5fbef691ddfecd080dff42f7e7e350d`,
   three Skills, eight files, and the MIT license blob.
2. `registry/skill-portfolio-current-55-subtractive-triage-2026-07-30.json`
   is a dated manager snapshot. It locks the then-promoted 22-item suite to
   `2ab958093e83e0ec752e6c1c5932da465bf23e0c` and names
   `.claude-plugin/plugin.json` as release authority.
3. `registry/skill-portfolio-current-authority.json` is the newer policy
   authority. It has no active adapted release and records a separate 17-item
   reviewed cohort (16 dependency-complete manager-installed, one review-only)
   as inactive. That current cohort does not source its 16 installed candidates
   from `mattpocock/skills`.

Therefore, “Matt updated” is a source-drift event across the first two dated
objects; it is not a lifecycle transition for the current 16-item candidate
cohort.

## Official source snapshot

Observed at `2026-08-06T02:13:14+08:00` using the official Git remote, Git
objects, raw files, and GitHub REST API only.

| Field | Observation |
|---|---|
| Repository | [`mattpocock/skills`](https://github.com/mattpocock/skills) |
| Default branch | `main` |
| Current HEAD | `07999e06b58541362f2f3d6de9e2b108ac28dc52` |
| HEAD commit time | `2026-08-05T18:51:28+01:00` |
| License blob | `f1dd2c09108dde1a5f56097cee8461b3ea834499`, 1,068 bytes, unchanged |
| Plugin manifest version | `1.2.0` at `2ab958...` → `1.2.1` at current HEAD |
| Package version | `1.1.0` at `2ab958...` → `1.2.0` at current HEAD |

Primary sources: [repository API](https://api.github.com/repos/mattpocock/skills),
[current recursive tree](https://api.github.com/repos/mattpocock/skills/git/trees/07999e06b58541362f2f3d6de9e2b108ac28dc52?recursive=1),
and [current promoted manifest](https://github.com/mattpocock/skills/blob/07999e06b58541362f2f3d6de9e2b108ac28dc52/.claude-plugin/plugin.json).

### Author announcement

Matt Pocock's [2026-08-05 X announcement](https://x.com/i/status/2084985277102031137)
identifies the public event as `mattpocock/skills v1.2`. It announces the new
documentation, Claude's official Plugin marketplace route, Codex metadata in
`agents/openai.yaml`, the redesigned `grilling` and `prototype` flows, the
`writing-for-agents` rename, and the new `wizard`, `to-questionnaire`, and
`wait-what` Skills. The thread links the repository's `v1.2.0` release and
instructs users to update through `npx skills update` or the Claude Plugin.
Those feature claims agree with the exact tagged source and changelog.

The same post reports repository rank and `skills.sh` download totals. Those
are author-reported, time-varying popularity claims and were not independently
used as version, admission, behavior, or value evidence. The announcement is
evidence for the tagged `v1.2.0` release event; it is not evidence that the
five later `main` commits, plugin version `1.2.1`, or any CC Switch payload are
part of one exact release.

### Three source states

| State | Exact identity | Promoted manifest | Meaning |
|---|---|---:|---|
| Current CC installation state | Mixed; no single revision explains all 22 central trees | 22 rows | 14 old-pin matches, 6 current-main matches, 2 intermediate trees; not an exact release |
| Stable upstream release | [`v1.2.0`](https://github.com/mattpocock/skills/tree/v1.2.0), annotated tag `e903586...`, peeled commit `2ffb184ffbb752faa664c0b204f3c9241b1428e9` | 25 | Stable tagged release; already contains the new `grilling` protocol |
| Current upstream `main` | `07999e06b58541362f2f3d6de9e2b108ac28dc52`, plugin version `1.2.1` | 25 | Five commits beyond `v1.2.0`; no `v1.2.1` tag was observed |

The five post-tag commits bump the plugin version, make
`writing-for-agents` model-invokable in Codex, and revise documentation. The
SEM-03 eight files are byte-identical between tagged `v1.2.0` and current
`main`; their material drift happened before the stable tag.

## Commit and tree delta

Official compare evidence shows:

| Baseline | Ahead | Behind | Changed paths |
|---|---:|---:|---:|
| `ed37663...` (SEM-03) | 89 commits | 0 | 94 |
| `2ab958...` (22-item suite) | 87 commits | 0 | 94 |
| `2ffb184...` (`v1.2.0`) | 5 commits | 0 | 23 |

The full commit sequences remain available through the official
[SEM-03 comparison](https://github.com/mattpocock/skills/compare/ed37663cc5fbef691ddfecd080dff42f7e7e350d...07999e06b58541362f2f3d6de9e2b108ac28dc52)
and [22-item-suite comparison](https://github.com/mattpocock/skills/compare/2ab958093e83e0ec752e6c1c5932da465bf23e0c...07999e06b58541362f2f3d6de9e2b108ac28dc52).
The commit count includes merges and replayed branch history; it is not a count
of independent capability changes.

Material source events include the `grilling` frontier-round redesign, the
`writing-great-skills` to `writing-for-agents` restructuring, promotion of
`wizard` and `to-questionnaire`, addition of `wait-what`, removal of unused
non-promoted Skills, and the current Codex metadata fix. These are observable
source events, not behavioral-value findings.

## Promoted suite delta

The official `.claude-plugin/plugin.json` manifest changed from 22 to 25
entries:

- removed: `writing-great-skills`;
- added: `wizard`, `to-questionnaire`, `wait-what`, `writing-for-agents`;
- retained: the other 21 prior promoted paths.

Current promoted names are:

- engineering (18): `ask-matt`, `code-review`, `codebase-design`,
  `diagnosing-bugs`, `domain-modeling`, `grill-with-docs`, `implement`,
  `improve-codebase-architecture`, `prototype`, `research`,
  `resolving-merge-conflicts`, `setup-matt-pocock-skills`, `tdd`, `to-spec`,
  `to-tickets`, `triage`, `wayfinder`, `wizard`;
- productivity (7): `grill-me`, `grilling`, `handoff`, `teach`,
  `to-questionnaire`, `wait-what`, `writing-for-agents`.

Across the prior 22 exact Skill directory trees, 12 remain byte-identical, 9
changed, and `writing-great-skills` was removed. The changed retained trees are
`ask-matt`, `triage`, `setup-matt-pocock-skills`, `tdd`, `to-spec`,
`wayfinder`, `prototype`, `code-review`, and `grilling`.

The recursive tree contains 35 total `SKILL.md` files at current HEAD versus
41 at both repository baselines. Current buckets are 18 engineering, 7
productivity, 6 in-progress, and 4 misc. A crawler that counts every Skill
directory is therefore not reporting the same object as the promoted manifest.

## Live manager observation

A read-only query of `~/.cc-switch/cc-switch.db` at the report observation time
found 22 rows attributed to `mattpocock/skills@main`. All 22 manager flags were
on for Claude and Codex; Gemini, OpenCode, Hermes, and Grok flags were off. The
22 names match the old promoted suite, including `writing-great-skills`, and do
not include `wizard`, `to-questionnaire`, `wait-what`, or
`writing-for-agents`.

This proves current database flags and source-row identity only. It does not
prove consumer exposure, loader behavior, invocation, or value. Because the
official tree now exposes 35 `SKILL.md` paths while the promoted manifest lists
25, a direct CC source refresh could discover a different set from either the
installed 22 or the promoted 25. A dry, source-pinned preview is required
before any manager write.

An exact, newline-normalized file-set comparison against the old and current
Git trees also proves that the live central payload is mixed:

- 14 trees match `2ab958...`: `codebase-design`, `diagnosing-bugs`,
  `domain-modeling`, `grill-me`, `grill-with-docs`, `handoff`, `implement`,
  `improve-codebase-architecture`, `research`, `resolving-merge-conflicts`,
  `tdd`, `teach`, `to-tickets`, and retained `writing-great-skills`;
- 6 trees match `07999e...`: `code-review`, `grilling`, `prototype`,
  `to-spec`, `triage`, and `wayfinder`;
- `ask-matt` and `setup-matt-pocock-skills` match neither endpoint and retain
  intermediate upstream bytes.

This is payload-cohort inconsistency, not proof that those files were modified
locally. It shows why update must be an atomic exact-revision cohort
transaction rather than independent best-effort item refreshes.

## SEM-03 eight-file delta

The three governed directories still contain the same eight paths, and
`grill-with-docs` still names `grilling` and `domain-modeling`; `domain-modeling`
still references `CONTEXT-FORMAT.md` and `ADR-FORMAT.md`. No static dependency
file was added or removed.

| File | `ed37663...` raw Git blob / bytes | Current raw Git blob / bytes | State |
|---|---|---|---|
| `grill-with-docs/SKILL.md` | `bed05d2...` / 245 | `bed05d2...` / 245 | identical |
| `grill-with-docs/agents/openai.yaml` | `5dbe278...` / 145 | `5dbe278...` / 145 | identical |
| `domain-modeling/SKILL.md` | `d0f7e1a...` / 3,427 | `d0f7e1a...` / 3,427 | identical |
| `domain-modeling/CONTEXT-FORMAT.md` | `eaf2a18...` / 2,299 | `eaf2a18...` / 2,299 | identical |
| `domain-modeling/ADR-FORMAT.md` | `da7e78e...` / 2,766 | `da7e78e...` / 2,766 | identical |
| `domain-modeling/agents/openai.yaml` | `7f1522d...` / 101 | `7f1522d...` / 101 | identical |
| `grilling/SKILL.md` | `52d8eb3...` / 843 | `95bd01e...` / 1,872 | changed |
| `grilling/agents/openai.yaml` | `85b1260...` / 105 | `ddbdb96...` / 113 | changed |

Exact current changed-file identities:

- [`grilling/SKILL.md`](https://github.com/mattpocock/skills/blob/07999e06b58541362f2f3d6de9e2b108ac28dc52/skills/productivity/grilling/SKILL.md):
  Git blob `95bd01ee9049a7e08120d54af9cd6ceeef282335`, SHA-256
  `fa5c1e5ee76b1c8f1ae56101f52c9e239de75d5c578adc61227b92d10b7e52ef`.
- [`grilling/agents/openai.yaml`](https://github.com/mattpocock/skills/blob/07999e06b58541362f2f3d6de9e2b108ac28dc52/skills/productivity/grilling/agents/openai.yaml):
  Git blob `ddbdb96139c0c1dfe6bca698f39d0465674b8a39`, SHA-256
  `1411d7df7d99b7e621a1ff8283c8133cc2464be63d064e52d8ce169c6800ee9b`.

The current `grilling` contract replaces one-at-a-time questioning with
frontier rounds over a design tree and explicitly asks the Agent to delegate
environmental fact finding to sub-agents without blocking unrelated frontier
questions. Its OpenAI short description changes accordingly. This is a
material interaction and host-capability dependency change even though the
static eight-file closure is unchanged.

## Claim and authority boundary

Proved here:

- official upstream identity, ancestry, commit/path delta, current promoted
  manifest, total Skill-tree count, and exact eight-file byte delta;
- old source-pinned evidence does not represent current upstream bytes.
- the live 22-row manager state is enabled on Claude and Codex and its central
  payload cannot be attributed to one exact revision.

Not proved here:

- whether a CC source refresh would follow the 25-item promoted manifest or
  discover all 35 current Skill paths, and consumer projection state beyond
  the separately observed 22 source rows and their manager enable flags;
- loader exposure, instruction delivery, invocation, sub-agent dispatch,
  behavior, value, task fit, or cross-host portability;
- security, dependency, overlap, or maintenance admission for the four newly
  promoted/restructured entries;
- that any current real task has a residual gap addressed by this update.

No manager, consumer, account, model, Hook, MCP, Plugin, App, candidate, or
repository policy state was changed.

## Next gate

If current Matt is to remain a reviewed candidate source, first choose and
record whether the comparison target is stable `v1.2.0` (`2ffb184...`) or
unreleased current `main` (`07999e...`). Then perform a new exact-revision
static admission that:

1. rechecks license, provenance, security, dependencies, overlap, and exact
   raw Git identities for the affected 25-item manifest;
2. treats the new sub-agent/parallel fact-finding requirement as a host-adapter
   question rather than assuming portability;
3. previews manifest-aware 25-item discovery against CC's possible 35-path
   whole-tree discovery and the currently enabled 22 rows, without writing;
4. requires separate authority to disable, update, add, remove, or re-enable
   any manager row; and
5. requires a separately bound real task and residual gap before any one-host,
   one-candidate behavioral comparison or update transaction.

Absent that gate, retain the existing pins as historical evidence and make no
runtime change.
