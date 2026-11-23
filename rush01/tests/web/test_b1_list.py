"""B1: / lists every folder in repo_dir_abs with its state (queued, running,
done, error) and, when done, the four verdict names + hearts."""

import os
import tempfile
import unittest

import fake_app as F


class TestB1List(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="rush01-web-b1-")
        self.fake = F.fake_make(self.tmp.name)
        for name in ("boom1", "slow1"):
            os.makedirs(os.path.join(self.fake["repo"], name, "ex00"))
        self.base = F.fake_serve(self.fake["app"])

    def tearDown(self):
        self.fake["gate"].set()
        self.tmp.cleanup()

    def test_states_verdicts_hearts(self):
        base = self.base
        # 1. the worker takes teams in order: slow1 holds it, running
        F.fake_wait_status(base, "slow1", ("running",))
        state = F.fake_state(base)
        self.assertEqual(sorted(state), ["boom1", "c01", "d3", "slow1"])
        self.assertEqual(state["boom1"]["status"], "error")
        self.assertIn("on purpose", state["boom1"]["error"])
        # 2. a rerun while the worker is busy waits in the queue
        code, _ = F.fake_post(base + "/api/rerun", {"team": "c01"})
        self.assertEqual(code, 200)
        self.assertEqual(F.fake_state(base)["c01"]["status"], "queued")
        # 3. let it go: everything ends done
        self.fake["gate"].set()
        F.fake_wait_status(base, "c01", ("done",))
        F.fake_wait_status(base, "slow1", ("done",))
        state = F.fake_state(base)
        # 4. the four verdict names and the hearts' facts
        c01 = state["c01"]["summary"]
        names = [c01["parts"][p]["name"]
                 for p in ("parse", "data", "solve", "print")]
        self.assertEqual(names, ["Scan and count", "2D array",
                                 "Backtracking + clue check when a line "
                                 "is full", "One write per char"])
        self.assertTrue(c01["built"])
        self.assertEqual(c01["forbidden"], [])
        self.assertEqual(c01["norm"], {"ran": True, "ok": False})
        self.assertEqual(c01["diagnosis"]["best"]["id"], "transposed")
        d3 = state["d3"]["summary"]
        self.assertFalse(d3["built"])
        self.assertEqual(d3["forbidden"], ["atoi", "printf"])
        self.assertEqual(d3["parts"]["print"]["confidence"], "unrecognized")
        # 5. the page itself
        code, body = F.fake_get(base + "/")
        self.assertEqual(code, 200)
        self.assertIn(b"/www/dash.js", body)

    def test_report_not_matching_shapes_is_named(self):
        F.fake_wait_status(self.base, "c01", ("done",))
        path = os.path.join(self.fake["reports"], "c01.json")
        with open(path, "w", encoding="utf-8") as fh:
            fh.write('{"team": "c01"}')
        c01 = F.fake_state(self.base)["c01"]
        self.assertIsNone(c01["summary"])
        self.assertIn("SHAPES", c01["error"])


if __name__ == "__main__":
    unittest.main()
