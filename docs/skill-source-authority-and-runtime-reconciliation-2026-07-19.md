# Skill Source Authority And Runtime Reconciliation — 2026-07-19

Status: read-only single-host reconciliation; current research/PoC phase; no
installation, projection repair, configuration mutation, cleanup, commit, or
push authority
Date: 2026-07-19
Machine record:
[`../registry/skill-source-authority-and-runtime-reconciliation-2026-07-19.json`](../registry/skill-source-authority-and-runtime-reconciliation-2026-07-19.json)
Reproducer: `scripts/reconcile_skill_source_authority.py`

## Result first

The apparent 176-Skill CC Switch physical gap is mostly a lifecycle/ownership
mix, not an instruction to install 176 payloads. Of the 176 database directories
missing from `~/.cc-switch/skills`, 148 matched an exact Skill directory in the
current Codex plugin cache and another 25 matched package-qualified aliases.
Only three rows remained unresolved on the observed disk:
`product-design-prototype`, `sales-user-context`, and
`suggest-sales-next-step`.

Therefore 173 rows are best classified as runtime/plugin metadata observed by
CC Switch. Their absence from the CC physical root does not prove a Codex
capability gap and does not justify copying official/runtime payloads into CC.
It does explain why the corresponding Claude links are unresolved: Claude does
not inherit the Codex plugin cache through those links.

For non-official shared user-level Skills, the intended runtime topology is the
opposite: one CC-managed physical entity with Codex and Claude consumer
projections. `~/.agents/skills` is a CC projection or an explicit compatibility
exception for an unsupported Agent, not a second same-name production store.
Canonical source may still live in a governed repository, and project-only
Skills remain project-scoped.

## Physical CC pool authority classes

The 75 physical CC Skills partitioned into these non-overlapping observed
classes:

| Class | Count | Evidence boundary |
| --- | ---: | --- |
| Approved payloads in this repository | 20 | All 20 existed in CC; 19 directory trees were byte-equal. |
| `larksuite/cli` attributed physical payloads | 27 | External source metadata; portability and value remain unproved. |
| Composio-attributed physical payload | 1 | `-21risk-automation`; catalog/source presence is not admission. |
| Unattributed physical payloads outside this repository's approved inventory | 27 | Exact names are in the machine record; source authority remains unresolved. |

The six enabled CC repository registrations are discovery/source-manager
configuration. They do not prove that every repository has a currently
physical, attributed payload in the CC root.

## Two concrete authority collisions

### Approved `handoff`

All 20 approved repository payload names were present in CC. Nineteen were
tree-equal. `handoff` differed: the CC copy was attributed directly to
`mattpocock/skills` and differed in `SKILL.md` plus an added
`agents/openai.yaml`; the repository-approved payload remains the governed
release source for this project.

This is not a quality verdict. It is a source-authority collision that matters
because fresh-session invocation of source-backed `handoff` is still an open
PoC. The trial must name which payload digest it uses instead of treating the
shared directory name as identity.

### Three repository-authored contracts

For `intent-contract`, `capability-router`, and `closure-contract`, the
canonical trees in `C:\Projects\codex-user-config` matched the physical Agents
and Codex copies. CC Switch and Claude matched a different tree for all three.
The source repository itself was on `main` at `0c93458` with unrelated dirty
README/test/temp paths; no cross-repository write was performed.

This proves the current migration into CC is incomplete. It does not authorize
overwriting CC or Claude. A future migration must preserve canonical source,
use CC Switch for supported distribution, and verify each consumer projection.
The 30 same-name different-content observations are therefore convergence debt,
not an intended multi-authority topology.

## What this changes in the program

1. Do not treat the 251/250 UI counts as a shopping or installation list.
2. Do not vendor or copy the 173 runtime/plugin matches into CC merely to make
   database and physical counts equal.
3. Resolve the three truly unmatched rows and the 27 unattributed physical
   payloads as metadata/source-authority questions before behavioral ranking.
4. Keep the 27 Lark Skills isolated as a source-specific cohort. Test only a
   concrete Feishu/Lark task with the required account/data boundary; do not
   include them in generic collaboration ablation by default.
5. Use exact payload digests for trials involving `handoff` or the three
   contract Skills.

The prior public-source research was not wasted: it produced review,
provenance, admission, adaptation, and rejection evidence that CC's repository
list alone does not supply. Future discovery should nevertheless start with CC
Switch repositories and `skills.sh`, then consult the inherited research only
as bounded supplemental evidence.

The target product body is narrower than the current inherited repository: it
keeps self-authored collaboration-control Skills and their chain as maintained
payloads, while external payloads remain host/CC/upstream-owned comparison and
reuse inputs. The current 20 approved third-party payloads are migration
candidates, not deletion candidates in this phase. A future migration needs an
exact replacement/successor map, behavior evidence, rollback, and preservation
of provenance, license, and review records.

## Next current-phase gate

Select the first self-authored-disabled weak-Agent trials from capabilities
with bound human-collaboration shortfalls and stable source authority. The
initial candidates are repository-anchored handoff and Git topology safety;
the contract Skills remain disabled until the later self-authored comparison
arm. Model and reasoning settings must be recorded from the host, and a weak
Agent gain cannot excuse authority or critical-fact failures.

Runtime cache matching does not prove live invocation, source equality does not
approve installation, and this reconciliation does not authorize projection
repair.
