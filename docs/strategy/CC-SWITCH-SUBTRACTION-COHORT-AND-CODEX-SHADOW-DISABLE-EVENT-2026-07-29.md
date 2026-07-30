# CC Switch Subtraction Cohort And Codex Shadow Disable Event

Date: 2026-07-29

Status: **exact shared subtraction and Codex-only shadow disable verified on the current host**

## Result

The owner authorized one exact subtraction transaction. CC Switch removed
`-21risk-automation`, both `git-guardrails` directories,
`scaffold-exercises`, `write-a-skill`, and `sora` from its shared entity
store and from the Claude and Codex projections. Five compatibility links
under `~/.agents/skills` became broken as a direct consequence and were then
removed by exact path. The common root itself was preserved.

`doc` and `pdf` were not uninstalled. CC Switch's `toggle_skill_app` backend
disabled only their Codex projection. Both remain in the CC Switch store,
Claude projection, and common compatibility root. Codex retains its broader
runtime-owned `documents` and `pdf` capabilities under
`codex-primary-runtime`.

The database moved from 61 rows with 60 distinct names to 55 rows with 55
distinct names. Claude has 55 enabled rows. Codex has 53 CC-managed enabled
rows plus its `.system` and `codex-primary-runtime` roots. No broken Skill
links remain on CC Switch, common, Claude, or Codex surfaces.

## Manager path and recovery

The mutation used CC Switch 3.18.0's own `uninstall_skill_unified` and
`toggle_skill_app` Tauri commands through a temporary loopback WebView2 CDP
bridge. SQLite was read only for verification.

Before mutation, a secret-screened recovery archive captured all 61 CC Skill
bodies, the three unique common-root bodies, all 20 existing CC Skill
backups, safe database columns, and projection topology. It excluded settings,
credentials, account data, and the raw database. The archive passed content
hash, extraction, source-consistency, and secret checks.

A one-item `-21risk-automation` canary succeeded before the remaining five
uninstalls and two Codex-only toggles. CC Switch retained all six exact
manager backups among its 20 managed backups. An explicit WebDAV upload
returned `uploaded`; the compatible remote snapshot contains `db.sql` and
`skills.zip`.

After verification, the temporary recovery archive, manifest, and CDP helper
were removed. CC Switch was restored to one ordinary background process and
the temporary debug port was closed.

## Preserved scope

Matt's 22 promoted rows remain installed. `intent-contract`,
`capability-router`, `closure-contract`, `caveman`, and `kimi-webbridge`
remain enabled for both Claude and Codex. No Hook, `AGENTS.md`/rules carrier,
CC Switch storage setting, model route, Git commit, or push changed.

Trae's common and versioned Plugin roots were excluded from every mutation
target. Their current read-only counts are 104 and 26 Skills respectively.
This transaction did not capture a pre/post Trae content-hash sentinel, so the
record claims bounded target exclusion rather than byte-level foreign-root
equality.

## Verification and limits

The 24-test extended SEM-03 projection, exposure, continuity, and current-Matt
static-admission set passed. The event-specific validator tests and
`python -B scripts/verify.py` passed after the temporary process root was
removed and the governed cleanup inventory returned to its expected state.

This task's startup Skill catalog predates the mutation. A fresh task or host
refresh is still required to observe catalog disappearance. The event proves
the exact shared subtraction, the two Codex-only projection disables, manager
backup/sync, and process cleanup on the current host. It does not prove loader
invocation, behavioral value, the quality of the remaining portfolio, final
disposition of the self-authored chain, or program closeout.
