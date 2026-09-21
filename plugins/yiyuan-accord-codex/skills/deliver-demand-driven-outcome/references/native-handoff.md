# Native carrier handoff interface

Read when integrating a fresh-task transfer through an authorized App Server
controller that survives the source and target. Resolve paths from this installed
plugin: [adapter contract](../../../adapter.json) and
[Node module](../../../runtime/carrier-handoff.cjs). Ordinary context assessment,
compaction and causal forks do not require this interface.

The CommonJS module exports `handoff(plan, {transport, recorder, verify})` and
`CarrierHandoffError`, plus `HANDOFF_PROPOSAL_TOOL`, `prepareHandoff` and
`runHandoffProposal` for the
[source proposal path](#source-proposal-and-outer-dispatch). It opens no process,
connection, account or recovery service.
`reconcileContinuation` resolves only a verified first-continuation acknowledgement
loss in the existing recorder, as described below; it does not resume a handoff.
Use an existing suitable controller or establish one within current authority;
installation does not give ordinary Desktop/IDE Hooks control of those tasks.
The caller decides when a transfer is needed from current evidence and owns the
semantic checks, native configuration, authentication, budgets and recovery route.
This module performs the bounded transfer after those conditions are established.

## Find a usable host connection

First distinguish a host's native continuation controls, an already owned App
Server connection, and an embedded client with no exposed control endpoint. Use
sufficient native continuity without adding a server. The presence of this module,
a saved thread id or an installed MCP server does not establish control of that
thread or register the proposal tool.

In the inspected Codex 0.155.1 implementation, `codex app-server daemon version`
only probes the default official control endpoint. `codex app-server proxy`
connects raw stdio bytes to an already running control socket; `--sock` selects an
explicitly bound endpoint. It is a byte tunnel, not a JSONL-to-WebSocket converter:
its peer must perform the WebSocket handshake and framing expected by that socket.
Do not feed the plain JSONL connection below directly into the proxy.
Connection failure leaves that route unavailable or unknown; it
does not authorize starting, bootstrapping, restarting or pairing a shared service.
`codex queue` sends a user message and can initialize a session-command runtime;
it is not a read-only discovery command or a transfer acknowledgment. Preserve the
user's selected configuration rather than removing overrides to force daemon reuse.

On a suitable shared App Server, official `thread/resume` can attach a new client
to a loaded thread and replay its pending server requests. The inspected resume
schema cannot add `dynamicTools`: the source proposal tool must already have been
registered at `thread/start`. Do not turn an MCP call or shell result into a forged
`item/tool/call` envelope to bypass that requirement. A separately authorized direct
`handoff()` still needs its own source quiescence, writer and recovery evidence.

Multiple clients can receive the same pending dynamic-tool request. A responding
client is not thereby its task owner. Before answering, bind the exact source,
turn, call and scope; leave unrelated tool, permission and input requests for
their responsible clients. Reconcile already resolved requests instead of replying
again. Keep the recovery controller subscribed/alive through takeover. Releasing
one subscription does not by itself close other clients or prove the thread has
unloaded. Reconcile any later host-authorized source input as a state change;
all writers must honor the scoped handoff before continuing shared writes.

These are version-bound implementation facts, not GUI adoption evidence. Recheck
material host changes against the actual entry. Sources: [daemon probe](https://github.com/openai/codex/blob/be2951ea34f0d295ed0becf97079f92fa5f6950e/codex-rs/app-server-daemon/src/lib.rs#L547),
[queue](https://github.com/openai/codex/blob/be2951ea34f0d295ed0becf97079f92fa5f6950e/codex-rs/tui/src/session_queue_commands.rs#L29),
[subscription and replay](https://github.com/openai/codex/blob/be2951ea34f0d295ed0becf97079f92fa5f6950e/codex-rs/app-server/src/request_processors/thread_lifecycle.rs#L696),
[resume input](https://github.com/openai/codex/blob/be2951ea34f0d295ed0becf97079f92fa5f6950e/codex-rs/app-server/src/request_processors/thread_processor.rs#L3701).
The [official interface](https://learn.chatgpt.com/docs/app-server) labels App Server
and WebSocket transport experimental and unsupported for production workloads;
retain this upstream limit in any integration/support claim. It is not evidence
that every other native continuity route is unsuitable.

## Source proposal and outer dispatch

### Use the SDK source session and durable recorder

`runtime/codex-session.cjs` exports `createCodexSourceSession(options)`. This is
the caller for a newly created source on an already initialized, authorized
connection; it is not an attachment to an existing GUI task. Supply `connection`,
`recorder`, `scopeRef`, explicit native `threadStart` settings, `planResolver`,
`verify`, `current` and `ownerRequest`. Use receiver-free or pre-bound callbacks.
It preserves the owner's other dynamic tools and appends context/proposal tools;
conflicting names are rejected before source creation.

Call `session.run({input, deadlineMs, turn?})` with a nonempty text/native input and
an absolute Unix millisecond deadline. `turn` carries the owner's explicit native
turn settings; it cannot replace the source identity or input. The session
creates and binds the source, starts the turn, answers context observations and
dispatches a proposal through the existing handoff core. `planResolver(request,
context)` must return the bound plan described below. `current(context)` returns
current scope/authority/state/writer references, and `verify` retains the core's
independent stage-by-stage contract. The session supplies no semantic verdict.

Other server requests go to `ownerRequest(request, context)`, which returns
exactly `{result}` or `{error}` according to the owner's authority. Contexts carry
a deadline and cancellation signal; callback timeout does not forcibly terminate
the owner's asynchronous work or permit replay. Threadless requests stay with
their existing owner unless `ownUnscopedRequests: true` explicitly assigns them
to this session. The borrowed connection remains the sole protocol reader.

Completed ordinary turns can continue through the same session. Concurrent runs,
failed sessions and writes after a successful transfer are rejected. Read
`session.snapshot()` and the thrown error's state/RPC reference to reconcile an
unknown effect. Persist necessary receipts in the owner's existing evidence path;
the in-memory session does not automatically reconstruct itself after a crash.
The session appends its context/proposal tools to the explicitly bound target
tool list before the core's preparation and target-settings checks. Other target
tools come only from `plan.target.dynamicTools`; source tools are not silently
copied. During intake and first continuation, context requests are answered and
other requests go to their owner. A nested handoff proposal receives
`TRANSFER_IN_PROGRESS` without dispatch or queued replay.

After a successful transfer, use `session.adoptTarget({deadlineMs})` to continue
with this session's own target under the same controller. It accepts no arbitrary
thread or directory. The adapter rechecks the exact final durable record/lease,
registered tools and current native idle/persistent target, then invokes
`verify('adopt-target', facts, deadline)`. The verdict must bind the same current
scope/authority/state, identify its evidence with `sourceRef`, allow adoption and
affirm `adoptionAuthorized`, `singleWriter` and `effectsVerified`. The verifier
must inspect actual current permission, pauses and effects; stored strings are
not new authority. A stale record, missing tools, busy target or denied verdict
leaves the target unadopted and the old source unwritable.

Only then does the adapter settle the completed transfer once and re-read its
scope before making the target the next source. A later `run` uses a new transfer
identity if another handoff is needed. Ambiguous settlement or failed readback
locks the session for owner reconciliation and preserves receipts; it cannot be
retried as another settlement. Full history stays in the recorder. Do not reopen
a new source to evade an unresolved scope, missing receipt or retained pause.
Adoption keeps the target's native settings; it does not restore the former
source's model, approval policy or sandbox implicitly. Bind any authorized next
turn settings through `run.turn` and verify the effective environment as needed.
The source connection owner must serialize its writes through this session;
scope reads before and after a turn do not create an OS lock or eliminate a
check-to-send race against an unrelated controller that ignores this ownership.

### Restore a settled target on a new controller

`await restoreCodexSourceSession(options, {transferId, expectedScope, deadlineMs,
resume})` reuses the same session executor after a completed, settled transfer.
`options` supplies the connection, recorder, scope and existing callbacks; it must
not contain `threadStart`. `expectedScope` is the exact inactive scope receipt
previously acknowledged by adoption/restoration, with `scopeRef`, `writerThreadId`,
`activeTransferId: null` and `token`. Retain that receipt in the owner's recovery
state. Reading the newest token after an uncertain attempt is not a replacement
for reconciling its effects.

The adapter derives the native target from the retained transfer. It rejects
active transfers, pending effects, mismatched receipts and reused controller
identity. A summary `thread/read` may show an idle or unloaded persistent target;
`notLoaded` on this connection does not prove another controller stopped.
`verify('restore-prepare', facts, deadline)` must bind the current scope/authority/
state and evidence source, allow restoration, and affirm prior-controller
quiescence, reconciled pending effects, single-writer ownership and safe resume
initialization. Missing current authority or a retained pause holds restoration.
The required affirmative fields are `pauseStateVerified`,
`priorControllerQuiesced`, `pendingEffectsReconciled`, `restorationAuthorized`,
`singleWriter` and `resumeInitializationSafe`, alongside `decision: "allow"` and
the matching references above.

Only after that check does `claimScope` atomically rotate the acknowledged token,
followed by readback and native `thread/resume`. This order consumes the old basis
before resume can cause initialization effects. A lost claim/resume receipt
cannot be retried by opening a new executor with the old basis. Any uncertain
effect requires owner reconciliation; the adapter never refreshes the basis or
replays automatically. Failed restoration executors cannot fall back to creating
a new source.

`resume` explicitly supplies `cwd`, `sandbox` and `approvalPolicy`. Optional
`model`/`modelProvider` are forwarded; omission uses native restoration behavior
and does not establish that the current user choice is satisfied. Explicit
`effort` maps to the version-supported `config.model_reasoning_effort` override.
The fixed 0.155.1 resume API has no direct `effort` field. No arbitrary config,
history, path or dynamic-tool replacement is accepted. `excludeTurns: true` and
summary reads avoid mandatory full-history hydration; the verifier retrieves the
necessary history through suitable bounded native sources.

After resume, `verify('restore-resumed', facts, deadline)` must verify actual
settings, retained history, effects and restored continuity tools, including a
`nativeToolEvidenceRef`. The saved Accord plan alone is not evidence that the
host restored tools. A final scope read must still match the claimed token before
the session becomes ready. Ordinary turns also recheck their held token, so a
stale cooperating executor cannot continue after a new claim. This covers a
settled target with reconciled effects; active-transfer/crash recovery and
arbitrary external writes require their own reconciliation path.
The resumed verdict requires matching references, `decision: "allow"`,
`continuityToolsRestored`, `targetSettingsMatch`, `historyRetained`, `singleWriter`
and `effectsVerified` all true, plus the nonempty native tool evidence reference.

`runtime/carrier-recorder.cjs` exports
`openCarrierRecorder({path, create?, busyTimeoutMs?})`. The path must be an
absolute, ordinary caller-owned database file; `create: true` exclusively creates
a new file, while the default requires this exact recorder schema. No directory,
database migration, account or background service is created implicitly.
`readScope` throws `SCOPE_NOT_FOUND` for an unbound scope. `bindScope`, `begin`,
`compareAndSet` and `read` implement the core's existing durable recorder contract.
`claimScope(scopeRef, expectedScope)` rotates only an unchanged inactive scope's
token in one transaction, preserving its writer and transfer history. It cannot
clear an active transfer, change writers, expire another owner or grant authority.
Explicit `settle(transferId, revision, lease)` only releases an active transfer
whose stored state has the verified source-release shape; it preserves the target
writer and history, rotates the token and does not grant another action.

The recorder lazily uses [Node's built-in SQLite](https://nodejs.org/download/release/v24.8.0/docs/api/sqlite.html)
`DatabaseSync`, available in the tested Node 24 runtime. That optional API remains
version-sensitive; absence is an explicit error, not a silent volatile fallback.
Hook/MCP loading does not open SQLite. Close the recorder and the owned host through
their respective owners after preserving unfinished state; the session closes
neither borrowed resource. Ledger CAS coordinates cooperating controllers, not
arbitrary external writers or user authority.

### Reuse an owned Node stdio connection

For a caller that already owns a suitable process, the accompanying
`runtime/codex-connection.cjs` exports `createOwnedAppServerConnection({stdin,
stdout, connectionId, hostVersion, maxMessageBytes?, maxJournalBytes?})`.
Pass that process's Node writable/readable streams and its actual connection and
version identity. Attach before initialization or other requests; this module
is the exclusive protocol reader, while a caller may separately retain raw bytes.
It does not discover, spawn, initialize, authenticate, restart or close a process.
Give each connection lifetime its own `connectionId`; reconnecting must not reuse
the old identity merely because the endpoint and host version stayed the same.

The returned `transport` supplies `request`, `notify` and `waitTerminal` using
absolute `performance.now()` deadlines. The caller sends the native `initialize`
request and `initialized` notification and registers the proposal tool at source
thread creation. Unmatched server requests, including approvals, remain for their
authorized handler; this connection never grants them automatically.
`receiveRequest(predicate, deadline)` returns an actual retained server request
with the fixed connection metadata. Pass that object to both `runHandoffProposal`
and `proposalChannel(request, current)`; the latter implements the channel below
with exact request-anchor replay and live events from its single reader.

`context(threadId, turnId, maxAgeMs)` feeds the same originally timed journal to
the existing context reader. Its initial model comes only from this connection's
actual thread start/resume response. Missing or evicted identity/history,
disconnect, reroute, compaction or expiry leaves affected observations unknown;
it does not infer authority, current-input reconciliation or a need to transfer.
Use the existing assessment with independently checked task state and forecasts.

To expose those observations to a source Agent, register the exported
`CONTEXT_OBSERVATION_TOOL` (`accord_inspect_context`) alongside any required
dynamic tools at `thread/start`. Its only optional argument is `maxAgeMs`;
the default is 30000 ms. On the exact corresponding native tool request, call
`connection.replyContext(request, deadline)`. It derives the thread/turn from
that retained request, reads the same native journal and replies once with
`yiyuan-accord-native-context-reply/v1`. It returns the sent payload to the
controller as well. Invalid arguments receive a failed tool result without
identity or operation overrides; foreign requests/namespaces are not answered.

An unknown observation is a successful read of unavailable evidence, not known
capacity. The first dynamic call may precede the first native usage event; later
completed responses may supply new signals. Do not poll an unchanged absence or
relabel the sample time. This query supplies no task text, semantics, forecast,
permission or handoff decision. The Agent/controller must still decide the next
useful span and satisfy the existing transfer conditions. Ordinary Desktop/IDE
installations do not acquire this tool through the plugin's MCP registration.

Frames default to 1 MiB and the in-memory journal to 4 MiB; pending work and
retained request handling are also bounded. These are transport limits, not model
capacity. An evicted anchor cannot be replayed; the caller must reconcile instead
of treating a truncated journal as complete. `close()` detaches only this module's
listeners and rejects its pending waits; process termination, durable evidence,
scope storage and recovery remain with the caller. No ambiguous send is retried.

This reuses the [official Node stdio protocol](https://learn.chatgpt.com/docs/app-server#protocol)
and built-in Node streams without a new package dependency. It is a usable
connection for an already authorized controller, not a default Desktop connection
or an autonomous timing/semantic-verification engine. Preserve the upstream
experimental support qualification described above.

### Reuse an owned WebSocket

`createOwnedAppServerWebSocketConnection({socket, connectionId, hostVersion,
maxMessageBytes?, maxJournalBytes?, maxBufferedBytes?})` accepts an already-open
standard WebSocket supplied by the caller. It exposes the same transport,
context, request and proposal interfaces as the stdio connection. Reuse a supported
WebSocket implementation for handshakes, authentication headers, fragmentation and
network I/O, such as [Node's implementation](https://github.com/nodejs/undici/blob/main/docs/docs/api/WebSocket.md)
where available; Accord adds no WebSocket dependency or framing implementation.
The caller binds the actual endpoint, authorization and host version before passing
the socket and supplies one RPC reader/writer owner per connection; separate clients
use separate sockets. This adapter never discovers, opens, authenticates or closes a socket,
starts a listener, or attaches to an ordinary Desktop task by itself.

One text message carries one JSON RPC object; valid whitespace is normalized for
the existing bounded reader. Binary, malformed or oversized messages invalidate
the bridge. Closing, socket errors or failed sends reject pending work and detach
only the adapter's listeners. A local send-buffer limit rejects the unsent call
without retry. The default outbound buffer cap is 4 MiB; unknown buffered capacity
is not zero. A successful send only means local queuing, not delivery, an accepted
effect or transfer authority. The message limit applies after the supplied
WebSocket assembles a message; it does not bound that library's internal buffering.
The caller remains responsible for socket shutdown and recovery.

An authorized `app-server --listen ws://127.0.0.1:0` can select a local port and
reports its actual endpoint. Bind its supported authentication and verify access
rather than assuming loopback is sufficient. On Windows, a `unix://PATH` listener
requires a private socket directory: the native implementation creates a new
directory with a user-only DACL and rejects an unsafe existing one without repair.
Do not weaken that check or modify unrelated directory ACLs. A newly created task
also needs a materialized native history before `thread/resume` by id; creation
alone is not evidence of a resumable source. These are connection prerequisites,
not a requirement to start another service for adequate native continuity.
Sources: [raw proxy dispatch](https://github.com/openai/codex/blob/be2951ea34f0d295ed0becf97079f92fa5f6950e/codex-rs/cli/src/main.rs#L1427)
and [private-directory creation](https://github.com/openai/codex/blob/be2951ea34f0d295ed0becf97079f92fa5f6950e/codex-rs/uds/src/windows_security.rs#L54).

For a controller-owned source to request transfer, register the exported
`HANDOFF_PROPOSAL_TOOL` in its native `thread/start.dynamicTools` with the host's
experimental API enabled. Its unnamespaced tool is `accord_request_handoff`;
arguments contain a bounded `reason` and optional `checkpointRef`. Treat these as
proposal data; the controller binds the plan, authority, scope, destination and
budgets. A source request is neither a takeover nor a new permission.

Pass the actual `item/tool/call` JSON-RPC request to
`prepareHandoff(plan, {transport, recorder, verify}, nativeRequest)`, adding the
bound `connectionId` and `hostVersion` to its envelope. The plan must identify the
same source thread and turn. Preparation performs only the existing recorder's
begin/CAS, retains the source writer and records `proposal-response-pending` with
the request identity, argument digest and pending tool response. It sends no native
request. The returned `{response, dispatch}` handle has no extra queue or store.

Send `response` as the answer to that server request. It acknowledges only `queued`
and asks the source to finish its current turn without further actions on the
transferred work. Preserve raw ordered events in the existing controller loop.
Do not run handoff inside the still-pending tool callback or nest requests on a
serialized receiver. After the exact successful dynamic tool `item/completed` and
source `turn/completed`, re-read current scope/authority/state/writer evidence and
invoke the handle once:

```js
await prepared.dispatch({
  toolCompleted,
  sourceTerminal,
  current: {scopeRef, authorityRef, stateRef, writerThreadId},
});
```

The tool receipt must match thread, turn, call, tool, namespace and returned
content, with `success: true`. This proposal path requires source status
`completed`; interruption or failure retains pending responsibility for
reconciliation, rather than being interpreted as permission to proceed. Dispatch
uses the original record/revision/lease and deadlines, and runs the existing
handoff checks without interrupting an already completed source. Current-reference
strings still require the independent `verify` checks below.

The handle is single-use, including after failed validation. Concurrent or repeated
dispatch cannot start a second transfer. Connection change, expired budgets or
uncertain CAS preserve unresolved state. This interface does not rebuild a handle
after controller failure or replay a tool response: the surviving authorized caller
must reconcile the durable record and actual native effects first. Existing
`handoff()` remains available for a separately bound direct transfer, including its
supported active-source quiescence; do not use it to bypass an unresolved proposal.

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
| `target` | `{cwd, model, modelProvider?, effort?, dynamicTools?}`; explicitly bound destination, model, optional reasoning effort and native tool specifications. |
| `handoffText` | Authorized intake context, including goal, pauses, evidence and unfinished work. |
| `continuation` | `{input, sandboxPolicy}` for the first bounded continuation after acceptance. |
| `deadlineMs`, `recoveryDeadlineMs` | Future absolute UTC millisecond deadlines; recovery must be at least the work deadline. |

References must be nonempty bounded strings. Inputs are bounded to 1,048,576 UTF-16
code units; this is an API size ceiling, not a token budget. Sandbox policy is a
native structured object, not an authorization grant. Preserve user-selected modes
and pauses when choosing the destination and continuation. A paused responsibility
requires an authorized preservation action, not resuming its effects.

The optional `target.dynamicTools` list is part of the immutable plan and target
settings checked by the verifier. It allows at most 64 unique `(namespace, name)`
identities and 1 MiB of encoded JSON. These are adapter input ceilings; the full
RPC envelope and host validation may impose lower usable limits. The controller
must handle their requests throughout intake and continuation. Direct core users
who omit this field retain the previous target behavior; it grants no tool action.

When an effort choice must survive transfer, bind `target.effort` to the current
authorized choice after checking the host model's supported values. The adapter
forwards it unchanged to every read-only intake and the first continuation via
the official [turn/start effort field](https://learn.chatgpt.com/docs/app-server#turns).
Omission adds no override; it is not proof of inheriting the source's selection.
The adapter neither maintains a model/effort catalogue nor retries a rejected value
with another value. Requested settings are not actual adoption evidence: verify
the native target context through the existing verifier. A later user choice or
changed support invalidates dependent allowances; do not restore a stale selection.

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
unsubscribes the source. It never enables Plan/Goal or issues archive/delete
operations. `status: "handed-off"` includes target/turn identities,
recorder revision/lease and evidence references. Subscription release does not
prove process unload, resource savings or completion of the overall user goal.
`source.archived` and `source.deleted` describe this adapter's actions; they do not
inspect changes made by other actors or guarantee that an ephemeral source exists.

`source.ephemeral` and `nativeHistoryRetained` follow the current source
`thread/read` metadata. An explicitly persistent source reports retained native
history; an ephemeral source reports false; missing or unavailable persistence
metadata reports null, even if an earlier read was known. Conflicting known values
require reconciliation. The final record preserves these facts separately from
`sourceRecovery: "retained"`. General `sourceRecoveryRetained` still depends on the
independent verifier and may be supported by a caller-owned checkpoint; it does
not establish native history or power-loss durability. Ephemeral or unknown
sources remain usable when that independent recovery requirement is met.

On failure retain `CarrierHandoffError.code`, `stage`, `reconciliationRequired`,
`details` and `state`, alongside the durable recorder and raw native receipts.
Recorder or connection uncertainty prevents further mutations; an ambiguous native
request prevents another native action. A known owned active target may be stopped
within the original recovery budget only while routing and ownership remain known.
Late or malformed results require the surviving caller to reconcile actual effects
and writer ownership before retry, rollback or source release. The module does not
resume an interrupted transfer; reconcile first rather than blindly calling it
again with either the same or a new transfer identity.

The owned connection attaches a frozen `rpcRequest` to a failed allocated call:
`{connectionId, hostVersion, requestId, method}`. It does not duplicate parameters
or claim that the call was sent or executed. The handoff adapter copies a bounded
reference into `pendingEffect.requestRef` and error details only when the connection,
version and method match the failing call. Foreign or malformed references do not
resolve uncertainty. The normal recorder persists that pending effect when available;
this does not close a hard-crash window before the failure record is saved.
A caller deadline that expires before the transport reports its failure may also
leave no reference; retain the original journal and the unresolved effect.

The surviving recovery owner first reads the current scope, revision and writer
lease. Correlate the reference with the retained original RPC request/response and
ordered native events, then query the exact target using `thread/read` with
`includeTurns: true` or supported paginated turn/item reads. Verify the identified
turn and actual effects through the existing verifier. Reconcile the original
operation instead of repeating `turn/start` to obtain another receipt. A missing
reference or an incomplete log is not proof that nothing ran. If the target owns
the scope, retain that writer while resolving uncertainty; a new transfer id is
not a bypass. Do not release source recovery from a locator or model report alone.

Preserve the native storage needed by the chosen recovery route, not just a copy
of its visible files. In inspected Codex 0.155.1 paginated history, full turn reads
validate [rollout lineage](https://github.com/openai/codex/blob/be2951ea34f0d295ed0becf97079f92fa5f6950e/codex-rs/thread-store/src/local/rollout_lineage.rs)
against selected rollout paths as well as SQLite history. Moving DB/WAL/SHM and
JSONL files alone does not relocate those references. Use an evidenced native
migration/restore route with resolvable lineage; do not rewrite database paths to
manufacture acceptance. A fresh process reading restored state does not establish
a resumed writer, a valid business workspace or current permission to continue.

## Reconcile a verified first continuation

Call `reconcileContinuation(input, {transport, recorder, verify})` only for an
existing `reconciliation-required` record whose writer already is the target and
whose pending effect is the first continuation's failed `turn/start` acknowledgement.
It does not resolve arbitrary effects, change writer, start/resume a native task,
enable modes, unsubscribe the source or authorize subsequent execution.

`input` has exactly `transferId`, `scopeRef`, `authorityRef`, `stateRef`, a fresh
absolute UTC `deadlineMs`, and `receipt: {requestRef, request, response}`. Supply
the retained original JSON-RPC request and successful response, not reconstructed
model reports. Current references must match the frozen plan and record. The old
plan's expired deadlines are evidence only; they cannot renew work or authority.

The ordinary `handoff` recorder contract is unchanged. This operation needs:

- `read(transferId, scopeRef, deadline)` returns an atomic current snapshot
  `{revision, state, lease}`, including the actual active scope lease.
- `compareAndSet(transferId, revision, nextState, expectedLease, deadline)` uses
  the existing atomic revision/lease fence. Scope, transfer and target writer stay
  fixed; the store may rotate its lease token. Persist the supplied state before
  acknowledging. Deadlines use the same monotonic clock as the other callbacks.

The helper correlates the pending reference, full request parameters and response,
then requests the target's full turns with `thread/read`. Exactly the recorded
intake turns and this completed continuation must be present, with matching input
and no additional/active turn. It uses no native mutation method; the host read
may itself refresh a persisted history projection for a loaded thread.

`verify("continuation-reconcile", facts, deadline)` receives the current input,
atomic ledger snapshot, original/current connections, native target read and
observed turn. Return matching scope/authority/state, a sourced `sourceRef`,
`decision: "allow"`, and true `sourceRecoveryReady`, `singleWriter`, `effectsVerified`,
`priorAttemptQuiesced`, `receiptVerified`, `reconciliationAuthorized`. Independently
verify original receipt provenance, consequential effects including native read
housekeeping, current pauses/authority, ownership and that the prior attempt can
no longer dispatch. The controller process itself need not be killed. Booleans
without evidence are not a verifier.

One CAS records `continuation-reconciled`, clears only this active pending effect
and preserves its original pending/failure evidence in `reconciliation`. A final
atomic read must match the commit. Conflicts, late or malformed acknowledgements
hold with no automatic retry. After uncertain commit, a fresh invocation with the
same receipt can return `already-reconciled` from an exact stored transition;
different evidence cannot replace it. That shortcut checks storage only, not
current native/business state. Both results leave `sourceReleaseAllowed` and
`continuationAllowed` false. These flags do not revoke existing user authorization;
they prevent deriving it from this record alone. The caller establishes any later
action from current authority and conditions, without inventing another human gate.

## Event-driven proposal dispatch

Controllers with an ordered native event receiver can instead call
`runHandoffProposal(plan, dependencies, nativeRequest, channel)`. It uses the same
proposal record, one-shot dispatcher and verification core. The controller still
decides whether the proposal serves the authorized task; this function does not
choose a context threshold or discover a control connection.

`channel` has exactly three receiver-free or pre-bound callbacks:

- `subscribe(listener, requestAnchor)` synchronously subscribes and returns a
  synchronous function that removes only this listener. Bind to the supplied
  validated request identity on the same connection. Replay the ordered journal
  **after that request** and join live delivery without a gap, including events
  between receiving the request and invoking this function. If that continuity
  cannot be established, throw before acknowledging the proposal. Supply each
  native notification with `connectionId` and `hostVersion` beside `method` and
  `params`. These labels are caller provenance, not authentication. Keep the raw
  journal independently; only two correlated receipts (each bounded to the
  adapter's text ceiling) are retained here.
- `respond(response, deadline)` sends the exact native tool response once and
  resolves when that local send completes. Keep the receiver pumping while it
  runs. A send acknowledgment alone is not native tool success; rejection or
  timeout never causes an automatic resend.
- `current(deadline)` independently re-reads and returns
  `{scopeRef, authorityRef, stateRef, writerThreadId}` after both receipts arrive.
  These references do not replace the existing semantic verifier or source-state
  reads. Connection identity and callbacks remain bound throughout the operation.

All deadlines use the monotonic clock described below. Subscription happens before
preparation and sending. Unrelated tasks are ignored; identical duplicate receipts
do not create another dispatch. Conflicting receipts, a new source turn from the
request anchor onward, a mismatched connection or out-of-order source terminal
hold the operation for reconciliation. An unordered event source must first supply
its own evidenced ordering; arrival alone must not be relabeled causal order.
Missing receipts expire under the existing plan deadline. Once both arrive, the
module rechecks current references and invokes the same dispatcher automatically.
Listening continues through intake, continuation and source release, so later
source activity invalidates subsequent dependent actions as well.

The listener is removed on success or failure; the shared native connection is
not closed. A failed listener release reports `PROPOSAL_CHANNEL_RELEASE_FAILED`;
when transfer already completed, `details.completedResult` retains that result.
Reconcile the listener and actual effects, never replay the transfer. Failure
before record creation leaves responsibility with the caller's retained request;
later failures preserve the existing record and pending effect. This adapter does
not provide a journal, survive controller loss itself or prove GUI integration.
