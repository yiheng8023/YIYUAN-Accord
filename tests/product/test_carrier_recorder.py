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


if __name__ == "__main__":
    unittest.main()
