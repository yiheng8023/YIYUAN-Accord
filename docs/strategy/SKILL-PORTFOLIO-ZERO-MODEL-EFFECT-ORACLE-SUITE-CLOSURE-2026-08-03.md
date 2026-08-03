# Zero-Model Effect-Oracle Suite Closure

Date: 2026-08-03
Status: eight-group zero-model suite calibrated; live behavior gate remains closed

## Decision card

- Eight effect groups cover all 17 static candidates exactly once.
- The suite contains 50 deterministic cases: 8 controls and 42 single-fault
  cases.
- Every group reports zero Agent dispatches, model calls, and candidate
  executions, and every claim boundary remains false.
- No candidate installation, live behavior arm, value claim, residual
  self-authored gap, or hard-standard promotion is authorized by this closure.

## What this closes

The suite validator reruns every group evaluator, reconciles the candidate set
against the frozen demand map, rejects duplicate or missing cross-group
coverage, and checks the per-group case counts and claim ceilings. This closes
the zero-model oracle-construction stage only.

The Obsidian group remains domain-only; it is not promoted to scenario
coverage. Reused historical comparisons, manager registration, official
metadata, preference packets, and parent protocols retain their original
bounded meanings.

## Verification and next gate

```powershell
python -B scripts/validate_skill_portfolio_zero_model_effect_oracle_suite.py
python -B -m unittest tests.test_skill_portfolio_zero_model_effect_oracle_suite -v
python -B scripts/verify.py
```

The next possible stage is not automatic installation or broad execution. It
is a separately authorized native/current-versus-one-candidate behavior arm
with explicit route visibility, no silent model substitution, task/data/cost
boundaries, stop conditions, cleanup, and acceptance. Until that authorization
is bound, the live gate remains closed.
