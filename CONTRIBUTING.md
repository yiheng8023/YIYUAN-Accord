# Contributing

Start with the outcome, problem or observation. You do not need to translate it
into Accord IDs, choose tools, learn repository topology or prepare a formal
plan. Include an exact revision, safe log, screenshot or patch when available.

## Current development

For current v3.3 work, [the consensus and plan](docs/operations/PLAN-v3.3.md)
owns the approved scope, decisions and procedures; its linked acceptance view
defines the criteria. [product/development.json](product/development.json) is
the machine validation projection, not a competing source of user decisions.
[Continuation](docs/operations/CONTINUATION.md) identifies the bound checkout and
current evidence limits. Git preserves the exact v3.1 documents and Golden Tasks;
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
not a fixed number of work items. Agreement on an authorized
next step means proceed; a correction revises only affected decisions.

Keep the Mermaid system and procedure diagrams in the consensus plan, together
with the overview in both [English](README.md#how-it-works) and
[Chinese](README.zh-CN.md#如何工作) READMEs, as maintained views of that design.
When a change affects depicted duties, relationships, boundaries or dependencies,
update the affected diagrams and surrounding explanations in the same change.
Keep the bilingual overviews equivalent, check links and Mermaid syntax, and
preserve feedback and conditional ordering. Diagrams explain the current design;
completion and support claims still require the plan's linked acceptance evidence.

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
Keep one writer per mutable target. Bind necessary user-authorized configuration
changes to a specific scope, verified backup, affected sessions and recovery;
do not change settings to manufacture a pass. Additional host adaptation remains deferred.

## Verification and publication

Run current development and package admission from the repository root:

~~~powershell
python -B -X utf8 -m yiyuan_accord verify-development --root . --json
python -B -X utf8 -m yiyuan_accord verify --root . --json
python -B -X utf8 -m yiyuan_accord host-check --adapter codex --root . --json
python -B -X utf8 -m unittest discover -s tests/product -v
~~~

These checks are maintainer tooling, not ordinary-user prerequisites. The
current validator controls admission; test counts or green static checks do not
prove normal-entry behavior, value, cross-host coverage or production readiness.
Keep historical fixture subjects separate from changed candidate packages.

For serialized App Server observers, [BoundedRpc](scripts/codex_rpc.py) separates
the work deadline from a fixed recovery window. Bind work, per-request and recovery
limits before execution. At a work deadline or failure, call `begin_recovery` with
the independently verified owned thread ID; only interruption, state reading and
unsubscribe for that target remain available. Recovery cannot renew its window
or resume work. An expired request is rejected before dispatch. After a send
attempt, a timeout means an uncertain effect, so reconcile the native state instead
of blindly retrying. A received RPC error is distinct from a deadline; an interrupt
acknowledgement alone does not prove that the turn stopped.

This helper does not supply a transport, authenticate ownership, cancel a turn
automatically or control the host's permissions. The caller retains raw events,
supplies the required `on_event` handler for interleaved notifications/requests,
provides bounded send/receive callbacks
using the same monotonic clock, and independently bounds process/resource cleanup.
Other transport/protocol failures also require post-state reconciliation. Keep
historical observers unchanged when their bytes are part of earlier evidence.

Encode testable, risk-relevant constraints in repeatable checks tied to the
authorized requirement and observable result. Challenge critical checks with
known failures; use targeted mutation or fault injection when it adds confidence.
Keep mutation survivors, equivalent changes, timeouts and tool errors distinct;
[PIT explains these limits](https://pitest.org/quickstart/basic_concepts/).
Broad mutation campaigns and universal score thresholds are not prerequisites.

Complexity, coverage and CRAP help locate change risk; they cannot establish
requirement coverage, architecture quality or product value. Define the measured
unit, coverage kind and justified threshold before using a metric as a gate.
[CRAP's original rationale](https://www.artima.com/weblogs/viewpost.jsp?thread=210575)
also warns against making metrics the objective. Preserve behavior and cohesive
interfaces rather than splitting code merely to lower a score.

Keep intent, authority, rationale and unencoded requirements alongside executable
checks; both can become wrong or stale. Gherkin needs
[step implementations](https://cucumber.io/docs/cucumber/step-definitions/)
and meaningful assertions. Agent-written QA is not independent ground truth.
Prefer supported controls at the action boundary for consequential constraints,
and verify their enforcement; when unavailable, disclose the limit of guidance.
Choose reviewer roles and fresh contexts by actual risk and coordination cost,
not a fixed five-Agent pipeline. Changes to checks need affected review and
counterexamples, not permission to redefine an unmet requirement as a pass.

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
