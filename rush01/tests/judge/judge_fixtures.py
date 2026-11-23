"""Shared bits of the judge/ tests: paths, a hand-made bank, tiny C teams
written into temp dirs (PROOF-9), and a stand-in for puzzle/ while it is not
built (AGENTS.md: a stub in your tests is fine). Tests whose result depends
on puzzle/ itself skip without the real one.
"""

import os
import shutil
import subprocess
import sys
import tempfile
import types

HERE = os.path.dirname(os.path.abspath(__file__))
RUSH01 = os.path.dirname(os.path.dirname(HERE))
TOOL = os.path.join(RUSH01, "tool")
COMMON = os.path.join(os.path.dirname(RUSH01), "common")
for _path in (COMMON, TOOL):
    if _path not in sys.path:
        sys.path.insert(0, _path)

QUICK = bool(os.environ.get("RUSH01_QUICK"))
NO_PUZZLE = "puzzle/ not built yet (puzzle_check / puzzle_diagnose): skipped"


def _puzzle_is_real():
    try:
        from puzzle import puzzle_check, puzzle_diagnose  # noqa: F401
    except ImportError:
        return False
    return True


def _visible(line):
    seen, top = 0, 0
    for v in line:
        if v > top:
            seen, top = seen + 1, v
    return seen


def stub_check(n, clues, grid):
    """What puzzle_check promises (puzzle/CONTRACT.md), for the stand-in."""
    cols = [[grid[r][c] for r in range(n)] for c in range(n)]
    latin = all(sorted(line) == list(range(1, n + 1)) for line in grid + cols)
    lines = ([("top", i, cols[i]) for i in range(n)]
             + [("bottom", i, cols[i][::-1]) for i in range(n)]
             + [("left", i, grid[i]) for i in range(n)]
             + [("right", i, grid[i][::-1]) for i in range(n)])
    broken = []
    for k, (side, i, line) in enumerate(lines):
        if _visible(line) != clues[k]:
            broken.append({"side": side, "index": i, "want": clues[k],
                           "seen": _visible(line)})
    return {"latin": latin, "broken": broken}


HAS_PUZZLE = _puzzle_is_real()
if not HAS_PUZZLE:
    _stub = types.ModuleType("puzzle")
    _stub.puzzle_check = stub_check
    _stub.puzzle_diagnose = lambda cases: {"best": None, "all": [], "extra": []}
    sys.modules["puzzle"] = _stub

import judge  # noqa: E402

SUBJECT = {"name": "rush01", "turn_in_dir": "ex00", "binary": "rush01",
           "build": ["cc", "-Wall", "-Wextra", "-Werror", "-o", "rush01"],
           "sizes": [4], "bonus_sizes": [5, 6, 7, 8, 9],
           "allowed": ["write", "malloc", "free"],
           "error_text": "Error\n", "error_on_stderr": "note",
           "norm_flags": ["-R", "CheckForbiddenSourceHeader"]}

PDF_ARG = "4 3 2 1 1 2 2 2 4 3 2 1 1 2 2 2"
PDF_GRID = [[1, 2, 3, 4], [2, 3, 4, 1], [3, 4, 1, 2], [4, 1, 2, 3]]
PDF_TEXT = "1 2 3 4\n2 3 4 1\n3 4 1 2\n4 1 2 3\n"
NOSOL_ARG = "1 2 2 2 1 2 2 2 1 2 2 2 1 2 2 2"


def clues_of(grid):
    """The 4N clues of a full grid, SHAPES order (top bottom left right)."""
    n = len(grid)
    cols = [[grid[r][c] for r in range(n)] for c in range(n)]
    return ([_visible(c) for c in cols] + [_visible(c[::-1]) for c in cols]
            + [_visible(r) for r in grid] + [_visible(r[::-1]) for r in grid])


def entry(eid, argv, clues, expect, timeout_ms=2000, n=4):
    """A puzzle entry (SHAPES); argv is the list after the program name."""
    return {"id": eid, "group": eid.rsplit("-", 1)[0], "n": n, "argv": argv,
            "clues": clues, "expect": expect, "timeout_ms": timeout_ms, "note": ""}


PDF_ENTRY = entry("ok4-01", [PDF_ARG], clues_of(PDF_GRID), "grid")
NOSOL_ENTRY = entry("nosol4-easy-01", [NOSOL_ARG],
                    [int(x) for x in NOSOL_ARG.split()], "error")
EMPTY_ENTRY = entry("fmt-01", [""], None, "error")


def c_string(text):
    """text as a C string literal."""
    out = ""
    for ch in text:
        if ch == "\n":
            out += "\\n"
        elif ch in "\\\"":
            out += "\\" + ch
        elif " " <= ch <= "~":
            out += ch
        else:
            out += "\\%03o" % ord(ch)
    return '"' + out + '"'


def answer_program(answers, default_out="Error\n", default_err=""):
    """main.c that prints a fixed answer per argv[1] (write only).
    answers: [(argv1, stdout, stderr)]."""
    rows = []
    for arg, out, err in answers:
        rows.append(f"\tif (argc == 2 && same(argv[1], {c_string(arg)}))\n"
                    f"\t\treturn (say({c_string(out)}, {c_string(err)}));")
    return ("#include <unistd.h>\n\n"
            "static int\tlen(const char *s)\n{\n\tint i = 0;\n\n"
            "\twhile (s[i])\n\t\ti++;\n\treturn (i);\n}\n\n"
            "static int\tsame(const char *a, const char *b)\n{\n"
            "\twhile (*a && *a == *b)\n\t{\n\t\ta++;\n\t\tb++;\n\t}\n"
            "\treturn (*a == *b);\n}\n\n"
            "static int\tsay(const char *out, const char *err)\n{\n"
            "\twrite(1, out, len(out));\n\twrite(2, err, len(err));\n"
            "\treturn (0);\n}\n\n"
            "int\tmain(int argc, char **argv)\n{\n"
            + "\n".join(rows) + "\n"
            + f"\treturn (say({c_string(default_out)}, {c_string(default_err)}));\n}}\n")


def write_team(root, files):
    """files: {relative path: text}; -> the team dir (root/team)."""
    team = os.path.join(root, "team")
    for rel, text in files.items():
        path = os.path.join(team, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(text)
    os.makedirs(team, exist_ok=True)
    return team


def run_judge(root, files, bank, subject=SUBJECT):
    """Write the team under root, judge it with a work dir under root."""
    team = write_team(root, files)
    work = os.path.join(root, "work")
    os.makedirs(work, exist_ok=True)
    return judge.judge_team(team, subject, bank, work)


def has_asan():
    return judge.judge_tools()["asan"]


def nm_undefined(source_text):
    """What `nm -u` shows for a program built like the official build
    (PROOF-8: the test checks the toolchain fact it relies on)."""
    with tempfile.TemporaryDirectory(prefix="rush01-nm-") as tmp:
        with open(os.path.join(tmp, "p.c"), "w", encoding="utf-8") as fh:
            fh.write(source_text)
        subprocess.run(SUBJECT["build"] + ["p.c"], cwd=tmp, check=True,
                       capture_output=True)
        out = subprocess.run(["nm", "-u", os.path.join(tmp, "rush01")],
                             capture_output=True, text=True).stdout
    return [line.split()[-1].split("@")[0] for line in out.splitlines() if line.split()]


def path_without(tmp, hidden):
    """A PATH whose dirs hold links to everything on the real PATH except the
    names in `hidden` (so cc, as, ld still work)."""
    bin_dir = os.path.join(tmp, "bin")
    os.makedirs(bin_dir)
    for d in os.environ.get("PATH", "").split(os.pathsep):
        if not os.path.isdir(d):
            continue
        for name in os.listdir(d):
            src = os.path.join(d, name)
            dst = os.path.join(bin_dir, name)
            if name in hidden or os.path.lexists(dst) or not os.access(src, os.X_OK):
                continue
            os.symlink(src, dst)
    return bin_dir


def tool_present(name):
    return shutil.which(name) is not None
