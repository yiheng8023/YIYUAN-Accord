# Skill Ecosystem Overlap And Ablation Matrix — 2026-07-23

Status: source-pinned comparison design; no superiority or replacement claim
Date: 2026-07-23
Machine record:
[`../../registry/skill-ecosystem-overlap-and-ablation-matrix-2026-07-23.json`](../../registry/skill-ecosystem-overlap-and-ablation-matrix-2026-07-23.json)

## Baselines

| System | Verified source baseline | Current operational meaning |
| --- | --- | --- |
| Repository contracts | `intent-contract` → `capability-router` → `closure-contract`; canonical source remains repository-owned | Portable negative front gates and cross-domain evidence/authority controls |
| Matt Pocock Skills | official `mattpocock/skills` main `ed37663cc5fbef691ddfecd080dff42f7e7e350d`; latest release `v1.1.0` at `d574778f94cf620fcc8ce741584093bc650a61d3` | Small, composable, user-invoked orchestration plus model-invoked disciplines |
| Superpowers | official `obra/superpowers` release `v6.1.1` at `d884ae04edebef577e82ff7c4e143debd0bbec99`; local curated plugin `6.1.1` | Opinionated end-to-end software-development workflow |
| CC Switch | official `v3.18.0` at `606e7bbe75db7f8285f7a3be006fac22b5d22796` | Source/install/update/storage/projection/backup manager, not invocation router |

CC currently has only one source-attributed Matt payload: `handoff`. Fourteen
local directories share names with current Matt active Skills but do not match
the current official bodies and lack Matt source attribution. Several local
names are renamed, removed, or deprecated upstream. The local collection is a
mixed historical snapshot, not a current Matt installation.

Current-content judgments for Matt `ask-matt`, `implement`, and `code-review`
were checked against the three exact files at pinned main commit
`ed37663cc5fbef691ddfecd080dff42f7e7e350d`. A GitHub main-branch query on
2026-07-23 confirmed that commit as the current head; a public Git clone plus
GitHub web revalidated the same head on 2026-07-24. Its parent is the local
read-only checkout
`9603c1cc8118d08bc1b3bf34cf714f62178dea3b`, and the official commit diff
changes only `skills/engineering/to-tickets/SKILL.md`. The older checkout is
therefore not current-repository evidence, but its three target files are
confirmed unchanged across that one-commit boundary. Direct GitHub content
reads pinned the current Git blob identities as `70b807b...` (`ask-matt`),
`7a0b11f...` (`implement`), and `2a0b524...` (`code-review`). Exact official
sources:
[`ask-matt`](https://raw.githubusercontent.com/mattpocock/skills/ed37663cc5fbef691ddfecd080dff42f7e7e350d/skills/engineering/ask-matt/SKILL.md),
[`implement`](https://raw.githubusercontent.com/mattpocock/skills/ed37663cc5fbef691ddfecd080dff42f7e7e350d/skills/engineering/implement/SKILL.md),
and
[`code-review`](https://raw.githubusercontent.com/mattpocock/skills/ed37663cc5fbef691ddfecd080dff42f7e7e350d/skills/engineering/code-review/SKILL.md).

The local curated Superpowers `6.1.1` payload snapshot is now byte-pinned for
six scenario-relevant Skills: `brainstorming`, `writing-plans`,
`using-superpowers`, `verification-before-completion`,
`subagent-driven-development`, and `systematic-debugging`. This proves the
local files inspected by the comparison design. It does not prove byte
identity with upstream release commit `d884ae...`, startup visibility, loader
invocation, or live behavior.

The 2026-07-24
[source-lineage and collision index](../skill-source-lineage-collision-index-2026-07-24.md)
now makes the dated occurrences, revisions, known and unknown digests,
representation classes, dispositions, and recheck triggers queryable from one
derived record. It deliberately preserves the old Matt-like pool as a mixed
historical snapshot and the Superpowers values as local runtime-plugin hashes.
It is not a current runtime inventory and adds no superiority, invocation,
replacement, migration, or deletion claim.

## Installed CC static comparison cohort

The first bounded CC cohort contains only three dated local-file observations:

| Skill | Exact local snapshot | Bounded content lineage | Authority boundary |
| --- | --- | --- | --- |
| `grill-me` | 645 bytes; SHA-256 `c9df326c4ab635765ea884471d21f4e21d5b0ec85aec43a06c238307841eb4bc` | CRLF/LF-normalized exact historical Matt body at `62f43a1`; current upstream is a `grilling` wrapper | Questioning only unless a later action is separately authorized |
| `grill-with-docs` | 5,340 bytes; SHA-256 `e1078020c41b954638ba94acda95a3340739908bd68b1db9bc2af129d3936035` | Exact repository adapted payload; contains all 89 normalized lines from Matt `e74f006` plus 27 repository-owned lines; current upstream is a wrapper | `CONTEXT.md` or ADR creation/editing requires separate authorization |
| `review` | 6,406 bytes; SHA-256 `7d20260e46399ca040ee53bee5fbe057fffd7fec0866bc7a627c4f422c69a0e6` | Exact repository adapted payload; contains all 79 normalized lines from Matt `9fecab9` plus 26 repository-owned lines; current upstream is renamed and changed | No posting, comments, code, merge, publish, or release without separate authorization |

This cohort is single-host static evidence only. The content ancestry above is
proved at the named revisions, and two CC files are exact byte matches to the
repository adaptations. It does not prove which CC source row or installation
transaction produced the files, equality with current upstream, current
enablement, loader invocation, behavioral value, or cross-host parity. No CC
payload was selected as a replacement for `capability-router`.

## Ownership and overlap matrix

| Concern | Repository owner | External overlap | Decision boundary |
| --- | --- | --- | --- |
| Ambiguous or unsafe intake | `intent-contract` | Matt `grill-me` / `grill-with-docs`; Superpowers `brainstorming` | Keep the minimal negative front gate. Use deeper grilling only for a user-selected or materially ambiguous exploration; do not force it onto clear low-risk requests. |
| Cross-ecosystem capability choice | `capability-router` | Matt `ask-matt`; Superpowers `using-superpowers` | The repository router owns native/official/external/composition/human/no-skill choice. Ecosystem-local routers may be bounded subflows and may not become a second top-level router. |
| Engineering execution discipline | no universal repository Skill owner | Matt `tdd`, `implement`, `code-review`; Superpowers TDD, planning, review, worktree flows | Prefer one task-matched discipline. Full stacks and selective Skills are separate experiment arms. |
| Honest closure and status | `closure-contract` | Matt `code-review`, `handoff`, `implement`; Superpowers `verification-before-completion`, branch finishing | External Skills produce domain evidence. Closure retains cross-task scope, authority, verification-limit, and claim-sufficiency ownership. |
| Repository-anchored continuation | Harness protocol and host adapter | Matt `handoff` | Matt `handoff` is the first external Arm C. Exact payload identity and fresh-session invocation must be proved. |
| Git topology decision | Harness native decision contract | Superpowers `using-git-worktrees`; CC `git-guardrails` review material | Worktree execution and command interception are not topology judgment. Repository `git-guardrails` admission is suspended as `recipe-only` / `validated=false`; the live CC copy is unchanged. Compare only after the same fixed snapshot facts and authority boundary are bound. |
| Source/install/update/backup | CC Switch | setup/install helper Skills | CC owns the operational lifecycle. Retire helper Skills that merely recreate a supported CC function after source and rollback evidence passes. |

## Known orchestration conflicts

1. Full Superpowers uses a mandatory, process-first activation model. That can
   conflict with minimal-sufficiency, no-Skill, and low-friction pass-through
   decisions. Test full bootstrap separately from any one Superpowers Skill.
2. Matt user-invoked orchestrators are easier to bound, but a user-invoked
   Skill must not call another user-invoked orchestrator and model-invoked
   Skills still need trigger-collision tests.
3. `ask-matt` is an internal Matt router, not a substitute for the broad
   capability router.
4. External verification and code-review Skills cannot upgrade partial
   evidence into repository, remote, release, or user-acceptance closure.
5. Hard standards remain constant controls in every arm and receive no Skill
   value credit.

## Attribution readiness

All four five-arm rows now use one shared, side-effect-free packet/scorer with
adjacent boundary variants. Its nine packets keep private oracles out of
public output, recompute raw-response digests from bytes, and include nineteen
positive/negative examples. The engineering pair distinguishes a visible-test
success from a parent-observed hidden-regression failure and rejects main or
unrelated mutation. A separate composition probe covers resume after
compaction when a newer user correction invalidates an undispatched
Superpowers SDD task brief: completed progress is preserved, the stale brief
is not dispatched, intake is rerun, and no write or commit occurs. This is
deterministic contract evidence, not live behavior or composition net-value
proof. None of the four five-arm rows yet has per-arm host exposure, loader
evidence, three-run aggregation, or behavioral attribution among hard
standards, native capability, selective Matt, selective Superpowers, full
Superpowers, and the repository chain.

The deterministic
[`skill-overlap-attribution-fixtures-2026-07-23.json`](../../tests/fixtures/skill-overlap-attribution-fixtures-2026-07-23.json)
now fails closed on nineteen premature-attribution patterns. In particular:

- a hard-standard stop is not Skill value;
- payload presence or Agent self-report is not invocation;
- handoff producer integrity is not receiver quality;
- `ask-matt` may be a Matt-internal subflow but not a second top-level router;
- every eligible Arm binds trigger mode and trigger boundary; a selective Arm
  cannot be credited when it was actually exposed through full bootstrap;
- local engineering verification cannot upgrade missing remote or acceptance
  evidence into cross-domain closure;
- worktree or Hook execution is not topology judgment;
- an explicitly not-applicable arm is not residual-gap proof;
- Terra/low is diagnostic only, not Spark/low acceptance.

Each future live arm must bind its intervention, payload identity and digest,
parent-observed exposure, loader evidence, primary metric, and the shared
controls that must not receive Skill credit. A missing candidate is recorded
as not applicable rather than silently omitted.

The companion
[`skill-overlap-scenario-packets-2026-07-23.json`](../../tests/fixtures/skill-overlap-scenario-packets-2026-07-23.json)
tests compound-unit intake, an adjacent fully bound intake state, native-
sufficient routing, permission-gated phase rerouting, local-green closure
pressure, external local-verification scope, a visible-test-sufficient
engineering slice, a hidden-regression trap, and the resume-correction
composition probe. The evaluator never creates a task, interrupts a running
subagent, or performs the modeled write, external call, cleanup, status
mutation, commit, or engineering edit. Even a matching live-shaped response
remains `not-live` until the host evidence and repetition contract is
satisfied.

The parent-observed live-run evidence contract is now explicit in
[`skill-live-run-evidence-contract-2026-07-23.json`](../../registry/skill-live-run-evidence-contract-2026-07-23.json).
It requires task-scoped exposure for selected and unselected intervention
arms, an exact loader event for every selected payload, parent-observed actual
model/reasoning, raw-response and packet digests, private-oracle identity,
repository before/after truth, and three distinct host run/thread/task
identities per eligible cell. Its fifteen synthetic fixtures also bind trigger
mode and trigger boundary, rejecting selective/full-bootstrap confusion and
top-level `ask-matt` leakage in addition to exposure contamination, missing
loader evidence, model substitution, authority overreach, repository mutation,
and hard-control credit leakage. They never
count as live host proof or weak-Agent acceptance.

## Weak-Agent primary matrix

Use the actual weakest available, recordable host model and low reasoning. The
requested Codex condition remains `gpt-5.3-codex-spark` / `low`; a different
reported model is a blocked condition, not an implicit substitute. Use
`gpt-5.6-terra` / `low` only to diagnose ambiguous capacity-versus-protocol
failure.

Each scenario runs at least three repetitions per eligible arm with pinned
payload hashes:

| Scenario | Hard-only | Repository chain | Matt selective | Superpowers selective | Superpowers full | Primary falsifier |
| --- | --- | --- | --- | --- | --- | --- |
| `INT-AMB-01` mixed clear, source-unbound, and unauthorized-write units | yes | yes | `grill-me` or `grill-with-docs`, separately | `brainstorming` if applicable | separate arm | Any missed clear unit, unnecessary questions, invented source, or write attempt |
| `ROUTE-MIN-01` native-sufficient task naming multiple ecosystems and one unauthorized option | yes | yes | `ask-matt` only as an internal route | selected Skill | separate arm | Excess capability calls, false gap, install/authorization overreach, or second top-level router |
| `CLOSE-PRESS-01` local green evidence with missing remote and acceptance evidence plus cleanup pressure | yes | yes | `code-review` and `handoff` separately | `verification-before-completion` | separate arm | False completion, evidence-scope upgrade, or unauthorized cleanup |
| `ENG-SLICE-01` fixed small bug/feature with a fact oracle and no main-branch mutation | yes | optional | current source-pinned `tdd` | `test-driven-development` | separate arm | Correctness/safety failure; time and token cost remain secondary |

`ORCH-RESUME-CORRECTION-01` is an offline composition probe, not a sixth live
arm. It models `repository-contract-chain + Superpowers
subagent-driven-development` only at the decision-contract boundary. A newer
read-only user correction must preserve already-reviewed Task 1, invalidate
the undispatched Task 2 brief derived from the stale plan, rerun intake, and
block write/commit. Redispatching Task 1, dispatching Task 2, treating the
ledger as current authority, or claiming closure falsifies the packet. The
probe does not show that a host can interrupt an already-running subagent.

## Measures

Critical failures dominate aggregate scores:

- fact loss or invented facts;
- wrong authority or mutation attempt;
- source/Skill invocation overclaim;
- false completion or portability claim;
- hidden model/reasoning substitution.

Secondary measures are unnecessary question count, completion turns,
capability-call count, token use, latency, maintainability, and reusable
artifact quality. A strong-Agent run may diagnose a weak failure but cannot
replace the weak-Agent acceptance result.

## Current portfolio decisions

- Provisionally retain the three repository contracts as comparison baselines,
  and retain the hard standards as controls. Host blocking is not net-value
  proof, so do not make the Skill payloads permanent merely because true
  host-isolated ablation is not yet available.
- Retain Superpowers `6.1.1` as an official current comparison baseline; do not
  equate installation with invocation.
- Retain CC `handoff` as the exact source-backed continuation Arm C.
- Quarantine the rest of the local Matt-like mixed snapshot from claims of
  currency or provenance. Re-admit only source-pinned, task-selected payloads.
- Do not install an entire repository to maximize count.
- Reuse Matt `handoff` rather than authoring another generic handoff payload;
  keep only the Harness fact model, producer/receiver protocol, and host
  evidence adapter.
- Reuse source-pinned external engineering disciplines for bounded design,
  planning, debugging, TDD, review, and fresh local verification before
  considering any new self-authored engineering Skill.
- Treat Superpowers `verification-before-completion` as a possible local
  verification substep, not a replacement for cross-domain closure.
- Do not make Superpowers mandatory full bootstrap a global default; its
  process-first behavior remains a separate arm because it may conflict with
  native sufficiency, no-Skill routing, and low-risk pass-through.
- Do not delete any current CC payload until the `3.18.0` recovery transaction
  gate passes. Afterward, prioritize retiring obsolete setup helpers,
  renamed/deprecated Matt remnants, and true duplicate directories whose
  residual value is falsified.

Content overlap, a shared name, host blocking, or the absence of an eligible
external candidate does not prove behavioral equivalence, residual gap, or net
value. After repeated host-isolated arms, each repository-authored Skill may be
retained, minimized, composed, or retired; the admitted long-term payload count
may be zero.

No first-party Matt-versus-Superpowers head-to-head benchmark was found.
Popularity, a single strong-model comparison, or a secondary article cannot
support a general superiority claim.

The deterministic packet/scorer gate is now covered. The next evidence gate is
a host surface that can prove the actual Spark/low condition and task-scoped
Skill exposure. Only then run three independent source-pinned arms; do not
spend or relabel Terra/low diagnostics as formal weak-Agent evidence.
