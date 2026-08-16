# Security Policy

Agent Autonomy Harness is a public, research-stage collaboration quality
project. The current v1.1 environment-attribution tree contains a product-contract
verifier, immutable stopped v1.0 history, and inactive reference-adapter source
candidates, not a production runtime or released installable product. Its
code-pinned v1.1 profile and cohort-protocol candidates are pre-freeze text/data
inputs only; they do not install, execute, activate a cohort, or grant authority.
The current module exposes no executable v1.0 credential or Scheduled Task
cleanup entrypoint; those retired mechanics are historical at revision
`910ac01`. It contains one v1.1-only expiry command and one first-freeze source
validator, but all execution-specific anchors are unset. The live unfrozen path
does not read a private source, and the command cannot delete an unbound resource
or act before its code-owned expiry. No v1.1 credential or task currently exists.

Treat every external capability, executable surface, instruction body,
generated artifact, and runtime claim as untrusted until its applicable review
and evidence gates close.

Demand-driven discovery expands the possible source surface, not its trust.
Search results, catalogs, registries, provider metadata, retrieved
instructions, and generated routes remain untrusted source-bound input.

Discovery alone grants no installation, enablement, account, data, execution,
or persistence authority.

## Supported surface

The current default branch and product-contract verification seam are the
maintained repository surface. Earlier Git revisions are inactive evidence,
not supported production releases.

The project does not currently claim a production-ready versioned runtime.

## Reporting security issues

For a sensitive finding, first try GitHub's
[private vulnerability-reporting form][private-report].
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
require separate authority, rollback, and live verification.

A reviewed or installed candidate is not thereby safe, enabled, exposed,
invoked, valuable, or portable.

The current verification seam validates authority and evidence contracts. It
is not a production runtime, sandbox, dependency scanner, or universal safety
layer.

## Scope limits

This project does not certify that an external capability is universally safe,
legally sufficient in every jurisdiction, suitable for every host, or free of
unknown dependencies. Claim scope remains limited to the recorded evidence.

[private-report]: https://github.com/yiheng8023/agent-autonomy-harness/security/advisories/new
