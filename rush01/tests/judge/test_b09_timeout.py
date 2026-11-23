"""B9: an infinite loop -> killed at timeout_ms, timed_out true, fail."""

import tempfile
import unittest

from judge_fixtures import NOSOL_ARG, QUICK, entry, run_judge

LOOP = ("int\tmain(int argc, char **argv)\n{\n\t(void)argv;\n"
        "\twhile (argc != 0)\n\t\targc = argc * 1;\n\treturn (argc);\n}\n")


@unittest.skipIf(QUICK, "slow: waits for timeouts (RUSH01_QUICK)")
class TestB9Timeout(unittest.TestCase):
    def test_infinite_loop_is_killed(self):
        bank = [entry("nosol4-deep-01", [NOSOL_ARG], [1] * 16, "error", timeout_ms=400)]
        with tempfile.TemporaryDirectory() as tmp:
            r = run_judge(tmp, {"ex00/main.c": LOOP}, bank)
        self.assertTrue(r["built"], r["build_log"])
        run = r["runs"][0]
        self.assertTrue(run["timed_out"])
        self.assertEqual(run["verdict"], "fail")
        self.assertIsNone(run["exit"])
        self.assertGreaterEqual(run["time_ms"], 400)
        self.assertLess(run["time_ms"], 3000)
        self.assertIn("timed out after 400 ms (killed)", run["reasons"])


if __name__ == "__main__":
    unittest.main()
