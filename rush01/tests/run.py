#!/usr/bin/env python3
"""The one check command for rush01 (PROOF-1, AGENTS.md).

  python3 rush01/tests/run.py                 everything
  python3 rush01/tests/run.py puzzle judge    some folders (+ the structure check)
  --quick       skip slow tests (tests read RUSH01_QUICK=1)
  --no-browser  skip browser tests (tests read RUSH01_NO_BROWSER=1)

Folders: structure, puzzle, judge, detect, web, corpus.
"""

import importlib
import os
import re
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
RUSH01 = os.path.dirname(HERE)
TOOL = os.path.join(RUSH01, "tool")
COMMON = os.path.join(os.path.dirname(RUSH01), "common")
FOLDERS = ["puzzle", "judge", "detect", "web"]
CORE = ["puzzle", "judge", "detect"]
ALL = ["structure"] + FOLDERS + ["corpus"]

sys.path[:0] = [TOOL, COMMON]


def check_structure():
    """SHAPE-2 contracts, SHAPE-3 published-only imports, CODE-11 no print."""
    errors = []
    # 1. every folder has a contract
    for f in FOLDERS:
        if not os.path.isfile(os.path.join(TOOL, f, "CONTRACT.md")):
            errors.append(f"tool/{f}/CONTRACT.md missing")
    if not os.path.isfile(os.path.join(HERE, "corpus", "CONTRACT.md")):
        errors.append("tests/corpus/CONTRACT.md missing")
    # 2. no import of another folder's inner module
    inner = re.compile(r"^\s*(?:from|import)\s+(%s)\.(\w+)" % "|".join(FOLDERS), re.M)
    for root in (TOOL, HERE):
        for dirpath, _, files in os.walk(root):
            for name in files:
                if not name.endswith(".py") and name != "rush01":
                    continue
                path = os.path.join(dirpath, name)
                rel = os.path.relpath(path, RUSH01)
                owner = rel.split(os.sep)[1] if rel.count(os.sep) >= 2 else ""
                with open(path, encoding="utf-8", errors="replace") as fh:
                    src = fh.read()
                for m in inner.finditer(src):
                    if m.group(1) != owner:
                        errors.append(f"{rel}: imports {m.group(1)}.{m.group(2)} "
                                      f"(use `from {m.group(1)} import ...`)")
    # 3. the core never prints
    for f in CORE:
        folder = os.path.join(TOOL, f)
        for dirpath, _, files in os.walk(folder):
            for name in files:
                if not name.endswith(".py"):
                    continue
                path = os.path.join(dirpath, name)
                with open(path, encoding="utf-8", errors="replace") as fh:
                    for no, line in enumerate(fh, 1):
                        if re.match(r"\s*print\(", line):
                            errors.append(f"{os.path.relpath(path, RUSH01)}:{no}: print() in the core")
    return errors


def run_unittests(folder):
    start = os.path.join(HERE, folder)
    if not os.path.isdir(start):
        return [f"tests/{folder}/ missing"]
    suite = unittest.defaultTestLoader.discover(start, pattern="test_*.py", top_level_dir=start)
    if suite.countTestCases() == 0:
        return [f"tests/{folder}: no tests yet"]
    res = unittest.TextTestRunner(verbosity=1).run(suite)
    if res.wasSuccessful():
        return []
    return [f"tests/{folder}: {len(res.failures)} failed, {len(res.errors)} errors"]


def read_expect(path):
    out = {}
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.split("#", 1)[0].strip()
            if "=" in line:
                k, v = line.split("=", 1)
                out[k.strip()] = v.strip()
    return out


def actual_labels(judge, detect):
    """The report, reduced to the keys of a corpus expect file (SHAPES)."""
    got = {}
    parts = detect["parts"]
    for p in ("parse", "data", "print"):
        got[p] = parts[p]["id"] or "unrecognized"
    s = parts["solve"]
    ids = [s["id"] or "unrecognized"] + list(s.get("also") or [])
    got["solve"] = " + ".join(ids)
    got["built"] = "yes" if judge["built"] else "no"
    got["ex_dir"] = "no" if judge["files"]["no_ex_dir"] else "yes"
    names = sorted({x["name"] for x in judge["forbidden"]["names"]})
    got["forbidden"] = " ".join(names) or "none"
    for g, c in judge["groups"].items():
        got[f"group.{g}"] = "fail" if c.get("fail") else "pass"
    best = (judge.get("diagnosis") or {}).get("best")
    got["diagnosis"] = best["id"] if best else "none"
    got["sanitizer"] = "finding" if judge["sanitizer"]["findings"] else "clean"
    norm = judge["norm"]
    got["norm"] = ("ok" if norm["ok"] else "errors") if norm["ran"] else "skipped"
    return got


def check_corpus():
    errors = []
    gen = os.path.join(HERE, "corpus", "gen.py")
    if not os.path.isfile(gen):
        return ["tests/corpus/gen.py missing"]
    # 1. the corpus checks itself
    r = subprocess.run([sys.executable, gen, "--check"], capture_output=True, text=True)
    if r.returncode != 0:
        errors.append("corpus gen.py --check failed:\n" + (r.stdout + r.stderr)[-2000:])
    # 2. judge + detect on every team, compared with expect/
    try:
        puzzle = importlib.import_module("puzzle")
        judge = importlib.import_module("judge")
        detect = importlib.import_module("detect")
        rush01 = importlib.import_module("rush01_wiring")
    except ImportError as e:
        return errors + [f"corpus: skipped the tool comparison ({e})"]
    subject = rush01.read_subject(os.path.join(TOOL, "subject.txt"))
    bank = puzzle.puzzle_load_bank(os.path.join(TOOL, "puzzle", "bank"))
    if os.environ.get("RUSH01_QUICK"):
        bank = [e for e in bank if e["group"] not in ("slow4", "nosol4-deep", "bonusN")]
    with tempfile.TemporaryDirectory(prefix="rush01-corpus-") as tmp:
        teams_dir = os.path.join(tmp, "repo")
        subprocess.run([sys.executable, gen, "--out", teams_dir], check=True,
                       capture_output=True)
        for team in sorted(os.listdir(teams_dir)):
            exp_path = os.path.join(HERE, "corpus", "expect", team + ".txt")
            if not os.path.isfile(exp_path):
                errors.append(f"corpus {team}: no expect file")
                continue
            team_dir = os.path.join(teams_dir, team)
            work = os.path.join(tmp, "work-" + team)
            os.makedirs(work)
            j = judge.judge_team(team_dir, subject, bank, work)
            d = detect.detect_team(team_dir, j["ex_dir"])
            got = actual_labels(j, d)
            exp = read_expect(exp_path)
            bad = [f"{k}: want {v!r}, got {got.get(k)!r}" for k, v in exp.items()
                   if got.get(k) != v]
            print(f"  corpus {team:6} {'ok' if not bad else 'MISMATCH'}")
            for b in bad:
                errors.append(f"corpus {team}: {b}")
    return errors


def main(argv):
    flags = {a for a in argv if a.startswith("--")}
    picked = [a for a in argv if not a.startswith("--")] or ALL
    unknown = [p for p in picked if p not in ALL]
    if unknown:
        print("unknown folder(s):", " ".join(unknown), "| known:", " ".join(ALL))
        return 2
    if "--quick" in flags:
        os.environ["RUSH01_QUICK"] = "1"
    if "--no-browser" in flags:
        os.environ["RUSH01_NO_BROWSER"] = "1"
    if "structure" not in picked:
        picked = ["structure"] + picked
    errors = []
    for p in picked:
        print(f"== {p}")
        if p == "structure":
            errs = check_structure()
        elif p == "corpus":
            errs = check_corpus()
        else:
            errs = run_unittests(p)
        for e in errs:
            print("  FAIL", e)
        errors += errs
    print()
    print("CHECK", "FAILED: %d problem(s)" % len(errors) if errors else "PASSED",
          "(" + " ".join(picked) + ")")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
