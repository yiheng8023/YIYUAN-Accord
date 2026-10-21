'use strict';

// Task-local execution inside the existing MCP process. Host metadata identifies
// callers; review decisions are accountable Agent judgments, never inferred human
// authorization or proof that a string names genuine evidence. No source GUI RPC.
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const crypto = require('node:crypto');
const {spawn, spawnSync} = require('node:child_process');
const {performance} = require('node:perf_hooks');
const {operate} = require('./task-checkpoint.cjs');
const capabilities = require('./codex-capabilities.cjs');
const {createExternalHandoff, createOwnedNativeRunner} = require('./external-handoff.cjs');
const {openCarrierRecorder} = require('./carrier-recorder.cjs');
const MAX_EVIDENCE = 4 * 1024 * 1024, MAX_TOTAL = 16 * 1024 * 1024;
const ACTIONS = ['inventory', 'prepare-skill', 'prepare', 'inspect', 'read-evidence', 'commit', 'release', 'review', 'cancel', 'reconcile', 'reconcile-target'];
const text = (v, n = 4096) => typeof v === 'string' && v.trim() && v.length <= n && !v.includes('\0');
const hash = bytes => crypto.createHash('sha256').update(bytes).digest('hex');
const clone = value => JSON.parse(JSON.stringify(value));
function fail(code) { throw Object.assign(new Error(code), {code}); }
function samePath(a, b) { const normalize = x => process.platform === 'win32' ? path.resolve(x).toLowerCase() : path.resolve(x); return normalize(a) === normalize(b); }
function safeDirectory(directory, create = false) {
  if (!path.isAbsolute(directory)) fail('unsafe-execution-directory');
  if (!fs.existsSync(directory)) {
    if (!create) fail('execution-directory-missing');
    safeDirectory(path.dirname(directory), true); fs.mkdirSync(directory, {mode: 0o700});
  }
  if (!fs.lstatSync(directory).isDirectory() || fs.lstatSync(directory).isSymbolicLink() || !samePath(fs.realpathSync(directory), directory)) fail('unsafe-execution-directory');
  return directory;
}
function readFile(file, limit = MAX_EVIDENCE) {
  const stat = fs.lstatSync(file);
  if (!stat.isFile() || stat.isSymbolicLink() || stat.nlink !== 1 || stat.size > limit || !samePath(fs.realpathSync(file), file)) fail('unsafe-execution-evidence');
  return fs.readFileSync(file);
}
function atomic(file, value) {
  const bytes = Buffer.from(JSON.stringify(value));
  if (bytes.length > MAX_EVIDENCE) fail('execution-evidence-limit');
  if (fs.existsSync(file)) readFile(file);
  const temporary = file + '.' + crypto.randomUUID() + '.tmp';
  try {
    const fd = fs.openSync(temporary, 'wx', 0o600);
    try { fs.writeFileSync(fd, bytes); fs.fsyncSync(fd); } finally { fs.closeSync(fd); }
    fs.renameSync(temporary, file);
  } finally { if (fs.existsSync(temporary)) fs.unlinkSync(temporary); }
}
async function launcherVersion(launch, cwd) {
  const child = spawn(launch.executable, [...launch.prefix, '--version'], {cwd,
    windowsHide: true, stdio: ['ignore', 'pipe', 'pipe'], detached: process.platform !== 'win32'});
  const ownedPid = child.pid ?? null;
  let output = '', stopped = false, tooLarge = false, spawnFailed = false, exited = false, exitCode = null;
  let terminationAttempt = null, closeObserved = false;
  function stopOwnedVersion() {
    if (exited || ownedPid === null || child.pid !== ownedPid || child.exitCode !== null || child.signalCode !== null || terminationAttempt) return;
    if (process.platform === 'win32') {
      terminationAttempt = 'owned-pid-tree';
      spawnSync(path.join(process.env.SystemRoot || 'C:\\Windows', 'System32', 'taskkill.exe'),
        ['/PID', String(ownedPid), '/T', '/F'], {stdio: 'ignore', windowsHide: true, shell: false, timeout: 1000});
    } else {
      terminationAttempt = 'owned-process-group';
      try { process.kill(-ownedPid, 'SIGKILL'); } catch (_) { /* No exit claim follows the signal alone. */ }
    }
  }
  child.stdout.on('data', bytes => {
    if (tooLarge) return;
    if (output.length + bytes.length > 16384) { tooLarge = true; stopOwnedVersion(); return; }
    output += bytes.toString('utf8');
  });
  child.stderr.on('data', () => {});
  const closed = new Promise(resolve => {
    child.once('error', () => { spawnFailed = true; });
    child.once('exit', code => { exited = true; exitCode = code; });
    child.once('close', code => { closeObserved = true; resolve(code); });
  });
  let timer, recoveryTimer, code;
  const timeout = new Promise(resolve => { timer = setTimeout(() => {
    stopped = true; stopOwnedVersion();
    recoveryTimer = setTimeout(() => resolve(null), 1000);
  }, 3000); });
  try { code = await Promise.race([closed, timeout]); } finally { clearTimeout(timer); clearTimeout(recoveryTimer); }
  if (stopped || tooLarge || spawnFailed || code !== 0 || !/^codex-cli [\w.\-]+\s*$/.test(output)) {
    if (code === null) { child.stdout.destroy(); child.stderr.destroy(); child.unref(); }
    throw Object.assign(new Error('native-cli-version-unavailable'), {code: 'native-cli-version-unavailable',
      processState: {pid: ownedPid, exitObserved: exited, closeObserved, exitCode, forced: stopped || tooLarge,
        terminationAttempt, descendantVerification: 'not-independently-observed', recoveryRequired: true}});
  }
  return output.trim();
}
const string = {type: 'string', minLength: 1, maxLength: 4096};
const TOOL = Object.freeze({name: 'coordinate_task_execution',
  description: 'Discover native skills or coordinate one bounded fresh target for this root task. Default is read-only. Optional workspace-write requires declared checkpoint outputs, protected write-authority evidence, exact original hashes and independent write-prepare review; after natural closure of the read-only peer, cold resume must report the restricted actual native policy before commit review or writing. Unsupported policy stays held; no setup or permission fallback. Selected-file snapshots total at most 1 MiB and are not an OS file allowlist or proof of outside-scope effects. Optional skillRequest reuses prepare-skill selection and fresh native inventory for exact typed input in the first continuation; policy metadata is observed, not automatic authorization or prohibition. Root reads the exact Skill source and applicable restrictions. Supply explicit cwd. Capability queries retain the helper defaults: 10 seconds for querying plus at most three 5-second cleanup windows, within the separately configured host tool timeout. prepare requires a current active checkpoint and complete reconciled native input; authoritySourceRef identifies the actual delegation and quiescenceSourceRef must name a protected checkpoint input containing the inspected drain/writer evidence. Those references do not prove authorization or absence of writers. Root must inspect each exact awaiting-review observation and submit its own independent judgment using reviewId and observationSha256. prepare/commit/release run asynchronously; inspect/read-evidence/cancel remain available. reconcile only settles an exact known-stopped source-retained lease after independent review of current authority, original pauses, old actor quiescence and effects; it starts no target and preserves the original failure/deadline. reconcile-target is separate: it requires an active current source, exact stopped-target record/lease and a protected effectSourceRef JSON of kind external-target-effects/v1 with operationId, recordSha256, actorSourceRef, authoritySourceRef, effects[{disposition:no-effect-verified|applied-verified|partial-effects-reviewed,sourceRef}], and unresolved:[]. These are review inputs, not proofs. Root reviews original invariants, actual local/external effects, actor quiescence and explicit source-current or target-retained ownership. The bounded reader only reads persistent target facts; notLoaded does not prove absence of another controller. After hash-bound review and rechecks, settlement rotates the fence and may return the exact original public scope to the current source. It neither resumes a target nor replays a turn, alters a pause, erases original failures/ACK loss, or declares business completion. The target result is never self-approved. Source identity comes only from native metadata. No default GUI control, permission escalation, replay, permanent daemon or shutdown-survival claim.',
  annotations: {readOnlyHint: false, destructiveHint: true, idempotentHint: false, openWorldHint: true},
  inputSchema: {type: 'object', additionalProperties: false, properties: {
    action: {type: 'string', enum: ACTIONS}, cwd: string,
    epoch: string, expectedRevision: {type: 'integer', minimum: 0}, scopeRef: string,
    model: string, effort: string, intake: {...string, maxLength: 32768},
    continuation: {...string, maxLength: 32768}, postRelease: {...string, maxLength: 32768},
    deadlineMs: {type: 'integer', minimum: 1}, authoritySourceRef: string, quiescenceSourceRef: string,
    sandbox: {type: 'string', enum: ['read-only', 'workspace-write']},
    writeScope: {type: 'object', additionalProperties: false, properties: {authoritySourceRef: string,
      outputs: {type: 'array', minItems: 1, maxItems: 64, items: {type: 'object', additionalProperties: false,
        properties: {path: string, expectedSha256: {type: ['string', 'null'], pattern: '^[a-f0-9]{64}$'}, expectedEffect: string},
        required: ['path', 'expectedSha256', 'expectedEffect']}}}, required: ['authoritySourceRef', 'outputs']},
    operationId: string, reviewId: string, observationSha256: {type: 'string', pattern: '^[a-f0-9]{64}$'},
    recordRevision: {type: 'integer', minimum: 0}, recordSha256: string, leaseSha256: string,
    effectSourceRef: string, writerDisposition: {type: 'string', enum: ['source-current', 'target-retained']},
    decision: {type: 'string', enum: ['allow', 'deny']}, sourceRef: string, reason: string,
    evidenceId: {type: 'string', pattern: '^[a-f0-9]{64}$'}, offset: {type: 'integer', minimum: 0},
    maxChars: {type: 'integer', minimum: 1, maximum: 16000},
    skillRequest: {type: 'object', additionalProperties: false, properties: {
      originalRequest: {...string, maxLength: 16384},
      delegation: {type: 'object', additionalProperties: false, properties: {sourceRef: string, scope: {...string, maxLength: 8192}}, required: ['sourceRef', 'scope']},
      selection: {type: 'object', additionalProperties: false, properties: {name: string, path: string,
        expectedSha256: {type: 'string', pattern: '^[a-fA-F0-9]{64}$'},
        expectedPolicySha256: {type: ['string', 'null']}}, required: ['name', 'path']},
    }, required: ['originalRequest', 'delegation', 'selection']},
  }, required: ['action', 'cwd']},
});

function createNativeTaskExecution(options) {
  const sourceOf = options.sourceOf, readState = options.readState || operate;
  const capability = options.capabilities || capabilities;
  const factory = options.nativeFactory || (async ({cwd, deadlineMs}) => {
    const launch = capabilities.launcher(process.env.CODEX_CLI_PATH || undefined);
    const hostVersion = await launcherVersion(launch, cwd);
    return createOwnedNativeRunner({executable: launch.executable,
      args: [...launch.prefix, 'app-server', '--listen', 'stdio://'], cwd, deadlineMs,
      hostVersion});
  });
  const slots = new Map(), capabilitiesPending = new Set(), requestOperations = new Map();
  let closing = false;
  function rootSource(params) {
    const source = sourceOf(params);
    if (!source) fail('native-call-metadata-unavailable');
    if (source.threadId !== source.sessionTreeId) fail('shared-session-scope-requires-reconciliation');
    if (!text(source.model) || !text(source.hostVersion)) fail('native-host-metadata-unavailable');
    return source;
  }
  function currentState(source, cwd, expected) {
    const snapshot = readState({op: 'status', session_id: source.sessionTreeId, cwd,
      nativeInputEvidence: true, currentHost: {threadId: source.threadId, turnId: source.turnId,
        model: source.model, hostVersion: source.hostVersion, sourceRef: 'codex-mcp-call:' + source.callId}});
    const evidence = snapshot.nativeInputEvidence;
    if (snapshot.mode !== 'active' || !snapshot.checkpoint || snapshot.checkpoint.canContinue !== true ||
        snapshot.needsNativeReplay || snapshot.needsResumeReconciliation || snapshot.hostObservationCurrent !== true ||
        snapshot.currentInputReconciled !== true || !snapshot.inputReceipt?.present ||
        evidence?.state !== 'observed' || evidence.latestInputReconciled !== true || evidence.latestNativeInputsComplete !== true ||
        !Array.isArray(evidence.pendingInputs) || evidence.pendingInputs.length) fail('current-source-not-executable');
    if (expected && (snapshot.epoch !== expected.epoch || snapshot.revision !== expected.expectedRevision)) fail('source-basis-changed');
    if (!snapshot.checkpointSource || !/^[a-f0-9]{64}$/.test(snapshot.checkpointSource.sha256) ||
        !Array.isArray(snapshot.inspection?.inputs) || snapshot.inspection.inputs.some(row => row.unchanged !== true || row.stable !== true)) fail('protected-source-unavailable');
    const protectedInputsDigest = hash(JSON.stringify(snapshot.inspection.inputs.map(row => ({path: row.path, current: row.current}))));
    return {snapshot, facts: {sourceThreadId: source.threadId, sourceTurnId: source.turnId,
      epoch: snapshot.epoch, revision: snapshot.revision,
      authorityRef: 'native-input:' + snapshot.epoch + ':checkpoint:' + snapshot.checkpointSource.sha256,
      snapshotRef: snapshot.checkpointSource.sha256, protectedInputsDigest,
      inputComplete: true, paused: false, recoveryRequired: false}};
  }
  function directory(source, cwd, create = false) {
    const base = options.storageRoot || process.env.YIYUAN_ACCORD_TASK_STATE_DIR || path.join(os.homedir(), '.yiyuan-accord', 'task-state');
    const id = hash(JSON.stringify({threadId: source.threadId, cwd: fs.realpathSync(cwd)}));
    return safeDirectory(path.join(path.resolve(base), 'native-executions', id), create);
  }
  function putEvidence(slot, value) {
    const bytes = Buffer.from(JSON.stringify(value)), evidenceId = hash(bytes);
    if (bytes.length > MAX_EVIDENCE) fail('execution-evidence-limit');
    const file = path.join(slot.dir, evidenceId + '.json');
    if (!fs.existsSync(file)) {
      if (slot.bytes + bytes.length > MAX_TOTAL) fail('execution-evidence-limit');
      fs.writeFileSync(file, bytes, {flag: 'wx', mode: 0o600}); slot.bytes += bytes.length;
    }
    else if (hash(readFile(file)) !== evidenceId) fail('execution-evidence-changed');
    return {evidenceId, sha256: evidenceId, bytes: bytes.length, complete: true};
  }
  function outputFiles(cwd, outputs) {
    let total = 0;
    return outputs.map(output => {
      const file = path.resolve(cwd, output.path);
      safeDirectory(path.dirname(file));
      try { fs.lstatSync(file); } catch (error) {
        if (error.code === 'ENOENT') return {path: output.path, sha256: null, bytes: 0, contentsBase64: null};
        throw error;
      }
      const bytes = readFile(file, 1024 * 1024);
      total += bytes.length;
      if (total > 1024 * 1024) fail('write-snapshot-limit');
      const sha256 = hash(bytes);
      if (hash(readFile(file, 1024 * 1024)) !== sha256) fail('write-output-unstable');
      return {path: output.path, sha256, bytes: bytes.length, contentsBase64: bytes.toString('base64')};
    });
  }
  const outputHashes = files => files.map(({path, sha256, bytes}) => ({path, sha256, bytes}));
  function writeBaseline(args, observed) {
    if (![undefined, 'read-only', 'workspace-write'].includes(args.sandbox)) fail('invalid-execution-sandbox');
    if (args.sandbox !== 'workspace-write') {
      if (args.writeScope !== undefined) fail('unexpected-write-scope');
      return null;
    }
    const scope = args.writeScope;
    if (!scope || Object.keys(scope).some(k => !['authoritySourceRef', 'outputs'].includes(k)) ||
        !text(scope.authoritySourceRef) || !Array.isArray(scope.outputs) || !scope.outputs.length || scope.outputs.length > 64 ||
        !observed.snapshot.inspection.inputs.some(row => row.path === scope.authoritySourceRef && row.current.present === true)) fail('protected-write-authority-required');
    const seen = new Set();
    for (const row of scope.outputs) {
      if (!row || Object.keys(row).some(k => !['path', 'expectedSha256', 'expectedEffect'].includes(k)) ||
          !text(row.path) || path.isAbsolute(row.path) || row.path.split(/[\\/]/).some(part => !part || part === '.' || part === '..' || /[:<>"|?*\0]|[. ]$/.test(part)) ||
          !text(row.expectedEffect) || row.expectedSha256 !== null && !/^[a-f0-9]{64}$/.test(row.expectedSha256 || '')) fail('invalid-write-output');
      const file = path.resolve(args.cwd, row.path), key = process.platform === 'win32' ? file.toLowerCase() : file;
      if (seen.has(key) || !observed.snapshot.checkpoint.outputs.some(out => samePath(path.resolve(args.cwd, out.path), file)) ||
          observed.snapshot.inspection.inputs.some(input => samePath(path.resolve(args.cwd, input.path), file))) fail('write-output-outside-bound-contract');
      seen.add(key);
    }
    const files = outputFiles(args.cwd, scope.outputs);
    if (files.some((file, i) => file.sha256 !== scope.outputs[i].expectedSha256)) fail('write-baseline-mismatch');
    return files;
  }
  function save(slot) {
    const view = slot.engine?.inspect() || slot.recovery?.view;
    if (view) slot.stateEvidence = putEvidence(slot, view);
    const summary = {operationId: slot.id, phase: view?.phase || 'preparing', busy: Boolean(view?.busy || slot.recovery?.reading || slot.recovery?.committing),
      source: {threadId: slot.source.threadId, turnId: slot.source.turnId},
      workspace: {cwd: slot.cwd, binding: 'caller-selected'},
      target: view?.target || null, writer: view?.writer || 'source',
      sourceRecovery: view?.sourceRecovery || 'retained',
      pendingEffect: view?.pendingEffect ? {kind: view.pendingEffect.kind, method: view.pendingEffect.method || null,
        requestRef: view.pendingEffect.requestRef || null} : null,
      nativeClosed: view?.nativeClosed || null, failure: slot.failure || view?.failure?.code || null,
      reviewRequest: slot.review ? {reviewId: slot.review.id, stage: slot.review.stage,
        observationSha256: slot.review.evidence.sha256, evidence: slot.review.evidence} : null,
      stateEvidence: slot.stateEvidence || null, controllerState: slot.recovery ? 'reconciliation-only-current-process' : 'owned-current-process',
      reconciliationBasis: stoppedBasis(slot),
      targetReconciliationBasis: stoppedBasis(slot, true),
      targetRecoveryResource: slot.targetRecoveryResource || null,
      targetSettlementAttempt: slot.targetSettlementAttempt || null,
      scopeBinding: view?.reconciliation?.scopeBinding || null,
      startupFailureEvidence: slot.startupFailureEvidence || null,
      prestartRejection: slot.prestartRejection || null,
      claimLimit: 'Root must verify scope, authorization, quiescence, semantic intake/results and resource effects from the bound sources. Cooperative duty release is not host shutdown survival.'};
    atomic(path.join(slot.dir, 'status.json'), summary);
    return summary;
  }
  function stoppedRecord(slot, target = false) {
    const locator = slot.stateEvidence || slot.saved?.stateEvidence;
    if (!locator) fail('stopped-record-unavailable');
    const bytes = readFile(path.join(slot.dir, locator.evidenceId + '.json'));
    if (hash(bytes) !== locator.sha256) fail('execution-evidence-changed');
    const view = JSON.parse(bytes), borrowed = slot.recorder && !slot.recorderClosed;
    const recorder = borrowed ? slot.recorder : openCarrierRecorder({path: path.join(path.dirname(slot.dir), 'carrier.sqlite')});
    try {
      const record = recorder[target ? 'inspectExternalStoppedTarget' : 'inspectExternalStopped'](slot.id, view.scopeRef);
      if (record.state.source.threadId !== slot.source.threadId) fail('operation-owner-mismatch');
      return {record, basis: {recordRevision: record.revision, recordSha256: hash(JSON.stringify(record.state)),
        leaseSha256: hash(JSON.stringify(record.lease))}};
    } finally { if (!borrowed) recorder.close(); }
  }
  function stoppedBasis(slot, target = false) {
    const phase = slot.engine?.inspect().phase || slot.recovery?.view.phase || slot.saved?.phase;
    if (!['held', 'cancelled-held', 'awaiting-stopped-review'].includes(phase)) return null;
    try { return stoppedRecord(slot, target).basis; } catch (_) { return null; }
  }
  function beginReconciliation(slot, args, source, target = false) {
    if (slot.review || slot.engine?.inspect().busy || slot.recovery?.committing || slot.recovery?.reading) fail('operation-busy');
    const resource = slot.targetRecoveryResource || slot.saved?.targetRecoveryResource;
    if (resource && resource.state !== 'closed') fail('recovery-resource-unverified');
    if ((slot.targetSettlementAttempt || slot.saved?.targetSettlementAttempt)?.state === 'outcome-unknown') fail('target-settlement-unknown');
    const original = stoppedRecord(slot, target);
    for (const key of Object.keys(original.basis)) if (args[key] !== original.basis[key]) fail('stopped-record-basis-changed');
    if (!Number.isSafeInteger(args.deadlineMs) || args.deadlineMs <= Date.now() || args.deadlineMs > Date.now() + 300000) fail('bounded-reconciliation-deadline-required');
    const currentObserved = currentState(source, slot.cwd, args), current = currentObserved.facts;
    if (target && (!text(args.effectSourceRef) || !['source-current', 'target-retained'].includes(args.writerDisposition))) fail('invalid-target-reconciliation');
    const recovery = {original, current, target, args: clone(args), deadlineMs: args.deadlineMs,
      view: {...original.record.state, phase: target ? 'reading-stopped-target' : 'awaiting-stopped-review'}};
    const fresh = {...slot, saved: null, engine: null, source: original.record.state.source,
      caller: source, recovery, recorderClosed: false, failure: null,
      bytes: fs.readdirSync(slot.dir).filter(name => /^[a-f0-9]{64}\.json$/.test(name))
        .reduce((sum, name) => sum + readFile(path.join(slot.dir, name)).length, 0),
      recorder: openCarrierRecorder({path: path.join(path.dirname(slot.dir), 'carrier.sqlite')})};
    fresh.current = () => {
      if (recovery.cancelled) fail('reconciliation-cancelled');
      if (fresh.caller.turnId !== source.turnId || fresh.caller.model !== source.model || fresh.caller.hostVersion !== source.hostVersion) fail('source-host-or-turn-changed');
      const observation = currentState(fresh.caller, slot.cwd, args), now = observation.facts;
      if (hash(JSON.stringify(now)) !== hash(JSON.stringify(current))) fail('reconciliation-source-changed');
      if (Date.now() >= args.deadlineMs) fail('reconciliation-review-expired');
      if (target && hash(JSON.stringify(targetMaterial(fresh, observation))) !== recovery.materialSha256) fail('target-effects-or-invariants-changed');
      return now;
    };
    if (target) {
      try { recovery.material = targetMaterial(fresh, currentObserved); }
      catch (error) { fresh.recorder.close(); throw error; }
      recovery.materialSha256 = hash(JSON.stringify(recovery.material));
      slots.set(slot.id, fresh);
      recovery.timer = setTimeout(() => stop(fresh, 'Target reconciliation expired').catch(() => {}), args.deadlineMs - Date.now());
      recovery.reading = true;
      fresh.running = prepareTargetReview(fresh).catch(async error => {
        fresh.failure ||= safeCode(error); recovery.view = original.record.state;
        if (!recovery.reader) fresh.targetRecoveryResource = {state: 'unverified', process: error.processState || null};
        try { await closeTargetReader(fresh); } finally { fresh.recorder.close(); fresh.recorderClosed = true; }
      }).finally(() => { recovery.reading = false; save(fresh); if (fresh.recorderClosed) releaseRequests(fresh); });
      return save(fresh);
    }
    const evidence = putEvidence(fresh, {stage: 'external-known-stopped', original: {state: original.record.state, ...original.basis},
      currentSource: source, currentBasis: current, currentContract: currentObserved.snapshot.checkpoint,
      currentContractSource: currentObserved.snapshot.checkpointSource, reconciliationDeadlineMs: args.deadlineMs,
      requiredJudgment: 'Independently verify current authority and original pause disposition, old actor quiescence, target initialization effects, resource closure and source-retained ownership. No target turn is replayed.'});
    fresh.review = {id: crypto.randomUUID(), stage: 'external-known-stopped', evidence, reject() {}};
    recovery.timer = setTimeout(() => stop(fresh, 'Reconciliation review expired').catch(() => {}), args.deadlineMs - Date.now());
    slots.set(slot.id, fresh);
    return save(fresh);
  }
  function evidenceObject(slot, id) {
    if (!/^[a-f0-9]{64}$/.test(id || '')) fail('invalid-recovery-evidence');
    const bytes = readFile(path.join(slot.dir, id + '.json'));
    if (hash(bytes) !== id) fail('execution-evidence-changed');
    return JSON.parse(bytes);
  }
  function targetMaterial(slot, observed) {
    const recovery = slot.recovery, state = recovery.original.record.state, args = recovery.args;
    const decision = evidenceObject(slot, state.verification.prepare);
    const packet = evidenceObject(slot, decision.observationSha256);
    if (decision.stage !== 'prepare' || decision.decision !== 'allow' || packet.stage !== 'prepare' ||
        hash(JSON.stringify({plan: packet.supplied.plan, source: state.source, basis: packet.supplied.basis})) !== state.planDigest) fail('original-plan-evidence-mismatch');
    const scopeBinding = {requestedScope: packet.requestedScope, cwd: fs.realpathSync(slot.cwd), sourceThreadId: state.source.threadId, scopeRef: state.scopeRef};
    if (!text(scopeBinding.requestedScope) || hash(JSON.stringify({threadId: state.source.threadId, cwd: scopeBinding.cwd, scope: scopeBinding.requestedScope})) !== state.scopeRef) fail('original-scope-binding-mismatch');
    for (const input of packet.checkpoint.inputs) {
      const now = observed.snapshot.inspection.inputs.find(row => row.path === input.path);
      if (!now || hash(JSON.stringify(now.current)) !== hash(JSON.stringify(input.observed))) fail('original-input-invariants-changed');
    }
    if (hash(JSON.stringify(observed.snapshot.checkpoint.outputs)) !== hash(JSON.stringify(packet.checkpoint.outputs))) fail('original-output-contract-changed');
    const effectRow = observed.snapshot.inspection.inputs.find(row => row.path === args.effectSourceRef && row.current.present);
    if (!effectRow) fail('protected-effect-source-required');
    const bytes = readFile(path.resolve(slot.cwd, args.effectSourceRef));
    if (hash(bytes) !== effectRow.current.sha256) fail('effect-source-changed');
    const effects = JSON.parse(bytes);
    if (effects.kind !== 'external-target-effects/v1' || effects.operationId !== slot.id || effects.recordSha256 !== recovery.original.basis.recordSha256 ||
        !text(effects.actorSourceRef) || !text(effects.authoritySourceRef) || !Array.isArray(effects.unresolved) || effects.unresolved.length ||
        !Array.isArray(effects.effects) || !effects.effects.length || effects.effects.length > 64 || effects.effects.some(row =>
          !text(row.sourceRef) || !['no-effect-verified', 'applied-verified', 'partial-effects-reviewed'].includes(row.disposition))) fail('target-effects-unresolved');
    const outputs = state.plan.writeScope?.outputs || packet.checkpoint.outputs;
    if (state.plan.writeScope) evidenceObject(slot, packet.writes.baseline.evidence.sha256);
    const files = outputFiles(slot.cwd, outputs);
    return {scopeBinding, effects, effectSource: {path: args.effectSourceRef, sha256: effectRow.current.sha256},
      originalPrepareEvidence: decision.observationSha256, originalBaseline: packet.writes?.baseline || null,
      currentOutputs: outputHashes(files), currentOutputEvidence: putEvidence(slot, {kind: 'selected-write-files', files})};
  }
  async function closeTargetReader(slot) {
    const recovery = slot.recovery;
    if (!recovery.reader) return;
    recovery.closing ||= recovery.reader.close();
    const closure = await recovery.closing;
    const closed = closure.closed === true && closure.primaryProcessClosed === true && closure.exitObserved === true &&
      closure.closeObserved === true && closure.forced === false && closure.exitCode === 0 && closure.signal === null &&
      closure.recoveryRequired === false && closure.terminationAttempt === null;
    slot.targetRecoveryResource = {...slot.targetRecoveryResource, state: closed ? 'closed' : 'unverified', closure};
    save(slot); return closure;
  }
  async function targetFacts(slot) {
    slot.current();
    const recovery = slot.recovery, state = recovery.original.record.state;
    const reply = await recovery.reader.request('thread/read', {threadId: state.target.threadId, includeTurns: true},
      performance.now() + Math.max(1, recovery.deadlineMs - Date.now()), ref => {
        recovery.readRequest = ref; slot.targetRecoveryResource.lastReadRequest = ref; save(slot);
      });
    slot.current();
    const thread = reply?.thread;
    if (thread?.id !== state.target.threadId || thread.ephemeral !== false ||
        !['idle', 'notLoaded'].includes(thread.status?.type) || !Array.isArray(thread.turns) ||
        thread.turns.length > state.turnStarts || new Set(thread.turns.map(turn => turn.id)).size !== thread.turns.length ||
        thread.turns.some(turn => !text(turn.id) || !['completed', 'interrupted', 'failed'].includes(turn.status))) fail('target-activity-unresolved');
    for (const turn of [state.intake, state.firstContinuation, state.postReleaseTurn, state.stoppedTurn].filter(Boolean)) {
      if (!thread.turns.some(row => row.id === turn.turnId && row.status === turn.terminal)) fail('target-terminal-evidence-mismatch');
    }
    if (state.pendingEffect?.kind === 'native-turn' && !thread.turns.some(row => row.id === state.pendingEffect.turnId)) fail('target-terminal-evidence-mismatch');
    return {id: thread.id, ephemeral: thread.ephemeral, status: thread.status, turns: thread.turns};
  }
  async function prepareTargetReview(slot) {
    const recovery = slot.recovery;
    slot.current(); slot.targetRecoveryResource = {state: 'starting'}; save(slot);
    recovery.reader = await factory({cwd: slot.cwd, source: slot.caller,
      deadlineMs: Math.min(recovery.deadlineMs, Date.now() + 10000)});
    slot.targetRecoveryResource = {state: 'open', connectionId: recovery.reader.connectionId, hostVersion: recovery.reader.hostVersion}; save(slot);
    slot.current();
    if (!text(recovery.reader.connectionId) || recovery.reader.connectionId === recovery.original.record.state.connection.connectionId ||
        recovery.reader.hostVersion !== recovery.original.record.state.connection.hostVersion) fail('target-reader-identity-changed');
    recovery.nativeFacts = await targetFacts(slot);
    const evidence = putEvidence(slot, {stage: 'external-known-stopped-target', original: recovery.original,
      originalStateEvidence: putEvidence(slot, recovery.original.record.state), currentSource: slot.caller,
      currentBasis: recovery.current, material: recovery.material, nativeFactsEvidence: putEvidence(slot, recovery.nativeFacts),
      readRequest: recovery.readRequest, writerDisposition: recovery.args.writerDisposition,
      requiredJudgment: 'Independently verify original actors cannot dispatch, all material local/external effects and pauses, unchanged original inputs, current authority and explicit writer disposition. notLoaded is connection-local, not proof of no other controller. Statements/selected bytes are not authorization or whole-workspace proof. No resume, replay, business completion or source release is inferred.'});
    recovery.view = {...recovery.view, phase: 'awaiting-target-effect-review'};
    slot.review = {id: crypto.randomUUID(), stage: 'external-known-stopped-target', evidence, reject() {}};
  }
  async function finishTargetReconciliation(slot, args, source, decision, review) {
    const recovery = slot.recovery;
    if (recovery.committing) fail('operation-busy');
    recovery.committing = true;
    try {
      if (args.decision !== 'allow') { recovery.view = recovery.original.record.state; return save(slot); }
      const facts = await targetFacts(slot);
      if (hash(JSON.stringify(facts)) !== hash(JSON.stringify(recovery.nativeFacts))) fail('target-facts-changed');
      const readerClosed = await closeTargetReader(slot);
      if (slot.targetRecoveryResource.state !== 'closed') fail('recovery-resource-unverified');
      const current = slot.current(), exact = stoppedRecord(slot, true);
      if (JSON.stringify(exact.basis) !== JSON.stringify(recovery.original.basis)) fail('stopped-record-basis-changed');
      const state = exact.record.state, receipt = {kind: 'external-known-stopped-target', ...exact.basis,
        originalFailure: state.failure, originalDeadlineMs: state.plan.deadlineMs,
        originalStateEvidence: putEvidence(slot, state).sha256, currentSource: source, currentBasis: current,
        recoveryDeadlineMs: recovery.deadlineMs,
        scopeBinding: recovery.material.scopeBinding, writerDisposition: recovery.args.writerDisposition,
        decision: args.decision, sourceRef: args.sourceRef, observationSha256: review.evidence.sha256,
        decisionEvidence: decision.sha256, materialSha256: recovery.materialSha256,
        nativeFactsSha256: hash(JSON.stringify(facts)), readerClosed};
      slot.current();
      slot.targetSettlementAttempt = {id: crypto.randomUUID(), state: 'outcome-unknown',
        recordRevision: exact.record.revision, leaseSha256: exact.basis.leaseSha256, decisionEvidence: decision.sha256};
      save(slot);
      const settled = slot.recorder.settleExternalStoppedTarget(slot.id, exact.record.revision, exact.record.lease, receipt);
      const seen = slot.recorder.read(slot.id, state.scopeRef), scope = slot.recorder.readScope(state.scopeRef);
      recovery.view = seen.state;
      if (seen.revision !== settled.revision || JSON.stringify(scope) !== JSON.stringify(settled.scope) ||
          seen.state.phase !== 'external-target-reconciled' || seen.state.reconciliation.decisionEvidence !== decision.sha256) fail('target-settlement-unknown');
      slot.targetSettlementAttempt.state = 'observed-settled';
      slot.current(); return save(slot);
    } catch (error) {
      slot.failure = safeCode(error);
      try { recovery.view = slot.recorder.read(slot.id, recovery.original.record.state.scopeRef).state; } catch (_) { /* Keep the unknown outcome. */ }
      if (slot.targetSettlementAttempt?.state === 'outcome-unknown' &&
          ['CAS_CONFLICT', 'EXTERNAL_TARGET_NOT_SETTLEABLE'].includes(error.code)) slot.targetSettlementAttempt.state = 'not-applied';
      throw error;
    }
    finally {
      clearTimeout(recovery.timer);
      try { await closeTargetReader(slot); } finally {
        recovery.committing = false; slot.recorder.close(); slot.recorderClosed = true; releaseRequests(slot); save(slot);
      }
    }
  }
  function finishReconciliation(slot, args, source, decision, review) {
    const recovery = slot.recovery;
    clearTimeout(recovery.timer);
    try {
      if (args.decision !== 'allow') { recovery.view = recovery.original.record.state; return save(slot); }
      const current = slot.current(), exact = stoppedRecord(slot);
      if (JSON.stringify(exact.basis) !== JSON.stringify(recovery.original.basis)) fail('stopped-record-basis-changed');
      slot.current();
      const record = exact.record, receipt = {kind: 'external-known-stopped', ...exact.basis,
        originalPhase: record.state.phase, originalFailure: record.state.failure,
        originalDeadlineMs: record.state.plan.deadlineMs, currentSource: source, currentBasis: current,
        decision: args.decision, sourceRef: args.sourceRef, observationSha256: review.evidence.sha256,
        decisionEvidence: decision.sha256};
      const settled = slot.recorder.settleExternalStopped(slot.id, record.revision, record.lease, receipt);
      const observed = slot.recorder.read(slot.id, record.state.scopeRef), scope = slot.recorder.readScope(record.state.scopeRef);
      recovery.view = observed.state;
      if (observed.revision !== settled.revision || JSON.stringify(scope) !== JSON.stringify(settled.scope) ||
          observed.state.phase !== 'external-source-retained' || JSON.stringify(observed.state.reconciliation) !== JSON.stringify(receipt)) fail('reconciliation-settlement-unknown');
      slot.current();
      return save(slot);
    } catch (error) {
      slot.failure = safeCode(error); save(slot); throw error;
    } finally { slot.recorder.close(); slot.recorderClosed = true; releaseRequests(slot); }
  }
  function load(source, cwd, id) {
    if (!/^[a-f0-9-]{36}$/.test(id || '')) fail('invalid-operation-id');
    const slot = slots.get(id);
    if (slot) {
      if (source.threadId !== slot.source.threadId || !samePath(cwd, slot.cwd)) fail('operation-owner-mismatch');
      slot.caller = source;
      return slot;
    }
    const dir = safeDirectory(path.join(directory(source, cwd), id));
    const summary = JSON.parse(readFile(path.join(dir, 'status.json')));
    if (summary.operationId !== id || summary.source.threadId !== source.threadId) fail('operation-owner-mismatch');
    return {id, dir, cwd, source, saved: {...summary, busy: null, controllerState: 'not-owned-current-process',
      recovery: 'Read retained evidence; no execution, cancellation of an unknown process, or replay is authorized by this record.'}};
  }
  function validate(args) {
    const common = ['action', 'cwd'], fields = {
      inventory: [], 'prepare-skill': ['skillRequest'],
      prepare: ['epoch', 'expectedRevision', 'scopeRef', 'model', 'effort', 'intake', 'continuation', 'postRelease', 'deadlineMs', 'authoritySourceRef', 'quiescenceSourceRef', 'skillRequest', 'sandbox', 'writeScope'],
      inspect: ['operationId'], 'read-evidence': ['operationId', 'evidenceId', 'offset', 'maxChars'],
      commit: ['operationId'], release: ['operationId'],
      review: ['operationId', 'reviewId', 'observationSha256', 'decision', 'sourceRef'], cancel: ['operationId', 'reason'],
      reconcile: ['operationId', 'epoch', 'expectedRevision', 'recordRevision', 'recordSha256', 'leaseSha256', 'deadlineMs'],
      'reconcile-target': ['operationId', 'epoch', 'expectedRevision', 'recordRevision', 'recordSha256', 'leaseSha256', 'deadlineMs', 'writerDisposition', 'effectSourceRef'],
    };
    if (!args || !ACTIONS.includes(args.action) || !text(args.cwd) || !path.isAbsolute(args.cwd) ||
        Object.keys(args).some(key => !common.includes(key) && !fields[args.action].includes(key)) ||
        Buffer.byteLength(JSON.stringify(args)) > 128 * 1024) fail('invalid-task-execution-request');
    safeDirectory(args.cwd);
  }
  function launch(slot, action) {
    if (slot.saved) fail('controller-not-owned');
    if (slot.engine.inspect().busy) fail('operation-busy');
    let promise;
    try { promise = action(); } catch (error) { promise = Promise.reject(error); }
    slot.running = promise.catch(async error => {
      slot.failure ||= safeCode(error);
      const view = slot.engine.inspect();
      if (['INVALID_PLAN', 'DEADLINE_EXCEEDED'].includes(error.code) && view.phase === 'new' &&
          view.busy === false && view.revision === null && view.turnStarts === 0 &&
          view.writer === 'source' && view.sourceRecovery === 'retained' &&
          !view.transferId && !view.connection && !view.pendingEffect && !view.nativeClosed &&
          view.nativeStartPending === false && view.skillPreparationPending === false && !view.lateNativeClosed) {
        slot.prestartRejection = {code: error.code,
          evidence: putEvidence(slot, {kind: 'known-prestart-rejection', code: error.code,
            deadlineMs: slot.requestedDeadlineMs, observation: view})};
        await slot.engine.cancel('Plan rejected before any start: ' + error.code);
      }
    })
      .finally(() => {
        if (slot.review) { slot.review.reject(Object.assign(new Error('operation-ended'), {code: 'operation-ended'})); slot.review = null; }
        try { save(slot); } finally {
          if (['completed', 'held', 'cancelled-held'].includes(slot.engine.inspect().phase)) {
            slot.recorder.close(); slot.recorderClosed = true; releaseRequests(slot);
          }
        }
        // Only this proven pre-execute rejection is dropped after persistence
        // and recorder closure. Arbitrary new/unknown operations are retained.
        if (slot.prestartRejection && slot.recorderClosed) slots.delete(slot.id);
      }).catch(error => { slot.failure ||= safeCode(error); });
    return save(slot);
  }
  async function stop(slot, reason) {
    if (slot.review) { slot.review.reject(Object.assign(new Error(reason), {code: 'execution-stopped'})); slot.review = null; }
    if (slot.recovery) {
      clearTimeout(slot.recovery.timer);
      if (slot.recovery.target) {
        slot.recovery.cancelled = true;
        await closeTargetReader(slot);
        if (slot.running) { try { await slot.running; } catch (_) {} }
        if (slot.recovery.view.phase !== 'external-target-reconciled') slot.recovery.view = slot.recovery.original.record.state;
      }
      if (slot.recovery.view.phase === 'awaiting-stopped-review') slot.recovery.view = slot.recovery.original.record.state;
      slot.recorder.close(); slot.recorderClosed = true;
    } else if (!slot.recorderClosed) await slot.engine.cancel(reason);
    if (slot.running) {
      if (slot.recovery?.target) { try { await slot.running; } catch (_) {} }
      else await slot.running;
    }
    if (slot.recorderClosed) releaseRequests(slot);
    return save(slot);
  }
  function releaseRequests(slot) { for (const [id, owner] of requestOperations) if (owner === slot) requestOperations.delete(id); }
  function reclaimFinishedSlots() {
    for (const [id, slot] of slots) {
      const view = slot.engine?.inspect() || slot.recovery?.view;
      if (!view || !slot.recorderClosed || slot.review || view.busy || view.pendingEffect ||
          view.nativeStartPending || view.lateNativeClosed || view.skillPreparationPending) continue;
      if (slot.targetSettlementAttempt?.state === 'outcome-unknown' ||
          slot.targetRecoveryResource && slot.targetRecoveryResource.state !== 'closed') continue;
      const skillFailure = view.skillPreparationFailure;
      if (skillFailure && (skillFailure.code === 'CLEANUP_UNVERIFIED' || skillFailure.process &&
          (!skillFailure.process.exitObserved || !skillFailure.process.closeObserved || skillFailure.process.forced))) continue;
      const noStart = ['held', 'cancelled-held'].includes(view.phase) && view.failure?.priorPhase === 'preparing' &&
        view.revision === null && view.turnStarts === 0 && !view.transferId && !view.connection && !view.nativeClosed;
      const closed = ['completed', 'external-source-retained', 'external-target-reconciled'].includes(view.phase) &&
        view.nativeClosed?.closed === true && view.nativeClosed.forced === false;
      if (!noStart && !closed) continue;
      try {
        const summary = JSON.parse(readFile(path.join(slot.dir, 'status.json')));
        const bytes = readFile(path.join(slot.dir, summary.stateEvidence.evidenceId + '.json'));
        if (summary.operationId !== id || hash(bytes) !== summary.stateEvidence.sha256 ||
            hash(JSON.stringify(view)) !== summary.stateEvidence.sha256) continue;
        if (closed) {
          const recorder = openCarrierRecorder({path: path.join(path.dirname(slot.dir), 'carrier.sqlite')});
          try {
            const record = recorder.read(id, view.scopeRef);
            if (record.lease.transferId === id || record.state.pendingEffect !== null ||
                record.state.phase !== (view.phase === 'completed' ? 'external-completed' : view.phase) ||
                hash(JSON.stringify(record.state.nativeClosed)) !== hash(JSON.stringify(view.nativeClosed)) ||
                view.revision !== undefined && record.revision !== view.revision) continue;
          }
          finally { recorder.close(); }
        }
        releaseRequests(slot); slots.delete(id);
      } catch (_) { /* Uncertain records retain their controller slot. */ }
    }
  }
  function observe(params) {
    let source; try { source = rootSource(params); } catch (_) { return; }
    const cwd = params.arguments?.cwd;
    if (!text(cwd) || !path.isAbsolute(cwd)) return;
    for (const slot of slots.values()) {
      if (slot.source.threadId !== source.threadId || !samePath(slot.cwd, cwd) || slot.recorderClosed) continue;
      slot.caller = source;
      try { slot.current(); }
      catch (error) {
        slot.failure ||= safeCode(error);
        slot.cancellation ||= stop(slot, 'Source authority or input changed').catch(() => { slot.failure ||= 'source-cancellation-unverified'; });
      }
    }
  }
  async function cancelRequest(requestId) {
    const slot = requestOperations.get(String(requestId));
    if (slot) await stop(slot, 'Native MCP request cancelled');
  }
  async function call(params, requestId = null) {
    try {
      if (closing) fail('execution-transport-closing');
      const args = params.arguments; validate(args);
      const source = rootSource(params);
      observe(params);
      if (args.action === 'inventory' || args.action === 'prepare-skill') {
        if (capabilitiesPending.size >= 2) fail('capability-query-busy');
        // Keep the helper's measured default query/cleanup windows. A host's
        // tool timeout is configured separately; never shorten healthy cleanup.
        const query = {cwd: args.cwd, ...(process.env.CODEX_CLI_PATH ? {codexPath: process.env.CODEX_CLI_PATH} : {})};
        const pending = args.action === 'inventory' ? capability.inventory(query) : capability.prepare(args.skillRequest, query);
        capabilitiesPending.add(pending);
        let value; try { value = await pending; } finally { capabilitiesPending.delete(pending); }
        if (Buffer.byteLength(JSON.stringify(value)) > 100 * 1024) fail('bounded-capability-result-exceeded');
        return {isError: false, value};
      }
      if (args.action === 'prepare') {
        if (slots.size >= 16) reclaimFinishedSlots();
        if (slots.size >= 16) fail('execution-operation-limit');
        if (!['epoch', 'scopeRef', 'model', 'intake', 'continuation', 'postRelease', 'authoritySourceRef', 'quiescenceSourceRef'].every(k => text(args[k], k === 'intake' || k === 'continuation' || k === 'postRelease' ? 32768 : 4096)) ||
            args.effort !== undefined && !text(args.effort) ||
            !Number.isSafeInteger(args.expectedRevision) || !Number.isSafeInteger(args.deadlineMs) || args.deadlineMs <= Date.now() || args.deadlineMs > Date.now() + 3600000) fail('invalid-execution-plan');
        const observed = currentState(source, args.cwd, args);
        const baseline = writeBaseline(args, observed);
        const quiescence = observed.snapshot.inspection.inputs.find(row => row.path === args.quiescenceSourceRef && row.current.present === true);
        if (!quiescence) fail('quiescence-protected-source-required');
        const base = directory(source, args.cwd, true), id = crypto.randomUUID(), dir = path.join(base, id);
        safeDirectory(dir, true);
        const dbPath = path.join(base, 'carrier.sqlite');
        const recorder = openCarrierRecorder({path: dbPath, create: !fs.existsSync(dbPath)});
        const scopeRef = hash(JSON.stringify({threadId: source.threadId, cwd: fs.realpathSync(args.cwd), scope: args.scopeRef}));
        try {
          const prior = recorder.readScope(scopeRef);
          if (prior.activeTransferId !== null) fail('SCOPE_BUSY');
          if (prior.writerThreadId !== source.threadId) fail('WRITER_CONFLICT');
        } catch (error) {
          if (error.code !== 'SCOPE_NOT_FOUND') { recorder.close(); fs.rmdirSync(dir); throw error; }
        }
        const slot = {id, dir, cwd: args.cwd, source, caller: source, bytes: 0, recorder,
          expected: {epoch: args.epoch, expectedRevision: args.expectedRevision},
          requestedDeadlineMs: args.deadlineMs, failure: null, review: null};
        const current = stage => {
          if (slot.caller.turnId !== source.turnId || slot.caller.model !== source.model || slot.caller.hostVersion !== source.hostVersion) fail('source-host-or-turn-changed');
          const now = currentState(slot.caller, args.cwd, slot.expected);
          const row = now.snapshot.inspection.inputs.find(x => x.path === args.quiescenceSourceRef && x.current.present === true);
          if (!row || row.current.sha256 !== quiescence.current.sha256) fail('quiescence-source-changed');
          if (slot.skillSource) {
            const skill = slot.skillSource, policy = path.join(path.dirname(skill.realPath), 'agents', 'openai.yaml');
            if (hash(readFile(skill.realPath)) !== skill.sha256 ||
                (fs.existsSync(policy) ? hash(readFile(policy)) : null) !== skill.policySha256) fail('skill-source-changed');
          }
          if (slot.outputReview && (slot.review || stage === 'after-' + slot.outputReview.stage) &&
              hash(JSON.stringify(outputHashes(outputFiles(args.cwd, args.writeScope.outputs)))) !== slot.outputReview.hash) fail('reviewed-write-outputs-changed');
          return {...now.facts, quiescence: {noInFlightEffects: true, noOtherWriters: true,
            evidenceRef: 'root-reviewed-protected-source:' + row.path + ':' + row.current.sha256}};
        };
        slot.current = current;
        if (baseline) slot.baseline = {fingerprints: outputHashes(baseline),
          evidence: putEvidence(slot, {kind: 'selected-write-files', files: baseline})};
        slot.engine = createExternalHandoff({source, recorder, current,
          async prepareSkill(request) {
            current();
            if (capabilitiesPending.size >= 2) fail('capability-query-busy');
            const pending = capability.prepare(request, {cwd: args.cwd,
              ...(process.env.CODEX_CLI_PATH ? {codexPath: process.env.CODEX_CLI_PATH} : {})});
            capabilitiesPending.add(pending);
            let result;
            try { result = await pending; } finally { capabilitiesPending.delete(pending); }
            if (slot.skillSource && hash(JSON.stringify(result.source)) !== hash(JSON.stringify(slot.skillSource))) fail('skill-source-changed');
            slot.skillSource = clone(result.source); current(); return result;
          },
          nativeFactory: async opts => {
            try { return await factory({...opts, source}); }
            catch (error) {
              if (error.processState) slot.startupFailureEvidence = putEvidence(slot, {reason: safeCode(error),
                process: Object.fromEntries(['pid', 'exitObserved', 'closeObserved', 'exitCode', 'forced', 'terminationAttempt', 'terminationExitCode', 'terminationError', 'descendantVerification', 'recoveryRequired', 'closureScope'].filter(key => Object.hasOwn(error.processState, key)).map(key => [key, error.processState[key]]))});
              throw error;
            }
          },
          verify(stage, supplied, state) {
            if (closing || slot.review) fail('review-state-unavailable');
            current();
            let writes = null;
            if (baseline) {
              const files = outputFiles(args.cwd, args.writeScope.outputs), fingerprints = outputHashes(files);
              if (['prepare', 'target-created', 'write-prepare', 'commit'].includes(stage) &&
                  hash(JSON.stringify(fingerprints)) !== hash(JSON.stringify(slot.baseline.fingerprints))) fail('write-before-transfer-or-baseline-changed');
              slot.outputReview = {stage, hash: hash(JSON.stringify(fingerprints))};
              writes = {scope: args.writeScope, baseline: slot.baseline, fingerprints,
                currentEvidence: putEvidence(slot, {kind: 'selected-write-files', files}),
                claimLimit: 'These are selected-file bytes and hashes, not a workspace-wide effect or OS allowlist proof. Root independently verifies authorized diffs, outside-scope effects, native policy and result quality.'};
            }
            const evidence = putEvidence(slot, {stage, supplied, state,
              writes,
              requestedScope: args.scopeRef,
              sourceBasis: observed.facts, checkpoint: observed.snapshot.checkpoint,
              authoritySourceRef: args.authoritySourceRef,
              quiescence: {sourceRef: args.quiescenceSourceRef, sha256: quiescence.current.sha256,
                claimLimit: 'Protected bytes are verified; Root must independently assess their current drain/writer meaning.'}});
            return new Promise((resolve, reject) => {
              slot.review = {id: crypto.randomUUID(), stage, evidence, resolve, reject}; save(slot);
            });
          }});
        slots.set(id, slot);
        if (requestId !== null) requestOperations.set(String(requestId), slot);
        const plan = Object.fromEntries(['model', 'effort', 'intake', 'continuation', 'postRelease', 'deadlineMs', 'skillRequest', 'sandbox', 'writeScope'].filter(k => args[k] !== undefined).map(k => [k, args[k]]));
        return {isError: false, value: launch(slot, () => slot.engine.prepare({...plan, cwd: args.cwd, transferId: id, scopeRef}))};
      }
      const slot = load(source, args.cwd, args.operationId);
      if (args.action === 'reconcile' || args.action === 'reconcile-target') {
        const value = beginReconciliation(slot, args, source, args.action === 'reconcile-target');
        if (requestId !== null) requestOperations.set(String(requestId), slots.get(slot.id));
        return {isError: false, value};
      }
      if (args.action === 'read-evidence') {
        if (!/^[a-f0-9]{64}$/.test(args.evidenceId || '') || !Number.isSafeInteger(args.offset ?? 0) || (args.offset ?? 0) < 0 ||
            !Number.isSafeInteger(args.maxChars ?? 8000) || (args.maxChars ?? 8000) < 1 || (args.maxChars ?? 8000) > 16000) fail('invalid-evidence-page');
        const bytes = readFile(path.join(slot.dir, args.evidenceId + '.json'));
        if (hash(bytes) !== args.evidenceId) fail('execution-evidence-changed');
        const body = new TextDecoder('utf-8', {fatal: true}).decode(bytes), offset = args.offset ?? 0;
        if (offset > body.length) fail('invalid-evidence-page');
        const end = Math.min(body.length, offset + (args.maxChars ?? 8000));
        return {isError: false, value: {operationId: slot.id, evidenceId: args.evidenceId, sha256: args.evidenceId,
          offset, text: body.slice(offset, end), totalChars: body.length, complete: end === body.length,
          next: end === body.length ? null : {operationId: slot.id, evidenceId: args.evidenceId, offset: end}}};
      }
      if (slot.saved) return {isError: args.action !== 'inspect', value: {...slot.saved,
        reconciliationBasis: stoppedBasis(slot), targetReconciliationBasis: stoppedBasis(slot, true)}};
      if (args.action === 'inspect') return {isError: false, value: save(slot)};
      if (args.action === 'cancel') {
        if (!text(args.reason)) fail('cancel-reason-required');
        return {isError: false, value: await stop(slot, args.reason)};
      }
      slot.current();
      if (args.action === 'review') {
        const review = slot.review;
        if (!review || args.reviewId !== review.id || args.observationSha256 !== review.evidence.sha256 ||
            !['allow', 'deny'].includes(args.decision) || !text(args.sourceRef)) fail('review-basis-mismatch');
        const bytes = readFile(path.join(slot.dir, review.evidence.evidenceId + '.json'));
        if (hash(bytes) !== args.observationSha256) fail('execution-evidence-changed');
        const decision = putEvidence(slot, {reviewId: review.id, observationSha256: args.observationSha256,
          stage: review.stage, decision: args.decision, sourceRef: args.sourceRef,
          nativeSource: {threadId: source.threadId, turnId: source.turnId, callId: source.callId}});
        slot.review = null;
        if (slot.recovery?.target) {
          slot.running = finishTargetReconciliation(slot, args, source, decision, review);
          return {isError: false, value: await slot.running};
        }
        if (slot.recovery) return {isError: false, value: finishReconciliation(slot, args, source, decision, review)};
        review.resolve({decision: args.decision, evidenceRef: decision.sha256});
        return {isError: false, value: save(slot)};
      }
      if (args.action === 'commit' || args.action === 'release') {
        if (slot.recovery) fail('operation-not-executable');
        if (requestId !== null) requestOperations.set(String(requestId), slot);
        return {isError: false, value: launch(slot, () => slot.engine[args.action]({requestedByCall: source.callId}))};
      }
      fail('invalid-task-execution-request');
    } catch (error) { return {isError: true, value: {schema: 'yiyuan-accord-task-execution/v1', state: 'unavailable', reason: safeCode(error),
      ...(error.processState ? {process: Object.fromEntries(['pid', 'started', 'exitObserved', 'closeObserved', 'exitCode', 'signal', 'forced', 'terminationAttempt', 'descendantVerification'].filter(key => Object.hasOwn(error.processState, key)).map(key => [key, error.processState[key]]))} : {}),
      claimLimit: 'No new authority or success is implied. Inspect the exact existing operation before retrying an uncertain effect.'}}; }
  }
  async function close() {
    closing = true;
    const results = await Promise.allSettled([...slots.values()].map(async slot => {
      const result = await stop(slot, 'MCP transport closed');
      slot.recorder.close(); slot.recorderClosed = true; return result;
    }));
    await Promise.allSettled([...capabilitiesPending]);
    return results.map(row => row.status === 'fulfilled' ? row.value : {state: 'cleanup-unverified'});
  }
  return Object.freeze({call, close, observe, cancelRequest});
}
function safeCode(error) { return /^[A-Za-z][A-Za-z0-9_-]{0,95}$/.test(error?.code || error?.message || '') ? error.code || error.message : 'task-execution-unavailable'; }
module.exports = {TOOL, createNativeTaskExecution};
