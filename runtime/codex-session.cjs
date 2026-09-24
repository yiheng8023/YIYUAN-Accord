'use strict';

// Source-side Codex SDK session. The caller owns an already initialized native
// connection, its authentication, the durable recorder, and all policy choices.
// This adapter never starts/discovers/closes a host, initializes a connection,
// retries an ambiguous native effect, or archives/deletes a thread. Only the
// explicit, validated adoptTarget path settles its current transfer. One session
// creates or explicitly restores one source thread, serializes ordinary turns,
// and may perform at most one verified fresh handoff per adopted carrier.

const {performance} = require('node:perf_hooks');
const {
  HANDOFF_PROPOSAL_TOOL,
  runHandoffProposal,
} = require('./carrier-handoff.cjs');
const {CONTEXT_OBSERVATION_TOOL} = require('./codex-connection.cjs');

const MAX_TIMER_MS = 0x7fffffff;
const MAX_REF = 4096;
const RESERVED_TOOLS = new Set([
  HANDOFF_PROPOSAL_TOOL.name,
  CONTEXT_OBSERVATION_TOOL.name,
]);
const RESTORE_SESSION = Symbol('accord.restoreCodexSourceSession');

class CodexSourceSessionError extends Error {
  constructor(code, message, options = {}) {
    super(message, options.cause ? {cause: options.cause} : undefined);
    this.name = 'CodexSourceSessionError';
    this.code = code;
    this.phase = options.phase || 'unknown';
    this.state = immutable(options.state || {});
    if (options.rpcRequest) this.rpcRequest = immutable(options.rpcRequest);
    if (options.nativeRequest) this.nativeRequest = immutable(options.nativeRequest);
  }
}

function plainObject(value) {
  if (!value || typeof value !== 'object' || Array.isArray(value)) return false;
  const prototype = Object.getPrototypeOf(value);
  return prototype === Object.prototype || prototype === null;
}

function text(value, name, limit = MAX_REF) {
  if (typeof value !== 'string' || !value.trim() || value.length > limit) {
    throw new TypeError(`${name} must be a nonempty bounded string`);
  }
  return value;
}

function cloneData(value, seen = new Set()) {
  if (value === null || typeof value === 'string' || typeof value === 'boolean') return value;
  if (typeof value === 'number') {
    if (!Number.isFinite(value)) throw new TypeError('non-finite data');
    return value;
  }
  if (typeof value !== 'object') throw new TypeError('non-data value');
  if (seen.has(value)) throw new TypeError('cyclic data');
  seen.add(value);
  let result;
  if (Array.isArray(value)) result = value.map(item => cloneData(item, seen));
  else {
    if (!plainObject(value)) throw new TypeError('non-plain data object');
    result = {};
    for (const [key, item] of Object.entries(value)) {
      if (item === undefined) throw new TypeError(`undefined data field: ${key}`);
      Object.defineProperty(result, key, {
        value: cloneData(item, seen), enumerable: true, writable: true, configurable: true,
      });
    }
  }
  seen.delete(value);
  return result;
}

function freezeDeep(value) {
  if (value && typeof value === 'object' && !Object.isFrozen(value)) {
    for (const item of Object.values(value)) freezeDeep(item);
    Object.freeze(value);
  }
  return value;
}

function immutable(value) {
  return freezeDeep(cloneData(value));
}

function canonical(value) {
  if (Array.isArray(value)) return `[${value.map(canonical).join(',')}]`;
  if (value && typeof value === 'object') {
    return `{${Object.keys(value).sort().map(key =>
      `${JSON.stringify(key)}:${canonical(value[key])}`).join(',')}}`;
  }
  return JSON.stringify(value);
}

function continuityTools(rawTools, name) {
  if (rawTools !== undefined && !Array.isArray(rawTools)) throw new TypeError(`${name} must be an array`);
  const tools = cloneData(rawTools || []);
  for (const tool of tools) {
    if (!plainObject(tool)) throw new TypeError(`${name} entries must be objects`);
    if (tool.namespace == null && RESERVED_TOOLS.has(tool.name)) {
      throw new TypeError(`dynamic tool identity conflict: ${tool.name}`);
    }
  }
  return cloneData([...tools, HANDOFF_PROPOSAL_TOOL, CONTEXT_OBSERVATION_TOOL]);
}

function hasContinuityTools(tools) {
  return Array.isArray(tools) && [HANDOFF_PROPOSAL_TOOL, CONTEXT_OBSERVATION_TOOL].every(expected =>
    tools.some(actual => actual?.namespace == null && canonical(actual) === canonical(expected)));
}

function callbackDeadline(deadline, label) {
  const remaining = deadline - performance.now();
  if (!Number.isFinite(deadline) || remaining <= 0 || remaining > MAX_TIMER_MS) {
    throw new Error(`${label} deadline is invalid or exceeded`);
  }
  return remaining;
}

async function boundedCallback(callback, args, deadline, label) {
  const remaining = callbackDeadline(deadline, label);
  const controller = new AbortController();
  const context = args[args.length - 1];
  if (plainObject(context)) context.signal = controller.signal;
  let timer;
  const timeout = new Promise((_, reject) => {
    timer = setTimeout(() => {
      controller.abort();
      reject(new Error(`${label} callback deadline exceeded`));
    }, remaining);
  });
  try {
    return await Promise.race([
      Promise.resolve().then(() => Reflect.apply(callback, undefined, args)),
      timeout,
    ]);
  } finally {
    clearTimeout(timer);
  }
}

async function boundedOperation(callback, args, deadline, label) {
  const remaining = callbackDeadline(deadline, label);
  let timer;
  const timeout = new Promise((_, reject) => {
    timer = setTimeout(() => reject(new Error(`${label} deadline exceeded`)), remaining);
  });
  try {
    return await Promise.race([
      Promise.resolve().then(() => Reflect.apply(callback, undefined, args)),
      timeout,
    ]);
  } finally {
    clearTimeout(timer);
  }
}

function toRunBudget(deadlineMs) {
  const wall = Date.now();
  const monotonic = performance.now();
  if (!Number.isSafeInteger(deadlineMs) || deadlineMs <= wall || deadlineMs - wall > MAX_TIMER_MS) {
    throw new TypeError('run.deadlineMs must be a future absolute millisecond deadline');
  }
  return Object.freeze({wallDeadlineMs: deadlineMs, monotonicDeadline: monotonic + deadlineMs - wall});
}

function terminalStatus(terminal) {
  return terminal?.method === 'turn/completed' ? terminal.params?.turn?.status : null;
}

function requestBody(value) {
  if (!plainObject(value) || Object.keys(value).length !== 1 ||
      !(Object.hasOwn(value, 'result') !== Object.hasOwn(value, 'error')) ||
      Object.values(value)[0] === undefined) {
    throw new TypeError('ownerRequest must return exactly {result} or {error}');
  }
  return immutable(value);
}

function validatePlanForRun(rawPlan, sourceThreadId, turnId, scopeRef, wallDeadlineMs) {
  const candidate = cloneData(rawPlan);
  if (!plainObject(candidate) || !plainObject(candidate.source) || !plainObject(candidate.target)) {
    throw new TypeError('planResolver must return a handoff plan');
  }
  candidate.target.dynamicTools = continuityTools(candidate.target.dynamicTools,
    'plan.target.dynamicTools');
  const plan = immutable(candidate);
  if (plan.source.threadId !== sourceThreadId || plan.source.turnId !== turnId || plan.scopeRef !== scopeRef) {
    throw new TypeError('handoff plan source or scope differs from the active source turn');
  }
  for (const name of ['deadlineMs', 'recoveryDeadlineMs']) {
    if (!Number.isSafeInteger(plan[name]) || plan[name] > wallDeadlineMs) {
      throw new TypeError(`handoff plan ${name} exceeds the run deadline`);
    }
  }
  return plan;
}

function validateRestoreInput(raw, scopeRef) {
  const sourceRestore = plainObject(raw) && Object.hasOwn(raw, 'source');
  if (!plainObject(raw) || Object.keys(raw).sort().join('|') !==
      ['deadlineMs', 'expectedScope', 'resume', sourceRestore ? 'source' : 'transferId'].sort().join('|')) {
    throw new TypeError('restore requires one source or transferId, expectedScope, deadlineMs and resume');
  }
  if (sourceRestore) {
    if (!plainObject(raw.source) || Object.keys(raw.source).sort().join('|') !==
        ['authorityRef', 'connectionId', 'stateRef', 'threadId'].sort().join('|')) {
      throw new TypeError('restore.source must identify the retained source, connection and current references');
    }
    for (const name of ['threadId', 'connectionId', 'authorityRef', 'stateRef']) {
      text(raw.source[name], `restore.source.${name}`);
    }
  } else text(raw.transferId, 'restore.transferId');
  const expected = raw.expectedScope;
  if (!plainObject(expected) || Object.keys(expected).sort().join('|') !==
      ['activeTransferId', 'scopeRef', 'token', 'writerThreadId'].sort().join('|') ||
      expected.scopeRef !== scopeRef || expected.activeTransferId !== null) {
    throw new TypeError('restore.expectedScope must be an exact inactive scope receipt');
  }
  text(expected.writerThreadId, 'restore.expectedScope.writerThreadId');
  text(expected.token, 'restore.expectedScope.token');
  const resume = cloneData(raw.resume);
  const allowed = new Set(['cwd', 'sandbox', 'approvalPolicy', 'model', 'modelProvider', 'effort']);
  if (!plainObject(resume) || Object.keys(resume).some(key => !allowed.has(key))) {
    throw new TypeError('restore.resume contains unsupported fields');
  }
  for (const name of ['cwd', 'sandbox', 'approvalPolicy']) text(resume[name], `restore.resume.${name}`, name === 'cwd' ? 32768 : MAX_REF);
  for (const name of ['model', 'modelProvider', 'effort']) {
    if (Object.hasOwn(resume, name)) text(resume[name], `restore.resume.${name}`);
  }
  const params = {cwd: resume.cwd, sandbox: resume.sandbox,
    approvalPolicy: resume.approvalPolicy,
    ...(resume.model ? {model: resume.model} : {}),
    ...(resume.modelProvider ? {modelProvider: resume.modelProvider} : {}),
    ...(resume.effort ? {config: {model_reasoning_effort: resume.effort}} : {})};
  return immutable({transferId: sourceRestore ? null : raw.transferId,
    source: sourceRestore ? raw.source : null, expectedScope: expected,
    deadlineMs: raw.deadlineMs, resume, params});
}

function createSession(options, restoreMode = false) {
  if (!plainObject(options)) throw new TypeError('options must be an object');
  const allowed = new Set(['connection', 'recorder', 'scopeRef', 'threadStart', 'planResolver',
    'verify', 'current', 'ownerRequest', 'ownUnscopedRequests']);
  for (const key of Object.keys(options)) if (!allowed.has(key)) throw new TypeError(`unsupported option: ${key}`);
  const {connection, recorder} = options;
  const scopeRef = text(options.scopeRef, 'scopeRef');
  if (!plainObject(connection) || !plainObject(connection.transport) ||
      typeof connection.transport.request !== 'function' ||
      typeof connection.transport.waitTerminal !== 'function' ||
      typeof connection.receiveTurnActivity !== 'function' ||
      typeof connection.respondRequest !== 'function' ||
      typeof connection.replyContext !== 'function' ||
      typeof connection.proposalChannel !== 'function') {
    throw new TypeError('an initialized owner connection with source-session APIs is required');
  }
  text(connection.transport.connectionId, 'connection.transport.connectionId');
  text(connection.transport.hostVersion, 'connection.transport.hostVersion');
  if (!plainObject(recorder) || typeof recorder.readScope !== 'function' ||
      typeof recorder.bindScope !== 'function' || typeof recorder.begin !== 'function' ||
      typeof recorder.compareAndSet !== 'function' || typeof recorder.read !== 'function' ||
      typeof recorder.settle !== 'function' ||
      restoreMode && typeof recorder.claimScope !== 'function') {
    throw new TypeError('a borrowed durable carrier recorder is required');
  }
  for (const name of ['planResolver', 'verify', 'current', 'ownerRequest']) {
    if (typeof options[name] !== 'function') throw new TypeError(`${name} callback is required`);
  }
  if (Object.hasOwn(options, 'ownUnscopedRequests') && typeof options.ownUnscopedRequests !== 'boolean') {
    throw new TypeError('ownUnscopedRequests must be a boolean');
  }
  if (restoreMode && Object.hasOwn(options, 'threadStart')) throw new TypeError('restore options cannot include threadStart');
  if (!restoreMode && !plainObject(options.threadStart)) throw new TypeError('threadStart must be explicit native parameters');
  const sourceStart = restoreMode ? null : cloneData(options.threadStart);
  if (sourceStart) {
    text(sourceStart.cwd, 'threadStart.cwd', 32768);
    text(sourceStart.model, 'threadStart.model');
    if (Object.hasOwn(sourceStart, 'ephemeral') && sourceStart.ephemeral !== false) {
      throw new TypeError('threadStart.ephemeral must be false for a recoverable source');
    }
    sourceStart.ephemeral = false;
    if (Object.hasOwn(sourceStart, 'threadId')) throw new TypeError('threadStart cannot select an existing thread');
    sourceStart.dynamicTools = continuityTools(sourceStart.dynamicTools,
      'threadStart.dynamicTools');
  }
  const bound = Object.freeze({
    request: connection.transport.request,
    waitTerminal: connection.transport.waitTerminal,
    connectionId: connection.transport.connectionId,
    hostVersion: connection.transport.hostVersion,
    receive: connection.receiveTurnActivity,
    respond: connection.respondRequest,
    replyContext: connection.replyContext,
    proposalChannel: connection.proposalChannel,
    readScope: recorder.readScope,
    bindScope: recorder.bindScope,
    begin: recorder.begin,
    compareAndSet: recorder.compareAndSet,
    readRecord: recorder.read,
    settle: recorder.settle,
    claimScope: recorder.claimScope,
    planResolver: options.planResolver,
    verify: options.verify,
    current: options.current,
    ownerRequest: options.ownerRequest,
  });
  const handoffTransport = Object.freeze({connectionId: bound.connectionId,
    hostVersion: bound.hostVersion, request: bound.request, waitTerminal: pumpHandoffTerminal});
  const handoffRecorder = Object.freeze({begin: bound.begin, compareAndSet: bound.compareAndSet});
  const ownUnscopedRequests = options.ownUnscopedRequests === true;
  let busy = false;
  let state = {
    status: restoreMode ? 'restore-required' : 'new',
    phase: restoreMode ? 'restore-required' : 'new',
    scopeRef, sourceThreadId: null, lastTurnId: null,
    turnCount: 0, transferCount: 0, transfers: [], lastSafeReceipt: null, pendingRequest: null,
  };

  const snapshot = () => immutable(state);
  function ensureBindings() {
    if (connection.transport.request !== bound.request ||
        connection.transport.waitTerminal !== bound.waitTerminal ||
        connection.transport.connectionId !== bound.connectionId ||
        connection.transport.hostVersion !== bound.hostVersion ||
        connection.receiveTurnActivity !== bound.receive || connection.respondRequest !== bound.respond ||
        connection.replyContext !== bound.replyContext || connection.proposalChannel !== bound.proposalChannel ||
        recorder.readScope !== bound.readScope || recorder.bindScope !== bound.bindScope ||
        recorder.begin !== bound.begin || recorder.compareAndSet !== bound.compareAndSet ||
        recorder.read !== bound.readRecord || recorder.settle !== bound.settle ||
        restoreMode && recorder.claimScope !== bound.claimScope ||
        options.planResolver !== bound.planResolver ||
        options.verify !== bound.verify || options.current !== bound.current ||
        options.ownerRequest !== bound.ownerRequest) {
      throw new Error('source session owner binding changed');
    }
  }
  function lockFailure(code, message, cause, extra = {}) {
    let causeView = null;
    if (cause) {
      causeView = {name: typeof cause.name === 'string' ? cause.name : 'Error',
        message: typeof cause.message === 'string' ? cause.message : String(cause)};
      if (typeof cause.code === 'string' || typeof cause.code === 'number') causeView.code = cause.code;
      if (typeof cause.stage === 'string') causeView.stage = cause.stage;
      for (const key of ['rpcRequest', 'state']) {
        if (!plainObject(cause[key])) continue;
        try { causeView[key] = cloneData(cause[key]); } catch (_) {}
      }
    }
    state = {...state, status: 'failed', phase: extra.phase || state.phase,
      pendingRequest: extra.nativeRequest ? immutable(extra.nativeRequest) : state.pendingRequest,
      failure: {code, message, cause: causeView}, ...extra.state};
    throw new CodexSourceSessionError(code, message, {
      cause, phase: state.phase, state: snapshot(), rpcRequest: causeView?.rpcRequest,
      nativeRequest: extra.nativeRequest,
    });
  }
  async function callOwner(callback, args, deadline, label) {
    ensureBindings();
    const value = await boundedCallback(callback, args, deadline, label);
    ensureBindings();
    callbackDeadline(deadline, label);
    return value;
  }

  async function pumpHandoffTerminal(threadId, turnId, deadline) {
    for (;;) {
      ensureBindings();
      const activity = await Reflect.apply(bound.receive, undefined,
        [threadId, turnId, deadline, {includeUnscoped: ownUnscopedRequests}]);
      ensureBindings();
      if (activity?.type === 'terminal') return immutable(activity.terminal);
      if (activity?.type !== 'request' || !plainObject(activity.request)) {
        throw new Error('connection returned invalid handoff target activity');
      }
      const nativeRequest = immutable(activity.request);
      state = {...state, pendingRequest: nativeRequest};
      if (nativeRequest.method === 'item/tool/call' &&
          nativeRequest.params?.tool === CONTEXT_OBSERVATION_TOOL.name &&
          nativeRequest.params?.namespace == null) {
        await Reflect.apply(bound.replyContext, undefined, [nativeRequest, deadline]);
      } else if (nativeRequest.method === 'item/tool/call' &&
          nativeRequest.params?.tool === HANDOFF_PROPOSAL_TOOL.name &&
          nativeRequest.params?.namespace == null) {
        const payload = immutable({schema: 'yiyuan-accord-nested-handoff-reply/v1',
          code: 'TRANSFER_IN_PROGRESS', accepted: false,
          message: 'The current transfer must be adopted and settled before this target can request another handoff.'});
        await Reflect.apply(bound.respond, undefined, [nativeRequest, {result: {success: false,
          contentItems: [{type: 'inputText', text: JSON.stringify(payload)}]}}, deadline]);
      } else {
        const ownerContext = {threadId, turnId, scopeRef, deadline, phase: 'handoff-target'};
        const body = requestBody(await callOwner(bound.ownerRequest,
          [nativeRequest, ownerContext], deadline, 'ownerRequest'));
        await Reflect.apply(bound.respond, undefined, [nativeRequest, body, deadline]);
      }
      state = {...state, pendingRequest: null};
    }
  }

  async function ensureSource(deadline) {
    if (state.sourceThreadId) return state.sourceThreadId;
    if (!sourceStart) return lockFailure('RESTORED_SOURCE_MISSING',
      'restored session cannot create a replacement source', null, {phase: 'restored-source-missing'});
    state = {...state, status: 'starting', phase: 'scope-check'};
    try {
      let prior, missing = false;
      try {
        prior = await boundedOperation(bound.readScope, [scopeRef], deadline, 'recorder.readScope');
      } catch (error) {
        if (error?.code !== 'SCOPE_NOT_FOUND') throw error;
        missing = true;
      }
      ensureBindings();
      if (!missing && prior === undefined) throw new Error('recorder.readScope returned no scope state');
      if (prior) throw Object.assign(new Error('scope is already bound to another writer'), {code: 'WRITER_CONFLICT'});
      callbackDeadline(deadline, 'source start');
      state = {...state, phase: 'source-start-pending'};
      let receipt;
      try {
        receipt = await Reflect.apply(bound.request, undefined,
          ['thread/start', immutable(sourceStart), deadline]);
      } catch (error) {
        return lockFailure('SOURCE_START_UNKNOWN', 'source thread start did not return a usable acknowledgement', error,
          {phase: 'source-start-unknown'});
      }
      state = {...state, lastSafeReceipt: immutable(receipt)};
      const sourceThreadId = receipt?.thread?.id;
      try { text(sourceThreadId, 'source start thread id'); }
      catch (error) {
        return lockFailure('SOURCE_START_UNKNOWN', 'source thread start acknowledgement is malformed', error,
          {phase: 'source-start-unknown', state: {lastSafeReceipt: immutable(receipt)}});
      }
      // Retain the created identity for owner reconciliation even when the host
      // has not confirmed that the source can survive this connection.
      state = {...state, sourceThreadId, phase: 'source-persistence-check'};
      if (receipt.thread.ephemeral !== false) {
        return lockFailure('SOURCE_PERSISTENCE_UNVERIFIED',
          'source acknowledgement did not confirm a persistent thread', null,
          {phase: 'source-persistence-unverified'});
      }
      state = {...state, phase: 'scope-bind-pending'};
      try {
        const binding = await boundedOperation(bound.bindScope, [scopeRef, sourceThreadId],
          deadline, 'recorder.bindScope');
        ensureBindings();
        if (!binding || binding.scope?.writerThreadId !== sourceThreadId || binding.scope?.scopeRef !== scopeRef) {
          throw new Error('scope bind did not return the source writer');
        }
        state = {...state, status: 'ready', phase: 'ready', scope: immutable(binding.scope)};
        return sourceThreadId;
      } catch (error) {
        let observedScope = null;
        try {
          observedScope = await boundedOperation(bound.readScope, [scopeRef], deadline,
            'recorder.readScope after bind failure');
        } catch (_) {}
        return lockFailure('SOURCE_BIND_FAILED', 'source exists but durable scope binding failed', error,
          {phase: 'source-created-unbound', state: {sourceThreadId,
            lastSafeReceipt: immutable(receipt), observedScope}});
      }
    } catch (error) {
      if (error instanceof CodexSourceSessionError) throw error;
      return lockFailure(error?.code || 'SOURCE_SETUP_FAILED', 'source session setup failed', error,
        {phase: state.phase});
    }
  }

  // The recorder coordinates cooperating controllers; it is not an OS lock.
  // The connection owner must not issue source writes outside this serialized
  // session between this check and turn/start.
  async function requireWritableScope(sourceThreadId, deadline, phase) {
    let observed;
    try {
      observed = await boundedOperation(bound.readScope, [scopeRef], deadline, 'recorder.readScope');
      ensureBindings();
    } catch (error) {
      return lockFailure('SOURCE_SCOPE_UNKNOWN', 'source scope could not be verified', error,
        {phase});
    }
    if (!observed || observed.scopeRef !== scopeRef ||
        observed.writerThreadId !== sourceThreadId || observed.activeTransferId !== null ||
        typeof state.scope?.token !== 'string' || observed.token !== state.scope.token) {
      return lockFailure('SOURCE_SCOPE_CHANGED', 'source scope no longer grants an idle single writer', null,
        {phase, state: {observedScope: immutable(observed || {})}});
    }
    state = {...state, scope: immutable(observed)};
    return observed;
  }

  async function run(raw) {
    if (busy) throw new CodexSourceSessionError('RUN_IN_PROGRESS', 'source session already has an active run', {phase: state.phase, state: snapshot()});
    if (state.status === 'restore-required') throw new CodexSourceSessionError(
      'RESTORE_REQUIRED', 'restore executor cannot run before successful restoration',
      {phase: state.phase, state: snapshot()});
    if (state.status === 'failed') throw new CodexSourceSessionError('SESSION_FAILED', 'failed source session requires owner reconciliation', {phase: state.phase, state: snapshot(), rpcRequest: state.failure?.cause?.rpcRequest});
    if (state.status === 'transferred') throw new CodexSourceSessionError('SOURCE_TRANSFERRED', 'source ownership has transferred; this session cannot write again', {phase: state.phase, state: snapshot()});
    if (!plainObject(raw)) throw new TypeError('run must be an object');
    for (const key of Object.keys(raw)) if (!['input', 'deadlineMs', 'turn'].includes(key)) throw new TypeError(`unsupported run option: ${key}`);
    const budget = toRunBudget(raw.deadlineMs);
    const input = typeof raw.input === 'string' ? [{type: 'text', text: text(raw.input, 'run.input', 1024 * 1024)}] : immutable(raw.input);
    if (!Array.isArray(input) || input.length === 0) throw new TypeError('run.input must be a nonempty string or native input array');
    if (Object.hasOwn(raw, 'turn') && !plainObject(raw.turn)) throw new TypeError('run.turn must be native turn parameters');
    const turnOptions = cloneData(raw.turn || {});
    if (Object.hasOwn(turnOptions, 'threadId') || Object.hasOwn(turnOptions, 'input')) throw new TypeError('run.turn cannot override threadId or input');
    busy = true;
    try {
      ensureBindings();
      const sourceThreadId = await ensureSource(budget.monotonicDeadline);
      await requireWritableScope(sourceThreadId, budget.monotonicDeadline, 'source-scope-before-turn');
      state = {...state, status: 'running', phase: 'turn-start-pending', pendingRequest: null};
      let start;
      try {
        start = await Reflect.apply(bound.request, undefined, ['turn/start', immutable({
          ...turnOptions, threadId: sourceThreadId, input,
        }), budget.monotonicDeadline]);
      } catch (error) {
        return lockFailure('TURN_START_UNKNOWN', 'source turn start did not return a usable acknowledgement', error,
          {phase: 'turn-start-unknown'});
      }
      state = {...state, lastSafeReceipt: immutable(start)};
      const turnId = start?.turn?.id;
      try { text(turnId, 'turn start turn id'); }
      catch (error) {
        return lockFailure('TURN_START_UNKNOWN', 'source turn start acknowledgement is malformed', error,
          {phase: 'turn-start-unknown', state: {lastSafeReceipt: immutable(start)}});
      }
      state = {...state, phase: 'turn-running', lastTurnId: turnId,
        lastSafeReceipt: immutable(start), turnCount: state.turnCount + 1};
      for (;;) {
        let activity;
        try {
          activity = await Reflect.apply(bound.receive, undefined,
            [sourceThreadId, turnId, budget.monotonicDeadline, {includeUnscoped: ownUnscopedRequests}]);
        } catch (error) {
          return lockFailure('TURN_ACTIVITY_FAILED', 'source turn activity became unavailable', error,
            {phase: 'turn-activity-unknown'});
        }
        if (activity?.type === 'terminal') {
          const terminal = immutable(activity.terminal);
          const status = terminalStatus(terminal);
          if (status !== 'completed') {
            return lockFailure('TURN_NOT_COMPLETED', `source turn ended with ${status || 'an unknown status'}`, null,
              {phase: 'turn-terminal-failed', state: {lastSafeReceipt: terminal}});
          }
          state = {...state, lastSafeReceipt: terminal};
          await requireWritableScope(sourceThreadId, budget.monotonicDeadline,
            'source-scope-after-terminal');
          state = {...state, status: 'ready', phase: 'ready', lastSafeReceipt: terminal, pendingRequest: null};
          return immutable({status: 'completed', scopeRef, sourceThreadId, turnId, terminal,
            sourceWritable: true, claimLimit: 'This ordinary source turn completed under the borrowed owner connection and cooperative recorder scope. The owner must keep source writes serialized; no OS lock, handoff or broader acceptance is implied.'});
        }
        if (activity?.type !== 'request' || !plainObject(activity.request)) {
          return lockFailure('INVALID_TURN_ACTIVITY', 'connection returned invalid source turn activity', null,
            {phase: 'turn-activity-invalid'});
        }
        const nativeRequest = immutable(activity.request);
        state = {...state, phase: 'server-request', pendingRequest: nativeRequest};
        try {
          if (nativeRequest.method === 'item/tool/call' &&
              nativeRequest.params?.tool === CONTEXT_OBSERVATION_TOOL.name &&
              nativeRequest.params?.namespace == null) {
            await Reflect.apply(bound.replyContext, undefined, [nativeRequest, budget.monotonicDeadline]);
            state = {...state, phase: 'turn-running', pendingRequest: null};
            continue;
          }
          if (nativeRequest.method === 'item/tool/call' &&
              nativeRequest.params?.tool === HANDOFF_PROPOSAL_TOOL.name &&
              nativeRequest.params?.namespace == null) {
            if (state.transferCount !== 0) throw new Error('source session handoff proposal is already used');
            const resolverContext = {threadId: sourceThreadId, turnId, scopeRef,
              deadlineMs: budget.wallDeadlineMs};
            const rawPlan = await callOwner(bound.planResolver,
              [nativeRequest, resolverContext], budget.monotonicDeadline, 'planResolver');
            const plan = validatePlanForRun(rawPlan, sourceThreadId, turnId, scopeRef,
              budget.wallDeadlineMs);
            const current = deadline => callOwner(bound.current, [{nativeRequest, sourceThreadId,
              turnId, scopeRef, deadline}], Math.min(deadline, budget.monotonicDeadline), 'current');
            const channel = Reflect.apply(bound.proposalChannel, undefined, [nativeRequest, current]);
            state = {...state, phase: 'handoff-running', transferCount: 1};
            const handoff = await runHandoffProposal(plan, {
              transport: handoffTransport, recorder: handoffRecorder, verify: bound.verify,
            }, nativeRequest, channel);
            let record;
            try {
              record = await boundedOperation(bound.readRecord, [handoff.transferId, scopeRef],
                budget.monotonicDeadline, 'recorder.read');
              ensureBindings();
            } catch (error) {
              return lockFailure('TRANSFER_RECORD_UNAVAILABLE', 'handoff completed but its recovery record is unavailable', error,
                {phase: 'transferred-record-unavailable', state: {handoff: immutable(handoff)}});
            }
            const targetContinuityToolsRegistered = hasContinuityTools(
              record?.state?.plan?.target?.dynamicTools);
            const transferSummary = immutable({transferId: handoff.transferId,
              sourceThreadId, targetThreadId: handoff.target.threadId,
              revision: record.revision, settled: false});
            state = {...state, status: 'transferred', phase: 'transferred', pendingRequest: null,
              targetThreadId: handoff.target.threadId, handoff: immutable(handoff),
              record: immutable(record), targetContinuityToolsRegistered,
              transfers: [...state.transfers, transferSummary]};
            return immutable({status: 'transferred', scopeRef, sourceThreadId, turnId,
              target: {threadId: handoff.target.threadId, ownedWriter: true,
                automaticHandoffToolRegistered: targetContinuityToolsRegistered}, handoff, record,
              sourceWritable: false,
              claimLimit: 'Verified caller-owned fresh transfer only. The source session is closed to writes; target adoption and another handoff require a separate durable settle and a new run.'});
          }
          const ownerContext = {threadId: sourceThreadId, turnId, scopeRef,
            deadline: budget.monotonicDeadline};
          const body = requestBody(await callOwner(bound.ownerRequest,
            [nativeRequest, ownerContext], budget.monotonicDeadline, 'ownerRequest'));
          await Reflect.apply(bound.respond, undefined,
            [nativeRequest, body, budget.monotonicDeadline]);
          state = {...state, phase: 'turn-running', pendingRequest: null};
        } catch (error) {
          if (error instanceof CodexSourceSessionError) throw error;
          return lockFailure('SERVER_REQUEST_FAILED', 'source server request was not safely completed', error,
            {phase: state.phase, nativeRequest});
        }
      }
    } catch (error) {
      if (error instanceof CodexSourceSessionError) throw error;
      return lockFailure('SESSION_RUN_FAILED', 'source session run failed and requires owner reconciliation',
        error, {phase: state.phase});
    } finally {
      busy = false;
    }
  }

  async function adoptTarget(raw) {
    if (busy) throw new CodexSourceSessionError('RUN_IN_PROGRESS', 'source session already has an active run or adoption', {phase: state.phase, state: snapshot()});
    if (state.status === 'failed') throw new CodexSourceSessionError('SESSION_FAILED', 'failed source session requires owner reconciliation', {phase: state.phase, state: snapshot(), rpcRequest: state.failure?.cause?.rpcRequest});
    if (state.status !== 'transferred') throw new CodexSourceSessionError('TARGET_ADOPTION_UNAVAILABLE', 'only this session\'s current transferred target can be adopted', {phase: state.phase, state: snapshot()});
    if (!plainObject(raw) || Object.keys(raw).some(key => key !== 'deadlineMs')) {
      throw new TypeError('adoptTarget requires only deadlineMs');
    }
    const budget = toRunBudget(raw.deadlineMs);
    const retained = state;
    let settleInvoked = false;
    busy = true;
    state = {...state, phase: 'adopt-target-check'};
    try {
      ensureBindings();
      const handoff = retained.handoff, previous = retained.record;
      const transferId = handoff?.transferId, targetThreadId = handoff?.target?.threadId;
      text(transferId, 'retained transfer id');
      text(targetThreadId, 'retained target thread id');
      const record = immutable(await boundedOperation(bound.readRecord,
        [transferId, scopeRef], budget.monotonicDeadline, 'recorder.read'));
      ensureBindings();
      const ledger = record.state, plan = ledger?.plan;
      if (!plainObject(record) || !Number.isSafeInteger(record.revision) || !plainObject(record.lease) ||
          !plainObject(ledger) || !plainObject(plan) || record.revision !== previous?.revision ||
          canonical(record.lease) !== canonical(previous?.lease) || ledger.phase !== 'source-subscription-released' ||
          ledger.pendingEffect !== null || ledger.transferId !== transferId || ledger.scopeRef !== scopeRef ||
          ledger.writer !== 'target' || ledger.writerThreadId !== targetThreadId ||
          ledger.target?.threadId !== targetThreadId || record.lease.scopeRef !== scopeRef ||
          record.lease.transferId !== transferId || record.lease.writerThreadId !== targetThreadId ||
          plan.scopeRef !== scopeRef || plan.authorityRef !== ledger.authorityRef ||
          plan.stateRef !== ledger.stateRef || ledger.connection?.connectionId !== bound.connectionId ||
          ledger.connection?.hostVersion !== bound.hostVersion) {
        throw Object.assign(new Error('durable transfer record or lease is stale'), {code: 'TARGET_RECORD_STALE'});
      }
      if (!hasContinuityTools(plan.target?.dynamicTools)) {
        throw Object.assign(new Error('target continuity tools are absent from the durable plan'),
          {code: 'TARGET_CONTINUITY_TOOLS_UNAVAILABLE'});
      }
      const targetRead = immutable(await Reflect.apply(bound.request, undefined,
        ['thread/read', {threadId: targetThreadId}, budget.monotonicDeadline]));
      ensureBindings();
      if (targetRead?.thread?.id !== targetThreadId || targetRead.thread?.status?.type !== 'idle' ||
          targetRead.thread?.ephemeral !== false) {
        throw Object.assign(new Error('target is not the exact idle persistent writer'),
          {code: 'TARGET_NOT_ADOPTABLE'});
      }
      const facts = immutable({connectionId: bound.connectionId, hostVersion: bound.hostVersion,
        scopeRef, authorityRef: ledger.authorityRef, stateRef: ledger.stateRef,
        transferId, target: {threadId: targetThreadId}, record, targetRead});
      const verdict = immutable(await boundedOperation(bound.verify,
        ['adopt-target', facts, budget.monotonicDeadline], budget.monotonicDeadline,
        'verify:adopt-target'));
      ensureBindings();
      if (verdict?.decision !== 'allow' || verdict.scopeRef !== scopeRef ||
          verdict.authorityRef !== ledger.authorityRef || verdict.stateRef !== ledger.stateRef ||
          typeof verdict.sourceRef !== 'string' || !verdict.sourceRef.trim() ||
          verdict.adoptionAuthorized !== true || verdict.singleWriter !== true ||
          verdict.effectsVerified !== true) {
        throw Object.assign(new Error('adopt-target verifier did not authorize the current target'),
          {code: 'TARGET_ADOPTION_DENIED'});
      }
      state = {...state, phase: 'adopt-target-settle-pending', adoption: {
        transferId, targetThreadId, recordRevision: record.revision,
        verificationSourceRef: verdict.sourceRef, targetRead, verdict}};
      const settled = immutable(await boundedOperation(() => {
        settleInvoked = true;
        return Reflect.apply(bound.settle, undefined,
          [transferId, record.revision, record.lease]);
      }, [], budget.monotonicDeadline, 'recorder.settle'));
      state = {...state, adoption: {...state.adoption, settleReceipt: settled}};
      ensureBindings();
      if (!Number.isSafeInteger(settled?.revision) || settled.revision <= record.revision ||
          settled.scope?.scopeRef !== scopeRef || settled.scope?.writerThreadId !== targetThreadId ||
          settled.scope?.activeTransferId !== null || typeof settled.scope?.token !== 'string' ||
          !settled.scope.token.trim() || settled.scope.token === record.lease.token) {
        throw Object.assign(new Error('settle acknowledgement is malformed'),
          {code: 'TARGET_SETTLE_UNKNOWN'});
      }
      const currentScope = immutable(await boundedOperation(bound.readScope, [scopeRef],
        budget.monotonicDeadline, 'recorder.readScope after settle'));
      ensureBindings();
      if (canonical(currentScope) !== canonical(settled.scope)) {
        throw Object.assign(new Error('settled scope readback differs'),
          {code: 'TARGET_SETTLE_UNKNOWN'});
      }
      const transfers = retained.transfers.map(item => item.transferId === transferId ? immutable({
        ...item, settled: true, settleRevision: settled.revision,
        verificationSourceRef: verdict.sourceRef,
      }) : item);
      const {handoff: ignoredHandoff, record: ignoredRecord, targetThreadId: ignoredTarget,
        targetContinuityToolsRegistered: ignoredTools, adoption: ignoredAdoption,
        lastAdoptionFailure: ignoredFailure, ...rest} = state;
      state = {...rest, status: 'ready', phase: 'ready', sourceThreadId: targetThreadId,
        lastTurnId: null, transferCount: 0, pendingRequest: null, scope: currentScope,
        lastSafeReceipt: settled, transfers, adoptedFromTransferId: transferId};
      return immutable({status: 'adopted', scopeRef, sourceThreadId: targetThreadId,
        transferId, settle: settled, scope: currentScope,
        claimLimit: 'Same-controller hot adoption after durable settle only; no cold recovery, archive, deletion or cross-controller takeover is implied.'});
    } catch (error) {
      if (settleInvoked) {
        if (error instanceof CodexSourceSessionError) throw error;
        return lockFailure(error?.code || 'TARGET_SETTLE_UNKNOWN',
          'target settlement outcome is unknown and must not be replayed', error,
          {phase: 'adopt-target-settle-unknown'});
      }
      const code = typeof error?.code === 'string' ? error.code : 'TARGET_ADOPTION_FAILED';
      state = {...retained, status: 'transferred', phase: 'transferred',
        lastAdoptionFailure: {code, message: error?.message || String(error)}};
      throw new CodexSourceSessionError(code, error?.message || 'target adoption failed', {
        cause: error, phase: state.phase, state: snapshot(), rpcRequest: error?.rpcRequest});
    } finally {
      busy = false;
    }
  }

  async function restoreExisting(raw) {
    if (busy || state.status !== 'restore-required') throw new CodexSourceSessionError(
      'RESTORE_UNAVAILABLE', 'restore requires a fresh source-session executor',
      {phase: state.phase, state: snapshot()});
    const input = validateRestoreInput(raw, scopeRef);
    const budget = toRunBudget(input.deadlineMs);
    let claimInvoked = false;
    busy = true;
    state = {...state, status: 'restoring', phase: 'restore-read',
      restoration: {transferId: input.transferId, expectedScope: input.expectedScope,
        ...(input.source ? {source: input.source} : {}),
        requestedResume: input.resume}};
    try {
      ensureBindings();
      const record = input.source ? null : immutable(await boundedOperation(bound.readRecord,
        [input.transferId, scopeRef], budget.monotonicDeadline, 'recorder.read'));
      const observedScope = immutable(await boundedOperation(bound.readScope,
        [scopeRef], budget.monotonicDeadline, 'recorder.readScope'));
      ensureBindings();
      const ledger = record?.state, plan = ledger?.plan;
      const targetThreadId = input.source?.threadId ?? ledger?.target?.threadId;
      if (input.source) {
        if (canonical(observedScope) !== canonical(input.expectedScope) ||
            input.source.threadId !== input.expectedScope.writerThreadId ||
            input.source.connectionId === bound.connectionId) {
          return lockFailure('RESTORE_PRECONDITION_FAILED',
            'source identity, acknowledged scope or fresh controller binding differs', null,
            {phase: 'restore-precondition-failed', state: {observedScope}});
        }
      } else if (!plainObject(record) || !Number.isSafeInteger(record.revision) ||
          !plainObject(ledger) || !plainObject(plan) ||
          canonical(observedScope) !== canonical(input.expectedScope) ||
          record.lease?.scopeRef !== input.expectedScope.scopeRef ||
          record.lease?.writerThreadId !== input.expectedScope.writerThreadId ||
          record.lease?.transferId !== null ||
          record.lease?.token !== input.expectedScope.token ||
          ledger.phase !== 'source-subscription-released' || ledger.pendingEffect !== null ||
          ledger.transferId !== input.transferId || ledger.scopeRef !== scopeRef ||
          ledger.writer !== 'target' || ledger.writerThreadId !== targetThreadId ||
          ledger.sourceRecovery !== 'retained' ||
          ledger.subscriptionRelease?.observed !== true ||
          ledger.subscriptionRelease?.threadId !== ledger.source?.threadId ||
          plan.scopeRef !== scopeRef || plan.authorityRef !== ledger.authorityRef ||
          plan.stateRef !== ledger.stateRef || input.expectedScope.writerThreadId !== targetThreadId ||
          input.expectedScope.activeTransferId !== null ||
          ledger.observedLease?.scopeRef !== scopeRef ||
          ledger.observedLease?.transferId !== input.transferId ||
          ledger.observedLease?.writerThreadId !== targetThreadId ||
          ledger.observedLease?.token === input.expectedScope.token ||
          typeof ledger.verification?.release !== 'string' ||
          !ledger.verification.release.trim() ||
          ledger.connection?.connectionId === bound.connectionId ||
          !hasContinuityTools(plan.target?.dynamicTools)) {
        return lockFailure('RESTORE_PRECONDITION_FAILED',
          'durable transfer, explicit scope receipt or fresh controller binding is not restorable', null,
          {phase: 'restore-precondition-failed', state: {record, observedScope}});
      }
      const authorityRef = input.source?.authorityRef ?? ledger.authorityRef;
      const stateRef = input.source?.stateRef ?? ledger.stateRef;
      const priorConnectionId = input.source?.connectionId ?? ledger.connection.connectionId;
      text(targetThreadId, 'restored target thread id');
      const before = immutable(await Reflect.apply(bound.request, undefined,
        ['thread/read', {threadId: targetThreadId},
          budget.monotonicDeadline]));
      ensureBindings();
      const beforeStatus = before?.thread?.status?.type;
      if (before?.thread?.id !== targetThreadId || before.thread?.ephemeral !== false ||
          !['idle', 'notLoaded'].includes(beforeStatus)) {
        return lockFailure('RESTORE_TARGET_UNAVAILABLE',
          'native target is not the exact persistent idle or unloaded thread', null,
          {phase: 'restore-target-unavailable', state: {record, observedScope, before}});
      }
      const prepareFacts = immutable({connectionId: bound.connectionId,
        hostVersion: bound.hostVersion, transferId: input.transferId, scopeRef,
        authorityRef, stateRef, ...(input.source ? {source: input.source} : {}),
        target: {threadId: targetThreadId}, record, expectedScope: input.expectedScope,
        observedScope, threadRead: before, requestedResume: input.resume,
        nativeResumeParams: {threadId: targetThreadId, excludeTurns: true, ...input.params}});
      const prepared = immutable(await boundedOperation(bound.verify,
        ['restore-prepare', prepareFacts, budget.monotonicDeadline],
        budget.monotonicDeadline, 'verify:restore-prepare'));
      ensureBindings();
      if (prepared?.decision !== 'allow' || prepared.scopeRef !== scopeRef ||
          prepared.authorityRef !== authorityRef || prepared.stateRef !== stateRef ||
          typeof prepared.sourceRef !== 'string' || !prepared.sourceRef.trim() ||
          prepared.pauseStateVerified !== true || prepared.priorControllerQuiesced !== true ||
          prepared.pendingEffectsReconciled !== true || prepared.restorationAuthorized !== true ||
          prepared.singleWriter !== true || prepared.resumeInitializationSafe !== true ||
          input.source && (prepared.sourceOriginVerified !== true ||
            typeof prepared.sourceOriginEvidenceRef !== 'string' || !prepared.sourceOriginEvidenceRef.trim())) {
        return lockFailure('RESTORE_PREPARE_DENIED',
          'restore-prepare verifier did not authorize initialization', null,
          {phase: 'restore-prepare-denied', state: {record, observedScope, before, prepared}});
      }
      state = {...state, phase: 'restore-claim-pending', restoration: {
        ...state.restoration, targetThreadId, recordRevision: record?.revision ?? null,
        prepareSourceRef: prepared.sourceRef, threadReadBefore: before,
        prepareVerdict: prepared}};
      let claim;
      try {
        claim = immutable(await boundedOperation(() => {
          claimInvoked = true;
          return Reflect.apply(bound.claimScope, undefined,
            [scopeRef, input.expectedScope]);
        }, [], budget.monotonicDeadline, 'recorder.claimScope'));
      } catch (error) {
        return lockFailure(claimInvoked ? 'RESTORE_CLAIM_UNKNOWN' : 'RESTORE_CLAIM_NOT_INVOKED',
          claimInvoked ? 'scope claim outcome is unknown and must not be replayed' :
            'scope claim deadline elapsed before invocation', error,
          {phase: claimInvoked ? 'restore-claim-unknown' : 'restore-claim-not-invoked'});
      }
      state = {...state, restoration: {...state.restoration, claimReceipt: claim}};
      ensureBindings();
      if (claim?.scope?.scopeRef !== scopeRef ||
          claim.scope.writerThreadId !== targetThreadId || claim.scope.activeTransferId !== null ||
          typeof claim.scope.token !== 'string' || !claim.scope.token.trim() ||
          claim.scope.token === input.expectedScope.token) {
        return lockFailure('RESTORE_CLAIM_UNKNOWN',
          'scope claim acknowledgement is malformed and must not be replayed', null,
          {phase: 'restore-claim-unknown'});
      }
      const claimedScope = immutable(await boundedOperation(bound.readScope, [scopeRef],
        budget.monotonicDeadline, 'recorder.readScope after claim'));
      ensureBindings();
      if (canonical(claimedScope) !== canonical(claim.scope)) {
        return lockFailure('RESTORE_CLAIM_UNKNOWN',
          'scope claim readback differs and must not be replayed', null,
          {phase: 'restore-claim-unknown', state: {claimedScope}});
      }
      state = {...state, phase: 'restore-resume-pending', scope: claimedScope,
        sourceThreadId: targetThreadId,
        restoration: {...state.restoration, claimedScope}};
      const resumeParams = immutable({threadId: targetThreadId, excludeTurns: true, ...input.params});
      let resumed;
      try {
        resumed = immutable(await Reflect.apply(bound.request, undefined,
          ['thread/resume', resumeParams, budget.monotonicDeadline]));
      } catch (error) {
        return lockFailure('RESTORE_RESUME_UNKNOWN',
          'native thread resume outcome is unknown and must not be replayed', error,
          {phase: 'restore-resume-unknown', state: {resumeParams}});
      }
      state = {...state, phase: 'restore-resumed-check', lastSafeReceipt: resumed,
        restoration: {...state.restoration, resumeReceipt: resumed}};
      if (resumed?.thread?.id !== targetThreadId || resumed.thread?.ephemeral !== false) {
        return lockFailure('RESTORE_RESUME_UNKNOWN',
          'native thread resume acknowledgement has an invalid identity', null,
          {phase: 'restore-resume-unknown'});
      }
      const after = immutable(await Reflect.apply(bound.request, undefined,
        ['thread/read', {threadId: targetThreadId},
          budget.monotonicDeadline]));
      ensureBindings();
      if (after?.thread?.id !== targetThreadId || after.thread?.ephemeral !== false ||
          after.thread?.status?.type !== 'idle') {
        return lockFailure('RESTORE_POSTCHECK_FAILED',
          'resumed target is not the exact idle persistent thread', null,
          {phase: 'restore-postcheck-failed', state: {threadReadAfter: after}});
      }
      const restoredFacts = immutable({...prepareFacts, claimedScope,
        resumeParams, resumeReceipt: resumed, threadReadAfter: after});
      const restored = immutable(await boundedOperation(bound.verify,
        ['restore-resumed', restoredFacts, budget.monotonicDeadline],
        budget.monotonicDeadline, 'verify:restore-resumed'));
      ensureBindings();
      if (restored?.decision !== 'allow' || restored.scopeRef !== scopeRef ||
          restored.authorityRef !== authorityRef || restored.stateRef !== stateRef ||
          typeof restored.sourceRef !== 'string' || !restored.sourceRef.trim() ||
          typeof restored.nativeToolEvidenceRef !== 'string' ||
          !restored.nativeToolEvidenceRef.trim() ||
          restored.continuityToolsRestored !== true ||
          restored.targetSettingsMatch !== true || restored.historyRetained !== true ||
          restored.singleWriter !== true || restored.effectsVerified !== true) {
        return lockFailure('RESTORE_POSTCHECK_DENIED',
          'restore-resumed verifier did not accept native settings, tools and history', null,
          {phase: 'restore-postcheck-denied', state: {threadReadAfter: after, restored}});
      }
      const finalScope = immutable(await boundedOperation(bound.readScope, [scopeRef],
        budget.monotonicDeadline, 'recorder.readScope after restore verification'));
      ensureBindings();
      if (canonical(finalScope) !== canonical(claimedScope)) {
        return lockFailure('RESTORE_SCOPE_CHANGED',
          'claimed source scope changed before restoration could become ready', null,
          {phase: 'restore-scope-changed', state: {finalScope}});
      }
      state = {status: 'ready', phase: 'ready', scopeRef,
        sourceThreadId: targetThreadId, lastTurnId: null, turnCount: 0, transferCount: 0,
        // Counts and transfer receipts belong to this executor; an empty list
        // never asserts that the persisted source has no earlier history.
        transfers: input.source ? [] : [immutable({transferId: input.transferId,
          sourceThreadId: ledger.source.threadId, targetThreadId, revision: record.revision,
          settled: true, restored: true})], lastSafeReceipt: resumed,
        pendingRequest: null, scope: finalScope,
        restoration: immutable({transferId: input.transferId, targetThreadId,
          ...(input.source ? {source: input.source, sourceOriginEvidenceRef: prepared.sourceOriginEvidenceRef} : {}),
          priorConnectionId,
          connectionId: bound.connectionId, expectedScope: input.expectedScope,
          claimedScope: finalScope, resumeParams, prepareSourceRef: prepared.sourceRef,
          restoredSourceRef: restored.sourceRef,
          nativeToolEvidenceRef: restored.nativeToolEvidenceRef})};
      return immutable({status: 'restored', scopeRef, sourceThreadId: targetThreadId,
        transferId: input.transferId, scope: finalScope,
        claimLimit: input.source
          ? 'Owner-reconciled known source on a fresh controller; no created thread, fabricated transfer, effect replay or complete cold-recovery claim.'
          : 'Settled-transfer restoration on one fresh bound controller only; no active-effect, arbitrary-thread or complete cold-recovery claim.'});
    } catch (error) {
      if (error instanceof CodexSourceSessionError) throw error;
      return lockFailure(error?.code || 'RESTORE_FAILED',
        'source-session restoration failed', error, {phase: state.phase});
    } finally {
      busy = false;
    }
  }

  return Object.freeze({run, adoptTarget, snapshot, [RESTORE_SESSION]: restoreExisting});
}

function createCodexSourceSession(options) {
  return createSession(options, false);
}

async function restoreCodexSourceSession(options, raw) {
  const session = createSession(options, true);
  try {
    await session[RESTORE_SESSION](raw);
    return session;
  } catch (error) {
    if (error && typeof error === 'object') {
      Object.defineProperty(error, 'session', {value: session, enumerable: false});
    }
    throw error;
  }
}

module.exports = {
  createCodexSourceSession,
  restoreCodexSourceSession,
  CodexSourceSessionError,
};
