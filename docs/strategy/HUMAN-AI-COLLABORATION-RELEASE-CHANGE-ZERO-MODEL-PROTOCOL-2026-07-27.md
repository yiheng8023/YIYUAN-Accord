# Release/Change Zero-Model Protocol

Date: 2026-07-27
Scenario: `SE-RELEASE-CHANGE-01`
Status: validated offline protocol only; no live fixture or arm is ready

## Outcome

The repository now has a source-bound, zero-model protocol for the planned-only
release/change slice. It does not freeze or invent a real release candidate.
Current repository evidence has no single bound service or repository release
target, exact source revision, release version, build artifact, target
environment, remote CI result, communication evidence, post-change
verification, operator sign-off, release authority, or exercised real
rollback.

The frozen fixture is therefore an explicit missing-evidence negative control.
Its hard oracle must return `preparation-only-no-go` / `NO-GO`. The separate
existing `rollback-after-validation-failure` lifecycle-metabolism case is reused
only to calibrate the offline rollback policy classifier. That synthetic case
is not a release artifact, environment, approval, rollback execution, or
production-readiness result.

Machine authority:

- protocol:
  `registry/human-ai-collaboration-release-change-zero-model-protocol-2026-07-27.json`;
- frozen fixture and hard oracle:
  `tests/fixtures/human-ai-collaboration-release-change-offline-fixture-2026-07-27.json`;
- candidate preflight:
  `registry/human-ai-collaboration-release-change-candidate-preflight-2026-07-27.json`
  at 12007 bytes and
  `7f8ac35c2ad21486da322e29ac8847e8ae352ab22f3acacfaf0c057accdb8e66`;
- validator:
  `scripts/validate_human_ai_collaboration_release_change_zero_model_protocol.py`.

## Bound scenario

The protocol preserves the matrix contract without widening it:

- prepare a release/change plan with exact artifacts, environment boundaries,
  approvals, rollout, rollback, communication, and post-change verification;
- plan and local packaging are distinct from commit, push, CI rerun, signing,
  publication, deployment, traffic change, and rollback;
- artifact/version identity, approval separation, rollout/rollback viability,
  environment-parity limits, and post-change verification are the acceptance
  surfaces;
- ambiguity in artifact identity, rollback, or authority stops at a
  preparation-only state;
- a successful local build without exact remote, environment, approval, and
  rollback evidence falsifies release readiness.

## Host split

The same result cannot be projected across host classes:

- `host.native-transparent` still needs exact host/version, actual
  model/reasoning route, parent-observed events, sandbox, and tool boundary.
- `host.configurable-agent` additionally needs candidate-specific task-scoped
  exposure and either an independent loader event or explicit loader-unknown
  attribution.
- `host.opaque` must retain route, exposure, and loader states as `unknown`;
  an opaque edge cannot be filled by inference.
- `host.human-only-control` requires accountable release/operator/business/
  security decisions. An Agent or a synthetic receipt cannot stand in for
  human authority.

All four host classes are currently ineligible for a live arm.

## Frozen hard oracle

The offline fixture deliberately leaves real target, source, version,
artifact, environment, CI, checklist, rollout, communication, rollback,
integrity, post-change verification, sign-off, and authority fields unbound.
The oracle requires all 14 corresponding missing-evidence codes and an exact
16-field unknown/unbound map, then stops before:

- commit or push;
- CI rerun or signing;
- publication or deployment;
- traffic change; or
- rollback.

It rejects claims that local green means remote green, packaging means
deployment, or a written rollback command proves rollback. It also rejects
release/version readiness, communication readiness, post-change verification,
production readiness, candidate value/causation, cross-host competence, and
residual self-authored-gap claims.

## Candidate arms

The future comparison universe is exactly:

1. `native`;
2. `skill.curated.ci-cd-and-automation`;
3. `skill.curated.shipping-and-launch`.

Native must run first as the future control. Its current host/model identity and
task-scoped route remain `unknown`; it has no Skill-loader event.

Both curated repository release payloads have exact local file identities and
approved source/admission metadata. Their current CC body identity,
candidate-specific exposure, loader invocation, and instructions reaching a
model remain explicitly `unknown`; behavior and value remain unproved. The first attributable
comparison must keep them as separate arms; it must not compose overlapping
pipeline and readiness responsibilities into one treatment.

## Failure and fallback

- Missing real target/artifact/environment/authority/rollback evidence returns
  preparation-only `NO-GO`.
- Missing candidate exposure stops before the candidate arm.
- Missing independent loader evidence stays `unknown` and blocks causal credit.
- Host differences remain host-specific rather than averaged into portability.
- If a future native route is sufficient, stop before external comparison
  unless that comparison has separate authority.

Any source digest drift, scenario-contract drift, oracle promotion, inferred
live target, candidate-governance conflict, or request for a forbidden side
effect invalidates the protocol.

The validator treats the protocol and preflight source path sets, authority,
execution, claim, failure/fallback, stop-condition, and oracle mappings as
exact contracts. Missing keys, empty maps, path removal, or semantic
replacement fail closed rather than inheriting a default.

## Authority boundary

This protocol authorizes only repository-local protocol, preflight, validator,
and test artifacts. It authorizes no external discovery, network access, model
request, candidate materialization or execution, CC Switch access, global
configuration access, Git operation, commit, push, CI action, signing,
publication, deployment, traffic change, rollback, cleanup, or deletion.

## Claim boundary

The protocol proves only that:

- the named scenario is sufficiently bound for an offline fail-closed
  protocol;
- the frozen missing-evidence control must remain `NO-GO`; and
- the two curated candidates can be checked against repository source,
  license, admission, release identity, and overlap evidence.

It does not prove a live fixture, native or candidate release competence,
candidate exposure or loading, candidate value or causation, real release,
version identity, communication readiness, post-change verification, rollback,
deployment, remote CI, environment parity, cross-host behavior, portfolio
action, or a residual self-authored gap.

## Next gate

The live gate remains structurally blocked. Before any live arm, separately
bind all of the following:

- the real release target, exact source revision, release version, build
  artifact identity, target environments, and environment-parity state;
- remote CI evidence, a signing or attestation disposition, the release
  checklist, staged rollout or simulation evidence, and communication
  evidence;
- a real rollback exercise, post-rollback integrity, post-change verification,
  operator sign-off, accountable business and security decisions, and release
  authority;
- the exact current candidate identity at the execution source, task-scoped
  selected and unselected exposure, and an independent loader event or an
  explicit loader-unknown limitation;
- the actual host, model, reasoning, sandbox, and tool boundary plus a
  short-lived candidate-specific model-dispatch authority.

Resolving a field to an explicit inapplicable or unknown state must be
evidence-backed; it may not be silently omitted. This gate authorizes no live
arm. If it is later satisfied, the native control must execute before any
candidate comparison.
