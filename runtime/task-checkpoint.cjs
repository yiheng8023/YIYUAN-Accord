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
  try {
    fs.writeFileSync(temporary, encoded, {flag: 'wx', mode: 0o600});
    if (fs.existsSync(file)) regular(file, 128 * 1024);
    fs.renameSync(temporary, file);
  } finally {
    if (fs.existsSync(temporary)) fs.unlinkSync(temporary);
  }
}

function location(session, cwd, create = false) {
  if (!text(session) || session.length > 200 || !path.isAbsolute(cwd || '')) fail('unbound-session');
  const root = fs.realpathSync(cwd);
  if (!fs.statSync(root).isDirectory()) fail('unbound-workspace');
  const base = path.resolve(process.env.YIYUAN_ACCORD_TASK_STATE_DIR ||
                            path.join(os.tmpdir(), 'yiyuan-accord-tasks'));
  if (create) fs.mkdirSync(base, {recursive: true, mode: 0o700});
  if (!fs.existsSync(base)) return null;
  if (!samePath(fs.realpathSync(base), base) || fs.lstatSync(base).isSymbolicLink()) fail('unsafe-state-directory');
  const id = sha(canonical({session, cwd: process.platform === 'win32' ? root.toLowerCase() : root}));
  const workspaceId = sha(process.platform === 'win32' ? root.toLowerCase() : root);
  return {root, input: path.join(base, `${id}.input.json`),
          state: path.join(base, `${id}.state.json`), lock: path.join(base, `${id}.lock`),
          failure: path.join(base, `${id}.input-failure.json`),
          workspaceFailure: path.join(base, `${workspaceId}.workspace-input-failure.json`)};
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

function inspect(where, state) {
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
    : outputs.some((item) => !item.matched) ? 'incomplete' : 'verified-local', inputs, outputs};
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

function binding(request, where, prior, currentInput) {
  if (!currentInput || request.epoch !== currentInput.epoch) fail('latest-user-input-not-reconciled');
  if (currentInput.interrupted) fail('interrupted-task-needs-new-user-input');
  if (currentInput.needsNativeReplay) fail('input-receipt-needs-native-replay');
  if (request.expectedRevision !== (prior?.revision || 0)) fail('task-revision-conflict');
  if (!text(request.result) || !text(request.nextAction) || typeof request.canContinue !== 'boolean' ||
      !Array.isArray(request.inputs) || !Array.isArray(request.outputs) || request.outputs.length === 0 ||
      request.inputs.length + request.outputs.length > 100) fail('incomplete-task-binding');
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
    revision: (prior?.revision || 0) + 1, mode: 'active', result: request.result,
    inputs, outputs, nextAction: request.nextAction, canContinue: request.canContinue,
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
    if (request.op === 'status') return {epoch: currentInput.epoch, revision: prior?.revision || 0,
      needsNativeReplay: currentInput.needsNativeReplay === true,
      mode: prior?.mode || 'unbound', currentInputReconciled: !currentInput.needsNativeReplay && prior?.epoch === currentInput.epoch,
      inspection: prior ? inspectDiagnostic(where, prior) : null};
    if (request.op === 'bind') {
      const state = binding(request, where, prior, currentInput);
      const inspection = inspect(where, state);
      return inputLocked(where, () => {
        currentEpoch(where, currentInput.epoch);
        atomic(where.state, state);
        return {revision: state.revision, inspection};
      });
    }
    if (request.op === 'retire' && !prior) {
      if (currentInput.needsNativeReplay) fail('input-receipt-needs-native-replay');
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

function hint(event, where, currentInput) {
  const skill = path.join(__dirname, '..', 'skills', 'deliver-demand-driven-outcome', 'SKILL.md');
  return {hookSpecificOutput: {hookEventName: event.hook_event_name, additionalContext:
    `Accord task checkpoint: session=${event.session_id}; epoch=${currentInput.epoch}. ` +
    `For authorized nontrivial work, or material continuation, correction or recovery within it, apply "${skill}" ` +
    'through the supported Skill or file-reading tool. Reuse fully loaded guidance while applicable; ' +
    'keep standalone simple answers lightweight and preserve active work across side questions. ' +
    `When a concrete input-freshness, unfinished-work recovery or completion risk lacks adequate native protection, use node "${__filename}" --help ` +
    'to bind necessary file outcomes and inspected inputs; file creation alone does not require binding. Honor existing bindings. Retire task-owned checkpoints after verified completion; ' +
    'preserve unfinished work. Reconcile later user steering; pause on an actual stop. ' +
    'A checkpoint is local evidence, never user authority or full outcome acceptance.'}};
}

function handleHook(event) {
  const name = event.hook_event_name;
  if (!['UserPromptSubmit', 'Stop', 'Interrupt', 'SessionEnd'].includes(name)) fail('unsupported-hook-event');
  const where = location(event.session_id, event.cwd, name === 'UserPromptSubmit');
  if (!where) return {};
  if (name === 'UserPromptSubmit') {
    if (typeof event.prompt !== 'string') fail('missing-native-prompt');
    return inputLocked(where, () => {
    const previous = readInput(where);
    const prior = fs.existsSync(where.state) ? readJson(where.state) : null;
    if (Object.hasOwn(event, 'recovery_epoch') && (previous
        ? !previous.needsNativeReplay || event.recovery_epoch !== previous.epoch
        : event.recovery_epoch !== null)) fail('native-replay-conflict');
    // Codex may deliver our Stop reason as a continuation prompt. Its exact
    // receipt must never be mistaken for fresh human authority.
    if (prior?.continuation === event.prompt) {
      return !previous?.needsNativeReplay && prior.epoch === previous?.epoch ? hint(event, where, previous) : {};
    }
    if (previous?.needsNativeReplay && !Object.hasOwn(event, 'recovery_epoch')) fail('input-receipt-needs-native-replay');
    const input = {schema: 1, epoch: crypto.randomUUID(), promptSha256: sha(event.prompt),
      turnId: event.turn_id || null, continuation: null, failures: previous?.failures || {}};
    publishInput(where, input);
    return hint(event, where, input);
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
        if (!input.needsNativeReplay && readInput(where)?.epoch === input.epoch) fs.unlinkSync(where.input);
      });
      return {}; // Keep unfinished work for an explicitly bound resume/recovery.
    }
    if (!state || state.mode !== 'active' || !state.canContinue || input.interrupted || input.needsNativeReplay ||
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
    if (['UserPromptSubmit', 'Interrupt'].includes(event?.hook_event_name) &&
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
  status: {op: 'status', session_id: 'native-session-id', cwd: 'absolute-workspace'},
  bind: {op: 'bind', session_id: 'native-session-id', cwd: 'absolute-workspace', epoch: 'from-status', expectedRevision: 0,
    result: 'latest authorized result', inputs: ['source.json'],
    outputs: [{path: 'summary.json', json: {'/total': 60}}, {path: 'details.csv'}],
    nextAction: 'finish and verify both affected files', canContinue: true},
  revise: 'Call bind with the current epoch/revision and a revisionReason for changed output checks; old inputs are re-observed.',
  pause: 'op=pause with current epoch/revision and reason; preserve pending work without continuation.',
  retire: 'op=retire after verified local predicates, or explicit user-cancelled disposition plus reason. With no bound checkpoint, current epoch, expectedRevision=0 and a reason retire only the input receipt. A surviving caller may do this after verified native exit if no end Hook ran. Removes only checkpoint files; does not prove task completion.',
  recovery: 'op=recover-lock with lock=state or input requires a provably dead owner. Input recovery invalidates an existing receipt because native input may have been lost. A surviving caller must replay the actual current native input before binding or continuation; do not ask for repeated user input when the host retains it. Uncertain or live ownership is preserved.',
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
      if (hookIndex !== -1 && (!hookName || ['UserPromptSubmit', 'Interrupt'].includes(hookName))) {
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
        process.stdout.write(JSON.stringify(process.argv.includes('--hook') ? hook(request) : operate(request)) + '\n');
      } catch (error) {
        process.stderr.write(`YIYUAN Accord task checkpoint unavailable: ${error.code || error.message}.\n`);
        process.exitCode = 1;
      }
    });
  }
}
module.exports = {operate, hook};
