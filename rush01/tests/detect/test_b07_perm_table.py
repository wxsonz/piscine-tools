"""B7: a 24-row permutation table -> solve.row_perm, not solve.hardcode
(the table is written out in the code, but it lists row orders)."""

import itertools
import unittest

from c_team import TeamCase, team_files
from test_b01_catalog_ids import SOLVE_ROW_PERM

TABLE = "".join("".join(str(v) for v in p)
                for p in itertools.permutations([1, 2, 3, 4]))

PERMS_LITERAL = """\
void    ft_fill_perms(int perms[24][4])
{
    char    *s;
    int     i;

    s = "%s";
    i = 0;
    while (i < 96)
    {
        perms[i / 4][i %% 4] = s[i] - '0';
        i++;
    }
}
""" % TABLE


class TestB7PermTable(TeamCase):

    def test_table_is_row_perm(self):
        v = self.assert_id(team_files(solve=SOLVE_ROW_PERM,
                                      perms=PERMS_LITERAL), "solve",
                           "solve.row_perm")
        self.assertNotIn("solve.hardcode", v["also"])


if __name__ == "__main__":
    unittest.main()
