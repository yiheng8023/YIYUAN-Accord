import ast
import io
import json
from pathlib import Path
import re
import shlex
import subprocess
import tokenize
from urllib.parse import urlsplit


RELEASE_RE = re.compile(r"^v(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)(?:\.(0|[1-9][0-9]*))?$")

CONSTITUTION_FIELDS = set((
    "schema id productId identity domainModel purpose successDefinition kernel "
    "hostAdapterStandard learnedFailureStandards qualityInvariants humanAuthority "
    "productBoundary evidenceBoundary evolutionPolicy authority"
).split())
PROGRAM_FIELDS = set((
    "schema id productId release releaseIntent constitution acceptance maintenancePlan "
    "status inputEvidence increment releaseProcedure goalModePrompt hostProjections "
    "complexityBudget processLossControl"
).split())
ACCEPTANCE_FIELDS = set((
    "schema id productId release constitution program canonicalGoalObjectiveSha256 "
    "completionExpression evidenceLanes representativeBehaviorPolicy criteria "
    "candidateVerification releaseAuthorization publicRelease claimCeiling"
).split())


def _nonempty_string(value):
    return isinstance(value, str) and bool(value.strip())


def _exact(value, fields, texts=()):
    return (
        isinstance(value, dict) and set(value) == set(fields)
        and all(_nonempty_string(value.get(field)) for field in texts)
    )


def _string_list(value):
    if not isinstance(value, list) or any(
        not _nonempty_string(item) for item in value
    ) or len(value) != len(set(value)):
        return None
    return value


def _safe_https_locator(value):
    try:
        parsed = urlsplit(value)
    except (TypeError, ValueError):
        return False
    return (
        parsed.scheme == "https" and bool(parsed.hostname)
        and parsed.username is None and parsed.password is None
        and not parsed.query and not parsed.fragment
    )


def _ast_name(node):
    return getattr(node, "id", getattr(node, "attr", getattr(node, "name", "")))


def identity_contract_errors(product_id, identity):
    fields = {
        "displayName",
        "repository",
        "pythonModule",
        "pluginIds",
        "compatibilityAliases",
    }
    if not _exact(identity, fields):
        return ["constitution.identity shape is invalid"]

    errors = []
    if not isinstance(product_id, str) or re.fullmatch(
        r"[a-z0-9]+(?:-[a-z0-9]+)*", product_id
    ) is None:
        errors.append("constitution.productId must be a lowercase slug")
    if not _nonempty_string(identity.get("displayName")):
        errors.append("constitution.identity.displayName must be non-empty")

    if not _safe_https_locator(identity.get("repository")):
        errors.append("constitution.identity.repository must be a safe HTTPS URL")

    module = identity.get("pythonModule")
    if not isinstance(module, str) or re.fullmatch(
        r"[a-z][a-z0-9_]*", module
    ) is None:
        errors.append("constitution.identity.pythonModule is invalid")
    plugin_ids = _string_list(identity.get("pluginIds"))
    if (
        not plugin_ids
        or not isinstance(product_id, str)
        or any(not item.startswith(f"{product_id}-") for item in plugin_ids)
    ):
        errors.append("constitution.identity.pluginIds are invalid")
    if identity.get("compatibilityAliases") != []:
        errors.append("constitution.identity.compatibilityAliases must be empty")
    return errors


def domain_model_errors(domain):
    fields = {
        "missionScope",
        "currentProductScope",
        "productCategory",
        "decisionDimensions",
        "crossCuttingObjects",
        "roleDistinctions",
        "rule",
    }
    if not _exact(domain, fields):
        return ["constitution.domainModel shape is invalid"]
    errors = []
    for field in ("missionScope", "currentProductScope", "productCategory", "rule"):
        if not _nonempty_string(domain.get(field)):
            errors.append(f"constitution.domainModel.{field} must be non-empty")
    for field in ("decisionDimensions", "crossCuttingObjects", "roleDistinctions"):
        values = _string_list(domain.get(field))
        if not values:
            errors.append(f"constitution.domainModel.{field} is invalid")
    return errors


def operating_model_errors(constitution):
    policies = {
        "humanAuthority": (
            ("humanOwns", "agentOwnsWithinBoundedAuthority"),
            ("humanOnlyStepRule",),
        ),
        "productBoundary": (("includes", "excludes"), ("hostRule",)),
        "evidenceBoundary": (("classes",), ("releaseRule", "claimRule")),
        "evolutionPolicy": (
            ("principles", "mechanismAdmissionRequires"),
            ("repairRule", "nonInterferenceRule", "feedbackRule", "retirementRule"),
        ),
    }
    errors = [] if set(constitution) == CONSTITUTION_FIELDS else [
        "constitution top-level shape is invalid"
    ]
    for label, (list_fields, text_fields) in policies.items():
        value = constitution.get(label)
        if not _exact(value, list_fields + text_fields):
            errors.append(f"constitution.{label} shape is invalid")
            continue
        for field in list_fields:
            items = _string_list(value.get(field))
            if not items:
                errors.append(f"constitution.{label}.{field} is invalid")
        for field in text_fields:
            if not _nonempty_string(value.get(field)):
                errors.append(f"constitution.{label}.{field} must be non-empty")
    boundary = constitution.get("productBoundary")
    if isinstance(boundary, dict) and set(boundary.get("includes", [])) & set(
        boundary.get("excludes", [])
    ):
        errors.append("constitution.productBoundary includes and excludes overlap")
    return errors


_FLAGS = "BbdEiIOPqRsSuvx"
_COMMAND = re.compile(fr"^-[{_FLAGS}]*([mc])(.*)$")
_YAML_C = re.compile(
    fr"(?m)^( *)- *-[{_FLAGS}]*c *(?:#.*)?\r?\n"
    r"(?: *(?:#.*)?\r?\n)*"
    r"\1- *[|>][+-]? *(?:#.*)?\r?\n"
    r"((?:\1 +[^\r\n]*(?:\r?\n|$))+)",
)


def _logical_shell_text(text):
    logical, quote, comment, index = [], None, False, 0
    while index < len(text):
        char = text[index]
        if char == "\\" and quote != "'":
            if text.startswith("\\\r\n", index):
                index += 3
                continue
            if text.startswith("\\\n", index):
                index += 2
                continue
        if comment:
            logical.append(char)
            comment = char not in "\r\n"
            index += 1
            continue
        if char == "#" and quote is None:
            comment = True
        if char == "\\" and quote != "'" and index + 1 < len(text):
            logical.extend(text[index:index + 2])
            index += 2
            continue
        if char in "'\"" and quote in (None, char):
            quote = char if quote is None else None
        logical.append(char)
        index += 1
    return "".join(logical)


def _lex(text):
    lexer = shlex.shlex(_logical_shell_text(text), posix=True,
                        punctuation_chars="[]{}(),=:")
    lexer.wordchars += "&*!"
    return list(lexer)


def _command_ref(text, module):
    name = re.compile(fr"{re.escape(module)}(?=$|[.:;&|<>])")
    if any(_python_ref(item[2], module) for item in _YAML_C.finditer(text)):
        return True
    try:
        items = _lex(text)
    except ValueError:
        items = []
        for line in text.splitlines():
            try:
                items.extend(_lex(line))
            except ValueError:
                items.extend(re.findall(r"\S+", line.partition("#")[0]))
    items = [item for item in items
             if re.search(r"\w", item) and item[:1] not in "&*!"]
    for index, (item, following) in enumerate(zip(items, items[1:] + [""])):
        if option := _COMMAND.fullmatch(item):
            kind, attached = option.groups()
            payload = attached or following
            target = index if attached else index + 1
            if kind == "m":
                match = name.match(payload) or any(
                    name.match(value) for value in items[target + 1:target + 3])
            else:
                match = _python_ref(payload, module)
            if match:
                return True
            if kind == "c" and payload:
                items[target] = ""
    return any(
        re.search(r"\s", item) and _command_ref(item, module) for item in items
    )


def _python_ref(source, module):
    if len(source) > 1_000_000:
        return True
    token = re.compile(fr"(?<!\w){re.escape(module)}(?!\w)")
    tokens, parts, size = [], [], 0

    def mentions(value):
        return token.search(value) or _command_ref(value, module)

    def decoded(value):
        if isinstance(value, bytes):
            try:
                return value.decode()
            except UnicodeDecodeError:
                return None
        return value if isinstance(value, str) else None

    try:
        for item in tokenize.generate_tokens(io.StringIO(source).readline):
            if item.type == tokenize.COMMENT:
                continue
            tokens.append(item)
            if item.type == tokenize.NAME and item.string == module:
                return True
            elif item.type == tokenize.STRING:
                try:
                    value = decoded(ast.literal_eval(item.string))
                except (SyntaxError, TypeError, ValueError):
                    value = item.string
                if value and mentions(value):
                    return True
                if value is not None:
                    parts.append(value)
                    size += len(value)
                    if len(parts) > 4_096 or size > 1_000_000:
                        return True
            elif item.type == getattr(tokenize, "FSTRING_MIDDLE", -1):
                if mentions(item.string):
                    return True
            elif not (item.type in (tokenize.INDENT, tokenize.DEDENT, tokenize.NL)
                      or item.type == tokenize.OP and item.string in "+()"):
                if parts and mentions("".join(parts)):
                    return True
                parts, size = [], 0
    except IndentationError:
        normalized = re.sub(r"(?m)^[ \t]+", "", source)
        return _python_ref(normalized, module) if normalized != source else False
    except (tokenize.TokenError, UnicodeError):
        return bool(parts and mentions("".join(parts))
                    or mentions(tokenize.untokenize(tokens)))
    return bool(parts and mentions("".join(parts)))


def active_tree_errors(root, locators, historical_revision):
    locators = list(locators)
    errors = [
        f"symbolic link is not admitted in active tree: {locator}"
        for locator in locators
        if (root / locator).is_symlink()
    ]
    try:
        if not isinstance(historical_revision, str) or not re.fullmatch(
            r"[0-9a-f]{40}", historical_revision
        ):
            raise ValueError
        history = [subprocess.check_output(
            ["git", "-C", str(root), "show", f"{historical_revision}:{locator}"],
            text=True, encoding="utf-8", timeout=10, stderr=subprocess.DEVNULL,
        ) for locator in ("product/constitution.json", "README.md")]
        old, readme = json.loads(history[0]), history[1]
        command = old.get("authority", {}).get("executableVerifier", "")
        product_id = old.get("productId")
        title = next(
            (line[2:] for line in readme.splitlines() if line.startswith("# ")), None
        )
        module = command.split()[3] if command.startswith("python -B -m ") else None
        if not all(_nonempty_string(value) for value in (product_id, title, module)):
            raise ValueError
    except (OSError, ValueError, json.JSONDecodeError, subprocess.SubprocessError):
        return errors + ["historical identity boundary is unavailable"]
    exact_tokens = tuple(value.lower().encode() for value in (product_id, title))
    module_re = re.escape(module.lower().encode())
    context = re.compile(
        rb"(?<![\w.-])" + module_re
        + rb"(?:(?:\.[a-z_]\w*)*:[a-z_]\w*|[\\/]|\.pyi?(?![\w]))|(?<![\w])"
        + rb"[\"']?(?:pythonmodule|python_module|module|entry|entrypoint|entry_point)"
        rb"[\"']?\s*[:=]\s*[\"']?"
        + module_re
        + rb"(?:\.[a-z_]\w*)*(?::[a-z_]\w*)?[\"']?(?![\w.-])"
    )
    for locator in locators:
        try:
            raw = locator.encode() + b"\0" + (root / locator).read_bytes()
        except OSError:
            continue
        content = raw.lower()
        source = raw.split(b"\0", 1)[1]
        text = source.decode("utf-8", errors="ignore")
        is_python = Path(locator).suffix.lower() in {".py", ".pyi"}
        surface = locator.lower().encode() if is_python else content
        if (
            any(token in content for token in exact_tokens)
            or context.search(re.sub(rb"(?m)#.*$", b"", surface))
            or not is_python and _command_ref(
                text, module
            )
            or is_python and _python_ref(
                text, module
            )
        ):
            errors.append(f"superseded identity remains in active tree: {locator}")
    return sorted(errors)


def module_layout_errors(root, module, executing, test_markers, minimum_test_count):
    errors = [] if module == executing else ["pythonModule does not match executing verifier"]
    base = root / module
    errors.extend(
        f"executing verifier module is incomplete: {module}/{name}"
        for name in ("__init__.py", "__main__.py", "control.py")
        if not (base / name).is_file()
    )
    test_file = root / "tests/product/test_product_control.py"
    if not test_file.is_file():
        return errors + ["product control tests are missing"]
    try:
        tree = ast.parse(test_file.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, SyntaxError):
        tree = ast.Module(body=[], type_ignores=[])
    markers = test_markers or []
    classes = [item[6:] for item in markers if item.startswith("class ")]
    methods = [item[4:] for item in markers if item.startswith("def ")]
    matches = [node for node in tree.body if isinstance(node, ast.ClassDef)
               and node.name in classes]
    test_class = matches[0] if len(classes) == len(matches) == 1 else None
    functions = ({node.name: node for node in test_class.body
                  if isinstance(node, ast.FunctionDef)} if test_class else {})
    assigned = {
        target.id for node in tree.body if isinstance(node, (ast.Assign, ast.AnnAssign))
        for target in getattr(node, "targets", (getattr(node, "target", None),))
        if isinstance(target, ast.Name)
    }
    invalid = (
        not methods or len(markers) != len(methods) + 1 or test_class is None
        or "TestCase" not in {_ast_name(node) for node in test_class.bases}
        or set(methods) - set(functions)
        or not isinstance(minimum_test_count, int) or isinstance(minimum_test_count, bool)
        or minimum_test_count <= 0
        or sum(name.startswith("test_") for name in functions) < minimum_test_count
        or test_class.decorator_list
        or any(functions[name].decorator_list for name in methods if name in functions)
        or assigned & (set(classes) | {"load_tests"})
        or any(isinstance(node, ast.FunctionDef) and node.name == "load_tests"
               for node in tree.body)
        or any(
            _ast_name(node) in {"_exit", "exit", "quit"}
            or isinstance(node, ast.Raise) and _ast_name(node.exc) == "SystemExit"
            for node in ast.walk(tree)
        )
    )
    if invalid:
        errors.append("product control test markers are not executable unittest methods")
    return errors


def authority_contract_errors(
    root, authority, python_module, semantic_files, required_surfaces,
):
    fields = {
        "semantic",
        "executableVerifier",
        "derivedSurfaces",
        "historicalAndResearchRole",
        "conflictRule",
    }
    if not _exact(authority, fields):
        return ["constitution.authority shape is invalid"]
    errors = []
    if authority.get("semantic") != list(semantic_files):
        errors.append("constitution.authority.semantic must name the authority files")
    if authority.get("executableVerifier") != f"python -B -m {python_module} verify":
        errors.append("constitution.authority.executableVerifier is invalid")
    surfaces = _string_list(authority.get("derivedSurfaces"))
    if not surfaces:
        errors.append("constitution.authority.derivedSurfaces is invalid")
        surfaces = []
    required = {item for item in required_surfaces if _nonempty_string(item)}
    if not required.issubset(set(surfaces)):
        errors.append("constitution.authority omits a required derived surface")
    try:
        resolved_root = root.resolve(strict=True)
    except OSError:
        return errors + ["constitution.authority repository root is unavailable"]
    for locator in surfaces:
        relative = Path(locator)
        if "\\" in locator or relative.is_absolute() or ".." in relative.parts:
            errors.append(f"constitution.authority derived surface is invalid: {locator}")
            continue
        candidate = resolved_root / relative
        try:
            resolved = candidate.resolve(strict=True)
        except OSError:
            errors.append(f"constitution.authority derived surface is missing: {locator}")
            continue
        if not resolved.is_relative_to(resolved_root) or candidate.is_symlink():
            errors.append(f"constitution.authority derived surface is unsafe: {locator}")
    for field in ("historicalAndResearchRole", "conflictRule"):
        if not _nonempty_string(authority.get(field)):
            errors.append(f"constitution.authority.{field} must be non-empty")
    return errors


def release_identity_errors(
    identity, program, acceptance,
):
    errors = []
    if set(program) != PROGRAM_FIELDS:
        errors.append("program top-level shape is invalid")
    if set(acceptance) != ACCEPTANCE_FIELDS:
        errors.append("acceptance top-level shape is invalid")
    release = program.get("release")
    match = RELEASE_RE.fullmatch(release) if isinstance(release, str) else None
    if match is None:
        return errors + ["program.release must be a v-prefixed semantic version"]
    major, minor, patch = match.groups()
    package_version = f"{major}.{minor}.{patch or '0'}"
    for index, projection in enumerate(program.get("hostProjections", [])):
        if isinstance(projection, dict) and projection.get("packageVersion") != package_version:
            errors.append(
                f"hostProjections[{index}].packageVersion does not match program.release"
            )

    repository = identity.get("repository")
    parsed = urlsplit(repository) if isinstance(repository, str) else None
    parts = parsed.path.strip("/").split("/") if parsed is not None else []
    public = acceptance.get("publicRelease")
    if parsed is None or parsed.hostname != "github.com" or len(parts) != 2:
        return errors + ["release identity requires a canonical GitHub repository"]
    owner, repo = parts
    expected = {
        "tag": release,
        "releaseLocator": f"{repository.rstrip('/')}/releases/tag/{release}",
        "releaseApi": f"https://api.github.com/repos/{owner}/{repo}/releases/tags/{release}",
        "tagApi": f"https://api.github.com/repos/{owner}/{repo}/git/ref/tags/{release}",
        "releaseNotes": f"docs/releases/{release}.md",
    }
    if not isinstance(public, dict) or any(public.get(k) != v for k, v in expected.items()):
        errors.append("acceptance.publicRelease does not match release and repository identity")
    systems = acceptance.get("candidateVerification", {}).get("requiredSystems")
    procedure = program.get("releaseProcedure", {})
    planned_systems = procedure.get("candidateVerificationSystems")
    if systems != planned_systems:
        errors.append("candidateVerification systems do not match release procedure")
    github_runs = f"{repository.rstrip('/')}/actions/runs/"
    if not isinstance(systems, dict) or any(
        locator != github_runs
        for system, locator in systems.items()
        if isinstance(system, str) and system.startswith("github-actions-")
    ):
        errors.append("candidate GitHub systems do not match repository identity")
    if isinstance(public, dict) and public.get("assetPolicy") != procedure.get(
        "assetPolicy"
    ):
        errors.append("public release asset policy does not match release procedure")
    return errors
