"""Task-time evidence admission, conditional on a trusted external observer.

The caller owns provenance, independence, bounded read-only observation and
review authenticity. A callable is a delegation seam, NOT proof of those facts.
For v5, retained execution times remain historical; observe/recheck must freshly
verify applicable host, configuration, authority and continuing-state dependencies.
Missing current evidence is not an unchanged condition. maxAgeSeconds bounds this
observe-through-final-check window, not the age of an immutable, still-applicable result.
No data can select code, commands, imports, credentials or remote access here.
"""

import copy
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path, PurePosixPath
import re
import subprocess
from time import monotonic

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
_PARENT_CLAIMS = {"v33-admitted-entry-delivery": "function",
                  "v33-admitted-entry-lifecycle": "package-lifecycle",
                  "v33-system-integration": "function",
                  "v33-system-impact-assessment": "impact-assessment"}
_ENTRY_COVERAGE_SCOPE = "v33-codex-entry-coverage"
_HOST_LIFECYCLE_SCOPE = "v33-codex-lifecycle"
_SELECTED_SUBJECT_SCOPES = {_HOST_LIFECYCLE_SCOPE, "v33-system-integration"}
_ENTRY_COVERAGE_PREDICATES = {
    "discoveryDenominatorBound", "officialAndActualSourcesReconciled",
    "zeroUnexplainedOmissions", "capabilityDispositionsSupported",
    "necessaryCapabilityUseVerified", "authorityAndExitPathsAccounted",
    "unavailableAndSufficientNativeCounterexamplesPreserved", "changedUserOrHostStateReconciled",
}
_ENTRY_DISPOSITIONS = {"selected", "pending", "deferred", "inapplicable"}
_ENTRY_MODES = {
    "chatgpt-desktop": {"chat", "work-local", "work-cloud", "remote"},
    "chatgpt-mobile": {"chat", "work-cloud", "remote"},
    "chatgpt-web": {"chat", "work-cloud"},
}
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


def _within_limit_ceiling(actual, maximum):
    if isinstance(maximum, dict):
        return (bool(maximum) and isinstance(actual, dict) and actual.keys() == maximum.keys()
                and all(_within_limit_ceiling(actual[key], value) for key, value in maximum.items()))
    return type(actual) is int and type(maximum) is int and 0 < actual <= maximum


def _conditions_match(actual, required):
    # Only an explicit typed ceiling permits smaller budgets. Other conditions,
    # including legacy limits, still bind exactly; observed receipts bind the
    # actual case budget, not this parent ceiling.
    return all(key in actual and (
        _within_limit_ceiling(actual[key], value)
        if key == 'limits' and required.get('limitSemantics') == 'maximum'
        else _json(actual[key]) == _json(value)) for key, value in required.items())


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


def _entry_modes(dispositions, catalog=None):
    """Keep unresolved modes visible when selecting a mixed OpenAI entry.

    Earlier v5 policies with all mixed entries pending retain their original form.
    New scope-bound catalogs replace the historical default. Neither catalog
    proves host availability, user authority or functional acceptance.
    """
    if catalog is None:
        catalog = _ENTRY_MODES
    elif (not isinstance(catalog, dict)
          or set(catalog) != set(_ENTRY_MODES) & set(dispositions)
          or any(not isinstance(values, list) or not values
                 or any(not _text(value) for value in values)
                 or len(values) != len(set(values))
                 for values in catalog.values())):
        raise ValueError("entry mode catalog must bind the current mixed entry scope")
    if (not any("modes" in row for row in dispositions.values())
            and all(row["status"] == "pending" for key, row in dispositions.items() if key in catalog)):
        return {}
    modes = {}
    for key, row in dispositions.items():
        if key not in catalog:
            if "modes" in row:
                raise ValueError("entry modes require a declared catalog")
            continue
        values = row.get("modes")
        if (not isinstance(values, dict) or set(values) != set(catalog[key])
                or any(not isinstance(value, dict) or set(value) != {"status", "basis"}
                       or value.get("status") not in _ENTRY_DISPOSITIONS | {"auxiliary"}
                       or not _text(value.get("basis")) for value in values.values())):
            raise ValueError("mixed entry selection must disposition every known mode")
        selected = any(value["status"] == "selected" for value in values.values())
        pending = any(value["status"] == "pending" for value in values.values())
        if ((row["status"] == "selected") != selected
                or (not selected and (row["status"] == "pending") != pending)):
            raise ValueError("entry status must account for its selected and pending modes")
        modes[key] = values
    return modes


def _entry_mode_effects(expected, required_modes, *, strict=False):
    for key, required in required_modes.items():
        if not required and not strict:
            continue
        effects = expected[key].get("modes", {} if not required else None)
        predicates = {name: value for name, value in expected[key].items() if name != "modes"}
        if (not isinstance(effects, dict) or set(effects) != required
                or not predicates or any(not isinstance(value, dict)
                    or any(name not in value or _json(value[name]) != _json(predicate)
                           for name, predicate in predicates.items()) for value in effects.values())):
            raise ValueError("entry case must bind per-mode expected effects")


def _entry_selection(policy, entries, mode_catalog=None):
    """Validate and return the current v5 multi-entry parent selection."""
    scopes = {row["id"]: row for row in policy["scopes"] if isinstance(row, dict) and _text(row.get("id"))}
    present = set(scopes) & set(_ENTRY_PARENT_SCOPES)
    coverage_cases = [row for row in policy["cases"]
                      if isinstance(row, dict) and row.get("scope") == _ENTRY_COVERAGE_SCOPE]
    selected_cases = [row for row in policy["cases"]
                      if isinstance(row, dict) and row.get("scope") in _SELECTED_SUBJECT_SCOPES]
    if not present:
        if coverage_cases or selected_cases:
            raise ValueError("selected-subject case requires the applicability selection")
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
            or any(not isinstance(row, dict) or set(row) not in ({"status", "basis"}, {"status", "basis", "modes"})
                   or row.get("status") not in _ENTRY_DISPOSITIONS or not _text(row.get("basis"))
                   for row in dispositions.values())):
        raise ValueError("entry dispositions must bind every candidate, status and basis")
    modes = _entry_modes(dispositions, mode_catalog)
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
        required_modes = {key: {mode for mode, value in values.items()
                               if case["scope"] == "v33-openai-entry-applicability" or value["status"] == "selected"}
                          for key, values in modes.items()}
        _entry_mode_effects(expected, required_modes)
    selected_modes = {key: {mode for mode, value in modes.get(key, {}).items()
                            if value["status"] == "selected"} for key in selected}
    for case in coverage_cases:
        declared = case["conditions"].get("subjectEntries")
        declared_modes = case["conditions"].get("selectedModes")
        expected = case.get("expected", {}).get("effect", {}).get("entryCapabilityCoverage")
        if (not _refs(declared, set(entries)) or set(declared) != selected
                or not isinstance(declared_modes, dict) or set(declared_modes) != selected
                or any(not _refs(declared_modes[key], selected_modes[key])
                       or set(declared_modes[key]) != selected_modes[key] for key in selected)
                or not isinstance(expected, dict) or set(expected) != selected
                or any(not isinstance(row, dict)
                       or any(row.get(key) is not True for key in _ENTRY_COVERAGE_PREDICATES)
                       for row in expected.values())):
            raise ValueError("entry coverage case must preserve selected subjects, modes and necessary effects")
        _entry_mode_effects(expected, selected_modes, strict=True)
    for case in selected_cases:
        declared = case["conditions"].get("subjectEntries")
        declared_modes = case["conditions"].get("selectedModes")
        if (not _refs(declared, set(entries)) or set(declared) != selected
                or not isinstance(declared_modes, dict) or set(declared_modes) != selected
                or any(not _refs(declared_modes[key], selected_modes[key])
                       or set(declared_modes[key]) != selected_modes[key] for key in selected)):
            raise ValueError("selected-subject case must bind selected subjects and modes")
    pending = any(row["status"] == "pending" for row in dispositions.values())
    pending_modes = {key: sorted(mode for mode, value in values.items() if value["status"] == "pending")
                     for key, values in modes.items()}
    return {"final": final and not pending and not any(pending_modes.values()),
            "scopeIds": (set(_ENTRY_PARENT_SCOPES) | ({_ENTRY_COVERAGE_SCOPE} if coverage_cases else set())
                         | {row["scope"] for row in selected_cases}),
            "caseIds": {row["id"] for row in [*cases, *coverage_cases, *selected_cases]}, "selected": selected,
            "selectedModes": {key: sorted(mode for mode, value in values.items() if value["status"] == "selected")
                              for key, values in modes.items()}, "pendingModes": pending_modes}


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
            conditions = scope['conditions']
            if ('limitSemantics' in conditions and (
                    conditions['limitSemantics'] != 'maximum' or 'limits' not in conditions
                    or not _within_limit_ceiling(conditions['limits'], conditions['limits']))):
                return ["scope limit ceiling must declare maximum positive integer budgets"]
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
                    or not _conditions_match(case["conditions"], scope["conditions"])):
                return ["evidence case differs from its declared claim scope"]
            if "packageFiles" in case:
                _sparse_package_files(contract, case)
        try:
            _entry_selection(policy, entries, contract["capabilityMap"]["entrySurfaces"].get("modeCatalog")) if current else None
        except ValueError as error:
            return [str(error)]
    except (KeyError, TypeError, ValueError, RecursionError):
        return ["evidence admission dependencies or bounded JSON are invalid"]
    return []


def declaration_case_binding_summary(contract):
    """Summarize valid current admission declarations without observing evidence.

    None means unavailable/invalid, never an empty set of proven gaps. Callers
    still own development-source conformance and all empirical qualification.
    """
    try:
        if (not isinstance(contract, dict)
                or contract.get("schema") != "yiyuan-accord-development/v5"
                or admission_contract_errors(contract)):
            return None
        policy = contract["acceptance"]["admission"]
        if policy["schema"] != CURRENT_SCHEMA:
            return None
    except (AttributeError, KeyError, TypeError, ValueError, RecursionError):
        return None
    return _case_binding_summary(policy)


def _case_binding_summary(policy):
    """Compute declarations for a policy already accepted by its caller."""
    cases = {row["id"]: row for row in policy["cases"]}
    scopes = {row["id"]: row for row in policy["scopes"]}
    required_pairs = {(claim, scope) for claim, ids in policy["requiredCoverage"].items() for scope in ids}
    defined_pairs = {(claim, scope_id) for claim, scope_id in required_pairs
                     if scope_id in scopes and claim in scopes[scope_id]["claims"]}
    joint_scopes = set(next(row for row in policy["acceptanceRequirements"] if row["id"] == "A08")
                       ["requiredCoverage"].get("function", []))
    dimensions = ("duties", "qualityAxes", "scenarios")
    binding_gaps, without_cases = {}, set()
    for claim, scope_id in sorted(required_pairs & defined_pairs):
        scope = scopes[scope_id]
        relevant = sorted(key for key, case in cases.items()
                          if case["scope"] == scope_id and claim in case["claims"])
        missing_dimensions = {
            field: sorted(set(scope[field]) - {value for key in relevant for value in cases[key][field]})
            for field in dimensions}
        joint_missing = claim == "function" and scope_id in joint_scopes and not any(
            all(set(scope[field]) <= set(cases[key][field]) for field in dimensions) for key in relevant)
        if not relevant:
            without_cases.add((claim, scope_id))
        if not relevant or any(missing_dimensions.values()) or joint_missing:
            binding_gaps.setdefault(scope_id, {})[claim] = {
                "caseIds": relevant, "missingDimensions": missing_dimensions,
                "jointCaseMissing": joint_missing}
    return {
        "scope": "current-v3.3-case-binding-declarations-only",
        "claimLimit": "No evidence observed; complete declarations do not establish functional completion or candidate eligibility.",
        "caseBindingGaps": binding_gaps,
        "coverageTotal": len(required_pairs),
        "coverageDefined": len(required_pairs & defined_pairs),
        "coverageUnbound": len(required_pairs - defined_pairs),
        "coverageWithoutCases": len(without_cases),
        "coverageWithCaseBindingGaps": sum(len(claims) for claims in binding_gaps.values()),
        "casesDefined": len(cases),
    }


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
    subjects = case.get("subjectEntries")
    if (contract["acceptance"]["admission"]["schema"] == CURRENT_SCHEMA
            and (case["scope"] in {_ENTRY_COVERAGE_SCOPE, _HOST_LIFECYCLE_SCOPE}
                 or (case["scope"] == "v33-system-integration"
                     and {"subjectEntries", "selectedModes"} <= case["conditions"].keys()))):
        # Legacy integration definitions retain their stored identity. Current
        # admission separately requires both selection bindings before hashing.
        subjects = case["conditions"]["subjectEntries"]
        definition["entrySelectionScope"] = selected(
            contract["acceptance"]["admission"]["scopes"], ["v33-openai-entry-applicability"])
    if subjects is not None:
        definition["subjectEntries"] = selected(
            contract["capabilityMap"]["entrySurfaces"]["rows"], subjects)
        if (catalog := contract["capabilityMap"]["entrySurfaces"].get("modeCatalog")) is not None:
            definition["subjectModeCatalog"] = {key: value for key, value in catalog.items()
                                               if key in subjects}
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
    current_case = copy.deepcopy(case)
    policy = current["acceptance"]["admission"]
    for claim, scopes in policy["requiredCoverage"].items():
        policy["requiredCoverage"][claim] = sorted(scopes)
    if "requiredHosts" in policy:
        policy["requiredHosts"] = sorted(policy["requiredHosts"])
    if "acceptanceRequirements" in policy:
        policy["acceptanceRequirements"].sort(key=lambda requirement: requirement["id"])
        for requirement in policy["acceptanceRequirements"]:
            for claim, scopes in requirement["requiredCoverage"].items():
                requirement["requiredCoverage"][claim] = sorted(scopes)
    # These declaration fields are validated as sets of references. Do not
    # recursively sort arbitrary condition/effect arrays: their order may matter.
    for scope in policy["scopes"]:
        for key in ("duties", "qualityAxes", "scenarios", "claims", "subjectEntries"):
            if key in scope:
                scope[key] = sorted(scope[key])
    if "subjectEntries" in current_case:
        current_case["subjectEntries"] = sorted(current_case["subjectEntries"])
    if (policy["schema"] == CURRENT_SCHEMA and current_case["scope"] == "v33-system-integration"
            and {"subjectEntries", "selectedModes"} <= current_case["conditions"].keys()):
        conditions = current_case["conditions"]
        conditions["subjectEntries"] = sorted(conditions["subjectEntries"])
        conditions["selectedModes"] = {key: sorted(values) for key, values in conditions["selectedModes"].items()}
    if (catalog := current["capabilityMap"]["entrySurfaces"].get("modeCatalog")) is not None:
        # Catalog membership is a set; its presentation order is not a changed
        # criterion. Normalize only the reuse copy, never the stored identity.
        for key, values in catalog.items():
            catalog[key] = sorted(values)
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
    return _definition(current, current_case)


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


def bind_evidence_execution(root, case_id, execution, package_files):
    """Preflight a caller's execution plan, not observed facts or admission.

    The optional runner contract lives in the existing case conditions. It must
    already be committed; this function never creates or changes a case. Other
    conditions, actual execution, provenance and independent review remain the
    caller's observation duties. Returned hashes are identity, not attestation.
    """
    root = Path(root)
    if not clean_git_checkout(root):
        raise ValueError("execution binding requires a clean committed checkout")
    subject = evidence_subject(root)
    contract = _strict_json_object(_git(
        root, "show", f"{subject['revision']}:product/development.json").decode("utf-8"))
    if admission_contract_errors(contract):
        raise ValueError("execution binding requires a valid admission contract")
    cases = [case for case in contract["acceptance"]["admission"]["cases"] if case["id"] == case_id]
    if len(cases) != 1:
        raise ValueError("execution case was not prebound")
    case = cases[0]
    planned = case["conditions"].get("execution")
    if not isinstance(planned, dict) or not planned or _json(planned) != _json(execution):
        raise ValueError("execution differs from the prebound case conditions")
    # Older prose conditions stay meaningful: a new structured block cannot
    # silently contradict the scalar settings already bound in that case.
    for key in ("entryProtocol", "model", "reasoning", "windowsSandbox", "codexVersion"):
        if key in case["conditions"] and _json(case["conditions"][key]) != _json(execution.get(key)):
            raise ValueError("execution contradicts an existing case condition")
    if any(execution.get(key) not in case["oracleFiles"] for key in ("runner", "caseFile")):
        raise ValueError("execution runner and fixture must be declared oracle dependencies")
    if any(execution.get(key) != case[key] for key in ("host", "entry")):
        raise ValueError("execution differs from the case host entry")
    fixture = _git(root, "show", f"{subject['revision']}:{execution['caseFile']}")
    if sha256(fixture).hexdigest() != execution.get("caseSha256"):
        raise ValueError("execution fixture differs from the committed candidate")
    projection = next(row for row in contract["delivery"]["hostProjections"] if row["id"] == case["host"])
    package = Path(projection["manifest"]).parents[1].as_posix()
    snapshot = _revision_package_snapshot(root, subject["revision"], package,
                                          {"calls": 0, "files": 0, "bytes": 0})
    expected_files = {path[len(package) + 1:]: sha256(raw).hexdigest()
                      for path, raw in snapshot["files"].items()}
    if snapshot["sha256"] != projection["packageSha256"] or _json(expected_files) != _json(package_files):
        raise ValueError("execution package differs from the committed candidate")
    if evidence_subject(root) != subject or not clean_git_checkout(root):
        raise ValueError("execution subject changed during binding")
    return {"subject": subject, "case": case_id, "scope": case["scope"],
            "definitionSha256": _definition(contract, case), "packageSha256": snapshot["sha256"],
            "execution": copy.deepcopy(execution),
            "remainingConditions": sorted(set(case["conditions"]) - {"execution"}),
            "claimLimit": "Prepared execution identity only; actual conditions, facts, observe/recheck and independent review remain required."}


def _fresh(value, seconds, now):
    try:
        at = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return at if at.utcoffset() is not None and 0 <= (now - at).total_seconds() <= seconds else None
    except (AttributeError, TypeError, ValueError):
        return None


def _impact_definition(contract, case):
    """Isolate only same-base artifact identities in the reuse comparison copy."""
    current = copy.deepcopy(contract)
    current["delivery"]["version"] = _normalized_cache_version(current["delivery"]["version"])
    for projection in current["delivery"]["hostProjections"]:
        if projection["id"] == case["host"]:
            projection["packageVersion"] = _normalized_cache_version(projection["packageVersion"])
            projection["packageSha256"] = "0" * 64
    return _reuse_definition(current, case)


def _impact_eligible(contract, case):
    policy = contract["acceptance"]["admission"]
    scope = next(row for row in policy["scopes"] if row["id"] == case["scope"])
    a08 = next(row for row in policy["acceptanceRequirements"] if row["id"] == "A08")

    def aggregate(value):
        if isinstance(value, dict):
            return bool({"subjectEntries", "selectedModes"} & value.keys()) or any(
                aggregate(item) for item in value.values())
        return isinstance(value, list) and any(aggregate(item) for item in value)

    return (contract["schema"] == "yiyuan-accord-development/v5"
            and policy["schema"] == CURRENT_SCHEMA
            and case["claims"] == ["function"] and scope["claims"] == ["function"]
            and case["scope"] not in {*_ENTRY_PARENT_SCOPES, _ENTRY_COVERAGE_SCOPE,
                                      _HOST_LIFECYCLE_SCOPE, "v33-system-integration"}
            and case["scope"] not in a08["requiredCoverage"].get("function", [])
            and not aggregate([case, scope]))


def _impact_differences(root, original_revision, current_revision, packages, oracle_files, budget):
    """Compute the full declared execution and adjudicator delta, including modes.

    Renames are deletion/addition pairs. No caller selects a smaller adjudicator
    set, and no AST/call graph is treated as a proof of side-effect freedom.
    """
    paths = sorted({*packages, *oracle_files, "yiyuan_accord"})
    if budget["calls"] + 1 > _PACKAGE_ASSESSMENT_CALLS:
        raise ValueError("impact read bound exceeded")
    budget["calls"] += 1
    raw = _git(root, "diff", "--raw", "--no-abbrev", "-z", "--no-renames",
               "--no-ext-diff", "--no-textconv", original_revision, current_revision, "--", *paths)
    if raw and not raw.endswith(b"\0"):
        raise ValueError("unterminated impact delta")
    rows = raw.split(b"\0")[:-1] if raw else []
    if len(rows) % 2:
        raise ValueError("incomplete impact delta")
    entries, requests = [], []
    seen = set()
    for offset in range(0, len(rows), 2):
        fields = rows[offset].decode("ascii").split()
        path = rows[offset + 1].decode("utf-8")
        if (len(fields) != 5 or not fields[0].startswith(":") or not _locator(path) or path in seen
                or fields[4] not in {"A", "D", "M", "T"}):
            raise ValueError("invalid impact delta")
        seen.add(path)
        old_mode, new_mode = fields[0][1:], fields[1]
        if {old_mode, new_mode} - {"000000", "100644", "100755"}:
            raise ValueError("unsupported impact object type")
        if ((fields[4] == "A" and (old_mode != "000000" or new_mode == "000000"))
                or (fields[4] == "D" and (old_mode == "000000" or new_mode != "000000"))
                or (fields[4] in {"M", "T"} and "000000" in {old_mode, new_mode})):
            raise ValueError("inconsistent impact object status")
        entry = {"path": path, "oldMode": old_mode, "newMode": new_mode}
        for side, mode, blob in (("old", old_mode, fields[2]), ("new", new_mode, fields[3])):
            entry[side + "Sha256"] = None
            if mode == "000000" and blob != "0" * 40:
                raise ValueError("invalid absent impact blob")
            if mode != "000000":
                if re.fullmatch(r"[0-9a-f]{40}", blob) is None:
                    raise ValueError("invalid impact blob")
                requests.append((entry, side, blob))
        entries.append(entry)
    if (budget["calls"] + bool(requests) > _PACKAGE_ASSESSMENT_CALLS
            or budget["files"] + len(requests) > _PACKAGE_ASSESSMENT_FILES
            or budget["bytes"] + _PACKAGE_TREE_BYTES > _PACKAGE_ASSESSMENT_BYTES):
        raise ValueError("impact read bound exceeded")
    if requests:
        budget["calls"] += 1
        budget["files"] += len(requests)
        budget["bytes"] += _PACKAGE_TREE_BYTES
        blobs, total = _batch_blobs(root, [request[2] for request in requests])
        budget["bytes"] -= _PACKAGE_TREE_BYTES - total
        for (entry, side, _), blob in zip(requests, blobs, strict=True):
            entry[side + "Sha256"] = sha256(blob).hexdigest()
    return entries


def _condition_leaves(value, pointer=""):
    if isinstance(value, (dict, list)) and value:
        items = value.items() if isinstance(value, dict) else enumerate(value)
        return {path: item for key, child in items for path, item in _condition_leaves(
            child, pointer + "/" + str(key).replace("~", "~0").replace("/", "~1")).items()}
    return {pointer: value}


def _current_impact(root, material, record, original_contract, original, contract, case,
                    subject, snapshots, packages, budget, now, candidate_time, *, parent=False):
    """Validate consistency; authenticated completeness/semantics remain caller duties.

    Source hashes are observer attestations, not files opened or authenticated by
    this function. Independent impact reviews must bind this exact material.
    Qualification concerns the final *case claim*, not unrelated episode errors.
    """
    def require(condition):
        if not condition:
            raise _CaseRejection("current-applicability-unsupported")

    require(isinstance(material, dict) and set(material) == {
        "schema", "original", "current", "differences", "conditionBindings", "sources", "reviewBundle"}
        | ({"predicateBindings", "roles", "relationships"} if parent else set()))
    require(material["schema"] == ("yiyuan-accord-parent-applicability/v1" if parent
                                   else "yiyuan-accord-current-applicability/v1"))
    if parent:
        claim = _PARENT_CLAIMS.get(case["scope"])
        require(claim is not None and original_contract["schema"] == contract["schema"]
                == "yiyuan-accord-development/v5" and all(
                c["acceptance"]["admission"]["schema"] == CURRENT_SCHEMA
                and v["claims"] == [claim] for c, v in ((original_contract, original), (contract, case))))
    else:
        require(_impact_eligible(original_contract, original) and _impact_eligible(contract, case))
    require(_json(original) == _json(case)
            and _impact_definition(original_contract, original) == _impact_definition(contract, case))
    revision = record["evaluatedRevision"]
    original_subject = {"revision": revision,
                        "tree": _git(root, "rev-parse", "--verify", revision + "^{tree}").decode("ascii").strip()}
    sources = material["sources"]
    require(isinstance(sources, dict) and bool(sources))
    for key, source in sources.items():
        require(_text(key) and isinstance(source, dict)
                and set(source) == {"sourceRef", "sha256", "kind"}
                and _text(source["sourceRef"]) and isinstance(source["sha256"], str)
                and re.fullmatch(r"[0-9a-f]{64}", source["sha256"]) is not None
                and source["kind"] in {"original-qualification", "original-final-outcome",
                                       "source-analysis", "current-observation"})

    def refs(values, kind=None):
        return (isinstance(values, list) and bool(values)
                and all(isinstance(value, str) and value in sources for value in values)
                and len(values) == len(set(values))
                and (kind is None or all(sources[value]["kind"] == kind for value in values)))

    old = material["original"]
    require(isinstance(old, dict) and set(old) == {
        "subject", "recordSha256", "definitionSha256", "packageSha256", "episodeId", "qualification"})
    require(old["subject"] == original_subject and old["recordSha256"] == _hash(record)
            and all(old[key] == record[key] for key in ("definitionSha256", "packageSha256", "episodeId")))
    qualification = old["qualification"]
    require(isinstance(qualification, dict) and set(qualification) == {
        "case", "scope", "claim", "episodeId", "recordSha256", "subject", "decision",
        "stage", "qualifiedAt", "sources", "finalOutcomeSources", "knownFailuresAndLimits"})
    require(qualification["case"] == case["id"] and qualification["scope"] == case["scope"]
            and qualification["claim"] == (_PARENT_CLAIMS[case["scope"]] if parent else "function")
            and qualification["subject"] == original_subject
            and qualification["recordSha256"] == _hash(record)
            and qualification["episodeId"] == record["episodeId"]
            and qualification["decision"] == "accepted" and qualification["stage"] == "final-case-qualification"
            and refs(qualification["sources"], "original-qualification")
            and refs(qualification["finalOutcomeSources"], "original-final-outcome"))
    # The caller must disclose all known failures/limits, including orthogonal
    # episode closeout failures. An early PASS relabelled as final is insufficient.
    # Completeness and claim attribution are reviewed semantic source duties.
    negatives = qualification["knownFailuresAndLimits"]
    require(isinstance(negatives, list))
    for row in negatives:
        require(isinstance(row, dict) and set(row) == {"sources", "disposition", "basis", "resolutionSources"}
                and refs(row["sources"]) and _text(row["basis"])
                and row["disposition"] in {"outside-case-claim", "resolved-before-final-case-qualification"}
                and (row["resolutionSources"] == [] if row["disposition"] == "outside-case-claim"
                     else refs(row["resolutionSources"], "original-final-outcome")))
    qualified = _fresh(qualification["qualifiedAt"], float("inf"), now)
    require(qualified is not None and qualified >= _fresh(record["observedAt"], float("inf"), now))
    current = material["current"]
    require(isinstance(current, dict) and set(current) == {"subject", "definitionSha256", "packageSha256", "context"})
    require(current["subject"] == subject and current["definitionSha256"] == _definition(contract, case)
            and current["packageSha256"] == snapshots[1]["sha256"])
    context = current["context"]
    require(isinstance(context, dict) and set(context) == {
        "host", "entry", "configuration", "authority", "helpers", "continuingState"})
    for key in ("host", "entry"):
        require(isinstance(context[key], dict) and set(context[key]) == {"value", "sources"}
                and context[key]["value"] == case[key] and refs(context[key]["sources"], "current-observation"))
    require(all(refs(context[key], "current-observation")
                for key in ("configuration", "authority", "helpers", "continuingState")))
    differences = material["differences"]
    expected = _impact_differences(root, revision, subject["revision"], packages, case["oracleFiles"], budget)
    require(isinstance(differences, list) and len(differences) == len(expected))
    by_path = {}
    for row in differences:
        require(isinstance(row, dict) and set(row) == {
            "path", "oldMode", "newMode", "oldSha256", "newSha256", "role", "impact", "basis", "sources", "currentConsequences"})
        require(isinstance(row["path"], str) and row["path"] not in by_path
                and _text(row["role"]) and _text(row["basis"])
                and row["impact"] in {"original-observation-still-applies", "current-consequence-supported"}
                and refs(row["sources"]) and refs(row["currentConsequences"], "current-observation"))
        # An applicable retained current observation may support multiple deltas;
        # metadata changes do not mandate new business executions or new episodes.
        by_path[row["path"]] = row
    require(set(by_path) == {row["path"] for row in expected}
            and all(all(by_path[row["path"]][key] == value for key, value in row.items()) for row in expected))
    leaves = _condition_leaves(original["conditions"])
    bindings = material["conditionBindings"]
    require(isinstance(bindings, list) and len(bindings) == len(leaves))
    seen = set()
    for row in bindings:
        require(isinstance(row, dict) and set(row) == {
            "pointer", "originalValue", "responsibility", "currentValue", "basis", "sources"}
            | ({"role", "originalSources"} if parent else set()))
        pointer = row["pointer"]
        require(isinstance(pointer, str) and pointer in leaves and pointer not in seen
                and _json(row["originalValue"]) == _json(leaves[pointer])
                and row["responsibility"] in ({"historical-execution", "continuing-applicability"}
                    | ({"actual-current-reassessment"} if parent else set()))
                and (row["responsibility"] != "continuing-applicability"
                     or _json(row["currentValue"]) == _json(leaves[pointer]))
                and _text(row["basis"]) and refs(row["sources"], "current-observation"))
        seen.add(pointer)
    if parent:
        _parent_bindings(material, record, case, refs, require)
    digest = _hash({key: value for key, value in material.items() if key != "reviewBundle"})
    review_policy = contract["acceptance"]["admission"]["reviewPolicy"]
    require(set(review_policy["requiredAxes"]) == {"product", "specification", "implementation", "standards"}
            and review_policy["minimumReviewers"] >= 2
            and any(set(pair) == {"specification", "implementation"} for pair in review_policy["independentAxes"]))
    review = material["reviewBundle"]
    require(evaluate_review_bundle(review, subject["revision"], subject["tree"], policy=review_policy,
                                  expected_evidence_sha256=digest)["decision"] == "pass")
    require(all((at := _fresh(row["reviewedAt"], contract["acceptance"]["admission"]["reviewMaxAgeSeconds"], now))
                is not None and at.timestamp() >= candidate_time for row in review["reviews"]))
    return {"evidenceSha256": digest, "original": copy.deepcopy(old), "current": copy.deepcopy(current),
            "conditionBindings": copy.deepcopy(bindings),
            **({"predicateBindings": copy.deepcopy(material["predicateBindings"]),
                "roles": copy.deepcopy(material["roles"]), "relationships": copy.deepcopy(material["relationships"])}
               if parent else {}),
            "claimLimit": ("complete-original-parent-case-current-applicability-not-new-execution" if parent else
                "historical-single-entry-function-current-applicability-not-new-execution-or-parent-coverage")}



def _parent_bindings(material, record, case, refs, require):
    """Complete-case only. Source meaning and actual causality need source review."""
    modes = case["conditions"].get("selectedModes")
    if modes is None:
        modes = {key: [name for name, row in value.get("modes", {}).items()
                       if row["status"] == "selected"]
                 for key, value in case["conditions"].get("entryDispositions", {}).items()}
    entries = case.get("subjectEntries", case["conditions"].get("subjectEntries", [case["entry"]]))
    selected = {(entry, None) for entry in entries} | {
        (entry, mode) for entry in entries for mode in modes.get(entry, [])}
    roles = material["roles"]
    require(isinstance(roles, list) and len(roles) == len(selected))
    by_id, identities = {}, set()
    for row in roles:
        require(isinstance(row, dict) and set(row) == {
            "id", "entry", "mode", "originalActor", "currentActor", "responsibility",
            "originalSources", "currentSources", "basis"})
        require(_text(row["id"]) and row["id"] not in by_id and _text(row["originalActor"])
                and _text(row["basis"]) and row["responsibility"] in {
                    "historical-execution", "continuing-applicability", "actual-current-reassessment"}
                and refs(row["originalSources"], "original-final-outcome"))
        identity = (row["entry"], row["mode"])
        require(identity in selected and identity not in identities)
        if row["responsibility"] == "historical-execution":
            require(row["currentActor"] is None and row["currentSources"] == [])
        else:
            require(_text(row["currentActor"]) and refs(row["currentSources"], "current-observation"))
        by_id[row["id"]] = row
        identities.add(identity)
    def binding_responsibility(row, role, sources):
        responsibility = row["responsibility"]
        require(responsibility in {"historical-execution", "continuing-applicability", "actual-current-reassessment"})
        require((sources == [] and responsibility == "historical-execution")
                or refs(sources, "current-observation"))
        if responsibility == "continuing-applicability":
            require(role["responsibility"] != "historical-execution" and _text(role["currentActor"]))

    expected = _condition_leaves(case["expected"])
    actual = _condition_leaves({key: value["value"] for key, value in record["facts"].items()})
    bindings = material["predicateBindings"]
    require(isinstance(bindings, list) and len(bindings) == len(expected))
    seen = set()
    for row in bindings:
        require(isinstance(row, dict) and set(row) == {
            "pointer", "role", "responsibility", "originalValue", "currentValue", "originalSources", "currentSources", "basis"})
        pointer, role_id = row["pointer"], row["role"]
        require(isinstance(pointer, str) and pointer in expected and pointer not in seen
                and role_id in by_id and _text(row["basis"])
                and _json(row["originalValue"]) == _json(actual[pointer]) == _json(expected[pointer])
                and _json(row["currentValue"]) == _json(expected[pointer])
                and refs(row["originalSources"], "original-final-outcome"))
        role = by_id[role_id]
        parts = pointer.split("/")
        for entry in entries:
            if entry in parts:
                require(role["entry"] == entry)
        if "modes" in parts:
            require(role["mode"] == parts[parts.index("modes") + 1])
        elif len(parts) > 3 and parts[1] == "effect" and parts[2] in {"entryDelivery", "entryLifecycle"}:
            require(role["mode"] is None)
        binding_responsibility(row, role, row["currentSources"])
        seen.add(pointer)
    # Conditions stay complete even when a historical actor has ended. Current
    # dependency declarations cannot erase a missing original duty.
    for row in material["conditionBindings"]:
        require(row["role"] in by_id and refs(row["originalSources"], "original-final-outcome")
                and _json(row["currentValue"]) == _json(row["originalValue"]))
        binding_responsibility(row, by_id[row["role"]], row["sources"])
    edges = material["relationships"]
    kinds = {"authority", "single-writer", "action", "feedback", "adoption", "poststate"}
    joined = case["scope"] == "v33-system-integration"
    require(isinstance(edges, list) and (not joined or len(edges) == len(kinds)))
    previous = None
    for edge in edges:
        require(isinstance(edge, dict) and set(edge) == {
            "kind", "episodeId", "fromRole", "toRole", "fromEvent", "toEvent", "sources", "basis"})
        require(edge["kind"] in kinds and edge["episodeId"] == record["episodeId"]
                and edge["fromRole"] in by_id and edge["toRole"] in by_id
                and _text(edge["fromEvent"]) and _text(edge["toEvent"])
                and edge["fromEvent"] != edge["toEvent"] and _text(edge["basis"])
                and refs(edge["sources"], "original-final-outcome"))
        require(not joined or previous is None or (previous["toEvent"], previous["toRole"])
                == (edge["fromEvent"], edge["fromRole"]))
        previous = edge
        kinds.remove(edge["kind"])


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
                       for row in contract["capabilityMap"]["entrySurfaces"]["rows"]},
                       contract["capabilityMap"]["entrySurfaces"].get("modeCatalog"))
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
    admitted, package_reuse, current_applicability, parent_applicability = set(), {}, {}, {}
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
            observation_started = monotonic()
            data = _strict_json_object(_json(observer(copy.deepcopy(request))))
            if (not {"records", "reviewBundle"} <= set(data)
                    or set(data) - {"records", "reviewBundle", "currentApplicability", "parentApplicability"}
                    or not isinstance(data["records"], list)):
                raise ValueError("invalid observation envelope")
            ordinary_materials = data.get("currentApplicability", {})
            parent_materials = data.get("parentApplicability", {})
            if any(not isinstance(rows, dict) or not set(rows) <= cases.keys()
                   for rows in (ordinary_materials, parent_materials)) or set(ordinary_materials) & set(parent_materials):
                raise ValueError("invalid current applicability mapping")
            materials = {**ordinary_materials, **parent_materials}
            now = datetime.now(timezone.utc)
            candidate_time = int(_git(root, "show", "-s", "--format=%ct", subject["revision"]).strip())
            prior, package_snapshots, seen, read_blobs = {}, {}, set(), set()
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
                    reuse_issues = []
                    if key in materials and not checks["reuse-definition"]:
                        reuse_issues.append("reuse-definition-mismatch")
                        checks.pop("reuse-definition")
                    if not all(checks.values()):
                        raise _CaseRejection(*(f"{name}-mismatch" for name, valid in checks.items() if not valid))
                    package_files = _sparse_package_files(contract, case)
                    if package_files is None:
                        if record["packageSha256"] != bound["packageSha256"]:
                            if key not in materials:
                                raise _CaseRejection("complete-package-changed")
                            reuse_issues.append("complete-package-changed")
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
                        if key not in materials:
                            raise _CaseRejection("execution-dependency-changed")
                        reuse_issues.append("execution-dependency-changed")
                    for path in case["oracleFiles"]:
                        for source_revision in ([revision, subject["revision"]] if path in review_files else [revision]):
                            locator = f"{source_revision}:{path}"
                            if locator not in read_blobs:
                                _git(root, "cat-file", "blob", locator)
                                read_blobs.add(locator)
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
                    if (policy["schema"] != CURRENT_SCHEMA
                            and _fresh(record["observedAt"], case["maxAgeSeconds"], now) is None):
                        unmet.append("observation-expired")
                    if _json(record["conditions"]) != _json(case["conditions"]):
                        unmet.append("execution-conditions-mismatch")
                    if any(_json(facts[k]["value"]) != _json(v) for k, v in case["expected"].items()):
                        unmet.append("consequence-mismatch")
                    if unmet:
                        reject_case(key, *unmet)
                        case_errors.append(f"{key}: freshness, conditions or consequence not admitted")
                    else:
                        if key in materials:
                            destination = parent_applicability if key in parent_materials else current_applicability
                            destination[key] = _current_impact(
                                root, materials[key], record, prior[revision], original, contract, case,
                                subject, (original_snapshot, current_snapshot),
                                (original_package, current_package), package_budget, now, candidate_time,
                                parent=key in parent_materials)
                            destination[key]["reconciledReasons"] = reuse_issues
                        admitted.add(key)
                except (OSError, subprocess.SubprocessError, KeyError, TypeError, ValueError, StopIteration) as error:
                    reject_case(key, *(error.codes if isinstance(error, _CaseRejection) else ("source-evidence-unavailable",)))
                    errors.append(f"{key}: source, identity, freshness, conditions or consequence not admitted")
            if not set(materials) <= seen:
                raise ValueError("current applicability has no original record")
            review = data["reviewBundle"]
            if review_bundle is not None and _json(review_bundle) != _json(review):
                errors.append("review input differs from the observer-checked bundle")
            review_result = evaluate_review_bundle(review, subject["revision"], subject["tree"],
                                                   policy=policy["reviewPolicy"])
            errors.extend("independent review: " + error for error in review_result["errors"])
            if review_result["decision"] == "pass" and any(
                    (at := _fresh(v["reviewedAt"], contract["acceptance"]["admission"]["reviewMaxAgeSeconds"], now)) is None
                    or at.timestamp() < candidate_time
                    for v in review["reviews"]):
                errors.append("independent review predates its subject, is future-dated or expired")
            observation_hash = _hash(data)
            recheck = _strict_json_object(_json(observer(copy.deepcopy({
                **request, "phase": "recheck", "observationSha256": observation_hash,
            }))))
            recheck_fields = {"subject", "conditions", "observationSha256"}
            for name, rows in (("currentApplicability", ordinary_materials), ("parentApplicability", parent_materials)):
                if rows:
                    recheck_fields.add(name)
            if (set(recheck) != recheck_fields
                    or recheck["subject"] != subject or recheck["observationSha256"] != observation_hash
                    or not isinstance(recheck["conditions"], dict)):
                raise ValueError("invalid observer recheck")
            for name, rows in (("currentApplicability", ordinary_materials), ("parentApplicability", parent_materials)):
                if rows and (not isinstance(recheck[name], dict) or set(recheck[name]) != set(rows)):
                    raise ValueError("invalid current applicability recheck")
            applicable = {**current_applicability, **parent_applicability}
            for key in list(admitted):
                if key in applicable:
                    fields = ("evidenceSha256", "current", "conditionBindings") + ((
                        "predicateBindings", "roles", "relationships") if key in parent_applicability else ())
                    expected = {field: applicable[key][field] for field in fields}
                    name = "parentApplicability" if key in parent_applicability else "currentApplicability"
                    if _json(recheck[name][key]) != _json(expected):
                        admitted.remove(key)
                        reject_case(key, "current-applicability-changed")
                        case_errors.append(f"{key}: current applicability changed or unavailable")
                        continue
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
            observation_elapsed = monotonic() - observation_started
            for record in data["records"]:
                if isinstance(record, dict) and record.get("case") in admitted:
                    key = record["case"]
                    current = policy["schema"] == CURRENT_SCHEMA
                    expired = (not 0 <= observation_elapsed < cases[key]["maxAgeSeconds"] if current
                               else _fresh(record["observedAt"], cases[key]["maxAgeSeconds"], final_now) is None)
                    if expired:
                        admitted.remove(key)
                        reason = "current-applicability-expired" if current else "observation-expired"
                        reject_case(key, reason)
                        case_errors.append(f"{key}: {reason} before final qualification")
            if review_result["decision"] == "pass" and any(
                    _fresh(v["reviewedAt"], contract["acceptance"]["admission"]["reviewMaxAgeSeconds"], final_now) is None
                    for v in review["reviews"]):
                errors.append("independent review expired before final qualification")
            for key in list(admitted & applicable.keys()):
                if any(_fresh(row["reviewedAt"], policy["reviewMaxAgeSeconds"], final_now) is None
                       for row in materials[key]["reviewBundle"]["reviews"]):
                    admitted.remove(key)
                    reject_case(key, "current-impact-review-expired")
                    case_errors.append(f"{key}: impact review expired before final qualification")
            if errors:
                # A dedicated impact review cannot replace the ordinary current
                # candidate review or rescue another failed source/identity guard.
                for key in list(admitted & applicable.keys()):
                    admitted.remove(key)
                    reject_case(key, "current-candidate-review-or-source-invalid")
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
                                    "selected": sorted(entry_selection["selected"]),
                                    "selectedModes": entry_selection["selectedModes"],
                                    "pendingModes": entry_selection["pendingModes"]}
    report["acceptedCases"] = sorted(admitted)
    if current_applicability:
        report["currentApplicability"] = {key: current_applicability[key]
                                          for key in sorted(admitted & current_applicability.keys())}
    if parent_applicability:
        report["currentParentApplicability"] = {key: parent_applicability[key]
            for key in sorted(admitted & parent_applicability.keys())}
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
        # The same declaration-only diagnostic is exposed by the static CLI.
        declaration_summary = _case_binding_summary(policy)
        report["caseBindingGaps"] = declaration_summary["caseBindingGaps"]
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
            "coverageWithoutCases": declaration_summary["coverageWithoutCases"],
            "coverageWithCaseBindingGaps": declaration_summary["coverageWithCaseBindingGaps"],
            "casesDefined": len(cases),
            "casesAccepted": len(admitted),
        }
    return report
