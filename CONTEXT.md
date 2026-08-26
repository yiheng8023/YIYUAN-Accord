# YIYUAN Accord

YIYUAN Accord is the derived glossary for the domain model defined by
`product/constitution.json`. It explains an open, Agent-neutral and
mechanism-neutral collaboration system without adding semantic authority. Its
broad mission concerns human-AI collaboration; its current product surface
concerns human-Agent work.
`_Source_` selectors use stable IDs or exact declared values instead of array
positions, so reordering authority data cannot silently retarget a definition.

## Identity and scope

**YIYUAN Accord**:
The canonical project and product name. It always includes `YIYUAN`; `Accord`
means bounded, verifiable coordination rather than forced agreement.
_Source_: `product/constitution.json#/identity/displayName`
_Avoid_: Accord, ACCORD, unqualified generic labels, governance platform

**Human-AI mission**:
The long-term problem space covering collaboration between people and
intelligent systems.
_Source_: `product/constitution.json#/domainModel/missionScope`
_Avoid_: current verified product scope

**Human-Agent product scope**:
The currently implemented and evaluated surface for people working with
tool-using Agents through host projections.
_Source_: `product/constitution.json#/domainModel/currentProductScope`
_Avoid_: universal human-AI coverage

**Adaptive collaboration system**:
The portable reliability kernel plus context-tailored discovery, routing,
carriers, topology, continuity, verification and lifecycle mechanics that turn
a goal into a bounded outcome without becoming domain authority.
_Source_: `product/constitution.json#/domainModel/productCategory`,
`product/constitution.json#/purpose`
_Avoid_: thin contract alone, universal runtime, fixed workflow

**Host projection**:
A replaceable, scoped expression of the portable kernel and adaptive behavior
in a local, client or cloud Agent host.
_Source_: `product/constitution.json#/productBoundary/includes (value: replaceable-host-local-cloud-and-client-projections)`,
`product/constitution.json#/productBoundary/hostRule`
_Avoid_: product identity, permanent host binding, universal behavior proof

## Decision dimensions

**Goal**:
The current versioned goal, priority, constraint and phase.
_Source_: `product/constitution.json#/domainModel/decisionDimensions (value: goal)`,
`product/constitution.json#/kernel (id: K1)`
_Avoid_: prompt, initial request

**Requirement**:
A condition that a feasible route or completed outcome must satisfy, including
explicit constraints and material inferred omissions subject to correction.
_Source_: `product/constitution.json#/domainModel/decisionDimensions (value: requirement)`,
`product/constitution.json#/kernel (id: K1)`
_Avoid_: implementation step, assumed preference

**Capability**:
An actor's observed fitness to perform a bounded part of the current goal.
_Source_: `product/constitution.json#/domainModel/decisionDimensions (value: capability)`,
`product/constitution.json#/hostAdapterStandard (id: H4)`
_Avoid_: installation, label, theoretical availability

**Authority**:
The bounded right to decide or act on a named resource and effect.
_Source_: `product/constitution.json#/domainModel/decisionDimensions (value: authority)`,
`product/constitution.json#/humanAuthority`
_Avoid_: capability, accountability

**Evidence**:
Information that supports a bounded claim at the consequence level asserted.
_Source_: `product/constitution.json#/domainModel/decisionDimensions (value: evidence)`,
`product/constitution.json#/evidenceBoundary/claimRule`
_Avoid_: trace, artifact, confidence

**Cost**:
The combined code, prompt, context, latency, money, cognition, interference,
recovery, maintenance and retirement burden of a route or mechanism.
_Source_: `product/constitution.json#/domainModel/decisionDimensions (value: cost)`,
`product/constitution.json#/learnedFailureStandards (id: L3)`
_Avoid_: price alone, code size alone

## Cross-cutting objects

**Context**:
The current task, host, model route, environment, capability exposure and
evidence conditions that can change which factors apply.
_Source_: `product/constitution.json#/domainModel/crossCuttingObjects (value: context)`,
`product/constitution.json#/productBoundary/hostRule`
_Avoid_: transcript alone, permanent global setting

**State**:
The current source-bound facts, resources, constraints and unresolved items.
_Source_: `product/constitution.json#/domainModel/crossCuttingObjects (value: state)`,
`product/constitution.json#/kernel (id: K4)`
_Avoid_: chat history, memory dump

**Effect**:
An observed material change to a resource, system, person or decision surface.
_Source_: `product/constitution.json#/domainModel/crossCuttingObjects (value: effect)`,
`product/constitution.json#/qualityInvariants (value: material side effects are attributable and are stopped, recovered or rolled back where the effect permits)`
_Avoid_: proposed action, claimed outcome

**Continuity**:
Preservation and reconciliation of the current goal and state across phases,
carriers and actors.
_Source_: `product/constitution.json#/domainModel/crossCuttingObjects (value: continuity)`,
`product/constitution.json#/learnedFailureStandards (id: L6)`
_Avoid_: copied history, implicit handoff

**Topology**:
The selected code carriers and conversation carriers through which work and
state move, including their synchronization, handoff and cleanup relations.
_Source_: `product/constitution.json#/domainModel/crossCuttingObjects (value: topology)`,
`product/constitution.json#/hostAdapterStandard (id: H8)`
_Avoid_: branch alone, copied conversation alone, user-operated routing

**Lifecycle**:
The path from observed gap through admission, operation, evaluation,
replacement and retirement.
_Source_: `product/constitution.json#/domainModel/crossCuttingObjects (value: lifecycle)`,
`product/constitution.json#/evolutionPolicy`
_Avoid_: permanent installation

## Human and Agent roles

**Responsibility**:
The assigned duty to perform or review a bounded part of the collaboration.
_Source_: `product/constitution.json#/domainModel/roleDistinctions (value: responsibility)`,
`product/constitution.json#/humanAuthority`
_Avoid_: authority, liability

**Accountability**:
The named ownership of consequential judgment and its accepted residual risk.
_Source_: `product/constitution.json#/domainModel/roleDistinctions (value: accountability)`,
`product/constitution.json#/humanAuthority/humanOwns (value: accountable-final-judgment)`
_Avoid_: approval click, Agent self-assessment

**Representative outcome**:
A bounded real task used to test one complete goal-to-effect path and its claim
limits without presenting the sample as universal product coverage.
_Source_: `product/program.json#/increment/representativeOutcome`
_Avoid_: demonstration artifact, test suite, universal use case

**Route**:
A current, derived path through capabilities, carriers and evidence that can
satisfy a bound outcome within authority and total lifecycle cost.
_Source_: `product/program.json#/increment/fourSurfaceMapping/process/routeRule`
_Avoid_: fixed workflow, preferred product, installed capability

**Residual gap**:
A consequential collaboration problem not sufficiently covered by healthy
native, maintained or accountable domain mechanisms.
_Source_: `product/constitution.json#/kernel (id: K2)`,
`product/constitution.json#/evolutionPolicy/principles (value: residual-gap-fill)`
_Avoid_: any inconvenience, missing feature

**Mechanism**:
A bounded means for creating, observing, controlling, recovering or verifying
an effect, admitted with scope, applicability, owner, evidence, cost, rollback
and retirement semantics.
_Source_: `product/constitution.json#/evolutionPolicy/mechanismAdmissionRequires`,
`product/constitution.json#/evolutionPolicy/retirementRule`
_Avoid_: product goal, automatically active feature, permanently forbidden carrier

**Applicability**:
The conditions under which a visible or installed factor becomes active for
the current goal, plus its priority, override, degradation, expiry and
retirement relations.
_Source_: `product/reshaping-guidance.json#/factorApplicabilityContract`
_Avoid_: global visibility, installation, unconditional SOP

**Dynamic index**:
A source- and freshness-bound query view that joins durable semantic records
with current environment observations without turning a snapshot into truth.
_Source_: `product/reshaping-guidance.json#/dynamicIndex`
_Avoid_: manually duplicated catalog, committed host snapshot, authority replacement

**Graph projection**:
A derived node-and-edge view used to find feasible routes, affected evidence
and retirement dependencies; it does not imply a graph database.
_Source_: `product/reshaping-guidance.json#/dynamicIndex/graphProjection`
_Avoid_: second source of truth, mandatory database

**Closure**:
A state transition supported by consequence-level evidence, reconciled effects
and explicit residual limits.
_Source_: `product/constitution.json#/kernel (id: K5)`,
`product/constitution.json#/qualityInvariants (value: completion is supported by external criteria and observed effects rather than model self-assessment or artifact shape)`
_Avoid_: summary, commit, test pass
