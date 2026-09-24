"""Task-time evidence admission, conditional on a trusted external observer.

The caller owns provenance, independence, bounded read-only observation and
review authenticity. A callable is a delegation seam, NOT proof of those facts.
No data can select code, commands, imports, credentials or remote access here.
"""

import copy
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path, PurePosixPath
import re
import subprocess

from .identity import _bounded_git_bytes, _strict_json_object
from .guardrails import clean_git_checkout
from .reviews import evaluate_review_bundle, review_policy_errors


SCHEMA = "yiyuan-accord-evidence-admission/v3"
IMPACT_SCHEMA = "yiyuan-accord-evidence-admission/v4"
CURRENT_SCHEMA = "yiyuan-accord-evidence-admission/v5"
_LIMIT = 1_000_000
_CLAIMS = {"function", "incremental-value", "package-lifecycle"}
_CASE_FIELDS = set("id scope host entry duties qualityAxes scenarios claims oracle oracleFiles conditions maxAgeSeconds expected".split())
_SCOPE_FIELDS = set("id host entry duties qualityAxes scenarios claims conditions rule".split())
_RECORD_FIELDS = set("case evaluatedRevision definitionSha256 packageSha256 observedAt conditions observerId sourceRef episodeId facts".split())
_ENTRY_PARENT_SCOPES = {
    "v33-openai-entry-applicability": "entryApplicability",
    "v33-admitted-entry-delivery": "entryDelivery",
    "v33-admitted-entry-lifecycle": "entryLifecycle",
}
_ENTRY_DISPOSITIONS = {"selected", "pending", "deferred", "inapplicable"}
_TRUST = ("Conditional on the caller's authenticated, independent, bounded read-only observer "
          "and review provenance; callable shape and this verifier do not authenticate external facts.")
_CURRENT_REVIEW_FILES = {"docs/operations/ACCEPTANCE-v3.3.md", "docs/operations/PLAN-v3.3.md"}
_CODEX_CACHE_VERSION = re.compile(
    r"^(?P<base>[0-9]+\.[0-9]+\.[0-9]+(?:-[0-9A-Za-z.-]+)?)(?:\+codex\.[0-9]{14})$"
)
_PACKAGE_TREE_FILES = 256
_PACKAGE_BLOB_BYTES = 1_048_576
_PACKAGE_TREE_BYTES = 4_194_304
_PACKAGE_BATCH_CAPTURE = _PACKAGE_TREE_BYTES + _PACKAGE_TREE_FILES * 128
_PACKAGE_ASSESSMENT_CALLS = 64
_PACKAGE_ASSESSMENT_FILES = 4096
_PACKAGE_ASSESSMENT_BYTES = 67_108_864
_PROJECTION_FILE_FIELDS = {
    "legalFiles", "metadataFiles", "mechanismFiles", "referenceFiles", "supportingSkills",
}


class _CaseRejection(ValueError):
    """Only verifier-owned reason codes may cross the diagnostic boundary."""

    def __init__(self, *codes):
        super().__init__("evidence case rejected")
        self.codes = codes


def _json(value):
    text = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)
    if len(text.encode("utf-8")) > _LIMIT:
        raise ValueError("evidence size limit")
    return text


def _hash(value):
    return sha256(_json(value).encode("utf-8")).hexdigest()


def _text(value):
    return isinstance(value, str) and 0 < len(value.strip()) <= 4096


def _refs(value, known):
    return (isinstance(value, list) and all(isinstance(v, str) for v in value)
            and len(value) == len(set(value)) and set(value) <= known)


def _locator(value):
    return (_text(value) and not any(c in value for c in "\\:\0\n\r")
            and not value.startswith("/") and PurePosixPath(value).as_posix() == value
            and not {".", ".."} & set(PurePosixPath(value).parts))


def _projection_package_files(projection):
    files = {projection.get(key) for key in ("manifest", "contract", "skill")}
    for key in _PROJECTION_FILE_FIELDS:
        values = projection.get(key, [])
        if isinstance(values, list):
            files.update(values)
    return {value for value in files if isinstance(value, str)}


def _sparse_package_files(contract, case):
    """Return a valid v5 pure-function dependency set, otherwise None.

    This is an invalidation boundary, not proof that the declared files are a
    complete behavioral dependency graph; the episode and review retain that duty.
    """
    if "packageFiles" not in case:
        return None
    if contract["acceptance"]["admission"]["schema"] != CURRENT_SCHEMA:
        raise ValueError("package file dependencies require current admission")
    scopes = {row["id"]: row for row in contract["acceptance"]["admission"]["scopes"]}
    scope = scopes.get(case.get("scope"))
    files = case["packageFiles"]
    requirements = contract["acceptance"]["admission"].get("acceptanceRequirements", [])
    a08_function = set(next((row["requiredCoverage"].get("function", []) for row in requirements
                             if row.get("id") == "A08"), []))
    projections = [row for row in contract["delivery"]["hostProjections"]
                   if row.get("id") == case.get("host")]
    if (len(projections) != 1 or scope is None or set(case.get("claims", [])) != {"function"}
            or set(scope.get("claims", [])) != {"function"} or "subjectEntries" in case
            or case.get("scope") in _ENTRY_PARENT_SCOPES or case.get("scope") in a08_function
            or not isinstance(files, list) or not files or len(files) != len(set(files))
            or any(not _locator(value) for value in files)):
        raise ValueError("package file dependencies require one pure function entry")
    projection = projections[0]
    manifest = projection.get("manifest")
    if not isinstance(manifest, str):
        raise ValueError("package manifest is unavailable")
    package = Path(manifest).parents[1].as_posix()
    declared = _projection_package_files(projection)
    required = {manifest, projection.get("contract"), projection.get("skill")}
    if (not required <= set(files) or not set(files) <= declared
            or any(not value.startswith(package + "/") for value in files)):
        raise ValueError("package file dependencies must include the host activation contract")
    return sorted(files)


def _entry_selection(policy, entries):
    """Validate and return the current v5 multi-entry parent selection."""
    scopes = {row["id"]: row for row in policy["scopes"] if isinstance(row, dict) and _text(row.get("id"))}
    present = set(scopes) & set(_ENTRY_PARENT_SCOPES)
    if not present:
        return None
    if present != set(_ENTRY_PARENT_SCOPES):
        raise ValueError("entry parent scopes must be declared together")
    applicability = scopes["v33-openai-entry-applicability"]
    candidates = {key for key, host in entries.items() if host == applicability["host"]}
    if set(applicability["subjectEntries"]) != candidates:
        raise ValueError("entry applicability must disposition every host entry")
    conditions = applicability["conditions"]
    dispositions = conditions.get("entryDispositions")
    final = conditions.get("selectionFinal")
    if (not isinstance(dispositions, dict) or set(dispositions) != candidates or type(final) is not bool
            or any(not isinstance(row, dict) or set(row) != {"status", "basis"}
                   or row.get("status") not in _ENTRY_DISPOSITIONS or not _text(row.get("basis"))
                   for row in dispositions.values())):
        raise ValueError("entry dispositions must bind every candidate, status and basis")
    selected = {key for key, row in dispositions.items() if row["status"] == "selected"}
    if not selected:
        raise ValueError("entry selection cannot be empty")
    for scope_id in ("v33-admitted-entry-delivery", "v33-admitted-entry-lifecycle"):
        scope = scopes[scope_id]
        if (scope["host"] != applicability["host"] or set(scope["subjectEntries"]) != selected
                or _json(scope["conditions"].get("entryDispositions")) != _json(dispositions)
                or scope["conditions"].get("selectionFinal") is not final):
            raise ValueError("entry parent scopes must share the selected entry set and conditions")
    cases = [row for row in policy["cases"] if isinstance(row, dict) and row.get("scope") in _ENTRY_PARENT_SCOPES]
    for case in cases:
        scope = scopes[case["scope"]]
        expected_key = _ENTRY_PARENT_SCOPES[case["scope"]]
        expected = case.get("expected", {}).get("effect", {}).get(expected_key)
        if (case.get("subjectEntries") != scope["subjectEntries"] or not isinstance(expected, dict)
                or set(expected) != set(case["subjectEntries"])
                or any(not isinstance(value, dict) or not value for value in expected.values())):
            raise ValueError("entry parent case must bind per-entry expected effects")
    pending = any(row["status"] == "pending" for row in dispositions.values())
    return {"final": final and not pending, "scopeIds": set(_ENTRY_PARENT_SCOPES),
            "caseIds": {row["id"] for row in cases}, "selected": selected}


def admission_contract_errors(contract):
    """Check declarations, not empirical adequacy of oracles or coverage claims."""
    policy = contract.get("acceptance", {}).get("admission")
    current = isinstance(policy, dict) and policy.get("schema") == CURRENT_SCHEMA
    fields = {"schema", "rule", "reviewPolicy", "reviewMaxAgeSeconds", "requiredCoverage", "scopes", "cases"}
    if current:
        fields |= {"requiredHosts", "acceptanceRequirements"}
    if (not isinstance(policy, dict) or set(policy) != fields
            or policy.get("schema") not in {SCHEMA, IMPACT_SCHEMA, CURRENT_SCHEMA} or not _text(policy.get("rule"))
            or type(policy.get("reviewMaxAgeSeconds")) is not int or policy["reviewMaxAgeSeconds"] <= 0
            or any(not isinstance(policy.get(k), list) or len(policy[k]) > 128 for k in ("scopes", "cases"))):
        return ["current evidence admission policy is missing or invalid"]
    if errors := review_policy_errors(policy["reviewPolicy"]):
        return errors
    try:
        _json(policy)
        required = policy["requiredCoverage"]
        impact_policy = policy["schema"] in {IMPACT_SCHEMA, CURRENT_SCHEMA}
        claims = _CLAIMS | ({"impact-assessment"} if impact_policy else set())
        if (not isinstance(required, dict) or set(required) != claims
                or any(not isinstance(ids, list) or not (0 if impact_policy and claim == "incremental-value" else 1) <= len(ids) <= 128
                       or not all(_text(v) for v in ids) or len(ids) != len(set(ids))
                       for claim, ids in required.items())):
            return ["qualification claims must prebind required scope IDs; only v4 incremental value may be undeclared"]
        sets = {
            "duties": {v["id"] for v in contract["acceptance"]["duties"]},
            "qualityAxes": {v["id"] for v in contract["systemOptimization"]["qualityAxes"]},
            "scenarios": {v["id"] for v in contract["environmentControl"]["adaptationScenarios"]},
            "claims": claims,
        }
        entries = {v["id"]: v["host"] for v in contract["capabilityMap"]["entrySurfaces"]["rows"]}
        hosts = {v["id"] for v in contract["delivery"]["hostProjections"]}
        if current:
            if (contract.get("schema") != "yiyuan-accord-development/v5"
                    or contract["acceptance"].get("currentQualification") != "current-v3.3-policy-bound"
                    or not _refs(policy["requiredHosts"], hosts) or not policy["requiredHosts"]):
                return ["current admission must bind the successor and its required delivery hosts"]
            requirements = policy["acceptanceRequirements"]
            if (not isinstance(requirements, list) or len(requirements) != 8
                    or any(not isinstance(r, dict) or set(r) != {"id", "requiredCoverage"} for r in requirements)
                    or {r["id"] for r in requirements} != {f"A{i:02}" for i in range(1, 9)}):
                return ["current admission must map A01 through A08 exactly once"]
            mapped = {claim: set() for claim in claims}
            for row in requirements:
                coverage = row["requiredCoverage"]
                if (not isinstance(coverage, dict) or not coverage or not set(coverage) <= claims
                        or any(not _refs(ids, set(required[claim])) or not ids for claim, ids in coverage.items())):
                    return ["current acceptance requirements must bind declared nonempty claim scopes"]
                for claim, ids in coverage.items():
                    mapped[claim].update(ids)
            if any(mapped[claim] != set(ids) for claim, ids in required.items()):
                return ["current acceptance mappings and required claim coverage differ"]
        scopes = {}
        for scope in policy["scopes"]:
            scope_id = scope.get("id") if isinstance(scope, dict) else None
            fields = _SCOPE_FIELDS | ({"subjectEntries"} if current and scope_id in _ENTRY_PARENT_SCOPES else set())
            if (not isinstance(scope, dict) or set(scope) != fields
                    or not _text(scope_id) or scope_id in scopes
                    or not isinstance(scope.get("host"), str) or scope["host"] not in hosts
                    or not isinstance(scope.get("entry"), str) or entries.get(scope["entry"]) != scope["host"]
                    or current and scope_id in _ENTRY_PARENT_SCOPES
                    and (not _refs(scope.get("subjectEntries"), set(entries)) or not scope["subjectEntries"]
                         or any(entries[key] != scope["host"] for key in scope["subjectEntries"]))
                    or any(not _refs(scope.get(k), values) for k, values in sets.items())
                    or not scope["duties"] or not scope["qualityAxes"] or not scope["claims"]
                    or not _text(scope.get("rule"))
                    or not isinstance(scope.get("conditions"), dict) or not scope["conditions"]
                    or any(v is None for v in scope["conditions"].values())):
                return ["evidence scope must bind its entry, relevant environment axes and required coverage"]
            scopes[scope["id"]] = scope
        if current and any(scope["host"] not in policy["requiredHosts"] for scope in scopes.values()):
            return ["current scopes cannot silently activate a deferred delivery host"]
        if impact_policy and {key for key, scope in scopes.items() if "incremental-value" in scope["claims"]} != set(required["incremental-value"]):
            return ["every active incremental-value claim must be required; undeclared claims belong in history"]
        ids = set()
        for case in policy["cases"]:
            parent = case.get("scope") if isinstance(case, dict) else None
            fields = (_CASE_FIELDS
                      | ({"subjectEntries"} if current and parent in _ENTRY_PARENT_SCOPES else set())
                      | ({"packageFiles"} if current and isinstance(case, dict)
                         and "packageFiles" in case else set()))
            if (not isinstance(case, dict) or set(case) != fields
                    or not _text(case.get("id")) or case["id"] in ids
                    or not isinstance(case.get("host"), str) or case["host"] not in hosts
                    or not isinstance(case.get("entry"), str) or entries.get(case["entry"]) != case["host"]
                    or current and parent in _ENTRY_PARENT_SCOPES
                    and (not _refs(case.get("subjectEntries"), set(entries)) or not case["subjectEntries"]
                         or any(entries[key] != case["host"] for key in case["subjectEntries"]))
                    or any(not _refs(case.get(k), values) for k, values in sets.items())
                    or not case["duties"] or not case["qualityAxes"] or not case["claims"]
                    or not _text(case.get("oracle"))
                    or not isinstance(case.get("oracleFiles"), list)
                    or any(not _locator(v) for v in case["oracleFiles"])
                    or len(case["oracleFiles"]) != len(set(case["oracleFiles"]))
                    or type(case.get("maxAgeSeconds")) is not int or case["maxAgeSeconds"] <= 0
                    or not isinstance(case.get("conditions"), dict) or not case["conditions"]
                    or any(v is None for v in case["conditions"].values())
                    or not isinstance(case.get("expected"), dict)
                    or not {"effect", "authority", "poststate", "cleanup"} <= case["expected"].keys()
                    or any(not isinstance(v, dict) or not v for v in case["expected"].values())
                    or (set(case["claims"]) & {"incremental-value", "impact-assessment"} and "comparison" not in case["expected"])):
                return ["evidence case must bind its applicable need, entry, oracle, conditions and post-state"]
            ids.add(case["id"])
            if current and not _CURRENT_REVIEW_FILES <= set(case["oracleFiles"]):
                return ["current cases must bind the acceptance document and its consensus/criteria source as oracle dependencies"]
            scope = scopes.get(case.get("scope"))
            if (scope is None or any(case[k] != scope[k] for k in ("host", "entry"))
                    or current and parent in _ENTRY_PARENT_SCOPES
                    and case["subjectEntries"] != scope["subjectEntries"]
                    or any(not set(case[k]) <= set(scope[k]) for k in sets)
                    or any(k not in case["conditions"] or _json(case["conditions"][k]) != _json(v)
                           for k, v in scope["conditions"].items())):
                return ["evidence case differs from its declared claim scope"]
            if "packageFiles" in case:
                _sparse_package_files(contract, case)
        try:
            _entry_selection(policy, entries) if current else None
        except ValueError as error:
            return [str(error)]
    except (KeyError, TypeError, ValueError, RecursionError):
        return ["evidence admission dependencies or bounded JSON are invalid"]
    return []


def _definition(contract, case):
    def selected(rows, ids):
        return sorted((v for v in rows if v["id"] in ids), key=lambda v: v["id"])
    definition = {
        "schema": contract["acceptance"]["admission"]["schema"], "case": {**case, **{k: sorted(case[k]) for k in
            ("duties", "qualityAxes", "scenarios", "claims", "oracleFiles", "packageFiles") if k in case}},
        "shared": {k: contract[k] for k in ("schema", "productId", "predecessorSnapshot", "authority",
                   "baselineRole", "cycle", "source", "applicability", "implementation",
                   "supportingPrinciples", "changePolicy")},
        "admission": {k: v for k, v in contract["acceptance"]["admission"].items() if k not in {"scopes", "cases"}},
        "scope": selected(contract["acceptance"]["admission"]["scopes"], [case["scope"]]),
        "delivery": {k: v for k, v in contract["delivery"].items() if k != "hostProjections"},
        "projection": selected(contract["delivery"]["hostProjections"], [case["host"]]),
        "acceptance": {k: v for k, v in contract["acceptance"].items()
                       if k not in {"admission", "duties", "retiredDuties"}},
        "duties": selected(contract["acceptance"]["duties"], case["duties"]),
        "quality": selected(contract["systemOptimization"]["qualityAxes"], case["qualityAxes"]),
        "qualityRule": {k: contract["systemOptimization"][k] for k in ("aggregation", "rule")},
        "scenarios": selected(contract["environmentControl"]["adaptationScenarios"], case["scenarios"]),
        "environment": {k: v for k, v in contract["environmentControl"].items() if k != "adaptationScenarios"},
        "entry": selected(contract["capabilityMap"]["entrySurfaces"]["rows"], [case["entry"]]),
        "entryRule": contract["capabilityMap"]["entrySurfaces"]["rule"],
    }
    if "subjectEntries" in case:
        definition["subjectEntries"] = selected(
            contract["capabilityMap"]["entrySurfaces"]["rows"], case["subjectEntries"])
    return _hash(definition)


def _reuse_definition(contract, case):
    """Compare meaning without changing the original stored-record digest."""
    projections = [v for v in contract["delivery"]["hostProjections"] if v["id"] == case["host"]]
    if (len(projections) != 1 or type(projections[0].get("maxSkillBytes")) is not int
            or projections[0]["maxSkillBytes"] <= 0):
        raise ValueError("invalid Skill budget")
    projection = {k: v for k, v in projections[0].items() if k != "maxSkillBytes"}
    # Keep stored-record identity intact. Progress descriptions are not criteria;
    # the current subject still needs a fresh independent review and recheck.
    current = copy.deepcopy(contract)
    if _sparse_package_files(contract, case) is not None:
        # The selected package files, not an unrelated package change or the
        # development cache stamp, determine whether this execution still applies.
        current["delivery"]["version"] = _normalized_cache_version(current["delivery"]["version"])
        projection["packageVersion"] = _normalized_cache_version(projection["packageVersion"])
        projection.pop("packageSha256", None)
    current["delivery"]["hostProjections"] = [projection]
    if current["acceptance"]["admission"]["schema"] == CURRENT_SCHEMA:
        for row in current["acceptance"]["duties"]:
            row.pop("assessment", None)
            row.pop("evidence", None)
        for row in current["systemOptimization"]["qualityAxes"]:
            row.pop("assessment", None)
        for row in current["capabilityMap"]["entrySurfaces"]["rows"]:
            row.pop("observation", None)
            row.pop("currentEffect", None)
    # Static validation still enforces the actual Skill byte limit. All case,
    # scope, package, authority and substantive criteria remain bound.
    return _definition(current, case)


def _git(root, *args):
    return _bounded_git_bytes(root, ("--no-replace-objects", "--literal-pathspecs", *args), _LIMIT)


def _batch_blobs(root, requests):
    encoded = [request.encode("utf-8") for request in requests]
    capture = _bounded_git_bytes(
        root, ("--no-replace-objects", "cat-file", "--batch"), _PACKAGE_BATCH_CAPTURE,
        b"".join(request + b"\n" for request in encoded),
    )
    blobs, offset, total = [], 0, 0
    for _request in encoded:
        end = capture.find(b"\n", offset)
        if end < 0:
            raise ValueError("invalid package batch header")
        fields = capture[offset:end].split()
        offset = end + 1
        if len(fields) != 3 or fields[1] != b"blob":
            raise ValueError("invalid package batch object")
        size = int(fields[2])
        if size < 0 or size > _PACKAGE_BLOB_BYTES or total + size > _PACKAGE_TREE_BYTES:
            raise ValueError("package batch byte bound exceeded")
        content = capture[offset:offset + size]
        offset += size + 1
        if len(content) != size or capture[offset - 1:offset] != b"\n":
            raise ValueError("invalid package batch body")
        total += size
        blobs.append(content)
    if offset != len(capture):
        raise ValueError("unexpected package batch suffix")
    return blobs, total


def _revision_package_snapshot(root, revision, package, budget):
    """Read one complete revision package under per-tree and shared assessment bounds."""
    if budget["calls"] + 1 > _PACKAGE_ASSESSMENT_CALLS:
        raise ValueError("package assessment call bound exceeded")
    budget["calls"] += 1
    listing = _git(root, "ls-tree", "-r", "-z", revision, "--", package)
    locators = []
    for row in (item for item in listing.split(b"\0") if item):
        metadata, separator, raw_locator = row.partition(b"\t")
        fields = metadata.split()
        locator = raw_locator.decode("utf-8")
        if (not separator or len(fields) != 3 or fields[0] not in {b"100644", b"100755"}
                or fields[1] != b"blob" or not locator.startswith(package + "/")):
            raise ValueError("revision package tree is invalid")
        locators.append(locator)
    if (not locators or len(locators) != len(set(locators))
            or len(locators) > _PACKAGE_TREE_FILES
            or budget["files"] + len(locators) > _PACKAGE_ASSESSMENT_FILES):
        raise ValueError("revision package file set is invalid")
    if (budget["calls"] + 1 > _PACKAGE_ASSESSMENT_CALLS
            or budget["bytes"] + _PACKAGE_TREE_BYTES > _PACKAGE_ASSESSMENT_BYTES):
        raise ValueError("package assessment batch bound exceeded")
    budget["calls"] += 1
    budget["files"] += len(locators)
    budget["bytes"] += _PACKAGE_TREE_BYTES
    blobs, total = _batch_blobs(root, [f"{revision}:{locator}" for locator in sorted(locators)])
    if total > _PACKAGE_TREE_BYTES:
        raise ValueError("package assessment byte bound exceeded")
    budget["bytes"] -= _PACKAGE_TREE_BYTES - total
    digest = sha256()
    files = {}
    for locator, content in zip(sorted(locators), blobs, strict=True):
        digest.update(locator.encode("utf-8"))
        digest.update(b"\0")
        digest.update(sha256(content).digest())
        files[locator] = content
    return {"sha256": digest.hexdigest(), "files": files}


def _normalized_cache_version(value):
    if not isinstance(value, str):
        raise ValueError("package version is unavailable")
    match = _CODEX_CACHE_VERSION.fullmatch(value)
    return match.group("base") if match else value


def _normalized_manifest(raw):
    value = _strict_json_object(raw.decode("utf-8"))
    value["version"] = _normalized_cache_version(value.get("version"))
    return _json(value)


def _selected_package_files_unchanged(original, current, files, manifest):
    for locator in files:
        if locator not in original["files"] or locator not in current["files"]:
            raise ValueError("selected package dependency is unavailable")
        original_bytes = original["files"][locator]
        current_bytes = current["files"][locator]
        if locator == manifest:
            if _normalized_manifest(original_bytes) != _normalized_manifest(current_bytes):
                return False
        elif original_bytes != current_bytes:
            return False
    return True


def evidence_subject(root):
    """Bind before static reads; resolve the tree from that commit, not another HEAD."""
    revision = _git(root, "rev-parse", "--verify", "HEAD^{commit}").decode("ascii").strip()
    tree = _git(root, "rev-parse", "--verify", revision + "^{tree}").decode("ascii").strip()
    return {"revision": revision, "tree": tree}


def _fresh(value, seconds, now):
    try:
        at = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return at if at.utcoffset() is not None and 0 <= (now - at).total_seconds() <= seconds else None
    except (AttributeError, TypeError, ValueError):
        return None


def assess_development_evidence(root, contract, observer, review_bundle=None, *, subject=None):
    """Two bounded, caller-owned queries: observe checked sources, then recheck.

    Returned data may not choose an observer. The caller must independently
    establish record/review provenance and same-episode facet attribution.
    The observer must not mutate the subject and must own its execution deadline.
    No observer (including the CLI default) means no empirical admission.
    """
    report = {"scope": "caller-observed-development-candidate", "trustBoundary": _TRUST,
              "acceptedCases": [], "openCoverage": {}, "unboundCoverage": {}, "functionalCompletion": False,
              "incrementalValue": "unverified", "candidateEligible": False,
              "checkoutClean": None, "packageReuse": {}, "caseRejections": {}, "errors": []}

    def reject_case(key, *codes):
        reasons = report["caseRejections"].setdefault(key, [])
        reasons.extend(code for code in codes if code not in reasons)
    successor = contract.get("schema") == "yiyuan-accord-development/v5"
    if successor and contract.get("acceptance", {}).get("admission", {}).get("schema") != CURRENT_SCHEMA:
        # Retained v4 case definitions are regression inputs, not the new
        # ordinary-entry/continuity/resource acceptance for the successor.
        # Do not even dispatch an observer that could promote those old cases.
        report["scope"] = "current-v3.3-admission-not-yet-bound"
        report["unboundCoverage"] = {"currentAcceptance": "docs/operations/ACCEPTANCE-v3.3.md"}
        return report
    if successor:
        if errors := admission_contract_errors(contract):
            report["errors"] = errors
            return report
        report["scope"] = "current-v3.3-caller-observed-candidate"
    policy = contract["acceptance"]["admission"]
    cases = {v["id"]: v for v in policy["cases"]}
    scopes = {v["id"]: v for v in policy["scopes"]}
    entry_selection = (_entry_selection(policy, {row["id"]: row["host"]
                       for row in contract["capabilityMap"]["entrySurfaces"]["rows"]})
                       if policy["schema"] == CURRENT_SCHEMA else None)
    errors = report["errors"]
    case_errors = []
    hosts = {v["id"]: v for v in contract["delivery"]["hostProjections"]}
    required = {
        "duties": {v["id"] for v in contract["acceptance"]["duties"]},
        "qualityAxes": {v["id"] for v in contract["systemOptimization"]["qualityAxes"]},
        # The inventory names possible conditions; required scopes activate them.
        # Keep this axis so each scope still requires its selected case evidence.
        "scenarios": set(),
    }
    admitted, package_reuse = set(), {}
    if observer is not None:
        try:
            if not callable(observer):
                raise ValueError("caller-selected observer required")
            if not cases:
                raise ValueError("no bound current evidence cases")
            if subject is None or evidence_subject(root) != subject:
                raise ValueError("subject changed after static checks")
            checked = _strict_json_object(_git(root, "show", f"{subject['revision']}:product/development.json").decode("utf-8"))
            if _json(checked) != _json(contract):
                raise ValueError("static contract does not belong to the bound subject")
            _git(root, "diff", "--quiet", "--no-ext-diff", "--no-textconv", subject["revision"], "--")
            request = {"phase": "observe", "subject": subject, "cases": {
                key: {"case": case, "scope": scopes[case["scope"]], "definitionSha256": _definition(contract, case),
                      "packageSha256": hosts[case["host"]]["packageSha256"]}
                for key, case in cases.items()}}
            # Copy before invoking foreign code; never let it rewrite expected facts.
            data = _strict_json_object(_json(observer(copy.deepcopy(request))))
            if set(data) != {"records", "reviewBundle"} or not isinstance(data["records"], list):
                raise ValueError("invalid observation envelope")
            now = datetime.now(timezone.utc)
            prior, package_snapshots, seen = {}, {}, set()
            package_budget = {"calls": 0, "files": 0, "bytes": 0}
            for record in data["records"]:
                if (not isinstance(record, dict) or set(record) != _RECORD_FIELDS
                        or not isinstance(record.get("case"), str) or record["case"] not in cases):
                    errors.append("unknown or malformed evidence record")
                    continue
                key = record["case"]
                if key in seen:
                    admitted.discard(key)
                    reject_case(key, "duplicate-observation")
                    errors.append(f"{key}: duplicate or conflicting observations")
                    continue
                seen.add(key)
                case, bound = cases[key], request["cases"][key]
                try:
                    at = _fresh(record["observedAt"], float("inf"), now)
                    if at is None:
                        raise _CaseRejection("observation-time-invalid")
                    revision = record["evaluatedRevision"]
                    if not isinstance(revision, str) or re.fullmatch(r"[0-9a-f]{40}", revision) is None:
                        raise _CaseRejection("evaluated-revision-invalid")
                    _git(root, "merge-base", "--is-ancestor", revision, subject["revision"])
                    if revision not in prior:
                        original_contract = _strict_json_object(_git(root, "show", f"{revision}:product/development.json").decode("utf-8"))
                        if (original_contract.get("schema") != contract["schema"]
                                or admission_contract_errors(original_contract)):
                            raise _CaseRejection("evaluated-admission-invalid")
                        prior[revision] = original_contract
                    original = next((v for v in prior[revision]["acceptance"]["admission"]["cases"] if v["id"] == key), None)
                    if original is None:
                        raise _CaseRejection("case-not-prebound")
                    original_hosts = {v["id"]: v for v in prior[revision]["delivery"]["hostProjections"]}
                    original_host = original_hosts[original["host"]]
                    current_host = hosts[case["host"]]
                    original_package = Path(original_host["manifest"]).parents[1].as_posix()
                    current_package = Path(current_host["manifest"]).parents[1].as_posix()
                    original_hash_key = (revision, original_package)
                    current_hash_key = (subject["revision"], current_package)
                    if original_hash_key not in package_snapshots:
                        package_snapshots[original_hash_key] = _revision_package_snapshot(
                            root, revision, original_package, package_budget)
                    if current_hash_key not in package_snapshots:
                        package_snapshots[current_hash_key] = _revision_package_snapshot(
                            root, subject["revision"], current_package, package_budget)
                    original_snapshot = package_snapshots[original_hash_key]
                    current_snapshot = package_snapshots[current_hash_key]
                    checks = {
                        "record-definition": record["definitionSha256"] == _definition(prior[revision], original),
                        "reuse-definition": _reuse_definition(prior[revision], original) == _reuse_definition(contract, case),
                        "record-declared-package": record["packageSha256"] == original_host["packageSha256"],
                        "record-actual-package": record["packageSha256"] == original_snapshot["sha256"],
                        "current-actual-package": bound["packageSha256"] == current_snapshot["sha256"],
                    }
                    if not all(checks.values()):
                        raise _CaseRejection(*(f"{name}-mismatch" for name, valid in checks.items() if not valid))
                    package_files = _sparse_package_files(contract, case)
                    if package_files is None:
                        if record["packageSha256"] != bound["packageSha256"]:
                            raise _CaseRejection("complete-package-changed")
                    else:
                        if not _selected_package_files_unchanged(
                                original_snapshot, current_snapshot, package_files, current_host["manifest"]):
                            raise _CaseRejection("selected-package-dependency-changed")
                        if record["packageSha256"] != bound["packageSha256"]:
                            package_reuse[key] = {
                                "evaluatedRevision": revision,
                                "evaluatedPackageSha256": record["packageSha256"],
                                "currentRevision": subject["revision"],
                                "currentPackageSha256": bound["packageSha256"],
                                "packageFiles": package_files,
                                "claimLimit": "selected-files-unchanged-not-dependency-completeness",
                            }
                    # Current normative documents belong to the fresh candidate
                    # review. New prose alone does not require repeating execution;
                    # changed case/quality criteria still fail the definition check.
                    review_files = _CURRENT_REVIEW_FILES if policy["schema"] == CURRENT_SCHEMA else set()
                    execution_files = [path for path in case["oracleFiles"] if path not in review_files]
                    diff_files = execution_files if package_files is not None else [current_package, *execution_files]
                    # The bounded Git helper deliberately hides subprocess error
                    # details. Ask for bounded names so drift differs from I/O
                    # failure without exporting file names or exception text.
                    if _git(root, "diff", "--name-only", "-z", "--no-ext-diff", "--no-textconv", revision, "--", *diff_files):
                        raise _CaseRejection("execution-dependency-changed")
                    for path in case["oracleFiles"]:
                        _git(root, "cat-file", "blob", f"{revision}:{path}")
                        if path in review_files:
                            _git(root, "cat-file", "blob", f"{subject['revision']}:{path}")
                    committed = int(_git(root, "show", "-s", "--format=%ct", revision).strip())
                    if at.timestamp() < committed:
                        raise _CaseRejection("observation-predates-candidate")
                    if not all(_text(record[k]) for k in ("episodeId", "sourceRef", "observerId")):
                        raise _CaseRejection("provenance-missing")
                    facts = record["facts"]
                    if not isinstance(facts, dict) or set(facts) != set(case["expected"]):
                        raise _CaseRejection("facet-shape-invalid")
                    for actual in facts.values():
                        if (not isinstance(actual, dict) or set(actual) != {"episodeId", "value"}
                                or actual["episodeId"] != record["episodeId"]):
                            raise _CaseRejection("facet-episode-mismatch")
                    # Only attributable consequences can leave independent claims intact.
                    unmet = []
                    if _fresh(record["observedAt"], case["maxAgeSeconds"], now) is None:
                        unmet.append("observation-expired")
                    if _json(record["conditions"]) != _json(case["conditions"]):
                        unmet.append("execution-conditions-mismatch")
                    if any(_json(facts[k]["value"]) != _json(v) for k, v in case["expected"].items()):
                        unmet.append("consequence-mismatch")
                    if unmet:
                        reject_case(key, *unmet)
                        case_errors.append(f"{key}: freshness, conditions or consequence not admitted")
                    else:
                        admitted.add(key)
                except (OSError, subprocess.SubprocessError, KeyError, TypeError, ValueError, StopIteration) as error:
                    reject_case(key, *(error.codes if isinstance(error, _CaseRejection) else ("source-evidence-unavailable",)))
                    errors.append(f"{key}: source, identity, freshness, conditions or consequence not admitted")
            review = data["reviewBundle"]
            if review_bundle is not None and _json(review_bundle) != _json(review):
                errors.append("review input differs from the observer-checked bundle")
            review_result = evaluate_review_bundle(review, subject["revision"], subject["tree"],
                                                   policy=policy["reviewPolicy"])
            errors.extend("independent review: " + error for error in review_result["errors"])
            candidate_time = int(_git(root, "show", "-s", "--format=%ct", subject["revision"]).strip())
            if review_result["decision"] == "pass" and any(
                    (at := _fresh(v["reviewedAt"], contract["acceptance"]["admission"]["reviewMaxAgeSeconds"], now)) is None
                    or at.timestamp() < candidate_time
                    for v in review["reviews"]):
                errors.append("independent review predates its subject, is future-dated or expired")
            observation_hash = _hash(data)
            recheck = _strict_json_object(_json(observer(copy.deepcopy({
                **request, "phase": "recheck", "observationSha256": observation_hash,
            }))))
            if (set(recheck) != {"subject", "conditions", "observationSha256"}
                    or recheck["subject"] != subject or recheck["observationSha256"] != observation_hash
                    or not isinstance(recheck["conditions"], dict)):
                raise ValueError("invalid observer recheck")
            for key in list(admitted):
                if _json(recheck["conditions"].get(key)) != _json(cases[key]["conditions"]):
                    admitted.remove(key)
                    reject_case(key, "current-conditions-changed")
                    case_errors.append(f"{key}: current conditions changed or unavailable")
            if evidence_subject(root) != subject:
                raise ValueError("subject changed during observation")
            _git(root, "diff", "--quiet", "--no-ext-diff", "--no-textconv", subject["revision"], "--")
            report["checkoutClean"] = clean_git_checkout(root)
            if not report["checkoutClean"] or evidence_subject(root) != subject:
                raise ValueError("subject or checkout changed before final qualification")
            final_now = datetime.now(timezone.utc)
            for record in data["records"]:
                if isinstance(record, dict) and record.get("case") in admitted:
                    key = record["case"]
                    if _fresh(record["observedAt"], cases[key]["maxAgeSeconds"], final_now) is None:
                        admitted.remove(key)
                        reject_case(key, "observation-expired")
                        case_errors.append(f"{key}: observation expired before final qualification")
            if review_result["decision"] == "pass" and any(
                    _fresh(v["reviewedAt"], contract["acceptance"]["admission"]["reviewMaxAgeSeconds"], final_now) is None
                    for v in review["reviews"]):
                errors.append("independent review expired before final qualification")
        except Exception:
            # External exception text may contain private source data or credentials.
            errors.append("evidence observer unavailable, invalid or subject changed")
            admitted.clear()
    if entry_selection is not None and not entry_selection["final"]:
        for key in sorted(admitted & entry_selection["caseIds"]):
            admitted.remove(key)
            reject_case(key, "entry-selection-pending")
    if entry_selection is not None:
        report["entrySelection"] = {"final": entry_selection["final"],
                                    "selected": sorted(entry_selection["selected"])}
    report["acceptedCases"] = sorted(admitted)
    report["packageReuse"] = {key: package_reuse[key] for key in sorted(admitted & set(package_reuse))}
    bound = {claim: {key for key in ids if key in scopes and claim in scopes[key]["claims"]}
             for claim, ids in policy["requiredCoverage"].items()}
    report["unboundCoverage"] = {claim: sorted(set(ids) - bound[claim])
                                 for claim, ids in policy["requiredCoverage"].items()}
    completed = {claim: bool(bound[claim]) and not report["unboundCoverage"][claim] and not errors
                 for claim in bound}
    # A08 integration requires one complete episode, not a union of unrelated
    # successes. Case admission already checks all facets against its episode.
    joint_scopes = (set(next(r for r in policy["acceptanceRequirements"] if r["id"] == "A08")
                        ["requiredCoverage"].get("function", []))
                    if policy["schema"] == CURRENT_SCHEMA else set())
    if policy["schema"] == CURRENT_SCHEMA:
        report["unjoinedCoverage"] = {"function": []}
    report["productCoverage"] = {}
    required_hosts = policy["requiredHosts"] if policy["schema"] == CURRENT_SCHEMA else hosts
    for host in required_hosts:
        selected = [scopes[key] for key in set().union(*bound.values()) if scopes[key]["host"] == host]
        report["productCoverage"][host] = {
            k: sorted(values - {v for scope in selected for v in scope[k]}) for k, values in required.items()}
        for claim in ("function", "package-lifecycle") + (("impact-assessment",) if policy["schema"] in {IMPACT_SCHEMA, CURRENT_SCHEMA} else ()):
            completed[claim] &= any(scopes[key]["host"] == host for key in bound[claim])
    for scope_id, scope in scopes.items():
        row = {"host": scope["host"], "entry": scope["entry"],
               "conditions": copy.deepcopy(scope["conditions"]), "claims": {}}
        if "subjectEntries" in scope:
            row["subjectEntries"] = copy.deepcopy(scope["subjectEntries"])
        report["openCoverage"][scope_id] = row
        for claim in scope["claims"]:
            relevant = {key for key in cases if cases[key]["scope"] == scope_id and claim in cases[key]["claims"]}
            covered = {k: set() for k in required}
            for key in admitted & relevant:
                for field in covered:
                    covered[field].update(cases[key][field])
            missing = {k: sorted(set(scope[k]) - values) for k, values in covered.items()}
            row["claims"][claim] = missing
            if scope_id in bound[claim]:
                completed[claim] &= bool(relevant) and relevant <= admitted and not any(missing.values())
            if claim == "function" and scope_id in joint_scopes:
                if not any(all(set(scope[field]) <= set(cases[key][field]) for field in required)
                           for key in admitted & relevant):
                    report["unjoinedCoverage"][claim].append(scope_id)
                    completed[claim] = False
    report["functionalCompletion"] = completed["function"]
    report["incrementalValue"] = "supported-for-bound-cases" if completed["incremental-value"] else "unverified"
    report["impactAssessment"] = "complete-for-bound-scopes" if completed.get("impact-assessment") else "unverified"
    global_errors = bool(errors)
    errors.extend(case_errors)
    required_claims = {claim for claim, ids in policy["requiredCoverage"].items() if ids}
    report["candidateEligible"] = (not errors and all(completed[claim] for claim in required_claims) and len(admitted) == len(cases)
                                   and not any(v for row in report["productCoverage"].values() for v in row.values()))
    if policy["schema"] == CURRENT_SCHEMA:
        report["acceptanceRequirements"] = {}
        for requirement in policy["acceptanceRequirements"]:
            missing = {}
            for claim, ids in requirement["requiredCoverage"].items():
                missing[claim] = [scope_id for scope_id in ids if scope_id not in bound[claim]
                    or not (relevant := {key for key, case in cases.items()
                                         if case["scope"] == scope_id and claim in case["claims"]})
                    or not relevant <= admitted
                    or scope_id in report["unjoinedCoverage"].get(claim, [])
                    or any(report["openCoverage"][scope_id]["claims"][claim].values())]
            report["acceptanceRequirements"][requirement["id"]] = {
                "complete": not global_errors and not any(missing.values()), "missingScopes": missing}
        requirements = report["acceptanceRequirements"]
        requirements["A08"]["blockedBy"] = sorted(key for key, row in requirements.items()
                                                   if key != "A08" and not row["complete"])
        requirements["A08"]["complete"] &= not requirements["A08"]["blockedBy"]
        # Derived counts and coverage expose remaining work without adding a gate.
        required_pairs = {(claim, scope) for claim, ids in policy["requiredCoverage"].items() for scope in ids}
        missing_pairs = {(claim, scope) for row in requirements.values()
                         for claim, ids in row["missingScopes"].items() for scope in ids}
        defined_pairs = {(claim, scope) for claim, ids in bound.items() for scope in ids}
        verified_pairs = required_pairs - missing_pairs if not global_errors else set()
        report["progress"] = {
            "scope": "acceptance-evidence-coverage-not-effort-or-implementation-completion",
            "requirementsTotal": len(requirements),
            "requirementsComplete": sum(bool(row["complete"]) for row in requirements.values()),
            "coverageTotal": len(required_pairs),
            "coverageDefined": len(required_pairs & defined_pairs),
            "coverageVerified": len(verified_pairs),
            "coverageScorePercent": round(100 * len(verified_pairs) / len(required_pairs), 2) if required_pairs else None,
            "coverageUnbound": len(required_pairs - defined_pairs),
            "coverageDefinedButUnverified": len((required_pairs & defined_pairs) - verified_pairs),
            "casesDefined": len(cases),
            "casesAccepted": len(admitted),
        }
    return report
