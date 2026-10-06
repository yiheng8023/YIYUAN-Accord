"""Native-method sequencing and failure invariants; no model or account calls."""
import json
from pathlib import Path, PurePosixPath, PureWindowsPath
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
import re
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
DRIVER = Path(__file__).with_name('carrier_handoff_host.cjs')
PROPOSAL_TOOL = 'accord_request_handoff'


def _shared_config_observation():
    configured=os.environ.get('CODEX_HOME')
    path=(Path(configured) if configured else Path.home()/'.codex')/'config.toml'
    if not path.exists(): return {'path':str(path),'present':False}
    if not path.is_file() or path.is_symlink(): raise ValueError('shared config is not an ordinary file')
    return {'path':str(path),'present':True,'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
            'size':path.stat().st_size}


class CarrierHandoffTests(unittest.TestCase):
    def run_case(self, scenario='success', **options):
        result = subprocess.run([shutil.which('node'), str(DRIVER)],
            input=json.dumps({'scenario':scenario, **options})+'\n', capture_output=True,
            text=True, encoding='utf-8', timeout=15)
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(result.stdout)

    def recovery_case(self, mode):
        return self.run_case('lost-continuation-ack',reconcile=mode,rpcFailureRef={
            'connectionId':'test-connection','hostVersion':'fixture-host',
            'requestId':'original-continuation-request','method':'turn/start'})['reconciled']

    def finalization_case(self, mode):
        return self.run_case('lost-continuation-ack', reconcile='success', finalize=mode,
            rpcFailureRef={'connectionId':'test-connection','hostVersion':'fixture-host',
                           'requestId':'original-continuation-request','method':'turn/start'})['reconciled']

    def test_recovery_reconciles_one_completed_effect_and_retains_failure_evidence(self):
        r=self.recovery_case('success')
        self.assertEqual(r['first']['result']['status'],'continuation-reconciled')
        self.assertEqual(r['second']['result']['status'],'already-reconciled')
        self.assertFalse(r['second']['result']['currentNativeStateChecked'])
        self.assertEqual((r['commits'],r['checks']), (1,1))
        self.assertEqual([c['method'] for c in r['calls']],['thread/read'])
        self.assertEqual(r['state']['writerThreadId'],r['originalState']['writerThreadId'])
        self.assertIsNone(r['state']['pendingEffect'])
        self.assertEqual(r['state']['reconciliation']['originalPendingEffect'],r['originalState']['pendingEffect'])
        self.assertEqual(r['state']['reconciliation']['originalFailure'],r['originalState']['failure'])
        for key in ['sourceReleaseAllowed','continuationAllowed']:
            self.assertFalse(r['first']['result'][key])

    def test_recovery_holds_conflicting_identity_current_state_and_missing_verification(self):
        modes=['foreign-request','foreign-response','foreign-scope','wrong-writer','wrong-phase',
               'altered-plan','intake-reused','extra-turn','wrong-input','failed-turn','active-target',
               'effectsVerified','priorAttemptQuiesced','receiptVerified','reconciliationAuthorized','binding-drift']
        for mode in modes:
            with self.subTest(mode=mode):
                r=self.recovery_case(mode)
                self.assertIn('error',r['first'])
                self.assertEqual(r['commits'],0)
                self.assertIsNotNone(r['state']['pendingEffect'])
                self.assertTrue(all(c['method']=='thread/read' for c in r['calls']))

    def test_recovery_unknown_commit_is_not_replayed_and_readback_catches_false_receipts(self):
        for mode in ['race','false-ack','readback-changed','foreign-lease']:
            with self.subTest(mode=mode):
                r=self.recovery_case(mode)
                self.assertEqual(r['first']['error']['code'],'RECORDER_COMMIT_UNKNOWN')
                self.assertEqual(r['commits'],1)
                self.assertEqual(len(r['calls']),1)
        r=self.recovery_case('lost-cas-ack')
        self.assertEqual(r['first']['error']['code'],'RECORDER_COMMIT_UNKNOWN')
        self.assertEqual(r['second']['result']['status'],'already-reconciled')
        self.assertEqual((r['commits'],len(r['calls'])),(1,1))
        r=self.recovery_case('rotate-lease')
        self.assertEqual(r['first']['result']['lease']['token'],'rotated-token')
        self.assertEqual(self.recovery_case('idle-target')['first']['result']['status'],'continuation-reconciled')
        r=self.recovery_case('different-receipt')
        self.assertEqual(r['first']['result']['status'],'continuation-reconciled')
        self.assertIn('error',r['second'])
        self.assertEqual(r['commits'],1)
        for mode in ['corrupt-missing-digest','corrupt-digest','corrupt-connection','corrupt-extra','corrupt-turn']:
            with self.subTest(mode=mode):
                r=self.recovery_case(mode)
                self.assertEqual(r['first']['result']['status'],'continuation-reconciled')
                self.assertIn('error',r['second'])
                self.assertEqual((r['commits'],len(r['calls'])),(1,1))

    def test_reconciled_cross_controller_release_records_closed_prior_connection_without_unsubscribe(self):
        result=self.finalization_case('cross')
        final=result['finalized']['first']['result']
        self.assertEqual(final['status'],'finalized')
        self.assertEqual(final['subscriptionRelease']['kind'],'prior-controller-closed')
        self.assertIsNone(final['subscriptionRelease']['nativeStatus'])
        self.assertTrue(final['sourceSubscriptionReleased'])
        self.assertFalse(any(call['method']=='thread/unsubscribe' for call in result['calls']))
        self.assertEqual(result['state']['phase'],'source-subscription-released')
        self.assertIsNone(result['state']['pendingEffect'])
        self.assertEqual(result['state']['expectedLease'],result['state']['observedLease'])
        self.assertEqual(final['settle']['revision'],result['revision'])
        ephemeral=self.finalization_case('cross-ephemeral')
        self.assertTrue(ephemeral['state']['sourceEphemeral'])
        self.assertFalse(ephemeral['state']['nativeHistoryRetained'])

    def test_same_source_connection_records_each_native_unsubscribe_status_once(self):
        for mode,status in [('same','unsubscribed'),('same-not-subscribed','notSubscribed'),
                            ('same-not-loaded','notLoaded')]:
            with self.subTest(mode=mode):
                result=self.finalization_case(mode)
                final=result['finalized']['first']['result']
                self.assertEqual(final['subscriptionRelease']['kind'],'native-unsubscribe')
                self.assertEqual(final['subscriptionRelease']['nativeStatus'],status)
                self.assertEqual(sum(c['method']=='thread/unsubscribe' for c in result['calls']),1)
                self.assertEqual(result['state']['verification']['release'],
                                 'independent-native-release-receipt')

    def test_release_authorization_rejects_missing_prior_or_reconciliation_controller_evidence(self):
        denied=self.finalization_case('cross-denied')
        self.assertEqual(denied['finalized']['first']['error']['code'],'VERIFICATION_DENIED')
        self.assertEqual(denied['state']['phase'],'continuation-reconciled')
        third=self.finalization_case('third-missing')
        self.assertEqual(third['finalized']['first']['error']['code'],'VERIFICATION_DENIED')
        allowed=self.finalization_case('third-proven')
        self.assertEqual(allowed['finalized']['first']['result']['status'],'finalized')

    def test_unknown_or_unrecognized_unsubscribe_is_never_replayed(self):
        unknown=self.finalization_case('same-unknown')
        self.assertEqual(unknown['finalized']['first']['error']['code'],'NATIVE_EFFECT_UNKNOWN')
        self.assertEqual(unknown['finalized']['second']['result']['status'],'finalized')
        self.assertEqual(sum(c['method']=='thread/unsubscribe' for c in unknown['calls']),1)
        pending=unknown['finalized']['afterFirst']['state']['pendingEffect']
        self.assertEqual(pending['requestRef']['method'],'thread/unsubscribe')
        self.assertEqual(unknown['finalized']['afterFirst']['state']['failure']['code'],
                         'NATIVE_EFFECT_UNKNOWN')
        self.assertEqual(unknown['state']['subscriptionRelease']['evidenceRef'],
                         'recovered-native-unsubscribe-receipt')
        held=self.finalization_case('same-invalid')
        self.assertEqual(held['finalized']['first']['error']['code'],'SOURCE_RELEASE_UNVERIFIED')
        self.assertEqual(held['finalized']['second']['result']['status'],'finalized')
        self.assertEqual(sum(c['method']=='thread/unsubscribe' for c in held['calls']),1)
        cross=self.finalization_case('same-unknown-cross')
        self.assertEqual(cross['finalized']['first']['error']['code'],'NATIVE_EFFECT_UNKNOWN')
        self.assertEqual(cross['finalized']['second']['result']['status'],'finalized')
        self.assertEqual(sum(c['method']=='thread/unsubscribe' for c in cross['calls']),1)
        release=cross['state']['subscriptionRelease']
        self.assertEqual(release['kind'],'prior-controller-closed')
        self.assertEqual(release['originalIntentKind'],'native-unsubscribe')
        self.assertIsNone(release['nativeStatus'])
        denied=self.finalization_case('same-unknown-cross-denied')
        self.assertEqual(denied['finalized']['second']['error']['code'],'VERIFICATION_DENIED')
        self.assertEqual(sum(c['method']=='thread/unsubscribe' for c in denied['calls']),1)

    FORBIDDEN_RECOVERY_METHODS = ('thread/unsubscribe','turn/start','thread/resume',
                                  'thread/archive','thread/delete')

    def assert_recovery_never_replays(self, calls):
        methods=[c['method'] for c in calls]
        self.assertFalse(any(m in self.FORBIDDEN_RECOVERY_METHODS for m in methods), methods)
        return methods

    def release_failure_record(self, result):
        return [s for s in result['snapshots']
                if s.get('phase') == 'release-authorized' and s.get('failure')][-1]

    def test_release_unknown_failure_preserves_original_materials_then_finalizes(self):
        r=self.run_case('release-unknown-status', releaseRecovery='observed-status')
        self.assertEqual(r['error']['code'],'UNSUBSCRIBE_OUTCOME_UNKNOWN')
        last=self.release_failure_record(r)
        self.assertEqual(last['phase'],'release-authorized')
        self.assertEqual(last['writer'],'target')
        self.assertEqual(last['releaseIntent'],{'kind':'native-unsubscribe',
            'threadId':'source-1','sourceConnectionId':'test-connection',
            'currentConnectionId':'test-connection'})
        self.assertNotIn('receiptDigest',last['releaseIntent'])
        self.assertEqual(last['releaseObservation'],
            {'response':{'status':'notSubscribed','nativeRequestId':'unsub-1'},
             'nativeStatus':'notSubscribed','requestRef':None})
        self.assertEqual(last['failure']['stage'],'release:source-unsubscribe')
        self.assertEqual(last['failure']['originalError']['code'],'UNSUBSCRIBE_OUTCOME_UNKNOWN')
        attempt=last['normalReleaseAttempt']
        self.assertEqual(attempt['request'],{'method':'thread/unsubscribe','params':{'threadId':'source-1'}})
        self.assertEqual(attempt['continuationTerminal']['params']['turn']['status'],'completed')
        rr=r['releaseRecovery']
        final=rr['first']['result']
        self.assertEqual(final['status'],'finalized')
        self.assertEqual(final['subscriptionRelease']['kind'],'native-unsubscribe')
        self.assertEqual(final['subscriptionRelease']['nativeStatus'],'notSubscribed')
        self.assertNotIn('receiptDigest',final['subscriptionRelease'])
        self.assertEqual(rr['second']['result']['status'],'already-finalized')
        methods=self.assert_recovery_never_replays(rr['calls'])
        self.assertEqual(methods,['thread/read','thread/read'])
        self.assertEqual(rr['ledgerAfterFirst']['state']['phase'],
                         'source-subscription-released')
        self.assertIsNone(rr['ledgerAfterFirst']['state']['pendingEffect'])

    def test_release_unknown_without_supported_observation_is_held_without_requests(self):
        r=self.run_case('release-unknown-weird', releaseRecovery='held')
        self.assertEqual(r['error']['code'],'UNSUBSCRIBE_OUTCOME_UNKNOWN')
        rr=r['releaseRecovery']
        held=rr['first']['result']
        self.assertEqual(held['status'],'held')
        self.assertEqual(held['reason'],'SOURCE_RELEASE_OBSERVATION_UNSUPPORTED')
        self.assertIsNotNone(held['settle'])
        self.assertEqual(held['releaseObservation']['nativeStatus'],
                         'dispatched-no-recognized-receipt')
        self.assertEqual(rr['second']['result']['status'],'held')
        methods=self.assert_recovery_never_replays(rr['calls'])
        self.assertEqual(methods,['thread/read']*4)
        ledger=rr['ledgerAfterFirst']['state']
        self.assertEqual(ledger['phase'],'release-authorized')
        self.assertEqual(ledger['failure']['code'],'UNSUBSCRIBE_OUTCOME_UNKNOWN')
        self.assertIsNotNone(ledger['releaseIntent'])
        self.assertEqual(ledger['releaseObservation']['nativeStatus'],
                         'dispatched-no-recognized-receipt')

    def test_release_transport_throw_recovers_via_fresh_independent_observation(self):
        r=self.run_case('release-unsubscribe-throw', releaseRecovery='fresh-observation')
        self.assertEqual(r['error']['code'],'NATIVE_EFFECT_UNKNOWN')
        last=self.release_failure_record(r)
        self.assertIsNone(last['releaseObservation']['response'])
        self.assertIsNone(last['releaseObservation']['nativeStatus'])
        self.assertEqual(last['releaseObservation']['requestRef']['requestId'],
                         'unsubscribe-original-1')
        self.assertEqual(last['pendingEffect']['requestRef']['requestId'],
                         'unsubscribe-original-1')
        rr=r['releaseRecovery']
        final=rr['first']['result']
        self.assertEqual(final['status'],'finalized')
        self.assertEqual(final['subscriptionRelease']['evidenceRef'],
                         'release-recovery-fresh-evidence')
        self.assertEqual(final['subscriptionRelease']['nativeStatus'],'unsubscribed')
        methods=self.assert_recovery_never_replays(rr['calls'])
        self.assertEqual(methods,['thread/read','thread/read'])
        self.assertEqual(rr['second']['result']['status'],'already-finalized')

    def test_root_recovery_preserves_original_materials_and_refuses_corruption(self):
        for mode in ('missing-attempt','missing-terminal','wrong-request',
                     'missing-original-error','empty-original-error','wrong-request-ref'):
            with self.subTest(mode=mode):
                rr=self.run_case('release-unknown-status',releaseRecovery=mode)['releaseRecovery']
                self.assertEqual(rr['first']['error']['code'],'FINALIZATION_EVIDENCE_CONFLICT')
                self.assertEqual(rr['calls'],[])
        for mode in ('missing-response','mismatched-response'):
            with self.subTest(mode=mode):
                rr=self.run_case('release-unknown-status',releaseRecovery=mode)['releaseRecovery']
                self.assertEqual(rr['first']['result']['status'],'held')
                self.assert_recovery_never_replays(rr['calls'])

    def test_root_finalized_basis_refuses_another_connection(self):
        rr=self.run_case('release-unknown-status',releaseRecovery='repeat-foreign')['releaseRecovery']
        self.assertEqual(rr['first']['result']['status'],'finalized')
        self.assertEqual(rr['second']['error']['code'],'FINALIZATION_RELEASE_KIND_MISMATCH')
        self.assertEqual([c['method'] for c in rr['calls']],['thread/read','thread/read'])

    def test_root_existing_reconciled_recovery_keeps_its_original_guards(self):
        for mode in ('same-corrupt-kind','same-corrupt-target','same-corrupt-terminal'):
            with self.subTest(mode=mode):
                final=self.finalization_case(mode)['finalized']
                self.assertEqual(final['first']['error']['code'],'FINALIZATION_NOT_APPLICABLE')

    def test_root_release_original_request_identity_cannot_be_changed_or_erased(self):
        for mode in ('changed-request-id','missing-request-ref'):
            with self.subTest(mode=mode):
                rr=self.run_case('release-unsubscribe-throw',releaseRecovery=mode)['releaseRecovery']
                self.assertEqual(rr['first']['error']['code'],'FINALIZATION_EVIDENCE_CONFLICT')
                self.assertEqual(rr['calls'],[])

    def test_root_already_finalized_still_requires_its_original_basis(self):
        for mode in ('repeat-missing-attempt','repeat-missing-error','repeat-failed-terminal','repeat-injected-digest'):
            with self.subTest(mode=mode):
                rr=self.run_case('release-unknown-status',releaseRecovery=mode)['releaseRecovery']
                self.assertEqual(rr['first']['result']['status'],'finalized')
                self.assertEqual(rr['second']['error']['code'],'FINALIZATION_EVIDENCE_CONFLICT')
                self.assertEqual([call['method'] for call in rr['calls']],['thread/read','thread/read'])

    def test_reconciled_completed_repeat_rejects_a_foreign_turn(self):
        final=self.finalization_case('repeat-foreign-turn')['finalized']
        self.assertEqual(final['first']['result']['status'],'finalized')
        self.assertEqual(final['second']['error']['code'],'FINALIZATION_EVIDENCE_CONFLICT')

    def test_release_recovery_commit_unknown_is_not_replayed_and_repeat_finalizes(self):
        r=self.run_case('release-unsubscribe-throw', releaseRecovery='commit-unknown')
        rr=r['releaseRecovery']
        self.assertEqual(rr['first']['error']['code'],'RECORDER_COMMIT_UNKNOWN')
        self.assertEqual(rr['second']['result']['status'],'already-finalized')
        methods=self.assert_recovery_never_replays(rr['calls'])
        self.assertEqual(methods,['thread/read','thread/read'])

    def test_release_unknown_cross_controller_recovery_uses_prior_close_evidence(self):
        r=self.run_case('release-unknown-status', releaseRecovery='cross-controller')
        rr=r['releaseRecovery']
        final=rr['first']['result']
        self.assertEqual(final['status'],'finalized')
        release=final['subscriptionRelease']
        self.assertEqual(release['kind'],'prior-controller-closed')
        self.assertEqual(release['originalIntentKind'],'native-unsubscribe')
        self.assertIsNone(release['receiptDigest'])
        methods=self.assert_recovery_never_replays(rr['calls'])
        self.assertEqual(methods,['thread/read','thread/read'])
        self.assertEqual(rr['ledgerAfterFirst']['state']['phase'],
                         'source-subscription-released')

    def test_release_recovery_rejections_preserve_ledger_and_send_nothing(self):
        expectations={
            'legacy-shape':('FINALIZATION_NOT_APPLICABLE',0,'reconciliation-required'),
            'foreign-connection':('FINALIZATION_RELEASE_KIND_MISMATCH',0,'release-authorized'),
            'foreign-state':('INVALID_FINALIZATION_STATE',0,'release-authorized'),
            'stale-cas':('FINALIZATION_BASIS_CHANGED',0,'release-authorized'),
            'fabricated-digest':('FINALIZATION_EVIDENCE_CONFLICT',0,'release-authorized'),
            'active-source':('FINALIZATION_THREAD_ACTIVE',2,'release-authorized'),
            'active-target':('FINALIZATION_THREAD_ACTIVE',2,'release-authorized'),
            'history-changed':('FINALIZATION_NATIVE_MISMATCH',2,'release-authorized'),
            'failed-history':('FINALIZATION_NATIVE_MISMATCH',2,'release-authorized'),
            'paused-denied':('VERIFICATION_DENIED',2,'release-authorized'),
            'authority-denied':('VERIFICATION_DENIED',2,'release-authorized'),
        }
        for mode,(code,reads,phase) in expectations.items():
            with self.subTest(mode=mode):
                r=self.run_case('release-unknown-status', releaseRecovery=mode)
                self.assertEqual(r['error']['code'],'UNSUBSCRIBE_OUTCOME_UNKNOWN')
                rr=r['releaseRecovery']
                self.assertEqual(rr['first']['error']['code'],code)
                methods=self.assert_recovery_never_replays(rr['calls'])
                self.assertEqual(methods,['thread/read']*reads)
                ledger=rr['ledgerAfterFirst']['state']
                self.assertEqual(ledger['phase'],phase)
                self.assertEqual(ledger['failure']['code'],'UNSUBSCRIBE_OUTCOME_UNKNOWN')
                if mode!='legacy-shape':
                    self.assertIsNotNone(ledger['releaseIntent'])
                    self.assertNotIn('receiptDigest',ledger['releaseIntent'])

    def test_finalization_cas_ack_loss_and_repeat_use_readback_without_duplicate_effects(self):
        for mode,second_status in [('authorization-cas-loss','finalized'),
                                   ('authorization-cas-loss-third','finalized'),
                                   ('observation-cas-loss','finalized'),
                                   ('final-cas-loss','already-finalized')]:
            with self.subTest(mode=mode):
                result=self.finalization_case(mode)
                self.assertEqual(result['finalized']['first']['error']['code'],
                                 'RECORDER_COMMIT_UNKNOWN')
                self.assertEqual(result['finalized']['second']['result']['status'],second_status)
                expected_unsubscribe=1 if mode=='observation-cas-loss' else 0
                self.assertEqual(sum(c['method']=='thread/unsubscribe' for c in result['calls']),
                                 expected_unsubscribe)
        repeated=self.finalization_case('repeated')
        self.assertEqual(repeated['finalized']['first']['result']['status'],'finalized')
        self.assertEqual(repeated['finalized']['second']['result']['status'],'already-finalized')
        third=self.finalization_case('third-finalizer-cas-loss')
        self.assertEqual(third['finalized']['first']['error']['code'],'RECORDER_COMMIT_UNKNOWN')
        self.assertEqual(third['finalized']['second']['result']['status'],'finalized')
        self.assertFalse(any(c['method']=='thread/unsubscribe' for c in third['calls']))
        denied=self.finalization_case('third-finalizer-cas-loss-denied')
        self.assertEqual(denied['finalized']['second']['error']['code'],'VERIFICATION_DENIED')
        self.assertEqual(denied['state']['phase'],'release-authorized')

    def test_concurrent_finalizers_have_one_winner_and_expired_pre_cas_is_not_commit_unknown(self):
        concurrent=self.finalization_case('concurrent')['finalized']
        statuses=sorted('result' if 'result' in row else row['error']['code'] for row in concurrent)
        self.assertIn('result',statuses)
        self.assertEqual(statuses.count('result'),1)
        expired=self.finalization_case('deadline-before-cas')
        self.assertNotEqual(expired['finalized']['first']['error']['code'],'RECORDER_COMMIT_UNKNOWN')
        self.assertEqual(expired['commits'],1) # reconciliation CAS only

    def test_reconciled_finalization_settle_and_sdk_restore_compose_with_real_sqlite(self):
        with tempfile.TemporaryDirectory() as directory:
            database=Path(directory)/'carrier.sqlite'
            completed=subprocess.run([shutil.which('node'),str(DRIVER)],
                input=json.dumps({'mode':'finalize-sqlite','database':str(database)})+'\n',
                capture_output=True,text=True,encoding='utf-8',timeout=15)
            self.assertEqual(completed.returncode,0,completed.stderr)
            result=json.loads(completed.stdout)
            self.assertEqual(result['finalized']['status'],'finalized')
            self.assertEqual(result['finalized']['subscriptionRelease']['kind'],
                             'prior-controller-closed')
            self.assertEqual(result['restored']['status'],'ready')
            self.assertEqual(result['restored']['sourceThreadId'],'target-1')
            self.assertEqual(result['record']['state']['phase'],'source-subscription-released')
            self.assertIsNone(result['record']['state']['pendingEffect'])
            self.assertEqual(result['record']['state']['observedLease'],
                             result['record']['state']['expectedLease'])
            self.assertNotEqual(result['record']['state']['observedLease']['token'],
                                result['finalized']['lease']['token'])
            self.assertNotEqual(result['record']['state']['observedLease']['token'],
                                result['settled']['scope']['token'])
            self.assertNotEqual(result['settled']['scope']['token'],result['scope']['token'])
            methods=[call['method'] for call in result['calls']]
            self.assertEqual(methods.count('thread/resume'),1)
            self.assertFalse(any(method in methods for method in
                                 ('thread/start','turn/start','thread/unsubscribe')))
            connection=sqlite3.connect(database)
            try:
                transfer=connection.execute(
                    'SELECT revision,settled,state_json FROM transfers WHERE transfer_id=?',
                    ('sqlite-transfer',)).fetchone()
                scope=connection.execute(
                    'SELECT writer_thread_id,active_transfer_id,fence_token FROM scopes WHERE scope_ref=?',
                    ('sqlite-scope',)).fetchone()
            finally:
                connection.close()
            self.assertEqual(transfer[1],1)
            self.assertEqual(json.loads(transfer[2])['phase'],'source-subscription-released')
            self.assertEqual((scope[0],scope[1]),('target-1',None))

    def test_event_channel_drives_one_dispatch_and_releases_only_its_listener(self):
        r = self.run_case('proposal-event-success')
        self.assertIsNone(r['error'])
        self.assertEqual(r['result']['status'], 'handed-off')
        self.assertEqual(r['proposal']['callsBeforeDispatch'], [])
        self.assertEqual(r['proposal']['respondCount'], 1)
        self.assertEqual(r['proposal']['currentCount'], 1)
        self.assertEqual(r['proposal']['releaseCount'], 1)
        self.assertEqual(r['proposal']['subscriptionAnchor']['params']['callId'], 'source-proposal-call')
        self.assertEqual(sum(c['method']=='thread/start' for c in r['calls']), 1)

    def test_event_channel_does_not_dispatch_on_uncertain_source_or_response(self):
        for suffix in ('new-turn-before-response', 'new-turn-after-response',
                       'new-turn-during-current', 'connection-drift',
                       'response-unknown', 'missing-terminal', 'source-failed',
                       'tool-failed', 'wrong-response', 'changed-state',
                       'conflicting-replay', 'early-terminal'):
            with self.subTest(suffix=suffix):
                r = self.run_case('proposal-event-' + suffix)
                self.assertIsNotNone(r['error'])
                self.assertTrue(r['error']['reconciliationRequired'])
                self.assertEqual(r['proposal']['releaseCount'], 1)
                self.assertFalse(any(c['method']=='thread/start' for c in r['calls']))
                self.assertIsNone(r['result'])

    def test_event_channel_remains_attached_through_intake_verification(self):
        r = self.run_case('proposal-event-new-turn-during-intake')
        self.assertIsNotNone(r['error'])
        self.assertEqual(r['proposal']['releaseCount'], 1)
        self.assertEqual(sum(c['method']=='turn/start' for c in r['calls']), 1)
        self.assertFalse(any(c['method']=='thread/unsubscribe' for c in r['calls']))

    def test_listener_release_failure_retains_completed_transfer_not_retry_permission(self):
        r = self.run_case('proposal-event-release-error')
        self.assertEqual(r['error']['code'], 'PROPOSAL_CHANNEL_RELEASE_FAILED')
        self.assertEqual(r['error']['details']['completedResult']['status'], 'handed-off')
        self.assertTrue(r['error']['reconciliationRequired'])
        self.assertEqual(r['snapshots'][-1]['phase'], 'source-subscription-released')
        self.assertEqual(sum(c['method']=='thread/start' for c in r['calls']), 1)

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

    def test_target_tools_are_explicitly_bound_and_preserved_in_start_and_record(self):
        tools = [{"name": "owner_tool", "description": "Owner-selected task capability",
                  "inputSchema": {"type": "object", "properties": {}}, "deferLoading": True},
                 {"name": "owner_tool", "namespace": "separate_owner",
                  "description": "Different explicit namespace", "inputSchema": {"type": "object"}}]
        result = self.run_case(targetTools=tools)
        self.assertIsNone(result['error'])
        start = next(call['params'] for call in result['calls'] if call['method'] == 'thread/start')
        self.assertEqual(start['dynamicTools'], tools)
        self.assertEqual(result['snapshots'][-1]['plan']['target']['dynamicTools'], tools)

    def test_invalid_target_tools_are_rejected_before_native_effects(self):
        tool = {"name": "t", "description": "Bound tool", "inputSchema": {"type": "object"}}
        for tools in ({}, [tool, tool], [dict(tool, inputSchema=[])], [dict(tool, description="")],
                      [dict(tool, name=str(i)) for i in range(65)]):
            with self.subTest(tools=tools):
                result = self.run_case(targetTools=tools)
                self.assertIsNotNone(result['error'])
                self.assertEqual(result['calls'], [])
                self.assertEqual(result['snapshots'], [])

    def test_active_source_must_reach_exact_terminal_before_fresh_target(self):
        r=self.run_case('active-source')
        self.assertIsNone(r['error'])
        methods=[c['method'] for c in r['calls']]
        self.assertLess(methods.index('turn/interrupt'),methods.index('waitTerminal'))
        self.assertLess(methods.index('waitTerminal'),methods.index('thread/start'))

    def test_bound_effort_reaches_every_intake_and_continuation_without_defaulting(self):
        r=self.run_case('extra-context',targetEffort='medium')
        self.assertIsNone(r['error'])
        turns=[c['params'] for c in r['calls'] if c['method']=='turn/start']
        self.assertEqual(len(turns),3)
        self.assertTrue(all(t['effort']=='medium' for t in turns))
        self.assertEqual(r['snapshots'][0]['plan']['target']['effort'],'medium')
        r=self.run_case('lost-continuation-ack',targetEffort='high')
        self.assertEqual(r['error']['state']['pendingEffect']['params']['effort'],'high')
        self.assertFalse(any(c['method']=='thread/unsubscribe' for c in r['calls']))
        r=self.run_case()
        self.assertTrue(all('effort' not in c['params'] for c in r['calls']))

    def test_invalid_or_native_rejected_effort_does_not_silently_fall_back(self):
        for effort in ('', ' ', None, 42):
            with self.subTest(effort=effort):
                r=self.run_case(targetEffort=effort)
                self.assertEqual(r['error']['code'],'INVALID_INPUT')
                self.assertEqual(r['calls'],[])
        r=self.run_case('unsupported-effort',targetEffort='host-specific-effort')
        self.assertIsNotNone(r['error'])
        turns=[c['params'] for c in r['calls'] if c['method']=='turn/start']
        self.assertEqual(len(turns),1)
        self.assertEqual(turns[0]['effort'],'host-specific-effort')
        self.assertFalse(any(c['method']=='thread/unsubscribe' for c in r['calls']))

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

    def test_unknown_effect_keeps_only_a_matching_native_request_reference(self):
        reference={'connectionId':'test-connection','hostVersion':'fixture-host',
                   'requestId':'native-request-17','method':'turn/start'}
        r=self.run_case('lost-continuation-ack',rpcFailureRef=reference)
        self.assertEqual(r['snapshots'][-1]['pendingEffect']['requestRef'],reference)
        self.assertEqual(r['error']['state']['pendingEffect']['requestRef'],reference)
        self.assertEqual(r['error']['details']['original']['requestRef'],reference)
        self.assertFalse(any(c['method'] in ('turn/interrupt','thread/unsubscribe') for c in r['calls']))
        for change in ({'connectionId':'foreign'},{'hostVersion':'foreign'},
                       {'method':'thread/start'},{'requestId':''},{'requestId':True},
                       {'requestId':'x'*4097},
                       {'extra':'untrusted'}):
            with self.subTest(change=change):
                r=self.run_case('lost-continuation-ack',rpcFailureRef={**reference,**change})
                self.assertNotIn('requestRef',r['error']['state']['pendingEffect'])
                self.assertTrue(r['error']['reconciliationRequired'])
        r=self.run_case('lost-continuation-ack',inheritedRpcRef=True)
        self.assertNotIn('requestRef',r['error']['state']['pendingEffect'])
        self.assertTrue(r['error']['reconciliationRequired'])

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
    context_read = state.get('contextRemaining', 0) > 0
    if context_read: state['contextRemaining'] -= 1
    else: state['next'] = False
    tool_name = 'accord_inspect_context' if context_read else PROPOSAL_TOOL
    tools = body.get('tools', []) + [t for row in body.get('input', [])
        if row.get('type') == 'additional_tools' for t in row.get('tools', [])]
    arguments = {} if context_read else {'reason': 'Preserve the fixed task in the already authorized fresh carrier.'}
    direct = [t for t in tools if t.get('type') == 'function' and t.get('name') == tool_name]
    if len(direct) == 1:
        return {'id':f'proposal_{ordinal}', 'type':'function_call', 'call_id':f'proposal_call_{ordinal}',
                'name':tool_name, 'arguments':json.dumps(arguments), 'status':'completed'}
    wrappers = [f for t in tools if t.get('type')=='namespace' and t.get('name')=='functions'
                for f in t.get('tools',[]) if f.get('name')=='exec']
    if len(wrappers)!=1 or tool_name not in wrappers[0].get('description',''):
        raise ValueError('prepared native proposal tool is not exposed')
    return {'id':f'proposal_{ordinal}', 'type':'custom_tool_call', 'call_id':f'proposal_call_{ordinal}',
            'namespace':'functions', 'name':'exec', 'status':'completed',
            'input':'text(await tools.'+tool_name+'('+json.dumps(arguments)+'));'}


def inspect_finalize_receipt_evidence(value):
    sys.path.insert(0, str(ROOT))
    from scripts.inspect_native_resources import native_processes_released
    root=Path(value).absolute()
    if (not root.is_dir() or root.is_symlink() or root.resolve(strict=True)!=root):
        raise ValueError('ordinary finalize evidence root required')
    def read_json(path,limit=16*1024*1024):
        info=path.lstat()
        if (not path.is_file() or path.is_symlink() or info.st_size>limit
                or path.resolve(strict=True)!=path):
            raise ValueError('unsafe or oversize finalize evidence: '+str(path))
        return json.loads(path.read_text(encoding='utf-8'))
    def lines(path,limit=32*1024*1024):
        info=path.lstat()
        if (not path.is_file() or path.is_symlink() or info.st_size>limit
                or path.resolve(strict=True)!=path):
            raise ValueError('unsafe or oversize finalize JSONL evidence: '+str(path))
        return [json.loads(line) for line in path.read_text(encoding='utf-8').splitlines() if line]
    manifest=read_json(root/'manifest.json');post=read_json(root/'poststate.json')
    cleanup=read_json(root/'cleanup.json');result=read_json(root/'retained/finalize-receipt-result.json')
    readback=read_json(root/'retained/finalize-readback.json')
    identities=manifest.get('identities',{})
    if (manifest.get('scenario')!='finalize-receipt' or manifest.get('faultInjection') is None
            or not identities.get('codex',{}).get('version') or not identities.get('node',{}).get('version')
            or post.get('codexSha256After')!=identities.get('codex',{}).get('sha256')
            or post.get('nodeSha256After')!=identities.get('node',{}).get('sha256')
            or post.get('sharedConfigAfter')!=manifest.get('sharedConfigBefore')
            or post.get('completedCases')!=1 or post.get('providerRequests')!=4
            or post.get('credentialsObserved') is not False or post.get('keepPreserved') is not True
            or post.get('realModelCalls')!=0
            or cleanup!={'ownedRootsRemoved':['home','state','temp'],'workspaceRetained':True,
                         'nativeSessionEvidenceRetained':True}):
        raise ValueError('finalize evidence identity, limits or cleanup differs')
    pure=PureWindowsPath if manifest.get('resourceController')=='windows-job-object' else PurePosixPath
    recorded_root=pure(manifest.get('evidence',''));source_root=pure(manifest.get('sourceRoot',''))
    if not recorded_root.is_absolute() or not source_root.is_absolute():
        raise ValueError('recorded finalize roots are not absolute')
    snapshot=root/'retained/executed-sources'
    for source,expected in manifest.get('sourceHashes',{}).items():
        try: relative=pure(source).relative_to(source_root)
        except ValueError: raise ValueError('frozen source is outside recorded source root') from None
        frozen=snapshot.joinpath(*relative.parts)
        if (not frozen.is_file() or frozen.is_symlink() or frozen.resolve(strict=True)!=frozen
                or hashlib.sha256(frozen.read_bytes()).hexdigest()!=expected):
            raise ValueError('frozen finalize source differs: '+str(relative))
    if post.get('sourceHashesAfter')!=manifest.get('sourceHashes'):
        raise ValueError('execution source changed during finalize evidence run')
    config_path=root/'retained/finalize-receipt-config.json';config=read_json(config_path)
    if (hashlib.sha256(config_path.read_bytes()).hexdigest()!=post.get('finalizeConfigSha256')
            or config.get('finalizeReceipt') is not True or config.get('recoverReceipt') is not True
            or config.get('contextRead') is not False):
        raise ValueError('finalize controller config hash or mode differs')
    if (root/'retained/recorder.sqlite').exists():
        raise ValueError('finalize artifact contains the legacy fixture recorder')
    for field,expected in (('nativeLogRoot',('native','finalize-receipt')),
                           ('recorderPath',('retained','finalize-receipt-carrier.sqlite'))):
        try: relative=pure(config.get(field,'')).relative_to(recorded_root)
        except ValueError: raise ValueError('finalize config path is outside evidence root') from None
        if relative.parts!=expected: raise ValueError('finalize config locator differs: '+field)
    keep=root/'workspace/keep.txt';retained_keep=root/'retained/keep.txt'
    keep_hash=hashlib.sha256(keep.read_bytes()).hexdigest()
    if (keep_hash!=hashlib.sha256(retained_keep.read_bytes()).hexdigest()
            or [p.name for p in (root/'workspace').iterdir()]!=['keep.txt']):
        raise ValueError('protected finalize workspace differs')
    native_home_hashes=read_json(root/'retained/native-home-sha256.json')
    native_home=root/'retained/native-home'
    if set(native_home_hashes)!={p.name for p in native_home.iterdir()}:
        raise ValueError('retained native home inventory differs')
    for name,digest in native_home_hashes.items():
        path=native_home/name
        if (path.parent!=native_home or not path.is_file() or path.is_symlink()
                or path.resolve(strict=True)!=path
                or hashlib.sha256(path.read_bytes()).hexdigest()!=digest):
            raise ValueError('retained native home file differs')
    # This fixture supplies settings through argv; a config.toml is optional.
    if ('ownedConfigSha256' not in post
            or native_home_hashes.get('config.toml')!=post['ownedConfigSha256']):
        raise ValueError('owned native config hash receipt differs')
    for role,name in (('source','codex'),('node','node')):
        record=read_json(root/f'retained/version-probes/{role}/record.json')
        stdout=(root/f'retained/version-probes/{role}/stdout.txt').read_text(encoding='utf-8').strip()
        identity=identities[name]
        if (record.get('arguments')!=[identity['path'],'--version']
                or record.get('sha256')!=identity['sha256'] or record.get('version')!=identity['version']
                or stdout!=identity['version'] or record.get('exitCode')!=0
                or record.get('forced') is not False or record.get('failure') is not None
                or not native_processes_released(record.get('after'),manifest.get('resourceController'))):
            raise ValueError('bounded executable version receipt differs: '+role)

    if (result.get('kind')!='done' or result.get('result') is not None
            or result.get('error',{}).get('code')!='NATIVE_EFFECT_UNKNOWN'
            or result.get('exitCode')!=0 or result.get('recorderCloseError') is not None):
        raise ValueError('controlled lost acknowledgement was not preserved')
    recovery=result.get('recovery') or {};reconciliation=result.get('reconciliation') or {}
    finalization=result.get('finalization') or {};final=finalization.get('finalized') or {}
    settled=finalization.get('settled') or {};record=finalization.get('record') or {}
    scope=finalization.get('scope') or {};state=record.get('state') or {}
    if (reconciliation.get('first',{}).get('status')!='continuation-reconciled'
            or reconciliation.get('repeated',{}).get('status')!='already-reconciled'
            or final.get('status')!='finalized' or final.get('sourceSubscriptionReleased') is not True
            or final.get('subscriptionRelease',{}).get('kind')!='native-unsubscribe'
            or final.get('subscriptionRelease',{}).get('observed') is not True
            or settled.get('scope')!=scope or scope.get('activeTransferId') is not None
            or state.get('phase')!='source-subscription-released' or state.get('pendingEffect') is not None
            or state.get('reconciliation',{}).get('originalFailure',{}).get('code')!='NATIVE_EFFECT_UNKNOWN'
            or state.get('reconciliation',{}).get('requestRef')!=recovery.get('requestRef')
            or state.get('writer')!='target' or state.get('sourceRecovery')!='retained'):
        raise ValueError('reconciliation, finalization or exact settle receipt differs')
    if (readback.get('originalFailure')!=result.get('error')
            or readback.get('requestRef')!=recovery.get('requestRef')
            or readback.get('finalization')!=finalization
            or readback.get('nativeCounts')!={'threadStart':2,'turnStart':3,
                                               'unsubscribe':1,'archiveDelete':0}):
        raise ValueError('independent finalize readback differs')

    database_path=root/'retained/finalize-receipt-carrier.sqlite'
    database_info=database_path.lstat()
    if (not database_path.is_file() or database_path.is_symlink()
            or database_path.resolve(strict=True)!=database_path
            or hashlib.sha256(database_path.read_bytes()).hexdigest()!=post.get('carrierSha256')):
        raise ValueError('finalize carrier hash differs')
    for suffix in ('-wal','-journal'):
        sidecar=database_path.with_name(database_path.name+suffix)
        if sidecar.is_symlink() or sidecar.exists() and (not sidecar.is_file() or sidecar.stat().st_size):
            raise ValueError('finalize carrier is not checkpointed')
    shared_memory=database_path.with_name(database_path.name+'-shm')
    if shared_memory.is_symlink() or shared_memory.exists() and not shared_memory.is_file():
        raise ValueError('finalize carrier SHM is unsafe')
    database=sqlite3.connect(database_path.as_uri()+'?mode=ro&immutable=1',uri=True)
    try:
        scopes=database.execute('SELECT scope_ref,writer_thread_id,active_transfer_id,fence_token FROM scopes').fetchall()
        transfers=database.execute('SELECT transfer_id,scope_ref,revision,state_json,settled FROM transfers').fetchall()
    finally: database.close()
    if (scopes!=[(final.get('scopeRef'),final.get('targetThreadId'),None,scope.get('token'))]
            or len(transfers)!=1 or transfers[0][0]!=final.get('transferId')
            or transfers[0][2]!=record.get('revision') or transfers[0][4]!=1
            or json.loads(transfers[0][3])!=state):
        raise ValueError('portable finalized SQLite state differs')

    native=root/'native/finalize-receipt';sent=lines(native/'requests.jsonl');received=lines(native/'stdout.jsonl')
    methods=[row.get('method') for row in sent if isinstance(row.get('method'),str)]
    starts=[row for row in sent if row.get('method')=='thread/start']
    turns=[row for row in sent if row.get('method')=='turn/start']
    unsubscribes=[row for row in sent if row.get('method')=='thread/unsubscribe']
    if (len(starts)!=2 or len(turns)!=3 or len(unsubscribes)!=1
            or unsubscribes[0].get('params',{}).get('threadId')!=final.get('sourceThreadId')
            or any(method in ('thread/archive','thread/delete','turn/interrupt') for method in methods)
            or any(method.startswith('account/') for method in methods)):
        raise ValueError('portable native finalize RPC sequence differs')
    rpc_key=lambda value:(type(value).__name__,value)
    client_requests=[row for row in sent if 'id' in row and isinstance(row.get('method'),str)]
    response_by_id={}
    for row in received:
        if 'id' in row and 'method' not in row:
            response_by_id.setdefault(rpc_key(row['id']),[]).append(row)
    request_keys=[rpc_key(row['id']) for row in client_requests]
    if len(request_keys)!=len(set(request_keys)) or set(response_by_id)!=set(request_keys):
        raise ValueError('native finalize RPC identity set differs')
    for request in client_requests:
        matched=response_by_id.get(rpc_key(request['id']),[])
        if len(matched)!=1 or 'result' not in matched[0] or 'error' in matched[0]:
            raise ValueError('native finalize RPC response is missing or failed')
    lost_ref=recovery.get('requestRef') or {};lost_request=[row for row in sent if row.get('id')==lost_ref.get('requestId')]
    lost_response=[row for row in received if row.get('id')==lost_ref.get('requestId') and 'method' not in row]
    if (lost_request!=[recovery.get('originalRequest')] or len(lost_response)!=1
            or lost_response[0].get('result')!=recovery.get('originalResponse')):
        raise ValueError('portable raw continuation receipt differs')
    unsubscribe_response=response_by_id[rpc_key(unsubscribes[0]['id'])][0].get('result',{})
    if unsubscribe_response.get('status') not in ('unsubscribed','notSubscribed','notLoaded'):
        raise ValueError('native source unsubscribe acknowledgement differs')
    release_verification=read_json(root/'retained/finalization-verification.json')
    observed_verification=read_json(root/'retained/finalization-observed-verification.json')
    release_facts=release_verification.get('facts',{});observed_facts=observed_verification.get('facts',{})
    release_ledger=release_facts.get('ledger',{});release_state=release_ledger.get('state',{})
    observed_ledger=observed_facts.get('ledger',{});observed_state=observed_ledger.get('state',{})
    release_source=release_facts.get('sourceRead',{}).get('thread',{})
    release_target=release_facts.get('targetRead',{}).get('thread',{})
    release_turn_ids=[item.get('turnId') for item in release_state.get('intakeTurns',[])]+[
        release_state.get('reconciliation',{}).get('turn',{}).get('turnId')]
    if (release_verification.get('verdict',{}).get('decision')!='allow'
            or observed_verification.get('verdict',{}).get('decision')!='allow'
            or release_facts.get('input',{}).get('receiptDigest')!=state.get('reconciliation',{}).get('receiptDigest')
            or release_facts.get('input',{}).get('expectedRevision')!=release_ledger.get('revision')
            or release_facts.get('input',{}).get('expectedLease')!=release_ledger.get('lease')
            or release_state.get('phase')!='continuation-reconciled'
            or release_state.get('reconciliation')!=state.get('reconciliation')
            or release_facts.get('releaseKind')!='native-unsubscribe'
            or release_facts.get('plan')!=release_state.get('plan')
            or release_facts.get('currentConnection')!=release_facts.get('originalConnection')
            or release_facts.get('currentConnection')!=release_facts.get('reconciliationConnection')
            or release_source.get('id')!=final.get('sourceThreadId')
            or release_source.get('status',{}).get('type') not in ('idle','notLoaded')
            or release_source.get('ephemeral') is not False
            or release_target.get('id')!=final.get('targetThreadId')
            or release_target.get('status',{}).get('type') not in ('idle','notLoaded')
            or release_target.get('ephemeral') is not False
            or [item.get('id') for item in release_target.get('turns',[])]!=release_turn_ids
            or any(item.get('status')!='completed' for item in release_target.get('turns',[]))
            or release_facts.get('continuationTurn')!=state.get('reconciliation',{}).get('turn')
            or observed_state.get('phase')!='release-observed'
            or observed_state.get('writer')!='target'
            or observed_state.get('pendingEffect')!={'method':'thread/unsubscribe',
                'params':{'threadId':final.get('sourceThreadId')}}
            or observed_ledger.get('revision',0)<=release_ledger.get('revision',0)):
        raise ValueError('saved finalization facts do not independently bind the ledger and receipt')
    if (observed_facts.get('nativeResponse')!=unsubscribe_response
            or observed_facts.get('nativeStatus')!=unsubscribe_response.get('status')
            or observed_state.get('releaseObservation',{}).get('response')!=unsubscribe_response
            or observed_state.get('releaseObservation',{}).get('nativeStatus')!=unsubscribe_response.get('status')):
        raise ValueError('saved observed-release facts differ from the raw unsubscribe receipt')

    sessions=root/'retained/native-sessions';session_hashes=read_json(root/'retained/native-sessions-sha256.json')
    actual_hashes={p.relative_to(sessions).as_posix():hashlib.sha256(p.read_bytes()).hexdigest()
                   for p in sessions.rglob('*') if p.is_file() and not p.is_symlink()}
    ids=set()
    for name in actual_hashes:
        if name.endswith('.jsonl'):
            for row in lines(sessions/name):
                if row.get('type')=='session_meta' and isinstance(row.get('payload',{}).get('id'),str):
                    ids.add(row['payload']['id'])
    if actual_hashes!=session_hashes or ids!={final.get('sourceThreadId'),final.get('targetThreadId')}:
        raise ValueError('retained native finalize sessions differ')
    provider=[read_json(root/'retained'/f'provider-response-{index}.json') for index in range(1,5)]
    if (any(row.get('transportStatus')!='completed' for row in provider)
            or len(lines(root/'retained/provider-requests.jsonl'))!=4):
        raise ValueError('fixed provider finalize receipts differ')
    resource=read_json(root/'retained/finalize-receipt-resources.json')
    if (resource.get('exitCode')!=0 or resource.get('forced') is not False
            or resource.get('readerStopped') is not True or resource.get('failure') is not None
            or resource.get('released') is not True
            or not native_processes_released(resource.get('after'),manifest.get('resourceController'))):
        raise ValueError('finalize process domain was not naturally released')
    return {'valid':True,'scenario':'finalize-receipt','providerRequests':4,
            'sourceThreadId':final.get('sourceThreadId'),'targetThreadId':final.get('targetThreadId'),
            'settledRevision':record.get('revision'),
            'claimLimit':'Portable controlled lost-ACK finalization evidence; no model, task completion or general crash-recovery claim.'}


"""Insert before native_integration in test_carrier_handoff.py; never auto-run."""


def _release_read_json(path, *, lines=False, limit=16*1024*1024):
    path = Path(path)
    if not path.is_file() or path.is_symlink() or path.resolve(strict=True) != path.absolute():
        raise ValueError('release evidence must be an ordinary file')
    if path.stat().st_size > limit:
        raise ValueError('release evidence exceeds its byte bound')
    text = path.read_text(encoding='utf-8')
    return [json.loads(line) for line in text.splitlines() if line.strip()] if lines else json.loads(text)


def _release_resource_closed(resource):
    from scripts.observe_codex_lifecycle import _released
    return (isinstance(resource, dict) and type(resource.get('ownerPid')) is int
            and resource['ownerPid'] > 0 and type(resource.get('exitCode')) is int and resource['exitCode'] == 0
            and resource.get('forced') is False and resource.get('readerStopped') is True
            and resource.get('failure') is None and resource.get('released') is True
            and isinstance(resource.get('after'), dict) and _released(resource['after'])
            and type(resource.get('startedAtMs')) is int
            and type(resource.get('closedAtMs')) is int
            and resource['startedAtMs'] <= resource['closedAtMs']
            and type(resource.get('startedMonotonic')) in (int, float)
            and type(resource.get('closedMonotonic')) in (int, float)
            and resource['startedMonotonic'] <= resource['closedMonotonic'])


def _release_native_closed(done):
    # close() returns undefined on the real stdio adapter: no closeState bool.
    return (done.get('kind') == 'done' and done.get('transportKind') == 'stdio'
            and type(done.get('nativePid')) is int and done['nativePid'] > 0
            and done.get('nativeStreamsClosed') is True
            and type(done.get('nativeCloseCode')) is int and type(done.get('exitCode')) is int
            and done['nativeCloseCode'] == done['exitCode'] == 0
            and done.get('transportCloseError') is None
            and done.get('recorderCloseError') is None)


def _release_prior_valid(prior, plan):
    """Read original parent receipts and exact native frames; never infer closure."""
    try:
        root = Path(prior['sourceRoot']).absolute()
        if root.resolve(strict=True) != root or root.is_symlink():
            return False
        result_path = root/'retained/release-source-result.json'
        done = _release_read_json(result_path)
        resource = _release_read_json(root/'retained/release-source-resources.json')
        config = _release_read_json(root/'retained/release-source-config.json')
        loss = done.get('releaseLoss') or {}
        record = loss.get('record') or {}
        state = record.get('state') or {}
        fault = loss.get('fault') or {}
        ref = fault.get('requestRef') or {}
        source = state.get('source', {}).get('threadId')
        target = state.get('target', {}).get('threadId')
        sent = _release_read_json(root/'native/release-source/requests.jsonl', lines=True)
        received = _release_read_json(root/'native/release-source/stdout.jsonl', lines=True)
        exact_requests = [v for v in sent if v.get('id') == ref.get('requestId')]
        exact_responses = [v for v in received if v.get('id') == ref.get('requestId') and 'method' not in v]
        db_path = root/'retained/release-recovery-carrier.sqlite'
        if not db_path.is_file() or db_path.is_symlink() or db_path.resolve(strict=True) != db_path:
            return False
        # The original native owner is already closed. Successor has made no
        # recorder mutation at this gate; pending WAL bytes would invalidate it.
        for suffix in ('-wal', '-journal'):
            sidecar = db_path.with_name(db_path.name+suffix)
            if sidecar.is_symlink() or sidecar.exists() and (not sidecar.is_file() or sidecar.stat().st_size):
                return False
        database = sqlite3.connect(db_path.as_uri()+'?mode=ro&immutable=1', uri=True)
        try:
            transfers = database.execute('SELECT transfer_id,scope_ref,revision,state_json,settled FROM transfers').fetchall()
            scopes = database.execute('SELECT scope_ref,writer_thread_id,active_transfer_id,fence_token FROM scopes').fetchall()
        finally: database.close()
        expected_scope = {'scopeRef': plan['scopeRef'], 'writerThreadId': target,
                          'activeTransferId': plan['transferId'], 'token': record.get('lease', {}).get('token')}
        return (done == prior.get('sourceDone') and resource == prior.get('resourceReceipt')
                and hashlib.sha256(result_path.read_bytes()).hexdigest() == prior.get('sourceHash')
                and _release_resource_closed(resource) and _release_native_closed(done)
                and done['nativePid'] != resource['ownerPid']
                and loss.get('plan') == done.get('plan') == plan == state.get('plan')
                and done.get('nativeArgv') == config.get('argv')
                and config.get('mode') == 'native-connection' and config.get('releaseAckLoss') is True
                and config.get('recoverReceipt') is False and config.get('finalizeReceipt') is False
                and state.get('connection') == config.get('binding')
                and done.get('sourceSnapshot', {}).get('record') == record
                and done.get('sourceSnapshot', {}).get('scope') == expected_scope
                and scopes == [(plan['scopeRef'], target, plan['transferId'], expected_scope['token'])]
                and len(transfers) == 1 and transfers[0][:3] == (plan['transferId'], plan['scopeRef'], record.get('revision'))
                and transfers[0][4] == 0 and json.loads(transfers[0][3]) == state
                and resource.get('configSha256') == hashlib.sha256((root/'retained/release-source-config.json').read_bytes()).hexdigest()
                and source == plan['source']['threadId'] and isinstance(target, str) and target != source
                and ref == {**state['connection'], 'requestId': ref.get('requestId'), 'method': 'thread/unsubscribe'}
                and isinstance(ref.get('requestId'), str) and bool(ref['requestId'])
                and len(exact_requests) == len(exact_responses) == 1
                and exact_requests[0] == fault.get('request')
                and exact_requests[0].get('method') == 'thread/unsubscribe'
                and exact_requests[0].get('params') == {'threadId': source}
                and exact_responses[0].get('result') == fault.get('response')
                and fault.get('response', {}).get('status') == 'unsubscribed'
                and len([v for v in sent if v.get('method') == 'thread/start']) == 2
                and len([v for v in sent if v.get('method') == 'turn/start']) == 3
                and len([v for v in sent if v.get('method') == 'thread/unsubscribe']) == 1
                and not any(v.get('method') in ('thread/resume', 'thread/archive', 'thread/delete')
                            or str(v.get('method', '')).startswith('account/') for v in sent)
                and done.get('error', {}).get('code') == state.get('failure', {}).get('code') == 'NATIVE_EFFECT_UNKNOWN'
                and done.get('error', {}).get('details', {}).get('pendingEffect') == state.get('pendingEffect'))
    except (OSError, ValueError, TypeError, KeyError, AttributeError, sqlite3.Error):
        return False


def _release_recovery_verdict(stage, facts, plan, prior, keep_unchanged):
    """Fixed fixture judgment, with an independent parent receipt boundary."""
    value = {'decision': 'hold', **{k: plan[k] for k in ('scopeRef', 'authorityRef', 'stateRef')},
             'sourceRef': 'fixed-native-fixture:release-recovery:'+stage}
    if stage != 'reconciled-release' or not keep_unchanged or not _release_prior_valid(prior, plan):
        return value
    ledger = facts.get('ledger') or {}
    state = ledger.get('state') or {}
    if not isinstance(state, dict) or not isinstance(state.get('connection'), dict):
        return value
    source = state.get('source', {}).get('threadId')
    target = state.get('target', {}).get('threadId')
    original = state.get('connection')
    current = facts.get('currentConnection') or {}
    original_error = state.get('failure', {}).get('originalError') or {}
    attempt = state.get('normalReleaseAttempt') or {}
    ref = prior['sourceDone']['releaseLoss']['fault']['requestRef']
    continuation = state.get('continuationTurn') or {}
    terminal = attempt.get('continuationTerminal') or {}
    params = terminal.get('params') or {}
    source_thread = facts.get('sourceRead', {}).get('thread') or {}
    target_thread = facts.get('targetRead', {}).get('thread') or {}
    turns = target_thread.get('turns')
    intake = state.get('intakeTurns') or []
    expected_turns = [item.get('turnId') for item in intake]+[continuation.get('turnId')]
    release_input = facts.get('input') or {}
    lease = ledger.get('lease') or {}
    prior_state = prior['sourceDone']['releaseLoss']['record']['state']
    checks = [
        ledger == prior['sourceDone']['releaseLoss']['record'], facts.get('plan') == state.get('plan') == plan,
        state.get('phase') == 'release-authorized', 'reconciliation' not in state,
        facts.get('reconciliationConnection') is None,
        state.get('writer') == 'target', state.get('writerThreadId') == target,
        state.get('sourceRecovery') == 'retained', source == plan['source']['threadId'], source != target,
        state.get('pendingEffect') == {'method': 'thread/unsubscribe', 'params': {'threadId': source}, 'requestRef': ref},
        state.get('failure') == prior_state.get('failure'), state.get('normalReleaseAttempt') == prior_state.get('normalReleaseAttempt'),
        original_error.get('code') == state.get('failure', {}).get('code') == 'NATIVE_EFFECT_UNKNOWN',
        original_error.get('stage') == state.get('failure', {}).get('stage') == 'release:source-unsubscribe',
        original_error.get('details', {}).get('requestRef') == ref,
        state.get('releaseObservation') == {'response': None, 'nativeStatus': None, 'requestRef': ref},
        state.get('releaseIntent') == {'kind': 'native-unsubscribe', 'threadId': source,
            'sourceConnectionId': original.get('connectionId'), 'currentConnectionId': original.get('connectionId')},
        attempt.get('kind') == 'verified-continuation-release', attempt.get('transferId') == plan['transferId'],
        attempt.get('scopeRef') == plan['scopeRef'], attempt.get('sourceThreadId') == source,
        attempt.get('targetThreadId') == target, attempt.get('connection') == original,
        attempt.get('request') == {'method': 'thread/unsubscribe', 'params': {'threadId': source}},
        attempt.get('continuationTurn') == facts.get('continuationTurn') == continuation,
        attempt.get('continuedSourceRef') == state.get('verification', {}).get('continued'),
        attempt.get('releaseSourceRef') == state.get('verification', {}).get('normalReleaseAuthorized'),
        bool(attempt.get('continuedSourceRef')), bool(attempt.get('releaseSourceRef')),
        terminal.get('method') == 'turn/completed', params.get('threadId') == target,
        params.get('turn', {}).get('id') == continuation.get('turnId'), params.get('turn', {}).get('status') == 'completed',
        continuation.get('threadId') == target,
        len(intake) == 1, len(set(expected_turns)) == len(expected_turns), all(expected_turns),
        isinstance(turns, list) and [t.get('id') for t in turns] == expected_turns,
        isinstance(turns, list) and all(t.get('status') == 'completed' for t in turns),
        source_thread.get('id') == source, target_thread.get('id') == target,
        source_thread.get('ephemeral') is False, target_thread.get('ephemeral') is False,
        source_thread.get('status', {}).get('type') in ('idle', 'notLoaded'),
        target_thread.get('status', {}).get('type') in ('idle', 'notLoaded'),
        release_input.get('transferId') == plan['transferId'],
        all(release_input.get(k) == plan[k] for k in ('scopeRef', 'authorityRef', 'stateRef')),
        release_input.get('expectedRevision') == ledger.get('revision'), release_input.get('expectedLease') == lease,
        'receiptDigest' in release_input and release_input['receiptDigest'] is None,
        release_input.get('releaseKind') == facts.get('releaseKind') == 'prior-controller-closed',
        type(release_input.get('deadlineMs')) is int and release_input['deadlineMs'] > int(time.time()*1000),
        facts.get('originalConnection') == original, current.get('connectionId') != original.get('connectionId'),
        bool(current.get('connectionId')), current.get('hostVersion') == original.get('hostVersion'),
        lease.get('scopeRef') == plan['scopeRef'], lease.get('transferId') == plan['transferId'],
        lease.get('writerThreadId') == target, bool(lease.get('token')),
    ]
    ok = all(checks)
    value.update(decision='allow' if ok else 'hold')
    for name in ('pauseStateVerified', 'sourceRecoveryReady', 'singleWriter', 'effectsVerified',
                 'receiptVerified', 'reconciliationAuthorized', 'releaseAuthorized', 'priorAttemptQuiesced',
                 'priorControllerClosed', 'priorControllerQuiesced', 'sourceConnectionReleased', 'subscriptionReleaseVerified'):
        value[name] = ok
    value['subscriptionReleaseEvidenceRef'] = ('retained/release-source-resources.json:'+prior['sourceHash']) if ok else None
    return value


def _release_run_owned(root, label, arguments, env, work_deadline, close_deadline, *, config=None, handler=None):
    """One owned process; absolute deadlines cover attach, read, reply and close."""
    from scripts.observe_codex_lifecycle import _new_controller, _spawn_options, _wait_job, _released, save
    retained = root/'retained'
    job, proc, reader = _new_controller(), None, None
    inbox, done, failure, forced = queue.Queue(), None, None, False
    reader_errors, config_hash = [], None
    started_at, started_monotonic = int(time.time()*1000), time.monotonic()
    stdout_path = retained/(label+'-stdout.txt')
    resource_path = retained/(label+'-resources.json')
    try:
        if time.monotonic() >= work_deadline:
            raise TimeoutError('shared deadline exhausted before process launch')
        with (retained/(label+'-stderr.txt')).open('xb') as errors:
            proc = subprocess.Popen(arguments, stdin=subprocess.PIPE if config else subprocess.DEVNULL,
                stdout=subprocess.PIPE, stderr=errors, cwd=ROOT, env=env, **_spawn_options())
            try:
                job.attach_and_resume(proc)
            except BaseException:
                forced = True
                job.terminate()
                if proc.poll() is None: proc.kill()
                raise
            def consume():
                total = 0
                try:
                    with stdout_path.open('xb') as output:
                        for line in proc.stdout:
                            total += len(line)
                            if len(line) > 4*1024*1024 or total > 16*1024*1024:
                                raise ValueError('owned process stdout exceeds bound')
                            output.write(line); output.flush()
                            if config is not None: inbox.put(json.loads(line))
                except BaseException as error:
                    reader_errors.append({'type': type(error).__name__, 'message': str(error)})
                    inbox.put(error)
                finally: inbox.put(None)
            reader = threading.Thread(target=consume, daemon=True); reader.start()
            if config is not None:
                # Node gets the original owner budget, never a renewed 90 seconds.
                remaining = int((config.pop('_ownerDeadline')-time.monotonic())*1000)
                if remaining <= 0 or time.monotonic() >= work_deadline:
                    raise TimeoutError('shared deadline exhausted before config dispatch')
                config['remainingMs'] = remaining
                save(retained/(label+'-config.json'), config)
                config_hash = hashlib.sha256((retained/(label+'-config.json')).read_bytes()).hexdigest()
                proc.stdin.write((json.dumps(config)+'\n').encode()); proc.stdin.flush()
                while True:
                    remaining = work_deadline-time.monotonic()
                    if remaining <= 0: raise TimeoutError('owned process work deadline')
                    message = inbox.get(timeout=remaining)
                    if message is None: raise RuntimeError('bridge exited before result')
                    if isinstance(message, BaseException): raise message
                    with (retained/(label+'-bridge.jsonl')).open('a', encoding='utf-8') as stream:
                        stream.write(json.dumps(message)+'\n')
                    if message.get('kind') == 'done':
                        done = message; save(retained/(label+'-result.json'), done); break
                    try: reply = {'id': message['id'], 'result': handler(message)}
                    except Exception as error: reply = {'id': message.get('id'), 'error': str(error)}
                    if time.monotonic() >= work_deadline:
                        raise TimeoutError('shared deadline exhausted before bridge reply')
                    proc.stdin.write((json.dumps(reply)+'\n').encode()); proc.stdin.flush()
                proc.stdin.close()
            else:
                while proc.poll() is None:
                    if time.monotonic() >= work_deadline: raise TimeoutError('version work deadline')
                    time.sleep(min(0.01, max(0, work_deadline-time.monotonic())))
            close_deadline = min(close_deadline, time.monotonic()+15)
            proc.wait(timeout=max(0, close_deadline-time.monotonic()))
            if proc.returncode: raise RuntimeError('owned process failed')
    except BaseException as error:
        failure = {'type': type(error).__name__, 'message': str(error)}
        raise
    finally:
        # Reserve the last half of this fixed close span for forced shutdown.
        graceful = close_deadline-7.5
        if proc is not None and proc.poll() is None:
            try: proc.wait(timeout=max(0, graceful-time.monotonic()))
            except subprocess.TimeoutExpired: forced = True; job.terminate()
        after = _wait_job(job, max(time.monotonic(), graceful), exact_deadline=True)
        if not _released(after):
            forced = True; job.terminate()
        if proc is not None and proc.poll() is None:
            try: proc.wait(timeout=max(0, close_deadline-time.monotonic()))
            except subprocess.TimeoutExpired: pass
        after = _wait_job(job, close_deadline, exact_deadline=True)
        if reader: reader.join(timeout=max(0, close_deadline-time.monotonic()))
        if reader_errors and failure is None: failure = reader_errors[0]
        resource = {'ownerPid': proc.pid if proc else None, 'startedAtMs': started_at,
            'closedAtMs': int(time.time()*1000), 'startedMonotonic': started_monotonic,
            'closedMonotonic': time.monotonic(), 'exitCode': proc.returncode if proc else None,
            'forced': forced, 'readerStopped': reader is None or not reader.is_alive(),
            'failure': failure, 'after': after, 'released': _released(after),
            'arguments': list(arguments), 'cwd': str(ROOT)}
        if config_hash is not None:
            resource['configSha256'] = config_hash
        save(resource_path, resource)
        job.close()
        if reader is not None and reader.is_alive():
            raise RuntimeError('owned reader exit remains unknown; retain test home')
        if proc and proc.stdout: proc.stdout.close()
        if proc and proc.stdin and not proc.stdin.closed: proc.stdin.close()
    if not _release_resource_closed(resource):
        raise RuntimeError('owned normal exit/group release not observed; retain test home')
    if config_hash is not None and hashlib.sha256((retained/(label+'-config.json')).read_bytes()).hexdigest() != config_hash:
        raise RuntimeError('recorded phase config changed after dispatch')
    if config is not None: return done, resource
    lines = stdout_path.read_text(encoding='utf-8').splitlines()
    if len(lines) != 1 or not lines[0].strip() or len(lines[0]) > 1024:
        raise ValueError('invalid bounded version probe output')
    return lines[0].strip(), resource


def native_release_recovery_integration(codex, evidence):
    """Explicit two-controller, fixed localhost release-loss fixture only."""
    sys.path.insert(0, str(ROOT))
    from scripts.observe_codex_lifecycle import _Fixture, _argv, _owned_environment, _remove_owned_tree, save
    started = time.monotonic()
    work_deadline, close_deadline = started+240, started+270
    root = Path(evidence).absolute()
    if root.exists() or not root.parent.is_dir() or root.parent.resolve() != root.parent:
        raise ValueError('fresh ordinary evidence root required')
    root.mkdir()
    for name in ('home', 'workspace', 'state', 'temp', 'native', 'retained'):
        (root/name).mkdir()
    codex, node = Path(codex).resolve(strict=True), Path(shutil.which('node')).resolve(strict=True)
    if os.name == 'nt' and codex.suffix.lower() != '.exe': raise ValueError('native executable required')
    keep = root/'workspace/keep.txt'; keep.write_bytes(b'Preserve this fixture original.\n')
    digest = lambda path: hashlib.sha256(Path(path).read_bytes()).hexdigest()
    original = digest(keep)
    sources = [ROOT/'runtime'/name for name in ('carrier-handoff.cjs', 'carrier-recorder.cjs',
        'codex-connection.cjs', 'task-checkpoint.cjs', 'codex-context.cjs')]
    sources += [DRIVER, Path(__file__), ROOT/'scripts/observe_codex_lifecycle.py',
                ROOT/'scripts/observe_codex_entry.py', ROOT/'scripts/codex_rpc.py', ROOT/'scripts/inspect_native_resources.py']
    manifest = {'scenario': 'release-recovery', 'evidence': str(root), 'sourceRoot': str(ROOT),
        'codex': str(codex), 'node': str(node), 'realModelCalls': 0,
        'ownedRoots': {n: str(root/n) for n in ('home', 'workspace', 'state', 'temp')},
        'limits': {'workSeconds': 240, 'closeSeconds': 30, 'requestSeconds': 30, 'recoverySeconds': 15,
                   'providerRequestBytes': 2*1024*1024, 'providerRequests': 4},
        'sourceHashes': {str(p): digest(p) for p in sources}, 'keepSha256': original,
        'sharedConfigBefore': _shared_config_observation(),
        'binaryHashes': {'codex': digest(codex), 'node': digest(node)},
        'resourceController': 'windows-job-object' if os.name == 'nt' else 'posix-session-process-group',
        'faultInjection': 'Lose only the consumer acknowledgement after the original real unsubscribe returned unsubscribed; no retry or reset.',
        'claimLimit': 'Native fixed-response release mechanism only; zero real model calls, no autonomous or semantic takeover, installation, trust, user environment or full acceptance claim.'}
    save(root/'manifest.json', manifest)
    snapshot = root/'retained/executed-sources'; snapshot.mkdir()
    for p in sources:
        destination = snapshot/p.relative_to(ROOT)
        destination.parent.mkdir(parents=True, exist_ok=True); shutil.copyfile(p, destination)
        if digest(destination) != manifest['sourceHashes'][str(p)]: raise RuntimeError('source snapshot changed')
    env = _owned_environment(manifest)
    resources, fixture, results = [], None, []
    try:
        for role, binary in (('codex', codex), ('node', node)):
            probe_work = min(work_deadline, time.monotonic()+10)
            version, receipt = _release_run_owned(root, 'version-'+role, [str(binary), '--version'], env,
                probe_work, min(close_deadline, probe_work+15))
            resources.append(receipt)
            manifest.setdefault('identities', {})[role] = {'path': str(binary), 'version': version,
                                                        'sha256': manifest['binaryHashes'][role]}
            if digest(binary) != manifest['binaryHashes'][role]: raise RuntimeError('binary changed during version probe')
        save(root/'manifest.json', manifest)
        if time.monotonic() >= work_deadline: raise TimeoutError('shared work deadline exhausted before provider creation')
        proposal_state = {'next': True}
        fixture = _Fixture(manifest, lambda body, ordinal: proposal_fixture_item(body, ordinal, proposal_state))
        argv = _argv(manifest, fixture, ('-c', 'features.plugins=false', '-c', 'features.hooks=false'))
        source_work = min(work_deadline, time.monotonic()+90)
        source_close = min(close_deadline, source_work+15)
        if source_work-time.monotonic() <= 16: raise TimeoutError('insufficient original budget for source plan')
        now = int(time.time()*1000)
        plan = {'transferId': 'release-recovery', 'scopeRef': 'fixture-release-recovery',
            'authorityRef': 'fixture-authority-v1', 'stateRef': 'fixture-source-v1',
            'source': {'threadId': 'pending-source', 'turnId': 'pending-turn'},
            'target': {'cwd': str(root/'workspace'), 'model': 'fixture-no-model', 'modelProvider': 'accord_fixture'},
            'handoffText': 'Read-only intake of the fixed fixture task; preserve keep.txt and do not call tools.',
            'continuation': {'input': 'Continue the accepted read-only fixture task; preserve keep.txt and do not call tools.',
                             'sandboxPolicy': {'type': 'readOnly'}},
            'deadlineMs': now+min(60000, int((source_work-time.monotonic())*1000)-15000),
            'recoveryDeadlineMs': now+min(75000, int((source_work-time.monotonic())*1000)-1000)}
        binding = {'connectionId': 'release-source-'+secrets.token_hex(16),
                   'hostVersion': manifest['identities']['codex']['version']}
        def source_handler(message):
            args = message.get('args', [])
            if message.get('kind') == 'sourceReady':
                source, turn = args
                if (plan['source']['threadId'] != 'pending-source' or source.get('cwd') != plan['target']['cwd']
                    or source.get('model') != plan['target']['model'] or source.get('thread', {}).get('ephemeral') is not False):
                    raise ValueError('native source binding differs')
                plan['source'] = {'threadId': source['thread']['id'], 'turnId': turn['turn']['id']}
                save(root/'retained/owned-source-binding.json', {'start': source, 'turn': turn})
                return {'bound': True}
            if message.get('kind') == 'sourceContext':
                if (len(args) != 1 or not isinstance(args[0], dict)
                        or args[0].get('state') not in ('unknown','window-observed')
                        or args[0].get('sourceReleaseAllowed') is not False
                        or args[0].get('state') == 'unknown' and args[0].get('windowTokens') is not None):
                    raise ValueError('source context must preserve unknown and no release authority')
                save(root/'retained/owned-source-context.json', args[0])
                return args[0]
            if message.get('kind') != 'verify' or len(args) != 3: raise ValueError('unexpected source caller operation')
            stage, facts = args[:2]
            if stage not in ('prepare', 'quiesced', 'target-created', 'accepted', 'continue', 'continued', 'release'):
                raise ValueError('unexpected source verifier stage')
            unchanged = digest(keep) == original
            value = {'decision': 'allow' if unchanged else 'hold', **{k: plan[k] for k in ('scopeRef','authorityRef','stateRef')},
                'sourceRef': 'fixed-native-fixture:release-source:'+stage, 'sourceRecoveryReady': True,
                'quiesced': True, 'noOtherWriters': True, 'targetSettingsMatch': True, 'accepted': True,
                'sourceIdle': True, 'singleWriter': True, 'effectsVerified': unchanged,
                'targetInitializationSafe': True, 'initializationEffectsVerified': True, 'intakeEffectsVerified': unchanged}
            if stage == 'target-created':
                actual = facts['startResponse']
                value['targetSettingsMatch'] = (actual.get('model') == plan['target']['model']
                    and actual.get('cwd') == plan['target']['cwd'] and actual.get('approvalPolicy') == 'never'
                    and actual.get('sandbox', {}).get('type') == 'readOnly')
            save(root/'retained'/('source-verification-'+stage+'.json'), {'facts': facts, 'verdict': value,
                 'claimLimit': 'Existing fixed-response test verifier; not autonomous model or semantic judgment.'})
            return value
        (root/'native/release-source').mkdir()
        config = {'mode': 'native-connection', 'releaseAckLoss': True, 'recoverReceipt': False,
            'finalizeReceipt': False, 'contextRead': False, 'plan': plan, 'binding': binding,
            'nativeLogRoot': str(root/'native/release-source'), 'argv': argv,
            'recorderPath': str(root/'retained/release-recovery-carrier.sqlite'), '_ownerDeadline': source_work}
        source_done, source_resource = _release_run_owned(root, 'release-source', [str(node), str(DRIVER)], env,
            source_work, source_close, config=config, handler=source_handler)
        resources.append(source_resource); results.append(source_done)
        prior = {'sourceDone': source_done, 'resourceReceipt': source_resource, 'sourceRoot': str(root),
                 'sourceHash': digest(root/'retained/release-source-result.json')}
        if not _release_prior_valid(prior, plan): raise RuntimeError('source release loss or normal closure not verified')
        if time.monotonic() >= work_deadline: raise TimeoutError('original deadline exhausted before successor')
        save(root/'retained/release-prior.json', prior)
        successor_binding = {'connectionId': 'release-successor-'+secrets.token_hex(16), 'hostVersion': binding['hostVersion']}
        def successor_handler(message):
            args = message.get('args', [])
            if message.get('kind') != 'verify' or len(args) != 4 or args[3] != prior:
                raise ValueError('successor verifier changed parent-owned prior')
            stage, facts, remaining, _ = args
            if (not isinstance(remaining, (int, float)) or remaining <= 0 or time.monotonic() >= work_deadline
                    or facts.get('currentConnection') != successor_binding):
                raise ValueError('successor budget or binding differs')
            value = _release_recovery_verdict(stage, facts, plan, prior, digest(keep) == original)
            save(root/'retained/release-recovery-verification.json', {'facts': facts, 'verdict': value,
                 'claimLimit': manifest['claimLimit']})
            return value
        (root/'native/release-successor').mkdir()
        recovery_config = {'mode': 'native-release-recovery', 'binding': successor_binding,
            'nativeLogRoot': str(root/'native/release-successor'), 'argv': argv,
            'recorderPath': config['recorderPath'], 'prior': prior, '_ownerDeadline': work_deadline}
        successor_done, successor_resource = _release_run_owned(root, 'release-successor', [str(node), str(DRIVER)],
            env, work_deadline, work_deadline+15, config=recovery_config, handler=successor_handler)
        resources.append(successor_resource); results.append(successor_done)
        if (not _release_native_closed(successor_done) or successor_done.get('error') is not None
            or source_resource['closedMonotonic'] > successor_resource['startedMonotonic']):
            raise RuntimeError('successor release result or sequential controller closure differs')
    finally:
        provider_closed = False
        if fixture is not None:
            fixture.close(); provider_closed = not fixture.thread.is_alive()
        if time.monotonic() > close_deadline:
            save(root/'retained/close-budget-overrun.json', {'observedMonotonic': time.monotonic(),
                 'closeDeadlineMonotonic': close_deadline, 'reason': 'provider/resource close exceeded original allowance'})
        all_resources = [_release_read_json(p) for p in (root/'retained').glob('*-resources.json')]
        released = bool(all_resources) and all(_release_resource_closed(r) for r in all_resources)
        for phase in ('release-source', 'release-successor'):
            if (root/'retained'/(phase+'-resources.json')).exists():
                phase_result = root/'retained'/(phase+'-result.json')
                released = released and phase_result.exists() and _release_native_closed(_release_read_json(phase_result))
        retained = root/'retained/native-home'
        if released and (fixture is None or provider_closed) and time.monotonic() <= close_deadline:
            if any(p.is_symlink() or not p.resolve().is_relative_to(root/'home') for p in (root/'home').rglob('*')):
                raise RuntimeError('native home retention contains an unowned link; retain original')
            shutil.copytree(root/'home', retained)
            shutil.copyfile(keep, root/'retained/keep.txt')
            home_hashes = {p.relative_to(retained).as_posix(): digest(p) for p in retained.rglob('*') if p.is_file()}
            save(root/'retained/native-home-sha256.json', home_hashes)
            if (root/'home/sessions').exists(): shutil.copytree(root/'home/sessions', root/'retained/native-sessions')
        poststate = {'providerRequests': len(fixture.requests) if fixture else 0,
            'credentialsObserved': fixture.auth_seen if fixture else False, 'providerClosed': provider_closed,
            'realModelCalls': 0, 'keepPreserved': digest(keep) == original, 'resourcesReleased': released,
            'sharedConfigAfter': _shared_config_observation(), 'completedStages': len(results),
            'binaryHashesAfter': {'codex': digest(codex), 'node': digest(node)},
            'sourceHashesAfter': {p: digest(p) for p in manifest['sourceHashes']}, 'claimLimit': manifest['claimLimit']}
        poststate.update(codexSha256After=digest(codex), nodeSha256After=digest(node),
            configHashes={phase: digest(root/'retained'/(phase+'-config.json'))
                for phase in ('release-source','release-successor')
                if (root/'retained'/(phase+'-config.json')).is_file()},
            carrierSha256=digest(root/'retained/release-recovery-carrier.sqlite')
                if (root/'retained/release-recovery-carrier.sqlite').is_file() else None)
        save(root/'poststate.json', poststate)
        if released and (fixture is None or provider_closed) and time.monotonic() <= close_deadline:
            for name in ('home','state','temp'):
                target = (root/name).resolve(strict=True)
                if target.parent != root: raise ValueError('task-owned cleanup root mismatch')
                _remove_owned_tree(target)
            save(root/'cleanup.json', {'ownedRootsRemoved': ['home','state','temp'], 'workspaceRetained': True,
                 'nativeSessionEvidenceRetained': True})
        else:
            save(root/'cleanup.json', {'ownedRootsRemoved': [], 'reason': 'resource exit or provider closure unconfirmed'})
    if (poststate['credentialsObserved'] or poststate['providerRequests'] != 4
            or poststate['sharedConfigAfter'] != manifest['sharedConfigBefore'] or not poststate['keepPreserved']
            or poststate['binaryHashesAfter'] != manifest['binaryHashes']
            or poststate['sourceHashesAfter'] != manifest['sourceHashes']
            or (root/'retained/close-budget-overrun.json').exists() or time.monotonic() > close_deadline):
        raise RuntimeError('release fixture protection or fixed provider count differs')
    for ordinal in range(1,5):
        response = _release_read_json(root/'retained'/f'provider-response-{ordinal}.json')
        if (response.get('ordinal') != ordinal or response.get('transportStatus') != 'completed'
            or response.get('response', {}).get('id') != f'resp_fixture_{ordinal}'
            or response.get('response', {}).get('status') != 'completed'):
            raise RuntimeError('fixed localhost provider response was not completed')
    verdict = inspect_release_recovery_evidence(root)
    if verdict.get('valid') is not True: raise RuntimeError('independent release-recovery evidence inspection denied')
    if time.monotonic() > close_deadline: raise TimeoutError('original total close allowance exhausted during inspection')
    save(root/'inspection.json', verdict)
    print(json.dumps({'nativeCases': 1, 'nativeStages': 2, 'realModelCalls': 0,
                      'providerRequests': 4, 'evidence': str(root), 'claimLimit': manifest['claimLimit']}))


def inspect_release_recovery_evidence(value):
    """Read retained evidence only; never launch a host or infer model judgment."""
    sys.path.insert(0, str(ROOT))
    from scripts.inspect_native_resources import native_processes_released
    import math
    root = Path(value).absolute()
    if not root.is_dir() or root.is_symlink() or root.resolve(strict=True) != root:
        raise ValueError('ordinary release-recovery evidence required')
    def need(ok, message):
        if not ok: raise ValueError(message)
    def data(relative, limit=32*1024*1024):
        p=root/relative
        need(p.is_file() and not p.is_symlink() and p.resolve(strict=True)==p and p.stat().st_size<=limit,
             'unsafe/missing/oversize release evidence: '+relative)
        return p.read_bytes()
    def js(relative): return json.loads(data(relative))
    def rows(relative): return [json.loads(line) for line in data(relative).decode('utf-8').splitlines() if line.strip()]
    sha=lambda value:hashlib.sha256(value).hexdigest()
    manifest=js('manifest.json');post=js('poststate.json')
    need(manifest.get('scenario')=='release-recovery','wrong release-recovery scenario')
    identities=manifest.get('identities',{})
    need(all(identities.get(k,{}).get('version') and identities[k].get('sha256') for k in ['codex','node']),
         'actual version identities missing')
    need(post.get('codexSha256After')==identities['codex']['sha256'] and
         post.get('nodeSha256After')==identities['node']['sha256'] and
         post.get('sharedConfigAfter')==manifest.get('sharedConfigBefore') and
         post.get('sourceHashesAfter')==manifest.get('sourceHashes') and
         post.get('providerRequests')==4 and post.get('realModelCalls')==0 and
         post.get('credentialsObserved') is False and post.get('keepPreserved') is True,
         'release-recovery provenance/environment/provider differs')
    for role in ('codex','node'):
        version=data('retained/version-'+role+'-stdout.txt').decode('utf-8').strip()
        receipt=js('retained/version-'+role+'-resources.json')
        need(version==identities[role]['version'] and _release_resource_closed(receipt) and
             receipt.get('arguments')==[identities[role]['path'],'--version'], 'version original receipt differs')
    provider=rows('retained/provider-requests.jsonl')
    need([x.get('ordinal') for x in provider]==[1,2,3,4] and
         all(x.get('request',{}).get('model')=='fixture-no-model' for x in provider) and
         all(js('retained/provider-response-'+str(i)+'.json').get('transportStatus')=='completed' for i in range(1,5)) and
         post.get('providerClosed') is True, 'fixed provider original receipts differ')
    controller=manifest.get('resourceController')
    need(controller in ['windows-job-object','posix-session-process-group'],'unbound resource controller')
    pure=PureWindowsPath if controller=='windows-job-object' else PurePosixPath
    original=pure(manifest.get('evidence',''));source_root=pure(manifest.get('sourceRoot',''))
    need(original.is_absolute() and source_root.is_absolute(),'recorded roots unavailable')
    required_sources={'runtime/carrier-handoff.cjs','runtime/carrier-recorder.cjs','runtime/codex-connection.cjs',
        'runtime/codex-context.cjs','runtime/task-checkpoint.cjs','tests/product/carrier_handoff_host.cjs',
        'tests/product/test_carrier_handoff.py','scripts/observe_codex_lifecycle.py','scripts/observe_codex_entry.py',
        'scripts/codex_rpc.py','scripts/inspect_native_resources.py'}
    observed_sources=set()
    for name,expected in manifest.get('sourceHashes',{}).items():
        try: relative=pure(name).relative_to(source_root)
        except ValueError: raise ValueError('source outside recorded checkout') from None
        observed_sources.add('/'.join(relative.parts))
        need(sha(data('retained/executed-sources/'+'/'.join(relative.parts)))==expected,'executed source bytes changed')
    need(required_sources<=observed_sources,'necessary execution sources not retained')
    def location(value, relative):
        try: observed=pure(value).relative_to(original)
        except (ValueError,TypeError): return False
        return observed.parts==pure(relative).parts
    configs={p:js('retained/'+p+'-config.json') for p in ['release-source','release-successor']}
    results={p:js('retained/'+p+'-result.json') for p in configs}
    resources={p:js('retained/'+p+'-resources.json') for p in configs}
    for phase,c in configs.items():
        need(location(c.get('nativeLogRoot'),'native/'+phase) and
             location(c.get('recorderPath'),'retained/release-recovery-carrier.sqlite'),
             'phase paths do not bind this evidence')
        need(post.get('configHashes',{}).get(phase)==sha(data('retained/'+phase+'-config.json')),
             'phase configuration hash differs')
        d=results[phase];r=resources[phase]
        need(d.get('exitCode')==0 and d.get('nativeCloseCode')==0 and
             d.get('nativeStreamsClosed') is True and d.get('transportCloseError') is None and
             d.get('recorderCloseError') is None and type(d.get('nativePid')) is int and d['nativePid']>0,
             'native direct process/stream closure missing')
        need(type(r.get('ownerPid')) is int and r['ownerPid']>0 and r.get('exitCode')==0 and
             r.get('forced') is False and r.get('failure') is None and r.get('readerStopped') is True and
             r.get('released') is True and native_processes_released(r.get('after'),controller),
             'owned controller/reader/group closure missing')
        need(all(type(r.get(k)) in (int,float) and math.isfinite(r[k]) for k in ['startedMonotonic','closedMonotonic']) and
             r['startedMonotonic']<=r['closedMonotonic'],'invalid controller lifetime')
    old=results['release-source'];new=results['release-successor'];loss=old.get('releaseLoss') or {}
    first=loss.get('record') or {};state=first.get('state') or {};plan=loss.get('plan')
    fault=loss.get('fault') or {};ref=fault.get('requestRef') or {}
    need(configs['release-source'].get('releaseAckLoss') is True and not configs['release-source'].get('recoverReceipt') and
         not configs['release-source'].get('finalizeReceipt') and configs['release-successor'].get('mode')=='native-release-recovery',
         'not the normal release loss/successor route')
    need(old.get('error',{}).get('code')=='NATIVE_EFFECT_UNKNOWN' and old.get('result') is None and
         state.get('phase')=='release-authorized' and state.get('writer')=='target' and
         state.get('sourceRecovery')=='retained' and 'reconciliation' not in state and
         state.get('failure',{}).get('stage')=='release:source-unsubscribe' and
         state.get('failure',{}).get('originalError',{}).get('code')=='NATIVE_EFFECT_UNKNOWN' and
         state.get('plan')==plan==old.get('plan') and
         state.get('releaseObservation',{}).get('response') is None and state['releaseObservation'].get('nativeStatus') is None,
         'original normal-release failure was not retained')
    source=state['source']['threadId'];target=state['target']['threadId']
    need(state.get('normalReleaseAttempt',{}).get('kind')=='verified-continuation-release' and
         all(k in state for k in ['failure','normalReleaseAttempt','continuationTurn','planDigest','intakeTurns',
                                  'connection','releaseIntent','releaseObservation']),
         'required original release evidence missing')
    need(source!=target and state.get('writerThreadId')==target and first.get('lease',{}).get('writerThreadId')==target,
         'original sole target writer differs')
    need(ref.get('method')=='thread/unsubscribe' and ref==state.get('pendingEffect',{}).get('requestRef') and
         ref==state['releaseObservation'].get('requestRef') and ref==state['failure']['originalError'].get('details',{}).get('requestRef'),
         'lost request/error identities differ')
    prior=configs['release-successor'].get('prior') or {}
    need(prior.get('sourceDone')==old and prior.get('resourceReceipt')==resources['release-source'] and
         prior.get('sourceHash')==sha(data('retained/release-source-result.json')) and
         pure(prior.get('sourceRoot',''))==original,'successor prior does not bind actual original files')
    need(resources['release-source']['closedMonotonic']<=resources['release-successor']['startedMonotonic'],
         'successor started before original resources closed')
    for phase,r in resources.items():
        need(r.get('configSha256')==post['configHashes'][phase] and
             r.get('arguments')==[identities['node']['path'],str(source_root/'tests/product/carrier_handoff_host.cjs')],
             'actual controller launch/config identity differs')
    source_binding=configs['release-source']['binding'];successor_binding=configs['release-successor']['binding']
    need(source_binding==state.get('connection') and source_binding['connectionId']!=successor_binding['connectionId'] and
         source_binding['hostVersion']==successor_binding['hostVersion']==identities['codex']['version'],
         'actual connection/version bindings differ')
    need(ref.get('connectionId')==source_binding['connectionId'] and ref.get('hostVersion')==source_binding['hostVersion'],
         'lost receipt belongs to another native connection')
    argv=configs['release-source'].get('argv')
    need(isinstance(argv,list) and len(argv)>1 and argv[0]==identities['codex']['path'] and argv[1]=='app-server' and
         configs['release-successor'].get('argv')==argv==old.get('nativeArgv')==new.get('nativeArgv'),
         'recorded native launch differs from the bound executable')
    traces={phase:rows('native/'+phase+'/requests.jsonl') for phase in configs}
    replies={phase:rows('native/'+phase+'/stdout.jsonl') for phase in configs}
    native=[x for x in traces['release-source'] if 'method' in x]
    need(sum(x['method']=='thread/start' for x in native)==2 and sum(x['method']=='turn/start' for x in native)==3 and
         sum(x['method']=='thread/unsubscribe' for x in native)==1 and
         not any(x['method'] in ['thread/resume','thread/archive','thread/delete'] or x['method'].startswith('account/') for x in native),
         'source native scope or effect count differs')
    for call in [x for x in native if x['method']=='thread/start']:
        params=call.get('params',{});values=[x.get('result') for x in replies['release-source'] if x.get('id')==call.get('id') and 'method' not in x]
        need(params.get('model')=='fixture-no-model' and params.get('modelProvider')=='accord_fixture' and
             params.get('sandbox')=='read-only' and params.get('approvalPolicy')=='never' and
             pure(params.get('cwd',''))==original/'workspace' and len(values)==1, 'native fixture permission/model request differs')
        actual=values[0]
        need(actual.get('model')=='fixture-no-model' and actual.get('modelProvider')=='accord_fixture' and
             actual.get('approvalPolicy')=='never' and actual.get('sandbox',{}).get('type')=='readOnly' and
             pure(actual.get('cwd',''))==original/'workspace' and actual.get('thread',{}).get('ephemeral') is False,
             'native fixture actual permission/model differs')
    turn_calls=[x for x in native if x['method']=='turn/start']
    need([x.get('params',{}).get('threadId') for x in turn_calls]==[source,target,target],
         'native turn ownership/order differs')
    for call,text in zip(turn_calls[1:],[plan['handoffText'],plan['continuation']['input']]):
        need(call.get('params',{}).get('input')==[{'type':'text','text':text}], 'native target input request differs')
    for call in turn_calls:
        values=[x.get('result') for x in replies['release-source'] if x.get('id')==call.get('id') and 'method' not in x]
        need(len(values)==1 and isinstance(values[0].get('turn',{}).get('id'),str),'native turn start acknowledgement missing')
        terminals=[x for x in replies['release-source'] if x.get('method')=='turn/completed' and
                   x.get('params',{}).get('threadId')==call['params']['threadId'] and
                   x.get('params',{}).get('turn',{}).get('id')==values[0]['turn']['id']]
        need(len(terminals)==1 and terminals[0]['params']['turn'].get('status')=='completed',
             'native source/intake/continuation terminal missing')
    request=[x for x in native if x['method']=='thread/unsubscribe'][0]
    ack=[x for x in replies['release-source'] if x.get('id')==request['id'] and 'method' not in x]
    need(request==fault.get('request') and request.get('params')=={'threadId':source} and
         request['id']==ref.get('requestId') and len(ack)==1 and ack[0].get('result')==fault.get('response') and
         fault['response'].get('status')=='unsubscribed','original native release ACK was not observed before loss')
    successor=traces['release-successor'];methods=[x['method'] for x in successor if 'method' in x]
    need(methods==['initialize','initialized','thread/read','thread/read'],'successor repeated or expanded native effects')
    reads=[x for x in successor if x.get('method')=='thread/read']
    need([x['params'] for x in reads]==[{'threadId':source},{'threadId':target,'includeTurns':True}],
         'successor does not read exact source/target history')
    recovery=new.get('releaseRecovery') or {};last=recovery.get('finalSnapshot') or {};final=recovery.get('finalized') or {}
    need(new.get('error') is None and new.get('result')==final and final.get('status')=='finalized' and
         final.get('subscriptionRelease',{}).get('kind')=='prior-controller-closed' and
         final['subscriptionRelease'].get('receiptDigest') is None and recovery.get('sourceSnapshot',{}).get('record')==first,
         'successor normal-release finalization missing')
    after=last.get('record',{});end=after.get('state',{})
    preserved=['failure','normalReleaseAttempt','continuationTurn','continuationTerminal','planDigest','intakeTurns',
               'connection','releaseIntent','releaseObservation']
    need(all(end.get(k)==state.get(k) for k in preserved) and end.get('phase')=='source-subscription-released' and
         end.get('pendingEffect') is None and end.get('sourceRecovery')=='retained' and end.get('writerThreadId')==target and
         after.get('revision')==first.get('revision')+1 and after.get('lease',{}).get('token')!=first['lease']['token'],
         'same-recorder CAS lost original evidence or writer')
    expected_turns=[x['turnId'] for x in state['intakeTurns']]+[state['continuationTurn']['turnId']]
    for read_call,field in zip(reads,['sourceRead','targetRead']):
        values=[x.get('result') for x in replies['release-successor'] if x.get('id')==read_call['id'] and 'method' not in x]
        need(len(values)==1 and values[0]==recovery.get(field),'successor readback differs from raw native response')
        thread=values[0]['thread'];need(thread.get('ephemeral') is False and thread.get('status',{}).get('type') in ['idle','notLoaded'],
                                      'source/target still active or history not persistent')
        if field=='targetRead':
            need([x['id'] for x in thread.get('turns',[])]==expected_turns and all(x['status']=='completed' for x in thread['turns']),
                 'target exact completed history differs')
            expected_inputs=[x.get('input') for x in [plan['continuation']]]
            expected_inputs=[plan['handoffText'],*expected_inputs]
            need(len(thread['turns'])==len(expected_inputs),'unexpected intake repair in fixed fixture')
            for turn,text in zip(thread['turns'],expected_inputs):
                messages=[x for x in turn.get('items',[]) if x.get('type')=='userMessage']
                need(len(messages)==1 and len(messages[0].get('content',[]))==1 and
                     messages[0]['content'][0].get('type')=='text' and messages[0]['content'][0].get('text')==text and
                     not messages[0]['content'][0].get('text_elements',[]),'target original input text differs')
    # Read final SQLite itself, not an actor's boolean summary.
    db=root/'retained/release-recovery-carrier.sqlite'
    data('retained/release-recovery-carrier.sqlite')
    need(sha(data('retained/release-recovery-carrier.sqlite'))==post.get('carrierSha256'),
         'final carrier bytes changed after poststate')
    for suffix in ['-wal','-journal']:
        p=Path(str(db)+suffix);need(not p.exists() or p.is_file() and not p.is_symlink() and p.stat().st_size==0,'uncheckpointed recorder')
    connection=sqlite3.connect(db.as_uri()+'?mode=ro&immutable=1',uri=True)
    try:
        scopes=connection.execute('SELECT scope_ref,writer_thread_id,active_transfer_id,fence_token FROM scopes').fetchall()
        transfers=connection.execute('SELECT transfer_id,scope_ref,revision,state_json,settled FROM transfers').fetchall()
    finally: connection.close()
    need(scopes==[(plan['scopeRef'],target,plan['transferId'],after['lease']['token'])] and len(transfers)==1 and
         transfers[0][:3]==(plan['transferId'],plan['scopeRef'],after['revision']) and transfers[0][4]==0 and
         json.loads(transfers[0][3])==end,'durable recorder differs or was settled')
    need(sha(data('workspace/keep.txt'))==manifest.get('keepSha256') and
         data('workspace/keep.txt')==data('retained/keep.txt') and
         sorted(p.name for p in (root/'workspace').iterdir())==['keep.txt'],'protected workspace changed')
    need(js('cleanup.json')=={'ownedRootsRemoved':['home','state','temp'],'workspaceRetained':True,
         'nativeSessionEvidenceRetained':True},'owned cleanup unverified')
    need(all(not (root/name).exists() and not (root/name).is_symlink() for name in ('home','state','temp')),
         'owned original roots remain after claimed cleanup')
    home=root/'retained/native-home';hashes=js('retained/native-home-sha256.json')
    need(isinstance(hashes,dict) and bool(hashes) and home.is_dir() and not home.is_symlink(), 'native home preservation missing')
    actual_home={}
    for file in home.rglob('*'):
        need(not file.is_symlink() and file.resolve().is_relative_to(home), 'unsafe native home evidence')
        if file.is_file(): actual_home[file.relative_to(home).as_posix()]=sha(file.read_bytes())
    need(actual_home==hashes, 'native home preservation differs')
    sessions={name[len('sessions/'):]:digest for name,digest in hashes.items() if name.startswith('sessions/')}
    if sessions:
        copied=root/'retained/native-sessions'
        need(copied.is_dir() and not copied.is_symlink(), 'native session copy missing')
        observed={};ids=set()
        for file in copied.rglob('*'):
            need(not file.is_symlink() and file.resolve().is_relative_to(copied), 'unsafe native session evidence')
            if file.is_file():
                rel=file.relative_to(copied).as_posix();observed[rel]=sha(file.read_bytes())
                if file.suffix=='.jsonl':
                    for item in rows('retained/native-sessions/'+rel):
                        if item.get('type')=='session_meta': ids.add(item.get('payload',{}).get('id'))
        need(observed==sessions and ids=={source,target}, 'retained native session identities differ')
    return {'valid':True,'scenario':'release-recovery','providerRequests':4,'sourceThreadId':source,'targetThreadId':target,
        'sourceConnectionId':source_binding['connectionId'],'successorConnectionId':successor_binding['connectionId'],
        'revision':after['revision'],'claimLimit':'Controlled native normal-release ACK loss and successor finalization only; no model autonomy, business outcome or full acceptance.'}


class SyntheticReleaseRecoveryOracleTests(unittest.TestCase):
    """SYNTHETIC inspector fixtures; never native execution or acceptance evidence.

    Only the existing
    model-free Node mock runs. Versions, processes, provider and native frames are
    explicit stubs; actual repository source bytes are copied into each temp tree.
    """
    SOURCES = (
        'runtime/carrier-handoff.cjs', 'runtime/carrier-recorder.cjs',
        'runtime/codex-connection.cjs', 'runtime/codex-context.cjs',
        'runtime/task-checkpoint.cjs', 'tests/product/carrier_handoff_host.cjs',
        'tests/product/test_carrier_handoff.py', 'scripts/observe_codex_lifecycle.py',
        'scripts/observe_codex_entry.py', 'scripts/codex_rpc.py',
        'scripts/inspect_native_resources.py',
    )

    @classmethod
    def setUpClass(cls):
        cls.mock = CarrierHandoffTests().run_case(
            'release-unsubscribe-throw', releaseRecovery='cross-controller')

    def test_shared_driver_context_callback_preserves_observation(self):
        # Exercise the actual nested handler without starting its native owner.
        import ast
        tree = ast.parse(Path(__file__).read_text(encoding='utf-8'))
        owner = next(n for n in tree.body if isinstance(n, ast.FunctionDef)
                     and n.name == 'native_release_recovery_integration')
        handler = next(n for n in ast.walk(owner) if isinstance(n, ast.FunctionDef)
                       and n.name == 'source_handler')
        saved = []
        namespace = {'root': self.root, 'save': lambda path, value: saved.append((path, value))}
        exec(compile(ast.Module(body=[handler], type_ignores=[]), '<actual-source-handler>', 'exec'), namespace)
        invoke = namespace['source_handler']
        for observation in ({'state':'unknown','sourceReleaseAllowed':False},
                            {'state':'window-observed','sourceReleaseAllowed':False,'windowTokens':400000}):
            self.assertEqual(invoke({'kind':'sourceContext','args':[observation]}), observation)
            self.assertEqual(saved[-1], (self.root/'retained/owned-source-context.json', observation))
        for args in ([], [None], [{}, {}], [{'state':'invented','sourceReleaseAllowed':False}],
                     [{'state':'unknown','sourceReleaseAllowed':True}],
                     [{'state':'unknown','sourceReleaseAllowed':False,'windowTokens':1}]):
            with self.subTest(args=args), self.assertRaises(ValueError):
                invoke({'kind':'sourceContext','args':args})
        self.assertEqual(len(saved), 2)

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='SYNTHETIC-release-oracle-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.make_fixture()

    @staticmethod
    def clone(value):
        return json.loads(json.dumps(value))

    def write(self, relative, value):
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value, indent=2) + '\n', encoding='utf-8')

    def read(self, relative):
        return json.loads((self.root / relative).read_text(encoding='utf-8'))

    def frames(self, relative, values):
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(''.join(json.dumps(row) + '\n' for row in values), encoding='utf-8')

    def read_frames(self, relative):
        return [json.loads(row) for row in (self.root / relative).read_text(
            encoding='utf-8').splitlines() if row.strip()]

    def digest(self, relative):
        return hashlib.sha256((self.root / relative).read_bytes()).hexdigest()

    def sync_prior_and_hashes(self):
        """Keep derived bindings current so negative tests reach their named gate."""
        prior = self.read('retained/release-successor-config.json')
        prior['prior'].update(
            sourceDone=self.read('retained/release-source-result.json'),
            resourceReceipt=self.read('retained/release-source-resources.json'),
            sourceHash=self.digest('retained/release-source-result.json'))
        self.write('retained/release-successor-config.json', prior)
        post = self.read('poststate.json')
        post['configHashes'] = {phase:self.digest('retained/' + phase + '-config.json')
                                for phase in ('release-source', 'release-successor')}
        self.write('poststate.json', post)
        for phase in ('release-source', 'release-successor'):
            resource = self.read('retained/'+phase+'-resources.json')
            resource['configSha256'] = post['configHashes'][phase]
            self.write('retained/'+phase+'-resources.json', resource)
        # Updating resource binding changes the prior embedded source receipt.
        prior = self.read('retained/release-successor-config.json')
        prior['prior']['resourceReceipt'] = self.read('retained/release-source-resources.json')
        self.write('retained/release-successor-config.json', prior)
        post['configHashes']['release-successor'] = self.digest('retained/release-successor-config.json')
        self.write('poststate.json', post)
        resource = self.read('retained/release-successor-resources.json')
        resource['configSha256'] = post['configHashes']['release-successor']
        self.write('retained/release-successor-resources.json', resource)

    def make_fixture(self):
        for name in ('workspace', 'retained', 'native'):
            (self.root / name).mkdir()
        (self.root / 'SYNTHETIC-NOT-NATIVE-EVIDENCE.txt').write_text(
            'SYNTHETIC unit-test data. All native/provider/version/process claims are stubs.\n',
            encoding='utf-8')
        keep = b'SYNTHETIC protected input; no native host execution.\n'
        (self.root / 'workspace/keep.txt').write_bytes(keep)
        (self.root / 'retained/keep.txt').write_bytes(keep)
        mock = self.clone(self.mock)
        state = next(s for s in reversed(mock['snapshots'])
                     if s['phase'] == 'release-authorized' and 'failure' in s)
        final = mock['releaseRecovery']['first']['result']
        old_lease = self.clone(state['expectedLease'])
        first = {'revision':final['recorderRevision']-1, 'state':state, 'lease':old_lease}
        end = mock['releaseRecovery']['ledgerAfterFirst']['state']
        lease = {**old_lease, 'token':'SYNTHETIC-rotated-fence'}
        final['lease'] = self.clone(lease)
        final['settle']['lease'] = self.clone(lease)
        after = {'revision':first['revision']+1, 'state':end, 'lease':lease}
        plan = state['plan']; source = state['source']['threadId']; target = state['target']['threadId']
        ref = state['pendingEffect']['requestRef']
        request = {'id':ref['requestId'], 'method':'thread/unsubscribe', 'params':{'threadId':source}}
        fault = {'requestRef':ref, 'request':request, 'response':{'status':'unsubscribed'}}
        controller = 'windows-job-object' if os.name == 'nt' else 'posix-session-process-group'
        identities = {
            'codex':{'path':str(self.root/'SYNTHETIC-codex-stub'), 'version':'fixture-host', 'sha256':'a'*64},
            'node':{'path':str(self.root/'SYNTHETIC-node-stub'), 'version':'SYNTHETIC-node-version', 'sha256':'b'*64}}
        argv = [identities['codex']['path'], 'app-server']
        hashes = {}
        for name in self.SOURCES:
            actual = ROOT / name
            retained = self.root / 'retained/executed-sources' / name
            retained.parent.mkdir(parents=True, exist_ok=True)
            source_bytes = actual.read_bytes()
            retained.write_bytes(source_bytes)
            hashes[str(actual)] = hashlib.sha256(source_bytes).hexdigest()
        manifest = {'scenario':'release-recovery', 'synthetic':True,
                    'claimLimit':'SYNTHETIC inspector unit test only; no native acceptance.',
                    'evidence':str(self.root), 'sourceRoot':str(ROOT),
                    'resourceController':controller, 'identities':identities,
                    'sourceHashes':hashes, 'keepSha256':hashlib.sha256(keep).hexdigest(),
                    'sharedConfigBefore':{'synthetic':True, 'present':False}}
        self.write('manifest.json', manifest)
        post = {'codexSha256After':identities['codex']['sha256'],
                'nodeSha256After':identities['node']['sha256'],
                'sourceHashesAfter':hashes, 'sharedConfigAfter':manifest['sharedConfigBefore'],
                'providerRequests':4, 'realModelCalls':0, 'credentialsObserved':False,
                'keepPreserved':True, 'providerClosed':True, 'configHashes':{}}
        self.write('poststate.json', post)
        closure = {'exitCode':0, 'nativeCloseCode':0, 'nativeStreamsClosed':True,
                   'transportCloseError':None, 'recorderCloseError':None,
                   'nativePid':900000001, 'nativeArgv':argv}
        old = {**closure, 'result':None, 'error':mock['error'], 'plan':plan,
               'releaseLoss':{'record':first, 'plan':plan, 'fault':fault}}
        turns = [dict(id=item['turnId'], status='completed', items=[{
            'type':'userMessage', 'content':[{'type':'text', 'text':text, 'text_elements':[]}]}])
            for item,text in zip([*state['intakeTurns'],state['continuationTurn']],
                                 [plan['handoffText'],plan['continuation']['input']])]
        source_read = {'thread':{'id':source, 'ephemeral':False, 'status':{'type':'idle'}}}
        target_read = {'thread':{'id':target, 'ephemeral':False, 'status':{'type':'idle'}, 'turns':turns}}
        new = {**closure, 'nativePid':900000002, 'result':final, 'error':None,
               'releaseRecovery':{'sourceSnapshot':{'record':first},
                   'finalSnapshot':{'record':after}, 'finalized':final,
                   'sourceRead':source_read, 'targetRead':target_read}}
        self.write('retained/release-source-result.json', old)
        self.write('retained/release-successor-result.json', new)
        for ordinal,phase in enumerate(('release-source', 'release-successor')):
            after_process = ({'controller':controller, 'activeProcesses':0} if os.name == 'nt' else
                {'controller':controller, 'activeProcesses':None, 'processGroupState':'absent',
                 'processGroupId':900000001+ordinal, 'rootPid':900000001+ordinal, 'rootExitCode':0})
            resource = {'ownerPid':900000001+ordinal, 'exitCode':0, 'forced':False,
                        'failure':None, 'readerStopped':True, 'released':True,
                        'after':after_process, 'startedMonotonic':1.0+ordinal*2,
                        'closedMonotonic':2.0+ordinal*2, 'synthetic':True,
                        'startedAtMs':1000+ordinal*2000, 'closedAtMs':2000+ordinal*2000,
                        'arguments':[identities['node']['path'],str(ROOT/'tests/product/carrier_handoff_host.cjs')]}
            self.write('retained/'+phase+'-resources.json', resource)
            config = {'binding':state['connection'] if ordinal == 0 else
                      {'connectionId':'new-controller-connection', 'hostVersion':'fixture-host'},
                      'nativeLogRoot':str(self.root/'native'/phase),
                      'recorderPath':str(self.root/'retained/release-recovery-carrier.sqlite'),
                      'argv':argv, 'synthetic':True}
            if ordinal == 0: config.update(releaseAckLoss=True)
            else: config.update(mode='native-release-recovery', prior={'sourceRoot':str(self.root)})
            self.write('retained/'+phase+'-config.json', config)
        settings = {'cwd':str(self.root/'workspace'), 'model':'fixture-no-model',
                    'modelProvider':'accord_fixture', 'approvalPolicy':'never',
                    'sandbox':'read-only', 'sandboxPolicy':{'type':'readOnly'}, 'ephemeral':False}
        source_calls = [{'id':'SYNTHETIC-start-'+str(n), 'method':'thread/start',
                         'params':self.clone(settings)} for n in range(2)]
        turn_inputs = ['SYNTHETIC fixed source task.',plan['handoffText'],plan['continuation']['input']]
        source_calls += [{'id':'SYNTHETIC-turn-'+str(n), 'method':'turn/start',
                          'params':{'threadId':thread,'input':[{'type':'text','text':text}]}}
                         for n,(thread,text) in enumerate(zip([source,target,target],turn_inputs))]
        source_calls += [request]
        self.frames('native/release-source/requests.jsonl', source_calls)
        start_replies = [{'id':call['id'], 'result':{**self.clone(settings),
            'sandbox':{'type':'readOnly'},
            'thread':{'id':thread, 'ephemeral':False, 'cwd':settings['cwd']}}}
            for call,thread in zip(source_calls[:2],[source,target])]
        turn_ids = ['SYNTHETIC-source-turn',state['intakeTurns'][0]['turnId'],state['continuationTurn']['turnId']]
        turn_replies = []
        for call,turn_id in zip(source_calls[2:5],turn_ids):
            turn_replies += [{'id':call['id'],'result':{'turn':{'id':turn_id}}},
                             {'method':'turn/completed','params':{'threadId':call['params']['threadId'],
                              'turn':{'id':turn_id,'status':'completed','items':[]}}}]
        self.frames('native/release-source/stdout.jsonl', [*start_replies,*turn_replies,
                    {'id':request['id'], 'result':fault['response']}])
        successor_calls = [{'id':'SYNTHETIC-init', 'method':'initialize', 'params':{}},
                           {'method':'initialized', 'params':{}},
                           {'id':'SYNTHETIC-read-source', 'method':'thread/read', 'params':{'threadId':source}},
                           {'id':'SYNTHETIC-read-target', 'method':'thread/read', 'params':{'threadId':target,'includeTurns':True}}]
        self.frames('native/release-successor/requests.jsonl', successor_calls)
        self.frames('native/release-successor/stdout.jsonl', [
            {'id':'SYNTHETIC-read-source','result':source_read},
            {'id':'SYNTHETIC-read-target','result':target_read}])
        self.write('cleanup.json', {'ownedRootsRemoved':['home','state','temp'],
            'workspaceRetained':True, 'nativeSessionEvidenceRetained':True})
        version_resource = self.read('retained/release-source-resources.json')
        for identity,item in identities.items():
            version_resource = self.clone(version_resource)
            version_resource['arguments'] = [item['path'],'--version']
            self.write('retained/version-'+identity+'-resources.json', version_resource)
            (self.root/'retained'/('version-'+identity+'-stdout.txt')).write_text(item['version']+'\n',encoding='utf-8')
        self.frames('retained/provider-requests.jsonl', [
            {'ordinal':ordinal,'request':{'model':'fixture-no-model'},'synthetic':True}
            for ordinal in range(1,5)])
        for ordinal in range(1,5):
            self.write('retained/provider-response-'+str(ordinal)+'.json',
                       {'transportStatus':'completed','synthetic':True})
        home_hashes = {}
        for thread in (source,target):
            relative = 'sessions/SYNTHETIC-'+thread+'.jsonl'
            self.frames('retained/native-home/'+relative,[{'type':'session_meta','payload':{'id':thread,'synthetic':True}}])
            self.frames('retained/native-sessions/SYNTHETIC-'+thread+'.jsonl',
                        [{'type':'session_meta','payload':{'id':thread,'synthetic':True}}])
            home_hashes[relative] = self.digest('retained/native-home/'+relative)
        self.write('retained/native-home-sha256.json',home_hashes)
        self.write_sqlite(after)
        self.sync_prior_and_hashes()

    def write_sqlite(self, record):
        db = sqlite3.connect(self.root/'retained/release-recovery-carrier.sqlite')
        try:
            db.execute('CREATE TABLE IF NOT EXISTS scopes (scope_ref TEXT, writer_thread_id TEXT, active_transfer_id TEXT, fence_token TEXT)')
            db.execute('CREATE TABLE IF NOT EXISTS transfers (transfer_id TEXT, scope_ref TEXT, revision INTEGER, state_json TEXT, settled INTEGER)')
            db.execute('DELETE FROM scopes'); db.execute('DELETE FROM transfers')
            state = record['state']; plan = state['plan']
            db.execute('INSERT INTO scopes VALUES (?,?,?,?)', (plan['scopeRef'],state['writerThreadId'],plan['transferId'],record['lease']['token']))
            db.execute('INSERT INTO transfers VALUES (?,?,?,?,0)', (plan['transferId'],plan['scopeRef'],record['revision'],json.dumps(state)))
            db.commit()
        finally:
            db.close()
        self.sync_carrier_hash()

    def sync_carrier_hash(self):
        post = self.read('poststate.json')
        post['carrierSha256'] = self.digest('retained/release-recovery-carrier.sqlite')
        self.write('poststate.json',post)

    def reject(self, message):
        with self.assertRaisesRegex(ValueError, re.escape(message)):
            inspect_release_recovery_evidence(self.root)

    def test_synthetic_valid_tree_passes_independent_inspector(self):
        verdict = inspect_release_recovery_evidence(self.root)
        self.assertTrue(verdict['valid'])
        self.assertEqual(verdict['scenario'], 'release-recovery')
        self.assertTrue(self.read('manifest.json')['synthetic'])

    def test_source_direct_process_must_have_exited(self):
        old = self.read('retained/release-source-result.json'); old['nativeCloseCode'] = None
        self.write('retained/release-source-result.json', old); self.sync_prior_and_hashes()
        self.reject('native direct process/stream closure missing')

    def test_source_controller_cannot_claim_released_with_active_processes(self):
        resource = self.read('retained/release-source-resources.json')
        if os.name == 'nt': resource['after']['activeProcesses'] = 1
        else: resource['after'].update(processGroupState='alive',rootExitCode=None)
        self.write('retained/release-source-resources.json',resource)
        self.sync_prior_and_hashes()
        self.reject('owned controller/reader/group closure missing')

    def test_source_ack_request_id_must_match_lost_request(self):
        path = 'native/release-source/stdout.jsonl'; frames = self.read_frames(path)
        frames[-1]['id'] = 'SYNTHETIC-unrelated-ACK'; self.frames(path,frames)
        self.reject('original native release ACK was not observed before loss')

    def test_duplicate_release_ack_is_not_unique_evidence(self):
        path = 'native/release-source/stdout.jsonl'; frames = self.read_frames(path)
        frames.append(self.clone(frames[-1])); self.frames(path,frames)
        self.reject('original native release ACK was not observed before loss')

    def test_successor_cannot_precede_source_controller_close(self):
        resource = self.read('retained/release-successor-resources.json'); resource['startedMonotonic'] = 1.5
        self.write('retained/release-successor-resources.json', resource)
        self.reject('successor started before original resources closed')

    def test_successor_requires_distinct_connection(self):
        config = self.read('retained/release-successor-config.json')
        config['binding']['connectionId'] = 'test-connection'
        self.write('retained/release-successor-config.json', config); self.sync_prior_and_hashes()
        self.reject('actual connection/version bindings differ')

    def test_release_ack_must_exist_in_raw_frames(self):
        path = 'native/release-source/stdout.jsonl'
        self.frames(path,[frame for frame in self.read_frames(path) if frame.get('id')!='unsubscribe-original-1'])
        self.reject('original native release ACK was not observed before loss')

    def test_release_ack_must_match_raw_response(self):
        path = 'native/release-source/stdout.jsonl'; frames = self.read_frames(path)
        frames[-1]['result'] = {'status':'still-subscribed'}; self.frames(path,frames)
        self.reject('original native release ACK was not observed before loss')

    def test_successor_cannot_start_extra_turn(self):
        path = 'native/release-successor/requests.jsonl'
        frames = self.read_frames(path); frames.append({'id':'SYNTHETIC-extra','method':'turn/start','params':{}})
        self.frames(path, frames)
        self.reject('successor repeated or expanded native effects')

    def change_target_read(self, mutate):
        new = self.read('retained/release-successor-result.json')
        mutate(new['releaseRecovery']['targetRead']['thread'])
        self.write('retained/release-successor-result.json', new)
        frames = self.read_frames('native/release-successor/stdout.jsonl')
        frames[-1]['result'] = new['releaseRecovery']['targetRead']
        self.frames('native/release-successor/stdout.jsonl', frames)

    def test_exact_target_history_required(self):
        self.change_target_read(lambda thread: thread['turns'].pop(0))
        self.reject('target exact completed history differs')

    def test_original_target_input_required(self):
        self.change_target_read(lambda thread: thread['turns'][0]['items'][0]['content'][0].update(text='SYNTHETIC changed input'))
        self.reject('target original input text differs')

    def test_final_sqlite_is_independently_read(self):
        db = sqlite3.connect(self.root/'retained/release-recovery-carrier.sqlite')
        try: db.execute('UPDATE transfers SET settled=1'); db.commit()
        finally: db.close()
        self.sync_carrier_hash()
        self.reject('durable recorder differs or was settled')

    def test_carrier_bytes_must_match_poststate_hash(self):
        db = sqlite3.connect(self.root/'retained/release-recovery-carrier.sqlite')
        try: db.execute('UPDATE transfers SET settled=1'); db.commit()
        finally: db.close()
        self.reject('final carrier bytes changed after poststate')

    def test_source_turn_ownership_and_order_must_match(self):
        path = 'native/release-source/requests.jsonl'; frames = self.read_frames(path)
        frames[2]['params']['threadId'] = 'target-1'; self.frames(path,frames)
        self.reject('native turn ownership/order differs')

    def test_target_raw_input_request_must_match_plan(self):
        path = 'native/release-source/requests.jsonl'; frames = self.read_frames(path)
        frames[3]['params']['input'] = [{'type':'text','text':'SYNTHETIC altered intake'}]
        self.frames(path,frames)
        self.reject('native target input request differs')

    def test_each_source_turn_requires_raw_start_ack(self):
        path = 'native/release-source/stdout.jsonl'; frames = self.read_frames(path)
        self.frames(path,[frame for frame in frames if frame.get('id')!='SYNTHETIC-turn-0'])
        self.reject('native turn start acknowledgement missing')

    def test_raw_terminal_turn_id_must_match_start_ack(self):
        path = 'native/release-source/stdout.jsonl'; frames = self.read_frames(path)
        terminal = next(frame for frame in frames if frame.get('method')=='turn/completed')
        terminal['params']['turn']['id'] = 'SYNTHETIC-unrelated-turn'; self.frames(path,frames)
        self.reject('native source/intake/continuation terminal missing')

    def test_raw_terminal_requires_completed_status(self):
        path = 'native/release-source/stdout.jsonl'; frames = self.read_frames(path)
        terminal = next(frame for frame in frames if frame.get('method')=='turn/completed')
        terminal['params']['turn']['status'] = 'failed'; self.frames(path,frames)
        self.reject('native source/intake/continuation terminal missing')

    def change_original_and_final_state(self, mutate):
        old = self.read('retained/release-source-result.json')
        new = self.read('retained/release-successor-result.json')
        mutate(old['releaseLoss']['record']['state'])
        mutate(new['releaseRecovery']['finalSnapshot']['record']['state'])
        new['releaseRecovery']['sourceSnapshot']['record'] = old['releaseLoss']['record']
        self.write('retained/release-source-result.json',old)
        self.write('retained/release-successor-result.json',new)
        self.write_sqlite(new['releaseRecovery']['finalSnapshot']['record'])
        self.sync_prior_and_hashes()

    def test_normal_release_attempt_kind_must_be_verified_continuation(self):
        self.change_original_and_final_state(lambda state:state['normalReleaseAttempt'].update(kind='SYNTHETIC-other-kind'))
        self.reject('required original release evidence missing')

    def test_required_original_release_intent_cannot_be_omitted_from_both_records(self):
        self.change_original_and_final_state(lambda state:state.pop('releaseIntent'))
        self.reject('required original release evidence missing')

    def test_final_state_must_preserve_original_failure(self):
        new = self.read('retained/release-successor-result.json')
        del new['releaseRecovery']['finalSnapshot']['record']['state']['failure']
        self.write_sqlite(new['releaseRecovery']['finalSnapshot']['record'])
        self.write('retained/release-successor-result.json', new)
        self.reject('same-recorder CAS lost original evidence or writer')

    def test_original_source_failure_cannot_be_erased(self):
        old = self.read('retained/release-source-result.json')
        del old['releaseLoss']['record']['state']['failure']
        new = self.read('retained/release-successor-result.json')
        new['releaseRecovery']['sourceSnapshot']['record'] = old['releaseLoss']['record']
        self.write('retained/release-source-result.json',old)
        self.write('retained/release-successor-result.json',new)
        self.sync_prior_and_hashes()
        self.reject('original normal-release failure was not retained')

    def test_empty_source_hash_map_cannot_claim_provenance(self):
        manifest = self.read('manifest.json'); manifest['sourceHashes'] = {}
        post = self.read('poststate.json'); post['sourceHashesAfter'] = {}
        self.write('manifest.json',manifest); self.write('poststate.json',post)
        self.reject('necessary execution sources not retained')

    def test_version_binding_cannot_drift(self):
        config = self.read('retained/release-successor-config.json')
        config['binding']['hostVersion'] = 'SYNTHETIC-foreign-version'
        self.write('retained/release-successor-config.json',config); self.sync_prior_and_hashes()
        self.reject('actual connection/version bindings differ')

    def test_cleanup_flags_cannot_hide_actual_home_residue(self):
        (self.root/'home').mkdir()
        (self.root/'home/SYNTHETIC-residue').write_text('retained residue', encoding='utf-8')
        self.reject('owned original roots remain after claimed cleanup')

    def test_version_stdout_must_match_original_identity(self):
        (self.root/'retained/version-codex-stdout.txt').write_text('SYNTHETIC-foreign-version\n',encoding='utf-8')
        self.reject('version original receipt differs')

    def test_version_process_must_have_closed(self):
        resource = self.read('retained/version-codex-resources.json'); resource['readerStopped'] = False
        self.write('retained/version-codex-resources.json',resource)
        self.reject('version original receipt differs')

    def test_provider_raw_model_must_be_fixed_fixture(self):
        path = 'retained/provider-requests.jsonl'; frames = self.read_frames(path)
        frames[0]['request']['model'] = 'SYNTHETIC-other-model'; self.frames(path,frames)
        self.reject('fixed provider original receipts differ')

    def test_provider_request_ordinals_must_be_exact_once(self):
        path = 'retained/provider-requests.jsonl'; frames = self.read_frames(path)
        frames[-1]['ordinal'] = 3; self.frames(path,frames)
        self.reject('fixed provider original receipts differ')

    def test_provider_top_level_model_cannot_replace_request_body(self):
        path = 'retained/provider-requests.jsonl'; frames = self.read_frames(path)
        frames[0]['model'] = frames[0].pop('request')['model']; self.frames(path,frames)
        self.reject('fixed provider original receipts differ')

    def test_provider_final_response_must_be_completed(self):
        self.write('retained/provider-response-4.json',{'transportStatus':'failed','synthetic':True})
        self.reject('fixed provider original receipts differ')

    def test_provider_closed_summary_is_required(self):
        post = self.read('poststate.json'); post['providerClosed'] = False
        self.write('poststate.json',post)
        self.reject('fixed provider original receipts differ')

    def test_controller_launch_must_bind_actual_driver(self):
        resource = self.read('retained/release-source-resources.json')
        resource['arguments'][1] = str(ROOT/'SYNTHETIC-other-driver.cjs')
        self.write('retained/release-source-resources.json',resource); self.sync_prior_and_hashes()
        self.reject('actual controller launch/config identity differs')

    def test_source_permission_request_cannot_expand_sandbox(self):
        path = 'native/release-source/requests.jsonl'; frames = self.read_frames(path)
        frames[0]['params']['sandbox'] = 'danger-full-access'; self.frames(path,frames)
        replies = self.read_frames('native/release-source/stdout.jsonl')
        replies[0]['result']['sandbox'] = {'type':'dangerFullAccess'}
        self.frames('native/release-source/stdout.jsonl',replies)
        self.reject('native fixture permission/model request differs')

    def test_source_actual_permission_cannot_override_safe_request(self):
        path = 'native/release-source/stdout.jsonl'; frames = self.read_frames(path)
        frames[0]['result']['sandbox'] = {'type':'dangerFullAccess'}; self.frames(path,frames)
        self.reject('native fixture actual permission/model differs')

    def test_native_home_inventory_must_match_retained_bytes(self):
        self.frames('retained/native-home/sessions/SYNTHETIC-source-1.jsonl',
                    [{'type':'session_meta','payload':{'id':'SYNTHETIC-changed'}}])
        self.reject('native home preservation differs')

    def test_session_identity_must_be_original_source_and_target(self):
        relative = 'sessions/SYNTHETIC-source-1.jsonl'
        frames = [{'type':'session_meta','payload':{'id':'SYNTHETIC-foreign-source'}}]
        self.frames('retained/native-home/'+relative,frames)
        self.frames('retained/native-sessions/SYNTHETIC-source-1.jsonl',frames)
        hashes = self.read('retained/native-home-sha256.json')
        hashes[relative] = self.digest('retained/native-home/'+relative)
        self.write('retained/native-home-sha256.json',hashes)
        self.reject('retained native session identities differ')

    def test_session_copy_must_match_native_home(self):
        self.frames('retained/native-sessions/SYNTHETIC-source-1.jsonl',
                    [{'type':'session_meta','payload':{'id':'SYNTHETIC-foreign-copy'}}])
        self.reject('retained native session identities differ')

    def test_protected_input_original_hash_cannot_be_replaced_by_matching_copies(self):
        changed = b'SYNTHETIC replacement of both protected copies.\n'
        (self.root/'workspace/keep.txt').write_bytes(changed)
        (self.root/'retained/keep.txt').write_bytes(changed)
        self.reject('protected workspace changed')


def native_integration(codex, evidence, scenario=None):
    """Explicit model-free integration; reuse existing transport/fixture/jobs.

    The test controller supplies a scoped durable ledger and fixture verdicts.
    It proves protocol execution, not autonomous timing or semantic takeover.
    """
    if scenario == 'release-recovery':
        return native_release_recovery_integration(codex, evidence)
    sys.path.insert(0, str(ROOT))
    from scripts.observe_codex_lifecycle import (_App, _Fixture, _argv, _codex_version, _owned_environment,
        _new_controller, _spawn_options, _wait_job, _released, _remove_owned_tree, save)
    from scripts.codex_rpc import BoundedRpc
    scenarios = (scenario,) if scenario else ('success','reject-intake','extra-context','source-proposal','source-event-proposal','ephemeral-source','owned-connection','source-context')
    if any(s not in ('success','reject-intake','extra-context','source-proposal','source-event-proposal','ephemeral-source','owned-connection','source-context','websocket-connection','recover-receipt','finalize-receipt') for s in scenarios):
        raise ValueError('unknown native handoff scenario')
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
    version = (None if scenarios==('finalize-receipt',) else
               subprocess.check_output([str(codex),'--version'],timeout=10,text=True).strip())
    manifest={'evidence':str(root),'codex':str(codex),'node':str(node),
        'ownedRoots':{name:str(root/name) for name in ('home','workspace','state','temp')},
        'limits':{'requestSeconds':30,'recoverySeconds':15,'providerRequestBytes':2*1024*1024,'providerRequests':31},
        'resourceController':'windows-job-object' if os.name=='nt' else 'posix-session-process-group'}
    if scenarios in (('websocket-connection',),('recover-receipt',),('finalize-receipt',)):
        manifest['limits']['providerRequests']=4
    sources=[ROOT/'runtime/carrier-handoff.cjs',DRIVER,Path(__file__),ROOT/'scripts/observe_codex_lifecycle.py',
             ROOT/'scripts/observe_codex_entry.py',ROOT/'scripts/codex_rpc.py',ROOT/'scripts/inspect_native_resources.py']
    if any(s in ('owned-connection','source-context','websocket-connection','recover-receipt','finalize-receipt') for s in scenarios):
        sources.extend(ROOT/'runtime'/name for name in ('codex-connection.cjs','task-checkpoint.cjs','codex-context.cjs'))
    if 'finalize-receipt' in scenarios:
        sources.append(ROOT/'runtime/carrier-recorder.cjs')
    manifest['sourceHashes']={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in sources}
    if scenarios==('finalize-receipt',):
        manifest.update(scenario='finalize-receipt',sourceRoot=str(ROOT),
                        sharedConfigBefore=_shared_config_observation())
    source_snapshot=root/'retained/executed-sources'
    source_snapshot.mkdir()
    for path in sources:
        destination=source_snapshot/path.relative_to(ROOT)
        destination.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(path,destination)
        if hashlib.sha256(destination.read_bytes()).hexdigest()!=manifest['sourceHashes'][str(path)]:
            raise ValueError('execution source changed during preparation')
    manifest['claimLimit']='Native method execution with fixed localhost replies and a test verifier; no model judgment, ordinary Desktop control, autonomous timing or whole acceptance.'
    if any(s in ('recover-receipt','finalize-receipt') for s in scenarios):
        manifest['faultInjection']='After native continuation start returns, the adapter callback reports acknowledgement loss. Raw native response and surviving caller remain available; not a network disconnect or controller/power loss.'
    if scenarios==('finalize-receipt',):
        env=_owned_environment(manifest)
        version=_codex_version(codex,manifest,'source',env)
        node_version=_codex_version(node,manifest,'node',env)
        manifest['identities']={
            'codex':{'path':str(codex),'version':version,
                     'sha256':hashlib.sha256(codex.read_bytes()).hexdigest()},
            'node':{'path':str(node),'version':node_version,
                    'sha256':hashlib.sha256(node.read_bytes()).hexdigest()}}
    else:
        save(root/'manifest.json',manifest)
        env=_owned_environment(manifest)
    if scenarios==('finalize-receipt',): save(root/'manifest.json',manifest)
    proposal_state = {'next':False}
    fixture=_Fixture(manifest, lambda body, ordinal: proposal_fixture_item(body, ordinal, proposal_state))
    app=None
    websocket_listener=None
    results=[]
    owned_threads=set()
    finalize_config_hash=None
    deadline=time.monotonic()+260
    ledger_db=None
    if scenarios!=('finalize-receipt',):
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
        if not all(s in ('owned-connection','source-context','websocket-connection','recover-receipt','finalize-receipt') for s in scenarios):
            app=_App(manifest,'carrier-controller',_argv(manifest,fixture,('-c','features.plugins=false','-c','features.hooks=false')),env,deadline)
            app.initialize()
        for scenario in scenarios:
            direct_connection = scenario in ('owned-connection','source-context','websocket-connection','recover-receipt','finalize-receipt')
            websocket_endpoint = None
            if scenario=='websocket-connection':
                token=secrets.token_urlsafe(32)
                token_hash=hashlib.sha256(token.encode()).hexdigest()
                websocket_listener=_App(manifest,'owned-websocket-listener',_argv(manifest,fixture,
                    ('-c','features.plugins=false','-c','features.hooks=false','--listen','ws://127.0.0.1:0',
                     '--ws-auth','capability-token','--ws-token-sha256',token_hash)),env,deadline)
                ready_deadline=min(deadline,time.monotonic()+15)
                while websocket_endpoint is None:
                    banner=(websocket_listener.root/'stderr.txt').read_text(encoding='utf-8',errors='replace')
                    matched=re.search(r'listening on:\s*(ws://127\.0\.0\.1:[1-9][0-9]*)',banner)
                    if matched: websocket_endpoint=matched[1];break
                    if websocket_listener.process.poll() is not None or time.monotonic()>=ready_deadline:
                        raise RuntimeError('owned authenticated WebSocket listener unavailable')
                    time.sleep(0.05)
                save(root/'retained/websocket-endpoint.json',{'endpoint':websocket_endpoint,
                    'authentication':'temporary token in child environment only; listener uses hash',
                    'processOwner':'bounded test controller, not shared daemon'})
            proposal_case = scenario in ('source-proposal','source-event-proposal')
            source_settings={'model':'fixture-no-model','modelProvider':'accord_fixture',
                'cwd':manifest['ownedRoots']['workspace'],'sandbox':'read-only','approvalPolicy':'never'}
            if scenario=='ephemeral-source': source_settings['ephemeral']=True
            if proposal_case:
                source_settings['dynamicTools']=[{'type':'function','name':PROPOSAL_TOOL,
                    'description':'Submit a handoff proposal; the controller records it before acknowledgement and dispatches after this turn ends.',
                    'inputSchema':{'type':'object','properties':{'reason':{'type':'string'}},
                                   'required':['reason'],'additionalProperties':False}}]
                proposal_state['next']=True
            if direct_connection:
                source,turn,proposed='pending-source','pending-turn',{'direct':True}
                proposal_state['next']=True
                proposal_state['contextRemaining']=2 if scenario=='source-context' else 0
                native_log=root/'native'/scenario
                native_log.mkdir()
            else:
                source=request('thread/start',source_settings)['thread']['id']
                source_prompt = ('Submit one handoff proposal for the bound fixed task, then finish this source turn without other actions.'
                                 if proposal_case else 'Retain the fixed fixture task; do not call tools.')
                turn=request('turn/start',{'threadId':source,'input':[{'type':'text','text':source_prompt}]})['turn']['id']
                proposed=source_proposal(source,turn) if proposal_case else None
                if proposed is None and terminal(source,turn)['params']['turn']['status']!='completed':
                    raise RuntimeError('source fixture turn did not complete')
            now=int(time.time()*1000)
            plan={'transferId':scenario,'scopeRef':'fixture-'+scenario,'authorityRef':'fixture-authority-v1','stateRef':'fixture-source-v1',
                'source':{'threadId':source, **({'turnId':turn} if proposed else {})},'target':{'cwd':manifest['ownedRoots']['workspace'],'model':'fixture-no-model','modelProvider':'accord_fixture'},
                'handoffText':'Read-only intake of the fixed fixture task; preserve keep.txt and do not call tools.',
                'continuation':{'input':'Continue the accepted read-only fixture task; preserve keep.txt and do not call tools.','sandboxPolicy':{'type':'readOnly'}},
                'deadlineMs':now+60000,'recoveryDeadlineMs':now+75000}
            ledger=root/'retained'/f'{scenario}-ledger.json'
            if scenario!='finalize-receipt':
                ledger_db.execute('INSERT INTO scopes VALUES (?,?,NULL,NULL)',(plan['scopeRef'],source))
            intake_reviews=0
            messages=root/'retained'/f'{scenario}-bridge.jsonl'
            job=_new_controller();proc=None;reader=None;inbox=queue.Queue();result=None
            forced=False;bridge_failure=None
            with (root/'retained'/f'{scenario}-stderr.txt').open('wb') as errors:
                try:
                    driver_env={**env,'ACCORD_TEST_CONTROL_TOKEN':token} if websocket_endpoint else env
                    proc=subprocess.Popen([str(node),str(DRIVER)],stdin=subprocess.PIPE,stdout=subprocess.PIPE,
                        stderr=errors,cwd=ROOT,env=driver_env,**_spawn_options())
                    job.attach_and_resume(proc)
                    def consume(stream=proc.stdout):
                        try:
                            for line in stream:
                                if len(line)>4*1024*1024: raise ValueError('bridge message too large')
                                inbox.put(json.loads(line))
                        except BaseException as error: inbox.put(error)
                        finally: inbox.put(None)
                    reader=threading.Thread(target=consume,daemon=True);reader.start()
                    binding={'connectionId':scenario if direct_connection else app.root.name,'hostVersion':version}
                    config={'mode':'native','plan':plan,'binding':binding}
                    if proposed is not None: config['nativeProposal']={**binding,**proposed}
                    if scenario=='source-event-proposal': config['nativeEventProposal']=True
                    if direct_connection:
                        config={'mode':'native-connection','plan':plan,'binding':binding,'nativeLogRoot':str(native_log),
                            'contextRead':scenario=='source-context',
                            'recoverReceipt':scenario in ('recover-receipt','finalize-receipt'),
                            'finalizeReceipt':scenario=='finalize-receipt',
                            **({'recorderPath':str(root/'retained/finalize-receipt-carrier.sqlite')}
                               if scenario=='finalize-receipt' else {}),
                            'argv':_argv(manifest,fixture,('-c','features.plugins=false','-c','features.hooks=false'))}
                        if websocket_endpoint: config['websocketEndpoint']=websocket_endpoint
                    if scenario=='finalize-receipt':
                        save(root/'retained/finalize-receipt-config.json',config)
                        finalize_config_hash=hashlib.sha256(
                            (root/'retained/finalize-receipt-config.json').read_bytes()).hexdigest()
                    proc.stdin.write((json.dumps(config)+'\n').encode());proc.stdin.flush()
                    while True:
                        message=inbox.get(timeout=max(0.01,min(40,deadline-time.monotonic())))
                        if message is None: raise RuntimeError('bridge exited before result')
                        if isinstance(message,BaseException): raise message
                        with messages.open('a',encoding='utf-8') as out: out.write(json.dumps(message)+'\n')
                        if message.get('kind')=='done': result=message;break
                        args=message['args']
                        try:
                            if message['kind']=='sourceReady':
                                if not direct_connection or source!='pending-source':
                                    raise ValueError('source binding is not available')
                                observed_source,observed_turn=args
                                if (observed_source.get('cwd')!=plan['target']['cwd']
                                        or observed_source.get('model')!=plan['target']['model']):
                                    raise ValueError('native source settings differ')
                                source=observed_source['thread']['id'];turn=observed_turn['turn']['id']
                                plan['source']={'threadId':source,'turnId':turn}
                                if scenario!='finalize-receipt':
                                    ledger_db.execute('UPDATE scopes SET owner=? WHERE scope=? AND owner=?',
                                        (source,plan['scopeRef'],'pending-source'))
                                save(root/'retained/owned-source-binding.json',{'start':observed_source,'turn':observed_turn})
                                value={'bound':True}
                            elif message['kind']=='sourceContext':
                                value=args[0]
                                save(root/'retained/owned-source-context.json',value)
                                # The first pending dynamic call can precede the
                                # host's first usage event. Do not invent capacity.
                                if (value.get('state') not in ('unknown','window-observed')
                                        or value.get('sourceReleaseAllowed') is not False):
                                    raise ValueError('native source context contract differs')
                                if value.get('state')=='unknown' and value.get('windowTokens') is not None:
                                    raise ValueError('unknown native capacity must not be promoted')
                            elif message['kind']=='request': value=request(args[0],args[1],args[2])
                            elif message['kind']=='waitTerminal': value=terminal(args[0],args[1],args[2])
                            elif message['kind']=='begin':
                                value=record_begin(*args)
                            elif message['kind']=='readRecord':
                                transfer_id,scope_ref=args
                                if transfer_id!=scenario or scope_ref!=plan['scopeRef']:
                                    raise ValueError('foreign recovery record')
                                ledger_db.execute('BEGIN')
                                try:
                                    row=ledger_db.execute('SELECT revision,state FROM transfers WHERE id=?',(transfer_id,)).fetchone()
                                    owner,active,token=ledger_db.execute('SELECT owner,active,token FROM scopes WHERE scope=?',(scope_ref,)).fetchone()
                                    value={'revision':row[0],'state':json.loads(row[1]),'lease':{
                                        'scopeRef':scope_ref,'transferId':active,'token':token,'writerThreadId':owner}}
                                    ledger_db.execute('COMMIT')
                                except BaseException:
                                    ledger_db.execute('ROLLBACK');raise
                            elif message['kind']=='compareAndSet':
                                if args[2].get('phase')=='continuation-reconciled':
                                    before=ledger_db.execute('SELECT revision,state FROM transfers WHERE id=?',(scenario,)).fetchone()
                                    save(root/'retained/reconciliation-before.json',{'revision':before[0],'state':json.loads(before[1])})
                                value=record_cas(*args)
                            elif message['kind'] in ('proposalEvidence','proposalEvents'):
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
                                if message['kind']=='proposalEvents':
                                    anchor=next(i for i,e in enumerate(app.events) if e is proposed)
                                    # Preserve the whole ordered native suffix; the product
                                    # selects correlated receipts, not this test controller.
                                    value=app.events[anchor+1:]
                                    save(root/'retained/source-proposal-events.json',value)
                            elif message['kind']=='verify':
                                stage,facts=args[:2]
                                unchanged=hashlib.sha256((root/'workspace/keep.txt').read_bytes()).hexdigest()==original
                                value={'decision':'allow' if unchanged else 'hold','scopeRef':plan['scopeRef'],'authorityRef':plan['authorityRef'],
                                    'stateRef':plan['stateRef'],'sourceRef':f'fixed-native-fixture:{scenario}:{stage}',
                                    'sourceRecoveryReady':True,'quiesced':True,'noOtherWriters':True,'targetSettingsMatch':True,
                                    'accepted':True,'sourceIdle':True,'singleWriter':True,'effectsVerified':unchanged}
                                value.update(targetInitializationSafe=True,initializationEffectsVerified=True,intakeEffectsVerified=unchanged)
                                if stage=='continuation-reconcile':
                                    value.update(priorAttemptQuiesced=True,receiptVerified=True,reconciliationAuthorized=True)
                                    save(root/'retained/reconciliation-verification.json',{'facts':facts,'verdict':value,
                                        'claimLimit':'Controlled fixed-response verifier; effects checks include protected original and task-owned native read projection. Not production semantic verification.'})
                                if stage=='reconciled-release':
                                    ledger=facts.get('ledger',{});state=ledger.get('state',{});release_input=facts.get('input',{})
                                    source_thread=facts.get('sourceRead',{}).get('thread',{})
                                    target_thread=facts.get('targetRead',{}).get('thread',{})
                                    reconciliation=state.get('reconciliation',{})
                                    expected_turns=[item.get('turnId') for item in state.get('intakeTurns',[])]+[
                                        reconciliation.get('turn',{}).get('turnId')]
                                    observed_turns=target_thread.get('turns',[])
                                    release_ok=(unchanged and release_input.get('transferId')==plan['transferId']
                                        and release_input.get('scopeRef')==plan['scopeRef']
                                        and release_input.get('authorityRef')==plan['authorityRef']
                                        and release_input.get('stateRef')==plan['stateRef']
                                        and release_input.get('releaseKind')=='native-unsubscribe'
                                        and release_input.get('expectedRevision')==ledger.get('revision')
                                        and release_input.get('expectedLease')==ledger.get('lease')
                                        and release_input.get('receiptDigest')==reconciliation.get('receiptDigest')
                                        and state.get('phase')=='continuation-reconciled'
                                        and state.get('pendingEffect') is None and state.get('writer')=='target'
                                        and state.get('writerThreadId')==state.get('target',{}).get('threadId')
                                        and state.get('sourceRecovery')=='retained'
                                        and state.get('reconciliation',{}).get('originalFailure',{}).get('code')=='NATIVE_EFFECT_UNKNOWN'
                                        and facts.get('plan')==state.get('plan')==plan
                                        and facts.get('currentConnection')==facts.get('originalConnection')==binding
                                        and facts.get('reconciliationConnection')==binding
                                        and source_thread.get('id')==state.get('source',{}).get('threadId')
                                        and source_thread.get('status',{}).get('type') in ('idle','notLoaded')
                                        and source_thread.get('ephemeral') is False
                                        and target_thread.get('id')==state.get('target',{}).get('threadId')
                                        and target_thread.get('status',{}).get('type') in ('idle','notLoaded')
                                        and target_thread.get('ephemeral') is False
                                        and [item.get('id') for item in observed_turns]==expected_turns
                                        and all(item.get('status')=='completed' for item in observed_turns)
                                        and facts.get('continuationTurn')==reconciliation.get('turn')
                                        and ledger.get('lease',{}).get('transferId')==plan['transferId']
                                        and ledger.get('lease',{}).get('writerThreadId')==state.get('target',{}).get('threadId'))
                                    value.update(decision='allow' if release_ok else 'hold',
                                        pauseStateVerified=release_ok,receiptVerified=release_ok,
                                        reconciliationAuthorized=release_ok,releaseAuthorized=release_ok,
                                        priorAttemptQuiesced=release_ok,effectsVerified=release_ok,
                                        singleWriter=release_ok,sourceRecoveryReady=release_ok)
                                    save(root/'retained/finalization-verification.json',{'facts':facts,'verdict':value,
                                        'claimLimit':'Controlled exact-receipt release authorization after retained failure and reconciliation; not task completion or general recovery.'})
                                if stage=='reconciled-release-observed':
                                    ledger=facts.get('ledger',{});state=ledger.get('state',{});response=facts.get('nativeResponse')
                                    status=facts.get('nativeStatus');source_id=state.get('source',{}).get('threadId')
                                    observed_ok=(unchanged and status in ('unsubscribed','notSubscribed','notLoaded')
                                        and response==state.get('releaseObservation',{}).get('response')
                                        and status==state.get('releaseObservation',{}).get('nativeStatus')
                                        and state.get('phase')=='release-observed' and state.get('writer')=='target'
                                        and state.get('pendingEffect')=={'method':'thread/unsubscribe','params':{'threadId':source_id}}
                                        and state.get('releaseIntent',{}).get('kind')=='native-unsubscribe'
                                        and state.get('releaseIntent',{}).get('threadId')==source_id
                                        and state.get('releaseIntent',{}).get('sourceConnectionId')==binding['connectionId']
                                        and state.get('releaseIntent',{}).get('currentConnectionId')==binding['connectionId']
                                        and state.get('releaseIntent',{}).get('receiptDigest')==state.get('reconciliation',{}).get('receiptDigest')
                                        and facts.get('currentConnection')==facts.get('originalConnection')==binding
                                        and facts.get('reconciliationConnection')==binding
                                        and ledger.get('lease',{}).get('writerThreadId')==state.get('target',{}).get('threadId')
                                        and ledger.get('revision',0)>facts.get('input',{}).get('expectedRevision',-1))
                                    value.update(decision='allow' if observed_ok else 'hold',
                                        subscriptionReleaseVerified=observed_ok,
                                        sameConnectionSubscriptionReleased=observed_ok,
                                        singleWriter=observed_ok,
                                        subscriptionReleaseEvidenceRef=(
                                            'fixed-native-fixture:finalize-receipt:unsubscribe' if observed_ok else None))
                                    save(root/'retained/finalization-observed-verification.json',{'facts':facts,'verdict':value,
                                        'claimLimit':'Controlled readback of one native source unsubscribe response; no archive, deletion or task-completion claim.'})
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
                except BaseException as error:
                    bridge_failure={'type':type(error).__name__,'message':str(error)}
                    raise
                finally:
                    if proc is not None and proc.poll() is None:
                        forced=True;job.terminate();proc.wait(timeout=15)
                    after=_wait_job(job,time.monotonic()+15)
                    if not _released(after):
                        forced=True;job.terminate();after=_wait_job(job,time.monotonic()+5)
                    if reader: reader.join(2)
                    reader_stopped=not reader or not reader.is_alive()
                    resource={'exitCode':proc.returncode if proc else None,'after':after,'released':_released(after)}
                    if scenario=='finalize-receipt':
                        resource.update(forced=forced,readerStopped=reader_stopped,failure=bridge_failure)
                    save(root/'retained'/f'{scenario}-resources.json',resource)
                    job.close()
                    if reader and reader.is_alive(): raise RuntimeError('bridge reader still alive')
                    if proc and proc.stdout: proc.stdout.close()
            if result is None: raise RuntimeError('missing adapter result')
            stored=(ledger_db.execute('SELECT revision,state FROM transfers WHERE id=?',(scenario,)).fetchone()
                    if ledger_db is not None else None)
            if stored: save(ledger,{'revision':stored[0],'state':json.loads(stored[1])})
            save(root/'retained'/f'{scenario}-result.json',result);results.append(result)
            if scenario in ('success','extra-context','source-proposal','source-event-proposal','ephemeral-source','owned-connection','source-context','websocket-connection'):
                if result['error'] or result['result']['status']!='handed-off':
                    raise RuntimeError('native handoff failed; inspect retained result')
                expected_history=scenario!='ephemeral-source'
                if (result['result']['source']['nativeHistoryRetained'] is not expected_history
                        or result['result']['sourceRecovery']['nativeHistoryRetained'] is not expected_history):
                    raise RuntimeError('source history claim differs from native persistence')
                if scenario=='source-event-proposal' and (result['proposal']['respondCount']!=1
                        or result['proposal']['releaseCount']!=1 or result['proposal']['currentCount']!=1):
                    raise RuntimeError('native event dispatcher lifecycle mismatch')
                if direct_connection and not websocket_endpoint and result.get('exitCode')!=0:
                    raise RuntimeError('owned native connection failed to exit naturally')
                if scenario=='source-context':
                    observations=[v['observation'] for v in result.get('contextReplies',[])]
                    if (len(observations)!=2 or observations[0]['state']!='unknown'
                            or observations[1]['state']!='window-observed'
                            or any(v['sourceReleaseAllowed'] is not False for v in observations)):
                        raise RuntimeError('source context tool did not preserve unknown then observe fresh native usage')
            if scenario=='recover-receipt':
                recovered=result.get('recovery') or {}
                state=json.loads(stored[1]) if stored else {}
                ref=recovered.get('requestRef')
                if (result.get('error',{}).get('code')!='NATIVE_EFFECT_UNKNOWN' or result.get('result') is not None
                        or not ref or result.get('exitCode')!=0 or state.get('phase')!='continuation-reconciled'
                        or state.get('pendingEffect') is not None
                        or state.get('reconciliation',{}).get('originalPendingEffect',{}).get('requestRef')!=ref
                        or state.get('writer')!='target' or state.get('sourceRecovery')!='retained'):
                    raise RuntimeError('lost acknowledgement was not retained under the target writer')
                pending=state['reconciliation']['originalPendingEffect']
                before=json.loads((root/'retained/reconciliation-before.json').read_text(encoding='utf-8'))
                if (before['state']['phase']!='reconciliation-required' or before['state']['pendingEffect']!=pending
                        or state['reconciliation']['originalFailure']!=before['state']['failure']
                        or stored[0]!=before['revision']+1
                        or result['reconciliation']['first']['status']!='continuation-reconciled'
                        or result['reconciliation']['repeated']['status']!='already-reconciled'
                        or result['reconciliation']['repeated']['currentNativeStateChecked'] is not False):
                    raise RuntimeError('reconciliation did not preserve failure or repeated the state transition')
                sent=[json.loads(line) for line in (native_log/'requests.jsonl').read_text(encoding='utf-8').splitlines()]
                received=[json.loads(line) for line in (native_log/'stdout.jsonl').read_text(encoding='utf-8').splitlines()]
                matching=[v for v in sent if v.get('id')==ref['requestId']]
                responses=[v for v in received if v.get('id')==ref['requestId'] and 'method' not in v]
                if (ref.get('connectionId')!=binding['connectionId'] or ref.get('hostVersion')!=version
                        or ref.get('method')!='turn/start' or matching!=[recovered['originalRequest']]
                        or len(responses)!=1 or responses[0].get('result')!=recovered['originalResponse']
                        or matching[0]['params']!=pending['params']):
                    raise RuntimeError('native request reference did not locate the exact raw receipt')
                target=matching[0]['params']['threadId'];turn_id=responses[0]['result']['turn']['id']
                observed=recovered['targetRead']['thread']
                turns=[v for v in observed['turns'] if v['id']==turn_id]
                native_turns=[v for v in sent if v.get('method')=='turn/start' and v.get('params',{}).get('threadId')==target]
                scope=ledger_db.execute('SELECT owner,active FROM scopes WHERE scope=?',(plan['scopeRef'],)).fetchone()
                if (observed['id']!=target or len(turns)!=1 or turns[0]['status']!='completed'
                        or len(native_turns)!=2 or scope!=(target,scenario)
                        or any(v.get('method') in ('thread/unsubscribe','turn/interrupt') for v in sent)):
                    raise RuntimeError('recovery replayed work or lost original turn/writer ownership')
                save(root/'retained/recovery-readback.json',{'requestRef':ref,'targetThreadId':target,
                    'continuationTurnId':turn_id,'nativeTurnCompleted':True,'targetWriterRetained':True,
                    'targetTurnStarts':len(native_turns),'sourceSubscriptionReleased':False,
                    'reconciledRevision':stored[0],'pendingEffectCleared':True,'originalFailureRetained':True,
                    'repeatedReconciliation':'already-reconciled',
                    'claimLimit':manifest['faultInjection']})
            if scenario=='finalize-receipt':
                recovered=result.get('recovery') or {};reconciled=result.get('reconciliation') or {}
                finalized=result.get('finalization') or {};native_log=root/'native/finalize-receipt'
                final=finalized.get('finalized') or {};settled=finalized.get('settled') or {}
                record=finalized.get('record') or {};scope=finalized.get('scope') or {}
                if (result.get('error',{}).get('code')!='NATIVE_EFFECT_UNKNOWN' or result.get('result') is not None
                        or result.get('exitCode')!=0 or result.get('recorderCloseError') is not None
                        or reconciled.get('first',{}).get('status')!='continuation-reconciled'
                        or reconciled.get('repeated',{}).get('status')!='already-reconciled'
                        or final.get('status')!='finalized' or final.get('sourceSubscriptionReleased') is not True
                        or final.get('subscriptionRelease',{}).get('kind')!='native-unsubscribe'
                        or final.get('subscriptionRelease',{}).get('observed') is not True
                        or settled.get('scope',{}).get('activeTransferId') is not None
                        or record.get('state',{}).get('phase')!='source-subscription-released'
                        or record.get('state',{}).get('pendingEffect') is not None
                        or record.get('state',{}).get('reconciliation',{}).get('originalFailure',{}).get('code')!='NATIVE_EFFECT_UNKNOWN'
                        or record.get('state',{}).get('writer')!='target'
                        or scope!=settled.get('scope')):
                    raise RuntimeError('finalized lost-ack state or exact settlement receipt differs')
                sent=[json.loads(line) for line in (native_log/'requests.jsonl').read_text(encoding='utf-8').splitlines()]
                received=[json.loads(line) for line in (native_log/'stdout.jsonl').read_text(encoding='utf-8').splitlines()]
                starts=[v for v in sent if v.get('method')=='thread/start']
                turns=[v for v in sent if v.get('method')=='turn/start']
                unsubscribes=[v for v in sent if v.get('method')=='thread/unsubscribe']
                if (len(starts)!=2 or len(turns)!=3 or len(unsubscribes)!=1
                        or unsubscribes[0].get('params',{}).get('threadId')!=final.get('sourceThreadId')
                        or any(v.get('method') in ('thread/archive','thread/delete') for v in sent)
                        or any(str(v.get('method','')).startswith('account/') for v in sent)):
                    raise RuntimeError('finalization repeated work or changed native lifecycle scope')
                lost_ref=recovered.get('requestRef') or {}
                exact_requests=[v for v in sent if v.get('id')==lost_ref.get('requestId')]
                exact_responses=[v for v in received if v.get('id')==lost_ref.get('requestId') and 'method' not in v]
                if (len(exact_requests)!=1 or len(exact_responses)!=1
                        or exact_requests[0]!=recovered.get('originalRequest')
                        or exact_responses[0].get('result')!=recovered.get('originalResponse')
                        or record['state']['reconciliation']['originalPendingEffect']['requestRef']!=lost_ref):
                    raise RuntimeError('finalized evidence lost the original continuation receipt or failure')
                database_path=root/'retained/finalize-receipt-carrier.sqlite'
                database_path.lstat()
                if (not database_path.is_file() or database_path.is_symlink()
                        or database_path.resolve(strict=True)!=database_path):
                    raise RuntimeError('finalization carrier is not an ordinary file')
                for suffix in ('-wal','-journal'):
                    sidecar=database_path.with_name(database_path.name+suffix)
                    if sidecar.is_symlink() or sidecar.exists() and (not sidecar.is_file() or sidecar.stat().st_size):
                        raise RuntimeError('finalization carrier has uncheckpointed data')
                shared_memory=database_path.with_name(database_path.name+'-shm')
                if shared_memory.is_symlink() or shared_memory.exists() and not shared_memory.is_file():
                    raise RuntimeError('finalization carrier SHM is unsafe')
                database=sqlite3.connect(database_path.as_uri()+'?mode=ro&immutable=1',uri=True)
                try:
                    durable_scope=database.execute(
                        'SELECT scope_ref,writer_thread_id,active_transfer_id,fence_token FROM scopes').fetchall()
                    durable_transfer=database.execute(
                        'SELECT transfer_id,scope_ref,revision,state_json,settled FROM transfers').fetchall()
                finally: database.close()
                if (durable_scope!=[(plan['scopeRef'],final.get('targetThreadId'),None,settled['scope']['token'])]
                        or len(durable_transfer)!=1 or durable_transfer[0][0]!=plan['transferId']
                        or durable_transfer[0][2]!=record.get('revision') or durable_transfer[0][4]!=1
                        or json.loads(durable_transfer[0][3])!=record.get('state')):
                    raise RuntimeError('durable finalized ledger differs from exact receipt')
                save(root/'retained/finalize-readback.json',{'originalFailure':result['error'],
                    'requestRef':lost_ref,'reconciliation':reconciled,'finalization':finalized,
                    'nativeCounts':{'threadStart':len(starts),'turnStart':len(turns),
                        'unsubscribe':len(unsubscribes),'archiveDelete':0},
                    'durableScope':durable_scope,'durableTransfer':durable_transfer,
                    'claimLimit':'Controlled lost-ACK completion, reconciliation, exact source unsubscribe and durable settlement; no repeated turn, model call, archive, delete or general recovery claim.'})
            if scenario=='reject-intake' and (result['error'] is None or any(c['method']=='thread/unsubscribe' for c in result['calls'])): raise RuntimeError('rejected intake released source')
    finally:
        retained={}
        try:
            if app: save(root/'controller-resources.json',app.close())
            if websocket_listener: save(root/'websocket-listener-resources.json',websocket_listener.close(stop_owned=True))
        finally:
            fixture.close()
            if ledger_db is not None: ledger_db.close()
        if (root/'home/sessions').exists():
            shutil.copytree(root/'home/sessions',root/'retained/native-sessions')
            if 'finalize-receipt' in scenarios:
                session_hashes={p.relative_to(root/'retained/native-sessions').as_posix():
                    hashlib.sha256(p.read_bytes()).hexdigest()
                    for p in (root/'retained/native-sessions').rglob('*') if p.is_file() and not p.is_symlink()}
                save(root/'retained/native-sessions-sha256.json',session_hashes)
        if websocket_listener or any(s in ('recover-receipt','finalize-receipt') for s in scenarios):
            native_state=root/'retained/native-home'
            native_state.mkdir()
            native_files=lambda: {p.name:p for p in (root/'home').iterdir() if p.is_file() and not p.is_symlink()}
            before_files=native_files()
            for name, source in before_files.items():
                before=hashlib.sha256(source.read_bytes()).hexdigest()
                destination=native_state/name
                shutil.copyfile(source,destination)
                if (hashlib.sha256(destination.read_bytes()).hexdigest()!=before
                        or hashlib.sha256(source.read_bytes()).hexdigest()!=before):
                    raise RuntimeError('native state retention mismatch')
                retained[name]=before
            if set(native_files())!=set(before_files):
                raise RuntimeError('native state files changed during retention')
            save(root/'retained/native-home-sha256.json',retained)
            shutil.copyfile(root/'workspace/keep.txt',root/'retained/keep.txt')
        save(root/'poststate.json',{'providerRequests':len(fixture.requests),'credentialsObserved':fixture.auth_seen,
            'keepPreserved':hashlib.sha256((root/'workspace/keep.txt').read_bytes()).hexdigest()==original,
            'completedCases':len(results),'claimLimit':manifest['claimLimit'],
            **({'finalizeConfigSha256':finalize_config_hash,'realModelCalls':0,
                'ownedConfigSha256':retained.get('config.toml'),
                'sharedConfigAfter':_shared_config_observation(),
                'carrierSha256':hashlib.sha256((root/'retained/finalize-receipt-carrier.sqlite').read_bytes()).hexdigest(),
                'codexSha256After':hashlib.sha256(codex.read_bytes()).hexdigest(),
                'nodeSha256After':hashlib.sha256(node.read_bytes()).hexdigest(),
                'sourceHashesAfter':{name:hashlib.sha256(Path(name).read_bytes()).hexdigest()
                    for name in manifest['sourceHashes']}}
               if 'finalize-receipt' in scenarios else {})})
    if fixture.auth_seen or len(results)!=len(scenarios): raise RuntimeError('native integration incomplete')
    if scenarios in (('websocket-connection',),('recover-receipt',),('finalize-receipt',)):
        responses=sorted((root/'retained').glob('provider-response-*.json'))
        if (len(fixture.requests)!=4 or {p.name for p in responses}!={f'provider-response-{i}.json' for i in range(1,5)}
                or any(json.loads(p.read_text(encoding='utf-8'))['transportStatus']!='completed' for p in responses)
                or results[0].get('transportKind')!=('websocket' if scenarios==('websocket-connection',) else 'stdio')):
            raise RuntimeError('native composition or fixed-response receipts incomplete')
    cleanup_names=('home','state','temp') if scenarios==('finalize-receipt',) else ('home','workspace','state','temp')
    for name in cleanup_names:
        target=(root/name).resolve(strict=True)
        if target.parent!=root: raise ValueError('owned cleanup root mismatch')
        _remove_owned_tree(target)
    cleanup_receipt=({'ownedRootsRemoved':list(cleanup_names),'workspaceRetained':True,
        'nativeSessionEvidenceRetained':True} if scenarios==('finalize-receipt',) else
        {'ownedRootsRemoved':True,'nativeSessionEvidenceRetained':True})
    save(root/'cleanup.json',cleanup_receipt)
    print(json.dumps({'nativeCases':len(scenarios),'modelCalls':0,'providerRequests':len(fixture.requests),'evidence':str(root)}))


if __name__=='__main__':
    if '--native-codex' in sys.argv:
        import argparse
        p=argparse.ArgumentParser();p.add_argument('--native-codex',required=True);p.add_argument('--evidence',required=True)
        p.add_argument('--scenario')
        a=p.parse_args();native_integration(a.native_codex,a.evidence,a.scenario)
    elif '--inspect-evidence' in sys.argv:
        import argparse
        p=argparse.ArgumentParser();p.add_argument('--inspect-evidence',required=True)
        a=p.parse_args()
        scenario=json.loads((Path(a.inspect_evidence)/'manifest.json').read_text(encoding='utf-8')).get('scenario')
        inspector=inspect_release_recovery_evidence if scenario=='release-recovery' else inspect_finalize_receipt_evidence
        print(json.dumps(inspector(a.inspect_evidence),ensure_ascii=False))
    else: unittest.main()
