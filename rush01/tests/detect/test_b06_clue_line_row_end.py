"""B6: row clues checked at `col == 3`, column clues only when full ->
solve.bt_clue_line with fact row-end (and col-end for the mirror case)."""

import unittest

from c_team import TeamCase, team_files
from test_b01_catalog_ids import SOLVE_CLUE_LINE

SOLVE_COL_END = SOLVE_CLUE_LINE.replace(
    "ft_row_ok(int grid[4][4], int *clues, int row)",
    "ft_col_ok(int grid[4][4], int *clues, int col)").replace(
    "ft_count_row(grid, row, 0) == clues[8 + row]",
    "ft_count_col(grid, col, 0) == clues[col]").replace(
    "ft_count_row(grid, row, 1) == clues[12 + row]",
    "ft_count_col(grid, col, 1) == clues[4 + col]").replace(
    "(c != 3 || ft_row_ok(grid, clues, r))",
    "(r != 3 || ft_col_ok(grid, clues, c))")


class TestB6ClueLineRowEnd(TeamCase):

    def clue_fact(self, v):
        facts = [f["text"] for f in v["facts"] if f["key"] == "clue_check"]
        self.assertEqual(len(facts), 1, self.explain(v))
        return facts[0]

    def test_row_end(self):
        v = self.assert_id(team_files(solve=SOLVE_CLUE_LINE), "solve",
                           "solve.bt_clue_line")
        self.assertTrue(self.clue_fact(v).startswith("row-end"),
                        self.explain(v))

    def test_col_end(self):
        v = self.assert_id(team_files(solve=SOLVE_COL_END), "solve",
                           "solve.bt_clue_line")
        self.assertTrue(self.clue_fact(v).startswith("col-end"),
                        self.explain(v))


if __name__ == "__main__":
    unittest.main()
