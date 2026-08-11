# Continuation

Updated: 2026-08-11

This file is a compact navigation aid. Recheck live Git truth before using it.

## Current product authority

- `product/constitution.json`
- `product/program.json`
- `product/acceptance.json`
- `docs/operations/CURRENT-GOAL-MODE-PROMPT.md`

The predecessor evidence corpus is inactive and has no current product,
planning, acceptance, runtime, or release authority.

## Current increment

`increment.product-control-reset` is active. Its purpose is to replace the
inherited research scheduler with finite product acceptance and to isolate all
predecessor authority.

Current expected product report during the increment:

- O1 finite plan-bound delivery: verified;
- O2 real task produces a route: verified for this repository reset;
- O3 capability lifecycle: planned;
- O4 fresh continuation: planned;
- O5 bounded cleanup: verified;
- G1-G4: passing after active-surface cutover.

This is `3/5` product outcomes, not release acceptance.

## First checks in a continuation

```powershell
git branch --show-current
git status --short --branch
git rev-parse HEAD
git rev-parse --abbrev-ref --symbolic-full-name '@{u}'
git rev-list --left-right --count 'HEAD...@{u}'
python -B -m harness verify --root . --json
```

## Next bounded action

Finish only the active reset increment: eliminate active predecessor identity
and path matches, run product tests and the public verifier, review the diff,
then commit and push. Do not start the planned O3 or O4 increment in the same
slice.

## Claim boundary

A passing reset proves only that current product control is internally
consistent and independently identified. It does not prove O3, O4, cross-host
behavior, production readiness, release readiness, or broad user value.
