"""Judge one run against its puzzle entry (PLAN.md §6 step 7), and the sums
over all runs: groups, timing, diagnosis cases (steps 8, 9; SHAPES "run").
"""

import re
import statistics

from puzzle import puzzle_check

SHORT_CHARS = 60


def judge_run(entry, raw, subject):
    """entry: a puzzle entry; raw: a run_capped result -> a run (SHAPES)."""
    n = entry["n"]
    stdout = raw["stdout"].decode("utf-8", "replace")
    stderr = raw["stderr"].decode("utf-8", "replace")
    run = {"id": entry["id"], "group": entry["group"], "argv": entry["argv"],
           "expect": entry["expect"], "stdout": stdout, "stderr": stderr,
           "exit": raw["exit"], "signal": raw["signal"],
           "timed_out": raw["timed_out"], "time_ms": raw["time_ms"],
           "verdict": "pass", "reasons": [], "notes": [],
           "grid": parse_grid(stdout, n), "broken": []}
    # 1. the grid against the real clues, whatever was expected
    check = None
    if run["grid"] is not None and entry["clues"] is not None:
        check = puzzle_check(n, entry["clues"], run["grid"])
        run["broken"] = check["broken"]
    # 2. why it failed
    if raw["error"]:
        run["reasons"].append(f"could not start the program: {raw['error']}")
    elif raw["timed_out"]:
        run["reasons"].append(f"timed out after {entry['timeout_ms']} ms (killed)")
    elif raw["over_cap"]:
        run["reasons"].append("printed more than 1 MB: stopped")
    elif raw["signal"]:
        run["reasons"].append(f"crashed: {raw['signal']}")
    elif entry["expect"] == "grid":
        run["reasons"] += _grid_reasons(run, n, check, subject["error_text"])
    elif entry["expect"] == "error":
        _error_verdict(run, subject)
    if entry["expect"] != "error" and stderr:
        run["notes"].append("printed on stderr: " + _short(stderr))
    # 3. the verdict
    if entry["expect"] == "info":
        run["verdict"] = "info"
        if check is not None:
            fits = check["latin"] and not check["broken"]
            run["reasons"].append("printed a grid that " + (
                "fits every clue" if fits else "does not fit the clues"))
        elif printed_error(stdout, stderr, subject["error_text"]):
            run["reasons"].append("printed Error")
        run["notes"] = run["reasons"] + run["notes"]
        run["reasons"] = []
    elif run["reasons"]:
        run["verdict"] = "fail"
    elif entry["group"].startswith("multi"):
        run["notes"].append("several solutions exist: any correct grid passes")
    return run


def parse_grid(text, n):
    """The first n non-empty lines as n ints each, else None (lenient: the
    strict format is judged apart, so a trailing space still shows the grid).
    n is None for inputs that aren't any valid size: no grid to read."""
    if not n:
        return None
    rows = [line.split() for line in text.split("\n") if line.strip()]
    if len(rows) < n:
        return None
    grid = []
    for row in rows[:n]:
        if len(row) != n or not all(tok.isascii() and tok.isdigit() for tok in row):
            return None
        grid.append([int(tok) for tok in row])
    return grid


def count_groups(runs):
    """-> {group: {"pass", "fail", "info"}} in run order."""
    groups = {}
    for run in runs:
        counts = groups.setdefault(run["group"], {"pass": 0, "fail": 0, "info": 0})
        counts[run["verdict"]] += 1
    return groups


def sum_timing(runs):
    """-> the "timing" part: the slowest run and median slow4 / median ok4.
    Times are whole ms; a median of 0 ms counts as 1 ms (no division by 0)."""
    timing = {"slowest_id": None, "slowest_ms": None, "slow4_over_ok4": None}
    if runs:
        slowest = max(runs, key=lambda r: r["time_ms"])
        timing["slowest_id"] = slowest["id"]
        timing["slowest_ms"] = slowest["time_ms"]
    slow = [r["time_ms"] for r in runs if r["group"] == "slow4"]
    ok = [r["time_ms"] for r in runs if r["group"] == "ok4"]
    if slow and ok:
        ratio = statistics.median(slow) / max(statistics.median(ok), 1)
        timing["slow4_over_ok4"] = round(ratio, 1)
    return timing


def diagnosis_cases(runs, entries, error_text):
    """-> SHAPES "diagnosis case" list: judged runs (not info) on puzzles
    with clues, whose output is a grid or Error; no crash, no timeout."""
    cases = []
    for run, entry in zip(runs, entries):
        if entry["clues"] is None or entry["expect"] == "info":
            continue
        if run["timed_out"] or run["signal"] or run["exit"] is None:
            continue
        case = {"id": entry["id"], "n": entry["n"], "clues": entry["clues"]}
        if run["grid"] is not None:
            check = puzzle_check(entry["n"], entry["clues"], run["grid"])
            case.update(outcome="grid", grid=run["grid"],
                        correct=check["latin"] and not check["broken"])
        elif printed_error(run["stdout"], run["stderr"], error_text):
            case.update(outcome="error", grid=None,
                        correct=entry["expect"] == "error")
        else:
            continue
        cases.append(case)
    return cases


def printed_error(stdout, stderr, error_text):
    """Error on stdout, or only on stderr; spacing around it ignored."""
    word = error_text.strip()
    return stdout.strip() == word or (stdout.strip() == "" and stderr.strip() == word)


def _grid_reasons(run, n, check, error_text):
    """Reasons a valid puzzle's output fails: format, Latin, clues."""
    stdout = run["stdout"]
    grid = run["grid"]
    # 1. no grid at all
    if grid is None:
        if stdout == "":
            return ["printed nothing"]
        if stdout.strip() == error_text.strip():
            return ["printed Error on a puzzle that has a solution"]
        return [f"output is not a {n}x{n} grid: {_short(stdout)}"]
    # 2. the strict format: n lines of n digits, single spaces, final \n
    reasons = _format_reasons(stdout, n, grid)
    # 3. the grid itself
    if not all(1 <= v <= n for row in grid for v in row):
        reasons.append(f"values outside 1..{n}")
    if not check["latin"]:
        reasons.append("not a Latin square (a row or column repeats a value)")
    if check["broken"]:
        shown = ", ".join(f"{b['side']} {b['index'] + 1} wants {b['want']} sees {b['seen']}"
                          for b in check["broken"][:4])
        more = f" (+{len(check['broken']) - 4} more)" if len(check["broken"]) > 4 else ""
        reasons.append(f"breaks {len(check['broken'])} clue(s): {shown}{more}")
    return reasons


def _format_reasons(stdout, n, grid):
    canonical = "".join(" ".join(str(v) for v in row) + "\n" for row in grid)
    if stdout == canonical:
        return []
    reasons = []
    lines = stdout.split("\n")
    if stdout.endswith("\n"):
        lines.pop()
    else:
        reasons.append("no newline at the end of the output")
    row_shape = re.compile(r"[0-9]( [0-9]){%d}" % (n - 1))
    for i, line in enumerate(lines):
        if line != line.rstrip(" \t"):
            reasons.append(f"trailing space on line {i + 1}")
            break
    grid_lines = [line for line in lines if line.strip()][:n]
    for i, line in enumerate(grid_lines):
        if not row_shape.fullmatch(line.rstrip(" \t")):
            reasons.append(f"line {i + 1} is not {n} digits separated by single spaces")
            break
    if lines[:n] != grid_lines:
        reasons.append("blank line before or inside the grid")
    elif any(line.strip() for line in lines[n:]):
        reasons.append("extra output after the grid: " + _short("\n".join(lines[n:])))
    elif lines[n:]:
        reasons.append("extra blank line after the grid")
    if not reasons:
        reasons.append(f"output is not exactly {n} lines of {n} digits")
    return reasons


def _error_verdict(run, subject):
    """An error puzzle: exactly error_text on stdout; on stderr per subject."""
    stdout, stderr = run["stdout"], run["stderr"]
    err = subject["error_text"]
    # 1. right
    if stdout == err:
        if stderr:
            run["notes"].append("also printed on stderr: " + _short(stderr))
        return
    if stdout == "" and stderr == err:
        if subject["error_on_stderr"] == "fail":
            run["reasons"].append("Error printed on stderr (fd 2), the subject wants stdout")
        else:
            run["notes"].append("Error printed on stderr (fd 2), not stdout")
        return
    # 2. wrong: say how
    if run["grid"] is not None:
        run["reasons"].append("printed a grid, expected Error")
    elif stdout == "" and stderr == "":
        run["reasons"].append("printed nothing, expected Error")
    elif stdout.startswith(err):
        run["reasons"].append("extra output on stdout after Error: " + _short(stdout[len(err):]))
    else:
        where = "stdout" if stdout else "stderr"
        run["reasons"].append(f"printed {_short(stdout or stderr)} on {where}, "
                              f"expected {err!r} on stdout")
    if stderr and stderr != err:
        run["notes"].append("printed on stderr: " + _short(stderr))


def _short(text):
    return repr(text[:SHORT_CHARS]) + ("..." if len(text) > SHORT_CHARS else "")
