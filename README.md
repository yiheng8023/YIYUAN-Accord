# YIYUAN Accord

YIYUAN Accord is an open, Agent-neutral collaboration reliability contract and
evaluation framework. It helps an Agent start from the user's real goal, choose
the minimum sufficient route, preserve human authority, correct from observed
effects, and finish with honest verification and cleanup.

The broader mission is human-AI collaboration. The current product surface and
evidence are deliberately limited to human-Agent collaboration.

[简体中文](README.zh-CN.md)

## Start here

Clone the repository and run the product verifier with Python 3.10–3.14. CI
tests every supported Python version; the minimum and current versions run on
Windows, macOS and Linux. After v2.0 is published, reproduce that release from
its immutable tag:

```powershell
git clone --branch v2.0 --single-branch https://github.com/yiheng8023/YIYUAN-Accord.git
```

From the selected checkout, run:

```powershell
python -B -m yiyuan_accord verify --root . --json
```

Check either reference projection statically:

```powershell
python -B -m yiyuan_accord host-check --adapter codex --root . --json
python -B -m yiyuan_accord host-check --adapter claude-code --root . --json
```

These commands validate repository and package conformance. They do not install
a plugin, enable a Skill, prove host behavior, or authorize a release.

## Use it in an Agent host

Cloning is not plugin installation. Codex may read this checkout's `AGENTS.md`
as project guidance; that does not mean the YIYUAN Accord plugin is installed.

### Codex

1. Open this repository in the ChatGPT desktop app or Codex CLI. After cloning
   or changing the local marketplace, restart the desktop app so it reloads
   the catalog.
2. Open **Plugins** (or run `/plugins` in the CLI), refresh the repository's
   local marketplace, and install `yiyuan-accord-codex`. If local discovery is
   unavailable in the CLI, a published v2.0 can be added without following
   future `main` changes: `codex plugin marketplace add
   yiheng8023/YIYUAN-Accord --ref v2.0`, then `codex plugin add
   yiyuan-accord-codex@yiyuan-accord`.
3. Start a new task. Confirm the installed plugin and its
   `deliver-demand-driven-outcome` Skill appear before relying on them. Select
   the Skill explicitly when you want a deterministic activation check.
4. Run the Codex `host-check`, then run fresh Golden Tasks before claiming
   effective behavior.

The local catalog is
[`.agents/plugins/marketplace.json`](.agents/plugins/marketplace.json); the
package is [`plugins/yiyuan-accord-codex`](plugins/yiyuan-accord-codex).
OpenAI's current documentation requires explicit installation and a host
reload/new task: [package a plugin](https://developers.openai.com/plugins/build/plugins)
and [use plugins](https://learn.chatgpt.com/docs/plugins).

#### Update, disable or remove

Inspect the effective installation with `codex plugin list --json`. Refresh a
configured Git marketplace with:

```powershell
codex plugin marketplace upgrade yiyuan-accord
```

An immutable release ref does not advance to a later tag. To update or roll
back, replace `VERSION_TAG` with the intended exact tag, remove the installed
plugin and marketplace, then install again and start a new task:

```powershell
codex plugin remove yiyuan-accord-codex@yiyuan-accord
codex plugin marketplace remove yiyuan-accord
codex plugin marketplace add yiheng8023/YIYUAN-Accord --ref VERSION_TAG
codex plugin add yiyuan-accord-codex@yiyuan-accord
```

Use **Plugins** to disable or re-enable the plugin without changing the
marketplace. Remove both entries with the first two commands to uninstall it.

### Claude Code

From the repository root, load the package for one local session:

```powershell
claude --plugin-dir ./plugins/yiyuan-accord-claude
```

Then verify the namespaced Skill is present with
`/yiyuan-accord-claude:deliver-demand-driven-task`. This direct-load route is
for local use and testing; it does not create a persistent installation.
See the [official Claude Code plugin guide](https://code.claude.com/docs/en/plugins).

Changes to that checkout can be loaded with `/reload-plugins`; confirm the
namespaced Skill in `/help`. To disable or remove a direct-loaded package, end
the session and omit `--plugin-dir` next time. To roll back, check out the
intended immutable tag and launch a new session against that tag's package.

### Rollback and Troubleshoot

Rollback always selects an earlier immutable tag; never move an existing tag.
If activation is unclear, first inspect the host's installed/loaded plugin
list, then start a new task or session and run the matching `host-check`.
Absence from the host list means not enabled. A static PASS confirms package
conformance only; use fresh Golden Tasks before making a behavior claim. For a
repository defect, include the exact revision and verifier output in a report.

If the host does not explicitly list the package or Skill, it is not enabled.
The project intentionally has no installer, background runtime, Hook, MCP
server, App, state store, or automatic user-configuration mutation.

## What the product contains

- The semantic authority:
  [`constitution.json`](product/constitution.json),
  [`program.json`](product/program.json), and
  [`acceptance.json`](product/acceptance.json)
- The derived vocabulary and boundary: [`CONTEXT.md`](CONTEXT.md)
- One generic, data-driven verifier:
  [`yiyuan_accord/control.py`](yiyuan_accord/control.py)
- Replaceable, runtime-free Codex and Claude Code Skill projections
- Representative help-and-interference tasks:
  [`evals/golden-tasks.json`](evals/golden-tasks.json)

The portable loop is K1–K5: goal first, minimum sufficient route, human
authority, continuous reconciliation, and loop closure. Host rules H1–H10 and
learned-failure rules L1–L7 keep host drift and trial history outside the core.

## Evidence and release status

This checkout describes the v2.0 source line; its external state is determined
from the exact revision and tag, not a branch name. A valid verifier result
means the checkout conforms to the finite repository contract, including the
integrity and criterion mapping of accepted representative observations. It
does not independently replay host behavior or satisfy exact-candidate local
review, hosted verification, field value, production safety, publication
authority or project closeout. The exact criteria and gates are in
[`product/acceptance.json`](product/acceptance.json); finite claims and retained
behavior exclusions are in [`docs/releases/v2.0.md`](docs/releases/v2.0.md).

The previous public tag remains immutable history. Its observations are not
renamed or reused as evidence for the v2.0 identity and projections.

## Learn more only when needed

- Architecture and trust boundaries: [`docs/architecture.md`](docs/architecture.md)
- Maintainer continuation: [`docs/operations/CONTINUATION.md`](docs/operations/CONTINUATION.md)
- Development, maintenance and contributing: [`CONTRIBUTING.md`](CONTRIBUTING.md)
- Security boundary and reporting: [`SECURITY.md`](SECURITY.md)
- Project-specific analysis inputs: [`research/reviews`](research/reviews)

YIYUAN Accord is Apache-2.0 licensed. See [`NOTICE`](NOTICE) and
[`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md).
