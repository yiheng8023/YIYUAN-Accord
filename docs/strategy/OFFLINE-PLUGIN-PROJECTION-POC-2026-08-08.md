# Offline Plugin Projection PoC — 2026-08-08

## Outcome

The Harness now has a deterministic, zero-model, offline proof of concept for
mapping one canonical repository metadata object into two **preview-only**
consumer projections:

- the Agent Plugins portable packaging floor; and
- the OpenAI plugin package shape.

The result remains `plugin-compatible + manager-agnostic +
release-not-eligible`. The PoC creates no plugin directory or manifest file,
does not install or enable anything, and assigns no runtime lifecycle authority.

## Public seam

`scripts/project_offline_plugin_projection.py` exposes one pure mapping seam:

```text
canonical repository metadata object
  -> two literal, non-installable projection previews
  or one structured fail-closed rejection
```

The repository record at
`registry/offline-plugin-projection-poc-2026-08-08.json` contains the canonical
synthetic fixture, exact expected preview, and exact expected rejection
receipts. The validator replays all of them without network, account, model, or
host-runtime access.

## Field mapping

| Canonical component | Agent Plugins preview | OpenAI preview |
| --- | --- | --- |
| Plugin identity | `plugin.json` | `.codex-plugin/plugin.json` |
| Skills | fixed `skills/` location | manifest `skills: "./skills/"` |
| Bundled MCP servers | fixed `mcp.json` location | manifest `mcpServers: "./.mcp.json"` |

This is an explicit adapter mapping, not a claim that OpenAI host extensions
are part of the portable Agent Plugins standard. The portable standard fixes
the Skill and MCP locations; the OpenAI package uses host-specific manifest
path fields.

## Lifecycle ownership

| Component class | Packaging preview | Runtime lifecycle owner |
| --- | --- | --- |
| Repository-owned synthetic fixture | represented for this PoC only | none |
| Future admitted repository-owned component | eligible for a future projection after its own gates | one selected host or manager |
| CC Switch-managed exact-upstream third-party payload | rejected | CC Switch |
| Official runtime-owned component | not copied by this PoC | owning runtime |

One component may have only one lifecycle authority. A consumer projection is
not a second manager. CC Switch remains an operational adapter where suitable;
the portable Harness core does not depend on it.

## Fail-closed cases

The PoC returns stable structured rejections for:

1. attempting to bundle a CC Switch-managed third-party payload;
2. assigning two lifecycle authorities to one component;
3. making the portable core depend on CC Switch;
4. promoting an offline preview to release-eligible; and
5. attempting to copy an official runtime-owned component; and
6. projecting a component kind outside this PoC's Skill/MCP scope.

## Evidence boundary

This proves only literal field mapping, ownership receipts, and deterministic
failure behavior for synthetic metadata. It does **not** prove that a plugin
exists, installs, conforms on either host, invokes correctly, changes model
behavior, produces task value, ports across hosts, or is ready for production
or release.

The canonical acceptance inventory therefore remains **46 verified / 15
partial / 0 planned**, with no criterion promoted. The existing release gates
for an admitted repository-owned residual-gap component, real task value,
per-host conformance, lifecycle receipts, rights/security/privacy/maintenance,
and separate release approval remain intact.
