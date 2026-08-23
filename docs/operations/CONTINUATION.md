# Continuation

This file is navigation, not product authority. Recover live Git, remote and
product truth before continuing.

## Start

```powershell
git branch --show-current
git status --short
git rev-parse HEAD
git rev-parse origin/main
git rev-list --left-right --count HEAD...origin/main
python -B -m yiyuan_accord verify --root . --json
```

Then read, in order:

1. `product/constitution.json`
2. `product/program.json`
3. `product/acceptance.json`
4. `CONTEXT.md`
5. this file

## Current authority state

- Canonical identity: YIYUAN Accord / `yiyuan-accord` /
  `yiyuan_accord` / `https://github.com/yiheng8023/YIYUAN-Accord`.
- Active line: v2.0. `program.status` is `ready`; the sole increment, work item
  and four ordered work stages are retained as completed.
- All R1–R4 and Q1–Q4 assessments are `verified` by the live verifier. The
  fresh current-projection release sample contains six passes and one retained
  GT-07 failure; its exact exclusions are public in `docs/releases/v2.0.md`.
  The earlier GT-08 failure remains immutable historical counterevidence; the
  current rerun passed after resolving current official host guidance.
- Determine the first incomplete gate from live Git, the exact candidate's
  local checks, hosted results, task-time human authority and public release
  state. Never infer a live gate from this navigation file. A ready repository
  state grants no hosted, human or release authority.
- The immutable v1.2 revision is
  `6d857517455b6f3f86a4c9cbd79fc618febbbe00`. Its observations remain in Git
  history and must not be renamed or replayed as current evidence.
- The full project analysis and accepted lifecycle framework are retained under
  `research/reviews/` as high-weight, non-authoritative inputs.
- The shared human-AI collaboration shortfall corpus remains read-only in
  YIYUAN-CALIBRATION at revision
  `e060a08f05361cb4cc9a67be050236cdbbde1de5`.
- Separately governed user-level Skills are not release dependencies. Add or
  project one only for a reproduced residual gap with separate lifecycle
  authority.

## Strict v2.0 route

1. Complete the no-alias identity migration across authority, code, commands,
   projection packages, docs, tests, repository URLs and public metadata.
2. Make the generic verifier compute deterministic conformance directly; run
   both host checks, full regressions, residue and identity scans, and diff
   checks. Repository observations cannot self-attest these results.
3. Run the required Golden Tasks against the exact current projections. Keep
   each decision, material effect, human burden and cleanup disposition; a
   failed task remains failed and narrows the claim.
4. Mark criteria verified only from live-computed lanes and accepted behavior
   evidence, retain the completed increment, and commit one clean local candidate.
5. On that unchanged local SHA, directly run the canonical verifier, both host
   checks, full product tests, diff, identity, link, workflow and residue checks
   plus independent specification, implementation-robustness and
   standards-conformance review. Independently
   compare the publishable source bundle with original host/session records,
   and have one evaluator isolated from candidate-preparation context complete
   the README activation, confirmation and removal path from a clean state. The
   accountable user, a colleague or a second observation surface may execute
   this context-isolated, outcome-bound, identity-neutral internal usability
   sample. Resolve every P0/P1; only then push the same SHA.
6. Verify the unchanged pushed SHA on GitHub Actions for Linux, Windows and
   macOS plus ordinary Codex Cloud. Repository data cannot satisfy this gate.
7. Only then request a named accountable human decision for that exact SHA and
   complete claim ceiling. Do not write the decision into the candidate.
8. After authorization, create the lightweight `v2.0` tag and public release
   with no attached assets.
9. Directly verify the release and tag APIs, exact tracked release notes and
   zero-asset policy; clean task resources, verify zero residue and replay local
   checks before finite closeout.

Do not start a later gate early. Failure returns to the smallest affected prior
gate and invalidates later candidate-specific evidence. Reports, plans, tests,
commits, pushes, transitions, hosted passes and authorization are supporting
facts, not substitutes for the next effect or for completion.

## Continuity

No universal turn count, context size, token percentage or summary ratio
governs carrier transitions. Use reliable source-bound host signals when
available; otherwise record capacity as unknown and transition conservatively.
The Agent owns destination verification, reconciliation and source release.

## Checks

```powershell
python -B -m yiyuan_accord verify --root . --json
python -B -m yiyuan_accord host-check --adapter codex --root . --json
python -B -m yiyuan_accord host-check --adapter claude-code --root . --json
python -B -c "import json,sys,unittest; e=json.load(open('product/program.json',encoding='utf-8'))['complexityBudget']['minimumTestCount']; s=unittest.defaultTestLoader.discover('tests/product'); r=unittest.TextTestRunner(verbosity=2).run(s); sys.exit(not(r.wasSuccessful() and r.testsRun>=e and not r.skipped and not r.expectedFailures))"
git diff --check
```

A routine green local check is deterministic conformance only. The exact local
completion gate additionally requires the complete unchanged-candidate check
set and independent dual-axis review observed by the active goal carrier.
Before a handoff, record the exact checkout, upstream relation, dirty paths,
program and stage state, checks, residue, next external or human gate, and
source-carrier release state.
