# Repository-authored gap-fill gate

Date: 2026-08-06

Status: verified synthetic gate mechanism; no real candidate or execution

Machine-readable evidence:
[`../../registry/repository-authored-gap-fill-gate-2026-08-06.json`](../../registry/repository-authored-gap-fill-gate-2026-08-06.json)

## Decision

The repository now has a pure fail-closed admission seam for a future
repository-authored Skill or Hook candidate. A candidate is mechanism-eligible
only when all of these are present:

1. the repository-authored origin class;
2. no exemption for incumbent self-authored Skills, AGENTS carriers, or Hooks;
3. a reproduced, source-bound residual gap;
4. evidenced exhaustion of native/runtime, official/runtime, task-bound
   targeted discovery, reviewed maintained external, composition, non-Skill
   Harness, project-standard, and human-control routes;
5. repository-owned design provenance and license ownership;
6. security, portability, and overlap review;
7. passing tests; and
8. an owner approval receipt.

Even the complete synthetic fixture returns `executionAuthorized: false`.
Admission readiness and execution authority remain separate transitions.

## Verification

The public seam is
`scripts/evaluate_repository_authored_gap_fill_candidate.py`. It accepts one
structured candidate record and emits an ordered decision with blockers,
execution authority, and claim boundary. The repository record supplies one
declared-synthetic positive fixture and nineteen single-field failure
injections. Every mutation blocks with its expected reason.

The mechanism uses no model, Skill, Hook, Plugin, App, MCP, account, installer,
manager, consumer projection, or third-party payload. It creates no real task,
candidate body, executable path, or release object.

## Acceptance effect and limits

`acceptance.repository-authored-gap-fill-gate` advances from `planned` to
`verified` because the gate mechanism and its failure behavior are now
deterministic. `acceptance.residual-gap-proof` remains `partial`: the synthetic
fixture proves no real residual gap, candidate need, behavior, value,
portability, or production readiness.

The canonical program state is therefore 45 verified, 16 partial, and 0
planned criteria. Program closeout remains unavailable, and no installation,
enablement, manager or consumer mutation, model dispatch, acceptance outside
this gate, or goal-status mutation follows from this checkpoint.
