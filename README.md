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
`SessionStart` reference adapter, an inactive thin Codex plugin source candidate
with one task-facing Skill and that continuation Hook, a workspace discovery
entry that exposes the projection as available without installing it,
content-addressed stopped Codex results, and an inactive session-scoped Claude
Code projection over the same continuation semantics. It does not contain an
Agent runtime, a persistently installed or behavior-accepted adapter, or
accepted cross-host proof.

v0.2 is `active` on one pre-registered matched O5 source-candidate gate. O1
through O4 are verified (`4/5` outcomes); O5 remains unverified. O1 is
supported by the accepted public-intake, Codex Skill-source, and Claude
Skill-source results. O3 binds
those three route decisions across native retention and finite official
discovery or adaptation. O2 instead binds the materially distinct
public-intake, Codex Skill-source, and continuation-reconciliation scenarios;
the similar Claude and Codex Skill deliveries are not double-counted. The
accepted continuation result replaces a 6,301-character active-work projection
that exceeded Codex's 4,096-character Hook limit with a bounded read-only
authority, active-work, and Git reconciliation checkpoint. O4 applies the
unchanged candidate.5 profile and scorecard to that exact three-scenario cohort
plus one honestly stopped plugin-rollover case. The task-bound validator and
named-human bounded judgment accept only this Codex 0.147.0 Windows reference-
host calibration: aggregate registered user orchestration falls from 8 to 0,
two accepted native-compaction crossings recover without user reconstruction,
and the failed Hook-chronology floor remains failed. It does not verify O5,
installed Hook value, general context management, release, or production. The
program makes explicit that authorized product-plan delivery is real demand
when the primary purpose is the deliverable, rather than exercising or
diagnosing the Harness.

The active O5 task asks Codex CLI 0.147.0/gpt-5.6-sol and distinct-host Claude
Code 2.1.232/claude-sonnet-5 to perform the same independently useful, read-only
source-candidate gate on exact commit `48ef653`. The registration freezes the
prompt, supported common schema, host and adapter identities, minimum tool
surfaces, equivalence tolerance, explicit unknown-context rule, cleanup floor,
and claim ceiling before either model runs. A matched fact-grounded `blocked`
decision can pass; no result, model execution, cross-host acceptance, release,
or completion is claimed yet.

The Codex source candidate projects the Codex-reference-calibrated candidate.5
method through one concise
implicitly invocable Skill; its Hook and the Claude projection only derive
bounded continuation context from current repository authority. Neither host
projection adds an MCP server, App, prompt interception, CC Switch dependency,
runtime, or product authority. Neither is persistently installed or enabled.
One temporary Codex continuity task delivered the expected Skill plus startup
and post-compaction projections but stopped when required native Hook lifecycle
records were unavailable. A later fixed-source review stopped before the
conditional Claude call: an isolated `CODEX_HOME` still exposed an unrelated
user-global code-review Skill, which selected an unregistered parallel route and
the single Codex call timed out without a final result. A subsequent closeout
decision task successfully excluded 24 non-Harness Skills and disabled
multi-agent, but its immutable structured-output schema was rejected before
model generation because one constant property lacked the explicit type
required by the host. A later context-carrier decision passed that corrected
schema and the same Skill and topology preflight, but the single Codex call then
used the built-in `list_mcp_resources` surface and enumerated 46 ambient App
plugin and Skill descriptors. That unregistered capability and data boundary
triggered the fixed stop; the process was terminated and the conditional Claude
call did not run. All task-created state was cleaned, and every stopped attempt
counts as zero O1-O5 progress.

Current Codex exposes task-scoped native controls for inspecting the
model-visible prompt, disabling an exact Skill, and disabling multi-agent tools.
For a future measured dispatch, the Agent—not the user—must inspect visible
capabilities, reject only the causally inapplicable routes through per-invocation
configuration, and fail closed when the intended capability and topology cannot
be proven. The plugin does not override the user's broader capability inventory.
The parent must also bind a schema that the exact host accepts before consuming
the task's only allowed model call; general JSON Schema validity alone is not
host-compatibility evidence. Prompt-visible Skill exclusion is likewise not a
complete tool or data-boundary preflight: the current measured Codex route is
ineligible until an official stable per-call seam can bound ambient MCP/App
resources while retaining the required read-only repository operations. A
subsequent no-auth, no-plugin, no-model Codex 0.147.0 app-server probe verified
that `apps._default.enabled=false` is honored per process: it reported zero
installed or callable Apps and zero MCP servers. The same isolated home still
discovered 39 enabled Skills—33 from the replaceable CC Switch shared root and
six Codex system Skills—so home isolation alone is not capability isolation and
CC Switch is not a Harness dependency. The probe could not prove the later
thread-specific model tool specification or repository-tool coexistence; future
registrations must preflight those exact surfaces and constrain unauthorized
resources, invocation, and effects rather than demand the absence of harmless
host plumbing without causal need. This is a parent-dispatch constraint, not
authority to add a generic capability manager or control plane. The verifier is
the current machine-readable state source.

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
5. observes whether the current conversation remains a safe carrier and owns
   native compaction or verified handoff before preventable context loss;
6. owns synchronization, code merge or conclusion reconciliation, archive or
   release, and cleanup for any such carrier;
7. asks the user only for missing facts, consequential judgment, or new
   authority—not for tool names or invocation syntax;
8. executes, recovers, verifies, releases task-scoped capability exposure, and
   removes task-created residue;
9. returns the result and its evidence for accountable human judgment.

This is the product target, not a claim about current runtime behavior.

## What belongs to the Harness

| The Harness owns | The Harness reuses | The Harness does not become |
| --- | --- | --- |
| A demand-to-capability collaboration methodology | Healthy Agent-native behavior | A universal Agent runtime |
| An open minimum quality-conformance profile | Tool and Agent protocols such as MCP, A2A, or CHAP when suitable | A fixed capability catalog or marketplace |
| Measures for user burden, outcome quality, authority, evidence, recovery, context-carrier fitness and transition, code and conversation task-topology lifecycle, resource lifecycle, and cleanup | Existing discovery, identity, authorization, audit, provenance, Git, and host task primitives | A new wire protocol, context monitor, Git or task manager, identity system, or audit format without a proven residual gap |
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
- the exact [candidate.5 methodology and minimum quality profile](docs/DEMAND-TO-CAPABILITY-PROFILE.md),
  accepted only for the bounded O4 Codex reference-host calibration; its source
  bytes retain the pre-calibration status header frozen by registration;
- a standard-library-only verifier that rejects invalid authority, evidence,
  work graphs, and repository residue;
- an inactive, standard-library-only Codex `SessionStart` adapter candidate
  that projects a bounded current-authority, active-work, and read-only Git
  reconciliation checkpoint after startup, resume, clear, or compaction without
  reading prompt, transcript, session, diff, or dirty-path content or storing
  session state;
- an inactive Codex plugin source candidate with one task-facing Skill for the
  Codex-reference-calibrated method and one Hook that packages the continuation adapter, without
  turning the repository or portable core into a plugin;
- a workspace-scoped Codex marketplace entry that exposes only that projection
  as `AVAILABLE`; discovery does not install, enable, or trust it;
- one content-addressed stopped Codex continuity result showing that an exact
  temporary install delivered the Skill and both startup and compact
  projections, while preserving the missing native Hook-event evidence as a
  failed mandatory floor and restoring all consumer state afterward;
- an inactive Claude Code Skill-plus-Hook projection that reuses the same
  candidate method, translates native `SessionStart` input and plain-stdout
  context output into repository-owned continuation semantics, and can be
  exposed for one session without persistent installation;
- product tests for the public verification seam;
- a fixed-source external-landscape review that narrows what the project may
  build instead of duplicating existing layers.

It does not provide task execution, persistent capability installation,
accepted live routing, or an accepted quality profile today. The adapters are
not installed in user configuration. Passing repository checks and the stopped
live mechanism result do not prove accepted user value.

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
| Apply the bounded Codex-reference-calibrated candidate profile | [Demand-to-capability profile](docs/DEMAND-TO-CAPABILITY-PROFILE.md) |
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
