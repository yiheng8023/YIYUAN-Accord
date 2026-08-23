from contextlib import contextmanager
import hashlib, json, shutil, tempfile, unittest
from pathlib import Path
from unittest.mock import patch
from yiyuan_accord.control import host_check, verify_product
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

def _rehash(root, locator):
    acceptance = _read(root, A)
    digest = hashlib.sha256((root / locator).read_bytes()).hexdigest()
    for criterion in acceptance['criteria']:
        for item in criterion['evidence']:
            if item['locator'] == locator:
                item['sha256'] = digest
    _write(root, A, acceptance)

def _retired_errors(body, locator='sample.txt'):
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        (root / locator).write_text(body.replace('@', 'retired_module'), encoding='utf-8')
        history = [json.dumps(RETIRED), '# Retired Product\n']
        with patch('yiyuan_accord.identity.subprocess.check_output', side_effect=history):
            return active_tree_errors(root, [locator], '0' * 40)

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
        program, acceptance = _read(ROOT, P), _read(ROOT, A)
        limit = program['complexityBudget']['targets']['maxProductCodeAndTestBytes']
        self.assertGreaterEqual(limit - report['complexity']['productCodeAndTestBytes'], (limit + 19) // 20)
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
            locator = 'evals/observations/2026-08-24-v20-codex-gt01.json'
            observation = _read(root, locator)
            observation['projectionIdentity']['skillSha256'] = '0' * 64
            _write(root, locator, observation)
            _rehash(root, locator)
            self.assert_has(verify_product(root)['errors'], 'skillSha256 does not match')

    def test_representative_sample_binds_projection_source_and_task(self):
        with _fixture() as root:
            errors = verify_product(root)['errors']
            self.assertFalse(any(('representative' in item or 'R3 evidence' in item for item in errors)))
            acceptance = _read(root, A)
            acceptance['criteria'][2]['passRule'] += ' Expanded after capture.'
            _write(root, A, acceptance)
            self.assert_has(verify_product(root)['errors'], 'evaluation contract digest mismatch')
            source = _read(root, SOURCE)
            capture = json.loads(source['records']['GT-02']['payload'])['capture']
            self.assertIn('Skill search remained enabled', capture)
            self.assertNotIn('non-target Skill search disabled', capture)
            current_gt08 = _read(root, 'evals/observations/2026-08-24-v20-codex-gt08.json')
            self.assertEqual(current_gt08['decision'], {'state': 'passed'})
            self.assertEqual(
                current_gt08['behaviorDecisions']['required']['resolve-current-official-guidance'],
                'observed')
            source['records']['GT-01']['payload'] = 'tampered'
            _write(root, SOURCE, source)
            acceptance = _read(root, A)
            acceptance['criteria'][7]['evidence'].pop()
            _write(root, A, acceptance)
            self.assert_has(verify_product(root)['errors'], 'sourceEvidence', 'Q4 representative coverage')

    def test_failed_sample_narrows_claim(self):
        self.rejected(A, 'claim must equal claimLimit.statement', lambda v:
                      ((c := next(c for c in v['criteria'] if c['id'] == 'Q1')).update(assessment='planned'),
                       next(iter(c['evidence'])).update(claim='overclaim')))
        self.rejected(A, 'retained behavior exclusions', lambda v:
                      v['claimCeiling'].update(retainedBehaviorExclusions=[]))
        with _fixture() as root:
            locator = 'evals/observations/2026-08-24-v20-claude-gt07.json'
            observation = _read(root, locator)
            observation['criterionDecisions']['Q4'] = 'accepted'
            observation['claimLimit'] = {'retainedFailure': False, 'excludedClaims': [], 'statement': 'all supported'}
            observation['residue'] = [{'kind': 'task-owned-residue'}]
            _write(root, locator, observation)
            _rehash(root, locator)
            self.assert_has(verify_product(root)['errors'], 'criterionDecisions', 'claimLimit contradicts', 'cleanup contradicts residue')
            locator = 'evals/observations/2026-08-24-v20-codex-gt01.json'
            observation = _read(root, locator)
            observation['decision'] = {'state': 'failed'}
            _write(root, locator, observation)
            _rehash(root, locator)
            self.assert_has(verify_product(root)['errors'], 'must-pass tasks')

    def test_plan_process_acceptance_and_release_order_stay_aligned(self):
        with _fixture() as root:
            program = _read(root, P)
            workflow = root / '.github/workflows/validate.yml'
            body = workflow.read_text(encoding='utf-8')
            mutations = (
                ('permissions:\n  contents: read', 'permissions: write-all\n# permissions: contents: read'),
                ('run: python -B -m yiyuan_accord verify',
                 'run: echo disabled # python -B -m yiyuan_accord verify'),
            )
            for old, new in mutations:
                workflow.write_text(body.replace(old, new), encoding='utf-8')
                self.assert_has(verify_product(root)['errors'],
                                'derived surface markers or structure')
            workflow.write_text(body, encoding='utf-8')
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

    def test_legitimate_host_language_and_additional_regressions_are_allowed(self):
        errors = verify_product(ROOT)['errors']
        self.assertFalse(any('superseded identity' in item for item in errors), errors)
        self.assertFalse(any('test markers' in item for item in errors), errors)
        for locator, body in (
            ('sample.py', '# import @\n# python -m @\n# @.py\n# @\nif\n'
             '@_other = "@_other"\n'),
            ('sample.toml', 'entry = "@_other"\n'),
            ('sample.py', 'if True:\n    pass\n  pass\n# @\n'),
            ('sample.py', 'value=' + "'safe'+" * 999 + "'safe'\n"),
            ('sample.py', 'value=f"@_other"\nvalue=(\n"safe_"+"module"'),
            ('sample.txt', 'python -Xm@\npython -c "print(\'@_other\')"\n'
             'python -c "# import @"\npython -c "x=1 # @"\n'
             'python -c "# module=\'@\'"\npython -c "# @.py"\n'),
        ):
            self.assertFalse(_retired_errors(body, locator))

    def test_retired_module_identity_contexts_are_rejected(self):
        cases = {
            'sample.py': (
                'from @ import item\n', 'import os as @\n',
                'try: pass\nexcept Exception as @: pass\n', 'global @\n',
                'match value:\n    case {"key": @}: pass\n',
                'class Box[@]: pass\n', 'value = b"@"\n',
                'target = "retired_" + "module"\n__import__(target)\n',
                'import subprocess\nsubprocess.run("python -m @", shell=True)\n',
                'import subprocess\nsubprocess.run(["python", "-Im@"])\n',
                'exec("import @")\n',
                'from pathlib import Path\nPath("@/__init__.py")\n',
                'entry = "uvicorn @:app"\n', 'import @\nif\n',
                'value=' + "'safe'+" * 999 + "'safe'+' '+'retired_'+'module'\n",
                'value=' + "'safe'+" * 4096 + "'safe'\n",
                'value=f"@"\n', 'value=(\n"retired_"+"module"',
            ),
            'sample.txt': (
                '@/path.py\n', '@.pyi\n', '@.cli:main\n',
                'python -m@\n', 'python -Im@\n',
                *(f'python -m pydoc {flag}@\n' for flag in ('', '-w ')),
            ),
            'sample.toml': (
                'entry = "@"\n', 'entry = "@.cli"\n', 'module = "@"\n',
                'command = "python -m @"\n',
                'command = [\n  "python",\n  "-m", # module flag\n  "@",\n]\n',
                'command = ["python", "-c", "__import__(\'@\')"]\n',
            ),
            'sample.json': (
                '{"pythonModule":"@"}\n',
                '{"command":"python -m @"}\n',
                '{"scripts":{"verify":"python -m @"}}\n',
                '{"command":["python","-c","__import__(\'@\')"]}\n',
            ),
            'sample.yaml': (
                'command: "python -m @"\n',
                'run: "python -m @"\n',
                'command:\n  - python\n  - -m\n  - &target @\n',
                "description: don't stop\ncommand: [python, -m, @]\n",
                'command:\n  - python\n  - -c\n    # code follows\n\n  - |\n'
                '    import importlib\n'
                '    importlib.import_module("@")\n',
            ),
            'sample.sh': (
                'python -m \\\n@\n', 'python -c "__import__(\'@\')"\n',
                'python -c "import runpy; runpy.run_module(\'@\')"\n',
                "python -c 'import importlib\nimportlib.import_module(\"@\")'\n",
                *(f'python -c "__import__(\'retired_\'{x}\'module\')"\n'
                  for x in ('+', ' ')),
                *(f'python -m @{x}\n' for x in '; |more & >out.txt'.split()),
            ),
        }
        for locator, bodies in cases.items():
            for body in bodies:
                with self.subTest(body=body):
                    self.assert_has(_retired_errors(body, locator),
                                    'superseded identity remains')

    def test_retired_residue_and_duplicate_json_fail_closed(self):
        with _fixture() as root:
            retired = 'yiyuan_accord/task_validator_o4_continuous_self_correction_v3.py'
            (root / retired).mkdir()
            (root / '.tmp').mkdir()
            self.assert_has(verify_product(root)['errors'],
                            f'forbidden active path remains: {retired}', 'known task residue')
        self.assert_has(_retired_errors('retired-product', 'README.md'),
                        'superseded identity remains')
        with _fixture() as root:
            (root / P).write_text('{"schema":2,"schema":2}\n', encoding='utf-8')
            self.assert_has(verify_product(root)['errors'], 'duplicate JSON key')
