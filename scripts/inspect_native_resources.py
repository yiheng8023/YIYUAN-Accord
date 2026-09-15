"""Read a complete caller-bound set of native process exit records.

This validates record completeness and basic types, not process ownership,
filesystem-wide protection or a successful lifecycle. Callers still correlate
each label with its captured invocation and judge exit/forced-cleanup evidence.
"""
import json
from pathlib import Path
import re


def native_processes_released(after, controller="windows-job-object"):
    """Judge only the declared controller's observed exit boundary."""
    if not _valid_after(after, controller):
        return False
    if controller == "windows-job-object":
        return type(after.get("activeProcesses")) is int and after["activeProcesses"] == 0
    if controller == "posix-session-process-group":
        return (after.get("controller") == controller and "activeProcesses" in after and after["activeProcesses"] is None
                and after.get("processGroupState") == "absent"
                and type(after.get("rootExitCode")) is int)
    return False


def _valid_after(after, controller):
    if not isinstance(after, dict):
        return False
    if controller == "windows-job-object":
        return (after.get("controller", controller) == controller
                and type(after.get("activeProcesses")) is int and after["activeProcesses"] >= 0)
    if controller == "posix-session-process-group":
        return (after.get("controller") == controller and "activeProcesses" in after and after["activeProcesses"] is None
                and after.get("processGroupState") in {"alive", "absent", "unobservable"}
                and type(after.get("processGroupId")) is int and after["processGroupId"] > 0
                and type(after.get("rootPid")) is int and after["rootPid"] == after["processGroupId"]
                and (after.get("rootExitCode") is None or type(after["rootExitCode"]) is int))
    return False


def read_native_resource_records(root, expected_labels):
    root = Path(root).resolve(strict=True)
    labels = tuple(expected_labels)
    if (not labels
            or any(not isinstance(label, str) or not re.fullmatch(r"[A-Za-z0-9_-]+", label)
                   for label in labels)
            or len(set(labels)) != len(labels)):
        raise ValueError("nonempty distinct resource labels required")
    observed = {path.parent.name for path in root.glob("*/resources.json")}
    if observed != set(labels):
        raise ValueError("native resource record set differs from its binding")
    records = {}
    for label in labels:
        path = root / label / "resources.json"
        if path.resolve(strict=True) != path or not path.is_file():
            raise ValueError("redirected or non-file resource record")
        with path.open("rb") as stream:
            data = stream.read(1024 * 1024 + 1)
        if len(data) > 1024 * 1024:
            raise ValueError("resource record exceeds read bound")
        record = json.loads(data)
        if (not isinstance(record, dict) or type(record.get("exitCode")) is not int
                or type(record.get("forced")) is not bool):
            raise ValueError("invalid native resource record")
        after = record.get("after")
        # Missing controller retains the immutable Windows record meaning.
        if not _valid_after(after, record.get("controller", "windows-job-object")):
            raise ValueError("invalid final process count")
        records[label] = record
    return records
