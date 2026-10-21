'use strict';

// One metadata query, then an optional prepared input. Never starts a model turn,
// changes configuration, copies credentials, or controls an existing thread.
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const {spawn, spawnSync} = require('node:child_process');
const {performance} = require('node:perf_hooks');
const {createOwnedAppServerConnection} = require('./codex-connection.cjs');

const MAX_INPUT = 65536;
const MAX_SOURCE = 262144;
const MAX_POLICY = 65536;
const HASH = /^[a-f0-9]{64}$/i;
function fail(code, message) { const error = new Error(message); error.code = code; throw error; }
function object(value) { return value && typeof value === 'object' && !Array.isArray(value); }
function text(value, limit = 16384) { return typeof value === 'string' && value.trim().length > 0 && value.length <= limit && !value.includes('\0'); }
function digest(value) { return crypto.createHash('sha256').update(value).digest('hex'); }
function existingCwd(value) {
  if (!text(value, 32768) || !path.isAbsolute(value)) fail('INVALID_INPUT', 'cwd must be an absolute existing directory');
  const resolved = fs.realpathSync(value);
  if (!fs.statSync(resolved).isDirectory()) fail('INVALID_INPUT', 'cwd must be a directory');
  return resolved;
}
function samePath(a, b) {
  if (!text(a, 32768) || !text(b, 32768) || !path.isAbsolute(a) || !path.isAbsolute(b)) return false;
  const normal = value => process.platform === 'win32' ? path.resolve(value).toLowerCase() : path.resolve(value);
  return normal(a) === normal(b);
}
function sameSourcePath(a, b) {
  if (samePath(a, b)) return true;
  try { return samePath(fs.realpathSync(a), fs.realpathSync(b)); } catch (_) { return false; }
}
function launcher(explicit) {
  const command = value => {
    if (!path.isAbsolute(value) || !fs.existsSync(value) || !fs.statSync(value).isFile()) return null;
    if (/\.c?js$/i.test(value)) return {executable: process.execPath, prefix: [value]};
    if (process.platform !== 'win32' || /\.exe$/i.test(value)) return {executable: value, prefix: []};
    return null; // Never pass .cmd/.ps1 through a shell.
  };
  if (explicit != null) {
    if (!text(explicit, 32768)) fail('INVALID_INPUT', 'codex path must be an absolute executable or JS launcher');
    const selected = command(explicit);
    if (!selected) fail('LAUNCHER_UNAVAILABLE', 'use an absolute native executable or installed JS launcher');
    return selected;
  }
  for (const entry of (process.env.PATH || '').split(path.delimiter)) {
    if (!entry || !path.isAbsolute(entry)) continue;
    const direct = command(path.join(entry, process.platform === 'win32' ? 'codex.exe' : 'codex'));
    if (direct) return direct;
    if (process.platform === 'win32' && fs.existsSync(path.join(entry, 'codex.cmd'))) {
      const npm = command(path.join(entry, 'node_modules', '@openai', 'codex', 'bin', 'codex.js'));
      if (npm) return npm;
    }
  }
  fail('LAUNCHER_UNAVAILABLE', 'no shell-free Codex launcher found; supply --codex');
}
function milliseconds(value, fallback, maximum) {
  const n = value === undefined ? fallback : Number(value);
  if (!Number.isSafeInteger(n) || n < 50 || n > maximum) fail('INVALID_INPUT', 'deadline is outside the supported bounds');
  return n;
}
function safeProjection(raw, cwd) {
  if (!Array.isArray(raw?.data)) fail('NATIVE_QUERY_FAILED', 'native skills result has no data array');
  const rows = raw.data.filter(row => samePath(row?.cwd, cwd));
  if (rows.length !== 1 || !Array.isArray(rows[0].skills) || !Array.isArray(rows[0].errors)) fail('NATIVE_QUERY_FAILED', 'native skills result does not identify one complete cwd inventory');
  if (rows[0].skills.length > 4096 || rows[0].errors.length > 4096) fail('NATIVE_QUERY_FAILED', 'native inventory exceeds the supported limit');
  const skills = rows[0].skills.map(row => {
    if (!text(row?.name, 256) || !text(row.path, 32768) || !path.isAbsolute(row.path) || typeof row.enabled !== 'boolean' || !text(row.scope, 64)) fail('NATIVE_QUERY_FAILED', 'native skill identity is incomplete');
    return {name: row.name, path: row.path, enabled: row.enabled, scope: row.scope};
  });
  // Error text and descriptions may contain unrelated configuration or data.
  const errors = rows[0].errors.map(row => ({kind: 'native-skill-load-error',
    path: text(row?.path, 32768) && path.isAbsolute(row.path) ? row.path : null, detailsOmitted: true}));
  return {skills, errors};
}
async function inventory(options) {
  if (!object(options)) fail('INVALID_INPUT', 'inventory options are required');
  const cwd = existingCwd(options.cwd);
  const deadlineMs = milliseconds(options.deadlineMs, 10000, 60000);
  const cleanupMs = milliseconds(options.cleanupMs, 5000, 10000);
  const launch = launcher(options.codexPath);
  const child = spawn(launch.executable, [...launch.prefix, 'app-server', '--stdio'], {
    cwd, stdio: ['pipe', 'pipe', 'pipe'], windowsHide: true, detached: process.platform !== 'win32', shell: false,
  });
  const ownedPid = child.pid || null;
  // Own stream errors even after the borrowed connection detaches during close.
  child.stdin.on('error', () => {});
  child.stdout.on('error', () => {});
  child.stderr.on('error', () => {});
  let exited = false, closeObserved = false, exitCode = null, signal = null, spawnError = false, stderrBytes = 0;
  // Last attempted stage, not evidence that the peer received the request.
  let connection, pendingFailure, queryPhase = 'initialize';
  const closed = new Promise(resolve => {
    child.once('error', () => { spawnError = true; });
    child.once('exit', (code, reason) => { exited = true; exitCode = code; signal = reason; });
    child.once('close', () => { closeObserved = true; resolve(); });
  });
  child.stderr.on('data', data => { stderrBytes += data.length; if (stderrBytes > MAX_SOURCE) connection?.close(); });
  const waitExit = ms => new Promise(resolve => {
    const timer = setTimeout(() => resolve(false), ms);
    closed.then(() => { clearTimeout(timer); resolve(true); });
  });
  let projection;
  const started = performance.now();
  try {
    connection = createOwnedAppServerConnection({stdin: child.stdin, stdout: child.stdout,
      connectionId: crypto.randomUUID(), hostVersion: 'metadata-query-version-unobserved',
      maxMessageBytes: 1048576, maxJournalBytes: 2097152});
    const deadline = started + deadlineMs;
    await connection.transport.request('initialize', {clientInfo: {name: 'accord_capability_inventory', version: '1.0.0'}}, deadline);
    queryPhase = 'initialized';
    await connection.transport.notify('initialized', {}, deadline);
    queryPhase = 'skills-list';
    const result = await connection.transport.request('skills/list', {cwds: [cwd], forceReload: true}, deadline);
    projection = safeProjection(result, cwd);
    queryPhase = 'complete';
  } catch (_) {
    pendingFailure = {code: 'NATIVE_QUERY_FAILED', message: 'native metadata query failed; no model turn was requested'};
  } finally {
    connection?.close();
    // The connection removes its data listener. Continue draining the owned
    // pipe so buffered shutdown output cannot prevent end/close observation.
    child.stdout.resume();
    child.stdin.end();
  }
  let forced = false, terminationAttempt = null, terminationExitCode = null, terminationSignal = null,
    terminationError = null, terminationElapsedMs = null;
  if (!await waitExit(cleanupMs)) {
    if (!exited && ownedPid !== null && child.pid === ownedPid && child.exitCode === null && child.signalCode === null) {
      forced = true;
      const terminationStarted = performance.now();
      if (process.platform === 'win32') {
        terminationAttempt = 'owned-pid-tree';
        // On the supported Windows Node runtime, keep the original process
        // handle alive across the bounded helper. An asynchronous launch could
        // process onexit/handle.close before taskkill resolves the numeric PID.
        const stopped = spawnSync(path.join(process.env.SystemRoot || 'C:\\Windows', 'System32', 'taskkill.exe'),
          ['/PID', String(ownedPid), '/T', '/F'], {stdio: 'ignore', windowsHide: true, shell: false, timeout: cleanupMs});
        terminationExitCode = Number.isInteger(stopped.status) ? stopped.status : null;
        terminationSignal = /^SIG[A-Z0-9]{1,20}$/.test(stopped.signal || '') ? stopped.signal : null;
        terminationError = /^E[A-Z0-9_]{1,40}$/.test(stopped.error?.code || '') ? stopped.error.code : null;
      } else {
        terminationAttempt = 'owned-process-group';
        try { process.kill(-ownedPid, 'SIGKILL'); } catch (error) {
          terminationError = /^E[A-Z0-9_]{1,40}$/.test(error.code || '') ? error.code : null;
        }
      }
      // Helper/signal diagnostics only: none proves native exit or tree closure.
      terminationElapsedMs = Math.max(0, Math.round(performance.now() - terminationStarted));
    }
    await waitExit(cleanupMs);
  }
  const processState = {pid: ownedPid, started: ownedPid !== null, stdinClosed: child.stdin.writableEnded,
    exitObserved: exited, closeObserved, exitCode, signal, forced, terminationAttempt, stderrBytes,
    queryPhase, terminationExitCode, terminationSignal, terminationError, terminationElapsedMs,
    descendantVerification: exited && !closeObserved ? 'unknown-launcher-exited-with-open-pipes' : 'not-independently-observed'};
  if (ownedPid !== null && !exited || !closeObserved) {
    // Do not keep this CLI alive for an unobserved child. Preserve its exact PID
    // for the caller's recovery; do not claim that a kill request proved exit.
    child.stdout.destroy(); child.stderr.destroy(); child.stdin.destroy(); child.unref();
    pendingFailure = {code: 'CLEANUP_UNVERIFIED', message: 'owned metadata process exit was not observed; reconcile the returned pid'};
  } else if (!pendingFailure && (spawnError || forced || exitCode !== 0)) {
    pendingFailure = {code: 'NATIVE_QUERY_FAILED', message: 'metadata process did not close normally; inventory is not admitted'};
  }
  if (pendingFailure) { const error = new Error(pendingFailure.message); error.code = pendingFailure.code; error.processState = processState; throw error; }
  return {schema: 'yiyuan-accord-capability-inventory/v1', cwd, observedAt: new Date().toISOString(),
    ...projection, process: processState, claimLimit: 'Native cwd inventory only; no task control, model execution or authority is established.'};
}
function requestInput(raw) {
  if (!object(raw) || Buffer.byteLength(JSON.stringify(raw), 'utf8') > MAX_INPUT ||
      !text(raw.originalRequest) || !object(raw.delegation) || !text(raw.delegation.sourceRef, 4096) ||
      !text(raw.delegation.scope, 8192) || !object(raw.selection) ||
      !text(raw.selection.name, 128) || !/^[a-zA-Z0-9][a-zA-Z0-9_-]*$/.test(raw.selection.name) ||
      !text(raw.selection.path, 32768) || !path.isAbsolute(raw.selection.path)) fail('INVALID_INPUT', 'bounded original request, delegation source/scope and exact skill selection are required');
  if (Object.hasOwn(raw.selection, 'expectedSha256') &&
      (typeof raw.selection.expectedSha256 !== 'string' || !HASH.test(raw.selection.expectedSha256))) fail('INVALID_INPUT', 'expected source hash must be SHA-256');
  if (Object.hasOwn(raw.selection, 'expectedPolicySha256') &&
      (!Object.hasOwn(raw.selection, 'expectedSha256') || raw.selection.expectedPolicySha256 !== null &&
       (typeof raw.selection.expectedPolicySha256 !== 'string' || !HASH.test(raw.selection.expectedPolicySha256)))) fail('INVALID_INPUT', 'reviewed policy requires the reviewed skill hash and a SHA-256 or absent-policy null');
  return raw;
}
function readSource(file, maximum, optional = false) {
  if (optional) {
    try { fs.lstatSync(file); } catch (error) { if (error.code === 'ENOENT') return null; throw error; }
  }
  const realPath = fs.realpathSync(file), descriptor = fs.openSync(realPath, 'r');
  let bytes;
  try {
    const before = fs.fstatSync(descriptor);
    if (!before.isFile() || before.size > maximum) fail('INVALID_SOURCE', 'selected source is not a bounded regular file');
    const buffer = Buffer.alloc(maximum + 1);
    let length = 0, amount;
    while (length < buffer.length && (amount = fs.readSync(descriptor, buffer, length, buffer.length - length, null)) > 0) length += amount;
    const after = fs.fstatSync(descriptor), current = fs.statSync(file);
    if (length > maximum || before.size !== after.size || before.mtimeMs !== after.mtimeMs ||
        before.ino !== current.ino || before.dev !== current.dev || fs.realpathSync(file) !== realPath) fail('SOURCE_CHANGED', 'selected source changed during observation');
    bytes = buffer.subarray(0, length);
  } finally { fs.closeSync(descriptor); }
  let body;
  try { body = new TextDecoder('utf-8', {fatal: true}).decode(bytes); } catch (_) { fail('INVALID_SOURCE', 'selected source is not UTF-8'); }
  return {realPath, sha256: digest(bytes), body};
}
function invocationPolicy(skill, yaml) {
  const frontmatter = /^\uFEFF?---\r?\n([\s\S]*?)\r?\n---(?:\r?\n|$)/.exec(skill)?.[1] || '';
  const model = [...frontmatter.matchAll(/^disable-model-invocation:\s*(true|false)\s*$/gm)];
  const sections = yaml == null ? [] : [...yaml.matchAll(/^policy:\s*\r?\n((?:[ \t]+[^\n]*(?:\n|$)|\r?\n)*)/gm)];
  const implicit = sections.length === 1 ? [...sections[0][1].matchAll(/^[ \t]+allow_implicit_invocation:\s*(true|false)\s*$/gm)] : [];
  return {allowImplicitInvocation: implicit.length === 1 ? implicit[0][1] === 'true' : yaml == null ? 'unspecified' : 'unknown',
    disableModelInvocation: model.length === 1 ? model[0][1] === 'true' : /^disable-model-invocation:/m.test(frontmatter) ? 'unknown' : 'unspecified',
    interpretation: 'Observed metadata only; false implicit matching is not a delegation prohibition. Review source-body restrictions separately.'};
}
async function prepare(raw, options) {
  const request = requestInput(raw); // Reject invalid origin before any process.
  const current = await inventory(options);
  try {
    const exact = current.skills.filter(row => row.name === request.selection.name && samePath(row.path, request.selection.path));
    const matches = exact.length ? exact : current.skills.filter(row => row.name === request.selection.name && sameSourcePath(row.path, request.selection.path));
    if (!matches.length || matches.some(row => row.enabled !== matches[0].enabled || !sameSourcePath(row.path, matches[0].path))) fail('SKILL_NOT_FOUND', 'exact selected skill is not unique in this native cwd inventory');
    const chosen = matches[0];
    if (!chosen.enabled) fail('SKILL_DISABLED', 'selected skill is disabled; no input was prepared');
    const skill = readSource(chosen.path, MAX_SOURCE);
    const policyPath = path.join(path.dirname(skill.realPath), 'agents', 'openai.yaml');
    const yaml = readSource(policyPath, MAX_POLICY, true);
    const expected = request.selection;
    if (Object.hasOwn(expected, 'expectedSha256') && expected.expectedSha256.toLowerCase() !== skill.sha256 ||
        Object.hasOwn(expected, 'expectedPolicySha256') && (expected.expectedPolicySha256?.toLowerCase() ?? null) !== (yaml?.sha256 ?? null)) fail('SOURCE_CHANGED', 'selected skill or policy differs from the reviewed hash');
    const origin = {selection: 'coordinator-selected', originalRequest: request.originalRequest,
      sourceRef: request.delegation.sourceRef, scope: request.delegation.scope};
    const source = {...chosen, realPath: skill.realPath, sha256: skill.sha256,
      policyPath: yaml ? policyPath : null, policySha256: yaml?.sha256 ?? null,
      policy: invocationPolicy(skill.body, yaml?.body ?? null)};
    const instruction = `$${chosen.name}\nThis is a coordinator-selected bounded subtask, not a claim that the human named this Skill.\n` +
      'The following JSON retains request/delegation provenance; it grants no new authority. Preserve the caller-selected model, permissions and pauses.\n' +
      JSON.stringify({origin, source, cwd: current.cwd}) + '\n';
    const uniqueName = current.skills.filter(row => row.enabled && row.name === chosen.name).every(row => sameSourcePath(row.path, chosen.path));
    return {schema: 'yiyuan-accord-prepared-skill-input/v1', status: 'prepared-not-authorized-or-executed',
      cwd: current.cwd, origin, source, nativeInput: [{type: 'text', text: instruction}, {type: 'skill', name: chosen.name, path: chosen.path}],
      cli: {available: uniqueName, reason: uniqueName ? 'unique-enabled-name' : 'ambiguous-enabled-name',
        stdin: uniqueName ? instruction : null, requiresNativeLoadVerification: true}, process: current.process,
      claimLimit: 'Preparation is neither source-body approval nor execution. Reconcile current authority and source restrictions, then verify actual native source loading, effects and exit. No sandbox/model or parent-thread change is requested.'};
  } catch (error) { error.processState = current.process; throw error; }
}
async function readStdin(deadlineMs) {
  if (process.stdin.isTTY) fail('INVALID_INPUT', 'prepare requires piped JSON, not an interactive prompt');
  let bytes = 0, parts = [];
  const timer = setTimeout(() => process.stdin.destroy(new Error('stdin deadline exceeded')), deadlineMs);
  try {
    for await (const chunk of process.stdin) {
      bytes += chunk.length;
      if (bytes > MAX_INPUT) fail('INVALID_INPUT', 'stdin exceeds the request byte limit');
      parts.push(chunk);
    }
  } catch (_) { fail('INVALID_INPUT', 'stdin exceeded its byte/time bound or became unavailable'); }
  finally { clearTimeout(timer); }
  try { return JSON.parse(Buffer.concat(parts).toString('utf8')); } catch (_) { fail('INVALID_INPUT', 'stdin must contain one JSON request'); }
}
async function main(args) {
  if (args.length === 1 && args[0] === '--help') return {commands: ['inventory --cwd ABSOLUTE [--codex EXE_OR_JS] [--deadline-ms 10000] [--cleanup-ms 5000]', 'prepare --cwd ABSOLUTE [same options] < request.json'],
    prepareRequest: {originalRequest: 'bounded original user requirement', delegation: {sourceRef: 'actual input or delegation locator', scope: 'bounded subtask'}, selection: {name: 'enabled-skill', path: 'native inventory absolute SKILL.md', expectedSha256: 'optional reviewed SHA-256', expectedPolicySha256: 'optional reviewed SHA-256 or null'}},
    effects: 'One shell-free metadata process; no model turns, configuration changes, credential copying or existing-thread control.',
    timing: 'Prepare allows one input deadline before the query deadline, plus at most three cleanup windows. The caller must retain process ownership through this bound; forcible termination of this helper itself is outside its recovery guarantee.'};
  const op = args.shift(), options = {}, keys = {'--cwd': 'cwd', '--codex': 'codexPath', '--deadline-ms': 'deadlineMs', '--cleanup-ms': 'cleanupMs'};
  if (!['inventory', 'prepare'].includes(op)) fail('INVALID_INPUT', 'expected inventory or prepare');
  while (args.length) {
    const key = keys[args.shift()], value = args.shift();
    if (!key || value === undefined || Object.hasOwn(options, key)) fail('INVALID_INPUT', 'unsupported, duplicate or incomplete option');
    options[key] = value;
  }
  return op === 'inventory' ? inventory(options) : prepare(await readStdin(milliseconds(options.deadlineMs, 10000, 60000)), options);
}
if (require.main === module) main(process.argv.slice(2)).then(result => process.stdout.write(JSON.stringify(result) + '\n')).catch(error => {
  process.stdout.write(JSON.stringify({status: 'failed', error: {code: typeof error.code === 'string' ? error.code : 'CAPABILITY_ERROR',
    message: ['INVALID_INPUT', 'LAUNCHER_UNAVAILABLE', 'NATIVE_QUERY_FAILED', 'CLEANUP_UNVERIFIED', 'SKILL_NOT_FOUND', 'SKILL_DISABLED', 'INVALID_SOURCE', 'SOURCE_CHANGED'].includes(error.code) ? error.message : 'capability preparation failed; inspect the selected source and host availability'},
    ...(error.processState ? {process: error.processState} : {})}) + '\n'); process.exitCode = 1;
});
module.exports = {inventory, prepare, launcher};
