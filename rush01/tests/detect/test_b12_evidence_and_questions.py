"""B12: every verdict has 2-5 evidence lines (or `where` when
unrecognized), and the catalog's questions; the catalog has every id of
PLAN.md §7.3."""

import unittest

from c_team import TeamCase, team_files
from detect import detect_catalog
import test_b01_catalog_ids as b1
from test_b09_hello_world import HELLO

PLAN_IDS = """
parse.fixed parse.scan parse.split parse.atoi parse.fsm parse.none
data.grid2d data.padded data.malloc2d data.flat data.char data.struct
data.bits data.cand
solve.hardcode solve.brute16 solve.brute_perm_loops solve.bt_end
solve.bt_unique solve.bt_clue_line solve.bt_iter solve.row_perm
solve.prefill solve.cands solve.bits solve.partial_prune solve.mrv
solve.propagate solve.line_solver solve.dlx
print.char print.line print.board print.putstr
""".split()

TEAMS = [team_files(), team_files(parse=b1.PARSE_SCAN, print=b1.PRINT_LINE),
         team_files(solve=b1.SOLVE_CLUE_LINE, print=b1.PRINT_PUTSTR),
         team_files(main=b1.MAIN_PREFILL, prefill=b1.PREFILL,
                    solve=b1.SOLVE_PREFILL_AWARE),
         team_files(solve=b1.SOLVE_CANDS), b1.PADDED,
         {"main.c": b1.HARDCODE_MAIN}, {"hello.c": HELLO}]


class TestB12EvidenceAndQuestions(TeamCase):

    def test_catalog_has_every_plan_id(self):
        cat = detect_catalog()
        self.assertEqual(sorted(e["id"] for e in cat), sorted(PLAN_IDS))
        for e in cat:
            self.assertEqual(e["part"], e["id"].split(".")[0])
            self.assertTrue(1 <= len(e["questions"]) <= 3, e["id"])
            self.assertTrue(e["name"] and e["explain"] and e["demo"])
            if e["part"] == "solve":
                self.assertIn(e["tier"], (0, 1, 2, 3), e["id"])
            else:
                self.assertIsNone(e["tier"], e["id"])

    def test_every_verdict(self):
        cat = {e["id"]: e for e in detect_catalog()}
        for files in TEAMS:
            for part, v in self.detect(files)["parts"].items():
                msg = f"{part}: {self.explain(v)}"
                self.assertTrue(v["where"], msg)
                self.assertTrue(v["questions"], msg)
                if v["id"] is None:
                    continue
                self.assertTrue(2 <= len(v["evidence"]) <= 5, msg)
                for e in v["evidence"]:
                    self.assertEqual(set(e), {"file", "line", "text", "why"})
                    self.assertTrue(e["text"] and e["why"], msg)
                want = cat[v["id"]]["questions"]
                self.assertEqual(v["questions"][:len(want)], want, msg)
                self.assertEqual(v["name"], cat[v["id"]]["name"])
                if part == "solve":
                    self.assertEqual(v["tier"], cat[v["id"]]["tier"])
                else:
                    self.assertIsNone(v["tier"])
                if v["confidence"] == "mix":
                    self.assertTrue(v["also"], msg)


if __name__ == "__main__":
    unittest.main()
