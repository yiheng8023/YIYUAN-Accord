import ast
from hashlib import sha256
import io
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import tempfile
import time
import tokenize
from unicodedata import normalize
from urllib.parse import urlsplit


_SEMVER_PRERELEASE = (
    r"(?:0|[1-9][0-9]*|[0-9]*[A-Za-z-][0-9A-Za-z-]*)"
    r"(?:\.(?:0|[1-9][0-9]*|[0-9]*[A-Za-z-][0-9A-Za-z-]*))*"
)
_SEMVER_BUILD = r"[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*"
RELEASE_RE = re.compile(
    rf"^v(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\."
    rf"(0|[1-9][0-9]*)(?:-({_SEMVER_PRERELEASE}))?"
    rf"(?:\+({_SEMVER_BUILD}))?$"
)
CONTRACT_RELEASE_RE = re.compile(
    r"^v(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)$"
)


def _unique_json_object(pairs):
    value = {}
    for key, item in pairs:
        if key in value:
            raise ValueError(f"duplicate JSON key: {key}")
        value[key] = item
    return value


def _reject_json_constant(value):
    raise ValueError(f"non-finite JSON number: {value}")


def _strict_json_object(text):
    value = json.loads(
        text,
        object_pairs_hook=_unique_json_object,
        parse_constant=_reject_json_constant,
    )
    if not isinstance(value, dict):
        raise ValueError("top-level JSON value is not an object")
    return value

CONSTITUTION_FIELDS = set((
    "schema id productId identity domainModel purpose successDefinition kernel "
    "hostAdapterStandard learnedFailureStandards qualityInvariants humanAuthority "
    "productBoundary resourceStewardship evidenceBoundary evolutionPolicy authority"
).split())
PROGRAM_FIELDS = set((
    "schema id productId release distributionVersion historicalRelease releaseIntent constitution acceptance maintenancePlan "
    "status inputEvidence increment releaseProcedure goalModePrompt hostProjections "
    "complexityBudget processLossControl"
).split())
ACCEPTANCE_FIELDS = set((
    "schema id productId release distributionVersion historicalRelease constitution program canonicalGoalObjectiveSha256 "
    "completionExpression evidenceLanes representativeBehaviorPolicy criteria "
    "candidateVerification releaseAuthorization publicRelease claimCeiling"
).split())
_GIT_CAPTURE_LIMIT = 262_144


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


def _bounded_git_bytes(root, arguments, limit=_GIT_CAPTURE_LIMIT):
    with tempfile.TemporaryFile() as output:
        process = subprocess.Popen(
            ["git", "-C", str(root), *arguments], stdout=output,
            stderr=subprocess.DEVNULL,
        )
        try:
            deadline = time.monotonic() + 10
            while process.poll() is None:
                if (os.fstat(output.fileno()).st_size > limit
                        or time.monotonic() >= deadline):
                    raise subprocess.SubprocessError("bounded Git capture failed")
                time.sleep(.01)
            if process.returncode or os.fstat(output.fileno()).st_size > limit:
                raise subprocess.SubprocessError("bounded Git capture failed")
        except BaseException:
            if process.poll() is None:
                process.kill()
            process.wait()
            raise
        output.seek(0)
        return output.read(limit + 1)


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
        "resourceStewardship": (
            ("resourceKinds", "lifecycle"),
            ("role", "nativeRule", "automaticActionRule", "unknownOwnershipRule", "diagnosticRule"),
        ),
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


_SCAN_LIMIT = 1_000_000
_LITERAL_PART_LIMIT = 4_096
_PYTHON_AST_NODE_LIMIT = 100_000


class _IdentityScanUnknown(ValueError):
    pass


def _folded_visible_text(value):
    return normalize("NFKC", value).casefold()


def _identity_word(value):
    return re.compile(
        rf"(?<!\w){re.escape(normalize('NFKC', value).casefold())}(?!\w)"
    )


def _identity_token(value):
    folded = normalize("NFKC", value).casefold()
    boundary = r"[\w-]" if re.fullmatch(
        r"[a-z0-9]+(?:-[a-z0-9]+)+", folded
    ) else r"\w"
    return re.compile(
        rf"(?<!{boundary}){re.escape(folded)}(?!{boundary})"
    )


def _python_ref(source, module, exact_tokens=()):
    if len(source) > _SCAN_LIMIT:
        raise _IdentityScanUnknown("Python identity surface exceeds scan budget")
    target = _identity_word(module)
    exact_matchers = tuple(_identity_token(token) for token in exact_tokens)

    def mentions(value):
        folded = normalize("NFKC", value).casefold()
        return bool(
            target.search(folded)
            or any(matcher.search(folded) for matcher in exact_matchers)
        )

    def text_value(value):
        if isinstance(value, str):
            return value
        if isinstance(value, bytes):
            return value.decode("utf-8", errors="ignore")
        return None

    try:
        tree = ast.parse(source, feature_version=(3, 10))
    except (MemoryError, RecursionError, SyntaxError, TypeError, ValueError) as exc:
        raise _IdentityScanUnknown(
            "Python source is outside the shared 3.10 grammar"
        ) from exc

    pending, nodes = [tree], []
    while pending:
        if len(nodes) >= _PYTHON_AST_NODE_LIMIT:
            raise _IdentityScanUnknown("Python AST exceeds scan budget")
        current = pending.pop()
        nodes.append(current)
        pending.extend(ast.iter_child_nodes(current))

        for _field, value in ast.iter_fields(current):
            candidates = value if isinstance(value, (list, tuple)) else (value,)
            for candidate in candidates:
                visible = text_value(candidate)
                if visible is not None and mentions(visible):
                    return True

    static = {}
    for current in reversed(nodes):
        if isinstance(current, ast.Constant) and isinstance(
            current.value, (str, bytes)
        ):
            static[id(current)] = (type(current.value), 1, len(current.value))
            continue
        if not (
            isinstance(current, ast.BinOp) and isinstance(current.op, ast.Add)
        ):
            continue
        left = static.get(id(current.left))
        right = static.get(id(current.right))
        if left is None or right is None or left[0] is not right[0]:
            continue
        parts = left[1] + right[1]
        length = left[2] + right[2]
        if parts > _LITERAL_PART_LIMIT or length > _SCAN_LIMIT:
            raise _IdentityScanUnknown(
                "Python literal expression exceeds scan budget"
            )
        static[id(current)] = (left[0], parts, length)

    nested_static_adds = {
        id(child)
        for current in nodes
        if id(current) in static
        and isinstance(current, ast.BinOp)
        and isinstance(current.op, ast.Add)
        for child in (current.left, current.right)
        if id(child) in static
        and isinstance(child, ast.BinOp)
        and isinstance(child.op, ast.Add)
    }
    for current in nodes:
        if not (
            id(current) in static
            and isinstance(current, ast.BinOp)
            and isinstance(current.op, ast.Add)
            and id(current) not in nested_static_adds
        ):
            continue
        leaves, pending = [], [current]
        while pending:
            item = pending.pop()
            if isinstance(item, ast.BinOp) and id(item) in static:
                pending.extend((item.right, item.left))
            else:
                leaves.append(item.value)
        value = ("" if static[id(current)][0] is str else b"").join(leaves)
        visible = text_value(value)
        if visible is not None and mentions(visible):
            return True
    return False


def _repository_text(source):
    if source.startswith((b"\xff\xfe\x00\x00", b"\x00\x00\xfe\xff")):
        return source.decode("utf-32")
    if source.startswith((b"\xff\xfe", b"\xfe\xff")):
        return source.decode("utf-16")
    if source.startswith(b"\xef\xbb\xbf"):
        return source.decode("utf-8-sig")
    if b"\0" in source:
        raise UnicodeError("unclassified NUL-bearing content")
    return source.decode("utf-8")


def _python_source_text(source):
    encoding, _ = tokenize.detect_encoding(io.BytesIO(source).readline)
    return source.decode(encoding)


def _bounded_regular_bytes(path):
    try:
        before = path.lstat()
    except OSError:
        return None, "unreadable"
    if not stat.S_ISREG(before.st_mode):
        return None, "not-regular"
    if before.st_size > _SCAN_LIMIT:
        return None, "oversized"

    descriptor = None
    flags = os.O_RDONLY | getattr(os, "O_BINARY", 0)
    flags |= getattr(os, "O_NONBLOCK", 0) | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(path, flags)
        opened = os.fstat(descriptor)
        state = lambda value: (value.st_size, value.st_mtime_ns, value.st_ctime_ns)
        if not stat.S_ISREG(opened.st_mode):
            return None, "not-regular"
        if not os.path.samestat(before, opened):
            return None, "unreadable"
        if opened.st_size > _SCAN_LIMIT:
            return None, "oversized"
        chunks, remaining = [], _SCAN_LIMIT + 1
        while remaining:
            chunk = os.read(descriptor, min(65_536, remaining))
            if not chunk:
                break
            chunks.append(chunk)
            remaining -= len(chunk)
        source = b"".join(chunks)
        after, current = os.fstat(descriptor), path.lstat()
        if (
            not os.path.samestat(after, current)
            or state(opened) != state(after)
            or state(before) != state(current)
        ):
            return None, "unreadable"
    except (MemoryError, OSError):
        return None, "unreadable"
    finally:
        if descriptor is not None:
            os.close(descriptor)
    if len(source) > _SCAN_LIMIT:
        return None, "oversized"
    return source, None


def active_tree_errors(
    root,
    locators,
    historical_revision,
    historical_reference_locators=(),
    digest_bound_binary_assets=None,
):
    locators = list(locators)
    locator_set = set(locators)
    binary_assets = {}
    if digest_bound_binary_assets is None:
        digest_bound_binary_assets = {}
    if not isinstance(digest_bound_binary_assets, dict):
        errors = ["digest-bound binary assets must be an object"]
    else:
        errors = []
        for locator, digest in digest_bound_binary_assets.items():
            relative = Path(locator) if isinstance(locator, str) else None
            if (
                relative is None or "\\" in locator or relative.is_absolute()
                or ".." in relative.parts or relative.suffix.casefold() != ".png"
                or not isinstance(digest, str)
                or re.fullmatch(r"[0-9a-f]{64}", digest) is None
            ):
                errors.append("digest-bound binary asset declaration is invalid")
            elif locator not in locator_set:
                errors.append(f"digest-bound binary asset is not tracked: {locator}")
            else:
                binary_assets[locator] = digest
    references = {
        locator for locator in historical_reference_locators
        if isinstance(locator, str)
        and not Path(locator).is_absolute()
        and Path(locator).parts[:2] == ("research", "reviews")
        and ".." not in Path(locator).parts
        and Path(locator).suffix.casefold() == ".md"
    }
    symlinks = {locator for locator in locators if (root / locator).is_symlink()}
    errors.extend(
        f"symbolic link is not admitted in active tree: {locator}"
        for locator in symlinks
    )
    try:
        if not isinstance(historical_revision, str) or not re.fullmatch(
            r"[0-9a-f]{40}", historical_revision
        ):
            raise ValueError
        history = [
            _bounded_git_bytes(
                root, ("show", f"{historical_revision}:{locator}"), _SCAN_LIMIT
            ).decode("utf-8")
            for locator in ("product/constitution.json", "README.md")
        ]
        old, readme = _strict_json_object(history[0]), history[1]
        command = old.get("authority", {}).get("executableVerifier", "")
        product_id = old.get("productId")
        title = next(
            (line[2:] for line in readme.splitlines() if line.startswith("# ")), None
        )
        module = command.split()[3] if command.startswith("python -B -m ") else None
        if not all(_nonempty_string(value) for value in (product_id, title, module)):
            raise ValueError
    except (OSError, ValueError, json.JSONDecodeError, subprocess.SubprocessError):
        return sorted(errors + ["historical identity boundary is unavailable"])

    exact_tokens = tuple(
        normalize("NFKC", value).casefold() for value in (product_id, title)
    )
    exact_matchers = tuple(_identity_token(token) for token in exact_tokens)
    module_token = _identity_word(module)
    for locator in locators:
        if locator in symlinks:
            continue
        locator_text = _folded_visible_text(locator)
        locator_has_identity = (
            any(matcher.search(locator_text) for matcher in exact_matchers)
            or module_token.search(locator_text)
        )
        source, read_state = _bounded_regular_bytes(root / locator)
        if read_state == "unreadable":
            errors.append(f"active tree file is unreadable: {locator}")
            continue
        if read_state == "not-regular":
            errors.append(f"active tree path is not a regular file: {locator}")
            continue
        if read_state == "oversized":
            errors.append(f"active tree identity scan is indeterminate: {locator}")
            continue

        if locator_has_identity:
            errors.append(f"superseded identity remains in active tree: {locator}")
            continue
        if locator in binary_assets:
            if (
                not source.startswith(b"\x89PNG\r\n\x1a\n")
                or sha256(source).hexdigest() != binary_assets[locator]
            ):
                errors.append(f"digest-bound binary asset does not match: {locator}")
            continue

        suffix = Path(locator).suffix.casefold()
        is_python = suffix in {".py", ".pyi", ".pyw"}
        try:
            text = (
                _python_source_text(source)
                if is_python
                else _repository_text(source)
            )
        except (LookupError, SyntaxError, UnicodeError):
            errors.append(f"active tree file is undecodable: {locator}")
            continue

        if locator in references:
            continue

        folded_text = _folded_visible_text(text)
        try:
            if is_python:
                identity_present = _python_ref(
                    text, module, exact_tokens
                )
            else:
                identity_present = (
                    any(matcher.search(folded_text) for matcher in exact_matchers)
                    or bool(module_token.search(folded_text))
                )
        except _IdentityScanUnknown:
            errors.append(f"active tree identity scan is indeterminate: {locator}")
            continue
        if identity_present:
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
        source, read_state = _bounded_regular_bytes(test_file)
        if read_state is not None:
            raise OSError(read_state)
        tree = ast.parse(source.decode("utf-8"))
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
        or minimum_test_count != len(methods)
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
    historical = program.get("historicalRelease")
    historical_fields = {
        "releaseLine", "releasedTags", "unreleasedCheckpoint",
        "supersededDevelopmentDistributions", "authority", "rule",
    }
    released_tags = historical.get("releasedTags") if isinstance(historical, dict) else None
    superseded_development = (
        historical.get("supersededDevelopmentDistributions")
        if isinstance(historical, dict) else None
    )
    historical_valid = (
        isinstance(historical, dict)
        and set(historical) == historical_fields
        and acceptance.get("historicalRelease") == historical
        and all(_nonempty_string(historical.get(field)) for field in (
            "releaseLine", "unreleasedCheckpoint", "authority", "rule",
        ))
        and bool(_string_list(released_tags))
        and bool(_string_list(superseded_development))
        and historical.get("authority") == "docs/operations/HISTORY.md"
    )
    historical_release = historical.get("releaseLine") if historical_valid else None
    historical_match = (
        CONTRACT_RELEASE_RE.fullmatch(historical_release)
        if isinstance(historical_release, str) else None
    )
    checkpoint = historical.get("unreleasedCheckpoint") if historical_valid else None
    checkpoint_match = RELEASE_RE.fullmatch(checkpoint) if isinstance(checkpoint, str) else None
    if (
        not historical_valid or historical_match is None or checkpoint_match is None
        or released_tags[0] != historical_release
        or len(released_tags) != 2
        or RELEASE_RE.fullmatch(released_tags[1]) is None
        or any(RELEASE_RE.fullmatch(item) is None for item in superseded_development)
        or len(set(superseded_development)) != len(superseded_development)
        or not set(superseded_development).isdisjoint(
            {*released_tags, checkpoint}
        )
        or checkpoint_match.groups()[:2] != historical_match.groups()
        or RELEASE_RE.fullmatch(released_tags[1]).groups()[:2]
        != historical_match.groups()
    ):
        errors.append("program and acceptance historicalRelease provenance is invalid")

    contract_release = program.get("release")
    distribution = program.get("distributionVersion")
    selected_current_release = any(
        value is not None for value in (
            contract_release,
            distribution,
            acceptance.get("release"),
            acceptance.get("distributionVersion"),
        )
    )
    if program.get("status") != "ready" and not selected_current_release:
        contract_release = historical_release
        distribution = checkpoint
    else:
        if acceptance.get("release") != contract_release:
            errors.append("program and acceptance release must match")
        if acceptance.get("distributionVersion") != distribution:
            errors.append("acceptance.distributionVersion does not match program")
    contract_match = (
        CONTRACT_RELEASE_RE.fullmatch(contract_release)
        if isinstance(contract_release, str) else None
    )
    if contract_match is None:
        errors.append("program and acceptance release must name one v-prefixed contract line")
    match = RELEASE_RE.fullmatch(distribution) if isinstance(distribution, str) else None
    if match is None:
        return errors + ["program.distributionVersion must be a v-prefixed semantic version"]
    if isinstance(superseded_development, list) and distribution in superseded_development:
        errors.append(
            "program.distributionVersion reuses a superseded development distribution"
        )
    major, minor, _patch, prerelease, _build = match.groups()
    if contract_match is not None and (major, minor) != contract_match.groups():
        errors.append("program.distributionVersion must belong to the contract release line")
    package_version = distribution[1:]
    for index, projection in enumerate(program.get("hostProjections", [])):
        if isinstance(projection, dict) and projection.get("packageVersion") != package_version:
            errors.append(
                f"hostProjections[{index}].packageVersion does not match program.distributionVersion"
            )

    repository = identity.get("repository")
    parsed = urlsplit(repository) if isinstance(repository, str) else None
    parts = parsed.path.strip("/").split("/") if parsed is not None else []
    public = acceptance.get("publicRelease")
    if parsed is None or parsed.hostname != "github.com" or len(parts) != 2:
        return errors + ["release identity requires a canonical GitHub repository"]
    owner, repo = parts
    expected = {
        "tag": distribution,
        "releaseLocator": f"{repository.rstrip('/')}/releases/tag/{distribution}",
        "releaseApi": f"https://api.github.com/repos/{owner}/{repo}/releases/tags/{distribution}",
        "tagApi": f"https://api.github.com/repos/{owner}/{repo}/git/ref/tags/{distribution}",
        "releaseNotes": f"docs/releases/{distribution}.md",
    }
    if not isinstance(public, dict) or any(public.get(k) != v for k, v in expected.items()):
        errors.append("acceptance.publicRelease does not match release and repository identity")
    candidate = acceptance.get("candidateVerification", {})
    systems = candidate.get("systems")
    procedure = program.get("releaseProcedure", {})
    planned_systems = procedure.get("candidateVerificationSystems")
    required_system_ids = procedure.get("requiredCandidateVerificationSystemIds")
    expected_systems = (
        {system: planned_systems.get(system) for system in required_system_ids}
        if isinstance(planned_systems, dict)
        and _string_list(required_system_ids) is not None else None
    )
    if systems != expected_systems:
        errors.append("candidateVerification systems do not match release procedure")
    github_runs = f"{repository.rstrip('/')}/actions/runs/"
    if not isinstance(planned_systems, dict) or any(
        locator != github_runs
        for system, locator in planned_systems.items()
        if isinstance(system, str) and system.startswith("github-actions-")
    ):
        errors.append("candidate GitHub systems do not match repository identity")
    if isinstance(public, dict) and public.get("assetPolicy") != procedure.get(
        "assetPolicy"
    ):
        errors.append("public release asset policy does not match release procedure")
    if candidate.get("requiredSystemIds") != required_system_ids:
        errors.append("candidate required systems do not match release procedure")
    expected_prerelease = prerelease is not None
    expected_channel = "public-preview" if expected_prerelease else "full-release"
    if (
        not isinstance(public, dict)
        or public.get("prerelease") is not expected_prerelease
        or public.get("maturity") != expected_channel
        or procedure.get("releaseChannel") != expected_channel
    ):
        errors.append("publicRelease maturity does not match semantic version")
    return errors
