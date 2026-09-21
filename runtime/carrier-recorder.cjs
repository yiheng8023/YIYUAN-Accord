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
  let database;
  try {
    if (create) {
      const descriptor = fs.openSync(databasePath, 'wx', 0o600);
      fs.closeSync(descriptor);
      statOrdinary(databasePath, false);
      database = new DatabaseSync(databasePath, {allowExtension: false, timeout: busyTimeoutMs});
      createSchema(database);
      validateDatabase(database);
    } else {
      let inspection;
      try {
        inspection = new DatabaseSync(databasePath, {
          readOnly: true, allowExtension: false, timeout: busyTimeoutMs,
        });
        validateDatabase(inspection);
      } finally {
        if (inspection) inspection.close();
      }
      statOrdinary(databasePath, false);
      database = new DatabaseSync(databasePath, {allowExtension: false, timeout: busyTimeoutMs});
      validateDatabase(database);
      database.exec('PRAGMA synchronous=FULL');
      database.exec(`PRAGMA busy_timeout=${busyTimeoutMs}`);
    }
  } catch (cause) {
    if (database) {
      try { database.close(); } catch (_) {}
    }
    throw cause;
  }

  let closed = false;
  const ensureOpen = () => {
    if (closed) reject('RECORDER_CLOSED', 'carrier recorder is closed');
  };
  const getScope = database.prepare(
    'SELECT scope_ref, writer_thread_id, active_transfer_id, fence_token FROM scopes WHERE scope_ref = ?',
  );
  const getTransfer = database.prepare(
    'SELECT transfer_id, scope_ref, plan_digest, revision, state_json, settled FROM transfers WHERE transfer_id = ?',
  );

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

  function close() {
    if (closed) return;
    closed = true;
    database.close();
  }

  return Object.freeze({bindScope, readScope, begin, compareAndSet, read, settle, close});
}

module.exports = {openCarrierRecorder, CarrierRecorderError};
