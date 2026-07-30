# Self-authored control-chain factorial ablation protocol — 2026-07-28

## Decision

The next comparison is preregistered as a two-factor experiment. It separates:

1. native hard-only behavior from the exact current
   `intent-contract -> capability-router -> closure-contract` candidate chain;
2. Hook `off` from the currently observed candidate Hook `auto` behavior.

This record starts no model turn and changes no Skill, Hook, CC Switch, global
configuration, repository cleanup state, commit, or remote. The current live
Hook registration is a dated identity source only. Any future `off` treatment
must use a disposable isolated profile or a parent-controlled equivalent; it
must not edit the user's live Hook configuration.

## Why the factors are independent

The current carrier audit found exact rule overlap between global hard
standards and the three Skill bodies, duplicate Skill visibility across two
roots, and a registered advisory Hook that emits routing context before a
prompt. A correct response can therefore be caused by the hard baseline, the
scenario-relevant Skill, the Hook reminder, or their interaction.

The four frozen cells are:

| Cell | Chain | Hook |
| --- | --- | --- |
| `CHAIN-HARD-HOOK-OFF` | hard-only | off |
| `CHAIN-HARD-HOOK-AUTO` | hard-only | auto |
| `CHAIN-EXACT-HOOK-OFF` | exact current three-Skill exposure | off |
| `CHAIN-EXACT-HOOK-AUTO` | exact current three-Skill exposure | auto |

All cells keep mandatory hard standards active. Their success is never
credited as treatment value.

## Reused scenarios

No new scenario family or generic runner is introduced. The protocol reuses:

- `INT-AMB-01`, where only `intent-contract` is scenario-relevant;
- `ROUTE-MIN-01`, where only `capability-router` is scenario-relevant;
- `CLOSE-PRESS-01`, where only `closure-contract` is
  scenario-relevant.

The exact-chain cells expose all three pinned Skill bodies task-scoped, but
invocation credit requires a parent-observed loader event for the
scenario-relevant Skill. Loading unrelated Skills cannot be counted as value.
The hard-only cells allow neither Skill payloads nor Skill loader events.

Exact-chain identity includes five files: the three `SKILL.md` bodies plus
`intent-contract/references/intake-contract.md` and
`capability-router/references/routing-contract.md`. Body-only projection is
not dependency-complete and is ineligible for the four-cell exposure gate.

## Measurement and attribution

Each scenario-cell requires three independent valid runs, for 36 valid runs
across the complete factorial. Run, task, host-run, and host-thread identities
must differ. Within a paired block, the packet, private oracle, requested
model, sandbox, authority envelope, and repository baseline stay fixed.

The parent must preserve:

- actual model and reasoning route;
- public packet and private-oracle digests;
- task-scoped exposure and scenario-relevant loader events;
- Hook mode, trigger event, raw added context, digest, bytes, and latency;
- raw response bytes and digest;
- hard-oracle verdict;
- capability calls, authority outcomes, and repository truth.

Hard-oracle outcome, authority errors, unnecessary questions or capability
calls, context bytes, Hook latency, end-to-end latency, failure fallback, and
repeated-context invariant loss are reported separately. The chain main effect
is computed only across matched Hook levels; the Hook main effect is computed
only across matched chain levels; interaction is reported separately.

A Hook reminder cannot prove that a Skill loaded. Task-scoped Skill exposure
cannot prove invocation without a loader event. Passing the final hard oracle
does not erase process cost or repeated-context loss.

## Failure fallback

Before any live comparison, a separate zero-model failure probe must inject a
bounded Hook-handler failure in isolation. The request must continue with no
advisory context and with parent-visible failure evidence. That probe is not a
weak-model cell and cannot be credited as Hook value.

## Zero-model Hook-mode preflight

The isolated direct-handler preflight now passes without editing
`hooks.json`. It used `CAPABILITY_ROUTER_HOOK_MODE` as a parent-controlled
mode override:

- all three `off` observations emitted zero bytes;
- `auto` emitted the same 428-byte advisory for `INT-AMB-01` and
  `ROUTE-MIN-01`;
- `auto` emitted no advisory for `CLOSE-PRESS-01`, showing that Hook
  registration and Hook injection are distinct evidence;
- an invalid-JSON failure returned success with zero advisory bytes and
  parent-visible debug evidence;
- registration, handler, and policy identities remained pinned, and the live
  registration digest was unchanged before and after.

The durable report is
[`audits/human-ai-collaboration-self-authored-control-chain-hook-mode-preflight-2026-07-28/REPORT.json`](../../audits/human-ai-collaboration-self-authored-control-chain-hook-mode-preflight-2026-07-28/REPORT.json).
This proves the dated handler's isolated mode and failure behavior only. It
does not prove host consumption, stable latency, Skill loading, behavioral
value, or weak-Agent acceptance.

## Current gate

The protocol and four cells are frozen, but execution admission is not open.
The existing live-run evaluator predates the Hook factor and must not be
silently reused as if it could attribute Hook effects. A separate side-effect
free factorial adapter now validates all twelve scenario/cell contract
combinations and rejects hard-only contamination, missing relevant loader
events, Hook-mode drift, silent model substitution, hard-standard credit,
authority errors, and repository drift. Synthetic adapter fixtures never
receive live-host or weak-Agent credit.

The isolated Hook-mode and failure-fallback preflight also passes. The smallest
next step was task-scoped no-model exposure for the four cells.

That preflight now passes on Codex Desktop `0.145.0`. A five-file atomic
projection was loaded under an isolated strict-config `CODEX_HOME`. The four
cells exposed `0`, `0`, `3`, and `3` configurable Skills, while the direct
Hook-mode evidence emitted `0`, `428`, `0`, and `428` bytes respectively.
Default config, live Hook registration, projected bytes, and repository status
remained stable. The projection and isolated home were removed after evidence
capture. The durable report is
[`audits/human-ai-collaboration-self-authored-control-chain-four-cell-exposure-2026-07-28/REPORT.json`](../../audits/human-ai-collaboration-self-authored-control-chain-four-cell-exposure-2026-07-28/REPORT.json).

Two rejected startup attempts exposed probe defects rather than candidate
failures: an isolated empty home cannot receive incomplete
`mcp_servers.*.enabled=false` tables, and an atomic staging manifest must point
to final rather than staging Skill paths. Both defects are fault-tested. The
remaining gate is an independent scenario-relevant Skill loader event and
host Hook-consumption surface. Without that evidence, a weak-model turn would
still be attribution-invalid. The requested `gpt-5.3-codex-spark` / `low`
route remains mandatory if a later live run is separately admitted; silent
route substitution remains invalid.

The dated
[`loader and Hook observability admission`](HUMAN-AI-COLLABORATION-SELF-AUTHORED-CONTROL-CHAIN-LOADER-HOOK-OBSERVABILITY-ADMISSION-2026-07-28.md)
now confirms that current app-server `0.145.0` cannot satisfy that frozen gate.
`skills/changed` is a file-watch invalidation signal, not a task-bound loader
event. `hook/started` and `hook/completed` can bind a Hook run to a thread and
turn, but observing them requires a turn and would still leave Skill
invocation unattributed. Model dispatch therefore remains zero. This is a
current-host observability constraint, not a candidate or code-stack failure.

The next gate is either a future host with an independent task-bound Skill
loader identity or digest event, or a separate owner decision to weaken the
frozen attribution acceptance boundary to behavior association. This protocol
does not authorize the latter.

No result from this protocol directly authorizes installing, updating,
replacing, retiring, or deleting a Skill; changing CC Switch or the live Hook;
cleaning retained artifacts; committing; pushing; or declaring program
closeout.

The machine-readable authority is
[`registry/human-ai-collaboration-self-authored-control-chain-factorial-ablation-protocol-2026-07-28.json`](../../registry/human-ai-collaboration-self-authored-control-chain-factorial-ablation-protocol-2026-07-28.json).
