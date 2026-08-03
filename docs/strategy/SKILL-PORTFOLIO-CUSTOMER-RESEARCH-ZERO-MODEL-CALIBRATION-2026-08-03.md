# Customer-Research Incremental Effect Calibration

Date: 2026-08-03
Status: zero-model oracle calibrated; no candidate behavior or participant evidence

## Purpose

This package reuses the synthetic `GEN-RESEARCH-01` oracle and the participant
consent/retention boundary from the product-discovery calibration, then adds
five customer-research effect dimensions:

- source provenance;
- confidence labels;
- source-bias and proxy-persona limits;
- no invented quotation;
- privacy and retention boundaries before participant data.

It does not duplicate or re-execute either parent scenario. The extension
contains one source-free customer-research packet and five single-fault
mutations.

## Candidate and evidence boundary

The exact `customer-research` candidate remains static metadata at
`coreyhaines31/marketingskills@7868cb9251fad80a73d26e488a5ad5f6c4a9f335`.
Its mapping to all five dimensions is protocol design only, not measured
candidate capability. Future attribution remains current/native first and one
candidate at a time; composition is ineligible.

The parent research protocol is offline-oracle ready but explicitly not
live-comparison ready. This calibration does not promote older live results to
current comparator health or general research quality.

## Verification and limits

```powershell
python -B scripts/validate_skill_portfolio_customer_research_zero_model_protocol.py
python -B -m unittest tests.test_skill_portfolio_customer_research_zero_model_calibration -v
python -B scripts/verify.py
```

The evaluator reads no candidate payload and performs no installation,
projection, Agent/model dispatch, external research, customer/participant data
access, contact, recording, collection, retention, or deletion. Passing proves
only deterministic loss detection. It does not prove candidate behavior or
value, research quality, customer preference, participant consent, privacy or
retention satisfaction, live exposure, residual self-authored need, or
hard-standard eligibility.
