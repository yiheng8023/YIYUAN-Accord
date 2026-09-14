'use strict';

const crypto = require('node:crypto');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');

const HEAD_BYTES = 64 * 1024;
const TAIL_BYTES = 1024 * 1024;
const UUID = '[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}';
const ROLLOUT_NAME = new RegExp(
  `^rollout-(\\d{4})-(\\d{2})-(\\d{2})T\\d{2}-\\d{2}-\\d{2}-(${UUID})(?:_(${UUID}))?\\.jsonl$`,
  'i',
);

function text(value) {
  return typeof value === 'string' && value.length > 0;
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
    observationId: null, sourceRef: null,
  };
}

function samePath(left, right) {
  const a = path.resolve(left);
  const b = path.resolve(right);
  return process.platform === 'win32' ? a.toLowerCase() === b.toLowerCase() : a === b;
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

// Read-only adapter over the one native rollout path supplied by the current Hook.
// The byte limits bound local I/O only; they are not model capacity or quality limits.
function observeNativeTranscript(binding, options = {}) {
  if (!binding || !['transcriptPath', 'sessionId', 'turnId', 'cwd', 'model'].every((key) => text(binding[key]))) {
    return empty('binding-missing');
  }
  const now = options.now;
  const maxAgeMs = options.maxAgeMs;
  if (!integer(now) || !integer(maxAgeMs) || maxAgeMs === 0) return empty('observation-time-invalid');

  let sessionsRoot;
  let transcriptPath;
  let suppliedIdentity;
  try {
    sessionsRoot = fs.realpathSync(options.sessionsRoot || defaultSessionsRoot());
    const supplied = path.resolve(binding.transcriptPath);
    const suppliedStat = fs.lstatSync(supplied, {bigint: true});
    if (suppliedStat.isSymbolicLink() || !suppliedStat.isFile()) return empty('transcript-not-regular-file');
    suppliedIdentity = statIdentity(suppliedStat);
    transcriptPath = fs.realpathSync(supplied);
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
  try {
    fd = fs.openSync(transcriptPath, 'r');
    before = fs.fstatSync(fd, {bigint: true});
    if (!before.isFile()) return empty('transcript-not-regular-file');
    const size = Number(before.size);
    if (!Number.isSafeInteger(size) || size <= 0) return empty('transcript-empty-or-too-large');
    head = readSlice(fd, 0, Math.min(size, HEAD_BYTES));
    tailOffset = Math.max(0, size - TAIL_BYTES);
    tail = readSlice(fd, tailOffset, size - tailOffset);
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
        !samePath(fs.realpathSync(supplied), transcriptPath)) {
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

  if (hasUnterminatedRecord(tail)) return empty('unterminated-tail-record');
  const tailRows = completeLines(tail, tailOffset, tailOffset > 0);
  if (tailRows.length === 0) return empty('bounded-tail-unavailable');
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
  if (!Number.isSafeInteger(validUntilMs) || validUntilMs <= now) return empty('token-count-expired');

  const conditions = {
    threadId: meta.id,
    turnId: binding.turnId,
    hostVersion: meta.cli_version,
    model: binding.model,
    contextGeneration: sha({threadId: meta.id, turnId: binding.turnId, hostVersion: meta.cli_version,
      model: binding.model, sourceIdentity: {dev: identity.dev, ino: identity.ino},
      windowTokens: latestToken.window, turnContextOffset: targetContext.offset, generationEvents}),
  };
  const sourceRef = `codex-rollout:${relative.split(path.sep).join('/')}#byte=${latestToken.offset}`;
  const observationId = sha({conditions, identity, latestToken, sourceRef});
  return {
    state: 'observed', reason: 'native-last-response-boundary', conditions,
    lastResponseTokens: latestToken.last, lastResponseScope: 'last-native-response-boundary',
    cumulativeTokens: latestToken.cumulative, cumulativeScope: 'session-cumulative-not-occupancy',
    windowTokens: latestToken.window, observedAtMs: latestToken.observedAtMs, validUntilMs,
    observationId, sourceRef,
  };
}

module.exports = {observeNativeTranscript};
