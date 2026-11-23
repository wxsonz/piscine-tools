"""B4: the 3D view draws a team's output for any bank puzzle: blocks by
height, clues on the base, top / front / iso; clicking a clue lights the
sightline (visible teal, hidden faded, count shown, orange if wrong);
fallback 2D grid, same sightlines.

1. the sightline logic of sky3d.js, run in node, must agree with the judge's
   `broken` clues on every run of the fixture (no browser needed);
2. the drawing, in headless chromium (skipped without it)."""

import json
import os
import shutil
import subprocess
import tempfile
import unittest

import fake_app as F

SKY = os.path.join(F.RUSH01, "tool", "web", "www", "sky3d.js")
SIDES = ["top", "bottom", "left", "right"]


def node_eval(expr_js):
    script = (f"const S = require({json.dumps(SKY)});\n"
              f"console.log(JSON.stringify({expr_js}));")
    p = subprocess.run(["node", "-e", script], capture_output=True,
                       text=True, timeout=30)
    if p.returncode != 0:
        raise AssertionError(p.stderr)
    return json.loads(p.stdout)


@unittest.skipUnless(shutil.which("node"), "needs node to run sky3d.js")
class TestB4Lines(unittest.TestCase):
    def test_clues_from_argv(self):
        pdf = "4 3 2 1 1 2 2 2 4 3 2 1 1 2 2 2"
        cases = [[pdf], [], [pdf, pdf], [pdf + " "], [" " + pdf],
                 [pdf.replace(" ", "  ", 1)], ["2 " * 17 + "2"],
                 [pdf[:-1] + "5"], [" ".join(["1"] * 40)],
                 [" ".join(["9"] * 36)], ["1 1 1 1"]]
        got = node_eval("%s.map(S.sky_clues_from_argv)" % json.dumps(cases))
        self.assertEqual(got[0]["n"], 4)
        self.assertEqual(got[0]["clues"][:4], [4, 3, 2, 1])
        self.assertEqual(got[1:9], [None] * 8)
        self.assertEqual(got[9]["n"], 9)
        self.assertEqual(got[10]["n"], 1)

    def test_lines_and_seen(self):
        got = node_eval("[S.sky_line(4, 'top', 1), S.sky_line(4, 'bottom', 2),"
                        " S.sky_line(4, 'left', 0), S.sky_line(4, 'right', 3),"
                        " S.sky_seen([2, 1, 4, 3])]")
        self.assertEqual(got[0], [[0, 1], [1, 1], [2, 1], [3, 1]])
        self.assertEqual(got[1], [[3, 2], [2, 2], [1, 2], [0, 2]])
        self.assertEqual(got[2], [[0, 0], [0, 1], [0, 2], [0, 3]])
        self.assertEqual(got[3], [[3, 3], [3, 2], [3, 1], [3, 0]])
        self.assertEqual(got[4], {"count": 2,
                                  "visible": [True, False, True, False]})

    def test_agrees_with_the_judge(self):
        with open(F.FIXTURE, encoding="utf-8") as fh:
            runs = json.load(fh)["judge"]["runs"]
        runs = [r for r in runs if r["grid"] and r["expect"] == "grid"]
        self.assertGreater(len(runs), 5)
        got = node_eval("%s.map(function (r) { return "
                        "[S.sky_clues_from_argv(r.argv), S.sky_counts(r.grid)]"
                        "; })" % json.dumps(runs))
        for run, (puzzle, counts) in zip(runs, got):
            n = puzzle["n"]
            broken = [{"side": SIDES[k // n], "index": k % n,
                       "want": puzzle["clues"][k], "seen": counts[k]}
                      for k in range(4 * n) if counts[k] != puzzle["clues"][k]]
            self.assertEqual(broken, run["broken"], run["id"])


class TestB4Browser(unittest.TestCase):
    def test_drawing(self):
        tools = F.fake_browser_tools()
        if isinstance(tools, str):
            self.skipTest(tools)
        with tempfile.TemporaryDirectory(prefix="rush01-web-b4-") as root:
            fake = F.fake_make(root)
            fake["gate"].set()
            base = F.fake_serve(fake["app"])
            F.fake_wait_status(base, "c01", ("done",))
            res = F.fake_browser(tools, base, "sky")
        self.assertEqual(res["errors"], [])
        facts = res["facts"]
        # a wrong 4x4 grid: 16 blocks, 16 clues, the broken ones orange
        self.assertEqual(facts["first"]["run"], "ok4-02")
        self.assertEqual(facts["first"]["boxes"], 16)
        self.assertEqual(facts["first"]["clues"], 16)
        self.assertEqual(facts["first"]["bad"], 6)
        # every clue: teal blocks = count shown, the rest of the line faded
        for line in facts["lines"]:
            self.assertEqual(line["seen"], line["count"], line)
            self.assertEqual(line["seen"] + line["hidden"], 4, line)
            self.assertEqual(line["shown"], str(line["count"]), line)
            self.assertEqual(line["bad"], line["count"] != line["want"], line)
        self.assertIn("rotateX(0deg)", facts["top"])
        self.assertEqual(facts["nine"], 81)
        self.assertTrue(facts["flat"]["visible"])
        self.assertEqual(facts["flat"]["cells"], 81)
        self.assertEqual(facts["flat"]["seen"], facts["flat"]["count"])
        self.assertEqual(facts["error_run"]["boxes"], 0)
        self.assertEqual(facts["error_run"]["msg"].strip(), "Error")


if __name__ == "__main__":
    unittest.main()
