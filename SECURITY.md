# Security Policy

Agent Autonomy Harness is a public product repository with an unfinished v0.1
runtime surface. Treat every external
capability candidate, executable surface, instruction body, generated artifact,
and runtime claim as untrusted until its applicable review and evidence gates
close.

## Supported surface

The current default branch and product-control seam are the maintained
repository surface. Earlier Git revisions are inactive evidence, not supported
production releases. The project does not currently claim a production-ready
versioned runtime.

## Reporting security issues

Private vulnerability reporting is enabled for this repository. Submit
sensitive findings through
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

Private reporting availability is a live GitHub setting and must be rechecked
before making a current availability claim.

Include the affected revision and artifact, impact and authority boundary, safe
reproduction evidence, known downstream state, and any containment or cleanup
already performed.

## Runtime boundary

Repository verification does not authorize runtime mutation. Installation,
enablement, account connection, external writes, and trust-boundary changes
require separate authority, rollback, and live verification. A reviewed or
installed candidate is not thereby safe, enabled, exposed, invoked, valuable,
or portable.

## Scope limits

This project does not certify that an external capability is universally safe,
legally sufficient in every jurisdiction, suitable for every host, or free of
unknown dependencies. Claim scope remains limited to the recorded evidence.
