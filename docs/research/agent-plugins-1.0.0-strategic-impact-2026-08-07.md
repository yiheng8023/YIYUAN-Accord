# Agent Plugins 1.0.0 source verification and strategic impact — 2026-08-07

## Decision card

- **The standard is real.** Agent Plugins 1.0.0 defines a vendor-neutral
  directory package with a required root `plugin.json`, portable Agent Skills
  under `skills/`, and MCP servers in `mcp.json`.
- **The multi-vendor claim is substantially true.** The initial Technical
  Steering Committee lists individual representatives affiliated with Amazon,
  Cursor, Microsoft, OpenAI, and Vercel. Vercel's Jonathan Hefner is the Lead
  Core Maintainer.
- **“Formally released” needs a qualification.** The exact current
  specification repository calls 1.0.0 `Published` and contains a 2026-07-24
  publication commit, but the separately deployed documentation source still
  calls the same version `Working Draft`. The specification repository exposes
  no Git tag or GitHub Release at the review time.
- **Client support is real but incremental.** The official compatibility page
  lists VS Code, Cursor, GitHub Copilot, ChatGPT & Codex, and Kiro. It does not
  list Claude Code, Warp, Cloudflare, Adobe, Google, AMD, Unitree, Meta, Z.ai,
  DeepSeek, or Doubao as conformant clients or governing organizations.
- **Harness impact is high but layer-bounded.** Agent Plugins should become the
  external interoperability floor for packaging Skills and MCP servers. It
  prevents the Harness from inventing a competing generic plugin package
  format. It does not replace the Harness product.

## Scope and claim boundary

The user supplied an OCR-like Chinese news excerpt but no original publisher
or post locator for that excerpt. This review therefore verifies the underlying
claims against primary sources; it does not attribute the excerpt to a specific
author or publication.

This is public-source research and a repository strategy rebaseline only. No
Plugin, Skill, MCP server, App, Hook, account, model, configuration, CC Switch
state, or consumer projection was installed, enabled, connected, executed, or
changed. No client conformance or cross-host behavior was tested.

## Frozen primary sources

Retrieved on 2026-08-07:

- Agent Plugins specification repository at exact commit
  [`bd383552`](https://github.com/agentplugins/agent-plugins-spec/tree/bd383552095128f6effe895b9257cfd580a6d179).
- The publication commit
  [`1fc1b627`](https://github.com/agentplugins/agent-plugins-spec/commit/1fc1b6270e3cc492ec2d24ad7a34277c6d53b9c1),
  dated 2026-07-24 and titled “Publish Agent Plugins Specification 1.0.0”.
- Exact normative
  [specification](https://github.com/agentplugins/agent-plugins-spec/blob/bd383552095128f6effe895b9257cfd580a6d179/spec/1.0.0.md),
  [plugin schema](https://github.com/agentplugins/agent-plugins-spec/blob/bd383552095128f6effe895b9257cfd580a6d179/schemas/1.0.0/plugin.schema.json),
  [MCP schema](https://github.com/agentplugins/agent-plugins-spec/blob/bd383552095128f6effe895b9257cfd580a6d179/schemas/1.0.0/mcp.schema.json),
  [governance](https://github.com/agentplugins/agent-plugins-spec/blob/bd383552095128f6effe895b9257cfd580a6d179/GOVERNANCE.md),
  [maintainers](https://github.com/agentplugins/agent-plugins-spec/blob/bd383552095128f6effe895b9257cfd580a6d179/MAINTAINERS.md),
  and [future considerations](https://github.com/agentplugins/agent-plugins-spec/blob/bd383552095128f6effe895b9257cfd580a6d179/FUTURE_CONSIDERATIONS.md).
- Agent Plugins documentation source at exact commit
  [`e139c263`](https://github.com/agentplugins/agent-plugins-site/tree/e139c26382e8dacfde2f61675e413286054e5be6),
  including its current
  [compatible-client data](https://github.com/agentplugins/agent-plugins-site/blob/e139c26382e8dacfde2f61675e413286054e5be6/lib/compatible-clients.ts)
  and the still-stale
  [Working Draft label](https://github.com/agentplugins/agent-plugins-site/blob/e139c26382e8dacfde2f61675e413286054e5be6/content/docs/specification.mdx).
- OpenAI's current
  [Plugins in ChatGPT and Codex](https://help.openai.com/en/articles/20001256-plugins-in-codex)
  documentation.
- GitHub's current
  [Copilot CLI plugin reference](https://docs.github.com/en/enterprise-cloud@latest/copilot/reference/copilot-cli-reference/cli-plugin-reference)
  and Microsoft's current
  [VS Code Agent Plugins](https://code.visualstudio.com/docs/agent-customization/agent-plugins)
  documentation.

The exact specification repository revision was the live `main` and `HEAD`
revision during review. `git ls-remote` returned no `refs/tags/*`. This is a
dated observation, not a promise that upstream will remain untagged.

## What 1.0.0 standardizes

The portable floor is deliberately small:

```text
plugin root/
├── plugin.json
├── skills/
│   └── <skill>/SKILL.md
├── mcp.json
└── <reverse-domain client extension>/
```

The normative contract includes:

- one required, closed root `plugin.json` manifest;
- fixed discovery locations for Skills and MCP servers;
- versioned canonical schemas;
- path containment for package-supplied paths;
- isolated failure boundaries for invalid component types, Skills, MCP entries,
  and component processes;
- incremental client conformance: a client may support only Skills or only a
  subset of MCP transports;
- `PLUGIN_ROOT` and client-managed persistent `PLUGIN_DATA` for stdio MCP
  subprocesses;
- reverse-domain namespaces for client-specific extensions.

The v1 portable component set contains exactly two types: Agent Skills and MCP
servers. Commands, Hooks, Agents, rules, and LSP servers remain outside the
portable core.

## What it explicitly does not standardize

The specification keeps distribution, installation, permissions, user
experience, and client-specific capabilities under client control. Its future
considerations explicitly leave these areas open:

- trust, permission declarations, approval UX, and sandbox policy;
- provenance, signatures, and attestations;
- secret injection, scope, rotation, and revocation;
- enterprise allowlists, registries, and policy overrides;
- lifecycle audit events;
- plugin dependencies;
- a standard validator or conformance test harness.

Package path containment is not a subprocess sandbox. A valid package can still
start code or reach external systems subject to the client and operating-system
boundary.

## News-claim adjudication

| Claim in the supplied excerpt | Verdict | Qualification |
|---|---|---|
| Agent Plugins 1.0.0 exists | verified | Exact normative spec and schemas exist. |
| Vercel and OpenAI participated | verified | More precisely, their affiliated individuals sit on the initial TSC with Amazon, Cursor, and Microsoft representatives. |
| It is vendor-neutral and openly governed | verified | Governance seats belong to individuals; no vendor-reserved seats or single-vendor TSC majority are allowed. |
| It bundles Skills and MCP servers in one directory | verified | These are the only two portable v1 component types. |
| One invalid component need not break the rest | verified with boundary | Fatal root-manifest violations reject the plugin; narrower component failures are isolated. |
| ChatGPT and multiple clients already support it | verified as documented support | The official list is VS Code, Cursor, GitHub Copilot, ChatGPT & Codex, and Kiro; support is component- and transport-specific. |
| It is an unqualified final/GA release | not safe to claim | Repository text says Published, while the deployed site source says Working Draft and there is no tag or GitHub Release. |
| Every brand appearing in the excerpt is a participant or supported client | unsupported | The official governance and compatibility lists do not contain most of those names. |

OpenAI's product-level term “plugin” is broader than the Agent Plugins 1.0.0
portable core: OpenAI documents plugin listings that may include Skills, Apps,
and app templates. The official Agent Plugins compatibility list supports the
claim that ChatGPT & Codex load the portable format, but the two taxonomies must
not be treated as identical.

## Strategic impact on Agent Autonomy Harness

### Decision: adopt, do not duplicate

Treat Agent Plugins 1.0.0 as the current external packaging-interoperability
baseline for Skills plus MCP servers. Do not author a competing general-purpose
plugin manifest, component-discovery layout, or portable MCP package schema
unless a later exact comparison proves a residual gap that cannot be expressed
through the standard or a client extension.

This is an architecture-adjusting decision, not a project-ending one.

| Harness layer | Effect |
|---|---|
| Capability ecosystem | Add Agent Plugins version, exact revision, schema identities, conformance scope, and upstream-status conflict to source metadata. |
| Consumer projections | Prefer emitting or consuming the standard portable core; keep host-specific behavior in reverse-domain extensions or adapters. |
| CC Switch | Remains the operational authority for source pinning, review, install/update transactions, enablement, rollback, and consumer projection. The standard does not replace it. |
| Portable decision core | Unchanged: intent intake, routing, rerouting, context lifecycle, topology, verification, and closure are not packaging concerns. |
| Runtime lifecycle plane | Unchanged: desired state, leases, observed state, release, recovery, and cleanup evidence remain Harness/runtime concerns. |
| Host authorization | Unchanged: native approvals, sandboxing, account/data boundaries, and permission enforcement remain client/host-owned. |
| Process-fidelity program | Unchanged: requirement-to-delivery loss, durable decisions, receipts, human gates, cumulative loss, handoff, and acceptance are outside the format. |

### Immediate design consequences

1. Separate **package conformance** from installation, enablement, exposure,
   invocation, instruction delivery, behavior, value, portability, and
   production readiness.
2. Add a first-class `agent-plugins` standard identity to future capability
   source snapshots instead of inferring compatibility from a filename.
3. Freeze exact upstream revisions or schema digests because the current
   repository and deployed documentation disagree on publication status.
4. Preserve exact upstream package bytes. Compatibility, policy, routing, and
   host differences belong in metadata, client extensions, adapters, Recipes,
   or repository-owned wrappers.
5. Do not assume that a client appearing on the compatibility page supports all
   component types, transports, lifecycle operations, or security controls.
6. Do not migrate, install, enable, or repackage current CC Switch or consumer
   state from this research result alone.

## Next gate

The smallest next step is an offline mapping from the standard's exact portable
fields and failure boundaries to the Harness capability-source model and CC
Switch consumer-projection contract. That mapping should identify direct reuse,
metadata additions, client-extension needs, and retained lifecycle authority.

It must remain no-install, no-enable, no-model, and no-consumer-mutation. A live
client conformance probe or an actual package migration would require a new
task-bound authority and verification surface.
