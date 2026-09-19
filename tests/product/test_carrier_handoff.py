"""Native-method sequencing and failure invariants; no model or account calls."""
import json
from pathlib import Path
import shutil
import subprocess
import sys
import os
import time
import hashlib
import queue
import threading
import sqlite3
import secrets
import unittest

ROOT = Path(__file__).resolve().parents[2]
DRIVER = Path(__file__).with_name('carrier_handoff_host.cjs')
PROPOSAL_TOOL = 'accord_request_handoff'


class CarrierHandoffTests(unittest.TestCase):
    def run_case(self, scenario='success', **options):
        result = subprocess.run([shutil.which('node'), str(DRIVER)],
            input=json.dumps({'scenario':scenario, **options})+'\n', capture_output=True,
            text=True, encoding='utf-8', timeout=15)
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(result.stdout)

    def test_success_proves_continuation_before_releasing_only_source_subscription(self):
        r=self.run_case()
        self.assertIsNone(r['error'])
        self.assertEqual(r['result']['status'],'handed-off')
        self.assertEqual(r['result']['writer'],'target')
        self.assertTrue(r['result']['sourceRecoveryRetained'])
        self.assertTrue(r['result']['sourceSubscriptionReleased'])
        self.assertIsNone(r['result']['sourceUnloaded'])
        methods=[c['method'] for c in r['calls']]
        self.assertEqual(methods.count('thread/start'),1)
        self.assertEqual(methods.count('turn/start'),2)
        self.assertLess(max(i for i,m in enumerate(methods) if m=='waitTerminal'),methods.index('thread/unsubscribe'))
        start=next(c['params'] for c in r['calls'] if c['method']=='thread/start')
        self.assertIs(start['ephemeral'],False)
        self.assertEqual(start['sandbox'],'read-only')
        self.assertEqual(start['approvalPolicy'],'never')
        self.assertFalse(any(m in methods for m in ('thread/fork','thread/archive','thread/delete','thread/goal/set')))

    def test_active_source_must_reach_exact_terminal_before_fresh_target(self):
        r=self.run_case('active-source')
        self.assertIsNone(r['error'])
        methods=[c['method'] for c in r['calls']]
        self.assertLess(methods.index('turn/interrupt'),methods.index('waitTerminal'))
        self.assertLess(methods.index('waitTerminal'),methods.index('thread/start'))

    def test_history_retention_uses_current_native_metadata_not_generic_recovery(self):
        for scenario, expected in (('success', True), ('ephemeral-source', False),
                                   ('unknown-persistence', None), ('persistence-not-reobserved', None)):
            with self.subTest(scenario=scenario):
                r=self.run_case(scenario)
                self.assertIsNone(r['error'])
                self.assertIs(r['result']['source']['nativeHistoryRetained'], expected)
                self.assertIs(r['result']['sourceRecovery']['nativeHistoryRetained'], expected)
                self.assertIs(r['snapshots'][-1]['nativeHistoryRetained'], expected)
                self.assertEqual(r['snapshots'][-1]['sourceRecovery'], 'retained')
                self.assertTrue(r['result']['sourceRecoveryRetained'])

    def test_conflicting_source_persistence_requires_reconciliation_before_release(self):
        r=self.run_case('source-persistence-changed')
        self.assertIsNotNone(r['error'])
        self.assertFalse(any(c['method'] in ('thread/start','thread/unsubscribe') for c in r['calls']))

    def test_unknown_denied_or_partial_results_never_release_source(self):
        for scenario in ('duplicate','wrong-source','wrong-authority','same-target','ambiguous-start',
                         'invalid-settings','reject-intake','changed-authority','ambiguous-commit',
                         'wait-timeout','wrong-terminal','continuation-failed','missing-effects'):
            with self.subTest(scenario=scenario):
                r=self.run_case(scenario)
                self.assertIsNotNone(r['error'])
                self.assertFalse(any(c['method']=='thread/unsubscribe' for c in r['calls']))
                self.assertLessEqual(sum(c['method']=='thread/start' for c in r['calls']),1)
                if scenario in ('duplicate','wrong-source','wrong-authority'):
                    self.assertFalse(any(c['method']=='thread/start' for c in r['calls']))
                if scenario in ('invalid-settings','same-target'):
                    self.assertFalse(any(c['method']=='turn/start' for c in r['calls']))
                if scenario in ('ambiguous-commit','changed-authority'):
                    self.assertEqual(sum(c['method']=='turn/start' for c in r['calls']),1)

    def test_input_mutation_during_callback_cannot_redirect_target(self):
        r=self.run_case('mutate-plan')
        self.assertIsNone(r['error'])
        start=next(c['params'] for c in r['calls'] if c['method']=='thread/start')
        self.assertEqual(start['cwd'],'/bound-workspace')
        intake=next(c['params'] for c in r['calls'] if c['method']=='turn/start')
        self.assertNotEqual(intake['input'],[{'type':'text','text':'changed'}])

    def test_late_cas_or_changed_binding_cannot_trigger_recovery_effects(self):
        for scenario in ('late-cas-active','malformed-cas-active','connection-drift'):
            with self.subTest(scenario=scenario):
                r=self.run_case(scenario, beforeContinuationDelayMs=200 if scenario=='late-cas-active' else 0)
                self.assertIsNotNone(r['error'])
                self.assertTrue(r['error']['reconciliationRequired'])
                self.assertFalse(any(c['method'] in ('turn/interrupt','thread/unsubscribe') for c in r['calls']))
                if scenario in ('late-cas-active','malformed-cas-active'):
                    self.assertEqual(r['snapshots'][-1]['phase'],'continuation-started')
                if scenario == 'late-cas-active':
                    self.assertEqual(r['error']['code'],'RECORDER_COMMIT_UNKNOWN')

    def test_unknown_begin_cannot_be_treated_as_a_fresh_retry(self):
        for scenario in ('duplicate','bad-begin','begin-null'):
            with self.subTest(scenario=scenario):
                r=self.run_case(scenario)
                self.assertTrue(r['error']['reconciliationRequired'])
                self.assertEqual(r['calls'],[])

    def test_failed_terminal_is_not_interrupted_again_and_unknown_is_not_success(self):
        r=self.run_case('continuation-failed')
        self.assertIsNotNone(r['error'])
        self.assertFalse(any(c['method']=='turn/interrupt' for c in r['calls']))
        for scenario in ('unknown-terminal','reused-turn','invalid-unsubscribe'):
            with self.subTest(scenario=scenario):
                r=self.run_case(scenario)
                self.assertIsNotNone(r['error'])
                self.assertIsNone(r['result'])

    def test_durable_plan_and_unknown_effect_survive_missing_continuation_ack(self):
        r=self.run_case('lost-continuation-ack')
        self.assertIsNotNone(r['error'])
        self.assertIn('handoffText',r['snapshots'][0]['plan'])
        self.assertIn('continuation',r['snapshots'][0]['plan'])
        self.assertEqual(r['snapshots'][-1]['pendingEffect']['method'],'turn/start')
        self.assertIsNone(r['error']['state']['targetTurnId'])
        self.assertFalse(r['error']['state']['targetTurnTerminal'])
        self.assertFalse(any(c['method']=='turn/interrupt' for c in r['calls']))

    def test_monotonic_budget_rejects_late_callback_but_ignores_wall_clock_jump(self):
        r=self.run_case('late-verifier')
        self.assertIsNotNone(r['error'])
        self.assertFalse(any(c['method']=='thread/start' for c in r['calls']))
        r=self.run_case('clock-jump')
        self.assertIsNone(r['error'])

    def test_unreturned_verifier_is_bounded_by_the_real_timer(self):
        r=self.run_case('stalled-verifier')
        self.assertEqual(r['verdicts'], ['prepare'])
        self.assertEqual(r['error']['code'], 'VERIFIER_FAILED')
        self.assertFalse(any(c['method']=='thread/start' for c in r['calls']))

    def test_additional_intake_stays_read_only_and_requires_current_authority(self):
        r=self.run_case('extra-context')
        self.assertIsNone(r['error'])
        turns=[c['params'] for c in r['calls'] if c['method']=='turn/start']
        self.assertEqual(len(turns),3)
        self.assertTrue(all(t['sandboxPolicy']=={'type':'readOnly'} for t in turns[:2]))
        self.assertEqual(r['verdicts'].count('accepted'),2)
        r=self.run_case('bad-extra-context')
        self.assertIsNotNone(r['error'])
        self.assertEqual(sum(c['method']=='turn/start' for c in r['calls']),1)
        self.assertFalse(any(c['method']=='thread/unsubscribe' for c in r['calls']))
        r=self.run_case('reuse-first-intake')
        self.assertIsNotNone(r['error'])
        self.assertFalse(any(c['method']=='thread/unsubscribe' for c in r['calls']))

    def test_same_scope_concurrent_transfers_cannot_both_dispatch(self):
        r=self.run_case('same-scope-concurrent')
        self.assertEqual(sorted(x['status'] for x in r['concurrent']),['fulfilled','rejected'])
        self.assertEqual(sum(c['method']=='thread/start' for c in r['calls']),1)

    def test_startup_and_non_filesystem_intake_effects_need_independent_clearance(self):
        r=self.run_case('unsafe-startup')
        self.assertIsNotNone(r['error'])
        self.assertFalse(any(c['method']=='thread/start' for c in r['calls']))
        r=self.run_case('unknown-intake-effect')
        self.assertIsNotNone(r['error'])
        self.assertEqual(sum(c['method']=='turn/start' for c in r['calls']),1)
        self.assertFalse(any(c['method']=='thread/unsubscribe' for c in r['calls']))

    def test_distributed_adapter_matches_canonical_source(self):
        self.assertEqual((ROOT/'runtime/carrier-handoff.cjs').read_bytes(),
                         (ROOT/'plugins/yiyuan-accord-codex/runtime/carrier-handoff.cjs').read_bytes())

    def test_proposal_only_records_before_response_and_reuses_one_transfer(self):
        r = self.run_case('proposal-success')
        self.assertIsNone(r['error'])
        self.assertEqual(r['proposal']['callsBeforeDispatch'], [])
        self.assertEqual(r['proposal']['response']['id'], 42)
        self.assertTrue(r['proposal']['response']['result']['success'])
        queued = json.loads(r['proposal']['response']['result']['contentItems'][0]['text'])
        self.assertEqual(queued['status'], 'queued')
        self.assertEqual(queued['transferId'], 'transfer-1')
        before = r['proposal']['snapshotsBeforeDispatch'][-1]
        self.assertEqual(before['phase'], 'proposal-response-pending')
        self.assertEqual(before['writerThreadId'], 'source-1')
        self.assertEqual(r['result']['status'], 'handed-off')
        self.assertFalse(any(c['method']=='turn/interrupt' for c in r['calls']))

    def test_proposal_requires_its_exact_native_receipts_and_current_binding(self):
        for scenario in ('proposal-foreign-request', 'proposal-foreign-namespace', 'proposal-injected-authority', 'proposal-wrong-tool',
                         'proposal-wrong-turn', 'proposal-failed-tool', 'proposal-failed-source',
                         'proposal-wrong-response', 'proposal-expired', 'proposal-changed-state',
                         'proposal-connection-drift'):
            with self.subTest(scenario=scenario):
                r = self.run_case(scenario)
                self.assertIsNotNone(r['error'])
                self.assertEqual(r['calls'], [])
                if r['proposal'] and scenario!='proposal-connection-drift':
                    self.assertEqual(r['snapshots'][-1]['pendingEffect']['type'], 'tool-response')

    def test_proposal_dispatch_is_single_use(self):
        r = self.run_case('proposal-double-dispatch')
        self.assertIsNone(r['error'])
        self.assertTrue(r['proposal']['duplicateError'])
        self.assertEqual(r['proposal']['callsAfterDuplicate'], 0)


def proposal_fixture_item(body, ordinal, state):
    """Reuse the previously observed direct/Code Mode native tool shapes."""
    if not state.get('next'):
        return None
    state['next'] = False
    tools = body.get('tools', []) + [t for row in body.get('input', [])
        if row.get('type') == 'additional_tools' for t in row.get('tools', [])]
    arguments = {'reason': 'Preserve the fixed task in the already authorized fresh carrier.'}
    direct = [t for t in tools if t.get('type') == 'function' and t.get('name') == PROPOSAL_TOOL]
    if len(direct) == 1:
        return {'id':f'proposal_{ordinal}', 'type':'function_call', 'call_id':f'proposal_call_{ordinal}',
                'name':PROPOSAL_TOOL, 'arguments':json.dumps(arguments), 'status':'completed'}
    wrappers = [f for t in tools if t.get('type')=='namespace' and t.get('name')=='functions'
                for f in t.get('tools',[]) if f.get('name')=='exec']
    if len(wrappers)!=1 or PROPOSAL_TOOL not in wrappers[0].get('description',''):
        raise ValueError('prepared native proposal tool is not exposed')
    return {'id':f'proposal_{ordinal}', 'type':'custom_tool_call', 'call_id':f'proposal_call_{ordinal}',
            'namespace':'functions', 'name':'exec', 'status':'completed',
            'input':'text(await tools.'+PROPOSAL_TOOL+'('+json.dumps(arguments)+'));'}


def native_integration(codex, evidence):
    """Explicit model-free integration; reuse existing transport/fixture/jobs.

    The test controller supplies a scoped durable ledger and fixture verdicts.
    It proves protocol execution, not autonomous timing or semantic takeover.
    """
    sys.path.insert(0, str(ROOT))
    from scripts.observe_codex_lifecycle import (_App, _Fixture, _argv, _owned_environment,
        _new_controller, _spawn_options, _wait_job, _released, _remove_owned_tree, save)
    from scripts.codex_rpc import BoundedRpc
    root = Path(evidence).absolute()
    if root.exists() or not root.parent.is_dir() or root.parent.resolve() != root.parent:
        raise ValueError('fresh ordinary evidence root required')
    root.mkdir()
    for name in ('home','workspace','state','temp','native','retained'):
        (root/name).mkdir()
    node = Path(shutil.which('node')).resolve()
    codex = Path(codex).resolve(strict=True)
    if os.name=='nt' and codex.suffix.lower()!='.exe': raise ValueError('native executable required')
    (root/'workspace/keep.txt').write_bytes(b'Preserve this fixture original.\n')
    original = hashlib.sha256((root/'workspace/keep.txt').read_bytes()).hexdigest()
    version = subprocess.check_output([str(codex),'--version'],timeout=10,text=True).strip()
    manifest={'evidence':str(root),'codex':str(codex),'node':str(node),
        'ownedRoots':{name:str(root/name) for name in ('home','workspace','state','temp')},
        'limits':{'requestSeconds':30,'recoverySeconds':15,'providerRequestBytes':2*1024*1024,'providerRequests':17},
        'resourceController':'windows-job-object' if os.name=='nt' else 'posix-session-process-group'}
    sources=[ROOT/'runtime/carrier-handoff.cjs',DRIVER,Path(__file__),ROOT/'scripts/observe_codex_lifecycle.py',
             ROOT/'scripts/observe_codex_entry.py',ROOT/'scripts/codex_rpc.py',ROOT/'scripts/inspect_native_resources.py']
    manifest['sourceHashes']={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in sources}
    source_snapshot=root/'retained/executed-sources'
    source_snapshot.mkdir()
    for path in sources:
        destination=source_snapshot/path.relative_to(ROOT)
        destination.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(path,destination)
        if hashlib.sha256(destination.read_bytes()).hexdigest()!=manifest['sourceHashes'][str(path)]:
            raise ValueError('execution source changed during preparation')
    manifest['claimLimit']='Native method execution with fixed localhost replies and a test verifier; no model judgment, ordinary Desktop control, autonomous timing or whole acceptance.'
    save(root/'manifest.json',manifest)
    env=_owned_environment(manifest)
    proposal_state = {'next':False}
    fixture=_Fixture(manifest, lambda body, ordinal: proposal_fixture_item(body, ordinal, proposal_state))
    app=None
    results=[]
    owned_threads=set()
    deadline=time.monotonic()+260
    ledger_db=sqlite3.connect(root/'retained/recorder.sqlite',isolation_level=None)
    ledger_db.execute('PRAGMA synchronous=FULL')
    ledger_db.execute('CREATE TABLE scopes (scope TEXT PRIMARY KEY, owner TEXT, active TEXT, token TEXT)')
    ledger_db.execute('CREATE TABLE transfers (id TEXT PRIMARY KEY, digest TEXT, revision INTEGER, state TEXT)')
    def request(method,params,remaining_ms=None):
        allowed={'thread/read','thread/start','turn/start','turn/interrupt','thread/unsubscribe'}
        if method not in allowed: raise ValueError('method outside owned integration')
        if method!='thread/start' and params.get('threadId') not in owned_threads: raise ValueError('unowned native task')
        if remaining_ms is None:
            value=app.rpc(method,params)
        else:
            request_deadline=min(deadline,time.monotonic()+max(0,remaining_ms)/1000)
            rpc=BoundedRpc(app._send,app._receive,work_deadline=request_deadline,request_timeout=30,
                           recovery_timeout=15,on_event=app.events.append)
            value=rpc.request(method,params)
        if method=='thread/start': owned_threads.add(value['thread']['id'])
        return value
    def terminal(thread_id,turn_id,remaining_ms=None):
        limit=min(deadline,time.monotonic()+(30 if remaining_ms is None else max(0,remaining_ms)/1000))
        def matches(event):
            return (event.get('method')=='turn/completed' and event.get('params',{}).get('threadId')==thread_id
                    and event.get('params',{}).get('turn',{}).get('id')==turn_id)
        for event in app.events:
            if matches(event): return event
        while time.monotonic()<limit:
            event=app._receive(limit);app.events.append(event)
            if matches(event): return event
        raise TimeoutError('exact terminal missing before deadline')
    def source_proposal(thread_id, turn_id):
        limit = min(deadline, time.monotonic()+30)
        def matches(event):
            params = event.get('params', {})
            return (event.get('method')=='item/tool/call' and 'id' in event
                    and params.get('threadId')==thread_id and params.get('turnId')==turn_id
                    and params.get('tool')==PROPOSAL_TOOL)
        for event in app.events:
            if matches(event): return event
        while time.monotonic()<limit:
            event=app._receive(limit);app.events.append(event)
            if matches(event): return event
        raise TimeoutError('source did not submit its native proposal')
    def record_begin(transfer_id,digest,initial):
        ledger_db.execute('BEGIN IMMEDIATE')
        try:
            prior=ledger_db.execute('SELECT revision FROM transfers WHERE id=?',(transfer_id,)).fetchone()
            scope=ledger_db.execute('SELECT owner,active FROM scopes WHERE scope=?',(initial['scopeRef'],)).fetchone()
            if prior or not scope or scope[0]!=initial['source']['threadId'] or scope[1] is not None:
                ledger_db.execute('ROLLBACK');return {'created':False,'revision':prior[0] if prior else 0}
            token=secrets.token_hex(16)
            lease={'scopeRef':initial['scopeRef'],'transferId':transfer_id,'token':token,'writerThreadId':scope[0]}
            ledger_db.execute('INSERT INTO transfers VALUES (?,?,?,?)',(transfer_id,digest,0,json.dumps(initial)))
            ledger_db.execute('UPDATE scopes SET active=?,token=? WHERE scope=?',(transfer_id,token,initial['scopeRef']))
            ledger_db.execute('COMMIT')
            return {'created':True,'revision':0,'lease':lease}
        except BaseException:
            ledger_db.execute('ROLLBACK');raise
    def record_cas(transfer_id,revision,next_state,expected_lease):
        ledger_db.execute('BEGIN IMMEDIATE')
        try:
            old=ledger_db.execute('SELECT revision FROM transfers WHERE id=?',(transfer_id,)).fetchone()
            scope=ledger_db.execute('SELECT owner,active,token FROM scopes WHERE scope=?',(expected_lease['scopeRef'],)).fetchone()
            actual={'scopeRef':expected_lease['scopeRef'],'transferId':scope[1], 'token':scope[2],'writerThreadId':scope[0]} if scope else None
            if not old or old[0]!=revision or actual!=expected_lease or next_state['scopeRef']!=expected_lease['scopeRef']:
                raise RuntimeError('scope/transfer CAS conflict')
            writer=next_state['writerThreadId'];new_revision=revision+1
            ledger_db.execute('UPDATE transfers SET revision=?,state=? WHERE id=?',(new_revision,json.dumps(next_state),transfer_id))
            active=None if next_state['phase']=='source-subscription-released' else transfer_id
            ledger_db.execute('UPDATE scopes SET owner=?,active=? WHERE scope=?',(writer,active,expected_lease['scopeRef']))
            ledger_db.execute('COMMIT')
            return {'revision':new_revision,'lease':{**expected_lease,'writerThreadId':writer}}
        except BaseException:
            ledger_db.execute('ROLLBACK');raise
    try:
        app=_App(manifest,'carrier-controller',_argv(manifest,fixture,('-c','features.plugins=false','-c','features.hooks=false')),env,deadline)
        app.initialize()
        for scenario in ('success','reject-intake','extra-context','source-proposal','ephemeral-source'):
            source_settings={'model':'fixture-no-model','modelProvider':'accord_fixture',
                'cwd':manifest['ownedRoots']['workspace'],'sandbox':'read-only','approvalPolicy':'never'}
            if scenario=='ephemeral-source': source_settings['ephemeral']=True
            if scenario=='source-proposal':
                source_settings['dynamicTools']=[{'type':'function','name':PROPOSAL_TOOL,
                    'description':'Submit a handoff proposal; the controller records it before acknowledgement and dispatches after this turn ends.',
                    'inputSchema':{'type':'object','properties':{'reason':{'type':'string'}},
                                   'required':['reason'],'additionalProperties':False}}]
                proposal_state['next']=True
            source=request('thread/start',source_settings)['thread']['id']
            source_prompt = ('Submit one handoff proposal for the bound fixed task, then finish this source turn without other actions.'
                             if scenario=='source-proposal' else 'Retain the fixed fixture task; do not call tools.')
            turn=request('turn/start',{'threadId':source,'input':[{'type':'text','text':source_prompt}]})['turn']['id']
            proposed=source_proposal(source,turn) if scenario=='source-proposal' else None
            if proposed is None and terminal(source,turn)['params']['turn']['status']!='completed':
                raise RuntimeError('source fixture turn did not complete')
            now=int(time.time()*1000)
            plan={'transferId':scenario,'scopeRef':'fixture-'+scenario,'authorityRef':'fixture-authority-v1','stateRef':'fixture-source-v1',
                'source':{'threadId':source, **({'turnId':turn} if proposed else {})},'target':{'cwd':manifest['ownedRoots']['workspace'],'model':'fixture-no-model','modelProvider':'accord_fixture'},
                'handoffText':'Read-only intake of the fixed fixture task; preserve keep.txt and do not call tools.',
                'continuation':{'input':'Continue the accepted read-only fixture task; preserve keep.txt and do not call tools.','sandboxPolicy':{'type':'readOnly'}},
                'deadlineMs':now+60000,'recoveryDeadlineMs':now+75000}
            ledger=root/'retained'/f'{scenario}-ledger.json'
            ledger_db.execute('INSERT INTO scopes VALUES (?,?,NULL,NULL)',(plan['scopeRef'],source))
            intake_reviews=0
            messages=root/'retained'/f'{scenario}-bridge.jsonl'
            job=_new_controller();proc=None;reader=None;inbox=queue.Queue();result=None
            with (root/'retained'/f'{scenario}-stderr.txt').open('wb') as errors:
                try:
                    proc=subprocess.Popen([str(node),str(DRIVER)],stdin=subprocess.PIPE,stdout=subprocess.PIPE,
                        stderr=errors,cwd=ROOT,env=env,**_spawn_options())
                    job.attach_and_resume(proc)
                    def consume(stream=proc.stdout):
                        try:
                            for line in stream:
                                if len(line)>4*1024*1024: raise ValueError('bridge message too large')
                                inbox.put(json.loads(line))
                        except BaseException as error: inbox.put(error)
                        finally: inbox.put(None)
                    reader=threading.Thread(target=consume,daemon=True);reader.start()
                    binding={'connectionId':app.root.name,'hostVersion':version}
                    config={'mode':'native','plan':plan,'binding':binding}
                    if proposed is not None: config['nativeProposal']={**binding,**proposed}
                    proc.stdin.write((json.dumps(config)+'\n').encode());proc.stdin.flush()
                    while True:
                        message=inbox.get(timeout=max(0.01,min(40,deadline-time.monotonic())))
                        if message is None: raise RuntimeError('bridge exited before result')
                        if isinstance(message,BaseException): raise message
                        with messages.open('a',encoding='utf-8') as out: out.write(json.dumps(message)+'\n')
                        if message.get('kind')=='done': result=message;break
                        args=message['args']
                        try:
                            if message['kind']=='request': value=request(args[0],args[1],args[2])
                            elif message['kind']=='waitTerminal': value=terminal(args[0],args[1],args[2])
                            elif message['kind']=='begin':
                                value=record_begin(*args)
                            elif message['kind']=='compareAndSet':
                                value=record_cas(*args)
                            elif message['kind']=='proposalEvidence':
                                if proposed is None or args[0].get('id')!=proposed['id']:
                                    raise ValueError('unbound native proposal response')
                                app._send(args[0])
                                source_terminal=terminal(source,turn)
                                tool_events=[e for e in app.events if e.get('method')=='item/completed'
                                    and e.get('params',{}).get('threadId')==source
                                    and e.get('params',{}).get('turnId')==turn
                                    and e.get('params',{}).get('item',{}).get('type')=='dynamicToolCall'
                                    and e['params']['item'].get('id')==proposed['params']['callId']]
                                if len(tool_events)!=1: raise ValueError('exact native tool completion missing')
                                value={'toolCompleted':tool_events[0],'sourceTerminal':source_terminal,
                                    'current':{k:plan[k] for k in ('scopeRef','authorityRef','stateRef')}}
                                value['current']['writerThreadId']=source
                                save(root/'retained/source-proposal-receipts.json',{'request':proposed,
                                    'response':args[0], **value})
                            elif message['kind']=='verify':
                                stage,facts=args[:2]
                                unchanged=hashlib.sha256((root/'workspace/keep.txt').read_bytes()).hexdigest()==original
                                value={'decision':'allow' if unchanged else 'hold','scopeRef':plan['scopeRef'],'authorityRef':plan['authorityRef'],
                                    'stateRef':plan['stateRef'],'sourceRef':f'fixed-native-fixture:{scenario}:{stage}',
                                    'sourceRecoveryReady':True,'quiesced':True,'noOtherWriters':True,'targetSettingsMatch':True,
                                    'accepted':True,'sourceIdle':True,'singleWriter':True,'effectsVerified':unchanged}
                                value.update(targetInitializationSafe=True,initializationEffectsVerified=True,intakeEffectsVerified=unchanged)
                                if stage=='target-created':
                                    actual=facts['startResponse']
                                    value['targetSettingsMatch']=(actual.get('model')==plan['target']['model']
                                        and actual.get('cwd')==plan['target']['cwd'] and actual.get('approvalPolicy')=='never'
                                        and actual.get('sandbox',{}).get('type')=='readOnly')
                                if scenario=='reject-intake' and stage=='accepted': value['decision']='hold'
                                if stage=='accepted':
                                    intake_reviews+=1
                                    if scenario=='extra-context' and intake_reviews==1:
                                        value.update(decision='request-context',additionalInput='Additional fixed context: preserve keep.txt; no tools or writes are required.')
                                        value.pop('accepted')
                            else: raise ValueError('unknown caller operation')
                            reply={'id':message['id'],'result':value}
                        except Exception as error: reply={'id':message['id'],'error':str(error)}
                        proc.stdin.write((json.dumps(reply)+'\n').encode());proc.stdin.flush()
                    proc.stdin.close();proc.wait(timeout=15)
                    if proc.returncode: raise RuntimeError('bridge process failed')
                finally:
                    if proc is not None and proc.poll() is None: job.terminate();proc.wait(timeout=15)
                    after=_wait_job(job,time.monotonic()+15)
                    if not _released(after): job.terminate();after=_wait_job(job,time.monotonic()+5)
                    save(root/'retained'/f'{scenario}-resources.json',{'exitCode':proc.returncode if proc else None,'after':after,'released':_released(after)})
                    job.close()
                    if reader: reader.join(2)
                    if reader and reader.is_alive(): raise RuntimeError('bridge reader still alive')
                    if proc and proc.stdout: proc.stdout.close()
            if result is None: raise RuntimeError('missing adapter result')
            stored=ledger_db.execute('SELECT revision,state FROM transfers WHERE id=?',(scenario,)).fetchone()
            if stored: save(ledger,{'revision':stored[0],'state':json.loads(stored[1])})
            save(root/'retained'/f'{scenario}-result.json',result);results.append(result)
            if scenario in ('success','extra-context','source-proposal','ephemeral-source'):
                if result['error'] or result['result']['status']!='handed-off':
                    raise RuntimeError('native handoff failed; inspect retained result')
                expected_history=scenario!='ephemeral-source'
                if (result['result']['source']['nativeHistoryRetained'] is not expected_history
                        or result['result']['sourceRecovery']['nativeHistoryRetained'] is not expected_history):
                    raise RuntimeError('source history claim differs from native persistence')
            if scenario=='reject-intake' and (result['error'] is None or any(c['method']=='thread/unsubscribe' for c in result['calls'])): raise RuntimeError('rejected intake released source')
    finally:
        try:
            if app: save(root/'controller-resources.json',app.close())
        finally:
            fixture.close()
            ledger_db.close()
        if (root/'home/sessions').exists(): shutil.copytree(root/'home/sessions',root/'retained/native-sessions')
        save(root/'poststate.json',{'providerRequests':len(fixture.requests),'credentialsObserved':fixture.auth_seen,
            'keepPreserved':hashlib.sha256((root/'workspace/keep.txt').read_bytes()).hexdigest()==original,
            'completedCases':len(results),'claimLimit':manifest['claimLimit']})
    if fixture.auth_seen or len(results)!=5: raise RuntimeError('native integration incomplete')
    for name in ('home','workspace','state','temp'):
        target=(root/name).resolve(strict=True)
        if target.parent!=root: raise ValueError('owned cleanup root mismatch')
        _remove_owned_tree(target)
    save(root/'cleanup.json',{'ownedRootsRemoved':True,'nativeSessionEvidenceRetained':True})
    print(json.dumps({'nativeCases':5,'modelCalls':0,'providerRequests':len(fixture.requests),'evidence':str(root)}))


if __name__=='__main__':
    if '--native-codex' in sys.argv:
        import argparse
        p=argparse.ArgumentParser();p.add_argument('--native-codex',required=True);p.add_argument('--evidence',required=True)
        a=p.parse_args();native_integration(a.native_codex,a.evidence)
    else: unittest.main()
