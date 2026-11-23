"""B5: unknown team / bad path -> 404; paths can't leave repo_dir_abs."""

import base64
import json
import os
import tempfile
import unittest

import fake_app as F


class TestB5Paths(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory(prefix="rush01-web-b5-")
        root = cls.tmp.name
        cls.fake = F.fake_make(root)
        cls.fake["gate"].set()
        # a secret next to the repo, and a team file that links to it
        cls.secret = os.path.join(root, "secret.c")
        with open(cls.secret, "w") as fh:
            fh.write("int secret_marker_42;\n")
        os.symlink(cls.secret, os.path.join(cls.fake["repo"], "c01", "ex00",
                                            "evil.c"))
        cls.base = F.fake_serve(cls.fake["app"])
        F.fake_wait_status(cls.base, "c01", ("done",))

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def code(self, path, headers=None):
        return F.fake_get(self.base + path, headers)[0]

    def test_unknown_teams(self):
        for path in ("/team/nope", "/team/..%2F..%2Fetc", "/team/.trash",
                     "/team/", "/api/team/nope", "/api/team/%2e%2e",
                     "/api/team/..%2Freports", "/api/source/nope",
                     "/api/source/..", "/nothing"):
            self.assertEqual(self.code(path), 404, path)

    def test_static_stays_in_www(self):
        for path in ("/www/../web_server.py", "/www/%2e%2e/web_teams.py",
                     "/www/fonts/../../web_teams.py", "/www/",
                     "/www/..%2F..%2F..%2FAGENTS.md"):
            self.assertEqual(self.code(path), 404, path)
        # the links into rush00 are on purpose and work
        self.assertEqual(self.code("/www/notebook.css"), 200)
        self.assertEqual(self.code("/www/fonts/PatrickHand-Regular.ttf"), 200)

    def test_source_never_reads_outside(self):
        path = os.path.join(self.fake["reports"], "c01.json")
        with open(path, encoding="utf-8") as fh:
            report = json.load(fh)
        report["judge"]["files"]["sources"] += ["ex00/evil.c",
                                                "../../secret.c"]
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(report, fh)
        code, body = F.fake_get(self.base + "/api/source/c01")
        self.assertEqual(code, 200)
        self.assertNotIn(b"secret_marker_42", body)
        notes = json.loads(body)["notes"]
        self.assertEqual(len(notes), 2)
        for note in notes:
            self.assertIn("outside the team folder", note)

    def test_upload_paths(self):
        b64 = base64.b64encode(b"x").decode()
        bad = [{"team": "../x", "files": [{"path": "a.c", "b64": b64}]},
               {"team": ".hidden", "files": [{"path": "a.c", "b64": b64}]},
               {"team": "ok1", "files": [{"path": "../../evil.c",
                                          "b64": b64}]},
               {"team": "ok2", "files": [{"path": "/etc/evil.c",
                                          "b64": b64}]}]
        for body in bad:
            code, _ = F.fake_post(self.base + "/api/upload", body)
            self.assertEqual(code, 400, body)
        for name in ("evil.c", "x", "ok1", "ok2"):
            self.assertFalse(os.path.exists(os.path.join(self.tmp.name,
                                                         name)))
            self.assertFalse(os.path.exists(os.path.join(self.fake["repo"],
                                                         name)))

    def test_only_local_and_json(self):
        self.assertEqual(self.code("/", {"Host": "evil.example"}), 403)
        self.assertEqual(self.code("/", {"Host": "localhost:4243"}), 200)
        code, _ = F.fake_post(self.base + "/api/rerun", {"all": True},
                              ctype="text/plain")
        self.assertEqual(code, 415)


if __name__ == "__main__":
    unittest.main()
