'use strict';

// Callable Codex carrier handoff adapter.
//
// The caller is a trusted, serialized host controller that already owns an
// initialized App Server connection, authentication, model/token budgets and
// ordered event delivery, and that survives both carriers. This module never
// starts or closes a process, discovers a Desktop connection, sets Goal/Plan,
// supplies storage, retries an ambiguous native effect, or archives/deletes a
// thread. Plan deadlines are absolute Unix milliseconds; callbacks receive the
// corresponding performance.now() deadline. Callbacks must be receiver-free or
// pre-bound. Hidden callback routing remains the trusted controller's duty and
// is not authenticated here. The recorder is the cooperating writer authority;
// it must arbitrate the pre-owned scope across controllers and restarts, but is
// not an OS lock and cannot assign scope authority the caller does not own.

const crypto = require('node:crypto');
const {performance} = require('node:perf_hooks');

const MAX_TEXT = 1024 * 1024;
const MAX_REF = 4096;
const MAX_TIMER_MS = 0x7fffffff;
const ALLOWED_METHODS = new Set([
  'thread/read',
  'turn/interrupt',
  'thread/start',
  'turn/start',
  'thread/resume',
  'thread/unsubscribe',
]);

class CarrierHandoffError extends Error {
  constructor(code, message, options = {}) {
    super(message);
    this.name = 'CarrierHandoffError';
    this.code = code;
    this.reason = message;
    this.stage = options.stage || 'unknown';
    this.transferId = options.transferId || null;
    this.reconciliationRequired = options.reconciliationRequired === true;
    this.details = immutable(options.details || {});
    this.state = immutable(options.state || {});
  }
}

class CallbackDeadline extends Error {
  constructor(label) {
    super(`${label} callback deadline exceeded`);
    this.name = 'CallbackDeadline';
  }
}

function fail(code, message, options) {
  throw new CarrierHandoffError(code, message, options);
}

function plainObject(value) {
  if (!value || typeof value !== 'object' || Array.isArray(value)) return false;
  const prototype = Object.getPrototypeOf(value);
  return prototype === Object.prototype || prototype === null;
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
  let copy;
  if (Array.isArray(value)) {
    copy = value.map((item) => cloneData(item, seen));
  } else {
    if (!plainObject(value)) throw new TypeError('non-plain data object');
    copy = {};
    for (const [key, item] of Object.entries(value)) {
      if (item === undefined) throw new TypeError(`undefined data field: ${key}`);
      Object.defineProperty(copy, key, {
        value: cloneData(item, seen), enumerable: true, writable: true, configurable: true,
      });
    }
  }
  seen.delete(value);
  return copy;
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
    return `{${Object.keys(value).sort().map((key) =>
      `${JSON.stringify(key)}:${canonical(value[key])}`).join(',')}}`;
  }
  return JSON.stringify(value);
}

function digest(value) {
  return crypto.createHash('sha256').update(canonical(value)).digest('hex');
}

function nativeRequestReference(error, method, binding) {
  try {
    const value = error?.rpcRequest;
    exactKeys(value, ['connectionId', 'hostVersion', 'requestId', 'method'], [], 'rpcRequest');
    const ref = {connectionId: value.connectionId, hostVersion: value.hostVersion,
      requestId: value.requestId, method: value.method};
    if (ref.connectionId !== binding.connectionId || ref.hostVersion !== binding.hostVersion ||
        ref.method !== method ||
        !((typeof ref.requestId === 'string' && ref.requestId.trim() && ref.requestId.length <= MAX_REF) ||
          Number.isSafeInteger(ref.requestId))) return null;
    return immutable({connectionId: ref.connectionId, hostVersion: ref.hostVersion,
      requestId: ref.requestId, method: ref.method});
  } catch (_) { return null; }
}

const HANDOFF_PROPOSAL_TOOL = immutable({
  type: 'function',
  name: 'accord_request_handoff',
  description: 'Request a carrier handoff. On queued acknowledgement, finish this source turn without further actions on the transferred work; responsibility remains with the source until verified takeover.',
  inputSchema: {
    type: 'object',
    properties: {
      reason: {type: 'string', minLength: 1, maxLength: MAX_REF},
      checkpointRef: {type: 'string', minLength: 1, maxLength: MAX_REF},
    },
    required: ['reason'],
    additionalProperties: false,
  },
});

function text(value, name, limit = MAX_REF) {
  if (typeof value !== 'string' || !value.trim() || value.length > limit) {
    throw new TypeError(`${name} must be a nonempty bounded string`);
  }
  return value;
}

function exactKeys(value, required, optional, name) {
  if (!plainObject(value)) throw new TypeError(`${name} must be an object`);
  const allowed = new Set([...required, ...optional]);
  for (const key of required) {
    if (!Object.hasOwn(value, key)) throw new TypeError(`${name}.${key} is required`);
  }
  for (const key of Object.keys(value)) {
    if (!allowed.has(key)) throw new TypeError(`${name}.${key} is not supported`);
  }
}

function validatePlan(raw, wallNowMs, historical = false) {
  exactKeys(raw,
    ['transferId', 'scopeRef', 'authorityRef', 'stateRef', 'source', 'target', 'handoffText',
      'continuation', 'deadlineMs', 'recoveryDeadlineMs'], [], 'plan');
  exactKeys(raw.source, ['threadId'], ['turnId'], 'plan.source');
  exactKeys(raw.target, ['cwd', 'model'], ['modelProvider', 'effort', 'dynamicTools'], 'plan.target');
  exactKeys(raw.continuation, ['input', 'sandboxPolicy'], [], 'plan.continuation');
  text(raw.transferId, 'plan.transferId');
  text(raw.scopeRef, 'plan.scopeRef');
  text(raw.authorityRef, 'plan.authorityRef');
  text(raw.stateRef, 'plan.stateRef');
  text(raw.source.threadId, 'plan.source.threadId');
  if (Object.hasOwn(raw.source, 'turnId')) text(raw.source.turnId, 'plan.source.turnId');
  text(raw.target.cwd, 'plan.target.cwd', 32768);
  text(raw.target.model, 'plan.target.model');
  if (Object.hasOwn(raw.target, 'modelProvider')) text(raw.target.modelProvider, 'plan.target.modelProvider');
  if (Object.hasOwn(raw.target, 'effort')) text(raw.target.effort, 'plan.target.effort');
  if (Object.hasOwn(raw.target, 'dynamicTools')) {
    const tools = raw.target.dynamicTools;
    if (!Array.isArray(tools) || tools.length > 64) throw new TypeError('plan.target.dynamicTools must be a bounded array');
    const names = new Set();
    for (const tool of tools) {
      if (!plainObject(tool) || !plainObject(tool.inputSchema)) throw new TypeError('target dynamic tool and inputSchema must be objects');
      text(tool.name, 'target dynamic tool name');
      text(tool.description, 'target dynamic tool description', MAX_TEXT);
      if (tool.namespace != null) text(tool.namespace, 'target dynamic tool namespace');
      const name = JSON.stringify([tool.namespace ?? null, tool.name]);
      if (names.has(name)) throw new TypeError('target dynamic tool identity is duplicated');
      names.add(name);
    }
    if (Buffer.byteLength(JSON.stringify(cloneData(tools)), 'utf8') > MAX_TEXT) throw new TypeError('target dynamic tools exceed the plan size bound');
  }
  text(raw.handoffText, 'plan.handoffText', MAX_TEXT);
  text(raw.continuation.input, 'plan.continuation.input', MAX_TEXT);
  if (!plainObject(raw.continuation.sandboxPolicy)) {
    throw new TypeError('plan.continuation.sandboxPolicy must be an object');
  }
  cloneData(raw.continuation.sandboxPolicy);
  for (const name of ['deadlineMs', 'recoveryDeadlineMs']) {
    if (!Number.isSafeInteger(raw[name]) || raw[name] <= 0 || (!historical && raw[name] <= wallNowMs)) {
      throw new TypeError(`plan.${name} must be a future absolute millisecond deadline`);
    }
    if (!historical && raw[name] - wallNowMs > MAX_TIMER_MS) {
      throw new TypeError(`plan.${name} exceeds the supported callback timer range`);
    }
  }
  if (raw.recoveryDeadlineMs < raw.deadlineMs) {
    throw new TypeError('plan.recoveryDeadlineMs must not precede plan.deadlineMs');
  }
  return immutable(raw);
}

function validateInterfaces(dependencies) {
  exactKeys(dependencies, ['transport', 'recorder', 'verify'], [], 'dependencies');
  const {transport, recorder, verify} = dependencies;
  if (!plainObject(transport)) throw new TypeError('transport must be an object');
  text(transport.connectionId, 'transport.connectionId');
  text(transport.hostVersion, 'transport.hostVersion');
  if (typeof transport.request !== 'function' || typeof transport.waitTerminal !== 'function') {
    throw new TypeError('transport request and waitTerminal callbacks are required');
  }
  if (!plainObject(recorder) || typeof recorder.begin !== 'function' ||
      typeof recorder.compareAndSet !== 'function') {
    throw new TypeError('recorder begin and compareAndSet callbacks are required');
  }
  if (typeof verify !== 'function') throw new TypeError('verify callback is required');
  return {transport, recorder, verify};
}

function validateProposalRequest(value, plan, connectionBinding) {
  exactKeys(value, ['connectionId', 'hostVersion', 'id', 'method', 'params'], ['jsonrpc'],
    'nativeRequest');
  if (Object.hasOwn(value, 'jsonrpc') && value.jsonrpc !== '2.0') {
    throw new TypeError('nativeRequest.jsonrpc must be 2.0 when supplied');
  }
  if (!((typeof value.id === 'string' && value.id.trim() && value.id.length <= MAX_REF) ||
      Number.isSafeInteger(value.id))) {
    throw new TypeError('nativeRequest.id must be a bounded string or safe integer');
  }
  if (value.connectionId !== connectionBinding.connectionId ||
      value.hostVersion !== connectionBinding.hostVersion) {
    throw new TypeError('nativeRequest host/controller binding differs');
  }
  if (value.method !== 'item/tool/call') throw new TypeError('nativeRequest.method must be item/tool/call');
  exactKeys(value.params, ['threadId', 'turnId', 'callId', 'tool', 'arguments'], ['namespace'],
    'nativeRequest.params');
  if (value.params.threadId !== plan.source.threadId || value.params.turnId !== plan.source.turnId) {
    throw new TypeError('nativeRequest source identity differs from the plan');
  }
  text(value.params.callId, 'nativeRequest.params.callId');
  if (value.params.tool !== HANDOFF_PROPOSAL_TOOL.name) {
    throw new TypeError('nativeRequest.params.tool is not the handoff proposal tool');
  }
  if (Object.hasOwn(value.params, 'namespace') && value.params.namespace !== null) {
    throw new TypeError('nativeRequest.params.namespace differs from the unnamespaced proposal tool');
  }
  exactKeys(value.params.arguments, ['reason'], ['checkpointRef'], 'nativeRequest.params.arguments');
  text(value.params.arguments.reason, 'nativeRequest.params.arguments.reason');
  if (Object.hasOwn(value.params.arguments, 'checkpointRef')) {
    text(value.params.arguments.checkpointRef, 'nativeRequest.params.arguments.checkpointRef');
  }
  return immutable(value);
}

function before(deadlineMs, stage, transferId) {
  if (performance.now() >= deadlineMs) {
    fail('DEADLINE_EXCEEDED', `${stage} deadline exceeded`, {stage, transferId});
  }
}

async function bounded(callback, deadlineMs, label) {
  const remaining = deadlineMs - performance.now();
  if (remaining <= 0) throw new CallbackDeadline(label);
  let timer;
  try {
    return await Promise.race([
      Promise.resolve().then(callback),
      new Promise((_, reject) => {
        timer = setTimeout(() => reject(new CallbackDeadline(label)), remaining);
      }),
    ]);
  } finally {
    if (timer) clearTimeout(timer);
  }
}

function threadFrom(value, expected, stage, transferId) {
  const thread = value && plainObject(value.thread) ? value.thread : null;
  if (!thread || typeof thread.id !== 'string' || !thread.id.trim() ||
      (expected && thread.id !== expected)) {
    fail('INVALID_NATIVE_RECEIPT', `${stage} returned an invalid thread identity`, {
      stage, transferId, reconciliationRequired: stage === 'target-created',
    });
  }
  return thread;
}

function turnFrom(value, expectedThread, stage, transferId) {
  const turn = value && plainObject(value.turn) ? value.turn : null;
  if (!turn || typeof turn.id !== 'string' || !turn.id.trim()) {
    fail('INVALID_NATIVE_RECEIPT', `${stage} returned an invalid turn identity`, {
      stage, transferId, reconciliationRequired: true,
      details: {expectedThread},
    });
  }
  return turn;
}

function terminalView(value) {
  if (!plainObject(value) || value.method !== 'turn/completed') return null;
  const params = plainObject(value.params) ? value.params : null;
  const turn = params && plainObject(params.turn) ? params.turn : null;
  if (params && typeof params.threadId === 'string' && turn && typeof turn.id === 'string') {
    return {threadId: params.threadId, turnId: turn.id, status: turn.status};
  }
  return null;
}

function idleThread(value, stage, transferId) {
  const thread = threadFrom(value, null, stage, transferId);
  const kind = plainObject(thread.status) ? thread.status.type : null;
  if (!['idle', 'notLoaded'].includes(kind)) {
    fail('SOURCE_NOT_QUIESCENT', `${stage} source is not observably idle`, {
      stage, transferId, reconciliationRequired: true,
      details: {statusType: typeof kind === 'string' ? kind : null},
    });
  }
}

function exactTerminal(value, threadId, turnId, stage, transferId) {
  const view = terminalView(value);
  const allowedTerminal = new Set(['completed', 'interrupted', 'failed']);
  if (!view || view.threadId !== threadId || view.turnId !== turnId ||
      typeof view.status !== 'string' || !view.status.trim() ||
      !allowedTerminal.has(view.status)) {
    fail('INVALID_TERMINAL_RECEIPT', `${stage} did not observe the exact required terminal`, {
      stage, transferId, reconciliationRequired: true,
      details: {threadId, turnId},
    });
  }
  return view;
}

function requireCompleted(value, threadId, turnId, stage, transferId) {
  const view = terminalView(value);
  if (!view || view.threadId !== threadId || view.turnId !== turnId || view.status !== 'completed') {
    fail('TARGET_TURN_UNSUCCESSFUL', `${stage} target turn did not complete successfully`, {
      stage, transferId, reconciliationRequired: true,
      details: {threadId, turnId, status: view?.status || null},
    });
  }
}

function validateProposalDispatch(value, plan, proposalRequest, response, transferId) {
  exactKeys(value, ['toolCompleted', 'sourceTerminal', 'current'], [], 'dispatch');
  exactKeys(value.current, ['scopeRef', 'authorityRef', 'stateRef', 'writerThreadId'], [],
    'dispatch.current');
  if (value.current.scopeRef !== plan.scopeRef || value.current.authorityRef !== plan.authorityRef ||
      value.current.stateRef !== plan.stateRef ||
      value.current.writerThreadId !== plan.source.threadId) {
    fail('PROPOSAL_CURRENT_STATE_CHANGED', 'proposal dispatch current state differs', {
      stage: 'proposal-dispatch', transferId, reconciliationRequired: true,
    });
  }

  const completed = value.toolCompleted;
  exactKeys(completed, ['method', 'params'], ['emittedAtMs'], 'dispatch.toolCompleted');
  if (completed.method !== 'item/completed') {
    fail('INVALID_PROPOSAL_COMPLETION', 'proposal tool completion method differs', {
      stage: 'proposal-dispatch', transferId, reconciliationRequired: true,
    });
  }
  exactKeys(completed.params, ['item', 'threadId', 'turnId'], ['completedAtMs'],
    'dispatch.toolCompleted.params');
  const item = completed.params.item;
  exactKeys(item, ['type', 'id', 'tool', 'status', 'contentItems', 'success'],
    ['namespace', 'arguments', 'durationMs'], 'dispatch.toolCompleted.params.item');
  const requestParams = proposalRequest.params;
  const namespace = Object.hasOwn(requestParams, 'namespace') ? requestParams.namespace : null;
  const completedNamespace = Object.hasOwn(item, 'namespace') ? item.namespace : null;
  if (completed.params.threadId !== requestParams.threadId ||
      completed.params.turnId !== requestParams.turnId || item.type !== 'dynamicToolCall' ||
      item.id !== requestParams.callId || item.tool !== requestParams.tool ||
      completedNamespace !== namespace ||
      (Object.hasOwn(item, 'arguments') && canonical(item.arguments) !== canonical(requestParams.arguments)) ||
      item.status !== 'completed' || item.success !== true ||
      canonical(item.contentItems) !== canonical(response.result.contentItems)) {
    fail('INVALID_PROPOSAL_COMPLETION', 'proposal tool completion identity or result differs', {
      stage: 'proposal-dispatch', transferId, reconciliationRequired: true,
    });
  }

  exactTerminal(value.sourceTerminal, plan.source.threadId, plan.source.turnId,
    'proposal-dispatch:source-terminal', transferId);
  requireCompleted(value.sourceTerminal, plan.source.threadId, plan.source.turnId,
    'proposal-dispatch:source-terminal', transferId);
  return immutable(value);
}

function summarizeThread(value) {
  const thread = value.thread;
  return immutable({id: thread.id});
}

function summarizeTurn(value, threadId) {
  return immutable({threadId, id: value.turn.id});
}

function verificationRequirements(stage) {
  const requirements = {};
  if (stage === 'prepare') Object.assign(requirements, {targetInitializationSafe: true});
  if (stage === 'quiesced') Object.assign(requirements, {quiesced: true, noOtherWriters: true});
  if (stage === 'target-created') Object.assign(requirements,
    {targetSettingsMatch: true, initializationEffectsVerified: true});
  if (stage === 'accepted') Object.assign(requirements,
    {accepted: true, sourceIdle: true, intakeEffectsVerified: true});
  if (stage === 'continue') Object.assign(requirements, {singleWriter: true});
  if (stage === 'continued' || stage === 'release') {
    Object.assign(requirements, {effectsVerified: true, singleWriter: true});
  }
  return requirements;
}

function createExecution(rawPlan, rawDependencies) {
  const entryClock = {wallMs: Date.now(), monotonicMs: performance.now()};
  let plan;
  let dependencies;
  try {
    plan = validatePlan(rawPlan, entryClock.wallMs);
    dependencies = validateInterfaces(rawDependencies);
  } catch (error) {
    if (error instanceof CarrierHandoffError) throw error;
    throw new CarrierHandoffError('INVALID_INPUT', error.message, {
      transferId: rawPlan && typeof rawPlan.transferId === 'string' ? rawPlan.transferId : null,
    });
  }

  const {transport, recorder, verify} = dependencies;
  const connectionBinding = immutable({
    connectionId: transport.connectionId,
    hostVersion: transport.hostVersion,
  });
  const callbackBinding = {
    request: transport.request,
    waitTerminal: transport.waitTerminal,
    begin: recorder.begin,
    compareAndSet: recorder.compareAndSet,
    verify,
  };
  const transferId = plan.transferId;
  const workDeadlineMs = entryClock.monotonicMs + (plan.deadlineMs - entryClock.wallMs);
  const recoveryDeadlineMs = entryClock.monotonicMs +
    (plan.recoveryDeadlineMs - entryClock.wallMs);
  const planDigest = digest(plan);
  const packet = immutable({
    transferId,
    scopeRef: plan.scopeRef,
    planDigest,
    authorityRef: plan.authorityRef,
    stateRef: plan.stateRef,
    connection: connectionBinding,
    plan,
    source: plan.source,
    target: plan.target,
  });
  let revision = null;
  let lease = null;
  let recordState = null;
  let recorderCertain = true;
  let bindingCertain = true;
  let nativeMutation = false;
  let nativeRequestUnresolved = false;
  let unresolvedEffect = null;
  let writerTransferred = false;
  let targetThreadId = null;
  let targetTurnId = null;
  let targetTurnTerminal = false;
  let sourceEphemeral = null, knownSourceEphemeral = null;
  let stage = 'begin';
  let proposalRequest = null;
  let proposalResponse = null;
  let dispatchStarted = false;
  let proposalChannelCheck = null;
  const verificationSourceRefs = {};
  const evidence = {};

  const ensureWork = (name) => before(workDeadlineMs, name, transferId);
  const ensureRecovery = (name) => before(recoveryDeadlineMs, name, transferId);

  function observeSourceThread(value, readStage) {
    const source = threadFrom(value, plan.source.threadId, readStage, transferId);
    const observed = typeof source.ephemeral === 'boolean' ? source.ephemeral : null;
    if (observed !== null && knownSourceEphemeral !== null && observed !== knownSourceEphemeral) {
      fail('SOURCE_PERSISTENCE_CHANGED', 'native source persistence changed during handoff', {
        stage: readStage, transferId, reconciliationRequired: true,
        details: {previousEphemeral: knownSourceEphemeral, observedEphemeral: observed},
      });
    }
    if (observed !== null) knownSourceEphemeral = observed;
    // Missing current metadata cannot borrow an earlier positive observation.
    sourceEphemeral = observed;
    return source;
  }

  function ensureBinding(name) {
    if (proposalChannelCheck) proposalChannelCheck();
    if (transport.connectionId !== connectionBinding.connectionId ||
        transport.hostVersion !== connectionBinding.hostVersion ||
        transport.request !== callbackBinding.request ||
        transport.waitTerminal !== callbackBinding.waitTerminal ||
        recorder.begin !== callbackBinding.begin ||
        recorder.compareAndSet !== callbackBinding.compareAndSet ||
        rawDependencies.verify !== callbackBinding.verify) {
      bindingCertain = false;
      fail('HOST_BINDING_CHANGED', `${name} host/controller binding changed`, {
        stage: name, transferId, reconciliationRequired: true,
        state: {connection: connectionBinding, pendingEffect: unresolvedEffect},
      });
    }
  }

  async function begin(initialEffect = {method: 'thread/read', threadId: plan.source.threadId},
      initialPhase = 'prepared') {
    ensureWork('begin');
    const initial = immutable({
      phase: initialPhase,
      transferId,
      planDigest,
      scopeRef: plan.scopeRef,
      authorityRef: plan.authorityRef,
      stateRef: plan.stateRef,
      connection: connectionBinding,
      plan,
      writer: 'source',
      writerThreadId: plan.source.threadId,
      sourceRecovery: 'retained',
      source: plan.source,
      target: null,
      intakeTurn: null,
      continuationTurn: null,
      expectedLease: null,
      observedLease: null,
      pendingEffect: initialEffect,
    });
    let result;
    try {
      ensureBinding('begin');
      result = await bounded(() => Reflect.apply(callbackBinding.begin, undefined,
        [transferId, planDigest, initial]),
        workDeadlineMs, 'recorder.begin');
      ensureBinding('begin');
      ensureWork('begin');
    } catch (cause) {
      recorderCertain = false;
      throw new CarrierHandoffError('RECORDER_BEGIN_UNKNOWN',
        'recorder begin outcome is unknown', {
          stage: 'begin', transferId, reconciliationRequired: true,
          details: {cause: errorData(cause)},
        });
    }
    let snap;
    try { snap = immutable(result); }
    catch (cause) {
      recorderCertain = false;
      throw new CarrierHandoffError('RECORDER_BEGIN_UNRECONCILED',
        'recorder begin returned malformed state without reconciliation', {
          stage: 'begin', transferId, reconciliationRequired: true,
          details: {cause: errorData(cause)},
        });
    }
    if (!plainObject(snap) || snap.created !== true ||
        !Number.isSafeInteger(snap.revision) || snap.revision < 0 ||
        !plainObject(snap.lease) || snap.lease.scopeRef !== plan.scopeRef ||
        snap.lease.transferId !== transferId || typeof snap.lease.token !== 'string' ||
        !snap.lease.token.trim() || snap.lease.token.length > MAX_REF ||
        snap.lease.writerThreadId !== plan.source.threadId) {
      recorderCertain = false;
      fail('RECORDER_BEGIN_UNRECONCILED',
        'recorder did not create a unique transfer or reconcile existing state', {
        stage: 'begin', transferId, reconciliationRequired: true,
      });
    }
    revision = snap.revision;
    lease = immutable(snap.lease);
    recordState = immutable({...initial, observedLease: lease});
  }

  async function record(next, useRecovery = false) {
    const deadline = useRecovery ? recoveryDeadlineMs : workDeadlineMs;
    before(deadline, `record:${next.phase}`, transferId);
    if (!recorderCertain || revision === null || !lease) {
      fail('RECORDER_STATE_UNKNOWN', 'recorder revision is not safe for another transition', {
        stage, transferId, reconciliationRequired: true,
      });
    }
    const permittedWriters = new Set([plan.source.threadId, targetThreadId].filter(Boolean));
    if (!permittedWriters.has(next.writerThreadId)) {
      fail('INVALID_WRITER_TRANSITION', 'next recorder state lacks the bound scope writer', {
        stage, transferId, reconciliationRequired: true,
      });
    }
    const expectedLease = immutable(lease);
    const snap = immutable({...next, scopeRef: plan.scopeRef,
      writerThreadId: next.writerThreadId, expectedLease, observedLease: lease});
    let result;
    try {
      ensureBinding(`record:${next.phase}`);
      result = await bounded(() => Reflect.apply(callbackBinding.compareAndSet, undefined,
        [transferId, revision, snap, expectedLease]),
        deadline, 'recorder.compareAndSet');
      ensureBinding(`record:${next.phase}`);
      before(deadline, `record:${next.phase}`, transferId);
    } catch (cause) {
      recorderCertain = false;
      throw new CarrierHandoffError('RECORDER_COMMIT_UNKNOWN', 'recorder transition outcome is unknown', {
        stage, transferId, reconciliationRequired: true,
        details: {attemptedPhase: snap.phase, cause: errorData(cause)},
      });
    }
    let normalizedResult;
    let nextLease;
    let nextRecordState;
    try {
      normalizedResult = immutable(result);
      if (!plainObject(normalizedResult) ||
          !Number.isSafeInteger(normalizedResult.revision) ||
          normalizedResult.revision <= revision || !plainObject(normalizedResult.lease) ||
          normalizedResult.lease.scopeRef !== plan.scopeRef ||
          normalizedResult.lease.transferId !== transferId ||
          typeof normalizedResult.lease.token !== 'string' ||
          !normalizedResult.lease.token.trim() ||
          normalizedResult.lease.token.length > MAX_REF ||
          normalizedResult.lease.writerThreadId !== snap.writerThreadId) {
        throw new TypeError('invalid scoped lease acknowledgement');
      }
      nextLease = immutable(normalizedResult.lease);
      nextRecordState = immutable({...snap, observedLease: nextLease});
    } catch (cause) {
      recorderCertain = false;
      throw new CarrierHandoffError('INVALID_RECORDER_LEASE',
        'recorder did not return the requested scoped lease state', {
          stage, transferId, reconciliationRequired: true,
          details: {attemptedPhase: snap.phase, cause: errorData(cause)},
      });
    }
    revision = normalizedResult.revision;
    lease = nextLease;
    recordState = nextRecordState;
  }

  async function request(method, params, effectStage, mutating = false, recovery = false) {
    if (!ALLOWED_METHODS.has(method)) {
      fail('UNSUPPORTED_NATIVE_METHOD', `native method is not allowed: ${method}`, {
        stage: effectStage, transferId,
      });
    }
    const deadline = recovery ? recoveryDeadlineMs : workDeadlineMs;
    before(deadline, effectStage, transferId);
    if (mutating) nativeMutation = true;
    const plannedEffect = mutating ? immutable({method, params}) : null;
    if (plannedEffect) unresolvedEffect = plannedEffect;
    try {
      ensureBinding(effectStage);
      const value = await bounded(
        () => Reflect.apply(callbackBinding.request, undefined,
          [method, immutable(params), deadline]),
        deadline, `transport.request:${method}`);
      before(deadline, effectStage, transferId);
      ensureBinding(effectStage);
      const result = immutable(value);
      if (plannedEffect) unresolvedEffect = null;
      return result;
    } catch (cause) {
      const requestRef = nativeRequestReference(cause, method, connectionBinding);
      if (mutating) {
        nativeRequestUnresolved = true;
        if (requestRef) unresolvedEffect = immutable({...plannedEffect, requestRef});
      }
      if (cause instanceof CarrierHandoffError) throw cause;
      throw new CarrierHandoffError(mutating ? 'NATIVE_EFFECT_UNKNOWN' : 'NATIVE_READ_FAILED',
        `${effectStage} failed`, {
          stage: effectStage,
          transferId,
          reconciliationRequired: mutating || nativeMutation,
          details: {method, cause: errorData(cause), ...(requestRef ? {requestRef} : {})},
        });
    }
  }

  async function waitTerminal(threadId, turnId, waitStage, recovery = false) {
    const deadline = recovery ? recoveryDeadlineMs : workDeadlineMs;
    before(deadline, waitStage, transferId);
    let value;
    try {
      ensureBinding(waitStage);
      value = immutable(await bounded(
        () => Reflect.apply(callbackBinding.waitTerminal, undefined,
          [threadId, turnId, deadline]),
        deadline, 'transport.waitTerminal'));
      before(deadline, waitStage, transferId);
      ensureBinding(waitStage);
    } catch (cause) {
      if (cause instanceof CarrierHandoffError) throw cause;
      throw new CarrierHandoffError('TERMINAL_OUTCOME_UNKNOWN', `${waitStage} failed`, {
        stage: waitStage, transferId, reconciliationRequired: true,
        details: {threadId, turnId, cause: errorData(cause)},
      });
    }
    exactTerminal(value, threadId, turnId, waitStage, transferId);
    return value;
  }

  async function verifyStage(name, facts) {
    ensureWork(`verify:${name}`);
    let result;
    try {
      ensureBinding(`verify:${name}`);
      result = immutable(await bounded(
        () => Reflect.apply(callbackBinding.verify, undefined,
          [name, immutable({packet, ledger: recordState, ...facts}), workDeadlineMs]),
        workDeadlineMs, `verify:${name}`));
      ensureWork(`verify:${name}`);
      ensureBinding(`verify:${name}`);
    } catch (cause) {
      if (cause instanceof CarrierHandoffError) throw cause;
      throw new CarrierHandoffError('VERIFIER_FAILED', `${name} verifier failed`, {
        stage: name, transferId, reconciliationRequired: nativeMutation,
        details: {cause: errorData(cause)},
      });
    }
    const requirements = verificationRequirements(name);
    const requestsContext = name === 'accepted' && result.decision === 'request-context';
    const allowed = result.decision === 'allow' || requestsContext;
    let requestContextValid = true;
    if (requestsContext) {
      try { text(result.additionalInput, 'accepted.additionalInput', MAX_TEXT); }
      catch (_) { requestContextValid = false; }
      requestContextValid = requestContextValid && result.sourceIdle === true &&
        result.intakeEffectsVerified === true;
    }
    if (!allowed || !requestContextValid || result.scopeRef !== plan.scopeRef ||
        result.authorityRef !== plan.authorityRef ||
        result.stateRef !== plan.stateRef || typeof result.sourceRef !== 'string' ||
        !result.sourceRef.trim() || result.sourceRecoveryReady !== true ||
        (!requestsContext && Object.entries(requirements)
          .some(([key, expected]) => result[key] !== expected))) {
      fail('VERIFICATION_DENIED', `${name} verifier did not allow the transition`, {
        stage: name, transferId, reconciliationRequired: nativeMutation,
        details: {required: requirements, decision: result.decision || null},
      });
    }
    verificationSourceRefs[name] = result.sourceRef;
    return result;
  }

  async function bestEffortTargetStop() {
    if (!recorderCertain || !bindingCertain) {
      return {attempted: false, recorderCertain, bindingCertain};
    }
    try { ensureBinding('recovery:binding'); }
    catch (_) { return {attempted: false, recorderCertain, bindingCertain: false}; }
    if (nativeRequestUnresolved || !targetThreadId || !targetTurnId || targetTurnTerminal ||
        performance.now() >= recoveryDeadlineMs) {
      return {attempted: false, unresolvedNativeRequest: nativeRequestUnresolved};
    }
    const recovery = {attempted: true, threadId: targetThreadId, turnId: targetTurnId};
    try {
      if (recorderCertain && revision !== null) {
        await record({...recordState, phase: 'reconciliation-required', sourceRecovery: 'retained',
          pendingEffect: {method: 'turn/interrupt', threadId: targetThreadId, turnId: targetTurnId}}, true);
      }
      ensureRecovery('recovery:target-interrupt');
      recovery.interrupt = await request('turn/interrupt',
        {threadId: targetThreadId, turnId: targetTurnId}, 'recovery:target-interrupt', true, true);
      recovery.terminal = await waitTerminal(targetThreadId, targetTurnId,
        'recovery:target-terminal', true);
      targetTurnTerminal = true;
      if (recorderCertain && revision !== null) {
        await record({...recordState, phase: 'reconciliation-required', sourceRecovery: 'retained',
          pendingEffect: null, recoveryStop: {threadId: targetThreadId,
            turnId: targetTurnId, terminalObserved: true}}, true);
      }
    } catch (error) {
      recovery.error = errorData(error);
    }
    return immutable(recovery);
  }

  async function handleFailure(cause) {
    const original = cause instanceof CarrierHandoffError ? cause :
      new CarrierHandoffError('HANDOFF_FAILED', 'carrier handoff failed', {
        stage, transferId, reconciliationRequired: nativeMutation || unresolvedEffect !== null,
        details: {cause: errorData(cause)},
      });
    const recovery = await bestEffortTargetStop();
    const reconciliationRequired = original.reconciliationRequired || nativeMutation ||
      unresolvedEffect !== null || writerTransferred || targetThreadId !== null ||
      !recorderCertain || !bindingCertain;
    const retainedPendingEffect = unresolvedEffect;
    if (recorderCertain && bindingCertain && revision !== null) {
      try {
        await record({...recordState,
          phase: reconciliationRequired ? 'reconciliation-required' : 'held',
          sourceRecovery: 'retained',
          pendingEffect: retainedPendingEffect,
          failure: {
            code: original.code,
            stage: original.stage,
            targetThreadId,
            targetTurnId,
            targetTurnTerminal,
            writerTransferred,
            recovery,
          }}, true);
      } catch (_) {
        recorderCertain = false;
      }
    }
    throw new CarrierHandoffError(original.code, original.message, {
      stage: original.stage,
      transferId,
      reconciliationRequired,
      state: {
        targetThreadId,
        targetTurnId,
        targetTurnTerminal,
        writer: writerTransferred ? 'target-or-unknown' : 'source-or-unknown',
        sourceRecovery: 'retained',
        recorderRevision: recorderCertain ? revision : null,
        scopeRef: plan.scopeRef,
        lease,
        bindingCertain,
        nativeRequestUnresolved,
        pendingEffect: retainedPendingEffect,
      },
      details: {
        planDigest,
        scopeRef: plan.scopeRef,
        lease,
        connectionId: connectionBinding.connectionId,
        hostVersion: connectionBinding.hostVersion,
        recorderRevision: recorderCertain ? revision : null,
        recorderCertain,
        bindingCertain,
        writer: writerTransferred ? 'target-or-unknown' : 'source-or-unknown',
        sourceRecovery: 'retained',
        targetThreadId,
        targetTurnId,
        targetTurnTerminal,
        nativeRequestUnresolved,
        pendingEffect: retainedPendingEffect,
        recovery,
        original: original.details,
      },
    });
  }

  async function runCore(observedSourceTerminal = null, beginRequired = true) {
    try {
      if (beginRequired) await begin();

      stage = 'prepare';
      const sourceReadBefore = await request('thread/read', {threadId: plan.source.threadId},
        'prepare:source-read');
    observeSourceThread(sourceReadBefore, stage);
    const prepared = await verifyStage('prepare', {
      connectionId: transport.connectionId,
      hostVersion: transport.hostVersion,
      source: plan.source,
      sourceRead: sourceReadBefore,
    });
    await record({...recordState, phase: 'prepared', pendingEffect: null,
      sourceRead: summarizeThread(sourceReadBefore), verification: {prepare: prepared.sourceRef}});

    let sourceTerminal = observedSourceTerminal;
    if (plan.source.turnId && !sourceTerminal) {
      stage = 'quiesce-source';
      await record({...recordState, phase: 'quiescing-source',
        pendingEffect: {method: 'turn/interrupt', threadId: plan.source.threadId,
          turnId: plan.source.turnId}});
      evidence.sourceInterrupt = await request('turn/interrupt',
        {threadId: plan.source.threadId, turnId: plan.source.turnId}, stage, true);
      sourceTerminal = await waitTerminal(plan.source.threadId, plan.source.turnId,
        'quiesce-source:terminal');
    }

    stage = 'quiesced';
    const sourceReadAfter = await request('thread/read', {threadId: plan.source.threadId},
      'quiesced:source-read');
    observeSourceThread(sourceReadAfter, stage);
    const quiesced = await verifyStage('quiesced', {
      connectionId: transport.connectionId,
      hostVersion: transport.hostVersion,
      source: plan.source,
      sourceReadBefore,
      sourceReadAfter,
      sourceTerminal,
    });
    idleThread(sourceReadAfter, stage, transferId);
    await record({...recordState, phase: 'source-quiesced', pendingEffect: null,
      sourceRead: summarizeThread(sourceReadAfter),
      verification: {...recordState.verification, quiesced: quiesced.sourceRef}});

    stage = 'target-created';
    await record({...recordState, phase: 'starting-target', pendingEffect: {
      method: 'thread/start', fresh: true, persistent: true, readOnly: true,
    }});
    const startParams = {
      cwd: plan.target.cwd,
      model: plan.target.model,
      ...(plan.target.modelProvider ? {modelProvider: plan.target.modelProvider} : {}),
      ...(Object.hasOwn(plan.target, 'dynamicTools') ? {dynamicTools: plan.target.dynamicTools} : {}),
      ephemeral: false,
      sandbox: 'read-only',
      approvalPolicy: 'never',
    };
    const targetStart = await request('thread/start', startParams, 'target-created:thread-start', true);
    targetThreadId = threadFrom(targetStart, null, stage, transferId).id;
    if (targetThreadId === plan.source.threadId) {
      fail('TARGET_NOT_FRESH', 'native target reused the source thread', {
        stage, transferId, reconciliationRequired: true,
      });
    }
    await record({...recordState, phase: 'target-started', target: {threadId: targetThreadId},
      pendingEffect: {method: 'thread/read', threadId: targetThreadId}});
    const targetRead = await request('thread/read', {threadId: targetThreadId},
      'target-created:thread-read');
    threadFrom(targetRead, targetThreadId, stage, transferId);
    const targetCreated = await verifyStage('target-created', {
      connectionId: transport.connectionId,
      hostVersion: transport.hostVersion,
      source: plan.source,
      target: {threadId: targetThreadId},
      requestedSettings: startParams,
      startResponse: targetStart,
      targetRead,
    });
    await record({...recordState, phase: 'target-created', pendingEffect: null,
      targetRead: summarizeThread(targetRead),
      verification: {...recordState.verification, targetCreated: targetCreated.sourceRef}});

    const intakeTurns = [];
    const intakeTerminals = [];
    const intakeVerificationSourceRefs = [];
    const seenIntakeTurnIds = new Set();
    let intake = null;
    let intakeTerminal = null;
    let intakeTurnId = null;
    let sourceReadAccepted = null;
    let accepted = null;
    let nextIntakeInput = plan.handoffText;
    while (true) {
      stage = 'intake';
      const inputDigest = digest(nextIntakeInput);
      const intakeParams = immutable({
        threadId: targetThreadId,
        input: [{type: 'text', text: nextIntakeInput}],
        ...(Object.hasOwn(plan.target, 'effort') ? {effort: plan.target.effort} : {}),
        sandboxPolicy: {type: 'readOnly'},
      });
      await record({...recordState, phase: 'starting-intake', intakeTurns,
        intakeTerminals, pendingEffect: {method: 'turn/start',
          params: intakeParams, input: nextIntakeInput, inputDigest}});
      targetTurnId = null;
      targetTurnTerminal = false;
      intake = await request('turn/start', intakeParams, 'intake:turn-start', true);
      try {
        targetTurnId = turnFrom(intake, targetThreadId, stage, transferId).id;
        if (seenIntakeTurnIds.has(targetTurnId)) {
          fail('INTAKE_TURN_REUSED', 'read-only intake reused an observed turn identity', {
            stage, transferId, reconciliationRequired: true,
          });
        }
      } catch (error) {
        nativeRequestUnresolved = true;
        unresolvedEffect = immutable({method: 'turn/start', params: intakeParams});
        targetTurnId = null;
        throw error;
      }
      seenIntakeTurnIds.add(targetTurnId);
      intakeTurnId = targetTurnId;
      intakeTurns.push(immutable({threadId: targetThreadId, turnId: intakeTurnId,
        input: nextIntakeInput, inputDigest}));
      await record({...recordState, phase: 'intake-started', intakeTurns,
        intakeTerminals, intakeTurn: {threadId: targetThreadId, turnId: intakeTurnId},
        pendingEffect: null});
      intakeTerminal = await waitTerminal(targetThreadId, intakeTurnId, 'intake:terminal');
      targetTurnTerminal = true;
      requireCompleted(intakeTerminal, targetThreadId, intakeTurnId,
        'intake:terminal', transferId);
      intakeTerminals.push(immutable({threadId: targetThreadId, turnId: intakeTurnId,
        status: terminalView(intakeTerminal).status}));

      stage = 'accepted';
      await record({...recordState, phase: 'checking-acceptance', intakeTurns,
        intakeTerminals, pendingEffect: {method: 'thread/read',
          threadId: plan.source.threadId}});
      sourceReadAccepted = await request('thread/read', {threadId: plan.source.threadId},
        'accepted:source-read');
      observeSourceThread(sourceReadAccepted, stage);
      accepted = await verifyStage('accepted', {
        connectionId: transport.connectionId,
        hostVersion: transport.hostVersion,
        source: plan.source,
        target: {threadId: targetThreadId},
        intakeTurns,
        intakeTerminals,
        intakeTurn: summarizeTurn(intake, targetThreadId),
        intakeTerminal,
        sourceRead: sourceReadAccepted,
        targetRead,
      });
      idleThread(sourceReadAccepted, stage, transferId);
      intakeVerificationSourceRefs.push(accepted.sourceRef);
      verificationSourceRefs[`accepted:${intakeTurns.length}`] = accepted.sourceRef;
      if (accepted.decision === 'allow') break;
      nextIntakeInput = accepted.additionalInput;
      await record({...recordState, phase: 'context-requested', intakeTurns,
        intakeTerminals, sourceRead: summarizeThread(sourceReadAccepted),
        contextRequest: {input: nextIntakeInput, inputDigest: digest(nextIntakeInput),
          sourceRef: accepted.sourceRef}, pendingEffect: null,
        verification: {...recordState.verification,
          accepted: [...intakeVerificationSourceRefs]}});
    }
    await record({...recordState, phase: 'target-accepted', intakeTurns,
      intakeTerminals, pendingEffect: null, sourceRead: summarizeThread(sourceReadAccepted),
      verification: {...recordState.verification,
        accepted: [...intakeVerificationSourceRefs]}});

    stage = 'writer-transfer';
    await record({...recordState, phase: 'writer-transferred', writer: 'target',
      writerThreadId: targetThreadId, sourceRecovery: 'retained', pendingEffect: null});
    writerTransferred = true;

    stage = 'continue';
    const continueVerdict = await verifyStage('continue', {
      connectionId: transport.connectionId,
      hostVersion: transport.hostVersion,
      source: plan.source,
      target: {threadId: targetThreadId},
      sourceRead: sourceReadAccepted,
      targetRead,
      recordedWriter: recordState.writer,
    });
    await record({...recordState, phase: 'continuation-authorized',
      verification: {...recordState.verification, continue: continueVerdict.sourceRef},
      pendingEffect: {method: 'turn/start', threadId: targetThreadId,
        purpose: 'first-bounded-continuation'}});

    stage = 'continuation';
    const continuationParams = immutable({
      threadId: targetThreadId,
      input: [{type: 'text', text: plan.continuation.input}],
      ...(Object.hasOwn(plan.target, 'effort') ? {effort: plan.target.effort} : {}),
      sandboxPolicy: plan.continuation.sandboxPolicy,
    });
    targetTurnId = null;
    targetTurnTerminal = false;
    const continuation = await request('turn/start', continuationParams,
      'continuation:turn-start', true);
    try {
      targetTurnId = turnFrom(continuation, targetThreadId, stage, transferId).id;
      if (seenIntakeTurnIds.has(targetTurnId)) {
        fail('CONTINUATION_TURN_REUSED', 'continuation reused an observed intake turn identity', {
          stage, transferId, reconciliationRequired: true,
        });
      }
    } catch (error) {
      nativeRequestUnresolved = true;
      unresolvedEffect = immutable({method: 'turn/start', params: continuationParams});
      targetTurnId = null;
      throw error;
    }
    await record({...recordState, phase: 'continuation-started', continuationTurn: {
      threadId: targetThreadId, turnId: targetTurnId}, pendingEffect: null});
    const continuationTerminal = await waitTerminal(targetThreadId, targetTurnId,
      'continuation:terminal');
    targetTurnTerminal = true;
    requireCompleted(continuationTerminal, targetThreadId, targetTurnId,
      'continuation:terminal', transferId);

    stage = 'continued';
    const continued = await verifyStage('continued', {
      connectionId: transport.connectionId,
      hostVersion: transport.hostVersion,
      source: plan.source,
      target: {threadId: targetThreadId},
      continuationTurn: summarizeTurn(continuation, targetThreadId),
      continuationTerminal,
      recordedWriter: recordState.writer,
    });
    await record({...recordState, phase: 'continued', pendingEffect: null,
      verification: {...recordState.verification, continued: continued.sourceRef}});

    stage = 'release';
    await record({...recordState, phase: 'checking-release', pendingEffect: {
      method: 'thread/read', threadId: plan.source.threadId,
    }});
    const releaseSourceRead = await request('thread/read', {threadId: plan.source.threadId},
      'release:source-read');
    observeSourceThread(releaseSourceRead, stage);
    const releaseTargetRead = await request('thread/read', {threadId: targetThreadId},
      'release:target-read');
    threadFrom(releaseTargetRead, targetThreadId, stage, transferId);
    const release = await verifyStage('release', {
      connectionId: transport.connectionId,
      hostVersion: transport.hostVersion,
      source: plan.source,
      target: {threadId: targetThreadId},
      sourceRead: releaseSourceRead,
      targetRead: releaseTargetRead,
      continuationTerminal,
      recordedWriter: recordState.writer,
    });
    idleThread(releaseSourceRead, stage, transferId);
    await record({...recordState, phase: 'release-authorized', pendingEffect: {
      method: 'thread/unsubscribe', threadId: plan.source.threadId,
    }, verification: {...recordState.verification, release: release.sourceRef}});
    const unsubscribe = await request('thread/unsubscribe', {threadId: plan.source.threadId},
      'release:source-unsubscribe', true);
    if (!plainObject(unsubscribe) || unsubscribe.status !== 'unsubscribed') {
      nativeRequestUnresolved = true;
      unresolvedEffect = immutable({method: 'thread/unsubscribe',
        params: {threadId: plan.source.threadId}});
      fail('UNSUBSCRIBE_OUTCOME_UNKNOWN', 'source unsubscribe lacked a positive native receipt', {
        stage: 'release:source-unsubscribe', transferId, reconciliationRequired: true,
      });
    }
    const nativeHistoryRetained = sourceEphemeral === null ? null : !sourceEphemeral;
    await record({...recordState, phase: 'source-subscription-released',
      sourceRecovery: 'retained', sourceEphemeral, nativeHistoryRetained, pendingEffect: null,
      subscriptionRelease: {threadId: plan.source.threadId, observed: true}});

    return immutable({
      status: 'handed-off',
      transferId,
      scopeRef: plan.scopeRef,
      sourceThreadId: plan.source.threadId,
      targetThreadId,
      planDigest,
      connectionId: transport.connectionId,
      hostVersion: transport.hostVersion,
      source: {
        threadId: plan.source.threadId,
        turnId: plan.source.turnId || null,
        subscriptionReleased: true,
        ephemeral: sourceEphemeral,
        nativeHistoryRetained,
        archived: false,
        deleted: false,
      },
      target: {
        threadId: targetThreadId,
        intakeTurnId,
        intakeTurnIds: intakeTurns.map((item) => item.turnId),
        continuationTurnId: continuation.turn.id,
      },
      writer: 'target',
      sourceSubscriptionReleased: true,
      sourceRecoveryRetained: true,
      sourceUnloaded: null,
      revision,
      lease,
      sourceRecovery: {
        ready: release.sourceRecoveryReady,
        nativeHistoryRetained,
        subscriptionReleased: true,
      },
      evidence: {
        recorderRevision: revision,
        verificationSourceRefs,
        intakeTurnIds: intakeTurns.map((item) => item.turnId),
        intakeTerminals,
        intakeVerificationSourceRefs,
        intakeTerminal,
        continuationTerminal,
        unsubscribe,
      },
      claimLimit: 'host-controller-bound handoff only; no autonomous or default-Desktop claim',
    });
    } catch (cause) {
      return handleFailure(cause);
    }
  }

  async function prepareProposal(rawNativeRequest) {
    if (!plan.source.turnId) {
      fail('PROPOSAL_SOURCE_TURN_REQUIRED', 'handoff proposal requires an exact active source turn', {
        stage: 'proposal-prepare', transferId,
      });
    }
    if (proposalRequest || revision !== null) {
      fail('PROPOSAL_ALREADY_PREPARED', 'handoff proposal has already been prepared', {
        stage: 'proposal-prepare', transferId, reconciliationRequired: true,
      });
    }
    try {
      stage = 'proposal-prepare';
      proposalRequest = validateProposalRequest(rawNativeRequest, plan, connectionBinding);
      const queued = immutable({
        status: 'queued',
        transferId,
        scopeRef: plan.scopeRef,
        takeoverStarted: false,
        sourceWriterRetained: true,
        message: 'Proposal recorded. Finish this source turn without further actions on the transferred work; takeover has not started and source responsibility is retained.',
      });
      proposalResponse = immutable({
        ...(proposalRequest.jsonrpc === '2.0' ? {jsonrpc: '2.0'} : {}),
        id: proposalRequest.id,
        result: {success: true, contentItems: [{type: 'inputText', text: JSON.stringify(queued)}]},
      });
      const pendingEffect = immutable({
        type: 'tool-response',
        requestId: proposalRequest.id,
        method: proposalRequest.method,
        threadId: proposalRequest.params.threadId,
        turnId: proposalRequest.params.turnId,
        callId: proposalRequest.params.callId,
        tool: proposalRequest.params.tool,
        responseDigest: digest(proposalResponse.result),
      });
      unresolvedEffect = pendingEffect;
      await begin(pendingEffect, 'proposal-preparing');
      await record({...recordState,
        phase: 'proposal-response-pending',
        pendingEffect,
        proposal: {
          connection: connectionBinding,
          nativeRequest: proposalRequest,
          argumentsDigest: digest(proposalRequest.params.arguments),
          reason: proposalRequest.params.arguments.reason,
          checkpointRef: proposalRequest.params.arguments.checkpointRef || null,
          packet,
          responseDigest: pendingEffect.responseDigest,
        },
      });
      stage = 'proposal-response-pending';

      const dispatch = async (rawDispatch) => {
        if (dispatchStarted) {
          throw new CarrierHandoffError('PROPOSAL_DISPATCH_ALREADY_USED',
            'handoff proposal dispatcher is one-shot', {
              stage: 'proposal-dispatch', transferId, reconciliationRequired: true,
              state: {pendingEffect: unresolvedEffect, lease, recorderRevision: revision},
            });
        }
        dispatchStarted = true;
        try {
          ensureWork('proposal-dispatch');
          ensureBinding('proposal-dispatch');
          let observed;
          try {
            observed = validateProposalDispatch(rawDispatch, plan, proposalRequest,
              proposalResponse, transferId);
          } catch (cause) {
            if (cause instanceof CarrierHandoffError) throw cause;
            throw new CarrierHandoffError('INVALID_PROPOSAL_DISPATCH',
              'handoff proposal dispatch evidence is invalid', {
                stage: 'proposal-dispatch', transferId, reconciliationRequired: true,
                details: {cause: errorData(cause)},
              });
          }
          await record({...recordState,
            phase: 'proposal-response-observed',
            pendingEffect: null,
            proposal: {...recordState.proposal,
              completionDigest: digest(observed.toolCompleted),
              completion: {
                method: observed.toolCompleted.method,
                threadId: observed.toolCompleted.params.threadId,
                turnId: observed.toolCompleted.params.turnId,
                callId: observed.toolCompleted.params.item.id,
                status: observed.toolCompleted.params.item.status,
                success: observed.toolCompleted.params.item.success,
              },
              sourceTerminalDigest: digest(observed.sourceTerminal),
              sourceTerminal: terminalView(observed.sourceTerminal),
              current: observed.current,
            },
          });
          unresolvedEffect = null;
          return runCore(observed.sourceTerminal, false);
        } catch (cause) {
          return handleFailure(cause);
        }
      };
      return Object.freeze({response: proposalResponse, dispatch});
    } catch (cause) {
      return handleFailure(cause);
    }
  }

  async function runProposal(nativeRequest, channel) {
    exactKeys(channel, ['subscribe', 'respond', 'current'], [], 'proposal channel');
    const callbacks = {};
    for (const key of ['subscribe', 'respond', 'current']) {
      if (typeof channel[key] !== 'function') throw new TypeError(`channel.${key} must be a function`);
      callbacks[key] = channel[key];
    }
    // Only two correlated receipts are retained. The owning receiver continues
    // pumping RPC replies and keeps the original ordered journal independently.
    let toolCompleted = null, sourceTerminal = null, fault = null, boundRequest;
    let responseStarted = false, accepting = true, unsubscribe = null;
    let wake;
    const ready = new Promise(resolve => { wake = resolve; });
    const channelError = (code, message) => new CarrierHandoffError(code, message, {
      stage: 'proposal-channel', transferId, reconciliationRequired: true,
    });
    function checkChannelCallbacks() {
      if (Object.keys(callbacks).some(key => callbacks[key] !== channel[key])) {
        bindingCertain = false;
        throw channelError('PROPOSAL_CHANNEL_CHANGED', 'proposal channel callbacks changed');
      }
      if (fault) { bindingCertain = false; throw fault; }
    }
    function checkChannel() {
      ensureBinding('proposal-channel');
      checkChannelCallbacks();
    }
    function observe(envelope) {
      if (!accepting || fault || !plainObject(envelope)) return;
      const params = envelope.params;
      if (!plainObject(params) || params.threadId !== plan.source.threadId) return;
      const tool = envelope.method === 'item/completed' &&
        params.turnId === plan.source.turnId && params.item?.id === boundRequest.params.callId;
      const terminal = envelope.method === 'turn/completed' && params.turn?.id === plan.source.turnId;
      const newTurn = envelope.method === 'turn/started' &&
        params.turn?.id !== plan.source.turnId;
      if (!tool && !terminal && !newTurn) return;
      try {
        checkChannel();
        if (envelope.connectionId !== connectionBinding.connectionId ||
            envelope.hostVersion !== connectionBinding.hostVersion) {
          throw channelError('PROPOSAL_EVENT_BINDING_CHANGED', 'proposal event connection differs');
        }
        if (!responseStarted || newTurn) {
          throw channelError('PROPOSAL_SOURCE_CHANGED', 'source events do not belong to the queued response');
        }
        const event = immutable({method: envelope.method, params});
        if (canonical(event).length > MAX_TEXT) {
          throw channelError('PROPOSAL_EVENT_TOO_LARGE', 'proposal receipt exceeds the bounded event size');
        }
        const prior = tool ? toolCompleted : sourceTerminal;
        if (prior && digest(prior) !== digest(event)) {
          throw channelError('PROPOSAL_EVENT_CONFLICT', 'conflicting completion for the same native operation');
        }
        if (tool) toolCompleted = event;
        else {
          if (!toolCompleted) {
            throw channelError('PROPOSAL_EVENT_ORDER', 'source terminal arrived before the tool receipt');
          }
          sourceTerminal = event;
        }
        if (toolCompleted && sourceTerminal) wake();
      } catch (error) {
        fault = error;
        wake();
      }
    }
    let prepared, result, failure;
    try {
      // Validate before exposing the receiver or recording a response intent.
      boundRequest = validateProposalRequest(nativeRequest, plan, connectionBinding);
      proposalChannelCheck = checkChannelCallbacks;
      // subscribe must replay the caller's ordered journal from this exact
      // request and attach live delivery without a gap (including reconnects).
      unsubscribe = Reflect.apply(callbacks.subscribe, undefined, [observe, boundRequest]);
      if (typeof unsubscribe !== 'function') {
        throw channelError('INVALID_PROPOSAL_SUBSCRIPTION', 'subscribe must return its exact synchronous release function');
      }
      checkChannel();
      prepared = await prepareProposal(boundRequest);
      checkChannel();
      responseStarted = true;
      await bounded(() => Reflect.apply(callbacks.respond, undefined,
        [prepared.response, workDeadlineMs]), workDeadlineMs, 'proposal.respond');
      checkChannel();
      await bounded(() => ready, workDeadlineMs, 'proposal.events');
      checkChannel();
      const current = await bounded(() => Reflect.apply(callbacks.current, undefined,
        [workDeadlineMs]), workDeadlineMs, 'proposal.current');
      checkChannel();
      // dispatch owns all existing receipt, CAS, semantic and recovery gates.
      result = await prepared.dispatch({toolCompleted, sourceTerminal, current});
    } catch (error) {
      // Preparation/dispatch already preserve their own failures. Channel
      // failures retain the unanswered/uncertain tool response in the same log.
      if (!prepared || dispatchStarted) failure = error;
      else {
        try { await handleFailure(error); } catch (retained) { failure = retained; }
      }
    } finally {
      accepting = false;
      proposalChannelCheck = null;
      if (unsubscribe) {
        try {
          const released = Reflect.apply(unsubscribe, undefined, []);
          if (released && typeof released.then === 'function') {
            throw new TypeError('subscription release must be synchronous');
          }
        } catch (cause) {
          failure = new CarrierHandoffError('PROPOSAL_CHANNEL_RELEASE_FAILED',
            'proposal listener release is unconfirmed; reconcile without replay', {
              stage: 'proposal-channel-release', transferId, reconciliationRequired: true,
              details: {cause: errorData(cause), priorFailure: failure ? errorData(failure) : null,
                completedResult: result || null},
              state: failure?.state || recordState || {},
            });
        }
      }
    }
    if (failure) throw failure;
    return result;
  }

  return Object.freeze({
    runImmediate: () => runCore(null, true),
    prepareProposal,
    runProposal,
  });
}

async function handoff(rawPlan, rawDependencies) {
  return createExecution(rawPlan, rawDependencies).runImmediate();
}

async function prepareHandoff(rawPlan, rawDependencies, nativeRequest) {
  return createExecution(rawPlan, rawDependencies).prepareProposal(nativeRequest);
}

async function runHandoffProposal(rawPlan, rawDependencies, nativeRequest, channel) {
  return createExecution(rawPlan, rawDependencies).runProposal(nativeRequest, channel);
}

// Resolve only an acknowledged-by-native first continuation whose callback lost
// the receipt. No native mutation method, new writer, release or storage engine;
// the host's read API may refresh its own persisted history projection.
async function reconcileContinuation(rawInput, dependencies) {
  const clock = {wall: Date.now(), monotonic: performance.now()};
  let input, transport, recorder, verify;
  try {
    input = immutable(rawInput);
    exactKeys(input, ['transferId', 'scopeRef', 'authorityRef', 'stateRef', 'deadlineMs', 'receipt'], [], 'recovery');
    for (const key of ['transferId', 'scopeRef', 'authorityRef', 'stateRef']) text(input[key], key);
    if (!Number.isSafeInteger(input.deadlineMs) || input.deadlineMs <= clock.wall ||
        input.deadlineMs - clock.wall > MAX_TIMER_MS) throw new TypeError('fresh bounded recovery deadline required');
    exactKeys(input.receipt, ['requestRef', 'request', 'response'], [], 'receipt');
    exactKeys(input.receipt.request, ['id', 'method', 'params'], ['jsonrpc'], 'receipt.request');
    exactKeys(input.receipt.response, ['id', 'result'], ['jsonrpc'], 'receipt.response');
    for (const frame of [input.receipt.request, input.receipt.response]) {
      if (Object.hasOwn(frame, 'jsonrpc') && frame.jsonrpc !== '2.0') throw new TypeError('invalid JSON-RPC version');
    }
    exactKeys(dependencies, ['transport', 'recorder', 'verify'], [], 'dependencies');
    ({transport, recorder, verify} = dependencies);
    if (!plainObject(transport) || !plainObject(recorder) || typeof transport.request !== 'function' ||
        typeof recorder.read !== 'function' || typeof recorder.compareAndSet !== 'function' ||
        typeof verify !== 'function') throw new TypeError('bound reader, CAS, transport and verifier required');
    text(transport.connectionId, 'connectionId'); text(transport.hostVersion, 'hostVersion');
  } catch (error) {
    throw new CarrierHandoffError('INVALID_INPUT', error.message);
  }
  const {transferId} = input;
  const deadline = clock.monotonic + input.deadlineMs - clock.wall;
  const binding = immutable({connectionId: transport.connectionId, hostVersion: transport.hostVersion});
  const callbacks = {request: transport.request, read: recorder.read, cas: recorder.compareAndSet, verify};
  let commitAttempted = false;
  const reject = (code, message) => fail(code, message, {stage: 'continuation-reconcile', transferId, reconciliationRequired: true});
  const checkBinding = () => {
    if (transport.connectionId !== binding.connectionId || transport.hostVersion !== binding.hostVersion ||
        transport.request !== callbacks.request || recorder.read !== callbacks.read ||
        recorder.compareAndSet !== callbacks.cas || dependencies.verify !== callbacks.verify) {
      reject('RECOVERY_BINDING_CHANGED', 'recovery callbacks or connection changed');
    }
  };
  async function call(name, args) {
    checkBinding(); before(deadline, name, transferId);
    const value = immutable(await bounded(() => Reflect.apply(callbacks[name], undefined, args), deadline, name));
    checkBinding(); before(deadline, name, transferId);
    return value;
  }
  function snapshot(value) {
    exactKeys(value, ['revision', 'state', 'lease'], [], 'recorder snapshot');
    const {state, lease, revision} = value;
    if (!Number.isSafeInteger(revision) || revision < 0 || !plainObject(state) || !plainObject(lease)) {
      reject('INVALID_RECOVERY_STATE', 'invalid recorder revision/state/lease');
    }
    const plan = validatePlan(state.plan, clock.wall, true);
    if (!plainObject(state.connection)) reject('INVALID_RECOVERY_STATE', 'original connection is unavailable');
    text(state.connection.connectionId, 'original connection'); text(state.connection.hostVersion, 'original host version');
    for (const key of ['transferId', 'scopeRef', 'authorityRef', 'stateRef']) {
      if (state[key] !== input[key] || plan[key] !== input[key]) reject('RECOVERY_BINDING_MISMATCH', 'record and current references differ');
    }
    if (state.planDigest !== digest(plan) || canonical(state.source) !== canonical(plan.source) || state.writer !== 'target' ||
        !plainObject(state.target) || state.target.threadId === plan.source.threadId ||
        state.writerThreadId !== state.target.threadId || lease.writerThreadId !== state.target.threadId ||
        lease.scopeRef !== input.scopeRef || lease.transferId !== transferId || state.sourceRecovery !== 'retained') {
      reject('INVALID_RECOVERY_STATE', 'target writer or original plan is not bound');
    }
    text(state.target.threadId, 'target thread'); text(lease.token, 'lease token');
    return plan;
  }
  const receiptDigest = digest(input.receipt);
  try {
    const current = await call('read', [transferId, input.scopeRef, deadline]);
    const plan = snapshot(current);
    const {state, lease, revision} = current;
    const targetId = state.target.threadId;
    const result = (status, observed) => immutable({status, transferId, scopeRef: input.scopeRef,
      recorderRevision: observed.revision, lease: observed.lease, writer: 'target',
      targetThreadId: targetId, continuationTurnId: observed.state.reconciliation.turn.turnId,
      sourceReleaseAllowed: false, continuationAllowed: false,
      currentNativeStateChecked: status === 'continuation-reconciled',
      claimLimit: 'Observed recorder transition only; no new execution, source release or task completion permission.'});
    const already = state.phase === 'continuation-reconciled';
    const pending = already ? state.reconciliation?.originalPendingEffect : state.pendingEffect;
    const reference = nativeRequestReference({rpcRequest: input.receipt.requestRef}, 'turn/start', state.connection || {});
    const expectedParams = {threadId: targetId, input: [{type: 'text', text: plan.continuation.input}],
      ...(Object.hasOwn(plan.target, 'effort') ? {effort: plan.target.effort} : {}), sandboxPolicy: plan.continuation.sandboxPolicy};
    if ((!already && state.phase !== 'reconciliation-required') || state.continuationTurn !== null ||
        state.failure?.code !== 'NATIVE_EFFECT_UNKNOWN' || state.failure?.stage !== 'continuation:turn-start' ||
        state.failure.targetThreadId !== targetId || state.failure.targetTurnId !== null || state.failure.targetTurnTerminal !== false ||
        !plainObject(pending) || pending.method !== 'turn/start' || !reference ||
        canonical(reference) !== canonical(pending.requestRef) || canonical(pending.params) !== canonical(expectedParams) ||
        input.receipt.request.id !== reference.requestId || input.receipt.request.method !== reference.method ||
        canonical(input.receipt.request.params) !== canonical(expectedParams) || input.receipt.response.id !== reference.requestId ||
        (!already && Object.hasOwn(state, 'reconciliation'))) {
      reject('RECOVERY_NOT_APPLICABLE', 'only the bound unknown first continuation can be reconciled');
    }
    const turnId = turnFrom(input.receipt.response.result, targetId, 'continuation-reconcile', transferId).id;
    text(turnId, 'continuation turn');
    if (!Array.isArray(state.intakeTurns) || state.intakeTurns.length === 0 ||
        state.intakeTurns.some(t => !plainObject(t) || t.threadId !== targetId || typeof t.turnId !== 'string')) {
      reject('INVALID_RECOVERY_STATE', 'intake turn identities unavailable');
    }
    const ids = [...state.intakeTurns.map(t => t.turnId), turnId];
    if (new Set(ids).size !== ids.length) reject('RECOVERY_EVIDENCE_CONFLICT', 'continuation reused an intake identity');
    if (already) {
      const saved = state.reconciliation;
      exactKeys(saved, ['kind', 'receiptDigest', 'requestRef', 'originalPendingEffect', 'originalFailure',
        'turn', 'targetReadDigest', 'verificationSourceRef', 'connection'], [], 'stored reconciliation');
      exactKeys(saved.connection, ['connectionId', 'hostVersion'], [], 'stored recovery connection');
      exactKeys(saved.turn, ['threadId', 'turnId', 'status'], [], 'stored recovery turn');
      text(saved.connection.connectionId, 'stored recovery connection');
      text(saved.connection.hostVersion, 'stored recovery version');
      if (typeof saved.targetReadDigest !== 'string' || !/^[a-f0-9]{64}$/.test(saved.targetReadDigest)) {
        reject('RECOVERY_EVIDENCE_CONFLICT', 'stored native read digest is unavailable or malformed');
      }
      if (state.pendingEffect !== null || saved.kind !== 'first-continuation' || saved.receiptDigest !== receiptDigest ||
          canonical(saved.requestRef) !== canonical(reference) || canonical(saved.originalFailure) !== canonical(state.failure) ||
          saved.turn?.threadId !== targetId || saved.turn?.turnId !== turnId || saved.turn?.status !== 'completed') {
        reject('RECOVERY_EVIDENCE_CONFLICT', 'stored reconciliation does not match this receipt');
      }
      text(saved.verificationSourceRef, 'stored verification source');
      return result('already-reconciled', current);
    }
    const targetRead = await call('request', ['thread/read', {threadId: targetId, includeTurns: true}, deadline]);
    const thread = threadFrom(targetRead, targetId, 'continuation-reconcile', transferId);
    if (!['idle', 'notLoaded'].includes(thread.status?.type) || !Array.isArray(thread.turns) ||
        thread.turns.length !== ids.length || thread.turns.some((t, i) => t.id !== ids[i] || t.status !== 'completed')) {
      reject('RECOVERY_NATIVE_MISMATCH', 'native target is active, changed or lacks the exact completed turns');
    }
    const observedTurn = thread.turns[thread.turns.length - 1];
    const inputs = Array.isArray(observedTurn.items) ? observedTurn.items.filter(i => i.type === 'userMessage') : [];
    if (inputs.length !== 1 || inputs[0].content?.length !== 1 || inputs[0].content[0]?.type !== 'text' ||
        inputs[0].content[0].text !== plan.continuation.input) {
      reject('RECOVERY_NATIVE_MISMATCH', 'native continuation input does not match the bound action');
    }
    const verdict = await call('verify', ['continuation-reconcile', immutable({input, ledger: current,
      currentConnection: binding, originalConnection: state.connection, targetRead, observedTurn}), deadline]);
    if (verdict.decision !== 'allow' || ['scopeRef', 'authorityRef', 'stateRef'].some(k => verdict[k] !== input[k]) ||
        ['sourceRecoveryReady', 'singleWriter', 'effectsVerified', 'priorAttemptQuiesced',
          'receiptVerified', 'reconciliationAuthorized'].some(k => verdict[k] !== true)) {
      reject('VERIFICATION_DENIED', 'current recovery authority, effects or writer verification denied');
    }
    text(verdict.sourceRef, 'verification source');
    const next = immutable({...state, phase: 'continuation-reconciled', pendingEffect: null,
      expectedLease: lease, observedLease: lease,
      reconciliation: {kind: 'first-continuation', receiptDigest, requestRef: reference,
        originalPendingEffect: pending, originalFailure: state.failure,
        turn: {threadId: targetId, turnId, status: 'completed'},
        targetReadDigest: digest(targetRead), verificationSourceRef: verdict.sourceRef, connection: binding}});
    checkBinding(); before(deadline, 'reconciliation commit', transferId);
    commitAttempted = true;
    const committed = await call('cas', [transferId, revision, next, lease, deadline]);
    if (!Number.isSafeInteger(committed.revision) || committed.revision <= revision || !plainObject(committed.lease) ||
        committed.lease.scopeRef !== input.scopeRef || committed.lease.transferId !== transferId ||
        committed.lease.writerThreadId !== targetId) reject('INVALID_RECORDER_LEASE', 'reconciliation changed scope/writer or returned an invalid revision');
    text(committed.lease.token, 'committed lease token');
    const confirmed = await call('read', [transferId, input.scopeRef, deadline]);
    snapshot(confirmed);
    if (confirmed.revision !== committed.revision || canonical(confirmed.lease) !== canonical(committed.lease) ||
        canonical(confirmed.state) !== canonical(next)) reject('RECORDER_READBACK_CHANGED', 'committed reconciliation was not read back exactly');
    return result('continuation-reconciled', confirmed);
  } catch (cause) {
    if (commitAttempted) throw new CarrierHandoffError('RECORDER_COMMIT_UNKNOWN', 'reconciliation commit requires a fresh read; do not replay', {
      stage: 'continuation-reconcile', transferId, reconciliationRequired: true,
      details: {receiptDigest, cause: errorData(cause)},
    });
    if (cause instanceof CarrierHandoffError) throw cause;
    throw new CarrierHandoffError('RECONCILIATION_HELD', 'recovery conditions could not be verified', {
      stage: 'continuation-reconcile', transferId, reconciliationRequired: true, details: {cause: errorData(cause)},
    });
  }
}

// Finish only the release tail of an exactly reconciled first continuation.
// No turn is started or resumed. A same-connection caller may remove its own
// source subscription once; a different controller must instead prove that the
// prior source connection is closed and can no longer dispatch.
async function finalizeReconciledHandoff(rawInput, rawDependencies) {
  const clock = {wall: Date.now(), monotonic: performance.now()};
  let input, transport, recorder, verify;
  try {
    input = immutable(rawInput);
    exactKeys(input, ['transferId', 'scopeRef', 'authorityRef', 'stateRef',
      'deadlineMs', 'expectedRevision', 'expectedLease', 'receiptDigest',
      'releaseKind'], [], 'finalization');
    for (const key of ['transferId', 'scopeRef', 'authorityRef', 'stateRef']) {
      text(input[key], `finalization.${key}`);
    }
    if (!Number.isSafeInteger(input.deadlineMs) || input.deadlineMs <= clock.wall ||
        input.deadlineMs - clock.wall > MAX_TIMER_MS) {
      throw new TypeError('fresh bounded finalization deadline required');
    }
    if (!Number.isSafeInteger(input.expectedRevision) || input.expectedRevision < 0) {
      throw new TypeError('finalization.expectedRevision must be nonnegative');
    }
    exactKeys(input.expectedLease,
      ['scopeRef', 'transferId', 'token', 'writerThreadId'], [],
      'finalization.expectedLease');
    if (input.expectedLease.scopeRef !== input.scopeRef ||
        input.expectedLease.transferId !== input.transferId) {
      throw new TypeError('finalization expected lease differs');
    }
    text(input.expectedLease.token, 'finalization.expectedLease.token');
    text(input.expectedLease.writerThreadId,
      'finalization.expectedLease.writerThreadId');
    if (typeof input.receiptDigest !== 'string' ||
        !/^[a-f0-9]{64}$/.test(input.receiptDigest)) {
      throw new TypeError('finalization.receiptDigest is invalid');
    }
    if (!['native-unsubscribe', 'prior-controller-closed'].includes(input.releaseKind)) {
      throw new TypeError('finalization.releaseKind is unsupported');
    }
    exactKeys(rawDependencies, ['transport', 'recorder', 'verify'], [], 'dependencies');
    ({transport, recorder, verify} = rawDependencies);
    if (!plainObject(transport) || typeof transport.request !== 'function' ||
        !plainObject(recorder) || typeof recorder.read !== 'function' ||
        typeof recorder.compareAndSet !== 'function' || typeof verify !== 'function') {
      throw new TypeError('bound transport, recorder and verifier are required');
    }
    text(transport.connectionId, 'transport.connectionId');
    text(transport.hostVersion, 'transport.hostVersion');
  } catch (error) {
    throw new CarrierHandoffError('INVALID_INPUT', error.message, {
      transferId: rawInput && typeof rawInput.transferId === 'string' ? rawInput.transferId : null,
    });
  }
  const deadline = clock.monotonic + input.deadlineMs - clock.wall;
  const binding = immutable({connectionId: transport.connectionId,
    hostVersion: transport.hostVersion});
  const callbacks = {request: transport.request, read: recorder.read,
    cas: recorder.compareAndSet, verify};
  let commitInFlight = false;
  const reject = (code, message, details = {}) => fail(code, message, {
    stage: 'reconciled-finalization', transferId: input.transferId,
    reconciliationRequired: true, details,
  });
  const checkBinding = () => {
    if (transport.connectionId !== binding.connectionId ||
        transport.hostVersion !== binding.hostVersion ||
        transport.request !== callbacks.request || recorder.read !== callbacks.read ||
        recorder.compareAndSet !== callbacks.cas || rawDependencies.verify !== callbacks.verify) {
      reject('FINALIZATION_BINDING_CHANGED', 'finalization callbacks or connection changed');
    }
  };
  async function call(name, args) {
    checkBinding(); before(deadline, name, input.transferId);
    const value = immutable(await bounded(
      () => Reflect.apply(callbacks[name], undefined, args), deadline, name));
    checkBinding(); before(deadline, name, input.transferId);
    return value;
  }
  function snapshot(value) {
    exactKeys(value, ['revision', 'state', 'lease'], [], 'finalization snapshot');
    if (!Number.isSafeInteger(value.revision) || value.revision < 0 ||
        !plainObject(value.state) || !plainObject(value.lease)) {
      reject('INVALID_FINALIZATION_STATE', 'invalid recorder revision, state or lease');
    }
    const plan = validatePlan(value.state.plan, clock.wall, true);
    if (value.state.transferId !== input.transferId ||
        value.state.scopeRef !== input.scopeRef ||
        value.state.authorityRef !== input.authorityRef ||
        value.state.stateRef !== input.stateRef ||
        plan.transferId !== input.transferId || plan.scopeRef !== input.scopeRef ||
        plan.authorityRef !== input.authorityRef || plan.stateRef !== input.stateRef ||
        value.state.planDigest !== digest(plan) || value.state.writer !== 'target' ||
        value.state.writerThreadId !== value.state.target?.threadId ||
        value.lease.scopeRef !== input.scopeRef ||
        value.lease.transferId !== input.transferId ||
        value.lease.writerThreadId !== value.state.target?.threadId ||
        value.state.sourceRecovery !== 'retained') {
      reject('INVALID_FINALIZATION_STATE', 'reconciled target writer or plan differs');
    }
    text(value.lease.token, 'finalization lease token');
    return plan;
  }
  async function commit(current, next, label) {
    checkBinding(); before(deadline, label, input.transferId);
    const nextSnapshot = immutable({...next, expectedLease: current.lease,
      observedLease: current.lease});
    let invoked = false;
    let committed;
    try {
      committed = immutable(await bounded(() => {
        invoked = true;
        commitInFlight = true;
        return Reflect.apply(callbacks.cas, undefined, [input.transferId,
          current.revision, nextSnapshot, current.lease, deadline]);
      }, deadline, label));
      checkBinding(); before(deadline, label, input.transferId);
    } catch (error) {
      if (!invoked) commitInFlight = false;
      throw error;
    }
    if (!Number.isSafeInteger(committed?.revision) ||
        committed.revision <= current.revision || !plainObject(committed.lease) ||
        committed.lease.scopeRef !== input.scopeRef ||
        committed.lease.transferId !== input.transferId ||
        committed.lease.writerThreadId !== current.state.target.threadId ||
        typeof committed.lease.token !== 'string' || !committed.lease.token.trim()) {
      throw new TypeError(`${label} returned an invalid recorder lease`);
    }
    const confirmed = await call('read', [input.transferId, input.scopeRef, deadline]);
    snapshot(confirmed);
    if (confirmed.revision !== committed.revision ||
        canonical(confirmed.lease) !== canonical(committed.lease) ||
        canonical(confirmed.state) !== canonical(nextSnapshot)) {
      throw new TypeError(`${label} readback differs`);
    }
    commitInFlight = false;
    return confirmed;
  }
  try {
    let current = await call('read', [input.transferId, input.scopeRef, deadline]);
    const plan = snapshot(current);
    if (current.revision !== input.expectedRevision ||
        canonical(current.lease) !== canonical(input.expectedLease)) {
      reject('FINALIZATION_BASIS_CHANGED', 'expected revision or lease changed');
    }
    const {state} = current;
    const sourceId = state.source?.threadId, targetId = state.target?.threadId;
    text(sourceId, 'finalization source thread');
    text(targetId, 'finalization target thread');
    const result = (status, observed) => immutable({status,
      transferId: input.transferId, scopeRef: input.scopeRef,
      recorderRevision: observed.revision, lease: observed.lease,
      writer: 'target', sourceThreadId: sourceId, targetThreadId: targetId,
      sourceSubscriptionReleased: true,
      subscriptionRelease: observed.state.subscriptionRelease,
      settle: {transferId: input.transferId, revision: observed.revision,
        lease: observed.lease},
      claimLimit: 'Reconciled continuation release only; no new turn, source resume, task completion or general crash-recovery claim.',
    });
    if (state.phase === 'source-subscription-released') {
      if (state.pendingEffect !== null ||
          state.reconciliation?.receiptDigest !== input.receiptDigest ||
          state.subscriptionRelease?.kind !== input.releaseKind ||
          state.subscriptionRelease?.threadId !== sourceId ||
          state.subscriptionRelease?.observed !== true ||
          typeof state.verification?.release !== 'string' ||
          !state.verification.release.trim()) {
        reject('FINALIZATION_EVIDENCE_CONFLICT',
          'stored released state differs from this finalization basis');
      }
      return result('already-finalized', current);
    }
    const initial = state.phase === 'continuation-reconciled';
    const recovering = ['release-authorized', 'release-observed',
      'release-held'].includes(state.phase);
    if ((!initial && !recovering) ||
        initial && (state.pendingEffect !== null || state.continuationTurn !== null) ||
        state.reconciliation?.kind !== 'first-continuation' ||
        state.reconciliation?.receiptDigest !== input.receiptDigest ||
        state.reconciliation?.turn?.threadId !== targetId ||
        state.reconciliation?.turn?.status !== 'completed') {
      reject('FINALIZATION_NOT_APPLICABLE',
        'only an exact reconciled first continuation can be finalized');
    }
    const originalConnection = state.connection;
    if (!plainObject(originalConnection)) {
      reject('INVALID_FINALIZATION_STATE', 'original source connection is unavailable');
    }
    const sameConnection = binding.connectionId === originalConnection.connectionId;
    if ((input.releaseKind === 'native-unsubscribe') !== sameConnection) {
      reject('FINALIZATION_RELEASE_KIND_MISMATCH',
        'release kind does not match the current/source connection relationship');
    }
    const nativeIntentClosedByNewController = recovering &&
      state.releaseIntent?.kind === 'native-unsubscribe' &&
      input.releaseKind === 'prior-controller-closed' && !sameConnection;
    const priorIntentMovedToNewController = recovering &&
      state.releaseIntent?.kind === 'prior-controller-closed' &&
      input.releaseKind === 'prior-controller-closed' &&
      state.releaseIntent?.currentConnectionId !== binding.connectionId;
    const releaseIntentMatches = !recovering ||
      (state.releaseIntent?.kind === input.releaseKind &&
        (input.releaseKind === 'prior-controller-closed' ||
          state.releaseIntent?.currentConnectionId === binding.connectionId)) ||
      (nativeIntentClosedByNewController &&
        state.releaseIntent?.currentConnectionId === originalConnection.connectionId);
    if (recovering && (!releaseIntentMatches ||
        state.releaseIntent?.threadId !== sourceId ||
        state.releaseIntent?.sourceConnectionId !== originalConnection.connectionId ||
        state.releaseIntent?.receiptDigest !== input.receiptDigest ||
        (state.releaseIntent?.kind === 'native-unsubscribe' &&
          (state.pendingEffect?.method !== 'thread/unsubscribe' ||
            state.pendingEffect?.params?.threadId !== sourceId)))) {
      reject('FINALIZATION_EVIDENCE_CONFLICT',
        'stored release intent differs from this finalization basis');
    }
    const sourceRead = await call('request', ['thread/read',
      {threadId: sourceId}, deadline]);
    const targetRead = await call('request', ['thread/read',
      {threadId: targetId, includeTurns: true}, deadline]);
    const sourceThread = threadFrom(sourceRead, sourceId,
      'reconciled-finalization:source-read', input.transferId);
    const targetThread = threadFrom(targetRead, targetId,
      'reconciled-finalization:target-read', input.transferId);
    const sourceStatus = plainObject(sourceThread.status) ? sourceThread.status.type : null;
    const targetStatus = plainObject(targetThread.status) ? targetThread.status.type : null;
    if (!['idle', 'notLoaded'].includes(sourceStatus) ||
        !['idle', 'notLoaded'].includes(targetStatus)) {
      reject('FINALIZATION_THREAD_ACTIVE', 'source or target is not quiescent');
    }
    const ids = [...state.intakeTurns.map(item => item.turnId),
      state.reconciliation.turn.turnId];
    if (!Array.isArray(targetThread.turns) || targetThread.turns.length !== ids.length ||
        targetThread.turns.some((turn, index) =>
          turn.id !== ids[index] || turn.status !== 'completed')) {
      reject('FINALIZATION_NATIVE_MISMATCH',
        'target history changed after continuation reconciliation');
    }
    const facts = immutable({input, ledger: current, plan,
      currentConnection: binding, originalConnection,
      reconciliationConnection: state.reconciliation.connection,
      releaseKind: input.releaseKind, sourceRead, targetRead,
      continuationTurn: state.reconciliation.turn});
    const verdict = await call('verify',
      ['reconciled-release', facts, deadline]);
    const common = verdict?.decision === 'allow' &&
      verdict.scopeRef === input.scopeRef &&
      verdict.authorityRef === input.authorityRef &&
      verdict.stateRef === input.stateRef &&
      typeof verdict.sourceRef === 'string' && verdict.sourceRef.trim() &&
      verdict.pauseStateVerified === true &&
      verdict.sourceRecoveryReady === true && verdict.singleWriter === true &&
      verdict.effectsVerified === true && verdict.receiptVerified === true &&
      verdict.reconciliationAuthorized === true &&
      verdict.releaseAuthorized === true;
    const branch = input.releaseKind === 'native-unsubscribe' ?
      verdict.priorAttemptQuiesced === true :
      verdict.priorControllerClosed === true &&
        verdict.priorControllerQuiesced === true &&
        verdict.sourceConnectionReleased === true &&
        verdict.subscriptionReleaseVerified === true &&
        typeof verdict.subscriptionReleaseEvidenceRef === 'string' &&
        verdict.subscriptionReleaseEvidenceRef.trim();
    const reconciliationConnectionId = state.reconciliation.connection?.connectionId;
    const reconciliationBranch = reconciliationConnectionId === binding.connectionId ||
      reconciliationConnectionId === originalConnection.connectionId ||
      verdict.reconciliationControllerClosed === true &&
        verdict.reconciliationControllerQuiesced === true &&
        typeof verdict.reconciliationControllerEvidenceRef === 'string' &&
        verdict.reconciliationControllerEvidenceRef.trim();
    const priorIntentControllerId = state.releaseIntent?.currentConnectionId;
    const releaseIntentControllerBranch = !priorIntentMovedToNewController ||
      priorIntentControllerId === originalConnection.connectionId ||
      priorIntentControllerId === reconciliationConnectionId ||
      verdict.releaseIntentControllerClosed === true &&
        verdict.releaseIntentControllerQuiesced === true &&
        typeof verdict.releaseIntentControllerEvidenceRef === 'string' &&
        verdict.releaseIntentControllerEvidenceRef.trim();
    if (!common || !branch || !reconciliationBranch ||
        !releaseIntentControllerBranch) {
      reject('VERIFICATION_DENIED',
        'current authority, effects or subscription release verification denied');
    }
    const intent = nativeIntentClosedByNewController || priorIntentMovedToNewController ? immutable({
      kind: 'prior-controller-closed', threadId: sourceId,
      sourceConnectionId: originalConnection.connectionId,
      currentConnectionId: binding.connectionId,
      receiptDigest: input.receiptDigest,
      evidenceRef: verdict.subscriptionReleaseEvidenceRef,
      originalIntentKind: state.releaseIntent.kind}) : recovering ? state.releaseIntent : immutable({
      kind: input.releaseKind, threadId: sourceId,
      sourceConnectionId: originalConnection.connectionId,
      currentConnectionId: binding.connectionId,
      receiptDigest: input.receiptDigest,
      evidenceRef: input.releaseKind === 'prior-controller-closed' ?
        verdict.subscriptionReleaseEvidenceRef : null});
    const plannedEffect = input.releaseKind === 'native-unsubscribe' ?
      {method: 'thread/unsubscribe', params: {threadId: sourceId}} : null;
    if (initial) {
      current = await commit(current, {...state,
        phase: 'release-authorized',
        continuationTurn: {threadId: targetId,
          turnId: state.reconciliation.turn.turnId},
        pendingEffect: plannedEffect,
        releaseIntent: intent,
        verification: {...state.verification,
          reconciledRelease: verdict.sourceRef}}, 'release authorization');
    }
    let nativeStatus = null;
    let releaseEvidenceRef = intent.evidenceRef;
    let releaseSourceRef = verdict.sourceRef;
    if (input.releaseKind === 'native-unsubscribe') {
      let response = current.state.releaseObservation?.response || null;
      nativeStatus = current.state.releaseObservation?.nativeStatus || null;
      if (initial) {
        try {
          response = await call('request', ['thread/unsubscribe',
            {threadId: sourceId}, deadline]);
      } catch (cause) {
        const details = {cause: errorData(cause)};
        const reference = nativeRequestReference(cause,
          'thread/unsubscribe', binding);
        if (reference) {
          details.requestRef = reference;
          const failure = {code: 'NATIVE_EFFECT_UNKNOWN',
            stage: 'reconciled-finalization:unsubscribe', nativeStatus: null,
            cause: errorData(cause), requestRef: reference};
          current = await commit(current, {...current.state,
            phase: 'release-authorized', pendingEffect: {
              ...current.state.pendingEffect, requestRef: reference}, failure},
          'unsubscribe failure evidence');
        }
          throw new CarrierHandoffError('NATIVE_EFFECT_UNKNOWN',
            'source unsubscribe outcome is unknown; do not replay', {
              stage: 'reconciled-finalization:unsubscribe',
              transferId: input.transferId, reconciliationRequired: true,
              state: {pendingEffect: current.state.pendingEffect,
                recorderRevision: current.revision, lease: current.lease},
              details,
            });
        }
        nativeStatus = response?.status;
        const recognized = ['unsubscribed', 'notSubscribed', 'notLoaded']
          .includes(nativeStatus);
        current = await commit(current, {...current.state,
          phase: recognized ? 'release-observed' : 'release-held',
          pendingEffect: current.state.pendingEffect,
          releaseObservation: {response: response || null,
            nativeStatus: nativeStatus || null},
          ...(!recognized ? {failure: {code: 'SOURCE_RELEASE_UNVERIFIED',
            stage: 'reconciled-finalization:unsubscribe',
            nativeStatus: nativeStatus || null}} : {})},
        recognized ? 'release observation' : 'release hold');
        if (!recognized) {
          reject('SOURCE_RELEASE_UNVERIFIED',
            'native unsubscribe returned no recognized current-connection status',
            {nativeStatus: nativeStatus || null,
              recorderRevision: current.revision});
        }
      }
      let observedVerdict;
      if (['unsubscribed', 'notSubscribed', 'notLoaded'].includes(nativeStatus)) {
        observedVerdict = await call('verify',
          ['reconciled-release-observed', immutable({...facts,
            ledger: current, nativeResponse: response, nativeStatus}), deadline]);
      } else {
        observedVerdict = await call('verify',
          ['reconciled-release-recover', immutable({...facts,
            ledger: current, releaseObservation: current.state.releaseObservation || null}),
          deadline]);
        nativeStatus = observedVerdict?.nativeStatus || null;
      }
      if (observedVerdict?.decision !== 'allow' ||
          observedVerdict.scopeRef !== input.scopeRef ||
          observedVerdict.authorityRef !== input.authorityRef ||
          observedVerdict.stateRef !== input.stateRef ||
          typeof observedVerdict.sourceRef !== 'string' ||
          !observedVerdict.sourceRef.trim() ||
          typeof observedVerdict.subscriptionReleaseEvidenceRef !== 'string' ||
          !observedVerdict.subscriptionReleaseEvidenceRef.trim() ||
          !['unsubscribed', 'notSubscribed', 'notLoaded'].includes(nativeStatus) ||
          observedVerdict.subscriptionReleaseVerified !== true ||
          observedVerdict.sameConnectionSubscriptionReleased !== true ||
          observedVerdict.singleWriter !== true) {
        reject('SOURCE_RELEASE_RECONCILIATION_REQUIRED',
          'native unsubscribe is pending independent release reconciliation',
          {nativeStatus: nativeStatus || null,
            recorderRevision: current.revision});
      }
      releaseEvidenceRef = observedVerdict.subscriptionReleaseEvidenceRef;
      releaseSourceRef = observedVerdict.sourceRef;
    }
    const observedSourceEphemeral = typeof sourceThread.ephemeral === 'boolean' ?
      sourceThread.ephemeral : state.sourceEphemeral;
    const subscriptionRelease = immutable({...intent, observed: true,
      nativeStatus, evidenceRef: releaseEvidenceRef,
      ...(nativeIntentClosedByNewController || priorIntentMovedToNewController ?
        {originalReleaseIntent: state.releaseIntent} : {})});
    const released = immutable({...current.state,
      phase: 'source-subscription-released', pendingEffect: null,
      sourceRecovery: 'retained', sourceEphemeral: observedSourceEphemeral,
      nativeHistoryRetained: typeof observedSourceEphemeral === 'boolean' ?
        !observedSourceEphemeral : state.nativeHistoryRetained ?? null,
      subscriptionRelease,
      sourceRead: summarizeThread(sourceRead),
      verification: {...current.state.verification,
        release: releaseSourceRef}});
    current = await commit(current, released, 'source subscription release');
    return result('finalized', current);
  } catch (cause) {
    if (commitInFlight) {
      throw new CarrierHandoffError('RECORDER_COMMIT_UNKNOWN',
        'finalization commit requires a fresh read; do not replay', {
          stage: 'reconciled-finalization', transferId: input.transferId,
          reconciliationRequired: true, details: {cause: errorData(cause)},
        });
    }
    if (cause instanceof CarrierHandoffError) throw cause;
    throw new CarrierHandoffError('FINALIZATION_HELD',
      'reconciled finalization conditions could not be verified', {
        stage: 'reconciled-finalization', transferId: input.transferId,
        reconciliationRequired: true, details: {cause: errorData(cause)},
      });
  }
}

function errorData(error) {
  if (!error || typeof error !== 'object') return {name: typeof error, message: String(error)};
  const data = {
    name: typeof error.name === 'string' ? error.name : 'Error',
    message: typeof error.message === 'string' ? error.message : String(error),
  };
  if (typeof error.code === 'string' || typeof error.code === 'number') data.code = error.code;
  return data;
}

module.exports = {HANDOFF_PROPOSAL_TOOL, prepareHandoff, runHandoffProposal, handoff,
  reconcileContinuation, finalizeReconciledHandoff, CarrierHandoffError};
