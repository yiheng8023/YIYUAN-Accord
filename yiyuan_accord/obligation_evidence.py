"""Bounded supplementary execution evidence, conditional on caller provenance.

Hashes establish identity, never native origin, historical prebinding or semantic
sufficiency. The trusted observer and exact independent review own those facts.
This channel neither admits cases nor joins episodes into parent claims.
"""
import copy
from pathlib import PurePosixPath
import re


_ALLOWED = {
    'a02-delegated-managed-selection', 'a02-explicit-policy-native-adoption',
}
_SCOPE = 'v33-dynamic-model-routing'


def evaluate(root, witness, contract, cases, records, admitted, subject, budget, now, candidate_time):
    # Local import keeps the seam internal and reuses the existing bounded source
    # readers, review policy and canonical identity rather than another verifier.
    from . import admission as a

    def require(value):
        if not value:
            raise ValueError('unsupported supplementary execution')

    require(isinstance(witness, dict) and set(witness) == {
        'schema', 'base', 'obligations', 'execution', 'chain', 'sources', 'quality',
        'knownFailuresAndLimits', 'current', 'differences', 'normativeDifferences', 'reviewBundle'})
    require(witness['schema'] == 'yiyuan-accord-obligation-execution-evidence/v1')
    base = witness['base']
    require(isinstance(base, dict) and set(base) == {'case', 'recordSha256'})
    key = base['case']
    require(isinstance(key, str) and key in admitted and key in cases and key in records)
    case, record = cases[key], records[key]
    require(case['scope'] == _SCOPE and a._impact_eligible(contract, case)
            and base['recordSha256'] == a._hash(record))
    obligations = {row['id']: row for requirement in contract['acceptance']['admission']['acceptanceRequirements']
                   if requirement['id'] == 'A02' for row in requirement['outcomeObligations']}
    rows = witness['obligations']
    require(isinstance(rows, list) and 1 <= len(rows) <= len(_ALLOWED))
    selected = []
    for row in rows:
        require(isinstance(row, dict) and set(row) == {'id', 'criterion'})
        oid = row['id']
        require(isinstance(oid, str) and oid in _ALLOWED and oid in obligations and oid not in selected)
        obligation = obligations[oid]
        require(obligation['scope'] == case['scope'] and obligation['claim'] == 'function'
                and row['criterion'] == obligation['source'] and row['criterion']['path'] in case['oracleFiles'])
        selected.append(oid)
    sources = witness['sources']
    require(isinstance(sources, dict) and 1 <= len(sources) <= 128)
    for name, source in sources.items():
        require(a._text(name) and isinstance(source, dict) and set(source) == {'sourceRef', 'sha256', 'kind'}
                and a._text(source['sourceRef']) and isinstance(source['sha256'], str)
                and re.fullmatch(r'[0-9a-f]{64}', source['sha256']) is not None
                and source['kind'] in {'execution-observation', 'current-observation', 'source-analysis'})

    def refs(values, kind):
        return (isinstance(values, list) and bool(values) and len(values) == len(set(values))
                and all(isinstance(v, str) and v in sources and sources[v]['kind'] == kind for v in values))

    execution = witness['execution']
    require(isinstance(execution, dict) and set(execution) == {
        'subject', 'packageSha256', 'episodeId', 'operationId', 'roles', 'managedSkill', 'sourcePolicy'})
    require(all(a._text(execution[k]) for k in ('episodeId', 'operationId'))
            and execution['episodeId'] != record['episodeId'])
    roles = execution['roles']
    require(isinstance(roles, dict) and set(roles) == {'coordinator', 'executor', 'consumer', 'cleanup'})

    def selected_entry(source, role):
        dispositions = next(s for s in source['acceptance']['admission']['scopes']
                            if s['id'] == 'v33-openai-entry-applicability')['conditions']['entryDispositions']
        entries = {row['id']: row['host'] for row in source['capabilityMap']['entrySurfaces']['rows']}
        return (entries.get(role['entry']) == case['host']
                and dispositions.get(role['entry'], {}).get('status') == 'selected')

    for role in roles.values():
        require(isinstance(role, dict) and set(role) == {'actor', 'host', 'entry', 'profile'}
                and all(a._text(role[k]) for k in ('actor', 'host', 'entry'))
                and role['host'] == case['host'] and isinstance(role['profile'], dict) and bool(role['profile'])
                and selected_entry(contract, role))
    require(roles['coordinator']['entry'] == case['entry'])
    require(isinstance(execution['managedSkill'], dict) and set(execution['managedSkill']) == {'id', 'sha256'}
            and a._text(execution['managedSkill']['id']))
    require(isinstance(execution['sourcePolicy'], dict) and set(execution['sourcePolicy']) == {'mode', 'sha256'}
            and execution['sourcePolicy']['mode'] == 'explicit-only')
    require(all(isinstance(v, str) and re.fullmatch(r'[0-9a-f]{64}', v)
                for v in (execution['managedSkill']['sha256'], execution['sourcePolicy']['sha256'])))
    old_subject = execution['subject']
    require(isinstance(old_subject, dict) and set(old_subject) == {'revision', 'tree'}
            and isinstance(old_subject['revision'], str) and re.fullmatch(r'[0-9a-f]{40}', old_subject['revision']))
    revision = old_subject['revision']
    a._git(root, 'merge-base', '--is-ancestor', revision, subject['revision'])
    require(old_subject['tree'] == a._git(root, 'rev-parse', '--verify', revision + '^{tree}').decode('ascii').strip())
    old_contract = a._strict_json_object(a._git(root, 'show', f'{revision}:product/development.json').decode('utf-8'))
    require(old_contract.get('schema') == contract['schema'] and not a.admission_contract_errors(old_contract))
    require(all(selected_entry(old_contract, role) for role in roles.values()))
    old_projection = next(p for p in old_contract['delivery']['hostProjections'] if p['id'] == case['host'])
    projection = next(p for p in contract['delivery']['hostProjections'] if p['id'] == case['host'])
    old_package = PurePosixPath(old_projection['manifest']).parents[1].as_posix()
    package = PurePosixPath(projection['manifest']).parents[1].as_posix()
    snapshot = a._revision_package_snapshot(root, revision, old_package, budget)
    require(execution['packageSha256'] == snapshot['sha256'] == old_projection['packageSha256'])
    current_snapshot = a._revision_package_snapshot(root, subject['revision'], package, budget)
    current = witness['current']
    require(isinstance(current, dict) and set(current) == {'subject', 'packageSha256', 'context'}
            and current['subject'] == subject
            and current['packageSha256'] == current_snapshot['sha256'] == projection['packageSha256'])
    require(isinstance(current['context'], dict) and set(current['context']) == {
        'configuration', 'authority', 'helpers', 'continuingState'}
        and all(refs(v, 'current-observation') for v in current['context'].values()))

    common = {k: execution[k] for k in ('managedSkill', 'sourcePolicy')}
    identity_fields = {'actor', 'host', 'entry', 'profile', 'managedSkill', 'sourcePolicy', 'permissions'}
    chain = witness['chain']
    types = ('pre-effect-binding', 'select', 'native-load', 'useful-adoption', 'cleanup')
    role_names = ('coordinator', 'coordinator', 'executor', 'consumer', 'cleanup')
    require(isinstance(chain, list) and len(chain) == len(types))
    previous_sequence, previous_time = -1, None
    for node, kind, role_name in zip(chain, types, role_names, strict=True):
        identity = {**roles[role_name], **common}
        require(isinstance(node, dict) and set(node) == {
            'type', 'source', 'episodeId', 'operationId', 'sequence', 'at', 'facts', 'role'}
            and node['type'] == kind and node['episodeId'] == execution['episodeId']
            and node['role'] == role_name
            and node['operationId'] == execution['operationId']
            and type(node['sequence']) is int and node['sequence'] > previous_sequence
            and refs([node['source']], 'execution-observation') and isinstance(node['facts'], dict)
            and sources[node['source']]['sha256'] == a._hash({k: v for k, v in node.items() if k != 'source'})
            and all(node['facts'].get(k) == v for k, v in identity.items()))
        at = a._fresh(node['at'], float('inf'), now)
        require(at is not None and (previous_time is None or at > previous_time))
        previous_sequence, previous_time = node['sequence'], at
    bound, selection, native, adoption, cleanup = [n['facts'] for n in chain]
    require(set(bound) == identity_fields | {'subject', 'packageSha256', 'naturalInput', 'selectionDelegation',
        'oneWriter', 'resourceLimits', 'deadlineAt', 'expectedRoles', 'rolePermissions'}
        and bound['subject'] == old_subject and bound['packageSha256'] == execution['packageSha256']
        and a._text(bound['naturalInput']) and a._text(bound['deadlineAt'])
        and bound['selectionDelegation'] == 'coordinator'
        and isinstance(bound['permissions'], dict) and bool(bound['permissions'])
        and bound['oneWriter'] == roles['coordinator']['actor'] and isinstance(bound['resourceLimits'], dict)
        and type(bound['resourceLimits'].get('seconds')) is int
        and bound['resourceLimits']['seconds'] > 0)
    expected_roles, permissions = bound['expectedRoles'], bound['rolePermissions']
    require(isinstance(expected_roles, dict) and set(expected_roles) == set(roles)
            and isinstance(permissions, dict) and set(permissions) == set(roles))
    for name, actual in roles.items():
        expected = expected_roles[name]
        require(isinstance(expected, dict) and set(expected) in (
            {'actor', 'host', 'entry', 'profile'}, {'host', 'entry', 'profile'})
            and ('actor' in expected or name in {'executor', 'cleanup'})
            and all(actual[k] == value for k, value in expected.items())
            and isinstance(permissions[name], dict) and bool(permissions[name]))
    require(all(node['facts'].get('permissions') == permissions[name]
                for node, name in zip(chain, role_names, strict=True)))
    committed = int(a._git(root, 'show', '-s', '--format=%ct', revision).strip())
    require(a._fresh(chain[0]['at'], float('inf'), now).timestamp() >= committed)
    deadline = a._fresh(bound['deadlineAt'], float('inf'), now)
    # A deadline may be future relative to this review; parse without extending it.
    if deadline is None:
        from datetime import datetime
        deadline = datetime.fromisoformat(bound['deadlineAt'].replace('Z', '+00:00'))
    window_seconds = (deadline - a._fresh(chain[0]['at'], float('inf'), now)).total_seconds()
    # seconds is the sourced ceiling from this pre-effect binding, not an
    # unrelated positive number or permission to extend the declared deadline.
    require(deadline.tzinfo is not None and 0 < window_seconds <= bound['resourceLimits']['seconds'])
    # Negative attribution can explain late mechanical cleanup; it cannot
    # retroactively authorize the actions that form the claimed obligation.
    require(all(a._fresh(node['at'], float('inf'), now) <= deadline for node in chain[1:4]))
    require(set(selection) == identity_fields | {'selectionAuthority', 'confirmedExecutor', 'confirmedPermissions'}
            and selection['selectionAuthority'] == 'coordinator-delegated'
            and selection['confirmedExecutor'] == roles['executor']
            and selection['confirmedPermissions'] == permissions['executor'])
    require(set(native) == identity_fields | {'origin', 'fullBodyLoaded', 'dependenciesLoaded'}
            and native['origin'] == 'native-skill-loader' and native['fullBodyLoaded'] is True
            and native['dependenciesLoaded'] is True)
    require(set(adoption) == identity_fields | {'useful', 'actualEffect'}
            and adoption['useful'] is True and a._text(adoption['actualEffect']))
    require(set(cleanup) == identity_fields | {'resourcesReleased', 'poststate'}
            and cleanup['resourcesReleased'] is True and a._text(cleanup['poststate']))

    axes = {q['id'] for q in contract['systemOptimization']['qualityAxes']}
    quality = witness['quality']
    require(isinstance(quality, list) and len(quality) == len(axes))
    seen = set()
    for row in quality:
        require(isinstance(row, dict) and set(row) == {'axis', 'disposition', 'basis', 'sources'}
                and isinstance(row['axis'], str) and row['axis'] in axes and row['axis'] not in seen
                and row['disposition'] == 'supported' and a._text(row['basis'])
                and refs(row['sources'], 'execution-observation'))
        seen.add(row['axis'])
    negatives = witness['knownFailuresAndLimits']
    require(isinstance(negatives, list) and len(negatives) <= 128)
    deadline_accounted = False
    for row in negatives:
        require(isinstance(row, dict) and set(row) == {'kind', 'sources', 'impacts'}
                and a._text(row['kind']) and refs(row['sources'], 'execution-observation')
                and isinstance(row['impacts'], list) and len(row['impacts']) == len(selected))
        impacted = set()
        for impact in row['impacts']:
            require(isinstance(impact, dict) and set(impact) == {
                'obligation', 'qualityAxes', 'disposition', 'basis', 'sources'}
                and isinstance(impact['obligation'], str) and impact['obligation'] in selected
                and impact['obligation'] not in impacted and isinstance(impact['qualityAxes'], list)
                and len(impact['qualityAxes']) == len(axes) and set(impact['qualityAxes']) == axes
                and impact['disposition'] in {'unaffected', 'resolved-before-adoption'}
                and a._text(impact['basis']) and refs(impact['sources'], 'execution-observation'))
            impacted.add(impact['obligation'])
        deadline_accounted |= row['kind'] == 'deadline-exceeded'
    require(previous_time <= deadline or deadline_accounted)

    def deltas(actual, expected, field):
        require(isinstance(actual, list) and len(actual) == len(expected))
        expected = {r[field]: r for r in expected}
        seen = set()
        for row in actual:
            require(isinstance(row, dict) and set(row) == set(next(iter(expected.values()), {})) | {
                'basis', 'sources', 'currentConsequences'})
            name = row[field]
            require(isinstance(name, str) and name in expected and name not in seen
                    and all(row[k] == v for k, v in expected[name].items())
                    and a._text(row['basis']) and refs(row['sources'], 'source-analysis')
                    and refs(row['currentConsequences'], 'current-observation'))
            seen.add(name)
    changes = a._impact_differences(root, revision, subject['revision'], (old_package, package),
                                    case['oracleFiles'], budget, complete=True)
    deltas(witness['differences'], changes, 'path')
    deltas(witness['normativeDifferences'], a._normative_differences(old_contract, contract), 'pointer')
    digest = a._hash({k: v for k, v in witness.items() if k != 'reviewBundle'})
    policy = contract['acceptance']['admission']
    review_policy = policy['reviewPolicy']
    require(set(review_policy['requiredAxes']) == {'product', 'specification', 'implementation', 'standards'}
            and review_policy['minimumReviewers'] >= 2
            and any(set(pair) == {'specification', 'implementation'} for pair in review_policy['independentAxes']))
    require(a.evaluate_review_bundle(witness['reviewBundle'], subject['revision'], subject['tree'],
        policy=review_policy, expected_evidence_sha256=digest)['decision'] == 'pass')
    require(all((at := a._fresh(r['reviewedAt'], policy['reviewMaxAgeSeconds'], now)) is not None
                and at.timestamp() >= max(candidate_time, previous_time.timestamp())
                for r in witness['reviewBundle']['reviews']))
    return {'evidenceSha256': digest, 'current': copy.deepcopy(current), 'baseCase': key,
            'supportedObligations': sorted(selected), 'episodeId': execution['episodeId']}
