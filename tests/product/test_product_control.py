from contextlib import contextmanager
import hashlib, json, shutil, subprocess, tempfile, unittest
from pathlib import Path
from unittest.mock import patch
from yiyuan_accord.control import host_check, verify_product
from yiyuan_accord.evidence import (
    _digest,
    _observation_errors,
    representative_contract_sha256,
)
from yiyuan_accord.guardrails import validate_projection_package
from yiyuan_accord.identity import active_tree_errors
ROOT = Path(__file__).resolve().parents[2]
(C, A, P, G) = ('product/constitution.json', 'product/acceptance.json', 'product/program.json', 'evals/golden-tasks.json')
SOURCE = 'evals/evidence/2026-08-24-v20-representative-source.json'
CRITERIA = ['R1', 'R2', 'R3', 'R4', 'Q1', 'Q2', 'Q3', 'Q4']
RETIRED = {'productId': 'retired-product',
           'authority': {'executableVerifier': 'python -B -m retired_module verify'}}

def _read(root, locator):
    return json.loads((root / locator).read_text(encoding='utf-8'))

def _write(root, locator, value):
    path = root / locator
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, separators=(',', ':')) + '\n', encoding='utf-8')

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
        subprocess.run(
            ['git', '-C', str(target), 'add', '-A'],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        subprocess.run([
            'git', '-C', str(target), '-c', 'user.name=Accord Fixture',
            '-c', 'user.email=fixture@example.invalid', 'commit', '--quiet',
            '--allow-empty', '-m', 'current fixture',
        ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        yield target

def _rehash(root, locator):
    acceptance = _read(root, A)
    digest = hashlib.sha256((root / locator).read_bytes()).hexdigest()
    for item in (item for criterion in acceptance['criteria']
                 for item in criterion['evidence']):
        if item['locator'] == locator:
            item['sha256'] = digest
    _write(root, A, acceptance)

def _attach_evidence(root, criterion_id, locator):
    acceptance = _read(root, A)
    observation = _read(root, locator)
    criterion = next(
        item for item in acceptance['criteria'] if item['id'] == criterion_id
    )
    criterion['evidence'].append({
        'locator': locator,
        'sha256': hashlib.sha256((root / locator).read_bytes()).hexdigest(),
        'claim': observation['claimLimit']['statement'],
        'bindsProjection': observation['projectionIdentity']['adapterId'],
        'supportsCriterion': criterion_id,
    })
    _write(root, A, acceptance)

def _observe(root, locator, observation=None, label='fixture observation'):
    golden, observed = _read(root, G), observation or _read(root, locator)
    task = next(item for item in golden['tasks'] if item['id'] == observed['taskId'])
    return _observation_errors(
        root, label, observed, task, golden['metrics']['humanBurden'], locator,
        observed['projectionIdentity']['adapterId'], observed['evaluationContractSha256'],
        lambda current_root, current_locator, _: _read(current_root, current_locator)
    )

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
        history = [json.dumps(RETIRED), '# Retired Product\n']
        with patch('yiyuan_accord.identity.subprocess.check_output', side_effect=history):
            return active_tree_errors(root, [locator], '0' * 40)

def _lacks(errors, *fragments):
    return not any(fragment in error for error in errors for fragment in fragments)

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
            program = _read(ROOT, P)
            stages = program['increment']['workItems'][0]['closeoutSequence']
            self.assertFalse(all(stage['state'] == 'completed' for stage in stages))
            self.assertFalse(report['repositoryCandidateReady'])
        else:
            self.assertEqual(report['programStatus'], 'ready')
            self.assertEqual(report['criteria']['verified'], 8)
            self.assertEqual(report['repositoryCandidateReady'], report['checkoutClean'])
        self.assertTrue(all(host['staticReady'] for host in report['hostChecks'].values()))
        program, acceptance = _read(ROOT, P), _read(ROOT, A)
        limit = program['complexityBudget']['targets']['maxProductCodeAndTestBytes']
        percent = program['complexityBudget']['minimumProductCodeAndTestHeadroomPercent']
        self.assertGreaterEqual(limit - report['complexity']['productCodeAndTestBytes'],
                                (limit * percent + 99) // 100)
        self.assertNotRegex((ROOT / 'CONTEXT.md').read_text(encoding='utf-8'),
                            r'#/[^`\n]+/[0-9]+(?:/|`)')
        self.assertNotIn('maxControlBytes', program['complexityBudget']['targets'])
        gate = program['releaseProcedure']['orderedGates'][1]['condition']
        for marker in ('original host or session records', 'context-isolated, outcome-bound, identity-neutral'):
            self.assertIn(marker, gate)
            self.assertIn(marker, acceptance['candidateVerification']['rule'])

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
        with _fixture() as root:
            projection = _read(root, P)['hostProjections'][0]
            target = root / projection['skill']
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
                    projection['metadataFiles'],
                )
            self.assertIsNone(digest)
            self.assert_has(errors, 'package declared file is unsafe')
        with _fixture() as root:
            projection = _read(root, P)['hostProjections'][0]
            target = root / projection['skill']
            with target.open('wb') as stream:
                stream.truncate(2_000_000)
            original_text, original_bytes = Path.read_text, Path.read_bytes

            def reject_text(path, *args, **kwargs):
                if path == target:
                    raise AssertionError('oversized Skill was read without a bound')
                return original_text(path, *args, **kwargs)

            def reject_bytes(path):
                if path == target:
                    raise AssertionError('oversized package file was read without a bound')
                return original_bytes(path)

            with patch.object(Path, 'read_text', reject_text), \
                    patch.object(Path, 'read_bytes', reject_bytes):
                errors = host_check(root, 'codex')['errors']
            self.assert_has(errors, 'Skill exceeds budget', 'package identity is unavailable')

    def test_projection_evidence_rejects_drift_and_relocation(self):
        with _fixture() as root:
            locator = 'evals/observations/2026-08-24-v20-codex-gt01.json'
            _attach_evidence(root, 'R3', locator)
            observation = _read(root, locator)
            observation['projectionIdentity']['skillSha256'] = '0' * 64
            _write(root, locator, observation)
            _rehash(root, locator)
            self.assert_has(verify_product(root)['errors'], 'skillSha256 does not match')

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
            locator = 'evals/observations/2026-08-24-v20-codex-gt01.json'
            observation = _read(root, locator)
            source = _read(root, SOURCE)
            source['records']['GT-01']['payload'] = 'tampered'
            _write(root, SOURCE, source)
            observation['goldenTaskSha256'] = '0' * 64
            errors, _ = _observe(root, locator, observation)
            self.assert_has(
                errors,
                'Golden Task digest mismatch',
                'sourceEvidence[0] is invalid',
            )
            record = source['records']['GT-01']
            observation['goldenTaskSha256'] = record['goldenTaskSha256']
            observation['transcriptOrEventEvidence'][0]['sha256'] = _digest(record)
            self.assert_has(_observe(root, locator, observation)[0],
                            'sourceEvidence[0] is invalid')

        payload = _read(ROOT, SOURCE)['records']['GT-02']['payload']
        self.assertEqual(payload['captureProtocol'], 'direct-host-material-events-v1')
        current_gt08 = _read(
            ROOT, 'evals/observations/2026-08-24-v20-codex-gt08.json'
        )
        self.assertEqual(current_gt08['decision'], {'state': 'passed'})
        self.assertEqual(
            current_gt08['behaviorDecisions']['required'][
                'resolve-current-official-guidance'
            ],
            'observed',
        )

    def test_failed_sample_narrows_claim(self):
        with _fixture() as root:
            _attach_evidence(
                root, 'Q1',
                'evals/observations/2026-08-24-v20-codex-gt03.json',
            )
            acceptance = _read(root, A)
            criterion = next(
                item for item in acceptance['criteria'] if item['id'] == 'Q1'
            )
            criterion['evidence'][0]['claim'] = 'overclaim'
            _write(root, A, acceptance)
            self.assert_has(
                verify_product(root)['errors'],
                'claim must equal claimLimit.statement',
            )
        self.assertEqual(
            _read(ROOT, A)['claimCeiling']['retainedBehaviorExclusions'], ['GT-07:cleanup']
        )
        self.rejected(A, 'retained behavior exclusions', lambda v:
                      v['claimCeiling'].update(
                          retainedBehaviorExclusions=['GT-07:stale exclusion']))
        with _fixture() as root:
            locator = 'evals/observations/2026-08-24-v20-claude-gt07.json'
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
            locator = 'evals/observations/2026-08-24-v20-codex-gt01.json'
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
                self.assert_has(verify_product(root)['errors'],
                                'derived surface markers or structure')
            workflow.write_bytes(body)
            readme = (root / 'README.md').read_text(encoding='utf-8')
            (root / 'README.md').write_text(
                readme.replace('restart the desktop app', 'skip reload'), encoding='utf-8')
            self.assert_has(verify_product(root)['errors'], 'derived surface markers')
            (root / 'README.md').write_text(readme, encoding='utf-8')
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
            self.assert_has(verify_product(root)['errors'], 'goalModePrompt.mapsTo',
                            'increment.acceptanceIds', 'workItems[0].acceptanceIds',
                            'closeoutSequence', 'required release gate sequence',
                            'workStageIds', 'objective is not the canonical projection',
                            'objective does not preserve')

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
        with _fixture() as root:
            report = verify_product(root)
            self.assert_has(
                report['errors'],
                'tracked repository surface is unavailable',
            )
            measured = report['complexity']['productCodeAndTestBytes']
            program = _read(root, P)
            percent = program['complexityBudget']['minimumProductCodeAndTestHeadroomPercent']
            valid_limit = (measured * 100 + 99 - percent) // (100 - percent)
            while valid_limit - measured < (valid_limit * percent + 99) // 100:
                valid_limit += 1
            program['complexityBudget']['targets']['maxProductCodeAndTestBytes'] = valid_limit - 1
            _write(root, P, program)
            self.assert_has(verify_product(root)['errors'], 'complexity headroom too small')
            program['complexityBudget']['targets']['maxProductCodeAndTestBytes'] = valid_limit
            _write(root, P, program)
            self.assertTrue(_lacks(
                verify_product(root)['errors'], 'complexity headroom too small'
            ))

        with _indexed_fixture() as root:
            revision = subprocess.check_output(
                ['git', '-C', str(root), 'rev-parse', 'HEAD'],
                text=True,
            ).strip()
            (root / 'vendor').mkdir()
            subprocess.run([
                'git', '-C', str(root), 'update-index', '--add',
                '--cacheinfo', '160000', revision, 'vendor',
            ], check=True)
            self.assert_has(
                verify_product(root)['errors'],
                'tracked repository entry is not a regular file: vendor (mode 160000)',
            )

        with _indexed_fixture() as root:
            (root / '.DS_Store').write_bytes(b'\0retired_module\0')
            sparse_locator = 'docs/license-policy.md'
            subprocess.run([
                'git', '-C', str(root), 'update-index', '--skip-worktree',
                sparse_locator,
            ], check=True)
            (root / sparse_locator).unlink()
            status = subprocess.check_output([
                'git', '-C', str(root), 'status', '--porcelain=v1',
                '--untracked-files=all',
            ])
            self.assertEqual(status, b'')
            report = verify_product(root)
            errors = report['errors']
            self.assert_has(
                errors,
                f'active tree file is unreadable: {sparse_locator}',
            )
            self.assertTrue(_lacks(errors, '.DS_Store'), errors)
            self.assertFalse(report['checkoutClean'])
            (root / sparse_locator).write_text('local hidden drift\n', encoding='utf-8')
            self.assertEqual(subprocess.check_output([
                'git', '-C', str(root), 'status', '--porcelain=v1',
                '--untracked-files=all',
            ]), b'')
            hidden_report = verify_product(root)
            self.assertFalse(hidden_report['checkoutClean'])
            self.assertTrue(_lacks(
                hidden_report['errors'], sparse_locator
            ), hidden_report['errors'])
            original = subprocess.check_output([
                'git', '-C', str(root), 'show', f'HEAD:{sparse_locator}',
            ])
            (root / sparse_locator).write_bytes(original)
            subprocess.run([
                'git', '-C', str(root), 'update-index', '--no-skip-worktree',
                '--assume-unchanged', sparse_locator,
            ], check=True)
            (root / sparse_locator).write_text('assumed local drift\n', encoding='utf-8')
            self.assertEqual(subprocess.check_output([
                'git', '-C', str(root), 'status', '--porcelain=v1',
                '--untracked-files=all',
            ]), b'')
            self.assertFalse(verify_product(root)['checkoutClean'])

        with _indexed_fixture() as root:
            locator = 'oversized-static-surface.bin'
            oversized = root / locator
            with oversized.open('wb') as stream:
                stream.truncate(2_000_000)
            subprocess.run([
                'git', '-C', str(root), 'add', '-f', locator,
            ], check=True)
            unbounded_read = Path.read_bytes

            def reject_unbounded_read(path):
                if path == oversized:
                    raise AssertionError('oversized tracked file was read without a bound')
                return unbounded_read(path)

            with patch.object(Path, 'read_bytes', reject_unbounded_read):
                errors = verify_product(root)['errors']
            self.assert_has(
                errors,
                f'active tree identity scan is indeterminate: {locator}',
            )

        with _indexed_fixture() as root:
            locator = 'docs/license-policy.md'
            (root / locator).unlink()
            (root / locator).mkdir()
            self.assert_has(
                verify_product(root)['errors'],
                f'active tree path is not a regular file: {locator}',
            )

        for payload in (
            b'\xff\xfeX', b'\xfe\xffX',
            b'\xff\xfe\x00\x00X', b'\x00\x00\xfe\xffX',
        ):
            with self.subTest(malformed_utf16=payload[:2]):
                self.assert_has(
                    _retired_byte_errors(payload),
                    'active tree file is undecodable: sample.txt',
                )
        historical_text = 'Retired Product and retired-product'
        for payload in (
            historical_text.encode('utf-16'),
            b'\xfe\xff' + historical_text.encode('utf-16-be'),
            historical_text.encode('utf-32'),
            b'\x00\x00\xfe\xff' + historical_text.encode('utf-32-be'),
            b'\xef\xbb\xbf' + historical_text.encode('utf-8'),
            'Ｒｅｔｉｒｅｄ Ｐｒｏｄｕｃｔ and '
            'ｒｅｔｉｒｅｄ－ｐｒｏｄｕｃｔ'.encode('utf-8'),
        ):
            with self.subTest(valid_utf16=payload[:2]):
                self.assert_has(
                    _retired_byte_errors(payload),
                    'superseded identity remains in active tree: sample.txt',
                )
        encoded_python_cases = (
            ('script', b'\xef\xbb\xbf' + (
                '#!/usr/bin/env python\nimport @\n'.replace('@', 'retired_module')
            ).encode()),
            ('sample.py', (
                '# -*- coding: gb18030 -*-\n'
                'import ｒｅｔｉｒｅｄ＿ｍｏｄｕｌｅ\n'
            ).encode('gb18030')),
        )
        for locator, payload in encoded_python_cases:
            with self.subTest(encoded_python=locator):
                self.assert_has(
                    _retired_byte_errors(payload, locator),
                    f'superseded identity remains in active tree: {locator}',
                )
        mixed_command = (
            '汉字' * 100 + '\npython -m @\n'
        ).replace('@', 'retired_module')
        for encoding in ('utf-16-le', 'utf-16-be', 'utf-32-le', 'utf-32-be'):
            with self.subTest(ambiguous_nul_text=encoding):
                self.assert_has(
                    _retired_byte_errors(mixed_command.encode(encoding), 'sample.sh'),
                    'active tree file is undecodable: sample.sh',
                )
        safe_utf8 = ('汉字' * 100 + '\npython -m retired_module_other\n').encode()
        self.assertTrue(_lacks(
            _retired_byte_errors(safe_utf8, 'sample.sh'),
            'superseded identity', 'undecodable',
        ))
        safe_gb18030 = (
            '# -*- coding: gb18030 -*-\n'
            '# import ｒｅｔｉｒｅｄ＿ｍｏｄｕｌｅ\n'
        ).encode('gb18030')
        self.assertTrue(_lacks(
            _retired_byte_errors(safe_gb18030, 'sample.py'), 'superseded identity'
        ))

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            locator = 'sample.txt'
            target = root / locator
            target.write_text('safe\n', encoding='utf-8')
            history = [json.dumps(RETIRED), '# Retired Product\n']
            original_open = __import__('os').open

            def deny_target(path, flags):
                if Path(path) == target:
                    raise PermissionError('denied by fixture')
                return original_open(path, flags)

            with patch('yiyuan_accord.identity.subprocess.check_output', side_effect=history), \
                    patch('yiyuan_accord.identity.os.open', deny_target):
                errors = active_tree_errors(root, [locator], '0' * 40)
            self.assert_has(errors, 'active tree file is unreadable: sample.txt')

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            locator = 'sample.txt'
            target = root / locator
            target.write_text('safe\n', encoding='utf-8')
            history = [json.dumps(RETIRED), '# Retired Product\n']
            original_is_symlink = Path.is_symlink
            original_open = __import__('os').open

            def active_symlink(path):
                return path == target or original_is_symlink(path)

            def never_follow_active(path, flags):
                if Path(path) == target:
                    raise AssertionError('active-tree symlink target was read')
                return original_open(path, flags)

            with patch('yiyuan_accord.identity.subprocess.check_output', side_effect=history), \
                    patch.object(Path, 'is_symlink', active_symlink), \
                    patch('yiyuan_accord.identity.os.open', never_follow_active):
                errors = active_tree_errors(root, [locator], '0' * 40)
            self.assertEqual(errors, ['symbolic link is not admitted in active tree: sample.txt'])

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

    def test_conservative_identity_boundary_allows_declared_safe_surfaces(self):
        errors = verify_product(ROOT)['errors']
        self.assertTrue(_lacks(
            errors, 'superseded identity', 'identity scan is indeterminate', 'test markers'
        ), errors)

        safe_cases = (
            ('sample.py', '# retired_module\n# import retired_module\nvalue = 1\n'),
            ('sample.py', '# Retired Product\n# retired-product\nvalue = 1\n'),
            ('sample.py', 'retired_module_other = "retired_module_other"\n'),
            ('sample.py', 'value = "Retired Productive retired-product_other"\n'),
            ('sample.py', 'value = "retired-product-other"\n'),
            ('sample.py', 'value = f"retired_{name}module"\n'),
            ('sample.py', 'value = rf"retired_\\u006dodule"\n'),
            ('sample.py', 'value = fr"Retired\\x20Product"\n'),
            ('sample.py', 'value = (' + "'safe' + " * 999 + "'safe')\n"),
            ('sample.py', 'value = ' + _balanced_add(
                ['name'] + ["'safe'"] * 5_000
            ) + '\n'),
            ('sample.py', 'value = ' + _balanced_add(["'safe'"] * 4_096) + '\n'),
            ('sample.txt', 'retired_module_other xretired_module harnessed\n'),
            ('sample.txt', 'Retired Productive retired-product_other\n'),
            ('sample.txt', 'retired-product-other\n'),
            ('sample.json', '{"module":"retired_module_other"}\n'),
            ('sample.json', '{"module":"retired_\\u006dodule"}\n'),
            ('sample.yaml', 'module: retired_module_other\n'),
            ('sample.yaml', 'module: retired_\\x6dodule\n'),
            ('sample.sh', 'printf %s retired_module_other\n'),
        )
        for locator, body in safe_cases:
            with self.subTest(safe=locator):
                self.assertTrue(_lacks(
                    _retired_raw_errors(body, locator),
                    'superseded identity', 'indeterminate',
                ))

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            locator = 'research/reviews/reference.md'
            path = root / locator
            path.parent.mkdir(parents=True)
            path.write_text('Historical retired_module reference.\n', encoding='utf-8')
            history = [json.dumps(RETIRED), '# Retired Product\n']
            with patch(
                'yiyuan_accord.identity.subprocess.check_output',
                side_effect=history,
            ):
                admitted = active_tree_errors(
                    root, [locator], '0' * 40, {locator}
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

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            locator = 'retired_module/config.txt'
            path = root / locator
            path.parent.mkdir(parents=True)
            path.write_text('safe\n', encoding='utf-8')
            history = [json.dumps(RETIRED), '# Retired Product\n']
            with patch(
                'yiyuan_accord.identity.subprocess.check_output',
                side_effect=history,
            ):
                errors = active_tree_errors(root, [locator], '0' * 40)
            self.assert_has(errors, 'superseded identity remains')

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            locator = 'docs/new-surface.txt'
            path = root / locator
            path.parent.mkdir(parents=True)
            path.write_text('retired_module\n', encoding='utf-8')
            history = [json.dumps(RETIRED), '# Retired Product\n']
            with patch(
                'yiyuan_accord.identity.subprocess.check_output',
                side_effect=history,
            ):
                errors = active_tree_errors(root, [locator], '0' * 40)
            self.assert_has(
                errors,
                'superseded identity remains in active tree: docs/new-surface.txt',
            )
            with patch(
                'yiyuan_accord.identity.subprocess.check_output',
                side_effect=history,
            ):
                still_active = active_tree_errors(
                    root, [locator], '0' * 40, {locator}
                )
            self.assert_has(
                still_active,
                'superseded identity remains in active tree: docs/new-surface.txt',
            )

    def test_retired_residue_and_duplicate_json_fail_closed(self):
        with _fixture() as root:
            retired = 'yiyuan_accord/task_validator_o4_continuous_self_correction_v3.py'
            (root / retired).mkdir()
            (root / '.tmp').mkdir()
            self.assert_has(verify_product(root)['errors'],
                            f'forbidden active path remains: {retired}', 'known task residue')
        self.assert_has(_retired_raw_errors('retired-product', 'README.md'),
                        'superseded identity remains')
        with _fixture() as root:
            (root / P).write_text('{"schema":2,"schema":2}\n', encoding='utf-8')
            self.assert_has(verify_product(root)['errors'], 'duplicate JSON key')
        with _fixture() as root:
            target = root / P
            with target.open('wb') as stream:
                stream.truncate(2_000_000)
            unbounded_read = Path.read_bytes

            def reject_unbounded_json(path):
                if path == target:
                    raise AssertionError('oversized JSON was read without a bound')
                return unbounded_read(path)

            with patch.object(Path, 'read_bytes', reject_unbounded_json):
                errors = verify_product(root)['errors']
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
            unbounded_read = Path.read_bytes

            def reject_unbounded_input(path):
                if path == target:
                    raise AssertionError('oversized input was hashed without a bound')
                return unbounded_read(path)

            with patch.object(Path, 'read_bytes', reject_unbounded_input):
                errors = verify_product(root)['errors']
            self.assert_has(errors, 'inputEvidence[6] digest source is oversized')
