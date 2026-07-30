# Self-Authored Three Live Authority and CC Collision Reconciliation

Date: 2026-07-30
Status: read-only authority proved; ordinary CC Switch actions blocked

## Outcome

The three self-authored Skills are not one CC-managed package set. Current
evidence proves two different carrier families:

- `C:\Projects\codex-user-config\skills`, `~/.agents/skills`, and
  `~/.codex/skills` contain byte-identical current first-party trees;
- `~/.cc-switch/skills` contains smaller divergent snapshots, and Claude's
  three paths are symbolic links to those older CC trees.

`codex-user-config` remains the declared and live-matching source authority.
The CC database rows are local, unattributed entities with no repository
metadata. Their presence and enablement do not transfer first-party source
authority to CC Switch.

This is an ownership collision, not a normal duplicate-name cleanup.

## Live source and projection identity

The source repository is on `main` at
`0c93458d48cb1ebaa6d0d289e3a21f46d2f61f65`, equal to `origin/main`.
Its dirty files are outside the three Skill trees. The installer explicitly
copies the three first-party packages to both `.agents/skills` and
`.codex/skills`; it defines neither a Claude target nor a CC Switch target.

For every logical name, the source, common-root, and Codex-private manifests
are exact:

| Skill | Current tree files | Current bytes | Current tree manifest SHA-256 | Legacy CC/Claude tree manifest SHA-256 |
| --- | ---: | ---: | --- | --- |
| `intent-contract` | 2 | 50,087 | `67d30201ed6ab42f65ae896e55ad3594a5bf97402db9cc1ba980b0b7494a7e1d` | `9d716e595dcfc1b0e6e471dbe72f34d6491ec84387b45de5c422769d28e5224e` |
| `capability-router` | 2 | 32,126 | `193a2e413084aa2d2a7714bbaddfaf076393c7c4c9ce049709129f1afb8bce1a` | `a313d8cb76fe34c63066a404e68495cd6ef16e5031a6335eee3ab4ff1f05a79b` |
| `closure-contract` | 1 | 12,187 | `5a6924e0efe9153307003322b9ee0d5cd3efae40cc0067fe0a1b84cc67d8fd99` | `2933dc8485c495b3afcfc643184c56959c4104d87c3641ab24a5e62aa9fedeea` |

The dependency files matter. Both `intent-contract` and `capability-router`
have reference files, and those reference files diverge across the two carrier
families. A body-only comparison would understate the split.

## Codex exposure is duplicate exposure, not value proof

A fresh no-model Codex app-server `skills/list` call with `forceReload=true`
returned two enabled user-scoped entries for each logical name: one from
`.agents/skills` and one from `.codex/skills`. All six entries point to the
current source-matching trees.

This proves current duplicate discovery on that surface. It does not prove
task-bound invocation, instruction delivery, behavior, incremental value,
superiority, or future-host stability. Claude has only static link evidence in
this reconciliation; fresh Claude loader exposure remains unproved.

## Current CC Switch 3.19.0 collision

The running binary reports `3.19.0`, so the earlier 3.18.0 transaction preview
is no longer execution-current. The official `v3.19.0` tag resolves through tag
object `09ccf3280c779c6cf7023cd2c3fc3faa21af8b73` to commit
`c0ff89b9b208c092d6ef40b155403dcf290e5767`. GitHub reports the annotated tag
as unsigned, and local binary-to-tag cryptographic attribution is not claimed.

The current tag source nevertheless preserves the material file semantics:

- unified uninstall calls `SkillService::uninstall`;
- uninstall iterates every application type, including Claude and Codex,
  without consulting each row's enabled flags before filesystem cleanup;
- Codex resolves to `~/.codex/skills`;
- `remove_from_app` passes an existing target to `remove_path`;
- `remove_path` removes only a symbolic link when the target is a link, but
  recursively deletes a physical directory;
- disabling a host calls the same removal path;
- with the live `symlink` sync method, enabling or syncing first removes an
  existing target and then creates a CC-owned link.

All three current `.codex/skills/{name}` targets are physical directories.
Therefore ordinary CC uninstall, Codex disable, Codex enable, or sync can
delete a newer first-party projection owned by `codex-user-config`.

The CC uninstall backup captures the CC body and metadata. It does not capture
or restore the divergent newer source-owned `.codex` tree that the manager can
delete. Consequently, ordinary uninstall is not made safe by the normal CC
backup.

## Decision boundary

Do not call ordinary CC uninstall, toggle, or sync for these three identities.
Do not update the CC bodies merely to force parity. Cross-host parity is not
automatically required, and copying current Codex-oriented bodies into Claude
would still leave source, adapter, verification, and rollback ownership
unresolved.

The next mutation needs a collision-safe transaction and one explicit host
policy choice:

1. **Quarantine the Claude legacy projection.** Preserve the current
   source-owned `.agents` and `.codex` trees, detach the three older Claude
   links, and retire the CC rows and SSOT copies through a special transaction.
   Claude would temporarily have no projection for these three Skills.
2. **Create a source-owned Claude adapter first.** Define and test a
   first-party Claude projection under an accepted source authority, then retire
   the CC rows and older links through the same collision-safe boundary.

The first route is the smaller subtractive move; it is not authorized merely
because it is preferred. The second route changes the cross-host product and
trust boundary and likewise needs explicit authorization and evidence.

Codex dual-root simplification is a separate gate. Native common-root discovery
is now observed, but changing `codex-user-config/scripts/install.py`, deleting
the `.codex` copies, or changing rollback behavior requires its own source-repo
transaction and fresh-host validation.

## `diagnose` reference boundary

The current authoritative `capability-router` source still names the legacy
`diagnose` identity. The old CC router does too.
`observability-and-instrumentation` separately names canonical `diagnose` and
still contains the previously identified PII logging example, while the
promoted `diagnosing-bugs` package exists.

Any router reference migration belongs in `codex-user-config`, not in the old
CC copy. The observability adaptation has its own governed payload and CC
projection path. Neither mutation is authorized by this reconciliation.

## Version drift consequence for the fourteen-item preview

The earlier fourteen-item subtraction preview remains useful historical
evidence, but its manager semantics were frozen against 3.18.0. Before any
execution authorization can be consumed, its backend, backup rotation,
rollback, expected projections, and sentinels must be refreshed against live 3.19.0.
This record does not authorize that deletion transaction.

## No-action and claim boundary

No Skill body was executed. No model turn was sent. No database, CC row,
projection, link, Skill, config, rule, Hook, Plugin, MCP, App, Trae root,
repository branch, commit, or remote was changed. No temporary source root,
database copy, or recovery archive was created.

This reconciliation proves current authority, tree identity, Codex duplicate
exposure, Claude static divergence, and the current CC source-level collision
risk. It does not prove Claude loading, Skill invocation, instruction delivery,
behavioral value, cross-host superiority, retirement readiness, or program
closeout.
