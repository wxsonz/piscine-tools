"""B3: build failure -> built false, first error in build_log, runs empty,
everything else filled."""

import tempfile
import unittest

from judge_fixtures import PDF_ENTRY, run_judge

BROKEN = "#include <unistd.h>\n\nint\tmain(void)\n{\n\tint\tunused;\n\n\treturn (0);\n}\n"


class TestB3BuildFailure(unittest.TestCase):
    def test_build_failure(self):
        with tempfile.TemporaryDirectory() as tmp:
            r = run_judge(tmp, {"ex00/main.c": BROKEN}, [PDF_ENTRY])
        self.assertFalse(r["built"])
        first = r["build_log"].split("\n")[0]
        self.assertIn("error", first)
        self.assertIn("unused", first)
        self.assertEqual(r["runs"], [])
        self.assertIsNone(r["diagnosis"])
        self.assertEqual(r["groups"], {})
        self.assertEqual(r["files"]["sources"], ["ex00/main.c"])
        self.assertIsNotNone(r["forbidden"])
        self.assertIn("build failed", " ".join(r["forbidden"]["notes"]))
        self.assertIn("ran", r["norm"])
        self.assertFalse(r["sanitizer"]["ran"])
        self.assertEqual(set(r["tools"]), {"cc", "norminette", "valgrind", "asan"})

    def test_no_c_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            r = run_judge(tmp, {"ex00/README": "nothing\n"}, [PDF_ENTRY])
        self.assertFalse(r["built"])
        self.assertIn("no .c files", r["build_log"])
        self.assertEqual(r["runs"], [])


if __name__ == "__main__":
    unittest.main()
