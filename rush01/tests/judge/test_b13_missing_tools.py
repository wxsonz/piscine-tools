"""B13: a missing tool (norminette, valgrind, asan) -> `ran` false and a note;
nothing fails because of it."""

import os
import stat
import tempfile
import unittest

from judge_fixtures import (EMPTY_ENTRY, PDF_ARG, PDF_ENTRY, PDF_TEXT, SUBJECT,
                            answer_program, has_asan, path_without, run_judge)
from test_b12_lsan_retry import FAKE_LSAN

MAIN = answer_program([(PDF_ARG, PDF_TEXT, "")])
NO_ASAN_CC = ("#!/bin/sh\nfor a in \"$@\"; do\n  case \"$a\" in\n"
              "    -fsanitize=*) echo \"cc: cannot find -lasan\" >&2; exit 1 ;;\n"
              "  esac\ndone\nexec cc \"$@\"\n")


class TestB13MissingTools(unittest.TestCase):
    def hide(self, tmp, names):
        old = os.environ["PATH"]
        os.environ["PATH"] = path_without(tmp, names)
        self.addCleanup(os.environ.__setitem__, "PATH", old)

    def test_no_asan_runtime(self):
        with tempfile.TemporaryDirectory() as tmp:
            cc = os.path.join(tmp, "cc-no-asan")
            with open(cc, "w", encoding="utf-8") as fh:
                fh.write(NO_ASAN_CC)
            os.chmod(cc, stat.S_IRWXU)
            subject = dict(SUBJECT, build=[cc] + SUBJECT["build"][1:])
            r = run_judge(tmp, {"ex00/main.c": MAIN}, [PDF_ENTRY], subject)
        self.assertFalse(r["tools"]["asan"])
        self.assertTrue(r["built"], r["build_log"])
        self.assertFalse(r["sanitizer"]["ran"])
        self.assertIn("ASan not available", r["sanitizer"]["note"])
        self.assertEqual(r["runs"][0]["verdict"], "pass")

    def test_no_norminette(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.hide(tmp, {"norminette"})
            r = run_judge(tmp, {"ex00/main.c": MAIN}, [PDF_ENTRY])
        self.assertFalse(r["tools"]["norminette"])
        self.assertEqual(r["norm"], {"ran": False, "ok": None, "errors": [],
                                     "note": "norminette not installed: skipped"})
        self.assertTrue(r["built"])
        self.assertEqual(r["runs"][0]["verdict"], "pass")

    @unittest.skipUnless(has_asan(), "ASan does not build and run here")
    def test_no_valgrind_when_lsan_dies(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.hide(tmp, {"valgrind"})
            r = run_judge(tmp, {"ex00/main.c": FAKE_LSAN}, [PDF_ENTRY, EMPTY_ENTRY])
        self.assertFalse(r["tools"]["valgrind"])
        self.assertTrue(r["sanitizer"]["ran"])
        self.assertIn("valgrind not installed: leaks not checked", r["sanitizer"]["note"])


if __name__ == "__main__":
    unittest.main()
