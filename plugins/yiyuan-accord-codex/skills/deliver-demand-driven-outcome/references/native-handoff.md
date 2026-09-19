# Native carrier handoff interface

Read when integrating a fresh-task transfer through an authorized App Server
controller that survives the source and target. Resolve paths from this installed
plugin: [adapter contract](../../../adapter.json) and
[Node module](../../../runtime/carrier-handoff.cjs). Ordinary context assessment,
compaction and causal forks do not require this interface.

The CommonJS module exports `handoff(plan, {transport, recorder, verify})` and
`CarrierHandoffError`. It opens no process, connection, account or recovery service.
Use an existing suitable controller or establish one within current authority;
installation does not give ordinary Desktop/IDE Hooks control of those tasks.
The caller decides when a transfer is needed from current evidence and owns the
semantic checks, native configuration, authentication, budgets and recovery route.
This module performs the bounded transfer after those conditions are established.

## Plan and call

Load the module from the installed plugin root; retain the same controller and
callback identities throughout the call. `handoff` returns a Promise. The plan is
plain data with these exact keys (only fields marked optional may be omitted):

| Field | Meaning |
|---|---|
| `transferId` | Unique operation identity; a reused record requires reconciliation. |
| `scopeRef` | Shared effects whose already-authorized writer the recorder arbitrates. |
| `authorityRef`, `stateRef` | Current authority and recoverable task-state references. |
| `source` | `{threadId, turnId?}`; supply the exact active turn when it must be stopped. |
| `target` | `{cwd, model, modelProvider?}`; explicitly bound destination and suitable model. |
| `handoffText` | Authorized intake context, including goal, pauses, evidence and unfinished work. |
| `continuation` | `{input, sandboxPolicy}` for the first bounded continuation after acceptance. |
| `deadlineMs`, `recoveryDeadlineMs` | Future absolute UTC millisecond deadlines; recovery must be at least the work deadline. |

References must be nonempty bounded strings. Inputs are bounded to 1,048,576 UTF-16
code units; this is an API size ceiling, not a token budget. Sandbox policy is a
native structured object, not an authorization grant. Preserve user-selected modes
and pauses when choosing the destination and continuation. A paused responsibility
requires an authorized preservation action, not resuming its effects.

UTC deadlines convert once to Node `performance.now()` budgets. Every callback
deadline below uses that monotonic clock domain. A cross-process bridge translates
remaining duration into its own clock. Timeouts do not cancel native effects.
Callbacks must be receiver-free or pre-bound; immutable data arguments and checked
identities cannot authenticate a callback's hidden routing.

## Caller interfaces

`transport` supplies fixed `connectionId`, `hostVersion` and:

- `request(method, params, deadline)` returns the native response object, without
  a JSON-RPC envelope. Use bounded native requests on the owned connection.
- `waitTerminal(threadId, turnId, deadline)` returns the exact ordered
  `turn/completed` notification: `{method, params: {threadId, turn: {id, status}}}`.
  Intake and continuation require `status: "completed"`; source interruption may
  also finish as `interrupted` or `failed`. Preserve events arriving before the
  waiter is registered and correlate native effects with transfer/revision.

`recorder` supplies durable, atomic scope ownership across controllers and restarts:

- `begin(transferId, planDigest, initialState)` checks the already-bound source
  writer and excludes an in-flight transfer for the same scope. Return
  `{created: true, revision, lease: {scopeRef, transferId, token, writerThreadId}}`.
  The initial revision is a nonnegative safe integer and writer is the source.
- `compareAndSet(transferId, revision, nextState, expectedLease)` compares both
  revision and scope lease atomically, stores the full next state and changes
  ownership as requested. Return `{revision, lease}` with a strictly greater
  revision, matching scope/transfer and requested writer. Tokens must be nonempty.

Persist the full supplied state before returning success. Scope ownership remains
with the target after success. All cooperating writers must honor that authority;
this is not an OS lock. The caller owns protected storage, recovery reads and
eventual record retirement. Payloads and leases can contain sensitive task data.
Neither an in-memory map nor unconditional success callbacks provide these duties.

`verify(stage, facts, deadline)` independently checks current authority, state,
effects, budgets, modes and writer ownership. Facts include `packet` (the bound
plan and connection), `ledger`, and stage-specific native observations. Fetch any
missing decision-relevant evidence through the authorized controller; native
terminal receipts and model self-reports alone do not prove semantic acceptance.

To permit a stage, return `decision: "allow"`, matching `authorityRef`, `stateRef`,
`scopeRef`, a sourced nonempty `sourceRef`, `sourceRecoveryReady: true`, and the
following true predicates. Each assertion needs current evidence; copying the
required booleans is not verification.

| Stage | Additional predicates |
|---|---|
| `prepare` | `targetInitializationSafe` |
| `quiesced` | `quiesced`, `noOtherWriters` |
| `target-created` | `targetSettingsMatch`, `initializationEffectsVerified` |
| `accepted` | `accepted`, `sourceIdle`, `intakeEffectsVerified` |
| `continue` | `singleWriter` |
| `continued`, `release` | `effectsVerified`, `singleWriter` |

Only at `accepted`, the verifier may instead return `decision: "request-context"`
with sourced `additionalInput`, all common reference/recovery fields,
`sourceIdle: true` and `intakeEffectsVerified: true`. The module runs another
read-only intake within the original budgets, retaining the source writer.
Unresolved acceptance otherwise denies the transfer.

Filesystem read-only does not constrain every Hook, MCP, network or host effect.
Check initialization exposure before target creation, effective settings after
creation, and actual effects after each intake and continuation. Changed authority,
user intervention or shared state invalidates dependent prior allowances.

## Completion and recovery

The module records intent, stops the exact source turn if supplied, checks source
quiescence, creates a persistent fresh read-only target, verifies intake, atomically
transfers writer ownership, runs and verifies the first bounded continuation, then
unsubscribes the source. It retains native history and never enables Plan/Goal or
archives/deletes a task. `status: "handed-off"` includes target/turn identities,
recorder revision/lease and evidence references. Subscription release does not
prove process unload, resource savings or completion of the overall user goal.

On failure retain `CarrierHandoffError.code`, `stage`, `reconciliationRequired`,
`details` and `state`, alongside the durable recorder and raw native receipts.
Recorder or connection uncertainty prevents further mutations; an ambiguous native
request prevents another native action. A known owned active target may be stopped
within the original recovery budget only while routing and ownership remain known.
Late or malformed results require the surviving caller to reconcile actual effects
and writer ownership before retry, rollback or source release. The module does not
resume an interrupted transfer; reconcile first rather than blindly calling it
again with either the same or a new transfer identity.
