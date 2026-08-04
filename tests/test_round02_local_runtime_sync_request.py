import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent


def load(path: str) -> dict[str, object]:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


class Round02LocalRuntimeSyncRequestTests(unittest.TestCase):
    def setUp(self) -> None:
        self.request = load("registry/round02-local-runtime-sync-approval-request.json")
        self.proposal = load("registry/round02-approved-payload-routing-proposal.json")
        self.manifest = load("release-manifest.json")
        self.events = load("registry/round02-local-runtime-sync-approval-events.json")
        self.execution = load("registry/round02-local-runtime-sync-execution.json")

    def test_request_is_not_approval_and_binds_validated_source(self) -> None:
        self.assertEqual(self.request["schema_version"], 1)
        self.assertEqual(
            self.request["id"],
            "round02-local-runtime-sync-approval-request-2026-07-02",
        )
        self.assertEqual(self.request["status"], "awaiting_owner_approval")
        self.assertTrue(self.request["not_approval"])
        self.assertFalse(self.request["approval_recorded"])
        self.assertEqual(
            self.request["source_execution_record"],
            "registry/round02-approved-payload-routing-proposal.json",
        )
        self.assertEqual(
            self.proposal["status"],
            "approved_payload_routing_proposal_validated_github_only",
        )
        self.assertEqual(
            self.request["release_inventory"],
            {"skill_count": 20, "file_count": 42, "routing_scenario_count": 105},
        )

    def test_preflight_records_only_the_expected_local_drift(self) -> None:
        snapshot = self.request["preflight_snapshot"]
        self.assertEqual(snapshot["mode"], "read_only")
        self.assertEqual(
            snapshot["canonical_local_source"],
            r"C:\Users\15521\.cc-switch\skills",
        )
        self.assertEqual(
            snapshot["cc_switch_manifest_file_status"],
            {"match": 34, "drift": 7, "missing": 1},
        )
        self.assertEqual(
            snapshot["drift_files"],
            [
                "skills/grill-with-docs/SKILL.md",
                "skills/prototype/SKILL.md",
                "skills/review/SKILL.md",
                "skills/shipping-and-launch/SKILL.md",
                "skills/to-issues/SKILL.md",
                "skills/to-prd/SKILL.md",
                "skills/triage/SKILL.md",
            ],
        )
        self.assertEqual(
            snapshot["missing_files"],
            ["skills/obsidian-open-format-knowledge-files/SKILL.md"],
        )
        for missing in snapshot["missing_release_roots_by_directory"].values():
            self.assertEqual(missing, ["obsidian-open-format-knowledge-files"])

    def test_permissions_fail_closed_until_owner_approval(self) -> None:
        permissions = self.request["current_permissions"]
        self.assertTrue(permissions["approval_request_allowed"])
        for key, value in permissions.items():
            if key != "approval_request_allowed" and key != "network_access_required":
                self.assertFalse(value, key)
        self.assertFalse(permissions["network_access_required"])
        self.assertEqual(
            self.request["safe_approval_phrases"],
            [
                "批准执行 Round-02 local runtime sync（允许 junction fallback）",
                "Approve Round-02 local runtime sync with junction fallback only",
            ],
        )
        disallowed = set(self.request["still_disallowed"])
        self.assertIn("local runtime sync without owner approval", disallowed)
        self.assertIn(
            "modifying Codex-owned .system, codex-primary-runtime, plugin, or cache Skills",
            disallowed,
        )
        self.assertIn("promoting adapter-only, reference-only, or rejected candidates", disallowed)

    def test_request_registry_links_its_evidence_doc(self) -> None:
        doc_path = self.request["evidence_doc"]
        doc = (ROOT / doc_path).read_text(encoding="utf-8")
        for phrase in [
            "This is an approval request, not approval.",
            "Read-Only Preflight",
            "批准执行 Round-02 local runtime sync（允许 junction fallback）",
            "Junction fallback",
            "Explicitly Not Requested",
            "Until the approval event exists, local runtime sync remains blocked",
        ]:
            self.assertIn(phrase, doc)

        self.assertEqual(
            self.request["evidence_doc"],
            "docs/round02-local-runtime-sync-approval-request.md",
        )

    def test_approval_event_matches_request_scope(self) -> None:
        self.assertEqual(
            self.events["status"],
            "owner_approval_recorded_for_round02_local_runtime_sync",
        )
        self.assertTrue(self.events["approval_recorded"])
        self.assertTrue(self.events["local_runtime_sync_allowed"])
        self.assertTrue(self.events["create_junction_fallback_allowed"])
        event = self.events["events"][0]
        self.assertEqual(
            event["approval_request_id"],
            "round02-local-runtime-sync-approval-request-2026-07-02",
        )
        self.assertEqual(event["approved_scope"], self.request["requested_scope_if_approved"])
        self.assertEqual(event["explicitly_not_approved"], self.request["explicitly_not_requested"])
        self.assertEqual(event["next_state"], "round02_local_runtime_sync_execution")

    def test_execution_records_junction_fallback_and_local_verification(self) -> None:
        self.assertEqual(
            self.execution["status"],
            "passed_with_junction_fallback",
        )
        self.assertEqual(
            self.execution["approval_event_id"],
            "round02-owner-approval-2026-07-02-local-runtime-sync",
        )
        attempts = {item["id"]: item for item in self.execution["attempts"]}
        self.assertEqual(attempts["round02-local-runtime-sync-attempt-1"]["status"], "failed_rolled_back_and_cleaned")
        self.assertEqual(attempts["round02-local-runtime-sync-attempt-2"]["status"], "passed")
        self.assertEqual(attempts["round02-local-runtime-sync-attempt-2"]["fallback_used"], "directory-junction")
        self.assertEqual(
            self.execution["verification_results"]["cc_switch_manifest_hashes"],
            {"checked": 42, "matched": 42, "drift": 0, "missing": 0},
        )
        links = self.execution["verification_results"]["link_entries"]
        self.assertEqual(len(links), 2)
        for link in links:
            self.assertEqual(link["linkType"], "Junction")
            self.assertTrue(link["exists"])
            self.assertEqual(
                link["target"],
                r"C:\Users\15521\.cc-switch\skills\obsidian-open-format-knowledge-files",
            )
        boundaries = self.execution["boundary_results"]
        self.assertFalse(any(boundaries.values()))

    def test_execution_registry_links_its_evidence_doc(self) -> None:
        doc_path = self.execution["evidence_doc"]
        doc = (ROOT / doc_path).read_text(encoding="utf-8")
        for phrase in [
            "Round 02 Local Runtime Sync Execution",
            "Attempt 1",
            "Attempt 2",
            "Junction fallback",
            "cc-switch manifest files matched: 42",
        ]:
            self.assertIn(phrase, doc)
        self.assertEqual(
            self.execution["evidence_doc"],
            "docs/round02-local-runtime-sync-execution.md",
        )


if __name__ == "__main__":
    unittest.main()
