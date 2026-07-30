# CC Switch Lark Seven-Skill Update Event

Date: 2026-07-27

Status: **seven named live updates verified on the current host; residual drift
open**

## Result

The seven CC Switch updates shown as pending were applied through the CC Switch
GUI in two bounded passes of four and three:

- `lark-apps`
- `lark-base`
- `lark-calendar`
- `lark-doc`
- `lark-drive`
- `lark-slides`
- `lark-task`

The pending-update indicator was zero afterward. Each current local `SKILL.md`
entrypoint has the same SHA-256 as the corresponding file returned for
`larksuite/cli` `HEAD` at commit
`7abcaa7f68ac60811f6c4b95e2f9f2a25800c852`. Claude and Codex projections for
all seven still resolve to the same CC Switch SSOT directories.

This is entrypoint equality, not whole-tree equality, loader invocation, or
behavioral-value evidence.

## Authority and backup boundary

The user authorized all seven pending CC Switch updates. No separate
agent-created backup was made. CC Switch's own rollback-backup behavior was
observed, but the Agent did not invoke cloud backup, read account or credential
values, change global configuration, enable or disable Skills, delete data, or
mutate Git or the upstream repository.

## Post-update counts

The layered counts did not collapse into one number:

| Surface | Entries | Resolvable `SKILL.md` | Residual |
| --- | ---: | ---: | ---: |
| CC Switch database enabled for Claude | 251 | not a body count | n/a |
| CC Switch database enabled for Codex | 251 | not a body count | n/a |
| CC Switch physical SSOT | 75 | 75 | 0 |
| `~/.agents/skills` | 73 | 73 | 0 |
| Claude projection | 251 | 75 | 176 |
| Codex top-level projection/container roots | 77 | 75 | 2 containers |

The update therefore did not repair the historical 176 unresolved Claude
entries. Those rows remain a separate stale-row/projection gap.

## Actual drift retained

Two database rows, `lark-apps` and `lark-calendar`, still retain `master`
branch/readme metadata while the source registration is `larksuite/cli@HEAD`
and the repository default is `main`. At the observation point, `main` and
`master` both resolved to the same commit, so the two entrypoints still matched
current `HEAD`; the metadata alias is recorded rather than silently rewritten.

The Composio discovery/update scan still returned HTTP 404 even though the
repository remained reachable. This event does not claim that CC Switch source
discovery is healthy for every source.

## NO-GO boundary

This event does not authorize stale-row repair, source relinking,
deduplication, deletion, cleanup, migration, or portfolio change. It also does
not prove whole-tree equality, cross-device restore equality, loader
invocation, candidate causation, or behavioral value.

The bounded next action is to retain these seven CC-managed entrypoints and
treat stale rows, Composio discovery, whole-tree identity, loader behavior,
cross-device restore, deduplication, and cleanup as separate falsifiable gaps.
