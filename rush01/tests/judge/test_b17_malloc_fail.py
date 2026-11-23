"""B17: the team's mallocs are made to fail one at a time (the sheet: "break
their program if possible; if it breaks, select 'Crash'"). An unchecked
malloc crashes on N=1; a checked one doesn't; no malloc -> a note."""

import tempfile
import unittest

from judge_fixtures import PDF_ENTRY, run_judge

UNCHECKED = ("#include <stdlib.h>\n#include <unistd.h>\n\n"
             "int\tmain(void)\n{\n\tchar\t*a;\n\tchar\t*b;\n\n"
             "\ta = malloc(4);\n\tb = malloc(4);\n\ta[0] = 'E';\n\tb[0] = '\\n';\n"
             "\twrite(1, a, 1);\n\twrite(1, b, 1);\n\tfree(a);\n\tfree(b);\n"
             "\treturn (0);\n}\n")
CHECKED = UNCHECKED.replace("\ta[0] = 'E';",
                            "\tif (!a || !b)\n\t\treturn (1);\n\ta[0] = 'E';")
NO_MALLOC = "int\tmain(void)\n{\n\treturn (0);\n}\n"


class TestB17MallocFail(unittest.TestCase):
    def judge(self, src):
        with tempfile.TemporaryDirectory() as tmp:
            return run_judge(tmp, {"ex00/main.c": src}, [PDF_ENTRY])["malloc_fail"]

    def test_unchecked_crashes(self):
        m = self.judge(UNCHECKED)
        self.assertTrue(m["ran"], m["note"])
        self.assertEqual(m["mallocs"], 2)
        self.assertEqual(m["crashes"], [1, 2])
        self.assertEqual(m["tries"][0]["outcome"], "crash")

    def test_checked_survives(self):
        m = self.judge(CHECKED)
        self.assertTrue(m["ran"], m["note"])
        self.assertEqual(m["crashes"], [])
        self.assertEqual([t["outcome"] for t in m["tries"]], ["exit 1", "exit 1"])

    def test_no_malloc_is_a_note(self):
        m = self.judge(NO_MALLOC)
        self.assertFalse(m["ran"])
        self.assertIn("never calls malloc", m["note"])


if __name__ == "__main__":
    unittest.main()
