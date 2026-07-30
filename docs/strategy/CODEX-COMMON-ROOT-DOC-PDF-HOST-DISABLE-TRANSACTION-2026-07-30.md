# Codex Common-Root Doc/PDF Host-Disable Transaction

Date: 2026-07-30

Status: **applied; live no-model exposure verified; process artifacts clean**

## Result first

The authorized Codex-only correction succeeded. The shared CC Switch `doc`
and `pdf` entities remain present, as do their common-root and Claude links.
Codex's private `~/.codex/skills` projections remain absent.

Two exact `skills.config` entries now disable only the common-root paths for
Codex. After a real Desktop restart, fresh app-server processes resolve the
two links to the CC Switch true source and report both as `enabled=false`.
With Plugin and runtime features enabled, Codex's runtime-owned
`documents:documents` and `pdf:pdf` Skills remain `enabled=true`.

This closes the host-exposure contradiction found by the predecessor record:

```text
shared entity retained
+ common compatibility carrier retained
+ Codex exact-path exclusion
= no duplicate Codex selection exposure
```

## Transaction integrity

The live config still had the expected preflight hash and zero
`skills.config` entries immediately before mutation. The write enforced that
old hash as a concurrency precondition, wrote a same-directory temporary file,
and used `System.IO.File.Replace` to atomically install the new config while
creating an exact-byte rollback backup.

The resulting TOML parsed successfully and contained exactly the two authorized
rows. The backup hash equals the preflight config hash. After restart, Codex
updated its volatile computer-use pipe address and bundled-marketplace
timestamp; the intended Skill rows remained intact.

## No-model live verification

Both verification arms used `skills/list` with `forceReload=true` in fresh
Codex Desktop 0.146.0 app-server processes:

- Plugin features disabled: 64 rows, zero stderr, shared `doc=false` and
  `pdf=false`.
- Plugin features enabled: 76 rows, shared `doc=false` and `pdf=false`,
  runtime `documents:documents=true` and `pdf:pdf=true`.

No thread, turn, model request, CC Switch operation, common-root edit, Claude
edit, Trae edit, commit, or push occurred. The live config hash was stable
across each probe.

The disabled rows remaining in `skills/list` are useful: they prove the
entities are still discoverable and policy-disabled rather than missing due to
deletion or a broken link. The current task's startup Skill surface omits the
disabled shared variants while retaining the runtime-owned alternatives.

## Cleanup and claim boundary

The atomic-write temporary file and detached restart helper are absent. After
the new repository evidence passed its validator and top-level verifier, the
single exact rollback backup was hash-checked and removed by exact path. The
dedicated tests, top-level verifier, and cleanup inventory passed again against
the final evidence state.

This transaction proves post-restart Codex exposure state and carrier
preservation. It does not prove Skill invocation, behavior, incremental value,
cross-host behavioral equivalence, remaining-portfolio quality, or program
closeout.
