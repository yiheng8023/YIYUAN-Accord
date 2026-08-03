# Decision-Challenge Incremental Effect Calibration

Date: 2026-08-03
Status: zero-model oracle calibrated; no candidate behavior or value evidence

## Purpose

This package tests whether a deterministic parent-recomputed oracle can detect
loss in the incremental effect dimensions mapped to `strategy-red-team`:

- steelman quality;
- failure assumptions;
- falsification signals;
- cheap reversible test quality;
- preservation of human decision authority.

It reuses the frozen `GEN-ORG-DECISION-01` protocol and fixture. It does not
create or duplicate a full organizational-decision scenario. The new fixture
contains only a source-free structured challenge packet, one lossless control,
and six single-fault mutations.

## Boundaries

The exact candidate remains static review metadata at
`phuryn/pm-skills@18468a95b427e70e258b51389796367c6f684e7d`. This calibration
does not read the candidate payload, install or project a Skill, mutate CC
Switch, dispatch an Agent or model, access an account or organizational data,
or communicate or implement a decision.

Passing the oracle proves only that the structured fixture detects the six
declared omission/change classes and preserves their cumulative history after
terminal recovery. It does not prove live exposure, candidate behavior,
incremental value, organizational decision quality, a residual self-authored
gap, or hard-standard eligibility.

## Verification

```powershell
python -B scripts/validate_skill_portfolio_decision_challenge_zero_model_protocol.py
python -B -m unittest tests.test_skill_portfolio_decision_challenge_zero_model_calibration -v
python -B scripts/verify.py
```

The next possible gate is a separately authorized native/current-versus-one-
candidate behavior comparison. That gate still requires task-scoped exposure,
visible route evidence, stop and cleanup controls, and independent acceptance;
this calibration does not authorize it.
