# Human-AI Collaboration Unknown-Quadrant Parent-Oracle Seam Reuse Decision

Date: 2026-07-27
Status: existing parent-only seams sufficient; no new adapter justified

## Decision

The unknown-quadrant overlays do not need a new generic renderer or oracle
adapter in the current zero-model phase. Three byte-bound repository builders
already implement the required separation:

- the weak-Agent trial builder accepts a protocol-owned
  `privateOraclePayload`, writes only its canonical hash and
  `contentWrittenIntoTrial=false` into the parent manifest, and writes the
  public task to `TASK.json`;
- the process-fidelity packet builder keeps `agentVisibleProjection` and
  `privateOracle` distinct and rejects private-content injection;
- the context-continuation builder omits `oraclePrivate` from its default public
  output and exposes it only through a separate explicit parent mode.

Existing regression tests cover the relevant no-write, no-injection, and
default-public-output boundaries.

## Why no generic override

A global arbitrary runtime oracle override would increase leakage, schema, and
authority surface before any exact live scenario is authorized. It would also
weaken ownership: the private score contract belongs to the selected protocol,
not to a universal mutable runtime option.

For now, the four-class overlays remain evaluator-time parent inputs. When one
exact live scenario and arm is authorized, the selected protocol may add one
owned `privateOraclePayload` mapping plus a leakage regression using the
existing builder pattern.

## Boundary

No builder or historical test was changed by this decision. No model was
called, no Skill was invoked, and no CC Switch, global configuration, Git, or
external state was mutated.

This record does not prove live integration, make oracle leakage impossible,
prove candidate value, establish a residual adapter gap, or justify a new
Skill or adapter.
