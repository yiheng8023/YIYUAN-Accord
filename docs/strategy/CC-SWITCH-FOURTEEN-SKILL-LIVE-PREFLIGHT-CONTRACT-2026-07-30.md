# CC Switch fourteen-Skill live preflight contract

Date: 2026-07-30
Status: read-only, fail-closed preflight ready; no mutation authorized

## Outcome

The fourteen-item subtraction preview now has a repeatable live preflight
instead of relying on a human comparison with the earlier snapshot. The
preflight reads the current user-state surfaces, computes deterministic
fingerprints, applies target-specific semantic checks, and fails closed on any
drift. It invokes no CC Switch command and writes no recovery archive, remote
snapshot, host projection, database row, configuration, or repository state.

## Whole-state drift gate

The frozen identity covers:

- the exact 32,584,192-byte CC Switch executable and its SHA-256;
- the two selected Skill settings and absence of a Skill path override;
- the safe Skill columns for all 55 database rows, excluding the raw database;
- all 55 physical CC Skill trees;
- every top-level entry and resolvable tree identity in `.cc-switch`,
  `.agents`, `.claude`, and `.codex` Skill roots;
- all 20 existing manager backups, including modified-time eviction order and
  complete tree identities; and
- only the two Codex Skill-configuration rows that disable shared `doc` and
  `pdf`, without projecting unrelated configuration data.

The whole-state fingerprint is not a transaction lock. CC Switch or another
actor can still change state after a successful check. Therefore the preflight
must run again immediately before the canary, and execution must stop if any
component or semantic check fails.

Tree manifests order normalized relative paths case-insensitively, with the
original path as a deterministic tie-breaker. This makes the earlier
Windows/PowerShell ordering assumption explicit; the first live run correctly
rejected the ambiguous definition on the only multi-file target before the
definition was repaired.

## Semantic checks

The checker independently verifies all fourteen target database rows, host
flags, content hashes, CC trees, and three symbolic-link projections. It also
checks the exact 14-oldest-plus-6-retained backup order.

Protected sentinels are not inferred from the absence of target drift:

- the current `.agents` and `.codex` trees for `intent-contract`,
  `capability-router`, and `closure-contract` must remain physical and match
  the current first-party tree identities;
- the exact Matt promoted 22-row set must remain present, source-attributed,
  enabled for Claude and Codex, and backed by a CC tree;
- shared `doc` and `pdf` carriers must remain physical in CC, linked through
  `.agents` and `.claude`, absent from private `.codex` top-level projections,
  and explicitly disabled in Codex configuration; and
- `diagnose` and the three first-party identities must remain outside the
  fourteen-item cohort.

## Command and claim boundary

The governed live command is:

```powershell
python -B scripts\preflight_cc_switch_fourteen_skill_subtraction.py
```

A pass proves only that the recorded point-in-time live state still matches
the governed preconditions. It does not authorize uninstall, prove an atomic
manager transaction, create rollback evidence, request a remote snapshot, or
prove the post-state.
