'use strict';
// Test caller, not a shipped controller. Native mode delegates to the existing
// Python App Server controller; mock mode exercises failure paths without a model.
const readline = require('node:readline');
const {performance} = require('node:perf_hooks');
const {handoff} = require('../../runtime/carrier-handoff.cjs');
const rl = readline.createInterface({input: process.stdin});
const pending = new Map();
let sequence = 0, started = false;
const clone = value => JSON.parse(JSON.stringify(value));
function remote(kind, args) {
  const id = ++sequence;
  process.stdout.write(JSON.stringify({kind, id, args}) + '\n');
  return new Promise((resolve, reject) => pending.set(id, {resolve, reject}));
}
async function run(config) {
  const calls = [], snapshots = [], verdicts = [];
  let revision = -1, state = null, target = null, turn = 0, sourceActive = config.scenario === 'active-source';
  let lease = null, scopeBusy = false;
  const scenario = config.scenario || 'success';
  // Inject only the two late-ack fixture clocks. Advance at the exact callback,
  // so host scheduling cannot expire an earlier, unrelated operation instead.
  let fixtureNow = performance.now(), requestDeadline = null;
  if (config.mode !== 'native' && ['late-cas-active', 'late-verifier'].includes(scenario)) {
    Object.defineProperty(performance, 'now', {value: () => fixtureNow, configurable: true});
  }
  const plan = config.plan || {transferId: 'transfer-1', scopeRef: 'fixture-scope', authorityRef: 'authority-1', stateRef: 'state-1',
    source: {threadId: 'source-1', ...(sourceActive ? {turnId: 'source-turn'} : {})},
    target: {cwd: '/bound-workspace', model: 'fixture-model'},
    handoffText: 'Retain the authorized task and protected original; current pause is absent.',
    continuation: {input: 'Perform the next authorized bounded step.', sandboxPolicy: {type: 'readOnly'}},
    deadlineMs: Date.now() + 5000, recoveryDeadlineMs: Date.now() + 6000};
  const reply = (stage) => ({decision: 'allow', scopeRef: plan.scopeRef, authorityRef: plan.authorityRef, stateRef: plan.stateRef,
    sourceRef: 'mock-evidence:' + stage, sourceRecoveryReady: true, quiesced: true, noOtherWriters: true,
    targetInitializationSafe: true, initializationEffectsVerified:true, intakeEffectsVerified:true,
    targetSettingsMatch: true, accepted: true, sourceIdle: true, singleWriter: true, effectsVerified: true});
  const transport = {connectionId: config.binding?.connectionId || 'test-connection', hostVersion: config.binding?.hostVersion || 'fixture-host',
    async request(method, params, deadline) {
      requestDeadline = deadline;
      calls.push({method, params: clone(params)});
      if (config.mode === 'native') return remote('request', [method, params, Math.max(0, deadline - performance.now())]);
      if (scenario === 'ambiguous-start' && method === 'thread/start') throw new Error('start response lost');
      if (method === 'thread/read') return {thread: {id: scenario === 'wrong-source' ? 'foreign' : params.threadId,
        status: {type: params.threadId === 'source-1' && sourceActive ? 'active' : 'idle'}}};
      if (method === 'turn/interrupt') {sourceActive = false; return {};}
      if (method === 'thread/start') {
        target = scenario === 'same-target' ? 'source-1' : 'target-1';
        if (scenario === 'connection-drift') transport.connectionId = 'replaced-connection';
        return {thread: {id: target, status: {type: 'idle'}}, cwd: params.cwd, model: params.model,
          approvalPolicy: 'never', sandbox: {type: 'readOnly'}};
      }
      if (method === 'turn/start') {
        turn++;
        if (turn === 2 && config.beforeContinuationDelayMs) {
          Atomics.wait(new Int32Array(new SharedArrayBuffer(4)), 0, 0, config.beforeContinuationDelayMs);
        }
        if (scenario === 'lost-continuation-ack' && turn === 2) throw new Error('continuation response lost');
        return {turn: {id: 'turn-' + (scenario === 'reused-turn' || scenario === 'reuse-first-intake' && turn===3 ? 1 : turn), status: 'inProgress'}};
      }
      if (method === 'thread/unsubscribe') return scenario === 'invalid-unsubscribe' ? {} : {status:'unsubscribed'};
      throw new Error('unexpected native method:' + method);
    },
    async waitTerminal(threadId, turnId, deadline) {
      calls.push({method: 'waitTerminal', params: {threadId, turnId}});
      if (config.mode === 'native') return remote('waitTerminal', [threadId, turnId, Math.max(0, deadline - performance.now())]);
      if (scenario === 'wait-timeout' && threadId === 'target-1') throw new Error('terminal unavailable');
      const status = scenario === 'unknown-terminal' ? 'queued' : threadId === 'source-1' ? 'interrupted' : scenario === 'continuation-failed' && turn === 2 ? 'failed' : 'completed';
      return {method: 'turn/completed', params: {threadId: scenario === 'wrong-terminal' ? 'foreign' : threadId,
        turn: {id: turnId, status, items: []}}};
    }};
  const recorder = {
    async begin(id, digest, initial) {
      if (config.mode === 'native') return remote('begin', [id, digest, initial]);
      if (scenario === 'duplicate') return {created: false, revision: 5};
      if (scenario === 'bad-begin') return {created:true, revision:'unknown'};
      if (scenario === 'begin-null') return null;
      if (scopeBusy || lease && lease.writerThreadId!==initial.source.threadId) return {created:false,revision};
      scopeBusy=true;
      lease={scopeRef:initial.scopeRef,transferId:id,token:'test-scope-lease',writerThreadId:initial.source.threadId};
      revision = 0; state = clone(initial); snapshots.push(state); return {created: true, revision, lease:clone(lease)};
    },
    async compareAndSet(id, expected, next, expectedLease) {
      if (config.mode === 'native') return remote('compareAndSet', [id, expected, next, expectedLease]);
      if (expected !== revision) throw new Error('CAS conflict');
      if (JSON.stringify(expectedLease)!==JSON.stringify(lease)) throw new Error('scope lease conflict');
      state = clone(next); snapshots.push(state); revision++;
      lease={...lease,writerThreadId:next.writerThreadId};
      if (state.phase==='source-subscription-released') scopeBusy=false;
      if (scenario === 'ambiguous-commit' && state.writer === 'target') throw new Error('commit acknowledgement lost');
      if (scenario === 'late-cas-active' && state.phase === 'continuation-started') {
        fixtureNow = requestDeadline + 1;
      }
      if (scenario === 'malformed-cas-active' && state.phase === 'continuation-started') {
        const broken={...lease};broken.self=broken;return {revision,lease:broken};
      }
      return {revision,lease:clone(lease)};
    }};
  const verify = async (stage, facts, deadline) => {
    verdicts.push(stage);
    if (config.mode === 'native') return remote('verify', [stage, facts, Math.max(0, deadline - performance.now())]);
    const verdict = reply(stage);
    if (scenario === 'reject-intake' && stage === 'accepted' || scenario === 'changed-authority' && stage === 'continue') verdict.decision = 'hold';
    if (scenario === 'wrong-authority') verdict.authorityRef = 'stale';
    if (scenario === 'invalid-settings' && stage === 'target-created') verdict.targetSettingsMatch = false;
    if (scenario === 'missing-effects' && stage === 'continued') delete verdict.effectsVerified;
    if (['extra-context','bad-extra-context','reuse-first-intake'].includes(scenario) && stage === 'accepted' && verdicts.filter(s=>s==='accepted').length===1) {
      verdict.decision='request-context';
      verdict.additionalInput='Additional already-authorized context: keep the original unchanged.';
      if (scenario==='bad-extra-context') verdict.authorityRef='unrelated-authority';
      delete verdict.accepted;
    }
    if (scenario === 'clock-jump' && stage === 'prepare') { const old=Date.now; Date.now=()=>old()+1000000; }
    if (scenario === 'late-verifier' && stage === 'prepare') fixtureNow = deadline + 1;
    if (scenario === 'stalled-verifier' && stage === 'prepare') await new Promise(() => {});
    if (scenario === 'unsafe-startup' && stage === 'prepare') delete verdict.targetInitializationSafe;
    if (scenario === 'unknown-intake-effect' && stage === 'accepted') delete verdict.intakeEffectsVerified;
    if (scenario === 'mutate-plan' && stage === 'prepare') {plan.target.cwd = '/foreign'; plan.handoffText = 'changed';}
    return verdict;
  };
  let result = null, error = null, concurrent = null;
  try {
    if (scenario==='same-scope-concurrent') {
      concurrent=await Promise.allSettled([handoff(plan,{transport,recorder,verify}),
        handoff({...plan,transferId:'transfer-2'},{transport,recorder,verify})]);
      result=concurrent.find(r=>r.status==='fulfilled')?.value || null;
      concurrent=concurrent.map(r=>({status:r.status,code:r.reason?.code}));
    } else result = await handoff(plan, {transport, recorder, verify});
  }
  catch (e) {error = {name:e.name, message:e.message, code:e.code, reconciliationRequired:e.reconciliationRequired, state:e.state};}
  process.stdout.write(JSON.stringify({kind:'done', result, error, calls, snapshots, verdicts, concurrent}) + '\n');
  rl.close(); process.stdin.destroy();
}
rl.on('line', line => {
  const value = JSON.parse(line);
  if (!started) {started = true; run(value).catch(e => {process.stderr.write(String(e.stack)); process.exitCode=1; rl.close(); process.stdin.destroy();}); return;}
  const waiting = pending.get(value.id);
  if (!waiting) throw new Error('unmatched host reply');
  pending.delete(value.id);
  if (value.error) waiting.reject(new Error(value.error)); else waiting.resolve(value.result);
});
