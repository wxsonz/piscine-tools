"""B10: a segfault -> signal "SIGSEGV", fail. Output > 1 MB -> capped."""

import tempfile
import unittest

from judge_fixtures import PDF_ENTRY, run_judge

SEGV = ("int\tmain(int argc, char **argv)\n{\n\tint\t*p;\n\n"
        "\t(void)argv;\n\tp = (int *)0;\n\tp[argc] = 1;\n\treturn (0);\n}\n")
FLOOD = ("#include <unistd.h>\n\nint\tmain(void)\n{\n\tchar\tbuf[4096];\n\tint\ti;\n\n"
         "\ti = 0;\n\twhile (i < 4096)\n\t\tbuf[i++] = '1';\n"
         "\twhile (1)\n\t\twrite(1, buf, 4096);\n\treturn (0);\n}\n")


class TestB10CrashAndCap(unittest.TestCase):
    def test_segfault(self):
        with tempfile.TemporaryDirectory() as tmp:
            r = run_judge(tmp, {"ex00/main.c": SEGV}, [PDF_ENTRY])
        run = r["runs"][0]
        self.assertEqual(run["signal"], "SIGSEGV")
        self.assertIsNone(run["exit"])
        self.assertEqual(run["verdict"], "fail")
        self.assertIn("crashed: SIGSEGV", run["reasons"])

    def test_output_over_one_megabyte_is_capped(self):
        bank = [dict(PDF_ENTRY, timeout_ms=10_000)]
        with tempfile.TemporaryDirectory() as tmp:
            r = run_judge(tmp, {"ex00/main.c": FLOOD}, bank)
        run = r["runs"][0]
        self.assertEqual(len(run["stdout"]), 1_000_000)
        self.assertFalse(run["timed_out"])
        self.assertLess(run["time_ms"], 10_000)
        self.assertEqual(run["verdict"], "fail")
        self.assertIn("printed more than 1 MB: stopped", run["reasons"])


if __name__ == "__main__":
    unittest.main()
