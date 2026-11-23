"""B2: dropping a folder or pasting a git URL adds the team and evaluates it;
a team whose files change is re-evaluated (mtime scan)."""

import base64
import os
import tempfile
import time
import unittest

import fake_app as F


class TestB2Add(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="rush01-web-b2-")
        self.fake = F.fake_make(self.tmp.name)
        self.fake["gate"].set()
        self.base = F.fake_serve(self.fake["app"])

    def tearDown(self):
        self.tmp.cleanup()

    def test_upload(self):
        files = [{"path": "ex00/main.c",
                  "b64": base64.b64encode(b"int main(void){return 0;}\n")
                  .decode()}]
        code, res = F.fake_post(self.base + "/api/upload",
                                {"team": "up1", "files": files})
        self.assertEqual((code, res["files"]), (200, 1))
        self.assertTrue(os.path.isfile(os.path.join(
            self.fake["repo"], "up1", "ex00", "main.c")))
        F.fake_wait_status(self.base, "up1", ("done",))
        self.assertIn("up1", self.fake["calls"])
        # an existing team is replaced only when asked; the old one is kept
        code, _ = F.fake_post(self.base + "/api/upload",
                              {"team": "up1", "files": files})
        self.assertEqual(code, 409)
        code, _ = F.fake_post(self.base + "/api/upload",
                              {"team": "up1", "files": files,
                               "replace": True})
        self.assertEqual(code, 200)
        trash = os.listdir(os.path.join(self.fake["repo"], ".trash"))
        self.assertEqual(len(trash), 1)
        self.assertNotIn(".trash", F.fake_state(self.base))

    def test_git_url(self):
        code, res = F.fake_post(self.base + "/api/add",
                                {"url": "https://example.invalid/team9.git"})
        self.assertEqual((code, res["team"]), (200, "team9"))
        F.fake_wait_status(self.base, "team9", ("done",))
        self.assertIn("team9", self.fake["calls"])
        code, _ = F.fake_post(self.base + "/api/add", {"url": "not a url"})
        self.assertEqual(code, 400)

    def test_changed_files_are_evaluated_again(self):
        F.fake_wait_status(self.base, "c01", ("done",))
        before = self.fake["calls"].count("c01")
        # an edit, dated in the past so the settle wait doesn't apply
        path = os.path.join(self.fake["repo"], "c01", "ex00", "main.c")
        with open(path, "a", encoding="utf-8") as fh:
            fh.write("\n")
        old = time.time() - 10
        os.utime(path, (old, old))
        F.fake_wait(lambda: self.fake["calls"].count("c01") > before, 20,
                    "c01 to be evaluated again")

    def test_folder_copied_in_by_hand(self):
        path = os.path.join(self.fake["repo"], "hand1", "ex00")
        os.makedirs(path)
        with open(os.path.join(path, "main.c"), "w") as fh:
            fh.write("int main(void){return 0;}\n")
        F.fake_wait_status(self.base, "hand1", ("done",), 20)


if __name__ == "__main__":
    unittest.main()
