"""B13: garbage input (unbalanced braces, a binary file named .c, nesting
deep enough to break the reader) -> `error` set, parts unrecognized, no
exception."""

import os
import tempfile
import unittest

from c_team import team_files, team_write
from detect import detect_team


class TestB13Garbage(unittest.TestCase):

    def run_on(self, files):
        with tempfile.TemporaryDirectory(prefix="rush01-detect-") as tmp:
            team_write(tmp, files)
            return detect_team(tmp, "ex00")

    def assert_failed(self, result, words):
        self.assertIsNotNone(result["error"])
        self.assertIn(words, result["error"])
        for part, v in result["parts"].items():
            self.assertIsNone(v["id"], part)
            self.assertEqual(v["confidence"], "unrecognized", part)

    def test_unbalanced_braces(self):
        files = team_files(solve="int    ft_solve(int g[4][4])\n{\n    {\n")
        self.assert_failed(self.run_on(files), "ex00/solve.c: unbalanced")

    def test_binary_file(self):
        files = team_files(junk=b"\x7fELF\x02\x01\x01\x00\x00\x00binary")
        self.assert_failed(self.run_on(files), "ex00/junk.c: binary")

    def test_reader_crash_is_caught(self):
        deep = "int    f(void)\n{\n" + "{" * 5000 + "}" * 5000 + "\n}\n"
        result = self.run_on(team_files(deep=deep))
        self.assert_failed(result, "detection crashed")
        self.assertEqual(result["parts"]["solve"]["where"][0]["file"],
                         "ex00/check.c")

    def test_no_source(self):
        with tempfile.TemporaryDirectory(prefix="rush01-detect-") as tmp:
            os.makedirs(os.path.join(tmp, "ex00"))
            result = detect_team(tmp, "ex00")
        self.assert_failed(result, "no .c file")

    def test_missing_team_dir(self):
        result = detect_team("/nonexistent/rush01-team", None)
        self.assertIsNotNone(result["error"])


if __name__ == "__main__":
    unittest.main()
