# Continuation

Updated: 2026-08-13

This file is a navigation aid, not product authority or a history ledger.
Recheck live Git truth and the machine contract before acting. Closed changes
remain recoverable from Git and `docs/operations/HISTORY.md`; do not copy their
commit-by-commit narrative back here.

## Current authority and state

Read these files first:

- `product/constitution.json`
- `product/program.json`
- `product/acceptance.json`

The current machine program is v0.2 and `paused`. Its current increment graph
is empty. The public verifier should report:

- completion `in-progress`;
- O1-O5 false (`0/5` outcomes);
- G1-G4 true (`4/4` guardrails);
- no active increment.

If live Git or the verifier disagrees, investigate that evidence instead of
repairing this document first.

## Why the program is paused

O1-O5 require natural, non-diagnostic real-task evidence. The repository does
not invent such a task or ask the user to manufacture one merely to keep the
program active. The current release has only the criterion-scoped O1 receipt
validator; it does not create a natural task or prove naturalness. O2-O5 have
no code-owned validation path.

The pause does not block bounded retrospective counterexample analysis,
mechanism-only validation, authority-defect repair, or task-independent
portfolio curation. Such work must start from an observed problem, have a
finite stop, remain inside existing authority, and count as zero O1-O5
progress.

## Outcome-entry boundary

When a natural task is actually bound, do not open an outcome increment until
every mapped outcome has the necessary criterion-scoped code-owned validation
path. Then open exactly one causal increment with at most one active work item
and use the existing acceptance operationalization rather than creating a
parallel workflow.

The user supplies the goal, domain facts, bounded authorization, corrections,
and accountable final judgment. The Agent owns available-capability
observation, gap detection, source-bounded discovery when needed, route
selection, task-scoped dispatch and release, bounded execution, recovery,
verification, cleanup, and progress accounting. Do not transfer capability or
product names, discovery channels, invocation syntax, setup, verification
commands, cleanup commands, or push orchestration to the user.

Compare only decision-relevant routes. A capability may be discovered or added
only after a reproducible residual gap and its exact authority, trust, data,
cost, side-effect, rollback, and acceptance boundaries are known. Catalogs and
discovery channels are adaptive sources, not portable-core authority.
Installed or visible Skills, Hooks, Plugins, MCPs, Apps, memories, and consumer
projections cannot create work or promote evidence.

## Paused boundary

Without a bound task and its required authority, do not run outcome A/B work,
mutate CC Switch or another consumer, install or enable capabilities, connect
accounts, execute a third-party candidate, activate a Hook, incur cost,
publish, release, deploy, or open a new trust or data boundary.

## First checks

```powershell
git branch --show-current
git status --short --branch
git rev-parse HEAD
git for-each-ref --format='%(upstream:short)' refs/heads/main
git rev-list --left-right --count HEAD...origin/main
python -B -m harness verify --root . --json
python -B -m unittest discover -s tests/product -v
```
