# TDD Non-Comparative Dispatch Authorization Adapter PoC

Date: 2026-07-26
Status: offline immutable authorization envelope validated; current candidates remain blocked

The ledger's intended public reservation path no longer accepts admission and
source-freshness booleans or a ledger path directly. It captures the
non-comparative protocol, dispatch-fresh source/toolchain preflight, static gap
audit, independent diagnostic-only exact-candidate admission, and the
protocol-bound ledger-authority document exactly once as immutable bytes.

The adapter verifies their raw byte digests, the protocol candidate identity
envelope, candidate-specific identity, one-dispatch/no-replacement/
non-comparison limits, static-audit bindings, source revalidation timestamp,
admission validity window, ledger-authority boundary, and absence of live task
activity. It returns one frozen authorization envelope containing those bytes,
the canonical reservation input, and the protocol-selected ledger path. The
ledger consumes that exact envelope rather than rereading mutable document
paths before reservation.

Twenty-three adapter, ledger, and preconstruction-transaction tests passed. A
synthetic, internally consistent five-document bundle is accepted. Digest
drift, stale source evidence, expiry, candidate mismatch, and comparison
authority fail closed. A post-envelope path mutation cannot change the
captured bytes, authorization digest, or selected ledger path. The actual
current repository protocol and preflight are explicitly rejected because
candidate execution eligibility is false and the dated preflight is not fresh
for dispatch.

The synthetic fixture is not a repository admission decision. No real
diagnostic admission record or dispatch-fresh preflight was created. No
app-server process, candidate Skill, thread, turn, or model request was
started. The offline wrapper consumes this envelope, but the formal runner does
not. Envelope-to-reservation consistency does not prove live
source-to-factory materialization freshness, live authority, or runtime cap
enforcement.

The offline wrapper now requires a structured handle validator and exercises
same-process registered resource cleanup, but those results do not change this
adapter's source-freshness boundary. Before formal-runner integration, the next
bounded PoC is a real app-server handle adapter plus live
source-snapshot-to-factory materialization freshness. Same-process synthetic
cleanup must not be promoted into live runtime, process-crash, or real-resource
proof.
