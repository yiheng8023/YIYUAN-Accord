# Matt Pocock Skills v1.2.3 exact-pin reconciliation

Date: 2026-08-08
Status: committed, restart-persistent, metadata-only

## Outcome

The 25 CC Switch rows for `mattpocock/skills` now bind source metadata to the
annotated release `v1.2.3`, peeled to
`6acc160e4e0cd062dbbbd7a1b26ae92855edf07e`. The previous mutable `main`
values were replaced only in `repo_branch` and `readme_url`; `updated_at` is
the transaction timestamp.

The transaction did not rewrite Skill payloads, consumer links, enabled flags,
or the manager-owned `content_hash`. That hash is retained as an opaque CC
Switch field; exact payload identity is proved independently from the immutable
Git release trees.

## Evidence

| Surface | Verified result |
| --- | --- |
| Upstream identity | annotated tag object `835450ef244ab7335f75d95b83e7d979eae22a6d` peels to the exact release commit |
| Database | 25 rows; all `repo_branch = v1.2.3`; all 25 README URLs use `/blob/v1.2.3/` |
| Enabled state | Claude 24, Codex 24, all other hosts 0; `wizard` remains disabled |
| Payloads | 25/25 match the exact release; SSOT snapshot stayed `22c09224bd8614b72eaca269fc42ffa9fe39025b61617cd9ddbd08221f410e5d` |
| Consumers | 72 symlinks across common, Claude, and Codex roots; 0 direct directories |
| Recovery | exact before/target rows in the local journal; injected post-commit failure and explicit synthetic rollback tests pass |
| Execution | 0 third-party scripts, 0 model calls, 0 payload writes, 0 consumer writes |

The portable post-restart report is
[`POST-RESTART-REPORT.json`](../../audits/mattpocock-skills/6acc160e4e0cd062dbbbd7a1b26ae92855edf07e/exact-pin-reconciliation-2026-08-08/POST-RESTART-REPORT.json).
The governed event is
[`mattpocock-skills-v1.2.3-exact-pin-reconciliation-event-2026-08-08.json`](../../registry/mattpocock-skills-v1.2.3-exact-pin-reconciliation-event-2026-08-08.json).

## Recovery boundary

The local journal remains at
`C:/Users/15521/.cc-switch/skill-backups/aah-matt-v123-exact-pin-20260808T161214/journal.json`.
Rollback is implemented by `rollback_exact_pin` in
`scripts/reconcile_matt_cc_manager_exact_pin.py`, is restricted to the same
three metadata columns, and must run while CC Switch is quiesced. A live
rollback was not needed and was not executed.

The isolated exact-source Git root was moved to the Windows Recycle Bin after
the report was bound. Its original path no longer exists and one matching
recoverable entry was observed.

## Claim boundary

This proves exact source provenance, a committed metadata-only transaction,
unchanged payload/projection/enablement surfaces, and persistence across an
ordinary manager restart. It does not prove loader invocation, instruction
delivery, task behavior, value, cross-host portability, or production
readiness. The 46 verified / 15 partial / 0 planned acceptance inventory does
not change.
