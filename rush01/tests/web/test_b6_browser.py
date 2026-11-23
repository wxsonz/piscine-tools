"""B6: the pages load without JS errors on the report fixture, in headless
chromium (node + playwright-core). Skipped without them, or when
RUSH01_NO_BROWSER is set."""

import tempfile
import unittest

import fake_app as F


class TestB6Browser(unittest.TestCase):
    def test_pages_load(self):
        tools = F.fake_browser_tools()
        if isinstance(tools, str):
            self.skipTest(tools)
        with tempfile.TemporaryDirectory(prefix="rush01-web-b6-") as root:
            fake = F.fake_make(root)
            fake["gate"].set()
            base = F.fake_serve(fake["app"])
            F.fake_wait_status(base, "c01", ("done",))
            F.fake_wait_status(base, "d3", ("done",))
            res = F.fake_browser(tools, base, "load")
        self.assertEqual(res["errors"], [])
        facts = res["facts"]
        # dashboard list: one row per team, 4 parts each, a link when
        # evaluated; "failing" keeps d3 (no build); the search box filters
        rows = facts["list"]["rows"]
        self.assertEqual(sorted(rows), ["c01", "d3"])
        self.assertEqual(rows["c01"]["parts"], 4)
        self.assertEqual(rows["d3"]["unrec"], 1)
        # the result is the eval sheet's: both stop at norm (the fixture)
        self.assertEqual(rows["d3"]["stamp"], "STOP norm")
        self.assertEqual(rows["c01"]["stamp"], "STOP norm")
        self.assertTrue(rows["c01"]["link"])
        self.assertEqual(sorted(facts["list"]["stop_shown"]), ["c01", "d3"])
        self.assertEqual(facts["list"]["find_shown"], ["c01"])
        self.assertTrue(facts["list"]["nomatch"])
        # select view: the roster, ↓ picks the first team, its card shows
        sel = facts["select"]
        self.assertEqual(sel["roster"], 2)
        self.assertEqual(sel["on"], sel["preview"])
        self.assertEqual(sel["chips"], 4)
        # dashboard cards: both teams, 4 verdict chips and 3 hearts each
        self.assertEqual(facts["dash"]["c01"]["chips"], 4)
        self.assertEqual(facts["dash"]["c01"]["hearts"], 3)
        self.assertEqual(facts["dash"]["d3"]["unrec"], 1)
        self.assertIn("STOP", facts["dash"]["d3"]["stamp"])
        # c01: every section drawn
        c01 = facts["c01"]
        self.assertEqual(c01["parts"], 4)
        self.assertEqual(c01["unrec"], 0)
        self.assertIn("8 of 8 failures fit", c01["diag"])
        self.assertEqual(c01["groups"], 8)
        self.assertEqual(c01["boxes"], 16)
        self.assertEqual(c01["files"], 4)
        self.assertTrue(c01["graph"])
        # the gates: the sheet's 7 steps; c01 stops at norm (gate 2), the
        # gates after it are marked; the HUD names the stop
        self.assertEqual(len(c01["gates"]), 7)
        self.assertEqual(c01["gates"][1], "stop")
        self.assertTrue(all("after" in g for g in c01["gates"][2:]))
        self.assertIn("STOP norm", c01["hud"])
        self.assertEqual(c01["slots"], 4)
        self.assertEqual(c01["deck_runs"], {"runs": True, "parts": False})
        self.assertTrue(c01["gate_norm"])
        # d3: no build, an unrecognized part, no 3D blocks
        d3 = facts["d3"]
        self.assertEqual(d3["parts"], 4)
        self.assertEqual(d3["unrec"], 1)
        self.assertIn("does not build", d3["diag"])
        self.assertTrue(d3["sky_empty"])
        # d3: the build gate stops too
        self.assertEqual(d3["gates"][2].split()[0], "stop")
        self.assertEqual(d3["files"], 2)


if __name__ == "__main__":
    unittest.main()
