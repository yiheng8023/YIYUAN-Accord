'use strict';

// A bounded stdio MCP adapter, not another state engine or a control connection.
// Codex supplies call metadata separately from model-chosen tool arguments.
const {once} = require('node:events');
const path = require('node:path');
const {TextDecoder} = require('node:util');
const {operate} = require('./task-checkpoint.cjs');

const PROTOCOL = '2025-06-18';
const MAX_FRAME = 128 * 1024;
const MAX_RESULT = 128 * 1024;
const TOOL = Object.freeze({
  name: 'inspect_task_state',
  description: 'Read the saved Accord state for the calling Codex thread at an explicitly selected workspace. Inspect pauses, unresolved work and recovery conditions before relying on saved state. This does not establish permission, current-input freshness, completion or a handoff control connection.',
  inputSchema: {type: 'object', properties: {cwd: {type: 'string', minLength: 1, maxLength: 4096,
    description: 'Absolute existing workspace directory. Caller-selected scope, not host-attested current cwd.'}},
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

function inspectNativeState(params) {
  if (!record(params) || params.name !== TOOL.name || !record(params.arguments)
      || Object.keys(params.arguments).length !== 1 || !own(params.arguments, 'cwd')
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
      const code = error?.code || error?.message;
      checkpoint = {state: 'unavailable', reason: typeof code === 'string'
        && /^[A-Za-z][A-Za-z0-9_-]{0,95}$/.test(code) ? code : 'state-inspection-unavailable'};
    }
  }
  const value = {schema: 'yiyuan-accord-native-state/v1', state: 'observed-call-context',
    source, workspace, checkpoint, claimLimit: CLAIM_LIMIT};
  if (Buffer.byteLength(JSON.stringify(value)) > MAX_RESULT) {
    return {isError: true, value: unavailable('bounded-state-result-exceeded')};
  }
  return {isError: false, value};
}

function createHandler() {
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
        serverInfo: {name: 'yiyuan-accord-native-state', version: '3.3.0-dev.1'}});
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

async function serve(input = process.stdin, output = process.stdout) {
  const handle = createHandler();
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
  serve().catch(() => {
    process.stderr.write('Accord native-state transport stopped; no state mutation was requested.\n');
    process.exitCode = 1;
  });
}
module.exports = {inspectNativeState, createHandler, serve};
