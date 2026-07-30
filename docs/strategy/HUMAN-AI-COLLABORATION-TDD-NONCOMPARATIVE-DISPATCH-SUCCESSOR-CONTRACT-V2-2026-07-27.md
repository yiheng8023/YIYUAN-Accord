# TDD Non-Comparative Dispatch Successor Contract V2

Date: 2026-07-27

Status: `offline-successor-contract-preregistered-live-no-go`

## Outcome

The v2 contract and pure bundle builder replace no historical record. They
preregister a fail-closed preparation boundary for one possible future
non-comparative TDD diagnostic. The current decision remains `NO-GO`.

The builder can validate already-provided documents and return either:

- `NO-GO` when an independent authority grant is absent; or
- `offline-structure-consistent-authority-unverified-live-no-go` when a
  complete bundle is structurally consistent and the exact snapshot bytes
  match the parent protocol's candidate file set. Revision, license, projection
  tree, toolchain, authority, and clock remain separately bound or unverified
  rather than inferred from file bytes alone.

The missing-grant path first validates the repository-bound successor contract
and the selected candidate's static identity. It then returns `NO-GO` before
validating the supplied snapshot, preflight, or ledger-authority documents.
That fail-closed result must not be described as validation of those skipped
inputs.

Neither result authorizes a live effect.

## Why a successor is required

Four historical incompatibilities cannot be repaired by flipping one
eligibility field:

1. The parent protocol declares `replacementDispatchesAllowed`; the historical
   adapter reads `replacementDispatchAllowed`.
2. The static gap audit permanently binds the dated preflight, while the
   historical adapter requires that binding to equal the dispatch-time fresh
   preflight.
3. The historical ledger binds thread and turn identities only after host
   responses; it has no durable pre-send `thread-start-intent` or
   `turn-start-intent`.
4. The historical formal runner uses a formal weak-acceptance policy shell,
   while the non-comparative diagnostic contributes nothing to formal
   acceptance. The historical runner preflight also returns a raw successful
   handle without an explicit closeable owner.

Rewriting the old protocol, audit, adapter, ledger, runner preflight, or formal
runner would invalidate their evidence identity. V2 therefore records them as
immutable baseline evidence and excludes the formal policy shell.

## Three evidence layers

The successor keeps three evidence layers separate:

1. **Static governance** — the dated source observation, gap audit, and two
   identity-bound diagnostic-only admission decisions.
2. **Dispatch-time freshness** — one exact source-file snapshot and a
   preflight whose file bindings and time window are recomputed against that
   snapshot. Toolchain fields remain structurally bound but unauthenticated.
3. **Independent authority** — a short-lived grant and one shared
   experiment-level ledger authority supplied from outside the builder.

No layer substitutes for another. The pure builder cannot issue the grant,
create or append a ledger, fetch source, or infer authority from static
admission.

## Pure offline builder

The builder:

- validates the current successor contract and all exact historical source
  hashes through the hard-coded validator rather than trusting a mutable
  contract's policy fields;
- binds this companion document by exact byte length and SHA-256 so that
  authorization wording cannot be appended while marker-only validation still
  passes;
- requires disjoint existing control and trial roots;
- rejects absolute, parent-traversing, linked, missing, case-colliding, or
  duplicate snapshot file paths;
- reads every snapshot file under the control root and recomputes its byte
  length and digest against the parent protocol's exact candidate file set;
- recomputes snapshot, preflight, grant, and ledger-authority bindings;
- checks 1,200-second ledger-authority age, snapshot-to-preflight,
  preflight-age, and grant windows against an injected offset-aware clock while
  explicitly recording that the builder does not authenticate that clock;
- enforces `ledger issued ≤ snapshot captured ≤ preflight observed ≤ grant
  issued ≤ valid from ≤ evaluated at < valid until`; and
- rejects broadened effects, fallback providers, network access, comparison,
  replacement, scoring, portfolio mutation, or formal acceptance credit; and
- emits a deterministic bundle digest.

The locator prefix on a supplied grant and the shape of a supplied ledger
authority are structural checks only. The builder cannot authenticate a user
confirmation, runtime authority, ledger authority, or trusted clock. Its
non-`NO-GO` output therefore records both
`authorityAuthenticityVerified=false`, `clockAuthorityVerified=false`, and
`toolchainAuthenticityVerified=false`, plus the remaining live gates. A
runtime must not treat that offline output as execution authority.

It does not authorize or perform candidate materialization, candidate
instruction execution, ledger mutation, app-server start, thread or turn
creation, model dispatch, source download, CC Switch access, global
configuration change, Git operation, release, publication, or external write.

## Required future ordering

A separately authorized future runtime slice must preserve this order:

1. validate static history and exact candidate identity;
2. capture one control bundle and one ledger authority;
3. capture the exact source snapshot and toolchain;
4. persist and revalidate the fresh preflight;
5. wait for the independent grant;
6. freeze the authorization envelope;
7. reserve before candidate materialization;
8. materialize only from the snapshot and validate the projection;
9. construct an explicit closeable owner and persist construction success;
10. persist `thread-start-intent` before `thread/start`;
11. persist `turn-start-intent` before `turn/start`;
12. retain ambiguous outcomes as consumed with no automatic retry; and
13. close or abort the owner and persist `resources-closed`.

This document specifies that order; the current builder implements none of the
live transitions.

## Verification

```text
python -B scripts/validate_human_ai_collaboration_tdd_noncomparative_dispatch_successor_contract_v2.py
python -B -m unittest tests.test_human_ai_collaboration_tdd_noncomparative_dispatch_successor_contract_v2
```

The tests use temporary synthetic directories and caller-provided component
documents. The repository does not vendor the exact candidate source bytes, so
the current end-to-end builder test deliberately proves that a metadata-only
manifest cannot pass as a candidate snapshot. The tests do not create a real
grant, live ledger, candidate projection, app-server, thread, turn, or model
request.

## Claim boundary

This slice does not authorize or prove:

- real source or toolchain freshness;
- an actual human or runtime authority grant, trusted clock, or authenticated
  authority evidence;
- a live ledger authority, reservation, or cross-process exclusion;
- candidate materialization, invocation, instruction delivery, or causation;
- a model request or weak-Agent acceptance contribution;
- real app-server ownership, cleanup, crash recovery, or task-end release;
- candidate value, preference, or superiority;
- a residual need for a self-authored TDD capability;
- portfolio mutation, approved release admission, or production readiness.

A valid offline bundle is preparation evidence only. It is not current
execution authority and must not be fed into the historical formal runner as
if it were a formal comparison arm.
