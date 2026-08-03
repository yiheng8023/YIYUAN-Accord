# Product-Discovery Incremental Effect Calibration

Date: 2026-08-03
Status: zero-model oracle calibrated; no candidate behavior or participant evidence

## Purpose

This package extends the existing source-bound `SE-DISCOVERY-REQ-01` fixture
with five product-discovery effect dimensions:

- evidence linkage;
- anti-leading interview language;
- recording and outreach consent boundaries;
- outcome-to-opportunity-to-solution-to-test traceability;
- visible uncertainty and missing research evidence.

It reuses the parent requirements protocol and fixture rather than duplicating
the full scenario. The extension contains one source-free discovery packet and
five single-fault mutations.

## Candidate and history boundary

The exact candidates remain static metadata at
`phuryn/pm-skills@18468a95b427e70e258b51389796367c6f684e7d`:

- `interview-script` is mapped to evidence linkage, anti-leading language,
  consent, and uncertainty visibility;
- `opportunity-solution-tree` is mapped to evidence linkage, structured trace,
  and uncertainty visibility.

This matrix is static protocol design only, not measured candidate capability.
Future attribution remains current/native first and one candidate at a time.

The historical `SE-DISCOVERY-REQ-01` live comparison used
`cc.grill-with-docs`, not either current candidate. Both historical arms passed
the full hidden contract zero times, so that evidence is retained only as a
claim ceiling. It is not current candidate proof, product-discovery competence,
preference, or residual-gap evidence.

## Verification and limits

```powershell
python -B scripts/validate_skill_portfolio_product_discovery_zero_model_protocol.py
python -B -m unittest tests.test_skill_portfolio_product_discovery_zero_model_calibration -v
python -B scripts/verify.py
```

The evaluator reads no candidate payload and performs no installation,
projection, Agent/model dispatch, participant contact, recording, data
collection, retention decision, or discovery-artifact write. Passing proves
only deterministic loss detection. It does not prove candidate behavior or
value, product discovery, requirements completeness, participant consent, live
exposure, residual self-authored need, or hard-standard eligibility.
