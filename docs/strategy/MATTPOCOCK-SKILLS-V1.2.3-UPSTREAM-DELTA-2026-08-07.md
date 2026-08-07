# Matt Pocock Skills v1.2.3 upstream delta

Date: 2026-08-07

Status: first-party upstream review plus separately generated exact-release and
read-only live-manager preview; no installation, execution, projection,
configuration change, or manager mutation

Repository: [`mattpocock/skills`](https://github.com/mattpocock/skills)

## Question and authority boundary

This note checks whether Matt Pocock's Skills repository advanced beyond the
Harness-governed `v1.2.2` cohort and whether the delta changes the current
portfolio decision. The review uses only the repository's own Git refs,
release, compare view, committed files, and the Harness's current authority
record.

It does not authorize or perform a CC Switch refresh, installation, enablement,
consumer projection, direct installer invocation, third-party script
execution, model dispatch, account access, or configuration change. Source
structure and release publication are not loader, instruction-delivery,
behavior, value, portability, or production evidence.

## Executive judgment

Matt's repository has materially advanced. The prior Harness-governed cohort
was the annotated `v1.2.2` release peeled to
`8b36d4fb2635b3c21998dcd8144439c9e5ba7302`, while the latest formal upstream
release is `v1.2.3`, peeled to
`6acc160e4e0cd062dbbbd7a1b26ae92855edf07e`. The default branch has advanced
two additional commits to `84fdeffd12f2ee307994d1eb6feb48173b6e0502`, but
that post-release delta changes only one documentation sentence and no Skill
payload.

`v1.2.3` warranted a separately governed exact-release update preview. Its most
important change is explicit secret redaction in `diagnosing-bugs`; it also
removes Claude-specific subagent tool names from three engineering flows and
removes false-precision time estimates from `wizard`. These are security,
portability, and truthfulness improvements, not proof of runtime behavior.

The subsequent read-only preview found that all 25 live managed payloads already
match `v1.2.3`, while their database source rows now name mutable `main`. The
refresh occurred before this review and its actor or trigger is unattributed.
Do not blindly update from `main` or rewrite the five changed directories. A
later transaction, if separately authorized, should reconcile source metadata
to the exact `v1.2.3` release only after rechecking the current payloads. Keep
`wizard` disabled because its credential and external-write surfaces remain.

## Frozen source comparison

| Field | Observed value | Primary evidence |
| --- | --- | --- |
| Harness authority | `v1.2.2`; annotated tag object `8651af486bb7c9e695ab1c6f44bd9a79fabb9999`; peeled commit `8b36d4fb2635b3c21998dcd8144439c9e5ba7302`; 25 promoted and 35 recursive Skills | [current portfolio authority](../../registry/skill-portfolio-current-authority.json), [v1.2.2 update event](../../registry/mattpocock-skills-v1.2.2-cc-manager-cohort-update-event-2026-08-06.json), [upstream tag object](https://api.github.com/repos/mattpocock/skills/git/tags/8651af486bb7c9e695ab1c6f44bd9a79fabb9999) |
| Latest formal release | `v1.2.3`; annotated tag object `835450ef244ab7335f75d95b83e7d979eae22a6d`; peeled commit `6acc160e4e0cd062dbbbd7a1b26ae92855edf07e`; published 2026-08-06 14:05:28 UTC | [release](https://github.com/mattpocock/skills/releases/tag/v1.2.3), [tag object](https://api.github.com/repos/mattpocock/skills/git/tags/835450ef244ab7335f75d95b83e7d979eae22a6d), [release commit](https://github.com/mattpocock/skills/commit/6acc160e4e0cd062dbbbd7a1b26ae92855edf07e) |
| Current default branch | `main` at `84fdeffd12f2ee307994d1eb6feb48173b6e0502` | [repository metadata](https://api.github.com/repos/mattpocock/skills), [HEAD commit](https://github.com/mattpocock/skills/commit/84fdeffd12f2ee307994d1eb6feb48173b6e0502) |
| Governed pin to release | 11 commits; 11 modified files; no added, removed, or renamed files | [`v1.2.2` to `v1.2.3` compare](https://github.com/mattpocock/skills/compare/8b36d4fb2635b3c21998dcd8144439c9e5ba7302...6acc160e4e0cd062dbbbd7a1b26ae92855edf07e) |
| Release to current `main` | 2 commits; only `docs/productivity/grill-me.md` changes by one line | [`v1.2.3` to `main` compare](https://github.com/mattpocock/skills/compare/6acc160e4e0cd062dbbbd7a1b26ae92855edf07e...84fdeffd12f2ee307994d1eb6feb48173b6e0502) |

The upstream release manifest remains 25 promoted Skills and changes only its
version to `1.2.3`; no Skill locator was added, removed, or renamed. Because
the release comparison contains no added or removed files, the governed 35
recursive `SKILL.md` paths and ten non-promoted paths also remain structurally
unchanged. See the exact [release plugin
manifest](https://github.com/mattpocock/skills/blob/6acc160e4e0cd062dbbbd7a1b26ae92855edf07e/.claude-plugin/plugin.json#L1-L48)
and the complete [release compare](https://github.com/mattpocock/skills/compare/8b36d4fb2635b3c21998dcd8144439c9e5ba7302...6acc160e4e0cd062dbbbd7a1b26ae92855edf07e).

## Payload changes

### 1. `diagnosing-bugs`: material security improvement

Facts:

- The Skill now requires commands, outputs, and captured artifacts to have every
  secret replaced with `<REDACTED>`, keeps credentials in environment variables,
  and limits quoted artifacts to signal-bearing lines. It tells the agent to ask
  the user when redacted evidence is insufficient. See
  [`diagnosing-bugs/SKILL.md`](https://github.com/mattpocock/skills/blob/6acc160e4e0cd062dbbbd7a1b26ae92855edf07e/skills/engineering/diagnosing-bugs/SKILL.md#L12-L16).
- The reproduction fallback now requests a redacted captured artifact and the
  completion criterion requires redacted command output. See
  [`diagnosing-bugs/SKILL.md`](https://github.com/mattpocock/skills/blob/6acc160e4e0cd062dbbbd7a1b26ae92855edf07e/skills/engineering/diagnosing-bugs/SKILL.md#L53-L62).
- The HITL template warns that `capture` prints its value to the terminal and
  directs sign-in to remain a human `step`. See
  [`hitl-loop.template.sh`](https://github.com/mattpocock/skills/blob/6acc160e4e0cd062dbbbd7a1b26ae92855edf07e/skills/engineering/diagnosing-bugs/scripts/hitl-loop.template.sh#L11-L18).
- The upstream release attributes the patch to a Snyk `W007` HIGH finding about
  insecure credential handling. See [release notes](https://github.com/mattpocock/skills/releases/tag/v1.2.3)
  and [PR #779](https://github.com/mattpocock/skills/pull/779).

Inference:

This is a concrete reason to review `v1.2.3`; it is not merely version chasing.
It reduces instruction-level credential exposure risk. It does not enforce
redaction at the host, terminal, transport, log, or model boundary, so it is not
proof that secrets cannot escape.

### 2. Three engineering flows: more host-neutral subagent language

Facts:

- `code-review` no longer says to call Claude Code's `Agent` tool with the
  `general-purpose` type; it keeps the requirement to run two review subagents
  in parallel. See
  [`code-review/SKILL.md`](https://github.com/mattpocock/skills/blob/6acc160e4e0cd062dbbbd7a1b26ae92855edf07e/skills/engineering/code-review/SKILL.md#L58-L67).
- `codebase-design` now says to spawn three or more subagents without naming an
  `Agent` tool. See
  [`DESIGN-IT-TWICE.md`](https://github.com/mattpocock/skills/blob/6acc160e4e0cd062dbbbd7a1b26ae92855edf07e/skills/engineering/codebase-design/DESIGN-IT-TWICE.md#L19-L28).
- `improve-codebase-architecture` now requests a subagent without the
  Claude-specific `subagent_type=Explore`. See
  [`improve-codebase-architecture/SKILL.md`](https://github.com/mattpocock/skills/blob/6acc160e4e0cd062dbbbd7a1b26ae92855edf07e/skills/engineering/improve-codebase-architecture/SKILL.md#L24-L31).
- The intended change is explicitly described as making the instructions
  followable on Codex and other harnesses. See [PR #781](https://github.com/mattpocock/skills/pull/781).

Inference:

The instructions are structurally more portable, and the change is relevant to
the Harness's agent-neutral goal. They still assume that the active host can
create suitable subagents and preserve delegation boundaries. Static wording
does not prove availability, invocation, instruction delivery, receipts,
behavior, or cross-host equivalence.

### 3. `wizard`: less false precision, unchanged consequential surfaces

Facts:

- The Skill and template remove `TOTAL_MINUTES`, per-stage minute parameters,
  and the remaining-time display; progress is now reported only by stage count.
  See [`wizard/SKILL.md`](https://github.com/mattpocock/skills/blob/6acc160e4e0cd062dbbbd7a1b26ae92855edf07e/skills/engineering/wizard/SKILL.md#L33-L37),
  [`wizard/template.sh`](https://github.com/mattpocock/skills/blob/6acc160e4e0cd062dbbbd7a1b26ae92855edf07e/skills/engineering/wizard/template.sh#L21-L55),
  and [PR #783](https://github.com/mattpocock/skills/pull/783).
- The Skill still describes `.env`, GitHub secret, and GitHub variable writes,
  browser navigation, credentials, and third-party configuration. See
  [`wizard/SKILL.md`](https://github.com/mattpocock/skills/blob/6acc160e4e0cd062dbbbd7a1b26ae92855edf07e/skills/engineering/wizard/SKILL.md#L6-L12).
- The template still calls `gh secret set` when `gh` is available and
  authenticated. See
  [`wizard/template.sh`](https://github.com/mattpocock/skills/blob/6acc160e4e0cd062dbbbd7a1b26ae92855edf07e/skills/engineering/wizard/template.sh#L141-L153).

Inference:

Removing invented time estimates improves truthfulness and avoids one source of
user expectation loss. It does not reduce the Skill's trust, credential,
account, or external-write boundary. The existing default-disabled disposition
therefore remains appropriate.

### 4. Post-release `grill-me` change is documentation-only

After `v1.2.3`, `main` changes the public description from interviewing until
an idea “has real decisions in it” to interviewing until the user “can commit
to it.” The only changed path is
[`docs/productivity/grill-me.md`](https://github.com/mattpocock/skills/blob/84fdeffd12f2ee307994d1eb6feb48173b6e0502/docs/productivity/grill-me.md#L1-L6);
the corresponding Skill payload did not change. This wording may better express
decision commitment, but it is not a reason to pin mutable `main`.

## README, installer, dependency, and license review

Facts:

- `README.md` did not change between the governed commit, `v1.2.3`, and current
  `main`. It still offers a Claude plugin route and
  `npx skills@latest add mattpocock/skills`, warns that using both creates
  duplicates, and says the `skills.sh` route copies editable files that update
  only when the user requests an update. See [README installation
  section](https://github.com/mattpocock/skills/blob/84fdeffd12f2ee307994d1eb6feb48173b6e0502/README.md#L25-L70)
  and the [full governed-to-main compare](https://github.com/mattpocock/skills/compare/8b36d4fb2635b3c21998dcd8144439c9e5ba7302...84fdeffd12f2ee307994d1eb6feb48173b6e0502).
- No installer implementation or `setup-matt-pocock-skills` file changed. A
  direct installer still bypasses the Harness's CC Switch transaction and
  projection authority unless separately governed.
- `package.json` changes only `version` from `1.2.2` to `1.2.3`; package scripts,
  two development dependencies, `npm@10.9.4`, private-package status, and MIT
  metadata are unchanged. See
  [`package.json`](https://github.com/mattpocock/skills/blob/6acc160e4e0cd062dbbbd7a1b26ae92855edf07e/package.json#L1-L21)
  and the [exact compare](https://github.com/mattpocock/skills/compare/8b36d4fb2635b3c21998dcd8144439c9e5ba7302...6acc160e4e0cd062dbbbd7a1b26ae92855edf07e).
- No dependency manifest other than the two version fields changed; no runtime
  dependency or installer code was added.
- `LICENSE` is unchanged and remains MIT. See the exact
  [LICENSE](https://github.com/mattpocock/skills/blob/84fdeffd12f2ee307994d1eb6feb48173b6e0502/LICENSE)
  and [repository license metadata](https://api.github.com/repos/mattpocock/skills).
- The release has no binary assets. Its authoritative payload is the Git tag and
  repository tree, not a new installer bundle. See [release API](https://api.github.com/repos/mattpocock/skills/releases/tags/v1.2.3).

## Governance effect

### Supported facts

1. The dated live CC Switch payload cohort is now explained by exact `v1.2.3`
   bytes, but its 25 database source rows name mutable `main`; provenance and
   payload identity therefore need separate treatment.
2. `v1.2.3` changes five promoted Skill directories but does not change the
   promoted or recursive inventory.
3. The `diagnosing-bugs` security correction is a substantive candidate-update
   benefit.
4. The three subagent wording changes reduce Claude-specific coupling.
5. `wizard` retains consequential local and GitHub write surfaces.

### Bounded recommendation

- Keep exact formal release `v1.2.3@6acc160e4e0cd062dbbbd7a1b26ae92855edf07e`
  as the governed source identity. Do not select current `main`.
- Compare all 25 promoted directories and preserve the single-revision closure,
  even though only five Skill directories changed.
- Keep `wizard` disabled and preserve task, account/data, credential, external
  write, cleanup, and rollback gates.
- Treat the redaction patch as static policy improvement until a separately
  authorized test verifies sensitive-data handling. Treat host-neutral wording
  as portability intent until exact-host behavior is verified.
- Do not use this finding to blindly install, refresh, enable, project, or
  execute the release. Current payload bytes need no rewrite while their exact
  identity holds. Any metadata reconciliation remains a separate, previewable,
  recoverable authorization boundary.

## Dated live-manager observation

At `2026-08-07T17:18:41+08:00`, the existing read-only previewer compared the
exact `v1.2.3` Git objects with CC Switch and the three consumer roots. It found
25 manager rows, 24 enabled for both Claude and Codex, and `wizard` disabled.
Twenty payloads were unchanged across `v1.2.2` and `v1.2.3`; the five changed
payloads matched only `v1.2.3`. All 72 consumer entries were symlinks to the
manager root and no direct same-name directory remained.

The same database rows named `repo_branch=main` and carried update timestamps
from `2026-08-07T16:47:21+08:00` through `16:47:56+08:00`, before this preview.
The review did not cause that state change and cannot attribute it to automatic
refresh, manual action, or another process. The exact report is
[`REPORT.json`](../../audits/mattpocock-skills/6acc160e4e0cd062dbbbd7a1b26ae92855edf07e/manifest-update-preview-2026-08-07/REPORT.json).

## Limits

- GitHub is a mutable external source. These refs were observed on 2026-08-07;
  the exact hashes above, not “latest,” are the durable evidence.
- The upstream note itself used first-party refs and files. A separate temporary
  Git object acquisition then fed the existing previewer; no dependency or
  third-party code ran. The preview read non-secret CC Switch rows and consumer
  topology without mutating them, did not invoke the direct installer, connect
  an account, or dispatch a model. After the report was bound, the Git-only
  temporary root was sent to the Windows Recycle Bin; its original path no
  longer exists and cleanup remains recoverable.
- GitHub's anonymous API and Git transport intermittently returned TLS resets;
  critical refs were cross-checked through the formal release, compare API,
  raw files, tag peeling, and `git ls-remote`.
- No loader, instruction delivery, behavior, causation, user value, cross-host
  portability, rollback, or production claim follows from this review.
- An earlier ambiguous interpretation briefly queried LongHorizon-Harness.
  That result was discarded before this note was written and is not evidence
  for the Matt project assessment.
