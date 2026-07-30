# CC Switch Fourteen-Skill Subtraction Preview — 3.19 Refresh

Date: 2026-07-30
Status: read-only refresh; exact mutation authorization still required

## Outcome

The fourteen-item subtraction cohort remains live and internally unchanged,
but the manager boundary has moved from CC Switch 3.18.0 to the running
3.19.0. The official `v3.19.0` source preserves the required uninstall,
backup, restore, link-removal, and retention semantics for this exact cohort.

This cohort is materially different from the three self-authored collision
rows. Every candidate's Claude and Codex projection is a symbolic link to its
CC SSOT tree. None of the fourteen occupies an externally owned physical
`.codex` directory. Ordinary manager uninstall therefore unlinks the two host
projections without recursively deleting a newer first-party tree.

That source-level safety distinction does not authorize the transaction.

## Current manager evidence

The running binary reports `3.19.0`. The official tag resolves through
`09ccf3280c779c6cf7023cd2c3fc3faa21af8b73` to commit
`c0ff89b9b208c092d6ef40b155403dcf290e5767`. The tag is unsigned according to
GitHub, and binary-to-tag cryptographic identity is not claimed.

The current source:

- validates a stored directory as a safe single segment before uninstall
  filesystem actions;
- creates the CC body and metadata backup before projection, SSOT, or row
  deletion;
- iterates all applications during uninstall;
- removes a symbolic link without deleting its source, but recursively deletes
  a physical target;
- restores one selected host only and rejects identity/directory collisions;
- retains 20 Skill backups by modified time and treats cleanup failure as a
  warning.

All fourteen observed directory names pass the single-segment shape. Their
Claude and Codex targets are CC links. The separate first-party physical-target
hazard is retained as an unchanged sentinel and excluded from this cohort.

## Refreshed live cohort

The database still contains 55 distinct rows. All fourteen target rows remain
local or unattributed, enabled for Claude and Codex, disabled for the other
recorded hosts, and equal to their prior manager content hashes. Their CC trees
still total 19 files and 58,356 bytes; all three projection links resolve to
each target CC tree.

A fresh no-model Codex app-server `skills/list` returned 64 entries and exactly
the fourteen enabled target identities from their direct CC paths. This proves
current exposure on that surface, not invocation, instruction delivery,
behavior, or value.

The refresh freezes new current tree-manifest digests under an explicit
algorithm rather than silently assuming the previous preview's hash
construction: sort files by relative path, emit
`path NUL byte-count NUL file-sha256`, join with LF, and SHA-256 the UTF-8
result.

## Backup rotation

The manager still holds 20 backups. With no concurrent backup creation,
fourteen successful uninstalls create fourteen backups and evict the current
fourteen oldest entries:

`lark-note`, `lark-okr`, `lark-openapi-explorer`, `lark-shared`,
`lark-sheets`, `lark-skill-maker`, `lark-slides`, `lark-task`, `lark-vc`,
`lark-vc-agent`, `lark-whiteboard`, `lark-wiki`,
`lark-workflow-meeting-summary`, and `lark-workflow-standup-report`.

The six existing 2026-07-29 recovery entries remain. This automatic deletion
of recovery evidence is an explicit authorization item, not an incidental
implementation detail.

## Transaction and rollback

`edit-article` remains the one-file canary. Before it:

1. recheck the live manager, database, rows, trees, links, backups, and
   sentinels;
2. create and verify a secret-screened exact recovery archive containing only
   the fourteen bodies, manifests, and bounded row metadata;
3. call `uninstall_skill_unified` for the canary and verify its row, SSOT,
   Claude/Codex links, new backup, fresh host exposure, and unchanged
   sentinels;
4. uninstall the remaining thirteen sequentially and stop on the first error;
5. only after all manager operations succeed, remove the fourteen broken
   `.agents/skills` compatibility links;
6. verify the expected 41-row state, zero broken links, doc/PDF policy, 22
   promoted Matt packages, current source-owned first-party trees, and Trae
   foreign roots;
7. write and verify one configured remote snapshot, then exactly clean the
   recovery archive and temporary CDP/debug helper.

Rollback restores completed removals in reverse order. Each backup restores one
selected host; restoring Claude must be followed by a Codex enable toggle.
Compatibility links remain until the whole manager batch succeeds, so a
pre-cleanup rollback makes them resolve again.

## Authorization boundary

The pending authorization still has five exact parts:

1. uninstall exactly the fourteen named Skills;
2. permit eviction of the fourteen named oldest backups if the backup inventory
   remains concurrent-change-free;
3. remove exactly the fourteen resulting broken common-root links after full
   manager success;
4. write and verify one configured CC remote snapshot;
5. create and then exactly clean the bounded recovery and CDP/debug artifacts.

`diagnose`, the three self-authored rows, first-party physical directories,
doc/PDF shared entities, installs, updates, source relinks, AGENTS/rules,
Hooks, MCPs, Plugins, Apps, global configuration, Trae roots, models, commits,
and pushes remain outside that authorization.

## No-action and claim boundary

No uninstall, restore, toggle, remote snapshot, link cleanup, archive, debug
bridge, Skill execution, model turn, config change, Hook, rule, Plugin, MCP,
App, Trae root, commit, or push occurred. No temporary source root was created.

This refresh proves the bounded 3.19.0 source semantics, current cohort rows,
tree shapes, links, host exposure, and projected backup rotation. It does not
prove executed deletion, post-state, remaining-portfolio behavior, or program
closeout.
