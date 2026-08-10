# Task 4 Report — Govern Acceptance Authority Migration References

## Scope

This task adds only a tracked-text occurrence inventory and its focused
validator. It does not modify the frozen v1 authority, program plan, packet
fixtures, selector state, assessment state, external systems, or consumer
configuration.

## TDD evidence

- Interface preflight: the named discovery test initially failed only because
  the inventory module did not exist; this was not counted as RED.
- Discovery RED:
  `python -B -m unittest tests.test_program_acceptance_migration_inventory.ProgramAcceptanceMigrationInventoryTests.test_discovery_finds_live_tracked_occurrences_with_symbolic_pattern_ids -v`
  failed on `AssertionError: [] is not true` after the temporary empty stub.
- Discovery GREEN: the same command passed after the minimal Git tracked
  UTF-8, one-literal-occurrence discovery implementation.
- Exact-set RED: the named exact-set test failed by its equality assertion
  with 203 discovered rows versus the temporary empty projection, not by an
  import, key, or application error.
- The initial strict raw-literal rejection exposed the approved-contract
  conflict for the legacy map's own host locator. After the recorded human
  option-1 ruling, the inventory test suite passed with the precise host-path
  exception and direct mutation coverage.

## Reviewed inventory

The final settled Task 4 tracked tree has 205 occurrences across 110 files.
The reviewed classifications are 166 immutable historical (A), 11 current
authority consumers (B), zero physical explicit-input reusable-validator
occurrences (C), and 28 migration-governance/regression occurrences (D).
Class C path ownership is directly covered with a synthesized adversarial row;
`scripts/harness_decision_packet.py` retains mixed B/A occurrence semantics.

The record contains symbolic pattern IDs and action text. The sole decoded raw
legacy-path value is the exact host locator for its own tracked occurrence. A
dedicated deterministic inventory wire serializer (not the repository's
ordinary `canonical_file_bytes`) encodes only that `path` value's slash as
`\/`; it does not escape unrelated fields. A checked replay rebuilds the
physical record byte-for-byte from its parsed document. The raw legacy ID
remains forbidden everywhere. Direct tests reject moving the permitted path
value into governance, actions, or a non-path identity field, and reject a
wrong identity host path.

## Verification

Fresh focused evidence:

```powershell
python -B -m unittest tests.test_program_acceptance_authority_v2 tests.test_program_acceptance_migration_inventory -v
# Ran 48 tests ... OK

python -B -c "from pathlib import Path; from scripts.program_acceptance_migration_inventory import load_migration_inventory, validate_migration_inventory; p=load_migration_inventory(Path('.')); validate_migration_inventory(Path('.'), p); print(len(p['occurrences']))"
# 205
```

The four frozen v1 locks were revalidated with `validate_legacy_locks`; the
physical inventory raw-literal scan passed; final `git diff --check` is
recorded with the Task 4 commit.

## Commit and residual boundary

Commit message: `feat: govern acceptance authority migration references`.

This is exact local inventory and validation evidence only. It does not prove
or authorize a live migration, selector activation, behavior, value,
cross-host portability, production readiness, release eligibility, or overall
Harness completion.
