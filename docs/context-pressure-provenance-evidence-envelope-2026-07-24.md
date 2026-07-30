# CTX-03 pressure-signal provenance evidence envelope (offline)

This dated, local contract closes a narrow interface gap: the CTX-03 advisory
previously classifies supplied booleans, while its future live-observation
schema names host and evidence fields.  The envelope makes those fields a
fail-closed input surface before an observation is offered to the advisory.

It validates records only.  It does not inspect the named host, read a live
counter, open or create a task, invoke a loader, alter MCP state, access an
account, or write a repository artifact.

## Inputs and verdict

For `direct-counter` and `host-event`, a record must bind host identity,
version, profile, allowed source class, numeric value/unit, UTC observation
time, parent run, observed delivery, and a SHA-256-bound evidence artifact.
The caller must separately bind the expected host/version/profile, parent run,
and observation time; a self-consistent envelope cannot bind those targets by
itself.
`heuristic` and `user-observed` records must not masquerade as host telemetry;
they may use an explicitly classified opaque reference instead.

The validator emits `advisory-evidence-ready-offline-only` only for a complete
record.  Otherwise it emits `blocked-missing-host-pressure-evidence` with
machine-readable failure codes.  A valid verdict is still only an admissible
input to the existing CTX-03 advisory; it cannot make a thread, authorize a
host observation, or replace the CTX-04/05 packet and explicit authority gate.

## Counter-fixtures

The focused suite rejects an opaque `host-event` reference, invalid direct
counter unit, missing host binding, non-host provenance dressed as telemetry,
authority promotion, claim promotion, and unknown provenance.
It also rejects target-host and parent-run/time binding mismatches.

## Claim boundary

Every broad outcome remains false: live telemetry, best efficiency threshold,
automatic thread creation, compaction, fresh session, loader invocation,
weak-Agent acceptance, host/MCP/account mutation, and cross-host behavior.
The next evidence step remains a separately authorized, host-specific
observation followed by the existing advisory and handoff gates.
