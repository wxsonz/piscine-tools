"""B10: a struct in a .h, a global array, `#define N 4` -> found in the
project block (and authorship is null outside a git repo)."""

import os
import shutil
import subprocess
import tempfile
import unittest

from c_team import HEADER, MAIN, TeamCase, team_files, team_write
from detect import detect_team

HEADER_STRUCT = HEADER.replace("#endif", """\
# define N 4

typedef struct s_view
{
    int    top[N];
    int    bottom[N];
}    t_view;

#endif""")

MAIN_GLOBAL = MAIN.replace("void    ft_error(void)",
                           "int    g_seen[4][4];\n\nvoid    ft_error(void)")


class TestB10ProjectBlock(TeamCase):

    def test_struct_global_define(self):
        project = self.detect(team_files(rush_h=HEADER_STRUCT,
                                         main=MAIN_GLOBAL))["project"]
        line = HEADER_STRUCT.split("\n").index("typedef struct s_view") + 1
        self.assertIn({"file": "ex00/rush.h", "line": line, "name": "t_view"},
                      project["structs"])
        self.assertTrue(any(g["file"] == "ex00/main.c"
                            and "g_seen[4][4]" in g["text"]
                            for g in project["globals"]), project["globals"])
        self.assertTrue(any(d["name"] == "N" and d["value"] == "4"
                            for d in project["defines"]), project["defines"])
        # the include guard is a define too, with no value
        self.assertTrue(any(d["name"] == "RUSH_H"
                            for d in project["defines"]))

    def test_sizes_and_authors(self):
        project = self.detect(team_files())["project"]
        # main ft_error ft_strlen ft_parse ft_is_free ft_count_row
        # ft_count_col ft_check_all ft_solve ft_putchar ft_print
        self.assertEqual(project["functions"], 11)
        self.assertEqual(project["longest"], {"name": "main", "file": "ex00/main.c",
                                              "lines": 22})
        self.assertFalse(project["never_freed"])
        self.assertFalse(project["bonus"])
        self.assertIsNone(project["authors"])
        self.assertIsNone(project["commits"])


    @unittest.skipUnless(shutil.which("git"), "git not installed")
    def test_authors_from_git(self):
        with tempfile.TemporaryDirectory(prefix="rush01-detect-") as tmp:
            env = dict(os.environ, HOME=tmp, GIT_CONFIG_NOSYSTEM="1",
                       GIT_CONFIG_GLOBAL=os.devnull)

            def git(*args, who="ana"):
                person = {"GIT_AUTHOR_NAME": who, "GIT_COMMITTER_NAME": who,
                          "GIT_AUTHOR_EMAIL": who + "@x",
                          "GIT_COMMITTER_EMAIL": who + "@x"}
                subprocess.run(["git", "-C", tmp] + list(args), check=True,
                               capture_output=True, env=dict(env, **person))

            files = team_files()
            git("init", "-q")
            team_write(tmp, {k: v for k, v in files.items()
                             if k != "print.c"})
            git("add", ".")
            git("commit", "-q", "-m", "solver")
            team_write(tmp, {"print.c": files["print.c"]})
            git("add", ".")
            git("commit", "-q", "-m", "printer", who="ben")
            project = detect_team(tmp, "ex00")["project"]
        self.assertEqual(project["commits"], 2)
        self.assertEqual(set(project["authors"]), {"ana", "ben"})
        self.assertGreater(project["authors"]["ana"],
                           project["authors"]["ben"])


if __name__ == "__main__":
    unittest.main()
