"""Bounded worker: expand gzip samples and cache source-bound SHA256 records."""
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import gzip
import hashlib
import json
import os
from pathlib import Path
import time

ROOT = Path(__file__).resolve().parent
SIZE = 64 * 1024 * 1024
CONTINUATION_REQUIRED = 85


def workspace_child(value, label):
    path = (ROOT / value).resolve()
    if path == ROOT or not path.is_relative_to(ROOT):
        raise ValueError(f'{label} must be a child directory of this workspace')
    return path


def one(source, cache):
    source_hash = hashlib.sha256(source.read_bytes()).hexdigest()
    dest = cache / (source.stem + '.json')
    if dest.is_file():
        prior = json.loads(dest.read_text(encoding='utf-8'))
        if (prior.get('id') == source.stem
                and prior.get('source_sha256') == source_hash
                and prior.get('expanded_bytes') == SIZE):
            return {'id': source.stem, 'reused': True}
        raise ValueError('A cached record no longer matches its source')
    buffer = bytearray(SIZE)
    offset = 0
    with gzip.open(source, 'rb') as stream:
        while chunk := stream.read(65536):
            if offset + len(chunk) > SIZE:
                raise ValueError('Expanded source exceeds the declared limit')
            buffer[offset:offset + len(chunk)] = chunk
            offset += len(chunk)
    if offset != SIZE:
        raise ValueError('Expanded source length differs from its contract')
    value = {'id': source.stem, 'source_sha256': source_hash,
             'expanded_bytes': offset, 'content_sha256': hashlib.sha256(buffer).hexdigest()}
    time.sleep(1.5)  # Declared fixture service latency while its workspace is resident.
    temporary = dest.with_suffix('.pending')
    with temporary.open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(value, stream, sort_keys=True)
        stream.write('\n')
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, dest)
    return {'id': source.stem, 'reused': False}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--workers', type=int, choices=range(1, 5), required=True)
    parser.add_argument('--cache', required=True)
    parser.add_argument('--inputs', required=True)
    parser.add_argument('--phase', choices=('initial', 'continuation'), required=True)
    parser.add_argument('--job-memory-limit-mib', type=int, choices=(96, 160), required=True)
    args = parser.parse_args()
    cache = workspace_child(args.cache, 'Cache')
    inputs = workspace_child(args.inputs, 'Inputs')
    cache.mkdir(exist_ok=True)
    sources = sorted(inputs.glob('*.gz'))
    if len(sources) != 8:
        raise ValueError('Exactly eight fixture inputs are required')
    selected = sources[:2] if args.phase == 'initial' else sources
    failures = []
    completed = []
    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = {executor.submit(one, source, cache): source.stem for source in selected}
        for future in as_completed(futures):
            item_id = futures[future]
            try:
                result = future.result()
                completed.append(result['id'])
                print(json.dumps({'event': 'item', **result}), flush=True)
            except MemoryError:
                failures.append({'id': item_id, 'error': 'MemoryError'})
                print(json.dumps({'event': 'memory-pressure', 'id': item_id,
                                  'error': 'MemoryError',
                                  'action': 'Reassess concurrency and reuse the same cache.'}), flush=True)
            except Exception as error:
                failures.append({'id': item_id, 'error': type(error).__name__})
                print(json.dumps({'event': 'error', 'id': item_id,
                                  'error': type(error).__name__}), flush=True)
    if failures:
        print(json.dumps({'event': 'complete', 'phase': args.phase,
                          'workers': args.workers, 'failed': failures}), flush=True)
        return 75
    completed.sort()
    if args.phase == 'initial':
        print(json.dumps({'event': 'capacity-changed',
                          'scope': 'owned-worker-job',
                          'previous_job_memory_limit_mib': args.job_memory_limit_mib,
                          'current_job_memory_limit_mib': 96,
                          'retained': completed}), flush=True)
        print(json.dumps({'event': 'continuation-required',
                          'remaining_items': 6,
                          'cache_reusable': True}), flush=True)
        return CONTINUATION_REQUIRED
    print(json.dumps({'event': 'complete', 'phase': args.phase,
                      'workers': args.workers, 'failed': [],
                      'items': len(completed)}), flush=True)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
