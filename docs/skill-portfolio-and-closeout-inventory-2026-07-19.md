# Skill Portfolio And Closeout Inventory — 2026-07-19

Status: single-host read-only Skill observation with a deferred final-closeout
ledger seed; the program is not in closeout; no repair, installation,
configuration, cleanup, commit, or push authority
Host: Windows, user home `C:\Users\15521`
Observation time: `2026-07-19T03:24:22+08:00`
Machine record:
[`../registry/skill-portfolio-and-closeout-inventory-2026-07-19.json`](../registry/skill-portfolio-and-closeout-inventory-2026-07-19.json)
Reproducer: `python -B scripts/inventory_skill_portfolio.py`

## Result first

CC Switch remains the correct operational manager, but the UI counts are
database enablement counts rather than physical, resolvable, behaviorally
verified Skill counts. The observed database contained 251 rows and reported
251 Claude plus 250 Codex enablements. The CC Switch physical Skill root
contained 75 resolvable Skill directories.

That distinction explains the earlier apparent count disagreement. It also
exposes reconciliation work that must precede installation or quality
comparison: 176 database directories had no resolvable `SKILL.md` in the CC
Switch root; Claude had 176 links to those missing paths; and 30 names had
different top-level `SKILL.md` hashes across roots.

These observations do not prove that all 176 capabilities are unavailable to
Codex. Some names also exist in runtime/plugin-owned locations outside CC
Switch. They prove only that the CC Switch database, its physical root, and its
consumer projections are not currently a content-equal set.

## Four-layer count

| Surface | Top-level directories | Physical | Symbolic links | Junctions | Resolvable top-level `SKILL.md` |
| --- | ---: | ---: | ---: | ---: | ---: |
| `~/.cc-switch/skills` | 75 | 75 | 0 | 0 | 75 |
| `~/.agents/skills` | 73 | 30 | 42 | 1 | 73 |
| `~/.claude/skills` | 251 | 1 | 243 | 7 | 75 |
| `~/.codex/skills` | 76 | 6 | 69 | 1 | 74 |

The two Codex top-level directories without a top-level `SKILL.md` are
`.system` and `codex-primary-runtime`; they are container/runtime roots, not
classified here as broken consumer projections.

## Database and source observations

- CC Switch version: `3.17.0`.
- Storage setting: `cc_switch`; sync method: `symlink`.
- Database rows: 251; distinct names: 233.
- Enabled rows: Claude 251, Codex 250, Gemini/OpenCode/Hermes 0.
- Six enabled repository registrations were observed:
  `anthropics/skills`, `cexll/myclaude`,
  `ComposioHQ/awesome-claude-skills`, `JimLiu/baoyu-skills`,
  `larksuite/cli`, and `mattpocock/skills`.
- Of the 75 physical CC Switch Skills, 46 database rows had no repository
  attribution, 27 were attributed to `larksuite/cli`, one to Composio, and one
  to Matt Pocock. Missing attribution is not a provenance conclusion; it is an
  unresolved metadata field.
- The database had 15 duplicate-name groups. Duplicate rows are not assumed to
  be duplicate content because several directories intentionally use qualified
  names.

## Projection and collision observations

1. `~/.claude/skills` had 176 symbolic links whose CC Switch targets lacked a
   resolvable `SKILL.md`. This is a concrete broken-projection set for the
   observed filesystem.
2. Codex had only 74 database-named directories with resolvable `SKILL.md`
   under `~/.codex/skills`, although 250 database rows were enabled for Codex.
   Runtime/plugin discovery may supply some of the other names and must be
   evaluated separately.
3. Thirty same-name entries had different top-level `SKILL.md` hashes:
   `intent-contract`, `capability-router`, `closure-contract`, and all 27
   observed `lark-*` Skills. The three contract Skills remain repository-owned
   sources requiring ordinary admission into CC Switch. The Lark set requires
   source/version/host comparison; the prefix alone does not prove portability
   or non-portability.
4. `~/.agents/skills` contained 30 physical directories: the three contract
   Skills and 27 Lark Skills. Those physical entries prevent CC Switch from
   being a content-equal single source for those names even though the other 43
   entries are CC projections.
5. `-21risk-automation` existed in CC Switch and Claude but not Agents or Codex;
   `kimi-webbridge` existed in CC Switch, Claude, and Codex but not Agents.
   These are exact projection differences, not behavioral suitability claims.

No links or database rows were repaired. The next operational decision must be
made through a CC Switch-supported reconciliation path or a separately reviewed
fallback; the harness must not implement a competing manager.

## Backup boundary

The local CC Switch Skill backup root contained 20 top-level entries, 71
directories, 406 files, and 7,389,241 bytes. The configured retain count was
three, but the observed per-Skill backup layout is not interpreted as three
complete portfolio snapshots.

This proves local recovery material exists. It does not prove WebDAV coverage,
cross-device content equality, restoration completeness, or preservation of
external physical directories. Those remain fresh-environment verification
items.

## Deferred final-closeout debt ledger seed

The program is not in closeout. The following entries only prevent known
process debris and external debt from being forgotten when the total control
plan eventually reaches its final closeout gate. They are not a current cleanup
queue, do not compete with research and PoC work, and are not eligible for
action in the current phase.

| Exact target or set | Current role | Candidate disposition at eventual final-closeout review | Recheck trigger |
| --- | --- | --- | --- |
| Current repository dirty PoC working set | Current uncommitted evidence and verifier work | `retain-authoritative` | Review after this evidence package passes local verification; commit/push remain separately authorized. |
| `C:\tmp\agent-autonomy-codex-app-server-schema-0.144.6-stable` | Static CTX schema evidence named by the current evidence document | `retain-authoritative` | After CTX evidence no longer needs local reproduction, propose `delete-after-authorization`. |
| `C:\tmp\agent-autonomy-codex-app-server-schema-0.144.6-experimental` | Comparison bundle for the same CTX observation | `retain-authoritative` | Same as the stable bundle. |
| `C:\tmp\agent-autonomy-harness-mcp-schema-20260719` | Stable and experimental app-server schema bundles used for the MCP refresh interface review | `retain-authoritative` | After the MCP interface-evidence phase exits, propose `delete-after-authorization`. |
| Two exact isolated app-server homes under `C:\Users\15521\.codex\visualizations\2026\07\18\019f75fd-2b84-75f3-98b3-461fb9895206`: `mcp-status-probe-20260719` and `mcp-status-probe-20260719-run02` | Failed transport attempt and successful read-only MCP status evidence; neither contains `auth.json` or `config.toml` | `retain-authoritative` | After the MCP live-evidence phase exits, propose exact-target deletion under separate authorization. |
| `C:\tmp\codex-app-server-schema-0.145.0-20260723` and five exact `C:\tmp\agent-autonomy-mcp-tool-call-0.145.0-20260723*` probe roots | Stable 0.145.0 schema plus five isolated direct-call/multi-instance observations, including retained failure and cleanup evidence | `retain-authoritative` | After the MCP direct-call and lifecycle-evidence phase exits, propose exact-target deletion under separate authorization. |
| `C:\tmp\agent-autonomy-mcp-reload-new-threads-0.145.0-20260723-run01` | Isolated 0.145.0 new-thread config-state and status/runtime-divergence evidence | `retain-authoritative` | After the MCP new-thread-transition evidence phase exits, propose exact-target deletion under separate authorization. |
| Ten exact `C:\tmp\agent-autonomy-*` bootstrap scratch files listed in the machine record | Bootstrap copies, patch, scan patterns, or a stale plan snapshot | `delete-after-authorization` | Only when the total control plan reaches final closeout, after repository copies/Git history are rechecked. No deletion is authorized now. |
| 43 exact comparative, treatment-fidelity, and source-pinned projection temporary targets listed in the machine record, including weak-Agent incident roots and reports, synthetic Skill treatment-fidelity roots and reports, the source-pinned Matt checkout, two no-turn projection roots plus reports, two retained classifier-invalid guard runs, and three valid current-Matt/Superpowers pairs | Reproducible comparison evidence, failed/prebuilt guard evidence, treatment-delivery evidence, source review input, and exact project-projection inventory evidence | `delete-after-authorization` | Only when the total control plan reaches final closeout, durable evidence validators remain green, and separate exact-target deletion authority is granted. No deletion is authorized now. |
| `C:\Projects\agent-skills-curated` | Historical source repository and stability-period fallback | `retain-historical` | Re-evaluate only after the new harness is stable and a separate archive/delete decision is authorized. |
| `C:\Projects\agent-capability-manager` | Retired custom manager workspace | already absent; verify absence at closeout | Recheck exact path absence; do not recreate it. |
| CC database/physical/projection mismatch | Active operational debt | `blocked` | Resolve exact source authority and CC Switch-supported repair behavior before any installation or cleanup transaction. |
| GitHub Actions run for HEAD `55659f3` | Remote acceptance evidence | `blocked` | Re-run only after the account billing/spending constraint is resolved; local tests cannot replace remote matrix evidence. |

Seven of the ten bootstrap scratch files were byte-identical to current
repository files at observation time. The temporary research-plan copy was a
stale snapshot; the bootstrap patch and secret-pattern list had no one-file
repository counterpart. Their exact hashes and paths remain available for a
future final-closeout review, but this inventory does not authorize one and
does not make cleanup a current workstream.

The exact-HEAD Actions run remained recorded as a three-job failure with zero
steps. The bootstrap evidence attributes that state to account payment or
spending limits. This inventory therefore retains `blocked`; it does not call
the code red and does not claim remote green.

## Falsifiable conclusions and next gate

- Supported: CC Switch can remain the operational manager without the harness
  rebuilding source, installation, distribution, backup, or restore logic.
- Supported: UI enablement count, physical Skill count, resolvable projection
  count, and behavioral availability are different measurements.
- Falsified for this host snapshot: the current CC Switch database, physical
  root, Agents root, Claude root, and Codex root are content-equal.
- Not proved: live invocation of each Skill, Lark portability, CC Switch
  cross-device equality, or a safe automatic reconciliation action.
- Next gate: classify the 75 physical Skills and the 30 collisions by source
  authority and task coverage, then select small self-authored-disabled
  ablation scenarios. Installation and cleanup remain out of scope.
