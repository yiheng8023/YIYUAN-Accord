from __future__ import annotations

from contextlib import contextmanager
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

from harness.control import host_check, verify_product


ROOT = Path(__file__).resolve().parents[2]


def _read_json(root: Path, locator: str) -> dict:
    return json.loads((root / locator).read_text(encoding="utf-8"))


def _write_json(root: Path, locator: str, value: dict) -> None:
    (root / locator).write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


@contextmanager
def _fixture():
    with tempfile.TemporaryDirectory(prefix="aah-v12-test-") as temporary:
        target = Path(temporary) / "repository"
        shutil.copytree(
            ROOT,
            target,
            ignore=shutil.ignore_patterns(".git", ".tmp", "__pycache__", "*.pyc"),
        )
        yield target


class ProductControlTests(unittest.TestCase):
    maxDiff = None

    def test_current_contract_is_valid_but_not_release_complete(self) -> None:
        report = verify_product(ROOT)

        self.assertTrue(report["valid"], report["errors"])
        self.assertTrue(report["contractValid"])
        self.assertFalse(report["releaseComplete"])
        self.assertEqual(report["completionState"], "incomplete")
        self.assertEqual(report["criteria"]["verified"], 0)
        self.assertEqual(report["criteria"]["total"], 8)
        self.assertEqual(report["goalModePromptState"], "prepared-host-goal-paused")
        self.assertEqual(
            report["goldenTasks"]["behaviorEvidence"],
            "not-established-by-static-suite",
        )
        self.assertLessEqual(report["complexity"]["trackedFiles"], 55)
        self.assertLessEqual(
            report["complexity"]["harnessAndProductTestBytes"],
            120_000,
        )

    def test_public_cli_reports_the_same_contract(self) -> None:
        result = subprocess.run(
            [
                sys.executable,
                "-B",
                "-m",
                "harness",
                "verify",
                "--root",
                str(ROOT),
                "--json",
            ],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
            timeout=30,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads(result.stdout)
        self.assertTrue(report["valid"])
        self.assertFalse(report["releaseComplete"])
        self.assertEqual(set(report["hostChecks"]), {"codex", "claude-code"})

    def test_host_check_is_immediate_and_honest_about_behavior(self) -> None:
        for adapter in ("codex", "claude-code"):
            with self.subTest(adapter=adapter):
                report = host_check(ROOT, adapter)
                self.assertTrue(report["valid"], report["errors"])
                self.assertTrue(report["staticReady"])
                self.assertEqual(report["behaviorEvidenceState"], "unverified")
                self.assertEqual(
                    report["claim"],
                    "static host-admission conformance only",
                )

        unknown = host_check(ROOT, "not-a-host")
        self.assertFalse(unknown["valid"])
        self.assertIn("unknown host projection: not-a-host", unknown["errors"])

    def test_adapter_mapping_drift_fails(self) -> None:
        with _fixture() as root:
            locator = "plugins/agent-autonomy-harness-codex/adapter.json"
            contract = _read_json(root, locator)
            contract["hostStandardIds"].remove("H10")
            _write_json(root, locator, contract)

            report = verify_product(root)

            self.assertFalse(report["valid"])
            self.assertIn(
                "adapter codex hostStandardIds does not match constitution order",
                report["errors"],
            )

    def test_codex_marketplace_must_resolve_current_plugin(self) -> None:
        with _fixture() as root:
            locator = ".agents/plugins/marketplace.json"
            marketplace = _read_json(root, locator)
            self.assertEqual(marketplace["name"], "agent-autonomy-harness")
            self.assertEqual(
                marketplace["interface"]["displayName"],
                "Agent Autonomy Harness",
            )
            self.assertEqual(marketplace["plugins"][0]["category"], "Developer Tools")
            marketplace["plugins"][0]["source"]["path"] = (
                "./adapters/agent-autonomy-harness-codex"
            )
            _write_json(root, locator, marketplace)

            report = verify_product(root)

            self.assertFalse(report["valid"])
            self.assertIn(
                "adapter codex marketplace source is invalid",
                report["errors"],
            )

    def test_codex_marketplace_cannot_add_an_unbound_plugin(self) -> None:
        with _fixture() as root:
            locator = ".agents/plugins/marketplace.json"
            marketplace = _read_json(root, locator)
            extra = json.loads(json.dumps(marketplace["plugins"][0]))
            extra["name"] = "unbound-plugin"
            marketplace["plugins"].append(extra)
            _write_json(root, locator, marketplace)

            report = verify_product(root)

            self.assertFalse(report["valid"])
            self.assertIn(
                "adapter codex marketplace entry is not unique",
                report["errors"],
            )

    def test_codex_metadata_cannot_add_an_mcp_dependency(self) -> None:
        with _fixture() as root:
            metadata = (
                root
                / "plugins/agent-autonomy-harness-codex/skills/"
                "deliver-demand-driven-outcome/agents/openai.yaml"
            )
            metadata.write_text(
                metadata.read_text(encoding="utf-8")
                + "\ndependencies:\n"
                + "  tools: mcp\n",
                encoding="utf-8",
            )

            report = host_check(root, "codex")

            self.assertFalse(report["valid"])
            self.assertIn(
                "adapter codex metadata top-level fields are invalid",
                report["errors"],
            )

    def test_adapter_cannot_self_declare_observed_behavior(self) -> None:
        with _fixture() as root:
            locator = "plugins/agent-autonomy-harness-codex/adapter.json"
            contract = _read_json(root, locator)
            contract["behaviorEvidenceState"] = "observed"
            _write_json(root, locator, contract)

            report = host_check(root, "codex")

            self.assertFalse(report["valid"])
            self.assertIn(
                "adapter codex observed behavior lacks direct evidence",
                report["errors"],
            )

    def test_projection_bound_evidence_cannot_replay_after_skill_drift(self) -> None:
        with _fixture() as root:
            skill = root / (
                "plugins/agent-autonomy-harness-codex/skills/"
                "deliver-demand-driven-outcome/SKILL.md"
            )
            skill.write_text(
                skill.read_text(encoding="utf-8") + "\nnew behavior\n",
                encoding="utf-8",
            )

            report = verify_product(root)

            self.assertFalse(report["valid"])
            self.assertIn(
                "criteria[1].evidence[0] skillSha256 does not match "
                "current adapter codex",
                report["errors"],
            )

    def test_static_projection_evidence_cannot_replay_after_relocation(self) -> None:
        with _fixture() as root:
            locator = "evals/observations/2026-08-20-codex-static-admission.json"
            observation = _read_json(root, locator)
            observation["projection"]["skill"] = (
                "adapters/agent-autonomy-harness-codex/skills/"
                "deliver-demand-driven-outcome/SKILL.md"
            )
            _write_json(root, locator, observation)

            acceptance = _read_json(root, "product/acceptance.json")
            acceptance["criteria"][1]["evidence"][0]["sha256"] = hashlib.sha256(
                (root / locator).read_bytes()
            ).hexdigest()
            _write_json(root, "product/acceptance.json", acceptance)

            report = verify_product(root)

            self.assertFalse(report["valid"])
            self.assertIn(
                "criteria[1].evidence[0] skill locator does not match current "
                "adapter codex",
                report["errors"],
            )

    def test_required_sample_evidence_must_bind_current_projection(self) -> None:
        with _fixture() as root:
            acceptance = _read_json(root, "product/acceptance.json")
            representative = next(
                criterion
                for criterion in acceptance["criteria"]
                if criterion["id"] == "R3"
            )
            representative["evidence"][0].pop("bindsProjection")
            _write_json(root, "product/acceptance.json", acceptance)

            report = verify_product(root)

            self.assertFalse(report["valid"])
            self.assertIn(
                "R3 evidence[0] required sample observation is not "
                "projection-bound",
                report["errors"],
            )

    def test_required_sample_observation_must_follow_golden_schema(self) -> None:
        with _fixture() as root:
            locator = "evals/observations/2026-08-20-codex-gt01-paired.json"
            observation = _read_json(root, locator)
            observation.pop("residue")
            _write_json(root, locator, observation)

            acceptance = _read_json(root, "product/acceptance.json")
            acceptance["criteria"][2]["evidence"][0]["sha256"] = hashlib.sha256(
                (root / locator).read_bytes()
            ).hexdigest()
            _write_json(root, "product/acceptance.json", acceptance)

            report = verify_product(root)

            self.assertFalse(report["valid"])
            self.assertIn(
                "R3 evidence[0] omits fields: ['residue']",
                report["errors"],
            )

    def test_goal_prompt_and_increment_map_every_criterion(self) -> None:
        with _fixture() as root:
            program = _read_json(root, "product/program.json")
            program["goalModePrompt"]["mapsTo"].remove("Q4")
            program["activeIncrement"]["acceptanceIds"].remove("R3")
            _write_json(root, "product/program.json", program)

            report = verify_product(root)

            self.assertFalse(report["valid"])
            self.assertIn(
                "program.goalModePrompt.mapsTo must map every criterion exactly",
                report["errors"],
            )
            self.assertIn(
                "activeIncrement.acceptanceIds must map every criterion exactly",
                report["errors"],
            )

    def test_more_than_one_active_work_item_fails(self) -> None:
        with _fixture() as root:
            program = _read_json(root, "product/program.json")
            duplicate = dict(program["activeIncrement"]["workItems"][0])
            duplicate["id"] = "duplicate-active-work"
            program["activeIncrement"]["workItems"].append(duplicate)
            _write_json(root, "product/program.json", program)

            report = verify_product(root)

            self.assertFalse(report["valid"])
            self.assertIn(
                "activeIncrement must contain exactly one active work item",
                report["errors"],
            )

    def test_criterion_cannot_verify_without_direct_evidence(self) -> None:
        with _fixture() as root:
            acceptance = _read_json(root, "product/acceptance.json")
            acceptance["criteria"][0]["assessment"] = "verified"
            _write_json(root, "product/acceptance.json", acceptance)

            report = verify_product(root)

            self.assertFalse(report["valid"])
            self.assertIn(
                "criteria[0] is verified without direct evidence",
                report["errors"],
            )

    def test_repository_evidence_cannot_self_attest_release_completion(self) -> None:
        with _fixture() as root:
            acceptance = _read_json(root, "product/acceptance.json")
            deterministic = next(
                criterion
                for criterion in acceptance["criteria"]
                if criterion["id"] == "R2"
            )["evidence"][0]
            representative = next(
                criterion
                for criterion in acceptance["criteria"]
                if criterion["id"] == "R3"
            )["evidence"][0]
            for criterion in acceptance["criteria"]:
                criterion["assessment"] = "verified"
                if criterion["id"] == "R3":
                    continue
                source = (
                    deterministic
                    if criterion["evidenceClass"] == "deterministic-conformance"
                    else representative
                )
                criterion["evidence"] = [json.loads(json.dumps(source))]
            acceptance["releaseAuthorization"] = {
                "state": "authorized",
                "candidateRevision": "0" * 40,
                "namedHuman": "repository-authored-name",
                "authorizedAt": "2026-08-20T00:00:00Z",
                "claimCeilingAccepted": True,
                "publicationAuthorized": True,
                "releaseAuthorized": True,
            }
            _write_json(root, "product/acceptance.json", acceptance)

            program = _read_json(root, "product/program.json")
            program["status"] = "ready"
            program["activeIncrement"] = None
            _write_json(root, "product/program.json", program)

            report = verify_product(root)

            self.assertFalse(report["valid"])
            self.assertFalse(report["releaseComplete"])
            self.assertIn(
                "repository releaseAuthorization cannot grant human authority",
                report["errors"],
            )

    def test_runtime_release_authorization_binds_clean_exact_head(self) -> None:
        with _fixture() as root:
            acceptance = _read_json(root, "product/acceptance.json")
            acceptance["releaseAuthorization"]["state"] = "requested"
            _write_json(root, "product/acceptance.json", acceptance)
            for command in (
                ["git", "init"],
                ["git", "config", "user.name", "Harness Test"],
                ["git", "config", "user.email", "harness-test@example.invalid"],
                ["git", "add", "-A"],
                ["git", "commit", "-m", "candidate"],
            ):
                subprocess.run(
                    command,
                    cwd=root,
                    check=True,
                    capture_output=True,
                    text=True,
                    timeout=30,
                )
            head = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=root,
                check=True,
                capture_output=True,
                text=True,
                timeout=30,
            ).stdout.strip()
            authorization = {
                "schema": 1,
                "state": "authorized",
                "source": "explicit-runtime-human-authority",
                "candidateRevision": head,
                "namedHuman": "accountable-test-human",
                "authorizedAt": "2026-08-20T00:00:00Z",
                "claimCeilingAccepted": True,
                "publicationAuthorized": True,
                "releaseAuthorized": True,
            }

            report = verify_product(root, authorization)
            self.assertTrue(report["valid"], report["errors"])
            self.assertFalse(report["releaseComplete"])

            authorization["candidateRevision"] = "0" * 40
            mismatch = verify_product(root, authorization)
            self.assertFalse(mismatch["valid"])
            self.assertIn(
                "runtime release authorization does not match repository HEAD",
                mismatch["errors"],
            )

            authorization["candidateRevision"] = head
            (root / "task-residue.tmp").write_text("residue\n", encoding="utf-8")
            dirty = verify_product(root, authorization)
            self.assertFalse(dirty["valid"])
            self.assertIn(
                "runtime release authorization requires a clean worktree",
                dirty["errors"],
            )

    def test_verified_criterion_requires_explicit_observation_support(self) -> None:
        with _fixture() as root:
            acceptance = _read_json(root, "product/acceptance.json")
            r2 = next(
                criterion
                for criterion in acceptance["criteria"]
                if criterion["id"] == "R2"
            )
            r2["assessment"] = "verified"
            _write_json(root, "product/acceptance.json", acceptance)

            report = verify_product(root)

            self.assertFalse(report["valid"])
            self.assertIn(
                "criteria[1] verified evidence lacks an accepted R2 decision",
                report["errors"],
            )

    def test_verified_representative_sample_rejects_pending_human_review(self) -> None:
        with _fixture() as root:
            acceptance = _read_json(root, "product/acceptance.json")
            r3 = next(
                criterion
                for criterion in acceptance["criteria"]
                if criterion["id"] == "R3"
            )
            r3["assessment"] = "verified"
            _write_json(root, "product/acceptance.json", acceptance)

            report = verify_product(root)

            self.assertFalse(report["valid"])
            self.assertIn(
                "R3 verified sample has nonterminal task decisions: "
                "['GT-01', 'GT-07']",
                report["errors"],
            )

    def test_forbidden_paths_must_remain_repository_relative(self) -> None:
        with _fixture() as root, tempfile.TemporaryDirectory(
            prefix="aah-v12-outside-"
        ) as outside:
            outside_locator = Path(outside).as_posix()
            program = _read_json(root, "product/program.json")
            program["complexityBudget"]["forbiddenActivePaths"] = [
                outside_locator
            ]
            program["hostProjections"][0]["forbiddenPaths"] = [outside_locator]
            _write_json(root, "product/program.json", program)

            report = verify_product(root)

            self.assertFalse(report["valid"])
            self.assertIn(
                "program.complexityBudget.forbiddenActivePaths[0] is not a "
                "repository-relative path",
                report["errors"],
            )
            self.assertIn(
                "adapter codex forbiddenPaths[0] is not a repository-relative path",
                report["errors"],
            )

    def test_codex_marketplace_cannot_expand_installation_policy(self) -> None:
        with _fixture() as root:
            marketplace_locator = ".agents/plugins/marketplace.json"
            marketplace = _read_json(root, marketplace_locator)
            marketplace["plugins"][0]["policy"] = {
                "installation": "INSTALLED_BY_DEFAULT",
                "authentication": "ON_USE",
            }
            _write_json(root, marketplace_locator, marketplace)

            observation_locator = (
                "evals/observations/2026-08-20-codex-static-admission.json"
            )
            observation = _read_json(root, observation_locator)
            observation["projection"]["marketplaceSha256"] = hashlib.sha256(
                (root / marketplace_locator).read_bytes()
            ).hexdigest()
            _write_json(root, observation_locator, observation)

            acceptance = _read_json(root, "product/acceptance.json")
            r2 = next(
                criterion
                for criterion in acceptance["criteria"]
                if criterion["id"] == "R2"
            )
            r2["evidence"][0]["sha256"] = hashlib.sha256(
                (root / observation_locator).read_bytes()
            ).hexdigest()
            _write_json(root, "product/acceptance.json", acceptance)

            report = verify_product(root)

            self.assertFalse(report["valid"])
            self.assertIn(
                "adapter codex marketplace policy must be AVAILABLE/ON_INSTALL",
                report["errors"],
            )

    def test_skill_only_manifest_rejects_an_mcp_execution_surface(self) -> None:
        with _fixture() as root:
            manifest_locator = (
                "plugins/agent-autonomy-harness-codex/.codex-plugin/plugin.json"
            )
            manifest = _read_json(root, manifest_locator)
            manifest["mcpServers"] = {
                "not-executed": {"command": "not-executed"}
            }
            _write_json(root, manifest_locator, manifest)

            observation_locator = (
                "evals/observations/2026-08-20-codex-static-admission.json"
            )
            observation = _read_json(root, observation_locator)
            observation["projection"]["manifestSha256"] = hashlib.sha256(
                (root / manifest_locator).read_bytes()
            ).hexdigest()
            _write_json(root, observation_locator, observation)

            acceptance = _read_json(root, "product/acceptance.json")
            r2 = next(
                criterion
                for criterion in acceptance["criteria"]
                if criterion["id"] == "R2"
            )
            r2["evidence"][0]["sha256"] = hashlib.sha256(
                (root / observation_locator).read_bytes()
            ).hexdigest()
            _write_json(root, "product/acceptance.json", acceptance)

            report = verify_product(root)

            self.assertFalse(report["valid"])
            self.assertIn(
                "adapter codex manifest contains unsupported fields: ['mcpServers']",
                report["errors"],
            )

    def test_projection_evidence_requires_the_complete_current_identity(self) -> None:
        with _fixture() as root:
            locator = "evals/observations/2026-08-20-codex-gt01-paired.json"
            observation = _read_json(root, locator)
            for field in (
                "manifest",
                "manifestSha256",
                "marketplace",
                "marketplaceSha256",
                "contract",
                "contractSha256",
            ):
                observation["projectionIdentity"].pop(field, None)
            _write_json(root, locator, observation)

            acceptance = _read_json(root, "product/acceptance.json")
            r3 = next(
                criterion
                for criterion in acceptance["criteria"]
                if criterion["id"] == "R3"
            )
            item = next(
                item for item in r3["evidence"] if item["locator"] == locator
            )
            item["sha256"] = hashlib.sha256((root / locator).read_bytes()).hexdigest()
            _write_json(root, "product/acceptance.json", acceptance)

            report = verify_product(root)

            self.assertFalse(report["valid"])
            self.assertIn(
                "criteria[2].evidence[0] projection identity fields do not match "
                "current adapter codex",
                report["errors"],
            )

    def test_static_suite_cannot_claim_behavior_evidence(self) -> None:
        with _fixture() as root:
            suite = _read_json(root, "evals/golden-tasks.json")
            suite["evaluationProtocol"]["staticSuiteIsNotBehaviorEvidence"] = False
            _write_json(root, "evals/golden-tasks.json", suite)

            report = verify_product(root)

            self.assertFalse(report["valid"])
            self.assertIn(
                "golden tasks must reject static-suite-as-behavior-evidence",
                report["errors"],
            )

    def test_representative_policy_classifies_every_golden_task(self) -> None:
        with _fixture() as root:
            acceptance = _read_json(root, "product/acceptance.json")
            acceptance["representativeBehaviorPolicy"]["postReleaseTasks"].remove(
                "GT-10"
            )
            _write_json(root, "product/acceptance.json", acceptance)

            report = verify_product(root)

            self.assertFalse(report["valid"])
            self.assertIn(
                "representative policy does not classify golden tasks: ['GT-10']",
                report["errors"],
            )

    def test_historical_validator_on_active_path_fails(self) -> None:
        with _fixture() as root:
            forbidden = root / "harness/task_validator_o4_continuous_self_correction_v3.py"
            forbidden.write_text("# historical proof generation\n", encoding="utf-8")

            report = verify_product(root)

            self.assertFalse(report["valid"])
            self.assertIn(
                "forbidden active path remains: "
                "harness/task_validator_o4_continuous_self_correction_v3.py",
                report["errors"],
            )

    def test_ignored_python_cache_is_release_blocking_residue(self) -> None:
        with _fixture() as root:
            cache = root / "nested" / "__pycache__"
            cache.mkdir(parents=True)
            (cache / "task.cpython-314.pyc").write_bytes(b"task residue")

            report = verify_product(root)

            self.assertFalse(report["valid"])
            self.assertIn(
                "known task residue remains: "
                "['nested/__pycache__', "
                "'nested/__pycache__/task.cpython-314.pyc']",
                report["errors"],
            )

    def test_ignored_empty_task_directory_is_release_blocking_residue(self) -> None:
        with _fixture() as root:
            (root / ".tmp").mkdir()

            report = verify_product(root)

            self.assertFalse(report["valid"])
            self.assertIn(
                "known task residue remains: ['.tmp']",
                report["errors"],
            )

    def test_project_audit_digest_is_bound(self) -> None:
        with _fixture() as root:
            report_path = (
                root
                / "research/reviews/"
                "2026-08-20-agent-autonomy-harness-refactor-and-evolution-report.md"
            )
            report_path.write_text(
                report_path.read_text(encoding="utf-8") + "\nchanged\n",
                encoding="utf-8",
            )

            report = verify_product(root)

            self.assertFalse(report["valid"])
            self.assertIn(
                "inputEvidence[0] repository digest mismatch",
                report["errors"],
            )

    def test_required_representative_sample_keeps_failed_observation(self) -> None:
        with _fixture() as root:
            acceptance = _read_json(root, "product/acceptance.json")
            representative = next(
                criterion
                for criterion in acceptance["criteria"]
                if criterion["id"] == "R3"
            )
            representative["evidence"] = [
                item
                for item in representative["evidence"]
                if "gt02" not in item["locator"]
            ]
            _write_json(root, "product/acceptance.json", acceptance)

            report = verify_product(root)

            self.assertFalse(report["valid"])
            self.assertIn(
                "representative release sample missing task observations: "
                "['GT-02']",
                report["errors"],
            )

    def test_duplicate_json_key_fails_closed(self) -> None:
        with _fixture() as root:
            path = root / "product/constitution.json"
            raw = path.read_text(encoding="utf-8")
            path.write_text(
                raw.replace('"schema": 2,', '"schema": 2,\n  "schema": 2,', 1),
                encoding="utf-8",
            )

            report = verify_product(root)

            self.assertFalse(report["valid"])
            self.assertTrue(
                any("duplicate JSON key: schema" in error for error in report["errors"])
            )

if __name__ == "__main__":
    unittest.main()
