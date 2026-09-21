'use strict';

// Fixed-response native caller for test_codex_session_native.py. The Python
// controller owns process containment, provider fixture and evidence roots.

const crypto = require('node:crypto');
const fs = require('node:fs');
const path = require('node:path');
const readline = require('node:readline');
const {spawn} = require('node:child_process');
const {Writable} = require('node:stream');
const {performance} = require('node:perf_hooks');

const SNAPSHOT = path.resolve(__dirname, '..', '..');
const {createOwnedAppServerConnection} = require(path.join(SNAPSHOT, 'runtime', 'codex-connection.cjs'));
const {createCodexSourceSession, restoreCodexSourceSession} = require(path.join(SNAPSHOT, 'runtime', 'codex-session.cjs'));
const {openCarrierRecorder} = require(path.join(SNAPSHOT, 'runtime', 'carrier-recorder.cjs'));

const MAX_NATIVE_BYTES = 16 * 1024 * 1024;
const MAX_TIMER_MS = 0x7fffffff;

function plain(value) {
  if (!value || typeof value !== 'object' || Array.isArray(value)) return false;
  const prototype = Object.getPrototypeOf(value);
  return prototype === Object.prototype || prototype === null;
}

function text(value, name) {
  if (typeof value !== 'string' || !value.trim()) throw new TypeError(`${name} is required`);
  return value;
}

function clone(value) { return JSON.parse(JSON.stringify(value)); }
const canonical = value => JSON.stringify(value, function (_, child) {
  return child && typeof child === 'object' && !Array.isArray(child)
    ? Object.fromEntries(Object.keys(child).sort().map(key => [key, child[key]])) : child;
});

function inside(root, value, name) {
  const resolved = path.resolve(text(value, name));
  const relative = path.relative(root, resolved);
  if (!relative || relative.startsWith('..') || path.isAbsolute(relative)) {
    throw new TypeError(`${name} must be a child of the evidence root`);
  }
  return resolved;
}

function sha256(file) {
  return crypto.createHash('sha256').update(fs.readFileSync(file)).digest('hex');
}

function readJson(file, limit = 16 * 1024 * 1024) {
  const info = fs.lstatSync(file);
  if (!info.isFile() || info.isSymbolicLink() || info.size > limit || fs.realpathSync(file) !== path.resolve(file)) {
    throw new Error('unsafe or oversize JSON evidence: ' + file);
  }
  return JSON.parse(fs.readFileSync(file, 'utf8'));
}

function readJsonLines(file, limit = 32 * 1024 * 1024) {
  const info = fs.lstatSync(file);
  if (!info.isFile() || info.isSymbolicLink() || info.size > limit || fs.realpathSync(file) !== path.resolve(file)) {
    throw new Error('unsafe or oversize JSONL evidence: ' + file);
  }
  return fs.readFileSync(file, 'utf8').split(/\r?\n/).filter(Boolean).map(line => JSON.parse(line));
}

function existingInside(root, value, name) {
  const resolved = path.resolve(text(value, name));
  const relative = path.relative(root, resolved);
  if (!relative || relative.startsWith('..') || path.isAbsolute(relative) ||
      !fs.statSync(resolved).isFile() || fs.lstatSync(resolved).isSymbolicLink() ||
      fs.realpathSync(resolved) !== resolved) throw new TypeError(`${name} must be an ordinary file inside its root`);
  return resolved;
}

function completed(terminal, threadId, turnId) {
  return terminal?.method === 'turn/completed' && terminal.params?.threadId === threadId &&
    terminal.params?.turn?.id === turnId && terminal.params?.turn?.status === 'completed';
}

function idleThread(value, id) {
  return value?.thread?.id === id && value.thread?.status?.type === 'idle' &&
    value.thread?.ephemeral === false;
}

function dynamicNames(tools) {
  return Array.isArray(tools) ? tools.filter(tool => tool?.namespace == null).map(tool => tool?.name) : [];
}

function validateConfig(raw) {
  const baseKeys = ['schema', 'evidence', 'argv', 'workspace', 'nativeLogRoot', 'recorderPath',
    'resultPath', 'binding', 'keepPath', 'keepSha256', 'overallDeadlineMs', 'identities'];
  if (!plain(raw)) throw new TypeError('invalid native caller config');
  const mode = raw.mode ?? 'hot';
  const keys = mode === 'restore' ? [...baseKeys, 'mode', 'restore'] : baseKeys;
  if (Object.keys(raw).sort().join('|') !== keys.sort().join('|') ||
      raw.schema !== (mode === 'restore' ? 'accord-codex-session-native-config/v2' :
        'accord-codex-session-native-config/v1') || !['hot', 'restore'].includes(mode)) {
    throw new TypeError('invalid native caller config');
  }
  const evidence = path.resolve(text(raw.evidence, 'evidence'));
  if (!path.isAbsolute(evidence) || !fs.statSync(evidence).isDirectory()) throw new TypeError('ordinary evidence root required');
  if (!Array.isArray(raw.argv) || raw.argv.length < 2 || raw.argv.some(value => typeof value !== 'string')) {
    throw new TypeError('bound native argv is required');
  }
  if (!plain(raw.binding) || !text(raw.binding.connectionId, 'connectionId') ||
      !text(raw.binding.hostVersion, 'hostVersion')) throw new TypeError('native binding is required');
  if (!plain(raw.identities) || !plain(raw.identities.node) || !plain(raw.identities.codex)) {
    throw new TypeError('bound executable identities are required');
  }
  if (!Number.isSafeInteger(raw.overallDeadlineMs) || raw.overallDeadlineMs <= Date.now() ||
      raw.overallDeadlineMs - Date.now() > 180000) throw new TypeError('bounded overall deadline required');
  let restore = null;
  if (mode === 'restore') {
    const value = raw.restore;
    const restoreKeys = ['priorRoot', 'sessionsRoot', 'scopeRef', 'transferId', 'expectedScope'];
    if (!plain(value) || Object.keys(value).sort().join('|') !== restoreKeys.sort().join('|') ||
        !plain(value.expectedScope) || Object.keys(value.expectedScope).sort().join('|') !==
          ['activeTransferId', 'scopeRef', 'token', 'writerThreadId'].sort().join('|') ||
        value.expectedScope.scopeRef !== value.scopeRef || value.expectedScope.activeTransferId !== null) {
      throw new TypeError('invalid restore binding');
    }
    for (const name of ['scopeRef', 'transferId']) text(value[name], `restore.${name}`);
    for (const name of ['scopeRef', 'token', 'writerThreadId']) {
      text(value.expectedScope[name], `restore.expectedScope.${name}`);
    }
    const priorRoot = inside(evidence, value.priorRoot, 'restore.priorRoot');
    const sessionsRoot = inside(evidence, value.sessionsRoot, 'restore.sessionsRoot');
    if (!fs.statSync(priorRoot).isDirectory() || !fs.statSync(sessionsRoot).isDirectory() ||
        fs.lstatSync(priorRoot).isSymbolicLink() || fs.lstatSync(sessionsRoot).isSymbolicLink()) {
      throw new TypeError('restore roots must be ordinary directories');
    }
    restore = Object.freeze({...clone(value), priorRoot, sessionsRoot});
  }
  return Object.freeze({...raw, evidence, mode, restore,
    workspace: inside(evidence, raw.workspace, 'workspace'),
    nativeLogRoot: inside(evidence, raw.nativeLogRoot, 'nativeLogRoot'),
    recorderPath: inside(evidence, raw.recorderPath, 'recorderPath'),
    resultPath: inside(evidence, raw.resultPath, 'resultPath'),
    keepPath: inside(evidence, raw.keepPath, 'keepPath')});
}

function walkFiles(root) {
  const found = [];
  const visit = directory => {
    for (const entry of fs.readdirSync(directory, {withFileTypes: true})) {
      const file = path.join(directory, entry.name);
      if (entry.isSymbolicLink()) throw new Error('session tree contains a symbolic link');
      if (entry.isDirectory()) visit(file);
      else if (entry.isFile()) found.push(file);
      else throw new Error('session tree contains a non-file entry');
    }
  };
  visit(root);
  return found.sort();
}

function sessionFileEvidence(file, sessionsRoot, threadId) {
  const resolved = existingInside(sessionsRoot, file, 'native thread.path');
  const rows = readJsonLines(resolved);
  const meta = rows.filter(row => row?.type === 'session_meta' && row.payload?.id === threadId);
  if (meta.length !== 1) throw new Error('native session metadata identity differs');
  const contexts = rows.filter(row => row?.type === 'turn_context' && row.payload?.turn_id);
  const tools = dynamicNames(meta[0].payload.dynamic_tools);
  return {path: resolved, relativePath: path.relative(sessionsRoot, resolved).replace(/\\/g, '/'),
    meta: meta[0], contexts, rowCount: rows.length, tools};
}

function releasedResource(record, manifest) {
  const controller = manifest.resourceController || 'windows-job-object';
  if (record?.controller !== controller || record.exitCode !== 0 || record.forced !== false ||
      record.failure !== null || record.readerStopped !== true ||
      record.cleanupState !== 'released-within-controller-scope') return false;
  if (controller === 'windows-job-object') return record.after?.activeProcesses === 0;
  return controller === 'posix-session-process-group' && record.after?.activeProcesses === null &&
    record.after?.processGroupState === 'absent' && record.after?.rootExitCode === record.exitCode;
}

async function runRestore(config, connection, recorder, mono, wall, claimRequests, claimReceipts) {
  const priorRoot = config.restore.priorRoot;
  const priorManifest = readJson(path.join(priorRoot, 'manifest.json'));
  const priorPost = readJson(path.join(priorRoot, 'poststate.json'));
  const priorEnvelope = readJson(path.join(priorRoot, 'node-result.json'));
  const priorResource = readJson(path.join(priorRoot, 'controller-resource.json'));
  const priorSessionHashes = readJson(path.join(priorRoot, 'native-sessions-sha256.json'));
  const priorResult = priorEnvelope.result;
  const expectedScope = config.restore.expectedScope;
  const threadId = expectedScope.writerThreadId;
  const transferId = config.restore.transferId;
  if (priorManifest.schema !== 'accord-codex-session-native-evidence/v1' ||
      priorPost.executionFailure !== null || priorPost.cleanupFailure !== null ||
      priorEnvelope.success !== true || priorEnvelope.failure !== null ||
      priorManifest.identities?.codex?.sha256 !== config.identities.codex.sha256 ||
      priorManifest.identities?.codex?.version !== config.identities.codex.version ||
      priorManifest.identities?.node?.sha256 !== config.identities.node.sha256 ||
      priorManifest.identities?.node?.version !== config.identities.node.version ||
      canonical(priorResult?.adoptedSecond?.scope) !== canonical(expectedScope) ||
      priorResult?.adoptedSecond?.transferId !== transferId ||
      priorResult?.threadIds?.target2 !== threadId || !releasedResource(priorResource, priorManifest) ||
      priorEnvelope.close?.nativeExit?.code !== 0 || priorEnvelope.close?.nativeExit?.signal !== null ||
      priorEnvelope.close?.connectionClosed !== true || priorEnvelope.close?.stdoutEnded !== true ||
      priorEnvelope.close?.closeFailure !== null) {
    throw new Error('portable prior release or settled adoption evidence differs');
  }
  const priorRecord = priorResult.records?.[transferId];
  const priorHistory = priorResult.histories?.[threadId];
  if (!priorRecord || !priorHistory?.thread || priorHistory.thread.id !== threadId ||
      !Array.isArray(priorHistory.thread.turns) || priorHistory.thread.turns.length !== 2) {
    throw new Error('portable prior ledger or history differs');
  }
  const targetSessionNames = Object.keys(priorSessionHashes).filter(name => name.endsWith(`${threadId}.jsonl`));
  if (Object.keys(priorSessionHashes).length !== 3 || targetSessionNames.length !== 1) {
    throw new Error('portable prior native session inventory differs');
  }

  const verifyStages = [], verifyEvidence = {}, ownerRequests = [], contextRefs = [];
  let historyBefore = null;
  async function verifier(stage, facts, deadline) {
    if (!Number.isFinite(deadline) || performance.now() >= deadline) throw new Error('verifier deadline exceeded');
    if (sha256(config.keepPath) !== config.keepSha256) throw new Error('protected keep input changed');
    verifyStages.push(stage);
    const base = {decision: 'allow', scopeRef: config.restore.scopeRef,
      authorityRef: priorRecord.state.authorityRef, stateRef: priorRecord.state.stateRef,
      sourceRef: `native:${stage}:${transferId}`};
    if (stage === 'restore-prepare') {
      const status = facts.threadRead?.thread?.status?.type;
      const preSession = sessionFileEvidence(facts.threadRead?.thread?.path,
        config.restore.sessionsRoot, threadId);
      if (facts.connectionId !== config.binding.connectionId ||
          facts.hostVersion !== config.binding.hostVersion || facts.transferId !== transferId ||
          canonical(facts.expectedScope) !== canonical(expectedScope) ||
          canonical(facts.observedScope) !== canonical(expectedScope) ||
          facts.target?.threadId !== threadId || !['idle', 'notLoaded'].includes(status) ||
          facts.threadRead?.thread?.id !== threadId || facts.threadRead.thread.ephemeral !== false ||
          canonical(facts.record) !== canonical(priorRecord) ||
          facts.record.state.plan?.scopeRef !== config.restore.scopeRef ||
          facts.record.state.plan?.authorityRef !== priorRecord.state.authorityRef ||
          facts.record.state.plan?.stateRef !== priorRecord.state.stateRef ||
          facts.record.state.target?.threadId !== threadId ||
          preSession.relativePath !== targetSessionNames[0] ||
          canonical(preSession.meta.payload.dynamic_tools) !==
            canonical(priorRecord.state.plan.target.dynamicTools) ||
          facts.record.state.connection?.connectionId === config.binding.connectionId) {
        throw new Error('restore-prepare facts differ from portable prior evidence');
      }
      verifyEvidence.prepare = {threadStatus: status, recordRevision: facts.record.revision,
        priorControllerReleased: true, expectedScope: clone(expectedScope),
        threadPath: facts.threadRead.thread.path, sessionRelativePath: preSession.relativePath,
        tools: preSession.tools};
      return {...base, pauseStateVerified: true, priorControllerQuiesced: true,
        pendingEffectsReconciled: true, restorationAuthorized: true, singleWriter: true,
        resumeInitializationSafe: true};
    }
    if (stage === 'restore-resumed') {
      const resume = facts.resumeParams;
      const receipt = facts.resumeReceipt;
      const after = facts.threadReadAfter?.thread;
      if (canonical(resume) !== canonical({threadId, excludeTurns: true, cwd: config.workspace,
          sandbox: 'read-only', approvalPolicy: 'never', model: 'fixture-no-model',
          modelProvider: 'accord_fixture'}) || facts.claimedScope?.writerThreadId !== threadId ||
          facts.claimedScope?.activeTransferId !== null ||
          facts.claimedScope?.token === expectedScope.token || after?.id !== threadId ||
          after.ephemeral !== false || after.status?.type !== 'idle' ||
          path.resolve(after.cwd) !== config.workspace || after.model !== 'fixture-no-model' ||
          after.modelProvider !== 'accord_fixture' || path.resolve(receipt?.cwd || '') !== config.workspace ||
          receipt?.model !== 'fixture-no-model' || receipt?.modelProvider !== 'accord_fixture' ||
          receipt?.approvalPolicy !== 'never' || receipt?.sandbox?.type !== 'readOnly') {
        throw new Error('restore-resumed native settings or claimed scope differ');
      }
      const sessionEvidence = sessionFileEvidence(after.path, config.restore.sessionsRoot, threadId);
      if (sessionEvidence.relativePath !== targetSessionNames[0] ||
          canonical(sessionEvidence.meta.payload.dynamic_tools) !==
            canonical(priorRecord.state.plan.target.dynamicTools) ||
          canonical(sessionEvidence.tools) !== canonical(['accord_request_handoff', 'accord_inspect_context'])) {
        throw new Error('restored persistent session metadata differs');
      }
      historyBefore = await connection.transport.request('thread/read',
        {threadId, includeTurns: true}, deadline);
      if (historyBefore?.thread?.id !== threadId ||
          canonical(historyBefore.thread.turns) !== canonical(priorHistory.thread.turns)) {
        throw new Error('restored native history differs from portable prior history');
      }
      verifyEvidence.resumed = {threadPath: after.path, sessionRelativePath: sessionEvidence.relativePath,
        tools: sessionEvidence.tools, historyTurns: historyBefore.thread.turns.length,
        actual: {cwd: receipt.cwd, model: receipt.model, modelProvider: receipt.modelProvider,
          sandbox: receipt.sandbox.type, approvalPolicy: receipt.approvalPolicy},
        threadRead: {cwd: after.cwd, model: after.model, modelProvider: after.modelProvider}};
      return {...base, nativeToolEvidenceRef: `native-session-meta:${sessionEvidence.relativePath}`,
        continuityToolsRestored: true, targetSettingsMatch: true, historyRetained: true,
        singleWriter: true, effectsVerified: true};
    }
    throw new Error('unexpected restore verifier stage: ' + stage);
  }
  const options = {connection, recorder, scopeRef: config.restore.scopeRef,
    planResolver() { throw new Error('cold continuation must not create a handoff plan'); },
    verify: verifier,
    current(context) {
      const scope = recorder.readScope(config.restore.scopeRef);
      contextRefs.push({threadId: context.sourceThreadId, writerThreadId: scope.writerThreadId});
      return {scopeRef: config.restore.scopeRef, authorityRef: priorRecord.state.authorityRef,
        stateRef: priorRecord.state.stateRef, writerThreadId: scope.writerThreadId};
    },
    ownerRequest(request, context) {
      ownerRequests.push({method: request.method, threadId: request.params?.threadId || null,
        turnId: request.params?.turnId || null, phase: context.phase || 'source'});
      return {error: {code: -32601, message: 'fixed cold fixture has no owner handler for this request'}};
    }};
  const scopeBefore = recorder.readScope(config.restore.scopeRef);
  const recordsBefore = {
    'native-transfer-1': recorder.read('native-transfer-1', config.restore.scopeRef),
    'native-transfer-2': recorder.read('native-transfer-2', config.restore.scopeRef),
  };
  const session = await restoreCodexSourceSession(options, {transferId, expectedScope,
    deadlineMs: wall(), resume: {cwd: config.workspace, model: 'fixture-no-model',
      modelProvider: 'accord_fixture', sandbox: 'read-only', approvalPolicy: 'never'}});
  const restoredState = session.snapshot();
  if (claimRequests.length !== 1 || claimReceipts.length !== 1) {
    throw new Error('restore must claim the prior scope exactly once');
  }
  const runResult = await session.run({input: 'Inspect current context once, then finish this restored source turn.',
    deadlineMs: wall()});
  const historyAfter = await connection.transport.request('thread/read',
    {threadId, includeTurns: true}, mono());
  const scopeAfter = recorder.readScope(config.restore.scopeRef);
  const recordsAfter = {
    'native-transfer-1': recorder.read('native-transfer-1', config.restore.scopeRef),
    'native-transfer-2': recorder.read('native-transfer-2', config.restore.scopeRef),
  };
  const sessionState = session.snapshot();
  const evidence = sessionFileEvidence(historyAfter.thread.path, config.restore.sessionsRoot, threadId);
  const lastContext = evidence.contexts.at(-1)?.payload;
  const oldTurns = priorHistory.thread.turns;
  if (runResult.status !== 'completed' || runResult.sourceThreadId !== threadId ||
      scopeAfter.writerThreadId !== threadId || scopeAfter.activeTransferId !== null ||
      scopeAfter.token === expectedScope.token || sessionState.status !== 'ready' ||
      sessionState.sourceThreadId !== threadId || sessionState.turnCount !== 1 ||
      sessionState.transfers.length !== 1 || sessionState.transfers[0].restored !== true ||
      historyAfter.thread.id !== threadId || historyAfter.thread.turns.length !== oldTurns.length + 1 ||
      evidence.relativePath !== targetSessionNames[0] ||
      canonical(historyAfter.thread.turns.slice(0, oldTurns.length)) !== canonical(oldTurns) ||
      historyAfter.thread.turns.at(-1)?.status !== 'completed' ||
      path.resolve(lastContext?.cwd || '') !== config.workspace || lastContext?.model !== 'fixture-no-model' ||
      lastContext?.approval_policy !== 'never' || lastContext?.sandbox_policy?.type !== 'read-only') {
    throw new Error('restored ordinary run or final native history differs');
  }
  for (const transfer of ['native-transfer-1', 'native-transfer-2']) {
    if (recordsAfter[transfer].revision !== recordsBefore[transfer].revision ||
        canonical(recordsAfter[transfer].state) !== canonical(recordsBefore[transfer].state) ||
        recordsAfter[transfer].lease.writerThreadId !== threadId ||
        recordsAfter[transfer].lease.token !== scopeAfter.token) {
      throw new Error('cold restore changed settled transfer history');
    }
  }
  const files = walkFiles(config.restore.sessionsRoot);
  if (files.length !== 3) throw new Error('cold restore native session count differs');
  const targetRelative = targetSessionNames[0];
  for (const [name, expectedHash] of Object.entries(priorSessionHashes)) {
    const current = path.join(config.restore.sessionsRoot, ...name.split('/'));
    const prior = path.join(priorRoot, 'native-sessions', ...name.split('/'));
    if (name === targetRelative) {
      const before = fs.readFileSync(prior), after = fs.readFileSync(current);
      if (after.length <= before.length || !after.subarray(0, before.length).equals(before)) {
        throw new Error('restored target session did not preserve and append prior history');
      }
    } else if (sha256(current) !== expectedHash) {
      throw new Error('unrelated native session changed during restore');
    }
  }
  return {schema: 'accord-codex-session-native-restore-result/v1', success: true,
    binding: config.binding, threadIds: priorResult.threadIds,
    prior: {threadIds: priorResult.threadIds, expectedScope,
      transferId, sessionHashes: priorSessionHashes}, restoredState, run: runResult,
    historyBefore, historyAfter, recordsBefore, recordsAfter, scopeBefore, scopeAfter,
    sessionState, verifyStages, verifyEvidence, claimRequests, claimReceipts,
    contextRefs, ownerRequests, nativeSession: {path: evidence.path,
      relativePath: evidence.relativePath, tools: evidence.tools, rowCount: evidence.rowCount},
    identities: {node: {path: config.identities.node.path, sha256: sha256(process.execPath),
      version: process.version}, codex: {path: config.argv[0], sha256: sha256(config.argv[0]),
      version: config.binding.hostVersion}}, keepSha256: sha256(config.keepPath),
    providerRequestsExpected: 2,
    claimLimit: 'Controlled quiescent-controller restore using copied native history and durable ledger; no crash simulation, new thread, handoff, Goal or other host-state migration, model judgment or product acceptance.'};
}

async function run(rawConfig) {
  const config = validateConfig(rawConfig);
  if (path.resolve(process.execPath) !== path.resolve(config.identities.node.path) ||
      sha256(process.execPath) !== config.identities.node.sha256 ||
      process.version !== config.identities.node.version ||
      path.resolve(config.argv[0]) !== path.resolve(config.identities.codex.path) ||
      sha256(config.argv[0]) !== config.identities.codex.sha256 ||
      config.binding.hostVersion !== config.identities.codex.version) {
    throw new Error('bound executable identity differs before execution');
  }
  if (sha256(config.keepPath) !== config.keepSha256) throw new Error('protected keep input differs before execution');
  fs.mkdirSync(config.nativeLogRoot, {recursive: false});
  const stdoutFd = fs.openSync(path.join(config.nativeLogRoot, 'stdout.jsonl'), 'wx');
  const stderrFd = fs.openSync(path.join(config.nativeLogRoot, 'stderr.txt'), 'wx');
  const requestsFd = fs.openSync(path.join(config.nativeLogRoot, 'requests.jsonl'), 'wx');
  const native = spawn(config.argv[0], config.argv.slice(1), {
    cwd: config.workspace, env: process.env, stdio: ['pipe', 'pipe', stderrFd], windowsHide: true,
  });
  let nativeBytes = 0, connection = null, recorder = null, connectionClosed = false;
  let nativeExit = null, stdoutEnded = false, closeFailure = null;
  const exitPromise = new Promise((resolve, reject) => {
    native.once('error', reject);
    native.once('exit', (code, signal) => { nativeExit = {code, signal}; resolve(nativeExit); });
  });
  const stdoutPromise = new Promise(resolve => native.stdout.once('end', () => {
    stdoutEnded = true; resolve();
  }));
  const capture = chunk => {
    nativeBytes += chunk.length;
    if (nativeBytes > MAX_NATIVE_BYTES) {
      native.stdout.pause();
      native.stdin.destroy(new Error('native output bound exceeded'));
      return;
    }
    fs.writeSync(stdoutFd, chunk);
  };
  native.stdout.on('data', capture);
  const outgoing = new Writable({write(chunk, encoding, done) {
    try { fs.writeSync(requestsFd, chunk); native.stdin.write(chunk, encoding, done); }
    catch (error) { done(error); }
  }});
  const overall = performance.now() + (config.overallDeadlineMs - Date.now());
  const mono = (millis = 30000) => {
    const deadline = Math.min(overall, performance.now() + millis);
    if (deadline - performance.now() <= 0 || deadline - performance.now() > MAX_TIMER_MS) {
      throw new Error('native caller deadline exceeded');
    }
    return deadline;
  };
  const wall = (millis = 30000) => {
    const remaining = Math.min(config.overallDeadlineMs - Date.now(), millis);
    if (remaining <= 0) throw new Error('native caller wall deadline exceeded');
    return Date.now() + remaining;
  };
  const verifyStages = [], plans = [], ownerRequests = [], contextRefs = [];
  const claimRequests = [], claimReceipts = [];
  let activePlan = null;
  let result = null, failure = null;
  try {
    connection = createOwnedAppServerConnection({stdin: outgoing, stdout: native.stdout,
      connectionId: config.binding.connectionId, hostVersion: config.binding.hostVersion,
      maxMessageBytes: 2 * 1024 * 1024, maxJournalBytes: 12 * 1024 * 1024});
    const openedRecorder = openCarrierRecorder({path: config.recorderPath,
      create: config.mode !== 'restore', busyTimeoutMs: 5000});
    if (config.mode === 'restore') {
      recorder = Object.freeze({
        bindScope: openedRecorder.bindScope, readScope: openedRecorder.readScope,
        begin: openedRecorder.begin, compareAndSet: openedRecorder.compareAndSet,
        read: openedRecorder.read, settle: openedRecorder.settle,
        claimScope(scopeRef, expectedScope) {
          claimRequests.push({scopeRef, expectedScope: clone(expectedScope)});
          const receipt = openedRecorder.claimScope(scopeRef, expectedScope);
          claimReceipts.push(clone(receipt));
          return receipt;
        },
        close: openedRecorder.close,
      });
    } else recorder = openedRecorder;
    await connection.transport.request('initialize', {clientInfo: {
      name: 'accord_codex_session_native', title: 'Accord Codex session native fixture', version: '1'},
      capabilities: {experimentalApi: true}}, mono());
    await connection.transport.notify('initialized', {}, mono());

    if (config.mode === 'restore') {
      result = await runRestore(config, connection, recorder, mono, wall, claimRequests, claimReceipts);
    } else {
    function verifier(stage, facts, deadline) {
      if (!Number.isFinite(deadline) || performance.now() >= deadline) throw new Error('verifier deadline exceeded');
      if (sha256(config.keepPath) !== config.keepSha256) throw new Error('protected keep input changed');
      verifyStages.push(stage);
      if (stage === 'adopt-target') {
        if (!idleThread(facts?.targetRead, facts?.target?.threadId) ||
            facts?.record?.state?.phase !== 'source-subscription-released' ||
            facts.record.state.pendingEffect !== null || facts.record.state.writerThreadId !== facts.target.threadId) {
          throw new Error('adopt-target evidence differs');
        }
        return {decision: 'allow', scopeRef: facts.scopeRef, authorityRef: facts.authorityRef,
          stateRef: facts.stateRef, sourceRef: `native:${stage}:${facts.transferId}`,
          adoptionAuthorized: true, singleWriter: true, effectsVerified: true};
      }
      const plan = facts?.packet?.plan, sourceId = plan?.source?.threadId;
      if (!plan || facts.packet.scopeRef !== plan.scopeRef || facts.packet.authorityRef !== plan.authorityRef ||
          facts.packet.stateRef !== plan.stateRef || facts.connectionId !== config.binding.connectionId ||
          facts.hostVersion !== config.binding.hostVersion || facts.ledger?.scopeRef !== plan.scopeRef) {
        throw new Error(`verifier binding differs at ${stage}`);
      }
      const targetId = facts.target?.threadId;
      const verdict = {decision: 'allow', scopeRef: plan.scopeRef, authorityRef: plan.authorityRef,
        stateRef: plan.stateRef, sourceRef: `native:${stage}:${plan.transferId}`,
        sourceRecoveryReady: true};
      if (stage === 'prepare') {
        if (facts.sourceRead?.thread?.id !== sourceId || plan.target.cwd !== config.workspace) throw new Error('prepare evidence differs');
        verdict.targetInitializationSafe = true;
      } else if (stage === 'quiesced') {
        if (!idleThread(facts.sourceReadAfter, sourceId) || !completed(facts.sourceTerminal, sourceId, plan.source.turnId)) throw new Error('quiesced evidence differs');
        verdict.quiesced = true; verdict.noOtherWriters = true;
      } else if (stage === 'target-created') {
        const names = dynamicNames(facts.requestedSettings?.dynamicTools);
        if (!idleThread(facts.targetRead, targetId) || facts.startResponse?.thread?.id !== targetId ||
            !names.includes('accord_request_handoff') || !names.includes('accord_inspect_context')) throw new Error('target creation evidence differs');
        verdict.targetSettingsMatch = true; verdict.initializationEffectsVerified = true;
      } else if (stage === 'accepted') {
        if (!completed(facts.intakeTerminal, targetId, facts.intakeTurn?.id) || !idleThread(facts.sourceRead, sourceId)) throw new Error('intake evidence differs');
        verdict.accepted = true; verdict.sourceIdle = true; verdict.intakeEffectsVerified = true;
      } else if (stage === 'continue') {
        if (facts.recordedWriter !== 'target' || !idleThread(facts.sourceRead, sourceId)) throw new Error('continue evidence differs');
        verdict.singleWriter = true;
      } else if (stage === 'continued') {
        if (facts.recordedWriter !== 'target' || !completed(facts.continuationTerminal, targetId, facts.continuationTurn?.id)) throw new Error('continuation evidence differs');
        verdict.singleWriter = true; verdict.effectsVerified = true;
      } else if (stage === 'release') {
        if (facts.recordedWriter !== 'target' || !idleThread(facts.sourceRead, sourceId) ||
            !idleThread(facts.targetRead, targetId) || !completed(facts.continuationTerminal,
              targetId, facts.continuationTerminal?.params?.turn?.id)) throw new Error('release evidence differs');
        verdict.singleWriter = true; verdict.effectsVerified = true;
      } else throw new Error(`unknown verifier stage: ${stage}`);
      return verdict;
    }

    const session = createCodexSourceSession({connection, recorder, scopeRef: 'native-session-scope',
      threadStart: {cwd: config.workspace, model: 'fixture-no-model', modelProvider: 'accord_fixture',
        sandbox: 'read-only', approvalPolicy: 'never'},
      planResolver(nativeRequest, context) {
        const ordinal = plans.length + 1;
        if (ordinal > 2 || nativeRequest.params?.threadId !== context.threadId ||
            nativeRequest.params?.turnId !== context.turnId) throw new Error('unexpected source proposal');
        const now = Date.now(), recovery = context.deadlineMs;
        if (recovery - now < 6000) throw new Error('handoff budget is too small');
        activePlan = {transferId: `native-transfer-${ordinal}`, scopeRef: 'native-session-scope',
          authorityRef: `native-authority-${ordinal}`, stateRef: `native-state-${ordinal}`,
          source: {threadId: context.threadId, turnId: context.turnId},
          target: {cwd: config.workspace, model: 'fixture-no-model', modelProvider: 'accord_fixture'},
          handoffText: ordinal === 1 ?
            'Inspect current context once, request a nested handoff once, then finish this fixed read-only intake.' :
            'Finish this fixed read-only intake without tools or writes.',
          continuation: {input: 'Complete the fixed first continuation without tools or writes.',
            sandboxPolicy: {type: 'readOnly'}},
          deadlineMs: recovery - 4000, recoveryDeadlineMs: recovery};
        plans.push(clone(activePlan));
        return activePlan;
      }, verify: verifier,
      current(context) {
        const scope = recorder.readScope('native-session-scope');
        if (!activePlan || activePlan.source.threadId !== context.sourceThreadId) throw new Error('current plan differs');
        contextRefs.push({transferId: activePlan.transferId, writerThreadId: scope.writerThreadId});
        return {scopeRef: activePlan.scopeRef, authorityRef: activePlan.authorityRef,
          stateRef: activePlan.stateRef, writerThreadId: scope.writerThreadId};
      },
      ownerRequest(request, context) {
        ownerRequests.push({method: request.method, threadId: request.params?.threadId || null,
          turnId: request.params?.turnId || null, phase: context.phase || 'source'});
        return {error: {code: -32601, message: 'fixed native fixture has no owner handler for this request'}};
      }});

    const first = await session.run({input: 'Submit one handoff proposal, then finish this source turn.', deadlineMs: wall()});
    const adoptedFirst = await session.adoptTarget({deadlineMs: wall()});
    const second = await session.run({input: 'Submit one new handoff proposal, then finish this adopted source turn.', deadlineMs: wall()});
    const adoptedSecond = await session.adoptTarget({deadlineMs: wall()});
    const sourceId = first.sourceThreadId, target1 = first.target.threadId, target2 = second.target.threadId;
    if (new Set([sourceId, target1, target2]).size !== 3 || adoptedFirst.sourceThreadId !== target1 ||
        adoptedSecond.sourceThreadId !== target2) throw new Error('native carrier identities differ');
    const histories = {};
    for (const id of [sourceId, target1, target2]) {
      histories[id] = await connection.transport.request('thread/read', {threadId: id, includeTurns: true}, mono());
    }
    const records = {
      'native-transfer-1': recorder.read('native-transfer-1', 'native-session-scope'),
      'native-transfer-2': recorder.read('native-transfer-2', 'native-session-scope'),
    };
    const scope = recorder.readScope('native-session-scope');
    const sessionState = session.snapshot();
    if (sessionState.status !== 'ready' || sessionState.sourceThreadId !== target2 ||
        sessionState.transfers.length !== 2 || sessionState.transfers.some(item => item.settled !== true) ||
        scope.writerThreadId !== target2 || scope.activeTransferId !== null) throw new Error('native post-state differs');
    result = {schema: 'accord-codex-session-native-result/v1', success: true,
      binding: config.binding, first, adoptedFirst, second, adoptedSecond,
      threadIds: {source: sourceId, target1, target2}, histories, records, scope, sessionState,
      plans, verifyStages, contextRefs, ownerRequests,
      identities: {node: {path: config.identities.node.path, sha256: sha256(process.execPath),
        version: process.version}, codex: {path: config.argv[0], sha256: sha256(config.argv[0]),
        version: config.binding.hostVersion}},
      keepSha256: sha256(config.keepPath), providerRequestsExpected: 10,
      claimLimit: 'Fixed localhost provider and evidence-based test verifier only; no model judgment, shared Desktop control, cold recovery or product acceptance.'};
    }
  } catch (error) {
    failure = {name: error?.name || 'Error', message: error?.message || String(error),
      code: error?.code || null, phase: error?.phase || null, state: error?.state || null,
      rpcRequest: error?.rpcRequest || null};
  } finally {
    try {
      if (connection) { connection.close(); connectionClosed = true; }
      if (recorder) recorder.close();
      native.stdin.end();
      const remaining = Math.max(1, Math.min(15000, config.overallDeadlineMs - Date.now()));
      let timer;
      try {
        await Promise.race([Promise.all([exitPromise, stdoutPromise]),
          new Promise((_, reject) => { timer = setTimeout(() => reject(new Error('native natural exit timed out')), remaining); })]);
      } finally { clearTimeout(timer); }
      if (!nativeExit || nativeExit.code !== 0 || nativeExit.signal !== null || !stdoutEnded) {
        throw new Error('native app-server did not exit naturally');
      }
    } catch (error) {
      closeFailure = {name: error?.name || 'Error', message: error?.message || String(error)};
      if (!failure) failure = closeFailure;
    } finally {
      native.stdout.off('data', capture);
      for (const fd of [stdoutFd, stderrFd, requestsFd]) {
        try { fs.closeSync(fd); } catch (error) { if (!closeFailure) closeFailure = {name:error.name,message:error.message}; }
      }
    }
  }
  const document = {schema: 'accord-codex-session-native-envelope/v1', success: !failure && !closeFailure,
    result, failure, close: {connectionClosed, nativeExit, stdoutEnded, closeFailure, nativeBytes}};
  fs.writeFileSync(config.resultPath, JSON.stringify(document, null, 2) + '\n', {encoding: 'utf8', flag: 'wx'});
  process.stdout.write(JSON.stringify({kind: 'done', success: document.success,
    resultPath: config.resultPath, threadIds: result?.threadIds || null}) + '\n');
  if (!document.success) process.exitCode = 1;
}

const rl = readline.createInterface({input: process.stdin, crlfDelay: Infinity});
let received = false;
rl.on('line', line => {
  if (received) { process.stderr.write('multiple controller requests are not supported\n'); process.exitCode = 1; return; }
  received = true; rl.close(); process.stdin.destroy();
  let value;
  try { value = JSON.parse(line); }
  catch (error) { process.stderr.write(`invalid controller request: ${error.message}\n`); process.exitCode = 1; return; }
  run(value).catch(error => { process.stderr.write(`${error.stack || error}\n`); process.exitCode = 1; });
});
rl.on('close', () => { if (!received) process.exitCode = 1; });
