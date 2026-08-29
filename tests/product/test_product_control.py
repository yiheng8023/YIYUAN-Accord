from contextlib import contextmanager
import hashlib, json, shutil, subprocess, tempfile, unittest
from pathlib import Path
from unittest.mock import patch
from yiyuan_accord.closure import reconcile_closure
from yiyuan_accord.control import (
    _validate_four_surface_mapping, host_check, verify_product,
)
from yiyuan_accord.evidence import (
    _canonical_official_url,
    _behavior_subject_revision_errors,
    _digest,
    _evaluation_contracts,
    _continuity_handoff_bundle,
    _continuity_narrative_hashes,
    _longitudinal_bundle,
    _observation_errors,
    _postcapture_bundle,
    _publishable_payload,
    _sequence_digest,
    _source_amendments,
    _time,
    representative_contract_sha256,
    representative_sample_errors,
)
from yiyuan_accord.guardrails import (
    canonical_goal_objective,
    closeout_sequence_errors,
    projection_evidence_binding_errors,
    projection_observation_errors,
    validate_projection_package,
)
from yiyuan_accord.identity import (
    CONTRACT_RELEASE_RE,
    RELEASE_RE,
    active_tree_errors,
)
ROOT = Path(__file__).resolve().parents[2]
HOOK_PROCESS_TIMEOUT_SECONDS = 15
(C, A, P, G) = ('product/constitution.json', 'product/acceptance.json', 'product/program.json', 'evals/golden-tasks.json')
SOURCE = 'evals/evidence/2026-08-24-v20-representative-source.json'
CURRENT_GT11_SOURCE = 'evals/evidence/2026-08-27-v310-codex-local-regression-source.json'
CURRENT_GT11_OBSERVATION = 'evals/observations/2026-08-28-f4dce57-gt-11-codex-local.json'
CURRENT_GT16_SOURCE = 'evals/evidence/2026-08-28-553f5a9-gt14-16-codex-local-source.json'
CURRENT_GT17_OBSERVATION = 'evals/observations/2026-08-28-fd4b99a-gt-17-codex-local.json'
SRC310 = 'evals/evidence/2026-08-27-v310-codex-local-regression-source.json'
OBS11 = 'evals/observations/2026-08-28-f4dce57-gt-11-codex-local.json'
OBS13 = 'evals/observations/2026-08-28-f182a0a-gt-13-codex-local.json'
OBS = {
    1: 'evals/observations/2026-08-24-v20-claude-gt01.json',
    2: 'evals/observations/2026-08-24-v20-claude-gt02.json',
    3: 'evals/observations/2026-08-24-v20-codex-gt03.json',
    7: 'evals/observations/2026-08-24-v20-claude-gt07.json',
    8: 'evals/observations/2026-08-24-v20-codex-gt08.json',
}
CRITERIA = ['R1', 'R2', 'R3', 'R4', 'Q1', 'Q2', 'Q3', 'Q4']
RETIRED = {'productId': 'retired-product',
           'authority': {'executableVerifier': 'python -B -m retired_module verify'}}

def _retired_history():
    return [json.dumps(RETIRED).encode(), b'# Retired Product\n']

def _read(root, locator):
    return json.loads((root / locator).read_text(encoding='utf-8'))

def _write(root, locator, value):
    path = root / locator
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, separators=(',', ':')) + '\n', encoding='utf-8')

def _git(root, *arguments, **options):
    return subprocess.check_output(
        ['git', '-C', str(root), *arguments], stderr=subprocess.DEVNULL, **options
    )

@contextmanager
def _fixture():
    with tempfile.TemporaryDirectory(prefix='ya-') as temporary:
        target = Path(temporary) / 'repository'
        shutil.copytree(ROOT, target, ignore=shutil.ignore_patterns(
            '.git', '.tmp', '.remember', '__pycache__', '*.pyc'))
        yield target

def _make_indexed_fixture():
    temporary = tempfile.TemporaryDirectory(prefix='ya-index-')
    target = Path(temporary.name) / 'repository'
    subprocess.run(['git', 'clone', '--quiet', '--no-hardlinks', str(ROOT),
                    str(target)], check=True)
    shutil.copytree(ROOT, target, dirs_exist_ok=True,
                    ignore=shutil.ignore_patterns(
                        '.git', '.tmp', '.remember', '__pycache__', '*.pyc'))
    for path in _git(ROOT, 'diff', 'HEAD', '--no-renames', '--name-only', '--diff-filter=D', text=True).splitlines():
        (target / path).unlink()
    _git(target, 'add', '-A')
    _git(target, '-c', 'user.name=Accord Fixture',
         '-c', 'user.email=fixture@example.invalid', 'commit', '--quiet',
         '--allow-empty', '-m', 'current fixture')
    return temporary, target

@contextmanager
def _indexed_fixture():
    temporary, target = _make_indexed_fixture()
    with temporary:
        yield target

def _rehash(root, locator):
    acceptance = _read(root, A)
    digest = hashlib.sha256((root / locator).read_bytes()).hexdigest()
    items = [
        item for criterion in acceptance['criteria']
        for item in criterion['evidence']
    ] + acceptance['representativeBehaviorPolicy']['historicalEvidence']
    for item in items:
        if item['locator'] == locator:
            item['sha256'] = digest
    _write(root, A, acceptance)

def _enable_current_sample_validation(root):
    acceptance = _read(root, A)
    criterion = next(
        item for item in acceptance['criteria'] if item['id'] == 'R3'
    )
    criterion['assessment'] = 'continuing'
    _write(root, A, acceptance)

def _bind_source(root, locator, bundle, observation):
    _write(root, SRC310, bundle)
    observation['transcriptOrEventEvidence'][0]['sha256'] = _digest(bundle[
        'records'][observation['taskId']])
    _write(root, locator, observation)
    _rehash(root, locator)

def _observe(root, locator, observation=None, label='fixture observation'):
    golden, observed = _read(root, G), observation or _read(root, locator)
    task = next(item for item in golden['tasks'] if item['id'] == observed['taskId'])
    policy = _read(root, A)['representativeBehaviorPolicy']
    historical = policy['historicalTaskContracts'].get(observed['taskId'])
    if (
        historical is not None
        and observed['evaluationContractSha256']
        == policy['historicalEvidenceContractSha256']
    ):
        task = historical['task']
    return _observation_errors(
        root, label, observed, task, golden['metrics']['humanBurden'], locator,
        observed['projectionIdentity']['adapterId'], observed['evaluationContractSha256'],
        lambda current_root, current_locator, _: _read(current_root, current_locator)
    )

def _public_source_errors(
    root, locator, bundle, observation, source_locator=SOURCE,
):
    source = observation['transcriptOrEventEvidence'][0]
    record = bundle['records'][source['recordId']]
    _write(root, source_locator, bundle)
    source['sha256'] = _digest(record)
    task = next(item for item in _read(root, G)['tasks'] if item['id'] == observation['taskId'])
    postcapture = _postcapture_bundle(record['payload'], task, _time(record['capturedAt']))
    if postcapture is not None and 'postSessionBindingsSha256' in source:
        source['postSessionBindingsSha256'] = _digest(postcapture)
    _write(root, locator, observation)
    _rehash(root, locator)
    return _errors(root)

def _source_error_fragment(root, locator):
    items = _read(root, A)['representativeBehaviorPolicy']['historicalEvidence']
    index = next(i for i, item in enumerate(items) if item['locator'] == locator)
    return f'historicalEvidence[{index}] sourceEvidence[0] is invalid'

def _balanced_add(terms):
    terms = list(terms)
    while len(terms) > 1:
        terms = [f'({left} + {right})'
                 for left, right in zip(terms[::2], terms[1::2])
                 ] + terms[len(terms) // 2 * 2:]
    return terms[0]

def _refresh_gt19_episode(episode):
    episode['closureRequestSha256'] = _digest(episode['closureRequest'])
    episode['coreDecision'] = reconcile_closure(episode['closureRequest'])
    episode['coreDecisionSha256'] = _digest(episode['coreDecision'])
    for fact in episode['sourceFacts']:
        fact['valueSha256'] = episode['coreDecisionSha256']

def _gt19_state_bindings(request, composition, generation, order):
    source_kind = (
        'official-host-state' if order == 2
        else 'bounded-direct-observation'
    )
    unavailable = (
        [] if source_kind == 'official-host-state'
        else ['official-host-state', 'accord-state']
    )
    source_order = 0 if order == 1 else order

    def binding(field, target_kind, subject, fact_id, value):
        return {
            'field': field,
            'targetKind': target_kind,
            'subjectRef': subject,
            'factId': fact_id,
            'value': value,
            'writer': 'fixture:host-state-normalizer',
            'readers': ['accord'],
            'sourceKind': source_kind,
            'sourceRef': f'fixture:host-state:{source_order}:{field}',
            'unavailableSources': unavailable,
            'generation': generation,
        }

    bindings = [
        binding(
            f'environment.{fact_id}', 'environment-fact', composition,
            fact_id, value,
        )
        for fact_id, value in request['environment']['facts'].items()
    ]
    for route in request['routes']:
        bindings.extend(
            binding(
                f'route.{route["id"]}.{fact_id}', 'route-fact',
                route['id'], fact_id, value,
            )
            for fact_id, value in route['facts'].items()
        )
        if len(route['forms']) > 1:
            bindings.extend(
                binding(
                    f'coherence.{route["id"]}.{fact_id}',
                    'coherence-fact', route['id'], fact_id, value,
                )
                for fact_id, value in route['coherence'].items()
            )
    return bindings

def _gt19_v2_payload(historical_event, revision):
    event = json.loads(json.dumps(historical_event))
    baseline, replacement = 'current-plugin', 'native-no-add'
    event['behaviorArms'].pop('readOnlyBlocked', None)
    event['behaviorArms']['AccordBacked']['finalAnswerTranscriptionErrors'] = []
    observations = (
        ('gt19-observation-1', 'gt19-composition-1', 7,
         '2026-08-29T00:00:00Z', '2026-08-29T00:01:00Z', []),
        ('gt19-observation-1', 'gt19-composition-1', 7,
         '2026-08-29T00:00:00Z', '2026-08-29T00:02:00Z',
         ['user-intervention']),
        ('gt19-observation-2', 'gt19-composition-2', 8,
         '2026-08-29T00:03:00Z', '2026-08-29T00:04:00Z', []),
        ('gt19-observation-3', 'gt19-composition-3', 9,
         '2026-08-29T00:05:00Z', '2026-08-29T00:06:00Z', []),
    )
    h_states = (
        'absent', 'injection-observed-effect-unknown',
        'admitted-current', 'evidence-expired',
    )
    a_states = (
        ('allocated', None),
        ('preserved-last-valid', None),
        ('retired-with-recheck', 'allocated'),
        ('restored', 'unavailable'),
    )
    dispositions = (
        'retain-Accord-baseline',
        'retain-last-valid-on-invalidated-receipt',
        'retire-exact-redundant-allocation',
        'restore-after-native-expiry',
    )
    freshness = (
        'current', 'invalidated-event-only',
        'current-resensed', 'current-recomputed',
    )
    for order, episode in enumerate(event['episodes']):
        request = episode['closureRequest']
        request['schema'] = 'yiyuan-accord-closure/v2'
        identity, composition, generation, captured, decision, invalidations = (
            observations[order]
        )
        request['environment']['compositionKey'] = composition
        request['environment']['observation'] = {
            'id': identity,
            'compositionKey': composition,
            'generation': generation,
            'capturedAt': captured,
            'decisionAt': decision,
            'validUntil': '2026-08-29T00:20:00Z',
            'stateBindings': [],
            'invalidatedBy': invalidations,
        }
        for route in request['routes']:
            if route['id'] == baseline:
                route['responsibilityModes'] = {
                    responsibility: (
                        'accord-agent-composed'
                        if responsibility == 'sense-environment'
                        else 'accord-contained'
                    )
                    for responsibility in route['supplies']
                }
            elif route['id'] == replacement:
                route['responsibilityModes'] = {
                    responsibility: 'agent-native'
                    for responsibility in route['supplies']
                }
            else:
                route['responsibilityModes'] = {
                    responsibility: 'accord-agent-composed'
                    for responsibility in route['supplies']
                }
        request['environment']['observation']['stateBindings'] = (
            json.loads(json.dumps(event['episodes'][0]['closureRequest'][
                'environment']['observation']['stateBindings']))
            if order == 1 else _gt19_state_bindings(
                request, composition, generation, order
            )
        )
        request['environment']['lastSafeAllocation'] = (
            {
                'routeId': baseline,
                'responsibilityModes': {
                    responsibility: next(
                        route for route in request['routes']
                        if route['id'] == baseline
                    )['responsibilityModes'][responsibility]
                    for responsibility in request['outcome'][
                        'responsibilities'
                    ]
                },
                'observationId': identity,
                'observationGeneration': generation,
                'evidence': {
                    'sourceRef': 'fixture:prior-safe-decision',
                    'observerRef': 'fixture:independent-oracle',
                    'subjectRef': baseline,
                    'boundaryRef': 'fixture:gt19-sequence',
                },
            } if order == 1 else None
        )
        if order == 1:
            injection = json.loads(json.dumps(request['events'][0]))
            injection['factId'] = 'context-injection'
            injection['state'] = 'observed'
            injection['independent'] = 'unknown'
            request['events'] = [injection]
        episode['disposition'] = dispositions[order]
        episode['sparseViews']['H'] = {
            f'{replacement}/sense-environment': h_states[order],
        }
        episode['sparseViews']['A'] = {
            f'{baseline}/sense-environment': a_states[order][0],
            f'{baseline}/bind-authority': 'preserved-outside-scope',
        }
        if a_states[order][1] is not None:
            episode['sparseViews']['A'][
                f'{replacement}/sense-environment'
            ] = a_states[order][1]
        episode['sparseViews']['S'] = {
            binding['field']: {
                key: binding[key] for key in (
                    'targetKind', 'subjectRef', 'factId', 'value', 'writer',
                    'readers', 'sourceKind', 'sourceRef',
                    'unavailableSources', 'generation',
                )
            } | {'freshness': freshness[order]}
            for binding in request['environment']['observation'][
                'stateBindings'
            ]
        }
        _refresh_gt19_episode(episode)

    allocations = (
        {'sense-environment': baseline, 'bind-authority': baseline},
        {'sense-environment': baseline, 'bind-authority': baseline},
        {'sense-environment': replacement, 'bind-authority': baseline},
        {'sense-environment': baseline, 'bind-authority': baseline},
    )
    states = []
    for order, episode in enumerate(event['episodes']):
        receipt = episode['closureRequest']['environment']['observation']
        states.append({
            'episodeOrder': order,
            'effectiveAllocations': allocations[order],
            'retiredAllocations': (
                [f'{baseline}/sense-environment'] if order == 2 else []
            ),
            'observationId': receipt['id'],
            'observationGeneration': receipt['generation'],
            'evidenceFreshness': freshness[order],
        })
    for order, edge in enumerate(event['carrierEdges']):
        edge['sourceState'] = states[order]
        edge['targetState'] = states[order + 1]
        edge['sourceStateSha256'] = _digest(edge['sourceState'])
        edge['targetStateSha256'] = _digest(edge['targetState'])
    event['stateCarrier']['finalEffectiveAllocations'] = allocations[3]
    event['stateCarrier']['lastObservationId'] = observations[3][0]
    event['stateCarrierSha256'] = _digest(event['stateCarrier'])
    event['revision'] = revision
    event['sequenceSha256'] = _sequence_digest(event)
    return {'evaluatedRevision': revision, 'materialEvents': [event]}

def _retired_raw_errors(body, locator='sample.txt', encoding='utf-8'):
    return _retired_byte_errors(body.encode(encoding), locator)

def _retired_byte_errors(body, locator='sample.txt'):
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        (root / locator).write_bytes(body)
        return _history_errors(root, [locator])

def _history_errors(root, locators, research=None):
    with patch('yiyuan_accord.identity._bounded_git_bytes',
               side_effect=_retired_history()):
        return active_tree_errors(root, locators, '0' * 40, research or set())

def _active_file_errors(locator, body='safe\n', research=None):
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        path = root / locator
        path.parent.mkdir(parents=True)
        path.write_text(body, encoding='utf-8')
        return _history_errors(root, [locator], research)

@contextmanager
def _deny_path(method, target):
    original = getattr(Path, method)
    def denied(path, *args, **kwargs):
        if path == target:
            raise AssertionError(f'unbounded Path.{method}')
        return original(path, *args, **kwargs)
    with patch.object(Path, method, denied):
        yield

def _lacks(errors, *fragments):
    return not any(fragment in error for error in errors for fragment in fragments)

def _errors(root):
    return verify_product(root)['errors']

class ProductControlTests(unittest.TestCase):

    def assert_has(self, errors, *fragments):
        for fragment in fragments:
            self.assertTrue(any(fragment in error for error in errors), fragment)

    def rejected(self, locator, message, mutate):
        with _fixture() as root:
            value = _read(root, locator)
            mutate(value)
            _write(root, locator, value)
            self.assert_has(_errors(root), message)

    def test_current_contract_is_valid_and_explicitly_incomplete(self):
        temporary, root = _make_indexed_fixture()
        self.addCleanup(temporary.cleanup)
        report = verify_product(root)
        self.assertTrue(report['valid'], report['errors'])
        self.assertEqual(report['criteria']['ids'], CRITERIA)
        if report['programStatus'] == 'active':
            program = _read(root, P)
            stages = program['increment']['workItems'][0]['closeoutSequence']
            self.assertIn('self-audit-remediate-and-reaccept-whole-system-balance',
                          {stage['id'] for stage in stages})
            self.assertEqual(
                all(stage['state'] == 'completed' for stage in stages),
                program['increment']['state'] == 'completed',
            )
            self.assertFalse(report['repositoryCandidateReady'])
        else:
            self.assertEqual(report['programStatus'], 'ready')
            self.assertEqual(report['criteria']['verified'], 8)
            self.assertEqual(report['repositoryCandidateReady'], report['checkoutClean'])
        self.assertTrue(all(host['staticReady'] for host in report['hostChecks'].values()))
        program, acceptance = _read(root, P), _read(root, A)
        constitution = _read(root, C)
        guidance = _read(root, 'product/reshaping-guidance.json')
        self.assertEqual(guidance['status'], 'accepted-revisable-guidance')
        self.assertEqual(
            guidance['wholeSystemBalanceReview']['status'],
            'completed-refreshed-independent-review-active',
        )
        for locator, stale in (
            ('README.md', 'GT-19 host-drift lane is designed but'),
            ('README.zh-CN.md', 'GT-19 宿主漂移任务已经设计但尚未执行'),
            ('docs/architecture.md', 'It is designed but unperformed'),
            ('docs/releases/v3.1.0.md', 'host-drift behavior but is unperformed'),
            ('docs/operations/CONTINUATION.md', 'behavior, but remains unperformed'),
        ):
            self.assertNotIn(stale, (root / locator).read_text(encoding='utf-8'))
        self.assertEqual(
            guidance['dynamicIndex']['graphProjection']['implementation'],
            'derived-in-memory-or-ignored-cache-first',
        )
        self.assertIn('model-inherent',
                      guidance['capabilityDiscovery']['provenanceKinds'])
        self.assertIn('Cartesian product',
                      guidance['dynamicIndex']['graphProjection']['normalizationRule'])
        model = guidance['selfBootstrappingCore']['semanticModel']
        graph = guidance['dynamicIndex']['graphProjection']
        self.assertEqual(model['id'], 'complete-bounded-self-bootstrapping/v1')
        self.assertEqual(model['factModel']['values'],
                         ['observed', 'not-observed', 'unknown'])
        self.assertEqual(
            model['routeDecision']['comparison']['mode'],
            'pareto-then-context-then-equivalent-fit-reuse-tiebreak',
        )
        self.assertEqual(model['formAllocation']['cardinality'],
                         'many-to-many-context-and-freshness-bound')
        self.assertTrue(
            {item['id'] for item in model['entities']}
            <= set(graph['nodeKinds'])
        )
        self.assertTrue(
            {item['id'] for item in model['relationKinds']}
            <= set(graph['edgeKinds'])
        )
        invariants = {item['id'] for item in model['invariants']}
        self.assertIn('authority-is-not-derived', invariants)
        self.assertTrue(all(set(item['guards']) <= invariants
                            for item in model['stressScenarios']))
        self.assertTrue(all(
            item['expectedDisposition'] in model['closureModel']['routeDispositions']
            for item in model['stressScenarios']
        ))
        self.assertGreaterEqual(len(model['stressScenarios']), 8)
        self.assertGreaterEqual(len(model['degradationPaths']), 10)
        environment = guidance['selfBootstrappingCore'][
            'environmentAdmissionContract'
        ]
        self.assertEqual(environment['id'], 'composed-environment-admission/v1')
        self.assertEqual(
            environment['admissionUnit'],
            'one-bounded-claim-under-one-provenance-bound-composition-and-freshness-window',
        )
        self.assertEqual(
            environment['snapshot']['factModelRef'],
            '#/selfBootstrappingCore/semanticModel/factModel',
        )
        self.assertEqual(
            {item['id'] for item in environment['armKinds']},
            {
                'official-clean', 'isolated-minimal', 'current-enabled',
                'isolated-no-Accord', 'candidate-enabled-isolated',
            },
        )
        self.assertEqual(
            [item['order'] for item in environment['isolationLadder']],
            list(range(5)),
        )
        dispositions = set(environment['admission']['dispositions'])
        self.assertTrue(all(
            item['expectedDisposition'] in dispositions
            for item in environment['stressScenarios']
        ))
        self.assertIn(
            'an-Accord-enabled-arm-cannot-attest-the-no-Accord-or-native-baseline',
            environment['comparisonContract']['independenceRules'],
        )
        self.assertIn(
            'credential-content',
            environment['snapshot']['privacyBoundary']['forbid'],
        )
        self.assertGreaterEqual(len(environment['stressScenarios']), 10)
        self.assertGreaterEqual(len(environment['cleanupAndInvalidation'][
            'invalidateOn']), 8)
        prototype = guidance['selfBootstrappingCore'][
            'productFormPrototypeDecision'
        ]
        self.assertEqual(
            prototype['id'], 'product-form-neutral-vertical-slice/v1'
        )
        self.assertEqual(
            set(prototype['routeCandidates']),
            {
                'no-added-mechanism', 'current-plugin-projection',
                'replaceable-composition',
                'bounded-authored-persistent-controller',
            },
        )
        scenario_results = {
            item['id']: item for item in prototype['scenarioResults']
        }
        self.assertEqual(
            scenario_results['native-whole-loop-observed']['selected'],
            'no-added-mechanism',
        )
        self.assertEqual(
            scenario_results[
                'effect-succeeds-but-cleanup-leaves-residue'
            ]['disposition'],
            'completion-rejected',
        )
        self.assertIn(
            'runtime-service-database-or-background-process',
            prototype['referenceCoreAdmission']['prohibited'],
        )
        self.assertFalse(prototype['isolation']['liveHostRead'])
        reference = guidance['selfBootstrappingCore'][
            'referenceCoreImplementation'
        ]
        self.assertEqual(
            reference['interface'],
            'reconcile_closure(request)-to-json-serializable-decision',
        )
        self.assertIn(
            'route-source-kinds-and-product-forms',
            reference['openEndedInputs'],
        )
        self.assertIn(
            'host-and-capability-discovery', reference['replaceableAdapters']
        )
        golden = _read(root, G)
        suite = golden['suiteDesign']
        self.assertEqual(
            suite['id'],
            'representative-and-longitudinal-self-bootstrapping-evaluation/v1',
        )
        self.assertIn('source-complete', suite['status'])
        self.assertEqual(suite['attemptedTaskIds'], [
            'GT-14', 'GT-15', 'GT-16', 'GT-17', 'GT-18', 'GT-19',
        ])
        self.assertEqual(suite['unperformedTaskIds'], ['GT-20', 'GT-21'])
        self.assertEqual(
            {item['id'] for item in suite['caseTypes']},
            {'representative-case', 'longitudinal-sequence'},
        )
        dimensions = suite['fullAcceptanceVector']['dimensions']
        self.assertEqual(len(dimensions), 10)
        self.assertTrue(all(
            isinstance(item['hardGate'], bool) and item['requires']
            for item in dimensions
        ))
        self.assertEqual(
            set(suite['comparisonEligibility']['armKinds']),
            {item['id'] for item in environment['armKinds']},
        )
        self.assertEqual(
            {item['taskId'] for item in suite['coverageMatrix']},
            {f'GT-{number}' for number in range(14, 22)},
        )
        new_tasks = {
            item['id']: item for item in golden['tasks']
            if item['id'] in {f'GT-{number}' for number in range(14, 22)}
        }
        self.assertTrue(all(item['evaluationDesign'] for item in new_tasks.values()))
        self.assertEqual(
            new_tasks['GT-18']['evaluationDesign']['minimumEpisodes'], 4
        )
        self.assertEqual(
            new_tasks['GT-18']['evaluationDesign']['episodeRoles'],
            [item['id'] for item in suite['longitudinalSequence']['episodeRoles']],
        )
        self.assertEqual(
            new_tasks['GT-19']['evaluationDesign']['minimumEpisodes'], 4
        )
        self.assertIn(
            'equate-one-responsibility-replacement-with-whole-product-retirement',
            new_tasks['GT-19']['prohibited'],
        )
        self.assertIn(
            'replace-truncate-or-silently-append-AGENTS-CLAUDE-config-toml-or-settings-files',
            new_tasks['GT-20']['prohibited'],
        )
        self.assertIn(
            'preserve-concurrent-user-edits-and-stop-on-ownership-or-merge-conflict',
            new_tasks['GT-20']['required'],
        )
        self.assertIn(
            'use-fresh-thread-start-not-fork-for-sequential-load-relief',
            new_tasks['GT-21']['required'],
        )
        self.assertIn(
            'consume-supported-structured-official-facts-directly-and-normalize-only-needed-fields',
            new_tasks['GT-21']['required'],
        )
        self.assertIn(
            'persist-a-second-authoritative-host-capability-database-or-load-unrelated-official-surfaces',
            new_tasks['GT-21']['prohibited'],
        )
        self.assertIn(
            'equate-conversation-fork-Git-worktree-Git-branch-or-repository-fork',
            new_tasks['GT-21']['prohibited'],
        )
        tasks = {item['id']: item for item in golden['tasks']}
        for needle, values in (
            ('keep-code-topology-independent-from-conversation-topology',
             tasks['GT-07']['required']),
            ('change-branch-worktree-checkout-or-repository-to-solve-conversation-load',
             tasks['GT-07']['prohibited']),
            ('build-a-proposition-ledger-and-distinguish-contradiction-category-error-tension-and-evidence-gap',
             tasks['GT-17']['required']),
            ('binary capability incidence overlap',
             ' '.join(guidance['selfBootstrappingCore']['falsifiers'])),
        ):
            self.assertIn(needle, values)
        topology = guidance['topology']
        self.assertEqual(set(topology), {
            'code', 'conversation', 'execution', 'independenceRule', 'rule',
            'hostVocabularyRule', 'continuityRiskRule', 'codexCloud',
        })
        self.assertNotIn('cloud-environment', topology['code'])
        self.assertIn('cloud-environment', topology['execution'])
        self.assertIn('localized labels', topology['hostVocabularyRule'].lower())
        self.assertIn('object, operation and inheritance semantics',
                      topology['hostVocabularyRule'])
        views = guidance['dynamicIndex']['sparseMatrixViews']
        self.assertEqual(
            views['authority'],
            'derived-query-views-only-never-a-second-source-of-truth',
        )
        self.assertIn('functional family', views['semanticEquivalenceRule'])
        self.assertIn('not a closed taxonomy', topology['continuityRiskRule'])
        self.assertIn(
            'preview2-is-a-current-release-candidate',
            {item['id'] for item in guidance['retiredAsActivePremises']},
        )
        historical_notes = (
            root / 'docs/releases/v2.0.1-preview.2.md'
        ).read_text(encoding='utf-8')
        self.assertIn('Unreleased historical checkpoint', historical_notes)
        self.assertNotIn('claude plugin marketplace add', historical_notes)
        self.assertNotIn('The intended release is', historical_notes)
        self.assertNotIn(
            'universal-agent-runtime', constitution['productBoundary']['excludes']
        )
        self.assertIn(
            'dynamic-index-and-route-derivation',
            constitution['productBoundary']['includes'],
        )
        self.assertEqual(
            constitution['resourceStewardship']['role'],
            'host-neutral-dynamic-scheduling-and-release-contract',
        )
        self.assertIn(
            'L8',
            {item['id'] for item in constitution['learnedFailureStandards']},
        )
        self.assertEqual(
            acceptance['representativeBehaviorPolicy']['requiredTaskIdsForRelease'],
            ['GT-07','GT-11','GT-12','GT-13',*[f'GT-{n}' for n in range(14,22)]],
        )
        release_notes = (root / acceptance['publicRelease']['releaseNotes']).read_text(
            encoding='utf-8')
        internal_claims = (
            acceptance['claimCeiling']['finiteReleaseClaims']
            + acceptance['claimCeiling']['notImplied']
            + acceptance['claimCeiling']['retainedBehaviorExclusions']
        )
        self.assertTrue(all(value not in release_notes for value in internal_claims))
        self.assertTrue(all(
            value in release_notes
            for field in (
                'publicFiniteReleaseClaims', 'publicNotImplied',
                'publicRetainedBehaviorExclusions',
            )
            for value in acceptance['claimCeiling'][field].values()
        ))
        self.assertEqual(
            guidance['resourceStewardship']['decision'],
            'required-as-a-host-neutral-dynamic-contract',
        )
        target = program['complexityBudget']['targets']
        self.assertGreaterEqual(
            target['maxTrackedFiles'] - report['complexity']['trackedFiles'], 3
        )
        limit = target['maxProductCodeAndTestBytes']
        percent = program['complexityBudget']['minimumProductCodeAndTestHeadroomPercent']
        self.assertGreaterEqual(limit - report['complexity']['productCodeAndTestBytes'],
                                (limit * percent + 99) // 100)
        self.assertNotRegex((root / 'CONTEXT.md').read_text(encoding='utf-8'),
                            r'#/[^`\n]+/[0-9]+(?:/|`)')
        self.assertNotIn('maxControlBytes', program['complexityBudget']['targets'])
        if report['programStatus'] == 'ready':
            gate = program['releaseProcedure']['orderedGates'][1]['condition']
            self.assertEqual(program['complexityBudget']['minimumTestCount'], 19)
            for marker in (
                'without accessing credential or session logs',
                'context-isolated, outcome-bound, identity-neutral',
                'does not claim public-tag installation before the immutable tag exists',
            ):
                self.assertIn(marker, gate)
                self.assertIn(marker, acceptance['candidateVerification']['rule'])
            final_gate = program['releaseProcedure']['orderedGates'][-1]['condition']
            for marker in (
                'context-isolated clean-state evaluator replay',
                'against the public immutable tag',
            ):
                self.assertIn(marker, final_gate)
                self.assertIn(marker, acceptance['publicRelease']['rule'])
        else:
            prompt = program['goalModePrompt']
            expected_goal_states = (
                {'retired'} if program['increment']['state'] == 'completed'
                else {'prepared-host-goal-paused', 'active-in-host'}
            )
            self.assertIn(prompt['state'], expected_goal_states)
            mapping = program['increment']['fourSurfaceMapping']
            self.assertEqual(
                mapping['outcomeId'],
                program['increment']['representativeOutcome']['id'],
            )
            projection = json.loads(prompt['objective'])
            self.assertEqual(projection['schema'], 'yiyuan-accord-goal/v2')
            self.assertEqual(projection['workspace'][-1],
                             'no-branch-worktree-or-repository-fork')
            self.assertEqual(
                projection['route']['alignment'],
                program['processLossControl']['alignmentRule'],
            )
            ordered = projection['route']['orderedSteps']
            self.assertLessEqual(
                len(prompt['objective']), 3600,
                'canonical host goal must keep headroom below the Codex limit',
            )
            self.assertEqual(
                ordered,
                [{field: step[field] for field in (
                     'id', 'state', 'dependsOn', 'acceptanceIds'
                )} for step in mapping['process']['orderedSteps']
                 if step['state'] in {'active', 'blocked'}],
            )

    def test_reference_core_is_policy_driven_and_fail_closed(self):
        responsibilities = [
            'sense-environment', 'bind-authority', 'preserve-correction',
            'execute-outcome', 'observe-consequence',
            'release-task-residue',
        ]
        compliance = {
            'within-human-authority': 'observed',
            'compliant': 'observed',
            'independent-consequence-verifier': 'observed',
            'available': 'observed',
        }
        coherence = {
            'responsibility-boundaries': 'observed',
            'interfaces-and-version': 'observed',
            'authority-and-side-effects': 'observed',
            'state-owner-and-freshness': 'observed',
            'evidence-and-independent-poststate': 'observed',
            'failure-degradation-and-recovery': 'observed',
            'update-replacement-and-rollback': 'observed',
            'cleanup-retirement-and-residue': 'observed',
        }
        dimensions = [
            'human-burden', 'interference', 'persistence', 'recovery',
            'maintenance', 'retirement',
        ]
        experiment_dimensions = [
            'outcome', 'authority', 'evidence', 'privacy', 'burden',
            'interference', 'recovery', 'resources', 'continuity',
            'lifecycle',
        ]
        experiment_facts = [
            'exact-baseline', 'fixed-budget', 'one-bounded-mutable-surface',
            'immutable-evaluator', 'full-acceptance-vector',
            'preauthorized-tolerances', 'available-rollback',
            'independent-effect-and-cleanup-poststate',
        ]

        def evidence(subject, observer='fixture-oracle'):
            return {
                'sourceRef': f'fixture-source:{subject}',
                'observerRef': observer,
                'subjectRef': subject,
                'boundaryRef': 'task-owned-process:synthetic-p4',
            }

        def state_binding(field, target_kind, subject, fact_id, value):
            return {
                'field': field,
                'targetKind': target_kind,
                'subjectRef': subject,
                'factId': fact_id,
                'value': value,
                'writer': 'fixture:bounded-observer',
                'readers': ['accord'],
                'sourceKind': 'bounded-direct-observation',
                'sourceRef': f'fixture:state:{field}',
                'unavailableSources': [
                    'official-host-state', 'accord-state',
                ],
                'generation': 1,
            }

        def fixture(*, healthy_native=False, residue=False):
            native_supplies = [
                item for item in responsibilities
                if healthy_native or item != 'preserve-correction'
            ]
            routes = [
                {
                    'id': 'native-no-add', 'sourceKind': 'no-added',
                    'forms': [], 'supplies': native_supplies,
                    'responsibilityModes': {
                        item: 'agent-native' for item in native_supplies
                    },
                    'facts': dict(compliance), 'coherence': {},
                    'lifecycle': {item: 0 for item in dimensions},
                },
                {
                    'id': 'current-plugin', 'sourceKind': 'maintained',
                    'forms': ['plugin'],
                    'supplies': ['sense-environment', 'bind-authority'],
                    'responsibilityModes': {
                        'sense-environment': 'accord-contained',
                        'bind-authority': 'accord-agent-composed',
                    },
                    'facts': {
                        **compliance,
                        'independent-consequence-verifier': 'unknown',
                    },
                    'coherence': {},
                    'lifecycle': {item: 1 for item in dimensions},
                },
                {
                    'id': 'minimal-composition', 'sourceKind': 'composition',
                    'forms': [
                        'native-executor', 'task-scoped-handoff',
                        'independent-effect-probe',
                    ],
                    'supplies': list(responsibilities),
                    'responsibilityModes': {
                        'sense-environment': 'accord-contained',
                        'bind-authority': 'accord-agent-composed',
                        'preserve-correction': 'accord-agent-composed',
                        'execute-outcome': 'agent-native',
                        'observe-consequence': 'accord-agent-composed',
                        'release-task-residue': 'accord-agent-composed',
                    },
                    'facts': dict(compliance), 'coherence': dict(coherence),
                    'lifecycle': {item: 1 for item in dimensions},
                },
                {
                    'id': 'persistent-controller', 'sourceKind': 'authored',
                    'forms': ['persistent-controller'],
                    'supplies': list(responsibilities),
                    'responsibilityModes': {
                        item: 'accord-contained' for item in responsibilities
                    },
                    'facts': dict(compliance), 'coherence': {},
                    'lifecycle': {
                        'human-burden': 2, 'interference': 3,
                        'persistence': 4, 'recovery': 3,
                        'maintenance': 4, 'retirement': 4,
                    },
                },
            ]
            state_bindings = [state_binding(
                'environment.provenance-bound', 'environment-fact',
                'synthetic:p4:v1', 'provenance-bound', 'observed',
            )]
            for route in routes:
                state_bindings.extend(
                    state_binding(
                        f'route.{route["id"]}.{fact_id}', 'route-fact',
                        route['id'], fact_id, value,
                    )
                    for fact_id, value in route['facts'].items()
                )
                if len(route['forms']) > 1:
                    state_bindings.extend(
                        state_binding(
                            f'coherence.{route["id"]}.{fact_id}',
                            'coherence-fact', route['id'], fact_id, value,
                        )
                        for fact_id, value in route['coherence'].items()
                    )
            selected = 'native-no-add' if healthy_native else 'minimal-composition'
            events = [
                {
                    'kind': 'fact-observed', 'routeId': selected,
                    'factId': 'execution', 'state': 'observed',
                    'independent': 'observed',
                    'evidence': evidence(selected),
                },
                {
                    'kind': 'fact-observed', 'routeId': selected,
                    'factId': 'consequence', 'state': 'observed',
                    'independent': 'observed',
                    'evidence': evidence(selected),
                },
            ]
            if not healthy_native:
                events.append({
                    'kind': 'experiment-evaluated',
                    'baselineRouteId': selected,
                    'candidateRouteId': 'persistent-controller',
                    'preconditions': {
                        item: 'observed' for item in experiment_facts
                    },
                    'comparison': {
                        item: (
                            'better' if item == 'outcome'
                            else 'worse' if item == 'lifecycle'
                            else 'equal'
                        ) for item in experiment_dimensions
                    },
                    'evidence': evidence('persistent-controller'),
                })
                events.append({
                    'kind': 'experiment-poststate',
                    'baselineRouteId': selected,
                    'candidateRouteId': 'persistent-controller',
                    'disposition': 'rollback-complete',
                    'state': 'observed',
                    'independent': 'observed',
                    'evidence': evidence('persistent-controller'),
                })
            events.append({
                'kind': 'resource-poststate', 'routeId': selected,
                'releasedResources': (
                    [] if healthy_native or residue else ['task-scoped-handoff']
                ),
                'residualTaskResources': (
                    ['task-scoped-handoff'] if residue else []
                ),
                'independent': 'observed',
                'evidence': evidence(selected),
            })
            return {
                'schema': 'yiyuan-accord-closure/v2',
                'outcome': {
                    'id': 'preserve-corrected-brief-across-one-interruption',
                    'responsibilities': list(responsibilities),
                },
                'environment': {
                    'compositionKey': 'synthetic:p4:v1',
                    'facts': {'provenance-bound': 'observed'},
                    'unknowns': ['field-value', 'cross-host-equivalence'],
                    'lastSafeAllocation': None,
                    'observation': {
                        'id': 'synthetic:p4:observation:1',
                        'compositionKey': 'synthetic:p4:v1',
                        'generation': 1,
                        'capturedAt': '2026-08-29T00:00:00Z',
                        'decisionAt': '2026-08-29T00:00:01Z',
                        'validUntil': '2026-08-29T00:05:00Z',
                        'stateBindings': state_bindings,
                        'invalidatedBy': [],
                    },
                },
                'policy': {
                    'id': 'p4-task-policy/v1',
                    'requiredEnvironmentFacts': ['provenance-bound'],
                    'requiredRouteFacts': ['available'],
                    'requiredCoherenceFacts': list(coherence),
                    'comparisonDimensions': list(dimensions),
                    'sourcePreference': [
                        'no-added', 'native', 'maintained', 'composition',
                        'authored',
                    ],
                    'contextPreference': [],
                    'requiredCompletionFacts': ['execution'],
                    'requiredExperimentFacts': list(experiment_facts),
                    'experimentDimensions': list(experiment_dimensions),
                },
                'routes': routes,
                'events': events,
            }

        decision = reconcile_closure(fixture())
        self.assertTrue(decision['valid'], decision['errors'])
        self.assertEqual(decision['selectedRouteId'], 'minimal-composition')
        self.assertEqual(decision['disposition'], 'admit')
        self.assertTrue(decision['environmentObservation']['current'])
        self.assertEqual(
            next(item for item in decision['assessments']
                 if item['routeId'] == 'minimal-composition')[
                     'responsibilityModes'],
            {
                'sense-environment': 'accord-contained',
                'bind-authority': 'accord-agent-composed',
                'preserve-correction': 'accord-agent-composed',
                'execute-outcome': 'agent-native',
                'observe-consequence': 'accord-agent-composed',
                'release-task-residue': 'accord-agent-composed',
            },
        )
        self.assertTrue(decision['lifecycle']['completionAllowed'])
        self.assertEqual(
            decision['lifecycle']['experimentResults'][0]['decision'],
            'discard-and-rollback',
        )
        self.assertTrue(
            decision['lifecycle']['experimentResults'][0]['poststate'][
                'accepted']
        )
        self.assertFalse(next(
            item for item in decision['assessments']
            if item['routeId'] == 'current-plugin'
        )['admitted'])

        native = reconcile_closure(fixture(healthy_native=True))
        self.assertEqual(native['selectedRouteId'], 'native-no-add')
        self.assertEqual(native['disposition'], 'no-op')
        self.assertTrue(native['lifecycle']['completionAllowed'])

        retirement_facts = [
            'within-human-authority',
            'current-successor-capability-observed',
            'same-responsibility-overlap-derived',
            'retired-route-prestate',
            'task-defined-observation-window-complete',
            'available-rollback', 'fallback-preserved',
        ]
        dynamic_retirement = fixture(healthy_native=True)
        dynamic_retirement['policy'].update({
            'requiredRetirementFacts': ['fallback-preserved'],
            'requiredRetirementAllocations': [{
                'routeId': 'current-plugin',
                'responsibilities': ['sense-environment'],
            }],
        })
        dynamic_retirement['events'].append({
            'kind': 'responsibility-allocation-retired',
            'routeId': 'current-plugin',
            'replacementRouteId': 'native-no-add',
            'responsibilities': ['sense-environment'],
            'replacementEvidence': evidence('native-no-add'),
            'preconditions': {
                item: 'observed' for item in retirement_facts
            },
            'recheckTriggers': [
                'environment-composition-change',
                'replacement-effect-drift',
                'evidence-expiry',
            ],
            'state': 'observed',
            'independent': 'observed',
            'evidence': evidence('current-plugin'),
        })
        retirement = reconcile_closure(dynamic_retirement)
        retirement_result = retirement['lifecycle']['retirementResults'][0]
        self.assertTrue(retirement_result['accepted'])
        self.assertEqual(
            retirement_result['disposition'], 'retired-with-recheck'
        )
        self.assertEqual(
            retirement_result['replacementEvidenceBinding']['subjectRef'],
            'native-no-add',
        )
        self.assertEqual(retirement['lifecycle']['retiredAllocations'], [{
            'routeId': 'current-plugin',
            'replacementRouteId': 'native-no-add',
            'responsibilities': ['sense-environment'],
            'recheckTriggers': [
                'environment-composition-change',
                'replacement-effect-drift',
                'evidence-expiry',
            ],
        }])
        self.assertTrue(retirement['lifecycle']['completionAllowed'])

        stale_replacement = json.loads(json.dumps(dynamic_retirement))
        stale_replacement['events'][-1]['preconditions'][
            'task-defined-observation-window-complete'
        ] = 'unknown'
        stale_retirement = reconcile_closure(stale_replacement)
        self.assertFalse(
            stale_retirement['lifecycle']['retirementResults'][0]['accepted']
        )
        self.assertFalse(stale_retirement['lifecycle']['completionAllowed'])
        self.assertIn(
            'completion:retirement:current-plugin:sense-environment',
            {item['code'] for item in stale_retirement['lifecycle'][
                'completionFailures']},
        )

        discovery_unproved = json.loads(json.dumps(dynamic_retirement))
        discovery_unproved['events'][-1]['preconditions'][
            'current-successor-capability-observed'
        ] = 'unknown'
        discovery_decision = reconcile_closure(discovery_unproved)
        self.assertFalse(
            discovery_decision['lifecycle']['retirementResults'][0]['accepted']
        )
        self.assertFalse(discovery_decision['lifecycle']['completionAllowed'])

        missing_retirement = json.loads(json.dumps(dynamic_retirement))
        missing_retirement['events'].pop()
        missing_retirement_decision = reconcile_closure(missing_retirement)
        self.assertFalse(
            missing_retirement_decision['lifecycle']['completionAllowed']
        )
        self.assertIn(
            'completion:retirement:current-plugin:sense-environment',
            {item['code'] for item in missing_retirement_decision['lifecycle'][
                'completionFailures']},
        )

        premature_retirement = json.loads(json.dumps(dynamic_retirement))
        retirement_event = premature_retirement['events'].pop()
        premature_retirement['events'].insert(0, retirement_event)
        premature_retirement_decision = reconcile_closure(premature_retirement)
        self.assertFalse(
            premature_retirement_decision['lifecycle'][
                'retirementResults'][0]['accepted']
        )
        self.assertFalse(
            premature_retirement_decision['lifecycle']['completionAllowed']
        )

        no_experiment_policy = fixture(healthy_native=True)
        no_experiment_policy['policy']['requiredExperimentFacts'] = []
        no_experiment_policy['policy']['experimentDimensions'] = []
        no_experiment_policy['policy']['requiredCompletionFacts'] = []
        no_experiment = reconcile_closure(no_experiment_policy)
        self.assertTrue(no_experiment['valid'], no_experiment['errors'])
        self.assertTrue(no_experiment['lifecycle']['completionAllowed'])

        no_environment_gate = fixture(healthy_native=True)
        no_environment_gate['policy']['requiredEnvironmentFacts'] = []
        no_environment_gate['environment']['facts'] = {}
        no_environment_decision = reconcile_closure(no_environment_gate)
        self.assertEqual(no_environment_decision['disposition'], 'hold-unknown')
        self.assertIsNone(no_environment_decision['selectedRouteId'])

        no_availability_gate = fixture(healthy_native=True)
        no_availability_gate['policy']['requiredRouteFacts'] = []
        for route in no_availability_gate['routes']:
            route['facts'].pop('available', None)
        no_availability_decision = reconcile_closure(no_availability_gate)
        self.assertEqual(no_availability_decision['disposition'], 'hold-unknown')
        self.assertTrue(all(
            not item['admitted']
            for item in no_availability_decision['assessments']
        ))

        for missing_coherence_fact in coherence:
            with self.subTest(missing_coherence_fact=missing_coherence_fact):
                missing_coherence = fixture()
                missing_coherence['policy']['requiredCoherenceFacts'] = []
                missing_coherence['routes'][2]['coherence'].pop(
                    missing_coherence_fact
                )
                decision = reconcile_closure(missing_coherence)
                self.assertFalse(decision['valid'])

        residual = reconcile_closure(fixture(residue=True))
        self.assertFalse(residual['lifecycle']['completionAllowed'])
        self.assertIn(
            'completion:task-residue',
            {item['code'] for item in residual['lifecycle'][
                'completionFailures']},
        )

        injection_only = fixture()
        injection_only['events'] = [
            event for event in injection_only['events']
            if event.get('factId') not in {'execution', 'consequence'}
        ]
        injection_only['events'].insert(0, {
            'kind': 'fact-observed', 'routeId': 'minimal-composition',
            'factId': 'context-injection', 'state': 'observed',
            'independent': 'observed',
            'evidence': evidence('minimal-composition'),
        })
        injection_decision = reconcile_closure(injection_only)
        self.assertTrue(injection_decision['valid'])
        self.assertFalse(injection_decision['lifecycle']['completionAllowed'])
        self.assertTrue({
            'completion:execution', 'completion:consequence',
        }.issubset({
            item['code'] for item in injection_decision['lifecycle'][
                'completionFailures']
        }))

        for corrected_fact in (
            'within-human-authority', 'compliant', 'available',
        ):
            corrected = fixture()
            corrected['events'].append({
                'kind': 'fact-observed',
                'routeId': 'minimal-composition',
                'factId': corrected_fact,
                'state': 'not-observed',
                'independent': 'observed',
                'evidence': evidence('minimal-composition'),
            })
            corrected_decision = reconcile_closure(corrected)
            with self.subTest(corrected_fact=corrected_fact):
                self.assertFalse(
                    corrected_decision['lifecycle']['completionAllowed']
                )
                self.assertIn(
                    f'route-poststate:{corrected_fact}',
                    {item['code'] for item in corrected_decision['lifecycle'][
                        'completionFailures']},
                )

        rollback_unverified = fixture()
        rollback_unverified['events'] = [
            event for event in rollback_unverified['events']
            if event['kind'] != 'experiment-poststate'
        ]
        rollback_decision = reconcile_closure(rollback_unverified)
        self.assertFalse(rollback_decision['lifecycle']['completionAllowed'])
        self.assertIn(
            'completion:experiment-poststate:persistent-controller',
            {item['code'] for item in rollback_decision['lifecycle'][
                'completionFailures']},
        )

        self_attested = fixture()
        self_attested['events'][1]['evidence']['observerRef'] = (
            'minimal-composition'
        )
        self.assertFalse(reconcile_closure(self_attested)['valid'])

        wrong_subject = fixture()
        wrong_subject['events'][1]['evidence']['subjectRef'] = 'native-no-add'
        self.assertFalse(reconcile_closure(wrong_subject)['valid'])

        cross_boundary = fixture()
        cross_boundary['events'][3]['evidence']['boundaryRef'] = (
            'task-owned-process:different-boundary'
        )
        cross_boundary_decision = reconcile_closure(cross_boundary)
        self.assertFalse(
            cross_boundary_decision['lifecycle']['completionAllowed']
        )
        self.assertFalse(
            cross_boundary_decision['lifecycle']['experimentResults'][0][
                'poststate']['accepted']
        )

        unknown = fixture()
        unknown['environment']['facts']['provenance-bound'] = 'unknown'
        unknown_decision = reconcile_closure(unknown)
        self.assertEqual(unknown_decision['disposition'], 'hold-unknown')
        self.assertIsNone(unknown_decision['selectedRouteId'])

        observation_failures = {
            'signal-only': lambda value: value.update(stateBindings=[]),
            'composition-mismatch': lambda value: value.update(
                compositionKey='synthetic:different'
            ),
            'future': lambda value: value.update(
                capturedAt='2026-08-29T00:00:02Z'
            ),
            'expired': lambda value: value.update(
                validUntil='2026-08-29T00:00:00Z'
            ),
            'invalidated': lambda value: value.update(
                invalidatedBy=['user-intervention']
            ),
        }
        for name, mutate in observation_failures.items():
            request = fixture(healthy_native=True)
            mutate(request['environment']['observation'])
            held = reconcile_closure(request)
            with self.subTest(environment_observation=name):
                self.assertTrue(held['valid'], held['errors'])
                self.assertEqual(held['disposition'], 'hold-unknown')
                self.assertIsNone(held['selectedRouteId'])
                self.assertFalse(held['environmentObservation']['current'])

        refreshed = fixture(healthy_native=True)
        refreshed['environment']['compositionKey'] = 'synthetic:p4:v2'
        refreshed['environment']['observation'].update({
            'id': 'synthetic:p4:observation:2',
            'compositionKey': 'synthetic:p4:v2',
            'generation': 2,
            'capturedAt': '2026-08-29T00:00:02Z',
            'decisionAt': '2026-08-29T00:00:03Z',
            'validUntil': '2026-08-29T00:05:02Z',
            'invalidatedBy': [],
        })
        for binding in refreshed['environment']['observation'][
            'stateBindings'
        ]:
            binding['generation'] = 2
            if binding['targetKind'] == 'environment-fact':
                binding['subjectRef'] = 'synthetic:p4:v2'
        refreshed_decision = reconcile_closure(refreshed)
        self.assertEqual(refreshed_decision['selectedRouteId'], 'native-no-add')
        self.assertEqual(
            refreshed_decision['environmentObservation']['generation'], 2
        )

        dynamic_policy = fixture()
        dynamic_policy['policy']['requiredRouteFacts'].append(
            'fit-for-current-context'
        )
        policy_decision = reconcile_closure(dynamic_policy)
        self.assertEqual(policy_decision['disposition'], 'hold-unknown')
        self.assertTrue(all(
            not item['admitted'] for item in policy_decision['assessments']
        ))

        malformed = fixture()
        malformed['schema'] = 'invented'
        invalid = reconcile_closure(malformed)
        self.assertFalse(invalid['valid'])
        self.assertEqual(invalid['disposition'], 'reject')

        conflicting_writer = fixture()
        duplicate = dict(conflicting_writer['environment']['observation'][
            'stateBindings'][0], writer='another-writer')
        conflicting_writer['environment']['observation'][
            'stateBindings'].append(duplicate)
        conflict = reconcile_closure(conflicting_writer)
        self.assertTrue(conflict['valid'], conflict['errors'])
        self.assertEqual(conflict['disposition'], 'hold-unknown')
        self.assertFalse(conflict['environmentObservation']['current'])

        unbound_value = fixture()
        unbound_value['environment']['observation']['stateBindings'][0][
            'value'
        ] = 'not-observed'
        unbound = reconcile_closure(unbound_value)
        self.assertTrue(unbound['valid'], unbound['errors'])
        self.assertEqual(unbound['disposition'], 'hold-unknown')
        self.assertIsNone(unbound['selectedRouteId'])

        unbound_target = fixture()
        unbound_target['environment']['observation']['stateBindings'][0][
            'factId'
        ] = 'unrelated-fact'
        unbound = reconcile_closure(unbound_target)
        self.assertTrue(unbound['valid'], unbound['errors'])
        self.assertEqual(unbound['disposition'], 'hold-unknown')
        self.assertIsNone(unbound['selectedRouteId'])

        signal_only = fixture(healthy_native=True)
        signal_only['environment']['observation']['invalidatedBy'] = [
            'user-intervention'
        ]
        signal_only['environment']['lastSafeAllocation'] = {
            'routeId': 'native-no-add',
            'responsibilityModes': {
                item: 'agent-native' for item in responsibilities
            },
            'observationId': 'synthetic:p4:observation:1',
            'observationGeneration': 1,
            'evidence': evidence('native-no-add'),
        }
        preserved = reconcile_closure(signal_only)
        self.assertIsNone(preserved['selectedRouteId'])
        self.assertEqual(
            preserved['preservedAllocation']['routeId'], 'native-no-add'
        )
        self.assertTrue(
            preserved['environmentObservation']['preservedLastSafe']
        )

        malformed_cases = []
        sensitive_state = fixture()
        sensitive_state['environment']['observation']['stateBindings'][0][
            'field'] = 'Credential.token'
        malformed_cases.append(sensitive_state)
        stale_binding = fixture()
        stale_binding['environment']['observation']['generation'] = 2
        malformed_cases.append(stale_binding)
        precedence_bypass = fixture()
        precedence_bypass['environment']['observation']['stateBindings'][0][
            'unavailableSources'
        ] = []
        malformed_cases.append(precedence_bypass)
        missing_mode = fixture()
        missing_mode['routes'][2]['responsibilityModes'].pop(
            'preserve-correction'
        )
        malformed_cases.append(missing_mode)
        invented_mode = fixture()
        invented_mode['routes'][2]['responsibilityModes'][
            'preserve-correction'
        ] = 'plugin-does-everything'
        malformed_cases.append(invented_mode)
        bad_forms = fixture()
        bad_forms['routes'][0]['forms'] = None
        malformed_cases.append(bad_forms)
        bad_dimensions = fixture()
        bad_dimensions['policy']['comparisonDimensions'] = None
        malformed_cases.append(bad_dimensions)
        bad_route_binding = fixture()
        bad_route_binding['events'][0]['routeId'] = []
        malformed_cases.append(bad_route_binding)
        same_experiment_route = fixture()
        same_experiment_route['events'][2]['candidateRouteId'] = (
            'minimal-composition'
        )
        malformed_cases.append(same_experiment_route)
        contradictory_poststate = fixture()
        contradictory_poststate['events'][-1][
            'residualTaskResources'
        ] = ['task-scoped-handoff']
        contradictory_poststate['events'][-1][
            'releasedResources'
        ] = ['task-scoped-handoff']
        malformed_cases.append(contradictory_poststate)
        cleanup_self_claim = fixture()
        cleanup_self_claim['events'][-1] = {
            'kind': 'fact-observed',
            'routeId': 'minimal-composition',
            'factId': 'cleanup-poststate',
            'state': 'observed',
            'independent': 'observed',
            'evidence': evidence('minimal-composition'),
        }
        malformed_cases.append(cleanup_self_claim)
        missing_retirement_recheck = json.loads(json.dumps(dynamic_retirement))
        missing_retirement_recheck['events'][-1]['recheckTriggers'] = []
        malformed_cases.append(missing_retirement_recheck)
        retirement_scope_overreach = json.loads(json.dumps(dynamic_retirement))
        retirement_scope_overreach['events'][-1]['responsibilities'].append(
            'execute-outcome'
        )
        malformed_cases.append(retirement_scope_overreach)
        wrong_replacement_evidence = json.loads(json.dumps(dynamic_retirement))
        wrong_replacement_evidence['events'][-1][
            'replacementEvidence'
        ] = evidence('current-plugin')
        malformed_cases.append(wrong_replacement_evidence)
        unknown_required_retirement = fixture(healthy_native=True)
        unknown_required_retirement['policy'][
            'requiredRetirementAllocations'
        ] = [{
            'routeId': 'invented-route',
            'responsibilities': ['sense-environment'],
        }]
        malformed_cases.append(unknown_required_retirement)
        whole_route_shortcut = json.loads(json.dumps(dynamic_retirement))
        whole_route_shortcut['policy'].pop('requiredRetirementAllocations')
        whole_route_shortcut['policy'][
            'requiredRetirementRouteIds'
        ] = ['current-plugin']
        malformed_cases.append(whole_route_shortcut)
        for case in malformed_cases:
            with self.subTest(case=case):
                invalid = reconcile_closure(case)
                self.assertFalse(invalid['valid'])
                self.assertEqual(invalid['disposition'], 'reject')

    def test_authority_and_static_suite_mutations_fail_closed(self):
        cases = (
            (C, 'constitution top-level shape', lambda v: v.update(extra=True)),
            (P, 'program top-level shape', lambda v: v.update(releaseComplete=True)),
            (A, 'acceptance top-level shape', lambda v: v.update(authorize=True)),
            (C, 'compatibilityAliases must be empty',
             lambda v: v['identity'].update(compatibilityAliases=['x'])),
            (C, 'responsibilityAllocationModes is invalid', lambda v: v[
                'domainModel'].update(responsibilityAllocationModes=[
                    'plugin-does-everything'
                ])),
            (C, 'stateCoordinationModes is invalid', lambda v: v[
                'domainModel'].update(stateCoordinationModes=['implicit-shared'])),
            (C, 'humanAuthority shape', lambda v: v.pop('humanAuthority')),
            (C, 'resourceStewardship shape', lambda v: v[
                'resourceStewardship'].pop('diagnosticRule')),
            (P, 'minimumProductCodeAndTestHeadroomPercent', lambda v: v[
                'complexityBudget'].update(minimumProductCodeAndTestHeadroomPercent=4)),
            (P, 'product control test markers are not executable unittest methods',
             lambda v: v['complexityBudget'].update(minimumTestCount=18)),
            (P, 'digestBoundBinaryAssets must be an object', lambda v: v[
                'complexityBudget'].pop('digestBoundBinaryAssets')),
            (G, 'static-suite-as-behavior',
             lambda v: v['evaluationProtocol'].update(staticSuiteIsNotBehaviorEvidence=False)),
            (G, 'humanBurden metrics', lambda v: v['metrics'].update(help=['self-claim'])),
            (G, 'bound reviewable GT-13 workspace', lambda v: next(
                task for task in v['tasks'] if task['id'] == 'GT-13'
            ).update(workspaceContract=None)),
            (G, 'bound reviewable GT-13 workspace', lambda v: next(
                task for task in v['tasks'] if task['id'] == 'GT-13'
            ).update(prompt=(
                'Do not use a reviewable, explicitly bound workspace; '
                'use an ephemeral clone.'
            ))),
            (G, 'golden tasks do not cover contract ids', lambda v: [
                task['mapsTo'].remove('L8')
                for task in v['tasks'] if 'L8' in task['mapsTo']
            ]),
            (A, 'representative post-session binding contracts', lambda v: v[
                'representativeBehaviorPolicy'].update(postSessionBindingContracts=[])),
            (A, 'acceptance.claimCeiling is invalid', lambda v: v[
                'claimCeiling'].pop('publicFiniteReleaseClaims')),
            (A, 'finite-release evidence lanes', lambda v: (
                v['evidenceLanes']['continuingAfterRelease'].append(
                    v['evidenceLanes']['requiredForFiniteRelease'].pop())))
        )
        for case in cases:
            with self.subTest(case=case[:2]):
                self.rejected(*case)

    def test_projection_package_and_admission_are_fail_closed(self):
        with _fixture() as root:
            program = _read(root, P)
            projection = program['hostProjections'][0]
            projection['mcpServers'] = {'x': {'command': 'x'}}
            projection['interfaceDefaultPrompt'] = ['x' * 129]
            _write(root, P, program)
            manifest_path = projection['manifest']
            manifest = _read(root, manifest_path)
            (manifest['interface']['defaultPrompt'], manifest['mcpServers']) = (projection['interfaceDefaultPrompt'], {})
            _write(root, manifest_path, manifest)
            skill = root / projection['skill']
            skill.write_text(skill.read_text(encoding='utf-8').replace(
                'name: deliver-demand-driven-outcome', 'name: publish-now', 1
            ).replace('## Resource stewardship', '## Capacity management', 1), encoding='utf-8')
            market = _read(root, projection['marketplace'])
            market['plugins'][0]['policy']['installation'] = 'INSTALLED_BY_DEFAULT'
            _write(root, projection['marketplace'], market)
            self.assert_has(host_check(root, 'codex')['errors'], 'program projection shape',
                            'package digest', 'unsupported fields', 'Skill frontmatter identity',
                            'AVAILABLE/ON_INSTALL', 'interface contract',
                            'Skill omits marker Resource stewardship')
        with _fixture() as root:
            # Preserve a lexical alias so the mock follows the verifier's
            # canonical root on hosts whose temporary path resolves elsewhere.
            root = root / '..' / root.name
            projection = _read(root, P)['hostProjections'][0]
            target = root.resolve(strict=True) / projection['skill']
            original_is_symlink = Path.is_symlink
            original_read_bytes = Path.read_bytes

            def declared_symlink(path):
                return path == target or original_is_symlink(path)

            def never_follow_declared(path):
                if path == target:
                    raise AssertionError('declared symlink target was read')
                return original_read_bytes(path)

            with patch.object(Path, 'is_symlink', declared_symlink), \
                    patch.object(Path, 'read_bytes', never_follow_declared):
                digest, errors = validate_projection_package(
                    root, projection['id'], projection['manifest'],
                    projection['contract'], projection['skill'],
                    projection['metadataFiles'], [], projection['mechanismFiles'],
                )
            self.assertIsNone(digest)
            self.assert_has(errors, 'package declared file is unsafe')
        with _fixture() as root:
            projection = _read(root, P)['hostProjections'][0]
            target = root / projection['skill']
            with target.open('wb') as stream:
                stream.truncate(2_000_000)
            with _deny_path('read_text', target), _deny_path('read_bytes', target):
                errors = host_check(root, 'codex')['errors']
            self.assert_has(errors, 'Skill exceeds budget', 'package identity is unavailable')

        with _fixture() as root:
            projection = _read(root, P)['hostProjections'][0]
            manifest = _read(root, projection['manifest'])
            manifest['author']['name'] = 'collective'
            manifest['interface']['composerIcon'] = './assets/other.png'
            _write(root, projection['manifest'], manifest)
            self.assert_has(
                host_check(root, 'codex')['errors'],
                'manifest author is not canonical',
                'manifest interface contract is invalid',
                'package declared file is unsafe',
            )

        with _fixture() as root:
            projection = _read(root, P)['hostProjections'][0]
            icon = root / 'plugins/yiyuan-accord-codex/assets/yiyuan-nexus-mark.png'
            icon.write_bytes(icon.read_bytes() + b'tampered')
            self.assert_has(
                host_check(root, 'codex')['errors'],
                'package digest is not approved by program',
            )

        with _fixture() as root:
            projection = _read(root, P)['hostProjections'][1]
            manifest = _read(root, projection['manifest'])
            manifest['displayName'] = 'YIYUAN Accord for Claude Code'
            _write(root, projection['manifest'], manifest)
            marketplace = _read(root, projection['marketplace'])
            marketplace['plugins'][0]['source'] = './plugins/wrong'
            marketplace['plugins'][0]['version'] = '2.0.1-preview.1'
            _write(root, projection['marketplace'], marketplace)
            self.assert_has(
                host_check(root, 'claude-code')['errors'],
                'manifest displayName is invalid',
                'marketplace source is invalid',
                'marketplace presentation is invalid',
                'package digest is not approved by program',
            )

        with _fixture() as root:
            projection = _read(root, P)['hostProjections'][1]
            marketplace = _read(root, projection['marketplace'])
            marketplace['plugins'][0]['description'] = 'Drifted description'
            _write(root, projection['marketplace'], marketplace)
            self.assert_has(
                host_check(root, 'claude-code')['errors'],
                'marketplace presentation is invalid',
            )

        for adapter_id, projection_index in (('codex', 0), ('claude-code', 1)):
            with self.subTest(adapter=adapter_id), _fixture() as root:
                program = _read(root, P)
                projection = program['hostProjections'][projection_index]
                hook_path = projection['mechanismFiles'][0]
                hook = _read(root, hook_path)
                hook['hooks']['SessionStart'][0]['hooks'][0]['command'] = 'echo drifted'
                _write(root, hook_path, hook)
                self.assert_has(
                    host_check(root, adapter_id)['errors'],
                    'activation mechanism contract is invalid',
                    'package digest is not approved by program',
                )

        with _fixture() as root:
            program = _read(root, P)
            projection = program['hostProjections'][0]
            hook_path = root / projection['mechanismFiles'][0]
            raw = hook_path.read_text(encoding='utf-8')
            hook_path.write_text(
                raw.replace('"hooks": {', '"hooks": {},\n  "hooks": {', 1),
                encoding='utf-8',
            )
            self.assert_has(
                host_check(root, 'codex')['errors'],
                'activation mechanism is unreadable',
                'package digest is not approved by program',
            )

        for suffix in (' & extra', '; extra', ' $(extra)', ' `extra`', ' %PATH%'):
            with self.subTest(shell_suffix=suffix), _fixture() as root:
                program = _read(root, P)
                program['hostProjections'][0]['activationContext'] += suffix
                _write(root, P, program)
                self.assert_has(
                    host_check(root, 'codex')['errors'],
                    'activation context is invalid',
                )

        with _fixture() as root:
            observation = _read(root, OBS11)
            bundle = _read(root, SRC310)
            record = bundle['records']['GT-11']
            record['payload']['projectionExposure']['mechanismSha256'] = '0' * 64
            _bind_source(root, OBS11, bundle, observation)
            self.assert_has(_observe(root, OBS11)[0], 'sourceEvidence[0] is invalid')

        with _fixture() as root:
            observation = _read(root, OBS13)
            bundle = _read(root, SRC310)
            record = bundle['records']['GT-13']
            record['amendments'][0] = None
            _bind_source(root, OBS13, bundle, observation)
            self.assert_has(_observe(root, OBS13)[0], 'sourceEvidence[0] is invalid')

        with _fixture() as root:
            observation = _read(root, OBS13)
            bundle = _read(root, SRC310)
            record = bundle['records']['GT-13']
            duplicate = dict(record['amendments'][0])
            duplicate['priorGoldenTaskSha256'] = '1' * 64
            record['amendments'].append(duplicate)
            _bind_source(root, OBS13, bundle, observation)
            self.assert_has(_observe(root, OBS13)[0], 'sourceEvidence[0] is invalid')

    def test_projection_evidence_rejects_drift_and_relocation(self):
        current = host_check(ROOT, 'codex')['details']
        observation = {
            'adapterId': 'codex',
            'contract': current['contract'],
            'skill': current['skill'],
            'mechanismFiles': current['mechanismFiles'],
            'contractSha256': current['identity']['contractSha256'],
            'skillSha256': current['identity']['skillSha256'],
            'mechanismSha256': current['identity']['mechanismSha256'],
        }
        presentation_drift = dict(
            observation,
            manifestSha256='0' * 64,
            packageSha256='0' * 64,
        )
        self.assertEqual(
            projection_observation_errors(
                presentation_drift, current, 'presentation-only', 'codex'
            ),
            [],
        )
        changed_locator = json.loads(json.dumps(current))
        changed_locator['skill'] = 'plugins/changed/SKILL.md'
        self.assert_has(
            projection_observation_errors(
                observation, changed_locator, 'behavior-bearing', 'codex'
            ),
            'skill does not match current adapter',
        )
        behavior_drift = dict(observation, skillSha256='0' * 64)
        self.assert_has(
            projection_observation_errors(
                behavior_drift, current, 'behavior-drift', 'codex'
            ),
            'skillSha256 does not match',
        )

        with _fixture() as root:
            acceptance = _read(root, A)
            criterion = next(
                item for item in acceptance['criteria']
                if any(evidence.get('bindsProjection') == 'codex'
                       for evidence in item.get('evidence', []))
            )
            evidence = next(
                item for item in criterion['evidence']
                if item.get('bindsProjection') == 'codex'
            )
            for item in acceptance['criteria']:
                item['evidence'] = []
            criterion['assessment'] = 'continuing'
            criterion['evidence'] = [evidence]
            _write(root, A, acceptance)
            locator = criterion['evidence'][0]['locator']
            observation = _read(root, locator)
            observation['projectionIdentity'].update({
                'adapterId': 'codex',
                'contract': current['contract'],
                'skill': current['skill'],
                'mechanismFiles': current['mechanismFiles'],
                'contractSha256': current['identity']['contractSha256'],
                'skillSha256': current['identity']['skillSha256'],
                'mechanismSha256': current['identity']['mechanismSha256'],
            })
            _write(root, locator, observation)
            reports = {'codex': host_check(root, 'codex')['details']}
            self.assertEqual(
                projection_evidence_binding_errors(
                    root, acceptance, reports,
                    lambda current_root, current_locator, _: _read(
                        current_root, current_locator
                    ),
                ),
                [],
            )
            observation['projectionIdentity']['skillSha256'] = '0' * 64
            _write(root, locator, observation)
            self.assert_has(
                projection_evidence_binding_errors(
                    root, acceptance, reports,
                    lambda current_root, current_locator, _: _read(
                        current_root, current_locator
                    ),
                ),
                'skillSha256 does not match current adapter codex',
            )

    def test_representative_sample_binds_projection_source_and_task(self):
        acceptance, golden = _read(ROOT, A), _read(ROOT, G)
        baseline = representative_contract_sha256(acceptance, golden)
        changed = json.loads(json.dumps(acceptance))
        changed['criteria'][2]['passRule'] += ' Expanded after capture.'
        self.assertNotEqual(
            baseline, representative_contract_sha256(changed, golden)
        )
        changed = json.loads(json.dumps(acceptance))
        changed['evidenceLanes']['rule'] += (
            ' Later revisions affect only future results.'
        )
        self.assertNotEqual(
            baseline, representative_contract_sha256(changed, golden)
        )

        with _fixture() as root:
            locator = OBS[1]
            observation = _read(root, locator)
            source = _read(root, SOURCE)
            source['records']['GT-01']['payload'] = 'tampered'
            observation['goldenTaskSha256'] = '0' * 64
            errors = _public_source_errors(root, locator, source, observation)
            self.assert_has(
                errors,
                'Golden Task digest mismatch',
                'sourceEvidence[0] is invalid',
            )
            record = source['records']['GT-01']
            observation['goldenTaskSha256'] = record['goldenTaskSha256']
            self.assert_has(_public_source_errors(root, locator, source, observation),
                            'sourceEvidence[0] is invalid')

        with _fixture() as root:
            locator = OBS[3]
            observation = _read(root, locator)
            source = _read(root, SOURCE)
            record = source['records']['GT-03']
            record['payload']['projectionExposure'] = {
                'kind': 'exact-skill-content-read',
                'adapterId': 'codex',
                'skill': observation['projectionIdentity']['skill'],
                'skillSha256': '0' * 64,
            }
            self.assert_has(_public_source_errors(root, locator, source, observation),
                            'sourceEvidence[0] is invalid')

        with _fixture() as root:
            locator = OBS[8]
            observation = _read(root, locator)
            original = _read(root, SOURCE)
            official = original['records']['GT-08']['payload']['officialSources']
            invalid_sources = (
                [official[0], official[0]],
                [dict(official[0], kind='web-page'), official[1]],
                [dict(official[0], url='https://example.invalid/source'), official[1]],
                [dict(official[0], retrievedAt='2999-01-01T00:00:00Z'), official[1]],
            )
            for sources in invalid_sources:
                bundle = json.loads(json.dumps(original))
                record = bundle['records']['GT-08']
                record['payload']['officialSources'] = sources
                self.assert_has(_public_source_errors(root, locator, bundle, observation),
                                'sourceEvidence[0] is invalid')

    def test_evidence_authority_bindings_and_types_fail_closed(self):
        precise = _time('2026-08-26T03:54:29.3353264Z')
        self.assertIsNotNone(precise)
        self.assertEqual(precise.microsecond, 335326)
        self.assertIsNone(_time('not-a-time'))

        tasks = {item['id']: item for item in _read(ROOT, G)['tasks']}
        bundle = _read(ROOT, SOURCE)
        record = bundle['records']['GT-07']
        payload, task = record['payload'], tasks['GT-07']
        contract = (tasks['GT-02']['postSessionBindingContract']
                    + task['postSessionBindingContract'])
        payload['postSessionBindingContract'] = task['postSessionBindingContract'] = contract
        payload['materialEvents'].append(
            {'kind': 'independent-poststate', 'sourceBindings': [
                payload['cleanupEvidence']['observations'][-1]['sourceBindings'][0]
            ]}
        )
        self.assertIsNone(_postcapture_bundle(payload, task, _time(record['capturedAt'])))

        for task_id in ('GT-02',):
            with self.subTest(policy_anchor=task_id), _fixture() as root:
                golden = _read(root, G)
                task = next(item for item in golden['tasks'] if item['id'] == task_id)
                locator = OBS[int(task_id[-2:])]
                source_locator = SOURCE
                bundle = _read(root, source_locator)
                observation = _read(root, locator)
                record = bundle['records'][observation[
                    'transcriptOrEventEvidence'][0]['recordId']]
                payload = record['payload']
                task.pop('postSessionBindingContract')
                payload.pop('postSessionBindingContract')
                payload['materialEvents'] = [
                    event for event in payload['materialEvents']
                    if event['kind'] != 'independent-poststate'
                ]
                observation['transcriptOrEventEvidence'][0].pop(
                    'postSessionBindingsSha256'
                )
                digest = _digest(task)
                record['goldenTaskSha256'] = observation['goldenTaskSha256'] = digest
                _write(root, G, golden)
                self.assert_has(
                    _public_source_errors(
                        root, locator, bundle, observation, source_locator,
                    ),
                    'post-session binding contract does not match representative policy',
                )

        malformed = {'postSessionBindingContract': [{
            'kind': 'independent-poststate', 'location': {}, 'bindingCount': 1
        }]}
        self.assertIsNone(_postcapture_bundle(
            malformed, malformed, _time('2026-08-24T00:00:00Z')
        ))

        current = _read(ROOT, CURRENT_GT11_SOURCE)['records']['GT-11']
        current_task = tasks['GT-11']
        self.assertIsNotNone(_postcapture_bundle(
            current['payload'], current_task, _time(current['capturedAt'])
        ))
        command_payload = json.loads(json.dumps(current['payload']))
        command_payload['independentCommandResults'] = [{
            'kind': 'independent-command-result',
            'carrierSessionId': '01a03c8f-ba9e-7991-b375-c673345ed4ad',
            'taskLocator': 'GT-11/independent-observer',
            'phase': 'bounded-agent-result',
            'nonce': 'gt11-independent-observer-20260826-a',
            'report': 'The isolated Agent wrote a structured result and exited cleanly.',
        }]
        command_event = next(
            item for item in command_payload['materialEvents']
            if item['kind'] == 'independent-poststate'
        )
        command_event['sourceBindings'] = [{
            'kind': 'direct-independent-command-result',
            'carrierSessionId': '01a03c8f-ba9e-7991-b375-c673345ed4ad',
            'taskLocator': 'GT-11/independent-observer',
            'resultLocator': 'task-artifact:GT-11/independent-observer/agent-final.txt',
            'phaseNonces': ['gt11-independent-observer-20260826-a'],
            'resultSha256': hashlib.sha256(
                command_payload['independentCommandResults'][0][
                    'report'
                ].encode('utf-8')
            ).hexdigest(),
            'resultRecordSha256': _digest(
                command_payload['independentCommandResults']
            ),
            'completedAt': '2026-08-26T03:54:30Z',
            'claim': 'Bound to the isolated command result without reading session logs.',
        }]
        self.assertIsNotNone(_postcapture_bundle(
            command_payload, current_task, _time(current['capturedAt'])
        ))
        mutations = (
            ('binding', 'resultSha256', '0' * 64),
            ('binding', 'resultRecordSha256', '0' * 64),
            ('binding', 'carrierSessionId', 'wrong'),
            ('binding', 'taskLocator', 'GT-11/other-observer'),
            ('binding', 'resultLocator', 'task-artifact:other.txt'),
            ('binding', 'phaseNonces', ['other-nonce']),
            ('binding', 'completedAt', '2999-01-01T00:00:00Z'),
            ('result', 'report', 'drift'),
            ('payload', 'independentCommandResults', None),
        )
        for scope, key, value in mutations:
            payload = json.loads(json.dumps(command_payload))
            event = next(
                item for item in payload['materialEvents']
                if item['kind'] == 'independent-poststate'
            )
            binding = event['sourceBindings'][0]
            target = {'binding': binding, 'result': payload[
                'independentCommandResults'][0], 'payload': payload}[scope]
            if value is None:
                target.pop(key)
            else:
                target[key] = value
            with self.subTest(direct_independent_command_binding=(scope, key)):
                self.assertIsNone(_postcapture_bundle(
                    payload, current_task, _time(current['capturedAt'])
                ))
        swapped = json.loads(json.dumps(command_payload))
        first = swapped['independentCommandResults'][0]
        second = dict(
            first,
            carrierSessionId='01a03c90-409d-79f9-8232-7522da1eefac',
            taskLocator='GT-11/second-observer',
            nonce='gt11-second-observer-20260826-b',
            report='The second isolated Agent completed its own bounded report.',
        )
        swapped['independentCommandResults'].append(second)
        event = next(
            item for item in swapped['materialEvents']
            if item['kind'] == 'independent-poststate'
        )
        binding = event['sourceBindings'][0]
        binding['carrierSessionId'] = second['carrierSessionId']
        binding['taskLocator'] = second['taskLocator']
        binding['resultLocator'] = (
            'task-artifact:GT-11/second-observer/agent-final.txt'
        )
        binding['phaseNonces'] = [second['nonce']]
        binding['resultSha256'] = hashlib.sha256(
            second['report'].encode('utf-8')
        ).hexdigest()
        binding['resultRecordSha256'] = _digest([second])
        with self.subTest(swapped_direct_command_carrier=True):
            self.assertIsNone(_postcapture_bundle(
                swapped, current_task, _time(current['capturedAt'])
            ))
        source_bundle = _read(ROOT, CURRENT_GT11_SOURCE)
        gt12 = source_bundle['records']['GT-12']
        with self.subTest(cross_task_command_bundle=True):
            self.assertIsNone(_postcapture_bundle(
                gt12['payload'], current_task, _time(gt12['capturedAt'])
            ))
        traversed = json.loads(json.dumps(command_payload))
        traversed_result = traversed['independentCommandResults'][0]
        traversed_result['taskLocator'] = (
            'GT-11/../GT-12/independent-observer'
        )
        traversed_event = next(
            item for item in traversed['materialEvents']
            if item['kind'] == 'independent-poststate'
        )
        traversed_binding = traversed_event['sourceBindings'][0]
        traversed_binding['taskLocator'] = traversed_result['taskLocator']
        traversed_binding['resultLocator'] = (
            'task-artifact:GT-11/../GT-12/independent-observer/agent-final.txt'
        )
        traversed_binding['resultRecordSha256'] = _digest([traversed_result])
        with self.subTest(cross_task_path_traversal=True):
            self.assertIsNone(_postcapture_bundle(
                traversed, current_task, _time(current['capturedAt'])
            ))
        for field in ('phase', 'report'):
            payload = json.loads(json.dumps(command_payload))
            payload['independentCommandResults'][0][field] = ''
            event = next(
                item for item in payload['materialEvents']
                if item['kind'] == 'independent-poststate'
            )
            event['sourceBindings'][0]['resultRecordSha256'] = _digest(
                payload['independentCommandResults']
            )
            with self.subTest(empty_direct_command_field=field):
                self.assertIsNone(_postcapture_bundle(
                    payload, current_task, _time(current['capturedAt'])
                ))
        observation = _read(ROOT, CURRENT_GT11_OBSERVATION)
        payload = json.loads(json.dumps(current['payload']))
        payload.pop('recheckTriggers')
        self.assertFalse(_publishable_payload(
            payload, current_task, observation['cleanup'],
            _time(current['capturedAt']), observation['projectionIdentity'],
        ))
        self.assertFalse(_publishable_payload(
            current['payload'], current_task, 'malformed-cleanup',
            _time(current['capturedAt']), observation['projectionIdentity'],
        ))
        with _fixture() as root:
            malformed_observation = _read(root, CURRENT_GT11_OBSERVATION)
            malformed_observation['cleanup'] = 'malformed-cleanup'
            errors, _ = _observe(
                root, CURRENT_GT11_OBSERVATION, malformed_observation
            )
            self.assert_has(
                errors,
                'sourceEvidence[0] is invalid',
                'cleanup is invalid',
            )

        gt18 = tasks['GT-18']
        source = _read(ROOT, CURRENT_GT16_SOURCE)
        gt07 = tasks['GT-07']
        gt07_record = source['records']['GT-07-cb11759']
        gt07_payload = gt07_record['payload']
        narratives = _continuity_narrative_hashes(
            ROOT, CURRENT_GT16_SOURCE, 'GT-07-cb11759', gt07_payload, gt07,
        )
        self.assertIsNotNone(narratives)
        continuity = lambda payload: _continuity_handoff_bundle(
            payload, gt07, narratives
        )
        self.assertIsNotNone(continuity(gt07_payload))
        for path, value in (
            (('materialEvents', 0, 'capacity'), 'known-80-percent'),
            (('materialEvents', 0, 'universalThreshold'), 75),
            (('materialEvents', 1, 'classifications', 1, 'sequentialContextRelief'), True),
            (('materialEvents', 1, 'classifications', 2, 'historyInheritance'), 'copied'),
            (('materialEvents', 1, 'codeTopology', 'changed'), True),
            (('materialEvents', 1, 'executionPlacement', 'changed'), True),
            (('materialEvents', 1, 'sourceReleasedObserved'), True),
        ):
            payload = json.loads(json.dumps(gt07_payload))
            target = payload
            for part in path[:-1]:
                target = target[part]
            target[path[-1]] = value
            with self.subTest(gt07_semantic_path=path):
                self.assertIsNone(continuity(payload))
        malformed_handoff = json.loads(json.dumps(gt07_payload))
        poststate = next(
            item for item in malformed_handoff['materialEvents']
            if item['kind'] == 'independent-poststate'
        )
        poststate['sourceBindings'][0]['taskLocator'] = []
        self.assertIsNone(continuity(malformed_handoff))

        extra_handoff_state = json.loads(json.dumps(gt07_payload))
        extra_handoff_state['materialEvents'][1]['receivedFields'].append(
            'credential-content'
        )
        self.assertIsNone(continuity(extra_handoff_state))

        contradictory_report = json.loads(json.dumps(gt07_payload))
        result = next(
            item for item in contradictory_report['independentCommandResults']
            if item['taskLocator'].endswith('/destination-poststate')
        )
        result['report'] += '; inherited copied history and source released early'
        binding = next(
            item for item in next(
                event for event in contradictory_report['materialEvents']
                if event['kind'] == 'independent-poststate'
            )['sourceBindings']
            if item['taskLocator'].endswith('/destination-poststate')
        )
        binding['resultSha256'] = hashlib.sha256(
            result['report'].encode('utf-8')
        ).hexdigest()
        binding['resultRecordSha256'] = _digest([result])
        self.assertIsNone(continuity(contradictory_report))
        cross_bound_drift = json.loads(json.dumps(gt07_payload))
        result = next(item for item in cross_bound_drift[
            'independentCommandResults'
        ] if item['taskLocator'].endswith('/destination-poststate'))
        result['facts']['sourceReleasedObserved'] = True
        result['report'] = json.dumps(
            result['facts'], ensure_ascii=False, sort_keys=True,
            separators=(',', ':'),
        )
        self.assertIsNone(continuity(cross_bound_drift))
        provenance = json.loads(json.dumps(gt07_payload))
        result = next(item for item in provenance[
            'independentCommandResults'
        ] if item['taskLocator'].endswith('/destination-poststate'))
        result['facts']['sourceNarrativeSha256'] = '0' * 64
        result['report'] = json.dumps(
            result['facts'], ensure_ascii=False, sort_keys=True,
            separators=(',', ':'),
        )
        self.assertIsNone(continuity(provenance))

        event = next(
            item for item in source['records']['GT-18-2460adc'][
                'payload']['materialEvents']
            if item['kind'] == 'longitudinal-sequence'
        )
        gt18_payload = {
            'evaluatedRevision': source['records']['GT-18-2460adc'][
                'payload']['evaluatedRevision'],
            'materialEvents': [event],
        }
        self.assertIsNotNone(_longitudinal_bundle(gt18_payload, gt18))
        for path, value in (
            (('fullAcceptanceVector', 'states'), ['pass']),
            (('episodes', 1, 'acceptanceVector'), lambda items: items[:-1]),
            (('episodes', 2, 'evaluatorSha256'), 'b' * 64),
            (('episodes', 2, 'sourceFacts', 0, 'valueSha256'), 'b' * 64),
            (('carrierEdges', 0, 'sourceStateSummary'), ''),
            (('carrierEdges', 0, 'sourceState', 'activeRoute'), 'drift'),
            (('carrierEdges',), lambda items: items[:-1]),
        ):
            payload = json.loads(json.dumps(gt18_payload))
            event_target = payload['materialEvents'][0]
            target = event_target
            for part in path[:-1]:
                target = target[part]
            target[path[-1]] = value(target[path[-1]]) if callable(value) else value
            event_target['sequenceSha256'] = _sequence_digest(event_target)
            with self.subTest(longitudinal_path=path):
                self.assertIsNone(_longitudinal_bundle(payload, gt18))

        for path, value in (
            (('episodes', 1, 'disposition'), 'retain-proxy-regression'),
            (('episodes', 1, 'candidateAcceptanceVector'), []),
            (('episodes', 1, 'candidateAcceptanceVector'),
             lambda items: [dict(item, state='pass') for item in items]),
            (('episodes', 2, 'disposition'), 'retain-unbounded-change'),
            (('episodes', 3, 'invalidatedRoute'), 'minimal-composition'),
        ):
            payload = json.loads(json.dumps(gt18_payload))
            event_target = payload['materialEvents'][0]
            target = event_target
            for part in path[:-1]:
                target = target[part]
            target[path[-1]] = value(target[path[-1]]) if callable(value) else value
            event_target['sequenceSha256'] = _sequence_digest(event_target)
            with self.subTest(gt18_semantic_path=path, value=str(value)):
                self.assertIsNone(_longitudinal_bundle(payload, gt18))

        bounded_alternative = json.loads(json.dumps(gt18_payload))
        candidate = bounded_alternative['materialEvents'][0]['episodes'][1][
            'candidateAcceptanceVector'
        ]
        for item in candidate:
            item['state'] = (
                'fail' if item['id'] == 'authority-and-accountability' else 'pass'
            )
        bounded_alternative['materialEvents'][0]['sequenceSha256'] = (
            _sequence_digest(bounded_alternative['materialEvents'][0])
        )
        self.assertIsNotNone(_longitudinal_bundle(bounded_alternative, gt18))

        irrelevant_regression = json.loads(json.dumps(gt18_payload))
        candidate = irrelevant_regression['materialEvents'][0]['episodes'][1][
            'candidateAcceptanceVector'
        ]
        for item in candidate:
            item['state'] = 'fail' if item['id'] == 'human-burden' else 'pass'
        irrelevant_regression['materialEvents'][0]['sequenceSha256'] = (
            _sequence_digest(irrelevant_regression['materialEvents'][0])
        )
        self.assertIsNone(_longitudinal_bundle(irrelevant_regression, gt18))

        for carrier in ('malformed-carrier', [], None):
            malformed = json.loads(json.dumps(gt18_payload))
            malformed['materialEvents'][0]['stateCarrier'] = carrier
            malformed['materialEvents'][0]['sequenceSha256'] = _sequence_digest(
                malformed['materialEvents'][0]
            )
            with self.subTest(malformed_state_carrier=repr(carrier)):
                self.assertIsNone(_longitudinal_bundle(malformed, gt18))

        revision_mismatch = json.loads(json.dumps(gt18_payload))
        revision_mismatch['materialEvents'][0]['revision'] = '0' * 40
        revision_mismatch['materialEvents'][0]['sequenceSha256'] = _sequence_digest(
            revision_mismatch['materialEvents'][0]
        )
        self.assertIsNone(_longitudinal_bundle(revision_mismatch, gt18))
        unbound_sequence = json.loads(json.dumps(gt18_payload))
        unbound_sequence['materialEvents'][0]['sequenceSha256'] = '0' * 64
        self.assertIsNone(_longitudinal_bundle(unbound_sequence, gt18))
        unknown_longitudinal = json.loads(json.dumps(gt18))
        unknown_longitudinal['id'] = 'GT-UNKNOWN'
        unknown_longitudinal['kind'] = 'future-longitudinal-contract'
        self.assertIsNone(_longitudinal_bundle(gt18_payload, unknown_longitudinal))

        gt19 = tasks['GT-19']
        gt19_event = next(
            item for item in source['records']['GT-19-2460adc'][
                'payload']['materialEvents']
            if item['kind'] == 'longitudinal-sequence'
        )
        gt19_payload = {
            'evaluatedRevision': source['records']['GT-19-2460adc'][
                'payload']['evaluatedRevision'],
            'materialEvents': [gt19_event],
        }
        self.assertIsNone(_longitudinal_bundle(gt19_payload, gt19))
        gt19_v2 = _gt19_v2_payload(
            gt19_event, gt19_payload['evaluatedRevision']
        )
        self.assertIsNotNone(_longitudinal_bundle(gt19_v2, gt19))

        no_invalidation = json.loads(json.dumps(gt19_v2))
        episode = no_invalidation['materialEvents'][0]['episodes'][1]
        episode['closureRequest']['environment']['observation'][
            'invalidatedBy'
        ] = []
        _refresh_gt19_episode(episode)
        no_invalidation['materialEvents'][0]['sequenceSha256'] = (
            _sequence_digest(no_invalidation['materialEvents'][0])
        )
        self.assertIsNone(_longitudinal_bundle(no_invalidation, gt19))

        state_view_drift = json.loads(json.dumps(gt19_v2))
        event_target = state_view_drift['materialEvents'][0]
        event_target['episodes'][2]['sparseViews']['S'][
            'environment.provenance-bound'
        ]['writer'] = 'self-attested-writer'
        event_target['sequenceSha256'] = _sequence_digest(event_target)
        self.assertIsNone(_longitudinal_bundle(state_view_drift, gt19))

        unbound_route_fact = json.loads(json.dumps(gt19_v2))
        event_target = unbound_route_fact['materialEvents'][0]
        episode = event_target['episodes'][2]
        route = next(
            item for item in episode['closureRequest']['routes']
            if item['id'] == 'native-no-add'
        )
        route['facts']['available'] = 'not-observed'
        _refresh_gt19_episode(episode)
        event_target['sequenceSha256'] = _sequence_digest(event_target)
        self.assertIsNone(_longitudinal_bundle(unbound_route_fact, gt19))

        stale_field_generation = json.loads(json.dumps(gt19_v2))
        event_target = stale_field_generation['materialEvents'][0]
        episode = event_target['episodes'][2]
        episode['closureRequest']['environment']['observation'][
            'stateBindings'
        ][0]['generation'] -= 1
        _refresh_gt19_episode(episode)
        event_target['sequenceSha256'] = _sequence_digest(event_target)
        self.assertIsNone(_longitudinal_bundle(
            stale_field_generation, gt19
        ))

        priority_bypass = json.loads(json.dumps(gt19_v2))
        event_target = priority_bypass['materialEvents'][0]
        episode = event_target['episodes'][3]
        episode['closureRequest']['environment']['observation'][
            'stateBindings'
        ][0]['unavailableSources'] = []
        _refresh_gt19_episode(episode)
        event_target['sequenceSha256'] = _sequence_digest(event_target)
        self.assertIsNone(_longitudinal_bundle(priority_bypass, gt19))

        missing_last_safe = json.loads(json.dumps(gt19_v2))
        event_target = missing_last_safe['materialEvents'][0]
        episode = event_target['episodes'][1]
        episode['closureRequest']['environment']['lastSafeAllocation'] = None
        _refresh_gt19_episode(episode)
        event_target['sequenceSha256'] = _sequence_digest(event_target)
        self.assertIsNone(_longitudinal_bundle(missing_last_safe, gt19))

        injection_as_effect = json.loads(json.dumps(gt19_v2))
        episode = injection_as_effect['materialEvents'][0]['episodes'][1]
        consequence = json.loads(json.dumps(episode['closureRequest']['events'][0]))
        consequence['factId'] = 'consequence'
        consequence['independent'] = 'observed'
        episode['closureRequest']['events'].append(consequence)
        _refresh_gt19_episode(episode)
        injection_as_effect['materialEvents'][0]['sequenceSha256'] = (
            _sequence_digest(injection_as_effect['materialEvents'][0])
        )
        self.assertIsNone(_longitudinal_bundle(injection_as_effect, gt19))

        whole_route_mode = json.loads(json.dumps(gt19_v2))
        for episode in whole_route_mode['materialEvents'][0]['episodes']:
            baseline = next(
                route for route in episode['closureRequest']['routes']
                if route['id'] == 'current-plugin'
            )
            baseline['responsibilityModes']['sense-environment'] = 'agent-native'
            _refresh_gt19_episode(episode)
        whole_route_mode['materialEvents'][0]['sequenceSha256'] = (
            _sequence_digest(whole_route_mode['materialEvents'][0])
        )
        self.assertIsNone(_longitudinal_bundle(whole_route_mode, gt19))

        changed_on_invalidated_receipt = json.loads(json.dumps(gt19_v2))
        event_target = changed_on_invalidated_receipt['materialEvents'][0]
        invalid_allocation = {
            'sense-environment': 'native-no-add',
            'bind-authority': 'current-plugin',
        }
        event_target['carrierEdges'][0]['targetState'][
            'effectiveAllocations'
        ] = invalid_allocation
        event_target['carrierEdges'][1]['sourceState'][
            'effectiveAllocations'
        ] = invalid_allocation
        for edge in event_target['carrierEdges'][:2]:
            edge['sourceStateSha256'] = _digest(edge['sourceState'])
            edge['targetStateSha256'] = _digest(edge['targetState'])
        event_target['sequenceSha256'] = _sequence_digest(event_target)
        self.assertIsNone(_longitudinal_bundle(
            changed_on_invalidated_receipt, gt19
        ))

        acceptance = _read(ROOT, A)
        policy = acceptance['representativeBehaviorPolicy']
        current = representative_contract_sha256(acceptance, _read(ROOT, G))
        old = policy['evaluationContractHistory'][0]['sha256']
        sequence_contract = policy['evaluationContractHistory'][1]['sha256']
        qualification_contract = policy['evaluationContractHistory'][2]['sha256']
        self.assertIn(old, _evaluation_contracts(policy, 'GT-14', current))
        self.assertEqual(
            _evaluation_contracts(policy, 'GT-17', current),
            {current, sequence_contract, qualification_contract},
        )
        self.assertEqual(
            _evaluation_contracts(policy, 'GT-18', current),
            {current, sequence_contract},
        )
        malformed = json.loads(json.dumps(policy))
        malformed['evaluationContractHistory'][0]['preservedTaskIds'] = []
        self.assertIsNone(_evaluation_contracts(malformed, 'GT-14', current))

        candidate_bundle = _read(ROOT, CURRENT_GT16_SOURCE)
        candidate_record = candidate_bundle['records']['GT-17-fd4b99a']
        candidate_task = next(item for item in _read(ROOT, G)['tasks']
                              if item['id'] == 'GT-17')
        candidate_args = (
            ROOT, candidate_record, candidate_task, _digest(candidate_task),
            _time(candidate_record['capturedAt']), (acceptance, _read(ROOT, G), current),
        )
        self.assertFalse(_source_amendments(*candidate_args))
        unamended = json.loads(json.dumps(candidate_record))
        unamended.pop('amendments')
        self.assertFalse(_source_amendments(
            ROOT, unamended, *candidate_args[2:],
        ))
        injected = json.loads(json.dumps(candidate_record))
        injected['payload']['evaluatedRevision'] = '--output=unexpected'
        with patch('yiyuan_accord.evidence._bounded_git_bytes') as git_read:
            self.assertFalse(_source_amendments(
                ROOT, injected, *candidate_args[2:],
            ))
            git_read.assert_not_called()
        malformed_history = [
            b'{"tasks":[null]}', json.dumps(acceptance).encode(),
        ]
        with patch('yiyuan_accord.evidence._bounded_git_bytes',
                   side_effect=malformed_history):
            self.assertFalse(_source_amendments(*candidate_args))
        revision = candidate_record['payload']['evaluatedRevision']
        malformed_acceptance = [
            _git(ROOT, 'show', f'{revision}:evals/golden-tasks.json'),
            b'{"claimCeiling":null}',
        ]
        with patch('yiyuan_accord.evidence._bounded_git_bytes',
                   side_effect=malformed_acceptance):
            self.assertFalse(_source_amendments(*candidate_args))
        with patch('yiyuan_accord.evidence._bounded_git_bytes',
                   side_effect=subprocess.CalledProcessError(1, 'git')):
            self.assertFalse(_source_amendments(*candidate_args))
        changed_acceptance = json.loads(json.dumps(acceptance))
        changed_acceptance['representativeBehaviorPolicy'][
            'releaseDecisionRule'
        ] += ' Unreviewed semantic expansion.'
        changed_contract = (
            changed_acceptance, candidate_args[-1][1],
            representative_contract_sha256(changed_acceptance, candidate_args[-1][1]),
        )
        changed_record = json.loads(json.dumps(candidate_record))
        changed_record['amendments'][0][
            'correctedEvaluationContractSha256'
        ] = changed_contract[-1]
        changed_args = (
            ROOT, changed_record, *candidate_args[2:-1], changed_contract,
        )
        self.assertFalse(_source_amendments(*changed_args))

        source_cases = (
            (8, ('officialSources', 0, 'url'), 'https://github.com/openai/../x'),
            (8, ('officialSources', 0, 'url'), 'https://github.com/openai/%2e%2e/x'),
            (8, ('officialSources', 0, 'url'), 'https://github.com/\nopenai/x'),
            (8, ('officialSources',), lambda x: [dict(x[0], url='https://github.com/openai/x'),
                                                  dict(x[1], url='https://github.com/openai/%78')]),
            (8, ('messages', 0, 'role'), {}),
            (8, ('projectionExposure', 'kind'), {}),
            (2, ('materialEvents',), lambda xs: [dict(x, sourceBindings=[])
                                                  if x['kind'] == 'independent-poststate' else x for x in xs]),
            (2, ('materialEvents',), lambda xs: [x for x in xs
                                                  if x['kind'] != 'independent-poststate']),
            (2, ('materialEvents',), None),
            (7, ('cleanupEvidence', 'observations', -1, 'kind'), {}),
            (7, ('cleanupEvidence', 'observations', -1, 'sourceBindings'), lambda x: x[:-1]),
            (7, ('cleanupEvidence', 'observations', -1, 'sourceBindings'), lambda x: [x[0], x[0]]),
        )
        for task_id, path, value in source_cases:
            with self.subTest(source=task_id), _fixture() as root:
                locator, bundle = OBS[task_id], _read(root, SOURCE)
                observation = _read(root, locator)
                target = bundle['records'][observation['taskId']]['payload']
                for part in path[:-1]:
                    target = target[part]
                target[path[-1]] = value(target[path[-1]]) if callable(value) else value
                self.assert_has(_public_source_errors(root, locator, bundle, observation),
                                _source_error_fragment(root, locator))

        for section, error in (
            ('behaviorDecisions', 'behaviorDecisions are incomplete'),
            ('criterionDecisions', 'criterionDecisions contradict behavior'),
            ('decision', 'has invalid decision'),
        ):
            with self.subTest(observation=section), _fixture() as root:
                locator, observation = OBS[8], _read(root, OBS[8])
                values = observation[section]
                if section == 'decision':
                    values['state'] = {}
                else:
                    values = values.get('required', values)
                    values[next(iter(values))] = {}
                _write(root, locator, observation)
                _rehash(root, locator)
                self.assert_has(_errors(root), error)

    def test_failed_sample_narrows_claim(self):
        with _fixture() as root:
            acceptance = _read(root, A)
            acceptance['representativeBehaviorPolicy']['historicalEvidence'][2][
                'claim'
            ] = 'overclaim'
            _write(root, A, acceptance)
            self.assert_has(
                _errors(root), 'historical claim binding is invalid'
            )
        excluded = _read(ROOT, A)['claimCeiling']['retainedBehaviorExclusions']
        self.assertEqual(excluded, ['GT-07:claude-code:cleanup'])
        archive = _read(ROOT, CURRENT_GT16_SOURCE)['records']
        self.assertTrue(all(archive[
            f'archive-observation-GT-{number}-553f5a9']['retainedFailure']
            for number in range(14, 17)))
        with _fixture() as root:
            _enable_current_sample_validation(root)
            acceptance = _read(root, A)
            token = excluded[0]
            acceptance['claimCeiling']['retainedBehaviorExclusions'].remove(token)
            acceptance['claimCeiling']['publicRetainedBehaviorExclusions'].pop(token)
            _write(root, A, acceptance)
            self.assert_has(
                _errors(root), 'retained behavior exclusions mismatch'
            )
        self.rejected(A, 'retained behavior exclusions', lambda v:
                      v['claimCeiling'].update(
                          retainedBehaviorExclusions=['GT-07:stale exclusion']))
        self.rejected(
            A, 'historicalTaskContracts', lambda v: v[
                'representativeBehaviorPolicy'
            ]['historicalTaskContracts']['GT-07'].update(
                goldenTaskSha256='0' * 64
            )
        )

        with _fixture() as root:
            acceptance = _read(root, A)
            ceiling = acceptance['claimCeiling']
            excluded = next(iter(ceiling['publicNotImplied']))
            ceiling['publicNotImplied'][excluded] = next(iter(
                ceiling['publicFiniteReleaseClaims'].values()
            ))
            _write(root, A, acceptance)
            self.assert_has(
                _errors(root),
                'public claim summaries overlap',
            )
        with _fixture() as root:
            locator = OBS[7]
            observation = _read(root, locator)
            observation['criterionDecisions']['Q4'] = 'accepted'
            observation['claimLimit'] = {'retainedFailure': False, 'excludedClaims': [], 'statement': 'all supported'}
            observation['residue'] = []
            errors, _ = _observe(root, locator, observation, 'failed fixture')
            self.assert_has(
                errors,
                'criterionDecisions contradict behavior',
                'claimLimit contradicts behavior',
                'cleanup contradicts residue',
            )
            locator = OBS[1]
            observation = _read(root, locator)
            observation['decision'] = {'state': 'failed'}
            errors, state = _observe(root, locator, observation, 'must-pass fixture')
            self.assertEqual(state, 'failed')
            self.assert_has(errors, 'failure lacks counterevidence')

    def test_current_sample_blocks_release(self):
        a,g=_read(ROOT,A),_read(ROOT,G)
        next(c for c in a['criteria'] if c['id']=='R3')['assessment']='verified'
        e=representative_sample_errors(
            ROOT,a,a['representativeBehaviorPolicy']['requiredTaskIdsForRelease'],
            g,lambda r,p,_:_read(r,p),True)
        self.assert_has(e,'representative tasks missing',
                        'R3 representative coverage mismatch')

        revision = _git(ROOT, 'rev-parse', 'HEAD', text=True).strip()
        task = {'behaviorSubjectFiles': ['yiyuan_accord/closure.py']}
        current_errors = _behavior_subject_revision_errors(
            ROOT, 'current subject', {'evaluatedRevision': revision}, task)
        subject_dirty = subprocess.run(
            ['git', '-C', str(ROOT), 'diff', '--quiet', 'HEAD', '--',
             'yiyuan_accord/closure.py'],
            stderr=subprocess.DEVNULL,
        ).returncode == 1
        if subject_dirty:
            self.assert_has(current_errors, 'behavior subject differs')
        else:
            self.assertEqual(current_errors, [])
        self.assert_has(_behavior_subject_revision_errors(
            ROOT, 'stale subject', {'evaluatedRevision': '84447a7a1b9557e22ef5585d159459e8701fa40e'}, task),
            'behavior subject differs from evaluatedRevision')

    def test_plan_process_acceptance_and_release_order_stay_aligned(self):
        with _fixture() as root:
            program = _read(root, P)
            program['releaseProcedure']['orderedGates'][0]['requiredTaskIds'].remove(
                'GT-13'
            )
            _write(root, P, program)
            self.assert_has(
                _errors(root),
                'requiredTaskIds is invalid',
            )

        with _indexed_fixture() as root:
            program = _read(root, P)
            workflow = root / '.github/workflows/validate.yml'
            body = workflow.read_bytes()
            mutations = (
                (b'permissions:\n  contents: read',
                 b'permissions: write-all\n# permissions: contents: read'),
                (b'run: python -B -m yiyuan_accord verify',
                 b'run: echo disabled # python -B -m yiyuan_accord verify'),
            )
            for old, new in mutations:
                workflow.write_bytes(body.replace(old, new))
                self.assert_has(_errors(root),
                                'derived surface markers or structure')
            workflow.write_bytes(body)
            readme = (root / 'README.md').read_text(encoding='utf-8')
            (root / 'README.md').write_text(
                readme.replace(
                    'Current release',
                    'Current experimental recommendation',
                    1,
                ),
                encoding='utf-8')
            self.assert_has(_errors(root), 'derived surface markers')
            (root / 'README.md').write_text(readme, encoding='utf-8')
            path = root / 'docs/operations/CONTINUATION.md'
            text = path.read_text(encoding='utf-8')
            path.write_text(
                text.replace(
                    'immutable, non-prerelease',
                    'v3.0.1 draft only',
                    1,
                ),
                encoding='utf-8',
            )
            self.assert_has(_errors(root), 'derived surface markers')
            path.write_text(text, encoding='utf-8')
            program['goalModePrompt']['mapsTo'].remove('Q4')
            increment = program['increment']
            increment['acceptanceIds'].remove('R3')
            increment['workItems'][0]['acceptanceIds'].remove('Q1')
            increment['workItems'][0]['closeoutSequence'][0]['state'] = 'active'
            increment['workItems'][0]['closeoutSequence'][0]['stopCondition'] = 'opposite'
            increment['fourSurfaceMapping']['outcomeId'] = 'wrong-outcome'
            increment['fourSurfaceMapping']['process']['phases'] = []
            increment['fourSurfaceMapping']['process']['orderedSteps'][1][
                'dependsOn'
            ] = []
            program['releaseProcedure']['orderedGates'][0]['id'] = ''
            program['goalModePrompt']['objective'] = '先推送再审查'
            program['goalModePrompt']['workStageIds'] = ['wrong']
            _write(root, P, program)
            self.assert_has(_errors(root), 'goalModePrompt.mapsTo',
                            'increment.acceptanceIds', 'workItems[0].acceptanceIds',
                            'closeoutSequence', 'required release gate sequence',
                            'workStageIds', 'objective is not the canonical projection',
                            'fourSurfaceMapping outcomeId',
                            'fourSurfaceMapping.process phases',
                            'orderedSteps[1].dependsOn',
                            )

        with _fixture() as root:
            program = _read(root, P)
            acceptance = _read(root, A)
            prompt = program['goalModePrompt']
            projection = json.loads(prompt['objective'])
            projection['route'] = {
                'semantics': 'do-not-execute-the-listed-route',
                'work': prompt['workStageIds'],
                'gates': prompt['releaseGateIds'],
                'actualInstruction': 'publish-first-and-skip-every-review-gate',
            }
            objective = json.dumps(
                projection, ensure_ascii=False, sort_keys=True, separators=(',', ':')
            )
            program['goalModePrompt']['objective'] = objective
            acceptance['canonicalGoalObjectiveSha256'] = hashlib.sha256(
                objective.encode('utf-8')
            ).hexdigest()
            _write(root, P, program)
            _write(root, A, acceptance)
            self.assert_has(
                _errors(root),
                'objective is not the deterministic structured projection',
            )

        program = _read(ROOT, P)
        increment = program['increment']
        increment['state'] = 'blocked'
        item = increment['workItems'][0]
        item['state'] = 'blocked'
        next(
            (stage for stage in item['closeoutSequence']
             if stage['state'] == 'active'),
            item['closeoutSequence'][-1],
        )['state'] = 'blocked'
        steps = increment['fourSurfaceMapping']['process']['orderedSteps']
        next(
            (step for step in steps if step['state'] == 'active'),
            steps[-1],
        )['state'] = 'blocked'
        blocked_errors = []
        criteria = set(program['goalModePrompt']['mapsTo'])
        _validate_four_surface_mapping(increment, criteria, blocked_errors)
        blocked_errors.extend(closeout_sequence_errors(item, criteria))
        self.assertFalse(blocked_errors)

        program = _read(ROOT, P)
        prompt = program['goalModePrompt']
        locators = ['authority/root.json', 'authority/evidence.json']
        projection = json.loads(canonical_goal_objective(
            program, {'semantic': locators},
            prompt['workStageIds'], prompt['releaseGateIds'],
        ))
        self.assertEqual(projection['authority']['locators'], locators)
        self.assertEqual(projection['authority']['mode'],
                         'reviewable-versioned-current-set')
        self.assertEqual(
            projection['outcome']['id'],
            'outcome.complete-bounded-self-bootstrapping-core',
        )
        self.assertEqual(
            _canonical_official_url('https://code.claude.com/docs/en/desktop'),
            'https://code.claude.com/docs/en/desktop',
        )
        self.assertEqual(
            _canonical_official_url(
                'https://learn.chatgpt.com/docs/environments/cloud-environment'
            ),
            'https://learn.chatgpt.com/docs/environments/cloud-environment',
        )
        self.assertEqual(
            projection['route']['semantics'],
            program['increment']['fourSurfaceMapping']['process']['routeRule'],
        )

    def test_evidence_cannot_self_verify_or_self_authorize(self):
        with _fixture() as root:
            acceptance = _read(root, A)
            criterion = acceptance['criteria'][0]
            criterion['assessment'] = 'verified'
            locator = 'evals/observations/self-deterministic.json'
            _write(root, locator, {'evidenceClass': 'deterministic-conformance'})
            criterion['evidence'] = [
                {'locator': P, 'sha256': hashlib.sha256((root / P).read_bytes()).hexdigest(),
                 'claim': 'self claim', 'supportsCriterion': 'R1'},
                {'locator': locator, 'sha256': hashlib.sha256((root / locator).read_bytes()).hexdigest(),
                 'claim': 'repository self-attestation', 'supportsCriterion': 'R1'}]
            acceptance['releaseAuthorization'].update(
                state='authorized', candidateRevision='0' * 40, namedHuman='repo',
                authorizedAt='2026-08-21T00:00:00Z', claimCeilingAccepted=True,
                publicationAuthorized=True, releaseAuthorized=True)
            _write(root, A, acceptance)
            report = verify_product(root)
            self.assert_has(report['errors'], 'direct evidence must use', 'deterministic conformance is computed live', 'cannot grant human authority')
            self.assertNotIn('releaseComplete', report)

    def test_external_release_contract_is_exact_and_external(self):
        self.assertIsNotNone(RELEASE_RE.fullmatch('v2.0.1-preview.1+build.7'))
        self.assertIsNotNone(CONTRACT_RELEASE_RE.fullmatch('v2.0'))
        for invalid in ('v2.0', 'v2.0.01', 'v2.0.1-01', '2.0.1', 'v2.0.1-'):
            with self.subTest(invalid_distribution=invalid):
                self.assertIsNone(RELEASE_RE.fullmatch(invalid))

        self.rejected(
            P, 'distributionVersion must be a v-prefixed semantic version',
            lambda v: v.update(distributionVersion='v2.0.01'),
        )
        self.rejected(
            P, 'release must name one v-prefixed contract line',
            lambda v: v.update(release='v2.0.1'),
        )
        self.rejected(
            P, 'acceptance.distributionVersion does not match program',
            lambda v: v.update(distributionVersion='v3.0.2'),
        )
        self.rejected(
            P, 'historicalRelease provenance is invalid',
            lambda v: v['historicalRelease'].update(
                unreleasedCheckpoint='v2.0.01'
            ),
        )
        self.rejected(
            P, 'historicalRelease provenance is invalid',
            lambda v: v['historicalRelease'].update(
                supersededDevelopmentDistributions=[]
            ),
        )
        self.rejected(
            P, 'reuses a superseded development distribution',
            lambda v: v.update(distributionVersion='v3.0.0'),
        )
        self.rejected(
            A, 'historicalRelease provenance is invalid',
            lambda v: v['historicalRelease'].update(releasedTags=[]),
        )
        self.rejected(
            P, 'required candidate systems are invalid',
            lambda v: v['releaseProcedure'].update(
                requiredCandidateVerificationSystemIds=['codex-cloud']
            ),
        )
        self.rejected(
            A, 'publicRelease maturity does not match semantic version',
            lambda v: v['publicRelease'].update(
                maturity='public-preview', prerelease=True
            ),
        )
        with _fixture() as root:
            acceptance = _read(root, A)
            acceptance['candidateVerification']['systems'] = {
                'codex-cloud': 'https://example.invalid'
            }
            acceptance['publicRelease']['assetPolicy'] = 'allow-assets'
            acceptance['claimCeiling']['finiteReleaseClaims'].append(acceptance['claimCeiling']['notImplied'][0])
            _write(root, A, acceptance)
            notes = root / acceptance['publicRelease']['releaseNotes']
            notes.write_text('# expanded\n', encoding='utf-8')
            self.assert_has(_errors(root), 'systems do not match', 'publicRelease policy',
                            'release notes digest', 'claims and exclusions overlap')

        with _fixture() as root:
            acceptance = _read(root, A)
            notes = root / acceptance['publicRelease']['releaseNotes']
            summary = next(iter(
                acceptance['claimCeiling']['publicNotImplied'].values()))
            notes.write_text(notes.read_text(encoding='utf-8').replace(
                'It does not imply:', f'- {summary}\n\nIt does not imply:', 1),
                encoding='utf-8')
            acceptance['publicRelease']['releaseNotesSha256'] = hashlib.sha256(notes.read_bytes()).hexdigest()
            _write(root, A, acceptance)
            self.assert_has(_errors(root), 'release notes do not expose the complete claim ceiling')

    def test_complexity_identity_and_paths_fail_closed(self):
        with _fixture() as root:
            report = verify_product(root)
            self.assert_has(report['errors'], 'tracked repository surface is unavailable')
            measured = report['complexity']['productCodeAndTestBytes']
            program = _read(root, P)
            percent = program['complexityBudget']['minimumProductCodeAndTestHeadroomPercent']
            valid_limit = (measured * 100 + 99 - percent) // (100 - percent)
            while valid_limit - measured < (valid_limit * percent + 99) // 100:
                valid_limit += 1
            target = program['complexityBudget']['targets']
            for limit, rejected in ((valid_limit - 1, True), (valid_limit, False)):
                target['maxProductCodeAndTestBytes'] = limit
                _write(root, P, program)
                errors = _errors(root)
                self.assertEqual(
                    any('complexity headroom too small' in error for error in errors),
                    rejected,
                )

        with _indexed_fixture() as root:
            revision = _git(root, 'rev-parse', 'HEAD', text=True).strip()
            (root / 'vendor').mkdir()
            _git(root, 'update-index', '--add', '--cacheinfo', '160000', revision, 'vendor')
            self.assert_has(
                _errors(root),
                'tracked repository entry is not a regular file: vendor (mode 160000)',
            )

        locator = 'docs/license-policy.md'
        for flag in ('--skip-worktree', '--assume-unchanged'):
            with self.subTest(index_flag=flag), _indexed_fixture() as root:
                _git(root, 'update-index', flag, locator)
                if flag == '--skip-worktree':
                    (root / '.DS_Store').write_bytes(b'\0retired_module\0')
                    (root / locator).unlink()
                else:
                    (root / locator).write_text('hidden drift\n', encoding='utf-8')
                self.assertEqual(
                    _git(root, 'status', '--porcelain=v1', '--untracked-files=all'), b''
                )
                report = verify_product(root)
                self.assertFalse(report['checkoutClean'])
                if flag == '--skip-worktree':
                    self.assert_has(report['errors'], f'active tree file is unreadable: {locator}')
                    self.assertTrue(_lacks(report['errors'], '.DS_Store'))
                else:
                    self.assertTrue(_lacks(report['errors'], locator))

        with _indexed_fixture() as root:
            locator = 'oversized-static-surface.bin'
            oversized = root / locator
            with oversized.open('wb') as stream:
                stream.truncate(2_000_000)
            _git(root, 'add', '-f', locator)
            with _deny_path('read_bytes', oversized):
                errors = _errors(root)
            self.assert_has(errors, f'active tree identity scan is indeterminate: {locator}')

        with _indexed_fixture() as root:
            locator = 'docs/license-policy.md'
            (root / locator).unlink()
            (root / locator).mkdir()
            self.assert_has(_errors(root),
                            f'active tree path is not a regular file: {locator}')

        with _fixture() as root, tempfile.TemporaryDirectory() as outside:
            program = _read(root, P)
            program['complexityBudget'].update(
                primaryInstructionPaths=[],
                forbiddenActivePaths=[Path(outside).as_posix()],
            )
            _write(root, P, program)
            constitution = _read(root, C)
            constitution['identity']['pythonModule'] = 'missing_module'
            constitution['authority']['executableVerifier'] = 'python -B -m missing_module verify'
            _write(root, C, constitution)
            markers = program['complexityBudget']['requiredTestMarkers']
            body = '\n'.join(f'    {item}(self): pass' for item in markers
                             if item.startswith('def '))
            bad_prefixes = (
                "@unittest.skip('x')\n",
                'def load_tests(*a): return unittest.TestSuite()\n',
                'from os import _exit as stop\nstop(0)\n',
            )
            for prefix in bad_prefixes:
                fake = f'import unittest\n{prefix}class ProductControlTests(unittest.TestCase):\n{body}'
                (root / 'tests/product/test_product_control.py').write_text(
                    fake, encoding='utf-8'
                )
                self.assert_has(
                    _errors(root), 'pythonModule does not match',
                    'primaryInstructionPaths', 'not a repository-relative path',
                    'test markers',
                )

    def test_identity_decoding_and_file_io_fail_closed(self):
        historical = 'Retired Product and retired-product'
        malformed = (b'\xff\xfeX', b'\xfe\xffX', b'\xff\xfe\x00\x00X', b'\x00\x00\xfe\xffX')
        retired = (
            historical.encode('utf-16'),
            b'\xfe\xff' + historical.encode('utf-16-be'),
            historical.encode('utf-32'),
            b'\x00\x00\xfe\xff' + historical.encode('utf-32-be'),
            b'\xef\xbb\xbf' + historical.encode(),
            'Ｒｅｔｉｒｅｄ Ｐｒｏｄｕｃｔ and ｒｅｔｉｒｅｄ－ｐｒｏｄｕｃｔ'.encode(),
        )
        cases = [
            *((payload, 'sample.txt', 'undecodable') for payload in malformed),
            *((payload, 'sample.txt', 'superseded identity') for payload in retired),
            (b'\xef\xbb\xbf#!/usr/bin/env python\nimport retired_module\n',
             'script', 'superseded identity'),
            (('# -*- coding: gb18030 -*-\nimport ｒｅｔｉｒｅｄ＿ｍｏｄｕｌｅ\n').encode('gb18030'),
             'sample.py', 'superseded identity'),
        ]
        mixed = '汉字' * 100 + '\npython -m retired_module\n'
        cases += [(mixed.encode(encoding), 'sample.sh', 'undecodable')
                  for encoding in ('utf-16-le', 'utf-16-be', 'utf-32-le', 'utf-32-be')]
        for payload, locator, message in cases:
            with self.subTest(locator=locator, prefix=payload[:4]):
                self.assert_has(_retired_byte_errors(payload, locator), message)

        safe = (
            (('汉字' * 100 + '\npython -m retired_module_other\n').encode(), 'sample.sh'),
            (('# -*- coding: gb18030 -*-\n# import ｒｅｔｉｒｅｄ＿ｍｏｄｕｌｅ\n').encode('gb18030'),
             'sample.py'),
        )
        for payload, locator in safe:
            self.assertTrue(_lacks(
                _retired_byte_errors(payload, locator), 'superseded identity', 'undecodable'
            ))

        png = b'\x89PNG\r\n\x1a\n' + b'bounded-fixture'
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            locator = 'assets/sample.png'
            target = root / locator
            target.parent.mkdir()
            target.write_bytes(png)
            assets = {locator: hashlib.sha256(png).hexdigest()}
            def scan(declared=None):
                with patch('yiyuan_accord.identity._bounded_git_bytes',
                           side_effect=_retired_history()):
                    return active_tree_errors(
                        root, [locator], '0' * 40,
                        digest_bound_binary_assets=declared,
                    )
            self.assertTrue(_lacks(
                scan(assets), 'digest-bound binary asset', 'undecodable',
            ))
            target.write_bytes(png + b'tampered')
            self.assert_has(
                scan(assets), 'digest-bound binary asset does not match',
            )
            self.assert_has(scan(), 'active tree file is undecodable')

        with _indexed_fixture() as root:
            target = root / 'docs/assets/sponsoring/wechat-pay.png'
            target.write_bytes(target.read_bytes() + b'tampered')
            self.assert_has(
                _errors(root),
                'digest-bound binary asset does not match',
            )

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            locator = 'sample.txt'
            target = root / locator
            target.write_text('safe\n', encoding='utf-8')
            original_open = __import__('os').open

            def deny_target(path, flags, *args):
                if Path(path) == target:
                    raise PermissionError('denied by fixture')
                return original_open(path, flags, *args)

            with patch('yiyuan_accord.identity._bounded_git_bytes', side_effect=_retired_history()), \
                    patch('yiyuan_accord.identity.os.open', deny_target):
                errors = active_tree_errors(root, [locator], '0' * 40)
            self.assert_has(errors, 'active tree file is unreadable: sample.txt')
            original_is_symlink = Path.is_symlink

            def active_symlink(path):
                return path == target or original_is_symlink(path)

            def never_follow_active(path, flags, *args):
                if Path(path) == target:
                    raise AssertionError('active-tree symlink target was read')
                return original_open(path, flags, *args)

            with patch('yiyuan_accord.identity._bounded_git_bytes', side_effect=_retired_history()), \
                    patch.object(Path, 'is_symlink', active_symlink), \
                    patch('yiyuan_accord.identity.os.open', never_follow_active):
                errors = active_tree_errors(root, [locator], '0' * 40)
            self.assertEqual(errors, ['symbolic link is not admitted in active tree: sample.txt'])

    def test_active_tree_reads_are_descriptor_bound(self):
        with _indexed_fixture() as root, tempfile.TemporaryDirectory() as outside:
            locator = 'docs/license-policy.md'
            target = root / locator
            decoy = Path(outside) / 'same-size.md'
            decoy.write_bytes(b'x' * target.stat().st_size)
            original_open = __import__('os').open

            def redirect(path, flags, *args):
                return original_open(
                    decoy if Path(path) == target else path, flags, *args
                )

            with patch('yiyuan_accord.identity.os.open', redirect):
                self.assert_has(
                    _errors(root),
                    f'active tree file is unreadable: {locator}',
                )

    def test_git_metadata_capture_is_bounded(self):
        with _indexed_fixture() as root:
            blob = _git(root, 'hash-object', '-w', '--stdin', input=b'').strip()
            records = b''.join(
                b'100644 ' + blob + b'\tbulk/' + str(index).encode()
                + b'-' + b'x' * 96 + b'.txt\n'
                for index in range(2_500)
            )
            _git(root, 'update-index', '--index-info', input=records)
            self.assertGreater(len(records), 262_144)
            self.assert_has(
                _errors(root),
                'tracked repository surface is unavailable',
            )

    def test_historical_identity_capture_is_bounded(self):
        with _indexed_fixture() as root:
            constitution = _read(root, C)
            constitution['oversizedFixture'] = 'x' * 1_000_001
            _write(root, C, constitution)
            _git(root, 'add', C)
            _git(root, '-c', 'user.name=Accord Fixture',
                 '-c', 'user.email=fixture@example.invalid', 'commit', '--quiet',
                 '-m', 'oversized historical identity')
            revision = _git(root, 'rev-parse', 'HEAD', text=True).strip()
            self.assert_has(
                active_tree_errors(root, [], revision),
                'historical identity boundary is unavailable',
            )

    def test_conservative_identity_boundary_allows_declared_safe_surfaces(self):
        errors = _errors(ROOT)
        self.assertTrue(_lacks(
            errors, 'superseded identity', 'identity scan is indeterminate', 'test markers'
        ), errors)

        safe_cases = {
            'sample.py': (
                '# retired_module\n# import retired_module\nvalue = 1\n',
                '# Retired Product\n# retired-product\nvalue = 1\n',
                'retired_module_other = "retired_module_other"\n',
                'value = "Retired Productive retired-product_other"\n',
                'value = "retired-product-other"\n',
                'value = f"retired_{name}module"\n',
                'value = rf"retired_\\u006dodule"\n',
                'value = fr"Retired\\x20Product"\n',
                'value = (' + "'safe' + " * 999 + "'safe')\n",
                'value = ' + _balanced_add(['name'] + ["'safe'"] * 5_000) + '\n',
                'value = ' + _balanced_add(["'safe'"] * 4_096) + '\n',
            ),
            'sample.txt': ('retired_module_other xretired_module harnessed\n',
                           'Retired Productive retired-product_other\n',
                           'retired-product-other\n'),
            'sample.json': ('{"module":"retired_module_other"}\n',
                            '{"module":"retired_\\u006dodule"}\n'),
            'sample.yaml': ('module: retired_module_other\n',
                            'module: retired_\\x6dodule\n'),
            'sample.sh': ('printf %s retired_module_other\n',),
        }
        for locator, bodies in safe_cases.items():
            for body in bodies:
                self.assertTrue(_lacks(_retired_raw_errors(body, locator),
                                       'superseded identity', 'indeterminate'))

        locator = 'research/reviews/reference.md'
        admitted = _active_file_errors(
            locator, 'Historical retired_module reference.\n', {locator}
        )
        self.assertTrue(_lacks(admitted, 'superseded identity'))

    def test_retired_identity_static_surfaces_are_rejected(self):
        deep_retired = (
            'value = (' + "'safe ' + " * 999
            + "'retired_' + 'module')\n"
        )
        cases = {
            'sample.py': (
                'import retired_module\n',
                'from retired_module import item\n',
                'retired_module = 1\n',
                'value = "retired_module"\n',
                'value = "retired_" + "module"\n',
                'title = "Retired Product"\n',
                'slug = "retired-" + "product"\n',
                'value = f"retired_" f"module"\n',
                'value = f"retired_" "module"\n',
                'value = f"retired_\\u006dodule"\n',
                'value = f"retired_\\155odule"\n',
                'value = f"retired_\\N{LATIN SMALL LETTER M}odule"\n',
                'value = f"retired_' + '\\' + '\nmodule"\n',
                'value = f"{\'retired_\' + \'module\'}"\n',
                deep_retired,
            ),
            'sample.txt': (
                'retired_module\n',
                'python -m retired_module\n',
                'printf retired_module | python -\n',
            ),
            'sample.sh': (
                '# retired_module\n',
                "printf '%s\\n' 'import retired_module' | python -\n",
                "printf '%s\\n' 'import retired_module' | python\n",
                "printf '%s\\n' 'import retired_module' | python -u -\n",
                "printf '%s\\n' 'import retired_module' | python /dev/stdin\n",
            ),
            'sample.ps1': (
                "Write-Output 'retired_module'\r\n",
                'powershell -EncodedCommand retired_module\r\n',
            ),
            'sample.cmd': (
                'echo retired_module\r\n',
                'set cmd=python -m retired_module\r\n',
            ),
            'sample.json': (
                '{"module":"retired_module"}\n',
            ),
            'sample.yaml': (
                'module: retired_module\n',
            ),
        }
        for locator, bodies in cases.items():
            for body in bodies:
                with self.subTest(locator=locator, body=body[-80:]):
                    self.assert_has(
                        _retired_raw_errors(body, locator),
                        'superseded identity remains',
                    )

        for body in (
            'value = t"retired_module"\n',
            'value = t"retired_\\155odule"\n',
            'value = rt"retired_\\u006dodule"\n',
        ):
            with self.subTest(shared_python_grammar=body):
                self.assert_has(
                    _retired_raw_errors(body, 'sample.py'),
                    'active tree identity scan is indeterminate',
                )

        self.assert_has(
            _retired_raw_errors('ｒｅｔｉｒｅｄ＿ｍｏｄｕｌｅ\n'),
            'superseded identity remains',
        )
        self.assert_has(
            _retired_raw_errors('safe' * 250_001),
            'active tree identity scan is indeterminate',
        )
        self.assert_has(
            _retired_raw_errors(
                'value = ' + _balanced_add(["'safe'"] * 4_097) + '\n',
                'sample.py',
            ),
            'active tree identity scan is indeterminate',
        )

        self.assert_has(
            _active_file_errors('retired_module/config.txt'),
            'superseded identity remains',
        )
        locator = 'docs/new-surface.txt'
        message = 'superseded identity remains in active tree: ' + locator
        self.assert_has(_active_file_errors(locator, 'retired_module\n'), message)
        self.assert_has(
            _active_file_errors(locator, 'retired_module\n', {locator}), message
        )

    def test_retired_residue_and_duplicate_json_fail_closed(self):
        with _fixture() as root:
            retired = 'yiyuan_accord/task_validator_o4_continuous_self_correction_v3.py'
            (root / retired).mkdir()
            (root / '.tmp').mkdir()
            (root / '.remember').mkdir()
            self.assert_has(_errors(root), f'forbidden active path remains: {retired}',
                            'known task residue', '.remember')
            with patch('yiyuan_accord.guardrails.os.walk', side_effect=lambda *_, onerror, **k:
                       (onerror(OSError()), ())[1]):
                self.assert_has(_errors(root), '<unreadable>')
        self.assert_has(_retired_raw_errors('retired-product', 'README.md'),
                        'superseded identity remains')
        with _fixture() as root:
            (root / P).write_text('{"schema":2,"schema":2}\n', encoding='utf-8')
            self.assert_has(_errors(root), 'duplicate JSON key')
        with _fixture() as root:
            target = root / P
            with target.open('wb') as stream:
                stream.truncate(2_000_000)
            with _deny_path('read_bytes', target):
                errors = _errors(root)
            self.assert_has(errors, f'invalid JSON {P}', 'exceeds 1000000 bytes')
        with _fixture() as root:
            locator = 'research/reviews/oversized-input.md'
            target = root / locator
            target.parent.mkdir(parents=True, exist_ok=True)
            with target.open('wb') as stream:
                stream.truncate(2_000_000)
            program = _read(root, P)
            program['inputEvidence'].append({
                'id': 'oversized-input', 'kind': 'bounded-input',
                'repositoryLocator': locator, 'repositorySha256': '0' * 64,
                'disposition': 'test-only',
            })
            _write(root, P, program)
            with _deny_path('read_bytes', target):
                errors = _errors(root)
            self.assert_has(errors, 'digest source is oversized')

    def test_live_hook_stays_silent_for_fresh_startup(self):
        node = shutil.which('node')
        self.assertIsNotNone(node, 'the selected live-hook adapter requires node')
        event = {
            'session_id': 'must-not-be-emitted-or-persisted',
            'transcript_path': 'must-not-be-opened-or-emitted',
            'cwd': 'C:/disposable/workspace',
            'hook_event_name': 'SessionStart',
            'model': 'fixture-model',
            'permission_mode': 'default',
            'source': 'startup',
        }
        with tempfile.TemporaryDirectory(prefix='accord-hook-') as temporary:
            result = subprocess.run(
                [node, str(ROOT / 'runtime' / 'accord-hook.cjs')],
                input=json.dumps(event), text=True, capture_output=True,
                cwd=temporary, timeout=HOOK_PROCESS_TIMEOUT_SECONDS,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout, '')
            self.assertEqual(list(Path(temporary).iterdir()), [])

    def test_live_hook_emits_only_typed_minimum_continuity_context(self):
        node = shutil.which('node')
        self.assertIsNotNone(node, 'the selected live-hook adapter requires node')
        event = {
            'session_id': 'private-session-sentinel',
            'transcript_path': 'private-transcript-sentinel',
            'cwd': 'C:/private-workspace-sentinel',
            'hook_event_name': 'SessionStart',
            'model': 'fixture-model',
            'permission_mode': 'default',
            'source': 'compact',
        }
        with tempfile.TemporaryDirectory(prefix='accord-hook-') as temporary:
            result = subprocess.run(
                [node, str(ROOT / 'runtime' / 'accord-hook.cjs')],
                input=json.dumps(event), text=True, capture_output=True,
                cwd=temporary, timeout=HOOK_PROCESS_TIMEOUT_SECONDS,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            envelope = json.loads(result.stdout)
            context = json.loads(
                envelope['hookSpecificOutput']['additionalContext'])
            self.assertEqual(envelope['hookSpecificOutput']['hookEventName'],
                             'SessionStart')
            self.assertEqual(context, {
                'schema': 'yiyuan-accord-hook-context/v1',
                'signal': {
                    'event': 'SessionStart',
                    'source': 'compact',
                    'sourceKind': 'supported-official-hook-event',
                },
                'eventHints': [
                    {
                        'field': 'host.model',
                        'value': 'fixture-model',
                        'sourceRef': 'SessionStart.model',
                    },
                    {
                        'field': 'host.permission-mode',
                        'value': 'default',
                        'sourceRef': 'SessionStart.permission_mode',
                    },
                ],
                'directives': [
                    'invalidate-dependent-assumptions',
                    're-sense-decision-relevant-state-from-supported-official-structured-sources',
                    'hold-missing-or-conflicting-fields-unknown',
                    'preserve-independently-bound-last-safe-allocation',
                    'use-fresh-zero-history-only-if-sequential-relief-is-required',
                    'verify-destination-before-source-release',
                ],
                'claimLimit': [
                    'signal-is-not-current-task-state',
                    'signal-is-not-user-authority',
                    'event-hints-are-not-state-receipts',
                    'injection-is-not-agent-use-execution-consequence-evidence-or-value',
                ],
            })
            self.assertNotIn('private-session-sentinel', result.stdout)
            self.assertNotIn('private-transcript-sentinel', result.stdout)
            self.assertNotIn('private-workspace-sentinel', result.stdout)
            self.assertEqual(list(Path(temporary).iterdir()), [])

    def test_live_hook_distinguishes_recovery_from_fresh_sources(self):
        node = shutil.which('node')
        self.assertIsNotNone(node, 'the selected live-hook adapter requires node')
        base = {
            'session_id': 'private-session-sentinel',
            'transcript_path': 'private-transcript-sentinel',
            'cwd': 'C:/private-workspace-sentinel',
            'hook_event_name': 'SessionStart',
            'model': 'fixture-model',
            'permission_mode': 'default',
        }
        with tempfile.TemporaryDirectory(prefix='accord-hook-') as temporary:
            fresh = subprocess.run(
                [node, str(ROOT / 'runtime' / 'accord-hook.cjs')],
                input=json.dumps({**base, 'source': 'clear'}), text=True,
                capture_output=True, cwd=temporary,
                timeout=HOOK_PROCESS_TIMEOUT_SECONDS,
            )
            resumed = subprocess.run(
                [node, str(ROOT / 'runtime' / 'accord-hook.cjs')],
                input=json.dumps({**base, 'source': 'resume'}), text=True,
                capture_output=True, cwd=temporary,
                timeout=HOOK_PROCESS_TIMEOUT_SECONDS,
            )
            self.assertEqual(fresh.returncode, 0, fresh.stderr)
            self.assertEqual(fresh.stdout, '')
            self.assertEqual(resumed.returncode, 0, resumed.stderr)
            envelope = json.loads(resumed.stdout)
            context = json.loads(
                envelope['hookSpecificOutput']['additionalContext'])
            self.assertEqual(context['signal'], {
                'event': 'SessionStart',
                'source': 'resume',
                'sourceKind': 'supported-official-hook-event',
            })
            self.assertEqual(list(Path(temporary).iterdir()), [])

    def test_live_hook_does_not_propagate_invalid_or_unbound_fields(self):
        node = shutil.which('node')
        self.assertIsNotNone(node, 'the selected live-hook adapter requires node')
        event = {
            'session_id': 'private-session-sentinel',
            'transcript_path': 'private-transcript-sentinel',
            'cwd': 'C:/private-workspace-sentinel',
            'hook_event_name': 'SessionStart',
            'model': {'raw': 'private-model-sentinel'},
            'permission_mode': ['private-permission-sentinel'],
            'source': 'compact',
        }
        with tempfile.TemporaryDirectory(prefix='accord-hook-') as temporary:
            invalid_fields = subprocess.run(
                [node, str(ROOT / 'runtime' / 'accord-hook.cjs')],
                input=json.dumps(event), text=True, capture_output=True,
                cwd=temporary, timeout=HOOK_PROCESS_TIMEOUT_SECONDS,
            )
            malformed = subprocess.run(
                [node, str(ROOT / 'runtime' / 'accord-hook.cjs')],
                input='{malformed', text=True, capture_output=True,
                cwd=temporary, timeout=HOOK_PROCESS_TIMEOUT_SECONDS,
            )
            unknown_source = subprocess.run(
                [node, str(ROOT / 'runtime' / 'accord-hook.cjs')],
                input=json.dumps({**event, 'source': 'unknown'}), text=True,
                capture_output=True, cwd=temporary,
                timeout=HOOK_PROCESS_TIMEOUT_SECONDS,
            )
            self.assertEqual(invalid_fields.returncode, 0,
                             invalid_fields.stderr)
            envelope = json.loads(invalid_fields.stdout)
            context = json.loads(
                envelope['hookSpecificOutput']['additionalContext'])
            self.assertEqual(context['eventHints'], [])
            self.assertNotIn('private-model-sentinel', invalid_fields.stdout)
            self.assertNotIn('private-permission-sentinel',
                             invalid_fields.stdout)
            self.assertEqual(malformed.returncode, 1)
            self.assertEqual(malformed.stdout, '')
            self.assertEqual(
                malformed.stderr,
                'YIYUAN Accord: invalid SessionStart hook input; state remains unknown.\n',
            )
            self.assertEqual(unknown_source.returncode, 1)
            self.assertEqual(unknown_source.stdout, '')
            self.assertEqual(unknown_source.stderr, malformed.stderr)
            self.assertEqual(list(Path(temporary).iterdir()), [])

    def test_live_hook_is_packaged_behind_both_host_adapters(self):
        canonical = (ROOT / 'runtime' / 'accord-hook.cjs').read_bytes()
        projections = {
            'codex': (
                'plugins/yiyuan-accord-codex',
                {
                    'type': 'command',
                    'command': 'node "${PLUGIN_ROOT}/runtime/accord-hook.cjs"',
                    'timeout': 3,
                    'additionalContextLimit': 700,
                },
            ),
            'claude-code': (
                'plugins/yiyuan-accord-claude',
                {
                    'type': 'command',
                    'command': 'node "${CLAUDE_PLUGIN_ROOT}/runtime/accord-hook.cjs"',
                    'timeout': 3,
                },
            ),
        }
        for adapter, (root, expected_handler) in projections.items():
            with self.subTest(adapter=adapter):
                self.assertEqual(
                    (ROOT / root / 'runtime' / 'accord-hook.cjs').read_bytes(),
                    canonical,
                )
                hook = _read(ROOT, f'{root}/hooks/hooks.json')
                handler = hook['hooks']['SessionStart'][0]['hooks'][0]
                self.assertEqual(handler, expected_handler)
