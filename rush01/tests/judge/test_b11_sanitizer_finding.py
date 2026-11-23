"""B11: reading past '\\0' on "" -> a sanitizer finding with the case id.
(ASan does not watch argv itself, so the program reads past the end of a
heap copy of argv[1], as a team that mallocs its input would.)"""

import tempfile
import unittest

from judge_fixtures import EMPTY_ENTRY, PDF_ENTRY, has_asan, run_judge

MAIN = ("#include <stdlib.h>\n#include <unistd.h>\n\n"
        "int\tmain(int argc, char **argv)\n{\n\tchar\t*s;\n\tint\t\tn;\n\tint\t\ti;\n"
        "\tint\t\tsum;\n\n\tif (argc != 2)\n\t\treturn (1);\n\tn = 0;\n"
        "\twhile (argv[1][n])\n\t\tn++;\n\ts = malloc(n + 1);\n\ti = -1;\n"
        "\twhile (++i <= n)\n\t\ts[i] = argv[1][i];\n\tsum = 0;\n\ti = 0;\n"
        "\twhile (i < 16)\n\t\tsum += s[2 * i++];\n\tfree(s);\n"
        "\twrite(1, \"Error\\n\", 6 + (sum & 0));\n\treturn (0);\n}\n")


@unittest.skipUnless(has_asan(), "ASan does not build and run here (B13 covers that)")
class TestB11SanitizerFinding(unittest.TestCase):
    def test_read_past_end_on_empty_argument(self):
        with tempfile.TemporaryDirectory() as tmp:
            r = run_judge(tmp, {"ex00/main.c": MAIN}, [PDF_ENTRY, EMPTY_ENTRY])
        san = r["sanitizer"]
        self.assertTrue(san["ran"], san["note"])
        by_case = {f["case"]: f for f in san["findings"]}
        self.assertIn("fmt-01", by_case)
        self.assertEqual(by_case["fmt-01"]["kind"], "heap-buffer-overflow")
        self.assertIn("main.c", by_case["fmt-01"]["text"])
        self.assertNotIn(tmp, by_case["fmt-01"]["text"])
        self.assertNotIn("ok4-01", by_case)

    def test_clean_program_has_no_findings(self):
        main = ("#include <unistd.h>\n\nint\tmain(void)\n{\n"
                "\twrite(1, \"Error\\n\", 6);\n\treturn (0);\n}\n")
        with tempfile.TemporaryDirectory() as tmp:
            r = run_judge(tmp, {"ex00/main.c": main}, [PDF_ENTRY, EMPTY_ENTRY])
        self.assertTrue(r["sanitizer"]["ran"])
        self.assertEqual(r["sanitizer"]["findings"], [])


if __name__ == "__main__":
    unittest.main()
