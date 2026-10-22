'use strict';

// Cooperative transfer from a host-owned MCP source to one caller-owned native
// target. The source is never impersonated on the target's App Server connection.
// Metadata/current/verification callbacks are trusted integration boundaries, not
// model-selected authority. No daemon, retry, GUI control or shutdown-survival claim.
const crypto = require('node:crypto');
const path = require('node:path');
const {performance} = require('node:perf_hooks');
const {spawn, spawnSync} = require('node:child_process');
const {EventEmitter} = require('node:events');
const {StringDecoder} = require('node:string_decoder');
const {createOwnedAppServerConnection} = require('./codex-connection.cjs');
const copy = value => JSON.parse(JSON.stringify(value));
const digest = value => crypto.createHash('sha256').update(JSON.stringify(value)).digest('hex');
const text = value => typeof value === 'string' && value.trim() && value.length <= 1024 * 1024;
const samePath = (a, b) => typeof a === 'string' && typeof b === 'string' &&
  (process.platform === 'win32' ? path.resolve(a).toLowerCase() === path.resolve(b).toLowerCase() : path.resolve(a) === path.resolve(b));
function reject(code) { throw Object.assign(new Error(code), {code}); }
function remaining(deadline) { const value = deadline - performance.now(); if (value <= 0) reject('DEADLINE_EXCEEDED'); return value; }
async function bounded(callback, deadline) {
  const wait = remaining(deadline);
  let timer;
  try { return await Promise.race([Promise.resolve().then(() => { remaining(deadline); return callback(); }), new Promise((_, no) => {
    timer = setTimeout(() => no(Object.assign(new Error('DEADLINE_EXCEEDED'), {code: 'DEADLINE_EXCEEDED'})), wait);
  })]); } finally { clearTimeout(timer); }
}
function sourceIdentity(value) {
  if (!value || value.kind !== 'codex-mcp-request-metadata' ||
      !['threadId', 'sessionTreeId', 'turnId', 'callId'].every(key => text(value[key]))) reject('SOURCE_IDENTITY_REQUIRED');
  if (value.threadId !== value.sessionTreeId) reject('SOURCE_SHARED_PARENT_IDENTITY');
  return Object.freeze(copy(value));
}

function createExternalHandoff(options) {
  const source = sourceIdentity(options.source);
  const {recorder, current, verify, nativeFactory} = options;
  if (!recorder || ['bindScope', 'begin', 'read', 'readScope', 'compareAndSet', 'settleExternal'].some(key => typeof recorder[key] !== 'function') ||
      [current, verify, nativeFactory].some(fn => typeof fn !== 'function')) reject('INTERNAL_DEPENDENCIES_REQUIRED');
  let state = {kind: 'external-source-handoff/v1', phase: 'new', source,
    writer: 'source', writerThreadId: source.threadId, pendingEffect: null,
    sourceRecovery: 'retained', nativeClosed: null, turnStarts: 0};
  let plan, basis, deadline, revision = null, lease = null, native = null;
  let busy = false, running = null, cancelled = false, cancelReason = null, closePromise = null;
  let activeTurn = null, recordCertain = true, sequence = 0, stopping = false;
  let deadlineTimer = null, nativeStartPending = false, lateNativeClosed = null;
  let skillPreparationPending = false;
  const seenTurns = new Set();
  const inspect = () => copy({...state, revision, busy, cancelRequested: cancelled,
    nativeStartPending, lateNativeClosed, skillPreparationPending,
    recovery: state.phase === 'held' || state.phase === 'cancelled-held'
      ? 'Inspect original request, target effects and scoped lease; do not replay this operation.' : null});
  function live() { remaining(deadline); if (cancelled) reject('CANCELLED'); }
  function record(delta) {
    if (!recordCertain || revision === null) reject('RECORDER_STATE_UNKNOWN');
    const next = {...state, ...copy(delta)};
    try {
      const receipt = recorder.compareAndSet(plan.transferId, revision, next, lease);
      const seen = recorder.read(plan.transferId, plan.scopeRef);
      if (seen.revision !== receipt.revision || digest(seen.lease) !== digest(receipt.lease) || digest(seen.state) !== digest(next)) reject('RECORDER_READBACK_CHANGED');
      revision = receipt.revision; lease = receipt.lease; state = next;
    } catch (error) { recordCertain = false; throw error; }
  }
  async function guard(stage) {
    live();
    const observed = copy(await bounded(() => current(stage), deadline));
    live();
    if (!observed || observed.sourceThreadId !== source.threadId || observed.sourceTurnId !== source.turnId) reject('SOURCE_IDENTITY_CHANGED');
    if (observed.inputComplete !== true || observed.recoveryRequired !== false) reject('SOURCE_INPUT_UNAVAILABLE');
    if (observed.paused !== false) reject('SOURCE_PAUSED');
    const q = observed.quiescence;
    if (!q || q.noInFlightEffects !== true || q.noOtherWriters !== true || !text(q.evidenceRef)) reject('SOURCE_NOT_QUIESCENT');
    const selected = Object.fromEntries(['epoch', 'revision', 'authorityRef', 'snapshotRef', 'protectedInputsDigest'].map(key => [key, observed[key]]));
    if (!text(selected.epoch) || !Number.isSafeInteger(selected.revision) || selected.revision < 0 ||
        !text(selected.authorityRef) || !text(selected.snapshotRef) || !/^[a-f0-9]{64}$/.test(selected.protectedInputsDigest)) reject('SOURCE_BASIS_UNAVAILABLE');
    if (basis && digest(selected) !== digest(basis)) reject('SOURCE_BASIS_CHANGED');
    if (!basis) basis = selected;
    if (revision !== null) {
      const scope = recorder.readScope(plan.scopeRef);
      if (scope.activeTransferId !== plan.transferId || scope.writerThreadId !== lease.writerThreadId || scope.token !== lease.token) reject('SCOPE_CHANGED');
    }
    return observed;
  }
  async function review(stage, supplied) {
    await guard('before-' + stage);
    const verdict = copy(await bounded(() => verify(stage, copy(supplied ?? null), inspect()), deadline));
    await guard('after-' + stage);
    if (verdict?.decision !== 'allow' || !text(verdict.evidenceRef)) reject('VERIFICATION_DENIED');
    return verdict.evidenceRef;
  }
  async function request(method, params, mutating = false) {
    await guard('before-' + method);
    const intent = mutating ? {kind: 'native-request', sequence: ++sequence, method, params: copy(params), requestRef: null} : null;
    if (intent) record({pendingEffect: intent,
      ...(method === 'turn/start' ? {turnStarts: state.turnStarts + 1} : {})});
    let sentRef = null;
    const response = copy(await bounded(() => native.request(method, copy(params), deadline, intent ? ref => {
      live();
      if (ref?.connectionId !== native.connectionId || ref.hostVersion !== native.hostVersion || ref.method !== method || !text(ref.requestId)) reject('REQUEST_REFERENCE_INVALID');
      sentRef = copy(ref); record({pendingEffect: {...intent, requestRef: sentRef}});
    } : undefined), deadline));
    if (intent) {
      if (!sentRef) reject('NATIVE_REQUEST_REFERENCE_MISSING');
      record({lastNativeReceipt: {method, response, request: {...intent, requestRef: sentRef}}});
    }
    await guard('after-' + method);
    if (intent) record({pendingEffect: null});
    return response;
  }
  async function turn(input, purpose) {
    if (purpose !== 'intake') await prepareSkill();
    const skillInput = purpose === 'first-continuation' ? state.preparedSkill?.nativeInput || [] : [];
    const scopeInput = plan.writeScope ? [{type: 'text', text:
      'Bound task write scope; this metadata grants no additional authority. Intake is read-only. ' +
      'Workspace sandbox capability does not authorize other effects. Preserve immutable inputs and follow the current reviewed delegation.\n' +
      JSON.stringify(plan.writeScope)}] : [];
    const started = await request('turn/start', {threadId: state.target.threadId,
      input: [...copy(skillInput), ...scopeInput, {type: 'text', text: input}],
      sandboxPolicy: purpose === 'intake' ? {type: 'readOnly'} : state.writePolicy?.sandbox || {type: 'readOnly'},
      ...(plan.effort ? {effort: plan.effort} : {})}, true);
    if (!text(started?.turn?.id) || seenTurns.has(started.turn.id)) {
      record({pendingEffect: {...state.lastNativeReceipt.request, identityUnknown: true, purpose}}); reject('TURN_IDENTITY_UNKNOWN');
    }
    seenTurns.add(started.turn.id);
    activeTurn = {threadId: state.target.threadId, turnId: started.turn.id};
    record({phase: purpose + '-running', pendingEffect: {kind: 'native-turn', ...activeTurn, purpose}});
    const result = copy(await bounded(() => native.waitTurn(activeTurn.threadId, activeTurn.turnId, deadline, () => guard(purpose)), deadline));
    await guard('after-' + purpose);
    const terminal = result?.terminal;
    if (terminal?.method !== 'turn/completed' || terminal.params?.threadId !== activeTurn.threadId ||
        terminal.params?.turn?.id !== activeTurn.turnId) reject('TARGET_TURN_NOT_COMPLETED');
    if (terminal.params.turn.status !== 'completed') {
      if (['interrupted', 'failed'].includes(terminal.params.turn.status)) {
        record({stoppedTurn: {...activeTurn, purpose, terminal: terminal.params.turn.status,
          observation: result}, pendingEffect: {...state.pendingEffect,
          terminal: terminal.params.turn.status, effectsUnreviewed: true}});
        activeTurn = null;
      }
      reject('TARGET_TURN_NOT_COMPLETED');
    }
    if (typeof result.output !== 'string' || Buffer.byteLength(result.output) > 1024 * 1024 ||
        !Array.isArray(result.events) || !result.events.length || result.events.some(event =>
          event.method !== 'item/completed' || event.threadId !== activeTurn.threadId || event.turnId !== activeTurn.turnId)) reject('TARGET_EVIDENCE_UNAVAILABLE');
    const observation = {...activeTurn, output: result.output, events: result.events,
      terminal: terminal.params.turn.status, observedAfterRelease: state.release?.kind === 'cooperative-duty-release'};
    activeTurn = null;
    record({phase: purpose + '-complete', pendingEffect: null, [purpose === 'post-release' ? 'postReleaseTurn' : purpose === 'first-continuation' ? 'firstContinuation' : 'intake']: observation});
  }
  async function prepareSkill() {
    if (!plan.skillRequest) return;
    if (typeof options.prepareSkill !== 'function') reject('SKILL_PREPARATION_UNAVAILABLE');
    await guard('before-skill-preparation');
    skillPreparationPending = true;
    const prepared = copy(await bounded(async () => {
      try { return await options.prepareSkill(plan.skillRequest); }
      catch (error) {
        state = {...state, skillPreparationFailure: {code: error.code || 'SKILL_PREPARATION_FAILED',
          process: copy(error.processState || null)}};
        throw error;
      } finally { skillPreparationPending = false; }
    }, deadline));
    const rows = prepared?.nativeInput, selected = prepared?.source;
    if (prepared?.schema !== 'yiyuan-accord-prepared-skill-input/v1' ||
        selected?.enabled !== true ||
        !Array.isArray(rows) || rows.length !== 2 || rows[0]?.type !== 'text' || !text(rows[0].text) ||
        rows[1]?.type !== 'skill' || rows[1].name !== selected.name || rows[1].path !== selected.path ||
        Object.keys(rows[0]).some(k => !['type', 'text'].includes(k)) ||
        Object.keys(rows[1]).some(k => !['type', 'name', 'path'].includes(k))) reject('SKILL_EXECUTION_NOT_ADMITTED');
    if (state.preparedSkill && digest({source: selected, nativeInput: rows}) !==
        digest({source: state.preparedSkill.source, nativeInput: state.preparedSkill.nativeInput})) reject('SKILL_SOURCE_CHANGED');
    await guard('after-skill-preparation');
    if (!state.preparedSkill) state = {...state, preparedSkill: prepared};
  }
  async function closeNative() {
    if (!native) return null;
    if (!closePromise) closePromise = Promise.resolve().then(() => native.close());
    return copy(await closePromise);
  }
  async function startNative() {
    record({pendingEffect: {kind: 'owned-native-start'}, nativeClosed: null});
    native = await bounded(async () => {
      try {
        nativeStartPending = true;
        const owned = await nativeFactory({cwd: plan.cwd, deadlineMs: plan.deadlineMs});
        if (stopping || cancelled || performance.now() >= deadline) {
          if (owned && typeof owned.close === 'function') lateNativeClosed = copy(await owned.close());
          reject('NATIVE_START_EXPIRED');
        }
        return owned;
      } finally { nativeStartPending = false; }
    }, deadline);
    if (!native || !text(native.connectionId) || !text(native.hostVersion) || ['request', 'waitTurn', 'close'].some(key => typeof native[key] !== 'function')) reject('NATIVE_OWNER_INVALID');
    await guard('native-started');
    record({connection: {connectionId: native.connectionId, hostVersion: native.hostVersion}, pendingEffect: null});
  }
  async function prepareWritePolicy() {
    if (plan.sandbox !== 'workspace-write') return;
    const evidenceRef = await review('write-prepare', {writeScope: plan.writeScope,
      claimLimit: 'Review current task authorization, output baselines, immutable inputs and single writer before any permission transition. Native policy is checked separately after cold resume.'});
    record({phase: 'write-policy-transition', pendingEffect: {kind: 'owned-native-close'}});
    const closed = await closeNative(), priorConnection = state.connection;
    record({nativeClosed: closed});
    if (closed?.closed !== true || closed.primaryProcessClosed !== true || closed.exitObserved !== true || closed.closeObserved !== true ||
        closed.exitCode !== 0 || closed.forced !== false || closed.signal !== null) reject('NATIVE_CLOSE_UNVERIFIED');
    record({priorNative: {connection: priorConnection, closure: closed, intakeReceipt: state.lastNativeReceipt}, pendingEffect: null,
      verification: {...state.verification, writePrepare: evidenceRef}});
    native = null; closePromise = null;
    await startNative();
    if (native.hostVersion !== priorConnection.hostVersion || native.connectionId === priorConnection.connectionId) reject('NATIVE_REPLACEMENT_MISMATCH');
    const requirements = await request('configRequirements/read', {});
    if (!requirements || !Object.hasOwn(requirements, 'requirements') ||
        requirements.requirements !== null && (typeof requirements.requirements !== 'object' || Array.isArray(requirements.requirements))) reject('NATIVE_REQUIREMENTS_UNAVAILABLE');
    const limits = requirements.requirements;
    if (limits?.allowedSandboxModes != null && (!Array.isArray(limits.allowedSandboxModes) || !limits.allowedSandboxModes.includes('workspace-write')) ||
        limits?.allowedApprovalPolicies != null && (!Array.isArray(limits.allowedApprovalPolicies) || !limits.allowedApprovalPolicies.includes('never'))) reject('NATIVE_REQUIREMENTS_DENIED');
    const resumed = await request('thread/resume', {threadId: state.target.threadId, excludeTurns: true,
      sandbox: 'workspace-write', approvalPolicy: 'never', config: {
        'sandbox_workspace_write.writable_roots': [], 'sandbox_workspace_write.network_access': false,
        'sandbox_workspace_write.exclude_tmpdir_env_var': true, 'sandbox_workspace_write.exclude_slash_tmp': true}}, true);
    const sandbox = resumed?.sandbox;
    record({writePolicy: {sandbox: sandbox || null, cwd: resumed?.cwd || null, approvalPolicy: resumed?.approvalPolicy || null,
      requirements: limits === null ? null : Object.fromEntries(['allowedSandboxModes', 'allowedApprovalPolicies', 'allowedPermissionProfiles', 'defaultPermissions', 'network'].filter(k => Object.hasOwn(limits, k)).map(k => [k, limits[k]])),
      requirementsSha256: digest(requirements), resumeRequest: state.lastNativeReceipt.request.requestRef}});
    if (resumed?.thread?.id !== state.target.threadId || resumed.thread.ephemeral !== false ||
        !path.isAbsolute(resumed.cwd || '') || !samePath(resumed.cwd, plan.cwd) || resumed.model !== plan.model || resumed.approvalPolicy !== 'never' ||
        sandbox?.type !== 'workspaceWrite' || sandbox.networkAccess !== false ||
        sandbox.excludeSlashTmp !== true || sandbox.excludeTmpdirEnvVar !== true ||
        !Array.isArray(sandbox.writableRoots) || sandbox.writableRoots.some(root => typeof root !== 'string' || !path.isAbsolute(root) || !samePath(root, plan.cwd)) ||
        Object.keys(sandbox).some(k => !['type', 'writableRoots', 'networkAccess', 'excludeSlashTmp', 'excludeTmpdirEnvVar'].includes(k))) reject('NATIVE_WRITE_POLICY_UNVERIFIED');
  }
  async function hold(error) {
    stopping = true;
    clearTimeout(deadlineTimer);
    let closure = null, closureError = null;
    try { closure = await closeNative(); } catch (e) { closureError = e.code || 'NATIVE_CLOSE_UNVERIFIED'; }
    const failed = {phase: cancelled ? 'cancelled-held' : 'held',
      failure: state.failure || {code: error.code || 'EXTERNAL_HANDOFF_FAILED', cancelReason, closureError,
        priorPhase: state.phase}, nativeClosed: closure};
    if (revision !== null && recordCertain) { try { record(failed); } catch (_) { state = {...state, ...failed}; } }
    else state = {...state, ...failed};
  }
  function execute(action) {
    if (busy) return Promise.reject(Object.assign(new Error('OPERATION_BUSY'), {code: 'OPERATION_BUSY'}));
    if (['held', 'cancelled-held', 'completed'].includes(state.phase)) return Promise.reject(Object.assign(new Error('OPERATION_NOT_REPLAYABLE'), {code: 'OPERATION_NOT_REPLAYABLE'}));
    busy = true;
    running = (async () => { try { await action(); }
      catch (error) { await hold(error); throw error; } finally { busy = false; }
      return inspect(); })();
    return running;
  }
  function prepare(raw) {
    if (busy) return Promise.reject(Object.assign(new Error('OPERATION_BUSY'), {code: 'OPERATION_BUSY'}));
    if (state.phase !== 'new') return Promise.reject(Object.assign(new Error('ALREADY_PREPARED'), {code: 'ALREADY_PREPARED'}));
    const allowed = new Set(['transferId', 'scopeRef', 'cwd', 'model', 'effort', 'intake', 'continuation', 'postRelease', 'deadlineMs', 'skillRequest', 'sandbox', 'writeScope']);
    if (!raw || Object.keys(raw).some(key => !allowed.has(key)) ||
        !['transferId', 'scopeRef', 'cwd', 'model', 'intake', 'continuation', 'postRelease'].every(key => text(raw[key])) ||
        !path.isAbsolute(raw.cwd) || !Number.isSafeInteger(raw.deadlineMs) || raw.deadlineMs <= Date.now() || raw.deadlineMs - Date.now() > 0x7fffffff ||
        (raw.effort !== undefined && !text(raw.effort)) ||
        ![undefined, 'read-only', 'workspace-write'].includes(raw.sandbox) ||
        (raw.sandbox === 'workspace-write' ? !raw.writeScope : raw.writeScope !== undefined)) return Promise.reject(Object.assign(new Error('INVALID_PLAN'), {code: 'INVALID_PLAN'}));
    plan = Object.freeze(copy(raw)); deadline = performance.now() + plan.deadlineMs - Date.now();
    deadlineTimer = setTimeout(async () => {
      stopping = true;
      try { await closeNative(); } catch (_) {}
      if (busy && running) { try { await running; } catch (_) {} }
      else if (state.phase !== 'completed') await hold(Object.assign(new Error('DEADLINE_EXCEEDED'), {code: 'DEADLINE_EXCEEDED'}));
    }, remaining(deadline));
    return execute(async () => {
      state = {...state, phase: 'preparing'};
      await guard('prepare');
      await prepareSkill();
      const prepareEvidence = await review('prepare', {plan, basis});
      const binding = recorder.bindScope(plan.scopeRef, source.threadId);
      if (binding.scope.writerThreadId !== source.threadId || binding.scope.activeTransferId !== null) reject('SCOPE_CHANGED');
      state = {...state, transferId: plan.transferId, scopeRef: plan.scopeRef,
        planDigest: digest({plan, source, basis}), basis, phase: 'prepared',
        plan: copy(plan), target: null, verification: {prepare: prepareEvidence}};
      const begun = recorder.begin(plan.transferId, state.planDigest, state);
      if (begun.created !== true) reject('TRANSFER_ALREADY_EXISTS');
      revision = begun.revision; lease = begun.lease;
      await startNative();
      const started = await request('thread/start', {cwd: plan.cwd, model: plan.model,
        ephemeral: false, sandbox: 'read-only', approvalPolicy: 'never'}, true);
      if (!text(started?.thread?.id) || started.thread.id === source.threadId || started.thread.ephemeral !== false) {
        record({pendingEffect: {...state.lastNativeReceipt.request, identityUnknown: true, receipt: started}}); reject('TARGET_IDENTITY_UNKNOWN');
      }
      record({target: {threadId: started.thread.id}, phase: 'target-created'});
      if (plan.sandbox === 'workspace-write' && (started.sandbox?.type !== 'readOnly' ||
          started.approvalPolicy !== 'never' || !samePath(started.cwd, plan.cwd))) reject('NATIVE_INITIAL_POLICY_UNVERIFIED');
      const targetEvidence = await review('target-created', started);
      record({verification: {...state.verification, targetCreated: targetEvidence}});
      await turn(plan.intake, 'intake');
      record({phase: 'awaiting-intake-review'});
    });
  }
  function commit(supplied) {
    if (state.phase !== 'awaiting-intake-review') return Promise.reject(Object.assign(new Error('INTAKE_REVIEW_NOT_READY'), {code: 'INTAKE_REVIEW_NOT_READY'}));
    return execute(async () => {
      await prepareSkill();
      await prepareWritePolicy();
      const evidenceRef = await review('commit', supplied);
      record({phase: 'writer-transferred', writer: 'target', writerThreadId: state.target.threadId,
        verification: {...state.verification, commit: evidenceRef}});
      await turn(plan.continuation, 'first-continuation');
      record({phase: 'awaiting-release-review'});
    });
  }
  function release(supplied) {
    if (state.phase !== 'awaiting-release-review') return Promise.reject(Object.assign(new Error('RELEASE_REVIEW_NOT_READY'), {code: 'RELEASE_REVIEW_NOT_READY'}));
    return execute(async () => {
      await prepareSkill();
      const evidenceRef = await review('release', supplied);
      record({phase: 'external-source-duty-released', sourceRecovery: 'controller-owned',
        release: {kind: 'cooperative-duty-release', sourceThreadId: source.threadId, callId: source.callId,
          epoch: basis.epoch, evidenceRef, sequence: ++sequence},
        verification: {...state.verification, release: evidenceRef}});
      await turn(plan.postRelease, 'post-release');
      const idle = await request('thread/read', {threadId: state.target.threadId});
      if (idle?.thread?.id !== state.target.threadId || idle.thread.ephemeral !== false || idle.thread.status?.type !== 'idle') reject('TARGET_NOT_IDLE');
      const resultEvidence = await review('result', {postReleaseTurn: state.postReleaseTurn, idle});
      record({phase: 'closing-native', verification: {...state.verification, result: resultEvidence}});
      const closure = await closeNative();
      if (closure?.closed !== true || !Number.isInteger(closure.exitCode) || closure.forced !== false || closure.exitCode !== 0) reject('NATIVE_CLOSE_UNVERIFIED');
      await guard('closed');
      const closedEvidence = await review('closed', closure);
      record({phase: 'external-completed', pendingEffect: null, nativeClosed: closure,
        verification: {...state.verification, closed: closedEvidence}});
      const settled = recorder.settleExternal(plan.transferId, revision, lease);
      const scope = recorder.readScope(plan.scopeRef);
      if (digest(scope) !== digest(settled.scope)) reject('SETTLE_READBACK_CHANGED');
      revision = settled.revision; lease = {scopeRef: scope.scopeRef, transferId: null, writerThreadId: scope.writerThreadId, token: scope.token};
      state = {...state, phase: 'completed', settled: true};
      clearTimeout(deadlineTimer);
    });
  }
  async function cancel(reason) {
    if (!text(reason)) reject('CANCEL_REASON_REQUIRED');
    if (state.phase === 'completed') return inspect();
    cancelled = true; cancelReason = reason;
    clearTimeout(deadlineTimer);
    // Only this executor's process is closed; no source, daemon or foreign PID.
    try { await closeNative(); } catch (_) {}
    if (busy && running) { try { await running; } catch (_) {} }
    else await hold(Object.assign(new Error('CANCELLED'), {code: 'CANCELLED'}));
    return inspect();
  }
  return Object.freeze({prepare, commit, release, cancel, inspect});
}

// This process owner is deliberately separate from transfer policy. The passive
// notification collector only keeps bounded target message facts; the borrowed
// connection remains the sole RPC requester, responder and request-queue consumer.
async function createOwnedNativeRunner(options) {
  if (!path.isAbsolute(options.executable || '') || !path.isAbsolute(options.cwd || '') || !text(options.hostVersion)) reject('NATIVE_START_CONFIGURATION_REQUIRED');
  const timeoutMs = options.cleanupTimeoutMs ?? 5000;
  if (!Number.isInteger(timeoutMs) || timeoutMs < 100 || timeoutMs > 30000) reject('INVALID_CLEANUP_TIMEOUT');
  const nativeArgs = options.args ?? ['app-server', '--listen', 'stdio://'];
  if (!Array.isArray(nativeArgs) || nativeArgs.some(value => typeof value !== 'string' || value.includes('\0'))) reject('INVALID_NATIVE_ARGUMENTS');
  const proc = spawn(options.executable, nativeArgs,
    {cwd: options.cwd, windowsHide: true, stdio: ['pipe', 'pipe', 'pipe'], detached: process.platform !== 'win32'});
  const ownedPid = proc.pid ?? null;
  let exited = false, closeObserved = false, exitCode = null, exitSignal = null, processError = null;
  const exitedPromise = new Promise(resolve => {
    proc.once('error', error => { processError = error; });
    proc.once('exit', (code, signal) => { exited = true; exitCode = code; exitSignal = signal; });
    proc.once('close', (code, signal) => { closeObserved = true; exitCode = code; exitSignal = signal; resolve(); });
  });
  proc.stderr.on('data', () => {});
  proc.stdin.on('error', () => {});
  let armed = null, closedPromise = null, parseBuffer = '', collectorFailure = null, outputBytes = 0;
  const decoder = new StringDecoder('utf8');
  const messages = [], events = [];
  const input = new EventEmitter();
  input.write = (bytes, done) => {
    try {
      const frame = JSON.parse(bytes.toString('utf8'));
      if (armed && frame.method) {
        const expected = armed; armed = null;
        if (frame.method !== expected.method || digest(frame.params) !== expected.paramsDigest) reject('OUTBOUND_REQUEST_MISMATCH');
        expected.callback({connectionId, hostVersion: options.hostVersion, requestId: String(frame.id), method: frame.method});
      }
      proc.stdin.write(bytes, done);
    } catch (error) { done(error); }
  };
  const connectionId = 'accord-external:' + crypto.randomUUID();
  const connection = createOwnedAppServerConnection({stdin: input, stdout: proc.stdout, connectionId, hostVersion: options.hostVersion});
  function collect(bytes) {
    if (collectorFailure) return;
    parseBuffer += decoder.write(bytes);
    if (Buffer.byteLength(parseBuffer) > 2 * 1024 * 1024) { collectorFailure = 'NATIVE_EVIDENCE_LIMIT'; return; }
    let end;
    while ((end = parseBuffer.indexOf('\n')) >= 0) {
      const line = parseBuffer.slice(0, end); parseBuffer = parseBuffer.slice(end + 1);
      let frame; try { frame = JSON.parse(line); } catch (_) { collectorFailure = 'NATIVE_EVIDENCE_INVALID'; return; }
      if (frame.method !== 'item/completed') continue;
      const p = frame.params, item = p?.item;
      if (!text(p?.threadId) || !text(p?.turnId) || !item) continue;
      events.push({method: frame.method, threadId: p.threadId, turnId: p.turnId, itemType: item.type});
      if (events.length > 4096) { collectorFailure = 'NATIVE_EVIDENCE_LIMIT'; return; }
      if (item.type === 'agentMessage' && typeof item.text === 'string') {
        outputBytes += Buffer.byteLength(item.text);
        if (outputBytes > 1024 * 1024) { collectorFailure = 'NATIVE_EVIDENCE_LIMIT'; return; }
        messages.push({threadId: p.threadId, turnId: p.turnId, text: item.text});
      }
    }
  }
  proc.stdout.on('data', collect);
  async function close() {
    if (closedPromise) return closedPromise;
    closedPromise = (async () => {
      let forced = false, terminationAttempt = null, terminationExitCode = null, terminationError = null;
      if (!exited) proc.stdin.end();
      let timer;
      try { await Promise.race([exitedPromise, new Promise(resolve => { timer = setTimeout(resolve, timeoutMs); })]); }
      finally { clearTimeout(timer); }
      if (!closeObserved && !exited && ownedPid !== null && proc.pid === ownedPid && proc.exitCode === null && proc.signalCode === null) {
        forced = true;
        if (process.platform === 'win32') {
          terminationAttempt = 'owned-pid-tree';
          // Do not queue a later PID-only kill. Start the bounded helper while
          // this exact ChildProcess still owns the un-reaped process handle;
          // the event loop cannot process its exit/close and release that handle
          // during spawnSync. An already observed exit never enters this path.
          const killed = spawnSync(path.join(process.env.SystemRoot || 'C:\\Windows', 'System32', 'taskkill.exe'),
            ['/PID', String(ownedPid), '/T', '/F'], {stdio: 'ignore', windowsHide: true, shell: false, timeout: timeoutMs});
          terminationExitCode = killed.status;
          terminationError = killed.error?.code || null;
        } else {
          terminationAttempt = 'owned-process-group';
          try { process.kill(-ownedPid, 'SIGKILL'); } catch (error) { terminationError = error.code || 'GROUP_STOP_FAILED'; }
        }
        try { await bounded(() => exitedPromise, performance.now() + timeoutMs); } catch (_) { /* Retain the unknown post-state below. */ }
      }
      connection.close(); proc.stdout.off('data', collect);
      if (!closeObserved) {
        // A launcher may have exited while descendants keep inherited pipes.
        // Closing our pipe ends is not evidence those descendants exited. Never
        // signal the old PID, guess zero descendants, or keep this caller hung.
        proc.stdin.destroy(); proc.stdout.destroy(); proc.stderr.destroy(); proc.unref();
      }
      const primaryProcessClosed = exited && closeObserved;
      return {closed: primaryProcessClosed && !forced, primaryProcessClosed,
        pid: ownedPid, exitObserved: exited, closeObserved, exitCode, signal: exitSignal,
        forced, terminationAttempt, terminationExitCode, terminationError,
        closureScope: 'owned-launcher-and-stdio; descendant effects require independent verification',
        descendantVerification: !closeObserved && exited ? 'unknown-launcher-exited-with-open-pipes' : 'not-independently-observed',
        recoveryRequired: forced || !primaryProcessClosed,
        ...(processError ? {processError: processError.code || 'SPAWN_FAILED'} : {})};
    })();
    return closedPromise;
  }
  try {
    const deadline = performance.now() + Math.max(1, options.deadlineMs - Date.now());
    await connection.transport.request('initialize', {clientInfo: {name: 'yiyuan_accord_external_handoff', version: '1'}}, deadline);
    await connection.transport.notify('initialized', {}, deadline);
  } catch (error) { error.processState = await close(); throw error; }
  return Object.freeze({connectionId, hostVersion: options.hostVersion,
    async request(method, params, deadline, beforeSend) {
      if (armed) reject('NATIVE_REQUEST_BUSY');
      if (beforeSend) armed = {method, paramsDigest: digest(params), callback: beforeSend};
      try { return await connection.transport.request(method, params, deadline); }
      finally { armed = null; }
    },
    async waitTurn(threadId, turnId, deadline, check) {
      for (;;) {
        await check();
        if (collectorFailure) reject(collectorFailure);
        let activity;
        try { activity = await connection.receiveTurnActivity(threadId, turnId, Math.min(deadline, performance.now() + 250)); }
        catch (error) { if (error.message === 'turn activity deadline exceeded' && performance.now() < deadline && !exited) continue; throw error; }
        await check();
        if (activity.type === 'request') {
          // This bounded route never grants extra permissions or impersonates
          // a human answer. Preserve the failed request and close its owned host.
          reject('TARGET_OWNER_REQUEST_UNSUPPORTED');
        }
        if (activity.type === 'terminal') return {terminal: activity.terminal,
          output: messages.filter(x => x.threadId === threadId && x.turnId === turnId).map(x => x.text).join('\n'),
          events: events.filter(x => x.threadId === threadId && x.turnId === turnId)};
      }
    }, close});
}

module.exports = {createExternalHandoff, createOwnedNativeRunner};
