"""Fixture Git commands must never inherit a caller's repository routing."""

import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from tests.product import test_product_control as fixtures
from tests.product.git_fixture import owned_git_environment


class SnapshotCheckTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='accord-static-snapshot-')
        self.addCleanup(self.temporary.cleanup)
        self.base = Path(self.temporary.name).resolve()
        self.root = self.base / 'source'
        GitFixtureIsolationTests().repository(self.root)
        declaration = self.root / 'product/development.json'
        declaration.parent.mkdir()
        declaration.write_text('{"schema":"yiyuan-accord-development/v5"}', encoding='utf-8')
        for args in (['add', '.'], ['-c', 'user.name=Fixture',
                     '-c', 'user.email=fixture@example.invalid', 'commit',
                     '--quiet', '-m', 'Current development fixture']):
            subprocess.run(['git', '-C', str(self.root), *args],
                           env=owned_git_environment(), check=True, capture_output=True)
        self.head = subprocess.check_output(['git', '-C', str(self.root), 'rev-parse', 'HEAD'],
                                            env=owned_git_environment()).decode().strip()
        self.work = self.base / 'result'

    def run_check(self, *, checks=None, archive=False, work=None, head=None):
        from yiyuan_accord import __main__ as cli
        good = lambda *args: {'valid': True, 'errors': []}
        checks = checks or (good, good, good)
        with patch.object(cli, 'verify_development', side_effect=checks[0]), \
                patch.object(cli, 'verify_product', side_effect=checks[1]), \
                patch.object(cli, 'host_check', side_effect=checks[2]):
            return cli.check_snapshot(self.root, work or self.work,
                                      head or self.head, 'codex', archive)

    def run_cli(self, work, *options, development=None):
        from yiyuan_accord import __main__ as cli
        output = io.StringIO()
        good = {'valid': True, 'errors': []}
        arguments = ['yiyuan_accord', 'check-snapshot', '--root', str(self.root),
                     '--work-dir', str(work), '--expected-head', self.head,
                     '--adapter', 'codex', *options]
        with patch.object(sys, 'argv', arguments), patch.object(sys, 'stdout', output), \
                patch.object(cli, 'verify_development', return_value=development or good), \
                patch.object(cli, 'verify_product', return_value=good), \
                patch.object(cli, 'host_check', return_value=good):
            status = cli.main()
        return status, json.loads(output.getvalue())

    def test_snapshot_summary_keeps_full_reports_and_default_output(self):
        for index, options in enumerate(((), ('--json',), ('--summary',),
                                         ('--summary', '--json'))):
            with self.subTest(options=options):
                work = self.base / ('output-' + str(index))
                status, output = self.run_cli(work, *options, '--archive')
                saved = json.loads((work / 'result.json').read_text(encoding='utf-8'))
                self.assertEqual(status, 0)
                self.assertTrue(output['valid'])
                self.assertEqual(output['cleanup'], 'removed')
                self.assertTrue(output['sourceStable'])
                self.assertTrue(output['snapshotStable'])
                self.assertEqual(output['workDirectory'], str(work))
                self.assertEqual(len(output['checks']), 3)
                self.assertEqual(set(saved['source']['files']),
                                 {'keep.txt', 'product/development.json'})
                self.assertEqual(output['archiveSha256'],
                                 hashlib.sha256((work / 'source.zip').read_bytes()).hexdigest())
                self.assertFalse((work / 'repo').exists())
                if '--summary' in options:
                    self.assertNotIn('source', output)
                    self.assertEqual(output, {k: v for k, v in saved.items() if k != 'source'})
                else:
                    self.assertEqual(output, saved)

    def test_snapshot_summary_preserves_failed_check_and_detailed_error(self):
        original = {'valid': False, 'errors': ['controlled source mismatch']}
        status, output = self.run_cli(self.work, '--summary', development=original)
        self.assertEqual(status, 1)
        self.assertFalse(output['valid'])
        self.assertTrue(output['errors'])
        self.assertEqual(output['checks'][0], {'name': 'development', 'valid': False})
        self.assertEqual(output['cleanup'], 'retained')
        self.assertEqual(json.loads((self.work / 'development.json').read_text()), original)
        self.assertIn('source', json.loads((self.work / 'result.json').read_text()))
        self.assertTrue((self.work / 'repo').is_dir())

    def test_snapshot_summary_preserves_preflight_failure_without_report_directory(self):
        status, output = self.run_cli(self.work, '--summary', '--expected-head', '0' * 40)
        self.assertEqual(status, 1)
        self.assertFalse(output['valid'])
        self.assertTrue(output['errors'])
        self.assertEqual(output['checks'], [])
        self.assertEqual(output['cleanup'], 'not-created')
        self.assertNotIn('workDirectory', output)
        self.assertFalse(self.work.exists())

    def test_snapshot_summary_preserves_result_write_failure(self):
        original_open = Path.open
        def refuse_result(path, mode='r', *args, **kwargs):
            if path == self.work / 'result.json' and mode == 'x':
                raise OSError('controlled result write refusal')
            return original_open(path, mode, *args, **kwargs)
        with patch.object(Path, 'open', refuse_result):
            status, output = self.run_cli(self.work, '--summary', '--json')
        self.assertEqual(status, 1)
        self.assertFalse(output['valid'])
        self.assertIn('controlled result write refusal', str(output['errors']))
        self.assertEqual(output['cleanup'], 'removed')
        self.assertFalse((self.work / 'result.json').exists())
        self.assertTrue((self.work / 'source.json').is_file())

    def test_snapshot_checks_working_bytes_preserves_index_and_archives_on_request(self):
        import zipfile
        from yiyuan_accord import __main__ as cli
        (self.root / 'keep.txt').write_text('staged', encoding='utf-8')
        subprocess.run(['git', '-C', str(self.root), 'add', 'keep.txt'],
                       env=owned_git_environment(), check=True)
        (self.root / 'keep.txt').write_bytes('working\n中文'.encode('utf-8'))
        before = GitFixtureIsolationTests().protected_bytes(self.root)
        calls = []
        def check(label):
            def run(root, *args):
                self.assertEqual((root / 'keep.txt').read_bytes(), 'working\n中文'.encode())
                calls.append((label, args))
                return {'valid': True, 'errors': []}
            return run
        report = self.run_check(checks=tuple(check(x) for x in ('development', 'product', 'host')),
                                archive=True)
        self.assertTrue(report['valid'], report)
        self.assertEqual(calls, [('development', ()), ('product', ()), ('host', ('codex',))])
        self.assertEqual(report['cleanup'], 'removed')
        self.assertFalse((self.work / 'repo').exists())
        self.assertEqual(GitFixtureIsolationTests().protected_bytes(self.root), before)
        with zipfile.ZipFile(self.work / 'source.zip') as saved:
            self.assertEqual(saved.namelist(), ['keep.txt', 'product/development.json'])
            self.assertEqual(saved.read('keep.txt'), (self.root / 'keep.txt').read_bytes())
        self.assertEqual(json.loads((self.work / 'result.json').read_text())['valid'], True)

    def test_snapshot_ignores_foreign_git_routes(self):
        from yiyuan_accord.identity import _bounded_git_bytes
        foreign = self.base / 'foreign'
        GitFixtureIsolationTests().repository(foreign)
        before = GitFixtureIsolationTests().protected_bytes(foreign)
        (self.root / 'keep.txt').write_bytes(b'working update')
        def real_history_check(root, *args):
            self.assertEqual(_bounded_git_bytes(root, ('show', 'HEAD:keep.txt')), b'source')
            self.assertIn(b'keep.txt', _bounded_git_bytes(root, ('diff', '--name-only')))
            return {'valid': True, 'errors': []}
        routes = {'GIT_DIR': str(foreign / '.git'), 'GIT_WORK_TREE': str(foreign),
                  'GIT_INDEX_FILE': str(foreign / '.git/index')}
        with patch.dict(os.environ, routes):
            report = self.run_check(checks=(real_history_check,
                                          lambda *a: {'valid': True, 'errors': []},
                                          lambda *a: {'valid': True, 'errors': []}))
        self.assertEqual(GitFixtureIsolationTests().protected_bytes(foreign), before)
        self.assertTrue(report['valid'], report)

    def test_snapshot_rejects_out_of_scope_declarations_before_checks_or_writes(self):
        declaration = self.root / 'product/development.json'
        for index, data in enumerate((b'{}', b'{"schema":"yiyuan-accord-development/v4"}',
                                      b'[]', b'{', None,
                                      b'{"schema":"x","schema":"yiyuan-accord-development/v5"}')):
            with self.subTest(data=data):
                if data is None:
                    declaration.unlink()
                else:
                    declaration.write_bytes(data)
                calls = []
                def check(*args):
                    calls.append(args)
                    return {'valid': True, 'errors': []}
                work = self.base / ('scope-' + str(index))
                report = self.run_check(work=work, checks=(check, check, check))
                self.assertFalse(report['valid'], report)
                self.assertEqual(calls, [])
                self.assertFalse(work.exists())

    def test_snapshot_rejects_wrong_head_existing_overlap_and_untracked_source(self):
        existing = self.base / 'existing';existing.mkdir()
        (existing / 'keep').write_text('protected')
        for arguments in ({'head': '0' * 40}, {'work': existing},
                          {'work': self.root / 'nested'}, {'work': self.base / 'absent/child'}):
            with self.subTest(arguments=arguments):
                report = self.run_check(**arguments)
                self.assertFalse(report['valid'], report)
        self.assertEqual((existing / 'keep').read_text(), 'protected')
        (self.root / 'untracked.txt').write_text('input')
        self.assertFalse(self.run_check()['valid'])
        self.assertFalse(self.work.exists())

    def test_snapshot_rejects_deleted_hidden_and_new_index_paths(self):
        subprocess.run(['git', '-C', str(self.root), 'update-index', '--assume-unchanged', 'keep.txt'],
                       env=owned_git_environment(), check=True)
        self.assertFalse(self.run_check()['valid'])
        subprocess.run(['git', '-C', str(self.root), 'update-index', '--no-assume-unchanged', 'keep.txt'],
                       env=owned_git_environment(), check=True)
        data = (self.root / 'keep.txt').read_bytes();(self.root / 'keep.txt').unlink()
        self.assertFalse(self.run_check()['valid'])
        (self.root / 'keep.txt').write_bytes(data)
        (self.root / 'added.txt').write_text('new')
        subprocess.run(['git', '-C', str(self.root), 'add', 'added.txt'],
                       env=owned_git_environment(), check=True)
        self.assertFalse(self.run_check()['valid'])
        self.assertFalse(self.work.exists())

    def test_snapshot_rejects_nonregular_git_mode_and_reparse_path(self):
        from types import SimpleNamespace
        from yiyuan_accord import __main__ as cli
        blob = subprocess.check_output(['git', '-C', str(self.root), 'rev-parse', 'HEAD:keep.txt'],
                                       env=owned_git_environment()).decode().strip()
        subprocess.run(['git', '-C', str(self.root), 'update-index', '--cacheinfo',
                        '120000,' + blob + ',keep.txt'], env=owned_git_environment(), check=True)
        self.assertFalse(self.run_check()['valid'])
        self.assertFalse(self.work.exists())
        with patch.object(Path, 'lstat', return_value=SimpleNamespace(st_mode=0o100644,
                                                                    st_file_attributes=1024)):
            with self.assertRaisesRegex(ValueError, 'reparse'):
                cli._snapshot_plain_path(self.root)

    def test_snapshot_keeps_failed_check_and_cleanup_evidence(self):
        from yiyuan_accord import __main__ as cli
        for index, failure in enumerate(({'valid': False, 'errors': ['original']},
                                          {'valid': 'true', 'errors': []},
                                          {'valid': True, 'errors': ['contradiction']})):
            with self.subTest(failure=failure):
                work = self.base / ('failure-' + str(index))
                report = self.run_check(work=work, checks=(lambda *a: failure,
                                                         lambda *a: {'valid': True, 'errors': []},
                                                         lambda *a: {'valid': True, 'errors': []}))
                self.assertFalse(report['valid'])
                self.assertTrue((work / 'repo/keep.txt').is_file())
                self.assertEqual(json.loads((work / 'development.json').read_text()), failure)
        with patch.object(cli.shutil, 'rmtree', side_effect=OSError('controlled cleanup refusal')):
            report = self.run_check()
        self.assertFalse(report['valid'])
        self.assertTrue((self.work / 'repo').is_dir())
        self.assertIn('controlled cleanup refusal', str(report['errors']))

    def test_snapshot_keeps_checker_exception_and_observed_drift(self):
        def broken(*args):raise RuntimeError('controlled checker failure')
        report = self.run_check(checks=(broken, broken, broken))
        self.assertFalse(report['valid'])
        self.assertIn('RuntimeError', str(report['errors']))
        self.assertTrue((self.work / 'result.json').is_file())
        def change_source(*args):
            (self.root / 'keep.txt').write_text('changed during check')
            return {'valid': True, 'errors': []}
        report = self.run_check(work=self.base / 'source-drift',
                                checks=(change_source, lambda *a: {'valid': True, 'errors': []},
                                        lambda *a: {'valid': True, 'errors': []}))
        self.assertFalse(report['valid']);self.assertFalse(report['sourceStable'])
        self.assertEqual((self.root / 'keep.txt').read_text(), 'changed during check')
        def change_copy(root, *args):
            (root / 'keep.txt').write_text('changed copy')
            return {'valid': True, 'errors': []}
        report = self.run_check(work=self.base / 'snapshot-drift',
                                checks=(change_copy, lambda *a: {'valid': True, 'errors': []},
                                        lambda *a: {'valid': True, 'errors': []}))
        self.assertFalse(report['valid']);self.assertFalse(report['snapshotStable'])


class GitFixtureIsolationTests(unittest.TestCase):
    def test_pinned_history_reads_ignore_an_unrelated_repository_route(self):
        from tests.product import test_codex_lifecycle as lifecycle_tests
        from tests.product.test_admission import CurrentDevelopmentEvidenceTests
        from tests.product.test_tool_batch_feedback import HookEventScopeTests
        expected = lifecycle_tests.legacy_close_helper_sources(
            lifecycle_tests.lifecycle.ROOT, env=owned_git_environment())
        with tempfile.TemporaryDirectory(prefix='accord-git-history-') as temporary:
            protected = Path(temporary).resolve() / 'protected'
            self.repository(protected)
            before = self.protected_bytes(protected)
            routes = {'GIT_DIR': str(protected / '.git'),
                      'GIT_WORK_TREE': str(protected),
                      'GIT_INDEX_FILE': str(protected / '.git/index')}
            with patch.dict(os.environ, {**owned_git_environment(), **routes}, clear=True):
                with self.subTest(reader='lifecycle-pinned-helper'):
                    self.assertEqual(lifecycle_tests.legacy_close_helper_sources(
                        lifecycle_tests.lifecycle.ROOT), expected)
                with self.subTest(reader='retained-hook-package'):
                    HookEventScopeTests(
                        'test_current_and_retained_packages_keep_separate_hook_registration'
                    ).test_current_and_retained_packages_keep_separate_hook_registration()
                with self.subTest(reader='admission-original-contract'):
                    reader = type('OwnedHistoryReader', (), {'root': lifecycle_tests.lifecycle.ROOT})
                    original = CurrentDevelopmentEvidenceTests.historical_contract.__func__(reader)
                    self.assertIsInstance(original['acceptance']['admission']['cases'], list)
                with self.subTest(reader='admission-original-mode-catalog'):
                    CurrentDevelopmentEvidenceTests(
                        'test_historical_mode_catalog_keeps_its_original_reading'
                    ).test_historical_mode_catalog_keeps_its_original_reading()
            self.assertEqual(self.protected_bytes(protected), before)

    def test_owned_git_maintenance_does_not_detach(self):
        with tempfile.TemporaryDirectory(prefix='accord-git-maintenance-') as temporary:
            root = Path(temporary) / 'owned'
            trace = Path(temporary) / 'trace.jsonl'
            environment = owned_git_environment()
            environment['GIT_TRACE2_EVENT'] = str(trace)
            self.repository(root, environment=environment)
            events = [json.loads(line) for line in trace.read_text(encoding='utf-8').splitlines()]
            automatic = [row['argv'] for row in events if row.get('event') == 'child_start'
                         and any(name in row.get('argv', []) for name in ('maintenance', 'gc'))]
            self.assertTrue(automatic, events)
            for command in automatic:
                self.assertNotIn('--detach', command)

    def repository(self, root, *, environment=None):
        root.mkdir()
        (root / 'keep.txt').write_text(root.name, encoding='utf-8')
        environment = owned_git_environment() if environment is None else environment
        for args in (['init', '--quiet'], ['add', '.'],
                     ['-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.invalid',
                      'commit', '--quiet', '-m', 'Initial fixture']):
            subprocess.run(['git', '-C', str(root), *args], env=environment,
                           check=True, timeout=30, capture_output=True)

    def protected_bytes(self, root):
        return {path.relative_to(root).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
                for path in root.rglob('*') if path.is_file()}

    def test_fixture_mutations_ignore_ambient_git_routes(self):
        for routing in ('all', 'work-tree', 'index'):
            with self.subTest(routing=routing), tempfile.TemporaryDirectory(prefix='accord-git-fixture-') as temporary:
                base = Path(temporary).resolve()
                protected, owned = base / 'protected', base / 'owned'
                self.repository(protected)
                self.repository(owned)
                (owned / 'keep.txt').write_text('owned update', encoding='utf-8')
                before = self.protected_bytes(protected)
                routes = {'GIT_DIR': str(protected / '.git'),
                          'GIT_WORK_TREE': str(protected),
                          'GIT_INDEX_FILE': str(protected / '.git/index')}
                if routing == 'work-tree':
                    routes = {'GIT_WORK_TREE': routes['GIT_WORK_TREE']}
                elif routing == 'index':
                    routes = {'GIT_INDEX_FILE': routes['GIT_INDEX_FILE']}
                with patch.dict(os.environ, {**owned_git_environment(), **routes}, clear=True):
                    fixtures._git(owned, 'config', 'fixture.owner', 'owned')
                    fixtures._git(owned, 'add', 'keep.txt')
                    fixtures._commit(owned, 'Owned update')
                self.assertEqual(self.protected_bytes(protected), before)
                content = subprocess.check_output(['git', '-C', str(owned), 'show', 'HEAD:keep.txt'],
                                                  env=owned_git_environment(), timeout=30)
                self.assertEqual(content, b'owned update')

    def test_fixture_clone_and_module_checkout_keep_their_owned_repository(self):
        for routing in ('all', 'work-tree', 'index'):
            with self.subTest(routing=routing), tempfile.TemporaryDirectory(prefix='accord-git-fixture-') as temporary:
                base = Path(temporary).resolve()
                protected, source = base / 'protected', base / 'source'
                self.repository(protected)
                self.repository(source)
                revision = subprocess.check_output(
                    ['git', '-C', str(source), 'rev-parse', 'HEAD'],
                    env=owned_git_environment(), timeout=30).decode().strip()
                (source / 'product').mkdir()
                (source / 'product/development.json').write_text(json.dumps({
                    'predecessorSnapshot': revision + ':product/program.json#/snapshot',
                }), encoding='utf-8')
                before = self.protected_bytes(protected)
                routes = {'GIT_DIR': str(protected / '.git'),
                          'GIT_WORK_TREE': str(protected),
                          'GIT_INDEX_FILE': str(protected / '.git/index')}
                if routing == 'work-tree':
                    routes = {'GIT_WORK_TREE': routes['GIT_WORK_TREE']}
                elif routing == 'index':
                    routes = {'GIT_INDEX_FILE': routes['GIT_INDEX_FILE']}
                callbacks = []
                def register_cleanup(callback, *args, **kwargs):
                    callbacks.append((callback, args, kwargs))
                with patch.dict(os.environ, {**owned_git_environment(), **routes}, clear=True), \
                        patch.object(fixtures, 'ROOT', source), \
                        patch.object(fixtures.unittest, 'addModuleCleanup', register_cleanup):
                    with fixtures._indexed(revision) as owned:
                        self.assertEqual((owned / 'keep.txt').read_text(), 'source')
                        self.assertEqual(subprocess.check_output(
                            ['git', '-C', str(owned), 'rev-parse', 'HEAD'],
                            env=owned_git_environment(), timeout=30).decode().strip(), revision)
                    try:
                        fixtures.setUpModule()
                        self.assertNotEqual(fixtures.ROOT, source)
                        self.assertEqual((fixtures.ROOT / 'keep.txt').read_text(), 'source')
                    finally:
                        for callback, args, kwargs in reversed(callbacks):
                            callback(*args, **kwargs)
                self.assertEqual(self.protected_bytes(protected), before)
