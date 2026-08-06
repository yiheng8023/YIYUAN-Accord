# Codex consumer Skill mapping snapshot

## Scope

This dated snapshot refreshes only the physical Skill roots, CC Switch `skills`
table identity, source-revision metadata, and four materialized tree identities
observed for the local Codex consumer. The database was opened with SQLite URI
read-only mode. Only non-secret Skill identity, source, projection, hash, and
timestamp columns were queried. Provider, account, prompt, settings, request-log,
and credential-bearing content was not retained in this evidence.

The shared `C:/Users/15521/.agents/skills` root contained 44 entries: 40 CC
Switch symlinks and four materialized directories. Every entry matched one
`enabled_codex=1` row. Twenty-four symlinks bind exact
`mattpocock/skills@v1.2.2` source metadata; sixteen symlinks and four
materialized directories retain local row identities. This supersedes the old
July count and zero-source-backed observation as current physical evidence; it
does not rewrite the historical record.

The Codex-specific root contained 43 matching user-projection names plus two
runtime-owned directories. `doc` was present only in the common root. The three
materialized control-contract trees exactly matched consumer repository HEAD
`fff0041bf074996b63a4f178741ccbc1bf0d6657`; the dirty `.tmp/` path was
excluded. `kimi-webbridge` exactly matched the CC Switch stored tree. All four
materialized tree digests matched between the common and Codex-specific roots.
These are tree identities, not source-ownership admission or loader-precedence
proof.

## Evidence and authority boundary

This snapshot proves dated physical mapping, database-row reconciliation, one
exact source revision for 24 rows, and four materialized tree identities. A DB
enablement flag or directory presence does not prove instruction discovery,
loader precedence, live enablement, invocation, instruction delivery, behavior,
backup/restore, cross-device parity, value, or production readiness.

No CC Switch, Skill body, projection, consumer repository, Agent configuration,
source registration, installation, enablement, backup, restore, deletion, or
release mutation was authorized or performed. The three supported acceptance
criteria therefore remain `partial`.
