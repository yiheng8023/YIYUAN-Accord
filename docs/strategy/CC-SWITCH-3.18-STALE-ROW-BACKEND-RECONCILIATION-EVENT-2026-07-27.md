# CC Switch 3.18 stale-row backend reconciliation event

Status: current-host backend reconciliation verified; portfolio review remains open.

The earlier 251-row display was real database state, not 251 usable Skill
bodies. Read-only preflight found 75 physical CC Switch SSOT bodies and 176
unowned `local:*` rows whose SSOT directories no longer existed. Those rows
also produced 176 broken Claude projections.

The repair used the running CC Switch 3.18 application backend. The application
was temporarily restarted with a localhost-only WebView2 debugging endpoint,
and its existing Tauri `uninstall_skill_unified` command was invoked directly.
No Computer Use action and no raw SQLite mutation performed the repair. One
canary (`local:coderabbit-review`) was verified before the remaining 175 calls.
All 176 backend calls succeeded.

Post-verification observed:

- 75 database rows and 75 physical SSOT bodies;
- zero database rows with missing bodies;
- 75 Claude projection entries and zero broken symlinks;
- 77 Codex top-level entries, including its native container roots, and zero
  broken symlinks;
- the existing `handoff` body retained tree hash
  `d3fa95374feefb3e51f25d06dddd984778425f78663a650d52399406ad40b042`;
- CC Switch returned to ordinary startup and the temporary debugging endpoint
  was closed;
- CC Switch WebDAV status recorded equal local and remote manifest hashes after
  the backend mutation.

This event supersedes later-live-count use of the earlier 251/75/176 snapshots.
Those files remain valid point-in-time evidence and are not rewritten.

The result does not prove loader invocation, behavioral value, cross-device
restore equality, quality of all 75 remaining bodies, deduplication, retirement,
or a final portfolio. The next bounded action is a fresh 75-body portfolio
rebaseline followed by source, overlap, weak-Agent value, and residual-gap
review.

Machine evidence:
`registry/cc-switch-3.18-stale-row-backend-reconciliation-event-2026-07-27.json`.
