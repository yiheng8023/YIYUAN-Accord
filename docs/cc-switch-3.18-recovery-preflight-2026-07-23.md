# CC Switch 3.18 Recovery Preflight — 2026-07-23

Status: local recovery artifact verified; official isolated uninstall/restore
fixtures pass; live CC mutation has not started
Observed: 2026-07-23T15:45:25+08:00
Machine record:
[`../registry/cc-switch-3.18-recovery-preflight-2026-07-23.json`](../registry/cc-switch-3.18-recovery-preflight-2026-07-23.json)

## Result first

The recovery gate has advanced without changing CC Switch or any live Agent
Skill root.

Two official `3.18.0` integration tests passed against an isolated test home:

- `uninstall_skill_creates_backup_before_removing_ssot`;
- `restore_skill_backup_restores_files_to_ssot_and_current_app`.

A separate secret-screened local recovery archive was built from the live
machine and then extracted into a temporary directory. The archive and
extracted payloads were independently rehashed. It contains 75 CC SSOT bodies,
all 30 unique physical Agents bodies, the three canonical repository contracts,
all 20 existing CC Skill backups, 251 safe Skill database rows, six
repository-registration rows, and projection topology.

This is strong pre-change recovery evidence. It is not yet a real-user-state CC
uninstall/restore rehearsal and does not authorize direct SQLite repair.

## Recovery artifact

| Field | Evidence |
| --- | --- |
| Archive | `C:\tmp\cc-switch-skill-recovery-20260723-prechange-v3.zip` |
| Sidecar | `C:\tmp\cc-switch-skill-recovery-20260723-prechange-v3.manifest.json` |
| SHA-256 | `a3e760d0d9700e72be2fed34fe1eaee108d9f31b478068826e5b635f9a07b26d` |
| Size | 5,560,348 bytes |
| Payload files | 1,493 |
| CC SSOT bodies | 75 |
| Agents unique physical bodies | 30: three contracts plus 27 Lark Skills |
| Canonical contracts | 3 |
| Existing CC Skill backups | 20, captured before any retention rotation |
| Safe database metadata | 251 Skill rows and six repository rows |
| Extraction rehearsal | member paths, file set, archive hashes, and extracted hashes matched |
| Source consistency | selected roots, files, safe database export, and projection topology matched before/after capture |

The snapshot is produced by
[`../scripts/build_cc_skill_recovery_snapshot.py`](../scripts/build_cc_skill_recovery_snapshot.py).
Its focused tests verify exclusion, high-confidence secret rejection, archive
integrity, extraction integrity, and overwrite refusal.

## Secret and account boundary

The snapshot code never reads `settings.json` and never copies the raw CC
SQLite database. It exports only explicit columns from the `skills` and
`skill_repos` tables. Provider configuration, account data, credentials, and
WebDAV material are excluded.

Before writing the archive, every selected Skill or backup file and generated
metadata record is screened for high-confidence private-key, OpenAI-key,
GitHub-token, AWS-access-key, and Slack-token forms. The completed archive is
then scanned again. No match was found.

This screening is deliberately bounded. A zero result is not proof that
arbitrary prose contains no sensitive business information. The artifact stays
local under `C:\tmp` and must not be committed or uploaded.

The earlier `prechange.zip` and `prechange-v2.zip` pairs were valid intermediate
artifacts. The first omitted the pre-existing 20-backup history; the second did
not enforce pre/post live-source equality. Both remain explicit final-cleanup
debt and are not the selected recovery package.

## Official fixture evidence

The tests were run from the official `v3.18.0` source fixed at
`606e7bbe75db7f8285f7a3be006fac22b5d22796`.

The uninstall fixture verifies that the Skill body and metadata are backed up
before the SSOT directory and database row are removed. The restore fixture
then verifies that the body returns to the SSOT, the database row returns, and
only the selected application projection is enabled and recreated.

The fixtures exercise the same `SkillService` paths exposed by the Tauri
commands. They do not exercise this machine's live database, GUI, WebDAV
transport, or the 176 missing-body rows.

## Official cloud-sync source boundary

A separate read-only review used the same official `v3.18.0` commit. The
relevant implementation is in `services/webdav_sync.rs`,
`services/sync_protocol.rs`, `services/webdav_sync/archive.rs`,
`commands/webdav_sync.rs`, `commands/sync_support.rs`, and
`services/provider/live.rs`.

The source contract is materially narrower than a general machine backup:

- WebDAV and S3 share a snapshot protocol whose remote set is `db.sql`,
  `skills.zip`, and `manifest.json`.
- `skills.zip` is recursively built from CC's physical
  `~/.cc-switch/skills` SSOT. Agent projection links are not cloud artifacts
  and do not need to travel with the snapshot.
- CC's separate Skill uninstall-backup directory is not part of `skills.zip`.
- Download validates the artifacts and replaces the entire local CC SSOT. It
  backs up the prior SSOT and rolls it back if the subsequent database import
  fails.
- After download, CC attempts to rebuild Skill projections for every supported
  application from database enablement state. An individual Skill projection failure is logged
  and does not make that post-import routine fail.

This static source review supports CC-as-SSOT with locally derived projection
links. It does not prove a successful WebDAV or S3 transfer, cross-device
content equality, or successful projection rebuild on this machine. No cloud
transport was executed and no synchronization credential or settings file was
read for this review. Restoring the existing database would also reproduce its
176 stale rows; the snapshot protocol does not automatically heal them.

## What remains recovery-gated

- Supported per-item disable and uninstall mechanisms exist, but no safe,
  reversible batch mechanism exists for reconciling the 176 missing-body rows.
  Disable leaves the tombstone and cannot re-enable without a body; uninstall
  removes the row without producing a restorable content backup.
- Direct database mutation remains prohibited.
- No live Skill has been uninstalled, restored, imported, overwritten, or
  deleted.
- The 176 Claude broken projections remain present.
- The contract split and five substantively drifted Lark bodies remain
  unchanged.
- The local archive is not cross-device recovery proof and is not a durable
  off-device backup.

The next gate is an owner decision on stale-row debt disposition: retain it,
accept a bounded per-item irreversible cleanup risk, or pursue an upstream
integrity/reconciliation capability. The gap does not justify bypassing CC with
an unreviewed database script.
