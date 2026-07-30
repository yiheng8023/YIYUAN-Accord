# Codex Common-Root Doc/PDF Shadow-Disable Exposure Reconciliation

Date: 2026-07-30

Status: **fresh-task contradiction found; isolated official correction passes**

## Result first

The six Skills uninstalled on 2026-07-29 are absent from the new task's
startup Skill list. `doc` and `pdf` are not absent. Both still appear alongside
Codex's runtime-owned `documents` and `pdf` capabilities.

The CC Switch operation did remove `doc` and `pdf` from
`~/.codex/skills`. It did not remove the two links retained under the common
`~/.agents/skills` root. Codex officially discovers that common root, and the
startup list resolves both links to their CC Switch targets. Therefore:

```text
CC-managed Codex projection disabled
!=
Codex host exposure disabled
```

The completed CC toggle remains valid filesystem and database evidence. It is
not host-exposure evidence.

## Isolated no-model preflight

Exact current `doc` and `pdf` bodies were copied into a disposable project
`.agents/skills` root. Two native app-server arms ran against an isolated
`CODEX_HOME` on Codex Desktop 0.146.0:

- control: both exact paths were discovered and enabled;
- treatment: the same two identity paths remained listed with
  `enabled=false` after exact `skills.config` overrides.

No thread, turn, model request, global config write, CC Switch action, or
foreign-root action occurred. Source and projected `SKILL.md` hashes matched,
both app-server processes produced zero stderr lines, and the temporary
projection and isolated home were removed afterward.

This proves the official path-disable mechanism in isolation. It does not
prove that the live global transaction or restart has occurred.

## Option judgment

Deleting the two common-root links is not the preferred correction. It would
remove a shared compatibility projection for every present or future Agent in
order to express one host's policy.

Leaving the current state is also rejected: it preserves duplicate Codex
exposure and makes the CC Codex toggle semantically ineffective at the
host-exposure layer.

The preferred correction is two exact Codex host-adapter entries:

```toml
[[skills.config]]
path = "C:/Users/15521/.agents/skills/doc/SKILL.md"
enabled = false

[[skills.config]]
path = "C:/Users/15521/.agents/skills/pdf/SKILL.md"
enabled = false
```

This uses the official host mechanism while retaining the common root,
CC Switch entity store, and Claude projection.

## Remaining authorization gate

The live transaction requires new authorization because it would mutate the
global Codex config, restart Codex Desktop, and later remove the exact verified
rollback backup. The transaction does not require CC Switch, common-root,
Claude, Trae, model, commit, or push mutation.

Until that authorization is supplied, `doc`/`pdf` must be reported as
filesystem-shadow-disabled but still exposed to Codex through the common root.
