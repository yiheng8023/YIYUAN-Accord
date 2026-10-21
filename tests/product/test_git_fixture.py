"""Fixture Git commands must never inherit a caller's repository routing."""

import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from tests.product import test_product_control as fixtures
from tests.product.git_fixture import owned_git_environment


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
