In Codex 0.154.0, a changed active plugin root is rechecked when creating the next
turn, including external-process version switches. Same-root, same-version edits
do not have that assurance. Use a supported distinct build identity and reinstall
for such development updates, then verify exact bytes; a version suffix is not
content verification. Skill file watching, MCP reload and Hook refresh have
different triggers and limits. Hook trust covers the normalized declaration,
not the referenced script bytes; unchanged trust is not proof of unchanged code.
A changed declaration may require renewed trust under the host's effective policy;
respect disabled choices and the actual authorization boundary. Recheck these
version-bound facts when the host changes: [native turn refresh](https://github.com/openai/codex/blob/rust-v0.154.0/codex-rs/core/src/session/turn_context.rs#L956),
[active-root cache check](https://github.com/openai/codex/blob/rust-v0.154.0/codex-rs/core-plugins/src/manager.rs#L567),
[Hook trust](https://learn.chatgpt.com/docs/hooks), and
[App Server refresh interfaces](https://learn.chatgpt.com/docs/app-server).
