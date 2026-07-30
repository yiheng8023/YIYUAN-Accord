# Self-authored three Claude carrier and subtraction sequencing decision preview

Date: 2026-07-30
Status: read-only decision-ready preview; no mutation authorized

## Decision

The preferred Claude policy is now **B: source-owned Claude symlink adapter**,
not temporary quarantine.

Claude Code's current official Skill documentation explicitly says that from
v2.1.203 onward, a personal or project Skill entry may be a directory symlink,
Claude follows it to `SKILL.md`, and the same target reachable from several
locations is loaded once. The installed Claude Code is 2.1.220. The adapter can
therefore be the small host-specific projection:

```text
~/.claude/skills/<name> -> ~/.agents/skills/<name>
```

This does not require a Hook, custom loader, duplicate body copy, Plugin
namespace, or parallel Skill manager. `codex-user-config` remains the source
authority, `.agents` remains the portable physical projection, and CC Switch
continues to own shared third-party Skills.

The official documentation still names `~/.claude/skills`, project
`.claude/skills`, and Plugin Skills; it does not document direct discovery from
`~/.agents/skills`. The host-specific link is therefore still required.

Primary source:
[Extend Claude with skills](https://code.claude.com/docs/en/skills),
accessed 2026-07-30.

The same page documents `enterprise > personal > project` for name
collisions. An official-repository issue reports the opposite personal/project
runtime observation and was closed without a product resolution. This preview
therefore treats the order as the documented contract only; current runtime
precedence has not been independently proved, and the three names should remain
unique across standalone scopes.

## Why A is no longer preferred

Option A would safely remove the three stale Claude links but leave Claude
without `intent-contract`, `capability-router`, or `closure-contract`.
That would discard the current Claude arm before these three falsifiable
candidates have been compared against native and upstream alternatives.

Before official symlink support was verified, that temporary loss avoided an
unproved adapter. The v2.1.203 contract removes that specific uncertainty.
Option B now preserves the test arm with less lifecycle machinery than either
a copied third body or a Plugin.

This does not prove live Claude exposure. The current three links still resolve
to older CC bodies, and the Plugin CLI correctly reports no installed Plugins;
standalone Skills and Plugin registration are different lifecycle surfaces.

One authoring-quality warning remains. Exact newline counts are 504 for
`intent-contract`, 419 for `capability-router`, and 253 for
`closure-contract`. The first is four lines above Claude's guidance to keep a
`SKILL.md` below 500 lines. The documentation does not present 500 lines as a
hard loader limit, so this does not block the static adapter design. It also
does not justify editing the frozen control body before exposure and value
evidence identifies a real adaptation need.

## Collision-safe manager sequence

Ordinary CC uninstall remains unsafe while each current physical
`.codex/skills/<name>` tree occupies the destination that CC Switch tries to
remove. The later transaction must:

1. fixture-test an explicit opt-in Claude-link adapter in
   `codex-user-config`;
2. create and verify the bounded secret-screened recovery archive;
3. close Codex consumers;
4. for each first-party name, move only its current physical Codex tree to a
   bounded quarantine, invoke the ordinary manager uninstall, then immediately
   restore and hash-verify that Codex tree;
5. stop and roll back on the first failure; and
6. only after the old Claude link is absent, rename a staged new link to the
   current `.agents` physical tree into place.

A local disposable Windows simulation proved that a staged directory link can
be renamed into an absent destination. Replacing an existing directory symlink
with `os.replace` failed with `WinError 5`. This is why the old CC-owned link
must leave through the manager transaction before the source-owned link is
installed.

No direct database write is required.

## The two transactions are coupled

The manager retains only 20 Skill backups. The currently prepared fourteen
uninstalls create fourteen backups and evict the fourteen named oldest Lark
backups. Retiring the three first-party CC rows later creates three more
backups. Assuming no concurrent CC mutation, those three would additionally
evict:

- `20260729_093746_21risk-automation`;
- `20260729_093826_git-guardrails`; and
- `20260729_093827_git-guardrails-claude-code`.

Across both phases, seventeen original backups leave. The final three original
backups are `scaffold-exercises`, `write-a-skill`, and `sora`; the full
pre-transaction recovery archive remains the independent recovery surface.

Run the fourteen-item transaction first. Its whole-state preflight is current
now. Running the three first-party retirements first would invalidate all
current database, tree, projection, and backup fingerprints and force the
fourteen-item preview to be rebuilt. The first-party phase still needs a fresh
preflight and a new explicit authorization for the additional three backup
evictions.

## Projected topology under B

After both phases, if no concurrent state changes and every verification gate
passes:

| Surface | Projected count or state |
|---|---:|
| CC database rows | 38 |
| CC physical Skill trees | 38 |
| `.agents/skills` entries | 27 |
| `.claude/skills` entries | 41 |
| `.codex/skills` top-level entries | 41 |
| first-party CC rows/bodies | 0 |
| first-party `.agents` physical trees | 3 |
| first-party `.codex` physical trees | 3 |
| first-party Claude links to `.agents` | 3 |

These are forecasts, not a proved post-state.

## Verification boundary

The next Claude evidence ladder remains:

1. fresh no-model `/skills` menu or autocomplete exposure;
2. explicit invocation in a separate authorized model turn;
3. proof that the intended instructions reached the model;
4. paired behavior evidence; and
5. incremental value over native or reviewed upstream alternatives.

The ordinary `claude plugin list` result is not a standalone Skill inventory.
No documented standalone no-model CLI inventory command was found. The
documented `/skills` UI is the next exposure surface, but it is not invocation,
instruction delivery, behavior, or value proof.

No installer, Skill, CC row, link, backup, host configuration, interactive
Claude session, model, commit, or remote changed in this preview.
