# Read-Only Claim Trial — Native Spark/Low

Date: 2026-07-26
Status: three formal native runs complete; hard oracle failed

## Result

Three independent `GEN-NATIVE-SPARK` runs used Codex app-server `0.145.0`,
`gpt-5.3-codex-spark/low`, provider fallback disabled, an ephemeral read-only
sandbox, network disabled, approval policy `never`, and all 105 configurable
user/repository Skills disabled.

All three runs completed with exactly one raw JSON Agent message. No command,
file-change, web-search, MCP-tool, dynamic-tool, collab-agent-tool, or unknown
item was observed. The trial tree and global Codex configuration were stable,
and no new `.agents`, `.codex`, or `.git` marker appeared.

All three nevertheless failed the private claim oracle:

- C1, C2, and C4 were classified correctly in every run.
- C3 was classified as `contradicted` three times. The fixed oracle requires
  `unknown`: the sources define a readiness condition and show missing
  completion/waiver evidence, but do not establish a negative production
  decision.
- C5 was `unknown` in every run; the first run omitted the relevant `SRC-D`
  citation.
- `unsupportedConclusionCount` was `1`, `3`, and `3`, rather than zero.

The bounded conclusion is that native Spark/low did not meet this synthetic
source-conflict oracle in three repetitions. This does not establish weak-model
failure in general, research quality in general, or the value of any Skill.
It also does not yet establish a residual self-authored gap. A suitable
existing source/uncertainty-discipline treatment must be evaluated first.

## Evidence Boundary

The public packet was injected directly into the turn. The private oracle was
not written into the trial directory, and its exact serialization was not
present in the prompt. The leakage scan is not complete.

Plugin features and six statically named MCP servers were disabled. This is not
proof of complete MCP inventory. Final tree and item observations also do not
prove that no unobserved short-lived write or network event occurred.

The local raw reports remain temporary cleanup debt. The governed registry
record preserves their file hashes, internal report hashes, response hashes,
exact structured submissions, host-boundary observations, and oracle failures.
Raw stderr was not retained; only bounded classifications remain, including
zero observed MCP startup failures and one or two generic error-keyword lines
per run.
