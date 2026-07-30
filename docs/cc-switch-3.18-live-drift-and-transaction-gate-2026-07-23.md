# CC Switch 3.18 Live Drift And Transaction Gate — 2026-07-23

Status: live single-host observation; CC Skill portfolio management is
owner-authorized, but destructive candidates remain recovery-gated
Observed: 2026-07-23T15:20:45+08:00
Machine record:
[`../registry/cc-switch-3.18-live-drift-and-transaction-gate-2026-07-23.json`](../registry/cc-switch-3.18-live-drift-and-transaction-gate-2026-07-23.json)

## Result first

CC Switch remains the operational manager, but the July 19 inventory is now a
dated snapshot rather than live truth. The installed process is `3.18.0` at
official tag commit `606e7bbe75db7f8285f7a3be006fac22b5d22796`.

The live database contains 251 Skill rows and reports 251 Claude plus 251 Codex
enablements. The CC SSOT contains only 75 physical Skill directories. Exactly
176 database directories have no SSOT body, and Claude has 176 corresponding
broken projections. UI or database counts therefore do not equal usable
Skills.

The user has authorized CC-specific admission, retention, disablement,
uninstallation, and cleanup decisions. That authority does not make a
candidate safe to delete. No payload is currently deletion-ready because
recovery, canonical-source, and projection evidence is incomplete.

## Current four-layer truth

| Layer | Observed state | Interpretation |
| --- | --- | --- |
| CC database | 251 rows; 233 distinct names | Registration and per-app flags, not usable-body count |
| CC SSOT | 75 physical directories; all have `SKILL.md` | Current materialized shared pool |
| Claude projection | 251 entries; only 75 resolve | 176 broken projections mirror missing SSOT bodies |
| Codex projection | 77 top-level directories; 75 CC bodies resolve plus two runtime containers | Runtime-owned `.system` and `codex-primary-runtime` are outside CC cleanup |
| Agents directory | 73 directories; no broken entries | Mixed CC projections and 30 physical exceptions |

The CC database has no SSOT-orphan body: every one of the 75 physical
directories has a database row. The active defect is the opposite direction:
176 database rows and their Claude projections have no physical source body.

## Source and version classes

- Six enabled repository registrations remain discovery sources:
  `ComposioHQ/awesome-claude-skills`, `JimLiu/baoyu-skills`,
  `anthropics/skills`, `cexll/myclaude`, `larksuite/cli`, and
  `mattpocock/skills`.
- A repository registration does not prove that a local payload came from that
  repository. Of 75 physical bodies, only 27 Lark Skills, one Composio Skill,
  and Matt's `handoff` have repository attribution in the database.
- The remaining 46 physical bodies are local/unattributed database records.
  Twenty correspond to the repository's inherited approved inventory, but
  attribution still requires immutable source evidence rather than name
  inference.
- Official/runtime/plugin Skills remain host-owned. The 176 missing CC bodies
  are not an instruction to copy runtime caches into CC.

## Two atomic reconciliation cohorts

### Repository-authored contracts

`intent-contract`, `capability-router`, and `closure-contract` are newer and
tree-equal in Agents and Codex, while CC and Claude point to a different older
tree. CC therefore does not yet manage one canonical version across supported
hosts.

Before importing the canonical release into CC:

1. bind the canonical repository revision and exact tree manifest;
2. back up both current trees, not only the older CC tree;
3. retain the passed official isolated uninstall/restore fixtures and obtain
   separate authorization for any live CC integration transaction;
4. import through a CC-supported path;
5. verify Claude and Codex projections separately;
6. retain the repository as source, tests, and review authority.

### Lark cohort

The 27 Lark Skills are one dependency cohort, not 27 independent deletion
candidates. Twenty-six declare `lark-cli`, all reference `lark-shared`, and
most contain sibling-Skill references. Agents and CC copies differ at the byte
level; after line-ending normalization, five still have substantive drift:
`lark-base`, `lark-doc`, `lark-drive`, `lark-im`, and `lark-wiki`.

No generic collaboration trial may treat this cohort as portable. Its next
gate is a concrete Feishu/Lark task with a bound account/data boundary, an
atomic version decision, dependency health evidence, and full-cohort rollback.

## Backup and recovery boundary

CC's official `3.18.0` source confirms that uninstallation creates a Skill
backup before removing application projections, the SSOT directory, and the
database row. Restore refuses to overwrite an existing Skill and recreates one
selected application projection after copying the backup and recomputing its
hash.

Current evidence is still insufficient:

- three database backups reproduce the current 251-row registration state,
  including the stale 176-row condition;
- the 20 retained Skill backups are all Lark-related;
- the three repository-authored contracts have no Skill-level CC backup;
- official source shows that WebDAV/S3 snapshots carry CC's physical SSOT in
  `skills.zip` and rebuild Agent projections locally rather than transporting
  projection links;
- WebDAV manifest equality is not a restore rehearsal. Neither manifest
  equality nor that source contract proves cross-device content equality or
  projection-rebuild success. Individual Skill projection failures are logged
  without making the post-import routine fail.

The local settings surface contains a stored synchronization credential.
Evidence capture must never copy the settings file or credential into this
repository, logs, fixtures, or reports. Credential rotation is a separate
user/account action.

## Ordered CC transaction gate

1. Capture a secret-free manifest of database rows, SSOT bodies, projections,
   canonical trees, and CC hashes.
2. Create content backups for both sides of the three-contract split and the
   complete Lark cohort.
3. Preserve the passed official isolated uninstall/restore fixtures as the
   service-path evidence. Do not add a copy-only canary: deleting and copying
   an extracted directory back would not prove a supported CC operation.
4. Stop the 176-row lane for an owner decision. CC `3.18.0` supports per-item
   disable and uninstall, but neither is a safe reversible batch reconciler
   for rows whose SSOT body is already missing. Direct SQLite editing is not an
   accepted production path.
5. If separately authorized after that decision, exercise one exact visible
   GUI transaction and re-inventory the database, SSOT, and every enabled
   projection. A body-present canary proves only live GUI/service integration,
   not missing-body recovery.
6. Import and distribute one canonical contract release through CC, then
   verify Claude and Codex independently.
7. Treat Lark as an atomic cohort; do not mix the Agents and CC versions.
8. Resolve the two live duplicate-display groups (`git-guardrails` and
   `setup-project-skills`) using directory identity, source, and task evidence.
9. Only then admit, retain, disable, or uninstall individual external
   capabilities from the overlap and ablation matrix.

## Falsifiable acceptance

The cleanup/rebuild transaction passes only if:

- database-managed directories and SSOT bodies are reconciled with no
  unexplained missing body;
- every enabled consumer projection resolves to the selected SSOT body;
- database content hashes equal recomputed SSOT hashes;
- Claude and Codex receive the intended canonical contract trees;
- Lark sibling references remain complete and version-coherent;
- a restore rehearsal reproduces file bytes, database state, and projection;
- runtime-owned host directories are unchanged;
- no credential or private account content enters repository evidence.

Until then, supported status is `authorized-but-recovery-gated`, not
`cleanup-complete`.
