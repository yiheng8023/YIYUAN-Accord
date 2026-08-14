# Contributing

Agent Autonomy Harness is still a research-stage product contract, not a
released runtime.

Contributions should make its claims clearer, its evidence stronger, or its
verified implementation closer to O1-O5 without adding user burden or
duplicating an existing external layer.

## Start with the problem or outcome

You do not need to know the Harness criteria, repository workflow, capability
route, or verification commands before contributing. Start with:

- what you want to improve or what went wrong;
- what a good result would look like;
- the relevant facts you already know; and
- whether the material may contain credentials, private account state,
  personal data, or other sensitive content.

If you already have a revision, file, screenshot, safe log, or patch, include
it. Do not investigate the repository or learn a command solely to complete an
intake checklist.

Maintainers and their Agents own the safely discoverable mechanics: recovering
the current revision and affected artifacts, reconciling product authority,
mapping the work to O1-O5 or G1-G4, defining the smallest causal increment and
stop condition, selecting the route and task topology, running verification,
and cleaning up. They should ask a contributor only for a fact or decision that
cannot be discovered safely and that changes the next safe action.

## Small corrections

Typos, broken links, clearer wording, and narrowly scoped test repairs do not
need a full causal proposal. Describe what is wrong or send the smallest patch
you already have. Maintainers and their Agents run the relevant checks.

## What maintainers bind for product or behavior changes

Before a change that affects purpose, behavior, acceptance, authority,
capability routing, external dependencies, or lifecycle state becomes current
work, maintainers bind:

- the affected O1-O5 outcome or G1-G4 guardrail;
- the observed problem and evidence;
- the proposed cause-and-effect hypothesis and what would falsify it;
- the smallest deliverable and finite stop condition;
- authority, data, cost, rollback, cleanup, and claim boundaries.

A contributor may supply any of these details when they already know them, but
is not required to translate a goal or report into Harness program syntax. A
proposal is not automatically current work. Maintainers do not add a
speculative queue to `product/program.json`; they bind at most one active causal
increment and one active work item when the work becomes current.

Do not prebuild an outcome validator before its real task and evidence sources
are bound. Add only the smallest code path scoped to that exact causal
increment and criterion needed to falsify the event's claim; a self-reported
receipt shape is not outcome proof.

## How maintainers handle capability and external-layer changes

Maintainers start from the user's goal and the observed healthy, authorized
route. They name an external candidate only after identifying a residual gap or
when performing a bounded product-layer landscape review. A contributor does
not need to select a capability, provider, catalog, or invocation route.

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

## Verification

Maintainers and their Agents own the canonical checks. A contributor who
already has Python 3.10 or newer may also run them from the repository root:

```powershell
python -B -m harness verify --root . --json
python -B -m unittest discover -s tests/product -v
```

A contributor does not need to install Python or learn these commands merely to
report a problem or propose a bounded change. A green check proves only the
current repository contract. Claims about Agent behavior, user value,
portability, production, or release need their own evidence and acceptance.

Do not submit credentials, private memory, account state, unsanitized consumer
configuration, restricted source bodies, or claims broader than the supplied
evidence.

See [SECURITY.md](SECURITY.md), [NOTICE](NOTICE), and the
[license policy](docs/license-policy.md).
