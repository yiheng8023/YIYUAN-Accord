# Current Goal-Mode Prompt

## Goal

Pass O4 on one real continuation event: preserve the current task contract so
a fresh receiver does not require the user to reconstruct material goal,
authority, causal-rationale, open-work, evidence, or cleanup facts.

## Current causal increment

`increment.context-continuity-product-slice`

Observed problem: long collaboration chains lose active goal, authority,
causal rationale, open work, evidence limits, and cleanup state, forcing the
user to repeat context or correct drift.

Hypothesis: a repository-anchored source packet plus a fresh receiver delta can
preserve those facts without promoting the packet over live repository truth.

Falsifier: the receiver needs the user to restate one material carried fact,
or treats the packet as current fact without rechecking the repository.

Stop condition: one real continuation event records zero material user
restatement items, an explicit receiver claim boundary, deterministic PASS,
commit, and push.

## Allowed work

- inspect current repository truth;
- edit the bound repository's O4 mechanism and evidence surfaces;
- create a bounded source packet and use an already-authorized fresh-receiver
  mechanism;
- run local deterministic verification;
- commit and push this bounded mainline increment.

## Not authorized by this increment

- capability installation, enablement, or portfolio activation;
- account connection or model dispatch;
- CC Switch or consumer mutation;
- release or publication;
- Git-history rewriting;
- unrelated workspace deletion;
- claiming O3 or v0.1 acceptance.

## Required checks

```powershell
git status --short --branch
python -B -m harness verify --root . --json
python -B scripts/verify.py
python -B -m unittest discover -s tests/product -v
```
