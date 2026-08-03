from __future__ import annotations

import copy
from datetime import UTC, datetime
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from scripts.revalidate_skill_ablation_host_transaction import (
    BLOCKED_STATUS,
    MATCH_STATUS,
    _validate_revalidation_report_against_digest,
    build_revalidation_report,
    canonical_sha256,
    validate_revalidation_report,
)


def sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def build_contract(root: Path) -> tuple[dict, Path, list[Path], Path]:
    config = root / "config.toml"
    config.write_bytes(b'model = "example"\n')
    targets: list[Path] = []
    target_rows = []
    for name in ("intent-contract", "capability-router"):
        path = root / name / "SKILL.md"
        path.parent.mkdir()
        path.write_text(f"# {name}\n", encoding="utf-8")
        targets.append(path)
        target_rows.append(
            {
                "name": name,
                "path": path.as_posix(),
                "sha256": sha256(path.read_bytes()),
            }
        )
    backup = root / "config.toml.preflight.bak"
    contract = {
        "id": "skill-ablation-host-config-transaction-2026-07-19",
        "date": "2026-07-19",
        "observedBaseline": {
            "configPath": config.as_posix(),
            "sha256": sha256(config.read_bytes()),
            "lengthBytes": config.stat().st_size,
            "skillsConfigEntryCount": 0,
        },
        "targets": target_rows,
        "transaction": {"backupPath": backup.as_posix()},
    }
    return contract, config, targets, backup


class SkillAblationHostTransactionRevalidationTests(unittest.TestCase):
    def contract_sha256(self, contract: dict) -> str:
        return canonical_sha256(contract)

    def build_report(self, contract: dict, contract_path: Path) -> dict:
        return build_revalidation_report(
            contract,
            contract_path=contract_path,
            contract_sha256=self.contract_sha256(contract),
            clock=lambda: datetime(2026, 7, 24, tzinfo=UTC),
        )

    def validate(self, report: dict, contract: dict) -> list[str]:
        return _validate_revalidation_report_against_digest(
            report,
            contract,
            expected_contract_sha256=self.contract_sha256(contract),
        )

    def test_matching_preconditions_still_require_authorization(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            contract, _, _, _ = build_contract(root)

            report = self.build_report(contract, root / "contract.json")

            self.assertEqual(MATCH_STATUS, report["status"])
            self.assertEqual([], report["driftReasons"])
            self.assertEqual([], self.validate(report, contract))
            self.assertTrue(all(report["comparison"].values()))
            self.assertTrue(
                all(value is False for value in report["claimBoundary"].values())
            )

    def test_config_drift_blocks_and_does_not_emit_secret_content(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            contract, config, _, _ = build_contract(root)
            secret = "sk-proj-this-must-never-be-recorded"
            config.write_text(f'token = "{secret}"\n', encoding="utf-8")

            report = self.build_report(contract, root / "contract.json")
            encoded = json.dumps(report, sort_keys=True)

            self.assertEqual(BLOCKED_STATUS, report["status"])
            self.assertIn("config-sha256-drift", report["driftReasons"])
            self.assertNotIn(secret, encoded)
            self.assertFalse(report["contentBoundary"]["configContentIncluded"])
            self.assertEqual([], self.validate(report, contract))

    def test_target_drift_and_missing_target_are_both_blocking(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            contract, _, targets, _ = build_contract(root)
            targets[0].write_text("# drift\n", encoding="utf-8")
            targets[1].unlink()

            report = self.build_report(contract, root / "contract.json")

            self.assertEqual(BLOCKED_STATUS, report["status"])
            self.assertIn("target-missing", report["driftReasons"])
            self.assertIn("target-sha256-drift", report["driftReasons"])
            self.assertEqual([], self.validate(report, contract))

    def test_existing_prepared_backup_blocks_reuse(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            contract, _, _, backup = build_contract(root)
            backup.write_text("existing", encoding="utf-8")

            report = self.build_report(contract, root / "contract.json")

            self.assertEqual(BLOCKED_STATUS, report["status"])
            self.assertIn(
                "prepared-backup-already-exists",
                report["driftReasons"],
            )
            self.assertEqual([], self.validate(report, contract))

    def test_validator_rejects_claim_promotion(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            contract, _, _, _ = build_contract(root)
            report = self.build_report(contract, root / "contract.json")
            report["claimBoundary"]["countsAsSkillDisablement"] = True
            report["reportSha256"] = canonical_sha256(
                {
                    key: value
                    for key, value in report.items()
                    if key != "reportSha256"
                }
            )

            self.assertIn(
                "hard-fail-claim-promotion",
                self.validate(report, contract),
            )

    def test_validator_rejects_report_digest_drift(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            contract, _, _, _ = build_contract(root)
            report = self.build_report(contract, root / "contract.json")
            report["observedAt"] = "2026-07-25T00:00:00+00:00"

            self.assertIn(
                "fail-report-digest",
                self.validate(report, contract),
            )

    def test_validator_rejects_self_consistent_wrong_source_digest(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            contract, _, _, _ = build_contract(root)
            report = self.build_report(contract, root / "contract.json")
            report["sourceContract"]["sha256"] = "0" * 64
            report["reportSha256"] = canonical_sha256(
                {
                    key: value
                    for key, value in report.items()
                    if key != "reportSha256"
                }
            )

            self.assertIn(
                "fail-source-contract-binding",
                self.validate(report, contract),
            )

    def test_production_validator_rejects_noncanonical_contract(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            contract, _, _, _ = build_contract(root)
            report = self.build_report(contract, root / "contract.json")

            self.assertEqual(
                ["fail-source-contract-binding"],
                validate_revalidation_report(report, contract),
            )

    def test_production_validator_rejects_false_provenance_path(self) -> None:
        contract_path = (
            Path(__file__).resolve().parents[1]
            / "registry"
            / "skill-ablation-host-config-transaction-2026-07-19.json"
        )
        contract_bytes = contract_path.read_bytes()
        contract = json.loads(contract_bytes.decode("utf-8"))
        report = build_revalidation_report(
            contract,
            contract_path=contract_path,
            contract_sha256=sha256(contract_bytes),
            clock=lambda: datetime(2026, 7, 24, tzinfo=UTC),
        )
        report["sourceContract"]["path"] = "C:/copied-or-untrusted/contract.json"
        report["reportSha256"] = canonical_sha256(
            {
                key: value
                for key, value in report.items()
                if key != "reportSha256"
            }
        )

        self.assertEqual(
            ["fail-source-contract-binding"],
            validate_revalidation_report(report, contract),
        )

    def test_recorded_capture_path_is_portable_to_current_worktree(self) -> None:
        root = Path(__file__).resolve().parents[1]
        contract = json.loads(
            (root / "registry/skill-ablation-host-config-transaction-2026-07-19.json")
            .read_text(encoding="utf-8")
        )
        report = json.loads(
            (root / "registry/skill-ablation-host-transaction-revalidation-2026-07-24.json")
            .read_text(encoding="utf-8")
        )
        self.assertEqual([], validate_revalidation_report(report, contract))

    def test_semantic_toml_count_accepts_header_with_trailing_comment(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            contract, config, _, _ = build_contract(root)
            config.write_text(
                '[[skills.config]] # semantic entry\n'
                'path = "C:/example/SKILL.md"\n',
                encoding="utf-8",
            )
            contract["observedBaseline"].update(
                {
                    "sha256": sha256(config.read_bytes()),
                    "lengthBytes": config.stat().st_size,
                    "skillsConfigEntryCount": 1,
                }
            )

            report = self.build_report(contract, root / "contract.json")

            self.assertTrue(report["configObservation"]["tomlParseComplete"])
            self.assertEqual(
                1,
                report["configObservation"]["skillsConfigEntryCount"],
            )
            self.assertEqual([], self.validate(report, contract))

    def test_validator_rejects_atomic_snapshot_claim(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            contract, _, _, _ = build_contract(root)
            report = self.build_report(contract, root / "contract.json")
            report["cohortBoundary"]["atomicSnapshotProved"] = True
            report["reportSha256"] = canonical_sha256(
                {
                    key: value
                    for key, value in report.items()
                    if key != "reportSha256"
                }
            )

            self.assertIn(
                "hard-fail-cohort-boundary",
                self.validate(report, contract),
            )


if __name__ == "__main__":
    unittest.main()
