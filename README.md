# Agent Autonomy Harness

[简体中文](README.zh-CN.md)

Agent Autonomy Harness is an open, Agent-neutral quality safety net for
human-Agent collaboration. It starts from the outcome the user actually wants,
fills only a demonstrated gap in native host behavior, and keeps human
authority, continuous correction, consequence-level verification, recovery
and cleanup in one loop.

It is not a universal Agent runtime, capability marketplace, model router,
identity or audit system, or context predictor. A release does not claim to
solve every human-AI collaboration problem.

## Why the project was reshaped

Roughly two months of real Codex-led trial and correction exposed systematic
failure modes in long-running Agent work: repair-by-addition, proof proxies,
historical evidence controlling the current product, topology and context
burden returning to the user, and local milestones being mistaken for
completion. v1.2 preserves those failures as portable standards and Golden
Tasks while removing generation-specific validators from the default path.
Exact history remains recoverable through Git.

The project-specific audit is preserved as the
[2026-08-20 refactor and evolution report](research/reviews/2026-08-20-agent-autonomy-harness-refactor-and-evolution-report.md).
The shared collaboration-shortfall research keeps unique custody in the
[fixed YIYUAN-CALIBRATION revision](https://github.com/yiheng8023/YIYUAN-CALIBRATION/tree/e060a08f05361cb4cc9a67be050236cdbbde1de5/common/human-ai-collaboration-shortfalls);
this repository references and admits its findings without copying the corpus.

## Portable kernel

| ID | Commitment |
| --- | --- |
| K1 | Goal First: keep one current, traceable goal and phase |
| K2 | Minimum Sufficient Route: native first and no-op when sufficient |
| K3 | Human Authority: preserve real judgment, authorization and veto |
| K4 | Continuous Reconciliation: compare intent, facts, effects and resources |
| K5 | Close the Loop: verify to the claim, recover, clean up and limit claims |

Two compact layers make the trial history immediately testable:

- H1–H10 host-admission standards cover conditional use of official guidance,
  capability over version, effective over declared behavior, first-class
  unknowns, drift, consequential verification, no user compensation, host/core
  separation and retirement.
- L1–L7 learned-failure standards cover outcome over process, subtraction before
  repeated repair, total complexity cost, progressive assurance, help and
  interference, threshold-neutral continuity and counterevidence without
  inherited proof.

## Current surface

- Three semantic authorities:
  [constitution](product/constitution.json),
  [program](product/program.json), and
  [acceptance](product/acceptance.json)
- One generic data-driven command, `python -B -m harness verify`, implemented by
  [control.py](harness/control.py) and the pure admission checks in
  [guardrails.py](harness/guardrails.py)
- Two runtime-free, Hook-free thin Skill projections:
  [Codex](plugins/agent-autonomy-harness-codex) and
  [Claude Code](plugins/agent-autonomy-harness-claude)
- Representative [Golden Tasks](evals/golden-tasks.json) that measure both help
  and interference

These two release projections are not copies of separately governed personal
or user-level governance Skills, and they do not require those Skills to be
installed or enabled. Consumer packages share the K/H/L semantics and lifecycle
boundary; host-required names, manifests and metadata intentionally remain
different. A user-level Skill stays unprojected unless a reproduced residual
gap and separate lifecycle authority justify it.

~~~powershell
python -B -m harness verify --root . --json
python -B -m harness host-check --adapter codex --root . --json
python -B -m harness host-check --adapter claude-code --root . --json
python -B -m unittest discover -s tests/product -v
~~~

host-check proves static projection admission only. It deliberately does not
turn Skill visibility, installation state or valid JSON into host-behavior
evidence. Exact-host Golden Task observations are required for that claim.

The first Codex GT-02 run made the distinction concrete: the Agent produced the
right bounded repository fix and preserved unrelated dirty state, but left two
undisclosed Python cache files. The exact task and Codex cleanup behavior remain
failed, including after one repeated same-purpose prompt repair. The Harness
passes only the narrower test of detecting, retaining and claim-limiting that
failure; evaluator cleanup cannot convert it into a host pass.

## Status and completion boundary

The global subtractive reshape defines a repository-ready v1.2 candidate:
R1–R4 and Q1–Q4 have direct bounded evidence, and readiness additionally
requires the exact Git checkout to be clean. The no-budget goal-mode objective
in [product/program.json](product/program.json) remains active through external
verification, authorization, release and cleanup. A ready repository and an
active host goal are compatible: neither is release or field-effect evidence.

A release-eligible candidate requires the active goal carrier to directly
verify the exact clean HEAD on GitHub Actions (Linux, Windows and macOS) plus
ordinary Codex Cloud, followed by named-human authorization of that same SHA,
claim ceiling, publication and release. After publication, the carrier reads
the public GitHub release and tag, checks the exact tracked release notes and
zero-attached-asset policy, cleans task resources and replays local validation.
None of these facts is a verifier input or repository state; the verifier
cannot mint an external gate. Broad field effectiveness, population-level burden
reduction, all-host equivalence and longitudinal outcomes remain continuing
post-release evidence lanes. They neither delay the bounded release
indefinitely nor become fabricated release claims.

The release procedure is strict and dependency ordered:

1. create and locally verify one clean repository candidate;
2. push it and directly observe every hosted result for the unchanged SHA;
3. only then ask the named accountable human for the exact release decision;
4. create the exact lightweight tag and public release without changing the
   candidate;
5. directly verify the live public surface, clean task resources and replay
   local validation.

No later gate starts early. A failure returns to the smallest affected earlier
gate; a plan, commit, push, hosted pass or authorization is not a later result.

The v1.2 representative sample is GT-01, GT-02 and GT-07. A failed sample task
blocks the exact host-behavior qualification, but does not automatically make
the evaluation product nonconformant when the failure remains failed, its
residue disposition is explicit, and the release claim excludes that behavior.

Completion is a maintainable open-source baseline, not the end of learning.
Later evidence can add a Golden Task, narrow a claim, simplify or retire a
projection, or open one new bounded increment.

## Contributing

Describe the goal, problem or observation directly; contributors do not need to
learn Harness terminology, tools or topology first. Maintainers and their
Agents own mapping, minimum-route selection, verification and cleanup. See
[CONTRIBUTING.md](CONTRIBUTING.md), [SECURITY.md](SECURITY.md), and the
[history boundary](docs/operations/HISTORY.md).
