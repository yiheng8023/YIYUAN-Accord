# Continuation

This file is navigation, not product authority. Recover live Git and product
truth before continuing.

## Start

~~~powershell
git branch --show-current
git status --short
git rev-parse HEAD
git rev-parse origin/main
git rev-list --left-right --count main...origin/main
python -B -m harness verify --root . --json
~~~

Read product/constitution.json, product/program.json and
product/acceptance.json. The current program contains one active global
reshape-and-release increment and one active work item.

## Current boundary

- The pre-reshape reference is
  534a77aae9e1d191173e6e05b4327c80d22855d8.
- Historical O1–O5 validators, registrations and evidence are not current
  authority or active proof. Retrieve them from Git only for a named
  counterexample; do not restore a generation wholesale.
- The project-specific 2026-08-20 audit is preserved under research/reviews.
- The shared human-AI shortfall corpus remains read-only at
  YIYUAN-CALIBRATION revision e060a08f05361cb4cc9a67be050236cdbbde1de5.
- The replacement goal-mode objective is prepared in program.goalModePrompt.
  The previous host goal is paused; do not claim that repository mutation
  resumed or replaced it.
- On 2026-08-20, the authenticated Codex CLI account returned zero cloud
  environments. A later in-app-browser refresh confirmed a Pro login and a
  reachable Codex Cloud workbench, but no repository or executable environment
  was visible; the settings route remained blank with frontend/network timeout
  errors. No cloud task, repository connection or environment mutation
  occurred. Treat workbench reachability and executable-environment readiness
  as separate gates and refresh them before a cloud run.
- Claude Code 2.1.237 passed strict plugin and Skill package validation. Its
  native `plugin eval` surface reported early access on this account, so no
  Claude behavior result has been claimed.
- Codex GT-01 and GT-07 are candidate passes awaiting human review. GT-02
  remains failed: its bounded fix and preservation of unrelated dirty state
  succeeded, but it left two undisclosed Python cache files; one minimal
  same-purpose Skill repair repeated the failure and was removed. Do not add
  another prompt layer or promote evaluator cleanup into a pass.
- The finite v1.2 representative sample is GT-01, GT-02 and GT-07. Retain all
  three observations. GT-02 blocks Codex cleanup-behavior qualification; it
  does not block the narrower Harness evaluation claim if the failure remains
  visible, current evidence is projection-bound and the release claim excludes
  that behavior.

## Current release path

1. Finish authority, generic verifier, documentation and projection
   consistency.
2. Run static contract, both host-admission checks and product tests.
3. Review the finite GT-01/GT-02/GT-07 observations and refresh Codex Cloud only
   if an exact executable environment becomes available. Keep Cloud, local
   Codex and Claude as distinct exact-host lanes.
4. Reconcile findings. One same-purpose failure causes replan and subtraction
   review, not another validator generation; a failed task narrows the host
   claim instead of being erased or forcing an unrelated product failure.
5. Prepare a clean candidate, security/privacy/residue review and exact claim
   ceiling.
6. Request named-human authorization for that exact candidate, publication and
   release. Only then create and verify the release.

No universal turn count, context size, token percentage or summary ratio
governs carrier transitions. Use reliable source-bound host signals when
available; otherwise record unknown and transition conservatively. The Agent
owns destination verification, reconciliation and source release.

## Checks

~~~powershell
python -B -m harness verify --root . --json
python -B -m harness host-check --adapter codex --root . --json
python -B -m harness host-check --adapter claude-code --root . --json
python -B -m unittest discover -s tests/product -v
git diff --check
~~~

A green check is deterministic conformance, not field value or release. Before
handoff, record the exact checkout, dirty files, program state, checks, residue,
remaining human gate and source-carrier release state.
