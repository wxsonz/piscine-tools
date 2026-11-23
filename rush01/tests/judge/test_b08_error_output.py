"""B8: Error\\n on stdout -> pass; on stderr -> pass + note (or fail when
subject.error_on_stderr == "fail")."""

import tempfile
import unittest

from judge_fixtures import NOSOL_ARG, NOSOL_ENTRY, SUBJECT, answer_program, run_judge


def judge_error(out, err, subject=SUBJECT):
    main = answer_program([(NOSOL_ARG, out, err)])
    with tempfile.TemporaryDirectory() as tmp:
        r = run_judge(tmp, {"ex00/main.c": main}, [NOSOL_ENTRY], subject)
    return r["runs"][0]


class TestB8ErrorOutput(unittest.TestCase):
    def test_error_on_stdout_passes(self):
        run = judge_error("Error\n", "")
        self.assertEqual((run["verdict"], run["reasons"], run["notes"]), ("pass", [], []))

    def test_error_on_stderr_passes_with_note(self):
        run = judge_error("", "Error\n")
        self.assertEqual(run["verdict"], "pass")
        self.assertEqual(run["notes"], ["Error printed on stderr (fd 2), not stdout"])

    def test_error_on_stderr_fails_when_subject_says_so(self):
        run = judge_error("", "Error\n", dict(SUBJECT, error_on_stderr="fail"))
        self.assertEqual(run["verdict"], "fail")
        self.assertIn("stderr", run["reasons"][0])

    def test_wrong_text_fails(self):
        for out in ("Error", "error\n", "Error\n\n", ""):
            run = judge_error(out, "")
            self.assertEqual(run["verdict"], "fail", repr(out))
            self.assertTrue(run["reasons"], repr(out))


if __name__ == "__main__":
    unittest.main()
