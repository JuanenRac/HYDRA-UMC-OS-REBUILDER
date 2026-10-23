"""The updater dependency names a release tag, never a branch."""
import re
import unittest
from pathlib import Path

PYPROJECT = Path(__file__).resolve().parent.parent / "pyproject.toml"


class UpdaterPinTest(unittest.TestCase):
    def test_every_git_dependency_is_pinned_to_a_release_tag(self):
        text = PYPROJECT.read_text(encoding="utf-8")
        found = re.findall(r'"([A-Za-z0-9_.-]+) @ (git\+[^"]+)"', text)
        self.assertTrue(any(name == "hydra-umc-updater" for name, _ in found))
        for name, url in found:
            self.assertRegex(url, r"\.git@v\d+\.\d+\.\d+(?:\.\d+)?$", name)


if __name__ == "__main__":
    unittest.main()
