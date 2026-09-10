'use strict';

// Local task evidence and a scoped continuation callback. This neither grants
// authority nor supplies the host's executor, semantic judgment or sandbox.
const fs = require('node:fs');
const path = require('node:path');
const os = require('node:os');
const crypto = require('node:crypto');
const sha = (value) => crypto.createHash('sha256').update(value).digest('hex');
const canonical = (value) => JSON.stringify(value, function (_, child) {
  return child && typeof child === 'object' && !Array.isArray(child)
    ? Object.fromEntries(Object.keys(child).sort().map((key) => [key, child[key]])) : child;
});
const samePath = (left, right) => process.platform === 'win32'
  ? left.toLowerCase() === right.toLowerCase() : left === right;
const fail = (message) => { throw new Error(message); };
const text = (value) => typeof value === 'string' && value.trim().length > 0;
const needsInput = (input) => input?.needsNativeReplay || input?.needsResumeReconciliation;

function regular(file, limit = 8 * 1024 * 1024) {
  const stat = fs.lstatSync(file);
  if (!stat.isFile() || stat.isSymbolicLink() || stat.size > limit ||
      !samePath(fs.realpathSync(file), path.resolve(file))) fail('unsafe-or-oversize-file');
  return fs.readFileSync(file);
}

function readJson(file) {
  const value = JSON.parse(regular(file, 128 * 1024).toString('utf8'));
  if (!value || typeof value !== 'object' || Array.isArray(value)) fail('invalid-state-object');
  return value;
}

function atomic(file, value) {
  const encoded = JSON.stringify(value);
  if (Buffer.byteLength(encoded) > 128 * 1024) fail('oversize-state-object');
  const temporary = `${file}.${crypto.randomUUID()}.tmp`;
  let descriptor = null;
  try {
    descriptor = fs.openSync(temporary, 'wx', 0o600);
    fs.writeFileSync(descriptor, encoded);
    fs.fsyncSync(descriptor);
    fs.closeSync(descriptor);
    descriptor = null;
    if (fs.existsSync(file)) regular(file, 128 * 1024);
    fs.renameSync(temporary, file);
  } finally {
    if (descriptor !== null) fs.closeSync(descriptor);
    if (fs.existsSync(temporary)) fs.unlinkSync(temporary);
  }
}

function location(session, cwd, create = false) {
  if (!text(session) || session.length > 200 || !path.isAbsolute(cwd || '')) fail('unbound-session');
  const root = fs.realpathSync(cwd);
  if (!fs.statSync(root).isDirectory()) fail('unbound-workspace');
  const id = sha(canonical({session, cwd: process.platform === 'win32' ? root.toLowerCase() : root}));
  const workspaceId = sha(process.platform === 'win32' ? root.toLowerCase() : root);
  const relevant = (base) => {
    if (!fs.existsSync(base)) return false;
    if (!samePath(fs.realpathSync(base), base) || fs.lstatSync(base).isSymbolicLink()) fail('unsafe-state-directory');
    return [`${id}.input.json`, `${id}.input.json.lock`, `${id}.state.json`, `${id}.lock`,
            `${id}.input-failure.json`, `${workspaceId}.workspace-input-failure.json`]
      .some((name) => fs.existsSync(path.join(base, name)));
  };
  const override = process.env.YIYUAN_ACCORD_TASK_STATE_DIR;
  let base = path.resolve(override || path.join(os.homedir(), '.yiyuan-accord', 'task-state'));
  let kind = override ? 'explicit-directory' : 'durable-user-data';
  if (!override) {
    const legacy = path.resolve(os.tmpdir(), 'yiyuan-accord-tasks');
    if (!samePath(base, legacy) && relevant(legacy)) {
      if (relevant(base)) fail('conflicting-state-locations');
      // Preserve exact-session legacy state; discovery does not migrate, merge
      // or adopt another task. Its temporary lifetime remains explicit.
      base = legacy;
      kind = 'legacy-temporary';
    }
  }
  if (create) {
    // Validate the existing ancestor before recursive creation; checking only
    // afterwards could already have written through a redirected parent.
    let ancestor = base;
    while (!fs.existsSync(ancestor) && path.dirname(ancestor) !== ancestor) ancestor = path.dirname(ancestor);
    if (!fs.statSync(ancestor).isDirectory() || fs.lstatSync(ancestor).isSymbolicLink() ||
        !samePath(fs.realpathSync(ancestor), ancestor)) fail('unsafe-state-directory');
    fs.mkdirSync(base, {recursive: true, mode: 0o700});
  }
  if (!fs.existsSync(base)) return null;
  if (!samePath(fs.realpathSync(base), base) || fs.lstatSync(base).isSymbolicLink()) fail('unsafe-state-directory');
  return {root, input: path.join(base, `${id}.input.json`),
          state: path.join(base, `${id}.state.json`), lock: path.join(base, `${id}.lock`),
          failure: path.join(base, `${id}.input-failure.json`),
          workspaceFailure: path.join(base, `${workspaceId}.workspace-input-failure.json`),
          storage: {path: base, kind}};
}

// Failure publication must not take the input lock that just failed. These
// small watermarks remain until the owning state directory is safely retired;
// deleting a shared workspace watermark could revive another session's input.
function markInputFailure(where, workspace = false) {
  atomic(workspace ? where.workspaceFailure : where.failure,
         {schema: 1, generation: crypto.randomUUID()});
}

function readInput(where) {
  const input = fs.existsSync(where.input) ? readJson(where.input) : null;
  const failures = {};
  for (const [key, file] of [['session', where.failure], ['workspace', where.workspaceFailure]]) {
    if (fs.existsSync(file)) {
      const marker = readJson(file);
      if (marker.schema !== 1 || !text(marker.generation)) fail('invalid-input-failure-watermark');
      failures[key] = marker.generation;
    }
  }
  if (!input && Object.keys(failures).length === 0) return null;
  if (canonical(input?.failures || {}) === canonical(failures)) return input;
  // The recovery token changes even if no receipt could be written. A stale
  // replay cannot acknowledge a later loss merely because the old epoch stayed.
  return {...input, epoch: sha(canonical({receiptEpoch: input?.epoch || null, failures})),
          needsNativeReplay: true, failures};
}

function relative(root, name) {
  if (!text(name) || path.isAbsolute(name) || name.split(/[\\/]/).some((part) => part === '.' || part === '..' || !part)) {
    fail('reference-must-be-workspace-relative');
  }
  const file = path.resolve(root, name);
  if (file === root || !file.startsWith(root + path.sep)) fail('reference-outside-workspace');
  // Also reject a symlink in a parent of a not-yet-created output.
  let existing = file;
  while (!fs.existsSync(existing)) {
    existing = path.dirname(existing);
  }
  if (!samePath(fs.realpathSync(existing), existing)) fail('unsafe-reference-parent');
  return file;
}

function snapshot(root, name) {
  const file = relative(root, name);
  if (!fs.existsSync(file)) return {current: {present: false}};
  const stat = fs.lstatSync(file);
  if (stat.isSymbolicLink()) fail('unsafe-reference');
  if (!stat.isFile()) fail('reference-is-not-a-file');
  const bytes = regular(file);
  return {current: {present: true, sha256: sha(bytes)}, bytes};
}

const fingerprint = (root, name) => snapshot(root, name).current;

function pointer(value, key) {
  if (key === '') return {present: true, value};
  if (!key.startsWith('/') || /~(?![01])/.test(key)) fail('invalid-json-pointer');
  for (const part of key.slice(1).split('/').map((item) => item.replace(/~1/g, '/').replace(/~0/g, '~'))) {
    if (!value || typeof value !== 'object' || !Object.hasOwn(value, part)) return {present: false};
    value = value[part];
  }
  return {present: true, value};
}

function unresolvedConditions(value) {
  if (!Array.isArray(value) || value.length > 32 ||
      value.some((item) => !text(item) || item.length > 2048) ||
      new Set(value.map((item) => item.trim())).size !== value.length) fail('invalid-unresolved-conditions');
  return value;
}

function savedUnresolved(state) {
  return unresolvedConditions(state && Object.hasOwn(state, 'unresolved') ? state.unresolved : []);
}

function inspect(where, state) {
  const unresolved = savedUnresolved(state);
  const inputs = state.inputs.map((input) => {
    const current = fingerprint(where.root, input.path);
    return {path: input.path, current, unchanged: canonical(current) === canonical(input.observed)};
  });
  const outputs = state.outputs.map((output) => {
    const {current, bytes} = snapshot(where.root, output.path);
    let matched = current.present;
    if (matched && output.sha256) matched = current.sha256 === output.sha256;
    if (matched && output.json) {
      try {
        const parsed = JSON.parse(bytes.toString('utf8'));
        matched = Object.entries(output.json).every(([key, expected]) => {
          const found = pointer(parsed, key);
          return found.present && canonical(found.value) === canonical(expected);
        });
      } catch (error) {
        if (error instanceof SyntaxError) matched = false;
        else throw error;
      }
    }
    return {path: output.path, current, matched};
  });
  // Hashes and predicates describe one read per file. Recheck after collection
  // so a producer changing an earlier file cannot pass using mixed observations.
  // This detects observed drift; it does not lock external writers or provide a
  // transactional workspace snapshot. Check inputs last, after output reads.
  for (const [items, flag] of [[outputs, 'matched'], [inputs, 'unchanged']]) {
    for (const item of items) {
      item.stable = canonical(fingerprint(where.root, item.path)) === canonical(item.current);
      item[flag] = item[flag] && item.stable;
    }
  }
  return {status: inputs.some((item) => !item.unchanged) ? 'stale-inputs'
    : outputs.some((item) => !item.matched) ? 'incomplete'
      : unresolved.length ? 'unresolved' : 'verified-local', inputs, outputs, unresolved};
}

// Inspection failures are diagnostics for status, pause and explicit cancellation.
// Binding and successful completion still require strict inspection; this never
// upgrades an unreadable result or relaxes state/input concurrency checks.
function inspectDiagnostic(where, state) {
  try { return inspect(where, state); }
  catch (error) {
    return {status: 'inspection-unavailable', error: String(error.code || error.message).slice(0, 512)};
  }
}

function locked(where, callback, wait = false, retainOnFailure = false) {
  let fd;
  let keepLock = false;
  const deadline = Date.now() + 500;
  while (fd === undefined) {
    try { fd = fs.openSync(where.lock, 'wx', 0o600); }
    catch (error) {
      if (!wait || error.code !== 'EEXIST' || Date.now() >= deadline) throw error;
      Atomics.wait(new Int32Array(new SharedArrayBuffer(4)), 0, 0, 10);
    }
  }
  try {
    fs.writeSync(fd, JSON.stringify({pid: process.pid}));
    return callback();
  } catch (error) {
    keepLock = retainOnFailure && error.inputPublicationFailed === true;
    throw error;
  } finally {
    fs.closeSync(fd);
    if (!keepLock) fs.unlinkSync(where.lock);
  }
}

// Only short receipt/state publication sections hold this lock. Expensive file
// inspection never delays input invalidation. Lock order is state then input;
// native input handling never takes the state lock.
const inputLocked = (where, callback, retainOnFailure = false) =>
  locked({...where, lock: where.input + '.lock'}, callback, true, retainOnFailure);
function publishInput(where, input) {
  try { atomic(where.input, input); }
  catch (error) { error.inputPublicationFailed = true; throw error; }
}
function currentEpoch(where, epoch) {
  const input = readInput(where);
  if (input?.epoch !== epoch) fail('latest-user-input-not-reconciled');
  return input;
}

function retireFiles(where, epoch, prior = null) {
  return inputLocked(where, () => {
    const input = currentEpoch(where, epoch);
    const receipt = fs.existsSync(where.input) ? readJson(where.input) : null;
    const files = [[where.state, prior], [where.input, receipt]].filter(([, value]) => value !== null);
    try {
      for (const [file] of files) fs.unlinkSync(file);
      // Input failures publish outside this lock. Keep the recovery context if
      // one arrives during deletion; an acknowledged old watermark is harmless.
      if (canonical(readInput(where)?.failures || {}) !== canonical(input.failures || {})) {
        fail('latest-user-input-not-reconciled');
      }
    } catch (error) {
      // Both locks are still held; restore only our missing checkpoint files,
      // never erase failure watermarks. Storage failure still requires a caller.
      for (const [file, value] of files) if (!fs.existsSync(file)) atomic(file, value);
      throw error;
    }
  });
}

// Consume only a caller-owned connection's structured notification envelopes.
// No transcript text, host database access, filesystem state or model request.
function observeContext(request, now = Date.now()) {
  const b = request.binding;
  const integer = (v) => Number.isSafeInteger(v) && v >= 0;
  const result = {state: 'unknown', conditions: null, observationId: null, usageEvent: null,
    observedAtMs: null, validUntilMs: null, windowTokens: null, occupancy: null,
    efficiency: null, integrity: 'unknown', sourceReleaseAllowed: false};
  const unknown = (reason) => ({...result, reason});
  if (!b || !['connectionId', 'threadId', 'hostVersion', 'model'].every((k) => text(b[k])) ||
      !text(request.turnId) || !integer(request.maxAgeMs) || request.maxAgeMs === 0) return unknown('unbound-connection');
  if (request.connected !== true) return unknown('connection-not-live');
  if (!Array.isArray(request.events)) return unknown('notification-stream-unavailable');
  let turn = null, model = b.model, generation = sha(canonical(b)), usage = null, observed = null;
  let active = false, compacting = false, lastTime = -1;
  const invalidate = (kind, identity) => {
    generation = sha(canonical({generation, kind, identity})); usage = null; observed = null;
  };
  for (const [sequence, envelope] of request.events.entries()) {
    const event = envelope?.event, at = envelope?.receivedAtMs;
    if (!integer(at) || at < lastTime || at > now || !event || typeof event !== 'object') return unknown('invalid-notification-order');
    lastTime = at;
    const p = event.params;
    if (!p || p.threadId !== b.threadId) continue;
    if (event.method === 'turn/started') {
      if (!text(p.turn?.id)) return unknown('invalid-turn-start');
      turn = p.turn.id; active = true; compacting = false;
      invalidate('turn-start', {turn, sequence});
    } else if (event.method === 'turn/completed' && p.turn?.id === turn) {
      active = false; invalidate('turn-completed', {turn, sequence});
    } else if (active && p.turnId === turn) {
      if (event.method === 'model/rerouted') {
        if (!text(p.toModel)) return unknown('unknown-rerouted-model');
        model = p.toModel; invalidate('model-rerouted', {model, sequence});
      } else if (['item/started', 'item/completed'].includes(event.method) && p.item?.type === 'contextCompaction') {
        compacting = event.method === 'item/started';
        invalidate(event.method, {item: p.item.id, sequence});
      } else if (event.method === 'thread/compacted') {
        invalidate('legacy-compaction-notification', sequence);
      } else if (event.method === 'thread/tokenUsage/updated' && !compacting) {
        const window = p.tokenUsage?.modelContextWindow;
        // Do not retain an earlier known capacity after a newer unknown value.
        if (!integer(window) || window === 0) { usage = null; observed = null; continue; }
        usage = {method: event.method, params: {threadId: p.threadId, turnId: p.turnId,
          tokenUsage: {modelContextWindow: window}}};
        observed = {at, sequence};
      }
    }
  }
  if (!active || turn !== request.turnId) return unknown('current-turn-not-observed-active');
  result.conditions = {threadId: b.threadId, turnId: turn, hostVersion: b.hostVersion,
    model, contextGeneration: generation};
  if (compacting || !usage) return unknown('fresh-post-change-usage-unavailable');
  if (!integer(observed.at + request.maxAgeMs) || now >= observed.at + request.maxAgeMs) return unknown('usage-observation-expired');
  return {...result, state: 'window-observed', reason: 'native-capacity-only-not-occupancy-or-quality',
    observationId: sha(canonical({generation, observed, usage})), usageEvent: usage,
    observedAtMs: observed.at, validUntilMs: observed.at + request.maxAgeMs,
    windowTokens: usage.params.tokenUsage.modelContextWindow};
}

// Read-only, caller-bound planning evidence. Native usage is not live occupancy;
// a forecast cannot authorize a transfer, clear a pause or trigger host actions.
function assessContext(request, prior, input, now = Date.now()) {
  const result = {decision: 'unknown', sourceReleaseAllowed: false,
    scope: 'conditional-context-budget-only', reasons: [], windowTokens: null,
    remainingAfterReserves: null, efficiencyCeilingTokens: null};
  const stop = (decision, reason) => ({...result, decision, reasons: [reason]});
  if (request.epoch !== input.epoch || request.expectedRevision !== (prior?.revision || 0)) {
    return stop('reassess', 'task-revision-or-input-conflict');
  }
  if (prior?.mode === 'paused' || input.interrupted) return stop('paused', 'preserve-pause-or-interruption');
  if (needsInput(input) || prior && prior.epoch !== input.epoch) return stop('reassess', 'reconcile-current-input-first');
  const scope = request.conditions;
  const fields = ['threadId', 'turnId', 'hostVersion', 'model', 'contextGeneration'];
  if (!scope || !fields.every((key) => text(scope[key])) || Object.keys(scope).length !== fields.length) {
    return stop('unknown', 'current-host-conditions-missing');
  }
  const assessment = request.assessment;
  if (!assessment || canonical(assessment.conditions) !== canonical(scope) || assessment.epoch !== input.epoch) {
    return stop('reassess', 'assessment-binding-missing-or-changed');
  }
  if (Object.hasOwn(request, 'signals')) {
    const current = observeContext(request.signals, now);
    if (current.state !== 'window-observed' || current.observationId !== assessment.observationId ||
        canonical(current.conditions) !== canonical(scope) ||
        canonical(current.usageEvent) !== canonical(assessment.usageEvent)) {
      return stop('reassess', 'native-observation-changed-or-unavailable');
    }
  }
  if (!Number.isSafeInteger(assessment.observedAtMs) || !Number.isSafeInteger(assessment.validUntilMs) ||
      assessment.observedAtMs > now || assessment.validUntilMs <= now ||
      assessment.validUntilMs <= assessment.observedAtMs) return stop('reassess', 'assessment-expired-or-invalid-time');
  if (!text(assessment.sourceRef)) return stop('unknown', 'assessment-source-missing');
  if (assessment.integrity === 'degraded') return stop('reassess', 'resolve-observed-context-loss-or-drift');
  if (assessment.integrity !== 'verified') return stop('unknown', 'inheritance-integrity-unknown');
  const native = assessment.usageEvent;
  if (native?.method !== 'thread/tokenUsage/updated' || native.params?.threadId !== scope.threadId ||
      native.params?.turnId !== scope.turnId) return stop('unknown', 'matching-native-usage-unavailable');
  const count = (n) => Number.isSafeInteger(n) && n >= 0;
  const window = native.params.tokenUsage?.modelContextWindow;
  if (!count(window) || window === 0) return stop('unknown', 'native-window-unknown');
  result.windowTokens = window;
  // last/total, cached tokens and compaction counts cannot fill these estimates.
  const estimate = assessment.estimates;
  const quantities = ['contextUpperBoundTokens', 'nextWorkTokens', 'handoffTokens', 'recoveryTokens', 'safetyMarginTokens'];
  if (!estimate || !text(estimate.sourceRef) || !quantities.every((key) => count(estimate[key])) ||
      estimate.handoffTokens === 0 || estimate.recoveryTokens === 0 || estimate.safetyMarginTokens === 0) {
    return stop('unknown', 'sourced-context-and-work-transfer-recovery-estimates-required');
  }
  const efficiency = estimate.efficiencyCeilingTokens;
  if (efficiency != null && (!count(efficiency) || efficiency === 0 || !text(estimate.efficiencySourceRef))) {
    return stop('unknown', 'efficiency-range-not-evidenced');
  }
  const limit = efficiency == null ? window : Math.min(window, efficiency);
  result.efficiencyCeilingTokens = efficiency ?? null;
  const reserve = estimate.contextUpperBoundTokens + estimate.handoffTokens + estimate.recoveryTokens + estimate.safetyMarginTokens;
  if (!Number.isSafeInteger(reserve + estimate.nextWorkTokens)) return stop('unknown', 'forecast-overflow');
  result.remainingAfterReserves = limit - reserve;
  if (result.remainingAfterReserves <= 0) return stop('preserve-recovery', 'transfer-reserve-already-at-risk');
  if (estimate.nextWorkTokens >= result.remainingAfterReserves) return stop('prepare-handoff', 'next-span-would-consume-transfer-reserve');
  if (efficiency == null) return stop('unknown', 'hard-capacity-fit-does-not-establish-efficient-range');
  return stop('continue-bounded', 'forecast-fits-sourced-range-recheck-before-next-span');
}

function binding(request, where, prior, currentInput) {
  if (!currentInput || request.epoch !== currentInput.epoch) fail('latest-user-input-not-reconciled');
  if (currentInput.interrupted) fail('interrupted-task-needs-new-user-input');
  if (currentInput.needsNativeReplay) fail('input-receipt-needs-native-replay');
  if (currentInput.needsResumeReconciliation) fail('resumed-task-needs-native-input-reconciliation');
  if (request.expectedRevision !== (prior?.revision || 0)) fail('task-revision-conflict');
  if (!text(request.result) || !text(request.nextAction) || typeof request.canContinue !== 'boolean' ||
      !Array.isArray(request.inputs) || !Array.isArray(request.outputs) || request.outputs.length === 0 ||
      request.inputs.length + request.outputs.length > 100) fail('incomplete-task-binding');
  const resuming = Object.hasOwn(request, 'resumeReason');
  if (resuming && (prior?.mode !== 'paused' || !text(request.resumeReason) || request.resumeReason.length > 2048)) {
    fail('resume-needs-paused-task-and-explicit-reason');
  }
  // Reconciliation and revised predicates do not lift a user pause. The caller
  // must establish actual authority before explicitly disposing of that pause.
  const paused = prior?.mode === 'paused' && !resuming;
  const inherited = savedUnresolved(prior);
  const unresolved = Object.hasOwn(request, 'unresolved') ? unresolvedConditions(request.unresolved) : inherited;
  if (inherited.some((item) => !unresolved.includes(item)) && !text(request.revisionReason)) {
    fail('changed-unresolved-conditions-need-reason');
  }
  const names = new Set();
  const outputs = request.outputs.map((output) => {
    const key = typeof output?.path === 'string' && process.platform === 'win32'
      ? output.path.replace(/\\/g, '/').toLowerCase() : output?.path;
    if (!output || !text(output.path) || names.has(key) ||
        Object.keys(output).some((key) => !['path', 'sha256', 'json'].includes(key))) fail('invalid-output-check');
    names.add(key);
    relative(where.root, output.path);
    if (Object.hasOwn(output, 'sha256') && !/^[a-f0-9]{64}$/.test(output.sha256)) fail('invalid-output-hash');
    if (Object.hasOwn(output, 'json') && (!output.json || typeof output.json !== 'object' || Array.isArray(output.json))) {
      fail('invalid-output-json-check');
    }
    for (const key of Object.keys(output.json || {})) pointer({}, key);
    return output;
  });
  if (prior && canonical(prior.outputs) !== canonical(outputs) && !text(request.revisionReason)) {
    fail('changed-output-contract-needs-reason');
  }
  const inputs = request.inputs.map((name) => {
    const key = typeof name === 'string' && process.platform === 'win32' ? name.replace(/\\/g, '/').toLowerCase() : name;
    if (names.has(key)) fail('duplicate-or-overlapping-reference');
    names.add(key);
    const observed = fingerprint(where.root, name);
    if (!observed.present) fail('input-unavailable');
    return {path: name, observed};
  });
  return {schema: 1, session: request.session_id, cwd: where.root, epoch: currentInput.epoch,
    revision: (prior?.revision || 0) + 1, mode: paused ? 'paused' : 'active', result: request.result,
    reason: paused ? prior.reason : null, resumeReason: resuming ? request.resumeReason : null,
    inputs, outputs, unresolved, nextAction: request.nextAction, canContinue: request.canContinue,
    revisionReason: request.revisionReason || null,
    lastBlock: prior?.epoch === currentInput.epoch ? prior.lastBlock : null};
}

function operate(request) {
  const where = location(request.session_id, request.cwd);
  if (where && request.op === 'recover-lock') {
    if (!['state', 'input'].includes(request.lock || 'state')) fail('unknown-lock-kind');
    const inputRecovery = request.lock === 'input';
    const file = inputRecovery ? where.input + '.lock' : where.lock;
    const recover = () => {
    const original = regular(file, 1024);
    const owner = JSON.parse(original.toString('utf8'));
    if (!Number.isSafeInteger(owner.pid) || owner.pid <= 0) fail('unknown-lock-owner');
    try { process.kill(owner.pid, 0); fail('lock-owner-still-running'); }
    catch (error) { if (error.code !== 'ESRCH') throw error; }
    if (!regular(file, 1024).equals(original)) fail('lock-owner-changed');
    // A failed native input Hook can be nonblocking: an old receipt is no
    // longer evidence that the latest input was captured. Invalidate it before
    // releasing the dead input lock; a surviving caller must replay the actual
    // current native event. Do not invent a receipt when none ever existed.
    if (inputRecovery && fs.existsSync(where.input)) {
      atomic(where.input, {...readJson(where.input), epoch: crypto.randomUUID(), needsNativeReplay: true});
    }
    fs.unlinkSync(file);
    return {recovered: true, scope: inputRecovery ? 'dead-input-lock-and-receipt-invalidation'
      : 'dead-owner-checkpoint-lock-only', needsNativeReplay: inputRecovery};
    };
    return inputRecovery ? locked(where, recover) : recover();
  }
  if (!where) fail('native-user-input-receipt-missing');
  return locked(where, () => {
    const currentInput = inputLocked(where, () => readInput(where));
    if (!currentInput) fail('native-user-input-receipt-missing');
    const prior = fs.existsSync(where.state) ? readJson(where.state) : null;
    if (request.op === 'assess-context') return assessContext(request, prior, currentInput);
    if (request.op === 'status') return {epoch: currentInput.epoch, revision: prior?.revision || 0,
      storage: where.storage,
      inputSource: currentInput.inputSource || 'unspecified-legacy-receipt',
      hostObservation: currentInput.hostObservation || null,
      hostObservationCurrent: Boolean(currentInput.hostObservation) && !needsInput(currentInput) && !currentInput.interrupted,
      needsNativeReplay: currentInput.needsNativeReplay === true,
      needsResumeReconciliation: currentInput.needsResumeReconciliation === true,
      mode: prior?.mode || 'unbound', currentInputReconciled: !needsInput(currentInput) && prior?.epoch === currentInput.epoch,
      checkpoint: prior ? {epoch: prior.epoch, result: prior.result, inputs: prior.inputs, outputs: prior.outputs,
        nextAction: prior.nextAction, canContinue: prior.canContinue, unresolved: savedUnresolved(prior),
        revisionReason: prior.revisionReason, reason: prior.reason || null, resumeReason: prior.resumeReason || null} : null,
      inspection: prior ? inspectDiagnostic(where, prior) : null};
    if (request.op === 'bind') {
      const state = binding(request, where, prior, currentInput);
      const inspection = inspect(where, state);
      return inputLocked(where, () => {
        currentEpoch(where, currentInput.epoch);
        atomic(where.state, state);
        return {revision: state.revision, mode: state.mode, inspection};
      });
    }
    if (request.op === 'retire' && !prior) {
      if (currentInput.needsNativeReplay) fail('input-receipt-needs-native-replay');
      if (currentInput.needsResumeReconciliation) fail('resumed-task-needs-native-input-reconciliation');
      if (request.expectedRevision !== 0 || request.epoch !== currentInput.epoch || !text(request.reason)) {
        fail('unbound-retirement-needs-current-receipt-and-reason');
      }
      retireFiles(where, currentInput.epoch);
      return {retired: true, scope: 'unbound-input-receipt-only', inspection: null};
    }
    if (!prior || request.expectedRevision !== prior.revision || request.epoch !== currentInput.epoch) {
      fail('task-revision-or-input-conflict');
    }
    if (request.op === 'pause') {
      if (!text(request.reason)) fail('pause-reason-required');
      const pending = inspectDiagnostic(where, prior);
      return inputLocked(where, () => {
        currentEpoch(where, currentInput.epoch);
        atomic(where.state, {...prior, revision: prior.revision + 1, mode: 'paused', reason: request.reason});
        return {mode: 'paused', revision: prior.revision + 1, pending};
      });
    }
    if (request.op === 'retire') {
      if (currentInput.needsNativeReplay && request.disposition !== 'user-cancelled') fail('input-receipt-needs-native-replay');
      if (prior.epoch !== currentInput.epoch && request.disposition !== 'user-cancelled') fail('latest-user-input-not-reconciled');
      if (prior.mode === 'paused' && request.disposition !== 'user-cancelled') fail('paused-task-cannot-retire');
      const result = request.disposition === 'user-cancelled'
        ? inspectDiagnostic(where, prior) : inspect(where, prior);
      if (result.status !== 'verified-local' && request.disposition !== 'user-cancelled') fail('unmet-output-cannot-retire');
      if (request.disposition === 'user-cancelled' && !text(request.reason)) fail('cancellation-reason-required');
      retireFiles(where, currentInput.epoch, prior);
      return {retired: true, scope: 'task-checkpoint-files-only', inspection: result};
    }
    fail('unknown-operation');
  });
}

function observeNativeHost(event, previous) {
  // These are documented common Codex Hook fields, not a scan of user config.
  // Unknown/custom identifiers are data; no model or permission enum is routed here.
  const value = (raw) => typeof raw === 'string' && raw.length <= 256 &&
    /^[A-Za-z0-9][A-Za-z0-9._:/-]*$/.test(raw) ? raw : null;
  const values = {model: value(event.model), permissionMode: value(event.permission_mode)};
  const usable = previous?.hostObservation && !needsInput(previous) && !previous.interrupted;
  const changes = [];
  for (const field of Object.keys(values)) {
    const before = usable ? value(previous.hostObservation.values?.[field]) : null;
    const after = values[field];
    if (before !== after) changes.push({field, previous: before, current: after,
      kind: before === null ? 'available' : after === null ? 'unavailable' : 'changed'});
  }
  return {schema: 'yiyuan-accord-native-host-observation/v1', event: 'UserPromptSubmit',
    turnId: value(event.turn_id), comparison: usable ? 'previous-input-receipt' : 'no-current-prior-observation',
    values, changes, sourceRefs: {model: 'UserPromptSubmit.model', permissionMode: 'UserPromptSubmit.permission_mode'},
    scope: 'reported-fields-at-input-only; other-settings-and-mid-turn-state-unknown; no-user-intent-or-collaboration-mode-inference'};
}

function hint(event, where, currentInput, prior = null) {
  const skill = path.join(__dirname, '..', 'skills', 'deliver-demand-driven-outcome', 'SKILL.md');
  return {hookSpecificOutput: {hookEventName: event.hook_event_name, additionalContext:
    'Accord task entry: apply these duties directly; loading a Skill is not a prerequisite. ' +
    'The user may only express an idea and may not know feasibility or technical operations. ' +
    'For authorized work, assess feasibility, inspect current facts, research uncertain facts and compare suitable capabilities when it can improve the route. ' +
    'When model or subagent selection matters, discover current account and dispatch-path support, honor user restrictions, and match task needs; do not hardcode model names, versions, tiers or effort ladders. Recheck material availability changes and actual execution. ' +
    'Own execution through the verified result; do not hand discoverable mechanics or documentation reading to the user. ' +
    'Answer side questions and incorporate corrections while preserving the unfinished goal. ' +
    'After a tool failure, inspect actual post-state, change the method when warranted, and continue safe work without a reminder. ' +
    'Before ending, check consequential output claims against inspected source facts, not just shape or keyword checks. Missing operational facts remain unresolved; do not invent them or mark dependent work complete. Reconcile remaining work, continuity needs and owned resources; verify attributable cleanup. ' +
    'Use supported host state, continuation and resource controls; a stopped turn is not evidence of completion. Before context renewal can omit history, save recoverable goal, authority, pauses and unfinished work; verify restoration before resuming effects. ' +
    'For needed handoff, quiesce source writes but retain recovery until the exact target accepts the reconciled goal, authority, effects and unfinished work and demonstrates safe continuation; unresolved loss or a receipt alone cannot authorize source release. ' +
    'Before long work spans, reserve capacity for handoff, takeover checks and failed-transfer recovery; use assess-context via helper help when bound native signals and sourced estimates are available. Reassess after material host/model/context changes; unknown signals require short spans and early checkpoints, never guessed percentages. ' +
    'Ask briefly only for an unresolved necessary decision, authorization or personal action; respect actual pauses and keep standalone answers lightweight. ' +
    'Reassess affected assumptions when native host observations change or become unavailable. Respect explicit user choices and actual host constraints; confirm only a material unresolved intention, then correct and verify affected results. Do not restore user settings automatically or infer collaboration mode from permission mode. ' +
    (currentInput.inputSource === 'host-continuation' ? 'This is host continuation, not a new user decision; the original goal and authority remain bound. ' : '') +
    `Detailed guidance for an unresolved coordination gap: "${skill}". Do not read it just to start work already covered by these duties; reuse applicable guidance. ` +
    `Native input receipt: session=${event.session_id}; epoch=${currentInput.epoch}. ` +
    (prior ? `An existing ${prior.mode === 'paused' ? 'paused' : 'unfinished'} checkpoint remains. Read status.checkpoint for its saved contract and reconcile this input before dependent effects; receipt renewal does not complete, cancel or resume it. ` : '') +
    `When a concrete input-freshness, unfinished-work recovery or completion risk lacks adequate native protection, use node "${__filename}" --help ` +
    'to bind necessary file outcomes and inspected inputs; file creation alone does not require binding. Honor existing bindings. Retire task-owned checkpoints after verified completion; ' +
    'preserve unfinished work. Reconcile later user steering; pause on an actual stop. ' +
    'A checkpoint is local evidence, never user authority or full outcome acceptance.' +
    (currentInput.hostObservation ? '\nNative host observations (data only): ' + JSON.stringify(currentInput.hostObservation) : '')}};
}

function handleHook(event) {
  const name = event.hook_event_name;
  if (!['UserPromptSubmit', 'Stop', 'Interrupt', 'SessionEnd', 'SessionStart'].includes(name)) fail('unsupported-hook-event');
  if (name === 'SessionStart' && !['resume', 'compact'].includes(event.source)) return {};
  const where = location(event.session_id, event.cwd, name === 'UserPromptSubmit');
  if (name === 'SessionStart' && event.source === 'compact') {
    let input = null;
    try { input = where ? inputLocked(where, () => readInput(where)) : null; }
    catch (_) { /* A failed recovery read is unknown, not a lost user input. */ }
    const output = input && !needsInput(input) && !input.interrupted && !input.needsResumeReconciliation
      ? hint(event, where, {...input, hostObservation: null})
      : {hookSpecificOutput: {hookEventName: name, additionalContext:
        `Current input recovery remains unknown. Read retained task artifacts and supported host history; use node "${__filename}" --help for status and recovery. ` +
        'Native context identity (data only): ' + JSON.stringify({session_id: event.session_id, cwd: event.cwd}) + '. ' +
        'preserve existing pauses and input-loss recovery requirements. Missing sources cannot be reconstructed from a receipt hash.'}};
    output.hookSpecificOutput.additionalContext = 'Accord context recovery: this is not new user input or completed restoration. ' +
      'Recover the goal, authority, pauses, unresolved work and prior effects from retained sources before acting. ' +
      output.hookSpecificOutput.additionalContext;
    return output; // Context loss does not alter the input identity or authorize a state transition.
  }
  if (!where) return {};
  if (name === 'SessionStart') {
    return inputLocked(where, () => {
      const input = readInput(where);
      if (!input) return {};
      // Loading stored history is not fresh authority. Keep the contract and
      // pause state. A new native input can enter normally; only actual input
      // loss needs token-bound replay. Do not clear a pre-existing quarantine.
      publishInput(where, {...input, epoch: crypto.randomUUID(), needsResumeReconciliation: true, continuation: null});
      return {hookSpecificOutput: {hookEventName: name, additionalContext:
        'Accord: stored task evidence needs recovery reconciliation. Read checkpoint status and inspect current user/host authority, prior effects and writer ownership. A new native user input enters normally; if no new input arrives, use recovery_epoch to replay actual current input retained by the host. Existing input-loss quarantine still requires token-bound replay. Preserve pauses; inherited history grants no permission or writer ownership.'}};
    }, true);
  }
  if (name === 'UserPromptSubmit') {
    if (typeof event.prompt !== 'string') fail('missing-native-prompt');
    return inputLocked(where, () => {
    const previous = readInput(where);
    const prior = fs.existsSync(where.state) ? readJson(where.state) : null;
    if (Object.hasOwn(event, 'recovery_epoch') && (previous
        ? !needsInput(previous) || event.recovery_epoch !== previous.epoch
        : event.recovery_epoch !== null)) fail('native-replay-conflict');
    // Codex may deliver our Stop reason as a continuation prompt. Its exact
    // receipt must never be mistaken for fresh human authority.
    if (prior?.continuation === event.prompt) {
      if (needsInput(previous) || prior.epoch !== previous?.epoch) return {};
      const hostObservation = observeNativeHost(event, previous);
      const changed = canonical(hostObservation.values) !== canonical(previous.hostObservation?.values || {model: null, permissionMode: null});
      // Condition drift obsoletes the old continuation decision. Preserve the
      // original prompt identity: a host callback cannot create user authority.
      const refreshed = {...previous, hostObservation, inputSource: 'host-continuation',
        ...(changed ? {epoch: crypto.randomUUID(), continuation: null} : {})};
      publishInput(where, refreshed);
      return hint(event, where, refreshed, prior);
    }
    if (previous?.needsNativeReplay && !Object.hasOwn(event, 'recovery_epoch')) fail('input-receipt-needs-native-replay');
    const input = {schema: 1, epoch: crypto.randomUUID(), promptSha256: sha(event.prompt),
      turnId: event.turn_id || null, continuation: null, failures: previous?.failures || {},
      inputSource: 'native-input-event', hostObservation: observeNativeHost(event, previous)};
    publishInput(where, input);
    return hint(event, where, input, prior);
    }, true); // Preserve a failed publication as a recoverable lock, not stale success.
  }
  if (!fs.existsSync(where.input)) {
    if (name === 'Interrupt' && readInput(where)?.needsNativeReplay) fail('input-receipt-needs-native-replay');
    return {};
  }
  if (name === 'Interrupt') {
    return inputLocked(where, () => {
    const input = readInput(where);
    publishInput(where, {...input, epoch: crypto.randomUUID(), interrupted: true, continuation: null});
    return {};
    }, true);
  }
  return locked(where, () => {
    const input = inputLocked(where, () => readInput(where));
    const state = fs.existsSync(where.state) ? readJson(where.state) : null;
    if (name === 'SessionEnd') {
      if (!state) inputLocked(where, () => {
        if (!needsInput(input) && readInput(where)?.epoch === input.epoch) fs.unlinkSync(where.input);
      });
      return {}; // Keep unfinished work for an explicitly bound resume/recovery.
    }
    if (!state || state.mode !== 'active' || !state.canContinue || input.interrupted || needsInput(input) ||
        state.epoch !== input.epoch) return {};
    const result = inspect(where, state);
    if (result.status === 'verified-local') return {};
    const key = sha(canonical(result));
    if (state.lastBlock === key) return {systemMessage:
      'Accord: required local results remain unmet with unchanged observations. Reassess the method or report the actual blocker; no further automatic retry was requested.'};
    const reason = `Accord continuation ${crypto.randomUUID()}: ${result.status}. ` +
      `Recheck the bound task with ${__filename}; then ${state.nextAction}. ` +
      'Reconcile stale inputs before dependent effects. This callback grants no new authority; honor user changes or stop.';
    return inputLocked(where, () => {
      if (readInput(where)?.epoch !== input.epoch) return {};
      atomic(where.state, {...state, lastBlock: key, continuation: reason});
      if (readInput(where)?.epoch !== input.epoch) return {};
      return {decision: 'block', reason};
    });
  });
}

function hook(event) {
  try { return handleHook(event); }
  catch (error) {
    // An unsuccessful replay is not another native input. It cannot advance
    // the token and invalidate the correctly selected current replay.
    if (['UserPromptSubmit', 'Interrupt', 'SessionStart'].includes(event?.hook_event_name) &&
        !(event.hook_event_name === 'SessionStart' && event.source === 'compact') &&
        !Object.hasOwn(event, 'recovery_epoch')) {
      try { markInputFailure(location(event.session_id, event.cwd, true)); }
      catch (_) {
        process.stderr.write('Accord: input loss could not be persisted; freshness is unknown. The native caller must hold continuation and recover current input.\n');
      }
    }
    throw error;
  }
}

const HELP = {
  scope: 'Task-local file evidence and supported native Stop continuation; no command, archive or handoff executor.',
  input: 'One JSON object on stdin. Use --hook only for native events; other calls need the current native session/cwd receipt.',
  storage: 'YIYUAN_ACCORD_TASK_STATE_DIR selects an explicit scoped directory. Otherwise use ~/.yiyuan-accord/task-state. Exact-session legacy temporary records remain at their original location; competing locations fail without merge. status.storage reports the selected path and kind. No automatic migration, cross-session adoption, scheduler or power-loss guarantee. State file contents are flushed before atomic replacement; filesystem and directory-entry durability need separate validation.',
  status: {op: 'status', session_id: 'native-session-id', cwd: 'absolute-workspace'},
  contextBudget: {
    operation: 'assess-context',
    binding: 'Use status session/cwd/epoch/expectedRevision plus current conditions: threadId, turnId, hostVersion, model, contextGeneration. The native caller must independently bind these; shared session is not thread/writer identity.',
    assessment: 'Provide assessment with matching conditions and epoch, observedAtMs/validUntilMs, sourceRef, integrity (verified/degraded/unknown), and the actual matching thread/tokenUsage/updated notification as usageEvent. Never restamp old evidence as fresh. Change contextGeneration after compaction or other material context changes and recheck affected estimates.',
    estimates: 'assessment.estimates needs sourceRef and nonnegative integer token upper bounds for contextUpperBoundTokens and nextWorkTokens, positive handoffTokens (including takeover verification), recoveryTokens and safetyMarginTokens. Optional efficiencyCeilingTokens requires efficiencySourceRef. Estimates include additions since the usage event; all bounds must apply to current source-carrier conditions. Target capacity needs its own assessment.',
    limits: 'Read-only advisory arithmetic; does not authenticate caller evidence, measure live occupancy, dispatch, compact, transfer, release or change checkpoint state. Native last/total/cached usage and compression count never substitute for occupancy, efficiency or integrity. Missing data returns unknown; shorten spans and checkpoint early. Never treat a fit as permission or evidence of completed handoff.',
  },
  contextSignals: {
    invocation: '--context-signals reads one JSON object; no input receipt or state write is required',
    input: 'binding {connectionId, threadId, hostVersion, model} from the actual current connection and thread/start result; turnId from the active native call; connected from live transport; maxAgeMs chosen for the task; events [{receivedAtMs, event}] in receive order from this connection. Preserve turn/started and turn/completed, model/rerouted, contextCompaction item starts/completions, legacy thread/compacted and thread/tokenUsage/updated. Do not mix connections or remove invalidations.',
    output: 'Capacity-only observation plus condition generation and observationId. New turn, reroute, compaction or unknown capacity discards old usage; a post-change matching observation is required. Disconnection, expired or missing data stays unknown. Never restamp historical events. A reconnection gets a new connectionId.',
    integration: 'The owning App Server client may expose this through native dynamic tools. For assess-context pass signals containing the current observation request and assessment.observationId from the earlier query; the helper re-observes and rejects changed/unavailable evidence. Keep current input epoch and independently inspected integrity/forecasts. The helper does not subscribe itself, authenticate supplied transport records or establish an efficiency range. No installed Desktop event integration is implied.',
  },
  readback: 'status.checkpoint returns the saved contract or null. Its epoch belongs to the old binding; the top-level epoch belongs to the current input. Readback grants no authority, does not reconcile input, resume paused work or clear quarantine. Stored canContinue is a historical caller decision, not current permission; verify current user and host authority before effects. Never reconstruct missing user input from the contract.',
  hostObservation: 'UserPromptSubmit model and permission_mode are bounded event observations. Missing fields become unknown; resume, interruption or input loss makes stored observations historical. Condition changes on our host continuation invalidate old readiness without creating a new user decision. Other settings, collaboration mode and mid-turn effects are not inferred; the caller checks intent and affected results within current authority.',
  references: 'bind.inputs are workspace-relative path strings; each outputs.path is workspace-relative too. Input fingerprints are observed by the helper. cwd alone is absolute.',
  bind: {op: 'bind', session_id: 'native-session-id', cwd: 'absolute-workspace', epoch: 'from-status', expectedRevision: 0,
    result: 'latest authorized result', inputs: ['source.json'],
    outputs: [{path: 'summary.json', json: {'/total': 60}}, {path: 'details.csv'}],
    nextAction: 'finish and verify both affected files', canContinue: true},
  revise: 'bind rechecks inputs; changed output checks require revisionReason. Pause and its reason survive rebinding unless an authorized resumeReason (nonempty, at most 2048 characters) explicitly lifts it. bind returns mode; status.checkpoint exposes resumeReason, not proof of authority. Older helpers may implicitly activate: inspect the installed interface.',
  unresolved: 'Optional bind.unresolved is a list of up to 32 distinct nonempty strings, each at most 2048 characters, describing known unmet result or fact conditions. Omission inherits existing conditions; an explicit list replaces them, and removing or rewording a prior condition requires revisionReason. status.checkpoint and inspection expose them independently of matched files; any remaining condition prevents verified-local and successful retirement. canContinue means safe authorized work remains, not that the gap is resolved; use false or pause for a necessary external wait. Existing pause, input freshness and bounded Stop retry rules still apply. The caller must verify the evidence or authorized scope change behind a disposition; a reason is not proof. This neither discovers undeclared gaps nor validates semantics. Older helpers do not enforce this field; retain the compatible executor for unfinished state.',
  pause: 'op=pause with current epoch/revision and reason; preserve pending work without continuation.',
  retire: 'op=retire requires verified local predicates and a resolved pause, or explicit user-cancelled disposition plus reason. Without a checkpoint, use current epoch, expectedRevision=0 and reason to retire only the receipt, including after verified exit without an end Hook. Removes only checkpoint files; does not prove task completion.',
  recovery: 'op=recover-lock with lock=state or input requires a provably dead owner. Input recovery invalidates an existing receipt because native input may have been lost. A surviving caller must replay the actual current native input before binding or continuation; do not ask for repeated user input when the host retains it. Uncertain or live ownership is preserved.',
  resume: 'SessionStart/resume sets needsResumeReconciliation without changing the contract or pause state. New native user input enters normally; absent new input, the native caller may replay actual current retained input with recovery_epoch. Neither route resumes paused work or reconciles the saved binding automatically. Existing needsNativeReplay quarantine from real input loss remains strict. Inspect current authority, effects and writer ownership before binding. No cross-task adoption, writer lock or host permission enforcement.',
  replay: 'After input failure or recovery, replay the actual current UserPromptSubmit event through --hook UserPromptSubmit with recovery_epoch from status. The derived token binds the receipt and failure watermarks, including a missing receipt. Use null only when no receipt or failure watermark exists. A later uncaptured native input changes the token; ordinary inputs cannot silently clear quarantine. Never reconstruct missing human intent from the old checkpoint.',
  inputFailure: 'Input loss is conservatively latched outside the input lock. Unidentified input transport failure invalidates helper freshness only in the native caller working directory. Recovery acknowledges it per session. Small failure watermarks remain until the owning state directory is safely retired. If the watermark itself cannot persist, cross-process protection is unknown and the native caller must hold continuation; this helper is not a host permission barrier.',
  limits: 'Existence checks prove only existence; JSON pointers and hashes share observed file bytes, followed by a stability recheck. External writers are not locked: this is local evidence, not an atomic workspace transaction. Caller owns goal, source trust, authority, predicate adequacy and external acceptance. No transcript parsing or extra model call.',
};
if (require.main === module) {
  if (process.argv.includes('--help')) process.stdout.write(JSON.stringify(HELP) + '\n');
  else {
    let input = '';
    const hookIndex = process.argv.indexOf('--hook');
    const hookName = hookIndex === -1 ? null : process.argv[hookIndex + 1];
    const transportFailure = (reason) => {
      if (hookIndex !== -1 && (!hookName || ['UserPromptSubmit', 'Interrupt', 'SessionStart'].includes(hookName))) {
        try { markInputFailure(location('unidentified-native-input', process.cwd(), true), true); }
        catch (_) { process.stderr.write('Accord: unidentified input loss could not be persisted; caller workspace freshness is unknown.\n'); }
      }
      process.stderr.write(`YIYUAN Accord task checkpoint unavailable: ${reason}.\n`);
      process.exitCode = 1;
    };
    process.stdin.setEncoding('utf8');
    process.stdin.on('data', (chunk) => {
      input += chunk;
      if (Buffer.byteLength(input) > 128 * 1024) {
        transportFailure('oversize-native-input');
        process.exit(1);
      }
    });
    process.stdin.on('end', () => {
      let request;
      try { request = JSON.parse(input); }
      catch (_) { transportFailure('invalid-json-input'); return; }
      if (hookName && request?.hook_event_name !== hookName) { transportFailure('native-hook-kind-mismatch'); return; }
      if (hookIndex !== -1 && ['UserPromptSubmit', 'Interrupt'].includes(request?.hook_event_name) &&
          !Object.hasOwn(request, 'recovery_epoch')) {
        try { location(request.session_id, request.cwd); }
        catch (_) { transportFailure('unbound-native-input'); return; }
      }
      try {
        process.stdout.write(JSON.stringify(process.argv.includes('--context-signals') ? observeContext(request)
          : process.argv.includes('--hook') ? hook(request) : operate(request)) + '\n');
      } catch (error) {
        process.stderr.write(`YIYUAN Accord task checkpoint unavailable: ${error.code || error.message}.\n`);
        process.exitCode = 1;
      }
    });
  }
}
module.exports = {operate, hook, assessContext, observeContext};
