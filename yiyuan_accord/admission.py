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
_LIMIT = 1_000_000
_CLAIMS = {"function", "incremental-value", "package-lifecycle"}
_CASE_FIELDS = set("id scope host entry duties qualityAxes scenarios claims oracle oracleFiles conditions maxAgeSeconds expected".split())
_SCOPE_FIELDS = set("id host entry duties qualityAxes scenarios claims conditions rule".split())
_RECORD_FIELDS = set("case evaluatedRevision definitionSha256 packageSha256 observedAt conditions observerId sourceRef episodeId facts".split())
_TRUST = ("Conditional on the caller's authenticated, independent, bounded read-only observer "
          "and review provenance; callable shape and this verifier do not authenticate external facts.")


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


def admission_contract_errors(contract):
    """Check declarations, not empirical adequacy of oracles or coverage claims."""
    policy = contract.get("acceptance", {}).get("admission")
    if (not isinstance(policy, dict) or set(policy) != {"schema", "rule", "reviewPolicy", "reviewMaxAgeSeconds", "requiredCoverage", "scopes", "cases"}
            or policy.get("schema") != SCHEMA or not _text(policy.get("rule"))
            or type(policy.get("reviewMaxAgeSeconds")) is not int or policy["reviewMaxAgeSeconds"] <= 0
            or any(not isinstance(policy.get(k), list) or len(policy[k]) > 128 for k in ("scopes", "cases"))):
        return ["current evidence admission policy is missing or invalid"]
    if errors := review_policy_errors(policy["reviewPolicy"]):
        return errors
    try:
        _json(policy)
        required = policy["requiredCoverage"]
        if (not isinstance(required, dict) or set(required) != _CLAIMS
                or any(not isinstance(ids, list) or not 0 < len(ids) <= 128
                       or not all(_text(v) for v in ids) or len(ids) != len(set(ids))
                       for ids in required.values())):
            return ["all three qualification claims must prebind required scope IDs"]
        sets = {
            "duties": {v["id"] for v in contract["acceptance"]["duties"]},
            "qualityAxes": {v["id"] for v in contract["systemOptimization"]["qualityAxes"]},
            "scenarios": {v["id"] for v in contract["environmentControl"]["adaptationScenarios"]},
            "claims": _CLAIMS,
        }
        entries = {v["id"]: v["host"] for v in contract["capabilityMap"]["entrySurfaces"]["rows"]}
        hosts = {v["id"] for v in contract["delivery"]["hostProjections"]}
        scopes = {}
        for scope in policy["scopes"]:
            if (not isinstance(scope, dict) or set(scope) != _SCOPE_FIELDS
                    or not _text(scope.get("id")) or scope["id"] in scopes
                    or not isinstance(scope.get("host"), str) or scope["host"] not in hosts
                    or not isinstance(scope.get("entry"), str) or entries.get(scope["entry"]) != scope["host"]
                    or any(not _refs(scope.get(k), values) for k, values in sets.items())
                    or not scope["duties"] or not scope["qualityAxes"] or not scope["claims"]
                    or not _text(scope.get("rule"))
                    or not isinstance(scope.get("conditions"), dict) or not scope["conditions"]
                    or any(v is None for v in scope["conditions"].values())):
                return ["evidence scope must bind its entry, relevant environment axes and required coverage"]
            scopes[scope["id"]] = scope
        ids = set()
        for case in policy["cases"]:
            if (not isinstance(case, dict) or set(case) != _CASE_FIELDS
                    or not _text(case.get("id")) or case["id"] in ids
                    or not isinstance(case.get("host"), str) or case["host"] not in hosts
                    or not isinstance(case.get("entry"), str) or entries.get(case["entry"]) != case["host"]
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
                    or ("incremental-value" in case["claims"] and "comparison" not in case["expected"])):
                return ["evidence case must bind its applicable need, entry, oracle, conditions and post-state"]
            ids.add(case["id"])
            scope = scopes.get(case.get("scope"))
            if (scope is None or any(case[k] != scope[k] for k in ("host", "entry"))
                    or any(not set(case[k]) <= set(scope[k]) for k in sets)
                    or any(k not in case["conditions"] or _json(case["conditions"][k]) != _json(v)
                           for k, v in scope["conditions"].items())):
                return ["evidence case differs from its declared claim scope"]
    except (KeyError, TypeError, ValueError, RecursionError):
        return ["evidence admission dependencies or bounded JSON are invalid"]
    return []


def _definition(contract, case):
    def selected(rows, ids):
        return sorted((v for v in rows if v["id"] in ids), key=lambda v: v["id"])
    return _hash({
        "schema": SCHEMA, "case": {**case, **{k: sorted(case[k]) for k in
            ("duties", "qualityAxes", "scenarios", "claims", "oracleFiles")}},
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
    })


def _git(root, *args):
    return _bounded_git_bytes(root, ("--no-replace-objects", "--literal-pathspecs", *args), _LIMIT)


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
              "checkoutClean": None, "errors": []}
    policy = contract["acceptance"]["admission"]
    cases = {v["id"]: v for v in policy["cases"]}
    scopes = {v["id"]: v for v in policy["scopes"]}
    errors = report["errors"]
    hosts = {v["id"]: v for v in contract["delivery"]["hostProjections"]}
    required = {
        "duties": {v["id"] for v in contract["acceptance"]["duties"]},
        "qualityAxes": {v["id"] for v in contract["systemOptimization"]["qualityAxes"]},
        "scenarios": {v["id"] for v in contract["environmentControl"]["adaptationScenarios"]},
    }
    admitted = set()
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
            prior, seen = {}, set()
            for record in data["records"]:
                if (not isinstance(record, dict) or set(record) != _RECORD_FIELDS
                        or not isinstance(record.get("case"), str) or record["case"] not in cases):
                    errors.append("unknown or malformed evidence record")
                    continue
                key = record["case"]
                if key in seen:
                    admitted.discard(key)
                    errors.append(f"{key}: duplicate or conflicting observations")
                    continue
                seen.add(key)
                case, bound = cases[key], request["cases"][key]
                try:
                    at = _fresh(record["observedAt"], case["maxAgeSeconds"], now)
                    if at is None:
                        raise ValueError("future, undated or expired observation")
                    revision = record["evaluatedRevision"]
                    if not isinstance(revision, str) or re.fullmatch(r"[0-9a-f]{40}", revision) is None:
                        raise ValueError("invalid evaluated revision")
                    _git(root, "merge-base", "--is-ancestor", revision, subject["revision"])
                    if revision not in prior:
                        original_contract = _strict_json_object(_git(root, "show", f"{revision}:product/development.json").decode("utf-8"))
                        if (original_contract.get("schema") != contract["schema"]
                                or admission_contract_errors(original_contract)):
                            raise ValueError("evaluated admission declaration is invalid")
                        prior[revision] = original_contract
                    original = next(v for v in prior[revision]["acceptance"]["admission"]["cases"] if v["id"] == key)
                    if (record["definitionSha256"] != bound["definitionSha256"]
                            or _definition(prior[revision], original) != bound["definitionSha256"]
                            or record["packageSha256"] != bound["packageSha256"]):
                        raise ValueError("definition or package identity changed")
                    package = Path(hosts[case["host"]]["manifest"]).parents[1].as_posix()
                    _git(root, "diff", "--quiet", "--no-ext-diff", "--no-textconv", revision, "--", package, *case["oracleFiles"])
                    for path in case["oracleFiles"]:
                        _git(root, "cat-file", "blob", f"{revision}:{path}")
                    committed = int(_git(root, "show", "-s", "--format=%ct", revision).strip())
                    if at.timestamp() < committed or _json(record["conditions"]) != _json(case["conditions"]):
                        raise ValueError("unbound capture time or conditions")
                    if not all(_text(record[k]) for k in ("episodeId", "sourceRef", "observerId")):
                        raise ValueError("source, observer and episode must be bound")
                    facts = record["facts"]
                    if not isinstance(facts, dict) or set(facts) != set(case["expected"]):
                        raise ValueError("incomplete effect and post-state facets")
                    for facet, expected in case["expected"].items():
                        actual = facts[facet]
                        if (not isinstance(actual, dict) or set(actual) != {"episodeId", "value"}
                                or actual["episodeId"] != record["episodeId"]
                                or _json(actual["value"]) != _json(expected)):
                            raise ValueError("failed or cross-episode effect/post-state")
                    admitted.add(key)
                except (OSError, subprocess.SubprocessError, KeyError, TypeError, ValueError, StopIteration):
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
                    errors.append(f"{key}: current conditions changed or unavailable")
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
                        errors.append(f"{key}: observation expired before final qualification")
            if review_result["decision"] == "pass" and any(
                    _fresh(v["reviewedAt"], contract["acceptance"]["admission"]["reviewMaxAgeSeconds"], final_now) is None
                    for v in review["reviews"]):
                errors.append("independent review expired before final qualification")
        except Exception:
            # External exception text may contain private source data or credentials.
            errors.append("evidence observer unavailable, invalid or subject changed")
            admitted.clear()
    report["acceptedCases"] = sorted(admitted)
    bound = {claim: {key for key in ids if key in scopes and claim in scopes[key]["claims"]}
             for claim, ids in policy["requiredCoverage"].items()}
    report["unboundCoverage"] = {claim: sorted(set(ids) - bound[claim])
                                 for claim, ids in policy["requiredCoverage"].items()}
    completed = {claim: bool(bound[claim]) and not report["unboundCoverage"][claim] and not errors
                 for claim in _CLAIMS}
    report["productCoverage"] = {}
    for host in hosts:
        selected = [scopes[key] for key in set().union(*bound.values()) if scopes[key]["host"] == host]
        report["productCoverage"][host] = {
            k: sorted(values - {v for scope in selected for v in scope[k]}) for k, values in required.items()}
        for claim in ("function", "package-lifecycle"):
            completed[claim] &= any(scopes[key]["host"] == host for key in bound[claim])
    for scope_id, scope in scopes.items():
        row = {"host": scope["host"], "entry": scope["entry"],
               "conditions": copy.deepcopy(scope["conditions"]), "claims": {}}
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
    report["functionalCompletion"] = completed["function"]
    report["incrementalValue"] = "supported-for-bound-cases" if completed["incremental-value"] else "unverified"
    report["candidateEligible"] = (all(completed.values()) and len(admitted) == len(cases)
                                   and not any(v for row in report["productCoverage"].values() for v in row.values()))
    return report
