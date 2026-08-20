# Architecture

Agent Autonomy Harness has one small semantic core and replaceable projections.

~~~text
latest bound user goal and corrections
                |
                v
 constitution + program + acceptance
                |
                v
      generic contract verifier
          /             \
         v               v
  Codex thin Skill   Claude thin Skill
         \               /
          v             v
     representative Golden Tasks
~~~

The arrows mean dependency, not authority promotion. Reports and observations
can change a later program decision after review, but they do not become a
fourth authority.

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

These identifiers and their full current statements live only in
product/constitution.json. Derived prose may explain them but cannot redefine
them.

## One deep verification seam

`python -B -m harness verify` is the one public verification seam.
`harness/control.py` evaluates the product data while `harness/guardrails.py`
contains pure repository, projection-package and external-authorization checks.
Together they validate:

- the three authority schemas and their cross-file mappings;
- one active increment and one active work item;
- goal-mode prompt coverage;
- evidence-lane separation, criterion-specific acceptance and an external
  release authorization bound to the exact clean candidate;
- Golden Task coverage and its refusal to self-certify behavior;
- complete projection identities, exact Skill-only package surfaces,
  repository-scoped absence paths and non-expansive marketplace policy;
- the explicit complexity budget and retired proof-generation paths.

The verifier does not contain copies of the product's purpose, criterion
statements or pass rules. It validates the contract supplied by the authority
files. A valid report means the current contract is internally conformant;
release completion is a separate computed state.

## Host admission

Each projection consists of one host-native manifest, one small Harness adapter
contract and one progressively disclosed Skill. The native manifest contains
only fields supported by that host; `adapter.json` carries the machine-readable
K, H and L mapping used by the generic host check. There is no Harness runtime,
Hook, state store, MCP, App, private capture protocol or fixed host-version
dependency.

The host-check command is deliberately two-level:

1. static readiness checks that the exact projection maps the current K, H and
   L interface and adds no forbidden surface;
2. behavior evidence remains unverified until Golden Tasks run on the exact
   host and independent observations exist.

Declared, installed or visible capability is not automatically effective
capability. Current official host guidance is high-weight task-time evidence,
not permanent core authority. Host drift causes revalidation, and native
improvement may retire projection logic.

## Evaluation

evals/golden-tasks.json contains representative help, no-op, authority,
correction, proof-proxy, continuity, capability, report-handling and cleanup
cases. A task declares required and prohibited behaviors before execution.
Observations record Agent actions, human actions, effects, residue and claim
limits independently of the model's own verdict.

Task outcome and evaluator conformance are separate decisions. A prohibited
behavior keeps the exact task failed and blocks that host or projection claim.
The Harness is conformant only if it preserves the failure, rejects stale
projection evidence, records residue and recovery, and excludes the failed
behavior from the release claim. This prevents both proof-by-receipt and the
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

A repeated same-purpose failure triggers replan and a deletion or replacement
attempt. A new mechanism requires an observed residual gap, insufficient native
or maintained coverage, benefit greater than total lifecycle cost,
proportionate verification, and a retirement trigger. Finite release closes a
bounded product version; later evidence can simplify, narrow, retire or open one
new causal increment.
