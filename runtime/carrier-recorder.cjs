'use strict';

// Durable scope recorder for runtime/carrier-handoff.cjs.
//
// Opening this module is always explicit. It owns only a caller-selected new
// database file or an existing database carrying this exact identity/schema.
// It arbitrates cooperating writers; it is not an OS lock, authentication,
// transfer authorization, native-effect replay, or proof of task completion.

const crypto = require('node:crypto');
const fs = require('node:fs');
const pathModule = require('node:path');
const {isDeepStrictEqual} = require('node:util');

const MODULE_ID = 'yiyuan-accord/carrier-recorder';
const SCHEMA_VERSION = '1';
const DEFAULT_BUSY_TIMEOUT_MS = 5000;
const MAX_BUSY_TIMEOUT_MS = 30000;
const MAX_REF = 4096;
const MAX_STATE_BYTES = 16 * 1024 * 1024;

const EXPECTED_COLUMNS = Object.freeze({
  metadata: [
    ['key', 'TEXT', 1, 1],
    ['value', 'TEXT', 1, 0],
  ],
  scopes: [
    ['scope_ref', 'TEXT', 1, 1],
    ['writer_thread_id', 'TEXT', 1, 0],
    ['active_transfer_id', 'TEXT', 0, 0],
    ['fence_token', 'TEXT', 1, 0],
  ],
  transfers: [
    ['transfer_id', 'TEXT', 1, 1],
    ['scope_ref', 'TEXT', 1, 0],
    ['plan_digest', 'TEXT', 1, 0],
    ['revision', 'INTEGER', 1, 0],
    ['state_json', 'TEXT', 1, 0],
    ['settled', 'INTEGER', 1, 0],
  ],
});

class CarrierRecorderError extends Error {
  constructor(code, message, options = {}) {
    super(message, options.cause ? {cause: options.cause} : undefined);
    this.name = 'CarrierRecorderError';
    this.code = code;
  }
}

function reject(code, message, options) {
  throw new CarrierRecorderError(code, message, options);
}

function plainObject(value) {
  if (!value || typeof value !== 'object' || Array.isArray(value)) return false;
  const prototype = Object.getPrototypeOf(value);
  return prototype === Object.prototype || prototype === null;
}

function text(value, name) {
  if (typeof value !== 'string' || !value.trim() || value.length > MAX_REF) {
    throw new TypeError(`${name} must be a nonempty bounded string`);
  }
  return value;
}

function safeInteger(value, name) {
  if (!Number.isSafeInteger(value) || value < 0) {
    throw new TypeError(`${name} must be a nonnegative safe integer`);
  }
  return value;
}

function cloneData(value, seen = new Set()) {
  if (value === null || typeof value === 'string' || typeof value === 'boolean') return value;
  if (typeof value === 'number') {
    if (!Number.isFinite(value)) throw new TypeError('state contains a non-finite number');
    return value;
  }
  if (typeof value !== 'object') throw new TypeError('state contains a non-data value');
  if (seen.has(value)) throw new TypeError('state contains a cycle');
  seen.add(value);
  let result;
  if (Array.isArray(value)) {
    result = value.map((item) => cloneData(item, seen));
  } else {
    if (!plainObject(value)) throw new TypeError('state contains a non-plain object');
    result = {};
    for (const [key, item] of Object.entries(value)) {
      if (item === undefined) throw new TypeError(`state.${key} is undefined`);
      Object.defineProperty(result, key, {
        value: cloneData(item, seen), enumerable: true, writable: true, configurable: true,
      });
    }
  }
  seen.delete(value);
  return result;
}

function freezeDeep(value) {
  if (value && typeof value === 'object' && !Object.isFrozen(value)) {
    for (const item of Object.values(value)) freezeDeep(item);
    Object.freeze(value);
  }
  return value;
}

function immutable(value) {
  return freezeDeep(cloneData(value));
}

function stateText(value) {
  if (!plainObject(value)) throw new TypeError('state must be a plain object');
  const normalized = cloneData(value);
  const encoded = JSON.stringify(normalized);
  if (Buffer.byteLength(encoded, 'utf8') > MAX_STATE_BYTES) {
    throw new TypeError('state exceeds the recorder size limit');
  }
  return {normalized, encoded};
}

function parseState(encoded) {
  try {
    const value = JSON.parse(encoded);
    if (!plainObject(value)) throw new TypeError('recorded state is not an object');
    return immutable(value);
  } catch (cause) {
    reject('CORRUPT_RECORD', 'recorded state is invalid JSON data', {cause});
  }
}

function exactLease(value, name = 'expectedLease') {
  if (!plainObject(value)) throw new TypeError(`${name} must be an object`);
  const keys = Object.keys(value).sort();
  const expected = ['scopeRef', 'token', 'transferId', 'writerThreadId'].sort();
  if (keys.length !== expected.length || keys.some((key, index) => key !== expected[index])) {
    throw new TypeError(`${name} has unsupported fields`);
  }
  return immutable({
    scopeRef: text(value.scopeRef, `${name}.scopeRef`),
    transferId: text(value.transferId, `${name}.transferId`),
    token: text(value.token, `${name}.token`),
    writerThreadId: text(value.writerThreadId, `${name}.writerThreadId`),
  });
}

function token() {
  return crypto.randomBytes(32).toString('hex');
}

function rotatedToken(previous) {
  let next = token();
  while (next === previous) next = token();
  return next;
}

function inactiveScopeSnapshot(value, scopeRef) {
  if (!plainObject(value)) throw new TypeError('expectedScope must be an object');
  const keys = Object.keys(value).sort();
  const expected = ['activeTransferId', 'scopeRef', 'token', 'writerThreadId'].sort();
  if (keys.length !== expected.length || keys.some((key, index) => key !== expected[index])) {
    throw new TypeError('expectedScope has unsupported fields');
  }
  const snapshot = immutable({
    scopeRef: text(value.scopeRef, 'expectedScope.scopeRef'),
    writerThreadId: text(value.writerThreadId, 'expectedScope.writerThreadId'),
    activeTransferId: value.activeTransferId,
    token: text(value.token, 'expectedScope.token'),
  });
  if (snapshot.scopeRef !== scopeRef) throw new TypeError('expectedScope scope differs');
  if (snapshot.activeTransferId !== null) {
    throw new TypeError('expectedScope must describe an inactive scope');
  }
  return snapshot;
}

function loadDatabaseSync() {
  try {
    const {DatabaseSync} = require('node:sqlite');
    if (typeof DatabaseSync !== 'function') throw new TypeError('DatabaseSync export is absent');
    return DatabaseSync;
  } catch (cause) {
    reject('SQLITE_UNAVAILABLE', 'Node built-in node:sqlite DatabaseSync is unavailable', {cause});
  }
}

function statOrdinary(databasePath, missingAllowed) {
  let stat;
  try {
    stat = fs.lstatSync(databasePath);
  } catch (error) {
    if (error && error.code === 'ENOENT' && missingAllowed) return null;
    if (error && error.code === 'ENOENT') reject('DATABASE_MISSING', 'recorder database does not exist');
    throw error;
  }
  if (!stat.isFile() || stat.isSymbolicLink()) {
    reject('DATABASE_PATH_UNSAFE', 'recorder path must identify an ordinary file');
  }
  if (stat.nlink !== 1) {
    reject('DATABASE_PATH_UNSAFE', 'recorder database must not be hard-linked');
  }
  return stat;
}

function validatePath(databasePath, create) {
  if (typeof databasePath !== 'string' || !pathModule.isAbsolute(databasePath) ||
      databasePath.includes('\0')) {
    throw new TypeError('path must be an absolute ordinary file path');
  }
  const parent = pathModule.dirname(databasePath);
  const parentStat = fs.lstatSync(parent);
  if (!parentStat.isDirectory() || parentStat.isSymbolicLink()) {
    reject('DATABASE_PATH_UNSAFE', 'recorder parent must be an ordinary directory');
  }
  if (create) {
    if (statOrdinary(databasePath, true)) {
      reject('DATABASE_EXISTS', 'create requires a new recorder database path');
    }
  } else {
    statOrdinary(databasePath, false);
  }
  return databasePath;
}

function columnsMatch(database, table) {
  const rows = database.prepare(`PRAGMA table_info(${table})`).all();
  const expected = EXPECTED_COLUMNS[table];
  return rows.length === expected.length && rows.every((row, index) =>
    row.name === expected[index][0] && String(row.type).toUpperCase() === expected[index][1] &&
    row.notnull === expected[index][2] && row.pk === expected[index][3]);
}

function assertIdentityAndSchema(database) {
  let objects;
  try {
    objects = database.prepare(
      "SELECT type, name FROM sqlite_master WHERE name NOT LIKE 'sqlite_%' ORDER BY type, name",
    ).all();
  } catch (cause) {
    reject('DATABASE_INVALID', 'recorder database is not a readable SQLite database', {cause});
  }
  if (objects.length !== 3 || objects.some((row) => row.type !== 'table') ||
      objects.map((row) => row.name).sort().join(',') !== 'metadata,scopes,transfers') {
    reject('SCHEMA_UNKNOWN', 'recorder database has an unknown schema');
  }
  for (const table of Object.keys(EXPECTED_COLUMNS)) {
    if (!columnsMatch(database, table)) reject('SCHEMA_UNKNOWN', 'recorder schema shape differs');
  }
  const metadata = database.prepare('SELECT key, value FROM metadata ORDER BY key').all();
  if (metadata.length !== 2 || metadata[0]?.key !== 'module_id' || metadata[0]?.value !== MODULE_ID ||
      metadata[1]?.key !== 'schema_version' || metadata[1]?.value !== SCHEMA_VERSION) {
    reject('SCHEMA_UNKNOWN', 'recorder database identity or version differs');
  }
  const check = database.prepare('PRAGMA quick_check(1)').get();
  if (!check || check.quick_check !== 'ok') reject('DATABASE_INVALID', 'recorder database failed quick_check');
}

function assertStoredRows(database) {
  const scopes = database.prepare(
    'SELECT scope_ref, writer_thread_id, active_transfer_id, fence_token FROM scopes',
  ).all();
  const transfers = database.prepare(
    'SELECT transfer_id, scope_ref, plan_digest, revision, state_json, settled FROM transfers',
  ).all();
  const byTransfer = new Map(transfers.map((row) => [row.transfer_id, row]));
  const byScope = new Map(scopes.map((row) => [row.scope_ref, row]));
  for (const scope of scopes) {
    text(scope.scope_ref, 'stored scope');
    text(scope.writer_thread_id, 'stored writer');
    text(scope.fence_token, 'stored fence token');
    if (scope.active_transfer_id !== null) {
      text(scope.active_transfer_id, 'stored active transfer');
      const active = byTransfer.get(scope.active_transfer_id);
      if (!active || active.scope_ref !== scope.scope_ref || active.settled !== 0) {
        reject('CORRUPT_RECORD', 'scope active transfer is inconsistent');
      }
      const state = parseState(active.state_json);
      if (state.writerThreadId !== scope.writer_thread_id) {
        reject('CORRUPT_RECORD', 'scope writer differs from its active record');
      }
    }
  }
  for (const transfer of transfers) {
    text(transfer.transfer_id, 'stored transfer');
    text(transfer.scope_ref, 'stored transfer scope');
    text(transfer.plan_digest, 'stored plan digest');
    safeInteger(transfer.revision, 'stored revision');
    if (transfer.settled !== 0 && transfer.settled !== 1) {
      reject('CORRUPT_RECORD', 'stored settlement flag is invalid');
    }
    const scope = byScope.get(transfer.scope_ref);
    const state = parseState(transfer.state_json);
    if (!scope || state.transferId !== transfer.transfer_id || state.scopeRef !== transfer.scope_ref ||
        state.planDigest !== transfer.plan_digest) {
      reject('CORRUPT_RECORD', 'stored transfer identity is inconsistent');
    }
    if (transfer.settled === 0 && scope.active_transfer_id !== transfer.transfer_id) {
      reject('CORRUPT_RECORD', 'unsettled transfer is not active');
    }
  }
}

function createSchema(database) {
  database.exec('PRAGMA journal_mode=WAL');
  database.exec('PRAGMA synchronous=FULL');
  database.exec('PRAGMA foreign_keys=ON');
  database.exec('BEGIN EXCLUSIVE');
  try {
    database.exec(`
      CREATE TABLE metadata (
        key TEXT PRIMARY KEY NOT NULL,
        value TEXT NOT NULL
      ) WITHOUT ROWID;
      CREATE TABLE scopes (
        scope_ref TEXT PRIMARY KEY NOT NULL,
        writer_thread_id TEXT NOT NULL,
        active_transfer_id TEXT,
        fence_token TEXT NOT NULL
      ) WITHOUT ROWID;
      CREATE TABLE transfers (
        transfer_id TEXT PRIMARY KEY NOT NULL,
        scope_ref TEXT NOT NULL,
        plan_digest TEXT NOT NULL,
        revision INTEGER NOT NULL CHECK(revision >= 0),
        state_json TEXT NOT NULL,
        settled INTEGER NOT NULL CHECK(settled IN (0, 1))
      ) WITHOUT ROWID;
    `);
    const insert = database.prepare('INSERT INTO metadata(key, value) VALUES (?, ?)');
    insert.run('module_id', MODULE_ID);
    insert.run('schema_version', SCHEMA_VERSION);
    database.exec('COMMIT');
  } catch (cause) {
    try { database.exec('ROLLBACK'); } catch (_) {}
    throw cause;
  }
}

function transaction(database, mode, callback) {
  database.exec(`BEGIN ${mode}`);
  try {
    const result = callback();
    database.exec('COMMIT');
    return result;
  } catch (cause) {
    try { database.exec('ROLLBACK'); } catch (_) {}
    throw cause;
  }
}

function validateDatabase(database) {
  return transaction(database, 'DEFERRED', () => {
    try {
      assertIdentityAndSchema(database);
      assertStoredRows(database);
    } catch (cause) {
      if (cause instanceof CarrierRecorderError) throw cause;
      reject('CORRUPT_RECORD', 'recorder database contains invalid stored data', {cause});
    }
  });
}

function scopeView(row) {
  return immutable({
    scopeRef: row.scope_ref,
    writerThreadId: row.writer_thread_id,
    activeTransferId: row.active_transfer_id,
    token: row.fence_token,
  });
}

function leaseView(scope) {
  return immutable({
    scopeRef: scope.scope_ref,
    transferId: scope.active_transfer_id,
    token: scope.fence_token,
    writerThreadId: scope.writer_thread_id,
  });
}

function externalStopped(state, lease) {
  const closed = state.nativeClosed, source = state.source, target = state.target;
  return state.kind === 'external-source-handoff/v1' && ['held', 'cancelled-held'].includes(state.phase) &&
    state.pendingEffect === null && state.turnStarts === 0 && state.writer === 'source' &&
    source?.kind === 'codex-mcp-request-metadata' && source.threadId === source.sessionTreeId &&
    ['threadId', 'sessionTreeId', 'turnId', 'callId'].every(key => typeof source[key] === 'string' && source[key].trim()) &&
    Number.isSafeInteger(state.plan?.deadlineMs) && state.plan.deadlineMs > 0 &&
    state.planDigest === stateDigest({plan: state.plan, source, basis: state.basis}) &&
    state.writerThreadId === source.threadId && lease.writerThreadId === source.threadId &&
    lease.transferId === state.transferId && state.sourceRecovery === 'retained' &&
    !state.intake && !state.firstContinuation && !state.postReleaseTurn && !state.release &&
    ['prepared', 'target-created'].includes(state.failure?.priorPhase) &&
    closed?.closed === true && closed.primaryProcessClosed === true && closed.exitObserved === true &&
    closed.closeObserved === true && closed.exitCode === 0 && closed.forced === false && closed.signal === null &&
    Number.isSafeInteger(closed.pid) && closed.pid > 0 &&
    closed.recoveryRequired === false && closed.terminationAttempt === null &&
    (target === null && state.lastNativeReceipt == null || target?.threadId &&
      state.lastNativeReceipt?.method === 'thread/start' &&
      state.lastNativeReceipt.request?.method === 'thread/start' &&
      state.lastNativeReceipt.request.requestRef?.method === 'thread/start' &&
      state.lastNativeReceipt.response?.thread?.id === target.threadId &&
      state.lastNativeReceipt.response.thread.ephemeral === false &&
      state.lastNativeReceipt.request?.requestRef?.connectionId === state.connection?.connectionId);
}
const stateDigest = value => crypto.createHash('sha256').update(JSON.stringify(value)).digest('hex');

function externalNaturalClose(closed) {
  return closed?.closed === true && closed.primaryProcessClosed === true && closed.exitObserved === true &&
    closed.closeObserved === true && closed.exitCode === 0 && closed.forced === false && closed.signal === null &&
    Number.isSafeInteger(closed.pid) && closed.pid > 0 && closed.recoveryRequired === false && closed.terminationAttempt === null;
}

function externalIntakeReceipt(state, receipt, connection) {
  const request = receipt?.request;
  return receipt?.method === 'turn/start' && request?.method === 'turn/start' &&
    request.params?.threadId === state.target.threadId &&
    isDeepStrictEqual(request.params.sandboxPolicy, {type: 'readOnly'}) &&
    request.requestRef?.method === 'turn/start' && request.requestRef.connectionId === connection?.connectionId &&
    request.requestRef.hostVersion === connection?.hostVersion &&
    typeof request.requestRef.requestId === 'string' && request.requestRef.requestId.trim() &&
    receipt.response?.turn?.id === state.intake.turnId;
}

function externalStoppedIntake(state, lease) {
  const intake = state.intake;
  if (!(state.writer === 'source' && state.writerThreadId === state.source.threadId &&
    lease.writerThreadId === state.source.threadId && state.sourceRecovery === 'retained' &&
    state.turnStarts === 1 && state.pendingEffect === null &&
    intake?.threadId === state.target.threadId && typeof intake.turnId === 'string' && intake.turnId.trim() &&
    intake.terminal === 'completed' && !state.stoppedTurn && !state.firstContinuation &&
    !state.postReleaseTurn && !state.release && !state.verification?.commit)) return false;
  if (['intake-complete', 'awaiting-intake-review'].includes(state.failure?.priorPhase)) {
    return externalIntakeReceipt(state, state.lastNativeReceipt, state.connection);
  }
  const prior = state.priorNative, receipt = state.lastNativeReceipt, request = receipt?.request;
  if (state.failure?.priorPhase !== 'write-policy-transition' || state.plan?.sandbox !== 'workspace-write' ||
      typeof state.verification?.writePrepare !== 'string' || !state.verification.writePrepare.trim() ||
      !externalNaturalClose(prior?.closure) || typeof prior?.connection?.connectionId !== 'string' ||
      !prior.connection.connectionId.trim() || prior.connection.connectionId === state.connection?.connectionId ||
      prior.connection.hostVersion !== state.connection?.hostVersion ||
      !externalIntakeReceipt(state, prior.intakeReceipt, prior.connection)) return false;
  if (isDeepStrictEqual(receipt, prior.intakeReceipt)) return !Object.hasOwn(state, 'writePolicy');
  return receipt?.method === 'thread/resume' && request?.method === 'thread/resume' &&
    isDeepStrictEqual(request.params, {threadId: state.target.threadId, excludeTurns: true,
      sandbox: 'workspace-write', approvalPolicy: 'never', config: {
        'sandbox_workspace_write.writable_roots': [], 'sandbox_workspace_write.network_access': false,
        'sandbox_workspace_write.exclude_tmpdir_env_var': true, 'sandbox_workspace_write.exclude_slash_tmp': true}}) &&
    request.requestRef?.method === 'thread/resume' && request.requestRef.connectionId === state.connection?.connectionId &&
    request.requestRef.hostVersion === state.connection?.hostVersion &&
    typeof request.requestRef.requestId === 'string' && request.requestRef.requestId.trim() &&
    receipt.response?.thread?.id === state.target.threadId && receipt.response.thread.ephemeral === false &&
    isDeepStrictEqual(state.writePolicy?.resumeRequest, request.requestRef) &&
    isDeepStrictEqual(state.writePolicy.sandbox, receipt.response.sandbox || null);
}

function externalStoppedTarget(state, lease) {
  const source = state.source, target = state.target, closed = state.nativeClosed, pending = state.pendingEffect;
  return state.kind === 'external-source-handoff/v1' && ['held', 'cancelled-held'].includes(state.phase) &&
    source?.kind === 'codex-mcp-request-metadata' && source.threadId === source.sessionTreeId &&
    ['threadId', 'turnId', 'callId'].every(k => typeof source[k] === 'string' && source[k].trim()) &&
    typeof target?.threadId === 'string' && target.threadId !== source.threadId &&
    (state.writer === 'target' && state.writerThreadId === target.threadId && lease.writerThreadId === target.threadId ||
      externalStoppedIntake(state, lease)) &&
    ['retained', 'controller-owned'].includes(state.sourceRecovery) &&
    typeof state.failure?.code === 'string' && state.failure.code.trim() &&
    ['connectionId', 'hostVersion'].every(k => typeof state.connection?.[k] === 'string' && state.connection[k].trim()) &&
    lease.transferId === state.transferId && state.scopeRef === lease.scopeRef &&
    Number.isSafeInteger(state.turnStarts) && state.turnStarts > 0 &&
    Number.isSafeInteger(state.plan?.deadlineMs) && state.plan.deadlineMs > 0 &&
    state.planDigest === stateDigest({plan: state.plan, source, basis: state.basis}) &&
    externalNaturalClose(closed) &&
    (pending === null || pending?.kind === 'native-turn' && pending.threadId === target.threadId && typeof pending.turnId === 'string' ||
      pending?.kind === 'native-request' && pending.method === 'turn/start' && pending.params?.threadId === target.threadId &&
      pending.requestRef?.connectionId === state.connection?.connectionId && pending.requestRef?.method === 'turn/start' &&
      typeof pending.requestRef?.requestId === 'string');
}

function noteUnverifiedClose(cause, closeError) {
  const code = /^[A-Z][A-Z0-9_]{0,63}$/.test(closeError?.code || '') ? closeError.code : 'RECORDER_CLOSE_FAILED';
  try { Object.defineProperty(cause, 'recorderCleanup', {value: {state: 'close-unverified', code}, configurable: true}); }
  catch (_) { /* Preserve even a non-extensible original exception. */ }
}

function openCarrierRecorder(options) {
  if (!plainObject(options)) throw new TypeError('options must be an object');
  for (const key of Object.keys(options)) {
    if (!['path', 'create', 'busyTimeoutMs'].includes(key)) {
      throw new TypeError(`unsupported option: ${key}`);
    }
  }
  const create = options.create === true;
  if (Object.hasOwn(options, 'create') && typeof options.create !== 'boolean') {
    throw new TypeError('create must be a boolean');
  }
  const busyTimeoutMs = Object.hasOwn(options, 'busyTimeoutMs') ? options.busyTimeoutMs : DEFAULT_BUSY_TIMEOUT_MS;
  if (!Number.isInteger(busyTimeoutMs) || busyTimeoutMs < 0 || busyTimeoutMs > MAX_BUSY_TIMEOUT_MS) {
    throw new TypeError(`busyTimeoutMs must be an integer from 0 through ${MAX_BUSY_TIMEOUT_MS}`);
  }
  const databasePath = validatePath(options.path, create);
  const DatabaseSync = loadDatabaseSync();
  let database, getScope, getTransfer;
  try {
    if (create) {
      const descriptor = fs.openSync(databasePath, 'wx', 0o600);
      fs.closeSync(descriptor);
      statOrdinary(databasePath, false);
      database = new DatabaseSync(databasePath, {allowExtension: false, timeout: busyTimeoutMs});
      createSchema(database);
      validateDatabase(database);
    } else {
      let inspection, inspectionFailure;
      try {
        inspection = new DatabaseSync(databasePath, {
          readOnly: true, allowExtension: false, timeout: busyTimeoutMs,
        });
        validateDatabase(inspection);
      } catch (cause) { inspectionFailure = cause; throw cause; }
      finally {
        if (inspection) {
          try { inspection.close(); } catch (closeError) {
            noteUnverifiedClose(inspectionFailure || closeError, closeError);
            if (!inspectionFailure) throw closeError;
          }
        }
      }
      statOrdinary(databasePath, false);
      database = new DatabaseSync(databasePath, {allowExtension: false, timeout: busyTimeoutMs});
      validateDatabase(database);
      database.exec('PRAGMA synchronous=FULL');
      database.exec(`PRAGMA busy_timeout=${busyTimeoutMs}`);
    }
    getScope = database.prepare(
      'SELECT scope_ref, writer_thread_id, active_transfer_id, fence_token FROM scopes WHERE scope_ref = ?',
    );
    getTransfer = database.prepare(
      'SELECT transfer_id, scope_ref, plan_digest, revision, state_json, settled FROM transfers WHERE transfer_id = ?',
    );
  } catch (cause) {
    if (database) {
      try { database.close(); } catch (closeError) { noteUnverifiedClose(cause, closeError); }
    }
    throw cause;
  }

  let closed = false;
  const ensureOpen = () => {
    if (closed) reject('RECORDER_CLOSED', 'carrier recorder is closed');
  };

  function bindScope(scopeRef, writerThreadId) {
    ensureOpen();
    text(scopeRef, 'scopeRef');
    text(writerThreadId, 'writerThreadId');
    return transaction(database, 'DEFERRED', () => {
      const prior = getScope.get(scopeRef);
      if (prior) {
        if (prior.active_transfer_id !== null) reject('SCOPE_BUSY', 'scope has an active transfer');
        if (prior.writer_thread_id !== writerThreadId) {
          reject('WRITER_CONFLICT', 'scope is already bound to another writer');
        }
        return immutable({created: false, scope: scopeView(prior)});
      }
      const fenceToken = token();
      database.prepare(
        'INSERT INTO scopes(scope_ref, writer_thread_id, active_transfer_id, fence_token) VALUES (?, ?, NULL, ?)',
      ).run(scopeRef, writerThreadId, fenceToken);
      return immutable({created: true, scope: {
        scopeRef, writerThreadId, activeTransferId: null, token: fenceToken,
      }});
    });
  }

  function readScope(scopeRef) {
    ensureOpen();
    text(scopeRef, 'scopeRef');
    const row = getScope.get(scopeRef);
    if (!row) reject('SCOPE_NOT_FOUND', 'scope is not bound');
    return scopeView(row);
  }

  function claimScope(scopeRef, expectedScope) {
    // The caller separately verifies that the previous controller is quiescent.
    // This rotates a cooperating-controller fence; it grants no writer authority.
    ensureOpen();
    text(scopeRef, 'scopeRef');
    const expected = inactiveScopeSnapshot(expectedScope, scopeRef);
    return transaction(database, 'IMMEDIATE', () => {
      const current = getScope.get(scopeRef);
      if (!current) reject('CLAIM_CONFLICT', 'scope changed since the expected snapshot');
      if (current.active_transfer_id !== null) reject('SCOPE_BUSY', 'scope has an active transfer');
      if (current.writer_thread_id !== expected.writerThreadId ||
          current.fence_token !== expected.token) {
        reject('CLAIM_CONFLICT', 'scope changed since the expected snapshot');
      }
      const nextToken = rotatedToken(expected.token);
      const updated = database.prepare(
        'UPDATE scopes SET fence_token = ? WHERE scope_ref = ? AND writer_thread_id = ? AND active_transfer_id IS NULL AND fence_token = ?',
      ).run(nextToken, scopeRef, expected.writerThreadId, expected.token);
      if (updated.changes !== 1) reject('CLAIM_CONFLICT', 'scope changed during claim');
      return immutable({scope: {
        scopeRef, writerThreadId: expected.writerThreadId,
        activeTransferId: null, token: nextToken,
      }});
    });
  }

  function begin(transferId, planDigest, initialState) {
    ensureOpen();
    text(transferId, 'transferId');
    text(planDigest, 'planDigest');
    const {normalized, encoded} = stateText(initialState);
    if (normalized.transferId !== transferId || normalized.planDigest !== planDigest) {
      throw new TypeError('initial state transfer or plan digest differs');
    }
    const scopeRef = text(normalized.scopeRef, 'initialState.scopeRef');
    const writerThreadId = text(normalized.writerThreadId, 'initialState.writerThreadId');
    if (!plainObject(normalized.source) || normalized.source.threadId !== writerThreadId) {
      throw new TypeError('initial state source writer differs');
    }
    return transaction(database, 'IMMEDIATE', () => {
      const prior = getTransfer.get(transferId);
      if (prior) return immutable({created: false, revision: prior.revision});
      const scope = getScope.get(scopeRef);
      if (!scope || scope.active_transfer_id !== null || scope.writer_thread_id !== writerThreadId) {
        return immutable({created: false, revision: 0});
      }
      const fenceToken = token();
      database.prepare(
        'INSERT INTO transfers(transfer_id, scope_ref, plan_digest, revision, state_json, settled) VALUES (?, ?, ?, 0, ?, 0)',
      ).run(transferId, scopeRef, planDigest, encoded);
      database.prepare(
        'UPDATE scopes SET active_transfer_id = ?, fence_token = ? WHERE scope_ref = ?',
      ).run(transferId, fenceToken, scopeRef);
      return immutable({created: true, revision: 0, lease: {
        scopeRef, transferId, token: fenceToken, writerThreadId,
      }});
    });
  }

  function compareAndSet(transferId, revision, nextState, expectedLease) {
    ensureOpen();
    text(transferId, 'transferId');
    safeInteger(revision, 'revision');
    const lease = exactLease(expectedLease);
    if (lease.transferId !== transferId) throw new TypeError('lease transfer differs');
    const {normalized, encoded} = stateText(nextState);
    if (normalized.transferId !== transferId || normalized.scopeRef !== lease.scopeRef) {
      throw new TypeError('next state transfer or scope differs');
    }
    const writerThreadId = text(normalized.writerThreadId, 'nextState.writerThreadId');
    return transaction(database, 'IMMEDIATE', () => {
      const transfer = getTransfer.get(transferId);
      const scope = getScope.get(lease.scopeRef);
      if (!transfer || transfer.settled !== 0 || transfer.revision !== revision ||
          transfer.scope_ref !== lease.scopeRef || normalized.planDigest !== transfer.plan_digest ||
          !scope || scope.active_transfer_id !== lease.transferId ||
          scope.writer_thread_id !== lease.writerThreadId || scope.fence_token !== lease.token) {
        reject('CAS_CONFLICT', 'scope lease or transfer revision changed');
      }
      if (revision === Number.MAX_SAFE_INTEGER) reject('REVISION_EXHAUSTED', 'transfer revision is exhausted');
      const nextRevision = revision + 1;
      const nextToken = token();
      database.prepare(
        'UPDATE transfers SET revision = ?, state_json = ? WHERE transfer_id = ?',
      ).run(nextRevision, encoded, transferId);
      database.prepare(
        'UPDATE scopes SET writer_thread_id = ?, fence_token = ? WHERE scope_ref = ?',
      ).run(writerThreadId, nextToken, lease.scopeRef);
      return immutable({revision: nextRevision, lease: {
        scopeRef: lease.scopeRef, transferId, token: nextToken, writerThreadId,
      }});
    });
  }

  function read(transferId, scopeRef) {
    ensureOpen();
    text(transferId, 'transferId');
    text(scopeRef, 'scopeRef');
    return transaction(database, 'DEFERRED', () => {
      const transfer = getTransfer.get(transferId);
      const scope = getScope.get(scopeRef);
      if (!transfer || transfer.scope_ref !== scopeRef || !scope) {
        reject('RECORD_NOT_FOUND', 'transfer or scope record was not found');
      }
      return immutable({
        revision: transfer.revision,
        state: parseState(transfer.state_json),
        lease: leaseView(scope),
      });
    });
  }

  function settle(transferId, revision, expectedLease) {
    ensureOpen();
    text(transferId, 'transferId');
    safeInteger(revision, 'revision');
    const lease = exactLease(expectedLease);
    if (lease.transferId !== transferId) throw new TypeError('lease transfer differs');
    return transaction(database, 'IMMEDIATE', () => {
      const transfer = getTransfer.get(transferId);
      const scope = getScope.get(lease.scopeRef);
      if (!transfer || transfer.settled !== 0 || transfer.revision !== revision ||
          transfer.scope_ref !== lease.scopeRef || !scope ||
          scope.active_transfer_id !== transferId || scope.writer_thread_id !== lease.writerThreadId ||
          scope.fence_token !== lease.token) {
        reject('CAS_CONFLICT', 'scope lease or transfer revision changed');
      }
      const state = parseState(transfer.state_json);
      const complete = state.phase === 'source-subscription-released' && state.pendingEffect === null &&
        state.writer === 'target' && state.writerThreadId === lease.writerThreadId &&
        state.sourceRecovery === 'retained' && plainObject(state.source) &&
        plainObject(state.target) && state.target.threadId === lease.writerThreadId &&
        plainObject(state.continuationTurn) && state.continuationTurn.threadId === lease.writerThreadId &&
        typeof state.continuationTurn.turnId === 'string' && Boolean(state.continuationTurn.turnId.trim()) &&
        plainObject(state.subscriptionRelease) && state.subscriptionRelease.observed === true &&
        state.subscriptionRelease.threadId === state.source.threadId &&
        plainObject(state.verification) && typeof state.verification.release === 'string' &&
        Boolean(state.verification.release.trim());
      if (!complete) reject('TRANSFER_NOT_SETTLEABLE', 'transfer has not reached a verified released shape');
      if (revision === Number.MAX_SAFE_INTEGER) reject('REVISION_EXHAUSTED', 'transfer revision is exhausted');
      const nextRevision = revision + 1;
      const nextToken = token();
      database.prepare(
        'UPDATE transfers SET revision = ?, settled = 1 WHERE transfer_id = ?',
      ).run(nextRevision, transferId);
      database.prepare(
        'UPDATE scopes SET active_transfer_id = NULL, fence_token = ? WHERE scope_ref = ?',
      ).run(nextToken, lease.scopeRef);
      return immutable({revision: nextRevision, scope: {
        scopeRef: lease.scopeRef,
        writerThreadId: lease.writerThreadId,
        activeTransferId: null,
        token: nextToken,
      }});
    });
  }

  function settleFailedTransfer(transferId, revision, expectedLease, reconciliation) {
    // Effect/authority verification belongs to the caller. This transaction
    // only closes an exactly observed failed source lease, retaining its history.
    ensureOpen();
    text(transferId, 'transferId');
    safeInteger(revision, 'revision');
    const lease = exactLease(expectedLease);
    if (lease.transferId !== transferId) throw new TypeError('lease transfer differs');
    const receipt = immutable(reconciliation);
    return transaction(database, 'IMMEDIATE', () => {
      const transfer = getTransfer.get(transferId);
      const scope = getScope.get(lease.scopeRef);
      if (!transfer || transfer.settled !== 0 || transfer.revision !== revision ||
          transfer.scope_ref !== lease.scopeRef || !scope || scope.active_transfer_id !== transferId ||
          scope.writer_thread_id !== lease.writerThreadId || scope.fence_token !== lease.token) {
        reject('CAS_CONFLICT', 'scope lease or transfer revision changed');
      }
      const state = parseState(transfer.state_json);
      const targetId = state.target?.threadId ?? null;
      if (!['held', 'reconciliation-required'].includes(state.phase) || state.pendingEffect !== null ||
          state.writer !== 'source' || state.writerThreadId !== lease.writerThreadId ||
          state.source?.threadId !== lease.writerThreadId || state.sourceRecovery !== 'retained' ||
          state.continuationTurn !== null || !plainObject(state.failure) ||
          state.failure.writerTransferred !== false || state.failure.targetThreadId !== targetId ||
          !plainObject(receipt) || receipt.kind !== 'failed-transfer' ||
          receipt.originalPhase !== state.phase || receipt.originalPendingEffect !== state.pendingEffect ||
          !isDeepStrictEqual(receipt.originalFailure, state.failure) ||
          !plainObject(receipt.connection) || !plainObject(receipt.evidenceRefs) ||
          typeof receipt.sourceReadDigest !== 'string' || !/^[a-f0-9]{64}$/.test(receipt.sourceReadDigest) ||
          (targetId === null ? receipt.targetReadDigest !== null :
            typeof receipt.targetReadDigest !== 'string' || !/^[a-f0-9]{64}$/.test(receipt.targetReadDigest))) {
        reject('FAILED_TRANSFER_NOT_SETTLEABLE', 'failed source transfer or reconciliation receipt differs');
      }
      for (const key of ['connectionId', 'hostVersion']) text(receipt.connection[key], `reconciliation.connection.${key}`);
      for (const key of ['priorAttempt', 'effects', 'sourceRecovery', 'target']) {
        text(receipt.evidenceRefs[key], `reconciliation.evidenceRefs.${key}`);
      }
      text(receipt.verificationSourceRef, 'reconciliation.verificationSourceRef');
      if (revision === Number.MAX_SAFE_INTEGER) reject('REVISION_EXHAUSTED', 'transfer revision is exhausted');
      const next = stateText({...state, phase: 'failed-source-reconciled',
        expectedLease: lease, observedLease: lease, failedReconciliation: receipt});
      const nextRevision = revision + 1;
      const nextToken = rotatedToken(lease.token);
      database.prepare('UPDATE transfers SET revision = ?, state_json = ?, settled = 1 WHERE transfer_id = ?')
        .run(nextRevision, next.encoded, transferId);
      database.prepare('UPDATE scopes SET active_transfer_id = NULL, fence_token = ? WHERE scope_ref = ?')
        .run(nextToken, lease.scopeRef);
      return immutable({revision: nextRevision, scope: {scopeRef: lease.scopeRef,
        writerThreadId: lease.writerThreadId, activeTransferId: null, token: nextToken}});
    });
  }

  // External MCP sources have no subscription on the target's owned transport.
  // Keep this terminal shape distinct from native unsubscribe and old records.
  // Semantic acceptance and actual effect/resource verification belong to the
  // caller; this transaction only settles its exact observed cooperative lease.
  function settleExternal(transferId, revision, expectedLease) {
    ensureOpen();
    text(transferId, 'transferId'); safeInteger(revision, 'revision');
    const lease = exactLease(expectedLease);
    if (lease.transferId !== transferId) throw new TypeError('lease transfer differs');
    return transaction(database, 'IMMEDIATE', () => {
      const transfer = getTransfer.get(transferId), scope = getScope.get(lease.scopeRef);
      if (!transfer || transfer.settled !== 0 || transfer.revision !== revision ||
          transfer.scope_ref !== lease.scopeRef || !scope || scope.active_transfer_id !== transferId ||
          scope.writer_thread_id !== lease.writerThreadId || scope.fence_token !== lease.token) {
        reject('CAS_CONFLICT', 'external transfer lease or revision changed');
      }
      const state = parseState(transfer.state_json), targetId = state.target?.threadId;
      const complete = state.kind === 'external-source-handoff/v1' && state.phase === 'external-completed' &&
        state.pendingEffect === null && state.writer === 'target' && state.writerThreadId === targetId &&
        targetId === lease.writerThreadId && state.sourceRecovery === 'controller-owned' &&
        state.source?.kind === 'codex-mcp-request-metadata' &&
        state.source.threadId === state.source.sessionTreeId && state.source.threadId !== targetId &&
        state.release?.kind === 'cooperative-duty-release' &&
        state.release.sourceThreadId === state.source.threadId && state.release.callId === state.source.callId &&
        state.release.epoch === state.basis?.epoch &&
        state.firstContinuation?.threadId === targetId && state.firstContinuation.terminal === 'completed' &&
        state.postReleaseTurn?.threadId === targetId && state.postReleaseTurn.terminal === 'completed' &&
        state.postReleaseTurn.observedAfterRelease === true &&
        state.postReleaseTurn.turnId !== state.firstContinuation.turnId &&
        Array.isArray(state.postReleaseTurn.events) && state.postReleaseTurn.events.length > 0 &&
        state.nativeClosed?.closed === true && state.nativeClosed.exitCode === 0 && state.nativeClosed.forced === false;
      if (!complete) reject('EXTERNAL_TRANSFER_NOT_SETTLEABLE', 'external source release, continuation or resources are unverified');
      for (const key of ['prepare', 'targetCreated', 'commit', 'release', 'result', 'closed']) text(state.verification?.[key], `verification.${key}`);
      for (const value of [state.source.callId, state.source.turnId, state.firstContinuation.turnId, state.postReleaseTurn.turnId]) text(value, 'external identity');
      if (revision === Number.MAX_SAFE_INTEGER) reject('REVISION_EXHAUSTED', 'transfer revision is exhausted');
      const nextRevision = revision + 1, nextToken = rotatedToken(lease.token);
      database.prepare('UPDATE transfers SET revision = ?, settled = 1 WHERE transfer_id = ?').run(nextRevision, transferId);
      database.prepare('UPDATE scopes SET active_transfer_id = NULL, fence_token = ? WHERE scope_ref = ?').run(nextToken, lease.scopeRef);
      return immutable({revision: nextRevision, scope: {scopeRef: lease.scopeRef,
        writerThreadId: lease.writerThreadId, activeTransferId: null, token: nextToken}});
    });
  }

  function inspectExternalStopped(transferId, scopeRef) {
    const snapshot = read(transferId, scopeRef);
    if (!externalStopped(snapshot.state, snapshot.lease)) reject('EXTERNAL_STOPPED_NOT_APPLICABLE', 'external effects or actor closure are not known stopped');
    return snapshot;
  }
  function settleExternalStopped(transferId, revision, expectedLease, reconciliation) {
    ensureOpen(); text(transferId, 'transferId'); safeInteger(revision, 'revision');
    const lease = exactLease(expectedLease), receipt = immutable(reconciliation);
    if (lease.transferId !== transferId) throw new TypeError('lease transfer differs');
    return transaction(database, 'IMMEDIATE', () => {
      const transfer = getTransfer.get(transferId), scope = getScope.get(lease.scopeRef);
      if (!transfer || transfer.settled !== 0 || transfer.revision !== revision ||
          transfer.scope_ref !== lease.scopeRef || !scope || scope.active_transfer_id !== transferId ||
          scope.writer_thread_id !== lease.writerThreadId || scope.fence_token !== lease.token) reject('CAS_CONFLICT', 'external stopped lease changed');
      const state = parseState(transfer.state_json);
      if (!externalStopped(state, lease) || receipt.kind !== 'external-known-stopped' ||
          receipt.recordRevision !== revision || receipt.recordSha256 !== stateDigest(state) ||
          receipt.leaseSha256 !== stateDigest(lease) || receipt.originalPhase !== state.phase ||
          !isDeepStrictEqual(receipt.originalFailure, state.failure) ||
          receipt.originalDeadlineMs !== state.plan?.deadlineMs ||
          receipt.currentSource?.kind !== 'codex-mcp-request-metadata' ||
          receipt.currentSource?.threadId !== state.source.threadId ||
          receipt.currentSource.sessionTreeId !== state.source.threadId ||
          receipt.decision !== 'allow') reject('EXTERNAL_STOPPED_NOT_APPLICABLE', 'stopped reconciliation differs from exact original evidence');
      for (const key of ['turnId', 'callId']) text(receipt.currentSource[key], 'currentSource.' + key);
      for (const key of ['epoch', 'authorityRef', 'snapshotRef', 'protectedInputsDigest']) text(receipt.currentBasis?.[key], 'currentBasis.' + key);
      safeInteger(receipt.currentBasis.revision, 'currentBasis.revision');
      for (const key of ['sourceRef', 'observationSha256', 'decisionEvidence']) text(receipt[key], 'reconciliation.' + key);
      if (![receipt.observationSha256, receipt.decisionEvidence, receipt.currentBasis.snapshotRef,
        receipt.currentBasis.protectedInputsDigest].every(value => /^[a-f0-9]{64}$/.test(value))) {
        reject('EXTERNAL_STOPPED_NOT_APPLICABLE', 'reconciliation evidence hashes are invalid');
      }
      if (revision === Number.MAX_SAFE_INTEGER) reject('REVISION_EXHAUSTED', 'transfer revision is exhausted');
      const next = stateText({...state, phase: 'external-source-retained', reconciliation: receipt});
      const nextRevision = revision + 1, nextToken = rotatedToken(lease.token);
      database.prepare('UPDATE transfers SET revision = ?, state_json = ?, settled = 1 WHERE transfer_id = ?')
        .run(nextRevision, next.encoded, transferId);
      database.prepare('UPDATE scopes SET active_transfer_id = NULL, fence_token = ? WHERE scope_ref = ?').run(nextToken, lease.scopeRef);
      return immutable({revision: nextRevision, scope: {scopeRef: lease.scopeRef,
        writerThreadId: lease.writerThreadId, activeTransferId: null, token: nextToken}});
    });
  }

  function close() {
    if (closed) return;
    database.close();
    closed = true;
  }

  function inspectExternalStoppedTarget(transferId, scopeRef) {
    const snapshot = read(transferId, scopeRef);
    if (!externalStoppedTarget(snapshot.state, snapshot.lease)) reject('EXTERNAL_TARGET_NOT_SETTLEABLE', 'target identity, original actor closure or dispatch evidence is unavailable');
    return snapshot;
  }
  function settleExternalStoppedTarget(transferId, revision, expectedLease, reconciliation) {
    ensureOpen(); text(transferId, 'transferId'); safeInteger(revision, 'revision');
    const lease = exactLease(expectedLease), receipt = immutable(reconciliation);
    return transaction(database, 'IMMEDIATE', () => {
      const transfer = getTransfer.get(transferId), scope = getScope.get(lease.scopeRef);
      if (!transfer || transfer.settled !== 0 || transfer.revision !== revision || transfer.scope_ref !== lease.scopeRef ||
          lease.transferId !== transferId || !scope || scope.active_transfer_id !== transferId ||
          scope.writer_thread_id !== lease.writerThreadId || scope.fence_token !== lease.token) reject('CAS_CONFLICT', 'target recovery lease changed');
      const state = parseState(transfer.state_json), current = receipt.currentSource;
      if (!externalStoppedTarget(state, lease) || receipt.kind !== 'external-known-stopped-target' ||
          state.writer === 'source' && receipt.writerDisposition !== 'source-current' ||
          receipt.recordRevision !== revision || receipt.recordSha256 !== stateDigest(state) || receipt.leaseSha256 !== stateDigest(lease) ||
          receipt.originalStateEvidence !== receipt.recordSha256 || !Number.isSafeInteger(receipt.recoveryDeadlineMs) ||
          receipt.recoveryDeadlineMs <= Date.now() || receipt.recoveryDeadlineMs > Date.now() + 300000 ||
          receipt.originalDeadlineMs !== state.plan.deadlineMs || !isDeepStrictEqual(receipt.originalFailure, state.failure) ||
          current?.kind !== 'codex-mcp-request-metadata' || current.threadId !== state.source.threadId || current.sessionTreeId !== current.threadId ||
          receipt.decision !== 'allow' || !['source-current', 'target-retained'].includes(receipt.writerDisposition) ||
          receipt.currentBasis?.inputComplete !== true || receipt.currentBasis.paused !== false || receipt.currentBasis.recoveryRequired !== false ||
          receipt.scopeBinding?.scopeRef !== state.scopeRef || receipt.scopeBinding.sourceThreadId !== current.threadId ||
          receipt.scopeBinding.scopeRef !== stateDigest({threadId: current.threadId, cwd: receipt.scopeBinding.cwd, scope: receipt.scopeBinding.requestedScope}) ||
          receipt.readerClosed?.closed !== true || receipt.readerClosed.primaryProcessClosed !== true ||
          receipt.readerClosed.exitObserved !== true || receipt.readerClosed.closeObserved !== true ||
          receipt.readerClosed.forced !== false || receipt.readerClosed.exitCode !== 0 || receipt.readerClosed.signal !== null ||
          receipt.readerClosed.recoveryRequired !== false || receipt.readerClosed.terminationAttempt !== null) reject('EXTERNAL_TARGET_NOT_SETTLEABLE', 'target recovery receipt does not bind the observed state');
      for (const key of ['turnId', 'callId']) text(current[key], 'currentSource.' + key);
      text(receipt.scopeBinding.requestedScope, 'scopeBinding.requestedScope');
      if (!pathModule.isAbsolute(text(receipt.scopeBinding.cwd, 'scopeBinding.cwd'))) reject('EXTERNAL_TARGET_NOT_SETTLEABLE', 'scope cwd must be absolute');
      for (const key of ['epoch', 'authorityRef', 'snapshotRef', 'protectedInputsDigest']) text(receipt.currentBasis[key], 'currentBasis.' + key);
      safeInteger(receipt.currentBasis.revision, 'currentBasis.revision'); text(receipt.sourceRef, 'sourceRef');
      for (const key of ['observationSha256', 'decisionEvidence', 'materialSha256', 'nativeFactsSha256', 'originalStateEvidence']) {
        if (!/^[a-f0-9]{64}$/.test(receipt[key] || '')) reject('EXTERNAL_TARGET_NOT_SETTLEABLE', 'target recovery evidence digest is invalid');
      }
      if (revision === Number.MAX_SAFE_INTEGER) reject('REVISION_EXHAUSTED', 'transfer revision is exhausted');
      const writerThreadId = receipt.writerDisposition === 'source-current' ? current.threadId : state.target.threadId;
      const next = stateText({...state, phase: 'external-target-reconciled',
        writer: receipt.writerDisposition === 'source-current' ? 'source' : 'target', writerThreadId,
        sourceRecovery: receipt.writerDisposition === 'source-current' ? 'current-source' : state.sourceRecovery,
        pendingEffect: null, reconciliation: {...receipt, originalPendingEffect: state.pendingEffect,
          originalSourceRecovery: state.sourceRecovery, originalPhase: state.phase}});
      const nextRevision = revision + 1, nextToken = rotatedToken(lease.token);
      database.prepare('UPDATE transfers SET revision = ?, state_json = ?, settled = 1 WHERE transfer_id = ?')
        .run(nextRevision, next.encoded, transferId);
      database.prepare('UPDATE scopes SET writer_thread_id = ?, active_transfer_id = NULL, fence_token = ? WHERE scope_ref = ?')
        .run(writerThreadId, nextToken, lease.scopeRef);
      return immutable({revision: nextRevision, scope: {scopeRef: lease.scopeRef, writerThreadId, activeTransferId: null, token: nextToken}});
    });
  }

  return Object.freeze({bindScope, readScope, claimScope, begin, compareAndSet, read, settle, settleFailedTransfer, settleExternal,
    inspectExternalStopped, settleExternalStopped, inspectExternalStoppedTarget, settleExternalStoppedTarget, close});
}

module.exports = {openCarrierRecorder, CarrierRecorderError};
