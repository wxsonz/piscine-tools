"""B7: a correct grid -> pass; trailing space / missing final newline /
extra stdout -> fail with the reason. Also: a wrong grid names the broken
clue (needs the real puzzle_check)."""

import tempfile
import unittest

from judge_fixtures import (HAS_PUZZLE, NO_PUZZLE, PDF_ARG, PDF_ENTRY, PDF_GRID,
                            PDF_TEXT, answer_program, run_judge)


def judge_output(text):
    with tempfile.TemporaryDirectory() as tmp:
        r = run_judge(tmp, {"ex00/main.c": answer_program([(PDF_ARG, text, "")])},
                      [PDF_ENTRY])
    return r["runs"][0]


@unittest.skipUnless(HAS_PUZZLE, NO_PUZZLE)
class TestB7GridFormat(unittest.TestCase):
    def test_correct_grid_passes(self):
        run = judge_output(PDF_TEXT)
        self.assertEqual(run["verdict"], "pass", run["reasons"])
        self.assertEqual(run["grid"], PDF_GRID)
        self.assertEqual(run["broken"], [])

    def test_trailing_space_fails(self):
        run = judge_output(PDF_TEXT.replace("2 3 4 1\n", "2 3 4 1 \n"))
        self.assertEqual(run["verdict"], "fail")
        self.assertIn("trailing space on line 2", run["reasons"])
        self.assertEqual(run["grid"], PDF_GRID)

    def test_missing_final_newline_fails(self):
        run = judge_output(PDF_TEXT[:-1])
        self.assertEqual(run["verdict"], "fail")
        self.assertIn("no newline at the end of the output", run["reasons"])

    def test_extra_stdout_fails(self):
        run = judge_output(PDF_TEXT + "Error\n")
        self.assertEqual(run["verdict"], "fail")
        self.assertTrue(any(x.startswith("extra output after the grid") for x in run["reasons"]),
                        run["reasons"])

    def test_wrong_grid_names_the_broken_clue(self):
        wrong = "2 1 4 3\n1 2 3 4\n4 3 2 1\n3 4 1 2\n"
        run = judge_output(wrong)
        self.assertEqual(run["verdict"], "fail")
        self.assertTrue(run["broken"])
        self.assertTrue(any(x.startswith("breaks ") for x in run["reasons"]), run["reasons"])

    def test_error_on_a_valid_puzzle_fails(self):
        run = judge_output("Error\n")
        self.assertEqual(run["verdict"], "fail")
        self.assertIn("printed Error on a puzzle that has a solution", run["reasons"])


if __name__ == "__main__":
    unittest.main()
