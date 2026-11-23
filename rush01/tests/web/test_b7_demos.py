"""B7 & B8: preset demos for every catalog entry, /team/<name> "show how it
works" button, /library page and side-by-side compare mode.

1. Pure generator checks in node: every entry of detect_catalog() has a
   generator in demos_gen.js; every real solver produces a valid grid whose
   sightlines match the clues; capped brute-force demos report their cap;
   hardcode matches only the PDF example.
2. HTTP route checks for /library and the demo JS assets.
3. Headless chromium check (skipped without node + chromium)."""

import json
import os
import shutil
import subprocess
import tempfile
import unittest

import fake_app as F
from detect import detect_catalog

DEMOS = os.path.join(F.RUSH01, "tool", "web", "www", "demos_gen.js")
SKY = os.path.join(F.RUSH01, "tool", "web", "www", "sky3d.js")


def node_eval(expr_js):
    script = (f"const D = require({json.dumps(DEMOS)});\n"
              f"const S = require({json.dumps(SKY)});\n"
              f"console.log(JSON.stringify({expr_js}));")
    p = subprocess.run(["node", "-e", script], capture_output=True,
                       text=True, timeout=30)
    if p.returncode != 0:
        raise AssertionError(p.stderr)
    return json.loads(p.stdout)


@unittest.skipUnless(shutil.which("node"), "needs node to run demos_gen.js")
class TestB7Generators(unittest.TestCase):
    def test_every_catalog_entry_has_a_demo(self):
        catalog = detect_catalog()
        keys = set(node_eval("Object.keys(D.DEMO_GENERATORS)"))
        missing = [e["demo"] for e in catalog if e["demo"] not in keys]
        self.assertEqual(missing, [], f"missing demo generators: {missing}")

    def test_parse_data_print_generators(self):
        catalog = [e for e in detect_catalog() if e["part"] != "solve"]
        ids = [e["demo"] for e in catalog]
        got = node_eval(
            "%s.map(function (id) {"
            " const r = D.demo_run(id, 'asym');"
            " return {id: id, kind: r.kind, n: r.steps.length, total: r.total};"
            "})" % json.dumps(ids)
        )
        for item in got:
            self.assertGreater(item["n"], 1, item)
            self.assertGreaterEqual(item["total"], item["n"], item)

    def test_solvers_produce_valid_grids_or_honest_caps(self):
        capped_ids = {"solve_brute16", "solve_bt_end"}
        exact_ids = [
            "solve_bt_unique", "solve_bt_clue_line", "solve_bt_iter",
            "solve_row_perm", "solve_prefill", "solve_cands",
            "solve_bits", "solve_partial_prune", "solve_mrv",
            "solve_propagate", "solve_line_solver", "solve_dlx",
        ]
        # 1. real solvers must find a valid grid matching all 16 clues on pdf & asym
        for pid in ("pdf", "asym"):
            got = node_eval(
                "%s.map(function (id) {"
                " const r = D.demo_run(id, %s);"
                " return {id: id, solved: r.solved, capped: r.capped,"
                "  total: r.total, clues: r.clues,"
                "  seen: r.grid ? S.sky_counts(r.grid) : null};"
                "})" % (json.dumps(exact_ids), json.dumps(pid))
            )
            for item in got:
                self.assertTrue(item["solved"], (pid, item))
                self.assertFalse(item["capped"], (pid, item))
                self.assertEqual(item["seen"], item["clues"], (pid, item))
        # 2. capped brute-force solvers report capped, never fake a solution
        got_cap = node_eval(
            "%s.map(function (id) {"
            " const r = D.demo_run(id, 'asym');"
            " return {id: id, solved: r.solved, capped: r.capped,"
            "  last: r.steps[r.steps.length - 1].op};"
            "})" % json.dumps(sorted(capped_ids))
        )
        for item in got_cap:
            self.assertFalse(item["solved"], item)
            self.assertTrue(item["capped"], item)
            self.assertEqual(item["last"], "cap", item)
        # 3. brute_perm_loops either solves genuinely or caps honestly
        bpl = node_eval(
            "(function () {"
            " const r = D.demo_run('solve_brute_perm_loops', 'pdf');"
            " return {solved: r.solved, capped: r.capped,"
            "  clues: r.clues, seen: r.grid ? S.sky_counts(r.grid) : null};"
            "})()"
        )
        self.assertTrue(bpl["solved"] or bpl["capped"], bpl)
        if bpl["solved"]:
            self.assertEqual(bpl["seen"], bpl["clues"])
        # 4. hardcode succeeds on pdf and fails on asym
        hc = node_eval(
            "[D.demo_run('solve_hardcode', 'pdf').solved,"
            " D.demo_run('solve_hardcode', 'asym').solved]"
        )
        self.assertEqual(hc, [True, False])


class TestB8RoutesAndBrowser(unittest.TestCase):
    def test_library_routes(self):
        with tempfile.TemporaryDirectory(prefix="rush01-web-b8-") as root:
            fake = F.fake_make(root)
            fake["gate"].set()
            base = F.fake_serve(fake["app"])
            code, body = F.fake_get(base + "/library")
            self.assertEqual(code, 200)
            for tok in (b"library.js", b"demos_gen.js", b"demos_ui.js",
                        b"sky3d.js", b"preset"):
                self.assertIn(tok, body)
            for asset in ("demos_gen.js", "demos_ui.js", "library.js"):
                ac, _ = F.fake_get(base + "/www/" + asset)
                self.assertEqual(ac, 200, asset)

    def test_browser_demos_and_library(self):
        tools = F.fake_browser_tools()
        if isinstance(tools, str):
            self.skipTest(tools)
        with tempfile.TemporaryDirectory(prefix="rush01-web-b8b-") as root:
            fake = F.fake_make(root)
            fake["gate"].set()
            base = F.fake_serve(fake["app"])
            F.fake_wait_status(base, "c01", ("done",))
            res = F.fake_browser(tools, base, "demos")
        self.assertEqual(res["errors"], [])
        self.assertTrue(res["facts"]["modal"]["open"])
        self.assertIn("preset", res["facts"]["modal"]["banner"].lower())
        self.assertGreaterEqual(res["facts"]["library"]["items"], 7)
        self.assertIn("preset", res["facts"]["library"]["banner"].lower())
        # the catalog filter: "t2" keeps tier 2 only; nonsense shows a note
        self.assertEqual(res["facts"]["library"]["t2"], ["T2"])
        self.assertTrue(res["facts"]["library"]["none"])
        self.assertTrue(res["facts"]["compare"]["visible"])
        self.assertEqual(res["facts"]["compare"]["left_boxes"], 16)
        self.assertEqual(res["facts"]["compare"]["right_boxes"], 16)
        self.assertIn("vs", res["facts"]["compare"]["summary"])
        # the VS race: both ended at "end both", each stamp says its steps
        self.assertIn("steps", res["facts"]["compare"]["vs_l"])
        self.assertIn("steps", res["facts"]["compare"]["vs_r"])


if __name__ == "__main__":
    unittest.main()
