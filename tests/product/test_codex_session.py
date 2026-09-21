"""Source-session protocol integration; fixed local RPC, no model or host process."""
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
MODULE = ROOT / "runtime" / "codex-session.cjs"


NODE_SCENARIO = r'''
const {PassThrough, Writable} = require('node:stream');
const {performance} = require('node:perf_hooks');
const {createOwnedAppServerConnection} = require(process.argv[1]);
const {openCarrierRecorder} = require(process.argv[2]);
const {createCodexSourceSession} = require(process.argv[3]);
const mode = process.argv[4], databasePath = process.argv[5];
const output = new PassThrough(), sent = [], starts = [], serverResponses = [];
let targetTurn = 0, sourceTurn = 0, targetCreated = 0, sourceUnsubscribed = 0, sourceStarted = false;
const emit = value => output.write(Buffer.from(JSON.stringify(value) + '\n'));
const response = (frame, result) => queueMicrotask(() => emit({jsonrpc:'2.0', id:frame.id, result}));
function serverRequest(id, method, params) { emit({jsonrpc:'2.0', id, method, params}); }
function handle(frame) {
  sent.push(frame);
  if (!frame.method) {
    serverResponses.push(frame);
    if (frame.id === 100) queueMicrotask(() => serverRequest(101, 'approval/request', {
      threadId:'source-1', turnId:'source-turn-1', reason:'fixture-owner-decision'}));
    if (frame.id === 101) queueMicrotask(() => serverRequest(102, 'item/tool/call', {
      threadId:'source-1', turnId:'source-turn-1', callId:'handoff-call',
      tool:'accord_request_handoff', namespace:null,
      arguments:{reason:'Move the fixed task to a fresh carrier.'}}));
    if (frame.id === 102) queueMicrotask(() => {
      emit({method:'item/completed', params:{threadId:'source-1', turnId:'source-turn-1',
        item:{type:'dynamicToolCall', id:'handoff-call', tool:'accord_request_handoff',
          namespace:null, status:'completed', success:true,
          contentItems:frame.result.contentItems}}});
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
        if (mode === 'concurrent' || mode === 'scope-after-terminal') emit({method:'turn/completed', params:{threadId:'source-1',
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
        } else if (mode === 'adopt-chain' && targetTurn === 1) {
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
const connection = createOwnedAppServerConnection({stdin:input, stdout:output,
  connectionId:'fixture-connection', hostVersion:'fixture-host'});
const recorder = openCarrierRecorder({path:databasePath, create:true});
let scopeReads = 0, recordReads = 0, settleCalls = 0;
const wrappedRecorder = ['scope-active','scope-after-terminal','adopt-old-lease',
  'adopt-missing-tools','adopt-settle-loss','adopt-bad-settle',
  'adopt-deadline-before-settle'].includes(mode);
const sessionRecorder = wrappedRecorder ? {
  bindScope:recorder.bindScope, begin:recorder.begin, compareAndSet:recorder.compareAndSet,
  read(...args) {
    recordReads++;
    const value = recorder.read(...args);
    if (recordReads !== 2) return value;
    const changed = JSON.parse(JSON.stringify(value));
    if (mode === 'adopt-old-lease') changed.lease.token = 'stale-lease-token';
    if (mode === 'adopt-missing-tools') delete changed.state.plan.target.dynamicTools;
    return changed;
  },
  settle(...args) {
    settleCalls++;
    const value = recorder.settle(...args);
    if (mode === 'adopt-settle-loss') throw new Error('settle acknowledgement lost');
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
    return scope;
  },
} : recorder;
const planCalls = [], ownerCalls = [], currentCalls = [], verifyCalls = [];
let adoptionVerifyCalls = 0;
const session = createCodexSourceSession({connection, recorder:sessionRecorder, scopeRef:'fixture-scope',
  threadStart:{cwd:'C:/fixture', model:'owner-model', effort:'owner-effort',
    sandbox:'workspace-write', approvalPolicy:'on-request', dynamicTools:[{
      type:'function', name:'owner_tool', description:'owner tool',
      inputSchema:{type:'object', properties:{}, additionalProperties:false}}]},
  planResolver(request, context) {
    planCalls.push({request, context:{...context, signal:undefined}});
    const ordinal = planCalls.length;
    const now = Date.now();
    return {transferId:`transfer-${ordinal}`, scopeRef:'fixture-scope', authorityRef:'authority-1',
      stateRef:'state-1', source:{threadId:context.threadId, turnId:context.turnId},
      target:{cwd:'C:/fixture', model:`target-model-${ordinal}`, effort:'target-effort'},
      handoffText:'Retain the fixed authorized task and protected inputs.',
      continuation:{input:'Perform the next bounded step.', sandboxPolicy:{type:'readOnly'}},
      deadlineMs:now+4000, recoveryDeadlineMs:now+4500};
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
  ownerRequest(request) { ownerCalls.push(request); return {result:{decision:'denied-by-owner'}}; },
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
    } else if (mode === 'adopt-chain') {
      result.first = await session.run({input:'one source turn', deadlineMs:Date.now()+6000});
      result.adopted = await session.adoptTarget({deadlineMs:Date.now()+3000});
      result.secondTransfer = await session.run({input:'second source carrier',
        deadlineMs:Date.now()+6000});
      try { await session.run({input:'must wait for second adoption', deadlineMs:Date.now()+1000}); }
      catch (error) { result.second = error.code; }
    } else if (mode.startsWith('adopt-')) {
      result.first = await session.run({input:'one source turn', deadlineMs:Date.now()+6000});
      const adoptionDeadline = mode === 'adopt-deadline-before-settle' ? 10 : 3000;
      try { result.adopted = await session.adoptTarget({deadlineMs:Date.now()+adoptionDeadline}); }
      catch (error) { result.adoptionError = {code:error.code, state:error.state}; }
      if (mode === 'adopt-deadline-before-settle') {
        result.settleCallsAfterDeadline = settleCalls;
        result.statusAfterDeadline = session.snapshot().status;
        result.adopted = await session.adoptTarget({deadlineMs:Date.now()+3000});
      }
      if (mode === 'adopt-settle-loss' || mode === 'adopt-bad-settle') {
        try { await session.adoptTarget({deadlineMs:Date.now()+1000}); }
        catch (error) { result.retry = error.code; }
      }
    } else {
      try { result.first = await session.run({input:'one source turn',
        turn:{effort:'turn-owner-effort', sandboxPolicy:{type:'workspaceWrite'}},
        deadlineMs:Date.now()+6000}); }
      catch (error) { result.error = {code:error.code, phase:error.phase,
        state:error.state, rpcRequest:error.rpcRequest, nativeRequest:error.nativeRequest}; }
      try { await session.run({input:'must not replay', deadlineMs:Date.now()+1000}); }
      catch (error) { result.second = error.code; }
    }
    result.snapshot = session.snapshot(); result.sent = sent; result.starts = starts;
    result.serverResponses = serverResponses; result.planCalls = planCalls.length;
    result.ownerCalls = ownerCalls.length; result.currentCalls = currentCalls.length;
    result.verifyCalls = verifyCalls; result.recordReads = recordReads;
    result.settleCalls = settleCalls;
    console.log(JSON.stringify(result));
  } finally { connection.close(); recorder.close(); }
})().catch(error=>{console.error(error);process.exitCode=1});
'''


class CodexSourceSessionTests(unittest.TestCase):
    def run_case(self, mode):
        with tempfile.TemporaryDirectory() as temp:
            database = Path(temp) / "carrier.sqlite"
            command = [shutil.which("node"), "-e", NODE_SCENARIO,
                       str(ROOT / "runtime" / "codex-connection.cjs"),
                       str(ROOT / "runtime" / "carrier-recorder.cjs"),
                       str(MODULE), mode, str(database)]
            completed = subprocess.run(command, capture_output=True, text=True,
                                       encoding="utf-8", timeout=15)
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

    def test_source_start_ack_loss_is_not_retried_and_locks_the_session(self):
        result = self.run_case("start-loss")
        self.assertEqual(result["error"]["code"], "SOURCE_START_UNKNOWN")
        self.assertEqual(result["error"]["phase"], "source-start-unknown")
        self.assertEqual(result["error"]["rpcRequest"]["method"], "thread/start")
        self.assertEqual(result["error"]["state"]["failure"]["cause"]["rpcRequest"],
                         result["error"]["rpcRequest"])
        self.assertEqual(result["second"], "SESSION_FAILED")
        self.assertEqual(sum(frame.get("method") == "thread/start" for frame in result["sent"]), 1)

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
                self.assertEqual(result["adoptionError"]["code"], code)
                self.assertEqual(result["snapshot"]["status"], "transferred")
                self.assertEqual(result["settleCalls"], 0)
                self.assertEqual(result["snapshot"]["sourceThreadId"], "source-1")
                self.assertEqual(result["snapshot"]["targetThreadId"], "target-1")

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


if __name__ == "__main__":
    unittest.main()
