"""Build the local Claude Code package or render a shared Skill for Codex."""

import argparse
import errno
from hashlib import sha256
import json
import os
from os.path import samestat
from pathlib import Path
import re
import stat
from tempfile import TemporaryDirectory


ROOT = Path(__file__).resolve().parents[1]
CURRENT = "plugins/yiyuan-accord-codex"
ENTRY = "deliver-demand-driven-outcome"
PACKAGE = "yiyuan-accord"
MARKETPLACE = "yiyuan-accord-development"
HOOK_SOURCE = "plugins/yiyuan-accord-claude-code/runtime/accord-hook.cjs"
ENTRY_SOURCE = "product/skill-sources/deliver-demand-driven-outcome.md"
LIFECYCLE_SKILL = "skills/manage-plugin-lifecycle/SKILL.md"
LIFECYCLE_SOURCE = "product/skill-sources/manage-plugin-lifecycle.md"
CODEX_LIFECYCLE_SOURCE = "product/skill-sources/manage-plugin-lifecycle.codex.md"
SKILLS = ("coordinate-capabilities", "maintain-task-continuity",
          "verify-and-close-outcome")
FOUNDATION = (f"skills/{ENTRY}/references/meta-guidance.md",
              f"skills/{ENTRY}/references/meta-guidance.zh-CN.md")

CLAUDE_ENTRY = """Claude Code's native Hook supplies brief coordination guidance. Reuse the
meta-guidance already present in this task. When it is missing, read the bundled
[English translation](references/meta-guidance.md) before applying these duties.
The [Chinese source](references/meta-guidance.zh-CN.md) travels with it. Use this
foundation within the host's instruction hierarchy and the user's authority."""

SESSION_NOTES = {
    "startup": "",
    "resume": "Accord resume entry: reconcile the current user instruction, pauses, ownership and observed effects before continuing.",
    "clear": "Accord clear entry: recover any unfinished work only from explicitly retained, applicable evidence.",
    "compact": "Accord compact entry: check which task facts survived and recover missing evidence before acting on it.",
    "fork": "Accord fork entry: copied history carries context. Establish this task’s authority and writer before acting.",
}
SUBAGENT_NOTE = "Accord subagent entry: apply these duties within the delegated scope. Reconcile your own inputs and leave the parent task state to its owner."

NATIVE_CAPABILITIES = """# Claude Code capabilities

Use the available Skill and Agent tools, the native plugin view, and the session’s
effective tool requirements as sources. Respect user-only Skill invocation and
managed or disabled components.

For authorized delegation, check the current Agent tool and subagent definition
for model and effort. Choose them per subtask when both the dispatch interface
and the configured provider support them. Check context inheritance separately.
Record unsupported choices, environment overrides and observable substitutions.
[Skills](https://code.claude.com/docs/en/skills) · [Subagents](https://code.claude.com/docs/en/sub-agents)
"""

CONTINUITY = """## Restore the current task

Use Claude Code’s native history and continuation for the same task. Match the
actual session and workspace before reusing earlier facts. Preserve the current
goal, new user instructions, accepted results, pauses, permissions and outstanding
effects. A resume or compaction event calls for reconciliation. Use explicit
evidence of permission and ownership before acting.

Treat interruption as a request to stop. Check the tool’s actual terminal and
target state before retrying. When the result is uncertain, retain the uncertainty
and proceed only with independent work. A completed task leaves room for a normal
new request. Resume, a new task and a copied-history fork have different effects.

For authorized cross-entry continuation, use the host’s supported path with the
actual entry and configuration. Verify that the old writer stopped before allowing
another process to write. Use the host’s session and context observations where
available. Keep unfinished responsibilities with enough source evidence to recover.
[CLI resume](https://code.claude.com/docs/en/cli-reference) · [Desktop continuation](https://code.claude.com/docs/en/desktop#coming-from-the-cli)

"""

CLAUDE_LIFECYCLE = """
## Claude Code entry conditions

Use the installed CLI’s `--plugin-dir` for an isolated session. For local Desktop
Code, start with its native plugin management and check the actual Code engine,
provider, plugin scope and effective Hook policy. Use scoped setup and removal
controls within the user’s authority. Observe enabled state, actual events and
usable output before concluding adoption.
[CLI flags](https://code.claude.com/docs/en/cli-reference) · [Desktop plugin management](https://code.claude.com/docs/en/desktop#install-plugins)
"""


def json_bytes(value):
    return (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def split_guidance(data, heading):
    text = data.decode("utf-8").replace("\r\n", "\n")
    if text.count("\n" + heading) != 1:
        raise ValueError(f"Current Skill structure changed around {heading}")
    return text.split("\n" + heading, 1)


def compose_entry(source, host_intro=None):
    """Render the Skill, collecting the named duties without exposing source markers."""
    text = source.decode("utf-8").replace("\r\n", "\n")
    header = re.match(r"\A---\n(.+?)\n---\n", text, re.DOTALL)
    fields = header[1].splitlines() if header else []
    metadata = dict(line.split(": ", 1) for line in fields if ": " in line)
    if (len(fields) != 2 or metadata.get("name") != ENTRY or
            not metadata.get("description", "").strip()):
        raise ValueError("Invalid coordination Skill metadata")
    # The released Codex entry parser consumes these two fields in this order.
    text = f"---\nname: {ENTRY}\ndescription: {metadata['description']}\n---\n" + text[header.end():]
    roles = {"host-entry", "scope", "action", "verification"}
    sections = {}

    def render(match):
        role, body = match.groups()
        if role not in roles or role in sections or not body.strip() or "<!-- accord:" in body:
            raise ValueError(f"Invalid coordination Skill section: {role}")
        sections[role] = body
        return host_intro if role == "host-entry" and host_intro is not None else body

    rendered = re.sub(r"^<!-- accord:([\w-]+) -->\n(.*?)\n^<!-- /accord -->$",
                      render, text, flags=re.MULTILINE | re.DOTALL)
    if sections.keys() != roles or "<!-- accord:" in rendered or "<!-- /accord" in rendered:
        raise ValueError("Incomplete or unmatched coordination Skill sections")
    skill = rendered.encode("utf-8")
    if len(skill) > 10000:
        raise ValueError("Coordination Skill exceeds the 10000-byte input limit")
    return skill, sections


def compile_entry_hook(template, skill, sections):
    """Bind the short Claude context to the full Skill before exposing the package."""
    context = "\n\n".join((
        "Accord task entry. For material needs, consult the installed yiyuan-accord:deliver-demand-driven-outcome Skill. Reuse equivalent meta-guidance already present.",
        sections["scope"],
        sections["action"],
        "Retain the goal, authority, pauses, verified results and unfinished work. Check actual effects and writer ownership before retry, recovery or handoff.",
        sections["verification"],
    ))
    # Keep every variant within the project's budget for the local Desktop entry.
    max_bytes = 1800
    for note in (*SESSION_NOTES.values(), SUBAGENT_NOTE):
        output = context + ("\n\n" + note if note else "")
        if len(output.encode("utf-8")) > max_bytes:
            raise ValueError(f"Claude entry exceeds the {max_bytes}-byte context budget")
    entry = {"skillSha256": sha256(skill).hexdigest(), "context": context,
             "sessionNotes": SESSION_NOTES, "subagentNote": SUBAGENT_NOTE,
             "maxContextBytes": max_bytes}
    marker = b"/* compiled entry guidance */ null"
    if template.count(marker) != 1:
        raise ValueError("Expected one compiled guidance slot in the Claude Hook")
    return template.replace(marker, json.dumps(entry, ensure_ascii=True, indent=2).encode("ascii"))


def compose_lifecycle(common, setup_mechanism, host_guidance):
    placeholder = b"{{setup_mechanism}}"
    if common.count(placeholder) != 1:
        raise ValueError("Expected one setup mechanism in the shared lifecycle Skill source")
    shared = common.replace(b"\r\n", b"\n").replace(placeholder, setup_mechanism)
    appendix = host_guidance.replace(b"\r\n", b"\n")
    return shared.rstrip() + b"\n\n" + appendix.lstrip()


def write_new_projection(output, content):
    """Publish a fully written Skill without overwriting an existing destination."""
    with TemporaryDirectory(prefix=".accord-skill-", dir=output.parent) as temporary:
        staged = Path(temporary) / "SKILL.md"
        if staged.write_bytes(content) != len(content):
            raise OSError("Incomplete Skill projection")
        if os.name == "nt":
            staged.rename(output)  # Windows rename refuses an existing destination.
            return
        try:
            os.link(staged, output)
            return
        except OSError as error:
            if error.errno not in (errno.EPERM, errno.ENOSYS, errno.EOPNOTSUPP):
                raise
            raise OSError(error.errno, "Select a destination filesystem that permits hard links", output) from error


def build_codex_lifecycle(output):
    """Write the Codex lifecycle projection to a new file."""
    output = Path(output).absolute()
    content = compose_lifecycle(
        (ROOT / LIFECYCLE_SOURCE).read_bytes(),
        b"Accord's Node commands or state MCP",
        (ROOT / CODEX_LIFECYCLE_SOURCE).read_bytes(),
    )
    write_new_projection(output, content)
    return output


def restore_staged_entry(output, staging, entry, written):
    files = {Path(name): data for name, data in written.items()
             if name == entry or name.startswith(entry + "/")}
    members = set(files)
    members.update(parent for name in files for parent in name.parents if parent.parts)
    for relative in sorted(members, key=lambda name: len(name.parts)):
        path = output / relative
        info = path.lstat()
        if stat.S_ISLNK(info.st_mode) or (
                getattr(info, "st_file_attributes", 0) & stat.FILE_ATTRIBUTE_REPARSE_POINT):
            raise OSError(f"Build output changed at {path}")
        if relative in files:
            data = files[relative]
            unchanged = (stat.S_ISREG(info.st_mode) and info.st_size == len(data)
                         and path.read_bytes() == data)
        else:
            children = {output / name for name in members if name.parent == relative}
            unchanged = stat.S_ISDIR(info.st_mode) and set(path.iterdir()) == children
        if not unchanged:
            raise OSError(f"Build output changed at {path}")
    (output / entry).rename(staging / entry)


def build(output):
    """Write a new local marketplace and package. Return the package path."""
    output = Path(output).absolute()
    source_paths = ["scripts/build_claude_plugin.py", f"{CURRENT}/.codex-plugin/plugin.json",
                    HOOK_SOURCE, ENTRY_SOURCE, LIFECYCLE_SOURCE, "LICENSE", "NOTICE"]
    source_paths.extend(f"{CURRENT}/skills/{skill}/SKILL.md" for skill in SKILLS)
    source_paths.extend(f"{CURRENT}/{name}" for name in FOUNDATION)
    sources = {name: (ROOT / name).read_bytes() for name in source_paths}

    metadata = json.loads(sources[f"{CURRENT}/.codex-plugin/plugin.json"])
    version = metadata["version"]
    if not isinstance(version, str) or not re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+(?:-[A-Za-z0-9.-]+)?", version):
        raise ValueError("Expected a current Accord version")
    manifest = {key: metadata[key] for key in
                ("description", "author", "homepage", "repository", "license", "keywords")}
    manifest.update(name=PACKAGE, version=f"{version}-claude-dev.4", skills="./skills/")
    hook_command = 'node "${CLAUDE_PLUGIN_ROOT}/runtime/accord-hook.cjs"'
    command = {"type": "command", "command": hook_command, "timeout": 3}
    hooks = {
        "SessionStart": [{"matcher": "|".join(SESSION_NOTES), "hooks": [command]}],
        "SubagentStart": [{"hooks": [command]}],
    }
    files = {
        ".claude-plugin/plugin.json": json_bytes(manifest),
        "hooks/hooks.json": json_bytes({"hooks": hooks}),
        "LICENSE": sources["LICENSE"],
        "NOTICE": sources["NOTICE"],
        "README.md": (
            "# YIYUAN Accord development package\n\n"
            f"This Claude Code candidate uses Accord {version} guidance. It is intended for scoped verification.\n\n"
            "Use the plugin directory with `claude --plugin-dir` for a single CLI session. "
            "The package supplies Skills and adds coordination guidance at supported native entry events. "
            "Claude Code owns execution, interruption and session restoration. "
            "Validate the actual local Desktop Code entry before treating it as supported.\n"
        ).encode("utf-8"),
    }
    for skill in SKILLS:
        name = f"skills/{skill}/SKILL.md"
        files[name] = sources[f"{CURRENT}/{name}"]
    entry = f"skills/{ENTRY}/SKILL.md"
    files[entry], sections = compose_entry(sources[ENTRY_SOURCE], CLAUDE_ENTRY)
    files["runtime/accord-hook.cjs"] = compile_entry_hook(sources[HOOK_SOURCE], files[entry], sections)
    for name in FOUNDATION:
        files[name] = sources[f"{CURRENT}/{name}"]
    files["skills/coordinate-capabilities/references/native-capabilities.md"] = NATIVE_CAPABILITIES.encode("utf-8")

    continuity = "skills/maintain-task-continuity/SKILL.md"
    head, _ = split_guidance(files[continuity], "## Modes and saved task state")
    _, tail = split_guidance(files[continuity], "## Interruptions and changed surroundings")
    interruptions, _ = split_guidance(tail.encode("utf-8"), "## Context capacity and handoff")
    files[continuity] = (
        head + "\n\n" + CONTINUITY + "## Interruptions and changed surroundings" + interruptions.rstrip() + "\n"
    ).encode("utf-8")
    files[LIFECYCLE_SKILL] = compose_lifecycle(
        sources[LIFECYCLE_SOURCE], b"the plugin's entry Hook", CLAUDE_LIFECYCLE.encode("utf-8"),
    )

    package = output / "plugins" / PACKAGE
    catalog = {
        "name": MARKETPLACE,
        "description": "Local YIYUAN Accord development builds for Claude Code.",
        "owner": {"name": manifest["author"]["name"]},
        "plugins": [{"name": PACKAGE, "source": f"./plugins/{PACKAGE}", "description": manifest["description"]}],
    }
    catalog_bytes = json_bytes(catalog)
    written = {
        **{f"plugins/{PACKAGE}/{name}": data for name, data in files.items()},
        "build.json": json_bytes({
            "accordSourceVersion": version,
            "candidateVersion": manifest["version"],
            "sources": {name: sha256(data).hexdigest() for name, data in sources.items()},
            "marketplaceSha256": sha256(catalog_bytes).hexdigest(),
            "packageFiles": {name: sha256(data).hexdigest() for name, data in files.items()},
        }),
        ".claude-plugin/marketplace.json": catalog_bytes,
    }
    output.mkdir()
    owned_output = output.lstat()
    try:
        with TemporaryDirectory(prefix=".build-", dir=output) as temporary:
            staging = Path(temporary)
            for name, data in written.items():
                target = staging / name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(data)
            published = []
            try:
                # The build record and full package precede marketplace discovery.
                for name in ("build.json", "plugins", ".claude-plugin"):
                    destination = output / name
                    if destination.exists() or destination.is_symlink():
                        raise FileExistsError(destination)
                    (staging / name).rename(destination)
                    published.append(name)
            except OSError:
                if not samestat(owned_output, output.lstat()):
                    raise OSError("Build output directory was replaced")
                for name in reversed(published):
                    restore_staged_entry(output, staging, name, written)
                raise
    except OSError as error:
        try:
            if samestat(owned_output, output.lstat()):
                output.rmdir()
            else:
                raise OSError("Build output directory was replaced")
        except OSError:
            raise OSError(f"Build failed with output remaining at {output}: {error}") from error
        raise
    return package


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    destination = parser.add_mutually_exclusive_group(required=True)
    destination.add_argument("--output", type=Path, help="A new local Claude marketplace directory")
    codex_output_help = "a new file; on POSIX use a directory that permits hard links"
    destination.add_argument("--codex-lifecycle-output", type=Path, help=f"Render the lifecycle Skill to {codex_output_help}")
    destination.add_argument("--codex-entry-output", type=Path, help=f"Render the coordination Skill to {codex_output_help}")
    args = parser.parse_args()
    try:
        if args.codex_entry_output is not None:
            content, _ = compose_entry((ROOT / ENTRY_SOURCE).read_bytes())
            write_new_projection(args.codex_entry_output, content)
            print(args.codex_entry_output)
        elif args.codex_lifecycle_output is not None:
            print(build_codex_lifecycle(args.codex_lifecycle_output))
        else:
            print(build(args.output))
    except (OSError, ValueError, KeyError) as error:
        parser.exit(1, f"{error}\n")


if __name__ == "__main__":
    main()
