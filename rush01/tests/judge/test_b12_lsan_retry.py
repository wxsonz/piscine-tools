"""B12: LeakSanitizer "fatal error" -> retried with detect_leaks=0, the note
says so. LSan only dies where ptrace is blocked, so the program plays that
part: it prints the fatal line unless ASAN_OPTIONS has detect_leaks=0."""

import tempfile
import unittest

from judge_fixtures import EMPTY_ENTRY, PDF_ENTRY, has_asan, run_judge

FAKE_LSAN = (
    "#include <stdlib.h>\n#include <unistd.h>\n\n"
    "static int\thas(const char *s, const char *w)\n{\n\tint\ti;\n\n"
    "\twhile (s && *s)\n\t{\n\t\ti = 0;\n\t\twhile (w[i] && s[i] == w[i])\n\t\t\ti++;\n"
    "\t\tif (!w[i])\n\t\t\treturn (1);\n\t\ts++;\n\t}\n\treturn (0);\n}\n\n"
    "int\tmain(void)\n{\n\tconst char\t*m;\n\tint\t\t\tn;\n\n"
    "\tm = \"==1==LeakSanitizer has encountered a fatal error.\\n\";\n"
    "\tn = 0;\n\twhile (m[n])\n\t\tn++;\n"
    "\twrite(1, \"Error\\n\", 6);\n"
    "\tif (has(getenv(\"ASAN_OPTIONS\"), \"detect_leaks=1\"))\n"
    "\t{\n\t\twrite(2, m, n);\n\t\treturn (1);\n\t}\n\treturn (0);\n}\n")


@unittest.skipUnless(has_asan(), "ASan does not build and run here (B13 covers that)")
class TestB12LsanRetry(unittest.TestCase):
    def test_fatal_lsan_is_retried_without_leaks(self):
        with tempfile.TemporaryDirectory() as tmp:
            r = run_judge(tmp, {"ex00/main.c": FAKE_LSAN}, [PDF_ENTRY, EMPTY_ENTRY])
        san = r["sanitizer"]
        self.assertTrue(san["ran"])
        self.assertIn("re-ran with ASAN_OPTIONS=detect_leaks=0", san["note"])
        self.assertEqual(san["findings"], [])


if __name__ == "__main__":
    unittest.main()
