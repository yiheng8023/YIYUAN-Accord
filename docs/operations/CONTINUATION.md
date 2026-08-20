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
product/acceptance.json. The subtractive product increment is recorded as
completed-local-candidate; `program.status` is `ready`, `activeIncrement` is
null, all eight repository criteria are verified, and all four task-time
external completion gates remain unevaluated until observed outside the
repository in their declared order. `repositoryCandidateReady` is a live
checkout result: it remains false while WIP is dirty and becomes true only when
this exact contract is committed in a clean repository root.

## Current boundary

- The pre-reshape reference is
  534a77aae9e1d191173e6e05b4327c80d22855d8.
- Historical O1–O5 validators, registrations and evidence are not current
  authority or active proof. Retrieve them from Git only for a named
  counterexample; do not restore a generation wholesale.
- The project-specific 2026-08-20 audit is preserved under research/reviews.
- The shared human-AI shortfall corpus remains read-only at
  YIYUAN-CALIBRATION revision e060a08f05361cb4cc9a67be050236cdbbde1de5.
- Separately governed self-authored user Skills remain outside this release and
  under their own `codex-user-config` / CC Switch lifecycle. No reproduced
  residual gap currently justifies a Codex or Claude projection. The two
  Harness reference packages align K/H/L semantics and lifecycle boundaries,
  while host-required names, manifests and metadata intentionally differ.
- The exact no-budget objective in `program.goalModePrompt` was resumed in the
  current host task on 2026-08-20 after accountable user approval. Its state is
  `active-in-host`; this lifecycle event authorizes bounded continuation but
  does not prove a criterion, release or field outcome.
- On 2026-08-20, ordinary Codex Cloud was exercised through the authenticated
  account after the in-app browser login was refreshed. A read-only task on the
  remote `origin/main` baseline `534a77aae9e1d191173e6e05b4327c80d22855d8`
  ran in a clean temporary `work` branch with Python 3.14.4 and reproduced the
  canonical verifier as valid, incomplete and 0/8 verified. It created no diff
  and did not observe the unpublished local candidate. This is an ordinary
  Cloud execution lane, not Codex Security trusted access; keep remote-baseline
  evidence distinct from local-candidate or post-push hosted evidence.
- Revision `9f31f2c3a8418ac4b087b64c300e377617da5555` was then pushed to
  `origin/main`. GitHub Actions run `32387615663` passed on Linux, Windows and
  macOS. Ordinary Codex Cloud task
  `task_e_6a87206b8ab8832ba50676f967edf21b` independently matched that exact SHA,
  used Python 3.14.4, passed all four requested commands and 32/32 tests, kept
  the worktree clean and produced no diff. Its checkout had no Git remote, so
  local `git ls-remote` and GitHub establish origin/main identity while Cloud
  establishes exact-SHA reproducibility. This is a hosted route baseline, not
  evidence for a later final candidate.
- Claude Code 2.1.237 passed strict plugin and Skill package validation. Its
  native `plugin eval` surface reported early access on this account, so no
  Claude behavior result has been claimed.
- The accountable project human accepted the bounded GT-01 and GT-07 passes,
  static Codex/Claude admission only, and the retained GT-02 failure. GT-02
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

1. **Repository candidate:** align constitution, program, acceptance, goal
   prompt, evidence and derived docs; run both local Python versions, canonical,
   both host checks, complexity, privacy and residue checks; commit and push one
   clean candidate under the already granted push authority.
2. **Exact hosted verification:** after push, require unchanged-SHA GitHub
   Actions results on Linux, Windows and macOS plus an ordinary Codex Cloud
   no-diff reproduction. The active goal carrier records the exact locators,
   revision, result and limits in the task; the repository verifier does not
   accept a receipt for this gate.
3. **Exact human decision:** only after gate 2, present that SHA, the claim
   ceiling, retained GT-02 failure and continuing evidence lanes to a named
   accountable human. Repository state stays `request-prepared`; the decision
   remains task-bound and is never written into the candidate.
4. **Exact tagged release:** only after gates 2–3 are directly established may
   the goal carrier create the lightweight v1.2 tag and public release. The
   authorized candidate must not change and no attached assets are admitted.
5. **Live verification and cleanup:** directly read the public GitHub release
   and tag, verify the tracked release notes and zero-attached-asset policy,
   clean task-created resources, confirm repository/evaluator residue is absent
   and replay the local checks before closing the goal.

The dependency chain is strict. Do not start a later gate early. Any failure
returns to the smallest affected earlier gate, which creates a new candidate
and invalidates older candidate-specific hosted evidence and authorization.

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
# Also replay verify and unittest with an available Python 3.10 interpreter.
git diff --check
~~~

A green check is deterministic conformance, not hosted evidence, human
authority, field value or release. Before
handoff, record the exact checkout, dirty files, program state, checks, residue,
remaining human gate and source-carrier release state.
