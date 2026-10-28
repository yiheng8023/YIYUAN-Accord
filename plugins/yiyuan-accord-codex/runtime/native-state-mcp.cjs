'use strict';

// Bounded state and explicit task-execution tools on one existing stdio MCP.
// State reads do not dispatch work; the shared observer protects owned execution.
// Codex supplies call metadata separately from model-chosen tool arguments.
const path = require('node:path');
const fs = require('node:fs');
const crypto = require('node:crypto');
const {TextDecoder} = require('node:util');
const {operate, loadedFunctionSha256, nativeInputDiagnostic} = require('./task-checkpoint.cjs');
const {TOOL: EXECUTION_TOOL, createNativeTaskExecution} = require('./native-task-execution.cjs');

const PROTOCOL = '2025-06-18';
const MAX_FRAME = 128 * 1024;
const MAX_RESULT = 128 * 1024;
const TOKEN_BOUND = {type: 'integer', minimum: 0, maximum: Number.MAX_SAFE_INTEGER};
const CURSOR_SCHEMA = {type: 'object', properties: {
  sourceId: {type: 'string'}, headSha256: {type: 'string', pattern: '^[a-f0-9]{64}$'},
  anchorOffset: TOKEN_BOUND, endOffset: TOKEN_BOUND,
  prefixSha256: {type: 'string', pattern: '^[a-f0-9]{64}$'},
  signalsSha256: {type: 'string', pattern: '^[a-f0-9]{64}$'},
}, required: ['sourceId', 'headSha256', 'anchorOffset', 'endOffset', 'prefixSha256', 'signalsSha256'], additionalProperties: false};
function validCursor(cursor) {
  return record(cursor) && Object.keys(cursor).sort().join(',') === CURSOR_SCHEMA.required.slice().sort().join(',') &&
    text(cursor.sourceId, 200) && Number.isSafeInteger(cursor.anchorOffset) && cursor.anchorOffset >= 0 &&
    Number.isSafeInteger(cursor.endOffset) && cursor.endOffset >= cursor.anchorOffset &&
    ['headSha256', 'prefixSha256', 'signalsSha256'].every(key => /^[a-f0-9]{64}$/.test(cursor[key]));
}
const CONTEXT_ASSESSMENT = Object.freeze({
  type: 'object',
  description: 'Assess one bounded next work span against a previously observed receipt epoch and context generation. Identity comes only from current native call metadata. Times and sourced estimates are caller evidence and are not refreshed by the adapter.',
  properties: {
    epoch: {type: 'string', minLength: 1, maxLength: 256,
      description: 'Exact receipt epoch returned by the prior inspection; a later input requires reassessment.'},
    expectedRevision: {...TOKEN_BOUND,
      description: 'Exact checkpoint revision returned by the same prior inspection; a later revision requires reassessment.'},
    contextGeneration: {type: 'string', pattern: '^[a-f0-9]{64}$',
      description: 'Exact context generation returned by the prior native context observation. Turn, model, host and compaction changes invalidate it.'},
    observedAtMs: {...TOKEN_BOUND, description: 'Original observation time for the caller evidence; never restamped.'},
    validUntilMs: {...TOKEN_BOUND, description: 'Original exclusive expiry for the caller evidence; never extended.'},
    sourceRef: {type: 'string', minLength: 1, maxLength: 2048,
      description: 'Inspectible source for the integrity and time claims.'},
    integrity: {type: 'string', enum: ['verified', 'degraded', 'unknown'],
      description: 'Inheritance completeness under the bound receipt and context conditions.'},
    estimates: {type: 'object', properties: {
      sourceRef: {type: 'string', minLength: 1, maxLength: 2048,
        description: 'Inspectible source or derivation for every token estimate below.'},
      contextTailUpperBoundTokens: {...TOKEN_BOUND,
        description: 'Upper bound for unaccounted context after the latest native response boundary.'},
      nextWorkTokens: {...TOKEN_BOUND, description: 'Upper bound for the next bounded work span.'},
      handoffTokens: {type: 'integer', minimum: 1, maximum: Number.MAX_SAFE_INTEGER,
        description: 'Reserve for handoff preparation and takeover verification.'},
      recoveryTokens: {type: 'integer', minimum: 1, maximum: Number.MAX_SAFE_INTEGER,
        description: 'Reserve for failure recovery.'},
      safetyMarginTokens: {type: 'integer', minimum: 1, maximum: Number.MAX_SAFE_INTEGER,
        description: 'Additional uncertainty margin.'},
    }, required: ['sourceRef', 'contextTailUpperBoundTokens', 'nextWorkTokens', 'handoffTokens',
      'recoveryTokens', 'safetyMarginTokens'], additionalProperties: false},
  }, required: ['epoch', 'expectedRevision', 'contextGeneration', 'observedAtMs', 'validUntilMs', 'sourceRef',
    'integrity', 'estimates'], additionalProperties: false,
});
const OBSERVATION_EFFECT = 'The shared MCP handler may stop an existing owned execution and retain operation evidence when its source becomes invalid.';
const TOOL = Object.freeze({
  name: 'inspect_task_state',
  description: 'Read saved Accord task state; request includeContext for bounded native context observations, or contextAssessment to assess one sourced work span against a prior observation. Oversized details return a checked checkpoint file locator and digest; read and verify that full contract before dependent actions. Current host identity comes from call metadata, separately from recorded session metadata. A fit is advice only; no permission, completion, takeover or handoff control is established. ' + OBSERVATION_EFFECT,
  inputSchema: {type: 'object', properties: {cwd: {type: 'string', minLength: 1, maxLength: 4096,
    description: 'Absolute existing workspace directory. Reconcile the cwd in the native Hook receipt or recovery locators: it keys task state and is the base for checkpoint file references, which may differ from the directory containing business files. Caller-selected scope, not host-attested current cwd; do not silently substitute another scope.'},
    includeContext: {type: 'boolean', description: 'Also read current Hook-bound context counters. Defaults to false; missing or stale evidence remains unknown.'},
    includeNativeInputs: {type: 'boolean', description: 'Read bounded source evidence for captured-input coverage and pending native inputs; no receipt mutation.'},
    contextMaxAgeMs: {type: 'integer', minimum: 1, maximum: Number.MAX_SAFE_INTEGER,
      description: 'Requires includeContext or contextAssessment. Caller-selected age limit for the native response boundary; defaults to 30000 ms and does not extend caller evidence.'},
    contextAssessment: CONTEXT_ASSESSMENT},
    required: ['cwd'], additionalProperties: false},
  annotations: {readOnlyHint: false, destructiveHint: true, idempotentHint: false, openWorldHint: false},
});
const INPUT_TOOL = Object.freeze({
  name: 'read_task_input',
  description: 'Read saved input text pages, or a sourcePart selected from inspect_task_state(includeNativeInputs) by cursor/record offset/hash/part index. Source selection is mutually exclusive with index and requires expectedReceiptEpoch. It can read an original anchor or pending text/one inline PNG before reconciliation; wrapper paths and remote URLs are never fetched. Image content is transient, bounded to the existing 8 MiB native-input byte budget. Reading, byte coverage and Agent understanding are separate; no replay, receipt write, read-count gate or permission. ' + OBSERVATION_EFFECT,
  inputSchema: {type: 'object', properties: {
    cwd: TOOL.inputSchema.properties.cwd,
    index: {type: 'integer', minimum: 0, maximum: Number.MAX_SAFE_INTEGER, description: 'Captured input index; defaults to zero. Nonzero pagination requires expectedReceiptEpoch.'},
    offset: {type: 'integer', minimum: 0, maximum: Number.MAX_SAFE_INTEGER, description: 'Unicode code-point offset within that input; defaults to zero. Nonzero pagination requires expectedReceiptEpoch.'},
    maxChars: {type: 'integer', minimum: 1, maximum: 16000, description: 'Page character budget; defaults to 4000.'},
    sourcePart: {type: 'object', properties: {evidenceCursor: CURSOR_SCHEMA,
      recordOffset: TOKEN_BOUND, recordSha256: {type: 'string', pattern: '^[a-f0-9]{64}$'}, partIndex: TOKEN_BOUND},
      required: ['evidenceCursor', 'recordOffset', 'recordSha256', 'partIndex'], additionalProperties: false},
    expectedReceiptEpoch: {type: 'string', minLength: 1, maxLength: 256,
      description: 'Use the returned next cursor or prior inspection epoch to reject a changed input basis. This is a read condition, not a recovery token or authorization.'},
  }, required: ['cwd'], additionalProperties: false},
  annotations: {readOnlyHint: false, destructiveHint: true, idempotentHint: false, openWorldHint: false},
});
const OUTPUT_CHECK = Object.freeze({type: 'object', properties: {
  path: {type: 'string', minLength: 1, maxLength: 4096,
    description: 'Workspace-relative file path. The checkpoint helper inspects it; this tool does not write it.'},
  sha256: {type: 'string', pattern: '^[a-f0-9]{64}$'},
  json: {type: 'object', description: 'JSON Pointer keys mapped to exact expected values.'},
}, required: ['path'], additionalProperties: false});
const OBSERVED_FILE = Object.freeze({type: 'object', properties: {
  present: {type: 'boolean'}, sha256: {type: 'string', pattern: '^[a-f0-9]{64}$'},
}, required: ['present'], additionalProperties: false});
const MANAGE_TOOL = Object.freeze({
  name: 'manage_task_state',
  description: 'Bind, pause, retire or explicitly reconcile this root task\'s saved native inputs using the exact observed epoch and revision. Identity comes only from native call metadata. For native-input-reconciliation-required, inspect_task_state with includeNativeInputs, review actual pending input and coverage, then reconcile-input with its evidenceCursor; rebind a complete reviewed contract under the returned new epoch. This does not resume a pause or clear recovery flags. For bind, explicitly provide result, inputs, outputs, nextAction and canContinue every time; none of these five fields is inherited. Use inputs: [] when appropriate and at least one output predicate. These operations write no business files or user messages. Retire retains its existing task-state predicates. Metadata, reasons and source matches establish neither permission nor completion; verify the actual user decision.',
  inputSchema: {type: 'object', properties: {
    cwd: TOOL.inputSchema.properties.cwd,
    action: {type: 'string', enum: ['bind', 'pause', 'retire', 'reconcile-input']},
    evidenceCursor: {...CURSOR_SCHEMA, description: 'Exact prior inspect nativeInputEvidence.cursor; benign later tool/assistant append is permitted, changed input/control or old bytes is rejected.'},
    epoch: {type: 'string', minLength: 1, maxLength: 256,
      description: 'Exact current receipt epoch from inspect_task_state. The adapter never refreshes it automatically.'},
    expectedRevision: {...TOKEN_BOUND,
      description: 'Exact current checkpoint revision from inspect_task_state. The adapter never refreshes it automatically.'},
    result: {type: 'string', minLength: 1, maxLength: 16384,
      description: 'Required for bind: the intended authorized outcome and its scope, preserved across work spans. Put progress in nextAction, necessary unresolved conditions and sourced result records. Reconcile an actual authorized goal change; explicitly supply the reviewed outcome on every bind.'},
    inputs: {type: 'array', maxItems: 100, items: {type: 'string', minLength: 1, maxLength: 4096},
      description: 'Required for bind: the complete protected input list, not inherited. Use [] when there are no protected inputs; reconcile any removal of prior inputs.'},
    outputs: {type: 'array', minItems: 1, maxItems: 100, items: OUTPUT_CHECK,
      description: 'Required for bind: the complete output predicate list with at least one entry, not inherited. Read the current contract and reconcile changes before submitting it.'},
    nextAction: {type: 'string', minLength: 1, maxLength: 16384,
      description: 'Required for bind: the next concrete action within current authority; explicitly supply it on every bind.'},
    canContinue: {type: 'boolean',
      description: 'Required for bind: explicitly supply true or false on every bind. Caller observation that the next safe work is feasible; this records feasibility and never requests a turn or drives automatic execution. '
        + 'Set true only when the next concrete work can proceed safely within current authority. '
        + 'Set false while waiting for necessary user observation, decision, authorization or external conditions, preserving unfinished conditions. '
        + 'An unfinished project or mode=active alone does not justify true. '
        + 'False does not mean completion, cancellation or user pause, and does not block later user input.'},
    revisionReason: {type: 'string', minLength: 1, maxLength: 2048},
    inputRevisions: {type: 'array', maxItems: 100, items: {type: 'object', properties: {
      path: {type: 'string', minLength: 1, maxLength: 4096}, observed: OBSERVED_FILE,
      reason: {type: 'string', minLength: 1, maxLength: 2048},
    }, required: ['path', 'observed', 'reason'], additionalProperties: false}},
    unresolved: {type: 'array', maxItems: 32,
      items: {type: 'string', minLength: 1, maxLength: 2048}},
    resumeReason: {type: 'string', minLength: 1, maxLength: 2048},
    reason: {type: 'string', minLength: 1, maxLength: 2048,
      description: 'Required for pause, unbound receipt retirement and user-cancelled retirement.'},
    disposition: {type: 'string', enum: ['user-cancelled'],
      description: 'Explicit cancellation disposition for retire only; it is a caller claim, not proof of a user decision.'},
  }, required: ['cwd', 'action', 'epoch', 'expectedRevision'], additionalProperties: false},
  // Retire can remove this task's own checkpoint and receipt. Other actions
  // still write checkpoint state, so this is intentionally not read-only.
  annotations: {readOnlyHint: false, destructiveHint: true, idempotentHint: false, openWorldHint: false},
});
const CLAIM_LIMIT = 'Native-call metadata is received context, not authentication or permission. The workspace is caller-selected. Saved state and canContinue do not prove current intent, freshness, completion, takeover or control of this thread. The state read writes no checkpoint or business files and dispatches no new task. ' + OBSERVATION_EFFECT;
const INPUT_CLAIM_LIMIT = 'Saved text pages and bound native source parts are recorded data, not human origin, permission, complete history or work progress. PNG byte identity, image-content return and Agent understanding are separate. A read does not clear quarantine, resume a pause or authorize effects; reconcile current input and actual authority separately. ' + CLAIM_LIMIT;
const MANAGE_CLAIM_LIMIT = 'This operation records or retires only the existing root-task checkpoint state under the supplied stale-write conditions. Caller-provided reasons, native metadata, tool annotations and returned inspection are observations, not proof of task completion, user permission, current intent, writer ownership, takeover or external acceptance. The Agent must verify the actual user decision or applicable host-approved source; this adapter performs no keyword or semantic authorization judgment. Bind may read declared workspace files but does not write business outputs, dispatch work, replay input, recover locks or change a host mode. ' + OBSERVATION_EFFECT;
const record = value => value !== null && typeof value === 'object' && !Array.isArray(value);
const text = (value, max = 200) => typeof value === 'string' && value.trim().length > 0
  && value.length <= max && !/[\u0000-\u001f\u007f]/u.test(value);
const own = (value, key) => Object.prototype.hasOwnProperty.call(value, key);

function validContextAssessment(value) {
  const keys = ['contextGeneration', 'epoch', 'estimates', 'expectedRevision', 'integrity', 'observedAtMs', 'sourceRef', 'validUntilMs'];
  const estimateKeys = ['contextTailUpperBoundTokens', 'handoffTokens', 'nextWorkTokens',
    'recoveryTokens', 'safetyMarginTokens', 'sourceRef'];
  const count = n => Number.isSafeInteger(n) && n >= 0;
  const estimates = value?.estimates;
  return record(value) && Object.keys(value).sort().join(',') === keys.join(',')
    && text(value.epoch, 256) && /^[a-f0-9]{64}$/.test(value.contextGeneration)
    && count(value.expectedRevision) && count(value.observedAtMs) && count(value.validUntilMs)
    && text(value.sourceRef, 2048) && ['verified', 'degraded', 'unknown'].includes(value.integrity)
    && record(estimates) && Object.keys(estimates).sort().join(',') === estimateKeys.join(',')
    && text(estimates.sourceRef, 2048)
    && ['contextTailUpperBoundTokens', 'nextWorkTokens'].every(key => count(estimates[key]))
    && ['handoffTokens', 'recoveryTokens', 'safetyMarginTokens'].every(key => count(estimates[key]) && estimates[key] > 0);
}

function unavailableAssessment(reason, decision = 'unknown') {
  return {decision, capacityFit: 'unknown', sourceReleaseAllowed: false,
    scope: 'conditional-context-budget-only', reasons: [reason], windowTokens: null,
    remainingAfterReserves: null, efficiencyCeilingTokens: null};
}

function unavailable(reason) {
  return {schema: 'yiyuan-accord-native-state/v1', state: 'unavailable', reason, claimLimit: CLAIM_LIMIT};
}

function inspectionReason(error) {
  const code = error?.code || error?.message;
  return typeof code === 'string' && /^[A-Za-z][A-Za-z0-9_-]{0,95}$/.test(code)
    ? code : 'state-inspection-unavailable';
}

function nativeCallSource(params) {
  const meta = params._meta;
  const native = record(meta) && meta['x-codex-turn-metadata'];
  if (!record(native) || !text(meta.callId, 1024) || !text(native.thread_id)
      || !text(native.session_id) || !text(native.turn_id)) return null;
  return {kind: 'codex-mcp-request-metadata', callId: meta.callId,
    threadId: native.thread_id, sessionTreeId: native.session_id, turnId: native.turn_id,
    model: text(native.model, 200) ? native.model : null,
    hostVersion: text(native.codex_version, 100) ? native.codex_version : null};
}

function inspectNativeState(params, serverVersion = null) {
  if (!record(params) || params.name !== TOOL.name || !record(params.arguments)
      || Object.keys(params.arguments).some(key => !['cwd', 'includeContext', 'includeNativeInputs', 'contextMaxAgeMs', 'contextAssessment'].includes(key))
      || !own(params.arguments, 'cwd')
      || own(params.arguments, 'includeContext') && typeof params.arguments.includeContext !== 'boolean'
      || own(params.arguments, 'includeNativeInputs') && typeof params.arguments.includeNativeInputs !== 'boolean'
      || own(params.arguments, 'contextAssessment') && !validContextAssessment(params.arguments.contextAssessment)
      || own(params.arguments, 'contextMaxAgeMs') && (params.arguments.includeContext !== true
        && !own(params.arguments, 'contextAssessment')
        || !Number.isSafeInteger(params.arguments.contextMaxAgeMs) || params.arguments.contextMaxAgeMs <= 0)
      || !text(params.arguments.cwd, 4096) || !path.isAbsolute(params.arguments.cwd)) {
    return {isError: true, value: unavailable('explicit-workspace-required')};
  }
  // The argument schema exposes no selectable identity, operation or storage path;
  // an epoch can only bind advisory evidence to an already observed receipt.
  const source = nativeCallSource(params);
  if (!source) {
    return {isError: true, value: unavailable('native-call-metadata-unavailable')};
  }
  const workspace = {cwd: params.arguments.cwd, binding: 'caller-selected'};
  const currentHost = source.model && source.hostVersion ? {threadId: source.threadId, turnId: source.turnId,
    model: source.model, hostVersion: source.hostVersion, sourceRef: `codex-mcp-call:${source.callId}`} : null;
  let checkpoint;
  if (source.threadId !== source.sessionTreeId) {
    // In the inspected host, Hook session_id is shared by a session tree.
    // A descendant must not silently adopt that shared checkpoint as its own.
    checkpoint = {state: 'unavailable', reason: 'shared-session-scope-requires-reconciliation'};
  } else {
    try {
      checkpoint = {state: 'observed', snapshot: operate({op: 'status',
        session_id: source.sessionTreeId, cwd: params.arguments.cwd,
        nativeInputEvidence: params.arguments.includeNativeInputs === true,
        ...(currentHost ? {currentHost} : {})})};
    } catch (error) {
      checkpoint = {state: 'unavailable', reason: inspectionReason(error)};
    }
  }
  const value = {schema: 'yiyuan-accord-native-state/v1', state: 'observed-call-context',
    source, workspace, checkpoint, claimLimit: CLAIM_LIMIT};
  value.runtime = {schema: 'yiyuan-accord-loaded-runtime/v1', serverVersion,
    processId: process.pid, modulePathAtLoad: __filename,
    fingerprintFormat: 'sha256-of-function-prototype-toString',
    functionSha256: {...(loadedFunctionSha256 || {}), inspectNativeState:
      crypto.createHash('sha256').update(Function.prototype.toString.call(inspectNativeState)).digest('hex'),
      manageTaskState: crypto.createHash('sha256').update(Function.prototype.toString.call(manageTaskState)).digest('hex')},
    claimLimit: 'This responder and listed loaded function bodies only; excludes closures, constants, full package, other Hook processes, behavior, authority and process-control permission.'};
  if (params.arguments.includeContext === true) {
    const unknown = reason => ({state: 'unknown', reason, sourceReleaseAllowed: false});
    if (checkpoint.state !== 'observed') value.context = unknown(checkpoint.reason);
    else if (!currentHost) value.context = unknown('current-host-binding-missing');
    else {
      try {
        const observed = operate({op: 'observe-context', session_id: source.sessionTreeId,
          cwd: params.arguments.cwd, currentHost,
          maxAgeMs: params.arguments.contextMaxAgeMs ?? 30000});
        value.context = observed.epoch === checkpoint.snapshot.epoch
          ? observed : unknown('input-changed-between-state-and-context');
      } catch (error) { value.context = unknown(inspectionReason(error)); }
    }
  }
  if (own(params.arguments, 'contextAssessment')) {
    const supplied = params.arguments.contextAssessment;
    if (checkpoint.state !== 'observed') {
      value.contextAssessment = unavailableAssessment(checkpoint.reason);
    } else {
      const conditions = currentHost ? {threadId: currentHost.threadId, turnId: currentHost.turnId,
        hostVersion: currentHost.hostVersion, model: currentHost.model,
        contextGeneration: supplied.contextGeneration} : null;
      try {
        value.contextAssessment = operate({op: 'assess-context', session_id: source.sessionTreeId,
          cwd: params.arguments.cwd, epoch: supplied.epoch,
          expectedRevision: supplied.expectedRevision, conditions, nativeContext: true,
          ...(currentHost ? {currentHost} : {}), maxAgeMs: params.arguments.contextMaxAgeMs ?? 30000,
          assessment: {conditions, epoch: supplied.epoch, observedAtMs: supplied.observedAtMs,
            validUntilMs: supplied.validUntilMs, sourceRef: supplied.sourceRef,
            integrity: supplied.integrity, estimates: supplied.estimates}});
      } catch (error) {
        value.contextAssessment = unavailableAssessment(inspectionReason(error));
      }
    }
  }
  if (Buffer.byteLength(JSON.stringify(value)) > MAX_RESULT) {
    const snapshot = value.checkpoint.snapshot;
    const saved = snapshot?.checkpoint;
    const locator = snapshot?.checkpointSource;
    if (saved && locator && typeof locator.path === 'string' && path.isAbsolute(locator.path)
        && /^[a-f0-9]{64}$/.test(locator.sha256)) {
      // Preserve all input/recovery gates. This is a partial observation, never
      // an empty contract or permission to drop omitted outcomes and conditions.
      value.checkpoint = {...value.checkpoint, snapshot: {...snapshot,
        checkpoint: {epoch: saved.epoch, canContinue: saved.canContinue,
          details: 'omitted-bounded-result'},
        inspection: snapshot.inspection ? {
          status: snapshot.inspection.status,
          ...(own(snapshot.inspection, 'error') ? {error: snapshot.inspection.error} : {}),
          details: 'omitted-bounded-result',
        } : null,
      }};
      value.detailRead = 'Read checkpointSource.path and verify SHA-256 over the same bytes you parse for the full saved contract. '
        + 'The file contains saved input baselines and output predicates, not current per-file inspection results or new authority. '
        + 'Independently inspect business files when those current results are needed. Before dependent effects, '
        + 'reconcile the current input and re-inspect epoch, revision, checkpointSource.sha256, pause and recovery flags; '
        + 'a changed or unavailable source remains unresolved. Do not replace omitted details with empty values.';
      if (Buffer.byteLength(JSON.stringify(value)) <= MAX_RESULT) return {isError: false, value};
    }
    const evidence = snapshot?.nativeInputEvidence;
    if (evidence && Array.isArray(evidence.records)) {
      // Keep the observation and all recovery gates; missing detail is not an
      // empty input set. The existing helper can read the complete evidence.
      const {records, pendingInputs, enrichments, cursor, ...summary} = evidence;
      value.checkpoint.snapshot.nativeInputEvidence = {...summary,
        details: 'omitted-bounded-result',
        counts: {records: records.length, pendingInputs: pendingInputs?.length ?? 0,
          enrichments: enrichments?.length ?? 0},
        detailRead: {helperPath: path.join(__dirname, 'task-checkpoint.cjs'),
          request: {op: 'status', session_id: source.sessionTreeId, cwd: workspace.cwd,
            nativeInputEvidence: true, ...(currentHost ? {currentHost} : {})},
          expected: {epoch: snapshot.epoch, revision: snapshot.revision, storage: snapshot.storage},
          rule: 'Use an available compatible helper with the same storage selection and host environment. '
            + 'This status request is read-only; inspect its complete evidence and source parts before reconciliation. '
            + 'Compare storage, epoch, revision and native source/host; changed or unavailable evidence remains unresolved. '
            + 'Omitted lists are not empty; this reply supplies no reconciliation cursor or new authority.'}};
      if (Buffer.byteLength(JSON.stringify(value)) <= MAX_RESULT) return {isError: false, value};
    }
    return {isError: true, value: unavailable('bounded-state-result-exceeded')};
  }
  return {isError: false, value};
}

function readTaskInput(params) {
  const rejected = reason => ({isError: true, value: {
    schema: 'yiyuan-accord-native-input/v1', state: 'unavailable', reason, claimLimit: INPUT_CLAIM_LIMIT}});
  if (!record(params) || params.name !== INPUT_TOOL.name || !record(params.arguments)
      || Object.keys(params.arguments).some(key => !own(INPUT_TOOL.inputSchema.properties, key))
      || !own(params.arguments, 'cwd') || !text(params.arguments.cwd, 4096)
      || !path.isAbsolute(params.arguments.cwd)) return rejected('explicit-workspace-required');
  const args = params.arguments;
  if (['index', 'offset'].some(key => own(args, key) && (!Number.isSafeInteger(args[key]) || args[key] < 0))
      || own(args, 'maxChars') && (!Number.isSafeInteger(args.maxChars) || args.maxChars < 1 || args.maxChars > 16000)
      || own(args, 'expectedReceiptEpoch') && !text(args.expectedReceiptEpoch, 256)) return rejected('invalid-input-page');
  if (own(args, 'sourcePart')) {
    const selected = args.sourcePart;
    if (own(args, 'index') || !own(args, 'expectedReceiptEpoch') || !record(selected) ||
        Object.keys(selected).sort().join(',') !== 'evidenceCursor,partIndex,recordOffset,recordSha256' ||
        !validCursor(selected.evidenceCursor) || !Number.isSafeInteger(selected.partIndex) || selected.partIndex < 0 ||
        !Number.isSafeInteger(selected.recordOffset) || selected.recordOffset < 0 ||
        !/^[a-f0-9]{64}$/.test(selected.recordSha256)) return rejected('invalid-native-source-selection');
  }
  if (['index', 'offset'].some(key => own(args, key) && args[key] !== 0)
      && !own(args, 'expectedReceiptEpoch')) return rejected('captured-input-basis-required');
  const source = nativeCallSource(params);
  if (!source) return rejected('native-call-metadata-unavailable');
  if (source.threadId !== source.sessionTreeId) return rejected('shared-session-scope-requires-reconciliation');
  let input;
  try {
    input = operate({op: 'read-native-input', session_id: source.sessionTreeId, cwd: args.cwd,
      ...(!own(args, 'sourcePart') ? {index: own(args, 'index') ? args.index : undefined} :
        {sourcePart: args.sourcePart, expectedReceiptEpoch: args.expectedReceiptEpoch,
          ...(source.model && source.hostVersion ? {currentHost: {threadId: source.threadId, turnId: source.turnId,
            model: source.model, hostVersion: source.hostVersion, sourceRef: `codex-mcp-call:${source.callId}`}} : {})}),
      offset: own(args, 'offset') ? args.offset : undefined,
      maxChars: own(args, 'maxChars') ? args.maxChars : undefined});
  } catch (error) { return rejected(inspectionReason(error)); }
  if (own(args, 'expectedReceiptEpoch') && args.expectedReceiptEpoch !== input.receiptEpoch) {
    return rejected('captured-input-basis-changed');
  }
  // Pin subsequent pages to this observed basis; never rewrite or replay it.
  if (input.next) input = {...input, next: {...input.next, expectedReceiptEpoch: input.receiptEpoch}};
  const {imageContent, ...description} = input;
  const value = {schema: 'yiyuan-accord-native-input/v1', state: 'observed-input-page',
    source, workspace: {cwd: args.cwd, binding: 'caller-selected'}, input: description, claimLimit: INPUT_CLAIM_LIMIT};
  if (Buffer.byteLength(JSON.stringify(value)) > MAX_RESULT) return rejected('bounded-input-result-exceeded');
  return {isError: false, value, ...(imageContent ? {imageContent} : {})};
}

function manageTaskState(params) {
  const rejected = (reason, effect = 'not-requested') => ({isError: true, value: {
    schema: 'yiyuan-accord-native-state-mutation/v1', state: 'unavailable', reason,
    ...(reason === 'native-input-reconciliation-required' ? {recoveryHint:
      'Inspect with includeNativeInputs; review actual source-derived pending input and limits, reconcile-input using its cursor, then explicitly bind the reviewed contract under the new epoch. Pause/recovery flags remain.'} : {}),
    effect, claimLimit: MANAGE_CLAIM_LIMIT}});
  const args = params?.arguments;
  const common = ['action', 'cwd', 'epoch', 'expectedRevision'];
  const byAction = {
    bind: ['canContinue', 'inputRevisions', 'inputs', 'nextAction', 'outputs', 'result',
      'resumeReason', 'revisionReason', 'unresolved'],
    pause: ['reason'],
    retire: ['disposition', 'reason'],
    'reconcile-input': ['evidenceCursor'],
  };
  const boundedText = (value, max) => typeof value === 'string' && value.trim().length > 0
    && value.length <= max;
  if (!record(params) || params.name !== MANAGE_TOOL.name || !record(args)
      || !['bind', 'pause', 'retire', 'reconcile-input'].includes(args.action)) {
    return rejected('invalid-task-state-operation');
  }
  const unsupportedFields = Object.keys(args)
    .filter(key => !common.includes(key) && !byAction[args.action].includes(key)).sort();
  if (unsupportedFields.length) {
    const error = rejected('invalid-task-state-operation');
    // Only schema-owned names are public. Locate other keys by their key-order
    // positions, never by reflecting caller-chosen names or values.
    error.value.unsupportedFields = unsupportedFields.filter(key => own(MANAGE_TOOL.inputSchema.properties, key));
    const ranges = [];
    Object.keys(args).forEach((key, index) => {
      if (own(MANAGE_TOOL.inputSchema.properties, key)) return;
      const last = ranges[ranges.length - 1];
      if (last && last[1] === index - 1) last[1] = index;
      else ranges.push([index, index]);
    });
    // Inclusive zero-based Object.keys positions keep even many private names
    // locatable with bounded diagnostics (at most one range per public key gap).
    error.value.unknownFieldRanges = ranges;
    return error;
  }
  if (!common.every(key => own(args, key)) || !boundedText(args.cwd, 4096)
      || !path.isAbsolute(args.cwd) || !text(args.epoch, 256)
      || !Number.isSafeInteger(args.expectedRevision) || args.expectedRevision < 0
      || Buffer.byteLength(JSON.stringify(args)) > MAX_FRAME) return rejected('invalid-task-state-operation');
  if (args.action === 'bind') {
    const required = ['result', 'inputs', 'outputs', 'nextAction', 'canContinue'];
    const missingFields = required.filter(key => !own(args, key));
    if (missingFields.length) {
      const error = rejected('invalid-task-state-binding');
      error.value.requiredFields = required;
      error.value.missingFields = missingFields;
      return error;
    }
    const observed = value => record(value) && typeof value.present === 'boolean'
      && Object.keys(value).sort().join(',') === (value.present ? 'present,sha256' : 'present')
      && (!value.present || typeof value.sha256 === 'string' && /^[a-f0-9]{64}$/.test(value.sha256));
    const output = value => record(value) && Object.keys(value).every(key => ['path', 'sha256', 'json'].includes(key))
      && boundedText(value.path, 4096)
      && (!own(value, 'sha256') || typeof value.sha256 === 'string' && /^[a-f0-9]{64}$/.test(value.sha256))
      && (!own(value, 'json') || record(value.json));
    const revision = value => record(value)
      && Object.keys(value).sort().join(',') === 'observed,path,reason'
      && boundedText(value.path, 4096) && observed(value.observed) && boundedText(value.reason, 2048);
    if (!boundedText(args.result, 16384)
        || !boundedText(args.nextAction, 16384) || typeof args.canContinue !== 'boolean'
        || !Array.isArray(args.inputs) || !Array.isArray(args.outputs) || args.outputs.length === 0
        || args.inputs.length + args.outputs.length > 100
        || args.inputs.some(value => !boundedText(value, 4096)) || args.outputs.some(value => !output(value))
        || own(args, 'revisionReason') && !boundedText(args.revisionReason, 2048)
        || own(args, 'resumeReason') && !boundedText(args.resumeReason, 2048)
        || own(args, 'inputRevisions') && (!Array.isArray(args.inputRevisions)
          || args.inputRevisions.length > 100 || args.inputRevisions.some(value => !revision(value)))
        || own(args, 'unresolved') && (!Array.isArray(args.unresolved) || args.unresolved.length > 32
          || args.unresolved.some(value => !boundedText(value, 2048)))) {
      return rejected('invalid-task-state-binding');
    }
  } else if (args.action === 'pause') {
    if (!own(args, 'reason') || !boundedText(args.reason, 2048)) return rejected('invalid-task-state-pause');
  } else if (args.action === 'reconcile-input') {
    if (!validCursor(args.evidenceCursor)) {
      return rejected('invalid-native-input-evidence-cursor');
    }
  } else if (own(args, 'reason') && !boundedText(args.reason, 2048)
      || own(args, 'disposition') && (args.disposition !== 'user-cancelled' || !boundedText(args.reason, 2048))) {
    return rejected('invalid-task-state-retirement');
  }
  const source = nativeCallSource(params);
  if (!source) return rejected('native-call-metadata-unavailable');
  if (source.threadId !== source.sessionTreeId) return rejected('shared-session-scope-requires-reconciliation');
  const request = {op: args.action === 'reconcile-input' ? 'reconcile-native-input' : args.action, session_id: source.sessionTreeId, cwd: args.cwd,
    epoch: args.epoch, expectedRevision: args.expectedRevision, nativeTurnId: source.turnId,
    ...(source.model && source.hostVersion ? {currentHost: {threadId: source.threadId, turnId: source.turnId,
      model: source.model, hostVersion: source.hostVersion, sourceRef: `codex-mcp-call:${source.callId}`}} : {})};
  for (const key of byAction[args.action]) if (own(args, key)) request[key] = args[key];
  let observation;
  try { observation = operate(request); }
  catch (error) {
    const response = rejected(inspectionReason(error), 'unknown-check-post-state');
    const diagnostic = nativeInputDiagnostic(error);
    if (diagnostic) response.value.nativeInputDiagnostic = diagnostic;
    return response;
  }
  let value = {schema: 'yiyuan-accord-native-state-mutation/v1', state: 'observed-operation',
    action: args.action, source, workspace: {cwd: args.cwd, binding: 'caller-selected'},
    observation, claimLimit: MANAGE_CLAIM_LIMIT};
  if (Buffer.byteLength(JSON.stringify(value)) > MAX_RESULT) {
    const summary = Object.fromEntries(['revision', 'mode', 'retired', 'scope']
      .filter(key => own(observation, key)).map(key => [key, observation[key]]));
    const status = observation.inspection?.status ?? observation.pending?.status;
    if (typeof status === 'string') summary.inspection = {status};
    summary.details = 'omitted-bounded-result';
    value = {...value, observation: summary};
  }
  return {isError: false, value};
}

function runtimeVersion(root = path.resolve(__dirname, '..')) {
  const manifest = path.join(root, '.codex-plugin', 'plugin.json');
  const packaged = fs.existsSync(manifest);
  const data = JSON.parse(fs.readFileSync(packaged ? manifest : path.join(root, 'product', 'development.json'), 'utf8'));
  const version = packaged ? data.version : data.delivery?.version;
  if (!text(version, 200)) throw new Error('package-version-unavailable');
  return version;
}

function createHandler(version = runtimeVersion(), executionOptions = {}) {
  let initialized = false, ready = false;
  const execution = createNativeTaskExecution({...executionOptions, sourceOf: nativeCallSource});
  const error = (id, code, message) => ({jsonrpc: '2.0', id, error: {code, message}});
  const result = (id, value) => ({jsonrpc: '2.0', id, result: value});
  const handle = request => {
    if (!record(request) || request.jsonrpc !== '2.0' || !text(request.method, 100)) {
      return error(null, -32600, 'Invalid request');
    }
    if (!own(request, 'id')) {
      if (request.method === 'notifications/initialized' && initialized) ready = true;
      if (request.method === 'notifications/cancelled' && ready) execution.cancelRequest(request.params?.requestId).catch(() => {});
      return null;
    }
    const id = request.id;
    if (!(text(id, 1024) || Number.isSafeInteger(id))) return error(null, -32600, 'Invalid request id');
    if (request.method === 'ping') return result(id, {});
    if (request.method === 'initialize') {
      if (initialized) return error(id, -32600, 'Already initialized');
      if (!record(request.params) || !text(request.params.protocolVersion, 40)
          || !record(request.params.capabilities) || !record(request.params.clientInfo)
          || !text(request.params.clientInfo.name, 200) || !text(request.params.clientInfo.version, 100)) {
        return error(id, -32602, 'Invalid initialization');
      }
      initialized = true;
      return result(id, {protocolVersion: PROTOCOL, capabilities: {tools: {listChanged: false}},
        serverInfo: {name: 'yiyuan-accord-native-state', version}});
    }
    if (!ready) return error(id, -32002, 'Initialization required');
    if (request.method === 'tools/list') {
      if (request.params != null && (!record(request.params) || request.params.cursor != null)) {
        return error(id, -32602, 'Invalid tool-list parameters');
      }
      return result(id, {tools: [TOOL, INPUT_TOOL, MANAGE_TOOL, EXECUTION_TOOL]});
    }
    if (request.method === 'tools/call') {
      if (!record(request.params) || ![TOOL.name, INPUT_TOOL.name, MANAGE_TOOL.name, EXECUTION_TOOL.name].includes(request.params.name)) {
        return error(id, -32602, 'Unknown tool');
      }
      execution.observe(request.params);
      if (request.params.name === EXECUTION_TOOL.name) return execution.call(request.params, id).then(inspected =>
        result(id, {isError: inspected.isError, structuredContent: inspected.value,
          content: [{type: 'text', text: JSON.stringify(inspected.value)}]}));
      const inspected = request.params.name === TOOL.name ? inspectNativeState(request.params, version)
        : request.params.name === INPUT_TOOL.name ? readTaskInput(request.params) : manageTaskState(request.params);
      execution.observe(request.params);
      return result(id, {isError: inspected.isError, structuredContent: inspected.value,
        content: [{type: 'text', text: JSON.stringify(inspected.value)},
          ...(inspected.imageContent ? [inspected.imageContent] : [])]});
    }
    return error(id, -32601, 'Method not found');
  };
  handle.close = () => execution.close();
  return handle;
}

async function serve(input = process.stdin, output = process.stdout, version = runtimeVersion(), executionOptions = {}) {
  const handle = createHandler(version, executionOptions);
  const decoder = new TextDecoder('utf-8', {fatal: true});
  let pending = Buffer.alloc(0), writes = Promise.resolve();
  const inFlight = new Set();
  let outputClosed = false;
  const stopOutput = () => { outputClosed = true; input.destroy(); };
  for (const event of ['close', 'finish', 'error']) output.on(event, stopOutput);
  const waitForDrain = () => new Promise((resolve, reject) => {
    const finish = error => {
      output.removeListener('drain', drained);
      output.removeListener('error', failed);
      output.removeListener('close', closed);
      output.removeListener('finish', closed);
      input.removeListener('close', inputClosed);
      error ? reject(error) : resolve();
    };
    const drained = () => finish();
    const failed = () => finish(new Error('mcp-output-failed'));
    const closed = () => finish(new Error('mcp-output-closed'));
    const inputClosed = () => { if (!input.readableEnded) closed(); };
    output.once('drain', drained); output.once('error', failed);
    output.once('close', closed); output.once('finish', closed);
    input.once('close', inputClosed);
    if (outputClosed || output.destroyed || output.writableEnded
        || input.destroyed && !input.readableEnded) closed();
  });
  const emit = response => {
    if (response === null) return;
    writes = writes.then(async () => {
      if (outputClosed || output.destroyed || output.writableEnded) throw new Error('mcp-output-closed');
      if (!output.write(JSON.stringify(response) + '\n')) await waitForDrain();
    });
    writes.catch(() => {});
    return writes;
  };
  const dispatch = frame => {
    let request, response;
    try { request = JSON.parse(decoder.decode(frame)); }
    catch (_) { return emit({jsonrpc: '2.0', id: null, error: {code: -32700, message: 'Invalid JSON'}}); }
    if (inFlight.size >= 64 && record(request) && own(request, 'id')
        && request.method === 'tools/call' && request.params?.name === EXECUTION_TOOL.name) {
      return emit({jsonrpc: '2.0', id: request.id ?? null, error: {code: -32001, message: 'Too many pending requests'}});
    }
    try { response = handle(request); }
    catch (_) { return emit({jsonrpc: '2.0', id: request?.id ?? null, error: {code: -32603, message: 'Request failed'}}); }
    if (!response || typeof response.then !== 'function') return emit(response);
    const task = Promise.resolve(response).then(emit, () => emit({jsonrpc: '2.0', id: request.id ?? null,
      error: {code: -32603, message: 'Request failed; inspect prior effects'}})).finally(() => inFlight.delete(task));
    task.catch(() => {});
    inFlight.add(task);
  };
  try {
    for await (const chunk of input) {
      let offset = 0;
      while (offset < chunk.length) {
        if (outputClosed) throw new Error('mcp-output-closed');
        const newline = chunk.indexOf(10, offset), end = newline < 0 ? chunk.length : newline;
        if (pending.length + end - offset > MAX_FRAME) throw new Error('oversize-mcp-input');
        const frame = pending.length ? Buffer.concat([pending, chunk.subarray(offset, end)]) : chunk.subarray(offset, end);
        pending = newline < 0 ? Buffer.from(frame) : Buffer.alloc(0);
        if (newline < 0) break;
        await dispatch(frame); offset = newline + 1;
      }
    }
    if (pending.length) throw new Error('incomplete-mcp-input');
  } finally {
    try {
      await handle.close();
      await Promise.allSettled([...inFlight]);
      await writes;
      if (outputClosed) throw new Error('mcp-output-closed');
    } finally {
      for (const event of ['close', 'finish', 'error']) output.removeListener(event, stopOutput);
    }
  }
}

function main(versionReader = runtimeVersion) {
  return Promise.resolve().then(() => {
    const version = versionReader();
    // Windows cannot replace a cache directory held as a live process cwd.
    // Modules are loaded; every task workspace is supplied as an absolute path.
    // Preserve the original base of configured state, session, home and temp paths.
    for (const key of ['YIYUAN_ACCORD_TASK_STATE_DIR', 'CODEX_HOME', 'CODEX_CLI_PATH', 'HOME', 'USERPROFILE', 'TMPDIR', 'TMP', 'TEMP']) {
      if (process.env[key]) process.env[key] = path.resolve(process.env[key]);
    }
    process.chdir(require('node:os').homedir());
    return serve(process.stdin, process.stdout, version);
  }).catch(() => {
    process.stderr.write('Accord native-state transport stopped; inspect task state for prior operation effects before retrying.\n');
    process.exitCode = 1;
  });
}
if (require.main === module) main();
module.exports = {inspectNativeState, readTaskInput, manageTaskState, createHandler, serve, main, runtimeVersion};
