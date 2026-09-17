"""The isolation in `conftest.py` must be REAL, and must be able to fail."""
import os
import pathlib
import unittest

from tools.omr import staff_labels_surya as S


class TestNoTestCanReachTheUsersRealSuryaServer(unittest.TestCase):
    def test_the_sentinel_is_not_the_users_real_path(self):
        real = pathlib.Path(
            os.path.expanduser("~/.cache/datalab/surya/llamacpp_server.json"))
        self.assertNotEqual(
            pathlib.Path(S.SENTINEL).resolve(), real.resolve(),
            "a test is pointed at the REAL Surya sentinel — it can read "
            "another session's server, and stop_server() can reach for it")

    def test_the_redirect_is_writable_and_empty(self):
        """⚠️ The positive control. Asserting only 'not the real path' passes
        if SENTINEL were None, a broken value, or an unwritable stub — so the
        redirect has to be shown to be a usable temp location."""
        p = pathlib.Path(S.SENTINEL)
        self.assertFalse(p.exists(), "a fresh test must start with no sentinel")
        p.write_text("{}")
        self.assertTrue(p.exists())
        p.unlink()

    def test_resident_server_reports_nothing_under_isolation(self):
        """The observable consequence: whatever is running on this machine,
        a test sees no server."""
        self.assertIsNone(S.resident_server())


if __name__ == "__main__":
    unittest.main()
