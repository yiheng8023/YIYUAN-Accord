import base64
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import tempfile
import textwrap
import unittest


ROOT = Path(__file__).resolve().parents[2]
RECORDER = ROOT / "runtime" / "carrier-recorder.cjs"
PLUGIN_RECORDER = ROOT / "plugins" / "yiyuan-accord-codex" / "runtime" / "carrier-recorder.cjs"


RUNNER = r"""
'use strict';
const fs = require('node:fs');
const request = JSON.parse(Buffer.from(process.argv[2], 'base64').toString('utf8'));
const {openCarrierRecorder} = require(request.module);
function reply(value) { process.stdout.write(JSON.stringify({ok: true, value})); }
try {
  if (request.action === 'create') {
    const recorder = openCarrierRecorder({path: request.path, create: true, busyTimeoutMs: 3000});
    const value = recorder.bindScope(request.scopeRef, request.writerThreadId);
    recorder.close(); reply(value);
  } else if (request.action === 'open') {
    const recorder = openCarrierRecorder({path: request.path, busyTimeoutMs: 3000});
    recorder.close(); reply({opened: true});
  } else if (request.action === 'bind') {
    const recorder = openCarrierRecorder({path: request.path, busyTimeoutMs: 3000});
    const value = recorder.bindScope(request.scopeRef, request.writerThreadId);
    recorder.close(); reply(value);
  } else if (request.action === 'scope') {
    const recorder = openCarrierRecorder({path: request.path, busyTimeoutMs: 3000});
    const value = recorder.readScope(request.scopeRef);
    recorder.close(); reply(value);
  } else if (request.action === 'claim' || request.action === 'waitClaim') {
    if (request.action === 'waitClaim') {
      const until = Date.now() + 5000;
      while (!fs.existsSync(request.gate) && Date.now() < until) {
        Atomics.wait(new Int32Array(new SharedArrayBuffer(4)), 0, 0, 10);
      }
      if (!fs.existsSync(request.gate)) throw new Error('gate timeout');
    }
    const recorder = openCarrierRecorder({path: request.path, busyTimeoutMs: 3000});
    const value = recorder.claimScope(request.scopeRef, request.expectedScope);
    recorder.close(); reply(value);
  } else if (request.action === 'begin' || request.action === 'waitBegin') {
    if (request.action === 'waitBegin') {
      const until = Date.now() + 5000;
      while (!fs.existsSync(request.gate) && Date.now() < until) {
        Atomics.wait(new Int32Array(new SharedArrayBuffer(4)), 0, 0, 10);
      }
      if (!fs.existsSync(request.gate)) throw new Error('gate timeout');
    }
    const recorder = openCarrierRecorder({path: request.path, busyTimeoutMs: 3000});
    const value = recorder.begin(request.transferId, request.planDigest, request.state);
    recorder.close(); reply(value);
  } else if (request.action === 'read') {
    const recorder = openCarrierRecorder({path: request.path, busyTimeoutMs: 3000});
    const value = recorder.read(request.transferId, request.scopeRef);
    recorder.close(); reply(value);
  } else if (request.action === 'cas') {
    const recorder = openCarrierRecorder({path: request.path, busyTimeoutMs: 3000});
    const value = recorder.compareAndSet(
      request.transferId, request.revision, request.state, request.lease,
    );
    recorder.close(); reply(value);
  } else if (['settleFailed', 'waitSettleFailed', 'failSettlement'].includes(request.action)) {
    if (request.action === 'waitSettleFailed') {
      const until = Date.now() + 5000;
      while (!fs.existsSync(request.gate) && Date.now() < until) {
        Atomics.wait(new Int32Array(new SharedArrayBuffer(4)), 0, 0, 10);
      }
      if (!fs.existsSync(request.gate)) throw new Error('gate timeout');
    }
    const recorder = openCarrierRecorder({path: request.path, busyTimeoutMs: 3000});
    if (request.action === 'failSettlement') {
      // Install after opening, then fail the second statement in the actual
      // transaction. Remove this test-only trigger before reopen validation.
      const {DatabaseSync} = require('node:sqlite');
      const fault = new DatabaseSync(request.path);
      fault.exec("CREATE TRIGGER fail_scope_update BEFORE UPDATE ON scopes BEGIN SELECT RAISE(ABORT, 'fixture scope fault'); END");
      let error;
      try { recorder.settleFailedTransfer(request.transferId, request.revision, request.lease, request.receipt); }
      catch (e) { error = {code: e.code, message: e.message}; }
      finally {fault.exec('DROP TRIGGER fail_scope_update');fault.close();recorder.close();}
      reply({error});
    } else {
      const value = recorder.settleFailedTransfer(request.transferId, request.revision, request.lease, request.receipt);
      recorder.close(); reply(value);
    }
  } else if (request.action === 'settle') {
    const recorder = openCarrierRecorder({path: request.path, busyTimeoutMs: 3000});
    const value = recorder.settle(request.transferId, request.revision, request.lease);
    recorder.close(); reply(value);
  } else if (request.action === 'churn') {
    const until = Date.now() + 5000;
    while (!fs.existsSync(request.gate) && Date.now() < until) {
      Atomics.wait(new Int32Array(new SharedArrayBuffer(4)), 0, 0, 10);
    }
    const recorder = openCarrierRecorder({path: request.path, busyTimeoutMs: 3000});
    let snapshot = recorder.read(request.transferId, request.scopeRef);
    for (let index = 0; index < request.count; index += 1) {
      const state = {...snapshot.state, phase: `concurrent-${index}`};
      const committed = recorder.compareAndSet(
        request.transferId, snapshot.revision, state, snapshot.lease,
      );
      snapshot = {revision: committed.revision, state, lease: committed.lease};
      Atomics.wait(new Int32Array(new SharedArrayBuffer(4)), 0, 0, 1);
    }
    recorder.close(); reply({revision: snapshot.revision});
  } else if (request.action === 'observeMany') {
    const until = Date.now() + 5000;
    while (!fs.existsSync(request.gate) && Date.now() < until) {
      Atomics.wait(new Int32Array(new SharedArrayBuffer(4)), 0, 0, 10);
    }
    let revision = -1;
    for (let index = 0; index < request.count; index += 1) {
      const recorder = openCarrierRecorder({path: request.path, busyTimeoutMs: 3000});
      revision = recorder.read(request.transferId, request.scopeRef).revision;
      recorder.close();
      Atomics.wait(new Int32Array(new SharedArrayBuffer(4)), 0, 0, 1);
    }
    reply({revision});
  } else if (request.action === 'rawCrash') {
    const {DatabaseSync} = require('node:sqlite');
    const database = new DatabaseSync(request.path, {timeout: 3000, allowExtension: false});
    database.exec('BEGIN IMMEDIATE');
    database.prepare('UPDATE transfers SET revision = ? WHERE transfer_id = ?').run(
      request.revision, request.transferId,
    );
    process.exit(17);
  } else {
    throw new Error('unknown action');
  }
} catch (error) {
  process.stdout.write(JSON.stringify({
    ok: false, code: error.code || null, name: error.name, message: error.message,
  }));
}
"""


class CarrierRecorderTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="accord-carrier-recorder-")
        self.root = Path(self.temp.name)
        self.runner = self.root / "runner.cjs"
        self.runner.write_text(textwrap.dedent(RUNNER), encoding="utf-8")
        self.db = self.root / "recorder.sqlite"

    def tearDown(self):
        self.temp.cleanup()

    def test_initialization_owns_statements_and_failed_close_is_not_idempotent_success(self):
        script = r"""
const assert=require('node:assert/strict'),path=require('node:path'),sqlite=require('node:sqlite');
const Real=sqlite.DatabaseSync,api=require(process.argv[1]),rows=[];
for(const mode of ['scope','transfer','scope-close','validation-close','retry-close','normal']){
 const file=path.join(process.argv[2],mode+'.sqlite');
 const seed=api.openCarrierRecorder({path:file,create:true});seed.close();
 const handles=[],errors=[];
 class Controlled extends Real{
  constructor(file,options){super(file,options);this.readonly=options.readOnly===true;this.calls=0;this.closed=false;handles.push(this);}
  prepare(sql){
   if(mode==='validation-close'&&this.readonly)throw Object.assign(Error('validation fixture'),{code:'INJECTED_VALIDATION'});
   if(!this.readonly&&((mode.startsWith('scope')&&sql.endsWith('FROM scopes WHERE scope_ref = ?'))||
      (mode==='transfer'&&sql.endsWith('FROM transfers WHERE transfer_id = ?'))))
    throw Object.assign(Error('statement fixture'),{code:'STATEMENT_FAILED'});
   return super.prepare(sql);
  }
  close(){this.calls++;
   if((mode==='scope-close'&&!this.readonly)||(mode==='validation-close'&&this.readonly)||
      (mode==='retry-close'&&!this.readonly&&this.calls===1))
    throw Object.assign(Error('secret close detail'),{code:'CLOSE_FAILED'});
   super.close();this.closed=true;
  }
 }
 sqlite.DatabaseSync=Controlled;
 try{
  let recorder;
  try{recorder=api.openCarrierRecorder({path:file});}catch(e){errors.push({code:e.code,cleanup:e.recorderCleanup});}
  if(recorder)for(let i=0;i<3;i++){try{recorder.close();}catch(e){errors.push({code:e.code});}}
  const states=handles.map(x=>({readonly:x.readonly,calls:x.calls,closed:x.closed}));
  rows.push({mode,errors,states});
 }finally{
  sqlite.DatabaseSync=Real;
  for(const db of handles)if(!db.closed){Real.prototype.close.call(db);db.closed=true;}
  assert(handles.every(db=>db.closed));
 }
}
console.log(JSON.stringify(rows));
"""
        for index, module in enumerate((RECORDER, PLUGIN_RECORDER)):
            with self.subTest(module=module):
                directory = self.root / str(index); directory.mkdir()
                run = subprocess.run(['node', '-e', script, str(module), str(directory)],
                                     capture_output=True, text=True, encoding='utf-8', timeout=15)
                self.assertEqual(run.returncode, 0, run.stderr)
                for row in json.loads(run.stdout):
                    with self.subTest(mode=row['mode']):
                        states, errors = row['states'], row['errors']
                        self.assertEqual(states[-1]['calls'], 2 if row['mode']=='retry-close' else 1, row)
                        if row['mode'] in ('scope-close', 'validation-close'):
                            self.assertFalse(states[-1]['closed'], row)
                            self.assertEqual(errors[0]['cleanup'], {'state':'close-unverified','code':'CLOSE_FAILED'})
                        else:
                            self.assertTrue(states[-1]['closed'], row)
                        expected = {'scope':'STATEMENT_FAILED','transfer':'STATEMENT_FAILED',
                                    'scope-close':'STATEMENT_FAILED','validation-close':'DATABASE_INVALID',
                                    'retry-close':'CLOSE_FAILED'}
                        self.assertEqual([e['code'] for e in errors], [] if row['mode']=='normal' else [expected[row['mode']]], row)

    def request(self, action, *, check=True, module=RECORDER, **values):
        request = {"action": action, "module": str(module), **values}
        encoded = base64.b64encode(json.dumps(request).encode()).decode()
        completed = subprocess.run(
            ["node", str(self.runner), encoded], cwd=ROOT, text=True,
            capture_output=True, timeout=15, check=False,
        )
        if check:
            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertTrue(completed.stdout, completed.stderr)
            result = json.loads(completed.stdout)
            self.assertTrue(result["ok"], result)
            return result["value"]
        return completed

    def encoded_request(self, action, **values):
        request = {"action": action, "module": str(RECORDER), **values}
        return base64.b64encode(json.dumps(request).encode()).decode()

    @staticmethod
    def initial(transfer, scope="scope-a", writer="source", digest=None):
        digest = digest or f"digest-{transfer}"
        return {
            "phase": "prepared",
            "transferId": transfer,
            "planDigest": digest,
            "scopeRef": scope,
            "writer": "source",
            "writerThreadId": writer,
            "sourceRecovery": "retained",
            "source": {"threadId": writer},
            "target": None,
            "continuationTurn": None,
            "pendingEffect": None,
        }

    def create(self, scope="scope-a", writer="source"):
        return self.request(
            "create", path=str(self.db), scopeRef=scope, writerThreadId=writer,
        )

    def test_optional_sqlite_unavailable_keeps_entry_usable_and_files_unchanged(self):
        plugin_checkpoint = PLUGIN_RECORDER.with_name("task-checkpoint.cjs")
        missing = self.root / "not-created.sqlite"
        self.db.write_bytes(b"retained input, not a database")
        before = {path.name: path.read_bytes() for path in self.root.iterdir()}
        script = r"""
const [recorderPath, checkpointPath, missingPath, retainedPath, mode] = process.argv.slice(1);
const Module = require('node:module');
const load = Module._load;
let sqliteRequests = 0;
Module._load = function (id, ...args) {
  if (id === 'node:sqlite') {
    sqliteRequests += 1;
    if (mode === 'missing-export') return {};
    throw Object.assign(new Error('fixture: SQLite unavailable'), {code: 'ERR_UNKNOWN_BUILTIN_MODULE'});
  }
  return load.call(this, id, ...args);
};
const {openCarrierRecorder} = require(recorderPath);
const guidance = require(checkpointPath).entryGuidance();
const entrySqliteRequests = sqliteRequests;
const codes = [];
for (const [path, create] of [[missingPath, true], [retainedPath, false]]) {
  try { openCarrierRecorder({path, create}); codes.push('unexpected-success'); }
  catch (error) { codes.push(error.code); }
}
process.stdout.write(JSON.stringify({guidancePresent: Boolean(guidance), entrySqliteRequests, codes}));
"""
        for module in (RECORDER, PLUGIN_RECORDER):
            for mode in ("missing-module", "missing-export"):
                with self.subTest(module=module, mode=mode):
                    completed = subprocess.run(
                        ["node", "-e", script, str(module), str(plugin_checkpoint),
                         str(missing), str(self.db), mode],
                        cwd=ROOT, text=True, capture_output=True, timeout=15,
                    )
                    self.assertEqual(completed.returncode, 0, completed.stderr)
                    self.assertEqual(json.loads(completed.stdout), {
                        "guidancePresent": True, "entrySqliteRequests": 0,
                        "codes": ["SQLITE_UNAVAILABLE", "SQLITE_UNAVAILABLE"],
                    })
                    self.assertEqual(
                        {path.name: path.read_bytes() for path in self.root.iterdir()}, before,
                    )

    def test_two_processes_compete_for_one_scope(self):
        self.assertTrue(self.create()["created"])
        gate = self.root / "start.gate"
        requests = []
        processes = []
        for transfer in ("transfer-one", "transfer-two"):
            state = self.initial(transfer)
            encoded = self.encoded_request(
                "waitBegin", path=str(self.db), gate=str(gate), transferId=transfer,
                planDigest=state["planDigest"], state=state,
            )
            process = subprocess.Popen(
                ["node", str(self.runner), encoded], cwd=ROOT, text=True,
                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            )
            processes.append(process)
            requests.append(transfer)
        gate.write_text("go", encoding="ascii")
        results = []
        for process in processes:
            stdout, stderr = process.communicate(timeout=15)
            self.assertEqual(process.returncode, 0, stderr)
            results.append(json.loads(stdout))
        self.assertTrue(all(result["ok"] for result in results), results)
        created = [result["value"] for result in results if result["value"]["created"]]
        rejected = [result["value"] for result in results if not result["value"]["created"]]
        self.assertEqual(len(created), 1)
        self.assertEqual(len(rejected), 1)
        self.assertEqual(rejected[0], {"created": False, "revision": 0})
        scope = self.request("scope", path=str(self.db), scopeRef="scope-a")
        self.assertIn(scope["activeTransferId"], requests)
        self.assertEqual(scope["writerThreadId"], "source")

    def test_two_processes_claim_one_inactive_scope_only_once(self):
        self.create()
        expected = self.request("scope", path=str(self.db), scopeRef="scope-a")
        gate = self.root / "claim.gate"
        processes = []
        for _ in range(2):
            encoded = self.encoded_request(
                "waitClaim", path=str(self.db), gate=str(gate),
                scopeRef="scope-a", expectedScope=expected,
            )
            processes.append(subprocess.Popen(
                ["node", str(self.runner), encoded], cwd=ROOT, text=True,
                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            ))
        gate.write_text("go", encoding="ascii")
        results = []
        for process in processes:
            stdout, stderr = process.communicate(timeout=15)
            self.assertEqual(process.returncode, 0, stderr)
            results.append(json.loads(stdout))
        successes = [result["value"] for result in results if result["ok"]]
        conflicts = [result for result in results if not result["ok"]]
        self.assertEqual(len(successes), 1, results)
        self.assertEqual(len(conflicts), 1, results)
        self.assertEqual(conflicts[0]["code"], "CLAIM_CONFLICT")
        claimed = successes[0]["scope"]
        self.assertEqual(claimed["scopeRef"], expected["scopeRef"])
        self.assertEqual(claimed["writerThreadId"], expected["writerThreadId"])
        self.assertIsNone(claimed["activeTransferId"])
        self.assertNotEqual(claimed["token"], expected["token"])
        reopened = self.request("scope", path=str(self.db), scopeRef="scope-a")
        self.assertEqual(reopened, claimed)
        stale = self.request(
            "claim", check=False, path=str(self.db), scopeRef="scope-a",
            expectedScope=expected,
        )
        self.assertEqual(json.loads(stale.stdout)["code"], "CLAIM_CONFLICT")

    def test_claim_requires_the_exact_inactive_scope_snapshot(self):
        self.create()
        expected = self.request("scope", path=str(self.db), scopeRef="scope-a")
        cases = (
            ({**expected, "writerThreadId": "other"}, "CLAIM_CONFLICT"),
            ({**expected, "activeTransferId": "transfer"}, None),
            ({**expected, "extra": True}, None),
        )
        for candidate, code in cases:
            with self.subTest(candidate=candidate):
                rejected = self.request(
                    "claim", check=False, path=str(self.db), scopeRef="scope-a",
                    expectedScope=candidate,
                )
                result = json.loads(rejected.stdout)
                self.assertFalse(result["ok"])
                self.assertEqual(result["code"], code)
                if code is None:
                    self.assertEqual(result["name"], "TypeError")
                self.assertEqual(
                    self.request("scope", path=str(self.db), scopeRef="scope-a"), expected,
                )

    def test_claim_refuses_active_transfer_and_preserves_settled_history(self):
        self.create()
        initial_scope = self.request("scope", path=str(self.db), scopeRef="scope-a")
        active_state = self.initial("transfer-active")
        active = self.request(
            "begin", path=str(self.db), transferId="transfer-active",
            planDigest=active_state["planDigest"], state=active_state,
        )
        rejected = self.request(
            "claim", check=False, path=str(self.db), scopeRef="scope-a",
            expectedScope=initial_scope,
        )
        self.assertEqual(json.loads(rejected.stdout)["code"], "SCOPE_BUSY")
        self.assertEqual(
            self.request("scope", path=str(self.db), scopeRef="scope-a"),
            {"scopeRef": "scope-a", "writerThreadId": "source",
             "activeTransferId": "transfer-active", "token": active["lease"]["token"]},
        )

        transferred = {
            **active_state, "phase": "source-subscription-released", "writer": "target",
            "writerThreadId": "target", "target": {"threadId": "target"},
            "continuationTurn": {"threadId": "target", "turnId": "turn-1"},
            "pendingEffect": None, "verification": {"release": "evidence-release"},
            "subscriptionRelease": {"threadId": "source", "observed": True},
        }
        committed = self.request(
            "cas", path=str(self.db), transferId="transfer-active", revision=0,
            state=transferred, lease=active["lease"],
        )
        settled = self.request(
            "settle", path=str(self.db), transferId="transfer-active",
            revision=committed["revision"], lease=committed["lease"],
        )
        history_before = self.request(
            "read", path=str(self.db), transferId="transfer-active", scopeRef="scope-a",
        )
        claimed = self.request(
            "claim", path=str(self.db), scopeRef="scope-a", expectedScope=settled["scope"],
        )["scope"]
        history_after = self.request(
            "read", path=str(self.db), transferId="transfer-active", scopeRef="scope-a",
        )
        self.assertEqual(claimed["writerThreadId"], "target")
        self.assertIsNone(claimed["activeTransferId"])
        self.assertNotEqual(claimed["token"], settled["scope"]["token"])
        self.assertEqual(history_after["revision"], history_before["revision"])
        self.assertEqual(history_after["state"], history_before["state"])
        self.assertEqual(history_after["lease"], {
            "scopeRef": "scope-a", "transferId": None,
            "token": claimed["token"], "writerThreadId": "target",
        })

    def failed_basis(self):
        self.create()
        state = {**self.initial('failed-transfer'), 'phase': 'held', 'failure': {
            'code': 'VERIFICATION_DENIED', 'stage': 'prepare', 'writerTransferred': False,
            'targetThreadId': None, 'targetTurnId': None, 'targetTurnTerminal': False}}
        begun = self.request('begin', path=str(self.db), transferId=state['transferId'],
                             planDigest=state['planDigest'], state=state)
        # Storage-contract fixture only; native effect verification is tested by
        # FailedTransferRecoveryTests using actual handoff execution.
        receipt = {'kind': 'failed-transfer', 'originalPhase': state['phase'],
            'originalFailure': state['failure'], 'originalPendingEffect': None,
            'connection': {'connectionId': 'fixture', 'hostVersion': 'fixture'},
            'sourceReadDigest': 'a' * 64, 'targetReadDigest': None,
            'verificationSourceRef': 'fixture:verification',
            'evidenceRefs': dict.fromkeys(('priorAttempt', 'effects', 'sourceRecovery', 'target'), 'fixture:storage')}
        return state, begun, receipt

    def test_failed_settlement_validates_receipt_and_rolls_back_both_rows_on_fault(self):
        state, begun, receipt = self.failed_basis()
        before = self.request('read', path=str(self.db), transferId=state['transferId'], scopeRef='scope-a')
        scope = self.request('scope', path=str(self.db), scopeRef='scope-a')
        invalid = ({**receipt, 'originalPhase': 'fabricated'},
                   {**receipt, 'originalFailure': {**state['failure'], 'stage': 'different'}},
                   {**receipt, 'originalPendingEffect': {'method': 'turn/start'}},
                   {**receipt, 'sourceReadDigest': 'invalid'},
                   {**receipt, 'evidenceRefs': {**receipt['evidenceRefs'], 'effects': ''}})
        for candidate in invalid:
            with self.subTest(candidate=candidate):
                rejected = self.request('settleFailed', check=False, path=str(self.db),
                    transferId=state['transferId'], revision=begun['revision'], lease=begun['lease'], receipt=candidate)
                self.assertFalse(json.loads(rejected.stdout)['ok'])
                self.assertEqual(self.request('read', path=str(self.db), transferId=state['transferId'], scopeRef='scope-a'), before)
                self.assertEqual(self.request('scope', path=str(self.db), scopeRef='scope-a'), scope)
        fault = self.request('failSettlement', path=str(self.db), transferId=state['transferId'],
                            revision=begun['revision'], lease=begun['lease'], receipt=receipt)
        self.assertIn('fixture scope fault', fault['error']['message'])
        self.assertEqual(self.request('read', path=str(self.db), transferId=state['transferId'], scopeRef='scope-a'), before)
        self.assertEqual(self.request('scope', path=str(self.db), scopeRef='scope-a'), scope)
        connection = sqlite3.connect(self.db)
        try:
            self.assertEqual(connection.execute('SELECT settled FROM transfers').fetchone()[0], 0)
        finally:
            connection.close()

    def test_two_processes_close_one_failed_source_lease_only_once(self):
        state, begun, receipt = self.failed_basis()
        gate = self.root / 'failed-settlement.gate'
        encoded = self.encoded_request('waitSettleFailed', path=str(self.db), gate=str(gate),
            transferId=state['transferId'], revision=begun['revision'], lease=begun['lease'], receipt=receipt)
        processes = [subprocess.Popen(['node', str(self.runner), encoded], cwd=ROOT, text=True,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE) for _ in range(2)]
        gate.write_text('go', encoding='ascii')
        results = []
        for process in processes:
            stdout, stderr = process.communicate(timeout=15)
            self.assertEqual(process.returncode, 0, stderr)
            results.append(json.loads(stdout))
        self.assertEqual(sum(result['ok'] for result in results), 1, results)
        self.assertEqual(next(r for r in results if not r['ok'])['code'], 'CAS_CONFLICT')
        winner = next(r['value'] for r in results if r['ok'])
        self.assertEqual(winner['scope']['writerThreadId'], 'source')
        self.assertIsNone(winner['scope']['activeTransferId'])
        self.assertNotEqual(winner['scope']['token'], begun['lease']['token'])
        reopened = self.request('read', path=str(self.db), transferId=state['transferId'], scopeRef='scope-a')
        self.assertEqual(reopened['state']['failure'], state['failure'])
        self.assertEqual(reopened['state']['failedReconciliation'], receipt)
        self.assertEqual(reopened['revision'], begun['revision'] + 1)
        rebound = self.request('claim', path=str(self.db), scopeRef='scope-a', expectedScope=winner['scope'])
        self.assertNotEqual(rebound['scope']['token'], winner['scope']['token'])

    def test_cas_fences_stale_revision_and_lease_and_reopens(self):
        self.create()
        initial = self.initial("transfer-a")
        begun = self.request(
            "begin", path=str(self.db), transferId="transfer-a",
            planDigest=initial["planDigest"], state=initial,
        )
        next_state = {**initial, "phase": "writer-transferred", "writer": "target",
                      "writerThreadId": "target", "target": {"threadId": "target"}}
        committed = self.request(
            "cas", path=str(self.db), transferId="transfer-a", revision=0,
            state=next_state, lease=begun["lease"],
        )
        stale_revision = self.request(
            "cas", check=False, path=str(self.db), transferId="transfer-a", revision=0,
            state=next_state, lease=begun["lease"],
        )
        stale_revision_result = json.loads(stale_revision.stdout)
        self.assertFalse(stale_revision_result["ok"])
        self.assertEqual(stale_revision_result["code"], "CAS_CONFLICT")
        stale_lease = self.request(
            "cas", check=False, path=str(self.db), transferId="transfer-a",
            revision=committed["revision"], state=next_state, lease=begun["lease"],
        )
        self.assertEqual(json.loads(stale_lease.stdout)["code"], "CAS_CONFLICT")
        reopened = self.request(
            "read", path=str(self.db), transferId="transfer-a", scopeRef="scope-a",
        )
        self.assertEqual(reopened["revision"], committed["revision"])
        self.assertEqual(reopened["state"], next_state)
        self.assertEqual(reopened["lease"], committed["lease"])

    def test_crash_with_uncommitted_sqlite_transaction_keeps_prior_state(self):
        self.create()
        initial = self.initial("transfer-crash")
        begun = self.request(
            "begin", path=str(self.db), transferId="transfer-crash",
            planDigest=initial["planDigest"], state=initial,
        )
        committed_state = {**initial, "phase": "target-created"}
        committed = self.request(
            "cas", path=str(self.db), transferId="transfer-crash", revision=0,
            state=committed_state, lease=begun["lease"],
        )
        crashed = self.request(
            "rawCrash", check=False, path=str(self.db), transferId="transfer-crash",
            revision=999,
        )
        self.assertEqual(crashed.returncode, 17, crashed.stderr)
        reopened = self.request(
            "read", path=str(self.db), transferId="transfer-crash", scopeRef="scope-a",
        )
        self.assertEqual(reopened["revision"], committed["revision"])
        self.assertEqual(reopened["state"], committed_state)

    def test_concurrent_reopen_observes_only_atomic_cas_snapshots(self):
        self.create()
        initial = self.initial("transfer-concurrent")
        self.request(
            "begin", path=str(self.db), transferId="transfer-concurrent",
            planDigest=initial["planDigest"], state=initial,
        )
        gate = self.root / "validation.gate"
        processes = []
        for action in ("churn", "observeMany"):
            encoded = self.encoded_request(
                action, path=str(self.db), gate=str(gate), count=80,
                transferId="transfer-concurrent", scopeRef="scope-a",
            )
            processes.append(subprocess.Popen(
                ["node", str(self.runner), encoded], cwd=ROOT, text=True,
                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            ))
        gate.write_text("go", encoding="ascii")
        results = []
        for process in processes:
            stdout, stderr = process.communicate(timeout=20)
            self.assertEqual(process.returncode, 0, stderr)
            results.append(json.loads(stdout))
        self.assertTrue(all(result["ok"] for result in results), results)
        final = self.request(
            "read", path=str(self.db), transferId="transfer-concurrent", scopeRef="scope-a",
        )
        self.assertEqual(final["revision"], 80)

    def test_settle_requires_complete_shape_then_allows_next_transfer(self):
        self.create()
        initial = self.initial("transfer-first")
        begun = self.request(
            "begin", path=str(self.db), transferId="transfer-first",
            planDigest=initial["planDigest"], state=initial,
        )
        pending = {
            **initial, "phase": "release-authorized", "writer": "target",
            "writerThreadId": "target", "target": {"threadId": "target"},
            "continuationTurn": {"threadId": "target", "turnId": "turn-1"},
            "pendingEffect": {"method": "thread/unsubscribe"},
            "verification": {"release": "evidence-release"},
        }
        pending_commit = self.request(
            "cas", path=str(self.db), transferId="transfer-first", revision=0,
            state=pending, lease=begun["lease"],
        )
        rejected = self.request(
            "settle", check=False, path=str(self.db), transferId="transfer-first",
            revision=pending_commit["revision"], lease=pending_commit["lease"],
        )
        self.assertEqual(json.loads(rejected.stdout)["code"], "TRANSFER_NOT_SETTLEABLE")
        complete = {
            **pending, "phase": "source-subscription-released", "pendingEffect": None,
            "subscriptionRelease": {"threadId": "source", "observed": True},
        }
        final_commit = self.request(
            "cas", path=str(self.db), transferId="transfer-first",
            revision=pending_commit["revision"], state=complete,
            lease=pending_commit["lease"],
        )
        settled = self.request(
            "settle", path=str(self.db), transferId="transfer-first",
            revision=final_commit["revision"], lease=final_commit["lease"],
        )
        self.assertGreater(settled["revision"], final_commit["revision"])
        self.assertIsNone(settled["scope"]["activeTransferId"])
        self.assertEqual(settled["scope"]["writerThreadId"], "target")
        self.assertNotEqual(settled["scope"]["token"], final_commit["lease"]["token"])
        rebound = self.request(
            "bind", path=str(self.db), scopeRef="scope-a", writerThreadId="target",
        )
        self.assertFalse(rebound["created"])
        second = self.initial("transfer-second", writer="target")
        next_begin = self.request(
            "begin", path=str(self.db), transferId="transfer-second",
            planDigest=second["planDigest"], state=second,
        )
        self.assertTrue(next_begin["created"])
        stale = self.request(
            "cas", check=False, path=str(self.db), transferId="transfer-first",
            revision=final_commit["revision"], state=complete,
            lease=final_commit["lease"],
        )
        self.assertEqual(json.loads(stale.stdout)["code"], "CAS_CONFLICT")
        old = self.request(
            "read", path=str(self.db), transferId="transfer-first", scopeRef="scope-a",
        )
        self.assertEqual(old["state"], complete)
        self.assertEqual(old["lease"], next_begin["lease"])

    def test_unknown_corrupt_and_linked_databases_are_rejected_without_repair(self):
        unknown = self.root / "unknown.sqlite"
        connection = sqlite3.connect(unknown)
        connection.execute("CREATE TABLE unrelated(value TEXT)")
        connection.execute("INSERT INTO unrelated VALUES ('preserve-me')")
        connection.commit()
        connection.close()
        before = hashlib.sha256(unknown.read_bytes()).digest()
        result = self.request("open", check=False, path=str(unknown))
        self.assertEqual(json.loads(result.stdout)["code"], "SCHEMA_UNKNOWN")
        self.assertEqual(hashlib.sha256(unknown.read_bytes()).digest(), before)

        corrupt = self.root / "corrupt.sqlite"
        corrupt.write_bytes(b"not a sqlite database\x00preserve")
        before = hashlib.sha256(corrupt.read_bytes()).digest()
        result = self.request("open", check=False, path=str(corrupt))
        self.assertEqual(json.loads(result.stdout)["code"], "DATABASE_INVALID")
        self.assertEqual(hashlib.sha256(corrupt.read_bytes()).digest(), before)

        invalid_rows = self.root / "invalid-rows.sqlite"
        self.request(
            "create", path=str(invalid_rows), scopeRef="scope-invalid",
            writerThreadId="source",
        )
        connection = sqlite3.connect(invalid_rows)
        connection.execute(
            "UPDATE scopes SET fence_token = '' WHERE scope_ref = 'scope-invalid'"
        )
        connection.commit()
        connection.close()
        result = self.request("open", check=False, path=str(invalid_rows))
        self.assertEqual(json.loads(result.stdout)["code"], "CORRUPT_RECORD")
        moved = self.root / "invalid-rows-moved.sqlite"
        os.replace(invalid_rows, moved)
        self.assertTrue(moved.is_file())

        self.create()
        linked = self.root / "linked.sqlite"
        os.link(self.db, linked)
        before = hashlib.sha256(self.db.read_bytes()).digest()
        result = self.request("open", check=False, path=str(linked))
        self.assertEqual(json.loads(result.stdout)["code"], "DATABASE_PATH_UNSAFE")
        self.assertEqual(hashlib.sha256(self.db.read_bytes()).digest(), before)

    def test_create_is_exclusive_and_distribution_copy_is_identical(self):
        self.create()
        result = self.request(
            "create", check=False, path=str(self.db), scopeRef="scope-a",
            writerThreadId="source",
        )
        self.assertEqual(json.loads(result.stdout)["code"], "DATABASE_EXISTS")
        self.assertEqual(RECORDER.read_bytes(), PLUGIN_RECORDER.read_bytes())


class ExternalTargetSettlementTests(unittest.TestCase):
    def test_typed_target_settlement_is_atomic_fenced_and_preserves_history(self):
        script = r'''
const {openCarrierRecorder}=require(process.argv[1]);
const {DatabaseSync}=require('node:sqlite');
const crypto=require('node:crypto'),mode=process.argv[3];
const sourceIntake=mode.startsWith('source-intake');
const hash=x=>crypto.createHash('sha256').update(JSON.stringify(x)).digest('hex');
const source={kind:'codex-mcp-request-metadata',threadId:'source',sessionTreeId:'source',turnId:'old-turn',callId:'old-call'};
const scopeBinding={requestedScope:'bounded-work',cwd:process.cwd(),sourceThreadId:'source'};
scopeBinding.scopeRef=hash({threadId:'source',cwd:scopeBinding.cwd,scope:scopeBinding.requestedScope});
const plan={scopeRef:scopeBinding.scopeRef,cwd:process.cwd(),deadlineMs:100,intake:'Read the fixed intake without changing the task.'},basis={epoch:'old'};
const closed={closed:true,primaryProcessClosed:true,exitObserved:true,closeObserved:true,exitCode:0,
 forced:false,signal:null,pid:12345,recoveryRequired:false,terminationAttempt:null}; // Fixture facts, not a live process claim.
const r=openCarrierRecorder({path:process.argv[2],create:true});r.bindScope(scopeBinding.scopeRef,'source');
const initial={kind:'external-source-handoff/v1',transferId:'transfer',scopeRef:scopeBinding.scopeRef,plan,source,basis,
 planDigest:hash({plan,source,basis}),writer:'source',writerThreadId:'source',phase:'prepared'};
const begun=r.begin('transfer',initial.planDigest,initial);
const pending={kind:'native-request',method:'turn/start',params:{threadId:'target'},
 requestRef:{connectionId:'owned-connection',method:'turn/start',requestId:'missing-ack'}};
const state={...initial,phase:'held',writer:'target',writerThreadId:'target',target:{threadId:'target'},
 connection:{connectionId:'owned-connection',hostVersion:'fixture'},turnStarts:2,sourceRecovery:'retained',
 failure:{code:'ACK_LOST',priorPhase:'writer-transferred'},pendingEffect:pending,nativeClosed:{...closed}};
if(sourceIntake){
 Object.assign(state,{phase:'cancelled-held',writer:'source',writerThreadId:'source',turnStarts:1,pendingEffect:null,
  failure:{code:'execution-stopped',cancelReason:'User paused the fixed attempt.',closureError:null,priorPhase:'awaiting-intake-review'},
  intake:{threadId:'target',turnId:'intake-turn',terminal:'completed',output:'Fixed intake completed.',observedAfterRelease:false,
   events:[{method:'item/completed',threadId:'target',turnId:'intake-turn',itemType:'agentMessage'}]},
  lastNativeReceipt:{method:'turn/start',response:{turn:{id:'intake-turn'}},request:{kind:'native-request',sequence:1,method:'turn/start',
   params:{threadId:'target',input:[{type:'text',text:plan.intake}],sandboxPolicy:{type:'readOnly'}},
   requestRef:{connectionId:'owned-connection',hostVersion:'fixture',method:'turn/start',requestId:'intake-request'}}}});
 if(mode==='source-intake-wrong-thread')state.intake.threadId='other-target';
 if(mode==='source-intake-wrong-turn')state.intake.turnId='other-turn';
 if(mode==='source-intake-missing-receipt')delete state.lastNativeReceipt;
 if(mode==='source-intake-wrong-receipt-method')state.lastNativeReceipt.method='thread/start';
 if(mode==='source-intake-wrong-request-method')state.lastNativeReceipt.request.method='thread/start';
 if(mode==='source-intake-wrong-receipt-thread')state.lastNativeReceipt.request.params.threadId='other-target';
 if(mode==='source-intake-wrong-receipt-turn')state.lastNativeReceipt.response.turn.id='other-turn';
 if(mode==='source-intake-wrong-connection')state.lastNativeReceipt.request.requestRef.connectionId='other-connection';
 if(mode==='source-intake-wrong-host-version')state.lastNativeReceipt.request.requestRef.hostVersion='other-version';
 if(mode==='source-intake-wrong-policy')state.lastNativeReceipt.request.params.sandboxPolicy={type:'workspaceWrite'};
 if(mode==='source-intake-extra-turn')state.turnStarts=2;
 if(mode==='source-intake-pending')state.pendingEffect={kind:'native-turn',threadId:'target',turnId:'intake-turn',purpose:'intake'};
 if(mode==='source-intake-first-continuation')state.firstContinuation={threadId:'target',turnId:'business-turn',terminal:'completed'};
 if(mode==='source-intake-stopped-turn')state.stoppedTurn={threadId:'target',turnId:'business-turn',purpose:'first-continuation',terminal:'interrupted'};
 if(mode==='source-intake-post-release')state.postReleaseTurn={threadId:'target',turnId:'business-turn',terminal:'completed'};
 if(mode==='source-intake-release')state.release={kind:'cooperative-duty-release',sourceThreadId:'source'};
 if(mode==='source-intake-committed')state.verification={commit:'fixture-prior-commit'};
 if(mode==='source-intake-incomplete-terminal')state.intake.terminal='interrupted';
 if(mode==='source-intake-wrong-phase')state.failure.priorPhase='writer-transferred';
}
if(mode==='forced')state.nativeClosed.forced=true;
if(mode==='unknown-resource')state.nativeClosed.closeObserved=false;
const moved=r.compareAndSet('transfer',begun.revision,state,begun.lease);
let exact=r.read('transfer',scopeBinding.scopeRef);
const receipt={kind:'external-known-stopped-target',recordRevision:exact.revision,recordSha256:hash(exact.state),leaseSha256:hash(exact.lease),
 originalDeadlineMs:100,originalFailure:state.failure,currentSource:{...source,turnId:'new-turn',callId:'new-call'},
 currentBasis:{epoch:'new',revision:2,authorityRef:'current-authority',snapshotRef:'a'.repeat(64),protectedInputsDigest:'b'.repeat(64),inputComplete:true,paused:false,recoveryRequired:false},
 decision:'allow',sourceRef:'independent-effect-actor-authority-judgment',writerDisposition:['retain','source-intake-retain'].includes(mode)?'target-retained':'source-current',
 scopeBinding,readerClosed:closed,observationSha256:'c'.repeat(64),decisionEvidence:'d'.repeat(64),materialSha256:'e'.repeat(64),nativeFactsSha256:'f'.repeat(64),
 originalStateEvidence:hash(exact.state),recoveryDeadlineMs:Date.now()+10000};
if(mode==='wrong-source')receipt.currentSource.threadId='other';
if(mode==='expired')receipt.recoveryDeadlineMs=Date.now()-1;
if(mode==='stale')r.compareAndSet('transfer',exact.revision,exact.state,exact.lease);
let fault;
if(mode==='atomic-fault'){fault=new DatabaseSync(process.argv[2]);fault.exec("CREATE TRIGGER fail_target_scope BEFORE UPDATE ON scopes BEGIN SELECT RAISE(ABORT,'fixed failure'); END");}
const beforeSettlement=r.read('transfer',scopeBinding.scopeRef);
let result=null,error=null;
try{result=r.settleExternalStoppedTarget('transfer',exact.revision,exact.lease,receipt);}catch(e){error={code:e.code||null,message:e.message};}
if(fault){fault.exec('DROP TRIGGER fail_target_scope');fault.close();}
const after=r.read('transfer',scopeBinding.scopeRef);let staleWrite=null;
try{r.compareAndSet('transfer',exact.revision,exact.state,exact.lease);}catch(e){staleWrite=e.code;}
console.log(JSON.stringify({mode,result,error,before:exact,beforeSettlement,after,staleWrite}));r.close();
'''
        with tempfile.TemporaryDirectory(prefix='accord-target-settlement-') as directory:
            modes = (
                'source', 'retain', 'stale', 'wrong-source', 'expired', 'forced', 'unknown-resource', 'atomic-fault',
                'source-intake', 'source-intake-retain', 'source-intake-wrong-thread', 'source-intake-wrong-turn',
                'source-intake-missing-receipt', 'source-intake-wrong-receipt-method',
                'source-intake-wrong-request-method', 'source-intake-wrong-receipt-thread',
                'source-intake-wrong-receipt-turn', 'source-intake-wrong-connection',
                'source-intake-wrong-host-version', 'source-intake-wrong-policy',
                'source-intake-extra-turn', 'source-intake-pending', 'source-intake-first-continuation',
                'source-intake-stopped-turn', 'source-intake-post-release', 'source-intake-release',
                'source-intake-committed', 'source-intake-incomplete-terminal',
                'source-intake-wrong-phase',
            )
            for mode in modes:
                with self.subTest(mode=mode):
                    run = subprocess.run(['node', '-e', script, str(PLUGIN_RECORDER),
                        str(Path(directory)/(mode+'.sqlite')), mode], cwd=ROOT, text=True,
                        encoding='utf-8', capture_output=True, timeout=10)
                    self.assertEqual(run.returncode, 0, run.stderr)
                    result = json.loads(run.stdout)
                    if mode in ('source', 'retain', 'source-intake'):
                        self.assertIsNone(result['error'])
                        self.assertEqual(result['after']['state']['phase'], 'external-target-reconciled')
                        self.assertEqual(result['after']['lease']['writerThreadId'], 'target' if mode=='retain' else 'source')
                        self.assertIsNone(result['after']['lease']['transferId'])
                        self.assertNotEqual(result['after']['lease']['token'], result['before']['lease']['token'])
                        self.assertEqual(result['after']['state']['failure'], result['before']['state']['failure'])
                        self.assertEqual(result['after']['state']['plan']['deadlineMs'], 100)
                        self.assertEqual(result['after']['state']['reconciliation']['originalPendingEffect'], result['before']['state']['pendingEffect'])
                        self.assertEqual(result['staleWrite'], 'CAS_CONFLICT')
                        if mode == 'source-intake':
                            self.assertEqual(result['after']['state']['intake'], result['before']['state']['intake'])
                            self.assertEqual(result['after']['state']['reconciliation']['originalPhase'], 'cancelled-held')
                            self.assertEqual(result['after']['state']['reconciliation']['originalSourceRecovery'], 'retained')
                            for key in ('firstContinuation', 'postReleaseTurn', 'release'):
                                self.assertNotIn(key, result['after']['state'])
                    else:
                        self.assertIsNotNone(result['error'])
                        self.assertEqual(result['after']['state'], result['beforeSettlement']['state'])
                        self.assertEqual(result['after']['lease'], result['beforeSettlement']['lease'])
                        self.assertEqual(result['after']['lease']['transferId'], 'transfer')
                        if mode.startswith('source-intake'):
                            self.assertEqual(result['error']['code'], 'EXTERNAL_TARGET_NOT_SETTLEABLE')
                        self.assertEqual(result['after']['revision'], result['beforeSettlement']['revision'])


if __name__ == "__main__":
    unittest.main()
