'use strict';

const crypto = require('node:crypto');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');

const HEAD_BYTES = 64 * 1024;
const TAIL_BYTES = 1024 * 1024;
const MAX_TAIL_BYTES = 16 * TAIL_BYTES;
// A receipt-located origin permits a separate cumulative source-verification
// budget. It is neither an anonymous history search nor model capacity.
const MAX_RETAINED_BYTES = 32 * TAIL_BYTES;
const MAX_NATIVE_MEDIA_BYTES = 8 * 1024 * 1024; // Existing native-input/receipt byte budget.
const UUID = '[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}';
const ROLLOUT_NAME = new RegExp(
  `^rollout-(\\d{4})-(\\d{2})-(\\d{2})T\\d{2}-\\d{2}-\\d{2}-(${UUID})(?:_(${UUID}))?\\.jsonl$`,
  'i',
);
const CURRENT_HOST_FIELDS = ['threadId', 'turnId', 'model', 'hostVersion', 'sourceRef'];

function text(value) {
  return typeof value === 'string' && value.length > 0;
}

function boundedText(value, limit) {
  return text(value) && value.trim().length > 0 && value.length <= limit &&
    !/[\u0000-\u001f\u007f]/u.test(value);
}

function currentHost(binding, options) {
  if (!Object.prototype.hasOwnProperty.call(options, 'currentHost')) {
    return {host: null, reason: null};
  }
  const host = options.currentHost;
  if (!host || typeof host !== 'object' || Array.isArray(host) ||
      Object.keys(host).length !== CURRENT_HOST_FIELDS.length ||
      !CURRENT_HOST_FIELDS.every((key) => Object.prototype.hasOwnProperty.call(host, key)) ||
      !boundedText(host.threadId, 200) || !boundedText(host.turnId, 200) ||
      !boundedText(host.model, 200) || !boundedText(host.hostVersion, 100) ||
      !boundedText(host.sourceRef, 2048)) {
    return {host: null, reason: 'current-host-fields-invalid'};
  }
  if (host.threadId !== binding.sessionId) return {host: null, reason: 'current-host-thread-mismatch'};
  if (host.turnId !== binding.turnId) return {host: null, reason: 'current-host-turn-mismatch'};
  if (host.model !== binding.model) return {host: null, reason: 'current-host-model-mismatch'};
  return {host, reason: null};
}

function integer(value) {
  return Number.isSafeInteger(value) && value >= 0;
}

function canonical(value) {
  if (Array.isArray(value)) return `[${value.map(canonical).join(',')}]`;
  if (value && typeof value === 'object') {
    return `{${Object.keys(value).sort().map((key) => `${JSON.stringify(key)}:${canonical(value[key])}`).join(',')}}`;
  }
  return JSON.stringify(value);
}

function sha(value) {
  return crypto.createHash('sha256').update(canonical(value)).digest('hex');
}

function empty(reason) {
  return {
    state: 'unknown', reason, conditions: null,
    lastResponseTokens: null, lastResponseScope: null,
    cumulativeTokens: null, cumulativeScope: null,
    windowTokens: null, observedAtMs: null, validUntilMs: null,
    observationId: null, sourceRef: null, recordedHostVersion: null, hostSourceRef: null,
  };
}

function samePath(left, right) {
  const a = path.resolve(left);
  const b = path.resolve(right);
  return process.platform === 'win32' ? a.toLowerCase() === b.toLowerCase() : a === b;
}

function realPath(file) {
  // Native Windows Hooks may supply the extended-length path namespace.
  return process.platform === 'win32' ? fs.realpathSync.native(file) : fs.realpathSync(file);
}

function statIdentity(stat) {
  return {
    dev: stat.dev.toString(), ino: stat.ino.toString(), size: stat.size.toString(),
    mtimeNs: stat.mtimeNs.toString(), ctimeNs: stat.ctimeNs.toString(), mode: stat.mode.toString(),
  };
}

function readSlice(fd, position, length) {
  const buffer = Buffer.alloc(length);
  const read = fs.readSync(fd, buffer, 0, length, position);
  if (read !== length) throw new Error('transcript-short-read');
  return buffer.subarray(0, read);
}

function completeLines(buffer, baseOffset, dropLeadingPartial) {
  let start = 0;
  if (dropLeadingPartial) {
    const newline = buffer.indexOf(0x0a);
    if (newline === -1) return [];
    start = newline + 1;
  }
  const rows = [];
  while (start < buffer.length) {
    const newline = buffer.indexOf(0x0a, start);
    if (newline === -1) break;
    let end = newline;
    if (end > start && buffer[end - 1] === 0x0d) end--;
    if (end > start) rows.push({offset: baseOffset + start, bytes: buffer.subarray(start, end)});
    start = newline + 1;
  }
  return rows;
}

function hasUnterminatedRecord(buffer) {
  const lastNewline = buffer.lastIndexOf(0x0a);
  return buffer.subarray(lastNewline + 1).toString('utf8').trim().length > 0;
}

function parseRow(row) {
  try {
    return JSON.parse(row.bytes.toString('utf8'));
  } catch (_) {
    return null;
  }
}

function defaultSessionsRoot() {
  const codexHome = text(process.env.CODEX_HOME) ? process.env.CODEX_HOME : path.join(os.homedir(), '.codex');
  return path.join(codexHome, 'sessions');
}

function wrappedImage(content) {
  if (!Array.isArray(content) || content.length < 4 || (content.length - 1) % 3 ||
      content[0]?.type !== 'input_text' || typeof content[0].text !== 'string') return false;
  for (let index = 1; index < content.length; index += 3) {
    if (content[index]?.type !== 'input_text' ||
        !/^<image name=\[Image #[1-9]\d*\] path="[^"\u0000-\u001f]+">$/u.test(content[index].text || '') ||
        content[index + 1]?.type !== 'input_image' || content[index + 2]?.type !== 'input_text' ||
        content[index + 2].text !== '</image>') return false;
  }
  return true;
}

// Source shape only: host ambient metadata grants no human authority. A user
// typing the same wrapper text does not qualify for this narrow capture gap.
function typedAmbient(payload, turnId) {
  const metadata = payload?.internal_chat_message_metadata_passthrough;
  return metadata?.turn_id === turnId && Array.isArray(metadata.content_item_kinds) &&
    metadata.content_item_kinds.length === 1 && metadata.content_item_kinds[0] === 'additional_content.codex_apps_open_page';
}

// Runtime context is a source classification, never human authorization or a
// disposition of its continuation/budget/update meaning. Keep every raw record.
// requires-review names caller interpretation duty, not a new stop/clear state.
function goalRuntimeContext(payload, turnId) {
  const metadata = payload?.internal_chat_message_metadata_passthrough;
  const content = payload?.content, kinds = metadata?.content_item_kinds;
  const attribution = metadata?.content_item_metadata;
  if (payload?.type !== 'message' || payload.role !== 'user' || metadata?.turn_id !== turnId ||
      !Array.isArray(content) || content.length !== 1 || content[0]?.type !== 'input_text' ||
      typeof content[0].text !== 'string' || !Array.isArray(kinds) || kinds.length !== 1 ||
      kinds[0] !== 'goal.internal_context' || !Array.isArray(attribution) || attribution.length !== 1 ||
      canonical(attribution[0]?.provenance) !== canonical({type: 'harness', hook: false})) return false;
  const opening = '<codex_internal_context source="goal">', closing = '</codex_internal_context>';
  const value = content[0].text;
  if (!value.startsWith(opening) || !value.endsWith(closing)) return false;
  const body = value.slice(opening.length, -closing.length);
  return Boolean(body.trim()) && !/<\/?codex_internal_context\b/u.test(body);
}

// Resolve only an already captured input, not a global host flattening rule.
// A candidate text projection must match the bound Hook/source hash exactly.
function multipartText(payload, binding, expectedHash) {
  const content = payload?.content, metadata = payload?.internal_chat_message_metadata_passthrough;
  if (payload?.type !== 'message' || payload.role !== 'user' ||
      !Array.isArray(content) || content.length < 2 ||
      !content.every(item => item?.type === 'input_text' && typeof item.text === 'string') ||
      metadata?.turn_id !== binding?.turnId || !Array.isArray(metadata?.content_item_kinds) ||
      metadata.content_item_kinds.length !== content.length ||
      !metadata.content_item_kinds.every(kind => kind === 'user.text') ||
      !/^[a-f0-9]{64}$/.test(expectedHash || '')) return null;
  const parts = content.map(item => item.text);
  for (const separator of ['', '\n']) {
    const prompt = parts.join(separator);
    if (crypto.createHash('sha256').update(prompt).digest('hex') === expectedHash) return {prompt};
  }
  return null;
}

function inputHash(line, binding, expectedHash) {
  const payload = line?.type === 'response_item' ? line.payload : null;
  const content = payload?.content;
  const multiText = multipartText(payload, binding, expectedHash);
  if (multiText) return crypto.createHash('sha256').update(multiText.prompt).digest('hex');
  if (payload?.type === 'message' && payload.role === 'user' && wrappedImage(content)) {
    return crypto.createHash('sha256').update(content[0].text).digest('hex');
  }
  return payload?.type === 'message' && payload.role === 'user' &&
    Array.isArray(content) && content.some(item => item?.type === 'input_text') &&
    content.filter(item => item?.type === 'input_text').every(item => typeof item.text === 'string')
    ? crypto.createHash('sha256').update(content.filter(item => item?.type === 'input_text')
      .map(item => item.text).join('\n')).digest('hex') : null;
}

function pngData(value) {
  const prefix = 'data:image/png;base64,';
  if (typeof value !== 'string' || !value.startsWith(prefix)) return null;
  const encoded = value.slice(prefix.length);
  if (!encoded || encoded.length % 4 || encoded.length > Math.ceil(MAX_NATIVE_MEDIA_BYTES / 3) * 4 ||
      !/^[A-Za-z0-9+/]+={0,2}$/u.test(encoded)) return null;
  const bytes = Buffer.from(encoded, 'base64');
  if (bytes.length > MAX_NATIVE_MEDIA_BYTES || bytes.length < 8 || bytes.toString('base64') !== encoded ||
      !bytes.subarray(0, 8).equals(Buffer.from([137, 80, 78, 71, 13, 10, 26, 10]))) return null;
  // Verify the encoding, MIME signature and byte identity, not pixels/meaning.
  // The native image consumer owns PNG decoding; no custom PNG parser here.
  return {data: encoded, mimeType: 'image/png', bytes: bytes.length,
    sha256: crypto.createHash('sha256').update(bytes).digest('hex')};
}

function contentEvidence(payload, binding, expectedHash) {
  const content = payload?.content;
  const singleText = Array.isArray(content) && content.length === 1 &&
    content[0]?.type === 'input_text' && typeof content[0].text === 'string';
  const multiText = multipartText(payload, binding, expectedHash);
  if (payload?.type !== 'message' || !singleText && !multiText && !wrappedImage(content)) return {supported: false, parts: []};
  const parts = [];
  let mediaBytes = 0;
  for (let partIndex = 0; partIndex < content.length; partIndex++) {
    const item = content[partIndex];
    if (item.type === 'input_text') parts.push({partIndex, type: 'text', textChars: [...item.text].length,
      sha256: crypto.createHash('sha256').update(item.text).digest('hex')});
    else {
      const image = pngData(item.image_url);
      if (!image || (mediaBytes += image.bytes) > MAX_NATIVE_MEDIA_BYTES) return {supported: false, parts};
      const {data, ...description} = image;
      parts.push({partIndex, type: 'image', ...description, encodingScope: 'strict-base64-png-signature'});
    }
  }
  return {supported: true, parts, prompt: multiText ? multiText.prompt : content[0].text};
}

function completedCompaction(line, sessionId, turnId) {
  const payload = line?.type === 'event_msg' ? line.payload : null;
  return payload?.type === 'item_completed' && payload.thread_id === sessionId &&
    payload.turn_id === turnId && payload.item?.type === 'ContextCompaction' &&
    boundedText(payload.item.id, 200);
}

// RFC 7386 tools-only delta: the directory is observation, not permission.
function toolsDelta(line) {
  const p = line?.payload, state = p?.state, tools = state?.tools;
  const object = value => value !== null && typeof value === 'object' && !Array.isArray(value);
  return line?.type === 'world_state' && object(p) && p.full === false &&
    Object.keys(p).sort().join(',') === 'full,state' && object(state) &&
    Object.keys(state).join(',') === 'tools' && (tools === null || object(tools) &&
      Object.values(tools).every(value => value === null || typeof value === 'string'));
}

function environmentDelta(line) {
  const p = line?.payload, state = p?.state, env = state?.environments;
  return line?.type === 'world_state' && p?.full === false &&
    Object.keys(p).sort().join(',') === 'full,state' && state &&
    Object.keys(state).join(',') === 'environments' && env && typeof env === 'object' && !Array.isArray(env);
}

// Historical output before a late first input stays inside the verified prefix.
// This is not the benign-append policy: metadata here grants no new authority.
function lateOriginOutput(row, binding) {
  const line = parseRow(row), value = line?.payload;
  if (toolsDelta(line)) return true;
  if (Object.hasOwn(value || {}, 'turn_id') && value.turn_id !== binding.turnId ||
      Object.hasOwn(value || {}, 'thread_id') && value.thread_id !== binding.sessionId) return false;
  if (retryRecordIsBenign(row)) return true;
  if (line?.type === 'event_msg') return value?.type === 'item_completed' &&
    value.thread_id === binding.sessionId && value.turn_id === binding.turnId &&
    ['Reasoning', 'AgentMessage', 'SubAgentActivity', 'CommandExecution', 'McpToolCall', 'FileChange'].includes(value.item?.type) &&
    boundedText(value.item.id, 200) && integer(value.started_at_ms) && integer(value.completed_at_ms) &&
    value.completed_at_ms >= value.started_at_ms;
  if (line?.type === 'response_item') return value?.type === 'agent_message' &&
    !Object.hasOwn(value, 'role') && boundedText(value.id, 200) &&
    boundedText(value.author, 200) && boundedText(value.recipient, 200) &&
    value.internal_chat_message_metadata_passthrough?.turn_id === binding.turnId &&
    Array.isArray(value.content) && value.content.length > 0 &&
    value.content.every(item => ['input_text', 'encrypted_content'].includes(item?.type));
  if (line?.type === 'inter_agent_communication_metadata') return value?.trigger_turn === false &&
    Object.keys(value).join(',') === 'trigger_turn';
  return environmentDelta(line);
}

// Only the verified host-authored reasoning control is supported. It is
// ordered source evidence, never a human instruction or authority to act.
// The 200-character bound is local; callers must review custom value semantics.
function configurationUpdate(line) {
  const p = line?.payload, m = line?.metadata;
  return line?.type === 'response_item' && p?.type === 'configuration_update' &&
    Object.keys(p).sort().join(',') === 'reasoning,type' &&
    p.reasoning && typeof p.reasoning === 'object' && !Array.isArray(p.reasoning) &&
    Object.keys(p.reasoning).join(',') === 'effort' &&
    boundedText(p.reasoning.effort, 200) &&
    m && typeof m === 'object' && !Array.isArray(m) &&
    Object.keys(m).sort().join(',') === 'client_authored,harness_authored_configuration' &&
    m.client_authored === false && m.harness_authored_configuration === true;
}

function retryOrigin(rows, binding, promptHash) {
  for (let index = 0; index + 1 < rows.length; index++) {
    const line = parseRow(rows[index]);
    if (line?.type !== 'turn_context' || line.payload?.turn_id !== binding.turnId) continue;
    const prior = rows.slice(0, index).map(parseRow).findLast(item =>
      item?.type === 'event_msg' && item.payload?.type === 'task_started' && item.payload.turn_id === binding.turnId);
    const root = prior?.payload.root_turn_id || line.payload.root_turn_id;
    const contextAt = Date.parse(line.timestamp);
    for (let next = index + 1; next < rows.length; next++) {
      const candidate = parseRow(rows[next]);
      if (candidate?.type === 'response_item' && candidate.payload?.type === 'message' &&
          candidate.payload.role === 'developer') continue;
      if (candidate?.type === 'response_item' && candidate.payload?.type === 'message' &&
          candidate.payload.role === 'user' && (typedAmbient(candidate.payload, binding.turnId) ||
            goalRuntimeContext(candidate.payload, binding.turnId))) continue;
      if (candidate?.type === 'event_msg' && candidate.payload?.type === 'token_count' &&
          (!Object.hasOwn(candidate.payload, 'turn_id') || candidate.payload.turn_id === binding.turnId) ||
          candidate?.type === 'token_usage_record' && candidate.payload?.turn_id === binding.turnId) continue;
      if (completedCompaction(candidate, binding.sessionId, binding.turnId)) continue;
      if (configurationUpdate(candidate) && integer(contextAt) &&
          integer(Date.parse(candidate.timestamp)) && Date.parse(candidate.timestamp) >= contextAt) continue;
      // Initial settings may precede the first input. Locate only within this
      // bound thread/context; the input scan still retains the full control digest.
      const settings = candidate?.payload?.thread_settings;
      if (candidate?.type === 'event_msg' && candidate.payload?.type === 'thread_settings_applied' &&
          candidate.payload.thread_id === binding.sessionId &&
          (!Object.hasOwn(candidate.payload, 'turn_id') || candidate.payload.turn_id === binding.turnId) &&
          text(settings?.model) && settings.model === line.payload.model &&
          text(settings.cwd) && path.isAbsolute(settings.cwd) && samePath(settings.cwd, binding.cwd)) continue;
      if (inputHash(candidate, binding, promptHash) === promptHash) return index;
      // Same-turn history before the first Hook input is still source-bound.
      // No human match is supplied: this cannot skip an uncovered UI input.
      const at = Date.parse(candidate?.timestamp);
      if (boundedText(root, 200) && (!Object.hasOwn(line.payload, 'root_turn_id') || line.payload.root_turn_id === root) &&
          integer(contextAt) && integer(at) && at >= contextAt &&
          nativeExecutionRecord(candidate, binding, binding.turnId, root, line.payload.model,
            prior?.payload.turn_attribution, null, !prior && line.payload.root_turn_id === root)) continue;
      if ((!toolsDelta(candidate) || integer(contextAt) && integer(at) && at >= contextAt) &&
          lateOriginOutput(rows[next], binding)) continue;
      if (candidate?.type === 'turn_context' && candidate.payload?.turn_id === binding.turnId &&
          candidate.payload.model === line.payload.model && text(candidate.payload.cwd) && text(line.payload.cwd) &&
          samePath(candidate.payload.cwd, line.payload.cwd)) continue;
      // Do not jump over a rejected input/control to a later repeated context.
      return -1;
    }
  }
  return -1;
}

// Keep the original input prefix separate from a receipt-accepted execution
// turn (for example retained-input recovery). Only the saved receipt supplies
// that starting turn; a trigger claim or latest context alone cannot.
function capacityRetry(rows, binding, host, promptHash, sourceRef, captured = [promptHash], accepted = null, recovered = [], unchanged = false) {
  const origin = retryOrigin(rows, binding, promptHash);
  if (origin < 0) return empty('capacity-retry-original-input-unavailable');
  const execution = accepted || binding;
  const start = accepted ? rows.findIndex((row, index) => {
    const line = index >= origin ? parseRow(row) : null;
    return line?.type === 'turn_context' && line.payload?.turn_id === execution.turnId && line.payload.model === execution.model;
  }) : origin;
  if (start < 0) return empty('capacity-retry-accepted-execution-unavailable');
  let turn = execution.turnId;
  let inputTurn = binding.turnId;
  let model = execution.model;
  let completedAt = null;
  let pending = null;
  let boundaryAt = Date.parse(parseRow(rows[start]).timestamp);
  let retryCount = 0;
  let retryOffset = null;
  const visited = new Set([turn]);
  let inputIndex = 0;
  for (let index = origin; index < rows.length; index++) {
    const line = parseRow(rows[index]);
    if (!line) return empty('invalid-complete-tail-record');
    const payload = line.payload;
    if (line.type === 'response_item' && payload?.role === 'user') {
      if (inputHash(line, {...binding, turnId: inputTurn}, captured[inputIndex]) !== captured[inputIndex++]) return empty('capacity-retry-input-or-interruption-conflict');
      continue;
    }
    if (line.type === 'event_msg' && ['user_message', 'task_interrupted', 'turn_aborted',
          'task_cancelled', 'shutdown_complete'].includes(payload?.type)) {
      if (index < start && recovered.includes(rows[index].offset)) continue;
      return empty('capacity-retry-input-or-interruption-conflict');
    }
    if (line.type === 'turn_context') {
      if (!text(payload?.turn_id) || !text(payload.model) || !text(payload.cwd) ||
          !samePath(payload.cwd, binding.cwd) || !integer(Date.parse(line.timestamp))) {
        return empty('capacity-retry-context-mismatch');
      }
      if (index === origin && payload.model !== binding.model) return empty('capacity-retry-context-mismatch');
      inputTurn = payload.turn_id;
      if (index < start) continue;
      if (index === start && payload.model !== execution.model ||
          payload.turn_id !== (pending || turn) || completedAt !== null) {
        return empty('capacity-retry-turn-conflict');
      }
      if (pending && Date.parse(line.timestamp) < boundaryAt) return empty('capacity-retry-order-conflict');
      turn = payload.turn_id;
      model = payload.model;
      pending = null;
      continue;
    }
    if (index < start) continue;
    if (line.type !== 'event_msg') continue;
    if (payload?.type === 'model_rerouted' && text(payload.to_model)) model = payload.to_model;
    if (payload?.type === 'task_complete') {
      const at = Date.parse(line.timestamp);
      if (pending || completedAt !== null || payload.turn_id !== turn || payload.root_turn_id !== turn ||
          payload.error?.codex_error_info !== 'server_overloaded' ||
          payload.error.message !== 'Selected model is at capacity. Please try a different model.' ||
          !integer(at) || at < boundaryAt) return empty('capacity-retry-failure-unproven');
      completedAt = at;
    }
    if (payload?.type === 'task_started') {
      const attribution = payload.turn_attribution;
      const next = payload.turn_id;
      const at = Date.parse(line.timestamp);
      if (completedAt === null || pending || !boundedText(next, 200) || visited.has(next) ||
          payload.root_turn_id !== next || attribution?.turn_id !== next ||
          attribution.root_turn_id !== next || !['capacity_retry_automatic', 'capacity_retry_manual', 'resume_interrupted_task'].includes(attribution.turn_trigger) ||
          attribution.parent_turn_id !== null || attribution.initiating_agent_path !== null ||
          !integer(at) || at < completedAt || ++retryCount > 64) return empty('capacity-retry-start-unproven');
      pending = next;
      visited.add(next);
      completedAt = null;
      boundaryAt = at;
      retryOffset = rows[index].offset;
    }
  }
  if (inputIndex !== captured.length || !retryCount && !unchanged || pending || completedAt !== null || turn !== host.turnId || model !== host.model) {
    return empty('capacity-retry-current-turn-unproven');
  }
  return {state: 'observed', reason: 'native-automatic-capacity-retry',
    originalTurnId: binding.turnId, acceptedExecutionTurnId: execution.turnId, retryCount,
    conditions: {threadId: binding.sessionId, turnId: turn, model, hostVersion: host.hostVersion},
    sourceRef: `${sourceRef}#byte=${retryOffset}`, hostSourceRef: host.sourceRef};
}


// Native task transport is data, not human input or an authority grant.
function nativeTaskOutput(payload) {
  return payload?.type === 'function_call_output' && payload.namespace === 'codex_app' &&
    !Object.hasOwn(payload, 'call_id') && ['create_thread', 'send_message_to_thread'].includes(payload.name);
}

function taskMessageMatches(payload, turnId) {
  if (!nativeTaskOutput(payload) || Object.hasOwn(payload, 'role') ||
      !boundedText(payload.id, 200) ||
      payload.internal_chat_message_metadata_passthrough?.turn_id !== turnId ||
      typeof payload.output !== 'string' || Buffer.byteLength(payload.output, 'utf8') > MAX_NATIVE_MEDIA_BYTES) return false;
  const wrapper = new RegExp(`^<codex_delegation>\\s*<source_thread_id>(${UUID})</source_thread_id>` +
    '\\s*<input>([\\s\\S]*)</input>\\s*</codex_delegation>$', 'u').exec(payload.output.trim());
  return Boolean(wrapper && wrapper[2].trim());
}

// This proof starts at the saved execution, retaining the same human origin.
// It composes only native app-message and unchanged narrow capacity edges.
function appToolContinuation(rows, binding, host, promptHash, sourceRef, captured = [promptHash], accepted, recovered = []) {
  const reject = () => empty('native-tool-continuation-unproven');
  const origin = retryOrigin(rows, binding, promptHash);
  if (origin < 0) return reject();
  const execution = accepted || binding;
  const start = rows.findIndex((row, index) => {
    const line = index >= origin ? parseRow(row) : null;
    return line?.type === 'turn_context' && line.payload?.turn_id === execution.turnId &&
      line.payload.model === execution.model;
  });
  if (start < 0) return reject();
  let turn = execution.turnId, model = execution.model, root = turn;
  for (let index = origin; index < start; index++) {
    const line = parseRow(rows[index]), value = line?.payload;
    if (line?.type === 'event_msg' && value?.type === 'task_started' && value.turn_id === turn) {
      const attribution = value.turn_attribution;
      if (!boundedText(value.root_turn_id, 200) || attribution?.turn_id !== turn ||
          attribution.root_turn_id !== value.root_turn_id || attribution.initiating_agent_path !== null) return reject();
      root = value.root_turn_id;
    }
  }
  let inputTurn = binding.turnId, inputIndex = 0, completed = null, pending = null;
  let needsMessage = false, messageSeen = false, edges = 0, tools = 0, retries = 0, firstToolOffset = null;
  let boundaryAt = Date.parse(parseRow(rows[start]).timestamp);
  const visited = new Set([turn]), messageIds = new Set();
  for (let index = origin; index < rows.length; index++) {
    const row = rows[index], line = parseRow(row), value = line?.payload;
    if (!line) return reject();
    if (line.type === 'response_item' && value?.role === 'user') {
      if (inputHash(line, {...binding, turnId: inputTurn}, captured[inputIndex]) !== captured[inputIndex++]) return reject();
      continue;
    }
    if (line.type === 'event_msg' && ['user_message', 'task_interrupted', 'turn_aborted',
          'task_cancelled', 'shutdown_complete'].includes(value?.type)) {
      if (index < start && recovered.includes(row.offset)) continue;
      return reject();
    }
    if (line.type === 'turn_context') {
      if (!text(value?.turn_id) || !text(value.model) || !text(value.cwd) ||
          !samePath(value.cwd, binding.cwd) || !integer(Date.parse(line.timestamp))) return reject();
      inputTurn = value.turn_id;
      if (index < start) continue;
      if (index === start && value.model !== execution.model ||
          value.turn_id !== (pending?.turnId || turn) || completed !== null ||
          pending && Date.parse(line.timestamp) < boundaryAt) return reject();
      if (pending) {
        turn = pending.turnId; root = pending.root; needsMessage = pending.tool; messageSeen = false;
      }
      model = value.model; pending = null;
      continue;
    }
    if (index < start) continue;
    if (line.type === 'response_item' && nativeTaskOutput(value)) {
      if (!taskMessageMatches(value, turn) || messageIds.has(value.id) ||
          pending || completed !== null) return reject();
      messageIds.add(value.id);
      if (needsMessage) {
        if (value.name !== 'send_message_to_thread') return reject();
        messageSeen = true;
      }
    }
    if (line.type !== 'event_msg') continue;
    if (value?.type === 'model_rerouted' && text(value.to_model)) model = value.to_model;
    if (value?.type === 'task_complete') {
      const at = Date.parse(line.timestamp);
      if (pending || completed || needsMessage && !messageSeen || value.turn_id !== turn ||
          value.root_turn_id !== root || !integer(at) || at < boundaryAt) return reject();
      completed = {at, error: value.error};
    }
    if (value?.type === 'task_started') {
      const attribution = value.turn_attribution, next = value.turn_id, at = Date.parse(line.timestamp);
      if (!completed || pending || !boundedText(next, 200) || visited.has(next) ||
          attribution?.turn_id !== next || !boundedText(value.root_turn_id, 200) ||
          attribution.root_turn_id !== value.root_turn_id || attribution.initiating_agent_path !== null ||
          !integer(at) || at < completed.at || ++edges > 64) return reject();
      const tool = attribution.turn_trigger === 'app_tool_send_message';
      if (tool) {
        if (completed.error != null || !boundedText(attribution.parent_turn_id, 200) ||
            attribution.parent_turn_id === next) return reject();
        tools++; firstToolOffset ??= row.offset;
      } else {
        if (!['capacity_retry_automatic', 'capacity_retry_manual', 'resume_interrupted_task'].includes(attribution.turn_trigger) ||
            value.root_turn_id !== next || attribution.parent_turn_id !== null ||
            completed.error?.codex_error_info !== 'server_overloaded' ||
            completed.error.message !== 'Selected model is at capacity. Please try a different model.') return reject();
        retries++;
      }
      pending = {turnId: next, root: value.root_turn_id, tool};
      visited.add(next); completed = null; boundaryAt = at;
    }
  }
  if (inputIndex !== captured.length || !tools || pending || completed ||
      needsMessage && !messageSeen || turn !== host.turnId || model !== host.model) return reject();
  return {state: 'observed', reason: 'native-app-tool-continuation',
    originalTurnId: binding.turnId, acceptedExecutionTurnId: execution.turnId,
    toolContinuationCount: tools, retryCount: retries,
    conditions: {threadId: binding.sessionId, turnId: turn, model, hostVersion: host.hostVersion},
    sourceRef: `${sourceRef}#byte=${firstToolOffset}`, hostSourceRef: host.sourceRef};
}

function continuationAssociation(rows, binding, host, promptHash, sourceRef, captured = [promptHash], accepted, recovered = []) {
  const retry = capacityRetry(rows, binding, host, promptHash, sourceRef, captured, accepted, recovered);
  if (retry.state === 'observed' || !rows.some(row => {
    const line = parseRow(row);
    return line?.type === 'event_msg' && line.payload?.type === 'task_started' &&
      line.payload.turn_attribution?.turn_trigger === 'app_tool_send_message';
  })) return retry;
  return appToolContinuation(rows, binding, host, promptHash, sourceRef, captured, accepted, recovered);
}

// Prove only the native execution edge. The source context remains pending
// until explicit reconciliation; its meaning/authority is still caller review.
// This edge is neither a human composer turn nor a capacity failure retry.
// Recognize recorded host data inside a same-execution origin or Goal proof.
// These snapshots/output records do not grant permission, restore a turn, or
// enter the global benign-append policy. Source bytes remain cursor-bound.
function nativeExecutionRecord(line, binding, turn, root, model, attribution, human, anchor) {
  const p = line.payload;
  if (configurationUpdate(line)) return true;
  if (toolsDelta(line)) return true;
  if (!p || typeof p !== 'object' || Array.isArray(p)) return false;
  if (Object.hasOwn(p, 'thread_id') && p.thread_id !== binding.sessionId ||
      Object.hasOwn(p, 'turn_id') && p.turn_id !== turn ||
      Object.hasOwn(p, 'root_turn_id') && p.root_turn_id !== root ||
      Object.hasOwn(p, 'session_id') && p.session_id !== binding.sessionId) return false;
  const object = value => value && typeof value === 'object' && !Array.isArray(value);
  const sameExecution = p.thread_id === binding.sessionId && p.turn_id === turn;
  if (line.type === 'token_usage_record') {
    const keys = ['input_tokens', 'cached_input_tokens', 'cache_write_input_tokens',
      'output_tokens', 'reasoning_output_tokens', 'total_tokens'];
    const counts = value => object(value) && Object.keys(value).length === keys.length &&
      keys.every(key => integer(value[key]) && value[key] >= 0);
    return sameExecution && p.session_id === binding.sessionId && p.root_turn_id === root &&
      boundedText(p.response_id, 200) && counts(p.usage) && counts(p.turn_token_usage) && counts(p.thread_token_usage);
  }
  if (line.type === 'event_msg' && p.type === 'thread_settings_applied') {
    const settings = p.thread_settings;
    // Other settings are recorded environment changes, never Accord authority.
    return p.thread_id === binding.sessionId && (!Object.hasOwn(p, 'turn_id') || p.turn_id === turn) &&
      object(settings) && settings.model === model && text(settings.cwd) && samePath(settings.cwd, binding.cwd);
  }
  if (line.type === 'compacted') {
    const resume = p.resume_metadata, a = resume?.turn_attribution;
    // A retained anchor can omit the earlier start. Reuse only its already
    // accepted execution and explicit context root; do not invent an edge.
    const anchorMatch = anchor && a?.turn_id === turn && a.root_turn_id === root &&
      a.initiating_agent_path === null && (root === turn
        ? a.parent_turn_id === null && ['composer', 'send_user_message_async_question'].includes(a.turn_trigger)
        : a.turn_trigger === 'goal' && boundedText(a.parent_turn_id, 200) && a.parent_turn_id !== turn);
    // Explicit null/missing resume identity is not evidence of this execution.
    // Replacement history is preserved data, not a new input or recovery source.
    return object(resume) && resume.multi_agent_version === 'v2' && resume.last_started_turn_id === turn &&
      (attribution ? canonical(a) === canonical(attribution) : anchorMatch) &&
      resume.previous_turn_settings?.model === model && Array.isArray(p.replacement_history) &&
      Array.isArray(p.replacement_history_metadata) &&
      p.replacement_history.length === p.replacement_history_metadata.length && object(p.retained_context);
  }
  if (line.type === 'world_state') {
    // Full snapshots may also be initial context, not just compaction output.
    const state = p.state, local = state?.environments?.environments?.local;
    return p.full === true && object(state) && state.model?.model === model && object(local) &&
      text(local.cwd) && samePath(local.cwd, binding.cwd);
  }
  if (line.type !== 'event_msg' || p.type !== 'item_completed' || !sameExecution ||
      !boundedText(p.item?.id, 200) || !integer(p.started_at_ms) || !integer(p.completed_at_ms) ||
      p.completed_at_ms < p.started_at_ms) return false;
  const item = p.item;
  if (item.type === 'UserMessage') {
    // UI item IDs differ from source IDs. Require the nearest covered typed
    // input in this turn, exact text parts, and one consumption before reset.
    return human && Array.isArray(item.content) && item.content.length === human.content.length &&
      item.content.every((part, index) => part?.type === 'text' && typeof part.text === 'string' &&
        part.text === human.content[index].text && Array.isArray(part.text_elements) && part.text_elements.length === 0);
  }
  if (item.type === 'CollabAgentToolCall') return item.tool === 'wait' && item.status === 'completed' &&
    item.sender_thread_id === binding.sessionId && Array.isArray(item.receiver_thread_ids) && Array.isArray(item.receiver_agents);
  if (item.type !== 'Extension') return false;
  return item.kind === 'clock.sleep' ? integer(item.durationMs) && item.durationMs >= 0
    : item.kind === 'web.search' && ['search', 'openPage', 'findInPage'].includes(item.action?.type);
}

function goalChain(rows, binding, host, sourceRef, scan, accepted = null) {
  const reject = () => empty('native-goal-continuation-unproven');
  if (!scan || scan.state !== 'observed' || !scan.latestInputReconciled) return reject();
  const execution = accepted || binding;
  const start = rows.findIndex(row => {
    const line = parseRow(row), p = line?.payload;
    return line?.type === 'turn_context' && p.turn_id === execution.turnId && p.model === execution.model;
  });
  if (start < 0) return reject();
  const priorStart = rows.slice(0, start).map(parseRow).findLast(line =>
    line?.type === 'event_msg' && line.payload?.type === 'task_started' && line.payload.turn_id === execution.turnId);
  const contextRoot = parseRow(rows[start]).payload.root_turn_id;
  const anchorRoot = !priorStart && execution.turnId === binding.turnId &&
    scan.cursor?.anchorOffset === rows[start].offset && boundedText(contextRoot, 200) ? contextRoot : null;
  let root = priorStart?.payload.root_turn_id || anchorRoot || execution.turnId;
  if (!boundedText(root, 200)) return reject();
  let turn = execution.turnId, model = execution.model, boundary = Date.parse(parseRow(rows[start]).timestamp);
  let completed = null, pending = null, needsGoal = false, needsRootGoal = false, edges = 0, edgeOffset = null, rootEdge = false;
  let attribution = priorStart?.payload.turn_attribution, human = null;
  const visited = new Set([turn, root]);
  if (!integer(boundary)) return reject();
  for (let index = start; index < rows.length; index++) {
    const row = rows[index], line = parseRow(row), p = line?.payload;
    if (!line) return reject();
    const at = Date.parse(line.timestamp);
    if (line.type === 'turn_context') {
      if (p?.turn_id !== (pending?.turn || turn) || p.model !== model || !text(p.cwd) ||
          !samePath(p.cwd, binding.cwd) || !integer(at) || at < boundary || completed !== null ||
          Object.hasOwn(p, 'source') || pending?.newRoot && p.root_turn_id !== pending.root ||
          Object.hasOwn(p, 'root_turn_id') && p.root_turn_id !== (pending?.root || root)) return reject();
      if (pending) { turn = pending.turn; root = pending.root; attribution = pending.attribution;
        needsRootGoal = pending.newRoot; pending = null; needsGoal = true; human = null; }
      boundary = at;
      continue;
    }
    if (line.type === 'event_msg' && p?.type === 'task_complete') {
      if (pending || needsGoal || completed !== null || p.turn_id !== turn || p.root_turn_id !== root ||
          p.error != null || !integer(at) || at < boundary) return reject();
      completed = at;
      continue;
    }
    if (line.type === 'event_msg' && p?.type === 'task_started') {
      const a = p.turn_attribution, next = p.turn_id;
      const child = p.root_turn_id === root && a?.root_turn_id === root && a?.parent_turn_id === turn;
      const newRoot = p.root_turn_id === next && a?.root_turn_id === next && a?.parent_turn_id === null;
      if (completed === null || pending || !boundedText(next, 200) || visited.has(next) ||
          !(child || newRoot) || a?.turn_id !== next ||
          a.turn_trigger !== 'goal' || a.initiating_agent_path !== null ||
          !integer(at) || at < completed || ++edges > 64) return reject();
      pending = {turn: next, root: newRoot ? next : root, attribution: a, newRoot};
      rootEdge ||= newRoot; visited.add(next); completed = null; boundary = at; edgeOffset = row.offset;
      continue;
    }
    // Nothing with effects may intervene between completion/start/context.
    if (completed !== null || pending) return reject();
    if (line.type === 'response_item' && p?.role === 'user') {
      const record = scan.records.find(item => item.recordOffset === row.offset && item.turnId === turn && item.supported);
      if (!record || edges && !goalRuntimeContext(p, turn) || needsRootGoal && (!integer(at) || at < boundary)) return reject();
      human = typedHumanInput(p, turn) ? p : null;
      if (edges) { needsGoal = false; needsRootGoal = false; }
      continue;
    }
    if (needsGoal && !(line.type === 'response_item' && p?.type === 'message' && p.role === 'developer') &&
        !((configurationUpdate(line) || toolsDelta(line)) && integer(at) && at >= boundary)) return reject();
    if (integer(at) && at >= boundary && nativeExecutionRecord(line, binding, turn, root, model, attribution, human,
        anchorRoot !== null && turn === execution.turnId)) {
      if (line.type === 'compacted' || p?.item?.type === 'UserMessage') human = null;
      continue;
    }
    if (line.type === 'response_item' && p?.type === 'message' && p.role === 'developer' ||
        completedCompaction(line, binding.sessionId, turn) ||
        (!toolsDelta(line) || integer(at) && at >= boundary) && lateOriginOutput(row, {...binding, turnId: turn})) continue;
    return reject();
  }
  if (!edges || pending || completed !== null || needsGoal || turn !== host.turnId || model !== host.model) return reject();
  return {state: 'observed', reason: rootEdge ? 'native-root-goal-execution-continuation' : 'native-goal-continuation',
    conditions: {threadId: binding.sessionId, turnId: turn, model, hostVersion: host.hostVersion},
    sourceRef: `${sourceRef}#byte=${edgeOffset}`, hostSourceRef: host.sourceRef,
    claimLimit: rootEdge ? 'native-root-goal-execution-association-only; no same goal_id or parent-child claim; Goal context meaning and authority require review'
      : 'native-execution-attribution-only; Goal context meaning and authority require review'};
}

function typedHumanInput(payload, turnId) {
  const meta = payload?.internal_chat_message_metadata_passthrough;
  return boundedText(turnId, 200) && payload?.type === 'message' && payload.role === 'user' && boundedText(payload.id, 200) &&
    meta?.turn_id === turnId && Array.isArray(payload.content) && payload.content.length > 0 &&
    payload.content.every(item => item?.type === 'input_text') && Array.isArray(meta.content_item_kinds) &&
    meta.content_item_kinds.length === payload.content.length && meta.content_item_kinds.every(kind => kind === 'user.text') &&
    Array.isArray(meta.content_item_metadata) && meta.content_item_metadata.length === payload.content.length &&
    meta.content_item_metadata.every(item => item?.provenance?.type === 'user');
}

// Compose only an independently proved earlier human execution with the same
// strict Goal-chain verifier. Prefixes shrink and share the human proof limit;
// the temporary accepted execution is never persisted as a separate decision.
function goalContinuation(rows, binding, host, hash, sourceRef, scan, accepted = null, recovered = [], depth = 0) {
  const reject = () => empty('native-goal-continuation-unproven');
  if (depth >= 64 || !scan || scan.state !== 'observed' || !scan.latestInputReconciled) return reject();
  const direct = goalChain(rows, binding, host, sourceRef, scan, accepted);
  if (direct.state === 'observed') return direct;
  const target = rows.findIndex(row => {
    const line = parseRow(row);
    return line?.type === 'turn_context' && line.payload?.turn_id === host.turnId;
  });
  if (target < 0) return reject();
  const humanIndex = rows.findLastIndex((row, index) => {
    const line = index < target ? parseRow(row) : null, p = line?.payload;
    return line?.type === 'response_item' && typedHumanInput(p, p?.internal_chat_message_metadata_passthrough?.turn_id);
  });
  if (humanIndex < 0) return reject();
  const human = parseRow(rows[humanIndex]).payload.internal_chat_message_metadata_passthrough.turn_id;
  if (human === (accepted || binding).turnId || human === host.turnId) return reject();
  const previous = rows.slice(0, humanIndex).map(parseRow).findLast(line =>
    line?.type === 'turn_context' && line.payload?.turn_id === human)?.payload;
  if (!previous) return reject();
  const completed = rows.findIndex((row, index) => {
    const line = index > humanIndex && index < target ? parseRow(row) : null;
    return line?.type === 'event_msg' && line.payload?.type === 'task_complete' &&
      line.payload.turn_id === human && line.payload.error == null;
  });
  if (completed < 0) return reject();
  const proof = nativeHumanContinuation(rows.slice(0, completed), binding,
    {...host, turnId: human, model: previous.model}, hash, sourceRef, scan, accepted, recovered, depth + 1);
  return proof.state === 'observed'
    ? goalChain(rows, binding, host, sourceRef, scan, {turnId: human, model: previous.model}) : reject();
}

// Only explicit source reconciliation supplies this checked scan. A later human
// cannot erase an unproved execution between the saved accepted turn and itself.
function nativeHumanContinuation(rows, binding, host, hash, sourceRef, scan, accepted, recovered, depth = 0, closedBefore = null) {
  const reject = () => empty('native-human-continuation-unproven'), execution = accepted || binding;
  if (depth >= 64) return reject();
  const context = row => { const line = parseRow(row); return line?.type === 'turn_context' ? line.payload : null; };
  const start = rows.findIndex(row => context(row)?.turn_id === execution.turnId && context(row).model === execution.model);
  const at = rows.findIndex((row, index) => index > start && context(row)?.turn_id === host.turnId);
  if (start < 0 || at < 0 || host.turnId === execution.turnId) return reject();
  const prefix = rows.slice(0, at), previous = prefix.findLast(row => context(row));
  const prior = context(previous), root = prefix.map(parseRow).findLast(line =>
    line?.payload?.type === 'task_started' && line.payload.turn_id === prior.turn_id)?.payload.root_turn_id || prior.turn_id;
  let human = null;
  for (const row of rows.slice(at)) {
    const line = parseRow(row), p = line?.payload;
    if (line?.type === 'turn_context' && (p.turn_id !== host.turnId || p.model !== host.model ||
        !samePath(p.cwd, binding.cwd) || Object.hasOwn(p, 'source') ||
        Object.hasOwn(p, 'root_turn_id') && p.root_turn_id !== host.turnId)) return reject();
    if (line?.type === 'event_msg' && ['task_started', 'task_complete'].includes(p?.type)) return reject();
    if (line?.type === 'response_item' && typedHumanInput(p, host.turnId)) {
      human = scan.records.find(item => item.recordOffset === row.offset && item.turnId === host.turnId && item.supported);
    }
  }
  if (!human || closedBefore !== null && scan.records.some(item =>
      item.turnId === host.turnId && item.recordOffset >= closedBefore)) return reject();
  let completions = 0, starts = 0, invalidBoundary = false, completionOffset = null;
  let completionAt = null, humanStartAt = null;
  const before = prefix.filter(row => {
    const line = parseRow(row), p = line?.payload;
    if (line?.type !== 'event_msg') return true;
    if (p?.type === 'task_started' && p.turn_id === host.turnId) {
      const a = p.turn_attribution;
      if (row.offset > previous.offset && ['composer', 'send_user_message_async_question'].includes(a?.turn_trigger) && a.turn_id === host.turnId && a.root_turn_id === host.turnId &&
          p.root_turn_id === host.turnId && a.parent_turn_id === null && a.initiating_agent_path === null) {
        starts++; humanStartAt = Date.parse(line.timestamp); return false;
      }
    }
    if (row.offset > previous.offset && p?.type === 'task_complete' && p.turn_id === prior.turn_id &&
        p.root_turn_id === root && p.error == null) {
      if (starts) invalidBoundary = true;
      completions++; completionOffset = row.offset; completionAt = Date.parse(line.timestamp); return false;
    }
    return true;
  });
  if (invalidBoundary || completions > 1 || starts > 1 ||
      completionOffset !== null && scan.records.some(item =>
        item.turnId === prior.turn_id && item.recordOffset >= completionOffset)) return reject();
  let proof = continuationAssociation(before, binding, {...host, turnId: prior.turn_id, model: prior.model}, hash,
    sourceRef, scan.records.filter(item => item.recordOffset < rows[at].offset).map(item => item.promptSha256), accepted, recovered);
  // The previous execution may have stayed on its already accepted turn.
  if (proof.state !== 'observed') proof = capacityRetry(before, binding,
    {...host, turnId: prior.turn_id, model: prior.model}, hash, sourceRef,
    scan.records.filter(item => item.recordOffset < rows[at].offset).map(item => item.promptSha256), accepted, recovered, true);
  // A Goal predecessor needs its full normal-close/human-start boundary.
  // This does not relax the existing human or capacity continuation policies.
  const previousAt = Date.parse(parseRow(previous).timestamp), humanContextAt = Date.parse(parseRow(rows[at]).timestamp);
  if (proof.state !== 'observed' && completions === 1 && starts === 1 &&
      [previousAt, completionAt, humanStartAt, humanContextAt].every(integer) &&
      previousAt <= completionAt && completionAt <= humanStartAt && humanStartAt <= humanContextAt) {
    proof = goalContinuation(before, binding, {...host, turnId: prior.turn_id, model: prior.model},
      hash, sourceRef, scan, accepted, recovered, depth + 1);
  }
  // Prove each earlier native human turn; retain the original accepted basis.
  // Carry its terminal offset so filtering cannot revive input after completion.
  if (proof.state !== 'observed') proof = nativeHumanContinuation(before, binding,
    {...host, turnId: prior.turn_id, model: prior.model}, hash, sourceRef, scan,
    accepted, recovered, depth + 1, completionOffset);
  return proof.state === 'observed' ? {state: 'observed', reason: 'native-human-input-continuation',
    conditions: {threadId: binding.sessionId, turnId: host.turnId, model: host.model, hostVersion: host.hostVersion},
    sourceRef: human.sourceRef, hostSourceRef: host.sourceRef} : reject();
}

function associateNativeTurn(binding, host, promptHash, captured, acceptedExecution, retryInputScan) {
  return observeNativeTranscript(binding, {now: Date.now(), maxAgeMs: 1,
    retryHost: host, retryInputSha256: promptHash, capturedInputHashes: captured,
    ...(retryInputScan ? {retryInputScan} : {}),
    ...(acceptedExecution ? {acceptedExecution} : {})});
}

// One file snapshot supplies both the human/control sequence and the old byte
// prefix. A later assistant/tool append may extend it without renewing evidence.
function scanNativeInputs(rows, tail, tailOffset, binding, scan, identity, headHash, sourceRef) {
  const start = retryOrigin(rows, binding, scan.anchorHash);
  if (start < 0) return empty('native-input-origin-unavailable');
  const anchorOffset = rows[start].offset;
  let turn = binding.turnId, model = null, originModel = null, inputIndex = 0;
  const signals = [], pendingInputs = [], records = [], enrichments = [], controls = [];
  let contextAt = null;
  const hooks = scan.captured.filter(item => !item.recordSha256);
  const sourced = scan.captured.filter(item => item.recordSha256);
  const matchedSources = new Set();
  // Only token-bound replay proposes one additional interruption reconciliation.
  // Retained entries must still match the immutable byte prefix on every read.
  const recovered = scan.recoveredControl;
  if (recovered && (!recovered.cursor || !Array.isArray(recovered.resumes))) return empty('native-input-evidence-changed');
  const resumes = [...(recovered?.resumes || []), ...(scan.resumeControl ? [scan.resumeControl] : [])];
  if (resumes.length > 64 || resumes.some(item => !item || Object.keys(item).sort().join(',') !== 'model,turnId' ||
      !boundedText(item.turnId, 200) || !boundedText(item.model, 200)) ||
      new Set(resumes.map(item => item.turnId)).size !== resumes.length) return empty('native-input-evidence-changed');
  let resumeIndex = 0, pendingResume = null;
  const recoveredInterruptOffsets = [];
  let selectedPart = null;
  for (let index = start; index < rows.length; index++) {
    const row = rows[index], line = parseRow(row), payload = line?.payload;
    if (!line) return empty('invalid-complete-tail-record');
    const digest = crypto.createHash('sha256').update(row.bytes).digest('hex');
    if (pendingResume && line.type !== 'turn_context' &&
        !(line.type === 'event_msg' && payload?.type === 'task_started')) {
      return empty('native-input-control-needs-reconciliation');
    }
    if (line.type === 'turn_context') {
      if (!text(payload?.turn_id) || !text(payload.model) || !text(payload.cwd) ||
          !samePath(payload.cwd, binding.cwd) || index === start && binding.model && payload.model !== binding.model) {
        return empty('native-input-context-conflict');
      }
      if (pendingResume) {
        const expected = resumes[resumeIndex];
        if (!pendingResume.started || payload.turn_id !== expected.turnId || payload.model !== expected.model ||
            !integer(Date.parse(line.timestamp)) || Date.parse(line.timestamp) < pendingResume.at) {
          return empty('native-input-control-needs-reconciliation');
        }
        resumeIndex++; pendingResume = null;
      }
      turn = payload.turn_id; model = payload.model; contextAt = Date.parse(line.timestamp);
      if (index === start) originModel = model;
      signals.push([row.offset, digest]);
    }
    if (line.type === 'response_item' && payload?.type === 'configuration_update') {
      if (!configurationUpdate(line) || !integer(contextAt) || !integer(Date.parse(line.timestamp)) ||
          Date.parse(line.timestamp) < contextAt) return empty('native-input-control-unrecognized');
      signals.push([row.offset, digest]);
      controls.push({turnId: turn, sourceRef: `${sourceRef}#byte=${row.offset}`, recordOffset: row.offset,
        recordSha256: digest, type: 'configuration_update', reasoningEffort: payload.reasoning.effort,
        controlDisposition: 'host-control-not-human-or-permission'});
    }
    if (line.type === 'world_state' && payload?.full !== true &&
        !toolsDelta(line) && !environmentDelta(line))
      return empty('native-input-control-unrecognized');
    if (toolsDelta(line)) {
      if (!integer(contextAt) || !integer(Date.parse(line.timestamp)) || Date.parse(line.timestamp) < contextAt)
        return empty('native-input-control-unrecognized');
      signals.push([row.offset, digest]);
      controls.push({turnId: turn, sourceRef: `${sourceRef}#byte=${row.offset}`, recordOffset: row.offset,
        recordSha256: digest, type: 'world_state', section: 'tools',
        controlDisposition: 'host-tool-directory-not-permission-or-invocation'});
    }
    if (line.type === 'response_item' && nativeTaskOutput(payload)) signals.push([row.offset, digest]);
    const user = line.type === 'response_item' && payload?.role === 'user';
    const event = line.type === 'event_msg' ? payload?.type : null;
    if (user) {
      signals.push([row.offset, digest]);
      const sourceRefAtRow = `${sourceRef}#byte=${row.offset}`;
      const sourceIndex = sourced.findIndex(item => item.recordSha256 === digest && item.sourceRef === sourceRefAtRow &&
        (!item.turnId || item.turnId === turn));
      if (sourceIndex >= 0 && matchedSources.has(sourceIndex)) return empty('native-captured-input-prefix-mismatch');
      const sourceMatch = sourceIndex >= 0;
      const goal = goalRuntimeContext(payload, turn);
      const ambient = typedAmbient(payload, turn);
      const hostContext = ambient || goal;
      const kinds = payload?.internal_chat_message_metadata_passthrough?.content_item_kinds;
      const claimedGoal = Array.isArray(kinds) && kinds.includes('goal.internal_context');
      if (sourceMatch && sourced[sourceIndex].sourceCategory &&
          sourced[sourceIndex].sourceCategory !== (goal ? 'goal-runtime-context' : null)) {
        return empty('native-captured-input-prefix-mismatch');
      }
      const expected = hooks[inputIndex];
      const capturedHash = sourceMatch ? sourced[sourceIndex].promptSha256 : expected?.promptSha256;
      const promptHash = inputHash(line, {...binding, turnId: turn}, capturedHash);
      const hookMatch = !sourceMatch && !hostContext && expected && expected.promptSha256 === promptHash &&
        (!expected.turnId || expected.turnId === turn);
      if (sourceMatch) matchedSources.add(sourceIndex);
      else if (hookMatch) inputIndex++;
      else if (expected && !hostContext) return empty('native-captured-input-prefix-mismatch');
      const content = contentEvidence(payload, {...binding, turnId: turn}, capturedHash);
      const record = {turnId: turn, sourceRef: sourceRefAtRow, recordOffset: row.offset,
        recordSha256: digest, promptSha256: promptHash, itemId: payload.id ?? null, captured: Boolean(sourceMatch || hookMatch),
        supported: content.supported && (!claimedGoal || goal), parts: content.parts,
        ...(goal ? {sourceCategory: 'goal-runtime-context', controlDisposition: 'requires-review'} : {})};
      records.push(record);
      if (record.captured) {
        if (!record.supported || (content.parts.length > 1) && !scan.coverage?.some(item =>
            item.recordOffset === row.offset && item.recordSha256 === digest && canonical(item.parts) === canonical(content.parts))) {
          enrichments.push(record);
        }
      } else {
        pendingInputs.push({...record,
          ...(record.supported ? {prompt: content.prompt, promptSha256: promptHash} : {})});
      }
      if (scan.readPart?.recordOffset === row.offset && scan.readPart.recordSha256 === digest) {
        const descriptor = content.parts.find(part => part.partIndex === scan.readPart.partIndex);
        if (!content.supported || !descriptor) return empty('native-source-part-unsupported');
        const item = payload.content[scan.readPart.partIndex];
        selectedPart = descriptor.type === 'text' ? {...descriptor, text: item.text, record}
          : {...descriptor, image: {type: 'image', mimeType: 'image/png', data: pngData(item.image_url).data}, record};
      }
    }
    if (line.type === 'compacted' || event === 'context_compacted' ||
        completedCompaction(line, binding.sessionId, turn)) signals.push([row.offset, digest]);
    if (event && /^(?:task_|turn_|thread_settings_|model_rerouted|interrupt|shutdown|user_message)/u.test(event)) {
      if (!['task_started', 'task_complete', 'task_interrupted', 'turn_aborted', 'task_cancelled',
          'thread_settings_applied', 'model_rerouted', 'shutdown_complete', 'user_message'].includes(event)) {
        return empty('native-input-control-unrecognized');
      }
      signals.push([row.offset, digest]);
      if (event === 'model_rerouted' && text(payload.to_model)) model = payload.to_model;
      if (event === 'turn_aborted' && resumes[resumeIndex] && payload.reason === 'interrupted' &&
          payload.turn_id === turn && turn !== resumes[resumeIndex].turnId && integer(Date.parse(line.timestamp))) {
        if (resumeIndex < (recovered?.resumes.length || 0) && row.offset >= recovered.cursor.endOffset) {
          return empty('native-input-evidence-changed');
        }
        pendingResume = {at: Date.parse(line.timestamp), started: false};
        recoveredInterruptOffsets.push(row.offset);
        continue;
      }
      if (event === 'task_started' && pendingResume) {
        const expected = resumes[resumeIndex], at = Date.parse(line.timestamp), attribution = payload.turn_attribution;
        if (pendingResume.started || payload.turn_id !== expected.turnId || payload.root_turn_id !== expected.turnId ||
            attribution?.turn_id !== expected.turnId || attribution.root_turn_id !== expected.turnId ||
            attribution.turn_trigger !== 'resume_interrupted_task' || attribution.parent_turn_id !== null ||
            attribution.initiating_agent_path !== null || !integer(at) || at < pendingResume.at) {
          return empty('native-input-control-needs-reconciliation');
        }
        pendingResume = {at, started: true};
      }
      if (['task_interrupted', 'turn_aborted', 'task_cancelled', 'shutdown_complete', 'user_message'].includes(event)) {
        return empty('native-input-control-needs-reconciliation');
      }
    }
  }
  if (pendingResume || resumeIndex !== resumes.length || scan.resumeControl &&
      (turn !== scan.resumeControl.turnId || model !== scan.resumeControl.model)) {
    return empty('native-input-control-needs-reconciliation');
  }
  if (inputIndex !== hooks.length || matchedSources.size !== sourced.length) return empty('native-captured-input-prefix-incomplete');
  if (scan.host && (scan.host.threadId !== binding.sessionId || scan.host.turnId !== turn || scan.host.model !== model)) {
    return empty('native-input-current-host-conflict');
  }
  if (scan.expectedTurnId && scan.expectedTurnId !== turn) return empty('native-input-current-turn-conflict');
  const cursor = {sourceId: `${identity.dev}:${identity.ino}`, headSha256: headHash, anchorOffset,
    endOffset: tailOffset + tail.length, prefixSha256: crypto.createHash('sha256')
      .update(tail.subarray(anchorOffset - tailOffset)).digest('hex'), signalsSha256: sha(signals)};
  for (const expected of [scan.retainedCursor, scan.expectedCursor, recovered?.cursor].filter(Boolean)) {
    const prefix = tail.subarray(anchorOffset - tailOffset, expected.endOffset - tailOffset);
    if (expected.sourceId !== cursor.sourceId || expected.headSha256 !== cursor.headSha256 ||
        expected.anchorOffset !== anchorOffset || expected.endOffset > cursor.endOffset ||
        expected.endOffset < anchorOffset || expected === scan.expectedCursor && expected.signalsSha256 !== cursor.signalsSha256 ||
        expected !== scan.expectedCursor && expected.signalsSha256 !== sha(signals.filter(([offset]) => offset < expected.endOffset)) ||
        expected.prefixSha256 !== crypto.createHash('sha256').update(prefix).digest('hex')) {
      return empty('native-input-evidence-changed');
    }
  }
  if (scan.readPart && !selectedPart) return empty('native-source-record-unavailable');
  const supported = records.every(record => record.supported);
  return {state: 'observed', reason: 'bound-native-input-prefix', cursor, pendingInputs, records, enrichments, controls,
    ...(resumes.length ? {recoveredControl: {resumes, cursor}, recoveredInterruptOffsets} : {}),
    ...(selectedPart ? {selectedPart} : {}),
    capturedPrefixMatched: true, latestInputReconciled: pendingInputs.length === 0,
    latestNativeInputsComplete: pendingInputs.length === 0 && enrichments.length === 0 && supported,
    currentTurnId: turn, currentModel: model, originModel, sourceRef, sourceReleaseAllowed: false,
    contentCoverage: !supported ? 'unsupported-native-content' : records.some(record => record.parts.some(part => part.type === 'image'))
      ? 'structured-text-png-records' : 'text-records'};
}

function inspectNativeInputs(binding, scan) {
  return observeNativeTranscript(binding, {now: Date.now(), maxAgeMs: 1, inputScan: scan});
}

// Read-only adapter over the one native rollout path supplied by the current Hook.
// The byte limits bound local I/O only; they are not model capacity or quality limits.
function retryRecordIsBenign(row) {
  const line = parseRow(row), value = line?.payload;
  if (['user', 'developer', 'system'].includes(value?.role) || nativeTaskOutput(value)) return false;
  if (line?.type === 'event_msg') {
    return ['token_count', 'agent_message', 'agent_reasoning'].includes(value?.type);
  }
  if (line?.type !== 'response_item') return false;
  return value?.type === 'message' ? value.role === 'assistant'
    : ['reasoning', 'function_call', 'function_call_output', 'custom_tool_call',
      'custom_tool_call_output'].includes(value?.type);
}

function observeNativeTranscript(binding, options = {}) {
  const prior = {};
  const first = readNativeTranscript(binding, options, prior);
  // Optional coherent retry only; the unchanged fail-closed reader remains authoritative.
  // Authenticate every byte this read consumed; unobserved history is not claimed.
  if (first.reason !== 'transcript-path-changed-after-read' || !prior.identity ||
      prior.tail.at(-1) !== 0x0a) return first;
  const remaining = MAX_RETAINED_BYTES - prior.head.length - prior.tail.length;
  if (remaining <= 0) return first;
  const next = {maximumBytes: remaining};
  const second = readNativeTranscript(binding, options, next);
  if (!next.identity || next.identity.dev !== prior.identity.dev ||
      next.identity.ino !== prior.identity.ino || next.identity.mode !== prior.identity.mode ||
      !samePath(next.transcriptPath, prior.transcriptPath) || next.size <= prior.size ||
      next.tailOffset > prior.tailOffset || next.tailOffset + next.tail.length < prior.size ||
      !next.head.subarray(0, prior.head.length).equals(prior.head) ||
      !next.tail.subarray(prior.tailOffset - next.tailOffset,
        prior.tailOffset - next.tailOffset + prior.tail.length).equals(prior.tail)) return first;
  const appended = completeLines(next.tail.subarray(prior.size - next.tailOffset), prior.size, false);
  if (!appended.length || hasUnterminatedRecord(next.tail) ||
      !appended.every(retryRecordIsBenign) || !next.sourceUnchanged()) return first;
  return second;
}

function readNativeTranscript(binding, options = {}, snapshot = null) {
  const inputScan = options.inputScan;
  if (!binding || !['transcriptPath', 'sessionId', 'turnId', 'cwd'].every((key) => text(binding[key])) ||
      !inputScan && !text(binding.model)) {
    return empty('binding-missing');
  }
  const now = options.now;
  const maxAgeMs = options.maxAgeMs;
  if (!integer(now) || !integer(maxAgeMs) || maxAgeMs === 0) return empty('observation-time-invalid');
  const proofOnly = Object.hasOwn(options, 'retryHost');
  const accepted = options.acceptedExecution;
  if (Object.hasOwn(options, 'acceptedExecution') && (!accepted || typeof accepted !== 'object' || Array.isArray(accepted) ||
      Object.keys(accepted).sort().join(',') !== 'model,turnId' ||
      !boundedText(accepted.turnId, 200) || !boundedText(accepted.model, 200))) {
    return empty('accepted-execution-fields-invalid');
  }
  const execution = accepted ? {...binding, turnId: accepted.turnId, model: accepted.model} : binding;
  const retry = proofOnly || Object.hasOwn(options, 'retryInputSha256') &&
    Object.hasOwn(options, 'currentHost') && options.currentHost?.turnId !== execution.turnId;
  const retryHost = proofOnly ? options.retryHost : options.currentHost;
  const liveHost = inputScan ? {host: null, reason: null} : retry ? currentHost({...execution, turnId: retryHost?.turnId,
    model: retryHost?.model}, {currentHost: retryHost}) : currentHost(execution, options);
  if (liveHost.reason) return empty(liveHost.reason);
  if (retry && !/^[a-f0-9]{64}$/.test(options.retryInputSha256 || '')) return empty('capacity-retry-input-hash-missing');

  let sessionsRoot;
  let transcriptPath;
  let suppliedIdentity;
  try {
    sessionsRoot = realPath(options.sessionsRoot || defaultSessionsRoot());
    const supplied = path.resolve(binding.transcriptPath);
    const suppliedStat = fs.lstatSync(supplied, {bigint: true});
    if (suppliedStat.isSymbolicLink() || !suppliedStat.isFile()) return empty('transcript-not-regular-file');
    suppliedIdentity = statIdentity(suppliedStat);
    transcriptPath = realPath(supplied);
  } catch (_) {
    return empty('transcript-unavailable');
  }

  const relative = path.relative(sessionsRoot, transcriptPath);
  if (!relative || path.isAbsolute(relative) || relative === '..' || relative.startsWith(`..${path.sep}`)) {
    return empty('transcript-outside-sessions-root');
  }
  const parts = relative.split(path.sep);
  const name = parts.at(-1);
  const match = ROLLOUT_NAME.exec(name || '');
  if (parts.length !== 4 || !match || parts[0] !== match[1] || parts[1] !== match[2] || parts[2] !== match[3]) {
    return empty('noncanonical-rollout-path');
  }
  if (match[4].toLowerCase() !== binding.sessionId.toLowerCase()) return empty('rollout-thread-identity-mismatch');

  let fd;
  let before;
  let after;
  let head;
  let tail;
  let tailOffset;
  let retainedOrigin = false;
  try {
    fd = fs.openSync(transcriptPath, 'r');
    before = fs.fstatSync(fd, {bigint: true});
    if (!before.isFile()) return empty('transcript-not-regular-file');
    const size = Number(before.size);
    if (!Number.isSafeInteger(size) || size <= 0) return empty('transcript-empty-or-too-large');
    const requiredScan = inputScan || options.retryInputScan;
    const retained = requiredScan?.retainedCursor;
    if (snapshot?.maximumBytes !== undefined) {
      const retryBytes = Math.min(size, HEAD_BYTES) + (retained ? size - retained.anchorOffset : Math.min(size, MAX_TAIL_BYTES));
      if (retryBytes > snapshot.maximumBytes) return empty('transcript-path-changed-after-read');
    }
    head = readSlice(fd, 0, Math.min(size, HEAD_BYTES));
    if (retained) {
      const first = completeLines(head, 0, false)[0];
      if (typeof retained !== 'object' || Array.isArray(retained) ||
          Object.keys(retained).sort().join(',') !== 'anchorOffset,endOffset,headSha256,prefixSha256,signalsSha256,sourceId' ||
          !integer(retained.anchorOffset) || !integer(retained.endOffset) ||
          retained.endOffset <= retained.anchorOffset || retained.endOffset > size ||
          retained.sourceId !== `${before.dev}:${before.ino}` || !first ||
          !['headSha256', 'prefixSha256', 'signalsSha256'].every(key => /^[a-f0-9]{64}$/.test(retained[key])) ||
          retained.headSha256 !== crypto.createHash('sha256').update(first.bytes).digest('hex')) {
        return empty('native-input-evidence-changed');
      }
      if (size - retained.anchorOffset > MAX_RETAINED_BYTES) return empty('native-input-recovery-range-exceeded');
      // Read each byte once on the same descriptor and fixed snapshot size.
      // Keep bounded bytes/row views; rebuild every semantic sequence below.
      tailOffset = retained.anchorOffset;
      tail = Buffer.alloc(size - tailOffset);
      for (let offset = 0; offset < tail.length; offset += TAIL_BYTES) {
        tail.set(readSlice(fd, tailOffset + offset, Math.min(TAIL_BYTES, tail.length - offset)), offset);
      }
      retainedOrigin = true;
    } else {
      tailOffset = Math.max(0, size - TAIL_BYTES);
      tail = readSlice(fd, tailOffset, size - tailOffset);
      // A long native turn can exceed the initial chunk well before capacity
      // pressure. Extend only until its latest turn boundary is visible, within
      // a fixed local I/O budget and the same file snapshot.
      let tailBytes = TAIL_BYTES;
      const hasBoundary = () => {
        const rows = completeLines(tail, tailOffset, tailOffset > 0);
        // Context after reconciliation also verifies the original input prefix.
        return requiredScan ? retryOrigin(rows, binding, requiredScan.anchorHash) >= 0
          : retry ? retryOrigin(rows, binding, options.retryInputSha256) >= 0
          : rows.some((row) => parseRow(row)?.type === 'turn_context');
      };
      while (tailOffset > 0 && tailBytes < MAX_TAIL_BYTES && !hasBoundary()) {
        tailBytes *= 2;
        const expandedOffset = Math.max(0, size - tailBytes);
        tail = Buffer.concat([readSlice(fd, expandedOffset, tailOffset - expandedOffset), tail]);
        tailOffset = expandedOffset;
      }
    }
    after = fs.fstatSync(fd, {bigint: true});
  } catch (_) {
    return empty('transcript-read-failed');
  } finally {
    if (fd !== undefined) fs.closeSync(fd);
  }
  const identity = statIdentity(before);
  if (canonical(suppliedIdentity) !== canonical(identity)) return empty('transcript-changed-before-read');
  if (canonical(identity) !== canonical(statIdentity(after))) return empty('transcript-changed-during-read');
  const sourceUnchanged = () => {
    try {
      const supplied = path.resolve(binding.transcriptPath);
      const stat = fs.lstatSync(supplied, {bigint: true});
      return !stat.isSymbolicLink() && stat.isFile() &&
        canonical(statIdentity(stat)) === canonical(identity) && samePath(realPath(supplied), transcriptPath);
    } catch (_) { return false; }
  };
  if (snapshot) Object.assign(snapshot, {identity, size: Number(before.size), head, tail, tailOffset, transcriptPath, sourceUnchanged});
  if (!sourceUnchanged()) return empty('transcript-path-changed-after-read');
  // Parsing, media decoding and proof derivation can outlast the file read.
  // Recheck the same source after deriving a result; this is a bounded snapshot,
  // not an atomic transaction with the native writer's future appends.
  const finish = result => sourceUnchanged() ? result : empty('transcript-path-changed-after-read');

  const headRows = completeLines(head, 0, false);
  if (headRows.length === 0) return empty('session-meta-unavailable');
  const metaLine = parseRow(headRows[0]);
  const meta = metaLine?.type === 'session_meta' ? metaLine.payload : null;
  if (!meta || meta.id !== binding.sessionId || !text(meta.cwd) || !text(meta.cli_version)) {
    return empty('session-meta-mismatch');
  }
  if (!samePath(meta.cwd, binding.cwd)) return empty('session-cwd-mismatch');
  if ((retry || inputScan) && !['cli', 'vscode', 'exec', 'appServer'].includes(meta.source)) return empty('capacity-retry-root-source-unproven');
  // v2 root rollouts can have a UUID suffix; children can be unsuffixed.
  // The shared session/tree ID must equal the bound thread, independently of
  // the filename suffix. Keep the native caller's thread/tree isolation and
  // all subsequent input/continuation checks. The retained cursor starts at
  // turn_context, so a preceding task_started need not remain in its window.
  if (retry || inputScan) {
    if (match[5] && meta.multi_agent_version !== 'v2') return empty('capacity-retry-subagent-rollout');
    if (meta.multi_agent_version === 'v2' && (meta.session_id !== binding.sessionId ||
        meta.thread_source === 'subagent' || meta.parent_thread_id != null || meta.agent_path != null)) {
      return empty('capacity-retry-root-source-unproven');
    }
  }

  if (hasUnterminatedRecord(tail) || retainedOrigin && tail.at(-1) !== 0x0a) return empty('unterminated-tail-record');
  const tailRows = completeLines(tail, tailOffset, tailOffset > 0 && !retainedOrigin);
  if (retainedOrigin && tailRows.some(row => row.bytes.length > MAX_TAIL_BYTES)) {
    return empty('native-input-recovery-record-too-large');
  }
  if (tailRows.length === 0) return empty('bounded-tail-unavailable');
  if (inputScan) return finish(scanNativeInputs(tailRows, tail, tailOffset, binding, inputScan, identity,
    crypto.createHash('sha256').update(headRows[0].bytes).digest('hex'),
    `codex-rollout:${relative.split(path.sep).join('/')}`));
  let recoveredInterruptOffsets = [], inputProof = null;
  if (options.retryInputScan) {
    const evidence = scanNativeInputs(tailRows, tail, tailOffset, binding, options.retryInputScan, identity,
      crypto.createHash('sha256').update(headRows[0].bytes).digest('hex'),
      `codex-rollout:${relative.split(path.sep).join('/')}`);
    if (evidence.state !== 'observed' || !evidence.latestInputReconciled) return finish(empty('native-input-evidence-changed'));
    recoveredInterruptOffsets = evidence.recoveredInterruptOffsets || [];
    inputProof = evidence;
  }
  let association = retry ? continuationAssociation(tailRows, binding, liveHost.host, options.retryInputSha256,
    `codex-rollout:${relative.split(path.sep).join('/')}`, options.capturedInputHashes, accepted, recoveredInterruptOffsets) : null;
  if (retry && inputProof && association.state !== 'observed') {
    const goal = goalContinuation(tailRows, binding, liveHost.host, options.retryInputSha256,
      `codex-rollout:${relative.split(path.sep).join('/')}`, inputProof, accepted, recoveredInterruptOffsets);
    if (goal.state === 'observed') association = goal;
  }
  if (retry && inputProof && association.state !== 'observed') {
    const human = nativeHumanContinuation(tailRows, binding, liveHost.host, options.retryInputSha256,
      `codex-rollout:${relative.split(path.sep).join('/')}`, inputProof, accepted, recoveredInterruptOffsets);
    if (human.state === 'observed') association = human;
  }
  if (proofOnly) return finish(association);
  if (association && association.state !== 'observed') return empty('current-host-turn-mismatch');
  binding = association ? {...binding, turnId: association.conditions.turnId, model: association.conditions.model} : execution;
  let currentTurn = null;
  let currentModel = null;
  let currentCwd = null;
  let targetContext = null;
  let latestToken = null;
  let pendingGeneration = null;
  const generationEvents = [];

  for (const row of tailRows) {
    const line = parseRow(row);
    if (!line) return empty('invalid-complete-tail-record');
    if (line.type === 'turn_context') {
      const payload = line.payload;
      if (!payload || !text(payload.turn_id) || !text(payload.cwd) || !text(payload.model)) {
        return empty('invalid-turn-context');
      }
      currentTurn = payload.turn_id;
      currentModel = payload.model;
      currentCwd = payload.cwd;
      latestToken = null;
      pendingGeneration = null;
      if (currentTurn === binding.turnId) targetContext = {offset: row.offset, model: currentModel, cwd: currentCwd};
      continue;
    }
    if (currentTurn !== binding.turnId) continue;

    const payloadType = line.type === 'event_msg' ? line.payload?.type : null;
    const responseType = line.type === 'response_item' ? line.payload?.type : null;
    if (payloadType === 'context_compacted' || responseType === 'context_compaction' ||
        line.type === 'compacted' || completedCompaction(line, binding.sessionId, currentTurn)) {
      latestToken = null;
      pendingGeneration = 'compaction';
      generationEvents.push({kind: 'compaction', offset: row.offset});
      continue;
    }
    if (payloadType === 'model_rerouted') {
      latestToken = null;
      pendingGeneration = 'reroute';
      generationEvents.push({kind: 'reroute', offset: row.offset, toModel: line.payload?.to_model ?? null});
      if (text(line.payload?.to_model)) currentModel = line.payload.to_model;
      continue;
    }
    if (payloadType !== 'token_count') continue;
    const info = line.payload?.info;
    if (!info) {
      latestToken = null;
      pendingGeneration = 'unknown-token-count';
      continue;
    }
    const last = info.last_token_usage?.total_tokens;
    const cumulative = info.total_token_usage?.total_tokens;
    const window = info.model_context_window;
    const observedAtMs = Date.parse(line.timestamp);
    if (!integer(last) || !integer(cumulative) || !integer(window) || window === 0 ||
        cumulative < last || last > window || !integer(observedAtMs)) {
      latestToken = null;
      pendingGeneration = 'invalid-token-count';
      continue;
    }
    latestToken = {last, cumulative, window, observedAtMs, offset: row.offset,
      ordinal: integer(line.ordinal) ? line.ordinal : null};
    pendingGeneration = null;
  }

  if (!targetContext) return empty('current-turn-context-not-in-bounded-tail');
  if (currentTurn !== binding.turnId) return empty('current-turn-not-latest');
  if (!samePath(targetContext.cwd, binding.cwd) || !samePath(currentCwd, binding.cwd)) {
    return empty('turn-cwd-mismatch');
  }
  if (targetContext.model !== binding.model || currentModel !== binding.model) return empty('turn-model-mismatch');
  if (!latestToken) return empty(pendingGeneration || 'current-turn-token-count-unavailable');
  if (latestToken.observedAtMs > now) return empty('token-count-from-future');
  const validUntilMs = latestToken.observedAtMs + maxAgeMs;
  if (!Number.isSafeInteger(validUntilMs) || validUntilMs <= now) {
    return {...empty('token-count-expired'), observedAtMs: latestToken.observedAtMs,
      validUntilMs: Number.isSafeInteger(validUntilMs) ? validUntilMs : null,
      sampleAgeMs: now - latestToken.observedAtMs};
  }

  const conditions = {
    threadId: meta.id,
    turnId: binding.turnId,
    hostVersion: liveHost.host?.hostVersion ?? null,
    model: binding.model,
    contextGeneration: sha({threadId: meta.id, turnId: binding.turnId,
      recordedHostVersion: meta.cli_version, currentHost: liveHost.host && {
        threadId: liveHost.host.threadId, turnId: liveHost.host.turnId,
        model: liveHost.host.model, hostVersion: liveHost.host.hostVersion,
      },
      model: binding.model, sourceIdentity: {dev: identity.dev, ino: identity.ino},
      windowTokens: latestToken.window, turnContextOffset: targetContext.offset, generationEvents}),
  };
  const sourceRef = `codex-rollout:${relative.split(path.sep).join('/')}#byte=${latestToken.offset}`;
  const observationId = sha({conditions, identity, latestToken, sourceRef,
    recordedHostVersion: meta.cli_version, hostSourceRef: liveHost.host?.sourceRef ?? null});
  return finish({
    state: 'observed', reason: 'native-last-response-boundary', conditions,
    lastResponseTokens: latestToken.last, lastResponseScope: 'last-native-response-boundary',
    cumulativeTokens: latestToken.cumulative, cumulativeScope: 'session-cumulative-not-occupancy',
    windowTokens: latestToken.window, observedAtMs: latestToken.observedAtMs, validUntilMs,
    sampleAgeMs: now - latestToken.observedAtMs,
    observationId, sourceRef, recordedHostVersion: meta.cli_version,
    hostSourceRef: liveHost.host?.sourceRef ?? null,
    ...(association ? {turnAssociation: association} : {}),
  });
}

module.exports = {observeNativeTranscript, associateNativeTurn, inspectNativeInputs};
