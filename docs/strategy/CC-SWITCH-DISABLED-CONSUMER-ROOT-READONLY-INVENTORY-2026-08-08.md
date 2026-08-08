# CC Switch disabled-consumer root read-only inventory

Date: 2026-08-08

## Result

A privacy-minimized local probe observed the four CC Switch consumer roots not
enabled for the current Matt cohort:

| Host | Governed root | Root exists | Matt rows enabled | Matt projections |
| --- | --- | ---: | ---: | ---: |
| Gemini | `~/.gemini/skills` | no | 0 | 0 |
| GrokBuild | `~/.grok/skills` | no | 0 | 0 |
| OpenCode | `~/.config/opencode/skills` | no | 0 | 0 |
| Hermes | `~/.hermes/skills` | no | 0 | 0 |

The CC Switch database contained 25 `mattpocock/skills` rows. It was opened in
SQLite read-only/query-only mode, and its file SHA-256 was identical before and
after the observation. All four root observations were also stable.

The probe did not identify or disclose non-Matt entry names, read Skill bodies,
read settings or account data, invoke CC Switch, run third-party code, call a
model, create a missing root, or write a consumer surface.

Machine-readable evidence:
[`cc-switch-disabled-consumer-root-readonly-inventory-2026-08-08.json`](../../registry/cc-switch-disabled-consumer-root-readonly-inventory-2026-08-08.json).
Portable report:
[`REPORT.json`](../../audits/cc-switch-disabled-consumer-roots-2026-08-08/REPORT.json).

## Boundary

This establishes only disabled flags, root presence, and Matt-projection
absence at one observation time. An absent root does not prove that the host is
installed, configured, healthy, able to load Skills, able to restore state, or
convergent across devices. It is not authority to create the root, enable a
Skill, connect an account, execute a host, or dispatch a model.

The canonical acceptance inventory remains 46 verified / 15 partial / 0
planned. Consumer mapping, source governance, and foreign-managed coexistence
remain partial.
