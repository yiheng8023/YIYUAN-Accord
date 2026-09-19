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

function validatePlan(raw, wallNowMs) {
  exactKeys(raw,
    ['transferId', 'scopeRef', 'authorityRef', 'stateRef', 'source', 'target', 'handoffText',
      'continuation', 'deadlineMs', 'recoveryDeadlineMs'], [], 'plan');
  exactKeys(raw.source, ['threadId'], ['turnId'], 'plan.source');
  exactKeys(raw.target, ['cwd', 'model'], ['modelProvider'], 'plan.target');
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
  text(raw.handoffText, 'plan.handoffText', MAX_TEXT);
  text(raw.continuation.input, 'plan.continuation.input', MAX_TEXT);
  if (!plainObject(raw.continuation.sandboxPolicy)) {
    throw new TypeError('plan.continuation.sandboxPolicy must be an object');
  }
  cloneData(raw.continuation.sandboxPolicy);
  for (const name of ['deadlineMs', 'recoveryDeadlineMs']) {
    if (!Number.isSafeInteger(raw[name]) || raw[name] <= wallNowMs) {
      throw new TypeError(`plan.${name} must be a future absolute millisecond deadline`);
    }
    if (raw[name] - wallNowMs > MAX_TIMER_MS) {
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

async function handoff(rawPlan, rawDependencies) {
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
  let stage = 'begin';
  const verificationSourceRefs = {};
  const evidence = {};

  const ensureWork = (name) => before(workDeadlineMs, name, transferId);
  const ensureRecovery = (name) => before(recoveryDeadlineMs, name, transferId);

  function ensureBinding(name) {
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

  async function begin() {
    ensureWork('begin');
    const initial = immutable({
      phase: 'prepared',
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
      pendingEffect: {method: 'thread/read', threadId: plan.source.threadId},
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
      if (mutating) nativeRequestUnresolved = true;
      if (cause instanceof CarrierHandoffError) throw cause;
      throw new CarrierHandoffError(mutating ? 'NATIVE_EFFECT_UNKNOWN' : 'NATIVE_READ_FAILED',
        `${effectStage} failed`, {
          stage: effectStage,
          transferId,
          reconciliationRequired: mutating || nativeMutation,
          details: {method, cause: errorData(cause)},
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

  try {
    await begin();

    stage = 'prepare';
    const sourceReadBefore = await request('thread/read', {threadId: plan.source.threadId},
      'prepare:source-read');
    threadFrom(sourceReadBefore, plan.source.threadId, stage, transferId);
    const prepared = await verifyStage('prepare', {
      connectionId: transport.connectionId,
      hostVersion: transport.hostVersion,
      source: plan.source,
      sourceRead: sourceReadBefore,
    });
    await record({...recordState, phase: 'prepared', pendingEffect: null,
      sourceRead: summarizeThread(sourceReadBefore), verification: {prepare: prepared.sourceRef}});

    let sourceTerminal = null;
    if (plan.source.turnId) {
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
    threadFrom(sourceReadAfter, plan.source.threadId, stage, transferId);
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
      threadFrom(sourceReadAccepted, plan.source.threadId, stage, transferId);
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
    threadFrom(releaseSourceRead, plan.source.threadId, stage, transferId);
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
    await record({...recordState, phase: 'source-subscription-released',
      sourceRecovery: 'native-history-retained', pendingEffect: null,
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
        nativeHistoryRetained: true,
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
        nativeHistoryRetained: true,
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
    const original = cause instanceof CarrierHandoffError ? cause :
      new CarrierHandoffError('HANDOFF_FAILED', 'carrier handoff failed', {
        stage, transferId, reconciliationRequired: nativeMutation,
        details: {cause: errorData(cause)},
      });
    const recovery = await bestEffortTargetStop();
    const reconciliationRequired = original.reconciliationRequired || nativeMutation ||
      writerTransferred || targetThreadId !== null || !recorderCertain || !bindingCertain;
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

module.exports = {handoff, CarrierHandoffError};
