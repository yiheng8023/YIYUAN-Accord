"""Source-session protocol integration; fixed local RPC, no model or host process."""
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
MODULE = ROOT / "runtime" / "codex-session.cjs"


SOURCE_TOOL_FORMAT_SCENARIO = r'''
const {createCodexSourceSession}=require(process.argv[1]);
const tools=JSON.parse(process.argv[2]), original=JSON.stringify(tools), requests=[];
let scope=null,scopeWrites=0;
const connection={transport:{connectionId:'format-fixture',hostVersion:'format-fixture',
  async request(method,params){requests.push({method,params});
    if(method==='thread/start'){
      if(params.dynamicTools.some(tool=>tool.type!=='function'))
        throw Error('dynamic tools must use either canonical or legacy format consistently');
      return {thread:{id:'source',ephemeral:false,status:{type:'idle'}}};}
    return {turn:{id:'turn'}};},waitTerminal(){}},
  async receiveTurnActivity(){return {type:'terminal',terminal:{method:'turn/completed',
    params:{threadId:'source',turn:{id:'turn',status:'completed'}}}};},
  respondRequest(){},replyContext(){},proposalChannel(){}};
const recorder={readScope(){if(!scope)throw Object.assign(Error('missing'),{code:'SCOPE_NOT_FOUND'});
    return scope;},bindScope(ref,id){scopeWrites++;scope={scopeRef:ref,writerThreadId:id,
    activeTransferId:null,token:'fixture'};return {scope};},begin(){},compareAndSet(){},read(){},settle(){}};
(async()=>{let error=null;
  try{const session=createCodexSourceSession({connection,recorder,scopeRef:'scope',
    threadStart:{cwd:'C:/fixture',model:'fixture',dynamicTools:tools},
    planResolver(){},verify(){},current(){},ownerRequest(){}});
    await session.run({input:'format fixture',deadlineMs:Date.now()+2000});}
  catch(e){error={name:e.name,message:e.message,code:e.code};}
  console.log(JSON.stringify({error,requests,scopeWrites,inputUnchanged:JSON.stringify(tools)===original}));
})().catch(e=>{console.error(e);process.exitCode=1});
'''


SCOPE_REQUEST_SCENARIO = r'''
const {createCodexSourceSession}=require(process.argv[1]);
const mode=process.argv[2];
let scope=null,unreadable=false,ownerCalls=0,replies=0,activity=0;
const lose=()=>{if(mode.endsWith('unknown'))unreadable=true;
  else scope={...scope,[mode.endsWith('writer')?'writerThreadId':'token']:'changed'};};
const recorder={readScope(){if(unreadable)throw Error('scope unavailable');
  if(!scope)throw Object.assign(Error('missing'),{code:'SCOPE_NOT_FOUND'});return scope;},
  bindScope(ref,id){scope={scopeRef:ref,writerThreadId:id,activeTransferId:null,token:'one'};
    return {scope};},begin(){},compareAndSet(){},read(){},settle(){}};
const request={id:1,method:'approval/request',params:{threadId:'source',turnId:'turn'}};
const connection={transport:{connectionId:'fixture',hostVersion:'fixture',
  async request(method){return method==='thread/start'?{thread:{id:'source',ephemeral:false}}:{turn:{id:'turn'}};},
  waitTerminal(){}},async receiveTurnActivity(){if(!activity++){
    if(mode.startsWith('before-'))lose();return {type:'request',request};}
    return {type:'terminal',terminal:{method:'turn/completed',
      params:{threadId:'source',turn:{id:'turn',status:'completed'}}}};},
  async respondRequest(){replies++;},replyContext(){},proposalChannel(){}};
const session=createCodexSourceSession({connection,recorder,scopeRef:'scope',
  threadStart:{cwd:'C:/fixture',model:'fixture'},planResolver(){},verify(){},current(){},
  ownerRequest(){ownerCalls++;if(mode.startsWith('during-'))lose();
    return {result:{decision:'approved'}};}});
(async()=>{let code=null,retry=null;
  try{await session.run({input:'fixture',deadlineMs:Date.now()+2000});}
  catch(error){code=error.code;try{await session.run({input:'no replay',deadlineMs:Date.now()+1000});}
    catch(next){retry=next.code;}}
  console.log(JSON.stringify({code,retry,ownerCalls,replies,snapshot:session.snapshot()}));
})().catch(error=>{console.error(error);process.exitCode=1});
'''


NODE_SCENARIO = r'''
const {PassThrough, Writable} = require('node:stream');
const {performance} = require('node:perf_hooks');
const {createOwnedAppServerConnection} = require(process.argv[1]);
const {openCarrierRecorder} = require(process.argv[2]);
const {createCodexSourceSession,CodexSourceSessionError} = require(process.argv[3]);
const mode = process.argv[4], databasePath = process.argv[5];
const slowRecordMs = Number(process.argv[6] || 0);
const slowReleaseMs = Number(process.argv[7] || 0);
const handoffWorkMs = Number(process.argv[8] || 0);
const targetTools = process.argv[9] ? JSON.parse(process.argv[9]) : null;
const adoptionPrecondition = ['adopt-old-lease', 'adopt-stale-ref',
  'adopt-busy', 'adopt-missing-tools'].includes(mode);
const output = new PassThrough(), sent = [], starts = [], serverResponses = [];
let targetTurn = 0, sourceTurn = 0, targetCreated = 0, sourceUnsubscribed = 0, sourceStarted = false;
const emit = value => output.write(Buffer.from(JSON.stringify(value) + '\n'));
const response = (frame, result) => queueMicrotask(() => emit({jsonrpc:'2.0', id:frame.id, result}));
function serverRequest(id, method, params) {
  if (id === 102) {
    if (mode === 'proposal-no-turn') delete params.turnId;
    if (mode === 'proposal-unscoped') delete params.threadId;
    if (mode === 'proposal-no-call') delete params.callId;
    if (mode === 'proposal-bad-args') params.arguments = {};
  }
  emit({jsonrpc:'2.0', id, method, params});
}
function invalidateProposalSource() {
  emit({method:'turn/started', params:{threadId:'source-1', turn:{id:'changed-source-turn'}}});
}
function handle(frame) {
  sent.push(frame);
  if (!frame.method) {
    serverResponses.push(frame);
    if (['decline-send-loss', 'handoff-source-send-loss'].includes(mode) && frame.id === 102)
      throw new Error('decline response send outcome is unknown');
    if (frame.id === 100) queueMicrotask(() => serverRequest(101, 'approval/request', {
      threadId:'source-1', turnId:'source-turn-1', reason:'fixture-owner-decision'}));
    if (frame.id === 101) queueMicrotask(() => {
      serverRequest(102, 'item/tool/call', {
        threadId:'source-1', turnId:'source-turn-1', callId:'handoff-call',
        tool:'accord_request_handoff', namespace:null,
        arguments:{reason:'Move the fixed task to a fresh carrier.'}});
      if (['handoff-source-queued', 'handoff-source-send-loss'].includes(mode)) serverRequest(105, 'item/tool/call', {
        threadId:'source-1', turnId:'source-turn-1', callId:'queued-context',
        tool:'accord_inspect_context', namespace:null, arguments:{maxAgeMs:30000}});
    });
    if (frame.id === 102 && frame.result?.success === false) {
      queueMicrotask(() => mode === 'decline-then-transfer'
        ? serverRequest(103, 'item/tool/call', {threadId:'source-1', turnId:'source-turn-1',
            callId:'later-handoff-call', tool:'accord_request_handoff', namespace:null,
            arguments:{reason:'New conditions now require a fresh carrier.'}})
        : serverRequest(104, 'owner/work', {threadId:'source-1', turnId:'source-turn-1'}));
      return;
    }
    if (frame.id === 104 || frame.id === 105) queueMicrotask(() => emit({method:'turn/completed',
      params:{threadId:'source-1', turn:{id:'source-turn-1', status:'completed', items:[]}}}));
    if (frame.id === 102 || frame.id === 103) queueMicrotask(() => {
      emit({method:'item/completed', params:{threadId:'source-1', turnId:'source-turn-1',
        item:{type:'dynamicToolCall', id:frame.id === 103 ? 'later-handoff-call' : 'handoff-call', tool:'accord_request_handoff',
          namespace:null, status:'completed', success:true,
          contentItems:frame.result.contentItems}}});
      if (mode.startsWith('fault-source-')) {
        if (mode.endsWith('-before')) invalidateProposalSource();
        return serverRequest(105, 'approval/request', {threadId:'source-1', turnId:'source-turn-1'});
      }
      if (mode === 'handoff-source-queued') return;
      if (mode.startsWith('handoff-source-')) serverRequest(106, 'approval/request', {
        threadId:'unrelated-source', turnId:'other-turn', reason:'not-owned'});
      if (mode === 'handoff-source-context' || mode.startsWith('binding-handoff-source-')) return serverRequest(105, 'item/tool/call', {
        threadId:'source-1', turnId:'source-turn-1', callId:'late-context',
        tool:'accord_inspect_context', namespace:null, arguments:{maxAgeMs:30000}});
      if (['handoff-source-owner', 'handoff-source-owner-failure'].includes(mode)) return serverRequest(105, 'approval/request', {
        threadId:'source-1', turnId:'source-turn-1', reason:'late-owner-decision'});
      if (mode === 'handoff-source-nested') return serverRequest(105, 'item/tool/call', {
        threadId:'source-1', turnId:'source-turn-1', callId:'late-handoff',
        tool:'accord_request_handoff', namespace:null, arguments:{reason:'Must not start a second transfer.'}});
      emit({method:'turn/completed', params:{threadId:'source-1',
        turn:{id:'source-turn-1', status:'completed', items:[]}}});
    });
    if (frame.id === 200) queueMicrotask(() => serverRequest(201, 'item/tool/call', {
      threadId:'target-1', turnId:'target-turn-1', callId:'nested-handoff-call',
      tool:'accord_request_handoff', namespace:null,
      arguments:{reason:'This must wait until adoption.'}}));
    if (frame.id === 201) queueMicrotask(() => {
      emit({method:'item/completed', params:{threadId:'target-1', turnId:'target-turn-1',
        item:{type:'dynamicToolCall', id:'nested-handoff-call', tool:'accord_request_handoff',
          namespace:null, status:'completed', success:false,
          contentItems:frame.result.contentItems}}});
      emit({method:'turn/completed', params:{threadId:'target-1',
        turn:{id:'target-turn-1', status:'completed', items:[]}}});
    });
    if (frame.id === 300) queueMicrotask(() => {
      emit({method:'item/completed', params:{threadId:'target-1', turnId:'target-turn-3',
        item:{type:'dynamicToolCall', id:'second-handoff-call', tool:'accord_request_handoff',
          namespace:null, status:'completed', success:true,
          contentItems:frame.result.contentItems}}});
      emit({method:'turn/completed', params:{threadId:'target-1',
        turn:{id:'target-turn-3', status:'completed', items:[]}}});
    });
    return;
  }
  if (frame.method === 'thread/start') {
    starts.push(frame.params);
    if (!sourceStarted) {
      sourceStarted = true;
      if (mode === 'start-loss') return queueMicrotask(() => output.end());
      if (mode === 'source-ephemeral') return response(frame,
        {thread:{id:'source-1', ephemeral:true}, model:frame.params.model});
      if (mode === 'source-persistence-missing') return response(frame,
        {thread:{id:'source-1'}, model:frame.params.model});
      const answer = () => emit({jsonrpc:'2.0', id:frame.id,
        result:{thread:{id:'source-1', status:{type:'idle'}, ephemeral:false},
          model:frame.params.model}});
      if (mode === 'concurrent') setTimeout(answer, 20); else queueMicrotask(answer);
    } else {
      const id = `target-${++targetCreated}`;
      response(frame, {thread:{id, status:{type:'idle'}, ephemeral:false},
      cwd:frame.params.cwd, model:frame.params.model, approvalPolicy:frame.params.approvalPolicy,
      sandbox:{type:'readOnly'}});
    }
    return;
  }
  if (frame.method === 'turn/start') {
    if (frame.params.threadId === 'source-1') {
      const id = `source-turn-${++sourceTurn}`;
      if (mode === 'malformed-turn') return response(frame, {turn:{status:'inProgress'}});
      response(frame, {turn:{id, status:'inProgress'}});
      queueMicrotask(() => {
        emit({method:'turn/started', params:{threadId:'source-1', turn:{id}}});
        emit({method:'thread/tokenUsage/updated', params:{threadId:'source-1',
          turnId:id, tokenUsage:{modelContextWindow:1000,
            last:{totalTokens:100}}}});
        if (mode === 'concurrent' || mode === 'scope-after-terminal' ||
            mode === 'decline' && sourceTurn > 1) emit({method:'turn/completed', params:{threadId:'source-1',
          turn:{id, status:'completed', items:[]}}});
        else serverRequest(100, 'item/tool/call', {threadId:'source-1',
          turnId:'source-turn-1', callId:'context-call', tool:'accord_inspect_context',
          namespace:null, arguments:{maxAgeMs:30000}});
      });
    } else {
      const id = `target-turn-${++targetTurn}`;
      response(frame, {turn:{id, status:'inProgress'}});
      queueMicrotask(() => {
        if (mode === 'adopt-chain' && frame.params.input?.[0]?.text === 'second source carrier') {
          serverRequest(300, 'item/tool/call', {threadId:frame.params.threadId, turnId:id,
            callId:'second-handoff-call', tool:'accord_request_handoff', namespace:null,
            arguments:{reason:'Continue to the next fresh carrier.'}});
        } else if (mode.startsWith('fault-target-') && targetTurn === 1) {
          if (mode.endsWith('-before')) invalidateProposalSource();
          serverRequest(200, 'approval/request', {threadId:frame.params.threadId, turnId:id});
        } else if ((mode === 'adopt-chain' || mode.startsWith('binding-handoff-target-')) && targetTurn === 1) {
          serverRequest(200, 'item/tool/call', {threadId:frame.params.threadId, turnId:id,
            callId:'target-context-call', tool:'accord_inspect_context', namespace:null,
            arguments:{maxAgeMs:30000}});
        } else emit({method:'turn/completed', params:{threadId:frame.params.threadId,
          turn:{id, status:'completed', items:[]}}});
      });
    }
    return;
  }
  if (frame.method === 'thread/read') return response(frame, {thread:{id:frame.params.threadId,
    status:{type:mode==='adopt-busy' && sourceUnsubscribed>0 && frame.params.threadId==='target-1'?'active':'idle'}, ephemeral:false}});
  if (frame.method === 'thread/unsubscribe') { sourceUnsubscribed++; return response(frame, {status:'unsubscribed'}); }
  if (frame.method === 'turn/interrupt') return response(frame, {});
  throw new Error('unexpected native method: ' + frame.method);
}
let buffered = '';
const input = new Writable({write(chunk, encoding, done) {
  buffered += chunk.toString('utf8');
  let newline;
  while ((newline = buffered.indexOf('\n')) >= 0) {
    const line = buffered.slice(0, newline); buffered = buffered.slice(newline + 1);
    if (line) handle(JSON.parse(line));
  }
  done();
}});
const nativeConnection = createOwnedAppServerConnection({stdin:input, stdout:output,
  connectionId:'fixture-connection', hostVersion:'fixture-host'});
// Public source sessions also accept borrowed mutable connection adapters.
// Keep the actual protocol reader; change only the borrower's binding while
// an asynchronous receive or context reply is in progress.
const connection = mode.startsWith('binding-') || mode.startsWith('fault-') ? {
  ...nativeConnection, transport:{...nativeConnection.transport},
} : nativeConnection;
if (mode.startsWith('fault-')) {
  connection.receiveTurnActivity = async (...args) => {
    const activity = await nativeConnection.receiveTurnActivity(...args);
    if (mode.endsWith('-receive') && activity.type === 'request' &&
        activity.request.id === (mode.startsWith('fault-source-') ? 105 : 200))
      invalidateProposalSource();
    return activity;
  };
}
if (mode.startsWith('binding-')) {
  connection.receiveTurnActivity = async (...args) => {
    const activity = await nativeConnection.receiveTurnActivity(...args);
    if (activity.type === 'request' && activity.request.id === 100) {
      if (mode === 'binding-receive-id') connection.transport.connectionId = 'replacement';
      if (mode === 'binding-receive-version') connection.transport.hostVersion = 'replacement';
      if (mode === 'binding-receive-callback') connection.replyContext = async () => {};
    }
    if (activity.type === 'request' &&
        (mode === 'binding-handoff-source-receive' && activity.request.id === 105 ||
         mode === 'binding-handoff-target-receive' && activity.request.id === 200))
      connection.transport.connectionId = 'replacement';
    return activity;
  };
  connection.replyContext = async (...args) => {
    const reply = await nativeConnection.replyContext(...args);
    if (mode === 'binding-reply-id' ||
        mode === 'binding-handoff-source-reply' && args[0].id === 105 ||
        mode === 'binding-handoff-target-reply' && args[0].id === 200)
      connection.transport.connectionId = 'replacement';
    return reply;
  };
  connection.respondRequest = async (...args) => {
    const reply = await nativeConnection.respondRequest(...args);
    if (mode === 'binding-owner-reply' && args[0].id === 101)
      connection.transport.connectionId = 'replacement';
    return reply;
  };
}
const storedRecorder = openCarrierRecorder({path:databasePath, create:true});
let beginCalls = 0;
const recorder = {...storedRecorder, begin(...args) {
  beginCalls++;
  return storedRecorder.begin(...args);
}, compareAndSet(...args) {
  if (slowRecordMs && args[2].phase === 'writer-transferred')
    Atomics.wait(new Int32Array(new SharedArrayBuffer(4)), 0, 0, slowRecordMs);
  if (slowReleaseMs && args[2].phase === 'source-subscription-released')
    Atomics.wait(new Int32Array(new SharedArrayBuffer(4)), 0, 0, slowReleaseMs);
  return storedRecorder.compareAndSet(...args);
}};
let scopeReads = 0, recordReads = 0, settleCalls = 0;
let adoptionStarted = false, adoptionRecordChanged = false;
const wrappedRecorder = ['scope-active','scope-after-terminal','decline-scope-change',
  'decline-scope-after-send','adopt-old-lease',
  'adopt-missing-tools','adopt-settle-loss','adopt-bad-settle','adopt-session-error',
  'adopt-deadline-before-settle','no-claim-recorder'].includes(mode);
const sessionRecorder = wrappedRecorder ? {
  bindScope:recorder.bindScope, begin:recorder.begin, compareAndSet:recorder.compareAndSet,
  claimScope:recorder.claimScope,
  read(...args) {
    recordReads++;
    const value = recorder.read(...args);
    if (!adoptionStarted || adoptionRecordChanged) return value;
    adoptionRecordChanged = true;
    const changed = JSON.parse(JSON.stringify(value));
    if (mode === 'adopt-old-lease') changed.lease.token = 'stale-lease-token';
    if (mode === 'adopt-missing-tools') delete changed.state.plan.target.dynamicTools;
    return changed;
  },
  settle(...args) {
    settleCalls++;
    const value = recorder.settle(...args);
    if (mode === 'adopt-settle-loss') throw new Error('settle acknowledgement lost');
    if (mode === 'adopt-session-error') throw new CodexSourceSessionError('CALLBACK_FAILURE', 'settle acknowledgement lost');
    if (mode === 'adopt-bad-settle') return {...value, revision:'unknown'};
    return value;
  },
  readScope(scopeRef) {
    scopeReads++;
    const scope = recorder.readScope(scopeRef);
    if (mode === 'scope-active' && scopeReads >= 2)
      return {...scope, activeTransferId:'foreign-transfer'};
    if (mode === 'scope-after-terminal' && scopeReads >= 3)
      return {...scope, writerThreadId:'foreign-writer'};
    if (mode === 'decline-scope-change' && planCalls.length > 0)
      return {...scope, writerThreadId:'foreign-writer'};
    if (mode === 'decline-scope-after-send' && serverResponses.some(frame => frame.id === 102))
      return {...scope, writerThreadId:'foreign-writer'};
    return scope;
  },
} : recorder;
if(mode==='no-claim-recorder')delete sessionRecorder.claimScope;
const planCalls = [], ownerCalls = [], ownerPhases = [], currentCalls = [], verifyCalls = [];
let adoptionVerifyCalls = 0;
const session = createCodexSourceSession({connection, recorder:sessionRecorder, scopeRef:'fixture-scope',
  ownUnscopedRequests:mode === 'proposal-unscoped',
  threadStart:{cwd:'C:/fixture', model:'owner-model', effort:'owner-effort',
    sandbox:'workspace-write', approvalPolicy:'on-request', dynamicTools:[{
      type:'function', name:'owner_tool', description:'owner tool',
      inputSchema:{type:'object', properties:{}, additionalProperties:false}}]},
  planResolver(request, context) {
    planCalls.push({request, context:{...context, signal:undefined}});
    const ordinal = planCalls.length;
    if (mode === 'resolver-null') return null;
    if (mode === 'resolver-throws') throw new Error('current authority cannot be established');
    if ((mode.startsWith('decline') || mode.startsWith('proposal-')) && ordinal === 1) {
      const decision = {decision:'continue-source', reason:'Current work fits this source.',
        sourceRef:'owner-current-task-observation'};
      if (mode === 'decline-invalid') decision.reason = '';
      if (mode === 'decline-extra') decision.target = {cwd:'C:/foreign'};
      return decision;
    }
    const now = Date.now();
    const plan = {transferId:`transfer-${ordinal}`, scopeRef:'fixture-scope', authorityRef:'authority-1',
      stateRef:'state-1', source:{threadId:context.threadId, turnId:context.turnId},
      target:{cwd:'C:/fixture', model:`target-model-${ordinal}`, effort:'target-effort'},
      handoffText:'Retain the fixed authorized task and protected inputs.',
      continuation:{input:'Perform the next bounded step.', sandboxPolicy:{type:'readOnly'}},
      // Protocol/ownership fixtures are not disk-speed benchmarks. Derive the
      // ordinary plan from its run window, reserving recovery and caller time.
      // Deadline regressions opt into a deliberately smaller plan explicitly.
      deadlineMs:handoffWorkMs ? now+handoffWorkMs : context.deadlineMs-8000,
      recoveryDeadlineMs:handoffWorkMs ? now+handoffWorkMs+500 : context.deadlineMs-6000};
    if (mode === 'target-format') plan.target.dynamicTools = targetTools;
    return plan;
  },
  verify(stage, facts) {
    verifyCalls.push(stage);
    if (stage === 'adopt-target') {
      adoptionVerifyCalls++;
      if (mode === 'adopt-deadline-before-settle' && adoptionVerifyCalls === 1)
        Atomics.wait(new Int32Array(new SharedArrayBuffer(4)), 0, 0, 30);
    }
    return {decision:'allow', scopeRef:'fixture-scope', authorityRef:'authority-1',
      stateRef:mode==='adopt-stale-ref' && stage==='adopt-target'?'stale-state':'state-1',
      sourceRef:'fixture:'+stage, sourceRecoveryReady:true,
      targetInitializationSafe:true, quiesced:true, noOtherWriters:true,
      targetSettingsMatch:true, initializationEffectsVerified:true, accepted:true,
      sourceIdle:true, intakeEffectsVerified:true, singleWriter:true, effectsVerified:true,
      adoptionAuthorized:true};
  },
  current(context) {
    currentCalls.push({...context, signal:undefined});
    return {scopeRef:'fixture-scope', authorityRef:'authority-1', stateRef:'state-1',
      writerThreadId:context.sourceThreadId};
  },
  ownerRequest(request, context) {
    ownerCalls.push(request);
    ownerPhases.push(context.phase || 'ordinary');
    if (mode.endsWith('-owner') && mode.startsWith('fault-') &&
        request.id === (mode.startsWith('fault-source-') ? 105 : 200))
      invalidateProposalSource();
    if (mode === 'handoff-source-owner-failure' && request.id === 105)
      throw new Error('current source authority cannot be established');
    if (mode === 'owner-reentrant') return session.run({input:'nested turn', deadlineMs:Date.now()+1000});
    return {result:{decision:'denied-by-owner'}};
  },
});
(async()=>{
  const result = {};
  try {
    if (mode === 'conflict') {
      try {
        createCodexSourceSession({connection, recorder, scopeRef:'other',
          threadStart:{cwd:'C:/fixture',model:'owner-model',
            dynamicTools:[{type:'function',name:'accord_inspect_context'}]},
          planResolver(){},verify(){},current(){},ownerRequest(){}});
      } catch (error) { result.conflict = error.message; }
    } else if (mode === 'concurrent') {
      const first = session.run({input:'one ordinary turn', deadlineMs:Date.now()+3000});
      try { await session.run({input:'must be rejected', deadlineMs:Date.now()+3000}); }
      catch (error) { result.concurrent = error.code; }
      result.first = await first;
      result.secondOrdinary = await session.run({input:'a second serialized turn',
        deadlineMs:Date.now()+3000});
    } else if (mode === 'scope-conflict') {
      recorder.bindScope('fixture-scope', 'foreign-writer');
      try { await session.run({input:'must not create source', deadlineMs:Date.now()+3000}); }
      catch (error) { result.error = {code:error.code, phase:error.phase, state:error.state}; }
    } else if (mode === 'decline') {
      try {
        result.first = await session.run({input:'one ordinary turn', deadlineMs:Date.now()+3000});
        result.secondOrdinary = await session.run({input:'continue without a transfer',
          deadlineMs:Date.now()+3000});
      } catch (error) { result.error = {code:error.code, phase:error.phase, state:error.state}; }
    } else if (mode === 'adopt-chain') {
      result.first = await session.run({input:'one source turn', deadlineMs:Date.now()+20000});
      result.adopted = await session.adoptTarget({deadlineMs:Date.now()+3000});
      result.secondTransfer = await session.run({input:'second source carrier',
        deadlineMs:Date.now()+20000});
      try { await session.run({input:'must wait for second adoption', deadlineMs:Date.now()+1000}); }
      catch (error) { result.second = error.code; }
    } else if (mode.startsWith('adopt-')) {
      result.first = await session.run({input:'one source turn', deadlineMs:Date.now()+20000});
      adoptionStarted = true;
      const adoptionDeadline = mode === 'adopt-deadline-before-settle' ? 10 :
        adoptionPrecondition ? 8000 : 3000;
      try { result.adopted = await session.adoptTarget({deadlineMs:Date.now()+adoptionDeadline}); }
      catch (error) { result.adoptionError = {code:error.code, state:error.state}; }
      if (mode === 'adopt-deadline-before-settle') {
        result.settleCallsAfterDeadline = settleCalls;
        result.statusAfterDeadline = session.snapshot().status;
        result.adopted = await session.adoptTarget({deadlineMs:Date.now()+3000});
      }
      if (['adopt-settle-loss', 'adopt-bad-settle', 'adopt-session-error'].includes(mode)) {
        try { await session.adoptTarget({deadlineMs:Date.now()+1000}); }
        catch (error) { result.retry = error.code; }
      }
    } else {
      try { result.first = await session.run({input:'one source turn',
        turn:{effort:'turn-owner-effort', sandboxPolicy:{type:'workspaceWrite'}},
        deadlineMs:Date.now()+20000}); }
      catch (error) { result.error = {code:error.code, phase:error.phase,
        state:error.state, rpcRequest:error.rpcRequest, nativeRequest:error.nativeRequest}; }
      try { await session.run({input:'must not replay', deadlineMs:Date.now()+1000}); }
      catch (error) { result.second = error.code; }
    }
    result.snapshot = session.snapshot(); result.sent = sent; result.starts = starts;
    result.serverResponses = serverResponses; result.planCalls = planCalls.length;
    result.ownerCalls = ownerCalls.length; result.currentCalls = currentCalls.length;
    result.ownerPhases = ownerPhases;
    result.verifyCalls = verifyCalls; result.recordReads = recordReads;
    result.settleCalls = settleCalls;
    result.beginCalls = beginCalls;
    if (mode.startsWith('decline') || mode.startsWith('resolver-') || mode.startsWith('proposal-') || mode.startsWith('adopt-'))
      result.finalScope = recorder.readScope('fixture-scope');
    if (mode === 'source-ephemeral' || mode === 'source-persistence-missing') {
      try { recorder.readScope('fixture-scope'); result.scopeReadCode = 'present'; }
      catch (error) { result.scopeReadCode = error.code; }
    }
    console.log(JSON.stringify(result));
  } finally { connection.close(); recorder.close(); }
})().catch(error=>{console.error(error);
  const detail=error.cause?.details?.original;
  console.error('recorder failure:',detail?.attemptedPhase,detail?.cause?.code);
  process.exitCode=1});
'''


RESTORE_SCENARIO = r'''
const {performance} = require('node:perf_hooks');
const {openCarrierRecorder} = require(process.argv[2]);
const {createCodexSourceSession,restoreCodexSourceSession,CodexSourceSessionError} = require(process.argv[1]);
const databasePath=process.argv[3], rawMode=process.argv[4];
const slowRecordMs=Number(process.argv[5]||0);
const sourceMode=rawMode.startsWith('source-'), mode=sourceMode?rawMode.slice(7):rawMode;
const until=ms=>Date.now()+ms, mono=()=>performance.now()+5000;
let threadStarts=0, targetTurn=0, proposalUsed=false;
const oldCalls=[];
const oldConnection={transport:{connectionId:'old-connection',hostVersion:'fixture-host',
  async request(method,params){oldCalls.push({method,params:JSON.parse(JSON.stringify(params))});
    if(method==='thread/start'){const id=++threadStarts===1?'source-1':'target-1';return {thread:{id,ephemeral:false,status:{type:'idle'}},model:params.model};}
    if(method==='thread/read')return {thread:{id:params.threadId,ephemeral:false,status:{type:'idle'}}};
    if(method==='turn/start')return {turn:{id:params.threadId==='source-1'?'source-turn':`target-turn-${++targetTurn}`,status:'inProgress'}};
    if(method==='thread/unsubscribe')return {status:'unsubscribed'};
    throw Error('unexpected old request:'+method);},
  async waitTerminal(threadId,turnId){return {method:'turn/completed',params:{threadId,turn:{id:turnId,status:'completed',items:[]}}};}},
  async receiveTurnActivity(threadId,turnId){
    if(threadId==='source-1'&&!proposalUsed&&(!sourceMode||mode==='active')){proposalUsed=true;return {type:'request',request:{connectionId:'old-connection',hostVersion:'fixture-host',id:41,
      method:'item/tool/call',params:{threadId,turnId,callId:'proposal-call',tool:'accord_request_handoff',namespace:null,arguments:{reason:'fixed'}}}};}
    return {type:'terminal',terminal:{method:'turn/completed',params:{threadId,turn:{id:turnId,status:'completed',items:[]}}}};
  },
  async respondRequest(){throw Error('unexpected response')},async replyContext(){throw Error('unexpected context')},
  proposalChannel(request,current){let listener=null;return {subscribe(fn){listener=fn;return()=>{listener=null}},
    async respond(response){listener({connectionId:'old-connection',hostVersion:'fixture-host',method:'item/completed',params:{
      threadId:request.params.threadId,turnId:request.params.turnId,item:{type:'dynamicToolCall',id:request.params.callId,
      tool:request.params.tool,namespace:null,status:'completed',success:true,contentItems:response.result.contentItems}}});
      listener({connectionId:'old-connection',hostVersion:'fixture-host',method:'turn/completed',params:{
        threadId:request.params.threadId,turn:{id:request.params.turnId,status:'completed',items:[]}}});},
    current};}
};
const storedRecorder=openCarrierRecorder({path:databasePath,create:true});
const recorder={...storedRecorder,compareAndSet(...args){
  if(slowRecordMs&&args[2].phase==='writer-transferred')
    Atomics.wait(new Int32Array(new SharedArrayBuffer(4)),0,0,slowRecordMs);
  return storedRecorder.compareAndSet(...args);
}};
const verdict=(stage,refs)=>({decision:'allow',scopeRef:refs.scopeRef||'fixture-scope',authorityRef:refs.authorityRef||'authority-1',
  stateRef:refs.stateRef||'state-1',sourceRef:'fixture:'+stage,sourceRecoveryReady:true,targetInitializationSafe:true,
  quiesced:true,noOtherWriters:true,targetSettingsMatch:true,initializationEffectsVerified:true,accepted:true,sourceIdle:true,
  intakeEffectsVerified:true,singleWriter:true,effectsVerified:true,adoptionAuthorized:true});
const oldSession=createCodexSourceSession({connection:oldConnection,recorder,scopeRef:'fixture-scope',
  threadStart:{cwd:'C:/fixture',model:'fixture-model',sandbox:'read-only',approvalPolicy:'never'},
  planResolver(request,context){return {transferId:'settled-transfer',scopeRef:'fixture-scope',authorityRef:'authority-1',stateRef:'state-1',
    source:{threadId:context.threadId,turnId:context.turnId},target:{cwd:'C:/fixture',model:'fixture-model'},handoffText:'fixed intake',
    continuation:{input:'fixed continuation',sandboxPolicy:{type:'readOnly'}},
    deadlineMs:context.deadlineMs-8000,recoveryDeadlineMs:context.deadlineMs-6000}},
  verify(stage,facts){return verdict(stage,facts.packet?.plan||facts)},
  current(){const scope=recorder.readScope('fixture-scope');return {scopeRef:'fixture-scope',authorityRef:'authority-1',stateRef:'state-1',writerThreadId:scope.writerThreadId}},
  ownerRequest(){return {error:{code:-1,message:'unexpected'}}}});
let resumeCalls=0,claimCalls=0,restoredTurnStarts=0,resumed=false,resumeParamsSeen=null,effects=[],restoreReadParams=[];
function restoreConnection(id){return {transport:{connectionId:id,hostVersion:'fixture-host',
  async request(method,params){
    if(method==='thread/read'){restoreReadParams.push(JSON.parse(JSON.stringify(params)));return {thread:{id:params.threadId,ephemeral:mode==='ephemeral',status:{type:mode==='native-active'?'active':resumed?'idle':'notLoaded'},
      cwd:'C:/restored',model:'restored-model',reasoningEffort:'high'}};}
    if(method==='thread/resume'){resumeCalls++;effects.push('resume');resumeParamsSeen=JSON.parse(JSON.stringify(params));resumed=true;if(mode==='resume-loss'){const e=Error('resume ack lost');e.rpcRequest={connectionId:id,hostVersion:'fixture-host',requestId:'resume-1',method};throw e;}
      return {thread:{id:params.threadId,ephemeral:false,status:{type:'idle'}},cwd:params.cwd,model:params.model,reasoningEffort:params.config?.model_reasoning_effort};}
    if(method==='turn/start'){restoredTurnStarts++;return {turn:{id:'restored-turn',status:'inProgress'}};}
    throw Error('unexpected restore request:'+method);},async waitTerminal(){throw Error('unused')}},
  async receiveTurnActivity(threadId,turnId){return {type:'terminal',terminal:{method:'turn/completed',params:{threadId,turn:{id:turnId,status:'completed',items:[]}}}}},
  async respondRequest(){throw Error('unused')},async replyContext(){throw Error('unused')},proposalChannel(){throw Error('unused')}};}
// Independent fixture evidence supplied to the verifier contract. This unit
// does not claim thread/read exposes native tools or complete history.
const persistedNativeEvidence={checkpointRef:'persisted-checkpoint',tools:['accord_request_handoff','accord_inspect_context']};
function restoreVerifier(stage,facts){
  if(stage==='restore-prepare')return {decision:'allow',scopeRef:facts.scopeRef,authorityRef:facts.authorityRef,stateRef:facts.stateRef,
    sourceRef:'restore:prepare',pauseStateVerified:mode!=='pause-unverified',priorControllerQuiesced:true,pendingEffectsReconciled:true,
    restorationAuthorized:true,singleWriter:true,resumeInitializationSafe:true,
    sourceOriginVerified:mode!=='origin-unverified',sourceOriginEvidenceRef:mode==='origin-ref-missing'?'':'fixture:original-start-and-scope-ack-and-native-tools'};
  if(stage==='restore-resumed'){const toolsOk=persistedNativeEvidence.tools.includes('accord_request_handoff')&&persistedNativeEvidence.tools.includes('accord_inspect_context');
    if(mode==='verifier-session-error')throw new CodexSourceSessionError('CALLBACK_FAILURE','restored effects unverified');
    if(mode==='scope-changed'){effects.push('verifier-claim');recorder.claimScope('fixture-scope',facts.claimedScope)}
    return {decision:'allow',scopeRef:facts.scopeRef,authorityRef:facts.authorityRef,stateRef:facts.stateRef,
    sourceRef:'restore:resumed',nativeToolEvidenceRef:toolsOk?'fixture-persisted-native-metadata:tools':'',continuityToolsRestored:mode!=='tools-denied'&&toolsOk,
    targetSettingsMatch:facts.resumeParams.cwd==='C:/restored'&&facts.resumeParams.config.model_reasoning_effort==='high',
    historyRetained:persistedNativeEvidence.checkpointRef==='persisted-checkpoint',singleWriter:true,effectsVerified:true};}
  throw Error('unexpected restore verifier:'+stage);
}
function options(connection,rec=recorder){return {connection,recorder:rec,scopeRef:'fixture-scope',verify:restoreVerifier,
  planResolver(){throw Error('unused plan')},current(){throw Error('unused current')},ownerRequest(){return {error:{code:-1,message:'unused'}}}};}
const restoreArgs=(basis)=>({...sourceMode?{source:{threadId:mode==='wrong-id'?'foreign':'source-1',
  connectionId:mode==='same-connection'?'new-connection':'old-connection',authorityRef:'authority-1',stateRef:'state-1'}}:
  {transferId:'settled-transfer'},expectedScope:basis,deadlineMs:until(5000),
  resume:{cwd:'C:/restored',sandbox:'read-only',approvalPolicy:'never',model:'restored-model',modelProvider:'fixture',effort:'high'}});
(async()=>{let out={};try{
  // Build the settled source before exercising restore guards or lost receipts.
  const transfer=await oldSession.run({input:'propose',deadlineMs:until(20000)});
  const preAdoptScope=oldSession.snapshot().scope;
  if(mode==='active'){
    try{await restoreCodexSourceSession(options(restoreConnection('new-active')),restoreArgs(preAdoptScope))}catch(e){out.error={code:e.code,state:e.state};out.failedSession=e.session.snapshot()}
  }else{
    const adopted=sourceMode?null:await oldSession.adoptTarget({deadlineMs:until(5000)});
    const basis=sourceMode?oldSession.snapshot().scope:adopted.scope;
    out.original=transfer;
    let restoreRecorder=recorder;
    if(mode==='claim-loss')restoreRecorder={bindScope:recorder.bindScope,readScope:recorder.readScope,begin:recorder.begin,
      compareAndSet:recorder.compareAndSet,read:recorder.read,settle:recorder.settle,close:recorder.close,
      claimScope(...args){claimCalls++;effects.push('claim');const value=recorder.claimScope(...args);throw Error('claim ack lost')}};
    else restoreRecorder={bindScope:recorder.bindScope,readScope:recorder.readScope,begin:recorder.begin,
      compareAndSet:recorder.compareAndSet,read:recorder.read,settle:recorder.settle,close:recorder.close,
      claimScope(...args){claimCalls++;effects.push('claim');return recorder.claimScope(...args)}};
    let requestedRestore=restoreArgs(basis);
    if(mode==='ambiguous-origin')requestedRestore.transferId='settled-transfer';
    if(mode==='invalid-restore')delete requestedRestore.resume;
    if(mode==='expired-restore')requestedRestore.deadlineMs=Date.now()-1;
    try{
      const restored=await restoreCodexSourceSession(options(restoreConnection('new-connection'),restoreRecorder),requestedRestore);
      out.restored=restored.snapshot();out.turn=await restored.run({input:'ordinary restored turn',deadlineMs:until(5000)});
    }catch(e){out.error={code:e.code||e.name,rpcRequest:e.rpcRequest,state:e.state};out.failedSession=e.session.snapshot();
      try{await e.session.run({input:'must stay failed',deadlineMs:until(1000)})}catch(locked){out.locked=locked.code}}
    if(mode==='success'){
      const before=oldCalls.filter(x=>x.method==='turn/start').length;
      try{await oldSession.run({input:'old writer must fail',deadlineMs:until(1000)})}catch(e){out.oldWriter=e.code}
      out.oldWriterExtraTurns=oldCalls.filter(x=>x.method==='turn/start').length-before;
    }
    if(mode==='resume-loss'||mode==='claim-loss'){
      try{await restoreCodexSourceSession(options(restoreConnection('fresh-retry')),restoreArgs(basis))}catch(e){out.retry=e.code;out.retryState=e.session.snapshot()}
    }
    out.basis=basis;out.currentScope=recorder.readScope('fixture-scope');out.adopted=adopted;
  }
  out.resumeCalls=resumeCalls;out.claimCalls=claimCalls;out.restoredTurnStarts=restoredTurnStarts;out.resumeParamsSeen=resumeParamsSeen;out.restoreReadParams=restoreReadParams;out.effects=effects;out.oldCalls=oldCalls;
}finally{recorder.close()}console.log(JSON.stringify(out))})().catch(e=>{console.error(e);
  const detail=e.cause?.details?.original;
  console.error('recorder failure:',detail?.attemptedPhase,detail?.cause?.code);
  process.exitCode=1});
'''


class CodexSourceSessionTests(unittest.TestCase):
    def test_proposal_fault_stops_source_and_target_request_effects_at_live_boundaries(self):
        for phase, request_id in (('source', 105), ('target', 200)):
            for point in ('before', 'receive', 'owner'):
                with self.subTest(phase=phase, point=point):
                    result = self.run_case(f'fault-{phase}-{point}')
                    self.assertEqual(result['snapshot']['status'], 'failed')
                    self.assertEqual(result['second'], 'SESSION_FAILED')
                    self.assertNotIn(request_id, {frame['id'] for frame in result['serverResponses']})
                    self.assertEqual(result['ownerCalls'], 2 if point == 'owner' else 1)
                    self.assertEqual(len(result['starts']), 1 if phase == 'source' else 2)
                    self.assertEqual(result['snapshot']['failure']['cause']['code'],
                                     'PROPOSAL_SOURCE_CHANGED')
                    if point != 'before':
                        self.assertEqual(result['snapshot']['pendingRequest']['id'], request_id)
                    self.assertFalse(any(frame.get('method') == 'thread/unsubscribe'
                                         for frame in result['sent']))

    def test_owner_request_rechecks_writer_token_and_unknown_scope_at_both_boundaries(self):
        for mode in ["stable"] + [f"{point}-{loss}" for point in ("before", "during")
                                  for loss in ("writer", "token", "unknown")]:
            with self.subTest(mode=mode):
                run = subprocess.run([shutil.which("node"), "-e", SCOPE_REQUEST_SCENARIO,
                    str(MODULE), mode], capture_output=True, text=True, encoding="utf-8", timeout=5)
                self.assertEqual(run.returncode, 0, run.stderr)
                result = json.loads(run.stdout)
                self.assertEqual(result["ownerCalls"], 0 if mode.startswith("before") else 1)
                self.assertEqual(result["replies"], 1 if mode == "stable" else 0)
                self.assertEqual(result["code"], None if mode == "stable" else
                    "SOURCE_SCOPE_UNKNOWN" if mode.endswith("unknown") else "SOURCE_SCOPE_CHANGED")
                if mode != "stable":
                    self.assertEqual(result["retry"], "SESSION_FAILED")
                    self.assertEqual(result["snapshot"]["status"], "failed")
                    self.assertEqual(result["snapshot"]["pendingRequest"]["id"], 1)

    def run_case(self, mode, *, slow_record_ms=0, slow_release_ms=0,
                 handoff_work_ms=0, target_tools=None):
        with tempfile.TemporaryDirectory() as temp:
            database = Path(temp) / "carrier.sqlite"
            command = [shutil.which("node"), "-e", NODE_SCENARIO,
                       str(ROOT / "runtime" / "codex-connection.cjs"),
                       str(ROOT / "runtime" / "carrier-recorder.cjs"),
                       str(MODULE), mode, str(database), str(slow_record_ms),
                       str(slow_release_ms), str(handoff_work_ms), json.dumps(target_tools)]
            completed = subprocess.run(command, capture_output=True, text=True,
                                       encoding="utf-8", timeout=50 if mode == "adopt-chain" else 30)
            self.assertEqual(completed.returncode, 0, completed.stderr)
            return json.loads(completed.stdout)

    def restore_case(self, mode, *, slow_record_ms=0):
        with tempfile.TemporaryDirectory() as temp:
            database = Path(temp) / "restore.sqlite"
            completed = subprocess.run([shutil.which("node"), "-e", RESTORE_SCENARIO,
                str(MODULE), str(ROOT / "runtime" / "carrier-recorder.cjs"),
                str(database), mode, str(slow_record_ms)], capture_output=True, text=True,
                encoding="utf-8", timeout=30)
            self.assertEqual(completed.returncode, 0, completed.stderr)
            return json.loads(completed.stdout)

    def test_real_connection_carrier_and_recorder_complete_one_fresh_transfer(self):
        result = self.run_case("handoff")
        self.assertNotIn("error", result)
        self.assertEqual(result["first"]["status"], "transferred")
        self.assertEqual(result["first"]["target"], {
            "threadId": "target-1", "ownedWriter": True,
            "automaticHandoffToolRegistered": True})
        self.assertFalse(result["first"]["sourceWritable"])
        self.assertEqual(result["second"], "SOURCE_TRANSFERRED")
        self.assertEqual(result["snapshot"]["status"], "transferred")
        self.assertEqual(result["first"]["record"]["state"]["writerThreadId"], "target-1")
        self.assertEqual(result["first"]["record"]["state"]["phase"],
                         "source-subscription-released")
        self.assertEqual(result["planCalls"], 1)
        self.assertEqual(result["ownerCalls"], 1)
        self.assertEqual(result["currentCalls"], 1)
        self.assertEqual(result["verifyCalls"], ["prepare", "quiesced", "target-created",
                                                 "accepted", "continue", "continued", "release"])
        source_start = result["starts"][0]
        self.assertIs(source_start["ephemeral"], False)
        self.assertEqual((source_start["model"], source_start["effort"],
                          source_start["sandbox"], source_start["approvalPolicy"]),
                         ("owner-model", "owner-effort", "workspace-write", "on-request"))
        self.assertEqual([tool["name"] for tool in source_start["dynamicTools"]],
                         ["owner_tool", "accord_request_handoff", "accord_inspect_context"])
        target_start = result["starts"][1]
        self.assertEqual([tool["name"] for tool in target_start["dynamicTools"]],
                         ["accord_request_handoff", "accord_inspect_context"])
        source_turn = next(frame for frame in result["sent"]
                           if frame.get("method") == "turn/start"
                           and frame["params"]["threadId"] == "source-1")
        self.assertEqual(source_turn["params"]["effort"], "turn-owner-effort")
        self.assertEqual(source_turn["params"]["sandboxPolicy"], {"type": "workspaceWrite"})
        replies = {frame["id"]: frame for frame in result["serverResponses"]}
        self.assertTrue(replies[100]["result"]["success"])
        self.assertEqual(replies[101]["result"], {"decision": "denied-by-owner"})
        self.assertTrue(replies[102]["result"]["success"])
        methods = [frame["method"] for frame in result["sent"] if "method" in frame]
        self.assertEqual(methods.count("thread/start"), 2)
        self.assertEqual(methods.count("thread/unsubscribe"), 1)
        self.assertNotIn("thread/archive", methods)
        self.assertNotIn("thread/delete", methods)

    def test_handoff_pumps_queued_and_late_source_requests_before_target_creation(self):
        for mode in ('handoff-source-queued', 'handoff-source-context', 'handoff-source-owner',
                     'handoff-source-nested'):
            with self.subTest(mode=mode):
                result = self.run_case(mode)
                self.assertNotIn('error', result)
                self.assertEqual(result['first']['status'], 'transferred')
                replies = {frame['id']: frame for frame in result['serverResponses']}
                if mode == 'handoff-source-owner':
                    self.assertEqual(replies[105]['result'], {'decision': 'denied-by-owner'})
                    self.assertEqual(result['ownerCalls'], 2)
                    self.assertEqual(result['ownerPhases'], ['ordinary', 'handoff-source'])
                elif mode == 'handoff-source-nested':
                    self.assertFalse(replies[105]['result']['success'])
                    self.assertEqual(json.loads(replies[105]['result']['contentItems'][0]['text'])['code'],
                                     'TRANSFER_IN_PROGRESS')
                    self.assertEqual(result['planCalls'], 1)
                else:
                    self.assertTrue(replies[105]['result']['success'])
                    self.assertEqual(result['ownerCalls'], 1)
                reply_index = next(i for i, frame in enumerate(result['sent']) if frame.get('id') == 105)
                starts = [i for i, frame in enumerate(result['sent']) if frame.get('method') == 'thread/start']
                self.assertEqual(len(starts), 2)
                self.assertLess(reply_index, starts[1])
                self.assertEqual(result['second'], 'SOURCE_TRANSFERRED')
                self.assertNotIn(106, replies)

    def test_queued_source_pump_allows_slow_durable_release_within_run_budget(self):
        result = self.run_case('handoff-source-queued', slow_release_ms=4300)
        self.assertNotIn('error', result.keys())
        self.assertEqual(result['first']['status'], 'transferred')
        replies = [frame['id'] for frame in result['serverResponses']]
        self.assertEqual(replies.count(105), 1)
        methods = [frame['method'] for frame in result['sent'] if 'method' in frame]
        self.assertEqual(methods.count('thread/start'), 2)
        self.assertEqual(methods.count('thread/unsubscribe'), 1)
        self.assertEqual(result['second'], 'SOURCE_TRANSFERRED')

    def test_explicit_release_deadline_still_locks_without_replaying_unsubscribe(self):
        result = self.run_case('handoff-source-queued', slow_release_ms=4300,
                               handoff_work_ms=4000)
        self.assertEqual(result['error']['code'], 'SERVER_REQUEST_FAILED')
        cause = result['error']['state']['failure']['cause']
        self.assertEqual(cause['code'], 'RECORDER_COMMIT_UNKNOWN')
        self.assertEqual(cause['stage'], 'release')
        self.assertTrue(cause['state']['targetTurnTerminal'])
        self.assertEqual(sum(frame.get('method') == 'thread/unsubscribe'
                             for frame in result['sent']), 1)
        self.assertEqual(result['second'], 'SESSION_FAILED')

    def test_source_pump_failure_retains_exact_request_without_target_or_replay(self):
        for mode, pending in (('handoff-source-send-loss', 102), ('handoff-source-owner-failure', 105)):
            with self.subTest(mode=mode):
                result = self.run_case(mode)
                self.assertEqual(result['snapshot']['status'], 'failed')
                self.assertEqual(result['snapshot']['pendingRequest']['id'], pending)
                self.assertEqual(len(result['starts']), 1)
                self.assertEqual(result['second'], 'SESSION_FAILED')
                self.assertNotIn(105, {frame['id'] for frame in result['serverResponses']})

    def test_declined_handoff_finishes_work_and_keeps_the_same_source_usable(self):
        result = self.run_case("decline")
        self.assertNotIn("error", result)
        self.assertEqual(result["first"]["status"], "completed")
        self.assertEqual(result["secondOrdinary"]["sourceThreadId"], "source-1")
        self.assertEqual(result["snapshot"]["status"], "ready")
        self.assertEqual(result["snapshot"]["transferCount"], 0)
        self.assertEqual(result["snapshot"]["transfers"], [])
        self.assertEqual(result["ownerCalls"], 2)  # ordinary work after the refusal
        self.assertEqual(result["verifyCalls"], [])
        self.assertEqual(result["finalScope"]["writerThreadId"], "source-1")
        self.assertIsNone(result["finalScope"]["activeTransferId"])
        replies = [frame for frame in result["serverResponses"] if frame["id"] == 102]
        self.assertEqual(len(replies), 1)
        self.assertFalse(replies[0]["result"]["success"])
        reply = json.loads(replies[0]["result"]["contentItems"][0]["text"])
        self.assertFalse(reply["accepted"])
        self.assertEqual(reply["decision"], "continue-source")
        self.assertEqual(reply["sourceRef"], "owner-current-task-observation")
        methods = [frame["method"] for frame in result["sent"] if "method" in frame]
        self.assertEqual(methods.count("thread/start"), 1)
        self.assertNotIn("turn/interrupt", methods)
        self.assertNotIn("thread/unsubscribe", methods)
        self.assertEqual(result["settleCalls"], 0)

    def test_decline_does_not_consume_a_later_valid_handoff(self):
        result = self.run_case("decline-then-transfer")
        self.assertNotIn("error", result)
        self.assertEqual(result["first"]["status"], "transferred")
        self.assertEqual(result["planCalls"], 2)
        self.assertEqual(result["snapshot"]["transferCount"], 1)
        self.assertEqual(len(result["snapshot"]["transfers"]), 1)
        self.assertEqual(result["second"], "SOURCE_TRANSFERRED")
        self.assertEqual(result["finalScope"]["writerThreadId"], "target-1")
        self.assertEqual(len(result["starts"]), 2)

    def test_decline_does_not_hide_invalid_decisions_or_unknown_effects(self):
        for mode in ("decline-invalid", "decline-extra", "resolver-null", "resolver-throws",
                     "decline-scope-change", "decline-send-loss"):
            with self.subTest(mode=mode):
                result = self.run_case(mode)
                expected = "SOURCE_SCOPE_CHANGED" if mode == "decline-scope-change" else "SERVER_REQUEST_FAILED"
                self.assertEqual(result["error"]["code"], expected)
                self.assertEqual(result["second"], "SESSION_FAILED")
                self.assertEqual(result["snapshot"]["pendingRequest"]["id"], 102)
                self.assertFalse(any(frame["id"] == 102 for frame in result["serverResponses"]))
                self.assertEqual(result["snapshot"]["transferCount"], 0)
                self.assertEqual(len(result["starts"]), 1)
                self.assertEqual(result["verifyCalls"], [])
                self.assertIsNone(result["finalScope"]["activeTransferId"])
                replies = [frame for frame in result["serverResponses"] if frame["id"] == 102]
                self.assertEqual(len(replies), 1 if mode == "decline-send-loss" else 0)

    def test_decline_validates_proposal_identity_before_calling_the_owner(self):
        for mode in ("proposal-no-turn", "proposal-unscoped", "proposal-no-call", "proposal-bad-args"):
            with self.subTest(mode=mode):
                result = self.run_case(mode)
                self.assertEqual(result.get("error", {}).get("code"), "SERVER_REQUEST_FAILED")
                self.assertEqual(result["planCalls"], 0)
                self.assertEqual(result["second"], "SESSION_FAILED")
                self.assertFalse(any(frame["id"] == 102 for frame in result["serverResponses"]))
                self.assertEqual(len(result["starts"]), 1)

    def test_decline_rechecks_ownership_before_processing_following_work(self):
        result = self.run_case("decline-scope-after-send")
        self.assertEqual(result["error"]["code"], "SOURCE_SCOPE_CHANGED")
        self.assertEqual(result["error"]["phase"], "source-scope-after-decline")
        self.assertEqual(result["ownerCalls"], 1)
        self.assertEqual(result["second"], "SESSION_FAILED")
        self.assertEqual(len([frame for frame in result["serverResponses"] if frame["id"] == 102]), 1)

    def test_changed_borrowed_binding_rejects_received_context_without_reply(self):
        for mode in ("binding-receive-id", "binding-receive-version",
                     "binding-receive-callback"):
            with self.subTest(mode=mode):
                result = self.run_case(mode)
                self.assertEqual(result["serverResponses"], [])
                self.assertEqual(result["error"]["code"], "TURN_ACTIVITY_FAILED")
                self.assertEqual(result["error"]["nativeRequest"]["id"], 100)
                self.assertEqual(result["snapshot"]["pendingRequest"]["id"], 100)
                self.assertEqual(result["snapshot"]["status"], "failed")
                self.assertEqual(result["ownerCalls"], 0)
                self.assertEqual(result["planCalls"], 0)
                self.assertEqual(result["second"], "SESSION_FAILED")
                self.assertEqual(len(result["starts"]), 1)

    def test_binding_change_during_context_reply_retains_request_without_replay(self):
        result = self.run_case("binding-reply-id")
        self.assertEqual(result["error"]["nativeRequest"]["id"], 100)
        self.assertEqual(result["error"]["code"], "SERVER_REQUEST_FAILED")
        self.assertEqual(result["snapshot"]["pendingRequest"]["id"], 100)
        self.assertEqual(result["snapshot"]["status"], "failed")
        self.assertEqual([frame["id"] for frame in result["serverResponses"]], [100])
        self.assertEqual(result["ownerCalls"], 0)
        self.assertEqual(result["planCalls"], 0)
        self.assertEqual(result["second"], "SESSION_FAILED")
        self.assertEqual(len(result["starts"]), 1)

    def test_handoff_binding_changes_retain_the_actual_source_or_target_request(self):
        for side, request_id, starts in (("source", 105, 1), ("target", 200, 2)):
            for point, replies in (("receive", 0), ("reply", 1)):
                with self.subTest(side=side, point=point):
                    result = self.run_case(f"binding-handoff-{side}-{point}")
                    self.assertEqual(result["error"]["nativeRequest"]["id"], request_id)
                    self.assertEqual(result["snapshot"]["pendingRequest"]["id"], request_id)
                    self.assertEqual(result["snapshot"]["status"], "failed")
                    self.assertEqual(result["second"], "SESSION_FAILED")
                    self.assertEqual(len(result["starts"]), starts)
                    self.assertEqual(len([r for r in result["serverResponses"]
                                          if r["id"] == request_id]), replies)
                    self.assertFalse(any(r["id"] == 201 for r in result["serverResponses"]))
                    self.assertFalse(any(r.get("method") == "thread/unsubscribe"
                                         for r in result["sent"]))

    def test_binding_change_after_owner_reply_preserves_that_request_once(self):
        result = self.run_case("binding-owner-reply")
        self.assertEqual(result["error"]["nativeRequest"]["id"], 101)
        self.assertEqual(result["snapshot"]["pendingRequest"]["id"], 101)
        self.assertEqual([r["id"] for r in result["serverResponses"]], [100, 101])
        self.assertEqual(result["second"], "SESSION_FAILED")
        self.assertEqual(result["planCalls"], 0)
        self.assertEqual(len(result["starts"]), 1)

    def test_source_start_ack_loss_is_not_retried_and_locks_the_session(self):
        result = self.run_case("start-loss")
        self.assertEqual(result["error"]["code"], "SOURCE_START_UNKNOWN")
        self.assertEqual(result["error"]["phase"], "source-start-unknown")
        self.assertEqual(result["error"]["rpcRequest"]["method"], "thread/start")
        self.assertEqual(result["error"]["state"]["failure"]["cause"]["rpcRequest"],
                         result["error"]["rpcRequest"])
        self.assertEqual(result["second"], "SESSION_FAILED")
        self.assertEqual(sum(frame.get("method") == "thread/start" for frame in result["sent"]), 1)

    def test_unconfirmed_source_persistence_preserves_identity_without_dispatching_work(self):
        for mode in ("source-ephemeral", "source-persistence-missing"):
            with self.subTest(mode=mode):
                result = self.run_case(mode)
                self.assertTrue("error" in result, "Unconfirmed persistence must hold source dispatch")
                self.assertEqual(result["error"]["code"], "SOURCE_PERSISTENCE_UNVERIFIED")
                state = result["error"]["state"]
                self.assertEqual(state["sourceThreadId"], "source-1")
                self.assertEqual(state["lastSafeReceipt"]["thread"]["id"], "source-1")
                self.assertNotIn("scope", state)
                self.assertEqual(result["scopeReadCode"], "SCOPE_NOT_FOUND")
                self.assertEqual(result["second"], "SESSION_FAILED")
                self.assertEqual(sum(frame.get("method") == "thread/start" for frame in result["sent"]), 1)
                self.assertFalse(any(frame.get("method") == "turn/start" for frame in result["sent"]))

    def test_concurrent_run_is_rejected_without_poisoning_the_active_turn(self):
        result = self.run_case("concurrent")
        self.assertEqual(result["concurrent"], "RUN_IN_PROGRESS")
        self.assertEqual(result["first"]["status"], "completed")
        self.assertEqual(result["secondOrdinary"]["status"], "completed")
        self.assertTrue(result["first"]["sourceWritable"])
        self.assertEqual(result["snapshot"]["status"], "ready")
        self.assertEqual(sum(frame.get("method") == "thread/start" for frame in result["sent"]), 1)
        self.assertEqual(sum(frame.get("method") == "turn/start" for frame in result["sent"]), 2)

    def test_existing_scope_writer_blocks_source_creation(self):
        result = self.run_case("scope-conflict")
        self.assertEqual(result["error"]["code"], "WRITER_CONFLICT")
        self.assertEqual(result["sent"], [])
        self.assertEqual(result["snapshot"]["status"], "failed")

    def test_ordinary_session_does_not_require_unused_claim_capability(self):
        result = self.run_case("no-claim-recorder")
        self.assertEqual(result["first"]["status"], "transferred")
        self.assertEqual(result["second"], "SOURCE_TRANSFERRED")

    def test_active_or_changed_scope_blocks_turn_or_writable_claim(self):
        before = self.run_case("scope-active")
        self.assertEqual(before["error"]["code"], "SOURCE_SCOPE_CHANGED")
        self.assertEqual(sum(frame.get("method") == "turn/start" for frame in before["sent"]), 0)
        after = self.run_case("scope-after-terminal")
        self.assertEqual(after["error"]["code"], "SOURCE_SCOPE_CHANGED")
        self.assertEqual(sum(frame.get("method") == "turn/start" for frame in after["sent"]), 1)
        self.assertEqual(after["snapshot"]["status"], "failed")
        self.assertEqual(after["snapshot"]["lastSafeReceipt"]["method"], "turn/completed")
        self.assertEqual(after["snapshot"]["lastSafeReceipt"]["params"]["turn"]["status"], "completed")

    def test_malformed_turn_ack_is_retained_and_never_retried(self):
        result = self.run_case("malformed-turn")
        self.assertEqual(result["error"]["code"], "TURN_START_UNKNOWN")
        self.assertEqual(result["error"]["state"]["lastSafeReceipt"],
                         {"turn": {"status": "inProgress"}})
        self.assertEqual(result["second"], "SESSION_FAILED")
        self.assertEqual(sum(frame.get("method") == "turn/start" for frame in result["sent"]), 1)

    def test_reserved_dynamic_tool_conflict_is_rejected_before_native_work(self):
        result = self.run_case("conflict")
        self.assertIn("dynamic tool identity conflict", result["conflict"])
        self.assertEqual(result["sent"], [])

    @staticmethod
    def incompatible_dynamic_tools():
        tool = {"type": "function", "name": "owner_tool", "description": "owner",
                "inputSchema": {"type": "object", "properties": {}}}
        return {
            "legacy": [{key: value for key, value in tool.items() if key != "type"}],
            "wrong-type": [{**tool, "type": "unknown"}],
            "mixed": [tool, {**tool, "name": "legacy_tool", "type": None}],
            "legacy-namespace": [{**tool, "namespace": "owner"}],
            "namespace-container": [{"type": "namespace", "name": "owner",
                                     "description": "owner", "tools": [tool]}],
            "reserved-namespace": [{**tool, "name": "accord_inspect_context",
                                    "namespace": "owner"}],
        }

    def test_source_dynamic_tool_format_is_rejected_before_creation_or_scope_binding(self):
        for name, tools in self.incompatible_dynamic_tools().items():
            with self.subTest(name=name):
                run = subprocess.run([shutil.which("node"), "-e", SOURCE_TOOL_FORMAT_SCENARIO,
                    str(MODULE), json.dumps(tools)], capture_output=True, text=True,
                    encoding="utf-8", timeout=5)
                self.assertEqual(run.returncode, 0, run.stderr)
                result = json.loads(run.stdout)
                self.assertEqual(result["requests"], [])
                self.assertEqual(result["scopeWrites"], 0)
                self.assertEqual(result["error"]["name"], "TypeError")
                self.assertIn("threadStart.dynamicTools", result["error"]["message"])
                self.assertTrue(result["inputUnchanged"])

    def test_target_dynamic_tool_format_is_rejected_before_transfer_effects(self):
        for name, tools in self.incompatible_dynamic_tools().items():
            with self.subTest(name=name):
                result = self.run_case("target-format", target_tools=tools)
                self.assertEqual(len(result["starts"]), 1)
                self.assertEqual(result["beginCalls"], 0)
                self.assertEqual(result["planCalls"], 1)
                self.assertNotIn("first", result)
                self.assertEqual(result["snapshot"]["status"], "failed")
                self.assertEqual(result["snapshot"]["pendingRequest"]["id"], 102)
                self.assertFalse(any(frame.get("method") in ("thread/resume", "thread/fork",
                    "thread/unsubscribe") for frame in result["sent"]))

    def test_canonical_dynamic_tools_are_forwarded_without_mutation(self):
        tool = {"type": "function", "name": "owner_tool", "description": "owner",
                "inputSchema": {"type": "object", "properties": {"text": {"type": "string"}}},
                "deferLoading": True, "namespace": None}
        run = subprocess.run([shutil.which("node"), "-e", SOURCE_TOOL_FORMAT_SCENARIO,
            str(MODULE), json.dumps([tool])], capture_output=True, text=True,
            encoding="utf-8", timeout=5)
        self.assertEqual(run.returncode, 0, run.stderr)
        source = json.loads(run.stdout)
        self.assertIsNone(source["error"])
        self.assertTrue(source["inputUnchanged"])
        self.assertEqual(source["requests"][0]["params"]["dynamicTools"][0], tool)
        target = self.run_case("target-format", target_tools=[tool])
        self.assertNotIn("error", target)
        self.assertEqual(target["starts"][1]["dynamicTools"][0], tool)

    def test_same_controller_adopts_target_then_completes_a_second_real_transfer(self):
        result = self.run_case("adopt-chain")
        self.assertEqual(result["first"]["target"]["threadId"], "target-1")
        self.assertTrue(result["first"]["target"]["automaticHandoffToolRegistered"])
        self.assertEqual(result["adopted"]["status"], "adopted")
        self.assertEqual(result["adopted"]["sourceThreadId"], "target-1")
        self.assertEqual(result["secondTransfer"]["target"]["threadId"], "target-2")
        self.assertTrue(result["secondTransfer"]["target"]["automaticHandoffToolRegistered"])
        self.assertEqual(result["second"], "SOURCE_TRANSFERRED")
        self.assertEqual(result["planCalls"], 2)
        self.assertEqual(result["currentCalls"], 2)
        self.assertEqual(len(result["starts"]), 3)
        self.assertEqual([item["settled"] for item in result["snapshot"]["transfers"]],
                         [True, False])
        self.assertEqual(result["snapshot"]["sourceThreadId"], "target-1")
        self.assertEqual(result["snapshot"]["targetThreadId"], "target-2")
        replies = {frame["id"]: frame for frame in result["serverResponses"]}
        self.assertTrue(replies[200]["result"]["success"])
        nested = json.loads(replies[201]["result"]["contentItems"][0]["text"])
        self.assertFalse(replies[201]["result"]["success"])
        self.assertEqual(nested["code"], "TRANSFER_IN_PROGRESS")
        self.assertTrue(replies[300]["result"]["success"])
        self.assertEqual([tool["name"] for tool in result["starts"][2]["dynamicTools"]],
                         ["accord_request_handoff", "accord_inspect_context"])

    def test_adoption_preconditions_leave_the_transferred_target_read_only(self):
        cases = {
            "adopt-old-lease": "TARGET_RECORD_STALE",
            "adopt-stale-ref": "TARGET_ADOPTION_DENIED",
            "adopt-busy": "TARGET_NOT_ADOPTABLE",
            "adopt-missing-tools": "TARGET_CONTINUITY_TOOLS_UNAVAILABLE",
        }
        for mode, code in cases.items():
            with self.subTest(mode=mode):
                result = self.run_case(mode)
                self.assertEqual(result["first"]["status"], "transferred")
                self.assertEqual(result["adoptionError"]["code"], code)
                self.assertEqual(result["snapshot"]["status"], "transferred")
                self.assertEqual(result["settleCalls"], 0)
                self.assertEqual(result["snapshot"]["sourceThreadId"], "source-1")
                self.assertEqual(result["snapshot"]["targetThreadId"], "target-1")

    def test_adoption_guard_runs_after_slow_completed_handoff(self):
        # A slow real SQLite transition must not turn this guard check into a
        # handoff-timeout test. Dedicated deadline tests retain their short clocks.
        result = self.run_case("adopt-old-lease", slow_record_ms=4200)
        self.assertEqual(result["first"]["status"], "transferred")
        self.assertEqual(result["adoptionError"]["code"], "TARGET_RECORD_STALE")
        self.assertEqual(result["snapshot"]["status"], "transferred")
        self.assertEqual(result["settleCalls"], 0)

    def test_unknown_or_malformed_settle_locks_without_replay(self):
        for mode in ("adopt-settle-loss", "adopt-bad-settle"):
            with self.subTest(mode=mode):
                result = self.run_case(mode)
                self.assertEqual(result["adoptionError"]["code"], "TARGET_SETTLE_UNKNOWN")
                self.assertEqual(result["snapshot"]["status"], "failed")
                self.assertEqual(result["retry"], "SESSION_FAILED")
                self.assertEqual(result["settleCalls"], 1)
                adoption = result["adoptionError"]["state"]["adoption"]
                self.assertIn("targetRead", adoption)
                self.assertTrue(adoption["verdict"]["adoptionAuthorized"])
                if mode == "adopt-bad-settle":
                    self.assertIn("settleReceipt", adoption)
                else:
                    self.assertNotIn("settleReceipt", adoption)

    def test_deadline_before_settle_invocation_remains_retryable(self):
        result = self.run_case("adopt-deadline-before-settle")
        self.assertEqual(result["adoptionError"]["code"], "TARGET_ADOPTION_FAILED")
        self.assertEqual(result["settleCallsAfterDeadline"], 0)
        self.assertEqual(result["statusAfterDeadline"], "transferred")
        self.assertEqual(result["adopted"]["status"], "adopted")
        self.assertEqual(result["settleCalls"], 1)
        self.assertEqual(result["snapshot"]["status"], "ready")

    def test_distributed_runtime_matches_canonical_source(self):
        self.assertEqual(MODULE.read_bytes(),
                         (ROOT / "plugins" / "yiyuan-accord-codex" / "runtime" /
                          "codex-session.cjs").read_bytes())

    def test_settled_transfer_restores_on_a_fresh_controller_and_fences_the_old_token(self):
        result = self.restore_case("success")
        self.assertEqual(result["effects"], ["claim", "resume"])
        self.assertEqual((result["claimCalls"], result["resumeCalls"]), (1, 1))
        self.assertEqual(result["restored"]["status"], "ready")
        self.assertEqual(result["restored"]["sourceThreadId"], "target-1")
        self.assertNotEqual(result["basis"]["token"], result["currentScope"]["token"])
        self.assertEqual(result["turn"]["status"], "completed")
        self.assertEqual(result["restoredTurnStarts"], 1)
        self.assertEqual(result["oldWriter"], "SOURCE_SCOPE_CHANGED")
        self.assertEqual(result["oldWriterExtraTurns"], 0)
        self.assertEqual(result["resumeParamsSeen"], {"threadId": "target-1", "excludeTurns": True, "cwd": "C:/restored",
            "sandbox": "read-only", "approvalPolicy": "never", "model": "restored-model",
            "modelProvider": "fixture", "config": {"model_reasoning_effort": "high"}})
        self.assertEqual(result["restoreReadParams"], [{"threadId": "target-1"},
                                                        {"threadId": "target-1"}])

    def test_active_transfer_is_rejected_before_claim_or_resume(self):
        result = self.restore_case("active")
        self.assertEqual(result["error"]["code"], "RESTORE_PRECONDITION_FAILED")
        self.assertEqual(result["failedSession"]["status"], "failed")
        self.assertEqual((result["claimCalls"], result["resumeCalls"]), (0, 0))

    def test_ordinary_source_restores_without_fabricating_a_transfer_or_new_thread(self):
        result = self.restore_case("source-success")
        self.assertNotIn("error", result)
        self.assertEqual(result["original"]["status"], "completed")
        self.assertEqual(result["restored"]["sourceThreadId"], "source-1")
        self.assertEqual(result["restored"]["transfers"], [])
        self.assertIsNone(result["adopted"])
        self.assertEqual(result["resumeCalls"], 1)
        self.assertEqual(result["claimCalls"], 1)
        self.assertEqual(result["restoredTurnStarts"], 1)
        self.assertEqual(result["effects"], ["claim", "resume"])
        self.assertEqual(result["restoreReadParams"], [{"threadId": "source-1"}, {"threadId": "source-1"}])
        self.assertEqual(sum(x["method"] == "thread/start" for x in result["oldCalls"]), 1)
        self.assertEqual(result["oldWriterExtraTurns"], 0)
        self.assertEqual(result["oldWriter"], "SOURCE_SCOPE_CHANGED")

    def test_source_restore_requires_identity_origin_and_native_quiescence_before_claim(self):
        for mode in ("wrong-id", "same-connection", "ambiguous-origin", "origin-unverified", "origin-ref-missing",
                     "pause-unverified", "native-active", "ephemeral", "active"):
            with self.subTest(mode=mode):
                result = self.restore_case("source-" + mode)
                self.assertIn("error", result)
                self.assertEqual(result["claimCalls"], 0)
                self.assertEqual(result["resumeCalls"], 0)
                self.assertEqual(result["restoredTurnStarts"], 0)

    def test_source_restore_uncertain_effects_consume_the_old_basis_without_replay(self):
        for mode, code, resumes in (("claim-loss", "RESTORE_CLAIM_UNKNOWN", 0),
                                    ("resume-loss", "RESTORE_RESUME_UNKNOWN", 1)):
            with self.subTest(mode=mode):
                result = self.restore_case("source-" + mode)
                self.assertEqual(result["error"]["code"], code)
                self.assertEqual(result["retry"], "RESTORE_PRECONDITION_FAILED")
                self.assertEqual(result["claimCalls"], 1)
                self.assertEqual(result["resumeCalls"], resumes)
                self.assertEqual(result["restoredTurnStarts"], 0)
                self.assertNotEqual(result["basis"]["token"], result["currentScope"]["token"])

    def test_source_restore_post_verification_holds_tools_and_concurrent_scope_changes(self):
        for mode, code in (("tools-denied", "RESTORE_POSTCHECK_DENIED"),
                           ("scope-changed", "RESTORE_SCOPE_CHANGED")):
            with self.subTest(mode=mode):
                result = self.restore_case("source-" + mode)
                self.assertEqual(result["error"]["code"], code)
                self.assertEqual(result["failedSession"]["status"], "failed")
                self.assertEqual(result["resumeCalls"], 1)
                self.assertEqual(result["restoredTurnStarts"], 0)
                self.assertEqual(result["locked"], "SESSION_FAILED")

    def test_unknown_resume_claims_first_then_old_basis_cannot_replay(self):
        result = self.restore_case("resume-loss")
        self.assertEqual(result["error"]["code"], "RESTORE_RESUME_UNKNOWN")
        self.assertEqual(result["locked"], "SESSION_FAILED")
        self.assertEqual(result["effects"], ["claim", "resume"])
        self.assertEqual(result["retry"], "RESTORE_PRECONDITION_FAILED")
        self.assertEqual(result["resumeCalls"], 1)

    def test_unknown_claim_rotates_fence_and_same_basis_cannot_replay_or_resume(self):
        result = self.restore_case("claim-loss")
        self.assertEqual(result["error"]["code"], "RESTORE_CLAIM_UNKNOWN")
        self.assertEqual(result["locked"], "SESSION_FAILED")
        self.assertEqual(result["effects"], ["claim"])
        self.assertEqual(result["retry"], "RESTORE_PRECONDITION_FAILED")
        self.assertEqual(result["resumeCalls"], 0)

    def test_claim_loss_guard_runs_after_slow_completed_handoff(self):
        result = self.restore_case("claim-loss", slow_record_ms=4200)
        self.assertEqual(result["original"]["status"], "transferred")
        self.assertEqual(result["error"]["code"], "RESTORE_CLAIM_UNKNOWN")
        self.assertEqual(result["claimCalls"], 1)
        self.assertNotEqual(result["basis"]["token"], result["currentScope"]["token"])
        self.assertEqual(result["retry"], "RESTORE_PRECONDITION_FAILED")
        self.assertEqual(result["resumeCalls"], 0)

    def test_native_tool_evidence_denial_after_resume_keeps_restored_executor_failed(self):
        result = self.restore_case("tools-denied")
        self.assertEqual(result["error"]["code"], "RESTORE_POSTCHECK_DENIED")
        self.assertEqual(result["failedSession"]["status"], "failed")
        self.assertEqual(result["locked"], "SESSION_FAILED")
        self.assertEqual(result["effects"], ["claim", "resume"])

    def test_scope_change_during_post_verification_prevents_ready_state(self):
        result = self.restore_case("scope-changed")
        self.assertEqual(result["error"]["code"], "RESTORE_SCOPE_CHANGED")
        self.assertEqual(result["failedSession"]["status"], "failed")
        self.assertEqual(result["locked"], "SESSION_FAILED")
        self.assertEqual(result["effects"], ["claim", "resume", "verifier-claim"])
        self.assertNotEqual(result["error"]["state"]["scope"]["token"],
                            result["error"]["state"]["finalScope"]["token"])

    def test_invalid_or_expired_restore_executor_cannot_fallback_to_source_creation(self):
        for mode in ("invalid-restore", "expired-restore"):
            with self.subTest(mode=mode):
                result = self.restore_case(mode)
                self.assertEqual(result["error"]["code"], "TypeError")
                self.assertEqual(result["failedSession"]["status"], "restore-required")
                self.assertEqual(result["locked"], "RESTORE_REQUIRED")
                self.assertEqual((result["claimCalls"], result["resumeCalls"]), (0, 0))
                self.assertEqual(result["restoreReadParams"], [])


    def test_reentrant_owner_callback_failure_locks_outer_run(self):
        result = self.run_case('owner-reentrant')
        self.assertEqual(result['error']['state']['status'], 'failed')
        self.assertEqual(result['error']['code'], 'SERVER_REQUEST_FAILED')
        self.assertEqual(result['snapshot']['failure']['cause']['code'], 'RUN_IN_PROGRESS')
        self.assertEqual(result['snapshot']['pendingRequest']['method'], 'approval/request')
        self.assertEqual(result['second'], 'SESSION_FAILED')
        self.assertEqual(sum(frame.get('method') == 'turn/start' for frame in result['sent']), 1)

    def test_same_class_restore_verifier_error_cannot_authorize_a_turn(self):
        for mode in ('verifier-session-error', 'source-verifier-session-error'):
            with self.subTest(mode=mode):
                result = self.restore_case(mode)
                self.assertEqual(result['failedSession']['status'], 'failed')
                self.assertEqual(result['locked'], 'SESSION_FAILED')
                self.assertEqual(result['failedSession']['failure']['cause']['code'], 'CALLBACK_FAILURE')
                self.assertEqual(result['claimCalls'], 1)
                self.assertEqual(result['resumeCalls'], 1)
                self.assertEqual(result['restoredTurnStarts'], 0)
                self.assertEqual(result['failedSession']['lastSafeReceipt']['thread']['id'],
                                 'source-1' if mode.startswith('source-') else 'target-1')

    def test_same_class_settle_error_does_not_allow_settle_replay(self):
        result = self.run_case('adopt-session-error')
        self.assertEqual(result['snapshot']['status'], 'failed')
        self.assertEqual(result['snapshot']['failure']['cause']['code'], 'CALLBACK_FAILURE')
        self.assertEqual(result['retry'], 'SESSION_FAILED')
        self.assertEqual(result['settleCalls'], 1)
        self.assertEqual(result['snapshot']['adoption']['transferId'], 'transfer-1')
        self.assertNotIn('settleReceipt', result['snapshot']['adoption'])
        self.assertIsNone(result['finalScope']['activeTransferId'])


if __name__ == "__main__":
    unittest.main()
