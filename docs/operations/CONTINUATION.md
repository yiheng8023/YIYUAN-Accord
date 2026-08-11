# Continuation

Updated: 2026-08-12

This is a navigation aid. Recheck live Git truth and the three product
authority files before acting.

## Current authority and state

- `product/constitution.json`
- `product/program.json`
- `product/acceptance.json`
- `docs/operations/CURRENT-GOAL-MODE-PROMPT.md` as a human-readable projection

The machine program is v0.2 and `paused`, with `no active increment` and no
active work item. The public verifier should report:

- release `v0.2`;
- completion `in-progress`;
- O1-O5 false (`0/5` outcomes);
- G1-G4 true (`4/4` guardrails);
- no active increment.

## What closed

The guardrail-only causal-authority reset was committed and pushed at
`a5a0834`. It:

- bound v0.2 to the terminal user-burden proposition;
- froze v0.1 at `be498f9` as historical repository-control evidence;
- replaced historical-event-specific current authority with a smaller
  historical-event-neutral fail-closed control seam;
- reconciled the README, North Star, research plan, architecture, acceptance,
  program, and continuation surfaces;
- left O1-O5 planned and false;
- did not change CC Switch, Skills, Hooks, consumers, accounts, or capability
  activation.

The reset removed 4,844 net lines from its 13-file candidate and reduced the
control-plus-product-test surface from 260,917 bytes at v0.1 to about 73 KB.
These are debt and maintainability results, not product outcomes.

## Why the program is paused

The next evidence-bearing increment requires a natural, non-diagnostic real
task. No such task is invented by the repository, and the next dogfood/A-B
increment is not automatically active merely because the reset closed.

Historical evidence under `product/evidence` and in Git is inactive. Do not
replay the old O3 lifecycle attempts or restore their validators as current
code.

## Next causal slice

When a natural task is bound, open exactly one outcome-bearing increment. For
that same task, first freeze only the provisional event taxonomy, baseline
matching, scenario/complexity/risk band, accountable acceptance fields, task
floors, claim boundary, process-loss stop, and exact cleanup paths needed to
evaluate it. Then run one vertical Codex reference-host O1 falsification slice.

The user supplies the goal, domain facts, bounded authority, corrections, and
accountable final judgment—not Skill names, tool selection, setup, recovery,
verification commands, cleanup commands, or push instructions. Compare only
decision-relevant routes; do not run a full Cartesian experiment.

Record task outcome, material user tool-orchestration interventions, repeated
fact/authority requests, route changes, failure and recovery, time/call cost,
claim limits, and residue. A repeated process-loss class stops the slice.
Capability addition is allowed when a reproducible residual gap survives
comparison; subtraction is not a veto.

## Paused boundary

With no active increment, do not run A/B tasks, mutate CC Switch or a consumer,
install or enable capabilities, connect accounts, execute a third-party
candidate, activate a Hook, incur new cost, publish, release, deploy, or open a
new trust/data boundary.

## First checks

```powershell
git branch --show-current
git status --short --branch
git rev-parse HEAD
git for-each-ref --format='%(upstream:short)' refs/heads/main
git rev-list --left-right --count HEAD...origin/main
python -B -m harness verify --root . --json
```
