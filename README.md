# Agent Autonomy Harness

English | [简体中文](README.zh-CN.md)

> Describe the outcome. Let the Agent work out which capabilities it needs.

Agent Autonomy Harness is an open research project for reducing the amount of
Agent and tool knowledge a person must carry into a task.

The intended experience is simple: the user states a goal, supplies facts and
judgment, and grants bounded authority. The Agent chooses a sufficient route
and task carrier, uses them safely, reconciles any split work, verifies the
result, and cleans up afterward.

**Research-stage status:** the repository currently contains the product
contract, acceptance model, deterministic verifier, an inactive Codex
`SessionStart` reference adapter, an inactive thin Codex plugin projection for
that adapter, a workspace discovery entry that exposes the projection as
available without installing it, and an inactive session-scoped Claude Code
projection over the same continuation semantics. It does not contain an Agent
runtime, an installed or behavior-accepted adapter, or accepted cross-host proof.

v0.2 is `active` on one bounded recovery of the already-requested Chinese
README first-screen delivery, and O1-O5 are still false. The
program now makes explicit that authorized product-plan delivery is real demand
when the primary purpose is the deliverable, rather than exercising or
diagnosing the Harness. The adapters only derive bounded continuation context
from the current repository authority. The host projections add no Skill,
MCP server, App, prompt interception, CC Switch dependency, or product
authority. Neither is persistently installed or enabled, and neither proves
runtime behavior or an outcome. The verifier is the current machine-readable
state source.

## The problem

Agent platforms keep gaining native features, tools, Skills, Plugins, Apps,
MCP servers, and other extensions. That growth is useful.

Users are still often expected to know what exists, choose the right route,
configure it, recover failures, verify completion, and remove residue.

The Harness asks whether that burden can move upstream to the Agent without
moving away the decisions that should remain human.

## The target experience

Imagine a user says:

> Audit this repository and make it ready for a public release. Do not publish
> anything until I approve it.

The target behavior is that the Agent:

1. understands the desired result and the publication boundary;
2. checks whether its healthy, authorized native capabilities are sufficient;
3. discovers or adds an external capability only if a real gap remains;
4. stays in the current task and checkout by default, creating a branch,
   worktree, repository fork, conversation fork, or new task only when
   isolation, parallelism, host capacity, or an authority boundary requires it;
5. owns synchronization, code merge or conclusion reconciliation, archive or
   release, and cleanup for any such carrier;
6. asks the user only for missing facts, consequential judgment, or new
   authority—not for tool names or invocation syntax;
7. executes, recovers, verifies, releases task-scoped capability exposure, and
   removes task-created residue;
8. returns the result and its evidence for accountable human judgment.

This is the product target, not a claim about current runtime behavior.

## What belongs to the Harness

| The Harness owns | The Harness reuses | The Harness does not become |
| --- | --- | --- |
| A demand-to-capability collaboration methodology | Healthy Agent-native behavior | A universal Agent runtime |
| An open minimum quality-conformance profile | Tool and Agent protocols such as MCP, A2A, or CHAP when suitable | A fixed capability catalog or marketplace |
| Measures for user burden, outcome quality, authority, evidence, recovery, code and conversation task-topology lifecycle, resource lifecycle, and cleanup | Existing discovery, identity, authorization, audit, provenance, Git, and host task primitives | A new wire protocol, Git or task manager, identity system, or audit format without a proven residual gap |
| Thin reference adapters that test the same semantics on real hosts | Maintained external implementations with source, version, license or terms, maturity, and boundary recorded | A replacement for human goals, domain judgment, consent, or final accountability |

Codex is the first reference host because it is a strong, practical test bed.
Codex-specific configuration remains outside the portable product core. A
distinct second host is required before any cross-host claim can pass.

## What exists today

The current repository provides:

- a machine-readable [constitution](product/constitution.json) for purpose and
  fixed boundaries;
- a [program](product/program.json) for the current causal work state;
- explicit [v0.2 acceptance criteria](product/acceptance.json);
- an [unaccepted candidate methodology and minimum quality profile](docs/DEMAND-TO-CAPABILITY-PROFILE.md)
  for exact pre-registration by future Codex cohort tasks;
- a standard-library-only verifier that rejects invalid authority, evidence,
  work graphs, and repository residue;
- an inactive, standard-library-only Codex `SessionStart` adapter candidate
  that projects current authority after startup, resume, clear, or compaction
  without reading prompt or transcript content or storing session state;
- an inactive, Hook-only Codex plugin projection that packages that adapter
  through the host's plugin boundary without turning the repository or portable
  core into a plugin;
- a workspace-scoped Codex marketplace entry that exposes only that projection
  as `AVAILABLE`; discovery does not install, enable, or trust it;
- an inactive, Hook-only Claude Code projection that translates the host's
  native `SessionStart` input and plain-stdout context output into the same
  repository-owned continuation semantics and can be exposed for one session
  without persistent installation;
- product tests for the public verification seam;
- a fixed-source external-landscape review that narrows what the project may
  build instead of duplicating existing layers.

It does not provide task execution, capability installation, live routing, or
an accepted quality profile today. The adapter is executable for offline
mechanism validation but is not installed in user configuration. Passing
repository checks proves that the current contract is internally valid; it does
not prove user value.

## Verify the repository

Prerequisites: Git and Python 3.10 or newer. No package installation, account,
or external service is required.

```powershell
git clone https://github.com/yiheng8023/agent-autonomy-harness.git
cd agent-autonomy-harness
python -B -m harness verify --root . --json
python -B -m unittest discover -s tests/product -v
```

The JSON report is the current state surface. See the
[continuation guide](docs/operations/CONTINUATION.md) for the work boundary.

## What v0.2 must prove

- **O1 — one closed loop:** one natural goal-level task completes without the
  user selecting, invoking, recovering, verifying, or cleaning the capability
  route or choosing, operating, merging, archiving, or cleaning code and
  conversation topology, and without a material collaboration-loss correction
  such as fixing misunderstood intent, reopened decisions, unrequested work,
  process bloat, residue, continuity failure, topology divergence, or a false
  completion claim.
- **O2 — repeated burden reduction:** at least three materially different
  natural tasks repeat that zero-loss floor and beat a source-bound ad-hoc
  baseline without losing task quality.
- **O3 — demand-driven capability lifecycle:** both a no-gap/native case and a
  real-gap/discovery case make bounded, evidence-backed route decisions and end
  task-scoped exposure.
- **O4 — calibrated methodology and quality profile:** the same pre-registered
  profile evaluates accepted and failed real-task receipts on the Codex
  reference host. It cannot claim Agent-neutral portability.
- **O5 — bounded cross-host proof:** the same task and core semantics produce
  accepted, equivalent outcomes on Codex and a distinct second Agent host or
  runtime through thin adapters.

For O1-O4, a natural task is a logical pre-registered demand-and-outcome unit,
not a Codex sidebar task or thread. Sequential receipts may remain in one
healthy host task, and one receipt may support more than one criterion only
when it independently meets each criterion's pre-registration and validation
burden. It cannot be counted twice toward one criterion's sample minimum.
An authorized product-plan delivery is already real demand when its primary
purpose is the needed deliverable; the excluded case is a task created mainly
to exercise or diagnose the Harness. This distinction does not waive
pre-registration, evidence, floors, or named-human acceptance.

Human authority, zero-trust evidence, lean independent authority, and bounded
process/resource loss are mandatory guardrails, not substitutes for outcomes.

## Design rules

- Start from the user's goal, not a named tool or catalog.
- Observe healthy authorized capability before searching for more.
- Add only for an evidenced residual gap; release task-scoped exposure when the
  need ends.
- Reuse sufficient protocols, runtimes, and evidence layers before composing or
  authoring anything new.
- Keep goals, consequential judgment, new trust, cost, publication, release,
  and irreversible actions under human authority.
- Claim only what source-bound evidence actually proves.

## Read, contribute, and report

| Need | Document |
| --- | --- |
| Understand the product boundary | [Product North Star](docs/strategy/PRODUCT-NORTH-STAR.md) |
| Apply the unaccepted Codex-first candidate profile | [Demand-to-capability profile](docs/DEMAND-TO-CAPABILITY-PROFILE.md) |
| Understand the technical separation of concerns | [Architecture](docs/architecture.md) |
| Inspect the proof sequence and external reuse gate | [Research and proof plan](docs/strategy/RESEARCH-AND-POC-PLAN.md) |
| Resume repository work | [Continuation](docs/operations/CONTINUATION.md) |
| See why earlier assets are not current authority | [History boundary](docs/operations/HISTORY.md) |
| Propose a focused change | [Contributing](CONTRIBUTING.md) |
| Read participation expectations | [Code of Conduct](CODE_OF_CONDUCT.md) |
| Ask a non-sensitive question | [Support](SUPPORT.md) |
| Report a sensitive vulnerability | [Security policy](SECURITY.md) |
| Support maintenance | [Sponsoring](SPONSORING.md) |

Repository-owned code and documentation are Apache-2.0 unless a file says
otherwise. Third-party material keeps its original rights.

See [LICENSE](LICENSE), [NOTICE](NOTICE),
[third-party notices](THIRD_PARTY_NOTICES.md), and the
[license policy](docs/license-policy.md).
