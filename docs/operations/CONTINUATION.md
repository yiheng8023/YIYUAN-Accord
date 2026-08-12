# Continuation

Updated: 2026-08-12

This is a navigation aid. Recheck live Git truth and the three product
authority files before acting.

## Current authority and state

- `product/constitution.json`
- `product/program.json`
- `product/acceptance.json`

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

The later capability-chain and asset-integrity baseline used six real Harness
threads as counterevidence. It bound capability-added goal, input, deliverable,
human-round-trip, authority, side-effect, and acceptance requirements as an O4
evaluation surface; removed raw v0.1 receipts from the current tree; retired a
duplicate goal-mode prompt and verifier wrapper; removed one-time predecessor
byte proxies and marker-only document parity; and closed mapping and residue
blind spots. These are evaluation and debt results, not verified O1-O5
outcomes. No consumer, Skill, Hook, account, or capability activation changed.

The outcome-operationalization baseline then closed a pre-experiment authority
defect: O1-O5 now declare structured sample units, code-owned sample floors and
comparison designs, pre-registration fields, required measures, pass rules,
falsifiers, and human authority. Generic outcome evidence must identify its
source, carry a named accountable human acceptance, report an accepted result,
declare claim limits, and still pass a criterion-specific code-owned validator.
This narrows evidence admission; it does not make an absent validator or absent
natural-task receipt valid. O1-O5 remain planned and false.

## Why the program is paused

The next positive outcome-bearing increment requires a natural,
non-diagnostic real task. No such task is invented by the repository or
requested from the user merely to keep the program active, and the next
dogfood/A-B increment is not automatically active merely because the reset
closed.

The pause is not a whole-program stop. The Agent may continue bounded
retrospective counterexample analysis, portfolio curation, mechanism-only
validation, and authority-defect repair without claiming O1-O5 progress.
Historical evidence in Git is inactive as product or acceptance authority, but
remains valid counterevidence and replanning input. Do not replay the old O3
lifecycle attempts or restore their validators as current code.

## Next causal slice

When a natural task is bound, open exactly one outcome-bearing increment. For
that same task, instantiate only the task-specific values required by the
existing operationalization contract: event taxonomy, applicable baseline
matching, scenario/complexity/risk band, accountable acceptance fields, task
floors, claim boundary, process-loss stop, and exact cleanup paths. Then run one
vertical Codex reference-host O1 falsification slice.

The user supplies the goal, domain facts, bounded authority, corrections, and
accountable final judgment—not Skill names, tool selection, setup, recovery,
verification commands, cleanup commands, or push instructions. Compare only
decision-relevant routes; do not run a full Cartesian experiment.

Record task outcome, material user tool-orchestration interventions, repeated
fact/authority requests, reopened settled decisions, unrequested artifacts,
capability-added requirements, route changes, failure and recovery, time/call
cost, claim limits, and residue. A repeated process-loss class stops the slice.
Capability addition is allowed when a reproducible residual gap survives
comparison; subtraction is not a veto.

Do not reopen a settled handoff decision without new counterevidence. Treat
`AGENTS.md` as execution guidance, Skills and Hooks as advisory inputs,
self-authored Skills as replaceable host projections, and the peripheral
ecosystem as replaceable capability input. None may create product direction,
causal work, authority, evidence promotion, acceptance, or release state.

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
