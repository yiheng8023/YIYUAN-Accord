'use strict';

// A bounded stdio MCP adapter, not another state engine or a control connection.
// Codex supplies call metadata separately from model-chosen tool arguments.
const {once} = require('node:events');
const path = require('node:path');
const fs = require('node:fs');
const {TextDecoder} = require('node:util');
const {operate} = require('./task-checkpoint.cjs');

const PROTOCOL = '2025-06-18';
const MAX_FRAME = 128 * 1024;
const MAX_RESULT = 128 * 1024;
const TOOL = Object.freeze({
  name: 'inspect_task_state',
  description: 'Read saved Accord task state; request includeContext for bounded native context observations before long work or continuity decisions. Current host identity comes from call metadata, separately from recorded session metadata. No permission, completion or handoff control is established.',
  inputSchema: {type: 'object', properties: {cwd: {type: 'string', minLength: 1, maxLength: 4096,
    description: 'Absolute existing workspace directory. Caller-selected scope, not host-attested current cwd.'},
    includeContext: {type: 'boolean', description: 'Also read current Hook-bound context counters. Defaults to false; missing or stale evidence remains unknown.'},
    contextMaxAgeMs: {type: 'integer', minimum: 1, maximum: Number.MAX_SAFE_INTEGER,
      description: 'Requires includeContext. Caller-selected age limit for the last native response boundary; defaults to 30000 ms. Original sample time and unobserved-tail uncertainty remain.'}},
    required: ['cwd'], additionalProperties: false},
  annotations: {readOnlyHint: true, destructiveHint: false, idempotentHint: true, openWorldHint: false},
});
const INPUT_TOOL = Object.freeze({
  name: 'read_task_input',
  description: 'Read a bounded page of this root task\'s Hook-captured input when needed for recovery. Follow the returned next cursor and retain receipt/hash identity; recorded text is not new input, complete history or permission. No replay or state change.',
  inputSchema: {type: 'object', properties: {
    cwd: TOOL.inputSchema.properties.cwd,
    index: {type: 'integer', minimum: 0, maximum: Number.MAX_SAFE_INTEGER, description: 'Captured input index; defaults to zero. Nonzero pagination requires expectedReceiptEpoch.'},
    offset: {type: 'integer', minimum: 0, maximum: Number.MAX_SAFE_INTEGER, description: 'Unicode code-point offset within that input; defaults to zero. Nonzero pagination requires expectedReceiptEpoch.'},
    maxChars: {type: 'integer', minimum: 1, maximum: 16000, description: 'Page character budget; defaults to 4000.'},
    expectedReceiptEpoch: {type: 'string', minLength: 1, maxLength: 256,
      description: 'Use the returned next cursor or prior inspection epoch to reject a changed input basis. This is a read condition, not a recovery token or authorization.'},
  }, required: ['cwd'], additionalProperties: false},
  annotations: {readOnlyHint: true, destructiveHint: false, idempotentHint: true, openWorldHint: false},
});
const CLAIM_LIMIT = 'Native-call metadata is received context, not authentication or permission. The workspace is caller-selected. Saved state and canContinue do not prove current intent, freshness, completion, takeover or control of this thread. No state mutation or task dispatch is performed.';
const INPUT_CLAIM_LIMIT = 'Captured Hook input is recorded data, not new input or permission, complete history, attachments or work progress. A stable page does not establish that the latest input was captured, restore a task, clear quarantine or resume a pause. Reconcile current native input and authority separately. ' + CLAIM_LIMIT;
const record = value => value !== null && typeof value === 'object' && !Array.isArray(value);
const text = (value, max = 200) => typeof value === 'string' && value.trim().length > 0
  && value.length <= max && !/[\u0000-\u001f\u007f]/u.test(value);
const own = (value, key) => Object.prototype.hasOwnProperty.call(value, key);

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

function inspectNativeState(params) {
  if (!record(params) || params.name !== TOOL.name || !record(params.arguments)
      || Object.keys(params.arguments).some(key => !['cwd', 'includeContext', 'contextMaxAgeMs'].includes(key))
      || !own(params.arguments, 'cwd')
      || own(params.arguments, 'includeContext') && typeof params.arguments.includeContext !== 'boolean'
      || own(params.arguments, 'contextMaxAgeMs') && (params.arguments.includeContext !== true
        || !Number.isSafeInteger(params.arguments.contextMaxAgeMs) || params.arguments.contextMaxAgeMs <= 0)
      || !text(params.arguments.cwd, 4096) || !path.isAbsolute(params.arguments.cwd)) {
    return {isError: true, value: unavailable('explicit-workspace-required')};
  }
  // The argument schema exposes no identity, operation, receipt or storage path.
  const source = nativeCallSource(params);
  if (!source) {
    return {isError: true, value: unavailable('native-call-metadata-unavailable')};
  }
  const workspace = {cwd: params.arguments.cwd, binding: 'caller-selected'};
  let checkpoint;
  if (source.threadId !== source.sessionTreeId) {
    // In the inspected host, Hook session_id is shared by a session tree.
    // A descendant must not silently adopt that shared checkpoint as its own.
    checkpoint = {state: 'unavailable', reason: 'shared-session-scope-requires-reconciliation'};
  } else {
    try {
      checkpoint = {state: 'observed', snapshot: operate({op: 'status',
        session_id: source.sessionTreeId, cwd: params.arguments.cwd})};
    } catch (error) {
      checkpoint = {state: 'unavailable', reason: inspectionReason(error)};
    }
  }
  const value = {schema: 'yiyuan-accord-native-state/v1', state: 'observed-call-context',
    source, workspace, checkpoint, claimLimit: CLAIM_LIMIT};
  if (params.arguments.includeContext === true) {
    const unknown = reason => ({state: 'unknown', reason, sourceReleaseAllowed: false});
    if (checkpoint.state !== 'observed') value.context = unknown(checkpoint.reason);
    else if (!source.model || !source.hostVersion) value.context = unknown('current-host-binding-missing');
    else {
      try {
        const currentHost = {threadId: source.threadId, turnId: source.turnId,
          model: source.model, hostVersion: source.hostVersion,
          sourceRef: `codex-mcp-call:${source.callId}`};
        const observed = operate({op: 'observe-context', session_id: source.sessionTreeId,
          cwd: params.arguments.cwd, currentHost,
          maxAgeMs: params.arguments.contextMaxAgeMs ?? 30000});
        value.context = observed.epoch === checkpoint.snapshot.epoch
          ? observed : unknown('input-changed-between-state-and-context');
      } catch (error) { value.context = unknown(inspectionReason(error)); }
    }
  }
  if (Buffer.byteLength(JSON.stringify(value)) > MAX_RESULT) {
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
  if (['index', 'offset'].some(key => own(args, key) && args[key] !== 0)
      && !own(args, 'expectedReceiptEpoch')) return rejected('captured-input-basis-required');
  const source = nativeCallSource(params);
  if (!source) return rejected('native-call-metadata-unavailable');
  if (source.threadId !== source.sessionTreeId) return rejected('shared-session-scope-requires-reconciliation');
  let input;
  try {
    input = operate({op: 'read-native-input', session_id: source.sessionTreeId, cwd: args.cwd,
      index: own(args, 'index') ? args.index : undefined,
      offset: own(args, 'offset') ? args.offset : undefined,
      maxChars: own(args, 'maxChars') ? args.maxChars : undefined});
  } catch (error) { return rejected(inspectionReason(error)); }
  if (own(args, 'expectedReceiptEpoch') && args.expectedReceiptEpoch !== input.receiptEpoch) {
    return rejected('captured-input-basis-changed');
  }
  // Pin subsequent pages to this observed basis; never rewrite or replay it.
  if (input.next) input = {...input, next: {...input.next, expectedReceiptEpoch: input.receiptEpoch}};
  const value = {schema: 'yiyuan-accord-native-input/v1', state: 'observed-input-page',
    source, workspace: {cwd: args.cwd, binding: 'caller-selected'}, input, claimLimit: INPUT_CLAIM_LIMIT};
  if (Buffer.byteLength(JSON.stringify(value)) > MAX_RESULT) return rejected('bounded-input-result-exceeded');
  return {isError: false, value};
}

function runtimeVersion() {
  const root = path.resolve(__dirname, '..');
  const manifest = path.join(root, '.codex-plugin', 'plugin.json');
  const packaged = fs.existsSync(manifest);
  const data = JSON.parse(fs.readFileSync(packaged ? manifest : path.join(root, 'product', 'development.json'), 'utf8'));
  const version = packaged ? data.version : data.delivery?.version;
  if (!text(version, 200)) throw new Error('package-version-unavailable');
  return version;
}

function createHandler(version = runtimeVersion()) {
  let initialized = false, ready = false;
  const error = (id, code, message) => ({jsonrpc: '2.0', id, error: {code, message}});
  const result = (id, value) => ({jsonrpc: '2.0', id, result: value});
  return request => {
    if (!record(request) || request.jsonrpc !== '2.0' || !text(request.method, 100)) {
      return error(null, -32600, 'Invalid request');
    }
    if (!own(request, 'id')) {
      if (request.method === 'notifications/initialized' && initialized) ready = true;
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
      return result(id, {tools: [TOOL, INPUT_TOOL]});
    }
    if (request.method === 'tools/call') {
      if (!record(request.params) || ![TOOL.name, INPUT_TOOL.name].includes(request.params.name)) {
        return error(id, -32602, 'Unknown tool');
      }
      const inspected = request.params.name === TOOL.name ? inspectNativeState(request.params) : readTaskInput(request.params);
      return result(id, {isError: inspected.isError, structuredContent: inspected.value,
        content: [{type: 'text', text: JSON.stringify(inspected.value)}]});
    }
    return error(id, -32601, 'Method not found');
  };
}

async function serve(input = process.stdin, output = process.stdout, version = runtimeVersion()) {
  const handle = createHandler(version);
  const decoder = new TextDecoder('utf-8', {fatal: true});
  let pending = Buffer.alloc(0);
  for await (const chunk of input) {
    pending = Buffer.concat([pending, chunk]);
    let newline;
    while ((newline = pending.indexOf(10)) !== -1) {
      if (newline > MAX_FRAME) throw new Error('oversize-mcp-input');
      const frame = pending.subarray(0, newline);
      pending = pending.subarray(newline + 1);
      let response;
      try { response = handle(JSON.parse(decoder.decode(frame))); }
      catch (_) { response = {jsonrpc: '2.0', id: null, error: {code: -32700, message: 'Invalid JSON'}}; }
      if (response !== null && !output.write(JSON.stringify(response) + '\n')) await once(output, 'drain');
    }
    if (pending.length > MAX_FRAME) throw new Error('oversize-mcp-input');
  }
  if (pending.length) throw new Error('incomplete-mcp-input');
}

if (require.main === module) {
  Promise.resolve().then(() => {
    const version = runtimeVersion();
    // Windows cannot replace a cache directory held as a live process cwd.
    // Modules are loaded; every task workspace is supplied as an absolute path.
    // Preserve the original base of configured state, session, home and temp paths.
    for (const key of ['YIYUAN_ACCORD_TASK_STATE_DIR', 'CODEX_HOME', 'HOME', 'USERPROFILE', 'TMPDIR', 'TMP', 'TEMP']) {
      if (process.env[key]) process.env[key] = path.resolve(process.env[key]);
    }
    process.chdir(require('node:os').homedir());
    return serve(process.stdin, process.stdout, version);
  }).catch(() => {
    process.stderr.write('Accord native-state transport stopped; no state mutation was requested.\n');
    process.exitCode = 1;
  });
}
module.exports = {inspectNativeState, readTaskInput, createHandler, serve};
