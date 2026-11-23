"""B1: finds ex00/ at depth <= 2 (rush00's find_ex_dir order); none ->
files.no_ex_dir true and the root is judged."""

import tempfile
import unittest

from judge_fixtures import PDF_ENTRY, PDF_TEXT, PDF_ARG, answer_program, run_judge

MAIN = answer_program([(PDF_ARG, PDF_TEXT, "")])


class TestB1FindExDir(unittest.TestCase):
    def test_ex00_at_depth_two(self):
        with tempfile.TemporaryDirectory() as tmp:
            r = run_judge(tmp, {"rush01/ex00/main.c": MAIN, "README.md": "hi\n",
                                "rush01/notes.txt": "x\n"}, [PDF_ENTRY])
        self.assertEqual(r["ex_dir"], "rush01/ex00")
        self.assertFalse(r["files"]["no_ex_dir"])
        self.assertEqual(r["files"]["sources"], ["rush01/ex00/main.c"])
        self.assertTrue(r["built"])
        outside = {f["path"] for f in r["files"]["flagged"] if "outside" in f["why"]}
        self.assertEqual(outside, {"README.md", "rush01/notes.txt"})

    def test_shallowest_ex00_with_c_files_wins(self):
        with tempfile.TemporaryDirectory() as tmp:
            r = run_judge(tmp, {"ex00/README": "empty\n", "a/ex00/main.c": MAIN},
                          [PDF_ENTRY])
        self.assertEqual(r["ex_dir"], "a/ex00")

    def test_too_deep_or_missing_judges_the_root(self):
        with tempfile.TemporaryDirectory() as tmp:
            r = run_judge(tmp, {"main.c": MAIN, "a/b/ex00/x.c": "int x;\n"},
                          [PDF_ENTRY])
        self.assertTrue(r["files"]["no_ex_dir"])
        self.assertEqual(r["ex_dir"], ".")
        self.assertEqual(r["files"]["sources"], ["main.c"])
        self.assertTrue(r["built"])
        self.assertEqual(r["runs"][0]["verdict"], "pass")

    def test_flags_objects_binaries_and_extra_dirs(self):
        with tempfile.TemporaryDirectory() as tmp:
            r = run_judge(tmp, {"ex00/main.c": MAIN, "ex00/main.o": "obj",
                                "ex00/a.out": "\x7fELF....", "ex00/.DS_Store": "x",
                                "ex00/tests/t.c": "int t;\n"}, [PDF_ENTRY])
        why = {f["path"]: f["why"] for f in r["files"]["flagged"]}
        self.assertIn("object", why["ex00/main.o"])
        self.assertIn("binary", why["ex00/a.out"])
        self.assertIn(".DS_Store", why["ex00/.DS_Store"])
        self.assertIn("directory", why["ex00/tests/"])


if __name__ == "__main__":
    unittest.main()
