# Security Policy

Agent Autonomy Harness is a public research repository. Treat every external
capability candidate, executable surface, instruction body, generated artifact,
and runtime claim as untrusted until its applicable review and evidence gates
close.

## Supported surface

The current default branch is the maintained repository surface. Historical
manifests, deprecated adapted payloads, drafts, audits, candidates, and dated
observations are evidence, not supported production releases. The project does
not currently claim a production-ready versioned runtime.

## Reporting security issues

Private vulnerability reporting is not currently enabled for this repository.
Do not place secrets, exploit payloads, or restricted material in a public
issue. Until a private reporting channel is enabled, file only a minimal
non-sensitive notice that a private channel is needed.

When private vulnerability reporting becomes available, use it for:

- credentials, private memory, account state, or restricted material;
- malicious or prompt-injecting instructions;
- unsafe executable, installation, Hook, MCP, Plugin, App, or adapter behavior;
- dependency or supply-chain vulnerabilities;
- license, provenance, privacy, path traversal, permission, rollback, or cleanup
  defects with material security impact.

Repository documentation must not claim that private reporting is available
until the GitHub setting has been verified live.

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
