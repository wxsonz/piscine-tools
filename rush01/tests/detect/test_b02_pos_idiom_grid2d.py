"""B2: `grid[pos / 4][pos % 4]` on `int grid[4][4]` -> data.grid2d, never
data.flat (a cell number split into row and column is still a 2D array)."""

import unittest

from c_team import TeamCase, team_files


class TestB2PosIdiomGrid2d(TeamCase):

    def test_pos_idiom_is_grid2d(self):
        # the default solver writes grid[pos / 4][pos % 4] = v
        v = self.assert_id(team_files(), "data", "data.grid2d")
        self.assertNotIn("data.flat", v["also"])
        self.assertTrue(any("pos / 4" in e["text"] for e in v["evidence"]),
                        self.explain(v))


if __name__ == "__main__":
    unittest.main()
