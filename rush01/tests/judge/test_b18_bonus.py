"""B18: the bonus size: the biggest N whose bonus puzzles all pass, from 5
up; counted only when everything mandatory passed (the sheet)."""

import unittest

from judge_fixtures import SUBJECT
from judge.judge_sheet import sheet_bonus


def run(eid, group, verdict):
    return {"id": eid, "group": group, "verdict": verdict}


BANK = [{"id": f"bonusN-{n}{k}", "n": n} for n in (5, 6, 7, 10) for k in (1, 2)]


def result(bonus, mandatory="pass"):
    runs = [run("ok4-01", "ok4", mandatory), run("small-01", "small", "info")]
    runs += [run(f"bonusN-{n}{k}", "bonusN", bonus.get(n, "pass"))
             for n in (5, 6, 7, 10) for k in (1, 2)]
    return {"runs": runs}


class TestB18Bonus(unittest.TestCase):
    def test_largest_consecutive_size(self):
        b = sheet_bonus(result({7: "fail"}), BANK, SUBJECT, [])
        self.assertEqual(b["sizes"], {"5": "pass", "6": "pass", "7": "fail"})
        self.assertEqual(b["largest_n"], 6)
        self.assertTrue(b["counted"])

    def test_not_counted_when_mandatory_fails(self):
        b = sheet_bonus(result({}, mandatory="fail"), BANK, SUBJECT, [])
        self.assertEqual(b["largest_n"], 7)
        self.assertFalse(b["counted"])
        self.assertIn("not counted", b["note"])

    def test_not_counted_after_a_stop(self):
        stops = [{"key": "norm", "level": "stop", "text": "", "sheet": ""}]
        self.assertFalse(sheet_bonus(result({}), BANK, SUBJECT, stops)["counted"])

    def test_five_fails(self):
        self.assertIsNone(sheet_bonus(result({5: "fail"}), BANK, SUBJECT,
                                      [])["largest_n"])


if __name__ == "__main__":
    unittest.main()
