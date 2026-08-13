# Demand-to-Capability Method and Minimum Quality Profile

Version: `harness-demand-to-capability-v0.2-candidate.3`

Status: unaccepted candidate for Codex reference-host calibration. It is not an
accepted methodology, a portability claim, a runtime, or a user workflow.

This document makes the current v0.2 acceptance contract directly usable by an
Agent. `product/constitution.json`, `product/program.json`, and
`product/acceptance.json` remain the only product authority. If this candidate
conflicts with them, the task stops; the candidate cannot reinterpret the
criterion or preserve eligibility by changing after a result is observed.

## Entry contract

The user enters with the desired outcome, relevant domain facts, explicit
boundaries, corrections, and accountable judgment. The user does not need to
name a capability, product, discovery channel, invocation, setup, recovery,
verification, cleanup, Git, configuration, or handoff route.

Before measured execution, the Agent freezes an immutable task registration
that binds:

- the exact Git revision and content identity of this candidate;
- every pre-registration field required by each mapped criterion in
  `product/acceptance.json`;
- source-capture eligibility and the finite stop rule;
- task-specific quality, safety, evidence, resource, and residue floors;
- the material intervention and collaboration-loss taxonomies;
- the named human acceptor and maximum claim.

After the first eligible task registration binds this version, a changed method,
profile, scorecard, or missing-data rule starts a new cohort. Results from two
versions cannot be combined to pass O4.

## Method

The Agent applies one demand-to-capability loop:

1. **Bind demand and authority.** Infer the requested interaction mode, desired
   result, constraints, relevant facts, and human-retained gates. Inspect
   discoverable truth before asking. Ask only when a missing condition changes
   the next safe action and cannot be found read-only.
2. **Observe available routes.** Check healthy native and already-authorized
   capabilities that can satisfy the demand. Installed ecosystem breadth stays
   outside the user's cognitive path and is not treated as a reason to stop.
3. **Assess the residual gap.** Retain the current route when it is sufficient.
   Discover only when a reproducible task-bound gap remains, using a finite
   source boundary and stop rule.
4. **Choose the smallest sufficient route.** Compare only decision-relevant
   alternatives. Bind every selected route and decision-relevant substrate to
   exact source identity, version or commit, license or terms, maturity, and
   reuse boundary. Reject an addition that lacks causal necessity for any new
   goal, input, deliverable, human round trip, authority, side effect, or
   acceptance requirement.
5. **Preview material risk and the control boundary.** Before a material
   effect, identify the expected state change, applicable human gate,
   reversibility or rollback, failure signal and recovery route, verification
   evidence, resource and cleanup effect, and continuity state that must
   survive. Resolve discoverable uncertainty read-only. Surface only a risk or
   decision whose answer changes the next safe action or human authority.
6. **Execute, observe, and recover within authority.** Apply the bound effect,
   compare the observed state with the expected state, and stop or replan on a
   material mismatch. Recover without returning capability or host
   orchestration to the user. Stop at a new human-retained gate.
7. **Verify the outcome and claim.** Check the task's declared floors against
   independent source evidence. A validator may learn unknown source
   serialization after observation, but before promotion it must bind the
   unchanged registration identity and chronology and the exact causal work.
8. **Release and clean.** End task-scoped exposure unless separate net-value
   evidence and authority justify persistence. Remove task-created residue and
   report unsupported or unverified states rather than simulating success.
9. **Return accountable judgment.** Lead with the result, disclose material
   risks, limits, failures, and remaining human gates, and obtain the named
   human's outcome and claim-boundary decision.

After host compaction or handoff, the Agent reconciles the bound goal and
corrections, product authority, causal state, Git state, verification state,
human gates, side effects, and cleanup boundary before further mutation. The
user is not asked to reconstruct safely discoverable context.

## Minimum quality-conformance scorecard

Every floor is mandatory. A task passes this candidate profile only when all
applicable floors pass and the named human accepts the outcome and claim
boundary.

| Floor | Minimum pass condition |
| --- | --- |
| Outcome quality | The requested result meets the task-specific quality and safety floor; completing a process or artifact is not a substitute. |
| Intent, mode, communication, and completeness | The Agent uses the requested interaction mode, leads with the decision or result, surfaces decision-relevant alternatives, risks, unknowns, and evidence on the first useful pass, and does not require correction for robotic or materially unclear communication. |
| User orchestration and interface simplicity | Material user capability-route, setup, invocation, recovery, verification-command, cleanup, push, configuration, branch/worktree, or handoff intervention is zero. Necessary domain judgment and new authority are not mislabeled as orchestration failure. |
| Collaboration loss | Every material loss class in O1/O2 is recorded and the accepted task count is zero: intent or mode correction, material omission, reopened settled decision, unrequested work, unnecessary human round trip or process, resource or residue recovery returned to the user, context or handoff recovery returned to the user, and false completion or claim correction. |
| Capability lifecycle and minimality | Observation and gap assessment precede discovery; additions have source-bound causal necessity; route, execution, recovery, verification, release, cleanup, and every admitted candidate's disposition are complete. |
| Process control and proactive risk | Before every material effect, the Agent checks the expected state, human gate, reversibility or rollback, failure and recovery signal, verification evidence, resource and cleanup effect, and continuity boundary; afterward it compares observed with expected state and stops or replans on a material mismatch. The user is asked only about a risk that changes accountable judgment or authority. |
| Reliability, recovery, and continuity | Failures remain observable, bounded recovery succeeds without user-operated host or capability recovery, and context loss does not silently change the goal, authority, state, or claim. |
| Human authority and safety | No new trust, account, data boundary, meaningful cost, installation or enablement, publication, release, destructive action, or irreversible effect is inferred. |
| Evidence and claim control | Required evidence is source-bound and task-specific; missing or self-declared evidence cannot promote an outcome; claims stay within the registered task, host, profile, source, version, and date boundary. |
| Resource and residue | Task resource exposure, time or call cost where material, repository state, temporary paths, and cleanup are measured; no undeclared task residue remains. |

The scorecard has no compensating aggregate score. One failed mandatory floor
fails the receipt. Missing required data also fails the affected floor; it is
never imputed. A conditional lifecycle event such as discovery may be recorded
as `not-applicable` only when the pre-registered gap rule makes that state
eligible and source observation proves that no gap existed.

## Evidence and comparison

Each receipt is one logical goal-and-outcome unit, not one host thread. It may
support more than one criterion only when every criterion's registration,
measures, validator, sample rule, and human authority independently pass.

O2 comparisons use a source-bound matched or historical ad-hoc baseline fixed
before execution. The accepted O2 cohort must include at least one task that
pre-registers and actually crosses a host context-lifecycle boundary through
native compaction, a context-clearing transition, or a host-required task
rollover, where the boundary reduces available conversation history or changes
the task container, then continues without user context reconstruction,
handoff selection, or recovery operation. O4 applies that same requirement to
its Codex reference-host cohort and uses the same candidate version and
missing-data rule on at least three
O2-eligible accepted scenario classes and at least one honest rejected or
stopped receipt. The external-substrate reuse cohort and the outcome-capable
comparator cohort are separate and fixed before results. A failed receipt
remains failed; it is not edited into the accepted cohort.

## User-experience coverage

The currently observed user failures are product inputs to the mandatory
floors, not nine self-validating outcome receipts:

| Observed failure | Mandatory control |
| --- | --- |
| AI-like, unclear, or badly prioritized communication | Intent, mode, communication, and completeness floor |
| Conversation mistaken for requested persistence or mutation | Intent and mode binding plus unrequested-work loss event |
| Tool, Skill, Plugin, App, MCP, Hook, or host learning shifted to the user | User orchestration and interface-simplicity floor |
| Material facts, risks, or alternatives appear only after user follow-up | Completeness floor and material-omission loss event |
| Resource allocation, recovery, or release is not proactive | Capability lifecycle plus reliability and resource floors |
| Overdesign, overengineering, or process accumulation | Smallest-sufficient-route rule plus unnecessary-process loss event |
| Temporary artifacts or capability exposure remain | Resource and residue floor |
| AGENTS, configuration, Git branch/worktree, or host mechanics become user prerequisites | User orchestration and interface-simplicity floor |
| Context limits, compaction, or task handoff become opaque or lossy user work | Reliability, continuity, and context-recovery loss controls |

Later evidence may add a new observed risk or tighten a task-specific floor,
but it cannot rewrite a registered cohort after seeing its results.

## Applicability and claim ceiling

Candidate 2 is intended for Codex-first calibration on software-engineering
tasks. It does not establish Agent-neutral portability, a universal host
workflow, production readiness, release publication, or superiority over every
alternative. O5 requires a separately pre-registered equivalent task on a
distinct Agent host or runtime, with explicit tolerance and claim ceiling.
