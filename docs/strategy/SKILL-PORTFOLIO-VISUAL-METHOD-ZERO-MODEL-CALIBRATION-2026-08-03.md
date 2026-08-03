# Visual-Method Incremental Effect Calibration

Date: 2026-08-03
Status: zero-model oracle calibrated; no candidate behavior or generated artifact evidence

## Purpose

This package reuses the creative-capability baseline and bounded preference
packet, then adds five visual-method effect dimensions: source faithfulness,
layout/visual planning, a confirmation gate, native-backend preference, and an
artifact-manifest/write boundary. It contains one source-free plan packet and
five single-fault mutations; the parent scenario is not duplicated or run.

## Candidate and generation boundary

The three exact Baoyu candidates remain static metadata at
`JimLiu/baoyu-skills@6b7a2e417500561a5ecdd0b168332f4142584617`.
Their mapping to the five dimensions is protocol design only, not measured
behavior. Future attribution remains native/current first and one candidate at
a time; composition is ineligible.

The methods' native-image-backend preference does not authorize a model call,
cost, external backend, preference write, or generated artifact. User visual
judgment and confirmation remain authoritative.

## Verification and limits

```powershell
python -B scripts/validate_skill_portfolio_visual_method_zero_model_protocol.py
python -B -m unittest tests.test_skill_portfolio_visual_method_zero_model_calibration -v
python -B scripts/verify.py
```

The evaluator reads no candidate payload and performs no installation,
projection, Agent/model dispatch, image generation, backend/cost authorization,
or artifact write. Passing proves only deterministic loss detection. It does
not prove candidate behavior or value, visual quality, source faithfulness,
generalized preference, generation/write authority, live exposure, residual
self-authored need, or hard-standard eligibility.
