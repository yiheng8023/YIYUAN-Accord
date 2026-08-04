# Contributing

Thank you for helping improve Agent Autonomy Harness.

This is a public research repository for agent-neutral collaboration,
capability orchestration, lifecycle control, and evidence-bound engineering.
It is not a prompt dump, a general capability mirror, a user configuration
repository, or a production runtime.

## Useful contributions

Contributions may include:

- reproducible host-capability or lifecycle observations;
- counterexamples to current assumptions or evidence claims;
- context, thread, worktree, MCP, Hook, permission, or cleanup experiments;
- exact-upstream Skill or other capability source suggestions;
- license, provenance, security, dependency, portability, maintenance, or
  overlap corrections;
- deterministic builders, validators, fixtures, and failure controls;
- documentation and public-accessibility improvements.

## External capability intake

A proposed external capability should identify:

- the concrete demand or bounded portfolio-coverage objective;
- canonical source and exact revision when available;
- license, redistribution, provenance, and maintenance evidence;
- relevant component paths and dependency closure;
- executable surfaces, install scripts, network access, file writes, accounts,
  permissions, background processes, and cleanup obligations;
- host-specific assumptions, overlap, conflicts, fallback, and exit cost;
- proposed disposition such as `candidate`, `composition`, `reference`,
  `duplicate`, `reject`, or `needs-evidence`.

Popularity, stars, installation, official-looking branding, or usefulness does
not establish admission or runtime authority.

## Third-party body policy

Keep third-party bodies exact upstream by default. Do not neutralize,
generalize, rename inside, or silently rewrite a third-party Skill to make it
portable. Put compatibility, naming, routing, composition, policy, and host
differences in metadata, Recipes, adapters, or repository-owned wrappers.

A modified fork is a separately owned derivative and must not inherit the
upstream identity or review result automatically.

## State-transition gates

Source review, portfolio admission, manager installation, host enablement,
exposure, invocation, instruction delivery, behavior, value, portability, and
release are separate decisions. A contribution affecting one state does not
authorize the next.

Runtime or external-state changes require an explicit task, authority boundary,
rollback path, and verification surface. Pull requests must not silently modify
live Agent configuration, accounts, consumer repositories, or installed
capabilities.

## Local verification

For documentation or narrow changes, run the checks relevant to the affected
surface. Before broad repository changes, run:

```bash
python -B scripts/verify_bootstrap.py
python -B scripts/verify.py
python -B -m unittest discover -s tests -v
```

Hosted CI is optional corroboration. A pull request should include the exact
local commands and limitations rather than treating a remote badge as proof.

## Public-data boundary

Do not submit:

- secrets, tokens, private account state, personal memory, private user
  preferences, or unsanitized local configuration;
- leaked prompts, proprietary dumps, restricted bodies, or content with unclear
  redistribution rights;
- raw sensitive logs or unnecessary machine/user paths;
- generated outputs as hand-authored authority;
- claims broader than the supplied evidence.

See [SECURITY.md](SECURITY.md), [NOTICE](NOTICE), and
[docs/license-policy.md](docs/license-policy.md) before contributing third-party
or security-relevant material.

## Review posture

The project may accept, revise, defer, reject, supersede, or remove a proposal.
Contribution does not imply admission, release, installation, support priority,
or endorsement. Human acceptance remains separate from automated checks.
