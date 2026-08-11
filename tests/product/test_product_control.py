from __future__ import annotations

import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]


class ProductControlCliTests(unittest.TestCase):
    def run_verify(self, root: Path) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [
                sys.executable,
                "-B",
                "-m",
                "harness",
                "verify",
                "--root",
                str(root),
                "--json",
            ],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )

    def test_current_repository_exposes_one_product_progress_report(self) -> None:
        result = self.run_verify(ROOT)

        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
        report = json.loads(result.stdout)
        self.assertTrue(report["valid"])
        self.assertEqual(report["productId"], "agent-autonomy-harness")
        self.assertEqual(report["release"], "v0.1")
        self.assertEqual(
            report["activeIncrement"],
            "increment.context-continuity-product-slice",
        )
        self.assertEqual(report["outcomes"], {"total": 5, "verified": 3})
        self.assertEqual(report["guardrails"], {"total": 4, "passed": 4})
        self.assertEqual(report["completionState"], "in-progress")

    def test_unmapped_work_is_rejected_at_the_product_seam(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary)
            shutil.copytree(ROOT / "product", target / "product")
            program_path = target / "product" / "program.json"
            program = json.loads(program_path.read_text(encoding="utf-8"))
            program["increments"][0]["workItems"].append(
                {
                    "id": "work.unmapped",
                    "state": "planned",
                    "acceptanceIds": [],
                    "deliverables": ["nowhere"],
                }
            )
            program_path.write_text(
                json.dumps(program, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )

            result = self.run_verify(target)

        self.assertNotEqual(result.returncode, 0)
        report = json.loads(result.stdout)
        self.assertIn(
            "work item work.unmapped must map to at least one acceptance criterion",
            report["errors"],
        )

    def test_predecessor_identity_is_rejected_from_active_product_authority(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary)
            shutil.copytree(ROOT / "product", target / "product")
            program_path = target / "product" / "program.json"
            program = json.loads(program_path.read_text(encoding="utf-8"))
            predecessor_identity = "agent" + "-skills" + "-curated"
            program["purpose"] = f"{predecessor_identity} compatibility mode"
            program_path.write_text(
                json.dumps(program, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )

            result = self.run_verify(target)

        self.assertNotEqual(result.returncode, 0)
        report = json.loads(result.stdout)
        self.assertIn(
            "active product authority contains a forbidden predecessor identity",
            report["errors"],
        )

    def test_top_level_contract_drift_cannot_leave_o1_verified(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary)
            shutil.copytree(ROOT / "product", target / "product")
            program_path = target / "product" / "program.json"
            program = json.loads(program_path.read_text(encoding="utf-8"))
            program["completionExpression"] = "O1"
            program_path.write_text(
                json.dumps(program, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )

            result = self.run_verify(target)

        self.assertNotEqual(result.returncode, 0)
        report = json.loads(result.stdout)
        self.assertFalse(report["criterionStates"]["O1"])

    def test_constitution_cannot_disable_the_predecessor_guard(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary)
            shutil.copytree(ROOT / "product", target / "product")
            constitution_path = target / "product" / "constitution.json"
            constitution = json.loads(constitution_path.read_text(encoding="utf-8"))
            constitution["predecessorIdentityPattern"] = "(?!)"
            constitution_path.write_text(
                json.dumps(constitution, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            program_path = target / "product" / "program.json"
            program = json.loads(program_path.read_text(encoding="utf-8"))
            predecessor_identity = "agent" + "-skills" + "-curated"
            program["purpose"] = f"{predecessor_identity} compatibility mode"
            program_path.write_text(
                json.dumps(program, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )

            result = self.run_verify(target)

        self.assertNotEqual(result.returncode, 0)
        report = json.loads(result.stdout)
        self.assertFalse(report["criterionStates"]["G3"])
        self.assertIn(
            "active product authority contains a forbidden predecessor identity",
            report["errors"],
        )

    def test_constitution_cannot_remove_a_bootstrap_authority_file(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary)
            shutil.copytree(ROOT / "product", target / "product")
            constitution_path = target / "product" / "constitution.json"
            constitution = json.loads(constitution_path.read_text(encoding="utf-8"))
            constitution["requiredAuthorityFiles"] = [
                "product/constitution.json",
                "product/program.json",
                "product/acceptance.json",
                "product/evidence/project-reset-real-task-route-2026-08-11.json",
                "product/evidence/project-reset-cleanup-observation-2026-08-11.json",
            ]
            constitution_path.write_text(
                json.dumps(constitution, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            predecessor_identity = "agent" + "-skills" + "-curated"
            (target / "README.md").write_text(
                f"# {predecessor_identity}\n",
                encoding="utf-8",
            )

            result = self.run_verify(target)

        self.assertNotEqual(result.returncode, 0)
        report = json.loads(result.stdout)
        self.assertFalse(report["criterionStates"]["G3"])
        self.assertIn(
            "active product authority contains a forbidden predecessor identity",
            report["errors"],
        )

    def test_reintroduced_predecessor_authority_path_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary)
            shutil.copytree(ROOT / "product", target / "product")
            registry = target / "registry"
            registry.mkdir()
            predecessor_plan = registry / ("curation" + "-program" + "-plan.json")
            predecessor_plan.write_text("{}\n", encoding="utf-8")

            result = self.run_verify(target)

        self.assertNotEqual(result.returncode, 0)
        report = json.loads(result.stdout)
        self.assertFalse(report["criterionStates"]["G3"])
        self.assertIn(
            "current checkout contains a forbidden predecessor authority path",
            report["errors"],
        )

    def test_malformed_program_items_are_structurally_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary)
            shutil.copytree(ROOT / "product", target / "product")
            program_path = target / "product" / "program.json"
            program = json.loads(program_path.read_text(encoding="utf-8"))
            program["increments"] = ["not-an-object"]
            program_path.write_text(
                json.dumps(program, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )

            result = self.run_verify(target)

        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn("Traceback", result.stderr)
        report = json.loads(result.stdout)
        self.assertIn("program increment 0 must be an object", report["errors"])
        self.assertFalse(report["criterionStates"]["O1"])

    def test_outcome_evidence_is_not_interchangeable(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary)
            shutil.copytree(ROOT / "product", target / "product")
            acceptance_path = target / "product" / "acceptance.json"
            acceptance = json.loads(acceptance_path.read_text(encoding="utf-8"))
            route_evidence = "product/evidence/project-reset-real-task-route-2026-08-11.json"
            for criterion in acceptance["criteria"]:
                if criterion["id"] in {"O3", "O4"}:
                    criterion["assessment"] = "verified"
                    criterion["evidence"] = [route_evidence]
            acceptance_path.write_text(
                json.dumps(acceptance, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )

            result = self.run_verify(target)

        self.assertNotEqual(result.returncode, 0)
        report = json.loads(result.stdout)
        self.assertFalse(report["criterionStates"]["O3"])
        self.assertFalse(report["criterionStates"]["O4"])
        self.assertIn(
            f"evidence {route_evidence} is not an accepted capability lifecycle transaction",
            report["errors"],
        )
        self.assertIn(
            f"evidence {route_evidence} is not a real continuation receipt",
            report["errors"],
        )

    def test_cleanup_evidence_requires_resolved_absolute_roots(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary)
            shutil.copytree(ROOT / "product", target / "product")
            evidence_path = target / "product" / "evidence" / "project-reset-cleanup-observation-2026-08-11.json"
            evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
            evidence["roots"] = ["%TEMP%"]
            evidence_path.write_text(
                json.dumps(evidence, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )

            result = self.run_verify(target)

        self.assertNotEqual(result.returncode, 0)
        report = json.loads(result.stdout)
        self.assertFalse(report["criterionStates"]["O5"])
        self.assertFalse(report["criterionStates"]["G4"])
        self.assertIn(
            "cleanup evidence product/evidence/project-reset-cleanup-observation-2026-08-11.json must declare resolved absolute roots",
            report["errors"],
        )

    def test_release_identity_cannot_drift_between_plan_and_acceptance(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary)
            shutil.copytree(ROOT / "product", target / "product")
            acceptance_path = target / "product" / "acceptance.json"
            acceptance = json.loads(acceptance_path.read_text(encoding="utf-8"))
            acceptance["release"] = "v-next"
            acceptance_path.write_text(
                json.dumps(acceptance, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )

            result = self.run_verify(target)

        self.assertNotEqual(result.returncode, 0)
        report = json.loads(result.stdout)
        self.assertFalse(report["criterionStates"]["O1"])
        self.assertIn("program and acceptance releases must match", report["errors"])

    def test_arbitrary_authority_text_cannot_satisfy_the_human_guard(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary)
            shutil.copytree(ROOT / "product", target / "product")
            program_path = target / "product" / "program.json"
            program = json.loads(program_path.read_text(encoding="utf-8"))
            program["authorityBoundary"]["userOwns"] = ["none"]
            program["authorityBoundary"]["agentOwnsWithinBoundedAuthority"] = [
                "release",
                "delete",
            ]
            program_path.write_text(
                json.dumps(program, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )

            result = self.run_verify(target)

        self.assertNotEqual(result.returncode, 0)
        report = json.loads(result.stdout)
        self.assertFalse(report["criterionStates"]["G1"])
        self.assertIn("program authority boundary is incomplete or conflicting", report["errors"])

    def test_active_work_cannot_claim_an_unauthorized_operation(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary)
            shutil.copytree(ROOT / "product", target / "product")
            program_path = target / "product" / "program.json"
            program = json.loads(program_path.read_text(encoding="utf-8"))
            active_increment = next(
                item for item in program["increments"] if item["state"] == "active"
            )
            active_work = next(
                item for item in active_increment["workItems"] if item["state"] == "active"
            )
            active_work["operationIds"] = ["release"]
            program_path.write_text(
                json.dumps(program, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )

            result = self.run_verify(target)

        self.assertNotEqual(result.returncode, 0)
        report = json.loads(result.stdout)
        self.assertFalse(report["criterionStates"]["G1"])
        self.assertIn("active work requests unauthorized operations: release", report["errors"])

    def test_active_work_must_bind_at_least_one_operation(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary)
            shutil.copytree(ROOT / "product", target / "product")
            program_path = target / "product" / "program.json"
            program = json.loads(program_path.read_text(encoding="utf-8"))
            active_increment = next(
                item for item in program["increments"] if item["state"] == "active"
            )
            active_work = next(
                item for item in active_increment["workItems"] if item["state"] == "active"
            )
            active_work["operationIds"] = []
            program_path.write_text(
                json.dumps(program, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )

            result = self.run_verify(target)

        self.assertNotEqual(result.returncode, 0)
        report = json.loads(result.stdout)
        self.assertFalse(report["criterionStates"]["G1"])
        self.assertIn("active or completed work must bind at least one operation", report["errors"])

    def test_constitution_cannot_reactivate_the_local_legacy_quarantine(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary)
            shutil.copytree(ROOT / "product", target / "product")
            constitution_path = target / "product" / "constitution.json"
            constitution = json.loads(constitution_path.read_text(encoding="utf-8"))
            constitution["activeAuthorityGlobs"].append("Legacy/**/*.json")
            constitution_path.write_text(
                json.dumps(constitution, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )

            result = self.run_verify(target)

        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn("Traceback", result.stderr)
        report = json.loads(result.stdout)
        self.assertFalse(report["criterionStates"]["O1"])
        self.assertIn(
            "constitution cannot activate excluded authority locator: Legacy/**/*.json",
            report["errors"],
        )

    def test_absolute_authority_glob_is_structurally_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary)
            shutil.copytree(ROOT / "product", target / "product")
            constitution_path = target / "product" / "constitution.json"
            constitution = json.loads(constitution_path.read_text(encoding="utf-8"))
            constitution["activeAuthorityGlobs"].append("C:/**/*.json")
            constitution_path.write_text(
                json.dumps(constitution, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )

            result = self.run_verify(target)

        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn("Traceback", result.stderr)
        report = json.loads(result.stdout)
        self.assertIn(
            "constitution authority glob must be relative: C:/**/*.json",
            report["errors"],
        )

    def test_posix_absolute_cleanup_root_is_portable_evidence_syntax(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary)
            shutil.copytree(ROOT / "product", target / "product")
            evidence_path = target / "product" / "evidence" / "project-reset-cleanup-observation-2026-08-11.json"
            evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
            evidence["roots"] = ["/tmp"]
            evidence_path.write_text(
                json.dumps(evidence, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )

            result = self.run_verify(target)

        report = json.loads(result.stdout)
        self.assertTrue(report["criterionStates"]["O5"])
        self.assertTrue(report["criterionStates"]["G4"])
        self.assertNotIn(
            "cleanup evidence product/evidence/project-reset-cleanup-observation-2026-08-11.json must declare resolved absolute roots",
            report["errors"],
        )

    def test_top_level_authority_id_cannot_drift(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary)
            shutil.copytree(ROOT / "product", target / "product")
            acceptance_path = target / "product" / "acceptance.json"
            acceptance = json.loads(acceptance_path.read_text(encoding="utf-8"))
            acceptance["id"] = "renamed-authority"
            acceptance_path.write_text(
                json.dumps(acceptance, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )

            result = self.run_verify(target)

        self.assertNotEqual(result.returncode, 0)
        report = json.loads(result.stdout)
        self.assertFalse(report["criterionStates"]["O1"])
        self.assertIn(
            "product/acceptance.json must retain authority id harness-product-acceptance-v0.1",
            report["errors"],
        )


if __name__ == "__main__":
    unittest.main()
