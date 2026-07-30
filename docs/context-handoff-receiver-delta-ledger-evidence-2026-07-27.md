# Context Handoff Receiver Delta Ledger Evidence (2026-07-27)

## Decision

`CTX-HANDOFF-RECEIVER-DELTA-LEDGER-01` is an additive, parent-recomputed
measurement module for the existing `ABL-CTX-HANDOFF-01` Arm C receiver. It
does not define a new scenario and does not replace, loosen, or rewrite the
canonical scorer in
`scripts/evaluate_skill_ablation_batch_01_protocol.py`.

The ledger exists because the canonical receiver normalizer is intentionally
strict: malformed or incomplete receiver output can stop with an exception
before the specific loss is retained. The ledger records those deltas and then
reports the canonical result, when available, as a separate unchanged field.

## Exact ledger contract

The module emits sorted exact sets and corresponding exact counts for:

- `omitted`: expected critical-fact IDs absent from the response;
- `changed`: expected critical-fact IDs whose machine-comparable values differ;
- `missingEvidence`: provenance references in the form
  `critical:<id>` or `stale:<id>`;
- `acceptedStale`: injected stale-assertion IDs marked `accepted`;
- `unresolvedStale`: injected stale-assertion IDs marked `unknown` or omitted;
- `unsupportedClaim`: bounded claim IDs derived from explicit claim booleans;
- `repositoryTruthDrift`: shared repository-truth field names whose values
  differ across the oracle, before projection, after projection, or receiver
  response.

`opaque=true` means a required source, shape, or digest binding cannot support
a non-zero/zero interpretation. Missing facts are not converted to zero and
are not represented only by an exception. `failureCodes` is a sorted exact
set, `failureCodeCount` is its exact cardinality, and both are independent of
canonical status.

## Parent-owned bindings

The ledger recomputes and requires matching parent observations for:

1. canonical packet JSON SHA-256;
2. supplied handoff artifact byte SHA-256;
3. raw receiver-response byte SHA-256;
4. private-oracle canonical JSON SHA-256;
5. observed source-manifest canonical JSON SHA-256;
6. shared Git observer before-projection canonical JSON SHA-256;
7. shared Git observer after-projection canonical JSON SHA-256.

The source manifest must also equal the packet oracle manifest. The handoff
artifact bytes must equal the receiver-bound artifact digest. Before and after
Git projections must have the established
`REPOSITORY_TRUTH_FIELDS` shape. A recursively exposed `oraclePrivate` or
`privateOracle` key on a public surface is a hard failure.

The string
`scripts.observe_git_snapshot.observe_repository` identifies the established
shared Git observer. This ledger consumes its parent-owned projections; it does
not create a second Git parser or run Git.

## Deterministic falsification surface

The fixture
`tests/fixtures/context-handoff-receiver-delta-ledger-2026-07-27.json`
declares 16 cases:

- exact control;
- one critical-fact omission;
- one critical-fact value change;
- one provenance break;
- accepted and unknown handling of the same stale assertion;
- one unsupported automatic-creation claim;
- one repository-truth field drift;
- packet, artifact, raw-response, oracle, source-manifest, shared-Git-before,
  and shared-Git-after digest drift;
- private-oracle key leakage.

The control calls the existing canonical scorer and requires
`live-context-arm-c-producer-receiver-private-oracle-matched` in deterministic
replay. Every case asserts the entire set map, count map, `opaque`, status, and
exact failure-code set. Existing canonical-scorer regression tests remain
separate and unchanged.

## Execution and claim boundary

This evidence used zero Agent dispatches, zero model calls, zero created
threads, no remote Git, and no host configuration change. The test fixture
replays synthetic parent evidence; it is not live-host evidence.

It does **not** prove receiver recovery, Skill invocation, a fresh session,
lossless handoff, atomicity, dirty-file ownership, AGENTS/rules adherence,
weak-Agent behavior, or cross-host behavior. A passing ledger demonstrates
only deterministic ledger behavior and unchanged canonical-scorer reuse under
the bound fixture.

## Independent verification

Run:

```powershell
python -B -m unittest tests.test_context_handoff_receiver_delta_ledger -v
python -B scripts/validate_context_handoff_receiver_delta_ledger_evidence.py
python -B -m unittest tests.test_skill_ablation_batch_01_protocol -v
```

The standalone validator checks registry source bindings, fixture coverage,
zero-side-effect fields, negative-claim fields, additive-scorer identity, and
the current focused test result. It does not call a model, create a thread, use
remote Git, or change configuration.
