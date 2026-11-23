"""B2: the turn-in is copied to work_dir_abs; the team folder is unchanged
afterwards (no files added, none changed)."""

import hashlib
import os
import tempfile
import unittest

from judge_fixtures import (EMPTY_ENTRY, PDF_ENTRY, PDF_TEXT, PDF_ARG,
                            answer_program, run_judge, write_team)


def snapshot(root):
    out = {}
    for dirpath, dirnames, filenames in os.walk(root):
        for name in dirnames + filenames:
            path = os.path.join(dirpath, name)
            data = b""
            if os.path.isfile(path):
                with open(path, "rb") as fh:
                    data = fh.read()
            out[os.path.relpath(path, root)] = (os.stat(path).st_mtime_ns,
                                                hashlib.sha256(data).hexdigest())
    return out


class TestB2Copy(unittest.TestCase):
    def test_team_folder_unchanged(self):
        with tempfile.TemporaryDirectory() as tmp:
            files = {"ex00/main.c": answer_program([(PDF_ARG, PDF_TEXT, "")]),
                     "ex00/rush01": "#!/bin/sh\necho prebuilt\n"}
            team = os.path.join(tmp, "team")
            write_team(tmp, files)
            before = snapshot(team)
            r = run_judge(tmp, {}, [PDF_ENTRY, EMPTY_ENTRY])
            after = snapshot(team)
            copied = os.path.isfile(os.path.join(tmp, "work", "team", "ex00", "main.c"))
        self.assertEqual(before, after)
        self.assertTrue(copied)
        self.assertTrue(r["built"])
        # the team's own `rush01` file is never what runs
        self.assertEqual(r["runs"][0]["stdout"], PDF_TEXT)


if __name__ == "__main__":
    unittest.main()
