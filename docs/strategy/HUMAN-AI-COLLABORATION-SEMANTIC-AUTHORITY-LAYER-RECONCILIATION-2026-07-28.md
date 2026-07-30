# Human-AI Collaboration Semantic Authority Layer Reconciliation

Date: 2026-07-28
Status: read-only source reconciliation and cross-lifecycle design calibration
Machine record:
[`../../registry/human-ai-collaboration-semantic-authority-layer-reconciliation-2026-07-28.json`](../../registry/human-ai-collaboration-semantic-authority-layer-reconciliation-2026-07-28.json)

## Judgment

Matt Pocock's core argument is accepted: a grilling conversation that does not
persist settled terminology and consequential decisions loses alignment at the
next session or lifecycle hop. A durable ubiquitous language and sparse
decision records reduce repeated explanation and make semantic drift
observable.

This is more important than one Skill. The durable result is a cross-lifecycle
semantic authority plane, not a universal requirement to run a long interview
for every code change. Clear, low-risk, terminology-stable work may consume the
existing glossary directly or use native reasoning.

## Current upstream architecture

At exact upstream head
[`ed37663`](https://github.com/mattpocock/skills/commit/ed37663cc5fbef691ddfecd080dff42f7e7e350d),
[`grill-with-docs`](https://github.com/mattpocock/skills/blob/ed37663cc5fbef691ddfecd080dff42f7e7e350d/skills/engineering/grill-with-docs/SKILL.md)
is a 245-byte user-invoked composition entry. It runs the reusable
[`grilling`](https://github.com/mattpocock/skills/blob/ed37663cc5fbef691ddfecd080dff42f7e7e350d/skills/productivity/grilling/SKILL.md)
human-decision elicitation primitive with the
[`domain-modeling`](https://github.com/mattpocock/skills/blob/ed37663cc5fbef691ddfecd080dff42f7e7e350d/skills/engineering/domain-modeling/SKILL.md)
semantic-maintenance primitive. `grill-me` is the grilling-only entry.

That split is the maintainable architecture for the Harness:

- `grilling` asks one human decision at a time, recommends an answer, looks up
  discoverable facts, and does not act before shared understanding is
  confirmed;
- `domain-modeling` challenges terminology, tests concrete scenarios,
  cross-checks code, updates a glossary, and offers ADRs only for hard-to-reverse,
  surprising, real trade-offs;
- `grill-with-docs` composes the two when both elicitation and durable semantic
  state are needed.

## Current local boundary

The CC Switch copies are not the current upstream composition. The local
`grill-with-docs` is the exact 5,340-byte repository-adapted historical
monolith already bound by the requirements-domain protocol. Its database row
is local and carries no upstream repository/revision ownership. Neither
`grilling` nor `domain-modeling` is installed as a separate CC body.

Therefore a silent update to the current 245-byte wrapper would create an
incomplete dependency set and would also change the exact treatment under
test. The existing protocol remains bound to the current adapted SHA-256. No
CC update, primitive installation, wrapper replacement, or portfolio mutation
is performed by this reconciliation.

## Cross-lifecycle contract

The portable contract does not mandate the literal filename `CONTEXT.md`.
Projects may use `CONTEXT.md`, a bounded-context glossary, or an equivalent
authoritative carrier. The invariants are:

1. the glossary contains canonical domain language, not implementation plans;
2. unresolved terms, working notes, generated projections, and handoffs do not
   become authority automatically;
3. authoritative terminology and hard-to-reverse decisions change only after
   the responsible human accepts them;
4. ADRs remain sparse and record context, decision, alternatives,
   consequences, status, supersession, and evidence only when warranted;
5. requirements, architecture, implementation/TDD, independent review,
   release/rollback, operations/maintenance, handoff, and closure consume the
   same accepted semantic state and report conflicts or deltas;
6. hard standards remain independent mandatory gates and cannot be replaced by
   shared vocabulary or an ADR.

## Acceptance and next gate

The program remains partial until one source-backed lifecycle trial proves
that accepted terms and decisions survive stage transitions, conflicts are
surfaced rather than silently normalized, superseded decisions are traceable,
and unresolved material is not promoted. The first comparison should hold the
scenario and hard standards fixed while comparing the exact current upstream
three-piece composition with the existing adapted monolith or native
composition.

This record proves source structure and a bounded design correction only. It
does not prove invocation, token savings, behavioral value, superiority,
cross-Agent adherence, full lifecycle continuity, or a residual need for a
self-authored Skill.
