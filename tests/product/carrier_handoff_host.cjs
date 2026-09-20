'use strict';
// Test caller, not a shipped controller. Native mode delegates to the existing
// Python App Server controller; mock mode exercises failure paths without a model.
const readline = require('node:readline');
const {performance} = require('node:perf_hooks');
const {handoff, prepareHandoff, runHandoffProposal, HANDOFF_PROPOSAL_TOOL} = require('../../runtime/carrier-handoff.cjs');
const rl = readline.createInterface({input: process.stdin});
const pending = new Map();
let sequence = 0, started = false;
const clone = value => JSON.parse(JSON.stringify(value));
function remote(kind, args) {
  const id = ++sequence;
  process.stdout.write(JSON.stringify({kind, id, args}) + '\n');
  return new Promise((resolve, reject) => pending.set(id, {resolve, reject}));
}

async function runOwnedConnection(config) {
  // The test owns and launches the process. The shipped connection only receives
  // its streams; Python provides the existing fixture/recorder/verifier, not RPC.
  const fs = require('node:fs');
  const {spawn} = require('node:child_process');
  const {Writable} = require('node:stream');
  const {createOwnedAppServerConnection,CONTEXT_OBSERVATION_TOOL} = require('../../runtime/codex-connection.cjs');
  const log = config.nativeLogRoot;
  const stderr = fs.openSync(log + '/stderr.txt', 'wx');
  const stdout = fs.openSync(log + '/stdout.jsonl', 'wx');
  const requests = fs.openSync(log + '/requests.jsonl', 'wx');
  const native = spawn(config.argv[0], config.argv.slice(1), {
    cwd:config.plan.target.cwd, stdio:['pipe','pipe',stderr], windowsHide:true,
  });
  let rawBytes=0;
  const capture = chunk => {
    rawBytes+=chunk.length;
    if (rawBytes>8*1024*1024) throw new Error('native fixture output exceeded bound');
    fs.writeSync(stdout,chunk);
  };
  native.stdout.on('data',capture);
  const outgoing = new Writable({write(chunk,encoding,done) {
    fs.writeSync(requests,chunk); native.stdin.write(chunk,encoding,done);
  }});
  const connection=createOwnedAppServerConnection({stdin:outgoing,stdout:native.stdout,
    connectionId:config.binding.connectionId,hostVersion:config.binding.hostVersion});
  let result=null,error=null,context=null,exitCode=null,closeState=null;
  const contextReplies=[];
  const ended=new Promise((resolve,reject)=>{native.once('exit',code=>{exitCode=code;resolve(code);});native.once('error',reject);});
  try {
    const deadline=performance.now()+45000;
    const t=connection.transport;
    await t.request('initialize',{clientInfo:{name:'accord_connection_fixture',version:'1'},
      capabilities:{experimentalApi:true}},deadline);
    await t.notify('initialized',{},deadline);
    const source=await t.request('thread/start',{model:'fixture-no-model',modelProvider:'accord_fixture',
      cwd:config.plan.target.cwd,sandbox:'read-only',approvalPolicy:'never',
      dynamicTools:[HANDOFF_PROPOSAL_TOOL,...(config.contextRead?[CONTEXT_OBSERVATION_TOOL]:[])]},deadline);
    const turn=await t.request('turn/start',{threadId:source.thread.id,
      input:[{type:'text',text:'Submit one handoff proposal for the bound fixed task, then finish without other actions.'}]},deadline);
    const plan={...config.plan,source:{threadId:source.thread.id,turnId:turn.turn.id}};
    await remote('sourceReady',[source,turn]);
    let proposal;
    for (;;) {
      const received=await connection.receiveRequest(value=>value.method==='item/tool/call' &&
        value.params?.threadId===source.thread.id && value.params?.turnId===turn.turn.id &&
        [HANDOFF_PROPOSAL_TOOL.name,CONTEXT_OBSERVATION_TOOL.name].includes(value.params?.tool),deadline);
      if(received.params.tool===HANDOFF_PROPOSAL_TOOL.name){proposal=received;break;}
      if(!config.contextRead || contextReplies.length>=2) throw new Error('unexpected fixture context request');
      contextReplies.push(await connection.replyContext(received,deadline));
    }
    context=connection.context(source.thread.id,turn.turn.id,30000);
    await remote('sourceContext',[context]);
    const channel=connection.proposalChannel(proposal,async()=>({scopeRef:plan.scopeRef,
      authorityRef:plan.authorityRef,stateRef:plan.stateRef,writerThreadId:source.thread.id}));
    result=await runHandoffProposal(plan,{transport:t,
      recorder:{begin:(...args)=>remote('begin',args),compareAndSet:(...args)=>remote('compareAndSet',args)},
      verify:(stage,facts,limit)=>remote('verify',[stage,facts,Math.max(0,limit-performance.now())])},proposal,channel);
  } catch (e) {
    error={name:e.name,message:e.message,code:e.code,state:e.state,details:e.details};
  } finally {
    closeState=connection.close();
    native.stdin.end();
    let timer;
    try {await Promise.race([ended,new Promise((_,reject)=>{timer=setTimeout(()=>reject(new Error('native EOF exit timed out')),10000);})]);}
    finally {clearTimeout(timer);native.stdout.off('data',capture);fs.closeSync(stderr);fs.closeSync(stdout);fs.closeSync(requests);}
  }
  process.stdout.write(JSON.stringify({kind:'done',result,error,context,contextReplies,exitCode,closeState,rawBytes})+'\n');
  rl.close();process.stdin.destroy();
}
async function run(config) {
  const calls = [], snapshots = [], verdicts = [];
  let eventListener = null;
  let revision = -1, state = null, target = null, turn = 0, sourceActive = config.scenario === 'active-source';
  let lease = null, scopeBusy = false, sourceReads = 0;
  const scenario = config.scenario || 'success';
  // Inject only the two late-ack fixture clocks. Advance at the exact callback,
  // so host scheduling cannot expire an earlier, unrelated operation instead.
  let fixtureNow = performance.now(), requestDeadline = null;
  if (config.mode !== 'native' && ['late-cas-active', 'late-verifier'].includes(scenario)) {
    Object.defineProperty(performance, 'now', {value: () => fixtureNow, configurable: true});
  }
  const proposalCase = scenario.startsWith('proposal-');
  const plan = config.plan || {transferId: 'transfer-1', scopeRef: 'fixture-scope', authorityRef: 'authority-1', stateRef: 'state-1',
    source: {threadId: 'source-1', ...(sourceActive || proposalCase ? {turnId: 'source-turn'} : {})},
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
      if (method === 'thread/read') {
        const source = params.threadId === 'source-1';
        if (source) sourceReads++;
        const omitPersistence = source && (scenario === 'unknown-persistence' ||
          scenario === 'persistence-not-reobserved' && sourceReads === 4);
        return {thread: {id: scenario === 'wrong-source' ? 'foreign' : params.threadId,
          ...(!omitPersistence ? {ephemeral: source && (scenario === 'ephemeral-source' ||
            scenario === 'source-persistence-changed' && sourceReads > 1)} : {}),
          status: {type: source && sourceActive ? 'active' : 'idle'}}};
      }
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
    if (scenario === 'proposal-event-new-turn-during-intake' && stage === 'accepted') {
      eventListener({connectionId:transport.connectionId,hostVersion:transport.hostVersion,
        method:'turn/started',params:{threadId:plan.source.threadId,turn:{id:'new-source-turn'}}});
    }
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
  let result = null, error = null, concurrent = null, proposal = null;
  try {
    if (config.nativeProposal || proposalCase) {
      const nativeRequest = config.nativeProposal || {
        connectionId: transport.connectionId, hostVersion: transport.hostVersion,
        id: 42, method: 'item/tool/call', params: {threadId: 'source-1', turnId: 'source-turn',
          callId: 'source-proposal-call', tool: HANDOFF_PROPOSAL_TOOL.name, namespace: null,
          arguments: {reason: 'Preserve the bound responsibility in a fresh carrier.'}},
      };
      if (scenario === 'proposal-foreign-request') nativeRequest.params.threadId = 'foreign';
      if (scenario === 'proposal-foreign-namespace') nativeRequest.params.namespace = 'unrelated-component';
      if (scenario === 'proposal-injected-authority') nativeRequest.params.arguments.scopeRef = 'foreign';
      if (scenario.startsWith('proposal-event-') || config.nativeEventProposal) {
        proposal = {respondCount:0, currentCount:0, releaseCount:0};
        const envelope = event => ({connectionId:transport.connectionId,hostVersion:transport.hostVersion,...event});
        const newTurn = () => envelope({method:'turn/started',params:{threadId:plan.source.threadId,turn:{id:'new-source-turn'}}});
        const channel = {
          subscribe(listener, anchor) {
            proposal.subscriptionAnchor=clone(anchor);
            eventListener=listener;
            if (scenario === 'proposal-event-new-turn-before-response') listener(newTurn());
            return () => {
              proposal.releaseCount++; eventListener=null;
              if (scenario === 'proposal-event-release-error') throw new Error('listener removal uncertain');
            };
          },
          async respond(response) {
            proposal.respondCount++;
            proposal.callsBeforeDispatch=clone(calls);
            if (config.mode === 'native') {
              const observed = await remote('proposalEvents', [response]);
              for (const event of observed) eventListener(envelope(event));
              return;
            }
            const tool = envelope({method:'item/completed',params:{threadId:plan.source.threadId,turnId:plan.source.turnId,
              item:{type:'dynamicToolCall',id:nativeRequest.params.callId,tool:HANDOFF_PROPOSAL_TOOL.name,
                namespace:null,status:'completed',success:true,contentItems:response.result.contentItems}}});
            const terminal = envelope({method:'turn/completed',params:{threadId:plan.source.threadId,
              turn:{id:plan.source.turnId,status:'completed'}}});
            const foreign=clone(tool); foreign.params.threadId='foreign';
            eventListener(foreign);
            if (scenario === 'proposal-event-source-failed') terminal.params.turn.status='failed';
            if (scenario === 'proposal-event-tool-failed') tool.params.item.success=false;
            if (scenario === 'proposal-event-wrong-response') tool.params.item.contentItems=[];
            if (scenario === 'proposal-event-connection-drift') tool.connectionId='other-connection';
            if (scenario === 'proposal-event-early-terminal') eventListener(terminal);
            eventListener(tool);
            eventListener(tool); // duplicate replay is harmless, never another dispatch
            if (scenario === 'proposal-event-conflicting-replay') {
              const conflict=clone(tool); conflict.params.item.success=false; eventListener(conflict);
            }
            if (scenario === 'proposal-event-missing-terminal') {
              // Simulate the work deadline at the exact wait, not host timing.
              const end = performance.now()+7000;
              Object.defineProperty(performance,'now',{value:()=>end,configurable:true});
              return;
            }
            eventListener(terminal);
            if (scenario === 'proposal-event-new-turn-after-response') eventListener(newTurn());
            if (scenario === 'proposal-event-response-unknown') throw new Error('response write acknowledgement lost');
          },
          async current() {
            proposal.currentCount++;
            if (scenario === 'proposal-event-new-turn-during-current') eventListener(newTurn());
            return {scopeRef:plan.scopeRef,authorityRef:plan.authorityRef,
              stateRef:scenario==='proposal-event-changed-state'?'changed-state':plan.stateRef,
              writerThreadId:plan.source.threadId};
          },
        };
        result=await runHandoffProposal(plan,{transport,recorder,verify},nativeRequest,channel);
      } else {
      const prepared = await prepareHandoff(plan, {transport, recorder, verify}, nativeRequest);
      proposal = {response: prepared.response, callsBeforeDispatch: clone(calls), snapshotsBeforeDispatch: clone(snapshots)};
      const readiness = config.mode === 'native' ? await remote('proposalEvidence', [prepared.response]) : {
        toolCompleted: {method: 'item/completed', params: {threadId: 'source-1', turnId: 'source-turn',
          item: {type: 'dynamicToolCall', id: 'source-proposal-call', tool: HANDOFF_PROPOSAL_TOOL.name,
            namespace: null, status: 'completed', success: true, contentItems: prepared.response.result.contentItems}}},
        sourceTerminal: {method: 'turn/completed', params: {threadId: 'source-1', turn: {id: 'source-turn', status: 'completed'}}},
        current: {scopeRef: plan.scopeRef, authorityRef: plan.authorityRef, stateRef: plan.stateRef,
          writerThreadId: plan.source.threadId},
      };
      if (scenario === 'proposal-wrong-tool') readiness.toolCompleted.params.item.id = 'unrelated-call';
      if (scenario === 'proposal-wrong-turn') readiness.sourceTerminal.params.turn.id = 'unrelated-turn';
      if (scenario === 'proposal-failed-tool') readiness.toolCompleted.params.item.success = false;
      if (scenario === 'proposal-wrong-response') readiness.toolCompleted.params.item.contentItems = [{type:'inputText',text:'another response'}];
      if (scenario === 'proposal-failed-source') readiness.sourceTerminal.params.turn.status = 'failed';
      if (scenario === 'proposal-changed-state') readiness.current.stateRef = 'new-state';
      if (scenario === 'proposal-connection-drift') transport.connectionId = 'reconnected';
      if (scenario === 'proposal-expired') {
        const expiredNow = performance.now() + 7000;
        Object.defineProperty(performance, 'now', {value: () => expiredNow, configurable: true});
      }
      result = await prepared.dispatch(readiness);
      if (scenario === 'proposal-double-dispatch') {
        const before = calls.length;
        try { await prepared.dispatch(readiness); } catch (e) { proposal.duplicateError = e.code; }
        proposal.callsAfterDuplicate = calls.length - before;
      }
      }
    } else if (scenario==='same-scope-concurrent') {
      concurrent=await Promise.allSettled([handoff(plan,{transport,recorder,verify}),
        handoff({...plan,transferId:'transfer-2'},{transport,recorder,verify})]);
      result=concurrent.find(r=>r.status==='fulfilled')?.value || null;
      concurrent=concurrent.map(r=>({status:r.status,code:r.reason?.code}));
    } else result = await handoff(plan, {transport, recorder, verify});
  }
    catch (e) {error = {name:e.name, message:e.message, code:e.code, reconciliationRequired:e.reconciliationRequired, state:e.state, details:e.details};}
  process.stdout.write(JSON.stringify({kind:'done', result, error, calls, snapshots, verdicts, concurrent, proposal}) + '\n');
  rl.close(); process.stdin.destroy();
}
rl.on('line', line => {
  const value = JSON.parse(line);
  if (!started) {started = true; (value.mode==='native-connection'?runOwnedConnection(value):run(value)).catch(e => {process.stderr.write(String(e.stack)); process.exitCode=1; rl.close(); process.stdin.destroy();}); return;}
  const waiting = pending.get(value.id);
  if (!waiting) throw new Error('unmatched host reply');
  pending.delete(value.id);
  if (value.error) waiting.reject(new Error(value.error)); else waiting.resolve(value.result);
});
