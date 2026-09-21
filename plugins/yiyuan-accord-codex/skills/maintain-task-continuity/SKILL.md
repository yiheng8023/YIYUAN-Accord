---
name: maintain-task-continuity
description: Preserve task state through context pressure, interruption, reconnect, user-selected mode changes and handoff. Use before large reads or long work, on material context changes, or when recovery and unfinished-state protection are needed.
---

# Maintain task continuity

Use the current goal and authority. If Accord's coordination duties are absent,
read the [brief entry](../deliver-demand-driven-outcome/SKILL.md). Invoke other
specialists only for an actual dependency; this Skill grants no new authority.

## Modes and saved task state

Preserve the user's explicit mode choice and actual host constraints. Reconcile
changed modes with the latest goal, pauses, budget and unfinished work; permission
mode is not collaboration mode. Ordinary continuation does not enable Plan/Goal,
create a new goal, reset its budget or lift a pause. A genuinely achieved Goal may
be completed through its normal lifecycle. Task plans remain revisable artifacts.

When mode state matters, use the host's read-only Goal query (`get_goal` or
`thread/goal/get` on an existing owned connection), independently of collaboration
mode. Bind task and time: null is absence at that read only; unavailable or failed
reads stay unknown. Preserve status, budget and unfinished work; do not enable a
mode to observe it.

Use sufficient native state. Bind a file checkpoint when input freshness,
unfinished-work recovery or completion needs protection the host does not supply;
file creation alone is not a trigger. Honor existing bindings and pauses, and
reconcile current input, effects and authority before revising or resuming them.
When the host exposes `inspect_task_state`, use it for read-only inspection of
the existing root-session checkpoint at an explicit workspace. Call identity
comes from host MCP metadata; the workspace remains caller-selected. Missing
metadata/state or a descendant's shared session remains unavailable, not adopted
parent state. The host owns this stdio process; no control connection is created.
For long work or a continuity decision, request `includeContext: true` to join
Hook-bound counters with current call identity. `recordedHostVersion` belongs to
the old session header; use the separately sourced current conditions. Unknown
or changed input, turn, model or version holds dependent assessment. Ordinary
status reads omit this additional file read.
`contextMaxAgeMs` can bind an age limit appropriate to the actual work; retain the
original sample time and account for the unobserved tail. A larger limit alone
does not make old evidence current or allow a transfer.
Use current helper `--help` from the plugin root for other status, binding, revision,
`unresolved`, pause and retirement; readback or file matches do not grant authority.
Retain known unmet conditions until evidenced resolution or authorized cancellation.

For missing captured input, use an available `read_task_input` tool or the helper's
`read-native-input`. Both expose only captured input, not complete history,
attachments or progress. The MCP tool binds identity from the native call; pass
its returned `next` cursor, including `expectedReceiptEpoch`, for subsequent pages.
On a changed basis, reconcile the new receipt and needed text instead of combining
pages. Preserve reported input-loss, resume and interruption flags; reading clears
none of them. Replay only the actual current input through the helper using the
recovery token from status when required; never reconstruct it from a checkpoint or hash.
Prove dead ownership before lock recovery, preserving other sessions and failure
watermarks. Unavailable or incompatible storage leaves freshness unknown and holds
dependent effects; use a surviving authorized host recovery path. Helper state is
local evidence, not a semantic verifier, permission barrier or autonomous executor.

## Interruptions and changed surroundings

A lost connection does not establish whether an operation stopped or succeeded.
Retain action identity and inspect the actual target to distinguish not dispatched,
in flight, applied, verified and unknown effects. Use supported queries or
idempotency before retry or compensation; a missing receipt is not retry permission.
Reconcile current authority, pauses and the responsible writer before proceeding.

New tools, extensions, settings or external actors can change shared resources,
outputs or credentials during an interruption. Recheck affected dependencies,
compatibility and ownership even when Accord did not cause the change. Preserve
unrelated user components and unresolved conflicts; old state cannot override them.
Confirm a live authorized actor can resume through a supported startup/reconnect
route. Saved files do not wake execution, and normal restart survival does not
prove power-loss or remote-effect durability.

## Context capacity and handoff

Before large reads or long work, use available native signals and sourced forecasts
to reserve verification, handoff, takeover and failure-recovery capacity. Distinguish
current occupancy, cumulative usage, configured window and compaction threshold.
Unknown signals require smaller useful spans and earlier state preservation, not
guessed percentages. Reassess material host/model/context changes and stale signals.
For an actual gap, `observe-context` reads the Hook-bound transcript; `assess-context`
with `nativeContext: true` re-reads counters with sourced tail/work/reserve forecasts.
App Server callers may supply bound signals through `--context-signals`. These
operations provide evidence and advisory arithmetic, not dispatch or permission.
On an owned App Server source that exposes `accord_inspect_context`, use that
read-only native-call route for needed signals. It may be unknown before the
first usage event; preserve state and choose a smaller justified next step instead
of polling unchanged evidence. Arguments cannot choose another thread or model.

Choose supported compaction, same-task renewal or a fresh task by the needed effect;
context-copying forks serve causal branches. Before history can be omitted, retain
the goal, authority and pauses, verified results with source references, observed
or unknown effects and unfinished work. On recovery, reuse valid results, reconcile
loss and inspect the next necessary source. Repeated reads or renewals without
progress call for changing the work unit, representation or permitted topology.

For a fresh-task transfer or its unresolved effects through an owned App Server controller, read the
[native handoff interface](../deliver-demand-driven-outcome/references/native-handoff.md)
before integration. The adapter coordinates caller-supplied transport, durable
writer ownership and independent verification; the caller owns timing and recovery.
For other host surfaces, discover an applicable supported control path within
current authority. Installation alone supplies no Desktop/IDE control connection.
Use the reference's version-bound connection distinctions before attachment;
connection and source-tool registration are separate prerequisites.
Discovery is read-only: queueing messages or starting shared infrastructure
requires its own bound task authority. Preserve unrelated clients and requests.

Keep the bound checkout unless transfer is authorized. Quiesce transferred writes,
rebind the exact destination's authority, paths and state, and keep recovery until
it has inspected the handoff and demonstrated safe continuation or the required
pause. A summary or receipt alone is not takeover. Commit to one writer for shared
effects; independent work may continue. Parent release may terminate descendants,
so verify the successor and its required support can survive release. After target
effects begin, reconcile them before rollback to avoid duplication. Handoff grants
no archiving authority. Source and destination must respect user-selected budgets
and pauses throughout.
