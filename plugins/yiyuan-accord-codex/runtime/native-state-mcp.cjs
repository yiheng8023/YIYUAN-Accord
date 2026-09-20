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
const CLAIM_LIMIT = 'Native-call metadata is received context, not authentication or permission. The workspace is caller-selected. Saved state and canContinue do not prove current intent, freshness, completion, takeover or control of this thread. No state mutation or task dispatch is performed.';
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
  const meta = params._meta;
  const native = record(meta) && meta['x-codex-turn-metadata'];
  if (!record(native) || !text(meta.callId, 1024) || !text(native.thread_id)
      || !text(native.session_id) || !text(native.turn_id)) {
    return {isError: true, value: unavailable('native-call-metadata-unavailable')};
  }
  const source = {kind: 'codex-mcp-request-metadata', callId: meta.callId,
    threadId: native.thread_id, sessionTreeId: native.session_id, turnId: native.turn_id,
    model: text(native.model, 200) ? native.model : null,
    hostVersion: text(native.codex_version, 100) ? native.codex_version : null};
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
      return result(id, {tools: [TOOL]});
    }
    if (request.method === 'tools/call') {
      if (!record(request.params) || request.params.name !== TOOL.name) {
        return error(id, -32602, 'Unknown tool');
      }
      const inspected = inspectNativeState(request.params);
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
module.exports = {inspectNativeState, createHandler, serve};
