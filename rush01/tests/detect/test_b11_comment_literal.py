"""B11: `'1'` inside a comment is not a signal (literals come from code
only, never from comments)."""

import unittest

from c_team import TeamCase, team_files
from test_b01_catalog_ids import MAIN_NO_PARSE_CHECK

PARSE_COMMENTED = """\
void    ft_parse(char *str, int *clues)
{
    int    i;

    /* if (str[i * 2] < '1' || str[i * 2] > '4')
        return (0); */
    i = 0;
    while (i < 16)
    {
        // if (str[i * 2 + 1] != ' ') return (0);
        clues[i] = str[i * 2] - '0';
        i++;
    }
}
"""


class TestB11CommentLiteral(TeamCase):

    def test_commented_checks_do_not_count(self):
        v = self.assert_id(team_files(parse=PARSE_COMMENTED,
                                      main=MAIN_NO_PARSE_CHECK), "parse",
                           "parse.none")
        comment_lines = {5, 6, 10}
        for e in v["evidence"]:
            self.assertFalse(e["file"] == "ex00/parse.c"
                             and e["line"] in comment_lines, e)


if __name__ == "__main__":
    unittest.main()
