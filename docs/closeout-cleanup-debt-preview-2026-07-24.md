# Closeout cleanup-debt preview — 2026-07-24

This is a repository-local inventory preview, not cleanup execution and not
program closeout evidence.

This document is now a frozen pre-cleanup snapshot. The exact 2026-07-30
execution and post-delete absence are recorded separately in
`closeout-cleanup-execution-2026-07-30.md`; the historical digest and counts
below are intentionally unchanged.

The registry identity/date remains `closeout-cleanup-debt-preview-2026-07-24`
for compatibility. The latest read-only observation is 2026-07-27.

The bounded scan covers the thirty-five exact top-level roots currently present
under `.tmp`, including thirty-one directories and four standalone JSON reports.
It counts paths and file sizes and classifies filename suffixes. It does not
open SQLite databases, JSONL logs, session state, or other retained runtime
content.

## Current inventory

| Measure | Observed value |
| --- | ---: |
| Exact roots | 35 |
| Files | 2,459 |
| Directories below the roots | 811 |
| Total bytes | 60,346,279 |
| Roots containing SQLite-like runtime state | 15 |
| Directly path-bound evidence roots | 18 |
| Evidence-class-only roots | 17 |
| Reparse points | 0 |
| Unexpected `.tmp` top-level entries | 0 |

### Retention classes

These classes distinguish authoritative evidence from process artifacts without
turning either into a deletion candidate. Invalid/excluded attempts remain
evidence of those invalid or excluded attempts; the label does not validate
their intended experimental outcome.

| Retention class | Roots | Files | Directories | Bytes |
| --- | ---: | ---: | ---: | ---: |
| Authoritative evidence | 16 | 1,235 | 566 | 36,352,497 |
| Invalid or excluded attempt evidence | 11 | 516 | 237 | 16,758,179 |
| Process artifact with unresolved authority | 7 | 707 | 8 | 6,686,417 |
| User source preservation | 1 | 1 | 0 | 549,186 |

### Exact repository-local roots

| Exact root | Retention class | Files | Directories | Bytes |
| --- | --- | ---: | ---: | ---: |
| `.tmp/mcp-child-exit-recovery-20260723-run01` | authoritative evidence | 74 | 32 | 2,317,886 |
| `.tmp/mcp-child-exit-recovery-20260723-run02` | authoritative evidence | 77 | 33 | 2,310,808 |
| `.tmp/mcp-idle-observation-20260723` | authoritative evidence | 68 | 32 | 1,465,264 |
| `.tmp/mcp-idle-preflight-20260723` | authoritative evidence | 72 | 32 | 2,301,969 |
| `.tmp/mcp-idle-preflight-20260723-b` | authoritative evidence | 72 | 32 | 2,302,062 |
| `.tmp/mcp-startup-profiles-20260723-run01` | authoritative evidence | 410 | 198 | 11,847,044 |
| `.tmp/source-archives` | user source preservation | 1 | 0 | 549,186 |
| `.tmp/codex-app-server-schema-0145-tdd-20260726` | unresolved process artifact | 347 | 2 | 3,303,877 |
| `.tmp/tdd-raw-item-pilot-20260726-r1` | authoritative evidence | 12 | 3 | 443,375 |
| `.tmp/tdd-raw-item-pilot-20260726-r2` | authoritative evidence | 12 | 3 | 414,573 |
| `.tmp/tdd-formal-native-20260726-r1` | authoritative evidence | 10 | 3 | 398,039 |
| `.tmp/tdd-formal-native-20260726-r2` | authoritative evidence | 9 | 1 | 409,052 |
| `.tmp/tdd-formal-native-20260726-r3` | authoritative evidence | 8 | 3 | 191,414 |
| `.tmp/app-server-schema-0.145.0` | unresolved process artifact | 347 | 2 | 3,303,877 |
| `.tmp/process-fidelity-live-20260727` | invalid/excluded attempt evidence | 4 | 1 | 25,984 |
| `.tmp/process-fidelity-v2-zero-dispatch-20260727` | unresolved process artifact | 4 | 2 | 22,897 |
| `.tmp/process-fidelity-v2-zero-dispatch-20260727-report.json` | unresolved process artifact | 1 | 0 | 509 |
| `.tmp/process-fidelity-v2-live-20260727-r1-source-backed` | invalid/excluded attempt evidence | 4 | 2 | 22,897 |
| `.tmp/process-fidelity-v2-live-20260727-r1-source-backed-report.json` | invalid/excluded attempt evidence | 1 | 0 | 12,601 |
| `.tmp/process-fidelity-v2-zero-dispatch-corrected-20260727` | unresolved process artifact | 4 | 2 | 22,897 |
| `.tmp/process-fidelity-v2-zero-dispatch-corrected-20260727-report.json` | unresolved process artifact | 1 | 0 | 509 |
| `.tmp/process-fidelity-v2-live-20260727-r2-source-backed` | authoritative evidence | 4 | 2 | 22,897 |
| `.tmp/process-fidelity-v2-live-20260727-r2-source-backed-report.json` | authoritative evidence | 1 | 0 | 12,599 |
| `.tmp/mcp-unsubscribe-attribution-calibration-20260727-01` | invalid/excluded attempt evidence | 136 | 64 | 4,421,064 |
| `.tmp/mcp-unsubscribe-attribution-formal-20260727-01` | authoritative evidence | 136 | 64 | 4,392,363 |
| `.tmp/mcp-unsubscribe-attribution-formal-20260727-02` | authoritative evidence | 134 | 64 | 3,130,780 |
| `.tmp/mcp-unsubscribe-attribution-formal-20260727-03` | authoritative evidence | 136 | 64 | 4,392,372 |
| `.tmp/mcp-multi-connection-subscription-preflight-2026-07-27-attempt-01` | invalid/excluded attempt evidence | 4 | 5 | 987 |
| `.tmp/mcp-multi-connection-subscription-preflight-2026-07-27-attempt-02` | invalid/excluded attempt evidence | 73 | 33 | 2,263,970 |
| `.tmp/mcp-multi-connection-subscription-preflight-2026-07-27-attempt-03` | invalid/excluded attempt evidence | 74 | 33 | 2,315,210 |
| `.tmp/mcp-multi-connection-subscription-preflight-2026-07-27-attempt-04` | invalid/excluded attempt evidence | 74 | 33 | 2,328,170 |
| `.tmp/mcp-multi-connection-subscription-preflight-2026-07-27-attempt-05` | invalid/excluded attempt evidence | 73 | 33 | 2,683,653 |
| `.tmp/mcp-creator-close-calibration-20260727-01` | invalid/excluded attempt evidence | 73 | 33 | 2,683,643 |
| `.tmp/mcp-creator-close-calibration-workspace-20260727-01` | invalid/excluded attempt evidence | 0 | 0 | 0 |
| `.tmp/inflight-full-suite-20260727` | unresolved process artifact | 3 | 0 | 31,851 |

There are no unexpected or missing `.tmp` top-level roots in this observation.
All thirty-five exact targets remain retained.

The two short idle-preflight roots are associated with the idle-unload
evidence class but are not named literally in the normalized evidence records.
That weaker binding is preserved instead of being upgraded to direct-path
evidence.

The seventh root is the user-restored Kimi research ZIP preservation copy. Its
report and chart member hashes match the earlier bounded intake, but the ZIP
container hash differs. It remains protected cleanup debt until durable
retention or intentional disposal is separately reviewed.

The six additional roots retain the bounded app-server schema/preflight,
raw-item pilots, and three native formal TDD attempts. They are now
bound to their protocol or normalized attempt records; the schema/preflight
root remains evidence-class-only because its exact basename is not recorded in
those normalized records. Inventorying them does not make the invalid attempts
valid and does not authorize deletion. The filename-only scan observes 15
potentially sensitive filenames under the schema/preflight root; their
contents were not inspected and absence of sensitive data is not claimed.

Four later process-fidelity entries retain the generated app-server dynamic
tool schema, the measurement-ambiguous v1 calibration root, the v2
source-backed zero-dispatch carrier root, and its standalone summary report.
The v1 root is directly path-bound; the other three retain evidence-class-only
bindings. Their inclusion preserves cleanup debt and does not turn schema
inspection, an invalid v1 measurement, or zero dispatch into live v2 evidence.

Four subsequent entries retain the first measurement-invalid v2 source-backed
smoke and its report plus the corrected zero-dispatch carrier root and report.
The live smoke pair is directly path-bound to the normalized protocol
calibration record; the corrected zero-dispatch pair remains
evidence-class-only. Inventorying either pair does not create a valid v2 arm.

The final two entries retain the valid replacement source-backed smoke root and
its report. Both are directly path-bound to the normalized smoke evidence.
They preserve one absolute-task-valid transport repetition, not a completed arm or topology
comparison, and remain cleanup debt pending final-program review.

Four newer entries retain the excluded one-second MCP thread-unsubscribe
calibration root and the three formal paired host roots. They are
evidence-class-only because the normalized record binds the repository audit
files and host-root class rather than each exact `.tmp` basename. These roots
contain retained app-server runtime state; inventorying their names, counts,
and sizes neither inspects that state nor proves safe deletion. They remain
cleanup debt under the final-program exact-target gate.

Five subsequent entries retain excluded multi-connection subscription-preflight
calibration host state from protocol correction, failed resume calibration,
and auto-attach calibration. They are evidence-class-only: the normalized
record binds their evidence class and the separate formal audit runs, not
these exact `.tmp` basenames. Keeping them in this inventory neither promotes
them into formal evidence nor proves safe deletion. They remain cleanup debt
under the final-program exact-target gate.

The final two entries retain the invalid pre-window MCP
creator-connection-close calibration host state and its empty isolated
workspace. Both are directly path-bound to the normalized invalid-attempt
record. The host-state root contains retained app-server runtime state;
inventorying it does not validate the aborted calibration, inspect its
contents, or prove safe deletion. Both roots remain cleanup debt under the
final-program exact-target gate.

The final entry retains the failed full-suite verification log created while
the cleanup-debt inventory was already enforcing an exact-root set. The test
run itself completed with 1,667 tests but was invalidated by the newly
unexpected root before unrelated mutation assertions could be evaluated. The
log is retained as an unresolved process artifact rather than silently deleted;
its presence does not count as product evidence or a valid full-suite result.

## Protected external workspace

`C:/Projects/agent-skills-curated` exists and remains explicitly protected
through the stability-observation period. It is outside this repository-local
`.tmp` inventory, its contents were not scanned, and its files/directories/bytes
are not included in the aggregates above. No archive, move, or deletion is
authorized.

## Authority and claim boundary

- No retained runtime content was inspected.
- A filename-only scan does not prove that secrets, private data, credentials,
  session data, or other sensitive content are absent.
- These roots are cleanup debt rather than product payloads, but neither safe
  deletion nor recoverability has been proved.
- No deletion, archive, migration, commit, push, or broad recursive cleanup is
  authorized by this preview.
- This inventory covers only the named repository-local `.tmp` roots. It does
  not prove that every temporary artifact, external workspace, branch,
  worktree, backup, or remote-state debt has been inventoried.

The machine-readable record is
[`registry/closeout-cleanup-debt-preview-2026-07-24.json`](../registry/closeout-cleanup-debt-preview-2026-07-24.json).
Reproduce it with:

```powershell
python -B scripts\inventory_closeout_cleanup_debt.py
```

At final program closeout, re-run the inventory, review each exact target and
its normalized evidence, bind ownership, recoverability, and sensitive-data
handling, then request separate exact-target deletion authority. If deletion
is authorized, verify exact target absence and remaining evidence links
afterward. Do not substitute a broad recursive cleanup command for that gate.
