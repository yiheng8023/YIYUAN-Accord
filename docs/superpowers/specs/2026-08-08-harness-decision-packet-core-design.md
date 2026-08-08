# Harness Decision Packet Core Design

Date: 2026-08-08
Status: owner-approved design; implementation not started
Repository: `agent-autonomy-harness`

## Purpose

Build the first Agent-consumable vertical slice of the Harness portable core.
Given a structured, already-interpreted collaboration request, the slice emits
a deterministic, source-bound decision packet that preserves current coverage,
evidence ceilings, unknowns, authorization gates, claim limits, fallbacks, and
recheck triggers.

This is a real Harness product-engineering task in the portfolio-curation and
mechanism-validation lanes. It does not require the user to invent an external
domain task. A naturally occurring decision-relevant task remains necessary
before task-time activation or claims about instruction delivery, behavior,
value, portability, or production.

## Product Position

The decision packet core is part of the independent Agent-neutral Harness. It
is not a Plugin, Skill, manager, live router, or second semantic authority.
Plugins remain generated consumer projections. CC Switch remains a replaceable
operational manager for shared third-party Skills where suitable, while a
host-native plugin manager owns that host's plugin lifecycle. One component
must have one lifecycle authority.

The current distribution posture remains:

```text
plugin-compatible + manager-agnostic + release-not-eligible
```

The slice must not install, enable, execute, connect an account, dispatch a
model, publish, release, delete, or mutate CC Switch or a consumer environment.

## Scope

The first vertical slice will:

1. accept one structured `DecisionRequest`;
2. bind the current portfolio semantic authority, current human-AI
   collaboration coverage reconciliation, portfolio/task-time projection
   contract, and program acceptance map;
3. reopen the original evidence bound by the selected scenario;
4. preserve all six route classes and their evidence ceilings;
5. apply the scheduler-lane and claim-boundary rules;
6. emit and validate one deterministic `DecisionPacket`;
7. expose a thin stdout-first CLI;
8. prove fail-closed behavior with a positive fixture and mutation cases; and
9. add mechanism evidence without promoting acceptance or release status.

The first scenario is `GEN-RESEARCH-01`. It exercises represented native,
composition, and human-control routes; explicitly unassessed official and
external routes; and a residual route that remains
`not-eligible-no-residual-gap`.

## Non-Goals

The slice will not:

- parse or classify natural language;
- decide what the user "really means";
- select or invoke a live capability;
- infer current host availability from a static inventory;
- revive the deprecated adapted third-party routing projection;
- fill unassessed cells by discovery, installation, or authoring;
- prove candidate causation, instruction delivery, behavior, value,
  portability, or production readiness;
- establish a repository-authored Skill, Hook, Plugin, or manager gap;
- split or rewrite the whole legacy verifier; or
- add a new hard standard or acceptance criterion.

## Authority Model

### Current authority inputs

The builder binds these current repository surfaces:

- `registry/skill-portfolio-current-authority.json` for portfolio policy,
  lifecycle ownership, manager boundaries, and plugin posture;
- `registry/human-ai-collaboration-current-candidate-capability-coverage-reconciliation-2026-08-01.json`
  for the thirteen governed scenarios, six route classes, evidence ceilings,
  unassessed cells, fallbacks, and residual-gap dispositions;
- `registry/portfolio-tasktime-projection-contract-2026-08-06.json` for the
  portfolio-curation, mechanism-validation, task-time, and repository-authored
  gap-fill lanes; and
- `registry/program-acceptance-map.json` for current acceptance and evidence
  relationships.

For the selected scenario, the builder must reopen every path listed in
`evidenceSourcePaths`. The current coverage reconciliation is a derived
judgment; it cannot erase, strengthen, or replace the original evidence state.

### Historical inputs

`registry/capabilities.json`, `registry/routing.json`,
`registry/scenarios.json`, `registry/skills.json`, and `release-manifest.json`
belong to the deprecated adapted third-party release path. The builder must not
use them as current routing authority. They may be accepted only through a
future explicitly typed historical-comparison input.

### Current-task authority

Authority recorded inside historical evidence describes the historical trial.
It must be surfaced as evidence context but must not replace the current task's
independent authorization boundary. Conversely, current repository-write
authorization must not retroactively upgrade a historical experiment.

## Architecture

```text
structured DecisionRequest
        |
        v
request contract validation
        |
        v
AuthorityLoader
  - current semantic authority
  - coverage reconciliation
  - scheduler projection
  - acceptance map
  - original scenario evidence
        |
        v
DecisionPacketBuilder
  - preserve six route classes
  - preserve fallback order
  - compute decision state
  - compute authorization gates
  - compute claim ceiling
  - compute recheck triggers
        |
        v
DecisionPacketValidator
        |
        v
canonical JSON + SHA-256
```

The implementation has four bounded responsibilities:

1. `DecisionRequest` contract validation;
2. source and authority loading with explicit identity checks;
3. pure packet construction; and
4. independent packet validation plus canonical serialization.

A thin CLI composes those responsibilities. Agent, Skill, Plugin, and future
host adapters call the same interface rather than copying decision logic.

## DecisionRequest Contract

The version-one request is structured and solution-neutral:

```json
{
  "schema": 1,
  "requestId": "fixture.gen-research-01",
  "scenarioId": "GEN-RESEARCH-01",
  "evidenceLane": "portfolio-curation",
  "expectedSemanticAuthorityId": "skill-portfolio-current-authority-v1",
  "observedAvailability": null,
  "taskBinding": null,
  "activationAuthority": false
}
```

Rules:

- `portfolio-curation` and `mechanism-validation` do not require a real task.
- `task-time` is a valid lane, but it cannot yield an executable route without
  a bound task, current capability gap, dated live availability, and separate
  activation authority.
- The request cannot name a preferred Skill or candidate as the answer.
- Availability must be an explicit dated observation supplied by the caller;
  a catalog, installed directory, or static registry is not live availability.
- Request fields cannot grant permission or raise an evidence grade.
- The expected semantic authority ID must match the current repository record.

Version one implements the portfolio-curation path and the fail-closed
task-time insufficiency result. Live task-time route selection is outside this
slice.

## DecisionPacket Contract

Every successful packet contains:

- `schema`, `packetId`, and `packetSha256`;
- `authorityBinding`, including paths, IDs, and canonical source digests;
- the normalized `request`;
- `sourceEvidence`, including original status, evidence ceiling, and historical
  authority boundary;
- `routeCoverage` for all six route classes;
- the governed `fallbackOrder`;
- `decisionState` and nullable `selectedRoute`;
- `authorizationGates`;
- `claimBoundary`;
- `recheckTriggers`; and
- a statement that the packet is a derived projection rather than authority.

The route classes are:

| Code | Meaning |
| --- | --- |
| `N` | native |
| `O` | official or runtime-owned |
| `E` | reviewed external |
| `C` | composition |
| `H` | accountable human control |
| `R` | residual or repository-authored |

The packet must retain every class even when the class is unassessed or not
eligible. Absence is not a substitute for an explicit state.

For `GEN-RESEARCH-01`, the expected result is:

- `decisionState` is `coverage-packet-only`;
- `selectedRoute` is `null`;
- N, C, and H preserve their bounded evidence states;
- O and E remain `unassessed`;
- R remains `not-eligible-no-residual-gap`; and
- instruction-delivery, behavior, value, cross-host, production, and residual
  self-authored-gap claims remain false.

No wall-clock generation time participates in the canonical packet. Dated
facts come from bound sources or the request. This keeps fixture replay
deterministic.

## Data Flow

1. Validate `DecisionRequest` structurally.
2. Load and validate the expected current semantic authority.
3. Load the current coverage reconciliation and locate `scenarioId`.
4. Load the scheduler projection and current acceptance map.
5. Reopen every original evidence source bound by the scenario.
6. Compare derived route states and claim ceilings with their source limits.
7. Preserve all route classes and the governed fallback order.
8. Apply the selected scheduler lane.
9. Compute decision state, authorization gates, claim boundary, and recheck
   triggers.
10. Validate the completed packet independently.
11. Serialize canonical JSON and compute `packetSha256` over the packet body
    excluding the digest field.

The default CLI writes the canonical packet only to stdout. A future explicit
`--output` option may write a file, but version one does not require persistent
output outside checked-in fixtures and evidence.

## Error Semantics

### Contract or authority errors

These conditions are execution failures:

- invalid request schema;
- unexpected semantic authority ID;
- missing or malformed current authority;
- missing original evidence;
- source identity or digest drift;
- missing route class;
- derived evidence stronger than its source ceiling;
- deprecated routing elevated to current authority;
- fallback-order drift;
- authorization or claim promotion; or
- non-deterministic packet output.

The library raises a typed contract or authority error. The CLI emits a
machine-readable error to stderr, exits nonzero, and emits no normal packet.

### Valid but insufficient decisions

These are successful evaluations, not program failures:

- `needs-task-binding`;
- `needs-current-capability-gap`;
- `needs-live-availability`;
- `needs-activation-authority`; and
- `needs-human-judgment`.

The CLI exits zero and returns a packet with no selected execution route. A
consumer must not reinterpret a successful evaluation as successful task
execution.

## Implementation Shape

Implementation should add focused files rather than grow the legacy verifier:

- `schemas/harness-decision-request-v1.schema.json`;
- `schemas/harness-decision-packet-v1.schema.json`;
- a pure decision-packet library under `scripts/`;
- a thin builder CLI under `scripts/`;
- focused tests and fixtures under `tests/`;
- one dated mechanism evidence record under `registry/`; and
- the minimum plan, acceptance, continuation, goal-mode, and verification
  integration needed to keep projections consistent.

`scripts/verify.py` may import and call the focused repository validator. It
must not absorb the new construction or validation logic.

## Verification

### Positive verification

- Build the `GEN-RESEARCH-01` packet from repository sources.
- Validate request and packet schemas.
- Confirm all bound authority IDs, paths, and digests.
- Confirm all six route classes and the original fallback order.
- Confirm the expected evidence and claim ceilings.
- Replay the build and compare canonical bytes and digest.
- Confirm default stdout operation changes no repository or external state.

### Failure injection

The test suite must reject or safely block at least these cases:

1. unknown scenario;
2. semantic authority ID drift;
3. missing original evidence;
4. original evidence digest drift;
5. one route class removed;
6. an `unassessed` route promoted;
7. R promoted to an eligible repository-authored gap;
8. portfolio mode gains a selected execution route;
9. behavior, value, cross-host, or production claim promotion;
10. governed fallback-order drift;
11. deprecated routing restored as current authority;
12. task-time conditions missing while an execution route is selected;
13. historical experiment authority overriding current-task authority; and
14. Plugin or CC Switch becoming a portable-core dependency.

Targeted tests run before the repository-wide deterministic verifier. Hosted
CI may repeat these checks, but GitHub Actions is neither required nor
sufficient as the sole acceptance surface.

## Acceptance And Claim Boundary

The slice reuses `acceptance.decision-ready-consumer-projection`. It adds
mechanism evidence but does not by itself advance the criterion from `partial`
or add a new acceptance criterion. The canonical inventory is expected to
remain 46 verified / 15 partial / 0 planned.

The slice may establish only that:

- one structured scenario can produce a deterministic, source-bound packet;
- unknowns, evidence ceilings, authorization gates, and recheck triggers are
  retained;
- deprecated Skill routing is not current authority; and
- the packet core does not depend on a Plugin, CC Switch, or one host.

It cannot establish natural-language interpretation, live route correctness,
candidate invocation, instruction delivery, behavior, user value, cross-host
portability, production readiness, release eligibility, or a residual
self-authored need.

## Documentation And Continuation

If implementation passes its mechanism gate, update the current research plan,
program acceptance evidence mapping, goal-mode prompt, and continuation record
as projections of the current semantic authority. Update README surfaces only
if the implemented interface materially changes the public product shape.

The implementation commit and push close only this mechanism slice. Further
task-time behavior or live-plugin work remains behind its existing natural-task
and authorization gates.
