"""Distinguishing calibration checks; these are not Accord comparison trials."""

import copy
import json
from pathlib import Path
import stat
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from scripts import grade_accord_comparison as grading


class ComparisonCalibrationTests(unittest.TestCase):
    def setUp(self):
        self.suite, self.sha = grading.load_suite()
        self.temporary = tempfile.TemporaryDirectory(prefix="accord-grader-")
        self.addCleanup(self.temporary.cleanup)
        self.parent = Path(self.temporary.name)

    def workspace(self, case_id="S1A", name="work"):
        case = grading.select_case(self.suite, case_id)
        root = self.parent / name
        grading.prepare(case, root)
        return case, root

    def write_outputs(self, case, root, stage="final"):
        for relative, expected in case["stages"][stage]["outputs"].items():
            target = root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(json.dumps(expected, ensure_ascii=False), encoding="utf-8")

    def result(self, case, root, stage="final"):
        return grading.grade(case, stage, root, self.sha)

    def test_each_case_and_stage_has_a_solvable_file_contract(self):
        # Reference constructions calibrate the checker, not any Agent's ability.
        for case in self.suite["cases"]:
            for stage in case["stages"]:
                with self.subTest(case=case["id"], stage=stage):
                    root = self.parent / (case["id"] + stage)
                    grading.prepare(case, root)
                    self.write_outputs(case, root, stage)
                    result = self.result(case, root, stage)
                    self.assertEqual(result["fileCriteria"], "pass")
                    self.assertEqual(result["runValidity"], "unverified")
                    self.assertEqual(result["taskOutcome"], "unverified")
                    self.assertEqual(result["incrementalValue"], "unverified")

    def test_reference_totals_are_independently_recomputed_from_raw_inputs(self):
        for case in self.suite["cases"]:
            if case["kind"] == "simple":
                rows = json.loads(case["inputs"]["items.json"])
                selected = [row for row in rows if row["status"] == "active"]
                expected = case["stages"]["final"]["outputs"]["report.json"]
                self.assertEqual(sum(row["units"] for row in selected), expected["activeUnits"])
                self.assertEqual({r["category"]: sum(x["units"] for x in selected if x["category"] == r["category"])
                                  for r in selected}, expected["byCategory"])
            elif case["kind"] == "change":
                rows = json.loads(case["inputs"]["tickets.json"])
                for stage, excluded in (("initial", {"done"}), ("final", {"done", "blocked"})):
                    selected = [row for row in rows if row["state"] not in excluded]
                    outputs = case["stages"][stage]["outputs"]
                    self.assertEqual(sum(row["units"] for row in selected), outputs["summary.json"]["units"])
                    if stage == "final":
                        self.assertEqual(len(selected), outputs["dashboard.json"]["includedCount"])
                        self.assertEqual({r["team"]: sum(x["team"] == r["team"] for x in selected)
                                          for r in selected}, outputs["dashboard.json"]["byTeam"])
            else:
                rows = [row for text in case["inputs"].values() for row in json.loads(text)]
                expected = case["stages"]["final"]["outputs"]["manifest.json"]
                self.assertEqual(sum(row["units"] for row in rows), expected["totalUnits"])
                self.assertEqual(len(rows), expected["recordCount"])

    def test_preparation_contains_only_inputs_not_answers_or_agent_guidance(self):
        case, root = self.workspace()
        self.assertEqual({p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file()}, set(case["inputs"]))
        before = (root / "items.json").read_bytes()
        with self.assertRaises(FileExistsError):
            grading.prepare(case, root)
        self.assertEqual((root / "items.json").read_bytes(), before)

    def test_order_variations_and_optional_explanation_do_not_require_accord_words(self):
        case, root = self.workspace("S1B")
        expected = copy.deepcopy(case["stages"]["final"]["outputs"]["report.json"])
        expected["excludedIds"].reverse()
        expected["note"] = "按输入规则整理完成。"
        (root / "report.json").write_text(json.dumps(expected, indent=4), encoding="utf-8-sig")
        self.assertEqual(self.result(case, root)["fileCriteria"], "pass")

    def test_plausible_success_text_does_not_hide_wrong_numbers(self):
        case, root = self.workspace()
        self.write_outputs(case, root)
        wrong = copy.deepcopy(case["stages"]["final"]["outputs"]["report.json"])
        wrong["activeUnits"] = 19
        wrong["note"] = "全部通过，原件已保护，任务完成。"
        (root / "report.json").write_text(json.dumps(wrong), encoding="utf-8")
        self.assertEqual(self.result(case, root)["fileCriteria"], "not-passed")

    def test_unchanged_old_summary_fails_even_with_correct_new_dashboard(self):
        case, root = self.workspace("C1A")
        self.write_outputs(case, root)
        old = case["stages"]["initial"]["outputs"]["summary.json"]
        (root / "summary.json").write_text(json.dumps(old), encoding="utf-8")
        result = self.result(case, root)
        rows = {row["path"]: row["state"] for row in result["checks"]}
        self.assertEqual(rows["summary.json"], "fail")
        self.assertEqual(rows["dashboard.json"], "pass")

    def test_missing_batch_is_not_recovery_even_when_manifest_claims_all(self):
        case, root = self.workspace("R1A")
        self.write_outputs(case, root)
        (root / "output/two.json").unlink()
        result = self.result(case, root)
        self.assertEqual(result["fileCriteria"], "not-passed")
        self.assertEqual(result["runValidity"], "unverified")

    def test_original_mutation_cannot_be_compensated_by_correct_outputs(self):
        case, root = self.workspace()
        self.write_outputs(case, root)
        (root / "items.json").write_text("[]", encoding="utf-8")
        result = self.result(case, root)
        self.assertEqual(result["fileCriteria"], "not-passed")
        self.assertEqual(result["counts"]["fail"], 1)

    def test_false_types_duplicates_nonfinite_and_malformed_data_do_not_pass(self):
        case, root = self.workspace("R1B")
        self.write_outputs(case, root)
        target = root / "output/one.json"
        good = target.read_text(encoding="utf-8")
        for text in [good.replace('"units": 4', '"units": true'),
                     good.replace('"units": 4', '"units": 4.0'),
                     '{"records": [], "units": 4, "units": 4}',
                     '{"records": [], "units": NaN}', '{']:
            with self.subTest(text=text):
                target.write_text(text, encoding="utf-8")
                self.assertEqual(self.result(case, root)["fileCriteria"], "not-passed")

    def test_duplicate_rows_cannot_replace_missing_rows(self):
        case, root = self.workspace("R1A")
        self.write_outputs(case, root)
        wrong = {"records": [{"id": "a", "units": 3}, {"id": "a", "units": 3}], "units": 3}
        (root / "output/one.json").write_text(json.dumps(wrong), encoding="utf-8")
        self.assertEqual(self.result(case, root)["fileCriteria"], "not-passed")

    def test_grading_is_read_only_and_binding_is_visible(self):
        case, root = self.workspace()
        self.write_outputs(case, root)
        before = {p: p.read_bytes() for p in root.rglob("*") if p.is_file()}
        result = self.result(case, root)
        self.assertEqual(result["suiteSha256"], self.sha)
        self.assertEqual({p: p.read_bytes() for p in root.rglob("*") if p.is_file()}, before)

    def test_oversize_material_and_escaping_paths_are_not_valid(self):
        case, root = self.workspace()
        (root / "report.json").write_bytes(b" " * (grading.LIMIT + 1))
        self.assertEqual(self.result(case, root)["fileCriteria"], "not-passed")
        for relative in ("../outside.json", "/absolute", "C:/outside", "a\\b", "a//b", "./a"):
            with self.subTest(relative=relative), self.assertRaises(ValueError):
                grading.path_parts(relative)

    def test_relative_manifest_path_spellings_and_order_are_equivalent(self):
        case, root = self.workspace("R1A")
        self.write_outputs(case, root)
        target = root / "manifest.json"
        (root / "output/sub").mkdir()
        output = json.loads(target.read_text())
        output["files"] = ["./output/three.json", "output\\two.json", "output/sub/../one.json"]
        target.write_text(json.dumps(output), encoding="utf-8")
        self.assertEqual(self.result(case, root)["fileCriteria"], "pass")
        output["files"][0] = "../output/three.json"
        target.write_text(json.dumps(output), encoding="utf-8")
        self.assertEqual(self.result(case, root)["fileCriteria"], "not-passed")

    def test_manifest_rejects_drive_or_invalid_segments_before_normalization(self):
        case, root = self.workspace("R1A")
        self.write_outputs(case, root)
        target = root / "manifest.json"
        output = json.loads(target.read_text())
        for value in ("C:/../output/one.json", "output/\u0000/../one.json", "../work/output/one.json",
                      "/output/one.json", "output/missing/../one.json"):
            with self.subTest(value=value):
                output["files"][0] = value
                target.write_text(json.dumps(output), encoding="utf-8")
                self.assertEqual(self.result(case, root)["fileCriteria"], "not-passed")

    def test_manifest_case_follows_actual_filesystem_identity(self):
        case, root = self.workspace("R1A")
        self.write_outputs(case, root)
        target = root / "manifest.json"
        output = json.loads(target.read_text())
        output["files"][0] = "OUTPUT/ONE.JSON"
        target.write_text(json.dumps(output), encoding="utf-8")
        reference_exists = (root / "OUTPUT/ONE.JSON").is_file()
        expected = "pass" if reference_exists else "not-passed"
        self.assertEqual(self.result(case, root)["fileCriteria"], expected)

    def test_known_format_errors_and_unreadable_files_have_distinct_states(self):
        case, root = self.workspace()
        target = root / "report.json"
        for text in ("{", '{"activeUnits": 17, "activeUnits": 17}', '{"activeUnits": NaN}'):
            target.write_text(text, encoding="utf-8")
            row = self.result(case, root)["checks"][-1]
            self.assertEqual((row["state"], row["reason"]), ("fail", "output-format-invalid"))
        target.write_bytes(b" " * (grading.LIMIT + 1))
        row = self.result(case, root)["checks"][-1]
        self.assertEqual((row["state"], row["reason"]), ("unknown", "output-unreadable-or-unsafe"))

    def test_finite_exponent_in_optional_explanation_is_not_a_hidden_float_limit(self):
        case, root = self.workspace()
        self.write_outputs(case, root)
        target = root / "report.json"
        target.write_text(target.read_text()[:-1] + ', "optionalValue": 1e999}', encoding="utf-8")
        self.assertEqual(self.result(case, root)["fileCriteria"], "pass")

    def test_missing_input_is_a_known_file_failure(self):
        case, root = self.workspace()
        self.write_outputs(case, root)
        (root / "items.json").unlink()
        row = self.result(case, root)["checks"][0]
        self.assertEqual((row["state"], row["reason"]), ("fail", "required-input-missing"))

    def test_omitting_an_active_zero_only_category_fails(self):
        case, root = self.workspace("S1B")
        self.write_outputs(case, root)
        target = root / "report.json"
        output = json.loads(target.read_text())
        del output["byCategory"]["misc"]
        target.write_text(json.dumps(output), encoding="utf-8")
        self.assertEqual(self.result(case, root)["fileCriteria"], "not-passed")

    def test_symbolic_output_does_not_read_or_change_the_target(self):
        case, root = self.workspace()
        outside = self.parent / "outside.json"
        outside.write_text('{"private": "not-an-output"}', encoding="utf-8")
        try:
            (root / "report.json").symlink_to(outside)
        except OSError:
            # Some Windows runners cannot create links. Exercise the observed
            # filesystem metadata boundary without requiring new host trust.
            link_info = SimpleNamespace(st_mode=stat.S_IFLNK, st_file_attributes=0x400)
            with patch.object(Path, "lstat", return_value=link_info):
                with self.assertRaises(ValueError):
                    grading.read_file(root, "report.json")
            self.assertEqual(outside.read_text(), '{"private": "not-an-output"}')
            return
        else:
            result = self.result(case, root)
        self.assertEqual(result["checks"][-1]["state"], "unknown")
        self.assertEqual(outside.read_text(), '{"private": "not-an-output"}')


if __name__ == "__main__":
    unittest.main()
