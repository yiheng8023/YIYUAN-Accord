# Security Policy

Agent Autonomy Harness is a public product repository with an unfinished v0.2
reference implementation. Treat every external
capability candidate, executable surface, instruction body, generated artifact,
and runtime claim as untrusted until its applicable review and evidence gates
close.

Demand-driven discovery expands the possible source surface, not its trust.
Treat search results, catalogs, registries, provider metadata, retrieved
instructions, and generated route suggestions as untrusted source-bound input;
discovery alone grants no installation, enablement, account, data, execution,
or persistence authority.

## Supported surface

The current default branch and product-control seam are the maintained
repository surface. Earlier Git revisions are inactive evidence, not supported
production releases. The project does not currently claim a production-ready
versioned runtime.

## Reporting security issues

Last verified on 2026-08-11, private vulnerability reporting was enabled for
this repository. Submit sensitive findings through
<https://github.com/yiheng8023/agent-autonomy-harness/security/advisories/new>.
Do not place secrets, exploit payloads, or restricted material in a public
issue.

Use private vulnerability reporting for:

- credentials, private memory, account state, or restricted material;
- malicious or prompt-injecting instructions;
- unsafe executable, installation, Hook, MCP, Plugin, App, or adapter behavior;
- dependency or supply-chain vulnerabilities;
- license, provenance, privacy, path traversal, permission, rollback, or cleanup
  defects with material security impact.

Private reporting is a GitHub-controlled live setting. If the form is
unavailable, do not post sensitive content publicly; open a non-sensitive issue
asking the maintainers to provide a private contact route.

Include the affected revision and artifact, impact and authority boundary, safe
reproduction evidence, known downstream state, and any containment or cleanup
already performed.

## Runtime boundary

Repository verification does not authorize runtime mutation. Installation,
enablement, account connection, external writes, and trust-boundary changes
require separate authority, rollback, and live verification. A reviewed or
installed candidate is not thereby safe, enabled, exposed, invoked, valuable,
or portable.

The current control seam validates authority and evidence contracts. It is not
a production runtime, sandbox, dependency scanner, or universal safety layer.

## Scope limits

This project does not certify that an external capability is universally safe,
legally sufficient in every jurisdiction, suitable for every host, or free of
unknown dependencies. Claim scope remains limited to the recorded evidence.
