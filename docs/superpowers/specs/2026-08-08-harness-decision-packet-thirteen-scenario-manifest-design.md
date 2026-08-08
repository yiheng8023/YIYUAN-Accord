# Harness Decision Packet Thirteen-Scenario Manifest Design

Date: 2026-08-08
Status: owner-approved design; implementation not started
Repository: `agent-autonomy-harness`

## Purpose

Extend the verified single-scenario decision-packet core into a deterministic,
zero-model carrier for all thirteen scenarios in the current human-AI
collaboration coverage authority. The extension must preserve heterogeneous
source truth instead of pretending that every evidence document exposes the
same scenario-record shape.

The deliverable is an atomic summary manifest. It records the binding mode,
source and authority digests, packet digest, decision state, and claim ceiling
for each scenario. Complete packets remain reproducible on demand and are not
duplicated in the manifest.

This is a Harness product-engineering and mechanism-validation task. It does
not require an invented external task, and it does not authorize task-time
activation.

## Product And Authority Position

The mechanism belongs to the independent Agent-neutral Harness. It is not a
Plugin, Skill, lifecycle manager, live router, or second semantic authority.
Plugins remain consumer projections. CC Switch and host-native managers remain
the sole lifecycle authorities for the components they manage.

The distribution posture remains:

```text
plugin-compatible + manager-agnostic + release-not-eligible
```

The current coverage reconciliation continues to determine:

- the exact thirteen-scenario set;
- each scenario's original evidence source paths;
- all six route classes and their evidence states;
- fallback order and explicit unassessed cells; and
- the current claim ceiling.

The new scenario-evidence binding registry only declares how to locate or
classify scenario identity in heterogeneous original sources. It cannot add a
scenario, redirect a source, select a route, strengthen evidence, grant
authority, or replace the coverage reconciliation.

## Scope

The implementation will:

1. preserve the existing request and packet v1 contracts and their
   `GEN-RESEARCH-01` fixture;
2. define a strict scenario-evidence binding registry for exactly the current
   thirteen scenarios;
3. define a packet v2 contract that makes the binding mode and normalized
   binding result explicit;
4. build and independently validate one canonical packet v2 for every current
   scenario;
5. emit one atomic summary manifest containing thirteen packet references;
6. fail closed without a partial manifest when any scenario fails;
7. add deterministic positive and mutation tests; and
8. update only the plan, acceptance, continuation, and public navigation
   surfaces that would otherwise become stale.

The implementation will not parse natural language, use a real task, select or
invoke a route, run a model or candidate, install or enable a capability,
connect an account, mutate CC Switch or a consumer, publish, release, or claim
behavior, value, portability, production readiness, or a residual gap.

## Versioning

Packet v1 is frozen. Its schema, builder behavior, fixture bytes, and verified
single-scenario evidence remain valid.

Packet v2 reuses the structured request v1 contract and the current v1
authority, route, fallback, authorization, claim, and digest semantics. It
adds one exact top-level `scenarioEvidenceBinding` object. This avoids changing
the meaning or accepted field set of packet v1.

The batch manifest has its own version-one schema. Its version is independent
of the packet version it references.

## Scenario-Evidence Binding Registry

The repository-authored registry is governed by a strict schema and contains
exactly one entry per current coverage row. Each entry contains:

- `scenarioId`;
- `sourcePath`;
- `bindingMode`;
- mode-specific identity pointers;
- `scenarioIdentityPresentInSource`;
- the additional binding evidence ceiling; and
- an explanation restricted to the source-shape distinction.

JSON Pointer is the only locator syntax. Pointers address identity-bearing
scalar fields, not arbitrary text. The registry must not embed or rewrite any
third-party payload or historical evidence body.

### `scenario-record`

For eleven scenarios, one or more declared pointers resolve to the requested
scenario ID. Every pointer must resolve, every resolved value must equal the
requested ID, and at least one pointer must exist. Multiple pointers are
allowed only when the bound source intentionally contains multiple records for
the same scenario, as it does for `SE-OPS-INCIDENT-01`.

The planned bindings are:

| Scenario | Identity pointer or pointers |
| --- | --- |
| `GEN-CREATIVE-01` | `/scenarioBinding/scenarioId` |
| `GEN-RESEARCH-01` | `/scenarios/1/id` |
| `GEN-LEARNING-01` | `/scenarioBinding/scenarioId` |
| `GEN-ORG-DECISION-01` | `/scenarioBinding/scenarioId` |
| `GEN-ACCESS-COMMS-01` | `/scenarioBinding/scenarioId` |
| `SE-DISCOVERY-REQ-01` | `/behaviorallyObservedScenarioCells/0/scenarioId` |
| `SE-IMPLEMENT-REVIEW-01` | `/behaviorallyObservedScenarioCells/1/scenarioId` |
| `SE-RELEASE-CHANGE-01` | `/scenarioId` |
| `SE-OPS-INCIDENT-01` | `/behaviorallyObservedScenarioCells/2/scenarioId`, `/behaviorallyObservedScenarioCells/3/scenarioId` |
| `SE-MAINT-MIGRATE-01` | `/behaviorallyObservedScenarioCells/4/scenarioId` |
| `SE-MGMT-PRACTICE-01` | `/scenarioBinding/scenarioId` |

### `document-level-support`

`SE-ARCH-DESIGN-01` and `SE-VERIFY-SECURE-01` are bound by the current coverage
authority to the same lifecycle aggregate evidence document. That document's
own identity is `SE-E2E-THIN-01`; it does not expose either requested scenario
as an independent identity-bearing record.

For these entries:

- `scenarioIdentityPresentInSource` is exactly `false`;
- `/scenarioId` must resolve to `SE-E2E-THIN-01`;
- a recursive identity-field check must find no `scenarioId` field equal to
  the requested scenario and no `id` field under a `scenarios` array equal to
  the requested scenario;
- the coverage row must still bind the same aggregate source path; and
- the additional ceiling is
  `document-level-support-no-independent-scenario-identity`.

This mode records a governed coverage relationship. It does not convert an
aggregate mechanism result into atomic scenario evidence. If the source later
gains an independent identity-bearing scenario record, validation fails and
requires an explicit registry review instead of silently promoting the mode.

## Architecture

```text
current authorities + binding registry
                 |
                 v
        BindingRegistryValidator
        - exact scenario-set equality
        - exact source-path equality
        - mode-specific locator checks
                 |
                 v
     canonical mechanism probe requests
                 |
                 v
        DecisionPacketV2Builder
        - reuse v1 authority and route logic
        - attach normalized binding result
                 |
                 v
       DecisionPacketV2Validator
                 |
                 v
       ManifestBuilder (in memory)
                 |
                 v
          ManifestValidator
                 |
                 v
       canonical atomic serialization
```

Responsibilities stay separated:

1. the registry schema describes heterogeneous source binding;
2. the binding resolver executes JSON Pointers and returns a normalized result;
3. packet v2 construction reuses current decision semantics and adds the
   normalized result;
4. packet v2 validation independently reopens authorities and evidence;
5. the manifest builder extracts only approved summary fields; and
6. the manifest validator proves completeness, order, digests, and ceilings.

No scenario-specific branch belongs in the resolver. Differences reside in
the governed registry and its mode-specific schema.

## Canonical Probe Requests

The batch builder creates one deterministic request v1 per coverage row:

- `scenarioId` is the current row's ID;
- `evidenceLane` is `mechanism-validation`;
- `expectedSemanticAuthorityId` is the current authority ID;
- `observedAvailability`, `taskBinding`, `currentCapabilityGap`, and
  `activationAuthority` are `null`; and
- `requestId` is derived deterministically from the manifest schema and
  scenario ID.

These requests are mechanism probes only. They do not represent user tasks or
task-time routing attempts.

## Packet V2 Binding Object

`scenarioEvidenceBinding` contains:

- the binding-registry path, ID, and SHA-256 digest;
- `scenarioId` and `sourcePath`;
- `bindingMode`;
- the declared identity pointers and their resolved values;
- `scenarioIdentityPresentInSource`;
- `sourceScenarioId`, equal to the requested scenario for `scenario-record`
  and `SE-E2E-THIN-01` for `document-level-support`; and
- the binding-specific evidence ceiling.

All existing packet gates remain unchanged. In particular, `selectedRoute` is
`null`, authorization gates are all false, and the coverage claim boundary is
not raised. Packet v2 hashes include the complete normalized binding object.

## Summary Manifest Contract

The manifest contains:

- schema, ID, packet schema version, and manifest SHA-256;
- current semantic-authority, coverage, scheduler, acceptance, and
  binding-registry bindings;
- `atomic=true` and `scenarioCount=13`;
- one entry per scenario in current coverage order;
- for each entry: scenario ID, binding mode, source path and SHA-256, packet
  SHA-256, decision state, `selectedRoute=null`, and binding evidence ceiling;
- zero execution counters for models, candidates, Plugins, managers, accounts,
  consumers, installs, enablements, and publications;
- all-false authorization and claim boundaries; and
- the unchanged Plugin, manager, and consumer-projection boundary.

The manifest references packet digests and does not embed packet bodies. A
consumer can reproduce and validate the complete packet from the repository
sources and canonical probe request.

## Atomic Data Flow

1. Load and validate current semantic, coverage, scheduler, and acceptance
   authorities.
2. Load the binding registry and require exact ordered scenario-set and source-
   path equality with coverage.
3. Build canonical requests in coverage order.
4. Resolve and validate every source binding.
5. Build and independently validate every packet v2.
6. Collect packet summaries only after each packet passes.
7. Assemble and independently validate the thirteen-entry manifest in memory.
8. Serialize canonical JSON and compute the manifest digest over the body
   excluding its digest field.
9. Write to stdout by default. When an explicit output path is supplied, write
   a sibling temporary file and replace the target only after full validation.

No partial manifest is valid. A failed build creates no new target and leaves
an existing valid target byte-for-byte unchanged.

## Error Semantics

Any scenario failure produces one top-level `batch-binding-failed` error and
no manifest. Its `issues` array is ordered by current coverage order. Each
issue contains only `scenarioId`, stable error code, message, and source path.
Successful packet bodies are not included in error output.

Stable failure classes include:

- `binding-registry-missing` or `binding-registry-invalid`;
- `binding-scenario-set-drift`;
- `binding-source-path-drift`;
- `binding-mode-invalid`;
- `binding-pointer-invalid` or `binding-pointer-unresolved`;
- `binding-scenario-identity-mismatch`;
- `binding-aggregate-identity-drift`;
- `document-level-identity-promotion`;
- current-authority or original-source digest drift;
- packet v2 contract or digest failure;
- manifest entry omission, duplication, or order drift; and
- manifest digest mismatch.

Independent failures may be collected in one deterministic pass, but one
failure must never weaken another or permit partial output.

## Verification

### Positive cases

- Validate registry and schema exactness.
- Confirm exactly thirteen entries: eleven `scenario-record` and two
  `document-level-support`.
- Resolve every declared pointer against current source bytes.
- Build and independently validate all thirteen packet v2 values.
- Confirm all selected routes remain null and all gates remain false.
- Build the manifest twice and compare canonical bytes and SHA-256.
- Reproduce each manifest packet digest independently.
- Verify stdout-only operation changes no repository or external state.
- Verify explicit output uses atomic replacement.

### Mutation cases

Tests must reject at least:

1. one missing, extra, duplicated, or reordered registry scenario;
2. a source-path redirection;
3. an undeclared binding mode;
4. a malformed or unresolved JSON Pointer;
5. a pointer resolving to the wrong scenario;
6. removal of one of the two operations-scenario pointers;
7. either document-level entry marked as an atomic scenario record;
8. aggregate identity changed from `SE-E2E-THIN-01`;
9. an independent scenario identity appearing under document-level mode;
10. semantic, coverage, scheduler, acceptance, registry, or source digest
    drift;
11. route, fallback, authorization, claim, or residual-gap promotion;
12. a missing, duplicated, reordered, or altered manifest entry;
13. a packet digest or manifest digest mismatch; and
14. output failure that would otherwise overwrite an existing valid file.

Focused tests run first, followed by the complete local test suite and
`python -B scripts/verify.py`. GitHub Actions may corroborate the result but is
not the primary or sole acceptance surface.

## Implementation Shape

The implementation adds these focused contract and runtime surfaces:

- `schemas/harness-scenario-evidence-binding-registry-v1.schema.json`;
- `registry/harness-scenario-evidence-bindings-v1.json`;
- `schemas/harness-decision-packet-v2.schema.json`;
- `schemas/harness-decision-packet-manifest-v1.schema.json`;
- `scripts/harness_scenario_evidence_binding.py`;
- `scripts/harness_decision_packet_v2.py`;
- `scripts/harness_decision_packet_manifest.py`;
- `scripts/build_harness_decision_packet_v2.py` for one on-demand packet;
- `scripts/build_harness_decision_packet_manifest.py` for the atomic batch;
- focused tests and fixtures; and
- one dated validator plus machine-readable mechanism-evidence record.

Existing packet v1 files remain unchanged except for verifier integration or
shared helpers whose behavior is proven byte-compatible by the v1 fixture.

`scripts/verify.py` may call focused validators. It must not absorb binding,
packet construction, manifest construction, or mutation logic.

The implementation plan must preserve small, independently testable units and
must sequence schema and failing tests before implementation behavior.

## Acceptance And Claim Boundary

This slice reuses `acceptance.decision-ready-consumer-projection`. It adds
mechanism evidence but does not by itself change the criterion from `partial`
or create a new acceptance criterion. The expected program inventory remains
46 verified / 15 partial / 0 planned.

The slice may prove only that all thirteen current coverage scenarios can be
bound, packetized, and summarized deterministically without erasing the two
aggregate-source limitations.

It cannot prove natural-language interpretation, a real task, current host
availability, route correctness, instruction delivery, candidate causation,
behavior, value, cross-host portability, production readiness, release
eligibility, or a repository-authored residual gap.

It authorizes no install, enablement, account connection, candidate execution,
model dispatch, CC Switch or consumer mutation, publication, release,
acceptance promotion, or goal closeout.

## Documentation And Continuation

After implementation passes local deterministic verification:

- add a dated machine-readable and human-readable mechanism-evidence record;
- update the research and PoC plan with the exact proved boundary;
- add the new evidence reference to the existing partial acceptance criterion
  without changing its grade or inventory counts;
- append the latest repository-anchored continuation entry;
- update the goal-mode prompt only if its next-action or capability statement
  would otherwise be stale; and
- update README only if its current public capability description would
  otherwise be inaccurate.

Before each repository write and at closeout, verify branch, status, HEAD,
upstream, origin/main, ahead/behind, and relevant dirty files. Commit and push
the implementation only after focused tests, the full local suite, and the
repository verifier pass.
