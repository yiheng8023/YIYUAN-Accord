'use strict';

// Local task evidence and a scoped continuation callback. This neither grants
// authority nor supplies the host's executor, semantic judgment or sandbox.
const fs = require('node:fs');
const path = require('node:path');
const os = require('node:os');
const crypto = require('node:crypto');

// Keep optional reader code with this process's loaded runtime generation.
// A long-lived MCP may outlive its old package directory during native update.
// Loading code here performs no transcript read; missing optional code is still
// reported only when a context operation actually needs it.
let nativeContextReader, nativeContextLoadError;
try { nativeContextReader = require('./codex-context.cjs').observeNativeTranscript; }
catch (error) { nativeContextLoadError = error; }
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
const INPUT_RECEIPT_LIMIT = 8 * 1024 * 1024;

function present(file) {
  try { fs.lstatSync(file); return true; }
  catch (error) { if (error.code === 'ENOENT') return false; throw error; }
}

function regular(file, limit = 8 * 1024 * 1024) {
  const stat = fs.lstatSync(file);
  if (!stat.isFile() || stat.isSymbolicLink() || stat.size > limit ||
      !samePath(fs.realpathSync(file), path.resolve(file))) fail('unsafe-or-oversize-file');
  return fs.readFileSync(file);
}

function jsonObject(bytes) {
  const value = JSON.parse(bytes.toString('utf8'));
  if (!value || typeof value !== 'object' || Array.isArray(value)) fail('invalid-state-object');
  return value;
}
const readJson = (file, limit = 128 * 1024) => jsonObject(regular(file, limit));

function atomic(file, value, limit = 128 * 1024) {
  const encoded = JSON.stringify(value);
  if (Buffer.byteLength(encoded) > limit) fail('oversize-state-object');
  const temporary = `${file}.${crypto.randomUUID()}.tmp`;
  let descriptor = null;
  try {
    descriptor = fs.openSync(temporary, 'wx', 0o600);
    fs.writeFileSync(descriptor, encoded);
    fs.fsyncSync(descriptor);
    fs.closeSync(descriptor);
    descriptor = null;
    if (fs.existsSync(file)) regular(file, limit);
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
    if (!present(base)) return false;
    if (!samePath(fs.realpathSync(base), base) || fs.lstatSync(base).isSymbolicLink()) fail('unsafe-state-directory');
    return [`${id}.input.json`, `${id}.input.json.lock`, `${id}.state.json`, `${id}.lock`, `${id}.lock.recovery`,
            `${id}.input-failure.json`, `${workspaceId}.workspace-input-failure.json`]
      .some((name) => present(path.join(base, name)));
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
  if (!present(base)) return null;
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

function readInput(where, read = readJson, exists = fs.existsSync) {
  const input = exists(where.input) ? read(where.input, INPUT_RECEIPT_LIMIT) : null;
  const failures = {};
  for (const [key, file] of [['session', where.failure], ['workspace', where.workspaceFailure]]) {
    if (exists(file)) {
      const marker = read(file);
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

function retainedInputs(input) {
  if (!Object.hasOwn(input || {}, 'nativeInputs')) return null;
  const entries = input.nativeInputs;
  if (!Array.isArray(entries) || entries.some((entry) => !entry || !text(entry.epoch) ||
      typeof entry.prompt !== 'string' || entry.promptSha256 !== sha(entry.prompt) ||
      Object.hasOwn(entry, 'recoveryEpoch') && (entry.source !== 'retained-native-replay' ||
        entry.recoveryEpoch !== null && !text(entry.recoveryEpoch)) ||
      !['native-input-event', 'retained-native-replay'].includes(entry.source))) fail('invalid-retained-input');
  return entries;
}

// Recovery evidence only. Paging does not reconcile current input or grant access
// to another session, attachments, work progress or unrecorded earlier history.
function readNativeInput(request, input) {
  const entries = retainedInputs(input);
  const result = {available: entries !== null, coverage: 'captured-hook-inputs-only',
    receiptEpoch: input.epoch, count: entries?.length || 0, entries: [], next: null,
    inputStatus: {needsNativeReplay: input.needsNativeReplay === true,
      needsResumeReconciliation: input.needsResumeReconciliation === true, interrupted: input.interrupted === true}};
  if (entries === null) return result;
  let index = request.index ?? 0;
  let offset = request.offset ?? 0;
  let remaining = request.maxChars ?? 4000;
  if (![index, offset, remaining].every(Number.isSafeInteger) || index < 0 || index > entries.length ||
      offset < 0 || remaining < 1 || remaining > 16000 || index === entries.length && offset !== 0) fail('invalid-input-page');
  while (index < entries.length && remaining > 0 && result.entries.length < 20) {
    const entry = entries[index];
    const characters = Array.from(entry.prompt);
    if (offset > characters.length) fail('invalid-input-page');
    const content = characters.slice(offset, offset + remaining);
    result.entries.push({index, epoch: entry.epoch, turnId: entry.turnId, source: entry.source,
      ...(Object.hasOwn(entry, 'recoveryEpoch') ? {recoveryEpoch: entry.recoveryEpoch} : {}),
      promptSha256: entry.promptSha256, totalChars: characters.length, offset, text: content.join('')});
    remaining -= content.length;
    offset += content.length;
    if (offset === characters.length) { index++; offset = 0; }
  }
  if (index < entries.length) result.next = {index, offset};
  return result;
}

// Recovery text is observational: do not require write permission just to read
// it. Reject overlapping publication or changed input/failure evidence instead
// of acquiring write locks. This snapshot never reconciles or authorizes work.
function readNativeInputSnapshot(request, where) {
  const idle = () => {
    if (fs.existsSync(where.lock) || fs.existsSync(where.input + '.lock')) fail('input-read-busy');
  };
  const read = () => {
    idle();
    const input = readInput(where);
    idle();
    if (!input) fail('native-user-input-receipt-missing');
    return input;
  };
  const input = read();
  const result = readNativeInput(request, input);
  if (canonical(input) !== canonical(read())) fail('input-changed-during-read');
  return result;
}

function nativeContextSource(event) {
  if (!text(event.transcript_path) || !path.isAbsolute(event.transcript_path) ||
      !text(event.session_id) || !text(event.turn_id) || !text(event.model) || !text(event.cwd)) return null;
  return {transcriptPath: event.transcript_path, sessionId: event.session_id,
    turnId: event.turn_id, cwd: event.cwd, model: event.model};
}

function observeStoredContext(input, request, now = Date.now()) {
  if (!input || needsInput(input) || input.interrupted || !input.nativeContextSource) {
    return {state: 'unknown', reason: 'current-native-context-source-unavailable',
      scope: 'native-last-response-context-basis', sourceReleaseAllowed: false};
  }
  if (nativeContextLoadError) throw nativeContextLoadError;
  if (typeof nativeContextReader !== 'function') fail('native-context-reader-unavailable');
  return nativeContextReader(input.nativeContextSource, {now, maxAgeMs: request.maxAgeMs ?? 30000,
    ...(Object.hasOwn(request, 'currentHost') ? {currentHost: request.currentHost} : {})});
}

function readNativeContextSnapshot(request, where) {
  const read = () => {
    if (fs.existsSync(where.lock) || fs.existsSync(where.input + '.lock')) fail('input-read-busy');
    const input = readInput(where);
    if (!input) fail('native-user-input-receipt-missing');
    if (fs.existsSync(where.lock) || fs.existsSync(where.input + '.lock')) fail('input-read-busy');
    return input;
  };
  const input = read();
  const observation = observeStoredContext(input, request);
  if (canonical(input) !== canonical(read())) fail('input-changed-during-read');
  return {...observation, epoch: input.epoch, sourceReleaseAllowed: false};
}

function relativeName(name) {
  if (!text(name) || path.isAbsolute(name) || process.platform === 'win32' && path.win32.parse(name).root ||
      name.split(/[\\/]/).some((part) => part === '.' || part === '..' || !part)) {
    fail('reference-must-be-workspace-relative');
  }
}

function relative(root, name) {
  relativeName(name);
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

function validateOutputCheck(output) {
  if (!output || !text(output.path) ||
      Object.keys(output).some((key) => !['path', 'sha256', 'json'].includes(key))) fail('invalid-output-check');
  relativeName(output.path);
  if (Object.hasOwn(output, 'sha256') && !/^[a-f0-9]{64}$/.test(output.sha256)) fail('invalid-output-hash');
  if (Object.hasOwn(output, 'json') && (!output.json || typeof output.json !== 'object' || Array.isArray(output.json))) {
    fail('invalid-output-json-check');
  }
  for (const key of Object.keys(output.json || {})) pointer({}, key);
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
  try { atomic(where.input, input, INPUT_RECEIPT_LIMIT); }
  catch (error) { error.inputPublicationFailed = true; throw error; }
}
function requireNativeTurn(request, input) {
  if (!request || !Object.hasOwn(request, 'nativeTurnId')) return;
  const expected = request.nativeTurnId;
  const observed = input?.hostObservation?.turnId ??
    (input?.inputSource === 'host-continuation' ? null : input?.turnId);
  if (!text(expected) || expected.length > 200 || expected !== observed) fail('native-call-turn-conflict');
}

function currentEpoch(where, epoch, request = null) {
  const input = readInput(where);
  if (input?.epoch !== epoch) fail('latest-user-input-not-reconciled');
  requireNativeTurn(request, input);
  return input;
}

function retireFiles(where, epoch, prior = null, request = null) {
  return inputLocked(where, () => {
    const input = currentEpoch(where, epoch, request);
    const receipt = fs.existsSync(where.input) ? readJson(where.input, INPUT_RECEIPT_LIMIT) : null;
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
      for (const [file, value] of files) if (!fs.existsSync(file)) {
        atomic(file, value, file === where.input ? INPUT_RECEIPT_LIMIT : 128 * 1024);
      }
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
    observedAtMs: null, validUntilMs: null, windowTokens: null, remainingTokens: null,
    remainingScope: null, occupancy: null, occupancyScope: null,
    efficiency: null, integrity: 'unknown', sourceReleaseAllowed: false};
  const unknown = (reason) => ({...result, reason});
  if (!b || !['connectionId', 'threadId', 'hostVersion', 'model'].every((k) => text(b[k])) ||
      !text(request.turnId) || !integer(request.maxAgeMs) || request.maxAgeMs === 0) return unknown('unbound-connection');
  if (request.connected !== true) return unknown('connection-not-live');
  if (!Array.isArray(request.events)) return unknown('notification-stream-unavailable');
  let turn = null, nextModel = b.model, model = b.model, generation = sha(canonical(b)), usage = null, observed = null;
  let remaining = null, remainingObserved = null;
  let remainingCalls = new Set();
  let active = false, compacting = false, lastTime = -1;
  const invalidate = (kind, identity) => {
    generation = sha(canonical({generation, kind, identity})); usage = null; observed = null;
    remaining = null; remainingObserved = null; remainingCalls = new Set();
  };
  const parseRemaining = (output) => {
    if (typeof output !== 'string') return undefined;
    const match = /^You have ([0-9]+) tokens left in this context window\.$/.exec(output);
    if (match) {
      const tokens = Number(match[1]);
      return integer(tokens) ? tokens : undefined;
    }
    return output === 'You have unknown tokens left in this context window.' ? null : undefined;
  };
  for (const [sequence, envelope] of request.events.entries()) {
    const event = envelope?.event, at = envelope?.receivedAtMs;
    if (!integer(at) || at < lastTime || at > now || !event || typeof event !== 'object') return unknown('invalid-notification-order');
    lastTime = at;
    const p = event.params;
    if (!p || p.threadId !== b.threadId) continue;
    if (event.method === 'thread/settings/updated') {
      // This snapshot describes next-turn settings, not an active-turn reroute.
      // Keep the current turn's observed model and usage until its own boundary.
      const settings = p.threadSettings;
      if (!settings || typeof settings !== 'object' || Array.isArray(settings) || !text(settings.model)) {
        return unknown('next-turn-model-unavailable');
      }
      nextModel = settings.model;
    } else if (event.method === 'turn/started') {
      if (!text(p.turn?.id)) return unknown('invalid-turn-start');
      turn = p.turn.id; model = nextModel; active = true; compacting = false;
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
      } else if (event.method === 'item/completed' && p.item?.type === 'functionCallOutput' &&
          p.item.name === 'get_context_remaining' && p.item.namespace == null) {
        const tokens = parseRemaining(p.item.output);
        if (tokens === undefined) return unknown('invalid-native-remaining-output');
        remaining = tokens;
        remainingObserved = tokens == null ? null : {at, sequence, item: p.item.id};
      } else if (event.method === 'item/completed') {
        // Any later model-visible input or output makes an earlier remaining
        // budget stale. The response-boundary usage remains explicitly scoped.
        remaining = null; remainingObserved = null;
      } else if (event.method === 'rawResponseItem/completed') {
        const item = p.item;
        remaining = null; remainingObserved = null;
        if (item?.type === 'function_call' && item.name === 'get_context_remaining' &&
            item.namespace == null && text(item.call_id)) remainingCalls.add(item.call_id);
        else if (item?.type === 'function_call_output' && text(item.call_id) && remainingCalls.has(item.call_id)) {
          const tokens = parseRemaining(item.output);
          if (tokens === undefined) return unknown('invalid-native-remaining-output');
          remaining = tokens;
          remainingObserved = tokens == null ? null : {at, sequence, item: item.id ?? item.call_id};
          remainingCalls.delete(item.call_id);
        }
      } else if (event.method === 'thread/compacted') {
        invalidate('legacy-compaction-notification', sequence);
      } else if (event.method === 'thread/tokenUsage/updated' && !compacting) {
        const window = p.tokenUsage?.modelContextWindow;
        // A newer response boundary invalidates earlier remaining-budget evidence.
        remaining = null; remainingObserved = null; remainingCalls = new Set();
        // Do not retain an earlier known capacity after a newer unknown value.
        if (!integer(window) || window === 0) { invalidate('unknown-capacity', sequence); continue; }
        const boundary = p.tokenUsage?.last?.totalTokens;
        if (boundary != null && !integer(boundary)) return unknown('invalid-native-boundary-usage');
        usage = {method: event.method, params: {threadId: p.threadId, turnId: p.turnId,
          tokenUsage: {modelContextWindow: window, ...(boundary == null ? {} : {last: {totalTokens: boundary}})}}};
        observed = {at, sequence};
      }
    }
  }
  if (!active || turn !== request.turnId) return unknown('current-turn-not-observed-active');
  result.conditions = {threadId: b.threadId, turnId: turn, hostVersion: b.hostVersion,
    model, contextGeneration: generation};
  if (compacting || !usage) return unknown('fresh-post-change-usage-unavailable');
  const validUntil = Math.min(observed.at + request.maxAgeMs,
    remainingObserved ? remainingObserved.at + request.maxAgeMs : Number.MAX_SAFE_INTEGER);
  if (!integer(validUntil) || now >= validUntil) return unknown('usage-observation-expired');
  const occupancy = usage.params.tokenUsage.last?.totalTokens ?? null;
  const reason = remaining != null ? 'native-remaining-budget-and-response-boundary-occupancy' :
    occupancy != null ? 'native-response-boundary-occupancy-not-unobserved-tail-or-quality' :
      'native-capacity-only-not-occupancy-or-quality';
  return {...result, state: 'window-observed', reason,
    observationId: sha(canonical({generation, observed, usage, remaining, remainingObserved})), usageEvent: usage,
    observedAtMs: Math.max(observed.at, remainingObserved?.at ?? observed.at), validUntilMs: validUntil,
    windowTokens: usage.params.tokenUsage.modelContextWindow, remainingTokens: remaining,
    remainingScope: remaining == null ? null : 'native-auto-compact-or-full-window-minimum',
    occupancy, occupancyScope: occupancy == null ? null : 'last-response-boundary'};
}

// Read-only, caller-bound planning evidence. Native last usage is a response-boundary
// context basis, not timeless occupancy; a forecast cannot authorize host actions.
function assessContext(request, prior, input, now = Date.now(), transcriptObservation = null) {
  const result = {decision: 'unknown', capacityFit: 'unknown', sourceReleaseAllowed: false,
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
  let nativeRemaining = null;
  let transcript = null;
  if (request.nativeContext === true) {
    transcript = transcriptObservation;
    if (Object.hasOwn(request, 'signals') || transcript?.state !== 'observed' ||
        canonical(transcript.conditions) !== canonical(scope) || transcript.validUntilMs <= now) {
      return stop('reassess', 'native-transcript-observation-changed-or-unavailable');
    }
    result.observationId = transcript.observationId;
    result.nativeSourceRef = transcript.sourceRef;
  }
  if (Object.hasOwn(request, 'signals')) {
    const current = observeContext(request.signals, now);
    if (current.state !== 'window-observed' || current.observationId !== assessment.observationId ||
        canonical(current.conditions) !== canonical(scope) ||
        canonical(current.usageEvent) !== canonical(assessment.usageEvent)) {
      return stop('reassess', 'native-observation-changed-or-unavailable');
    }
    nativeRemaining = current.remainingTokens;
  }
  if (!Number.isSafeInteger(assessment.observedAtMs) || !Number.isSafeInteger(assessment.validUntilMs) ||
      assessment.observedAtMs > now || assessment.validUntilMs <= now ||
      assessment.validUntilMs <= assessment.observedAtMs) return stop('reassess', 'assessment-expired-or-invalid-time');
  if (!text(assessment.sourceRef)) return stop('unknown', 'assessment-source-missing');
  if (assessment.integrity === 'degraded') return stop('reassess', 'resolve-observed-context-loss-or-drift');
  if (assessment.integrity !== 'verified') return stop('unknown', 'inheritance-integrity-unknown');
  const native = assessment.usageEvent;
  if (!transcript && (native?.method !== 'thread/tokenUsage/updated' || native.params?.threadId !== scope.threadId ||
      native.params?.turnId !== scope.turnId)) return stop('unknown', 'matching-native-usage-unavailable');
  const count = (n) => Number.isSafeInteger(n) && n >= 0;
  const window = transcript ? transcript.windowTokens : native.params.tokenUsage?.modelContextWindow;
  if (!count(window) || window === 0) return stop('unknown', 'native-window-unknown');
  result.windowTokens = window;
  // total is cumulative. last is the native response-boundary context basis,
  // while get_context_remaining includes the tighter native compaction/window budget.
  let estimate = assessment.estimates;
  if (transcript) {
    if (!count(estimate?.contextTailUpperBoundTokens) || !count(transcript.lastResponseTokens) ||
        !Number.isSafeInteger(transcript.lastResponseTokens + estimate.contextTailUpperBoundTokens)) {
      return stop('unknown', 'sourced-unaccounted-context-tail-required');
    }
    // Read and assess together. An intervening model response may legitimately
    // grow last usage; consume fresh counters rather than repeatedly reject it.
    estimate = {...estimate, contextUpperBoundTokens: transcript.lastResponseTokens + estimate.contextTailUpperBoundTokens};
  }
  const common = ['nextWorkTokens', 'handoffTokens', 'recoveryTokens', 'safetyMarginTokens'];
  if (!estimate || !text(estimate.sourceRef) || !common.every((key) => count(estimate[key])) ||
      estimate.handoffTokens === 0 || estimate.recoveryTokens === 0 || estimate.safetyMarginTokens === 0) {
    return stop('unknown', 'sourced-work-transfer-recovery-estimates-required');
  }
  const transferReserve = estimate.handoffTokens + estimate.recoveryTokens + estimate.safetyMarginTokens;
  if (!Number.isSafeInteger(transferReserve + estimate.nextWorkTokens)) return stop('unknown', 'forecast-overflow');
  if (nativeRemaining != null) {
    result.capacityFit = transferReserve + estimate.nextWorkTokens < nativeRemaining ? 'fits' : 'does-not-fit';
    result.remainingAfterReserves = nativeRemaining - transferReserve;
    if (result.remainingAfterReserves <= 0) return stop('preserve-recovery', 'transfer-reserve-already-at-risk');
    if (estimate.nextWorkTokens >= result.remainingAfterReserves) {
      return stop('prepare-handoff', 'next-span-would-consume-transfer-reserve');
    }
    return stop('continue-bounded', 'forecast-fits-native-remaining-budget-recheck-before-next-span');
  }
  if (!count(estimate.contextUpperBoundTokens)) {
    return stop('unknown', 'sourced-context-upper-bound-required-without-native-remaining-budget');
  }
  const responseBasis = transcript ? transcript.lastResponseTokens : native.params.tokenUsage?.last?.totalTokens;
  if (count(responseBasis) && estimate.contextUpperBoundTokens < responseBasis) {
    return stop('reassess', 'context-forecast-below-observed-response-basis');
  }
  const efficiency = estimate.efficiencyCeilingTokens;
  if (efficiency != null && (!count(efficiency) || efficiency === 0 || !text(estimate.efficiencySourceRef))) {
    return stop('unknown', 'efficiency-range-not-evidenced');
  }
  const limit = efficiency == null ? window : Math.min(window, efficiency);
  result.efficiencyCeilingTokens = efficiency ?? null;
  const reserve = estimate.contextUpperBoundTokens + transferReserve;
  if (!Number.isSafeInteger(reserve + estimate.nextWorkTokens)) return stop('unknown', 'forecast-overflow');
  // Capacity uses the hard window; a stricter efficiency range still controls
  // the combined decision below. A fit is conditional arithmetic, not permission.
  result.capacityFit = reserve + estimate.nextWorkTokens < window ? 'fits' : 'does-not-fit';
  result.remainingAfterReserves = limit - reserve;
  if (result.remainingAfterReserves <= 0) return stop('preserve-recovery', 'transfer-reserve-already-at-risk');
  if (estimate.nextWorkTokens >= result.remainingAfterReserves) return stop('prepare-handoff', 'next-span-would-consume-transfer-reserve');
  // Efficiency and the native compaction threshold can remain unknown without
  // making a sourced, bounded capacity forecast unknowable. Preserve state
  // first: the host may compact sooner than this hard-window estimate.
  if (efficiency == null) return stop('continue-bounded',
    'forecast-fits-hard-window-preserve-state-and-recheck-unknown-efficiency-and-compaction-threshold');
  return stop('continue-bounded', 'forecast-fits-sourced-range-recheck-before-next-span');
}

// A generic output revision cannot silently replace or discard an input basis.
// These explicit dispositions bind observations, not proof of human authority.
function reviseInputs(request, where, prior, inputs, epoch) {
  const key = (name) => process.platform === 'win32' ? name.replace(/\\/g, '/').toLowerCase() : name;
  const requested = Object.hasOwn(request, 'inputRevisions') ? request.inputRevisions : [];
  if (!Array.isArray(requested) || requested.length > 100) fail('invalid-input-revision');
  const pending = new Map();
  for (const item of requested) {
    if (!item || Object.keys(item).sort().join(',') !== 'observed,path,reason' ||
        !text(item.reason) || item.reason.length > 2048) fail('invalid-input-revision');
    relative(where.root, item.path);
    const observed = item.observed;
    if (!observed || typeof observed.present !== 'boolean' ||
        Object.keys(observed).sort().join(',') !== (observed.present ? 'present,sha256' : 'present') ||
        observed.present && (typeof observed.sha256 !== 'string' || !/^[a-f0-9]{64}$/.test(observed.sha256))) fail('invalid-input-revision');
    if (pending.has(key(item.path))) fail('invalid-input-revision');
    pending.set(key(item.path), item);
  }
  const next = new Map(inputs.map((item) => [key(item.path), item]));
  const revisions = [];
  for (const previous of prior?.inputs || []) {
    const current = next.get(key(previous.path));
    if (current && canonical(previous.observed) === canonical(current.observed)) continue;
    const item = pending.get(key(previous.path));
    if (!item) fail('input-revision-required');
    const observed = current?.observed || fingerprint(where.root, previous.path);
    if (canonical(item.observed) !== canonical(observed)) fail('input-revision-observation-changed');
    revisions.push({path: previous.path, previous: previous.observed, observed,
      disposition: current ? 'refresh' : 'remove', reason: item.reason, epoch});
    pending.delete(key(previous.path));
  }
  if (pending.size) fail('input-revision-not-needed');
  return revisions;
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
    validateOutputCheck(output);
    const key = typeof output?.path === 'string' && process.platform === 'win32'
      ? output.path.replace(/\\/g, '/').toLowerCase() : output?.path;
    if (names.has(key)) fail('invalid-output-check');
    names.add(key);
    relative(where.root, output.path);
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
  const inputRevisions = reviseInputs(request, where, prior, inputs, currentInput.epoch);
  return {schema: 1, session: request.session_id, cwd: where.root, epoch: currentInput.epoch,
    revision: (prior?.revision || 0) + 1, mode: paused ? 'paused' : 'active', result: request.result,
    reason: paused ? prior.reason : null, resumeReason: resuming ? request.resumeReason : null,
    inputs, outputs, unresolved, inputRevisions: inputRevisions.length ? inputRevisions : prior?.inputRevisions || [],
    nextAction: request.nextAction, canContinue: request.canContinue,
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
      publishInput(where, {...readJson(where.input, INPUT_RECEIPT_LIMIT), epoch: crypto.randomUUID(), needsNativeReplay: true});
    }
    fs.unlinkSync(file);
    return {recovered: true, scope: inputRecovery ? 'dead-input-lock-and-receipt-invalidation'
      : 'dead-owner-checkpoint-lock-only', needsNativeReplay: inputRecovery};
    };
    // Serialize recovery callers from owner inspection through deletion. Without
    // this gate, a second recovery can replace the checked lock with a live one.
    // Do not use the input lock here: both original locks may be left by a crash.
    return locked({...where, lock: where.lock + '.recovery'},
      () => inputRecovery ? locked(where, recover) : recover());
  }
  if (!where) fail('native-user-input-receipt-missing');
  if (request.op === 'status') return recoveryBasis(where, ({input: currentInput, state: prior}) => {
    validateRecoveryIdentity(request, where, currentInput, prior);
    if (!currentInput) fail('native-user-input-receipt-missing');
    const captured = retainedInputs(currentInput);
    return {epoch: currentInput.epoch, revision: prior?.revision || 0,
      storage: where.storage,
      recoveryInputs: {available: captured !== null, count: captured?.length || 0},
      inputSource: currentInput.inputSource || 'unspecified-legacy-receipt',
      hostObservation: currentInput.hostObservation ? projectHostObservation(currentInput.hostObservation) : null,
      nativeContextSourceAvailable: Boolean(currentInput.nativeContextSource) && !needsInput(currentInput) && !currentInput.interrupted,
      hostObservationCurrent: Boolean(currentInput.hostObservation) && !needsInput(currentInput) && !currentInput.interrupted,
      needsNativeReplay: currentInput.needsNativeReplay === true,
      needsResumeReconciliation: currentInput.needsResumeReconciliation === true,
      mode: prior?.mode || 'unbound', currentInputReconciled: !needsInput(currentInput) && prior?.epoch === currentInput.epoch,
      checkpoint: prior ? {epoch: prior.epoch, result: prior.result, inputs: prior.inputs, outputs: prior.outputs,
        nextAction: prior.nextAction, canContinue: prior.canContinue, unresolved: savedUnresolved(prior),
        inputRevisions: (prior.inputRevisions || []).map((item) => Object.fromEntries(
          ['path', 'previous', 'observed', 'disposition', 'reason', 'epoch'].map((key) => [key, item[key]]))),
        revisionReason: prior.revisionReason, reason: prior.reason || null, resumeReason: prior.resumeReason || null} : null,
      inspection: prior ? inspectDiagnostic(where, prior) : null};
  });
  if (request.op === 'read-native-input') return readNativeInputSnapshot(request, where);
  if (request.op === 'observe-context') return readNativeContextSnapshot(request, where);
  return locked(where, () => {
    const currentInput = inputLocked(where, () => readInput(where));
    if (!currentInput) fail('native-user-input-receipt-missing');
    const prior = fs.existsSync(where.state) ? readJson(where.state) : null;
    if (['bind', 'pause', 'retire'].includes(request.op)) requireNativeTurn(request, currentInput);
    if (request.op === 'assess-context') {
      const observation = request.nativeContext === true ? observeStoredContext(currentInput, request) : null;
      const result = assessContext(request, prior, currentInput, Date.now(), observation);
      const after = inputLocked(where, () => readInput(where));
      return canonical(after) === canonical(currentInput) ? result
        : {...result, decision: 'reassess', sourceReleaseAllowed: false, reasons: ['input-changed-during-assessment']};
    }
    if (request.op === 'bind') {
      const state = binding(request, where, prior, currentInput);
      const inspection = inspect(where, state);
      // Removed inputs are absent from inspect(state); recheck every current
      // disposition after output reads, without holding the native-input lock.
      for (const item of request.inputRevisions || []) {
        if (canonical(fingerprint(where.root, item.path)) !== canonical(item.observed)) fail('input-revision-unstable');
      }
      return inputLocked(where, () => {
        currentEpoch(where, currentInput.epoch, request);
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
      retireFiles(where, currentInput.epoch, null, request);
      return {retired: true, scope: 'unbound-input-receipt-only', inspection: null};
    }
    if (!prior || request.expectedRevision !== prior.revision || request.epoch !== currentInput.epoch) {
      fail('task-revision-or-input-conflict');
    }
    if (request.op === 'pause') {
      if (!text(request.reason)) fail('pause-reason-required');
      const pending = inspectDiagnostic(where, prior);
      return inputLocked(where, () => {
        currentEpoch(where, currentInput.epoch, request);
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
      retireFiles(where, currentInput.epoch, prior, request);
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

function projectHostObservation(observation) {
  const pick = (value, keys) => Object.fromEntries(keys.map((key) => [key, value[key]]));
  return {...pick(observation, ['schema', 'event', 'turnId', 'comparison', 'scope']),
    values: pick(observation.values, ['model', 'permissionMode']),
    sourceRefs: pick(observation.sourceRefs, ['model', 'permissionMode']),
    changes: observation.changes.map((change) => pick(change, ['field', 'previous', 'current', 'kind']))};
}

// Shared host judgment duty survives ordinary entry and context restoration.
// The brief Skill is the sole maintained entry body. Hook delivery resolves its
// package-local links; reading guidance never touches task state.
function entryGuidance() {
  const root = path.join(__dirname, '..');
  const packaged = fs.existsSync(path.join(root, '.codex-plugin', 'plugin.json'));
  const skill = path.join(root, ...(packaged ? [] : ['plugins', 'yiyuan-accord-codex']),
    'skills', 'deliver-demand-driven-outcome', 'SKILL.md');
  const info = fs.lstatSync(skill);
  if (!info.isFile() || info.isSymbolicLink() || info.size > 10000) fail('entry-guidance-unavailable');
  const text = fs.readFileSync(skill, 'utf8').replace(/\r\n/g, '\n');
  const matched = /^---\nname: deliver-demand-driven-outcome\ndescription: [^\n]+\n---\n+([\s\S]+)$/.exec(text);
  if (!matched || !matched[1].trim()) fail('entry-guidance-unavailable');
  const body = matched[1].trim().replace(/\]\((\.\.?\/[^)]+)\)/g,
    (_, target) => '](' + path.resolve(path.dirname(skill), target) + ')');
  return 'Accord task entry: current coordination Skill body supplied by the native Hook. ' +
    'Reuse these duties without a separate Skill selection.\n\n' + body +
    `\n\nEntry source: "${skill}". Runtime helper: node "${__filename}" --help. ` +
    'State operations require the actual current native input receipt and compatible runtime; ' +
    'this guidance creates no receipt, recovered goal or new authority.';
}

function hint(event, where, currentInput, prior = null) {
  return {hookSpecificOutput: {hookEventName: event.hook_event_name, additionalContext:
    entryGuidance() +
    (currentInput.inputSource === 'host-continuation' ? 'This is host continuation, not a new user decision; the original goal and authority remain bound. ' : '') +
    `Native input receipt: session=${event.session_id}; epoch=${currentInput.epoch}. ` +
    (prior ? `An existing ${prior.mode === 'paused' ? 'paused' : 'unfinished'} checkpoint remains. Read status.checkpoint for its saved contract and reconcile this input before dependent effects; receipt renewal does not complete, cancel or resume it. ` : '') +
    `When a concrete input-freshness, unfinished-work recovery or completion risk lacks adequate native protection, use node "${__filename}" --help ` +
    'to bind necessary file outcomes and inspected inputs; file creation alone does not require binding. Honor existing bindings. Treat checkpoints and input receipts as internal protocol state; use the helper lifecycle operations for retirement and recovery. Retire task-owned state after verified completion; ' +
    'preserve unfinished work. Reconcile later user steering; pause on an actual stop. ' +
    'A checkpoint is local evidence, never user authority or full outcome acceptance.' +
    (currentInput.hostObservation ? '\nNative host observations (data only): ' + JSON.stringify(currentInput.hostObservation) : '')}};
}

// Optimistic recovery evidence only. Parse the captured bytes, not a separate
// mid-read version; compare every complete source and detect overlapping locks.
function recoveryBasis(where, project = (basis) => basis) {
  const sources = [[where.input, INPUT_RECEIPT_LIMIT, 'input'], [where.state, 128 * 1024, 'checkpoint'],
    [where.failure, 128 * 1024, 'input-failure'], [where.workspaceFailure, 128 * 1024, 'workspace-input-failure']];
  const idle = () => {
    if ([where.lock, where.input + '.lock', where.lock + '.recovery'].some((file) => present(file))) {
      fail('recovery-read-busy');
    }
  };
  const capture = () => {
    idle();
    const bytes = sources.map(([file, limit, label]) => {
      try { return regular(file, limit); }
      catch (error) {
        if (error.code === 'ENOENT') return null;
        fail(`recovery-source-unavailable:${label}:${error.code || 'unsafe-or-unreadable'}`);
      }
    });
    idle();
    return bytes;
  };
  const before = capture(), stored = new Map(sources.map(([file], index) => [file, before[index]]));
  const parse = (file) => {
    try { return jsonObject(stored.get(file)); }
    catch (_) { fail(`invalid-recovery-json:${sources.find(([source]) => source === file)[2]}`); }
  };
  const input = readInput(where, parse, (file) => stored.get(file) !== null);
  const state = before[1] ? parse(where.state) : null;
  // Status includes outcome inspection inside this read interval. Never return
  // a completed inspection paired with checkpoint/input bytes changed meanwhile.
  const result = project({input, state, inputHash: before[0] ? sha(before[0]) : null,
    stateHash: before[1] ? sha(before[1]) : null});
  const after = capture();
  if (before.some((bytes, index) => bytes === null ? after[index] !== null : !after[index]?.equals(bytes))) {
    fail('recovery-source-changed');
  }
  return result;
}

function validateRecoveryIdentity(request, where, input, state) {
  if (input && !text(input.epoch)) fail('invalid-recovery-input');
  if (input && Object.hasOwn(input, 'schema') && input.schema !== 1) fail('invalid-recovery-input');
  if (input && Object.hasOwn(input, 'inputSource') &&
      (!text(input.inputSource) || input.inputSource.length > 256)) fail('invalid-recovery-input-source');
  if (input && ['interrupted', 'needsNativeReplay', 'needsResumeReconciliation'].some((key) =>
    Object.hasOwn(input, key) && typeof input[key] !== 'boolean')) fail('invalid-recovery-flags');
  if (state && (state.schema !== 1 || state.session !== request.session_id || !text(state.cwd) || !samePath(state.cwd, where.root) ||
      !text(state.epoch) || !Number.isSafeInteger(state.revision) || state.revision < 1 ||
      !['active', 'paused'].includes(state.mode) || typeof state.canContinue !== 'boolean' ||
      !text(state.result) || !text(state.nextAction) || !Array.isArray(state.inputs) || !Array.isArray(state.outputs) ||
      !state.outputs.length || state.inputs.length + state.outputs.length > 100)) {
    fail('invalid-recovery-checkpoint');
  }
  if (input?.hostObservation != null) {
    const observation = input.hostObservation;
    const value = (v) => v === null || typeof v === 'string' && v.length <= 256 && /^[A-Za-z0-9][A-Za-z0-9._:/-]*$/.test(v);
    if (observation.schema !== 'yiyuan-accord-native-host-observation/v1' || observation.event !== 'UserPromptSubmit' ||
        !observation.values || Object.keys(observation.values).sort().join(',') !== 'model,permissionMode' ||
        !Object.values(observation.values).every(value) || !value(observation.turnId) ||
        !['previous-input-receipt', 'no-current-prior-observation'].includes(observation.comparison) ||
        !text(observation.scope) || observation.scope.length > 512 ||
        observation.sourceRefs?.model !== 'UserPromptSubmit.model' ||
        observation.sourceRefs?.permissionMode !== 'UserPromptSubmit.permission_mode' ||
        !Array.isArray(observation.changes) || observation.changes.some((change) => !change ||
          !['model', 'permissionMode'].includes(change.field) || !value(change.previous) || !value(change.current) ||
          !['available', 'unavailable', 'changed'].includes(change.kind))) fail('invalid-recovery-host-observation');
  }
  if (state) {
    savedUnresolved(state);
    const names = new Set();
    const reference = (name) => {
      relativeName(name);
      const key = process.platform === 'win32' ? name.replace(/\\/g, '/').toLowerCase() : name;
      if (names.has(key)) fail('invalid-recovery-checkpoint-references');
      names.add(key);
    };
    const observed = (value) => value && typeof value.present === 'boolean' &&
      Object.keys(value).sort().join(',') === (value.present ? 'present,sha256' : 'present') &&
      (!value.present || typeof value.sha256 === 'string' && /^[a-f0-9]{64}$/.test(value.sha256));
    for (const output of state.outputs) { validateOutputCheck(output); reference(output.path); }
    for (const input of state.inputs) {
      if (!input || Object.keys(input).sort().join(',') !== 'observed,path' ||
          !observed(input.observed) || !input.observed.present) fail('invalid-recovery-input-baseline');
      reference(input.path);
    }
    if (Object.hasOwn(state, 'inputRevisions') && (!Array.isArray(state.inputRevisions) || state.inputRevisions.length > 100 ||
        state.inputRevisions.some((item) => !item || !text(item.path) || !observed(item.previous) || !observed(item.observed) ||
          !['refresh', 'remove'].includes(item.disposition) || !text(item.reason) || item.reason.length > 2048 || !text(item.epoch)))) {
      fail('invalid-recovery-input-revisions');
    }
    const revisedNames = new Set();
    for (const item of state.inputRevisions || []) {
      relativeName(item.path);
      const key = process.platform === 'win32' ? item.path.replace(/\\/g, '/').toLowerCase() : item.path;
      if (revisedNames.has(key)) fail('invalid-recovery-input-revisions');
      revisedNames.add(key);
    }
  }
}

function compactHint(event, where) {
  const request = {op: 'read-native-input', session_id: event.session_id, cwd: where?.root || event.cwd,
    index: 0, offset: 0, maxChars: 4000};
  const locators = {capturedInput: {inline: false, firstPageRequest: request},
    checkpoint: {inline: false, path: where?.state || null}};
  let data = {state: 'unknown', restorationComplete: false, session_id: event.session_id, cwd: request.cwd, ...locators};
  const fits = (value) => Buffer.byteLength(JSON.stringify(value)) <= 6000;
  try {
    if (!where) fail('recovery-storage-unavailable');
    const {input, state, inputHash, stateHash} = recoveryBasis(where);
    validateRecoveryIdentity(event, where, input, state);
    const flags = input ? {interrupted: input.interrupted === true, needsNativeReplay: input.needsNativeReplay === true,
      needsResumeReconciliation: input.needsResumeReconciliation === true} : null;
    const captured = input ? readNativeInput(request, input) : null;
    data = {...data, state: 'observed-snapshot', receiptEpoch: input?.epoch || null, inputFlags: flags,
      checkpointEpochMatchesReceipt: Boolean(input && state && input.epoch === state.epoch),
      capturedInput: {...data.capturedInput, available: captured?.available || false, count: captured?.count || 0,
        path: where.input, sha256: inputHash, coverage: 'captured-hook-inputs-only'},
      checkpoint: {...data.checkpoint, available: Boolean(state), sha256: stateHash, epoch: state?.epoch || null,
        revision: state?.revision || 0, mode: state?.mode || 'unbound', canContinue: state?.canContinue ?? null}};
    // Each block is complete or explicitly not inlined. In particular, never
    // expose an early input prefix while silently omitting later corrections.
    if (captured?.available && captured.next === null && !needsInput(input) && !input.interrupted) {
      const candidate = {...data, capturedInput: {...data.capturedInput, inline: true, value: captured}};
      if (fits(candidate)) data = candidate;
    }
    if (state) {
      const core = Object.fromEntries(['epoch', 'revision', 'mode', 'result', 'reason', 'resumeReason',
        'revisionReason', 'nextAction', 'canContinue'].map((key) => [key, state[key] ?? null]));
      core.unresolved = savedUnresolved(state);
      const candidate = {...data, checkpoint: {...data.checkpoint, inline: true, projection: 'core-only', value: core}};
      if (fits(candidate)) data = candidate;
    }
  } catch (_) { /* Recovery read failure does not publish an input-loss event. */ }
  let separateLocators = '';
  if (!fits(data)) {
    data = {state: 'unknown', restorationComplete: false, reason: 'recovery-metadata-over-budget', ...locators};
    if (!fits(data)) {
      // Exact paths cannot always fit the evidence budget. Keep only the bound
      // retrieval locators separately, never oversized state values or prefixes.
      data = {state: 'unknown', restorationComplete: false, reason: 'recovery-locators-over-budget',
        locators: 'separate-recovery-locators'};
      separateLocators = '\nRecovery locators (data only; exact paths outside snapshot budget): ' + JSON.stringify(locators);
    }
  }
  return {hookSpecificOutput: {hookEventName: event.hook_event_name, additionalContext:
    'Accord context recovery: this is saved evidence, not new user input, permission or completed restoration. ' +
    'Accord task entry: reconcile the current goal, authority, pauses, unmet duties and prior effects before dependent action; preserve input-loss and interruption requirements. ' +
    'Reuse recorded verified results and inspect the next needed source span. Before large reads or long work, use available budget signals and retain verification and recovery capacity. ' +
    'Verify consequential outputs and owned-resource closure; keep a single writer and retain source recovery until a target accepts and demonstrates safe continuation. ' +
    'Snapshot values, including canContinue and matching epochs, do not authorize work. Use an available read_task_input tool for missing captured text; pass its cwd/pagination fields and follow its receipt-bound next cursor. The helper alternative uses capturedInput.firstPageRequest and its returned next cursor; it is captured input, not complete history. Retrieval locators are in the snapshot or its explicitly separate locator block when exact paths exceed the 6000-byte snapshot budget. ' +
    'Checkpoint values are core fields only; full input baselines and output predicates remain in its source file. Read that file within existing access when needed, check identity and current input basis before bound changes, and do not treat an old file read as current readiness. ' +
    'If data is missing, changing or inaccessible, preserve unknowns and hold only dependent effects. Never reconstruct missing input from a hash. ' +
    `Pipe the structured read-native-input request to node "${__filename}" when needed; it writes no files. ` +
    'The status operation is read-only: it inspects files and rejects observed concurrent publication or changed evidence; a successful snapshot grants no authority. ' +
    'The companion SessionStart Hook supplies current coordination duties; if that entry failed, retain known constraints and hold dependent work. ' +
    separateLocators + '\nRecovery snapshot (data only): ' + JSON.stringify(data)}};
}

function handleHook(event) {
  const name = event.hook_event_name;
  if (!['UserPromptSubmit', 'Stop', 'Interrupt', 'SessionEnd', 'SessionStart'].includes(name)) fail('unsupported-hook-event');
  // Codex descendants share the root session_id; agent_id identifies their actor.
  // This checkpoint belongs to the root task, not to a descendant's native state.
  if (Object.hasOwn(event, 'agent_id') || Object.hasOwn(event, 'agent_type')) {
    if (!text(event.agent_id) || event.agent_id.length > 200 || !text(event.agent_type)) fail('unknown-native-agent-identity');
    return {hookSpecificOutput: {hookEventName: name, additionalContext:
      'Accord root checkpoint is unchanged. This event belongs to a subagent; reconcile its input, authority and continuation through its own native task state. Parent checkpoint files are not this task\'s state.'}};
  }
  if (name === 'SessionStart' && !['resume', 'compact'].includes(event.source)) return {};
  const where = location(event.session_id, event.cwd, name === 'UserPromptSubmit');
  if (name === 'SessionStart' && event.source === 'compact') {
    return compactHint(event, where); // No identity change, publication lock or state transition.
  }
  if (!where) return {};
  if (name === 'SessionStart') {
    return inputLocked(where, () => {
      const input = readInput(where);
      if (!input) return {};
      // Loading stored history is not fresh authority. Keep the contract and
      // pause state. A new native input can enter normally; only actual input
      // loss needs token-bound replay. Do not clear a pre-existing quarantine.
      publishInput(where, {...input, epoch: crypto.randomUUID(), needsResumeReconciliation: true,
        nativeContextSource: null, continuation: null});
      return {hookSpecificOutput: {hookEventName: name, additionalContext:
        'Accord: stored task evidence needs recovery reconciliation. Read checkpoint status and inspect current user/host authority, prior effects and writer ownership. A new native user input enters normally; if no new input arrives, use recovery_epoch to replay actual current input retained by the host. Existing input-loss quarantine still requires token-bound replay. Preserve pauses; inherited history grants no permission or writer ownership. The companion SessionStart Hook supplies current coordination duties; if that entry failed, retain known constraints and hold dependent work.'}};
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
      const refreshed = {...previous, hostObservation, inputSource: 'host-continuation', nativeContextSource: nativeContextSource(event),
        ...(changed ? {epoch: crypto.randomUUID(), continuation: null} : {})};
      publishInput(where, refreshed);
      return hint(event, where, refreshed, prior);
    }
    if (previous?.needsNativeReplay && !Object.hasOwn(event, 'recovery_epoch')) fail('input-receipt-needs-native-replay');
    const input = {schema: 1, epoch: crypto.randomUUID(), promptSha256: sha(event.prompt),
      turnId: event.turn_id || null, continuation: null, failures: previous?.failures || {},
      inputSource: 'native-input-event', hostObservation: observeNativeHost(event, previous),
      nativeContextSource: nativeContextSource(event)};
    input.nativeInputs = [...(retainedInputs(previous) || []), {epoch: input.epoch, turnId: input.turnId,
      source: Object.hasOwn(event, 'recovery_epoch') ? 'retained-native-replay' : 'native-input-event',
      ...(Object.hasOwn(event, 'recovery_epoch') ? {recoveryEpoch: event.recovery_epoch} : {}),
      promptSha256: input.promptSha256, prompt: event.prompt}];
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
        if (!needsInput(input) && !input.interrupted && readInput(where)?.epoch === input.epoch) fs.unlinkSync(where.input);
      });
      return {}; // Keep unfinished work for an explicitly bound resume/recovery.
    }
    // A continuation can keep human authority while entering a new native turn.
    const turnOf = (value) => value?.hostObservation?.turnId ??
      (value?.inputSource === 'host-continuation' ? null : value?.turnId);
    const currentTurn = turnOf(input);
    if (text(event.turn_id) && text(currentTurn) && event.turn_id !== currentTurn) return {};
    const sameInput = () => {
      const current = readInput(where);
      return current?.epoch === input.epoch && turnOf(current) === currentTurn;
    };
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
      if (!sameInput()) return {};
      atomic(where.state, {...state, lastBlock: key, continuation: reason});
      if (!sameInput()) return {};
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
  scope: 'Root-task file evidence and supported native Stop continuation; no command, archive or handoff executor. Native subagent events carry agent_id because session_id is shared with the root. They leave root state unchanged; subagent continuation uses native task state. This helper does not provide independent subagent checkpoints or enforce caller authorization.',
  input: 'One JSON object on piped stdin, not an interactive terminal. In PowerShell, pipe $request through ConvertTo-Json -Depth 8 -Compress to node <helper-path>. Use --hook only for native events; other calls need the current native session/cwd receipt.',
  storage: 'YIYUAN_ACCORD_TASK_STATE_DIR selects an explicit scoped directory. Otherwise use ~/.yiyuan-accord/task-state. Exact-session legacy temporary records remain at their original location; competing locations fail without merge. status.storage reports the selected path and kind. No automatic migration, cross-session adoption, scheduler or power-loss guarantee. State file contents are flushed before atomic replacement; filesystem and directory-entry durability need separate validation.',
  operations: ['status', 'read-native-input', 'observe-context', 'assess-context', 'bind', 'pause', 'retire', 'recover-lock'],
  nativeMutationIdentity: 'A native caller may supply nativeTurnId for bind/pause/retire. It must match the current input host observation at initial read and final publication/deletion, including a new host-continuation turn with unchanged human-input epoch. The MCP writer supplies it from native metadata; legacy callers without it retain their existing identity responsibility. This is local correlation, not authentication or user authority.',
  nativeContext: {
    read: {op: 'observe-context', session_id: 'native-session-id', cwd: 'absolute-workspace', maxAgeMs: 30000},
    source: 'Only the native transcript binding retained from a root UserPromptSubmit event is read; request-supplied paths are ignored. Reads are bounded to that file and do not scan other task history. Missing, stale, changing or unbound metadata is unknown. recordedHostVersion is session metadata, not live identity. For current host conditions pass currentHost {threadId, turnId, model, hostVersion, sourceRef} from an actual matching native observation, or use the MCP includeContext option. Without it conditions.hostVersion stays null; caller data is not authentication.',
    assessment: 'Use assess-context with nativeContext=true, the same independently sourced currentHost and chosen maxAgeMs, current epoch/revision, observation.conditions and your inspected integrity/time/estimate claims. Provide estimates.contextTailUpperBoundTokens for unaccounted history after the latest response, plus nextWorkTokens/handoffTokens/recoveryTokens/safetyMarginTokens and sourceRef. The operation reads counters within that age limit and derives contextUpperBoundTokens from lastResponseTokens plus the tail estimate; normal response growth does not force an observe/assess retry loop. Changed model/turn/context generation still requires reassessment. Returned observationId/nativeSourceRef identify the facts actually used.',
    limit: 'Native last usage is a recent response-boundary basis, cumulative usage is not occupancy, and neither proves inheritance integrity or authority. Existing pauses, input recovery, forecast and ownership checks remain; no automatic mode activation, dispatch or source release.'
  },
  status: {op: 'status', session_id: 'native-session-id', cwd: 'absolute-workspace'},
  retainedInputs: {
    read: {op: 'read-native-input', session_id: 'native-session-id', cwd: 'absolute-workspace', index: 0, offset: 0, maxChars: 4000},
    paging: 'Defaults read from the first captured event, with at most 4000 Unicode code points and 20 entries. maxChars may be 1..16000. Pass returned next.index and next.offset unchanged for the next page; null means the captured end, not the end of all task history. Text hashes cover full original strings, not fragments. Legacy receipts report unavailable instead of inventing text. Reads create no locks or files; observed publication locks or changed input/failure evidence reject the read. A stable snapshot does not establish later freshness or permission to act.',
    scope: 'Retains successful native input-event text and explicitly identified native replays in the existing local receipt. Replay entries preserve the consumed recoveryEpoch; missing is unknown, while null denotes an explicit replay without a prior receipt. Our recognized Stop continuation does not add a user input. Events and embedded quotations are not automatically new human decisions; reconcile original source, current input, authority and effects. Capture is not complete conversation, attachment content, model reasoning, a semantic checkpoint or an access grant. Reads preserve pause, quarantine and checkpoint state.',
    lifecycle: 'Input receipts, including captured text, are bounded to 8 MiB and never silently truncated; full storage fails capture and preserves existing failure/replay protection. Transport and bound checkpoint JSON remain limited to 128 KiB. Existing scoped storage and retirement apply: bound work retains the receipt at session end; reconciled unbound receipts end with SessionEnd or verified caller retirement. No new service, transcript scan or model call. Preserve a compatible executor; older versions may not retain or expose text. This local copy may contain sensitive user text and must not be published as routine evidence.'
  },
  contextBudget: {
    operation: 'assess-context',
    binding: 'Use status session/cwd/epoch/expectedRevision plus current conditions: threadId, turnId, hostVersion, model, contextGeneration. The native caller must independently bind these; shared session is not thread/writer identity.',
    assessment: 'Provide assessment with matching conditions and epoch, observedAtMs/validUntilMs, sourceRef, integrity (verified/degraded/unknown), and the actual matching thread/tokenUsage/updated notification as usageEvent. With signals, the helper re-observes any first-party get_context_remaining output before using it. Never restamp old evidence as fresh. Change contextGeneration after compaction or other material context changes and recheck affected estimates.',
    estimates: 'assessment.estimates needs sourceRef, a nonnegative nextWorkTokens bound, and positive handoffTokens (including takeover verification), recoveryTokens and safetyMarginTokens. A bound first-party get_context_remaining result supplies the tighter native compaction/window remainder. Without it, also provide contextUpperBoundTokens; optional efficiencyCeilingTokens requires efficiencySourceRef. All bounds apply to current source-carrier conditions. Target capacity needs its own assessment.',
    result: 'With a fresh native remaining budget, capacityFit and remainingAfterReserves compare the next span with transfer and recovery reserves inside that tighter budget. The value is not the full model window. Without it, sourced context/work/reserve bounds are compared with the hard native window and any evidenced efficiency ceiling. A strict fit with unknown efficiency permits only bounded continuation after preserving critical state; it does not prove efficiency or prevent earlier native compaction. Reassess after context changes and before the next span. Never override a pause, reassessment or recovery/handoff recommendation with capacityFit.',
    limits: 'Read-only advisory arithmetic; does not authenticate caller evidence, dispatch, compact, transfer, release or change checkpoint state. Native last.totalTokens is only the response-boundary context basis; cumulative total, cached usage and compression count are not occupancy. Later inputs or outputs make remaining-budget evidence stale. Missing data returns unknown; shorten spans and checkpoint early. Never treat a fit as permission or completed handoff.',
  },
  contextSignals: {
    invocation: '--context-signals reads one JSON object; no input receipt or state write is required',
    input: 'binding {connectionId, threadId, hostVersion, model} from the actual current connection and thread/start result; turnId from the active native call; connected from live transport; maxAgeMs chosen for the task; events [{receivedAtMs, event}] in receive order from this connection. Preserve thread/settings/updated, turn/started and turn/completed, model/rerouted, contextCompaction item starts/completions, rawResponseItem/completed call/output pairs or named functionCallOutput completions for first-party get_context_remaining, legacy thread/compacted and thread/tokenUsage/updated. Settings snapshots update the next-turn model; reroutes belong to their active turn. Do not mix connections, remove invalidations or detach outputs from call IDs.',
    output: 'The native window, last-response-boundary occupancy when reported, optional tighter native remaining budget, condition generation and observationId. New turn, reroute, compaction, later model-visible output or unknown capacity invalidates affected evidence; obtain a matching observation after change. Disconnection, expiry or missing data stays unknown. Never restamp historical events. A reconnection gets a new connectionId.',
    integration: 'The owning App Server client may expose this through native dynamic tools. For assess-context pass signals containing the current observation request and assessment.observationId from the earlier query; the helper re-observes and rejects changed/unavailable evidence. Keep current input epoch and independently inspected integrity/forecasts. The helper does not subscribe itself, authenticate supplied transport records or establish an efficiency range. No installed Desktop event integration is implied.',
  },
  readback: 'status is read-only and returns the saved contract or null only from a stable observed snapshot. It rejects observed publication/recovery locks, changed source bytes, invalid JSON (with its source role) and incompatible checkpoint identity/checks without repairing or deleting evidence. Host observations and input-revision metadata expose only declared fields; schema validation is not source authentication. Snapshot-file I/O failures identify the source role and error code; failures have a nonzero exit, never an unbound success. Its epoch belongs to the current input; checkpoint.epoch belongs to the old binding. Readback grants no authority, does not reconcile input, resume paused work or clear quarantine. Stored canContinue is a historical caller decision, not current permission; verify current user and host authority before effects. Never reconstruct missing user input from the contract.',
  hostObservation: 'UserPromptSubmit model and permission_mode are bounded event observations. Missing fields become unknown; resume, interruption or input loss makes stored observations historical. Condition changes on our host continuation invalidate old readiness without creating a new user decision. Other settings, collaboration mode and mid-turn effects are not inferred; the caller checks intent and affected results within current authority.',
  references: 'bind.inputs are workspace-relative path strings; each outputs.path is workspace-relative too. Input fingerprints are observed by the helper. cwd alone is absolute.',
  bind: {op: 'bind', session_id: 'native-session-id', cwd: 'absolute-workspace', epoch: 'from-status', expectedRevision: 0,
    result: 'latest authorized result', inputs: ['source.json'],
    outputs: [{path: 'summary.json', json: {'/total': 60}}, {path: 'details.csv'}],
    nextAction: 'finish and verify both affected files', canContinue: true},
  revisions: {op: 'bind', rules: 'bind rechecks inputs; changed output checks require revisionReason. Changed or removed existing inputs additionally require inputRevisions, one {path, observed, reason} per affected input. observed must exactly match its current status.inspection.inputs[].current fingerprint; for a removed reference it may be {present:false}. No extra or duplicate dispositions; each reason is nonempty and at most 2048 characters. Initial binding and added protections need no inputRevisions. Explicit dispositions are caller claims, not human authorization: check the actual user decision and affected scope first. The latest accepted dispositions, including prior fingerprints and their input epoch, remain in status.checkpoint.inputRevisions; this is not full revision history. Failed or drifting revisions preserve the prior checkpoint. Older helpers may silently rebaseline inputs. Pause and its reason survive rebinding unless an authorized resumeReason (nonempty, at most 2048 characters) explicitly lifts it. bind returns mode; status.checkpoint exposes resumeReason, not proof of authority. Inspect the installed interface.'},
  unresolved: 'Optional bind.unresolved is a list of up to 32 distinct nonempty strings, each at most 2048 characters, describing known unmet result or fact conditions. Omission inherits existing conditions; an explicit list replaces them, and removing or rewording a prior condition requires revisionReason. status.checkpoint and inspection expose them independently of matched files; any remaining condition prevents verified-local and successful retirement. canContinue means safe authorized work remains, not that the gap is resolved; use false or pause for a necessary external wait. Existing pause, input freshness and bounded Stop retry rules still apply. The caller must verify the evidence or authorized scope change behind a disposition; a reason is not proof. This neither discovers undeclared gaps nor validates semantics. Older helpers do not enforce this field; retain the compatible executor for unfinished state.',
  pause: 'op=pause with current epoch/revision and reason; preserve pending work without continuation.',
  retire: 'op=retire requires verified local predicates and a resolved pause, or explicit user-cancelled disposition plus reason. Without a checkpoint, use current epoch, expectedRevision=0 and reason to retire only the receipt, including after verified exit without an end Hook. Removes only checkpoint files; does not prove task completion.',
  recovery: 'op=recover-lock with lock=state or input requires a provably dead owner. Input recovery invalidates an existing receipt because native input may have been lost. A surviving caller must replay the actual current native input before binding or continuation; do not ask for repeated user input when the host retains it. Uncertain or live ownership is preserved. Cooperating recovery callers share a .lock.recovery gate; all copies recovering the same session must honor it, or the caller must establish exclusive maintenance. A leftover gate is not automatically reclaimed, even with a dead PID: preserve it until a caller establishes quiescence and bounded maintenance authority. Normal task operations do not acquire this recovery gate.',
  resume: 'SessionStart/resume sets needsResumeReconciliation without changing the contract or pause state. New native user input enters normally; absent new input, the native caller may replay actual current retained input with recovery_epoch. Neither route resumes paused work or reconciles the saved binding automatically. Existing needsNativeReplay quarantine from real input loss remains strict. Inspect current authority, effects and writer ownership before binding. No cross-task adoption, writer lock or host permission enforcement.',
  replay: 'After input failure or recovery, replay the actual current UserPromptSubmit event through --hook UserPromptSubmit with recovery_epoch from status. The derived token binds the receipt and failure watermarks, including a missing receipt. Use null only when no receipt or failure watermark exists. A later uncaptured native input changes the token; ordinary inputs cannot silently clear quarantine. Never reconstruct missing human intent from the old checkpoint.',
  inputFailure: 'Input loss is conservatively latched outside the input lock. Unidentified input transport failure invalidates helper freshness only in the native caller working directory. Recovery acknowledges it per session. Small failure watermarks remain until the owning state directory is safely retired. If the watermark itself cannot persist, cross-process protection is unknown and the native caller must hold continuation; this helper is not a host permission barrier.',
  limits: 'Existence checks prove only existence; JSON pointers and hashes share observed file bytes, followed by a stability recheck. External writers are not locked: this is local evidence, not an atomic workspace transaction. Caller owns goal, source trust, authority, predicate adequacy and external acceptance. Native context reads only bounded metadata from the Hook-bound transcript and returns no conversation text; no extra model call.',
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
    if (process.stdin.isTTY) {
      transportFailure('interactive-stdin-not-supported: pipe one JSON object or use --help');
      return;
    }
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
module.exports = {operate, hook, assessContext, observeContext, entryGuidance};
