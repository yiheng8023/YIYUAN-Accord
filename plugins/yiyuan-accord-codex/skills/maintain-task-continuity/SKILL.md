---
name: maintain-task-continuity
description: Preserve task state through context pressure, interruption, reconnect, user-selected mode changes and handoff. Use before large reads or long work, on material context changes, or when recovery and unfinished-state protection are needed.
---

# Maintain task continuity

Use current goal and authority. If coordination duties are absent, read the
[brief entry](../deliver-demand-driven-outcome/SKILL.md); reach specialists as needed.

## Modes and saved task state

Honor the user's mode choice and host limits; reconcile goals, pauses, budgets
and unfinished work after changes. Permission and collaboration modes differ.
Ordinary continuation enables no Plan/Goal or new goal, resets no budget and
lifts no pause. Complete achieved Goals through their lifecycle; plans are revisable.

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
For checkpoint changes, use `manage_task_state` with current authority and the
inspected epoch/revision. Retain input baselines, output predicates, pauses and
unmet work; supply required revision reasons and dispositions.
At rebind or recovery, align `result` with the authorized outcome and scope;
put progress in `nextAction`, unmet conditions and sourced results.
Retire only state whose responsibilities are resolved or explicitly cancelled.
Reasons and local file matches do not prove user permission or whole-task completion.
Honor access, disabled components and denials; inspect effects before retry.
For reads without MCP execution observation, trusted compatible helper
`status`/`read-native-input` (`--help`) proves no MCP identity/version.
Replay and lock recovery stay separate.

`canContinue` records whether concrete safe authorized work remains; it never
requests a new turn or dispatches work.
For necessary user/external input, use `false` and retain unmet conditions.
Active or unfinished is insufficient; `false` neither ends, cancels nor pauses
the task, and preserves later user input.

For truncated or damaged tool/file replies, recover the necessary missing spans
from the original source or a supported bounded continuation. Check the recovered
text before dependent effects; retain unaffected verified facts and leave only
unresolved dependencies on hold. A successful read or valid JSON is not proof
that instructions or evidence arrived completely and without character loss.

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

Local Codex CLI, app and IDE clients share the Codex foundation and configuration;
app and IDE can continue the same project chat. Prefer supported same-task resume
or compaction when sufficient. A client switch alone needs no SDK transfer or new
controller. Check the actual thread, effective settings, pauses, pending effects
and writer before continuing; shared history alone grants no control or write right.
Reuse proven common behavior and check only consequential entry differences.

For necessary fresh targets or recovery, read the
[native handoff interface](../deliver-demand-driven-outcome/references/native-handoff.md)
before dependent effects. It distinguishes ordinary root MCP execution, requiring
current input, scoped quiescence and independent review, from an owned App Server
controller. The owner supplies transport, writer ownership, verification, timing
and recovery. Verify supported control within current authority; installation gives
no control of existing Desktop/IDE tasks. Connection and source-tool registration
are separate. Discovery is read-only; queueing messages or starting shared
infrastructure needs bound authority. Preserve unrelated clients and requests.

Keep the bound checkout unless transfer is authorized. Quiesce transferred writes,
rebind the exact destination's authority, paths and state, and keep recovery until
it has inspected the handoff and demonstrated safe continuation or the required
pause. A summary or receipt alone is not takeover. Commit to one writer for shared
effects; independent work may continue. Parent release may terminate descendants,
so verify the successor and its required support can survive release. After target
effects begin, reconcile them before rollback to avoid duplication. Handoff grants
no archiving authority. Source and destination must respect user-selected budgets
and pauses throughout.
