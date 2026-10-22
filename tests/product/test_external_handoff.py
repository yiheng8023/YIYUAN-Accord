"""External-source public protocol tests; deterministic native fixture, no model."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
import time

ROOT = Path(__file__).resolve().parents[2]
MODULE = ROOT / "plugins/yiyuan-accord-codex/runtime/external-handoff.cjs"
RECORDER = ROOT / "plugins/yiyuan-accord-codex/runtime/carrier-recorder.cjs"
HOST = ROOT / "tests/product/external_handoff_host.cjs"

try:
    from .test_codex_capabilities import owned_process, owned_run
except ImportError:  # unittest discovery loads this directory as top-level modules
    from test_codex_capabilities import owned_process, owned_run

SCENARIO = r'''
const {createExternalHandoff}=require(process.argv[1]);
const {openCarrierRecorder}=require(process.argv[2]);
const mode=process.argv[4], calls=[], checks=[], source={kind:'codex-mcp-request-metadata',
 threadId:'external-root',sessionTreeId:'external-root',turnId:'external-turn',callId:'source-call'};
const basis={epoch:'input-1',revision:1,authorityRef:'authority-1',snapshotRef:'candidate-1',
 protectedInputsDigest:'a'.repeat(64),inputComplete:true,paused:false,recoveryRequired:false,
 sourceThreadId:source.threadId,sourceTurnId:source.turnId,
 quiescence:{noInFlightEffects:true,noOtherWriters:true,evidenceRef:'independent-drain-1'}};
const recorder=openCarrierRecorder({path:process.argv[3],create:true});
const controlled=['late-factory','factory-clock-expired','before-factory','idle-deadline'].includes(mode);
let clock=0;
if(controlled)Object.defineProperty(require('node:perf_hooks').performance,'now',{value:()=>clock});
const timers=[];
const realSetTimeout=global.setTimeout,realClearTimeout=global.clearTimeout;
if(['late-factory','idle-deadline'].includes(mode)){
 global.setTimeout=(fn,ms)=>{const t={fn,ms,cleared:false,unref(){return this;}};timers.push(t);return t;};
 global.clearTimeout=t=>{if(timers.includes(t)){t.cleared=true;realClearTimeout(t.real);}else realClearTimeout(t);};
}
let factoryEntered,returnFactory;
const entered=new Promise(r=>factoryEntered=r),factoryGate=new Promise(r=>returnFactory=r);
let turn=0,closed=false,operation,factoryStarted=false,closeCount=0,beforeFactoryReturn=null;
const native={connectionId:'fixture-connection',hostVersion:'fixture-no-model',
 async request(method,params,deadline,beforeSend){
  const requestRef={connectionId:this.connectionId,hostVersion:this.hostVersion,
   requestId:'native-'+(calls.length+1),method};
  if(beforeSend && mode!=='missing-request-ref')beforeSend(requestRef);
  calls.push({method,params});
  if(method==='thread/start')return {thread:{id:'fresh-target',ephemeral:false,status:{type:'idle'}}};
  if(method==='thread/read')return {thread:{id:'fresh-target',ephemeral:false,status:{type:mode==='target-busy'?'active':'idle'}}};
  if(method==='turn/start'){
   turn++;if(mode==='ack-loss' && turn===2)throw Object.assign(Error('lost'),{code:'ACK_LOST'});
   return {turn:{id:'turn-'+turn}};}
  if(method==='turn/interrupt')return {};
  throw Error('unexpected method');
 },
 async waitTurn(threadId,turnId,deadline,check){
  if(mode==='cancel-intake' && turn===1){queueMicrotask(()=>operation.cancel('root cancelled'));await new Promise(r=>setTimeout(r,15));}
  if(mode==='late-input' && turn===3)basis.epoch='changed-after-release';
  await check();return {
  terminal:{method:'turn/completed',params:{threadId,turn:{id:turnId,status:mode==='interrupted-continuation'&&turn===2?'interrupted':'completed'}}},
  output:'fixed response '+turnId, events:[{method:'item/completed',threadId,turnId,itemType:'agentMessage'}]};},
  async close(){closed=true;closeCount++;return {closed:true,exitCode:0,signal:null,forced:false};}
};
(async()=>{let error=null;
 try{
  if(mode==='shared-source')source.threadId='descendant';
  operation=createExternalHandoff({source,recorder:{...recorder,compareAndSet(...args){
     const r=recorder.compareAndSet(...args);
     if(mode==='before-factory' && args[2].pendingEffect?.kind==='owned-native-start')clock=6000;
     return r;}},current:async()=>JSON.parse(JSON.stringify(basis)),
    nativeFactory:async()=>{factoryStarted=true;factoryEntered();
     if(mode==='late-factory')return factoryGate;
     if(mode==='factory-clock-expired')clock=6000;
     return native;},
   verify:async(stage,review,facts)=>{checks.push(stage);return {decision:mode==='review-denied'&&stage==='commit'?'deny':'allow',evidenceRef:'independent-'+stage};}});
  const preparing=operation.prepare({transferId:'transfer-1',scopeRef:'review-scope',cwd:process.cwd(),
  model:'fixture',intake:'Inspect the candidate; do not review yet.',
  continuation:'Review first bounded section.',postRelease:'Finish remaining review.',
   deadlineMs:Date.now()+(mode==='idle-deadline'?100:5000)});
  if(mode==='late-factory'){
   await entered;
   const active=timers.filter(t=>!t.cleared);
   if(active.length!==2)throw Error('fixture deadline timers changed');
   clock=6000;active[1].fn();
   try{await preparing;}finally{
    beforeFactoryReturn={closed,pending:operation.inspect().nativeStartPending};
    returnFactory(native);await new Promise(setImmediate);
   }
  }else await preparing;
   if(mode==='idle-deadline'){
    // Setup is frozen; arm the original real deadline only once intake exists.
    const active=timers.filter(t=>!t.cleared);
    if(active.length!==1 || operation.inspect().phase!=='awaiting-intake-review')throw Error('fixture idle setup changed');
    active[0].real=realSetTimeout(active[0].fn,active[0].ms);
    await new Promise(r=>realSetTimeout(r,150));throw Object.assign(Error('expired'),{code:'DEADLINE_EXCEEDED'});
   }
  if(mode==='changed-input')basis.epoch='new-input';
  if(mode==='inflight')basis.quiescence.noInFlightEffects=false;
  if(mode==='stale-lease'){
   const s=recorder.read('transfer-1','review-scope');recorder.compareAndSet('transfer-1',s.revision,s.state,s.lease);}
  if(mode==='cancel-idle'){await operation.cancel('root cancelled');throw Object.assign(Error('cancelled'),{code:'CANCELLED'});}
  await operation.commit({evidenceRef:'root-reviewed-intake'});
  if(mode==='paused')basis.paused=true;
  await operation.release({evidenceRef:'root-reviewed-first-continuation'});
 }catch(e){error={code:e.code,message:e.message};}
 let retry=null;
 if(mode==='ack-loss'){try{await operation.commit({evidenceRef:'no replay'});}catch(e){retry=e.code;}}
  console.log(JSON.stringify({error,retry,calls,checks,closed,factoryStarted,closeCount,beforeFactoryReturn,state:operation?.inspect()??null}));
 recorder.close();
})().catch(e=>{console.error(e);process.exitCode=1});
'''

WIRE_SCENARIO = r'''
const {createExternalHandoff,createOwnedNativeRunner}=require(process.argv[1]);
const {openCarrierRecorder}=require(process.argv[2]);
const source={kind:'codex-mcp-request-metadata',threadId:'source',sessionTreeId:'source',turnId:'source-turn',callId:'source-call'};
const recorder=openCarrierRecorder({path:process.argv[3],create:true});
let rawClosed=null;
const op=createExternalHandoff({source,recorder,current:async()=>({sourceThreadId:'source',sourceTurnId:'source-turn',
 epoch:'input-1',revision:1,authorityRef:'authority',snapshotRef:'candidate',protectedInputsDigest:'a'.repeat(64),
 inputComplete:true,paused:false,recoveryRequired:false,quiescence:{noInFlightEffects:true,noOtherWriters:true,evidenceRef:'drained'}}),
 verify:async()=>({decision:'allow',evidenceRef:'fixture-independent-verification'}),
 nativeFactory:async options=>{
  const runner=await createOwnedNativeRunner({...options,executable:process.execPath,
   args:[process.argv[4],process.argv[5],process.argv[6]],hostVersion:'fixed-wire-fixture',cleanupTimeoutMs:5000});
  return {...runner,close:async()=>{rawClosed=await runner.close();return rawClosed;}};
 }});
(async()=>{let error=null;
 try{await op.prepare({transferId:'wire-transfer',scopeRef:'wire-scope',cwd:process.cwd(),model:'fixture',
 intake:'read the packet',continuation:'first useful chunk',postRelease:'remaining review',deadlineMs:Date.now()+25000});
 await op.commit({evidenceRef:'reviewed-intake'});await op.release({evidenceRef:'reviewed-first'});
 }catch(e){error={code:e.code,message:e.message};}
 console.log(JSON.stringify({error,state:op.inspect(),rawClosed}));recorder.close();
})().catch(e=>{console.error(e);process.exitCode=1});
'''


@unittest.skipUnless(shutil.which("node"), "Node required")
class ExternalHandoffTests(unittest.TestCase):
    def run_scenario(self, mode="normal"):
        with tempfile.TemporaryDirectory() as directory:
            completed = subprocess.run(
                ["node", "-e", SCENARIO, str(MODULE), str(RECORDER),
                 str(Path(directory) / "recorder.sqlite"), mode],
                cwd=ROOT, text=True, encoding="utf-8", capture_output=True, timeout=15,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            return json.loads(completed.stdout)

    def test_fresh_target_continues_after_cooperative_release_and_closes(self):
        result = self.run_scenario()
        self.assertIsNone(result["error"])
        self.assertEqual(result["state"]["phase"], "completed")
        self.assertTrue(result["closed"])
        self.assertEqual(result["state"]["source"]["threadId"], "external-root")
        self.assertEqual(result["state"]["writerThreadId"], "fresh-target")
        turns = [x for x in result["calls"] if x["method"] == "turn/start"]
        self.assertEqual(len(turns), 3)
        self.assertEqual(turns[2]["params"]["input"][0]["text"], "Finish remaining review.")
        self.assertEqual(result["state"]["release"]["kind"], "cooperative-duty-release")
        self.assertEqual(result["state"]["postReleaseTurn"]["turnId"], "turn-3")
        self.assertTrue(all(x["params"].get("threadId") != "external-root" for x in result["calls"]))

    def test_source_changes_and_review_denial_hold_before_writer_transfer(self):
        for mode, code in [("changed-input", "SOURCE_BASIS_CHANGED"),
                           ("inflight", "SOURCE_NOT_QUIESCENT"),
                           ("review-denied", "VERIFICATION_DENIED")]:
            with self.subTest(mode=mode):
                result = self.run_scenario(mode)
                self.assertEqual(result["error"]["code"], code)
                self.assertEqual(result["state"]["writer"], "source")
                self.assertTrue(result["closed"])
                self.assertEqual(len([x for x in result["calls"] if x["method"] == "turn/start"]), 1)

    def test_pause_after_transfer_does_not_return_writer_or_release_source(self):
        result = self.run_scenario("paused")
        self.assertEqual(result["error"]["code"], "SOURCE_PAUSED")
        self.assertEqual(result["state"]["writer"], "target")
        self.assertNotIn("release", result["state"])
        self.assertTrue(result["closed"])

    def test_ack_loss_retains_exact_request_and_does_not_replay(self):
        result = self.run_scenario("ack-loss")
        self.assertEqual(result["error"]["code"], "ACK_LOST")
        self.assertEqual(result["state"]["pendingEffect"]["requestRef"]["method"], "turn/start")
        self.assertTrue(result["retry"])
        self.assertEqual(len([x for x in result["calls"] if x["method"] == "turn/start"]), 2)
        self.assertEqual(result["state"]["writer"], "target")
        self.assertTrue(result["closed"])

    def test_known_interrupted_turn_retains_observed_terminal_and_unreviewed_effects(self):
        result = self.run_scenario('interrupted-continuation')
        self.assertEqual(result['error']['code'], 'TARGET_TURN_NOT_COMPLETED')
        self.assertEqual(result['state']['phase'], 'held')
        self.assertEqual(result['state']['writer'], 'target')
        stopped = result['state']['stoppedTurn']
        self.assertEqual(stopped['turnId'], 'turn-2')
        self.assertEqual(stopped['terminal'], 'interrupted')
        self.assertTrue(result['state']['pendingEffect']['effectsUnreviewed'])
        self.assertNotIn('release', result['state'])
        self.assertTrue(result['closed'])

    def test_cancel_during_intake_and_while_idle_closes_only_owned_target(self):
        for mode in ["cancel-intake", "cancel-idle"]:
            with self.subTest(mode=mode):
                result = self.run_scenario(mode)
                self.assertEqual(result["error"]["code"], "CANCELLED")
                self.assertEqual(result["state"]["phase"], "cancelled-held")
                self.assertEqual(result["state"]["writer"], "source")
                self.assertTrue(result["closed"])

    def test_late_input_after_release_holds_without_false_completion(self):
        result = self.run_scenario("late-input")
        self.assertEqual(result["error"]["code"], "SOURCE_BASIS_CHANGED")
        self.assertEqual(result["state"]["release"]["kind"], "cooperative-duty-release")
        self.assertEqual(result["state"]["phase"], "held")
        self.assertEqual(result["state"]["writer"], "target")
        self.assertTrue(result["state"]["pendingEffect"])

    def test_stale_lease_and_missing_native_request_anchor_are_not_accepted(self):
        for mode, code in [("stale-lease", "SCOPE_CHANGED"),
                           ("missing-request-ref", "NATIVE_REQUEST_REFERENCE_MISSING")]:
            with self.subTest(mode=mode):
                result = self.run_scenario(mode)
                self.assertEqual(result["error"]["code"], code)
                self.assertTrue(result["closed"])

    def test_shared_parent_identity_is_rejected_before_native_start(self):
        result = self.run_scenario("shared-source")
        self.assertEqual(result["error"]["code"], "SOURCE_SHARED_PARENT_IDENTITY")
        self.assertEqual(result["calls"], [])

    def test_busy_target_cannot_settle_as_complete(self):
        result = self.run_scenario("target-busy")
        self.assertEqual(result["error"]["code"], "TARGET_NOT_IDLE")
        self.assertEqual(result["state"]["phase"], "held")
        self.assertTrue(result["closed"])

    def test_idle_operation_expires_and_late_factory_is_reclaimed(self):
        for mode in ["idle-deadline", "late-factory"]:
            with self.subTest(mode=mode):
                result = self.run_scenario(mode)
                self.assertEqual(result["error"]["code"], "DEADLINE_EXCEEDED")
                self.assertTrue(result["closed"])
                self.assertEqual(result["state"]["phase"], "held")
                self.assertFalse(result["state"]["nativeStartPending"])
                self.assertTrue(result['factoryStarted'])
                self.assertEqual(result['closeCount'], 1)
                if mode == 'late-factory':
                    self.assertEqual(result['beforeFactoryReturn'], {'closed': False, 'pending': True})
                    self.assertTrue(result['state']['lateNativeClosed']['closed'])
        self.assertEqual(self.run_scenario("late-factory")["calls"], [])

    def test_expiry_before_factory_does_not_report_an_inflight_start(self):
        result = self.run_scenario('before-factory')
        self.assertEqual(result['error']['code'], 'DEADLINE_EXCEEDED')
        self.assertFalse(result['factoryStarted'])
        self.assertEqual(result['closeCount'], 0)
        self.assertFalse(result['state']['nativeStartPending'])
        self.assertEqual(result['calls'], [])

    def test_factory_return_after_deadline_is_closed_without_dispatch(self):
        result = self.run_scenario('factory-clock-expired')
        self.assertEqual(result['error']['code'], 'NATIVE_START_EXPIRED')
        self.assertTrue(result['factoryStarted'])
        self.assertEqual(result['closeCount'], 1)
        self.assertTrue(result['state']['lateNativeClosed']['closed'])
        self.assertFalse(result['state']['nativeStartPending'])
        self.assertEqual(result['calls'], [])

    def test_native_owner_uses_real_stdio_frames_preserves_utf8_and_closes(self):
        with tempfile.TemporaryDirectory() as directory:
            log = Path(directory) / "wire.jsonl"
            completed = owned_run(
                ["node", "-e", WIRE_SCENARIO, str(MODULE), str(RECORDER),
                 str(Path(directory) / "recorder.sqlite"), str(HOST), str(log), "normal"],
                cwd=ROOT, text=True, encoding="utf-8", timeout=30,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            result = json.loads(completed.stdout)
            self.assertIsNone(result["error"], result)
            self.assertEqual(result["state"]["postReleaseTurn"]["output"], "固定协议测试：未调用模型。")
            self.assertTrue(result["rawClosed"]["closed"])
            self.assertFalse(result["rawClosed"]["forced"])
            requests = [json.loads(line) for line in log.read_text().splitlines()]
            self.assertEqual(len([x for x in requests if x["method"] == "turn/start"]), 3)
            self.assertFalse(any(x["threadId"] == "source" for x in requests))

    def test_forced_exit_is_retained_and_not_reported_as_success(self):
        with tempfile.TemporaryDirectory() as directory:
            completed = owned_run(
                ["node", "-e", WIRE_SCENARIO, str(MODULE), str(RECORDER),
                 str(Path(directory) / "recorder.sqlite"), str(HOST),
                 str(Path(directory) / "wire.jsonl"), "hang-on-eof"],
                cwd=ROOT, text=True, encoding="utf-8", timeout=30,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            result = json.loads(completed.stdout)
            self.assertEqual(result["error"]["code"], "NATIVE_CLOSE_UNVERIFIED")
            self.assertEqual(result["state"]["phase"], "held")
            self.assertFalse(result["rawClosed"]["closed"])
            self.assertTrue(result["rawClosed"]["primaryProcessClosed"], result)
            self.assertTrue(result["rawClosed"]["forced"], result)
            if os.name == "nt":
                self.assertEqual(completed.fixture_resources["activeProcesses"], 0,
                                 (result, completed.fixture_resources))

    def test_incomplete_forced_stop_stays_held_before_fixture_cleanup(self):
        script = r"""
const cp=require('node:child_process');
cp.spawnSync=()=>({status:null,error:{code:'ETIMEDOUT'}});
const originalKill=process.kill;
process.kill=(pid,signal)=>{if(pid<0)throw Object.assign(Error('fixture'),{code:'ESRCH'});
 return originalKill(pid,signal);};
""" + WIRE_SCENARIO.replace('cleanupTimeoutMs:5000', 'cleanupTimeoutMs:100')
        with tempfile.TemporaryDirectory() as directory:
            completed = owned_run(['node', '-e', script, str(MODULE), str(RECORDER),
                str(Path(directory)/'recorder.sqlite'), str(HOST),
                str(Path(directory)/'wire.jsonl'), 'hang-on-eof'],
                cwd=ROOT, text=True, encoding='utf-8', timeout=30)
            self.assertEqual(completed.returncode, 0, completed.stderr)
            result = json.loads(completed.stdout)
            self.assertEqual(result['error']['code'], 'NATIVE_CLOSE_UNVERIFIED', result)
            self.assertEqual(result['state']['phase'], 'held', result)
            self.assertFalse(result['rawClosed']['primaryProcessClosed'], result)
            self.assertFalse(result['rawClosed']['closed'], result)
            self.assertTrue(result['rawClosed']['recoveryRequired'], result)
            self.assertEqual(result['rawClosed']['terminationError'],
                             'ETIMEDOUT' if os.name == 'nt' else 'ESRCH', result)

    def test_forced_cleanup_reclaims_exact_owned_descendant(self):
        self.check_owned_descendant('owned-tree')

    def test_exited_launcher_is_never_signalled_by_stale_pid(self):
        self.check_owned_descendant('exited-parent')

    def check_owned_descendant(self, mode):
        import ctypes
        from ctypes import wintypes
        kernel = ctypes.WinDLL('kernel32', use_last_error=True)
        kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
        kernel.OpenProcess.restype = wintypes.HANDLE
        kernel.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
        kernel.WaitForSingleObject.restype = wintypes.DWORD
        kernel.TerminateProcess.argtypes = [wintypes.HANDLE, wintypes.UINT]
        kernel.CloseHandle.argtypes = [wintypes.HANDLE]
        with tempfile.TemporaryDirectory() as directory:
            log = Path(directory) / 'wire.jsonl'
            owner = owned_process(["node", "-e", WIRE_SCENARIO, str(MODULE), str(RECORDER),
                str(Path(directory)/'recorder.sqlite'), str(HOST), str(log), mode],
                cwd=ROOT, text=True, encoding='utf-8', stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            with owner as process:
                handle = None
                try:
                    end = time.monotonic()+5
                    child_file = Path(str(log)+'.child')
                    while not child_file.exists() and time.monotonic() < end:
                        time.sleep(0.01)
                    self.assertTrue(child_file.exists())
                    # Retain the handle while the known child is live. Cleanup never
                    # uses a PID that could have been recycled after the observation.
                    handle = kernel.OpenProcess(0x00100001, False, int(child_file.read_text()))
                    self.assertTrue(handle)
                    output, error = process.communicate(timeout=25)
                    self.assertEqual(process.returncode, 0, error)
                    result = json.loads(output)
                    observed = kernel.WaitForSingleObject(handle, 1000)
                    self.assertEqual(result['error']['code'], 'NATIVE_CLOSE_UNVERIFIED')
                    self.assertFalse(result['rawClosed']['closed'])
                    self.assertTrue(result['rawClosed']['exitObserved'])
                    if mode == 'owned-tree':
                        self.assertEqual(observed, 0, 'owned descendant survived forced cleanup')
                        self.assertEqual(result['rawClosed']['terminationAttempt'], 'owned-pid-tree')
                    else:
                        self.assertEqual(observed, 258, 'fixture descendant should remain held for exact-handle cleanup')
                        self.assertIsNone(result['rawClosed']['terminationAttempt'])
                        self.assertFalse(result['rawClosed']['closeObserved'])
                        self.assertEqual(result['rawClosed']['descendantVerification'], 'unknown-launcher-exited-with-open-pipes')
                finally:
                    if handle:
                        try:
                            if kernel.WaitForSingleObject(handle, 0) != 0:
                                self.assertTrue(kernel.TerminateProcess(handle, 1), 'fixture exact-handle cleanup failed')
                                self.assertEqual(kernel.WaitForSingleObject(handle, 1000), 0,
                                                 'fixture descendant exit remained unverified')
                        finally:
                            kernel.CloseHandle(handle)



# These two cases specifically inspect Windows process handles/tree termination.
if os.name != 'nt':
    for name in ('test_forced_cleanup_reclaims_exact_owned_descendant',
                 'test_exited_launcher_is_never_signalled_by_stale_pid'):
        delattr(ExternalHandoffTests, name)

if __name__ == "__main__":
    unittest.main()
