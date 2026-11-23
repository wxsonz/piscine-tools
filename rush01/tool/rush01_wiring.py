"""rush01 wiring + CLI: reads subject.txt, calls the folders in order, writes
reports, prints. The only file that knows every folder (SHAPE-4); no rules
live here. Shapes: tool/SHAPES.md. Commands: PLAN.md §4.
"""

import datetime
import json
import os
import re
import subprocess
import sys
import tempfile

TOOL = os.path.dirname(os.path.abspath(__file__))
RUSH01 = os.path.dirname(TOOL)
REPO_DIR = os.path.join(RUSH01, "repo")
REPORT_DIR = os.path.join(RUSH01, "reports")
BANK_DIR = os.path.join(TOOL, "puzzle", "bank")
SUBJECT_TXT = os.path.join(TOOL, "subject.txt")
sys.path[:0] = [TOOL, os.path.join(os.path.dirname(RUSH01), "common")]

USAGE = """usage:
  rush01 serve [--port 4243] [--open]   dashboard on localhost
  rush01 <team dir | git URL>           evaluate one team, write its report
  rush01                                evaluate every team in repo/
  rush01 explain <team>                 the four verdicts + evidence
  rush01 puzzles                        regenerate the puzzle bank
  rush01 solve "4 3 2 1 ..."            reference answer(s)"""


# ---------------------------------------------------------------- subject

def read_subject(path):
    """subject.txt -> the subject shape (SHAPES)."""
    # 1. key = value lines
    raw = {}
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.split("#", 1)[0].strip()
            if "=" in line:
                key, value = line.split("=", 1)
                raw[key.strip()] = value.strip()
    # 2. typed fields
    return {
        "name": raw.get("name", "rush01"),
        "turn_in_dir": raw.get("turn_in_dir", "ex00"),
        "binary": raw.get("binary", "rush01"),
        "build": raw.get("build", "cc -Wall -Wextra -Werror -o rush01").split(),
        "sizes": [int(x) for x in raw.get("sizes", "4").split()],
        "bonus_sizes": [int(x) for x in raw.get("bonus_sizes", "").split()],
        "allowed": raw.get("allowed", "write malloc free").split(),
        "error_text": raw.get("error_text", "Error\\n").replace("\\n", "\n"),
        "error_on_stderr": raw.get("error_on_stderr", "note"),
        "norm_flags": raw.get("norm_flags", "").split(),
        "sheet_binary": raw.get("sheet_binary", raw.get("binary", "rush01")),
    }


# ---------------------------------------------------------------- one team

def cross_check(judge, detect):
    """Timing vs the solving tier (PLAN.md §7.2 step 6): questions, not verdicts."""
    notes = []
    solve = detect["parts"]["solve"]
    ratio = (judge.get("timing") or {}).get("slow4_over_ok4")
    tier = solve.get("tier")
    if ratio is None or tier is None:
        return notes
    if tier >= 2 and ratio > 50:
        notes.append(f"solving reads as tier {tier}, but slow4 is {ratio:.0f}x ok4: check")
    if tier == 0 and solve["id"] != "solve.hardcode" and ratio < 2:
        notes.append(f"solving reads as brute force, but slow4 is only {ratio:.1f}x ok4: check")
    return notes


def evaluate(team_dir_abs, subject=None, bank=None):
    """Judge + detect one team -> report (SHAPES); writes reports/<team>.json."""
    from puzzle import puzzle_load_bank
    from judge import judge_team
    from detect import detect_team

    subject = subject or read_subject(SUBJECT_TXT)
    bank = bank if bank is not None else puzzle_load_bank(BANK_DIR)
    team = os.path.basename(os.path.normpath(team_dir_abs))
    # 1. build and run in a temp dir
    with tempfile.TemporaryDirectory(prefix="rush01-") as work:
        judge = judge_team(team_dir_abs, subject, bank, work)
    # 2. read the code
    detect = detect_team(team_dir_abs, judge["ex_dir"])
    # 3. the report
    report = {
        "team": team,
        "team_dir_abs": os.path.abspath(team_dir_abs),
        "made_at": datetime.datetime.now().isoformat(timespec="seconds"),
        "subject": subject,
        "judge": judge,
        "detect": detect,
        "cross_check": cross_check(judge, detect),
    }
    os.makedirs(REPORT_DIR, exist_ok=True)
    with open(os.path.join(REPORT_DIR, team + ".json"), "w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=1)
    return report


def is_url(s):
    return bool(re.match(r"^(https?://|git@|ssh://|[\w.-]+@[\w.-]+:)", s))


def clone(url, name=None):
    """git URL -> repo/<name> (pull when it exists); None on failure."""
    name = name or re.sub(r"\.git$", "", url.rstrip("/").split("/")[-1].split(":")[-1])
    dest = os.path.join(REPO_DIR, name)
    os.makedirs(REPO_DIR, exist_ok=True)
    if os.path.exists(dest):
        cmd = ["git", "-C", dest, "pull", "--ff-only", "-q"]
    else:
        cmd = ["git", "clone", "-q", url, dest]
    if subprocess.run(cmd).returncode != 0:
        return None
    return dest


# ---------------------------------------------------------------- printing

GROUP_LABELS = {"evalsheet": "eliminatory"}


def print_report(r):
    j, d = r["judge"], r["detect"]
    print(f"\n== {r['team']}")
    # 0. the eval sheet's stops come first
    for s in j.get("stops", []):
        head = "STOP " if s["level"] == "stop" else "check"
        print(f"  {head}  {s['text']}\n          sheet: {s['sheet']}")
    # 1. build and checks
    if not j["built"]:
        print("  build   FAILED:", (j["build_log"].strip().splitlines() or ["?"])[0])
    else:
        print("  build   ok")
    names = sorted({x["name"] for x in j["forbidden"]["names"]})
    print("  forbid ", " ".join(names) if names else "none",
          *(f"\n          note: {n}" for n in j["forbidden"]["notes"]))
    nm = j["norm"]
    print("  norm   ", ("ok" if nm["ok"] else f"{len(nm['errors'])} error(s)")
          if nm["ran"] else "skipped: " + nm["note"],
          f"({nm['note']})" if nm["ran"] and nm["note"] else "")
    # 2. runs
    groups = sorted(j["groups"].items(), key=lambda gc: gc[0] != "evalsheet")
    for g, c in groups:
        print(f"  {GROUP_LABELS.get(g, g):12} pass {c.get('pass', 0):3}  fail {c.get('fail', 0):3}"
              + (f"  info {c['info']}" if c.get("info") else ""))
    b = j.get("bonus")
    if b and b["sizes"]:
        size = f"up to {b['largest_n']}x{b['largest_n']}" if b["largest_n"] else "none"
        print(f"  bonus        {size}" + (f"  ({b['note']})" if b["note"] else ""))
    m = j.get("malloc_fail") or {}
    if m.get("ran") and m.get("mallocs"):
        tried = len(m["tries"])
        print(f"  malloc fail  {len(m['crashes'])} of {tried} broke"
              + (f" (malloc #{', #'.join(map(str, m['crashes']))}): Crash (sheet)"
                 if m["crashes"] else ""))
    elif m.get("note"):
        print(f"  malloc fail  {m['note']}")
    best = (j.get("diagnosis") or {}).get("best")
    if best:
        print(f"  diagnosis: {best['explains']} of {best['failures']} failures fit: {best['text']}")
    for f in j["sanitizer"]["findings"]:
        print(f"  sanitizer: {f['case']}: {f['kind']}")
    # 3. the four parts
    for part in ("parse", "data", "solve", "print"):
        v = d["parts"][part]
        tier = f" (tier {v['tier']})" if v.get("tier") is not None else ""
        also = f" + {', '.join(v['also'])}" if v.get("also") else ""
        print(f"  {part:6} {v['name']}{tier}{also}  [{v['confidence']}]")
    for n in r["cross_check"]:
        print("  check: ", n)
    if d.get("error"):
        print("  detect error:", d["error"])
    sub = r["subject"]
    if sub.get("sheet_binary") and sub["sheet_binary"] != sub["binary"]:
        print(f"  note: the sheet runs ./{sub['sheet_binary']}; the subject "
              f"builds {sub['binary']} (used here)")


def print_explain(r):
    for part in ("parse", "data", "solve", "print"):
        v = r["detect"]["parts"][part]
        print(f"\n## {part}: {v['name']}  [{v['confidence']}]")
        if v.get("explain"):
            print("  " + v["explain"])
        for w in v["where"]:
            print(f"  where: {w['func']}() in {w['file']}:{w['line']}")
        for e in v["evidence"]:
            print(f"  {e['file']}:{e['line']}  {e['text']}\n      -> {e['why']}")
        for f in v["facts"]:
            print(f"  fact: {f['text']}")
        for q in v["questions"]:
            print(f"  ask: {q}")
    ask = r["detect"]["project"].get("ask") or []
    if ask:
        print("\n## lines to ask about (eval sheet: Explanation)")
    for a in ask:
        print(f"  {a['kind']:9} {a['file']}:{a['line']}  {a['text']}\n      -> {a['why']}")


# ---------------------------------------------------------------- commands

def team_dirs():
    if not os.path.isdir(REPO_DIR):
        return []
    return [os.path.join(REPO_DIR, d) for d in sorted(os.listdir(REPO_DIR))
            if not d.startswith(".") and os.path.isdir(os.path.join(REPO_DIR, d))]


def resolve_team(arg):
    if os.path.isdir(arg):
        return os.path.abspath(arg)
    if os.path.isdir(os.path.join(REPO_DIR, arg)):
        return os.path.join(REPO_DIR, arg)
    return None


def main(argv):
    # 1. commands that don't evaluate
    if argv[:1] in (["-h"], ["--help"], ["help"]):
        print(USAGE)
        return 0
    if argv[:1] == ["puzzles"]:
        from puzzle import puzzle_make_bank, puzzle_save_bank
        bank = puzzle_make_bank()
        puzzle_save_bank(BANK_DIR, bank)
        for g, entries in bank.items():
            print(f"  {g:12} {len(entries)}")
        return 0
    if argv[:1] == ["solve"] and len(argv) == 2:
        from puzzle import puzzle_solve
        nums = [int(x) for x in argv[1].split()]
        n = len(nums) // 4
        res = puzzle_solve(n, nums, limit=2)
        if not res["solutions"]:
            print("no solution (a correct program prints Error)")
        for i, g in enumerate(res["solutions"]):
            print(f"solution {i + 1}:" if len(res["solutions"]) > 1 else "solution:")
            print("\n".join(" ".join(map(str, row)) for row in g))
        print(f"({res['nodes']} nodes{', more than one solution' if len(res['solutions']) > 1 else ''})")
        return 0
    if argv[:1] == ["serve"]:
        from web import web_serve
        from detect import detect_catalog
        port = int(argv[argv.index("--port") + 1]) if "--port" in argv else 4243
        app = {"repo_dir_abs": REPO_DIR, "report_dir_abs": REPORT_DIR,
               "evaluate": evaluate, "clone": clone, "catalog": detect_catalog()}
        web_serve(app, port, "--open" in argv)
        return 0
    if argv[:1] == ["explain"] and len(argv) == 2:
        team = resolve_team(argv[1])
        if not team:
            print("no such team:", argv[1])
            return 1
        print_explain(evaluate(team))
        return 0
    # 2. evaluate teams
    if not argv:
        dirs = team_dirs()
    elif is_url(argv[0]):
        dirs = [clone(argv[0])]
        if dirs[0] is None:
            print("clone failed:", argv[0])
            return 1
    else:
        team = resolve_team(argv[0])
        if not team:
            print("no such team:", argv[0], "\n" + USAGE)
            return 1
        dirs = [team]
    subject = read_subject(SUBJECT_TXT)
    from puzzle import puzzle_load_bank
    bank = puzzle_load_bank(BANK_DIR)
    for d in dirs:
        print_report(evaluate(d, subject, bank))
    print(f"\nreports in {REPORT_DIR}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
