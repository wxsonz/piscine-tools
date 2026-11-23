"""Tests for tool/puzzle/: one per behaviour B1..B13 of its CONTRACT.md.
Run: python3 rush01/tests/run.py puzzle (RUSH01_QUICK=1 skips the slow ones)."""

import itertools
import os
import tempfile
import time
import unittest

from puzzle import puzzle_check, puzzle_clues, puzzle_diagnose
from puzzle import puzzle_load_bank, puzzle_make_bank, puzzle_misreadings
from puzzle import puzzle_save_bank, puzzle_solve, puzzle_visible

HERE = os.path.dirname(os.path.abspath(__file__))
BANK_DIR = os.path.join(HERE, "..", "..", "tool", "puzzle", "bank")
QUICK = bool(os.environ.get("RUSH01_QUICK"))
PDF = [4, 3, 2, 1, 1, 2, 2, 2, 4, 3, 2, 1, 1, 2, 2, 2]
PDF_GRID = [[1, 2, 3, 4], [2, 3, 4, 1], [3, 4, 1, 2], [4, 1, 2, 3]]
CONTRACT_IDS = ("transpose swap_top_bottom swap_left_right rows_first "
                "clockwise interleaved reverse_top reverse_bottom "
                "reverse_left reverse_right bottom_no_reverse "
                "right_no_reverse only_top_left only_rows only_cols "
                "count_plus1 count_minus1 max_one ge_not_gt").split()


def latin_squares_4():
    """All 4x4 Latin squares, by brute force (independent of the solver)."""
    squares = []
    for rows in itertools.permutations(itertools.permutations(range(1, 5)), 4):
        if all(len({row[c] for row in rows}) == 4 for c in range(4)):
            squares.append([list(row) for row in rows])
    return squares


def sides(clues):
    n = len(clues) // 4
    return [clues[k * n:(k + 1) * n] for k in range(4)]


def is_correct(n, clues, grid):
    check = puzzle_check(n, clues, grid)
    return check["latin"] and not check["broken"]


def team_case(entry, team_clues):
    """What a team that solves `team_clues` correctly prints for `entry`."""
    found = puzzle_solve(4, team_clues, limit=1)["solutions"]
    if not found:
        return {"id": entry["id"], "n": 4, "clues": entry["clues"],
                "outcome": "error", "grid": None, "correct": False}
    grid = found[0]
    return {"id": entry["id"], "n": 4, "clues": entry["clues"],
            "outcome": "grid", "grid": grid,
            "correct": is_correct(4, entry["clues"], grid)}


class PuzzleTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.bank = puzzle_load_bank(BANK_DIR)
        cls.groups = {}
        for entry in cls.bank:
            cls.groups.setdefault(entry["group"], []).append(entry)

    def test_b1_pdf_example(self):
        found = puzzle_solve(4, PDF, limit=2)
        self.assertEqual(found["solutions"], [PDF_GRID])
        self.assertGreater(found["nodes"], 0)

    def test_b2_clues_of_pdf_grid(self):
        self.assertEqual(puzzle_clues(PDF_GRID), PDF)
        self.assertEqual(puzzle_visible([1, 3, 2, 4]), 3)

    def test_b3_576_squares_and_bank_solution_counts(self):
        squares = latin_squares_4()
        self.assertEqual(len(squares), 576)
        by_clues = {}
        for grid in squares:
            by_clues.setdefault(tuple(puzzle_clues(grid)), []).append(grid)
        # the solver finds exactly the squares showing each clue list
        for clues, grids in by_clues.items():
            found = puzzle_solve(4, list(clues), limit=100)["solutions"]
            self.assertEqual(sorted(found), sorted(grids), clues)
        want = {"ok4": "one", "slow4": "one", "multi4": "many",
                "nosol4-easy": "none", "nosol4-deep": "none"}
        for group, kind in want.items():
            self.assertTrue(self.groups.get(group), group)
            for entry in self.groups[group]:
                count = len(by_clues.get(tuple(entry["clues"]), []))
                got = {0: "none", 1: "one"}.get(count, "many")
                self.assertEqual(got, kind, entry["id"])
                self.assertEqual(entry["expect"],
                                 "error" if kind == "none" else "grid")

    def test_b4_ok4_mostly_asymmetric(self):
        ok4 = self.groups["ok4"]
        asym = [e for e in ok4
                if sides(e["clues"])[0] != sides(e["clues"])[2]
                or sides(e["clues"])[1] != sides(e["clues"])[3]]
        all_differ = [e for e in ok4
                      if len({tuple(s) for s in sides(e["clues"])}) == 4]
        self.assertGreaterEqual(3 * len(asym), 2 * len(ok4))
        self.assertGreaterEqual(2 * len(all_differ), len(ok4))
        self.assertEqual(ok4[0]["clues"], PDF)

    def test_b5_nosol4_deep_pairs_fine(self):
        for entry in self.groups["nosol4-deep"]:
            top, bottom, left, right = sides(entry["clues"])
            for a, b in list(zip(top, bottom)) + list(zip(left, right)):
                self.assertTrue(3 <= a + b <= 5, entry["id"])
                self.assertNotEqual((a, b), (1, 1), entry["id"])

    def test_b6_fmt_inputs(self):
        fmt = self.groups["fmt"]
        for entry in fmt:
            self.assertIsNone(entry["clues"], entry["id"])
            self.assertEqual(entry["expect"], "error", entry["id"])
        argvs = [entry["argv"] for entry in fmt]
        singles = [argv[0] for argv in argvs if len(argv) == 1]
        words = [w for text in singles for w in text.split(" ")]
        for argv in ([""], ["1"], ["4 3"], []):
            self.assertIn(argv, argvs)
        self.assertTrue(any(len(argv) == 2 for argv in argvs), "two args")
        counts = [len(text.split()) for text in singles]
        self.assertIn(15, counts)
        self.assertIn(17, counts)
        for token in ("0", "5", "/", ":", "12", "04", "-1", "+1"):
            self.assertIn(token, words)
        self.assertTrue(any(w.isalpha() for w in words), "letters")
        checks = {
            "double space": lambda t: "  " in t,
            "leading space": lambda t: t.startswith(" "),
            "trailing space": lambda t: t.endswith(" "),
            "tab": lambda t: "\t" in t,
            "vertical tab": lambda t: "\v" in t,
            "newline inside": lambda t: "\n" in t.rstrip("\n"),
            "trailing newline": lambda t: t.endswith("\n"),
        }
        for name, test in checks.items():
            self.assertTrue(any(test(t) for t in singles), name)

    @unittest.skipIf(QUICK, "slow: builds the bank twice")
    def test_b7_same_seed_same_files(self):
        first = puzzle_make_bank(2026)
        second = puzzle_make_bank(2026)
        self.assertEqual(first, second)
        with tempfile.TemporaryDirectory(prefix="rush01-bank-") as tmp:
            puzzle_save_bank(tmp, first)
            names = sorted(os.listdir(tmp))
            self.assertEqual(names, sorted(os.listdir(BANK_DIR)))
            for name in names:
                with open(os.path.join(tmp, name), "rb") as fh:
                    made = fh.read()
                with open(os.path.join(BANK_DIR, name), "rb") as fh:
                    committed = fh.read()
                self.assertEqual(made, committed, name + " is stale")
            self.assertEqual(puzzle_load_bank(tmp), self.bank)
        for group, entries in first.items():
            ids = [entry["id"] for entry in entries]
            self.assertEqual(ids, ["%s-%02d" % (group, k + 1)
                                   for k in range(len(ids))])
        size = sum(os.path.getsize(os.path.join(BANK_DIR, name))
                   for name in os.listdir(BANK_DIR))
        self.assertLess(size, 200 * 1024)

    def test_b8_9x9_under_2s(self):
        entry = [e for e in self.groups["bonusN"]
                 if e["n"] == 9 and e["expect"] == "grid"][0]
        start = time.monotonic()
        found = puzzle_solve(9, entry["clues"], limit=1)
        took = time.monotonic() - start
        self.assertEqual(len(found["solutions"]), 1)
        self.assertTrue(is_correct(9, entry["clues"], found["solutions"][0]))
        self.assertLess(took, 2.0)

    def test_b9_transposed_team(self):
        picked = [e for e in self.groups["ok4"]
                  if len({tuple(s) for s in sides(e["clues"])}) == 4][:5]
        self.assertEqual(len(picked), 5)
        cases = []
        for entry in picked:
            top, bottom, left, right = sides(entry["clues"])
            cases.append(team_case(entry, left + right + top + bottom))
        diagnosis = puzzle_diagnose(cases)
        self.assertIsNotNone(diagnosis["best"], diagnosis)
        self.assertEqual(diagnosis["best"]["id"], "transpose")
        self.assertEqual(diagnosis["best"]["contradicted"], 0)
        self.assertEqual([m["id"] for m in puzzle_misreadings()], CONTRACT_IDS)

    def test_b10_error_where_misreading_has_no_solution(self):
        valid = [e for g in ("ok4", "multi4", "slow4") for e in self.groups[g]]
        # a team that indexes the bottom clues backwards: Error wherever
        # that puzzle has no solution, a (wrong) grid on the others
        cases = []
        for entry in valid:
            top, bottom, left, right = sides(entry["clues"])
            cases.append(team_case(entry, top + bottom[::-1] + left + right))
        errors = [c for c in cases if c["outcome"] == "error"]
        self.assertGreaterEqual(len(errors), 2)
        diagnosis = puzzle_diagnose(cases)
        self.assertEqual(diagnosis["best"]["id"], "reverse_bottom")
        # bottom clues read top-down: no valid puzzle has a solution then
        # (the column with N on top shows 1 from the top, >= 2 from the
        # bottom), so that team prints Error everywhere, like the +1
        # counter or a program that always prints Error: the diagnosis
        # must say they all fit, never pick one (AGENTS.md rule 1)
        cases = [{"id": e["id"], "n": 4, "clues": e["clues"],
                  "outcome": "error", "grid": None, "correct": False}
                 for e in valid]
        diagnosis = puzzle_diagnose(cases)
        self.assertIsNone(diagnosis["best"])
        note = " ".join(diagnosis["extra"])
        self.assertIn("bottom clues read top-down", note)
        self.assertIn("counter starts at 1", note)

    def test_b11_correct_grids_no_best(self):
        cases = []
        for entry in self.bank:
            if entry["n"] != 4 or entry["clues"] is None:
                continue
            cases.append(team_case(entry, entry["clues"]))
        diagnosis = puzzle_diagnose(cases)
        self.assertIsNone(diagnosis["best"])
        self.assertTrue(all(m["explains"] == 0 for m in diagnosis["all"]))

    def test_b12_zero_based_heights(self):
        grid = [[value - 1 for value in row] for row in PDF_GRID]
        cases = [{"id": "ok4-01", "n": 4, "clues": PDF, "outcome": "grid",
                  "grid": grid, "correct": False}]
        diagnosis = puzzle_diagnose(cases)
        self.assertTrue(any("0..N-1" in line and "+ 1" in line
                            for line in diagnosis["extra"]), diagnosis)

    def test_b13_check_non_latin(self):
        grid = [[1, 2, 3, 4], [1, 2, 3, 4], [3, 4, 1, 2], [4, 1, 2, 3]]
        check = puzzle_check(4, PDF, grid)
        self.assertFalse(check["latin"])
        self.assertIn({"side": "left", "index": 1, "want": 3, "seen": 4},
                      check["broken"])
        self.assertTrue(puzzle_check(4, PDF, PDF_GRID)["latin"])
        self.assertEqual(puzzle_check(4, PDF, PDF_GRID)["broken"], [])


if __name__ == "__main__":
    unittest.main()
