---
name: maintain-task-continuity
description: Preserve task state through context pressure, interruption, reconnect, user-selected mode changes and handoff. Use before large reads or long work, on material context changes, or when recovery and unfinished-state protection are needed.
---

# Maintain task continuity

Use current goal and authority. If coordination duties are absent, read the
[brief entry](../deliver-demand-driven-outcome/SKILL.md); reach specialists as needed.

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
Use available `inspect_task_state` at an explicit workspace; identity comes from
native call metadata, not workspace selection. Missing state or a descendant's
shared session cannot establish ownership of the parent's checkpoint.
For long work or continuity, request `includeContext: true`. The old header's
`recordedHostVersion` is separate from current host conditions.
Its optional `contextAssessment` reuses `assess-context`: supply the prior epoch,
expectedRevision and contextGeneration, original observation/expiry times,
integrity evidence and sourced tail/work/handoff/recovery/safety estimates.
The helper consumes fresh counters; changed input, revision or generation requires
reassessment. A fit grants neither permission nor takeover. Choose `contextMaxAgeMs`
for the work without restamping evidence or ignoring the unobserved tail.
Default status reads omit context I/O; assessment uses existing short-lived locks
without changing saved task state or creating a control connection.
For necessary checkpoint changes, use available `manage_task_state` with the
inspected epoch/revision and current authority. `bind` preserves input baselines,
output predicates and unresolved work; revisions need the required reasons and
dispositions. Pauses survive binding unless an actual authorized resume is recorded.
Retire only state whose responsibilities are resolved or explicitly cancelled.
Reasons and local file matches do not prove user permission or whole-task completion.
Inspect uncertain effects before retry. Honor host approval; do not bypass denial.
If absent, use helper `--help`; replay and lock recovery stay separate.

Retrieve missing captured text through `read_task_input` or `read-native-input`;
these contain Hook inputs, not full history, attachments or progress. Pass each
returned `next` cursor with its `expectedReceiptEpoch`; reconcile changed receipts
instead of joining pages. Reading clears no input-loss, resume or interruption
flags. When required, replay only host-retained current input through the helper
using the status recovery token. A hash cannot reconstruct missing text.
Prove dead ownership before lock recovery; preserve other sessions and failure
watermarks. Missing/incompatible storage holds dependent effects until a surviving
authorized host route restores sufficient evidence.

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
