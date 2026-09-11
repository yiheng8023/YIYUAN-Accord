"""Read-only structural observation for the bounded v3.3 collaboration case.

Run as python -m scripts.inspect_coordination. No model or host is started.
Prose, authorization and native action/terminal evidence need independent review;
passing this file checker is not case admission or semantic verification.
"""
import argparse
import csv
import io
import json
from pathlib import Path

from scripts.observe_codex_entry import digest, read_regular
from yiyuan_accord.identity import _strict_json_object

FIXTURE = Path(__file__).resolve().parents[1] / 'product/cases/coordination-v3.3.json'


def snapshot(workspace, names):
    root = Path(workspace)
    return {name: {'sha256': digest(root/name), 'mtimeNs': (root/name).stat().st_mtime_ns}
            for name in names if (root/name).exists()}


def inspect_stage(workspace, stage_id, *, originals, history):
    root = Path(workspace)
    fixture = json.loads(read_regular(FIXTURE))
    stage = next((row for row in fixture['stages'] if row['id'] == stage_id), None)
    if stage is None:
        raise ValueError('unknown prospective stage')
    if set(originals) != set(fixture['inputs']):
        raise ValueError('complete pre-turn original identities required')
    violations, errors = [], []
    try:
        current = snapshot(root, [*fixture['inputs'], *fixture['deliverables']])
    except (OSError, ValueError) as error:
        return {'stage': stage_id, 'decision': 'unknown', 'observationErrors': [str(error)],
                'violations': [], 'semanticDecision': 'unreviewed', 'files': {}}
    for name, identity in originals.items():
        if current.get(name) != identity:
            violations.append('original changed or missing: '+name)
    for name in stage.get('required_files', []):
        if name not in current:
            violations.append('required file missing: '+name)
        else:
            try:
                if not read_regular(root/name).strip():
                    violations.append('required file empty: '+name)
            except (OSError, ValueError) as error:
                errors.append(str(error))
    for name in stage.get('forbidden_files', []):
        if (root/name).exists():
            violations.append('file created before agreement: '+name)
    preservation = dict(stage.get('preserve_files_from_stage', {}))
    if 'preserve_stage' in stage:
        preservation[stage['preserve_stage']] = fixture['deliverables']
    for prior, names in preservation.items():
        reference = history.get(prior)
        if not isinstance(reference, dict) or not set(names) <= reference.keys():
            errors.append('missing observed predecessor snapshot: '+prior)
            continue
        for name in names:
            if current.get(name) != reference[name]:
                violations.append('preserved file changed or missing: '+name)
    for name, expected in (('schedule.csv', stage.get('schedule')), ('budget.json', stage.get('budget'))):
        if expected is None or name not in current:
            continue
        try:
            data = read_regular(root/name)
        except (OSError, ValueError) as error:
            errors.append(str(error))
            continue
        try:
            text = data.decode('utf-8-sig')
            value = list(csv.reader(io.StringIO(text))) if name.endswith('.csv') else _strict_json_object(text)
            target = [fixture['schedule_header'], *expected] if name.endswith('.csv') else expected
            if value != target:
                violations.append('structured output differs from current decision: '+name)
        except (ValueError, csv.Error) as error:
            violations.append('invalid structured output: '+name+' ('+type(error).__name__+')')
    allowed = set(fixture['inputs']) | set(fixture['deliverables']) | {'.accord-task-state'}
    try:
        extra = sorted(p.name for p in root.iterdir() if p.name not in allowed)
        violations.extend('unclassified workspace path: '+name for name in extra)
    except OSError as error:
        errors.append(str(error))
    return {'stage': stage_id, 'decision': 'unknown' if errors else 'fail' if violations else 'pass',
            'violations': violations, 'observationErrors': errors, 'files': current,
            'semanticDecision': 'unreviewed', 'requiredSemanticReview': stage['semantic_review'],
            'limit': 'File structure and protection only; no native input, authority, prose or resource verdict.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('workspace', type=Path)
    parser.add_argument('stage')
    parser.add_argument('--originals', type=Path, required=True)
    parser.add_argument('--history', type=Path, required=True)
    args = parser.parse_args()
    result = inspect_stage(args.workspace, args.stage,
                           originals=json.loads(read_regular(args.originals)),
                           history=json.loads(read_regular(args.history)))
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return {'pass': 0, 'fail': 1, 'unknown': 2}[result['decision']]


if __name__ == '__main__':
    raise SystemExit(main())
