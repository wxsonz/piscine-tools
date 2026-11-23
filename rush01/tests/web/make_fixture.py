#!/usr/bin/env python3
"""Rebuild tests/web/fixture_report*.json from the two small fixture teams.

The runs are real: fixture_team/ is built with cc and run on a small bank,
so every grid, `broken` clue and diagnosis vote in the fixture is what that
code really prints. detect's part is written by hand (read from the code).
Not a test; run it only when the fixture shape (tool/SHAPES.md) changes:
  python3 rush01/tests/web/make_fixture.py
"""

import itertools
import json
import os
import random
import shutil
import subprocess
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
TEAM = os.path.join(HERE, "fixture_team")
NOBUILD = os.path.join(HERE, "fixture_nobuild")
SUBJECT = {"name": "rush01", "turn_in_dir": "ex00", "binary": "rush01",
           "build": ["cc", "-Wall", "-Wextra", "-Werror", "-o", "rush01"],
           "sizes": [4], "bonus_sizes": [5, 6, 7, 8, 9],
           "allowed": ["write", "malloc", "free"],
           "error_text": "Error\n", "error_on_stderr": "note",
           "norm_flags": ["-R", "CheckForbiddenSourceHeader"],
           "sheet_binary": "rush-01"}
CRT = {"__libc_start_main", "__cxa_finalize", "__gmon_start__",
       "__stack_chk_fail", "_GLOBAL_OFFSET_TABLE_", "_ITM_deregisterTMCloneTable",
       "_ITM_registerTMCloneTable"}
MISREADINGS = [("transposed", "rows and columns swapped (transposed)"),
               ("top_bottom", "top and bottom clues swapped"),
               ("left_right", "left and right clues swapped")]


def main():
    with tempfile.TemporaryDirectory(prefix="rush01-fixture-") as tmp:
        # 1. the bank: a small one, in the shapes of SHAPES "puzzle entry"
        bank = make_bank()
        # 2. the main team: build, forbidden, norm, sanitizer, runs
        judge = sheet_part(judge_team(TEAM, bank, tmp))
        report = {"team": "c01", "team_dir_abs": "/fixture/repo/c01",
                  "made_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
                  "subject": SUBJECT, "judge": judge,
                  "detect": detect_main(), "cross_check": []}
        write(os.path.join(HERE, "fixture_report.json"), report)
        # 3. the team that does not build
        judge = sheet_part(judge_team(NOBUILD, bank, tmp))
        report = {"team": "d3", "team_dir_abs": "/fixture/repo/d3",
                  "made_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
                  "subject": SUBJECT, "judge": judge,
                  "detect": detect_nobuild(),
                  "cross_check": ["no runs: timing cross-check skipped"]}
        write(os.path.join(HERE, "fixture_report_nobuild.json"), report)


def sheet_part(judge):
    """The eval-sheet fields of SHAPES "judge result", by hand from what the
    fixture shows (judge/judge_sheet.py is judge's own; web only draws)."""
    stops = []
    if judge["norm"]["ran"] and not judge["norm"]["ok"]:
        stops.append({"key": "norm", "level": "stop",
                      "text": f"{len(judge['norm']['errors'])} norm error(s)",
                      "sheet": "Norm error: evaluation stops."})
    if not judge["built"]:
        stops.append({"key": "build", "level": "stop",
                      "text": "does not build: " + judge["build_log"].split("\n")[0],
                      "sheet": "Nothing to test: no binary."})
    names = sorted({x["name"] for x in judge["forbidden"]["names"]})
    if names:
        stops.append({"key": "forbidden", "level": "check",
                      "text": "calls " + ", ".join(names),
                      "sheet": "Subject: allowed functions are write, malloc, free."})
    judge["stops"] = stops
    judge["bonus"] = {"sizes": {"5": "fail"} if judge["built"] else {},
                      "largest_n": None, "counted": False,
                      "note": "not counted: the evaluation stops (norm)"
                      if judge["built"] else "no bonus runs"}
    judge["malloc_fail"] = {"ran": False, "mallocs": None, "tries": [],
                            "crashes": [],
                            "note": "the source never calls malloc: nothing to break"
                            if judge["built"] else "build failed: skipped"}
    return judge


def write(path, obj):
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(obj, fh, indent=1)
        fh.write("\n")


# ---------------------------------------------------------------- puzzles

def seen(line):
    count = 0
    top = 0
    for v in line:
        if v > top:
            top = v
            count += 1
    return count


def clues_of(grid):
    n = len(grid)
    cols = [[grid[r][c] for r in range(n)] for c in range(n)]
    return ([seen(col) for col in cols] + [seen(col[::-1]) for col in cols]
            + [seen(row) for row in grid] + [seen(row[::-1]) for row in grid])


def latin4():
    out = []
    for rows in itertools.product(itertools.permutations(range(1, 5)), repeat=4):
        if all(len({rows[r][c] for r in range(4)}) == 4 for c in range(4)):
            out.append([list(r) for r in rows])
    return out


def latin_random(n, rng):
    base = [[(r + c) % n + 1 for c in range(n)] for r in range(n)]
    rng.shuffle(base)
    cols = list(range(n))
    rng.shuffle(cols)
    return [[row[c] for c in cols] for row in base]


def make_bank():
    rng = random.Random(20)
    squares = latin4()
    by_clues = {}
    for g in squares:
        by_clues.setdefault(tuple(clues_of(g)), []).append(g)
    unique = [list(k) for k, v in by_clues.items() if len(v) == 1]
    multi = [list(k) for k, v in by_clues.items() if len(v) > 1]
    asym = [c for c in unique if c[0:4] != c[8:12]]
    slow = sorted(unique, key=lambda c: -sum(1 for v in c if v in (2, 3)))
    deep = find_deep(by_clues, rng)
    bank = []

    def add(group, clues, expect, argv=None, note="", timeout_ms=2000):
        k = sum(1 for e in bank if e["group"] == group) + 1
        if argv is None:
            argv = [" ".join(str(v) for v in clues)]
        bank.append({"id": f"{group}-{k:02d}", "group": group,
                     "n": len(clues) // 4 if clues else 4, "argv": argv,
                     "clues": clues, "expect": expect,
                     "timeout_ms": timeout_ms, "note": note})

    pdf = [4, 3, 2, 1, 1, 2, 2, 2, 4, 3, 2, 1, 1, 2, 2, 2]
    add("ok4", pdf, "grid", note="PDF example (symmetric)")
    for c in rng.sample(asym, 5):
        add("ok4", c, "grid", note="asymmetric")
    add("multi4", rng.choice(multi), "grid", note="2+ solutions")
    add("nosol4-easy", [1, 2, 2, 2, 1, 2, 2, 2, 4, 3, 2, 1, 1, 2, 2, 2],
        "error", note="col 1 seen as 1 from both ends")
    add("nosol4-deep", deep, "error", timeout_ms=5000, note="locally fine")
    add("slow4", slow[0], "grid", timeout_ms=5000, note="mostly 2s and 3s")
    pdf_txt = " ".join(str(v) for v in pdf)
    for argv, note in ([""], "empty"), (["4 3"], "2 numbers"), \
            ([pdf_txt + " "], "trailing space"), \
            ([pdf_txt.replace(" ", "  ", 1)], "double space"), \
            ([pdf_txt[:-1] + "5"], "value 5"), \
            (["a" + pdf_txt[1:]], "letter"), ([], "no argument"), \
            ([pdf_txt, pdf_txt], "two arguments"):
        add("fmt", None, "error", argv=argv, note=note)
    for n in (5, 9):
        add("bonusN", clues_of(latin_random(n, rng)), "grid",
            timeout_ms=10000, note=f"{n}x{n}")
    # a 9x9 this team finishes in time, so the 3D view has 81 blocks: the
    # first square its search order reaches, read back through its misreading
    first = latin_first(9)
    c = clues_of(first)
    add("bonusN", c[18:27] + c[27:36] + c[0:9] + c[9:18], "grid",
        timeout_ms=10000, note="9x9 (fast for row-major search)")
    add("bonusN", None, "error", argv=[" ".join(["2"] * 18)],
        timeout_ms=10000, note="18 numbers")
    add("small", [1, 1, 1, 1], "info", note="1x1")
    add("small", clues_of([[1, 2], [2, 1]]), "info", note="2x2")
    return bank


def latin_first(n):
    """The first Latin square a row-major 1..n backtracking search fills."""
    grid = [[0] * n for _ in range(n)]

    def fill(pos):
        if pos == n * n:
            return True
        r, c = divmod(pos, n)
        for v in range(1, n + 1):
            if v in grid[r] or any(grid[i][c] == v for i in range(r)):
                continue
            grid[r][c] = v
            if fill(pos + 1):
                return True
            grid[r][c] = 0
        return False

    assert fill(0)
    return grid


def find_deep(by_clues, rng):
    """Clues with every opposite pair fine (sum 3..5, no 1 1) and no grid."""
    while True:
        c = [rng.randint(1, 4) for _ in range(16)]
        pairs = [(c[i], c[4 + i]) for i in range(4)] + \
                [(c[8 + i], c[12 + i]) for i in range(4)]
        if all(3 <= a + b <= 5 and (a, b) != (1, 1) for a, b in pairs) \
                and tuple(c) not in by_clues:
            return c


# ---------------------------------------------------------------- judge

def judge_team(team, bank, tmp):
    # 1. build in a temp copy, like judge/ does
    work = os.path.join(tmp, os.path.basename(team))
    shutil.copytree(team, work)
    ex = os.path.join(work, "ex00")
    srcs = sorted(f for f in os.listdir(ex) if f.endswith(".c"))
    heads = sorted(f for f in os.listdir(ex) if f.endswith(".h"))
    b = subprocess.run(SUBJECT["build"] + srcs, cwd=ex, capture_output=True,
                       text=True)
    built = b.returncode == 0
    log = "" if built else first_error(b.stderr)
    files = {"sources": ["ex00/" + f for f in srcs],
             "headers": ["ex00/" + f for f in heads],
             "flagged": [], "no_ex_dir": False}
    tools = {"cc": True, "norminette": bool(shutil.which("norminette")),
             "valgrind": bool(shutil.which("valgrind")), "asan": True}
    res = {"ex_dir": "ex00", "built": built, "build_log": log,
           "files": files, "forbidden": forbidden(ex, built),
           "norm": norm(ex, srcs + heads), "sanitizer": None,
           "runs": [], "groups": {}, "timing": None, "diagnosis": None,
           "tools": tools}
    if not built:
        res["sanitizer"] = {"ran": False, "findings": [],
                            "note": "skipped: the turn-in does not build"}
        return res
    # 2. the bank, then the groups, the timing and the diagnosis
    binary = os.path.join(ex, "rush01")
    res["runs"] = [run_one(binary, e) for e in bank]
    for r in res["runs"]:
        g = res["groups"].setdefault(r["group"], {"pass": 0, "fail": 0,
                                                  "info": 0})
        g[r["verdict"]] += 1
    res["timing"] = timing(res["runs"])
    res["diagnosis"] = diagnose(bank, res["runs"])
    res["sanitizer"] = sanitizer(ex, srcs, bank)
    return res


def first_error(text):
    lines = text.splitlines()
    for i, line in enumerate(lines):
        if "error:" in line:
            return "\n".join(lines[max(0, i - 1):i + 4])
    return "\n".join(lines[:5])


def forbidden(ex, built):
    names = []
    notes = []
    allowed = set(SUBJECT["allowed"]) | CRT
    if built:
        out = subprocess.run(["nm", "-u", os.path.join(ex, "rush01")],
                             capture_output=True, text=True).stdout
        for line in out.splitlines():
            sym = line.split()[-1].split("@")[0]
            if sym not in allowed:
                names.append({"name": sym, "where": "binary",
                              "file": None, "line": None})
    for f in sorted(os.listdir(ex)):
        if not f.endswith(".c"):
            continue
        with open(os.path.join(ex, f), encoding="utf-8") as fh:
            for no, line in enumerate(fh, 1):
                for bad in ("printf", "atoi"):
                    if bad + "(" in line:
                        names.append({"name": bad, "where": "source",
                                      "file": "ex00/" + f, "line": no})
    return {"names": names, "notes": notes}


def norm(ex, files):
    if not shutil.which("norminette"):
        return {"ran": False, "ok": None, "errors": [],
                "note": "skipped: norminette not found"}
    p = subprocess.run(["norminette"] + SUBJECT["norm_flags"] + files,
                       cwd=ex, capture_output=True, text=True)
    errors = []
    cur = ""
    for line in p.stdout.splitlines():
        if line.endswith(": Error!"):
            cur = "ex00/" + line.split(":")[0]
        elif line.startswith("Error:") and cur:
            parts = line.split("(line:")
            no = int(parts[1].split(",")[0]) if len(parts) > 1 else None
            errors.append({"file": cur, "line": no,
                           "text": line[6:].split("(line:")[0].strip()})
    return {"ran": True, "ok": not errors, "errors": errors, "note": ""}


def run_one(binary, e):
    # 1. run with the timeout and a 1 MB cap
    t0 = time.monotonic()
    timed_out = False
    try:
        p = subprocess.run([binary] + e["argv"], capture_output=True,
                           timeout=e["timeout_ms"] / 1000)
        out = p.stdout[:1 << 20].decode(errors="replace")
        err = p.stderr[:1 << 20].decode(errors="replace")
        code = p.returncode
    except subprocess.TimeoutExpired as x:
        timed_out = True
        out = (x.stdout or b"")[:1 << 20].decode(errors="replace")
        err = (x.stderr or b"")[:1 << 20].decode(errors="replace")
        code = None
    ms = int((time.monotonic() - t0) * 1000)
    sig = None
    if code is not None and code < 0:
        sig = {-11: "SIGSEGV", -6: "SIGABRT", -9: "SIGKILL"}.get(code, "SIG?")
        code = None
    run = {"id": e["id"], "group": e["group"], "argv": e["argv"],
           "expect": e["expect"], "stdout": out, "stderr": err,
           "exit": code, "signal": sig, "timed_out": timed_out,
           "time_ms": ms, "verdict": "pass", "reasons": [], "notes": [],
           "grid": None, "broken": []}
    # 2. judge it
    n = e["n"]
    run["grid"] = parse_grid(out, n) if e["clues"] else None
    if timed_out:
        run["reasons"].append(f"timeout after {e['timeout_ms'] // 1000} s")
    elif sig:
        run["reasons"].append(f"crashed ({sig})")
    elif e["expect"] == "error":
        if out != "Error\n":
            run["reasons"].append("expected Error, got "
                                  + ("a grid" if out[:1].isdigit() else repr(out[:30])))
    elif out == "Error\n":
        run["reasons"].append("printed Error on a puzzle that has a solution")
    elif run["grid"] is None:
        run["reasons"].append("output is not a grid of %d rows" % n)
    else:
        run["broken"] = broken(run["grid"], e["clues"])
        if run["broken"]:
            run["reasons"].append(f"breaks {len(run['broken'])} of "
                                  f"{4 * n} clues")
    if e["expect"] == "info":
        run["verdict"] = "info"
        run["reasons"] = []
    elif run["reasons"]:
        run["verdict"] = "fail"
    return run


def parse_grid(out, n):
    rows = out.split("\n")
    if len(rows) != n + 1 or rows[-1] != "":
        return None
    grid = []
    for row in rows[:-1]:
        cells = row.split(" ")
        if len(cells) != n or not all(c.isdigit() for c in cells):
            return None
        grid.append([int(c) for c in cells])
    return grid


def broken(grid, clues):
    n = len(grid)
    got = clues_of(grid)
    sides = ["top", "bottom", "left", "right"]
    return [{"side": sides[i // n], "index": i % n, "want": clues[i],
             "seen": got[i]} for i in range(4 * n) if got[i] != clues[i]]


def timing(runs):
    ok = [r["time_ms"] for r in runs if r["group"] == "ok4"]
    slow = [r["time_ms"] for r in runs if r["group"] == "slow4"]
    worst = max(runs, key=lambda r: r["time_ms"])
    ratio = round(max(slow) / max(1, max(ok)), 1) if ok and slow else None
    return {"slowest_id": worst["id"], "slowest_ms": worst["time_ms"],
            "slow4_over_ok4": ratio}


def diagnose(bank, runs):
    """The two-way vote of PLAN.md §5, for three misreadings (4x4 exact)."""
    squares = latin4()
    cases = []
    for e, r in zip(bank, runs):
        if e["expect"] != "grid" or e["clues"] is None:
            continue
        if r["grid"] is not None and not r["timed_out"]:
            cases.append((e, "grid", r["grid"], not r["broken"]))
        elif r["stdout"] == "Error\n":
            cases.append((e, "error", None, False))
    failures = sum(1 for c in cases if not c[3])
    votes = []
    for mid, text in MISREADINGS:
        explains = 0
        contra = 0
        for e, outcome, grid, correct in cases:
            if correct:
                continue
            m = misread(mid, e["clues"])
            if outcome == "grid":
                fits = clues_of(grid) == m
            elif e["n"] == 4:
                fits = not any(clues_of(g) == m for g in squares)
            else:
                continue
            if fits:
                explains += 1
            else:
                contra += 1
        votes.append({"id": mid, "text": text, "explains": explains,
                      "failures": failures, "contradicted": contra})
    votes.sort(key=lambda v: -v["explains"])
    best = votes[0] if votes[0]["explains"] >= 2 and \
        votes[0]["contradicted"] == 0 else None
    return {"best": best, "all": votes, "extra": []}


def misread(mid, clues):
    n = len(clues) // 4
    top, bot = clues[0:n], clues[n:2 * n]
    left, right = clues[2 * n:3 * n], clues[3 * n:]
    if mid == "transposed":
        return left + right + top + bot
    if mid == "top_bottom":
        return bot + top + left + right
    return top + bot + right + left


def sanitizer(ex, srcs, bank):
    asan = os.path.join(ex, "rush01_asan")
    b = subprocess.run(["cc", "-g", "-fsanitize=address,undefined", "-o",
                        asan] + srcs, cwd=ex, capture_output=True, text=True)
    if b.returncode != 0:
        return {"ran": False, "findings": [], "note": "skipped: no ASan"}
    findings = []
    picks = [e for e in bank if e["id"] in ("ok4-01", "nosol4-easy-01",
                                             "fmt-01", "fmt-02")]
    for e in picks:
        p = subprocess.run([asan] + e["argv"], capture_output=True,
                           text=True, timeout=10)
        if "ERROR: AddressSanitizer" in p.stderr or "runtime error" in p.stderr:
            findings.append({"case": e["id"], "kind": "asan",
                             "text": p.stderr[:400]})
    return {"ran": True, "findings": findings, "note": ""}


# ---------------------------------------------------------------- detect
# Written by hand from reading fixture_team/ and fixture_nobuild/.

def detect_main():
    parse = {
        "id": "parse.scan", "name": "Scan and count", "tier": None,
        "confidence": "clear", "also": [],
        "where": [{"file": "ex00/main.c", "func": "parse_clues", "line": 3}],
        "evidence": [
            {"file": "ex00/main.c", "line": 12,
             "text": "if (str[i] >= '1' && str[i] <= '9')",
             "why": "a digit is stored, one pass over the string"},
            {"file": "ex00/main.c", "line": 19,
             "text": "else if (str[i] != ' ')",
             "why": "spaces are skipped, anything else is an error"},
            {"file": "ex00/main.c", "line": 24,
             "text": "return (count % 4 == 0 && *n >= 1);",
             "why": "N comes from the count of numbers"}],
        "facts": [{"key": "argc", "text": "checks argc != 2"},
                  {"key": "n", "text": "N from the count (bonus sizes)"},
                  {"key": "spaces", "text": "any number of spaces accepted"}],
        "explain": "Walks the argument once: a digit is stored and counted, "
                   "a space is skipped. The count decides if it is valid.",
        "questions": ["What does your program do with two spaces in a row?",
                      "Where do you check that a clue is not bigger than N?"]}
    data = {
        "id": "data.grid2d", "name": "2D array", "tier": None,
        "confidence": "likely", "also": [],
        "where": [{"file": "ex00/main.c", "func": "main", "line": 39}],
        "evidence": [
            {"file": "ex00/main.c", "line": 42, "text": "int grid[9][9];",
             "why": "a fixed 2D array, sized for the 9x9 bonus"},
            {"file": "ex00/solve.c", "line": 81,
             "text": "grid[pos / n][pos % n] = v;",
             "why": "indexed [row][col] through pos / n, pos % n"},
            {"file": "ex00/main.c", "line": 41, "text": "int clues[36];",
             "why": "the clues stay flat, in input order"}],
        "facts": [{"key": "clues", "text": "clues flat [36]: top 0..n-1, "
                                           "bottom n.., left 2n.., right 3n.."},
                  {"key": "globals", "text": "no globals: passed as arguments"}],
        "explain": "The board is an int[9][9]; only the top-left n x n part "
                   "is used.",
        "questions": ["Why is the grid 9 by 9 when the puzzle is 4 by 4?"]}
    solve = {
        "id": "solve.bt_clue_line",
        "name": "Backtracking + clue check when a line is full", "tier": 1,
        "confidence": "clear", "also": [],
        "where": [{"file": "ex00/solve.c", "func": "solve", "line": 70}],
        "evidence": [
            {"file": "ex00/solve.c", "line": 79,
             "text": "if (!fits(grid, n, pos, v))",
             "why": "row and column uniqueness before placing"},
            {"file": "ex00/solve.c", "line": 82,
             "text": "if ((pos % n != n - 1 || row_ok(grid, clues, n, pos / n))",
             "why": "row clues checked when the row is full"},
            {"file": "ex00/solve.c", "line": 83,
             "text": "&& (pos / n != n - 1 || col_ok(grid, clues, n, pos % n))",
             "why": "column clues checked when the column is full"},
            {"file": "ex00/solve.c", "line": 86,
             "text": "grid[pos / n][pos % n] = 0;",
             "why": "resets the cell after a failed try"}],
        "facts": [{"key": "line_check", "text": "row-end and col-end"},
                  {"key": "counter", "text": "count++ when a block is taller "
                                            "than max (max = 0)"},
                  {"key": "no_solution", "text": "prints Error when solve "
                                                "returns 0"}],
        "explain": "Fills the cells in order, tries 1..N, keeps a value only "
                   "if its row and column stay unique, and checks the clues "
                   "of a line as soon as that line is full.",
        "questions": ["When exactly do you check the clues of a row?",
                      "What does solve return when no value fits?",
                      "Which clue does row_ok compare row 0 with?"]}
    printing = {
        "id": "print.char", "name": "One write per char", "tier": None,
        "confidence": "clear", "also": [],
        "where": [{"file": "ex00/print.c", "func": "print_grid", "line": 8}],
        "evidence": [
            {"file": "ex00/print.c", "line": 5, "text": "write(1, &c, 1);",
             "why": "one byte per write"},
            {"file": "ex00/print.c", "line": 19,
             "text": "ft_putchar(grid[r][c] + '0');",
             "why": "a digit becomes a char with + '0'"}],
        "facts": [{"key": "error_fd", "text": "Error on fd 1"},
                  {"key": "spaces", "text": "no trailing space (c < n - 1)"}],
        "explain": "Writes each digit and each space with its own write call.",
        "questions": ["How many write calls print a 4x4 grid?"]}
    return {"parts": {"parse": parse, "data": data, "solve": solve,
                      "print": printing},
            "project": {"globals": [], "structs": [], "functions": 10,
                        "longest": {"name": "parse_clues",
                                    "file": "ex00/main.c", "lines": 22},
                        "never_freed": False, "bonus": True,
                        "authors": None, "commits": None,
                        "ask": [{"kind": "complex", "file": "ex00/solve.c",
                                 "line": 82,
                                 "text": "if ((pos % n != n - 1 || row_ok(grid, clues, n, pos / n))",
                                 "why": "13 operators, 3 lines: ask what this does"},
                                {"kind": "recursion", "file": "ex00/solve.c",
                                 "line": 70,
                                 "text": "int\tsolve(int grid[9][9], int *clues, int n, int pos)",
                                 "why": "recursive: solve() calls itself. Returns: `return (1)` (line 75); `return (1)` (line 85); `return (0)` (line 88). Ask what it returns when the grid is full, and when the grid is impossible"}]},
            "error": None}


def detect_nobuild():
    unrec = {
        "id": None, "name": "unrecognized", "tier": None,
        "confidence": "unrecognized", "also": [],
        "where": [{"file": "ex00/main.c", "func": "show", "line": 59}],
        "evidence": [],
        "facts": [{"key": "printf", "text": "prints with printf "
                                            "(forbidden)"}],
        "explain": "", "questions": []}
    parse = {
        "id": "parse.atoi", "name": "atoi per token", "tier": None,
        "confidence": "likely", "also": [],
        "where": [{"file": "ex00/main.c", "func": "read_clues", "line": 3}],
        "evidence": [
            {"file": "ex00/main.c", "line": 12,
             "text": "b->clue[k] = atoi(str + i);",
             "why": "each token goes through atoi"},
            {"file": "ex00/main.c", "line": 13,
             "text": "if (b->clue[k] < 1 || b->clue[k] > 4)",
             "why": "range check after the conversion"}],
        "facts": [{"key": "accepts", "text": "accepts 04 and +1 (atoi)"}],
        "explain": "Converts each token with atoi, then checks the range.",
        "questions": ["What does atoi give for \"04\"?"]}
    data = {
        "id": "data.struct", "name": "Struct board", "tier": None,
        "confidence": "clear", "also": [],
        "where": [{"file": "ex00/rush.h", "func": None, "line": 7}],
        "evidence": [
            {"file": "ex00/rush.h", "line": 7, "text": "typedef struct s_board",
             "why": "a struct type in the header"},
            {"file": "ex00/rush.h", "line": 10, "text": "int cell[4][4];",
             "why": "the grid lives in the struct"},
            {"file": "ex00/rush.h", "line": 11, "text": "int clue[16];",
             "why": "the clues live in the struct"}],
        "facts": [{"key": "clues", "text": "clues flat [16] in the struct"}],
        "explain": "One struct holds n, the grid and the clues.",
        "questions": ["Why a struct instead of separate arrays?"]}
    solve = {
        "id": "solve.prefill", "name": "Pre-fill rules, then search",
        "tier": 2, "confidence": "mix", "also": ["solve.bt_end"],
        "where": [{"file": "ex00/main.c", "func": "prefill", "line": 24},
                  {"file": "ex00/main.c", "func": "search", "line": 40}],
        "evidence": [
            {"file": "ex00/main.c", "line": 31,
             "text": "if (b->clue[i] == 4)",
             "why": "clue 4 fixes the edge before the search"},
            {"file": "ex00/main.c", "line": 46,
             "text": "if (b->cell[pos / 4][pos % 4])",
             "why": "the search skips pre-filled cells"},
            {"file": "ex00/main.c", "line": 51,
             "text": "b->cell[pos / 4][pos % 4] = v;",
             "why": "places without any check: checks only at the end"}],
        "facts": [{"key": "clue_check", "text": "no clue check found"}],
        "explain": "Fixes some cells from the clues first, then searches the "
                   "rest.",
        "questions": ["Which cells does a clue of 4 fix?",
                      "Where do you check the clues during the search?"]}
    return {"parts": {"parse": parse, "data": data, "solve": solve,
                      "print": unrec},
            "project": {"globals": [],
                        "structs": [{"file": "ex00/rush.h", "line": 7,
                                     "name": "t_board"}],
                        "functions": 5,
                        "longest": {"name": "search", "file": "ex00/main.c",
                                    "lines": 17},
                        "never_freed": False, "bonus": False,
                        "authors": {"alice": 70, "bob": 30}, "commits": 4,
                        "ask": []},
            "error": None}


if __name__ == "__main__":
    main()
