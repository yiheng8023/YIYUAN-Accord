import hashlib
from pathlib import Path
import tempfile
import unittest

from scripts.repository_text_identity import (
    repository_text_bytes,
    repository_text_identity_matches,
    repository_text_sha256,
    windows_crlf_projection_sha256,
)


class RepositoryTextIdentityTests(unittest.TestCase):
    def test_lf_and_crlf_checkouts_have_one_repository_identity(self) -> None:
        lf = b'{\n  "value": 1\n}\n'
        crlf = lf.replace(b"\n", b"\r\n")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            lf_path = root / "lf.json"
            crlf_path = root / "crlf.json"
            lf_path.write_bytes(lf)
            crlf_path.write_bytes(crlf)

            expected_repository = hashlib.sha256(lf).hexdigest()
            expected_capture = hashlib.sha256(crlf).hexdigest()
            self.assertEqual(repository_text_bytes(lf_path), lf)
            self.assertEqual(repository_text_bytes(crlf_path), lf)
            self.assertEqual(repository_text_sha256(lf_path), expected_repository)
            self.assertEqual(repository_text_sha256(crlf_path), expected_repository)
            self.assertEqual(
                windows_crlf_projection_sha256(lf_path), expected_capture
            )
            self.assertEqual(
                windows_crlf_projection_sha256(crlf_path), expected_capture
            )

    def test_mixed_or_lone_carriage_return_is_rejected(self) -> None:
        invalid = (b"one\r\ntwo\n", b"one\rtwo\n")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for index, data in enumerate(invalid):
                path = root / f"invalid-{index}.txt"
                path.write_bytes(data)
                with self.assertRaisesRegex(
                    RuntimeError, "deterministic LF or CRLF"
                ):
                    repository_text_bytes(path)

    def test_expected_lf_or_crlf_capture_identity_matches_either_checkout(
        self,
    ) -> None:
        lf = b"license\ntext\n"
        crlf = lf.replace(b"\n", b"\r\n")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name, checkout in (("lf", lf), ("crlf", crlf)):
                path = root / f"{name}.txt"
                path.write_bytes(checkout)
                self.assertTrue(
                    repository_text_identity_matches(
                        path,
                        expected_bytes=len(lf),
                        expected_sha256=hashlib.sha256(lf).hexdigest(),
                    )
                )
                self.assertTrue(
                    repository_text_identity_matches(
                        path,
                        expected_bytes=len(crlf),
                        expected_sha256=hashlib.sha256(crlf).hexdigest(),
                    )
                )
                self.assertFalse(
                    repository_text_identity_matches(
                        path,
                        expected_bytes=len(crlf),
                        expected_sha256="0" * 64,
                    )
                )


if __name__ == "__main__":
    unittest.main()
