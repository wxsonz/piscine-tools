"""B16: the eval sheet's stops, in its order: no ex00/ (0, over), norm
error (stops), extraneous files (check), build failure, forbidden calls
(check, the subject's rule), a failed eliminatory test (no points)."""

import tempfile
import unittest

from judge_fixtures import PDF_TEXT, SUBJECT, answer_program, entry, run_judge
from judge.judge_sheet import sheet_stops

ELIM = entry("evalsheet-05", ["Hello"], None, "error")
GOOD = answer_program([("x", "Error\n", "")])          # Error\n for all
BAD = answer_program([("x", "Error\n", "")], default_out=PDF_TEXT)  # a grid
NO_SEMI = "int\tmain(void)\n{\n\treturn (0)\n}\n"


def keys(r):
    return [(s["key"], s["level"]) for s in r["stops"]]


class TestB16SheetStops(unittest.TestCase):
    def test_clean_team_has_no_stop(self):
        with tempfile.TemporaryDirectory() as tmp:
            r = run_judge(tmp, {"ex00/main.c": GOOD}, [ELIM],
                          dict(SUBJECT, norm_flags=[]))
        self.assertNotIn("eliminatory", [k for k, _ in keys(r)])
        self.assertNotIn("no_ex_dir", [k for k, _ in keys(r)])

    def test_eliminatory_failure_stops(self):
        with tempfile.TemporaryDirectory() as tmp:
            r = run_judge(tmp, {"ex00/main.c": BAD}, [ELIM])
        self.assertIn(("eliminatory", "stop"), keys(r))
        stop = [s for s in r["stops"] if s["key"] == "eliminatory"][0]
        self.assertIn("evalsheet-05", stop["text"])
        self.assertIn("don't give them any points", stop["sheet"])

    def test_no_ex_dir_and_build_failure(self):
        with tempfile.TemporaryDirectory() as tmp:
            r = run_judge(tmp, {"main.c": NO_SEMI, ".notes.swp": "x"}, [ELIM])
        got = keys(r)
        self.assertEqual(got[0], ("no_ex_dir", "stop"))
        self.assertIn(("files", "check"), got)
        self.assertIn(("build", "stop"), got)

    def test_order_follows_the_sheet(self):
        result = {"files": {"no_ex_dir": True, "sources": ["a.c"],
                            "flagged": [{"path": ".x", "why": "hidden file"}]},
                  "norm": {"ran": True, "ok": False, "note": "",
                           "errors": [{"file": "a.c", "line": 1, "text": "x"}]},
                  "built": True, "build_log": "",
                  "forbidden": {"names": [{"name": "printf"}], "notes": []},
                  "runs": [{"id": "evalsheet-01", "group": "evalsheet",
                            "verdict": "fail"}]}
        got = [s["key"] for s in sheet_stops(result, SUBJECT)]
        self.assertEqual(got, ["no_ex_dir", "norm", "files", "forbidden",
                               "eliminatory"])


if __name__ == "__main__":
    unittest.main()
