from contextlib import contextmanager
import hashlib, json, re, shutil, subprocess, tempfile, unittest
from pathlib import Path
from unittest.mock import patch
from yiyuan_accord.closure import reconcile_closure
from yiyuan_accord.control import (
    _validate_evidence_item, _validate_four_surface_mapping,
    _validate_closeout_snapshot, _snapshot_lineage_contract_errors,
    _snapshot_documents, _snapshot_revision_contract_errors,
    _snapshot_bytes, _snapshot_v1_evidence_errors, _snapshot_v1_lineage,
    _snapshot_v1_projection_package_errors,
    _snapshot_v1_projection_shape_errors,
    _snapshot_v2_node_errors, _snapshot_v2_transition_errors,
    _validate_exact_package_evidence_lifecycle,
    _snapshot_v1_transition_errors, _snapshot_v1_json_structure_is_bounded,
    _SNAPSHOT_V1_MAX_JSON_DEPTH,
    _semantic_version_precedence,
    host_check, verify_product,
)
from yiyuan_accord.evidence import (
    FROZEN_GT20_21_REPRESENTATIVE_LANES,
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
    frozen_gt20_21_promotion_errors,
    provisional_gt20_21_source_errors,
    representative_contract_sha256 as _contract_sha,
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
    _bounded_git_bytes,
    _public_release_record_valid,
    active_tree_errors,
    release_identity_errors,
)
ROOT = Path(__file__).resolve().parents[2]
TC = unittest.TestCase
# CI deadlock guard; not the three-second product Hook timeout.
HOOK_PROCESS_TIMEOUT_SECONDS = 60
(C, A, P, G) = ('product/constitution.json', 'product/acceptance.json', 'product/program.json', 'evals/golden-tasks.json')
SOURCE = 'evals/evidence/2026-08-24-v20-representative-source.json'
GT11_SOURCE = 'evals/evidence/2026-08-27-v310-codex-local-regression-source.json'
GT11_OBSERVATION = 'evals/observations/2026-08-28-f4dce57-gt-11-codex-local.json'
GT16_SOURCE = 'evals/evidence/2026-08-28-553f5a9-gt14-16-codex-local-source.json'
CURRENT_GT17_OBSERVATION = 'evals/observations/2026-08-28-fd4b99a-gt-17-codex-local.json'
GT2021_SOURCE = 'evals/evidence/2026-08-30-v310-gt20-21-source.json'
FROZEN_OBS = (
    'evals/observations/cf1d8c9-gt20-frozen-r3-promotion.json',
    'evals/observations/cf1d8c9-gt21-frozen-r3-promotion.json',
)
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

def _clone(value): return json.loads(json.dumps(value))

def _reader(root, locator, _): return _read(root, locator)

def _sha(data): return hashlib.sha256(data).hexdigest()

def _file_sha(root, locator): return _sha((root / locator).read_bytes())

def _canonical(value): return json.dumps(
    value, ensure_ascii=False, sort_keys=True, separators=(',', ':'))

def _find(items, field, value):
    return next(item for item in items if item[field] == value)

def _event(payload, kind='independent-poststate'):
    return _find(payload['materialEvents'], 'kind', kind)

def _hook_event(source, **changes):
    return {**{
        'session_id': 'private-session-sentinel',
        'transcript_path': 'private-transcript-sentinel',
        'cwd': 'C:/private-workspace-sentinel',
        'hook_event_name': 'SessionStart',
        'model': 'fixture-model',
        'permission_mode': 'default',
        'source': source,
    }, **changes}

def _run_hook(case, event, cwd):
    node = shutil.which('node')
    case.assertIsNotNone(node, 'the selected live-hook adapter requires node')
    return subprocess.run(
        [node, str(ROOT / 'runtime' / 'accord-hook.cjs')],
        input=event if isinstance(event, str) else json.dumps(event),
        text=True, capture_output=True, cwd=cwd,
        timeout=HOOK_PROCESS_TIMEOUT_SECONDS,
    )

@contextmanager
def _hook_workspace(case):
    with tempfile.TemporaryDirectory(prefix='accord-hook-') as temporary:
        yield temporary
        case.assertEqual(list(Path(temporary).iterdir()), [])

def _projection_identity(report, adapter='codex'):
    identity = report['identity']
    return {
        'adapterId': adapter, 'contract': report['contract'],
        'skill': report['skill'], 'mechanismFiles': report['mechanismFiles'],
        **{field: identity[field] for field in (
            'contractSha256', 'skillSha256', 'mechanismSha256'
        )},
    }

_DELETE = object()

def _replace(value, path, replacement):
    if isinstance(path, str):
        path = path.split('.')
    for part in path[:-1]:
        value = value[part]
    if replacement is _DELETE:
        value.pop(path[-1])
    else:
        value[path[-1]] = (replacement(value[path[-1]])
                           if callable(replacement) else replacement)

def _write(root, locator, value):
    path = root / locator
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, separators=(',', ':')) + '\n', encoding='utf-8')

def _git(root, *arguments, **options):
    if options.get('text') and 'encoding' not in options:
        options['encoding'] = 'utf-8'
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

def _make_indexed():
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
def _indexed():
    temporary, target = _make_indexed()
    with temporary:
        yield target

@contextmanager
def _provisional():
    with tempfile.TemporaryDirectory(prefix='ya-provisional-') as temporary:
        target = Path(temporary) / 'repository'
        subprocess.run(
            ['git', 'clone', '--quiet', '--no-hardlinks', str(ROOT), str(target)],
            check=True,
        )
        for locator in (
            'yiyuan_accord/control.py',
            'yiyuan_accord/evidence.py',
            P,
            A,
            G,
            GT2021_SOURCE,
            *FROZEN_OBS,
        ):
            shutil.copy2(ROOT / locator, target / locator)
        yield target

def _rehash(root, locator):
    acceptance = _read(root, A)
    digest = _file_sha(root, locator)
    items = [
        item for criterion in acceptance['criteria']
        for item in criterion['evidence']
    ] + acceptance['representativeBehaviorPolicy']['historicalEvidence']
    for item in items:
        if item['locator'] == locator:
            item['sha256'] = digest
    _write(root, A, acceptance)

def _rehash_input(root, locator):
    program = _read(root, P)
    digest = _file_sha(root, locator)
    for item in program['inputEvidence']:
        if item.get('repositoryLocator') == locator:
            item['repositorySha256'] = digest
    lifecycle = program.get('increment', {}).get(
        'provisionalEvidenceLifecycle', {}
    )
    if lifecycle.get('sourceLocator') == locator:
        lifecycle['sourceSha256'] = digest
    _write(root, P, program)

def _enable_current_sample_validation(root):
    acceptance = _read(root, A)
    criterion = _find(acceptance['criteria'], 'id', 'R3')
    criterion['assessment'] = 'continuing'
    _write(root, A, acceptance)

def _bind_source(root, locator, bundle, observation):
    _write(root, SRC310, bundle)
    observation['transcriptOrEventEvidence'][0]['sha256'] = _digest(bundle[
        'records'][observation['taskId']])
    _write(root, locator, observation)
    _rehash(root, locator)

def _observe(
    root, locator, observation=None, label='fixture observation',
    require_current_subject=False, current_contract=None,
):
    golden, observed = _read(root, G), observation or _read(root, locator)
    task = _find(golden['tasks'], 'id', observed['taskId'])
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
        _reader, require_current_subject, current_contract,
    )

def _source_errors(
    root, locator, bundle, observation, src_path=SOURCE,
):
    source = observation['transcriptOrEventEvidence'][0]
    record = bundle['records'][source['recordId']]
    _write(root, src_path, bundle)
    source['sha256'] = _digest(record)
    task = _find(_read(root, G)['tasks'], 'id', observation['taskId'])
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
    event = _clone(historical_event)
    episodes = event['episodes']
    baseline, replacement = 'current-plugin', 'native-no-add'
    event['behaviorArms'].pop('readOnlyBlocked', None)
    event['behaviorArms']['AccordBacked']['finalAnswerTranscriptionErrors'] = []
    episode_data = (
        ('gt19-observation-1', 'gt19-composition-1', 7,
         '2026-08-29T00:00:00Z', '2026-08-29T00:01:00Z', [],
         'absent', 'allocated', None, 'retain-Accord-baseline', 'current'),
        ('gt19-observation-1', 'gt19-composition-1', 7,
         '2026-08-29T00:00:00Z', '2026-08-29T00:02:00Z',
         ['user-intervention'], 'injection-observed-effect-unknown',
         'preserved-last-valid', None,
         'retain-last-valid-on-invalidated-receipt', 'invalidated-event-only'),
        ('gt19-observation-2', 'gt19-composition-2', 8,
         '2026-08-29T00:03:00Z', '2026-08-29T00:04:00Z', [],
         'admitted-current', 'retired-with-recheck', 'allocated',
         'retire-exact-redundant-allocation', 'current-resensed'),
        ('gt19-observation-3', 'gt19-composition-3', 9,
         '2026-08-29T00:05:00Z', '2026-08-29T00:06:00Z', [],
         'evidence-expired', 'restored', 'unavailable',
         'restore-after-native-expiry', 'current-recomputed'),
    )
    for order, data in enumerate(episode_data):
        episode = episodes[order]
        request = episode['closureRequest']
        environment, routes = request['environment'], request['routes']
        request['schema'] = 'yiyuan-accord-closure/v2'
        (identity, composition, generation, captured, decision, invalidations,
         h_state, a_state, replacement_state, disposition, freshness) = data
        environment['compositionKey'] = composition
        environment['observation'] = {
            'id': identity,
            'compositionKey': composition,
            'generation': generation,
            'capturedAt': captured,
            'decisionAt': decision,
            'validUntil': '2026-08-29T00:20:00Z',
            'stateBindings': [],
            'invalidatedBy': invalidations,
        }
        for route in routes:
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
        observation = environment['observation']
        observation['stateBindings'] = (
            _clone(episodes[0]['closureRequest'][
                'environment']['observation']['stateBindings'])
            if order == 1 else _gt19_state_bindings(
                request, composition, generation, order
            )
        )
        environment['lastSafeAllocation'] = (
            {
                'routeId': baseline,
                'responsibilityModes': {
                    responsibility: _find(routes, 'id', baseline)[
                        'responsibilityModes'][responsibility]
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
            injection = _clone(request['events'][0])
            injection['factId'] = 'context-injection'
            injection['state'] = 'observed'
            injection['independent'] = 'unknown'
            request['events'] = [injection]
        episode['disposition'] = disposition
        episode['sparseViews']['H'] = {
            f'{replacement}/sense-environment': h_state,
        }
        episode['sparseViews']['A'] = {
            f'{baseline}/sense-environment': a_state,
            f'{baseline}/bind-authority': 'preserved-outside-scope',
        }
        if replacement_state is not None:
            episode['sparseViews']['A'][
                f'{replacement}/sense-environment'
            ] = replacement_state
        episode['sparseViews']['S'] = {
            binding['field']: {
                key: binding[key] for key in (
                    'targetKind', 'subjectRef', 'factId', 'value', 'writer',
                    'readers', 'sourceKind', 'sourceRef',
                    'unavailableSources', 'generation',
                )
            } | {'freshness': freshness}
            for binding in observation['stateBindings']
        }
        _refresh_gt19_episode(episode)

    allocations = (
        {'sense-environment': baseline, 'bind-authority': baseline},
        {'sense-environment': baseline, 'bind-authority': baseline},
        {'sense-environment': replacement, 'bind-authority': baseline},
        {'sense-environment': baseline, 'bind-authority': baseline},
    )
    states = []
    for order, episode in enumerate(episodes):
        receipt = episode['closureRequest']['environment']['observation']
        states.append({
            'episodeOrder': order,
            'effectiveAllocations': allocations[order],
            'retiredAllocations': (
                [f'{baseline}/sense-environment'] if order == 2 else []
            ),
            'observationId': receipt['id'],
            'observationGeneration': receipt['generation'],
            'evidenceFreshness': episode_data[order][-1],
        })
    for order, edge in enumerate(event['carrierEdges']):
        edge['sourceState'] = states[order]
        edge['targetState'] = states[order + 1]
        edge['sourceStateSha256'] = _digest(edge['sourceState'])
        edge['targetStateSha256'] = _digest(edge['targetState'])
    event['stateCarrier']['finalEffectiveAllocations'] = allocations[3]
    event['stateCarrier']['lastObservationId'] = episode_data[3][0]
    event['stateCarrierSha256'] = _digest(event['stateCarrier'])
    event['revision'] = revision
    event['sequenceSha256'] = _sequence_digest(event)
    return {'evaluatedRevision': revision, 'materialEvents': [event]}

def _retired_errors(body, locator='sample.txt', encoding='utf-8'):
    return _byte_errors(body.encode(encoding), locator)

def _byte_errors(body, locator='sample.txt'):
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        (root / locator).write_bytes(body)
        return _history_errors(root, [locator])

def _history_errors(root, locators, research=None):
    with patch('yiyuan_accord.identity._bounded_git_bytes',
               side_effect=_retired_history()):
        return active_tree_errors(root, locators, '0' * 40, research or set())

def _active_errors(locator, body='safe\n', research=None):
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
            self.at(any(fragment in error for error in errors), fragment)

    ae = TC.assertEqual
    at = TC.assertTrue
    af = TC.assertFalse
    an = TC.assertIsNone
    ann = TC.assertIsNotNone
    ai = TC.assertIn
    ani = TC.assertNotIn
    age = TC.assertGreaterEqual
    ale = TC.assertLessEqual
    ane = TC.assertNotEqual
    anr = TC.assertNotRegex
    has = assert_has

    def rejected(self, locator, message, mutate):
        with _fixture() as root:
            value = _read(root, locator)
            mutate(value)
            _write(root, locator, value)
            self.has(_errors(root), message)

    def test_current_contract_is_valid_and_explicitly_incomplete(self):
        temporary, root = _make_indexed()
        self.addCleanup(temporary.cleanup)
        report = verify_product(root)
        self.at(report['valid'], report['errors'])
        self.ae(report['criteria']['ids'], CRITERIA)
        if report['programStatus'] == 'active':
            program = _read(root, P)
            stages = program['increment']['workItems'][0]['closeoutSequence']
            self.ai('self-audit-remediate-and-reaccept-whole-system-balance',
                          {stage['id'] for stage in stages})
            self.ae(
                all(stage['state'] == 'completed' for stage in stages),
                program['increment']['state'] == 'completed',
            )
            self.af(report['repositoryCandidateReady'])
        else:
            self.ae(report['programStatus'], 'ready')
            self.ae(report['criteria']['verified'], 8)
            self.ae(report['repositoryCandidateReady'], report['checkoutClean'])
        self.at(all(host['staticReady'] for host in report['hostChecks'].values()))
        program, acceptance = _read(root, P), _read(root, A)
        constitution = _read(root, C)
        guidance = _read(root, 'product/reshaping-guidance.json')
        self.ae(guidance['status'], 'accepted-revisable-guidance')
        adaptive = guidance['adaptiveSystem']
        self.ae(adaptive['stageStateContract']['role'],
                         'derived-referenceable-node-not-authority-or-release-evidence')
        self.ae(len(adaptive['evolutionHorizon']['candidateClasses']), 7)
        self.ae(
            guidance['wholeSystemBalanceReview']['status'],
            'completed-refreshed-independent-review-accepted-candidate-selected',
        )
        for locator, stale in (
            ('README.md', 'GT-19 host-drift lane is designed but'),
            ('README.zh-CN.md', 'GT-19 宿主漂移任务已经设计但尚未执行'),
            ('docs/architecture.md', 'It is designed but unperformed'),
            ('docs/releases/v3.1.0.md', 'host-drift behavior but is unperformed'),
            ('docs/operations/CONTINUATION.md', 'behavior, but remains unperformed'),
        ):
            self.ani(stale, (root / locator).read_text(encoding='utf-8'))
        self.ae(
            guidance['dynamicIndex']['graphProjection']['implementation'],
            'derived-in-memory-or-ignored-cache-first',
        )
        self.ai('model-inherent',
                      guidance['capabilityDiscovery']['provenanceKinds'])
        self.ai('Cartesian product',
                      guidance['dynamicIndex']['graphProjection']['normalizationRule'])
        model = guidance['selfBootstrappingCore']['semanticModel']
        graph = guidance['dynamicIndex']['graphProjection']
        self.ae(model['id'], 'complete-bounded-self-bootstrapping/v1')
        self.ae(model['factModel']['values'],
                         ['observed', 'not-observed', 'unknown'])
        leveraged = model['hostLeveragedBootstrap']
        self.ae(
            [item['id'] for item in leveraged['dimensions']],
            [
                'self-knowledge', 'self-coherence', 'bounded-autonomy',
                'on-demand-learning', 'correction', 'recovery',
                'external-verifiability', 'governed-evolution',
            ],
        )
        self.ae(
            leveraged['allocationModesRef'],
            '#/selfBootstrappingCore/semanticModel/responsibilityAllocation/modes',
        )
        self.ai('upstream AI Agent', leveraged['upstreamRule'])
        self.ai('not eight built-in abilities', leveraged['evidenceRule'])
        self.ai(
            'does not claim host-independent operation',
            leveraged['independenceLimit'],
        )

        self.ae(
            model['routeDecision']['comparison']['mode'],
            'pareto-then-context-then-equivalent-fit-reuse-tiebreak',
        )
        self.ae(model['formAllocation']['cardinality'],
                         'many-to-many-context-and-freshness-bound')
        self.at(
            {item['id'] for item in model['entities']}
            <= set(graph['nodeKinds'])
        )
        self.at(
            {item['id'] for item in model['relationKinds']}
            <= set(graph['edgeKinds'])
        )
        invariants = {item['id'] for item in model['invariants']}
        self.ai('authority-is-not-derived', invariants)
        self.at(all(set(item['guards']) <= invariants
                            for item in model['stressScenarios']))
        self.at(all(
            item['expectedDisposition'] in model['closureModel']['routeDispositions']
            for item in model['stressScenarios']
        ))
        self.age(len(model['stressScenarios']), 8)
        self.age(len(model['degradationPaths']), 10)
        environment = guidance['selfBootstrappingCore'][
            'environmentAdmissionContract'
        ]
        self.ae(environment['id'], 'composed-environment-admission/v1')
        self.ae(
            environment['admissionUnit'],
            'one-bounded-claim-under-one-provenance-bound-composition-and-freshness-window',
        )
        self.ae(
            environment['snapshot']['factModelRef'],
            '#/selfBootstrappingCore/semanticModel/factModel',
        )
        self.ae(
            {item['id'] for item in environment['armKinds']},
            {
                'official-clean', 'isolated-minimal', 'current-enabled',
                'isolated-no-Accord', 'candidate-enabled-isolated',
            },
        )
        self.ae(
            [item['order'] for item in environment['isolationLadder']],
            list(range(5)),
        )
        dispositions = set(environment['admission']['dispositions'])
        self.at(all(
            item['expectedDisposition'] in dispositions
            for item in environment['stressScenarios']
        ))
        self.ai(
            'an-Accord-enabled-arm-cannot-attest-the-no-Accord-or-native-baseline',
            environment['comparisonContract']['independenceRules'],
        )
        self.ai(
            'credential-content',
            environment['snapshot']['privacyBoundary']['forbid'],
        )
        self.age(len(environment['stressScenarios']), 10)
        self.age(len(environment['cleanupAndInvalidation'][
            'invalidateOn']), 8)
        prototype = guidance['selfBootstrappingCore'][
            'productFormPrototypeDecision'
        ]
        self.ae(
            prototype['id'], 'product-form-neutral-vertical-slice/v1'
        )
        self.ae(
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
        self.ae(
            scenario_results['native-whole-loop-observed']['selected'],
            'no-added-mechanism',
        )
        self.ae(
            scenario_results[
                'effect-succeeds-but-cleanup-leaves-residue'
            ]['disposition'],
            'completion-rejected',
        )
        self.ai(
            'runtime-service-database-or-background-process',
            prototype['referenceCoreAdmission']['prohibited'],
        )
        self.af(prototype['isolation']['liveHostRead'])
        reference = guidance['selfBootstrappingCore'][
            'referenceCoreImplementation'
        ]
        self.ae(
            reference['interface'],
            'reconcile_closure(request)-to-json-serializable-decision',
        )
        self.ai(
            'route-source-kinds-and-product-forms',
            reference['openEndedInputs'],
        )
        self.ai(
            'host-and-capability-discovery', reference['replaceableAdapters']
        )
        golden = _read(root, G)
        suite = golden['suiteDesign']
        self.ae(
            suite['id'],
            'representative-and-longitudinal-self-bootstrapping-evaluation/v1',
        )
        self.ai('source-complete', suite['status'])
        self.ae(suite['attemptedTaskIds'], [
            'GT-14', 'GT-15', 'GT-16', 'GT-17', 'GT-18', 'GT-19',
            'GT-20', 'GT-21',
        ])
        self.ae(suite['unperformedTaskIds'], [])
        self.ae(
            {item['id'] for item in suite['caseTypes']},
            {'representative-case', 'longitudinal-sequence'},
        )
        dimensions = suite['fullAcceptanceVector']['dimensions']
        self.ae(len(dimensions), 10)
        self.at(all(
            isinstance(item['hardGate'], bool) and item['requires']
            for item in dimensions
        ))
        self.ae(
            set(suite['comparisonEligibility']['armKinds']),
            {item['id'] for item in environment['armKinds']},
        )
        self.ae(
            {item['taskId'] for item in suite['coverageMatrix']},
            {f'GT-{number}' for number in range(14, 22)},
        )
        new_tasks = {
            item['id']: item for item in golden['tasks']
            if item['id'] in {f'GT-{number}' for number in range(14, 22)}
        }
        self.at(all(item['evaluationDesign'] for item in new_tasks.values()))
        self.ae(
            new_tasks['GT-18']['evaluationDesign']['minimumEpisodes'], 4
        )
        self.ae(
            new_tasks['GT-18']['evaluationDesign']['episodeRoles'],
            [item['id'] for item in suite['longitudinalSequence']['episodeRoles']],
        )
        self.ae(
            new_tasks['GT-19']['evaluationDesign']['minimumEpisodes'], 4
        )
        self.ai(
            'equate-one-responsibility-replacement-with-whole-product-retirement',
            new_tasks['GT-19']['prohibited'],
        )
        self.ai(
            'replace-truncate-or-silently-append-AGENTS-CLAUDE-config-toml-or-settings-files',
            new_tasks['GT-20']['prohibited'],
        )
        self.ai(
            'preserve-concurrent-user-edits-and-stop-on-ownership-or-merge-conflict',
            new_tasks['GT-20']['required'],
        )
        self.ai(
            'use-fresh-thread-start-not-fork-for-sequential-load-relief',
            new_tasks['GT-21']['required'],
        )
        self.ai(
            'consume-supported-structured-official-facts-directly-and-normalize-only-needed-fields',
            new_tasks['GT-21']['required'],
        )
        self.ai(
            'persist-a-second-authoritative-host-capability-database-or-load-unrelated-official-surfaces',
            new_tasks['GT-21']['prohibited'],
        )
        self.ai(
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
            self.ai(needle, values)
        topology = guidance['topology']
        self.ae(set(topology), {
            'code', 'conversation', 'execution', 'independenceRule', 'rule',
            'hostVocabularyRule', 'continuityRiskRule', 'codexCloud',
        })
        self.ani('cloud-environment', topology['code'])
        self.ai('cloud-environment', topology['execution'])
        self.ai('localized labels', topology['hostVocabularyRule'].lower())
        self.ai('object, operation and inheritance semantics',
                      topology['hostVocabularyRule'])
        views = guidance['dynamicIndex']['sparseMatrixViews']
        self.ae(
            views['authority'],
            'derived-query-views-only-never-a-second-source-of-truth',
        )
        self.ai('functional family', views['semanticEquivalenceRule'])
        self.ai('not a closed taxonomy', topology['continuityRiskRule'])
        self.ai(
            'preview2-is-a-current-release-candidate',
            {item['id'] for item in guidance['retiredAsActivePremises']},
        )
        historical_notes = (
            root / 'docs/releases/v2.0.1-preview.2.md'
        ).read_text(encoding='utf-8')
        self.ai('Unreleased historical checkpoint', historical_notes)
        self.ani('claude plugin marketplace add', historical_notes)
        self.ani('The intended release is', historical_notes)
        self.ani(
            'universal-agent-runtime', constitution['productBoundary']['excludes']
        )
        self.ai(
            'dynamic-index-and-route-derivation',
            constitution['productBoundary']['includes'],
        )
        self.ae(
            constitution['resourceStewardship']['role'],
            'host-neutral-dynamic-scheduling-and-release-contract',
        )
        self.ai(
            'L8',
            {item['id'] for item in constitution['learnedFailureStandards']},
        )
        self.ae(
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
        self.at(all(value not in release_notes for value in internal_claims))
        self.at(all(
            value in release_notes
            for field in (
                'publicFiniteReleaseClaims', 'publicNotImplied',
                'publicRetainedBehaviorExclusions',
            )
            for value in acceptance['claimCeiling'][field].values()
        ))
        self.ae(
            guidance['resourceStewardship']['decision'],
            'required-as-a-host-neutral-dynamic-contract',
        )
        target = program['complexityBudget']['targets']
        self.age(
            target['maxTrackedFiles'] - report['complexity']['trackedFiles'], 3
        )
        limit = target['maxProductCodeAndTestBytes']
        percent = program['complexityBudget']['minimumProductCodeAndTestHeadroomPercent']
        self.age(limit - report['complexity']['productCodeAndTestBytes'],
                                (limit * percent + 99) // 100)
        self.anr((root / 'CONTEXT.md').read_text(encoding='utf-8'),
                            r'#/[^`\n]+/[0-9]+(?:/|`)')
        self.ani('maxControlBytes', program['complexityBudget']['targets'])
        if report['programStatus'] == 'ready':
            gate = program['releaseProcedure']['orderedGates'][1]['condition']
            self.ae(program['complexityBudget']['minimumTestCount'], 36)
            self.ai('without accessing credential or session logs', gate)
            self.ai(
                'without credential or session logs',
                acceptance['candidateVerification']['rule'],
            )
            for marker in (
                'context-isolated, outcome-bound, identity-neutral',
                'does not claim public-tag installation before the immutable tag exists',
            ):
                self.ai(marker, gate)
                self.ai(marker, acceptance['candidateVerification']['rule'])
            final_gate = program['releaseProcedure']['orderedGates'][-1]['condition']
            for marker in (
                'context-isolated clean-state evaluator replay',
                'against the public immutable tag',
            ):
                self.ai(marker, final_gate)
                self.ai(marker, acceptance['publicRelease']['rule'])
        else:
            prompt = program['goalModePrompt']
            expected_goal_states = (
                {'retired'} if program['increment']['state'] == 'completed'
                else {'prepared-host-goal-paused', 'active-in-host'}
            )
            self.ai(prompt['state'], expected_goal_states)
            mapping = program['increment']['fourSurfaceMapping']
            self.ae(
                mapping['outcomeId'],
                program['increment']['representativeOutcome']['id'],
            )
            projection = json.loads(prompt['objective'])
            self.ae(projection['schema'], 'yiyuan-accord-goal/v2')
            self.ae(projection['workspace'][-1],
                             'no-branch-worktree-or-repository-fork')
            self.ae(
                projection['route']['alignment'],
                program['processLossControl']['alignmentRule'],
            )
            ordered = projection['route']['orderedSteps']
            self.ale(
                len(prompt['objective']), 3600,
                'canonical host goal must keep headroom below the Codex limit',
            )
            self.ae(
                ordered,
                [{field: step[field] for field in (
                     'id', 'state', 'dependsOn', 'acceptanceIds'
                )} for step in mapping['process']['orderedSteps']
                 if step['state'] in {'active', 'blocked'}],
            )

    def test_provisional_gt20_revision_is_validated_while_r3_is_planned(self):
        with _provisional() as root:
            source = _read(root, GT2021_SOURCE)
            source['records']['GT-20-transactional-lifecycle-4c8bcc3'][
                'evaluatedRevision'
            ] = '0' * 40
            _write(root, GT2021_SOURCE, source)
            _rehash_input(root, GT2021_SOURCE)
            self.has(
                _errors(root),
                'frozen GT-20/21 source preimage or retained attempts drifted',
            )

        with _provisional() as root:
            program, acceptance, golden = (
                _read(root, P), _read(root, A), _read(root, G)
            )
            lifecycle = program['increment']['provisionalEvidenceLifecycle']
            r3 = _find(acceptance['criteria'], 'id', 'R3')

            def lifecycle_errors():
                return provisional_gt20_21_source_errors(
                    root, program, acceptance, golden, _reader,
                )

            def retire_to(release, observed_at):
                lifecycle.update({
                    'state': 'retired-after-recorded-public-release',
                    'targetReleaseTag': release['tag'],
                    'retiredByPublicRelease': {
                        'tag': release['tag'], 'revision': release['revision'],
                        'observedAt': observed_at,
                        'source': 'task-time-live-github-observation',
                        'releaseApi': acceptance['publicRelease']['releaseApi'],
                        'tagApi': acceptance['publicRelease']['tagApi'],
                    },
                })

            program['status'] = 'active'
            r3['assessment'] = 'planned'
            _write(root, P, program)
            _write(root, A, acceptance)
            self.has(
                _errors(root),
                'provisional GT-20/21 lifecycle transition is invalid',
            )

            program['status'] = 'ready'
            r3['assessment'] = 'verified'
            local = lifecycle_errors()
            self.at(
                _lacks(local, 'provisional GT-20', 'provisional GT-21'),
                local,
            )
            _write(root, P, program)
            _write(root, A, acceptance)
            direct_evidence = r3['evidence']
            r3['evidence'] = []
            _write(root, A, acceptance)
            self.has(
                _errors(root),
                'verified without direct evidence',
            )
            r3['evidence'] = direct_evidence
            _write(root, A, acceptance)

            old_release = program['historicalRelease']['publicReleases'][-1]
            retire_to(old_release, '2026-08-30T00:00:00Z')
            self.has(
                lifecycle_errors(),
                'provisional GT-20/21 lifecycle transition is invalid',
            )

            release = {**old_release, 'tag': 'v3.1.0', 'revision': 'c' * 40,
                       'publishedAt': '2026-09-01T00:00:00Z'}
            program['historicalRelease']['publicReleases'].append(release)
            program['historicalRelease']['recommendedPublicRelease'] = 'v3.1.0'
            acceptance['historicalRelease'] = _clone(
                program['historicalRelease']
            )
            retire_to(release, '2026-09-01T00:05:00Z')
            local = lifecycle_errors()
            self.at(
                _lacks(local, 'provisional GT-20', 'provisional GT-21'),
                local,
            )
            lifecycle['retiredByPublicRelease']['revision'] = None
            self.has(
                lifecycle_errors(),
                'provisional GT-20/21 lifecycle transition is invalid',
            )
            lifecycle['retiredByPublicRelease']['revision'] = release['revision']
            source = _read(root, GT2021_SOURCE)
            source['provisionalContract']['records'][0][
                'behaviorSubject'
            ].pop('plugins/yiyuan-accord-codex/adapter.json')
            _write(root, GT2021_SOURCE, source)
            self.has(
                lifecycle_errors(),
                'provisional GT-20 source contract record is not admitted',
            )

    def test_gt20_subjects_are_derived_from_projection_declarations(self):
        with _provisional() as root:
            golden = _read(root, G)
            task = _find(golden['tasks'], 'id', 'GT-20')
            task['behaviorSubjectFiles'].pop()
            _write(root, G, golden)
            self.has(
                _errors(root),
                'frozen GT-20 source or digest binding is invalid',
            )

    def test_provisional_source_contract_is_required_while_r3_is_planned(self):
        with _provisional() as root:
            source = _read(root, GT2021_SOURCE)
            source['provisionalContract'] = {}
            _write(root, GT2021_SOURCE, source)
            _rehash_input(root, GT2021_SOURCE)
            self.has(
                _errors(root),
                'provisional GT-20/21 source contract is invalid',
            )

    def test_provisional_gt20_21_mutations_fail_after_repository_rehash(self):
        def entry(source, task_id):
            return _find(source['provisionalContract']['records'],
                         'taskId', task_id)

        def refresh_record(source, task_id):
            contract = entry(source, task_id)
            record = source['records'][contract['recordId']]
            contract['sourceBindings'][0]['sha256'] = _digest(record)
            return contract, record

        def change_record(source, task_id, path, replacement, binding=None):
            contract = entry(source, task_id)
            record = source['records'][contract['recordId']]
            _replace(record, path, replacement)
            if binding:
                value = record
                bound_path = ('payload.liveObservation.independentPoststate'
                              if binding == 'independentPoststate' else path)
                for part in (bound_path.split('.') if isinstance(bound_path, str)
                             else bound_path):
                    value = value[part]
                contract[binding]['sha256'] = _digest(value)
            refresh_record(source, task_id)

        def mutate_null_gt20_release_observation(source):
            contract = entry(source, 'GT-20')
            record = source['records'][contract['recordId']]
            _find(record['orderedObservations'], 'phase',
                  'task-resource-release')['observed'] = None
            refresh_record(source, 'GT-20')

        claim = 'This provisional source proves candidate and release readiness.'
        contradictory_claim = (
            'This bounded source proves candidate and release readiness. '
            'It does not prove cross-host production value; candidate and release '
            'remain named exclusions.'
        )

        cases = (
            ('schema', 'provisional GT-20/21 source contract is invalid',
             lambda source: source.update(schema=2)),
            ('duplicate task entry', 'provisional GT-20/21 source record set is invalid',
             lambda source: source['provisionalContract']['records'].append(
                 _clone(entry(source, 'GT-20')))),
            ('retained order', 'provisional GT-20/21 retained attempt ledger is invalid',
             lambda source: source['provisionalContract'][
                 'retainedRecords'].__setitem__(
                     slice(0, 2),
                     list(reversed(source['provisionalContract'][
                         'retainedRecords'][:2])),
                 )),
            ('deleted failed attempt',
             'provisional GT-20/21 retained attempt ledger is invalid',
             lambda source: source['records'].pop(
                 'GT-21-simple-native-route-f5f281c')),
            ('task digest',
             'frozen GT-20/21 source preimage or retained attempts drifted',
             lambda source: entry(source, 'GT-20').update(
                 goldenTaskSha256='0' * 64)),
            ('evaluation digest',
             'frozen GT-20/21 source preimage or retained attempts drifted',
             lambda source: entry(source, 'GT-21').update(
                 evaluationContractSha256='0' * 64)),
            ('behavior subject',
             'frozen GT-20/21 source preimage or retained attempts drifted',
             lambda source: entry(source, 'GT-20')['behaviorSubject'].pop(
                 'plugins/yiyuan-accord-codex/adapter.json')),
            ('record payload behavior subject',
             'provisional GT-21 behavior subject binding is invalid',
             'GT-21', ('payload', 'behaviorSubject',
                       'yiyuan_accord/closure.py'), _DELETE),
            ('package digest',
             'frozen GT-20/21 source preimage or retained attempts drifted',
             lambda source: entry(source, 'GT-20')[
                 'projectionPackageSha256'].update(codex='0' * 64)),
            ('source binding', 'provisional GT-21 source binding is invalid',
             lambda source: entry(source, 'GT-21')['sourceBindings'][0].update(
                 sha256='0' * 64)),
            ('independent poststate', 'provisional GT-21 independent post-state is invalid',
             'GT-21', 'payload.liveObservation.independentPoststate.sourceDeleted',
             False, 'independentPoststate'),
            ('malformed poststate object',
             'provisional GT-21 independent post-state is invalid',
             'GT-21', 'payload.liveObservation', []),
            ('malformed authority object',
             'provisional GT-20 independent post-state is invalid',
             'GT-20', 'authorityAndPrivacy', []),
            ('cleanup', 'provisional GT-20 cleanup contract is invalid',
             lambda source: entry(source, 'GT-20')['cleanup'].update(
                 taskOwnedResidueCount=1)),
            ('claim ceiling', 'provisional GT-21 claim ceiling is invalid',
             'GT-21', 'payload.decision.claimLimit', claim, 'claimCeiling'),
            ('contradictory synchronized claim',
             'provisional GT-21 claim ceiling is invalid',
             'GT-21', 'payload.decision.claimLimit', contradictory_claim,
             'claimCeiling'),
            ('malformed decision object',
             'provisional GT-21 claim ceiling is invalid',
             'GT-21', 'payload.decision', []),
            ('null GT-21 observer',
             'provisional GT-21 independent post-state is invalid',
             'GT-21', 'payload.liveObservation.independentPoststate.observer',
             None, 'independentPoststate'),
            ('null GT-20 release observation',
             'provisional GT-20 independent post-state is invalid',
             mutate_null_gt20_release_observation),
        )
        with _provisional() as root:
            original = _read(root, GT2021_SOURCE)
            _write(root, GT2021_SOURCE, original)
            _rehash_input(root, GT2021_SOURCE)
            self.at(
                _lacks(_errors(root), 'provisional GT-20', 'provisional GT-21'),
                'the unmodified provisional contract must validate while R3 is planned',
            )
            for name, fragment, *mutation in cases:
                with self.subTest(name=name):
                    source = _clone(original)
                    (mutation[0](source) if len(mutation) == 1
                     else change_record(source, *mutation))
                    _write(root, GT2021_SOURCE, source)
                    _rehash_input(root, GT2021_SOURCE)
                    self.has(_errors(root), fragment)

        with _provisional() as root:
            source, golden, acceptance = (
                _read(root, GT2021_SOURCE),
                _read(root, G),
                _read(root, A),
            )
            task = _find(golden['tasks'], 'id', 'GT-21')
            task['prompt'] += ' synchronized semantic expansion'
            _write(root, G, golden)
            contract = entry(source, 'GT-21')
            contract['goldenTaskSha256'] = _digest(task)
            criterion = _find(acceptance['criteria'], 'id', 'R3')
            criterion['statement'] += ' synchronized semantic expansion'
            _write(root, A, acceptance)
            contract['evaluationContractSha256'] = _contract_sha(
                acceptance, golden
            )
            _write(root, GT2021_SOURCE, source)
            _rehash_input(root, GT2021_SOURCE)
            self.has(
                _errors(root),
                'provisional GT-21 source Golden Task digest is not admitted',
                'provisional GT-21 source evaluation contract digest is not admitted',
            )

    def test_frozen_gt20_21_promotion_is_exact_and_fail_closed(self):
        def errors(root):
            return frozen_gt20_21_promotion_errors(
                root, _read(root, P), _read(root, A), _read(root, G), _reader,
            )

        cases = (
            ('subject drift', ('frozenPromotion', 'promotedRecords', 0,
                               'behaviorSubject'), {}),
            ('record drift', ('records',
                              'GT-20-transactional-lifecycle-4c8bcc3',
                              'claimLimit'), 'drift'),
            ('marker omission', ('frozenPromotion', 'promotedRecords', 0,
                                 'cleanupBinding', 'requiredMarkers'), {}),
            ('claim expansion', ('frozenPromotion', 'claimCeiling',
                                 'liveBehaviorClaimed'), True),
            ('current digest', ('frozenPromotion',
                                'currentEvaluationContractSha256'), '0' * 64),
            ('promoted revision drift', ('frozenPromotion',
                                         'promotedRecords', 1,
                                         'evaluatedRevision'), '0' * 40),
            ('component revision collapsed', ('frozenPromotion',
                                               'promotedRecords', 1,
                                               'selectedRecordSet', 'components',
                                               0, 'evaluatedRevision'),
             'cf1d8c9e57741ed5c353bb630ca8dded7bd225b9'),
            ('component revision drift', ('frozenPromotion',
                                           'promotedRecords', 1,
                                           'selectedRecordSet', 'components',
                                           1, 'evaluatedRevision'), '0' * 40),
            ('composite omission', ('frozenPromotion', 'promotedRecords', 1,
                                    'selectedRecordSet', 'components'), []),
            ('composite order', ('frozenPromotion', 'promotedRecords', 1,
                                 'selectedRecordSet', 'components', 0,
                                 'order'), 3),
            ('composite failed substitute', ('frozenPromotion',
                                              'promotedRecords', 1,
                                              'selectedRecordSet', 'components',
                                              0, 'recordId'),
             'GT-21-simple-native-route-f5f281c'),
            ('non-ancestor', ('frozenPromotion',
                              'sourceBoundAncestorRevision'), '0' * 40),
            ('live masquerade', ('frozenPromotion', 'schema'),
             'direct-host-material-events-v1'),
            ('unselected attempt', ('frozenPromotion', 'nonPromotedAttempts',
                                    0, 'disposition'), 'promoted'),
        )
        with _provisional() as root:
            original = _read(root, GT2021_SOURCE)
            self.ae(errors(root), [])
            for name, path, replacement in cases:
                with self.subTest(name=name):
                    source = _clone(original)
                    _replace(source, path, replacement)
                    _write(root, GT2021_SOURCE, source)
                    self.at(errors(root))
            _write(root, GT2021_SOURCE, original)
            for field, value in (
                ('observedAt', '2026-08-30T00:00:00Z'),
                ('hostIdentity', {'hostProduct': 'gpt-9'}),
                ('evaluatedRevision',
                 '3878968d459adba57792c390eb277876028b0012'),
            ):
                observation = _read(ROOT, FROZEN_OBS[0])
                observation[field] = value
                _write(root, FROZEN_OBS[0], observation)
                self.at(errors(root))

    def test_frozen_promotion_maps_only_exact_observations_to_representative(self):
        with _provisional() as root:
            locator = FROZEN_OBS[0]
            item = {
                'locator': locator,
                'sha256': _file_sha(root, locator),
                'claim': 'Exact frozen promotion lane fixture.',
            }
            promo_errors = frozen_gt20_21_promotion_errors(
                root, _read(root, P), _read(root, A), _read(root, G),
                _reader,
            )
            errors = []
            observation = _validate_evidence_item(
                root, item, 'promotion lane', errors,
                {'representative-behavior'},
                FROZEN_GT20_21_REPRESENTATIVE_LANES
                if not promo_errors else {},
            )
            self.ae(promo_errors, [])
            self.ae(errors, [])
            self.ae(
                observation['evidenceClass'], 'representative-behavior'
            )

            raw = _read(root, locator)
            raw['observedAt'] = '2026-08-30T00:00:00Z'
            _write(root, locator, raw)
            item['sha256'] = _file_sha(root, locator)
            promo_errors = frozen_gt20_21_promotion_errors(
                root, _read(root, P), _read(root, A), _read(root, G),
                _reader,
            )
            errors = []
            observation = _validate_evidence_item(
                root, item, 'promotion lane', errors,
                {'representative-behavior'}, {},
            )
            self.at(promo_errors)
            self.ae(
                observation['evidenceClass'],
                'frozen-source-metadata-promotion',
            )
            self.has(errors, 'evidenceClass is not required')

    def test_reacceptance_projects_current_stage_without_model_binding(self):
        program = _read(ROOT, P)
        for stages in (program['increment']['fourSurfaceMapping']['process']['orderedSteps'],
                       program['increment']['workItems'][0]['closeoutSequence']):
            self.ae([step['state'] for step in stages[-2:]],
                             ['completed', 'completed'])
        active = '\n'.join((ROOT / name).read_text(encoding='utf-8') for name in (
            'README.md', 'README.zh-CN.md', P, 'product/reshaping-guidance.json',
            'docs/architecture.md', 'docs/operations/CONTINUATION.md',
            'docs/releases/v3.1.0.md'))
        self.an(re.search(
            r'\b(?:gpt|gemini)-\d|claude-(?:\d|opus|sonnet|haiku)|deepseek-[vr]\d|'
            r'run gt-20 next|whole-system reacceptance (?:is active|remains pending|'
            r'is now the earliest open boundary)|(keep the selected current component set) '
            r'and \1',
            active, re.IGNORECASE))

    def test_reference_core_is_policy_driven_and_fail_closed(self):
        minimal, native = 'minimal-composition', 'native-no-add'
        controller, sense = 'persistent-controller', 'sense-environment'
        reconcile = reconcile_closure
        responsibilities = [
            sense, 'bind-authority', 'preserve-correction',
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

        def make_route(identity, source, forms, supplies, modes, facts=None,
                       route_coherence=None, lifecycle=1):
            return {
                'id': identity, 'sourceKind': source, 'forms': forms,
                'supplies': supplies, 'responsibilityModes': modes,
                'facts': dict(compliance) if facts is None else facts,
                'coherence': route_coherence or {},
                'lifecycle': ({item: lifecycle for item in dimensions}
                              if isinstance(lifecycle, int) else lifecycle),
            }

        def fixture(*, native_ok=False, residue=False):
            native_supplies = [
                item for item in responsibilities
                if native_ok or item != 'preserve-correction'
            ]
            routes = [
                make_route(native, 'no-added', [], native_supplies,
                      {item: 'agent-native' for item in native_supplies}, lifecycle=0),
                make_route('current-plugin', 'maintained', ['plugin'],
                      [sense, 'bind-authority'], {
                          sense: 'accord-contained',
                          'bind-authority': 'accord-agent-composed',
                      }, {**compliance, 'independent-consequence-verifier': 'unknown'}),
                make_route(minimal, 'composition', [
                    'native-executor', 'task-scoped-handoff',
                    'independent-effect-probe'], list(responsibilities), dict(zip(
                        responsibilities, ('accord-contained', 'accord-agent-composed',
                        'accord-agent-composed', 'agent-native',
                        'accord-agent-composed', 'accord-agent-composed'))),
                      route_coherence=dict(coherence)),
                make_route(controller, 'authored', [controller],
                      list(responsibilities), {item: 'accord-contained'
                      for item in responsibilities}, lifecycle=dict(zip(
                          dimensions, (2, 3, 4, 3, 4, 4)))),
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
            selected = native if native_ok else minimal
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
            if not native_ok:
                events.append({
                    'kind': 'experiment-evaluated',
                    'baselineRouteId': selected,
                    'candidateRouteId': controller,
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
                    'evidence': evidence(controller),
                })
                events.append({
                    'kind': 'experiment-poststate',
                    'baselineRouteId': selected,
                    'candidateRouteId': controller,
                    'disposition': 'rollback-complete',
                    'state': 'observed',
                    'independent': 'observed',
                    'evidence': evidence(controller),
                })
            events.append({
                'kind': 'resource-poststate', 'routeId': selected,
                'releasedResources': (
                    [] if native_ok or residue else ['task-scoped-handoff']
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

        def require_route_fact(request, fact_id, observed_route_ids):
            request['policy']['requiredRouteFacts'].append(fact_id)
            for route in request['routes']:
                value = (
                    'observed' if route['id'] in observed_route_ids else 'unknown'
                )
                route['facts'][fact_id] = value
                request['environment']['observation']['stateBindings'].append(
                    state_binding(
                        f'route.{route["id"]}.{fact_id}', 'route-fact',
                        route['id'], fact_id, value,
                    )
                )

        def allocate_evidence_acquisition(request, route_id):
            responsibility = 'acquire-current-decision-evidence'
            request['outcome']['responsibilities'].append(responsibility)
            route = _find(request['routes'], 'id', route_id)
            route['supplies'].append(responsibility)
            route['responsibilityModes'][responsibility] = (
                'accord-agent-composed'
            )

        def evidence_case(route_id, fact_id, observed):
            request = fixture()
            allocate_evidence_acquisition(request, route_id)
            require_route_fact(request, fact_id, observed)
            return reconcile(request)

        def hold(request):
            result = reconcile(request)
            self.at(result['valid'], result['errors'])
            self.ae(result['disposition'], 'hold-unknown')
            return result

        def reject(request):
            result = reconcile(request)
            self.af(result['valid'])
            self.ae(result['disposition'], 'reject')
            return result

        def incomplete(result, *codes):
            self.af(result['lifecycle']['completionAllowed'])
            failures = {item['code'] for item in result['lifecycle'][
                'completionFailures']}
            for code in codes:
                self.ai(code, failures)

        decision = reconcile(fixture())
        self.at(decision['valid'], decision['errors'])
        self.ae(decision['selectedRouteId'], minimal)
        self.ae(decision['disposition'], 'admit')
        self.at(decision['environmentObservation']['current'])
        self.ae(
            _find(decision['assessments'], 'routeId', minimal)[
                'responsibilityModes'],
            {
                sense: 'accord-contained',
                'bind-authority': 'accord-agent-composed',
                'preserve-correction': 'accord-agent-composed',
                'execute-outcome': 'agent-native',
                'observe-consequence': 'accord-agent-composed',
                'release-task-residue': 'accord-agent-composed',
            },
        )
        self.at(decision['lifecycle']['completionAllowed'])
        self.ae(
            decision['lifecycle']['experimentResults'][0]['decision'],
            'discard-and-rollback',
        )
        self.at(
            decision['lifecycle']['experimentResults'][0]['poststate'][
                'accepted']
        )
        self.af(_find(
            decision['assessments'], 'routeId', 'current-plugin')['admitted'])

        native_decision = reconcile(fixture(native_ok=True))
        self.ae(native_decision['selectedRouteId'], native)
        self.ae(native_decision['disposition'], 'no-op')
        self.at(native_decision['lifecycle']['completionAllowed'])
        self.ani(
            'acquire-current-decision-evidence',
            fixture(native_ok=True)['outcome']['responsibilities'],
        )

        for route_id, fact, observed, selected, disposition in (
            (minimal,
             'consequential-evidence-not-public-lead-only',
             {minimal}, minimal, 'admit'),
            (minimal,
             'consequential-evidence-not-public-lead-only',
             set(), None, 'hold-unknown'),
            (controller,
             'bounded-search-and-authorship-authority',
             {controller}, controller, 'admit'),
        ):
            decision = evidence_case(route_id, fact, observed)
            self.ae(decision['selectedRouteId'], selected)
            self.ae(decision['disposition'], disposition)

        retirement_facts = [
            'within-human-authority',
            'current-successor-capability-observed',
            'same-responsibility-overlap-derived',
            'retired-route-prestate',
            'task-defined-observation-window-complete',
            'available-rollback', 'fallback-preserved',
        ]
        dynamic_retirement = fixture(native_ok=True)
        dynamic_retirement['policy'].update({
            'requiredRetirementFacts': ['fallback-preserved'],
            'requiredRetirementAllocations': [{
                'routeId': 'current-plugin',
                'responsibilities': [sense],
            }],
        })
        dynamic_retirement['events'].append({
            'kind': 'responsibility-allocation-retired',
            'routeId': 'current-plugin',
            'replacementRouteId': native,
            'responsibilities': [sense],
            'replacementEvidence': evidence(native),
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
        retirement = reconcile(dynamic_retirement)
        retirement_result = retirement['lifecycle']['retirementResults'][0]
        self.at(retirement_result['accepted'])
        self.ae(
            retirement_result['disposition'], 'retired-with-recheck'
        )
        self.ae(
            retirement_result['replacementEvidenceBinding']['subjectRef'],
            native,
        )
        self.ae(retirement['lifecycle']['retiredAllocations'], [{
            'routeId': 'current-plugin',
            'replacementRouteId': native,
            'responsibilities': [sense],
            'recheckTriggers': [
                'environment-composition-change',
                'replacement-effect-drift',
                'evidence-expiry',
            ],
        }])
        self.at(retirement['lifecycle']['completionAllowed'])

        retirement_failure = 'completion:retirement:current-plugin:sense-environment'
        for name, mutate, has_result, failures in (
            ('stale', lambda value: _replace(value, ('events', -1, 'preconditions',
             'task-defined-observation-window-complete'), 'unknown'), True,
             (retirement_failure,)),
            ('unproved', lambda value: _replace(value, ('events', -1,
             'preconditions', 'current-successor-capability-observed'), 'unknown'),
             True, ()),
            ('missing', lambda value: value['events'].pop(), False,
             (retirement_failure,)),
            ('premature', lambda value: value['events'].insert(
                0, value['events'].pop()), True, ()),
        ):
            request = _clone(dynamic_retirement)
            mutate(request)
            decision = reconcile(request)
            with self.subTest(retirement=name):
                if has_result:
                    self.af(decision['lifecycle'][
                        'retirementResults'][0]['accepted'])
                incomplete(decision, *failures)

        no_experiment_policy = fixture(native_ok=True)
        no_experiment_policy['policy']['requiredExperimentFacts'] = []
        no_experiment_policy['policy']['experimentDimensions'] = []
        no_experiment_policy['policy']['requiredCompletionFacts'] = []
        no_experiment = reconcile(no_experiment_policy)
        self.at(no_experiment['valid'], no_experiment['errors'])
        self.at(no_experiment['lifecycle']['completionAllowed'])

        for name, native_case, changes in (
            ('no-environment', True, ((('policy', 'requiredEnvironmentFacts'), []),
                                      (('environment', 'facts'), {}))),
            ('unknown', False, ((('environment', 'facts', 'provenance-bound'),
                                 'unknown'),)),
            ('unbound-value', False, ((('environment', 'observation',
                'stateBindings', 0, 'value'), 'not-observed'),)),
            ('unbound-target', False, ((('environment', 'observation',
                'stateBindings', 0, 'factId'), 'unrelated-fact'),)),
        ):
            request = fixture(native_ok=native_case)
            for path, replacement in changes:
                _replace(request, path, replacement)
            with self.subTest(hold_case=name):
                self.an(hold(request)['selectedRouteId'])

        for name, mutate in (
            ('no-availability', lambda value: (
                value['policy'].__setitem__('requiredRouteFacts', []),
                [route['facts'].pop('available', None) for route in value['routes']])),
            ('dynamic-policy', lambda value: value['policy'][
                'requiredRouteFacts'].append('fit-for-current-context')),
        ):
            request = fixture(native_ok=name == 'no-availability')
            mutate(request)
            with self.subTest(no_admitted_route=name):
                self.at(all(not item['admitted']
                                    for item in hold(request)['assessments']))

        for missing_coherence_fact in coherence:
            with self.subTest(missing_coherence_fact=missing_coherence_fact):
                missing_coherence = fixture()
                missing_coherence['policy']['requiredCoherenceFacts'] = []
                missing_coherence['routes'][2]['coherence'].pop(
                    missing_coherence_fact
                )
                decision = reconcile(missing_coherence)
                self.af(decision['valid'])

        residual = reconcile(fixture(residue=True))
        incomplete(residual, 'completion:task-residue')

        injection_only = fixture()
        injection_only['events'] = [
            event for event in injection_only['events']
            if event.get('factId') not in {'execution', 'consequence'}
        ]
        injection_only['events'].insert(0, {
            'kind': 'fact-observed', 'routeId': minimal,
            'factId': 'context-injection', 'state': 'observed',
            'independent': 'observed',
            'evidence': evidence(minimal),
        })
        injection_decision = reconcile(injection_only)
        self.at(injection_decision['valid'])
        incomplete(injection_decision, *{
            'completion:execution', 'completion:consequence',
        })

        for corrected_fact in (
            'within-human-authority', 'compliant', 'available',
        ):
            corrected = fixture()
            corrected['events'].append({
                'kind': 'fact-observed',
                'routeId': minimal,
                'factId': corrected_fact,
                'state': 'not-observed',
                'independent': 'observed',
                'evidence': evidence(minimal),
            })
            corrected_decision = reconcile(corrected)
            with self.subTest(corrected_fact=corrected_fact):
                incomplete(corrected_decision,
                           f'route-poststate:{corrected_fact}')

        rollback_unverified = fixture()
        rollback_unverified['events'] = [
            event for event in rollback_unverified['events']
            if event['kind'] != 'experiment-poststate'
        ]
        rollback_decision = reconcile(rollback_unverified)
        incomplete(rollback_decision,
                   'completion:experiment-poststate:persistent-controller')

        for field, value in (
            ('observerRef', minimal),
            ('subjectRef', native),
        ):
            request = fixture()
            request['events'][1]['evidence'][field] = value
            with self.subTest(invalid_evidence=field):
                self.af(reconcile(request)['valid'])

        cross_boundary = fixture()
        cross_boundary['events'][3]['evidence']['boundaryRef'] = (
            'task-owned-process:different-boundary'
        )
        cross_boundary_decision = reconcile(cross_boundary)
        incomplete(cross_boundary_decision)
        self.af(
            cross_boundary_decision['lifecycle']['experimentResults'][0][
                'poststate']['accepted']
        )

        for name, field, replacement in (
            ('signal-only', 'stateBindings', []),
            ('composition-mismatch', 'compositionKey', 'synthetic:different'),
            ('future', 'capturedAt', '2026-08-29T00:00:02Z'),
            ('expired', 'validUntil', '2026-08-29T00:00:00Z'),
            ('invalidated', 'invalidatedBy', ['user-intervention']),
        ):
            request = fixture(native_ok=True)
            request['environment']['observation'][field] = replacement
            held = hold(request)
            with self.subTest(environment_observation=name):
                self.an(held['selectedRouteId'])
                self.af(held['environmentObservation']['current'])

        refreshed = fixture(native_ok=True)
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
        refreshed_decision = reconcile(refreshed)
        self.ae(refreshed_decision['selectedRouteId'], native)
        self.ae(
            refreshed_decision['environmentObservation']['generation'], 2
        )

        conflicting_writer = fixture()
        duplicate = dict(conflicting_writer['environment']['observation'][
            'stateBindings'][0], writer='another-writer')
        conflicting_writer['environment']['observation'][
            'stateBindings'].append(duplicate)
        conflict = hold(conflicting_writer)
        self.af(conflict['environmentObservation']['current'])

        signal_only = fixture(native_ok=True)
        signal_only['environment']['observation']['invalidatedBy'] = [
            'user-intervention'
        ]
        signal_only['environment']['lastSafeAllocation'] = {
            'routeId': native,
            'responsibilityModes': {
                item: 'agent-native' for item in responsibilities
            },
            'observationId': 'synthetic:p4:observation:1',
            'observationGeneration': 1,
            'evidence': evidence(native),
        }
        preserved = reconcile(signal_only)
        self.an(preserved['selectedRouteId'])
        self.ae(
            preserved['preservedAllocation']['routeId'], native
        )
        self.at(
            preserved['environmentObservation']['preservedLastSafe']
        )

        reject_cases = (
            (None, (('schema',), 'invented')),
            (None, (('environment', 'observation', 'stateBindings', 0, 'field'), 'Credential.token')),
            (None, (('environment', 'observation', 'generation'), 2)),
            (None, (('environment', 'observation', 'stateBindings', 0, 'unavailableSources'), [])),
            (None, (('routes', 2, 'responsibilityModes', 'preserve-correction'), _DELETE)),
            (None, (('routes', 2, 'responsibilityModes', 'preserve-correction'), 'plugin-does-everything')),
            (None, (('routes', 0, 'forms'), None)),
            (None, (('policy', 'comparisonDimensions'), None)),
            (None, (('events', 0, 'routeId'), [])),
            (None, (('events', 2, 'candidateRouteId'), minimal)),
            (None, (('events', -1, 'residualTaskResources'),
                    ['task-scoped-handoff']),
             (('events', -1, 'releasedResources'), ['task-scoped-handoff'])),
            (None, (('events', -1), {
                'kind': 'fact-observed', 'routeId': minimal,
                'factId': 'cleanup-poststate', 'state': 'observed',
                'independent': 'observed',
                'evidence': evidence(minimal),
            })),
            ('r', (('events', -1, 'recheckTriggers'), [])),
            ('r', (('events', -1, 'responsibilities'), lambda items: items + ['execute-outcome'])),
            ('r', (('events', -1, 'replacementEvidence'), evidence('current-plugin'))),
            ('n', (('policy', 'requiredRetirementAllocations'), [{
                'routeId': 'invented-route',
                'responsibilities': [sense],
            }])),
            ('r', (('policy', 'requiredRetirementAllocations'), _DELETE),
             (('policy', 'requiredRetirementRouteIds'), ['current-plugin'])),
        )
        for base, *changes in reject_cases:
            case = (_clone(dynamic_retirement) if base == 'r'
                    else fixture(native_ok=base == 'n'))
            for path, replacement in changes:
                _replace(case, path, replacement)
            with self.subTest(case=case):
                reject(case)

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
            (G, 'bound reviewable GT-13 workspace', lambda v: _find(
                v['tasks'], 'id', 'GT-13').update(workspaceContract=None)),
            (G, 'bound reviewable GT-13 workspace', lambda v: _find(
                v['tasks'], 'id', 'GT-13').update(prompt=(
                'Do not use a reviewable, explicitly bound workspace; '
                'use an ephemeral clone.'
            ))),
            (G, 'golden tasks do not cover contract ids', lambda v: [
                task['mapsTo'].remove('L8')
                for task in v['tasks'] if 'L8' in task['mapsTo']
            ]),
            (A, 'representative post-session binding contracts', lambda v: v[
                'representativeBehaviorPolicy'].update(postSessionBindingContracts=[])),
            (A, 'representative evaluation contract history is invalid', lambda v: v[
                'representativeBehaviorPolicy']['evaluationContractHistory'][-1][
                    'preservedTaskIds'].append('GT-19')),
            (A, 'acceptance.claimCeiling is invalid', lambda v: v[
                'claimCeiling'].pop('publicFiniteReleaseClaims')),
            (A, 'finite-release evidence lanes', lambda v: (
                v['evidenceLanes']['continuingAfterRelease'].append(
                    v['evidenceLanes']['requiredForFiniteRelease'].pop())))
        )
        for case in cases:
            with self.subTest(case=case[:2]):
                self.rejected(*case)

        for field, replacement in (
            ('inputs', ['single-feature-roadmap']),
            ('candidateClasses', ['frozen-roadmap']),
            ('rule', 'Persist one exhaustive automatic roadmap as authority.'),
            ('storageRule', 'Persist every unpromoted horizon item in a permanent registry.'),
        ):
            with self.subTest(evolution_horizon=field), _fixture() as root:
                guidance = _read(root, 'product/reshaping-guidance.json')
                guidance['adaptiveSystem']['evolutionHorizon'][field] = replacement
                _write(root, 'product/reshaping-guidance.json', guidance)
                _rehash_input(root, 'product/reshaping-guidance.json')
                self.has(_errors(root),
                                'reshaping guidance evolution horizon contract is invalid')

    def test_projection_package_and_admission_are_fail_closed(self):
        def json_change(root, locator, mutate):
            value = _read(root, locator)
            mutate(value)
            _write(root, locator, value)

        def append_bytes(root, locator, suffix):
            path = root / locator
            path.write_bytes(path.read_bytes() + suffix)

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
            self.has(host_check(root, 'codex')['errors'], 'program projection shape',
                            'package digest', 'unsupported fields', 'Skill frontmatter identity',
                            'AVAILABLE/ON_INSTALL', 'interface contract',
                            'Skill omits marker Resource stewardship')
        with _fixture() as root:
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
                    projection['metadataFiles'], projection['legalFiles'], [],
                    projection['mechanismFiles'],
                )
            self.an(digest)
            self.has(errors, 'package declared file is unsafe')
        with _fixture() as root:
            projection = _read(root, P)['hostProjections'][0]
            target = root / projection['skill']
            with target.open('wb') as stream:
                stream.truncate(2_000_000)
            with _deny_path('read_text', target), _deny_path('read_bytes', target):
                errors = host_check(root, 'codex')['errors']
            self.has(errors, 'Skill exceeds budget', 'package identity is unavailable')

        drift_cases = (
            ('codex', 0, 'manifest', lambda root, p: json_change(
                root, p['manifest'], lambda m: (
                    m['author'].update(name='collective'),
                    m['interface'].__setitem__('composerIcon', './assets/other.png'))),
             ('manifest author is not canonical',
              'manifest interface contract is invalid',
              'package declared file is unsafe')),
            ('codex', 0, 'icon', lambda root, _: append_bytes(
                root, 'plugins/yiyuan-accord-codex/assets/yiyuan-nexus-mark.png',
                b'tampered'), ('package digest is not approved by program',)),
            ('claude-code', 1, 'manifest-marketplace', lambda root, p: (
                json_change(root, p['manifest'], lambda m: m.update(
                    displayName='YIYUAN Accord for Claude Code')),
                json_change(root, p['marketplace'], lambda m: m['plugins'][0].update(
                    source='./plugins/wrong', version='2.0.1-preview.1'))),
             ('manifest displayName is invalid', 'marketplace source is invalid',
              'marketplace presentation is invalid',
              'package digest is not approved by program')),
            ('claude-code', 1, 'description', lambda root, p: json_change(
                root, p['marketplace'], lambda m: m['plugins'][0].update(
                    description='Drifted description')),
             ('marketplace presentation is invalid',)),
            *((adapter, index, 'hook', lambda root, p: json_change(
                root, p['mechanismFiles'][0], lambda h: h['hooks'][
                    'SessionStart'][0]['hooks'][0].update(command='echo drifted')),
               ('activation mechanism contract is invalid',
                'package digest is not approved by program'))
              for adapter, index in (('codex', 0), ('claude-code', 1))),
            ('codex', 0, 'missing-legal-declaration', lambda root, _: json_change(
                root, P, lambda p: p['hostProjections'][0].pop('legalFiles')),
             ('program projection shape is invalid',
              'legal file declaration is invalid',
              'package contains undeclared files',
              'package digest is not approved by program')),
            ('codex', 0, 'legal-declaration-order', lambda root, p: json_change(
                root, P, lambda program: program['hostProjections'][0].update(
                    legalFiles=list(reversed(p['legalFiles'])))),
             ('legal file declaration is invalid',)),
            ('codex', 0, 'package-license', lambda root, p: append_bytes(
                root, p['legalFiles'][0], b'changed'),
             ('LICENSE differs from repository authority',
              'package digest is not approved by program')),
            ('codex', 0, 'package-notice-extra-restriction',
             lambda root, p: append_bytes(
                 root, p['legalFiles'][1],
                 b'Additional commercial restriction.\n'),
             ('NOTICE differs from repository authority',
              'package digest is not approved by program')),
            ('claude-code', 1, 'missing-package-notice',
             lambda root, p: (root / p['legalFiles'][1]).unlink(),
             ('package declared file is unsafe',
              'package digest is not approved by program')),
        )
        for adapter, index, name, mutate, fragments in drift_cases:
            with self.subTest(adapter=adapter, mutation=name), _fixture() as root:
                projection = _read(root, P)['hostProjections'][index]
                mutate(root, projection)
                self.has(host_check(root, adapter)['errors'], *fragments)

        with _fixture() as root:
            program = _read(root, P)
            projection = program['hostProjections'][0]
            hook_path = root / projection['mechanismFiles'][0]
            raw = hook_path.read_text(encoding='utf-8')
            hook_path.write_text(
                raw.replace('"hooks": {', '"hooks": {},\n  "hooks": {', 1),
                encoding='utf-8',
            )
            self.has(
                host_check(root, 'codex')['errors'],
                'activation mechanism is unreadable',
                'package digest is not approved by program',
            )

        for suffix in (' & extra', '; extra', ' $(extra)', ' `extra`', ' %PATH%'):
            with self.subTest(shell_suffix=suffix), _fixture() as root:
                program = _read(root, P)
                program['hostProjections'][0]['activationContext'] += suffix
                _write(root, P, program)
                self.has(
                    host_check(root, 'codex')['errors'],
                    'activation context is invalid',
                )

        for locator, record_id, mutate in (
            (OBS11, 'GT-11', lambda record: _replace(
                record, 'payload.projectionExposure.mechanismSha256', '0' * 64)),
            (OBS13, 'GT-13', lambda record: _replace(
                record, ('amendments', 0), None)),
            (OBS13, 'GT-13', lambda record: record['amendments'].append({
                **record['amendments'][0], 'priorGoldenTaskSha256': '1' * 64})),
        ):
            with self.subTest(source_mutation=record_id), _fixture() as root:
                observation, bundle = _read(root, locator), _read(root, SRC310)
                mutate(bundle['records'][record_id])
                _bind_source(root, locator, bundle, observation)
                self.has(_observe(root, locator)[0],
                                'sourceEvidence[0] is invalid')

    def test_snapshot_v1_legal_files_are_backward_compatible_and_bound(self):
        current = _read(ROOT, P)
        predecessor = current['increment']['closeoutSnapshot'][
            'predecessorSnapshotRef'
        ].split(':', 1)[0]
        constitution, legacy_program, *_ = _snapshot_documents(ROOT, predecessor)
        self.ae(
            _snapshot_v1_projection_shape_errors(legacy_program, constitution),
            [],
        )
        extended_program = _clone(legacy_program)
        for projection in extended_program['hostProjections']:
            package_root = f"plugins/{projection['packageId']}"
            projection['legalFiles'] = [
                f'{package_root}/LICENSE', f'{package_root}/NOTICE',
            ]
        self.ae(
            _snapshot_v1_projection_shape_errors(extended_program, constitution),
            [],
        )
        invalid_program = _clone(extended_program)
        invalid_program['hostProjections'][0]['legalFiles'].reverse()
        self.has(
            _snapshot_v1_projection_shape_errors(invalid_program, constitution),
            'hostProjections[0].legalFiles is invalid',
        )

        with _indexed() as root:
            revision = _git(root, 'rev-parse', 'HEAD', text=True).strip()
            constitution, program, *_ = _snapshot_documents(root, revision)
            self.at(
                all('legalFiles' in item for item in program['hostProjections']),
                'current revision must use the extended projection shape',
            )
            self.ae(
                _snapshot_v1_projection_package_errors(
                    root, program, constitution, revision,
                ),
                [],
            )
            locator = program['hostProjections'][0]['legalFiles'][0]
            path = root / locator
            path.write_bytes(path.read_bytes() + b'changed')
            _git(root, 'add', locator)
            _git(
                root, '-c', 'user.name=Accord Fixture',
                '-c', 'user.email=fixture@example.invalid',
                'commit', '--quiet', '-m', 'tampered legal projection',
            )
            tampered_revision = _git(
                root, 'rev-parse', 'HEAD', text=True,
            ).strip()
            constitution, program, *_ = _snapshot_documents(
                root, tampered_revision,
            )
            self.has(
                _snapshot_v1_projection_package_errors(
                    root, program, constitution, tampered_revision,
                ),
                'revision LICENSE differs from repository authority',
                'revision package digest mismatch',
            )

    def test_snapshot_v2_reopens_only_the_invalidated_package_boundary(self):
        program, acceptance = _read(ROOT, P), _read(ROOT, A)
        node = program['increment']['closeoutSnapshot']
        self.ae(_snapshot_v2_node_errors(program, acceptance), [])
        predecessor = node['predecessorSnapshotRef'].split(':', 1)[0]
        _, prior_program, *_ = _snapshot_documents(ROOT, predecessor)
        prior = prior_program['increment']['closeoutSnapshot']
        self.ae(_snapshot_v2_transition_errors(node, prior), [])

        changed = _clone(program)
        changed_node = changed['increment']['closeoutSnapshot']
        changed_node['replay']['preservedTaskIds'] = []
        self.has(
            _snapshot_v2_node_errors(changed, acceptance),
            'revision-bound v2 replay boundary is invalid',
        )

        self.ae(prior['state'], 'reopened')
        self.ae(node['state'], 'closed')
        self.has(
            _snapshot_v2_transition_errors(node, node),
            'revision-bound v2 close transition is invalid',
        )

    def test_exact_package_evidence_fails_closed_on_drift(self):
        with _indexed() as root:
            program = _read(root, P)
            lifecycle = program['increment']['exactPackageEvidenceLifecycle']
            locator = lifecycle['evidence']['locator']
            record = _read(root, locator)
            def validate(value):
                _write(root, locator, value)
                lifecycle['evidence']['sha256'] = _file_sha(root, locator)
                errors = []
                _validate_exact_package_evidence_lifecycle(root, program, errors)
                return errors
            self.ae(validate(record), [])
            for mutate in (
                lambda value: value['commands'][0].__setitem__('exitCode', 1),
                lambda value: value.__setitem__('behaviorSubject', [{'x': 1}]),
                lambda value: value['postState'].__setitem__('codexCacheFiles', [{}]),
                lambda value: value.__setitem__('claimLimit', 'production verified'),
            ):
                changed = _clone(record)
                mutate(changed)
                self.has(validate(changed), 'exact package evidence record contract is invalid')
            self.ae(validate(record), [])
            lifecycle['evidence']['evaluatedRevision'] = '0' * 40
            self.has(validate(record), 'exact package evidence verified state is invalid')
            lifecycle['evidence']['evaluatedRevision'] = record['evaluatedRevision']
            subject = next(iter(record['behaviorSubject']))
            (root / subject).write_bytes((root / subject).read_bytes() + b'drift')
            self.has(validate(record), 'exact package evidence subject binding is invalid')

    def test_projection_evidence_rejects_drift_and_relocation(self):
        current = host_check(ROOT, 'codex')['details']
        observation = _projection_identity(current)
        presentation_drift = dict(
            observation,
            manifestSha256='0' * 64,
            packageSha256='0' * 64,
        )
        self.ae(
            projection_observation_errors(
                presentation_drift, current, 'presentation-only', 'codex'
            ),
            [],
        )
        changed_locator = _clone(current)
        changed_locator['skill'] = 'plugins/changed/SKILL.md'
        self.has(
            projection_observation_errors(
                observation, changed_locator, 'behavior-bearing', 'codex'
            ),
            'skill does not match current adapter',
        )
        behavior_drift = dict(observation, skillSha256='0' * 64)
        self.has(
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
            observation['projectionIdentity'].update(_projection_identity(current))
            _write(root, locator, observation)
            reports = {'codex': host_check(root, 'codex')['details']}
            self.ae(
                projection_evidence_binding_errors(
                    root, acceptance, reports, _reader,
                ),
                [],
            )
            observation['projectionIdentity']['skillSha256'] = '0' * 64
            _write(root, locator, observation)
            self.has(
                projection_evidence_binding_errors(
                    root, acceptance, reports, _reader,
                ),
                'skillSha256 does not match current adapter codex',
            )

    def test_ready_frozen_projection_set_selects_only_exact_bound_adapter(self):
        with _provisional() as root:
            acceptance = _read(root, A)
            r3 = _find(acceptance['criteria'], 'id', 'R3')
            r3['assessment'] = 'verified'
            r3['evidence'] = []
            for locator in FROZEN_OBS:
                observation = _read(root, locator)
                r3['evidence'].append({
                    'locator': locator,
                    'sha256': _file_sha(root, locator),
                    'claim': observation['claimLimit']['statement'],
                    'bindsProjection': 'codex',
                    'supportsCriterion': 'R3',
                })
            reports = {
                adapter: host_check(root, adapter)['details']
                for adapter in ('codex', 'claude-code')
            }

            def errors():
                promo_errors = frozen_gt20_21_promotion_errors(
                    root, _read(root, P), acceptance, _read(root, G), _reader,
                )
                lanes = (
                    FROZEN_GT20_21_REPRESENTATIVE_LANES
                    if not promo_errors else {}
                )
                projection_errors = projection_evidence_binding_errors(
                    root, acceptance, reports, _reader, lanes,
                )
                return promo_errors, projection_errors

            self.ae(errors(), ([], []))
            locator = FROZEN_OBS[1]
            original = _read(root, locator)

            for name, path, replacement in (
                ('omitted adapter', ('projectionIdentity', 'projections'),
                 lambda items: items[:-1]),
                ('duplicate adapter', ('projectionIdentity', 'projections'),
                 lambda items: items + [_clone(items[0])]),
                ('mechanism locator drift', ('projectionIdentity', 'projections',
                 0, 'mechanismFiles', 0, 'locator'), 'plugins/drifted/hooks.json'),
            ):
                with self.subTest(name=name):
                    observation = _clone(original)
                    _replace(observation, path, replacement)
                    _write(root, locator, observation)
                    r3['evidence'][1]['sha256'] = _file_sha(root, locator)
                    promo_errors, projection_errors = errors()
                    self.at(promo_errors)
                    self.at(projection_errors)
            _write(root, locator, original)

    def test_representative_sample_binds_projection_source_and_task(self):
        acceptance, golden = _read(ROOT, A), _read(ROOT, G)
        baseline = _contract_sha(acceptance, golden)
        changed = _clone(acceptance)
        changed['criteria'][2]['passRule'] += ' Expanded after capture.'
        self.ane(
            baseline, _contract_sha(changed, golden)
        )
        changed = _clone(acceptance)
        changed['evidenceLanes']['rule'] += (
            ' Later revisions affect only future results.'
        )
        self.ane(
            baseline, _contract_sha(changed, golden)
        )

        with _fixture() as root:
            locator = OBS[1]
            observation = _read(root, locator)
            source = _read(root, SOURCE)
            source['records']['GT-01']['payload'] = 'tampered'
            observation['goldenTaskSha256'] = '0' * 64
            errors = _source_errors(root, locator, source, observation)
            self.has(
                errors,
                'Golden Task digest mismatch',
                'sourceEvidence[0] is invalid',
            )
            record = source['records']['GT-01']
            observation['goldenTaskSha256'] = record['goldenTaskSha256']
            self.has(_source_errors(root, locator, source, observation),
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
            self.has(_source_errors(root, locator, source, observation),
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
                bundle = _clone(original)
                record = bundle['records']['GT-08']
                record['payload']['officialSources'] = sources
                self.has(_source_errors(root, locator, bundle, observation),
                                'sourceEvidence[0] is invalid')

    def test_evidence_authority_bindings_and_types_fail_closed(self):
        precise = _time('2026-08-26T03:54:29.3353264Z')
        self.ann(precise)
        self.ae(precise.microsecond, 335326)
        self.an(_time('not-a-time'))

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
        self.an(_postcapture_bundle(payload, task, _time(record['capturedAt'])))

        for task_id in ('GT-02',):
            with self.subTest(policy_anchor=task_id), _fixture() as root:
                golden = _read(root, G)
                task = _find(golden['tasks'], 'id', task_id)
                locator = OBS[int(task_id[-2:])]
                src_path = SOURCE
                bundle = _read(root, src_path)
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
                self.has(
                    _source_errors(
                        root, locator, bundle, observation, src_path,
                    ),
                    'post-session binding contract does not match representative policy',
                )

        malformed = {'postSessionBindingContract': [{
            'kind': 'independent-poststate', 'location': {}, 'bindingCount': 1
        }]}
        self.an(_postcapture_bundle(
            malformed, malformed, _time('2026-08-24T00:00:00Z')
        ))

        current = _read(ROOT, GT11_SOURCE)['records']['GT-11']
        current_task = tasks['GT-11']
        captured = _time(current['capturedAt'])
        postcapture = lambda payload: _postcapture_bundle(
            payload, current_task, captured)
        self.ann(postcapture(current['payload']))
        direct_result = lambda value: value['independentCommandResults'][0]
        direct_binding = lambda value: _event(value)['sourceBindings'][0]
        command = _clone(current['payload'])
        command['independentCommandResults'] = [{
            'kind': 'independent-command-result',
            'carrierSessionId': '01a03c8f-ba9e-7991-b375-c673345ed4ad',
            'taskLocator': 'GT-11/independent-observer',
            'phase': 'bounded-agent-result',
            'nonce': 'gt11-independent-observer-20260826-a',
            'report': 'The isolated Agent wrote a structured result and exited cleanly.',
        }]
        command_event = _event(command)
        command_event['sourceBindings'] = [{
            'kind': 'direct-independent-command-result',
            'carrierSessionId': '01a03c8f-ba9e-7991-b375-c673345ed4ad',
            'taskLocator': 'GT-11/independent-observer',
            'resultLocator': 'task-artifact:GT-11/independent-observer/agent-final.txt',
            'phaseNonces': ['gt11-independent-observer-20260826-a'],
            'resultSha256': _sha(direct_result(command)['report'].encode('utf-8')),
            'resultRecordSha256': _digest(command['independentCommandResults']),
            'completedAt': '2026-08-26T03:54:30Z',
            'claim': 'Bound to the isolated command result without reading session logs.',
        }]
        self.ann(postcapture(command))
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
            payload = _clone(command)
            target = {'binding': direct_binding(payload),
                      'result': direct_result(payload), 'payload': payload}[scope]
            _replace(target, (key,), _DELETE if value is None else value)
            with self.subTest(direct_independent_command_binding=(scope, key)):
                self.an(postcapture(payload))
        swapped = _clone(command)
        first = direct_result(swapped)
        second = dict(
            first,
            carrierSessionId='01a03c90-409d-79f9-8232-7522da1eefac',
            taskLocator='GT-11/second-observer',
            nonce='gt11-second-observer-20260826-b',
            report='The second isolated Agent completed its own bounded report.',
        )
        swapped['independentCommandResults'].append(second)
        binding = direct_binding(swapped)
        binding['carrierSessionId'] = second['carrierSessionId']
        binding['taskLocator'] = second['taskLocator']
        binding['resultLocator'] = 'task-artifact:GT-11/second-observer/agent-final.txt'
        binding['phaseNonces'] = [second['nonce']]
        binding['resultSha256'] = _sha(second['report'].encode('utf-8'))
        binding['resultRecordSha256'] = _digest([second])
        with self.subTest(swapped_direct_command_carrier=True):
            self.an(postcapture(swapped))
        source_bundle = _read(ROOT, GT11_SOURCE)
        gt12 = source_bundle['records']['GT-12']
        with self.subTest(cross_task_command_bundle=True):
            self.an(_postcapture_bundle(
                gt12['payload'], current_task, _time(gt12['capturedAt'])
            ))
        traversed = _clone(command)
        traversed_result = direct_result(traversed)
        traversed_result['taskLocator'] = (
            'GT-11/../GT-12/independent-observer'
        )
        traversed_binding = direct_binding(traversed)
        traversed_binding['taskLocator'] = traversed_result['taskLocator']
        traversed_binding['resultLocator'] = 'task-artifact:GT-11/../GT-12/independent-observer/agent-final.txt'
        traversed_binding['resultRecordSha256'] = _digest([traversed_result])
        with self.subTest(cross_task_path_traversal=True):
            self.an(postcapture(traversed))
        for field in ('phase', 'report'):
            payload = _clone(command)
            direct_result(payload)[field] = ''
            direct_binding(payload)['resultRecordSha256'] = _digest(
                payload['independentCommandResults']
            )
            with self.subTest(empty_direct_command_field=field):
                self.an(postcapture(payload))
        observation = _read(ROOT, GT11_OBSERVATION)
        payload = _clone(current['payload'])
        payload.pop('recheckTriggers')
        self.af(_publishable_payload(
            payload, current_task, observation['cleanup'],
            captured, observation['projectionIdentity'],
        ))
        self.af(_publishable_payload(
            current['payload'], current_task, 'malformed-cleanup',
            captured, observation['projectionIdentity'],
        ))
        with _fixture() as root:
            malformed_observation = _read(root, GT11_OBSERVATION)
            malformed_observation['cleanup'] = 'malformed-cleanup'
            errors, _ = _observe(
                root, GT11_OBSERVATION, malformed_observation
            )
            self.has(
                errors,
                'sourceEvidence[0] is invalid',
                'cleanup is invalid',
            )

        gt18 = tasks['GT-18']
        source = _read(ROOT, GT16_SOURCE)
        gt07 = tasks['GT-07']
        gt07_record = source['records']['GT-07-cb11759']
        gt07_payload = gt07_record['payload']
        narratives = _continuity_narrative_hashes(
            ROOT, GT16_SOURCE, 'GT-07-cb11759', gt07_payload, gt07,
        )
        self.ann(narratives)
        continuity = lambda payload: _continuity_handoff_bundle(
            payload, gt07, narratives
        )
        destination = lambda items: next(
            item for item in items
            if item['taskLocator'].endswith('/destination-poststate'))
        self.ann(continuity(gt07_payload))
        for path, value in (
            (('materialEvents', 0, 'capacity'), 'known-80-percent'),
            (('materialEvents', 0, 'universalThreshold'), 75),
            (('materialEvents', 1, 'classifications', 1, 'sequentialContextRelief'), True),
            (('materialEvents', 1, 'classifications', 2, 'historyInheritance'), 'copied'),
            (('materialEvents', 1, 'codeTopology', 'changed'), True),
            (('materialEvents', 1, 'executionPlacement', 'changed'), True),
            (('materialEvents', 1, 'sourceReleasedObserved'), True),
        ):
            payload = _clone(gt07_payload)
            _replace(payload, path, value)
            with self.subTest(gt07_semantic_path=path):
                self.an(continuity(payload))
        for name, mutate in (
            ('malformed-binding', lambda value: _event(value)[
                'sourceBindings'][0].__setitem__('taskLocator', [])),
            ('extra-received-field', lambda value: value['materialEvents'][1][
                'receivedFields'].append('credential-content')),
        ):
            candidate = _clone(gt07_payload)
            mutate(candidate)
            with self.subTest(gt07_handoff=name):
                self.an(continuity(candidate))

        contradictory_report = _clone(gt07_payload)
        result = destination(contradictory_report['independentCommandResults'])
        result['report'] += '; inherited copied history and source released early'
        binding = destination(_event(contradictory_report)['sourceBindings'])
        binding['resultSha256'] = _sha(result['report'].encode('utf-8'))
        binding['resultRecordSha256'] = _digest([result])
        self.an(continuity(contradictory_report))
        for name, field, value in (
            ('cross-bound-drift', 'sourceReleasedObserved', True),
            ('provenance', 'sourceNarrativeSha256', '0' * 64),
        ):
            payload = _clone(gt07_payload)
            result = destination(payload['independentCommandResults'])
            result['facts'][field] = value
            result['report'] = _canonical(result['facts'])
            with self.subTest(gt07_destination=name):
                self.an(continuity(payload))

        event = _event(source['records']['GT-18-2460adc']['payload'],
                       'longitudinal-sequence')
        gt18_payload = {
            'evaluatedRevision': source['records']['GT-18-2460adc'][
                'payload']['evaluatedRevision'],
            'materialEvents': [event],
        }
        reject_longitudinal = lambda value, contract: self.an(
            _longitudinal_bundle(value, contract))
        def reject_sequence(value, contract):
            event = value['materialEvents'][0]
            event['sequenceSha256'] = _sequence_digest(event)
            reject_longitudinal(value, contract)

        self.ann(_longitudinal_bundle(gt18_payload, gt18))
        gt18_mutations = (
            (('fullAcceptanceVector', 'states'), ['pass']),
            (('episodes', 1, 'acceptanceVector'), lambda x: x[:-1]),
            (('episodes', 2, 'evaluatorSha256'), 'b' * 64),
            (('episodes', 2, 'sourceFacts', 0, 'valueSha256'), 'b' * 64),
            (('carrierEdges', 0, 'sourceStateSummary'), ''),
            (('carrierEdges', 0, 'sourceState', 'activeRoute'), 'drift'),
            (('carrierEdges',), lambda x: x[:-1]),
            (('episodes', 1, 'disposition'), 'retain-proxy-regression'),
            (('episodes', 1, 'candidateAcceptanceVector'), []),
            (('episodes', 1, 'candidateAcceptanceVector'), lambda x: [
                dict(item, state='pass') for item in x]),
            (('episodes', 2, 'disposition'), 'retain-unbounded-change'),
            (('episodes', 3, 'invalidatedRoute'), 'minimal-composition'),
            *((('stateCarrier',), value) for value in ('malformed-carrier', [], None)),
            (('revision',), '0' * 40),
        )
        for path, value in gt18_mutations:
            candidate = _clone(gt18_payload)
            event_target = candidate['materialEvents'][0]
            _replace(event_target, path, value)
            with self.subTest(gt18_mutation=path, value=repr(value)):
                reject_sequence(candidate, gt18)

        for failed_id, accepted in (
            ('authority-and-accountability', True), ('human-burden', False),
        ):
            candidate = _clone(gt18_payload)
            event_target = candidate['materialEvents'][0]
            vector = event_target['episodes'][1]['candidateAcceptanceVector']
            for item in vector:
                item['state'] = 'fail' if item['id'] == failed_id else 'pass'
            event_target['sequenceSha256'] = _sequence_digest(event_target)
            result = _longitudinal_bundle(candidate, gt18)
            (self.ann if accepted else self.an)(result)
        unbound_sequence = _clone(gt18_payload)
        unbound_sequence['materialEvents'][0]['sequenceSha256'] = '0' * 64
        reject_longitudinal(unbound_sequence, gt18)
        unknown_longitudinal = _clone(gt18)
        unknown_longitudinal['id'] = 'GT-UNKNOWN'
        unknown_longitudinal['kind'] = 'future-longitudinal-contract'
        reject_longitudinal(gt18_payload, unknown_longitudinal)

        gt19 = tasks['GT-19']
        gt19_event = _event(source['records']['GT-19-2460adc']['payload'],
                            'longitudinal-sequence')
        gt19_payload = {
            'evaluatedRevision': source['records']['GT-19-2460adc'][
                'payload']['evaluatedRevision'],
            'materialEvents': [gt19_event],
        }
        reject_longitudinal(gt19_payload, gt19)
        gt19_v2 = _gt19_v2_payload(
            gt19_event, gt19_payload['evaluatedRevision']
        )
        self.ann(_longitudinal_bundle(gt19_v2, gt19))

        for name, path, value, refresh in (
            ('no-invalidation', ('episodes', 1, 'closureRequest', 'environment',
             'observation', 'invalidatedBy'), [], 1),
            ('state-view-drift', ('episodes', 2, 'sparseViews', 'S',
             'environment.provenance-bound', 'writer'), 'self-attested-writer', None),
            ('stale-generation', ('episodes', 2, 'closureRequest', 'environment',
             'observation', 'stateBindings', 0, 'generation'), lambda x: x - 1, 2),
            ('priority-bypass', ('episodes', 3, 'closureRequest', 'environment',
             'observation', 'stateBindings', 0, 'unavailableSources'), [], 3),
            ('missing-last-safe', ('episodes', 1, 'closureRequest', 'environment',
             'lastSafeAllocation'), None, 1),
        ):
            candidate = _clone(gt19_v2)
            event_target = candidate['materialEvents'][0]
            _replace(event_target, path, value)
            if refresh is not None:
                _refresh_gt19_episode(event_target['episodes'][refresh])
            with self.subTest(gt19_mutation=name):
                reject_sequence(candidate, gt19)

        unbound_route_fact = _clone(gt19_v2)
        event_target = unbound_route_fact['materialEvents'][0]
        episode = event_target['episodes'][2]
        route = _find(episode['closureRequest']['routes'], 'id', 'native-no-add')
        route['facts']['available'] = 'not-observed'
        _refresh_gt19_episode(episode)
        reject_sequence(unbound_route_fact, gt19)

        injection_as_effect = _clone(gt19_v2)
        episode = injection_as_effect['materialEvents'][0]['episodes'][1]
        consequence = _clone(episode['closureRequest']['events'][0])
        consequence['factId'] = 'consequence'
        consequence['independent'] = 'observed'
        episode['closureRequest']['events'].append(consequence)
        _refresh_gt19_episode(episode)
        reject_sequence(injection_as_effect, gt19)

        whole_route_mode = _clone(gt19_v2)
        for episode in whole_route_mode['materialEvents'][0]['episodes']:
            baseline = _find(episode['closureRequest']['routes'],
                             'id', 'current-plugin')
            baseline['responsibilityModes']['sense-environment'] = 'agent-native'
            _refresh_gt19_episode(episode)
        reject_sequence(whole_route_mode, gt19)

        changed_on_invalidated_receipt = _clone(gt19_v2)
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
        reject_sequence(changed_on_invalidated_receipt, gt19)

        acceptance = _read(ROOT, A)
        policy = acceptance['representativeBehaviorPolicy']
        current = _contract_sha(acceptance, _read(ROOT, G))
        old = policy['evaluationContractHistory'][0]['sha256']
        sequence_contract = policy['evaluationContractHistory'][1]['sha256']
        qualification_contract = policy['evaluationContractHistory'][2]['sha256']
        dynamic_contract = policy['evaluationContractHistory'][3]['sha256']
        stage_contract = policy['evaluationContractHistory'][4]['sha256']
        self.ai(old, _evaluation_contracts(policy, 'GT-14', current))
        for task_id, expected in (
            ('GT-17', {current, sequence_contract, qualification_contract, stage_contract}),
            ('GT-18', {current, sequence_contract, stage_contract}),
            ('GT-20', {current, dynamic_contract, stage_contract}),
            ('GT-19', {current, stage_contract}),
        ):
            self.ae(_evaluation_contracts(policy, task_id, current),
                             expected)
        widened = _clone(policy)
        widened['evaluationContractHistory'][-1]['preservedTaskIds'].append('GT-01')
        self.an(_evaluation_contracts(widened, 'GT-19', current))
        changed_a = _clone(acceptance)
        changed_policy = changed_a['representativeBehaviorPolicy']
        changed_policy['releaseDecisionRule'] += ' Unrelated future semantic change.'
        changed_current = _contract_sha(
            changed_a, _read(ROOT, G),
        )
        self.ane(changed_current, current)
        self.ae(
            _evaluation_contracts(changed_policy, 'GT-20', changed_current),
            {changed_current},
        )
        malformed = _clone(policy)
        malformed['evaluationContractHistory'][0]['preservedTaskIds'] = []
        self.an(_evaluation_contracts(malformed, 'GT-14', current))

        candidate_bundle = _read(ROOT, GT16_SOURCE)
        cand_record = candidate_bundle['records']['GT-17-fd4b99a']
        candidate_task = _find(_read(ROOT, G)['tasks'], 'id', 'GT-17')
        cand_args = (
            ROOT, cand_record, candidate_task, _digest(candidate_task),
            _time(cand_record['capturedAt']), (acceptance, _read(ROOT, G), current),
        )
        amendments = lambda record=cand_record, contract=cand_args[-1]: (
            _source_amendments(ROOT, record, *cand_args[2:-1], contract))
        self.af(amendments())
        unamended = _clone(cand_record)
        unamended.pop('amendments')
        self.at(amendments(unamended))
        injected = _clone(cand_record)
        injected['payload']['evaluatedRevision'] = '--output=unexpected'
        with patch('yiyuan_accord.evidence._bounded_git_bytes') as git_read:
            self.af(amendments(injected))
            git_read.assert_not_called()
        malformed_history = [
            b'{"tasks":[null]}', json.dumps(acceptance).encode(),
        ]
        with patch('yiyuan_accord.evidence._bounded_git_bytes',
                   side_effect=malformed_history):
            self.af(amendments())
        revision = cand_record['payload']['evaluatedRevision']
        malformed_acceptance = [
            _git(ROOT, 'show', f'{revision}:evals/golden-tasks.json'),
            b'{"claimCeiling":null}',
        ]
        with patch('yiyuan_accord.evidence._bounded_git_bytes',
                   side_effect=malformed_acceptance):
            self.af(amendments())
        with patch('yiyuan_accord.evidence._bounded_git_bytes',
                   side_effect=subprocess.CalledProcessError(1, 'git')):
            self.af(amendments())
        changed_a = _clone(acceptance)
        changed_a['representativeBehaviorPolicy'][
            'releaseDecisionRule'
        ] += ' Unreviewed semantic expansion.'
        changed_contract = (
            changed_a, cand_args[-1][1],
            _contract_sha(changed_a, cand_args[-1][1]),
        )
        changed_record = _clone(cand_record)
        changed_record['amendments'][0][
            'correctedEvaluationContractSha256'
        ] = changed_contract[-1]
        self.af(amendments(changed_record, changed_contract))

        source_cases = (
            (8, ('officialSources', 0, 'url'), 'https://github.com/openai/../x'),
            (8, ('officialSources', 0, 'url'), 'https://github.com/openai/%2e%2e/x'),
            (8, ('officialSources', 0, 'url'), 'https://github.com/\nopenai/x'),
            (8, ('officialSources',), lambda x: [
                dict(x[0], url='https://github.com/openai/x'),
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
                _replace(bundle['records'][observation['taskId']]['payload'], path, value)
                self.has(_source_errors(root, locator, bundle, observation),
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
                self.has(_errors(root), error)

    def test_gt15_embedded_source_packet_is_self_contained_and_fail_closed(self):
        src_path = 'evals/evidence/2026-08-30-v310-gt14-19-source.json'
        obs_path = 'evals/observations/2026-08-30-cf1d8c9-gt-15-codex-local.json'
        record_id = 'GT-15-current-artifacts-cf1d8c9e'
        bundle = _read(ROOT, src_path)
        record = bundle['records'][record_id]
        payload = record['payload']
        task = _find(_read(ROOT, G)['tasks'], 'id', 'GT-15')
        observation = _read(ROOT, obs_path)
        publishable_args = (
            task, observation['cleanup'], _time(record['capturedAt']),
            observation['projectionIdentity'],
        )
        self.at(_publishable_payload(payload, *publishable_args))

        packet = payload['sourcePacket']
        binding = _event(payload, 'current-source-packet-binding')
        self.ae(binding['artifact'], 'embedded:payload.sourcePacket')
        self.ae(binding['artifactSha256'], _digest(packet))
        self.ae(packet['runtimeModelSelection'], 'host-default-variable')
        self.at(all(
            source['facts'] and source['counterevidence']
            and source['role'] and source['license'] and source['maintenance']
            for source in packet['sources'].values()
        ))

        mutations = (
            (0, 'sourcePacket', _DELETE),
            (1, 'runtimeModelSelection', 'concrete-model-version'),
            (2, 'counterevidence', []),
            (3, 'license', 'MIT'),
            (4, 'artifactSha256', '0' * 64),
            (0, 'materialEvents', lambda items: [item for item in items
                if item['kind'] != 'current-source-packet-binding']),
        )
        for index, (scope, path, replacement) in enumerate(mutations):
            candidate = _clone(payload)
            sources = candidate['sourcePacket']['sources']
            target = (candidate, candidate['sourcePacket'],
                      next(iter(sources.values())),
                      _find(sources.values(), 'role', 'public-lead-only'),
                      _event(candidate, 'current-source-packet-binding'))[scope]
            _replace(target, path, replacement)
            with self.subTest(source_packet_mutation=index):
                self.af(
                    _publishable_payload(candidate, *publishable_args)
                )

        with _fixture() as root:
            bundle = _read(root, src_path)
            observation = _read(root, obs_path)
            record = bundle['records'][record_id]
            record['payload'].pop('sourcePacket')
            record['payload']['materialEvents'] = [
                item for item in record['payload']['materialEvents']
                if item['kind'] != 'current-source-packet-binding'
            ]
            observation['transcriptOrEventEvidence'][0]['sha256'] = _digest(record)
            _write(root, src_path, bundle)
            _write(root, obs_path, observation)
            errors, _ = _observe(root, obs_path, observation)
            self.has(errors, 'sourceEvidence[0] is invalid')

    def test_gt16_retained_failure_and_corrected_poststate_are_fail_closed(self):
        src_path = 'evals/evidence/2026-08-30-v310-gt14-19-source.json'
        obs_path = 'evals/observations/2026-08-30-cf1d8c9-gt-16-codex-local.json'
        record_id = 'GT-16-current-artifacts-cf1d8c9e'

        def retained(payload): return _event(
            payload, 'retained-prior-failed-counterevidence')

        def rewrite_blob(blob, path, replacement):
            value = json.loads(blob['text'])
            _replace(value, path, replacement)
            blob['text'] = _canonical(value)
            raw = blob['text'].encode('utf-8')
            blob.update(byteLength=len(raw), sha256=_sha(raw))

        def rebind_command(payload, task_locator, path, replacement):
            result = _find(payload['independentCommandResults'],
                           'taskLocator', task_locator)
            _replace(result['facts'], path, replacement)
            result['report'] = _canonical(result['facts'])
            observations = [*payload['materialEvents'],
                            *payload['cleanupEvidence']['observations']]
            binding = next(
                item for observation in observations
                for item in observation.get('sourceBindings', [])
                if item.get('taskLocator') == task_locator
            )
            binding['resultSha256'] = _sha(result['report'].encode('utf-8'))
            binding['resultRecordSha256'] = _digest([result])

        def change(payload, scope, path, replacement):
            prior = retained(payload)
            if scope in {'originalResult', 'oracleAdjudication'}:
                rewrite_blob(prior[scope], path, replacement)
            elif scope.startswith('GT-16/'):
                rebind_command(payload, scope, path, replacement)
            elif scope == 'original-sha':
                _replace(prior, path, prior['originalResult']['sha256'])
            else:
                _replace(payload if scope == 'payload' else prior,
                         path, replacement)

        def observe_failure(items):
            next(item for item in items
                 if item.get('classification') == 'behavior-failure')[
                     'observed'] = True
            return items

        def reformat_assistant_bytes(payload):
            message = next(
                item for item in payload['messages']
                if item.get('role') == 'assistant'
            )
            value = json.loads(message['text'])
            message['text'] = json.dumps(
                value, ensure_ascii=False, sort_keys=True, indent=2,
            )

        p, r, j, z = 'payload', 'retained', 'oracleAdjudication', '0' * 64
        mutations = (
            ('missing-retained-event', p, 'materialEvents', lambda events: [
                item for item in events if item['kind'] != 'retained-prior-failed-counterevidence']),
            ('original-length', r, 'originalResult.byteLength', 1),
            ('original-sha', r, 'originalResult.sha256', z),
            ('original-bytes', r, 'originalResult.text', lambda text: text + ' '),
            ('original-effect-not-failed', 'originalResult', 'correctedState.effectObserved', True),
            ('adjudication-length', r, 'oracleAdjudication.byteLength', 1),
            ('adjudication-sha', r, 'oracleAdjudication.sha256', z),
            ('adjudication-result-binding', j, 'resultSha256', z),
            ('adjudication-failure-value', j, 'mismatches', observe_failure),
            ('failure-field', r, 'failure.field', 'receipt.consequence.state'),
            ('failure-value', r, 'failure.observedValue', True),
            ('oracle-mutation-permitted', j, 'oracleMutationPermitted', True),
            ('pre-call-oracle-not-retained', j, 'preCallOracleRetained', False),
            ('corrected-attempt-not-distinct', 'original-sha', 'correctedAttempt.resultSha256', None),
            ('corrected-attempt-failed', r, 'correctedAttempt.state', 'failed'),
            ('corrected-effect-not-observed', r, 'correctedAttempt.effectObserved', False),
            ('corrected-poststate-not-observed', r, 'correctedAttempt.independentPoststateObserved', False),
            ('corrected-cleanup-not-observed', r, 'correctedAttempt.cleanupObserved', False),
            ('model-prior-failure-unbound', p,
             'modelResult.value.priorFailureBinding.originalResultSha256', z),
            ('model-value-sha-missing', p, 'modelResult.valueSha256', _DELETE),
            ('model-value-sha-drift', p, 'modelResult.valueSha256', z),
            ('assistant-bytes-format-drift', reformat_assistant_bytes),
            ('effect-poststate-false', 'GT-16/effect-poststate', 'observation.facts.effectObserved', False),
            ('rollback-not-restored', 'GT-16/rollback-release-poststate',
             'observation.facts.fixtureRestoredToBaseline', False),
            ('cleanup-residue', 'GT-16/cleanup-poststate', 'observation.facts.taskOwnedResidueCount', 1),
        )

        with _indexed() as root:
            base_bundle = _read(root, src_path)
            base_obs = _read(root, obs_path)
            acceptance, golden = _read(root, A), _read(root, G)
            task = _find(golden['tasks'], 'id', 'GT-16')
            current = _contract_sha(acceptance, golden)
            ready_args = (True, (acceptance, golden, current))

            def observation_errors(observation):
                _write(root, obs_path, observation)
                return _observe(
                    root, obs_path, observation,
                    'fixture observation', *ready_args,
                )[0]

            def mutation_errors(bundle, observation, name):
                record = bundle['records'][record_id]
                postcapture = _postcapture_bundle(
                    record['payload'], task, _time(record['capturedAt']))
                self.ann(postcapture, name)
                source = observation['transcriptOrEventEvidence'][0]
                source['sha256'] = _digest(record)
                source['postSessionBindingsSha256'] = _digest(postcapture)
                _write(root, src_path, bundle)
                return observation_errors(observation)

            errors, state = _observe(
                root, obs_path, base_obs,
                'fixture observation', *ready_args,
            )
            self.af(any(
                fragment in error for error in errors for fragment in (
                    'sourceEvidence[0] is invalid',
                    'claimLimit contradicts behavior',
                )
            ), errors)
            self.ae(state, 'passed')
            for mutation in mutations:
                name = mutation[0]
                bundle = _clone(base_bundle)
                observation = _clone(base_obs)
                payload = bundle['records'][record_id]['payload']
                (mutation[1](payload) if len(mutation) == 2
                 else change(payload, *mutation[1:]))
                errors = mutation_errors(bundle, observation, name)
                with self.subTest(gt16_mutation=name):
                    self.has(errors, 'sourceEvidence[0] is invalid')

            _write(root, src_path, base_bundle)
            for name, excluded in (
                ('missing-prior-failure-exclusion', []),
                ('wrong-prior-failure-exclusion', ['the corrected attempt failed']),
            ):
                observation = _clone(base_obs)
                observation['claimLimit']['excludedClaims'] = excluded
                with self.subTest(gt16_claim_mutation=name):
                    self.has(observation_errors(observation),
                                    'claimLimit contradicts behavior')

            observation = _clone(base_obs)
            observation['decision']['state'] = 'failed'
            self.has(observation_errors(observation),
                            'failure lacks counterevidence')

    def test_failed_sample_narrows_claim(self):
        with _fixture() as root:
            acceptance = _read(root, A)
            acceptance['representativeBehaviorPolicy']['historicalEvidence'][2][
                'claim'
            ] = 'overclaim'
            _write(root, A, acceptance)
            self.has(
                _errors(root), 'historical claim binding is invalid'
            )
        excluded = _read(ROOT, A)['claimCeiling']['retainedBehaviorExclusions']
        self.ae(excluded, ['GT-07:claude-code:cleanup'])
        archive = _read(ROOT, GT16_SOURCE)['records']
        self.at(all(archive[
            f'archive-observation-GT-{number}-553f5a9']['retainedFailure']
            for number in range(14, 17)))
        with _fixture() as root:
            _enable_current_sample_validation(root)
            acceptance = _read(root, A)
            token = excluded[0]
            acceptance['claimCeiling']['retainedBehaviorExclusions'].remove(token)
            acceptance['claimCeiling']['publicRetainedBehaviorExclusions'].pop(token)
            _write(root, A, acceptance)
            self.has(
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
            self.has(
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
            self.has(
                errors,
                'criterionDecisions contradict behavior',
                'claimLimit contradicts behavior',
                'cleanup contradicts residue',
            )
            locator = OBS[1]
            observation = _read(root, locator)
            observation['decision'] = {'state': 'failed'}
            errors, state = _observe(root, locator, observation, 'must-pass fixture')
            self.ae(state, 'failed')
            self.has(errors, 'failure lacks counterevidence')

    def test_current_sample_blocks_release(self):
        a,g=_read(ROOT,A),_read(ROOT,G)
        r3 = _find(a['criteria'], 'id', 'R3')
        r3['assessment'] = 'verified'
        required = a['representativeBehaviorPolicy']['requiredTaskIdsForRelease']
        e=representative_sample_errors(
            ROOT,a,required,
            g,lambda r,p,_:_read(r,p),True)
        self.ae(e, [])

        missing_task = required[-1]
        r3['evidence'] = [
            item for item in r3['evidence']
            if _read(ROOT, item['locator'])['taskId'] != missing_task
        ]
        e=representative_sample_errors(
            ROOT,a,required,g,lambda r,p,_:_read(r,p),True)
        self.has(e,'representative tasks missing',
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
            self.has(current_errors, 'behavior subject differs')
        else:
            self.ae(current_errors, [])
        self.has(_behavior_subject_revision_errors(
            ROOT, 'stale subject', {'evaluatedRevision': '84447a7a1b9557e22ef5585d159459e8701fa40e'}, task),
            'behavior subject differs from evaluatedRevision')

    def test_plan_process_acceptance_and_release_order_stay_aligned(self):
        with _fixture() as root:
            program = _read(root, P)
            program['releaseProcedure']['orderedGates'][0]['requiredTaskIds'].remove(
                'GT-13'
            )
            _write(root, P, program)
            self.has(
                _errors(root),
                'requiredTaskIds is invalid',
            )

        with _indexed() as root:
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
                self.has(_errors(root),
                                'derived surface markers or structure')
            workflow.write_bytes(body)
            readme = (root / 'README.md').read_text(encoding='utf-8')
            (root / 'README.md').write_text(
                readme.replace(
                    'Release line',
                    'Experimental line',
                    1,
                ),
                encoding='utf-8')
            self.has(_errors(root), 'derived surface markers')
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
            self.has(_errors(root), 'derived surface markers')
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
            snapshot = increment['closeoutSnapshot']
            snapshot['revisionBinding']['exactCommitSha'] = '0' * 40
            snapshot['evaluationContractSha256'] = '0' * 64
            snapshot['acceptanceTransition']['affectedCriterionIds'].remove('R1')
            program['processLossControl']['evolutionHorizonRule'] = ''
            program['releaseProcedure']['orderedGates'][0]['id'] = ''
            program['goalModePrompt']['objective'] = '先推送再审查'
            program['goalModePrompt']['workStageIds'] = ['wrong']
            _write(root, P, program)
            self.has(_errors(root), 'goalModePrompt.mapsTo',
                            'increment.acceptanceIds', 'workItems[0].acceptanceIds',
                            'closeoutSequence', 'required release gate sequence',
                            'workStageIds', 'objective is not the canonical projection',
                            'fourSurfaceMapping outcomeId',
                            'fourSurfaceMapping.process phases',
                            'orderedSteps[1].dependsOn',
                            'closeoutSnapshot revision binding',
                            'closeoutSnapshot evaluation contract',
                            'closeoutSnapshot affected criteria',
                            'processLossControl.evolutionHorizonRule',
                            )

        with _indexed() as root:
            program = _read(root, P)
            snapshot = program['increment']['closeoutSnapshot']
            origin = _snapshot_v1_lineage(
                root, snapshot, 'HEAD', {},
            )[0]
            snapshot['predecessorSnapshotRef'] = (
                f'{origin}:'
                'product/program.json#/increment/closeoutSnapshot'
            )
            snapshot['acceptanceTransition']['affectedCriterionIds'].remove('R1')
            _write(root, P, program)
            self.has(_errors(root), 'closeoutSnapshot affected criteria')

        with _indexed() as root:
            current = _read(root, P)
            prior = _clone(current)
            prior['increment']['closeoutSnapshot']['id'] += '.different'
            _write(root, P, prior)
            _git(root, 'add', P)
            _git(root, '-c', 'user.name=Accord Fixture',
                 '-c', 'user.email=fixture@example.invalid',
                 'commit', '--quiet', '-m', 'different prior snapshot')
            current_snapshot = current['increment']['closeoutSnapshot']
            current_snapshot['predecessorSnapshotRef'] = None
            current_snapshot['acceptanceTransition'].update(
                kind='snapshot-bootstrap', affectedCriterionIds=CRITERIA)
            _write(root, P, current)
            self.has(_errors(root),
                            'bootstrap breaks predecessor lineage')

        snapshot_ref = 'product/program.json#/increment/closeoutSnapshot'

        def snapshot_errors(root, program=None, cache=None):
            a, g, errors = _read(root, A), _read(root, G), []
            _validate_closeout_snapshot(
                root, program or _read(root, P), a, set(CRITERIA),
                _contract_sha(a, g), errors, _cache=cache)
            return errors

        def advance(program, gates, index, predecessor):
            snapshot = program['increment']['closeoutSnapshot']
            snapshot['acceptanceTransition'].update(
                kind='unchanged', affectedCriterionIds=[])
            snapshot.update(id=f'stage.v3.1.0.{gates[index]}.closed',
                            stage=gates[index], closedGateId=gates[index],
                            nextGateId=gates[index + 1],
                            predecessorSnapshotRef=f'{predecessor}:{snapshot_ref}')
            snapshot['evidenceRefs'][-1] = (
                f'product/program.json#/releaseProcedure/orderedGates/{index}')
            return snapshot

        current = _read(ROOT, P)
        predecessor = current['increment']['closeoutSnapshot'][
            'predecessorSnapshotRef'
        ].split(':', 1)[0]
        prior = json.loads(_git(
            ROOT, 'show', f'{predecessor}:{P}', text=True,
        ))
        with patch(
            'yiyuan_accord.control._validate_constitution',
            side_effect=AssertionError('current rule leaked into snapshot v1'),
        ), patch(
            'yiyuan_accord.control._validate_acceptance',
            side_effect=AssertionError('current rule leaked into snapshot v1'),
        ), patch(
            'yiyuan_accord.control._validate_program',
            side_effect=AssertionError('current rule leaked into snapshot v1'),
        ), patch(
            'yiyuan_accord.control.representative_contract_sha256',
            side_effect=AssertionError('current digest leaked into snapshot v1'),
        ), patch(
            'yiyuan_accord.control.release_identity_errors',
            side_effect=AssertionError('current release rule leaked into snapshot v1'),
        ):
            self.ae(_snapshot_lineage_contract_errors(
                ROOT, predecessor,
                prior['increment']['closeoutSnapshot'], (predecessor,), (), {},
            ), [])
        unsupported = (
            _read(ROOT, C), _clone(current), _read(ROOT, A),
            _read(ROOT, 'product/reshaping-guidance.json'), _read(ROOT, G),
        )
        unsupported[1]['increment']['closeoutSnapshot']['schema'] = (
            'yiyuan-accord-stage-closeout-snapshot/v2'
        )
        self.has(
            _snapshot_revision_contract_errors(ROOT, predecessor, unsupported),
            'unsupported revision-bound snapshot schema',
        )

        exact_documents = _snapshot_documents(ROOT, predecessor)
        malformed_cases = (
            (0, ('identity',), []),
            (1, ('releaseProcedure',), []),
            (1, ('increment', 'closeoutSnapshot',
                 'evaluationContractSha256'), 7),
            (2, ('criteria',), 'not-a-list'),
            (2, ('representativeBehaviorPolicy', 'claimCeiling'), []),
        )
        with patch(
            'yiyuan_accord.control._snapshot_v1_projection_package_errors',
            return_value=[],
        ), patch(
            'yiyuan_accord.control._snapshot_v1_evidence_errors',
            return_value=[],
        ):
            for document_index, path, replacement in malformed_cases:
                documents = list(_clone(exact_documents))
                _replace(documents[document_index], path, replacement)
                self.at(
                    _snapshot_revision_contract_errors(
                        ROOT, predecessor, tuple(documents),
                    ),
                    f'malformed v1 history must fail closed: {path}',
                )
            renamed = list(_clone(exact_documents))
            renamed[1]['hostProjections'][0]['packageId'] = (
                'yiyuan-accord-renamed'
            )
            self.has(
                _snapshot_revision_contract_errors(
                    ROOT, predecessor, tuple(renamed),
                ),
                'projection package ids are invalid',
            )
        malformed_evidence = list(_clone(exact_documents))
        malformed_evidence[2]['representativeBehaviorPolicy'][
            'historicalEvidence'
        ][0]['sha256'] = 7
        with patch(
            'yiyuan_accord.control._snapshot_bytes', return_value=b'{}',
        ):
            self.has(
                _snapshot_v1_evidence_errors(
                    ROOT, malformed_evidence[1], malformed_evidence[2],
                    predecessor,
                ),
                'historicalEvidence[0] binding is invalid',
            )

        constitution, prior_program, prior_acceptance, prior_guidance, \
            prior_golden = exact_documents
        successor = _clone(prior_program)
        gates = [
            item['id'] for item in successor['releaseProcedure']['orderedGates']
        ]
        closed_index = gates.index(
            successor['increment']['closeoutSnapshot']['closedGateId']
        )
        advance(successor, gates, closed_index + 1, predecessor)
        successor['hostProjections'][0]['activationContext'] += ' Drift.'
        self.has(
            _snapshot_v1_transition_errors(
                ROOT, None, predecessor,
                successor, prior_acceptance, prior_guidance,
                constitution, prior_golden,
                prior_program, prior_acceptance, prior_guidance,
                constitution, prior_golden,
            ),
            'revision-bound v1 affected criteria are invalid',
        )
        successor['hostProjections'][0]['activationContext'] = (
            prior_program['hostProjections'][0]['activationContext']
        )
        with patch(
            'yiyuan_accord.control._snapshot_or_worktree_bytes',
            side_effect=lambda root, locator, revision=None: (
                b'prior-marketplace' if revision else b'current-marketplace'
            ),
        ):
            self.has(
                _snapshot_v1_transition_errors(
                    ROOT, None, predecessor,
                    successor, prior_acceptance, prior_guidance,
                    constitution, prior_golden,
                    prior_program, prior_acceptance, prior_guidance,
                    constitution, prior_golden,
                ),
                'revision-bound v1 affected criteria are invalid',
            )

        lineage_cache = {}
        with patch(
            'yiyuan_accord.control._bounded_git_bytes',
            wraps=_bounded_git_bytes,
        ) as bounded_git:
            _, latest, _, _ = _snapshot_v1_lineage(
                ROOT, current['increment']['closeoutSnapshot'],
                'HEAD', lineage_cache,
            )
            scans = sum(
                call.args[1][0] in {'log', 'cat-file'}
                for call in bounded_git.call_args_list
            )
            self.ann(latest)
            _snapshot_v1_lineage(
                ROOT, latest[1], latest[0], lineage_cache,
            )
            self.ae(sum(
                call.args[1][0] in {'log', 'cat-file'}
                for call in bounded_git.call_args_list
            ), scans)

        oversized_revision = 'a' * 40
        def oversized_history(root, args, limit=262_144, input_bytes=None):
            if args[0] == 'log':
                return f'{oversized_revision}\n'.encode('ascii')
            if args[:2] == ['cat-file', '--batch']:
                return (
                    f'{oversized_revision} blob 1000001\n'.encode('ascii')
                )
            raise AssertionError(args)
        with patch(
            'yiyuan_accord.control._bounded_git_bytes',
            side_effect=oversized_history,
        ), self.assertRaisesRegex(ValueError, 'blob bound'):
            _snapshot_v1_lineage(
                ROOT, {}, oversized_revision, {},
            )

        deeply_nested_revision = 'b' * 40
        deeply_nested = b'{"a":' * 100_000 + b'0' + b'}' * 100_000
        def deeply_nested_history(root, args, limit=262_144, input_bytes=None):
            if args[0] == 'log':
                return f'{deeply_nested_revision}\n'.encode('ascii')
            if args[:2] == ['cat-file', '--batch']:
                return (
                    f'{deeply_nested_revision} blob {len(deeply_nested)}\n'
                ).encode('ascii') + deeply_nested + b'\n'
            raise AssertionError(args)
        with patch(
            'yiyuan_accord.control._bounded_git_bytes',
            side_effect=deeply_nested_history,
        ), self.assertRaisesRegex(ValueError, 'structure'):
            _snapshot_v1_lineage(
                ROOT, {}, deeply_nested_revision, {},
            )
        parser_success = 0
        for _ in range(_SNAPSHOT_V1_MAX_JSON_DEPTH - 1):
            parser_success = {'a': parser_success}
        self.at(_snapshot_v1_json_structure_is_bounded(parser_success))
        parser_success = {'a': parser_success}
        self.af(_snapshot_v1_json_structure_is_bounded(parser_success))
        with patch(
            'yiyuan_accord.control._bounded_git_bytes',
            side_effect=deeply_nested_history,
        ), patch(
            'yiyuan_accord.control._strict_json_object',
            return_value=parser_success,
        ), self.assertRaisesRegex(ValueError, 'structure'):
            _snapshot_v1_lineage(
                ROOT, {}, deeply_nested_revision, {},
            )

        with _indexed() as root:
            locator = 'evals/evidence/large-snapshot-regression.json'
            raw = b'{"value":"' + (b'x' * 300_000) + b'"}\n'
            (root / locator).write_bytes(raw)
            _git(root, 'add', locator)
            _git(root, '-c', 'user.name=Accord Fixture',
                 '-c', 'user.email=fixture@example.invalid',
                 'commit', '--quiet', '-m', 'large snapshot blob')
            revision = _git(root, 'rev-parse', 'HEAD', text=True).strip()
            self.ae(_snapshot_bytes(root, locator, revision), raw)

        with _indexed() as root:
            program = _read(root, P)
            drifted = _clone(program)
            drifted['increment']['fourSurfaceMapping']['plan']['hypothesis'] += ' Drift.'
            self.has(snapshot_errors(root, drifted),
                     'snapshot-bound state drifted without successor')
            readme = root / 'README.md'
            readme.write_text(readme.read_text(encoding='utf-8') + '\ncarry\n',
                              encoding='utf-8')
            self.ae(snapshot_errors(root, program), [])

        with _indexed() as root:
            original = _read(root, P)
            drifted = _clone(original)
            drifted['increment']['fourSurfaceMapping']['plan']['hypothesis'] += ' Drift.'
            _write(root, P, drifted)
            _git(root, 'add', P)
            _git(root, '-c', 'user.name=Accord Fixture',
                 '-c', 'user.email=fixture@example.invalid',
                 'commit', '--quiet', '-m', 'invalid bound-state carry')
            _write(root, P, original)
            _git(root, 'add', P)
            _git(root, '-c', 'user.name=Accord Fixture',
                 '-c', 'user.email=fixture@example.invalid',
                 'commit', '--quiet', '-m', 'restore bound state')
            self.has(snapshot_errors(root),
                     'snapshot-bound state drifted without successor')

        with _indexed() as root:
            cache = {}

            def invalid_carry(
                locator, content, label, expected,
                lineage_expected='revision-bound repository contract is invalid',
            ):
                path, original = root / locator, (root / locator).read_bytes()
                path.write_bytes(content)
                _git(root, 'add', locator)
                _git(root, '-c', 'user.name=Accord Fixture',
                     '-c', 'user.email=fixture@example.invalid',
                     'commit', '--quiet', '-m', label)
                revision = _git(
                    root, 'rev-parse', 'HEAD', text=True,
                ).strip()
                revision_errors = _snapshot_revision_contract_errors(
                    root, revision,
                )
                if expected is None:
                    self.ae(revision_errors, [])
                else:
                    self.has(revision_errors, expected)
                cache[('revision-bound-snapshot-contract', revision)] = (
                    not revision_errors
                )
                path.write_bytes(original)
                _git(root, 'add', locator)
                _git(root, '-c', 'user.name=Accord Fixture',
                     '-c', 'user.email=fixture@example.invalid',
                     'commit', '--quiet', '-m', f'restore {label}')
                self.has(
                    snapshot_errors(root, cache=cache),
                    lineage_expected,
                )

            marketplace = '.agents/plugins/marketplace.json'
            changed_marketplace = _read(root, marketplace)
            changed_marketplace['plugins'][0]['category'] = 'Productivity'
            invalid_carry(
                marketplace,
                (json.dumps(changed_marketplace, separators=(',', ':')) + '\n').encode(),
                'drift valid Codex marketplace surface', None,
                'snapshot-bound state drifted without successor',
            )
            constitution = _read(root, C)
            constitution['identity']['displayName'] = ''
            invalid_carry(
                C, (json.dumps(constitution, separators=(',', ':')) + '\n').encode(),
                'constitution-invalid-then-restored',
                'revision-bound v1 identity is invalid',
            )
            acceptance = _read(root, A)
            acceptance['schema'] = 2
            invalid_carry(
                A, (json.dumps(acceptance, separators=(',', ':')) + '\n').encode(),
                'acceptance-invalid-then-restored',
                'revision-bound v1 authority schema is invalid',
            )
            invalid_carry(
                'evals/observations/'
                '2026-08-30-cf1d8c9-gt-07-codex-local.json',
                b'{"corrupted":true}\n', 'corrupt referenced snapshot evidence',
                'digest mismatch',
            )
            invalid_carry(
                'evals/observations/2026-08-24-v20-claude-gt01.json',
                b'{"corrupted":true}\n',
                'corrupt historical-only snapshot evidence',
                'digest mismatch',
            )
            package = 'plugins/yiyuan-accord-codex/adapter.json'
            invalid_carry(
                package, (root / package).read_bytes() + b'\n',
                'drift declared projection package',
                'revision package digest mismatch',
            )

        with _indexed() as root:
            program = _read(root, P)
            gates = [x['id'] for x in program['releaseProcedure']['orderedGates']]
            origin = _snapshot_v1_lineage(
                root, program['increment']['closeoutSnapshot'], 'HEAD', {},
            )[0]
            readme = root / 'README.md'
            readme.write_text(readme.read_text(encoding='utf-8') + '\ncarry\n',
                              encoding='utf-8')
            _git(root, 'add', 'README.md')
            _git(root, '-c', 'user.name=Accord Fixture',
                 '-c', 'user.email=fixture@example.invalid',
                 'commit', '--quiet', '-m', 'carry unchanged snapshot')
            carry = _git(root, 'rev-parse', 'HEAD', text=True).strip()
            advance(program, gates, 1, carry)
            self.has(snapshot_errors(root, program),
                     'predecessor is not latest accepted snapshot')
            program['increment']['closeoutSnapshot']['predecessorSnapshotRef'] = (
                f'{origin}:{snapshot_ref}'
            )
            self.ae(snapshot_errors(root, program), [])

        with _indexed() as root:
            original = _read(root, P)
            successor = _clone(original)
            gates = [x['id'] for x in successor['releaseProcedure']['orderedGates']]
            origin = _snapshot_v1_lineage(
                root, original['increment']['closeoutSnapshot'], 'HEAD', {},
            )[0]
            advance(successor, gates, 1, origin)
            _write(root, P, successor)
            _git(root, 'add', P)
            _git(root, '-c', 'user.name=Accord Fixture',
                 '-c', 'user.email=fixture@example.invalid',
                 'commit', '--quiet', '-m', 'new snapshot before replay')
            self.has(snapshot_errors(root, original),
                     'lineage replays a non-current node')

        with _indexed() as root:
            program = _read(root, P)
            invalid = _clone(program)
            invalid['increment']['closeoutSnapshot']['authorityRefs'] = ['invalid']
            _write(root, P, invalid)
            _git(root, 'add', P)
            _git(root, '-c', 'user.name=Accord Fixture',
                 '-c', 'user.email=fixture@example.invalid',
                 'commit', '--quiet', '-m', 'invalid snapshot node')
            revision = _git(root, 'rev-parse', 'HEAD', text=True).strip()
            gates = [x['id'] for x in program['releaseProcedure']['orderedGates']]
            advance(program, gates, 1, revision)
            _write(root, P, program)
            self.has(snapshot_errors(root, program),
                     'predecessor is not a valid revision-bound snapshot node')

        with _indexed() as root:
            program = _read(root, P)
            base = _snapshot_v1_lineage(
                root, program['increment']['closeoutSnapshot'], 'HEAD', {},
            )[0]
            snapshot = program['increment']['closeoutSnapshot']
            snapshot['predecessorSnapshotRef'] = f'{base}:{snapshot_ref}'
            snapshot['acceptanceTransition'].update(
                kind='unchanged', affectedCriterionIds=[])
            program['distributionVersion'] = 'v3.2.0'
            snapshot['id'] = 'stage.v3.2.0.repository-candidate.closed'
            errors = snapshot_errors(root, program)
            self.has(errors, 'predecessor cannot be resolved')

        with _indexed() as root:
            program = _read(root, P)
            gates = [item['id'] for item in program['releaseProcedure']['orderedGates']]
            base = _snapshot_v1_lineage(
                root, program['increment']['closeoutSnapshot'], 'HEAD', {},
            )[0]
            snapshot = advance(program, gates, 1, base)
            _write(root, P, program)
            _git(root, 'add', P)
            _git(root, '-c', 'user.name=Accord Fixture',
                 '-c', 'user.email=fixture@example.invalid',
                 'commit', '--quiet', '-m', 'newer accepted snapshot')
            latest = _git(root, 'rev-parse', 'HEAD', text=True).strip()
            advance(program, gates, 2, snapshot['predecessorSnapshotRef'].split(':')[0])
            errors = snapshot_errors(root, program)
            self.has(errors, 'predecessor is not latest accepted snapshot')
            snapshot['predecessorSnapshotRef'] = f'{latest}:{snapshot_ref}'
            errors = snapshot_errors(root, program)
            self.ae(errors, [])

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
            objective = _canonical(projection)
            program['goalModePrompt']['objective'] = objective
            acceptance['canonicalGoalObjectiveSha256'] = _sha(
                objective.encode('utf-8'))
            _write(root, P, program)
            _write(root, A, acceptance)
            self.has(
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
        self.af(blocked_errors)

        program = _read(ROOT, P)
        prompt = program['goalModePrompt']
        locators = ['authority/root.json', 'authority/evidence.json']
        projection = json.loads(canonical_goal_objective(
            program, {'semantic': locators},
            prompt['workStageIds'], prompt['releaseGateIds'],
        ))
        self.ae(projection['authority']['locators'], locators)
        self.ae(projection['authority']['mode'],
                         'reviewable-versioned-current-set')
        self.ae(
            projection['outcome']['id'],
            'outcome.complete-bounded-self-bootstrapping-core',
        )
        self.ae(
            _canonical_official_url('https://code.claude.com/docs/en/desktop'),
            'https://code.claude.com/docs/en/desktop',
        )
        self.ae(
            _canonical_official_url(
                'https://learn.chatgpt.com/docs/environments/cloud-environment'
            ),
            'https://learn.chatgpt.com/docs/environments/cloud-environment',
        )
        self.ae(
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
                {'locator': P, 'sha256': _file_sha(root, P),
                 'claim': 'self claim', 'supportsCriterion': 'R1'},
                {'locator': locator, 'sha256': _file_sha(root, locator),
                 'claim': 'repository self-attestation', 'supportsCriterion': 'R1'}]
            acceptance['releaseAuthorization'].update(
                state='authorized', candidateRevision='0' * 40, namedHuman='repo',
                authorizedAt='2026-08-21T00:00:00Z', claimCeilingAccepted=True,
                publicationAuthorized=True, releaseAuthorized=True)
            _write(root, A, acceptance)
            report = verify_product(root)
            self.has(report['errors'], 'direct evidence must use', 'deterministic conformance is computed live', 'cannot grant human authority')
            self.ani('releaseComplete', report)

    def test_external_release_contract_is_exact_and_external(self):
        self.ann(RELEASE_RE.fullmatch('v2.0.1-preview.1+build.7'))
        self.ann(CONTRACT_RELEASE_RE.fullmatch('v2.0'))
        for invalid in ('v2.0', 'v2.0.01', 'v2.0.1-01', '2.0.1', 'v2.0.1-'):
            with self.subTest(invalid_distribution=invalid):
                self.an(RELEASE_RE.fullmatch(invalid))
        huge_numeric = '9' * 5_000
        for value, lower, upper in (
            (f'v{huge_numeric}.0.0', 'v9.0.0', None),
            (f'v1.0.0-{huge_numeric}', 'v1.0.0-9', 'v1.0.0'),
        ):
            with self.subTest(semver=value[:12]):
                precedence, low = map(_semantic_version_precedence, (value, lower))
                high = _semantic_version_precedence(upper) if upper else None
                self.ann(precedence)
                self.at(precedence > low and (high is None or precedence < high))

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
            lambda v: v['historicalRelease'].update(publicReleases=[]),
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
            self.has(_errors(root), 'systems do not match', 'publicRelease policy',
                            'release notes digest', 'claims and exclusions overlap')

        with _fixture() as root:
            acceptance = _read(root, A)
            notes = root / acceptance['publicRelease']['releaseNotes']
            summary = next(iter(
                acceptance['claimCeiling']['publicNotImplied'].values()))
            notes.write_text(notes.read_text(encoding='utf-8').replace(
                'It does not imply:', f'- {summary}\n\nIt does not imply:', 1),
                encoding='utf-8')
            acceptance['publicRelease']['releaseNotesSha256'] = _sha(notes.read_bytes())
            _write(root, A, acceptance)
            self.has(_errors(root), 'release notes do not expose the complete claim ceiling')

    def test_public_release_history_freezes_admitted_snapshot_and_rejects_tail(self):
        program = _read(ROOT, P)
        acceptance = _read(ROOT, A)
        identity = _read(ROOT, C)['identity']
        ledger = (ROOT / 'docs/operations/HISTORY.md').read_text(
            encoding='utf-8'
        )

        def history_errors(history, projection=ledger):
            changed_program = _clone(program)
            changed_a = _clone(acceptance)
            changed_program['historicalRelease'] = _clone(history)
            changed_a['historicalRelease'] = _clone(history)
            return release_identity_errors(
                identity, changed_program, changed_a, projection,
            )

        def add_release(value, recommend=None, **changes):
            value['publicReleases'].append({
                **value['publicReleases'][-1], **changes})
            if recommend:
                value['recommendedPublicRelease'] = recommend

        baseline = _clone(program['historicalRelease'])
        legacy_future = {**baseline['publicReleases'][-1], 'tag': 'v4.0'}
        self.af(_public_release_record_valid(legacy_future))
        self.af(any(
            'historicalRelease provenance is invalid' in error
            for error in history_errors(baseline)
        ))

        for name, mutation in (
            ('known-revision-type', lambda value: value['publicReleases'][3].update(
                revision=7)),
            ('non-object-record', lambda value: value['publicReleases'].__setitem__(
                0, None)),
            ('known-order', lambda value: value['publicReleases'].__setitem__(
                slice(0, 2), list(reversed(value['publicReleases'][:2])))),
            ('duplicate-tag', lambda value: add_release(
                value, revision='a' * 40, publishedAt='2026-08-28T00:00:00Z')),
            ('duplicate-revision', lambda value: add_release(
                value, tag='v3.1.0', publishedAt='2026-08-28T00:00:00Z')),
            ('kind-mismatch', lambda value: value['publicReleases'][2].update(
                releaseKind='full-release')),
            ('preview-as-full', lambda value: add_release(
                value, 'v3.1.0-preview.2', tag='v3.1.0-preview.2',
                revision='a' * 40, publishedAt='2026-09-01T00:00:00Z')),
            ('legacy-tail', lambda value: add_release(
                value, tag='v4.0', revision='a' * 40,
                publishedAt='2026-09-01T00:00:00Z')),
            ('noncanonical-time', lambda value: add_release(
                value, tag='v3.1.0-preview.2', revision='a' * 40,
                releaseKind='public-preview', prerelease=True,
                publishedAt='2026-9-1T0:0:0Z')),
            ('fictional-full-tail', lambda value: add_release(
                value, 'v3.1.0', tag='v3.1.0', revision='b' * 40,
                publishedAt='2026-09-02T00:00:00Z')),
            ('semantic-authority-field', lambda value: (
                value.__setitem__('authority', value.pop('provenanceProjection')),
            )),
            ('repository-fact-source', lambda value: value.update(
                externalFactSource='repository-declared'
            )),
        ):
            with self.subTest(invalid_history=name):
                changed = _clone(baseline)
                mutation(changed)
                self.at(any(
                    'historicalRelease provenance is invalid' in error
                    for error in history_errors(changed)
                ))

        fictional_projection_tail = ledger.replace(
            '\nThe recorded recommendation pointer',
            '\n| `v9.9.9` | `aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa` | '
            '`2026-09-09T09:09:09Z` | full Release | no attached assets |\n'
            '\nThe recorded recommendation pointer',
        )
        table_lines = [
            line for line in ledger.splitlines()
            if line.startswith('|')
        ]
        reversed_projection = ledger.replace(
            '\n'.join(table_lines[2:4]),
            '\n'.join(reversed(table_lines[2:4])),
        )
        hidden_table = ledger.replace(
            '\n'.join(table_lines), '<!--\n' + '\n'.join(table_lines) + '\n-->',
        )
        for projection in (
            ledger.replace(
                '`24cf9f3750ecd700944988e81a519db54b67b8e8`',
                '`0000000000000000000000000000000000000000`',
            ),
            fictional_projection_tail,
            fictional_projection_tail.replace(
                '\n| `v9.9.9`', '\n | `v9.9.9`',
            ),
            reversed_projection,
          hidden_table,
          ledger.replace(
              '## Public Release ledger',
              '```markdown\n## Public Release ledger', 1,
          ).replace('## Major boundaries', '## Major boundaries\n```', 1),
          ledger.replace(
              '## Public Release ledger', '<!--\n## Public Release ledger', 1,
          ).replace('## Major boundaries', '## Major boundaries\n-->', 1),
          ledger.replace(
              '## Public Release ledger', '<div hidden>\n## Public Release ledger', 1,
          ).replace('## Major boundaries', '## Major boundaries\n</div>', 1),
          ledger.replace(
                'It is not semantic authority or live publication',
                'It is not live authority or publication', 1,
            ) + '\n<!-- It is not semantic authority or live publication -->',
            ledger.replace(
                'It is not semantic authority or live publication',
                'It is semantic authority and live publication', 1,
            ).replace(
                '\n## Major boundaries',
                '\n<!-- It is not semantic authority or live publication -->'
                '\n\n## Major boundaries',
            ),
            ledger.replace(
                '\n## Major boundaries',
                '\nThis ledger is semantic authority and live publication; '
                'the actual recommendation is `v9.9.9`.\n\n## Major boundaries',
            ),
        ):
            self.has(
                history_errors(baseline, projection),
                'historicalRelease provenance is invalid',
            )

    def test_complexity_identity_and_paths_fail_closed(self):
        with _fixture() as root:
            report = verify_product(root)
            self.has(report['errors'], 'tracked repository surface is unavailable')
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
                self.ae(
                    any('complexity headroom too small' in error for error in errors),
                    rejected,
                )

        with _indexed() as root:
            revision = _git(root, 'rev-parse', 'HEAD', text=True).strip()
            (root / 'vendor').mkdir()
            _git(root, 'update-index', '--add', '--cacheinfo', '160000', revision, 'vendor')
            self.has(
                _errors(root),
                'tracked repository entry is not a regular file: vendor (mode 160000)',
            )

        locator = 'docs/license-policy.md'
        for flag in ('--skip-worktree', '--assume-unchanged'):
            with self.subTest(index_flag=flag), _indexed() as root:
                _git(root, 'update-index', flag, locator)
                if flag == '--skip-worktree':
                    (root / '.DS_Store').write_bytes(b'\0retired_module\0')
                    (root / locator).unlink()
                else:
                    (root / locator).write_text('hidden drift\n', encoding='utf-8')
                self.ae(
                    _git(root, 'status', '--porcelain=v1', '--untracked-files=all'), b''
                )
                report = verify_product(root)
                self.af(report['checkoutClean'])
                if flag == '--skip-worktree':
                    self.has(report['errors'], f'active tree file is unreadable: {locator}')
                    self.at(_lacks(report['errors'], '.DS_Store'))
                else:
                    self.at(_lacks(report['errors'], locator))

        with _indexed() as root:
            locator = 'oversized-static-surface.bin'
            oversized = root / locator
            with oversized.open('wb') as stream:
                stream.truncate(2_000_000)
            _git(root, 'add', '-f', locator)
            with _deny_path('read_bytes', oversized):
                errors = _errors(root)
            self.has(errors, f'active tree identity scan is indeterminate: {locator}')

        with _indexed() as root:
            locator = 'docs/license-policy.md'
            (root / locator).unlink()
            (root / locator).mkdir()
            self.has(_errors(root),
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
                self.has(
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
                self.has(_byte_errors(payload, locator), message)

        safe = (
            (('汉字' * 100 + '\npython -m retired_module_other\n').encode(), 'sample.sh'),
            (('# -*- coding: gb18030 -*-\n# import ｒｅｔｉｒｅｄ＿ｍｏｄｕｌｅ\n').encode('gb18030'),
             'sample.py'),
        )
        for payload, locator in safe:
            self.at(_lacks(
                _byte_errors(payload, locator), 'superseded identity', 'undecodable'
            ))

        png = b'\x89PNG\r\n\x1a\n' + b'bounded-fixture'
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            locator = 'assets/sample.png'
            target = root / locator
            target.parent.mkdir()
            target.write_bytes(png)
            assets = {locator: _sha(png)}
            def scan(declared=None):
                with patch('yiyuan_accord.identity._bounded_git_bytes',
                           side_effect=_retired_history()):
                    return active_tree_errors(
                        root, [locator], '0' * 40,
                        digest_bound_binary_assets=declared,
                    )
            self.at(_lacks(
                scan(assets), 'digest-bound binary asset', 'undecodable',
            ))
            target.write_bytes(png + b'tampered')
            self.has(
                scan(assets), 'digest-bound binary asset does not match',
            )
            self.has(scan(), 'active tree file is undecodable')

        with _indexed() as root:
            target = root / 'docs/assets/sponsoring/wechat-pay.png'
            target.write_bytes(target.read_bytes() + b'tampered')
            self.has(
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
            self.has(errors, 'active tree file is unreadable: sample.txt')
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
            self.ae(errors, ['symbolic link is not admitted in active tree: sample.txt'])

    def test_active_tree_reads_are_descriptor_bound(self):
        with _indexed() as root, tempfile.TemporaryDirectory() as outside:
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
                self.has(
                    _errors(root),
                    f'active tree file is unreadable: {locator}',
                )

    def test_git_metadata_capture_is_bounded(self):
        original_popen = subprocess.Popen
        observed_stdin = []

        def launch(*arguments, **options):
            observed_stdin.append(options.get('stdin'))
            return original_popen(*arguments, **options)

        with patch('yiyuan_accord.identity.subprocess.Popen', side_effect=launch):
            captured = _bounded_git_bytes(
                ROOT, ['cat-file', '--batch'], 65_536, b'HEAD:AGENTS.md\n',
            )
        self.af(observed_stdin[0] == subprocess.PIPE)
        self.ai(b'YIYUAN Accord thin collaboration kernel', captured)

        with _indexed() as root:
            blob = _git(root, 'hash-object', '-w', '--stdin', input=b'').strip()
            records = b''.join(
                b'100644 ' + blob + b'\tbulk/' + str(index).encode()
                + b'-' + b'x' * 96 + b'.txt\n'
                for index in range(2_500)
            )
            _git(root, 'update-index', '--index-info', input=records)
            self.assertGreater(len(records), 262_144)
            self.has(
                _errors(root),
                'tracked repository surface is unavailable',
            )

    def test_historical_identity_capture_is_bounded(self):
        with _indexed() as root:
            constitution = _read(root, C)
            constitution['oversizedFixture'] = 'x' * 1_000_001
            _write(root, C, constitution)
            _git(root, 'add', C)
            _git(root, '-c', 'user.name=Accord Fixture',
                 '-c', 'user.email=fixture@example.invalid', 'commit', '--quiet',
                 '-m', 'oversized historical identity')
            revision = _git(root, 'rev-parse', 'HEAD', text=True).strip()
            self.has(
                active_tree_errors(root, [], revision),
                'historical identity boundary is unavailable',
            )

    def test_conservative_identity_boundary_allows_declared_safe_surfaces(self):
        errors = _errors(ROOT)
        self.at(_lacks(
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
                self.at(_lacks(_retired_errors(body, locator),
                                       'superseded identity', 'indeterminate'))

        locator = 'research/reviews/reference.md'
        admitted = _active_errors(
            locator, 'Historical retired_module reference.\n', {locator}
        )
        self.at(_lacks(admitted, 'superseded identity'))

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
                        _retired_errors(body, locator),
                        'superseded identity remains',
                    )

        for body in (
            'value = t"retired_module"\n',
            'value = t"retired_\\155odule"\n',
            'value = rt"retired_\\u006dodule"\n',
        ):
            with self.subTest(shared_python_grammar=body):
                self.assert_has(
                    _retired_errors(body, 'sample.py'),
                    'active tree identity scan is indeterminate',
                )

        self.assert_has(
            _retired_errors('ｒｅｔｉｒｅｄ＿ｍｏｄｕｌｅ\n'),
            'superseded identity remains',
        )
        self.assert_has(
            _retired_errors('safe' * 250_001),
            'active tree identity scan is indeterminate',
        )
        self.assert_has(
            _retired_errors(
                'value = ' + _balanced_add(["'safe'"] * 4_097) + '\n',
                'sample.py',
            ),
            'active tree identity scan is indeterminate',
        )

        self.assert_has(
            _active_errors('retired_module/config.txt'),
            'superseded identity remains',
        )
        locator = 'docs/new-surface.txt'
        message = 'superseded identity remains in active tree: ' + locator
        self.assert_has(_active_errors(locator, 'retired_module\n'), message)
        self.assert_has(
            _active_errors(locator, 'retired_module\n', {locator}), message
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
        self.assert_has(_retired_errors('retired-product', 'README.md'),
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
            self.has(errors, 'digest source is oversized')

    def test_live_hook_stays_silent_for_fresh_startup(self):
        event = _hook_event(
            'startup',
            session_id='must-not-be-emitted-or-persisted',
            transcript_path='must-not-be-opened-or-emitted',
            cwd='C:/disposable/workspace',
        )
        with _hook_workspace(self) as temporary:
            result = _run_hook(self, event, temporary)
            self.ae(result.returncode, 0, result.stderr)
            self.ae(result.stdout, '')

    def test_live_hook_emits_only_typed_minimum_continuity_context(self):
        with _hook_workspace(self) as temporary:
            result = _run_hook(self, _hook_event('compact'), temporary)
            self.ae(result.returncode, 0, result.stderr)
            envelope = json.loads(result.stdout)
            context = json.loads(
                envelope['hookSpecificOutput']['additionalContext'])
            self.ae(envelope['hookSpecificOutput']['hookEventName'],
                             'SessionStart')
            self.ae(context, {
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
            self.ani('private-session-sentinel', result.stdout)
            self.ani('private-transcript-sentinel', result.stdout)
            self.ani('private-workspace-sentinel', result.stdout)

    def test_live_hook_distinguishes_recovery_from_fresh_sources(self):
        with _hook_workspace(self) as temporary:
            fresh = _run_hook(self, _hook_event('clear'), temporary)
            resumed = _run_hook(self, _hook_event('resume'), temporary)
            self.ae(fresh.returncode, 0, fresh.stderr)
            self.ae(fresh.stdout, '')
            self.ae(resumed.returncode, 0, resumed.stderr)
            envelope = json.loads(resumed.stdout)
            context = json.loads(
                envelope['hookSpecificOutput']['additionalContext'])
            self.ae(context['signal'], {
                'event': 'SessionStart',
                'source': 'resume',
                'sourceKind': 'supported-official-hook-event',
            })

    def test_live_hook_does_not_propagate_invalid_or_unbound_fields(self):
        event = _hook_event(
            'compact', model={'raw': 'private-model-sentinel'},
            permission_mode=['private-permission-sentinel'],
        )
        with _hook_workspace(self) as temporary:
            invalid_fields = _run_hook(self, event, temporary)
            malformed = _run_hook(self, '{malformed', temporary)
            unknown_source = _run_hook(
                self, {**event, 'source': 'unknown'}, temporary)
            self.ae(invalid_fields.returncode, 0,
                             invalid_fields.stderr)
            envelope = json.loads(invalid_fields.stdout)
            context = json.loads(
                envelope['hookSpecificOutput']['additionalContext'])
            self.ae(context['eventHints'], [])
            self.ani('private-model-sentinel', invalid_fields.stdout)
            self.ani('private-permission-sentinel',
                             invalid_fields.stdout)
            self.ae(malformed.returncode, 1)
            self.ae(malformed.stdout, '')
            self.ae(
                malformed.stderr,
                'YIYUAN Accord: invalid SessionStart hook input; state remains unknown.\n',
            )
            self.ae(unknown_source.returncode, 1)
            self.ae(unknown_source.stdout, '')
            self.ae(unknown_source.stderr, malformed.stderr)

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
                self.ae(
                    (ROOT / root / 'runtime' / 'accord-hook.cjs').read_bytes(),
                    canonical,
                )
                hook = _read(ROOT, f'{root}/hooks/hooks.json')
                handler = hook['hooks']['SessionStart'][0]['hooks'][0]
                self.ae(handler, expected_handler)
