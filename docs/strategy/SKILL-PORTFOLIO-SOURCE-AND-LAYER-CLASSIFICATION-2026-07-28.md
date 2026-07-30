# Skill portfolio source and layer classification

Date: 2026-07-28
Status: verified read-only single-host classification; no portfolio mutation

Machine-readable authority:
[`../../registry/skill-portfolio-source-and-layer-classification-2026-07-28.json`](../../registry/skill-portfolio-source-and-layer-classification-2026-07-28.json)

## Result

Keep active Skill roots flat. Classify Skills through a derived registry and
management view, not by inserting `official/`, `third-party/`, or
`self-authored/` parent directories below an active Skill root.

The Agent Skills specification defines one Skill as a directory containing
`SKILL.md`, requires the frontmatter `name` to match that parent directory, and
allows an arbitrary string metadata map. The client implementation guide says
clients choose their own scan roots and describes discovering Skill directories
below those roots. Client recursion behavior is not a portable source-grouping
contract. A layout such as `skills/official/foo/SKILL.md` may work on one host
and disappear on another.

Use five independent dimensions instead:

| Dimension | Question |
| --- | --- |
| Source authority | Runtime-owned, official vendor, reviewed third party, self-authored, local unattributed, or unknown? |
| Carrier | System, bundled Plugin, primary runtime, curated Plugin/App, CC Switch SSOT, shared/client projection, or project-local? |
| Capability layer | Semantic control plane, domain workflow, host adapter, evidence/verification, or continuity/lifecycle? |
| Lifecycle | Runtime-provided, installed-managed, cached-only, candidate, test-only, inactive, or archived? |
| Exposure evidence | Disk-only, catalog-visible, startup-exposed, explicitly loaded, behavior-associated, or value-proved? |

This avoids two recurring errors: treating every cached Plugin Skill as a CC
Switch payload, and comparing semantic control-plane Skills directly with
single-task workflow Skills.

## Current CC Switch boundary

The live CC Switch 3.18.0 installed view and read-only database agree on 75
installed rows for Claude and Codex, with 73 distinct names. The recorded
source split is:

| Recorded source | Rows |
| --- | ---: |
| Local or unattributed | 46 |
| `larksuite/cli` | 27 |
| `ComposioHQ/awesome-claude-skills` | 1 |
| `mattpocock/skills` | 1 |

The only installed Matt row is `handoff`. Registering
`mattpocock/skills@main` as a repository did not install the full Matt suite.

The database supports repository owner, repository name, branch, and README
URL. It has no category or tag column. The installed UI displays inline source
labels such as `本地` or `owner/repository`, but no category or tag filter was
visible. Therefore CC Switch can remain the shared non-official installation,
projection, update, backup, and restore manager while the Harness supplies a
read-only classification index. Direct SQLite mutation is not an acceptable
way to add tags.

## Runtime and Plugin/App boundary

The current disk contains six system `SKILL.md` files and 328 files in Plugin
cache namespaces:

| Cache namespace | `SKILL.md` files |
| --- | ---: |
| OpenAI bundled | 6 |
| OpenAI primary runtime | 6 |
| OpenAI curated remote | 259 |
| Other cache namespaces | 57 |

These are cache observations, not current exposure counts. Plugin/App skills
have their own runtime-owned loading and lifecycle path; they do not
automatically belong to the CC Switch SSOT. CC Switch is therefore not a
complete inventory of official, bundled, primary-runtime, curated Plugin, or
App-provided Skills.

The historical `251` observation is not the current installed count. Current
installed evidence is 75. The historical number may have represented an older
database snapshot, a discoverable-candidate view, or runtime/Plugin metadata;
its exact current UI meaning has not been re-observed and must not be guessed.

## The three self-authored Skills

Do not retire the three Skills merely because narrower third-party workflows
look polished.

- `intent-contract` is a semantic negative-boundary intake checkpoint. It
  overlaps global hard gates, native intent reasoning, and bounded elicitation
  workflows. Its incremental value remains unproved.
- `capability-router` is a cross-ecosystem semantic control plane spanning
  native capability, Skills, Plugins, Apps, MCPs, authorization, composition,
  fallback, and reroute checkpoints. Current reviewed Matt and Superpowers
  workflows cover narrower engineering or process subflows. No known complete
  one-for-one replacement is proved.
- `closure-contract` is a cross-task claim-sufficiency checkpoint. It overlaps
  hard closeout gates and narrower verification, review, and handoff workflows.
  Its incremental value remains unproved.

The honest disposition is provisional retention pending isolated comparison,
not permanent admission and not premature removal. In particular, the absence
of a proved complete replacement for `capability-router` is evidence against a
rushed retirement decision; it is not proof that the current implementation is
optimal.

## Management rule

1. Keep each active Skill at a standard Skill directory boundary.
2. Preserve upstream payload bytes and provenance; do not rewrite third-party
   frontmatter solely to add local tags.
3. Use CC Switch repository metadata for source-backed installed Skills.
4. Join runtime/plugin inventories through a derived registry keyed by carrier,
   source locator, name, and exact digest.
5. Separate installed, cached runtime, discoverable candidate, and proven
   exposure views.
6. Compare Skills within the same capability layer before making replacement
   claims.

This classification performs no installation, uninstallation, Hook
enablement, database mutation, commit, or push.
