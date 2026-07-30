# Repository-local temporary cleanup execution — 2026-07-30

This record closes the repository-local process-artifact debt represented by
the 2026-07-27 frozen preview. It is a stage checkpoint, not program closeout.

## Exact result

- The transaction was limited to the thirty-five exact `.tmp` targets in the
  frozen preview: 2,459 files, 811 nested directories, and 60,346,279 bytes.
- No unexpected path was included.
- The repository-local `.tmp` root is absent after cleanup.
- `C:/Projects/agent-skills-curated`, CC Switch, global configuration, and
  consumer Skill roots were outside this transaction and were not modified.

Commit screening then found eight additional process-only directories nested
under the multi-connection audit: four complete `codex-home` trees and four
empty runtime workspaces. They contained 292 files, 124 nested directories,
9,058,784 bytes, SQLite/WAL state, temporary locks, and copied runtime Skills.
The eight exact directories were removed. The audit README, one calibration
log, and three compact `report.json` files remain and are the only retained
payloads from that audit cohort.

## Durable evidence retained

The user-supplied research ZIP already had an exact repository-custody copy at
`sources/user-supplied-human-ai-sdlc-research/hmc_report.agent.final.restored-2026-07-26.zip`.
Its 549,186-byte payload and SHA-256
`C59510DB88911D920228803ACE53A2A97D77B9DF7E0EBF79D067BEFC4D02A3BD`
match the deleted temporary duplicate.

The only verifier that still required raw temporary state was the invalid MCP
creator-connection-close calibration. Before cleanup, its five Sentinel events
and isolated configuration semantics were normalized into
`audits/mcp-thread-creator-connection-close-calibration-attempt-2026-07-27/normalized-evidence.json`.
That compact record preserves original byte counts and hashes but excludes raw
runtime state, machine-absolute paths, and secret material.

All other `.tmp` references in evidence records remain historical locator
metadata or optional retained-artifact checks. The repository validators use
their normalized documents and audit payloads, not the removed runtime trees.

## Claim boundary

This cleanup does not prove program closeout, product readiness, sensitive-data
absence inside every deleted runtime database, or byte-for-byte reconstruction
of every historical experiment. It proves only that the exact governed
repository-local temporary targets were removed after the necessary durable
evidence and the user-supplied source had been preserved. It also proves that
the eight exact audit-runtime debris directories found during commit screening
were removed without deleting their five compact audit artifacts.
