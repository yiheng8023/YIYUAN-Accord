import unittest

from scripts.validate_codex_desktop_official_control_surface_access_preflight import (
    validate_preflight,
)


class CodexDesktopOfficialControlSurfaceAccessPreflightTests(unittest.TestCase):
    def test_preflight_is_consistent(self) -> None:
        validate_preflight()


if __name__ == "__main__":
    unittest.main()
