"""B5: pre-fill + backtracking -> confidence "mix", id solve.prefill, and
`also` has the search entry."""

import unittest

from c_team import TeamCase, team_files
from test_b01_catalog_ids import MAIN_PREFILL, PREFILL, SOLVE_PREFILL_AWARE

PREFILL_PAIR = """\
void    ft_prefill(int grid[4][4], int *clues)
{
    int    i;

    i = 0;
    while (i < 4)
    {
        if (clues[8 + i] + clues[12 + i] == 5)
            grid[i][clues[8 + i] - 1] = 4;
        i++;
    }
}
"""


class TestB5PrefillMix(TeamCase):

    def check_mix(self, prefill):
        v = self.part(team_files(main=MAIN_PREFILL, prefill=prefill,
                                 solve=SOLVE_PREFILL_AWARE), "solve")
        self.assertEqual(v["id"], "solve.prefill", self.explain(v))
        self.assertEqual(v["confidence"], "mix", self.explain(v))
        self.assertIn("solve.bt_unique", v["also"], self.explain(v))
        return v

    def test_clue_four_and_one(self):
        v = self.check_mix(PREFILL)
        whys = " ".join(e["why"] for e in v["evidence"])
        self.assertIn("clue of 4", whys)
        self.assertIn("clue of 1", whys)

    def test_pair_sum(self):
        v = self.check_mix(PREFILL_PAIR)
        self.assertTrue(any("N + 1" in e["why"] for e in v["evidence"]),
                        self.explain(v))


if __name__ == "__main__":
    unittest.main()
