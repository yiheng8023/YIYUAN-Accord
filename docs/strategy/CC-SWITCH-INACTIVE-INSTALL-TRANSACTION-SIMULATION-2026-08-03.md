# CC Switch Inactive Install Transaction Simulation

## Decision

Keep the reviewed 17-candidate cohort inactive. Prefer an upstream CC Switch
inactive-install mode; do not use install-then-disable, direct database writes,
manual SSOT staging, a parallel manager, or a live thin adapter.

The installed manager remains CC Switch `3.19.1`. A fresh official Git check
found no later release. Current upstream `main` at
`eb356e15bd898a434fde7ca74e5e3a2aec6c90e4` still requires a current app and
constructs `SkillApps::only(current_app)` in the repository install path.
Current `main` is unreleased observation evidence, not runtime authority.

## What ran

`scripts/simulate_cc_switch_inactive_install_transaction.py` exercised one
synthetic, inert, dependency-closed two-Skill cohort in disposable homes. It
made zero model, network, candidate, manager, database, real SSOT, or consumer
calls.

Fifteen cases passed:

- one exact two-candidate inactive install;
- rejection of a non-empty app set, digest drift, missing entrypoint, missing
  dependency, duplicate directory, existing manager row, existing SSOT path,
  second-source drift before writes, and failure during the second staging
  copy without process residue;
- ordinary rollback after preparation, first SSOT move, and database replace;
- fresh recovery after simulated process loss following the first SSOT move
  and database replace.

Every failure restored the exact simulated pre-state. The successful row set
kept every app false. Codex and Claude consumer roots remained unchanged.

## Required upstream semantics

An eligible implementation must:

1. accept an explicit empty initial app set;
2. obtain and verify the dependency-complete cohort before any manager write;
3. reject identity, path, existing-state, and digest conflicts before mutation;
4. journal the transaction before same-volume SSOT moves;
5. write all manager rows disabled and skip consumer projection;
6. roll back ordinary failures and recover process-loss windows; and
7. treat an existing same-source row as a separate update decision, never an
   implicit enablement.

## Claim boundary

This proves that the required transaction semantics are internally coherent in
a repository-owned disposable simulator. It does not prove that CC Switch
implements them, that its Rust code builds, that its real database and backup
paths recover, or that any candidate is installed, exposed, invoked, useful,
or portable.

The governed record is
`registry/cc-switch-inactive-install-transaction-simulation-2026-08-03.json`.
The next boundary is third-party source/build and external-contribution
authority for an upstream implementation proposal and Rust-side failure tests.
