# YIYUAN Accord

YIYUAN Accord is the derived glossary for the domain model defined by
`product/constitution.json`. It explains an open, Agent-neutral,
mechanism-neutral and product-form-neutral collaboration system without adding semantic authority. Its
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

**Complete bounded self-bootstrapping**:
Accord's bounded ability to sense the composed environment, bind the current
outcome and authority, evaluate and reuse existing capabilities, establish the
minimum missing means, execute and verify consequences, learn through an
observed carrier, evolve through bounded experiments, and roll back, release
or retire its own replaceable mechanisms.
_Source_: `product/constitution.json#/purpose`,
`product/reshaping-guidance.json#/selfBootstrappingCore`
_Avoid_: unrestricted autonomy, self-authorizing modification, plugin activation, self-evolution alone

**Self-evolution**:
One bounded feedback operator that proposes and evaluates changes to routing,
policy, prompts, representations or replaceable mechanisms against the full
outcome, authority, evidence, burden, recovery and lifecycle vector.
_Source_: `product/reshaping-guidance.json#/selfBootstrappingCore/selfEvolutionRole`
_Avoid_: complete self-bootstrapping, one-metric optimization, permanent improvement

**Product-form neutrality**:
Plugin, Skill, Hook, protocol, library, runtime, service, client integration,
cloud carrier, an open-ended composition or no added artifact is selected from
required closure properties and total lifecycle cost rather than product
identity. One form may close a bounded outcome and several replaceable forms
may cooperate; shared outcome, authority, evidence and lifecycle contracts
provide coherence.
_Source_: `product/constitution.json#/productBoundary/hostRule`,
`product/reshaping-guidance.json#/selfBootstrappingCore/productFormRule`
_Avoid_: plugin-first, runtime-first, fixed form catalogue, mechanism
prohibition, flexibility without verification

**Responsibility-to-form allocation**:
A freshness- and context-bound derived relation assigning each currently
relevant outcome responsibility to no added artifact, one sufficient form or
several cooperating replaceable forms under a shared coherence contract.
_Source_: `product/reshaping-guidance.json#/selfBootstrappingCore/productFormRule`,
`product/reshaping-guidance.json#/dynamicIndex/graphProjection`
_Avoid_: permanent architecture, form identity, unverified composition

**Deep module**:
A cohesive responsibility-bearing unit whose narrow interface hides substantial
policy, state, evidence and lifecycle detail. A native or external capability
may fill a module role through an adapter without becoming Accord-owned code.
_Source_: `product/reshaping-guidance.json#/selfBootstrappingCore/productFormRule`,
`product/reshaping-guidance.json#/selfBootstrappingCore/referenceCore`
_Avoid_: one file per module, public internals, ownership by participation

**Interface and adapter seam**:
The smallest stable contract exposed by a module, plus an evidenced variation
point where two or more host-specific adapters supply that contract. Internal
graphs, matrices, caches and evaluators remain behind the interface.
_Source_: `product/reshaping-guidance.json#/selfBootstrappingCore/productFormRule`
_Avoid_: abstraction without two adapters, host leakage into the portable core

**Coherence contract**:
The shared responsibility, interface, authority, state, evidence, version,
failure, recovery and retirement boundary for cooperating product forms.
_Source_: `product/reshaping-guidance.json#/selfBootstrappingCore/semanticModel/formAllocation`
_Avoid_: co-installation, shared vendor, implicit integration, centralized runtime

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

**Outcome obligation**:
A result condition with an owner, completion criterion, consequence and
residual-risk boundary that must be closed, retired or honestly left open.
_Source_: `product/reshaping-guidance.json#/selfBootstrappingCore/semanticModel/entities (id: outcome-obligation)`
_Avoid_: task step, feature request, capability gap

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

**Composed environment**:
The exact host, model route, tools, extensions, configuration, permissions,
state and Accord exposure under which an observation was made. A current
Accord-enabled host is not an official-clean or no-Accord baseline.
_Source_: `product/constitution.json#/productBoundary/hostRule`,
`product/reshaping-guidance.json#/selfBootstrappingCore/environmentRule`
_Avoid_: host label alone, installed-equals-active, self-validating baseline

**Environment admission**:
A bounded judgment that one provenance-bound environment observation may
support one named claim within its freshness and uncertainty limits.
_Source_: `product/reshaping-guidance.json#/selfBootstrappingCore/environmentAdmissionContract`
_Avoid_: global cleanliness certificate, host approval, installation check

**Comparison arm**:
One provenance-bound environment composition used to answer a named
counterfactual; it supports causal attribution only when material dimensions
are matched or explicitly bounded and the evaluator is independent.
_Source_: `product/reshaping-guidance.json#/selfBootstrappingCore/environmentAdmissionContract/comparisonContract`
_Avoid_: universal baseline, current host minus narrative, automatically equivalent environment

**Material confounder**:
An observed or unknown composition difference that could change the route,
consequence, evidence independence, burden or claim currently being evaluated.
_Source_: `product/reshaping-guidance.json#/selfBootstrappingCore/environmentAdmissionContract/confounding`
_Avoid_: every installed extension, unexplained failure, permanent contamination label

**Isolation boundary**:
The least costly scoped separation that removes, holds constant, independently
measures or explicitly bounds a material confounder without creating authority.
_Source_: `product/reshaping-guidance.json#/selfBootstrappingCore/environmentAdmissionContract/isolationLadder`
_Avoid_: container equals clean, isolation at any cost, authority substitute

**Feasibility gate**:
The context-bound research boundary admitted before an affected architecture
commitment or implementation when a material unresolved premise could change
the route. It uses primary sources, prior failures, existing wheels and bounded
isolated probes to classify the premise as feasible, conditionally feasible,
currently infeasible or unknown; a sufficiently evidenced route needs no gate.
_Source_: `product/reshaping-guidance.json#/selfBootstrappingCore/feasibilityGate`
_Avoid_: universal project-opening search, conceptual attractiveness,
implementation-first research, hidden unknown

**Evidence-acquisition responsibility**:
A context- and freshness-bound duty to obtain only the decision evidence whose
absence, expiry or conflict could change the current route; it is omitted when
existing admitted evidence is sufficient and is allocated like any capability.
_Source_: `product/constitution.json#/kernel (id: K2)`,
`product/reshaping-guidance.json#/selfBootstrappingCore/feasibilityGate`
_Avoid_: mandatory research phase, permanent search subsystem, public lead as authority

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

**Observation facet**:
One independent tri-state fact about declaration, installation, enablement,
activation, execution, consequence, evidence or cleanup post-state.
_Source_: `product/reshaping-guidance.json#/selfBootstrappingCore/semanticModel/factModel`
_Avoid_: linear activation state, inferred causal chain, automatic backfill

**Representative case**:
One bounded outcome episode selected to exercise named product obligations and
failure modes under an exact evaluation contract.
_Source_: `evals/golden-tasks.json#/suiteDesign/caseTypes`
_Avoid_: convenient demo, passing example, population sample

**Longitudinal sequence**:
An ordered bounded evaluation containing baseline, rejected regression,
accepted net improvement and later invalidation through an observed state
carrier.
_Source_: `evals/golden-tasks.json#/suiteDesign/longitudinalSequence`
_Avoid_: repeated identical run, hidden memory, unbounded self-improvement

**Full acceptance vector**:
The non-compensating disposition of outcome, authority, evidence, privacy,
burden, interference, recovery, resources, continuity and lifecycle for one
evaluation case.
_Source_: `evals/golden-tasks.json#/suiteDesign/fullAcceptanceVector`
_Avoid_: universal score, averaged hard failure, proxy objective

**Resource**:
An observable unit of context, execution, connection, storage or host capacity
whose identity, ownership, lease and state determine whether it may be admitted,
rebalanced, released or preserved.
_Source_: `product/constitution.json#/domainModel/crossCuttingObjects (value: resource)`,
`product/constitution.json#/resourceStewardship`
_Avoid_: process count alone, task completion, automatically disposable state

**Continuity**:
Preservation and reconciliation of the current goal and state across phases,
carriers and actors.
_Source_: `product/constitution.json#/domainModel/crossCuttingObjects (value: continuity)`,
`product/constitution.json#/learnedFailureStandards (id: L6)`
_Avoid_: copied history mistaken for load relief, implicit handoff

**Causal fork**:
A copied-history branch used for divergent causal work. It is not sequential
handoff or a remedy for accumulated inherited context.
_Source_: `product/constitution.json#/learnedFailureStandards (id: L6)`
_Avoid_: context relief, source replacement, implicit state reconciliation

**Sequential handoff**:
A transition to a fresh zero-inherited-history carrier that transfers only the
minimum verified state, verifies destination goal, checkout and current state,
then releases the source.
_Source_: `product/constitution.json#/learnedFailureStandards (id: L6)`
_Avoid_: fork, copy-only continuation, release before destination verification

**Process-loss control**:
End-to-end reconciliation of the latest demand, accountable consensus and
corrections with authority, plan, process, acceptance, goal projection, route,
implementation, evidence, documentation and final claim. It
applies even when the current carrier is healthy; continuity transition is only
one possible response to an observed divergence.
_Source_: `product/program.json#/processLossControl/alignmentRule`,
`product/constitution.json#/humanAuthority/agentOwnsWithinBoundedAuthority (value: proactive-continuity-and-process-loss-control)`
_Avoid_: forced handoff, fixed workflow, plan compliance without outcome alignment

**Versioned baseline**:
A revision-bound statement of prior consensus and evidence. A globally
material later consensus may supersede affected authority and candidate status
from the earliest dependency while the old baseline remains immutable history.
_Source_: `product/constitution.json#/evolutionPolicy/feedbackRule`,
`product/reshaping-guidance.json#/selfBootstrappingCore/consensusRule`
_Avoid_: permanent truth, rewritten history, simultaneous stale ready state

**Code topology**:
The repository, checkout, branch, worktree, repository-fork, synchronization,
merge and cleanup relations that locate code and mutations.
_Source_: `product/reshaping-guidance.json#/topology/code`,
`product/constitution.json#/hostAdapterStandard (id: H8)`
_Avoid_: conversation fork, implicit handoff, code change inferred from task change

**Conversation topology**:
The current task, compaction, causal fork, fresh sequential handoff, conclusion
reconciliation, source release and archive relations that locate conversational
work and state. It changes independently of code topology.
_Source_: `product/reshaping-guidance.json#/topology/conversation`,
`product/constitution.json#/hostAdapterStandard (id: H8)`
_Avoid_: branch or worktree, repository fork, code move inferred from handoff

**Execution topology**:
The local or cloud environment, worker, process, terminal, connection and
placement relations used to execute work. It may bind to code or conversation
state for one outcome but changes neither topology by itself.
_Source_: `product/reshaping-guidance.json#/topology/execution`,
`product/constitution.json#/hostAdapterStandard (id: H8)`
_Avoid_: code branch, conversation fork, cloud placement as repository mutation

**Lifecycle**:
The path from observed gap through admission, operation, evaluation,
replacement and retirement.
_Source_: `product/constitution.json#/domainModel/crossCuttingObjects (value: lifecycle)`,
`product/constitution.json#/evolutionPolicy`
_Avoid_: permanent installation

**Responsibility-scoped retirement**:
The composition-bound end of one Accord responsibility allocation after an
admitted successor closes the same obligation and the transition remains
reversible, observed and recheckable. It does not imply whole-product retirement.
_Source_: `product/constitution.json#/evolutionPolicy/retirementRule`,
`product/reshaping-guidance.json#/selfBootstrappingCore/semanticModel`
_Avoid_: host-version cutoff, declaration-driven removal, global uninstall,
permanent retirement across environment drift

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

**Collaboration-closure need**:
An unclosed outcome obligation, unreliable relation, or coordination and
verification risk that still needs a feasible authorized path. A capability
gap is one local diagnostic view of this need, not the product definition or a
set-subtraction formula.
_Source_: `product/constitution.json#/kernel (id: K2)`,
`product/reshaping-guidance.json#/boundedAutonomy/closureModel`
_Avoid_: any inconvenience, missing feature, capability-set difference

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

**Sparse capability-surface views**:
Derived H (host-native responsibility incidence) and A (Accord responsibility
allocation) views, filtered by current admission and closure-lifecycle masks.
Their overlap opens redundancy evaluation but never proves retirement.
_Source_: `product/reshaping-guidance.json#/dynamicIndex/sparseMatrixViews`
_Avoid_: Cartesian capability catalog, binary-overlap retirement, second authority

**Capability provenance**:
The observed origin of a capability: model-inherent, host-native,
client-surface, tool or extension, configuration or policy, composition, or a
bounded authored mechanism. Origin informs discovery and retirement but does not
prove effective availability.
_Source_: `product/reshaping-guidance.json#/capabilityDiscovery/provenanceKinds`
_Avoid_: capability owner, vendor truth, product boundary

**Effective capability instance**:
One observation of a stable capability meaning under an exact Agent/host,
carrier, model route, tool set, configuration, permission, context and time.
Fitness and health belong to this combination and expire on material drift.
_Source_: `product/reshaping-guidance.json#/capabilityDiscovery/effectiveCapabilityIdentity`
_Avoid_: universal model ability, permanent host feature, duplicate semantic capability

**Graph projection**:
A derived node-and-edge view used to find feasible routes, affected evidence
and retirement dependencies, including responsibility-to-form allocations and
their coherence, replacement and lifecycle relations; it does not imply a
graph database.
_Source_: `product/reshaping-guidance.json#/dynamicIndex/graphProjection`
_Avoid_: second source of truth, mandatory database

**Closure**:
A state transition supported by consequence-level evidence, reconciled effects
and explicit residual limits.
_Source_: `product/constitution.json#/kernel (id: K5)`,
`product/constitution.json#/qualityInvariants (value: completion is supported by external criteria and observed effects rather than model self-assessment or artifact shape)`
_Avoid_: summary, commit, test pass
