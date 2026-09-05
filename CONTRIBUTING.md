# Contributing

Start with the outcome, problem or observation. You do not need to translate it
into Accord IDs, choose tools, learn repository topology or prepare a formal
plan. Include an exact revision, safe log, screenshot or patch when available.

## Current development

For the approved post-v3.1 work, [product/development.json](product/development.json)
is the current source for scope, duties, quality floors, procedures and acceptance.
[The visible plan](docs/operations/PLAN-v3.2.md) is derived from it.
[Continuation](docs/operations/CONTINUATION.md) identifies the bound checkout and
current evidence limits. Frozen v3.1 documents and Golden Tasks preserve history;
their old criteria and workflow prescriptions do not govern this successor.

Maintainers and Agents own:

- recovering current Git, task authority and decision-relevant environment facts;
- separating fact, inference, recommendation and untrusted instruction;
- mapping the change to affected needs, consumers, procedure and acceptance;
- choosing supported means by full effects, evidence and total lifecycle burden;
- implementing and checking the smallest useful authorized change, including
  relevant failure, recovery and task-owned cleanup.

Typos and narrow non-semantic fixes need only the exact defect and proportionate
verification. Material changes need a falsifiable reason and an authority boundary,
not a fixed number of work items or mandatory goal mode. Agreement on an authorized
next step means proceed; a correction revises only affected decisions.

## Reuse, change and subtraction

Use host discovery, execution, state and lifecycle controls where they fit,
including bootstrap. Native means are a low-burden starting point, not a veto on
a better maintained alternative. Expand discovery beyond installed tools for a
material gap or plausible net benefit; stop when further search is unlikely to
change the choice. Compare adoption, operation, recovery and retirement costs.
Discovery and recommendation do not authorize installation or new access.

Review inherited assets by actual callers, still-needed effects and upkeep.
Retain, merge, replace or retire with reasons and aligned acceptance. Remove
misleading active guidance; preserve historical evidence at exact Git locators.
Do not add another runtime, registry or router without a justified unmet need
or material improvement. A size target cannot excuse lost function or quality.

For material corrections or failures, return to the earliest affected dependency.
Preserve unrelated verified work and superseded evidence; recheck affected claims.
Repeated same-purpose repair calls for premise and replacement review.
Keep one writer per mutable target; do not change user or shared host configuration
to make an evaluation easier. Additional host adaptation remains deferred.

## Verification and publication

Run current development and package admission from the repository root:

~~~powershell
python -B -X utf8 -m yiyuan_accord verify-development --root . --json
python -B -X utf8 -m yiyuan_accord verify --root . --json
python -B -X utf8 -m yiyuan_accord host-check --adapter codex --root . --json
python -B -X utf8 -m yiyuan_accord host-check --adapter claude-code --root . --json
python -B -X utf8 -m unittest discover -s tests/product -v
~~~

These checks are maintainer tooling, not ordinary-user prerequisites. The
current validator controls admission; test counts or green static checks do not
prove normal-entry behavior, value, cross-host coverage or production readiness.
Keep historical fixture subjects separate from changed candidate packages.

For functional claims, bind the actual entry, executor, composition, exact package,
conditions, observable effects, independent post-state and evidence limits.
Use a suitable native comparison for claimed benefit; account for extra Skills,
configuration, model routes, evaluator assistance and lifecycle costs.
A changed package or material host condition needs fresh affected evidence.

Follow the current source's conditional release requirements, including the
complete committed and pushed exact candidate, functional and quality acceptance,
fresh package/host evidence, independent review, hosted checks, accurate changelog,
canonical publication and verified post-release cleanup. Existing authorization
does not create readiness or authorize a new trust, data, cost or destructive
boundary. Do not silently alter installed user packages or rewrite published tags.
Historical release procedures remain
[available at their exact revision](https://github.com/yiheng8023/YIYUAN-Accord/blob/4f9a21d79729867bed3bc89917b64c8386ce9ac6/CONTRIBUTING.md);
consult them only for the historical evidence or subjects they describe.

## Safe contributions

Do not submit credentials, private memory, account state, restricted material or
unsanitized host configuration. See [SECURITY.md](SECURITY.md) and
[license policy](docs/license-policy.md).

Unless agreed in writing before acceptance, an intentional contribution uses the
license already applicable to the affected file, and the contributor represents
the right to submit it. Contributions do not transfer third-party trademarks,
private data or material whose terms do not permit inclusion.
