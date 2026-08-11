# Current Goal-Mode Prompt

## Goal

Open v0.2 by binding the terminal burden-transfer proposition to measurable
acceptance and replacing v0.1 event-specific current authority with a small
historical-event-neutral, fail-closed product-control seam.

## Current causal increment

`increment.v0.2-causal-authority-reset`

Observed problem: v0.1 is an honest but narrow repository-control milestone;
its acceptance does not prove reduced user tool-learning burden, the required
strategy text still describes O3 as open, and the current verifier/test surface
hard-codes historical one-off events at greater cost than the reusable core.

Hypothesis: freeze v0.1 at `be498f9`, make v0.2 measure the terminal
proposition, and keep only historical-event-neutral structural, authority, evidence, and
process-loss checks as current code.

Falsifier: self-declared evidence can pass, historical evidence stays current
authority, strategy still contradicts machine state, the control surface grows,
or capability experiments/mutations start before this reset closes.

## Current work item

`work.bind-v0.2-outcomes-and-neutral-kernel`

It maps only to G1-G4 and counts as zero product progress. Its allowed operations are repository read/edit,
causal planning, local verification, progress accounting, commit, and push.

## Process-loss budget

- stop before the same user-correction class recurs;
- allow exactly one explicit guardrail-only reset work item and count it as
  zero product progress;
- require zero material user tool-orchestration interventions in this reset;
- stop on authority/irreversible incident or unbounded residue;
- require `.tmp`, `harness/__pycache__`, and `tests/product/__pycache__` absent.

## Closed boundaries

This increment does not authorize CC Switch or consumer mutation, capability
installation or enablement, account/OAuth connection, third-party execution,
Hook activation, paid service use, release tagging, package publication,
deployment, or a new trust/data boundary.

## Stop condition

The public verifier reports v0.2 `in-progress`, O1-O5 false, and G1-G4 true;
current explanatory documents agree; the historical-event-neutral control plus
product tests are materially smaller than the v0.1 baseline; local verification
passes; declared residue is absent; and the change is committed and pushed.

The next dogfood/A-B increment is not automatically active. It must be bound
after this stop condition is reached.

## Required checks

```powershell
git status --short --branch
python -B -m harness verify --root . --json
python -B -m unittest discover -s tests/product -v
git diff --check
```
