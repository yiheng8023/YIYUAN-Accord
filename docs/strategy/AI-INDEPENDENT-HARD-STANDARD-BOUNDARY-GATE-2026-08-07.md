# AI-Independent Hard-Standard Boundary Gate

## Status and purpose

This checkpoint verifies a deterministic admission-boundary mechanism for any
future hard-standard candidate. It does not create, select, admit, or promote a
real hard standard.

The public seam accepts a machine-readable candidate record and returns a
fail-closed decision without running a model, Agent, Skill, Hook, Plugin, App,
MCP server, external service, or candidate payload. A candidate is boundary
eligible only when its obligation, accountable owner, execution surface, and
proof surface remain meaningful after AI, models, Skills, Hooks, and Agent
behavior are removed. Each of those surfaces and the counterfactual must bind
non-empty evidence identifiers. Separate governed admission remains mandatory,
and the evaluator never grants it.

## Failure-injection coverage

Twenty single-field mutations cover:

- candidate class;
- obligation statement, AI independence, Skill independence, and evidence;
- accountable owner type, non-AI status, and evidence;
- execution carrier class and evidence;
- proof carrier class and evidence;
- the exact AI/model/Skill/Hook/Agent-behavior removal set;
- preservation of the obligation and owner;
- surviving execution and proof references;
- counterfactual evidence;
- separate governed admission and the current non-admitted state.

Every mutation returns `blocked`, retains `admissionAuthorized: false`, and
names the expected blocker. A Skill or other soft carrier may assist only when
an evidenced AI-independent execution and proof route survives beside it.

## Claim boundary

The synthetic fixture proves only that the repository-owned evaluator can
distinguish a structurally complete AI-independent boundary record from blocked
records. Evidence identifiers prove only structural binding; this mechanism
does not establish the truth or sufficiency of the referenced evidence. It is
not evidence of a real domain obligation, standard value,
cross-host behavior, adoption, compliance, production readiness, or admission
authority.
