"""Make, save and load the puzzle bank (PLAN.md §5 table, SHAPES "puzzle
entry"). Regenerate bank/ from rush01/tool with: python3 -m puzzle"""

import json
import os
import random

from .puzzle_cost import cost_latin_squares, cost_naive_tries
from .puzzle_misread import MISREADINGS, misread_constraints
from .puzzle_solve import puzzle_check, puzzle_clues, solve_constraints
from .puzzle_solve import subject_constraints

GROUPS = ["evalsheet", "ok4", "multi4", "nosol4-easy", "nosol4-deep", "slow4",
          "fmt", "bonusN", "small"]
TIMEOUT_MS = {"evalsheet": 2000, "ok4": 2000, "multi4": 2000, "nosol4-easy": 2000,
              "nosol4-deep": 5000, "slow4": 5000, "fmt": 2000,
              "bonusN": 10000, "small": 2000}
PDF_CLUES = [4, 3, 2, 1, 1, 2, 2, 2, 4, 3, 2, 1, 1, 2, 2, 2]
COUNTS = {"ok4": 10, "multi4": 6, "nosol4-deep": 8, "slow4": 6}
# Misreadings that print a wrong grid on few puzzles get one such puzzle in
# the bank, so a team with them doesn't print Error everywhere. Seven
# others (swap_top_bottom, swap_left_right, clockwise, bottom_no_reverse,
# right_no_reverse, count_plus1, count_minus1) fit no valid 4x4 puzzle at
# all (checked on all 438 clue lists): those teams print Error everywhere.
DIAGNOSTIC_OK4 = ["interleaved", "reverse_top", "reverse_bottom",
                  "reverse_left", "reverse_right"]
DIAGNOSTIC_MULTI4 = ["max_one"]
# Solving or proving a bonus puzzle stops after this many nodes (about
# 0.4 s); a puzzle the solver can't settle in that is not used. Measured on
# random full-clue puzzles: 7x7 are nearly always 2+ solutions, and most
# 8x8 / 9x9 ones don't settle, so one in ~10 is kept.
BONUS_NODE_CAP = 20000
BONUS_TRIES = 40
# nosol4-easy: (pair, values) -> one line that no grid can show.
EASY_BREAKS = [("col", (1, 1)), ("row", (1, 1)), ("col", (3, 3)),
               ("row", (4, 2)), ("col", (2, 4)), ("row", (4, 4))]


def puzzle_make_bank(seed=2026):
    """Every group of the bank, {group: [puzzle entry...]} (pure)."""
    rng = random.Random(seed)
    bank = {"evalsheet": _make_evalsheet()}
    # 1. all 576 4x4 Latin squares, grouped by their clues: a clue list's
    #    solutions are exactly the squares that show it
    squares, total_tries = cost_latin_squares(4)
    by_clues = {}
    for grid, tries in squares:
        by_clues.setdefault(tuple(puzzle_clues(grid)), []).append((grid, tries))
    unique = sorted(clues for clues, found in by_clues.items() if len(found) == 1)
    multi = sorted(clues for clues, found in by_clues.items() if len(found) > 1)
    # 2. the 4x4 groups
    bank["ok4"] = _make_ok4(rng, unique, by_clues)
    used = {tuple(entry["clues"]) for entry in bank["ok4"]}
    bank["multi4"] = _make_multi4(rng, multi, by_clues)
    bank["nosol4-easy"] = _make_nosol_easy(rng, unique)
    bank["nosol4-deep"] = _make_nosol_deep(rng, unique, by_clues, total_tries)
    bank["slow4"] = _make_slow4(unique, used, by_clues)
    bank["fmt"] = _make_fmt()
    # 3. the other sizes
    bank["bonusN"] = _make_bonus(rng)
    bank["small"] = _make_small(rng)
    return bank


# The exact inputs of the intra evaluation sheet (2026-11-22), all `Error`.
EVALSHEET = [
    ("4 3 2 1 1 2 2 2 4 3 2 1 1 2 2 2 3", "sheet: poorly shaped (17 numbers)"),
    ("4 3 2 1 1 2 2 2 4 3 2 1 1 2 2", "sheet: poorly shaped (15 numbers)"),
    ("4 3 2 1 1 2 2 2 6 3 2 1 1 2 2 2", "sheet: poorly shaped (a 6)"),
    ("4321122243211222", "sheet: poorly shaped (no spaces)"),
    ("Hello", "sheet: poorly shaped (Hello)"),
    ("4 3 2 1 1 2 2 2 4 3 2 1 1 2 2 4", "sheet: wrong grid, no valid solution"),
]


def _make_evalsheet():
    """The sheet's eliminatory tests, word for word (expect Error)."""
    out = []
    for k, (text, note) in enumerate(EVALSHEET):
        clues = [int(x) for x in text.split()] if k == 5 else None
        out.append(_entry("evalsheet", k + 1, 4, [text], clues, "error", note))
    return out


def puzzle_save_bank(bank_dir_abs, bank):
    """Write bank/<group>.jsonl: one entry per line, sorted keys."""
    os.makedirs(bank_dir_abs, exist_ok=True)
    # 1. one file per group, entries in id order
    for group in GROUPS:
        if group not in bank:
            continue
        lines = [json.dumps(entry, sort_keys=True) + "\n"
                 for entry in sorted(bank[group], key=lambda e: e["id"])]
        path = os.path.join(bank_dir_abs, group + ".jsonl")
        with open(path, "w", encoding="utf-8", newline="\n") as fh:
            fh.write("".join(lines))


def puzzle_load_bank(bank_dir_abs):
    """Every entry of the bank, group order as in SHAPES, then id."""
    entries = []
    # 1. each known group file that exists
    for group in GROUPS:
        path = os.path.join(bank_dir_abs, group + ".jsonl")
        if not os.path.isfile(path):
            continue
        found = []
        with open(path, encoding="utf-8") as fh:
            for number, line in enumerate(fh, 1):
                if not line.strip():
                    continue
                try:
                    found.append(json.loads(line))
                except ValueError as e:
                    raise ValueError("%s:%d: %s" % (path, number, e)) from None
        entries += sorted(found, key=lambda e: e["id"])
    return entries


def _entry(group, number, n, argv, clues, expect, note):
    """One puzzle entry (SHAPES), numbered from 1 within its group."""
    return {"id": "%s-%02d" % (group, number), "group": group, "n": n,
            "argv": argv, "clues": None if clues is None else list(clues),
            "expect": expect, "timeout_ms": TIMEOUT_MS[group], "note": note}


def _argv(clues):
    """The single argument a puzzle is given as."""
    return [" ".join(str(value) for value in clues)]


def _sides(clues):
    """(top, bottom, left, right) of a clue list."""
    n = len(clues) // 4
    return [tuple(clues[k * n:(k + 1) * n]) for k in range(4)]


def _cost_note(grid, tries):
    """How long the student solvers take on it."""
    return "piscine %d tries, naive %d grids" % (tries, cost_naive_tries(4, grid))


def _make_ok4(rng, unique, by_clues):
    """The PDF example, a diagnostic puzzle per DIAGNOSTIC_OK4 misreading,
    then random unique puzzles whose four sides all differ (a solver with
    rows and columns swapped passes the symmetric PDF one)."""
    entries = [_entry("ok4", 1, 4, _argv(PDF_CLUES), PDF_CLUES, "grid",
                      "PDF example (symmetric: top == left, bottom == right)")]
    # 1. the diagnostic ones
    picked = _diagnostic(rng, unique, DIAGNOSTIC_OK4)
    for clues, note in picked:
        grid, tries = by_clues[clues][0]
        entries.append(_entry("ok4", len(entries) + 1, 4, _argv(clues), clues,
                              "grid", "unique; %s; %s"
                              % (note, _cost_note(grid, tries))))
    # 2. the asymmetric candidates, picked at random
    taken = {clues for clues, note in picked}
    candidates = [clues for clues in unique
                  if len(set(_sides(clues))) == 4 and list(clues) != PDF_CLUES
                  and clues not in taken]
    rng.shuffle(candidates)
    for clues in candidates[:COUNTS["ok4"] - len(picked)]:
        grid, tries = by_clues[clues][0]
        entries.append(_entry("ok4", len(entries) + 1, 4, _argv(clues), clues,
                              "grid", "unique, all four sides differ; "
                              + _cost_note(grid, tries)))
    return entries


def _make_multi4(rng, multi, by_clues):
    """Puzzles with several solutions (any correct grid passes): the one
    with the most, a diagnostic one per DIAGNOSTIC_MULTI4, random ones."""
    entries = []
    # 1. the most solutions, the diagnostic ones, then random ones
    most = max(multi, key=lambda clues: (len(by_clues[clues]), clues))
    picked = [(most, "")] + _diagnostic(rng, multi, DIAGNOSTIC_MULTI4)
    candidates = [clues for clues in multi
                  if clues not in {clues for clues, note in picked}]
    rng.shuffle(candidates)
    picked += [(clues, "") for clues in
               candidates[:COUNTS["multi4"] - len(picked)]]
    for clues, note in picked:
        text = "%d solutions" % len(by_clues[clues])
        if note:
            text += "; " + note
        entries.append(_entry("multi4", len(entries) + 1, 4, _argv(clues),
                              clues, "grid", text))
    return entries


def _diagnostic(rng, clue_sets, rule_ids):
    """[(clues, note)]: for each misreading, a puzzle on which every grid a
    team with it can print is wrong (so that team prints a grid here, and
    its Errors elsewhere can vote). Four sides all different preferred."""
    rules = {rule["id"]: rule for rule in MISREADINGS}
    picked = []
    # 1. per misreading, the fitting puzzles not picked yet, one at random
    for rule_id in rule_ids:
        taken = {clues for clues, note in picked}
        fitting = []
        for clues in clue_sets:
            if clues in taken:
                continue
            found = solve_constraints(
                4, misread_constraints(rules[rule_id], 4, list(clues)), 50, None)
            if found["solutions"] and all(
                    puzzle_check(4, list(clues), grid)["broken"]
                    for grid in found["solutions"]):
                fitting.append(clues)
        assert fitting, "no diagnostic puzzle for " + rule_id
        best = [clues for clues in fitting if len(set(_sides(clues))) == 4]
        pool = best or fitting
        clues = pool[rng.randrange(len(pool))]
        picked.append((clues, "diagnostic: %s gives a wrong grid"
                       % rules[rule_id]["text"]))
    return picked


def _make_nosol_easy(rng, unique):
    """A unique puzzle with one opposite pair made impossible on its line."""
    entries = []
    # 1. one break per recipe, on a random puzzle and line
    for pair, values in EASY_BREAKS:
        clues = list(unique[rng.randrange(len(unique))])
        index = rng.randrange(4)
        if pair == "col":
            first, second = index, 4 + index
            where = "column %d (top, bottom)" % (index + 1)
        else:
            first, second = 8 + index, 12 + index
            where = "row %d (left, right)" % (index + 1)
        clues[first], clues[second] = values
        why = "a 1 1 pair" if values == (1, 1) else "a pair summing %d > 5" \
            % sum(values)
        entries.append(_entry("nosol4-easy", len(entries) + 1, 4, _argv(clues),
                              clues, "error", "%s on %s" % (why, where)))
    return entries


def _make_nosol_deep(rng, unique, by_clues, total_tries):
    """Every opposite pair sums 3..5 (fine on its own line), yet no grid
    fits. With no solution the piscine solver always runs its full search
    (the same tries for all), so these are ranked by the exact solver's
    nodes: hardest to refute first."""
    entries = []
    # 1. change one clue of a unique puzzle, keeping every pair fine
    candidates = set()
    for clues in unique:
        for k in range(16):
            for value in range(1, 5):
                changed = list(clues)
                changed[k] = value
                changed = tuple(changed)
                if changed not in by_clues and _pairs_fine(changed):
                    candidates.add(changed)
    candidates = sorted(candidates)
    rng.shuffle(candidates)
    # 2. the 200 first, ranked by exact-solver nodes
    ranked = []
    for clues in candidates[:200]:
        found = solve_constraints(4, subject_constraints(4, list(clues)), 1, None)
        assert not found["solutions"], "a deep no-solution puzzle has one"
        ranked.append((-found["nodes"], clues))
    ranked.sort()
    for minus_nodes, clues in ranked[:COUNTS["nosol4-deep"]]:
        entries.append(_entry("nosol4-deep", len(entries) + 1, 4, _argv(clues),
                              clues, "error", "every pair fine, no grid; exact "
                              "%d nodes, piscine %d tries (full search)"
                              % (-minus_nodes, total_tries)))
    return entries


def _pairs_fine(clues):
    """Every opposite pair sums 3..5 (so no 1 1 pair)."""
    pairs = [(clues[c], clues[4 + c]) for c in range(4)]
    pairs += [(clues[8 + r], clues[12 + r]) for r in range(4)]
    return all(3 <= a + b <= 5 for a, b in pairs)


def _make_slow4(unique, used, by_clues):
    """Unique puzzles the piscine solver takes longest on (its answer comes
    late in its order); ties: more 2s and 3s."""
    entries = []
    # 1. rank every unique puzzle not already in ok4
    ranked = []
    for clues in unique:
        if clues in used:
            continue
        grid, tries = by_clues[clues][0]
        middle = sum(1 for value in clues if value in (2, 3))
        ranked.append((-tries, -middle, clues))
    ranked.sort()
    for minus_tries, minus_middle, clues in ranked[:COUNTS["slow4"]]:
        grid, tries = by_clues[clues][0]
        entries.append(_entry("slow4", len(entries) + 1, 4, _argv(clues),
                              clues, "grid", "unique; " + _cost_note(grid, tries)))
    return entries


def _make_fmt():
    """Malformed input: every case of PLAN.md §5, all expecting Error."""
    words = [str(value) for value in PDF_CLUES]
    pdf = " ".join(words)
    # 1. the PDF example with one number (the 6th) replaced
    def replaced(text):
        return " ".join(words[:5] + [text] + words[6:])
    cases = [
        ([""], "empty string"),
        (["1"], "one number"),
        (["4 3"], "two numbers"),
        ([" ".join(words[:15])], "15 numbers"),
        ([pdf + " 2"], "17 numbers"),
        ([replaced("0")], "a 0"),
        ([replaced("5")], "a 5 (above N = 4)"),
        ([replaced("/")], "'/' (just below '0')"),
        ([replaced(":")], "':' (just above '9')"),
        ([replaced("12")], "a two-digit number 12"),
        ([replaced("04")], "a leading zero: 04"),
        ([replaced("a")], "a letter"),
        ([pdf.replace(" ", "  ", 1)], "double space"),
        ([" " + pdf], "leading space"),
        ([pdf + " "], "trailing space"),
        ([pdf.replace(" ", "\t", 1)], "a tab instead of a space"),
        ([pdf.replace(" ", "\v", 1)], "a \\v instead of a space"),
        ([pdf.replace(" ", "\n", 1)], "a \\n inside"),
        ([pdf + "\n"], "trailing \\n"),
        ([replaced("-1")], "a negative number -1"),
        ([replaced("+1")], "a plus sign +1"),
        ([], "no argument"),
        ([" ".join(words[:8]), " ".join(words[8:])], "two arguments"),
    ]
    return [_entry("fmt", k + 1, 4, argv, None, "error", note)
            for k, (argv, note) in enumerate(cases)]


def _make_bonus(rng):
    """N = 5..9: a valid, a several-solution and an impossible puzzle each,
    then input the bonus must refuse."""
    entries = []
    # 1. three puzzles per size
    for n in range(5, 10):
        for clues, expect, note in _bonus_size(rng, n):
            entries.append(_entry("bonusN", len(entries) + 1, n, _argv(clues),
                                  clues, expect, note))
    # 2. counts and values the bonus can't take
    five = puzzle_clues(_random_latin(rng, 5))
    bad_value = list(five)
    bad_value[rng.randrange(20)] = 6
    ten = puzzle_clues(_random_latin(rng, 10))
    refused = [
        (None, _argv(five[:18]), "18 numbers: not 4N for any N"),
        (5, _argv(bad_value), "a 6 among 20 numbers (above N = 5)"),
        (10, _argv(ten), "N = 10: real 10x10 clues, the bonus stops at 9"),
    ]
    for n, argv, note in refused:
        entries.append(_entry("bonusN", len(entries) + 1, n, argv, None,
                              "error", note))
    return entries


def _bonus_size(rng, n):
    """[(clues, expect, note)] for one size: valid, multi, impossible. Only
    puzzles the exact solver settles within BONUS_NODE_CAP are used."""
    valid = None
    multi = None
    out = []
    # 1. valid: a proved-unique puzzle for n <= 6 (else the first solvable
    #    one); for 7..9 the first solvable one. The note says what was
    #    proved.
    for _ in range(BONUS_TRIES):
        clues = puzzle_clues(_random_latin(rng, n))
        limit = 2 if n <= 7 else 1
        found = solve_constraints(n, subject_constraints(n, clues), limit,
                                  BONUS_NODE_CAP)
        if not found["solutions"]:
            continue
        if n >= 8:
            note = "solvable (uniqueness not checked)"
        elif len(found["solutions"]) == 2:
            note = "2+ solutions"
        elif found["complete"]:
            note = "unique"
        else:
            note = "solvable (uniqueness not proved)"
        if valid is None or note == "unique":
            valid = (clues, "grid", "%dx%d, %s" % (n, n, note))
        if note == "unique" or n >= 7:
            break
    assert valid, "no valid bonus puzzle found for N = %d" % n
    # 2. multi: a square with a 2x2 "a b / b a" whose swap keeps every clue,
    #    so two solutions are known without a search
    for _ in range(BONUS_TRIES):
        grid = _random_latin(rng, n)
        clues = puzzle_clues(grid)
        if _has_clue_keeping_swap(n, grid, clues):
            multi = (clues, "grid", "%dx%d, 2+ solutions (a 2x2 swap keeps "
                     "every clue)" % (n, n))
            break
    assert multi, "no multi bonus puzzle found for N = %d" % n
    out += [valid, multi]
    # 3. impossible: change one clue of the valid puzzle, every pair still
    #    fine on its line, until the solver proves no grid fits
    base = valid[0]
    for _ in range(BONUS_TRIES):
        clues = list(base)
        clues[rng.randrange(4 * n)] = 1 + rng.randrange(n)
        if clues == base or not _pairs_fine_n(n, clues):
            continue
        found = solve_constraints(n, subject_constraints(n, clues), 1,
                                  BONUS_NODE_CAP)
        if found["complete"] and not found["solutions"]:
            out.append((clues, "error", "%dx%d, every pair fine, no grid"
                        % (n, n)))
            return out
    # 4. none proved in time: break one line instead (provably impossible)
    clues = list(base)
    clues[0] = n
    clues[n] = n
    out.append((clues, "error", "%dx%d, column 1 is %d %d: impossible on "
                "its line" % (n, n, n, n)))
    return out


def _has_clue_keeping_swap(n, grid, clues):
    """Some 2x2 a b / b a in the grid can be swapped without changing any
    clue: the swapped grid is a second solution."""
    # 1. every pair of rows and pair of columns
    for r1 in range(n):
        for r2 in range(r1 + 1, n):
            for c1 in range(n):
                for c2 in range(c1 + 1, n):
                    a = grid[r1][c1]
                    b = grid[r1][c2]
                    if grid[r2][c1] != b or grid[r2][c2] != a:
                        continue
                    other = [row[:] for row in grid]
                    other[r1][c1], other[r1][c2] = b, a
                    other[r2][c1], other[r2][c2] = a, b
                    if puzzle_clues(other) == clues:
                        return True
    return False


def _pairs_fine_n(n, clues):
    """Every opposite pair fits one line: sum 3..n+1."""
    pairs = [(clues[c], clues[n + c]) for c in range(n)]
    pairs += [(clues[2 * n + r], clues[3 * n + r]) for r in range(n)]
    return all(3 <= a + b <= n + 1 for a, b in pairs)


def _random_latin(rng, n):
    """A random Latin square of 1..n: row by row, values in random order,
    backtracking when a cell has no value left."""
    grid = [[0] * n for _ in range(n)]
    rows = [0] * n
    cols = [0] * n
    # 1. fill every cell (the search always ends with a full square)
    filled = _random_fill(rng, n, 0, grid, rows, cols)
    assert filled, "no Latin square"
    return grid


def _random_fill(rng, n, cell, grid, rows, cols):
    """Fill cells from `cell` on; True when the grid is full."""
    if cell == n * n:
        return True
    r = cell // n
    c = cell % n
    values = list(range(1, n + 1))
    rng.shuffle(values)
    for value in values:
        bit = 1 << value
        if rows[r] & bit or cols[c] & bit:
            continue
        grid[r][c] = value
        rows[r] |= bit
        cols[c] |= bit
        if _random_fill(rng, n, cell + 1, grid, rows, cols):
            return True
        grid[r][c] = 0
        rows[r] &= ~bit
        cols[c] &= ~bit
    return False


def _make_small(rng):
    """N = 1, 2, 3: recorded, never pass/fail."""
    entries = []
    for n in (1, 2, 3):
        clues = puzzle_clues(_random_latin(rng, n))
        entries.append(_entry("small", n, n, _argv(clues), clues, "info",
                              "%dx%d (outside the subject: info only)" % (n, n)))
    return entries

