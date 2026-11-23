"""B15: timing.slow4_over_ok4 = median slow4 time / median ok4 time (null
if either is missing)."""

import statistics
import tempfile
import unittest

from judge_fixtures import PDF_ENTRY, entry, run_judge

SLEEPER = ("#include <unistd.h>\n\nint\tmain(int argc, char **argv)\n{\n"
           "\tif (argc == 2 && argv[1][0] == 's')\n\t\tusleep(150000);\n"
           "\telse\n\t\tusleep(15000);\n\twrite(1, \"Error\\n\", 6);\n\treturn (0);\n}\n")


class TestB15Timing(unittest.TestCase):
    def test_ratio_of_medians(self):
        clues = PDF_ENTRY["clues"]
        bank = ([entry(f"ok4-0{i}", [f"o{i}"], clues, "grid") for i in (1, 2, 3)]
                + [entry(f"slow4-0{i}", [f"s{i}"], clues, "grid") for i in (1, 2, 3)])
        with tempfile.TemporaryDirectory() as tmp:
            r = run_judge(tmp, {"ex00/main.c": SLEEPER}, bank)
        ok = [x["time_ms"] for x in r["runs"] if x["group"] == "ok4"]
        slow = [x["time_ms"] for x in r["runs"] if x["group"] == "slow4"]
        want = round(statistics.median(slow) / max(statistics.median(ok), 1), 1)
        self.assertEqual(r["timing"]["slow4_over_ok4"], want)
        self.assertGreater(want, 3)
        self.assertTrue(r["timing"]["slowest_id"].startswith("slow4-"))
        self.assertEqual(r["timing"]["slowest_ms"], max(ok + slow))

    def test_null_without_slow4(self):
        with tempfile.TemporaryDirectory() as tmp:
            r = run_judge(tmp, {"ex00/main.c": SLEEPER}, [PDF_ENTRY])
        self.assertIsNone(r["timing"]["slow4_over_ok4"])
        self.assertEqual(r["timing"]["slowest_id"], "ok4-01")


if __name__ == "__main__":
    unittest.main()
