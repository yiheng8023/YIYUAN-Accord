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
let targetTurn = 0, sourceTurn = 0, sourceStarted = false;
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
    } else response(frame, {thread:{id:'target-1', status:{type:'idle'}, ephemeral:false},
      cwd:frame.params.cwd, model:frame.params.model, approvalPolicy:frame.params.approvalPolicy,
      sandbox:{type:'readOnly'}});
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
      queueMicrotask(() => emit({method:'turn/completed', params:{threadId:'target-1',
        turn:{id, status:'completed', items:[]}}}));
    }
    return;
  }
  if (frame.method === 'thread/read') return response(frame, {thread:{id:frame.params.threadId,
    status:{type:'idle'}, ephemeral:false}});
  if (frame.method === 'thread/unsubscribe') return response(frame, {status:'unsubscribed'});
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
let scopeReads = 0;
const sessionRecorder = ['scope-active','scope-after-terminal'].includes(mode) ? {
  bindScope:recorder.bindScope, begin:recorder.begin, compareAndSet:recorder.compareAndSet,
  read:recorder.read, settle:recorder.settle,
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
const session = createCodexSourceSession({connection, recorder:sessionRecorder, scopeRef:'fixture-scope',
  threadStart:{cwd:'C:/fixture', model:'owner-model', effort:'owner-effort',
    sandbox:'workspace-write', approvalPolicy:'on-request', dynamicTools:[{
      type:'function', name:'owner_tool', description:'owner tool',
      inputSchema:{type:'object', properties:{}, additionalProperties:false}}]},
  planResolver(request, context) {
    planCalls.push({request, context:{...context, signal:undefined}});
    const now = Date.now();
    return {transferId:'transfer-1', scopeRef:'fixture-scope', authorityRef:'authority-1',
      stateRef:'state-1', source:{threadId:context.threadId, turnId:context.turnId},
      target:{cwd:'C:/fixture', model:'target-model', effort:'target-effort'},
      handoffText:'Retain the fixed authorized task and protected inputs.',
      continuation:{input:'Perform the next bounded step.', sandboxPolicy:{type:'readOnly'}},
      deadlineMs:now+4000, recoveryDeadlineMs:now+4500};
  },
  verify(stage, facts) {
    verifyCalls.push(stage);
    return {decision:'allow', scopeRef:'fixture-scope', authorityRef:'authority-1',
      stateRef:'state-1', sourceRef:'fixture:'+stage, sourceRecoveryReady:true,
      targetInitializationSafe:true, quiesced:true, noOtherWriters:true,
      targetSettingsMatch:true, initializationEffectsVerified:true, accepted:true,
      sourceIdle:true, intakeEffectsVerified:true, singleWriter:true, effectsVerified:true};
  },
  current(context) {
    currentCalls.push({...context, signal:undefined});
    return {scopeRef:'fixture-scope', authorityRef:'authority-1', stateRef:'state-1',
      writerThreadId:'source-1'};
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
    result.verifyCalls = verifyCalls;
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
            "automaticHandoffToolRegistered": False})
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
        self.assertIn("dynamic tool name conflict", result["conflict"])
        self.assertEqual(result["sent"], [])

    def test_distributed_runtime_matches_canonical_source(self):
        self.assertEqual(MODULE.read_bytes(),
                         (ROOT / "plugins" / "yiyuan-accord-codex" / "runtime" /
                          "codex-session.cjs").read_bytes())


if __name__ == "__main__":
    unittest.main()
