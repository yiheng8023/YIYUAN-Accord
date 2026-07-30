from __future__ import annotations

import copy
import hashlib
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from scripts.preflight_cc_switch_fourteen_skill_subtraction import (
    SAFE_SKILL_COLUMNS,
    _tree_identity,
    capture_live_state,
    validate_contract_document,
    validate_live_state,
)


TARGETS = [
    "design-an-interface",
    "edit-article",
    "qa",
    "request-refactor-plan",
    "review",
    "setup-pre-commit",
    "setup-project-skills",
    "to-issues",
    "to-prd",
    "ubiquitous-language",
    "writing-beats",
    "writing-fragments",
    "writing-shape",
    "zoom-out",
]
FIRST_PARTY = ["intent-contract", "capability-router", "closure-contract"]
MATT = [
    "ask-matt",
    "code-review",
    "codebase-design",
    "diagnosing-bugs",
    "domain-modeling",
    "grill-me",
    "grill-with-docs",
    "grilling",
    "handoff",
    "implement",
    "improve-codebase-architecture",
    "prototype",
    "research",
    "resolving-merge-conflicts",
    "setup-matt-pocock-skills",
    "tdd",
    "teach",
    "to-spec",
    "to-tickets",
    "triage",
    "wayfinder",
    "writing-great-skills",
]


def row(name: str, *, owner: str | None = None) -> dict[str, object]:
    values: dict[str, object] = {column: None for column in SAFE_SKILL_COLUMNS}
    values.update(
        {
            "id": f"fixture:{name}",
            "name": name,
            "description": "fixture",
            "directory": name,
            "repo_owner": owner,
            "repo_name": "skills" if owner else None,
            "repo_branch": "main" if owner else None,
            "enabled_claude": 1,
            "enabled_codex": 1,
            "enabled_gemini": 0,
            "enabled_opencode": 0,
            "enabled_hermes": 0,
            "enabled_grokbuild": 0,
            "content_hash": f"db-{name}",
        }
    )
    return values


def tree(name: str) -> dict[str, object]:
    return {
        "fileCount": 1,
        "bytes": len(name),
        "treeManifestSha256": f"tree-{name}",
        "files": [],
    }


def make_documents() -> tuple[
    dict[str, object],
    dict[str, object],
    dict[str, object],
    dict[str, object],
    dict[str, object],
]:
    extras = [f"other-{index:02d}" for index in range(13)]
    names = TARGETS + FIRST_PARTY + MATT + ["doc", "pdf", "diagnose"] + extras
    rows = [row(name, owner="mattpocock" if name in MATT else None) for name in names]
    cc_trees = {name: tree(name) for name in names}
    projections: dict[str, object] = {}
    for root_name in ("ccSwitch", "agents", "claude", "codex"):
        entries: dict[str, object] = {}
        for name in names:
            if root_name == "codex" and name in {"doc", "pdf"}:
                continue
            if root_name == "ccSwitch":
                kind = "physical"
                path = f"C:/fixture/.cc-switch/skills/{name}"
                target = None
            elif name in FIRST_PARTY and root_name in {"agents", "codex"}:
                kind = "physical"
                path = f"C:/fixture/.{root_name}/skills/{name}"
                target = None
            else:
                kind = "symlink"
                path = f"C:/fixture/.{root_name}/skills/{name}"
                target = f"C:/fixture/.cc-switch/skills/{name}"
            entries[name] = {
                "path": path,
                "kind": kind,
                "resolvedTarget": target,
                "resolvableDirectory": True,
                "skillMdResolvable": True,
                "fileCount": 1,
                "bytes": len(name),
                "treeManifestSha256": f"tree-{name}",
            }
        projections[root_name] = {
            "entryCount": len(entries),
            "entries": entries,
        }
    evicted = [f"old-{index:02d}" for index in range(14)]
    retained = [f"keep-{index:02d}" for index in range(6)]
    state: dict[str, object] = {
        "schema": 1,
        "managerBinary": {
            "path": "C:/fixture/cc-switch.exe",
            "bytes": 100,
            "sha256": "a" * 64,
        },
        "settings": {
            "skillStorageLocation": "cc_switch",
            "skillSyncMethod": "symlink",
            "skillPathOverrideKeys": [],
        },
        "database": {
            "rowCount": 55,
            "distinctNames": 55,
            "rows": rows,
        },
        "ccTrees": cc_trees,
        "projections": projections,
        "backups": {
            "count": 20,
            "orderedIds": evicted + retained,
            "items": [],
        },
        "codexSkillConfig": {
            "docPdfRows": [
                {
                    "path": "C:/fixture/.agents/skills/doc/SKILL.md",
                    "enabled": False,
                },
                {
                    "path": "C:/fixture/.agents/skills/pdf/SKILL.md",
                    "enabled": False,
                },
            ]
        },
        "fingerprints": {
            "managerBinary": "1" * 64,
            "settings": "2" * 64,
            "database": "3" * 64,
            "ccTrees": "4" * 64,
            "projections": "5" * 64,
            "backups": "6" * 64,
            "codexSkillConfig": "7" * 64,
            "wholeState": "8" * 64,
        },
    }
    refresh: dict[str, object] = {
        "manager": {
            "binaryPath": "C:/fixture/cc-switch.exe",
            "binaryBytes": 100,
            "binarySha256": "a" * 64,
        },
        "livePreState": {
            "databaseRows": 55,
            "databaseDistinctNames": 55,
        },
        "candidateCohort": {
            "items": [
                {
                    "name": name,
                    "dbContentHash": f"db-{name}",
                    "fileCount": 1,
                    "bytes": len(name),
                    "currentTreeManifestSha256": f"tree-{name}",
                }
                for name in TARGETS
            ]
        },
        "backupRotation": {
            "currentBackupCount": 20,
            "expectedEvictedBackupIds": evicted,
            "expectedRetainedExistingBackupIds": retained,
        },
    }
    first_party: dict[str, object] = {
        "packages": [
            {
                "name": name,
                "currentSourceProjection": {
                    "treeManifestSha256": f"tree-{name}",
                },
            }
            for name in FIRST_PARTY
        ]
    }
    portfolio: dict[str, object] = {
        "portfolioPartition": {
            "cohorts": [
                {
                    "id": "current-matt-promoted-exact",
                    "names": MATT,
                }
            ]
        }
    }
    contract: dict[str, object] = {
        "schema": 1,
        "id": "cc-switch-fourteen-skill-live-preflight-contract-2026-07-30",
        "status": "read-only-fail-closed-preflight-ready",
        "mutationAuthority": {
            "ccSwitchMutation": False,
            "hostProjectionMutation": False,
            "recoveryArchiveCreation": False,
            "remoteSnapshot": False,
            "gitCommitOrPush": False,
        },
        "expectedFingerprints": copy.deepcopy(state["fingerprints"]),
        "failClosedOnAnyWholeStateDrift": True,
        "pointInTimeCheckNotTransactionLock": True,
        "mustRerunImmediatelyBeforeCanary": True,
        "authorizesUninstall": False,
    }
    return state, contract, refresh, first_party, portfolio


class CcSwitchFourteenSkillLivePreflightTests(unittest.TestCase):
    def test_synthetic_current_state_passes(self) -> None:
        state, contract, refresh, first_party, portfolio = make_documents()
        result = validate_live_state(
            state,
            contract=contract,
            refresh=refresh,
            first_party=first_party,
            portfolio=portfolio,
        )
        self.assertEqual(result["status"], "pass")
        self.assertFalse(result["authorizesMutation"])

    def test_rejects_whole_state_fingerprint_drift(self) -> None:
        state, contract, refresh, first_party, portfolio = make_documents()
        state["fingerprints"]["database"] = "f" * 64
        with self.assertRaisesRegex(RuntimeError, "whole live Skill state"):
            validate_live_state(
                state,
                contract=contract,
                refresh=refresh,
                first_party=first_party,
                portfolio=portfolio,
            )

    def test_rejects_target_tree_drift(self) -> None:
        state, contract, refresh, first_party, portfolio = make_documents()
        refresh["candidateCohort"]["items"][0]["currentTreeManifestSha256"] = "drift"
        with self.assertRaisesRegex(RuntimeError, "target CC tree"):
            validate_live_state(
                state,
                contract=contract,
                refresh=refresh,
                first_party=first_party,
                portfolio=portfolio,
            )

    def test_rejects_backup_eviction_order_drift(self) -> None:
        state, contract, refresh, first_party, portfolio = make_documents()
        state["backups"]["orderedIds"][0:2] = reversed(
            state["backups"]["orderedIds"][0:2]
        )
        contract["expectedFingerprints"] = copy.deepcopy(state["fingerprints"])
        with self.assertRaisesRegex(RuntimeError, "eviction order"):
            validate_live_state(
                state,
                contract=contract,
                refresh=refresh,
                first_party=first_party,
                portfolio=portfolio,
            )

    def test_rejects_first_party_physical_sentinel_drift(self) -> None:
        state, contract, refresh, first_party, portfolio = make_documents()
        state["projections"]["codex"]["entries"]["intent-contract"][
            "kind"
        ] = "symlink"
        contract["expectedFingerprints"] = copy.deepcopy(state["fingerprints"])
        with self.assertRaisesRegex(RuntimeError, "first-party physical sentinel"):
            validate_live_state(
                state,
                contract=contract,
                refresh=refresh,
                first_party=first_party,
                portfolio=portfolio,
            )

    def test_rejects_matt_promoted_set_drift(self) -> None:
        state, contract, refresh, first_party, portfolio = make_documents()
        next(
            row
            for row in state["database"]["rows"]
            if row["name"] == "ask-matt"
        )["repo_owner"] = None
        contract["expectedFingerprints"] = copy.deepcopy(state["fingerprints"])
        with self.assertRaisesRegex(RuntimeError, "Matt promoted"):
            validate_live_state(
                state,
                contract=contract,
                refresh=refresh,
                first_party=first_party,
                portfolio=portfolio,
            )

    def test_rejects_doc_pdf_policy_drift(self) -> None:
        state, contract, refresh, first_party, portfolio = make_documents()
        state["codexSkillConfig"]["docPdfRows"][0]["enabled"] = True
        contract["expectedFingerprints"] = copy.deepcopy(state["fingerprints"])
        with self.assertRaisesRegex(RuntimeError, "doc/pdf disable-policy"):
            validate_live_state(
                state,
                contract=contract,
                refresh=refresh,
                first_party=first_party,
                portfolio=portfolio,
            )

    def test_tree_identity_uses_case_insensitive_path_order(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "SKILL.md").write_bytes(b"upper")
            (root / "domain.md").write_bytes(b"lower")
            records = [
                ("domain.md", b"lower"),
                ("SKILL.md", b"upper"),
            ]
            lines = [
                path.encode("utf-8")
                + b"\0"
                + str(len(content)).encode("ascii")
                + b"\0"
                + hashlib.sha256(content).hexdigest().encode("ascii")
                for path, content in records
            ]
            expected = hashlib.sha256(b"\n".join(lines)).hexdigest()
            self.assertEqual(_tree_identity(root)["treeManifestSha256"], expected)

    def test_capture_reads_without_mutating_fixture(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            home = Path(temporary)
            for relative in (
                ".cc-switch/skills",
                ".cc-switch/skill-backups/backup-1",
                ".agents/skills",
                ".claude/skills",
                ".codex/skills",
            ):
                (home / relative).mkdir(parents=True)
            skill = home / ".cc-switch/skills/fixture"
            skill.mkdir()
            (skill / "SKILL.md").write_text("# fixture\n", encoding="utf-8")
            backup = home / ".cc-switch/skill-backups/backup-1"
            (backup / "meta.json").write_text("{}", encoding="utf-8")
            (home / ".cc-switch/settings.json").write_text(
                json.dumps(
                    {
                        "skillStorageLocation": "cc_switch",
                        "skillSyncMethod": "symlink",
                    }
                ),
                encoding="utf-8",
            )
            (home / ".codex/config.toml").write_text("", encoding="utf-8")
            binary = home / "cc-switch.exe"
            binary.write_bytes(b"fixture")
            database = home / ".cc-switch/cc-switch.db"
            connection = sqlite3.connect(database)
            columns = ",".join(f"{name} text" for name in SAFE_SKILL_COLUMNS)
            connection.execute(f"create table skills ({columns})")
            connection.commit()
            connection.close()
            before = {
                path.relative_to(home).as_posix(): hashlib.sha256(
                    path.read_bytes()
                ).hexdigest()
                for path in home.rglob("*")
                if path.is_file()
            }
            state = capture_live_state(home, binary)
            after = {
                path.relative_to(home).as_posix(): hashlib.sha256(
                    path.read_bytes()
                ).hexdigest()
                for path in home.rglob("*")
                if path.is_file()
            }
            self.assertEqual(before, after)
            self.assertEqual(state["database"]["rowCount"], 0)
            validate_contract_document(make_documents()[1])


if __name__ == "__main__":
    unittest.main()
