# Skill Runtime and CC Count Drift Snapshot

Date: 2026-07-27

Status: **current-host read-only drift reconciled; no mutation**

## Result first

The old CC Switch screenshots were not necessarily miscounted. They showed a
database or enabled-projection surface, not the number of unique physical,
resolvable Skill bodies.

The current host has:

| Surface | Entries | Resolvable `SKILL.md` |
| --- | ---: | ---: |
| CC Switch database enabled for Claude | 251 | not a body count |
| CC Switch database enabled for Codex | 251 | not a body count |
| CC Switch physical SSOT | 75 | 75 |
| `~/.agents/skills` | 73 | 73 |
| Claude projection | 251 | 75 |
| Codex top-level projection/container roots | 77 | 75 |

The previously classified 176 missing-body rows remain present. Claude has 176
links whose CC target lacks a resolvable `SKILL.md`. The Codex count includes
two container roots, `.system` and `codex-primary-runtime`, which are not
top-level Skills. UI counts, database rows, physical bodies, projections, and
loader invocation must therefore be reported separately.

No CC row, body, link, setting, backup, or account state was changed.

## Later authorized update event

The read-only snapshot above remains historical. A later separately authorized
[seven-Skill Lark update event](CC-SWITCH-LARK-SEVEN-SKILL-UPDATE-EVENT-2026-07-27.md)
applied all seven pending updates through CC Switch and verified current
`SKILL.md` entrypoint equality against `larksuite/cli` `HEAD`. It did not prove
whole-tree equality or repair the 176 unresolved Claude entries; the Composio
discovery 404 also remains open.

## Current source drift

Matt's current `main` remains
`ed37663cc5fbef691ddfecd080dff42f7e7e350d`, so the existing pinned Matt
content review has not drifted.

The current OpenAI-curated Superpowers package is `6.2.0`, release commit
`3dcbd5c4b48e02263fbf4a3c01e3fe4f81d584d9`. The older general overlap
matrix used `6.1.1`, so it remains historical rather than current runtime
evidence. Version `6.2.0` is the current runtime-owned source/package
baseline, not a behavioral baseline or execution-admission decision.

The local `6.2.0` package contains 72 files:

- 55 are exact Git blobs from the release commit;
- 14 `SKILL.md` entries are all exact release bytes;
- 17 files differ or are added by OpenAI packaging: one manifest, two assets,
  and fourteen `agents/openai.yaml` metadata files.

Five of the prior six sampled Superpowers Skills changed between the recorded
`6.1.1` package and `6.2.0`; only `using-superpowers` retained the same
digest. The existing TDD protocol already pins the current `6.2.0`
`test-driven-development` and `writing-good-tests` payloads, so that selective
arm is not invalidated.

## Subtractive portfolio consequence

Superpowers remains runtime-owned. Copying its payloads into CC merely to make
Codex see them would create a second source of truth with no demonstrated
behavioral benefit. Prefer source-pinned selective use:

- retain `test-driven-development` as the current isolated TDD comparison arm;
- retain `systematic-debugging` as a bounded diagnostic candidate;
- allow `verification-before-completion` to produce domain evidence without
  replacing cross-domain closure;
- study the plan-scoped workspace and review-loop ideas from
  `subagent-driven-development`, but do not adopt its controller, commit,
  cleanup, or resume assumptions as global policy.

Do not make `using-superpowers`, `brainstorming`, or the full bootstrap a
global default. Their mandatory process rules conflict with native/no-Skill
minimal sufficiency, proportional fast paths, and separate write, commit,
branch, worktree, cleanup, and user-review authority.

The optional brainstorming visual companion is also a distinct data boundary.
Its documentation says the remote logo may transmit the Superpowers version
unless telemetry is disabled. It is not automatic at plugin startup and was
not activated or tested here.

## Claim boundary

Exact bytes prove source identity, not invocation or value. CC database
enablement does not prove a resolvable body or loader use. Source registration
does not mean that every repository Skill is installed. No weak-Agent
superiority, cross-device equality, stale-row repair, safe migration,
deduplication, self-authored residual gap, or portfolio retirement is proved
by this snapshot. The local backup-directory inventory does not prove restore
success or content equality after moving to another device.
