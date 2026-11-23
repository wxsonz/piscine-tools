"""B3: /team/<name> shows the strip, four part cards, the run table by group
with the diagnosis line, the 3D view, source + call graph. Here: the page and
the JSON it is drawn from; the drawing itself is B6's browser check."""

import json
import tempfile
import unittest

import fake_app as F


class TestB3Team(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory(prefix="rush01-web-b3-")
        cls.fake = F.fake_make(cls.tmp.name)
        cls.fake["gate"].set()
        cls.base = F.fake_serve(cls.fake["app"])
        F.fake_wait_status(cls.base, "c01", ("done",))
        F.fake_wait_status(cls.base, "d3", ("done",))

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def get_json(self, path):
        code, body = F.fake_get(self.base + path)
        self.assertEqual(code, 200, path)
        return json.loads(body)

    def test_page(self):
        code, body = F.fake_get(self.base + "/team/c01")
        self.assertEqual(code, 200)
        for part in (b"team.js", b"sky3d.js", b'id="parts"', b'id="runs"',
                     b'id="sky"', b'id="source"', b'id="strip"'):
            self.assertIn(part, body)
        for name in ("page.js", "team.js", "sky3d.js", "rush01.css",
                     "notebook.css"):
            code, _ = F.fake_get(self.base + "/www/" + name)
            self.assertEqual(code, 200, name)

    def test_team_json(self):
        data = self.get_json("/api/team/c01")
        self.assertEqual(data["status"], "done")
        report = data["report"]
        self.assertEqual(sorted(report["detect"]["parts"]),
                         ["data", "parse", "print", "solve"])
        self.assertEqual(report["judge"]["diagnosis"]["best"]["explains"], 8)

    def test_source_and_graph(self):
        data = self.get_json("/api/source/c01")
        paths = [f["path"] for f in data["files"]]
        self.assertEqual(paths, ["ex00/main.c", "ex00/print.c",
                                 "ex00/solve.c", "ex00/rush.h"])
        main = data["files"][0]
        self.assertEqual(main["id"], "f-ex00-main-c")
        self.assertIn('id="f-ex00-main-c-L12"', main["html"])
        self.assertIn("<svg", data["graph"])
        self.assertIn("parse_clues", data["graph"])
        self.assertIn(">write<", data["graph"])
        self.assertEqual(data["notes"], [])

    def test_forbidden_marked(self):
        data = self.get_json("/api/source/d3")
        self.assertIn("FORBIDDEN", data["graph"])
        main = [f for f in data["files"] if f["path"] == "ex00/main.c"][0]
        self.assertIn('class="sl badl" id="f-ex00-main-c-L66"', main["html"])

    def test_catalog(self):
        ids = [e["id"] for e in self.get_json("/api/catalog")]
        self.assertIn("solve.bt_end", ids)


if __name__ == "__main__":
    unittest.main()
