# CC Switch Lark Cohort Removal Event

Date: 2026-07-28

Status: **shared 27-Skill Lark cohort removed and verified on the current host**

## Result

The owner confirmed that the shared Lark cohort was not needed and authorized
its removal while preserving Trae's independently managed roots. The exact 27
shared `lark-*` Skills were treated as one dependency cohort.

CC Switch 3.18.0 was the manager mutation surface. A one-Skill canary succeeded,
then the remaining 26 Skills were removed through the same backend. The
database moved from 88 rows with 27 Lark rows to 61 rows with zero Lark rows.
The CC Switch SSOT, Codex projection, and Claude projection all contain zero
Lark entries and zero broken links.

The independent schema-3 lock-managed copies under `~/.agents/skills` were not
silently reclassified as CC projections. Their exact 27 directories were
removed together and the lock was atomically replaced with a valid empty Skill
map. The remaining `.agents` root contains 46 entries: 43 links and three
physical repository-authored control-chain Skills.

## Directory authority applied

This event applies the previously agreed directory boundary:

- `~/.cc-switch/skills` is the shared third-party entity store;
- Codex and Claude are CC Switch managed consumer projections;
- `~/.agents/skills` is a compatibility or unsupported-host adapter surface,
  not a second third-party entity store;
- Trae's common Skill root and versioned Feishu Plugin root are foreign-managed.

`skillStorageLocation` remains `cc_switch`. No unified-directory migration or
parallel installer was introduced.

## Foreign-root isolation

Trae's common root had zero Lark Skills before and after. Its versioned Feishu
Plugin retained 26 Lark Skills before and after. Pre/post name and content-hash
sentinels were stable on both roots. Nothing was copied, backfilled, rehomed,
or deleted under Trae.

## Backup, sync, and cleanup

CC Switch retained its 20 managed rollback backups. An explicit remote sync
returned `uploaded` and exposed the new compatible snapshot with `db.sql` and
`skills.zip`.

The temporary source clone, snapshot helper, and agent-created recovery bundle
were removed after verification. The recovery bundle was not retained because
the owner had already selected CC Switch's own managed backup and cloud sync as
the recovery authority. The temporary WebView debug listener was closed and CC
Switch was restarted normally with one process.

No unrelated `.agents` entry, foreign root, repository-local temporary root,
Hook, model, credential, Git commit, or remote repository was changed.

## Verification and limits

The current semantic-authority focused suite contains 18 tests, superseding the
16-test handoff count; all 18 passed. `python -B scripts/verify.py` also passed
after the governed cleanup inventory remained stable.

This task's Skill catalog was captured before removal, so a fresh task or UI
refresh is still required to observe catalog disappearance. The event proves
shared storage removal, projection cleanup, foreign-root isolation, manager
sync, and exact process cleanup. It does not prove fresh-task loader behavior,
cross-host behavior, portfolio quality, or program closeout.
