# Native Weak-Agent TDD Formal Attempt Batch

Date: 2026-07-26
Status: native attempt cap reached; zero valid repetitions; comparative
inference blocked

## Result

Three fresh `gpt-5.3-codex-spark/low` native attempts ran against the same
fixture, oracle, seven mutants, control plane, and hard gates. None counts as a
valid formal repetition.

- r1 had an observable timeline and a valid RED, but no focused GREEN after
  the production mutation. Its tests killed five of seven mutants.
- r2 wrote both the test and production implementation through opaque
  `Set-Content` commands. No independent `fileChange` lifecycle certified
  their order, so measurement failed closed. Its tests again killed five of
  seven mutants.
- r3 passed the visible suite, hidden oracle, and all seven mutants, but did
  not preserve an accepted RED-to-production-to-GREEN timeline.

The batch therefore demonstrates why final behavior, independent test quality,
and process conformance are separate hard gates. Final green did not erase
process loss.

## Stop Decision

The three complete failure signatures are heterogeneous, so this is not a
claim that one identical failure repeated three times. The arm stops because
the preregistered native attempt cap was reached. Invalid attempts are not
replaced until three passes appear.

There is no valid native comparison baseline. Matt and Superpowers must not now
be run as formal comparative treatment arms. A separately preregistered,
non-scored and non-comparative diagnostic may still ask whether one exact
treatment projection can produce an observable and absolutely feasible trace.
Even a passing diagnostic would not establish relative improvement, delivery,
causation, preference, general superiority, or production readiness.

## Measurement Contract Revision

All retained raw traces were reanalyzed with
`codex-app-server-tdd-normalizer-v2`. Version 2 accepts
`turn/plan/updated` only when its payload matches the observed plan-only schema,
continues to fail closed on schema drift, and no longer treats PowerShell
`2>$null` as a file write. Real `Set-Content` and file redirection remain
write-capable.

Raw traces and reanalysis reports remain under `.tmp` as retained cleanup debt.
They are not vendored evidence, and this record does not authorize deletion.

Machine record:
`registry/human-ai-collaboration-tdd-native-formal-attempt-batch-2026-07-26.json`.
