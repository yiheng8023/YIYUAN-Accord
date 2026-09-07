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
  return {root, input: path.join(base, `${id}.input.json`),
          state: path.join(base, `${id}.state.json`), lock: path.join(base, `${id}.lock`)};
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

function fingerprint(root, name) {
  const file = relative(root, name);
  if (!fs.existsSync(file)) return {present: false};
  const stat = fs.lstatSync(file);
  if (stat.isSymbolicLink()) fail('unsafe-reference');
  if (!stat.isFile()) fail('reference-is-not-a-file');
  return {present: true, sha256: sha(regular(file))};
}

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
    const current = fingerprint(where.root, output.path);
    let matched = current.present;
    if (matched && output.sha256) matched = current.sha256 === output.sha256;
    if (matched && output.json) {
      try {
        const parsed = JSON.parse(regular(relative(where.root, output.path)).toString('utf8'));
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
  return {status: inputs.some((item) => !item.unchanged) ? 'stale-inputs'
    : outputs.some((item) => !item.matched) ? 'incomplete' : 'verified-local', inputs, outputs};
}

function locked(where, callback, wait = false) {
  let fd;
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
  } finally {
    fs.closeSync(fd);
    fs.unlinkSync(where.lock);
  }
}

// Only short receipt/state publication sections hold this lock. Expensive file
// inspection never delays input invalidation. Lock order is state then input;
// native input handling never takes the state lock.
const inputLocked = (where, callback) => locked({...where, lock: where.input + '.lock'}, callback, true);
function currentEpoch(where, epoch) {
  if (readJson(where.input).epoch !== epoch) fail('latest-user-input-not-reconciled');
}

function binding(request, where, prior, currentInput) {
  if (!currentInput || request.epoch !== currentInput.epoch) fail('latest-user-input-not-reconciled');
  if (currentInput.interrupted) fail('interrupted-task-needs-new-user-input');
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
    const file = request.lock === 'input' ? where.input + '.lock' : where.lock;
    const original = regular(file, 1024);
    const owner = JSON.parse(original.toString('utf8'));
    if (!Number.isSafeInteger(owner.pid) || owner.pid <= 0) fail('unknown-lock-owner');
    try { process.kill(owner.pid, 0); fail('lock-owner-still-running'); }
    catch (error) { if (error.code !== 'ESRCH') throw error; }
    if (!regular(file, 1024).equals(original)) fail('lock-owner-changed');
    fs.unlinkSync(file);
    return {recovered: true, scope: 'dead-owner-checkpoint-lock-only'};
  }
  if (!where || !fs.existsSync(where.input)) fail('native-user-input-receipt-missing');
  return locked(where, () => {
    const currentInput = readJson(where.input);
    const prior = fs.existsSync(where.state) ? readJson(where.state) : null;
    if (request.op === 'status') return {epoch: currentInput.epoch, revision: prior?.revision || 0,
      mode: prior?.mode || 'unbound', currentInputReconciled: prior?.epoch === currentInput.epoch,
      inspection: prior ? inspect(where, prior) : null};
    if (request.op === 'bind') {
      const state = binding(request, where, prior, currentInput);
      const inspection = inspect(where, state);
      return inputLocked(where, () => {
        currentEpoch(where, currentInput.epoch);
        atomic(where.state, state);
        return {revision: state.revision, inspection};
      });
    }
    if (!prior || request.expectedRevision !== prior.revision || request.epoch !== currentInput.epoch) {
      fail('task-revision-or-input-conflict');
    }
    if (request.op === 'pause') {
      if (!text(request.reason)) fail('pause-reason-required');
      const pending = inspect(where, prior);
      return inputLocked(where, () => {
        currentEpoch(where, currentInput.epoch);
        atomic(where.state, {...prior, revision: prior.revision + 1, mode: 'paused', epoch: currentInput.epoch, reason: request.reason});
        return {mode: 'paused', revision: prior.revision + 1, pending};
      });
    }
    if (request.op === 'retire') {
      if (prior.epoch !== currentInput.epoch && request.disposition !== 'user-cancelled') fail('latest-user-input-not-reconciled');
      const result = inspect(where, prior);
      if (result.status !== 'verified-local' && request.disposition !== 'user-cancelled') fail('unmet-output-cannot-retire');
      if (request.disposition === 'user-cancelled' && !text(request.reason)) fail('cancellation-reason-required');
      return inputLocked(where, () => {
        currentEpoch(where, currentInput.epoch);
        fs.unlinkSync(where.state);
        fs.unlinkSync(where.input);
        return {retired: true, scope: 'task-checkpoint-files-only', inspection: result};
      });
    }
    fail('unknown-operation');
  });
}

function hint(event, where, currentInput) {
  return {hookSpecificOutput: {hookEventName: event.hook_event_name, additionalContext:
    `Accord task checkpoint: session=${event.session_id}; epoch=${currentInput.epoch}. ` +
    `For authorized work whose deliverables or continuation may be lost, use node "${__filename}" --help ` +
    'to bind necessary file outcomes and inspected inputs. Reconcile later user steering; pause on an actual stop. ' +
    'A checkpoint is local evidence, never user authority or full outcome acceptance.'}};
}

function hook(event) {
  const name = event.hook_event_name;
  if (!['UserPromptSubmit', 'Stop', 'Interrupt', 'SessionEnd'].includes(name)) fail('unsupported-hook-event');
  const where = location(event.session_id, event.cwd, name === 'UserPromptSubmit');
  if (!where) return {};
  if (name === 'UserPromptSubmit') {
    if (typeof event.prompt !== 'string') fail('missing-native-prompt');
    return inputLocked(where, () => {
    const previous = fs.existsSync(where.input) ? readJson(where.input) : null;
    const prior = fs.existsSync(where.state) ? readJson(where.state) : null;
    // Codex may deliver our Stop reason as a continuation prompt. Its exact
    // receipt must never be mistaken for fresh human authority.
    if (prior?.epoch === previous?.epoch && prior?.continuation === event.prompt) return hint(event, where, previous);
    const input = {schema: 1, epoch: crypto.randomUUID(), promptSha256: sha(event.prompt),
      turnId: event.turn_id || null, continuation: null};
    atomic(where.input, input);
    return hint(event, where, input);
    });
  }
  if (!fs.existsSync(where.input)) return {};
  if (name === 'Interrupt') {
    return inputLocked(where, () => {
    const input = readJson(where.input);
    atomic(where.input, {...input, epoch: crypto.randomUUID(), interrupted: true, continuation: null});
    return {};
    });
  }
  return locked(where, () => {
    const input = readJson(where.input);
    const state = fs.existsSync(where.state) ? readJson(where.state) : null;
    if (name === 'SessionEnd') {
      if (!state) inputLocked(where, () => {
        if (readJson(where.input).epoch === input.epoch) fs.unlinkSync(where.input);
      });
      return {}; // Keep unfinished work for an explicitly bound resume/recovery.
    }
    if (!state || state.mode !== 'active' || !state.canContinue || input.interrupted ||
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
      if (readJson(where.input).epoch !== input.epoch) return {};
      atomic(where.state, {...state, lastBlock: key, continuation: reason});
      return {decision: 'block', reason};
    });
  });
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
  retire: 'op=retire after verified local predicates, or explicit user-cancelled disposition plus reason. Removes only checkpoint files.',
  recovery: 'op=recover-lock with lock=state or input removes only a lock whose recorded process no longer exists; uncertain or live ownership is preserved.',
  limits: 'Existence checks prove only existence; JSON pointers and hashes check specified facts. Caller owns goal, source trust, authority, predicate adequacy and external acceptance. No transcript parsing or extra model call.',
};
if (require.main === module) {
  if (process.argv.includes('--help')) process.stdout.write(JSON.stringify(HELP) + '\n');
  else {
    let input = '';
    process.stdin.setEncoding('utf8');
    process.stdin.on('data', (chunk) => { input += chunk; if (Buffer.byteLength(input) > 128 * 1024) process.exit(1); });
    process.stdin.on('end', () => {
      try {
        const request = JSON.parse(input);
        process.stdout.write(JSON.stringify(process.argv.includes('--hook') ? hook(request) : operate(request)) + '\n');
      } catch (error) {
        process.stderr.write(`YIYUAN Accord task checkpoint unavailable: ${error.code || error.message}.\n`);
        process.exitCode = 1;
      }
    });
  }
}
module.exports = {operate, hook};
