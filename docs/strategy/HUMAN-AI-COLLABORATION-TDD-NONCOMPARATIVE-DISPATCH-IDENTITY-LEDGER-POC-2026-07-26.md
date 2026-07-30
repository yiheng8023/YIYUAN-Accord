# TDD Non-Comparative Dispatch Identity Ledger PoC

Date: 2026-07-26
Status: offline construction-state PoC validated; no formal-runner integration or live transition

This PoC implements a repository-local, Python-standard-library identity
ledger for a possible later non-comparative TDD diagnostic. It records
candidate reservation, construction success or failure, manual
retain-consumed reconciliation, thread binding, and turn binding as
append-only JSONL events linked by SHA-256. The write path uses an exclusive
lock, flush, and `fsync`.

Twenty ledger and resource-contract tests passed. They cover the first
reservation, missing admission and stale-source rejection, the single-candidate
reservation cap, reservation identity replacement, rejection of thread binding
before an explicit `construction-succeeded` event, ordered immutable thread and
turn binding, content tampering, a torn JSONL tail, and a same-process
two-thread race in which exactly one reservation succeeds. They also cover a
fresh reader classifying `reserved-without-construction-outcome`, an exact
manual missing-outcome reconciliation that retains the consumed cap, and a
two-authority same-candidate counterexample.

The torn-tail test proves detection and fail-closed behavior, not crash
recovery. The concurrent test uses two threads in one Python process; it does
not prove cross-process exclusion on every host. `fsync` invocation is not
proof of power-loss durability.

## Runtime boundary

The ledger's public reservation entry now requires the document-bound
authorization adapter. The raw boolean-bearing reservation core is private and
also requires protocol, preflight, audit, admission, and authorization digests.
A synthetic admission record was validated in tests, while the current
repository protocol and dated preflight remain rejected.

The ledger is used only by the offline injected-factory wrapper. It is not
integrated with the formal runner or a real app-server factory. Therefore the
current one-dispatch and construction-state rules are still not enforced for a
live runner.

The dispatch cap in this PoC is
`protocol-selected-ledger-local`. Two distinct synthetic protocol-bound
authorities can each reserve the same candidate once; that two-authority
same-candidate counterexample means a system-global cap is absent from this
PoC. It does not establish duplicate-dispatch behavior on a live host.

If success-event append fails before a construction outcome is durable, a
fresh reader exposes a manual-recovery-required state. The only implemented
manual missing-outcome reconciliation binds the reservation-event hash and
uses `retain-consumed-no-retry`; it neither releases the reservation nor
authorizes replacement.

No candidate Skill was invoked. No app-server process, thread, turn, or model
request was started. No candidate projection, global configuration, CC Switch,
network, Git, admission, release, or portfolio state was changed.

The next bounded step is real app-server handle compatibility, real
child-process or socket cleanup, cross-process exclusion, crash recovery, and
live source-snapshot-to-factory freshness. Same-process registered cleanup is
not evidence of real child-process or socket cleanup, cleanup after process
crash, or cross-process exactly-once cleanup. The current candidate task turns
remain blocked.
