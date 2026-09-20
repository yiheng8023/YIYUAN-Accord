'use strict';
const {performance} = require('node:perf_hooks');
const {observeContext} = require('./task-checkpoint.cjs');
const DEFAULT_MESSAGE_BYTES = 1024 * 1024, DEFAULT_JOURNAL_BYTES = 4 * 1024 * 1024, MAX_PENDING = 64;
const text = (v) => typeof v === 'string' && v.trim().length > 0;
const positive = (v, fallback) => {
  if (v === undefined) return fallback;
  if (!Number.isSafeInteger(v) || v <= 0) throw new TypeError('positive bounded transport limits are required');
  return v;
};
const copy = (v) => JSON.parse(JSON.stringify(v));
function frozen(v) { if (v && typeof v === 'object' && !Object.isFrozen(v)) { for (const x of Object.values(v)) frozen(x); Object.freeze(v); } return v; }
function canonical(v) { if (Array.isArray(v)) return `[${v.map(canonical).join(',')}]`; if (v && typeof v === 'object') return `{${Object.keys(v).sort().map(k => `${JSON.stringify(k)}:${canonical(v[k])}`).join(',')}}`; return JSON.stringify(v); }

const CONTEXT_OBSERVATION_TOOL = frozen({
  type: 'function',
  name: 'accord_inspect_context',
  description: 'Read native context signals for this calling thread and turn before a substantial work span or continuity decision. Unknown signals are not capacity or transfer permission; avoid unchanged polling.',
  inputSchema: {type: 'object', properties: {
    maxAgeMs: {type: 'integer', minimum: 1, maximum: Number.MAX_SAFE_INTEGER,
      description: 'Maximum observation age appropriate to this work; default 30000 ms. A larger age does not make evidence newer.'},
  }, additionalProperties: false},
});

// The streams are supplied by an already-authorized owner. This object never
// spawns, initializes, discovers, authenticates, closes, or persists a host.
function createOwnedAppServerConnection(options) {
  if (!options || typeof options !== 'object' || !options.stdin || !options.stdout || typeof options.stdin.write !== 'function' || typeof options.stdout.on !== 'function' || !text(options.connectionId) || !text(options.hostVersion)) throw new TypeError('owned stdin/stdout streams and fixed connection binding are required');
  const {stdin, stdout} = options;
  const connectionId = options.connectionId, hostVersion = options.hostVersion;
  const maxMessageBytes = positive(options.maxMessageBytes, DEFAULT_MESSAGE_BYTES), maxJournalBytes = positive(options.maxJournalBytes, DEFAULT_JOURNAL_BYTES);
  const maxEntries = Math.min(MAX_PENDING, Math.max(1, Math.floor(maxJournalBytes / 32)));
  let closed = false, broken = null, input = Buffer.alloc(0), sequence = 0, nextId = 0, journalBytes = 0;
  const journal = [], pending = new Map(), inbound = [], waiters = [], listeners = new Set(), threadModels = new Map(), answeredAnchors = new WeakSet(), timers = new Set(), aborters = new Set();
  const stopTimer = (timer) => { clearTimeout(timer); timers.delete(timer); };
  function fail(reason) {
    if (broken) return;
    broken = reason instanceof Error ? reason : new Error(reason);
    for (const abort of [...aborters]) abort(broken);
    input = Buffer.alloc(0);
    listeners.clear();
    detach();
  }
  function assertLive() { if (closed) throw new Error('owned connection is closed'); if (broken) throw broken; }
  function bounded(deadline, label, install) {
    const remaining = deadline - performance.now();
    if (!Number.isFinite(deadline) || remaining > 0x7fffffff) return Promise.reject(new Error(`${label} deadline is invalid`));
    if (remaining <= 0) return Promise.reject(new Error(`${label} deadline exceeded`));
    if (aborters.size >= MAX_PENDING * 2) return Promise.reject(new Error('connection waiter limit exceeded'));
    return new Promise((resolve, reject) => {
      let done = false, cleanup = () => {};
      const finish = (error, value) => { if (done) return; done = true; stopTimer(timer); aborters.delete(abort); try { cleanup(); } catch (_) {} if (error) reject(error); else resolve(value); };
      const abort = (error) => finish(error || new Error('owned connection is unavailable'));
      const timer = setTimeout(() => finish(new Error(`${label} deadline exceeded`)), remaining);
      timers.add(timer); aborters.add(abort);
      try {
        cleanup = install(finish) || (() => {});
        if (done) cleanup();
      } catch (error) { finish(error); }
    });
  }
  function append(message, bytes) {
    if (bytes > maxJournalBytes) { fail('native JSONL frame exceeds the journal limit'); return null; }
    while (journal.length && journalBytes + bytes > maxJournalBytes) { const old = journal.shift(); journalBytes -= old.bytes; for (const [id, item] of threadModels) if (item.record === old) threadModels.delete(id); }
    const record = frozen({sequence: ++sequence, receivedAtMs: Date.now(), bytes, message: frozen(copy(message))}); journal.push(record); journalBytes += bytes; return record;
  }
  function modelFrom(message) { const r = message?.result; for (const value of [r?.model, r?.thread?.model, r?.threadSettings?.model, r?.thread?.settings?.model]) if (text(value)) return value; return null; }
  function deliverRequest(record) {
    const request = frozen({...record.message, connectionId, hostVersion});
    const index = waiters.findIndex((w) => { try { return w.predicate(request); } catch (_) { return false; } });
    if (index >= 0) waiters.splice(index, 1)[0].finish(null, request); else if (inbound.length < maxEntries) inbound.push(request); else fail('unmatched native server request limit exceeded');
  }
  function deliver(record) {
    const message = record.message, response = Object.hasOwn(message, 'id') && !Object.hasOwn(message, 'method') && (Object.hasOwn(message, 'result') !== Object.hasOwn(message, 'error'));
    if (response) {
      const entry = pending.get(String(message.id)); if (!entry) return fail('unmatched native JSON-RPC response'); pending.delete(String(message.id));
      if (entry.method === 'thread/start' || entry.method === 'thread/resume') { const threadId = message.result?.thread?.id, model = modelFrom(message); if (text(threadId) && model) { threadModels.set(threadId, {model, record}); while (threadModels.size > maxEntries) threadModels.delete(threadModels.keys().next().value); } }
      entry.finish(Object.hasOwn(message, 'error') ? new Error('native RPC returned an error') : null, message.result); return;
    }
    if (text(message.method) && Object.hasOwn(message, 'id')) return deliverRequest(record);
    if (text(message.method) && !Object.hasOwn(message, 'id')) { const event = frozen({connectionId, hostVersion, method: message.method, params: message.params}); for (const listener of [...listeners]) { try { listener(event); } catch (error) { fail(error); break; } } return; }
    fail('invalid native JSONL message');
  }
  function frame(line) { if (line.length > maxMessageBytes) return fail('native JSONL frame exceeds the message limit'); let message; try { message = JSON.parse(new TextDecoder('utf-8', {fatal: true}).decode(line)); } catch (_) { return fail('invalid native JSONL frame'); } if (!message || typeof message !== 'object' || Array.isArray(message)) return fail('invalid native JSONL message'); const record = append(message, line.length); if (record) deliver(record); }
  function onData(chunk) {
    if (closed || broken) return;
    const bytes = Buffer.isBuffer(chunk) ? chunk : Buffer.from(chunk);
    let offset = 0;
    while (offset < bytes.length) {
      const end = bytes.indexOf(10, offset);
      const piece = bytes.subarray(offset, end < 0 ? bytes.length : end);
      // Never concatenate an unbounded input chunk, even if it contains many
      // valid frames. Retain at most one bounded partial frame between chunks.
      if (input.length + piece.length > maxMessageBytes) return fail('native JSONL frame exceeds the message limit');
      let line = input.length ? Buffer.concat([input, piece]) : piece;
      if (end < 0) { input = Buffer.from(line); return; }
      input = Buffer.alloc(0);
      if (line.length && line[line.length - 1] === 13) line = line.subarray(0, line.length - 1);
      frame(line);
      if (broken) return;
      offset = end + 1;
    }
  }
  function detach() { stdout.off?.('data', onData); stdout.off?.('end', onEnd); stdout.off?.('error', onEnd); stdin.off?.('error', onInputError); }
  function onEnd() { if (!closed) fail(input.length ? 'native JSONL EOF with partial frame' : 'native JSONL EOF'); input = Buffer.alloc(0); listeners.clear(); detach(); }
  function onInputError(error) { fail(error instanceof Error ? error : 'native stdin failed'); input = Buffer.alloc(0); listeners.clear(); detach(); }
  stdout.on('data', onData); stdout.once('end', onEnd); stdout.once('error', onEnd); stdin.on?.('error', onInputError);
  function write(value, deadline, label) { assertLive(); const body = Buffer.from(JSON.stringify(value) + '\n', 'utf8'); if (body.length > maxMessageBytes) return Promise.reject(new Error('outbound JSONL frame exceeds the message limit')); return bounded(deadline, label, (finish) => { try { stdin.write(body, (error) => finish(error || null)); } catch (error) { finish(error); } }); }
  async function request(method, params, deadline) {
    assertLive(); if (!text(method) || pending.size >= MAX_PENDING) throw new Error('native request is unavailable');
    const id = `accord-owned:${++nextId}`; let entry; const reply = bounded(deadline, 'native request', (finish) => { entry = {method, finish}; pending.set(id, entry); return () => pending.delete(id); }); reply.catch(() => {});
    if (!entry) return reply;
    try { await write({id, method, params}, deadline, 'native request write'); } catch (error) { entry.finish(error); throw error; } return reply;
  }
  function notify(method, params, deadline) { assertLive(); if (!text(method)) return Promise.reject(new Error('native notification is unavailable')); return write({method, params}, deadline, 'native notification write'); }
  function terminalMatches(message, threadId, turnId) { return message?.method === 'turn/completed' && message.params?.threadId === threadId && message.params?.turn?.id === turnId; }
  function waitTerminal(threadId, turnId, deadline) { assertLive(); for (const record of journal) if (terminalMatches(record.message, threadId, turnId)) return Promise.resolve(frozen(copy(record.message))); return bounded(deadline, 'native terminal', (finish) => { const listener = (event) => { if (terminalMatches(event, threadId, turnId)) finish(null, frozen({method: event.method, params: event.params})); }; listeners.add(listener); return () => listeners.delete(listener); }); }
  function receiveRequest(predicate, deadline) { assertLive(); if (typeof predicate !== 'function') return Promise.reject(new Error('request predicate is required')); const index = inbound.findIndex((value) => { try { return predicate(value); } catch (_) { return false; } }); if (index >= 0) return Promise.resolve(inbound.splice(index, 1)[0]); if (waiters.length >= maxEntries) return Promise.reject(new Error('server request waiter limit exceeded')); return bounded(deadline, 'server request', (finish) => { const waiter = {predicate, finish}; waiters.push(waiter); return () => { const i = waiters.indexOf(waiter); if (i >= 0) waiters.splice(i, 1); }; }); }
  function requestAnchor(request) {
    if (!request || request.connectionId !== connectionId || request.hostVersion !== hostVersion ||
        request.method !== 'item/tool/call' || !Object.hasOwn(request, 'id')) return null;
    const {connectionId: ignoredConnection, hostVersion: ignoredVersion, ...payload} = request;
    return journal.find(record => record.message.method === 'item/tool/call' &&
      canonical(record.message) === canonical(payload)) || null;
  }
  function respondOwned(nativeRequest, response, deadline) {
    assertLive();
    const remaining = deadline - performance.now();
    if (!Number.isFinite(deadline) || remaining <= 0 || remaining > 0x7fffffff) return Promise.reject(new Error('proposal response deadline is invalid or exceeded'));
    const anchor = requestAnchor(nativeRequest);
    if (!anchor || !response || response.id !== nativeRequest.id || answeredAnchors.has(anchor)) return Promise.reject(new Error('proposal response is not available'));
    answeredAnchors.add(anchor);
    return write(response, deadline, 'proposal response write');
  }
  function proposalChannel(nativeRequest, current) { if (typeof current !== 'function') throw new TypeError('proposal current reader is required'); return frozen({
    subscribe(listener, suppliedAnchor) { assertLive(); const anchor = requestAnchor(nativeRequest); if (!anchor) throw new Error('proposal anchor is unavailable'); if (typeof listener !== 'function' || requestAnchor(suppliedAnchor) !== anchor) throw new Error('proposal anchor differs from request'); const start = journal.indexOf(anchor) + 1; const live = (event) => listener(event); listeners.add(live); try { for (let i = start; i < journal.length; i++) { const message = journal[i].message; if (text(message.method) && !Object.hasOwn(message, 'id')) live(frozen({connectionId, hostVersion, method: message.method, params: message.params})); } } catch (error) { listeners.delete(live); throw error; } return () => listeners.delete(live); },
    respond: (response, deadline) => respondOwned(nativeRequest, response, deadline),
    current(deadline) { assertLive(); if (!Number.isFinite(deadline) || performance.now() >= deadline) return Promise.reject(new Error('proposal current deadline exceeded')); return Promise.resolve(current(deadline)); },
  }); }
  function context(threadId, turnId, maxAgeMs) { if (closed || broken) return frozen({state: 'unknown', reason: 'native-connection-unavailable', sourceReleaseAllowed: false}); const binding = threadModels.get(threadId); if (!binding || !journal.includes(binding.record)) return frozen({state: 'unknown', reason: 'thread-model-response-unavailable', sourceReleaseAllowed: false}); const events = journal.filter((r) => text(r.message.method) && !Object.hasOwn(r.message, 'id')).map((r) => frozen({receivedAtMs: r.receivedAtMs, event: r.message})); return frozen(observeContext({binding: {connectionId, threadId, hostVersion, model: binding.model}, turnId, connected: true, maxAgeMs, events})); }
  async function replyContext(nativeRequest, deadline) {
    assertLive();
    const anchor = requestAnchor(nativeRequest), params = anchor?.message.params;
    if (!anchor || params?.tool !== CONTEXT_OBSERVATION_TOOL.name || params.namespace != null ||
        !text(params.threadId) || !text(params.turnId)) throw new Error('exact owned context request is required');
    const args = params.arguments;
    const valid = args && typeof args === 'object' && !Array.isArray(args) &&
      Object.keys(args).every(key => key === 'maxAgeMs') &&
      (!Object.hasOwn(args, 'maxAgeMs') || Number.isSafeInteger(args.maxAgeMs) && args.maxAgeMs > 0);
    const observation = valid ? context(params.threadId, params.turnId, args.maxAgeMs ?? 30000) :
      frozen({state: 'unknown', reason: 'invalid-context-arguments', sourceReleaseAllowed: false});
    const payload = frozen({schema: 'yiyuan-accord-native-context-reply/v1', observation,
      claimLimit: 'Current native-call signals only. No task text, authorization, semantic integrity, forecast, checkpoint change or transfer is supplied.'});
    const response = {id: nativeRequest.id, result: {success: Boolean(valid),
      contentItems: [{type: 'inputText', text: JSON.stringify(payload)}]}};
    if (nativeRequest.jsonrpc === '2.0') response.jsonrpc = '2.0';
    await respondOwned(nativeRequest, response, deadline);
    return payload;
  }
  function close() { if (closed) return; closed = true; input = Buffer.alloc(0); detach(); fail('owned connection is closed'); listeners.clear(); inbound.length = 0; journal.length = 0; journalBytes = 0; threadModels.clear(); for (const timer of [...timers]) stopTimer(timer); }
  return frozen({transport: frozen({connectionId, hostVersion, request, notify, waitTerminal}), receiveRequest, proposalChannel, context, replyContext, close});
}
module.exports = {createOwnedAppServerConnection, CONTEXT_OBSERVATION_TOOL};
