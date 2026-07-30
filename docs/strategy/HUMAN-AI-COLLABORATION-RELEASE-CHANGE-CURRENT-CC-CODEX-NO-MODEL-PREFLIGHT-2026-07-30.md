# Release/Change Current CC And Codex No-Model Preflight

Date: 2026-07-30
Scenario: `SE-RELEASE-CHANGE-01`
Status: current CC identity proved; current task inventory listed; independent
fresh Desktop exposure remains blocked

## Result

The two approved release/change candidates did not drift:

- `ci-cd-and-automation` is still the exact 11,470-byte release payload at
  SHA-256
  `7aa008e4be26068c9e61ea8a9303711020e376c6cbfdf10d581a9fd400acf8ea`;
- `shipping-and-launch` is still the exact 11,464-byte release payload at
  SHA-256
  `195a1fad5612627464df4581954727b8ebd649b0ce4bfe91e06655bcc32302b0`.

Both have exact physical CC Switch true-source trees, enabled CC database rows,
and resolvable common-root, Claude, and Codex symlinks. The current task's
runtime-provided Skill inventory lists both from their CC true-source paths.
This advances current listing and projection evidence, not invocation,
instruction-delivery, behavior, or value evidence.

The whole-state CC subtraction preflight did fail, but the failure is unrelated
to these candidates. It is exactly the rehydration of the Codex `doc` and `pdf`
database flags and private projections.

## Exact drift attribution

The failure loop was:

```text
capture current safe CC/host projection
-> compare to frozen whole-state fingerprint
-> fail only database, projections, and whole-state
-> deep-copy the observation in memory
-> set only doc/pdf enabled_codex from 1 to 0
-> remove only the two Codex-private doc/pdf links
-> recompute all three fingerprints
-> exact frozen match
```

Manager binary, settings, all 55 CC trees, all 20 backups, and the two exact
Codex disable-policy rows still match the frozen evidence. The read-only
counterfactual reproduces the old database, projection, and whole-state
fingerprints exactly. No live row, link, config, or Skill was changed.

Ranked diagnosis:

1. a later CC Switch refresh or synchronization rehydrated the two host-specific
   rows and links — supported exactly;
2. the release candidate cohort drifted — falsified;
3. manager, settings, backup, CC-tree, or Codex policy drift caused the failure
   — falsified;
4. a new independent Desktop app-server can reproduce current task inventory
   exposure — not proved.

The frozen baseline must not be refreshed from the current state. Doing so
would erase a real host/manager lifecycle contradiction.

## Host-carrier boundary

`where codex` exposed both the npm CLI carrier and the Desktop-bundled carrier.
They cannot be treated as interchangeable merely because both report version
0.146.0.

Two short-lived npm CLI app-server `skills/list` arms, with Plugin features
disabled and enabled, each returned six system Skills, zero user Skills, and
zero release-candidate rows. Both exited cleanly with zero stderr and an
unchanged global config hash. This is a different-carrier observation, not a
candidate failure.

The running Desktop process uses the exact WindowsApps-bundled binary. Direct
fresh app-server launch was attempted both inside the sandbox and with approved
escalation; Windows package ACLs rejected `CreateProcess` with WinError 5.
No binary was copied, no ACL was changed, and no alternative executable was
silently substituted.

Therefore:

```text
current task inventory listing
+ exact CC source and projection identity
!= independently replayed fresh Desktop exposure
!= loader invocation
!= instructions reaching a model
```

## `doc` / `pdf` lifecycle consequence

The prior Codex-only correction intentionally retained the shared CC and common
carriers while removing Codex-private links and adding exact disabled
`skills.config` rows. The links and CC database flags have now reappeared while
the disable-policy rows remain exact.

The current task inventory omits the shared `doc` and `pdf` variants and keeps
the runtime-owned document and PDF capabilities, but a fresh independent
Desktop force-reload was not reproducible in this phase. Effective suppression
after rehydration therefore remains unproved by a fresh independent probe.

This is a lifecycle-reconciliation gap, not authority to delete a source,
rewrite CC rows, refresh the frozen baseline, or weaken the host policy.

## Authority, cleanup, and next gate

No model request, candidate invocation, dependency installation, Skill
installation/update/enable/disable/delete, CC Switch mutation, host projection
mutation, global config mutation, cleanup, commit, or push occurred during the
probe. No temporary root or raw config/database capture was created.

The release/change live comparison remains blocked until a real release
fixture, accountable authority, short-lived dispatch authority, and
independently reproducible Desktop task-scoped exposure are all bound.

The separate `doc`/`pdf` lifecycle path must explain the manager rehydration and
verify effective host suppression before any corrective mutation. Current
evidence supports no candidate value, release readiness, residual self-authored
gap, or portfolio change.
