# YIYUAN Accord

YIYUAN Accord is the derived glossary for the domain model defined by
`product/constitution.json`. It explains an open, Agent-neutral collaboration
reliability contract and evaluation framework without adding semantic
authority. Its broad mission concerns human-AI collaboration; its current
product surface concerns human-Agent work.

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

**Collaboration reliability contract**:
The portable commitments that keep goals, routes, authority, evidence, state,
effects and closure aligned without supplying a runtime or domain authority.
_Source_: `product/constitution.json#/domainModel/productCategory`,
`product/constitution.json#/purpose`
_Avoid_: control plane, workflow engine, infrastructure platform

**Host projection**:
A thin, replaceable expression of the portable contract in one Agent host.
_Source_: `product/constitution.json#/productBoundary/includes/3`,
`product/constitution.json#/productBoundary/hostRule`
_Avoid_: runtime, compatibility alias, permanent host integration

## Decision dimensions

**Intent**:
The current versioned goal, priority, constraint and phase.
_Source_: `product/constitution.json#/domainModel/decisionDimensions/0`,
`product/constitution.json#/kernel/0/commitment`
_Avoid_: prompt, initial request

**Capability**:
An actor's observed fitness to perform a bounded part of the current goal.
_Source_: `product/constitution.json#/domainModel/decisionDimensions/1`,
`product/constitution.json#/hostAdapterStandard/3/rule`
_Avoid_: installation, label, theoretical availability

**Authority**:
The bounded right to decide or act on a named resource and effect.
_Source_: `product/constitution.json#/domainModel/decisionDimensions/2`,
`product/constitution.json#/humanAuthority`
_Avoid_: capability, accountability

**Evidence**:
Information that supports a bounded claim at the consequence level asserted.
_Source_: `product/constitution.json#/domainModel/decisionDimensions/3`,
`product/constitution.json#/evidenceBoundary/claimRule`
_Avoid_: trace, artifact, confidence

## Cross-cutting objects

**State**:
The current source-bound facts, resources, constraints and unresolved items.
_Source_: `product/constitution.json#/domainModel/crossCuttingObjects/0`,
`product/constitution.json#/kernel/3/commitment`
_Avoid_: chat history, memory dump

**Effect**:
An observed material change to a resource, system, person or decision surface.
_Source_: `product/constitution.json#/domainModel/crossCuttingObjects/1`,
`product/constitution.json#/qualityInvariants/4`
_Avoid_: proposed action, claimed outcome

**Continuity**:
Preservation and reconciliation of the current goal and state across phases,
carriers and actors.
_Source_: `product/constitution.json#/domainModel/crossCuttingObjects/2`,
`product/constitution.json#/learnedFailureStandards/5/rule`
_Avoid_: copied history, implicit handoff

**Lifecycle**:
The path from observed gap through admission, operation, evaluation,
replacement and retirement.
_Source_: `product/constitution.json#/domainModel/crossCuttingObjects/3`,
`product/constitution.json#/evolutionPolicy`
_Avoid_: permanent installation

## Human and Agent roles

**Responsibility**:
The assigned duty to perform or review a bounded part of the collaboration.
_Source_: `product/constitution.json#/domainModel/roleDistinctions/1`,
`product/constitution.json#/humanAuthority`
_Avoid_: authority, liability

**Accountability**:
The named ownership of consequential judgment and its accepted residual risk.
_Source_: `product/constitution.json#/domainModel/roleDistinctions/3`,
`product/constitution.json#/humanAuthority/humanOwns/5`
_Avoid_: approval click, Agent self-assessment

**Residual gap**:
A consequential collaboration problem not sufficiently covered by healthy
native, maintained or accountable domain mechanisms.
_Source_: `product/constitution.json#/kernel/1/commitment`,
`product/constitution.json#/evolutionPolicy/principles/4`
_Avoid_: any inconvenience, missing feature

**Mechanism**:
A bounded intervention admitted for one evidenced residual gap with an owner,
verification method, cost and retirement trigger.
_Source_: `product/constitution.json#/evolutionPolicy/mechanismAdmissionRequires`,
`product/constitution.json#/evolutionPolicy/retirementRule`
_Avoid_: permanent layer, default feature

**Closure**:
A state transition supported by consequence-level evidence, reconciled effects
and explicit residual limits.
_Source_: `product/constitution.json#/kernel/4/commitment`,
`product/constitution.json#/qualityInvariants/8`
_Avoid_: summary, commit, test pass
