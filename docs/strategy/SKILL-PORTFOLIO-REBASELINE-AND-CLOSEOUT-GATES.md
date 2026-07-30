# Skill Portfolio Rebaseline And Closeout Gates

Status: owner-directed working gate; no live installation, configuration,
deletion, commit, or push authority
Date: 2026-07-19
Machine record:
[`../../registry/skill-portfolio-rebaseline-and-closeout-gate-2026-07-19.json`](../../registry/skill-portfolio-rebaseline-and-closeout-gate-2026-07-19.json)

## Decisions

1. Reuse CC Switch for every suitable and verified operational capability it
   already owns: source registration, installation, update detection,
   distribution, backup, and restore. Do not build a parallel manager for
   those functions.
2. Treat `~/.cc-switch/skills` as the physical runtime authority for shared
   user-level Skills managed by CC Switch. Agent-specific directories are
   consumer projections, not independent production stores.
   Official/native/plugin-owned Skills remain in their host runtime and are not
   copied into CC merely to equalize counts. `~/.agents/skills` may be a CC
   projection or an explicit unsupported-Agent compatibility exception, but a
   shared same-name Skill has only one physical runtime authority. Project-only
   Skills remain project-scoped.
3. Keep source authority separate from runtime placement:
   - official and external Skills remain upstream-owned and source-preserving;
   - repository-authored Skills keep canonical source, review, and tests in
     this repository and enter CC Switch only after ordinary admission;
   - project-only Skills remain project-scoped instead of being promoted into
     the global pool without evidence.
4. Use CC Switch registered repositories and `skills.sh` as the primary
   operational discovery surfaces. Existing public-discovery records remain
   provenance and stop-rationale evidence, not a second live catalog.
5. A catalog result, download, or public repository is not trust, admission,
   installation, host visibility, or behavioral value evidence.
6. The eventual repository product body maintains only self-authored
   collaboration capabilities that survive residual-gap proof and admission;
   the admitted payload count may be zero. Official and third-party payloads
   remain upstream/CC/host-owned; the repository retains their governed
   metadata and evidence instead of becoming a permanent mirror.
7. The 20 inherited approved third-party payloads are transition baselines and
   future migration candidates. Do not remove them until CC/host replacement or
   an evidenced self-authored successor has passed source, behavior, rollback,
   and evidence-preservation gates. This is not current migration authority.

## Portfolio workflow

```text
current native/runtime and live-pool inventory
-> official capability baseline
-> CC Switch repositories and skills.sh discovery metadata
-> existing repository discovery evidence as a bounded supplement
-> non-active candidate retrieval when a named demand selects it
-> provenance, license, executable, permission, and portability preflight
-> mechanical duplicate, same-name, collision, and source-lineage analysis
-> weak-Agent-floor ablation with self-authored Skills disabled
-> capable-Agent diagnostic only when weak-result attribution is ambiguous
-> reviewed external and composition comparison
-> approved source-preserving installation through CC Switch
-> per-host visibility and invocation verification
-> repository authoring only for a repeatable residual gap
```

No candidate payload enters an active Agent Skill root merely to make later
cleanup easier. Mechanical deduplication precedes behavioral comparison;
quality, superiority, and composition decisions use task evidence rather than
name or popularity alone.

The 2026-07-24
[source-lineage and collision index](../skill-source-lineage-collision-index-2026-07-24.md)
is dated navigation evidence for `SKL-01`, `SKL-02`, `SKL-04`, and `CLS-01`.
Use it for exact occurrence selection before a new observation or comparison.
It is not current inventory, behavior, invocation, replacement, migration, or
deletion evidence.

Self-authored does not mean reimplementing every domain capability. It means
owning the smallest portable collaboration-control layer left after native,
official, reviewed external, and composition routes have been tested. That
layer may contain zero Skill payloads when no repeatable residual gap is
supported.

## Inherited payload migration gate

Before any inherited third-party payload leaves the active repository product
body, its exact directory must have an individual migration record that binds:

- current governed source, upstream source/revision, license, and provenance;
- replacement route through the host or CC Switch, or a separately evidenced
  self-authored residual-gap successor;
- A–C comparison evidence and any D-arm successor evidence;
- Codex and Claude visibility/invocation checks for the replacement;
- references, Recipes, relations, docs, tests, and generated projections that
  must change;
- rollback source and recovery verification;
- historical evidence that remains after payload removal;
- separate migration and deletion authority.

Behavioral replacement equivalence requires the same named scenario, fixed
facts, and acceptance thresholds plus verified host invocation, authority
behavior, failure/fallback, recovery, and maintenance boundaries. Bulk name
matching, a similar description, content overlap, directory presence, a CC
catalog entry, or source availability alone is not a migration pass. A payload
stays in transition when replacement behavior, rollback, evidence
preservation, or consumer parity is unproved.

## Ablation ladder

This ladder varies upstream capability mechanisms only. The hard-standard
baseline is not a ladder arm and never turns off: repository instructions,
native permission enforcement, fixed facts, critical-fact and stale-fact
thresholds, safety/authority limits, and acceptance verification remain
constant. A Skill may improve passage through those gates; it cannot define,
skip, relax, or receive credit for the gates themselves.

| Arm | Capability layers | Repository-authored Skills | Question |
| --- | --- | --- | --- |
| `A` | native/runtime only | disabled | What does the host and model already solve? |
| `B` | native/runtime plus suitable official capability | disabled | What value comes from official capability? |
| `C` | `B` plus reviewed external Skills | disabled | Does reviewed external reuse close the shortfall? |
| `D` | best external baseline plus current repository-authored Skills | enabled | Do the current self-authored Skills add net value or duplicate/frustrate the route? |
| `E` | smallest sufficient composition | only when selected by evidence | Is composition better than another Skill body? |

The weak-Agent floor is the primary acceptance condition for repository-
authored Skills and their chain. Run the corresponding self-authored-disabled
arm first so any gain is attributable. A capable-model arm is conditional
diagnostic evidence when a weak result cannot distinguish capacity from a
protocol or host defect; it is not mandatory for every PoC. Whenever models are
compared, task facts and acceptance thresholds stay fixed and actual host model
and reasoning settings are recorded. A weak-Agent improvement is useful
evidence, but it does not excuse authority, safety, or critical-fact failures.
“Self-authored-disabled” removes the named Skill payloads, not the hard-standard
baseline.

## Portfolio acceptance

| ID | Acceptance requirement |
| --- | --- |
| `SKL-01` | A dated inventory distinguishes physical content, database rows, consumer projections, broken links, and same-name different-content collisions. |
| `SKL-02` | Official, runtime-owned, direct third-party, aggregate/index, project-local, and repository-authored origins remain distinct. |
| `SKL-03` | `skills.sh` and repository catalogs remain discovery inputs; candidates stay outside active roots until review and separate installation authority. |
| `SKL-04` | Mechanical duplicates and collisions are resolved or explicitly retained before behavioral comparison. |
| `SKL-05` | Ablation compares native, official, reviewed external, current self-authored, and composed routes without privileging the self-authored route. |
| `SKL-06` | Approved shared Skills are installed and distributed through CC Switch, then verified separately on each named host. |
| `SKL-07` | A new repository-authored Skill is eligible only after a repeatable residual gap survives native, official, reviewed external, and composition comparison. |

## Program closeout cleanup gate

Program closeout requires a dedicated debt and artifact inventory. It is not
inferred from passing tests, a clean latest batch, or user acceptance of one
slice.

The inventory must cover, where present:

- temporary candidate downloads and extracted source trees;
- disposable repositories, branches, worktrees, trial threads, and test homes;
- generated packets, logs, screenshots, reports, caches, and benchmark output;
- backups and recovery artifacts created by tests or migrations;
- broken or orphaned links and stale consumer projections;
- rejected, superseded, adapted, or provisional Skill bodies;
- obsolete plans, adapters, configuration paths, and retired implementations;
- unresolved migration, provenance, collision, verification, documentation,
  CI, release, and remote-state debt.

The 2026-07-24
[repository-local exact-root preview](../closeout-cleanup-debt-preview-2026-07-24.md)
is an initial bounded input to this gate. The exact-root preview counts six
retained `.tmp` roots without reading their runtime content. It does not
authorize deletion and does not satisfy the full program closeout inventory.

Every item receives one explicit disposition:

- `retain-authoritative` — required current source or evidence;
- `retain-historical` — dated evidence with current non-authority stated;
- `archive` — kept outside the active path with a locator and owner;
- `replace-or-migrate` — successor, verification, and rollback are bound;
- `delete-after-authorization` — exact target, recoverability, and separate
  deletion authority are bound;
- `blocked` — owner, external state, or evidence prevents an honest decision.

### Closeout acceptance

| ID | Acceptance requirement |
| --- | --- |
| `CLS-01` | The inventory names exact targets, ownership, purpose, active/historical status, and disposition; broad globs or inferred ownership are insufficient. |
| `CLS-02` | Historical debt is settled by verified repair, replacement, migration, retirement, archival, or an explicit retained-debt owner and recheck trigger. Silence is not settlement. |
| `CLS-03` | Deletion, archive moves, branch/worktree cleanup, remote mutation, and external cleanup retain their own authority gates. Completion never implies deletion authority. |
| `CLS-04` | Cleanup preserves authoritative source, provenance, acceptance evidence, user work, rollback material, and required historical records. |
| `CLS-05` | Post-cleanup verification checks exact target absence/presence, remaining links, repository status, required tests, generated-state consistency, and any separately authorized remote state. |
| `CLS-06` | The program cannot claim closeout while material unowned temporary state, broken projections, undispositioned debt, unverified cleanup, or required external acceptance remains. |

GitHub Actions blocked by account billing or spending limits remains an
external closeout limitation. It must not be relabeled as code failure, remote
green evidence, or debt silently cleared by local tests.

## Current authority boundary

This gate authorizes repository planning and deterministic validation only. It
does not authorize Skill download or installation, CC Switch or Kimi
configuration changes, Agent Home mutation, deletion or archival, branch or
worktree cleanup, commit, push, release, publication, or remote mutation.
