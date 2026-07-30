# Human-AI Collaboration Access/Comms Zero-Model Calibration

Date: 2026-07-27

## Outcome

`GEN-ACCESS-COMMS-01` now has one repository-local, zero-model calibration for
a structured semantic loss gate. The current result is bounded to:

`zero-model-calibrated-no-live-agent-or-domain`

It is not live-domain evidence and does not promote the whole scenario,
cross-cutting process fidelity, or any candidate capability to accepted.

## Bound task

The parent scenario asks whether a consequential message can be adapted across
language, literacy, and accessibility needs without changing its obligations,
uncertainty, or speaker intent.

The protocol now embeds the exact complete `GEN-ACCESS-COMMS-01` source
scenario contract and verifies it against the hash-bound scenario matrix. A
separate `localCalibrationNarrowing` object records what the synthetic
calibration narrows. It does not rewrite the source authority, data,
acceptance, evidence, fallback, falsifier, forbidden-claim, or evidence-state
contract.

This PoC uses one synthetic boil-water advisory represented as a frozen
structured semantic normal form. It does not attempt to parse or grade
arbitrary prose. The frozen fields are:

- accountable actor;
- obligation;
- negated prohibition;
- deadline;
- action unit;
- uncertainty;
- bound terminology;
- accessibility structure.

Official release, legally consequential wording, bilingual or domain review,
recipient testing, and accessibility certification remain human-owned future
evidence surfaces.

All source, fixture, reused-module, protocol, and documentation paths are
repository-relative and fail closed on absolute paths, parent traversal, or
link traversal. The evaluator computes the fixture digest from the bound file;
callers cannot supply a substitute digest.

## Reused process-fidelity mechanism

The domain evaluator does not implement another cumulative-loss framework. It
converts the frozen structured states into parent-scored active loss sets and
calls the existing
`build_cumulative_loss_ledger` implementation.

The reused ledger independently validates active loss weights and computes:

- new loss;
- carried loss;
- recovered loss;
- first-seen and reintroduced loss;
- deduplicated cumulative unique loss;
- peak active loss;
- first strict budget breach;
- the rule that terminal recovery does not erase historical unique loss.

The four frozen stages are source anchor, adapted message, review detection,
and exact-source recovery. The review stage is scripted calibration material,
not evidence of an actual human reviewer.

## Fault corpus

The frozen fixture contains one identity control and one case for each required
fault class:

1. obligation weakening;
2. actor swap;
3. negation flip;
4. deadline and unit drift;
5. uncertainty deletion;
6. invented commitment;
7. terminology drift;
8. accessibility-structure break.

Every fault must:

- appear as a parent-recomputed new loss at the adapted-message stage;
- remain carried and be detected exactly at the review stage;
- disappear from the active loss set after exact-source recovery;
- remain in the deduplicated historical cumulative-loss set;
- record its first strict zero-tolerance budget breach at the adapted-message
  stage.

The identity control must remain at zero active and cumulative loss.

## Evidence surfaces

- Protocol:
  `registry/human-ai-collaboration-access-comms-zero-model-protocol-2026-07-27.json`
- Frozen fixture:
  `tests/fixtures/human-ai-collaboration-access-comms-zero-model-calibration-2026-07-27.json`
- Evaluator:
  `scripts/evaluate_human_ai_collaboration_access_comms_zero_model_calibration.py`
- Focused tests:
  `tests/test_human_ai_collaboration_access_comms_zero_model_calibration.py`

Focused verification:

```text
python -B -m unittest tests.test_human_ai_collaboration_access_comms_zero_model_calibration
24 tests passed
```

The standalone evaluator emits a deterministic report and remains read-only:

```text
python -B scripts/evaluate_human_ai_collaboration_access_comms_zero_model_calibration.py
```

## Claim boundary

This calibration does not prove:

- correctness of free-form adaptation or translation;
- bilingual or specialist-domain correctness;
- recipient comprehension;
- accessibility conformance from the frozen structure alone;
- the effect of actual human review;
- live Agent, model, Skill, CC Switch, or host behavior;
- candidate value, preference, causation, or superiority;
- cross-host behavior;
- whole-scenario, whole-program, or end-to-end process-fidelity acceptance;
- a residual need for a self-authored capability.

No Agent dispatch, model call, network access, account or private-data access,
candidate execution, CC Switch operation, global configuration change, Git
operation, release, publication, or external side effect is part of this PoC.
