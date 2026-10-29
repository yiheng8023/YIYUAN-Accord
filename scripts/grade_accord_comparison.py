"""Prepare synthetic calibration inputs or inspect outputs; never run an Agent.

This developer tool grades specified file facts only. It cannot certify host
isolation, authority, process behavior, user effort, net value or release status.
"""

import argparse
from collections import Counter
from decimal import Decimal
import hashlib
import json
from pathlib import Path, PurePosixPath
import posixpath
import stat
import sys


ROOT = Path(__file__).resolve().parents[1]
SUITE = ROOT / "evals/comparisons/accord-toggle-v1.json"
LIMIT = 1_048_576


def strict_json(text):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError("duplicate JSON key")
            result[key] = value
        return result

    def invalid(_):
        raise ValueError("non-finite JSON number")

    return json.loads(text, object_pairs_hook=pairs, parse_constant=invalid, parse_float=Decimal)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def path_parts(relative):
    if not isinstance(relative, str) or not relative or "\\" in relative or ":" in relative:
        raise ValueError("invalid relative path")
    path = PurePosixPath(relative)
    if path.is_absolute() or any(part in (".", "..", "") for part in relative.split("/")):
        raise ValueError("invalid relative path")
    return path.parts


def check_links(path):
    for candidate in (path, *path.parents):
        info = candidate.lstat()
        if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & 0x400:
            raise ValueError("linked or reparse path")


def read_file(root, relative):
    path = root.joinpath(*path_parts(relative))
    check_links(path)
    before = path.stat()
    if not stat.S_ISREG(before.st_mode) or before.st_size > LIMIT:
        raise ValueError("not a bounded regular file")
    with path.open("rb") as source:
        data = source.read(LIMIT + 1)
    after = path.stat()
    if len(data) > LIMIT or (before.st_ino, before.st_size, before.st_mtime_ns) != (
            after.st_ino, after.st_size, after.st_mtime_ns):
        raise ValueError("file changed during read")
    return data


def load_suite():
    raw = read_file(SUITE.parent, SUITE.name)
    suite = strict_json(raw.decode("utf-8"))
    if suite.get("schema") != "accord-comparison-calibration/v1":
        raise ValueError("unsupported suite")
    ids = [case["id"] for case in suite["cases"]]
    if not ids or len(ids) != len(set(ids)):
        raise ValueError("empty or duplicate case ids")
    for case in suite["cases"]:
        for field in ("inputs", "stages"):
            if not isinstance(case[field], dict) or not case[field]:
                raise ValueError("empty case material")
        for name in case["inputs"]:
            path_parts(name)
        for stage in case["stages"].values():
            if not stage["request"] or not stage["outputs"]:
                raise ValueError("missing request or output contract")
            for name in stage["outputs"]:
                path_parts(name)
    return suite, digest(raw)


def select_case(suite, case_id):
    for case in suite["cases"]:
        if case["id"] == case_id:
            return case
    raise ValueError("unknown case")


def prepare(case, destination):
    """Create a new input-only workspace; existing paths are never overwritten."""
    destination = Path(destination).absolute()
    check_links(destination.parent)
    destination.mkdir(exist_ok=False)
    for relative, text in case["inputs"].items():
        path = destination.joinpath(*path_parts(relative))
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("xb") as target:
            target.write(text.encode("utf-8"))
    return {"state": "prepared-inputs-only", "case": case["id"],
            "inputs": {name: digest(text.encode("utf-8"))
                       for name, text in case["inputs"].items()},
            "requests": {name: stage["request"] for name, stage in case["stages"].items()},
            "claimLimit": "No Agent, model, trust, configuration or comparison run started."}


def canonical(value):
    """Type-sensitive JSON value, with array order ignored as the task permits."""
    if isinstance(value, dict):
        return ("object", tuple(sorted((key, canonical(child)) for key, child in value.items())))
    if isinstance(value, list):
        return ("array", tuple(sorted((canonical(child) for child in value), key=repr)))
    return (type(value).__name__, value)


def manifest_references(values, expected, root):
    if not isinstance(values, list) or not all(isinstance(item, str) for item in values):
        return None
    normalized = []
    for item in values:
        raw = item.replace("\\", "/")
        # Validate before normalization, which could otherwise erase a drive or
        # an invalid segment. Never leave the task root even temporarily.
        if ":" in raw or raw.startswith("/") or any(ord(char) < 32 for char in raw):
            return None
        depth = 0
        for part in raw.split("/"):
            if part == "..":
                depth -= 1
            elif part not in ("", "."):
                depth += 1
            if depth < 0:
                return None
        try:
            path_parts(posixpath.normpath(raw))
            reference = root.joinpath(*raw.split("/"))
            check_links(reference)
            targets = [name for name in expected if reference.samefile(root / name)]
        except (FileNotFoundError, ValueError):
            return None
        if len(targets) != 1:
            return None
        normalized.append(targets[0])
    return normalized


def matches(actual, expected, root):
    # Extra explanation fields in the top-level output object are permitted.
    if not isinstance(actual, dict) or not isinstance(expected, dict):
        return False
    for key, value in expected.items():
        if key not in actual:
            return False
        observed = actual[key]
        if key == "files":
            # The manifest requests relative file references, not one spelling.
            observed = manifest_references(observed, value, root)
            if observed is None:
                return False
        if canonical(observed) != canonical(value):
            return False
    return True


def grade(case, stage_name, workspace, suite_sha):
    if stage_name not in case["stages"]:
        raise ValueError("unknown stage")
    root = Path(workspace).absolute()
    check_links(root)
    checks = []
    for relative, expected_text in case["inputs"].items():
        row = {"kind": "input-bytes", "path": relative}
        try:
            data = read_file(root, relative)
            row.update(state="pass" if data == expected_text.encode("utf-8") else "fail",
                       sha256=digest(data))
        except FileNotFoundError:
            row.update(state="fail", reason="required-input-missing")
        except (OSError, ValueError):
            row.update(state="unknown", reason="input-unreadable-or-invalid")
        checks.append(row)
    stage = case["stages"][stage_name]
    for relative, expected in stage["outputs"].items():
        row = {"kind": "output-content", "path": relative}
        try:
            data = read_file(root, relative)
        except FileNotFoundError:
            row.update(state="fail", reason="required-output-missing")
        except (OSError, ValueError):
            row.update(state="unknown", reason="output-unreadable-or-unsafe")
        else:
            row["sha256"] = digest(data)
            try:
                actual = strict_json(data.decode("utf-8-sig"))
                row["state"] = "pass" if matches(actual, expected, root) else "fail"
            except (UnicodeError, ValueError):
                row.update(state="fail", reason="output-format-invalid")
            except RecursionError:
                row.update(state="unknown", reason="grader-depth-limit")
            except OSError:
                row.update(state="unknown", reason="output-reference-unreadable")
        checks.append(row)
    counts = dict(Counter(row["state"] for row in checks))
    return {"schema": "accord-comparison-file-observation/v1", "case": case["id"],
            "stage": stage_name, "suiteSha256": suite_sha,
            "fileCriteria": "pass" if all(row["state"] == "pass" for row in checks) else "not-passed",
            "checks": checks, "counts": counts,
            "manualReview": stage["manualReview"],
            "runValidity": "unverified", "taskOutcome": "unverified", "incrementalValue": "unverified",
            "claimLimit": "File facts only. Review actual inputs, behavior, environment, costs and resource exit separately."}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("prepare", "grade"))
    parser.add_argument("--case", required=True)
    parser.add_argument("--workspace", required=True)
    parser.add_argument("--stage", default="final")
    args = parser.parse_args()
    try:
        suite, suite_sha = load_suite()
        case = select_case(suite, args.case)
        result = (prepare(case, args.workspace) if args.action == "prepare" else
                  grade(case, args.stage, args.workspace, suite_sha))
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if args.action == "prepare" or result["fileCriteria"] == "pass" else 1
    except (OSError, ValueError, KeyError, TypeError, UnicodeError) as exc:
        print(json.dumps({"state": "operation-rejected", "errorType": type(exc).__name__,
                          "claimLimit": "No completion or comparison conclusion."}))
        return 2


if __name__ == "__main__":
    sys.exit(main())
