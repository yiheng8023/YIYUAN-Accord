# Contributing

Contributions should improve a mapped Agent Autonomy Harness product outcome
or mandatory guardrail. Research volume, candidate count, test count, and
governance artifacts are not independent contribution goals.

Before proposing work, name:

- the affected O1-O5 outcome or G1-G4 guardrail;
- the observed problem and current evidence;
- the causal hypothesis and falsifier;
- the smallest deliverable and finite stop condition;
- authority, data, cost, external dependency, rollback, cleanup, and claim
  boundaries.

A proposal is not a current program item. Put the fields above in the issue or
change description; do not add a `planned` increment or work item to
`product/program.json`. The current graph deliberately rejects speculative
queues. Change that graph only after maintainers bind the work as current: use
one `active` increment with exactly one `active` work item, or leave the paused
empty graph unchanged for a bounded guardrail repair.

For any proposed capability route, list additions to the bound goal, input,
deliverable, human round trip, authority, side effect, and acceptance surface.
An addition without source-bound causal necessity is a route defect, not a
contribution prerequisite.

Start capability proposals from goal-level demand and evidence about available
healthy routes. State the residual gap before naming a candidate or discovery
channel. A contribution must not require users to know or select a capability,
product, provider, catalog, channel, or invocation syntax, and must not make
one of those adaptive sources part of the portable product core.

External capabilities remain exact upstream and inactive until their own
review and state-transition gates pass. Installation, enablement, account
connection, dispatch, behavior, value, portability, acceptance, release, and
publication are distinct states.

Use Python 3.10 or newer. Run the canonical product checks from the repository
root:

```powershell
python -B -m harness verify --root . --json
python -B -m unittest discover -s tests/product -v
```

Do not run archived scripts or treat legacy green tests as current acceptance.
Do not submit credentials, private memory, account state, unsanitized consumer
configuration, restricted source bodies, or claims broader than the supplied
evidence. See [SECURITY.md](SECURITY.md), [NOTICE](NOTICE), and the
[license policy](docs/license-policy.md).
