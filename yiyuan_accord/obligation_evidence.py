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
    if isinstance(witness, dict) and witness.get('schema') == 'yiyuan-accord-obligation-execution-evidence/v2':
        return _correction(root, witness, contract, subject, budget, now, candidate_time)
    goal = isinstance(witness, dict) and witness.get('schema') == 'yiyuan-accord-obligation-execution-evidence/v3'
    # Local import keeps the seam internal and reuses the existing bounded source
    # readers, review policy and canonical identity rather than another verifier.
    from . import admission as a

    def require(value, *codes):
        if not value:
            if codes:
                raise a._CaseRejection(*codes)
            raise ValueError('unsupported supplementary execution')

    require(isinstance(witness, dict) and set(witness) == {
        'schema', 'base', 'obligations', 'execution', 'chain', 'sources', 'quality',
        'knownFailuresAndLimits', 'current', 'differences', 'normativeDifferences', 'reviewBundle'})
    require(witness['schema'] == ('yiyuan-accord-obligation-execution-evidence/v3' if goal
                                else 'yiyuan-accord-obligation-execution-evidence/v1'))
    if goal:
        require(contract['acceptance']['admission'].get('supplementalGoalEvidence') == a._SUPPLEMENTAL_GOAL_POLICY)
    base = witness['base']
    require(isinstance(base, dict) and set(base) == {'case', 'recordSha256'})
    key = base['case']
    require(isinstance(key, str) and key in cases and key in records)
    require(key in admitted, 'supplementary-base-case-not-admitted')
    case, record = cases[key], records[key]
    require(case['scope'] == ('v33-goal-authority-correction' if goal else _SCOPE) and a._impact_eligible(contract, case)
            and base['recordSha256'] == a._hash(record))
    if goal:
        require(key == a._SUPPLEMENTAL_GOAL_POLICY['baseCase'] and case['entry'] == 'cx-cli')
    allowed = {a._SUPPLEMENTAL_GOAL_POLICY['obligation']} if goal else _ALLOWED
    obligations = {row['id']: row for requirement in contract['acceptance']['admission']['acceptanceRequirements']
                   if requirement['id'] == ('A01' if goal else 'A02') for row in requirement['outcomeObligations']}
    rows = witness['obligations']
    require(isinstance(rows, list) and 1 <= len(rows) <= len(allowed))
    selected = []
    for row in rows:
        require(isinstance(row, dict) and set(row) == {'id', 'criterion'})
        oid = row['id']
        require(isinstance(oid, str) and oid in allowed and oid in obligations and oid not in selected)
        obligation = obligations[oid]
        require(obligation['scope'] == case['scope'] and obligation['claim'] == 'function'
                and row['criterion'] == obligation['source'] and row['criterion']['path'] in case['oracleFiles'])
        selected.append(oid)
    sources = witness['sources']
    require(isinstance(sources, dict) and 1 <= len(sources) <= 128)
    refs = _source_references(sources, require)

    execution = witness['execution']
    common_keys = () if goal else ('managedSkill', 'sourcePolicy')
    execution_fields = {'subject', 'packageSha256', 'episodeId', 'operationId', 'roles'} | set(common_keys)
    if goal:
        execution_fields.add('inputMode')
    require(isinstance(execution, dict) and set(execution) == execution_fields)
    require(all(a._text(execution[k]) for k in ('episodeId', 'operationId'))
            and execution['episodeId'] != record['episodeId'])
    roles = execution['roles']
    required_roles = {'coordinator', 'executor', 'consumer', 'cleanup'} | ({'requester'} if goal else set())
    require(isinstance(roles, dict) and set(roles) == required_roles)

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
    if goal:
        require(roles['executor']['entry'] == case['entry']
                and execution['inputMode'] in {'ordinary-user', 'transparent-maintainer-evaluation'})
    else:
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

    common = {k: execution[k] for k in common_keys}
    identity_fields = {'actor', 'host', 'entry', 'profile', 'permissions'} | set(common_keys)
    chain = witness['chain']
    types = (('pre-effect-binding', 'ordinary-goal-input', 'goal-interpretation',
              'requirements-applied', 'useful-adoption', 'cleanup') if goal else
             ('pre-effect-binding', 'select', 'native-load', 'useful-adoption', 'cleanup'))
    role_names = (('coordinator', 'requester', 'executor', 'executor', 'consumer', 'cleanup') if goal else
                  ('coordinator', 'coordinator', 'executor', 'consumer', 'cleanup'))
    if goal and isinstance(chain, list) and len(chain) == 6 and isinstance(chain[0], dict) \
            and chain[0].get('type') == 'ordinary-goal-input':
        types = ('ordinary-goal-input', 'pre-effect-binding', *types[2:])
        role_names = ('requester', 'coordinator', *role_names[2:])
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
    binding = next(n for n in chain if n['type'] == 'pre-effect-binding')
    bound = binding['facts']
    bound_fields = identity_fields | {'subject', 'packageSha256', 'naturalInput',
        'oneWriter', 'resourceLimits', 'deadlineAt', 'expectedRoles', 'rolePermissions'}
    bound_fields |= {'inputMode'} if goal else {'selectionDelegation'}
    require(set(bound) == bound_fields
        and bound['subject'] == old_subject and bound['packageSha256'] == execution['packageSha256']
        and a._text(bound['naturalInput']) and a._text(bound['deadlineAt'])
        and isinstance(bound['permissions'], dict) and bool(bound['permissions'])
        and bound['oneWriter'] == ('executor' if goal else roles['coordinator']['actor'])
        and isinstance(bound['resourceLimits'], dict)
        and type(bound['resourceLimits'].get('seconds')) is int
        and bound['resourceLimits']['seconds'] > 0)
    require(bound['inputMode'] == execution['inputMode'] if goal else bound['selectionDelegation'] == 'coordinator')
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
    binding_at = a._fresh(binding['at'], float('inf'), now)
    require(binding_at.timestamp() >= committed)
    deadline = a._fresh(bound['deadlineAt'], float('inf'), now)
    # A deadline may be future relative to this review; parse without extending it.
    if deadline is None:
        from datetime import datetime
        deadline = datetime.fromisoformat(bound['deadlineAt'].replace('Z', '+00:00'))
    window_seconds = (deadline - binding_at).total_seconds()
    # seconds is the sourced ceiling from this pre-effect binding, not an
    # unrelated positive number or permission to extend the declared deadline.
    require(deadline.tzinfo is not None and 0 < window_seconds <= bound['resourceLimits']['seconds'])
    # Negative attribution can explain late mechanical cleanup; it cannot
    # retroactively authorize the actions that form the claimed obligation.
    require(all(a._fresh(node['at'], float('inf'), now) <= deadline
                for node in chain if node['type'] not in {'pre-effect-binding', 'cleanup'}))
    if goal:
        _goal_chain(chain, execution, identity_fields, sources, refs, require)
    else:
        _, selection, native, adoption, cleanup = [n['facts'] for n in chain]
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

    deadline_accounted = _quality(contract, witness['quality'], witness['knownFailuresAndLimits'], selected, refs, require)
    require(previous_time <= deadline or deadline_accounted)

    changes = a._impact_differences(root, revision, subject['revision'], (old_package, package),
                                    case['oracleFiles'], budget, complete=True)
    _differences(witness['differences'], changes, 'path', refs, require)
    _differences(witness['normativeDifferences'], a._normative_differences(old_contract, contract), 'pointer', refs, require)
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


def _goal_chain(chain, execution, identity_fields, sources, refs, require):
    """Identity links do not establish genuine ambiguity or useful adoption."""
    from . import admission as a
    facts = {n['type']: n['facts'] for n in chain}
    bound, incoming = facts['pre-effect-binding'], facts['ordinary-goal-input']
    interpretation, applied = facts['goal-interpretation'], facts['requirements-applied']
    adopted, cleanup = facts['useful-adoption'], facts['cleanup']
    require(set(incoming) == identity_fields | {'origin', 'inputSource', 'naturalInput'}
            and incoming['origin'] == execution['inputMode']
            and incoming['naturalInput'] == bound['naturalInput']
            and refs([incoming['inputSource']]))
    require(set(interpretation) == identity_fields | {'inputSource', 'materialSources', 'resolution', 'requirements'}
            and interpretation['inputSource'] == incoming['inputSource']
            and refs(interpretation['materialSources']))
    resolution = interpretation['resolution']
    require(isinstance(resolution, dict) and set(resolution) == {'mode', 'alternatives', 'basis', 'clarificationSources'}
            and resolution['mode'] in {'source-grounded-interpretation', 'necessary-clarification'}
            and a._text(resolution['basis']) and isinstance(resolution['alternatives'], list)
            and 2 <= len(resolution['alternatives']) <= 8
            and all(a._text(v) for v in resolution['alternatives'])
            and len(set(resolution['alternatives'])) == len(resolution['alternatives'])
            and (resolution['clarificationSources'] == []
                 or refs(resolution['clarificationSources'])))
    require(resolution['mode'] != 'necessary-clarification' or refs(resolution['clarificationSources']))

    def artifact(value):
        return (isinstance(value, dict) and set(value) == {'id', 'source', 'sha256'}
            and a._text(value['id']) and refs([value['source']])
            and value['sha256'] == sources[value['source']]['sha256'])
    def same_artifact(value, expected):
        return artifact(value) and all(value[k] == expected[k] for k in ('id', 'sha256'))
    requirements = interpretation['requirements']
    require(artifact(requirements))
    require(set(applied) == identity_fields | {'requirements', 'applicationSources', 'output'}
            and same_artifact(applied['requirements'], requirements) and refs(applied['applicationSources'])
            and artifact(applied['output']))
    require(set(adopted) == identity_fields | {'requirements', 'output', 'useSources', 'useful'}
            and same_artifact(adopted['requirements'], requirements) and same_artifact(adopted['output'], applied['output'])
            and refs(adopted['useSources']) and adopted['useful'] is True)
    require(set(cleanup) == identity_fields | {'resourcesReleased', 'poststate'}
            and cleanup['resourcesReleased'] is True and refs(cleanup['poststate']))


def _correction(root, witness, contract, subject, budget, now, candidate_time):
    """Independent consequence only: never a substitute case or CLI admission."""
    from . import admission as a

    def require(value, *codes):
        if not value:
            if codes:
                raise a._CaseRejection(*codes)
            raise ValueError('unsupported independent correction')

    require(contract['acceptance']['admission'].get('independentObligationEvidence')
            == a._INDEPENDENT_OBLIGATION_POLICY)
    require(set(witness) == {'schema', 'type', 'obligation', 'execution', 'chain', 'sources',
        'quality', 'knownFailuresAndLimits', 'current', 'sourceEpochs', 'reviewBundle'}
        and witness['type'] == 'independent-native-root-correction-poststate')
    oid = 'a04-actual-retroactive-correction'
    obligation = next(o for r in contract['acceptance']['admission']['acceptanceRequirements']
                      if r['id'] == 'A04' for o in r['outcomeObligations'] if o['id'] == oid)
    require(witness['obligation'] == obligation and obligation['scope'] == 'v33-systemic-correction'
            and obligation['claim'] == 'function' and obligation['expected'] is True)
    sources = witness['sources']
    require(isinstance(sources, dict) and 1 <= len(sources) <= 128)
    refs = _source_references(sources, require)

    execution = witness['execution']
    require(isinstance(execution, dict) and set(execution) == {'loadedPackage', 'episodeId',
        'operationId', 'actor', 'host', 'entry', 'profile'}
        and all(a._text(execution[k]) for k in ('episodeId', 'operationId', 'actor', 'host', 'entry'))
        and isinstance(execution['profile'], dict) and bool(execution['profile']))
    loaded = execution['loadedPackage']
    require(isinstance(loaded, dict) and set(loaded) == {'sha256', 'sources', 'limits'}
            and (loaded['sha256'] is None or isinstance(loaded['sha256'], str)
                 and re.fullmatch(r'[0-9a-f]{64}', loaded['sha256']))
            and refs(loaded['sources']) and a._text(loaded['limits']))

    def projection(source, rev, expected):
        entries = {r['id']: r['host'] for r in source['capabilityMap']['entrySurfaces']['rows']}
        dispositions = next(s for s in source['acceptance']['admission']['scopes']
                            if s['id'] == 'v33-openai-entry-applicability')['conditions']['entryDispositions']
        require(entries.get(execution['entry']) == execution['host']
                and dispositions.get(execution['entry'], {}).get('status') == 'selected')
        projection = next(p for p in source['delivery']['hostProjections'] if p['id'] == execution['host'])
        package = PurePosixPath(projection['manifest']).parents[1].as_posix()
        require(a._revision_package_snapshot(root, rev, package, budget)['sha256'] == expected == projection['packageSha256'])
        return package
    current = witness['current']
    policy = contract['acceptance']['admission']
    require(isinstance(current, dict) and set(current) == {'subject', 'packageSha256', 'context', 'observedAt', 'maxAgeSeconds'}
            and current['subject'] == subject and type(current['maxAgeSeconds']) is int
            and 0 < current['maxAgeSeconds'] <= policy['reviewMaxAgeSeconds']
            and isinstance(current['context'], dict)
            and set(current['context']) == {'configuration', 'authority', 'helpers', 'continuingState'}
            and all(refs(v, 'current-observation') for v in current['context'].values()))
    observed = a._fresh(current['observedAt'], current['maxAgeSeconds'], now)
    require(observed is not None and observed.timestamp() >= candidate_time)
    package = projection(contract, subject['revision'], current['packageSha256'])
    epochs = witness['sourceEpochs']
    require(isinstance(epochs, list) and 1 <= len(epochs) <= 32)
    revisions = set()
    for epoch in epochs:
        require(isinstance(epoch, dict) and set(epoch) == {
            'subject', 'projectionPackageSha256', 'differences', 'normativeDifferences'})
        old = epoch['subject']
        require(isinstance(old, dict) and set(old) == {'revision', 'tree'}
                and isinstance(old['revision'], str) and re.fullmatch(r'[0-9a-f]{40}', old['revision'])
                and old['revision'] not in revisions)
        revision = old['revision']
        revisions.add(revision)
        a._git(root, 'merge-base', '--is-ancestor', revision, subject['revision'])
        require(old['tree'] == a._git(root, 'rev-parse', '--verify', revision + '^{tree}').decode('ascii').strip())
        old_contract = a._strict_json_object(a._git(root, 'show', f'{revision}:product/development.json').decode('utf-8'))
        require(old_contract.get('schema') == contract['schema'] and not a.admission_contract_errors(old_contract))
        old_package = projection(old_contract, revision, epoch['projectionPackageSha256'])
        _differences(epoch['differences'], a._impact_differences(root, revision, subject['revision'],
            (old_package, package), [obligation['source']['path']], budget, complete=True), 'path', refs, require)
        _differences(epoch['normativeDifferences'], a._normative_differences(old_contract, contract), 'pointer', refs, require)
    chain = witness['chain']
    require(isinstance(chain, list) and 4 <= len(chain) <= 128 and all(isinstance(n, dict) for n in chain)
            and [n.get('type') for n in chain[:-2]] == ['authority'] + ['correction'] * (len(chain)-3)
            and {n.get('type') for n in chain[-2:]} == {'poststate', 'cleanup'})
    previous, effects, used = None, set(), set()
    for node in chain:
        require(isinstance(node, dict) and set(node) == {'type', 'at', 'actor', 'source', 'facts', 'sourceEpochs'}
                and node['actor'] == execution['actor'] and refs([node['source']])
                and sources[node['source']]['sha256'] == a._hash({k: v for k, v in node.items() if k != 'source'}))
        at = a._fresh(node['at'], float('inf'), now)
        require(at is not None and (previous is None or at > previous))
        previous = at
        require(isinstance(node['sourceEpochs'], list)
                and len(node['sourceEpochs']) == len(set(node['sourceEpochs']))
                and set(node['sourceEpochs']) <= revisions
                and (node['type'] == 'authority' or node['sourceEpochs']))
        used.update(node['sourceEpochs'])
        facts = node['facts']
        require(isinstance(facts, dict))
        if node['type'] == 'authority':
            require(set(facts) == {'origin', 'task', 'constraints', 'permissions', 'oneWriter'}
                    and facts['origin'] == 'native-user-input' and a._text(facts['task'])
                    and a._text(facts['constraints']) and isinstance(facts['permissions'], dict)
                    and bool(facts['permissions']) and facts['oneWriter'] == execution['actor'])
        elif node['type'] == 'correction':
            require(set(facts) == {'callId', 'cause', 'targets', 'result', 'success'}
                    and a._text(facts['callId']) and facts['callId'] not in effects
                    and all(refs(facts[k]) for k in ('cause', 'targets', 'result')) and facts['success'] is True)
            effects.add(facts['callId'])
        elif node['type'] == 'poststate':
            require(set(facts) == {'affected', 'preserved', 'retainedFailures', 'verification', 'adoption'}
                    and all(refs(facts[k]) for k in ('preserved', 'verification', 'adoption'))
                    and isinstance(facts['retainedFailures'], list)
                    and (not facts['retainedFailures'] or refs(facts['retainedFailures'])))
            affected = facts['affected']
            require(isinstance(affected, list) and 1 <= len(affected) <= 128)
            names = set()
            for row in affected:
                require(isinstance(row, dict) and set(row) == {'target', 'disposition', 'before', 'after', 'verification', 'basis'}
                        and a._text(row['target']) and row['target'] not in names
                        and row['disposition'] in {'corrected-and-verified', 'valid-and-preserved'}
                        and all(refs(row[k]) for k in ('before', 'after', 'verification')) and a._text(row['basis']))
                names.add(row['target'])
        else:
            require(set(facts) == {'resourcesReleased', 'poststate'}
                    and facts['resourcesReleased'] is True and refs(facts['poststate']))
    require(previous <= observed and used == revisions)
    _quality(contract, witness['quality'], witness['knownFailuresAndLimits'], [oid], refs, require)
    digest = a._hash({k: v for k, v in witness.items() if k != 'reviewBundle'})
    review = policy['reviewPolicy']
    require(set(review['requiredAxes']) == {'product', 'specification', 'implementation', 'standards'}
            and review['minimumReviewers'] >= 2
            and any(set(pair) == {'specification', 'implementation'} for pair in review['independentAxes'])
            and a.evaluate_review_bundle(witness['reviewBundle'], subject['revision'], subject['tree'],
                policy=review, expected_evidence_sha256=digest)['decision'] == 'pass'
            and all((at := a._fresh(r['reviewedAt'], policy['reviewMaxAgeSeconds'], now)) is not None
                    and at >= observed for r in witness['reviewBundle']['reviews']))
    return {'evidenceKind': witness['type'], 'evidenceSha256': digest, 'current': copy.deepcopy(current),
            'scope': obligation['scope'], 'claim': obligation['claim'], 'criterion': copy.deepcopy(obligation['source']),
            'supportedObligations': [oid], 'episodeId': execution['episodeId'], 'operationId': execution['operationId'], 'entry': execution['entry']}


def _quality(contract, quality, negatives, selected, refs, require):
    from . import admission as a
    axes = {q['id'] for q in contract['systemOptimization']['qualityAxes']}
    require(isinstance(quality, list) and len(quality) == len(axes))
    seen = set()
    for row in quality:
        require(isinstance(row, dict) and set(row) == {'axis', 'disposition', 'basis', 'sources'}
                and isinstance(row['axis'], str) and row['axis'] in axes and row['axis'] not in seen
                and row['disposition'] == 'supported' and a._text(row['basis'])
                and refs(row['sources'], 'execution-observation'))
        seen.add(row['axis'])
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
    return deadline_accounted


def _differences(actual, expected, field, refs, require):
    from . import admission as a
    require(isinstance(actual, list) and len(actual) == len(expected))
    expected = {r[field]: r for r in expected}
    seen = set()
    for row in actual:
        require(isinstance(row, dict) and set(row) == set(next(iter(expected.values()), {})) | {
            'basis', 'sources', 'currentConsequences'})
        name = row[field]
        require(isinstance(name, str) and name in expected and name not in seen
                and all(row[k] == v for k, v in expected[name].items())
                and a._text(row['basis']))
        require(refs(row['sources'], None))
        require(refs(row['sources'], 'source-analysis'), 'source-analysis-reference-kind-mismatch')
        require(refs(row['currentConsequences'], None))
        require(refs(row['currentConsequences'], 'current-observation'),
                'current-observation-reference-kind-mismatch')
        seen.add(name)


def _source_references(sources, require):
    from . import admission as a
    for key, row in sources.items():
        require(a._text(key) and isinstance(row, dict) and set(row) == {'sourceRef', 'sha256', 'kind'}
                and a._text(row['sourceRef']) and isinstance(row['sha256'], str)
                and re.fullmatch(r'[0-9a-f]{64}', row['sha256'])
                and row['kind'] in {'execution-observation', 'current-observation', 'source-analysis'})
    def refs(values, kind='execution-observation'):
        return (isinstance(values, list) and bool(values)
                and all(isinstance(v, str) and v in sources for v in values)
                and len(values) == len(set(values))
                and (kind is None or all(sources[v]['kind'] == kind for v in values)))
    return refs
