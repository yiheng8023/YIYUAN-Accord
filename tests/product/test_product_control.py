from contextlib import contextmanager
import hashlib, json, re, shutil, tempfile, unittest
from pathlib import Path
from unittest.mock import patch
from yiyuan_accord.control import host_check, verify_product
from yiyuan_accord.evidence import representative_contract_sha256
from yiyuan_accord.identity import active_tree_errors
ROOT = Path(__file__).resolve().parents[2]
(C, A, P, G) = ('product/constitution.json', 'product/acceptance.json', 'product/program.json', 'evals/golden-tasks.json')
SOURCE = 'evals/evidence/s.json'
CRITERIA = ['R1', 'R2', 'R3', 'R4', 'Q1', 'Q2', 'Q3', 'Q4']

def _read(root, locator):
    return json.loads((root / locator).read_text(encoding='utf-8'))

def _write(root, locator, value):
    path = root / locator
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, separators=(',', ':')) + '\n', encoding='utf-8')

def _digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True,
                          separators=(',', ':')).encode()).hexdigest()

@contextmanager
def _fixture():
    with tempfile.TemporaryDirectory(prefix='ya-') as temporary:
        target = Path(temporary) / 'repository'
        shutil.copytree(ROOT, target, ignore=shutil.ignore_patterns('.git', '.tmp', '__pycache__', '*.pyc'))
        yield target

def _projection(root, adapter='codex'):
    report = verify_product(root)['hostChecks'][adapter]
    locators = {key: report[key] for key in ('manifest', 'marketplace', 'contract', 'skill') if isinstance(report.get(key), str)}
    return {'adapterId': adapter, **report['identity'], **locators}

def _rehash(root, locator):
    acceptance = _read(root, A)
    digest = hashlib.sha256((root / locator).read_bytes()).hexdigest()
    for criterion in acceptance['criteria']:
        for item in criterion['evidence']:
            if item['locator'] == locator:
                item['sha256'] = digest
    _write(root, A, acceptance)

def _sample(root):
    (acceptance, golden) = (_read(root, A), _read(root, G))
    required = set(acceptance['representativeBehaviorPolicy']['requiredTaskIdsForRelease'])
    projection = _projection(root)
    host = {'adapterId': 'codex', 'hostProduct': 'h', 'hostVersion': 'v', 'sessionId': 's'}
    evaluation = representative_contract_sha256(acceptance, golden)
    source,retained,by_id={'schema':1,'records':{}},[],{x['id']:x for x in acceptance['criteria']}
    for item in acceptance['criteria']:
        item['evidence']=[]
    for task in golden['tasks']:
        if task['id'] not in required:
            continue
        (task_id, failed) = (task['id'], task['id'] == 'GT-02')
        mapped = {item for item in task['mapsTo'] if re.fullmatch('[RQ][0-9]+', item)}
        task_digest = _digest(task)
        common = {'taskId': task_id, 'goldenTaskSha256': task_digest, 'evaluationContractSha256': evaluation, 'hostIdentity': host}
        record = {**common, 'kind': 'host-event-log', 'capturedAt': '2026-08-20T00:00Z', 'payload': task_id}
        source['records'][task_id] = record
        required_status = {item: 'observed' for item in task['required']}
        failures = []
        if failed:
            required_status[task['required'][0]] = 'not-observed'
            failures = [f"required:{task['required'][0]}"]
            retained.extend((f'{task_id}:{value}' for value in failures))
        observation = {
            **common, 'evidenceClass': 'representative-behavior',
            'observedAt': '2026-08-20T00:01Z',
            'observer': {'kind': 'host-event-recorder', 'identity': 'f'},
            'projectionIdentity': projection, 'startingState': {'declared': task['startingState']},
            'transcriptOrEventEvidence': [{'kind': 'host-event-log', 'locator': SOURCE,
                'recordId': task_id, 'sha256': _digest(record), 'claim': 's'}],
            'behaviorDecisions': {'required': required_status,
                'prohibited': {item: 'absent' for item in task['prohibited']}},
            'observedAgentActions': [{'kind': 'a'}], 'observedHumanActions': [],
            'humanBurden': {item: 0 for item in golden['metrics']['humanBurden']},
            'materialEffects': [], 'residue': [],
            'cleanup': {'state': 'verified-clean', 'taskOwnedResidueCount': 0, 'verified': True},
            'criterionDecisions': {item: 'accepted-with-exclusion' if failed else 'accepted'
                                   for item in mapped},
            'claimLimit': {'retainedFailure': failed, 'excludedClaims': failures,
                           'statement': 'b'},
            'decision': {'state': 'failed' if failed else 'passed'}}
        locator = f'evals/observations/current-{task_id.lower()}.json'
        _write(root, locator, observation)
        evidence = {'locator': locator, 'sha256': hashlib.sha256((root / locator).read_bytes()).hexdigest(), 'claim': task_id, 'bindsProjection': 'codex'}
        for criterion_id in mapped:
            criterion = by_id[criterion_id]
            if 'representative-behavior' in criterion['requiredEvidenceClasses']:
                criterion['evidence'].append({**evidence, 'supportsCriterion': criterion_id})
    for criterion in acceptance['criteria']:
        if criterion['requiredEvidenceClasses'] == ['representative-behavior']:
            criterion['assessment'] = 'verified'
    acceptance['claimCeiling']['retainedBehaviorExclusions'] = sorted(retained)
    notes = root / acceptance['publicRelease']['releaseNotes']
    marker = f"`retainedBehaviorExclusions={json.dumps(sorted(retained), separators=(',', ':'))}`"
    notes.write_text(re.sub('`retainedBehaviorExclusions=.*?`', marker,
                            notes.read_text(encoding='utf-8')), encoding='utf-8')
    acceptance['publicRelease']['releaseNotesSha256'] = hashlib.sha256(notes.read_bytes()).hexdigest()
    _write(root, SOURCE, source)
    _write(root, A, acceptance)

class ProductControlTests(unittest.TestCase):

    def assert_has(self, errors, *fragments):
        for fragment in fragments:
            self.assertTrue(any(fragment in error for error in errors), fragment)

    def rejected(self, locator, message, mutate):
        with _fixture() as root:
            value = _read(root, locator)
            mutate(value)
            _write(root, locator, value)
            self.assert_has(verify_product(root)['errors'], message)

    def test_current_contract_is_valid_and_explicitly_incomplete(self):
        report = verify_product(ROOT)
        self.assertTrue(report['valid'], report['errors'])
        self.assertEqual(report['criteria']['ids'], CRITERIA)
        if report['programStatus'] == 'active':
            self.assertLess(report['criteria']['verified'], 8)
            self.assertFalse(report['repositoryCandidateReady'])
        else:
            self.assertEqual(report['programStatus'], 'ready')
            self.assertEqual(report['criteria']['verified'], 8)
            self.assertEqual(report['repositoryCandidateReady'], report['checkoutClean'])
        self.assertTrue(all((host['staticReady'] for host in report['hostChecks'].values())))

    def test_authority_and_static_suite_mutations_fail_closed(self):
        cases = (
            (C, 'constitution top-level shape', lambda v: v.update(extra=True)),
            (P, 'program top-level shape', lambda v: v.update(releaseComplete=True)),
            (A, 'acceptance top-level shape', lambda v: v.update(authorize=True)),
            (C, 'compatibilityAliases must be empty',
             lambda v: v['identity'].update(compatibilityAliases=['x'])),
            (C, 'humanAuthority shape', lambda v: v.pop('humanAuthority')),
            (G, 'static-suite-as-behavior',
             lambda v: v['evaluationProtocol'].update(staticSuiteIsNotBehaviorEvidence=False)),
            (G, 'humanBurden metrics', lambda v: v['metrics'].update(help=['self-claim'])),
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

    def test_projection_evidence_rejects_drift_and_relocation(self):
        with _fixture() as root:
            _sample(root)
            locator = 'evals/observations/current-gt-01.json'
            observation = _read(root, locator)
            observation['projectionIdentity']['skillSha256'] = '0' * 64
            _write(root, locator, observation)
            _rehash(root, locator)
            self.assert_has(verify_product(root)['errors'], 'skillSha256 does not match')

    def test_representative_sample_binds_projection_source_and_task(self):
        with _fixture() as root:
            _sample(root)
            errors = verify_product(root)['errors']
            self.assertFalse(any(('representative' in item or 'R3 evidence' in item for item in errors)))
            acceptance = _read(root, A)
            acceptance['criteria'][2]['passRule'] += ' Expanded after capture.'
            _write(root, A, acceptance)
            self.assert_has(verify_product(root)['errors'], 'evaluation contract digest mismatch')
            source = _read(root, SOURCE)
            source['records']['GT-01']['payload'] = 'tampered'
            _write(root, SOURCE, source)
            acceptance = _read(root, A)
            acceptance['criteria'][7]['evidence'].pop()
            _write(root, A, acceptance)
            self.assert_has(verify_product(root)['errors'], 'sourceEvidence', 'Q4 representative coverage')

    def test_failed_sample_narrows_claim(self):
        with _fixture() as root:
            _sample(root)
            acceptance = _read(root, A)
            retained = acceptance['claimCeiling']['retainedBehaviorExclusions']
            acceptance['claimCeiling']['retainedBehaviorExclusions'] = []
            _write(root, A, acceptance)
            self.assert_has(verify_product(root)['errors'], 'retained behavior exclusions')
            acceptance['claimCeiling']['retainedBehaviorExclusions'] = retained
            _write(root, A, acceptance)
            locator = 'evals/observations/current-gt-02.json'
            observation = _read(root, locator)
            observation['criterionDecisions']['Q4'] = 'accepted'
            observation['claimLimit'] = {'retainedFailure': False, 'excludedClaims': [], 'statement': 'all supported'}
            observation['residue'] = [{'kind': 'task-owned-residue'}]
            _write(root, locator, observation)
            _rehash(root, locator)
            self.assert_has(verify_product(root)['errors'], 'criterionDecisions', 'claimLimit contradicts', 'cleanup contradicts residue')
            locator = 'evals/observations/current-gt-01.json'
            observation = _read(root, locator)
            observation['decision'] = {'state': 'failed'}
            _write(root, locator, observation)
            _rehash(root, locator)
            self.assert_has(verify_product(root)['errors'], 'must-pass tasks')

    def test_plan_process_acceptance_and_release_order_stay_aligned(self):
        with _fixture() as root:
            program = _read(root, P)
            program['goalModePrompt']['mapsTo'].remove('Q4')
            increment = program['increment']
            increment['acceptanceIds'].remove('R3')
            increment['workItems'][0]['acceptanceIds'].remove('Q1')
            increment['workItems'][0]['closeoutSequence'][0]['state'] = 'active'
            increment['workItems'][0]['closeoutSequence'][0]['stopCondition'] = 'opposite'
            program['releaseProcedure']['orderedGates'][0]['id'] = ''
            program['goalModePrompt']['objective'] = '先推送再审查'
            program['goalModePrompt']['workStageIds'] = ['wrong']
            _write(root, P, program)
            readme = (root / 'README.md').read_text(encoding='utf-8')
            (root / 'README.md').write_text(readme.replace('restart the desktop app', 'skip reload'), encoding='utf-8')
            self.assert_has(verify_product(root)['errors'], 'derived surface markers')
            (root / 'README.md').write_text(readme, encoding='utf-8')
            self.assert_has(verify_product(root)['errors'], 'goalModePrompt.mapsTo',
                            'increment.acceptanceIds', 'workItems[0].acceptanceIds',
                            'closeoutSequence', 'required release gate sequence',
                            'release gate order', 'workStageIds')

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
        with _fixture() as root:
            acceptance = _read(root, A)
            acceptance['candidateVerification']['requiredSystems'] = {'codex-cloud': 'https://example.invalid'}
            acceptance['publicRelease']['assetPolicy'] = 'allow-assets'
            acceptance['claimCeiling']['finiteReleaseClaims'].append(acceptance['claimCeiling']['notImplied'][0])
            _write(root, A, acceptance)
            (root / 'docs/releases/v2.0.md').write_text('# expanded\n', encoding='utf-8')
            self.assert_has(verify_product(root)['errors'], 'systems do not match', 'publicRelease policy', 'release notes digest', 'claims and exclusions overlap')

    def test_complexity_identity_and_paths_fail_closed(self):
        with _fixture() as root, tempfile.TemporaryDirectory() as outside:
            program = _read(root, P)
            program['complexityBudget']['primaryInstructionPaths'] = []
            program['complexityBudget']['forbiddenActivePaths'] = [Path(outside).as_posix()]
            _write(root, P, program)
            constitution = _read(root, C)
            constitution['identity']['pythonModule'] = 'missing_module'
            constitution['authority']['executableVerifier'] = 'python -B -m missing_module verify'
            _write(root, C, constitution)
            markers = program['complexityBudget']['requiredTestMarkers']
            body = '\n'.join(f'    {item}(self): pass' for item in markers
                             if item.startswith('def '))
            for bad in ("@unittest.skip('x')\n",
                        'def load_tests(*a): return unittest.TestSuite()\n',
                        'from os import _exit as stop\nstop(0)\n'):
                fake = f'import unittest\n{bad}class ProductControlTests(unittest.TestCase):\n{body}'
                (root / 'tests/product/test_product_control.py').write_text(fake, encoding='utf-8')
                self.assert_has(verify_product(root)['errors'], 'pythonModule does not match', 'primaryInstructionPaths', 'not a repository-relative path', 'test markers')

    def test_retired_residue_and_duplicate_json_fail_closed(self):
        with _fixture() as root:
            retired = 'yiyuan_accord/task_validator_o4_continuous_self_correction_v3.py'
            (root / retired).write_text('# retired\n', encoding='utf-8')
            (root / '.tmp').mkdir()
            self.assert_has(verify_product(root)['errors'], 'forbidden active path remains', 'known task residue')
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / 'README.md').write_text('retired-product', encoding='utf-8')
            old = {'productId': 'retired-product', 'authority': {'executableVerifier': 'python -B -m retired_module verify'}}
            with patch('yiyuan_accord.identity.subprocess.check_output', side_effect=[json.dumps(old), '# Retired Product\n']):
                self.assert_has(active_tree_errors(root, ['README.md'], '0' * 40), 'superseded identity remains')
        with _fixture() as root:
            (root / P).write_text('{"schema":2,"schema":2}\n', encoding='utf-8')
            self.assert_has(verify_product(root)['errors'], 'duplicate JSON key')
