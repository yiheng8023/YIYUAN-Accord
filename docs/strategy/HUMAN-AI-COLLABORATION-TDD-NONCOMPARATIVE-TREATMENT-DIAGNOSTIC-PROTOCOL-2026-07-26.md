# TDD Non-Comparative Treatment Diagnostic Protocol

Date: 2026-07-26
Status: preregistered; governance gate unsatisfied; no live diagnostic started

## Why this protocol exists

The native Spark/low TDD arm reached its cap after three attempts with zero
valid formal repetitions. That removes the baseline required for a defensible
Matt-versus-native or Superpowers-versus-native comparison. It also prevents a
Matt-versus-Superpowers result from being smuggled in as a substitute
comparison.

This protocol therefore narrows the next possible evidence surface to two
independent delivery and trace-observability diagnostics. No candidate task
turn has started. Each diagnostic is identity-bound and allows at most one
dispatch per exact candidate. There is no control arm, paired arm, replacement
run, aggregate score, or shared winner decision.

## What is bound

The candidates remain:

- current Matt `tdd` at revision
  `ed37663cc5fbef691ddfecd080dff42f7e7e350d`; and
- the OpenAI-curated runtime distribution of Superpowers 6.2.0
  `test-driven-development`.

Their exact file, license, projected-tree, and no-turn metadata-selection
digests are copied from the parent protocol and current exposure preflight.
Before any later dispatch, the selected projection must be rematerialized and
reverified, and a fresh app-server process must prove that only its configurable
metadata is enabled.

The one-dispatch and no-replacement rules are preregistered design constraints,
not current runtime enforcement. No runner consumes this protocol and no
append-only candidate/thread/turn identity ledger exists yet. Current safety
depends on live authority remaining false. A live transition must stay blocked
until a tested runner and identity ledger enforce the cap, replacement stop, and
shared-control-plane abort.

The host envelope stays frozen to Codex app-server 0.145.0,
`gpt-5.3-codex-spark` with `low` effort, no provider fallback, `approval=never`,
an ephemeral `workspaceWrite` thread, no network, disabled plugin features,
and disabled static MCP startup.

## Governance gate

Technical projection feasibility is not execution admission.

The current Matt projection is not the approved release payload. The repository
does contain an approved, validated `skill.curated.tdd` entry from Matt lineage,
but its released bytes and governed adaptations differ from the current
`ed37663…` three-file projection.

Superpowers 6.2.0 is not a repository-approved release entry. Its OpenAI-curated
distribution and local installation establish a bounded provenance and
availability observation, not admission by this repository's curated release
authority.

Exact-candidate execution admission remains unsatisfied for both projections.
This record consequently authorizes protocol and read-only governance work
only. It does not authorize a model request, task turn, third-party candidate
instruction execution, global configuration change, CC Switch mutation, or
portfolio decision.

## What a later admitted diagnostic may observe

A later separately admitted diagnostic may record absolute categorical facts:

- exact source and projected-tree identity;
- candidate-specific selected metadata;
- acceptance of the exact structured Skill `name` and `path`;
- candidate metadata attached to the bound turn, if the host exposes it;
- ordered raw item types, `fileChange` events, command events, and exit status;
- opaque or unclassifiable writes;
- whether a RED-before-production and GREEN-after-production timeline is
  observable; and
- visible and hidden task outcomes as non-scored facts.

It does not produce a score, ranking, winner, preference, or comparative result.
Task success may be recorded only as absolute feasibility evidence. Inventory
metadata selection does not prove Skill-body delivery. Structured input
acceptance does not prove an independent loader event, behavioral causation, or
candidate value.

## Fail-closed stops

Stop before or during a later diagnostic if exact source, license, projection,
fixture, oracle, hard-acceptance, or normalizer identity drifts; if selection is
ambiguous; if more than one configurable candidate is enabled; if the structured
input identity differs; if host controls drift; if the private oracle leaks; if
repository or global configuration changes; if a raw item is unknown or a write
is opaque; if the single-dispatch cap would be exceeded; or if exact candidate
admission is absent.

Any attempt to turn an observation into comparison, superiority, preference,
admission, rejection, self-authored residual-gap evidence, or portfolio mutation
also stops the diagnostic.

## Current decision

The protocol is ready for repository validation, not for candidate execution.
The dated
[source and governance preflight](HUMAN-AI-COLLABORATION-TDD-NONCOMPARATIVE-TREATMENT-DIAGNOSTIC-SOURCE-GOVERNANCE-PREFLIGHT-2026-07-26.md)
revalidated the pinned Matt bytes, local Superpowers bytes, Codex version, and
projection/normalization toolchain while confirming that exact-candidate
execution admission is still absent. The
[exact-candidate admission-gap audit](HUMAN-AI-COLLABORATION-TDD-EXACT-CANDIDATE-ADMISSION-GAP-AUDIT-2026-07-26.md)
classifies the exact candidates' pass, partial, and blocking evidence. The
static admission-gap audit admits or rejects neither candidate and records no
portfolio decision.
Formal comparison remains blocked. The next bounded work is an exact-candidate
governance review plus a tested dispatch runner and append-only identity ledger.
The
[offline dispatch identity ledger PoC](HUMAN-AI-COLLABORATION-TDD-NONCOMPARATIVE-DISPATCH-IDENTITY-LEDGER-POC-2026-07-26.md)
now validates a hash-chained module, single-candidate reservation cap, immutable
thread/turn bindings, tamper detection, torn-tail failure, and a same-process
thread race. The offline ledger PoC is not integrated with the formal runner
and does not consume the protocol or an admission record.
The
[dispatch authorization adapter PoC](HUMAN-AI-COLLABORATION-TDD-NONCOMPARATIVE-DISPATCH-AUTHORIZATION-ADAPTER-POC-2026-07-26.md)
now makes the intended ledger entry document-bound. The document-bound adapter
rejects the current protocol and preflight while accepting only an internally
consistent synthetic admission bundle. This is not real admission evidence.
The subsequent
[no-model runner preflight PoC](HUMAN-AI-COLLABORATION-TDD-NONCOMPARATIVE-RUNNER-PREFLIGHT-POC-2026-07-26.md)
now uses a synthetic protocol-bound ledger authority and no longer accepts a
caller-selected ledger path. Its admitted synthetic protocol digest-binds one
contained authority document, freezes the protocol, preflight, audit,
admission, and authority bytes in one authorization envelope, writes and
file-fsyncs the reservation from that same envelope, and only then calls the
injected fake factory. Post-envelope document-path drift therefore cannot
change the reservation authorization. A successful construction appends
`construction-succeeded` before returning its handle, and thread binding
rejects until that event exists. A factory exception appends an explicit
`construction-failed` event without persisting exception text. The wrapper now
requires a structured handle validator and cleans same-process registered
resources once in LIFO order on bounded factory or validation failures. If
failure append and cleanup both fail, the original factory exception remains
primary and secondary errors are attached best-effort. If success append is
ambiguous, durable success is accepted only after ledger readback; otherwise a
fresh reader exposes `reserved-without-construction-outcome`. A separately
supplied manual reconciliation document may only select
`retain-consumed-no-retry`; it neither releases the reservation nor reopens the
one-candidate cap. Two protocol-bound authorities can each reserve the same
candidate once, so the current cap is `protocol-selected-ledger-local`, not
system-global.

The actual current document bundle still rejects at the protocol-eligibility
gate before authority resolution or callback, and the later
preflight-freshness gate is not dynamically reached in that run. The wrapper
is not integrated with the formal runner or a real app-server factory, and no
live ledger authority is configured. The synthetic
authorization-envelope-to-reservation document-drift window is closed only for
this unit-tested path. Live source-snapshot-to-factory materialization
freshness, a real app-server handle adapter, real child-process or socket
cleanup, cross-process exactly-once cleanup, cross-process exclusion, crash
recovery, and power-loss durability remain open; there is no automatic release
or retry.
Only an admitted candidate protected by that runtime gate may later receive its
one independent disposable diagnostic; a candidate that does not pass both
gates remains metadata-only evidence.
