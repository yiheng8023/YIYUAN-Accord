# CC Switch 3.18 Stale-Row Reconciliation Gap — 2026-07-23

Status: source-pinned capability-gap finding; no live row removed
Source: `farion1231/cc-switch` tag `v3.18.0`, commit
`606e7bbe75db7f8285f7a3be006fac22b5d22796`
Machine record:
[`../registry/cc-switch-3.18-stale-row-reconciliation-gap-2026-07-23.json`](../registry/cc-switch-3.18-stale-row-reconciliation-gap-2026-07-23.json)

## Result first

CC Switch `3.18.0` does not expose a supported stale-row detector, preview,
batch reconciler, or transactional rebuild for the live condition “database
row exists, SSOT body is missing.”

It does expose supported per-item disable and uninstall mutations. Those paths
are narrower than reconciliation: disable leaves the database tombstone and
cannot re-enable it without a body, while missing-body uninstall removes the
row without producing a restorable content backup.

The 251 count shown by CC is consistent with its implementation: the installed
list returns database rows without validating the SSOT body. The live 176-row
gap is therefore not a display-count bug. It is an integrity gap between the
database, SSOT, and consumer projections.

No direct SQLite repair, hidden migration flag, WebDAV round-trip, import scan,
or internal RPC loop is accepted as a substitute for a supported reconciliation
path.

## Live stale-row classification

| Dimension | Result |
| --- | ---: |
| Missing-body database rows | 176 |
| Unique missing directories | 176 |
| Missing-directory duplicate groups | 0 |
| Rows with repository attribution | 0 |
| Rows without repository attribution | 176 |
| Exact current runtime-plugin directory matches | 148 |
| Qualified runtime-plugin alias matches | 25 |
| Heuristic unresolved | 3 |

The runtime-plugin matches are identity evidence, not permission to copy
runtime-owned plugin payloads into CC. The three heuristic unresolved entries
are `product-design-prototype`, `suggest-sales-next-step`, and
`sales-user-context`; “unresolved” means only that the current matcher did not
prove a source.

## Supported and unsupported paths

### Single-item uninstall

The supported GUI path is single-item only:

```text
item confirmation
-> frontend uninstall mutation
-> uninstall_skill_unified
-> SkillService::uninstall
```

The service tries to back up a body, removes application projections, removes
the SSOT directory, and then removes the database row. If no body exists in the
SSOT or application roots, it skips the content backup and continues.

This may remove a proved tombstone, but it is not atomic. Projection-removal
errors are ignored, and later filesystem or database failure has no
transactional rollback. A tombstone also has no content backup to restore.

### Import and ZIP install

The unmanaged scan treats every database directory as already managed before
looking for bodies. It therefore cannot rediscover a body with the same stale
directory. ZIP install also skips a directory already registered in the
database. Neither path is a stale-row repairer.

### Repository update

`update_skill` can rebuild a missing body only when a row has correct repository
metadata and the remote still contains the expected directory. All 176 live
rows lack repository attribution. The UI also offers update only after a hash
comparison that does not first prove that the local body exists. This path
cannot reliably reconcile the live set.

### Startup and storage migration

The v2-to-v3 SSOT rebuild is a one-time internal migration, not a registered
command. Startup skips it when the Skills table is nonempty. Storage migration
records missing bodies as skipped and preserves the database row. Neither is a
supported maintenance operation for this state.

### Ordinary sync

Ordinary application sync can clean some disabled or orphan projections but
does not remove stale database rows. An enabled row with no SSOT body can raise
an error and terminate the remaining application sync, so the current debt may
also block later projection refresh.

### WebDAV

WebDAV moves a paired database export and Skills archive as a whole. Uploading
the current 251/75 state would preserve the inconsistency. Restoring from an
unverified remote snapshot crosses account and full-database boundaries and is
not a local stale-row cleanup mechanism.

## Decision

There is no evidence-supported bulk mutation to run now.

The accepted conservative route is:

1. keep the secret-free recovery archive and immutable source evidence;
2. classify each stale row by source, runtime ownership, and recoverability;
3. stop for an owner decision before accepting the irreversible boundary of
   per-item missing-body cleanup;
4. if one exact visible GUI transaction is separately authorized, re-inventory
   the database, SSOT, and every supported projection afterward;
5. do not treat a body-present uninstall/restore canary as stale-row recovery;
6. stop on any unexplained delta;
7. retain the remaining capability gap for upstream improvement rather than
   create a parallel Skill manager or direct-database cleaner.

The absence of a batch reconciler simplifies neither the evidence obligation
nor the authorization boundary. It only narrows what can honestly be automated
through CC today.

## Visible GUI canary preflight

`-21risk-automation` was selected as the first recoverable canary because it is
outside the repository-authored contracts, Lark cohort, and runtime-owned
containers. Its CC body and Claude/Codex projections are tree-equal at
`d30d3753baad308fd33e66089bf3f12917aedd72a7888ff28918ab5cd7ad117f`;
both application flags are enabled, and its body is present in the selected
recovery archive.

The database points to `ComposioHQ/awesome-claude-skills@master`. Current master
is `92568c1edaff1bde5371154f036d959346c145a8`, whose body is not byte-equal to
the local canary. Historical commit
`27904475d1270d8395acf07691966267d5abda2d` is the exact source match. This
separates “current upstream source” from “exact recovery source.”

The supported visible-UI transaction was not executed. The bundled Windows
desktop-control runtime was initialized twice after the client restart and
timed out at 60 and 120 seconds before any UI interaction. The runtime reset
after each timeout. A post-attempt read-only check still found the database row,
SSOT body, and both projections unchanged.

Because this selected item has a body, even a later successful transaction
would prove only live GUI/service integration and ordinary body-backed recovery.
It would not prove that a missing-body tombstone can be restored, and it is no
longer the next gate for the 176-row lane.

No internal Tauri RPC, direct database edit, hidden automation helper, or
unconfirmed UI coordinate action replaced the unavailable supported path.
The canary stays `selected-and-recoverable-but-ui-runtime-blocked`; this is not
a failed CC uninstall/restore result and not a stale-row recovery result.

## Upstream residual capability

A maintainable upstream solution would need:

- an integrity preview across database rows, SSOT bodies, and app projections;
- stale-only multi-select or batch cleanup;
- paired database-and-file recovery snapshots;
- transactional behavior or a durable per-item result ledger;
- batch backup retention independent of the current 20-backup rotation;
- regression tests for missing-body uninstall and duplicate-directory cases;
- a post-repair rescan and verification report.

Opening an upstream issue or proposing code is a separate external-write
decision. This repository records the gap but does not claim that CC has
accepted or scheduled it.
