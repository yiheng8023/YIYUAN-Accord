# Contributing

Agent Autonomy Harness is still a research-stage product contract, not a
released runtime.

Contributions should make its claims clearer, its evidence stronger, or its
verified implementation closer to O1-O5 without adding user burden or
duplicating an existing external layer.

## Small corrections

Typos, broken links, clearer wording, and narrowly scoped test repairs do not
need a full causal proposal. Explain what was wrong, make the smallest change,
and run the relevant checks.

## Product or behavior changes

For a change that affects purpose, behavior, acceptance, authority, capability
routing, external dependencies, or lifecycle state, describe:

- the affected O1-O5 outcome or G1-G4 guardrail;
- the observed problem and evidence;
- the proposed cause-and-effect hypothesis and what would falsify it;
- the smallest deliverable and finite stop condition;
- authority, data, cost, rollback, cleanup, and claim boundaries.

A proposal is not automatically current work. Do not add a speculative queue to
`product/program.json`. Maintainers bind at most one active causal increment and
one active work item when the work becomes current.

Do not prebuild an outcome validator before its real task and evidence sources
are bound. Add only the smallest task- and criterion-scoped code path needed to
falsify that event's claim; a self-reported receipt shape is not outcome proof.

## Capability and external-layer changes

Start from the user's goal and the observed healthy, authorized route. Name an
external candidate only after identifying a residual gap or when performing a
bounded product-layer landscape review.

Bind every decision-relevant external capability or product layer to its exact
source, version or commit, license or applicable terms, maturity, and intended
reuse boundary.

Prefer reuse or a thin adapter when an existing layer is sufficient.
Composition requires an integration gap; new implementation requires a
repeatable residual semantic gap.

Do not make users learn a provider, catalog, product, or invocation syntax
merely to contribute to the Harness.

Installation, enablement, account connection, live execution, persistent
activation, publication, and release are separate operations and require their
own authority. A reviewed candidate remains inactive by default.

## Verify the change

Use Python 3.10 or newer and run the canonical checks from the repository root:

```powershell
python -B -m harness verify --root . --json
python -B -m unittest discover -s tests/product -v
```

A green check proves only the current repository contract. Claims about Agent
behavior, user value, portability, production, or release need their own
evidence and acceptance.

Do not submit credentials, private memory, account state, unsanitized consumer
configuration, restricted source bodies, or claims broader than the supplied
evidence.

See [SECURITY.md](SECURITY.md), [NOTICE](NOTICE), and the
[license policy](docs/license-policy.md).
