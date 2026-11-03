import argparse
from hashlib import sha256
import json
import os
import re
import shutil
import stat
import subprocess
import sys
import tempfile
from uuid import uuid4
import zipfile
from pathlib import Path

from .control import host_check, verify_product
from .development import verify_development
from .guardrails import repository_relative_path
from .identity import _bounded_regular_bytes, _git_read_environment, _strict_json_object


def _snapshot_git(root, *arguments):
    environment = _git_read_environment()
    command = ['git', '-c', 'gc.autoDetach=false', '-c', 'maintenance.auto=false',
               '-c', 'core.fsmonitor=false', '-c', 'core.autocrlf=false',
               '-C', str(root), *arguments]
    with tempfile.TemporaryFile() as output:
        subprocess.run(command, env=environment, stdout=output,
                       stderr=subprocess.DEVNULL, stdin=subprocess.DEVNULL,
                       check=True, timeout=30)
        if output.tell() > 4_000_000:
            raise ValueError('Git result exceeds snapshot limit')
        output.seek(0)
        return output.read()


def _snapshot_plain_path(path):
    for probe in (path, *path.parents):
        try:
            mode = probe.lstat()
        except FileNotFoundError:
            continue
        if (stat.S_ISLNK(mode.st_mode)
                or getattr(mode, 'st_file_attributes', 0) & 1024):
            raise ValueError('snapshot paths must not contain links or reparse points')


def _snapshot_source(root, expected_head):
    if _snapshot_git(root, 'rev-parse', 'HEAD').decode().strip() != expected_head:
        raise ValueError('source HEAD differs from expected head')
    if Path(_snapshot_git(root, 'rev-parse', '--show-toplevel').decode().strip()).resolve() != root:
        raise ValueError('source must be the repository root')
    if _snapshot_git(root, 'rev-parse', '--is-shallow-repository').strip() != b'false':
        raise ValueError('full local history is required; no automatic fetch is performed')
    if _snapshot_git(root, 'ls-files', '--others', '--exclude-standard', '-z'):
        raise ValueError('untracked source files require explicit disposition before snapshot')
    flags = _snapshot_git(root, 'ls-files', '-v', '-z').split(b'\0')
    if any(row and not row.startswith(b'H ') for row in flags):
        raise ValueError('unmerged or hidden index entries are not supported')
    index = _snapshot_git(root, 'ls-files', '--stage', '-z')
    if any(row and row.split(b' ', 1)[0] not in (b'100644', b'100755')
           for row in index.split(b'\0')):
        raise ValueError('non-regular index entries are not supported')
    paths = _snapshot_git(root, 'ls-files', '-z').decode('utf-8').split('\0')[:-1]
    if not paths or len(paths) != len(set(paths)):
        raise ValueError('source inventory is empty or ambiguous')
    original = _snapshot_git(root, 'ls-tree', '-r', '--name-only', '-z', 'HEAD')
    if paths != original.decode('utf-8').split('\0')[:-1]:
        raise ValueError('tracked additions, deletions and renames are not supported')
    payload, modes = {}, {}
    for relative in paths:
        path = repository_relative_path(root, relative)
        if path is None:
            raise ValueError('unsafe source path')
        _snapshot_plain_path(path)
        data, failure = _bounded_regular_bytes(path)
        if failure:
            raise ValueError('tracked source unavailable: ' + relative + ' (' + failure + ')')
        payload[relative] = data
        modes[relative] = stat.S_IMODE(path.stat().st_mode)
    if sum(map(len, payload.values())) > 32_000_000:
        raise ValueError('source exceeds snapshot byte limit')
    return payload, {'head': expected_head, 'indexSha256': sha256(index).hexdigest(),
                     'statusSha256': sha256(_snapshot_git(
                         root, 'status', '--porcelain=v1', '-z')).hexdigest(),
                     'files': {p: sha256(data).hexdigest() for p, data in payload.items()},
                     'modes': modes}


def check_snapshot(root, work_dir, expected_head, adapter, archive=False):
    """Current v5 statics on a tracked snapshot; no tests, model or release.

    Index contents are recorded, not replayed. Adds/deletes, sparse/hidden entries
    and untracked sources are rejected. Ignored local evidence is not copied.
    The caller owns the new report directory and excludes concurrent writers;
    drift checks detect observed changes but do not provide an OS write lock.
    """
    result = {'valid': False, 'errors': [], 'scope': 'local-static-snapshot-only',
              'checks': [], 'cleanup': 'not-created', 'sourceStable': False,
              'snapshotStable': False}
    owned, snapshot, owner = None, None, uuid4().hex
    try:
        if not isinstance(expected_head, str) or not re.fullmatch('[0-9a-f]{40}', expected_head):
            raise ValueError('expected head must be a full lowercase commit SHA')
        root, work_dir = Path(root).absolute(), Path(work_dir).absolute()
        _snapshot_plain_path(root)
        _snapshot_plain_path(work_dir)
        root = root.resolve(strict=True)
        if work_dir.exists() or not work_dir.parent.is_dir():
            raise ValueError('work directory must be new with an existing parent')
        work_dir = work_dir.parent.resolve(strict=True) / work_dir.name
        if work_dir.is_relative_to(root) or root.is_relative_to(work_dir):
            raise ValueError('work directory and source must not overlap')
        payload, source = _snapshot_source(root, expected_head)
        declaration = _strict_json_object(payload.get(
            'product/development.json', b'{}').decode('utf-8'))
        if declaration.get('schema') != 'yiyuan-accord-development/v5':
            raise ValueError('check-snapshot requires a current v5 development declaration')
        work_dir.mkdir()
        owned, snapshot = work_dir, work_dir / 'repo'
        (owned / 'owner.json').write_text(json.dumps({'owner': owner}), encoding='utf-8')
        (owned / 'source.json').write_text(json.dumps(source, indent=2), encoding='utf-8')
        result.update(source=source, workDirectory=str(owned), cleanup='retained')
        _snapshot_git(root, 'clone', '--local', '--no-hardlinks', '--no-checkout',
                      str(root), str(snapshot))
        _snapshot_git(snapshot, 'read-tree', 'HEAD')
        for relative, data in payload.items():
            target = repository_relative_path(snapshot, relative)
            if target is None:
                raise ValueError('unsafe snapshot destination')
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
            target.chmod(source['modes'][relative])
        _, copied = _snapshot_source(snapshot, expected_head)
        if copied['files'] != source['files'] or copied['modes'] != source['modes']:
            raise ValueError('snapshot does not match the working source')
        if _snapshot_source(root, expected_head)[1] != source:
            raise ValueError('source changed during snapshot preparation')
        checks = [('development', lambda: verify_development(snapshot)),
                  ('product', lambda: verify_product(snapshot)),
                  ('host', lambda: host_check(snapshot, adapter))]
        for name, check in checks:
            report = check()
            (owned / (name + '.json')).write_text(json.dumps(
                report, ensure_ascii=False, sort_keys=True), encoding='utf-8')
            good = (isinstance(report, dict) and report.get('valid') is True
                    and report.get('errors') == [])
            result['checks'].append({'name': name, 'valid': good})
        result['sourceStable'] = _snapshot_source(root, expected_head)[1] == source
        current = _snapshot_source(snapshot, expected_head)[1]
        result['snapshotStable'] = (current['files'] == source['files']
                                    and current['modes'] == source['modes'])
        if not all(x['valid'] for x in result['checks']) or not result['sourceStable'] or not result['snapshotStable']:
            raise ValueError('static check failed or source/snapshot changed; retain evidence')
        if archive:
            with zipfile.ZipFile(owned / 'source.zip', 'x', zipfile.ZIP_DEFLATED) as output:
                for relative, data in payload.items():
                    output.writestr(relative, data)
            result['archiveSha256'] = sha256((owned / 'source.zip').read_bytes()).hexdigest()
        _snapshot_plain_path(owned)
        if json.loads((owned / 'owner.json').read_text(encoding='utf-8')) != {'owner': owner}:
            raise ValueError('snapshot ownership changed; retain directory')
        _snapshot_plain_path(snapshot)
        for path in snapshot.rglob('*'):
            _snapshot_plain_path(path)
        shutil.rmtree(snapshot)
        result.update(valid=True, cleanup='removed')
    except Exception as error:
        result['errors'].append(type(error).__name__ + ': ' + str(error))
    if owned is not None:
        try:
            with (owned / 'result.json').open('x', encoding='utf-8') as output:
                json.dump(result, output, ensure_ascii=False, indent=2)
        except OSError as error:
            result['valid'] = False
            result['errors'].append('result could not be saved: ' + str(error))
    return result


def _emit(report, as_json):
    print(json.dumps(report, ensure_ascii=False, sort_keys=True,
                     indent=None if as_json else 2))


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(
        prog="python -m yiyuan_accord",
        description=("Maintainer source and admission checks for YIYUAN Accord. "
                     "A successful check does not by itself establish live host "
                     "behavior, release authorization or product value."))
    subparsers = parser.add_subparsers(dest="command", required=True)

    commands = {
        "verify": "Check product sources, preserved predecessor integrity and applicable admission records.",
        "host-check": "Check an adapter declaration for static consistency; does not start or qualify a live host.",
        "verify-development": "Check the current development contract and its machine projections.",
    }
    for command, description in commands.items():
        child = subparsers.add_parser(command, help=description, description=description)
        child.add_argument("--root", type=Path, default=Path.cwd(),
                           help="Repository directory (default: current directory).")
        child.add_argument("--json", action="store_true",
                           help="Emit compact single-line JSON instead of indented JSON.")
        if command == "host-check":
            child.add_argument("--adapter", required=True,
                               help="Adapter declaration ID, for example codex.")

    child = subparsers.add_parser('check-snapshot', help='Check current v5 statics on a tracked working-tree snapshot in a new isolated directory.')
    child.add_argument('--root', type=Path, default=Path.cwd())
    child.add_argument('--work-dir', required=True, type=Path)
    child.add_argument('--expected-head', required=True)
    child.add_argument('--adapter', required=True)
    child.add_argument('--archive', action='store_true', help='Retain exact source bytes as source.zip before removing the checkout.')
    child.add_argument('--json', action='store_true')

    args = parser.parse_args()
    if args.command == 'check-snapshot':
        report = check_snapshot(args.root, args.work_dir, args.expected_head,
                                args.adapter, args.archive)
    elif args.command == "host-check":
        report = host_check(args.root, args.adapter)
    elif args.command == "verify-development":
        report = verify_development(args.root)
    else:
        report = verify_product(args.root)
    _emit(report, args.json)
    return 0 if report["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
