# Skill ablation host transaction revalidation

Date: 2026-07-24
Status: blocked by config baseline drift; re-intake required
Machine record:
[`../registry/skill-ablation-host-transaction-revalidation-2026-07-24.json`](../registry/skill-ablation-host-transaction-revalidation-2026-07-24.json)
Reproducer:
`python -B scripts/revalidate_skill_ablation_host_transaction.py`

## Result first

The prepared 2026-07-19 global Codex Skill-configuration transaction is stale
and must not execute. The current config remains 9,723 bytes and still contains
zero entries in the semantic TOML `skills.config` array, but its SHA-256 changed
from the prepared
baseline `147635b...` to `baafd17...`. Matching length and entry count cannot
cancel a full-byte digest mismatch.

All six bound `intent-contract`, `capability-router`, and `closure-contract`
target files still exist and match their prepared SHA-256 values. The one exact
prepared backup path is absent. These facts narrow the drift to the config
precondition; they do not authorize replacing the old baseline with the new
digest.

The next state is therefore
`blocked-baseline-drift-reintake-required`, not transaction-ready.

## Read-only and content boundary

The revalidator binds the full prepared-contract file digest, then uses
`stat -> read/hash/count -> stat` for the config and each target. A size or
mtime change across either read marks that observation unstable. It records
only paths already present in the prepared private transaction, timestamps,
lengths, SHA-256 values, the semantic TOML entry count, comparison booleans,
and failure codes.

The production CLI has no alternate-contract argument: it resolves the one
repository-owned prepared contract relative to the script location. The public
validator rereads those canonical bytes and rejects a caller-supplied contract
that is merely self-consistent or reuses the same transaction ID.

Those per-file checks and the backup-path before/after check are not an atomic
multi-file snapshot. The report digest protects the recorded JSON from an
unnoticed edit; it is not a signature or live-state attestation. Any later
authorized mutation must revalidate the complete config, Skill-target, and
backup precondition cohort inside its own mutation critical section.

It does not emit config values, Skill bodies, tokens, endpoints, environment
variables, or backup content. It does not create or read the backup, write the
config, disable a Skill, restart Codex, create a task, invoke a loader or model,
or delete anything.

The exact prepared backup locator being absent does not prove that no other
historical backup exists. Config hash equality in a future run would prove only
byte equality with the prepared baseline, not semantic safety, restart state,
Skill exposure, loader invocation, actual model/reasoning, or weak-Agent
acceptance.

## Next gate

Before any host-wide transaction can be reconsidered, re-intake must explain
or accept the current config baseline without exposing its contents, rebuild
the exact reversible transaction from that accepted baseline, and obtain
separate authorization for config backup/mutation/restoration, two application
restarts, formal fresh-task trials, and deletion of only the verified
transaction backup. CC Switch mutation, installation, projection changes,
commit, and push remain outside that authority.
