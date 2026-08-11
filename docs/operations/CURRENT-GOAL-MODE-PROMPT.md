# Current Goal-Mode Prompt

## Current state

The v0.2 product program is `paused` with `no active increment`: O1-O5 false
(`0/5`), G1-G4 true (`4/4`), and completion is `in-progress`.
This pauses outcome-bearing experimentation; it does not require runtime goal
mode or all Agent-owned work to remain idle.

The guardrail-only `increment.v0.2-causal-authority-reset` and
`work.bind-v0.2-outcomes-and-neutral-kernel` closed after their implementation
was committed and pushed at `a5a0834`. They mapped only to G1-G4 and count as
zero product progress.

## Why the program is paused

The next positive outcome evidence requires a natural, non-diagnostic real
task. The repository cannot invent that task merely to keep an increment
active, and the user must not be asked to manufacture one. This does not erase
historical failures: they remain non-authoritative counterevidence that may
falsify assumptions and trigger replanning.

## Agent-owned non-outcome progression

Without an invented user task, the Agent may perform bounded retrospective
counterexample analysis, portfolio curation, mechanism-only validation, and
authority-defect repair. These lanes have strict claim ceilings and count as
zero O1-O5 progress. They must start from an observed problem and finite stop,
not from an available tool, Skill, or interesting artifact.

## Next activation contract

Open exactly one causal increment only after a natural task is bound with:

- the user's goal and available inputs;
- relevant domain facts and accountable human acceptor;
- bounded authority, trust, data, cost, and side-effect limits;
- a pre-registered scenario/complexity/risk band and ad-hoc baseline rule;
- task-quality, evidence, cleanup, and claim floors;
- a finite falsifier, process-loss stop, and residue boundary.

The first outcome-bearing slice should freeze the smallest provisional event
protocol needed for that same task, then execute the task as one vertical O1
falsification slice. Protocol writing by itself is not product progress.

## Capability influence boundary

`AGENTS.md` is execution guidance only. Skills and Hooks are advisory inputs;
self-authored Skills are replaceable host projections; the peripheral ecosystem
is a replaceable capability input. None can create product direction, causal
work, authority, evidence promotion, acceptance, or release state. Bound user
intent and the three current product-authority files win. Reject or downgrade
a route that conflicts with them or creates process loss disproportionate to
the task.

## Closed boundaries

While paused, there is no active authority to run A/B tasks, mutate CC Switch
or a consumer, install or enable capabilities, connect accounts/OAuth, execute
a third-party candidate, activate a Hook, incur new cost, publish, release,
deploy, or open a new trust/data boundary.

Historical v0.1 evidence remains reproducible at `be498f9` but is inactive as
product, acceptance, runtime, and release authority. It remains usable as
retrospective counterevidence and replanning input.
The accepted v0.1 repository-control milestone and the v0.2 authority reset do
not prove task behavior, burden reduction, software-engineering standards,
cross-host portability, production, or publication.

## Required checks

```powershell
git status --short --branch
python -B -m harness verify --root . --json
python -B -m unittest discover -s tests/product -v
git diff --check
```
