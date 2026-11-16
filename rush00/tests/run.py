#!/usr/bin/env python3
"""Run the rush00 tool over the teams in rush00/repo and check the tool itself.

    python3 rush00/tests/run.py              # evaluator + tracer + browser
    python3 rush00/tests/run.py --no-browser
    python3 rush00/tests/run.py math-03      # only teams whose name contains this

Teams with a tests/expect/<team>.txt (the generated corpus) get every check;
any other team (a real one) gets only the tracer and browser checks.
For each team:
  1. evaluator: a team marked correct=yes must pass its rush; correct=no must be
     caught (a failing core case, or an edge case that prints something)
  2. tracer: for several sizes, the gdb trace must print exactly what the real
     binary prints (catches tracer bugs on recursion, buffers, pointers, ...)
  3. browser (needs node + playwright-core + chromium): the visualizer page for
     the team loads without JS errors and its map has one cell per printed char
"""

import importlib.machinery
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading
from concurrent.futures import ThreadPoolExecutor

HERE = os.path.dirname(os.path.realpath(__file__))
BASE = os.path.dirname(HERE)
TEAMS = os.path.join(BASE, "repo")
EXPECT = os.path.join(HERE, "expect")
REPORTS = tempfile.mkdtemp(prefix="rush00-tests-")
os.environ["RUSH00_SUBJECT"] = os.path.join(HERE, "subject.txt")
os.environ["RUSH00_REPORTS"] = REPORTS
os.environ["RUSH00_REPO"] = TEAMS

sys.dont_write_bytecode = True
_loader = importlib.machinery.SourceFileLoader("rush00", os.path.join(BASE, "tool", "rush00"))
_spec = importlib.util.spec_from_loader("rush00", _loader)
R = importlib.util.module_from_spec(_spec)
sys.modules["rush00"] = R
_loader.exec_module(R)
sys.path.insert(0, os.path.join(BASE, "tool"))
import ctrace  # noqa: E402  (rush/common, on sys.path via rush00)

TRACE_SIZES = [(5, 3), (1, 1), (1, 5), (6, 5), (0, 3)]
TTY = sys.stdout.isatty()


def col(code, s):
    return f"\033[{code}m{s}\033[0m" if TTY else s


def read_expect(name):
    d = {"rush": None, "correct": "yes", "entry": None, "algorithm": "", "bug": "",
         "known": os.path.exists(os.path.join(EXPECT, name + ".txt"))}
    try:
        for ln in open(os.path.join(EXPECT, name + ".txt"), encoding="utf-8"):
            if "=" in ln:
                k, v = ln.split("=", 1)
                v = v.split("  (")[0].strip()
                d[k.strip()] = v
    except OSError:
        pass
    if d["rush"] is not None:
        m = re.search(r"\d+", str(d["rush"]))
        d["rush"] = int(m.group()) if m else None
    return d


def real_output(ex, srcs, entry, x, y, work):
    """Build like the tracer does (but without gdb) and run once."""
    objs = []
    for s in srcs:
        o = os.path.join(work, s + ".r.o")
        extra = ["-Dmain=__rush_student_main"] if s == "main.c" else []
        r = subprocess.run(["cc", "-c", "-w", "-O0", "-ffunction-sections"] + extra
                           + [os.path.join(ex, s), "-o", o], capture_output=True)
        if r.returncode == 0:
            objs.append(o)
    h = os.path.join(work, "h.c")
    with open(h, "w") as f:
        f.write(f"#include <stdlib.h>\nvoid {entry}(int x, int y);\n"
                f"int main(int c, char **v) {{ (void)c; {entry}(atoi(v[1]), atoi(v[2])); return 0; }}\n")
    exe = os.path.join(work, "real")
    r = subprocess.run(["cc", "-w", "-Wl,--gc-sections", h] + objs + ["-o", exe], capture_output=True)
    if r.returncode != 0:
        objs = [o for o in objs if not o.endswith("main.c.r.o")]
        r = subprocess.run(["cc", "-w", "-Wl,--gc-sections", h] + objs + ["-o", exe], capture_output=True)
    if r.returncode != 0:
        return None
    try:
        return subprocess.run([exe, str(x), str(y)], capture_output=True, timeout=5).stdout.decode("latin-1")
    except subprocess.TimeoutExpired:
        return "<timeout>"


def check_team(name):
    exp = read_expect(name)
    path = os.path.join(TEAMS, name)
    res = {"team": name, "expect": exp, "problems": [], "notes": []}
    S = R.Subject.load()
    meta_rush = exp["rush"]
    # 1. evaluator
    team = R.Team(path, S, rush=meta_rush).evaluate()
    res["verdict"] = team.verdict()
    n = team.assigned if team.assigned is not None else min(team.rush_results, default=None)
    if exp["rush"] is None:
        exp["rush"] = n
    RR = team.rush_results.get(n) if n is not None else None
    if not RR:
        res["problems"].append(f"evaluator: no result for rush{meta_rush}")
    else:
        core = [t for t in RR["tests"] if t["cat"] in ("subject", "core") and t["ok"] is not None]
        failed = [t for t in core if not t["ok"]]
        noisy_edge = [t for t in RR["tests"] if t["cat"] == "edge" and (t["got"] or t["crash"])]
        res["core"] = f"{len(core) - len(failed)}/{len(core)}"
        if exp["entry"] and RR["entry"] != exp["entry"]:
            res["problems"].append(f"evaluator: entry {RR['entry']!r}, expected {exp['entry']!r}")
        if not exp["known"]:
            res["notes"].append("no expect file: tracer/browser checks only")
        elif exp["correct"] == "yes":
            if failed:
                res["problems"].append("evaluator: correct team fails " + ", ".join(
                    f"rush({t['x']},{t['y']}) {t['why']}" for t in failed[:3]))
            if noisy_edge:
                res["notes"].append("edge output: " + ", ".join(f"({t['x']},{t['y']})" for t in noisy_edge[:3]))
        else:
            if not failed and not noisy_edge:
                res["problems"].append("evaluator: buggy team NOT caught (" + exp.get("bug", "") + ")")
            else:
                res["notes"].append("caught: " + (failed[0]["why"] if failed else
                                                   f"edge rush({noisy_edge[0]['x']},{noisy_edge[0]['y']}) prints"))
    # 2. tracer vs real binary
    if RR and RR["entry"]:
        ex = team.ex
        files = sorted(os.listdir(ex))
        rf = RR["file"]
        helpers = [f for f in files if f.endswith(".c") and not R.RUSH_FILE.match(f)
                   and f not in ("main.c", "ft_putchar.c")]
        srcs = [f for f in ("ft_putchar.c",) if f in files] + [rf] + helpers
        work = tempfile.mkdtemp(prefix="rt-")
        try:
            for x, y in TRACE_SIZES:
                tr = ctrace.trace(ex, srcs, RR["entry"], [x, y])
                if tr.get("error"):
                    res["problems"].append(f"trace({x},{y}): {tr['error'][:160]}")
                    break
                real = real_output(ex, srcs + (["main.c"] if "main.c" in files else []), RR["entry"], x, y, work)
                if real is not None and tr["output"] != real:
                    res["problems"].append(f"trace({x},{y}) prints {tr['output'][:40]!r}, real binary {real[:40]!r}")
                if tr.get("truncated"):
                    res["problems"].append(f"trace({x},{y}) truncated after {len(tr['steps'])} steps")
                if x == 5 and y == 3:
                    res["steps"] = len(tr["steps"])
        finally:
            shutil.rmtree(work, ignore_errors=True)
    # write the report so the browser check has a summary to show
    with open(os.path.join(REPORTS, name + ".json"), "w") as f:
        json.dump(team.summary(), f)
    team.cleanup()
    return res


def browser_check(names, port=4299):
    pw = os.environ.get("PLAYWRIGHT_CORE", os.path.expanduser("~/42me/ft_blueprint/node_modules/playwright-core"))
    chrome = shutil.which("chromium") or shutil.which("google-chrome") or shutil.which("chromium-browser")
    if not (shutil.which("node") and os.path.isdir(pw) and chrome):
        print(col("33", "browser check skipped (needs node, playwright-core, chromium)"))
        return None
    import web  # rush00/tool/web.py
    app = web.App(R, port)
    srv = web.ThreadingHTTPServer(("127.0.0.1", port), web.make_handler(app))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    script = os.path.join(HERE, "browser_check.cjs")
    try:
        p = subprocess.run(["node", script, pw, chrome, f"http://localhost:{port}", json.dumps(names)],
                           capture_output=True, text=True, timeout=60 + 40 * len(names))
    finally:
        srv.shutdown()
    try:
        return json.loads(p.stdout.strip().split("\n")[-1])
    except (ValueError, IndexError):
        print(col("31", "browser check crashed:\n" + p.stdout[-1500:] + p.stderr[-1500:]))
        return None


def main(argv):
    filt = [a for a in argv if not a.startswith("-")]
    names = sorted(d for d in os.listdir(TEAMS) if os.path.isdir(os.path.join(TEAMS, d))
                   and (not filt or any(f in d for f in filt)))
    if not names:
        print("no teams in", TEAMS)
        return 1
    print(f"{len(names)} team(s) · reports in {REPORTS}")
    with ThreadPoolExecutor(max_workers=min(8, os.cpu_count() or 4)) as pool:
        results = list(pool.map(check_team, names))
    by = {r["team"]: r for r in results}
    if "--no-browser" not in argv:
        br = browser_check(names)
        if br:
            for name, b in br.items():
                r = by.get(name)
                if not r:
                    continue
                r["lead"] = b.get("lead", "")
                r["flags"] = b.get("flags", 0)
                for e in b.get("errors", []):
                    r["problems"].append("browser: " + e[:200])
    bad = 0
    for r in results:
        e = r["expect"]
        ok = not r["problems"]
        bad += not ok
        v = r.get("verdict", ("", "?"))[1]
        mark = col("32", "✓") if ok else col("31", "✗")
        kind = "?  " if not e["known"] else "ok " if e["correct"] == "yes" else "BUG"
        print(f"{mark} {r['team']:38} rush0{e['rush']} {kind} "
              f"core {r.get('core', '-'):>5}  {v:28} steps {r.get('steps', '-')}")
        if r.get("lead"):
            print(col("2", f"      idea: {r["lead"][:300]}" + (f"  · ⚑ {r['flags']} special path(s)" if r.get("flags") else "")))
        for nt in r["notes"]:
            print(col("2", "      " + nt[:150]))
        for pb in r["problems"]:
            print(col("31", "      ! " + pb))
    print(f"\n{len(results) - bad}/{len(results)} teams behave as expected")
    shutil.rmtree(REPORTS, ignore_errors=True)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
