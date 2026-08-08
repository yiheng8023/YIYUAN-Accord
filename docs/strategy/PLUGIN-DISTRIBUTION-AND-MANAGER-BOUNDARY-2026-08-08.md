# Plugin Distribution And Manager Boundary Decision — 2026-08-08

Machine record:
[`../../registry/plugin-distribution-and-manager-boundary-decision-2026-08-08.json`](../../registry/plugin-distribution-and-manager-boundary-decision-2026-08-08.json)

## Decision

Agent Autonomy Harness remains an independent, Agent-neutral product authority.
It should be compatible with plugin packaging and may later emit generated
plugin consumer projections, but the repository as a whole does not become a
plugin. The current posture is:

```text
plugin-compatible + manager-agnostic + release-not-eligible
```

Plugin packaging and capability lifecycle management are separate concerns.
Agent Plugins 1.0.0 defines a portable packaging floor, while OpenAI and Vercel
also expose host-specific package, installation, enablement, Hook, command, and
runtime behavior. One universal manifest must not be treated as proof of every
host's format or lifecycle semantics.

## Ownership boundary

CC Switch remains the replaceable operational manager for shared third-party
Skills where suitable. A host-native plugin manager owns the installation,
cache, enablement, update, and removal state of that host's plugin projection.
The portable Harness core depends on neither manager implementation.

Every component has one lifecycle authority:

- a CC Switch-managed third-party Skill remains exact-upstream and must not be
  copied into a Harness plugin;
- an official or runtime-owned component remains host-owned;
- a repository-owned component may enter a future plugin only after residual-
  gap proof, admission, rights and security review, and task-value evidence;
- host-specific compatibility, Hooks, commands, and metadata belong in
  generated projections or adapters rather than a rewritten portable core.

The absence of a repository-authored universal manager is therefore not a
plugin blocker. Building one would duplicate lifecycle authority and is not
authorized. The required product work is a narrow replaceable Manager Adapter
contract and explicit ownership mapping, not another installer or package
manager.

## Current release gate

No distributable Harness plugin is eligible now. The repository has no admitted
self-authored residual-gap component, no plugin-specific task-value evidence,
no dual-format conformance PoC, no claimed-host lifecycle receipts, and no
plugin release closure or publication authority.

The next bounded PoC is offline and zero-model: map one canonical repository
metadata source to Agent Plugins 1.0.0 and OpenAI package fields, define the
component ownership matrix, and fail closed on third-party payload bundling,
dual lifecycle authority, CC Switch dependency promotion, or release-readiness
promotion. Synthetic or repository-owned non-release fixtures are sufficient.

This decision creates no plugin, performs no installation or enablement,
changes no CC Switch or consumer state, dispatches no model, and advances no
program acceptance count.
