"""B14: `diagnosis` is built from runs whose output is a grid or Error, on
puzzles with clues not null (SHAPES "diagnosis case")."""

import sys
import tempfile
import unittest
from unittest import mock

from judge_fixtures import (EMPTY_ENTRY, HAS_PUZZLE, NO_PUZZLE, NOSOL_ARG,
                            NOSOL_ENTRY, PDF_ARG, PDF_ENTRY, PDF_GRID, PDF_TEXT,
                            answer_program, clues_of, entry, run_judge)

GRID2 = PDF_GRID[::-1]
GRID3 = [[r[1], r[0], r[2], r[3]] for r in PDF_GRID]
GRID4 = PDF_GRID[1:] + PDF_GRID[:1]


def arg(grid):
    return " ".join(map(str, clues_of(grid)))


@unittest.skipUnless(HAS_PUZZLE, NO_PUZZLE)
class TestB14DiagnosisCases(unittest.TestCase):
    def test_cases_passed_to_diagnose(self):
        self.assertEqual(len({PDF_ARG, arg(GRID2), arg(GRID3), arg(GRID4)}), 4)
        bank = [PDF_ENTRY,
                entry("ok4-02", [arg(GRID2)], clues_of(GRID2), "grid"),
                entry("ok4-03", [arg(GRID3)], clues_of(GRID3), "grid"),
                entry("ok4-04", [arg(GRID4)], clues_of(GRID4), "grid"),
                NOSOL_ENTRY, EMPTY_ENTRY,
                entry("small-01", ["1 2 2 1 1 2 2 1"], [1, 2, 2, 1, 1, 2, 2, 1],
                      "info", n=2)]
        main = answer_program([(PDF_ARG, PDF_TEXT, ""), (arg(GRID2), PDF_TEXT, ""),
                               (arg(GRID3), "Error\n", ""), (arg(GRID4), "hello\n", ""),
                               (NOSOL_ARG, "Error\n", "")])
        real = sys.modules["judge.judge_evaluate"].puzzle_diagnose
        with mock.patch("judge.judge_evaluate.puzzle_diagnose", wraps=real) as spy:
            with tempfile.TemporaryDirectory() as tmp:
                r = run_judge(tmp, {"ex00/main.c": main}, bank)
        cases = spy.call_args[0][0]
        got = [(c["id"], c["outcome"], c["correct"], c["grid"]) for c in cases]
        self.assertEqual(got, [("ok4-01", "grid", True, PDF_GRID),
                               ("ok4-02", "grid", False, PDF_GRID),
                               ("ok4-03", "error", False, None),
                               ("nosol4-easy-01", "error", True, None)])
        self.assertEqual(cases[1]["clues"], clues_of(GRID2))
        self.assertEqual({c["n"] for c in cases}, {4})
        self.assertEqual(r["diagnosis"], real(cases))


if __name__ == "__main__":
    unittest.main()
