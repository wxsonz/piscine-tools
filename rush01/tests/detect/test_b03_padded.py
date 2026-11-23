"""B3: `int b[6][6]` with the clues on the border -> data.padded (also when
the size is written `N + 2`)."""

import unittest

from c_team import TeamCase
from test_b01_catalog_ids import PADDED


class TestB3Padded(TeamCase):

    def test_six_by_six(self):
        v = self.assert_id(PADDED, "data", "data.padded")
        layout = [f["text"] for f in v["facts"] if f["key"] == "clue_layout"]
        self.assertTrue(layout and "border" in layout[0], self.explain(v))

    def test_n_plus_two(self):
        files = {name: "#define N 4\n\n" + text.replace("[6][6]",
                                                         "[N + 2][N + 2]")
                 for name, text in PADDED.items()}
        self.assert_id(files, "data", "data.padded")


if __name__ == "__main__":
    unittest.main()
