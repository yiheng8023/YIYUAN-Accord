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

For any proposed capability route, list additions to the bound goal, input,
deliverable, human round trip, authority, side effect, and acceptance surface.
An addition without source-bound causal necessity is a route defect, not a
contribution prerequisite.

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
