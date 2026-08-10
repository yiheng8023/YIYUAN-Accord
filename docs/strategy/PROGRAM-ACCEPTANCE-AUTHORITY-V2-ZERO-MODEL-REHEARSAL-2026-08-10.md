# Program Acceptance Authority v2 Zero-Model Rehearsal — 2026-08-10

## Result boundary

This local deterministic rehearsal reconstructs the candidate program plan,
g000001 structural snapshot, g000002 evidence-only snapshot, two forward
receipts, one rollback receipt, and the two candidate-selector byte streams.
It writes them only under a newly created disposable root, resolves g000002,
atomically swaps that disposable selector to the checked rollback selector,
resolves g000001, and removes the exact disposable root.

The original v1 authority, v1 plan, and two locked packet fixtures are reopened
by SHA-256 before and after the rehearsal. They are not rewritten, registered,
repointed, or selected as a new live authority.

The registered thirteen-scenario manifest evidence source is also reopened from
the bound repository root and checked against its exact SHA-256 and the g000002
evidence row. Candidate bytes are staged, fsynced, and resolved through both
selectors before their directory is published. Cleanup first renames the exact
lexical output into a same-parent quarantine, binds its lstat identity, and
refuses a swapped symlink or junction rather than following it.

## Sequence proved locally

```text
g000000 frozen v1 input -> g000001 structural candidate -> g000002 evidence-only candidate
                                                            |
                                                            v
                                      rollback selector -> g000001 candidate
```

The runnable entry point performs this sequence with zero model, candidate,
Plugin, install, enablement, account, manager, consumer, publication, release,
and production-activation counters. A failed selector replacement preserves an
existing sentinel byte-for-byte. The repository record uses canonical compact
JSON bytes and independently replays its ordered 87-case, 32-code public failure matrix;
the matrix includes isolated real-source missing and digest-drift overlays.

## Not registered or activated

The candidate selector remains a rehearsal artifact. The v1 acceptance map is
still the repository's current authority. This record is not an authority
migration, assessment promotion, consumer projection, live selector change,
or release action. Registration remains false because frozen-v1 authority and a
live-v2 migration require separate authorization.

## Claim ceiling

This mechanism-only local check does not prove task-time selection, instruction
delivery, candidate or Plugin behavior, value, cross-host portability,
production readiness, release eligibility, a residual repository-authored gap,
or overall Harness closeout.
