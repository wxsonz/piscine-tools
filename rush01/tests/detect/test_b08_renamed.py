"""B8: the same code with functions renamed f1, f2, ... (and the arrays
renamed) -> the same verdicts: signals come from structure, not names."""

import re
import unittest

from c_team import TeamCase, team_files
from test_b01_catalog_ids import PRINT_LINE, SOLVE_CLUE_LINE


def rename(files):
    """ft_* -> f1, f2, ...; grid -> g; clues -> t."""
    names = sorted({m for text in files.values()
                    for m in re.findall(r"\bft_\w+", text)})
    table = {n: f"f{k + 1}" for k, n in enumerate(names)}
    table.update({"grid": "g", "clues": "t"})
    out = {}
    for name, text in files.items():
        out[name] = re.sub(r"\b(%s)\b" % "|".join(map(re.escape, table)),
                           lambda m: table[m.group(1)], text)
    return out


class TestB8Renamed(TeamCase):

    def same_verdicts(self, files):
        a = self.detect(files)["parts"]
        renamed = rename(files)
        self.assertNotIn("ft_solve", renamed["solve.c"])
        b = self.detect(renamed)["parts"]
        for part in a:
            self.assertEqual((a[part]["id"], a[part]["confidence"]),
                             (b[part]["id"], b[part]["confidence"]),
                             f"{part}: {self.explain(b[part])}")

    def test_default_team(self):
        self.same_verdicts(team_files())

    def test_clue_line_and_line_buffer(self):
        self.same_verdicts(team_files(solve=SOLVE_CLUE_LINE,
                                      print=PRINT_LINE))


if __name__ == "__main__":
    unittest.main()
