'use strict';

const crypto = require('node:crypto');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');

const HEAD_BYTES = 64 * 1024;
const TAIL_BYTES = 1024 * 1024;
const MAX_TAIL_BYTES = 16 * TAIL_BYTES;
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

function inputHash(line) {
  const payload = line?.type === 'response_item' ? line.payload : null;
  const content = payload?.content;
  // This observed host wrapper is not extra human text. Match only the saved
  // Hook text; image completeness remains explicitly unverified below.
  const wrappedImage = Array.isArray(content) && content.length === 4 &&
    content[0]?.type === 'input_text' && typeof content[0].text === 'string' &&
    content[1]?.type === 'input_text' &&
    /^<image name=\[Image #[1-9]\d*\] path="[^"\u0000-\u001f]+">$/u.test(content[1].text || '') &&
    content[2]?.type === 'input_image' && content[3]?.type === 'input_text' && content[3].text === '</image>';
  if (payload?.type === 'message' && payload.role === 'user' && wrappedImage) {
    return crypto.createHash('sha256').update(content[0].text).digest('hex');
  }
  return payload?.type === 'message' && payload.role === 'user' &&
    Array.isArray(content) && content.some(item => item?.type === 'input_text') &&
    content.filter(item => item?.type === 'input_text').every(item => typeof item.text === 'string')
    ? crypto.createHash('sha256').update(content.filter(item => item?.type === 'input_text')
      .map(item => item.text).join('\n')).digest('hex') : null;
}

function retryOrigin(rows, binding, promptHash) {
  for (let index = 0; index + 1 < rows.length; index++) {
    const line = parseRow(rows[index]);
    if (line?.type !== 'turn_context' || line.payload?.turn_id !== binding.turnId) continue;
    for (let next = index + 1; next < rows.length; next++) {
      const candidate = parseRow(rows[next]);
      if (candidate?.type === 'response_item' && candidate.payload?.type === 'message' &&
          candidate.payload.role === 'developer') continue;
      if (inputHash(candidate) === promptHash) return index;
      break;
    }
  }
  return -1;
}

// An automatic retry is not a new human input. Prove the entire transition from
// the Hook-bound original input; a trigger claim or latest context alone cannot.
function capacityRetry(rows, binding, host, promptHash, sourceRef, captured = [promptHash]) {
  const start = retryOrigin(rows, binding, promptHash);
  if (start < 0) return empty('capacity-retry-original-input-unavailable');
  let turn = binding.turnId;
  let model = binding.model;
  let completedAt = null;
  let pending = null;
  let boundaryAt = Date.parse(parseRow(rows[start]).timestamp);
  let retryCount = 0;
  let retryOffset = null;
  const visited = new Set([turn]);
  let inputIndex = 0;
  for (let index = start; index < rows.length; index++) {
    const line = parseRow(rows[index]);
    if (!line) return empty('invalid-complete-tail-record');
    const payload = line.payload;
    if (line.type === 'response_item' && payload?.role === 'user') {
      if (inputHash(line) !== captured[inputIndex++]) return empty('capacity-retry-input-or-interruption-conflict');
      continue;
    }
    if (line.type === 'event_msg' && ['user_message', 'task_interrupted', 'turn_aborted',
          'task_cancelled', 'shutdown_complete'].includes(payload?.type)) {
      return empty('capacity-retry-input-or-interruption-conflict');
    }
    if (line.type === 'turn_context') {
      if (!text(payload?.turn_id) || !text(payload.model) || !text(payload.cwd) ||
          !samePath(payload.cwd, binding.cwd) || !integer(Date.parse(line.timestamp))) {
        return empty('capacity-retry-context-mismatch');
      }
      if (index === start && payload.model !== binding.model ||
          payload.turn_id !== (pending || turn) || completedAt !== null) {
        return empty('capacity-retry-turn-conflict');
      }
      if (pending && Date.parse(line.timestamp) < boundaryAt) return empty('capacity-retry-order-conflict');
      turn = payload.turn_id;
      model = payload.model;
      pending = null;
      continue;
    }
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
          attribution.root_turn_id !== next || !['capacity_retry_automatic', 'capacity_retry_manual'].includes(attribution.turn_trigger) ||
          attribution.parent_turn_id !== null || attribution.initiating_agent_path !== null ||
          !integer(at) || at < completedAt || ++retryCount > 64) return empty('capacity-retry-start-unproven');
      pending = next;
      visited.add(next);
      completedAt = null;
      boundaryAt = at;
      retryOffset = rows[index].offset;
    }
  }
  if (!retryCount || pending || completedAt !== null || turn !== host.turnId || model !== host.model) {
    return empty('capacity-retry-current-turn-unproven');
  }
  return {state: 'observed', reason: 'native-automatic-capacity-retry',
    originalTurnId: binding.turnId, retryCount,
    conditions: {threadId: binding.sessionId, turnId: turn, model, hostVersion: host.hostVersion},
    sourceRef: `${sourceRef}#byte=${retryOffset}`, hostSourceRef: host.sourceRef};
}

function associateNativeTurn(binding, host, promptHash, captured) {
  return observeNativeTranscript(binding, {now: Date.now(), maxAgeMs: 1,
    retryHost: host, retryInputSha256: promptHash, capturedInputHashes: captured});
}

// One file snapshot supplies both the human/control sequence and the old byte
// prefix. A later assistant/tool append may extend it without renewing evidence.
function scanNativeInputs(rows, tail, tailOffset, binding, scan, identity, headHash, sourceRef) {
  const start = retryOrigin(rows, binding, scan.anchorHash);
  if (start < 0) return empty('native-input-origin-unavailable');
  const anchorOffset = rows[start].offset;
  let turn = binding.turnId, model = null, originModel = null, inputIndex = 0, attachments = false;
  const signals = [], pendingInputs = [];
  for (let index = start; index < rows.length; index++) {
    const row = rows[index], line = parseRow(row), payload = line?.payload;
    if (!line) return empty('invalid-complete-tail-record');
    const digest = crypto.createHash('sha256').update(row.bytes).digest('hex');
    if (line.type === 'turn_context') {
      if (!text(payload?.turn_id) || !text(payload.model) || !text(payload.cwd) ||
          !samePath(payload.cwd, binding.cwd) || index === start && binding.model && payload.model !== binding.model) {
        return empty('native-input-context-conflict');
      }
      turn = payload.turn_id; model = payload.model;
      if (index === start) originModel = model;
      signals.push([row.offset, digest]);
    }
    const user = line.type === 'response_item' && payload?.role === 'user';
    const event = line.type === 'event_msg' ? payload?.type : null;
    if (user) {
      if (Array.isArray(payload.content) && payload.content.some(item => item?.type !== 'input_text')) attachments = true;
      signals.push([row.offset, digest]);
      const expected = scan.captured[inputIndex++];
      if (expected) {
        if (expected.recordSha256 ? expected.recordSha256 !== digest : expected.promptSha256 !== inputHash(line)) {
          return empty('native-captured-input-prefix-mismatch');
        }
      } else {
        const content = payload.content;
        const supported = payload.type === 'message' && Array.isArray(content) && content.length === 1 &&
          content[0]?.type === 'input_text' && typeof content[0].text === 'string';
        pendingInputs.push({turnId: turn, sourceRef: `${sourceRef}#byte=${row.offset}`,
          recordSha256: digest, itemId: payload.id ?? null, supported,
          ...(supported ? {prompt: content[0].text, promptSha256: inputHash(line)} : {})});
      }
    }
    if (line.type === 'compacted' || event === 'context_compacted') signals.push([row.offset, digest]);
    if (event && /^(?:task_|turn_|thread_settings_|model_rerouted|interrupt|shutdown|user_message)/u.test(event)) {
      if (!['task_started', 'task_complete', 'task_interrupted', 'turn_aborted', 'task_cancelled',
          'thread_settings_applied', 'model_rerouted', 'shutdown_complete', 'user_message'].includes(event)) {
        return empty('native-input-control-unrecognized');
      }
      signals.push([row.offset, digest]);
      if (event === 'model_rerouted' && text(payload.to_model)) model = payload.to_model;
      if (['task_interrupted', 'turn_aborted', 'task_cancelled', 'shutdown_complete', 'user_message'].includes(event)) {
        return empty('native-input-control-needs-reconciliation');
      }
    }
  }
  if (inputIndex < scan.captured.length) return empty('native-captured-input-prefix-incomplete');
  if (scan.host && (scan.host.threadId !== binding.sessionId || scan.host.turnId !== turn || scan.host.model !== model)) {
    return empty('native-input-current-host-conflict');
  }
  if (scan.expectedTurnId && scan.expectedTurnId !== turn) return empty('native-input-current-turn-conflict');
  const cursor = {sourceId: `${identity.dev}:${identity.ino}`, headSha256: headHash, anchorOffset,
    endOffset: tailOffset + tail.length, prefixSha256: crypto.createHash('sha256')
      .update(tail.subarray(anchorOffset - tailOffset)).digest('hex'), signalsSha256: sha(signals)};
  for (const expected of [scan.retainedCursor, scan.expectedCursor].filter(Boolean)) {
    const prefix = tail.subarray(anchorOffset - tailOffset, expected.endOffset - tailOffset);
    if (expected.sourceId !== cursor.sourceId || expected.headSha256 !== cursor.headSha256 ||
        expected.anchorOffset !== anchorOffset || expected.endOffset > cursor.endOffset ||
        expected.endOffset < anchorOffset || expected === scan.expectedCursor && expected.signalsSha256 !== cursor.signalsSha256 ||
        expected.prefixSha256 !== crypto.createHash('sha256').update(prefix).digest('hex')) {
      return empty('native-input-evidence-changed');
    }
  }
  return {state: 'observed', reason: 'bound-native-input-prefix', cursor, pendingInputs,
    capturedPrefixMatched: true, latestInputReconciled: pendingInputs.length === 0,
    latestNativeInputsComplete: pendingInputs.length === 0 && !attachments,
    currentTurnId: turn, currentModel: model, originModel, sourceRef, sourceReleaseAllowed: false,
    contentCoverage: attachments ? 'captured-text-only; attachments-unverified' : 'text-records'};
}

function inspectNativeInputs(binding, scan) {
  return observeNativeTranscript(binding, {now: Date.now(), maxAgeMs: 1, inputScan: scan});
}

// Read-only adapter over the one native rollout path supplied by the current Hook.
// The byte limits bound local I/O only; they are not model capacity or quality limits.
function observeNativeTranscript(binding, options = {}) {
  const inputScan = options.inputScan;
  if (!binding || !['transcriptPath', 'sessionId', 'turnId', 'cwd'].every((key) => text(binding[key])) ||
      !inputScan && !text(binding.model)) {
    return empty('binding-missing');
  }
  const now = options.now;
  const maxAgeMs = options.maxAgeMs;
  if (!integer(now) || !integer(maxAgeMs) || maxAgeMs === 0) return empty('observation-time-invalid');
  const proofOnly = Object.hasOwn(options, 'retryHost');
  const retry = proofOnly || Object.hasOwn(options, 'retryInputSha256') &&
    Object.hasOwn(options, 'currentHost') && options.currentHost?.turnId !== binding.turnId;
  const retryHost = proofOnly ? options.retryHost : options.currentHost;
  const liveHost = inputScan ? {host: null, reason: null} : retry ? currentHost({...binding, turnId: retryHost?.turnId,
    model: retryHost?.model}, {currentHost: retryHost}) : currentHost(binding, options);
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
  if ((retry || inputScan) && match[5]) return empty('capacity-retry-subagent-rollout');

  let fd;
  let before;
  let after;
  let head;
  let tail;
  let tailOffset;
  try {
    fd = fs.openSync(transcriptPath, 'r');
    before = fs.fstatSync(fd, {bigint: true});
    if (!before.isFile()) return empty('transcript-not-regular-file');
    const size = Number(before.size);
    if (!Number.isSafeInteger(size) || size <= 0) return empty('transcript-empty-or-too-large');
    head = readSlice(fd, 0, Math.min(size, HEAD_BYTES));
    tailOffset = Math.max(0, size - TAIL_BYTES);
    tail = readSlice(fd, tailOffset, size - tailOffset);
    // A long native turn can exceed the initial chunk well before capacity
    // pressure. Extend only until its latest turn boundary is visible, within
    // a fixed local I/O budget and the same file snapshot.
    let tailBytes = TAIL_BYTES;
    const hasBoundary = () => {
      const rows = completeLines(tail, tailOffset, tailOffset > 0);
      return inputScan ? retryOrigin(rows, binding, inputScan.anchorHash) >= 0
        : retry ? retryOrigin(rows, binding, options.retryInputSha256) >= 0
        : rows.some((row) => parseRow(row)?.type === 'turn_context');
    };
    while (tailOffset > 0 && tailBytes < MAX_TAIL_BYTES && !hasBoundary()) {
      tailBytes *= 2;
      const expandedOffset = Math.max(0, size - tailBytes);
      tail = Buffer.concat([readSlice(fd, expandedOffset, tailOffset - expandedOffset), tail]);
      tailOffset = expandedOffset;
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
  try {
    const supplied = path.resolve(binding.transcriptPath);
    const finalPathStat = fs.lstatSync(supplied, {bigint: true});
    if (finalPathStat.isSymbolicLink() || !finalPathStat.isFile() ||
        canonical(statIdentity(finalPathStat)) !== canonical(identity) ||
        !samePath(realPath(supplied), transcriptPath)) {
      return empty('transcript-path-changed-after-read');
    }
  } catch (_) {
    return empty('transcript-path-changed-after-read');
  }

  const headRows = completeLines(head, 0, false);
  if (headRows.length === 0) return empty('session-meta-unavailable');
  const metaLine = parseRow(headRows[0]);
  const meta = metaLine?.type === 'session_meta' ? metaLine.payload : null;
  if (!meta || meta.id !== binding.sessionId || !text(meta.cwd) || !text(meta.cli_version)) {
    return empty('session-meta-mismatch');
  }
  if (!samePath(meta.cwd, binding.cwd)) return empty('session-cwd-mismatch');
  if ((retry || inputScan) && !['cli', 'vscode', 'exec', 'appServer'].includes(meta.source)) return empty('capacity-retry-root-source-unproven');

  if (hasUnterminatedRecord(tail)) return empty('unterminated-tail-record');
  const tailRows = completeLines(tail, tailOffset, tailOffset > 0);
  if (tailRows.length === 0) return empty('bounded-tail-unavailable');
  if (inputScan) return scanNativeInputs(tailRows, tail, tailOffset, binding, inputScan, identity,
    crypto.createHash('sha256').update(headRows[0].bytes).digest('hex'),
    `codex-rollout:${relative.split(path.sep).join('/')}`);
  const association = retry ? capacityRetry(tailRows, binding, liveHost.host, options.retryInputSha256,
    `codex-rollout:${relative.split(path.sep).join('/')}`, options.capturedInputHashes) : null;
  if (proofOnly) return association;
  if (association && association.state !== 'observed') return empty('current-host-turn-mismatch');
  if (association) binding = {...binding, turnId: association.conditions.turnId, model: association.conditions.model};
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
        line.type === 'compacted') {
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
  return {
    state: 'observed', reason: 'native-last-response-boundary', conditions,
    lastResponseTokens: latestToken.last, lastResponseScope: 'last-native-response-boundary',
    cumulativeTokens: latestToken.cumulative, cumulativeScope: 'session-cumulative-not-occupancy',
    windowTokens: latestToken.window, observedAtMs: latestToken.observedAtMs, validUntilMs,
    sampleAgeMs: now - latestToken.observedAtMs,
    observationId, sourceRef, recordedHostVersion: meta.cli_version,
    hostSourceRef: liveHost.host?.sourceRef ?? null,
    ...(association ? {turnAssociation: association} : {}),
  };
}

module.exports = {observeNativeTranscript, associateNativeTurn, inspectNativeInputs};
