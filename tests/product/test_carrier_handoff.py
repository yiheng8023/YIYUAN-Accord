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


def native_integration(codex, evidence, scenario=None):
    """Explicit model-free integration; reuse existing transport/fixture/jobs.

    The test controller supplies a scoped durable ledger and fixture verdicts.
    It proves protocol execution, not autonomous timing or semantic takeover.
    """
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
        a=p.parse_args();print(json.dumps(inspect_finalize_receipt_evidence(a.inspect_evidence),ensure_ascii=False))
    else: unittest.main()
