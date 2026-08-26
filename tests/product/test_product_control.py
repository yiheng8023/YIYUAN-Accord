from contextlib import contextmanager
import hashlib, json, shutil, subprocess, tempfile, unittest
from pathlib import Path
from unittest.mock import patch
from yiyuan_accord.control import (
    _validate_four_surface_mapping, host_check, verify_product,
)
from yiyuan_accord.evidence import (
    _canonical_official_url,
    _digest,
    _observation_errors,
    _postcapture_bundle,
    _publishable_payload,
    _time,
    representative_contract_sha256,
)
from yiyuan_accord.guardrails import (
    canonical_goal_objective,
    closeout_sequence_errors,
    projection_observation_errors,
    validate_projection_package,
)
from yiyuan_accord.identity import (
    CONTRACT_RELEASE_RE,
    RELEASE_RE,
    active_tree_errors,
)
ROOT = Path(__file__).resolve().parents[2]
(C, A, P, G) = ('product/constitution.json', 'product/acceptance.json', 'product/program.json', 'evals/golden-tasks.json')
SOURCE = 'evals/evidence/2026-08-24-v20-representative-source.json'
CURRENT_GT11_SOURCE = 'evals/evidence/2026-08-26-gt11-codex-local-source.json'
CURRENT_GT11_OBSERVATION = 'evals/observations/2026-08-26-gt11-codex-local.json'
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
        shutil.copytree(ROOT, target, ignore=shutil.ignore_patterns('.git', '.tmp', '__pycache__', '*.pyc'))
        yield target

@contextmanager
def _indexed_fixture():
    with tempfile.TemporaryDirectory(prefix='ya-index-') as temporary:
        target = Path(temporary) / 'repository'
        subprocess.run(
            ['git', 'clone', '--quiet', '--no-hardlinks', str(ROOT), str(target)],
            check=True,
        )
        shutil.copytree(
            ROOT,
            target,
            dirs_exist_ok=True,
            ignore=shutil.ignore_patterns('.git', '.tmp', '__pycache__', '*.pyc'),
        )
        _git(target, 'add', '-A')
        _git(target, '-c', 'user.name=Accord Fixture',
             '-c', 'user.email=fixture@example.invalid', 'commit', '--quiet',
             '--allow-empty', '-m', 'current fixture')
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

def _observe(root, locator, observation=None, label='fixture observation'):
    golden, observed = _read(root, G), observation or _read(root, locator)
    task = next(item for item in golden['tasks'] if item['id'] == observed['taskId'])
    return _observation_errors(
        root, label, observed, task, golden['metrics']['humanBurden'], locator,
        observed['projectionIdentity']['adapterId'], observed['evaluationContractSha256'],
        lambda current_root, current_locator, _: _read(current_root, current_locator)
    )

def _public_source_errors(root, locator, bundle, observation):
    record = bundle['records'][observation['taskId']]
    _write(root, SOURCE, bundle)
    source = observation['transcriptOrEventEvidence'][0]
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
        report = verify_product(ROOT)
        self.assertTrue(report['valid'], report['errors'])
        self.assertEqual(report['criteria']['ids'], CRITERIA)
        if report['programStatus'] == 'active':
            program = _read(ROOT, P)
            stages = program['increment']['workItems'][0]['closeoutSequence']
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
        program, acceptance = _read(ROOT, P), _read(ROOT, A)
        constitution = _read(ROOT, C)
        guidance = _read(ROOT, 'product/reshaping-guidance.json')
        self.assertEqual(guidance['status'], 'accepted-revisable-guidance')
        self.assertEqual(
            guidance['dynamicIndex']['graphProjection']['implementation'],
            'derived-in-memory-or-ignored-cache-first',
        )
        self.assertIn(
            'preview2-is-a-current-release-candidate',
            {item['id'] for item in guidance['retiredAsActivePremises']},
        )
        historical_notes = (
            ROOT / 'docs/releases/v2.0.1-preview.2.md'
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
        target = program['complexityBudget']['targets']
        self.assertGreaterEqual(
            target['maxTrackedFiles'] - report['complexity']['trackedFiles'], 3
        )
        limit = target['maxProductCodeAndTestBytes']
        percent = program['complexityBudget']['minimumProductCodeAndTestHeadroomPercent']
        self.assertGreaterEqual(limit - report['complexity']['productCodeAndTestBytes'],
                                (limit * percent + 99) // 100)
        self.assertNotRegex((ROOT / 'CONTEXT.md').read_text(encoding='utf-8'),
                            r'#/[^`\n]+/[0-9]+(?:/|`)')
        self.assertNotIn('maxControlBytes', program['complexityBudget']['targets'])
        if report['programStatus'] == 'ready':
            gate = program['releaseProcedure']['orderedGates'][1]['condition']
            for marker in (
                'original host or session records',
                'context-isolated, outcome-bound, identity-neutral',
            ):
                self.assertIn(marker, gate)
                self.assertIn(marker, acceptance['candidateVerification']['rule'])
        else:
            prompt = program['goalModePrompt']
            self.assertEqual(
                prompt['state'],
                'retired' if program['increment']['state'] == 'completed'
                else 'active-in-host',
            )
            mapping = program['increment']['fourSurfaceMapping']
            self.assertEqual(
                mapping['outcomeId'],
                program['increment']['representativeOutcome']['id'],
            )
            projection = json.loads(prompt['objective'])
            self.assertEqual(projection['schema'], 'yiyuan-accord-goal/v2')
            ordered = projection['route']['orderedSteps']
            self.assertLessEqual(
                len(prompt['objective']), 3600,
                'canonical host goal must keep headroom below the Codex limit',
            )
            self.assertEqual(
                ordered,
                [{field: step[field] for field in (
                    'id', 'state', 'dependsOn', 'acceptanceIds'
                )} for step in mapping['process']['orderedSteps']],
            )
    def test_authority_and_static_suite_mutations_fail_closed(self):
        cases = (
            (C, 'constitution top-level shape', lambda v: v.update(extra=True)),
            (P, 'program top-level shape', lambda v: v.update(releaseComplete=True)),
            (A, 'acceptance top-level shape', lambda v: v.update(authorize=True)),
            (C, 'compatibilityAliases must be empty',
             lambda v: v['identity'].update(compatibilityAliases=['x'])),
            (C, 'humanAuthority shape', lambda v: v.pop('humanAuthority')),
            (P, 'minimumProductCodeAndTestHeadroomPercent', lambda v: v[
                'complexityBudget'].update(minimumProductCodeAndTestHeadroomPercent=4)),
            (P, 'digestBoundBinaryAssets must be an object', lambda v: v[
                'complexityBudget'].pop('digestBoundBinaryAssets')),
            (G, 'static-suite-as-behavior',
             lambda v: v['evaluationProtocol'].update(staticSuiteIsNotBehaviorEvidence=False)),
            (G, 'humanBurden metrics', lambda v: v['metrics'].update(help=['self-claim'])),
            (A, 'representative post-session binding contracts', lambda v: v[
                'representativeBehaviorPolicy'].update(postSessionBindingContracts=[])),
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
            skill.write_text(skill.read_text(encoding='utf-8').replace('name: deliver-demand-driven-outcome', 'name: publish-now', 1), encoding='utf-8')
            market = _read(root, projection['marketplace'])
            market['plugins'][0]['policy']['installation'] = 'INSTALLED_BY_DEFAULT'
            _write(root, projection['marketplace'], market)
            self.assert_has(host_check(root, 'codex')['errors'], 'program projection shape',
                            'package digest', 'unsupported fields', 'Skill frontmatter identity',
                            'AVAILABLE/ON_INSTALL', 'interface contract')
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
                    projection['metadataFiles'], [],
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

    def test_projection_evidence_rejects_drift_and_relocation(self):
        observation = _read(ROOT, CURRENT_GT11_OBSERVATION)['projectionIdentity']
        current = host_check(ROOT, 'codex')['details']
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
        with _fixture() as root:
            locator = CURRENT_GT11_OBSERVATION
            observation = _read(root, locator)
            observation['projectionIdentity']['skillSha256'] = '0' * 64
            _write(root, locator, observation)
            _rehash(root, locator)
            self.assert_has(_errors(root), 'skillSha256 does not match')

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

        for task_id in ('GT-02', 'GT-07'):
            with self.subTest(policy_anchor=task_id), _fixture() as root:
                golden = _read(root, G)
                task = next(item for item in golden['tasks'] if item['id'] == task_id)
                locator, bundle = OBS[int(task_id[-2:])], _read(root, SOURCE)
                record, observation = bundle['records'][task_id], _read(root, locator)
                payload = record['payload']
                if task_id == 'GT-02':
                    task.pop('postSessionBindingContract')
                    payload.pop('postSessionBindingContract')
                    payload['materialEvents'] = [
                        event for event in payload['materialEvents']
                        if event['kind'] != 'independent-poststate'
                    ]
                    observation['transcriptOrEventEvidence'][0].pop(
                        'postSessionBindingsSha256'
                    )
                else:
                    task['postSessionBindingContract'][0]['bindingCount'] = 1
                    payload['postSessionBindingContract'][0]['bindingCount'] = 1
                    bindings = payload['cleanupEvidence']['observations'][-1]['sourceBindings']
                    payload['cleanupEvidence']['observations'][-1]['sourceBindings'] = bindings[:1]
                digest = _digest(task)
                record['goldenTaskSha256'] = observation['goldenTaskSha256'] = digest
                _write(root, G, golden)
                self.assert_has(
                    _public_source_errors(root, locator, bundle, observation),
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
        for mutation in (
            'digest', 'nonce', 'agent-task', 'carrier', 'locator', 'completed',
            'result', 'results-missing',
        ):
            payload = json.loads(json.dumps(current['payload']))
            event = next(
                item for item in payload['materialEvents']
                if item['kind'] == 'independent-poststate'
            )
            binding = event['sourceBindings'][0]
            if mutation == 'digest':
                binding['resultSha256'] = '0' * 64
            elif mutation == 'nonce':
                binding['phaseNonces'][0] = 'unbound-phase'
            elif mutation == 'agent-task':
                binding['agentTask'] = '/root/different-agent'
            elif mutation == 'carrier':
                binding['carrierSessionId'] = 'wrong'
            elif mutation == 'locator':
                binding['resultLocator'] = 'codex-collaboration-agent:/wrong'
            elif mutation == 'completed':
                binding['completedAt'] = '2999-01-01T00:00:00Z'
            elif mutation == 'result':
                payload['independentAgentResults'][0]['report'] += ' drift'
            else:
                payload.pop('independentAgentResults')
            with self.subTest(direct_independent_binding=mutation):
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
        self.assertEqual(
            _read(ROOT, A)['claimCeiling']['retainedBehaviorExclusions'], ['GT-07:cleanup']
        )
        self.rejected(A, 'retained behavior exclusions', lambda v:
                      v['claimCeiling'].update(
                          retainedBehaviorExclusions=['GT-07:stale exclusion']))
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

    def test_plan_process_acceptance_and_release_order_stay_aligned(self):
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
                    'v3.0.0 full-release candidate',
                    'v3.0.0 draft only',
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
        item['state'] = item['closeoutSequence'][-1]['state'] = 'blocked'
        steps = increment['fourSurfaceMapping']['process']['orderedSteps']
        steps[-1]['state'] = 'blocked'
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
            projection['outcome']['id'], 'outcome.agent-owned-repository-repair'
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
            lambda v: v.update(distributionVersion='v3.0.1'),
        )
        self.rejected(
            P, 'historicalRelease provenance is invalid',
            lambda v: v['historicalRelease'].update(
                unreleasedCheckpoint='v2.0.01'
            ),
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
