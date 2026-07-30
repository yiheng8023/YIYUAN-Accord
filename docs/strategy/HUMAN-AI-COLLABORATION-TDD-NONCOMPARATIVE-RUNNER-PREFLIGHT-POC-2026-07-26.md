# TDD Non-Comparative Runner Preflight PoC

Date: 2026-07-26
Status: offline immutable authorization and construction state validated; no live app-server

The no-model wrapper accepts repository-document paths, a candidate and
reservation identity, and an injected factory callback. It no longer accepts a
ledger path from its caller. The admitted synthetic protocol digest-binds one
contained ledger-authority document; that document selects the JSONL path and
forbids ledger replacement, automatic release, and automatic retry.

Twenty-nine wrapper, authority/reconciliation, preconstruction-transaction,
and resource-contract tests passed. The adapter reads the protocol, preflight,
audit, admission, and ledger-authority document once and freezes those exact
bytes, the canonical authorization, and the selected ledger path in one
immutable envelope. The ledger consumes that exact envelope without rereading
mutable source paths. A synthetic post-envelope path mutation therefore cannot
change the authorization used by reservation; this closes document drift only
from the captured authorization envelope to the offline reservation event.

With a synthetic, internally consistent bundle, the wrapper appends, flushes,
and file-fsyncs the reservation, and only then calls the fake factory. The fake
factory reads the ledger and observes its own reservation already present. A
successful factory is followed by `construction-succeeded` before its handle
is returned, and thread binding rejects until that event exists. This proves
same-process, protocol-selected-ledger and construction-state ordering, not
live source-to-factory materialization freshness, crash durability, or
power-loss durability.

The actual current document bundle rejects at the protocol-eligibility gate
before authority resolution, fake-factory invocation, or ledger creation; the
test does not dynamically reach the later preflight-freshness gate.
Authority-byte drift and a non-callable factory also fail before ledger
creation.

The wrapper requires a structured handle validator. The validator is invoked
exactly once; test validators explicitly reject `None`, `False`, and an empty
list. A factory can register same-process owned resources under unique
identities. Factory or validation failure cleans those same-process registered
resources once in LIFO order, then appends a bounded failure class. This is an
injected contract, not proof that a real app-server handle is compatible.

When the injected factory raises and failure-event append succeeds, the wrapper
appends `construction-failed` without persisting the exception text, then
propagates the original error. If failure-event append and registered cleanup
both raise, even a hostile original factory exception remains primary and
exposes the secondary errors best-effort.

If success append reports an error, durable success is confirmed by ledger
readback before resource ownership transfers. When no outcome is durable,
resources are cleaned and a fresh reader reports
`reserved-without-construction-outcome` plus `manual-recovery-required`.
A manual missing-outcome reconciliation binds the authority, candidate,
reservation, and reservation-event hash. Its only accepted disposition is
`retain-consumed-no-retry`; it neither releases the reservation nor authorizes
replacement. A second dispatch remains rejected before the factory is called.

Two protocol-selected ledger authorities can each reserve the same candidate
once. Therefore the current dispatch-cap scope is
`protocol-selected-ledger-local`; this counterexample falsifies a system-global
cap for the current PoC without making a claim about live-host behavior.

Only an injected fake factory was used. No real app-server implementation,
process, model, candidate Skill, projection, thread, or task turn was used.
The wrapper is not integrated into the formal runner. The tests do not prove
live app-server preconstruction ordering, real factory compatibility,
automatic crash recovery, cross-process exclusion, process-crash durability,
power-loss durability, live source-snapshot-to-factory freshness, real
app-server handle compatibility, real child-process or socket cleanup, cleanup
after process crash, cross-process exactly-once cleanup, live runtime cap
enforcement, a system-global cap across multiple authorities, or production
readiness. The protocol-bound authority exists only in synthetic test
documents; no live ledger authority is configured for the current blocked
protocol.

The next bounded PoC is a real app-server handle adapter and real resource
ownership contract, followed by live source-snapshot-to-factory freshness,
cross-process exclusion, and crash or kill recovery checks. The ledger-local
cap and manual retain-consumed fallback remain explicit. Formal runner
integration remains blocked.
