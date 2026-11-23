"""Norminette on the turn-in's .c and .h (PLAN.md §6 step 4). Output parsing
follows rush00's _norm; checked on norminette 3.3.59 (PROOF-8).
"""

import re
import shutil

from .judge_process import run_capped

NORM_MS = 180_000
NORM_ERRORS_CAP = 300
ANSI = re.compile(r"\x1b\[[0-9;]*m")
FILE_LINE = re.compile(r"^(.+?): (OK|Error)!")
ERROR_LINE = re.compile(r"^\s*Error:\s*(\S+)\s*\(line:\s*(\d+),\s*col:\s*(\d+)\):\s*(.*)")


def run_norm(ex_abs, ex_dir, files, flags):
    """-> the "norm" part of the judge result (SHAPES)."""
    result = {"ran": False, "ok": None, "errors": [], "note": ""}
    names = [rel.split("/")[-1] for rel in files["sources"] + files["headers"]]
    # 1. the tool and something to check
    if shutil.which("norminette") is None:
        result["note"] = "norminette not installed: skipped"
        return result
    if not names:
        result["note"] = "no .c or .h files: nothing to check"
        return result
    # 2. run, without the flags if this norminette doesn't know them (rush00)
    r = run_capped(["norminette"] + list(flags) + names, ex_abs, NORM_MS)
    out = ANSI.sub("", (r["stdout"] + r["stderr"]).decode("utf-8", "replace"))
    if flags and (r["exit"] not in (0, 1) or "usage" in out.lower()[:200]):
        r = run_capped(["norminette"] + names, ex_abs, NORM_MS)
        out = ANSI.sub("", (r["stdout"] + r["stderr"]).decode("utf-8", "replace"))
        result["note"] = "norminette rejected the flags: ran without them"
    if r["timed_out"] or r["error"]:
        result["note"] = "norminette did not finish: " + (r["error"] or "timed out")
        return result
    # 3. per-file status and errors
    result["ran"] = True
    current = None
    any_error = False
    total = 0
    for line in out.split("\n"):
        m = FILE_LINE.match(line)
        if m:
            current = m.group(1)
            any_error = any_error or m.group(2) == "Error"
            continue
        m = ERROR_LINE.match(line)
        if m and current:
            total += 1
            if len(result["errors"]) < NORM_ERRORS_CAP:
                result["errors"].append({
                    "file": _rel(ex_dir, current), "line": int(m.group(2)),
                    "text": f"{m.group(1)}: {m.group(4).strip()}"})
    result["ok"] = not any_error and total == 0
    if total > NORM_ERRORS_CAP:
        result["note"] = "; ".join(filter(None, [
            result["note"], f"{total} errors, the first {NORM_ERRORS_CAP} listed"]))
    return result


def _rel(ex_dir, name):
    return name if ex_dir == "." else f"{ex_dir}/{name}"
