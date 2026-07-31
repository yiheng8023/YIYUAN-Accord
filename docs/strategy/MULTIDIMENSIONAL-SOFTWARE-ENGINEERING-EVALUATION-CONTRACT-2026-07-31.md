# Multidimensional Software-Engineering Evaluation Contract

## Status and purpose

This is a carrier-neutral research and evaluation contract. It defines how the
Harness can describe software-engineering quality without reducing the result
to code quality, delivery speed, one maturity model, one Agent, or one scalar
score.

It does not create or admit a hard standard, create a Skill or Hook, prescribe
one lifecycle, authorize a model run, or claim that the repository already has
complete software-lifecycle evidence. The existing AI-era classical-principle
revalidation remains a horizontal lens; this contract supplies the broader
evaluation structure around it.

## Separation of carriers

The evaluation system has five distinct layers:

1. **evaluation ontology and contract** — dimensions, context, evidence,
   uncertainty, output shape, and anti-gaming rules;
2. **candidate hard floors** — independently testable obligations that may
   block a bounded evaluation when applicable, but remain non-authoritative
   until separate admission;
3. **deterministic validators** — tests, static checks, provenance checks,
   policy checks, and observed receipts;
4. **risk, stage, and domain profiles** — proportional evidence expectations
   derived from lifecycle stage, criticality, exposure, reversibility, data
   sensitivity, and AI involvement;
5. **optional orchestration** — an Agent or later Skill may select a profile,
   collect evidence, invoke existing validators, and explain results, but it
   cannot own truth, waive a floor, invent evidence, or mark acceptance.

The evaluation contract must remain usable when no Agent, Skill, Hook, Plugin,
App, or MCP is present. A future Skill is justified only after repeated tasks
show a residual orchestration gap that native, official, reviewed external,
and composed paths do not cover.

## Evaluation dimensions

Every evaluation declares which dimensions are applicable, not applicable, or
still unassessed:

1. goal value and requirement fitness;
2. intent and acceptance fidelity;
3. architecture and design integrity;
4. implementation and code quality;
5. verification, security, privacy, and safety;
6. supply chain and provenance;
7. delivery, change, and rollback;
8. reliability, operability, and observability;
9. maintainability, evolution, and retirement;
10. collaboration, knowledge, and accountability;
11. AI process loss and human control;
12. efficiency, resource stewardship, and sustainability.

These dimensions are not weights in a universal formula. A dimension may be
strong while another remains blocked. A good delivery score cannot cancel a
critical authority breach, fabricated evidence, an unresolved applicable
security floor, or an unsupported readiness claim.

## Evidence and uncertainty

Evidence strength is recorded separately from the dimension assessment:

- `claim-only`;
- `source-bound`;
- `deterministic`;
- `observed-live`;
- `repeated-comparative`;
- `longitudinal-or-cross-context`.

The evidence grade never broadens its own scope. A deterministic unit test is
not live operational evidence; one live observation is not a repeated causal
comparison; cross-host evidence is not automatically cross-domain evidence.
Each conclusion also records confidence, limitations, unknowns, freshness,
target identity, evaluator independence, and the exact context in which the
evidence applies.

Allowed dimension assessments are `not-applicable`, `unassessed`,
`insufficient-evidence`, `blocked`, `concerning`, `adequate`, and `strong`.
Unknown or unassessed is not zero, and absence of a detected defect is not a
positive score.

## Candidate hard-floor boundary

The first candidate floor hypotheses cover:

- evidence truth and provenance;
- authority and data boundaries;
- unresolved critical security, privacy, safety, or compliance risk;
- rollback, recovery, and accountable ownership for consequential change;
- third-party dependency and release provenance;
- completion, acceptance, and readiness claim integrity.

Each floor must declare applicability, owner, proof surface, counterexample,
fallback, and retirement condition. The repository may test these hypotheses,
but cannot promote them into project hard standards. Admission still requires
AI-independent meaning and proof, repeated evidence, a governed calibration
handoff, and the final standard authority's decision.

## Adaptive profiles

Profiles are derived rather than treated as one permanent checklist. The
minimum profile axes are:

- lifecycle stage: exploration, design, implementation, pre-merge,
  pre-release, operation, incident, migration, deprecation, or retirement;
- criticality: low, medium, high, or critical;
- exposure: local, internal, partner, public, or regulated;
- reversibility: easy, bounded, costly, or irreversible;
- data sensitivity: public, internal, confidential, restricted, or unknown;
- AI involvement: none, advisory, generative, agentic, or opaque.

A profile may raise evidence requirements or make a candidate floor
applicable. It may not lower an already applicable authority, truth, safety,
or acceptance boundary. Domain overlays remain separate and can be added only
when their source, owner, scope, and verification surface are bound.

## Source synthesis

No source below is the whole evaluation system:

- [ISO/IEC/IEEE 12207:2026](https://www.iso.org/standard/90219.html) provides a
  full lifecycle process framework without requiring one lifecycle method.
- [ISO/IEC 25010:2023](https://www.iso.org/standard/78176.html) supplies a
  nine-characteristic product-quality model.
- [ISO/IEC 25019:2023](https://www.iso.org/standard/78177.html) requires
  quality-in-use to be evaluated in a specified context of use.
- [ISO/IEC 25040:2024](https://www.iso.org/standard/83467.html) supplies a
  quality-evaluation framework but no universal test method.
- [NIST SSDF 1.1](https://csrc.nist.gov/pubs/sp/800/218/final) supplies
  outcome-oriented secure-development practices; the later 1.2 work remains
  draft at this checkpoint.
- [OWASP SAMM](https://owaspsamm.org/about/) supplies a risk-driven,
  adaptable security-maturity model and explicitly rejects maximum maturity
  as a universal target.
- [SLSA 1.2](https://slsa.dev/spec/v1.2/) supplies approved source/build
  provenance and supply-chain assurance tracks.
- [DORA delivery metrics](https://dora.dev/guides/dora-metrics/) cover
  throughput and instability in application context and warn against one
  metric, metric targets, and disparate comparisons.
- [SPACE](https://www.microsoft.com/en-us/research/publication/the-space-of-developer-productivity-theres-more-to-it-than-you-think/)
  treats developer productivity as multidimensional rather than individual
  activity or one metric.
- [NIST AI RMF 1.0](https://www.nist.gov/publications/artificial-intelligence-risk-management-framework-ai-rmf-10)
  supplies lifecycle risk, human-role, oversight, and third-party-component
  concepts. It is under revision and remains a bounded input rather than a
  permanent frozen authority.

The mapping is intentionally compositional: lifecycle coverage, product
quality, quality in use, evaluation process, security, supply-chain evidence,
delivery performance, developer experience, and AI governance are different
objects.

## Output contract and anti-gaming

An evaluation report must bind:

- target identity and version;
- evaluation context and selected profile axes;
- applicable dimensions and candidate floors;
- evidence items with source, freshness, scope, grade, and independence;
- per-dimension assessment, confidence, unknowns, and limitations;
- blocking floor results kept separate from dimension results;
- disagreements, counterevidence, and human/domain decisions;
- recommended next evidence, fallback, revalidation, and retirement triggers;
- an explicit claim boundary.

One scalar total score is prohibited. A presentation may summarize the profile,
but it must preserve every blocked floor, unassessed dimension, evidence grade,
and material uncertainty. Metric targets may not become acceptance criteria
without context, ownership, anti-gaming review, and separate authority.

## Existing capability boundary

Current native reasoning, repository validators, official security tooling,
and reviewed workflow Skills cover useful subproblems. Their presence does not
prove a complete evaluation system, and this contract does not credit their
behavior without task-bound evidence. A deterministic report schema and
positive fixture now prove the output shape, exact dimension/floor coverage,
evidence references, unknown preservation, independent review, acceptance
authority, and accepted-status guards without a model. The first bounded
application evaluates the immutable `bb65a26` eight-file contract package and
remains a same-system self-assessment with status `needs-verification`; it does
not establish independent validity, real-domain usefulness, cross-host value,
efficiency, or standard eligibility. The next implementation priority is a
non-self-referential bounded software change with independent review, not a
project-wide rating or a new evaluation Skill.

## Acceptance and authority boundary

This contract reuses the existing acceptance carriers:

- `acceptance.software-engineering-lifecycle-specialization`;
- `acceptance.end-to-end-process-fidelity`;
- `acceptance.ai-independent-hard-standard-boundary`;
- `acceptance.standard-candidate-contract`;
- `acceptance.adaptive-harness-proportionality`.

All remain at their independently evidenced status. The acceptance inventory
remains 61. This checkpoint authorizes no hard-standard promotion, Skill or
Hook creation, CC Switch change, external capability installation, model
dispatch, cross-repository write, CALIBRATION or ASSETS admission, commit,
push, release, or deployment.
