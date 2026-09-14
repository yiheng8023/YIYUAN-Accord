"""Read-only structural observation for bounded persistent local-file cases.

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
COORDINATION_SCHEMA = 'yiyuan-accord-coordination-case/v1'
SCOPED_SCHEMA = 'yiyuan-accord-scoped-task-case/v1'


def _safe_name(name):
    return (isinstance(name, str) and bool(name) and Path(name).name == name
            and not any(c in name for c in '/\\:') and name not in ('.', '..'))


def validate_case(case):
    """Validate declarations, never turn declared structure into observed facts."""
    if not isinstance(case, dict):
        raise ValueError('persistent case must be an object')
    if case.get('schema') == COORDINATION_SCHEMA:
        names = list(case.get('inputs', {})) + list(case.get('deliverables', []))
        if (set(case) != {'schema', 'purpose', 'inputs', 'deliverables', 'schedule_header',
                          'limits', 'stages', 'observation'}
                or not isinstance(case.get('inputs'), dict) or not case['inputs']
                or not isinstance(case.get('deliverables'), list) or not case['deliverables']
                or any(not _safe_name(name) for name in names)
                or any(not isinstance(value, (str, dict, list)) for value in case['inputs'].values())
                or not isinstance(case.get('stages'), list) or not 2 <= len(case['stages']) <= 16
                or any(not isinstance(stage.get('prompt'), str) or not stage['prompt'].strip()
                       for stage in case['stages'])):
            raise ValueError('unsupported persistent case')
        return case
    if case.get('schema') != SCOPED_SCHEMA or set(case) != {
            'schema', 'purpose', 'inputs', 'allowedPaths', 'deliverables', 'limits', 'stages'}:
        raise ValueError('unsupported persistent case')
    inputs, allowed, deliverables, stages = (case.get('inputs'), case.get('allowedPaths'),
                                             case.get('deliverables'), case.get('stages'))
    names = list(inputs) + allowed + deliverables if isinstance(inputs, dict) and isinstance(allowed, list) and isinstance(deliverables, list) else []
    if (not isinstance(case.get('purpose'), str) or not case['purpose'].strip()
            or not isinstance(inputs, dict) or not inputs
            or any(not isinstance(value, (str, dict, list)) for value in inputs.values())
            or not isinstance(allowed, list) or not allowed
            or not isinstance(deliverables, list) or not deliverables
            or any(not _safe_name(name) for name in names)
            or len(set(allowed)) != len(allowed) or len(set(deliverables)) != len(deliverables)
            or not set(deliverables) <= set(allowed)
            or not isinstance(stages, list) or not 1 <= len(stages) <= 4):
        raise ValueError('unsupported persistent case')
    stage_ids = [stage.get('id') for stage in stages if isinstance(stage, dict)]
    if (len(stage_ids) != len(stages)
            or any(not isinstance(value, str) or not value.strip() for value in stage_ids)
            or len(set(stage_ids)) != len(stage_ids)):
        raise ValueError('unsupported persistent case')
    declared = set(inputs) | set(allowed)
    for index, stage in enumerate(stages):
        if (set(stage) != {'id', 'prompt', 'files', 'semanticReview'}
                or not isinstance(stage['prompt'], str) or not stage['prompt'].strip() or len(stage['prompt']) > 100000
                or not isinstance(stage['semanticReview'], str) or not stage['semanticReview'].strip()
                or len(stage['semanticReview']) > 100000
                or not isinstance(stage['files'], dict) or not stage['files']
                or not set(stage['files']) <= declared):
            raise ValueError('unsupported persistent case')
        for name, rule in stage['files'].items():
            if not isinstance(rule, dict) or rule.get('state') not in ('required', 'absent', 'preserved'):
                raise ValueError('unsupported persistent case')
            if rule['state'] == 'absent' and set(rule) != {'state'}:
                raise ValueError('unsupported persistent case')
            if rule['state'] == 'preserved':
                source = rule.get('from')
                if (set(rule) != {'state', 'from'} or source != 'input' and source not in stage_ids[:index]
                        or source == 'input' and name not in inputs):
                    raise ValueError('unsupported persistent case')
            if rule['state'] == 'required':
                changed_from = rule.get('changedFrom')
                if changed_from is not None and changed_from not in stage_ids[:index]:
                    raise ValueError('unsupported persistent case')
                if rule.get('format') == 'utf8':
                    if (set(rule) not in ({'state', 'format', 'nonempty'},
                                         {'state', 'format', 'nonempty', 'changedFrom'})
                            or type(rule.get('nonempty')) is not bool):
                        raise ValueError('unsupported persistent case')
                elif rule.get('format') == 'json':
                    keys = rule.get('requiredKeys')
                    if (set(rule) not in ({'state', 'format', 'jsonType', 'requiredKeys'},
                                         {'state', 'format', 'jsonType', 'requiredKeys', 'changedFrom'})
                            or rule.get('jsonType') not in ('object', 'array')
                            or not isinstance(keys, list)
                            or any(not isinstance(key, str) or not key for key in keys)
                            or len(set(keys)) != len(keys)
                            or rule['jsonType'] != 'object' and keys):
                        raise ValueError('unsupported persistent case')
                else:
                    raise ValueError('unsupported persistent case')
    final_files = stages[-1]['files']
    if any(final_files.get(name, {}).get('state') != 'required' for name in deliverables):
        raise ValueError('final stage must require every deliverable')
    return case


def snapshot(workspace, names):
    root = Path(workspace)
    return {name: {'sha256': digest(root/name), 'mtimeNs': (root/name).stat().st_mtime_ns}
            for name in names if (root/name).exists()}


def _strict_json(text):
    def pairs(rows):
        if len({key for key, _ in rows}) != len(rows):
            raise ValueError('duplicate JSON key')
        return dict(rows)
    return json.loads(text, object_pairs_hook=pairs,
                      parse_constant=lambda value: (_ for _ in ()).throw(ValueError('non-finite JSON')))


def _inspect_scoped(root, fixture, stage, originals, history):
    violations, errors = [], []
    declared = set(fixture['inputs']) | set(fixture['allowedPaths'])
    try:
        current = snapshot(root, declared)
    except (OSError, ValueError) as error:
        return {'stage': stage['id'], 'decision': 'unknown', 'observationErrors': [str(error)],
                'violations': [], 'semanticDecision': 'unreviewed', 'files': {}}
    for name in set(fixture['inputs']) - set(fixture['allowedPaths']):
        if current.get(name) != originals[name]:
            violations.append('original changed or missing: ' + name)
    for name, rule in stage['files'].items():
        state = rule['state']
        if state == 'absent':
            if name in current:
                violations.append('declared absent file exists: ' + name)
            continue
        if state == 'preserved':
            reference = originals if rule['from'] == 'input' else history.get(rule['from'])
            if not isinstance(reference, dict) or name not in reference:
                errors.append('missing observed predecessor snapshot: ' + rule['from'])
            elif current.get(name) != reference[name]:
                violations.append('preserved file changed or missing: ' + name)
            continue
        if name not in current:
            violations.append('required file missing: ' + name)
            continue
        try:
            data = read_regular(root/name)
            text = data.decode('utf-8')
            if rule['format'] == 'utf8':
                if rule['nonempty'] and not text.strip():
                    violations.append('required UTF-8 file empty: ' + name)
            else:
                value = _strict_json(text)
                expected_type = dict if rule['jsonType'] == 'object' else list
                if not isinstance(value, expected_type):
                    violations.append('JSON type differs from declaration: ' + name)
                elif rule['requiredKeys'] and not set(rule['requiredKeys']) <= set(value):
                    violations.append('JSON keys missing from declaration: ' + name)
        except (OSError, UnicodeError, ValueError, TypeError) as error:
            violations.append('invalid declared structure: ' + name + ' (' + type(error).__name__ + ')')
        changed_from = rule.get('changedFrom')
        if changed_from is not None:
            reference = history.get(changed_from)
            if not isinstance(reference, dict) or name not in reference:
                errors.append('missing observed predecessor snapshot: ' + changed_from)
            elif current[name]['sha256'] == reference[name]['sha256']:
                violations.append('required file content did not change from stage: ' + name)
    allowed = declared | {'.accord-task-state'}
    try:
        violations.extend('unclassified workspace path: ' + path.name
                          for path in root.iterdir() if path.name not in allowed)
    except OSError as error:
        errors.append(str(error))
    return {'stage': stage['id'], 'decision': 'unknown' if errors else 'fail' if violations else 'pass',
            'violations': violations, 'observationErrors': errors, 'files': current,
            'semanticDecision': 'unreviewed', 'requiredSemanticReview': stage['semanticReview'],
            'limit': 'Declared file boundary, identity and UTF-8/JSON structure only; no semantic, authority or admission verdict.'}


def inspect_stage(workspace, stage_id, *, originals, history, fixture_path=FIXTURE):
    root = Path(workspace)
    fixture = json.loads(read_regular(fixture_path))
    validate_case(fixture)
    stage = next((row for row in fixture['stages'] if row['id'] == stage_id), None)
    if stage is None:
        raise ValueError('unknown prospective stage')
    if set(originals) != set(fixture['inputs']):
        raise ValueError('complete pre-turn original identities required')
    if fixture['schema'] == SCOPED_SCHEMA:
        return _inspect_scoped(root, fixture, stage, originals, history)
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
