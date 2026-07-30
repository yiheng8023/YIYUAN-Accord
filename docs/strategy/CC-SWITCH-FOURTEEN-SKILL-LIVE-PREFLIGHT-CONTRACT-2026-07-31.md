# CC Switch Fourteen-Skill Live Preflight Contract — 2026-07-31

Status: read-only fail-closed preflight passed for the current layered
`doc`/`pdf` state. No uninstall, host toggle, configuration write, restart,
separate app-server, model turn, archive, or remote mutation is authorized.

## Result

The fourteen subtraction targets, CC-owned trees, database rows, three host
links, backup order, Matt 22-row sentinel, first-party physical sentinels, and
the two Codex host-disable rows remain valid. The refreshed whole-state
fingerprint passes against the live CC Switch 3.19.0 state.

The previous contract failed because it required the private Codex `doc` and
`pdf` aliases to be absent. That condition was stricter than the actual
host-disable mechanism. CC Switch now marks both rows Codex-enabled and has
restored both private aliases, while the two official Codex
`[[skills.config]] enabled=false` entries remain present.

## Canonical identity boundary

Pinned OpenAI Codex `rust-v0.146.0` source establishes the relevant identity
rules:

- a path-based Skill configuration selector is canonicalized;
- every discovered `SKILL.md` path is canonicalized before metadata is stored;
- merged roots are deduplicated by canonical `path_to_skills_md`.

Therefore the common-root and private Codex aliases resolve to the same
CC-owned `SKILL.md` identity. The existing common-root path selectors continue
to describe that canonical identity even when CC Switch restores another
alias. Manager projection state and Codex host enablement are separate layers.

This source-backed conclusion replaces the earlier inference that alias
presence alone proved duplicate live host exposure. The current task startup
inventory is consistent with the conclusion, but no fresh separate app-server
probe was started, so fresh current-host exposure is deliberately not claimed.

## Current frozen state

- CC Switch database rows: 55;
- CC-owned Skill trees: 55;
- projection entries: CC 55, common agents root 41, Claude 55, Codex 57;
- backups: 20;
- subtraction targets: 14;
- `doc` and `pdf`: CC-owned physical trees, common/Claude/private-Codex
  aliases, plus two disabled Codex config rows;
- policy mode: `canonical-host-disable`.

The preflight fingerprints safe Skill metadata, tree identities, projection
topology, backup order, and the two relevant Codex config rows. Credentials,
provider data, account/session payloads, raw settings, and raw database bytes
remain excluded.

## Claim boundary

This proves only that the repeatable current read-only preflight passes and
that the Codex identity mechanism is source-backed. It does not prove:

- a fresh independent current-host exposure result;
- Skill invocation, instruction delivery, behavior, or value;
- atomic manager uninstall or rollback execution;
- remote recovery;
- authorization for the fourteen-item transaction or any other mutation.

The whole-state fingerprint remains a point-in-time gate, not a transaction
lock. It must be rerun immediately before any separately authorized canary.
