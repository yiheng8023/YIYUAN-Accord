#!/usr/bin/env python3
"""Falsify a proposed inactive CC Switch install transaction in a disposable home.

This is a repository-owned evidence instrument. It does not invoke CC Switch,
download or execute a candidate, or mutate a real Agent consumer root.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil
import tempfile
from typing import Any


class TransactionRejected(RuntimeError):
    pass


class SimulatedCrash(RuntimeError):
    pass


def _write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".new")
    temporary.write_text(
        json.dumps(value, ensure_ascii=False, sort_keys=True), encoding="utf-8"
    )
    os.replace(temporary, path)


def _tree_digest(root: Path) -> str | None:
    if not root.exists():
        return None
    digest = hashlib.sha256()
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        relative = path.relative_to(root).as_posix().encode("utf-8")
        data = path.read_bytes()
        digest.update(len(relative).to_bytes(8, "big"))
        digest.update(relative)
        digest.update(len(data).to_bytes(8, "big"))
        digest.update(data)
    return digest.hexdigest()


def _snapshot(root: Path) -> dict[str, str | None]:
    return {
        "manager": hashlib.sha256((root / "manager.json").read_bytes()).hexdigest(),
        "ssot": _tree_digest(root / "cc-switch" / "skills"),
        "codex": _tree_digest(root / "consumers" / "codex" / "skills"),
        "claude": _tree_digest(root / "consumers" / "claude" / "skills"),
    }


def _fixture(root: Path) -> tuple[list[dict[str, Any]], dict[str, str]]:
    candidates = [
        {
            "id": "candidate.alpha",
            "directory": "alpha",
            "dependencies": [],
            "files": {
                "SKILL.md": "---\nname: alpha\ndescription: alpha\n---\n",
                "references/method.md": "alpha method\n",
            },
        },
        {
            "id": "candidate.beta",
            "directory": "beta",
            "dependencies": ["candidate.alpha"],
            "files": {
                "SKILL.md": "---\nname: beta\ndescription: beta\n---\n",
            },
        },
    ]
    for candidate in candidates:
        source = root / "acquisition" / candidate["id"]
        for relative, content in candidate["files"].items():
            target = source / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")

    (root / "cc-switch" / "skills").mkdir(parents=True)
    for host in ("codex", "claude"):
        sentinel = root / "consumers" / host / "skills" / "sentinel" / "SKILL.md"
        sentinel.parent.mkdir(parents=True)
        sentinel.write_text(f"{host} sentinel\n", encoding="utf-8")
    _write_json(root / "manager.json", {"schema": 1, "skills": {}})
    expected = {
        candidate["id"]: _tree_digest(root / "acquisition" / candidate["id"])
        for candidate in candidates
    }
    return candidates, expected  # type: ignore[return-value]


def _validate(
    root: Path,
    candidates: list[dict[str, Any]],
    expected: dict[str, str],
    requested_apps: list[str],
) -> None:
    if requested_apps:
        raise TransactionRejected("inactive install requires an empty app set")
    ids = [candidate["id"] for candidate in candidates]
    directories = [candidate["directory"] for candidate in candidates]
    if len(ids) != len(set(ids)) or len(directories) != len(set(directories)):
        raise TransactionRejected("candidate identity or directory collision")
    manager = json.loads((root / "manager.json").read_text(encoding="utf-8"))
    for candidate in candidates:
        candidate_id = candidate["id"]
        directory = candidate["directory"]
        if (
            not isinstance(directory, str)
            or not directory
            or directory in {".", ".."}
            or "/" in directory
            or "\\" in directory
        ):
            raise TransactionRejected("unsafe install directory")
        if candidate_id in manager["skills"]:
            raise TransactionRejected("existing manager identity requires a separate update")
        if (root / "cc-switch" / "skills" / directory).exists():
            raise TransactionRejected("existing SSOT directory requires a separate update")
        if any(dependency not in ids for dependency in candidate["dependencies"]):
            raise TransactionRejected("dependency closure is incomplete")
        source = root / "acquisition" / candidate_id
        if not (source / "SKILL.md").is_file():
            raise TransactionRejected("candidate entrypoint is missing")
        if _tree_digest(source) != expected.get(candidate_id):
            raise TransactionRejected("candidate digest does not match the reviewed source")


def recover(root: Path) -> bool:
    transaction = root / "transaction"
    journal_path = transaction / "journal.json"
    if not journal_path.is_file():
        return False
    journal = json.loads(journal_path.read_text(encoding="utf-8"))
    for directory in reversed(journal.get("moved", [])):
        target = root / "cc-switch" / "skills" / directory
        if target.exists():
            shutil.rmtree(target)
    backup = transaction / "manager.before.json"
    if backup.is_file():
        shutil.copyfile(backup, root / "manager.json")
    shutil.rmtree(transaction)
    return True


def install_inactive_batch(
    root: Path,
    candidates: list[dict[str, Any]],
    expected: dict[str, str],
    *,
    requested_apps: list[str] | None = None,
    fault: str | None = None,
) -> dict[str, Any]:
    requested_apps = [] if requested_apps is None else requested_apps
    _validate(root, candidates, expected, requested_apps)
    transaction = root / "transaction"
    if transaction.exists():
        raise TransactionRejected("unfinished transaction requires recovery")
    stage = transaction / "stage"
    stage.mkdir(parents=True)
    shutil.copyfile(root / "manager.json", transaction / "manager.before.json")
    consumer_before = {
        host: _tree_digest(root / "consumers" / host / "skills")
        for host in ("codex", "claude")
    }
    try:
        for index, candidate in enumerate(candidates):
            source = root / "acquisition" / candidate["id"]
            staged = stage / candidate["directory"]
            if index == 1 and fault == "during-second-stage":
                raise TransactionRejected("injected failure during second staging copy")
            shutil.copytree(source, staged)
            if _tree_digest(staged) != expected[candidate["id"]]:
                raise TransactionRejected("staged candidate digest drifted")
    except Exception:
        shutil.rmtree(transaction)
        raise
    journal = {
        "schema": 1,
        "phase": "prepared",
        "moved": [],
        "consumerDigests": consumer_before,
    }
    _write_json(transaction / "journal.json", journal)

    try:
        if fault == "after-prepare":
            raise TransactionRejected("injected failure after preparation")
        for index, candidate in enumerate(candidates):
            directory = candidate["directory"]
            os.replace(stage / directory, root / "cc-switch" / "skills" / directory)
            journal["moved"].append(directory)
            journal["phase"] = "ssot-moved"
            _write_json(transaction / "journal.json", journal)
            if index == 0 and fault == "after-first-move-error":
                raise TransactionRejected("injected failure after first SSOT move")
            if index == 0 and fault == "after-first-move-crash":
                raise SimulatedCrash("injected crash after first SSOT move")

        manager = json.loads((root / "manager.json").read_text(encoding="utf-8"))
        for candidate in candidates:
            manager["skills"][candidate["id"]] = {
                "directory": candidate["directory"],
                "digest": expected[candidate["id"]],
                "apps": {
                    "claude": False,
                    "codex": False,
                    "gemini": False,
                    "opencode": False,
                    "hermes": False,
                },
            }
        _write_json(root / "manager.json", manager)
        journal["phase"] = "database-replaced"
        _write_json(transaction / "journal.json", journal)
        if fault == "after-database-error":
            raise TransactionRejected("injected failure after database replacement")
        if fault == "after-database-crash":
            raise SimulatedCrash("injected crash after database replacement")

        for host, digest in consumer_before.items():
            if _tree_digest(root / "consumers" / host / "skills") != digest:
                raise TransactionRejected("inactive install touched a consumer root")
        for candidate in candidates:
            row = manager["skills"][candidate["id"]]
            if any(row["apps"].values()):
                raise TransactionRejected("installed row is not default-disabled")
            if (
                _tree_digest(root / "cc-switch" / "skills" / candidate["directory"])
                != expected[candidate["id"]]
            ):
                raise TransactionRejected("installed SSOT bytes drifted")
        shutil.rmtree(transaction)
        return {"installed": len(candidates), "appsEnabled": 0}
    except SimulatedCrash:
        raise
    except Exception:
        recover(root)
        raise


def _run_case(name: str) -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="aah-cc-switch-inactive-") as temporary:
        root = Path(temporary)
        candidates, expected = _fixture(root)
        fault = None
        requested_apps: list[str] = []
        expected_outcome = "rejected-restored"

        if name == "success-two-candidate-batch":
            expected_outcome = "installed-inactive"
        elif name == "reject-nonempty-app-set":
            requested_apps = ["codex"]
        elif name == "reject-first-source-digest-drift":
            (root / "acquisition" / candidates[0]["id"] / "SKILL.md").write_text(
                "tampered\n", encoding="utf-8"
            )
        elif name == "reject-missing-entrypoint":
            (root / "acquisition" / candidates[0]["id"] / "SKILL.md").unlink()
        elif name == "reject-missing-dependency":
            candidates[1]["dependencies"] = ["candidate.missing"]
        elif name == "reject-duplicate-directory":
            candidates[1]["directory"] = candidates[0]["directory"]
        elif name == "reject-existing-manager-row":
            manager = json.loads((root / "manager.json").read_text(encoding="utf-8"))
            manager["skills"][candidates[0]["id"]] = {"apps": {"codex": True}}
            _write_json(root / "manager.json", manager)
        elif name == "reject-existing-ssot-directory":
            existing = root / "cc-switch" / "skills" / candidates[0]["directory"]
            existing.mkdir()
            (existing / "SKILL.md").write_text("existing\n", encoding="utf-8")
        elif name == "reject-second-source-before-write":
            (root / "acquisition" / candidates[1]["id"] / "SKILL.md").write_text(
                "second drift\n", encoding="utf-8"
            )
        elif name == "cleanup-after-second-stage-error":
            fault = "during-second-stage"
        elif name == "rollback-after-prepare-error":
            fault = "after-prepare"
        elif name == "rollback-after-first-move-error":
            fault = "after-first-move-error"
        elif name == "recover-after-first-move-crash":
            fault = "after-first-move-crash"
            expected_outcome = "crash-recovered"
        elif name == "rollback-after-database-error":
            fault = "after-database-error"
        elif name == "recover-after-database-crash":
            fault = "after-database-crash"
            expected_outcome = "crash-recovered"
        else:
            raise AssertionError(f"unknown case: {name}")

        before = _snapshot(root)
        outcome = ""
        installed = None
        try:
            installed = install_inactive_batch(
                root,
                candidates,
                expected,
                requested_apps=requested_apps,
                fault=fault,
            )
            outcome = "installed-inactive"
        except SimulatedCrash:
            recovered = recover(root)
            outcome = "crash-recovered" if recovered else "crash-unrecovered"
        except TransactionRejected:
            outcome = "rejected-restored"

        after = _snapshot(root)
        restored = before == after
        consumers_unchanged = (
            before["codex"] == after["codex"]
            and before["claude"] == after["claude"]
        )
        rows_disabled = True
        if installed is not None:
            manager = json.loads((root / "manager.json").read_text(encoding="utf-8"))
            rows_disabled = all(
                not any(row["apps"].values()) for row in manager["skills"].values()
            )
        passed = (
            outcome == expected_outcome
            and consumers_unchanged
            and rows_disabled
            and (outcome == "installed-inactive" or restored)
            and not (root / "transaction").exists()
        )
        return {
            "id": name,
            "outcome": outcome,
            "passed": passed,
            "preStateRestored": restored if outcome != "installed-inactive" else None,
            "consumerRootsUnchanged": consumers_unchanged,
            "rowsDefaultDisabled": rows_disabled,
        }


def run_failure_matrix() -> dict[str, Any]:
    names = [
        "success-two-candidate-batch",
        "reject-nonempty-app-set",
        "reject-first-source-digest-drift",
        "reject-missing-entrypoint",
        "reject-missing-dependency",
        "reject-duplicate-directory",
        "reject-existing-manager-row",
        "reject-existing-ssot-directory",
        "reject-second-source-before-write",
        "cleanup-after-second-stage-error",
        "rollback-after-prepare-error",
        "rollback-after-first-move-error",
        "recover-after-first-move-crash",
        "rollback-after-database-error",
        "recover-after-database-crash",
    ]
    cases = [_run_case(name) for name in names]
    failures = [case for case in cases if case["outcome"] != "installed-inactive"]
    return {
        "caseCount": len(cases),
        "passedCaseCount": sum(case["passed"] for case in cases),
        "cases": cases,
        "allFailureCasesRestoredPreState": all(
            case["preStateRestored"] is True for case in failures
        ),
        "allSuccessRowsDefaultDisabled": all(
            case["rowsDefaultDisabled"] for case in cases
        ),
        "allConsumerRootsUnchanged": all(
            case["consumerRootsUnchanged"] for case in cases
        ),
        "freshRecoveryProcessSimulated": all(
            any(case["id"] == expected and case["outcome"] == "crash-recovered" for case in cases)
            for expected in (
                "recover-after-first-move-crash",
                "recover-after-database-crash",
            )
        ),
        "liveManagerInvocations": 0,
        "candidateExecutions": 0,
        "modelCalls": 0,
        "networkCalls": 0,
    }


def main() -> int:
    print(json.dumps(run_failure_matrix(), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
