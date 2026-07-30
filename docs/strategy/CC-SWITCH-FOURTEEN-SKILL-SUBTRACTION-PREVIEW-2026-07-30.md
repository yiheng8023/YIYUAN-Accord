# CC Switch Fourteen-Skill Subtraction Preview

Date: 2026-07-30

Status: **read-only manager preview; exact mutation authorization pending**

## Result first

Fourteen of the fifteen strong subtraction candidates are now bound to exact
live database rows, bodies, projections, host exposure, backend commands,
backup rotation, rollback, and cleanup. `diagnose` is excluded because two
retained bodies still name its legacy identity.

All fourteen are currently enabled in both Claude and Codex, appear enabled in
a fresh no-model Codex `skills/list`, and have CC Switch, common-root, Claude,
and Codex links. Their payload is 19 files and 58,356 bytes. None carries CC
source metadata.

The proposed canary is `edit-article`: it is one file, was previously rejected,
is personal rather than promoted upstream, and has no observed dependency from
a retained Skill body.

## Manager and rollback semantics

The exact CC Switch 3.18.0 tag source confirms:

- `uninstall_skill_unified` calls `SkillService::uninstall`;
- an exact body plus metadata backup is created before application projections,
  SSOT, or database state are removed;
- `restore_skill_backup` restores the entity and enables exactly one requested
  host, not every prior host;
- a dual-host rollback must restore to one host and then call
  `toggle_skill_app` for the second host;
- CC Switch does not manage the separate `~/.agents/skills` compatibility
  links.

Therefore, compatibility links are not removed until the complete 14-item
manager batch has succeeded. If a manager operation fails before then, reverse
restore makes those still-present links resolve again. Direct SQLite writes
are neither needed nor allowed.

## Backup rotation is part of the decision

CC Switch currently holds its maximum 20 Skill backups. Its source enforces a
20-directory retention policy by modified time. Fourteen successful uninstalls
would create fourteen new backups and, absent concurrent backup creation,
automatically evict the fourteen oldest remaining Lark-removal backups. The six
2026-07-29 subtraction backups would remain.

This rotation is a predictable manager side effect, but it is still deletion
of recovery data and is included explicitly in the authorization request.

Before the canary, a separate secret-screened recovery archive would bind the
14 bodies, 19 files, tree manifests, and database row metadata while excluding
the raw database, settings, credentials, accounts, and sessions. It would be
removed only after the live state, manager backups, and configured remote
snapshot are verified.

## Dependency boundary

The ready cohort is:

`design-an-interface`, `edit-article`, `qa`, `request-refactor-plan`,
`review`, `setup-pre-commit`, `setup-project-skills`, `to-issues`, `to-prd`,
`ubiquitous-language`, `writing-beats`, `writing-fragments`, `writing-shape`,
and `zoom-out`.

The promoted `setup-matt-pocock-skills` text mentions deprecated `qa`, although
`qa` is omitted from the promoted manifest. This is recorded as an upstream
consistency warning, not a hard execution dependency and not permission to
edit the exact source package.

`diagnose` stays installed. `capability-router` and
`observability-and-instrumentation` must first be moved from the legacy name to
a neutral diagnosis capability or the current promoted identity.

## Expected verified state

After a successful canary, remaining batch, and exact compatibility-link
cleanup:

- database and CC/Claude entity counts: 41;
- Codex-enabled CC rows: 39, because shared `doc` and `pdf` remain disabled;
- common-root links: 27;
- zero broken links;
- Matt promoted rows: 22;
- self-authored controls: 3;
- `diagnose`: retained.

The transaction would also verify unchanged doc/pdf policy, Matt raw-blob
identity, self-authored controls, and Trae foreign-root sentinels, then close
the temporary debug surface and run focused plus top-level verification.

## Authorization boundary

No uninstall, restore, remote sync, compatibility-link cleanup, config, Hook,
rules, model, commit, or push action occurred during this preview.

One bounded authorization would cover exactly: the fourteen named manager
uninstalls, expected eviction of the fourteen oldest Lark backups, exact
cleanup of the fourteen resulting broken common-root links after full success,
one configured remote snapshot, and exact cleanup of the recovery/CDP process
artifacts. Everything else remains out of scope.
