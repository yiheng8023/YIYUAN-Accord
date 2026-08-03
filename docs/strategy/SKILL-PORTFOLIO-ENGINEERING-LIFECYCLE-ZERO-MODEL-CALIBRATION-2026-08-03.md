# Engineering-Lifecycle Shared Effect Calibration

Date: 2026-08-03
Status: zero-model shared-structure oracle calibrated; no candidate behavior

## Purpose

This package calibrates six structural loss classes shared across the mapped
engineering-lifecycle candidate group:

- repository conventions inspected before proposing change;
- request-to-change-to-verification traceability;
- explicit verification evidence;
- rollback or reversibility safeguards;
- current-source identity and freshness;
- retained human authority for destructive, migration, release, and deployment
  decisions.

It reuses six existing governed scenario identifiers and binds historical
release, migration, carrier-neutral engineering-evaluation, and source-snapshot
records. It does not duplicate a full scenario or rerun those historical
protocols.

## Candidate and attribution boundary

The four exact candidates remain static metadata at
`addyosmani/agent-skills@7829ffd90d973b6325f5f12f1b1226dcace74443`:

- `ci-cd-and-automation`;
- `deprecation-and-migration`;
- `documentation-and-adrs`;
- `source-driven-development`.

The candidate-to-dimension matrix is static protocol design only. It prevents
a later arm from scoring a candidate against unrelated dimensions; it is not
evidence that the candidate supplies any listed effect. A later comparison
must use one candidate at a time and only its declared eligible dimensions.

Historical release and migration evidence used older adapted or then-current
surfaces. This calibration does not promote that evidence to the four current
exact-upstream identities, to general preference, or to current behavior.

## Verification and limits

The fixture contains one lossless shared lifecycle packet and six single-fault
mutations. The evaluator performs no candidate payload read, installation,
projection, enablement, exposure, Agent/model dispatch, account access,
repository workflow mutation, migration, release, or deployment.

```powershell
python -B scripts/validate_skill_portfolio_engineering_lifecycle_zero_model_protocol.py
python -B -m unittest tests.test_skill_portfolio_engineering_lifecycle_zero_model_calibration -v
python -B scripts/verify.py
```

Passing proves deterministic loss detection for the shared structure only. It
does not prove current candidate behavior or value, comparator health, live
exposure, production readiness, a residual self-authored gap, or hard-standard
eligibility.
