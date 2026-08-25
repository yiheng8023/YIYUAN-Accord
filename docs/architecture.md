# Architecture

YIYUAN Accord has one small semantic core and replaceable projections.

~~~text
latest bound user goal and corrections
                |
                v
 immutable contract line + active distribution program
                |
                v
      generic contract verifier
          /             \
         v               v
  Codex thin Skill   Claude thin Skill
         \               /
          v             v
     representative Golden Tasks
                |
                v
 exact local verification + independent review
                |
                v
 push same SHA -> exact-HEAD hosted evidence -> named-human authority
                |
                v
 exact tagged release -> live public check + goal-carrier cleanup
~~~

The arrows mean dependency, not automatic authority promotion. Reports and
observations do not become authority merely by being present, but they can
challenge the current set and trigger a reviewed merge, split, replacement or
retirement. Such a topology change requires an explicit schema and verifier
migration, preserved provenance and replay from the earliest affected boundary.

The collaboration layer is the product's controllable seam. It does not try to
make an Agent imitate a person, replace a model provider, or remove human
limitations. People, models and their shared information are finite, so a
machine-native route is valid when it delivers the human outcome with lower net
burden, preserves authority and leaves honest evidence.

## Portable interface

K1–K5 are the product interface:

- goal and phase;
- minimum sufficient route and no-op;
- human and Agent authority;
- continuous reconciliation;
- consequence-level closure, recovery and cleanup.

H1–H10 constrain how a host projection admits current official guidance,
native capability, effective observation, unknown state, drift, verification,
user burden, host-specific detail and retirement. L1–L7 are regression
standards distilled from the project's two-month trial history.

In schema v2 these identifiers and their full current statements live in
product/constitution.json. Derived prose may explain them but cannot silently
redefine them. This is a current source location, not an eternal ontology or
permanent authority-file count.

## One deep verification seam

`python -B -m yiyuan_accord verify` is the one public verification seam.
`yiyuan_accord/control.py` coordinates product-data evaluation;
`yiyuan_accord/identity.py`, `yiyuan_accord/evidence.py` and
`yiyuan_accord/guardrails.py` contain focused identity, observation,
repository and projection-package checks.
Together they validate:

- the current schema-v2 authority set and its cross-file mappings;
- at most one active increment and one active work item, with the completed
  increment and work item retained when a clean candidate enters task-time gates;
- goal-mode prompt coverage;
- evidence-lane separation and criterion-specific acceptance;
- separation of the immutable behavior-contract line from the current
  distribution version, maturity, publisher, assets and package identity;
- a dependency-ordered release procedure, exact local verification and
  independent review before push, channel-specific required hosted verification
  bound to the same candidate, a separate later human authorization, and five
  completion gates that the active goal carrier, not repository evidence, must
  observe; optional unavailable hosted systems remain explicit unknowns;
- Golden Task coverage and its refusal to self-certify behavior;
- complete projection identities, complete thin projection package surfaces,
  repository-scoped absence paths and non-expansive marketplace policy;
- the explicit complexity budget and retired proof-generation paths.

The strict static retired-identity boundary is deliberately lexical, not a
multi-host command interpreter. The Git index is the declaration source: every
stage-zero `100644` or `100755` locator remains in scope even when its worktree
file is missing, while an unavailable index, unmerged entry, symlink, gitlink
or other non-regular mode blocks conformance. Ignored and untracked files are
outside this identity claim; the separate clean-checkout gate rejects dirty or
untracked state and hidden `skip-worktree` or `assume-unchanged` flags.

All repository reads share one bounded regular-file path with pre-open and
post-open type and size checks. Paths and strictly decoded non-Python whole text
reject exact NFKC/casefold superseded name, slug and module tokens at their
declared lexical boundaries; backslash escapes have no host-agnostic meaning.
Declared `.py`, `.pyi` and `.pyw` files are parsed under the shared Python 3.10
AST grammar on supported Python 3.10-3.14 hosts, then scan identifiers, literal
values and bounded maximum static-concatenation subtrees while ignoring
comments and not joining across runtime expressions. Syntax outside that shared
grammar and any unreadable, undecodable, oversized or over-budget surface are
indeterminate and fail closed. Only digest-bound Markdown research inputs under
`research/reviews/` and exact program-declared SHA-256-bound PNG distribution
assets are inert exceptions. A PNG declaration must name a tracked `.png`,
match its signature and bind its complete bytes; undeclared or changed binary
content still fails closed. This proves
static absence on that finite declared surface, not absence from Python
comments, ignored or untracked files, runtime-built or external dynamic
content. The workflow profile remains a separate exact structural constraint.

The verifier does not contain copies of the product's purpose, criterion
statements or pass rules. It validates the contract supplied by the current
reviewable authority set. The schema-v2 bootstrap currently consists of
constitution, program and acceptance; changing that topology requires a
versioned migration rather than treating three as a permanent constant. A valid
report means only that the authority and projections are
structurally conformant at their current declared lifecycle state. It is not
evidence that the tree is a candidate. Candidate readiness additionally
requires all applicable live-computed and representative criteria, a ready
program, one retained completed increment and a clean checkout. Exact local
review, hosted results, human authority, publication and cleanup are task-time
facts; the verifier accepts no caller-supplied receipt and never computes
release eligibility or completion.

## Host admission

Each projection consists of one host-native manifest, one small YIYUAN Accord
adapter contract and one progressively disclosed Skill, plus only the
host-native metadata or presentation assets declared by that manifest. The
native manifest contains only fields supported by that host; `adapter.json`
carries the machine-readable K, H and L mapping used by the generic host check.
There is no YIYUAN Accord runtime, Hook, state store, MCP, App, private capture
protocol or fixed host-version dependency.

The two packages are semantic siblings, not byte-identical copies. Their K/H/L
mapping and lifecycle boundary must agree; host-required names, manifests and
metadata may differ. Separately governed user-level Skills are outside the
release package and stay unprojected by default. Their installation or
visibility is neither a dependency nor evidence for these reference
projections.

Presentation remains host-specific. The Codex package may bind a declared
trademark image as a deterministic package asset, while a host manifest without
an equivalent visual field remains valid without one. Publisher, version,
homepage, icon and complete package bytes belong to distribution identity; they
do not rewrite the portable K/H/L behavior contract.

The host-check command is deliberately two-level:

1. static readiness checks that the exact projection maps the current K, H and
   L interface and adds no forbidden surface;
2. behavior evidence remains unverified until Golden Tasks run on the exact
   host and independent observations exist.

Declared, installed or visible capability is not automatically effective
capability. Current official host guidance is high-weight task-time evidence,
not permanent core authority. Host drift causes revalidation, and native
improvement may retire projection logic.

The host capability view is event-triggered and versioned, not an always-on
catalog: refresh it before release or after a material host, maturity,
permission, extension, cloud-route or deprecation change. Each review binds an
official source/date and exact host version to availability, maturity,
trust/persistence/effect surface, native equivalence, residual gap, a live probe
and a retirement trigger. Codex and Claude Code are current behavior-reference
adapters and test hosts; neither defines the portable contract or future host
scope. Claude web chat, the Claude Desktop Chat tab and Cowork are distribution
surfaces for the same Claude package, not inherited behavior evidence.

## Evaluation

evals/golden-tasks.json contains representative help, no-op, authority,
correction, proof-proxy, continuity, capability, report-handling and cleanup
cases. A task declares required and prohibited behaviors before execution.
Observations record Agent actions, human actions, effects, residue and claim
limits independently of the model's own verdict. Each release observation
binds the exact Golden Task digest, the evaluation protocol and burden metric
digest, the behavior-bearing adapter contract and exposed Skill, a typed
host/session identity and a
complete controlled transcript or host-event record held in a separate source
bundle. Independence is established by the source record and direct task-time
observation, not by a boolean written into the observation.
An assertion collected after the primary host session must carry structured
`sourceBindings` to the exact completed observer-session output, locator,
completion time and bounded
claim. That binding makes the later assertion independently locatable; it does
not convert a task-time failure into a pass or make repository data authentic.
The Golden Task declares every required post-session event, location and exact
count of distinct observer-session locators. The acceptance release-sample
policy independently anchors that exact contract, and locator uniqueness
applies across the complete contract. The
publishable payload mirrors that contract, and its observation source entry
hashes the complete selected event set. Omitting the contract, an event, a
binding or that digest therefore fails closed instead of silently narrowing
the claimed source.

Before the exact local release gate passes, an independent human or second
observation surface compares the publishable bundle with the original host or
session records. The raw records remain outside the public repository. One
evaluator isolated from candidate-preparation context also exercises the README
activation, confirmation and removal path from a clean state. The accountable
user, a colleague or a second observation surface may execute this
context-isolated, outcome-bound, identity-neutral internal usability sample; it
is not population-level field evidence.

The repository verifier recomputes these digests and rejects stale or partial
bindings. It does not authenticate a real-world observer or prove that a host
event happened; that would turn this project into the identity/audit system it
explicitly excludes. The active goal carrier must directly observe collection,
and release evidence must come from disposable controlled tasks whose complete
record is safe to publish. Private memory, account state and unsanitized host
transcripts are not release evidence.

A distribution-only change does not manufacture new behavior or invalidate an
unchanged behavior observation. It must still replay deterministic validation
of the complete manifest, marketplace, metadata, asset and package surface, and
it must obtain current clean-state activation, confirmation and removal
evidence. A contract or Skill locator/content change invalidates the dependent
behavior observation from that earliest boundary.

Task outcome and evaluator conformance are separate decisions. A prohibited
behavior keeps the exact task failed and blocks that host or projection claim.
YIYUAN Accord is conformant only if it preserves the failure, rejects stale
projection evidence, records residue and recovery, and excludes the failed
behavior from the release claim. Those exclusions are aggregated into the
public claim ceiling and release body rather than remaining private to an
observation. This prevents both proof-by-receipt and the
opposite category error of requiring every evaluated host behavior to pass
before the evaluation contract itself can ship.

The required finite-release lanes are deterministic conformance and bounded
representative behavior. Field effect and cross-host or longitudinal evidence
continue after release unless the release explicitly claims them.

## Complexity and evolution

The program binds the pre-reshape baseline at revision
534a77aae9e1d191173e6e05b4327c80d22855d8 and numeric reduction targets. Total
cost includes code, instructions, evidence, state, topology, human cognition,
recovery and retirement—not line count alone.

A repeated same-purpose failure triggers replan and a premise, interface and
representation review. Deletion, replacement, recomposition, native delegation
and bounded addition are all considered; there is no universal add-or-subtract
default. L2 retains one evidence-derived ordering constraint: try deletion or
replacement before admitting another same-purpose repair layer. A new or
retained mechanism requires an observed residual gap, insufficient native or
maintained coverage, benefit greater than total lifecycle cost, proportionate
verification, and a retirement trigger. Thinness constrains implementation
weight and permanent exposure; it is not a feature-deletion KPI. Finite release
closes a bounded product version, while later evidence can simplify, narrow,
retire or open one new causal increment.
