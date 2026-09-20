import json
from pathlib import Path
import shutil
import subprocess
import unittest


ROOT = Path(__file__).resolve().parents[2]
MODULE = ROOT / 'runtime' / 'codex-connection.cjs'


NODE_SCENARIO = r'''
const {PassThrough, Writable} = require('node:stream');
const {performance} = require('node:perf_hooks');
const {createOwnedAppServerConnection,CONTEXT_OBSERVATION_TOOL} = require(process.argv[1]);
const out = new PassThrough(); let writes=[];
const input = new Writable({write(c,e,done){writes.push(c.toString());done();}});
const options={stdin:input,stdout:out,connectionId:'c1',hostVersion:'v1',maxJournalBytes:process.argv[2]?Number(process.argv[2]):undefined,maxMessageBytes:process.argv[3]==='oversize'?128:undefined};
const c=createOwnedAppServerConnection(options);
const until=(ms=300)=>performance.now()+ms;
const emit=(v, split=false)=>{const b=Buffer.from(JSON.stringify(v)+'\n'); if(split){out.write(b.subarray(0,3));out.write(b.subarray(3));}else out.write(b)};
(async()=>{let r={}; try {
 if(process.argv[3]==='success'){
  const p=c.transport.request('thread/start',{},until()); emit({jsonrpc:'2.0',id:'accord-owned:1',result:{thread:{id:'t1'},model:'m1'}},true); await p;
  await c.transport.notify('initialized',{},until()); emit({method:'turn/started',params:{threadId:'t1',turn:{id:'u1'}}}); emit({method:'thread/tokenUsage/updated',params:{threadId:'t1',turnId:'u1',tokenUsage:{modelContextWindow:1000,last:{totalTokens:100}}}}); const context=c.context('t1','u1',1000);
  emit({jsonrpc:'2.0',id:9,method:'item/tool/call',params:{threadId:'t1',turnId:'u1',callId:'x',tool:'accord_request_handoff',arguments:{reason:'r'}}});
  const q=await c.receiveRequest(x=>x.id===9,until()); let got=[]; const ch=c.proposalChannel(q,()=>({scopeRef:'s',authorityRef:'a',stateRef:'z',writerThreadId:'t1'})); const clone=JSON.parse(JSON.stringify(q)); const stop=ch.subscribe(x=>got.push(x.method),clone);
  await ch.respond({jsonrpc:'2.0',id:9,result:{ok:true}},until()); emit({method:'item/completed',params:{threadId:'t1',turnId:'u1',item:{id:'x'}}}); emit({method:'turn/completed',params:{threadId:'t1',turn:{id:'u1',status:'completed'}}});
  const term=await c.transport.waitTerminal('t1','u1',until()); stop(); let duplicate=null; try{await ch.respond({id:9,result:{}},until())}catch(e){duplicate=e.message}; r={got,term,writes,duplicate,context};
 } else if(process.argv[3]==='timeout'){try{await c.receiveRequest(()=>true,until(5))}catch(e){r.timeout=e.message}; out.end(); await new Promise(x=>setTimeout(x,5)); r.broken=c.context('x','y',5).reason;
 } else if(process.argv[3]==='bad'){out.write(Buffer.from('{bad}\n')); await new Promise(x=>setTimeout(x,5)); r={reason:c.context('x','y',5).reason};
 } else if(process.argv[3]==='context-missing'){emit({method:'turn/started',params:{threadId:'t1',turn:{id:'u1'}}}); emit({method:'thread/tokenUsage/updated',params:{threadId:'t1',turnId:'u1',tokenUsage:{modelContextWindow:1000,last:{totalTokens:2}}}}); r={reason:c.context('t1','u1',1000).reason};
 } else if(process.argv[3]==='close-pending'){const rpc=c.transport.request('thread/read',{},until(60000)).catch(e=>e.message);const terminal=c.transport.waitTerminal('t','u',until(60000)).catch(e=>e.message);c.close();r={rpc:await rpc,terminal:await terminal};
 } else if(process.argv[3]==='stdin-error'){try{await c.transport.notify('x',{},NaN)}catch(e){r.invalid=e.message};input.destroy(new Error('write failed'));try{await c.transport.notify('initialized',{},until())}catch(e){r.error=e.message}
 } else if(process.argv[3]==='evict'){emit({jsonrpc:'2.0',id:3,method:'item/tool/call',params:{threadId:'t',turnId:'u',callId:'x',tool:'a',arguments:{reason:'r'}}});const q=await c.receiveRequest(()=>true,until());emit({method:'notice',params:{padding:'x'.repeat(100)}});try{const ch=c.proposalChannel(q,()=>({}));ch.subscribe(()=>{},q)}catch(e){r.error=e.message}
 } else if(process.argv[3].startsWith('context-tool')){
  const scenario=process.argv[3];
  if(scenario!=='context-tool-unknown'){
    const p=c.transport.request('thread/start',{},until());emit({id:'accord-owned:1',result:{thread:{id:'t'},model:'native-model'}});await p;
    emit({method:'turn/started',params:{threadId:'t',turn:{id:'u'}}});emit({method:'thread/tokenUsage/updated',params:{threadId:'t',turnId:'u',tokenUsage:{modelContextWindow:1000,last:{totalTokens:100}}}});
  }
  const argumentsValue=scenario==='context-tool-override'?{threadId:'foreign',maxAgeMs:1000}:scenario==='context-tool-invalid-age'?{maxAgeMs:-1}:{};
  emit({id:9,method:'item/tool/call',params:{threadId:'t',turnId:'u',callId:'x',tool:CONTEXT_OBSERVATION_TOOL.name,namespace:scenario==='context-tool-namespace'?'foreign':null,arguments:argumentsValue}});
  const q=await c.receiveRequest(()=>true,until());const before=writes.length;
  try{r.payload=await c.replyContext(q,until());}catch(e){r.error=e.message}
  r.sent=writes.length-before;
  if(r.sent){r.response=JSON.parse(writes[writes.length-1]);try{await c.replyContext(q,until())}catch(e){r.duplicate=e.message}}
  r.totalAfter=writes.length-before;
 } else if(process.argv[3]==='expired-reply'){emit({id:9,method:'item/tool/call',params:{threadId:'t',turnId:'u',callId:'x'}});const q=await c.receiveRequest(()=>true,until());const ch=c.proposalChannel(q,()=>({}));try{await ch.respond({id:9,result:{}},performance.now()-1)}catch(e){r.expired=e.message}r.before=writes.length;await ch.respond({id:9,result:{}},until());r.after=writes.length;
 } else if(process.argv[3]==='null-error'){const p=c.transport.request('thread/read',{},until()).catch(e=>e.message);emit({id:'accord-owned:1',error:null});r={error:await p};
 } else if(process.argv[3]==='oversize'){out.write(Buffer.alloc(1024*1024,65));r={reason:c.context('t','u',100).reason,attached:out.listenerCount('data')};
 } else if(process.argv[3]==='stream-replacement'){let foreignWrites=0;options.stdin=new Writable({write(c,e,done){foreignWrites++;done();}});await c.transport.notify('initialized',{},until());r={original:writes.length,foreign:foreignWrites};
 } else if(process.argv[3]==='listener-error'){emit({id:9,method:'item/tool/call',params:{threadId:'t',turnId:'u',callId:'x'}});const q=await c.receiveRequest(()=>true,until());c.proposalChannel(q,()=>({})).subscribe(()=>{throw new Error('caller listener failed')},q);emit({method:'notice',params:{threadId:'t'}});r={reason:c.context('t','u',100).reason,attached:out.listenerCount('data')};
 } else if(process.argv[3]==='rpc-error-reference'){
  const result=p=>p.catch(e=>({message:e.message,reference:e.rpcRequest,frozen:Object.isFrozen(e.rpcRequest)}));
  const first=result(c.transport.request('turn/start',{threadId:'t'},until()));
  const second=result(c.transport.request('thread/read',{threadId:'t'},until()));
  out.end();r.errors=await Promise.all([first,second]);r.requests=writes;
 } else if(process.argv[3]==='expired'){for(const method of ['request','notify']){try{await c.transport[method]('thread/start',{},performance.now()-1)}catch(e){r[method]=e.message}}r.writes=writes.length;
 } else if(process.argv[3]==='bad-cleanup'){out.write(Buffer.from('{}\n'));r={data:out.listenerCount('data'),end:out.listenerCount('end'),stdinError:input.listenerCount('error')};
 } else if(process.argv[3]==='close'){c.close(); r={destroyed:input.destroyed||out.destroyed,writeEnded:input.writableEnded};}
 }catch(e){r.error=e.message} console.log(JSON.stringify(r));})()
'''


WEBSOCKET_SCENARIO = r'''
const {EventEmitter} = require('node:events');
const {performance} = require('node:perf_hooks');
const {createOwnedAppServerWebSocketConnection} = require(process.argv[1]);
class Socket extends EventEmitter {
 constructor(){super();this.readyState=1;this.bufferedAmount=0;this.sent=[];this.closes=0;}
 addEventListener(n,f){this.on(n,f)} removeEventListener(n,f){this.off(n,f)}
 send(data){if(this.throwSend)throw Error('native send failed');this.sent.push(JSON.parse(data));}
 close(){this.closes++}
 message(value){this.emit('message',{data:JSON.stringify(value,null,2)})}
}
(async()=>{
 const s=new Socket(), foreign=()=>{}; s.on('message',foreign);
 const mode=process.argv[2], until=()=>performance.now()+60000;
 if(mode==='not-open'){s.readyState=0;try{createOwnedAppServerWebSocketConnection({socket:s,connectionId:'c',hostVersion:'v'})}catch(e){console.log(JSON.stringify({error:e.message,listeners:s.listenerCount('message')}));}return;}
 const c=createOwnedAppServerWebSocketConnection({socket:s,connectionId:'c',hostVersion:'v',maxMessageBytes:512,maxBufferedBytes:600});
 let result={};
 if(mode==='success'){
  const p=c.transport.request('thread/start',{},until());
  s.message({id:s.sent[0].id,result:{thread:{id:'t'},model:'m'}}); await p;
  s.message({method:'turn/started',params:{threadId:'t',turn:{id:'u'}}});
  s.message({method:'thread/tokenUsage/updated',params:{threadId:'t',turnId:'u',tokenUsage:{modelContextWindow:1000,last:{totalTokens:100}}}});
  result.context=c.context('t','u',1000);
  s.message({id:9,method:'item/tool/call',params:{threadId:'t',turnId:'u',callId:'x',tool:'accord_request_handoff',arguments:{reason:'r'}}});
  const request=await c.receiveRequest(()=>true,until());
  const channel=c.proposalChannel(request,()=>({scopeRef:'s',authorityRef:'a',stateRef:'z',writerThreadId:'t'}));
  result.events=[];const off=channel.subscribe(x=>result.events.push(x.method),request);
  await channel.respond({id:9,result:{success:true}},until());
  s.message({method:'turn/completed',params:{threadId:'t',turn:{id:'u',status:'completed'}}});
  result.terminal=await c.transport.waitTerminal('t','u',until());off();
 }else if(['buffer','unknown-buffer','send-error'].includes(mode)){
  if(mode==='buffer')s.bufferedAmount=600;if(mode==='unknown-buffer')s.bufferedAmount=undefined;if(mode==='send-error')s.throwSend=true;
  try{await c.transport.request('thread/read',{},until())}catch(e){result.error=e.message}
 }else{
  const rpc=c.transport.request('thread/read',{},until()).catch(e=>e.message);
  const terminal=c.transport.waitTerminal('t','u',until()).catch(e=>e.message);
  const inbound=c.receiveRequest(()=>true,until()).catch(e=>e.message);
  if(mode==='close')c.close();
  if(mode==='disconnect'){s.readyState=3;s.emit('close',{})}
  if(mode==='error')s.emit('error',{});
  if(mode==='bad')s.emit('message',{data:'{bad}'});
  if(mode==='binary')s.emit('message',{data:Buffer.from('{}')});
  if(mode==='oversize')s.emit('message',{data:' '.repeat(513)});
  if(mode==='closing-context'){s.readyState=2;result.context=c.context('t','u',1000);}
  if(mode==='concurrent-send-error'||mode==='concurrent-not-open'){
   if(mode==='concurrent-send-error')s.throwSend=true;else s.readyState=2;
   try{await c.transport.notify('initialized',{},until())}catch(e){result.failure=e.message}
  }
  result.rpc=await rpc;result.terminal=await terminal;result.inbound=await inbound;
  result.listenersBeforeClose={message:s.listenerCount('message'),close:s.listenerCount('close'),error:s.listenerCount('error')};
 }
 c.close();result.sent=s.sent;result.closes=s.closes;
 result.listeners={message:s.listenerCount('message'),close:s.listenerCount('close'),error:s.listenerCount('error')};
 console.log(JSON.stringify(result));
})().catch(error=>{console.error(error);process.exitCode=1});
'''


class CodexConnectionTests(unittest.TestCase):
    def websocket_case(self, mode):
        result = subprocess.run([shutil.which('node'), '-e', WEBSOCKET_SCENARIO, str(MODULE), mode],
                                capture_output=True, text=True, encoding='utf-8', timeout=5)
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(result.stdout)

    def test_websocket_reuses_rpc_context_and_proposal_with_whole_json_messages(self):
        result = self.websocket_case('success')
        self.assertEqual(result['context']['state'], 'window-observed')
        self.assertIn('turn/completed', result['events'])
        self.assertEqual(result['terminal']['params']['turn']['status'], 'completed')
        self.assertEqual(result['sent'][1]['id'], 9)
        self.assertEqual(result['closes'], 0)
        self.assertEqual(result['listeners'], {'message': 1, 'close': 0, 'error': 0})

    def test_websocket_failure_or_close_rejects_pending_work_and_releases_only_owned_listeners(self):
        for mode in ('close', 'disconnect', 'error', 'bad', 'binary', 'oversize', 'closing-context',
                     'concurrent-send-error', 'concurrent-not-open'):
            with self.subTest(mode=mode):
                result = self.websocket_case(mode)
                self.assertIsInstance(result['rpc'], str)
                self.assertIsInstance(result['terminal'], str)
                self.assertIsInstance(result['inbound'], str)
                self.assertEqual(result['closes'], 0)
                self.assertEqual(result['listenersBeforeClose'], {'message': 1, 'close': 0, 'error': 0})
                self.assertEqual(result['listeners'], {'message': 1, 'close': 0, 'error': 0})
                if mode == 'closing-context':
                    self.assertEqual(result['context']['state'], 'unknown')

    def test_websocket_rejects_unavailable_capacity_and_send_failure_without_retry(self):
        for mode in ('buffer', 'unknown-buffer', 'send-error'):
            with self.subTest(mode=mode):
                result = self.websocket_case(mode)
                self.assertIn('buffer' if mode != 'send-error' else 'send failed', result['error'])
                self.assertEqual(result['sent'], [])
                self.assertEqual(result['closes'], 0)
        result = self.websocket_case('not-open')
        self.assertIn('already-open', result['error'])
        self.assertEqual(result['listeners'], 1)

    def run_case(self, case, journal=None):
        command = [shutil.which('node'), '-e', NODE_SCENARIO, str(MODULE), '' if journal is None else str(journal), case]
        result = subprocess.run(command, capture_output=True, text=True, encoding='utf-8', timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(result.stdout)

    def test_owned_transport_anchor_replay_response_and_terminal(self):
        result = self.run_case('success')
        self.assertEqual(result['got'], ['item/completed', 'turn/completed'])
        self.assertEqual(result['context']['state'], 'window-observed')
        self.assertEqual(result['term']['params']['turn']['status'], 'completed')
        self.assertEqual(len(result['writes']), 3)
        self.assertIn('accord-owned:1', result['writes'][0])
        self.assertIn('"method":"initialized"', result['writes'][1])
        self.assertIn('"id":9', result['writes'][2])
        self.assertIn('not available', result['duplicate'])

    def test_timeout_and_eof_become_unknown_without_writes(self):
        result = self.run_case('timeout')
        self.assertIn('deadline exceeded', result['timeout'])
        self.assertEqual(result['broken'], 'native-connection-unavailable')

    def test_invalid_frame_breaks_connection(self):
        result = self.run_case('bad')
        self.assertEqual(result['reason'], 'native-connection-unavailable')

    def test_context_requires_an_unevicted_native_model_response(self):
        result = self.run_case('context-missing')
        self.assertEqual(result['reason'], 'thread-model-response-unavailable')

    def test_evicted_anchor_cannot_be_replayed(self):
        result = self.run_case('evict', 256)
        self.assertEqual(result['error'], 'proposal anchor is unavailable')

    def test_close_detaches_without_destroying_injected_streams(self):
        result = self.run_case('close')
        self.assertFalse(result['destroyed'])
        self.assertFalse(result['writeEnded'])

    def test_close_rejects_pending_rpc_and_terminal_without_leaving_waiters(self):
        result = self.run_case('close-pending')
        self.assertIn('owned connection is closed', result['rpc'])
        self.assertIn('owned connection is closed', result['terminal'])

    def test_stdin_error_and_invalid_deadline_are_rejected(self):
        result = self.run_case('stdin-error')
        self.assertIn('write failed', result['error'])
        self.assertIn('deadline is invalid', result['invalid'])

    def test_expired_calls_do_not_write_even_before_the_timer_turn(self):
        result = self.run_case('expired')
        self.assertEqual(result['writes'], 0)
        self.assertIn('deadline exceeded', result['request'])
        self.assertIn('deadline exceeded', result['notify'])

    def test_each_failed_rpc_keeps_its_own_frozen_request_reference(self):
        result=self.run_case('rpc-error-reference')
        sent=[json.loads(line) for line in result['requests']]
        self.assertEqual(len(result['errors']),2)
        for error, request in zip(result['errors'],sent):
            self.assertEqual(error['reference'],{'connectionId':'c1','hostVersion':'v1',
                'requestId':request['id'],'method':request['method']})
            self.assertTrue(error['frozen'])
        self.assertNotEqual(result['errors'][0]['reference']['requestId'],
                            result['errors'][1]['reference']['requestId'])

    def test_bad_frame_detaches_owned_listeners(self):
        self.assertEqual(self.run_case('bad-cleanup'), {'data': 0, 'end': 0, 'stdinError': 0})

    def test_options_mutation_cannot_reroute_the_bound_stream(self):
        self.assertEqual(self.run_case('stream-replacement'), {'original': 1, 'foreign': 0})

    def test_live_listener_failure_breaks_connection_without_crashing_host(self):
        self.assertEqual(self.run_case('listener-error'), {'reason': 'native-connection-unavailable', 'attached': 0})

    def test_expired_unsent_response_can_be_reconciled_before_a_single_send(self):
        result = self.run_case('expired-reply')
        self.assertEqual((result['before'], result['after']), (0, 1))
        self.assertIn('deadline', result['expired'])

    def test_null_error_is_not_a_successful_result(self):
        self.assertIn('native RPC returned an error', self.run_case('null-error')['error'])

    def test_oversize_single_chunk_fails_before_frame_accumulation(self):
        self.assertEqual(self.run_case('oversize'), {'reason': 'native-connection-unavailable', 'attached': 0})

    def test_context_tool_replies_once_using_native_request_identity(self):
        result = self.run_case('context-tool-known')
        observation = result['payload']['observation']
        self.assertEqual(observation['conditions']['threadId'], 't')
        self.assertEqual(observation['conditions']['model'], 'native-model')
        self.assertEqual(observation['windowTokens'], 1000)
        self.assertFalse(observation['sourceReleaseAllowed'])
        self.assertTrue(result['response']['result']['success'])
        self.assertEqual((result['sent'], result['totalAfter']), (1, 1))

    def test_context_tool_preserves_absent_signals_as_unknown(self):
        result = self.run_case('context-tool-unknown')
        self.assertEqual(result['payload']['observation']['state'], 'unknown')
        self.assertTrue(result['response']['result']['success'])
        self.assertEqual(result['sent'], 1)

    def test_context_arguments_cannot_override_identity_or_request_a_negative_age(self):
        for scenario in ('context-tool-override', 'context-tool-invalid-age'):
            with self.subTest(scenario=scenario):
                result = self.run_case(scenario)
                self.assertFalse(result['response']['result']['success'])
                self.assertEqual(result['payload']['observation']['reason'], 'invalid-context-arguments')
                self.assertNotIn('conditions', result['payload']['observation'])

    def test_context_tool_does_not_answer_an_unrelated_namespace(self):
        result = self.run_case('context-tool-namespace')
        self.assertEqual(result['sent'], 0)
        self.assertIn('exact owned context request', result['error'])
