# Obsidian Format-Semantics Effect Calibration

Date: 2026-08-03
Status: domain-only zero-model oracle calibrated; no scenario or candidate behavior evidence

## Purpose

This package adds a domain-only source-free fixture for five format-semantics
dimensions: format validity, referential integrity, source preservation,
bounded file writes, and no imposed vault-organization model. It contains one
control and five single-fault mutations.

There is intentionally no governed scenario mapping. The fixture is not
scenario coverage and its existence does not prove a residual gap.

## Candidate and manager boundary

The exact `json-canvas`, `obsidian-bases`, and `obsidian-markdown` candidates
remain static metadata at
`kepano/obsidian-skills@a1dc48e68138490d522c04cbf5822214c6eb1202`.
Their dimension subsets are protocol design only, not measured behavior.

CC Switch repository registration and candidate-name discovery were previously
verified. Payload bytes, installation, exposure, invocation, instruction
delivery, behavior, value, vault access, and file writes remain unproved or
unauthorized.

## Verification and limits

```powershell
python -B scripts/validate_skill_portfolio_obsidian_format_semantics_zero_model_protocol.py
python -B -m unittest tests.test_skill_portfolio_obsidian_format_semantics_zero_model_calibration -v
python -B scripts/verify.py
```

Passing proves only deterministic fixture-level loss detection. It does not
prove format correctness beyond the fixture, scenario coverage, residual gap,
candidate installation/exposure/behavior/value, vault access or write
authority, acceptance of an organization model, or hard-standard eligibility.
