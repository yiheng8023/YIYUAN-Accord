# Context Continuation PoC Evidence — 2026-07-19

Status: bounded single-host observation; `CTX-04` partial and `CTX-05` manual
path observed
Host: Codex Desktop, local host; companion CLI observed as `codex-cli 0.144.6`
(desktop build not exposed by this probe)
Repository: `C:/Projects/agent-autonomy-harness`
Repository HEAD at intake: `55659f30091990f7c589932e0379880de30dc403`

## Question

Can a user-authorized Codex project thread carry a repository-anchored handoff
into the same saved project and recover current repository truth without
replaying the old conversation?

This observation also asks what the same evidence does **not** prove about
automatic thread creation, lossless handoff, source-backed Skill invocation,
or cross-host portability.

## Bound identities

| Surface | Observed identity |
| --- | --- |
| Source thread | `019f65ee-2c62-77c3-9524-83924fca5364` |
| Source workspace | `C:/Projects/agent-skills-curated` |
| Source handoff turn | `019f75fa-a901-7e21-bd40-c929bc279226` |
| Destination thread | `019f75fd-2b84-75f3-98b3-461fb9895206` |
| Destination project ID | `772abb6d-eaf5-4d5b-829b-67c6b8a6a620` |
| Destination workspace | `C:/Projects/agent-autonomy-harness` |
| Destination branch/upstream at intake | `main` / `origin/main` |

The current Codex project list contains the destination project and the current
thread list binds the destination thread to the same repository path.

## Authority boundary

The source-thread user explicitly asked Codex to hand the task to the already
prepared workspace. The source thread then reported the created destination
thread ID. This is an explicit, user-authorized manual continuation path.

No new thread was created during this evidence capture. No project, thread,
host configuration, Skill, Hook, MCP, Plugin, account, Git branch, worktree,
commit, or remote was mutated by the probe.

## Native capability inventory

The observed runtime exposes native thread/project capabilities for:

- listing saved projects and recent threads;
- reading another thread's recent completed turns;
- creating a project or projectless thread;
- forking a thread in the same directory or a worktree;
- sending messages and waiting for background threads;
- handing another thread and its Git state between supported checkouts.

The current `create_thread` contract requires an explicit user request for a
new or background thread and a saved project ID for project-scoped work. The
current inventory exposes project listing but no project-registration action.
Therefore the observed native path supports user-authorized creation after
manual project registration; it is not evidence of autonomous registration or
automatic continuation.

For the prepared paired trial, the same current-host contract lists
`gpt-5.6-luna` and `gpt-5.3-codex-spark`, with `low` supported by both. This
supports a controlled ordinary/weak model pair when capacity attribution is
needed; it does not make both runs mandatory for every PoC.
The creation call must still validate the destination-host combination; tool
metadata alone is not an executed trial.

That July 19 Luna listing is historical host evidence. On July 23, the current
official subagent manual and callable spawn surface name `gpt-5.6-terra` as the
lightweight option. Future conditional diagnostics use Terra; the two labels
are not silently treated as equivalent.

## Current official-source check

A fresh Codex manual snapshot was fetched on 2026-07-19 after the native
inventory. It adds `recorded-static` evidence without upgrading any live-host
claim:

- [Codex App Server](https://learn.chatgpt.com/docs/app-server) documents
  conversation primitives including `thread/start`, `thread/resume`, and
  `thread/fork`, followed by `turn/start`; a client can also supply a `cwd` for
  a turn. This is an official integration surface for a future adapter, not a
  documented context-pressure trigger or proof that the current desktop app
  will create continuation threads automatically. The local `codex-cli 0.144.6`
  exposes `app-server`, but its help still labels the command experimental;
  transport/method maturity must be checked before relying on it.
- [Hooks](https://learn.chatgpt.com/docs/hooks) documents `PreCompact` and
  `PostCompact` events with `manual` and `auto` trigger values, plus
  `SessionStart` sources such as `resume`, `clear`, and `compact`. This proves
  that compaction events can be observable when supported hooks are configured;
  no Hook was configured or observed in this probe.
- [Advanced Configuration](https://learn.chatgpt.com/docs/config-file/config-advanced)
  documents opt-in OpenTelemetry events, including token counts on
  `response.completed`. It does not document a universal efficiency threshold
  or a built-in automatic continuation policy, and telemetry was not enabled
  by this probe.
- [Slash commands](https://learn.chatgpt.com/docs/developer-commands?surface=cli)
  documents the CLI `/compact` command as a manual way to summarize a long
  visible chat. This does not establish equivalent desktop automation.
- [Worktrees](https://learn.chatgpt.com/docs/environments/git-worktrees)
  defines Codex App Handoff as moving the same chat and Git state between Local
  and Worktree. That operation is distinct from starting a clean continuation
  thread with a repository-anchored delegation.

The official-source result changes the candidate inventory from “no known
surface” to “official primitives exist.” It does not change the observed
outcome: manual project-thread continuation is supported in this slice, while
automatic context-triggered continuation remains unproven.

## Local generated-protocol check

With separate user approval, the local `codex-cli 0.144.6` generated App
Server JSON schemas into bounded temporary directories, once without and once
with `--experimental`. The parent `codex app-server` command is still labelled
experimental, so schema presence is a runtime-owned static interface candidate,
not a maturity or desktop-exposure guarantee.

The non-`--experimental` bundle contains:

- `ThreadTokenUsageUpdatedNotification`, requiring `threadId`, `turnId`, and
  `tokenUsage`; its payload includes `last`, `total`, and an optional
  `modelContextWindow`, with input, cached-input, output, reasoning-output, and
  total-token breakdowns;
- deprecated `ContextCompactedNotification`, requiring `threadId` and
  `turnId`, with the schema directing clients to the `ContextCompaction` item
  type;
- `ThreadCompactStartParams`, requiring `threadId`, which is an explicit
  compaction actuation surface rather than an automatic new-thread policy;
- `ThreadStartParams`, `ThreadResumeParams`, and `ThreadForkParams`; start
  accepts `cwd`, model, approval, sandbox, and instruction settings, while the
  start-source enum is only `startup` or `clear`;
- `ThreadForkParams.lastTurnId`, which forks through an inclusive completed
  turn and therefore inherits history rather than creating a clean
  source-backed continuation.

The generated SHA-256 values for the three telemetry/compaction schema files
were:

| File | SHA-256 |
| --- | --- |
| `v2/ThreadTokenUsageUpdatedNotification.json` | `FE70A73653AE9E3FFFB0DB84D1312F47AC47D92526C2D44461492CD864ADA3AD` |
| `v2/ContextCompactedNotification.json` | `E0B92779009971631D385970CC0389D4F19E351466F84806DF36C29F4B9D5FFD` |
| `v2/ThreadCompactStartParams.json` | `A7C4395F60BDDD38C953CB9508A05D2082790DA7B3EB4EF7E4FB66CF15B92227` |

The generated bundles remain in
`C:/tmp/agent-autonomy-codex-app-server-schema-0.144.6-stable` and
`C:/tmp/agent-autonomy-codex-app-server-schema-0.144.6-experimental` during
this evidence phase. The current Agent tool surface did not expose these
notifications, and no live App Server client subscribed to them. Consequently
the probe upgrades `CTX-01`/`CTX-02` only to stronger `recorded-static`
evidence; it does not prove notification delivery, desktop integration,
automatic compaction quality, a best efficiency interval, or automatic thread
creation.

## Observation sequence

1. The user prepared and registered the destination workspace, then explicitly
   asked the source thread to hand off the task.
2. The source thread checked the destination project identity and reported
   creation of the destination thread.
3. The destination handoff bound five repository artifacts, expected Git
   posture, current product phase, three PoC lanes, open claims, authority
   limits, and the first matrix gate.
4. The destination thread read all five bound artifacts before action.
5. It independently checked branch, status, HEAD, upstream, ahead/behind,
   origin identity, local `origin/main`, and the live remote `main` SHA.
6. It verified that the project and destination thread now existed, while
   keeping the dated bootstrap handoff fields as historical rather than live
   host truth.
7. It did not replay the old conversation before producing the intake result.
8. The source thread was read only later, after the user authorized continuity
   lookup and the matrix selected this exact comparison scenario.

## Acceptance comparison

| Acceptance item | Result | Evidence limit |
| --- | --- | --- |
| Destination is a saved-project thread in the intended workspace | observed | One Codex Desktop/local-host observation only. |
| Thread creation followed explicit user authority | observed | The native approval-dialog surface was not independently captured. |
| Repository goal and phase recovered from repository-owned artifacts | observed | Proves the named artifacts were sufficient for intake, not that the old conversation was losslessly represented. |
| Branch, HEAD, upstream, ahead/behind, dirty state, origin, and live remote SHA rechecked | observed | Dated intake observation; later workspace changes require a new snapshot. |
| Stale handoff state was kept historical | observed | The bootstrap registration/thread fields were correctly distinguished from current host truth. |
| Old conversation replay was unnecessary for initial intake | observed | Later targeted lookup was still useful for this comparison and may be needed for future gaps. |
| Automatic same-workspace thread creation | unknown / not proven | The observed path was user-authorized, and the runtime contract requires an explicit request. |
| Automatic project registration | unsupported by current inventory | Absence from this inventory is not a universal host claim. |
| Lossless handoff | not proven | No predeclared complete fact oracle covered the full source thread. |
| Source-backed `handoff` Skill invocation | not tested | The handoff carrier was a Codex delegation/thread flow; loader and Skill activation were not observed. |
| Cross-host portability | not tested | No equivalent Claude Code or other-host run exists. |

## Measurements

- Thread-creation authority: one explicit user request in the source thread.
- Destination project registration: present before native thread creation;
  registration mechanism not exposed to the agent.
- Destination Git intake: `main`, clean, `HEAD == origin/main == live remote
  main`, ahead/behind `0/0` at the recorded intake.
- Native approval prompts observed in retained thread evidence: none recorded.
  This does not prove that the UI displayed none.
- Repository fact loss detected during intake: none among the explicitly bound
  five artifacts and Git checks.
- Full source-thread fact loss: unmeasured because no complete oracle was
  declared before the handoff.
- Current workspace after the observation: intentionally dirty only with the
  authorized matrix, protocol, fixture, evaluator, test, and evidence changes;
  this is not the intake pre-state.

## Supported claims

1. On the observed Codex Desktop/local host, a user-authorized project thread
   was created in the already registered destination repository.
2. A repository-anchored delegation plus named repository artifacts was
   sufficient to recover the required intake facts without replaying the old
   conversation first.
3. Live repository and project/thread checks correctly detected that dated
   handoff fields were historical.
4. Native thread/project inspection is sufficient for this evidence slice; no
   external capability or self-authored implementation is justified. Official
   app-server, Hook, and telemetry surfaces should be evaluated before any
   residual-gap implementation.

## Unsupported claims

This evidence does not support any claim that:

- Codex automatically registers projects or automatically creates continuation
  threads;
- the handoff was lossless or universally sufficient;
- the same behavior exists on another host, model, version, or workspace type;
- context pressure, token usage, or compaction timing was measured;
- a source-backed `handoff` Skill loaded or activated;
- a thread, Skill, Hook, or prompt can control runtime lifecycle outside the
  observed native interface.

The presence of official app-server, Hook, and OTel interfaces also does not
prove that they are enabled, connected, authorized, or effective in the current
desktop thread.

## Falsifiers and recheck triggers

The manual continuation hypothesis should be downgraded if a repeated run with
the same preconditions:

- creates a projectless or wrong-workspace thread;
- loses a predeclared critical fact that exists in the repository handoff;
- accepts stale branch, remote, dirty-state, or host-state claims without
  rechecking them;
- requires unrecorded additional authority or mutates unrelated state;
- cannot recover or report a failed/partial creation state.

Recheck after a Codex Desktop/tool-contract change, project model change,
different host, worktree target, remote host, loader change, or any claim of
automatic creation.

## Next bounded probe

A stronger `CTX-04`/`CTX-05` result requires a deliberately paired fresh-thread
trial with a predeclared fact oracle, injected stale facts, an interruption,
and measured recovery. The prepared
[`paired trial protocol`](context-continuation-paired-trial-protocol-2026-07-19.md)
prepares `gpt-5.6-terra`/`low` as a conditional capacity diagnostic and the
user-requested `gpt-5.3-codex-spark`/`low` as the weak-Agent floor. The weak arm
runs first when the result informs self-authored Skill or chain acceptance;
Terra is added only when attribution remains ambiguous. Holding reasoning effort
constant makes any triggered comparison easier to interpret without relaxing
the critical-fact or authority thresholds.

Creating each additional thread is a separate host side effect and requires an
explicit user request. Each exact model/reasoning pair must be revalidated by
the creation call; no substitute may silently inherit either arm's label. The
trial must keep manual creation distinct from any future supported automatic
trigger.
