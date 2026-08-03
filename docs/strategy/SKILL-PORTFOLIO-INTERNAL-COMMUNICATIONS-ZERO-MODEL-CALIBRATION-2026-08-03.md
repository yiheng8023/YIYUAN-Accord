# Internal-Communications Incremental Effect Calibration

Date: 2026-08-03
Status: zero-model oracle calibrated; no candidate behavior or delivery evidence

## Purpose

This package reuses the existing `GEN-ACCESS-COMMS-01` baseline and oracle,
then adds five internal-communications effect dimensions: audience fit,
carrier fit, source traceability, account/data boundaries, and send/publication
authority. It contains one source-free draft packet and five single-fault
mutations; the parent scenario is not duplicated or re-executed.

## Candidate and authority boundary

The exact `internal-comms` item remains dated official-upstream metadata at
`anthropics/skills@b29e7cf65e5cb78a5ac33d582270551bc74a14eb`.
Its mapping to the five dimensions is protocol design only, not measured
candidate capability. Official upstream status does not authorize vendoring,
installation, account connection, data access, sending, or publication.

Future attribution remains current/native first and one candidate at a time;
composition is ineligible. Any Slack, email, calendar, document, or other
organizational account/data access remains a separate task-time gate.

## Verification and limits

```powershell
python -B scripts/validate_skill_portfolio_internal_communications_zero_model_protocol.py
python -B -m unittest tests.test_skill_portfolio_internal_communications_zero_model_calibration -v
python -B scripts/verify.py
```

The evaluator reads no candidate payload and performs no installation,
projection, Agent/model dispatch, account/data access, message send,
publication, or external write. Passing proves only deterministic loss
detection. It does not prove candidate behavior or value, communication
effectiveness, audience/carrier fit, account or data authority, delivery,
live exposure, residual self-authored need, or hard-standard eligibility.
