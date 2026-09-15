import json
from pathlib import Path
import tempfile
import unittest

from scripts.inspect_native_resources import native_processes_released, read_native_resource_records


class NativeResourceRecordsTest(unittest.TestCase):
    labels = ("discovery", "resumed", "after-remove")

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        for label in self.labels:
            (self.root / label).mkdir()
            self.write(label, {"exitCode": 0, "forced": False, "after": {"activeProcesses": 0}})

    def write(self, label, value):
        (self.root / label / "resources.json").write_text(json.dumps(value), encoding="utf-8")

    def test_complete_records_preserve_non_success_for_caller_judgment(self):
        self.write("resumed", {"exitCode": 1, "forced": True, "after": {"activeProcesses": 2}})
        records = read_native_resource_records(self.root, self.labels)
        self.assertEqual(set(records), set(self.labels))
        self.assertEqual(records["resumed"]["after"]["activeProcesses"], 2)
        self.assertTrue(records["resumed"]["forced"])

    def test_missing_record_cannot_be_hidden_by_all_remaining_processes_zero(self):
        for label in self.labels:
            path = self.root / label / "resources.json"
            before = path.read_bytes()
            path.unlink()
            # The former present-files-only predicate falsely passed this state.
            self.assertTrue(all(json.loads(p.read_bytes())["after"]["activeProcesses"] == 0
                                for p in self.root.glob("*/resources.json")))
            with self.assertRaises(ValueError):
                read_native_resource_records(self.root, self.labels)
            path.write_bytes(before)

    def test_unbound_extra_record_is_not_silently_accepted(self):
        (self.root / "extra").mkdir()
        self.write("extra", {"exitCode": 0, "forced": False, "after": {"activeProcesses": 0}})
        with self.assertRaises(ValueError):
            read_native_resource_records(self.root, self.labels)

    def test_invalid_or_empty_binding_is_rejected(self):
        for labels in [[], ["discovery", "discovery"], ["../resumed"], ["*"]]:
            with self.assertRaises(ValueError):
                read_native_resource_records(self.root, labels)

    def test_false_and_missing_counters_are_not_zero(self):
        for after in [{"activeProcesses": False}, {}, {"activeProcesses": -1}]:
            self.write("resumed", {"exitCode": 0, "forced": False, "after": after})
            with self.assertRaises(ValueError):
                read_native_resource_records(self.root, self.labels)

    def test_posix_group_records_preserve_unknown_counts_and_observation_failures(self):
        after = {"controller": "posix-session-process-group", "activeProcesses": None,
                 "processGroupId": 42, "rootPid": 42, "rootExitCode": 0,
                 "processGroupState": "absent"}
        for state in ("alive", "absent", "unobservable"):
            with self.subTest(state=state):
                sample = {**after, "processGroupState": state}
                self.write("resumed", {"controller": "posix-session-process-group", "exitCode": 0,
                                      "forced": state != "absent", "after": sample})
                records = read_native_resource_records(self.root, self.labels)
                self.assertIsNone(records["resumed"]["after"]["activeProcesses"])
                self.assertEqual(native_processes_released(sample, "posix-session-process-group"), state == "absent")
                self.assertFalse(native_processes_released(sample, "windows-job-object"))
        self.assertFalse(native_processes_released({**after, "rootExitCode": None}, "posix-session-process-group"))
        self.assertFalse(native_processes_released({"activeProcesses": 0}, "posix-session-process-group"))
        self.assertFalse(native_processes_released({**after, "rootPid": 43}, "posix-session-process-group"))
        missing_count = dict(after)
        missing_count.pop("activeProcesses")
        self.write("resumed", {"controller": "posix-session-process-group", "exitCode": 0,
                               "forced": False, "after": missing_count})
        with self.assertRaises(ValueError):
            read_native_resource_records(self.root, self.labels)
        self.write("resumed", {"exitCode": 0, "forced": False, "after": after})
        with self.assertRaises(ValueError):
            read_native_resource_records(self.root, self.labels)


if __name__ == "__main__":
    unittest.main()
