#!/usr/bin/env python3
"""Corpus generator and self-check for rush01 (tests/corpus/CONTRACT.md).

  gen.py [--out DIR] [TEAM ...]   copy teams into DIR (default rush01/repo/),
                                  each as its own git repo with 2 authors
  gen.py --check [TEAM ...]       build every team in a temp dir and compare
                                  it with expect/<team>.txt (group.*, built,
                                  ex_dir, norm); exit 1 on any mismatch
"""
import argparse
import glob
import itertools
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
RUSH01 = os.path.dirname(os.path.dirname(HERE))
TEAMS_DIR = os.path.join(HERE, "teams")
EXPECT_DIR = os.path.join(HERE, "expect")
BANK_DIR = os.path.join(RUSH01, "tool", "puzzle", "bank")
PDF_ARGV = "4 3 2 1 1 2 2 2 4 3 2 1 1 2 2 2"
PDF_GRID = [[1, 2, 3, 4], [2, 3, 4, 1], [3, 4, 1, 2], [4, 1, 2, 3]]

# (name, email) pairs: one pair per team, picked by the team's position.
AUTHORS = [
    (("Lea Dubois", "ldubois@student.42.fr"), ("Tom Bernard", "tbernard@student.42.fr")),
    (("Yanis Moreau", "ymoreau@student.42.fr"), ("Chloe Petit", "cpetit@student.42.fr")),
    (("Hugo Laurent", "hlaurent@student.42.fr"), ("Ines Roux", "iroux@student.42.fr")),
    (("Maxime Girard", "mgirard@student.42.fr"), ("Sarah Fontaine", "sfontaine@student.42.fr")),
]
DATES = ["2026-11-16T10:12:00", "2026-11-16T15:40:00",
         "2026-11-17T09:05:00", "2026-11-17T18:22:00"]


# ---------------------------------------------------------------- helpers

def team_names():
    return sorted(d for d in os.listdir(TEAMS_DIR)
                  if os.path.isdir(os.path.join(TEAMS_DIR, d)))


def read_expect(team):
    path = os.path.join(EXPECT_DIR, team + ".txt")
    out = {}
    if not os.path.isfile(path):
        return out
    with open(path) as f:
        for line in f:
            line = line.split("#", 1)[0].strip()
            if "=" in line:
                key, val = line.split("=", 1)
                out[key.strip()] = val.strip()
    return out


def visible(line):
    best = 0
    seen = 0
    for h in line:
        if h > best:
            best = h
            seen += 1
    return seen


def clues_of(grid):
    n = len(grid)
    cols = [[grid[r][c] for r in range(n)] for c in range(n)]
    out = [visible(c) for c in cols]
    out += [visible(c[::-1]) for c in cols]
    out += [visible(r) for r in grid]
    out += [visible(r[::-1]) for r in grid]
    return out


def latin_squares4():
    perms = list(itertools.permutations([1, 2, 3, 4]))
    for rows in itertools.product(perms, repeat=4):
        if all(len({rows[r][c] for r in range(4)}) == 4 for c in range(4)):
            yield [list(r) for r in rows]


def builtin_bank():
    """Small stand-in for the puzzle bank (used when puzzle/ is not ready)."""
    by_clues = {}
    for g in latin_squares4():
        by_clues.setdefault(tuple(clues_of(g)), []).append(g)
    assert sum(len(v) for v in by_clues.values()) == 576
    ok = [(c, v[0]) for c, v in sorted(by_clues.items()) if len(v) == 1]
    asym = [c for c, g in ok if list(c[0:4]) != list(c[8:12])
            and list(c[4:8]) != list(c[12:16])
            and len(set(c[0:4]) | set(c[4:8]) | set(c[8:12])) > 2]
    bank = [entry("ok4-00", "ok4", [PDF_ARGV], "grid")]
    for i, c in enumerate(asym[::max(1, len(asym) // 6)][:6]):
        bank.append(entry("ok4-%02d" % (i + 1), "ok4", [" ".join(map(str, c))], "grid"))
    # impossible on one line: top and bottom of column 1 both see 1
    easy = [[1, 2, 2, 2, 1, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2],
            [2, 2, 2, 2, 2, 2, 2, 2, 1, 1, 2, 2, 2, 2, 2, 2],
            [4, 2, 2, 2, 3, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2]]
    for i, c in enumerate(easy):
        assert tuple(c) not in by_clues
        bank.append(entry("nosol4-easy-%02d" % i, "nosol4-easy", [" ".join(map(str, c))], "error"))
    base = PDF_ARGV
    fmt = [[""], ["1"], ["4 3"], [base[:-2]], [base + " 1"], ["0" + base[1:]],
           ["5" + base[1:]], ["/" + base[1:]], [":" + base[1:]],
           ["12" + base[1:]], ["04" + base[1:]], ["a" + base[1:]],
           [base.replace(" ", "  ", 1)], [" " + base], [base + " "],
           [base.replace(" ", "\t", 1)], [base.replace(" ", "\v", 1)],
           [base.replace(" ", "\n", 1)], [base + "\n"], ["-1" + base[1:]],
           ["+1" + base[1:]], [], [base, base]]
    for i, a in enumerate(fmt):
        bank.append(entry("fmt-%02d" % i, "fmt", a, "error"))
    return bank


def entry(eid, group, argv, expect):
    clues = None
    if expect == "grid" or group == "nosol4-easy":
        clues = [int(x) for x in argv[0].split()]
    return {"id": eid, "group": group, "n": 4, "argv": argv, "clues": clues,
            "expect": expect, "timeout_ms": 2000, "note": "built-in"}


def load_bank():
    sys.path.insert(0, os.path.join(RUSH01, "tool"))
    try:
        from puzzle import puzzle_load_bank, puzzle_check
        bank = puzzle_load_bank(BANK_DIR)
        if bank:
            return bank, puzzle_check, "bank"
    except Exception:
        pass
    return builtin_bank(), own_check, "built-in list"


def own_check(n, clues, grid):
    broken = []
    latin = all(sorted(r) == list(range(1, n + 1)) for r in grid)
    latin = latin and all(sorted(c) == list(range(1, n + 1)) for c in zip(*grid))
    if clues is not None and latin:
        for i, (a, b) in enumerate(zip(clues, clues_of(grid))):
            if a != b:
                broken.append({"side": i // n, "index": i % n, "want": a, "seen": b})
    return {"latin": latin, "broken": broken}


# ------------------------------------------------------------------ check

def find_norminette():
    return shutil.which("norminette") or (
        os.path.expanduser("~/.local/bin/norminette")
        if os.path.exists(os.path.expanduser("~/.local/bin/norminette")) else None)


def build(src_dir, tmp):
    work = os.path.join(tmp, "build")
    shutil.copytree(src_dir, work)
    srcs = sorted(os.path.basename(p) for p in glob.glob(os.path.join(work, "*.c")))
    cmd = ["cc", "-Wall", "-Wextra", "-Werror", "-o", "rush01"] + srcs
    try:
        r = subprocess.run(cmd, cwd=work, capture_output=True, text=True, timeout=60)
    except subprocess.TimeoutExpired:
        return None, "build timed out"
    if r.returncode != 0 or not srcs:
        return None, (r.stderr or "no .c files")[:300]
    return os.path.join(work, "rush01"), ""


def parse_grid(text):
    lines = text.split("\n")
    if lines[-1] != "":
        return None
    rows = []
    for ln in lines[:-1]:
        parts = ln.split(" ")
        if not all(len(p) == 1 and p.isdigit() for p in parts):
            return None
        rows.append([int(p) for p in parts])
    n = len(rows)
    if n == 0 or any(len(r) != n for r in rows):
        return None
    return rows


def judge_case(exe, case, checker):
    try:
        r = subprocess.run([exe] + case["argv"], capture_output=True,
                           timeout=case.get("timeout_ms", 2000) / 1000.0)
    except subprocess.TimeoutExpired:
        return False, "timeout"
    out = r.stdout[:1000000].decode("utf-8", "replace")
    err = r.stderr[:1000].decode("utf-8", "replace")
    if case["expect"] == "error":
        if out == "Error\n" or (out == "" and err == "Error\n"):
            return True, ""
        return False, "wanted Error, got %r" % out[:40]
    if case["expect"] == "info":
        return True, ""
    grid = parse_grid(out)
    if grid is None or len(grid) != case["n"]:
        return False, "no grid, got %r" % out[:40]
    res = checker(case["n"], case["clues"], grid)
    if not res["latin"] or res["broken"]:
        return False, "wrong grid"
    return True, ""


def run_groups(exe, bank, checker, wanted):
    got = {}
    why = {}
    for case in bank:
        g = case["group"]
        if g not in wanted:
            continue
        ok, reason = judge_case(exe, case, checker)
        if not ok:
            got[g] = "fail"
            why.setdefault(g, "%s: %s" % (case["id"], reason))
        else:
            got.setdefault(g, "pass")
    return got, why


def check_team(team, bank, checker, norm_path):
    exp = read_expect(team)
    problems = []
    tdir = os.path.join(TEAMS_DIR, team)
    has_ex = os.path.isdir(os.path.join(tdir, "ex00"))
    if "ex_dir" in exp and (exp["ex_dir"] == "yes") != has_ex:
        problems.append("ex_dir want %s" % exp["ex_dir"])
    src = os.path.join(tdir, "ex00") if has_ex else tdir
    with tempfile.TemporaryDirectory(prefix="rush01-corpus-") as tmp:
        exe, log = build(src, tmp)
        built = exe is not None
        if "built" in exp and (exp["built"] == "yes") != built:
            problems.append("built want %s: %s" % (exp["built"], log.replace("\n", " | ")))
        wanted = {k[6:]: v for k, v in exp.items() if k.startswith("group.")}
        if built and wanted:
            got, why = run_groups(exe, bank, checker, wanted)
            for g, want in wanted.items():
                have = got.get(g, "none")
                if have != want:
                    problems.append("group.%s want %s got %s (%s)" % (g, want, have, why.get(g, "")))
    if norm_path and exp.get("norm", "ok") in ("ok", "errors"):
        r = subprocess.run([norm_path, tdir], capture_output=True, text=True)
        errs = [l for l in r.stdout.splitlines()
                if l.startswith("Error:") and "INVALID_HEADER" not in l]
        have = "ok" if not errs else "errors"
        first = errs[:1]
        if have != exp.get("norm", "ok"):
            problems.append("norm want %s got %s %s" % (exp.get("norm", "ok"), have, first))
    return problems


def do_check(names):
    bank, checker, source = load_bank()
    norm_path = find_norminette()
    print("bank: %s (%d cases); norminette: %s" % (source, len(bank), norm_path or "absent, skipped"))
    bad = 0
    for team in names:
        if not os.path.isfile(os.path.join(EXPECT_DIR, team + ".txt")):
            print("%-4s skipped: no expect file yet" % team)
            continue
        problems = check_team(team, bank, checker, norm_path)
        if problems:
            bad += 1
            print("%-4s MISMATCH %s" % (team, "; ".join(problems)))
        else:
            print("%-4s ok" % team)
    return 1 if bad else 0


# --------------------------------------------------------------- make repos

def git(cwd, args, env=None):
    full = dict(os.environ)
    full.update(env or {})
    cmd = ["git", "-c", "commit.gpgsign=false", "-c", "core.hooksPath=/dev/null",
           "-c", "init.defaultBranch=main"] + args
    subprocess.run(cmd, cwd=cwd, env=full, check=True, capture_output=True)


def make_repo(team, index, out_dir):
    dest = os.path.join(out_dir, team)
    if os.path.exists(dest):
        shutil.rmtree(dest)
    shutil.copytree(os.path.join(TEAMS_DIR, team), dest)
    files = []
    for root, dirs, names in os.walk(dest):
        dirs[:] = sorted(d for d in dirs if d != ".git")
        for name in sorted(names):
            files.append(os.path.relpath(os.path.join(root, name), dest))
    files.sort()
    pair = AUTHORS[sum(map(ord, team)) % len(AUTHORS)]  # stable per name
    git(dest, ["init", "-q"])
    for step in range(4):
        chunk = [f for i, f in enumerate(files) if i % 4 == step]
        if not chunk:
            continue
        who = pair[step % 2]
        stamp = DATES[step] + "+0100"
        env = {"GIT_AUTHOR_NAME": who[0], "GIT_AUTHOR_EMAIL": who[1],
               "GIT_COMMITTER_NAME": who[0], "GIT_COMMITTER_EMAIL": who[1],
               "GIT_AUTHOR_DATE": stamp, "GIT_COMMITTER_DATE": stamp}
        git(dest, ["add", "--"] + chunk, env)
        git(dest, ["commit", "-q", "--no-verify", "-m", "work on " + chunk[0]], env)


def do_make(out_dir, names):
    os.makedirs(out_dir, exist_ok=True)
    for i, team in enumerate(team_names()):
        if names and team not in names:
            continue
        make_repo(team, i, out_dir)
        print("%s -> %s" % (team, os.path.join(out_dir, team)))
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", default=os.path.join(RUSH01, "repo"))
    ap.add_argument("--check", action="store_true")
    ap.add_argument("teams", nargs="*")
    a = ap.parse_args()
    if a.check:
        return do_check([t for t in team_names() if not a.teams or t in a.teams])
    return do_make(os.path.abspath(a.out), a.teams)


if __name__ == "__main__":
    sys.exit(main())
