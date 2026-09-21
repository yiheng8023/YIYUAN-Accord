"""Windows-only fixture CLI with an OS-enforced budget on its owned worker job."""
import argparse
import ctypes
from ctypes import wintypes as W
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import threading
import time
import uuid

ROOT = Path(__file__).resolve().parent
SIZE = 64 * 1024 * 1024
EXECUTION_SECONDS = 45
RECOVERY_SECONDS = 10


def load_windows_job(runtime_root_value):
    runtime_root = Path(runtime_root_value).resolve(strict=True)
    source = runtime_root / 'scripts' / 'observe_codex_entry.py'
    if not runtime_root.is_dir() or not source.is_file():
        raise ValueError('--runtime-root must be a directory containing scripts/observe_codex_entry.py')
    sys.path.insert(0, str(runtime_root))
    from scripts.observe_codex_entry import WindowsJob
    return WindowsJob


class Basic(ctypes.Structure):
    _fields_ = [('user', ctypes.c_longlong), ('job', ctypes.c_longlong), ('flags', W.DWORD),
                ('minWorking', ctypes.c_size_t), ('maxWorking', ctypes.c_size_t),
                ('activeLimit', W.DWORD), ('affinity', ctypes.c_size_t),
                ('priority', W.DWORD), ('scheduling', W.DWORD)]


class Extended(ctypes.Structure):
    _fields_ = [('basic', Basic), ('io', ctypes.c_ulonglong * 6),
                ('processMemory', ctypes.c_size_t), ('jobMemory', ctypes.c_size_t),
                ('peakProcessMemory', ctypes.c_size_t), ('peakJobMemory', ctypes.c_size_t)]


class Cpu(ctypes.Structure):
    _fields_ = [('flags', W.DWORD), ('rate', W.DWORD)]


def workspace_child(value, label):
    path = (ROOT / value).resolve()
    if path == ROOT or not path.is_relative_to(ROOT):
        raise ValueError(f'{label} must be a child directory of this workspace')
    return path


def matching_cache(source, cache):
    record = cache / (source.stem + '.json')
    if not record.is_file():
        return False
    try:
        value = json.loads(record.read_text(encoding='utf-8'))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return False
    return (value.get('id') == source.stem
            and value.get('source_sha256') == hashlib.sha256(source.read_bytes()).hexdigest()
            and value.get('expanded_bytes') == SIZE)


def parse_events(stdout):
    events = []
    for line in stdout.splitlines():
        try:
            value = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict) and isinstance(value.get('event'), str):
            events.append(value)
    return events


def cache_snapshot(cache):
    return {p.name: {'sha256': hashlib.sha256(p.read_bytes()).hexdigest(),
                     'mtimeNs': p.stat().st_mtime_ns}
            for p in sorted(cache.glob('*.json')) if p.is_file()}


def run(workers, cache_value, inputs_value, runtime_root_value):
    cache = workspace_child(cache_value, 'Cache')
    inputs = workspace_child(inputs_value, 'Inputs')
    sources = sorted(inputs.glob('*.gz'))
    if len(sources) != 8:
        raise ValueError('Exactly eight fixture inputs are required')
    cache.mkdir(exist_ok=True)
    phase = 'continuation' if all(matching_cache(source, cache) for source in sources[:2]) else 'initial'
    cache_before = cache_snapshot(cache)
    memory_mib = 96 if phase == 'continuation' else 160
    budget = memory_mib * 1024 * 1024
    WindowsJob = load_windows_job(runtime_root_value)
    job = WindowsJob()
    limits = Extended()
    limits.basic.flags = 0x2000 | 0x200
    limits.jobMemory = budget
    cpu = Cpu(0x1 | 0x4, 1000)
    for info, value in [(9, limits), (15, cpu)]:
        if not job.k.SetInformationJobObject(job.handle, info, ctypes.byref(value), ctypes.sizeof(value)):
            job.close()
            raise ctypes.WinError(ctypes.get_last_error())
    invocation = str(uuid.uuid4())
    logs = ROOT / 'run-records'
    logs.mkdir(exist_ok=True)
    proc = None
    samples = []
    stop = threading.Event()
    forced = False
    forced_reason = None
    recovery_deadline = None
    start = time.monotonic()

    def sample():
        while not stop.wait(0.2):
            samples.append(job.sample())

    try:
        command = [sys.executable, '-B', '-X', 'utf8', str(ROOT / 'batch_worker.py'),
                   '--workers', str(workers), '--cache', str(cache.relative_to(ROOT)),
                   '--inputs', str(inputs.relative_to(ROOT)), '--phase', phase,
                   '--job-memory-limit-mib', str(memory_mib)]
        proc = subprocess.Popen(command, cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                text=True, encoding='utf-8',
                                creationflags=subprocess.CREATE_NO_WINDOW | 0x4)
        try:
            job.attach_and_resume(proc)
        except Exception:
            proc.kill()
            proc.wait(timeout=RECOVERY_SECONDS)
            raise
        reader = threading.Thread(target=sample, daemon=True)
        reader.start()
        try:
            remaining = max(0.1, EXECUTION_SECONDS - (time.monotonic() - start))
            stdout, stderr = proc.communicate(timeout=remaining)
        except subprocess.TimeoutExpired:
            forced = True
            forced_reason = 'execution-timeout'
            recovery_deadline = time.monotonic() + RECOVERY_SECONDS
            job.terminate()
            stdout, stderr = proc.communicate(timeout=max(0.1, recovery_deadline - time.monotonic()))
        if recovery_deadline is None:
            recovery_deadline = time.monotonic() + RECOVERY_SECONDS
        stop.set()
        reader.join(timeout=max(0, min(2, recovery_deadline - time.monotonic())))
        before_recovery = job.sample()
        while job.sample()['activeProcesses'] and time.monotonic() < recovery_deadline:
            time.sleep(0.1)
        after_recovery = job.sample()
        if after_recovery['activeProcesses']:
            forced = True
            forced_reason = forced_reason or 'owned-processes-remained'
            job.terminate()
            while job.sample()['activeProcesses'] and time.monotonic() < recovery_deadline:
                time.sleep(0.1)
        post_state = job.sample()
        measured = Extended()
        if not job.k.QueryInformationJobObject(job.handle, 9, ctypes.byref(measured), ctypes.sizeof(measured), None):
            raise ctypes.WinError(ctypes.get_last_error())
        measured_cpu = Cpu()
        if not job.k.QueryInformationJobObject(job.handle, 15, ctypes.byref(measured_cpu), ctypes.sizeof(measured_cpu), None):
            raise ctypes.WinError(ctypes.get_last_error())
        events = parse_events(stdout)
        tool_exit = 124 if forced or post_state['activeProcesses'] else proc.returncode
        result = {
            'id': invocation,
            'platformScope': 'Windows Job Object for the owned worker process and descendants',
            'phase': phase,
            'workers': workers,
            'processExitCode': proc.returncode,
            'toolExitCode': tool_exit,
            'forced': forced,
            'forcedReason': forced_reason,
            'elapsedSeconds': time.monotonic() - start,
            'executionLimitSeconds': EXECUTION_SECONDS,
            'recoveryLimitSeconds': RECOVERY_SECONDS,
            'sourceSha256': {
                'batchTool': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                'batchWorker': hashlib.sha256((ROOT / 'batch_worker.py').read_bytes()).hexdigest(),
            },
            'jobMemoryLimitBytes': int(measured.jobMemory),
            'peakJobMemoryBytes': int(measured.peakJobMemory),
            'cpuRatePer10000': int(measured_cpu.rate),
            'cpuControlFlags': int(measured_cpu.flags),
            'cacheBefore': cache_before,
            'cacheAfter': cache_snapshot(cache),
            'budgetScope': 'owned-worker-job-only',
            'beforeRecovery': before_recovery,
            'afterRecovery': after_recovery,
            'postState': post_state,
            'postStateSource': 'supervisor query of the live Job Object, independent of worker stdout',
            'memoryErrorEvents': [event for event in events if event.get('error') == 'MemoryError'],
            'events': events,
            'samples': samples,
            'stdout': stdout,
            'stderr': stderr,
        }
        (logs / (invocation + '.json')).write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
        print(stdout, end='')
        summary_keys = ['id', 'phase', 'workers', 'processExitCode', 'toolExitCode', 'forced',
                        'elapsedSeconds', 'jobMemoryLimitBytes', 'peakJobMemoryBytes',
                        'cpuRatePer10000', 'postState']
        print(json.dumps({key: result[key] for key in summary_keys}))
        if stderr:
            print(stderr, file=sys.stderr)
        return tool_exit
    finally:
        stop.set()
        if proc is not None and proc.poll() is None:
            if recovery_deadline is None:
                recovery_deadline = time.monotonic() + RECOVERY_SECONDS
            try:
                job.terminate()
            finally:
                remaining = recovery_deadline - time.monotonic()
                if remaining > 0:
                    try:
                        proc.wait(timeout=remaining)
                    except subprocess.TimeoutExpired:
                        pass
        job.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description=('Decode eight compressed inputs in a Windows Job Object. The first invocation '
                     'retains two completed items before reporting a capacity change; later invocations '
                     'reuse matching cache entries. No model, network or installation is used.'))
    parser.add_argument('--workers', type=int, choices=range(1, 5), default=1,
                        help='Concurrent decoders; each uses a 64 MiB working buffer, plus runtime overhead.')
    parser.add_argument('--cache', default='cache',
                        help='Workspace-child directory for reusable item results.')
    parser.add_argument('--inputs', default='inputs',
                        help='Workspace-child directory containing exactly eight gzip inputs.')
    parser.add_argument('--runtime-root', required=True,
                        help='Read-only runtime root containing scripts/observe_codex_entry.py.')
    args = parser.parse_args()
    raise SystemExit(run(args.workers, args.cache, args.inputs, args.runtime_root))
